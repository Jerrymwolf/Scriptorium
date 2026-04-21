---
name: lit-extracting
description: Use when the user asks to pull full text of kept papers, extract methods/findings, or populate evidence.jsonl from PDFs. Runs the cascade user_pdf → unpaywall → arxiv → pmc → abstract_only and records every step.
---

# Literature Extracting

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

## Workflow — Cowork path

Unpaywall and arXiv are not available in Cowork. The cascade collapses to **user_pdf → pmc (via PubMed MCP) → abstract_only**.

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

## Hand-off

After every kept paper is extracted, report "N papers extracted, M evidence rows written" and hand off to `lit-synthesizing`.

## v0.3 additions

Full-text source enum: `user_pdf | unpaywall | arxiv | pmc | abstract_only`. Paper stubs require this field in frontmatter (`full_text_source`).
