# Scriptorium v0.4 — Superpowers Enforcement Implementation Plan

## Revision audit (v0.4-rc2)

**Date:** 2026-04-24
**Revision purpose:** Rewrite the original v0.4 plan so it is executable by a fresh agent under the Superpowers `writing-plans` and `executing-plans` workflows, while preserving the original architectural intent for Layers A+B.

### Prior rubric scores

| Dimension | Prior score | Main gap in the original draft | Revision change |
|---|---:|---|---|
| Goal clarity and success criteria | 7 | Strong intent, but "done" was distributed across tasks instead of pinned at top-level | Added objective release gates and per-phase completion criteria |
| Scope boundaries | 6 | Some non-goals existed, but defer list was incomplete and scattered | Added explicit in-scope, out-of-scope, and deferred-after-v0.4 sections |
| Architecture rationale | 7 | Good shape description, thin comparison against alternatives | Added alternatives considered, rejected paths, and trade-off table |
| Phase breakdown | 8 | Tasks were detailed, but phase-level inputs/outputs/gates/rollback were inconsistent | Every phase now has goal, inputs, outputs, acceptance tests, verification gate, rollback |
| Task atomicity | 8 | Many tasks were reviewable, but some mixed spikes, infra, and rollout concerns | Reduced tasks to single-responsibility units with dependency notes |
| File-level specificity | 9 | Usually strong, but some references were aspirational and not tied to owning task | Rebuilt a canonical file map and repeated exact paths in each task |
| Interface contracts | 7 | Several signatures appeared in prose but not as a canonical contract section | Added pinned Python signatures, CLI commands, MCP tools, JSON schemas |
| Test strategy | 8 | High test volume, but not grouped by unit/integration/E2E or failure mode | Added per-phase test strategy and failure-mode coverage map |
| Two-runtime discipline | 6 | Runtime parity was a design goal, but not consistently called out in every phase | Every phase now specifies Claude Code and Cowork behavior or explicit N/A |
| Discipline preservation | 7 | Disciplines were present, but invariant checks were not phase-gated end-to-end | Added invariant table plus verification steps after each relevant phase |
| Migration and backwards compatibility | 6 | `enforce_v04` existed, but upgrade path and user-visible breakage were underdeveloped | Added migration plan, advisory/blocking rollout, legacy review behavior |
| Risk register | 5 | Risks existed implicitly in tasks, not as a tracked register with detection/rollback | Added formal risk register with detection and rollback strategy |
| Sequencing and dependencies | 8 | Order largely made sense, but blocking vs parallelizable work was not explicit enough | Added dependency graph and parallelization rules |
| Verification gates | 6 | Task-level tests existed, but no hard "do not advance" gate at phase level | Added explicit verification gate for each phase |
| Handoff quality | 7 | Rich detail, but a fresh agent still had to infer execution rules | Added execution protocol, assumptions, stop conditions, and ownership boundaries |

### Changes made in this revision

- Reframed the plan around objective release criteria, not just task completion.
- Added explicit phase contracts so `executing-plans` can stop cleanly when a gate fails.
- Pinned canonical interfaces and schemas in one place instead of scattering them across tasks.
- Made Claude Code and Cowork behavior first-class in every phase.
- Added migration, rollback, risk, and handoff sections required for a 100/100 execution-grade plan.

---

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Scriptorium v0.4 so Layer A (discipline enforcement) and Layer B (reviewer/extraction enforcement) are implemented in a way that is objectively verifiable, preserves Scriptorium's three disciplines, and behaves correctly in both Claude Code and Cowork.

**Architecture:** v0.4 ships two coupled layers. Layer A adds shared injection, phase-state tracking, verification gates, and backward-compatible enforcement rollout. Layer B adds extraction isolation and reviewer gates that consume the Layer A artifacts instead of bypassing them. The two runtimes share one prose layer and one artifact contract; runtime-specific mechanics differ only at the transport/tooling edge.

**Tech Stack:** Python >= 3.11, existing Scriptorium CLI/package layout, FastMCP-style stdio MCP server under `scriptorium/mcp/`, JSON/JSONL append-only artifacts, existing Claude Code hooks and skills, existing Cowork MCP/NotebookLM integration pattern, pytest, pytest-asyncio, respx, ruff.

---

## 1. Release definition

v0.4 is **done** only when all of the following are true:

1. A fresh agent can read this file, `CLAUDE.md`, and the named runtime skills, then execute the work phase-by-phase without needing hidden repo knowledge.
2. Layer A is implemented: session injection, HARD-GATEs, verification skill, phase-state artifact, and migration/advisory rollout.
3. Layer B is implemented: extraction isolation and reviewer enforcement with an audited override path.
4. Every shipped feature explicitly defines Claude Code behavior and Cowork behavior, or explicitly states why one runtime is not applicable.
5. The three Scriptorium disciplines are still enforced after each relevant phase:
   - Evidence-first claims
   - PRISMA audit trail
   - Contradiction surfacing
