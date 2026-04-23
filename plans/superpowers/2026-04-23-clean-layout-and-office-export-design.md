# Clean Review Layout + Overview as Word Document

**Date:** 2026-04-23
**Status:** Design approved, pending implementation plan.
**Primary runtime:** Cowork (sandboxed Python). Secondary: Claude Code.

## Problem

Two issues with the current review folder:

1. **Messy layout.** The v0.3 review root mixes prose deliverables, JSONL data, PDFs, per-paper stubs, failed overview retries, and audit logs — ~15 items at the top level with no clear grouping. Failed overviews (`overview.failed.YYYYMMDDTHHMMSSZ.md`) accumulate at root.
2. **Overview is `.md` only.** Most users who receive a Scriptorium review don't know how to read markdown. The overview is the artifact they actually open — it must be a Word document. Obsidian users still need the `.md`.

## Scope (what this spec is and is not)

**In scope:**
- Revised folder layout (Hybrid: deliverables at root, sources/data/audit bucketed).
- Automatic `overview.docx` dual-write inside the existing overview generation step.
- Citation enrichment when rendering the docx.
- One-shot manual migration of the existing `values-review/` folder, performed by Claude in a single session.

**Out of scope (explicitly deferred until there is a real request):**
- `scriptorium export` CLI subcommand.
- `lit-export-office` skill.
- `scriptorium migrate` CLI command.
- `.xlsx` export for `evidence.jsonl` / `corpus.jsonl`.
- `.docx` for `synthesis.md` and `contradictions.md`.
- Any natural-language export skill.

Deferring these keeps v1 small, keeps the user-facing surface zero (everything happens automatically), and avoids shipping code paths no one has asked for.

## Constraints

- **Primary runtime is Cowork.** No external binaries (pandoc is out). Pure-Python pip dependencies only.
- **Evidence-first discipline is preserved.** Every overview render appends to `audit.jsonl`; citations in the `.docx` must remain traceable to `corpus.jsonl` + `evidence.jsonl`.
- **Obsidian keeps working.** `overview.md` stays at its current name and location; `.docx` is additive.
- **Zero user action required.** A non-terminal user should never need to run a command, remember a flag, or invoke a skill. Overview generation produces both files; that's it.

## Design

### 1. Revised folder layout

