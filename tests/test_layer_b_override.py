"""Layer B / T16: audited override and publish blocking.

Phase 5 final lock — publish stays blocked unless the synthesis and
contradiction phases are both ``complete`` (reviewer pass) or
``overridden`` (audited override). T16 also makes the override paths
themselves carry per-runtime authority guards and append an immutable
``phase.override`` audit row.

Pins (plan §7 + §6.3 + T16 brief):

  A. CLI override TTY-guard — ``scriptorium phase override`` requires
     either ``--yes`` (non-interactive) or an interactive ``y``/``yes``
     confirmation on a real TTY. Non-TTY without ``--yes`` returns
     ``E_USAGE`` and does NOT touch phase-state.
  B. MCP override explicit marker — ``phase_override`` requires
     ``confirm=True``. Truthy non-bool inputs ("yes", 1) do NOT pass —
     ``confirm is True`` is the only acceptance condition. Failed
     confirm returns ``E_USAGE`` and does NOT touch phase-state.
  C. Audit immutability — every successful override appends exactly
     ONE ``phase.override`` row carrying ``phase``, ``reason``,
     ``actor``, ``ts``, ``runtime`` in ``details``. The ``ts`` field
     equals ``phase-state.json::phases.<phase>.override.ts`` for the
     same call. Two overrides append two rows (append-only). CLI rows
     carry ``runtime="claude_code"``; MCP rows carry
     ``runtime="cowork"``.
  D. Publish blocking — ``enforce_v04=True`` makes incomplete
     synthesis or contradiction return ``E_REVIEW_INCOMPLETE``. Both
     phases must be ``complete`` or ``overridden`` for publish to
     proceed. Override unblocks identically to a clean reviewer pass.
     A ``publish.blocked`` audit row is appended on the blocking path.
  E. Publish advisory — ``enforce_v04=False`` (default) writes a
     warning to stderr and an ``audit.advisory`` audit row, then
     proceeds with the existing publish flow. JSON stdout payload is
     unaltered.
  F. Cowork-mode publish bypasses the gate — ``SCRIPTORIUM_FORCE_COWORK``
     short-circuits before the gate runs. No phase-state read by the
     gate, no gate audit row.
"""
from __future__ import annotations

import io
import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from scriptorium import cli as cli_mod
from scriptorium import phase_state
from scriptorium.errors import EXIT_CODES
from scriptorium.mcp import server as mcp_server
from scriptorium.nlm import NlmResult, NotebookCreated
from scriptorium.paths import resolve_review_dir
from scriptorium.storage.audit import load_audit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeTTY(io.StringIO):
    """A StringIO that reports as a TTY (for interactive prompt tests)."""

    def isatty(self) -> bool:  # noqa: D401 — boolean, not a description
        return True


def _run_cli(args, review_dir, *, stdin: io.StringIO | None = None):
    out, err = StringIO(), StringIO()
    full_args = list(args) + ["--review-dir", str(review_dir)]
    rc = cli_mod.main(
        argv=full_args,
        stdout=out,
        stderr=err,
        stdin=stdin if stdin is not None else StringIO(""),
    )
    return rc, out.getvalue(), err.getvalue()


def _write_enforce_v04(review_dir: Path, *, value: bool) -> None:
    """Write ``[scriptorium] enforce_v04 = <value>`` to config.toml."""
    cfg = review_dir / "config.toml"
    flag = "true" if value else "false"
    cfg.write_text(
        f"[scriptorium]\nenforce_v04 = {flag}\n",
        encoding="utf-8",
    )


def _make_publish_review(tmp_path: Path) -> Path:
    """Build a review dir with the four required prose deliverables.

    Mirrors ``tests/test_publish_flow.py::_make_review`` so the publish
    flow has something legitimate to operate on once the gate passes.
    """
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    for name in ("overview.md", "synthesis.md", "contradictions.md"):
        (root / name).write_text("x", encoding="utf-8")
    (root / "data").mkdir(parents=True)
    (root / "data" / "evidence.jsonl").write_text("x", encoding="utf-8")
    pdfs = root / "sources" / "pdfs"
    pdfs.mkdir(parents=True)
    (pdfs / "alpha.pdf").write_bytes(b"a")
    return root