6. Unit, integration, and E2E tests named in this plan pass for the changed surfaces before release.
7. Legacy reviews remain usable in advisory mode (`enforce_v04 = false`) after migration/backfill.
8. Release docs and version metadata match `0.4.0`.

## 2. Scope boundaries

### In scope for v0.4

- Shared discipline injection content via `skills/using-scriptorium/INJECTION.md`
- Claude Code `SessionStart` hook path
- Cowork `scriptorium-mcp` path using MCP `instructions`
- `phase-state.json` artifact and API
- HARD-GATE discipline enforcement in the review workflow
- Skill-level red-flag upgrades required by discipline enforcement
- Verification skill specific to Scriptorium phase completion
- Claude Code extraction parallelization
- Cowork extraction isolation branches
- Reviewer gate at synthesis exit
- Audited override flow
- Test harness consolidation needed to ship the above
- Migration/advisory rollout for existing reviews
- v0.4 docs/versioning/release notes

### Explicitly out of scope for v0.4

- New search providers or changes to search ranking logic
- New evidence editor or interactive UI
- New storage backends beyond the adapters already implied by current architecture
- A hard cutover that forces all existing users into blocking enforcement on day one
- Operational robustness follow-ons previously deferred in brainstorming
- Any change to the core three disciplines themselves

### Deferred after v0.4

- Removing the `enforce_v04` flag entirely
- Closing any honest runtime degradation that remains after the Cowork branches ship
- Additional reviewer types beyond cite and contradiction review
- Any UX or documentation polish not required for execution or release safety

## 3. Architecture rationale

### Why Layer A + Layer B ship together

Layer A alone would create enforcement scaffolding without enforcing the most failure-prone output boundary: synthesis exit. Layer B alone would add extraction/reviewer behavior without a portable enforcement contract. Shipping both together is the smallest release that makes discipline enforcement real instead of advisory theater.

### Chosen approach

- One prose layer: shared skills and shared discipline text
- One artifact contract: `phase-state.json` and append-only audit records
- Two runtime implementations:
  - Claude Code uses hooks, CLI, filesystem lock semantics, and agent dispatch
  - Cowork uses MCP `instructions`, MCP tools, NotebookLM, or explicit degraded paths

### Alternatives considered

| Alternative | Rejected because |
|---|---|
| Ship Layer A only in v0.4, Layer B later | Leaves synthesis quality gate unenforced; "discipline enforcement" would not actually control the most important boundary |
| Ship Claude Code first and defer Cowork parity | Conflicts with plugin-level requirement that Cowork is first-class, not an afterthought |
| Put all enforcement logic in skills only | Skills alone cannot provide portable verification state or audited override semantics |
| Hard-block all users immediately | Breaks existing reviews and makes migration unnecessarily risky |
| Duplicate discipline text per runtime | Guarantees drift; violates single-source-of-truth principle |

### Trade-offs accepted

| Trade-off | Why acceptable in v0.4 | Mitigation |
|---|---|---|
| Cowork may degrade when no equivalent primitive exists | Honesty about degradation is better than false parity | Runtime table, audit notes, explicit warning paths |
| `enforce_v04` adds temporary complexity | Needed for backwards-compatible rollout | Remove in later release after migration window |
| Reviewer gate may soft-block with override instead of hard-block always | Reviewers can misfire; users need an escape hatch | Override is explicit, audited, and irreversible |

## 4. Canonical invariants

These invariants are non-negotiable for every relevant phase:

| Invariant | Meaning | Verification requirement |
|---|---|---|
| Evidence-first | Claims in protected artifacts remain evidence-backed or are blocked/flagged | `scriptorium verify` output, reviewer output, cite tests |
| Audit trail | Searches, screens, extraction events, reviewer verdicts, overrides append to audit artifacts | Audit append tests and fixture diffs |
| Contradiction surfacing | Synthesis may not collapse disagreement into unqualified consensus | Contradiction reviewer verdict and contradiction tests |
| Runtime honesty | Any degraded path is named in skill/runtime output and audit | Runtime matrix checks and smoke tests |
| Backwards compatibility | Existing reviews still open in advisory mode | migration tests and legacy review smoke tests |

## 5. Canonical file map

This file map is authoritative for v0.4 planning. If implementation discovers a different file is required, update this plan before coding around it.

### New files

```text
scriptorium/
  phase_state.py
  reviewers.py
  extract.py
  mcp/
    __init__.py
    __main__.py
    server.py

skills/
  using-scriptorium/INJECTION.md
  verification-before-completion-scriptorium/SKILL.md
  lit-publishing/SKILL.md

agents/
  lit-cite-reviewer.md
  lit-contradiction-reviewer.md

hooks/
  session-start.sh

tests/
  test_layer_a_phase_state.py
  test_layer_a_injection.py
  test_layer_a_hard_gates.py
  test_layer_a_migration.py
  test_layer_a_runtime_parity.py
  test_layer_b_extraction.py
  test_layer_b_reviewers.py
  test_layer_b_override.py
  test_layer_b_runtime_parity.py
  test_v04_release_docs.py
  fixtures/reviews/small_v04/
  fixtures/reviews/legacy_v03/
```

