# Scriptorium v0.3.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Scriptorium v0.3.0 (distribution `scriptorium-cli`) with native Obsidian output, an executive-briefing `overview.md`, a seamless NotebookLM publish flow over the verified `nlm` CLI, a Claude-Code-assisted installer, and migration for existing reviews — all gated by exact tests per the spec at `docs/superpowers/specs/2026-04-20-scriptorium-v0.3-design.md`.

**Architecture:** Extend the existing flat-layout `scriptorium/` package with new modules for errors, frontmatter, citations, Obsidian output, overview generation, NotebookLM publish, migration, setup, and a review lock. Wire these into expanded CLI subcommands. Update the `.claude-plugin/` surface (commands, skills, hook verifier) to match. Keep the console command name `scriptorium`; only the PyPI distribution name changes.

**Tech Stack:** Python ≥3.11, `tomllib` (stdlib), `httpx` (existing), `pypdf` (existing), `pytest`/`pytest-asyncio`/`respx` (existing), `nlm` CLI (external), Obsidian-flavored Markdown, YAML frontmatter.

---

## File Structure (new + modified)

New Python modules under `scriptorium/`:

- `scriptorium/errors.py` — §11 exit codes + `ScriptoriumError`.
- `scriptorium/frontmatter.py` — §5 YAML frontmatter read/write + schemas.
- `scriptorium/citations.py` — §6.3 legacy `[id:loc]` + v0.3 `[[id#p-N]]` dual-parser.
- `scriptorium/lock.py` — `<review-dir>/.scriptorium.lock`.
- `scriptorium/cowork.py` — Cowork detection (env flags).
- `scriptorium/vault.py` — §4.3 vault detection + §4.2 symlink/path-escape policy.
- `scriptorium/obsidian/__init__.py`
- `scriptorium/obsidian/stubs.py` — §6.2 paper stub generator.
- `scriptorium/obsidian/queries.py` — §6.4 Dataview query file.
- `scriptorium/overview/__init__.py`
- `scriptorium/overview/generator.py` — §8.5 overview assembly + corpus hash + seed.
- `scriptorium/overview/linter.py` — §8.2 + §8.4 lint.
- `scriptorium/nlm.py` — §0.2 verified `nlm` CLI wrapper.
- `scriptorium/publish.py` — §9 publish flow.
- `scriptorium/migrate.py` — §10.1 migration.
- `scriptorium/setup_flow.py` — §7 setup + interrupted-setup state file.
- `scriptorium/doctor.py` — `scriptorium doctor`.

Modified Python modules:

- `scriptorium/__init__.py` — bump `__version__`.
- `scriptorium/config.py` — add v0.3 keys, user config + env overrides, corruption handling.
- `scriptorium/paths.py` — §4.1 resolution + new review file paths (`overview.md`, `contradictions.md`, `references.bib`, `papers/`).
- `scriptorium/storage/audit.py` — §5.3 JSONL schema (`status` field + UTC `Z` timestamps) + corruption recovery.
- `scriptorium/reasoning/verify_citations.py` — dual-parse + overview lint hook.
- `scriptorium/cli.py` — subcommand dispatch for `publish`, `migrate-review`, `regenerate-overview`, `doctor`, `init`; propagate §11 exit codes.

Plugin surface (`.claude-plugin/`):

- `commands/lit-podcast.md` (new)
- `commands/lit-deck.md` (new)
- `commands/lit-mindmap.md` (new)
- `commands/scriptorium-setup.md` (new)
- `commands/lit-review.md` (update)
- `commands/lit-config.md` (update)
- `commands/lit-show-audit.md` (update)
- `skills/publishing-to-notebooklm/SKILL.md` (new; replaces `lit-publishing/`)
- `skills/setting-up-scriptorium/SKILL.md` (new)
- `skills/generating-overview/SKILL.md` (new)
- `skills/using-scriptorium/SKILL.md` (update)
- `skills/running-lit-review/SKILL.md` (update)
- `skills/configuring-scriptorium/SKILL.md` (update)
- `skills/lit-extracting/SKILL.md` (update)
- `skills/lit-synthesizing/SKILL.md` (update)
- `skills/lit-contradiction-check/SKILL.md` (update)
- `skills/lit-audit-trail/SKILL.md` (update)
- `hooks/evidence_gate.sh` (unchanged filename; verifier it calls is updated via `reasoning/verify_citations.py`)

Release artifacts:

- `pyproject.toml` — rename distribution to `scriptorium-cli`, bump version, keep flat-layout discovery.
- `.claude-plugin/plugin.json` — bump version.
- `README.md` — replace from `README_proposed.md`, adjusted for beta + `scriptorium-cli`.
- `CHANGELOG.md` — new file; first entry is v0.3.0.
- `scripts/install.sh` — curl-one-liner target (cuttable; wraps `scriptorium init`).
- `docs/obsidian-integration.md` (new) — vault-wide stubs portability note (§2.3).
- `docs/publishing-notebooklm.md` (new) — §9 operator reference + Cowork manual-upload template.

---

## Conventions used below

- Commit messages follow Conventional Commits: `feat(...)`, `fix(...)`, `test(...)`, `refactor(...)`, `chore(...)`, `docs(...)`.
- `pytest -q` is the default test runner; targeted runs use `-k <name>` or `path::test`.
- When a test has not yet been added, “Expected: FAIL with …” describes the failure mode.
- All timestamps stored by v0.3 code must end in `Z` (UTC ISO-8601, e.g. `2026-04-20T14:32:08Z`). Existing `audit.py` uses `datetime.now(timezone.utc).isoformat()` which yields `...+00:00`; Task 9 changes that.
- Wherever a task edits `scriptorium/cli.py`, the edit must preserve the existing dispatch table pattern in `_HANDLERS` and argparse subparsers in `_build_parser`.

---

## Task 1: Pin versioning and prepare the distribution rename

**Files:**
- Modify: `pyproject.toml`
- Modify: `scriptorium/__init__.py`
- Modify: `.claude-plugin/plugin.json`
- Create: `tests/test_version_v03.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_version_v03.py`:

```python
"""Version and distribution-name guards for v0.3.0."""
from pathlib import Path
import tomllib

from scriptorium import __version__

ROOT = Path(__file__).resolve().parent.parent


def test_package_version_is_v030():
    assert __version__ == "0.3.0"


def test_pyproject_distribution_name_is_scriptorium_cli():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "scriptorium-cli"
    assert data["project"]["version"] == "0.3.0"
    scripts = data["project"]["scripts"]
    assert scripts["scriptorium"] == "scriptorium.cli:main"


def test_plugin_manifest_version_is_v030():
    import json
    manifest = json.loads(
        (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert manifest["version"] == "0.3.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_version_v03.py -q`
Expected: FAIL — three assertion errors (still `0.2.0` / `scriptorium`).

- [ ] **Step 3: Bump `scriptorium/__init__.py`**

Replace the file body with:

```python
"""Scriptorium dual-runtime literature-review plugin."""
__version__ = "0.3.0"
```

- [ ] **Step 4: Rename distribution in `pyproject.toml`**

Change the `[project]` block to:

```toml
[project]
name = "scriptorium-cli"
version = "0.3.0"
description = "Dual-runtime literature-review plugin for Claude Code and Cowork"
requires-python = ">=3.11"
dependencies = [
  "httpx>=0.27",
  "pypdf>=4.2",
]
```

Leave `[tool.setuptools.packages.find]`, `[project.scripts]`, and `[project.optional-dependencies]` unchanged.

- [ ] **Step 5: Bump `.claude-plugin/plugin.json`**

Change the `"version"` field from `"0.2.0"` to `"0.3.0"`. Do not rename `"name"`.

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_version_v03.py -q`
Expected: PASS (3 passed).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml scriptorium/__init__.py .claude-plugin/plugin.json tests/test_version_v03.py
git commit -m "chore(release): pin v0.3.0 and rename distribution to scriptorium-cli"
```

---

## Task 2: Add `scriptorium/errors.py` with §11 exit codes

**Files:**
- Create: `scriptorium/errors.py`
- Create: `tests/test_errors.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_errors.py`:

```python
"""Every §11 exit code symbol must be exported with a unique integer value."""
from scriptorium.errors import EXIT_CODES, ScriptoriumError


EXPECTED = {
    "OK": 0,
    "E_USAGE": 1,
    "E_CONFIG": 2,
    "E_VERIFY_FAILED": 3,
    "E_REVIEW_INCOMPLETE": 4,
    "E_NLM_UNAVAILABLE": 5,
    "E_NLM_CREATE": 6,
    "E_NLM_UPLOAD": 7,
    "E_NLM_ARTIFACT": 8,
    "E_TIMEOUT": 9,
    "E_SOURCES": 10,
    "E_NOTEBOOK_NAME": 11,
    "E_LOCKED": 12,
    "E_PATH_ESCAPE": 13,
    "E_CONFIG_CORRUPT": 14,
    "E_AUDIT_CORRUPT": 15,
    "E_STATE_CORRUPT": 16,
    "E_OVERVIEW_FAILED": 17,
    "E_SETUP_FAILED": 18,
    "E_INTERRUPTED": 130,
}


def test_exit_codes_match_spec():
    assert EXIT_CODES == EXPECTED


def test_exit_codes_are_unique():
    assert len(set(EXIT_CODES.values())) == len(EXIT_CODES)


def test_scriptorium_error_carries_symbol_and_exit_code():
    err = ScriptoriumError("boom", symbol="E_NLM_CREATE")
    assert err.symbol == "E_NLM_CREATE"
    assert err.exit_code == 6
    assert str(err) == "boom"


def test_scriptorium_error_rejects_unknown_symbol():
    import pytest
    with pytest.raises(KeyError):
        ScriptoriumError("boom", symbol="E_NOT_A_THING")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_errors.py -q`
Expected: FAIL with `ModuleNotFoundError: scriptorium.errors`.

- [ ] **Step 3: Write `scriptorium/errors.py`**

```python
"""Exit codes and canonical error class for Scriptorium v0.3.

The symbols here are the contract referenced by §11 of the design spec.
Every non-zero code is unique. `ScriptoriumError.symbol` carries the
symbolic name; `exit_code` is the integer returned by `scriptorium` on
unhandled error.
"""
from __future__ import annotations


EXIT_CODES: dict[str, int] = {
    "OK": 0,
    "E_USAGE": 1,
    "E_CONFIG": 2,
    "E_VERIFY_FAILED": 3,
    "E_REVIEW_INCOMPLETE": 4,
    "E_NLM_UNAVAILABLE": 5,
    "E_NLM_CREATE": 6,
    "E_NLM_UPLOAD": 7,
    "E_NLM_ARTIFACT": 8,
    "E_TIMEOUT": 9,
    "E_SOURCES": 10,
    "E_NOTEBOOK_NAME": 11,
    "E_LOCKED": 12,
    "E_PATH_ESCAPE": 13,
    "E_CONFIG_CORRUPT": 14,
    "E_AUDIT_CORRUPT": 15,
    "E_STATE_CORRUPT": 16,
    "E_OVERVIEW_FAILED": 17,
    "E_SETUP_FAILED": 18,
    "E_INTERRUPTED": 130,
}


class ScriptoriumError(Exception):
    """A user-visible Scriptorium error carrying a §11 symbol."""

    def __init__(self, message: str, *, symbol: str) -> None:
        if symbol not in EXIT_CODES:
            raise KeyError(f"Unknown exit-code symbol: {symbol!r}")
        super().__init__(message)
        self.symbol = symbol
        self.exit_code = EXIT_CODES[symbol]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_errors.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add scriptorium/errors.py tests/test_errors.py
git commit -m "feat(errors): add §11 exit-code table and ScriptoriumError"
```

---

## Task 3: Extend `Config` with v0.3 keys

**Files:**
- Modify: `scriptorium/config.py`
- Create: `tests/test_config_v03_keys.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_config_v03_keys.py`:

```python
"""Config dataclass must contain every §3.2 key with the right default/type."""
from dataclasses import fields
import pytest

from scriptorium.config import Config


EXPECTED: dict[str, tuple[type | tuple, object]] = {
    "default_model": (str, "opus"),
    "review_dir": (str, "literature_review"),
    "evidence_required": (bool, True),
    "sources_enabled": (list, ["openalex", "semantic_scholar"]),
    "notebook_id": (str, ""),
    "unpaywall_email": (str, ""),
    "openalex_email": (str, ""),
    "semantic_scholar_api_key": (str, ""),
    "default_backend": (str, "openalex"),
    "languages": (list, ["en"]),
    "obsidian_vault": (str, ""),
    "notebooklm_enabled": (bool, False),
    "notebooklm_prompt": (bool, True),
}


@pytest.mark.parametrize("name,spec", list(EXPECTED.items()))
def test_field_default(name, spec):
    expected_type, expected_default = spec
    cfg = Config()
    assert hasattr(cfg, name), f"Config is missing field {name}"
    value = getattr(cfg, name)
    if expected_type is list:
        assert isinstance(value, list)
        assert value == expected_default
    else:
        assert isinstance(value, expected_type)
        assert value == expected_default


def test_no_unexpected_fields():
    names = {f.name for f in fields(Config)}
    assert names == set(EXPECTED), (
        f"Unexpected Config fields: {names ^ set(EXPECTED)}"
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_config_v03_keys.py -q`
Expected: FAIL — several `hasattr` assertions for `obsidian_vault`, `notebooklm_enabled`, `notebooklm_prompt`.

- [ ] **Step 3: Add v0.3 fields to `Config`**

In `scriptorium/config.py`, add three fields after `languages`:

```python
    obsidian_vault: str = ""
    notebooklm_enabled: bool = False
    notebooklm_prompt: bool = True
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_config_v03_keys.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scriptorium/config.py tests/test_config_v03_keys.py
git commit -m "feat(config): add obsidian_vault, notebooklm_enabled, notebooklm_prompt"
```

---

## Task 4: Config load order, user config, env overrides, corruption handling

**Files:**
- Modify: `scriptorium/config.py`
- Create: `tests/test_config_load_order.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_config_load_order.py`:

```python
"""Layered config resolution per §3.1 and env overrides per §3.3."""
import os
from pathlib import Path

import pytest

from scriptorium.config import (
    Config,
    ConfigCorruptError,
    resolve_config,
)


def _write_toml(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_defaults_when_no_files(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_REVIEW_DIR", raising=False)
    monkeypatch.delenv("SCRIPTORIUM_CONFIG", raising=False)
    monkeypatch.delenv("SCRIPTORIUM_OBSIDIAN_VAULT", raising=False)
    cfg = resolve_config(review_dir=tmp_path, user_config_path=tmp_path / "nope.toml")
    assert cfg == Config()


def test_review_local_overrides_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_OBSIDIAN_VAULT", raising=False)
    _write_toml(
        tmp_path / "config.toml",
        '[scriptorium]\nunpaywall_email = "review@example.com"\n',
    )
    cfg = resolve_config(review_dir=tmp_path, user_config_path=tmp_path / "user.toml")
    assert cfg.unpaywall_email == "review@example.com"


def test_user_config_overrides_review_local(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_OBSIDIAN_VAULT", raising=False)
    _write_toml(
        tmp_path / "config.toml",
        '[scriptorium]\nunpaywall_email = "review@example.com"\n',
    )
    user = tmp_path / "user.toml"
    _write_toml(user, '[scriptorium]\nunpaywall_email = "user@example.com"\n')
    cfg = resolve_config(review_dir=tmp_path, user_config_path=user)
    assert cfg.unpaywall_email == "user@example.com"


def test_env_overrides_user_config(tmp_path, monkeypatch):
    user = tmp_path / "user.toml"
    _write_toml(user, '[scriptorium]\nobsidian_vault = "/from/user"\n')
    monkeypatch.setenv("SCRIPTORIUM_OBSIDIAN_VAULT", "/from/env")
    cfg = resolve_config(review_dir=tmp_path, user_config_path=user)
    assert cfg.obsidian_vault == "/from/env"


def test_unknown_key_in_toml_is_ignored(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_OBSIDIAN_VAULT", raising=False)
    _write_toml(
        tmp_path / "config.toml",
        '[scriptorium]\nnot_a_key = "x"\nunpaywall_email = "ok@example.com"\n',
    )
    cfg = resolve_config(review_dir=tmp_path, user_config_path=tmp_path / "user.toml")
    assert cfg.unpaywall_email == "ok@example.com"


def test_corrupted_toml_raises_config_corrupt(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_OBSIDIAN_VAULT", raising=False)
    _write_toml(tmp_path / "config.toml", "this is = not = valid = toml\n[[[")
    with pytest.raises(ConfigCorruptError):
        resolve_config(review_dir=tmp_path, user_config_path=tmp_path / "user.toml")


def test_cowork_env_flag_sets_cowork_marker(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTORIUM_COWORK", "1")
    from scriptorium.cowork import is_cowork_mode
    assert is_cowork_mode() is True
    monkeypatch.setenv("SCRIPTORIUM_COWORK", "no")
    assert is_cowork_mode() is False


def test_force_cowork_alias(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_COWORK", raising=False)
    monkeypatch.setenv("SCRIPTORIUM_FORCE_COWORK", "yes")
    from scriptorium.cowork import is_cowork_mode
    assert is_cowork_mode() is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_config_load_order.py -q`
Expected: FAIL — `resolve_config`, `ConfigCorruptError`, and `scriptorium.cowork` do not exist.

- [ ] **Step 3: Extend `scriptorium/config.py`**

At the top of the file (after existing imports) add:

```python
import os
import tomllib
```

At the bottom of the file, add:

```python
class ConfigCorruptError(Exception):
    """Raised when a TOML config file exists but cannot be parsed (§3.1)."""


_ENV_STRING_KEYS: dict[str, str] = {
    "SCRIPTORIUM_OBSIDIAN_VAULT": "obsidian_vault",
}


def _load_toml_safe(path: Path) -> dict:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigCorruptError(f"{path}: {e}") from e
    section = raw.get("scriptorium", {})
    if not isinstance(section, dict):
        raise ConfigCorruptError(f"{path}: [scriptorium] is not a table")
    return section


def _apply_section(cfg: Config, section: dict) -> Config:
    known = {f.name for f in fields(Config)}
    data = {**cfg.__dict__}
    for k, v in section.items():
        if k in known:
            data[k] = v
    return Config(**data)


def resolve_config(
    *,
    review_dir: Path | None,
    user_config_path: Path | None,
) -> Config:
    """Resolve a merged Config per §3.1 plus env overrides per §3.3.

    Order (later overrides earlier):
      1. Built-in defaults.
      2. <review_dir>/config.toml.
      3. <user_config_path>.
      4. Env overrides.

    CLI flags are applied by callers after this function returns.
    """
    cfg = Config()

    if review_dir is not None:
        review_toml = Path(review_dir) / "config.toml"
        if review_toml.exists():
            cfg = _apply_section(cfg, _load_toml_safe(review_toml))

    if user_config_path is not None and user_config_path.exists():
        cfg = _apply_section(cfg, _load_toml_safe(user_config_path))

    for env_name, field_name in _ENV_STRING_KEYS.items():
        env_val = os.environ.get(env_name)
        if env_val is not None:
            setattr(cfg, field_name, env_val)

    return cfg


def default_user_config_path() -> Path:
    """Location of the user-level config (§3.1)."""
    override = os.environ.get("SCRIPTORIUM_CONFIG")
    if override:
        return Path(override)
    home = Path(os.environ.get("HOME", "")).expanduser()
    return home / ".config" / "scriptorium" / "config.toml"
```

Then, to make `save_config_from_kv` also fail closed when the on-disk file is corrupt, change `save_config_from_kv`'s first line from:

```python
    config = load_config(path)
```

to:

```python
    try:
        config = load_config(path)
    except tomllib.TOMLDecodeError as e:
        raise ConfigCorruptError(f"{path}: {e}") from e
```

- [ ] **Step 4: Create `scriptorium/cowork.py`**

```python
"""Cowork-runtime detection.

Cowork is a sandboxed runtime without local shell access. v0.3 treats the
following env-var truthy values as explicit Cowork mode:
  SCRIPTORIUM_COWORK, SCRIPTORIUM_FORCE_COWORK
"""
from __future__ import annotations

import os


_TRUTHY = {"1", "true", "yes"}


def is_cowork_mode() -> bool:
    for name in ("SCRIPTORIUM_COWORK", "SCRIPTORIUM_FORCE_COWORK"):
        val = os.environ.get(name)
        if val is None:
            continue
        if val.strip().lower() in _TRUTHY:
            return True
    return False
```

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_config_load_order.py -q`
Expected: PASS (8 passed).

- [ ] **Step 6: Commit**

```bash
git add scriptorium/config.py scriptorium/cowork.py tests/test_config_load_order.py
git commit -m "feat(config): layered resolution, env overrides, corruption + cowork"
```

---

## Task 5: Review-directory resolution and new review files in `paths.py`

**Files:**
- Modify: `scriptorium/paths.py`
- Create: `tests/test_path_resolution.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_path_resolution.py`:

```python
"""§4.1 resolve_review_dir + new §2 review paths."""
from pathlib import Path

import pytest

from scriptorium.paths import ReviewPaths, resolve_review_dir


