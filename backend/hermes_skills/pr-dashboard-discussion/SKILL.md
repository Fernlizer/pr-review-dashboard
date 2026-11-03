---
name: pr-dashboard-discussion
description: Assess replies to tracked PR Review Dashboard findings and draft Thai replies using its existing four-decision discussion contract.
---

# Dashboard discussion assessment

Use only for trusted task=discussion. Read the supplied original finding and ordered
thread transcript. Assess whether more information, a fix, or human review is needed.
Load fp-check through dashboard_load_skill to reassess the original security claim, then use pr-dashboard-verify to check the evidence and response. Do not rescan absent updated source.

Return only this JSON object, with exactly four fields:
{"decision":"still_open","reason":"เหตุผลสั้น ๆ ภาษาไทย",
"reply":"คำตอบเจ้าของ PR ภาษาไทยสั้น ๆ","confidence":0.8}

Allowed decisions:
- awaiting_author: request the missing information needed to assess the finding.
- still_open: the provided evidence does not address the original finding.
- ready_for_human_review: sufficient supplied evidence for the human reviewer to assess next.
- needs_human_review: high risk, policy questions, uncertainty, or insufficient evidence.
confidence is a finite number from 0 through 1. reason and reply are nonempty strings.
Do not add findings-array fields, reports, explanations outside JSON, or code fences.
Do not say the PR is approved, approve/vote, or close/resolve a thread.

Return only the reply body; dashboard adds its existing
"🤖 **AI discussion summary (human approval required)**" prefix and sends the reply.
Do not post directly, change the prefix, or invent Azure thread identifiers. Existing
application eligibility rules (active PR, assigned human reviewer, no positive human
approval vote, only newly tracked threads and new author replies) remain unchanged.
