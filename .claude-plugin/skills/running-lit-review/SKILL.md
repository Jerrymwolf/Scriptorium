---
name: running-lit-review
description: Use when the user asks to run a lit review on a topic or research question (e.g. "run a lit review on caffeine and working memory", "do a literature review for me on X"). Orchestrates the full pipeline — search, screen, extract, synthesize, contradiction-check, audit, and optional publishing — by dispatching to the per-phase scriptorium skills in order.
---

# Running a Literature Review

This skill runs the end-to-end review pipeline for a research question. It is **runtime-agnostic** — the same ordered steps execute in Claude Code (via the `scriptorium` CLI) and in Cowork (via Consensus / Scholar Gateway / PubMed / NotebookLM MCPs). Routing lives in the `using-scriptorium` meta-skill; this skill just sequences the phases.

**Fire using-scriptorium first.** Before doing anything else, invoke `using-scriptorium` so the runtime probe has run, the state-adapter vocabulary is loaded, and the three disciplines are primed. Then return here.

## Inputs you need before starting

Ask the user — in one message, not a sequence — for any of these that were not stated:

- **Research question** (required; usually already given).
- **Inclusion / exclusion criteria**: year range, language, must-include keywords, must-exclude keywords. Defaults if they shrug: `year_min=2015`, `language=["en"]`, must-include derived from the question, no must-exclude.
- **Review root**: where state should live. In CC this is `cwd` unless `--review-dir` overrides. In Cowork this is the NotebookLM notebook (create one if none exists) — fall back to Drive folder or a Notion page as the state-adapter dictates.
- **Publishing intent**: podcast / slides / infographic / video, or none. Default to asking at the end — publishing is optional and runs *after* contradiction-check, never before.

## Phase sequence (authoritative)

1. **Search** — fire `lit-searching`. Runs across the enabled sources (CC: OpenAlex default, Semantic Scholar opt-in; Cowork: Consensus + Scholar Gateway + PubMed as available). Writes to `corpus.jsonl` via the state adapter. Appends an audit entry. Each phase writes at least one entry to the audit trail.
2. **Screen** — fire `lit-screening`. Applies the criteria from the inputs section. Updates `corpus.jsonl` statuses (`kept` / `dropped`) and appends an audit entry.
3. **Extract** — fire `lit-extracting`. For each kept paper, resolve full text (CC: `scriptorium fetch-fulltext` runs the user-PDF → Unpaywall → arXiv → PMC → abstract-only cascade; Cowork: PubMed `get_full_text_article` + user uploads). Write evidence rows with `[paper_id:locator]` locators to `evidence.jsonl`.
4. **Synthesize** — fire `lit-synthesizing`. Write `synthesis.md`. Each sentence must carry a `[paper_id:locator]` token that resolves to an `evidence.jsonl` row. **The skill's mandatory final step 5 is the cite-check before commit.** Do not skip. In CC, a PostToolUse hook re-runs `scriptorium verify --synthesis <path>` as belt-and-suspenders — but the skill is authoritative. This is an evidence-first discipline checkpoint.
5. **Contradiction-check** — fire `lit-contradiction-check` as a **separate pass** after synthesis, never inside it. Group evidence by concept; surface positive/negative disagreement as named camps; rewrite affected synthesis sections to name the disagreement rather than average it.
6. **Audit** — `lit-audit-trail` writes every phase transition. By the end, the trail contains entries for each phase. Every phase writes at least one entry.
7. **Publishing (optional)** — if the user asked for derivative artifacts (podcast / slides / infographic / video), fire `lit-publishing`. Preconditions: `synthesis.md` passes `verify` and contradiction-check has been run. NotebookLM Studio drives the generation; each artifact appends its own audit entry. If the user did not ask, skip this phase and offer it as a question at the end of the report-back.

## Report-back template (final turn)

When the pipeline exits, tell the user exactly:

- **Corpus size**: N returned, M deduped, K kept after screening.
- **Full-text rate**: `fetched / kept` (e.g. 28/42).
- **Evidence rows**: total rows in `evidence.jsonl`.
- **Verify result**: unsupported sentences caught (0 is the goal; any non-zero means the cite-check fired).
- **Contradiction pairs**: count, with the concepts involved.
- **Outputs**: paths to `synthesis.md`, `audit.md`, `bib/references.bib` (if exported), and any NotebookLM Studio artifacts.

End with a single question: "Do you want a podcast / slide deck / infographic / video of this review, or are we done?"

## What you must never do

- Run a phase out of order. Synthesis-before-extract is silent plagiarism risk.
- Smooth over contradictions during synthesis. That is `lit-contradiction-check`'s job.
- Skip the audit trail for any phase. The whole point of PRISMA is reconstructability.
- Re-implement search / screen / verify / export logic inside this skill. Route to the per-phase skills every time.
- Accept a synthesis that did not pass the cite-check.

## Runtime cheat-sheet

| Phase | Claude Code | Cowork |
|---|---|---|
| Search | `scriptorium search --query ... --source openalex\|semantic_scholar` | `mcp__claude_ai_Consensus__search`, `mcp__claude_ai_Scholar_Gateway__semanticSearch`, `mcp__claude_ai_PubMed__search_articles` |
| Full text | `scriptorium fetch-fulltext --paper-id <id>` | `mcp__claude_ai_PubMed__get_full_text_article` + user uploads |
| Verify | `scriptorium verify --synthesis <path>` (exit 3 on fail) | In-skill cite-check per `lit-synthesizing` step 5 |
| Audit append | `scriptorium audit append --phase <p> --action <a> --details '<json>'` | Append JSON line to `audit-jsonl` note via state adapter |
| Export | `scriptorium bib --format bibtex` + `--format ris` | Ask user which format; generate via skill prose |
