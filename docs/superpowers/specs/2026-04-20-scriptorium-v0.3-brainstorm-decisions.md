---
status: brainstorm-complete
next: write full design spec at docs/superpowers/specs/2026-04-20-scriptorium-v0.3-design.md
supersedes: scriptorium-v0.2.1-spec.md (absorbed into v0.3)
source_inputs: [README_proposed.md, scriptorium-v0.2.1-spec.md]
---

# Scriptorium v0.3.0 — brainstorm decisions

Locked decisions from the 2026-04-20 brainstorm session. The next session should read this, the project README_proposed.md, and scriptorium-v0.2.1-spec.md, then write the full design spec.

## Version

**v0.3.0**, status badge `beta` (not alpha). Interface stability commitment through 1.0 — CLI flags, skill interfaces, config keys don't change without deprecation. SemVer discipline: 0.3.x = bug fixes; 0.4.0 = additive features; breaking changes require 1.0.

## Scope — what's in v0.3

Carried forward from the (now superseded) v0.2.1 spec:
- `obsidian_vault` config key + vault detection (walk-up for `.obsidian/`)
- `scriptorium publish` subcommand + nlm CLI integration
- Cowork degradation block for publish
- Audit.md YAML frontmatter + publishing entries
- All v0.2.1 tests (vault detection, publish flow, config resolution)

Pulled forward from the deferred list into v0.3:
- Claude-Code-assisted install (`/scriptorium-setup` + curl fallback)
- Native Obsidian output (paper stubs, wikilinks, frontmatter, Dataview queries)
- Executive briefing (`overview.md`)
- Seamless NotebookLM flow (end-of-review prompt + standalone `/lit-*` commands)
- PyPI first release

Still deferred to v0.4+:
- Graphify/Firecrawl integration
- PRISMA SVG flow diagrams
- Thematic maps
- `comparison.csv`
- Live-watch view
- In-place update of existing NotebookLM notebooks

## Section 1 — Scope & output shape

**Output directory** (vault detected):

```
vault/
├── scriptorium-queries.md      ★ vault-scoped Dataview queries, shipped once
├── papers/                     ★ vault-wide aggregated stubs (per-review fallback if no vault)
│   ├── nehlig2010.md
│   └── ...
└── reviews/caffeine-wm/
    ├── overview.md             ★ front-door briefing, briefing-grade cites
    ├── audit.md                * YAML frontmatter
    ├── evidence.jsonl
    ├── synthesis.md            * frontmatter + [[wikilinks]]
    ├── contradictions.md       * frontmatter + [[wikilinks]]
    ├── references.bib
    └── pdfs/
```

No vault detected: paper stubs and queries fall back into the review dir.

Surfaces unchanged: Claude Code (primary), Codex CLI (symlinked skills), Cowork (degraded — no shell, Section 5 block on publish attempts).

## Section 2 — Install flow

**Prereq:** v0.3 ships on PyPI. First PyPI release for the project.

**Claude Code path** — `/scriptorium-setup` slash command + skill orchestrates:
1. Precheck (Python 3.11+, writable `~`)
2. `uv pip install scriptorium` (or `pip` fallback)
3. Install `.claude-plugin/` into CC's plugin dir; prompt for restart
4. Obsidian vault: scan common paths (`~/Documents/Obsidian/`, `~/Obsidian/`, iCloud), detect `.obsidian/`, confirm / pick / create-at-default / skip
5. Capture `unpaywall_email` via AskUserQuestion
6. Optional NotebookLM: `uv tool install notebooklm-mcp-cli` + dedicated-Google-account note + `nlm auth login`
7. Run `scriptorium doctor`
8. Print: "You're set. Try `/lit-review 'your question' --review-dir reviews/<slug>`"

**Non-CC path** — `curl -fsSL install.scriptorium.dev | bash` runs equivalent `scriptorium init` wizard at terminal. Same steps, text-only.

**Failure handling:** each step surfaces concrete recovery text. NotebookLM failure doesn't block setup (stores `notebooklm_enabled: false`, user can rerun `scriptorium setup --notebooklm`).

**Idempotent** — rerunning detects existing state, offers per-piece reconfig.

**Cowork**: no shell access; users install outside Cowork, configure via `configuring-scriptorium` skill modifying a user-memory note.

**Cuttable:** curl installer. CC-first audience makes it marginal coverage.

## Section 3 — Native Obsidian output

**Default, not a flag.** No `--obsidian-mode` toggle. Wikilinks and frontmatter degrade gracefully in non-Obsidian viewers.

