"""Security scanner — grep-based patterns + semgrep integration."""

import json
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# --- Grep-based Security Patterns ---

SECURITY_PATTERNS: Dict[str, tuple] = {
    # --- Hardcoded Secrets (HIGH) ---
    "hardcoded_password": (
        r'(?i)(password|passwd|pwd)\s*[:=]\s*["\'][^"\']{4,}["\']',
        "HIGH", "A07:Identification and Authentication Failures",
    ),
    "hardcoded_api_key": (
        r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\'][A-Za-z0-9_\-]{10,}["\']',
        "HIGH", "A07:Identification and Authentication Failures",
    ),
    "hardcoded_token": (
        r'(?i)(token|secret|auth)\s*[:=]\s*["\'][A-Za-z0-9_\-\.]{10,}["\']',
        "HIGH", "A07:Identification and Authentication Failures",
    ),
    "hardcoded_jwt": (
        r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}',
        "HIGH", "A07:Identification and Authentication Failures",
    ),
    "aws_key": (
        r'AKIA[0-9A-Z]{16}',
        "HIGH", "A07:Identification and Authentication Failures",
    ),
    "private_key": (
        r'-----BEGIN\s+(RSA\s+)?PRIVATE KEY-----',
        "HIGH", "A02:Cryptographic Failures",
    ),
    # --- Injection (HIGH) ---
    "sql_concat": (
        r'(?i)(query|execute|raw)\s*\(\s*[`"\'].*\$\{',
        "HIGH", "A03:Injection",
    ),
    "sql_string_format": (
        r'(?i)(query|execute)\s*\(\s*["\'].*(%s|%d|\.\.\.).*["\']',
        "HIGH", "A03:Injection",
    ),
    "command_injection": (
        r'(?i)(exec|execSync|spawn|system|popen|subprocess)\s*\([^)]*\+',
        "HIGH", "A03:Injection",
    ),
    "eval_usage": (
        r'\beval\s*\(',
        "HIGH", "A03:Injection",
    ),
    "dangerous_deserialize": (
        r'(?i)(pickle\.loads|yaml\.load\s*\(|deserialize|from_json)',
        "HIGH", "A08:Software and Data Integrity Failures",
    ),
    "xxe_parser": (
        r'(?i)(XMLParser|parseString|libxml|DOMParser).*?(?:noent|resolveExternals)',
        "HIGH", "A05:Security Misconfiguration",
    ),
    # --- SSRF (HIGH) ---
    "ssrf_user_url": (
        r'(?i)(fetch|axios|request|http\.get|https\.get|urllib)\s*\([^)]*(?:req\.|params\.|query\.|body\.)',
        "HIGH", "A10:Server-Side Request Forgery",
    ),
    "ssrf_url_construct": (
        r'(?i)(fetch|axios|request)\s*\(\s*[`"\'].*\$\{.*(?:req\.|params\.)',
        "HIGH", "A10:Server-Side Request Forgery",
    ),
    # --- Path Traversal (MEDIUM) ---
    "path_traversal": (
        r'(?:readFile|readFileSync|fs\.read|open|sendFile)\s*\([^)]*\+',
        "MEDIUM", "A01:Broken Access Control",
    ),
    "path_user_input": (
        r'(?:readFile|sendFile|path\.join)\s*\([^)]*(?:req\.|params\.|query\.|body\.)',
        "MEDIUM", "A01:Broken Access Control",
    ),
    # --- Sensitive Data (MEDIUM) ---
    "password_in_log": (
        r'(?i)(console\.log|logger\.|print|log\.)\s*\([^)]*(?:password|token|secret|credential)',
        "MEDIUM", "A09:Security Logging and Monitoring Failures",
    ),
    "password_in_response": (
        r'(?i)(res\.json|res\.send|return)\s*\([^)]*(?:password|passwordHash|password_hash)',
        "MEDIUM", "A01:Broken Access Control",
    ),
    "cors_wildcard": (
        r'(?i)(Access-Control-Allow-Origin|cors)\s*[:=(]\s*["\']?\*["\']?',
        "MEDIUM", "A05:Security Misconfiguration",
    ),
    # --- Insecure Config (MEDIUM) ---
    "ssl_verify_false": (
        r'(?i)(verify\s*=\s*False|rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED.*0)',
        "MEDIUM", "A02:Cryptographic Failures",
    ),
    "debug_enabled": (
        r'(?i)(debug\s*[:=]\s*true|DEBUG\s*=\s*True)',
        "MEDIUM", "A05:Security Misconfiguration",
    ),
    # --- Mass Assignment (MEDIUM) ---
    "mass_assign": (
        r'(?i)(Object\.assign|merge|spread)\s*\([^)]*(?:req\.body|body\b)',
        "MEDIUM", "A04:Insecure Design",
    ),
    "unvalidated_body": (
        r'(?i)(create|save|update)\s*\(\s*req\.body\s*\)',
        "MEDIUM", "A04:Insecure Design",
    ),
    # --- Weak Crypto (MEDIUM) ---
    "weak_hash": (
        r'(?i)(md5|sha1)\s*\(',
        "MEDIUM", "A02:Cryptographic Failures",
    ),
    "weak_random": (
        r'(?i)(Math\.random|random\.random)\s*\(',
        "LOW", "A02:Cryptographic Failures",
    ),
    # --- HTTP (LOW) ---
    "http_not_https": (
        r'http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)',
        "LOW", "A02:Cryptographic Failures",
    ),
}