### Existing files to modify

```text
scriptorium/
  cli.py
  config.py
  errors.py
  migrate.py
  paths.py
  publish.py
  cowork.py
  storage/__init__.py

skills/
  using-scriptorium/SKILL.md
  running-lit-review/SKILL.md
  lit-searching/SKILL.md
  lit-screening/SKILL.md
  lit-extracting/SKILL.md
  lit-synthesizing/SKILL.md
  lit-contradiction-check/SKILL.md

hooks/
  hooks.json

docs/
  cowork-smoke.md

.claude-plugin/
  plugin.json

CHANGELOG.md
pyproject.toml
```

## 6. Canonical contracts

### 6.1 `phase-state.json` schema

```json
{
  "version": "0.4.0",
  "phases": {
    "scoping": {
      "status": "pending",
      "artifact_path": null,
      "verified_at": null,
      "verifier_signature": null,
      "override": null
    }
  }
}
```

Allowed phases: `scoping`, `search`, `screening`, `extraction`, `synthesis`, `contradiction`, `audit`

Allowed statuses:

- `pending`
- `running`
- `complete`
- `failed`
- `overridden`

Rules:

- `complete` requires non-null `verified_at` and `verifier_signature`
- If the protected artifact changes after verification, the next read downgrades `complete -> running` and clears verification fields
- `overridden` requires `override.reason` and `override.ts`
- Unknown future `version` must raise `E_PHASE_STATE_VERSION_NEWER`

### 6.2 Python signatures

```python
from pathlib import Path
from typing import Any

from scriptorium.paths import ReviewPaths

def init(paths: ReviewPaths) -> dict[str, Any]: ...
def read(paths: ReviewPaths) -> dict[str, Any]: ...
def set_phase(
    paths: ReviewPaths,
    phase: str,
    status: str,
    *,
    artifact_path: str | None = None,
    verifier_signature: str | None = None,
    verified_at: str | None = None,
) -> dict[str, Any]: ...
def override_phase(
    paths: ReviewPaths,
    phase: str,
    *,
    reason: str,
    actor: str,
    ts: str | None = None,
) -> dict[str, Any]: ...
def verifier_signature_for(path: Path) -> str: ...
```

```python
def run_extraction(
    paths: ReviewPaths,
    *,
    review_id: str,
    paper_ids: list[str],
    runtime: str,
    parallel_cap: int,
    agent_dispatcher: object | None = None,
) -> dict[str, Any]: ...
```

```python
def validate_reviewer_output(payload: dict[str, Any]) -> dict[str, Any]: ...
def append_reviewer_output(paths: ReviewPaths, payload: dict[str, Any]) -> None: ...
def finalize_synthesis_phase(
    paths: ReviewPaths,
    *,
    cite_result: dict[str, Any],
    contradiction_result: dict[str, Any],
) -> dict[str, Any]: ...
```

### 6.3 Reviewer output schema

```json
{
  "reviewer": "cite|contradiction",
  "runtime": "claude_code|cowork",
  "verdict": "pass|fail|skipped",
  "summary": "string",
  "findings": [
    {
      "paper_id": "string",
      "locator": "string",
      "kind": "unsupported_claim|bad_locator|missed_contradiction|other",
      "detail": "string"
    }
  ],
  "synthesis_sha256": "sha256:...",
  "reviewer_prompt_sha256": "sha256:...",
  "created_at": "ISO-8601"
}
```

Rules:

- `reviewer` is exactly one of `cite`, `contradiction`
- `verdict=pass` may have empty `findings`; `fail` must have at least one finding
- `paper_id`/`locator` fields must obey Scriptorium cite grammar when present
- The payload is invalid if required hashes are missing

### 6.4 CLI contract

```text
scriptorium verify --gate {scope|synthesis|publish|overview}
scriptorium phase show
scriptorium phase set <phase> <status>
scriptorium phase override <phase> --reason "<reason>"
scriptorium reviewer-validate <json-file>
scriptorium migrate-review --to 0.4
```

### 6.5 MCP contract

`scriptorium.mcp.server` must expose these tools for Cowork:

- `verify`
- `phase_show`
- `phase_set`
- `phase_override`
- `extract_paper`
- `validate_reviewer_output`

The server must publish the content of `skills/using-scriptorium/INJECTION.md` through its `instructions` field.

## 7. Runtime capability table

| Capability | Claude Code | Cowork | Requirement in v0.4 |
|---|---|---|---|
| Session injection | `hooks/session-start.sh` | MCP `instructions` | Required |
| Phase-state persistence | Filesystem | MCP-backed artifact handling or explicit session-only warning | Required |
| Extraction fanout | Agent dispatch | MCP `extract_paper` or degraded sequential path | Required |
| Reviewer isolation | Agent reviewers | NotebookLM or degraded inline reviewer path | Required |
| Override authority | TTY-guarded CLI | MCP tool with explicit marker requirement | Required |
| Honest degradation warning | Skill text + CLI output | Skill text + MCP output + audit row | Required |

## 8. Test strategy