**Frontmatter** — only fields Dataview queries read. Per paper stub:
```yaml
paper_id: nehlig2010
authors: ["Nehlig, A."]
year: 2010
doi: 10.1093/ajcn/84.6.1246
tags: [caffeine, attention]
reviewed_in: [caffeine-wm, caffeine-attention]
```
Review files carry `review_id`, `created_at`, `research_question`, `cite_discipline`.

**Paper stubs** — `papers/<paper_id>.md`, vault-wide when vault detected, per-review fallback otherwise. Structure: frontmatter + title/authors/DOI + PDF link + abstract + per-page H2 anchors (`## p-4`, only for pages actually cited) with cited quotes + auto-populated "Claims in review: <slug>" section (aggregated across reviews when vault-wide).

**Wikilink locator format** — `[[nehlig2010#p-4]]` replaces `[nehlig2010:page:4]` in `overview.md`, `synthesis.md`, `contradictions.md`. Click in Obsidian jumps to the quote.

Cite-check hook dual-parses — v0.2.0 legacy `[paper_id:page:N]` tokens stay valid, no forced migration.

**Dataview queries** — shipped at vault root as `scriptorium-queries.md` on first vault use (idempotent). Vault-scoped since queries aggregate across reviews.

**Portability tradeoff accepted:** vault-wide stubs mean review dirs aren't self-contained. Ship `scriptorium export <review-dir>` later (cuttable in v0.3) to bundle a review with its referenced stubs into a tarball.

**Cuttable:** `scriptorium migrate-locators` — dual-parse handles legacy reviews; users can find/replace manually.

## Section 4 — Executive briefing (`overview.md`)

**Epistemic reframe (load-bearing):** overview summarizes THIS REVIEW'S CORPUS, not the field. Every section bounded by what the review retrieved. Two statement classes:
- Paper claim quoted/paraphrased → `[[paper_id#p-N]]` required
- Synthesis/interpretation (rankings, camp naming, corpus framing) → `<!-- synthesis -->` tag; NO paper-level cite that implies source support

**Generation** — one post-hoc LLM pass after cite-check passes on `synthesis.md` and `contradictions.md`. Reads those plus `evidence.jsonl`. Frontmatter records `model_version`, `generation_seed`, `generation_timestamp`, `corpus_hash`. Regeneration archives prior version to `overview-archive/<timestamp>.md`.

**Reproducibility caveat stated in frontmatter:** same corpus + same model + recorded seed yields *materially similar* (not bit-identical) output.

**Sections — scope-bounded names:**

| Section | Framing |
|---|---|
| TL;DR | One-sentence answer from corpus, confidence-tagged (strong/mixed/unresolved) |
| Scope & exclusions | Question, timeframe, languages; pointer to `audit.md` |
| Most-cited works in this corpus | Papers most-cited across synthesis — corpus's canon, not field's |
| Current findings | Sub-question → claim → direction → locator |
| Contradictions in brief | 1-3 biggest; pointer to `contradictions.md` |
| Recent work in this corpus (last 5 years) | What recent corpus papers add |
| Methods represented in this corpus | Methodologies in this corpus, not field-level claim |
| Gaps in this corpus | Questions this corpus doesn't answer |
| Reading list | 5-10 papers, ranking formula stated inline |

Three sections renamed from the initial draft to prevent field-level overreach.

**Provenance per section:** HTML-comment block at each section end:
```html
<!-- provenance: section=most-cited-works; contributing_papers=[nehlig2010, smith2018]; derived_from=synthesis.md §2 -->
```

**Reading list ranking formula, stated inline:** *"Ranked by: citation frequency in this review's synthesis (weight 0.6) + LLM-assessed salience given research question (weight 0.4). Weights in frontmatter."* Legible, not magic.

**Length target:** ~300 words, readable in 90 seconds. Prompt constraint; no hard cap.

**Failure mode:** no overview.md written on failure, error to `audit.md`, rerun via `scriptorium regenerate-overview`. User edits preserved via archive-on-regenerate.

**Front-door semantics:** `overview.md` sorts alphabetically before `synthesis.md`. Users can pin/star in Obsidian. No plugin dependency.

**Cuttable:** provenance blocks (belt-and-suspenders; section renames close 70% of scope-overreach risk alone).

## Section 5 — NotebookLM flow

**Two entry points, one underlying CLI.**

**Entry 1: End-of-review prompt (option B).** After `/lit-review` generates `overview.md` and cite-check passes, fires AskUserQuestion: `audio / deck / mindmap / skip` (skip default-selected). Only fires when three gates pass:
- nlm installed AND authenticated (runtime-detected)
- `notebooklm_prompt` config not false
- cite-check passed

