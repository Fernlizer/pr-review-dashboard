"""Authenticated MCP capabilities for the dedicated Hermes PR-review profile."""
import asyncio
import hmac
import json
import httpx
from urllib.parse import urlencode

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.responses import JSONResponse

from config import settings
from services import hermes_jobs
from services.azure_client import AzureDevOpsClient
from services.pr_scanner_tools import safe_path

mcp = FastMCP('PR Review Dashboard', stateless_http=True, json_response=True, streamable_http_path='/')
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)


@mcp.tool(annotations=READ_ONLY)
async def dashboard_load_skill(job_id: str, name: str, reference: str = '') -> dict:
    """Load an applicable, pinned skill and its core methodology. Optional reference is relative to that skill."""
    return await asyncio.to_thread(hermes_jobs.load_skill, job_id, name, reference)


@mcp.tool(annotations=READ_ONLY)
async def dashboard_context(job_id: str, path: str = '', side: str = 'head') -> dict:
    """Read this dashboard job's changed-file inventory/diffs or a supplied base/head file. No arbitrary filesystem access."""
    return await asyncio.to_thread(hermes_jobs.read_context, job_id, path, side)


@mcp.tool(annotations=READ_ONLY)
async def dashboard_scan_secrets(job_id: str) -> dict:
    """Run Gitleaks on this job's supplied changed files; secret values are redacted and unchanged-line findings excluded."""
    return await asyncio.to_thread(hermes_jobs.run_scanner, job_id, 'gitleaks')


@mcp.tool(annotations=READ_ONLY)
async def dashboard_scan_dependencies(job_id: str) -> dict:
    """Run OSV-Scanner on changed dependency files at base/head and return newly introduced known vulnerabilities."""
    return await asyncio.to_thread(hermes_jobs.run_scanner, job_id, 'osv-scanner')


@mcp.tool(annotations=READ_ONLY)
async def dashboard_prepare_review(job_id: str) -> dict:
    """Load the full dashboard context, every required upstream skill/core reference and required scanners in one call. No checks are skipped."""
    context = await asyncio.to_thread(hermes_jobs.read_context, job_id)
    names = context['required_skills']
    skills = await asyncio.gather(*[
        asyncio.to_thread(hermes_jobs.load_skill, job_id, name) for name in names
    ], return_exceptions=True)
    for skill in skills:
        if isinstance(skill, BaseException):
            raise skill
    scanners = await asyncio.gather(*[
        asyncio.to_thread(hermes_jobs.run_scanner, job_id, name)
        for name in ('gitleaks', 'osv-scanner') if name in names
    ], return_exceptions=True)
    for scanner in scanners:
        if isinstance(scanner, BaseException):
            raise scanner
    result = {'context':context, 'skills':skills, 'scanners':scanners,
              'next_step':'Analyze supplied evidence; batch related-file reads if needed, then verify candidates before final JSON.'}
    if len(json.dumps(result, ensure_ascii=False)) > 90000:
        # Never let Hermes spill a combined payload to an unreadable local file.
        # Revert to the original calls with every full payload still available.
        await asyncio.to_thread(hermes_jobs.reset_model_reads, job_id)
        await asyncio.to_thread(hermes_jobs.mark_preparation, job_id, 'fallback')
        return {'use_original_tools':True, 'required_skills':names,
                'reason':'Full bundle exceeds the inline budget. Read dashboard_context and each dashboard_load_skill separately, then retrieve scanner results using the original tools. No evidence was truncated.'}
    await asyncio.to_thread(hermes_jobs.mark_preparation, job_id, 'bundle')
    return result


def _validate_source_path(path: str) -> str:
    relative = safe_path(path)
    if relative.split('/')[-1].startswith('.env') or not relative.endswith(('.ts','.tsx','.js','.jsx','.py','.json','.yaml','.yml','.sql','.md')):
        raise ValueError('Only related source/schema/test files are allowed')
    return relative


def _metadata(job_id: str):
    with hermes_jobs.locked_job(job_id) as job:
        context = job['context']
        if not context.get('repo') or not context.get('source_commit'):
            raise ValueError('Pinned Azure repository context is unavailable for this job')
        count = job['receipts'].get('azure_reads', 0)
        if count >= 8:
            raise ValueError('Azure evidence budget exhausted (8 reads)')
        job['receipts']['azure_reads'] = count + 1
        return context['repo'], context['source_commit']


