"""§9.4 step 6: prior-publish prompt; --yes auto-confirms; N/EOF exits 0."""
import io
from unittest.mock import patch

import pytest

from scriptorium.cli import main
from scriptorium.nlm import NotebookCreated, NlmResult


_PRIOR_AUDIT_MD = (
    "# PRISMA Audit Trail\n\n## Publishing\n\n"
    "### 2026-04-01T00:00:00Z — NotebookLM\n\n"
    '**Notebook:** "Caffeine Wm" (id: `prev`)\n'
)


@pytest.fixture
def prior_published_review(publish_review_factory):
    """Publish-ready review with a prior NotebookLM publish row in audit.md."""
    return publish_review_factory(seed_audit_md=_PRIOR_AUDIT_MD)


@patch("scriptorium.publish.nlm")
def test_no_yes_no_stdin_exits_zero_without_remote_calls(mock_nlm, prior_published_review):
    root = prior_published_review
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err, stdin=io.StringIO(""))
    assert rc == 0
    mock_nlm.create_notebook.assert_not_called()


@patch("scriptorium.publish.nlm")
def test_yes_flag_bypasses_prompt(mock_nlm, prior_published_review):
    root = prior_published_review
    mock_nlm.doctor.return_value = NlmResult("", "", 0)
    mock_nlm.create_notebook.return_value = NotebookCreated(notebook_id="new", notebook_url="https://x", stdout="id: new\nurl: https://x")
    mock_nlm.upload_source.return_value = NlmResult("", "", 0)
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root), "--yes", "--json"], stdout=out, stderr=err)
    assert rc == 0
    mock_nlm.create_notebook.assert_called_once()


@patch("scriptorium.publish.nlm")
def test_yes_response_proceeds(mock_nlm, prior_published_review):
    root = prior_published_review
    mock_nlm.doctor.return_value = NlmResult("", "", 0)
    mock_nlm.create_notebook.return_value = NotebookCreated(notebook_id="new", notebook_url="https://x", stdout="id: new\nurl: https://x")
    mock_nlm.upload_source.return_value = NlmResult("", "", 0)
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root), "--json"], stdout=out, stderr=err, stdin=io.StringIO("y\n"))
    assert rc == 0
    mock_nlm.create_notebook.assert_called_once()
