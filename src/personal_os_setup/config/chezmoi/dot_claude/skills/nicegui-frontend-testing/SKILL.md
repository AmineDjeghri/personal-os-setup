---
name: nicegui-frontend-testing
description: "Use when testing a NiceGUI frontend (user fixture)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [testing, nicegui, pytest, frontend, ui]
    related_skills: [project-templates, coding-workflow]
---

# Testing a NiceGUI frontend (headless, no browser)

NiceGUI ships its own pytest harness (`nicegui.testing`): the `user` fixture drives the app's real pages
through an in-process httpx ASGI transport. No browser, no Selenium, no running backend, no services —
~0.2 s per test and xdist-safe. It is present in every NiceGUI 3.x the user's repos pin (3.14, 3.17).
Verified recipes: `references/user-fixture-recipes.md`.

## When to Use

- Adding tests to a NiceGUI app, or asked whether frontend tests are worth it.
- Writing or debugging a `user`-based test, or the `conftest.py` that hosts one.
- A NiceGUI page fails to boot and you want a test that would have caught it.
- Porting the harness across the user's NiceGUI apps (jym, generative-ai-project-template, add-on frontends).

## What is worth testing — decide before writing anything

- **One page-boot smoke test per app, first.** `await user.open("/")` plus a few `should_see` labels. It is
the only test that catches the whole class of "a refactor dropped a symbol that `main.py` and its
components still import": the app dies at startup and nothing else in the suite notices.
- **Component tests where there is logic**: callback wiring, selection/state update, error paths in
form/auth components, the failure branch of a data fetch.
- **Not worth it**: assertions on styling / Quasar props (churn, no behaviour), and the Selenium `Screen`
fixture (needs Chrome in CI for little gain). JS-only paths (webcam, canvas, vision) stay untested either
way — say so plainly instead of implying coverage.
- **Cheap**: no new dependency (pytest-asyncio is already in these repos' dev groups) and no services, so
the tests belong in the parallel / no-service stage of the repo's runner (`just test`, `make test`).

## Procedure

1. **Check the repo can host the harness**: a venv with the frontend package installed (a repo with no
   `.venv` needs `uv sync` first) and `python -c "import nicegui.testing"`. The harness executes the app, so
   it needs the app's own dependencies, not just nicegui.
2. **Probe in a scratch dir outside the repo**: a `pyproject.toml` holding `[tool.pytest.ini_options]`
   (`main_file = "<absolute path to the app's main.py>"` and the asyncio mode from step 3), a `conftest.py`,
   and one test file. An absolute `main_file` works — a relative one resolves against the pytest rootdir
   (`config.inipath.parent`).
3. **Decide the asyncio mode** — keep the repo's `strict` and add the wrapper fixture, or switch to `auto`.
   See the first pitfall; do not skip this, it is the difference between a 1-second probe and an hour of
   confusion.
4. **Get first-hand boot evidence before writing any test**: run the exact start command the repo's
   `just`/`make`/compose target uses for that app and read the traceback. Never infer boot breakage from
   reading imports. If it does fail, check whether the base branch shares the defect
   (`git show <base>:<path/to/module.py> | grep -c <SYMBOL>`) so you report it as pre-existing instead of
   blaming the current branch.
   **Recovering what a refactor dropped:** `git log -S '<symbol>' --all` misses a removal that happened
   inside a merge commit — add `--full-history -m` to surface the merge that lost it. A complete copy usually
   survives on another ref (`git show <other-ref>:<new-path>/<file>.py`), so diff the survivor against every
   symbol the code actually uses (`grep -rho 'ClassName\.[A-Z_]*' --include='*.py' . | sort -u`) before
   restoring: the survivor can be a later restyle with different values, and an older copy can be missing
   constants added since. Restore the maintained copy, tell the user which source you took, and probe it
   (scratch runner, repo untouched) before writing the tests.
5. **Write the tests in the repo only after the user agrees**, into the repo's existing test tree, and run
   them through the repo's own runner.

## Pitfalls

- **`asyncio_mode = "strict"` disables the harness fixtures** (and it is the mode both of the user's
  NiceGUI repos set). pytest errors at setup: *"requested an async fixture 'user', with no plugin or hook
  that handled it"* — the plugin's fixtures are plain `@pytest.fixture` async generators. Two working
  options: keep `strict` and add an 8-line `@pytest_asyncio.fixture` wrapper in the frontend test dir's
  `conftest.py` (preferred — it matches the `@pytest.mark.asyncio` style these repos already use, and every
  frontend test then needs that marker), or set `asyncio_mode = "auto"` (verified: existing tests with an
  explicit `@pytest.mark.asyncio` and plain async fixtures keep passing). Exact code in the reference.
- **The main file must be runnable by `runpy` as `__main__`.** Without
  `if __name__ in {"__main__", "__mp_main__"}: ui.run()` the harness aborts with `RuntimeError: You must
  call ui.run() to start the server`. Both repos' `main.py` already carry the guard — keep it when adding
  one.
- **Never import the app's main file to read its state.** The harness executes it via `runpy` as
  `__main__`, so a module-level object (callback list, counter) is a *different* module instance from the
  one the test imports — the assertion sees it empty even though the click worked. Assert on rendered UI
  (`should_see`) or use the isolated pattern: `user_simulation(root=<function defined in the test module>)`
  with the component built inside that function.
- **Trigger the event on the element that owns the listener.** `user.find(kind=ui.card).trigger("click")`
  fires the listeners registered on the found element only; triggering `click` on a child label does
  nothing, because the simulated user does not bubble events up the tree. Find the element that carries the
  handler, not the text you want to click.
- **Point the app at a dead backend while probing** (`BACKEND_URL=http://127.0.0.1:9` or the repo's
  equivalent): a page that calls the API on boot turns a 0.2 s test into a hang if a service happens to be
  listening. The swallowing path is itself worth asserting.
- **The plugin's `user` fixture fails a test that logs an ERROR record** (it inspects caplog). A page that
  turns a failure into a log line therefore fails by design — fix the page or assert on that behaviour
  explicitly.
- **The harness resets NiceGUI's global state, so it makes its neighbours order-dependent.**
  `user_simulation` calls `nicegui_reset_globals`; a non-harness test that asserts on the global
  `app` (e.g. `"/" in [r.path for r in app.routes]`) then passes or fails purely on collection order. Rule:
  never assert on the global `app` next to harness tests — re-register inside the test
  (`importlib.reload(<the app's main module>)`) so the assertion stands on its own. Corollary: after moving
  or adding a test file, run the whole test directory serial *and* `--numprocesses=N`; a move can reorder
  collection and expose order-dependence the single file never showed.
- **Every async fixture in the suite needs `pytest_asyncio.fixture`, not only the harness one.** Under
  `strict` a plain `@pytest.fixture` on an async function — including `autouse=True` — is a setup error for
  each requesting test (*"requested an async fixture 'X' with autouse=True, with no plugin or hook that
  handled it"*). Sweep the whole tree instead of the file in hand:
  `grep -rn -A3 "@pytest.fixture" tests/ | grep -E "@pytest.fixture|async def"`.
- **A service-gated module hides its own breakage locally.** If the module is skipped when MongoDB/Ollama
  is absent, the error surfaces only in CI. Reproduce it in one run by dropping the conftest that applies
  the skip and the addopts that enforce markers:
  `uv run pytest tests/<file>.py --noconftest -o addopts="" -q`. A/B it — the failure must *change* from the
  pytest-asyncio/fixture error to a service-connection error (`pymongo … Connection refused`); only that
  change proves the plumbing was fixed and the remaining failure is the missing service.
- **`should_see` polls ~0.1 s × `retries`.** An assertion against a widget that renders after a deliberate
  pause ("assistant is thinking") needs `retries=30` on that assertion — raise it there rather than slowing
  the whole test.
- **`ui.page_routes` does not exist in NiceGUI 3.** Enumerate routes on the FastAPI app object instead:
  `"/" in [str(r.path) for r in nicegui.app.routes]`. `AttributeError: module 'nicegui.ui' has no attribute
  'page_routes'` is the tell — reach for `app`, never `ui`, for route introspection.
- **A real-server smoke test launched from pytest inherits `PYTEST_CURRENT_TEST` and dies at `ui.run()`.**
  `nicegui.helpers.is_pytest()` is literally `'PYTEST_CURRENT_TEST' in os.environ`, and when it is true
  `ui.run()` ignores your `port=` and reads `int(os.environ['NICEGUI_SCREEN_TEST_PORT'])` →
  `KeyError: 'NICEGUI_SCREEN_TEST_PORT'`. Spawn the child with a cleaned env:
  `env={k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"}`. Only reach for the subprocess
  server when you need the real socket; rendering assertions belong on the in-process `user_simulation` path.
- **A test that starts a real server carries a `storage_secret`, which the repo's secret scanner flags.**
  `ui.run(..., storage_secret="…")` in a subprocess smoke test trips `detect-secrets` ("Secret Keyword").
  Allowlist inline with `# pragma: allowlist secret` — the repo convention; never exclude the file.
  Related trap: a file that was *untracked* is scanned for the first time when you first commit it, so an
  innocent move/add can turn CI red over a string that predates your change.

## Running probes in this environment

- Keep each probe ONE simple command. Compound chains and `for` loops over git branches trip the approval
  prompt here and time out; a timed-out prompt is not consent, so the probe is lost — report the gap
  instead of retrying it.
- Never write test files into the user's repos to run a probe: scratch dirs only, then offer the real
  implementation and wait for a go-ahead (commits in his repos need per-action approval).
- **Once the tests are pushed, the CI run is the oracle — read it, do not re-run locally "to be sure".**
  `gh run view <id> --json status,conclusion,jobs -q '{status, conclusion, jobs: [.jobs[] | {name, conclusion}]}'`
  gives job-by-job truth (a green badge on a job that `needs:` another one tells you nothing), then confirm
  the *specific* test in the log rather than trusting the badge:
  `gh run view <id> --log 2>/dev/null | grep -E "<test name>|passed"`. When he says he will wait for CI,
  stop the local runs and report from the run — a local reproduction of a model- or service-dependent test
  does not predict the runner's result.

## Answering "can we add X tests, is it worth it?" for this user

- Lead with the verdict, then the cost (deps, runtime, where the tests land in CI) in a few bullets; the
  mechanics belong in this skill, not in the reply.
- If the probe surfaced a real defect, state the defect in one line FIRST — with the exact command and
  traceback line — before answering whether the tests are worth it. A boot-broken app reorders the whole
  answer.
- Do the feasibility probe before answering; "worth it" answered from theory is the failure mode.