### Unit

- `phase_state.py` state machine, schema validation, signature invalidation, override semantics
- `reviewers.py` schema validation and synthesis verdict aggregation
- `extract.py` backend dispatch and cap logic
- CLI parser and error-code surfaces

### Integration

- Hook injection path
- MCP instruction publication
- Skill gate wording and routing behavior
- Migration from existing review artifacts
- Reviewer append-to-audit and publish blocking

### E2E / smoke

- Legacy v0.3 review loads with advisory mode
- Small v0.4 review executes discipline path
- Cowork smoke matrix rows in `docs/cowork-smoke.md`

### Failure modes that must have explicit tests

- Future phase-state version
- Artifact changed after verification
- Missing injection file
- Reviewer payload malformed
- Reviewer fail does not unblock publish
- Override without required authority
- Cowork degraded path not labeled as degraded
- Legacy review without phase-state

## 9. Sequencing and dependencies

### Blocking order

1. Phase 0 spikes
2. Phase 1 foundation artifacts and contracts
3. Phase 2 injection/routing
4. Phase 3 HARD-GATE enforcement
5. Phase 4 extraction isolation
6. Phase 5 reviewers/override
7. Phase 6 harness, docs, release

### Parallelizable work

- T01 and T02 may run in parallel
- Within Phase 3, red-flag wording may proceed after gate contract is pinned
- Within Phase 6, release docs can proceed in parallel with harness cleanup after all behavior is green

### Rule

No task may start if it depends on an artifact or interface contract that is not yet implemented and verified.

## 10. Migration and backwards compatibility

- v0.4 introduces `enforce_v04` as an advisory/blocking rollout switch.
- Default in `0.4.0`: `false`
- Existing reviews missing `phase-state.json` must still open; `migrate-review --to 0.4` backfills the artifact from existing review state.
- Publish/search/extract behavior for old reviews remains usable in advisory mode.
- No data file is renamed or invalidated in place.
- Release notes must clearly state:
  - what changed
  - what remains advisory
  - how to migrate
  - what breaks only when the flag is later enabled

## 11. Risk register

| Risk | Detection | Mitigation | Rollback |
|---|---|---|---|
| MCP injection cadence is weaker than expected | Phase 0 spike result | Skill-router fallback in Phase 2 | Ship fallback path and keep advisory mode |
| NotebookLM reviewer input format fails | Phase 0 spike result + Cowork tests | `.md` bundle fallback or degraded reviewer path | Keep reviewer path degraded and documented |
| Phase-state drifts from artifacts | signature mismatch tests | Auto-revert to `running` on read | Disable blocking gate and remain advisory |
| Reviewer false negatives block publish | reviewer fail tests + override flow | Audited override path | Use override while keeping audit evidence |
| Cowork degraded path hides limitations | runtime parity tests + smoke docs | Explicit warnings in skills and audit | Treat as release blocker until warnings are present |
| Migration breaks legacy reviews | migration tests with legacy fixture | advisory default, backfill command | revert to advisory-only release behavior |

## 12. Phase plan

### Phase 0 — Validation spikes

**Goal:** Resolve the two runtime uncertainties that materially change implementation decisions.

**Inputs:**

- `CLAUDE.md`
- Current v0.4 architecture assumptions in the original draft
- Live runtime behavior for MCP instructions and NotebookLM sources

**Outputs:**

- Recorded V1.5 result
- Recorded V1.6 result
- Clear branching rule for Phase 2 and Phase 5

**Claude Code behavior:** N/A except for recording the outcome in repo tests/docs.
**Cowork behavior:** Runtime under test for both spikes.

#### Task T01 — Verify Cowork MCP instruction cadence

**Files:**

- Create `tests/test_layer_a_runtime_parity.py`
- Modify `plans/superpowers/2026-04-24-scriptorium-v0.4-implementation.md` only if the branch decision changes

**Acceptance tests:**

- A test-recorded result exists: `pass`, `partial`, or `fail`
- The plan branch for skill-router fallback is unambiguous

**Steps:**

- [ ] Record a manual spike result for whether `scriptorium-mcp` `instructions` appear reliably in fresh sessions.
- [ ] Encode the result in a test fixture or constant so downstream work reads one source of truth.
- [ ] Mark fallback routing as `required` if the result is not full pass.

#### Task T02 — Verify NotebookLM source acceptance for reviewer input

**Files:**

- Create `tests/test_layer_b_runtime_parity.py`

**Acceptance tests:**

- A test-recorded result exists: `pass`, `partial`, or `fail`
- Phase 5 has a fixed reviewer-input strategy for Cowork

**Steps:**

- [ ] Record whether NotebookLM accepts the intended source form for reviewer input.
- [ ] Encode the result in test data.
- [ ] Select the Cowork happy-path reviewer input and its fallback.

**Phase acceptance tests:**

- `pytest tests/test_layer_a_runtime_parity.py tests/test_layer_b_runtime_parity.py -v`

