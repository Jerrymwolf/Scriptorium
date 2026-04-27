---
name: verification-before-completion-scriptorium
description: Use before claiming a Scriptorium phase is complete or before any phase transition; requires fresh `scriptorium verify` / `phase show` evidence (or the Cowork MCP equivalents) and forbids generic optimism. Fires on any wording that implies a phase finished, an artifact verified, or publishing is unblocked.
---

# Verification Before Completion — Scriptorium

Use this skill instead of `superpowers:verification-before-completion` whenever the work is Scriptorium-flavored — it adds the Scriptorium-specific evidence surface (`scriptorium verify`, `phase-state.json`, reviewer outputs, `audit.jsonl`).

## Iron Law

```
NO PHASE-COMPLETION CLAIMS WITHOUT FRESH SCRIPTORIUM VERIFICATION EVIDENCE
```

If you have not run `scriptorium verify --gate <gate>` (CC) or called the MCP `verify` tool (Cowork) **in this message**, you cannot claim a phase passed. Fresh means *this turn* — not last turn, not earlier in the conversation, not "I just changed code that should fix it".

**Violating the letter of this rule is violating the spirit.**

## Gate function

```
BEFORE claiming a phase is complete, transitioning a phase, or unblocking publish:

1. IDENTIFY: Which gate proves this claim?
   - scope        → `scriptorium verify --gate scope`        (Cowork: MCP `verify` with gate=scope)
   - synthesis    → `scriptorium verify --gate synthesis`    (Cowork: MCP `verify` with gate=synthesis)
   - publish      → `scriptorium verify --gate publish`      (Cowork: MCP `verify` with gate=publish)
   - overview     → `scriptorium verify --gate overview`     (Cowork: MCP `verify` with gate=overview)
2. RUN: Execute the FULL command this turn. No re-using prior output.
3. READ: Check exit code, the printed verdict, and any failure code.
4. CONFIRM phase-state: `scriptorium phase show` (CC) or MCP `phase_show` (Cowork).
   - `phases.<phase>.status` must be `"complete"`.
   - `phases.<phase>.verified_at` must be non-null.
   - `phases.<phase>.verifier_signature` must be non-null and current.
5. CONFIRM audit row: grep `audit.jsonl` for the corresponding action row
   (CC) or read the `audit` MCP resource (Cowork). The append must have
   actually landed — do not trust a `set_phase` call without rereading.
6. ONLY THEN: state the claim with the evidence inline.

Skip any step = lying, not verifying.
```

## Why fresh — auto-downgrade

If the protected artifact's bytes change after verification, the next read of `phase-state.json` automatically downgrades that phase from `complete` back to `running` and clears `verified_at` / `verifier_signature`. Enforced in `scriptorium/phase_state.py` — not skippable. A `phase show` from *before* an edit proves nothing about the artifact you have *now*. Re-run after every edit to the protected file.

## Common failures

Every row pairs the CC command with the Cowork MCP tool.

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| "Scope phase complete" | `scriptorium verify --gate scope` exit 0 + `phase show` (Cowork: MCP `phase_show`) shows `phases.scoping.status="complete"` with non-null `verifier_signature` | "scope.json looks complete"; a `set_phase` call you didn't reread |
| "Synthesis is clean" | `scriptorium verify --gate synthesis` exit 0 + matching row in `audit.jsonl` (Cowork: `audit` MCP resource) | "Cite-check passed locally"; a stale `verified_at` from before the last edit |
| "Ready to publish" | `scriptorium verify --gate publish` exit 0 + (Phase 5) reviewer JSON `verdict=pass` for both `cite` and `contradiction` | "Synthesis is clean" alone; reviewer `verdict=skipped` (does NOT unblock publish) |
| "Overview is correct" | `scriptorium verify --gate overview` exit 0 + regenerated overview hash equals `phase-state.json::phases.<phase>.verifier_signature` | The previous overview; optimism after a re-render |
| "Phase transition succeeded" | `scriptorium phase set <phase> <status>` returns + `scriptorium phase show` (Cowork: MCP `phase_show`) shows the new status with non-null verification fields | The CLI/MCP call returning — it may have raised and your prompt missed it |
| "Override applied" | `scriptorium phase override --reason "<reason>"` (Cowork: MCP `phase_override`) + next `phase show` shows `status="overridden"` with `override.reason` and `override.ts` populated | A planned override you intended to run but didn't |

