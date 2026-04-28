"""Layer B / T12 + T13: extraction orchestration across both runtimes.

Pins the contract for `scriptorium.extract.run_extraction` (plan §6.2):

  1. Dispatch count — exactly one dispatcher call per paper_id.
  2. Parallel cap enforced — max concurrent in-flight dispatcher calls
     never exceeds `parallel_cap` (sequential, small caps, large caps all
     covered).
  3. Contamination resistance — each per-paper prompt contains its own
     paper_id and NONE of the sibling paper_ids. Holds across all four
     runtime/backend combinations.
  4. Audit append — one `extraction.dispatch` row per paper, with the
     paper_id and runtime in `details`. Cowork rows additionally carry
     `details["backend"]`.
  5. Failure isolation — a dispatcher exception on one paper doesn't
     abort the batch; a `status="failure"` row is appended for it.
  6. Argument validation — non-positive cap, missing dispatcher, unknown
     runtime/backend, and the cowork-branch dispatch all raise the
     right symbol.
  7. SKILL.md content drift — `lit-extracting/SKILL.md` names the
     orchestration entry points, the parallel-cap config knob, all four
     runtime/backend literals, the `extraction.dispatch` audit action,
     per-paper subagent isolation, and the degraded-path `⚠` marker.

T12 owns `runtime == "claude_code"`. T13 wires the three Cowork
backends (`mcp`, `notebooklm`, `sequential`).
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import pytest

from scriptorium.errors import ScriptoriumError
from scriptorium.extract import run_extraction
from scriptorium.paths import ReviewPaths
from scriptorium.storage.audit import load_audit


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = REPO_ROOT / "skills" / "lit-extracting" / "SKILL.md"


# ---------------------------------------------------------------------------
# Test fixtures: instrumentable dispatcher + paths helper
# ---------------------------------------------------------------------------


def _make_paths(review_dir: Path) -> ReviewPaths:
    return ReviewPaths(root=review_dir)


class _RecordingDispatcher:
    """Thread-safe recorder for dispatcher invocations.

    Records (paper_id, prompt) pairs and tracks the maximum number of
    concurrent in-flight calls. The hold time forces real parallelism so
    the parallel-cap assertion isn't a no-op when callers run fast.
    """

    def __init__(self, hold_seconds: float = 0.0) -> None:
        self.calls: list[tuple[str, str]] = []
        self._lock = threading.Lock()
        self._in_flight = 0
        self.max_in_flight = 0
        self._hold = hold_seconds

    def __call__(self, paper_id: str, prompt: str) -> dict[str, Any]:
        with self._lock:
            self._in_flight += 1
            if self._in_flight > self.max_in_flight:
                self.max_in_flight = self._in_flight
            self.calls.append((paper_id, prompt))
        try:
            if self._hold > 0:
                time.sleep(self._hold)
        finally:
            with self._lock:
                self._in_flight -= 1
        return {"paper_id": paper_id, "ok": True}


# ---------------------------------------------------------------------------
# 1. Dispatch count
# ---------------------------------------------------------------------------


def test_dispatcher_called_once_per_paper(review_dir: Path) -> None:
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    paper_ids = ["W1", "W2", "W3", "W4"]
    run_extraction(
        paths,
        review_id="rev-A",
        paper_ids=paper_ids,
        runtime="claude_code",
        parallel_cap=2,
        agent_dispatcher=dispatcher,
    )
    dispatched_ids = sorted(c[0] for c in dispatcher.calls)
    assert dispatched_ids == sorted(paper_ids)
    assert len(dispatcher.calls) == len(paper_ids)


def test_empty_paper_list_dispatches_nothing(review_dir: Path) -> None:
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    result = run_extraction(
        paths,
        review_id="rev-A",
        paper_ids=[],
        runtime="claude_code",
        parallel_cap=4,
        agent_dispatcher=dispatcher,
    )
    assert dispatcher.calls == []
    # Empty input still returns a structured result (not None / not an error).
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# 2. Parallel cap enforcement
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n_papers,cap", [(10, 3), (8, 4), (6, 2)])
def test_parallel_cap_enforced(review_dir: Path, n_papers: int, cap: int) -> None:
    paths = _make_paths(review_dir)
    # Hold a short time inside each dispatch so the runtime actually has
    # the chance to pile up to (or beyond) the cap if the limit isn't enforced.
    dispatcher = _RecordingDispatcher(hold_seconds=0.05)
    paper_ids = [f"W{i}" for i in range(n_papers)]
    run_extraction(
        paths,
        review_id="rev-cap",
        paper_ids=paper_ids,
        runtime="claude_code",
        parallel_cap=cap,
        agent_dispatcher=dispatcher,
    )
    assert dispatcher.max_in_flight <= cap, (
        f"max concurrent dispatcher calls {dispatcher.max_in_flight} "
        f"exceeded parallel_cap {cap}"
    )
    assert dispatcher.max_in_flight >= 2, (
        f"with cap={cap} and {n_papers} papers, expected at least 2 concurrent "
        f"calls; observed {dispatcher.max_in_flight}. Either parallelism is "
        f"broken or the 50ms hold is too short for this CI box."
    )


def test_parallel_cap_one_runs_sequentially(review_dir: Path) -> None:
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher(hold_seconds=0.01)
    paper_ids = [f"W{i}" for i in range(5)]
    run_extraction(
        paths,
        review_id="rev-seq",
        paper_ids=paper_ids,
        runtime="claude_code",
        parallel_cap=1,
        agent_dispatcher=dispatcher,
    )
    assert dispatcher.max_in_flight == 1, (
        "parallel_cap=1 must be strictly sequential (max_in_flight==1); "
        f"observed {dispatcher.max_in_flight}"
    )


@pytest.mark.parametrize("bad_cap", [0, -1, -100])
def test_non_positive_parallel_cap_raises(
    review_dir: Path, bad_cap: int
) -> None:
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    with pytest.raises(ScriptoriumError) as excinfo:
        run_extraction(
            paths,
            review_id="rev-bad-cap",
            paper_ids=["W1"],
            runtime="claude_code",
            parallel_cap=bad_cap,
            agent_dispatcher=dispatcher,
        )
    assert excinfo.value.symbol == "E_EXTRACT_BAD_CAP"


@pytest.mark.parametrize("bad_cap", [True, False])
def test_bool_parallel_cap_rejected(review_dir: Path, bad_cap: bool) -> None:
    """`bool` is a subclass of `int` in Python — without explicit rejection,
    parallel_cap=True silently means cap=1. Pin that bools are rejected."""
    paths = _make_paths(review_dir)
    with pytest.raises(ScriptoriumError) as excinfo:
        run_extraction(
            paths,
            review_id="rev",
            paper_ids=["W1"],
            runtime="claude_code",
            parallel_cap=bad_cap,  # type: ignore[arg-type]
            agent_dispatcher=lambda pid, prompt: {"ok": True},
        )
    assert excinfo.value.symbol == "E_EXTRACT_BAD_CAP"


# ---------------------------------------------------------------------------
# 3. Contamination resistance — each prompt is isolated
# ---------------------------------------------------------------------------


def test_each_prompt_contains_only_its_paper_id(review_dir: Path) -> None:
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    paper_ids = ["W123", "W456", "W789", "W321"]
    run_extraction(
        paths,
        review_id="rev-iso",
        paper_ids=paper_ids,
        runtime="claude_code",
        parallel_cap=2,
        agent_dispatcher=dispatcher,
    )
    for target_id, prompt in dispatcher.calls:
        # The target id must be in its own prompt.
        assert target_id in prompt, (
            f"dispatcher prompt for {target_id!r} does not contain its "
            "own paper_id"
        )
        # No sibling paper_id may leak into the prompt.
        siblings = [pid for pid in paper_ids if pid != target_id]
        leaks = [pid for pid in siblings if pid in prompt]
        assert not leaks, (
            f"contamination: prompt for {target_id!r} contains sibling "
            f"paper_ids {leaks!r}"
        )


def test_paper_ids_with_overlapping_substrings_do_not_false_positive(
    review_dir: Path,
) -> None:
    """If `W12` and `W123` are both in the batch, the prompt for `W12`
    must still not name `W123`. The implementation should build per-paper
    prompts from a single-id template, not by concatenating the list.
    """
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    paper_ids = ["W12", "W123", "W1234"]
    run_extraction(
        paths,
        review_id="rev-overlap",
        paper_ids=paper_ids,
        runtime="claude_code",
        parallel_cap=1,
        agent_dispatcher=dispatcher,
    )
    by_id = {pid: prompt for pid, prompt in dispatcher.calls}
    # The shorter id W12 lives inside W123/W1234 strings, but the prompt
    # for W12 must not literally contain "W123" or "W1234" — i.e. the
    # implementation does not expose the full list to per-paper prompts.
    assert "W123" not in by_id["W12"]
    assert "W1234" not in by_id["W12"]
    # And the W123 prompt must not name W1234.
    assert "W1234" not in by_id["W123"]


# ---------------------------------------------------------------------------
# 4. Audit append — one row per paper, right shape
# ---------------------------------------------------------------------------


def test_one_audit_row_per_paper(review_dir: Path) -> None:
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    paper_ids = ["W1", "W2", "W3"]
    run_extraction(
        paths,
        review_id="rev-aud",
        paper_ids=paper_ids,
        runtime="claude_code",
        parallel_cap=2,
        agent_dispatcher=dispatcher,
    )
    rows = load_audit(paths)
    assert len(rows) == len(paper_ids), (
        f"expected {len(paper_ids)} audit rows, got {len(rows)}"
    )
    for row in rows:
        assert row.phase == "extraction"
        assert row.action == "extraction.dispatch"
        assert row.status == "success"
        assert row.details["runtime"] == "claude_code"
        assert row.details["review_id"] == "rev-aud"
        assert row.details["paper_id"] in paper_ids
    audited_ids = sorted(r.details["paper_id"] for r in rows)
    assert audited_ids == sorted(paper_ids)


# ---------------------------------------------------------------------------
# 5. Failure isolation
# ---------------------------------------------------------------------------


def test_dispatcher_failure_on_one_paper_does_not_abort_batch(
    review_dir: Path,
) -> None:
    paths = _make_paths(review_dir)
    failing_id = "W2"

    def dispatcher(paper_id: str, prompt: str) -> dict[str, Any]:
        if paper_id == failing_id:
            raise RuntimeError("simulated dispatcher failure")
        return {"paper_id": paper_id, "ok": True}

    paper_ids = ["W1", "W2", "W3"]
    result = run_extraction(
        paths,
        review_id="rev-fail",
        paper_ids=paper_ids,
        runtime="claude_code",
        parallel_cap=2,
        agent_dispatcher=dispatcher,
    )
    rows = load_audit(paths)
    assert len(rows) == len(paper_ids), (
        "even on partial failure, every paper must produce an audit row"
    )
    by_paper = {r.details["paper_id"]: r for r in rows}
    assert by_paper[failing_id].status == "failure"
    assert "error" in by_paper[failing_id].details
    for ok_id in ("W1", "W3"):
        assert by_paper[ok_id].status == "success"
    # The return dict surfaces the failure to the caller — discipline:
    # we don't pretend the batch was clean.
    assert isinstance(result, dict)
    failures = result.get("failures") or {}
    assert failing_id in failures
    successes = result.get("successes") or {}
    assert "W1" in successes and "W3" in successes


# ---------------------------------------------------------------------------
# 6. Argument validation — dispatcher / runtime / cowork branch
# ---------------------------------------------------------------------------


def test_missing_dispatcher_for_claude_code_raises(review_dir: Path) -> None:
    paths = _make_paths(review_dir)
    with pytest.raises(ScriptoriumError) as excinfo:
        run_extraction(
            paths,
            review_id="rev-no-disp",
            paper_ids=["W1"],
            runtime="claude_code",
            parallel_cap=2,
            agent_dispatcher=None,
        )
    assert excinfo.value.symbol == "E_EXTRACT_NO_DISPATCHER"


def test_non_callable_dispatcher_for_claude_code_raises(review_dir: Path) -> None:
    """A non-None but non-callable dispatcher must raise the same symbol as
    `None`. Pins the second `E_EXTRACT_NO_DISPATCHER` raise path."""
    paths = _make_paths(review_dir)
    with pytest.raises(ScriptoriumError) as excinfo:
        run_extraction(
            paths,
            review_id="rev",
            paper_ids=["W1"],
            runtime="claude_code",
            parallel_cap=1,
            agent_dispatcher="not_a_callable",  # type: ignore[arg-type]
        )
    assert excinfo.value.symbol == "E_EXTRACT_NO_DISPATCHER"


def test_unknown_runtime_raises(review_dir: Path) -> None:
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    with pytest.raises(ScriptoriumError) as excinfo:
        run_extraction(
            paths,
            review_id="rev-bad-rt",
            paper_ids=["W1"],
            runtime="some_other_runtime",
            parallel_cap=2,
            agent_dispatcher=dispatcher,
        )
    assert excinfo.value.symbol == "E_EXTRACT_UNKNOWN_RUNTIME"


# ---------------------------------------------------------------------------
# T13: Cowork backend dispatch — argument validation
# ---------------------------------------------------------------------------


def test_cowork_runtime_without_backend_raises(review_dir: Path) -> None:
    """`runtime='cowork'` without a `cowork_backend` must raise
    `E_EXTRACT_NO_BACKEND` — the using-scriptorium runtime probe is
    expected to set this. Silent success would let an orchestrator
    bypass the audit-row backend field."""
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    with pytest.raises(ScriptoriumError) as excinfo:
        run_extraction(
            paths,
            review_id="rev-cw",
            paper_ids=["W1"],
            runtime="cowork",
            parallel_cap=1,
            agent_dispatcher=dispatcher,
        )
    assert excinfo.value.symbol == "E_EXTRACT_NO_BACKEND"


def test_cowork_runtime_with_unknown_backend_raises(review_dir: Path) -> None:
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    with pytest.raises(ScriptoriumError) as excinfo:
        run_extraction(
            paths,
            review_id="rev-cw",
            paper_ids=["W1"],
            runtime="cowork",
            parallel_cap=1,
            agent_dispatcher=dispatcher,
            cowork_backend="bogus",
        )
    assert excinfo.value.symbol == "E_EXTRACT_UNKNOWN_BACKEND"


def test_claude_code_with_cowork_backend_raises(review_dir: Path) -> None:
    """`cowork_backend` is meaningless on the CC branch. Reject it
    explicitly so a misconfigured caller can't silently produce a
    'claude_code' audit row that should have been a Cowork row."""
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    with pytest.raises(ScriptoriumError) as excinfo:
        run_extraction(
            paths,
            review_id="rev",
            paper_ids=["W1"],
            runtime="claude_code",
            parallel_cap=1,
            agent_dispatcher=dispatcher,
            cowork_backend="mcp",
        )
    assert excinfo.value.symbol == "E_EXTRACT_UNKNOWN_BACKEND"


@pytest.mark.parametrize("backend", ["mcp", "notebooklm", "sequential"])
def test_cowork_missing_dispatcher_raises(
    review_dir: Path, backend: str
) -> None:
    """All three Cowork backends require a dispatcher; none must
    silently succeed without one."""
    paths = _make_paths(review_dir)
    with pytest.raises(ScriptoriumError) as excinfo:
        run_extraction(
            paths,
            review_id="rev",
            paper_ids=["W1"],
            runtime="cowork",
            parallel_cap=1,
            agent_dispatcher=None,
            cowork_backend=backend,
        )
    assert excinfo.value.symbol == "E_EXTRACT_NO_DISPATCHER"


# ---------------------------------------------------------------------------
# T13: Cowork backend dispatch — happy paths (mcp / notebooklm / sequential)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("backend", ["mcp", "notebooklm", "sequential"])
def test_cowork_dispatcher_called_once_per_paper(
    review_dir: Path, backend: str
) -> None:
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    paper_ids = ["W1", "W2", "W3"]
    run_extraction(
        paths,
        review_id="rev-cw",
        paper_ids=paper_ids,
        runtime="cowork",
        parallel_cap=2,
        agent_dispatcher=dispatcher,
        cowork_backend=backend,
    )
    dispatched = sorted(c[0] for c in dispatcher.calls)
    assert dispatched == sorted(paper_ids)
    assert len(dispatcher.calls) == len(paper_ids)


@pytest.mark.parametrize("backend", ["mcp", "notebooklm", "sequential"])
def test_cowork_audit_row_carries_runtime_and_backend(
    review_dir: Path, backend: str
) -> None:
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    paper_ids = ["W1", "W2"]
    run_extraction(
        paths,
        review_id="rev-cw-aud",
        paper_ids=paper_ids,
        runtime="cowork",
        parallel_cap=2,
        agent_dispatcher=dispatcher,
        cowork_backend=backend,
    )
    rows = load_audit(paths)
    assert len(rows) == len(paper_ids)
    for row in rows:
        assert row.phase == "extraction"
        assert row.action == "extraction.dispatch"
        assert row.status == "success"
        assert row.details["runtime"] == "cowork"
        assert row.details["backend"] == backend
        assert row.details["review_id"] == "rev-cw-aud"
        assert row.details["paper_id"] in paper_ids


@pytest.mark.parametrize("backend", ["mcp", "notebooklm", "sequential"])
def test_cowork_return_dict_carries_runtime_and_backend(
    review_dir: Path, backend: str
) -> None:
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    result = run_extraction(
        paths,
        review_id="rev-cw-ret",
        paper_ids=["W1"],
        runtime="cowork",
        parallel_cap=1,
        agent_dispatcher=dispatcher,
        cowork_backend=backend,
    )
    assert result["runtime"] == "cowork"
    assert result["backend"] == backend
    assert result["review_id"] == "rev-cw-ret"


# ---------------------------------------------------------------------------
# T13: parallel_cap discipline across the three backends
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("backend", ["mcp", "notebooklm"])
def test_cowork_isolated_backends_honor_parallel_cap(
    review_dir: Path, backend: str
) -> None:
    """`mcp` and `notebooklm` are HIGH-isolation backends — bounded
    parallel fan-out is fine and `parallel_cap` is the live ceiling.
    Same property as T12's CC branch."""
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher(hold_seconds=0.05)
    paper_ids = [f"W{i}" for i in range(8)]
    cap = 3
    run_extraction(
        paths,
        review_id="rev-cw-cap",
        paper_ids=paper_ids,
        runtime="cowork",
        parallel_cap=cap,
        agent_dispatcher=dispatcher,
        cowork_backend=backend,
    )
    assert dispatcher.max_in_flight <= cap, (
        f"backend {backend!r} let max_in_flight={dispatcher.max_in_flight} "
        f"exceed parallel_cap={cap}"
    )
    assert dispatcher.max_in_flight >= 2, (
        f"backend {backend!r}: with 8 papers and cap=3 we expected "
        f"observable parallelism; observed max_in_flight="
        f"{dispatcher.max_in_flight}. If this trips on a slow CI box, "
        "raise the dispatcher hold time, not the cap."
    )


