---
description: Run the full scriptorium lit-review pipeline on a research question. Delegates to the running-lit-review skill which handles search → screen → extract → synthesize → contradiction-check → audit → optional publishing. Usage: /lit-review "your research question" [--review-dir <path>].
argument-hint: "<research question>" [--review-dir <path>]
---

## Preflight

Run `scriptorium version` first.

If that command fails or is not on PATH, stop and tell the user exactly:
`Scriptorium CLI is not on PATH. Run \`pipx install scriptorium-cli\`, restart Claude Code, then retry this command.`

Do not continue in degraded mode for this slash command.

# /lit-review

You are starting an end-to-end literature review for: **{{ARGS}}**

## Delegate to the skill

1. Activate `using-scriptorium` — it runs the runtime probe and loads the state-adapter vocabulary.
2. Activate `running-lit-review` with the research question above. The skill owns the full phase sequence (search → screen → extract → synthesize → contradiction-check → audit → optional publishing).
3. If the user passed `--review-dir <path>` in the arguments, thread it through `using-scriptorium`'s state-adapter resolution so every subsequent `scriptorium` CLI call inherits it.

Do not re-implement the pipeline here. The skill is the single source of truth so that Claude Code and Cowork execute the same review.

## v0.3 end-of-review steps

After cite-check passes and `contradictions.md` is written, run:

```bash
scriptorium regenerate-overview {{REVIEW_DIR}}
```

If `notebooklm_prompt` is not `false`, `notebooklm_enabled` is `true`, and
`nlm doctor` succeeds, show this prompt (skip is default):

```
NotebookLM artifact? (skip default)
  audio
  deck
  mindmap
  skip
```

Route non-`skip` selections to `scriptorium publish --review-dir <path>
--generate <audio|deck|mindmap>`.
