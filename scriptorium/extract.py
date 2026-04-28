"""Extraction orchestration (plan §6.2).

T12 implements the Claude Code branch: parallel agent dispatch under a
configured cap, with each paper handled in an isolated per-paper prompt.
T13 adds the Cowork branches (``mcp``, ``notebooklm``, ``sequential``);
each calls the same callable contract ``(paper_id, prompt) -> dict`` so
the orchestrator can wire it to the right MCP/NotebookLM tool stack in
its session, while audit-row hygiene and contamination resistance
remain identical to T12.

Discipline (the v0.4 plan's three rails):

  1. Evidence-first: each paper gets its own dispatcher call with a
     prompt that names ONLY that paper_id. Sibling-paper context never
     bleeds across calls — the per-paper subagent runs in an isolated
     turn so it can't accidentally cite or paraphrase from a sibling.
     This property holds across all four runtime/backend combinations
     (claude_code, cowork:mcp, cowork:notebooklm, cowork:sequential).
  2. PRISMA audit trail: each dispatch appends one
     ``extraction.dispatch`` row, with ``status="success"`` or
     ``status="failure"`` plus the error string when the dispatcher
     raises. No silent skips. Cowork rows additionally carry
     ``details["backend"]`` so the runtime gap is auditable.
  3. Failure isolation: one paper's failure does not abort the batch.
     The return dict carries both ``successes`` and ``failures`` so the
     caller can decide whether the run was acceptable.

Honest-gap note (T10 runtime-honesty convention): the ``sequential``
backend is the degraded path. Even when ``parallel_cap > 1`` is
configured, sequential extraction runs strictly serially — the
orchestrator emits a context-clear prompt between papers and isolation
is prompt-discipline only. The audit row's ``details["backend"]`` plus
the SKILL.md ``⚠`` marker keep the asymmetry legible to reviewers.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from scriptorium.cowork import COWORK_BACKENDS, is_valid_backend
from scriptorium.errors import ScriptoriumError
from scriptorium.paths import ReviewPaths
from scriptorium.storage.audit import AuditEntry, append_audit


# Per-paper prompt template. Single-id only — never expose the full
# paper list, or sibling context can contaminate the subagent's
# reasoning. Phase-specific instructions live in the lit-extracting
# SKILL.md the subagent loads; this prompt names the target and hands
# off to that skill.
_PER_PAPER_PROMPT_TEMPLATE = (
    "Extract evidence for paper_id={paper_id} from review_id={review_id}.\n"
    "Fire the `lit-extracting` skill and follow its per-paper workflow.\n"
    "Process ONLY this single paper_id. Do not look up, name, or otherwise\n"
    "reference any other paper_id during this turn — sibling-paper context\n"
    "is reserved for the orchestrator, not for this subagent."
)

# Sequential-backend addendum: the orchestrator runs all papers in a
# single chat thread, so a context-clear marker between papers is the
# only isolation we have. Tag the prompt so the orchestrator (and any
# observer reading the dispatched prompt) can find it.
_SEQUENTIAL_PROMPT_SUFFIX = (
    "\n[cowork:sequential] Emit a context-clear prompt between papers — "
    "this paper's extraction must not carry over into the next paper's "
    "turn. Isolation here is prompt-discipline only (degraded)."
)


def _build_prompt(
    *,
    paper_id: str,
    review_id: str,
    runtime: str = "claude_code",
    backend: str | None = None,
) -> str:
    """Build a per-paper prompt that names ONLY this paper.

    The template is parameterized on paper_id and review_id alone — the
    caller's full paper_ids list never reaches per-paper prompts. That's
    the contamination-resistance property the T12 acceptance pins (and
    T13 extends to all three Cowork backends).

    When ``runtime == "cowork"`` and ``backend == "sequential"`` the
    prompt grows a small addendum reminding the orchestrator that
    isolation is prompt-discipline only. The base template is unchanged
    in every other branch — claude_code, cowork:mcp, and
    cowork:notebooklm all build the byte-identical T12 prompt.
    """
    base = _PER_PAPER_PROMPT_TEMPLATE.format(
        paper_id=paper_id, review_id=review_id
    )
    if runtime == "cowork" and backend == "sequential":
        return base + _SEQUENTIAL_PROMPT_SUFFIX
    return base


# Public alias: the MCP server reuses the same template so per-paper
# prompts have one source of truth. Don't duplicate the template literal
# elsewhere — call this.
build_per_paper_prompt = _build_prompt


__all__ = [
    "build_per_paper_prompt",
    "run_extraction",
]


def _audit_details(
    *,
    paper_id: str,
    review_id: str,
    runtime: str,
    backend: str | None,
) -> dict[str, Any]:
    """Build the ``details`` payload for an extraction.dispatch row.

    The Claude Code branch (T12) uses no ``backend`` field. Cowork
    branches (T13) carry ``details["backend"]`` set to one of the three
    canonical literals so the runtime gap is auditable.
    """
    details: dict[str, Any] = {
        "paper_id": paper_id,
        "review_id": review_id,
        "runtime": runtime,
    }
    if backend is not None:
        details["backend"] = backend
    return details


def _dispatch_one(
    *,
    paths: ReviewPaths,
    review_id: str,
    paper_id: str,
    runtime: str,
    backend: str | None = None,
    dispatcher: Callable[[str, str], dict[str, Any]],
) -> tuple[str, dict[str, Any] | Exception]:
    """Run one dispatcher call and append its audit row.

    Returns ``(paper_id, dispatcher_result_or_exception)``. Exceptions
    are returned, not re-raised — the caller aggregates per-paper
    success/failure into the return dict so a single failure can't
    abort the batch.
    """
    prompt = _build_prompt(
        paper_id=paper_id,
        review_id=review_id,
        runtime=runtime,
        backend=backend,
    )
    try:
        result = dispatcher(paper_id, prompt)
    except Exception as exc:  # noqa: BLE001 — the failure is audited
        details = _audit_details(
            paper_id=paper_id,
            review_id=review_id,
            runtime=runtime,
            backend=backend,
        )
        details["error"] = f"{type(exc).__name__}: {exc}"
        append_audit(
            paths,
            AuditEntry(
                phase="extraction",
                action="extraction.dispatch",
                status="failure",
                details=details,
            ),
        )
        return paper_id, exc
    append_audit(
        paths,
        AuditEntry(
            phase="extraction",
            action="extraction.dispatch",
            status="success",
            details=_audit_details(
                paper_id=paper_id,
                review_id=review_id,
                runtime=runtime,
                backend=backend,
            ),
        ),
    )
    return paper_id, result


def _run_pool(
    *,
    paths: ReviewPaths,
    review_id: str,
    paper_ids: list[str],
    parallel_cap: int,
    runtime: str,
    backend: str | None,
    dispatcher: Callable[[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Bounded-parallel fan-out shared by claude_code and cowork:mcp /
    cowork:notebooklm. ``parallel_cap`` is the in-flight ceiling.

    The cowork:sequential branch does NOT use this helper — even with
    parallel_cap > 1, sequential must run strictly serially.
    """
    successes: dict[str, dict[str, Any]] = {}
    failures: dict[str, str] = {}
    if not paper_ids:
        return {"successes": successes, "failures": failures}

    # ThreadPoolExecutor with max_workers=parallel_cap is the canonical
    # bounded fan-out pattern. parallel_cap=1 is strictly sequential
    # (one worker thread). The pool is reused across paper_ids so
    # in-flight count tops out at parallel_cap.
    with ThreadPoolExecutor(max_workers=parallel_cap) as pool:
        futures = [
            pool.submit(
                _dispatch_one,
                paths=paths,
                review_id=review_id,
                paper_id=pid,
                runtime=runtime,
                backend=backend,
                dispatcher=dispatcher,
            )
            for pid in paper_ids
        ]
        for fut in as_completed(futures):
            paper_id, outcome = fut.result()
            if isinstance(outcome, Exception):
                failures[paper_id] = f"{type(outcome).__name__}: {outcome}"
            else:
                successes[paper_id] = outcome
    return {"successes": successes, "failures": failures}


