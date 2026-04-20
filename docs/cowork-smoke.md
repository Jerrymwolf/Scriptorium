# Cowork Smoke Matrix (Manual)

Cowork can't be driven from a Claude Code test harness — skills run inside a live Cowork session and each user enables platform connectors individually. This document freezes the smoke-test spec so regressions are catchable by eye.

Run the matrix whenever a skill under `.claude-plugin/skills/` is edited, whenever `using-scriptorium`'s runtime probe changes, or before tagging a release.

## What "smoke test" means here

Open a fresh Cowork chat with the scriptorium plugin installed. Say:

> Run a lit review on caffeine and working memory.

The `running-lit-review` skill should activate (description match). The first thing it does is fire `using-scriptorium`, which runs the runtime probe. The probe reports which connectors it sees. That report is what you verify against each row below.

## Connector matrix

Test each combination by toggling the connectors in the Cowork connector settings, reopening a chat, and triggering the activation phrase above.

| Connectors enabled | Expected runtime-probe output | Expected search path | Expected state home |
|---|---|---|---|
| None (bare Cowork) | `mcp__claude_ai_*__search` absent; `mcp__notebooklm-mcp__*` absent | **Degraded mode** — WebFetch → OpenAlex REST (`https://api.openalex.org/works?search=...`). Skill announces "search is running in degraded mode — no Consensus/PubMed/Scholar Gateway detected" | session-only (no persistence across turns) |
| Consensus only | `mcp__claude_ai_Consensus__search` present | Consensus-first; claim-first search | session-only |
| PubMed only | `mcp__claude_ai_PubMed__search_articles`, `get_article_metadata`, `get_full_text_article` present | PubMed for biomed; skill warns if topic looks non-biomed | session-only |
| Scholar Gateway only | `mcp__claude_ai_Scholar_Gateway__semanticSearch` present | Scholar Gateway for breadth | session-only |
| NotebookLM only | `mcp__notebooklm-mcp__notebook_create` present | Degraded search; persistent state lives in the notebook | NotebookLM notebook (one per review) |
| Drive only | `mcp__claude_ai_Google_Drive__authenticate` present; no NotebookLM | Degraded search; state lives in a Drive folder | Drive folder |
| Notion only | `mcp__claude_ai_Notion__authenticate` present | Degraded search; state lives in a Notion page tree | Notion page |
| Consensus + PubMed + NotebookLM | All three probes present | Hybrid search (Consensus for claim-framed questions; PubMed for biomed recall); full cascade with PubMed's `get_full_text_article` as the primary full-text route | NotebookLM (primary) |
| Consensus + Scholar Gateway + PubMed + NotebookLM (ideal) | All four probes present | Every search tool available; dedupe across all three | NotebookLM (primary), Drive fallback |

## State fallback order (lock in the vocabulary)

When multiple state connectors are enabled, `using-scriptorium` picks in this fixed order:

1. **NotebookLM** — primary, because of native PDF sources + Studio publishing
2. **Drive** — fallback if no NotebookLM
3. **Notion** — stretch if no Drive
4. **session-only** — degraded: corpus/evidence/audit live in chat memory; nothing persists across turns

The runtime probe names the chosen home and the user can override by saying "use Drive / Notion / NotebookLM for this review."

## Consensus fencing rule spot-check

When Consensus is enabled and returns results, the `lit-searching` skill MUST:

- **Extract only** `{title, authors, year, doi, url}` from Consensus results into `corpus.jsonl`.
- **Never** propagate Consensus's numbered `[1]`/`[2]` inline citations into `evidence.jsonl` or `synthesis.md` — our grammar is `[paper_id:locator]`.
- **Never** carry Consensus's sign-up line into a corpus-building turn. The sign-up line only appears on a user-facing turn that ends directly on Consensus output.

To verify manually: after a Consensus-backed search, open the corpus note (or `corpus.jsonl` file in NotebookLM) and confirm every row carries the `[paper_id:locator]` vocabulary — never a numbered `[1]`.

## Publishing smoke (NotebookLM)

With NotebookLM enabled, after `lit-synthesizing` + `lit-contradiction-check` pass, say:

> Make a podcast of this review.

Expect `lit-publishing` to fire, call `mcp__notebooklm-mcp__studio_create(artifact_type="audio", ...)`, poll `studio_status`, download the artifact, and append an audit entry. Quota errors should surface the raw message and stop generation.

## Report-back format

When the smoke matrix is run, capture results in a short checklist per row: `connectors enabled` · `probe output` · `search path observed` · `state home observed` · `pass/fail`. A row fails if any of the four observations drift from the expected behavior.