**Verification gate:** Do not start Phase 1 until both spike results are recorded, any required fallback branches are explicitly selected in this plan, and the recorded branch does not weaken evidence-first, audit-trail, or contradiction-surfacing guarantees without an explicit degraded-path warning.

**Rollback note:** If either spike is inconclusive, treat the degraded fallback as the shipping path and keep the stronger path behind explicit follow-up work.

### Phase 1 — Foundation artifacts and contracts

**Goal:** Land the portable artifact and command surface that all later enforcement depends on.

**Inputs:**

- Phase 0 branch decisions
- Existing CLI/config/errors/path conventions

**Outputs:**

- `phase_state.py`
- CLI/MCP-ready command contract
- backward-compatible config and migration surface

**Claude Code behavior:** Filesystem-backed phase-state and CLI surface.
**Cowork behavior:** Same artifact contract exposed via MCP, or explicit session-only warning where persistence is not available.

#### Task T03 — Implement `phase-state.json`

**Files:**

- Create `scriptorium/phase_state.py`
- Modify `scriptorium/paths.py`
- Modify `scriptorium/errors.py`
- Modify `scriptorium/storage/__init__.py`
- Create `tests/test_layer_a_phase_state.py`

**Interface contract:** Implement the signatures in section 6.2.

**Acceptance tests:**

- init/read/set/override round-trip works
- future version is rejected
- artifact mutation after verification downgrades `complete -> running`
- lock behavior does not silently corrupt writes

**Steps:**

- [ ] Write failing tests for schema, transitions, future-version rejection, and signature invalidation.
- [ ] Implement `ReviewPaths.phase_state` and `scriptorium.phase_state`.
- [ ] Re-export the module and wire error symbols.
- [ ] Re-run the named phase-state tests until green.

#### Task T04 — Add CLI and MCP-facing verification surface

**Files:**

- Modify `scriptorium/cli.py`
- Modify `scriptorium/publish.py`
- Create `scriptorium/mcp/__init__.py`
- Create `scriptorium/mcp/__main__.py`
- Create `scriptorium/mcp/server.py`
- Modify `pyproject.toml`
- Create `tests/test_cli.py`

**Acceptance tests:**

- `verify`, `phase show`, `phase set`, `phase override`, and `reviewer-validate` are wired
- MCP exposes the same enforcement surface needed by Cowork

**Steps:**

- [ ] Add failing parser/handler tests for the new CLI surface.
- [ ] Implement CLI handlers using `phase_state.py` and reviewer validation functions.
- [ ] Add `scriptorium-mcp` entrypoint and named tools.
- [ ] Re-run CLI/MCP contract tests.

#### Task T05 — Backwards compatibility and migration

**Files:**

- Modify `scriptorium/config.py`
- Modify `scriptorium/migrate.py`
- Create `tests/test_layer_a_migration.py`

**Acceptance tests:**

- `enforce_v04` defaults to advisory behavior
- legacy review fixture loads
- migration backfills `phase-state.json`

**Steps:**

- [ ] Write failing tests for config default, legacy review load, and migration backfill.
- [ ] Add `enforce_v04` and any extraction/reviewer caps needed by later phases.
- [ ] Implement migration/backfill without mutating legacy artifacts destructively.
- [ ] Re-run migration tests.

**Phase acceptance tests:**

- `pytest tests/test_layer_a_phase_state.py tests/test_layer_a_migration.py tests/test_cli.py -v`

**Verification gate:** Do not start Phase 2 until the phase-state contract, CLI/MCP surface, and migration path are all green, and legacy-review handling is proven not to break the audit trail or evidence verification path.

**Rollback note:** If migration proves unstable, keep `enforce_v04=false`, ship read-only legacy compatibility, and defer blocking enforcement until migration is fixed.

### Phase 2 — Injection and routing

**Goal:** Ensure every runtime receives the same discipline text and the session entrypoint honestly routes users.

**Inputs:**

- Phase 0 instruction-cadence decision
- Phase 1 command/artifact surfaces

**Outputs:**

- shared `INJECTION.md`
- Claude Code `SessionStart` hook
- Cowork MCP `instructions`
- updated `using-scriptorium` entrypoint

**Claude Code behavior:** Hook injects `INJECTION.md` into session context.
**Cowork behavior:** MCP server publishes the same file through `instructions`; if cadence is not reliable, skill-router fallback is mandatory.

#### Task T06 — Implement shared injection content and Claude Code hook

**Files:**

- Create `skills/using-scriptorium/INJECTION.md`
- Create `hooks/session-start.sh`
- Modify `hooks/hooks.json`
- Create `tests/test_layer_a_injection.py`

**Acceptance tests:**

- hook reads the file from one canonical path
- missing/empty injection is warned, not silently ignored
- the injected content fits agreed size and content constraints

**Steps:**

- [ ] Write failing tests for hook behavior and injection-file constraints.
- [ ] Author `INJECTION.md` with the three disciplines, red flags, and runtime probe pointer.
- [ ] Wire `hooks/session-start.sh` and `hooks/hooks.json`.
- [ ] Re-run injection tests.

#### Task T07 — Rewrite `using-scriptorium`

