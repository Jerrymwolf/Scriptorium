"""§9.2: three slash commands map to scriptorium publish --generate <kind>."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / ".claude-plugin" / "commands"


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_lit_podcast_maps_to_audio():
    text = _read("lit-podcast.md")
    assert "scriptorium publish" in text
    assert "--generate audio" in text
    assert "nlm audio create" in text


def test_lit_deck_maps_to_deck():
    text = _read("lit-deck.md")
    assert "--generate deck" in text
    assert "nlm slides create" in text


def test_lit_mindmap_maps_to_mindmap():
    text = _read("lit-mindmap.md")
    assert "--generate mindmap" in text
    assert "nlm mindmap create" in text
