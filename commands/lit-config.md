---
description: Walk a one-question-at-a-time dialogue to set scriptorium configuration (Unpaywall email required; OpenAlex/Semantic Scholar/defaults optional). Delegates to the configuring-scriptorium skill. Every write goes through `scriptorium config set KEY VALUE` — no shell-exec of Python. Usage: /lit-config.
argument-hint: ""
---

# /lit-config

Activate the `configuring-scriptorium` skill and run its dialogue.

The skill walks each setting in required-first order, calls `scriptorium config set KEY VALUE` for each write, and surfaces a final summary. Do not hand-edit TOML files. Do not shell-execute an inline interpreter to persist values.

## v0.3 config keys

- `obsidian_vault` (string path) — enables vault-relative review paths and
  native Obsidian output defaults. See §3.2.
- `notebooklm_enabled` (boolean) — set by `/scriptorium-setup` only after
  `nlm doctor` succeeds. Gate for the end-of-review prompt.
- `notebooklm_prompt` (boolean) — set to `false` to suppress the end-of-review
  NotebookLM prompt even when `notebooklm_enabled` is `true`.
