from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / "skills"


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
    for bad in ("nlm auth login", "nlm studio create", "--confirm"):
        assert bad not in text, f"forbidden stale token present: {bad}"


def test_new_skill_documents_cowork_block():
    text = (SKILLS / "publishing-to-notebooklm" / "SKILL.md").read_text(encoding="utf-8")
    assert "Cowork" in text
    assert "local shell access" in text
