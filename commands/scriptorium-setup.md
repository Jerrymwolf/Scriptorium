---
name: scriptorium-setup
description: Configure Scriptorium after the CLI and plugin are installed. Collects unpaywall email, obsidian vault path, and optional NotebookLM MCP CLI.
---

# /scriptorium-setup

This command assumes Scriptorium is already installed:

1. CLI: `pipx install scriptorium-cli`
2. Plugin (in Claude Code):
   ```
   /plugin marketplace add Jerrymwolf/Scriptorium
   /plugin install scriptorium@scriptorium-local
   ```

## What this command does

### Step 1: Preflight

Run `scriptorium --version`. If it fails or is not on PATH, stop and tell the user:

`Scriptorium CLI is not on PATH. Run \`pipx install scriptorium-cli\`, restart Claude Code, then retry this command.`

### Step 2: Collect configuration

Ask the user:

1. **unpaywall_email** — required for OpenAlex/Unpaywall lookups. Must be a valid email.
2. **obsidian_vault** — absolute path to their Obsidian vault (the folder containing `.obsidian/`). Optional but strongly recommended.
3. **notebooklm_enabled** — whether to enable NotebookLM publishing. Optional; defaults to false.

### Step 3: Write config.toml

Write to `config.toml` in the current workspace:

```toml
[scriptorium]
unpaywall_email = "<value>"
obsidian_vault = "<value>"
notebooklm_enabled = false
```

### Step 4: Confirm

Tell the user: "Configuration saved to config.toml. Run `/lit-config` to verify, then `/lit-review` to start your first review."
