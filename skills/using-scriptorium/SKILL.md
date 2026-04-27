---
name: using-scriptorium
description: Use when the user mentions a literature review, asks to find/screen/synthesize research, or starts a new review session. The router. Probes the runtime (Claude Code vs Cowork), names degraded modes honestly, and dispatches to the phase-appropriate lit-* skill.
---

# Using Scriptorium

**Fire this first in every Scriptorium session.** It is the router. The first branch of this skill is runtime detection — not skill routing, not state setup, not discipline reminders. Detect the runtime, name what is and isn't available, then hand off.

The discipline contract (evidence-first claims, PRISMA audit trail, contradiction surfacing) lives in the sibling file `INJECTION.md`. Both runtimes inject it at session start: Claude Code via the `SessionStart` hook, Cowork via the MCP server's `instructions` payload. This SKILL.md does not duplicate that text — it points to it and enforces routing.

## Step 1: Runtime detection (run first — do not skip)

This is the **first branch** of every Scriptorium session. Probe before you do anything else. Set three session-state variables — `RUNTIME`, `STATE_BACKEND`, `SEARCH_TOOLS` — and announce them to the user in one sentence before handing off.

Do **not** infer the runtime from filenames, the user's phrasing, or prior sessions. Probe explicitly with the checks below.

### Probes (in order)

1. **`Bash` tool present AND `scriptorium version` exits 0** → set `RUNTIME=cc`. The `scriptorium` CLI is on PATH; the filesystem is the state home; PostToolUse hooks are live.
2. **`Bash` tool present BUT `scriptorium version` fails or is not on PATH** → set `RUNTIME=cc` with the **CLI missing** flag (see Degraded modes below). Do not fall through to Cowork — Bash availability proves you are in CC.
3. **No `Bash` tool, but at least one `mcp__claude_ai_*` tool present** → set `RUNTIME=cowork`. The filesystem is ephemeral; state lives in a platform backend.
4. **Neither `Bash` nor any `mcp__claude_ai_*` tool present** → degraded floor; set `RUNTIME=cowork`, `SEARCH_TOOLS=webfetch`, `STATE_BACKEND=session-only`. Tell the user explicitly that this is the minimum-degraded path before continuing.

### Inside Cowork — pick search tools

Check tool availability and set `SEARCH_TOOLS` to the list of what's present:

- `mcp__claude_ai_Consensus__search` → Consensus available.
- `mcp__claude_ai_Scholar_Gateway__semanticSearch` → Scholar Gateway available.
- `mcp__claude_ai_PubMed__search_articles` → PubMed available (biomed search + full text via `mcp__claude_ai_PubMed__get_full_text_article`).

If none of those three are present, set `SEARCH_TOOLS=webfetch` and treat as **no platform search** (see Degraded modes).

### Inside Cowork — pick a state backend

Check tool availability in this order; pick the **first** available and set `STATE_BACKEND` accordingly:

- `mcp__notebooklm-mcp__notebook_create` → `STATE_BACKEND=notebooklm`.
- `mcp__claude_ai_Google_Drive__authenticate` → `STATE_BACKEND=drive`.
- `mcp__claude_ai_Notion__authenticate` → `STATE_BACKEND=notion`.
- None of the above → `STATE_BACKEND=session-only` (see Degraded modes).

In CC, `STATE_BACKEND=disk` always; the review root is `cwd`.

### Announce

After probing, brief the user in one sentence so they know what mode you're in:

- "CC mode — using the `scriptorium` CLI and the filesystem at `<cwd>`." *or*
- "Cowork mode — search via `<SEARCH_TOOLS>`, state in `<STATE_BACKEND>` notebook `<id>`."

If any degraded condition fired, name it in that same announcement. Never start the review without telling the user which mode they're in.

## Step 2: Capability truth table

Reference for every downstream skill — what each runtime offers natively.

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

## Step 3: Degraded modes — name them honestly

When a probe leaves you without an expected capability, **you are in degraded mode**. Each degraded mode has a name. Use the name with the user — do not silently downgrade. Say `⚠ <degraded-mode>: <what is lost>` in the same breath as the runtime announcement.

| Degraded mode | When it fires | What is lost | What to tell the user |
|---|---|---|---|
| **CLI missing** in CC | `RUNTIME=cc` but `scriptorium version` fails | Slash commands (`/lit-review`, `/lit-config`), PostToolUse cite-check, every `scriptorium *` step in downstream skills | ⚠ tell the user: "The `scriptorium` CLI is not on PATH. Run `pipx install scriptorium-cli`, restart Claude Code, then retry." Stop — do not fall back. |
| **session-only state** in Cowork | `RUNTIME=cowork` and no NotebookLM / Drive / Notion backend | All review state — `corpus.jsonl`, `evidence.jsonl`, `audit.jsonl`, `synthesis.md` — vanishes when the conversation ends | ⚠ warn the user: "session-only state — nothing persists past this conversation. Authenticate NotebookLM, Drive, or Notion before doing real work, or accept that the review is throwaway." |
| **no platform search** | Cowork without Consensus, Scholar Gateway, **and** PubMed | Citation-grade search; falls back to WebFetch against OpenAlex with no relevance ranking, no abstract dedup, no platform citations | ⚠ warn the user: "no platform search — falling back to WebFetch against OpenAlex. Coverage is reduced and ranking is naive. Authenticate at least one of Consensus / Scholar Gateway / PubMed before promising a comprehensive review." |
| **no full-text retrieval available** | Neither Unpaywall (CC) nor PubMed `get_full_text_article` (Cowork) reachable, and the user has uploaded no PDFs | Extraction phase has nothing to read; only abstracts and titles are extractable | ⚠ tell the user: "no full-text retrieval available — extraction will be limited to abstracts unless you upload PDFs. Upload them now or expect a thinner evidence base." |

