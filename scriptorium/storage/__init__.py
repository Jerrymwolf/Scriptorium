"""Storage primitives: append-only JSONL ledgers + corpus.

v0.4 also re-exports the top-level :mod:`scriptorium.phase_state` module
so consumers have a single import surface for per-review state artifacts.
"""

from scriptorium import phase_state as phase_state

__all__ = ["phase_state"]
