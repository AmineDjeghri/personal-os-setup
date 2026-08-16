---
name: add-system-action
description: Use when adding a new TUI button/action (system action) or a new package-manager backend to personal-os-setup — e.g. "add a button to do X", "support a new package manager", "add a new tab/section". Covers the factory.py section-builder pattern, the managers/_shared.py boilerplate pattern, and the required test additions.
---

# Adding a system action or package manager backend

This repo's TUI is entirely data-driven from `src/personal_os_setup/tasks/factory.py::get_system_action_sections()`. Never wire a button directly in `frontend/app.py` — add it to a section builder in `factory.py` instead. The frontend renders whatever sections/actions the factory returns generically (one `TabPane` per section, one `Button` per action), except for two special-cased sections it knows by name: `"Sync dotfiles"` (renders the chezmoi tree/toolbar) and `"🚀 Start"` (renders the onboarding markdown before the doc-link buttons).

For anything involving the chezmoi source tree itself (`config/chezmoi/`) — adding a `run_*` script, or explaining why a synced file's companion script didn't fire — see [[chezmoi-scripts]] first; the dotfiles tree's targeted-apply scoping is easy to get wrong.

⚠️ Every `SystemAction.run` you write or edit here is a real system-mutating command (installs a package, edits/overwrites a config file, changes the default shell, touches drivers, etc.) once a user clicks it in the running app. That's expected — it's the app's whole purpose — but when *you* (as the coding agent) are implementing/testing one of these, never invoke it against the real host yourself to "check it works." Read the code, run it through the unit-test mocks (see [[run-tests]]), and if you genuinely need to exercise the real command, confirm the exact command with the user first. See `CLAUDE.md` § "Safety: always confirm before system-mutating actions".

## Adding a new action to an existing section

1. Find the right per-domain builder function in `factory.py` (e.g. `_dotfiles_section`, `_system_section`, `_wsl_section`) — sections are independently unit-tested in `tests/unit/test_factory.py`, one test class per section.
2. Append a `SystemAction(...)` to that builder's returned list. Fields available: `label` (button text), `run: Callable[[], TaskResult]`, `run_with_prompt`/`prompt_label`/`prompt_initial` (for free-text input actions), `confirm`/`confirm_message` (for destructive actions), `backup_target: Path | None` (file gets copied with a timestamp suffix before `run` executes), `group: str | None` (adjacent actions sharing a `group` render on one row).
3. The actual logic (`run` callable) lives in `tasks/system/<domain>.py`, not in `factory.py` — `factory.py` only assembles `SystemAction`s and returns `TaskResult`s from imported functions.
4. Add/extend a test in `tests/unit/test_factory.py` using the existing `_actions_in(system, distro, section_name)` / `_action_in(...)` helpers — these call `get_system_action_sections` directly, no App instantiation needed.

## Adding a brand-new section

1. Write a `_xxx_section(...) -> Section` function returning `(section_name, [SystemAction, ...])` (`Section = tuple[str, list[SystemAction]]`).
2. Wire it into `get_system_action_sections()`, gated on `system`/`distro` as appropriate (see the `if system in {...}:` blocks there).
3. Unless the section needs custom widgets (like dotfiles' tree or Start's markdown), it renders automatically via the generic `else` branch in `app.py::compose()` — no frontend change needed.
4. If it *does* need a custom widget, special-case it in `compose()` by section-name constant (see how `_DOTFILES_SECTION_NAME`/`_START_SECTION_NAME` are matched) — keep the section-name string in `app.py` a plain literal matching what the factory returns, that's the existing convention (not a shared import).

## Adding a new package-manager backend

1. Implement the `PackageManager` protocol (`tasks/managers/base.py`): `is_installed`, `install`, `update`, `upgrade`, `cleanup`.
2. Each method does its own `shutil.which(...)`/`sudo_non_interactive_ok()` check *locally in the manager's own module* (not through `_shared.py`) — this is deliberate, so unit tests can patch those checks at the manager's own module path.
3. Once a check fails, build the `TaskResult`/`InstallResult` via the shared helpers in `tasks/managers/_shared.py`: `command_details()`/`format_failed_command()`, `sudo_required_task_result()`/`sudo_required_install_result()`, `missing_executable_task_result()`/`missing_executable_install_result()`. Follow this "local check, shared result-builder" split rather than re-deriving the boilerplate.
4. Register it in `tasks/factory.py::_PACKAGE_MANAGER_FACTORY_BY_DISTRO` (maps `(distro, manager_name)` → manager class) and, if it should get its own tab/button, `_PRIMARY_MANAGERS_BY_DISTRO`.
5. Add packages for it under the right distro/manager/category in `src/personal_os_setup/config/packages.yaml`.

## Before opening a PR

Run `make test` and `make pre-commit` — see [[ship-feature]] for the full git/PR workflow. Never click a button wired to a real package-manager/system command from a test; build a synthetic `SystemAction` with an in-memory `run` lambda instead (see `tests/unit/test_app.py`'s confirm-flow test for the pattern).
