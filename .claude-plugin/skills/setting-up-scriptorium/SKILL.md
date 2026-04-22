---
name: setting-up-scriptorium
description: Install Scriptorium v0.3 end-to-end (package, plugin, vault, Unpaywall, NotebookLM) with a resumable setup-state.
---

# setting-up-scriptorium

This skill owns the `/scriptorium-setup` and `scriptorium init` flows (§7).
It's idempotent and resumable via `~/.config/scriptorium/setup-state.json`.

## Precheck

- Python `>=3.11`
- Writable `$HOME`
- Current shell available for subprocesses

## Install the package

Prefer `uv`:

```bash
uv pip install scriptorium-cli
```

Fallback:

```bash
pip install scriptorium-cli
```

Verify:

```bash
scriptorium --version   # must print "scriptorium 0.3.1"
```

## Install the Claude Code plugin

Copy `.claude-plugin/` into the Claude Code plugin directory via the
existing convention, then prompt the user to restart Claude Code.

## Configure Obsidian vault

Scan `~/Documents/Obsidian/`, `~/Obsidian/`,
`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/`, and any
existing `obsidian_vault`. Accept `--vault <path>` if passed. Only accept
a directory whose `.obsidian/` subdirectory exists. Persist:

```bash
scriptorium config set obsidian_vault <path>
```

## Collect Unpaywall email

```bash
scriptorium config set unpaywall_email <email>
```

## NotebookLM (skip with --skip-notebooklm)

Install the CLI (either works):

```bash
uv tool install notebooklm-mcp-cli
# or
pipx install notebooklm-mcp-cli
```

Show the dedicated-account warning verbatim, then:

```bash
nlm login
nlm doctor
scriptorium config set notebooklm_enabled true
```

Only set `notebooklm_enabled true` after `nlm doctor` exits zero.

## Dedicated-account warning

> Use a dedicated Google account for NotebookLM integration, not your primary
> account. The nlm CLI works via browser automation; Google may flag automated
> activity against your primary account. This is an upstream limitation of nlm,
> not Scriptorium.

## Resumable setup-state.json

After each step, append the step name to the `completed_steps` list in
`~/.config/scriptorium/setup-state.json`. On rerun, skip already-completed
steps after verifying their effect (e.g. `scriptorium --version`,
`nlm doctor`). On `Ctrl-C` during NotebookLM login, store
`notebooklm_enabled false`, exit `130`, and leave earlier steps intact.

## Closing message

```
You're set. Try /lit-review "your question" --review-dir reviews/<slug>
to kick off your first review.
```
