---
name: pr-dashboard-review
description: Review code supplied by PR Review Dashboard using its established changed-line checks and exact finding fields; only for dashboard review jobs.
---

# Dashboard review checks

Use only for trusted `task=review`. Read supplied code for context, then report only
problems attributable to lines marked [NEW] or [CHANGED]. Use the exact supplied file
path and L-number. Context-only lines may explain a finding but cannot be its location.

Apply the existing review checks:
- Logic: edge cases, null/empty inputs, defaults, state and condition errors.
- Error handling: swallowed failures, wrong error types, missing handling with a concrete impact.
- Type safety: contract mismatches and unsafe assumptions supported by the supplied code.
- Security: injection, SSRF, IDOR, exposed secrets, missing authorization. Require an
  attacker-controlled source, sensitive operation, and reachable path for security claims.
- Tests: identify missing coverage for a concrete changed behavior/edge case when the
  supplied evidence supports it. Do not claim tests are globally absent from a partial input.

Apply pr-dashboard-verify before returning candidates. Do not add style preferences,
new policy categories, hypothetical architecture rewrites, or findings on unchanged code.
Do not claim cross-file/caller/history analysis unless the relevant evidence was supplied.

Return a JSON array. Every finding has exactly these fields:
{"severity":"HIGH","category":"BUG","file_path":"/src/example.ts",
"line_number":42,"function_name":"methodName","description":"ปัญหา เหตุผล และผลกระทบ",
"code_snippet":"raw source code","fix_suggestion":"คำอธิบายวิธีแก้ แล้วตามด้วย raw code เมื่อจำเป็น",
"owasp_tag":null}

severity is HIGH, MEDIUM, or LOW. Preserve existing category names (e.g. BUG, Security,
Test, Architecture, Issue) when applicable; no new response fields. line_number is a
positive integer. owasp_tag is a string or null. All other fields are strings.
description is concise Markdown prose without code fences. code_snippet is raw code
on 1-3 lines. fix_suggestion starts with one explanation sentence, optionally followed
by raw code on new lines. Never include triple-backtick fences inside any field:
the existing dashboard formatter inserts language-specific code blocks and dedup markers.
