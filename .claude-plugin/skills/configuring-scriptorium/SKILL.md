---
name: configuring-scriptorium
description: Use when the user wants to set, inspect, or change scriptorium configuration (Unpaywall email, OpenAlex polite-pool email, Semantic Scholar API key, default backend, languages). Walks a one-question-at-a-time dialogue. In Claude Code, persists through `scriptorium config set KEY VALUE` so user input never reaches a shell as code. In Cowork, persists to a user-memory note.
---

# Configuring Scriptorium

This skill walks the user through scriptorium configuration, one question at a time, and writes each answer back immediately. The goal is zero TOML hand-editing — the user never opens the file.

**Discipline note (defect-fix #3):** in Claude Code, **every write goes through `scriptorium config set KEY VALUE`**. Argparse handles quoting, so a user value like `O'Malley <tim@example.com>` cannot escape into Python code. Never invoke an inline Python interpreter to write config. Never construct a Python source string from user input.

## Settings

| Key | Required? | What it's for |
|---|---|---|
| `unpaywall_email` | **Required** before any full-text cascade runs | Unpaywall's free API requires a contact email per ToS — mandatory |
| `openalex_email` | Optional (defaults to `unpaywall_email` if unset) | OpenAlex "polite pool" — better rate limits |
| `semantic_scholar_api_key` | Optional | Raises the Semantic Scholar rate limit from ~100 req/5min to ~1 req/sec |
| `default_backend` | Optional (default `openalex`) | `openalex` or `semantic_scholar` |
| `languages` | Optional (default `["en"]`) | Screening filter — JSON-encoded list string |

## Dialogue (same in both runtimes; storage path differs)

For each setting in order:

1. **Read the current value.**
   - In Claude Code: `scriptorium config get <key>`.
   - In Cowork: read the `scriptorium-config` note via the state adapter; if absent, treat as all-defaults.
2. **Ask the user in one short sentence:** "Current `unpaywall_email` is `<value>`. Keep it or change?" If the value is `(unset)` and the key is required, say so.
3. **Write their reply back.**
   - In Claude Code: `scriptorium config set <key> <value>`. Argparse quotes the value — safe for any input string. Do **not** shell-execute an inline interpreter.
   - In Cowork: update the `scriptorium-config` note with the new key/value pair. Keep it TOML-shaped for parity with the CC file.

## Required-first ordering

Start with `unpaywall_email`. If the user tries to skip it, say: "Unpaywall requires a contact email — the full-text cascade will refuse to run without it. Please set one now." Then ask.

After the required setting is in place, walk the four optional settings in the order above. For each, surface the current value and move on quickly if the user says "keep it."

## End-of-dialogue summary

Print one short block:

```
Config updated:
  unpaywall_email = <value>
  openalex_email = <value>
  semantic_scholar_api_key = <set|unset>
  default_backend = <value>
  languages = <value>
```

Then: "Stored in `<path>` (CC) or `<note>` (Cowork). Run `scriptorium config get <key>` any time to inspect."

## Failure modes

- **User pastes a multi-line value.** Reject gently ("config values are single-line"); ask again.
- **`scriptorium config set` exits non-zero.** Surface stderr verbatim and ask the user to retry or skip.
- **Cowork note write fails.** Fall back to session-only: tell the user the setting will not persist to the next session.

## v0.3 additions

New config keys:
- `obsidian_vault` — path to Obsidian vault root; enables vault-relative paths.
- `notebooklm_enabled` — boolean; set `true` only after `nlm doctor` succeeds.
- `notebooklm_prompt` — boolean; set `false` to suppress the end-of-review prompt.

In Cowork mode there is no local config file. Store config in a user-memory note named `scriptorium-config`, TOML-shaped.
