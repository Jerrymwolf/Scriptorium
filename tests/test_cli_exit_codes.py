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