def _set_synthesis_complete(paths) -> None:
    sig = "sha256:" + "a" * 64
    phase_state.set_phase(paths, "synthesis", "complete", verifier_signature=sig)


def _set_contradiction_complete(paths) -> None:
    sig = "sha256:" + "b" * 64
    phase_state.set_phase(
        paths, "contradiction", "complete", verifier_signature=sig
    )


# ===========================================================================
# A. CLI override TTY-guard
# ===========================================================================


class TestGroupA_CliOverrideTtyGuard:
    def test_yes_flag_succeeds_non_interactive(self, review_dir):
        rc, out, err = _run_cli(
            ["phase", "override", "synthesis",
             "--reason", "Reviewer misfire", "--yes"],
            review_dir,
        )
        assert rc == 0, err
        state = json.loads(out)
        assert state["phases"]["synthesis"]["status"] == "overridden"
        assert state["phases"]["synthesis"]["override"]["reason"] == (
            "Reviewer misfire"
        )

    def test_non_tty_without_yes_returns_e_usage(self, review_dir):
        # StringIO is not a TTY; without --yes the guard refuses.
        rc, out, err = _run_cli(
            ["phase", "override", "synthesis", "--reason", "skip"],
            review_dir,
        )
        assert rc == EXIT_CODES["E_USAGE"]
        # Phase-state must not have been mutated.
        paths = resolve_review_dir(explicit=review_dir)
        state = phase_state.read(paths)
        assert state["phases"]["synthesis"]["status"] == "pending"
        assert state["phases"]["synthesis"]["override"] is None
        # Stderr must explain the requirement.
        assert "--yes" in err or "TTY" in err or "tty" in err

    def test_tty_interactive_yes_succeeds(self, review_dir):
        stdin = _FakeTTY("y\n")
        rc, out, err = _run_cli(
            ["phase", "override", "synthesis", "--reason", "Reviewer misfire"],
            review_dir,
            stdin=stdin,
        )
        assert rc == 0, err
        # Stdout begins with the TTY prompt; the JSON payload follows.
        # Strip from the first '{' to the end and parse that.
        payload = out[out.index("{"):]
        state = json.loads(payload)
        assert state["phases"]["synthesis"]["status"] == "overridden"

    def test_tty_interactive_n_aborts(self, review_dir):
        stdin = _FakeTTY("n\n")
        rc, out, err = _run_cli(
            ["phase", "override", "synthesis", "--reason", "Reviewer misfire"],
            review_dir,
            stdin=stdin,
        )
        # An aborted override is a benign no-op — exit 0.
        assert rc == 0, err
        # Phase-state is still pending.
        paths = resolve_review_dir(explicit=review_dir)
        state = phase_state.read(paths)
        assert state["phases"]["synthesis"]["status"] == "pending"

    def test_tty_interactive_eof_aborts(self, review_dir):
        # Empty stdin (EOF) on a TTY is treated as a refusal.
        stdin = _FakeTTY("")
        rc, _, _ = _run_cli(
            ["phase", "override", "synthesis", "--reason", "Reviewer misfire"],
            review_dir,
            stdin=stdin,
        )
        assert rc == 0
        paths = resolve_review_dir(explicit=review_dir)
        state = phase_state.read(paths)
        assert state["phases"]["synthesis"]["status"] == "pending"


# ===========================================================================
# B. MCP override explicit marker
# ===========================================================================


