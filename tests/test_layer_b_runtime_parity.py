"""
Phase 0 / T02: NotebookLM source acceptance for reviewer input.

Records the empirical result of whether NotebookLM ingests synthesis-style
markdown for reviewer-style cite-checking.

Result:       pass
Date:         2026-04-26
Source form:  text (source_type="text")
Notebook:     scriptorium-t02-spike (deleted after probe)
Method:       Added a 10-claim test synthesis (7 cited via [paper:xxx],
              3 intentionally unsupported) via source_add(source_type="text").
              Source ingested cleanly (ready=True, sub-second).
              Reviewer-style query returned a per-claim breakdown that:
                - correctly named all 7 cited claims with their citation marker
                - flagged all 3 unsupported claims with verbatim quotes
              Output included structured citation back-references.

Implication for Phase 5:
    T15 Cowork reviewer branch = `notebooklm`.
    `source_type="text"` is the chosen reviewer-input form for v0.4.
    File/URL forms are not required to ship the cite-reviewer happy path.
"""

ALLOWED_GRADES = {"pass", "partial", "fail"}
ALLOWED_FORMS = {"text", "file", "url"}
ALLOWED_T15_BRANCHES = {"notebooklm", "degraded"}

NOTEBOOKLM_SOURCE_ACCEPTANCE: str = "pass"
NOTEBOOKLM_SOURCE_FORM: str = "text"

T15_COWORK_REVIEWER_BRANCH: str = (
    "notebooklm" if NOTEBOOKLM_SOURCE_ACCEPTANCE == "pass" else "degraded"
)


def test_t02_grade_recorded() -> None:
    assert NOTEBOOKLM_SOURCE_ACCEPTANCE in ALLOWED_GRADES


def test_t02_source_form_recorded() -> None:
    assert NOTEBOOKLM_SOURCE_FORM in ALLOWED_FORMS


def test_t15_branch_consistent_with_t02() -> None:
    assert T15_COWORK_REVIEWER_BRANCH in ALLOWED_T15_BRANCHES
    if NOTEBOOKLM_SOURCE_ACCEPTANCE == "pass":
        assert T15_COWORK_REVIEWER_BRANCH == "notebooklm"
    else:
        assert T15_COWORK_REVIEWER_BRANCH == "degraded"
