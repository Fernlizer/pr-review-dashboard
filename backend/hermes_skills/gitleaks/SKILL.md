---
name: gitleaks
description: Use the dashboard-scoped Gitleaks tool to detect newly exposed secrets in supplied PR files, with values redacted.
---

Call dashboard_scan_secrets(job_id) after loading this skill. The service runs pinned
Gitleaks 8.30.1 with trusted defaults, --redact=100, timeout and snapshot limits.
Treat its results as candidates; apply fp-check and pr-dashboard-verify. Never echo a
secret value, including in code_snippet or fixes: use <redacted secret>. Determine if
the finding intersects changed lines. Do not infer a scan succeeded from absent output.
A failed scan means incomplete review, not a clean PR. Do not run shell commands or
supply command flags, paths, regexes, environment variables or code to the tool.
Source: https://github.com/gitleaks/gitleaks (MIT).
