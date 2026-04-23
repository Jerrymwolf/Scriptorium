# Clean Review Layout + Microsoft Office Export

**Date:** 2026-04-23
**Status:** Design approved, pending implementation plan.
**Primary runtime:** Cowork (sandboxed Python). Secondary: Claude Code.

## Problem

The v0.3 review folder layout dumps every artifact — prose deliverables, JSONL data, PDFs, per-paper stubs, failed overview retries, audit logs — into a single flat root. Opening a review in Finder or Obsidian shows ~15 files and folders at the top level with no clear grouping. Failed overview attempts (`overview.failed.YYYYMMDDTHHMMSSZ.md`) land at root and accumulate. Collaborators who need Word or Excel versions have no path — Scriptorium writes only `.md` and `.jsonl`.

Two asks:

1. **Cleaner layout.** Deliverables visible at root, supporting files bucketed, failed retries archived.
2. **Microsoft Office export.** `.docx` for prose, `.xlsx` for data, alongside the existing markdown/JSONL (not replacing them — Obsidian integration must keep working).

## Constraints

- **Primary runtime is Cowork.** No external binaries (pandoc is out). Pure-Python pip dependencies only.
- **Evidence-first discipline is preserved.** Every export appends to `audit.jsonl`; citations in `.docx` must remain traceable to `corpus.jsonl` + `evidence.jsonl`.
- **Obsidian keeps working.** `.md` files stay at their current names; `.docx` is additive.
- **One-way export.** `.docx` → `.md` import is out of scope. Word is a handoff format.

## Design

### 1. Revised folder layout

```
<review>/
├── overview.md              # deliverables at root
├── overview.docx            # Office siblings, created on demand, side-by-side
├── synthesis.md
├── synthesis.docx
├── contradictions.md
├── contradictions.docx
├── scope.json               # visible: user-editable scope contract
├── references.bib           # derived export; root is where citation managers look
│
├── sources/                 # raw inputs only
│   ├── pdfs/
│   └── papers/              # per-paper stubs (Obsidian-linkable notes)
│
├── data/                    # machine-readable working set
│   ├── evidence.jsonl
│   ├── evidence.xlsx        # Excel sibling, on demand
│   ├── corpus.jsonl
│   ├── corpus.xlsx
│   └── extracts/
│
├── audit/
│   ├── audit.md
│   ├── audit.jsonl
│   └── overview-archive/    # failed overview retries land here, not root
│
└── .scriptorium/
    └── lock                 # truly internal, dotdir is correct here
```

**Rationale:**

- Office files sit next to their source (`overview.md` + `overview.docx` at root; `evidence.jsonl` + `evidence.xlsx` in `data/`). Collaborators who open the folder see the relationship without navigating into an `exports/` subfolder.
- `scope.json` stays visible at root because it is user-editable.
- `references.bib` stays at root because Zotero/BibTeX conventions look there.
- `sources/` contains only inputs. `data/` contains only machine-readable working set. `audit/` contains trail plus failed-overview archive. No overlap.
- `.scriptorium/` holds only the lock file. Nothing the user ever touches.
- No auto-generated `README.md`. Avoids collision with user-authored notes; Obsidian surfaces structure natively.

### 2. Export surface

**CLI:**

```
scriptorium export [--format docx|xlsx|all]
                   [--target overview|synthesis|contradictions|evidence|corpus|all]
                   [--review <path>]
                   [--dry-run]
```

- Review resolution order: `--review` flag, then `SCRIPTORIUM_REVIEW_DIR` env var, then cwd. Matches existing `resolve_review_dir()` in `paths.py`.
- Missing source files (e.g. no `synthesis.md` yet) → logged and skipped, never an error.
- `--dry-run` prints the planned writes without touching the filesystem.
- `.docx` / `.xlsx` are always regenerated from source. User edits live in `.md` / `.jsonl`. No round-trip import.
- Idempotent: re-running overwrites existing siblings.

**Skill (`scriptorium:lit-export-office`):**

- Natural-language wrapper: triggers on phrases like "give me the Word version," "export for my committee," "make a Word doc of the overview."
- Resolves review dir via the same order as the CLI.
- Shells out to `scriptorium export` with the resolved flags.
- Reports absolute paths of files written and anything skipped.

**Conversion module (`scriptorium/export.py`):**

- `md_to_docx(md_path, docx_path, corpus_path)` — uses `python-docx`. Walks the known Scriptorium markdown shape (H1/H2/H3 headings, paragraphs, bullet/ordered lists, tables, inline bold/italic/code) — not arbitrary markdown.
- `jsonl_to_xlsx(jsonl_path, xlsx_path, schema)` — uses `openpyxl`.

**Citation enrichment:**

- For each `[paper_id:locator]` in a prose file, `md_to_docx` looks up `paper_id` in `data/corpus.jsonl`.
- Renders as `(First-author Year, p. locator)` with a hyperlink to the paper stub in `sources/papers/<paper_id>.md`.
- Lookup miss → leaves raw `[paper_id:locator]` in the docx and logs a warning to the audit event. No silent drops.

**Stable xlsx schemas (declared as module constants):**

