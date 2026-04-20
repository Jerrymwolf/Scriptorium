---
description: Register a user-supplied PDF into the current review's pdfs/ cache and link it to a paper_id. Writes the PDF via `scriptorium register-pdf` and appends an audit entry. Usage: /lit-add-pdf <path> --paper-id <id> [--review-dir <path>].
argument-hint: <pdf-path> --paper-id <id> [--review-dir <path>]
---

# /lit-add-pdf

Args: **{{ARGS}}**

## Procedure

1. Parse the path (required), `--paper-id` (required), optional `--review-dir`.
2. If `--paper-id` is missing, search `scriptorium corpus list` for a paper whose title best matches the PDF filename. Show the best match and ask the user to confirm. If no good match, ask which `paper_id` to use.
3. Invoke:
   ```
   scriptorium register-pdf --pdf <path> --paper-id <id>
   ```
   (Add `--review-dir <path>` if the user passed it.)
4. Append an audit entry:
   ```
   scriptorium audit append --phase extraction --action user_pdf.register --details '{"paper_id":"<id>","src":"<original-path>"}'
   ```
5. Tell the user the cached-file path reported by step 3 and that the next `scriptorium fetch-fulltext --paper-id <id>` run will pick up the registered PDF first.
