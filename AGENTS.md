# AGENTS.md

Canonical working rules for ALL AI agents in this repository (Claude Code, Hermes, Codex, ...).
CLAUDE.md imports this file so all agents share the same rules and architecture guidance.

## What this is

- **`personal-os-setup`**: cross-platform Textual TUI app — OS/distro detection → package catalog →
  manager backends → system actions. Code in `src/personal_os_setup/`.
- **`docs/`**: documentation hub published via properdocs/mkdocs.
- `src/awesome_os/` is dead — ignore it.

## Safety: confirm before system-mutating actions (MANDATORY)

- Package installs/upgrades/removals, `chezmoi apply`, shell changes, driver/VM/WSL setup, `sudo` steps:
  **explicit, per-action user approval before running**. A prior "yes" is not standing approval.
- Destructive: `make vm-clean`, `make deploy-doc-gh` (pushes gh-pages). Never bypass the TUI's
  confirm dialogs (`SystemAction.confirm=False`).
- **Git: NEVER run `git commit` or `git push` without the user's explicit approval.** Both are
  approved per action, every single time. A task description, a plan, "do the work", a previous
  approval, or an earlier push on the same branch is NOT permission. Ask, wait for the yes, then
  run exactly the action that was approved. The same applies to `--force`, PR creation/merge and
  release-branch actions. **If an approval prompt times out, STOP** — silence is not consent; say
  "prompt me again" is the user's call, not yours.

## Config requests change the repo, never the machine (MANDATORY)

"Disable X in settings", "set Y in my config", "add this to my shell/editor" means edit the

## Commands

| Command                       | Purpose                                                                                   |
|-------------------------------|-------------------------------------------------------------------------------------------|
| `make check`                  | local gate: static/docs hooks, then `test-all`                                            |
| `make test-local`             | safe unit + isolated skills suites; also the default pytest discovery                     |
| `make test-coverage`          | safe checks with separate Python coverage; no threshold                                   |
| `make test-all`               | every self-contained suite: unit + skills, then the built-wheel install smoke             |
| `make pre-commit`             | static/docs hooks incl. actionlint and zizmor; no dependency sync or hook installation    |
| `make install-dev`            | full dev env and Git hooks (use this, not `uv pip install -e .`)                          |
| `make lint` / `make format`   | ruff directly                                                                             |
| `make test-integration`       | **CI only**: Linux/macOS mutate packages; Windows is read-only                            |

Run `make check` before any PR. It establishes local validation; required CI additionally runs
self-contained checks and executed integration on Ubuntu/macOS/Windows. CachyOS integration is not
covered by hosted CI. `make test-local` alone omits artifact/runtime and strict documentation checks.
Full validation targets reject `ARGS` and `PYTEST_ADDOPTS`; use `test-local ARGS="..."` for filtered runs.

## Conventions

- **Branch:** from `dev`. `feature/<name>` / `bugfix/<name>`.
- **Commits:** Conventional Commits, gitmoji optional. `feat`→minor · `fix`/`perf`→patch ·
  `feat!`/`BREAKING CHANGE:`→major · others→no release. **Never bump `pyproject.toml`; never
  create tags** — semantic-release does it. commitizen validates only at `git commit`
  (commit-msg hook), not in `make pre-commit`.
- **PRs:** target `dev`; promote `dev` to `main` for stable releases. Squash-merge, title must be conventional (= the release commit message).
- **Secrets:** inline `# pragma: allowlist secret`, never whole-file excludes.
- **Renovate:** 7-day cooldown on dependency PRs; `uv.lock` regenerated, not pinned.
- **Releases:** `make release-version` / `release-assets` / `release` (`scripts/release.sh`) are what
  the main release workflow runs too. Guards: `main`/`dev`, clean tree, in sync with origin; CI binds to
  tested `GITHUB_SHA`, while local releases default to `HEAD`. The
  token is `GH_TOKEN`, else the `gh auth login` session, else a hidden prompt. Never run them, nor
  `make deploy-doc-gh`, without per-action approval: they push, tag and publish.
