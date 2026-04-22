# Scriptorium Install Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v0.3.1 where `pipx install scriptorium-cli` + `/plugin marketplace add Jerrymwolf/Scriptorium` + `/plugin install scriptorium@scriptorium-local` is the complete install path — no clone, no symlink, slash commands actually appear.

**Architecture:** Move `commands/`, `skills/`, `hooks/`, `CLAUDE.md` from `.claude-plugin/` to plugin root (where Claude Code actually scans). Add `.claude-plugin/marketplace.json` so `/plugin install` from GitHub works. Delete the legacy `install_plugin.sh` symlink hack. Rewrite `/scriptorium-setup` as post-install config only. Publish `scriptorium-cli` to PyPI via OIDC on `v*` tag push.

**Tech Stack:** Python 3.12+, setuptools, pytest, bash, GitHub Actions (PyPI trusted publisher / OIDC), Claude Code plugin marketplace format.

**Spec reference:** `plans/superpowers/2026-04-20-install-fix-design.md`

**Working tree state at plan time:** Scriptorium main branch, 1 commit ahead of origin (`3083f28 docs: add install-fix design spec for v0.3.1`). Untracked: `config.toml`. All plugin surface currently at `.claude-plugin/{commands,skills,hooks,CLAUDE.md}`. Version `0.3.0` across 10+ files. Hook command shape already correct (`${CLAUDE_PLUGIN_ROOT}/hooks/evidence_gate.sh`).

---

## Pre-flight: create release branch

- [ ] **Step 0.1: Create branch**

Work from the Scriptorium repo, not Superpowers-Research.

```bash
cd /Users/jeremiahwolf/Desktop/Projects/APPs/Scriptorium
git checkout -b release/v0.3.1
git status
```