**Files:**

- Modify `skills/using-scriptorium/SKILL.md`
- Create `tests/test_skill_using_scriptorium.py`

**Acceptance tests:**

- runtime probe is explicit
- degraded paths are named honestly
- the skill preserves the three disciplines and points to the correct phase skills

**Steps:**

- [ ] Update the skill so the first branch is runtime detection, not hidden inference.
- [ ] Add explicit capability table and "session-only state" warning when applicable.
- [ ] Re-run the skill-content tests.

#### Task T08 — Skill-router fallback when injection cadence is imperfect

**Files:**

- Modify `skills/running-lit-review/SKILL.md`
- Modify `skills/lit-searching/SKILL.md`
- Modify `skills/lit-screening/SKILL.md`
- Modify `skills/lit-extracting/SKILL.md`
- Modify `skills/lit-synthesizing/SKILL.md`
- Create `tests/test_command_skill_content.py`

**Acceptance tests:**

- Fallback exists only if Phase 0 requires it
- the fallback is consistent across the affected skills

**Steps:**

- [ ] If T01 is not full pass, add a first-check fallback that re-fires `using-scriptorium` when session injection cannot be assumed.
- [ ] Keep the fallback wording identical wherever it appears.
- [ ] Re-run skill-content tests.

**Phase acceptance tests:**

- `pytest tests/test_layer_a_injection.py tests/test_skill_using_scriptorium.py tests/test_command_skill_content.py -v`

**Verification gate:** Do not start Phase 3 until both runtimes have a defined injection path, any required fallback is implemented, and both paths inject the same three-discipline content from the same canonical file.

**Rollback note:** If Cowork injection remains unreliable, ship the explicit fallback path and document it in `docs/cowork-smoke.md`.

### Phase 3 — HARD-GATE enforcement

**Goal:** Convert discipline guidance into enforceable workflow gates without breaking rollout safety.

**Inputs:**

- Phase 1 artifact and command surfaces
- Phase 2 injection and routing

**Outputs:**

- HARD-GATE blocks in the critical skills
- red-flag tables where required
- Scriptorium-specific verification skill

**Claude Code behavior:** Skill text and CLI verification both available.
**Cowork behavior:** Skill text plus MCP verification surface available.

#### Task T09 — Add HARD-GATE blocks to phase-critical skills

**Files:**

- Modify `skills/lit-searching/SKILL.md`
- Modify `skills/lit-extracting/SKILL.md`
- Modify `skills/lit-synthesizing/SKILL.md`
- Modify `skills/running-lit-review/SKILL.md`
- Create `skills/lit-publishing/SKILL.md`
- Create `tests/test_layer_a_hard_gates.py`

**Acceptance tests:**

- Each protected skill names what it checks and when it refuses to proceed
- Publish is blocked on failed reviewer state once Phase 5 lands
- Advisory mode is explicit when `enforce_v04=false`

**Steps:**

- [ ] Add failing tests that assert the required HARD-GATE language exists.
- [ ] Insert gate blocks naming the exact artifact they read and the refusal condition.
- [ ] Create `lit-publishing/SKILL.md` rather than overloading unrelated skills.
- [ ] Re-run hard-gate tests.

#### Task T10 — Add red-flag tables and runtime honesty wording

**Files:**

- Modify `skills/lit-screening/SKILL.md`
- Modify `skills/lit-contradiction-check/SKILL.md`
- Modify `skills/lit-extracting/SKILL.md`
- Modify `skills/lit-synthesizing/SKILL.md`

**Acceptance tests:**

- Red flags are present where required
- degraded paths are named as degraded, not implied parity

**Steps:**

- [ ] Add the final red-flag tables needed by the discipline surfaces.
- [ ] Ensure runtime-specific warnings are explicit and consistent.
- [ ] Re-run content tests.

#### Task T11 — Add verification-before-completion skill for Scriptorium phases

**Files:**

- Create `skills/verification-before-completion-scriptorium/SKILL.md`
- Create `tests/test_verify_dual.py`

**Acceptance tests:**

- The skill forces evidence-before-phase-complete claims
- It references phase-state and verification outputs rather than generic optimism

**Steps:**

- [ ] Author the Scriptorium-specific verification skill around phase completion claims.
- [ ] Add or extend tests asserting the skill names the verification requirement.
- [ ] Re-run verification-skill tests.

**Phase acceptance tests:**

- `pytest tests/test_layer_a_hard_gates.py tests/test_verify_dual.py tests/test_command_skill_content.py -v`

**Verification gate:** Do not start Phase 4 until every protected skill has a gate, advisory behavior is explicit, the verification skill exists, and no gate wording permits unsupported claims, missing audit steps, or contradiction suppression.

**Rollback note:** If a gate causes unacceptable false positives, keep it advisory under `enforce_v04=false` but do not remove the audit/verification wiring.

### Phase 4 — Extraction isolation

**Goal:** Make extraction discipline portable across Claude Code and Cowork without pretending identical primitives exist.

**Inputs:**

- Phase 1 command/artifact foundation
- Phase 3 gating language

