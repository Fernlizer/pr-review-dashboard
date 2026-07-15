"""LLM Code Reviewer — uses MiMo (Xiaomi AI Studio) for deep code analysis.

Sends PR diff + source code to LLM and returns structured findings
with exact file paths, line numbers, and fix suggestions.
"""

import json
import logging
import os
import re
import string
from typing import List, Dict, Any, Optional
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
    category: str          # BUG, Security, Issue, Suggestion
    file_path: str         # /src/modules/...
    line_number: int       # exact line
    function_name: str     # method/function name
    description: str       # detailed explanation
    code_snippet: str      # the problematic code
    fix_suggestion: str    # how to fix it
    owasp_tag: Optional[str] = None  # for security findings


REVIEW_PROMPT = string.Template("""คุณเป็น senior code reviewer ที่เชี่ยวชาญ NestJS, LoopBack 4, TypeScript, และ security

ตรวจสอบ PR นี้อย่างละเอียด แล้วตอบเป็น JSON array เท่านั้น

## สิ่งที่ต้องตรวจ:
1. **Logic correctness** — edge cases, null checks, missing defaults, wrong conditions
2. **Error handling** — missing try/catch, wrong exception type, swallowed errors
3. **Type safety** — wrong types, missing null checks, unsafe casts
4. **Security** — injection, SSRF, IDOR, hardcoded secrets, missing auth checks
5. **Test coverage** — missing tests, dead code, untested branches
6. **Architecture** — wrong layer, circular deps, missing validation
7. **Performance** — N+1 queries, missing pagination, unnecessary loops

## ข้อจำกัด:
- ตอบเป็น JSON array เท่านั้น ไม่มีข้อความอื่น
- ถ้าไม่พบปัญหา ตอบ []
- ทุก finding ต้องมี file_path ที่ตรงกับไฟล์ที่ให้มา
- line_number ต้องตรงกับบรรทัดจริงในโค้ด
- ข้าม finding ที่ไม่สำคัญ (formatting, trivial naming)

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

## Source Code:
$code_content
""")


async def review_pr_with_llm(
    title: str,
    author: str,
    source_branch: str,
    target_branch: str,
    files: List[Dict[str, Any]],
) -> List[LLMFinding]:
    """
    Send PR code to LLM for deep analysis.
    Returns structured findings with exact file paths and line numbers.
    """
    if not PROVIDERS:
        logger.warning("No LLM providers configured, skipping LLM review")
        return []

    logger.info(f"LLM review: {len(files)} files, total chars: {sum(len(f.get('src_content', '')) for f in files)}")

    # Build files info summary
    files_info = "\n".join(
        f"- {f['path']} ({f['change_type']}) — {len(f.get('src_content', '').splitlines())} lines"
        for f in files
    )

    # Build code content (limit to prevent token overflow)
    code_parts = []
    total_chars = 0
    max_chars = 30000  # ~10k tokens

    for f in files:
        src = f.get("src_content", "")
        if not src:
            continue

        header = f"\n{'='*60}\nFILE: {f['path']} ({f['change_type']})\n{'='*60}\n"

        # Add line numbers to code
        lines = src.splitlines()
        numbered = "\n".join(f"L{i+1}: {line}" for i, line in enumerate(lines))
        section = header + numbered

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

    # Call LLM API
    findings_raw = await _call_llm(prompt)
    if not findings_raw:
        return []

    # Parse findings
    findings = _parse_findings(findings_raw)
    logger.info(f"LLM review found {len(findings)} findings")
    return findings


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
                "content": "คุณเป็น senior code reviewer ตอบเป็น JSON array เท่านั้น ไม่มีข้อความอื่น"
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
    # Extract JSON from response (might have markdown code blocks)
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
            # Validate
            if finding.file_path and finding.line_number > 0:
                findings.append(finding)
            else:
                logger.warning(f"Skipping invalid finding: {item}")
        except Exception as e:
            logger.warning(f"Failed to parse finding: {e}")

    return findings
