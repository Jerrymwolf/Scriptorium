---
description: Export the kept-papers corpus to BibTeX and RIS under <review-dir>/bib/. Runs `scriptorium bib --format bibtex` and `scriptorium bib --format ris`, writes each to disk, and appends an audit entry. Usage: /lit-export-bib [--review-dir <path>].
argument-hint: "[--review-dir <path>]"
---

# /lit-export-bib

## Procedure

1. Resolve the review-dir (default `cwd`; honor `--review-dir` if provided). The output directory is `<review-dir>/bib/`; create it if absent.
2. Export BibTeX:
   ```
   scriptorium bib --format bibtex > <review-dir>/bib/references.bib
   ```
3. Export RIS:
   ```
   scriptorium bib --format ris > <review-dir>/bib/references.ris
   ```
4. Count the entries (number of `@` headers in the BibTeX output) and append an audit entry:
   ```
   scriptorium audit append --phase export --action bib.write --details '{"format":"bibtex+ris","path":"bib/","n_papers":<count>}'
   ```
5. Tell the user the two file paths and the count.
