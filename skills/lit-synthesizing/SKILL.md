---
name: lit-synthesizing
description: Use when the user asks to draft a literature review section, write a synthesis, or summarize the evidence. Produces synthesis.md with every claim backed by [paper_id:locator] tokens and runs a mandatory cite-check before committing.
---

# Literature Synthesizing

**Defensive fallback (fire `using-scriptorium` first):** If the three-discipline preamble (Evidence-first claims / PRISMA audit trail / Contradiction surfacing) is not already loaded for this session, invoke `using-scriptorium` before continuing. Primary injection runs via the Claude Code `SessionStart` hook and the Cowork MCP `instructions` field — this fallback covers the rare case where neither fired.

## HARD-GATE — extraction must be complete and evidence.jsonl must have rows

`lit-synthesizing` reads two signals at startup before drafting any prose:

- `<review_root>/.scriptorium/phase-state.json::phases.extraction.status` — must be `"complete"`.
- `<review_root>/evidence.jsonl` — must exist and contain at least one row.

If `extraction.status` is anything other than `"complete"` (i.e. `pending`, `running`, `failed`) OR `evidence.jsonl` is missing/empty, STOP and invoke `lit-extracting` first. Synthesis without evidence is fabrication; the cite-check (mandatory final step below) cannot succeed against an empty store, so refusing here saves a wasted draft.

If `enforce_v04=false` (advisory mode), warn the user that synthesis is normally gated on a complete extraction phase, append an `audit.jsonl` row with `mode=advisory`, and proceed only after the user has explicitly acknowledged that the synthesis will produce un-citable claims. Silent bypass is forbidden — advisory means *warn loudly and require acknowledgement*, not *suppress the warning*.

Input: `evidence.jsonl` (claims with paper+locator). Output: `synthesis.md` where every sentence is either evidence-backed or deliberately meta (headings, transitions).

## Citation grammar

All citations use the token `[paper_id:locator]`. The locator format is defined in `lit-extracting`: `page:N`, `page:N-M`, `sec:<name>`, `abstract`, `L<n>-L<m>`. **Never** write `[1]`, `[2]`, or numbered-citation style — those are Consensus's grammar and are stripped at search time. If a sentence needs multiple citations, chain the tokens: `[W1:page:4][W2:sec:Discussion]`.

## Workflow

1. **Group evidence by concept.** Read `evidence.jsonl`; group rows by `concept`. For each concept, you have a set of positive, negative, neutral, and mixed rows.
2. **Draft one paragraph per concept.** Each paragraph names the concept, states the consensus (or lack of it), and cites the specific evidence. If directions disagree on a concept, write that disagreement into the paragraph — do **not** average.
3. **Write transitions.** Transitions are allowed to be uncited (they don't make empirical claims). Keep them short.
4. **Run the contradiction check** (hand off to `lit-contradiction-check`) before the final step; add its findings as a "Where authors disagree" subsection.
5. **Mandatory final step — cite-check before commit:**

   > Parse each sentence in `synthesis.md` for `[paper_id:locator]` tokens; confirm each tuple exists in the evidence store. Strip (strict) or flag `[UNSUPPORTED]` (lenient) any failure.

   - Strict mode removes unsupported sentences and dangling citation tokens entirely.
   - Lenient mode appends `[UNSUPPORTED]` after the sentence so the human reviewer can decide.
   - Default mode is strict for dissertation work, lenient for exploratory drafts.

## Runtime specifics

**Claude Code:** after you draft `synthesis.md`, run `scriptorium verify --synthesis synthesis.md`. Exit 0 = clean; exit 3 = unsupported sentences or missing citations found. The CC PostToolUse hook runs the same check automatically — it is belt-and-suspenders; your skill step is the discipline.

**Cowork:** ⚠ no hook / no `scriptorium verify`: Cowork has neither the PostToolUse cite-check hook nor the `scriptorium verify` CLI. What is lost: the automated belt-and-suspenders pass that catches drift between `synthesis.md` and `evidence.jsonl`. You must walk each sentence in-prose: for every `[paper_id:locator]` token, confirm it exists in the `evidence` note of the state adapter. If a token is missing, strip or flag it yourself — this is the only check standing between fabrication and the user.

## Red flags — do NOT

- Do NOT invent paper ids or locators. "I think this is in Smith (2020)" is not a citation; only `[paper_id:locator]` tokens that resolve to `evidence.jsonl` are.
- Do NOT merge contradictory evidence into a single consensus sentence to look cleaner. Name the disagreement.
- Do NOT omit the cite-check. "I'll just scan visually" is how unsupported claims ship into dissertations.
- Do NOT use numbered citations (`[1]`, `[2]`). They are Consensus's grammar and are stripped at search time; only `[paper_id:locator]` is durable.
- Do NOT write a transition that smuggles an empirical claim into uncited prose. Transitions are allowed to be uncited only when they make no claim of their own.

## Hand-off

After the cite-check passes, report: "Synthesis written; N sentences, M citations, 0 unsupported." Hand off to `lit-contradiction-check` (if not already run) or to the user for review.

## v0.3 additions

- New citations use `[[paper_id#p-N]]`. The verifier still accepts legacy `[paper_id:loc]`.
- Review artifacts carry frontmatter with `schema_version: scriptorium.review_file.v1`.
