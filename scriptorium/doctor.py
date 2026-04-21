"""`scriptorium doctor` diagnostics."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from scriptorium import __version__
from scriptorium import nlm as nlm


def run_doctor(stdout) -> int:
    stdout.write(f"scriptorium {__version__}\n")
    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    stdout.write(f"python: {py}\n")
    home = Path(os.environ.get("HOME", "")).expanduser()
    writable = home.is_dir() and os.access(home, os.W_OK)
    stdout.write(f"writable HOME: {writable}\n")
    try:
        nlm.doctor()
        stdout.write("nlm: ok\n")
    except Exception as e:
        stdout.write(f"nlm: unavailable ({e})\n")
    return 0
