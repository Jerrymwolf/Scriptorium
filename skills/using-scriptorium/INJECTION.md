# Scriptorium — discipline contract

You are running inside Scriptorium, a literature-review plugin. Three disciplines are non-negotiable for any literature-review work in this session.

## The three disciplines

1. **Evidence-first claims.** Every sentence in `synthesis.md` must carry an inline citation `[paper_id:locator]` that maps to a row in `evidence.jsonl`. Sentences without a backing evidence row are flagged or stripped — never softened, never left uncited.
2. **PRISMA audit trail.** Every search, screen, extraction, and reasoning decision appends one row to `audit.jsonl` (and the human-readable `audit.md`). Append only — never overwrite. The trail must reconstruct end-to-end.
3. **Contradiction surfacing.** When evidence on the same concept disagrees, name the disagreement explicitly with both citations. Do not average findings into a single bland claim and do not silently drop the dissenting source.

## Red flags — do NOT

- Do NOT write a synthesis sentence without a `[paper_id:locator]` cite that resolves to `evidence.jsonl`.
- Do NOT skip the audit-trail append for any decision (search query, inclusion/exclusion, extraction, reasoning step).
- Do NOT overwrite or rewrite past audit rows; the trail is append-only.
- Do NOT paper over disagreement between sources by softening, averaging, or omitting the dissenter.
- Do NOT bypass `using-scriptorium` — fire it first so the runtime is probed and the right phase skill is dispatched.

## Before you do any literature-review work

Fire the `using-scriptorium` skill first. It owns the runtime probe (Claude Code vs Cowork), the state-adapter mapping, and the routing to the phase-appropriate `lit-*` skill. Do not inline that probe here; this file only sets the discipline contract.
