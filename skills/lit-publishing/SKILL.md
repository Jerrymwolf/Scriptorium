---
name: lit-publishing
description: Use as the publishing-phase entry point. This skill is a gate, not a runtime — it enforces phase-state preconditions (synthesis complete, contradiction-check complete) before handing off to `publishing-to-notebooklm` for the actual `nlm` CLI mechanics. Fires from `running-lit-review` step 7 and from any direct user request to publish a finished review.
---

# Literature Publishing — phase-state gate

**Defensive fallback (fire `using-scriptorium` first):** If the three-discipline preamble (Evidence-first claims / PRISMA audit trail / Contradiction surfacing) is not already loaded for this session, invoke `using-scriptorium` before continuing. Primary injection runs via the Claude Code `SessionStart` hook and the Cowork MCP `instructions` field — this fallback covers the rare case where neither fired.

## Single role: enforce preconditions, then hand off

`lit-publishing` is intentionally thin. Its only job is to read `phase-state.json`, refuse if synthesis or contradiction-check has not actually completed, and then hand off to `publishing-to-notebooklm` for the runtime mechanics (the verified `nlm` CLI surface, the Cowork-degradation block, the audit append). Do not re-implement any of that here — route to `publishing-to-notebooklm` once the gate passes.

This split is deliberate. `running-lit-review` step 7 fires `lit-publishing` (pipeline path → gate required). Direct user requests like "make a podcast of this" route through `using-scriptorium` straight to `publishing-to-notebooklm` (ad-hoc path → trust the user, the gate is moot). Both endpoints converge on the same mechanics skill.

## HARD-GATE — synthesis and contradiction must be complete

`lit-publishing` reads `<review_root>/.scriptorium/phase-state.json` at startup. The gate refuses to proceed unless **both** of these phases are at status `"complete"`:

- `phase-state.json::phases.synthesis.status` — must be `"complete"`. If not, STOP and tell the user that publishing is blocked because the synthesis phase has not finished its mandatory cite-check. Point them at `lit-synthesizing`.
- `phase-state.json::phases.contradiction.status` — must be `"complete"`. If not, STOP and tell the user that publishing is blocked because contradictions have not been surfaced. Point them at `lit-contradiction-check`.

If either field is `pending`, `running`, or `failed`, refuse and name the specific phase that blocks publish so the user knows which skill to fire next. Do not paper over a missing phase by re-running it inside `lit-publishing` — each gate failure is the upstream skill's responsibility to fix.

If `enforce_v04=false` (advisory mode), warn the user that publishing is normally gated, append an `audit.jsonl` row with `mode=advisory` naming the failing phase, and proceed only after explicit user acknowledgement. Silent bypass is forbidden in either mode — advisory means *warn loudly and require acknowledgement*, not *suppress the warning*.

## Phase 5 forward-reference — reviewer state

Once Phase 5 lands, `lit-publishing` also gates on reviewer state — `phase-state.json::phases.synthesis.verifier_signature` must reflect a passing cite-reviewer + contradiction-reviewer verdict. This forward-reference is intentional: today the gate is content-bytes only (status=complete with a sha256 signature of the artifact); after Phase 5, the same signature field carries a stricter verdict. When Phase 5 lands, update this section so the reviewer dependency is no longer forward-looking.

## Hand-off to `publishing-to-notebooklm`

When both gates pass, hand off to `publishing-to-notebooklm`. That skill owns:

- The verified `nlm` CLI surface (`nlm doctor`, `nlm notebook create`, `nlm source add`, `nlm audio create`, `nlm slides create`, `nlm mindmap create`, `nlm video create`).
- The Cowork-degradation block (`scriptorium publish` detects Cowork mode and emits the "publishing requires local shell access" message instead).
- The audit append (`## Publishing` subsection in `audit.md`, `publishing` row in `audit.jsonl`).

Do not duplicate any of this here. The hand-off is the entire post-gate behavior of this skill.

## Failure-mode summary

| Condition | Behavior |
|---|---|
| `synthesis.status != "complete"` (enforce) | STOP; name the failing phase; point at `lit-synthesizing` |
| `contradiction.status != "complete"` (enforce) | STOP; name the failing phase; point at `lit-contradiction-check` |
| Either failing under `enforce_v04=false` | Warn, append advisory audit row, require explicit user acknowledgement before hand-off |
| Both `complete` | Hand off to `publishing-to-notebooklm` |
