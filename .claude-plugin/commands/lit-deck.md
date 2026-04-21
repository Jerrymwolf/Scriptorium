---
description: Generate a NotebookLM slide deck for a completed review.
argument-hint: <review-dir>
---

Run:

```bash
scriptorium publish --review-dir {{ARGUMENTS}} --generate deck
```

User-facing "deck" maps to `nlm slides create <notebook_id>`. Upload order
and audit semantics match §9 of the design spec; see the
`publishing-to-notebooklm` skill for preconditions.
