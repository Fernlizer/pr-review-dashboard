"""Bounded scanner adapters. Never execute repository code or package-manager scripts."""
import json
import os
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

LOCKFILES = {'package-lock.json', 'npm-shrinkwrap.json', 'yarn.lock', 'pnpm-lock.yaml',
             'requirements.txt', 'poetry.lock', 'uv.lock', 'Pipfile.lock', 'go.sum',
             'Cargo.lock', 'composer.lock', 'Gemfile.lock', 'packages.lock.json'}


def safe_path(value: str) -> str:
    if not isinstance(value, str) or '\\' in value or '\x00' in value:
        raise ValueError('Invalid file path')
    path = PurePosixPath(value.lstrip('/'))
    if not path.parts or any(p in {'.', '..'} for p in path.parts):
        raise ValueError('Invalid file path')
    return str(path)


def dependency_files(files: list[dict]) -> list[str]:
    return [f['path'] for f in files if PurePosixPath(f['path']).name in LOCKFILES]


def _write_snapshot(root: Path, files: list[dict], side: str, dependencies_only=False):
    for item in files:
        if dependencies_only and PurePosixPath(item['path']).name not in LOCKFILES:
            continue
        content = item.get(side)
        if not content:
            continue
        path = root / safe_path(item['path'])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')


def _run(command: list[str], root: Path, report: Path) -> dict | list:
    env = {'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin'),
           'HOME': str(root), 'TMPDIR': str(root), 'NO_COLOR': '1'}
    try:
        done = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=90)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError('Scanner unavailable or timed out') from None
    # 0 = clean; 1 = findings. Any other code is a scan failure, not a clean result.
    if done.returncode not in (0, 1) or not report.is_file() or report.stat().st_size > 10_000_000:
        raise RuntimeError('Scanner failed to produce a valid bounded report')
    try:
        return json.loads(report.read_text())
    except (ValueError, UnicodeError):
        raise RuntimeError('Scanner returned invalid JSON') from None


def scan_secrets(files: list[dict], changed_lines: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix='pr-gitleaks-') as temp:
        root = Path(temp); src = root / 'source'; src.mkdir()
        _write_snapshot(src, files, 'src_content')
        report = root / 'report.json'
        rows = _run(['gitleaks', 'dir', str(src), '--config', '/app/scanner-config/gitleaks.toml',
                     '--no-banner', '--redact=100', '--report-format=json', '--report-path', str(report)], root, report)
        if not isinstance(rows, list):
            raise RuntimeError('Invalid Gitleaks report')
        findings = []
        for item in rows:
            raw_path = Path(item['File'])
            try:
                relative = raw_path.relative_to(src).as_posix() if raw_path.is_absolute() else safe_path(str(raw_path))
            except ValueError:
                raise RuntimeError('Scanner reported an out-of-snapshot path') from None
            path = '/' + relative
            start, end = int(item['StartLine']), int(item['EndLine'])
            changed = changed_lines.get(path, changed_lines.get(relative, []))
            if not any(start <= line <= end for line in changed):
                continue
            # Never return Secret, Match, raw Line, or report paths to the model/logs.
            findings.append({'file_path': path, 'line_number': start,
                             'rule': item['RuleID'], 'description': 'Potential exposed secret (value redacted)',
                             'severity': 'HIGH', 'code_snippet': '<redacted secret>'})
        return {'scanner': 'gitleaks', 'version': '8.30.1', 'status': 'completed',
                'coverage': 'Changed files, findings intersecting changed lines only', 'findings': findings[:100],
                'truncated': len(findings) > 100}


def _osv_scan(root: Path) -> dict:
    report = root.parent / (root.name + '-report.json')
    data = _run(['osv-scanner', 'scan', 'source', '--recursive', '--format=json',
                 '--output=' + str(report), str(root)], root.parent, report)
    if not isinstance(data, dict) or not isinstance(data.get('results', []), list):
        raise RuntimeError('Invalid OSV report')
    return data


def _osv_findings(data: dict, root: Path) -> dict:
    findings = {}
    for result in data.get('results', []):
        path = Path(result['source']['path'])
        if path.is_absolute():
            try:
                relative = path.relative_to(root).as_posix()
            except ValueError:
                raise RuntimeError('OSV reported an out-of-snapshot path') from None
        else:
            relative = safe_path(str(path))
        for entry in result.get('packages', []):
            package = entry.get('package', {})
            for vuln in entry.get('vulnerabilities', []):
                canonical = min([vuln['id'], *vuln.get('aliases', [])])
                key = (relative, package.get('ecosystem'), package.get('name'), canonical)
                findings[key] = {'file_path': '/' + relative, 'package': package.get('name'),
                    'version': package.get('version'), 'ecosystem': package.get('ecosystem'),
                    'vulnerability_id': vuln['id'], 'summary': vuln.get('summary', '')[:1000],
                    'aliases': vuln.get('aliases', []), 'severity': vuln.get('database_specific', {}).get('severity'),
                    'url': 'https://osv.dev/vulnerability/' + vuln['id']}
    return findings


def scan_dependencies(files: list[dict]) -> dict:
    selected = [f for f in files if PurePosixPath(f['path']).name in LOCKFILES]
    if not selected:
        return {'scanner': 'osv-scanner', 'status': 'not_applicable', 'findings': []}
    with tempfile.TemporaryDirectory(prefix='pr-osv-') as temp:
        root = Path(temp); base = root / 'base'; head = root / 'head'
        base.mkdir(); head.mkdir()
        _write_snapshot(base, selected, 'tgt_content', True)
        _write_snapshot(head, selected, 'src_content', True)
        before = _osv_findings(_osv_scan(base), base) if any(base.rglob('*')) else {}
        after = _osv_findings(_osv_scan(head), head) if any(head.rglob('*')) else {}
        introduced = [value for key, value in after.items() if key not in before]
        return {'scanner': 'osv-scanner', 'version': '2.7.0', 'status': 'completed',
                'coverage': 'Base/head comparison of supplied changed dependency files, not the full repository',
                'baseline_count': len(before), 'head_count': len(after),
                'findings': introduced[:100], 'truncated': len(introduced) > 100}
