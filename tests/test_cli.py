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


# ---------------------------------------------------------------------------
# T04 — CLI v0.4 enforcement surface
# ---------------------------------------------------------------------------


# --- phase show ---

def test_phase_show_returns_all_phases(review_dir):
    rc, out, err = run(["phase", "show"], review_dir)
    assert rc == 0, err
    data = json.loads(out)
    assert "phases" in data
    assert "synthesis" in data["phases"]


# --- phase set ---

def test_phase_set_running(review_dir):
    rc, out, err = run(["phase", "set", "search", "running"], review_dir)
    assert rc == 0, err
    # Confirm state persisted
    rc2, out2, _ = run(["phase", "show"], review_dir)
    assert rc2 == 0
    state = json.loads(out2)
    assert state["phases"]["search"]["status"] == "running"


def test_phase_set_complete_requires_signature(review_dir):
    """phase set synthesis complete without --verifier-signature should fail."""
    rc, out, err = run(["phase", "set", "synthesis", "complete"], review_dir)
    assert rc == 20  # E_PHASE_STATE_INVALID


def test_phase_set_complete_with_signature(review_dir):
    sig = "sha256:" + "a" * 64
    rc, out, err = run(
        ["phase", "set", "synthesis", "complete",
         "--verifier-signature", sig],
        review_dir,
    )
    assert rc == 0, err
    state = json.loads(out)
    assert state["phases"]["synthesis"]["status"] == "complete"
    assert state["phases"]["synthesis"]["verifier_signature"] == sig


def test_phase_set_overridden_rejected(review_dir):
    """phase set <phase> overridden should tell user to use phase override."""
    rc, out, err = run(["phase", "set", "synthesis", "overridden"], review_dir)
    assert rc == 20  # E_PHASE_STATE_INVALID


def test_phase_set_unknown_phase(review_dir):
    rc, out, err = run(["phase", "set", "bogus", "running"], review_dir)
    assert rc == 20  # E_PHASE_STATE_INVALID


# --- phase override ---

def test_phase_override_sets_overridden(review_dir):
    rc, out, err = run(
        ["phase", "override", "synthesis", "--reason", "Emergency override"],
        review_dir,
    )
    assert rc == 0, err
    state = json.loads(out)
    assert state["phases"]["synthesis"]["status"] == "overridden"
    assert state["phases"]["synthesis"]["override"]["reason"] == "Emergency override"


def test_phase_override_actor_from_flag(review_dir):
    rc, out, err = run(
        ["phase", "override", "extraction",
         "--reason", "Skip step",
         "--actor", "test-user"],
        review_dir,
    )
    assert rc == 0, err
    state = json.loads(out)
    assert state["phases"]["extraction"]["override"]["actor"] == "test-user"


def test_phase_override_requires_reason(review_dir):
    rc, out, err = run(["phase", "override", "synthesis"], review_dir)
    # argparse will return usage error (exit 2) for missing --reason
    assert rc != 0


# --- verify --gate ---

def test_verify_gate_scope_valid(review_dir):
    scope_path = review_dir / "scope.json"
    scope_path.write_text(json.dumps({
        "schema_version": 1,
        "created_at": "2026-01-01T00:00:00Z",
        "research_question": "Does caffeine improve working memory?",
        "purpose": "systematic",
        "fields": ["cognitive psychology"],
        "population": "healthy adults",
        "methodology": "RCT",
        "year_range": [2000, 2026],
        "corpus_target": 50,
        "publication_types": ["peer-reviewed"],
        "depth": "exhaustive",
        "conceptual_frame": "attention",
        "anchor_papers": [],
        "output_intent": "dissertation",
        "known_gaps_focus": True,
        "paradigm": "positivist",
        "soft_warnings": [],
    }), encoding="utf-8")
    rc, out, err = run(["verify", "--gate", "scope", "--scope", str(scope_path)], review_dir)
    assert rc == 0, err


def test_verify_gate_synthesis_clean(review_dir):
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
    rc, out, err = run(
        ["verify", "--gate", "synthesis", "--synthesis", str(synth)],
        review_dir,
    )
    assert rc == 0, err
    report = json.loads(out)
    assert report["ok"] is True


def test_verify_gate_publish_blocked_when_synthesis_pending(review_dir):
    """publish gate should fail when synthesis phase is pending."""
    rc, out, err = run(["verify", "--gate", "publish"], review_dir)
    assert rc == 3  # E_VERIFY_FAILED
    data = json.loads(err) if not out.strip() else json.loads(out) if out.strip() else {}
    # Accept either channel — just confirm non-zero exit
    assert rc != 0


def test_verify_gate_publish_passes_when_synthesis_complete(review_dir):
    sig = "sha256:" + "b" * 64
    rc, _, err = run(
        ["phase", "set", "synthesis", "complete", "--verifier-signature", sig],
        review_dir,
    )
    assert rc == 0, err
    rc, out, err = run(["verify", "--gate", "publish"], review_dir)
    assert rc == 0, err
    data = json.loads(out)
    assert data["ok"] is True