Expected: `On branch release/v0.3.1` with untracked `config.toml` (leave alone — user's local config).

---

## Task 1: Plugin layout regression test (TDD — write first, watch it fail)

**Files:**
- Create: `tests/test_plugin_layout.py`

- [ ] **Step 1.1: Write the failing layout test**

Create `tests/test_plugin_layout.py`:

```python
from pathlib import Path


def test_plugin_layout_is_rooted():
    """Claude Code scans commands/, skills/, hooks/ at plugin root — not inside .claude-plugin/."""
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

- [ ] **Step 1.2: Run it and confirm it fails**

```bash
python3 -m pytest tests/test_plugin_layout.py -v
```

Expected: FAIL — `commands/` etc. don't exist at root, `.claude-plugin/commands` does, `.claude-plugin/marketplace.json` doesn't.

- [ ] **Step 1.3: Commit the failing test**

```bash
git add tests/test_plugin_layout.py
git commit -m "test(layout): plugin surface must live at repo root, not inside .claude-plugin/"
```

---

## Task 2: Move plugin surface to repo root

**Files:**
- Move: `.claude-plugin/commands/` → `commands/`
- Move: `.claude-plugin/skills/` → `skills/`
- Move: `.claude-plugin/hooks/` → `hooks/`
- Move: `.claude-plugin/CLAUDE.md` → `CLAUDE.md`

- [ ] **Step 2.1: Move directories and CLAUDE.md with git mv**

```bash
git mv .claude-plugin/commands commands
git mv .claude-plugin/skills skills
git mv .claude-plugin/hooks hooks
git mv .claude-plugin/CLAUDE.md CLAUDE.md
```

Then confirm only `plugin.json` remains under `.claude-plugin/`:

```bash
ls .claude-plugin/
```

Expected: `plugin.json` (and nothing else yet — `marketplace.json` comes in Task 3).

- [ ] **Step 2.2: Commit the move on its own**

Keep this commit pure rename so `git log --follow` stays clean.

```bash
git commit -m "refactor(layout): move commands/skills/hooks/CLAUDE.md to plugin root"
```

---

## Task 3: Add marketplace manifest

**Files:**
- Create: `.claude-plugin/marketplace.json`

- [ ] **Step 3.1: Write marketplace.json**

The `name` field must match what README tells users to `/plugin install`. Target install line is `/plugin install scriptorium@scriptorium-local`, so marketplace name is `scriptorium-local` and plugin name is `scriptorium`.

Create `.claude-plugin/marketplace.json`:

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

- [ ] **Step 3.2: Run layout test — now passes**

```bash
python3 -m pytest tests/test_plugin_layout.py -v
```

Expected: PASS.

- [ ] **Step 3.3: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "feat(plugin): add marketplace.json so /plugin install from GitHub works"
```

---

## Task 4: Bump version to 0.3.1 everywhere

**Files (all edits):**
- Modify: `pyproject.toml`
- Modify: `.claude-plugin/plugin.json`
- Modify: `scriptorium/__init__.py`
- Modify: `scriptorium/setup_flow.py`
- Modify: `scriptorium/migrate.py`
- Modify: `scriptorium/overview/generator.py`
- Modify: `scriptorium/obsidian/stubs.py`
- Modify: `README.md`
- Modify: `commands/scriptorium-setup.md` (moved in Task 2)
- Modify: `skills/setting-up-scriptorium/SKILL.md` (moved in Task 2)
- Modify: `tests/test_version_v03.py`
- Modify: `tests/test_skill_setting_up_scriptorium.py`
- Modify: `tests/test_release_artifacts.py`
- Modify: `tests/test_frontmatter.py`
- Modify: `tests/test_doctor.py`
- Modify: `CHANGELOG.md` (add 0.3.1 entry)

- [ ] **Step 4.1: Audit every `0.3.0` occurrence**

```bash
grep -rn "0\.3\.0" --include="*.py" --include="*.toml" --include="*.json" --include="*.md" .
```

Expected output: the 19 files from the spec. Review the list — anything outside the documented set is a new surprise to inspect before blind-replacing.

- [ ] **Step 4.2: Also update pyproject.toml metadata**

In `pyproject.toml`, confirm or set:

```toml
[project]
name = "scriptorium-cli"
version = "0.3.1"
readme = "README.md"
authors = [{ name = "Jeremiah Wolf", email = "jeremiahmwolf@gmail.com" }]
```

Do **not** change `[build-system] build-backend`, `project.scripts.scriptorium`, or `[tool.setuptools.packages.find] include`. Those are already right.

- [ ] **Step 4.3: Replace 0.3.0 → 0.3.1 in each file**

Prefer surgical edits per file (use the Edit tool) so version strings that are *not* the plugin version (e.g., a dependency pin) aren't corrupted. For source files where `0.3.0` is unambiguously the Scriptorium version (e.g., `scriptorium/__init__.py: __version__ = "0.3.0"`), replace literally. For `CHANGELOG.md`, don't modify historical `## 0.3.0` headers — add a new `## 0.3.1 — 2026-04-22` section at the top with a short note referencing the install fix.

- [ ] **Step 4.4: Re-grep to confirm only intentional 0.3.0 references remain**

```bash
grep -rn "0\.3\.0" --include="*.py" --include="*.toml" --include="*.json" --include="*.md" .
```

Expected remaining references: `CHANGELOG.md` historical entries, `plans/superpowers/*-design.md` (frozen spec docs — leave them), and anywhere else `0.3.0` is genuinely the old version being referenced historically. No live version string, test assertion, or user-visible doc string should still say `0.3.0`.

- [ ] **Step 4.5: Run version + release-artifact tests**

```bash
python3 -m pytest tests/test_version_v03.py tests/test_release_artifacts.py tests/test_skill_setting_up_scriptorium.py tests/test_frontmatter.py tests/test_doctor.py -v
```

Expected: PASS. (If any test still expects `0.3.0`, update the assertion — the version itself is the source of truth for 0.3.1.)

- [ ] **Step 4.6: Commit**

```bash
git add -A
git commit -m "chore(release): bump version to 0.3.1 across all surfaces"
```

---

## Task 5: Delete legacy installer and scrub references

**Files:**
- Delete: `scripts/install_plugin.sh`
- Modify: `README.md` (lines 143-145, 328-333 per spec)
- Modify: `tests/test_readme.py` (lines 31-35, 69-72)
- Modify: `tests/test_release_artifacts.py` (lines 6-20)

- [ ] **Step 5.1: Delete the installer**

```bash
git rm scripts/install_plugin.sh
```

- [ ] **Step 5.2: Update README install section**

Open `README.md`. Replace the `scripts/install_plugin.sh` block (the spec cites lines 143-145 and 328-333 — line numbers may have shifted after the v0.3 README rewrite; search for `install_plugin.sh` and the "not yet on PyPI" string).

Replace the install instructions with the block from Task 7 below (README rewrite is combined — see step 7). For now, just delete every mention of `install_plugin.sh` and the "not yet on PyPI" caveat (spec line 132: `README.md:323`).

- [ ] **Step 5.3: Update test expectations**

`tests/test_readme.py` currently asserts the README contains `install_plugin.sh` text. Invert those assertions: the README must **not** contain `install_plugin.sh`. Example:

```python
def test_readme_has_no_legacy_installer_reference():
    body = Path("README.md").read_text()
    assert "install_plugin.sh" not in body
    assert "not yet on PyPI" not in body
```

Replace the old "contains install_plugin.sh" assertions with these.

`tests/test_release_artifacts.py` currently checks `install_plugin.sh` exists. Flip to:

```python
def test_legacy_plugin_installer_is_gone():
    assert not Path("scripts/install_plugin.sh").exists()
```

- [ ] **Step 5.4: Run the updated tests**

```bash
python3 -m pytest tests/test_readme.py tests/test_release_artifacts.py -v
```

Expected: FAIL on `test_readme_has_no_legacy_installer_reference` until Task 7 rewrites the README body. That's fine — keep going; Task 7 closes the gap.

- [ ] **Step 5.5: Commit**

```bash
git add -A
git commit -m "chore(install): delete legacy install_plugin.sh and invert test expectations"
```

---

## Task 6: Rewrite README install section

**Files:**
- Modify: `README.md`

- [ ] **Step 6.1: Replace the Claude Code install block**

Locate the current install section in `README.md` (search for `pipx install` or `install_plugin.sh`). Replace the block with:

````md
### Install

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

Delete the `README.md:323` line "not yet on PyPI" (will be false after publish). Also delete any paragraph that says to clone the repo or run `scripts/install_plugin.sh`.

- [ ] **Step 6.2: Run README tests**

```bash
python3 -m pytest tests/test_readme.py -v
```

Expected: PASS (legacy-installer assertions from Task 5 now pass because README no longer mentions it).

- [ ] **Step 6.3: Commit**

```bash
git add README.md
git commit -m "docs(readme): rewrite install section for marketplace + pipx flow"
```

---

## Task 7: Rewrite `/scriptorium-setup` as post-install config only

**Files:**
- Modify: `commands/scriptorium-setup.md`
- Modify: `skills/setting-up-scriptorium/SKILL.md`
- Modify: `scriptorium/setup_flow.py` (remove "mark steps complete without installing" lies at lines 70-95)
- Modify: `tests/test_skill_setting_up_scriptorium.py`
- Modify: `tests/test_slash_setup.py`

- [ ] **Step 7.1: Read current surfaces**

```bash
cat commands/scriptorium-setup.md
cat skills/setting-up-scriptorium/SKILL.md
sed -n '1,120p' scriptorium/setup_flow.py
```

Understand which steps are "install the plugin" (remove) vs. "collect config" (keep, rewrite as post-install).

- [ ] **Step 7.2: Rewrite `commands/scriptorium-setup.md`**

Replace its body with post-install configuration only. Template:

```md
---
name: scriptorium-setup
description: Configure Scriptorium after the CLI and plugin are installed. Collects unpaywall email, obsidian vault path, and optional NotebookLM MCP CLI.
---

# /scriptorium-setup

This command assumes you have already:

1. Installed the CLI: `pipx install scriptorium-cli`
2. Added and installed the plugin in Claude Code:
   ```
   /plugin marketplace add Jerrymwolf/Scriptorium
   /plugin install scriptorium@scriptorium-local
   ```

## What this command does

1. **Preflight.** Run `scriptorium --version`. If it fails, stop and tell the user to run `pipx install scriptorium-cli` then restart Claude Code.
2. **Collect `unpaywall_email`.** Required for OpenAlex/Unpaywall lookups.
3. **Set `obsidian_vault`.** The absolute path to the user's Obsidian vault.
4. **Optional: `notebooklm-mcp-cli`.** Offer to set it up; do not require it.
5. **Write `config.toml`** to the current workspace.

Do **not** install anything in this command. The plugin and CLI are prerequisites.
```

- [ ] **Step 7.3: Rewrite `skills/setting-up-scriptorium/SKILL.md`**

Mirror the same framing in the skill. Remove every instruction that tells the user or Claude to "install `.claude-plugin/`", copy files, or run `install_plugin.sh`. Keep the three config collection steps. Preserve the existing frontmatter format used by other skills in the repo.

- [ ] **Step 7.4: Rewrite `scriptorium/setup_flow.py` lines 70-95**

Remove the code that marks install steps complete without actually installing. The rewritten `setup_flow` should only drive config collection (unpaywall email, obsidian vault, optional NLM). If there is no remaining work for the "install" steps, delete those steps entirely — don't leave no-ops.

- [ ] **Step 7.5: Update associated tests**

`tests/test_skill_setting_up_scriptorium.py` and `tests/test_slash_setup.py` currently assert the skill/command contain install instructions. Flip the assertions:

```python
def test_setup_skill_does_not_claim_to_install_plugin():
    body = Path("skills/setting-up-scriptorium/SKILL.md").read_text()
    assert "install_plugin.sh" not in body
    assert "/plugin install" in body  # references prereq, doesn't perform it
    assert "pipx install scriptorium-cli" in body  # references prereq
```

```python
def test_setup_command_is_post_install_only():
    body = Path("commands/scriptorium-setup.md").read_text()
    assert ".claude-plugin" not in body
    assert "install_plugin.sh" not in body
    assert "unpaywall_email" in body
    assert "obsidian_vault" in body
```

- [ ] **Step 7.6: Run setup tests**

```bash
python3 -m pytest tests/test_skill_setting_up_scriptorium.py tests/test_slash_setup.py -v
```

Expected: PASS.

- [ ] **Step 7.7: Commit**

```bash
git add -A
git commit -m "feat(setup): /scriptorium-setup is post-install config only, not a self-installer"
```

---

## Task 8: Add hard preflight to CLI-dependent slash commands

**Files:**
- Modify: `commands/lit-config.md`
- Modify: `commands/lit-review.md`
- Modify: `skills/using-scriptorium/SKILL.md` (mirror the same preflight)

- [ ] **Step 8.1: Insert preflight block at top of `commands/lit-config.md`**

Immediately after the frontmatter block, insert:

````md
## Preflight

Run `scriptorium --version` first.

If that command fails or is not on PATH, stop and tell the user exactly:
`Scriptorium CLI is not on PATH. Run \`pipx install scriptorium-cli\`, restart Claude Code, then retry this command.`

Do not continue in degraded mode for this slash command.
````

- [ ] **Step 8.2: Insert the same preflight block at top of `commands/lit-review.md`**

Same text, same position (right after frontmatter).

- [ ] **Step 8.3: Update `skills/using-scriptorium/SKILL.md`**

The skill already uses `scriptorium --version` at lines 29-42 as the CC-mode probe. Change the failure branch: instead of falling into a degraded runtime path, emit the same hard-stop message. Find the existing probe block and replace the "else" branch with:

```md
If `scriptorium --version` fails:
- For CC-only commands (lit-config, lit-review): stop. Tell the user `Scriptorium CLI is not on PATH. Run \`pipx install scriptorium-cli\`, restart Claude Code, then retry this command.`
- For runtime-agnostic skills running in Cowork: continue in Cowork mode (this is expected).
```

- [ ] **Step 8.4: Write a preflight test**

Add to `tests/test_command_lit_config.py` and `tests/test_command_lit_review.py` (or create a new `tests/test_preflight.py`):

```python
from pathlib import Path

def test_lit_config_has_preflight():
    body = Path("commands/lit-config.md").read_text()
    assert "scriptorium --version" in body
    assert "pipx install scriptorium-cli" in body
    assert "degraded mode" in body

def test_lit_review_has_preflight():
    body = Path("commands/lit-review.md").read_text()
    assert "scriptorium --version" in body
    assert "pipx install scriptorium-cli" in body
    assert "degraded mode" in body
```

- [ ] **Step 8.5: Run preflight tests**

```bash
python3 -m pytest tests/test_command_lit_config.py tests/test_command_lit_review.py -v
```

Expected: PASS.

- [ ] **Step 8.6: Commit**

```bash
git add -A
git commit -m "feat(preflight): hard-stop lit-config and lit-review when scriptorium CLI missing"
```

---

## Task 9: Update internal path references for the new layout

**Files:**
- Modify: `CLAUDE.md` (moved in Task 2 — rewrite layout section)
- Modify: `scripts/codex_link.sh` (lines 7-8, 23, 32)
- Modify: `commands/lit-podcast.md`
- Modify: every test that hardcodes `.claude-plugin/commands`, `.claude-plugin/skills`, `.claude-plugin/hooks`, or `.claude-plugin/CLAUDE.md`

- [ ] **Step 9.1: Audit all remaining `.claude-plugin/` references**

```bash
grep -rn "\.claude-plugin/" --include="*.py" --include="*.sh" --include="*.md" --include="*.json" .
```

Allowed remaining references: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, historical `plans/*-design.md` (frozen). Everything else is a bug.

- [ ] **Step 9.2: Rewrite `CLAUDE.md` layout section**

In `CLAUDE.md`, replace the "Repository layout" block. Change:

```md
- `.claude-plugin/skills/` — portable prose skills (both runtimes)
- `.claude-plugin/commands/` — slash commands (Claude Code only)
- `.claude-plugin/hooks/` — PostToolUse hooks (Claude Code only)
```

To:

```md
- `skills/` — portable prose skills (both runtimes)
- `commands/` — slash commands (Claude Code only)
- `hooks/` — PostToolUse hooks (Claude Code only)
- `.claude-plugin/plugin.json` — plugin manifest
- `.claude-plugin/marketplace.json` — marketplace manifest so `/plugin install scriptorium@scriptorium-local` works from GitHub
```

- [ ] **Step 9.3: Update `scripts/codex_link.sh`**

Replace the `SRC_SKILLS` and `SRC_COMMANDS` paths and the symlink targets. Edit the file so:

```bash
SRC_SKILLS="$ROOT/skills"
SRC_COMMANDS="$ROOT/commands"
```

And the two symlink lines (currently `ln -sfn "../../.claude-plugin/skills/$name" ...` and `ln -sfn "../../.claude-plugin/commands/$name" ...`) become:

```bash
ln -sfn "../../skills/$name" "$DST_SKILLS/$name"
```

```bash
ln -sfn "../../commands/$name" "$DST_COMMANDS/$name"
```

- [ ] **Step 9.4: Update `commands/lit-podcast.md`**

Search for `.claude-plugin/skills/publishing-to-notebooklm/SKILL.md` and replace with `skills/publishing-to-notebooklm/SKILL.md`.

- [ ] **Step 9.5: Update every test with `.claude-plugin/` hardcoded paths**

From the grep in Task 9 step 1, for each test file, replace:

- `.claude-plugin/commands/` → `commands/`
- `.claude-plugin/skills/` → `skills/`
- `.claude-plugin/hooks/` → `hooks/`
- `.claude-plugin/CLAUDE.md` → `CLAUDE.md`

Leave `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` untouched.

Tests to sweep (from the grep earlier): `test_plugin_manifest.py`, `test_command_lit_config.py`, `test_command_lit_review.py`, `test_hook_evidence_gate.py`, `test_codex_symlinks.py`, `test_commands_cc_only.py`, `test_command_skill_content.py`, `test_updated_commands.py`, `test_skill_*.py` (many), `test_slash_*.py`.

Surgical approach: open each file, grep for `.claude-plugin`, rewrite the literal path. Do not blindly sed — some tests may legitimately assert `.claude-plugin/plugin.json` or `.claude-plugin/marketplace.json`.

- [ ] **Step 9.6: Regenerate `.codex/` symlinks with the new script**

If `.codex/` is tracked in git, the stale symlinks point to the old location. Rerun the link script:

```bash
bash scripts/codex_link.sh
```

Expected output: `Linked N skills, M commands into .codex/.`

- [ ] **Step 9.7: Run the sweep tests**

```bash
python3 -m pytest tests/test_plugin_manifest.py tests/test_codex_symlinks.py tests/test_hook_evidence_gate.py tests/test_commands_cc_only.py tests/test_command_skill_content.py tests/test_command_lit_config.py tests/test_command_lit_review.py -v
```

Expected: PASS.

- [ ] **Step 9.8: Full test run to catch stragglers**

```bash
python3 -m pytest -q
```

Expected: PASS across the whole suite (or only pre-existing unrelated failures — if any test fails that wasn't on the sweep list, inspect, fix or document).

- [ ] **Step 9.9: Confirm hook command shape is unchanged**

```bash
grep -n CLAUDE_PLUGIN_ROOT hooks/hooks.json
```

Expected: `"command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/evidence_gate.sh\""` — unchanged. This is correct for the new root layout; do not rewrite.

- [ ] **Step 9.10: Commit**

```bash
git add -A
git commit -m "refactor(paths): update CLAUDE.md, codex_link.sh, lit-podcast, and tests for root layout"
```

---

## Task 10: Add PyPI publish workflow

**Files:**
- Create: `.github/workflows/publish.yml`

- [ ] **Step 10.1: Confirm workflows dir does not exist yet**

```bash
ls .github/workflows/ 2>/dev/null || echo "no workflows dir — will create"
```

- [ ] **Step 10.2: Create `.github/workflows/publish.yml`**

Exactly as specified. Note: no `environment:` key on the publish job — PyPI trusted publisher shows "Environment: (Any)".

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

- [ ] **Step 10.3: Lint workflow syntax locally (best-effort)**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/publish.yml'))" && echo OK
```

Expected: `OK`.

- [ ] **Step 10.4: Commit**

```bash
git add .github/workflows/publish.yml
git commit -m "ci: add publish.yml with smoke install + install-surface tests before PyPI upload"
```

---

## Task 11: Clean the tree

**Files:**
- Delete: `scriptorium_cli.egg-info/` (if present in working tree)
- Ensure `.codex/` is either regenerated or untracked

- [ ] **Step 11.1: Remove build noise**

```bash
rm -rf scriptorium_cli.egg-info/
git status
```

Expected: nothing to commit from that directory (it's ignored by `.gitignore:18-21`). If it shows up in git status, something is wrong — inspect before forcing.

- [ ] **Step 11.2: Decide `.codex/` policy**

Check whether `.codex/` is tracked:

```bash
git ls-files .codex/ | head -5
```

If tracked: commit the regenerated symlinks from Task 9 step 6 (they already point to the new paths).

```bash
git add .codex/
git commit -m "chore(codex): regenerate .codex symlinks against root layout" || echo "nothing to commit"
```

If untracked: ensure `.gitignore` excludes it.

- [ ] **Step 11.3: Remove `config.toml` from untracked list if present**

Leave `config.toml` alone — it's the user's local config (was already untracked before the branch). Verify:

```bash
git status
```

Expected: clean working tree (or only `config.toml` untracked).

---

## Task 12: Local verification before tagging

- [ ] **Step 12.1: Run the full install-surface suite**

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

Expected: all green.

- [ ] **Step 12.2: Full suite sanity**

```bash
python3 -m pytest -q
```

Expected: all green (or only pre-existing unrelated failures — document any).

- [ ] **Step 12.3: Build sdist + wheel**

```bash
rm -rf dist/
python3 -m build
ls dist/
```

Expected: `scriptorium_cli-0.3.1-py3-none-any.whl` and `scriptorium_cli-0.3.1.tar.gz`.

- [ ] **Step 12.4: Smoke install the wheel in a throwaway venv**

```bash
rm -rf /tmp/scriptorium-smoke
python3 -m venv /tmp/scriptorium-smoke
/tmp/scriptorium-smoke/bin/pip install dist/*.whl
/tmp/scriptorium-smoke/bin/scriptorium --version
```

Expected: `0.3.1` (or a version string containing `0.3.1`).

- [ ] **Step 12.5: Manual Claude Code install check**

In a **fresh Claude Code session** (new terminal, new session):

```
/plugin marketplace add Jerrymwolf/Scriptorium
/plugin install scriptorium@scriptorium-local
```

Then type `/` and confirm the autocomplete shows `/lit-config` and `/lit-review`. Run `/lit-config` and confirm preflight reaches the CLI (since we installed via `pipx` on this machine).

If either slash command doesn't appear, STOP. Do not tag. Diagnose the layout/marketplace manifest.

- [ ] **Step 12.6: Push the release branch for review**

```bash
git push -u origin release/v0.3.1
```

Open a PR against `main` if the project uses PR-based release flow. Otherwise proceed to Task 13.

---

## Task 13: Tag and release

- [ ] **Step 13.1: Merge to main**

Merge the release branch (via PR or fast-forward). Then locally:

```bash
git checkout main
git pull --ff-only origin main
```

- [ ] **Step 13.2: Re-verify the real install path on main**

In a fresh shell:

```bash
pipx install scriptorium-cli || pipx upgrade scriptorium-cli
```

(This will use whatever is currently on PyPI — expect 0.3.0 or whatever was last shipped. That's fine; the purpose is to confirm the CLI installs cleanly before we tag.)

Then in a fresh Claude Code session:

```
/plugin marketplace add Jerrymwolf/Scriptorium
/plugin install scriptorium@scriptorium-local
```

Confirm `/lit-config` and `/lit-review` appear. (They pull from `main` now, which is the post-fix layout.)

- [ ] **Step 13.3: Tag**

```bash
git tag v0.3.1
git push origin v0.3.1
```

- [ ] **Step 13.4: Watch `publish.yml` run**

Open the GitHub Actions tab. Wait for `build` job (smoke install + install-surface tests) to pass, then `publish` to finish. If `build` fails, do NOT force `publish` — delete the tag, fix, retag.

If you need to delete a broken tag:

```bash
git push origin :refs/tags/v0.3.1
git tag -d v0.3.1
```

- [ ] **Step 13.5: Confirm PyPI shows the new release**

Check `https://pypi.org/project/scriptorium-cli/`. Confirm `0.3.1` is listed.

- [ ] **Step 13.6: End-to-end clean-machine test**

On a separate machine (or a throwaway pipx environment):

```bash
pipx uninstall scriptorium-cli 2>/dev/null || true
pipx install scriptorium-cli==0.3.1
scriptorium --version
```

Expected: `0.3.1`.

Then in a **fresh Claude Code session** (clear plugin state if needed — `rm -rf ~/.claude/plugins/scriptorium` to clear any stale symlink from early-user install):

```
/plugin marketplace add Jerrymwolf/Scriptorium
/plugin install scriptorium@scriptorium-local
/lit-config
```

Confirm slash commands appear and `/lit-config` runs preflight cleanly.

- [ ] **Step 13.7: Update CHANGELOG with shipped notes**

Edit `CHANGELOG.md`, ensure the `## 0.3.1 — 2026-04-22` entry lists:

- Fixed plugin layout so slash commands actually load in Claude Code
- Added marketplace manifest; install flow is now `pipx install scriptorium-cli` + `/plugin install scriptorium@scriptorium-local`
- Deleted legacy `scripts/install_plugin.sh`
- `/scriptorium-setup` is now post-install config only
- Hard preflight added to `/lit-config` and `/lit-review` when CLI is missing
- Migration note for early users: `rm -rf ~/.claude/plugins/scriptorium`

Commit and push:

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): 0.3.1 shipped — install fix"
git push origin main
```

- [ ] **Step 13.8: Announce**

Mention the new install UX in whatever channel the project uses (README header, release notes, or operator log).

---

## Migration note for early users

Add to README (near the install section) and to `CHANGELOG.md` 0.3.1 entry:

```md
### Migrating from the pre-0.3.1 installer

If you previously ran `scripts/install_plugin.sh`, you have a stale symlink at `~/.claude/plugins/scriptorium`. Remove it before the new flow:

```bash
rm -rf ~/.claude/plugins/scriptorium
```

Then follow the Install section above.
```

This is additive to Task 6 — if not already covered there, fold it in during Task 13.7 alongside CHANGELOG updates.

---

## Success Criteria (copied from spec — verify at end)

1. `tests/test_plugin_layout.py` passes.
2. Install-surface tests all green.
3. `python3 -m build` produces a wheel that smoke-installs and exposes `scriptorium --version`.
4. Fresh Claude Code session: `/plugin marketplace add Jerrymwolf/Scriptorium` → `/plugin install scriptorium@scriptorium-local` → `/lit-config` and `/lit-review` appear.
5. PyPI shows `scriptorium-cli 0.3.1` after tag push.
6. `pipx install scriptorium-cli` from a clean machine, then the Claude Code flow, completes end-to-end without clone or symlink.

---

## Self-review notes

**Spec coverage check.** The spec has 15 ordered steps. Mapping to tasks:

| Spec step | Task |
|---|---|
| 1 (move surface) | Task 2 |
| 2 (marketplace.json) | Task 3 |
| 3 (plugin.json version) | Task 4 |
| 4 (pyproject metadata) | Task 4 |
| 5 (version bump) | Task 4 |
| 6 (delete installer) | Task 5 |
| 7 (README rewrite) | Task 6 |
| 8 (scriptorium-setup rewrite) | Task 7 |
| 9 (preflight) | Task 8 |
| 10 (path refs) | Task 9 |
| 11 (hook command shape — leave alone) | Task 9.9 |
| 12 (layout regression test) | Task 1 |
| 13 (publish.yml) | Task 10 |
| 14 (clean tree) | Task 11 |
| 15 (local verification) | Task 12 |
| Tag + release sequence | Task 13 |
| Migration note | Migration section + Task 13.7 |

All spec sections mapped. Layout regression test hoisted to Task 1 (TDD: write failing test before the move).

**Placeholder scan.** No "TBD", no "similar to Task N", no "add appropriate error handling". Each step has exact commands, exact file paths, and concrete code or text to insert.

**Type/path consistency.** Plugin name (`scriptorium`), marketplace name (`scriptorium-local`), distribution name (`scriptorium-cli`), console script (`scriptorium`) are used consistently throughout. Every `.claude-plugin/commands/*` reference in Task 2+ is rewritten to `commands/*` in Task 9.
