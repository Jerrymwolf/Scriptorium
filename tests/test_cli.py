# tests/test_cli.py
import json
import tomllib
from io import StringIO
from pathlib import Path

import pytest

from scriptorium import cli as cli_mod


def run(args, review_dir, stdin_text=""):
    out, err = StringIO(), StringIO()
    full_args = list(args) + ["--review-dir", str(review_dir)]
    rc = cli_mod.main(
        argv=full_args,
        stdout=out,
        stderr=err,
        stdin=StringIO(stdin_text),
    )
    return rc, out.getvalue(), err.getvalue()


def test_version_prints_name_and_semver(review_dir):
    rc, out, err = run(["version"], review_dir)
    assert rc == 0, err
    assert "scriptorium" in out.lower()


@pytest.mark.parametrize(
    "subcmd",
    [
        "search", "fetch-doi", "corpus", "screen",
        "register-pdf", "fetch-fulltext", "extract-pdf",
        "evidence", "audit", "verify",
        "contradictions", "bib", "config",
    ],
)
def test_help_for_each_subcommand(review_dir, subcmd):
    rc, out, err = run([subcmd, "--help"], review_dir)
    assert rc == 0
    combined = out + err
    assert subcmd in combined or "usage" in combined.lower()


def test_unknown_command_returns_usage_error(review_dir):
    rc, out, err = run(["does-not-exist"], review_dir)
    assert rc != 0
    assert "invalid choice" in err.lower() or "error" in err.lower()


def test_evidence_add_then_list_roundtrip(review_dir):
    rc, _, err = run(
        [
            "evidence", "add",
            "--paper-id", "W1",
            "--locator", "page:4",
            "--claim", "Caffeine improves working memory.",
            "--quote", "Accuracy was higher (p=.02).",
            "--direction", "positive",
            "--concept", "caffeine_wm",
        ],
        review_dir,
    )
    assert rc == 0, err
    rc, out, err = run(["evidence", "list"], review_dir)
    assert rc == 0, err
    data = json.loads(out)
    assert len(data) == 1
    assert data[0]["paper_id"] == "W1"
    assert data[0]["direction"] == "positive"


def test_audit_append_then_read_roundtrip(review_dir):
    rc, _, err = run(
        [
            "audit", "append",
            "--phase", "screening",
            "--action", "rule.apply",
            "--details", '{"kept": 28, "dropped": 14}',
        ],
        review_dir,
    )
    assert rc == 0, err
    rc, out, err = run(["audit", "read"], review_dir)
    assert rc == 0, err
    entries = [json.loads(line) for line in out.splitlines() if line.strip()]
    assert len(entries) == 1
    assert entries[0]["phase"] == "screening"
    assert entries[0]["details"]["kept"] == 28


def test_verify_on_clean_synthesis_returns_zero(review_dir, tmp_path):
    from scriptorium.paths import resolve_review_dir
    from scriptorium.storage.evidence import EvidenceEntry, append_evidence
    paths = resolve_review_dir(explicit=review_dir)
    append_evidence(paths, EvidenceEntry(
        paper_id="W1", locator="page:4",
        claim="caffeine WM", quote="...",
        direction="positive", concept="c",
    ))
    synth = review_dir / "synthesis.md"
    synth.write_text("Caffeine helps [W1:page:4].\n", encoding="utf-8")
    rc, out, err = run(["verify", "--synthesis", str(synth)], review_dir)
    assert rc == 0, err
    report = json.loads(out)
    assert report["ok"] is True


def test_verify_on_unsupported_synthesis_exits_3(review_dir):
    synth = review_dir / "synthesis.md"
    synth.write_text("Unsupported floating claim.\n", encoding="utf-8")
    rc, out, err = run(["verify", "--synthesis", str(synth)], review_dir)
    assert rc == 3
    report = json.loads(out)
    assert report["ok"] is False


def test_bib_emits_bibtex_for_kept_papers(review_dir):
    from scriptorium.paths import resolve_review_dir
    from scriptorium.sources.base import Paper
    from scriptorium.storage.corpus import add_papers, set_status
    paths = resolve_review_dir(explicit=review_dir)
    add_papers(paths, [Paper(
        paper_id="W1", source="openalex", title="Caffeine WM",
        authors=["Smith, J."], year=2019, doi="10.1/abc",
    )])
    set_status(paths, "W1", "kept")
    rc, out, err = run(["bib", "--format", "bibtex"], review_dir)
    assert rc == 0, err
    assert "@article{W1" in out


def test_config_get_and_set(review_dir):
    cfg = review_dir / "config.toml"
    rc, _, err = run(["config", "set", "default_model", "haiku"], review_dir)
    assert rc == 0, err
    assert cfg.exists()
    rc, out, err = run(["config", "get", "default_model"], review_dir)
    assert rc == 0, err
    assert out.strip() == "haiku"


def test_config_set_stores_injection_value_literally(review_dir):
    """Defect-fix #3 at the CLI layer: --value is stored as literal TOML data."""
    cfg = review_dir / "config.toml"
    payload = 'opus"\nevil_key = "stolen'
    rc, _, err = run(
        ["config", "set", "default_model", payload],
        review_dir,
    )
    assert rc == 0, err
    rc, out, err = run(["config", "get", "default_model"], review_dir)
    assert rc == 0, err
    assert out.rstrip("\n") == payload

    data = tomllib.loads(cfg.read_text(encoding="utf-8"))
    assert "evil_key" not in data
    assert "evil_key" not in data.get("scriptorium", {})
    assert data["scriptorium"]["default_model"] == payload