- **Docs:** developer pages live in `docs/developer/` (numbered, one purpose line, short tables);
  update the page a change affects in the same change.

## Index

| Topic                                                    | Where                                 |
|----------------------------------------------------------|---------------------------------------|
| Deep architecture (frontend, tasks, managers)            | [Architecture](#architecture)         |
| Developer guide (setup, conventions, testing, release)   | `docs/developer/`                     |
| PR flow / ship process                                   | `.claude/skills/ship-feature`         |
| Documented-vs-reality drift                              | `.claude/skills/repo-gotchas`         |
| Tests & coverage                                         | `.claude/skills/run-tests`            |
| Docs site gotchas                                        | `.claude/skills/docs-site`            |
| Repo skill layout / adding skills                        | `.claude/skills/skill-layout`         |
| New TUI action / package-manager backend                 | `.claude/skills/add-system-action`    |
| Chezmoi dotfiles source scripts                          | `.claude/skills/chezmoi-scripts`      |
| VM test lab (CachyOS host)                               | `.claude/skills/vm-lab`               |
| Forking this repo for your own setup                     | `.claude/skills/fork-and-customize`   |

## Skills & plugins — one rule: authored → the repo tree, third-party → npx

- **Authored skills** live in ONE tree, repo `dot_claude/skills/` → `~/.claude/skills` (`make skills-personal-repo-to-live`).
  Codex gets per-skill links in `~/.agents/skills`; `make skills-status` verifies them.
  Hermes reads `~/.claude/skills` too (`skills.external_dirs`), so nothing is duplicated into
  `~/.hermes/skills` — a name in both roots is unloadable (`Ambiguous skill name … Refusing to guess`);
  `make skills-status` flags it. The saved set is listed in `skills.keep`; save a live skill into the
  repo with `make skills-personal-live-to-repo NAME=<name>`.
- **Private content stays out:** an `exposure: private` skill is live only (`hermes curator pin`) —
  **this repo is PUBLIC**.
- **Third-party, skills-only:** `npx skills add <owner>/<repo> -s <skill> -a <agent> -g -y --copy`;
  `--copy` makes the agent dir hold a **real directory** regardless of the CLI's symlink default; the
  lock (`$XDG_STATE_HOME/skills/.skill-lock.json`, older CLIs `~/.agents/.skill-lock.json`) is copied into the repo (`make skills-thirdparty-live-to-repo`;
  `make skills-thirdparty-repo-to-live` reinstalls for Claude Code and Codex). Use `AGENT=codex` for Codex only.
- **Never vendored:** agent-shipped (bundled / official optional) skills, plugin packs (that harness's
  own channel, one install per harness), and the Claude account sync (`~/.claude/skills/synced/`).
  Agent-created (Curator) skills are live only until triaged: promote, pin-private, or delete.

- **Corollaries:** no third-party pack vendored as a copy; no upstream-shipped skill forked into
  the repo; no agent-created name left untriaged. **One canal per pack per agent** — never plugin
  *and* npx for the same agent (the model then sees one name twice).
- **Transport for our own content is git + `make` only** — our skills never go through npx, a
  plugin, or a lock file; a tool that owns a directory must not own ours.
- **npx targeting — one name must be reachable by each agent exactly once.** `-a claude-code` alone
  already reaches Hermes (it reads `~/.claude/skills`), so never add `-a hermes-agent`: two roots
  Hermes reads → `Ambiguous skill name … Refusing to guess`. `-a claude-code -a codex` is safe
  (disjoint readers); **never `-a '*'`**, which expands to that bad pair. Keep third-party names
  disjoint from shipped/deployed ones, and check before installing (the lock's three
  `NousResearch/hermes-agent` names are a documented exception — see `skill-deployment`).
- **Three former entries are no longer in this repo:** `skill-creator` was vendored from
  `anthropics/skills` and is now served only by the Claude account sync — a second copy of that name
  collides with it and makes the name **unloadable in Hermes**. `hermes-s6-container-supervision` was
  a stale fork of the agent's official optional skill and is now installed from there instead
  (`hermes skills repair-official <name> --restore --yes`), not from this repo.
  `nicegui-frontend-testing` was removed as unused.
- **Bundled (addon-shipped) skills are read-only:** an edited copy is skipped by the sync forever;
  put local additions in a skill we own instead and run `hermes skills reset <name>` to unfreeze —
  see the shared [skill-deployment skill](src/personal_os_setup/config/chezmoi/dot_claude/skills/skill-deployment/SKILL.md).

## Known drift (trust nothing blindly)

- actionlint and zizmor are active; pip-audit, bandit and markdown-link-check remain disabled in `.pre-commit-config.yaml`
- `make docker-prod`/`docker-dev` don't exist
- Docs said `_PRIMARY_MANAGERS_BY_DISTRO` — the real constant is `_UI_VISIBLE_MANAGERS_BY_DISTRO`
- `properdocs.yml` uses `docs_dir: .` — new top-level dirs must join the exclude glob or they
  get crawled into the published site

## Architecture

### OS/distro detection → package catalog → UI

`detect_os.py` is the entry point for environment awareness:

- `detect_os()` returns an `OSInfo(family, distro, info)` — family is `windows`/`darwin`/`linux`/`unknown`; on Linux, `distro` comes from `/etc/os-release` `ID` (e.g. `ubuntu`, `cachyos`), and WSL is detected separately (`_is_wsl()`, checks `/proc/sys/fs/binfmt_misc/WSLInterop` or `/proc/version`).
- `build_packages_for_os()` loads `src/personal_os_setup/config/packages.yaml` (the single source of truth for installable packages, keyed by distro → manager → category → package list) and filters it to the current distro via `PackageCatalog.for_distro()`, producing a flat list of `PackageRef(name, manager, category)`.

### Package managers (`tasks/managers/`)

Each backend (apt, snap, brew/cask, winget, msstore, pacman/paru, webinstall) implements the `PackageManager` protocol in `tasks/managers/base.py`: `is_installed`, `install`, `update`, `upgrade`, `cleanup`. `tasks/factory.py` maps `(distro, manager_name)` → manager class in `_PACKAGE_MANAGER_FACTORY_BY_DISTRO`, and `_UI_VISIBLE_MANAGERS_BY_DISTRO` controls which managers are surfaced in the UI per distro (e.g. only `apt` shown for Ubuntu even though `snap`/`webinstall` also exist) to avoid duplicate buttons.

`tasks/managers/_shared.py` centralizes result-construction boilerplate reused across backends: `command_details()`/`format_failed_command()` (stdout/stderr → details text), `sudo_required_task_result()`/`sudo_required_install_result()`, `missing_executable_task_result()`/`missing_executable_install_result()`, and `winget_path()`/`winget_list_shows_installed()` (shared by the winget and msstore backends). Each manager still calls `shutil.which(...)`/`sudo_non_interactive_ok()` itself (not through `_shared.py`) so unit tests can keep patching those checks at the manager's own module path — `_shared.py` only builds the resulting `TaskResult`/`InstallResult` once the check has failed. Follow this pattern (local check, shared result-builder) when adding a new manager rather than re-deriving the boilerplate.

### System actions (`tasks/factory.py::get_system_action_sections`)

This function is the other half of the factory: given `(system, distro, info)` it builds an ordered list of `(section_name, [SystemAction])` used to render tabs/buttons in the TUI. It composes small per-domain builder functions (`_package_manager_sections`, `_start_section`, `_dotfiles_section`, `_docker_section`, `_nvidia_section`, `_wsl_section`, `_advanced_wsl_section`, `_windows_utilities_section`), each returning one `Section` (a `(name, [SystemAction])` tuple) and independently unit-tested in `tests/unit/test_factory.py`. `_start_section` ("🚀 Start" tab) returns only the two doc-link actions — the onboarding walkthrough text itself is frontend-only markdown (`app.py::_START_GUIDE_MARKDOWN`), special-cased in `compose()` the same way the dotfiles tree is. Sections are assembled conditionally based on `system`/`distro` (e.g. zsh/chezmoi/docker sections only for linux+darwin, WSL sections only for windows, NVIDIA section for windows+linux). `SystemAction` supports plain actions (`run`), prompted actions that take free-text input (`run_with_prompt` + `prompt_label`/`prompt_initial`), destructive-action confirmation (`confirm`/`confirm_message`), and file backup before mutating config (`backup_target`). When adding a new system action, add it to (or add a new) per-domain builder function rather than wiring buttons directly in the frontend.

### Task execution model

`tasks/task.py` defines the generic `Task`/`TaskResult`/`run_tasks()` primitives (idempotent check → run, catch-and-report exceptions as failed `TaskResult`s) used by some system tasks; individual `SystemAction.run` callables in the factory return `TaskResult` directly and are invoked from the UI without going through `run_tasks`.

### Frontend (`frontend/`)

Built on [Textual](https://textual.textualize.io/) (`textual`), not a web/GUI framework:

- `app.py` (`PersonalOsSetupApp`) — the whole UI in one `App` subclass, Textual-idiomatic (controller logic folds into the App rather than a separate controller class): `compose()` renders a `TabbedContent` with a "📦 Packages" tab (`SelectionList[PackageRef]` + install button + `ProgressBar`), one dynamically-generated `TabPane` per `(section_name, [SystemAction])` tuple from `get_system_action_sections()`, and a "📋 Logs" tab (`RichLog`). A single `is_busy: reactive[bool]` drives all busy-state UI (button disabling, the docked `LoadingIndicator`, status label) through one `watch_is_busy()` method — set `self.is_busy = True/False` rather than updating widgets by hand. Background work (package installs, system actions) runs via `@work(thread=True, exclusive=True)` workers that call back into the UI thread with `self.call_from_thread(...)` — there's no manual job queue or poll timer; toggling `is_busy` from a worker thread must go through `self.call_from_thread(setattr, self, "is_busy", False)` since reactive watchers touch widgets and must run on the app's own thread. Confirm/prompt gating (`action.confirm`, `action.run_with_prompt`) pushes `dialogs.py`'s modal screens via `self.push_screen(..., callback)`. Job completion also calls `self.notify(...)` for a toast, in addition to the Logs tab.
- `app.tcss` — external Textual CSS (via `CSS_PATH`), not an inline `CSS` string, so styling can be iterated on with `textual run --dev` live-reload.
- `dialogs.py` — `ConfirmScreen` (Yes/No) and `PromptScreen` (label + `Input` + OK/Cancel), both `ModalScreen` subclasses that dismiss with a typed result (`bool` / `str | None`) consumed by the pushing callback.
- `main.py` — thin entry point: `sudo_preauth()` then `PersonalOsSetupApp().run()`.

Frontend behavior is covered by `tests/unit/frontend/test_app.py` using Textual's headless `App.run_test()`/`Pilot` harness. When adding tests here, never click a button wired to a real package-manager/system action (e.g. real `brew`/`apt`/`winget` commands) — build a synthetic `SystemAction` with an in-memory `run` callable instead, the way the existing confirm-flow test does, so tests can't mutate the host system.

### Settings/logging (`settings.py`)

`ApplicationSettings` (pydantic-settings) reads `LOGGING_LEVEL` from env/`.env` (default `CRITICAL`); `logger` is a `loguru` logger bound to `name="personal-os-setup"` with the default sink removed to avoid duplicate output — use this `logger`, not a fresh loguru instance, in new modules.

## Code style

- **Exceptions**: always log (via the bound `logger`) then re-raise, unless inside a loop where one failure shouldn't abort the rest (see `run_tasks`). Prefer `if/else` + explicit raise over broad try/except when the failure condition is checkable upfront.
- **Docstrings**: Google-convention docstrings are enforced by ruff (`D` rules) except for the usual boilerplate exemptions (`D100-D104`, `D107`, `D417`); write them since they feed `properdocs`/mkdocstrings generation.
