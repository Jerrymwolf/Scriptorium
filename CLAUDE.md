# Scriptorium — plugin-level context

Scriptorium is a literature-review plugin architected in the style of [Superpowers](https://github.com/obra/superpowers). Skills here apply the same pattern — self-contained folders with `SKILL.md` files that Claude loads on demand — to the craft of literature review.

## What Scriptorium enforces (three disciplines)

1. **Evidence-first claims.** Every sentence in `synthesis.md` is either a citation `[paper_id:locator]` that maps to a row in `evidence.jsonl`, or it is flagged / stripped. The `lit-synthesizing` skill ends with a mandatory cite-check step; Claude Code additionally runs `scriptorium verify` via a PostToolUse hook for redundancy.
2. **PRISMA audit trail.** Every search, screen, extraction, and reasoning decision appends to `audit.jsonl` (and human-readable `audit.md`). The trail is reconstructable end-to-end.
3. **Contradiction surfacing.** The `lit-contradiction-check` skill groups evidence by concept and names disagreement explicitly, instead of averaging findings into a single bland claim.

## Two runtimes, one prose layer

Scriptorium runs in **Claude Code** and in **Cowork**. Skills are the only surface both runtimes agree on — slash commands, hooks, Bash, and the filesystem exist only in CC; Cowork has platform MCPs (Consensus, Scholar Gateway, PubMed, NotebookLM) and an ephemeral sandbox.

The `using-scriptorium` skill opens with a runtime probe and dispatches to the right path. Every other skill is written to be runtime-agnostic: it describes the *intent* of each step and lists the runtime-specific tools that realize it.

## Repository layout

- `scriptorium/` — Python package (CLI only used in Claude Code)
- `skills/` — portable prose skills (both runtimes)
- `commands/` — slash commands (Claude Code only)
- `hooks/` — PostToolUse hooks (Claude Code only)
- `.claude-plugin/plugin.json` — plugin manifest
- `.claude-plugin/marketplace.json` — marketplace manifest for `/plugin install scriptorium@scriptorium-local`

## When in doubt

Fire `using-scriptorium` first. It teaches the runtime probe and the three disciplines, then hands off to the skill that matches the phase the user is in (search, screen, extract, synthesize, contradiction-check, audit, publish).
