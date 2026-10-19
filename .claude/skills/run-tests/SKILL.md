---
name: run-tests
description: Use when writing or running tests in this repo, or when a test fails unexpectedly — "add a test", "run the tests", "why did this test fail/get skipped", "test the new manager/action". Covers make test vs make test-integration (the latter is destructive against the host!), the three test suites, and the exact mocking/patching conventions used across tests/unit.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Testing in personal-os-setup

There are **three** separate test setups in this repo — know which one you're in before running anything.

⚠️ `make test-integration` and `tests/archlinux/` run **real, host-mutating commands** (package installs/upgrades). Never run either without confirming with the user first, even if they already asked you to "run the tests" generically — that request defaults to `make test` (unit only). Canon: `AGENTS.md` § "Safety: confirm before system-mutating actions (MANDATORY)".

## 1. `tests/unit/` — `make test` (safe, run this freely)

`uv run pytest tests/unit --numprocesses=$(N)` — parallel via pytest-xdist, `N` defaulting to 4 (`make test N=1` for single-worker debugging). No `conftest.py` exists — fixtures are ad hoc per-file (`tmp_path`, `monkeypatch`) or hand-rolled fakes, not shared. Exit code 5 ("no tests collected") is treated as success by `test.mk`.

**Mocking conventions — copy these exactly, don't improvise:**

- **Patch at the import site, not the source module.** Package-manager tests patch `"personal_os_setup.tasks.managers.<backend>.run"` / `"...sudo_non_interactive_ok"` — wherever the name was imported *into*, matching the "local check, shared result-builder" split documented in [[add-system-action]]. `shutil.which` is the exception, patched at its global path (`"shutil.which"`), since managers call it directly rather than importing a bound name.
- Frontend tests patch chezmoi functions at `personal_os_setup.frontend.app.chezmoi_*` (where `app.py` imports them by name), not at `tasks.system.chezmoi` where they're defined.
- Fake a `subprocess.CompletedProcess` with `MagicMock(returncode=..., stdout=..., stderr=...)` — never shell out for real in a unit test.
- For a function calling `shutil.which`/`run` multiple times with different expected results, use `side_effect=iter([...])`.
- For a fake package manager, duck-type it: `type("FakePM", (), {"is_installed": ..., "install": ...})()` — used in both `test_app.py` and `test_factory.py`, no real manager subclass needed.
- **Never click a button/action wired to a real system command.** Build a synthetic `SystemAction(label=..., run=lambda: TaskResult(...))` with an in-memory `run` and inject it, the way `test_app.py`'s confirm-flow test does.
- Textual (`test_app.py`): `pytestmark = pytest.mark.asyncio` at **module level** is required — `asyncio_mode = "strict"` in `pyproject.toml` means an unmarked `async def test_...` silently breaks/skips. To wait for a `@work(thread=True)` worker inside a test, poll — there's no awaitable for a background worker's completion:

  ```python
  for _ in range(20):
      await pilot.pause(0.1)
      if not app.is_busy:
          break
  ```
- To find a dynamically-id'd `TabPane` (ids come from a shared `itertools.count()` in `app.py`), walk up from a known child widget by id (e.g. `#dotfiles-selection-list`) rather than hardcoding a tab id.
- Settings/env-var tests need `monkeypatch.setenv(...)` **plus** `importlib.reload(settings_module)` — `pydantic-settings` reads env at import time, so `setenv` alone doesn't affect an already-imported module.
- Adding a manager string to `packages.yaml` without registering a backend in `factory.py` fails `test_detect_os.py::TestPackagesYaml` specifically — it's the only guardrail (see [[repo-gotchas]]).

## 2. `tests/integration/` — `make test-integration` (⚠️ destructive)

Each module is OS-gated: `pytestmark = pytest.mark.skipif(detect_os().distro != "ubuntu", ...)` (or `macos`/`cachyos`). On a non-matching machine you get "no tests collected" (exit 5, treated as success) — it looks like it passed although nothing ran.

**On a matching machine these run real commands**: `apt-get install curl`, real `apt update`/`upgrade`/`autoremove`, equivalents for brew/pacman. CI runs them on disposable `ubuntu-26.04`/`macos-latest` runners, never on your dev box — don't run them locally unless real package installs/upgrades are fine.

## 3. `tests/archlinux/` — manual Docker smoke test, not wired to `make`/CI

`Dockerfile` + `run.sh`, a third harness for Arch/CachyOS smoke-testing. Not part of any target or workflow; run it manually via its own `README.md`.

## Before trusting a "tests pass" claim

`make pre-commit` and `make test` together are the CI-equivalent local check *except* for the commit-message format (only checked at real `git commit` time, see [[ship-feature]]) and the OS-specific integration suite (only checked on matching CI runners).
