---
name: add-system-action
description: Use when adding a new TUI button/action (system action) or a new package-manager backend to personal-os-setup — e.g. "add a button to do X", "support a new package manager", "add a new tab/section". Covers the factory.py section-builder pattern, the managers/_shared.py boilerplate pattern, and the required test additions.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Adding a system action or package manager backend

The TUI is entirely data-driven from `src/personal_os_setup/tasks/factory.py::get_system_action_sections()`. Never wire a button directly in `frontend/app.py` — add it to a section builder in `factory.py`; the frontend renders whatever sections/actions the factory returns generically (one `TabPane` per section, one `Button` per action), except for two sections it knows by name: `"Sync dotfiles"` (chezmoi tree/toolbar) and `"🚀 Start"` (onboarding markdown before the doc-link buttons).

For anything involving the chezmoi source tree (`config/chezmoi/`) — a `run_*` script, or why a synced file's companion script didn't fire — see [[chezmoi-scripts]] first; the targeted-apply scoping is easy to get wrong.

⚠️ Every `SystemAction.run` you write is a real system-mutating command (installs a package, overwrites a config file, changes the default shell, touches drivers) once a user clicks it. That's the app's purpose — but when *you* implement or test one, never invoke it against the real host to "check it works": read the code and run it through the unit-test mocks ([[run-tests]]). If you genuinely need to exercise the real command, confirm the exact command with the user first. Canon: `AGENTS.md` § "Safety: confirm before system-mutating actions (MANDATORY)".

## Adding a new action to an existing section

1. Find the right per-domain builder in `factory.py` (e.g. `_dotfiles_section`, `_system_section`, `_wsl_section`) — sections are independently unit-tested in `tests/unit/test_factory.py`, one test class per section.
2. Append a `SystemAction(...)` to that builder's returned list. Fields: `label`, `run: Callable[[], TaskResult]`, `run_with_prompt`/`prompt_label`/`prompt_initial` (free-text input), `confirm`/`confirm_message` (destructive actions), `backup_target: Path | None` (copied with a timestamp suffix before `run`), `group: str | None` (adjacent actions sharing a `group` render on one row).
3. The actual logic lives in `tasks/system/<domain>.py`, not `factory.py` — the factory only assembles `SystemAction`s and returns `TaskResult`s from imported functions.
4. Add/extend a test in `tests/unit/test_factory.py` using the existing `_actions_in(system, distro, section_name)` / `_action_in(...)` helpers — they call `get_system_action_sections` directly, no App instantiation needed.

## Adding a brand-new section

1. Write a `_xxx_section(...) -> Section` returning `(section_name, [SystemAction, ...])` (`Section = tuple[str, list[SystemAction]]`).
2. Wire it into `get_system_action_sections()`, gated on `system`/`distro` as appropriate.
3. Unless it needs custom widgets (dotfiles' tree, Start's markdown), it renders automatically via the generic branch in `app.py::compose()` — no frontend change.
4. If it does need a custom widget, special-case it in `compose()` by section-name constant (see `_DOTFILES_SECTION_NAME`/`_START_SECTION_NAME`) — the section-name string stays a plain literal in `app.py` matching the factory's, which is the existing convention.

## Adding a new package-manager backend

1. Implement the `PackageManager` protocol (`tasks/managers/base.py`): `is_installed`, `install`, `update`, `upgrade`, `cleanup`.
2. Each method does its own `shutil.which(...)`/`sudo_non_interactive_ok()` check *locally in the manager's own module* (not through `_shared.py`) — deliberate, so unit tests can patch those checks at the manager's module path.
3. Build `TaskResult`/`InstallResult` through the shared helpers in `tasks/managers/_shared.py` (`command_details()`/`format_failed_command()`, `sudo_required_task_result()`/`sudo_required_install_result()`, `missing_executable_task_result()`/`missing_executable_install_result()`) — follow that "local check, shared result-builder" split rather than re-deriving the boilerplate.
4. Register it in `tasks/factory.py::_PACKAGE_MANAGER_FACTORY_BY_DISTRO` (maps `(distro, manager_name)` → class) and, if it should get its own tab/button, `_UI_VISIBLE_MANAGERS_BY_DISTRO`.
5. Add its packages under the right distro/manager/category in `src/personal_os_setup/config/packages.yaml`.

Before a PR, run `make test` and `make pre-commit` — see [[ship-feature]] for the git/PR workflow.

## Distro-keying facts worth knowing

- Distro keying is exact-match on `/etc/os-release` `ID`, no fallback: `PackageCatalog.for_distro(distro)` → `packages.get(distro, {})`. The yaml keys are only `cachyos`, `darwin`, `ubuntu`, `windows` — anything else (e.g. Debian) silently gets an empty Packages tab, no error. Other tabs (Start/Dotfiles/Docker/zsh) still work, being keyed on linux/darwin rather than distro.
- Adding a distro needs entries in **three** places: the `packages.yaml` block, `_UI_VISIBLE_MANAGERS_BY_DISTRO` (`factory.py` — which primary managers get a tab/button), and `_PACKAGE_MANAGER_FACTORY_BY_DISTRO`. Missing one either hides the tab or crashes at load with a `TypeError`.
- Don't rename the `ubuntu:` key to generalize it — it's genuinely Ubuntu-specific (snap, PPAs) and CI's `integration-ubuntu` job depends on it.
