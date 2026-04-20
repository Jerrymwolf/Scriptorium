---
name: lit-audit-trail
description: Use when the user asks for the audit trail, PRISMA flow, or a record of what happened during the review. Reads the append-only audit log and renders it as a PRISMA-flavored summary.
---

# Literature Audit Trail

The audit log is the single source of truth for reconstructing what happened. Every phase writes one entry per meaningful action; nothing is overwritten.

## Phases covered

- `search` — every query against every source, with `n_results` returned
- `screening` — every batch rule application, with kept/dropped counts
- `extraction` — every full-text resolution, with the cascade source that won
- `synthesis` — verify runs, with unsupported/missing counts
- `contradiction-check` — concept-level pair counts
- `publishing` — NotebookLM Studio artifact generations (from `lit-publishing`)

## Workflow — CC

```bash
scriptorium audit read
```

Prints the entire JSONL log, newest last. Human-readable companion is `audit.md` in the review dir.

## Workflow — Cowork

Read the `audit-jsonl` note/file/child-page from the state adapter (see `using-scriptorium` for the mapping). The note contains one JSON line per action.

## Rendering a PRISMA-flavored summary

From the log, build a summary with:

1. **Identification.** Count of papers returned by source, across all `search` actions.
2. **Screening.** Sum of `kept` and `dropped` across all `screening` actions.
3. **Eligibility.** Count of papers that reached the `extraction` phase with a full-text source (anything but `abstract_only`).
4. **Included.** Count of papers that have at least one evidence row.
5. **Contradictions.** Number of concepts with a positive/negative pair.

Present this as a short numbered list — it is the skeleton of a PRISMA 2020 flow diagram. The user can turn it into a figure for the thesis.

## Appending entries from other skills

Every lit-* skill appends its own entries; this skill is read-focused. If the user asks "log this", call `scriptorium audit append --phase <phase> --action <verb.noun> --details '{...}'` in CC, or write to the state adapter in Cowork.