def test_cowork_sequential_is_serial_even_with_high_parallel_cap(
    review_dir: Path,
) -> None:
    """The honest-gap discipline: sequential MUST run strictly serial
    even when the caller passes a higher cap. This is the runtime
    backing the SKILL.md `⚠ sequential` marker."""
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher(hold_seconds=0.02)
    paper_ids = [f"W{i}" for i in range(6)]
    run_extraction(
        paths,
        review_id="rev-cw-seq",
        paper_ids=paper_ids,
        runtime="cowork",
        parallel_cap=8,  # try to encourage parallelism — must NOT happen
        agent_dispatcher=dispatcher,
        cowork_backend="sequential",
    )
    assert dispatcher.max_in_flight == 1, (
        "cowork:sequential must run strictly serially (max_in_flight==1) "
        f"even with parallel_cap=8; observed {dispatcher.max_in_flight}"
    )


# ---------------------------------------------------------------------------
# T13: contamination resistance across all three Cowork backends
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("backend", ["mcp", "notebooklm", "sequential"])
def test_cowork_each_prompt_contains_only_its_paper_id(
    review_dir: Path, backend: str
) -> None:
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    paper_ids = ["W123", "W456", "W789", "W321"]
    run_extraction(
        paths,
        review_id="rev-cw-iso",
        paper_ids=paper_ids,
        runtime="cowork",
        parallel_cap=2,
        agent_dispatcher=dispatcher,
        cowork_backend=backend,
    )
    for target_id, prompt in dispatcher.calls:
        assert target_id in prompt, (
            f"backend={backend!r}: dispatcher prompt for {target_id!r} "
            "does not contain its own paper_id"
        )
        siblings = [pid for pid in paper_ids if pid != target_id]
        leaks = [pid for pid in siblings if pid in prompt]
        assert not leaks, (
            f"backend={backend!r}: prompt for {target_id!r} contains "
            f"sibling paper_ids {leaks!r}"
        )


