"""LLM Code Reviewer — reviews changed code with full file context.

Sends the full file for context but marks which lines changed.
LLM understands the full flow but only reports findings on changed lines.
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
    severity: str
    category: str
    file_path: str
    line_number: int
    function_name: str
    description: str
    code_snippet: str
    fix_suggestion: str
    owasp_tag: Optional[str] = None


REVIEW_PROMPT = string.Template("""คุณเป็น senior code reviewer ที่เชี่ยวชาญ NestJS, LoopBack 4, TypeScript, และ security

## กฎเหล็ก:
1. **อ่านไฟล์เต็มเพื่อเข้าใจ context** — ดูว่า function ถูกเรียกจากไหน, data flow เป็นยังไง, มี edge case อะไร
2. **comment เฉพาะบรรทัดที่มี [NEW] หรือ [CHANGED] เท่านั้น** — ห้าม comment บนบรรทัดเดิม
3. **line_number ต้องตรงกับบรรทัดที่มี [NEW] หรือ [CHANGED]** — ดูจาก L{num}: ด้านหน้า
4. ถ้าไม่พบปัญหาใน code ที่เปลี่ยน → ตอบ []

## สิ่งที่ต้องตรวจ (เฉพาะ code ที่เปลี่ยน):
- **Logic** — edge cases, null checks, missing defaults, wrong conditions
- **Error handling** — missing try/catch, swallowed errors, wrong exception type
- **Type safety** — wrong types, missing null checks, type contract violations
- **Security** — injection, SSRF, IDOR, hardcoded secrets, missing auth
- **Tests** — ถ้า code เปลี่ยนแต่ไม่มี test ใหม่ → flag

## Format ตอบ (JSON array เท่านั้น):
ข้อกำหนดสำหรับ field:
- `description`: อธิบายสั้น กระชับ เป็น Markdown ได้ แต่ห้ามใส่ code block
- `code_snippet`: ใส่เฉพาะโค้ดที่มีปัญหาแบบ raw code 1-3 บรรทัด ห้ามใส่ ``` fence
- `fix_suggestion`: เริ่มด้วยคำอธิบายสั้น 1 ประโยค แล้วถ้ามีโค้ดแก้ไขให้ขึ้นบรรทัดใหม่เป็น raw code ห้ามใส่ ``` fence

```json
[
  {
    "severity": "HIGH",
    "category": "BUG",
    "file_path": "/src/path/to/file.ts",
    "line_number": 42,
    "function_name": "methodName",
    "description": "อธิบายปัญหา + ทำไมถึงเป็นปัญหา + impact",
    "code_snippet": "โค้ดที่มีปัญหา (1-3 บรรทัด)",
    "fix_suggestion": "วิธีแก้ไข (โค้ดจริง)",
    "owasp_tag": null
  }
]
```

## PR:
**Title:** $title | **Author:** $author | **Branch:** $source_branch → $target_branch

## Files:
$files_info

## Source Code (บรรทัดที่มี [NEW] หรือ [CHANGED] คือ code ที่เพิ่ม/แก้ไข):
$code_content
""")


def _build_code_with_markers(
    src_content: str, changed_lines: Set[int], max_chars: int = 25000
) -> str:
    """Build code with [NEW]/[CHANGED] markers on changed lines."""
    lines = src_content.splitlines()
    result = []
    total = 0

    for i, line in enumerate(lines):
        line_num = i + 1
        marker = "[NEW] " if line_num in changed_lines else "       "
        numbered = f"L{line_num:4d}:{marker}{line}"
        if total + len(numbered) + 1 > max_chars:
            result.append(f"       ... ({len(lines) - i} more lines truncated)")
            break
        result.append(numbered)
        total += len(numbered) + 1

    return "\n".join(result)


async def review_pr_with_llm(
    title: str,
    author: str,
    source_branch: str,
    target_branch: str,
    files: List[Dict[str, Any]],
    changed_lines: Dict[str, Set[int]],
) -> List[LLMFinding]:
    """
    Review PR with full file context, but only report findings on changed lines.

    Args:
        files: List of dicts with path, change_type, src_content, tgt_content
        changed_lines: {file_path: set of 1-indexed line numbers that changed}
    """
    if not PROVIDERS:
        return []

    total_changed = sum(len(v) for v in changed_lines.values())
    logger.info(f"LLM review: {len(files)} files, {total_changed} changed lines")

    # Build files info
    files_info = "\n".join(
        f"- {f['path']} ({f['change_type']}) — {len(changed_lines.get(f['path'], set()))} lines changed"
        for f in files
    )

    # Build code content with [NEW]/[CHANGED] markers
    code_parts = []
    total_chars = 0
    max_chars = 28000

    for f in files:
        src = f.get("src_content", "")
        if not src:
            continue

        path = f["path"]
        n_changed = len(changed_lines.get(path, set()))

        header = f"\n{'='*60}\nFILE: {path} ({f['change_type']}) — {n_changed} changed lines\n{'='*60}\n"
        code = _build_code_with_markers(src, changed_lines.get(path, set()))
        section = header + code

        if total_chars + len(section) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 500:
                code_parts.append(section[:remaining] + "\n... (truncated)")
            break

        code_parts.append(section)
        total_chars += len(section)

    code_content = "\n".join(code_parts)

    prompt = REVIEW_PROMPT.safe_substitute(
        title=title,
        author=author,
        source_branch=source_branch,
        target_branch=target_branch,
        files_info=files_info,
        code_content=code_content,
    )

    raw_response = await _call_llm(prompt)
    if not raw_response:
        return []

    findings = _parse_findings(raw_response)

    # FILTER: only keep findings on actually changed lines
    filtered = []
    for f in findings:
        file_changed = changed_lines.get(f.file_path, set())
        if f.line_number in file_changed:
            filtered.append(f)
        else:
            logger.info(f"Filtered: {f.file_path}:{f.line_number} not in changed lines")

    logger.info(f"LLM: {len(findings)} raw → {len(filtered)} on changed lines")
    return filtered


async def _call_llm(prompt: str) -> Optional[str]:
    for provider in PROVIDERS:
        result = await _try_provider(provider, prompt)
        if result:
            return result
        logger.warning(f"Provider {provider['name']} failed, trying next...")
    logger.error("All LLM providers failed")
    return None


async def _try_provider(provider: dict, prompt: str) -> Optional[str]:
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
                "content": "คุณเป็น senior code reviewer ตอบเป็น JSON array เท่านั้น comment เฉพาะบรรทัดที่มี [NEW] หรือ [CHANGED] เท่านั้น",
            },
            {"role": "user", "content": prompt},
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
    json_match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not json_match:
        logger.warning(f"No JSON array in LLM response")
        return []

    try:
        items = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return []

    findings = []
    for item in items:
        try:
            findings.append(
                LLMFinding(
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
            )
        except Exception as e:
            logger.warning(f"Parse error: {e}")

    return [f for f in findings if f.file_path and f.line_number > 0]
