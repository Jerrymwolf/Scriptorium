"""BibTeX + RIS emitters from the corpus. Only exports kept papers."""
from __future__ import annotations
from scriptorium.paths import ReviewPaths
from scriptorium.storage.corpus import load_corpus


def _kept(paths: ReviewPaths) -> list[dict]:
    return [r for r in load_corpus(paths) if r.get("status") == "kept"]


def export_bibtex(paths: ReviewPaths) -> str:
    chunks: list[str] = []
    for r in _kept(paths):
        fields = [f"  title = {{{r.get('title','')}}}",
                  f"  author = {{{' and '.join(r.get('authors') or [])}}}"]
        if r.get("year"):
            fields.append(f"  year = {{{r['year']}}}")
        if r.get("venue"):
            fields.append(f"  journal = {{{r['venue']}}}")
        if r.get("doi"):
            fields.append(f"  doi = {{{r['doi']}}}")
        chunks.append("@article{" + (r.get("paper_id") or "unknown") + ",\n" + ",\n".join(fields) + "\n}\n")
    out = "\n".join(chunks)
    paths.bib.mkdir(parents=True, exist_ok=True)
    (paths.bib / "export.bib").write_text(out, encoding="utf-8")
    return out


def export_ris(paths: ReviewPaths) -> str:
    chunks: list[str] = []
    for r in _kept(paths):
        lines = ["TY  - JOUR", f"TI  - {r.get('title','')}"]
        for a in r.get("authors") or []:
            lines.append(f"AU  - {a}")
        if r.get("year"):
            lines.append(f"PY  - {r['year']}")
        if r.get("venue"):
            lines.append(f"JO  - {r['venue']}")
        if r.get("doi"):
            lines.append(f"DO  - {r['doi']}")
        lines.append("ER  -")
        chunks.append("\n".join(lines))
    out = "\n\n".join(chunks)
    paths.bib.mkdir(parents=True, exist_ok=True)
    (paths.bib / "export.ris").write_text(out, encoding="utf-8")
    return out
