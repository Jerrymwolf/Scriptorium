---
name: lit-screening
description: Use after lit-searching when the user wants to apply inclusion/exclusion criteria (year range, language, must-include/exclude keywords) to the corpus. Marks papers kept or dropped with a reason and records the decision in the audit trail.
---

# Literature Screening

**Defensive fallback (fire `using-scriptorium` first):** If the three-discipline preamble (Evidence-first claims / PRISMA audit trail / Contradiction surfacing) is not already loaded for this session, invoke `using-scriptorium` before continuing. Primary injection runs via the Claude Code `SessionStart` hook and the Cowork MCP `instructions` field — this fallback covers the rare case where neither fired.

Input: `corpus.jsonl` with every row at status `candidate`. Output: same file with each row at `kept` or `dropped`, plus a `reason` field. The audit trail captures the batch decision.

## Criteria vocabulary (both runtimes)

All five criteria are optional. Any present criterion that fails for a given paper drops it.

- `year_min` — int; drops `year < year_min`
- `year_max` — int; drops `year > year_max`
- `languages` — list of ISO codes; drops papers whose `raw.language` is not in the list
- `must_include` — list of keywords (case-insensitive); drops papers whose title+abstract do not contain ALL listed keywords
- `must_exclude` — list of keywords; drops papers whose title+abstract contain ANY listed keyword

Order of evaluation is fixed: year → language → must_include → must_exclude. The first failing criterion sets `reason`.

## Workflow — CC path

1. Confirm the criteria with the user (print the JSON they imply).
2. Run one batch call:

```bash
scriptorium screen \
  --year-min 2015 --year-max 2026 \
  --language en \
  --must-include caffeine --must-include "working memory" \
  --must-exclude rats
```

3. The CLI prints `{"kept": N, "dropped": M}`. Report that to the user.
4. Append an audit entry:

```bash
scriptorium audit append --phase screening --action rule.apply \
  --details '{"year_min":2015,"year_max":2026,"languages":["en"],"kept":N,"dropped":M}'
```

## Workflow — Cowork path

⚠ manual screening: no `scriptorium screen` CLI in Cowork — you are the screener, evaluating each row in-prose against the criteria. What is lost: the batch idempotency and exact `{"kept": N, "dropped": M}` counts the CLI emits; the deterministic order-of-evaluation guarantee depends on you applying year → language → must_include → must_exclude in that order on every row. Slow down and apply the criteria mechanically.

1. Confirm the criteria with the user.
2. Read the `corpus` note/page from the state adapter.
3. For each row, evaluate the criteria in-prose (you are the screener). Update `status` and `reason` inline.
4. Write the updated corpus back to the adapter.
5. Append an `audit` entry with the same shape as the CC branch.

## Edge cases

- Missing `year` → fails `year_min`/`year_max` if those criteria are set. Record `reason = "year missing"`.
- Missing `abstract` → only title is searched for keywords. If `must_include` is set and title alone doesn't contain it, the paper drops. Flag that in the audit details so the user can revisit.
- Duplicate papers (same DOI) are already deduped in search; don't re-dedupe here.

## Reversibility

Screening is reversible — `set_status(paper_id, "candidate", reason=None)` restores a row. If the user wants to re-screen with different criteria, drop them all back to `candidate` first, then re-run.

## Red flags — do NOT

- Do NOT drop a paper without setting `reason` to the failing criterion. A `dropped` row with no `reason` is invisible to the audit trail.
- Do NOT re-screen a corpus that already has `kept`/`dropped` rows without first resetting them to `candidate`. Re-running over a partially-screened corpus produces silent inconsistency.
- Do NOT skip the `scriptorium audit append --phase screening` row (CC) or the equivalent `audit` note append (Cowork). Screening with no audit row is a PRISMA violation.
- Do NOT override an exclusion criterion silently to keep a paper you like. Either change the criteria explicitly (and re-run) or accept the drop.
- Do NOT re-evaluate criteria in a different order than year → language → must_include → must_exclude. The `reason` field depends on first-failing-criterion semantics.

## Hand-off

After reporting kept/dropped counts, ask: "Proceed to full-text extraction on the N kept papers?" Hand off to `lit-extracting`.
