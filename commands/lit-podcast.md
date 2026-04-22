---
description: Generate a NotebookLM audio overview for a completed review.
argument-hint: <review-dir>
---

Use this command after `/lit-review` finishes cite-check and writes
`overview.md`.

Run:

```bash
scriptorium publish --review-dir {{ARGUMENTS}} --generate audio
```

Behind the scenes this calls `nlm audio create <notebook_id>`. Files from
§9.4 upload order are sent to NotebookLM in this order: `overview.md`,
`synthesis.md`, `contradictions.md`, `evidence.jsonl`, and direct-child PDFs.

See `skills/publishing-to-notebooklm/SKILL.md` for full
preconditions, the Cowork degradation block, and audit semantics.
