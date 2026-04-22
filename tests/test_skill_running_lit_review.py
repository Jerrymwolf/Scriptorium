from pathlib import Path

SKILL = Path("skills/running-lit-review/SKILL.md")


def test_skill_exists():
    assert SKILL.exists()


def test_frontmatter_activation_phrase():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "name: running-lit-review" in text
    assert "lit review" in text.lower()
    assert "run" in text.lower()


def test_defers_runtime_choice_to_using_scriptorium():
    text = SKILL.read_text(encoding="utf-8")
    assert "using-scriptorium" in text


def test_names_every_phase_skill_in_order():
    text = SKILL.read_text(encoding="utf-8")
    required_order = [
        "lit-searching",
        "lit-screening",
        "lit-extracting",
        "lit-synthesizing",
        "lit-contradiction-check",
        "lit-audit-trail",
        "lit-publishing",
    ]
    idx = 0
    for skill in required_order:
        found = text.find(skill, idx)
        assert found != -1, f"missing skill mention: {skill}"
        idx = found + 1


def test_evidence_first_checkpoint_called_out():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "cite-check" in text or "verify" in text
    assert "evidence-first" in text


def test_contradiction_check_is_separate_pass():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "contradiction" in text
    assert "separate" in text or "after" in text


def test_audit_every_phase():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "audit" in text
    assert "every" in text or "each" in text


def test_publishing_is_optional_and_last():
    text = SKILL.read_text(encoding="utf-8")
    pub_idx = text.find("lit-publishing")
    contra_idx = text.find("lit-contradiction-check")
    assert pub_idx > contra_idx, "publishing must follow contradiction-check"
    assert "optional" in text.lower() or "if the user" in text.lower()