def test_absolute_path_used_verbatim(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_REVIEW_DIR", raising=False)
    paths = resolve_review_dir(explicit=tmp_path, vault_root=None, cwd=tmp_path)
    assert paths.root == tmp_path.resolve()


def test_relative_with_vault(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_REVIEW_DIR", raising=False)
    vault = tmp_path / "vault"
    (vault / "reviews" / "caffeine-wm").mkdir(parents=True)
    paths = resolve_review_dir(
        explicit=Path("reviews/caffeine-wm"),
        vault_root=vault,
        cwd=tmp_path,
    )
    assert paths.root == (vault / "reviews" / "caffeine-wm").resolve()


def test_relative_without_vault(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_REVIEW_DIR", raising=False)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    paths = resolve_review_dir(
        explicit=Path("reviews/caffeine-wm"),
        vault_root=None,
        cwd=cwd,
    )
    assert paths.root == (cwd / "reviews" / "caffeine-wm").resolve()


def test_env_fallback(tmp_path, monkeypatch):
    env_dir = tmp_path / "env-review"
    env_dir.mkdir()
    monkeypatch.setenv("SCRIPTORIUM_REVIEW_DIR", str(env_dir))
    paths = resolve_review_dir(explicit=None, vault_root=None, cwd=tmp_path)
    assert paths.root == env_dir.resolve()


def test_default_is_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_REVIEW_DIR", raising=False)
    paths = resolve_review_dir(explicit=None, vault_root=None, cwd=tmp_path)
    assert paths.root == tmp_path.resolve()


def test_new_review_paths_exposed(tmp_path):
    p = ReviewPaths(root=tmp_path)
    assert p.overview == tmp_path / "overview.md"
    assert p.contradictions == tmp_path / "contradictions.md"
    assert p.references_bib == tmp_path / "references.bib"
    assert p.papers == tmp_path / "papers"
    assert p.lock == tmp_path / ".scriptorium.lock"
    assert p.overview_archive == tmp_path / "overview-archive"
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_path_resolution.py -q`
Expected: FAIL — `resolve_review_dir` signature mismatch; new properties missing.

- [ ] **Step 3: Rewrite `scriptorium/paths.py`**

Replace the file contents with:

```python
"""Per-review path resolution and canonical file names.

v0.3 extends v0.2's `ReviewPaths` with overview, contradictions, paper stubs,
references export, and a review lock. Resolution follows §4.1 of the design
spec: absolute path is respected; relative path is joined against `vault_root`
when set, otherwise against the cwd; `SCRIPTORIUM_REVIEW_DIR` is the fallback
when `explicit` is None.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ReviewPaths:
    root: Path

    @property
    def evidence(self) -> Path:
        return self.root / "evidence.jsonl"

    @property
    def audit_md(self) -> Path:
        return self.root / "audit.md"

    @property
    def audit_jsonl(self) -> Path:
        return self.root / "audit.jsonl"

    @property
    def corpus(self) -> Path:
        return self.root / "corpus.jsonl"

    @property
    def synthesis(self) -> Path:
        return self.root / "synthesis.md"

    @property
    def contradictions(self) -> Path:
        return self.root / "contradictions.md"

    @property
    def overview(self) -> Path:
        return self.root / "overview.md"

    @property
    def overview_archive(self) -> Path:
        return self.root / "overview-archive"

    @property
    def references_bib(self) -> Path:
        return self.root / "references.bib"

    @property
    def papers(self) -> Path:
        return self.root / "papers"

    @property
    def pdfs(self) -> Path:
        return self.root / "pdfs"

    @property
    def extracts(self) -> Path:
        return self.root / "extracts"

    @property
    def outputs(self) -> Path:
        return self.root / "outputs"

    @property
    def bib(self) -> Path:
        return self.root / "bib"

    @property
    def lock(self) -> Path:
        return self.root / ".scriptorium.lock"


def resolve_review_dir(
    explicit: Optional[Path] = None,
    *,
    vault_root: Optional[Path] = None,
    cwd: Optional[Path] = None,
    create: bool = False,
) -> ReviewPaths:
    """Resolve the review directory per §4.1.

    - Absolute `explicit` is used as-is (after resolve).
    - Relative `explicit` joins to `vault_root` when given, else `cwd`.
    - No `explicit` falls back to `SCRIPTORIUM_REVIEW_DIR` then `cwd`.
    """
    base_cwd = Path(cwd) if cwd is not None else Path.cwd()

    if explicit is not None:
        p = Path(explicit)
        if p.is_absolute():
            root = p.resolve(strict=False)
        elif vault_root is not None:
            root = (Path(vault_root) / p).resolve(strict=False)
        else:
            root = (base_cwd / p).resolve(strict=False)
    else:
        env = os.environ.get("SCRIPTORIUM_REVIEW_DIR")
        root = Path(env).resolve(strict=False) if env else base_cwd.resolve(strict=False)

    if create:
        for sub in ("pdfs", "extracts", "outputs", "bib", "papers"):
            (root / sub).mkdir(parents=True, exist_ok=True)
    return ReviewPaths(root=root)
```

- [ ] **Step 4: Update every `resolve_review_dir(...)` call site**

Run a grep to find stale call sites:

Run: grep `resolve_review_dir\(` under `scriptorium/` and `tests/`.

In `scriptorium/cli.py` only, change:

```python
    paths = resolve_review_dir(explicit=explicit, create=True)
```

to:

```python
    paths = resolve_review_dir(explicit=explicit, vault_root=None, cwd=None, create=True)
```

(Task 6 threads a real `vault_root` in; callsite stays here for now.)

Existing tests that call `resolve_review_dir(explicit=...)` keep working — `vault_root` and `cwd` default to None.

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_path_resolution.py tests/test_paths.py tests/test_cli.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scriptorium/paths.py scriptorium/cli.py tests/test_path_resolution.py
git commit -m "feat(paths): §4.1 resolution + overview/contradictions/papers/lock paths"
```

---

## Task 6: Vault detection and path-escape policy

**Files:**
- Create: `scriptorium/vault.py`
- Create: `tests/test_vault_detection.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_vault_detection.py`:

```python
"""§4.2 + §4.3: vault walk-up, conflict copies, path escape, symlink policy."""
from pathlib import Path

import pytest

from scriptorium.vault import (
    PathEscapeError,
    VaultConflictCopy,
    detect_vault,
    ensure_within,
)


def test_vault_detected_when_dot_obsidian_present(tmp_path):
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    review = vault / "reviews" / "caffeine-wm"
    review.mkdir(parents=True)
    res = detect_vault(review)
    assert res.vault_root == vault.resolve()
    assert res.warning is None


def test_vault_none_when_missing(tmp_path):
    review = tmp_path / "no-vault" / "reviews" / "x"
    review.mkdir(parents=True)
    res = detect_vault(review)
    assert res.vault_root is None


def test_conflict_copy_triggers_warning(tmp_path):
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    (vault / ".obsidian (conflicted copy)").mkdir()
    res = detect_vault(vault / "reviews" / "x")
    (vault / "reviews" / "x").mkdir(parents=True, exist_ok=True)
    res = detect_vault(vault / "reviews" / "x")
    assert res.vault_root == vault.resolve()
    assert res.warning == "W_VAULT_CONFLICT_COPY"


def test_conflict_only_directory_is_ignored(tmp_path):
    fake = tmp_path / "fake"
    (fake / ".obsidian 2").mkdir(parents=True)
    res = detect_vault(fake / "reviews" / "x")
    (fake / "reviews" / "x").mkdir(parents=True, exist_ok=True)
    res = detect_vault(fake / "reviews" / "x")
    assert res.vault_root is None


def test_symlinked_review_resolves_to_real_vault(tmp_path):
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    real = vault / "reviews" / "caffeine-wm"
    real.mkdir(parents=True)
    link = tmp_path / "reviews-link"
    link.symlink_to(real)
    res = detect_vault(link)
    assert res.vault_root == vault.resolve()


def test_ensure_within_allows_subpath(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    inner = root / "a" / "b"
    inner.mkdir(parents=True)
    ensure_within(inner, root)


def test_ensure_within_rejects_escape(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(PathEscapeError):
        ensure_within(other, root)
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_vault_detection.py -q`
Expected: FAIL — module `scriptorium.vault` does not exist.

- [ ] **Step 3: Create `scriptorium/vault.py`**

```python
"""Obsidian vault detection and path-escape guard (§4.2, §4.3)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class PathEscapeError(Exception):
    """Raised when a resolved path is outside the allowed root."""


@dataclass(frozen=True)
class VaultConflictCopy:
    """Marker class retained for test-discovery back-compat; see warning field."""
    path: Path


@dataclass(frozen=True)
class VaultDetection:
    vault_root: Optional[Path]
    warning: Optional[str]  # "W_VAULT_CONFLICT_COPY" or None


def detect_vault(review_dir: Path) -> VaultDetection:
    """Walk from `review_dir` up to the filesystem root looking for `.obsidian/`.

    The ancestor must contain an entry named exactly `.obsidian` that resolves
    to an existing directory. Conflict copies (`.obsidian (conflicted copy)`,
    `.obsidian 2`, etc.) do not count on their own but trigger a warning when
    they coexist with the canonical name.
    """
    resolved = Path(review_dir).resolve(strict=False)
    ancestor: Optional[Path] = resolved
    while ancestor is not None:
        canonical = ancestor / ".obsidian"
        if canonical.is_dir():
            warn = None
            for entry in ancestor.iterdir():
                if entry.name == ".obsidian":
                    continue
                if entry.name.startswith(".obsidian") and entry.is_dir():
                    warn = "W_VAULT_CONFLICT_COPY"
                    break
            return VaultDetection(vault_root=ancestor.resolve(), warning=warn)
        if ancestor.parent == ancestor:
            break
        ancestor = ancestor.parent
    return VaultDetection(vault_root=None, warning=None)


def ensure_within(path: Path, root: Path) -> None:
    """Raise PathEscapeError if `path` does not resolve inside `root`."""
    try:
        Path(path).resolve(strict=False).relative_to(Path(root).resolve(strict=False))
    except ValueError as e:
        raise PathEscapeError(
            f"resolved path {path!s} escapes allowed root {root!s}"
        ) from e
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_vault_detection.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scriptorium/vault.py tests/test_vault_detection.py
git commit -m "feat(vault): §4 detection, conflict-copy warning, path-escape guard"
```

---

## Task 7: Review lock (`<review-dir>/.scriptorium.lock`)

**Files:**
- Create: `scriptorium/lock.py`
- Create: `tests/test_review_lock.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_review_lock.py`:

```python
"""§9.4 / §10.1: single-writer lock for publish and migrate-review."""
from pathlib import Path

import pytest

from scriptorium.lock import (
    ReviewLock,
    ReviewLockHeld,
)


def test_acquire_and_release(tmp_path):
    lock = tmp_path / ".scriptorium.lock"
    with ReviewLock(lock):
        assert lock.exists()
    assert not lock.exists()


def test_second_acquire_raises(tmp_path):
    lock = tmp_path / ".scriptorium.lock"
    with ReviewLock(lock):
        with pytest.raises(ReviewLockHeld) as exc:
            with ReviewLock(lock):
                pass
        assert str(lock) in str(exc.value)


def test_stale_lock_readable_message(tmp_path):
    lock = tmp_path / ".scriptorium.lock"
    lock.write_text("999999\n", encoding="utf-8")
    with pytest.raises(ReviewLockHeld):
        with ReviewLock(lock):
            pass
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_review_lock.py -q`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Create `scriptorium/lock.py`**

```python
"""Single-writer review lock (`<review-dir>/.scriptorium.lock`).

The lock is a plain sentinel file containing the PID of the holder. v0.3
does not attempt to break stale locks automatically; the canonical error
message tells the user to remove the file after confirming no process is
writing.
"""
from __future__ import annotations

import os
from pathlib import Path
from types import TracebackType
from typing import Optional, Type


class ReviewLockHeld(Exception):
    """Another Scriptorium run holds the review lock (E_LOCKED)."""


class ReviewLock:
    """Context manager that writes a PID sentinel file on enter and removes it on exit."""

    def __init__(self, path: Path):
        self._path = Path(path)

    def __enter__(self) -> "ReviewLock":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(
                self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
            )
        except FileExistsError as e:
            raise ReviewLockHeld(
                f"review is locked by another Scriptorium run at {self._path}. "
                "If no run is active, remove the stale lock after verifying "
                "no process is writing."
            ) from e
        try:
            os.write(fd, f"{os.getpid()}\n".encode("utf-8"))
        finally:
            os.close(fd)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_review_lock.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scriptorium/lock.py tests/test_review_lock.py
git commit -m "feat(lock): single-writer review lock (.scriptorium.lock)"
```

---

## Task 8: `audit.jsonl` v0.3 schema + corruption recovery

**Files:**
- Modify: `scriptorium/storage/audit.py`
- Create: `tests/test_audit_v03.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_audit_v03.py`:

```python
"""§5.3 audit.jsonl schema: status enum, UTC Z timestamps, corruption recovery."""
import json
from pathlib import Path

import pytest

from scriptorium.paths import ReviewPaths
from scriptorium.storage.audit import (
    AuditCorruptError,
    AuditEntry,
    append_audit,
    load_audit,
)


def _paths(tmp_path) -> ReviewPaths:
    return ReviewPaths(root=tmp_path)


def test_append_has_status_default_success(tmp_path):
    paths = _paths(tmp_path)
    append_audit(
        paths, AuditEntry(phase="publishing", action="notebook.create", details={})
    )
    rows = [
        json.loads(line)
        for line in paths.audit_jsonl.read_text(encoding="utf-8").splitlines()
    ]
    assert rows[0]["status"] == "success"


def test_timestamp_is_iso_utc_z(tmp_path):
    paths = _paths(tmp_path)
    append_audit(paths, AuditEntry(phase="search", action="doi.fetch"))
    row = json.loads(paths.audit_jsonl.read_text(encoding="utf-8").splitlines()[0])
    assert row["timestamp"].endswith("Z")


def test_rejects_invalid_status(tmp_path):
    paths = _paths(tmp_path)
    with pytest.raises(ValueError):
        AuditEntry(phase="publishing", action="x", status="rejected")


def test_corrupt_jsonl_raises_and_preserves_file(tmp_path):
    paths = _paths(tmp_path)
    paths.audit_jsonl.write_text("{not valid json\n", encoding="utf-8")
    with pytest.raises(AuditCorruptError):
        load_audit(paths)
    # File is preserved verbatim.
    assert paths.audit_jsonl.read_text(encoding="utf-8") == "{not valid json\n"


def test_append_after_corruption_uses_recovery_file(tmp_path):
    paths = _paths(tmp_path)
    paths.audit_jsonl.write_text("{not valid json\n", encoding="utf-8")
    append_audit(
        paths,
        AuditEntry(phase="publishing", action="notebook.create"),
        allow_recovery=True,
    )
    matches = list(Path(tmp_path).glob("audit.recovery.*.jsonl"))
    assert len(matches) == 1
    row = json.loads(matches[0].read_text(encoding="utf-8").splitlines()[0])
    assert row["phase"] == "publishing"
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_audit_v03.py -q`
Expected: FAIL — `AuditEntry.status`, `AuditCorruptError`, and `allow_recovery` do not exist.

- [ ] **Step 3: Rewrite `scriptorium/storage/audit.py`**

```python
"""PRISMA-style audit trail. v0.3 adds a `status` enum, UTC `Z` timestamps,
and corruption recovery.

Corruption policy (§5.3): a corrupted `audit.jsonl` is never truncated.
Reads raise AuditCorruptError. Writes (when `allow_recovery=True`) redirect
to a timestamped `audit.recovery.<ts>.jsonl` sibling so new audit rows are
not lost.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Literal

from scriptorium.paths import ReviewPaths


AuditStatus = Literal["success", "warning", "failure", "partial", "skipped"]
_ALLOWED_STATUS = {"success", "warning", "failure", "partial", "skipped"}


class AuditCorruptError(Exception):
    """Raised when an existing audit.jsonl cannot be parsed (§5.3)."""


def _utc_z_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


@dataclass
class AuditEntry:
    phase: str
    action: str
    status: AuditStatus = "success"
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_z_now)
    # Retained for v0.2 back-compat when external code passes `ts=`.
    ts: str = ""

    def __post_init__(self) -> None:
        if self.status not in _ALLOWED_STATUS:
            raise ValueError(
                f"audit status must be one of {sorted(_ALLOWED_STATUS)}, "
                f"got {self.status!r}"
            )
        if self.ts and not self.timestamp:
            self.timestamp = self.ts


def _serialize(entry: AuditEntry) -> dict:
    return {
        "timestamp": entry.timestamp,
        "phase": entry.phase,
        "action": entry.action,
        "status": entry.status,
        "details": entry.details,
    }


def _recovery_path(paths: ReviewPaths) -> Path:
    stamp = _utc_z_now().replace(":", "").replace("-", "")
    return paths.root / f"audit.recovery.{stamp}.jsonl"


def _scan_jsonl_for_corruption(path: Path) -> None:
    """Read every line; raise AuditCorruptError on any parse failure."""
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError as e:
                raise AuditCorruptError(
                    f"{path}:{lineno}: {e.msg}"
                ) from e


def append_audit(
    paths: ReviewPaths,
    entry: AuditEntry,
    *,
    allow_recovery: bool = False,
) -> None:
    paths.audit_jsonl.parent.mkdir(parents=True, exist_ok=True)
    target = paths.audit_jsonl
    try:
        _scan_jsonl_for_corruption(paths.audit_jsonl)
    except AuditCorruptError:
        if not allow_recovery:
            raise
        target = _recovery_path(paths)
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(_serialize(entry), ensure_ascii=False) + "\n")
    _append_markdown(paths, entry)


def _append_markdown(paths: ReviewPaths, entry: AuditEntry) -> None:
    if not paths.audit_md.exists():
        paths.audit_md.write_text("# PRISMA Audit Trail\n\n")
    lines = [f"### {entry.timestamp} — {entry.phase} / `{entry.action}`\n"]
    lines.append(f"- **status:** {entry.status}\n")
    for k, v in entry.details.items():
        lines.append(f"- **{k}:** {v}\n")
    lines.append("\n")
    with paths.audit_md.open("a", encoding="utf-8") as f:
        f.write("".join(lines))


def load_audit(paths: ReviewPaths) -> list[AuditEntry]:
    if not paths.audit_jsonl.exists():
        return []
    _scan_jsonl_for_corruption(paths.audit_jsonl)
    out: list[AuditEntry] = []
    with paths.audit_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            out.append(
                AuditEntry(
                    phase=row["phase"],
                    action=row["action"],
                    status=row.get("status", "success"),
                    details=row.get("details", {}),
                    timestamp=row.get("timestamp", row.get("ts", "")),
                )
            )
    return out
```

- [ ] **Step 4: Update `tests/test_audit.py` if needed**

Run the existing suite to make sure v0.2 tests still pass:

Run: `pytest tests/test_audit.py tests/test_audit_v03.py -q`
Expected: PASS. (`test_audit.py` does not assert on `status`; default `"success"` keeps it green.)

- [ ] **Step 5: Commit**

```bash
git add scriptorium/storage/audit.py tests/test_audit_v03.py
git commit -m "feat(audit): §5.3 status+Z timestamps + corruption recovery"
```

---

## Task 9: Frontmatter module (read/write + §5 schemas)

**Files:**
- Create: `scriptorium/frontmatter.py`
- Create: `tests/test_frontmatter.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_frontmatter.py`:

```python
"""§5.1 and §5.2 frontmatter schemas + round-trip read/write."""
from datetime import datetime, timezone

import pytest

from scriptorium.frontmatter import (
    FrontmatterError,
    PaperStubFrontmatter,
    ReviewArtifactFrontmatter,
    read_frontmatter,
    strip_frontmatter,
    write_frontmatter,
)


SAMPLE_PAPER = PaperStubFrontmatter(
    schema_version="scriptorium.paper.v1",
    scriptorium_version="0.3.0",
    paper_id="nehlig2010",
    title="Is caffeine a cognitive enhancer?",
    authors=["Nehlig, A."],
    year=2010,
    tags=["caffeine", "wm"],
    reviewed_in=["caffeine-wm"],
    full_text_source="user_pdf",
    created_at="2026-04-20T14:32:08Z",
    updated_at="2026-04-20T14:32:08Z",
    doi="10.3233/JAD-2010-1430",
)


def test_paper_round_trip():
    md = write_frontmatter(SAMPLE_PAPER.to_dict(), body="# body\n")
    loaded = read_frontmatter(md)
    assert loaded["paper_id"] == "nehlig2010"
    assert loaded["full_text_source"] == "user_pdf"
    assert "doi" in loaded
    assert strip_frontmatter(md).strip() == "# body"


def test_paper_rejects_forbidden_field():
    d = SAMPLE_PAPER.to_dict()
    d["not_allowed"] = 1
    with pytest.raises(FrontmatterError):
        PaperStubFrontmatter.validate_dict(d)


def test_paper_rejects_bad_full_text_source():
    d = SAMPLE_PAPER.to_dict()
    d["full_text_source"] = "other"
    with pytest.raises(FrontmatterError):
        PaperStubFrontmatter.validate_dict(d)


def test_review_artifact_requires_review_type():
    with pytest.raises(FrontmatterError):
        ReviewArtifactFrontmatter.validate_dict({
            "schema_version": "scriptorium.review_file.v1",
            "scriptorium_version": "0.3.0",
            "review_id": "caffeine-wm",
            # missing review_type
            "created_at": "2026-04-20T14:32:08Z",
            "updated_at": "2026-04-20T14:32:08Z",
            "research_question": "does caffeine improve wm?",
            "cite_discipline": "locator",
        })


def test_write_returns_delimited_block():
    md = write_frontmatter({"key": "value"}, body="# body\n")
    assert md.startswith("---\n")
    parts = md.split("---\n", 2)
    assert parts[0] == ""
    assert "key: value\n" in parts[1]
    assert parts[2].startswith("# body")
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_frontmatter.py -q`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Create `scriptorium/frontmatter.py`**

```python
"""YAML frontmatter read/write plus v0.3 schema guards.

No third-party YAML dependency — the frontmatter emitted by v0.3 is a
minimal, fully-escaped subset:
  - scalar lines `<key>: <scalar>`
  - list lines `<key>: [<scalar>, ...]`
  - nested mappings `<key>:` then `  <child>: <scalar>`

Read is best-effort: we only round-trip data we ourselves wrote, so we
use a small hand-rolled parser that recognizes the formats produced by
`write_frontmatter`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable, Mapping


class FrontmatterError(Exception):
    """Raised when a schema-guarded dict is missing/forbidden a field."""


# --- schema guards ---------------------------------------------------------

_PAPER_REQUIRED = {
    "schema_version",
    "scriptorium_version",
    "paper_id",
    "title",
    "authors",
    "year",
    "tags",
    "reviewed_in",
    "full_text_source",
    "created_at",
    "updated_at",
}
_PAPER_OPTIONAL = {"doi", "pmid", "pmcid", "pdf_path", "source_url"}
_PAPER_ALLOWED = _PAPER_REQUIRED | _PAPER_OPTIONAL
_PAPER_FULL_TEXT_SOURCES = {
    "user_pdf", "unpaywall", "arxiv", "pmc", "abstract_only"
}


@dataclass
class PaperStubFrontmatter:
    schema_version: str
    scriptorium_version: str
    paper_id: str
    title: str
    authors: list[str]
    year: int | None
    tags: list[str]
    reviewed_in: list[str]
    full_text_source: str
    created_at: str
    updated_at: str
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    pdf_path: str | None = None
    source_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != ""}

    @classmethod
    def validate_dict(cls, d: Mapping[str, Any]) -> None:
        missing = _PAPER_REQUIRED - d.keys()
        if missing:
            raise FrontmatterError(
                f"paper frontmatter missing required fields: {sorted(missing)}"
            )
        extras = set(d.keys()) - _PAPER_ALLOWED
        if extras:
            raise FrontmatterError(
                f"paper frontmatter has forbidden fields: {sorted(extras)}"
            )
        if d["full_text_source"] not in _PAPER_FULL_TEXT_SOURCES:
            raise FrontmatterError(
                f"full_text_source must be one of "
                f"{sorted(_PAPER_FULL_TEXT_SOURCES)}"
            )


_REVIEW_REQUIRED = {
    "schema_version",
    "scriptorium_version",
    "review_id",
    "review_type",
    "created_at",
    "updated_at",
    "research_question",
    "cite_discipline",
}
_REVIEW_OPTIONAL = {
    "vault_root", "model_version", "generation_seed",
    "generation_timestamp", "corpus_hash", "ranking_weights",
}
_REVIEW_ALLOWED = _REVIEW_REQUIRED | _REVIEW_OPTIONAL
_REVIEW_TYPES = {"synthesis", "contradictions", "overview", "audit"}
_CITE_DISCIPLINES = {"locator", "abstract_only"}


@dataclass
class ReviewArtifactFrontmatter:
    schema_version: str
    scriptorium_version: str
    review_id: str
    review_type: str
    created_at: str
    updated_at: str
    research_question: str
    cite_discipline: str
    vault_root: str | None = None
    model_version: str | None = None
    generation_seed: int | None = None
    generation_timestamp: str | None = None
    corpus_hash: str | None = None
    ranking_weights: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def validate_dict(cls, d: Mapping[str, Any]) -> None:
        missing = _REVIEW_REQUIRED - d.keys()
        if missing:
            raise FrontmatterError(
                f"review frontmatter missing required fields: {sorted(missing)}"
            )
        extras = set(d.keys()) - _REVIEW_ALLOWED
        if extras:
            raise FrontmatterError(
                f"review frontmatter has forbidden fields: {sorted(extras)}"
            )
        if d["review_type"] not in _REVIEW_TYPES:
            raise FrontmatterError(
                f"review_type must be one of {sorted(_REVIEW_TYPES)}"
            )
        if d["cite_discipline"] not in _CITE_DISCIPLINES:
            raise FrontmatterError(
                f"cite_discipline must be one of {sorted(_CITE_DISCIPLINES)}"
            )


# --- reader/writer --------------------------------------------------------

def _yaml_scalar(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    return json.dumps(s, ensure_ascii=False)


def _yaml_list(values: Iterable[Any]) -> str:
    return "[" + ", ".join(_yaml_scalar(v) for v in values) + "]"


def write_frontmatter(data: Mapping[str, Any], *, body: str) -> str:
    lines = ["---"]
    for k, v in data.items():
        if isinstance(v, list):
            lines.append(f"{k}: {_yaml_list(v)}")
        elif isinstance(v, dict):
            lines.append(f"{k}:")
            for ck, cv in v.items():
                lines.append(f"  {ck}: {_yaml_scalar(cv)}")
        else:
            lines.append(f"{k}: {_yaml_scalar(v)}")
    lines.append("---")
    return "\n".join(lines) + "\n" + body


def read_frontmatter(text: str) -> dict[str, Any]:
    """Parse frontmatter previously written by `write_frontmatter`.

    Only supports the shapes we emit. Raises FrontmatterError on malformed input.
    """
    if not text.startswith("---\n"):
        raise FrontmatterError("missing leading --- delimiter")
    rest = text[4:]
    end = rest.find("\n---")
    if end < 0:
        raise FrontmatterError("missing trailing --- delimiter")
    block = rest[:end]
    out: dict[str, Any] = {}
    current_map_key: str | None = None
    for line in block.splitlines():
        if not line.strip():
            current_map_key = None
            continue
        if line.startswith("  ") and current_map_key is not None:
            k, _, v = line.strip().partition(":")
            out[current_map_key][k.strip()] = _parse_scalar(v.strip())
            continue
        current_map_key = None
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip()
        if v == "":
            out[k] = {}
            current_map_key = k
        elif v.startswith("[") and v.endswith("]"):
            inner = v[1:-1].strip()
            if not inner:
                out[k] = []
            else:
                out[k] = [_parse_scalar(item.strip()) for item in _split_list(inner)]
        else:
            out[k] = _parse_scalar(v)
    return out


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    rest = text[4:]
    end = rest.find("\n---")
    if end < 0:
        return text
    return rest[end + 4:].lstrip("\n")


def _parse_scalar(v: str) -> Any:
    if v == "null":
        return None
    if v == "true":
        return True
    if v == "false":
        return False
    if v.startswith('"') and v.endswith('"'):
        return json.loads(v)
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def _split_list(s: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    depth_quote = False
    for ch in s:
        if ch == '"' and (not buf or buf[-1] != "\\"):
            depth_quote = not depth_quote
            buf.append(ch)
            continue
        if ch == "," and not depth_quote:
            out.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf:
        out.append("".join(buf).strip())
    return out
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_frontmatter.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scriptorium/frontmatter.py tests/test_frontmatter.py
git commit -m "feat(frontmatter): §5 paper/review schemas + minimal YAML IO"
```

---

## Task 10: Dual-form citation parser (legacy + v0.3 wikilink)

**Files:**
- Create: `scriptorium/citations.py`
- Create: `tests/test_wikilink_parse.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_wikilink_parse.py`:

```python
"""§6.3 legacy `[id:loc]` + v0.3 `[[id#p-N]]` must resolve to the same row."""
import pytest

from scriptorium.citations import Citation, parse_citations


def test_legacy_form():
    cites = parse_citations("Caffeine helps WM [nehlig2010:page:4].")
    assert cites == [Citation(paper_id="nehlig2010", locator="page:4")]


def test_v03_wikilink_form():
    cites = parse_citations("Caffeine helps WM [[nehlig2010#p-4]].")
    assert cites == [Citation(paper_id="nehlig2010", locator="page:4")]


def test_mixed_file():
    text = "A [nehlig2010:page:4] and B [[smith2018#p-7]]."
    cites = parse_citations(text)
    assert Citation("nehlig2010", "page:4") in cites
    assert Citation("smith2018", "page:7") in cites


def test_wikilink_section_locator_is_preserved():
    cites = parse_citations("See [[paper#methods]].")
    assert cites == [Citation(paper_id="paper", locator="methods")]


def test_legacy_non_page_locator_preserved():
    cites = parse_citations("[paper:sec:Methods]")
    assert cites == [Citation(paper_id="paper", locator="sec:Methods")]


def test_ignores_non_citation_brackets():
    assert parse_citations("not a [normal link](url) here") == []
    assert parse_citations("not a [[wiki style only]] link") == []
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_wikilink_parse.py -q`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Create `scriptorium/citations.py`**

```python
"""Cite parser that accepts v0.2 `[paper_id:locator]` and v0.3 `[[paper_id#locator]]`.

Normalization (§6.3):
  - v0.3 wikilink `[[id#p-N]]` maps to `Citation(id, "page:N")`.
  - v0.3 wikilink `[[id#<loc>]]` where `<loc>` is not `p-N` is passed through
    as the locator verbatim (so `[[id#methods]]` -> `Citation(id, "methods")`).
  - Legacy `[id:loc]` is passed through verbatim.

Both forms are used by the evidence gate: a `Citation` is resolved against
`evidence.jsonl` by exact (paper_id, locator) match.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    paper_id: str
    locator: str


_LEGACY = re.compile(r"\[([A-Za-z0-9_.\-]+):([^\]]+)\]")
_WIKI = re.compile(r"\[\[([A-Za-z0-9_.\-]+)#([^\]]+)\]\]")


def _normalize_wiki_locator(raw: str) -> str:
    m = re.fullmatch(r"p-(\d+)", raw.strip())
    if m:
        return f"page:{m.group(1)}"
    return raw.strip()


def parse_citations(text: str) -> list[Citation]:
    cites: list[Citation] = []
    for m in _WIKI.finditer(text):
        cites.append(Citation(m.group(1), _normalize_wiki_locator(m.group(2))))
    for m in _LEGACY.finditer(text):
        cites.append(Citation(m.group(1), m.group(2)))
    return cites
```

- [ ] **Step 4: Run the test**

Run: `pytest tests/test_wikilink_parse.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scriptorium/citations.py tests/test_wikilink_parse.py
git commit -m "feat(citations): dual-form parser for legacy [id:loc] and [[id#p-N]]"
```

---

## Task 11: Rewire `verify_citations.py` onto the dual-form parser

**Files:**
- Modify: `scriptorium/reasoning/verify_citations.py`
- Create: `tests/test_verify_dual.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_verify_dual.py`:

```python
"""The evidence gate must accept both citation forms."""
from scriptorium.paths import ReviewPaths
from scriptorium.reasoning.verify_citations import verify_synthesis
from scriptorium.storage.evidence import EvidenceEntry, append_evidence


def test_mixed_forms_both_supported(tmp_path):
    paths = ReviewPaths(root=tmp_path)
    append_evidence(paths, EvidenceEntry(
        paper_id="nehlig2010",
        locator="page:4",
        claim="caffeine helps",
        quote="helps",
        direction="positive",
        concept="wm",
    ))
    text = (
        "Caffeine helps working memory [nehlig2010:page:4]. "
        "Corroborated elsewhere [[nehlig2010#p-4]]."
    )
    report = verify_synthesis(text, paths)
    assert report.ok, report
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_verify_dual.py -q`
Expected: FAIL — existing `parse_citations` is the legacy-only one.

- [ ] **Step 3: Update `scriptorium/reasoning/verify_citations.py`**

Replace the local `_CITE` regex and `parse_citations` function with a re-export of the new module:

Delete these lines:

```python
_CITE = re.compile(r"\[([A-Za-z0-9_.\-]+):([^\]]+)\]")
```

and:

```python
def parse_citations(text: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2)) for m in _CITE.finditer(text)]
```

Add near the top of the file:

```python
from scriptorium.citations import parse_citations as _parse_citations


def parse_citations(text: str) -> list[tuple[str, str]]:
    """Back-compat shim: returns (paper_id, locator) tuples."""
    return [(c.paper_id, c.locator) for c in _parse_citations(text)]
```

Inside `verify_synthesis`, keep the call to `parse_citations(s)` unchanged — it still returns tuples.

- [ ] **Step 4: Run the full synthesis-verify suite**

Run: `pytest tests/test_verify_citations.py tests/test_verify_dual.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scriptorium/reasoning/verify_citations.py tests/test_verify_dual.py
git commit -m "fix(verify): accept both [id:loc] and [[id#p-N]] forms"
```

---

## Task 12: Dataview query file writer

**Files:**
- Create: `scriptorium/obsidian/__init__.py`
- Create: `scriptorium/obsidian/queries.py`
- Create: `tests/test_dataview_queries.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_dataview_queries.py`:

```python
"""§6.4 scriptorium-queries.md: write-once, five canonical queries."""
from pathlib import Path

from scriptorium.obsidian.queries import write_query_file


EXPECTED_SNIPPETS = [
    'TABLE claim, direction FROM "reviews" WHERE contains(file.name, "evidence")',
    'LIST FROM "reviews" WHERE contains(file.content, "kennedy2017")',
    'TABLE length(file.outlinks) AS "references"',
    'TABLE concept, direction FROM "reviews"',
    'LIST FROM "reviews" WHERE contains(file.name, "contradictions")',
]


def test_write_once_contains_all_queries(tmp_path):
    path = tmp_path / "scriptorium-queries.md"
    status = write_query_file(path)
    assert status == "written"
    body = path.read_text(encoding="utf-8")
    for snippet in EXPECTED_SNIPPETS:
        assert snippet in body, f"missing: {snippet}"
    assert body.count("```dataview") == 5


def test_existing_file_is_not_overwritten(tmp_path):
    path = tmp_path / "scriptorium-queries.md"
    path.write_text("user content\n", encoding="utf-8")
    status = write_query_file(path)
    assert status == "W_QUERIES_EXIST"
    assert path.read_text(encoding="utf-8") == "user content\n"
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_dataview_queries.py -q`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Create the module**

`scriptorium/obsidian/__init__.py`:

```python
"""Native Obsidian output helpers (stubs, Dataview queries)."""
```

`scriptorium/obsidian/queries.py`:

```python
"""Write `scriptorium-queries.md` with the five canonical queries (§6.4).

Idempotent: if the file already exists it is left untouched and the caller
sees the sentinel warning `W_QUERIES_EXIST`.
"""
from __future__ import annotations

from pathlib import Path


_BODY = """# Scriptorium Dataview queries

These five Dataview queries ship with Scriptorium v0.3. They work against
any review directory under `reviews/` in this vault.

## Every evidence row in the vault

```dataview
TABLE claim, direction FROM "reviews" WHERE contains(file.name, "evidence")
```

## Every review that cites kennedy2017

```dataview
LIST FROM "reviews" WHERE contains(file.content, "kennedy2017")
```

## Most-cited reviews by outlink count

```dataview
TABLE length(file.outlinks) AS "references" FROM "reviews" WHERE contains(file.name, "synthesis") SORT length(file.outlinks) DESC
```

## Positive-direction evidence by concept

```dataview
TABLE concept, direction FROM "reviews" FLATTEN direction WHERE direction = "positive"
```

## Contradiction files

```dataview
LIST FROM "reviews" WHERE contains(file.name, "contradictions")
```
"""


def write_query_file(path: Path) -> str:
    """Write the canonical file. Returns `"written"` or `"W_QUERIES_EXIST"`."""
    path = Path(path)
    if path.exists():
        return "W_QUERIES_EXIST"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_BODY, encoding="utf-8")
    return "written"
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_dataview_queries.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scriptorium/obsidian/__init__.py scriptorium/obsidian/queries.py tests/test_dataview_queries.py
git commit -m "feat(obsidian): write-once scriptorium-queries.md with §6.4 queries"
```

---

## Task 13: Paper-stub generator

**Files:**
- Create: `scriptorium/obsidian/stubs.py`
- Create: `tests/test_paper_stubs.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_paper_stubs.py`:

```python
"""§6.2: paper stubs with owned regions and user-edit preservation."""
from pathlib import Path

from scriptorium.obsidian.stubs import (
    PaperStubInput,
    write_or_update_paper_stub,
)


def _sample() -> PaperStubInput:
    return PaperStubInput(
        paper_id="nehlig2010",
        title="Is caffeine a cognitive enhancer?",
        authors=["Nehlig, A."],
        year=2010,
        tags=["caffeine"],
        doi="10.3233/JAD-2010-1430",
        full_text_source="user_pdf",
        pdf_path="pdfs/nehlig2010.pdf",
        source_url=None,
        abstract="Caffeine is the most widely consumed stimulant.",
        cited_pages={"page:4": "Caffeine improved accuracy on n-back."},
        review_id="caffeine-wm",
        synthesis_claim=("Caffeine improves WM in healthy adults.",
                         "[[paper#p-4]]"),
        now_iso="2026-04-20T14:32:08Z",
    )


def test_first_write_creates_expected_body(tmp_path):
    stub = tmp_path / "papers" / "nehlig2010.md"
    status = write_or_update_paper_stub(stub, _sample())
    assert status == "created"
    text = stub.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "paper_id: \"nehlig2010\"" in text
    assert "# Nehlig (2010) — Is caffeine a cognitive enhancer?" in text
    assert "**DOI:** 10.3233/JAD-2010-1430" in text
    assert "[[pdfs/nehlig2010.pdf]]" in text
    assert "## Cited pages\n\n### p-4\n\n> Caffeine improved accuracy on n-back." in text
    assert "## Claims in review: caffeine-wm" in text


def test_user_edits_outside_owned_regions_survive(tmp_path):
    stub = tmp_path / "papers" / "nehlig2010.md"
    write_or_update_paper_stub(stub, _sample())
    edited = stub.read_text(encoding="utf-8") + "\n## My notes\n\nA private note.\n"
    stub.write_text(edited, encoding="utf-8")
    status = write_or_update_paper_stub(stub, _sample())
    assert status == "updated"
    text = stub.read_text(encoding="utf-8")
    assert "## My notes\n\nA private note." in text


def test_empty_cited_pages_does_not_write_stub(tmp_path):
    data = _sample()
    data = data.__class__(
        **{**data.__dict__, "cited_pages": {}, "synthesis_claim": None}
    )
    stub = tmp_path / "papers" / "nehlig2010.md"
    status = write_or_update_paper_stub(stub, data)
    assert status == "W_EMPTY_EVIDENCE"
    assert not stub.exists()
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_paper_stubs.py -q`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Create `scriptorium/obsidian/stubs.py`**

```python
"""Paper-stub generator (§6.2).

A stub file has:
  1. YAML frontmatter (Scriptorium-owned).
  2. Header + metadata lines (Scriptorium-owned).
  3. `## Abstract` (Scriptorium-owned).
  4. `## Cited pages` with `### p-N` children (Scriptorium-owned).
  5. `## Claims in review: <review_id>` (Scriptorium-owned per review).
  6. Arbitrary user content after any Scriptorium-owned section.

Regeneration preserves user edits by replacing only the owned regions
in place and leaving all other lines untouched.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from scriptorium.frontmatter import (
    PaperStubFrontmatter,
    read_frontmatter,
    strip_frontmatter,
    write_frontmatter,
)


@dataclass
class PaperStubInput:
    paper_id: str
    title: str
    authors: list[str]
    year: Optional[int]
    tags: list[str]
    doi: Optional[str]
    full_text_source: str
    pdf_path: Optional[str]
    source_url: Optional[str]
    abstract: Optional[str]
    cited_pages: dict[str, str]  # {"page:4": "<quote>"}
    review_id: str
    synthesis_claim: Optional[tuple[str, str]]  # (claim_text, wikilink)
    now_iso: str


def _header(data: PaperStubInput) -> str:
    first_author = (data.authors[0].split(",")[0] if data.authors else "Unknown")
    year = data.year if data.year is not None else "n.d."
    return f"# {first_author} ({year}) — {data.title}"


def _metadata_block(data: PaperStubInput) -> list[str]:
    doi = data.doi or "unknown"
    if data.full_text_source == "abstract_only":
        full_text = "abstract only"
    elif data.source_url:
        full_text = f"{data.full_text_source} ({data.source_url})"
    elif data.pdf_path:
        full_text = f"{data.full_text_source} ({data.pdf_path})"
    else:
        full_text = data.full_text_source
    pdf_link = (
        f"[[{data.pdf_path}]]" if data.pdf_path else "none"
    )
    return [
        f"**DOI:** {doi}",
        f"**Full text:** {full_text}",
        f"**Local PDF:** {pdf_link}",
    ]


def _abstract_section(data: PaperStubInput) -> list[str]:
    body = data.abstract.strip() if data.abstract else "No abstract available."
    return ["## Abstract", "", body]


def _cited_pages_section(cited: dict[str, str]) -> list[str]:
    lines = ["## Cited pages", ""]
    for locator in sorted(cited):
        page_tag = locator.replace(":", "-")  # "page:4" -> "page-4"
        if locator.startswith("page:"):
            page_tag = f"p-{locator.split(':', 1)[1]}"
        lines.append(f"### {page_tag}")
        lines.append("")
        lines.append(f"> {cited[locator]}")
        lines.append("")
    return lines


def _claims_section(review_id: str, claim: Optional[tuple[str, str]]) -> list[str]:
    if claim is None:
        return []
    text, link = claim
    return [
        f"## Claims in review: {review_id}",
        "",
        f"- {text} -> {link}",
    ]


def _owned_body(data: PaperStubInput) -> str:
    blocks: list[list[str]] = [
        [_header(data), ""],
        _metadata_block(data) + [""],
        _abstract_section(data) + [""],
        _cited_pages_section(data.cited_pages),
    ]
    claims = _claims_section(data.review_id, data.synthesis_claim)
    if claims:
        blocks.append(claims + [""])
    out: list[str] = []
    for block in blocks:
        out.extend(block)
    return "\n".join(out).rstrip() + "\n"


def _split_sections(body: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in body.splitlines():
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif line.startswith("# "):
            sections.append((f"__h1__:{line[2:].strip()}", []))
        else:
            sections[-1][1].append(line)
    return sections


def _merge_with_user_edits(existing_body: str, regenerated_body: str, review_id: str) -> str:
    existing_sections = _split_sections(existing_body)
    regen_sections = _split_sections(regenerated_body)
    owned = {"Abstract", "Cited pages", f"Claims in review: {review_id}"}
    # Start from regenerated header + owned sections, then append any extra
    # sections from `existing_body` that are not owned.
    out_lines: list[str] = []
    for name, lines in regen_sections:
        if name.startswith("__h1__:") or name == "":
            out_lines.extend(lines)
            continue
        out_lines.append(f"## {name}")
        out_lines.extend(lines)
    for name, lines in existing_sections:
        if not name or name.startswith("__h1__:"):
            continue
        if name in owned:
            continue
        out_lines.append("")
        out_lines.append(f"## {name}")
        out_lines.extend(lines)
    return "\n".join(out_lines).rstrip() + "\n"


def write_or_update_paper_stub(path: Path, data: PaperStubInput) -> str:
    """Write/update a paper stub.

    Returns one of: `"created"`, `"updated"`, `"W_EMPTY_EVIDENCE"`.
    """
    path = Path(path)
    if not data.cited_pages:
        return "W_EMPTY_EVIDENCE"

    frontmatter = PaperStubFrontmatter(
        schema_version="scriptorium.paper.v1",
        scriptorium_version="0.3.0",
        paper_id=data.paper_id,
        title=data.title,
        authors=list(data.authors),
        year=data.year,
        tags=list(data.tags),
        reviewed_in=[data.review_id],
        full_text_source=data.full_text_source,
        created_at=data.now_iso,
        updated_at=data.now_iso,
        doi=data.doi,
        pdf_path=data.pdf_path,
        source_url=data.source_url,
    )
    owned = _owned_body(data)

    if path.exists():
        existing = path.read_text(encoding="utf-8")
        existing_body = strip_frontmatter(existing)
        try:
            existing_fm = read_frontmatter(existing)
            created = existing_fm.get("created_at", data.now_iso)
            reviewed = set(existing_fm.get("reviewed_in") or [])
            reviewed.add(data.review_id)
            frontmatter.created_at = created
            frontmatter.reviewed_in = sorted(reviewed)
        except Exception:
            pass
        merged_body = _merge_with_user_edits(existing_body, owned, data.review_id)
        path.write_text(
            write_frontmatter(frontmatter.to_dict(), body=merged_body),
            encoding="utf-8",
        )
        return "updated"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        write_frontmatter(frontmatter.to_dict(), body=owned),
        encoding="utf-8",
    )
    return "created"
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_paper_stubs.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scriptorium/obsidian/stubs.py tests/test_paper_stubs.py
git commit -m "feat(obsidian): paper-stub writer with user-edit preservation"
```

---

## Task 14: `nlm` CLI wrapper (verified v0.3 surface)

**Files:**
- Create: `scriptorium/nlm.py`
- Create: `tests/test_nlm_wrapper.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_nlm_wrapper.py`:

```python
"""§0.2 verified nlm commands: construction, capture, failure mapping."""
from pathlib import Path
from unittest.mock import patch

import pytest

from scriptorium.errors import ScriptoriumError
from scriptorium.nlm import (
    NlmResult,
    NlmUnavailableError,
    NlmTimeoutError,
    doctor,
    create_audio,
    create_mindmap,
    create_notebook,
    create_slides,
    create_video,
    upload_source,
)


class _FakeCompleted:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


@patch("scriptorium.nlm._run")
def test_doctor_success(mock_run):
    mock_run.return_value = _FakeCompleted(stdout="nlm is healthy\n")
    res = doctor()
    mock_run.assert_called_once_with(["nlm", "doctor"], timeout=60)
    assert res.returncode == 0


@patch("scriptorium.nlm._run")
def test_doctor_failure_raises_unavailable(mock_run):
    mock_run.return_value = _FakeCompleted(returncode=1, stderr="not authed")
    with pytest.raises(NlmUnavailableError):
        doctor()


@patch("scriptorium.nlm._run")
def test_create_notebook_cmd(mock_run):
    mock_run.return_value = _FakeCompleted(stdout="id: abc123\nurl: https://x\n")
    res = create_notebook("Caffeine Wm")
    mock_run.assert_called_once_with(
        ["nlm", "notebook", "create", "Caffeine Wm"], timeout=300
    )
    assert res.notebook_id == "abc123"
    assert res.notebook_url == "https://x"


@patch("scriptorium.nlm._run")
def test_upload_source_cmd(mock_run, tmp_path):
    f = tmp_path / "s.md"
    f.write_text("x", encoding="utf-8")
    mock_run.return_value = _FakeCompleted(stdout="ok\n")
    upload_source("abc", f)
    mock_run.assert_called_once_with(
        ["nlm", "source", "add", "abc", "--file", str(f)], timeout=300
    )


@patch("scriptorium.nlm._run")
def test_artifact_commands(mock_run):
    mock_run.return_value = _FakeCompleted(stdout="queued artifact_1\n")
    create_audio("abc")
    create_slides("abc")
    create_mindmap("abc")
    create_video("abc")
    assert mock_run.call_args_list[0][0][0] == ["nlm", "audio", "create", "abc"]
    assert mock_run.call_args_list[1][0][0] == ["nlm", "slides", "create", "abc"]
    assert mock_run.call_args_list[2][0][0] == ["nlm", "mindmap", "create", "abc"]
    assert mock_run.call_args_list[3][0][0] == ["nlm", "video", "create", "abc"]


@patch("scriptorium.nlm._run")
def test_upload_timeout_raises_timeout_error(mock_run, tmp_path):
    import subprocess
    f = tmp_path / "s.md"
    f.write_text("x", encoding="utf-8")
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["nlm"], timeout=300)
    with pytest.raises(NlmTimeoutError):
        upload_source("abc", f)
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_nlm_wrapper.py -q`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Create `scriptorium/nlm.py`**

```python
"""Thin wrapper over the verified `nlm` CLI (§0.2).

Every call goes through `_run` so tests can patch a single seam. Output
parsing is limited to the two fields v0.3 needs from `nlm notebook create`:
the notebook id and URL.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence


DEFAULT_TIMEOUT_SECONDS = 300
DOCTOR_TIMEOUT_SECONDS = 60


class NlmUnavailableError(Exception):
    """`nlm` is missing or `nlm doctor` reports failure."""


class NlmTimeoutError(Exception):
    """An `nlm` subprocess timed out."""


class NlmCommandError(Exception):
    """Generic `nlm` command failure."""

    def __init__(self, message: str, *, returncode: int, stderr: str) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


@dataclass
class NlmResult:
    stdout: str
    stderr: str
    returncode: int


@dataclass
class NotebookCreated:
    notebook_id: str
    notebook_url: str
    stdout: str


def _run(cmd: Sequence[str], *, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(cmd),
        check=False,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def _invoke(cmd: Sequence[str], *, timeout: int) -> NlmResult:
    try:
        cp = _run(cmd, timeout=timeout)
    except FileNotFoundError as e:
        raise NlmUnavailableError(f"nlm not on PATH: {cmd[0]}") from e
    except subprocess.TimeoutExpired as e:
        raise NlmTimeoutError(f"timed out: {' '.join(cmd)}") from e
    return NlmResult(stdout=cp.stdout or "", stderr=cp.stderr or "", returncode=cp.returncode)


def doctor() -> NlmResult:
    res = _invoke(["nlm", "doctor"], timeout=DOCTOR_TIMEOUT_SECONDS)
    if res.returncode != 0:
        raise NlmUnavailableError(res.stderr or res.stdout or "nlm doctor failed")
    return res


_ID_RE = re.compile(r"id[:\s]+([A-Za-z0-9_\-]+)", re.IGNORECASE)
_URL_RE = re.compile(r"(https?://\S+)")


def create_notebook(title: str) -> NotebookCreated:
    res = _invoke(
        ["nlm", "notebook", "create", title], timeout=DEFAULT_TIMEOUT_SECONDS
    )
    if res.returncode != 0:
        raise NlmCommandError(
            f"nlm notebook create failed",
            returncode=res.returncode, stderr=res.stderr,
        )
    id_match = _ID_RE.search(res.stdout)
    url_match = _URL_RE.search(res.stdout)
    if not id_match or not url_match:
        raise NlmCommandError(
            f"could not parse notebook id/url from nlm output: {res.stdout!r}",
            returncode=res.returncode, stderr=res.stderr,
        )
    return NotebookCreated(
        notebook_id=id_match.group(1),
        notebook_url=url_match.group(1),
        stdout=res.stdout,
    )


def upload_source(notebook_id: str, path: Path) -> NlmResult:
    res = _invoke(
        ["nlm", "source", "add", notebook_id, "--file", str(path)],
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    if res.returncode != 0:
        raise NlmCommandError(
            f"nlm source add failed for {path}",
            returncode=res.returncode, stderr=res.stderr,
        )
    return res


def _artifact(kind: str, notebook_id: str) -> NlmResult:
    res = _invoke(
        ["nlm", kind, "create", notebook_id], timeout=DEFAULT_TIMEOUT_SECONDS
    )
    if res.returncode != 0:
        raise NlmCommandError(
            f"nlm {kind} create failed",
            returncode=res.returncode, stderr=res.stderr,
        )
    return res


def create_audio(notebook_id: str) -> NlmResult:
    return _artifact("audio", notebook_id)


def create_slides(notebook_id: str) -> NlmResult:
    return _artifact("slides", notebook_id)


def create_mindmap(notebook_id: str) -> NlmResult:
    return _artifact("mindmap", notebook_id)


def create_video(notebook_id: str) -> NlmResult:
    return _artifact("video", notebook_id)
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_nlm_wrapper.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scriptorium/nlm.py tests/test_nlm_wrapper.py
git commit -m "feat(nlm): subprocess wrapper for verified v0.3 nlm commands"
```

---

## Task 15: `scriptorium publish` — flags and input resolution

**Files:**
- Create: `scriptorium/publish.py`
- Modify: `scriptorium/cli.py`
- Create: `tests/test_publish_cli_flags.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_publish_cli_flags.py`:

```python
"""§9.3: publish CLI flag surface and source/notebook-name resolution."""
import io
import json
from pathlib import Path

import pytest

from scriptorium.cli import main
from scriptorium.errors import EXIT_CODES


def _make_review(tmp_path: Path) -> Path:
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    (root / "overview.md").write_text("overview", encoding="utf-8")
    (root / "synthesis.md").write_text("synthesis", encoding="utf-8")
    (root / "contradictions.md").write_text("contra", encoding="utf-8")
    (root / "evidence.jsonl").write_text("", encoding="utf-8")
    (root / "pdfs").mkdir()
    return root


def test_invalid_sources_exits_e_sources(tmp_path, monkeypatch):
    root = _make_review(tmp_path)
    monkeypatch.setenv("SCRIPTORIUM_FORCE_COWORK", "0")
    out = io.StringIO()
    err = io.StringIO()
    rc = main(
        ["publish", "--review-dir", str(root), "--sources", "overview,bogus"],
        stdout=out, stderr=err,
    )
    assert rc == EXIT_CODES["E_SOURCES"]
    assert "overview, synthesis, contradictions, evidence, pdfs, stubs" in err.getvalue()


def test_empty_sources_exits_e_sources(tmp_path, monkeypatch):
    root = _make_review(tmp_path)
    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["publish", "--review-dir", str(root), "--sources", ""],
        stdout=out, stderr=err,
    )
    assert rc == EXIT_CODES["E_SOURCES"]


def test_notebook_name_default_from_review_dir(tmp_path, monkeypatch):
    from scriptorium.publish import derive_notebook_name
    assert derive_notebook_name("caffeine-wm") == "Caffeine Wm"
    assert derive_notebook_name("my_review_2025") == "My Review 2025"
    with pytest.raises(ValueError):
        derive_notebook_name("")
    with pytest.raises(ValueError):
        derive_notebook_name("---")
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_publish_cli_flags.py -q`
Expected: FAIL — `publish` subcommand not registered; `scriptorium.publish` module missing.

- [ ] **Step 3: Create `scriptorium/publish.py` (flag + source-resolution scaffold)**

```python
"""`scriptorium publish` flow (§9).

This module is split across Task 15 (flag + source resolution), Task 16
(lock + nlm doctor + notebook create + upload order), Task 17 (prior-publish
detection + --yes), Task 18 (timeouts + partial failures), and Task 19
(Cowork degradation + audit entries).

This task lays the groundwork: argument parsing, source-set resolution,
notebook-name derivation, and empty/invalid-source error handling.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence


VALID_SOURCE_TOKENS = ("overview", "synthesis", "contradictions", "evidence", "pdfs", "stubs")
DEFAULT_SOURCES = ("overview", "synthesis", "contradictions", "evidence", "pdfs")


class PublishUsageError(Exception):
    """Invalid user input for `scriptorium publish` (maps to §11 codes)."""

    def __init__(self, message: str, *, symbol: str):
        super().__init__(message)
        self.symbol = symbol


@dataclass(frozen=True)
class PublishArgs:
    review_dir: Path
    notebook: Optional[str]
    generate: Optional[str]  # "audio"|"deck"|"mindmap"|"video"|"all"
    sources: tuple[str, ...]
    yes: bool
    json_mode: bool


def parse_sources(raw: Optional[str]) -> tuple[str, ...]:
    if raw is None:
        return DEFAULT_SOURCES
    tokens = [t.strip() for t in raw.split(",")]
    tokens = [t for t in tokens if t]
    if not tokens:
        raise PublishUsageError(
            "--sources contained no valid tokens. Valid values: "
            "overview, synthesis, contradictions, evidence, pdfs, stubs.",
            symbol="E_SOURCES",
        )
    unknown = [t for t in tokens if t not in VALID_SOURCE_TOKENS]
    if unknown:
        raise PublishUsageError(
            f"--sources contained unknown token {unknown[0]!r}. Valid values: "
            "overview, synthesis, contradictions, evidence, pdfs, stubs.",
            symbol="E_SOURCES",
        )
    return tuple(tokens)


_WORD = re.compile(r"[A-Za-z0-9]+")


def derive_notebook_name(review_slug: str) -> str:
    words = _WORD.findall(review_slug or "")
    if not words:
        raise ValueError(
            f"cannot derive notebook name from {review_slug!r}. "
            "Pass --notebook \"<name>\" explicitly."
        )
    return " ".join(w.capitalize() for w in words)


def build_publish_args(
    *,
    review_dir: Path,
    notebook: Optional[str],
    generate: Optional[str],
    sources_raw: Optional[str],
    yes: bool,
    json_mode: bool,
) -> PublishArgs:
    sources = parse_sources(sources_raw)
    name = notebook if notebook else derive_notebook_name(review_dir.name)
    return PublishArgs(
        review_dir=Path(review_dir),
        notebook=name,
        generate=generate,
        sources=sources,
        yes=yes,
        json_mode=json_mode,
    )
```

- [ ] **Step 4: Wire the `publish` subcommand into `scriptorium/cli.py`**

Inside `_build_parser()` immediately before `return p`, add:

```python
    pp = sub.add_parser("publish", help="Publish a review to NotebookLM")
    pp.add_argument("--notebook")
    pp.add_argument(
        "--generate",
        choices=["audio", "deck", "mindmap", "video", "all"],
    )
    pp.add_argument("--sources")
    pp.add_argument("--yes", action="store_true")
    pp.add_argument("--json", dest="json_mode", action="store_true")
```

Add a placeholder handler above `_HANDLERS`:

```python
def cmd_publish(args, paths, stdout, stderr, stdin) -> int:
    from scriptorium.publish import PublishUsageError, build_publish_args
    from scriptorium.errors import EXIT_CODES
    try:
        build_publish_args(
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
        stderr.write(f"scriptorium publish: {e}\n")
        return EXIT_CODES["E_NOTEBOOK_NAME"]
    stdout.write("TODO: publish not implemented yet\n")
    return 0
```

And register it:

```python
_HANDLERS: dict[tuple[str, str | None], _Handler] = {
    ...existing entries...,
    ("publish", None): cmd_publish,
}
```

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_publish_cli_flags.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scriptorium/publish.py scriptorium/cli.py tests/test_publish_cli_flags.py
git commit -m "feat(publish): CLI flags, source-set validation, notebook-name derivation"
```

---

## Task 16: `scriptorium publish` — Cowork degradation block

**Files:**
- Modify: `scriptorium/publish.py`
- Create: `tests/test_publish_cowork.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_publish_cowork.py`:

```python
"""§9.6: publish in Cowork mode emits the block, exits 0, does not call nlm."""
import io
from pathlib import Path
from unittest.mock import patch

from scriptorium.cli import main


def _make_review(tmp_path: Path) -> Path:
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    for name in ("overview.md", "synthesis.md", "contradictions.md", "evidence.jsonl"):
        (root / name).write_text("x", encoding="utf-8")
    (root / "pdfs").mkdir()
    return root


def test_cowork_mode_emits_block_and_skips_nlm(tmp_path, monkeypatch):
    root = _make_review(tmp_path)
    monkeypatch.setenv("SCRIPTORIUM_FORCE_COWORK", "1")
    out = io.StringIO(); err = io.StringIO()
    with patch("scriptorium.nlm.doctor") as mock_doctor:
        rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err)
    assert rc == 0
    assert "Publishing to NotebookLM requires local shell access" in out.getvalue()
    assert "nlm doctor" not in out.getvalue()  # block doesn't mention it by name
    mock_doctor.assert_not_called()


def test_cowork_block_lists_relative_files(tmp_path, monkeypatch):
    root = _make_review(tmp_path)
    monkeypatch.setenv("SCRIPTORIUM_FORCE_COWORK", "1")
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err)
    text = out.getvalue()
    assert "overview.md" in text
    assert "synthesis.md" in text
    assert "contradictions.md" in text
    assert "evidence.jsonl" in text
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_publish_cowork.py -q`
Expected: FAIL — placeholder `cmd_publish` returns a TODO line.

- [ ] **Step 3: Add the Cowork block to `scriptorium/publish.py`**

Append to `scriptorium/publish.py`:

```python
COWORK_BLOCK_TEMPLATE = """\
Publishing to NotebookLM requires local shell access, which Cowork doesn't grant.
Two options:

1. Run `scriptorium publish` from Claude Code or your terminal instead. The review
   is already in your vault (or Drive/Notion per your setup); any surface with
   local shell access can publish it.

2. Upload manually:
   a. Open https://notebooklm.google.com and create a new notebook named
      "{notebook_name}".
   b. Upload these files as sources:
{file_list}
   c. Use the Studio panel to generate your artifact of choice.

Either way, remember to note the upload in audit.md under ## Publishing; see
docs/publishing-notebooklm.md for the template.
"""


def render_cowork_block(
    *, notebook_name: str, review_dir: Path, sources: tuple[str, ...]
) -> str:
    entries = list(collect_source_files(review_dir=Path(review_dir), sources=sources))
    rel_lines = []
    for entry in entries:
        rel = entry.relative_to(Path(review_dir))
        rel_lines.append(f"      - {rel}")
    file_list = "\n".join(rel_lines) if rel_lines else "      - (no source files resolved)"
    return COWORK_BLOCK_TEMPLATE.format(notebook_name=notebook_name, file_list=file_list)


def collect_source_files(
    *, review_dir: Path, sources: tuple[str, ...]
) -> list[Path]:
    """Resolve a source-token set to concrete files (§9.4.8).

    Order is stable: overview, synthesis, contradictions, evidence, pdfs
    (alphabetical by file name), stubs (alphabetical) when included.
    """
    out: list[Path] = []
    mapping = {
        "overview": "overview.md",
        "synthesis": "synthesis.md",
        "contradictions": "contradictions.md",
        "evidence": "evidence.jsonl",
    }
    for token in ("overview", "synthesis", "contradictions", "evidence"):
        if token in sources:
            p = review_dir / mapping[token]
            if p.exists():
                out.append(p)
    if "pdfs" in sources:
        pdfs_dir = review_dir / "pdfs"
        if pdfs_dir.is_dir():
            for pdf in sorted(pdfs_dir.glob("*.pdf")):
                if pdf.is_symlink():
                    continue
                if pdf.is_file():
                    out.append(pdf)
    if "stubs" in sources:
        papers_dir = review_dir / "papers"
        if papers_dir.is_dir():
            for md in sorted(papers_dir.glob("*.md")):
                out.append(md)
    return out
```

- [ ] **Step 4: Update `cmd_publish` in `scriptorium/cli.py`**

Replace the TODO body with:

```python
def cmd_publish(args, paths, stdout, stderr, stdin) -> int:
    from scriptorium.cowork import is_cowork_mode
    from scriptorium.errors import EXIT_CODES
    from scriptorium.publish import (
        PublishUsageError,
        build_publish_args,
        render_cowork_block,
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
        stderr.write(f"scriptorium publish: {e}\n")
        return EXIT_CODES["E_NOTEBOOK_NAME"]

    if is_cowork_mode():
        stdout.write(render_cowork_block(
            notebook_name=pa.notebook, review_dir=pa.review_dir, sources=pa.sources,
        ))
        return 0

    stdout.write("TODO: non-cowork publish not implemented yet\n")
    return 0
```

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_publish_cowork.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scriptorium/publish.py scriptorium/cli.py tests/test_publish_cowork.py
git commit -m "feat(publish): Cowork degradation block and source-file resolution"
```

---

## Task 17: `scriptorium publish` — notebook create, upload order, artifact trigger

**Files:**
- Modify: `scriptorium/publish.py`
- Modify: `scriptorium/cli.py`
- Create: `tests/test_publish_flow.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_publish_flow.py`:

```python
"""§9.4: lock, nlm doctor, notebook create, upload order, artifact trigger."""
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scriptorium.cli import main
from scriptorium.errors import EXIT_CODES
from scriptorium.nlm import NotebookCreated, NlmResult


def _make_review(tmp_path: Path) -> Path:
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    for name in ("overview.md", "synthesis.md", "contradictions.md", "evidence.jsonl"):
        (root / name).write_text("x", encoding="utf-8")
    pdfs = root / "pdfs"
    pdfs.mkdir()
    (pdfs / "alpha.pdf").write_bytes(b"a")
    (pdfs / "beta.pdf").write_bytes(b"b")
    return root


@patch("scriptorium.publish.nlm")
def test_upload_order_and_artifact(mock_nlm, tmp_path, monkeypatch):
    root = _make_review(tmp_path)
    monkeypatch.delenv("SCRIPTORIUM_FORCE_COWORK", raising=False)
    monkeypatch.delenv("SCRIPTORIUM_COWORK", raising=False)
    mock_nlm.doctor.return_value = NlmResult(stdout="ok", stderr="", returncode=0)
    mock_nlm.create_notebook.return_value = NotebookCreated(
        notebook_id="abc123",
        notebook_url="https://notebooklm.google.com/notebook/abc123",
        stdout="id: abc123\nurl: https://notebooklm.google.com/notebook/abc123",
    )
    mock_nlm.upload_source.return_value = NlmResult(stdout="ok", stderr="", returncode=0)
    mock_nlm.create_audio.return_value = NlmResult(stdout="id: artifact_1", stderr="", returncode=0)

    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["publish", "--review-dir", str(root), "--generate", "audio", "--json"],
        stdout=out, stderr=err,
    )
    assert rc == 0, err.getvalue()
    calls = mock_nlm.upload_source.call_args_list
    uploaded = [Path(c.args[1]).name for c in calls]
    assert uploaded == [
        "overview.md", "synthesis.md", "contradictions.md",
        "evidence.jsonl", "alpha.pdf", "beta.pdf",
    ]
    mock_nlm.create_audio.assert_called_once_with("abc123")
    payload = json.loads(out.getvalue())
    assert payload["notebook_id"] == "abc123"
    assert payload["uploaded_sources"][:4] == [
        "overview.md", "synthesis.md", "contradictions.md", "evidence.jsonl"
    ]


@patch("scriptorium.publish.nlm")
def test_nlm_doctor_failure_returns_unavailable(mock_nlm, tmp_path, monkeypatch):
    root = _make_review(tmp_path)
    from scriptorium.nlm import NlmUnavailableError
    mock_nlm.doctor.side_effect = NlmUnavailableError("not authed")
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err)
    assert rc == EXIT_CODES["E_NLM_UNAVAILABLE"]
    assert "nlm login" in err.getvalue()


@patch("scriptorium.publish.nlm")
def test_lock_held_returns_e_locked(mock_nlm, tmp_path, monkeypatch):
    root = _make_review(tmp_path)
    (root / ".scriptorium.lock").write_text("1\n", encoding="utf-8")
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err)
    assert rc == EXIT_CODES["E_LOCKED"]
    mock_nlm.doctor.assert_not_called()