- `EVIDENCE_COLUMNS = ["paper_id", "locator", "claim", "quote", "tags", "extracted_at", ...]`
- `CORPUS_COLUMNS = ["paper_id", "title", "authors", "year", "venue", "doi", "url", ...]`
- Unknown keys in a row trail in sorted order after the declared columns.
- Header row: bold, frozen. Column widths computed from max cell length, capped at 80 chars.

**Audit event schema:**

```json
{
  "ts": "2026-04-23T15:02:11Z",
  "event": "export",
  "targets": ["overview", "evidence"],
  "formats": ["docx", "xlsx"],
  "sources": {
    "overview.md": "<sha256>",
    "data/evidence.jsonl": "<sha256>"
  },
  "written": ["overview.docx", "data/evidence.xlsx"],
  "skipped": ["synthesis.md (not found)"],
  "citation_misses": []
}
```

Future `scriptorium verify` can prove: "this `.docx` was generated from this version of the `.md`."

**Dependencies added to `pyproject.toml`:** `python-docx`, `openpyxl`. Both pure Python, Cowork-safe.

### 3. Migration

```
scriptorium migrate [--review <path>] [--dry-run] [--apply]
```

- Detects old-layout review by the presence of `evidence.jsonl` or `audit.jsonl` at the review root.
- `--dry-run` (default) prints the move plan: `audit.md` → `audit/audit.md`, `pdfs/` → `sources/pdfs/`, `overview.failed.*.md` → `audit/overview-archive/`, `evidence.jsonl` → `data/evidence.jsonl`, etc.
- `--apply` executes the moves. Idempotent — re-running is a no-op. Non-destructive: never deletes, only moves. If a target path already exists, the move for that file is skipped and logged.
- Appends one `migrate` event to `audit.jsonl` with before/after paths for every rename.
- No auto-migration on other `scriptorium` subcommands. Migration is always explicit.

### 4. Code changes

- **`scriptorium/paths.py`** — update `ReviewPaths` so existing properties resolve to the new locations (e.g. `evidence` → `data/evidence.jsonl`; `audit_md` → `audit/audit.md`; `overview_archive` → `audit/overview-archive`; `pdfs` → `sources/pdfs`; `papers` → `sources/papers`; `extracts` → `data/extracts`). Add new properties where needed: `audit_dir`, `data_dir`, `sources_dir`, `scriptorium_dir`, `lock`. No renames — call sites keep working; the paths just move.
- **`scriptorium/storage/`** — update all writers to target the new paths via `ReviewPaths`.
- **`scriptorium/export.py`** — new module containing `md_to_docx`, `jsonl_to_xlsx`, column-schema constants, and the `export` CLI subcommand entrypoint.
- **`scriptorium/migrate.py`** — extend the existing migration module with the layout shift.
- **`skills/lit-export-office/SKILL.md`** — new skill, runtime-agnostic prose wrapper that dispatches to the CLI in Claude Code or the equivalent shell-through mechanism in Cowork.
- **`pyproject.toml`** — add `python-docx`, `openpyxl` to runtime deps.
- **`CHANGELOG.md`** — entry for layout change + new export surface.

### 5. Testing

| Test | What it proves |
|---|---|
| `test_md_to_docx_shape.py` | Fixture `overview.md` → `.docx`; assert heading levels, bullets, ordered lists, tables, bold/italic/code render correctly via python-docx inspection. |
| `test_citation_enrichment.py` | Hit path: `[paper_id:p.12]` + matching corpus row → `(Smith 2024, p. 12)` rendered with hyperlink to `sources/papers/<paper_id>.md`. Miss path: unknown `paper_id` left raw in docx and logged to audit. |
| `test_jsonl_to_xlsx_schema.py` | Evidence/corpus fixtures → `.xlsx`; assert column order matches declared schema, unknown keys trail in sorted order, header row is frozen + bold. |
| `test_export_audit_event.py` | Exports a fixture review; assert one audit event with correct targets/formats/sources sha256/written/skipped/citation_misses. |
| `test_export_dry_run.py` | `--dry-run` writes nothing; stdout lists planned paths. |
| `test_export_missing_targets.py` | Export `--target all` on a review missing `synthesis.md` → skipped entry in audit, other exports succeed. |
| `test_migrate_dry_run_then_apply.py` | Fixture old-layout review; `--dry-run` prints moves; `--apply` executes; second `--apply` is a no-op; audit event present. |
| `test_migrate_collision_safety.py` | Target path already exists → specific file skipped + logged, rest proceed. |
| `test_paths_new_layout.py` | `ReviewPaths.evidence` resolves to `data/evidence.jsonl`, `audit_md` to `audit/audit.md`, `pdfs` to `sources/pdfs`, etc. |

All fixtures live under `tests/fixtures/exports/` and `tests/fixtures/migrate/`.

## Non-goals

- No `.docx` → `.md` import. Word is a one-way handoff format.
- `scriptorium export` does not regenerate `references.bib` — that stays in `scriptorium:lit-export-bib`'s scope.
- No auto-migration on unrelated `scriptorium` subcommands — `scriptorium migrate` is always explicit and opt-in.
- No `README.md` auto-generation at review root.

## Open questions

None at design-approval time. Implementation plan (next step via `writing-plans`) will sequence the work into atomic commits.
