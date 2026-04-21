# Scriptorium Install Fix — Design Spec

**Date:** 2026-04-20
**Target version:** 0.3.1
**Status:** Approved for implementation

## Problem

New users following the README cannot install Scriptorium into Claude Code. After `pip install -e .` and `./scripts/install_plugin.sh`, restart, and running `/lit-config`, the slash commands do not appear. Install appears to succeed; silently does nothing.

## Root Cause — Two Compounding Bugs

1. **Layout bug.** `commands/`, `skills/`, and `hooks/` live inside `.claude-plugin/`. Claude Code scans them at the plugin root. Verified against working plugins:
   - `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.0.6/` — surfaces at root, only `plugin.json` and `marketplace.json` in `.claude-plugin/`
   - `~/.claude/plugins/cache/openai-codex/codex/1.0.1/` — same pattern
   The repo even self-documents the wrong layout in `.claude-plugin/CLAUDE.md:17-22`.

2. **No marketplace manifest.** Only `.claude-plugin/plugin.json` exists. `/plugin install` from GitHub cannot discover the plugin. The README workaround (`scripts/install_plugin.sh`) symlinks into `~/.claude/plugins/scriptorium` — a path modern Claude Code ignores. It scans `plugins/cache/<marketplace>/<plugin>/<version>/` registered in `installed_plugins.json`.

## Target Install UX

```bash
pipx install scriptorium-cli
```

Then in Claude Code:

```
/plugin marketplace add Jerrymwolf/Scriptorium
/plugin install scriptorium@scriptorium-local
/lit-config
```

Two shell lines. Two Claude Code lines. No clone. No symlink. No manual copy.

## Plan (15 Steps, Ordered)

### 1. Move the plugin surface to plugin root

```bash
git mv .claude-plugin/commands commands
git mv .claude-plugin/skills skills
git mv .claude-plugin/hooks hooks
git mv .claude-plugin/CLAUDE.md CLAUDE.md
```

Leave `.claude-plugin/plugin.json` in place. No duplicate directories.

### 2. Add `.claude-plugin/marketplace.json`

Name must match the target install command exactly:

```json
{
  "name": "scriptorium-local",
  "plugins": [
    {
      "name": "scriptorium",
      "version": "0.3.1",
      "source": "./"
    }
  ]
}
```

### 3. Update `.claude-plugin/plugin.json` version only

Keep plugin name `scriptorium`. Set `"version": "0.3.1"`.

### 4. Keep packaging identity stable

`pyproject.toml` is already correct on install-critical keys:
- `project.name = "scriptorium-cli"` (line 6)
- `build-backend = "setuptools.build_meta"` (line 3)
- `project.scripts.scriptorium = "scriptorium.cli:main"` (lines 22–23)
- Package discovery `include = ["scriptorium*"]` (lines 25–26)

Required deltas only:

```toml
[project]
version = "0.3.1"
readme = "README.md"
authors = [{ name = "Jeremiah Wolf", email = "jeremiahmwolf@gmail.com" }]
```

**Do not** rename the distribution. **Do not** change the console script. **Do not** touch package discovery.

### 5. Bump every user-visible and generated version string to `0.3.1`

Files with hardcoded `0.3.0`:

- `pyproject.toml`
- `.claude-plugin/plugin.json`
- `scriptorium/__init__.py`
- `scriptorium/setup_flow.py`
- `scriptorium/migrate.py`
- `scriptorium/overview/generator.py`
- `scriptorium/obsidian/stubs.py`
- `README.md`
- `.claude-plugin/commands/scriptorium-setup.md` (will be at `commands/scriptorium-setup.md` after step 1)
- `skills/setting-up-scriptorium/SKILL.md`
- `tests/test_version_v03.py`

### 6. Delete the legacy installer and every reference

- Remove `scripts/install_plugin.sh`
- Scrub README references at `README.md:143-145` and `README.md:328-333`
- Update test expectations in `tests/test_readme.py:31-35,69-72` and `tests/test_release_artifacts.py:6-20`
- Remove any docs or skills still telling users to copy `.claude-plugin/` manually