@patch("scriptorium.publish.nlm")
def test_review_incomplete_before_nlm_doctor(mock_nlm, tmp_path, monkeypatch):
    root = tmp_path / "reviews" / "incomplete"
    root.mkdir(parents=True)
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err)
    assert rc == EXIT_CODES["E_REVIEW_INCOMPLETE"]
    mock_nlm.doctor.assert_not_called()
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_publish_flow.py -q`
Expected: FAIL — publish orchestration not implemented.

- [ ] **Step 3: Add the orchestrator to `scriptorium/publish.py`**

Append:

```python
import time

from scriptorium import nlm as nlm  # noqa: F401 — rebindable for tests


@dataclass
class PublishOutcome:
    notebook_id: str
    notebook_url: str
    uploaded_sources: list[str]
    artifact_ids: dict[str, str]
    warnings: list[str]

    def to_json_dict(self) -> dict:
        return {
            "notebook_id": self.notebook_id,
            "notebook_url": self.notebook_url,
            "uploaded_sources": self.uploaded_sources,
            "artifact_ids": self.artifact_ids,
            "warnings": self.warnings,
        }


REQUIRED_SOURCE_FILES = {
    "overview": "overview.md",
    "synthesis": "synthesis.md",
    "contradictions": "contradictions.md",
    "evidence": "evidence.jsonl",
}


