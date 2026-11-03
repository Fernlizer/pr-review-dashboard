"""Authenticated MCP capabilities for the dedicated Hermes PR-review profile."""
import asyncio
import hmac
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
    relative = safe_path(path)
    if relative.split('/')[-1].startswith('.env') or not relative.endswith(('.ts','.tsx','.js','.jsx','.py','.json','.yaml','.yml','.sql','.md')):
        raise ValueError('Only related source/schema/test files are allowed')
    repo, commit = await asyncio.to_thread(_metadata, job_id)
    client = AzureDevOpsClient()
    query = urlencode({'path':'/'+relative, 'versionDescriptor.version':commit,
                       'versionDescriptor.versionType':'commit', 'api-version':'7.1'})
    client.headers["Accept"] = "text/plain"
    text = await client._get_raw(f'{client.repo_base}/{repo}/items?{query}&includeContent=true')
    return {'path':'/'+relative,'commit':commit,'content':(text or '')[:60000],
            'found':text is not None,'truncated':bool(text and len(text)>60000)}


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