### 7. Rewrite README install section

Replace the Claude Code install block with:

````md
```bash
pipx install scriptorium-cli
```

In Claude Code:

```
/plugin marketplace add Jerrymwolf/Scriptorium
/plugin install scriptorium@scriptorium-local
/lit-config
```

Then: `/lit-review "your research question" --review-dir reviews/<slug>`.
````

Delete `README.md:323` ("not yet on PyPI") — becomes false after publish.

### 8. Stop pretending `/scriptorium-setup` is the first-install path

The command and skill currently say "Install `.claude-plugin/`", but `scriptorium/setup_flow.py:70-95` doesn't install anything — just marks steps complete. Rewrite:

- `commands/scriptorium-setup.md`
- `skills/setting-up-scriptorium/SKILL.md`

As **post-install configuration only**: verify `scriptorium --version`, collect `unpaywall_email`, set `obsidian_vault`, optionally set up `notebooklm-mcp-cli`. Remove every instruction to install the plugin from inside the plugin.

### 9. Add hard preflight to CLI-dependent slash commands

The `using-scriptorium` skill already uses `scriptorium --version` as the CC-mode probe (`skills/using-scriptorium/SKILL.md:29-42`). Without a hard stop when CLI is missing, commands fall into a degraded runtime path.

Insert at the top of `commands/lit-config.md` and `commands/lit-review.md`, mirror in `skills/using-scriptorium/SKILL.md`:

````md
## Preflight

Run `scriptorium --version` first.

If that command fails or is not on PATH, stop and tell the user exactly:
`Scriptorium CLI is not on PATH. Run \`pipx install scriptorium-cli\`, restart Claude Code, then retry this command.`

Do not continue in degraded mode for this slash command.
````

### 10. Update internal path references for the new layout

- `CLAUDE.md`: rewrite layout section from `.claude-plugin/*` paths to root `commands/`, `skills/`, `hooks/`
- `scripts/codex_link.sh` lines 7–8, 23, 32: change source paths from `.claude-plugin/skills` and `.claude-plugin/commands` to `skills` and `commands`
- `commands/lit-podcast.md`: change `.claude-plugin/skills/publishing-to-notebooklm/SKILL.md` to `skills/publishing-to-notebooklm/SKILL.md`
- Every test hardcoding `.claude-plugin/commands`, `.claude-plugin/skills`, `.claude-plugin/hooks`, or `.claude-plugin/CLAUDE.md`

### 11. Leave hook command shape alone

`hooks/hooks.json:9` already uses:

```json
"command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/evidence_gate.sh\""
```

This is the correct runtime form once `hooks/` lives at plugin root. **Do not** rewrite to a repo-relative path.

### 12. Add layout regression test

Create `tests/test_plugin_layout.py`:

```python
from pathlib import Path

def test_plugin_layout_is_rooted():
    assert Path("commands").is_dir()
    assert Path("skills").is_dir()
    assert Path("hooks").is_dir()
    assert Path("CLAUDE.md").is_file()
    assert Path(".claude-plugin/plugin.json").is_file()
    assert Path(".claude-plugin/marketplace.json").is_file()
    assert not Path(".claude-plugin/commands").exists()
    assert not Path(".claude-plugin/skills").exists()
    assert not Path(".claude-plugin/hooks").exists()
    assert not Path(".claude-plugin/CLAUDE.md").exists()
```

### 13. Add `.github/workflows/publish.yml`

