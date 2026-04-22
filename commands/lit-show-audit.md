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

## v0.3 frontmatter and Publishing section

- `audit.md` now has YAML frontmatter (see §5.2). Treat the first `---`
  block as metadata, not content.
- A top-level `## Publishing` section holds every NotebookLM publish event
  (success, partial, or failure). Each event is a `### <timestamp> —
  NotebookLM` subsection with a status, destination, notebook URL, files
  attempted, files uploaded, artifact ids, and a privacy note.
- The same events appear as `publishing` rows in `audit.jsonl` for tools.
