---
name: lit-extracting
description: Use when the user asks to pull full text of kept papers, extract methods/findings, or populate evidence.jsonl from PDFs. Runs the cascade user_pdf → unpaywall → arxiv → pmc → abstract_only and records every step.
---

# Literature Extracting

**Defensive fallback (fire `using-scriptorium` first):** If the three-discipline preamble (Evidence-first claims / PRISMA audit trail / Contradiction surfacing) is not already loaded for this session, invoke `using-scriptorium` before continuing. Primary injection runs via the Claude Code `SessionStart` hook and the Cowork MCP `instructions` field — this fallback covers the rare case where neither fired.

## HARD-GATE — screening must be complete and corpus must have kept rows

`lit-extracting` reads two signals at startup before fetching any full text:

- `<review_root>/.scriptorium/phase-state.json::phases.screening.status` — must be `"complete"`.
- `<review_root>/corpus.jsonl` — must contain at least one row at `status: "kept"`.

If `screening.status` is anything other than `"complete"` (i.e. `pending`, `running`, `failed`) OR `corpus.jsonl` has no kept rows, STOP and invoke `lit-screening` first. Do not extract from candidate-status rows — they have not been screened against the inclusion/exclusion criteria, and extracting from them silently bypasses the PRISMA audit trail.

If `enforce_v04=false` (advisory mode), warn the user that extraction is normally gated on a complete screening phase, append an `audit.jsonl` row with `mode=advisory`, and proceed only if `corpus.jsonl` has at least one `kept` row AND the user has explicitly acknowledged the missing `screening.status=complete` signal. Silent bypass is forbidden — advisory means *warn loudly and require acknowledgement*, not *suppress the warning*.

Input: kept papers in `corpus.jsonl`. Output: full-text or abstract fallback per paper, plus structured `EvidenceEntry` rows in `evidence.jsonl`. Every row carries `[paper_id:locator]` where `locator` is `page:N`, `sec:<name>`, or a line range — never a numbered citation.

## Cascade (both runtimes)

Full-text retrieval uses a fixed cascade: **user_pdf → unpaywall → arxiv → pmc → abstract_only**. Earlier sources always win. Abstract-only is a valid terminal state — it is never an error.

## Workflow — CC path

For each paper in kept-status:

```bash
# If the user uploaded a PDF, register it first so it wins the cascade.
scriptorium register-pdf /abs/path/to/paper.pdf --paper-id W123

scriptorium fetch-fulltext --paper-id W123 --unpaywall-email you@example.com
# prints {"paper_id":"W123","source":"unpaywall","pdf_path":".../W123__unpaywall.pdf", ...}

scriptorium extract-pdf --pdf .../W123__unpaywall.pdf --paper-id W123
# prints {"paper_id":"W123","n_pages":12,"pages":["<p1 text>", "<p2 text>", ...]}
```

Then, for each claim you want to capture, append one `EvidenceEntry`:

```bash
scriptorium evidence add --paper-id W123 --locator page:4 \
  --claim "Caffeine improved working-memory accuracy at moderate doses." \
  --quote "Accuracy in the 200mg group was significantly higher (p=.02)." \
  --direction positive --concept caffeine_wm_accuracy
```

Record the extraction in the audit trail:

```bash
scriptorium audit append --phase extraction --action fulltext.resolved \
  --details '{"paper_id":"W123","source":"unpaywall","n_pages":12}'
```

## Orchestration — CC parallel fan-out

The per-paper bash block above is the inner loop. The Claude Code runtime fans those papers out under a parallel cap by calling `scriptorium.extract.run_extraction(paths, review_id=..., paper_ids=[...], runtime="claude_code", parallel_cap=<cap>, agent_dispatcher=<callable>)`. Each paper gets its own subagent — a single-id prompt with no sibling-paper context — so per-paper extractions stay isolated. The cap is read from the `extraction_parallel_cap` config key (default `4`); set it via `scriptorium config set extraction_parallel_cap <N>` or in `<review_root>/config.toml`.

For each paper the orchestrator dispatches, exactly one `extraction.dispatch` audit row is appended (`status="success"` on a clean dispatcher return, `status="failure"` with `error` populated when the dispatcher raises). The `details` payload always names `paper_id`, `review_id`, and `runtime="claude_code"`. A failure on one paper does NOT abort the batch — the orchestrator collects all outcomes into `{"successes": ..., "failures": ...}` so the caller can decide whether the run was acceptable. The per-paper inner loop above (`scriptorium fetch-fulltext` / `scriptorium extract-pdf` / `scriptorium evidence add`) runs inside each subagent's isolated context.

## Orchestration — backend dispatch (cowork:mcp / notebooklm / sequential)

The cowork runtime has no local shell. The `using-scriptorium` runtime probe selects an `ISOLATION_BACKEND` from the connectors the user has enabled and the orchestrator dispatches per-paper extraction through that backend. `run_extraction` accepts `runtime="cowork"` plus a `cowork_backend` literal — one of `mcp`, `notebooklm`, `sequential`. Backend selection is the orchestrator's job; this skill describes what each branch does and what audit row it leaves.

