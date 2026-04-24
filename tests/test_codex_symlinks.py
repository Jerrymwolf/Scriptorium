from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LINKER = ROOT / "scripts" / "codex_link.sh"
CODEX_SKILLS = ROOT / ".codex" / "skills"
CODEX_COMMANDS = ROOT / ".codex" / "commands"
# After f179da7, skills/commands/hooks live at repo root, not under .claude-plugin/.
PLUGIN_SKILLS = ROOT / "skills"
PLUGIN_COMMANDS = ROOT / "commands"


def test_linker_script_exists_and_is_executable():
    assert LINKER.exists(), f"missing: {LINKER}"
    assert os.access(LINKER, os.X_OK), f"not executable: {LINKER}"


def test_linker_runs_and_creates_codex_tree():
    result = subprocess.run(
        ["bash", str(LINKER)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr
    assert CODEX_SKILLS.exists()
    assert CODEX_COMMANDS.exists()


def test_codex_skills_mirror_plugin_skills():
    plugin_skill_dirs = sorted(
        d.name for d in PLUGIN_SKILLS.iterdir() if d.is_dir()
    )
    codex_skill_entries = sorted(
        e.name for e in CODEX_SKILLS.iterdir()
    )
    assert plugin_skill_dirs == codex_skill_entries


def test_every_codex_skill_is_symlink():
    for entry in CODEX_SKILLS.iterdir():
        assert entry.is_symlink(), f"not a symlink: {entry}"
        target = (entry.parent / os.readlink(entry)).resolve()
        assert target.parent == PLUGIN_SKILLS.resolve(), f"wrong target: {entry} → {target}"


def test_codex_commands_mirror_plugin_commands():
    plugin_commands = sorted(
        f.name for f in PLUGIN_COMMANDS.iterdir() if f.suffix == ".md"
    )
    codex_commands = sorted(e.name for e in CODEX_COMMANDS.iterdir())
    assert plugin_commands == codex_commands


def test_every_codex_command_is_symlink():
    for entry in CODEX_COMMANDS.iterdir():
        assert entry.is_symlink(), f"not a symlink: {entry}"
        target = (entry.parent / os.readlink(entry)).resolve()
        assert target.parent == PLUGIN_COMMANDS.resolve()


def test_rerun_is_idempotent():
    first = subprocess.run(["bash", str(LINKER)], capture_output=True, text=True, cwd=str(ROOT))
    second = subprocess.run(["bash", str(LINKER)], capture_output=True, text=True, cwd=str(ROOT))
    assert first.returncode == 0 and second.returncode == 0
    assert "File exists" not in second.stderr