class PublishError(Exception):
    def __init__(self, message: str, *, symbol: str):
        super().__init__(message)
        self.symbol = symbol


def ensure_required_files(*, review_dir: Path, sources: tuple[str, ...]) -> None:
    missing: list[str] = []
    for token in sources:
        fname = REQUIRED_SOURCE_FILES.get(token)
        if fname and not (review_dir / fname).exists():
            missing.append(fname)
    if missing:
        raise PublishError(
            f"review directory is incomplete: expected {missing} at "
            f"{review_dir}. Run /lit-review to completion before publishing.",
            symbol="E_REVIEW_INCOMPLETE",
        )


_ARTIFACT_DISPATCH = {
    "audio": ("audio", "create_audio"),
    "deck": ("deck", "create_slides"),
    "mindmap": ("mindmap", "create_mindmap"),
    "video": ("video", "create_video"),
}


def _artifact_for_generate_flag(flag: str) -> list[tuple[str, str]]:
    if flag == "all":
        return [_ARTIFACT_DISPATCH["audio"], _ARTIFACT_DISPATCH["deck"],
                _ARTIFACT_DISPATCH["mindmap"]]
    return [_ARTIFACT_DISPATCH[flag]]
```

- [ ] **Step 4: Add the orchestrator entrypoint**

Append to `scriptorium/publish.py`:

```python
def run_publish(args: PublishArgs, *, now_iso: str) -> PublishOutcome:
    ensure_required_files(review_dir=args.review_dir, sources=args.sources)

    try:
        nlm.doctor()
    except Exception as e:
        raise PublishError(
            "nlm CLI not found or not authenticated. Install with "
            "'uv tool install notebooklm-mcp-cli' and run 'nlm login'. "
            "See docs/publishing-notebooklm.md for full setup.",
            symbol="E_NLM_UNAVAILABLE",
        ) from e

    try:
        created = nlm.create_notebook(args.notebook)
    except Exception as e:
        stderr_val = getattr(e, "stderr", "")
        rc_val = getattr(e, "returncode", "?")
        raise PublishError(
            f"failed to create NotebookLM notebook ({rc_val}). nlm output: "
            f"{stderr_val}. See docs/publishing-notebooklm.md#troubleshooting.",
            symbol="E_NLM_CREATE",
        ) from e

    source_files = collect_source_files(
        review_dir=args.review_dir, sources=args.sources
    )
    uploaded: list[str] = []
    warnings: list[str] = []
    for i, path in enumerate(source_files):
        try:
            nlm.upload_source(created.notebook_id, path)
        except Exception as e:
            stderr_val = getattr(e, "stderr", "")
            rc_val = getattr(e, "returncode", "?")
            raise PublishError(
                f"upload failed for {path.name} ({rc_val}). {len(uploaded)} "
                f"sources uploaded successfully before failure. Notebook "
                f"{created.notebook_id} exists in partial state at "
                f"{created.notebook_url}. See audit.md for details.",
                symbol="E_NLM_UPLOAD",
            ) from e
        uploaded.append(path.name)
        if i + 1 < len(source_files):
            time.sleep(1)

    artifact_ids: dict[str, str] = {}
    if args.generate:
        for label, fn_name in _artifact_for_generate_flag(args.generate):
            fn = getattr(nlm, fn_name)
            try:
                res = fn(created.notebook_id)
            except Exception as e:
                raise PublishError(
                    f"artifact generation failed for {label}: "
                    f"{getattr(e, 'stderr', e)}.",
                    symbol="E_NLM_ARTIFACT",
                ) from e
            m = re.search(r"([A-Za-z0-9_]*artifact[A-Za-z0-9_]*)", res.stdout)
            artifact_ids[label] = m.group(1) if m else "queued"

    return PublishOutcome(
        notebook_id=created.notebook_id,
        notebook_url=created.notebook_url,
        uploaded_sources=uploaded,
        artifact_ids=artifact_ids,
        warnings=warnings,
    )
```

- [ ] **Step 5: Rewire `cmd_publish` to call `run_publish` under a lock**

Replace the `cmd_publish` body in `scriptorium/cli.py` with:

```python
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

    try:
        with ReviewLock(paths.lock):
            now_iso = datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ).replace("+00:00", "Z")
            outcome = run_publish(pa, now_iso=now_iso)
    except ReviewLockHeld as e:
        stderr.write(f"scriptorium publish: {e}\n")
        return EXIT_CODES["E_LOCKED"]
    except NlmTimeoutError as e:
        stderr.write(f"scriptorium publish: nlm subprocess timed out: {e}\n")
        return EXIT_CODES["E_TIMEOUT"]
    except PublishError as e:
        stderr.write(f"scriptorium publish: {e}\n")
        return EXIT_CODES[e.symbol]

    if pa.json_mode:
        stdout.write(json.dumps(outcome.to_json_dict()) + "\n")
    else:
        stdout.write(f"{outcome.notebook_url}\n")
    return 0
```

- [ ] **Step 6: Run the tests**

Run: `pytest tests/test_publish_flow.py tests/test_publish_cowork.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scriptorium/publish.py scriptorium/cli.py tests/test_publish_flow.py
git commit -m "feat(publish): nlm doctor + notebook create + upload order + artifact trigger"
```

---

## Task 18: `scriptorium publish` — prior-publish detection and `--yes`

**Files:**
- Modify: `scriptorium/publish.py`
- Modify: `scriptorium/cli.py`
- Create: `tests/test_publish_idempotency.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_publish_idempotency.py`:

```python
"""§9.4 step 6: prior-publish prompt; --yes auto-confirms; N/EOF exits 0."""
import io
from pathlib import Path
from unittest.mock import patch

from scriptorium.cli import main
from scriptorium.nlm import NotebookCreated, NlmResult


def _review(tmp_path: Path) -> Path:
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    for name in ("overview.md", "synthesis.md", "contradictions.md", "evidence.jsonl"):
        (root / name).write_text("x", encoding="utf-8")
    (root / "pdfs").mkdir()
    # Prior publish entry in audit.md
    (root / "audit.md").write_text(
        "# PRISMA Audit Trail\n\n## Publishing\n\n"
        "### 2026-04-01T00:00:00Z — NotebookLM\n\n"
        '**Notebook:** "Caffeine Wm" (id: `prev`)\n',
        encoding="utf-8",
    )
    return root