class TestGroupB_McpOverrideExplicitMarker:
    def test_confirm_true_succeeds(self, review_dir):
        result = mcp_server.phase_override(
            review_dir=str(review_dir),
            phase="synthesis",
            reason="Cowork override",
            actor="cowork-ops",
            confirm=True,
        )
        # Successful override returns the merged phase-state dict.
        assert "phases" in result
        assert result["phases"]["synthesis"]["status"] == "overridden"
        assert result["phases"]["synthesis"]["override"]["actor"] == "cowork-ops"

    def test_confirm_false_returns_e_usage(self, review_dir):
        result = mcp_server.phase_override(
            review_dir=str(review_dir),
            phase="synthesis",
            reason="Cowork override",
            actor="cowork-ops",
            confirm=False,
        )
        assert "error" in result
        assert result["code"] == EXIT_CODES["E_USAGE"]
        # No phase-state mutation.
        paths = resolve_review_dir(explicit=review_dir)
        state = phase_state.read(paths)
        assert state["phases"]["synthesis"]["status"] == "pending"
        # No audit row.
        assert load_audit(paths) == []

    def test_confirm_omitted_returns_e_usage(self, review_dir):
        # Default confirm=False applies — same shape as above.
        result = mcp_server.phase_override(
            review_dir=str(review_dir),
            phase="synthesis",
            reason="Cowork override",
            actor="cowork-ops",
        )
        assert "error" in result
        assert result["code"] == EXIT_CODES["E_USAGE"]
        paths = resolve_review_dir(explicit=review_dir)
        state = phase_state.read(paths)
        assert state["phases"]["synthesis"]["status"] == "pending"

    def test_truthy_non_bool_string_does_not_satisfy_confirm(self, review_dir):
        # "yes" is truthy but not `is True`; must be rejected.
        result = mcp_server.phase_override(
            review_dir=str(review_dir),
            phase="synthesis",
            reason="Cowork override",
            actor="cowork-ops",
            confirm="yes",  # type: ignore[arg-type]
        )
        assert "error" in result
        assert result["code"] == EXIT_CODES["E_USAGE"]

    def test_truthy_non_bool_int_does_not_satisfy_confirm(self, review_dir):
        # 1 is truthy but not `is True` — same rule.
        result = mcp_server.phase_override(
            review_dir=str(review_dir),
            phase="synthesis",
            reason="Cowork override",
            actor="cowork-ops",
            confirm=1,  # type: ignore[arg-type]
        )
        assert "error" in result
        assert result["code"] == EXIT_CODES["E_USAGE"]


# ===========================================================================
# C. Audit immutability of override rows
# ===========================================================================


class TestGroupC_AuditImmutability:
    def test_cli_override_appends_one_phase_override_row(self, review_dir):
        rc, out, err = _run_cli(
            ["phase", "override", "synthesis",
             "--reason", "Reviewer misfire", "--yes"],
            review_dir,
        )
        assert rc == 0, err
        paths = resolve_review_dir(explicit=review_dir)
        rows = load_audit(paths)
        override_rows = [r for r in rows if r.action == "phase.override"]
        assert len(override_rows) == 1
        row = override_rows[0]
        assert row.phase == "synthesis"
        assert row.status == "success"
        assert row.details["phase"] == "synthesis"
        assert row.details["reason"] == "Reviewer misfire"
        assert row.details["actor"]  # non-empty
        assert row.details["runtime"] == "claude_code"
        # ts is present and matches phase-state.
        state = json.loads(out)
        ps_ts = state["phases"]["synthesis"]["override"]["ts"]
        assert row.details["ts"] == ps_ts

    def test_mcp_override_appends_one_phase_override_row(self, review_dir):
        result = mcp_server.phase_override(
            review_dir=str(review_dir),
            phase="synthesis",
            reason="Cowork override",
            actor="cowork-ops",
            confirm=True,
        )
        paths = resolve_review_dir(explicit=review_dir)
        rows = load_audit(paths)
        override_rows = [r for r in rows if r.action == "phase.override"]
        assert len(override_rows) == 1
        row = override_rows[0]
        assert row.phase == "synthesis"
        assert row.status == "success"
        assert row.details["phase"] == "synthesis"
        assert row.details["reason"] == "Cowork override"
        assert row.details["actor"] == "cowork-ops"
        assert row.details["runtime"] == "cowork"
        ps_ts = result["phases"]["synthesis"]["override"]["ts"]
        assert row.details["ts"] == ps_ts

    def test_two_overrides_append_two_rows_append_only(self, review_dir):
        rc1, _, err1 = _run_cli(
            ["phase", "override", "synthesis",
             "--reason", "first override", "--yes"],
            review_dir,
        )
        assert rc1 == 0, err1
        rc2, _, err2 = _run_cli(
            ["phase", "override", "synthesis",
             "--reason", "second override", "--yes"],
            review_dir,
        )
        assert rc2 == 0, err2
        paths = resolve_review_dir(explicit=review_dir)
        rows = load_audit(paths)
        override_rows = [r for r in rows if r.action == "phase.override"]
        assert len(override_rows) == 2
        reasons = [r.details["reason"] for r in override_rows]
        assert reasons == ["first override", "second override"]

    def test_phase_field_equals_overridden_phase(self, review_dir):
        rc, _, err = _run_cli(
            ["phase", "override", "extraction",
             "--reason", "skip", "--yes"],
            review_dir,
        )
        assert rc == 0, err
        paths = resolve_review_dir(explicit=review_dir)
        rows = load_audit(paths)
        override_rows = [r for r in rows if r.action == "phase.override"]
        assert override_rows[0].phase == "extraction"
        assert override_rows[0].details["phase"] == "extraction"

    def test_failed_mcp_confirm_writes_no_audit_row(self, review_dir):
        # Failed confirm path: no phase-state mutation AND no audit row.
        result = mcp_server.phase_override(
            review_dir=str(review_dir),
            phase="synthesis",
            reason="Cowork override",
            actor="cowork-ops",
            confirm=False,
        )
        assert "error" in result
        paths = resolve_review_dir(explicit=review_dir)
        assert load_audit(paths) == []


