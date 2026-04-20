"""Corpus store: union of papers from all sources, dedup-aware."""
from __future__ import annotations
import json
import re
from dataclasses import asdict
from typing import Iterable
from scriptorium.paths import ReviewPaths
from scriptorium.sources.base import Paper

_NORMALIZE_TITLE = re.compile(r"[^a-z0-9]+")

def _title_key(t: str) -> str:
    return _NORMALIZE_TITLE.sub(" ", t.lower()).strip()

def _row_key(row: dict) -> str:
    if row.get("doi"):
        return f"doi:{row['doi']}"
    if row.get("paper_id"):
        return f"id:{row['source']}:{row['paper_id']}"
    return f"title:{_title_key(row.get('title',''))}"

def load_corpus(paths: ReviewPaths) -> list[dict]:
    if not paths.corpus.exists():
        return []
    rows: list[dict] = []
    with paths.corpus.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def _write_corpus(paths: ReviewPaths, rows: list[dict]) -> None:
    paths.corpus.parent.mkdir(parents=True, exist_ok=True)
    with paths.corpus.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def add_papers(paths: ReviewPaths, papers: Iterable[Paper]) -> int:
    """Append papers, deduping by DOI → (source, paper_id) → normalized title.
    Returns the number of newly added rows.
    """
    rows = load_corpus(paths)
    by_key = {_row_key(r): r for r in rows}
    title_index = {_title_key(r.get("title", "")): r for r in rows if not r.get("doi")}
    added = 0
    for p in papers:
        d = asdict(p)
        d["status"] = "candidate"
        d["reason"] = None
        d.pop("raw", None)
        key = _row_key(d)
        if key in by_key:
            continue
        if not d.get("doi"):
            tk = _title_key(d.get("title", ""))
            if tk and tk in title_index:
                continue
            title_index[tk] = d
        by_key[key] = d
        rows.append(d)
        added += 1
    _write_corpus(paths, rows)
    return added

def set_status(paths: ReviewPaths, paper_id: str, status: str, reason: str | None = None) -> None:
    rows = load_corpus(paths)
    for r in rows:
        if r.get("paper_id") == paper_id:
            r["status"] = status
            r["reason"] = reason
    _write_corpus(paths, rows)
