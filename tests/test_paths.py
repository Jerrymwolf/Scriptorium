from pathlib import Path
from scriptorium.paths import resolve_review_dir, ReviewPaths


def test_resolve_review_dir_uses_explicit_path(tmp_path):
    target = tmp_path / "my-review"
    target.mkdir()
    paths = resolve_review_dir(explicit=target)
    assert paths.root == target
    assert paths.evidence == target / "data" / "evidence.jsonl"
    assert paths.audit_md == target / "audit" / "audit.md"


def test_resolve_review_dir_creates_subdirs(tmp_path):
    target = tmp_path / "my-review"
    paths = resolve_review_dir(explicit=target, create=True)
    assert (target / "sources" / "pdfs").is_dir()
    assert (target / "sources" / "papers").is_dir()
    assert (target / "data" / "extracts").is_dir()
    assert (target / "audit" / "overview-archive").is_dir()
    assert (target / ".scriptorium").is_dir()


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


def test_review_paths_has_scope_property(tmp_path):
    from scriptorium.paths import ReviewPaths
    paths = ReviewPaths(root=tmp_path)
    assert paths.scope == tmp_path / "scope.json"
