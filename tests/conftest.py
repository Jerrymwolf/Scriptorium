"""Shared fixtures for the scriptorium test suite."""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _build_scriptorium_shim() -> str | None:
    """Return a path to a working ``scriptorium`` CLI for subprocess use.

    Hook tests shell out to ``bash hooks/evidence_gate.sh``, which resolves
    the CLI via ``SCRIPTORIUM_BIN`` (preferred) or ``command -v scriptorium``
    (fallback). Either can break in practice:

    * Console-script shebangs on macOS 14+ can be silently skipped when
      setuptools' editable ``.pth`` file is marked ``hidden`` by Finder.
    * A stale system-wide install may win ``command -v`` but fail to import
      the current checkout.

    The portable workaround is a one-line shim that invokes
    ``<pytest python> -m scriptorium.cli "$@"`` with ``PYTHONPATH`` pinned
    to the repo root. Pinning ``PYTHONPATH`` means the shim works regardless
    of the hook's ``cwd``, even when the setuptools-editable ``.pth`` file
    is silently skipped.
    """
    repo_root = Path(__file__).resolve().parent.parent
    shim_dir = Path(__file__).resolve().parent / ".hook-shims"
    shim_dir.mkdir(exist_ok=True)
    shim = shim_dir / "scriptorium"
    shim.write_text(
        "#!/usr/bin/env bash\n"
        # Prepend the repo root to PYTHONPATH so `import scriptorium` works
        # regardless of the process's cwd. Hook subprocesses generally run
        # from the review dir (writer's cwd), not the repo root.
        f'export PYTHONPATH="{repo_root}${{PYTHONPATH:+:$PYTHONPATH}}"\n'
        f'exec "{sys.executable}" -m scriptorium.cli "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)
    # Sanity-check the shim from a cwd that is not the repo root.
    try:
        result = subprocess.run(
            [str(shim), "version"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(shim_dir),
        )
    except Exception:
        return shutil.which("scriptorium")
    if result.returncode == 0:
        return str(shim)
    return shutil.which("scriptorium")


SCRIPTORIUM_BIN: str | None = _build_scriptorium_shim()


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the shared test fixtures directory."""
    return FIXTURES


@pytest.fixture
def review_dir(tmp_path: Path) -> Path:
    """Fresh per-review directory, isolated to tmp_path (new hybrid layout)."""
    d = tmp_path / "review"
    (d / "sources" / "pdfs").mkdir(parents=True)
    (d / "sources" / "papers").mkdir(parents=True)
    (d / "data" / "extracts").mkdir(parents=True)
    (d / "audit" / "overview-archive").mkdir(parents=True)
    (d / ".scriptorium").mkdir(parents=True)
    return d


def load_fixture(category: str, name: str) -> dict:
    """Load a JSON fixture by category and name."""
    return json.loads((FIXTURES / category / f"{name}.json").read_text())


@pytest.fixture
def fixture_loader():
    """Fixture providing the load_fixture function."""
    return load_fixture
