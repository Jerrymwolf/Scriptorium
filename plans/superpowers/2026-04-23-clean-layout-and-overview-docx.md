# Clean Review Layout + Automatic Overview.docx Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the review folder into a hybrid layout (deliverables at root, sources/data/audit bucketed) and render `overview.docx` automatically every time `overview.md` is written, with citation enrichment from `corpus.jsonl`.

**Architecture:** Single source of truth for paths is `scriptorium/paths.py` — changing `ReviewPaths` properties relocates every call site in one commit. A new `scriptorium/export.py` module renders `overview.md` → `overview.docx` using `python-docx`; it's invoked from inside `regenerate_overview()` right after the `.md` is written. Docx render is best-effort — failure logs an audit event but never fails the overview step.

**Tech Stack:** Python 3.11+, `python-docx>=1.1,<2`, `pytest`, existing `scriptorium` package.

**Spec:** `plans/superpowers/2026-04-23-clean-layout-and-office-export-design.md`

---

## File Structure

**New files:**
- `scriptorium/export.py` — docx rendering module: markdown walker + citation enricher.
- `tests/test_paths_new_layout.py`
- `tests/test_export_headings_paragraphs.py`
- `tests/test_export_lists.py`
- `tests/test_export_tables.py`
- `tests/test_export_inline_formatting.py`
- `tests/test_export_citations.py`
- `tests/test_export_code_fence_skip.py`
- `tests/test_export_corpus_missing.py`
- `tests/test_overview_dual_write.py`
- `tests/test_overview_docx_failure_isolation.py`
- `tests/test_overview_docx_opens.py`
- `tests/fixtures/overview/` — minimal overview.md + corpus.jsonl fixtures

**Modified files:**
- `scriptorium/paths.py` — relocate existing properties; add `audit_dir`, `data_dir`, `sources_dir`, `scriptorium_dir`, `lock`, `overview_docx`.
- `scriptorium/overview/generator.py` — call `render_overview_docx` after writing `.md`; fix `write_failed_draft` to use `paths.overview_archive`.
- `pyproject.toml` — add `python-docx>=1.1,<2`.
- `skills/generating-overview/SKILL.md` — one-line note about automatic `.docx`.
- `README.md` — one-sentence feature mention.
- `CHANGELOG.md` — entry.

**Manual (one-shot session action, not code):**
- Migrate existing `~/Desktop/values-review/` folder.

---

## Task 1: Update `ReviewPaths` to the new layout

**Files:**
- Modify: `scriptorium/paths.py`
- Test: `tests/test_paths_new_layout.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_paths_new_layout.py
from pathlib import Path
from scriptorium.paths import ReviewPaths


def test_paths_resolve_to_new_layout(tmp_path: Path):
    p = ReviewPaths(root=tmp_path)

    # Prose deliverables stay at root.
    assert p.overview == tmp_path / "overview.md"
    assert p.overview_docx == tmp_path / "overview.docx"
    assert p.synthesis == tmp_path / "synthesis.md"
    assert p.contradictions == tmp_path / "contradictions.md"
    assert p.scope == tmp_path / "scope.json"
    assert p.references_bib == tmp_path / "references.bib"

    # Sources bucket.
    assert p.sources_dir == tmp_path / "sources"
    assert p.pdfs == tmp_path / "sources" / "pdfs"
    assert p.papers == tmp_path / "sources" / "papers"

    # Data bucket.
    assert p.data_dir == tmp_path / "data"
    assert p.evidence == tmp_path / "data" / "evidence.jsonl"
    assert p.corpus == tmp_path / "data" / "corpus.jsonl"
    assert p.extracts == tmp_path / "data" / "extracts"

    # Audit bucket.
    assert p.audit_dir == tmp_path / "audit"
    assert p.audit_md == tmp_path / "audit" / "audit.md"
    assert p.audit_jsonl == tmp_path / "audit" / "audit.jsonl"
    assert p.overview_archive == tmp_path / "audit" / "overview-archive"

    # Internal state.
    assert p.scriptorium_dir == tmp_path / ".scriptorium"
    assert p.lock == tmp_path / ".scriptorium" / "lock"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_paths_new_layout.py -v`
Expected: FAIL — `overview_docx`, `sources_dir`, `data_dir`, `audit_dir`, `scriptorium_dir`, and `lock` don't exist; `evidence`, `corpus`, `audit_md`, etc. resolve to old paths.

- [ ] **Step 3: Update `ReviewPaths`**

Replace the body of `scriptorium/paths.py`'s `ReviewPaths` dataclass with:

```python
@dataclass(frozen=True)
class ReviewPaths:
    root: Path

    # Prose deliverables (root)
    @property
    def overview(self) -> Path:
        return self.root / "overview.md"

    @property
    def overview_docx(self) -> Path:
        return self.root / "overview.docx"

    @property
    def synthesis(self) -> Path:
        return self.root / "synthesis.md"

    @property
    def contradictions(self) -> Path:
        return self.root / "contradictions.md"

    @property
    def scope(self) -> Path:
        return self.root / "scope.json"

    @property
    def references_bib(self) -> Path:
        return self.root / "references.bib"

    # Sources bucket
    @property
    def sources_dir(self) -> Path:
        return self.root / "sources"

    @property
    def pdfs(self) -> Path:
        return self.sources_dir / "pdfs"

    @property
    def papers(self) -> Path:
        return self.sources_dir / "papers"

    # Data bucket
    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def evidence(self) -> Path:
        return self.data_dir / "evidence.jsonl"

    @property
    def corpus(self) -> Path:
        return self.data_dir / "corpus.jsonl"

    @property
    def extracts(self) -> Path:
        return self.data_dir / "extracts"

    # Audit bucket
    @property
    def audit_dir(self) -> Path:
        return self.root / "audit"

    @property
    def audit_md(self) -> Path:
        return self.audit_dir / "audit.md"

    @property
    def audit_jsonl(self) -> Path:
        return self.audit_dir / "audit.jsonl"

    @property
    def overview_archive(self) -> Path:
        return self.audit_dir / "overview-archive"

    # Internal state
    @property
    def scriptorium_dir(self) -> Path:
        return self.root / ".scriptorium"

    @property
    def lock(self) -> Path:
        return self.scriptorium_dir / "lock"

    # Retained for backwards API — remove if no callers.
    @property
    def bib(self) -> Path:
        return self.sources_dir / "bib"

    @property
    def outputs(self) -> Path:
        return self.root / "outputs"
```

