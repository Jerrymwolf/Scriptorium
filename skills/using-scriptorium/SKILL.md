---
name: using-scriptorium
description: Use when the user mentions a literature review, asks to find/screen/synthesize research, or starts a new review session. Probes the runtime (Claude Code vs Cowork), teaches the three disciplines, and dispatches to the phase-appropriate lit-* skill.
---

# Using Scriptorium

**Fire this first in every Scriptorium session.** It is the router. After you've probed the runtime and chosen state, hand off to the skill that matches the user's current phase.

## The three disciplines (non-negotiable)

1. **Evidence-first claims.** Every sentence in `synthesis.md` either cites `[paper_id:locator]` that exists in the evidence store, or it is stripped/flagged. There is no rhetorical-but-uncited writing.
2. **PRISMA audit trail.** Every search, screen, extraction, and reasoning decision appends one entry to the audit trail. Entries never overwrite; the trail is reconstructable.
3. **Contradiction surfacing.** When evidence on the same concept points in different directions, name the disagreement explicitly. Do not average away conflict.

## Runtime capability truth table

| Surface | Claude Code | Cowork |
|---|---|---|
| Skills (SKILL.md + description match) | ✓ | ✓ (only portable surface) |
| Slash commands (`/lit-review`) | ✓ | ✗ — natural-language fires skill |
| PostToolUse hooks | ✓ | ✗ — skill enforces the rule |
| Bash / local CLI | ✓ | ✗ |
| Local filesystem (cwd = review dir) | ✓ | ✗ — ephemeral sandbox |
| Search sources | `scriptorium` CLI + WebFetch | Consensus · Scholar Gateway · PubMed MCPs |
| State home | disk | NotebookLM → Drive → Notion → session-only |
| Full-text retrieval | Unpaywall, arXiv, PMC, user PDFs | PubMed `get_full_text_article` + user uploads; no Unpaywall/arXiv |

## Runtime probe (run at session start)

Check tool availability in this order and set session-state variables `RUNTIME` (`cc` or `cowork`), `SEARCH_TOOLS`, and `STATE_BACKEND`:

- `Bash` present AND `scriptorium --version` exits 0 → **CC-mode**; use the CLI path for search/verify/corpus/evidence/audit.
- `mcp__claude_ai_Consensus__search` present → Consensus available for search.
- `mcp__claude_ai_Scholar_Gateway__semanticSearch` present → Scholar Gateway available.
- `mcp__claude_ai_PubMed__search_articles` present → PubMed available (biomed search + full text).
- `mcp__notebooklm-mcp__notebook_create` present → NotebookLM available for state + publishing.
- `mcp__claude_ai_Google_Drive__authenticate` present → Drive available for state fallback.
- `mcp__claude_ai_Notion__authenticate` present → Notion available for state (stretch).
- If neither Bash nor any `mcp__claude_ai_*__search` tool is present → minimum degraded mode: use WebFetch against the OpenAlex API directly and warn the user that no platform MCPs are available.

In Cowork, pick the **first available** state backend in this order: NotebookLM > Drive > Notion > session-only. In CC, state is always the filesystem.

## State-adapter mapping (reference for every downstream skill)

Concept → CC path → Cowork NotebookLM → Cowork Drive → Cowork Notion

- review root → `cwd` → one notebook → one folder → one page
- `corpus.jsonl` → file → note titled `corpus` → `corpus.jsonl` file → child page `Corpus`
- `evidence.jsonl` → file → note titled `evidence` → `evidence.jsonl` file → child page `Evidence`
- `audit.md` + `audit.jsonl` → files → notes titled `audit-md`/`audit-jsonl` → files → child page `Audit`
- `synthesis.md` → file → note titled `synthesis` → `synthesis.md` file → child page `Synthesis`
- PDFs → `pdfs/` dir → notebook sources (native) → `pdfs/` subfolder → uploaded attachments

Every skill that reads/writes state calls through this mapping — skills never hardcode a filesystem path.

## When to fire which skill

| Phase | User says… | Skill to fire |
|---|---|---|
| Search | "find papers on X", "search for …" | `lit-searching` |
| Screen | "filter by year/language/keyword", "apply inclusion criteria" | `lit-screening` |
| Extract | "pull full text", "extract methods/findings from this PDF" | `lit-extracting` |
| Synthesize | "write the literature review section", "draft a synthesis" | `lit-synthesizing` |
| Contradict | "where do papers disagree?", "find contradictions" | `lit-contradiction-check` |
| Audit | "show the audit trail", "export PRISMA diagram" | `lit-audit-trail` |
| Publish | "make a podcast/slides/infographic of this" | `lit-publishing` |
| Orchestrate | "run a literature review on X (end-to-end)" | `running-lit-review` |

Scoping (phase 1) and final writing (phases 7+) stay with the student — Scriptorium covers phases 2–6.

## Unified JSON shapes (both runtimes agree on these)

- **Paper:** `{paper_id, source, title, authors[], year, doi, abstract, venue, open_access_url}`
- **EvidenceEntry:** `{paper_id, locator, claim, quote, direction: positive|negative|neutral|mixed, concept}`
- **AuditEntry:** `{phase, action, details{}, ts}`

CC enforces these via dataclasses in the CLI (`scriptorium evidence add` accepts named flags); Cowork enforces them via skill prose with worked examples.

## First-run checklist

1. Announce: "Using `using-scriptorium` to route this session."
2. Run the probe, record `RUNTIME` + `STATE_BACKEND`.
3. Brief the user in one sentence: "CC mode — using the `scriptorium` CLI and the filesystem at `<cwd>`." *or* "Cowork mode — using Consensus + PubMed for search, NotebookLM notebook `<id>` for state."
4. Ask for the research question if they haven't provided one.
5. Hand off to the phase-appropriate skill.

## v0.3 additions

- Setting `obsidian_vault` enables native Obsidian output: paper stubs to `<vault>/papers/`, Dataview queries to `<vault>/scriptorium-queries.md`.
- Publishing route is `scriptorium publish --review-dir <path> --generate <audio|deck|mindmap|video|all>`.
- Cowork degradation block is rendered automatically when `SCRIPTORIUM_COWORK` is set.
