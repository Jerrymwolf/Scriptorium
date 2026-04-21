---
name: publishing-to-notebooklm
description: Publish a completed Scriptorium review to NotebookLM via the verified `nlm` CLI (audio, deck, mindmap, video).
---

# publishing-to-notebooklm

Use this skill when a review has finished cite-check, `overview.md`,
`synthesis.md`, and `contradictions.md` are written, and the user wants a
NotebookLM artifact. v0.3 uses the `nlm` CLI exclusively; the `lit-publishing`
MCP/Studio instructions are removed.

## Preconditions

1. `notebooklm_enabled` is `true` in Scriptorium config.
2. `nlm doctor` returns zero (install `notebooklm-mcp-cli` with
   `uv tool install notebooklm-mcp-cli` then run `nlm login` — see the
   `setting-up-scriptorium` skill for first-time setup).
3. The review directory contains `overview.md`, `synthesis.md`,
   `contradictions.md`, `evidence.jsonl`, and `pdfs/`.

## Commands (verified v0.3 surface)

| Step | Command |
|---|---|
| Login | `nlm login` |
| Diagnose | `nlm doctor` |
| Create notebook | `nlm notebook create <title>` |
| Upload source | `nlm source add <notebook_id> --file <path>` |
| Create audio | `nlm audio create <notebook_id>` |
| Create slide deck | `nlm slides create <notebook_id>` |
| Create mind map | `nlm mindmap create <notebook_id>` |
| Create video | `nlm video create <notebook_id>` |

User-facing "deck" maps to `nlm slides create`.

## Normal flow

In Claude Code or terminal, prefer the CLI wrapper:

```bash
scriptorium publish --review-dir <path> --generate <audio|deck|mindmap|video|all>
```

`scriptorium publish` acquires `<review-dir>/.scriptorium.lock`, verifies
files, calls `nlm doctor`, creates the notebook, uploads sources in this
order — `overview.md`, `synthesis.md`, `contradictions.md`,
`evidence.jsonl`, alphabetical `pdfs/*.pdf` (symlinks skipped), paper stubs
only if `stubs` is in `--sources` — waits 1s between uploads, then triggers
the artifact(s). Each `nlm` subprocess has a five-minute timeout.

## Prior-publish prompt

If `audit.md` records a prior publish to the same notebook name, the CLI
prompts `Proceed and create a new notebook? [y/N]`. Pass `--yes` in
scripts or when running non-interactively.

## Cowork degradation

Cowork does not have local shell access. `scriptorium publish` detects
Cowork mode (via `SCRIPTORIUM_COWORK` / `SCRIPTORIUM_FORCE_COWORK`) and
emits this block instead of calling `nlm`:

> Publishing to NotebookLM requires local shell access, which Cowork doesn't grant.
> (Full block rendered by `scriptorium publish` — see §9.6.)

## Audit

On success or partial failure, `scriptorium publish` appends a
`## Publishing` subsection to `audit.md` and a `publishing` row to
`audit.jsonl`. The row carries notebook name/id/URL, attempted and
uploaded file manifests, artifact ids (or failing command + stderr),
and a privacy note.
