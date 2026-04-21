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
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Sequence, TextIO

from scriptorium import __version__
from scriptorium.config import load_config, save_config_from_kv
from scriptorium.paths import ReviewPaths, resolve_review_dir
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


def cmd_verify(args, paths, stdout, stderr, stdin) -> int:
    synth_path = Path(args.synthesis)
    if not synth_path.exists():
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


def cmd_migrate_review(args, paths, stdout, stderr, stdin) -> int:
    import json as _json
    from scriptorium.errors import EXIT_CODES, ScriptoriumError
    from scriptorium.lock import ReviewLockHeld
    from scriptorium.migrate import migrate_review
    from scriptorium.paths import resolve_review_dir
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
    pv.add_argument("--synthesis", required=True)

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

    pm = sub.add_parser("migrate-review", help="Migrate a legacy review to v0.3")
    pm.add_argument("review_dir_pos", metavar="review-dir")
    pm.add_argument("--dry-run", action="store_true")
    pm.add_argument("--json", dest="json_mode", action="store_true")

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

    return p


def main(
    argv: Sequence[str] | None = None,
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
    paths = resolve_review_dir(explicit=explicit, vault_root=None, cwd=None, create=True)

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