# ---------------------------------------------------------------------------
# T13: failure isolation across all three Cowork backends
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("backend", ["mcp", "notebooklm", "sequential"])
def test_cowork_dispatcher_failure_does_not_abort_batch(
    review_dir: Path, backend: str
) -> None:
    paths = _make_paths(review_dir)
    failing_id = "W2"

    def dispatcher(paper_id: str, prompt: str) -> dict[str, Any]:
        if paper_id == failing_id:
            raise RuntimeError(f"simulated {backend} failure")
        return {"paper_id": paper_id, "ok": True}

    paper_ids = ["W1", "W2", "W3"]
    result = run_extraction(
        paths,
        review_id="rev-cw-fail",
        paper_ids=paper_ids,
        runtime="cowork",
        parallel_cap=2,
        agent_dispatcher=dispatcher,
        cowork_backend=backend,
    )
    rows = load_audit(paths)
    assert len(rows) == len(paper_ids), (
        f"backend={backend!r}: even on partial failure, every paper "
        "must produce an audit row"
    )
    by_paper = {r.details["paper_id"]: r for r in rows}
    assert by_paper[failing_id].status == "failure"
    assert by_paper[failing_id].details["backend"] == backend
    assert "error" in by_paper[failing_id].details
    for ok_id in ("W1", "W3"):
        assert by_paper[ok_id].status == "success"
        assert by_paper[ok_id].details["backend"] == backend
    assert failing_id in (result.get("failures") or {})
    assert "W1" in (result.get("successes") or {})
    assert "W3" in (result.get("successes") or {})


