---
name: run-tests
description: Use when writing/running tests or interpreting coverage and integration completeness in personal-os-setup.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Testing in personal-os-setup

Read `tests/README.md` and `docs/developer/4.testing.md` for the test map and current targets.

## Safe local checks

1. `make test-local` / `make test` runs `tests/unit` and `tests/skills` with xdist (`N=4`, or `N=1`
   for debugging). Plain `pytest` has the same safe testpaths. Empty collection fails.
2. `make test-all` adds real wheel/sdist identity/resource checks and isolated wheel installation.
   The console callable loads without starting the app (startup can self-update and prepare sudo).
3. `make test-coverage` reuses `test-all` with separate Python coverage in `reports/coverage.xml`.
   Coverage does not establish OS integration completeness; no threshold is imposed yet.
4. `make check` runs static/docs hooks and `test-all`. `make install-dev` and
   `make pre-commit-install` prepare the environment/hooks separately. Checks do not install them.

## Isolation conventions

- Patch at the import site: frontend chezmoi functions at `personal_os_setup.frontend.app.chezmoi_*`,
  managers at `personal_os_setup.tasks.managers.<backend>.run` / `sudo_non_interactive_ok`.
  `shutil.which` is patched globally because managers access it through that module.
- Frontend tests live in `tests/unit/frontend`; its shared autouse fixture supplies a synthetic
  catalog, sections and managed paths, and fails on unexpected real manager/chezmoi actions.
  Override only the calls a test intentionally exercises. Never wire tests to real system actions.
- Fake results with `TaskResult`, `InstallResult` or `MagicMock(returncode=..., stdout=..., stderr=...)`.
  Use `tmp_path` and `monkeypatch`; xdist workers must share no mutable state.
- Textual async tests need `pytest.mark.asyncio` in strict mode. Poll `app.is_busy` with Pilot pauses
  for thread workers, and find dynamic TabPanes through a known child rather than fixed generated IDs.
- Settings tests set environment values and reload the settings module; values are read at import.
- Release regressions use explicit Git/uv/Make/GitHub stubs. Docs generators use temporary source/output
  trees; integration-report tests launch pytest only against synthetic modules.
- `tests/skills` deploys into temporary roots with a fake installer. POSIX Bash/jq are required;
  its chezmoi case skips when absent, and native Windows skips the POSIX harness.

## OS validation boundary

`make test-integration` and `tests/archlinux` can run real host-mutating commands on Linux/macOS.
Never run either without explicit authorization; a generic request to test means safe local suites.
Windows integration is deliberately read-only.

Hosted CI requires self-contained tests and executed integration on Ubuntu/macOS/Windows.
Other operating systems' skips are expected, but zero passing integration tests fail through
`scripts/integration_results.py`. Collection-only output is diagnostic, not completed validation.
CachyOS integration is not exercised by hosted CI; the Arch container is an interactive sandbox.
A local `make check` pass does not establish that required CI passed.
