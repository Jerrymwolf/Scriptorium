from pathlib import Path
from scriptorium.paths import resolve_review_dir, ReviewPaths


def test_resolve_review_dir_uses_explicit_path(tmp_path):
    target = tmp_path / "my-review"
    target.mkdir()
    paths = resolve_review_dir(explicit=target)
    assert paths.root == target
    assert paths.evidence == target / "evidence.jsonl"
    assert paths.audit_md == target / "audit.md"


def test_resolve_review_dir_creates_subdirs(tmp_path):
    target = tmp_path / "my-review"
    paths = resolve_review_dir(explicit=target, create=True)
    assert (target / "pdfs").is_dir()
    assert (target / "extracts").is_dir()
    assert (target / "outputs").is_dir()
    assert (target / "bib").is_dir()


def test_resolve_review_dir_defaults_to_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    paths = resolve_review_dir(explicit=None)
    assert paths.root == tmp_path


def test_resolve_review_dir_honors_env_var(tmp_path, monkeypatch):
    target = tmp_path / "from-env"
    target.mkdir()
    monkeypatch.setenv("SCRIPTORIUM_REVIEW_DIR", str(target))
    paths = resolve_review_dir(explicit=None)
    assert paths.root == target
