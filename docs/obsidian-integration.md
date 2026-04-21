# Obsidian integration (v0.3)

When `obsidian_vault` is set and a `.obsidian/` directory is found by the
vault-detection walk-up, Scriptorium writes paper stubs to
`<vault>/papers/` and the Dataview query file to
`<vault>/scriptorium-queries.md`. Review files live under
`<vault>/reviews/<slug>/`.

## Portability tradeoff

Vault-wide `papers/` stubs mean a vault-based review directory is **not self-contained** — the stubs it cites are elsewhere in the vault. If you
need a fully portable review folder, unset `obsidian_vault` when running
that review. `scriptorium export <review-dir>` (v0.4+) will bundle
referenced stubs into the review directory.

## Conflict copies

Dropbox-style `.obsidian (conflicted copy)` and `.obsidian 2` do not count
as vault markers on their own; when they coexist with a canonical
`.obsidian/` in the same directory, Scriptorium emits
`W_VAULT_CONFLICT_COPY` to the audit.
