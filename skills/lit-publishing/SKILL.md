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

## Phase 5 reviewer gate — current state

Phase 5 (T14/T15) has landed. `phase-state.json::phases.synthesis.status` is now promoted to `"complete"` only when both reviewer agents (`lit-cite-reviewer` and `lit-contradiction-reviewer`) return verdict `"pass"` AND `synthesis.md` exists; the cite-check, contradiction-check, and aggregation rows all land in `audit.jsonl`. A failing reviewer leaves the status at `"running"` (recoverable — re-run after fixing) or `"failed"` (terminal — caller decides whether to retry or override). The `verifier_signature` field is the sha256 of the synthesis bytes the reviewers just signed off on, so any post-pass mutation auto-downgrades the phase back to `"running"` on the next read.

When the reviewer gate misfires (false negatives, runaway model output, gate not implemented for a given runtime), the audited override path takes status to `"overridden"`: `scriptorium phase override synthesis --reason "..."` in Claude Code (TTY-guarded — `--yes` for non-interactive use), or `phase_override(review_dir, "synthesis", reason, actor, confirm=True)` via the Cowork MCP tool (explicit `confirm=True` marker). Both runtimes write a `phase.override` row to `audit.jsonl` carrying `phase`, `reason`, `actor`, `ts`, and `runtime`; the publish gate accepts `"overridden"` as equivalent to `"complete"` so publish proceeds.

## Audited override

When the reviewer gate misfires, an audited override unblocks publish without rewriting the reviewer history. The override sets `phase-state.json::phases.synthesis.status = "overridden"` (and likewise for `phases.contradiction` if that gate is the one stuck), records `{reason, actor, ts}` under `phase-state.json::phases.<phase>.override`, AND appends a `phase.override` row to `audit.jsonl` carrying the same fields plus `runtime`.

The override is irreversible in the audit sense: a second override of the same phase appends a SECOND `phase.override` row — the first is never rewritten or removed. Two literal forms exist, one per runtime:

- **Claude Code (TTY-guarded):** `scriptorium phase override <phase> --reason "..."` reads `stdin.isatty()`. On a real TTY the command prompts `Proceed with audited override of <phase>? [y/N]` and proceeds only on `y`/`yes`. Pass `--yes` to skip the prompt for non-interactive scripted use; without `--yes`, a non-TTY stdin is refused with `E_USAGE` and no phase-state mutation.
- **Cowork (explicit-marker):** `phase_override(review_dir, phase, reason, actor, confirm=True)` exposed by the Scriptorium MCP server. The `confirm=True` argument is the Cowork-side stand-in for the CC TTY confirmation; the check is `confirm is True`, so a truthy non-bool ("yes", `1`) does NOT pass. Without it the tool returns `{"error": ..., "code": E_USAGE}` and does not mutate phase-state.

The publish gate (`scriptorium publish`) treats `"overridden"` identically to `"complete"` — both unblock publish. Under `enforce_v04=true` an incomplete-and-not-overridden gate returns `E_REVIEW_INCOMPLETE` (4); under `enforce_v04=false` (advisory mode, the v0.4.0 default) the same condition writes a warning to stderr, appends a `publish.advisory` audit row, and proceeds. The blocking branch appends a `publish.blocked` audit row instead.

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