**Entry 2: Standalone commands (option D).** After-the-fact generation on any review dir:
- `/lit-podcast <review-dir>` → `scriptorium publish --review-dir <path> --generate audio`
- `/lit-deck <review-dir>` → `scriptorium publish --review-dir <path> --generate deck`
- `/lit-mindmap <review-dir>` → `scriptorium publish --review-dir <path> --generate mindmap`

**Default source set (revised from v0.2.1):**
- `overview.md` (new)
- `synthesis.md`
- `contradictions.md` (new, was implicit)
- `evidence.jsonl`
- `pdfs/*.pdf`

Paper stubs deliberately excluded — derivative of PDFs+evidence, and NotebookLM's ~50-source cap means stubs would starve PDFs. Override via `--sources`.

**Status visibility:** upload synchronous, artifact generation async. Return notebook URL immediately after upload; audit.md logs "Audio Overview queued (artifact_id: ...)". No blocking wait.

**Update flow:** rerunning on existing notebook triggers v0.2.1 idempotency prompt. v0.3 always creates new on `y`. In-place update is v0.4.

**Surface impact:**
| Runtime | End-of-review prompt | Standalone `/lit-*` |
|---|---|---|
| Claude Code | Full flow | Full flow |
| Codex CLI | Full flow via symlinked skill | Full flow |
| Cowork | Fires, emits manual-upload block (no shell) | Same block; never calls nlm |

Cowork prompt firing is a feature — presents upload bundle + manual instructions at right workflow moment.

**Cuttable:** three `/lit-*` standalone commands. Keep end-of-review prompt + `scriptorium publish` CLI; users run the CLI directly. Saves three command files + tests.

## Section 6 — Version & migration

**v0.3.0, beta.** First PyPI release.

**PyPI publish flow:**
1. Tag `v0.3.0-rc1` → Test-PyPI via GitHub Actions
2. Smoke-test from Test-PyPI against caffeine fixture
3. Tag `v0.3.0` → PyPI
4. Plugin marketplace deferred until marketplace exists

**Breaking changes vs. v0.2.0 — zero for existing reviews.** Dual-parse cite-check, additive format changes, backward-compat output.

**Migration — explicit, not auto:**
```bash
scriptorium migrate-review reviews/caffeine-wm
# Migrates tokens → wikilinks; generates paper stubs; adds frontmatter
# Does NOT regenerate overview.md (run regenerate-overview separately)
```

Auto-migration on read rejected — surprise file mutations violate audit-trail principle.

**Install path for existing v0.2.0 users:**
```bash
pip install -U scriptorium
/scriptorium-setup   # idempotent
```

**Docs updated:**
- `docs/publishing-notebooklm.md` (new, from v0.2.1 + extended for /lit-* commands)
- `docs/obsidian-integration.md` (new, from v0.2.1 + extended with paper-stub + wikilink semantics)
- `docs/cowork-smoke.md` (updated for v0.3 surface impacts)
- `README.md` (replaced with README_proposed.md contents, status text updated for beta)
- `CHANGELOG.md` (v0.3.0 entry)

**Rollout risks + mitigations:**
1. nlm CLI version drift — verify against `nlm --help` before implementing publish path
2. PyPI first-release friction — Test-PyPI rehearsal before `v0.3.0` tag
3. Obsidian vault detection false positives (Dropbox conflicts, symlinks) — behavior is log-and-continue, tests inherited from v0.2.1

**Cuttable:** `scriptorium migrate-review`. Dual-parse makes legacy reviews functional without it.

## Open verification tasks (surface at spec-write time)

1. `nlm --help` — verify subcommand names against the Jan 2026 refactor before locking Section 5 CLI mapping.
2. Existing `lit-publishing` skill — check whether it exists; if yes, rename to `publishing-to-notebooklm/SKILL.md` per v0.2.1 spec §4.
3. `/lit-publish` command — check existing `.claude-plugin/commands/` pattern before naming the new `/lit-podcast`, `/lit-deck`, `/lit-mindmap` commands to match or diverge knowingly.
4. PyPI package name — verify `scriptorium` is available on PyPI; fall back to `scriptorium-cli` or similar if squatted.

## Handoff — next session

1. Read this file + `README_proposed.md` + `scriptorium-v0.2.1-spec.md`.
2. Run the four verification tasks above; note findings at top of the spec.
3. Write the full design spec to `docs/superpowers/specs/2026-04-20-scriptorium-v0.3-design.md`.
4. Self-review loop (placeholders, contradictions, ambiguity, scope).
5. Present to Jerry for final review.
6. On approval, invoke `superpowers:writing-plans` to create the implementation plan.
