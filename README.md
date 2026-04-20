# Scriptorium

> **Architected in the style of [Superpowers](https://github.com/obra/superpowers).** Skills here apply the same pattern — self-contained folders with `SKILL.md` files that Claude loads on demand — to the craft of literature review. The name of the style is *Superpowers*; the application to literature review is *Scriptorium*.

Dual-runtime (Claude Code + Cowork) literature-review plugin. Replaces hand-rolled Elicit-style workflows for the search → synthesis path of a lit review, with three enforced disciplines:

1. **Evidence-first claims** — every synthesis sentence carries a `[paper_id:locator]` citation that resolves to an `evidence.jsonl` row; the `lit-synthesizing` skill ends with a mandatory cite-check.
2. **PRISMA audit trail** — every search, screen, extraction, and reasoning decision appends to `audit.jsonl` + `audit.md`.
3. **Contradiction surfacing** — `lit-contradiction-check` names disagreement between papers rather than averaging them into a bland claim.

## What's in v0.2

- OpenAlex (default) + Semantic Scholar (opt-in) search adapters in Claude Code
- Consensus + Scholar Gateway + PubMed MCP connector support in Cowork
- Full-text cascade: user-dropped PDFs → Unpaywall → arXiv → PMC → abstract-only (CC); PubMed `get_full_text_article` + user uploads (Cowork)
- Per-review state in plain files (`corpus.jsonl`, `evidence.jsonl`, `audit.md`/`audit.jsonl`, `synthesis.md`, `pdfs/`, `bib/`) with a state-adapter that maps the same concepts onto NotebookLM notebooks (primary), Google Drive folders (fallback), Notion pages (stretch), or session-only in Cowork
- Evidence-first PostToolUse hook (CC only) — belt-and-suspenders redundancy on top of the skill-level cite-check
- Basic contradiction surfacing (positive vs negative direction on the same concept)
- BibTeX + RIS export
- NotebookLM Studio publishing — generate a podcast, slide deck, infographic, or video overview of the finished review

## Two runtimes, one prose layer

Scriptorium runs in **Claude Code** via the `scriptorium` CLI plus slash commands + a PostToolUse hook, and in **Cowork** via skills + platform MCPs. The `using-scriptorium` meta-skill runs a runtime probe at session start and dispatches every phase to the right surface. See [`docs/cowork-smoke.md`](docs/cowork-smoke.md) for the Cowork connector matrix and the degraded-mode fallback.

## Install

### Claude Code

```bash
# 1. Install the CLI (gives you the `scriptorium` console script)
pipx install scriptorium

# 2. Install the plugin surface (symlinks .claude-plugin/ into ~/.claude/plugins/scriptorium)
git clone https://github.com/jeremiahwolf/scriptorium.git
cd scriptorium
./scripts/install_plugin.sh

# 3. Restart Claude Code so the plugin loads
```

Then in any Claude Code session:

```
/lit-config              # one-time: set Unpaywall email + other settings
/lit-review "your research question"
```

Optional flags on `/lit-review`: `--review-dir <path>` to put the review state somewhere other than the current directory.

### Cowork

Install the plugin in your Cowork workspace. Enable these connectors for the full experience:

- **Consensus** — claim-framed search (`mcp__claude_ai_Consensus__search`)
- **Scholar Gateway** — breadth search (`mcp__claude_ai_Scholar_Gateway__semanticSearch`)
- **PubMed** — biomed search + OA full text (`mcp__claude_ai_PubMed__*`)
- **NotebookLM** — state home + Studio publishing (`mcp__notebooklm-mcp__*`)

Without any search connector, the plugin falls back to WebFetch against the OpenAlex REST API (degraded mode — tell the user). Without NotebookLM, state lives in a Drive folder, a Notion page, or session-only in that order. See `docs/cowork-smoke.md` for the full capability table.

Then in any Cowork chat, say:

> Run a lit review on caffeine and working memory.

The `running-lit-review` skill activates on that phrasing and runs the same pipeline as `/lit-review` does in CC.

### Codex

Run `./scripts/codex_link.sh` to populate `.codex/skills/` and `.codex/commands/` as symlinks into `.claude-plugin/`. Point your Codex config at the repo.

## Per-review files

Run `/lit-review` (CC) or say "run a lit review on X" (Cowork) from the directory (or notebook) where review state should live — typically a dissertation chapter directory in CC, or a fresh NotebookLM notebook in Cowork. Override with `--review-dir <path>` in CC.

## Configuration

Run `/lit-config` (CC) or say "configure scriptorium" (Cowork). Required: `unpaywall_email`. Optional: `openalex_email`, `semantic_scholar_api_key`, `default_backend`, `languages`. All writes go through `scriptorium config set KEY VALUE` (CC) or a user-memory note (Cowork) — never through shell-exec.

## Test

```bash
pip install -e ".[dev]"
pytest
```

Runs the full suite — unit tests for every adapter, integration tests for the CLI, content tests for every skill/command, and the end-to-end caffeine fixture pipeline in `tests/test_e2e_caffeine.py`.

## License

MIT.