# ---------------------------------------------------------------------------
# T13: sequential prompt carries the context-clear marker
# ---------------------------------------------------------------------------


def test_cowork_sequential_prompt_carries_context_clear_marker(
    review_dir: Path,
) -> None:
    """The sequential backend's prompt must carry a context-clear
    marker so the orchestrator knows to inject the cleanup between
    papers. The other Cowork backends (mcp, notebooklm) keep the
    byte-identical T12 prompt because their isolation comes from
    per-paper context, not prompt discipline."""
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    run_extraction(
        paths,
        review_id="rev-cw-seq-prompt",
        paper_ids=["W1"],
        runtime="cowork",
        parallel_cap=1,
        agent_dispatcher=dispatcher,
        cowork_backend="sequential",
    )
    _, prompt = dispatcher.calls[0]
    assert "cowork:sequential" in prompt
    assert "context-clear" in prompt


@pytest.mark.parametrize("backend", ["mcp", "notebooklm"])
def test_cowork_isolated_backends_use_t12_base_prompt(
    review_dir: Path, backend: str
) -> None:
    """`mcp` and `notebooklm` reuse the byte-identical T12 prompt — no
    sequential addendum, no backend-specific phrasing. Per-paper
    isolation comes from the orchestrator's per-paper context, not
    from extra prompt discipline."""
    paths = _make_paths(review_dir)
    dispatcher = _RecordingDispatcher()
    run_extraction(
        paths,
        review_id="rev",
        paper_ids=["W1"],
        runtime="cowork",
        parallel_cap=1,
        agent_dispatcher=dispatcher,
        cowork_backend=backend,
    )
    _, prompt = dispatcher.calls[0]
    assert "cowork:sequential" not in prompt
    assert "context-clear" not in prompt


