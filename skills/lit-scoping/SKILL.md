---
name: lit-scoping
description: Use when the user asks to scope, frame, or plan a literature review before searching begins, OR when invoked by running-lit-review, OR when lit-searching finds no scope.json. Produces an approved scope.json artifact that drives every downstream phase. Adaptive: vague prompts get many questions, precise prompts skip straight to a recap.
---

# Literature Scoping

The goal of this skill is a single artifact: a **user-approved `scope.json`** that every downstream skill reads. Running this skill is the only legitimate way to produce that artifact.

**Fire `using-scriptorium` first.** The runtime probe must have run before you continue — scope.json persistence differs between Claude Code and Cowork.

## The three disciplines

1. **Adaptive depth** — ask only what the initial prompt has not already resolved.
2. **Recap + approval gate** — never proceed to search without an explicit user approval of a structured recap.
3. **Audit trail** — on approval, append one `scope_approved` entry to `audit.jsonl`.

---

## Step 1 — Runtime probe and existing-scope check

If `scope.json` already exists in the review root:

```
An existing scope.json was found (created <ts>).
  1. Resume with this scope and proceed to search
  2. Review and edit this scope
  3. Discard and start fresh
```

- Option 1: load the scope, skip to Step 6 (approval recap for one-click confirm).
- Option 2: load the scope, treat all present fields as resolved, jump to Step 5 (recap) for editing.
- Option 3: delete scope.json, continue to Step 2.

If no scope.json exists, continue.

## Step 2 — Inference pass

Parse the user's initial prompt. For each dimension below, mark it **resolved** only if the signal is unambiguous. When in doubt, leave it unresolved.

| Dimension | Signal to look for |
|---|---|
| research_question | Interrogative or declarative topic statement |
| purpose | Keywords: dissertation, grant, chapter, systematic, scoping, overview |
| fields | Named disciplines, theory→field mappings (SDT → psychology) |
| population | PICO-style noun phrases ("adolescents", "remote workers") |
| methodology | "RCTs", "qualitative", "ethnographies", "mixed methods" |
| year_range | Explicit years or relative phrases ("last 5 years", "since 2015") |
| corpus_target | Numbers with paper/study ("~30 papers", "a dozen") |
| publication_types | "peer-reviewed", "preprints", "grey literature", "dissertations" |
| depth | "systematic", "exhaustive", "representative", "canonical" |
| conceptual_frame | Named theories, lenses, construct sets |
| anchor_papers | DOIs, author-year citations |

## Step 3 — Vagueness check

Count resolved Tier 1+2 dimensions (research_question, purpose, fields, population, methodology, year_range, corpus_target, publication_types, depth).

- **< 4 resolved:** prompt is vague → Tier 2 asks all its unresolved dimensions.
- **4–8 resolved:** semi-specified → Tier 2 asks only gaps.
- **9+ resolved:** precise → skip Tier 2, go to Step 5 (Tier 3 offer).

## Step 4 — Tiered questioning

### Tier 1 — Required (always, for any unresolved)

Ask one question at a time. Never batch.

- **Research question:** "What specific question are you trying to answer with this review?"
- **Purpose:** "What is this review for? Choose one: dissertation chapter, grant proposal, narrative overview, systematic review, scoping review."
- **Disciplinary home:** "Which field(s) should the search cover? (e.g., psychology, education, clinical medicine)"

### Tier 2 — Contextual (when prompt is vague, or for unresolved gaps)

Ask one at a time, in this order:

- **Population:** "Who or what do the papers need to be about? (e.g., adolescents, remote workers, RCTs in oncology)"
- **Methodology:** "What study methodology? Choose: any, qualitative, quantitative, RCT, mixed."
- **Year range:** "What year range? (default: last 10 years; say 'no restriction' if you want all years)"
- **Corpus target:** "How many papers are you aiming for? (25 / 50 / 100 / exhaustive)"
- **Publication types:** "Which sources count? Choose any of: peer-reviewed, preprints, grey literature, dissertations."
- **Depth:** "Do you want an exhaustive search or a representative sample?"

### Tier 3 — Advanced (always offered as a single menu)

After Tier 1+2 complete, present this exact menu:

