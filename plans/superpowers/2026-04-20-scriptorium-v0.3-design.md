---
status: audited-revised
supersedes: scriptorium-v0.2.1-spec.md
derives_from: 2026-04-20-scriptorium-v0.3-brainstorm-decisions.md
target_release: v0.3.0
status_badge: beta
next: invoke superpowers:writing-plans to produce docs/superpowers/plans/2026-04-20-scriptorium-v0.3.md
---

# Scriptorium v0.3.0 — Design Spec

**Mode: build. Flag scope creep, don't absorb it.**

This spec is the implementation contract for Scriptorium v0.3.0. It absorbs `scriptorium-v0.2.1-spec.md`, the locked brainstorm decisions in `docs/superpowers/specs/2026-04-20-scriptorium-v0.3-brainstorm-decisions.md`, the user-facing contract in `README_proposed.md`, and the current repo facts verified on 2026-04-20.

A fresh engineer with no repo context should be able to produce a task-by-task implementation plan from this file alone. There are no open design questions in this spec; remaining choices are recorded as judgment calls in the self-review log.

---

## 0. Ground Truths

### 0.1 Repo facts to preserve

- Python package directory: `scriptorium/` at repo root. This is a flat layout, not `src/`.
- Current `pyproject.toml`: `name = "scriptorium"`, `version = "0.2.0"`, console script `scriptorium = "scriptorium.cli:main"`.
- v0.3 release target: package distribution name becomes `scriptorium-cli`, version becomes `0.3.0`, console script remains `scriptorium`, import path remains `scriptorium`.
- `.claude-plugin/commands/` currently holds `lit-*.md` command files.
- `.claude-plugin/skills/` currently holds skill directories including `lit-publishing/`; v0.3 renames that skill to `publishing-to-notebooklm/`.
- `.claude-plugin/hooks/evidence_gate.sh` exists and remains the single hook surface; v0.3 changes its underlying cite parser, not the hook filename.

### 0.2 Verified `nlm` CLI surface

The installed `nlm` CLI is verified on 2026-04-20. v0.3 must call exactly these subcommands:

| Purpose | Command |
|---|---|
| Login | `nlm login` |
| Diagnose install/auth | `nlm doctor` |
| Create notebook | `nlm notebook create <title>` |
| Upload source | `nlm source add <id> --file <path>` |
| Create audio | `nlm audio create <id>` |
| Create slide deck | `nlm slides create <id>` |
| Create mind map | `nlm mindmap create <id>` |
| Create video | `nlm video create <id>` |

Do not use stale authentication aliases, confirmation flags on audio generation, or Studio-generation command shapes from v0.2.1 or README examples. v0.3 implementation, tests, docs, and skills must use only the commands in the table above.

### 0.3 PyPI naming

The PyPI distribution name `scriptorium` is unavailable for this project. v0.3 publishes as `scriptorium-cli`. User-facing project name remains "Scriptorium"; command remains `scriptorium`; Python import path remains `scriptorium`.

### 0.4 Slash command naming

Existing slash commands use `.claude-plugin/commands/lit-*.md`. v0.3 adds:

- `.claude-plugin/commands/lit-podcast.md`
- `.claude-plugin/commands/lit-deck.md`
- `.claude-plugin/commands/lit-mindmap.md`
- `.claude-plugin/commands/scriptorium-setup.md`

User-facing "deck" maps internally to `nlm slides create <id>`.

---

## 1. Scope

### 1.1 In v0.3.0

Carried forward from v0.2.1:

- `obsidian_vault` config key and vault detection by walking up for `.obsidian/`.
- `scriptorium publish` subcommand with NotebookLM publishing via verified `nlm` CLI.
- Cowork degradation block for publish attempts.
- YAML frontmatter on `audit.md` and publishing audit entries.
- v0.2.1 tests for vault detection, publish flow, config resolution, partial publish, and Cowork degradation.

Pulled forward from the v0.3 brainstorm:

- Claude-Code-assisted install via `/scriptorium-setup` and `setting-up-scriptorium` skill.
- Terminal fallback via `scriptorium init`; curl one-liner is a release-engineering wrapper around that command.
- Native Obsidian output by default: paper stubs, wikilinks, frontmatter, Dataview queries.
- Executive briefing artifact: `overview.md`.
- Seamless NotebookLM flow: end-of-review prompt and standalone `/lit-podcast`, `/lit-deck`, `/lit-mindmap`.
- First PyPI release as `scriptorium-cli`.

### 1.2 Out of v0.3.0

- Graphify or Firecrawl integration.
- PRISMA SVG flow diagrams.
- Thematic maps across reviews.
- `comparison.csv` cross-paper matrices.
- `scriptorium watch` or live view.
- In-place update of existing NotebookLM notebooks.
- Multi-reviewer merge support.
- NotebookLM as a Scriptorium state home.
- An in-repo Obsidian MCP server.
- Automatic migration of old reviews on read.
- `scriptorium export <review-dir>`.

---

## 2. Output Layout

### 2.1 Vault detected

When a resolved review directory is inside an Obsidian vault, v0.3 writes:

```text
<vault>/
├── .obsidian/                         # existing user directory, untouched
├── scriptorium-queries.md             # written once, idempotent
├── papers/                            # vault-wide paper stubs
│   └── nehlig2010.md
└── reviews/
    └── caffeine-wm/
        ├── overview.md
        ├── audit.md
        ├── audit.jsonl
        ├── corpus.jsonl
        ├── evidence.jsonl
        ├── synthesis.md
        ├── contradictions.md
        ├── references.bib
        └── pdfs/
            └── nehlig2010.pdf
```

`papers/` is vault-wide. The same paper stub can accumulate "Claims in review" sections for multiple reviews.

### 2.2 No vault detected

When no `.obsidian/` ancestor exists and `obsidian_vault` is unset or invalid for the invocation, v0.3 writes:

```text
<review-dir>/
├── overview.md
├── scriptorium-queries.md             # review-scoped fallback copy
├── papers/                            # per-review stubs
│   └── nehlig2010.md
├── audit.md
├── audit.jsonl
├── corpus.jsonl
├── evidence.jsonl
├── synthesis.md
├── contradictions.md
├── references.bib
└── pdfs/
```

No-vault mode is fully functional plain Markdown. Obsidian-specific wikilinks remain human-readable.

### 2.3 Portability tradeoff

Vault-wide stubs mean a vault-based review directory is not self-contained. v0.3 documents this in `docs/obsidian-integration.md`; users who need self-contained review folders should avoid setting `obsidian_vault`. Bundling referenced stubs is deferred to `scriptorium export <review-dir>` in v0.4+.

---

## 3. Config Contract

### 3.1 Storage and load order

Config is TOML under a `[scriptorium]` table.

Load order for Claude Code and terminal CLI:

1. Built-in defaults from `scriptorium.config.Config`.
2. Repo/review config file at `<resolved_review_dir>/config.toml`, if present.
3. User config file at `~/.config/scriptorium/config.toml`, if present.
4. Environment overrides listed in §3.3.
5. Explicit CLI flags for the current command.

Later layers override earlier layers. Unknown keys in TOML are ignored on read but rejected by `scriptorium config set`. Corrupted TOML exits with `E_CONFIG_CORRUPT` and does not overwrite the file.

Cowork has no local shell config file. The same keys live in a user-memory note named `scriptorium-config`, TOML-shaped, written only through the `configuring-scriptorium` skill.

### 3.2 Complete key list after v0.3

| Key | Type | Default | Required | Meaning |
|---|---:|---|---:|---|
| `default_model` | string | `"opus"` | no | Existing model selector retained from v0.2.0. |
| `review_dir` | string path | `"literature_review"` | no | Existing default review directory retained. |
| `evidence_required` | boolean | `true` | no | Existing cite discipline flag retained. |
| `sources_enabled` | list[string] | `["openalex", "semantic_scholar"]` | no | Existing enabled source list retained. |
| `notebook_id` | string | `""` | no | Existing legacy NotebookLM field retained for compatibility; v0.3 publish does not use it as state. |
| `unpaywall_email` | string | `""` | yes for Unpaywall | Email for Unpaywall requests. |
| `openalex_email` | string | `""` | no | OpenAlex polite-pool email. |
| `semantic_scholar_api_key` | string | `""` | no | Semantic Scholar API key. |
| `default_backend` | string enum | `"openalex"` | no | Valid: `openalex`, `semantic_scholar`. |
| `languages` | list[string] | `["en"]` | no | ISO language filters used during screening/search. |
| `obsidian_vault` | string path | `""` | no | Enables vault-relative review paths. |
| `notebooklm_enabled` | boolean | `false` | no | Set true by setup only after `nlm doctor` succeeds. |
| `notebooklm_prompt` | boolean | `true` | no | Controls end-of-review NotebookLM prompt. |

### 3.3 Environment overrides

| Variable | Type | Overrides |
|---|---:|---|
| `SCRIPTORIUM_REVIEW_DIR` | string path | Default review directory when `--review-dir` is absent. |
| `SCRIPTORIUM_CONFIG` | string path | User config file path. |
| `SCRIPTORIUM_OBSIDIAN_VAULT` | string path | `obsidian_vault`. |
| `SCRIPTORIUM_COWORK` | boolean string | Forces Cowork degradation detection when `1`, `true`, or `yes`. |
| `SCRIPTORIUM_FORCE_COWORK` | boolean string | Test-only alias for Cowork degradation mode. |

### 3.4 `scriptorium config` CLI

```text
scriptorium config get <key> [--review-dir <path>]
scriptorium config set <key> <value> [--review-dir <path>]
```

Flags and arguments:

| Name | Type | Required | Default | Behavior |
|---|---:|---:|---|---|
| `<key>` | string | yes | none | Must be one of §3.2. |
| `<value>` | string | yes for `set` | none | Coerced to the key type. Lists use comma-separated strings. Booleans accept `true/false/1/0/yes/no`. |
| `--review-dir` | path | no | load order §3.1 | Selects review-local config path. |

Errors use global exit codes in §11.

---

## 4. Path Resolution and Vault Detection

### 4.1 Review directory resolution

For every command that accepts a review directory:

1. If `--review-dir <path>` is absolute, use it exactly after `Path.resolve(strict=False)`.
2. If `--review-dir <path>` is relative and `obsidian_vault` is non-empty, resolve to `<obsidian_vault>/<path>`.
3. If `--review-dir <path>` is relative and `obsidian_vault` is empty, resolve to `$CWD/<path>`.
4. If `--review-dir` is omitted, use `SCRIPTORIUM_REVIEW_DIR` if present, else config `review_dir`, else `$CWD`.

Commands that create review output create the directory and required subdirectories. Read-only commands fail if the resolved directory does not exist.

### 4.2 Symlink behavior

- Review-dir symlinks are followed with `Path.resolve(strict=False)` for vault detection and file writes.
- PDF source symlinks under `pdfs/` are not followed during publish; symlinked PDFs are skipped with warning `W_PDF_SYMLINK_SKIPPED`.
- Paper stub paths are never written through symlinks outside the selected vault or review root. If `papers/` is a symlink that resolves outside the allowed root, fail with `E_PATH_ESCAPE`.

### 4.3 Vault detection

Walk up from the resolved review directory to filesystem root. The first ancestor containing a directory named exactly `.obsidian` is `vault_root`.

Ambiguity rules:

- `.obsidian (conflicted copy)`, `.obsidian 2`, or other similarly named directories do not count.
- If both `.obsidian/` and a conflict copy exist in the same ancestor, use `.obsidian/` and append warning `W_VAULT_CONFLICT_COPY` to `audit.md`.
- If no exact `.obsidian/` exists, no vault is detected and no user-facing nag is printed.

`vault_root` is recorded in review-file frontmatter when detected.

