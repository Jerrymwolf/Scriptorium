# Changelog

All notable changes to this project are documented in this file.

## 0.3.1 — 2026-04-22

### Fixed

- Plugin layout: moved `commands/`, `skills/`, `hooks/`, `CLAUDE.md` to plugin root so Claude Code actually loads slash commands
- Added `.claude-plugin/marketplace.json` so `/plugin install scriptorium@scriptorium-local` works from GitHub
- Removed `scripts/install_plugin.sh` — the symlink-into-~/.claude/plugins/ approach was silently doing nothing in modern Claude Code
- `/scriptorium-setup` rewritten as post-install config only (no longer pretends to install the plugin)
- Hard preflight added to `/lit-config` and `/lit-review`: CLI-missing stops immediately with install instructions

### Migration for early users

If you ran the old `install_plugin.sh`, remove the stale symlink:

```bash
rm -rf ~/.claude/plugins/scriptorium
```

Then follow the new install flow in the README.

## 0.3.0 — 2026-04-20

### Added
- Native Obsidian output by default: paper stubs, wikilinks, frontmatter,
  Dataview queries.
- Executive briefing `overview.md` with nine corpus-bounded sections,
  per-section provenance, and deterministic seeding.
- Seamless NotebookLM publish flow over the verified `nlm` CLI, with
  `/lit-podcast`, `/lit-deck`, `/lit-mindmap` wrappers.
- `/scriptorium-setup` and `scriptorium init` for Claude-Code-assisted and
  terminal-fallback installs with resumable setup-state.
- `scriptorium migrate-review` for moving v0.2 reviews forward in place.
- `obsidian_vault`, `notebooklm_enabled`, `notebooklm_prompt` config keys.
- `.scriptorium.lock` review lock; §11 exit codes; `audit.jsonl` status enum
  with UTC `Z` timestamps; corruption recovery for audit and config.
- Cowork degradation block for publish attempts.

### Changed
- PyPI distribution renamed to `scriptorium-cli`. Console command, import
  path, and plugin name remain `scriptorium`.
- v0.3 generation writes citations as `[[paper_id#p-N]]`. Verifier also
  accepts legacy `[paper_id:loc]` form.
- Skill `lit-publishing` renamed to `publishing-to-notebooklm`; body
  rewritten to reference verified `nlm` commands only.

### Removed
- Stale v0.2 NotebookLM command shapes from docs, skills, and slash commands.

### Migration
Run `scriptorium migrate-review <review-dir>` once per existing review. The
command is idempotent and fails closed on corrupted state.
