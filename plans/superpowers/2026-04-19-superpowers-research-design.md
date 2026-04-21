# Superpowers-Research — Design Spec

**Date:** 2026-04-19
**Status:** Approved (brainstorming), pending implementation plan
**Author:** Jeremiah Wolf + Claude (brainstorming session)

## Purpose

A Claude Code + Cowork plugin that replaces Elicit for doctoral literature reviews. Applies the superpowers methodology (discipline, verification, composable skills) to the literature-review workflow. Token-light like superpowers; trustworthy where Elicit is shallow.

**Non-goals.** Not a systematic-review authoring suite; not a replacement for Rayyan/Covidence/Zotero; not a writing tool. Students bring the research question; the plugin finds and synthesizes the literature.

## Locked decisions (from brainstorming)

1. **Audience:** domain-neutral, any doctoral student. Public plugin day one.
2. **Scope:** phases 2–6 of the lit-review lifecycle (search → synthesis). Scoping and writing stay with the student.
3. **Search backends:** OpenAlex default, Semantic Scholar opt-in, behind a common adapter.
4. **Rigor mechanisms:** all three layered — evidence-first claims, PRISMA audit trail, contradiction surfacing.
5. **Graphify:** optional soft integration. If installed, synthesis upgrades with thematic clusters + landmark detection. Otherwise graceful fallback. A separate "Research Bundle" meta-plugin pins compatible versions of both.
6. **Full-text access:** Unpaywall + OA (arXiv/PMC) + user-dropped PDFs default. Firecrawl configurable.
7. **Structure:** Approach 3 hybrid. One `/lit-review` orchestrator command on top of composable auto-triggering skills.
8. **Cowork compatibility:** first-class. Same bundle in both Claude Code marketplace and Cowork plugin library.

## Section 1 — Plugin architecture

Plugin layout (cross-compatible Claude Code + Cowork bundle):

```
superpowers-research/
├── .claude-plugin/         # plugin manifest
├── .codex/                 # Codex adapter (parity with superpowers)
├── CLAUDE.md               # agent operating instructions
├── skills/
│   ├── using-research-superpowers/
│   ├── lit-searching/
│   ├── lit-screening/
│   ├── lit-extracting/
│   ├── lit-synthesizing/
│   ├── lit-contradiction-check/
│   └── lit-audit-trail/
├── commands/
│   ├── lit-review.md
│   ├── lit-add-pdf.md
│   ├── lit-show-audit.md
│   ├── lit-export-bib.md
│   └── lit-config.md
├── agents/                 # optional subagents for parallel extraction
├── hooks/                  # enforce rigor gates (evidence-first check post-synth)
├── mcp/                    # MCP server (Python) — the tool layer
│   ├── server.py
│   ├── tools/
│   │   ├── sources/        # openalex.py, semantic_scholar.py, base.py
│   │   ├── fulltext/       # unpaywall.py, arxiv.py, pmc.py, user_pdf.py, firecrawl.py
│   │   ├── evidence.py     # claim-source ledger
│   │   ├── audit.py        # PRISMA trail writer
│   │   └── graphify.py     # optional bridge
│   ├── pyproject.toml
│   └── requirements.txt
├── scripts/                # install, test, bundle
├── tests/                  # fixtures + unit tests with mocked APIs
└── docs/superpowers/specs/ # design docs (this file)
```

**Runtime split.**
- **Prose layer** (skills + commands + CLAUDE.md + hooks): the discipline; what the agent reads.
- **Tool layer** (`mcp/`): deterministic work (API calls, PDF parsing, ledger writes, PRISMA logs). Exposed via MCP so it works in both Claude Code and Cowork. Load-bearing for the token-light promise — work that lives here is tokens the model doesn't spend.

**Distribution.** Published to the Claude plugin marketplace and the Cowork plugin library. Also installable by URL.

## Section 2 — Skills & commands catalog

### Skills (auto-triggering)

| Skill | Triggers when agent sees... | Does |
|---|---|---|
| `using-research-superpowers` | session start | loads meta-instructions: when to invoke which lit skill, evidence discipline rules, PRISMA principle |
| `lit-searching` | "find papers on…", DOI lists, research questions | queries OpenAlex/SS, dedupes, persists corpus |
| `lit-screening` | after search + inclusion/exclusion criteria | applies rules to title/abstract/year/lang, logs keep/drop + reason |
| `lit-extracting` | kept papers without extracted fields | pulls claim, method, N, population, outcomes, limitations, quotes with locators from abstract → OA PDF → user PDF |
| `lit-synthesizing` | question answerable from ledger | writes narrative; every sentence carries `paper_id + locator`; unsupported claims removed or flagged |
| `lit-contradiction-check` | synthesis step sees disagreeing extractions | refuses smoothed consensus, names camps with sources, hands interpretation to the student |
| `lit-audit-trail` | side-effect of every other skill | appends PRISMA-style entry per pipeline step |