---

## 5. Frontmatter Schemas

All frontmatter is YAML between `---` delimiters. Timestamps are UTC ISO-8601 strings ending in `Z`. Paths are absolute strings unless explicitly described as relative. Fields not listed here are forbidden in v0.3-generated frontmatter.

### 5.1 Paper stub: `papers/<paper_id>.md`

Required fields:

| Field | Type | Meaning |
|---|---:|---|
| `schema_version` | string | Always `"scriptorium.paper.v1"`. |
| `scriptorium_version` | string | `"0.3.0"` for v0.3 output. |
| `paper_id` | string | Stable paper id used in citations. |
| `title` | string | Paper title. |
| `authors` | list[string] | Author display names. Empty list allowed only when source lacks authors. |
| `year` | integer or null | Publication year. |
| `tags` | list[string] | Concept tags from evidence rows. Empty list allowed. |
| `reviewed_in` | list[string] | Review slugs citing this paper. |
| `full_text_source` | string enum | `user_pdf`, `unpaywall`, `arxiv`, `pmc`, `abstract_only`. |
| `created_at` | string | Creation timestamp. |
| `updated_at` | string | Last Scriptorium update timestamp. |

Optional fields:

| Field | Type | Meaning |
|---|---:|---|
| `doi` | string | DOI without URL prefix. |
| `pmid` | string | PubMed id. |
| `pmcid` | string | PMC id. |
| `pdf_path` | string | Local PDF path when known. |
| `source_url` | string | OA URL when known. |

### 5.2 Review artifact: `synthesis.md`, `contradictions.md`, `overview.md`, `audit.md`

Required fields:

| Field | Type | Meaning |
|---|---:|---|
| `schema_version` | string | Always `"scriptorium.review_file.v1"`. |
| `scriptorium_version` | string | `"0.3.0"`. |
| `review_id` | string | Slug, normally basename of resolved review dir. |
| `review_type` | string enum | `synthesis`, `contradictions`, `overview`, `audit`. |
| `created_at` | string | Initial creation timestamp. |
| `updated_at` | string | Last Scriptorium update timestamp. |
| `research_question` | string | User research question. |
| `cite_discipline` | string enum | `locator` or `abstract_only`. |

Optional fields:

| Field | Type | Applies to | Meaning |
|---|---:|---|---|
| `vault_root` | string path | all | Present only when vault detected. |
| `model_version` | string | overview | LLM model used for overview generation. |
| `generation_seed` | integer | overview | Deterministic seed from §8.5. |
| `generation_timestamp` | string | overview | Overview generation timestamp. |
| `corpus_hash` | string | overview | SHA-256 from §8.5. |
| `ranking_weights` | mapping[string,float] | overview | Exactly `{citation_frequency: 0.6, llm_salience: 0.4}`. |

### 5.3 Audit JSONL rows

`audit.jsonl` remains machine-readable state. Each line is a JSON object:

| Field | Type | Required | Meaning |
|---|---:|---:|---|
| `timestamp` | string | yes | UTC ISO-8601. |
| `phase` | string | yes | `setup`, `search`, `screening`, `extraction`, `synthesis`, `verification`, `contradictions`, `overview`, `publishing`, `migration`, `export`. |
| `action` | string | yes | Dot-separated action, e.g. `notebook.create`. |
| `status` | string enum | yes | `success`, `warning`, `failure`, `partial`, `skipped`. |
| `details` | object | yes | JSON-serializable detail payload. |

Corrupted `audit.jsonl` is not truncated. v0.3 writes new rows to `audit.recovery.<timestamp>.jsonl`, emits `E_AUDIT_CORRUPT`, and instructs the user to repair or archive the corrupted file.

---

## 6. Native Obsidian Output

### 6.1 Default behavior

Native Obsidian output is always on. There is no `--obsidian-mode` flag. Generated citations in new v0.3 Markdown use wikilinks.

### 6.2 Paper stub body

`papers/<paper_id>.md` body format:

```markdown
# <First author> (<year>) — <title>

**DOI:** <doi or "unknown">
**Full text:** <source label and URL/path or "abstract only">
**Local PDF:** [[<relative path to pdf>]]

## Abstract

<abstract text exactly as stored in corpus/evidence source, or "No abstract available.">

## Cited pages

### p-4

> <exact quote from evidence.jsonl>

## Claims in review: <review_id>

- <claim text> -> [[reviews/<review_id>/synthesis.md]]
```

Invariants:

- `### p-N` sections exist only for cited pages.
- The quote text is copied exactly from the matching `evidence.jsonl` row.
- Scriptorium-owned regions are bounded by headings. User edits outside frontmatter, `## Cited pages`, and matching `## Claims in review: <review_id>` survive regeneration.
- Empty evidence produces no paper stub and logs `W_EMPTY_EVIDENCE`.

### 6.3 Wikilink citation format

New v0.3 files use:

```text
[[paper_id#p-N]]
```

The cite parser must accept both:

- Legacy v0.2.0 form: `[paper_id:page:N]`
- v0.3 form: `[[paper_id#p-N]]`

Both resolve to the same evidence row: `paper_id == paper_id` and `locator == "page:N"`. Mixed-form files are valid. New v0.3 generation never writes legacy form.

### 6.4 Dataview query file

Write `scriptorium-queries.md` once:

- Vault detected: `<vault>/scriptorium-queries.md`
- No vault: `<review-dir>/scriptorium-queries.md`

If the file already exists, leave it unchanged and log `W_QUERIES_EXIST`.

Content must include exactly the five canonical v0.2.1 queries, each with a one-line description:

```dataview
TABLE claim, direction FROM "reviews" WHERE contains(file.name, "evidence")
```

```dataview
LIST FROM "reviews" WHERE contains(file.content, "kennedy2017")
```

```dataview
TABLE length(file.outlinks) AS "references" FROM "reviews" WHERE contains(file.name, "synthesis") SORT length(file.outlinks) DESC
```

