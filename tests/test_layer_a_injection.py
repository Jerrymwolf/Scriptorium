"""T06 — INJECTION.md content + size constraints, SessionStart hook semantics.

Pins the canonical Layer-A injection file and the Claude Code SessionStart
hook that delivers it. The same file is the MCP `instructions` payload in
Cowork (see `scriptorium.mcp.server._INJECTION_PATH`); these tests guard
the cross-runtime contract that both runtimes inject identical text.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INJECTION = REPO_ROOT / "skills" / "using-scriptorium" / "INJECTION.md"
HOOK = REPO_ROOT / "hooks" / "session-start.sh"
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"

# Cap reflects: 3 disciplines (named imperatively) + red-flag list + runtime
# probe pointer. Conservative enough to keep session-start budget small;
# generous enough to absorb the agreed prose with a small safety margin.
INJECTION_BYTE_CAP = 4096
INJECTION_LINE_CAP = 80


# ---------------------------------------------------------------------------
# A. INJECTION.md content + size constraints
# ---------------------------------------------------------------------------


def test_injection_file_exists():
    assert INJECTION.exists(), f"INJECTION.md missing at {INJECTION}"


def test_injection_byte_size_within_cap():
    size = INJECTION.stat().st_size
    assert size <= INJECTION_BYTE_CAP, (
        f"INJECTION.md is {size} bytes; cap is {INJECTION_BYTE_CAP}. "
        "Trim before raising the cap."
    )


def test_injection_line_count_within_cap():
    n = len(INJECTION.read_text(encoding="utf-8").splitlines())
    assert n <= INJECTION_LINE_CAP, (
        f"INJECTION.md is {n} lines; cap is {INJECTION_LINE_CAP}."
    )


def test_injection_is_utf8_decodable():
    # read_bytes + decode forces a strict UTF-8 round-trip.
    INJECTION.read_bytes().decode("utf-8")


def test_injection_has_no_yaml_frontmatter():
    first_line = INJECTION.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.strip() != "---", (
        "INJECTION.md must not start with YAML frontmatter; it is literal "
        "injection text, not a SKILL.md."
    )


@pytest.mark.parametrize(
    "phrase",
    [
        "Evidence-first",
        "PRISMA audit",
        "Contradiction surfacing",
        "using-scriptorium",
    ],
)
def test_injection_contains_required_phrase(phrase):
    text = INJECTION.read_text(encoding="utf-8")
    assert phrase in text, f"INJECTION.md missing required phrase: {phrase!r}"


# ---------------------------------------------------------------------------
# B. Hook canonical path
# ---------------------------------------------------------------------------


def _run_hook(env: dict[str, str] | None) -> subprocess.CompletedProcess:
    """Run the session-start hook with a controlled environment.

    Pass ``env=None`` to use a clean env (no inherited PATH); pass a dict to
    override. This makes tests precise about what the hook sees.
    """
    if env is None:
        env_to_use = {"PATH": os.environ.get("PATH", "")}
    else:
        env_to_use = {"PATH": os.environ.get("PATH", ""), **env}
    return subprocess.run(
        ["bash", str(HOOK)],
        capture_output=True,
        text=True,
        env=env_to_use,
    )


def test_hook_reads_only_from_canonical_path(tmp_path):
    """Hook must read from $CLAUDE_PLUGIN_ROOT/skills/using-scriptorium/INJECTION.md.

    Point CLAUDE_PLUGIN_ROOT at an empty temp dir and assert the hook does
    NOT find the real INJECTION.md by accident (no fallback search paths).
    """
    res = _run_hook({"CLAUDE_PLUGIN_ROOT": str(tmp_path)})
    assert res.returncode == 0
    # stdout must be empty — the only file the hook can read does not exist
    # under the temp root, so no injection content may leak through.
    assert res.stdout == "", (
        "hook leaked stdout when canonical path was empty: "
        f"{res.stdout!r}"
    )
    # And the real INJECTION.md content must not appear in stdout.
    real_text = INJECTION.read_text(encoding="utf-8")
    assert real_text not in res.stdout


def test_hook_streams_injection_when_canonical_path_set():
    res = _run_hook({"CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)})
    assert res.returncode == 0, res.stderr
    assert res.stdout == INJECTION.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# C. Missing-injection warning
# ---------------------------------------------------------------------------


def test_hook_warns_on_missing_injection(tmp_path):
    res = _run_hook({"CLAUDE_PLUGIN_ROOT": str(tmp_path)})
    assert res.returncode == 0
    assert res.stdout == ""
    assert "INJECTION.md" in res.stderr
    assert "missing" in res.stderr.lower()


# ---------------------------------------------------------------------------
# D. Empty-injection warning
# ---------------------------------------------------------------------------


def test_hook_warns_on_empty_injection(tmp_path):
    inj = tmp_path / "skills" / "using-scriptorium" / "INJECTION.md"
    inj.parent.mkdir(parents=True)
    inj.write_text("", encoding="utf-8")

    res = _run_hook({"CLAUDE_PLUGIN_ROOT": str(tmp_path)})
    assert res.returncode == 0
    assert res.stdout == ""
    assert "empty" in res.stderr.lower()


# ---------------------------------------------------------------------------
# E. CLAUDE_PLUGIN_ROOT-unset path
# ---------------------------------------------------------------------------


def test_hook_warns_when_plugin_root_unset():
    res = _run_hook(env=None)
    assert res.returncode == 0
    assert res.stdout == ""
    assert "CLAUDE_PLUGIN_ROOT" in res.stderr


# ---------------------------------------------------------------------------
# F. Hook is executable + has shebang
# ---------------------------------------------------------------------------


def test_hook_exists_executable_and_has_shebang():
    assert HOOK.exists(), f"hook missing at {HOOK}"
    mode = HOOK.stat().st_mode
    assert mode & 0o111, (
        f"hook {HOOK} is not executable; mode={oct(mode)}"
    )
    first_line = HOOK.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("#!"), "hook missing shebang"


# ---------------------------------------------------------------------------
# G. hooks/hooks.json registers SessionStart and preserves PostToolUse
# ---------------------------------------------------------------------------


def test_hooks_json_registers_session_start_pointing_at_session_start_sh():
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    assert "hooks" in data
    assert "SessionStart" in data["hooks"]
    entries = data["hooks"]["SessionStart"]
    assert isinstance(entries, list) and entries
    # Find at least one hook command pointing at session-start.sh.
    commands = [
        h.get("command", "")
        for entry in entries
        for h in entry.get("hooks", [])
    ]
    assert any("session-start.sh" in c for c in commands), (
        f"no SessionStart hook references session-start.sh: {commands}"
    )


def test_hooks_json_preserves_post_tool_use_entry_unchanged():
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    assert "PostToolUse" in data["hooks"]
    ptu = data["hooks"]["PostToolUse"]
    # Existing PostToolUse entry must be byte-for-byte intent-preserved.
    assert ptu == [
        {
            "matcher": "Write|Edit",
            "hooks": [
                {
                    "type": "command",
                    "command": 'bash "${CLAUDE_PLUGIN_ROOT}/hooks/evidence_gate.sh"',
                    "async": False,
                }
            ],
        }
    ]


# ---------------------------------------------------------------------------
# H. MCP server still resolves the same canonical path
# ---------------------------------------------------------------------------


def test_mcp_server_resolves_same_canonical_injection():
    """Cross-runtime contract: CC hook and Cowork MCP server read the SAME file."""
    from scriptorium.mcp import server as mcp_server

    assert mcp_server._INJECTION_PATH == INJECTION
    assert mcp_server._INJECTION_PATH.exists()
    instructions = mcp_server._load_instructions()
    assert instructions != ""
    assert instructions == INJECTION.read_text(encoding="utf-8")