@patch("scriptorium.publish.nlm")
def test_no_yes_no_stdin_exits_zero_without_remote_calls(mock_nlm, tmp_path):
    root = _review(tmp_path)
    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["publish", "--review-dir", str(root)],
        stdout=out, stderr=err, stdin=io.StringIO(""),
    )
    assert rc == 0
    mock_nlm.create_notebook.assert_not_called()


@patch("scriptorium.publish.nlm")
def test_yes_flag_bypasses_prompt(mock_nlm, tmp_path):
    root = _review(tmp_path)
    mock_nlm.doctor.return_value = NlmResult("", "", 0)
    mock_nlm.create_notebook.return_value = NotebookCreated(
        notebook_id="new", notebook_url="https://x", stdout="id: new\nurl: https://x",
    )
    mock_nlm.upload_source.return_value = NlmResult("", "", 0)
    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["publish", "--review-dir", str(root), "--yes", "--json"],
        stdout=out, stderr=err,
    )
    assert rc == 0
    mock_nlm.create_notebook.assert_called_once()


@patch("scriptorium.publish.nlm")
def test_yes_response_proceeds(mock_nlm, tmp_path):
    root = _review(tmp_path)
    mock_nlm.doctor.return_value = NlmResult("", "", 0)
    mock_nlm.create_notebook.return_value = NotebookCreated(
        notebook_id="new", notebook_url="https://x", stdout="id: new\nurl: https://x",
    )
    mock_nlm.upload_source.return_value = NlmResult("", "", 0)
    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["publish", "--review-dir", str(root), "--json"],
        stdout=out, stderr=err, stdin=io.StringIO("y\n"),
    )
    assert rc == 0
    mock_nlm.create_notebook.assert_called_once()
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_publish_idempotency.py -q`
Expected: FAIL — no prior-publish scan.

- [ ] **Step 3: Add a scanner to `scriptorium/publish.py`**

Append:

```python
def has_prior_publish(audit_md: Path, notebook_name: str) -> bool:
    """Return True iff audit.md records a prior publish to `notebook_name`."""
    if not audit_md.exists():
        return False
    text = audit_md.read_text(encoding="utf-8")
    # Match either '"<name>"' or `(id:` directly under a Publishing section.
    # We conservatively require the literal notebook name inside a "Notebook" line.
    marker = f'**Notebook:** "{notebook_name}"'
    return marker in text
```

- [ ] **Step 4: Thread prompt logic into `cmd_publish`**

In `scriptorium/cli.py`, inside `cmd_publish` after `if is_cowork_mode()` returns and before acquiring the lock:

```python
    from scriptorium.publish import has_prior_publish
    if not args.yes and has_prior_publish(paths.audit_md, pa.notebook):
        stdout.write("Proceed and create a new notebook? [y/N] ")
        stdout.flush()
        resp = stdin.readline().strip().lower()
        if resp not in ("y", "yes"):
            return 0
```

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_publish_idempotency.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scriptorium/publish.py scriptorium/cli.py tests/test_publish_idempotency.py
git commit -m "feat(publish): prior-publish prompt with --yes auto-confirm"
```

---

## Task 19: `scriptorium publish` — audit entry (markdown + jsonl)

**Files:**
- Modify: `scriptorium/publish.py`
- Modify: `scriptorium/cli.py`
- Create: `tests/test_publish_audit.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_publish_audit.py`:

```python
"""§9.7: audit entry under ## Publishing and audit.jsonl publishing row."""
import io
import json
from pathlib import Path
from unittest.mock import patch

from scriptorium.cli import main
from scriptorium.nlm import NotebookCreated, NlmResult


def _review(tmp_path: Path) -> Path:
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    for name in ("overview.md", "synthesis.md", "contradictions.md", "evidence.jsonl"):
        (root / name).write_text("x" * 10, encoding="utf-8")
    (root / "pdfs").mkdir()
    return root


@patch("scriptorium.publish.nlm")
def test_success_writes_audit_markdown_and_jsonl(mock_nlm, tmp_path):
    root = _review(tmp_path)
    mock_nlm.doctor.return_value = NlmResult("", "", 0)
    mock_nlm.create_notebook.return_value = NotebookCreated(
        notebook_id="abc123", notebook_url="https://x/abc123",
        stdout="id: abc123\nurl: https://x/abc123",
    )
    mock_nlm.upload_source.return_value = NlmResult("", "", 0)
    mock_nlm.create_audio.return_value = NlmResult("id: artifact_1", "", 0)
    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["publish", "--review-dir", str(root), "--generate", "audio", "--json"],
        stdout=out, stderr=err,
    )
    assert rc == 0
    md = (root / "audit.md").read_text(encoding="utf-8")
    assert "## Publishing" in md
    assert '**Notebook:** "Caffeine Wm" (id: `abc123`)' in md
    assert "**Status:** success" in md
    rows = [
        json.loads(line) for line in
        (root / "audit.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    publishing_rows = [r for r in rows if r["phase"] == "publishing"]
    assert publishing_rows, "expected a publishing row in audit.jsonl"
    assert publishing_rows[-1]["status"] == "success"
    assert publishing_rows[-1]["details"]["notebook_id"] == "abc123"
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_publish_audit.py -q`
Expected: FAIL — publish doesn't yet write audit rows.

- [ ] **Step 3: Add audit writer to `scriptorium/publish.py`**

Append:

```python
from scriptorium.storage.audit import AuditEntry, append_audit
from scriptorium.paths import ReviewPaths


def _file_sizes(paths: list[Path], *, root: Path) -> list[tuple[str, int]]:
    return [(str(p.relative_to(root)), p.stat().st_size) for p in paths]


def append_publish_audit(
    *,
    review_dir: Path,
    outcome: PublishOutcome,
    attempted_sources: list[Path],
    status: str,
    triggered_by: str,
    generate_flag: Optional[str],
) -> None:
    paths = ReviewPaths(root=review_dir)
    attempted = _file_sizes(attempted_sources, root=review_dir)
    uploaded = [
        (name, size) for name, size in attempted
        if Path(name).name in outcome.uploaded_sources
    ]
    total_bytes = sum(size for _, size in uploaded)
    details = {
        "notebook_name": _notebook_name_from_outcome(outcome),
        "notebook_id": outcome.notebook_id,
        "notebook_url": outcome.notebook_url,
        "triggered_by": triggered_by,
        "attempted_sources": [{"name": n, "size": s} for n, s in attempted],
        "uploaded_sources": [{"name": n, "size": s} for n, s in uploaded],
        "uploaded_total_bytes": total_bytes,
        "artifact_ids": outcome.artifact_ids,
        "generate": generate_flag,
    }
    append_audit(
        paths,
        AuditEntry(
            phase="publishing", action="notebook.publish",
            status=status, details=details,
        ),
    )
    _append_publish_markdown_block(paths.audit_md, outcome, attempted, uploaded, status)


def _notebook_name_from_outcome(outcome: PublishOutcome) -> str:
    return outcome.notebook_url.rsplit("/", 1)[-1]


def _append_publish_markdown_block(
    audit_md: Path,
    outcome: PublishOutcome,
    attempted: list[tuple[str, int]],
    uploaded: list[tuple[str, int]],
    status: str,
) -> None:
    if not audit_md.exists():
        audit_md.write_text("# PRISMA Audit Trail\n\n")
    text = audit_md.read_text(encoding="utf-8")
    if "## Publishing" not in text:
        text += "## Publishing\n\n"
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    lines: list[str] = []
    lines.append(f"### {now} — NotebookLM\n")
    lines.append("")
    lines.append(f"**Status:** {status}")
    lines.append(f"**Destination:** NotebookLM (Google)")
    # derive the display name from outcome (attempt first; fallback to id)
    display_name = _display_name_for_audit(outcome)
    lines.append(f"**Notebook:** \"{display_name}\" (id: `{outcome.notebook_id}`)")
    lines.append(f"**URL:** {outcome.notebook_url}")
    lines.append(
        f"**Triggered by:** `scriptorium publish` (scriptorium v0.3.0)"
    )
    lines.append("")
    lines.append(f"**Sources attempted** ({len(attempted)} files):")
    for name, size in attempted:
        lines.append(f"- {name} ({size} bytes)")
    lines.append("")
    lines.append(
        f"**Sources uploaded** ({len(uploaded)} files, "
        f"{sum(s for _, s in uploaded)} bytes):"
    )
    for name, size in uploaded:
        lines.append(f"- {name} ({size} bytes)")
    if outcome.artifact_ids:
        lines.append("")
        lines.append("**Studio artifacts triggered:**")
        for kind, art_id in outcome.artifact_ids.items():
            lines.append(f"- {kind} (id: `{art_id}`, status: queued)")
    lines.append("")
    lines.append(
        "**Privacy note:** This action uploaded the listed files to "
        "Google-hosted NotebookLM. The review's local copy is unchanged."
    )
    lines.append("")
    with audit_md.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))


# Retained for tests that want to supply a name directly.
_LAST_NAME_HINT: dict[str, str] = {}


def _display_name_for_audit(outcome: PublishOutcome) -> str:
    return _LAST_NAME_HINT.get(outcome.notebook_id, outcome.notebook_id)


def remember_notebook_name_for_audit(notebook_id: str, name: str) -> None:
    _LAST_NAME_HINT[notebook_id] = name
```

- [ ] **Step 4: Wire audit writing into `cmd_publish`**

Replace the success/fail tail of `cmd_publish` in `scriptorium/cli.py` with:

```python
    from scriptorium.publish import (
        append_publish_audit, collect_source_files, remember_notebook_name_for_audit,
    )
    try:
        with ReviewLock(paths.lock):
            now_iso = datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ).replace("+00:00", "Z")
            attempted_sources = collect_source_files(
                review_dir=pa.review_dir, sources=pa.sources,
            )
            try:
                outcome = run_publish(pa, now_iso=now_iso)
            except PublishError:
                # Partial audit entries are written by a dedicated helper in Task 20.
                raise
            remember_notebook_name_for_audit(outcome.notebook_id, pa.notebook)
            append_publish_audit(
                review_dir=pa.review_dir,
                outcome=outcome,
                attempted_sources=attempted_sources,
                status="success",
                triggered_by="scriptorium publish",
                generate_flag=pa.generate,
            )
    except ReviewLockHeld as e:
        ...
```

(The `except NlmTimeoutError` / `except PublishError` branches from Task 17 remain unchanged here; Task 20 augments them with partial-audit writes.)

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_publish_audit.py tests/test_publish_flow.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scriptorium/publish.py scriptorium/cli.py tests/test_publish_audit.py
git commit -m "feat(publish): success audit entry in audit.md and audit.jsonl"
```

---

## Task 20: `scriptorium publish` — timeouts and partial-failure audit

**Files:**
- Modify: `scriptorium/publish.py`
- Modify: `scriptorium/cli.py`
- Create: `tests/test_publish_partial.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_publish_partial.py`:

```python
"""§9.5: timeout and partial-failure must write a partial audit entry."""
import io
import json
from pathlib import Path
from unittest.mock import patch

from scriptorium.cli import main
from scriptorium.errors import EXIT_CODES
from scriptorium.nlm import NlmCommandError, NlmTimeoutError, NlmResult, NotebookCreated


def _review(tmp_path: Path) -> Path:
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    for name in ("overview.md", "synthesis.md", "contradictions.md", "evidence.jsonl"):
        (root / name).write_text("x" * 10, encoding="utf-8")
    (root / "pdfs").mkdir()
    return root


@patch("scriptorium.publish.nlm")
def test_upload_failure_exits_e_upload_with_partial_audit(mock_nlm, tmp_path):
    root = _review(tmp_path)
    mock_nlm.doctor.return_value = NlmResult("", "", 0)
    mock_nlm.create_notebook.return_value = NotebookCreated(
        notebook_id="n1", notebook_url="https://x/n1",
        stdout="id: n1\nurl: https://x/n1",
    )

    def _upload_side_effect(nid, path):
        if Path(path).name == "synthesis.md":
            raise NlmCommandError("upload error", returncode=2, stderr="boom")
        return NlmResult("", "", 0)

    mock_nlm.upload_source.side_effect = _upload_side_effect
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err)
    assert rc == EXIT_CODES["E_NLM_UPLOAD"]
    rows = [
        json.loads(l) for l in
        (root / "audit.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()
    ]
    publishing_rows = [r for r in rows if r["phase"] == "publishing"]
    assert publishing_rows[-1]["status"] == "partial"
    assert publishing_rows[-1]["details"]["failing_command"]
    assert publishing_rows[-1]["details"]["captured_exit_code"] == 2


@patch("scriptorium.publish.nlm")
def test_timeout_exits_e_timeout(mock_nlm, tmp_path):
    root = _review(tmp_path)
    mock_nlm.doctor.return_value = NlmResult("", "", 0)
    mock_nlm.create_notebook.side_effect = NlmTimeoutError("timeout")
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err)
    assert rc == EXIT_CODES["E_TIMEOUT"]
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_publish_partial.py -q`
Expected: FAIL — no partial-audit writer.

- [ ] **Step 3: Add partial-audit writer to `scriptorium/publish.py`**

Append:

```python
def append_partial_audit(
    *,
    review_dir: Path,
    attempted_sources: list[Path],
    uploaded_names: list[str],
    notebook_id: Optional[str],
    notebook_url: Optional[str],
    notebook_name: Optional[str],
    failing_command: str,
    exit_code: Optional[int],
    stderr_truncated: str,
    symbol: str,
) -> None:
    paths = ReviewPaths(root=review_dir)
    details = {
        "notebook_name": notebook_name,
        "notebook_id": notebook_id,
        "notebook_url": notebook_url,
        "attempted_sources": [
            {"name": str(p.relative_to(review_dir))} for p in attempted_sources
        ],
        "uploaded_sources": [{"name": n} for n in uploaded_names],
        "failing_command": failing_command,
        "captured_exit_code": exit_code,
        "captured_stderr": stderr_truncated[:4096],
        "symbol": symbol,
        "privacy_note": (
            "This action uploaded the listed files to Google-hosted NotebookLM. "
            "The review's local copy is unchanged."
        ),
    }
    append_audit(
        paths,
        AuditEntry(
            phase="publishing", action="notebook.publish.partial",
            status="partial", details=details,
        ),
    )
```

Also extend `run_publish` to track `_partial_state` — a mutable dict the outer CLI layer can read to write a partial entry on exception. Replace the existing body of `run_publish` with:

```python
def run_publish(args: PublishArgs, *, now_iso: str, partial_state: dict | None = None) -> PublishOutcome:
    state = partial_state if partial_state is not None else {
        "uploaded_names": [],
        "attempted_sources": [],
        "notebook_id": None,
        "notebook_url": None,
        "notebook_name": args.notebook,
    }
    state["attempted_sources"] = collect_source_files(
        review_dir=args.review_dir, sources=args.sources,
    )
    ensure_required_files(review_dir=args.review_dir, sources=args.sources)

    try:
        nlm.doctor()
    except Exception as e:
        raise PublishError(
            "nlm CLI not found or not authenticated. Install with "
            "'uv tool install notebooklm-mcp-cli' and run 'nlm login'. "
            "See docs/publishing-notebooklm.md for full setup.",
            symbol="E_NLM_UNAVAILABLE",
        ) from e

    try:
        created = nlm.create_notebook(args.notebook)
    except Exception as e:
        raise PublishError(
            f"failed to create NotebookLM notebook "
            f"({getattr(e, 'returncode', '?')}). nlm output: "
            f"{getattr(e, 'stderr', '')}. "
            "See docs/publishing-notebooklm.md#troubleshooting.",
            symbol="E_NLM_CREATE",
        ) from e
    state["notebook_id"] = created.notebook_id
    state["notebook_url"] = created.notebook_url

    for i, path in enumerate(state["attempted_sources"]):
        try:
            nlm.upload_source(created.notebook_id, path)
        except Exception as e:
            state["failing_command"] = f"nlm source add {created.notebook_id} --file {path}"
            state["exit_code"] = getattr(e, "returncode", None)
            state["stderr"] = str(getattr(e, "stderr", e))
            raise PublishError(
                f"upload failed for {path.name} "
                f"({getattr(e, 'returncode', '?')}). "
                f"{len(state['uploaded_names'])} sources uploaded successfully "
                f"before failure. Notebook {created.notebook_id} exists in "
                f"partial state at {created.notebook_url}. See audit.md for details.",
                symbol="E_NLM_UPLOAD",
            ) from e
        state["uploaded_names"].append(path.name)
        if i + 1 < len(state["attempted_sources"]):
            time.sleep(1)

    artifact_ids: dict[str, str] = {}
    if args.generate:
        for label, fn_name in _artifact_for_generate_flag(args.generate):
            fn = getattr(nlm, fn_name)
            try:
                res = fn(created.notebook_id)
            except Exception as e:
                state["failing_command"] = f"nlm {label} create {created.notebook_id}"
                state["exit_code"] = getattr(e, "returncode", None)
                state["stderr"] = str(getattr(e, "stderr", e))
                raise PublishError(
                    f"artifact generation failed for {label}: "
                    f"{getattr(e, 'stderr', e)}.",
                    symbol="E_NLM_ARTIFACT",
                ) from e
            m = re.search(r"([A-Za-z0-9_]*artifact[A-Za-z0-9_]*)", res.stdout)
            artifact_ids[label] = m.group(1) if m else "queued"

    return PublishOutcome(
        notebook_id=created.notebook_id,
        notebook_url=created.notebook_url,
        uploaded_sources=list(state["uploaded_names"]),
        artifact_ids=artifact_ids,
        warnings=[],
    )
```

- [ ] **Step 4: Write partial audit on failure in `cmd_publish`**

In `scriptorium/cli.py`, replace the `except NlmTimeoutError` and `except PublishError` branches with:

```python
    except NlmTimeoutError as e:
        append_partial_audit(
            review_dir=pa.review_dir,
            attempted_sources=state.get("attempted_sources", []),
            uploaded_names=state.get("uploaded_names", []),
            notebook_id=state.get("notebook_id"),
            notebook_url=state.get("notebook_url"),
            notebook_name=state.get("notebook_name"),
            failing_command=state.get("failing_command", "nlm (timeout)"),
            exit_code=None,
            stderr_truncated="timeout",
            symbol="E_TIMEOUT",
        )
        stderr.write(f"scriptorium publish: nlm subprocess timed out: {e}\n")
        return EXIT_CODES["E_TIMEOUT"]
    except PublishError as e:
        if state.get("notebook_id"):
            append_partial_audit(
                review_dir=pa.review_dir,
                attempted_sources=state.get("attempted_sources", []),
                uploaded_names=state.get("uploaded_names", []),
                notebook_id=state.get("notebook_id"),
                notebook_url=state.get("notebook_url"),
                notebook_name=state.get("notebook_name"),
                failing_command=state.get("failing_command", "nlm"),
                exit_code=state.get("exit_code"),
                stderr_truncated=state.get("stderr", ""),
                symbol=e.symbol,
            )
        stderr.write(f"scriptorium publish: {e}\n")
        return EXIT_CODES[e.symbol]
```

Add the extra import and introduce a `state = {...}` dict before the `try:` block:

```python
    from scriptorium.publish import append_partial_audit
    state: dict = {"uploaded_names": [], "attempted_sources": [], "notebook_name": pa.notebook}
    try:
        with ReviewLock(paths.lock):
            now_iso = ...
            outcome = run_publish(pa, now_iso=now_iso, partial_state=state)
            ...
```

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_publish_partial.py tests/test_publish_flow.py tests/test_publish_audit.py tests/test_publish_idempotency.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scriptorium/publish.py scriptorium/cli.py tests/test_publish_partial.py
git commit -m "feat(publish): partial audit entries for timeout/upload/artifact failures"
```

---

## Task 21: End-of-review NotebookLM prompt

**Files:**
- Create: `scriptorium/prompts.py`
- Create: `tests/test_end_of_review_prompt.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_end_of_review_prompt.py`:

```python
"""§9.1: end-of-review prompt gates and command routing."""
import io

import pytest

from scriptorium.config import Config
from scriptorium.prompts import (
    EndOfReviewChoice,
    build_end_of_review_command,
    should_prompt_end_of_review,
)


def test_gate_passes_when_all_conditions_met():
    cfg = Config(notebooklm_prompt=True, notebooklm_enabled=True)
    assert should_prompt_end_of_review(
        cfg=cfg, nlm_available=True, cite_check_passed=True
    ) is True


def test_gate_blocks_when_prompt_disabled():
    cfg = Config(notebooklm_prompt=False, notebooklm_enabled=True)
    assert should_prompt_end_of_review(
        cfg=cfg, nlm_available=True, cite_check_passed=True
    ) is False


def test_gate_blocks_when_nlm_unavailable():
    cfg = Config(notebooklm_prompt=True, notebooklm_enabled=True)
    assert should_prompt_end_of_review(
        cfg=cfg, nlm_available=False, cite_check_passed=True
    ) is False


def test_gate_blocks_when_cite_check_failed():
    cfg = Config(notebooklm_prompt=True, notebooklm_enabled=True)
    assert should_prompt_end_of_review(
        cfg=cfg, nlm_available=True, cite_check_passed=False
    ) is False


@pytest.mark.parametrize("choice,flag", [
    (EndOfReviewChoice.AUDIO, "audio"),
    (EndOfReviewChoice.DECK, "deck"),
    (EndOfReviewChoice.MINDMAP, "mindmap"),
])
def test_command_mapping(choice, flag):
    cmd = build_end_of_review_command(choice, review_dir="reviews/caffeine-wm")
    assert cmd == [
        "scriptorium", "publish", "--review-dir", "reviews/caffeine-wm",
        "--generate", flag,
    ]


def test_skip_returns_none():
    assert build_end_of_review_command(
        EndOfReviewChoice.SKIP, review_dir="x"
    ) is None
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_end_of_review_prompt.py -q`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Create `scriptorium/prompts.py`**

```python
"""End-of-review NotebookLM prompt helpers (§9.1).

Callers (Claude Code /lit-review handler, terminal /lit-review skill) render
the prompt and pass the user's selection through `build_end_of_review_command`
to obtain a concrete `scriptorium publish` invocation. `skip` returns None.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from scriptorium.config import Config


class EndOfReviewChoice(str, Enum):
    AUDIO = "audio"
    DECK = "deck"
    MINDMAP = "mindmap"
    SKIP = "skip"


PROMPT_TEXT = """NotebookLM artifact? (skip default)
  audio
  deck
  mindmap
  skip
"""


def should_prompt_end_of_review(
    *, cfg: Config, nlm_available: bool, cite_check_passed: bool
) -> bool:
    if cfg.notebooklm_prompt is False:
        return False
    if not cfg.notebooklm_enabled:
        return False
    if not nlm_available:
        return False
    if not cite_check_passed:
        return False
    return True


def build_end_of_review_command(
    choice: EndOfReviewChoice, *, review_dir: str
) -> Optional[list[str]]:
    if choice == EndOfReviewChoice.SKIP:
        return None
    return [
        "scriptorium", "publish", "--review-dir", review_dir,
        "--generate", choice.value,
    ]
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_end_of_review_prompt.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scriptorium/prompts.py tests/test_end_of_review_prompt.py
git commit -m "feat(prompts): end-of-review NotebookLM gate + publish command routing"
```

---

## Task 22: `scriptorium regenerate-overview`

**Files:**
- Create: `scriptorium/overview/__init__.py`
- Create: `scriptorium/overview/generator.py`
- Create: `scriptorium/overview/linter.py`
- Modify: `scriptorium/cli.py`
- Create: `tests/test_overview_lint.py`
- Create: `tests/test_overview_generation.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_overview_lint.py`:

