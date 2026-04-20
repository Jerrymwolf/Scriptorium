"""Cowork-runtime detection.

Cowork is a sandboxed runtime without local shell access. v0.3 treats the
following env-var truthy values as explicit Cowork mode:
  SCRIPTORIUM_COWORK, SCRIPTORIUM_FORCE_COWORK
"""
from __future__ import annotations

import os


_TRUTHY = {"1", "true", "yes"}


def is_cowork_mode() -> bool:
    for name in ("SCRIPTORIUM_COWORK", "SCRIPTORIUM_FORCE_COWORK"):
        val = os.environ.get(name)
        if val is None:
            continue
        if val.strip().lower() in _TRUTHY:
            return True
    return False
