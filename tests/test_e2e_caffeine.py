# tests/test_e2e_caffeine.py
"""End-to-end CC pipeline test — drives `scriptorium.cli.main()` with argv
arrays, exactly like the installed console script. OpenAlex is stubbed with
respx; no real network. Proves: subcommand names are stable, exit codes
carry the right signal, JSON shapes are stable, audit trail covers every
phase the running-lit-review skill lists.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import httpx
import pytest
import respx

from scriptorium.cli import main as cli_main

FIXTURE = Path(__file__).parent / "fixtures/openalex/e2e_caffeine_search.json"


def _run(argv: list[str], *, review_dir: Path, stdin: str = "") -> tuple[int, str, str]:
    """Invoke scriptorium.cli.main in-process, capturing stdout/stderr."""
    out = io.StringIO()
    err = io.StringIO()
    inp = io.StringIO(stdin)
    code = cli_main(
        argv=["--review-dir", str(review_dir), *argv],
        stdout=out, stderr=err, stdin=inp,
    )
    return code, out.getvalue(), err.getvalue()


def test_caffeine_pipeline_end_to_end(review_dir):
    fixture_payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://api.openalex.org/works").mock(
            return_value=httpx.Response(200, json=fixture_payload)
        )

        # 1. Search — returns 6 papers as JSON on stdout.
        code, out, err = _run(
            ["search", "--query", "caffeine working memory", "--source", "openalex", "--limit", "20"],
            review_dir=review_dir,
        )
        assert code == 0, err
        papers = json.loads(out)
        assert len(papers) == 6
        assert {p["paper_id"] for p in papers} == {"W1", "W2", "W3", "W4", "W5", "W6"}

        # 2. Corpus add via --from-stdin — feed the JSON back in.
        code, out, _ = _run(
            ["corpus", "add", "--from-stdin"],
            review_dir=review_dir,
            stdin=json.dumps(papers),
        )
        assert code == 0
        assert json.loads(out) == {"added": 6}

    # 3. Screen — year_min=2015, must-include caffeine, must-exclude rats.
    code, out, _ = _run(
        [
            "screen",
            "--year-min", "2015",
            "--language", "en",
            "--must-include", "caffeine",
            "--must-exclude", "rats",
        ],
        review_dir=review_dir,
    )
    assert code == 0
    result = json.loads(out)
    # Expected: W1(2019), W2(2020), W5(2022) kept; W3(rats), W4(year<2015), W6(fr) dropped.
    assert result == {"kept": 3, "dropped": 3}

    # 4. Evidence add — 3 rows seeding the caffeine_wm concept.
    for pid, direction, quote in [
        ("W1", "positive", "Moderate caffeine improves working memory"),
        ("W2", "negative", "High doses of caffeine impair WM"),
        ("W5", "positive", "caffeine working memory students"),
    ]:
        code, _, _ = _run(
            [
                "evidence", "add",
                "--paper-id", pid,
                "--locator", "p.1",
                "--claim", f"{pid} claim",
                "--quote", quote,
                "--direction", direction,
                "--concept", "caffeine_wm",
            ],
            review_dir=review_dir,
        )
        assert code == 0

    # 5. Audit append for each phase so the trail covers search/screening/extraction.
    for phase, action, details in [
        ("search", "openalex.query", {"n_returned": 6, "n_added": 6}),
        ("screening", "rule.apply", {"kept": 3, "dropped": 3}),
        ("extraction", "extract", {"n_evidence_rows": 3}),
    ]:
        code, _, _ = _run(
            [
                "audit", "append",
                "--phase", phase,
                "--action", action,
                "--details", json.dumps(details),
            ],
            review_dir=review_dir,
        )
        assert code == 0

    # 6. Write a synthesis with ONE planted unsupported sentence.
    synth = review_dir / "synthesis.md"
    synth.write_text(
        "Moderate caffeine improves working memory [W1:p.1].\n"
        "Replication in students confirms the effect [W5:p.1].\n"
        "High doses impair working memory [W2:p.1].\n"
        "Caffeine cures all cognitive decline.\n",  # unsupported
        encoding="utf-8",
    )

    # 7. Verify — exit 3 signals unsupported / missing citations.
    code, out, err = _run(
        ["verify", "--synthesis", str(synth)],
        review_dir=review_dir,
    )
    assert code == 3, err
    report = json.loads(out)
    assert report["ok"] is False
    assert any(
        "cures all cognitive decline" in s.lower()
        for s in report["unsupported_sentences"]
    )

    # 8. Rewrite the synthesis without the planted sentence and verify again.
    synth.write_text(
        "Moderate caffeine improves working memory [W1:p.1].\n"
        "Replication in students confirms the effect [W5:p.1].\n"
        "High doses impair working memory [W2:p.1].\n",
        encoding="utf-8",
    )
    code, out, err = _run(
        ["verify", "--synthesis", str(synth)],
        review_dir=review_dir,
    )
    assert code == 0, err
    assert json.loads(out)["ok"] is True

    # 9. Contradictions — one pair on caffeine_wm (W1/W5 positive vs W2 negative).
    code, out, _ = _run(["contradictions"], review_dir=review_dir)
    assert code == 0
    pairs = json.loads(out)
    assert len(pairs) >= 1
    assert all(p["concept"] == "caffeine_wm" for p in pairs)

    # 10. Bib — kept papers only (W1, W2, W5).
    code, out, _ = _run(["bib", "--format", "bibtex"], review_dir=review_dir)
    assert code == 0
    body = out
    for key_marker in ("W1", "W2", "W5"):
        assert key_marker in body
    assert "W3" not in body  # dropped (rats)
    assert "W4" not in body  # dropped (year)
    assert "W6" not in body  # dropped (language)

    # 11. Audit read — every phase is represented.
    code, out, _ = _run(["audit", "read"], review_dir=review_dir)
    assert code == 0
    phases = {json.loads(line)["phase"] for line in out.splitlines() if line.strip()}
    assert {"search", "screening", "extraction"}.issubset(phases)
