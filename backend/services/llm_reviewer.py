"""LLM Code Reviewer — uses LLM for deep code analysis on DIFF only.

Reviews only the changed code (diff), not the entire file.
Posts inline comments only on lines that were actually changed.
"""

import json
import logging
import os
import re
import string
import difflib
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# OpenAI-compatible API endpoints (auto-detect available provider)
PROVIDERS = [
    {
        "name": "maxplus",
        "base_url": "https://api.maxplus-ai.cc/v1",
        "api_key": "ccsk-11a086ba17de989739cdf4e695452d9e9ecdcea1655d17affbfb4b0213831020",
        "model": "gpt-5.5",
    },
    {
        "name": "xiaomi",
        "base_url": "https://platform.xiaomimimo.com/v1",
        "api_key": os.environ.get("XIAOMI_API_KEY", "tp-sn9z655zroqlf64l910se8hom8gxo9kyrs6zk68c461v0pdp"),
        "model": "MiMo",
    },
    {
        "name": "ollama",
        "base_url": "http://host.docker.internal:11434/v1",
        "api_key": "no-key-required",
        "model": "qwen3:8b",
    },
]


@dataclass
class LLMFinding:
    severity: str          # HIGH, MEDIUM, LOW
    category: str          # BUG, Security, Issue, Suggestion, Test, Architecture
    file_path: str         # /src/modules/...
    line_number: int       # exact line in the NEW file
    function_name: str     # method/function name
    description: str       # detailed explanation
    code_snippet: str      # the problematic code
    fix_suggestion: str    # how to fix it
    owasp_tag: Optional[str] = None


REVIEW_PROMPT = string.Template("""คุณเป็น senior code reviewer ที่เชี่ยวชาญ NestJS, LoopBack 4, TypeScript, และ security

## สิ่งสำคัญ: ตรวจเฉพาะ CODE ที่เปลี่ยน (บรรทัดที่ขึ้นต้นด้วย +) เท่านั้น
- ห้าม comment บนบรรทัดที่ไม่ได้เปลี่ยน
- ห้าม comment บน code เดิมที่มีอยู่ก่อนแล้ว
- line_number ต้องตรงกับบรรทัดในไฟล์ใหม่ (ดูจาก L{line}: ด้านหน้า)

## สิ่งที่ต้องตรวจ (เฉพาะ code ที่เปลี่ยน):
1. **Logic correctness** — edge cases, null checks, missing defaults
2. **Error handling** — missing try/catch, swallowed errors
3. **Type safety** — wrong types, missing null checks
4. **Security** — injection, SSRF, IDOR, hardcoded secrets
5. **Missing tests** — ถ้า code เปลี่ยนแต่ไม่มี test ใหม่

## ข้อจำกัด:
- ตอบเป็น JSON array เท่านั้น ไม่มีข้อความอื่น
- ถ้าไม่พบปัญหาใน code ที่เปลี่ยน ตอบ []
- line_number ต้องเป็นบรรทัดที่มี + (บรรทัดที่เพิ่มเข้ามา)
- ข้าม finding ที่ไม่สำคัญ (formatting, trivial naming, import order)

## Format:
```json
[
  {
    "severity": "HIGH",
    "category": "BUG",
    "file_path": "/src/modules/example/service.ts",
    "line_number": 42,
    "function_name": "methodName",
    "description": "อธิบายปัญหาอย่างละเอียด",
    "code_snippet": "โค้ดที่มีปัญหา",
    "fix_suggestion": "วิธีแก้ไข",
    "owasp_tag": null
  }
]
```

## PR Information:
**Title:** $title
**Author:** $author
**Branch:** $source_branch → $target_branch

## Changed Files:
$files_info

## Diff (เฉพาะ code ที่เปลี่ยน):
$diff_content
""")


