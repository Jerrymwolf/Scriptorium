"""Scriptorium command-line entry.

v0.2 replaces v0.1's MCP server with this argparse CLI. Every MCP tool
maps to a ``scriptorium <subcommand>`` invocation. Stdout emits JSON.
On error: JSON to stderr ``{"error": "...", "code": N}`` and exit non-zero.
Exit codes:

- 0 — success
- 1 — unexpected internal error
- 2 — usage / user error (argparse also uses 2)
- 3 — ``verify`` found unsupported sentences or missing citations
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Sequence, TextIO

from scriptorium import __version__
from scriptorium.config import load_config, save_config_from_kv
from scriptorium.paths import ReviewPaths, resolve_review_dir
from scriptorium.scope import (
    ScopeValidationError,
    load_scope,
)
from scriptorium.reasoning.bib_export import export_bibtex, export_ris
from scriptorium.reasoning.contradictions import find_contradictions
from scriptorium.reasoning.screening import ScreenCriteria, screen
from scriptorium.reasoning.verify_citations import verify_synthesis
from scriptorium.sources.base import Paper
from scriptorium.storage.audit import AuditEntry, append_audit, load_audit
from scriptorium.storage.corpus import add_papers, load_corpus, set_status
from scriptorium.storage.evidence import (
    EvidenceEntry,
    append_evidence,
    load_evidence,
)


class CLIError(Exception):
    """User-visible CLI error.

    ``exit_code`` follows the conventions documented in the module docstring.
    """

    def __init__(self, message: str, exit_code: int = 2):
        super().__init__(message)
        self.exit_code = exit_code


def _config_path(paths: ReviewPaths) -> Path:
    return paths.root / "config.toml"


# --- handlers ---


def cmd_version(args, paths, stdout, stderr, stdin) -> int:
    stdout.write(f"scriptorium {__version__}\n")
    return 0


def cmd_search(args, paths, stdout, stderr, stdin) -> int:
    from scriptorium.sources.openalex import OpenAlexAdapter
    from scriptorium.sources.semantic_scholar import SemanticScholarAdapter
    import asyncio
    cfg = load_config(_config_path(paths))
    if args.source == "openalex":
        adapter = OpenAlexAdapter(mailto=cfg.openalex_email or cfg.unpaywall_email)
    elif args.source == "semantic_scholar":
        adapter = SemanticScholarAdapter()
    else:
        raise CLIError(f"Unknown source: {args.source!r}")
    papers = asyncio.run(adapter.search(args.query, limit=args.limit))
    stdout.write(
        json.dumps([asdict(p) for p in papers], indent=2, ensure_ascii=False)
        + "\n"
    )
    return 0


def cmd_fetch_doi(args, paths, stdout, stderr, stdin) -> int:
    from scriptorium.sources.openalex import OpenAlexAdapter
    from scriptorium.sources.semantic_scholar import SemanticScholarAdapter
    import asyncio
    cfg = load_config(_config_path(paths))
    for adapter in (
        OpenAlexAdapter(mailto=cfg.openalex_email or cfg.unpaywall_email),
        SemanticScholarAdapter(),
    ):
        paper = asyncio.run(adapter.fetch_by_doi(args.doi))
        if paper is not None:
            stdout.write(
                json.dumps(asdict(paper), indent=2, ensure_ascii=False) + "\n"
            )
            return 0
    raise CLIError(f"DOI not resolvable: {args.doi}")


def _read_paper_payload(args, stdin: TextIO) -> list[dict]:
    if getattr(args, "from_stdin", False):
        return json.loads(stdin.read())
    if args.file:
        return json.loads(Path(args.file).read_text(encoding="utf-8"))
    raise CLIError("Provide --file PATH or --from-stdin")


def cmd_corpus_add(args, paths, stdout, stderr, stdin) -> int:
    payload = _read_paper_payload(args, stdin)
    if not isinstance(payload, list):
        raise CLIError("Expected a JSON array of Paper-shaped objects")
    papers = [Paper(**row) for row in payload]
    added = add_papers(paths, papers)
    stdout.write(json.dumps({"added": added}) + "\n")
    return 0


def cmd_corpus_list(args, paths, stdout, stderr, stdin) -> int:
    rows = load_corpus(paths)
    if args.status:
        rows = [r for r in rows if r.get("status") == args.status]
    stdout.write(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    return 0


def cmd_screen(args, paths, stdout, stderr, stdin) -> int:
    criteria = ScreenCriteria(
        year_min=args.year_min,
        year_max=args.year_max,
        languages=args.language or [],
        must_include=args.must_include or [],
        must_exclude=args.must_exclude or [],
    )
    rows = load_corpus(paths)
    kept = 0
    dropped = 0
    for row in rows:
        paper = Paper(
            paper_id=row["paper_id"],
            source=row.get("source", ""),
            title=row.get("title", ""),
            authors=row.get("authors") or [],
            year=row.get("year"),
            doi=row.get("doi"),
            venue=row.get("venue"),
            abstract=row.get("abstract"),
            raw=row.get("raw") or {},
        )
        res = screen(paper, criteria)
        if res.keep:
            kept += 1
            set_status(paths, paper.paper_id, "kept", reason=res.reason)
        else:
            dropped += 1
            set_status(paths, paper.paper_id, "dropped", reason=res.reason)
    stdout.write(json.dumps({"kept": kept, "dropped": dropped}) + "\n")
    return 0


def cmd_register_pdf(args, paths, stdout, stderr, stdin) -> int:
    from scriptorium.fulltext.user_pdf import register_user_pdf
    record = register_user_pdf(
        paths, Path(args.pdf), paper_id=args.paper_id
    )
    stdout.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    return 0


def cmd_fetch_fulltext(args, paths, stdout, stderr, stdin) -> int:
    import asyncio
    from scriptorium.fulltext.arxiv import ArxivClient
    from scriptorium.fulltext.cascade import HttpxDownloader, resolve_fulltext
    from scriptorium.fulltext.pmc import PMCClient
    from scriptorium.fulltext.unpaywall import UnpaywallClient

    cfg = load_config(_config_path(paths))
    rows = load_corpus(paths)
    row = next((r for r in rows if r.get("paper_id") == args.paper_id), None)
    if row is None:
        raise CLIError(f"paper_id not in corpus: {args.paper_id}")
    paper = Paper(
        paper_id=row["paper_id"],
        source=row.get("source", ""),
        title=row.get("title", ""),
        authors=row.get("authors") or [],
        year=row.get("year"),
        doi=row.get("doi"),
        venue=row.get("venue"),
        abstract=row.get("abstract"),
        raw=row.get("raw") or {},
    )

    async def run_it():
        return await resolve_fulltext(
            paths, paper,
            unpaywall=UnpaywallClient(email=args.unpaywall_email or cfg.unpaywall_email),
            arxiv=ArxivClient(),
            pmc=PMCClient(),
            downloader=HttpxDownloader(),
        )

    res = asyncio.run(run_it())
    stdout.write(json.dumps({
        "paper_id": res.paper_id,
        "source": res.source,
        "pdf_path": str(res.pdf_path) if res.pdf_path else None,
        "has_text": bool(res.text),
        "n_pages": len(res.pages),
    }) + "\n")
    return 0


def cmd_extract_pdf(args, paths, stdout, stderr, stdin) -> int:
    from scriptorium.fulltext.pdf_text import extract_pages
    pages = extract_pages(Path(args.pdf))
    stdout.write(json.dumps({
        "paper_id": args.paper_id,
        "n_pages": len(pages),
        "pages": pages,
    }, ensure_ascii=False) + "\n")
    return 0


def cmd_evidence_add(args, paths, stdout, stderr, stdin) -> int:
    entry = EvidenceEntry(
        paper_id=args.paper_id,
        locator=args.locator,
        claim=args.claim,
        quote=args.quote,
        direction=args.direction,
        concept=args.concept,
    )
    append_evidence(paths, entry)
    stdout.write("ok\n")
    return 0


def cmd_evidence_list(args, paths, stdout, stderr, stdin) -> int:
    rows = load_evidence(paths)
    stdout.write(
        json.dumps([asdict(r) for r in rows], indent=2, ensure_ascii=False)
        + "\n"
    )
    return 0


def cmd_audit_append(args, paths, stdout, stderr, stdin) -> int:
    try:
        details = json.loads(args.details)
    except json.JSONDecodeError as e:
        raise CLIError(f"--details must be valid JSON: {e}")
    if not isinstance(details, dict):
        raise CLIError("--details must be a JSON object")
    append_audit(paths, AuditEntry(
        phase=args.phase, action=args.action, details=details,
    ))
    stdout.write("ok\n")
    return 0


def cmd_audit_read(args, paths, stdout, stderr, stdin) -> int:
    entries = load_audit(paths)
    for e in entries:
        stdout.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")
    return 0


def cmd_scope_validate(args, paths, stdout, stderr, stdin) -> int:
    """Validate scope.json. Exit 0 if valid, 2 if missing, 3 if invalid."""
    scope_path = Path(args.path) if args.path else paths.scope
    if not scope_path.exists():
        stderr.write(f"scope.json not found at {scope_path}\n")
        return 2
    try:
        load_scope(scope_path)
    except ScopeValidationError as e:
        stderr.write(f"scope validation failed: {e}\n")
        return 3
    stdout.write(f"scope.json is valid ({scope_path})\n")
    return 0


def cmd_verify(args, paths, stdout, stderr, stdin) -> int:
    from scriptorium.errors import EXIT_CODES

    # --gate is the new canonical surface (v0.4); legacy flags still work too.
    gate = getattr(args, "gate", None)

    # Resolve effective flags: --gate overrides the legacy positional flags.
    effective_scope = getattr(args, "scope", None)
    effective_overview = getattr(args, "overview", None)
    effective_synthesis = getattr(args, "synthesis", None)

    if gate == "scope":
        effective_overview = None
        effective_synthesis = None
        # --gate scope uses --scope path; default to paths.scope if not given.
        if not effective_scope:
            effective_scope = str(paths.scope)
    elif gate == "overview":
        effective_scope = None
        effective_synthesis = None
        # --gate overview requires --overview path.
        if not effective_overview:
            raise CLIError("--gate overview requires --overview <path>")
    elif gate == "synthesis":
        effective_scope = None
        effective_overview = None
        # --gate synthesis uses --synthesis path; default to paths.synthesis.
        if not effective_synthesis:
            effective_synthesis = str(paths.synthesis)
    elif gate == "publish":
        # Check phase-state: synthesis must be complete or overridden.
        from scriptorium import phase_state
        from scriptorium.errors import ScriptoriumError
        try:
            state = phase_state.read(paths)
        except ScriptoriumError as e:
            stderr.write(json.dumps({"error": str(e), "code": EXIT_CODES[e.symbol]}) + "\n")
            return EXIT_CODES[e.symbol]
        synth_status = state["phases"].get("synthesis", {}).get("status", "pending")
        if synth_status in ("complete", "overridden"):
            stdout.write(json.dumps({"ok": True, "synthesis_status": synth_status}) + "\n")
            return 0
        else:
            msg = {
                "ok": False,
                "publish_blocked": True,
                "reason": f"synthesis phase status is {synth_status!r}; must be 'complete' or 'overridden'",
                "synthesis_status": synth_status,
            }
            stderr.write(json.dumps(msg) + "\n")
            return EXIT_CODES["E_VERIFY_FAILED"]

    # Legacy / gate-dispatched paths below.
    if effective_scope is not None:
        scope_path = Path(effective_scope)
        try:
            load_scope(scope_path)
        except FileNotFoundError:
            stderr.write(f"scope.json not found at {scope_path}\n")
            return 3
        except ScopeValidationError as e:
            stderr.write(f"scope validation failed: {e}\n")
            return 3
        stdout.write(f"scope.json is valid ({scope_path})\n")
        return 0
    if effective_overview:
        from scriptorium.frontmatter import strip_frontmatter
        from scriptorium.overview.linter import OverviewLintError, lint_overview
        body = strip_frontmatter(Path(effective_overview).read_text(encoding="utf-8"))
        try:
            lint_overview(body)
        except OverviewLintError as e:
            stderr.write(f"scriptorium verify --overview: {e}\n")
            return EXIT_CODES["E_OVERVIEW_FAILED"]
        stdout.write(json.dumps({"ok": True}) + "\n")
        return 0
    synth_path = Path(effective_synthesis) if effective_synthesis else None
    if synth_path is None or not synth_path.exists():
        raise CLIError(f"synthesis file not found: {synth_path}")
    text = synth_path.read_text(encoding="utf-8")
    report = verify_synthesis(text, paths)
    stdout.write(json.dumps({
        "ok": report.ok,
        "unsupported_sentences": report.unsupported_sentences,
        "missing_citations": [list(c) for c in report.missing_citations],
    }, indent=2, ensure_ascii=False) + "\n")
    return 0 if report.ok else 3


def cmd_contradictions(args, paths, stdout, stderr, stdin) -> int:
    pairs = find_contradictions(paths)
    stdout.write(json.dumps([
        {
            "concept": p.concept,
            "a": asdict(p.a),
            "b": asdict(p.b),
        }
        for p in pairs
    ], indent=2, ensure_ascii=False) + "\n")
    return 0


def cmd_bib(args, paths, stdout, stderr, stdin) -> int:
    if args.format == "bibtex":
        out = export_bibtex(paths)
    elif args.format == "ris":
        out = export_ris(paths)
    else:
        raise CLIError(f"Unknown bib format: {args.format!r}")
    stdout.write(out + "\n")
    return 0


def cmd_config_get(args, paths, stdout, stderr, stdin) -> int:
    cfg = load_config(_config_path(paths))
    if not hasattr(cfg, args.key):
        raise CLIError(f"Unknown config key: {args.key}")
    stdout.write(str(getattr(cfg, args.key)) + "\n")
    return 0


def cmd_config_set(args, paths, stdout, stderr, stdin) -> int:
    save_config_from_kv(_config_path(paths), args.key, args.value)
    stdout.write("ok\n")
    return 0


def cmd_init(args, paths, stdout, stderr, stdin) -> int:
    from scriptorium.setup_flow import InitArgs, run_init
    return run_init(
        InitArgs(
            notebooklm=args.notebooklm,
            skip_notebooklm=args.skip_notebooklm,
            vault=Path(args.vault) if args.vault else None,
        ),
        stdout, stderr, stdin,
    )


def cmd_doctor(args, paths, stdout, stderr, stdin) -> int:
    from scriptorium.doctor import run_doctor
    return run_doctor(stdout)


def cmd_phase_show(args, paths, stdout, stderr, stdin) -> int:
    from scriptorium.errors import EXIT_CODES, ScriptoriumError
    from scriptorium import phase_state
    try:
        state = phase_state.read(paths)
    except ScriptoriumError as e:
        stderr.write(json.dumps({"error": str(e), "code": EXIT_CODES[e.symbol]}) + "\n")
        return EXIT_CODES[e.symbol]
    stdout.write(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    return 0


def cmd_phase_set(args, paths, stdout, stderr, stdin) -> int:
    from scriptorium.errors import EXIT_CODES, ScriptoriumError
    from scriptorium import phase_state
    try:
        state = phase_state.set_phase(
            paths,
            args.phase,
            args.status,
            artifact_path=getattr(args, "artifact_path", None),
            verifier_signature=getattr(args, "verifier_signature", None),
            verified_at=getattr(args, "verified_at", None),
        )
    except ScriptoriumError as e:
        stderr.write(json.dumps({"error": str(e), "code": EXIT_CODES[e.symbol]}) + "\n")
        return EXIT_CODES[e.symbol]
    stdout.write(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    return 0


def cmd_phase_override(args, paths, stdout, stderr, stdin) -> int:
    from scriptorium.errors import EXIT_CODES, ScriptoriumError
    from scriptorium import phase_state
    actor = getattr(args, "actor", None) or os.environ.get("USER") or "cli"

    # T16: TTY guard — the CLI is the Claude Code authority surface; an
    # override mutates phase-state irreversibly, so we require explicit
    # operator intent. `--yes` is the non-interactive bypass; on a real
    # TTY we ask for confirmation; otherwise refuse with E_USAGE.
    if not getattr(args, "yes", False):
        try:
            is_tty = stdin.isatty()
        except (AttributeError, ValueError):
            is_tty = False
        if is_tty:
            stdout.write(
                f"Proceed with audited override of {args.phase}? [y/N] "
            )
            stdout.flush()
            try:
                resp = stdin.readline()
            except (EOFError, OSError):
                resp = ""
            if resp.strip().lower() not in ("y", "yes"):
                stdout.write("aborted\n")
                return 0
        else:
            stderr.write(
                "scriptorium phase override: --yes required when stdin "
                "is not a TTY (refuse to mutate phase-state without "
                "explicit operator intent)\n"
            )
            return EXIT_CODES["E_USAGE"]

    try:
        state = phase_state.override_phase(
            paths,
            args.phase,
            reason=args.reason,
            actor=actor,
        )
    except ScriptoriumError as e:
        stderr.write(json.dumps({"error": str(e), "code": EXIT_CODES[e.symbol]}) + "\n")
        return EXIT_CODES[e.symbol]

    # T16: audit-row append. The ts MUST come from the phase-state entry
    # so the audit row and phase-state agree on the same timestamp; the
    # write is append-only (audit.jsonl) so two overrides of the same
    # phase produce two rows.
    append_audit(
        paths,
        AuditEntry(
            phase=args.phase,
            action="phase.override",
            status="success",
            details={
                "phase": args.phase,
                "reason": args.reason,
                "actor": actor,
                "ts": state["phases"][args.phase]["override"]["ts"],
                "runtime": "claude_code",
            },
        ),
    )

    stdout.write(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    return 0


def cmd_reviewer_validate(args, paths, stdout, stderr, stdin) -> int:
    from scriptorium.errors import EXIT_CODES, ScriptoriumError
    from scriptorium.reviewers import validate_reviewer_output
    try:
        payload = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        stderr.write(json.dumps({"error": str(e), "code": EXIT_CODES["E_REVIEWER_INVALID"]}) + "\n")
        return EXIT_CODES["E_REVIEWER_INVALID"]
    try:
        validate_reviewer_output(payload)
    except ScriptoriumError as e:
        stderr.write(json.dumps({"error": str(e), "code": EXIT_CODES[e.symbol]}) + "\n")
        return EXIT_CODES[e.symbol]
    stdout.write(json.dumps({"ok": True}) + "\n")
    return 0


def cmd_migrate_review(args, paths, stdout, stderr, stdin) -> int:
    import json as _json
    from scriptorium.errors import EXIT_CODES, ScriptoriumError
    from scriptorium.lock import ReviewLockHeld
    from scriptorium.migrate import backfill_phase_state_v04, migrate_review
    from scriptorium.paths import resolve_review_dir

    # v0.4 contract: when --to is supplied it must be "0.4"; other values are
    # rejected with a usage error. When --to is absent the legacy migration
    # path runs unchanged (backward compatibility with existing callers).
    to_version = getattr(args, "to", None)
    if to_version is not None and to_version != "0.4":
        stderr.write(f"scriptorium migrate-review: unsupported --to value {to_version!r}; only '0.4' is accepted\n")
        return 2

    rp = resolve_review_dir(
        explicit=Path(args.review_dir_pos), vault_root=None, cwd=None, create=False,
    )
    try:
        res = migrate_review(rp, dry_run=args.dry_run)
    except ReviewLockHeld as e:
        stderr.write(f"scriptorium migrate-review: {e}\n")
        return EXIT_CODES["E_LOCKED"]
    except ScriptoriumError as e:
        stderr.write(f"scriptorium migrate-review: {e}\n")
        return EXIT_CODES[e.symbol]

    # v0.4 §10: when --to 0.4 is supplied, backfill phase-state.json after
    # the legacy migration completes. The legacy migration's lock has been
    # released by now, so phase_state.set_phase can take it cleanly.
    if to_version == "0.4":
        try:
            upgraded = backfill_phase_state_v04(rp, dry_run=args.dry_run)
        except ReviewLockHeld as e:
            stderr.write(f"scriptorium migrate-review: {e}\n")
            return EXIT_CODES["E_LOCKED"]
        except ScriptoriumError as e:
            stderr.write(f"scriptorium migrate-review: {e}\n")
            return EXIT_CODES[e.symbol]
        if upgraded:
            verb = "would upgrade" if args.dry_run else "upgraded"
            res.warnings.append(
                f"phase-state backfill: {verb} {', '.join(upgraded)}"
            )

    if args.json_mode:
        stdout.write(_json.dumps(res.to_dict()) + "\n")
    else:
        stdout.write(f"changed: {res.changed_files}\n")
    return 0


def cmd_regenerate_overview(args, paths, stdout, stderr, stdin) -> int:
    import json as _json
    from scriptorium.config import default_user_config_path, resolve_config
    from scriptorium.errors import EXIT_CODES
    from scriptorium.overview.generator import regenerate_overview, write_failed_draft
    from scriptorium.overview.linter import OverviewLintError
    from scriptorium.paths import resolve_review_dir
    review_paths = resolve_review_dir(
        explicit=Path(args.review_dir_pos),
        vault_root=None,
        cwd=None,
        create=False,
    )
    cfg = resolve_config(
        review_dir=review_paths.root,
        user_config_path=default_user_config_path(),
    )
    model = args.model or cfg.default_model
    try:
        result = regenerate_overview(
            review_paths, model=model, seed=args.seed,
            research_question="", review_id=review_paths.root.name,
        )
    except OverviewLintError as e:
        write_failed_draft(review_paths, str(e))
        stderr.write(f"scriptorium regenerate-overview: {e}\n")
        return EXIT_CODES["E_OVERVIEW_FAILED"]
    if args.json_mode:
        stdout.write(_json.dumps(result.to_dict()) + "\n")
    else:
        stdout.write(f"{result.path}\n")
    return 0


def cmd_publish(args, paths, stdout, stderr, stdin) -> int:
    import json
    from datetime import datetime, timezone
    from scriptorium.cowork import is_cowork_mode
    from scriptorium.errors import EXIT_CODES
    from scriptorium.lock import ReviewLock, ReviewLockHeld
    from scriptorium.nlm import NlmTimeoutError
    from scriptorium.publish import (
        PublishError, PublishUsageError, build_publish_args,
        render_cowork_block, run_publish,
    )
    try:
        pa = build_publish_args(
            review_dir=paths.root,
            notebook=args.notebook,
            generate=args.generate,
            sources_raw=args.sources,
            yes=args.yes,
            json_mode=args.json_mode,
        )
    except PublishUsageError as e:
        stderr.write(f"scriptorium publish: {e}\n")
        return EXIT_CODES[e.symbol]
    except ValueError as e:
        stderr.write(
            f"scriptorium publish: cannot derive notebook name from "
            f"'{paths.root.name}'. Pass --notebook \"<name>\" explicitly.\n"
        )
        return EXIT_CODES["E_NOTEBOOK_NAME"]

    if is_cowork_mode():
        stdout.write(render_cowork_block(
            notebook_name=pa.notebook, review_dir=pa.review_dir, sources=pa.sources,
        ))
        return 0

    # T16: publish gate. Synthesis AND contradiction must be `complete`
    # or `overridden` for publish to proceed. Under `enforce_v04=True`
    # an incomplete gate blocks (E_REVIEW_INCOMPLETE); under the
    # default advisory mode we warn on stderr, append an advisory audit
    # row, and continue. Cowork-mode short-circuits BEFORE the gate.
    from scriptorium import phase_state as _phase_state
    _ALLOWED_GATE = ("complete", "overridden")
    try:
        _gate_state = _phase_state.read(paths)
    except ReviewLockHeld as e:
        # phase_state.read may take the lock when the artifact is
        # missing (init() path). Surface the same E_LOCKED contract the
        # publish flow uses for any held lock — gate-time held lock is
        # functionally identical to publish-time held lock.
        stderr.write(f"scriptorium publish: {e}\n")
        return EXIT_CODES["E_LOCKED"]
    _synth_status = _gate_state["phases"].get("synthesis", {}).get(
        "status", "pending"
    )
    _contra_status = _gate_state["phases"].get("contradiction", {}).get(
        "status", "pending"
    )
    if _synth_status not in _ALLOWED_GATE or _contra_status not in _ALLOWED_GATE:
        _cfg = load_config(_config_path(paths))
        if _cfg.enforce_v04:
            # Blocking branch — name the offending phase first.
            _failing = (
                "synthesis" if _synth_status not in _ALLOWED_GATE
                else "contradiction"
            )
            _failing_status = (
                _synth_status if _failing == "synthesis"
                else _contra_status
            )
            stderr.write(
                json.dumps({
                    "error": (
                        f"publish blocked: {_failing} not "
                        f"complete/overridden (status={_failing_status!r})"
                    ),
                    "code": EXIT_CODES["E_REVIEW_INCOMPLETE"],
                    "synthesis_status": _synth_status,
                    "contradiction_status": _contra_status,
                }) + "\n"
            )
            append_audit(paths, AuditEntry(
                phase="publishing",
                action="publish.blocked",
                status="failure",
                details={
                    "synthesis_status": _synth_status,
                    "contradiction_status": _contra_status,
                    "mode": "blocking",
                },
            ))
            return EXIT_CODES["E_REVIEW_INCOMPLETE"]
        else:
            # Advisory branch — warn to stderr, append advisory row,
            # continue with the existing publish flow. Stdout payload
            # stays untouched (test_publish_flow.py parses it as JSON).
            stderr.write(
                "scriptorium publish: WARNING: synthesis/contradiction "
                "not complete (advisory mode); proceeding...\n"
            )
            append_audit(paths, AuditEntry(
                phase="publishing",
                action="publish.advisory",
                status="warning",
                details={
                    "synthesis_status": _synth_status,
                    "contradiction_status": _contra_status,
                    "mode": "advisory",
                },
            ))

    from scriptorium.publish import has_prior_publish
    if not pa.yes and has_prior_publish(paths.audit_md, pa.notebook):
        stdout.write("Proceed and create a new notebook? [y/N] ")
        stdout.flush()
        resp = stdin.readline().strip().lower()
        if resp not in ("y", "yes"):
            return 0

    from scriptorium.publish import append_partial_audit
    state: dict = {"uploaded_names": [], "attempted_sources": [], "notebook_name": pa.notebook}

    try:
        with ReviewLock(paths.lock):
            now_iso = datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ).replace("+00:00", "Z")
            outcome = run_publish(pa, now_iso=now_iso, partial_state=state)
            from scriptorium.publish import append_publish_audit, collect_source_files
            append_publish_audit(
                review_dir=pa.review_dir,
                outcome=outcome,
                attempted_sources=collect_source_files(review_dir=pa.review_dir, sources=pa.sources),
                status="success",
                triggered_by="scriptorium publish",
                generate_flag=pa.generate,
                notebook_name=pa.notebook,
            )
    except ReviewLockHeld as e:
        stderr.write(f"scriptorium publish: {e}\n")
        return EXIT_CODES["E_LOCKED"]
    except NlmTimeoutError as e:
        append_partial_audit(
            review_dir=pa.review_dir, attempted_sources=state.get("attempted_sources", []),
            uploaded_names=state.get("uploaded_names", []), notebook_id=state.get("notebook_id"),
            notebook_url=state.get("notebook_url"), notebook_name=state.get("notebook_name"),
            failing_command=state.get("failing_command", "nlm (timeout)"),
            exit_code=None, stderr_truncated="timeout", symbol="E_TIMEOUT",
        )
        stderr.write(f"scriptorium publish: nlm subprocess timed out: {e}\n")
        return EXIT_CODES["E_TIMEOUT"]
    except PublishError as e:
        if state.get("notebook_id"):
            append_partial_audit(
                review_dir=pa.review_dir, attempted_sources=state.get("attempted_sources", []),
                uploaded_names=state.get("uploaded_names", []), notebook_id=state.get("notebook_id"),
                notebook_url=state.get("notebook_url"), notebook_name=state.get("notebook_name"),
                failing_command=state.get("failing_command", "nlm"),
                exit_code=state.get("exit_code"), stderr_truncated=state.get("stderr", ""),
                symbol=e.symbol,
            )
        stderr.write(f"scriptorium publish: {e}\n")
        return EXIT_CODES[e.symbol]

    if pa.json_mode:
        stdout.write(json.dumps(outcome.to_json_dict()) + "\n")
    else:
        stdout.write(f"{outcome.notebook_url}\n")
    return 0


# --- dispatch ---


_Handler = Callable[
    [argparse.Namespace, ReviewPaths, TextIO, TextIO, TextIO], int
]

_HANDLERS: dict[tuple[str, str | None], _Handler] = {
    ("version", None): cmd_version,
    ("search", None): cmd_search,
    ("fetch-doi", None): cmd_fetch_doi,
    ("corpus", "add"): cmd_corpus_add,
    ("corpus", "list"): cmd_corpus_list,
    ("screen", None): cmd_screen,
    ("register-pdf", None): cmd_register_pdf,
    ("fetch-fulltext", None): cmd_fetch_fulltext,
    ("extract-pdf", None): cmd_extract_pdf,
    ("evidence", "add"): cmd_evidence_add,
    ("evidence", "list"): cmd_evidence_list,
    ("audit", "append"): cmd_audit_append,
    ("audit", "read"): cmd_audit_read,
    ("scope", "validate"): cmd_scope_validate,
    ("verify", None): cmd_verify,
    ("contradictions", None): cmd_contradictions,
    ("bib", None): cmd_bib,
    ("config", "get"): cmd_config_get,
    ("config", "set"): cmd_config_set,
    ("publish", None): cmd_publish,
    ("regenerate-overview", None): cmd_regenerate_overview,
    ("migrate-review", None): cmd_migrate_review,
    ("doctor", None): cmd_doctor,
    ("init", None): cmd_init,
    # v0.4 phase management
    ("phase", "show"): cmd_phase_show,
    ("phase", "set"): cmd_phase_set,
    ("phase", "override"): cmd_phase_override,
    # v0.4 reviewer validation
    ("reviewer-validate", None): cmd_reviewer_validate,
}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scriptorium",
        description=(
            "Scriptorium: dual-runtime literature-review toolkit. "
            "Run the same subcommands from Claude Code; Cowork uses "
            "platform MCPs for the same workflow."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("version", help="Print version and exit")

    ps = sub.add_parser("search", help="Search an open catalog")
    ps.add_argument("--query", required=True)
    ps.add_argument(
        "--source",
        default="openalex",
        choices=["openalex", "semantic_scholar"],
    )
    ps.add_argument("--limit", type=int, default=20)

    pd = sub.add_parser("fetch-doi", help="Resolve a single DOI")
    pd.add_argument("--doi", required=True)

    pc = sub.add_parser("corpus", help="Corpus operations")
    pcs = pc.add_subparsers(dest="subcommand", required=True)
    pca = pcs.add_parser("add")
    pca.add_argument("--file", help="JSON file with a list of Paper objects")
    pca.add_argument(
        "--from-stdin", action="store_true",
        help="Read the Paper-list JSON from stdin",
    )
    pcl = pcs.add_parser("list")
    pcl.add_argument("--status", help="Filter by candidate/kept/dropped")

    psc = sub.add_parser("screen", help="Apply inclusion/exclusion criteria")
    psc.add_argument("--year-min", type=int)
    psc.add_argument("--year-max", type=int)
    psc.add_argument("--language", action="append")
    psc.add_argument("--must-include", action="append")
    psc.add_argument("--must-exclude", action="append")

    pr = sub.add_parser(
        "register-pdf",
        help="Register a user-supplied PDF into the review's pdfs/ dir",
    )
    pr.add_argument("--pdf", required=True)
    pr.add_argument("--paper-id", required=True)

    pf = sub.add_parser(
        "fetch-fulltext",
        help="Run the user→unpaywall→arxiv→pmc→abstract_only cascade",
    )
    pf.add_argument("--paper-id", required=True)
    pf.add_argument(
        "--unpaywall-email",
        help="Unpaywall requires a contact email for its free API",
    )

    px = sub.add_parser(
        "extract-pdf",
        help="Extract text from a PDF with page:N locators",
    )
    px.add_argument("--pdf", required=True)
    px.add_argument("--paper-id", required=True)

    pe = sub.add_parser("evidence", help="Evidence ledger operations")
    pes = pe.add_subparsers(dest="subcommand", required=True)
    pea = pes.add_parser("add")
    pea.add_argument("--paper-id", required=True)
    pea.add_argument("--locator", required=True)
    pea.add_argument("--claim", required=True)
    pea.add_argument("--quote", default="")
    pea.add_argument(
        "--direction",
        choices=["positive", "negative", "neutral", "mixed"],
        default="neutral",
    )
    pea.add_argument("--concept", default="")
    pes.add_parser("list")

    pa = sub.add_parser("audit", help="PRISMA audit trail operations")
    pas = pa.add_subparsers(dest="subcommand", required=True)
    paa = pas.add_parser("append")
    paa.add_argument("--phase", required=True)
    paa.add_argument("--action", required=True)
    paa.add_argument("--details", default="{}")
    pas.add_parser("read")

    pv = sub.add_parser("verify", help="Verify synthesis citations")
    pv.add_argument("--synthesis", default=None)
    pv.add_argument("--overview", default=None, help="Run overview lint instead of synthesis verify")
    pv.add_argument("--scope", default=None, help="Validate a scope.json file")
    pv.add_argument(
        "--gate",
        choices=["scope", "synthesis", "publish", "overview"],
        default=None,
        help="v0.4 canonical gate: scope | synthesis | publish | overview",
    )

    ps = sub.add_parser("scope", help="Scope artifact (scope.json) operations")
    ps_sub = ps.add_subparsers(dest="subcommand", required=True)
    ps_validate = ps_sub.add_parser("validate", help="Validate scope.json against v1 schema")
    ps_validate.add_argument("--path", default=None, help="Explicit scope.json path")

    sub.add_parser(
        "contradictions",
        help="Surface positive/negative pairs on the same concept",
    )

    pb = sub.add_parser("bib", help="Export the corpus (kept papers only)")
    pb.add_argument(
        "--format", choices=["bibtex", "ris"], default="bibtex",
    )

    pcg = sub.add_parser("config", help="Read or write config values")
    pcgs = pcg.add_subparsers(dest="subcommand", required=True)
    pcg_get = pcgs.add_parser("get")
    pcg_get.add_argument("key")
    pcg_set = pcgs.add_parser("set")
    pcg_set.add_argument("key")
    pcg_set.add_argument("value")

    sub.add_parser("doctor", help="Diagnose scriptorium installation")

    pi = sub.add_parser("init", help="Terminal setup flow (see /scriptorium-setup)")
    pi.add_argument("--notebooklm", action="store_true")
    pi.add_argument("--skip-notebooklm", action="store_true")
    pi.add_argument("--vault", default=None)

    pm = sub.add_parser("migrate-review", help="Migrate a legacy review to v0.3/v0.4")
    pm.add_argument("review_dir_pos", metavar="review-dir")
    pm.add_argument("--dry-run", action="store_true")
    pm.add_argument("--json", dest="json_mode", action="store_true")
    pm.add_argument("--to", dest="to", default=None, help="Target version (required: 0.4)")

    po = sub.add_parser("regenerate-overview", help="Rebuild overview.md")
    po.add_argument("review_dir_pos", metavar="review-dir")
    po.add_argument("--model", default=None)
    po.add_argument("--seed", type=int, default=None)
    po.add_argument("--json", dest="json_mode", action="store_true")

    pp = sub.add_parser("publish", help="Publish a review to NotebookLM")
    pp.add_argument("--notebook")
    pp.add_argument("--generate", choices=["audio", "deck", "mindmap", "video", "all"])
    pp.add_argument("--sources")
    pp.add_argument("--yes", action="store_true")
    pp.add_argument("--json", dest="json_mode", action="store_true")

    # v0.4 phase management
    pph = sub.add_parser("phase", help="Inspect and mutate per-review phase state")
    pph_sub = pph.add_subparsers(dest="subcommand", required=True)

    pph_sub.add_parser("show", help="Print the full phase-state JSON")

    pph_set = pph_sub.add_parser("set", help="Set a phase to a given status")
    pph_set.add_argument("phase", help="Phase name (e.g. synthesis)")
    pph_set.add_argument("status", help="New status (pending|running|complete|failed)")
    pph_set.add_argument("--artifact-path", default=None, dest="artifact_path",
                         help="Path of the protected artifact for this phase")
    pph_set.add_argument("--verifier-signature", default=None, dest="verifier_signature",
                         help="sha256:<64 hex> signature of the artifact")
    pph_set.add_argument("--verified-at", default=None, dest="verified_at",
                         help="ISO-8601 UTC timestamp (auto-filled when omitted)")

    pph_ov = pph_sub.add_parser("override", help="Mark a phase as overridden with a justification")
    pph_ov.add_argument("phase", help="Phase name to override")
    pph_ov.add_argument("--reason", required=True, help="Human-readable justification")
    pph_ov.add_argument("--actor", default=None,
                        help="Who is overriding (defaults to $USER or 'cli')")
    pph_ov.add_argument("--yes", action="store_true",
                        help="Skip the interactive TTY confirmation; required "
                             "when stdin is not a TTY (T16)")

    # v0.4 reviewer validation
    prv = sub.add_parser("reviewer-validate", help="Validate a reviewer output JSON file")
    prv.add_argument("json_file", metavar="json-file",
                     help="Path to the reviewer output JSON file")

    return p


def main(
    argv: Sequence[str] | None = None,
    cwd: Path | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    stdin: TextIO | None = None,
) -> int:
    stdout = stdout if stdout is not None else sys.stdout
    stderr = stderr if stderr is not None else sys.stderr
    stdin = stdin if stdin is not None else sys.stdin

    # Pre-extract --review-dir so it works whether it appears before or after
    # the subcommand (tests append it at the end: ["version", "--review-dir", ...]).
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--review-dir", default=None)
    pre_ns, remaining = pre.parse_known_args(argv)

    parser = _build_parser()
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            ns = parser.parse_args(remaining)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 2

    # Merge review_dir from pre-parser into ns
    ns.review_dir = pre_ns.review_dir

    explicit = Path(ns.review_dir) if ns.review_dir else None
    paths = resolve_review_dir(explicit=explicit, vault_root=None, cwd=cwd, create=True)

    handler = _HANDLERS.get((ns.command, getattr(ns, "subcommand", None)))
    if handler is None:
        stderr.write(
            f"error: no handler for ({ns.command!r}, "
            f"{getattr(ns, 'subcommand', None)!r})\n"
        )
        return 2

    try:
        return handler(ns, paths, stdout, stderr, stdin)
    except CLIError as e:
        stderr.write(json.dumps({"error": str(e), "code": e.exit_code}) + "\n")
        return e.exit_code
    except Exception as e:  # noqa: BLE001
        stderr.write(json.dumps({"error": f"{type(e).__name__}: {e}", "code": 1}) + "\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
