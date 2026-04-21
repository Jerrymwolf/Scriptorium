"""End-of-review NotebookLM prompt helpers (§9.1)."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from scriptorium.config import Config


class EndOfReviewChoice(str, Enum):
    AUDIO = "audio"
    DECK = "deck"
    MINDMAP = "mindmap"
    SKIP = "skip"


PROMPT_TEXT = """NotebookLM artifact? (skip default)
  audio
  deck
  mindmap
  skip
"""


def should_prompt_end_of_review(
    *, cfg: Config, nlm_available: bool, cite_check_passed: bool
) -> bool:
    if cfg.notebooklm_prompt is False:
        return False
    if not cfg.notebooklm_enabled:
        return False
    if not nlm_available:
        return False
    if not cite_check_passed:
        return False
    return True


def build_end_of_review_command(
    choice: EndOfReviewChoice, *, review_dir: str
) -> Optional[list[str]]:
    if choice == EndOfReviewChoice.SKIP:
        return None
    return [
        "scriptorium", "publish", "--review-dir", review_dir,
        "--generate", choice.value,
    ]
