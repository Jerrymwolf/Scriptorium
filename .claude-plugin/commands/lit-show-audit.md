---
description: Print the current PRISMA audit trail for this review. Runs `scriptorium audit read` and prints entries grouped by phase with key details. Usage: /lit-show-audit [--review-dir <path>].
argument-hint: "[--review-dir <path>]"
---

# /lit-show-audit

## Procedure

1. Invoke:
   ```
   scriptorium audit read
   ```
   (Add `--review-dir <path>` if the user passed it.)
2. Parse the JSONL stream (one entry per line). If empty, tell the user no audit entries exist yet.
3. Group by `phase` (search → screening → extraction → synthesis → verification → contradictions → publishing → export). Within each group, print `action` and the most important `details` keys.
4. Close with the pointer: "Full machine-readable form is at `<review-dir>/audit.jsonl`; human-readable at `<review-dir>/audit.md`."