These names are load-bearing. Use them verbatim in the announcement so the user (and any reviewer reading transcripts) can grep degraded sessions. **Do not proceed silently in any degraded mode.**

## The three disciplines (non-negotiable)

These are restated here as a routing reminder. The canonical, imperative wording — and the red-flag list — lives in `INJECTION.md`, which both runtimes inject at session start. Read it; do not paraphrase it away.

1. **Evidence-first claims.** Every sentence in `synthesis.md` either cites `[paper_id:locator]` that exists in the evidence store, or it is stripped/flagged. There is no rhetorical-but-uncited writing.
2. **PRISMA audit trail.** Every search, screen, extraction, and reasoning decision appends one entry to the audit trail. Entries never overwrite; the trail is reconstructable.
3. **Contradiction surfacing.** When evidence on the same concept points in different directions, name the disagreement explicitly. Do not average away conflict.

## State-adapter mapping (reference for every downstream skill)

Concept → CC path → Cowork NotebookLM → Cowork Drive → Cowork Notion

- review root → `cwd` → one notebook → one folder → one page
- `corpus.jsonl` → file → note titled `corpus` → `corpus.jsonl` file → child page `Corpus`
- `evidence.jsonl` → file → note titled `evidence` → `evidence.jsonl` file → child page `Evidence`
- `audit.md` + `audit.jsonl` → files → notes titled `audit-md`/`audit-jsonl` → files → child page `Audit`
- `synthesis.md` → file → note titled `synthesis` → `synthesis.md` file → child page `Synthesis`
- PDFs → `pdfs/` dir → notebook sources (native) → `pdfs/` subfolder → uploaded attachments

Every skill that reads/writes state calls through this mapping — skills never hardcode a filesystem path.

## Step 4: Dispatch to the phase-appropriate skill

After the probe completes and the announcement is made, hand off. Match the user's phrasing (or the phase they're already in) to one of these skills.

| Phase | User says… | Skill to fire |
|---|---|---|
| Scope (phase 1) | "I want to review the literature on X", "help me set up a review" | `lit-scoping` |
| Search | "find papers on X", "search for …" | `lit-searching` |
| Screen | "filter by year/language/keyword", "apply inclusion criteria" | `lit-screening` |
| Extract | "pull full text", "extract methods/findings from this PDF" | `lit-extracting` |
| Synthesize | "write the literature review section", "draft a synthesis" | `lit-synthesizing` |
| Contradict | "where do papers disagree?", "find contradictions" | `lit-contradiction-check` |
| Audit | "show the audit trail", "export PRISMA diagram" | `lit-audit-trail` |
| Publish | "make a podcast/slides/infographic of this" | `publishing-to-notebooklm` |
| Orchestrate end-to-end | "run a literature review on X (start to finish)" | `running-lit-review` |

Final-paper writing (phases 7+) stays with the student — Scriptorium covers phases 2–6 plus optional publishing.

If the user has not yet scoped the review, fire `lit-scoping` first to produce the `scope.json` artifact. Do not ask scoping questions directly from this skill — the scoping conversation is owned by `lit-scoping`.

## Unified JSON shapes (both runtimes agree on these)

- **Paper:** `{paper_id, source, title, authors[], year, doi, abstract, venue, open_access_url}`
- **EvidenceEntry:** `{paper_id, locator, claim, quote, direction: positive|negative|neutral|mixed, concept}`
- **AuditEntry:** `{phase, action, details{}, ts}`

CC enforces these via dataclasses in the CLI (`scriptorium evidence add` accepts named flags); Cowork enforces them via skill prose with worked examples.

## First-run checklist

1. Announce: "Using `using-scriptorium` to route this session."
2. **Run Step 1** — probe the runtime, set `RUNTIME` / `STATE_BACKEND` / `SEARCH_TOOLS`.
3. Brief the user in one sentence (per the Announce rule above). Name any degraded modes with the `⚠` prefix.
4. If the user has not yet scoped the review, fire `lit-scoping` to produce the `scope.json` artifact.
5. Hand off to the phase-appropriate skill from the dispatch table.

## v0.3 additions

- Setting `obsidian_vault` enables native Obsidian output: paper stubs to `<vault>/papers/`, Dataview queries to `<vault>/scriptorium-queries.md`.
- Publishing route is `scriptorium publish --review-dir <path> --generate <audio|deck|mindmap|video|all>` (CC) or the `publishing-to-notebooklm` skill (Cowork).
- Cowork degradation block is rendered automatically when `SCRIPTORIUM_COWORK` is set.