```
<review>/
├── overview.md              # deliverables at root
├── overview.docx            # Word sibling, written automatically alongside overview.md
├── synthesis.md             # stays .md for v1 (deferred)
├── contradictions.md        # stays .md for v1 (deferred)
├── scope.json               # visible: user-editable scope contract
├── references.bib           # derived export; root is where citation managers look
│
├── sources/                 # raw inputs only
│   ├── pdfs/
│   └── papers/              # per-paper stubs (Obsidian-linkable notes)
│
├── data/                    # machine-readable working set
│   ├── evidence.jsonl
│   ├── corpus.jsonl
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
- `overview.md` and `overview.docx` sit side-by-side at root. Anyone opening the folder sees the Word document immediately; Obsidian users see the `.md`.
- `scope.json` stays visible at root because it is user-editable.
- `references.bib` stays at root because Zotero/BibTeX conventions look there.
- `sources/` contains only inputs. `data/` contains only machine-readable working set. `audit/` contains trail plus failed-overview archive. No overlap.
- `.scriptorium/` holds only the lock file.
- No auto-generated `README.md`.

### 2. Overview dual-write

The existing `generating-overview` skill (and its underlying `scriptorium/overview/` module) currently writes `overview.md`. After this change, it also writes `overview.docx` in the same step, using the same content.

**Where it lives:**
- `scriptorium/overview/` — add a post-write hook in the overview generator that calls `render_overview_docx(md_path, docx_path, corpus_path)` immediately after the `.md` is finalized.
- Failure to render the `.docx` never fails the overview step. The `.md` is the source of truth; the `.docx` is a best-effort derivative. On docx-render failure: log to `audit.jsonl` with `event: "overview_docx_failed"` and move on. The `.md` is already saved.
- `generating-overview` skill text picks up a one-line note: "We also write `overview.docx` automatically — most users will open that."

**Conversion module (`scriptorium/export.py`):**
- `render_overview_docx(md_path, docx_path, corpus_path)` — uses `python-docx`. Walks the known overview markdown shape (H1/H2/H3 headings, paragraphs, bullet/ordered lists, tables, inline bold/italic/code). Scriptorium generates its own markdown, so the converter only has to handle shapes Scriptorium itself emits — not arbitrary markdown.
- Always regenerated from `overview.md`. User edits live in `.md`. The `.docx` is overwritten on every overview run.

**Citation enrichment:**
- For each `[paper_id:locator]` in `overview.md`, the converter looks up `paper_id` in `data/corpus.jsonl`.
- Renders in the docx as `(First-author Year, p. locator)`, with a hyperlink to the paper stub in `sources/papers/<paper_id>.md`.
- Corpus lookup miss → leaves the raw `[paper_id:locator]` text in the docx and records the miss in the audit event. No silent drops.

**Audit event schema** (appended on each overview render):
```json
{
  "ts": "2026-04-23T15:02:11Z",
  "event": "overview_rendered",
  "wrote": ["overview.md", "overview.docx"],
  "source_sha256": "<overview.md sha>",
  "citation_misses": []
}
```

On docx failure:
```json
{
  "ts": "...",
  "event": "overview_docx_failed",
  "wrote": ["overview.md"],
  "error": "<one-line error message>"
}
```

**Dependencies** added to `pyproject.toml`: `python-docx`. Pure Python, Cowork-safe.

### 3. Code changes

- **`scriptorium/paths.py`** — update `ReviewPaths` so existing properties resolve to the new locations (`evidence` → `data/evidence.jsonl`, `audit_md` → `audit/audit.md`, `overview_archive` → `audit/overview-archive`, `pdfs` → `sources/pdfs`, `papers` → `sources/papers`, `extracts` → `data/extracts`). Add new helper properties where useful: `audit_dir`, `data_dir`, `sources_dir`, `scriptorium_dir`, `lock`, `overview_docx`. No renames — call sites keep working; paths just move.
- **`scriptorium/storage/`** — update all writers to target the new paths via `ReviewPaths`.
- **`scriptorium/overview/`** — after `overview.md` is written, call `render_overview_docx` and append the audit event.
- **`scriptorium/export.py`** — new module containing `render_overview_docx` and its helpers (heading/list/table walkers, citation enricher).
- **`skills/generating-overview/SKILL.md`** — one-line addition noting that `.docx` is written automatically.
- **`pyproject.toml`** — add `python-docx` to runtime deps.
- **`CHANGELOG.md`** — entry for layout change + Word overview.
- **`README.md`** — one-sentence mention in the features list: "The overview is written as both Markdown and Word, so you can hand the `.docx` to a committee member who doesn't use Obsidian."

### 4. Migration of existing `values-review/`

Performed manually by Claude in a single session, not shipped as a command:

1. `mkdir -p values-review/{sources,data,audit,.scriptorium}`
2. Move `values-review/pdfs/` → `values-review/sources/pdfs/`.
3. Move `values-review/papers/` → `values-review/sources/papers/`.
4. Move `values-review/evidence.jsonl` → `values-review/data/evidence.jsonl`.
5. Move `values-review/corpus.jsonl` → `values-review/data/corpus.jsonl`.
6. Move `values-review/extracts/` → `values-review/data/extracts/`.
7. Move `values-review/audit.md` and `audit.jsonl` → `values-review/audit/`.
8. Move `values-review/overview.failed.*.md` → `values-review/audit/overview-archive/`.
9. The existing `bib/` and `outputs/` folders appear empty from the earlier listing; delete if empty, otherwise inspect and move contents to `sources/` or `audit/` as appropriate.
10. Append a `migrated_layout` event to `audit/audit.jsonl` listing every rename.

No files are deleted. The operation is idempotent — re-running it is a no-op.

### 5. Testing

| Test | What it proves |
|---|---|
| `test_overview_docx_shape.py` | Fixture `overview.md` → `.docx`; assert heading levels, bullets, ordered lists, tables, bold/italic/code render correctly via python-docx inspection. |
| `test_citation_enrichment.py` | Hit path: `[paper_id:p.12]` + matching corpus row → `(Smith 2024, p. 12)` rendered with hyperlink to `sources/papers/<paper_id>.md`. Miss path: unknown `paper_id` left raw in docx and logged to the audit event. |
| `test_overview_audit_event.py` | Overview run writes both files; one `overview_rendered` audit event with source sha256 and citation-miss list. |
| `test_overview_docx_failure_isolation.py` | Inject a docx render failure; assert `.md` still saved, `overview_docx_failed` event appended, overview step returns success. |
| `test_paths_new_layout.py` | `ReviewPaths.evidence` resolves to `data/evidence.jsonl`, `audit_md` to `audit/audit.md`, `pdfs` to `sources/pdfs`, etc. |

All fixtures live under `tests/fixtures/overview/`.

## Non-goals

- No `.docx` → `.md` import. Word is a one-way handoff format.
- No user-facing command or skill for export — overview dual-write is automatic and invisible.
- No `.docx` for synthesis / contradictions, and no `.xlsx` for evidence / corpus. If a real user request arrives later, add them as separate specs.
- No shipped migration command. The existing `values-review/` is migrated once, manually.

## Open questions

None at design-approval time. Implementation plan (next step via `writing-plans`) will sequence the work into atomic commits.
