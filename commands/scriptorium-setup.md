---
name: scriptorium-setup
description: Configure Scriptorium after the CLI and plugin are installed. Collects unpaywall email, obsidian vault path, and optional NotebookLM MCP CLI.
---

# /scriptorium-setup

## Step 1: Preflight

Run `scriptorium version`. If it fails, stop and tell the user:

> Scriptorium CLI is not on PATH. Run `pipx install scriptorium-cli`, restart Claude Code, then retry `/scriptorium-setup`.

## Step 2: Detect existing values

Before asking anything, read the session context silently:
- **email**: look for the user's email in CLAUDE.md or memory
- **vault**: look for an Obsidian vault path in CLAUDE.md or memory

## Step 3: Ask all questions at once using AskUserQuestion

Call the `AskUserQuestion` tool with these three questions in a **single call** (all at once, not one at a time):

**Question 1** — `header: "Email"`
> "Which email should Scriptorium use for Unpaywall and OpenAlex lookups?"

Options (if email was detected, e.g. `user@example.com`):
- `{ label: "user@example.com (Recommended)", description: "Found in your session — no changes needed" }`
- `{ label: "Use a different email", description: "Type a new address when prompted" }`

Options (if no email detected):
- `{ label: "I'll type my email", description: "Enter it in the next step" }`

**Question 2** — `header: "Obsidian vault"`
> "Where is your Obsidian vault?"

Options (if vault path was detected):
- `{ label: "Use detected path (Recommended)", description: "<detected path>" }`
- `{ label: "Enter a different path", description: "Specify a custom vault location" }`
- `{ label: "Skip for now", description: "Configure later with /lit-config" }`

Options (if no vault detected):
- `{ label: "I'll type the path", description: "Absolute path to the folder containing .obsidian/" }`
- `{ label: "Skip for now", description: "Configure later with /lit-config" }`

**Question 3** — `header: "NotebookLM"`
> "Enable NotebookLM publishing?"

Options:
- `{ label: "No, skip for now (Recommended)", description: "Enable later with /lit-config when you're ready to publish" }`
- `{ label: "Yes, enable it", description: "Publishes your reviews to Google NotebookLM automatically" }`

## Step 4: Collect any free-text answers

If the user chose "Use a different email" or "I'll type my email", ask for it now (plain text prompt, one question).

If the user chose "Enter a different path" or "I'll type the path", ask for it now (plain text prompt, one question).

## Step 5: Write config.toml

Write to `config.toml` in the current working directory:

```toml
[scriptorium]
unpaywall_email = "<value>"
obsidian_vault = "<value or empty string>"
notebooklm_enabled = false
```

Set `notebooklm_enabled = true` only if the user explicitly chose "Yes, enable it".
Leave `obsidian_vault` as an empty string if the user skipped it.

## Step 6: Confirm

Tell the user:

> Configuration saved to `config.toml`. Run `/lit-config` to review your settings, then `/lit-review` to start your first literature review.
