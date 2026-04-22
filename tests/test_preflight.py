from pathlib import Path


def test_lit_config_has_preflight():
    body = (Path(__file__).parents[1] / "commands" / "lit-config.md").read_text()
    assert "scriptorium version" in body
    assert "pipx install scriptorium-cli" in body
    assert "degraded mode" in body


def test_lit_review_has_preflight():
    body = (Path(__file__).parents[1] / "commands" / "lit-review.md").read_text()
    assert "scriptorium version" in body
    assert "pipx install scriptorium-cli" in body
    assert "degraded mode" in body


def test_using_scriptorium_skill_has_hard_stop():
    body = (Path(__file__).parents[1] / "skills" / "using-scriptorium" / "SKILL.md").read_text()
    assert "scriptorium version" in body
    assert "pipx install scriptorium-cli" in body
