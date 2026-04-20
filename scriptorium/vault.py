"""Obsidian vault detection and path-escape guard (§4.2, §4.3)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class PathEscapeError(Exception):
    """Raised when a resolved path is outside the allowed root."""


@dataclass(frozen=True)
class VaultConflictCopy:
    """Marker class retained for test-discovery back-compat; see warning field."""
    path: Path


@dataclass(frozen=True)
class VaultDetection:
    vault_root: Optional[Path]
    warning: Optional[str]  # "W_VAULT_CONFLICT_COPY" or None


def detect_vault(review_dir: Path) -> VaultDetection:
    """Walk from `review_dir` up to the filesystem root looking for `.obsidian/`.

    The ancestor must contain an entry named exactly `.obsidian` that resolves
    to an existing directory. Conflict copies (`.obsidian (conflicted copy)`,
    `.obsidian 2`, etc.) do not count on their own but trigger a warning when
    they coexist with the canonical name.
    """
    resolved = Path(review_dir).resolve(strict=False)
    ancestor: Optional[Path] = resolved
    while ancestor is not None:
        canonical = ancestor / ".obsidian"
        if canonical.is_dir():
            warn = None
            for entry in ancestor.iterdir():
                if entry.name == ".obsidian":
                    continue
                if entry.name.startswith(".obsidian") and entry.is_dir():
                    warn = "W_VAULT_CONFLICT_COPY"
                    break
            return VaultDetection(vault_root=ancestor.resolve(), warning=warn)
        if ancestor.parent == ancestor:
            break
        ancestor = ancestor.parent
    return VaultDetection(vault_root=None, warning=None)


def ensure_within(path: Path, root: Path) -> None:
    """Raise PathEscapeError if `path` does not resolve inside `root`."""
    try:
        Path(path).resolve(strict=False).relative_to(Path(root).resolve(strict=False))
    except ValueError as e:
        raise PathEscapeError(
            f"resolved path {path!s} escapes allowed root {root!s}"
        ) from e
