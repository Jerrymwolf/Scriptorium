---
name: lit-screening
description: Use after lit-searching when the user wants to apply inclusion/exclusion criteria (year range, language, must-include/exclude keywords) to the corpus. Marks papers kept or dropped with a reason and records the decision in the audit trail.
---

# Literature Screening

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

## Hand-off

After reporting kept/dropped counts, ask: "Proceed to full-text extraction on the N kept papers?" Hand off to `lit-extracting`.