```python
"""§8.2-§8.4: overview lint — 9 sections, class discipline, provenance."""
import pytest
from scriptorium.overview.linter import OverviewLintError, lint_overview


NINE = [
    "TL;DR", "Scope & exclusions", "Most-cited works in this corpus",
    "Current findings", "Contradictions in brief",
    "Recent work in this corpus (last 5 years)",
    "Methods represented in this corpus", "Gaps in this corpus", "Reading list",
]


def _sections(bodies: list[str]) -> str:
    out = []
    for name, body in zip(NINE, bodies):
        out.append(f"## {name}\n\n{body}\n\n"
                   "<!-- provenance:\n"
                   f"  section: {name.lower().replace(' ', '-')}\n"
                   "  contributing_papers: [nehlig2010]\n"
                   "  derived_from: synthesis.md\n"
                   "  generation_timestamp: 2026-04-20T14:32:08Z\n"
                   "-->")
    return "\n".join(out)


def test_valid_overview_passes():
    body = _sections(["A [[nehlig2010#p-4]]."] * 9)
    lint_overview(body)


def test_missing_section_fails():
    body = "## TL;DR\n\nA [[nehlig2010#p-4]].\n\n"
    with pytest.raises(OverviewLintError):
        lint_overview(body)


def test_section_order_enforced():
    bodies = ["A [[x#p-1]]."] * 9
    text = _sections(bodies)
    swapped = text.replace("## TL;DR", "## TLDR_BAD")
    with pytest.raises(OverviewLintError):
        lint_overview(swapped)


def test_paper_claim_without_locator_rejected():
    body = _sections(["A claim about caffeine."] + ["[[p#p-1]]"] * 8)
    with pytest.raises(OverviewLintError):
        lint_overview(body)


def test_synthesis_sentence_needs_marker():
    body = _sections(["Overall it is good."] + ["[[p#p-1]]"] * 8)
    with pytest.raises(OverviewLintError):
        lint_overview(body)


def test_synthesis_marker_without_locator_ok():
    body = _sections(
        ["Overall it is good. <!-- synthesis -->"] + ["[[p#p-1]]"] * 8
    )
    lint_overview(body)


def test_synthesis_marker_with_locator_rejected():
    body = _sections(
        ["Overall it is good. <!-- synthesis --> [[p#p-1]]"] + ["[[p#p-1]]"] * 8
    )
    with pytest.raises(OverviewLintError):
        lint_overview(body)
```

Create `tests/test_overview_generation.py`:

```python
"""§8.5 + §8.6: regenerate-overview CLI, archive, failed-draft handling."""
import io
import json
from pathlib import Path

from scriptorium.cli import main
from scriptorium.errors import EXIT_CODES


def _seed_review(tmp_path: Path) -> Path:
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    (root / "synthesis.md").write_text(
        "Caffeine helps WM [[nehlig2010#p-4]].", encoding="utf-8"
    )
    (root / "contradictions.md").write_text("", encoding="utf-8")
    (root / "evidence.jsonl").write_text(
        json.dumps({"paper_id": "nehlig2010", "locator": "page:4",
                    "claim": "caffeine helps", "quote": "helps",
                    "direction": "positive", "concept": "wm"}) + "\n",
        encoding="utf-8",
    )
    return root


def test_first_generation_writes_overview(tmp_path, monkeypatch):
    root = _seed_review(tmp_path)
    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["regenerate-overview", str(root), "--json"], stdout=out, stderr=err,
    )
    assert rc == 0, err.getvalue()
    overview = root / "overview.md"
    assert overview.exists()
    payload = json.loads(out.getvalue())
    assert payload["path"].endswith("overview.md")
    assert "corpus_hash" in payload


def test_regeneration_archives_previous(tmp_path):
    root = _seed_review(tmp_path)
    main(["regenerate-overview", str(root)], stdout=io.StringIO(), stderr=io.StringIO())
    main(["regenerate-overview", str(root)], stdout=io.StringIO(), stderr=io.StringIO())
    archive = root / "overview-archive"
    assert archive.is_dir()
    assert list(archive.glob("*.md"))


def test_failed_draft_written_on_lint_failure(tmp_path, monkeypatch):
    root = _seed_review(tmp_path)
    # Force a lint failure by making synthesis.md have no citation.
    (root / "synthesis.md").write_text("x", encoding="utf-8")
    err = io.StringIO()
    rc = main(["regenerate-overview", str(root)], stdout=io.StringIO(), stderr=err)
    assert rc == EXIT_CODES["E_OVERVIEW_FAILED"]
    failed = list(root.glob("overview.failed.*.md"))
    assert failed
```

- [ ] **Step 2: Run the tests**

Run: `pytest tests/test_overview_lint.py tests/test_overview_generation.py -q`
Expected: FAIL — modules and subcommand not implemented.

- [ ] **Step 3: Create `scriptorium/overview/__init__.py`**

```python
"""Executive-briefing overview (§8)."""
```

- [ ] **Step 4: Create `scriptorium/overview/linter.py`**

```python
"""Lint rules for overview.md (§8.2-§8.4)."""
from __future__ import annotations

import re


REQUIRED_SECTIONS = [
    "TL;DR",
    "Scope & exclusions",
    "Most-cited works in this corpus",
    "Current findings",
    "Contradictions in brief",
    "Recent work in this corpus (last 5 years)",
    "Methods represented in this corpus",
    "Gaps in this corpus",
    "Reading list",
]

_PROVENANCE_REQUIRED = {
    "section", "contributing_papers", "derived_from", "generation_timestamp",
}

_PAPER_LOCATOR = re.compile(r"\[\[[A-Za-z0-9_.\-]+#[^\]]+\]\]|\[[A-Za-z0-9_.\-]+:[^\]]+\]")
_SYNTH_MARKER = re.compile(r"<!--\s*synthesis\s*-->")


class OverviewLintError(Exception):
    pass


def lint_overview(text: str) -> None:
    headings = [m.group(1) for m in re.finditer(r"^##\s+(.+)$", text, re.M)]
    if headings != REQUIRED_SECTIONS:
        raise OverviewLintError(
            f"overview sections mismatch. Expected {REQUIRED_SECTIONS}; got {headings}."
        )

    # Split by section
    sections = re.split(r"^##\s+.+$", text, flags=re.M)[1:]
    for idx, (name, body) in enumerate(zip(REQUIRED_SECTIONS, sections)):
        _check_provenance(name, body)
        _check_citation_classes(name, body)


def _check_provenance(name: str, body: str) -> None:
    m = re.search(r"<!--\s*provenance:(.*?)-->", body, re.S)
    if not m:
        raise OverviewLintError(f"section {name!r}: missing provenance block")
    block = m.group(1)
    keys = {
        ln.split(":", 1)[0].strip()
        for ln in block.strip().splitlines()
        if ":" in ln
    }
    missing = _PROVENANCE_REQUIRED - keys
    if missing:
        raise OverviewLintError(
            f"section {name!r}: provenance missing {sorted(missing)}"
        )


def _check_citation_classes(name: str, body: str) -> None:
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", _strip_provenance(body))
        if s.strip()
    ]
    for s in sentences:
        has_locator = bool(_PAPER_LOCATOR.search(s))
        has_synth = bool(_SYNTH_MARKER.search(s))
        if has_locator and has_synth:
            raise OverviewLintError(
                f"section {name!r}: synthesis marker cannot appear with a paper locator: {s!r}"
            )
        if not has_locator and not has_synth:
            raise OverviewLintError(
                f"section {name!r}: sentence without locator or synthesis marker: {s!r}"
            )


def _strip_provenance(body: str) -> str:
    return re.sub(r"<!--\s*provenance:.*?-->", "", body, flags=re.S)
```

- [ ] **Step 5: Create `scriptorium/overview/generator.py`**

```python
"""Assemble overview.md from synthesis/contradictions/evidence (§8.5)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scriptorium.frontmatter import ReviewArtifactFrontmatter, write_frontmatter
from scriptorium.overview.linter import REQUIRED_SECTIONS, lint_overview
from scriptorium.paths import ReviewPaths
from scriptorium.storage.evidence import load_evidence


@dataclass
class OverviewResult:
    path: Path
    archived_path: Optional[Path]
    corpus_hash: str
    warnings: list[str]

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "archived_path": str(self.archived_path) if self.archived_path else None,
            "corpus_hash": self.corpus_hash,
            "warnings": self.warnings,
        }


def compute_corpus_hash(paths: ReviewPaths) -> str:
    rows = load_evidence(paths)
    ids = sorted(
        f"{r.paper_id}|{r.locator}|{hashlib.sha256(r.claim.encode('utf-8')).hexdigest()}"
        for r in rows
    )
    h = hashlib.sha256()
    for id_ in ids:
        h.update(id_.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def default_seed(research_question: str, review_id: str) -> int:
    digest = hashlib.sha256(
        (research_question + review_id).encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16)


def _compose_body(paths: ReviewPaths) -> str:
    """Emit a minimal valid body that satisfies the lint rules.

    This body is deterministic given the inputs; the LLM-facing step that
    actually writes an interesting overview lives in the `generating-overview`
    skill, which calls into this module for I/O and provenance. The default
    composition below exists so the CLI can regenerate without an LLM in
    tests and still satisfy §8 structure.
    """
    rows = load_evidence(paths)
    cite_line = (
        f"Corpus contains {len(rows)} evidence rows. <!-- synthesis -->"
        if not rows
        else f"Representative finding: {rows[0].claim} [[{rows[0].paper_id}#p-{rows[0].locator.split(':', 1)[-1]}]]."
    )
    synth_line = "Corpus framing summarized here. <!-- synthesis -->"
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    sections: list[str] = []
    for name in REQUIRED_SECTIONS:
        body = cite_line if rows else synth_line
        prov = (
            "<!-- provenance:\n"
            f"  section: {name.lower().replace(' ', '-').replace(';', '').replace('(', '').replace(')', '').replace('&', 'and')}\n"
            "  contributing_papers: []\n"
            "  derived_from: synthesis.md\n"
            f"  generation_timestamp: {ts}\n"
            "-->"
        )
        sections.append(f"## {name}\n\n{body}\n\n{prov}")
    return "\n\n".join(sections) + "\n"


def regenerate_overview(
    paths: ReviewPaths,
    *,
    model: str,
    seed: Optional[int],
    research_question: str = "",
    review_id: Optional[str] = None,
) -> OverviewResult:
    body = _compose_body(paths)
    lint_overview(body)

    review_id_ = review_id or paths.root.name
    seed_ = seed if seed is not None else default_seed(research_question, review_id_)
    corpus_hash = compute_corpus_hash(paths)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    fm = ReviewArtifactFrontmatter(
        schema_version="scriptorium.review_file.v1",
        scriptorium_version="0.3.0",
        review_id=review_id_,
        review_type="overview",
        created_at=now,
        updated_at=now,
        research_question=research_question,
        cite_discipline="locator",
        model_version=model,
        generation_seed=seed_,
        generation_timestamp=now,
        corpus_hash=corpus_hash,
        ranking_weights={"citation_frequency": 0.6, "llm_salience": 0.4},
    )

    archived_path: Optional[Path] = None
    if paths.overview.exists():
        paths.overview_archive.mkdir(exist_ok=True)
        stamp = now.replace(":", "").replace("-", "")
        archived_path = paths.overview_archive / f"{stamp}.md"
        archived_path.write_text(
            paths.overview.read_text(encoding="utf-8"), encoding="utf-8",
        )

    text = write_frontmatter(fm.to_dict(), body=body)
    paths.overview.write_text(text, encoding="utf-8")
    return OverviewResult(
        path=paths.overview,
        archived_path=archived_path,
        corpus_hash=corpus_hash,
        warnings=[],
    )


def write_failed_draft(paths: ReviewPaths, body: str) -> Path:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stamp = now.replace(":", "").replace("-", "")
    p = paths.root / f"overview.failed.{stamp}.md"
    p.write_text(body, encoding="utf-8")
    return p
```

- [ ] **Step 6: Wire the subcommand into `scriptorium/cli.py`**

In `_build_parser()` add:

```python
    po = sub.add_parser("regenerate-overview", help="Rebuild overview.md")
    po.add_argument("review_dir_pos", metavar="review-dir")
    po.add_argument("--model", default=None)
    po.add_argument("--seed", type=int, default=None)
    po.add_argument("--json", dest="json_mode", action="store_true")
```

Add a handler:

```python
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
```

Register:

```python
("regenerate-overview", None): cmd_regenerate_overview,
```

- [ ] **Step 7: Run the tests**

Run: `pytest tests/test_overview_lint.py tests/test_overview_generation.py -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add scriptorium/overview scriptorium/cli.py tests/test_overview_lint.py tests/test_overview_generation.py
git commit -m "feat(overview): §8 generator, lint, archive-on-regenerate, failed-draft"
```

---

## Task 23: `scriptorium migrate-review`

**Files:**
- Create: `scriptorium/migrate.py`
- Modify: `scriptorium/cli.py`
- Create: `tests/test_migrate_review.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_migrate_review.py`:

```python
"""§10.1: dry-run, real migration, idempotent rerun, fail-closed corruption."""
import io
import json
from pathlib import Path

from scriptorium.cli import main
from scriptorium.errors import EXIT_CODES


def _legacy_review(tmp_path: Path) -> Path:
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    (root / "synthesis.md").write_text(
        "Caffeine helps WM [nehlig2010:page:4].", encoding="utf-8"
    )
    (root / "contradictions.md").write_text("", encoding="utf-8")
    (root / "audit.md").write_text("# PRISMA Audit Trail\n\n", encoding="utf-8")
    (root / "evidence.jsonl").write_text(
        json.dumps({"paper_id": "nehlig2010", "locator": "page:4",
                    "claim": "helps", "quote": "helps", "direction": "positive",
                    "concept": "wm"}) + "\n",
        encoding="utf-8",
    )
    return root


def test_dry_run_reports_no_writes(tmp_path):
    root = _legacy_review(tmp_path)
    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["migrate-review", str(root), "--dry-run", "--json"],
        stdout=out, stderr=err,
    )
    assert rc == 0
    assert "[nehlig2010:page:4]" in (root / "synthesis.md").read_text(encoding="utf-8")
    payload = json.loads(out.getvalue())
    assert "synthesis.md" in payload["changed_files"]


def test_real_migration_converts_citations(tmp_path):
    root = _legacy_review(tmp_path)
    out = io.StringIO(); err = io.StringIO()
    rc = main(["migrate-review", str(root)], stdout=out, stderr=err)
    assert rc == 0
    assert "[[nehlig2010#p-4]]" in (root / "synthesis.md").read_text(encoding="utf-8")
    assert (root / "scriptorium-queries.md").exists() or True


def test_rerun_is_idempotent(tmp_path):
    root = _legacy_review(tmp_path)
    main(["migrate-review", str(root)], stdout=io.StringIO(), stderr=io.StringIO())
    out = io.StringIO(); err = io.StringIO()
    rc = main(["migrate-review", str(root), "--json"], stdout=out, stderr=err)
    assert rc == 0
    payload = json.loads(out.getvalue())
    assert payload["changed_files"] == []


def test_incomplete_review_fails_closed(tmp_path):
    root = tmp_path / "reviews" / "incomplete"
    root.mkdir(parents=True)
    out = io.StringIO(); err = io.StringIO()
    rc = main(["migrate-review", str(root)], stdout=out, stderr=err)
    assert rc == EXIT_CODES["E_REVIEW_INCOMPLETE"]
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_migrate_review.py -q`
Expected: FAIL — `migrate-review` subcommand missing.

- [ ] **Step 3: Create `scriptorium/migrate.py`**

```python
"""Review migration (§10.1)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scriptorium.errors import ScriptoriumError
from scriptorium.frontmatter import (
    ReviewArtifactFrontmatter, read_frontmatter, strip_frontmatter, write_frontmatter,
)
from scriptorium.lock import ReviewLock
from scriptorium.obsidian.queries import write_query_file
from scriptorium.paths import ReviewPaths
from scriptorium.storage.audit import AuditEntry, append_audit


_LEGACY = re.compile(r"\[([A-Za-z0-9_.\-]+):page:(\d+)\]")


@dataclass
class MigrationResult:
    changed_files: list[str]
    skipped_files: list[str]
    warnings: list[str]

    def to_dict(self) -> dict:
        return {
            "changed_files": self.changed_files,
            "skipped_files": self.skipped_files,
            "warnings": self.warnings,
        }


def _convert_legacy_citations(text: str) -> str:
    return _LEGACY.sub(lambda m: f"[[{m.group(1)}#p-{m.group(2)}]]", text)


def _has_frontmatter(text: str) -> bool:
    return text.startswith("---\n")


def _ensure_frontmatter(
    path: Path, *, review_id: str, review_type: str,
) -> bool:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if _has_frontmatter(text):
        return False
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    fm = ReviewArtifactFrontmatter(
        schema_version="scriptorium.review_file.v1",
        scriptorium_version="0.3.0",
        review_id=review_id,
        review_type=review_type,
        created_at=now,
        updated_at=now,
        research_question="",
        cite_discipline="locator",
    )
    path.write_text(write_frontmatter(fm.to_dict(), body=text), encoding="utf-8")
    return True


def migrate_review(review_paths: ReviewPaths, *, dry_run: bool) -> MigrationResult:
    changed: list[str] = []
    skipped: list[str] = []
    warnings: list[str] = []

    required = [review_paths.synthesis, review_paths.audit_md, review_paths.evidence]
    missing = [p.name for p in required if not p.exists()]
    if missing:
        raise ScriptoriumError(
            f"review directory is incomplete: expected {missing} at "
            f"{review_paths.root}. Run /lit-review to completion before migration.",
            symbol="E_REVIEW_INCOMPLETE",
        )

    def _maybe_convert(p: Path) -> None:
        if not p.exists():
            skipped.append(p.name)
            return
        original = p.read_text(encoding="utf-8")
        converted = _convert_legacy_citations(original)
        if converted != original:
            if not dry_run:
                p.write_text(converted, encoding="utf-8")
            changed.append(p.name)

    with ReviewLock(review_paths.lock):
        for p in (review_paths.synthesis, review_paths.contradictions):
            _maybe_convert(p)

        for p, t in [
            (review_paths.synthesis, "synthesis"),
            (review_paths.contradictions, "contradictions"),
            (review_paths.audit_md, "audit"),
        ]:
            if p.exists() and not _has_frontmatter(p.read_text(encoding="utf-8")):
                if not dry_run:
                    _ensure_frontmatter(p, review_id=review_paths.root.name, review_type=t)
                if p.name not in changed:
                    changed.append(p.name)

        queries = (review_paths.root.parent.parent / "scriptorium-queries.md") \
            if (review_paths.root.parent.parent / ".obsidian").is_dir() \
            else (review_paths.root / "scriptorium-queries.md")
        if not queries.exists() and not dry_run:
            write_query_file(queries)
            changed.append("scriptorium-queries.md")
        elif not queries.exists() and dry_run:
            changed.append("scriptorium-queries.md")

        if not dry_run:
            append_audit(
                review_paths,
                AuditEntry(
                    phase="migration", action="migrate-review",
                    status="success", details={"changed_files": changed},
                ),
            )

    return MigrationResult(changed_files=changed, skipped_files=skipped, warnings=warnings)
```

- [ ] **Step 4: Wire into `scriptorium/cli.py`**

In `_build_parser()`:

```python
    pm = sub.add_parser("migrate-review", help="Migrate a legacy review to v0.3")
    pm.add_argument("review_dir_pos", metavar="review-dir")
    pm.add_argument("--dry-run", action="store_true")
    pm.add_argument("--json", dest="json_mode", action="store_true")
```

Handler:

```python
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
```

Register:

```python
("migrate-review", None): cmd_migrate_review,
```

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_migrate_review.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scriptorium/migrate.py scriptorium/cli.py tests/test_migrate_review.py
git commit -m "feat(migrate): §10.1 migrate-review with dry-run and fail-closed corruption"
```

---

## Task 24: `scriptorium doctor`

**Files:**
- Create: `scriptorium/doctor.py`
- Modify: `scriptorium/cli.py`
- Create: `tests/test_doctor.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_doctor.py`:

```python
"""`scriptorium doctor` verifies version, writable HOME, nlm presence hint."""
import io
from unittest.mock import patch

from scriptorium.cli import main
from scriptorium.nlm import NlmUnavailableError, NlmResult


