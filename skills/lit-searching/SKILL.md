---
name: lit-searching
description: Use when the user asks to find/search/discover papers on a topic, wants candidate sources for a literature review, or is populating/extending corpus.jsonl. Fires for both Claude Code (CLI path) and Cowork (MCP path) and enforces the Consensus output-fencing rule.
---

# Literature Searching

**Defensive fallback (fire `using-scriptorium` first):** If the three-discipline preamble (Evidence-first claims / PRISMA audit trail / Contradiction surfacing) is not already loaded for this session, invoke `using-scriptorium` before continuing. Primary injection runs via the Claude Code `SessionStart` hook and the Cowork MCP `instructions` field — this fallback covers the rare case where neither fired.

## Precondition — scope.json is required

`lit-searching` reads `<review_root>/scope.json` at startup. If it does not exist, STOP and invoke `lit-scoping` first — do not ask the user for query, year range, or criteria yourself. Those values come from the scope artifact.

Fields consumed from scope.json:

- `research_question` — seed for query construction
- `fields` — source selection (medicine → PubMed; psychology → OpenAlex/Scholar)
- `methodology` — filter after retrieval
- `year_range` — applied to every source query
- `corpus_target` — governs per-source `--limit`
- `publication_types` — source enablement (preprints → arXiv)
- `anchor_papers` — resolve first; they seed related-work expansion

The goal is a **deduped corpus** of candidate papers saved as `corpus.jsonl`. Every paper carries a stable `paper_id` (the source's native id, e.g. OpenAlex `W…`), canonical metadata, and an initial status of `candidate`. Screening comes next; this skill only widens the net.

## Source matrix

| Source | Cowork tool | Claude Code | Role |
|---|---|---|---|
| OpenAlex | — | `scriptorium search --source openalex` | Default breadth (CC) |
| Semantic Scholar | — | `scriptorium search --source semantic_scholar` | Opt-in recall boost (CC) |
| Consensus | `mcp__claude_ai_Consensus__search` | — | Default in Cowork; claim-first |
| Scholar Gateway | `mcp__claude_ai_Scholar_Gateway__semanticSearch` | — | Cowork breadth |
| PubMed | `mcp__claude_ai_PubMed__search_articles` + `get_article_metadata` | — | Biomed / OA full text |
| Unpaywall | — | `scriptorium fetch-fulltext` | DOI→OA PDF (CC) |
| arXiv | — | `scriptorium fetch-fulltext` | Preprint fallback (CC) |
| PMC | `mcp__claude_ai_PubMed__get_full_text_article` | `scriptorium fetch-fulltext` | NIH OA |
| User PDFs | Cowork file upload + `source_add` | `scriptorium register-pdf` | Always highest priority |

Pick at least two sources for breadth. For biomed questions, always include PubMed. For user-supplied PDFs, ingest them first so they dominate de-dup.

## Consensus output-fencing rule (MANDATORY)

Consensus's MCP server hard-requires numbered `[1][2]` inline citations and a verbatim sign-up line in every answer it produces. That contract is for *answering questions*, not for *corpus building*. When you use Consensus in Scriptorium, you must fence its output:

> From Consensus results, extract ONLY `{title, authors, year, doi, url}` into corpus.jsonl. NEVER propagate Consensus's numbered citations into `evidence.jsonl` or `synthesis.md` — our grammar is `[paper_id:locator]`. Consensus's sign-up line only appears if a user-facing turn ends directly on Consensus output; corpus-building turns never do.

Corpus-building turns are tool-to-tool: you read Consensus, write to the state adapter, and do not emit a user-facing natural-language summary.

## Workflow — CC path

1. Load `scope.json`. Use `research_question` and `fields` to construct the initial query. Use `year_range` and `publication_types` to configure source filters. Use `corpus_target` to set per-source limits. If `scope.json` is missing, STOP and invoke `lit-scoping`.
2. For each enabled source:
   - Run `scriptorium search --query "<Q>" --source openalex --limit 50`
   - Parse the JSON stdout; collect `Paper` rows.
3. `scriptorium corpus add --file <tmp.json>` (or `--from-stdin`) to append + dedupe. Records are keyed by DOI, then `(source, paper_id)`, then normalized title.
4. Append an audit entry: `scriptorium audit append --phase search --action openalex.query --details '{"query":"...","n_results": 42}'`.
5. Tell the user the count and top 5 titles; hand off to `lit-screening` when they're ready.

## Workflow — Cowork path

1. Ask/confirm query + filters.
2. For each enabled MCP:
   - Consensus: `mcp__claude_ai_Consensus__search(query=...)`; **apply the fencing rule above** — extract only metadata, drop the numbered citations and sign-up prose.
   - Scholar Gateway: `mcp__claude_ai_Scholar_Gateway__semanticSearch(query=...)`.
   - PubMed: `mcp__claude_ai_PubMed__search_articles(query=...)`, then `get_article_metadata` per PMID for DOIs + abstracts.
3. Normalize every result to the Paper shape from `using-scriptorium`: `{paper_id, source, title, authors[], year, doi, abstract, venue, open_access_url}`.
4. Dedupe in-memory by DOI → `(source, paper_id)` → normalized title.
5. Write to the state adapter's `corpus` note (NotebookLM) / file (Drive) / child page (Notion) — as an appended JSONL block for notebooks/pages, or a real `corpus.jsonl` for Drive.
6. Append an `audit` entry describing (phase, action, details). In notebook-mode, the `audit-jsonl` note gets one appended JSON line per call.

## Dedupe semantics

- DOI is the strongest key; if two rows share a DOI, keep the one with the richer record (non-empty abstract, venue, authors).
- Otherwise, `(source, paper_id)` is unique within a source.
- Last-resort fallback is normalized title (`re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()`). Two titles that normalize identically are treated as the same paper.

## When to stop searching

Stop when (a) the user is satisfied with the count, or (b) the last 20 new results contain fewer than 3 novel titles after dedupe — diminishing returns. Record both the stopping condition and the final count in an audit entry before handing off to `lit-screening`.
