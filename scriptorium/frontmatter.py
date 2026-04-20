"""YAML frontmatter read/write plus v0.3 schema guards.

No third-party YAML dependency — the frontmatter emitted by v0.3 is a
minimal, fully-escaped subset:
  - scalar lines `<key>: <scalar>`
  - list lines `<key>: [<scalar>, ...]`
  - nested mappings `<key>:` then `  <child>: <scalar>`

Read is best-effort: we only round-trip data we ourselves wrote, so we
use a small hand-rolled parser that recognizes the formats produced by
`write_frontmatter`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable, Mapping


class FrontmatterError(Exception):
    """Raised when a schema-guarded dict is missing/forbidden a field."""


# --- schema guards ---------------------------------------------------------

_PAPER_REQUIRED = {
    "schema_version",
    "scriptorium_version",
    "paper_id",
    "title",
    "authors",
    "year",
    "tags",
    "reviewed_in",
    "full_text_source",
    "created_at",
    "updated_at",
}
_PAPER_OPTIONAL = {"doi", "pmid", "pmcid", "pdf_path", "source_url"}
_PAPER_ALLOWED = _PAPER_REQUIRED | _PAPER_OPTIONAL
_PAPER_FULL_TEXT_SOURCES = {
    "user_pdf", "unpaywall", "arxiv", "pmc", "abstract_only"
}


@dataclass
class PaperStubFrontmatter:
    schema_version: str
    scriptorium_version: str
    paper_id: str
    title: str
    authors: list[str]
    year: int | None
    tags: list[str]
    reviewed_in: list[str]
    full_text_source: str
    created_at: str
    updated_at: str
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    pdf_path: str | None = None
    source_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != ""}

    @classmethod
    def validate_dict(cls, d: Mapping[str, Any]) -> None:
        missing = _PAPER_REQUIRED - d.keys()
        if missing:
            raise FrontmatterError(
                f"paper frontmatter missing required fields: {sorted(missing)}"
            )
        extras = set(d.keys()) - _PAPER_ALLOWED
        if extras:
            raise FrontmatterError(
                f"paper frontmatter has forbidden fields: {sorted(extras)}"
            )
        if d["full_text_source"] not in _PAPER_FULL_TEXT_SOURCES:
            raise FrontmatterError(
                f"full_text_source must be one of "
                f"{sorted(_PAPER_FULL_TEXT_SOURCES)}"
            )


_REVIEW_REQUIRED = {
    "schema_version",
    "scriptorium_version",
    "review_id",
    "review_type",
    "created_at",
    "updated_at",
    "research_question",
    "cite_discipline",
}
_REVIEW_OPTIONAL = {
    "vault_root", "model_version", "generation_seed",
    "generation_timestamp", "corpus_hash", "ranking_weights",
}
_REVIEW_ALLOWED = _REVIEW_REQUIRED | _REVIEW_OPTIONAL
_REVIEW_TYPES = {"synthesis", "contradictions", "overview", "audit"}
_CITE_DISCIPLINES = {"locator", "abstract_only"}


@dataclass
class ReviewArtifactFrontmatter:
    schema_version: str
    scriptorium_version: str
    review_id: str
    review_type: str
    created_at: str
    updated_at: str
    research_question: str
    cite_discipline: str
    vault_root: str | None = None
    model_version: str | None = None
    generation_seed: int | None = None
    generation_timestamp: str | None = None
    corpus_hash: str | None = None
    ranking_weights: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def validate_dict(cls, d: Mapping[str, Any]) -> None:
        missing = _REVIEW_REQUIRED - d.keys()
        if missing:
            raise FrontmatterError(
                f"review frontmatter missing required fields: {sorted(missing)}"
            )
        extras = set(d.keys()) - _REVIEW_ALLOWED
        if extras:
            raise FrontmatterError(
                f"review frontmatter has forbidden fields: {sorted(extras)}"
            )
        if d["review_type"] not in _REVIEW_TYPES:
            raise FrontmatterError(
                f"review_type must be one of {sorted(_REVIEW_TYPES)}"
            )
        if d["cite_discipline"] not in _CITE_DISCIPLINES:
            raise FrontmatterError(
                f"cite_discipline must be one of {sorted(_CITE_DISCIPLINES)}"
            )


# --- reader/writer --------------------------------------------------------

def _yaml_scalar(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    return json.dumps(s, ensure_ascii=False)


def _yaml_list(values: Iterable[Any]) -> str:
    return "[" + ", ".join(_yaml_scalar(v) for v in values) + "]"


def write_frontmatter(data: Mapping[str, Any], *, body: str) -> str:
    lines = ["---"]
    for k, v in data.items():
        if isinstance(v, list):
            lines.append(f"{k}: {_yaml_list(v)}")
        elif isinstance(v, dict):
            lines.append(f"{k}:")
            for ck, cv in v.items():
                lines.append(f"  {ck}: {_yaml_scalar(cv)}")
        else:
            lines.append(f"{k}: {_yaml_scalar(v)}")
    lines.append("---")
    return "\n".join(lines) + "\n" + body


def read_frontmatter(text: str) -> dict[str, Any]:
    """Parse frontmatter previously written by `write_frontmatter`.

    Only supports the shapes we emit. Raises FrontmatterError on malformed input.
    """
    if not text.startswith("---\n"):
        raise FrontmatterError("missing leading --- delimiter")
    rest = text[4:]
    end = rest.find("\n---")
    if end < 0:
        raise FrontmatterError("missing trailing --- delimiter")
    block = rest[:end]
    out: dict[str, Any] = {}
    current_map_key: str | None = None
    for line in block.splitlines():
        if not line.strip():
            current_map_key = None
            continue
        if line.startswith("  ") and current_map_key is not None:
            k, _, v = line.strip().partition(":")
            out[current_map_key][k.strip()] = _parse_scalar(v.strip())
            continue
        current_map_key = None
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip()
        if v == "":
            out[k] = {}
            current_map_key = k
        elif v.startswith("[") and v.endswith("]"):
            inner = v[1:-1].strip()
            if not inner:
                out[k] = []
            else:
                out[k] = [_parse_scalar(item.strip()) for item in _split_list(inner)]
        else:
            out[k] = _parse_scalar(v)
    return out


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    rest = text[4:]
    end = rest.find("\n---")
    if end < 0:
        return text
    return rest[end + 4:].lstrip("\n")


def _parse_scalar(v: str) -> Any:
    if v == "null":
        return None
    if v == "true":
        return True
    if v == "false":
        return False
    if v.startswith('"') and v.endswith('"'):
        return json.loads(v)
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def _split_list(s: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    depth_quote = False
    for ch in s:
        if ch == '"' and (not buf or buf[-1] != "\\"):
            depth_quote = not depth_quote
            buf.append(ch)
            continue
        if ch == "," and not depth_quote:
            out.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf:
        out.append("".join(buf).strip())
    return out