@dataclass
class SecurityFinding:
    file: str
    line: int
    pattern: str
    severity: str
    owasp: str
    code: str
    source: str  # "grep" or "semgrep"


def scan_with_grep(files_content: Dict[str, str]) -> List[SecurityFinding]:
    """Scan files using built-in grep patterns."""
    findings = []
    for filepath, content in files_content.items():
        if not content:
            continue
        lines = content.split("\n")
        for pattern_name, (regex, severity, owasp) in SECURITY_PATTERNS.items():
            for i, line in enumerate(lines):
                if re.search(regex, line):
                    findings.append(SecurityFinding(
                        file=filepath,
                        line=i + 1,
                        pattern=pattern_name,
                        severity=severity,
                        owasp=owasp,
                        code=line.strip()[:200],
                        source="grep",
                    ))
    return findings


def scan_with_semgrep(files_content: Dict[str, str]) -> List[SecurityFinding]:
    """Run semgrep on files if available. Returns empty if not installed."""
    findings = []

    # Check if semgrep is available
    try:
        subprocess.run(["semgrep", "--version"], capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.info("semgrep not available, skipping")
        return findings

    # Write files to temp dir for scanning
    with tempfile.TemporaryDirectory(prefix="pr_review_semgrep_") as tmpdir:
        for filepath, content in files_content.items():
            if not content:
                continue
            # Create nested dirs
            full_path = os.path.join(tmpdir, filepath.lstrip("/"))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

        try:
            result = subprocess.run(
                [
                    "semgrep", "scan",
                    "--config", "p/security-audit",
                    "--json",
                    "--quiet",
                    tmpdir,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                for r in data.get("results", []):
                    findings.append(SecurityFinding(
                        file=r.get("path", ""),
                        line=r.get("start", {}).get("line", 0),
                        pattern=r.get("check_id", "semgrep"),
                        severity=_semgrep_severity(r.get("extra", {}).get("severity", "WARNING")),
                        owasp=r.get("extra", {}).get("metadata", {}).get("owasp", ""),
                        code=r.get("extra", {}).get("lines", "")[:200],
                        source="semgrep",
                    ))
        except subprocess.TimeoutExpired:
            logger.warning("semgrep scan timed out")
        except Exception as e:
            logger.error(f"semgrep error: {e}")

    return findings


def _semgrep_severity(sev: str) -> str:
    mapping = {"ERROR": "HIGH", "WARNING": "MEDIUM", "INFO": "LOW"}
    return mapping.get(sev.upper(), "MEDIUM")


def run_security_scan(files_content: Dict[str, str]) -> List[SecurityFinding]:
    """Run all security scans and deduplicate."""
    grep_findings = scan_with_grep(files_content)
    semgrep_findings = scan_with_semgrep(files_content)

    all_findings = grep_findings + semgrep_findings

    # Deduplicate by file+line+pattern
    seen = set()
    deduped = []
    for f in all_findings:
        key = (f.file, f.line, f.pattern)
        if key not in seen:
            seen.add(key)
            deduped.append(f)

    # Sort: HIGH first, then MEDIUM, then LOW
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    deduped.sort(key=lambda f: (severity_order.get(f.severity, 3), f.file, f.line))

    return deduped
