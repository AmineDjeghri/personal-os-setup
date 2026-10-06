---
name: fork-and-customize
description: Use when someone wants to fork this repo to build their own personal OS setup tool, or asks how to rebrand/adapt it — "fork this repo", "make this my own", "use this for my dotfiles", "rebrand this". Covers what to rename/rebrand, how to customize packages.yaml and the chezmoi dotfiles source, and what release/CI plumbing to leave alone.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Forking personal-os-setup for your own setup

Most personalization lives in **data** (`packages.yaml`, the chezmoi source dir, `docs/`), not code — a fork mainly replaces those, not the app.

## What to customize

1. **Package catalog** — `src/personal_os_setup/config/packages.yaml`. Structure: `packages: <distro>: <manager>: <category>: [package names]`. Categories are free-form strings (they become `Collapsible` groups in the Packages tab). See [[add-system-action]] if you're adding a brand-new manager backend, not just editing lists for existing managers.
2. **Dotfiles** — `src/personal_os_setup/config/chezmoi/` is the chezmoi source dir shipped with the package (`chezmoi_source_dir()` in `tasks/system/chezmoi.py` resolves it via `importlib.resources`). Replace `dot_zshrc`/`dot_p10k.zsh`/`dot_config/...` with your own, or add files interactively through the app's "Sync dotfiles" tab (`chezmoi: track a new file` action). `.chezmoiexternal.toml`/`.chezmoiignore` in that dir control externally-pulled resources (oh-my-zsh, plugins, theme) and ignore rules.
3. **Branding / metadata**:
   - `pyproject.toml`: `[project] name`, `description`, and the `[project.scripts]` entry-point name if you want a different CLI command.
   - `CNAME` (repo root) — custom domain for the docs site, only if you use GitHub Pages with one.
   - `src/personal_os_setup/tasks/system/help.py`'s `DOCS_SITE_URL` constant — the URL the in-app "🚀 Start" tab's doc-link buttons open (see `app.py`'s `_START_SECTION_NAME`/`_START_GUIDE_MARKDOWN` for the onboarding text).
   - `properdocs.yml`: `site_name`, `site_author`, `theme.logo`/`favicon`.
   - `README.md`/`docs/` content — the walkthrough the doc-link buttons point to.
4. **OS-specific config** under `src/personal_os_setup/config/{darwin,unix,windows,others}/` — bundled app-specific config files (Raycast, Aerospace, GlazeWM, …) referenced by individual system actions in `factory.py`; swap them and update the corresponding `tasks/system/*.py` action.

## What to leave alone (unless you specifically want it)

- Release/CI plumbing (`python-semantic-release` config in `pyproject.toml`, `.github/workflows/*.yml`, `scripts/emoji_commit_parser.py`) — only needed for the same automated versioning/release flow; strip it if you're not publishing releases.
- The `docs_dir: .` mkdocs setup in `properdocs.yml` — only matters if you publish a docs site via GitHub Pages. See [[docs-site]], especially the exclude-glob trap if your fork adds new repo-root directories.
- The package-manager backends (`tasks/managers/*.py`) and `detect_os.py` — the actual engineering, reusable as-is unless you target an unsupported distro/OS.

## Getting your fork running locally

Same as any contributor: `make install-dev`, `make run` to launch the TUI, `make test` to confirm the suite passes against your changes. Heavily edited `packages.yaml` is checked by `tests/unit/test_detect_os.py::TestPackagesYaml` — it catches a manager name with no registered backend. See [[run-tests]] for what's safe locally (`make test`) versus destructive (`make test-integration`).

To keep pulling upstream improvements, keep customizations in the data/config files above rather than in shared code paths (`factory.py`, `app.py`, `tasks/managers/`) — that keeps upstream merge conflicts minimal.
