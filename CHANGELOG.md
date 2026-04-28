# Changelog

All notable changes to this project are documented in this file.

## Unreleased

## 0.4.0 — 2026-04-28

v0.4 ships **Layer A** (discipline enforcement) and **Layer B** (reviewer and
extraction enforcement) so Scriptorium's three disciplines — evidence-first
claims, PRISMA audit trail, contradiction surfacing — are objectively
verifiable in both Claude Code and Cowork.

### Added (Layer A — discipline enforcement)
- `skills/using-scriptorium/INJECTION.md` is the shared discipline preamble;
  the Claude Code `SessionStart` hook injects it on every session and the
  Cowork `scriptorium-mcp` server exposes the same prose via the MCP
  `instructions` field.
- `phase-state.json` artifact and `scriptorium.phase_state` API track the
  review's current phase, gate signatures, and reviewer/override decisions
  with append-only auditability. Mutating an upstream artifact auto-downgrades
  the phase so a stale gate cannot survive a re-run.
- HARD-GATE blocks added to phase-critical skills (`lit-screening`,
  `lit-extracting`, `lit-synthesizing`, `lit-publishing`) so a runtime that
  ignores the injection still hits a stop-the-world gate at the skill body.
- `verification-before-completion-scriptorium` skill enforces a
  Scriptorium-specific completion check (cite scan, audit-row presence,
  contradiction file) before a phase can be declared done.
- `using-scriptorium` rewritten with an explicit runtime probe and a
  defensive skill-router fallback. Every downstream phase skill now opens
  with a red-flag table and runtime-honesty wording.
- `enforce_v04` and `extraction_parallel_cap` config keys (advisory by
  default; flips to blocking via config).

### Added (Layer B — reviewer and extraction enforcement)
- Claude Code extraction orchestration with `extraction_parallel_cap`
  enforcement; Cowork extraction backend dispatch over `mcp`,
  `notebooklm`, or `sequential` (degraded). Backend literal is recorded on
  every `extraction.dispatch` audit row.
- Synthesis-exit reviewer gate adds cite and contradiction reviewers; in
  Claude Code these run as parallel subagents, in Cowork they run via the
  `notebooklm` reviewer branch or — when NotebookLM is absent — the
  `inline_degraded` branch (warning row, no parity claim).
- Audited override path: a failed reviewer gate blocks publish until an
  explicit, signature-bound override is recorded. Override invalidates if
  upstream artifacts change.
- New `scriptorium.mcp` server exposes six tools: `extract_paper`,
  `finalize_synthesis_reviewers`, `phase_show`, `phase_set`, `phase_override`,
  `verify_gate`.

### Migration and advisory rollout
- `scriptorium migrate-review --to 0.4 <review-dir>` backfills
  `phase-state.json` for legacy reviews. Idempotent; fails closed on
  corrupted state.
- v0.4 ships in **advisory** mode: `enforce_v04 = false` is the default
  so legacy reviews stay usable. Set `enforce_v04 = true` in
  `~/.scriptorium/config.toml` to flip to blocking.
- New exit code `E_REVIEWER_INVALID = 22` for reviewer-validation failures.

### Cowork smoke matrix
- `docs/cowork-smoke.md` adds the **Extraction backend matrix** and
  **Reviewer branch matrix** so the runtime-degradation contract is
  catchable by eye for `mcp` / `notebooklm` / `sequential` extraction and
  `notebooklm` / `inline_degraded` reviewer branches.

### Added (overview rendering, carried forward from Unreleased)
- Automatic `overview.docx` render alongside `overview.md` on every overview
  generation. Citations resolve to `(Author Year, locator)` with a
  DOI → URL → local-stub hyperlink (in that precedence order). Docx render
  is best-effort; failure emits an `overview_docx_failed` audit event but
  never blocks the `.md` write.

### Changed
- Review folder layout reorganized into a hybrid structure: deliverables at
  root (`overview.md`, `overview.docx`, `synthesis.md`, `contradictions.md`,
  `scope.json`, `references.bib`); inputs under `sources/`; machine-readable
  data under `data/`; audit trail and failed-overview archive under
  `audit/`; internal state under `.scriptorium/`.
- Failed overview drafts now land in `audit/overview-archive/` instead of
  the review root.

### Dependencies
- Added `python-docx>=1.1,<2`.
- Added `mcp>=1.0` for the Cowork-facing `scriptorium.mcp` server.

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
