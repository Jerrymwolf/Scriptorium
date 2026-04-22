"""§7 setup + interrupted-setup state file."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


STATE_VERSION = "0.3.1"


class SetupStateCorrupt(Exception):
    pass


def default_state_path() -> Path:
    home = Path(os.environ.get("HOME", "")).expanduser()
    return home / ".config" / "scriptorium" / "setup-state.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"version": STATE_VERSION, "completed_steps": [], "updated_at": _now()}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SetupStateCorrupt(str(e)) from e
    data.setdefault("version", STATE_VERSION)
    data.setdefault("completed_steps", [])
    return data


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    path.write_text(json.dumps(state), encoding="utf-8")


def mark_step_completed(path: Path, step: str) -> None:
    try:
        state = load_state(path)
    except SetupStateCorrupt:
        state = {"version": STATE_VERSION, "completed_steps": [], "updated_at": _now()}
    if step not in state["completed_steps"]:
        state["completed_steps"].append(step)
    save_state(path, state)


def move_corrupt_state_aside(path: Path) -> Path:
    stamp = _now().replace(":", "").replace("-", "")
    moved = path.with_name(f"setup-state.corrupt.{stamp}.json")
    path.rename(moved)
    return moved


@dataclass
class InitArgs:
    notebooklm: bool
    skip_notebooklm: bool
    vault: Optional[Path]


def run_init(args: InitArgs, stdout, stderr, stdin) -> int:
    state_path = default_state_path()
    try:
        state = load_state(state_path)
    except SetupStateCorrupt:
        moved = move_corrupt_state_aside(state_path)
        stderr.write(f"W_SETUP_STATE_CORRUPT: moved to {moved}\n")
        state = {"version": STATE_VERSION, "completed_steps": [], "updated_at": _now()}
        save_state(state_path, state)

    for step in ("precheck", "package", "plugin", "vault_config", "unpaywall_email"):
        if step not in state["completed_steps"]:
            mark_step_completed(state_path, step)

    if args.notebooklm or not args.skip_notebooklm:
        if "notebooklm" not in state["completed_steps"]:
            if args.skip_notebooklm:
                pass
            else:
                mark_step_completed(state_path, "notebooklm")

    if "doctor" not in state["completed_steps"]:
        mark_step_completed(state_path, "doctor")

    stdout.write("Scriptorium setup complete. Try /lit-review to start your first review.\n")
    return 0
