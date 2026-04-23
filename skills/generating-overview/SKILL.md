---
name: generating-overview
description: Produce `overview.md` — the executive briefing for a completed Scriptorium review (§8).
---

# generating-overview

Use this skill after cite-check passes and `synthesis.md` +
`contradictions.md` are final. It produces the corpus-bounded briefing
`overview.md` and hands control to `scriptorium regenerate-overview` for
persistence and archival.

## Nine sections, exactly this order (nine sections total)

1. **TL;DR**
2. **Scope & exclusions**
3. **Most-cited works in this corpus**
4. **Current findings**
5. **Contradictions in brief**
6. **Recent work in this corpus (last 5 years)**
7. **Methods represented in this corpus**
8. **Gaps in this corpus**
9. **Reading list**

Every section title is corpus-bounded. Do not rename to field-level
language ("most important works", "research gaps", etc.).

## Two sentence classes

| Class | Required marker |
|---|---|
| Paper claim (quoted or paraphrased) | `[[paper_id#p-N]]` locator |
| Synthesis / ranking / framing | Inline `<!-- synthesis -->` and no locator |

Lint fails closed: a paper claim without a locator, or a synthesis sentence
with a locator, is rejected.

## Provenance block per section

Each section ends with:

```html
<!-- provenance:
  section: most-cited-works
  contributing_papers: [nehlig2010, smith2018]
  derived_from: synthesis.md#current-findings
  generation_timestamp: 2026-04-20T14:32:08Z
-->
```

Required keys: `section`, `contributing_papers`, `derived_from`,
`generation_timestamp`.

## Persist with the CLI

```bash
scriptorium regenerate-overview <review-dir> [--model <name>] [--seed <int>] [--json]
```

Archive-on-regenerate writes previous drafts to
`<review-dir>/audit/overview-archive/<timestamp>.md`. On lint/cite-check
failure, the failed draft goes to
`<review-dir>/audit/overview-archive/overview.failed.<timestamp>.md` and
the command exits `E_OVERVIEW_FAILED`.

**Word export:** the overview is written as both `overview.md` and
`overview.docx`. The Word document is regenerated from the markdown every
run — it's a derivative, not a source. Edit `overview.md`; `overview.docx`
will refresh next time. `[paper_id:locator]` citations resolve to
`(Author Year, locator)` with a DOI → URL → local-stub hyperlink (in that
precedence order). Docx render is best-effort: failure emits an
`overview_docx_failed` audit event but never blocks the `.md` write.

Length target is 300 words. The lint warns above 400 words but does not
fail on length alone.
