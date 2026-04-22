---
description: Generate a NotebookLM mind map for a completed review.
argument-hint: <review-dir>
---

Run:

```bash
scriptorium publish --review-dir {{ARGUMENTS}} --generate mindmap
```

Behind the scenes this calls `nlm mindmap create <notebook_id>`. See the
`publishing-to-notebooklm` skill for preconditions, the Cowork degradation
block, and audit semantics.
