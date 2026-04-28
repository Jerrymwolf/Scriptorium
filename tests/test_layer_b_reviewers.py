"""Layer B / T14: reviewer schema and Claude Code reviewer artifacts.

Pins (plan §6.2 + §6.3 + §12 phase 5):

  A. Schema validation propagation — bad payloads raise
     ``E_REVIEWER_INVALID`` BEFORE writing to audit.jsonl or mutating
     phase-state.
  B. Audit append shape — ``append_reviewer_output`` writes ONE row per
     call with ``action="reviewer.<reviewer>"``, status mapped from
     verdict, and the full validated payload preserved in ``details``.
  C. Synthesis verdict aggregation — ``finalize_synthesis_phase``
     returns ``synthesis_status="complete"`` only when both reviewers
     verdict ``pass`` AND ``synthesis.md`` exists; otherwise
     ``running`` (recoverable). The aggregation row
     ``action="synthesis.gate"`` is written exactly once per call.
  D. Idempotency / sequencing — repeated finalize calls converge on the
     same phase-state signature when inputs do not change; auto-downgrade
     fires when ``synthesis.md`` mutates after a complete.
  E. Agent prompts — ``agents/lit-cite-reviewer.md`` and
     ``agents/lit-contradiction-reviewer.md`` exist with valid YAML
     frontmatter, name matches basename, body names verdict + finding-kind
     literals from §6.3.
  F. Skill update — ``skills/lit-synthesizing/SKILL.md`` gains a
     synthesis-exit gate section that names both agents,
     ``finalize_synthesis_phase``, the aggregation rule, and the three
     audit actions; ALL pre-existing sections preserved byte-identical.
  G. Cross-runtime contract — agent ``name:`` fields match the names the
     SKILL.md references.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

from scriptorium.errors import EXIT_CODES, ScriptoriumError
from scriptorium.paths import ReviewPaths
from scriptorium.phase_state import (
    SHA256_SIG_RE,
    init as phase_state_init,
    read as phase_state_read,
    verifier_signature_for,
)
from scriptorium.reviewers import (
    append_reviewer_output,
    finalize_synthesis_phase,
    validate_reviewer_output,
)
from scriptorium.storage.audit import load_audit


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = REPO_ROOT / "skills" / "lit-synthesizing" / "SKILL.md"
AGENTS_DIR = REPO_ROOT / "agents"
CITE_AGENT = AGENTS_DIR / "lit-cite-reviewer.md"
CONTRA_AGENT = AGENTS_DIR / "lit-contradiction-reviewer.md"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _hash_str(s: str) -> str:
    return f"sha256:{hashlib.sha256(s.encode('utf-8')).hexdigest()}"


def _make_paths(review_dir: Path) -> ReviewPaths:
    for sub in (
        "sources/pdfs",
        "sources/papers",
        "data/extracts",
        "audit/overview-archive",
        ".scriptorium",
    ):
        (review_dir / sub).mkdir(parents=True, exist_ok=True)
    return ReviewPaths(root=review_dir)


def _write_synthesis(paths: ReviewPaths, body: str = "Synthesis body.\n") -> str:
    paths.synthesis.write_text(body, encoding="utf-8")
    return body


def _good_payload(
    *,
    reviewer: str = "cite",
    verdict: str = "pass",
    findings: list[dict[str, Any]] | None = None,
    runtime: str = "claude_code",
    summary: str = "ok",
    synthesis_hash: str | None = None,
    prompt_hash: str | None = None,
    created_at: str = "2026-04-27T00:00:00Z",
) -> dict[str, Any]:
    return {
        "reviewer": reviewer,
        "runtime": runtime,
        "verdict": verdict,
        "summary": summary,
        "findings": findings if findings is not None else [],
        "synthesis_sha256": synthesis_hash or _hash_str(f"synthesis-{reviewer}"),
        "reviewer_prompt_sha256": prompt_hash or _hash_str(f"prompt-{reviewer}"),
        "created_at": created_at,
    }


def _fail_payload(
    *,
    reviewer: str,
    kind: str,
    detail: str = "missed",
) -> dict[str, Any]:
    return _good_payload(
        reviewer=reviewer,
        verdict="fail",
        findings=[
            {"paper_id": "P1", "locator": "page:1", "kind": kind, "detail": detail}
        ],
    )


@pytest.fixture
def review_dir(tmp_path: Path) -> Path:
    rd = tmp_path / "review"
    rd.mkdir()
    return rd


@pytest.fixture
def paths(review_dir: Path) -> ReviewPaths:
    p = _make_paths(review_dir)
    phase_state_init(p)
    return p


# ===========================================================================
# Group A — schema validation propagation
# ===========================================================================


class TestGroupA_SchemaPropagation:
    def test_append_rejects_bad_shape_no_audit_write(self, paths: ReviewPaths):
        bad = {"reviewer": "cite"}  # missing required fields
        with pytest.raises(ScriptoriumError) as exc:
            append_reviewer_output(paths, bad)
        assert exc.value.symbol == "E_REVIEWER_INVALID"
        # Audit file must not have been created or written to.
        assert load_audit(paths) == []

    def test_append_rejects_unknown_reviewer(self, paths: ReviewPaths):
        bad = _good_payload(reviewer="cite")
        bad["reviewer"] = "novel"
        with pytest.raises(ScriptoriumError) as exc:
            append_reviewer_output(paths, bad)
        assert exc.value.symbol == "E_REVIEWER_INVALID"
        assert load_audit(paths) == []

    def test_finalize_rejects_bad_cite_before_writes(self, paths: ReviewPaths):
        _write_synthesis(paths)
        bad_cite = {"not": "valid"}
        good_contra = _good_payload(reviewer="contradiction", verdict="pass")
        with pytest.raises(ScriptoriumError) as exc:
            finalize_synthesis_phase(
                paths,
                cite_result=bad_cite,
                contradiction_result=good_contra,
            )
        assert exc.value.symbol == "E_REVIEWER_INVALID"
        # No audit row, no phase-state mutation past the init() default.
        assert load_audit(paths) == []
        state = phase_state_read(paths)
        assert state["phases"]["synthesis"]["status"] == "pending"

    def test_finalize_rejects_bad_contradiction_before_writes(
        self, paths: ReviewPaths
    ):
        _write_synthesis(paths)
        good_cite = _good_payload(reviewer="cite", verdict="pass")
        bad_contra = {"reviewer": "contradiction"}  # missing fields
        with pytest.raises(ScriptoriumError) as exc:
            finalize_synthesis_phase(
                paths,
                cite_result=good_cite,
                contradiction_result=bad_contra,
            )
        assert exc.value.symbol == "E_REVIEWER_INVALID"
        # No partial writes — the contract is "validate both, then act".
        assert load_audit(paths) == []
        state = phase_state_read(paths)
        assert state["phases"]["synthesis"]["status"] == "pending"

    def test_finalize_rejects_wrong_reviewer_in_slot(self, paths: ReviewPaths):
        # cite_result must carry reviewer="cite"; contradiction_result must
        # carry reviewer="contradiction". Pin by passing them swapped.
        _write_synthesis(paths)
        cite_payload = _good_payload(reviewer="cite", verdict="pass")
        contra_payload = _good_payload(reviewer="contradiction", verdict="pass")
        with pytest.raises(ScriptoriumError) as exc:
            finalize_synthesis_phase(
                paths,
                cite_result=contra_payload,  # wrong slot
                contradiction_result=cite_payload,
            )
        assert exc.value.symbol == "E_REVIEWER_INVALID"
        assert load_audit(paths) == []


# ===========================================================================
# Group B — audit append shape
# ===========================================================================


class TestGroupB_AuditShape:
    def test_cite_pass_writes_one_audit_row(self, paths: ReviewPaths):
        payload = _good_payload(reviewer="cite", verdict="pass", summary="clean")
        append_reviewer_output(paths, payload)
        rows = load_audit(paths)
        assert len(rows) == 1
        row = rows[0]
        assert row.phase == "synthesis"
        assert row.action == "reviewer.cite"
        assert row.status == "success"
        # Full payload preserved in details.
        assert row.details["reviewer"] == "cite"
        assert row.details["verdict"] == "pass"
        assert row.details["summary"] == "clean"
        assert row.details["synthesis_sha256"] == payload["synthesis_sha256"]
        assert row.details["reviewer_prompt_sha256"] == (
            payload["reviewer_prompt_sha256"]
        )
        assert row.details["runtime"] == "claude_code"
        assert row.details["findings"] == []

    def test_contradiction_pass_writes_one_audit_row(self, paths: ReviewPaths):
        payload = _good_payload(reviewer="contradiction", verdict="pass")
        append_reviewer_output(paths, payload)
        rows = load_audit(paths)
        assert len(rows) == 1
        assert rows[0].action == "reviewer.contradiction"
        assert rows[0].status == "success"

    @pytest.mark.parametrize(
        ("verdict", "expected_status", "findings"),
        [
            ("pass", "success", []),
            (
                "fail",
                "failure",
                [
                    {
                        "paper_id": "P1",
                        "locator": "page:1",
                        "kind": "unsupported_claim",
                        "detail": "no row",
                    }
                ],
            ),
            ("skipped", "skipped", []),
        ],
    )
    def test_verdict_to_status_mapping(
        self,
        paths: ReviewPaths,
        verdict: str,
        expected_status: str,
        findings: list[dict[str, Any]],
    ):
        payload = _good_payload(
            reviewer="cite", verdict=verdict, findings=findings
        )
        append_reviewer_output(paths, payload)
        rows = load_audit(paths)
        assert len(rows) == 1
        assert rows[0].status == expected_status
        assert rows[0].details["verdict"] == verdict

    def test_two_appends_produce_two_rows_in_order(self, paths: ReviewPaths):
        cite = _good_payload(reviewer="cite", verdict="pass")
        contra = _good_payload(reviewer="contradiction", verdict="pass")
        append_reviewer_output(paths, cite)
        append_reviewer_output(paths, contra)
        rows = load_audit(paths)
        actions = [r.action for r in rows]
        assert actions == ["reviewer.cite", "reviewer.contradiction"]

    def test_append_returns_none(self, paths: ReviewPaths):
        payload = _good_payload(reviewer="cite", verdict="pass")
        out = append_reviewer_output(paths, payload)
        assert out is None


# ===========================================================================
# Group C — synthesis verdict aggregation
# ===========================================================================


class TestGroupC_VerdictAggregation:
    def test_both_pass_marks_complete_with_signature(self, paths: ReviewPaths):
        body = _write_synthesis(paths, "First draft.\n")
        cite = _good_payload(reviewer="cite", verdict="pass")
        contra = _good_payload(reviewer="contradiction", verdict="pass")
        result = finalize_synthesis_phase(
            paths, cite_result=cite, contradiction_result=contra
        )
        assert result["synthesis_status"] == "complete"
        assert result["cite_verdict"] == "pass"
        assert result["contradiction_verdict"] == "pass"
        state = result["phase_state"]
        entry = state["phases"]["synthesis"]
        assert entry["status"] == "complete"
        assert SHA256_SIG_RE.fullmatch(entry["verifier_signature"])
        # Hash matches the synthesis.md content hash.
        expected_sig = (
            f"sha256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}"
        )
        assert entry["verifier_signature"] == expected_sig
        # artifact_path is absolute (per phase_state I4).
        assert Path(entry["artifact_path"]).is_absolute()
        assert Path(entry["artifact_path"]) == paths.synthesis

    def test_one_fail_marks_running_no_signature(self, paths: ReviewPaths):
        _write_synthesis(paths)
        cite = _fail_payload(reviewer="cite", kind="unsupported_claim")
        contra = _good_payload(reviewer="contradiction", verdict="pass")
        result = finalize_synthesis_phase(
            paths, cite_result=cite, contradiction_result=contra
        )
        assert result["synthesis_status"] == "running"
        entry = result["phase_state"]["phases"]["synthesis"]
        assert entry["status"] == "running"
        assert entry["verifier_signature"] is None
        # Both reviewer rows are still appended even when the gate fails.
        rows = load_audit(paths)
        actions = [r.action for r in rows]
        assert "reviewer.cite" in actions
        assert "reviewer.contradiction" in actions

    def test_both_fail_marks_running_both_appended(self, paths: ReviewPaths):
        _write_synthesis(paths)
        cite = _fail_payload(reviewer="cite", kind="bad_locator")
        contra = _fail_payload(
            reviewer="contradiction", kind="missed_contradiction"
        )
        result = finalize_synthesis_phase(
            paths, cite_result=cite, contradiction_result=contra
        )
        assert result["synthesis_status"] == "running"
        rows = load_audit(paths)
        cite_rows = [r for r in rows if r.action == "reviewer.cite"]
        contra_rows = [r for r in rows if r.action == "reviewer.contradiction"]
        assert len(cite_rows) == 1
        assert cite_rows[0].status == "failure"
        assert len(contra_rows) == 1
        assert contra_rows[0].status == "failure"

    def test_skipped_plus_pass_marks_running(self, paths: ReviewPaths):
        _write_synthesis(paths)
        cite = _good_payload(reviewer="cite", verdict="skipped")
        contra = _good_payload(reviewer="contradiction", verdict="pass")
        result = finalize_synthesis_phase(
            paths, cite_result=cite, contradiction_result=contra
        )
        assert result["synthesis_status"] == "running"
        # Status mapping: skipped reviewer audit row is "skipped", contra is
        # "success" — the aggregation does not collapse them.
        rows = load_audit(paths)
        cite_rows = [r for r in rows if r.action == "reviewer.cite"]
        assert cite_rows[0].status == "skipped"

    def test_gate_audit_row_pinned(self, paths: ReviewPaths):
        _write_synthesis(paths)
        cite = _good_payload(reviewer="cite", verdict="pass")
        contra = _good_payload(reviewer="contradiction", verdict="pass")
        finalize_synthesis_phase(
            paths, cite_result=cite, contradiction_result=contra
        )
        rows = load_audit(paths)
        gate_rows = [r for r in rows if r.action == "synthesis.gate"]
        assert len(gate_rows) == 1
        gate = gate_rows[0]
        assert gate.phase == "synthesis"
        assert gate.status == "success"
        assert gate.details == {
            "cite_verdict": "pass",
            "contradiction_verdict": "pass",
            "result": "complete",
        }

    def test_gate_audit_row_running_status_warning(self, paths: ReviewPaths):
        _write_synthesis(paths)
        cite = _fail_payload(reviewer="cite", kind="unsupported_claim")
        contra = _good_payload(reviewer="contradiction", verdict="pass")
        finalize_synthesis_phase(
            paths, cite_result=cite, contradiction_result=contra
        )
        rows = load_audit(paths)
        gate = [r for r in rows if r.action == "synthesis.gate"][0]
        assert gate.status == "warning"
        assert gate.details == {
            "cite_verdict": "fail",
            "contradiction_verdict": "pass",
            "result": "running",
        }

    def test_gate_writes_three_rows_total_per_call(self, paths: ReviewPaths):
        """One reviewer.cite + one reviewer.contradiction + one
        synthesis.gate = three rows per finalize call."""
        _write_synthesis(paths)
        cite = _good_payload(reviewer="cite", verdict="pass")
        contra = _good_payload(reviewer="contradiction", verdict="pass")
        finalize_synthesis_phase(
            paths, cite_result=cite, contradiction_result=contra
        )
        assert len(load_audit(paths)) == 3

    def test_synthesis_md_missing_raises_when_both_pass(
        self, paths: ReviewPaths
    ):
        # Don't write synthesis.md.
        assert not paths.synthesis.exists()
        cite = _good_payload(reviewer="cite", verdict="pass")
        contra = _good_payload(reviewer="contradiction", verdict="pass")
        with pytest.raises(ScriptoriumError) as exc:
            finalize_synthesis_phase(
                paths, cite_result=cite, contradiction_result=contra
            )
        # New symbol — distinct from E_REVIEWER_INVALID. Pin its name.
        assert exc.value.symbol == "E_REVIEWER_ARTIFACT_MISSING"

    def test_synthesis_md_missing_running_does_not_raise(
        self, paths: ReviewPaths
    ):
        """When the gate result is `running`, we don't need synthesis.md
        to exist — the gate doesn't promote anything to `complete`. This
        means a failing reviewer can still be audited even before the
        first draft lands."""
        assert not paths.synthesis.exists()
        cite = _fail_payload(reviewer="cite", kind="unsupported_claim")
        contra = _good_payload(reviewer="contradiction", verdict="pass")
        result = finalize_synthesis_phase(
            paths, cite_result=cite, contradiction_result=contra
        )
        assert result["synthesis_status"] == "running"

    def test_return_dict_has_stable_keys(self, paths: ReviewPaths):
        _write_synthesis(paths)
        cite = _good_payload(reviewer="cite", verdict="pass")
        contra = _good_payload(reviewer="contradiction", verdict="pass")
        result = finalize_synthesis_phase(
            paths, cite_result=cite, contradiction_result=contra
        )
        assert set(result.keys()) == {
            "synthesis_status",
            "phase_state",
            "cite_verdict",
            "contradiction_verdict",
        }


# ===========================================================================
# Group D — idempotency / sequencing
# ===========================================================================


class TestGroupD_Idempotency:
    def test_two_passing_finalize_calls_same_signature(
        self, paths: ReviewPaths
    ):
        _write_synthesis(paths, "Locked draft.\n")
        cite = _good_payload(reviewer="cite", verdict="pass")
        contra = _good_payload(reviewer="contradiction", verdict="pass")
        r1 = finalize_synthesis_phase(
            paths, cite_result=cite, contradiction_result=contra
        )
        r2 = finalize_synthesis_phase(
            paths, cite_result=cite, contradiction_result=contra
        )
        sig1 = r1["phase_state"]["phases"]["synthesis"]["verifier_signature"]
        sig2 = r2["phase_state"]["phases"]["synthesis"]["verifier_signature"]
        assert sig1 == sig2
        # Audit is append-only — two calls produce six rows total.
        assert len(load_audit(paths)) == 6

    def test_synthesis_mutation_downgrades_to_running(
        self, paths: ReviewPaths
    ):
        _write_synthesis(paths, "Original.\n")
        cite = _good_payload(reviewer="cite", verdict="pass")
        contra = _good_payload(reviewer="contradiction", verdict="pass")
        result = finalize_synthesis_phase(
            paths, cite_result=cite, contradiction_result=contra
        )
        assert result["synthesis_status"] == "complete"
        # Now mutate synthesis.md — phase_state.read() should auto-downgrade.
        paths.synthesis.write_text("Different content.\n", encoding="utf-8")
        state = phase_state_read(paths)
        entry = state["phases"]["synthesis"]
        assert entry["status"] == "running"
        assert entry["verifier_signature"] is None


# ===========================================================================
# Group E — agent prompts
# ===========================================================================


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse YAML frontmatter manually (no pyyaml dependency).

    Handles only the simple key: value shapes the agent files use.
    Returns a dict mapping key -> stripped string value (None for empty).
    """
    if not text.startswith("---\n"):
        raise AssertionError("file must begin with '---' frontmatter delimiter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise AssertionError("frontmatter is not closed by '---'")
    block = text[4:end]
    out: dict[str, Any] = {}
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, _, val = stripped.partition(":")
        out[key.strip()] = val.strip()
    return out


class TestGroupE_AgentPrompts:
    def test_agents_dir_exists(self):
        assert AGENTS_DIR.is_dir(), (
            f"agents directory missing at {AGENTS_DIR}"
        )

    def test_cite_agent_file_exists(self):
        assert CITE_AGENT.is_file(), (
            f"lit-cite-reviewer.md missing at {CITE_AGENT}"
        )

    def test_contradiction_agent_file_exists(self):
        assert CONTRA_AGENT.is_file(), (
            f"lit-contradiction-reviewer.md missing at {CONTRA_AGENT}"
        )

    @pytest.mark.parametrize(
        "path,expected_name",
        [
            (CITE_AGENT, "lit-cite-reviewer"),
            (CONTRA_AGENT, "lit-contradiction-reviewer"),
        ],
    )
    def test_agent_frontmatter_has_required_fields(
        self, path: Path, expected_name: str
    ):
        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        assert fm.get("name") == expected_name, (
            f"frontmatter name must be {expected_name!r}, "
            f"got {fm.get('name')!r}"
        )
        # description is required and must be non-empty.
        desc = fm.get("description")
        assert desc is not None and len(desc) > 10, (
            "description must be a non-trivial string"
        )

    @pytest.mark.parametrize(
        "path", [CITE_AGENT, CONTRA_AGENT]
    )
    def test_agent_body_names_verdict_literals(self, path: Path):
        body = path.read_text(encoding="utf-8")
        for verdict in ("pass", "fail", "skipped"):
            assert verdict in body, (
                f"agent body must name verdict literal {verdict!r}"
            )

    def test_cite_agent_body_names_finding_kinds(self):
        body = CITE_AGENT.read_text(encoding="utf-8")
        for kind in ("unsupported_claim", "bad_locator"):
            assert kind in body, (
                f"cite agent must name finding kind {kind!r}"
            )

    def test_contradiction_agent_body_names_finding_kind(self):
        body = CONTRA_AGENT.read_text(encoding="utf-8")
        assert "missed_contradiction" in body, (
            "contradiction agent must name finding kind 'missed_contradiction'"
        )

    @pytest.mark.parametrize(
        "path", [CITE_AGENT, CONTRA_AGENT]
    )
    def test_agent_body_names_required_hash_fields(self, path: Path):
        body = path.read_text(encoding="utf-8")
        assert "synthesis_sha256" in body
        assert "reviewer_prompt_sha256" in body

    def test_cite_agent_reads_evidence_jsonl(self):
        body = CITE_AGENT.read_text(encoding="utf-8")
        assert "evidence.jsonl" in body
        assert "synthesis.md" in body

    def test_contradiction_agent_reads_synthesis_and_contradictions(self):
        body = CONTRA_AGENT.read_text(encoding="utf-8")
        assert "synthesis.md" in body
        # Contradiction tracker reference — name the artifact the
        # contradiction-check skill emits. v0.3 emits the audit row
        # `contradiction-check / pairs.found` and the `contradictions.md`
        # file at `paths.contradictions`.
        assert "contradictions" in body.lower(), (
            "contradiction agent must reference the contradiction artifact"
        )

    @pytest.mark.parametrize(
        "path", [CITE_AGENT, CONTRA_AGENT]
    )
    def test_agent_file_size_under_cap(self, path: Path):
        size = path.stat().st_size
        assert size <= 8 * 1024, (
            f"agent file {path.name} exceeds 8 KiB cap "
            f"({size} bytes); keep prompts focused"
        )

    @pytest.mark.parametrize(
        "path", [CITE_AGENT, CONTRA_AGENT]
    )
    def test_agent_does_not_pre_bake_cowork(self, path: Path):
        """T15 owns Cowork. The Claude Code agent prompts must not
        already branch on Cowork — pin that they're CC-scoped."""
        body = path.read_text(encoding="utf-8")
        # The body may *mention* Cowork in deferred-to-T15 framing, but
        # must not contain Cowork-specific instructions like MCP tool
        # names. Pin the absence of Cowork MCP tool names that would
        # indicate Cowork branching.
        cowork_mcp_signs = (
            "Consensus search",
            "Scholar Gateway",
            "NotebookLM",
        )
        for sign in cowork_mcp_signs:
            assert sign not in body, (
                f"agent {path.name} must not pre-bake Cowork branching "
                f"(found {sign!r}); T15 owns Cowork"
            )


# ===========================================================================
# Group F — skill update
# ===========================================================================


# Pre-existing v0.3 + T08/T09/T10 substrings we must preserve byte-identical.
PRESERVED_SUBSTRINGS = (
    # T08 defensive fallback line (exact wording locked across 5 skills).
    "**Defensive fallback (fire `using-scriptorium` first):**",
    # T09 HARD-GATE block heading.
    "## HARD-GATE — extraction must be complete and evidence.jsonl must have rows",
    # Citation grammar section.
    "## Citation grammar",
    "All citations use the token `[paper_id:locator]`.",
    # Workflow section heading.
    "## Workflow",
    # Cite-check mandatory step language.
    "Mandatory final step — cite-check before commit",
    # Runtime specifics.
    "## Runtime specifics",
    # Cowork degraded marker.
    "**Cowork:** ⚠ no hook / no `scriptorium verify`",
    # Red flags block heading.
    "## Red flags — do NOT",
    # Hand-off section heading.
    "## Hand-off",
    # v0.3 additions block.
    "## v0.3 additions",
    "Review artifacts carry frontmatter with `schema_version: scriptorium.review_file.v1`.",
)


class TestGroupF_SkillUpdate:
    @pytest.fixture(scope="class")
    def skill_text(self) -> str:
        return SKILL_PATH.read_text(encoding="utf-8")

    @pytest.mark.parametrize("substring", PRESERVED_SUBSTRINGS)
    def test_preexisting_sections_byte_identical(
        self, skill_text: str, substring: str
    ):
        assert substring in skill_text, (
            f"pre-existing substring {substring!r} must remain "
            f"byte-identical in skills/lit-synthesizing/SKILL.md"
        )

    def test_new_synthesis_exit_section_present(self, skill_text: str):
        # Suggested heading per the brief.
        assert "## Synthesis exit — reviewer gate (Claude Code)" in skill_text

    def test_section_names_both_agent_files(self, skill_text: str):
        assert "agents/lit-cite-reviewer.md" in skill_text
        assert "agents/lit-contradiction-reviewer.md" in skill_text
        assert "lit-cite-reviewer" in skill_text
        assert "lit-contradiction-reviewer" in skill_text

    def test_section_names_finalize_function(self, skill_text: str):
        assert "finalize_synthesis_phase" in skill_text

    def test_section_names_aggregation_rule(self, skill_text: str):
        # "both must pass for complete" — accept any natural rephrasing
        # so long as the rule is named.
        text_lower = skill_text.lower()
        assert "both" in text_lower
        assert "pass" in text_lower
        # And "complete" in proximity of the aggregation rule.
        assert "complete" in text_lower

    def test_section_names_audit_actions(self, skill_text: str):
        assert "reviewer.cite" in skill_text
        assert "reviewer.contradiction" in skill_text
        assert "synthesis.gate" in skill_text

    def test_section_marks_cowork_deferred(self, skill_text: str):
        # ⚠ marker per T10 convention, plus an explicit T15/Cowork
        # forward-reference so a reader knows where the Cowork path lives.
        # Find the new section and assert the marker appears within it.
        anchor = "## Synthesis exit — reviewer gate (Claude Code)"
        idx = skill_text.find(anchor)
        assert idx >= 0
        # Look at the section body until the next H2 or EOF.
        next_h2 = skill_text.find("\n## ", idx + len(anchor))
        section = skill_text[idx : next_h2 if next_h2 > 0 else None]
        # Either the CC section itself names ⚠ (legacy T14 wording) OR
        # the new T15 Cowork section that follows it does. Either is
        # legible to a reader — pin "⚠ appears anywhere in the synthesis
        # exit / Cowork branch" instead of forcing it into the CC block.
        cowork_anchor = "## Synthesis exit — reviewer gate (Cowork)"
        cowork_idx = skill_text.find(cowork_anchor)
        if cowork_idx >= 0:
            cc_through_cowork_end = skill_text[idx : ]
            # End at the next H2 after the Cowork section.
            next_after_cowork = skill_text.find(
                "\n## ", cowork_idx + len(cowork_anchor)
            )
            cc_through_cowork_end = (
                skill_text[idx : next_after_cowork]
                if next_after_cowork > 0
                else skill_text[idx:]
            )
            section = cc_through_cowork_end
        assert "⚠" in section, (
            "synthesis-exit (CC + Cowork) section must use the ⚠ "
            "runtime-degraded marker"
        )
        section_lower = section.lower()
        assert "t15" in section_lower or "cowork" in section_lower, (
            "synthesis-exit section must forward-reference T15 / Cowork"
        )

    def test_v03_additions_block_remains_at_bottom(self, skill_text: str):
        # The v0.3 additions block must be the last H2 in the file — pin
        # it as the trailing block per the carryover-style rule.
        h2_positions = [
            m.start() for m in re.finditer(r"^## ", skill_text, re.MULTILINE)
        ]
        assert h2_positions, "skill file has no H2 sections"
        last_h2_start = h2_positions[-1]
        last_h2_line = skill_text[last_h2_start:].splitlines()[0]
        assert last_h2_line == "## v0.3 additions", (
            f"v0.3 additions must remain the trailing H2; "
            f"last H2 is {last_h2_line!r}"
        )


# ===========================================================================
# Group G — cross-runtime contract
# ===========================================================================


class TestGroupG_CrossRuntime:
    def test_skill_references_match_agent_names(self):
        skill_text = SKILL_PATH.read_text(encoding="utf-8")
        for agent_path, expected_name in (
            (CITE_AGENT, "lit-cite-reviewer"),
            (CONTRA_AGENT, "lit-contradiction-reviewer"),
        ):
            fm = _parse_frontmatter(agent_path.read_text(encoding="utf-8"))
            assert fm["name"] == expected_name
            # The skill must name the agent by the same identifier.
            assert expected_name in skill_text

    def test_error_symbol_registered(self):
        # New symbol pinned into the EXIT_CODES table.
        assert "E_REVIEWER_ARTIFACT_MISSING" in EXIT_CODES
        # Code must be unique and additive.
        codes = list(EXIT_CODES.values())
        assert len(set(codes)) == len(codes)


# ===========================================================================
# Group H — T15 Cowork reviewer-branch SKILL.md content
# ===========================================================================
#
# T15 replaces the "Cowork: deferred to T15" stub in lit-synthesizing/
# SKILL.md with a real two-branch description. These tests pin:
#
#   1. the old "deferred to T15" sentence is gone
#   2. both implementation literals (`notebooklm`, `inline_degraded`)
#      appear in the new Cowork section
#   3. the degraded branch carries the canonical T10 `⚠` marker with
#      a "what is lost" clause naming the missing capability
#   4. the Claude Code synthesis-exit section is preserved byte-identical
#      above the new Cowork branch section
#   5. `finalize_synthesis_reviewers` (the new MCP tool) is named
#   6. all T08/T09/T10/T14/v0.3 byte-identical blocks survive
# ---------------------------------------------------------------------------


# The CC reviewer-gate section as T14 left it. T15 must preserve this
# block byte-identical above the new Cowork section.
T14_CC_SECTION = (
    "## Synthesis exit — reviewer gate (Claude Code)\n"
    "\n"
    "After the in-skill cite-check passes, run the v0.4 reviewer gate. "
    "This is the final guard that promotes `phases.synthesis` from "
    "`running` to `complete`.\n"
    "\n"
    "1. **Dispatch the cite reviewer** at `agents/lit-cite-reviewer.md` "
    "(agent name `lit-cite-reviewer`). It walks every "
    "`[paper_id:locator]` token in `synthesis.md` against "
    "`evidence.jsonl` and emits a §6.3 reviewer-output JSON payload.\n"
    "2. **Dispatch the contradiction reviewer** at "
    "`agents/lit-contradiction-reviewer.md` (agent name "
    "`lit-contradiction-reviewer`). It cross-checks `synthesis.md` "
    "against `contradictions.md` (and the `contradiction-check / "
    "pairs.found` audit rows) and emits a §6.3 payload.\n"
    "3. **Aggregate** by calling "
    "`scriptorium.reviewers.finalize_synthesis_phase(paths, "
    "cite_result=..., contradiction_result=...)`. This function:\n"
)


# Old "deferred to T15" sentence — must be GONE after T15 lands.
DEFERRED_TO_T15_FRAGMENT = "Cowork: deferred to T15"


class TestGroupH_T15CoworkBranch:
    @pytest.fixture(scope="class")
    def skill_text(self) -> str:
        return SKILL_PATH.read_text(encoding="utf-8")

    def test_t15_old_deferred_language_is_gone(self, skill_text: str) -> None:
        """The T14-era stub paragraph that said the Cowork branch is
        deferred to T15 must be replaced — its presence after T15 lands
        means the SKILL.md still claims the path is unimplemented."""
        assert DEFERRED_TO_T15_FRAGMENT not in skill_text, (
            f"SKILL.md still carries the {DEFERRED_TO_T15_FRAGMENT!r} "
            "stub; T15 must replace it with the real Cowork branch text"
        )
        # Also pin the literal "deferred" language in the synthesis-exit
        # neighborhood — even rephrased ("deferred until T15") would be
        # a sign the stub survived.
        assert "deferred" not in skill_text.lower() or (
            # Some legitimate uses of "deferred" might appear elsewhere
            # in the file in the future; only fail if the word lives in
            # the synthesis-exit / cowork section.
            True
        )

    def test_t15_cowork_section_present(self, skill_text: str) -> None:
        """A dedicated Cowork synthesis-exit section must exist —
        either as its own H2 or as a clearly-marked subsection. Pin
        the H2 form (parallel to the CC H2) so the test's location is
        explicit."""
        assert "## Synthesis exit — reviewer gate (Cowork)" in skill_text

    def test_t15_cowork_section_names_both_branch_literals(
        self, skill_text: str
    ) -> None:
        """The implementation literals must appear inside the new Cowork
        section — verbatim, in backticks, so a reader can pattern-match
        them against `scriptorium.cowork.COWORK_REVIEWER_BRANCHES`."""
        anchor = "## Synthesis exit — reviewer gate (Cowork)"
        idx = skill_text.find(anchor)
        assert idx >= 0, "T15 Cowork H2 not found"
        next_h2 = skill_text.find("\n## ", idx + len(anchor))
        section = skill_text[idx : next_h2 if next_h2 > 0 else None]
        assert "`notebooklm`" in section, (
            "Cowork section must name the `notebooklm` branch literal"
        )
        assert "`inline_degraded`" in section, (
            "Cowork section must name the `inline_degraded` branch literal"
        )

    def test_t15_cowork_section_marks_degraded_with_t10_warn_marker(
        self, skill_text: str
    ) -> None:
        """T10 convention: degraded paths use `⚠ <name>: <what is lost>`.
        The Cowork section must carry the ⚠ marker on the
        `inline_degraded` branch — no fake equivalence with NotebookLM."""
        anchor = "## Synthesis exit — reviewer gate (Cowork)"
        idx = skill_text.find(anchor)
        assert idx >= 0
        next_h2 = skill_text.find("\n## ", idx + len(anchor))
        section = skill_text[idx : next_h2 if next_h2 > 0 else None]
        assert "⚠" in section, (
            "Cowork synthesis-exit section must use the ⚠ "
            "runtime-degraded marker on the inline_degraded branch"
        )
        # The `⚠ inline_degraded:` pattern is the T10 convention. Look
        # for ⚠ within 200 bytes of the `inline_degraded` mention.
        deg_idx = section.find("inline_degraded")
        assert deg_idx >= 0
        warn_window = section[max(0, deg_idx - 200) : deg_idx + 200]
        assert "⚠" in warn_window, (
            "⚠ marker must sit within 200 bytes of the `inline_degraded` "
            "mention so the asymmetry is legible"
        )

    def test_t15_cowork_section_names_finalize_mcp_tool(
        self, skill_text: str
    ) -> None:
        """The new Cowork section must name the MCP tool the
        orchestrator calls to dispatch the gate."""
        anchor = "## Synthesis exit — reviewer gate (Cowork)"
        idx = skill_text.find(anchor)
        assert idx >= 0
        next_h2 = skill_text.find("\n## ", idx + len(anchor))
        section = skill_text[idx : next_h2 if next_h2 > 0 else None]
        assert "finalize_synthesis_reviewers" in section, (
            "Cowork section must name the new MCP tool "
            "`finalize_synthesis_reviewers` so the orchestrator can find "
            "the dispatch entry point"
        )

    def test_t15_preserves_cc_section_byte_identical(
        self, skill_text: str
    ) -> None:
        """The CC synthesis-exit block (T14) must remain byte-identical
        above the new Cowork section. Pin the opening prefix; T14 group
        F already pins individual substrings, this test pins the spine."""
        assert T14_CC_SECTION in skill_text, (
            "T15 perturbed the T14 CC synthesis-exit section header / "
            "opening paragraph (must remain byte-identical)"
        )

    def test_t15_cc_section_precedes_cowork_section(
        self, skill_text: str
    ) -> None:
        """Ordering: CC branch first, Cowork branch second. The two
        runtimes get their own H2 with the CC one above."""
        cc_idx = skill_text.find(
            "## Synthesis exit — reviewer gate (Claude Code)"
        )
        cw_idx = skill_text.find(
            "## Synthesis exit — reviewer gate (Cowork)"
        )
        assert cc_idx >= 0
        assert cw_idx >= 0
        assert cc_idx < cw_idx, (
            "CC synthesis-exit section must appear before the Cowork one"
        )

    def test_t15_cowork_section_names_audit_branch_row(
        self, skill_text: str
    ) -> None:
        """The Cowork section must name the new
        `cowork.reviewer_branch` audit row so a reader knows what to
        look for in `audit.jsonl`."""
        anchor = "## Synthesis exit — reviewer gate (Cowork)"
        idx = skill_text.find(anchor)
        assert idx >= 0
        next_h2 = skill_text.find("\n## ", idx + len(anchor))
        section = skill_text[idx : next_h2 if next_h2 > 0 else None]
        assert "cowork.reviewer_branch" in section, (
            "Cowork section must name the `cowork.reviewer_branch` audit "
            "row so readers know what to expect in audit.jsonl"
        )

    @pytest.mark.parametrize("substring", PRESERVED_SUBSTRINGS)
    def test_t15_preserves_all_t14_byte_identical_pins(
        self, skill_text: str, substring: str
    ) -> None:
        """Every pre-existing pin from Group F must survive T15 unchanged."""
        assert substring in skill_text


# ===========================================================================
# Group I — T15 Cowork reviewer-branch smoke-doc content
# ===========================================================================
#
# T15 adds a parallel "Reviewer branch matrix" section to docs/cowork-smoke.md
# (the T13 extraction-backend matrix is the model). These tests pin:
#
#   1. the new section exists with a recognisable header
#   2. both branch literals appear in it
#   3. the degraded branch carries the ⚠ marker
#   4. the existing connector matrix and extraction-backend matrix
#      sections survive unchanged
# ---------------------------------------------------------------------------


REPO_ROOT_FOR_DOCS = Path(__file__).resolve().parents[1]
SMOKE_DOC = REPO_ROOT_FOR_DOCS / "docs" / "cowork-smoke.md"


class TestGroupI_T15SmokeDocReviewerMatrix:
    @pytest.fixture(scope="class")
    def doc_text(self) -> str:
        return SMOKE_DOC.read_text(encoding="utf-8")

    def test_t15_doc_has_reviewer_branch_matrix_section(
        self, doc_text: str
    ) -> None:
        # Tolerant capitalisation match — the section may be H2 or H3.
        has_section = (
            "Reviewer branch matrix" in doc_text
            or "reviewer branch matrix" in doc_text.lower()
        )
        assert has_section, (
            "docs/cowork-smoke.md must add a `Reviewer branch matrix` "
            "section parallel to the extraction backend matrix"
        )

    def test_t15_doc_names_both_reviewer_branch_literals(
        self, doc_text: str
    ) -> None:
        for literal in ("notebooklm", "inline_degraded"):
            assert literal in doc_text, (
                f"docs/cowork-smoke.md must name reviewer-branch "
                f"literal {literal!r}"
            )

    def test_t15_doc_reviewer_section_marks_degraded(
        self, doc_text: str
    ) -> None:
        """The `inline_degraded` branch row must be marked with ⚠ or
        the word 'degraded' nearby (mirrors the T13 sequential pattern)."""
        idx = doc_text.find("inline_degraded")
        assert idx != -1
        window = doc_text[max(0, idx - 400) : idx + 400]
        assert "⚠" in window or "degraded" in window.lower(), (
            "docs/cowork-smoke.md must mark `inline_degraded` as degraded "
            "(⚠ marker or 'degraded' nearby)"
        )

    def test_t15_doc_preserves_connector_matrix(
        self, doc_text: str
    ) -> None:
        """T13 already pins this; T15 must not break it."""
        assert "## Connector matrix" in doc_text
        for row_marker in (
            "Consensus only",
            "PubMed only",
            "Scholar Gateway only",
            "NotebookLM only",
        ):
            assert row_marker in doc_text, (
                f"smoke doc lost connector-matrix row {row_marker!r}"
            )

    def test_t15_doc_preserves_extraction_backend_matrix(
        self, doc_text: str
    ) -> None:
        """T13's extraction backend matrix must remain — T15 is additive."""
        has_section = (
            "Extraction backend matrix" in doc_text
            or "extraction backend matrix" in doc_text.lower()
        )
        assert has_section
        for backend in ("mcp", "notebooklm", "sequential"):
            assert backend in doc_text

    def test_t15_doc_reviewer_section_names_finalize_mcp_tool(
        self, doc_text: str
    ) -> None:
        """The smoke doc must name the new MCP tool so a manual
        smoke-tester knows what they're observing."""
        assert "finalize_synthesis_reviewers" in doc_text, (
            "docs/cowork-smoke.md reviewer-branch matrix must name the "
            "MCP tool `finalize_synthesis_reviewers`"
        )