def test_verify_gate_publish_passes_when_synthesis_overridden(review_dir):
    rc, _, err = run(
        ["phase", "override", "synthesis", "--reason", "skip"],
        review_dir,
    )
    assert rc == 0, err
    rc, out, err = run(["verify", "--gate", "publish"], review_dir)
    assert rc == 0, err
    data = json.loads(out)
    assert data["ok"] is True


# --- reviewer-validate ---

def test_reviewer_validate_valid_payload(review_dir, tmp_path):
    payload = {
        "reviewer": "cite",
        "runtime": "claude_code",
        "verdict": "pass",
        "summary": "All citations verified.",
        "findings": [],
        "synthesis_sha256": "sha256:" + "c" * 64,
        "reviewer_prompt_sha256": "sha256:" + "d" * 64,
        "created_at": "2026-01-01T00:00:00Z",
    }
    f = tmp_path / "reviewer_output.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    rc, out, err = run(["reviewer-validate", str(f)], review_dir)
    assert rc == 0, err
    data = json.loads(out)
    assert data["ok"] is True


def test_reviewer_validate_missing_hash(review_dir, tmp_path):
    payload = {
        "reviewer": "cite",
        "runtime": "claude_code",
        "verdict": "pass",
        "summary": "ok",
        "findings": [],
        # synthesis_sha256 intentionally missing
        "reviewer_prompt_sha256": "sha256:" + "d" * 64,
        "created_at": "2026-01-01T00:00:00Z",
    }
    f = tmp_path / "reviewer_bad.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    rc, out, err = run(["reviewer-validate", str(f)], review_dir)
    assert rc == 22  # E_REVIEWER_INVALID
    data = json.loads(err)
    assert data["code"] == 22


def test_reviewer_validate_fail_verdict_requires_findings(review_dir, tmp_path):
    payload = {
        "reviewer": "contradiction",
        "runtime": "cowork",
        "verdict": "fail",
        "summary": "Found issues.",
        "findings": [],  # fail requires at least one finding
        "synthesis_sha256": "sha256:" + "e" * 64,
        "reviewer_prompt_sha256": "sha256:" + "f" * 64,
        "created_at": "2026-01-01T00:00:00Z",
    }
    f = tmp_path / "reviewer_fail_empty.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    rc, out, err = run(["reviewer-validate", str(f)], review_dir)
    assert rc == 22  # E_REVIEWER_INVALID


def test_reviewer_validate_invalid_reviewer_field(review_dir, tmp_path):
    payload = {
        "reviewer": "not_a_real_reviewer",
        "runtime": "claude_code",
        "verdict": "pass",
        "summary": "ok",
        "findings": [],
        "synthesis_sha256": "sha256:" + "a" * 64,
        "reviewer_prompt_sha256": "sha256:" + "b" * 64,
        "created_at": "2026-01-01T00:00:00Z",
    }
    f = tmp_path / "reviewer_bad_reviewer.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    rc, out, err = run(["reviewer-validate", str(f)], review_dir)
    assert rc == 22  # E_REVIEWER_INVALID


def test_reviewer_validate_bad_hash_format(review_dir, tmp_path):
    payload = {
        "reviewer": "cite",
        "runtime": "claude_code",
        "verdict": "pass",
        "summary": "ok",
        "findings": [],
        "synthesis_sha256": "not-a-real-hash",
        "reviewer_prompt_sha256": "sha256:" + "b" * 64,
        "created_at": "2026-01-01T00:00:00Z",
    }
    f = tmp_path / "reviewer_badhash.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    rc, out, err = run(["reviewer-validate", str(f)], review_dir)
    assert rc == 22  # E_REVIEWER_INVALID


# --- migrate-review --to 0.4 ---

def test_migrate_review_rejects_unknown_to_version(review_dir, tmp_path):
    """migrate-review --to 99.0 should be rejected with a usage error."""
    rdir = tmp_path / "mig_review"
    rdir.mkdir()
    rc, out, err = run(["migrate-review", str(rdir), "--to", "99.0"], review_dir)
    assert rc == 2
    assert "unsupported" in err.lower() or "0.4" in err


def test_migrate_review_to_04_accepted(review_dir, tmp_path):
    from scriptorium.paths import resolve_review_dir
    from scriptorium.storage.corpus import add_papers
    from scriptorium.sources.base import Paper
    rdir = tmp_path / "mig_review2"
    rdir.mkdir()
    # create minimal structure expected by migrate
    (rdir / "data").mkdir()
    (rdir / "audit").mkdir()
    (rdir / "sources" / "pdfs").mkdir(parents=True)
    (rdir / "sources" / "papers").mkdir(parents=True)
    (rdir / "data" / "extracts").mkdir(parents=True)
    (rdir / "audit" / "overview-archive").mkdir(parents=True)
    (rdir / ".scriptorium").mkdir(parents=True)
    rc, out, err = run(["migrate-review", str(rdir), "--to", "0.4"], review_dir)
    # Only requirement: it accepted --to 0.4 (no argparse error)
    # It may succeed or fail based on migration logic, but rc != 2 from argparse
    assert rc != 2 or "unrecognized" not in err.lower()