### Commands

- `/lit-review "<question>"` — orchestrator running the full pipeline. One-shot Elicit-replacement path. Optional `--visual` flag activates the Layer 2 browser companion (see Section 6).
- `/lit-add-pdf <path>` — register user PDF to corpus, match or create paper node.
- `/lit-show-audit` — print current PRISMA trail.
- `/lit-show-live` — activate Layer 2 browser companion for the current review (same view as `--visual`).
- `/lit-export-bib` — dump corpus as BibTeX + RIS.
- `/lit-config` — chat-driven config dialogue (no TOML editing).

### Intentional omissions (YAGNI)

- No separate `lit-pdf-extract` — PDF is just another source to `lit-extracting`.
- No scoping or writing skills — out of scope.
- No search-refinement skill — handled conversationally in v0.1; promote to skill only if usage patterns demand it.

## Section 3 — Data flow

Pipeline (sequence):
```
user question → scope-check → lit-searching → lit-screening
  → lit-extracting (cascade: abstract → Unpaywall → arXiv/PMC → user PDF → Firecrawl)
  → lit-synthesizing (optionally augmented by Graphify)
  → lit-contradiction-check
  → outputs
```

Side effects (continuous):
- `lit-audit-trail` appends every step to `audit.md` + `audit.jsonl`.
- Persistent stores: `corpus.jsonl`, `evidence.jsonl`, `pdfs/`, `extracts/`.

Outputs:
- `synthesis.md` (inline `[paper_id:locator]` citations)
- `outputs/prisma.svg` (PRISMA 2020 flow)
- `outputs/comparison.csv` (Elicit-style column view: paper × method × N × finding × limitations)
- `outputs/themes.svg` (only if Graphify is present)
- `bib/export.bib` + `export.ris`

## Section 4 — State & storage

### Per-review state (lives next to the dissertation)

```
<review-dir>/
├── review.md           # question, scope, criteria
├── synthesis.md        # cited narrative output
├── audit.md            # PRISMA trail (human-readable)
├── audit.jsonl         # PRISMA trail (machine-readable)
├── corpus.jsonl        # papers + status
├── evidence.jsonl      # append-only claim → paper + locator + quote
├── extracts/<id>.json  # per-paper extracted fields (inspectable)
├── pdfs/<id>.pdf       # cached OA + user PDFs
├── outputs/            # prisma.svg, comparison.csv, themes.svg
└── bib/                # export.bib, export.ris
```

### Global config

`~/.config/superpowers-research/config.toml` — Unpaywall email (required), OpenAlex polite-pool email, SS key (optional), Firecrawl key (optional), default backend, language, Graphify on/off.

### Format principles

- Markdown for human artifacts (synthesis, audit, review scope).
- JSONL for append-only ledgers (crash-safe, greppable, diff-friendly).
- SVG for diagrams (editable in vector tools for dissertation polish).
- CSV for tables.
- **No SQLite, no database.** Breaks Cowork's "no infrastructure" promise; unnecessary at lit-review scale (typically <500 papers).

MCP server is stateless. All state lives in files. Multi-review via working-directory detection or explicit `--review <path>`. Default `.gitignore` excludes `pdfs/` and `extracts/`.

## Section 5 — Rigor mechanisms

Three disciplines, shared infrastructure (`evidence.jsonl`), hook-based enforcement.

### Mechanism 1 — Evidence-first claims (TDD analog)

Fires after `lit-synthesizing` writes `synthesis.md`. A hook parses every sentence, extracts citation tokens, verifies each resolves to a live `evidence.jsonl` entry with quote + locator.

- **Default mode (strict):** unsupported sentences are removed from `synthesis.md`.
- **Lenient mode** (opt-in via config): unsupported sentences kept but flagged inline as `[UNSUPPORTED]`. Student reviews before ship.

**Prevents:** Elicit-style hallucinated citations.

### Mechanism 2 — PRISMA audit trail (verification-before-completion analog)

Continuous side effect. Every skill invocation appends to `audit.md` + `audit.jsonl`. Captures query → retrieved → screened (in/out + reasons) → extracted → synthesized. `/lit-show-audit` prints trail. Auto-generates PRISMA 2020 flow diagram (`outputs/prisma.svg`).

**Prevents:** unreproducibility; committee asking "how did you get this set of papers?" and having no answer.

### Mechanism 3 — Contradiction surfacing (systematic-debugging analog)

Fires after `lit-synthesizing`, before ship. `lit-contradiction-check` scans the evidence ledger for pairs of claims on the same concept with opposing direction. When found, rewrites the affected synthesis section with named camps + both sources + no declared winner.

**Prevents:** smoothed-over consensus that buries real disagreement.

## Section 6 — Integrations, from the student's view

