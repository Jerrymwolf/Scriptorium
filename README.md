# Scriptorium

**A literature review workflow you can defend.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Status: beta](https://img.shields.io/badge/status-beta%20v0.3.1-blue.svg)](#status)

Are you tired of Ai research that all over the place? Moving citations from Elicit to Research Rabbit to Zotero, all while trying to keep the sources and context clear and organized? It is a challenge!   

Scriptorium turns the middle third of your lit review — **search through synthesis** — into a disciplined, auditable workflow inside the AI assistant you already use. It produces a committee-defensible record as you go: every claim locator-cited to a paper and page, every search and screening decision logged, contradictions between papers named rather than averaged.

When your committee asks *"how did you search?"*, you show them the file. When you need to get smart fast on an unfamiliar subject, you generate a synthesis tonight and listen to a NotebookLM podcast of it on the way to the meeting.

Runs in **Claude Code**, **Claude Cowork**, or **Codex CLI**. No new subscription — it rides the Claude or ChatGPT plan you already have.

Better yet, it is configurable to work with obsidian, so your LLM never forgets where its already been. 

Also it is configurable to work with NotebookLM, so you can build slidedecks, podcasts, and many other things all in one interconnected flow. 

Skill architecture follows the **[Superpowers](https://github.com/obra/superpowers)** pattern by Jesse Vincent — A proven set of self-contained skill folders that Claude/Codex loads on demand.

---

## Contents

- [Why Scriptorium (not Elicit, Consensus, or ResearchRabbit)](#why-scriptorium)
- [Who it's for](#who-its-for)
- [What you get](#what-you-get)
- [Three disciplines, enforced](#three-disciplines-enforced)
- [What the output looks like](#what-the-output-looks-like)
- [Your first review in 10 minutes](#your-first-review-in-10-minutes)
- [How a session flows](#how-a-session-flows)
- [Working inside an Obsidian vault](#obsidian-vault)
- [Use what you made](#use-what-you-made)
- [Publishing to NotebookLM](#publishing-to-notebooklm)
- [Where it runs](#where-it-runs)
- [Install](#install)
- [Configure](#configure)
- [Scope: what Scriptorium does and doesn't do](#scope)
- [FAQ](#faq)
- [Cite Scriptorium in your methods chapter](#cite-scriptorium)
- [Design, develop, license, credits](#design-docs)

---

## Why Scriptorium <a id="why-scriptorium"></a>

Scriptorium isn't a search engine. It's a workflow. Elicit answers questions. Consensus surfaces claims. ResearchRabbit maps citation networks. Scite checks whether a paper is supported or contradicted. **Scriptorium takes what those tools produce and turns it into a defensible chapter with an audit trail.** Use it alongside them, not instead of them.

|                          | Scriptorium       | Elicit             | Consensus       | ResearchRabbit   | Scite           |
|--------------------------|-------------------|--------------------|-----------------|------------------|-----------------|
| Primary job              | Workflow + audit  | Question answering | Claim search    | Citation graph   | Claim check     |
| Locator-cited extraction | ✅                | Partial            | ❌              | ❌               | ❌              |
| PRISMA-style audit log   | ✅                | ❌                 | ❌              | ❌               | ❌              |
| Names disagreement       | ✅                | ❌                 | Partial         | ❌               | ✅              |
| Output is a draft        | ✅ (`synthesis.md`) | Summary          | Answer card     | Graph            | Badges          |
| Your corpus stays local  | ✅                | ❌                 | ❌              | ❌               | ❌              |

If your review needs to **cite its sources and survive committee scrutiny**, Scriptorium is the layer that turns the other tools' output into a chapter.

---

## Who it's for <a id="who-its-for"></a>

Graduate researchers across disciplines — MS and PhD students, postdocs, research staff, librarians — and anyone who needs to get up to speed on a literature quickly and defensibly. Scriptorium is **domain-neutral**. The same three disciplines apply whether your question is:

- *"Does a caffeine dose of 75–150mg improve working memory in healthy adults?"* (health sciences)
- *"How do institutional investors shape shareholder voting outcomes?"* (political science / business)
- *"What epistemological commitments distinguish constructivist grounded theory from classical?"* (methodology / humanities)

Dissertation writers use it to build chapters that survive defense. Consultants and executives use it to come up the curve on a subject before a meeting. Librarians use it to produce reproducible searches for patrons. If your review needs to cite its sources, this tool is for you.

---

## What you get <a id="what-you-get"></a>

- **A defensible synthesis.** Every sentence in `synthesis.md` traces to a paper and page. If it's not in the evidence, it's not in the draft.
- **A committee-ready audit trail.** `audit.md` is a timestamped log of every query, screen decision, extraction call, and — if you publish — every upload event. Your methods chapter has a receipt.
- **A clean reference library.** BibTeX and RIS exports drop straight into Zotero, Mendeley, EndNote, or Paperpile.
- **The PDFs you actually read.** Scriptorium fetches open-access full text (Unpaywall, arXiv, PMC) and ingests ones you drop in. Your corpus lives where you work.
- **A knowledge base that accumulates.** Point `--review-dir` at a folder inside your Obsidian vault and every review links, cross-references, and searches alongside the last one — see [Working inside an Obsidian vault](#obsidian-vault).
- **Publishing to NotebookLM.** When you need a podcast, deck, or briefing doc, `scriptorium publish` pushes the review to NotebookLM Studio — see [Publishing to NotebookLM](#publishing-to-notebooklm).

---

## Three disciplines, enforced <a id="three-disciplines-enforced"></a>

**1. Every claim cites its source.** Every synthesis sentence carries a `[paper_id:page:N]` token that resolves to a row in an evidence ledger. A final cite-check strips or flags anything unsupported. In Claude Code, a write-time hook runs the same check redundantly — belt and suspenders against hallucination.

**2. Every decision is logged.** A PRISMA-style audit trail timestamps every search query, screen decision, extraction call, and reasoning step. When your corpus leaves your machine — via `scriptorium publish` — that event is logged too, with a source manifest. When your committee asks *"how did you search?"*, you show them the file.

**3. Disagreement stays visible.** When two papers disagree on the same concept, Scriptorium names the camps — not a bland average. Tension in the literature survives into your draft instead of getting smoothed into false consensus.

---

## What the output looks like <a id="what-the-output-looks-like"></a>

### A row of `evidence.jsonl` — one extracted claim, locator-cited

```json
{
  "paper_id": "nehlig2010",
  "locator": "page:4",
  "claim": "Caffeine at 75–150mg improves sustained attention in healthy adults",
  "quote": "Doses between 75 and 150 mg improve sustained attention and vigilance...",
  "direction": "positive",
  "concept": "attention"
}
```

### A fragment of `synthesis.md` — every sentence citation-grounded

```markdown
Caffeine at 75–150mg doses reliably improves sustained attention [nehlig2010:page:4],
though effects on working memory are mixed: short-term recall shows gains in healthy
adults [smith2018:page:7], while complex span tasks show no benefit [kennedy2017:page:12].
```

Every bracketed token resolves to a real row. Unsupported or hallucinated citations fail the cite-check before the file commits.

### A section of `contradictions.md` — disagreement named, not averaged

```markdown
## Does caffeine help working memory?

**Supports (2 papers):**
- smith2018:page:7 — short-term recall gains, healthy adults, n=48
- chen2020:page:3 — 2-back task improvement at 100mg, n=32

**Against (2 papers):**
- kennedy2017:page:12 — no benefit on complex span tasks, n=60
- park2019:page:9 — null result on operation span, n=45

**Unresolved:** dose–task interaction. None of the four studies
cross-compare span type against dose. Candidate gap for your review.
```

Disagreement becomes a discussion-chapter asset instead of a buried contradiction.

---

## Your first review in 10 minutes <a id="your-first-review-in-10-minutes"></a>

```bash
# 1. Install (Claude Code path shown; see Install for other surfaces)
git clone https://github.com/jerrymwolf/scriptorium.git
cd scriptorium
pip install -e .

# 2. One-time config
scriptorium config set unpaywall_email you@university.edu
scriptorium config set obsidian_vault ~/vault     # optional but recommended
```

Restart Claude Code, then in any session:

```
/lit-review "does caffeine improve working memory in healthy adults?" \
  --review-dir reviews/caffeine-wm
```

If `obsidian_vault` is set, `--review-dir` resolves relative to it. Scriptorium asks 3–5 clarifying questions, writes the scope to `audit.md`, runs the search, and reports back. A first pass on a well-scoped question typically runs 8–15 minutes and returns 40–80 screened papers with a draft `synthesis.md` on the subset it could retrieve full text for.

**What you should see after the first run:**

```
reviews/caffeine-wm/
├── overview.md         # index tying the review together
├── audit.md            # every query, screen, extraction — timestamped
├── evidence.jsonl      # one locator-cited claim per line
├── synthesis.md        # draft chapter, every sentence cited
├── contradictions.md   # named disagreement between papers
├── references.bib      # BibTeX, drop into Zotero
├── papers/             # paper-per-note with [[wikilink]] backlinks
└── pdfs/               # retrieved full text
```

If that folder is inside your Obsidian vault, Obsidian sees it immediately — graph view, backlinks, and search light up with no additional config.

---

## How a session flows <a id="how-a-session-flows"></a>

Four phases, one audit trail:

**Phase 1 — Scope.** Clarifying questions → `audit.md`.

**Phase 2 — Search & screen.** Query OpenAlex (default) or Semantic Scholar (opt-in) → dedupe → apply inclusion/exclusion criteria → log every call.

**Phase 3 — Extract & synthesize.** Cascade through user-dropped PDF → Unpaywall → arXiv → PMC → abstract-only. Pull locator-cited claims into `evidence.jsonl`. Write `synthesis.md` with every sentence citation-grounded. Surface contradictions by camp.

**Phase 4 — Defend.** Final cite-check flags or strips unsupported claims before commit. The review lives in your vault and is ready for the downstream pipeline — see [Use what you made](#use-what-you-made).

---

## Working inside an Obsidian vault <a id="obsidian-vault"></a>

Scriptorium's outputs are plain markdown. An Obsidian vault is a folder of plain markdown. Point `--review-dir` at a path inside your vault and you get the entire Obsidian ecosystem for free.

```bash
/lit-review "caffeine and working memory" --review-dir ~/vault/reviews/caffeine-wm
```

No plugins required, no special config, no new storage format. Obsidian sees the files the moment they're written. Deeper integration guide: [`docs/obsidian-integration.md`](docs/obsidian-integration.md).

### What you gain

- **Graph view** visualizes how papers relate across reviews, surfacing literature-level connections that don't exist in any single synthesis.
- **Backlinks** appear automatically — each review's notes show which other reviews touched the same papers, which contradictions reappear across topics.
- **Search** spans your entire research corpus, not just one review. Typing *"complex span"* pulls every extraction, every synthesis paragraph, every contradiction note across years of reviews.
- **Dataview queries** turn `evidence.jsonl` and frontmatter into a research dashboard — *"show me every claim with positive direction on working memory, grouped by paper"* becomes a query, not a grep.
- **Reviews accumulate.** Your third review talks to your first two. The vault becomes a growing knowledge base, not a pile of folders.

### Shipping in v0.3

When a review directory sits inside a folder containing `.obsidian/`, Scriptorium detects it and logs `vault_root` to `audit.md`. With `--obsidian-mode` (or when vault detection fires), Scriptorium emits:

- **YAML frontmatter** on every generated file (`type`, `paper_id`, `review`, `concepts`, `direction`) — queryable by Dataview out of the box.
- **Paper-per-note files** under `papers/`, one per included source, with `[[wikilink]]` backlinks between papers that cite the same claim or contradict each other.
- **An `overview.md` index** that ties the review together — scope, search log summary, links into every paper and concept note.
- **Dataview templates** shipped in `docs/obsidian-integration.md` for common queries (claims by direction, contradiction surface, cross-review concept rollup).

### Cowork users

Obsidian is local-first, and Cowork runs in a browser. To use Obsidian as a state home from Cowork you need to expose your local vault via a networked MCP server — the [`obsidian-claude-code-mcp`](https://github.com/iansinnott/obsidian-claude-code-mcp) plugin is the most actively maintained option, and it exposes the vault over HTTP/SSE for remote clients. If that's more setup than you want, Drive or Notion is the simpler default; sync to your vault afterwards.

### Coming in v1.0

SVG PRISMA flow diagrams committed alongside `audit.md`, thematic concept maps generated from the paper graph, a `comparison.csv` for systematic-review export, Graphify and Firecrawl integration for richer citation networks, and a live-watch view that renders the review as it's being built.

---

## Use what you made <a id="use-what-you-made"></a>

Scriptorium's outputs feed a three-stage pipeline:

> **Scriptorium → Obsidian → NotebookLM**

- **Scriptorium** does the rigorous extraction with audit trail. Every claim locator-cited, every decision logged, contradictions named. This is where defensibility comes from.
- **Obsidian** holds the accumulating knowledge. Multiple reviews link, cross-reference, and live alongside your own notes. This is where you *work* with the literature — draft chapters, follow threads across reviews, notice patterns.
- **NotebookLM** is the publishing endpoint. When you need an Audio Overview for the commute, a deck for committee, or a briefing doc for a meeting, NotebookLM Studio generates it from the corpus you curated in Obsidian. See [Publishing to NotebookLM](#publishing-to-notebooklm).

A few patterns that work:

### Get smart fast on an unfamiliar subject

You have a meeting tomorrow on a topic you don't own. Tonight: run a scoped lit review with `--review-dir` pointing at a new folder in your vault. Morning: run `scriptorium publish --generate audio` to push the corpus to NotebookLM and kick off the podcast. Commute: listen. You show up with the actual literature in your head, not a hot take. This is the single highest-leverage use of Scriptorium for non-dissertation work.

### Stack multiple reviews into a meta-synthesis

Run three targeted Scriptorium reviews — *caffeine and attention*, *caffeine and working memory*, *caffeine and executive function* — all landing in your vault. Obsidian's graph view shows where they touch; Dataview surfaces claims that appear across reviews. Publish all three corpora into one NotebookLM notebook when you want to interrogate the combined literature with Gemini's grounded, citation-backed responses.

### Drop citations straight into your draft

`references.bib` imports cleanly into Zotero, Mendeley, EndNote, or Paperpile. `synthesis.md` is locator-cited markdown — paste it into your draft and every citation token resolves to a real paper. No reconciliation step.

### Re-run as your question evolves

`audit.md` captures the scope, query set, and screening criteria of each run. As your understanding of the literature changes, rerun with adjusted scope. The audit trail preserves the evolution — useful both for your own thinking and for showing a committee how the question matured.

---

## Publishing to NotebookLM <a id="publishing-to-notebooklm"></a>

Google hasn't released an official NotebookLM API, but the community has. Scriptorium integrates with the [`notebooklm-mcp-cli`](https://github.com/jacob-bd/notebooklm-mcp-cli) project (the `nlm` CLI) to automate the push from a finished review to a NotebookLM notebook with Studio artifacts.

### One-time setup

```bash
# Install the notebooklm-cli
uv tool install notebooklm-mcp-cli

# Authenticate once (opens a browser for Google login)
nlm auth login
```

Use a **dedicated Google account** for this, not your primary. The CLI works via browser automation; Google may flag automated activity against a primary account. The author is explicit about this.

### Publishing a review

```bash
scriptorium publish --review-dir ~/vault/reviews/caffeine-wm \
  --notebook "Caffeine and Working Memory" \
  --generate audio
```

This creates a new NotebookLM notebook, uploads PDFs from `review/pdfs/` plus `synthesis.md` and `evidence.jsonl` as sources, and triggers an Audio Overview. `--generate` accepts `audio`, `deck`, `mindmap`, `video`, or `all`. Every upload event — notebook ID, file manifest, artifact IDs — is logged to `audit.md` with a privacy note showing exactly what left your machine.

### Manual path

If you'd rather skip the CLI — or the automation breaks after a Google UI update — the manual path is five minutes:

1. Open [NotebookLM](https://notebooklm.google.com), create a notebook.
2. Upload the PDFs from `review/pdfs/` plus `synthesis.md` and `evidence.jsonl`.
3. Use the Studio panel to generate whatever artifact you need.

Scriptorium doesn't require the CLI; `scriptorium publish` is a convenience wrapper. If it's down, the manual path is always available. [`docs/publishing-notebooklm.md`](docs/publishing-notebooklm.md) includes a template for noting the manual upload in `audit.md` so your record stays consistent either way.

### Tradeoffs of the CLI path

- **Fragility.** Browser automation breaks when Google changes the UI. Expect occasional breakage and patches from the upstream project.
- **Account risk.** Dedicated Google account recommended.
- **Not officially supported.** Google has not endorsed these tools and can disable them at any time.

If any of those are dealbreakers, stay with the manual path. Scriptorium's primary job — producing the defensible review — doesn't depend on any of this.

---

## Where it runs <a id="where-it-runs"></a>

Primary surface is **Claude Code**. Cowork and Codex run the same skills through different adapters.

| Surface       | Invocation                | Search                                             | Full text                            | State home                                                               | Publish to NotebookLM                | Cite-check                    |
|---------------|---------------------------|----------------------------------------------------|--------------------------------------|--------------------------------------------------------------------------|--------------------------------------|-------------------------------|
| Claude Code   | `/lit-review "…"`         | `scriptorium` CLI (OpenAlex, Semantic Scholar)     | Unpaywall · arXiv · PMC · user PDFs  | Plain files in review directory — recommend placing inside Obsidian vault | `scriptorium publish` (via `nlm`)    | Skill step + PostToolUse hook |
| Claude Cowork | *"run a lit review on X"* | Consensus · Scholar Gateway · PubMed MCPs          | PubMed full-text + user uploads      | Obsidian vault (via networked MCP) → Google Drive → Notion → session-only | Manual upload (Cowork can't shell out) | Skill step                    |
| Codex CLI     | `/lit-review "…"`         | CLI (via symlinked skills)                         | Unpaywall · arXiv · PMC · user PDFs  | Plain files in review directory — recommend placing inside Obsidian vault | `scriptorium publish` (via `nlm`)    | Skill step + PostToolUse hook |

Same prose layer, different surfaces. A runtime probe in the `using-scriptorium` meta-skill picks the right path at session start.

NotebookLM is not listed as a state home because it doesn't expose the kind of structured read/write access required to live there; it sits downstream of Scriptorium as a publishing destination.

---

## Install <a id="install"></a>

<details open>
<summary><b>Claude Code (recommended)</b></summary>

```bash
pipx install scriptorium-cli
```

In Claude Code:

```
/plugin marketplace add Jerrymwolf/Scriptorium
/plugin install scriptorium@scriptorium-local
/lit-config
```

Then: `/lit-review "your research question" --review-dir reviews/<slug>`.

</details>

### Migrating from the pre-0.3.1 installer

If you installed Scriptorium before v0.3.1 using the legacy shell script, remove the stale symlink first:

```bash
rm -rf ~/.claude/plugins/scriptorium
```

Then follow the install steps above.

<details>
<summary><b>Claude Cowork</b></summary>

Install the plugin in your Cowork workspace. Recommended connectors:

- **Consensus** — claim-framed search
- **Scholar Gateway** — breadth search
- **PubMed** — biomedical search + OA full text
- **State home:** Obsidian (via [obsidian-claude-code-mcp](https://github.com/iansinnott/obsidian-claude-code-mcp) exposed over HTTP/SSE), **or** Google Drive, **or** Notion

Without a search connector, the plugin falls back to WebFetch against OpenAlex and tells you it's in degraded mode. State home cascades: Obsidian (if configured) → Drive → Notion → session-only. See [`docs/cowork-smoke.md`](docs/cowork-smoke.md) for the full capability matrix.

In any Cowork chat:

> Run a lit review on caffeine and working memory.

</details>

<details>
<summary><b>Codex CLI</b></summary>

Codex CLI is OpenAI's agentic coding CLI. Scriptorium runs there via symlinked skills:

```bash
./scripts/codex_link.sh
```

This populates `.codex/skills/` and `.codex/commands/` as symlinks into `.claude-plugin/`. Point your Codex config at the repo.

</details>

---

## Configure <a id="configure"></a>

```bash
scriptorium config set unpaywall_email you@university.edu
scriptorium config set obsidian_vault ~/vault    # optional; enables relative --review-dir
```

**Required:** `unpaywall_email`. **Optional:** `obsidian_vault`, `openalex_email`, `semantic_scholar_api_key`, `default_backend`, `languages`.

In Cowork, the same config lives as a user-memory note — the `configuring-scriptorium` skill handles it. All writes go through `scriptorium config set KEY VALUE` — never shell-exec.

---

## Scope: what Scriptorium does and doesn't do <a id="scope"></a>

Scriptorium owns the **middle third** of the workflow — search through synthesis. Scoping the question and writing the final chapter stay with you. The cite-check fails closed: unsupported claims get flagged or stripped before commit, so nothing hallucinated ships in your draft.

Scriptorium also doesn't try to be your reference manager, your knowledge base, or your publishing platform. It produces clean outputs that feed into tools that already do those jobs well: Zotero/Mendeley for citations, Obsidian for accumulating knowledge, NotebookLM for Studio artifacts.

**Not in v0.3** — SVG PRISMA flow diagrams, thematic maps, `comparison.csv`, Graphify and Firecrawl integration, risk-of-bias extraction, and a live-watch view are planned for v1.0.

### Status <a id="status"></a>

**Beta (v0.3).** The pipeline is stable and used daily for real dissertation work. CLI flags and skill interfaces may change before 1.0. Breaking changes will be noted in release notes. Fine for dissertation work if you pin a version. Not yet recommended for multi-author systematic reviews where interface stability matters more than iteration speed.

---

## FAQ <a id="faq"></a>

**Does my corpus leave my machine?**
Not by default. In Claude Code or Codex, PDFs and extracted evidence stay local. In Cowork, state is stored in whichever connector you enable (Obsidian MCP, Google Drive, or Notion). `scriptorium publish` is the one operation that uploads your corpus to a third party (Google, via NotebookLM) — and it only runs when you invoke it. Every publish is logged to `audit.md` with a manifest of what was uploaded, so your record of where the corpus has been is always complete.

**What happens when a paper is paywalled?**
Scriptorium cascades: user-dropped PDF → Unpaywall OA version → arXiv preprint → PMC → abstract-only. Abstract-only papers are tagged; synthesis marks claims drawn from abstract as lower-confidence, and the cite-check flags them. You decide whether to chase institutional access.

**Does this replace Zotero / Mendeley / EndNote?**
No. Scriptorium exports BibTeX and RIS that import cleanly. Use your reference manager for the library you keep; use Scriptorium for the review you're writing now.

**Why Obsidian specifically? Why not [other note app]?**
Obsidian vaults are just folders of markdown — the format Scriptorium already produces, so there's zero translation overhead. Any tool that reads a folder of markdown works: Logseq, Foam, the new generation of Zettelkasten tools, even just VS Code with a markdown preview. Obsidian gets the call-out because its graph view, Dataview, and backlink ecosystem are the most mature for the kind of cross-review synthesis Scriptorium enables.

**Does this replace NotebookLM?**
No. They're complementary. Scriptorium produces a locator-cited synthesis with a full audit trail; NotebookLM is a conversational interface plus Studio artifact generator over a source set you curate. The pipeline is Scriptorium (rigor) → Obsidian (working knowledge) → NotebookLM (publishing artifacts).

**What's the legal posture on ingesting PDFs?**
Scriptorium retrieves open-access full text via Unpaywall, arXiv, and PMC — all legitimately OA sources. PDFs you drop into the review directory are your responsibility; Scriptorium doesn't redistribute them and doesn't phone home with their contents.

**Can I use it for a systematic review (Cochrane-style)?**
The audit trail supports the transparency requirements. Scriptorium doesn't yet generate PRISMA 2020 flow diagrams as SVG (planned for v1.0), and it doesn't currently handle risk-of-bias extraction. For a full Cochrane review, treat Scriptorium as a screening-and-extraction assistant, not a replacement for Covidence or RevMan.

**How much does it cost to run?**
Scriptorium itself is MIT-licensed and free. You need an existing Claude (Code / Cowork) or ChatGPT (Codex) plan. Optional API costs: Semantic Scholar is free with a key; OpenAlex is free; NotebookLM Studio outputs are quota-metered by Google.

---

## Cite Scriptorium in your methods chapter <a id="cite-scriptorium"></a>

Drop-in methods-section language:

> Literature identification, screening, and extraction were conducted using Scriptorium v0.3 (Wolf, 2026), a workflow tool that logs every search query, screening decision, and extraction call to a PRISMA-style audit trail. Claims in the synthesis carry locator-level citations (`[paper_id:page:N]`) resolved against an evidence ledger; a final cite-check pass flags or removes unsupported claims before the draft is committed. Contradictions between sources are surfaced by camp rather than averaged.

BibTeX:

```bibtex
@software{scriptorium2026,
  author  = {Wolf, Jerry},
  title   = {Scriptorium: a literature review workflow you can defend},
  year    = {2026},
  version = {0.3},
  url     = {https://github.com/jerrymwolf/scriptorium}
}
```

---

## Design, develop, license, credits <a id="design-docs"></a>

**Design spec:** [`docs/superpowers/specs/2026-04-19-superpowers-research-design.md`](docs/superpowers/specs/2026-04-19-superpowers-research-design.md)
**Cowork capability matrix:** [`docs/cowork-smoke.md`](docs/cowork-smoke.md)
**Obsidian integration:** [`docs/obsidian-integration.md`](docs/obsidian-integration.md)
**Publishing to NotebookLM:** [`docs/publishing-notebooklm.md`](docs/publishing-notebooklm.md)
**Changelog:** [`CHANGELOG.md`](CHANGELOG.md)

### Develop

```bash
pip install -e ".[dev]"
pytest
```

Runs the full suite — adapter unit tests, CLI integration tests, skill/command content tests, the end-to-end caffeine fixture in `tests/test_e2e_caffeine.py`, and mocked `nlm` tests for the `publish` subcommand.

### License

MIT.

### Credits

Scriptorium is architected in the style of **[Superpowers](https://github.com/obra/superpowers)** by Jesse Vincent — self-contained skill folders with `SKILL.md` files that Claude loads on demand. The pattern is *Superpowers*; the application to literature review is *Scriptorium*.

The NotebookLM publishing integration wraps **[`notebooklm-mcp-cli`](https://github.com/jacob-bd/notebooklm-mcp-cli)** by Jacob Ben-David. Scriptorium shells out to `nlm`; it does not vendor, embed, or modify that project.