```
Want to go deeper? I can also ask about:
  A. Conceptual frame — the theories or constructs you're working within
  B. Prior anchors — papers/authors you already trust
  C. Output intent — what you're producing (chapter, podcast, deck, export)
  D. Known gaps — are you trying to surface thin or absent areas?
  E. Research paradigm — positivist, interpretivist, critical, pragmatist

Type letters to add questions, or 'skip'.
```

For each selected letter, ask the corresponding question one at a time.

## Step 5 — Contradiction check

Before rendering the recap, scan the resolved set for these soft warnings:

| Condition | Warning |
|---|---|
| `purpose=systematic` AND `depth=representative` | "Systematic reviews typically require exhaustive retrieval — confirm or revise depth." |
| `purpose=systematic` AND `corpus_target` is a number < 25 | "Systematic reviews typically retrieve all eligible papers — a hard cap may not be appropriate." |
| `methodology=RCT` AND no medicine/psychology/education in fields | "RCTs are uncommon outside medicine/psych/education — confirm or broaden." |
| `publication_types=[preprints]` only AND `purpose=dissertation` | "Dissertations usually require peer-reviewed sources — confirm or broaden." |
| `depth=exhaustive` AND `corpus_target` is a number | "Exhaustive retrieval and a numeric target can conflict — clarify which governs." |

Warnings are **not blocking**. They go into the recap under "Soft warnings" and are persisted in `scope.json`'s `soft_warnings` array.

## Step 6 — Recap and approval

Render the recap exactly in this shape:

```
📋 Scoping recap — please review

Research question: <value>
Purpose:           <value>
Field(s):          <comma-joined>
Population:        <value or "not specified">
Methodology:       <value>
Year range:        <YYYY–YYYY or "no restriction">
Corpus target:     <value>
Publication types: <comma-joined>
Depth:             <exhaustive | representative>

Tier 3 (advanced):
<only resolved Tier 3 dims>

⚠ Soft warnings:
<one per line, or "None.">

Approve and proceed to search? (approve / revise <dimension> / start over)
```

Handle user responses:
- **approve** → proceed to Step 7.
- **revise <dim>** → re-ask that dimension only, re-render the recap.
- **start over** → clear resolved state, go to Step 2.

If 3 revision cycles pass without approval, proactively offer: "Want to start over with a fresh prompt?"

If the user types gibberish, re-render the approval prompt verbatim.

## Step 7 — Persist and hand off

### Claude Code path

1. Build the scope object matching the v1 schema.
2. Write it via:
   ```
   Write tool → <review_root>/scope.json
   ```
3. Validate by running:
   ```
   scriptorium verify --scope <review_root>/scope.json
   ```
   Exit 0 is required; exit 3 means the scope is malformed — report the error and re-enter revision.
4. Append the audit entry:
   ```
   scriptorium audit append --phase scoping --action scope_approved \
     --details '{"scope_version": 1, "dimensions_resolved_via_inference": [...], "dimensions_resolved_via_question": [...], "tier3_dimensions_selected": [...], "soft_warnings_acknowledged": [...], "revision_cycles": <n>}'
   ```

### Cowork path

1. Build the scope object in memory.
2. Add a header to the recap: "Running in Cowork — scope will not persist beyond this session. Export before closing."
3. Append the audit entry via the state adapter's `audit.jsonl` note.
4. Pass the scope object directly to `lit-searching` when handing off.

## Step 8 — Return to caller

Tell the user: "Scope approved and saved. Handing off to `lit-searching`." Then invoke `lit-searching`.

If running standalone via `/scriptorium:lit-scoping`, stop here and report the scope.json path.

---

## Performance targets

- Vague prompt → approval in ≤ 12 user messages (2–3 minutes).
- Semi-specified → ≤ 6 messages (45–90 seconds).
- Precise → ≤ 2 messages (< 30 seconds).

If you exceed 15 messages without approval, something is wrong — proactively offer "start over".

## What you must never do

- Never proceed to search without an approved `scope.json` / in-memory scope object.
- Never silently fill a resolved dimension the user did not confirm.
- Never treat contradictions as blockers — surface them, let the user decide.
- Never skip the audit append on approval.
- Never write `scope.json` without running `scriptorium verify --scope` first in CC.
