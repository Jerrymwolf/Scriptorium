---
name: lit-publishing
description: Use after lit-synthesizing + lit-contradiction-check complete, when the user wants a podcast, slide deck, infographic, or video summary of the literature review. Drives NotebookLM Studio via MCP tools and records outputs in the audit trail.
---

# Literature Publishing

After the synthesis passes the cite-check and the contradiction check has been run, the review is ready for **publishing** — generating derivative artifacts for defense committees, coursework, or public outreach. NotebookLM Studio produces four artifact types; this skill drives them all through the NotebookLM MCP.

This skill is **Cowork-primary** (NotebookLM MCP is the only route) but also works in Claude Code sessions that have the `notebooklm-mcp` connector enabled.

## Prerequisites

- A NotebookLM notebook exists and contains the kept-paper PDFs as sources (added during `lit-extracting`).
- `synthesis.md` passes `scriptorium verify` (CC) or the in-skill cite-check (Cowork). If the synthesis has not passed verify, publishing is a discipline violation — ask the user to fix first.
- `lit-contradiction-check` has been run; contradictions are captured in the synthesis.

## Artifact types

| Type | `studio_create(artifact_type=...)` | Output | Typical use |
|---|---|---|---|
| Podcast / audio overview | `"audio"` | 8–20 min two-host discussion (mp3) | Listen-while-walking review of the field |
| Slide deck | `"slides"` | Google Slides (shareable link) | Committee meeting / defense rehearsal |
| Infographic | `"infographic"` | Single-page PNG | Thesis appendix, poster section |
| Video overview | `"video"` | short video | Outreach / lab meeting |

## Workflow

1. **Ask the user which artifacts they want.** Default to "just audio" — it is the cheapest and most distinctive NotebookLM output. Tell the user the cost order before they commit: **audio < infographic < slides < video**.
2. **For each artifact:**
   ```
   mcp__notebooklm-mcp__studio_create(
     notebook_id="<notebook-id-from-state-adapter>",
     artifact_type="audio",           # or slides/infographic/video
     custom_instructions="<1-2 sentence framing>",
   )
   ```
   This kicks off an async generation job and returns a job id.
3. **Poll for completion:**
   ```
   mcp__notebooklm-mcp__studio_status(job_id=<id>)
   ```
   Keep polling every ~30s until `status == "complete"`.
4. **Download the artifact:**
   ```
   mcp__notebooklm-mcp__download_artifact(artifact_type="audio", job_id=<id>)
   ```
5. **Append an audit entry per artifact:**
   ```
   scriptorium audit append --phase publishing --action studio.created \
     --details '{"artifact_type":"audio","path":"<path>","job_id":"<id>"}'
   ```
   In Cowork, write the equivalent JSON line to the `audit-jsonl` note.

## Quota note

NotebookLM Studio generations are quota-metered on Google's side. Tell the user the cost order (audio < infographic < slides < video) before creating more than one or two per session. If a `studio_create` call fails with a quota error, surface the message verbatim and stop — do not retry silently.

## Failure modes

- **Notebook has no sources.** Studio refuses to generate; re-check that `lit-extracting` added the PDFs.
- **Synthesis is unsupported.** Publishing a synthesis that failed `verify` is a discipline violation — offer the user one chance to accept it ("I know — publish anyway"), but default to blocking.
- **Quota exceeded.** Stop, audit the failure, tell the user which artifact types were generated before the cutoff.

## Hand-off

After every requested artifact is downloaded (or its job id recorded for async fetch), hand control back to the user with a list: "Generated: audio at `<path>`. Audit log updated. Anything else?"
