---
name: setting-up-scriptorium
description: Configure Scriptorium after the CLI and plugin are already installed. Collects unpaywall_email, obsidian_vault, and optional NotebookLM settings.
---

# setting-up-scriptorium

This skill owns the `/scriptorium-setup` flow. It handles post-install configuration only.

## Prerequisites (already completed before running this skill)

1. CLI installed via `pipx install scriptorium-cli`
2. Plugin installed in Claude Code:
   ```
   /plugin marketplace add Jerrymwolf/Scriptorium
   /plugin install scriptorium@scriptorium-local
   ```

## Preflight check

Run `scriptorium --version`. If it fails, stop and tell the user:

`Scriptorium CLI is not on PATH. Run \`pipx install scriptorium-cli\`, restart Claude Code, then retry this command.`

## Collect configuration

### unpaywall_email

Required for OpenAlex/Unpaywall lookups. Must be a valid email address. Used to identify your API requests to Unpaywall — no account creation needed, just a real email for rate-limit tracking.

```bash
scriptorium config set unpaywall_email <email>
```

### obsidian_vault

Absolute path to the user's Obsidian vault (the folder containing `.obsidian/`). Optional but strongly recommended — enables automatic note export after each review.

Only accept a directory whose `.obsidian/` subdirectory exists. Persist:

```bash
scriptorium config set obsidian_vault <path>
```

### notebooklm_enabled

Whether to enable NotebookLM publishing. Optional; defaults to false.

If the user wants NotebookLM, they must have `notebooklm-mcp-cli` installed separately:

```bash
pipx install notebooklm-mcp-cli
```

Only set `notebooklm_enabled true` after confirming `nlm doctor` exits zero.

## Write config.toml

Write to `config.toml` in the current workspace:

```toml
[scriptorium]
unpaywall_email = "<value>"
obsidian_vault = "<value>"
notebooklm_enabled = false
```

## Closing message

```
Configuration saved to config.toml. Run /lit-config to verify, then /lit-review to start your first review.
```