**Core principle:** the student never sees an "adapter." Everything surfaces as conversation.

### First-run setup (one question, zero config)

Install from marketplace. First `/lit-review` asks for the student's email once (required by Unpaywall ToS). That's it. OpenAlex needs no key.

### Provenance visible in the synthesis

Every citation carries a source tag:
> "Moderate caffeine doses improve working-memory accuracy (Smith 2023, p.4) `[OpenAlex · Unpaywall OA]`."

Tag shows where the paper came from and how full text was retrieved. Yellow tag indicates abstract-only.

### Access-gap handling (plain English)

When some full text is unavailable:
> "I got full text for 28 of 42 papers. For the other 14, I only have abstracts. Three options: drop PDFs into `<path>`, enable Firecrawl (paid), or continue abstracts-only."

Student types a reply. No menus, no settings panels.

### Optional upgrades surface once

Graphify / Semantic Scholar / Firecrawl each offer themselves with a single sentence the first time they would help, then stay out of the way. One-click consent; "don't ask again" respected.

### Config is a conversation

`/lit-config` opens a chat dialogue; the plugin writes changes behind the scenes. No TOML editing.

### Visual companion — layered

**Layer 1 — Exportable artifacts (always on):**
- PRISMA flow diagram (required for dissertation appendix)
- Thematic cluster map (if Graphify)
- Comparison table (Elicit-style column view)
- Evidence ledger (claim → source + locator)

Exported as PNG/SVG/CSV/Markdown.

**Layer 2 — Live browser companion (opt-in):**
Invoked via `/lit-review --visual` or `/lit-show-live`. Browser shows running pipeline: funnel filling during screening, extraction queue with accept/modify/reject, contradiction pair-viewer with side-by-side quotes, theme reassignment drag-and-drop. Off by default because Cowork is already a desktop app; terminal users can flip it on per-review.

## Section 7 — Testing & release

### Testing

- **Adapter unit tests:** each source/fulltext adapter against recorded fixtures. Real API calls only in a nightly smoke job.
- **Skill activation tests:** LLM eval harness validates trigger conditions.
- **End-to-end fixture:** canonical "caffeine + working memory" review runs against a frozen OpenAlex snapshot; outputs diffed against known-good.
- **Rigor-gate tests:** synthetic drafts with planted unsupported claims must be caught; planted contradictions must trigger the checker. Binary pass/fail — load-bearing guarantees.
- **Token-budget regression:** per-phase counts logged for the fixture review; CI fails on >15% growth without justification. Protects the token-light promise.
- **Cross-platform:** every PR runs the fixture review in both Claude Code and a Cowork-compatibility harness.

### Release

- **Primary:** Claude plugin marketplace — `/plugin install superpowers-research`.
- **Secondary:** Cowork plugin library submission.
- **Bundle:** separate "Research Bundle" meta-plugin pinning compatible versions of `superpowers-research` + Graphify. One-click for users who want both.
- **Versioning:** semver. `v0.x` = private beta with a handful of doctoral students. `v1.0` requires: fixture review passes end-to-end, evidence-first gate 100% on synthetics, PRISMA 2020 diagram renders to spec, token budget measured and documented.

### v0.1 beta vs v1.0 scope

| Capability | v0.1 | v1.0 |
|---|---|---|
| Search (OpenAlex) | ✓ | ✓ |
| Search (Semantic Scholar) | ✓ | ✓ |
| Screening + extraction | ✓ | ✓ |
| Unpaywall + user PDFs | ✓ | ✓ |
| Synthesis + evidence-first gate | ✓ | ✓ |
| PRISMA audit trail (text) | ✓ | ✓ |
| PRISMA 2020 diagram export | — | ✓ |
| Contradiction check | basic | polished |
| Graphify integration | ✓ (if installed) | ✓ |
| Firecrawl integration | — | ✓ |
| Cowork submission | — | ✓ |
| Research Bundle meta-plugin | — | ✓ |

## Open threads (to resolve during implementation planning)

- Exact PRISMA 2020 diagram generator (matplotlib? d3? pre-built template?).
- Subagent strategy for parallel extraction — whether to use superpowers' subagent-driven-development patterns for the extraction loop, given corpus sizes >50 papers.
- Skill activation telemetry — do we instrument which skills fire in which order during v0.1 to tune triggers before v1.0?
- Where to host the frozen OpenAlex fixture snapshot (size estimate TBD).

## References

- [obra/superpowers](https://github.com/obra/superpowers) — parent methodology
- [safishamsi/graphify](https://github.com/safishamsi/graphify) — optional synthesis integration
- [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) — Cowork plugin templates
- [PRISMA 2020 statement](http://www.prisma-statement.org/) — systematic-review reporting standard
- [OpenAlex docs](https://docs.openalex.org/) — default search backend
- [Unpaywall API](https://unpaywall.org/products/api) — OA full-text retrieval