- **`mcp`** — preferred when scriptorium-mcp is running. The orchestrator calls `mcp__scriptorium__extract_paper(review_dir, paper_id)` per paper; each call resolves a fresh per-paper prompt server-side and returns the dispatch payload the orchestrator hands to its model turn. `parallel_cap` honored. Audit rows carry `runtime="cowork", backend="mcp"`. Isolation: HIGH — per-paper context lives in the MCP server's process.
- **`notebooklm`** — preferred when NotebookLM is enabled but scriptorium-mcp is not. The orchestrator creates a fresh notebook per paper (or rotates a single scratch notebook for quota-pressured users) via `mcp__notebooklm-mcp__notebook_create` → `source_add(source_type="text"|"file")` → `notebook_query` → `notebook_delete`. `parallel_cap` honored. Audit rows carry `runtime="cowork", backend="notebooklm"`. Isolation: HIGH (fresh notebook) or MEDIUM (rotating scratch — quota-pressured only).
- **⚠ `sequential`** — degraded path when neither scriptorium-mcp nor NotebookLM is reachable. Single chat thread, papers one at a time, with a context-clear prompt between them; the orchestrator must enforce a 5-paper batch ceiling per chat and ask the user to start a fresh chat past that. **`parallel_cap` is ignored — sequential runs strictly serially.** Audit rows carry `runtime="cowork", backend="sequential"`. Isolation: LOW — prompt-discipline only. What is lost: per-paper context isolation. Do not claim parity with `mcp`/`notebooklm`.

All three backends share the T12 audit-row hygiene: exactly one `extraction.dispatch` row per paper, `status="success"` or `status="failure"`, `details` carrying `paper_id`, `review_id`, `runtime`, `backend`, plus `error` on failure. A failure on one paper does NOT abort the batch — the return dict surfaces both `successes` and `failures` so the caller can decide. The per-paper prompt is single-id only (no sibling-paper context); this contamination-resistance property holds across all three Cowork backends.

## Workflow — Cowork path

⚠ no Unpaywall / no arXiv: Cowork has no platform CLI for these sources. The cascade collapses to **user_pdf → pmc (via PubMed MCP) → abstract_only**. What is lost: legal-OA discovery via Unpaywall and preprint full text via arXiv. Coverage drops sharply for any paper that is not user-uploaded and not on PMC; expect a higher proportion of `abstract_only` terminal states.

For each paper:
1. If the user uploaded a PDF, add it as a NotebookLM source via `mcp__notebooklm-mcp__source_add(source_type="file", file_path=...)`. NotebookLM becomes the full-text store.
2. If the paper has a PMCID, `mcp__claude_ai_PubMed__get_full_text_article(pmcid=...)` for NIH OA full text.
3. Otherwise, stay with `abstract` from the corpus row.
4. Read the source/abstract, identify claims, and write `EvidenceEntry` rows into the `evidence` note of the state adapter. Follow the unified shape: `{paper_id, locator, claim, quote, direction, concept}`.

## Locator grammar

Locators are the fine-grained citation handle. Valid forms:

- `page:N` — single PDF page (preferred for PDF-backed claims)
- `page:N-M` — page range
- `sec:<slug>` — section, e.g. `sec:Methods`, `sec:Discussion`
- `abstract` — the paper's abstract (used when only the abstract is available)
- `L<start>-L<end>` — line range inside an extracted plaintext

The synthesis layer reads these when verifying `[paper_id:locator]` tokens. Invent neither paper ids nor locators — the locator must map to something real.

## Direction + concept

- `direction`: one of `positive | negative | neutral | mixed`. "Positive" means the evidence supports the concept; "negative" means it contradicts it; "mixed" means the finding has both directions in the same paper; "neutral" means the paper is relevant but not directionally.
- `concept`: a short slug (`caffeine_wm_accuracy`, not "caffeine's effect on working memory accuracy in adults"). Downstream, `lit-contradiction-check` groups by concept and names positive/negative pairs.

## Red flags — do NOT

- Do NOT extract from rows whose `status != "kept"`. Candidate-status rows have not passed screening; extracting from them silently bypasses the inclusion/exclusion criteria and the PRISMA audit trail.
- Do NOT fabricate `locator` values. A `page:N` that doesn't map to an actual page in the PDF, or a `sec:Methods` for a section the paper doesn't have, is an evidence-fabrication red flag.
- Do NOT invent a `paper_id` when full-text retrieval fails. The cascade's terminal state is `abstract_only`, not "skip the row" and not "make up an id".
- Do NOT skip the `scriptorium audit append --phase extraction` row (CC) or the equivalent audit note append (Cowork). Each `fulltext.resolved` step gets its own audit row.
- Do NOT collapse a quote into your own paraphrase before storing it in the `quote` field. The quote is the verbatim source string the synthesis layer can re-verify.

## Hand-off

After every kept paper is extracted, report "N papers extracted, M evidence rows written" and hand off to `lit-synthesizing`.

## v0.3 additions

Full-text source enum: `user_pdf | unpaywall | arxiv | pmc | abstract_only`. Paper stubs require this field in frontmatter (`full_text_source`).