```dataview
TABLE concept, direction FROM "reviews" FLATTEN direction WHERE direction = "positive"
```

```dataview
LIST FROM "reviews" WHERE contains(file.name, "contradictions")
```

---

## 7. Install and Setup

### 7.1 `/scriptorium-setup`

Slash command file: `.claude-plugin/commands/scriptorium-setup.md`.

Skill: `.claude-plugin/skills/setting-up-scriptorium/SKILL.md`.

Arguments:

| Argument | Type | Required | Default | Meaning |
|---|---:|---:|---|---|
| `--notebooklm` | boolean flag | no | `false` | Re-run only NotebookLM setup when Scriptorium is already installed. |
| `--skip-notebooklm` | boolean flag | no | `false` | Install Scriptorium and plugin but skip NotebookLM. |
| `--vault <path>` | path | no | auto-detect | Use this Obsidian vault path after verifying `.obsidian/`. |

Flow:

1. Precheck Python `>=3.11`, writable `$HOME`, and current OS shell access.
2. Install package: prefer `uv pip install scriptorium-cli`; fallback `pip install scriptorium-cli`.
3. Verify `scriptorium --version` prints `scriptorium 0.3.0`.
4. Install `.claude-plugin/` into Claude Code plugin directory using existing plugin install convention; prompt user to restart Claude Code.
5. Configure Obsidian vault: scan `~/Documents/Obsidian/`, `~/Obsidian/`, `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/`, and current `obsidian_vault`.
6. Ask for `unpaywall_email`; persist with `scriptorium config set unpaywall_email <value>`.
7. NotebookLM unless skipped: install `notebooklm-mcp-cli` with `uv tool install notebooklm-mcp-cli` or `pipx install notebooklm-mcp-cli`; show §7.4 warning; run `nlm login`; verify `nlm doctor`; set `notebooklm_enabled true`.
8. Run `scriptorium doctor`.
9. Print: `You're set. Try /lit-review "your question" --review-dir reviews/<slug> to kick off your first review.`

### 7.2 `scriptorium init`

Terminal fallback command:

```text
scriptorium init [--notebooklm] [--skip-notebooklm] [--vault <path>]
```

Same flags and flow as §7.1 except plugin installation is skipped and prompts use terminal input instead of `AskUserQuestion`.

### 7.3 Interrupted setup

Setup writes a state file at `~/.config/scriptorium/setup-state.json` after each completed step:

```json
{"version":"0.3.0","completed_steps":["precheck","package"],"updated_at":"2026-04-20T14:32:08Z"}
```

On rerun:

- Completed steps are skipped after verifying current state.
- Failed or interrupted step is retried.
- `Ctrl-C` during NotebookLM login stores `notebooklm_enabled false`, exits 130, and leaves package/plugin/config steps intact.
- Corrupted setup state is moved to `setup-state.corrupt.<timestamp>.json`; setup restarts from precheck and emits `W_SETUP_STATE_CORRUPT`.

### 7.4 Dedicated Google account warning

```text
Use a dedicated Google account for NotebookLM integration, not your primary
account. The nlm CLI works via browser automation; Google may flag automated
activity against your primary account. This is an upstream limitation of nlm,
not Scriptorium.

Press Enter to acknowledge and continue, or Ctrl-C to skip NotebookLM setup.
```

### 7.5 Curl one-liner

The public docs may include:

```bash
curl -fsSL https://install.scriptorium.dev | bash
```

The script only installs `scriptorium-cli` and runs `scriptorium init`. If `install.scriptorium.dev` is not live at release time, docs must use the raw GitHub URL for `scripts/install.sh` instead. This wrapper is cuttable; `scriptorium init` is not.

---

## 8. Executive Briefing: `overview.md`

### 8.1 Purpose

`overview.md` is the front-door briefing for a completed review. It summarizes this review's corpus, not the field.

### 8.2 Statement classes

| Class | Required marker |
|---|---|
| Paper claim quoted or paraphrased | `[[paper_id#p-N]]` locator. |
| Synthesis, ranking, camp naming, or corpus framing | Inline `<!-- synthesis -->` tag and no paper locator. |

Overview lint fails closed: a paper claim without a locator or a synthesis sentence with a paper locator is rejected.

### 8.3 Required sections

Exactly nine sections, in this order:

1. `TL;DR`
2. `Scope & exclusions`
3. `Most-cited works in this corpus`
4. `Current findings`
5. `Contradictions in brief`
6. `Recent work in this corpus (last 5 years)`
7. `Methods represented in this corpus`
8. `Gaps in this corpus`
9. `Reading list`

Each section title is intentionally corpus-bounded. Do not rename to field-level language such as "most important works" or "research gaps".

### 8.4 Provenance blocks

Every section ends with:

```html
<!-- provenance:
  section: most-cited-works
  contributing_papers: [nehlig2010, smith2018]
  derived_from: synthesis.md#current-findings
  generation_timestamp: 2026-04-20T14:32:08Z
-->
```

Required keys: `section`, `contributing_papers`, `derived_from`, `generation_timestamp`.

### 8.5 Generation command

```text
scriptorium regenerate-overview <review-dir> [--model <name>] [--seed <int>] [--json]
```

Flags and arguments:

| Name | Type | Required | Default | Meaning |
|---|---:|---:|---|---|
| `<review-dir>` | path | yes | none | Review dir resolved by §4.1. |
| `--model` | string | no | config `default_model` | LLM model identifier recorded in frontmatter. |
| `--seed` | integer | no | SHA-256 of `research_question + review_id`, first 8 hex digits as int | Recorded for reproducibility signaling. |
| `--json` | boolean | no | `false` | Emits `{path, archived_path, corpus_hash, warnings[]}`. |

Inputs: `synthesis.md`, `contradictions.md`, `evidence.jsonl`, and cited paper stub frontmatter.

`corpus_hash` is SHA-256 of normalized evidence row ids in deterministic order: `<paper_id>|<locator>|<sha256(claim)>`.

