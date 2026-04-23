"""Shared fixtures for the scriptorium test suite."""
from __future__ import annotations
import json
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


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
