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

## Synthesis exit — reviewer gate (Claude Code)

After the in-skill cite-check passes, run the v0.4 reviewer gate. This is the final guard that promotes `phases.synthesis` from `running` to `complete`.

1. **Dispatch the cite reviewer** at `agents/lit-cite-reviewer.md` (agent name `lit-cite-reviewer`). It walks every `[paper_id:locator]` token in `synthesis.md` against `evidence.jsonl` and emits a §6.3 reviewer-output JSON payload.
2. **Dispatch the contradiction reviewer** at `agents/lit-contradiction-reviewer.md` (agent name `lit-contradiction-reviewer`). It cross-checks `synthesis.md` against `contradictions.md` (and the `contradiction-check / pairs.found` audit rows) and emits a §6.3 payload.
3. **Aggregate** by calling `scriptorium.reviewers.finalize_synthesis_phase(paths, cite_result=..., contradiction_result=...)`. This function:
   - Validates both payloads (raises `E_REVIEWER_INVALID` on a malformed shape).
   - Appends one audit row per reviewer (`reviewer.cite`, `reviewer.contradiction`).
   - Promotes `phases.synthesis` to `complete` **only when both reviewers' verdict is `pass`** AND `synthesis.md` exists. Any other combination — `fail`, `skipped`, or even `pass+pass` with `synthesis.md` missing — leaves the phase at `running` (recoverable) or raises `E_REVIEWER_ARTIFACT_MISSING`.
   - Appends one summary `synthesis.gate` audit row recording the aggregate result.

**Aggregation rule pinned**: both reviewers must verdict `pass` for `complete`. One `fail` or one `skipped` keeps the phase at `running`; the user re-drafts and re-reviews. Reviewer-fail is not terminal — `failed` is reserved for hard infrastructure failures.

**Audit row trio per gate run**: `reviewer.cite`, `reviewer.contradiction`, `synthesis.gate`. If you don't see all three in `audit.jsonl` after a finalize call, the gate did not run to completion — investigate before declaring synthesis done.

If `synthesis.md` is later edited, the next `phase_state.read()` auto-downgrades `phases.synthesis` from `complete` back to `running` (the artifact's hash no longer matches the recorded `verifier_signature`). That's intentional v0.4 architecture; re-run the reviewer gate to re-promote.

## Synthesis exit — reviewer gate (Cowork)

Cowork has no `Task` tool to dispatch CC-style sub-agents and no filesystem to host the agent prompts. The same §6.3 reviewer gate runs through the `mcp__scriptorium__finalize_synthesis_reviewers` MCP tool, with the orchestrator emitting both reviewer payloads and naming which branch produced them. The branch is selected by the `using-scriptorium` runtime probe at startup.

Two branches, named verbatim by their `scriptorium.cowork.COWORK_REVIEWER_BRANCHES` literal:

1. **`notebooklm`** (preferred). Phase 0 / T02 graded NotebookLM's text-source ingestion as `pass` — see `tests/test_layer_b_runtime_parity.py::T15_COWORK_REVIEWER_BRANCH`. The orchestrator:
   - Creates a fresh notebook (`mcp__notebooklm-mcp__notebook_create`).
   - Adds `synthesis.md` and `evidence.jsonl` as text sources via `source_add(source_type="text", ...)` — the spike's pinned source form.
   - Asks a reviewer-style query for the cite reviewer; transcribes the response into a §6.3 payload.
   - Repeats the query for the contradiction reviewer (cross-checking against `contradictions.md`).
   - Calls `mcp__scriptorium__finalize_synthesis_reviewers(review_dir=..., cite_result=..., contradiction_result=..., cowork_branch="notebooklm")`. The tool runs the same `finalize_synthesis_phase` aggregation as Claude Code, then appends a fourth audit row `cowork.reviewer_branch` with `status="success"` and `details.branch="notebooklm"`.
   - Deletes the scratch notebook (or rotates a long-lived scratch notebook between runs).

2. **`⚠ inline_degraded` (degraded path):** what is lost is the isolated reviewer context. The orchestrator emits both §6.3 payloads from its own model turn — no fresh notebook, no separate context boundary, no reviewer hash that's distinct from the drafting context. Use this branch only when NotebookLM is unavailable. The MCP tool appends `cowork.reviewer_branch` with `status="warning"` and `details.degraded=true` so a human auditor scanning `audit.md` sees the degraded run at a glance. Do not claim parity with the `notebooklm` branch.

**Branch selection rule.** The `using-scriptorium` runtime probe sets `REVIEWER_BRANCH` from the connectors the user has enabled: NotebookLM enabled → `notebooklm`; NotebookLM absent → `inline_degraded`. The orchestrator must NOT silently fall back from `notebooklm` to `inline_degraded` mid-run — if NotebookLM ingest fails, surface the error and stop, rather than producing a `notebooklm`-branded payload that the inline branch actually wrote.

**Audit row quartet per Cowork gate run**: `reviewer.cite`, `reviewer.contradiction`, `synthesis.gate`, `cowork.reviewer_branch`. If you don't see all four in `audit.jsonl` after a `finalize_synthesis_reviewers` call, the gate did not run to completion — investigate before declaring synthesis done.

The §6.3 schema is unchanged in this branch — `runtime="cowork"` is the only payload-level marker. The branch literal lives in the `cowork.reviewer_branch` audit row's `details["branch"]`, not on the §6.3 payload itself.

## Hand-off

After the cite-check passes, report: "Synthesis written; N sentences, M citations, 0 unsupported." Hand off to `lit-contradiction-check` (if not already run) or to the user for review.

## v0.3 additions

- New citations use `[[paper_id#p-N]]`. The verifier still accepts legacy `[paper_id:loc]`.
- Review artifacts carry frontmatter with `schema_version: scriptorium.review_file.v1`.
