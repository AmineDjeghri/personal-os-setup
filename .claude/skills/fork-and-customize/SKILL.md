---
name: fork-and-customize
description: Use when someone wants to fork this repo to build their own personal OS setup tool, or asks how to rebrand/adapt it — "fork this repo", "make this my own", "use this for my dotfiles", "rebrand this". Covers what to rename/rebrand, how to customize packages.yaml and the chezmoi dotfiles source, and what release/CI plumbing to leave alone.
---

# Forking personal-os-setup for your own setup

The repo is designed so most personalization lives in **data** (`packages.yaml`, the chezmoi source dir, `docs/`), not code — a fork mainly needs to replace those, not rewrite the app.

## What to customize

1. **Package catalog** — `src/personal_os_setup/config/packages.yaml`. Structure: `packages: <distro>: <manager>: <category>: [package names]`. Edit/add/remove entries per distro; categories are free-form strings (they become `Collapsible` groups in the Packages tab). See [[add-system-action]] if you're also adding a brand-new manager backend, not just editing package lists for existing managers.
2. **Dotfiles** — `src/personal_os_setup/config/chezmoi/` is the chezmoi source dir shipped with the package (`chezmoi_source_dir()` in `tasks/system/chezmoi.py` resolves it via `importlib.resources`). Replace `dot_zshrc`/`dot_p10k.zsh`/`dot_config/...` with your own, or use the app's own "Sync dotfiles" tab (`chezmoi: track a new file` action) to add files interactively once you're running your fork. `.chezmoiexternal.toml`/`.chezmoiignore` in that dir control externally-pulled resources (oh-my-zsh, plugins, theme) and ignore rules.
3. **Branding / metadata**:
   - `pyproject.toml`: `[project] name`, `description`, `[project.scripts]` entry point name if you want a different CLI command.
   - `CNAME` (repo root) — the custom domain for the docs site, only relevant if you're using GitHub Pages with a custom domain.
   - `src/personal_os_setup/tasks/system/help.py`'s `DOCS_SITE_URL` constant — the URL the in-app "🚀 Start" tab's doc-link buttons open. See app.py's `_START_SECTION_NAME`/`_START_GUIDE_MARKDOWN` if you also want to edit the in-app onboarding walkthrough text.
   - `properdocs.yml`: `site_name`, `site_author`, `theme.logo`/`favicon`.
   - `README.md`/`docs/` content — the actual walkthrough docs the doc-link buttons point to.
4. **OS-specific config** under `src/personal_os_setup/config/{darwin,unix,windows,others}/` — these are bundled app-specific config files (Raycast, Aerospace, GlazeWM, etc.) referenced by individual system actions in `factory.py`; swap for your own equivalents if you use different apps, and update the corresponding `tasks/system/*.py` action that references them.

## What to leave alone (unless you specifically want it)

- Release/CI plumbing (`python-semantic-release` config in `pyproject.toml`, `.github/workflows/*.yml`, `scripts/emoji_commit_parser.py`) — only relevant if you want the same automated versioning/release flow on your fork. If you're not publishing releases, you can ignore or strip this rather than maintain it.
- `docs_dir: .` mkdocs setup in `properdocs.yml` — only matters if you intend to publish a docs site via GitHub Pages. See [[docs-site]] for its quirks (the exclude-glob trap for new top-level directories especially matters if your fork adds new repo-root directories).
- The package-manager backend code (`tasks/managers/*.py`) and the factory's OS-detection logic (`detect_os.py`) — these are the actual engineering, reusable as-is unless you're targeting an unsupported distro/OS.

## Getting your fork running locally

Same as any contributor: `make install-dev`, `make run` to launch the TUI, `make test` to confirm the (currently upstream) test suite passes against your changes. If you heavily edit `packages.yaml`, run `make test` — `tests/unit/test_detect_os.py::TestPackagesYaml` will catch a manager name that doesn't resolve to a registered backend. See [[run-tests]] for what's safe to run locally (`make test`) versus destructive (`make test-integration`).

If you want to keep pulling upstream improvements into your fork, keep your customizations scoped to the data/config files above rather than editing shared code paths (`factory.py`, `app.py`, `tasks/managers/`) — that keeps merge conflicts from upstream minimal.