async def review_pr_with_llm(
    title: str,
    author: str,
    source_branch: str,
    target_branch: str,
    files: List[Dict[str, Any]],
    changed_lines: Dict[str, Set[int]],
) -> List[LLMFinding]:
    """
    Send PR diff to LLM for deep analysis.
    Only reviews changed code and returns findings on changed lines only.

    Args:
        changed_lines: Dict of {file_path: set of line numbers that were changed}
    """
    if not PROVIDERS:
        logger.warning("No LLM providers configured, skipping LLM review")
        return []

    logger.info(f"LLM review: {len(files)} files, {sum(len(v) for v in changed_lines.values())} changed lines")

    # Build files info summary
    files_info_parts = []
    for f in files:
        path = f['path']
        n_changed = len(changed_lines.get(path, set()))
        files_info_parts.append(f"- {path} ({f['change_type']}) — {n_changed} lines changed")
    files_info = "\n".join(files_info_parts)

    # Build diff content (not full file — just the diff)
    diff_parts = []
    total_chars = 0
    max_chars = 25000

    for f in files:
        src = f.get("src_content", "")
        tgt = f.get("tgt_content", "")
        path = f['path']

        if not src:
            continue

        # Generate diff with line numbers
        header = f"\n{'='*60}\nFILE: {path} ({f['change_type']})\nChanged lines: {sorted(changed_lines.get(path, set()))[:20]}\n{'='*60}\n"

        if tgt:
            # Generate unified diff
            diff_lines = list(difflib.unified_diff(
                tgt.splitlines(keepends=True),
                src.splitlines(keepends=True),
                fromfile=f"a{path}",
                tofile=f"b{path}",
                lineterm="",
            ))
            # Add line numbers to new file lines
            numbered_diff = []
            new_line = 0
            for line in diff_lines:
                if line.startswith("+") and not line.startswith("+++"):
                    new_line += 1
                    numbered_diff.append(f"L{new_line}: {line}")
                elif line.startswith("-") and not line.startswith("---"):
                    numbered_diff.append(f"     {line}")
                elif line.startswith("@@"):
                    # Parse hunk header to get line numbers
                    numbered_diff.append(f"     {line}")
                else:
                    new_line += 1
                    numbered_diff.append(f"L{new_line}: {line}")
            diff_text = "\n".join(numbered_diff)
        else:
            # New file — show with line numbers
            lines = src.splitlines()
            diff_text = "\n".join(f"L{i+1}: +{line}" for i, line in enumerate(lines))

        section = header + diff_text

        if total_chars + len(section) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 500:
                diff_parts.append(section[:remaining] + "\n... (truncated)")
            break

        diff_parts.append(section)
        total_chars += len(section)

    diff_content = "\n".join(diff_parts)

    prompt = REVIEW_PROMPT.safe_substitute(
        title=title,
        author=author,
        source_branch=source_branch,
        target_branch=target_branch,
        files_info=files_info,
        diff_content=diff_content,
    )

    # Call LLM
    raw_response = await _call_llm(prompt)
    if not raw_response:
        return []

    # Parse findings
    findings = _parse_findings(raw_response)

    # FILTER: only keep findings on lines that were actually changed
    filtered = []
    for f in findings:
        file_changed_lines = changed_lines.get(f.file_path, set())
        if f.line_number in file_changed_lines:
            filtered.append(f)
        else:
            logger.info(f"Filtered out finding on unchanged line {f.file_path}:{f.line_number}")

    logger.info(f"LLM review: {len(findings)} raw → {len(filtered)} after filtering to changed lines")
    return filtered


async def _call_llm(prompt: str) -> Optional[str]:
    """Call LLM API with fallback across multiple providers."""
    for provider in PROVIDERS:
        result = await _try_provider(provider, prompt)
        if result:
            return result
        logger.warning(f"Provider {provider['name']} failed, trying next...")
    logger.error("All LLM providers failed")
    return None


async def _try_provider(provider: dict, prompt: str) -> Optional[str]:
    """Try a single LLM provider."""
    url = f"{provider['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {provider['api_key']}",
        "Content-Type": "application/json",
    }
    body = {
        "model": provider["model"],
        "messages": [
            {
                "role": "system",
                "content": "คุณเป็น senior code reviewer ตอบเป็น JSON array เท่านั้น ไม่มีข้อความอื่น ตรวจเฉพาะ code ที่เปลี่ยน (บรรทัด +) เท่านั้น"
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.1,
        "max_tokens": 4000,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            logger.info(f"Calling LLM: {provider['name']} ({provider['model']})")
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                logger.warning(f"LLM {provider['name']} returned {resp.status_code}")
                return None
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"LLM {provider['name']} responded ({len(content)} chars)")
            return content
        except Exception as e:
            logger.warning(f"LLM {provider['name']} error: {e}")
            return None


def _parse_findings(raw: str) -> List[LLMFinding]:
    """Parse LLM response into structured findings."""
    json_match = re.search(r'\[.*\]', raw, re.DOTALL)
    if not json_match:
        logger.warning(f"No JSON array found in LLM response: {raw[:200]}")
        return []

    try:
        items = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON: {e}")
        return []

    findings = []
    for item in items:
        try:
            finding = LLMFinding(
                severity=item.get("severity", "MEDIUM").upper(),
                category=item.get("category", "Issue"),
                file_path=item.get("file_path", ""),
                line_number=int(item.get("line_number", 0)),
                function_name=item.get("function_name", ""),
                description=item.get("description", ""),
                code_snippet=item.get("code_snippet", ""),
                fix_suggestion=item.get("fix_suggestion", ""),
                owasp_tag=item.get("owasp_tag"),
            )
            if finding.file_path and finding.line_number > 0:
                findings.append(finding)
        except Exception as e:
            logger.warning(f"Failed to parse finding: {e}")

    return findings
