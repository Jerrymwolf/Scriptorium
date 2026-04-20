from pathlib import Path

CMD = Path(".claude-plugin/commands/lit-review.md")


def test_command_exists():
    assert CMD.exists()


def test_frontmatter_describes_command():
    text = CMD.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "description:" in text
    assert "argument-hint:" in text


def test_command_delegates_to_skill():
    text = CMD.read_text(encoding="utf-8")
    assert "running-lit-review" in text
    lines_after_frontmatter = text.split("---", 2)[-1].splitlines()
    non_blank = [ln for ln in lines_after_frontmatter if ln.strip()]
    assert len(non_blank) <= 30, "lit-review.md body is too long"


def test_command_passes_query_through():
    text = CMD.read_text(encoding="utf-8")
    assert "{{ARGS}}" in text or "$ARGUMENTS" in text


def test_command_mentions_review_dir_flag():
    text = CMD.read_text(encoding="utf-8")
    assert "--review-dir" in text