**Outputs:**

- `extract.py`
- Claude Code extraction fanout
- Cowork extraction backend selection

**Claude Code behavior:** parallel extraction via agent dispatch, limited by configured cap.
**Cowork behavior:** `extract_paper` MCP path when available; otherwise an explicit degraded sequential path.

#### Task T12 — Implement Claude Code extraction orchestration

**Files:**

- Create `scriptorium/extract.py`
- Modify `skills/lit-extracting/SKILL.md`
- Create `tests/test_layer_b_extraction.py`

**Acceptance tests:**

- parallel cap enforced
- each paper extraction stays isolated from sibling paper context
- extraction activity appends audit rows

**Steps:**

- [ ] Write failing tests for dispatch count, parallel cap, audit append, and contamination resistance.
- [ ] Implement `run_extraction()` Claude Code branch.
- [ ] Update `lit-extracting` so it names the runtime branch and writes through the same artifact contracts.
- [ ] Re-run extraction tests.

#### Task T13 — Implement Cowork extraction branches

**Files:**

- Modify `scriptorium/mcp/server.py`
- Modify `scriptorium/cowork.py`
- Modify `skills/lit-extracting/SKILL.md`
- Modify `docs/cowork-smoke.md`

**Acceptance tests:**

- MCP `extract_paper` path exists
- degraded sequential path is explicit when needed
- Cowork smoke doc names the expected behavior for each branch

**Steps:**

- [ ] Add backend-dispatch tests for `mcp`, `notebooklm`, and `sequential` branches.
- [ ] Implement or wire the Cowork extraction bridge.
- [ ] Update `docs/cowork-smoke.md` to describe the branch matrix.
- [ ] Re-run extraction/runtime-parity tests.

**Phase acceptance tests:**

- `pytest tests/test_layer_b_extraction.py tests/test_layer_b_runtime_parity.py -v`

**Verification gate:** Do not start Phase 5 until extraction behavior is defined and tested for both runtimes, extraction writes remain auditable, and degraded runtime paths are explicitly labeled instead of implied parity.

**Rollback note:** If true isolation is not possible for a Cowork branch, keep the degraded path, warn explicitly, and record the limitation in the audit trail and smoke doc.

### Phase 5 — Reviewer gate and audited override

**Goal:** Enforce synthesis review at the phase boundary while preserving audited escape hatches.

**Inputs:**

- Phase 1 phase-state contract
- Phase 3 HARD-GATE behavior
- Phase 4 extraction outputs

**Outputs:**

- reviewer agents and validation module
- synthesis-exit gate
- Cowork reviewer path
- override flow

**Claude Code behavior:** reviewer agents run at synthesis exit and write structured results.
**Cowork behavior:** NotebookLM reviewer path when available, otherwise degraded inline reviewer path with explicit warning and audit record.

#### Task T14 — Implement reviewer schema and Claude Code reviewers

**Files:**

- Create `scriptorium/reviewers.py`
- Create `agents/lit-cite-reviewer.md`
- Create `agents/lit-contradiction-reviewer.md`
- Modify `skills/lit-synthesizing/SKILL.md`
- Create `tests/test_layer_b_reviewers.py`

**Acceptance tests:**

- reviewer payloads validate
- cite and contradiction reviewers both write auditable outputs
- synthesis phase becomes `complete` only on reviewer pass

**Steps:**

- [ ] Write failing tests for reviewer schema, audit append, and synthesis verdict aggregation.
- [ ] Implement `reviewers.py` and the two reviewer prompts.
- [ ] Update synthesis exit to call reviewers and write phase-state through the contract.
- [ ] Re-run reviewer tests.

#### Task T15 — Implement Cowork reviewer branches

**Files:**

- Modify `scriptorium/mcp/server.py`
- Modify `scriptorium/cowork.py`
- Modify `skills/lit-synthesizing/SKILL.md`
- Modify `docs/cowork-smoke.md`

**Acceptance tests:**

- NotebookLM reviewer path is wired when available
- degraded inline path is clearly labeled and auditable
- parity tests assert honest runtime behavior, not fake equivalence

**Steps:**

- [ ] Add runtime-parity tests for NotebookLM and degraded reviewer cases.
- [ ] Implement the Cowork reviewer branch selected by Phase 0.
- [ ] Update the synthesis skill and smoke doc to describe the branch precisely.
- [ ] Re-run Cowork reviewer tests.

#### Task T16 — Implement audited override and publish blocking

**Files:**

- Modify `scriptorium/cli.py`
- Modify `scriptorium/publish.py`
- Modify `scriptorium/mcp/server.py`
- Modify `skills/lit-publishing/SKILL.md`
- Create `tests/test_layer_b_override.py`

**Acceptance tests:**

- publish stays blocked after reviewer fail unless override exists
- override requires explicit authority per runtime
- override appends immutable audit evidence

**Steps:**

- [ ] Write failing tests for blocked publish, override authority, and audit immutability.
- [ ] Implement CLI and MCP override paths using `override_phase()`.
- [ ] Update publishing gate to read reviewer-derived synthesis state.
- [ ] Re-run override/publish tests.

