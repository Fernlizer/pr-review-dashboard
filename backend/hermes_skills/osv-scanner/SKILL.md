---
name: osv-scanner
description: Use the dashboard-scoped OSV-Scanner tool when a supported dependency lockfile changes, comparing base/head for new known vulnerabilities.
---

Call dashboard_scan_dependencies(job_id) when the trusted job lists this skill as
required. The service runs pinned OSV-Scanner 2.7.0 on supported supplied dependency
files at base and head, then returns newly introduced vulnerability/package pairs.
Do not report baseline-only vulnerabilities as new. Do not invent severity or fixes:
use the returned vulnerability identifiers, versions and supplied lockfile/diff evidence.
Apply fp-check and pr-dashboard-verify to assess reachability and guards, but distinguish
known vulnerable dependency exposure from proof of exploitable runtime behavior.
If no changed supported dependency file exists the workflow does not select this skill.
Never run npm/pip install, package scripts, osv fix, untrusted registry commands, shell,
or modify a lockfile. A scan/network/parser failure is incomplete, not a clean result.
Source: https://google.github.io/osv-scanner/usage/ (Google, Apache-2.0).