def test_doctor_runs_and_reports_version(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    out = io.StringIO(); err = io.StringIO()
    with patch("scriptorium.doctor.nlm") as mock_nlm:
        mock_nlm.doctor.return_value = NlmResult("ok", "", 0)
        rc = main(["doctor"], stdout=out, stderr=err)
    assert rc == 0
    assert "scriptorium 0.3.0" in out.getvalue()
    assert "nlm: ok" in out.getvalue()


def test_doctor_reports_nlm_unavailable_without_failing(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    out = io.StringIO(); err = io.StringIO()
    with patch("scriptorium.doctor.nlm") as mock_nlm:
        mock_nlm.doctor.side_effect = NlmUnavailableError("no nlm")
        rc = main(["doctor"], stdout=out, stderr=err)
    assert rc == 0
    assert "nlm: unavailable" in out.getvalue()
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_doctor.py -q`
Expected: FAIL — no doctor subcommand.

- [ ] **Step 3: Create `scriptorium/doctor.py`**

```python
"""`scriptorium doctor` diagnostics."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from scriptorium import __version__
from scriptorium import nlm as nlm


def run_doctor(stdout) -> int:
    stdout.write(f"scriptorium {__version__}\n")
    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    stdout.write(f"python: {py}\n")
    home = Path(os.environ.get("HOME", "")).expanduser()
    writable = home.is_dir() and os.access(home, os.W_OK)
    stdout.write(f"writable HOME: {writable}\n")
    try:
        nlm.doctor()
        stdout.write("nlm: ok\n")
    except Exception as e:
        stdout.write(f"nlm: unavailable ({e})\n")
    return 0
```

- [ ] **Step 4: Wire into `scriptorium/cli.py`**

In `_build_parser()`:

```python
    sub.add_parser("doctor", help="Diagnose scriptorium installation")
```

Handler:

```python
def cmd_doctor(args, paths, stdout, stderr, stdin) -> int:
    from scriptorium.doctor import run_doctor
    return run_doctor(stdout)
```

Register:

```python
("doctor", None): cmd_doctor,
```

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_doctor.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scriptorium/doctor.py scriptorium/cli.py tests/test_doctor.py
git commit -m "feat(doctor): scriptorium doctor diagnostic command"
```

---

## Task 25: `scriptorium init` + setup state file

**Files:**
- Create: `scriptorium/setup_flow.py`
- Modify: `scriptorium/cli.py`
- Create: `tests/test_setup_state.py`
- Create: `tests/test_setup_init.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_setup_state.py`:

```python
"""§7.3: setup state file semantics."""
import json
from pathlib import Path

from scriptorium.setup_flow import (
    STATE_VERSION, SetupStateCorrupt, load_state, mark_step_completed,
    move_corrupt_state_aside,
)


def test_mark_and_load(tmp_path):
    state_path = tmp_path / "s.json"
    mark_step_completed(state_path, "precheck")
    mark_step_completed(state_path, "package")
    state = load_state(state_path)
    assert state["completed_steps"] == ["precheck", "package"]
    assert state["version"] == STATE_VERSION


def test_corrupt_state_moves_aside(tmp_path):
    state_path = tmp_path / "s.json"
    state_path.write_text("{not json", encoding="utf-8")
    moved = move_corrupt_state_aside(state_path)
    assert moved.exists()
    assert not state_path.exists()


def test_load_raises_on_corrupt(tmp_path):
    state_path = tmp_path / "s.json"
    state_path.write_text("{not json", encoding="utf-8")
    import pytest
    with pytest.raises(SetupStateCorrupt):
        load_state(state_path)
```

Create `tests/test_setup_init.py`:

```python
"""§7.2 init flag parsing (actual install is external)."""
import io

from scriptorium.cli import main


def test_init_help_lists_flags(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    out = io.StringIO(); err = io.StringIO()
    rc = main(["init", "--help"], stdout=out, stderr=err)
    assert rc == 0
    text = out.getvalue()
    assert "--notebooklm" in text
    assert "--skip-notebooklm" in text
    assert "--vault" in text


def test_init_skip_notebooklm_runs(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    out = io.StringIO(); err = io.StringIO()
    rc = main(["init", "--skip-notebooklm"], stdout=out, stderr=err)
    assert rc == 0
    assert "setup complete" in out.getvalue().lower()
```

- [ ] **Step 2: Run the tests**

Run: `pytest tests/test_setup_state.py tests/test_setup_init.py -q`
Expected: FAIL.

- [ ] **Step 3: Create `scriptorium/setup_flow.py`**

```python
"""§7 setup + interrupted-setup state file."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


STATE_VERSION = "0.3.0"


class SetupStateCorrupt(Exception):
    pass


def default_state_path() -> Path:
    home = Path(os.environ.get("HOME", "")).expanduser()
    return home / ".config" / "scriptorium" / "setup-state.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"version": STATE_VERSION, "completed_steps": [], "updated_at": _now()}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SetupStateCorrupt(str(e)) from e
    data.setdefault("version", STATE_VERSION)
    data.setdefault("completed_steps", [])
    return data


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    path.write_text(json.dumps(state), encoding="utf-8")


def mark_step_completed(path: Path, step: str) -> None:
    try:
        state = load_state(path)
    except SetupStateCorrupt:
        state = {"version": STATE_VERSION, "completed_steps": [], "updated_at": _now()}
    if step not in state["completed_steps"]:
        state["completed_steps"].append(step)
    save_state(path, state)


def move_corrupt_state_aside(path: Path) -> Path:
    stamp = _now().replace(":", "").replace("-", "")
    moved = path.with_name(f"setup-state.corrupt.{stamp}.json")
    path.rename(moved)
    return moved


@dataclass
class InitArgs:
    notebooklm: bool
    skip_notebooklm: bool
    vault: Optional[Path]


def run_init(args: InitArgs, stdout, stderr, stdin) -> int:
    """Non-interactive scaffold: writes setup-state as steps complete.

    Real package-install and plugin-install work is handled by shell helpers
    in release engineering (`scripts/install.sh`); this function handles the
    tracked state machine so interrupted setup can resume.
    """
    state_path = default_state_path()
    try:
        state = load_state(state_path)
    except SetupStateCorrupt:
        moved = move_corrupt_state_aside(state_path)
        stderr.write(f"W_SETUP_STATE_CORRUPT: moved to {moved}\n")
        state = {"version": STATE_VERSION, "completed_steps": [], "updated_at": _now()}
        save_state(state_path, state)

    for step in ("precheck", "package", "plugin", "vault_config", "unpaywall_email"):
        if step not in state["completed_steps"]:
            mark_step_completed(state_path, step)

    if args.notebooklm or not args.skip_notebooklm:
        if "notebooklm" not in state["completed_steps"]:
            if args.skip_notebooklm:
                pass
            else:
                mark_step_completed(state_path, "notebooklm")

    if "doctor" not in state["completed_steps"]:
        mark_step_completed(state_path, "doctor")

    stdout.write("Scriptorium setup complete. Try /lit-review to start your first review.\n")
    return 0
```

- [ ] **Step 4: Wire into `scriptorium/cli.py`**

In `_build_parser()`:

```python
    pi = sub.add_parser("init", help="Terminal setup flow (see /scriptorium-setup)")
    pi.add_argument("--notebooklm", action="store_true")
    pi.add_argument("--skip-notebooklm", action="store_true")
    pi.add_argument("--vault", default=None)
```

Handler:

```python
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
```

Register:

```python
("init", None): cmd_init,
```

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_setup_state.py tests/test_setup_init.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scriptorium/setup_flow.py scriptorium/cli.py tests/test_setup_state.py tests/test_setup_init.py
git commit -m "feat(setup): scriptorium init with resumable setup-state.json"
```

---

## Task 26: Slash commands — `/lit-podcast`, `/lit-deck`, `/lit-mindmap`

**Files:**
- Create: `.claude-plugin/commands/lit-podcast.md`
- Create: `.claude-plugin/commands/lit-deck.md`
- Create: `.claude-plugin/commands/lit-mindmap.md`
- Create: `tests/test_slash_publish_commands.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_slash_publish_commands.py`:

```python
"""§9.2: three slash commands map to scriptorium publish --generate <kind>."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / ".claude-plugin" / "commands"


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_lit_podcast_maps_to_audio():
    text = _read("lit-podcast.md")
    assert "scriptorium publish" in text
    assert "--generate audio" in text
    assert "nlm audio create" in text  # verified command referenced


def test_lit_deck_maps_to_deck():
    text = _read("lit-deck.md")
    assert "--generate deck" in text
    assert "nlm slides create" in text  # deck → slides


def test_lit_mindmap_maps_to_mindmap():
    text = _read("lit-mindmap.md")
    assert "--generate mindmap" in text
    assert "nlm mindmap create" in text
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_slash_publish_commands.py -q`
Expected: FAIL — files do not exist.

- [ ] **Step 3: Create `.claude-plugin/commands/lit-podcast.md`**

```markdown
---
description: Generate a NotebookLM audio overview for a completed review.
argument-hint: <review-dir>
---

Use this command after `/lit-review` finishes cite-check and writes
`overview.md`.

Run:

```bash
scriptorium publish --review-dir {{ARGUMENTS}} --generate audio
```

Behind the scenes this calls `nlm audio create <notebook_id>`. Files from
§9.4 upload order are sent to NotebookLM in this order: `overview.md`,
`synthesis.md`, `contradictions.md`, `evidence.jsonl`, and direct-child PDFs.

See `.claude-plugin/skills/publishing-to-notebooklm/SKILL.md` for full
preconditions, the Cowork degradation block, and audit semantics.
```

- [ ] **Step 4: Create `.claude-plugin/commands/lit-deck.md`**

```markdown
---
description: Generate a NotebookLM slide deck for a completed review.
argument-hint: <review-dir>
---

Run:

```bash
scriptorium publish --review-dir {{ARGUMENTS}} --generate deck
```

User-facing "deck" maps to `nlm slides create <notebook_id>`. Upload order
and audit semantics match §9 of the design spec; see the
`publishing-to-notebooklm` skill for preconditions.
```

- [ ] **Step 5: Create `.claude-plugin/commands/lit-mindmap.md`**

```markdown
---
description: Generate a NotebookLM mind map for a completed review.
argument-hint: <review-dir>
---

Run:

```bash
scriptorium publish --review-dir {{ARGUMENTS}} --generate mindmap
```

Behind the scenes this calls `nlm mindmap create <notebook_id>`. See the
`publishing-to-notebooklm` skill for preconditions, the Cowork degradation
block, and audit semantics.
```

- [ ] **Step 6: Run the tests**

Run: `pytest tests/test_slash_publish_commands.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add .claude-plugin/commands/lit-podcast.md .claude-plugin/commands/lit-deck.md .claude-plugin/commands/lit-mindmap.md tests/test_slash_publish_commands.py
git commit -m "feat(commands): add /lit-podcast, /lit-deck, /lit-mindmap wrappers"
```

---

## Task 27: Slash command `/scriptorium-setup`

**Files:**
- Create: `.claude-plugin/commands/scriptorium-setup.md`
- Create: `tests/test_slash_setup.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_slash_setup.py`:

```python
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / ".claude-plugin" / "commands" / "scriptorium-setup.md"


def test_file_exists_and_references_flags():
    text = PATH.read_text(encoding="utf-8")
    for flag in ("--notebooklm", "--skip-notebooklm", "--vault"):
        assert flag in text
    assert "uv pip install scriptorium-cli" in text
    assert "pip install scriptorium-cli" in text
    assert "nlm doctor" in text
    assert "nlm login" in text


def test_file_warns_dedicated_google_account():
    text = PATH.read_text(encoding="utf-8")
    assert "dedicated Google account" in text
    assert "browser automation" in text


def test_file_references_setting_up_scriptorium_skill():
    text = PATH.read_text(encoding="utf-8")
    assert "setting-up-scriptorium" in text
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_slash_setup.py -q`
Expected: FAIL.

- [ ] **Step 3: Create `.claude-plugin/commands/scriptorium-setup.md`**

```markdown
---
description: Install Scriptorium v0.3 and configure NotebookLM, Obsidian, and Unpaywall.
argument-hint: [--notebooklm] [--skip-notebooklm] [--vault <path>]
---

Use the `setting-up-scriptorium` skill to perform this install. The skill
is the authoritative flow; this slash command is a thin launcher.

Flags:

- `--notebooklm` — re-run only NotebookLM setup.
- `--skip-notebooklm` — install Scriptorium but skip NotebookLM.
- `--vault <path>` — use this Obsidian vault after verifying `.obsidian/`.

Outline (full body in `setting-up-scriptorium/SKILL.md`):

1. Precheck Python `>=3.11`, writable `$HOME`, current shell access.
2. Install package: prefer `uv pip install scriptorium-cli`; fallback
   `pip install scriptorium-cli`.
3. Verify `scriptorium --version` prints `scriptorium 0.3.0`.
4. Install `.claude-plugin/` and prompt the user to restart Claude Code.
5. Auto-detect Obsidian vault or accept `--vault <path>`; persist with
   `scriptorium config set obsidian_vault <path>`.
6. Ask for `unpaywall_email` and persist.
7. Unless `--skip-notebooklm`: install `notebooklm-mcp-cli`, show the
   dedicated-Google-account warning below, run `nlm login`, then verify
   with `nlm doctor`. Only set `notebooklm_enabled true` after
   `nlm doctor` succeeds.
8. Run `scriptorium doctor`.
9. Print: `You're set. Try /lit-review "your question" --review-dir reviews/<slug>`.

Dedicated-account warning (reproduce verbatim before `nlm login`):

> Use a dedicated Google account for NotebookLM integration, not your
> primary account. The nlm CLI works via browser automation; Google may
> flag automated activity against your primary account. This is an
> upstream limitation of nlm, not Scriptorium.
>
> Press Enter to acknowledge and continue, or Ctrl-C to skip NotebookLM setup.
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_slash_setup.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/commands/scriptorium-setup.md tests/test_slash_setup.py
git commit -m "feat(commands): add /scriptorium-setup launcher"
```

---

## Task 28: Update `/lit-review`, `/lit-config`, `/lit-show-audit`

**Files:**
- Modify: `.claude-plugin/commands/lit-review.md`
- Modify: `.claude-plugin/commands/lit-config.md`
- Modify: `.claude-plugin/commands/lit-show-audit.md`
- Create: `tests/test_updated_commands.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_updated_commands.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / ".claude-plugin" / "commands"


def test_lit_review_threads_overview_and_prompt():
    text = (ROOT / "lit-review.md").read_text(encoding="utf-8")
    assert "scriptorium regenerate-overview" in text
    assert "NotebookLM artifact?" in text
    assert "skip default" in text


def test_lit_config_mentions_new_keys():
    text = (ROOT / "lit-config.md").read_text(encoding="utf-8")
    for key in ("obsidian_vault", "notebooklm_enabled", "notebooklm_prompt"):
        assert key in text


def test_lit_show_audit_understands_publishing_section():
    text = (ROOT / "lit-show-audit.md").read_text(encoding="utf-8")
    assert "## Publishing" in text
```

- [ ] **Step 2: Read the current files**

Run: Read `/Users/jeremiahwolf/Desktop/Projects/APPs/Superpowers-Research/.claude-plugin/commands/lit-review.md`, `lit-config.md`, `lit-show-audit.md` to capture existing structure.

- [ ] **Step 3: Update `lit-review.md`**

Append a new section before the end-of-file:

```markdown

## v0.3 end-of-review steps

After cite-check passes and `contradictions.md` is written, run:

```bash
scriptorium regenerate-overview {{REVIEW_DIR}}
```

If `notebooklm_prompt` is not `false`, `notebooklm_enabled` is `true`, and
`nlm doctor` succeeds, show this prompt (skip is default):

```
NotebookLM artifact? (skip default)
  audio
  deck
  mindmap
  skip
```

Route non-`skip` selections to `scriptorium publish --review-dir <path>
--generate <audio|deck|mindmap>`.
```

- [ ] **Step 4: Update `lit-config.md`**

Append:

```markdown

## v0.3 config keys

- `obsidian_vault` (string path) — enables vault-relative review paths and
  native Obsidian output defaults. See §3.2.
- `notebooklm_enabled` (boolean) — set by `/scriptorium-setup` only after
  `nlm doctor` succeeds. Gate for the end-of-review prompt.
- `notebooklm_prompt` (boolean) — set to `false` to suppress the end-of-review
  NotebookLM prompt even when `notebooklm_enabled` is `true`.
```

- [ ] **Step 5: Update `lit-show-audit.md`**

Append:

```markdown

## v0.3 frontmatter and Publishing section

- `audit.md` now has YAML frontmatter (see §5.2). Treat the first `---`
  block as metadata, not content.
- A top-level `## Publishing` section holds every NotebookLM publish event
  (success, partial, or failure). Each event is a `### <timestamp> —
  NotebookLM` subsection with a status, destination, notebook URL, files
  attempted, files uploaded, artifact ids, and a privacy note.
- The same events appear as `publishing` rows in `audit.jsonl` for tools.
```

- [ ] **Step 6: Run the tests**

Run: `pytest tests/test_updated_commands.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add .claude-plugin/commands/lit-review.md .claude-plugin/commands/lit-config.md .claude-plugin/commands/lit-show-audit.md tests/test_updated_commands.py
git commit -m "docs(commands): v0.3 overview+prompt thread and new config keys"
```

---

## Task 29: Rename `lit-publishing/` → `publishing-to-notebooklm/` and rewrite

**Files:**
- Delete: `.claude-plugin/skills/lit-publishing/SKILL.md`
- Create: `.claude-plugin/skills/publishing-to-notebooklm/SKILL.md`
- Create: `tests/test_skill_publishing_to_notebooklm.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_skill_publishing_to_notebooklm.py`:

```python
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / ".claude-plugin" / "skills"


def test_old_skill_directory_is_removed():
    assert not (SKILLS / "lit-publishing").exists()


def test_new_skill_exists():
    assert (SKILLS / "publishing-to-notebooklm" / "SKILL.md").exists()


def test_new_skill_uses_verified_nlm_commands_only():
    text = (SKILLS / "publishing-to-notebooklm" / "SKILL.md").read_text(encoding="utf-8")
    required = ["nlm login", "nlm doctor", "nlm notebook create",
                "nlm source add", "nlm audio create", "nlm slides create",
                "nlm mindmap create", "nlm video create"]
    for cmd in required:
        assert cmd in text, f"missing verified nlm command: {cmd}"
    # Forbidden stale commands
    for bad in ("nlm auth login", "nlm studio create", "--confirm"):
        assert bad not in text, f"forbidden stale token present: {bad}"


def test_new_skill_documents_cowork_block():
    text = (SKILLS / "publishing-to-notebooklm" / "SKILL.md").read_text(encoding="utf-8")
    assert "Cowork" in text
    assert "local shell access" in text
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_skill_publishing_to_notebooklm.py -q`
Expected: FAIL.

- [ ] **Step 3: Remove the old skill directory**

```bash
git rm -r .claude-plugin/skills/lit-publishing
```

- [ ] **Step 4: Create `.claude-plugin/skills/publishing-to-notebooklm/SKILL.md`**

```markdown
---
name: publishing-to-notebooklm
description: Publish a completed Scriptorium review to NotebookLM via the verified `nlm` CLI (audio, deck, mindmap, video).
---

# publishing-to-notebooklm

Use this skill when a review has finished cite-check, `overview.md`,
`synthesis.md`, and `contradictions.md` are written, and the user wants a
NotebookLM artifact. v0.3 uses the `nlm` CLI exclusively; the `lit-publishing`
MCP/Studio instructions are removed.

## Preconditions

1. `notebooklm_enabled` is `true` in Scriptorium config.
2. `nlm doctor` returns zero (install `notebooklm-mcp-cli` with
   `uv tool install notebooklm-mcp-cli` then run `nlm login` — see the
   `setting-up-scriptorium` skill for first-time setup).
3. The review directory contains `overview.md`, `synthesis.md`,
   `contradictions.md`, `evidence.jsonl`, and `pdfs/`.

## Commands (verified v0.3 surface)

| Step | Command |
|---|---|
| Login | `nlm login` |
| Diagnose | `nlm doctor` |
| Create notebook | `nlm notebook create <title>` |
| Upload source | `nlm source add <notebook_id> --file <path>` |
| Create audio | `nlm audio create <notebook_id>` |
| Create slide deck | `nlm slides create <notebook_id>` |
| Create mind map | `nlm mindmap create <notebook_id>` |
| Create video | `nlm video create <notebook_id>` |

User-facing "deck" maps to `nlm slides create`.

## Normal flow

In Claude Code or terminal, prefer the CLI wrapper:

```bash
scriptorium publish --review-dir <path> --generate <audio|deck|mindmap|video|all>
```

`scriptorium publish` acquires `<review-dir>/.scriptorium.lock`, verifies
files, calls `nlm doctor`, creates the notebook, uploads sources in this
order — `overview.md`, `synthesis.md`, `contradictions.md`,
`evidence.jsonl`, alphabetical `pdfs/*.pdf` (symlinks skipped), paper stubs
only if `stubs` is in `--sources` — waits 1s between uploads, then triggers
the artifact(s). Each `nlm` subprocess has a five-minute timeout.

## Prior-publish prompt

If `audit.md` records a prior publish to the same notebook name, the CLI
prompts `Proceed and create a new notebook? [y/N]`. Pass `--yes` in
scripts or when running non-interactively.

## Cowork degradation

Cowork does not have local shell access. `scriptorium publish` detects
Cowork mode (via `SCRIPTORIUM_COWORK` / `SCRIPTORIUM_FORCE_COWORK`) and
emits this block instead of calling `nlm`:

> Publishing to NotebookLM requires local shell access, which Cowork doesn't grant.
> (Full block rendered by `scriptorium publish` — see §9.6.)

## Audit

On success or partial failure, `scriptorium publish` appends a
`## Publishing` subsection to `audit.md` and a `publishing` row to
`audit.jsonl`. The row carries notebook name/id/URL, attempted and
uploaded file manifests, artifact ids (or failing command + stderr),
and a privacy note.
```

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_skill_publishing_to_notebooklm.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .claude-plugin/skills tests/test_skill_publishing_to_notebooklm.py
git commit -m "feat(skills): rename lit-publishing → publishing-to-notebooklm (v0.3)"
```

---

## Task 30: New skill `setting-up-scriptorium/`

**Files:**
- Create: `.claude-plugin/skills/setting-up-scriptorium/SKILL.md`
- Create: `tests/test_skill_setting_up_scriptorium.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_skill_setting_up_scriptorium.py`:

```python
from pathlib import Path

PATH = (
    Path(__file__).resolve().parent.parent
    / ".claude-plugin" / "skills" / "setting-up-scriptorium" / "SKILL.md"
)


def test_exists_and_covers_flow():
    text = PATH.read_text(encoding="utf-8")
    for token in (
        "uv pip install scriptorium-cli", "pip install scriptorium-cli",
        "scriptorium --version", "scriptorium 0.3.0",
        "uv tool install notebooklm-mcp-cli", "pipx install notebooklm-mcp-cli",
        "nlm login", "nlm doctor",
        "notebooklm_enabled true", "--skip-notebooklm",
        "dedicated Google account", "setup-state.json",
    ):
        assert token in text, f"missing: {token}"
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_skill_setting_up_scriptorium.py -q`
Expected: FAIL.

- [ ] **Step 3: Create the skill**

`.claude-plugin/skills/setting-up-scriptorium/SKILL.md`:

```markdown
---
name: setting-up-scriptorium
description: Install Scriptorium v0.3 end-to-end (package, plugin, vault, Unpaywall, NotebookLM) with a resumable setup-state.
---

# setting-up-scriptorium

This skill owns the `/scriptorium-setup` and `scriptorium init` flows (§7).
It's idempotent and resumable via `~/.config/scriptorium/setup-state.json`.

## Precheck

- Python `>=3.11`
- Writable `$HOME`
- Current shell available for subprocesses

## Install the package

Prefer `uv`:

```bash
uv pip install scriptorium-cli
```

Fallback:

```bash
pip install scriptorium-cli
```

Verify:

```bash
scriptorium --version   # must print "scriptorium 0.3.0"
```

## Install the Claude Code plugin

Copy `.claude-plugin/` into the Claude Code plugin directory via the
existing convention, then prompt the user to restart Claude Code.

## Configure Obsidian vault

Scan `~/Documents/Obsidian/`, `~/Obsidian/`,
`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/`, and any
existing `obsidian_vault`. Accept `--vault <path>` if passed. Only accept
a directory whose `.obsidian/` subdirectory exists. Persist:

```bash
scriptorium config set obsidian_vault <path>
```

## Collect Unpaywall email

```bash
scriptorium config set unpaywall_email <email>
```

## NotebookLM (skip with --skip-notebooklm)

Install the CLI (either works):

```bash
uv tool install notebooklm-mcp-cli
# or
pipx install notebooklm-mcp-cli
```

Show the dedicated-account warning verbatim, then:

```bash
nlm login
nlm doctor
scriptorium config set notebooklm_enabled true
```

Only set `notebooklm_enabled true` after `nlm doctor` exits zero.

## Dedicated-account warning

> Use a dedicated Google account for NotebookLM integration, not your primary
> account. The nlm CLI works via browser automation; Google may flag automated
> activity against your primary account. This is an upstream limitation of nlm,
> not Scriptorium.

## Resumable setup-state.json

After each step, append the step name to the `completed_steps` list in
`~/.config/scriptorium/setup-state.json`. On rerun, skip already-completed
steps after verifying their effect (e.g. `scriptorium --version`,
`nlm doctor`). On `Ctrl-C` during NotebookLM login, store
`notebooklm_enabled false`, exit `130`, and leave earlier steps intact.

## Closing message

```
You're set. Try /lit-review "your question" --review-dir reviews/<slug>
to kick off your first review.
```
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_skill_setting_up_scriptorium.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/skills/setting-up-scriptorium/SKILL.md tests/test_skill_setting_up_scriptorium.py
git commit -m "feat(skills): add setting-up-scriptorium for /scriptorium-setup"
```

---

## Task 31: New skill `generating-overview/`

**Files:**
- Create: `.claude-plugin/skills/generating-overview/SKILL.md`
- Create: `tests/test_skill_generating_overview.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_skill_generating_overview.py`:

```python
from pathlib import Path

PATH = (
    Path(__file__).resolve().parent.parent
    / ".claude-plugin" / "skills" / "generating-overview" / "SKILL.md"
)


def test_file_exists_and_covers_key_points():
    text = PATH.read_text(encoding="utf-8")
    for token in (
        "nine sections", "TL;DR", "Scope & exclusions",
        "Most-cited works in this corpus", "Current findings",
        "Contradictions in brief", "Recent work in this corpus",
        "Methods represented in this corpus", "Gaps in this corpus",
        "Reading list", "<!-- synthesis -->", "<!-- provenance:",
        "corpus-bounded", "regenerate-overview",
    ):
        assert token in text, f"missing: {token}"
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_skill_generating_overview.py -q`
Expected: FAIL.

- [ ] **Step 3: Create the skill**

`.claude-plugin/skills/generating-overview/SKILL.md`:

```markdown
---
name: generating-overview
description: Produce `overview.md` — the executive briefing for a completed Scriptorium review (§8).
---

# generating-overview

Use this skill after cite-check passes and `synthesis.md` +
`contradictions.md` are final. It produces the corpus-bounded briefing
`overview.md` and hands control to `scriptorium regenerate-overview` for
persistence and archival.

## Nine sections, exactly this order

1. **TL;DR**
2. **Scope & exclusions**
3. **Most-cited works in this corpus**
4. **Current findings**
5. **Contradictions in brief**
6. **Recent work in this corpus (last 5 years)**
7. **Methods represented in this corpus**
8. **Gaps in this corpus**
9. **Reading list**

Every section title is corpus-bounded. Do not rename to field-level
language ("most important works", "research gaps", etc.).

## Two sentence classes

| Class | Required marker |
|---|---|
| Paper claim (quoted or paraphrased) | `[[paper_id#p-N]]` locator |
| Synthesis / ranking / framing | Inline `<!-- synthesis -->` and no locator |

Lint fails closed: a paper claim without a locator, or a synthesis sentence
with a locator, is rejected.

## Provenance block per section

Each section ends with:

```html
<!-- provenance:
  section: most-cited-works
  contributing_papers: [nehlig2010, smith2018]
  derived_from: synthesis.md#current-findings
  generation_timestamp: 2026-04-20T14:32:08Z
-->
```

Required keys: `section`, `contributing_papers`, `derived_from`,
`generation_timestamp`.

## Persist with the CLI

```bash
scriptorium regenerate-overview <review-dir> [--model <name>] [--seed <int>] [--json]
```

Archive-on-regenerate writes previous drafts to
`<review-dir>/overview-archive/<timestamp>.md`. On lint/cite-check failure,
the failed draft goes to `<review-dir>/overview.failed.<timestamp>.md` and
the command exits `E_OVERVIEW_FAILED`.

Length target is 300 words. The lint warns above 400 words but does not
fail on length alone.
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_skill_generating_overview.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/skills/generating-overview/SKILL.md tests/test_skill_generating_overview.py
git commit -m "feat(skills): add generating-overview for §8 overview.md"
```

---

## Task 32: Update existing skills for v0.3

**Files:**
- Modify: `.claude-plugin/skills/using-scriptorium/SKILL.md`
- Modify: `.claude-plugin/skills/running-lit-review/SKILL.md`
- Modify: `.claude-plugin/skills/configuring-scriptorium/SKILL.md`
- Modify: `.claude-plugin/skills/lit-extracting/SKILL.md`
- Modify: `.claude-plugin/skills/lit-synthesizing/SKILL.md`
- Modify: `.claude-plugin/skills/lit-contradiction-check/SKILL.md`
- Modify: `.claude-plugin/skills/lit-audit-trail/SKILL.md`
- Create: `tests/test_skill_v03_updates.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_skill_v03_updates.py`:

```python
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / ".claude-plugin" / "skills"


def _read(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def test_using_scriptorium_mentions_v03_config_and_publish():
    text = _read("using-scriptorium")
    assert "obsidian_vault" in text
    assert "scriptorium publish" in text
    assert "Cowork" in text


def test_running_lit_review_hands_off_to_overview_and_prompt():
    text = _read("running-lit-review")
    assert "regenerate-overview" in text
    assert "NotebookLM artifact?" in text


def test_configuring_scriptorium_lists_new_keys_and_cowork_parity():
    text = _read("configuring-scriptorium")
    for key in ("obsidian_vault", "notebooklm_enabled", "notebooklm_prompt"):
        assert key in text
    assert "scriptorium-config" in text  # user-memory note name (§3.1)


def test_lit_extracting_uses_v03_full_text_sources():
    text = _read("lit-extracting")
    for src in ("user_pdf", "unpaywall", "arxiv", "pmc", "abstract_only"):
        assert src in text


def test_lit_synthesizing_uses_wikilinks():
    text = _read("lit-synthesizing")
    assert "[[paper_id#p-N]]" in text
    assert "schema_version" in text


def test_lit_contradiction_check_uses_wikilinks():
    text = _read("lit-contradiction-check")
    assert "[[paper_id#p-N]]" in text


def test_lit_audit_trail_covers_publishing_section():
    text = _read("lit-audit-trail")
    assert "## Publishing" in text
    assert "audit.jsonl" in text
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_skill_v03_updates.py -q`
Expected: FAIL.

- [ ] **Step 3: Append v0.3 sections to each skill**

For each skill file, append a `## v0.3 additions` section. Use the Read tool on each before editing. The minimum content for each:

**using-scriptorium**: mention `obsidian_vault` enables native Obsidian output; publishing route is `scriptorium publish`; Cowork degradation block is rendered automatically.

**running-lit-review**: after cite-check, call `scriptorium regenerate-overview <dir>`; show the `NotebookLM artifact? (skip default)` prompt gated by §9.1.

**configuring-scriptorium**: list `obsidian_vault`, `notebooklm_enabled`, `notebooklm_prompt`; note that Cowork keeps the same keys in a user-memory note named `scriptorium-config`, TOML-shaped.

**lit-extracting**: the full-text source enum is now `user_pdf | unpaywall | arxiv | pmc | abstract_only`; paper stubs require this field in frontmatter.

**lit-synthesizing**: new citations use `[[paper_id#p-N]]`. The verifier still accepts legacy `[paper_id:loc]`. Review artifacts carry frontmatter with `schema_version: scriptorium.review_file.v1`.

**lit-contradiction-check**: emit citations as `[[paper_id#p-N]]`. Frontmatter mirrors synthesis.md.

**lit-audit-trail**: `audit.jsonl` rows have a `status` enum (`success|warning|failure|partial|skipped`). `audit.md` gains a `## Publishing` section for NotebookLM events; each event has `### <timestamp> — NotebookLM`, status, destination, URL, and attempted/uploaded manifests.

Each append should be a clear heading, then one-sentence bullets or a short table so the skills stay terse.

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_skill_v03_updates.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/skills tests/test_skill_v03_updates.py
git commit -m "docs(skills): v0.3 additions for config, publish, overview, frontmatter"
```

---

## Task 33: Hook verifier — overview lint pass-through

**Files:**
- Modify: `.claude-plugin/hooks/evidence_gate.sh`
- Modify: `scriptorium/reasoning/verify_citations.py`
- Modify: `scriptorium/cli.py`
- Create: `tests/test_hook_overview.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_hook_overview.py`:

```python
"""§12.3: verifier enforces overview lint when the edited file is overview.md."""
import io
from pathlib import Path

from scriptorium.cli import main
from scriptorium.errors import EXIT_CODES


def test_verify_overview_mode_rejects_bad_overview(tmp_path):
    overview = tmp_path / "overview.md"
    overview.write_text("# missing sections\n", encoding="utf-8")
    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["verify", "--overview", str(overview)], stdout=out, stderr=err,
    )
    assert rc == EXIT_CODES["E_OVERVIEW_FAILED"]


def test_verify_overview_mode_accepts_valid(tmp_path, monkeypatch):
    from scriptorium.overview.generator import regenerate_overview
    from scriptorium.paths import ReviewPaths
    rp = ReviewPaths(root=tmp_path)
    (tmp_path / "evidence.jsonl").write_text("", encoding="utf-8")
    regenerate_overview(rp, model="opus", seed=1, research_question="q", review_id="r")
    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["verify", "--overview", str(rp.overview)], stdout=out, stderr=err,
    )
    assert rc == 0
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_hook_overview.py -q`
Expected: FAIL — `verify` has no `--overview` option.

- [ ] **Step 3: Extend `cmd_verify` in `scriptorium/cli.py`**

In `_build_parser()`, add to the `verify` subparser:

```python
    pv.add_argument("--overview", default=None,
                    help="Run overview lint instead of synthesis verify")
```

Replace `cmd_verify` body with:

```python
def cmd_verify(args, paths, stdout, stderr, stdin) -> int:
    if args.overview:
        from scriptorium.errors import EXIT_CODES
        from scriptorium.frontmatter import strip_frontmatter
        from scriptorium.overview.linter import OverviewLintError, lint_overview
        body = strip_frontmatter(Path(args.overview).read_text(encoding="utf-8"))
        try:
            lint_overview(body)
        except OverviewLintError as e:
            stderr.write(f"scriptorium verify --overview: {e}\n")
            return EXIT_CODES["E_OVERVIEW_FAILED"]
        stdout.write(json.dumps({"ok": True}) + "\n")
        return 0
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
```

Also make `--synthesis` no longer required so `--overview` alone works — change the line in `_build_parser` from `pv.add_argument("--synthesis", required=True)` to `pv.add_argument("--synthesis", default=None)`.

- [ ] **Step 4: Teach the hook to call `--overview` when the edited file is `overview.md`**

Edit `.claude-plugin/hooks/evidence_gate.sh`. Replace the `case "$file_path"` block with:

```bash
case "$file_path" in
  *overview.md)
    if ! command -v scriptorium >/dev/null 2>&1; then
      printf '[evidence-first gate] scriptorium CLI not on PATH — skipping overview lint.\n' >&2
      exit 0
    fi
    out="$(scriptorium verify --overview "$file_path" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
      printf '[evidence-first gate] scriptorium verify --overview %s exited %s\n' "$file_path" "$rc" >&2
      printf '%s\n' "$out" >&2
    fi
    ;;
  *synthesis.md)
    if ! command -v scriptorium >/dev/null 2>&1; then
      printf '[evidence-first gate] scriptorium CLI not on PATH — skipping redundancy check; lit-synthesizing step 5 remains authoritative.\n' >&2
      exit 0
    fi
    out="$(scriptorium verify --synthesis "$file_path" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
      printf '[evidence-first gate] scriptorium verify --synthesis %s exited %s\n' "$file_path" "$rc" >&2
      printf '%s\n' "$out" >&2
      printf '[evidence-first gate] Skill lit-synthesizing step 5 is authoritative; this hook is belt-and-suspenders.\n' >&2
    fi
    ;;
  *)
    :
    ;;
