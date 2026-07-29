# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An "OS setup" project with two parts:
1. A cross-platform Python **terminal UI app** (`personal-os-setup`, package `src/personal_os_setup/`) that detects the host OS/distro and lets the user install packages and run system actions (WSL management, zsh/oh-my-zsh, NVIDIA drivers, Windows Terminal config, chezmoi dotfiles, Docker post-install, etc).
2. A **documentation hub** (`docs/`) covering Windows/WSL2, Linux, macOS, Android TV, and home-server setups, published as a static site via `properdocs`/`mkdocs`.

`src/awesome_os/` only contains stale `__pycache__` directories from a prior package name — the real package is `personal_os_setup`. Don't treat it as live code.

## Commands

All common tasks go through `make` (backed by `makefiles/*.mk`, included from the root `Makefile`). Run `make help` to list targets by category.

- `make install-dev` — installs uv (if needed) and all dependency groups (dev + docs) into `.venv`. Use this, not `uv pip install -e .` unless doing something one-off.
- `make test` — `uv run pytest tests/unit` (exit code 5 / "no tests collected" is treated as success).
- `make test-integration` — runs `tests/integration/*` (requires Ubuntu with passwordless sudo; not runnable on macOS/dev machines).
- Run a single test: `uv run pytest tests/unit/test_detect_os.py::test_name -v`
- `make pre-commit` — installs hooks then `pre-commit run --all-files` (ruff check+format, detect-secrets, commitizen, check-yaml/json/toml, uv-lock sync, etc). Run this and `make test` before opening a PR.
- `make lint` / `make format` — `ruff check .` / `ruff format .` directly.
- `make run` — launches the TUI (`python src/personal_os_setup/frontend/main.py`).
- `make deploy-doc-local` — builds and serves the `properdocs`/mkdocs site locally.
- `make build-package` — `uv build` (wheel).
- `make install-act` / `make act` — run GitHub Actions locally via `act` (requires Docker).

CI runs the identical `make pre-commit` / `make test` commands used locally — there is no separate GH-Actions-only tooling, so if it passes locally it passes in CI.

## Architecture

### OS/distro detection → package catalog → UI

`detect_os.py` is the entry point for environment awareness:
- `detect_os()` returns an `OSInfo(family, distro, info)` — family is `windows`/`darwin`/`linux`/`unknown`; on Linux, `distro` comes from `/etc/os-release` `ID` (e.g. `ubuntu`, `cachyos`), and WSL is detected separately (`_is_wsl()`, checks `/proc/sys/fs/binfmt_misc/WSLInterop` or `/proc/version`).
- `build_packages_for_os()` loads `src/personal_os_setup/config/packages.yaml` (the single source of truth for installable packages, keyed by distro → manager → category → package list) and filters it to the current distro via `PackageCatalog.for_distro()`, producing a flat list of `PackageRef(name, manager, category)`.

### Package managers (`tasks/managers/`)

Each backend (apt, snap, brew/cask, winget, msstore, pacman/paru, webinstall) implements the `PackageManager` protocol in `tasks/managers/base.py`: `is_installed`, `install`, `update`, `upgrade`, `cleanup`. `tasks/factory.py` maps `(distro, manager_name)` → manager class in `_PACKAGE_MANAGER_FACTORY_BY_DISTRO`, and `_PRIMARY_MANAGERS_BY_DISTRO` controls which managers are surfaced in the UI per distro (e.g. only `apt` shown for Ubuntu even though `snap`/`webinstall` also exist) to avoid duplicate buttons.

`tasks/managers/_shared.py` centralizes result-construction boilerplate reused across backends: `command_details()`/`format_failed_command()` (stdout/stderr → details text), `sudo_required_task_result()`/`sudo_required_install_result()`, `missing_executable_task_result()`/`missing_executable_install_result()`, and `winget_path()`/`winget_list_shows_installed()` (shared by the winget and msstore backends). Each manager still calls `shutil.which(...)`/`sudo_non_interactive_ok()` itself (not through `_shared.py`) so unit tests can keep patching those checks at the manager's own module path — `_shared.py` only builds the resulting `TaskResult`/`InstallResult` once the check has failed. Follow this pattern (local check, shared result-builder) when adding a new manager rather than re-deriving the boilerplate.

### System actions (`tasks/factory.py::get_system_action_sections`)

This function is the other half of the factory: given `(system, distro, info)` it builds an ordered list of `(section_name, [SystemAction])` used to render tabs/buttons in the TUI. It composes small per-domain builder functions (`_package_manager_sections`, `_help_section`, `_dotfiles_section`, `_docker_section`, `_nvidia_section`, `_wsl_section`, `_advanced_wsl_section`, `_windows_utilities_section`), each returning one `Section` (a `(name, [SystemAction])` tuple) and independently unit-tested in `tests/unit/test_factory.py`. Sections are assembled conditionally based on `system`/`distro` (e.g. zsh/chezmoi/docker sections only for linux+darwin, WSL sections only for windows, NVIDIA section for windows+linux). `SystemAction` supports plain actions (`run`), prompted actions that take free-text input (`run_with_prompt` + `prompt_label`/`prompt_initial`), destructive-action confirmation (`confirm`/`confirm_message`), and file backup before mutating config (`backup_target`). When adding a new system action, add it to (or add a new) per-domain builder function rather than wiring buttons directly in the frontend.

