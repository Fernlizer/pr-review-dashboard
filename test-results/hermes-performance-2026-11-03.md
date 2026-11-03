# Hermes latency experiment — 2026-11-03

Deployment decision: **keep `HERMES_BATCH_WORKFLOW=false`**. End-to-end speed and
quality parity have not been established. No timeout, model, scanner rules, required
skills, response validation, or Azure comment policy was relaxed.

The implementation adds optional full-evidence preparation, related-file batching,
per-job pinned-source reuse, independent scanner execution, and changed-line-first
initial excerpts. Original individual tools and initial-renderer fallback remain.
Tests: 78 backend unit/integration tests passed in the final image. These validate
contracts, concurrency, cache isolation and evidence receipts, not model accuracy.

A private frozen 24-file PR snapshot contained 210 changed lines. Initial prompt
coverage increased from 19 to 210 changed-line markers (31,887 to 28,032 characters).
This measures prompt inclusion only, not finding quality or end-to-end improvement.

Shadow runs invoked the reviewer without DB writes or Azure comment posting:

| Run | Elapsed seconds | Outcome |
| --- | ---: | --- |
| Original workflow | 424.65 | Invalid response: snippet exceeded existing three-line limit |
| Per-job cache, gateway still on old tool schemas | 401.25 | Completed, four findings; not a batch-mode benchmark |
| Batch, original initial excerpt | 450.09 | Request timeout |
| Batch, focused excerpt, lazy tool discovery | 240.93 | Interrupted native session; host sleep invalidated timing |
| Batch, focused excerpt, eager schemas, host kept awake | 450.06 | Request timeout; wall time 450.07 seconds |

An additional eager-schema attempt was invalidated by host sleep and job expiry.
The final awake run called preparation in its first model turn and received the full
bundle, but still timed out. Earlier completed production reviews are not a matched
control. No percentage speedup, p95 claim, or equal-quality claim is supported.

Experimental Hermes discovery/result-budget settings were restored after testing.
The feature remains disabled pending successful representative shadow replays.
Private source fixtures and raw findings are excluded from version control.