Length target is 300 words; lint warns above 400 words but does not fail solely for length.

### 8.6 Regeneration semantics

- First generation writes `overview.md`.
- If `overview.md` exists, archive it to `<review-dir>/overview-archive/<created_at-or-file-mtime>.md` before writing a replacement.
- User edits are preserved only in the archive; v0.3 does not merge regenerated content.
- If generation, lint, or cite-check fails, no new `overview.md` is written. The failed draft is written to `<review-dir>/overview.failed.<timestamp>.md`, an audit row is appended, and the command exits `E_OVERVIEW_FAILED`.

---

## 9. NotebookLM Publishing

### 9.1 End-of-review prompt

After `/lit-review` completes, cite-check passes, contradictions are written, and `overview.md` is written successfully, show:

```text
NotebookLM artifact? (skip default)
  audio
  deck
  mindmap
  skip
```

Prompt appears only when all gates are true:

1. `notebooklm_prompt` is not `false`.
2. `nlm doctor` succeeds and `notebooklm_enabled` is `true`.
3. Cite-check passed.

`skip` is default. Non-skip selections call `scriptorium publish --review-dir <path> --generate <audio|deck|mindmap>`.

In Cowork, the same prompt may appear, but the publish path emits the degradation block in §9.6 and never invokes `nlm`.

### 9.2 Standalone slash commands

| Slash command | File | Maps to |
|---|---|---|
| `/lit-podcast <review-dir>` | `.claude-plugin/commands/lit-podcast.md` | `scriptorium publish --review-dir <path> --generate audio` |
| `/lit-deck <review-dir>` | `.claude-plugin/commands/lit-deck.md` | `scriptorium publish --review-dir <path> --generate deck` |
| `/lit-mindmap <review-dir>` | `.claude-plugin/commands/lit-mindmap.md` | `scriptorium publish --review-dir <path> --generate mindmap` |

### 9.3 `scriptorium publish` CLI

```text
scriptorium publish
  --review-dir <path>
  [--notebook <title>]
  [--generate <audio|deck|mindmap|video|all>]
  [--sources <csv>]
  [--yes]
  [--json]
```

Flags:

| Flag | Type | Required | Default | Behavior |
|---|---:|---:|---|---|
| `--review-dir` | path | yes | none | Resolve by §4.1. |
| `--notebook` | string | no | Title-cased basename of resolved review dir, replacing `-` and `_` with spaces | Empty derived names fail with `E_NOTEBOOK_NAME`. |
| `--generate` | enum | no | none | `audio`, `deck`, `mindmap`, `video`, `all`. `all` means audio, deck, mindmap; video only when explicit. |
| `--sources` | CSV enum list | no | `overview,synthesis,contradictions,evidence,pdfs` | Valid tokens: `overview`, `synthesis`, `contradictions`, `evidence`, `pdfs`, `stubs`. |
| `--yes` | boolean | no | `false` | Auto-confirms creating a new notebook when an audit entry shows prior publish to same notebook name. |
| `--json` | boolean | no | `false` | Success emits documented JSON only. |

Success JSON:

```json
{
  "notebook_id": "abc123",
  "notebook_url": "https://notebooklm.google.com/notebook/abc123",
  "uploaded_sources": ["overview.md", "synthesis.md"],
  "artifact_ids": {"audio": "artifact_1"},
  "warnings": []
}
```

### 9.4 Publish behavior

1. Acquire lock `<review-dir>/.scriptorium.lock`. If held, fail with `E_LOCKED`.
2. Resolve review dir and source set.
3. Verify required files exist for selected sources. Empty source set fails `E_SOURCES`.
4. If Cowork mode, emit §9.6 block and exit 0 without lock-modifying files except optional audit warning if local files are writable.
5. Run `nlm doctor`; on failure exit `E_NLM_UNAVAILABLE`.
6. Scan `audit.md` for prior publish to the same notebook name. If found and `--yes` is absent, prompt `Proceed and create a new notebook? [y/N]`. `N` or EOF exits 0 with no remote calls.
7. Create notebook: `nlm notebook create <title>`. Capture notebook id and URL from stdout.
8. Upload sources in this order:
   - `overview.md`
   - `synthesis.md`
   - `contradictions.md`
   - `evidence.jsonl`
   - direct child PDFs matching `*.pdf` under `pdfs/`, alphabetically, symlinks skipped
   - paper stubs only when `stubs` is in `--sources`, alphabetically
9. Each upload command is `nlm source add <id> --file <path>`.
10. Wait one second between uploads.
11. On upload failure, stop remaining uploads, write partial audit entry, exit `E_NLM_UPLOAD`.
12. Trigger artifact commands:
    - audio: `nlm audio create <id>`
    - deck: `nlm slides create <id>`
    - mindmap: `nlm mindmap create <id>`
    - video: `nlm video create <id>`
13. Artifact failure does not roll back uploaded sources; write partial audit entry and exit `E_NLM_ARTIFACT`.
14. Append success audit entry and print notebook URL or JSON.
15. Release lock.

No rollback is attempted for remote NotebookLM state.

### 9.5 Timeouts and partial failures

Each `nlm` subprocess has a five-minute timeout. Timeout writes partial audit state and exits `E_TIMEOUT`.

Partial audit entries must include:

- notebook name, id, and URL if known
- source manifest attempted
- source manifest succeeded
- failing command
- captured exit code or timeout marker
- captured stderr truncated to 4 KiB
- privacy note

### 9.6 Cowork degradation block

Emit this block verbatim, substituting placeholders:

```text
Publishing to NotebookLM requires local shell access, which Cowork doesn't grant.
Two options:

1. Run `scriptorium publish` from Claude Code or your terminal instead. The review
   is already in your vault (or Drive/Notion per your setup); any surface with
   local shell access can publish it.

2. Upload manually:
   a. Open https://notebooklm.google.com and create a new notebook named
      "<notebook_name>".
   b. Upload these files as sources:
      <dynamic relative file list>
   c. Use the Studio panel to generate your artifact of choice.

Either way, remember to note the upload in audit.md under ## Publishing; see
docs/publishing-notebooklm.md for the template.
```

