"""Layer B / T12: Claude Code extraction orchestration.

Pins the contract for `scriptorium.extract.run_extraction` (plan §6.2):

  1. Dispatch count — exactly one dispatcher call per paper_id.
  2. Parallel cap enforced — max concurrent in-flight dispatcher calls
     never exceeds `parallel_cap` (sequential, small caps, large caps all
     covered).
  3. Contamination resistance — each per-paper prompt contains its own
     paper_id and NONE of the sibling paper_ids.
  4. Audit append — one `extraction.dispatch` row per paper, with the
     paper_id and runtime in `details`.
  5. Failure isolation — a dispatcher exception on one paper doesn't
     abort the batch; a `status="failure"` row is appended for it.
  6. Argument validation — non-positive cap, missing dispatcher, unknown
     runtime, and the cowork branch (T13) all raise the right symbol.
  7. SKILL.md content drift — `lit-extracting/SKILL.md` names the
     orchestration entry point, the parallel-cap config knob, the
     `claude_code` runtime literal, the `extraction.dispatch` audit
     action, and per-paper subagent isolation.

T13 will add the cowork branches; T12 only owns `runtime == "claude_code"`.
The cowork-branch test here pins that T13 starts from a failing test.
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


def test_cowork_runtime_is_t13_not_t12(review_dir: Path) -> None:
    """T12 owns only the Claude Code branch. T13 will replace this
    NotImplementedError with the cowork backend dispatch — at which point
    this test should be edited (or extended in T13's own test file)."""
    paths = _make_paths(review_dir)
    with pytest.raises(NotImplementedError) as excinfo:
        run_extraction(
            paths,
            review_id="rev-cw",
            paper_ids=["W1"],
            runtime="cowork",
            parallel_cap=1,
            agent_dispatcher=None,
        )
    # Pin the message so T13 sees a deliberate boundary, not a typo.
    assert "T13" in str(excinfo.value)


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