# ===========================================================================
# D. Publish blocking — enforce_v04=True
# ===========================================================================


class TestGroupD_PublishBlockingEnforced:
    @patch("scriptorium.publish.nlm")
    def test_synthesis_pending_contradiction_complete_blocks(
        self, mock_nlm, tmp_path, monkeypatch,
    ):
        monkeypatch.delenv("SCRIPTORIUM_FORCE_COWORK", raising=False)
        monkeypatch.delenv("SCRIPTORIUM_COWORK", raising=False)
        root = _make_publish_review(tmp_path)
        _write_enforce_v04(root, value=True)
        paths = resolve_review_dir(explicit=root)
        _set_contradiction_complete(paths)
        rc, out, err = _run_cli(["publish"], root)
        assert rc == EXIT_CODES["E_REVIEW_INCOMPLETE"]
        mock_nlm.doctor.assert_not_called()
        # Failure envelope is on stderr, not stdout.
        assert not out.strip()
        envelope = json.loads(err)
        assert envelope["code"] == EXIT_CODES["E_REVIEW_INCOMPLETE"]
        assert envelope["synthesis_status"] == "pending"
        assert envelope["contradiction_status"] == "complete"

    @patch("scriptorium.publish.nlm")
    def test_synthesis_complete_contradiction_running_blocks(
        self, mock_nlm, tmp_path, monkeypatch,
    ):
        monkeypatch.delenv("SCRIPTORIUM_FORCE_COWORK", raising=False)
        monkeypatch.delenv("SCRIPTORIUM_COWORK", raising=False)
        root = _make_publish_review(tmp_path)
        _write_enforce_v04(root, value=True)
        paths = resolve_review_dir(explicit=root)
        _set_synthesis_complete(paths)
        phase_state.set_phase(paths, "contradiction", "running")
        rc, out, err = _run_cli(["publish"], root)
        assert rc == EXIT_CODES["E_REVIEW_INCOMPLETE"]
        mock_nlm.doctor.assert_not_called()

    @patch("scriptorium.publish.nlm")
    def test_both_complete_proceeds(self, mock_nlm, tmp_path, monkeypatch):
        monkeypatch.delenv("SCRIPTORIUM_FORCE_COWORK", raising=False)
        monkeypatch.delenv("SCRIPTORIUM_COWORK", raising=False)
        root = _make_publish_review(tmp_path)
        _write_enforce_v04(root, value=True)
        paths = resolve_review_dir(explicit=root)
        _set_synthesis_complete(paths)
        _set_contradiction_complete(paths)
        mock_nlm.doctor.return_value = NlmResult(
            stdout="ok", stderr="", returncode=0,
        )
        mock_nlm.create_notebook.return_value = NotebookCreated(
            notebook_id="n1",
            notebook_url="https://notebooklm.google.com/notebook/n1",
            stdout="ok",
        )
        mock_nlm.upload_source.return_value = NlmResult(
            stdout="ok", stderr="", returncode=0,
        )
        rc, out, err = _run_cli(["publish", "--json"], root)
        assert rc == 0, err
        mock_nlm.doctor.assert_called_once()
        payload = json.loads(out)
        assert payload["notebook_id"] == "n1"

    @patch("scriptorium.publish.nlm")
    def test_synthesis_overridden_unblocks(
        self, mock_nlm, tmp_path, monkeypatch,
    ):
        monkeypatch.delenv("SCRIPTORIUM_FORCE_COWORK", raising=False)
        monkeypatch.delenv("SCRIPTORIUM_COWORK", raising=False)
        root = _make_publish_review(tmp_path)
        _write_enforce_v04(root, value=True)
        paths = resolve_review_dir(explicit=root)
        phase_state.override_phase(
            paths, "synthesis", reason="Reviewer misfire", actor="ops",
        )
        _set_contradiction_complete(paths)
        mock_nlm.doctor.return_value = NlmResult(
            stdout="ok", stderr="", returncode=0,
        )
        mock_nlm.create_notebook.return_value = NotebookCreated(
            notebook_id="n2", notebook_url="u", stdout="ok",
        )
        mock_nlm.upload_source.return_value = NlmResult(
            stdout="ok", stderr="", returncode=0,
        )
        rc, _, err = _run_cli(["publish", "--json"], root)
        assert rc == 0, err
        mock_nlm.doctor.assert_called_once()

    @patch("scriptorium.publish.nlm")
    def test_both_overridden_unblocks(self, mock_nlm, tmp_path, monkeypatch):
        monkeypatch.delenv("SCRIPTORIUM_FORCE_COWORK", raising=False)
        monkeypatch.delenv("SCRIPTORIUM_COWORK", raising=False)
        root = _make_publish_review(tmp_path)
        _write_enforce_v04(root, value=True)
        paths = resolve_review_dir(explicit=root)
        phase_state.override_phase(
            paths, "synthesis", reason="r1", actor="ops",
        )
        phase_state.override_phase(
            paths, "contradiction", reason="r2", actor="ops",
        )
        mock_nlm.doctor.return_value = NlmResult(
            stdout="ok", stderr="", returncode=0,
        )
        mock_nlm.create_notebook.return_value = NotebookCreated(
            notebook_id="n3", notebook_url="u", stdout="ok",
        )
        mock_nlm.upload_source.return_value = NlmResult(
            stdout="ok", stderr="", returncode=0,
        )
        rc, _, err = _run_cli(["publish", "--json"], root)
        assert rc == 0, err

    @patch("scriptorium.publish.nlm")
    def test_blocked_path_appends_publish_blocked_audit_row(
        self, mock_nlm, tmp_path, monkeypatch,
    ):
        monkeypatch.delenv("SCRIPTORIUM_FORCE_COWORK", raising=False)
        monkeypatch.delenv("SCRIPTORIUM_COWORK", raising=False)
        root = _make_publish_review(tmp_path)
        _write_enforce_v04(root, value=True)
        paths = resolve_review_dir(explicit=root)
        # Both phases pending.
        rc, _, _ = _run_cli(["publish"], root)
        assert rc == EXIT_CODES["E_REVIEW_INCOMPLETE"]
        rows = load_audit(paths)
        blocked_rows = [r for r in rows if r.action == "publish.blocked"]
        assert len(blocked_rows) == 1
        row = blocked_rows[0]
        assert row.phase == "publishing"
        assert row.status == "failure"
        assert row.details["mode"] == "blocking"
        assert row.details["synthesis_status"] == "pending"
        assert row.details["contradiction_status"] == "pending"