# ---------------------------------------------------------------------------
# 7. SKILL.md content pins — orchestration is documented
# ---------------------------------------------------------------------------

# These five tokens lock the orchestration paragraph in lit-extracting/
# SKILL.md against drift. Adding or renaming any one of them is a deliberate
# choice and should be made in the same commit that updates these tests.

T12_SKILL_REQUIRED_TOKENS = (
    "run_extraction",          # the orchestration entry point
    "extraction_parallel_cap", # the config knob
    "claude_code",             # the runtime literal
    "extraction.dispatch",     # the audit action
)


@pytest.mark.parametrize("token", T12_SKILL_REQUIRED_TOKENS)
def test_skill_names_orchestration_token(token: str) -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert token in text, (
        f"lit-extracting/SKILL.md must name the T12 orchestration token "
        f"{token!r}"
    )


def test_skill_states_per_paper_isolation() -> None:
    """T12 brief: 'each paper gets its own subagent / isolated context.'"""
    text = SKILL_PATH.read_text(encoding="utf-8").lower()
    has_subagent = "subagent" in text
    has_isolation = "isolat" in text or "per-paper" in text
    assert has_subagent and has_isolation, (
        "lit-extracting/SKILL.md must state that each paper gets its own "
        "subagent / isolated context (look for 'subagent' AND 'isolat' or "
        "'per-paper')"
    )