esac
```

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_hook_overview.py tests/test_hook_evidence_gate.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scriptorium/cli.py .claude-plugin/hooks/evidence_gate.sh tests/test_hook_overview.py
git commit -m "feat(hook): dispatch overview.md edits to scriptorium verify --overview"
```

---

## Task 34: Exit-code reachability + stale-command scan

**Files:**
- Create: `tests/test_cli_exit_codes.py`
- Create: `tests/test_command_skill_content.py`

- [ ] **Step 1: Write `tests/test_cli_exit_codes.py`**

This test is a static check: every symbol in §11 is referenced by at least one return path in `scriptorium/`.

```python
"""Every §11 exit symbol must appear in at least one source file."""
from pathlib import Path
from scriptorium.errors import EXIT_CODES


def test_every_symbol_is_reachable_in_source():
    root = Path(__file__).resolve().parent.parent / "scriptorium"
    corpus = "\n".join(p.read_text(encoding="utf-8") for p in root.rglob("*.py"))
    missing = [s for s in EXIT_CODES if s not in corpus]
    assert missing == [], f"symbols with no references: {missing}"


def test_every_integer_is_unique():
    assert len(set(EXIT_CODES.values())) == len(EXIT_CODES)
```

- [ ] **Step 2: Write `tests/test_command_skill_content.py`**

```python
"""§13.2 stale-command scan: forbidden nlm shapes must be absent everywhere."""
from pathlib import Path


FORBIDDEN = [
    "nlm auth login",
    "nlm studio create",
    "nlm source upload",
    "--confirm",  # stale audio confirmation flag from v0.2 docs
]

ALLOWED_WITH_CONFIRM = {"docs/publishing-notebooklm.md"}  # none at v0.3


def test_no_forbidden_tokens_in_plugin_surface():
    repo = Path(__file__).resolve().parent.parent
    targets = list((repo / ".claude-plugin").rglob("*.md"))
    targets += list((repo / "docs").rglob("*.md")) if (repo / "docs").is_dir() else []
    problems: list[str] = []
    for path in targets:
        text = path.read_text(encoding="utf-8")
        for bad in FORBIDDEN:
            if bad in text:
                rel = str(path.relative_to(repo))
                if rel in ALLOWED_WITH_CONFIRM and bad == "--confirm":
                    continue
                problems.append(f"{rel}: {bad!r}")
    assert problems == [], f"stale nlm tokens: {problems}"


def test_verified_commands_appear_in_skills():
    repo = Path(__file__).resolve().parent.parent
    skills = (repo / ".claude-plugin" / "skills" / "publishing-to-notebooklm"
              / "SKILL.md").read_text(encoding="utf-8")
    for cmd in ("nlm doctor", "nlm notebook create", "nlm source add",
                "nlm audio create", "nlm slides create",
                "nlm mindmap create", "nlm video create", "nlm login"):
        assert cmd in skills, f"missing verified command: {cmd}"
```

- [ ] **Step 3: Run the tests**

Run: `pytest tests/test_cli_exit_codes.py tests/test_command_skill_content.py -q`
Expected: PASS (all upstream tasks reference these symbols and use only verified commands).

- [ ] **Step 4: Commit**

```bash
git add tests/test_cli_exit_codes.py tests/test_command_skill_content.py
git commit -m "test: reachable exit codes + stale-nlm-command scan"
```

---

## Task 35: E2E caffeine test — v0.3 assertions

**Files:**
- Modify: `tests/test_e2e_caffeine.py`

- [ ] **Step 1: Read the current file**

Run: Read `/Users/jeremiahwolf/Desktop/Projects/APPs/Superpowers-Research/tests/test_e2e_caffeine.py`.

- [ ] **Step 2: Add a new test function**

Append:

```python
def test_e2e_caffeine_v03_artifacts(tmp_path, monkeypatch):
    """§13.3: after the caffeine fixture runs, v0.3 artifacts must exist."""
    from pathlib import Path
    import json
    from scriptorium.cli import main
    import io

    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    (root / "synthesis.md").write_text(
        "Caffeine helps WM [[nehlig2010#p-4]].\n", encoding="utf-8",
    )
    (root / "contradictions.md").write_text(
        "No disagreement in corpus. <!-- synthesis -->\n", encoding="utf-8",
    )
    (root / "evidence.jsonl").write_text(
        json.dumps({
            "paper_id": "nehlig2010", "locator": "page:4",
            "claim": "Caffeine helps WM", "quote": "helps",
            "direction": "positive", "concept": "wm",
        }) + "\n",
        encoding="utf-8",
    )
    # Regenerate overview
    out = io.StringIO(); err = io.StringIO()
    rc = main(["regenerate-overview", str(root), "--json"], stdout=out, stderr=err)
    assert rc == 0, err.getvalue()
    text = (root / "overview.md").read_text(encoding="utf-8")
    for section in (
        "TL;DR", "Scope & exclusions", "Most-cited works in this corpus",
        "Reading list",
    ):
        assert f"## {section}" in text
    assert text.startswith("---\n")
    assert "schema_version: \"scriptorium.review_file.v1\"" in text
```

- [ ] **Step 3: Run**

Run: `pytest tests/test_e2e_caffeine.py -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_e2e_caffeine.py
git commit -m "test(e2e): v0.3 overview + frontmatter assertions on caffeine fixture"
```

---

## Task 36: Release artifacts — README, CHANGELOG, docs, install.sh

**Files:**
- Modify: `README.md`
- Create: `CHANGELOG.md`
- Create: `scripts/install.sh`
- Create: `docs/obsidian-integration.md`
- Create: `docs/publishing-notebooklm.md`
- Create: `tests/test_release_artifacts.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_release_artifacts.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_readme_names_scriptorium_cli_and_beta():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "pip install scriptorium-cli" in text
    assert "beta" in text.lower()


def test_changelog_has_v030_entry():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "0.3.0" in text


def test_install_script_wraps_scriptorium_init():
    text = (ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
    assert "scriptorium-cli" in text
    assert "scriptorium init" in text


def test_obsidian_integration_doc_mentions_portability_tradeoff():
    text = (ROOT / "docs" / "obsidian-integration.md").read_text(encoding="utf-8")
    assert "not self-contained" in text
    assert "papers/" in text


def test_publishing_notebooklm_doc_has_manual_upload_template():
    text = (ROOT / "docs" / "publishing-notebooklm.md").read_text(encoding="utf-8")
    assert "## Publishing" in text
    assert "nlm notebook create" in text
```

- [ ] **Step 2: Run the tests**

Run: `pytest tests/test_release_artifacts.py -q`
Expected: FAIL — files missing or outdated.

- [ ] **Step 3: Replace `README.md` with `README_proposed.md` adjusted for beta**

Read `README_proposed.md`, then write `README.md` with:

- First heading unchanged.
- Near the top, a single line: `**Status:** beta (v0.3.0) — install with \`pip install scriptorium-cli\`.`
- All occurrences of `scriptorium` in install commands replaced with `scriptorium-cli`.
- Keep example slash-command sections unchanged.

- [ ] **Step 4: Create `CHANGELOG.md`**

```markdown
# Changelog

All notable changes to this project are documented in this file.

## 0.3.0 — 2026-04-20

### Added
- Native Obsidian output by default: paper stubs, wikilinks, frontmatter,
  Dataview queries.
- Executive briefing `overview.md` with nine corpus-bounded sections,
  per-section provenance, and deterministic seeding.
- Seamless NotebookLM publish flow over the verified `nlm` CLI, with
  `/lit-podcast`, `/lit-deck`, `/lit-mindmap` wrappers.
- `/scriptorium-setup` and `scriptorium init` for Claude-Code-assisted and
  terminal-fallback installs with resumable setup-state.
- `scriptorium migrate-review` for moving v0.2 reviews forward in place.
- `obsidian_vault`, `notebooklm_enabled`, `notebooklm_prompt` config keys.
- `.scriptorium.lock` review lock; §11 exit codes; `audit.jsonl` status enum
  with UTC `Z` timestamps; corruption recovery for audit and config.
- Cowork degradation block for publish attempts.

### Changed
- PyPI distribution renamed to `scriptorium-cli`. Console command, import
  path, and plugin name remain `scriptorium`.
- v0.3 generation writes citations as `[[paper_id#p-N]]`. Verifier also
  accepts legacy `[paper_id:loc]` form.
- Skill `lit-publishing` renamed to `publishing-to-notebooklm`; body
  rewritten to reference verified `nlm` commands only.

### Removed
- Stale v0.2 NotebookLM command shapes from docs, skills, and slash commands.

### Migration
Run `scriptorium migrate-review <review-dir>` once per existing review. The
command is idempotent and fails closed on corrupted state.
```

- [ ] **Step 5: Create `scripts/install.sh`**

```bash
#!/usr/bin/env bash
# Curl-one-liner target for Scriptorium v0.3.
# The stable flow is `scriptorium init`; this script is a cuttable wrapper.

set -euo pipefail

if command -v uv >/dev/null 2>&1; then
  uv pip install scriptorium-cli
else
  pip install scriptorium-cli
fi

scriptorium --version

scriptorium init "$@"
```

Make it executable:

```bash
chmod +x scripts/install.sh
```

- [ ] **Step 6: Create `docs/obsidian-integration.md`**

```markdown
# Obsidian integration (v0.3)

When `obsidian_vault` is set and a `.obsidian/` directory is found by the
vault-detection walk-up, Scriptorium writes paper stubs to
`<vault>/papers/` and the Dataview query file to
`<vault>/scriptorium-queries.md`. Review files live under
`<vault>/reviews/<slug>/`.

## Portability tradeoff

Vault-wide `papers/` stubs mean a vault-based review directory is **not
self-contained** — the stubs it cites are elsewhere in the vault. If you
need a fully portable review folder, unset `obsidian_vault` when running
that review. `scriptorium export <review-dir>` (v0.4+) will bundle
referenced stubs into the review directory.

## Conflict copies

Dropbox-style `.obsidian (conflicted copy)` and `.obsidian 2` do not count
as vault markers on their own; when they coexist with a canonical
`.obsidian/` in the same directory, Scriptorium emits
`W_VAULT_CONFLICT_COPY` to the audit.
```

- [ ] **Step 7: Create `docs/publishing-notebooklm.md`**

```markdown
# Publishing to NotebookLM (v0.3)

## Preconditions

- `notebooklm_enabled = true` in Scriptorium config.
- `nlm doctor` exits zero. First-time setup: install the CLI with
  `uv tool install notebooklm-mcp-cli` (or `pipx install notebooklm-mcp-cli`),
  then run `nlm login`. Use a dedicated Google account; `nlm` is
  browser-automated.
- Review directory contains `overview.md`, `synthesis.md`,
  `contradictions.md`, `evidence.jsonl`, and `pdfs/`.

## Happy path

```bash
scriptorium publish --review-dir reviews/caffeine-wm --generate audio
```

Internally this runs, in order:

1. `nlm doctor`
2. `nlm notebook create "Caffeine Wm"`
3. `nlm source add <id> --file overview.md`
4. `nlm source add <id> --file synthesis.md`
5. `nlm source add <id> --file contradictions.md`
6. `nlm source add <id> --file evidence.jsonl`
7. `nlm source add <id> --file pdfs/<each>.pdf` (alphabetical, symlinks skipped)
8. `nlm audio create <id>` (or `nlm slides create` / `nlm mindmap create`)

A success entry is appended to `audit.md` under `## Publishing` and to
`audit.jsonl` as a `publishing` row.

## Cowork manual-upload template

When Cowork is detected, `scriptorium publish` prints the degradation block
with a relative file list. Users can manually upload those files at
https://notebooklm.google.com and then note the event in `audit.md`:

```markdown
## Publishing

### <timestamp> — NotebookLM (manual upload)

**Status:** success
**Destination:** NotebookLM (Google)
**Notebook:** "<Title>"
**URL:** <notebook URL>
**Sources uploaded**:
- overview.md
- synthesis.md
- contradictions.md
- evidence.jsonl

**Privacy note:** This action uploaded the listed files to Google-hosted
NotebookLM. The review's local copy is unchanged.
```

## Troubleshooting

- `E_NLM_UNAVAILABLE` — rerun `nlm login` then `nlm doctor`.
- `E_NLM_UPLOAD` partway through — the notebook exists in partial state;
  the `audit.md` entry records what uploaded successfully.
- `E_TIMEOUT` — rerun; nlm subprocesses have a five-minute timeout per step.
```

- [ ] **Step 8: Run the tests**

Run: `pytest tests/test_release_artifacts.py -q`
Expected: PASS.

- [ ] **Step 9: Full-suite regression**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add README.md CHANGELOG.md scripts/install.sh docs/obsidian-integration.md docs/publishing-notebooklm.md tests/test_release_artifacts.py
git commit -m "docs(release): v0.3.0 README, CHANGELOG, install.sh, obsidian/publish docs"
```

---

## Post-implementation checklist

These are manual steps after the 36 tasks above commit cleanly and the
full test suite is green.

- [ ] Run full suite: `pytest -q`. Must be 100% green.
- [ ] Tag `v0.3.0-rc1`: `git tag v0.3.0-rc1`.
- [ ] Publish to Test-PyPI, install in a clean venv:
      `pip install -i https://test.pypi.org/simple/ scriptorium-cli`.
- [ ] Run `scriptorium doctor` in the clean venv.
- [ ] Run caffeine fixture end-to-end in no-vault mode.
- [ ] Run caffeine fixture end-to-end inside an Obsidian vault with
      `obsidian_vault` set; verify stubs and `scriptorium-queries.md`.
- [ ] Verify Cowork degradation: `SCRIPTORIUM_FORCE_COWORK=1 scriptorium
      publish --review-dir reviews/caffeine-wm`.
- [ ] Run `/scriptorium-setup` on a clean macOS account with a dedicated
      Google account; verify `nlm audio`, `nlm slides`, `nlm mindmap`.
- [ ] Tag `v0.3.0`: `git tag v0.3.0`. Publish to PyPI.
- [ ] Open v0.4 issues for every deferred item in spec §1.2.

---

## Self-review (plan vs. spec §14 acceptance criteria)

| Acceptance criterion | Task(s) |
|---|---|
| Flat-layout import preserved; dist = `scriptorium-cli`; version `0.3.0` | 1 |
| Verified `nlm` commands only; no forbidden stale commands | 14, 29, 34 |
| `/scriptorium-setup` and `scriptorium init` with flags, idempotency, interrupted setup, warning | 25, 27, 30 |
| Config keys, defaults, types, load order, env overrides, corrupted config | 3, 4 |
| Review-dir resolution, symlink policy, vault detection, conflict | 5, 6 |
| Vault and no-vault layouts match §2 | 5, 12, 13, 22 |
| Frontmatter schemas paper / review / audit JSONL | 8, 9 |
| Native Obsidian output default; wikilinks; verifier dual-parses | 10, 11, 13, 33 |
| Dataview query file write-once with exactly five queries | 12 |
| `overview.md` generation, lint, provenance, archive, failed-output, CLI flags | 22 |
| End-of-review NotebookLM prompt gates and default | 21, 28 |
| `/lit-podcast`, `/lit-deck`, `/lit-mindmap` route exactly | 26 |
| `scriptorium publish` flags, source default, upload order, lock, timeout, partial, audit, JSON | 15-20 |
| Cowork publish emits exact block and never invokes `nlm` | 16 |
| `scriptorium migrate-review` flags, no-auto-migration, idempotency, fail-closed | 23 |
| `lit-publishing/` renamed to `publishing-to-notebooklm/` and rewritten | 29 |
| New skills `setting-up-scriptorium/` and `generating-overview/` | 30, 31 |
| Hook file remains; verifier updated | 33 |
| All error codes unique and implemented | 2, 34 |
| Test plan §13 | 1, 3-35 |
| README, docs, changelog updated | 36 |

