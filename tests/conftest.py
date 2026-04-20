"""Shared fixtures for the scriptorium test suite."""
from __future__ import annotations
import json
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def review_dir(tmp_path: Path) -> Path:
    """Fresh per-review directory, isolated to tmp_path."""
    d = tmp_path / "review"
    (d / "pdfs").mkdir(parents=True)
    (d / "extracts").mkdir()
    (d / "outputs").mkdir()
    (d / "bib").mkdir()
    return d


def load_fixture(category: str, name: str) -> dict:
    return json.loads((FIXTURES / category / f"{name}.json").read_text())


@pytest.fixture
def fixture_loader():
    return load_fixture