## Red flags — STOP

If you catch yourself typing any of the following without having just run the verification command, STOP and run it.

- "should pass" / "should be complete" / "should work" — should ≠ does. Run `scriptorium verify --gate <gate>` (Cowork: MCP `verify`).
- "looks complete" / "looks clean" / "looks fine" — looks ≠ verified. Run `scriptorium phase show` (Cowork: MCP `phase_show`).
- "phase is done" without a `phase show` snapshot in this turn. Run it.
- "synthesis is clean" without `scriptorium verify --gate synthesis` exit-0 in this turn. Run it.
- "ready to publish" without `scriptorium verify --gate publish` AND (once Phase 5 lands) a reviewer pass for both `cite` and `contradiction` reviewers.
- Trusting a `set_phase("complete")` call without confirming `verified_at` and `verifier_signature` are non-null on the next `phase show`.
- Trusting an audit append happened without grepping `audit.jsonl` (CC) or reading the `audit` MCP resource (Cowork).
- Reusing a `verify` exit-0 from earlier in the conversation after editing the protected artifact — the auto-downgrade has already silently moved you back to `running`.
- Expressing satisfaction ("Great!", "Perfect!", "Done!") before the verification command has been run *this turn*.

## Rationalization prevention

| Excuse | Reality |
|--------|---------|
| "I ran verify two messages ago" | Auto-downgrade may have fired. Re-run. |
| "The artifact didn't change since then" | Prove it: rerun `scriptorium verify --gate <gate>`. The hash is cheap. |
| "Cowork doesn't have the CLI" | Cowork has the MCP. Call `verify`, `phase_show`, `phase_override`. The Iron Law is runtime-agnostic. |
| "The reviewer is a Phase 5 thing" | True for the *implementation*; the *gate* still demands reviewer pass for synthesis once Phase 5 lands. Don't ship "publish ready" today and pretend Phase 5 won't reread your claim. |
| "`set_phase` returned without raising" | Returning ≠ stored ≠ verified. Re-read `phase show` and confirm `verifier_signature` is non-null. |
| "I appended an audit row" | Did you grep `audit.jsonl` (CC) / read the `audit` MCP resource (Cowork) and see it? |
| "Override is fine, I have authority" | An override without `override.reason` populated is invisible to the audit trail. Use `scriptorium phase override --reason "..."` so the row is reconstructable. |

## Reviewer forward-reference (Phase 5)

For the synthesis phase specifically, "complete" once Phase 5 lands additionally requires both reviewer JSONs at `phases.synthesis.verifier_signature`:

- `cite` reviewer: `verdict=pass` (empty `findings[]` allowed)
- `contradiction` reviewer: `verdict=pass`

`verdict=fail` does NOT unblock publish. `verdict=skipped` does NOT unblock publish. The synthesis gate reads both verdicts; until both are `pass`, "synthesis is clean" is false.

## When to apply

Fire this skill **before**:

- Any sentence implying a phase finished, regardless of phrasing.
- Any `scriptorium phase set <phase> complete` call (CC) or MCP `phase_set` with `status=complete` (Cowork).
- Any `scriptorium phase override` call (CC) or MCP `phase_override` (Cowork).
- Any handoff between skills that reads phase-state as "done" upstream.
- Any commit, PR, or audit-export that references a phase as complete.
- Any "ready to publish" / "ready to ship the review" claim.

Rule applies to:

- Exact phrases listed in the red-flag block.
- Paraphrases and synonyms ("the scope checks out", "we're done with extraction").
- Implicit completion (moving on to the next phase without naming the previous one as verified).

## The bottom line

Run the command. Read the output. Reread `phase show`. Confirm the audit row. **Then** claim.

Non-negotiable.