@mcp.tool(annotations=READ_ONLY)
async def dashboard_repo_file(job_id: str, path: str) -> dict:
    """Read a related source file from the job's pinned Azure commit (8 shared Azure reads maximum)."""
    relative = _validate_source_path(path)
    cached = await asyncio.to_thread(hermes_jobs.cached_repo_file, job_id, relative)
    if cached is not None:
        return cached
    repo, commit = await asyncio.to_thread(_metadata, job_id)
    client = AzureDevOpsClient()
    query = urlencode({'path':'/'+relative, 'versionDescriptor.version':commit,
                       'versionDescriptor.versionType':'commit', 'api-version':'7.1'})
    client.headers["Accept"] = "text/plain"
    text = await client._get_raw(f'{client.repo_base}/{repo}/items?{query}&includeContent=true')
    result = {'path':'/'+relative,'commit':commit,'content':(text or '')[:60000],
              'found':text is not None,'truncated':bool(text and len(text)>60000)}
    await asyncio.to_thread(hermes_jobs.cache_repo_file, job_id, relative, result)
    return result


@mcp.tool(annotations=READ_ONLY)
async def dashboard_repo_files(job_id: str, paths: list[str]) -> dict:
    """Read up to 8 selected related source files concurrently, reusing same-job snapshot/cache results. Same pinned commit and shared Azure budget as single-file reads."""
    if not paths or len(paths) > 8:
        raise ValueError('Choose between 1 and 8 source paths')
    normalized = list(dict.fromkeys(_validate_source_path(path) for path in paths))
    semaphore = asyncio.Semaphore(4)
    async def read(path):
        async with semaphore:
            return await dashboard_repo_file(job_id, path)
    results = await asyncio.gather(*(read(path) for path in normalized), return_exceptions=True)
    result = {'files':[result if not isinstance(result, BaseException) else
                       {'path':'/'+path, 'available':False,
                        'reason':'Evidence unavailable or shared Azure read budget exhausted; do not infer file contents.'}
                       for path,result in zip(normalized,results)]}
    if len(json.dumps(result, ensure_ascii=False)) > 90000:
        return {'use_individual_reads':normalized,
                'reason':'Full batch exceeds the inline budget. Read each path with dashboard_repo_file; full results are cached in this job, with no additional Azure budget spent. No content was truncated.'}
    return result


@mcp.tool(annotations=READ_ONLY)
async def dashboard_file_history(job_id: str, path: str) -> dict:
    """Read up to five Azure commit metadata entries for a file at the job's pinned source commit; no shell/git execution."""
    relative = safe_path(path)
    repo, commit = await asyncio.to_thread(_metadata, job_id)
    client = AzureDevOpsClient()
    query = urlencode({'searchCriteria.itemPath':'/'+relative,
        'searchCriteria.itemVersion.version':commit,'searchCriteria.itemVersion.versionType':'commit',
        'searchCriteria.$top':5,'api-version':'7.1'})
    try:
        data = await client._get(f'{client.repo_base}/{repo}/commits?{query}')
    except httpx.HTTPError:
        return {'path':'/'+relative, 'available':False, 'commits':[],
                'coverage':'History unavailable for this pinned repository/commit; do not infer historical checks completed'}
    return {'path':'/'+relative,'commits':[{'commit':c.get('commitId'),'message':c.get('comment','')[:2000]}
             for c in data.get('value',[])[:5]],'coverage':'Up to five commit messages, not git blame or full caller analysis'}


class AuthenticatedMCP:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            headers = dict(scope.get('headers', []))
            expected = settings.HERMES_TOOLS_KEY
            given = headers.get(b'authorization', b'').decode('latin1')
            if not expected or not hmac.compare_digest(given, 'Bearer '+expected):
                await JSONResponse({'error':'Unauthorized'}, status_code=401)(scope, receive, send)
                return
        await self.app(scope, receive, send)


mcp_app = AuthenticatedMCP(mcp.streamable_http_app())