# ---------------------------------------------------------------------------
# T13 SKILL.md content pins — Cowork orchestration is documented
# ---------------------------------------------------------------------------

# These five tokens lock the Cowork-orchestration paragraph in
# lit-extracting/SKILL.md against drift. The three backend literals
# must match the COWORK_BACKENDS tuple in scriptorium.cowork.

T13_SKILL_REQUIRED_TOKENS = (
    "mcp",                              # backend literal
    "notebooklm",                       # backend literal
    "sequential",                       # backend literal
    "mcp__scriptorium__extract_paper",  # the Cowork:mcp tool name
    'backend="mcp"',                    # audit-row backend field shape
)


@pytest.mark.parametrize("token", T13_SKILL_REQUIRED_TOKENS)
def test_skill_names_cowork_orchestration_token(token: str) -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert token in text, (
        f"lit-extracting/SKILL.md must name the T13 Cowork-orchestration "
        f"token {token!r}"
    )


def test_skill_marks_sequential_as_degraded() -> None:
    """T10 / T13 runtime-honesty convention: the `sequential` backend
    must be flagged with the `⚠` marker (the canonical degraded-mode
    sigil borrowed from the T10 red-flag tables)."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert "sequential" in text, "SKILL.md must name the `sequential` backend"
    # Scan EVERY occurrence of `sequential`; at least one must sit
    # within a few lines of the `⚠` marker. A global ⚠ elsewhere in
    # the file isn't enough — but any mention of sequential paired with
    # ⚠ in its neighborhood proves the asymmetry is legible.
    found_pair = False
    start = 0
    while True:
        idx = text.find("sequential", start)
        if idx == -1:
            break
        window = text[max(0, idx - 200) : idx + 200]
        if "⚠" in window:
            found_pair = True
            break
        start = idx + len("sequential")
    assert found_pair, (
        "SKILL.md must mark `sequential` as degraded with the ⚠ marker "
        "(canonical T10 runtime-honesty convention) — neither of the "
        "neighborhoods around `sequential` carried ⚠"
    )


def test_skill_names_isolation_backend_probe() -> None:
    """The Cowork orchestration section must say HOW the orchestrator
    decides which backend to use — i.e. via the using-scriptorium
    runtime probe / ISOLATION_BACKEND."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    has_probe = (
        "ISOLATION_BACKEND" in text
        or "runtime probe" in text.lower()
        or "using-scriptorium" in text
    )
    assert has_probe, (
        "lit-extracting/SKILL.md must say the orchestrator picks the "
        "Cowork backend via the using-scriptorium runtime probe / "
        "ISOLATION_BACKEND"
    )


