"""§13.2 stale-command scan: forbidden nlm shapes must be absent everywhere."""
from pathlib import Path


FORBIDDEN = [
    "nlm auth login",
    "nlm studio create",
    "nlm source upload",
    "--confirm",
]

ALLOWED_WITH_CONFIRM = {"docs/publishing-notebooklm.md"}


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