### 9.7 Publishing audit entry

Append to `audit.md` for success, partial success, and failure after a notebook exists:

```markdown
## Publishing

### 2026-04-20T14:32:08Z — NotebookLM

**Status:** success
**Destination:** NotebookLM (Google)
**Notebook:** "Caffeine Wm" (id: `abc123`)
**URL:** https://notebooklm.google.com/notebook/abc123
**Triggered by:** `scriptorium publish` (scriptorium v0.3.0, nlm CLI v<nlm --version>)

**Sources attempted** (5 files):
- overview.md (2100 bytes)
- synthesis.md (12400 bytes)

**Sources uploaded** (5 files, 18300000 bytes):
- overview.md (2100 bytes)
- synthesis.md (12400 bytes)

**Studio artifacts triggered:**
- audio (id: `artifact_abc`, status: queued)

**Privacy note:** This action uploaded the listed files to Google-hosted NotebookLM. The review's local copy is unchanged.
```

`audit.jsonl` also receives a `publishing` row with equivalent structured data.

---

## 10. Migration and Release

### 10.1 `scriptorium migrate-review`

```text
scriptorium migrate-review <review-dir> [--dry-run] [--json]
```

Flags:

| Name | Type | Required | Default | Meaning |
|---|---:|---:|---|---|
| `<review-dir>` | path | yes | none | Review dir resolved by §4.1. |
| `--dry-run` | boolean | no | `false` | Report changes without writing. |
| `--json` | boolean | no | `false` | Emit `{changed_files, skipped_files, warnings}`. |

Behavior:

1. Acquire review lock.
2. Validate `audit.md`, `evidence.jsonl`, and `synthesis.md`; missing required files exits `E_REVIEW_INCOMPLETE`.
3. If required files are corrupt, exit `E_STATE_CORRUPT` without writes.
4. Convert legacy `[paper_id:page:N]` tokens to `[[paper_id#p-N]]` in `synthesis.md` and `contradictions.md`.
5. Add frontmatter to `synthesis.md`, `contradictions.md`, and `audit.md` if absent.
6. Generate or update paper stubs for cited evidence rows.
7. Write `scriptorium-queries.md` if absent.
8. Do not generate `overview.md`; user runs `scriptorium regenerate-overview`.
9. Append migration audit entry.
10. Release lock.

Rerun on an already migrated review exits 0 and reports no changes.

### 10.2 Version and release files

Implementation must update:

- `pyproject.toml`: `name = "scriptorium-cli"`, `version = "0.3.0"`, preserve flat package discovery for `scriptorium/`.
- `scriptorium/__init__.py`: `__version__ = "0.3.0"`.
- `.claude-plugin/plugin.json`: version `0.3.0`.
- `README.md`: replace with `README_proposed.md` content adjusted for beta and `pip install scriptorium-cli`.
- `CHANGELOG.md`: add v0.3.0 entry.

### 10.3 PyPI flow

1. Tag `v0.3.0-rc1`.
2. Publish to Test-PyPI.
3. Install in clean venv: `pip install -i https://test.pypi.org/simple/ scriptorium-cli`.
4. Run `scriptorium doctor` and caffeine fixture smoke.
5. Tag `v0.3.0`.
6. Publish to PyPI.

---

## 11. Errors, Warnings, and Exit Codes

### 11.1 Exit codes

Every non-zero code is unique.

| Exit | Symbol | Meaning |
|---:|---|---|
| 0 | `OK` | Success, no-op, or user declined idempotency prompt before remote calls. |
| 1 | `E_USAGE` | CLI usage or argparse error. |
| 2 | `E_CONFIG` | Unknown config key or invalid config value. |
| 3 | `E_VERIFY_FAILED` | Cite-check failed. Existing v0.2 behavior retained. |
| 4 | `E_REVIEW_INCOMPLETE` | Required review files missing. |
| 5 | `E_NLM_UNAVAILABLE` | `nlm doctor` failed or `nlm` missing. |
| 6 | `E_NLM_CREATE` | Notebook creation failed. |
| 7 | `E_NLM_UPLOAD` | Source upload failed after notebook creation. |
| 8 | `E_NLM_ARTIFACT` | Artifact generation failed after successful uploads. |
| 9 | `E_TIMEOUT` | Subprocess timeout. |
| 10 | `E_SOURCES` | Invalid or empty `--sources`. |
| 11 | `E_NOTEBOOK_NAME` | Could not derive notebook title. |
| 12 | `E_LOCKED` | Another Scriptorium run holds the review lock. |
| 13 | `E_PATH_ESCAPE` | Resolved path escapes allowed review/vault root. |
| 14 | `E_CONFIG_CORRUPT` | Config TOML cannot be parsed. |
| 15 | `E_AUDIT_CORRUPT` | Existing audit JSONL cannot be parsed safely. |
| 16 | `E_STATE_CORRUPT` | Corpus/evidence/frontmatter state is malformed. |
| 17 | `E_OVERVIEW_FAILED` | Overview generation or lint failed. |
| 18 | `E_SETUP_FAILED` | Setup failed before user interruption. |
| 130 | `E_INTERRUPTED` | User interrupted setup or generation. |

### 11.2 Canonical publish messages

All errors are prefixed `scriptorium publish:`.

