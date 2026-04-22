"""Paper-stub generator (§6.2).

A stub file has:
  1. YAML frontmatter (Scriptorium-owned).
  2. Header + metadata lines (Scriptorium-owned).
  3. `## Abstract` (Scriptorium-owned).
  4. `## Cited pages` with `### p-N` children (Scriptorium-owned).
  5. `## Claims in review: <review_id>` (Scriptorium-owned per review).
  6. Arbitrary user content after any Scriptorium-owned section.

Regeneration preserves user edits by replacing only the owned regions
in place and leaving all other lines untouched.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from scriptorium.frontmatter import (
    PaperStubFrontmatter,
    read_frontmatter,
    strip_frontmatter,
    write_frontmatter,
)


@dataclass
class PaperStubInput:
    paper_id: str
    title: str
    authors: list[str]
    year: Optional[int]
    tags: list[str]
    doi: Optional[str]
    full_text_source: str
    pdf_path: Optional[str]
    source_url: Optional[str]
    abstract: Optional[str]
    cited_pages: dict[str, str]  # {"page:4": "<quote>"}
    review_id: str
    synthesis_claim: Optional[tuple[str, str]]  # (claim_text, wikilink)
    now_iso: str


def _header(data: PaperStubInput) -> str:
    first_author = (data.authors[0].split(",")[0] if data.authors else "Unknown")
    year = data.year if data.year is not None else "n.d."
    return f"# {first_author} ({year}) — {data.title}"


def _metadata_block(data: PaperStubInput) -> list[str]:
    doi = data.doi or "unknown"
    if data.full_text_source == "abstract_only":
        full_text = "abstract only"
    elif data.source_url:
        full_text = f"{data.full_text_source} ({data.source_url})"
    elif data.pdf_path:
        full_text = f"{data.full_text_source} ({data.pdf_path})"
    else:
        full_text = data.full_text_source
    pdf_link = (
        f"[[{data.pdf_path}]]" if data.pdf_path else "none"
    )
    return [
        f"**DOI:** {doi}",
        f"**Full text:** {full_text}",
        f"**Local PDF:** {pdf_link}",
    ]


def _abstract_section(data: PaperStubInput) -> list[str]:
    body = data.abstract.strip() if data.abstract else "No abstract available."
    return ["## Abstract", "", body]


def _cited_pages_section(cited: dict[str, str]) -> list[str]:
    lines = ["## Cited pages", ""]
    for locator in sorted(cited):
        page_tag = locator.replace(":", "-")  # "page:4" -> "page-4"
        if locator.startswith("page:"):
            page_tag = f"p-{locator.split(':', 1)[1]}"
        lines.append(f"### {page_tag}")
        lines.append("")
        lines.append(f"> {cited[locator]}")
        lines.append("")
    return lines


def _claims_section(review_id: str, claim: Optional[tuple[str, str]]) -> list[str]:
    if claim is None:
        return []
    text, link = claim
    return [
        f"## Claims in review: {review_id}",
        "",
        f"- {text} -> {link}",
    ]


def _owned_body(data: PaperStubInput) -> str:
    blocks: list[list[str]] = [
        [_header(data), ""],
        _metadata_block(data) + [""],
        _abstract_section(data) + [""],
        _cited_pages_section(data.cited_pages),
    ]
    claims = _claims_section(data.review_id, data.synthesis_claim)
    if claims:
        blocks.append(claims + [""])
    out: list[str] = []
    for block in blocks:
        out.extend(block)
    return "\n".join(out).rstrip() + "\n"


def _split_sections(body: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in body.splitlines():
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif line.startswith("# "):
            sections.append((f"__h1__:{line[2:].strip()}", []))
        else:
            sections[-1][1].append(line)
    return sections


def _merge_with_user_edits(existing_body: str, regenerated_body: str, review_id: str) -> str:
    existing_sections = _split_sections(existing_body)
    regen_sections = _split_sections(regenerated_body)
    owned = {"Abstract", "Cited pages", f"Claims in review: {review_id}"}
    out_lines: list[str] = []
    for name, lines in regen_sections:
        if name.startswith("__h1__:") or name == "":
            out_lines.extend(lines)
            continue
        out_lines.append(f"## {name}")
        out_lines.extend(lines)
    for name, lines in existing_sections:
        if not name or name.startswith("__h1__:"):
            continue
        if name in owned:
            continue
        out_lines.append("")
        out_lines.append(f"## {name}")
        out_lines.extend(lines)
    return "\n".join(out_lines).rstrip() + "\n"


def write_or_update_paper_stub(path: Path, data: PaperStubInput) -> str:
    """Write/update a paper stub.

    Returns one of: `"created"`, `"updated"`, `"W_EMPTY_EVIDENCE"`.
    """
    path = Path(path)
    if not data.cited_pages:
        return "W_EMPTY_EVIDENCE"

    frontmatter = PaperStubFrontmatter(
        schema_version="scriptorium.paper.v1",
        scriptorium_version="0.3.1",
        paper_id=data.paper_id,
        title=data.title,
        authors=list(data.authors),
        year=data.year,
        tags=list(data.tags),
        reviewed_in=[data.review_id],
        full_text_source=data.full_text_source,
        created_at=data.now_iso,
        updated_at=data.now_iso,
        doi=data.doi,
        pdf_path=data.pdf_path,
        source_url=data.source_url,
    )
    owned = _owned_body(data)

    if path.exists():
        existing = path.read_text(encoding="utf-8")
        existing_body = strip_frontmatter(existing)
        try:
            existing_fm = read_frontmatter(existing)
            created = existing_fm.get("created_at", data.now_iso)
            reviewed = set(existing_fm.get("reviewed_in") or [])
            reviewed.add(data.review_id)
            frontmatter.created_at = created
            frontmatter.reviewed_in = sorted(reviewed)
        except Exception:
            pass
        merged_body = _merge_with_user_edits(existing_body, owned, data.review_id)
        path.write_text(
            write_frontmatter(frontmatter.to_dict(), body=merged_body),
            encoding="utf-8",
        )
        return "updated"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        write_frontmatter(frontmatter.to_dict(), body=owned),
        encoding="utf-8",
    )
    return "created"
