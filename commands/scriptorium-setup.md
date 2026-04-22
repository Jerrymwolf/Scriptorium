---
description: Install Scriptorium v0.3 and configure NotebookLM, Obsidian, and Unpaywall.
argument-hint: [--notebooklm] [--skip-notebooklm] [--vault <path>]
---

Use the `setting-up-scriptorium` skill to perform this install. The skill
is the authoritative flow; this slash command is a thin launcher.

Flags:

- `--notebooklm` — re-run only NotebookLM setup.
- `--skip-notebooklm` — install Scriptorium but skip NotebookLM.
- `--vault <path>` — use this Obsidian vault after verifying `.obsidian/`.

Outline (full body in `setting-up-scriptorium/SKILL.md`):

1. Precheck Python `>=3.11`, writable `$HOME`, current shell access.
2. Install package: prefer `uv pip install scriptorium-cli`; fallback
   `pip install scriptorium-cli`.
3. Verify `scriptorium --version` prints `scriptorium 0.3.1`.
4. Install `.claude-plugin/` and prompt the user to restart Claude Code.
5. Auto-detect Obsidian vault or accept `--vault <path>`; persist with
   `scriptorium config set obsidian_vault <path>`.
6. Ask for `unpaywall_email` and persist.
7. Unless `--skip-notebooklm`: install `notebooklm-mcp-cli`, show the
   dedicated-Google-account warning below, run `nlm login`, then verify
   with `nlm doctor`. Only set `notebooklm_enabled true` after
   `nlm doctor` succeeds.
8. Run `scriptorium doctor`.
9. Print: `You're set. Try /lit-review "your question" --review-dir reviews/<slug>`.

Dedicated-account warning (reproduce verbatim before `nlm login`):

> Use a dedicated Google account for NotebookLM integration, not your
> primary account. The nlm CLI works via browser automation; Google may
> flag automated activity against your primary account. This is an
> upstream limitation of nlm, not Scriptorium.
>
> Press Enter to acknowledge and continue, or Ctrl-C to skip NotebookLM setup.