def _run_serial(
    *,
    paths: ReviewPaths,
    review_id: str,
    paper_ids: list[str],
    runtime: str,
    backend: str | None,
    dispatcher: Callable[[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Strictly-serial dispatch loop for cowork:sequential.

    No executor — even one with ``max_workers=1`` would let a future
    refactor accidentally bump the cap. The discipline-honest behavior
    here is: process exactly one paper at a time, in the order the
    caller provided. Failure isolation is preserved (one paper's
    exception does not abort the loop) — the failure is recorded, then
    we move on.
    """
    successes: dict[str, dict[str, Any]] = {}
    failures: dict[str, str] = {}
    for paper_id in paper_ids:
        _, outcome = _dispatch_one(
            paths=paths,
            review_id=review_id,
            paper_id=paper_id,
            runtime=runtime,
            backend=backend,
            dispatcher=dispatcher,
        )
        if isinstance(outcome, Exception):
            failures[paper_id] = f"{type(outcome).__name__}: {outcome}"
        else:
            successes[paper_id] = outcome
    return {"successes": successes, "failures": failures}


def _run_claude_code(
    *,
    paths: ReviewPaths,
    review_id: str,
    paper_ids: list[str],
    parallel_cap: int,
    dispatcher: Callable[[str, str], dict[str, Any]],
) -> dict[str, Any]:
    return _run_pool(
        paths=paths,
        review_id=review_id,
        paper_ids=paper_ids,
        parallel_cap=parallel_cap,
        runtime="claude_code",
        backend=None,
        dispatcher=dispatcher,
    )


def _run_cowork_mcp(
    *,
    paths: ReviewPaths,
    review_id: str,
    paper_ids: list[str],
    parallel_cap: int,
    dispatcher: Callable[[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Cowork: scriptorium-mcp backend.

    Per-paper extraction context lives in the MCP server's process
    (each ``mcp__scriptorium__extract_paper`` call resolves a fresh
    per-paper prompt). The orchestrator brings the dispatcher; we share
    the bounded-parallel fan-out with the CC path.
    """
    return _run_pool(
        paths=paths,
        review_id=review_id,
        paper_ids=paper_ids,
        parallel_cap=parallel_cap,
        runtime="cowork",
        backend="mcp",
        dispatcher=dispatcher,
    )


def _run_cowork_notebooklm(
    *,
    paths: ReviewPaths,
    review_id: str,
    paper_ids: list[str],
    parallel_cap: int,
    dispatcher: Callable[[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Cowork: NotebookLM backend.

    The orchestrator creates a fresh notebook per paper (or rotates a
    scratch notebook for quota-pressured users) and dispatches the
    extraction inside that notebook's source-add → notebook_query →
    notebook_delete cycle. Bounded-parallel fan-out is fine — the
    isolation property comes from the per-paper notebook, not the
    thread pool.
    """
    return _run_pool(
        paths=paths,
        review_id=review_id,
        paper_ids=paper_ids,
        parallel_cap=parallel_cap,
        runtime="cowork",
        backend="notebooklm",
        dispatcher=dispatcher,
    )


def _run_cowork_sequential(
    *,
    paths: ReviewPaths,
    review_id: str,
    paper_ids: list[str],
    parallel_cap: int,
    dispatcher: Callable[[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Cowork: degraded sequential backend.

    Single chat thread, one paper at a time, with a context-clear
    prompt between them. ``parallel_cap`` is intentionally IGNORED —
    sequential is the honest-gap path and must run strictly serially
    even when the caller passes a higher cap. The SKILL.md and smoke
    doc carry the ``⚠`` marker; this branch is the runtime backing
    that label.
    """
    del parallel_cap  # explicit: cap does not apply to sequential
    return _run_serial(
        paths=paths,
        review_id=review_id,
        paper_ids=paper_ids,
        runtime="cowork",
        backend="sequential",
        dispatcher=dispatcher,
    )


_COWORK_DISPATCH: dict[
    str,
    Callable[..., dict[str, Any]],
] = {
    "mcp": _run_cowork_mcp,
    "notebooklm": _run_cowork_notebooklm,
    "sequential": _run_cowork_sequential,
}


def _check_dispatcher(agent_dispatcher: object | None, *, ctx: str) -> Callable[[str, str], dict[str, Any]]:
    """Validate ``agent_dispatcher`` and narrow it to a callable.

    ``ctx`` is a short string spliced into the error message
    (``"Claude Code"``, ``"Cowork:mcp"``, etc.) so a missing-dispatcher
    failure tells the caller WHICH branch they were on.
    """
    if agent_dispatcher is None:
        raise ScriptoriumError(
            f"{ctx} extraction requires an agent_dispatcher; none was provided",
            symbol="E_EXTRACT_NO_DISPATCHER",
        )
    if not callable(agent_dispatcher):
        raise ScriptoriumError(
            "agent_dispatcher must be callable as dispatcher(paper_id, "
            "prompt) -> dict",
            symbol="E_EXTRACT_NO_DISPATCHER",
        )
    return agent_dispatcher  # type: ignore[return-value]


def run_extraction(
    paths: ReviewPaths,
    *,
    review_id: str,
    paper_ids: list[str],
    runtime: str,
    parallel_cap: int,
    agent_dispatcher: object | None = None,
    cowork_backend: str | None = None,
) -> dict[str, Any]:
    """Orchestrate per-paper extraction (plan §6.2 signature).

    The ``runtime`` literal selects the top-level branch (``claude_code``
    or ``cowork``). For Cowork, ``cowork_backend`` selects one of the
    three dispatch backends from the ``using-scriptorium`` runtime
    probe — ``mcp``, ``notebooklm``, or ``sequential``. ``mcp`` and
    ``notebooklm`` honor ``parallel_cap`` (bounded fan-out); the
    degraded ``sequential`` backend ignores it and runs strictly serial.

    The return dict carries::

        {
          "runtime": "<runtime>",
          "backend": "<backend>",   # only present for Cowork
          "review_id": "<review_id>",
          "successes": {paper_id: <dispatcher_result>, ...},
          "failures":  {paper_id: "<ExcType>: <msg>", ...},
        }

    Raises:
        ScriptoriumError(symbol="E_EXTRACT_BAD_CAP") when parallel_cap < 1.
        ScriptoriumError(symbol="E_EXTRACT_NO_DISPATCHER") when
            ``agent_dispatcher`` is None or not callable for any branch
            that requires one.
        ScriptoriumError(symbol="E_EXTRACT_NO_BACKEND") when
            ``runtime == "cowork"`` and ``cowork_backend`` is None.
        ScriptoriumError(symbol="E_EXTRACT_UNKNOWN_BACKEND") when
            ``cowork_backend`` is not one of ``mcp|notebooklm|sequential``.
        ScriptoriumError(symbol="E_EXTRACT_UNKNOWN_RUNTIME") for any
            runtime literal we don't recognize.
    """
    if isinstance(parallel_cap, bool) or not isinstance(parallel_cap, int) or parallel_cap < 1:
        raise ScriptoriumError(
            f"parallel_cap must be a positive int, got {parallel_cap!r}",
            symbol="E_EXTRACT_BAD_CAP",
        )

    if runtime == "claude_code":
        # `cowork_backend` is meaningless on the CC branch. Reject
        # explicitly so a misconfigured caller can't silently bypass
        # the audit-row backend field.
        if cowork_backend is not None:
            raise ScriptoriumError(
                "cowork_backend is only valid when runtime='cowork'; "
                f"got runtime='claude_code' and cowork_backend="
                f"{cowork_backend!r}",
                symbol="E_EXTRACT_UNKNOWN_BACKEND",
            )
        dispatcher = _check_dispatcher(
            agent_dispatcher, ctx="Claude Code"
        )
        result = _run_claude_code(
            paths=paths,
            review_id=review_id,
            paper_ids=paper_ids,
            parallel_cap=parallel_cap,
            dispatcher=dispatcher,
        )
        result["runtime"] = "claude_code"
        result["review_id"] = review_id
        return result

    if runtime == "cowork":
        if cowork_backend is None:
            raise ScriptoriumError(
                "Cowork extraction requires `cowork_backend`; expected "
                f"one of {list(COWORK_BACKENDS)}, got None. The "
                "`using-scriptorium` runtime probe should set this from "
                "the orchestrator's ISOLATION_BACKEND.",
                symbol="E_EXTRACT_NO_BACKEND",
            )
        if not is_valid_backend(cowork_backend):
            raise ScriptoriumError(
                f"unknown cowork_backend {cowork_backend!r}; expected one "
                f"of {list(COWORK_BACKENDS)}",
                symbol="E_EXTRACT_UNKNOWN_BACKEND",
            )
        dispatcher = _check_dispatcher(
            agent_dispatcher, ctx=f"Cowork:{cowork_backend}"
        )
        runner = _COWORK_DISPATCH[cowork_backend]
        result = runner(
            paths=paths,
            review_id=review_id,
            paper_ids=paper_ids,
            parallel_cap=parallel_cap,
            dispatcher=dispatcher,
        )
        result["runtime"] = "cowork"
        result["backend"] = cowork_backend
        result["review_id"] = review_id
        return result

    raise ScriptoriumError(
        f"unknown runtime {runtime!r}; expected 'claude_code' or 'cowork'",
        symbol="E_EXTRACT_UNKNOWN_RUNTIME",
    )
