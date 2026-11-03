import asyncio
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from services import hermes_jobs as jobs, hermes_mcp as tools


class BatchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root = patch.object(jobs, 'ROOT', Path(temp.name)/'jobs'); root.start(); self.addCleanup(root.stop)
        self.context = {'repo':'test', 'source_commit':'source-A', 'files':[
            {'path':'/requirements.txt','change_type':'edit','src_content':'requests==2.19.1',
             'tgt_content':'requests==2.32.4','diff':'-requests==2.32.4\n+requests==2.19.1'}],
             'changed_lines':{'/requirements.txt':[1]}}

    def job(self, context=None, task='review', batch=True):
        token = jobs.create_job(task, self.context if context is None else context, batch=batch)
        self.addCleanup(jobs.delete_job, token)
        return token

    async def test_bundle_contains_the_same_complete_evidence_as_original_calls(self):
        old, new = self.job(batch=False), self.job()
        secret = {'scanner':'gitleaks','status':'completed','findings':[{'rule':'test','code_snippet':'<redacted secret>'}]}
        dependency = {'scanner':'osv-scanner','status':'completed','findings':[{'vulnerability_id':'CVE-test'}]}
        with patch.object(jobs,'scan_secrets',return_value=secret), patch.object(jobs,'scan_dependencies',return_value=dependency):
            context=jobs.read_context(old)
            skills=[jobs.load_skill(old,name) for name in context['required_skills']]
            scanners=[jobs.run_scanner(old,name) for name in ['gitleaks','osv-scanner']]
            bundled=await tools.dashboard_prepare_review(new)
        self.assertEqual(bundled['context'],context)
        self.assertEqual(bundled['skills'],skills)
        self.assertEqual(bundled['scanners'],scanners)
        jobs.require_complete(new)
        with jobs.locked_job(new) as job:self.assertEqual(job['receipts']['preparation'],'bundle')

    async def test_independent_scanners_run_concurrently(self):
        barrier=threading.Barrier(2)
        def scan(*args):
            barrier.wait(timeout=2)
            return {'status':'completed','findings':[]}
        token=self.job()
        with patch.object(jobs,'scan_secrets',side_effect=scan), patch.object(jobs,'scan_dependencies',side_effect=scan):
            await tools.dashboard_prepare_review(token)
        jobs.require_complete(token)

    async def test_duplicate_scanner_calls_coalesce_and_no_cross_job_osv_cache(self):
        token=self.job()
        jobs.load_skill(token,'gitleaks');jobs.load_skill(token,'osv-scanner')
        with patch.object(jobs,'scan_secrets',return_value={'status':'completed','findings':[]}) as scanner:
            await asyncio.gather(*(asyncio.to_thread(jobs.run_scanner,token,'gitleaks') for _ in range(3)))
        scanner.assert_called_once()
        second=self.job();jobs.load_skill(second,'osv-scanner')
        with patch.object(jobs,'scan_dependencies',return_value={'status':'completed','findings':[]}) as osv:
            jobs.run_scanner(token,'osv-scanner');jobs.run_scanner(second,'osv-scanner')
        self.assertEqual(osv.call_count,2)

    async def test_failed_required_scan_cannot_become_a_clean_bundle(self):
        token=self.job()
        with patch.object(jobs,'scan_secrets',return_value={'status':'completed','findings':[]}), patch.object(
            jobs,'scan_dependencies',side_effect=RuntimeError('offline')
        ):
            with self.assertRaises(RuntimeError): await tools.dashboard_prepare_review(token)
        with self.assertRaises(RuntimeError): jobs.require_complete(token)

    async def test_missing_upstream_skill_never_runs_scanners_or_passes_receipts(self):
        token=self.job()
        with tempfile.TemporaryDirectory() as directory, patch.object(jobs,'SKILL_ROOT',Path(directory)), patch.object(
            jobs,'scan_secrets'
        ) as scanner:
            with self.assertRaises(FileNotFoundError):await tools.dashboard_prepare_review(token)
        scanner.assert_not_called()
        with self.assertRaises(RuntimeError):jobs.require_complete(token)

    async def test_expired_job_cleanup_does_not_mask_original_review_failure(self):
        token=self.job()
        with jobs.locked_job(token) as job:job['created']=0
        with self.assertRaises(ValueError):jobs.require_complete(token)
        jobs.delete_job(token)
        self.assertFalse((jobs.ROOT/token).exists())

    async def test_cleanup_tolerates_a_stale_directory_check_after_expiry_sweep(self):
        token=self.job();jobs.delete_job(token)
        with patch.object(Path,'is_dir',return_value=True):
            jobs.delete_job(token)

    async def test_cleanup_waits_for_inflight_scanner_receipt(self):
        token=self.job();jobs.load_skill(token,'gitleaks')
        started=threading.Event();finish=threading.Event()
        def scanner(*args):
            started.set()
            if not finish.wait(timeout=2):raise RuntimeError('test scanner did not finish')
            return {'status':'completed','findings':[]}
        with patch.object(jobs,'scan_secrets',side_effect=scanner):
            running=asyncio.create_task(asyncio.to_thread(jobs.run_scanner,token,'gitleaks'))
            self.assertTrue(await asyncio.to_thread(started.wait,1))
            cleanup=asyncio.create_task(asyncio.to_thread(jobs.delete_job,token))
            await asyncio.sleep(0.02)
            self.assertFalse(cleanup.done())
            self.assertTrue((jobs.ROOT/token/'job.json').is_file())
            finish.set();await running;await cleanup
        self.assertFalse((jobs.ROOT/token).exists())

    async def test_batch_transport_keeps_schema_and_required_receipts(self):
        import re
        import httpx
        from config import settings
        from services import llm_reviewer
        client=AsyncMock();client.__aenter__.return_value=client
        async def post(url, **kwargs):
            system=kwargs['json']['messages'][0]['content']
            token=re.search(r'job_id=([A-Za-z0-9_-]{43})',system).group(1)
            self.assertIn('First call dashboard_prepare_review',system)
            await tools.dashboard_prepare_review(token)
            return httpx.Response(200,json={'choices':[{'message':{'content':'[]'}}]},request=httpx.Request('POST',url))
        client.post.side_effect=post
        with patch.multiple(settings,LLM_BACKEND='hermes',HERMES_REQUIRE_TOOLS=True,
                            HERMES_BATCH_WORKFLOW=True,HERMES_API_KEY='test-key'), patch.object(
            llm_reviewer.httpx,'AsyncClient',return_value=client
        ), patch.object(jobs,'scan_secrets',return_value={'status':'completed','findings':[]}):
            self.assertEqual(await llm_reviewer._call_llm('Review provided source'), '[]')
        self.assertEqual(list(jobs.ROOT.glob('*/job.json')),[])

    async def test_discussion_only_loads_original_fp_check_without_scanners(self):
        token=self.job({},task='discussion')
        with patch.object(jobs,'scan_secrets') as secret,patch.object(jobs,'scan_dependencies') as osv:
            bundle=await tools.dashboard_prepare_review(token)
        self.assertEqual([s['skill'] for s in bundle['skills']],['fp-check'])
        self.assertEqual(bundle['scanners'],[])
        secret.assert_not_called();osv.assert_not_called();jobs.require_complete(token)

    async def test_large_bundle_falls_back_without_truncating_original_payloads(self):
        context={'repo':'test','source_commit':'source','files':[],'scanner_findings':[{'code':'x'*95000}]}
        token=self.job(context)
        with patch.object(jobs,'scan_secrets',return_value={'status':'completed','findings':[]}):
            bundle=await tools.dashboard_prepare_review(token)
        self.assertTrue(bundle['use_original_tools'])
        with jobs.locked_job(token) as job:self.assertEqual(job['receipts']['preparation'],'fallback')
        with self.assertRaises(RuntimeError): jobs.require_complete(token)
        original=jobs.read_context(token)
        self.assertEqual(original['scanner_findings'][0]['code'],'x'*95000)
        for name in original['required_skills']: jobs.load_skill(token,name)
        jobs.require_complete(token)

    async def test_flag_keeps_original_workflow_available(self):
        old=self.job(batch=False);new=self.job(batch=True)
        self.assertNotIn('dashboard_prepare_review',jobs.job_instructions(old))
        self.assertIn('dashboard_prepare_review',jobs.job_instructions(new))
        self.assertIn('dashboard_repo_files',jobs.job_instructions(new))

    async def test_file_batch_is_parallel_and_duplicate_paths_are_read_once(self):
        token=self.job({'repo':'test','source_commit':'source-A','files':[]})
        started=0;ready=asyncio.Event()
        async def fetch(url):
            nonlocal started
            started+=1
            if started==2: ready.set()
            await asyncio.wait_for(ready.wait(),timeout=2)
            return 'code from source-A'
        with patch.object(tools.AzureDevOpsClient,'_get_raw',new=AsyncMock(side_effect=fetch)) as get:
            result=await tools.dashboard_repo_files(token,['/a.ts','a.ts','/b.ts'])
        self.assertEqual(get.await_count,2)
        self.assertEqual(len(result['files']),2)
        self.assertTrue(all(item['commit']=='source-A' and item['found'] for item in result['files']))

    async def test_snapshot_and_same_job_cache_do_not_spend_azure_budget_twice(self):
        context={'repo':'test','source_commit':'source-A','files':[{'path':'/a.ts','src_content':'snapshot'}]}
        token=self.job(context)
        with patch.object(tools.AzureDevOpsClient,'_get_raw',new=AsyncMock(return_value='related')) as get:
            self.assertEqual((await tools.dashboard_repo_file(token,'/a.ts'))['content'],'snapshot')
            first=await tools.dashboard_repo_file(token,'/b.ts')
            second=await tools.dashboard_repo_file(token,'b.ts')
        self.assertEqual(first,second);get.assert_awaited_once()
        with jobs.locked_job(token) as job: self.assertEqual(job['receipts']['azure_reads'],1)

    async def test_cache_is_not_shared_across_commits_or_jobs(self):
        a=self.job({'repo':'test','source_commit':'source-A','files':[]})
        b=self.job({'repo':'test','source_commit':'source-B','files':[]})
        with patch.object(tools.AzureDevOpsClient,'_get_raw',new=AsyncMock(side_effect=['old','new'])) as get:
            first=await tools.dashboard_repo_file(a,'/a.ts');second=await tools.dashboard_repo_file(b,'/a.ts')
        self.assertEqual(get.await_count,2)
        self.assertEqual((first['commit'],first['content']),('source-A','old'))
        self.assertEqual((second['commit'],second['content']),('source-B','new'))

    async def test_missing_file_is_cached_but_network_failures_are_not(self):
        token=self.job({'repo':'test','source_commit':'source-A','files':[]})
        with patch.object(tools.AzureDevOpsClient,'_get_raw',new=AsyncMock(return_value=None)) as get:
            self.assertFalse((await tools.dashboard_repo_file(token,'/missing.ts'))['found'])
            await tools.dashboard_repo_file(token,'/missing.ts')
        get.assert_awaited_once()
        with patch.object(tools.AzureDevOpsClient,'_get_raw',new=AsyncMock(side_effect=[RuntimeError('offline'),'recovered'])) as get:
            with self.assertRaises(RuntimeError):await tools.dashboard_repo_file(token,'/retry.ts')
            self.assertEqual((await tools.dashboard_repo_file(token,'/retry.ts'))['content'],'recovered')
        self.assertEqual(get.await_count,2)

    async def test_batch_preserves_read_budget_and_validates_all_paths_first(self):
        token=self.job({'repo':'test','source_commit':'source-A','files':[]})
        with patch.object(tools.AzureDevOpsClient,'_get_raw',new=AsyncMock(return_value='code')) as get:
            for paths in [[],['/a.ts']*9,['/a.ts','../../etc/passwd'],['/a.ts','/.env']]:
                with self.assertRaises(ValueError):await tools.dashboard_repo_files(token,paths)
            get.assert_not_awaited()
            result=await tools.dashboard_repo_files(token,[f'/file{i}.ts' for i in range(8)])
            self.assertTrue(all(f['found'] for f in result['files']))
            blocked=await tools.dashboard_repo_files(token,['/extra.ts'])
            self.assertFalse(blocked['files'][0]['available'])
            await tools.dashboard_repo_files(token,['/file0.ts'])
        self.assertEqual(get.await_count,8)

    async def test_oversized_batch_retains_full_results_for_original_tools(self):
        token=self.job({'repo':'test','source_commit':'source-A','files':[]})
        with patch.object(tools.AzureDevOpsClient,'_get_raw',new=AsyncMock(return_value='x'*60000)) as get:
            batch=await tools.dashboard_repo_files(token,['/a.ts','/b.ts'])
            self.assertEqual(batch['use_individual_reads'],['a.ts','b.ts'])
            for path in batch['use_individual_reads']:
                self.assertEqual((await tools.dashboard_repo_file(token,path))['content'],'x'*60000)
        self.assertEqual(get.await_count,2)