### Task execution model

`tasks/task.py` defines the generic `Task`/`TaskResult`/`run_tasks()` primitives (idempotent check → run, catch-and-report exceptions as failed `TaskResult`s) used by some system tasks; individual `SystemAction.run` callables in the factory return `TaskResult` directly and are invoked from the UI without going through `run_tasks`.

### Frontend (`frontend/`)

Built on [Textual](https://textual.textualize.io/) (`textual`), not a web/GUI framework:
- `app.py` (`PersonalOsSetupApp`) — the whole UI in one `App` subclass, Textual-idiomatic (controller logic folds into the App rather than a separate controller class): `compose()` renders a `TabbedContent` with a "📦 Packages" tab (`SelectionList[PackageRef]` + install button + `ProgressBar`), one dynamically-generated `TabPane` per `(section_name, [SystemAction])` tuple from `get_system_action_sections()`, and a "📋 Logs" tab (`RichLog`). A single `is_busy: reactive[bool]` drives all busy-state UI (button disabling, the docked `LoadingIndicator`, status label) through one `watch_is_busy()` method — set `self.is_busy = True/False` rather than updating widgets by hand. Background work (package installs, system actions) runs via `@work(thread=True, exclusive=True)` workers that call back into the UI thread with `self.call_from_thread(...)` — there's no manual job queue or poll timer; toggling `is_busy` from a worker thread must go through `self.call_from_thread(setattr, self, "is_busy", False)` since reactive watchers touch widgets and must run on the app's own thread. Confirm/prompt gating (`action.confirm`, `action.run_with_prompt`) pushes `dialogs.py`'s modal screens via `self.push_screen(..., callback)`. Job completion also calls `self.notify(...)` for a toast, in addition to the Logs tab.
- `app.tcss` — external Textual CSS (via `CSS_PATH`), not an inline `CSS` string, so styling can be iterated on with `textual run --dev` live-reload.
- `dialogs.py` — `ConfirmScreen` (Yes/No) and `PromptScreen` (label + `Input` + OK/Cancel), both `ModalScreen` subclasses that dismiss with a typed result (`bool` / `str | None`) consumed by the pushing callback.
- `main.py` — thin entry point: `sudo_preauth()` then `PersonalOsSetupApp().run()`.

Frontend behavior is covered by `tests/unit/test_app.py` using Textual's headless `App.run_test()`/`Pilot` harness. When adding tests here, never click a button wired to a real package-manager/system action (e.g. real `brew`/`apt`/`winget` commands) — build a synthetic `SystemAction` with an in-memory `run` callable instead, the way the existing confirm-flow test does, so tests can't mutate the host system.

### Settings/logging (`settings.py`)

`ApplicationSettings` (pydantic-settings) reads `LOGGING_LEVEL` from env/`.env` (default `CRITICAL`); `logger` is a `loguru` logger bound to `name="personal-os-setup"` with the default sink removed to avoid duplicate output — use this `logger`, not a fresh loguru instance, in new modules.

## Conventions specific to this repo

- **Exceptions**: always log (via the bound `logger`) then re-raise, unless inside a loop where one failure shouldn't abort the rest (see `run_tasks`). Prefer `if/else` + explicit raise over broad try/except when the failure condition is checkable upfront.
- **Docstrings**: Google-convention docstrings are enforced by ruff (`D` rules) except for the usual boilerplate exemptions (`D100-D104`, `D107`, `D417`); write them since they feed `properdocs`/mkdocstrings generation.
- **Secrets**: `detect-secrets` runs in pre-commit. Use `# pragma: allowlist secret` inline for a known false positive on a specific line (e.g. `${{ secrets.GITHUB_TOKEN }}`) rather than adding whole files to the pre-commit exclude list.
- **Commit messages / releases**: Conventional Commits with optional gitmoji prefix, e.g. `✨ feat(auth): ...`, `🐛 fix(llm): ...`. `python-semantic-release` (via `scripts/emoji_commit_parser.py`) drives versioning — `feat`→minor, `fix`/`perf`→patch, `feat!`/`BREAKING CHANGE`→major, `chore`/`ci`/`docs`/`style`/`refactor`/`test`/`build`→no release. **Never manually bump `pyproject.toml` version** — semantic-release does it on merge. Never create tags manually.
- **Branches**: work targets `dev`, not `main`; `dev`→`main` is a separate promotion PR. All PRs squash-merge, and the PR title becomes the release-determining commit message.
- **Renovate**: dependency PRs have a 7-day cooldown baked into `renovate.json`; `uv.lock` is regenerated rather than pinning versions directly in `pyproject.toml`.
