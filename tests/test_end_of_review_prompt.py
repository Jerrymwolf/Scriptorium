"""§9.1: end-of-review prompt gates and command routing."""
import io

import pytest

from scriptorium.config import Config
from scriptorium.prompts import (
    EndOfReviewChoice,
    build_end_of_review_command,
    should_prompt_end_of_review,
)


def test_gate_passes_when_all_conditions_met():
    cfg = Config(notebooklm_prompt=True, notebooklm_enabled=True)
    assert should_prompt_end_of_review(
        cfg=cfg, nlm_available=True, cite_check_passed=True
    ) is True


def test_gate_blocks_when_prompt_disabled():
    cfg = Config(notebooklm_prompt=False, notebooklm_enabled=True)
    assert should_prompt_end_of_review(
        cfg=cfg, nlm_available=True, cite_check_passed=True
    ) is False


def test_gate_blocks_when_nlm_unavailable():
    cfg = Config(notebooklm_prompt=True, notebooklm_enabled=True)
    assert should_prompt_end_of_review(
        cfg=cfg, nlm_available=False, cite_check_passed=True
    ) is False


def test_gate_blocks_when_cite_check_failed():
    cfg = Config(notebooklm_prompt=True, notebooklm_enabled=True)
    assert should_prompt_end_of_review(
        cfg=cfg, nlm_available=True, cite_check_passed=False
    ) is False


@pytest.mark.parametrize("choice,flag", [
    (EndOfReviewChoice.AUDIO, "audio"),
    (EndOfReviewChoice.DECK, "deck"),
    (EndOfReviewChoice.MINDMAP, "mindmap"),
])
def test_command_mapping(choice, flag):
    cmd = build_end_of_review_command(choice, review_dir="reviews/caffeine-wm")
    assert cmd == [
        "scriptorium", "publish", "--review-dir", "reviews/caffeine-wm",
        "--generate", flag,
    ]


def test_skip_returns_none():
    assert build_end_of_review_command(
        EndOfReviewChoice.SKIP, review_dir="x"
    ) is None