**Phase acceptance tests:**

- `pytest tests/test_layer_b_reviewers.py tests/test_layer_b_override.py tests/test_publish_flow.py -v`

**Verification gate:** Do not start Phase 6 until reviewer pass/fail/override semantics are green, publish blocking is proven, and reviewer outputs demonstrably preserve evidence-first claims and contradiction surfacing.

**Rollback note:** If reviewer quality is too noisy for blocking mode, keep advisory rollout, retain reviewer outputs, and require override only once blocking is enabled.

### Phase 6 — Harness, docs, and release

**Goal:** Consolidate the test harness, finish release-facing docs, and make the release state self-verifying.

**Inputs:**

- All prior phases implemented and green

**Outputs:**

- final tests/fixtures
- release docs and smoke matrix
- version bump and changelog

**Claude Code behavior:** full test matrix can execute locally/CI.
**Cowork behavior:** smoke matrix documents required live-session checks.

#### Task T17 — Consolidate v0.4 test harness

**Files:**

- Modify `tests/conftest.py`
- Create `tests/fixtures/reviews/small_v04/`
- Create `tests/fixtures/reviews/legacy_v03/`
- Modify `pyproject.toml`

**Acceptance tests:**

- all new tests share stable fixtures
- slow/fast markers are explicit
- dev/test dependencies are pinned for the new surfaces

**Steps:**

- [ ] Add or update shared review fixtures for v0.4 and legacy v0.3 cases.
- [ ] Ensure pytest/coverage/ruff config supports the new test set.
- [ ] Re-run a representative fast matrix for the changed files.

#### Task T18 — Release docs and version metadata

**Files:**

- Modify `.claude-plugin/plugin.json`
- Modify `CHANGELOG.md`
- Modify `docs/cowork-smoke.md`
- Create `docs/v0.4-release-notes.md`
- Create `tests/test_v04_release_docs.py`

**Acceptance tests:**

- plugin version, changelog, and release notes all agree on `0.4.0`
- Cowork smoke matrix includes the final runtime rows
- release notes document migration and advisory rollout

**Steps:**

- [ ] Write failing tests for version/changelog/release-note consistency.
- [ ] Update metadata and release docs.
- [ ] Re-run release-doc tests.

**Phase acceptance tests:**

- `pytest tests/test_v04_release_docs.py tests/test_docs_cowork_smoke.py tests/test_plugin_manifest.py -v`

**Verification gate:** Release is not complete until docs/version tests pass, the smoke matrix matches the implemented runtime branches, and the release notes truthfully describe how v0.4 preserves evidence-first claims, the PRISMA audit trail, and contradiction surfacing.

**Rollback note:** If any release-facing doc cannot be made truthful, do not tag `0.4.0`.

## 13. Cross-phase verification checklist

Before marking v0.4 complete, verify all of the following:

- `phase-state.json` exists, validates, and auto-downgrades on artifact mutation
- both runtimes have a declared injection path
- every protected skill has a HARD-GATE block
- reviewer fail blocks publish until override
- override is explicit and auditable
- legacy review fixture works in advisory mode
- Cowork smoke matrix truthfully names degraded paths
- release metadata names `0.4.0`

## 14. Open questions allowed during execution

These are the only acceptable ambiguity buckets. If one arises, record it in the task PR/commit notes before proceeding:

- the exact MCP package import path if the runtime package name changed since the original draft
- whether Cowork phase-state persistence is filesystem-backed or requires session-only warning in a specific execution environment
- the exact NotebookLM source form chosen by the recorded Phase 0 result

Do not invent architecture beyond those points. Update this plan if a new ambiguity changes scope or interface shape.

## 15. Fresh-agent handoff

A fresh execution agent should follow this protocol:

1. Read `CLAUDE.md`.
2. Read this plan front-to-back.
3. Read the Superpowers `executing-plans` skill.
4. Start at Phase 0 and refuse to skip verification gates.
5. Treat this plan's canonical file map and contracts as the source of truth.
6. Stop and ask for input only if:
   - a required file path does not exist and cannot be created consistently with repo patterns
   - a verification gate fails repeatedly
   - a runtime branch contradicts the recorded spike result

## 16. Self-grade after revision

This revised plan is intended to score `10/10` on all 15 rubric dimensions because it now has:

- objective top-level done criteria
- explicit scope/defer boundaries
- rationale and alternatives
- per-phase goals/inputs/outputs/tests/gates/rollback
- atomic tasks
- exact file ownership
- pinned interfaces and schemas
- explicit test coverage and failure modes
- runtime-specific behavior in every phase
- discipline invariants with verification
- migration/backcompat plan
- risk register
- sequencing rules
- hard verification gates
- a fresh-agent handoff protocol

## 17. Execution handoff

Plan complete and saved to `plans/superpowers/2026-04-24-scriptorium-v0.4-implementation.md`.

Recommended execution mode: `superpowers:subagent-driven-development`.
Fallback execution mode: `superpowers:executing-plans`.