Not a thin build-and-publish. Includes smoke install and install-surface tests:

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - "v*"

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install build and test tooling
        run: python -m pip install --upgrade pip build pytest

      - name: Build sdist and wheel
        run: python -m build

      - name: Smoke install wheel
        run: |
          python -m venv .venv-smoke
          . .venv-smoke/bin/activate
          pip install dist/*.whl
          scriptorium --version

      - name: Install dev dependencies
        run: python -m pip install -e ".[dev]"

      - name: Run install-surface tests
        run: |
          pytest -q \
            tests/test_plugin_layout.py \
            tests/test_plugin_manifest.py \
            tests/test_readme.py \
            tests/test_release_artifacts.py \
            tests/test_command_lit_config.py \
            tests/test_command_lit_review.py \
            tests/test_commands_cc_only.py \
            tests/test_slash_publish_commands.py \
            tests/test_slash_setup.py \
            tests/test_version_v03.py

      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

The publish job is **not** where you run network mocks, E2E fixtures, or Codex symlink churn. Install-surface only.

### 14. Clean the tree before release

- Delete `scriptorium_cli.egg-info/` from the working tree (release noise; `.gitignore:18-21` already ignores it)
- If `.codex` remains tracked in git, regenerate it after updating `scripts/codex_link.sh`; otherwise remove from git and treat as generated output

### 15. Local verification before tagging

```bash
python3 -m pytest -q \
  tests/test_plugin_layout.py \
  tests/test_plugin_manifest.py \
  tests/test_readme.py \
  tests/test_release_artifacts.py \
  tests/test_command_lit_config.py \
  tests/test_command_lit_review.py \
  tests/test_commands_cc_only.py \
  tests/test_slash_publish_commands.py \
  tests/test_slash_setup.py \
  tests/test_version_v03.py
```

```bash
python3 -m build
```

```bash
python3 -m venv /tmp/scriptorium-smoke
/tmp/scriptorium-smoke/bin/pip install dist/*.whl
/tmp/scriptorium-smoke/bin/scriptorium --version
```

Then in a fresh Claude Code session:

```
/plugin marketplace add Jerrymwolf/Scriptorium
/plugin install scriptorium@scriptorium-local
```

Manually confirm `/lit-config` and `/lit-review` appear before tagging.

## Tag + Release Sequence

1. Commit the repo-structure fix, marketplace file, README rewrite, setup-surface rewrite, preflight, path-reference fixes, tests, and workflow in one release-prep commit.
2. Push to release branch and run the local verification commands above.
3. Merge to `main`.
4. Push `main`.
5. In a fresh shell, manually verify the real install path:
   ```bash
   pipx install scriptorium-cli
   ```
   ```
   /plugin marketplace add Jerrymwolf/Scriptorium
   /plugin install scriptorium@scriptorium-local
   ```
   Confirm `/lit-config` and `/lit-review` appear.
6. Tag the verified commit: `git tag v0.3.1`
7. Push the tag: `git push origin v0.3.1`
8. Wait for `publish.yml` to finish. Confirm the PyPI release exists.
9. In a clean environment: `pipx install scriptorium-cli==0.3.1` and `scriptorium --version`.
10. Repeat the Claude Code marketplace install once more from clean plugin state. Confirm slash commands still appear.
11. Update `CHANGELOG.md` release notes. Announce the install UX.

## Migration for Early Users

Early users who ran the old `install_plugin.sh` have a stale symlink at `~/.claude/plugins/scriptorium`. Document in the v0.3.1 CHANGELOG and README:

```bash
rm -rf ~/.claude/plugins/scriptorium
```

Then the new four-line flow.

## PyPI Trusted Publisher Config (Already Done)

| Field | Value |
|---|---|
| PyPI Project Name | `scriptorium-cli` |
| Owner | `Jerrymwolf` |
| Repository name | `Scriptorium` |
| Workflow name | `publish.yml` |
| Environment name | (Any) |

No GitHub environment required. OIDC handles auth.

## Success Criteria

1. `tests/test_plugin_layout.py` passes.
2. Install-surface tests all green.
3. `python3 -m build` produces a wheel that smoke-installs and exposes `scriptorium --version`.
4. Fresh Claude Code session: `/plugin marketplace add Jerrymwolf/Scriptorium` → `/plugin install scriptorium@scriptorium-local` → `/lit-config` and `/lit-review` appear.
5. PyPI shows `scriptorium-cli 0.3.1` after tag push.
6. `pipx install scriptorium-cli` from a clean machine, then the Claude Code flow, completes end-to-end without clone or symlink.
