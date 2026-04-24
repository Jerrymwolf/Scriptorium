# Handoff — 2026-04-23 Clean Layout + Overview.docx

**Plan:** `plans/superpowers/2026-04-23-clean-layout-and-overview-docx.md`
**Branch:** `main`
**Env:** `.venv/bin/python` / `.venv/bin/pytest`

---

## Done (committed on `main`)

| Task | Commit | Summary |
|---|---|---|
| 1 | `d8a2cf5` + `b9c1ffc` | `ReviewPaths` hybrid layout (before this session) |
| 2 | `7416ce8` | `write_failed_draft` → `audit/overview-archive` |
| 3 | `2fd7d93` | `python-docx` dep + `scriptorium/export.py` scaffold |
| 4 | `abb14c3` | headings + paragraphs |
| 5 | `ac0744e` | bullet + ordered lists |
| 6 | `93aae59` | markdown tables |
| 7 | `55bcbbb` | inline bold/italic/code |
| 8 | `8a061d5` | citation enrichment (DOI → URL → stub → plain) |
| 9 | `338943f` | fence preservation + link-guard mask |
| 10 | `586d26a` | `OverviewDocxResult` (corpus_unavailable, citation_misses) |

**Test status:** 11 export tests green. Run with:
```bash
.venv/bin/python -m pytest tests/test_export_*.py tests/test_write_failed_draft_location.py -v
```

---

## Uncommitted work-in-progress

- `tests/test_overview_dual_write.py` — written, untracked. Test for Task 11.
  - Already adapted for real-world API mismatches (see Adaptations below).
- `scriptorium/overview/generator.py` — UNCHANGED beyond Task 2 commit. Still needs Task 11 wiring.

Run `git status` to confirm.

---

## Remaining tasks

### Task 11 — wire docx render into `regenerate_overview`

In `scriptorium/overview/generator.py`, after `paths.overview.write_text(text, encoding="utf-8")` (line 141), add:

```python
    import hashlib
    from scriptorium.export import render_overview_docx
    from scriptorium.storage.audit import append_audit, AuditEntry

    source_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    try:
        result = render_overview_docx(
            paths.overview, paths.overview_docx, paths.corpus
        )
        append_audit(paths, AuditEntry(
            phase="overview",
            action="overview_rendered",
            status="success",
            details={
                "wrote": ["overview.md", "overview.docx"],
                "source_sha256": source_sha,
                "citation_misses": result.citation_misses,
                "corpus_unavailable": result.corpus_unavailable,
            },
        ))
    except Exception as exc:
        append_audit(paths, AuditEntry(
            phase="overview",
            action="overview_docx_failed",
            status="failed",
            details={
                "wrote": ["overview.md"],
                "source_sha256": source_sha,
                "error": str(exc)[:200],
            },
        ))
```

Verify Task 11 `AuditStatus` accepts `"failed"` — look at `scriptorium/storage/audit.py` `_ALLOWED_STATUS` (top of file). If not, adjust to whatever the module allows (likely `"error"` or similar).

Run: `.venv/bin/python -m pytest tests/test_overview_dual_write.py -v`
Commit: `feat(overview): write overview.docx alongside .md, append audit event`

### Task 12 — failure-isolation test

Write `tests/test_overview_docx_failure_isolation.py` per plan, but adapt:
- Pass `model="m", seed=1` to `regenerate_overview`.
- Assert `e.get("action") == "overview_docx_failed"` (not `"event"`).
- Assert `"boom" in e["details"]["error"]`.

Should pass without code changes (Task 11's try/except handles it).

### Task 13 — docx-open smoke

`tests/test_overview_docx_opens.py` per plan. Put corpus at `tmp_path/data/corpus.jsonl` (layout compatibility — see Adaptations).

### Task 14 — docs

Per plan: `skills/generating-overview/SKILL.md`, `README.md`, `CHANGELOG.md`. No code changes.

### Task 15 — migrate `~/Desktop/values-review/`

**One-shot manual action.** Ask the user before running. Use the bash blocks from the plan. The `python -c` invocations at the end need `.venv/bin/python`.

---

## Key adaptations made (so fresh session doesn't re-discover)

1. **`papers_dir` derivation:** plan says `corpus_path.parent.parent / "sources" / "papers"`. This assumes corpus at `<root>/data/corpus.jsonl`. Original plan's citation tests put corpus at `tmp_path/corpus.jsonl` — I fixed the tests to use `tmp_path/data/corpus.jsonl` to match the real layout. **Keep this convention for Tasks 12–13.**

2. **Locator normalization:** plan test expects `[kim2022:p.9]` → `"(Kim 2022, p. 9)"` (note space). I added `_normalize_locator` in `scriptorium/export.py` (`p.N` → `p. N`, `pp.N` → `pp. N`).

3. **`regenerate_overview` signature:** requires keyword-only `model: str` and `seed: Optional[int]`. The plan's tests omit these. All new tests must pass them.

4. **`append_audit` API:** takes `AuditEntry(phase, action, status, details)`, not a plain dict. Plan's test assertion `e.get("event")` must become `e.get("action")`; `e["wrote"]` must become `e["details"]["wrote"]`. Already applied in `test_overview_dual_write.py`.

5. **Pre-existing test collection errors:** `tests/test_arxiv.py`, `test_e2e_caffeine.py`, `test_openalex.py`, `test_pmc.py`, `test_semantic_scholar.py`, `test_unpaywall.py` error on collection (likely missing `respx`/`pytest-asyncio`). **Unrelated to this work.** Don't block on them — run explicit file paths or `-k test_export`.

6. **Read-before-edit hook:** The session hook fires `READ-BEFORE-EDIT REMINDER` frequently but does not block. Edits succeed either way. Freshest-first: Read immediately before each Edit to silence it.

---

## How to resume

```bash
cd /Users/jeremiahwolf/Desktop/Projects/APPs/Scriptorium
git status                         # confirm untracked: test_overview_dual_write.py
git log --oneline -12               # last commit should be 586d26a
.venv/bin/python -m pytest tests/test_export_*.py -v  # sanity check: 11 green
```

Then resume at **Task 11** above.
