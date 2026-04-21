# Scriptorium

**A literature review workflow you can defend.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Status: beta](https://img.shields.io/badge/status-beta%20v0.3-blue.svg)](#status)

You have 200 candidate papers, a deadline, and no defensible record of how you got here. When your committee asks *"how did you search?"* — the honest answer won't reconstruct.

Scriptorium turns the middle third of your lit review — **search through synthesis** — into a disciplined, auditable workflow inside the AI assistant you already use. Every claim in your draft traces to a paper and page. Every search, screen, and extraction is logged. Contradictions get named, not averaged.

When you need to come up the curve on an unfamiliar subject fast: run a scoped review tonight, generate a NotebookLM podcast of it, listen on the commute, show up with the literature in your head.

Runs in **Claude Code**, **Claude Cowork**, or **Codex CLI**. No new subscription — it rides the Claude or ChatGPT plan you already have.

---

## Contents

- [Why Scriptorium (not Elicit, Consensus, ResearchRabbit)](#why-scriptorium)
- [What the output looks like](#output)
- [Your first review in 10 minutes](#first-review)
- [Working inside an Obsidian vault](#obsidian)
- [Publishing to NotebookLM](#publishing)
- [Where it runs](#where-it-runs)
- [Install · Configure · Scope · FAQ](#install)
- [Cite · Credits](#cite)

---

## Why Scriptorium <a id="why-scriptorium"></a>

Scriptorium isn't a search engine. It's a workflow. Elicit answers questions. Consensus surfaces claims. ResearchRabbit maps citation networks. Scite checks whether a paper is supported or contradicted. **Scriptorium takes what those tools produce and turns it into a defensible chapter with an audit trail.** Use it alongside them, not instead of them.

|                             | Scriptorium         | Elicit   | Consensus   | ResearchRabbit | Scite       |
|-----------------------------|---------------------|----------|-------------|----------------|-------------|
| Primary job                 | Workflow + audit    | Q&A      | Claim search| Citation graph | Claim check |
| Locator-cited extraction    | Yes                 | Partial  | No          | No             | No          |
| PRISMA-style audit log      | Yes                 | No       | No          | No             | No          |
| Names disagreement by camp  | Yes                 | No       | Partial     | No             | Yes         |
| Output is a draft chapter   | Yes (`synthesis.md`)| Summary  | Answer card | Graph          | Badges      |
| Corpus stays local          | Yes                 | No       | No          | No             | No          |

### Who it's for

Graduate researchers across disciplines — MS and PhD students, postdocs, research staff, librarians — and anyone who needs to get up to speed on a literature quickly and defensibly. Scriptorium is domain-neutral. The same three rules apply whether your question is:

- *"Does a caffeine dose of 75–150mg improve working memory in healthy adults?"* (health sciences)
- *"How do institutional investors shape shareholder voting outcomes?"* (political science / business)
- *"What epistemological commitments distinguish constructivist grounded theory from classical?"* (methodology / humanities)

### Three rules, enforced

**1. Every claim cites its source.** Every synthesis sentence carries a `[paper_id:page:N]` token that resolves to a row in an evidence ledger. A final cite-check strips or flags anything unsupported. In Claude Code, a write-time hook runs the same check redundantly.

**2. Every decision is logged.** A PRISMA-style audit trail timestamps every search query, screen decision, extraction call, and reasoning step. When the corpus leaves your machine — via `scriptorium publish` — that event is logged too, with a source manifest.

**3. Disagreement stays visible.** When two papers disagree on the same concept, Scriptorium names the camps. Tension in the literature survives into your draft instead of getting smoothed into false consensus.

---

## What the output looks like <a id="output"></a>

A row of `evidence.jsonl` — one extracted claim, locator-cited:

```json
{"paper_id": "nehlig2010", "locator": "page:4", "claim": "Caffeine at 75–150mg improves sustained attention in healthy adults", "quote": "Doses between 75 and 150 mg improve sustained attention and vigilance...", "direction": "positive", "concept": "attention"}
```

A fragment of `synthesis.md` — every sentence citation-grounded:

```markdown
Caffeine at 75–150mg doses reliably improves sustained attention [nehlig2010:page:4],
though effects on working memory are mixed: short-term recall shows gains in healthy
adults [smith2018:page:7], while complex span tasks show no benefit [kennedy2017:page:12].
```

A section of `contradictions.md` — disagreement named, not averaged:

```markdown
## Does caffeine help working memory?

Supports (2 papers):
- smith2018:page:7 — short-term recall gains, healthy adults, n=48
- chen2020:page:3 — 2-back task improvement at 100mg, n=32

Against (2 papers):
- kennedy2017:page:12 — no benefit on complex span tasks, n=60
- park2019:page:9 — null result on operation span, n=45

Unresolved: dose–task interaction. None of the four studies
cross-compare span type against dose. Candidate gap for your review.
```

---

## Your first review in 10 minutes <a id="first-review"></a>

```bash
git clone https://github.com/jerrymwolf/scriptorium.git
cd scriptorium
pip install -e .
./scripts/install_plugin.sh

scriptorium config set unpaywall_email you@university.edu
scriptorium config set obsidian_vault ~/vault     # optional, recommended
```

Restart Claude Code, then in any session:

```
/lit-review "does caffeine improve working memory in healthy adults?" \
  --review-dir reviews/caffeine-wm
```

Four phases, one audit trail:

1. **Scope.** Clarifying questions → `audit.md`.
2. **Search & screen.** OpenAlex (default) or Semantic Scholar (opt-in) → dedupe → apply inclusion/exclusion → log every call.
3. **Extract & synthesize.** Cascade through user-dropped PDF → Unpaywall → arXiv → PMC → abstract-only. Pull locator-cited claims into `evidence.jsonl`. Write `synthesis.md`. Surface contradictions by camp.
4. **Defend.** Final cite-check flags or strips unsupported claims before commit.

A first pass on a well-scoped question typically runs 8–15 minutes and returns 40–80 screened papers.

After the first run:

```
reviews/caffeine-wm/
├── audit.md            # every query, screen, extraction — timestamped
├── evidence.jsonl      # one locator-cited claim per line
├── synthesis.md        # draft chapter, every sentence cited
├── contradictions.md   # named disagreement between papers
├── references.bib      # BibTeX, drop into Zotero
└── pdfs/               # retrieved full text
```

### The highest-leverage use: get smart fast on an unfamiliar subject

You have a meeting tomorrow on a topic you don't own. Tonight: run a scoped review with `--review-dir` pointing at a new folder in your vault. Morning: `scriptorium publish --generate audio` pushes the corpus to NotebookLM and kicks off a podcast. Commute: listen. You show up with the actual literature in your head, not a hot take.

---

## Working inside an Obsidian vault <a id="obsidian"></a>

Scriptorium's outputs are plain markdown. An Obsidian vault is a folder of plain markdown. Point `--review-dir` at a path inside your vault and you get the entire Obsidian ecosystem for free — no plugins, no config, no new storage format.

```bash
/lit-review "caffeine and working memory" --review-dir ~/vault/reviews/caffeine-wm
```

What this buys you:

- **Graph view** visualizes how papers relate across reviews, surfacing connections that don't exist in any single synthesis.
- **Backlinks** show which other reviews touched the same papers, which contradictions reappear across topics.
- **Search** spans your entire corpus, not just one review.
- **Dataview queries** turn `evidence.jsonl` and frontmatter into a research dashboard.
- **Reviews accumulate.** Your third review talks to your first two. The vault becomes a knowledge base, not a pile of folders.

If a review directory sits inside a folder containing `.obsidian/`, Scriptorium detects it and logs `vault_root` to `audit.md`. v0.3 emits YAML frontmatter, paper-per-note files with wikilink backlinks (`[[paper_id]]`), and Dataview templates. An `overview.md` index ties the review together.

**Cowork users:** Obsidian is local-first; Cowork runs in a browser. To reach a local vault from Cowork, expose it via the [`obsidian-claude-code-mcp`](https://github.com/iansinnott/obsidian-claude-code-mcp) plugin over HTTP/SSE. If that's more setup than you want, Drive or Notion is the simpler default; sync to your vault afterwards.

---

## Publishing to NotebookLM <a id="publishing"></a>

```bash
scriptorium publish --review-dir ~/vault/reviews/caffeine-wm \
  --notebook "Caffeine and Working Memory" \
  --generate audio
```

Creates a NotebookLM notebook, uploads PDFs from `pdfs/` plus `synthesis.md` and `evidence.jsonl` as sources, triggers an Audio Overview. `--generate` accepts `audio`, `deck`, `mindmap`, `video`, or `all`. Every upload event — notebook ID, file manifest, artifact IDs — is logged to `audit.md`.

One-time setup:

```bash
uv tool install notebooklm-mcp-cli
nlm auth login    # use a dedicated Google account, not your primary
```

Google hasn't released an official NotebookLM API. Scriptorium integrates with the community [`notebooklm-mcp-cli`](https://github.com/jacob-bd/notebooklm-mcp-cli) project (the `nlm` CLI), which drives a browser under the hood.

**Tradeoffs:** The CLI breaks when Google changes the UI. Use a dedicated Google account (automation may flag a primary). Google has not endorsed these tools and can disable them at any time. If any of that is a dealbreaker, skip the CLI — open [NotebookLM](https://notebooklm.google.com), create a notebook, drag in the files from `pdfs/` plus `synthesis.md` and `evidence.jsonl`, generate artifacts from the Studio panel. Scriptorium's defensibility doesn't depend on any of this.

---

## Where it runs <a id="where-it-runs"></a>

Primary surface is **Claude Code**. Cowork and Codex run the same skills through different adapters.

| Surface       | Invocation                | Search                             | State home                                  |
|---------------|---------------------------|------------------------------------|---------------------------------------------|
| Claude Code   | `/lit-review "…"`         | CLI · OpenAlex · Semantic Scholar  | Obsidian vault (recommended) or plain files |
| Claude Cowork | *"run a lit review on X"* | Consensus · Scholar Gateway · PubMed MCPs | Obsidian MCP → Drive → Notion → session |
| Codex CLI     | `/lit-review "…"`         | CLI (via symlinked skills)         | Obsidian vault (recommended) or plain files |

All three surfaces publish to NotebookLM through `scriptorium publish` (Code, Codex) or manual upload (Cowork can't shell out). All three run the cite-check as a skill step; Code and Codex add a PostToolUse hook for write-time enforcement.

A runtime probe in the `using-scriptorium` meta-skill picks the right path at session start.

---

## Install, configure, scope, FAQ <a id="install"></a>

Source-install for now — not yet on PyPI.

<details>
<summary><b>Claude Code</b></summary>

```bash
git clone https://github.com/jerrymwolf/scriptorium.git
cd scriptorium
pip install -e .
./scripts/install_plugin.sh
```

Restart Claude Code, then:

```
/lit-config              # one-time: set unpaywall_email and obsidian_vault
/lit-review "your research question" --review-dir reviews/<slug>
```

Optional for publishing: `uv tool install notebooklm-mcp-cli && nlm auth login`
</details>

<details>
<summary><b>Claude Cowork</b></summary>

Install the plugin in your Cowork workspace. Recommended connectors:

- Consensus (claim-framed search), Scholar Gateway (breadth), PubMed (biomedical + OA full text)
- State home: Obsidian via [obsidian-claude-code-mcp](https://github.com/iansinnott/obsidian-claude-code-mcp), or Drive, or Notion

Without a search connector, the plugin falls back to WebFetch against OpenAlex and reports degraded mode. See [`docs/cowork-smoke.md`](docs/cowork-smoke.md) for the full capability matrix.

In any Cowork chat: *"run a lit review on caffeine and working memory"*.
</details>

<details>
<summary><b>Codex CLI</b></summary>

```bash
./scripts/codex_link.sh
```

Populates `.codex/skills/` and `.codex/commands/` as symlinks into `.claude-plugin/`. See [`docs/codex-setup.md`](docs/codex-setup.md).
</details>

### Configure

```bash
scriptorium config set unpaywall_email you@university.edu
scriptorium config set obsidian_vault ~/vault
```

Required: `unpaywall_email`. Optional: `obsidian_vault`, `openalex_email`, `semantic_scholar_api_key`, `default_backend`, `languages`. In Cowork, config lives as a user-memory note — the `configuring-scriptorium` skill handles it. All writes go through `scriptorium config set` — never shell-exec.

### Scope <a id="status"></a>

Scriptorium owns the middle third — search through synthesis. Scoping the question and writing the final chapter stay with you. The cite-check fails closed: unsupported claims get flagged or stripped before commit.

Scriptorium doesn't try to be your reference manager, your knowledge base, or your publishing platform. Zotero/Mendeley for citations, Obsidian for accumulating knowledge, NotebookLM for Studio artifacts.

**Status: beta (v0.3).** Pipeline is stable and used daily for real dissertation work. CLI flags and skill interfaces may shift before 1.0; breaking changes ship in release notes. Fine for dissertation work if you pin a version. Not yet recommended for multi-author systematic reviews where interface stability matters more than iteration speed.

**Not in v0.3:** SVG PRISMA flow diagrams, thematic maps, `comparison.csv`, Graphify/Firecrawl integration, risk-of-bias extraction, live-watch view.

### FAQ

**Does my corpus leave my machine?** Not by default. In Claude Code or Codex, PDFs and extracted evidence stay local. In Cowork, state is stored in whichever connector you enable (Obsidian MCP, Drive, or Notion). `scriptorium publish` is the one operation that uploads to a third party (Google, via NotebookLM) — only when you invoke it. Every publish is logged with a manifest.

**What happens when a paper is paywalled?** Scriptorium cascades: user-dropped PDF → Unpaywall OA → arXiv preprint → PMC → abstract-only. Abstract-only papers are tagged; synthesis marks those claims lower-confidence and the cite-check flags them.

**Does this replace Zotero / Mendeley / EndNote?** No. `references.bib` imports cleanly into any of them.

**Why Obsidian specifically?** Obsidian vaults are folders of markdown — the format Scriptorium already produces, zero translation overhead. Any markdown tool works (Logseq, Foam, VS Code). Obsidian gets the call-out because its graph view, Dataview, and backlink ecosystem are the most mature for cross-review synthesis.

**Does this replace NotebookLM?** No. The pipeline is Scriptorium (rigor) → Obsidian (working knowledge) → NotebookLM (publishing artifacts).

**Can I use it for a Cochrane-style systematic review?** The audit trail supports the transparency requirements. v0.3 doesn't generate PRISMA 2020 SVG flow diagrams or handle risk-of-bias extraction. Treat Scriptorium as a screening-and-extraction assistant, not a replacement for Covidence or RevMan.

**What does it cost?** Scriptorium is MIT-licensed and free. You need an existing Claude (Code / Cowork) or ChatGPT (Codex) plan. OpenAlex is free; Semantic Scholar is free with a key; NotebookLM Studio outputs are quota-metered by Google.

---

## Cite · Credits <a id="cite"></a>

Drop-in methods-section language:

> Literature identification, screening, and extraction were conducted using Scriptorium v0.3 (Wolf, 2026), a workflow tool that logs every search query, screening decision, and extraction call to a PRISMA-style audit trail. Claims in the synthesis carry locator-level citations (`[paper_id:page:N]`) resolved against an evidence ledger; a final cite-check pass flags or removes unsupported claims before the draft is committed. Contradictions between sources are surfaced by camp rather than averaged.

```bibtex
@software{scriptorium2026,
  author  = {Wolf, Jerry},
  title   = {Scriptorium: a literature review workflow you can defend},
  year    = {2026},
  version = {0.3},
  url     = {https://github.com/jerrymwolf/scriptorium}
}
```

Design spec: [`docs/superpowers/specs/2026-04-19-superpowers-research-design.md`](docs/superpowers/specs/2026-04-19-superpowers-research-design.md) · Changelog: [`CHANGELOG.md`](CHANGELOG.md) · Cowork matrix: [`docs/cowork-smoke.md`](docs/cowork-smoke.md)

### Develop

```bash
pip install -e ".[dev]"
pytest
```

Adapter unit tests, CLI integration tests, skill/command content tests, end-to-end caffeine fixture in `tests/test_e2e_caffeine.py`, mocked `nlm` tests for `publish`.

### License · Credits

MIT.

Scriptorium is architected in the style of **[Superpowers](https://github.com/obra/superpowers)** by Jesse Vincent — self-contained skill folders with `SKILL.md` files that Claude loads on demand. The pattern is *Superpowers*; the application to literature review is *Scriptorium*. The NotebookLM integration wraps **[`notebooklm-mcp-cli`](https://github.com/jacob-bd/notebooklm-mcp-cli)** by Jacob Ben-David; Scriptorium shells out to `nlm` and does not vendor, embed, or modify it.