# ===========================================================================
# E. Publish advisory — enforce_v04=False
# ===========================================================================


class TestGroupE_PublishAdvisory:
    @patch("scriptorium.publish.nlm")
    def test_advisory_warns_and_proceeds_on_incomplete(
        self, mock_nlm, tmp_path, monkeypatch,
    ):
        monkeypatch.delenv("SCRIPTORIUM_FORCE_COWORK", raising=False)
        monkeypatch.delenv("SCRIPTORIUM_COWORK", raising=False)
        root = _make_publish_review(tmp_path)
        _write_enforce_v04(root, value=False)
        # Both phases pending — gate would block under enforce_v04=True.
        mock_nlm.doctor.return_value = NlmResult(
            stdout="ok", stderr="", returncode=0,
        )
        mock_nlm.create_notebook.return_value = NotebookCreated(
            notebook_id="n4",
            notebook_url="https://notebooklm.google.com/notebook/n4",
            stdout="ok",
        )
        mock_nlm.upload_source.return_value = NlmResult(
            stdout="ok", stderr="", returncode=0,
        )
        rc, out, err = _run_cli(["publish", "--json"], root)
        assert rc == 0, err
        # Stdout still parses as the success payload (untouched).
        payload = json.loads(out)
        assert payload["notebook_id"] == "n4"
        # Warning message hits stderr.
        assert "WARNING" in err or "advisory" in err.lower()

    @patch("scriptorium.publish.nlm")
    def test_advisory_appends_publish_advisory_audit_row(
        self, mock_nlm, tmp_path, monkeypatch,
    ):
        monkeypatch.delenv("SCRIPTORIUM_FORCE_COWORK", raising=False)
        monkeypatch.delenv("SCRIPTORIUM_COWORK", raising=False)
        root = _make_publish_review(tmp_path)
        _write_enforce_v04(root, value=False)
        mock_nlm.doctor.return_value = NlmResult(
            stdout="ok", stderr="", returncode=0,
        )
        mock_nlm.create_notebook.return_value = NotebookCreated(
            notebook_id="n5", notebook_url="u", stdout="ok",
        )
        mock_nlm.upload_source.return_value = NlmResult(
            stdout="ok", stderr="", returncode=0,
        )
        rc, _, _ = _run_cli(["publish", "--json"], root)
        assert rc == 0
        paths = resolve_review_dir(explicit=root)
        rows = load_audit(paths)
        advisory_rows = [r for r in rows if r.action == "publish.advisory"]
        assert len(advisory_rows) == 1
        row = advisory_rows[0]
        assert row.phase == "publishing"
        assert row.status == "warning"
        assert row.details["mode"] == "advisory"
        assert row.details["synthesis_status"] == "pending"
        assert row.details["contradiction_status"] == "pending"

    @patch("scriptorium.publish.nlm")
    def test_advisory_skipped_when_both_complete(
        self, mock_nlm, tmp_path, monkeypatch,
    ):
        """When the gate would pass, the advisory branch must NOT fire —
        no warning, no advisory audit row."""
        monkeypatch.delenv("SCRIPTORIUM_FORCE_COWORK", raising=False)
        monkeypatch.delenv("SCRIPTORIUM_COWORK", raising=False)
        root = _make_publish_review(tmp_path)
        _write_enforce_v04(root, value=False)
        paths = resolve_review_dir(explicit=root)
        _set_synthesis_complete(paths)
        _set_contradiction_complete(paths)
        mock_nlm.doctor.return_value = NlmResult(
            stdout="ok", stderr="", returncode=0,
        )
        mock_nlm.create_notebook.return_value = NotebookCreated(
            notebook_id="n6", notebook_url="u", stdout="ok",
        )
        mock_nlm.upload_source.return_value = NlmResult(
            stdout="ok", stderr="", returncode=0,
        )
        rc, _, err = _run_cli(["publish", "--json"], root)
        assert rc == 0, err
        rows = load_audit(paths)
        advisory_rows = [r for r in rows if r.action == "publish.advisory"]
        assert advisory_rows == []
        assert "WARNING" not in err


# ===========================================================================
# F. Cowork-mode publish bypasses the gate
# ===========================================================================


class TestGroupF_CoworkBypassesGate:
    def test_cowork_short_circuit_runs_before_gate(
        self, tmp_path, monkeypatch,
    ):
        monkeypatch.setenv("SCRIPTORIUM_FORCE_COWORK", "1")
        root = _make_publish_review(tmp_path)
        # Even with enforce_v04=True and no phase-state, Cowork short
        # circuits BEFORE the gate runs.
        _write_enforce_v04(root, value=True)
        rc, out, err = _run_cli(["publish"], root)
        assert rc == 0, err
        # The Cowork block emits the "publishing requires local shell"
        # message on stdout; the publish gate would have written its
        # error envelope on stderr instead.
        assert "Cowork" in out or "local shell" in out
        # No publish.blocked row, no publish.advisory row from the gate.
        paths = resolve_review_dir(explicit=root)
        rows = load_audit(paths)
        gate_rows = [
            r for r in rows
            if r.action in ("publish.blocked", "publish.advisory")
        ]
        assert gate_rows == []
