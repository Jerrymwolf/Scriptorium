"""Extraction orchestration (plan §6.2).

T12 implements the Claude Code branch: parallel agent dispatch under a
configured cap, with each paper handled in an isolated per-paper prompt.
T13 adds the Cowork branches (`mcp`, `notebooklm`, `sequential`) — those
land as `NotImplementedError` here so T13 starts from a failing test.

Discipline (the v0.4 plan's three rails):

  1. Evidence-first: each paper gets its own dispatcher call with a
     prompt that names ONLY that paper_id. Sibling-paper context never
     bleeds across calls — the per-paper subagent runs in an isolated
     turn so it can't accidentally cite or paraphrase from a sibling.
  2. PRISMA audit trail: each dispatch appends one
     `extraction.dispatch` row, with `status="success"` or
     `status="failure"` plus the error string when the dispatcher
     raises. No silent skips.
  3. Failure isolation: one paper's failure does not abort the batch.
     The return dict carries both `successes` and `failures` so the
     caller can decide whether the run was acceptable.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

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


def _build_prompt(*, paper_id: str, review_id: str) -> str:
    """Build a per-paper prompt that names ONLY this paper.

    The template is parameterized on paper_id and review_id alone — the
    caller's full paper_ids list never reaches per-paper prompts. That's
    the contamination-resistance property the T12 acceptance pins.
    """
    return _PER_PAPER_PROMPT_TEMPLATE.format(
        paper_id=paper_id, review_id=review_id
    )


def _dispatch_one(
    *,
    paths: ReviewPaths,
    review_id: str,
    paper_id: str,
    runtime: str,
    dispatcher: Callable[[str, str], dict[str, Any]],
) -> tuple[str, dict[str, Any] | Exception]:
    """Run one dispatcher call and append its audit row.

    Returns ``(paper_id, dispatcher_result_or_exception)``. Exceptions
    are returned, not re-raised — the caller aggregates per-paper
    success/failure into the return dict so a single failure can't
    abort the batch.
    """
    prompt = _build_prompt(paper_id=paper_id, review_id=review_id)
    try:
        result = dispatcher(paper_id, prompt)
    except Exception as exc:  # noqa: BLE001 — the failure is audited
        append_audit(
            paths,
            AuditEntry(
                phase="extraction",
                action="extraction.dispatch",
                status="failure",
                details={
                    "paper_id": paper_id,
                    "review_id": review_id,
                    "runtime": runtime,
                    "error": f"{type(exc).__name__}: {exc}",
                },
            ),
        )
        return paper_id, exc
    append_audit(
        paths,
        AuditEntry(
            phase="extraction",
            action="extraction.dispatch",
            status="success",
            details={
                "paper_id": paper_id,
                "review_id": review_id,
                "runtime": runtime,
            },
        ),
    )
    return paper_id, result


def _run_claude_code(
    *,
    paths: ReviewPaths,
    review_id: str,
    paper_ids: list[str],
    parallel_cap: int,
    dispatcher: Callable[[str, str], dict[str, Any]],
) -> dict[str, Any]:
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
                runtime="claude_code",
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


def run_extraction(
    paths: ReviewPaths,
    *,
    review_id: str,
    paper_ids: list[str],
    runtime: str,
    parallel_cap: int,
    agent_dispatcher: object | None = None,
) -> dict[str, Any]:
    """Orchestrate per-paper extraction (plan §6.2 signature).

    Parameters mirror the plan's canonical signature byte-for-byte. The
    return dict carries::

        {
          "runtime": "<runtime>",
          "review_id": "<review_id>",
          "successes": {paper_id: <dispatcher_result>, ...},
          "failures":  {paper_id: "<ExcType>: <msg>", ...},
        }

    Raises:
        ScriptoriumError(symbol="E_EXTRACT_BAD_CAP") when parallel_cap < 1.
        ScriptoriumError(symbol="E_EXTRACT_NO_DISPATCHER") when
            ``runtime == "claude_code"`` and ``agent_dispatcher`` is None.
        ScriptoriumError(symbol="E_EXTRACT_UNKNOWN_RUNTIME") for any
            runtime literal we don't recognize.
        NotImplementedError when ``runtime == "cowork"`` (T13 lands the
            Cowork backend dispatch).
    """
    if isinstance(parallel_cap, bool) or not isinstance(parallel_cap, int) or parallel_cap < 1:
        raise ScriptoriumError(
            f"parallel_cap must be a positive int, got {parallel_cap!r}",
            symbol="E_EXTRACT_BAD_CAP",
        )

    if runtime == "claude_code":
        if agent_dispatcher is None:
            raise ScriptoriumError(
                "Claude Code extraction requires an agent_dispatcher; "
                "none was provided",
                symbol="E_EXTRACT_NO_DISPATCHER",
            )
        # The dispatcher is duck-typed: any callable with the
        # signature dispatcher(paper_id, prompt) -> dict will do.
        if not callable(agent_dispatcher):
            raise ScriptoriumError(
                "agent_dispatcher must be callable as dispatcher(paper_id, "
                "prompt) -> dict",
                symbol="E_EXTRACT_NO_DISPATCHER",
            )
        result = _run_claude_code(
            paths=paths,
            review_id=review_id,
            paper_ids=paper_ids,
            parallel_cap=parallel_cap,
            dispatcher=agent_dispatcher,
        )
        result["runtime"] = "claude_code"
        result["review_id"] = review_id
        return result

    if runtime == "cowork":
        # T13 wires the Cowork branches (`mcp`, `notebooklm`,
        # `sequential`). Until then the boundary is explicit so a
        # caller can't mistake silence for support.
        raise NotImplementedError(
            "cowork extraction lands in T13; T12 only owns "
            "runtime='claude_code'"
        )

    raise ScriptoriumError(
        f"unknown runtime {runtime!r}; expected 'claude_code' or 'cowork'",
        symbol="E_EXTRACT_UNKNOWN_RUNTIME",
    )
