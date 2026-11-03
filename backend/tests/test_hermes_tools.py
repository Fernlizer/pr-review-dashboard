import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from config import settings
from services import hermes_jobs as jobs, llm_reviewer, pr_scanner_tools as scanners
from services.hermes_mcp import AuthenticatedMCP


class JobTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        scope = patch.object(jobs, 'ROOT', Path(temp.name)/'jobs'); scope.start(); self.addCleanup(scope.stop)

    def test_review_requires_actual_skill_and_scanner_receipts(self):
        token = jobs.create_job('review', {'files':[{'path':'/src/a.ts','src_content':'const x=1;'}], 'changed_lines':{'/src/a.ts':[1]}})
        self.addCleanup(jobs.delete_job,token)
        with self.assertRaises(RuntimeError): jobs.require_complete(token)
        jobs.read_context(token)
        for name in ['fp-check','differential-review','gitleaks']:
            self.assertIn('SKILL.md',jobs.load_skill(token,name)['files'])
        with self.assertRaises(RuntimeError): jobs.require_complete(token)
        with patch.object(jobs,'scan_secrets',return_value={'status':'completed','findings':[]}) as scanner:
            jobs.run_scanner(token,'gitleaks'); jobs.run_scanner(token,'gitleaks')
        scanner.assert_called_once()
        jobs.require_complete(token)

    def test_osv_selected_only_when_supported_dependency_file_changes(self):
        token = jobs.create_job('review',{'files':[{'path':'/requirements.txt','src_content':'requests==2.19.1'}]})
        self.addCleanup(jobs.delete_job,token)
        self.assertIn('osv-scanner',jobs.read_context(token)['required_skills'])
        with self.assertRaises(ValueError): jobs.run_scanner(token,'osv-scanner')
        jobs.load_skill(token,'osv-scanner')
        with patch.object(jobs,'scan_dependencies',side_effect=RuntimeError('unavailable')):
            with self.assertRaises(RuntimeError): jobs.run_scanner(token,'osv-scanner')
        with jobs.locked_job(token) as job:
            self.assertNotIn('osv-scanner',job['receipts'])

    def test_discussion_uses_fp_check_without_rescanning_absent_code(self):
        token = jobs.create_job('discussion',{}); self.addCleanup(jobs.delete_job,token)
        self.assertEqual(jobs.read_context(token)['required_skills'],['fp-check'])
        jobs.load_skill(token,'fp-check')
        with self.assertRaises(ValueError): jobs.run_scanner(token,'gitleaks')
        jobs.require_complete(token)

    def test_job_capabilities_and_reference_paths_cannot_escape_scope(self):
        token = jobs.create_job('review',{'files':[{'path':'/a.ts','src_content':'head','tgt_content':'base'}]})
        self.addCleanup(jobs.delete_job,token)
        self.assertEqual(jobs.read_context(token,'/a.ts','base')['content'],'base')
        for action in [lambda:jobs.read_context(token,'/etc/passwd'),
                       lambda:jobs.load_skill(token,'fp-check','../../../config.py'),
                       lambda:jobs.load_skill(token,'other-skill'),
                       lambda:jobs.read_context('../job'),
                       lambda:jobs.create_job('review',{'files':[{'path':'../../etc/passwd'}]})]:
            with self.assertRaises((ValueError,OSError)): action()


class ScannerTests(unittest.TestCase):
    def test_gitleaks_output_contains_no_raw_secret_or_match(self):
        secret = 'FAKE-secret-only-used-for-this-unit-test'
        def run(command, root, report):
            self.assertIn('--redact=100',command)
            return [{'File':str(root/'source/src/a.ts'),'StartLine':2,'EndLine':2,'RuleID':'test',
                     'Secret':secret,'Match':'key='+secret}]
        with patch.object(scanners,'_run',side_effect=run):
            data=scanners.scan_secrets([{'path':'/src/a.ts','src_content':'const x=1;'}],{'/src/a.ts':[2]})
        self.assertEqual(len(data['findings']),1)
        self.assertNotIn(secret,json.dumps(data))
        self.assertEqual(data['findings'][0]['code_snippet'],'<redacted secret>')

    def test_osv_baseline_only_vulnerabilities_are_not_reported_as_introduced(self):
        def scan(root):
            vulnerabilities=[{'id':'EXISTING','summary':'old'}]
            if root.name=='head': vulnerabilities.append({'id':'NEW','summary':'new'})
            return {'results':[{'source':{'path':str(root/'requirements.txt')},'packages':[
                {'package':{'name':'example','version':'1','ecosystem':'PyPI'},'vulnerabilities':vulnerabilities}]}]}
        with patch.object(scanners,'_osv_scan',side_effect=scan):
            result=scanners.scan_dependencies([{'path':'/requirements.txt','tgt_content':'example==1','src_content':'example==2'}])
        self.assertEqual([f['vulnerability_id'] for f in result['findings']],['NEW'])
        self.assertEqual(result['baseline_count'],1)
        self.assertEqual(scanners.scan_dependencies([])['status'],'not_applicable')


class ToolTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_unauthenticated_mcp_request_never_reaches_tools(self):
        downstream=AsyncMock()
        with patch.object(settings,'HERMES_TOOLS_KEY','test-scoped-token'):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=AuthenticatedMCP(downstream)),base_url='http://test') as c:
                self.assertEqual((await c.post('/')).status_code,401)
        downstream.assert_not_awaited()

    async def test_snapshot_fetch_uses_iteration_commits_instead_of_moving_branches(self):
        from services.azure_client import AzureDevOpsClient
        client=AzureDevOpsClient()
        client.fetch_file_content=AsyncMock(return_value="const a=1;")
        await client.fetch_files_parallel('test',[{'item':{'path':'/a.ts'},'changeType':'edit'}],
            'feature','main',source_commit='source-sha',target_commit='target-sha')
        calls=client.fetch_file_content.await_args_list
        self.assertEqual({c.args[2] for c in calls},{'source-sha','target-sha'})
        self.assertTrue(all(c.kwargs['version_type']=='commit' for c in calls))

    async def test_fetch_content_requests_raw_commit_data(self):
        from services.azure_client import AzureDevOpsClient
        from services import azure_client
        client=AsyncMock();client.__aenter__.return_value=client
        client.get.return_value=httpx.Response(200,text='const x=1;',request=httpx.Request('GET','http://test'))
        with patch.object(azure_client.httpx,'AsyncClient',return_value=client):
            text=await AzureDevOpsClient().fetch_file_content('test','/file with space.ts','abc',version_type='commit')
        self.assertEqual(text,'const x=1;')
        self.assertIn('versionDescriptor.versionType=commit',client.get.call_args.args[0])
        self.assertEqual(client.get.call_args.kwargs['headers']['Accept'],'text/plain')

    async def test_unverified_scanner_candidate_cannot_bypass_hermes_into_comments(self):
        from models import PullRequest, Finding
        from services import pr_poller
        from services.azure_client import FetchedFile
        from services.security_scanner import SecurityFinding
        from unittest.mock import MagicMock
        db=MagicMock(commit=AsyncMock(),flush=AsyncMock())
        client=MagicMock(get_pr_iterations=AsyncMock(return_value=(1,'source','target')),
            get_pr_changes=AsyncMock(return_value=[{}]),
            fetch_files_parallel=AsyncMock(return_value=[FetchedFile(path='/a.ts',change_type='add',src_content='safe code')]))
        candidate=SecurityFinding(file='/a.ts',line=1,pattern='unverified',severity='HIGH',owasp='A01',code='safe code',source='grep')
        pr=PullRequest(id=7,azure_pr_id=99,repo='test')
        with patch.multiple(settings,LLM_BACKEND='hermes',HERMES_REQUIRE_TOOLS=True), patch.object(
            pr_poller,'run_security_scan',return_value=[candidate]
        ), patch.object(llm_reviewer,'review_pr_with_llm',new=AsyncMock(return_value=[])), patch.object(
            pr_poller,'_maybe_auto_comment',new=AsyncMock()
        ):
            await pr_poller._process_new_pr_unlocked(db,client,'test',
                {'azure_pr_id':99,'source_branch':'test','target_branch':'main'},existing_pr=pr)
        self.assertFalse(any(isinstance(c.args[0],Finding) for c in db.add.call_args_list))
        review=db.add.call_args_list[0].args[0]
        self.assertIn('unverified',review.security_scan_json)
        self.assertEqual(review.score_security,10)

    async def test_final_answer_is_rejected_if_hermes_skips_tools(self):
        client=AsyncMock();client.__aenter__.return_value=client
        client.post.return_value=httpx.Response(200,json={'choices':[{'message':{'content':'[]'}}]},request=httpx.Request('POST','http://test'))
        with tempfile.TemporaryDirectory() as directory, patch.object(jobs,'ROOT',Path(directory)/'jobs'), patch.multiple(
            settings,LLM_BACKEND='hermes',HERMES_REQUIRE_TOOLS=True,HERMES_API_KEY='test-key'
        ), patch.object(llm_reviewer.httpx,'AsyncClient',return_value=client):
            self.assertIsNone(await llm_reviewer._call_llm('Review without tools'))
            self.assertEqual(list((Path(directory)/'jobs').glob('*/job.json')),[])
