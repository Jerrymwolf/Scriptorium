"""§7.3: setup state file semantics."""
import json
from pathlib import Path

from scriptorium.setup_flow import (
    STATE_VERSION, SetupStateCorrupt, load_state, mark_step_completed,
    move_corrupt_state_aside,
)


def test_mark_and_load(tmp_path):
    state_path = tmp_path / "s.json"
    mark_step_completed(state_path, "precheck")
    mark_step_completed(state_path, "package")
    state = load_state(state_path)
    assert state["completed_steps"] == ["precheck", "package"]
    assert state["version"] == STATE_VERSION


def test_corrupt_state_moves_aside(tmp_path):
    state_path = tmp_path / "s.json"
    state_path.write_text("{not json", encoding="utf-8")
    moved = move_corrupt_state_aside(state_path)
    assert moved.exists()
    assert not state_path.exists()


def test_load_raises_on_corrupt(tmp_path):
    state_path = tmp_path / "s.json"
    state_path.write_text("{not json", encoding="utf-8")
    import pytest
    with pytest.raises(SetupStateCorrupt):
        load_state(state_path)
