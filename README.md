# Scriptorium

**Status:** beta (v0.3.0) — install with `pip install scriptorium-cli`.

**A literature review workflow you can defend.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> **Architected in the style of [Superpowers](https://github.com/obra/superpowers).** Skills here apply the same pattern — self-contained folders with `SKILL.md` files that Claude loads on demand — to the craft of literature review. The name of the style is *Superpowers*; the application to literature review is *Scriptorium*.

---

You've got 200 candidate papers, a deadline, and no defensible record of how you got here. Your committee asks *"how did you search?"* — and the honest answer won't reconstruct.

Scriptorium turns the middle third of your lit review — **search → synthesis** — into a disciplined, auditable workflow inside the AI assistant you already use. Every claim in your draft cites a paper and page. Every search, screen, and extraction is logged. Contradictions between papers get named, not averaged.

When you finish, you have a chapter you can defend, a methods-section-ready audit trail, and — optionally — a NotebookLM podcast, slide deck, infographic, or video generated from the review itself.

Runs in **Claude Code**, **Claude Cowork**, or **Codex**. No new subscription — it rides the Claude or ChatGPT plan you already have.

---

## Who this is for

Graduate researchers across disciplines — MS and PhD students, postdocs, research staff, librarians. Scriptorium is domain-neutral; the same three disciplines apply whether your question is:

- *"Does a caffeine dose of 75–150mg improve working memory in healthy adults?"* (health sciences)
- *"How do institutional investors shape shareholder voting outcomes?"* (political science / business)
- *"What epistemological commitments distinguish constructivist grounded theory from classical?"* (methodology / humanities)

If your review needs to cite its sources and survive committee scrutiny, this tool is for you.

---

## What you get

- **A defensible synthesis.** Every sentence in `synthesis.md` traces to a paper and page. If it's not in the evidence, it's not in the draft.
- **A committee-ready audit trail.** `audit.md` is a timestamped log of every query, screen decision, and extraction call. Your methods chapter has a receipt.
- **A clean reference library.** BibTeX and RIS exports drop straight into Zotero, Mendeley, EndNote, Paperpile — whatever you use.
- **The PDFs you actually read.** Scriptorium fetches open-access full text (Unpaywall, arXiv, PMC) and ingests ones you drop in. Your corpus lives where you work, not in someone else's cloud.
- **A published summary of your own review.** Generate a NotebookLM podcast, slide deck, infographic, or video — see [Share the finished review](#share-the-finished-review) below.

---

## Three disciplines, enforced

**1. Every claim cites its source.** Every synthesis sentence carries a `[paper_id:page:N]` token that resolves to a row in an evidence ledger. A final cite-check strips or flags anything unsupported. In Claude Code, a write-time hook runs the same check redundantly — belt and suspenders against hallucination.

**2. Every decision is logged.** A PRISMA-style audit trail timestamps every search query, screen decision, extraction call, and reasoning step. When your committee asks *"how did you search?"*, you show them the file.

**3. Disagreement stays visible.** When two papers disagree on the same concept, Scriptorium names the camps — not a bland average. The output labels papers supporting each side, so tension in the literature survives into your draft instead of getting smoothed into false consensus.

---

## What the output looks like

**A row of `evidence.jsonl`** — one extracted claim, locator-cited:

```json
{"paper_id": "nehlig2010", "locator": "page:4", "claim": "Caffeine at 75–150mg improves sustained attention in healthy adults", "quote": "Doses between 75 and 150 mg improve sustained attention and vigilance...", "direction": "positive", "concept": "attention"}
```

**A fragment of `synthesis.md`** — every sentence citation-grounded:

```markdown
Caffeine at 75–150mg doses reliably improves sustained attention [nehlig2010:page:4],
though effects on working memory are mixed: short-term recall shows gains in healthy
adults [smith2018:page:7], while complex span tasks show no benefit [kennedy2017:page:12].
```

Every bracketed token resolves to a real row. Unsupported or hallucinated citations fail the cite-check before the file commits.

---

## A session, step by step

In **Claude Code**:

```
/lit-review "does caffeine improve working memory in healthy adults?"
```

1. **Scope.** Scriptorium asks clarifying questions and writes the scope to `audit.md`.
2. **Search.** Queries OpenAlex (default) or Semantic Scholar (opt-in); dedupes results.
3. **Screen.** Applies your inclusion/exclusion criteria; logs every call.
4. **Retrieve full text.** Cascades through user-dropped PDF → Unpaywall → arXiv → PMC → abstract-only.
5. **Extract.** Pulls locator-cited claims into `evidence.jsonl`.
6. **Synthesize.** Writes `synthesis.md` with every sentence citation-grounded.
7. **Surface contradictions.** Names disagreement between papers by camp.
8. **Cite-check.** Final pass — unsupported claims get flagged or stripped before commit.
9. **Publish (optional).** Offers a NotebookLM podcast, deck, infographic, or video.

In **Claude Cowork**: say *"run a lit review on caffeine and working memory"* — the `running-lit-review` skill fires the same pipeline through Consensus, Scholar Gateway, and PubMed MCPs, with NotebookLM as the state home.

In **Codex**: same skills and commands, via symlink.

---

## Share the finished review

When your synthesis passes cite-check, Scriptorium offers four NotebookLM Studio artifacts — each generated from your actual corpus:

- **Audio podcast** (8–20 min, two-host) — commute-prep for comps, share with an advisor who won't read 30 pages.
- **Slide deck** — prospectus defense, committee meeting, conference talk.
- **Infographic** — poster section, chapter appendix, research-day handout.
- **Video overview** — lab wiki, teaching module, dissertation landing page.

Quota-metered by Google. All four use your own corpus — no external content gets injected.

---

## Where it runs

| Surface | Claude Code | Claude Cowork | Codex |
|---|---|---|---|
| Invocation | `/lit-review "…"` | *"run a lit review on X"* | `/lit-review "…"` via symlinked skills |
| Search | `scriptorium` CLI (OpenAlex, Semantic Scholar) | Consensus · Scholar Gateway · PubMed MCPs | CLI |
| Full text | Unpaywall · arXiv · PMC · user PDFs | PubMed full-text + user uploads | Unpaywall · arXiv · PMC · user PDFs |
| State home | Plain files in review directory | NotebookLM notebook → Drive → Notion → session | Plain files |
| Publishing | NotebookLM Studio (if enabled) | NotebookLM Studio | NotebookLM Studio (if enabled) |
| Cite-check | Skill step + PostToolUse hook | Skill step | Skill step + PostToolUse hook |

Same prose layer, different surfaces. A runtime probe in the `using-scriptorium` meta-skill picks the right path at session start.

---

## Install

Scriptorium is source-install for now — not yet on PyPI.

### Quick start (Claude Code)

```bash
git clone https://github.com/jerrymwolf/scriptorium.git
cd scriptorium
pip install -e .
./scripts/install_plugin.sh
```

Restart Claude Code, then in any session:

```
/lit-config              # one-time: set unpaywall_email
/lit-review "your research question"
```

Add `--review-dir <path>` to put review state somewhere other than the current directory.

### Claude Cowork

Install the plugin in your Cowork workspace. For the full experience, enable these connectors:

- **Consensus** — claim-framed search
- **Scholar Gateway** — breadth search
- **PubMed** — biomedical search + OA full text
- **NotebookLM** — state home + Studio publishing

Without a search connector, the plugin falls back to WebFetch against OpenAlex and tells you it's in degraded mode. Without NotebookLM, state lives in a Drive folder, a Notion page, or session-only — in that order. See [`docs/cowork-smoke.md`](docs/cowork-smoke.md) for the full capability matrix.

Then in any Cowork chat:

> Run a lit review on caffeine and working memory.

### Codex

```bash
./scripts/codex_link.sh
```

Populates `.codex/skills/` and `.codex/commands/` as symlinks into `.claude-plugin/`. Point your Codex config at the repo.

---

## Configure

```bash
scriptorium config set unpaywall_email you@university.edu
```

Required: `unpaywall_email`. Optional: `openalex_email`, `semantic_scholar_api_key`, `default_backend`, `languages`. In Cowork, the same config lives as a user-memory note — the `configuring-scriptorium` skill handles it.

All writes go through `scriptorium config set KEY VALUE` — never shell-exec.

---

## What stays yours

Scriptorium owns the middle third of the workflow — search through synthesis. Scoping the question and writing the final chapter stay with you. The cite-check fails closed: unsupported claims get flagged or stripped before commit, so nothing hallucinated ships in your draft.

**Not in v0.2** — SVG PRISMA flow diagrams, thematic maps, `comparison.csv`, Graphify and Firecrawl integration, and a live-watch view are planned for v0.3.

---

## Design and docs

- **Design spec:** [`docs/superpowers/specs/2026-04-19-superpowers-research-design.md`](docs/superpowers/specs/2026-04-19-superpowers-research-design.md)
- **Implementation plan:** [`docs/superpowers/plans/2026-04-19-scriptorium-v0.2.md`](docs/superpowers/plans/2026-04-19-scriptorium-v0.2.md)
- **Cowork capability matrix:** [`docs/cowork-smoke.md`](docs/cowork-smoke.md)

---

## Develop

```bash
pip install -e ".[dev]"
pytest
```

Runs the full suite — adapter unit tests, CLI integration tests, skill/command content tests, the end-to-end caffeine fixture in `tests/test_e2e_caffeine.py`, and a mocked-NotebookLM test for the `lit-publishing` skill.

---

## License

MIT.
