from pathlib import Path

ADD_PDF = Path("commands/lit-add-pdf.md")
SHOW_AUDIT = Path("commands/lit-show-audit.md")
EXPORT_BIB = Path("commands/lit-export-bib.md")


def _read(p: Path) -> str:
    assert p.exists(), f"missing: {p}"
    return p.read_text(encoding="utf-8")


def test_lit_add_pdf_exists_and_invokes_register_pdf():
    text = _read(ADD_PDF)
    assert text.startswith("---\n")
    assert "description:" in text
    assert "argument-hint:" in text
    assert "scriptorium register-pdf" in text
    assert "--pdf" in text
    assert "--paper-id" in text
    assert "scriptorium audit append" in text
    assert "user_pdf.register" in text


def test_lit_add_pdf_passes_args_through():
    text = _read(ADD_PDF)
    assert "{{ARGS}}" in text or "$ARGUMENTS" in text


def test_lit_show_audit_reads_audit():
    text = _read(SHOW_AUDIT)
    assert text.startswith("---\n")
    assert "scriptorium audit read" in text
    assert "audit.jsonl" in text
    assert "audit.md" in text


def test_lit_export_bib_calls_both_formats():
    text = _read(EXPORT_BIB)
    assert text.startswith("---\n")
    assert "scriptorium bib --format bibtex" in text
    assert "scriptorium bib --format ris" in text
    assert "scriptorium audit append" in text
    assert "bib.write" in text


def test_all_three_mention_review_dir_flag():
    for p in (ADD_PDF, SHOW_AUDIT, EXPORT_BIB):
        assert "--review-dir" in _read(p), f"missing --review-dir in {p.name}"


def test_none_shell_exec_python():
    for p in (ADD_PDF, SHOW_AUDIT, EXPORT_BIB):
        text = _read(p).lower()
        assert "python -c" not in text, f"{p.name} invokes python -c (defect #3)"