Also update `resolve_review_dir`'s `create=True` branch to create the new directory set:

```python
    if create:
        for sub in (
            "sources/pdfs",
            "sources/papers",
            "data/extracts",
            "audit/overview-archive",
            ".scriptorium",
        ):
            (root / sub).mkdir(parents=True, exist_ok=True)
    return ReviewPaths(root=root)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_paths_new_layout.py -v`
Expected: PASS.

- [ ] **Step 5: Run full test suite to catch regressions from the path move**

Run: `pytest -q`
Expected: Some existing tests may fail because fixtures assume the old layout. If a failure is a real bug (call site pointing at an old path that no longer exists), fix the call site in this commit. If a failure is purely a test fixture assumption (e.g. a test writes a file directly to `tmp_path/"evidence.jsonl"` and then checks `paths.evidence`), update the fixture to use the new path. Do not suppress failures.

- [ ] **Step 6: Commit**

```bash
git add scriptorium/paths.py tests/test_paths_new_layout.py
git commit -m "refactor(paths): hybrid review layout — sources/data/audit buckets"
```

---

## Task 2: Update `write_failed_draft` to use the audit archive

**Files:**
- Modify: `scriptorium/overview/generator.py:150-155`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_write_failed_draft_location.py
from pathlib import Path
from scriptorium.overview.generator import write_failed_draft
from scriptorium.paths import ReviewPaths


def test_failed_draft_goes_to_overview_archive(tmp_path: Path):
    paths = ReviewPaths(root=tmp_path)
    result = write_failed_draft(paths, body="# broken\n")
    assert result.parent == paths.overview_archive
    assert result.exists()
    assert result.name.endswith(".md")
    # Should not pollute review root.
    root_failed = list(tmp_path.glob("overview.failed.*.md"))
    assert root_failed == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_write_failed_draft_location.py -v`
Expected: FAIL — current implementation writes to `paths.root`.

- [ ] **Step 3: Update `write_failed_draft`**

Replace the function body in `scriptorium/overview/generator.py`:

```python
def write_failed_draft(paths: ReviewPaths, body: str) -> Path:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stamp = now.replace(":", "").replace("-", "")
    paths.overview_archive.mkdir(parents=True, exist_ok=True)
    p = paths.overview_archive / f"overview.failed.{stamp}.md"
    p.write_text(body, encoding="utf-8")
    return p
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_write_failed_draft_location.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scriptorium/overview/generator.py tests/test_write_failed_draft_location.py
git commit -m "fix(overview): failed drafts land in audit/overview-archive, not root"
```

---

## Task 3: Add `python-docx` dep and empty `export.py` module

**Files:**
- Modify: `pyproject.toml`
- Create: `scriptorium/export.py`

- [ ] **Step 1: Add dependency**

Edit `pyproject.toml`, add to the `dependencies` list:

```toml
dependencies = [
  "httpx>=0.27",
  "pypdf>=4.2",
  "python-docx>=1.1,<2",
]
```

- [ ] **Step 2: Create empty export module**

Create `scriptorium/export.py` with:

```python
"""Render overview.md → overview.docx with citation enrichment.

Best-effort converter: handles only the markdown shapes Scriptorium emits
(H1/H2/H3 headings, paragraphs, bullet/ordered lists, tables, inline
bold/italic/code, and `[paper_id:locator]` citations).

Failure must never block overview generation — the .md is the source of truth.
"""
from __future__ import annotations

from pathlib import Path
```

- [ ] **Step 3: Install the new dep**

Run: `pip install -e .`
Expected: `python-docx` installed.

- [ ] **Step 4: Verify import works**

Run: `python -c "from docx import Document; print('ok')"`
Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml scriptorium/export.py
git commit -m "feat(export): add python-docx dep and module scaffold"
```

---

## Task 4: Render headings and paragraphs

**Files:**
- Modify: `scriptorium/export.py`
- Create: `tests/test_export_headings_paragraphs.py`
- Create: `tests/fixtures/overview/`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_export_headings_paragraphs.py
from pathlib import Path
from docx import Document
from scriptorium.export import render_overview_docx


def test_headings_and_paragraphs(tmp_path: Path):
    md = tmp_path / "overview.md"
    md.write_text(
        "# Title\n\nIntro paragraph.\n\n"
        "## Section A\n\nBody of A.\n\n"
        "### Subsection\n\nDeeper body.\n",
        encoding="utf-8",
    )
    docx = tmp_path / "overview.docx"
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("", encoding="utf-8")

    render_overview_docx(md, docx, corpus)

    doc = Document(str(docx))
    paras = [(p.text, p.style.name) for p in doc.paragraphs]
    assert ("Title", "Heading 1") in paras
    assert ("Section A", "Heading 2") in paras
    assert ("Subsection", "Heading 3") in paras
    bodies = [t for t, _ in paras]
    assert "Intro paragraph." in bodies
    assert "Body of A." in bodies
    assert "Deeper body." in bodies
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_export_headings_paragraphs.py -v`
Expected: FAIL — `render_overview_docx` not defined.

- [ ] **Step 3: Implement headings + paragraphs**

Append to `scriptorium/export.py`:

```python
import re
from docx import Document


_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")


def render_overview_docx(md_path: Path, docx_path: Path, corpus_path: Path) -> None:
    """Render overview.md to .docx. Best-effort; caller isolates failures."""
    text = md_path.read_text(encoding="utf-8")
    body = _strip_frontmatter(text)
    doc = Document()
    for block in _blocks(body):
        _render_block(doc, block)
    doc.save(str(docx_path))


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5 :]
    return text


