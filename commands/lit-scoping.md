---
description: Scope a literature review before searching. Produces an approved scope.json that drives every downstream phase. Adaptive — vague prompts get many questions, precise prompts get a fast recap. Usage: /lit-scoping "your research direction" [--review-dir <path>] [--edit].
argument-hint: "<research direction>" [--review-dir <path>] [--edit]
---

## Preflight

Run `scriptorium version` first.

If that command fails or is not on PATH, stop and tell the user exactly:
`Scriptorium CLI is not on PATH. Run \`pipx install scriptorium-cli\`, restart Claude Code, then retry this command.`

Do not continue in degraded mode for this slash command.

# /lit-scoping

You are scoping a literature review for: **{{ARGS}}**

## Delegate to the skill

Invoke the `lit-scoping` skill with the user's prompt. If `--edit` was passed, load the existing scope.json and jump to the recap for revision rather than running inference fresh.