def test_skill_preserves_t12_cc_orchestration_paragraph() -> None:
    """T13 is additive on the orchestration section. The T12 paragraph
    naming `run_extraction(...)` with `runtime="claude_code"` must
    remain byte-identical."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    # These three substrings together pin the T12 paragraph's spine.
    t12_spine = (
        'runtime="claude_code"',
        "extraction_parallel_cap",
        "extraction.dispatch",
    )
    for token in t12_spine:
        assert token in text, (
            f"T13 must preserve T12 CC orchestration paragraph — missing {token!r}"
        )


def test_skill_preserves_t08_defensive_fallback_byte_identical() -> None:
    """T13 must not perturb the T08 defensive-fallback line."""
    from tests.test_layer_a_hard_gates import DEFENSIVE_FALLBACK_LINE
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert DEFENSIVE_FALLBACK_LINE in text, (
        "T13 broke the T08 byte-identical defensive fallback line"
    )


def test_skill_preserves_t09_hard_gate_block() -> None:
    """T13 must not perturb the T09 HARD-GATE block."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert "HARD-GATE" in text
    assert "screening.status" in text
    assert "corpus.jsonl" in text


def test_skill_preserves_t10_red_flag_section() -> None:
    """T13 must not perturb the T10 `## Red flags — do NOT` section."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert "## Red flags — do NOT" in text


def test_skill_preserves_v03_additions_block() -> None:
    """T13 must not perturb the trailing `## v0.3 additions` block."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert "## v0.3 additions" in text