| Symbol | Message |
|---|---|
| `E_REVIEW_INCOMPLETE` | `review directory is incomplete: expected <missing_files> at <resolved_path>. Run /lit-review to completion before publishing.` |
| `E_NLM_UNAVAILABLE` | `nlm CLI not found or not authenticated. Install with 'uv tool install notebooklm-mcp-cli' and run 'nlm login'. See docs/publishing-notebooklm.md for full setup.` |
| `E_NLM_CREATE` | `failed to create NotebookLM notebook (<nlm_exit_code>). nlm output: <captured_stderr>. See docs/publishing-notebooklm.md#troubleshooting.` |
| `E_NLM_UPLOAD` | `upload failed for <filename> (<nlm_exit_code>). <N> sources uploaded successfully before failure. Notebook <notebook_id> exists in partial state at <url>. See audit.md for details.` |
| `E_SOURCES` | `--sources contained unknown token '<token>'. Valid values: overview, synthesis, contradictions, evidence, pdfs, stubs.` |
| `E_NOTEBOOK_NAME` | `cannot derive notebook name from '<review-dir>'. Pass --notebook "<name>" explicitly.` |
| `E_LOCKED` | `review is locked by another Scriptorium run at <lock_path>. If no run is active, remove the stale lock after verifying no process is writing.` |

Warnings:

| Symbol | Meaning |
|---|---|
| `W_PRIOR_PUBLISH` | Prior publish to same notebook name found. |
| `W_PDF_SYMLINK_SKIPPED` | PDF symlink skipped during publish. |
| `W_VAULT_CONFLICT_COPY` | Dropbox-style Obsidian conflict marker detected. |
| `W_QUERIES_EXIST` | Existing query file left unchanged. |
| `W_EMPTY_EVIDENCE` | Empty evidence produced no stubs or overview. |
| `W_SETUP_STATE_CORRUPT` | Setup state moved aside and restarted. |

---

## 12. Skills, Commands, and Hooks

### 12.1 Commands

| File | Status | Required content |
|---|---|---|
| `.claude-plugin/commands/lit-review.md` | update | Thread review dir, generate overview after cite-check, offer NotebookLM prompt. |
| `.claude-plugin/commands/lit-config.md` | update | Include new config keys from §3.2. |
| `.claude-plugin/commands/lit-add-pdf.md` | unchanged | No v0.3 surface change. |
| `.claude-plugin/commands/lit-export-bib.md` | unchanged | No v0.3 surface change. |
| `.claude-plugin/commands/lit-show-audit.md` | update | Understand `audit.md` frontmatter and publishing entries. |
| `.claude-plugin/commands/lit-podcast.md` | new | Wrapper in §9.2. |
| `.claude-plugin/commands/lit-deck.md` | new | Wrapper in §9.2. |
| `.claude-plugin/commands/lit-mindmap.md` | new | Wrapper in §9.2. |
| `.claude-plugin/commands/scriptorium-setup.md` | new | Flow in §7.1. |

### 12.2 Skills

| Directory | Status | Required content |
|---|---|---|
| `using-scriptorium/` | update | v0.3 config keys, Obsidian output, publish route, Cowork degradation. |
| `running-lit-review/` | update | Overview generation and end-of-review prompt after cite-check. |
| `configuring-scriptorium/` | update | All §3.2 config keys; Cowork memory note parity. |
| `lit-searching/` | unchanged | No v0.3 change. |
| `lit-screening/` | unchanged | No v0.3 change. |
| `lit-extracting/` | update | Full-text source enum names in §5.1; paper stub inputs. |
| `lit-synthesizing/` | update | v0.3 wikilinks and frontmatter. |
| `lit-contradiction-check/` | update | v0.3 wikilinks and frontmatter. |
| `lit-audit-trail/` | update | Frontmatter and publishing entries. |
| `lit-publishing/` | rename | Rename to `publishing-to-notebooklm/`; replace MCP Studio instructions with CLI/manual flow. |
| `publishing-to-notebooklm/` | new after rename | Publish preconditions, verified `nlm` commands, privacy note, Cowork block. |
| `setting-up-scriptorium/` | new | `/scriptorium-setup` flow and interrupted setup handling. |
| `generating-overview/` | new | `overview.md` generation, lint, provenance, failure handling. |

### 12.3 Hook

`.claude-plugin/hooks/evidence_gate.sh` remains. The Python verifier it shells out to must dual-parse legacy citations and v0.3 wikilinks. For `overview.md`, verifier also enforces §8.2 and §8.4.

---

## 13. Tests

### 13.1 Unit tests

- `tests/test_config_v03.py`: all §3.2 keys, types, defaults, load order, unknown key rejection, corrupted TOML `E_CONFIG_CORRUPT`.
- `tests/test_path_resolution.py`: absolute review dir, relative with vault, relative without vault, env override, symlink resolution, path escape.
- `tests/test_vault_detection.py`: vault present, absent, parent-of-parent, symlinked review dir, conflict copy warning.
- `tests/test_frontmatter.py`: paper and review schemas with required/optional fields and forbidden fields.
- `tests/test_wikilink_parse.py`: legacy, v0.3, mixed citations resolve to evidence rows.
- `tests/test_paper_stubs.py`: create/update, cited pages only, user edits outside owned regions survive, empty evidence warning.
- `tests/test_dataview_queries.py`: exact five queries, idempotent existing file.
- `tests/test_overview_lint.py`: nine sections, provenance, citation class enforcement, length warning.
- `tests/test_migrate_review.py`: dry-run, real migration, idempotent rerun, corrupted state fail-closed.
- `tests/test_setup_state.py`: interrupted setup, corrupted setup state, idempotent rerun.

### 13.2 Integration tests

- `tests/test_publish_cli.py`: all §9.3 flags, defaults, invalid sources, empty sources, notebook derivation, `--yes`, JSON shape.
- `tests/test_publish_flow.py`: verified `nlm` command sequence, upload ordering, timeout, partial upload, artifact failure, audit entry, lock behavior.
- `tests/test_publish_cowork.py`: Cowork block emitted; no `nlm` subprocess attempted.
- `tests/test_end_of_review_prompt.py`: three gates, skip default, command mapping for audio/deck/mindmap.
- `tests/test_overview_generation.py`: generation inputs, archive-on-regenerate, failed draft handling.
- `tests/test_cli_exit_codes.py`: every §11 exit code is reachable and unique.
- `tests/test_command_skill_content.py`: command files and skills contain verified `nlm` commands and do not contain forbidden stale commands.

