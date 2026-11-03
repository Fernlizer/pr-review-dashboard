"""Replay an operator-provided frozen snapshot without DB writes or Azure comments.

Run inside the backend container: PYTHONPATH=/app python scripts/benchmark_hermes_batch.py
--snapshot /tmp/context.json --output /tmp/result.json [--batch]. Snapshot files are
private test inputs, never committed. Uses the normal Hermes backend and scanners.
"""
import argparse
import asyncio
import json
import time
from pathlib import Path

from config import settings
from services.llm_reviewer import review_pr_with_llm


async def run(args):
    snapshot=json.loads(args.snapshot.read_text())
    meta=snapshot['meta']
    settings.HERMES_BATCH_WORKFLOW=args.batch
    started=time.monotonic()
    wall_started=time.time()
    try:
        findings=await review_pr_with_llm(meta['title'],meta['author'],meta['source_branch'],
            meta['target_branch'],snapshot['files'],{p:set(lines) for p,lines in snapshot['changed_lines'].items()},
            evidence={'repo':meta['repo'],'source_commit':meta['source_commit'],'target_commit':meta['target_commit']})
        result={'status':'completed','elapsed_seconds':round(time.monotonic()-started,2),
                'findings':[vars(f) for f in findings], 'batch':args.batch}
    except (RuntimeError, ValueError, OSError) as error:
        result={'status':'failed','elapsed_seconds':round(time.monotonic()-started,2),
                'error_type':type(error).__name__,'batch':args.batch}
    result['wall_seconds']=round(time.time()-wall_started,2)
    result['clock_gap_seconds']=round(result['wall_seconds']-result['elapsed_seconds'],2)
    args.output.write_text(json.dumps(result,ensure_ascii=False))
    args.output.chmod(0o600)
    print({k:v for k,v in result.items() if k!='findings'})
    print('finding_count:',len(result.get('findings',[])))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--batch',action='store_true')
    asyncio.run(run(parser.parse_args()))
