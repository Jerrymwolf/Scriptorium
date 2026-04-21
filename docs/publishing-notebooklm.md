# Publishing to NotebookLM (v0.3)

## Preconditions

- `notebooklm_enabled = true` in Scriptorium config.
- `nlm doctor` exits zero. First-time setup: install the CLI with
  `uv tool install notebooklm-mcp-cli` (or `pipx install notebooklm-mcp-cli`),
  then run `nlm login`. Use a dedicated Google account; `nlm` is
  browser-automated.
- Review directory contains `overview.md`, `synthesis.md`,
  `contradictions.md`, `evidence.jsonl`, and `pdfs/`.

## Happy path

```bash
scriptorium publish --review-dir reviews/caffeine-wm --generate audio
```

Internally this runs, in order:

1. `nlm doctor`
2. `nlm notebook create "Caffeine Wm"`
3. `nlm source add <id> --file overview.md`
4. `nlm source add <id> --file synthesis.md`
5. `nlm source add <id> --file contradictions.md`
6. `nlm source add <id> --file evidence.jsonl`
7. `nlm source add <id> --file pdfs/<each>.pdf` (alphabetical, symlinks skipped)
8. `nlm audio create <id>` (or `nlm slides create` / `nlm mindmap create`)

A success entry is appended to `audit.md` under `## Publishing` and to
`audit.jsonl` as a `publishing` row.

## Publishing

### Manual upload template (Cowork)

When Cowork is detected, `scriptorium publish` prints the degradation block
with a relative file list. Users can manually upload those files at
https://notebooklm.google.com then note the event in `audit.md`:

```markdown
### <timestamp> — NotebookLM (manual upload)

**Status:** success
**Destination:** NotebookLM (Google)
**Notebook:** "<Title>"
**URL:** <notebook URL>
**Sources uploaded**:
- overview.md
- synthesis.md
- contradictions.md
- evidence.jsonl

**Privacy note:** This action uploaded the listed files to Google-hosted
NotebookLM. Review the notebook's privacy settings.
```

Also uses `nlm notebook create` for the programmatic path.