### 13.3 E2E and release tests

- Existing caffeine E2E passes and additionally asserts `overview.md`, frontmatter, stubs, query file, wikilinks.
- Test-PyPI smoke installs `scriptorium-cli`, verifies `scriptorium --version`, runs `scriptorium doctor`, and runs caffeine fixture.
- Real `nlm` smoke with dedicated Google account creates audio, deck, and mindmap from a small fixture.

---

## 14. Acceptance Criteria

Each criterion traces to a prior section.

- [ ] Package remains flat-layout import `scriptorium`; distribution is `scriptorium-cli`; version is `0.3.0` (§0.1, §10.2).
- [ ] Verified `nlm` commands are used exactly; forbidden stale commands are absent (§0.2, §9.4, §13.2).
- [ ] `/scriptorium-setup` and `scriptorium init` implement flags, idempotency, interrupted setup, and NotebookLM warning (§7).
- [ ] Config keys, defaults, types, load order, env overrides, and corrupted config behavior match §3.
- [ ] Review-dir resolution, symlink policy, vault detection, and conflict behavior match §4.
- [ ] Vault layout and no-vault layout match §2.
- [ ] Frontmatter schemas for paper stubs, review artifacts, and audit JSONL match §5.
- [ ] Native Obsidian output is default; new citations are wikilinks; verifier dual-parses legacy and v0.3 citations (§6).
- [ ] Dataview query file is written once with exactly five canonical queries (§6.4).
- [ ] `overview.md` generation, lint, provenance, archive, failed-output behavior, and CLI flags match §8.
- [ ] End-of-review NotebookLM prompt gates and defaults match §9.1.
- [ ] `/lit-podcast`, `/lit-deck`, `/lit-mindmap` route exactly as §9.2.
- [ ] `scriptorium publish` implements every flag, source default, upload order, lock, timeout, partial failure, audit entry, and JSON shape in §9.
- [ ] Cowork publish emits the exact degradation block and never invokes `nlm` (§9.6).
- [ ] `scriptorium migrate-review` implements flags, no-auto-migration policy, idempotency, and fail-closed corrupted-state behavior (§10.1).
- [ ] `.claude-plugin/skills/lit-publishing/` is renamed to `publishing-to-notebooklm/` and rewritten (§12.2).
- [ ] New skills `setting-up-scriptorium/` and `generating-overview/` exist with bodies matching §§7 and 8 (§12.2).
- [ ] Existing hook file remains and verifier behavior is updated (§12.3).
- [ ] All errors and exit codes are unique and implemented as §11.
- [ ] Tests in §13 pass, including PyPI smoke and command/skill stale-command scan.
- [ ] README, docs, and changelog are updated as §10.2 requires.

---

## 15. Post-Implementation Checklist

- [ ] Tag `v0.3.0-rc1`; publish to Test-PyPI.
- [ ] Run Test-PyPI smoke in a clean venv.
- [ ] Run `/scriptorium-setup` on a clean macOS account.
- [ ] Run no-vault and vault-mode caffeine fixtures.
- [ ] Run publish smoke with dedicated Google account: audio, deck, mindmap.
- [ ] Verify Cowork degradation by forcing `SCRIPTORIUM_FORCE_COWORK=1`.
- [ ] Tag `v0.3.0`; publish to PyPI.
- [ ] Open v0.4 issues for deferred scope in §1.2.

---

## Self-Review Log

### Coverage

- Brainstorm version/status: §0, §10.
- Brainstorm scope: §1.
- v0.2.1 config/vault/publish/Cowork/audit scope: §§3, 4, 5, 9, 11, 13.
- Native Obsidian output: §§2, 5, 6.
- Executive briefing: §8.
- NotebookLM flow: §9.
- Version, migration, PyPI release: §10.
- Skills, commands, hooks: §12.
- Acceptance criteria traceability: §14 maps every item to earlier sections.

### Drift corrected in this revision

- Removed stale v0.2.1 NotebookLM command shapes. All `nlm` calls now match verified installed commands.
- Removed open questions section. Design choices are resolved here so the next step can be an implementation plan.
- Replaced ambiguous edge-case language with explicit behavior for symlinks, partial failures, concurrent runs, empty inputs, interrupted setup, corrupted config, corrupted audit, and corrupted review state.
- Added complete config key table including current v0.2.0 keys and v0.3 additions.
- Added frontmatter schemas with required/optional fields and types.
- Added unique exit code table and canonical publish messages.
- Added `--yes` to publish so idempotency can be tested non-interactively.
- Added setup state file semantics for interrupted setup.
- Corrected package facts: current repo starts as `name = "scriptorium"`, `version = "0.2.0"`; v0.3 changes distribution to `scriptorium-cli` while preserving flat import layout and console command.

### Judgment calls

- Config load order includes both review-local and user config. v0.2.0 code currently reads review-local config; user config is a v0.3 addition needed for setup persistence.
- `scriptorium init` is treated as required while the curl one-liner wrapper is cuttable. This keeps non-Claude setup testable without depending on DNS.
- `--generate all` excludes video unless explicitly requested, preserving the brainstorm's three seamless artifacts while leaving video available from v0.2.1 publish scope.
- Setup state path is `~/.config/scriptorium/setup-state.json` to make interrupted setup resumable without touching review directories.
- Review locking uses `<review-dir>/.scriptorium.lock`; lock implementation details belong in the implementation plan, but the behavior is specified here.

### Consistency checks performed

- Section references in acceptance criteria resolve to existing sections.
- `nlm` commands in §§0.2 and 9.4 agree exactly.
- Distribution name vs. console script naming is consistent across §§0, 7, 10, 14.
- Skill rename is consistent across §§0.1, 12.2, 14.
- Error symbols in publish behavior map to unique exit codes in §11.
- No scope item outside the locked brainstorm list is included except implementation details required to make the locked items testable; those are marked as judgment calls.
