---
name: lit-contradiction-check
description: Use when the user asks where papers disagree, wants to surface contradictions, or is preparing a "limits of the evidence" section. Groups evidence by concept and reports positive vs negative camps explicitly instead of averaging.
---

# Literature Contradiction Check

Scriptorium refuses to average contradictory findings into a bland consensus sentence. When evidence on the same `concept` points in different directions, name the disagreement — **named camps**, not "some researchers find X while others find Y."

## Workflow — CC

```bash
scriptorium contradictions
```

Prints a JSON list of `{concept, a, b}` objects where `a.direction == "positive"` and `b.direction == "negative"`. Each element is a full `EvidenceEntry`, so you have `paper_id`, `locator`, `claim`, and `quote` in hand.

## Workflow — Cowork

⚠ manual grouping: no `scriptorium contradictions` CLI in Cowork — you walk `evidence` rows by hand and pair `direction: positive` with `direction: negative` per `concept`. What is lost: the deterministic JSON list of `{concept, a, b}` pairs and the typed `EvidenceEntry` view; you must read each row and group by hand. Slow down and tabulate per-concept rather than skimming.

Read the `evidence` note/page of the state adapter. Group entries by `concept`. For each concept, list the positive rows and the negative rows. If both sides are non-empty, that concept is a contradiction.

## Named-camps template

For each contradiction, write a paragraph with this shape:

> **<Concept, in one noun phrase>.** Camp A (`[<paper_id_1>:<locator_1>]`, `[<paper_id_2>:<locator_2>]`) argues <positive direction claim>. Camp B (`[<paper_id_3>:<locator_3>]`) reports the opposite: <negative direction claim>. <One sentence on what distinguishes the two camps — methods, sample, dose, year — if the evidence supports it.>

Mixed-direction rows are treated as a third camp only if there are at least two of them; otherwise fold them into the closer camp with a note.

## What counts as a contradiction

- Same `concept` slug
- At least one `direction: positive` row and at least one `direction: negative` row
- Concepts with only neutral/mixed rows are **not** contradictions — they are noisy findings

## Audit

Append: `audit append --phase contradiction-check --action pairs.found --details '{"concept":"caffeine_wm","n_pairs":3}'` — one entry per concept with contradictions.

## Red flags — do NOT

- Do NOT average disagreement into a single consensus prose claim. Scriptorium's contradiction discipline exists to surface conflict, not to launder it into a hedge.
- Do NOT drop or omit the dissenting source from a contradiction paragraph to make the prose look cleaner. Both camps must be cited.
- Do NOT write a camp without inline `[paper_id:locator]` citations for every paper in that camp. A camp without cites is rhetoric.
- Do NOT promote a single mixed-direction row into its own camp; mixed rows fold into the closer camp with a note unless there are at least two of them.
- Do NOT skip the `audit append --phase contradiction-check` row when contradictions are found. Silent contradictions are worse than no contradictions.

## Hand-off

Insert the named-camps paragraphs into `synthesis.md` under a "Where authors disagree" heading; re-run the cite-check in `lit-synthesizing`.

## v0.3 additions

Emit citations as `[[paper_id#p-N]]`. Frontmatter mirrors synthesis.md.