def _blocks(body: str) -> list[list[str]]:
    """Split body into blocks separated by blank lines."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in body.splitlines():
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _render_block(doc, block: list[str]) -> None:
    first = block[0]
    m = _HEADING_RE.match(first)
    if m and len(block) == 1:
        level = len(m.group(1))
        doc.add_heading(m.group(2).strip(), level=level)
        return
    # Default: paragraph (joined with spaces).
    doc.add_paragraph(" ".join(line.strip() for line in block))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_export_headings_paragraphs.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scriptorium/export.py tests/test_export_headings_paragraphs.py
git commit -m "feat(export): render headings and paragraphs"
```

---

## Task 5: Render bullet and ordered lists

**Files:**
- Modify: `scriptorium/export.py`
- Create: `tests/test_export_lists.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_export_lists.py
from pathlib import Path
from docx import Document
from scriptorium.export import render_overview_docx


def test_bullet_and_ordered_lists(tmp_path: Path):
    md = tmp_path / "overview.md"
    md.write_text(
        "- alpha\n- beta\n- gamma\n\n"
        "1. first\n2. second\n3. third\n",
        encoding="utf-8",
    )
    docx = tmp_path / "overview.docx"
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("", encoding="utf-8")

    render_overview_docx(md, docx, corpus)

    doc = Document(str(docx))
    styles = [p.style.name for p in doc.paragraphs if p.text.strip()]
    assert styles.count("List Bullet") == 3
    assert styles.count("List Number") == 3
    texts = [p.text for p in doc.paragraphs]
    assert "alpha" in texts and "beta" in texts and "gamma" in texts
    assert "first" in texts and "second" in texts and "third" in texts
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_export_lists.py -v`
Expected: FAIL — lists are rendered as one joined paragraph.

- [ ] **Step 3: Implement lists**

Update `_render_block` in `scriptorium/export.py`:

```python
_BULLET_RE = re.compile(r"^[-*+]\s+(.*)$")
_ORDERED_RE = re.compile(r"^\d+\.\s+(.*)$")


def _render_block(doc, block: list[str]) -> None:
    first = block[0]

    m = _HEADING_RE.match(first)
    if m and len(block) == 1:
        level = len(m.group(1))
        doc.add_heading(m.group(2).strip(), level=level)
        return

    if all(_BULLET_RE.match(line) for line in block):
        for line in block:
            doc.add_paragraph(_BULLET_RE.match(line).group(1), style="List Bullet")
        return

    if all(_ORDERED_RE.match(line) for line in block):
        for line in block:
            doc.add_paragraph(_ORDERED_RE.match(line).group(1), style="List Number")
        return

    doc.add_paragraph(" ".join(line.strip() for line in block))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_export_lists.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scriptorium/export.py tests/test_export_lists.py
git commit -m "feat(export): render bullet and ordered lists"
```

---

## Task 6: Render markdown tables

**Files:**
- Modify: `scriptorium/export.py`
- Create: `tests/test_export_tables.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_export_tables.py
from pathlib import Path
from docx import Document
from scriptorium.export import render_overview_docx


def test_markdown_table_becomes_docx_table(tmp_path: Path):
    md = tmp_path / "overview.md"
    md.write_text(
        "| Paper | Claim |\n"
        "| --- | --- |\n"
        "| Smith 2024 | X improves Y |\n"
        "| Jones 2025 | X has no effect |\n",
        encoding="utf-8",
    )
    docx = tmp_path / "overview.docx"
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("", encoding="utf-8")

    render_overview_docx(md, docx, corpus)

    doc = Document(str(docx))
    assert len(doc.tables) == 1
    t = doc.tables[0]
    assert len(t.rows) == 3
    assert t.rows[0].cells[0].text == "Paper"
    assert t.rows[0].cells[1].text == "Claim"
    assert t.rows[1].cells[0].text == "Smith 2024"
    assert t.rows[2].cells[1].text == "X has no effect"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_export_tables.py -v`
Expected: FAIL — table rendered as paragraph.

- [ ] **Step 3: Implement tables**

Update `_render_block`:

```python
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")


def _render_block(doc, block: list[str]) -> None:
    first = block[0]

    m = _HEADING_RE.match(first)
    if m and len(block) == 1:
        level = len(m.group(1))
        doc.add_heading(m.group(2).strip(), level=level)
        return

    if all(_BULLET_RE.match(line) for line in block):
        for line in block:
            doc.add_paragraph(_BULLET_RE.match(line).group(1), style="List Bullet")
        return

    if all(_ORDERED_RE.match(line) for line in block):
        for line in block:
            doc.add_paragraph(_ORDERED_RE.match(line).group(1), style="List Number")
        return

    if len(block) >= 2 and _TABLE_SEP_RE.match(block[1]) and "|" in block[0]:
        _render_table(doc, block)
        return

    doc.add_paragraph(" ".join(line.strip() for line in block))


def _split_table_row(line: str) -> list[str]:
    parts = line.strip().strip("|").split("|")
    return [p.strip() for p in parts]


def _render_table(doc, block: list[str]) -> None:
    header = _split_table_row(block[0])
    rows = [_split_table_row(line) for line in block[2:]]
    table = doc.add_table(rows=1 + len(rows), cols=len(header))
    table.style = "Table Grid"
    for i, cell in enumerate(table.rows[0].cells):
        cell.text = header[i] if i < len(header) else ""
    for r, row in enumerate(rows, start=1):
        for i, cell in enumerate(table.rows[r].cells):
            cell.text = row[i] if i < len(row) else ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_export_tables.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scriptorium/export.py tests/test_export_tables.py
git commit -m "feat(export): render markdown tables as docx tables"
```

---

## Task 7: Render inline bold, italic, and code formatting

**Files:**
- Modify: `scriptorium/export.py`
- Create: `tests/test_export_inline_formatting.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_export_inline_formatting.py
from pathlib import Path
from docx import Document
from scriptorium.export import render_overview_docx


def test_inline_formatting(tmp_path: Path):
    md = tmp_path / "overview.md"
    md.write_text(
        "This is **bold** and *italic* and `code` in one line.\n",
        encoding="utf-8",
    )
    docx = tmp_path / "overview.docx"
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("", encoding="utf-8")

    render_overview_docx(md, docx, corpus)

    doc = Document(str(docx))
    runs = list(doc.paragraphs[0].runs)
    texts = [(r.text, r.bold, r.italic, r.font.name) for r in runs]
    assert any(t == "bold" and b for t, b, _, _ in texts)
    assert any(t == "italic" and i for t, _, i, _ in texts)
    assert any(t == "code" and f in ("Consolas", "Courier New") for t, _, _, f in texts)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_export_inline_formatting.py -v`
Expected: FAIL — paragraph rendered as a single plain run.

- [ ] **Step 3: Implement inline formatting**

Add a tokenizer and a run-emitter in `scriptorium/export.py`:

```python
_INLINE_RE = re.compile(
    r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)"
)


def _emit_runs(paragraph, text: str) -> None:
    parts = _INLINE_RE.split(text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("*") and part.endswith("*"):
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
        else:
            paragraph.add_run(part)
```

Update the default paragraph branch in `_render_block`:

```python
    para = doc.add_paragraph()
    _emit_runs(para, " ".join(line.strip() for line in block))
```

Also update the list branches to use `_emit_runs` so bold/italic/code inside a list item is honored:

```python
    if all(_BULLET_RE.match(line) for line in block):
        for line in block:
            p = doc.add_paragraph(style="List Bullet")
            _emit_runs(p, _BULLET_RE.match(line).group(1))
        return

    if all(_ORDERED_RE.match(line) for line in block):
        for line in block:
            p = doc.add_paragraph(style="List Number")
            _emit_runs(p, _ORDERED_RE.match(line).group(1))
        return
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_export_inline_formatting.py -v`
Expected: PASS.

- [ ] **Step 5: Run all export tests to verify no regression**

Run: `pytest tests/test_export_ -v`
Expected: All export tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scriptorium/export.py tests/test_export_inline_formatting.py
git commit -m "feat(export): render inline bold/italic/code"
```

---

## Task 8: Citation enrichment — corpus lookup and hyperlink precedence

**Files:**
- Modify: `scriptorium/export.py`
- Create: `tests/test_export_citations.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_export_citations.py
import json
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from scriptorium.export import render_overview_docx


def _hyperlink_targets(paragraph) -> list[str]:
    """Return anchor URLs for every hyperlink in the paragraph."""
    urls = []
    part = paragraph.part
    for hl in paragraph._p.findall(qn("w:hyperlink")):
        rid = hl.get(qn("r:id"))
        if rid:
            urls.append(part.rels[rid].target_ref)
    return urls


def _write_corpus(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_citation_with_doi_becomes_doi_hyperlink(tmp_path: Path):
    md = tmp_path / "overview.md"
    md.write_text(
        "The claim holds [smith2024:p.12] under certain conditions.\n",
        encoding="utf-8",
    )
    corpus = tmp_path / "corpus.jsonl"
    _write_corpus(corpus, [{
        "paper_id": "smith2024",
        "authors": ["Smith, Jane"],
        "year": 2024,
        "doi": "10.1234/abc",
        "url": "https://example.org/smith2024",
    }])
    docx = tmp_path / "overview.docx"

    render_overview_docx(md, docx, corpus)

    doc = Document(str(docx))
    p = doc.paragraphs[0]
    assert "(Smith 2024, p. 12)" in p.text
    urls = _hyperlink_targets(p)
    assert urls == ["https://doi.org/10.1234/abc"]


def test_citation_falls_back_to_url_then_stub_then_plain(tmp_path: Path):
    # Row with url only → url used.
    corpus = tmp_path / "corpus.jsonl"
    _write_corpus(corpus, [{
        "paper_id": "jones2025",
        "authors": ["Jones, Lee"],
        "year": 2025,
        "url": "https://example.org/jones",
    }])
    md = tmp_path / "overview.md"
    md.write_text("See [jones2025:p.3].\n", encoding="utf-8")
    docx = tmp_path / "overview.docx"
    render_overview_docx(md, docx, corpus)
    doc = Document(str(docx))
    assert _hyperlink_targets(doc.paragraphs[0]) == ["https://example.org/jones"]

    # Row with no doi/url but stub exists → stub path used.
    _write_corpus(corpus, [{
        "paper_id": "lee2023",
        "authors": ["Lee, A."],
        "year": 2023,
    }])
    papers = tmp_path / "sources" / "papers"
    papers.mkdir(parents=True)
    stub = papers / "lee2023.md"
    stub.write_text("# lee2023\n")
    md.write_text("See [lee2023:p.1].\n", encoding="utf-8")
    render_overview_docx(md, docx, corpus)
    doc = Document(str(docx))
    assert _hyperlink_targets(doc.paragraphs[0]) == [str(stub)]

    # Row with no doi/url and no stub → plain text, no hyperlink.
    _write_corpus(corpus, [{
        "paper_id": "kim2022",
        "authors": ["Kim, B."],
        "year": 2022,
    }])
    md.write_text("See [kim2022:p.9].\n", encoding="utf-8")
    render_overview_docx(md, docx, corpus)
    doc = Document(str(docx))
    p = doc.paragraphs[0]
    assert "(Kim 2022, p. 9)" in p.text
    assert _hyperlink_targets(p) == []


def test_unknown_paper_id_left_raw(tmp_path: Path):
    corpus = tmp_path / "corpus.jsonl"
    _write_corpus(corpus, [])
    md = tmp_path / "overview.md"
    md.write_text("See [ghost2099:p.1].\n", encoding="utf-8")
    docx = tmp_path / "overview.docx"
    render_overview_docx(md, docx, corpus)
    doc = Document(str(docx))
    assert "[ghost2099:p.1]" in doc.paragraphs[0].text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_export_citations.py -v`
Expected: FAIL — `[paper_id:locator]` is rendered as plain text, no hyperlinks.

- [ ] **Step 3: Implement citation enrichment**

Add to `scriptorium/export.py`:

```python
import json
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


_CITATION_RE = re.compile(r"\[([A-Za-z0-9_\-]+):([^\]]+)\]")


def _load_corpus(corpus_path: Path) -> dict[str, dict]:
    if not corpus_path.exists() or corpus_path.stat().st_size == 0:
        return {}
    index: dict[str, dict] = {}
    for line in corpus_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        pid = row.get("paper_id")
        if pid:
            index[pid] = row
    return index


def _first_author_surname(row: dict) -> str:
    authors = row.get("authors") or []
    if not authors:
        return row.get("paper_id", "")
    first = authors[0]
    if isinstance(first, str):
        return first.split(",")[0].strip()
    return first.get("family") or first.get("name", "")


def _citation_label(row: dict, locator: str) -> str:
    surname = _first_author_surname(row)
    year = row.get("year", "n.d.")
    return f"({surname} {year}, {locator})"


def _citation_hyperlink(row: dict, papers_dir: Path) -> str | None:
    doi = row.get("doi")
    if doi:
        return f"https://doi.org/{doi}"
    url = row.get("url")
    if url:
        return url
    stub = papers_dir / f"{row.get('paper_id')}.md"
    if stub.exists():
        return str(stub)
    return None


def _add_hyperlink(paragraph, url: str, text: str) -> None:
    part = paragraph.part
    rid = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), rid)
    run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    style = OxmlElement("w:rStyle")
    style.set(qn("w:val"), "Hyperlink")
    rPr.append(style)
    run.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    run.append(t)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)
```

Thread the corpus through rendering. Change `render_overview_docx`:

```python
def render_overview_docx(md_path: Path, docx_path: Path, corpus_path: Path) -> None:
    text = md_path.read_text(encoding="utf-8")
    body = _strip_frontmatter(text)
    corpus = _load_corpus(corpus_path)
    papers_dir = corpus_path.parent.parent / "sources" / "papers"
    ctx = {"corpus": corpus, "papers_dir": papers_dir, "misses": []}
    doc = Document()
    for block in _blocks(body):
        _render_block(doc, block, ctx)
    doc.save(str(docx_path))
```

Add `ctx` to `_render_block` and `_emit_runs` signatures. Update `_emit_runs` to recognize citations alongside other inline tokens:

```python
_INLINE_RE = re.compile(
    r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[A-Za-z0-9_\-]+:[^\]]+\])"
)


def _emit_runs(paragraph, text: str, ctx: dict) -> None:
    parts = _INLINE_RE.split(text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("*") and part.endswith("*"):
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
        elif _CITATION_RE.fullmatch(part):
            _emit_citation(paragraph, part, ctx)
        else:
            paragraph.add_run(part)


def _emit_citation(paragraph, raw: str, ctx: dict) -> None:
    m = _CITATION_RE.fullmatch(raw)
    pid, locator = m.group(1), m.group(2).strip()
    row = ctx["corpus"].get(pid)
    if not row:
        paragraph.add_run(raw)  # unknown → leave raw
        ctx["misses"].append(pid)
        return
    label = _citation_label(row, locator)
    link = _citation_hyperlink(row, ctx["papers_dir"])
    if link:
        _add_hyperlink(paragraph, link, label)
    else:
        paragraph.add_run(label)
```

Update the default paragraph and list branches in `_render_block` to pass `ctx` through.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_export_citations.py -v`
Expected: PASS.

- [ ] **Step 5: Run all export tests**

Run: `pytest tests/test_export_ -v`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add scriptorium/export.py tests/test_export_citations.py
git commit -m "feat(export): citation enrichment with DOI/url/stub precedence"
```

---

## Task 9: Skip citations inside fenced code blocks and markdown links

**Files:**
- Modify: `scriptorium/export.py`
- Create: `tests/test_export_code_fence_skip.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_export_code_fence_skip.py
from pathlib import Path
from docx import Document
from scriptorium.export import render_overview_docx


def test_citation_inside_code_fence_left_alone(tmp_path: Path):
    md = tmp_path / "overview.md"
    md.write_text(
        "Regular [smith2024:p.1] here.\n\n"
        "```\n"
        "example syntax: [smith2024:p.1]\n"
        "```\n",
        encoding="utf-8",
    )
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        '{"paper_id":"smith2024","authors":["Smith, J."],"year":2024,"doi":"10.1/x"}\n',
        encoding="utf-8",
    )
    docx = tmp_path / "overview.docx"

    render_overview_docx(md, docx, corpus)

    doc = Document(str(docx))
    full = "\n".join(p.text for p in doc.paragraphs)
    # The code-fence line must be preserved verbatim (raw brackets).
    assert "example syntax: [smith2024:p.1]" in full
    # The non-fenced occurrence is enriched.
    assert "(Smith 2024, p. 1)" in full


def test_citation_inside_link_left_alone(tmp_path: Path):
    md = tmp_path / "overview.md"
    md.write_text(
        "See [link text](https://example.org/[smith2024:p.1]).\n",
        encoding="utf-8",
    )
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        '{"paper_id":"smith2024","authors":["Smith, J."],"year":2024,"doi":"10.1/x"}\n',
        encoding="utf-8",
    )
    docx = tmp_path / "overview.docx"

    render_overview_docx(md, docx, corpus)

    doc = Document(str(docx))
    # No (Smith 2024, p. 1) substitution inside the URL text.
    text = doc.paragraphs[0].text
    assert "[smith2024:p.1]" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_export_code_fence_skip.py -v`
Expected: FAIL — fenced block is treated as paragraph; link is tokenized.

- [ ] **Step 3: Implement fenced-block preservation and link guard**

Update `_blocks` to keep fenced blocks intact and tag their type. Introduce a block type carrier:

```python
def _blocks(body: str) -> list[tuple[str, list[str]]]:
    """Return list of (kind, lines). kind is 'fence' or 'prose'."""
    blocks: list[tuple[str, list[str]]] = []
    current: list[str] = []
    in_fence = False
    fence_lines: list[str] = []
    for line in body.splitlines():
        if line.strip().startswith("```"):
            if not in_fence:
                if current:
                    blocks.append(("prose", current))
                    current = []
                in_fence = True
                fence_lines = [line]
            else:
                fence_lines.append(line)
                blocks.append(("fence", fence_lines))
                fence_lines = []
                in_fence = False
            continue
        if in_fence:
            fence_lines.append(line)
            continue
        if line.strip() == "":
            if current:
                blocks.append(("prose", current))
                current = []
        else:
            current.append(line)
    if in_fence and fence_lines:
        blocks.append(("fence", fence_lines))
    if current:
        blocks.append(("prose", current))
    return blocks
```

Update `render_overview_docx` loop:

```python
    for kind, block in _blocks(body):
        if kind == "fence":
            for line in block:
                if line.strip().startswith("```"):
                    continue
                p = doc.add_paragraph(line)
                for r in p.runs:
                    r.font.name = "Consolas"
            continue
        _render_block(doc, block, ctx)
```

For the link guard, add a mask-then-restore step in `_emit_runs`:

```python
_LINK_RE = re.compile(r"\[[^\]]+\]\([^)]+\)")


def _emit_runs(paragraph, text: str, ctx: dict) -> None:
    # Mask inline markdown links so citations inside them are not enriched.
    masks: dict[str, str] = {}

    def _mask(m):
        token = f"\x00LINK{len(masks)}\x00"
        masks[token] = m.group(0)
        return token

    masked = _LINK_RE.sub(_mask, text)
    parts = _INLINE_RE.split(masked)
    for part in parts:
        if not part:
            continue
        # Restore any masked links inside this part before emitting as plain run.
        restored = part
        for token, original in masks.items():
            restored = restored.replace(token, original)
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(restored[2:-2] if restored == part else restored)
            run.bold = True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            run = paragraph.add_run(restored[1:-1] if restored == part else restored)
            run.italic = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(restored[1:-1] if restored == part else restored)
            run.font.name = "Consolas"
        elif _CITATION_RE.fullmatch(part):
            _emit_citation(paragraph, part, ctx)
        else:
            paragraph.add_run(restored)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_export_code_fence_skip.py -v`
Expected: PASS.

- [ ] **Step 5: Run all export tests**

Run: `pytest tests/test_export_ -v`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add scriptorium/export.py tests/test_export_code_fence_skip.py
git commit -m "feat(export): preserve fenced code and skip citations in links"
```

---

## Task 10: Handle missing / empty `corpus.jsonl` gracefully

**Files:**
- Modify: `scriptorium/export.py`
- Create: `tests/test_export_corpus_missing.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_export_corpus_missing.py
from pathlib import Path
from docx import Document
from scriptorium.export import render_overview_docx


def test_missing_corpus_renders_plain_with_misses(tmp_path: Path):
    md = tmp_path / "overview.md"
    md.write_text("See [smith2024:p.1] and [jones2025:p.3].\n", encoding="utf-8")
    corpus = tmp_path / "corpus.jsonl"  # does not exist
    docx = tmp_path / "overview.docx"

    result = render_overview_docx(md, docx, corpus)

    assert result.corpus_unavailable is True
    assert set(result.citation_misses) == {"smith2024", "jones2025"}
    doc = Document(str(docx))
    text = doc.paragraphs[0].text
    assert "[smith2024:p.1]" in text
    assert "[jones2025:p.3]" in text


def test_corpus_present_returns_misses_list(tmp_path: Path):
    md = tmp_path / "overview.md"
    md.write_text(
        "Known [a2024:p.1]. Unknown [b2099:p.2].\n", encoding="utf-8"
    )
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        '{"paper_id":"a2024","authors":["A."],"year":2024,"doi":"10/a"}\n',
        encoding="utf-8",
    )
    docx = tmp_path / "overview.docx"

    result = render_overview_docx(md, docx, corpus)

    assert result.corpus_unavailable is False
    assert result.citation_misses == ["b2099"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_export_corpus_missing.py -v`
Expected: FAIL — `render_overview_docx` returns `None`.

- [ ] **Step 3: Return a structured result**

Add to `scriptorium/export.py`:

```python
from dataclasses import dataclass, field


@dataclass
class OverviewDocxResult:
    corpus_unavailable: bool
    citation_misses: list[str] = field(default_factory=list)
```

Change `render_overview_docx` return type and body end:

```python
def render_overview_docx(
    md_path: Path, docx_path: Path, corpus_path: Path
) -> OverviewDocxResult:
    text = md_path.read_text(encoding="utf-8")
    body = _strip_frontmatter(text)
    corpus = _load_corpus(corpus_path)
    corpus_unavailable = not corpus
    papers_dir = corpus_path.parent.parent / "sources" / "papers"
    ctx = {"corpus": corpus, "papers_dir": papers_dir, "misses": []}
    doc = Document()
    for kind, block in _blocks(body):
        if kind == "fence":
            for line in block:
                if line.strip().startswith("```"):
                    continue
                p = doc.add_paragraph(line)
                for r in p.runs:
                    r.font.name = "Consolas"
            continue
        _render_block(doc, block, ctx)
    doc.save(str(docx_path))
    return OverviewDocxResult(
        corpus_unavailable=corpus_unavailable,
        citation_misses=list(dict.fromkeys(ctx["misses"])),  # dedup, preserve order
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_export_corpus_missing.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scriptorium/export.py tests/test_export_corpus_missing.py
git commit -m "feat(export): structured result with corpus availability and misses"
```

---

## Task 11: Integrate docx render into `regenerate_overview`

**Files:**
- Modify: `scriptorium/overview/generator.py`
- Create: `tests/test_overview_dual_write.py`

- [ ] **Step 1: Read the current `regenerate_overview` signature and audit append pattern**

Run: `grep -n "audit\|append_audit\|OverviewResult" scriptorium/overview/generator.py`
Note how the existing code appends audit events (`append_audit(paths, ...)` or direct call) so the new event uses the same pattern.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_overview_dual_write.py
import json
from pathlib import Path
from scriptorium.overview.generator import regenerate_overview
from scriptorium.paths import ReviewPaths


def _prepare_review(tmp_path: Path) -> ReviewPaths:
    paths = ReviewPaths(root=tmp_path)
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    paths.audit_dir.mkdir(parents=True, exist_ok=True)
    # Minimal inputs expected by _compose_body / lint_overview.
    paths.synthesis.write_text(
        "# Synthesis\n\n## Claim 1 [smith2024:p.1]\n\nBody.\n",
        encoding="utf-8",
    )
    paths.contradictions.write_text("# Contradictions\n\nNone noted.\n", encoding="utf-8")
    paths.evidence.write_text(
        '{"paper_id":"smith2024","locator":"p.1","claim":"X","quote":"Y"}\n',
        encoding="utf-8",
    )
    paths.corpus.write_text(
        '{"paper_id":"smith2024","authors":["Smith, J."],"year":2024,"doi":"10/a"}\n',
        encoding="utf-8",
    )
    return paths


def test_regenerate_overview_writes_md_and_docx(tmp_path: Path):
    paths = _prepare_review(tmp_path)
    regenerate_overview(
        paths=paths,
        research_question="Does X improve Y?",
        review_id="test-review",
    )
    assert paths.overview.exists()
    assert paths.overview_docx.exists()
    # The docx must be a valid zip / docx.
    from docx import Document
    Document(str(paths.overview_docx))  # raises on corruption


def test_regenerate_overview_appends_audit_event(tmp_path: Path):
    paths = _prepare_review(tmp_path)
    regenerate_overview(
        paths=paths,
        research_question="Q",
        review_id="r",
    )
    events = [
        json.loads(line)
        for line in paths.audit_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    overview_events = [e for e in events if e.get("event") == "overview_rendered"]
    assert len(overview_events) == 1
    ev = overview_events[0]
    assert set(ev["wrote"]) == {"overview.md", "overview.docx"}
    assert "source_sha256" in ev
    assert ev["citation_misses"] == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_overview_dual_write.py -v`
Expected: FAIL — `.docx` not written, no `overview_rendered` audit event.

- [ ] **Step 4: Integrate docx render**

Modify `scriptorium/overview/generator.py`'s `regenerate_overview`. After `paths.overview.write_text(text, encoding="utf-8")` (around line 141), add:

```python
    # Dual-write: best-effort docx alongside the canonical .md.
    import hashlib
    from scriptorium.export import render_overview_docx
    from scriptorium.storage.audit import append_audit

    source_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    try:
        result = render_overview_docx(
            paths.overview, paths.overview_docx, paths.corpus
        )
        append_audit(
            paths,
            {
                "event": "overview_rendered",
                "wrote": ["overview.md", "overview.docx"],
                "source_sha256": source_sha,
                "citation_misses": result.citation_misses,
                "corpus_unavailable": result.corpus_unavailable,
            },
        )
    except Exception as exc:  # docx render must never fail the overview step
        append_audit(
            paths,
            {
                "event": "overview_docx_failed",
                "wrote": ["overview.md"],
                "source_sha256": source_sha,
                "error": str(exc)[:200],
            },
        )
```

If `append_audit`'s signature differs from `(paths, dict)`, match the existing pattern in `scriptorium/storage/audit.py`. Check: `grep -n "def append_audit\|def append_event" scriptorium/storage/audit.py` — use whichever exists, passing the event dict accordingly.

- [ ] **Step 5: Run the dual-write tests**

Run: `pytest tests/test_overview_dual_write.py -v`
Expected: PASS.

- [ ] **Step 6: Run full test suite**

Run: `pytest -q`
Expected: All PASS. If an unrelated test fails because it now sees a new audit event, update the assertion to filter by event type.

- [ ] **Step 7: Commit**

```bash
git add scriptorium/overview/generator.py tests/test_overview_dual_write.py
git commit -m "feat(overview): write overview.docx alongside .md, append audit event"
```

---

## Task 12: Docx render failure isolation

**Files:**
- Create: `tests/test_overview_docx_failure_isolation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_overview_docx_failure_isolation.py
import json
from pathlib import Path
from unittest.mock import patch
from scriptorium.overview.generator import regenerate_overview
from scriptorium.paths import ReviewPaths


def _prepare(tmp_path: Path) -> ReviewPaths:
    paths = ReviewPaths(root=tmp_path)
    paths.data_dir.mkdir(parents=True)
    paths.audit_dir.mkdir(parents=True)
    paths.synthesis.write_text("# S\n\n## C\n\nBody.\n", encoding="utf-8")
    paths.contradictions.write_text("# X\n\nn/a.\n", encoding="utf-8")
    paths.evidence.write_text("", encoding="utf-8")
    paths.corpus.write_text("", encoding="utf-8")
    return paths


def test_docx_render_failure_isolated_from_md(tmp_path: Path):
    paths = _prepare(tmp_path)
    with patch(
        "scriptorium.overview.generator.render_overview_docx",
        side_effect=RuntimeError("boom"),
    ):
        regenerate_overview(
            paths=paths, research_question="Q", review_id="r"
        )
    # .md still written.
    assert paths.overview.exists()
    # .docx not written (or at least not required).
    # Audit event indicates failure.
    events = [
        json.loads(line)
        for line in paths.audit_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    failures = [e for e in events if e.get("event") == "overview_docx_failed"]
    assert len(failures) == 1
    assert "boom" in failures[0]["error"]
```

- [ ] **Step 2: Run test to verify behavior**

Run: `pytest tests/test_overview_docx_failure_isolation.py -v`
Expected: PASS (the try/except in Task 11 handles this). If it fails, the exception catch isn't wrapping the right call — fix.

- [ ] **Step 3: Commit**

```bash
git add tests/test_overview_docx_failure_isolation.py
git commit -m "test(overview): docx failure does not break .md write"
```

---

## Task 13: Docx-open integrity smoke test

**Files:**
- Create: `tests/test_overview_docx_opens.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_overview_docx_opens.py
import zipfile
from pathlib import Path
from docx import Document
from scriptorium.export import render_overview_docx


def test_rendered_docx_is_valid_zip_and_reopens(tmp_path: Path):
    md = tmp_path / "overview.md"
    md.write_text(
        "# Title\n\nA paragraph with **bold** and [smith2024:p.1] citation.\n\n"
        "- one\n- two\n\n"
        "| A | B |\n| - | - |\n| 1 | 2 |\n",
        encoding="utf-8",
    )
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        '{"paper_id":"smith2024","authors":["Smith, J."],"year":2024,"doi":"10/a"}\n',
        encoding="utf-8",
    )
    docx = tmp_path / "overview.docx"

    render_overview_docx(md, docx, corpus)

    # Valid zip.
    assert zipfile.is_zipfile(docx)
    # Reopens cleanly via python-docx.
    doc = Document(str(docx))
    # Must contain at least one heading, one paragraph, one table.
    assert any(p.style.name.startswith("Heading") for p in doc.paragraphs)
    assert len(doc.tables) == 1
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_overview_docx_opens.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_overview_docx_opens.py
git commit -m "test(export): docx integrity smoke — zip + python-docx reopen"
```

---

## Task 14: Update `generating-overview` skill, README, CHANGELOG

**Files:**
- Modify: `skills/generating-overview/SKILL.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add one-line note to the skill**

In `skills/generating-overview/SKILL.md`, add after the first descriptive paragraph (or under a relevant subsection like "Outputs"):

```markdown
**Word export:** the overview is written as both `overview.md` and `overview.docx`. The Word document is regenerated from the markdown every run — it's a derivative, not a source. Edit `overview.md`; `overview.docx` will refresh next time.
```

- [ ] **Step 2: Add one-line mention to README**

In `README.md`, in the features list (or create a "What you get" section), add:

```markdown
- **Word-ready overview.** The overview is written as both Markdown and `overview.docx`, so you can hand the Word document to a committee member who doesn't use Obsidian.
```

- [ ] **Step 3: Add CHANGELOG entry**

Prepend a new section to `CHANGELOG.md`:

```markdown
## Unreleased

### Added
- Automatic `overview.docx` render alongside `overview.md` on every overview generation. Citations resolve to `(Author Year, locator)` with a DOI/URL/stub hyperlink (in that precedence order).

### Changed
- Review folder layout reorganized into a hybrid structure: deliverables at root (`overview.md`, `overview.docx`, `synthesis.md`, `contradictions.md`, `scope.json`, `references.bib`); inputs under `sources/`; machine-readable data under `data/`; audit trail and failed-overview archive under `audit/`; internal state under `.scriptorium/`.
- Failed overview drafts now land in `audit/overview-archive/` instead of the review root.

### Dependencies
- Added `python-docx>=1.1,<2`.
```

- [ ] **Step 4: Commit**

```bash
git add skills/generating-overview/SKILL.md README.md CHANGELOG.md
git commit -m "docs: note automatic overview.docx in skill, README, CHANGELOG"
```

---

## Task 15: Migrate existing `~/Desktop/values-review/`

This task is a one-shot manual operation performed by Claude, not shipped as code. Run it only after all prior tasks pass.

**Target:** `/Users/jeremiahwolf/Desktop/values-review/`

- [ ] **Step 1: Dry-run inventory**

Run:
```bash
ls -la /Users/jeremiahwolf/Desktop/values-review/
ls -la /Users/jeremiahwolf/Desktop/values-review/bib/ 2>/dev/null
ls -la /Users/jeremiahwolf/Desktop/values-review/outputs/ 2>/dev/null
```
Note: any non-empty `bib/` or `outputs/` contents must trigger a pause and user confirmation before proceeding.

- [ ] **Step 2: Create the new directory skeleton**

```bash
cd /Users/jeremiahwolf/Desktop/values-review
mkdir -p sources data audit .scriptorium audit/overview-archive
```

- [ ] **Step 3: Move source inputs**

```bash
[ -d pdfs ] && mv pdfs sources/pdfs
[ -d papers ] && mv papers sources/papers
```

- [ ] **Step 4: Move data files**

```bash
[ -f evidence.jsonl ] && mv evidence.jsonl data/evidence.jsonl
[ -f corpus.jsonl ] && mv corpus.jsonl data/corpus.jsonl
[ -d extracts ] && mv extracts data/extracts
```

- [ ] **Step 5: Move audit trail and failed overviews**

```bash
[ -f audit.md ] && mv audit.md audit/audit.md
[ -f audit.jsonl ] && mv audit.jsonl audit/audit.jsonl
for f in overview.failed.*.md; do
  [ -f "$f" ] && mv "$f" audit/overview-archive/
done
```

- [ ] **Step 6: Clean up empty legacy folders**

```bash
[ -d bib ] && rmdir bib 2>/dev/null || echo "bib/ not empty — PAUSE and ask user"
[ -d outputs ] && rmdir outputs 2>/dev/null || echo "outputs/ not empty — PAUSE and ask user"
```

- [ ] **Step 7: Render `overview.docx` once against the migrated layout**

```bash
SCRIPTORIUM_REVIEW_DIR=/Users/jeremiahwolf/Desktop/values-review \
python -c "
from pathlib import Path
from scriptorium.export import render_overview_docx
from scriptorium.paths import ReviewPaths
p = ReviewPaths(root=Path('/Users/jeremiahwolf/Desktop/values-review'))
render_overview_docx(p.overview, p.overview_docx, p.corpus)
print('wrote', p.overview_docx)
"
```

Expected: `overview.docx` created at the review root.

- [ ] **Step 8: Append a `migrated_layout` audit event**

```bash
python -c "
from datetime import datetime, timezone
from pathlib import Path
from scriptorium.storage.audit import append_audit
from scriptorium.paths import ReviewPaths
p = ReviewPaths(root=Path('/Users/jeremiahwolf/Desktop/values-review'))
append_audit(p, {
    'event': 'migrated_layout',
    'ts': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
    'notes': 'manual migration to hybrid layout (2026-04-23)',
})
"
```

- [ ] **Step 9: Verify the final state**

Run: `ls -la /Users/jeremiahwolf/Desktop/values-review/`
Expected to see: `overview.md`, `overview.docx`, `synthesis.md`, `contradictions.md`, `sources/`, `data/`, `audit/`, `.scriptorium/`. No `evidence.jsonl`, `pdfs/`, `extracts/`, or `overview.failed.*.md` at root.

---

## Summary

15 tasks, each atomic. Task 1 is the widest-blast-radius change (path reorg); the full test suite run at step 5 of Task 1 is the safety net for unexpected call sites. Tasks 4–10 incrementally build the docx renderer with TDD. Task 11 wires it into overview generation. Tasks 12–13 harden failure modes. Task 14 updates user-facing docs. Task 15 migrates the existing review.