# ---------------------------------------------------------------------------
# T13 smoke-doc content pins
# ---------------------------------------------------------------------------

SMOKE_DOC_PATH = REPO_ROOT / "docs" / "cowork-smoke.md"


def test_smoke_doc_names_three_backend_literals() -> None:
    text = SMOKE_DOC_PATH.read_text(encoding="utf-8")
    for backend in ("mcp", "notebooklm", "sequential"):
        # Substring presence is the right test — the smoke doc may
        # render these as table-cell text, code spans, or prose.
        assert backend in text, (
            f"docs/cowork-smoke.md must name the {backend!r} backend"
        )


def test_smoke_doc_has_extraction_backend_section() -> None:
    text = SMOKE_DOC_PATH.read_text(encoding="utf-8")
    # The T13 brief calls for a section header; allow a tolerant match
    # on either of the two natural phrasings.
    has_section = (
        "Extraction backend matrix" in text
        or "extraction backend matrix" in text.lower()
    )
    assert has_section, (
        "docs/cowork-smoke.md must add an `Extraction backend matrix` "
        "section listing the three Cowork extraction backends"
    )


def test_smoke_doc_marks_sequential_as_degraded() -> None:
    text = SMOKE_DOC_PATH.read_text(encoding="utf-8")
    seq_idx = text.find("sequential")
    assert seq_idx != -1
    window = text[max(0, seq_idx - 400) : seq_idx + 400]
    assert "⚠" in window or "degraded" in window.lower(), (
        "docs/cowork-smoke.md must mark `sequential` as degraded "
        "(⚠ marker or 'degraded' label nearby)"
    )


def test_smoke_doc_preserves_existing_connector_matrix() -> None:
    """The T13 additions are additive; the existing connector matrix
    must remain in place."""
    text = SMOKE_DOC_PATH.read_text(encoding="utf-8")
    assert "## Connector matrix" in text
    # Pin a few rows from the connector matrix so a careless rewrite
    # of cowork-smoke.md trips this test.
    for row_marker in (
        "Consensus only",
        "PubMed only",
        "Scholar Gateway only",
        "NotebookLM only",
    ):
        assert row_marker in text, (
            f"smoke doc lost connector-matrix row {row_marker!r}"
        )
