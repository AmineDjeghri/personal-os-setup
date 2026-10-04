# NiceGUI test-harness recipes (all verified end-to-end)

Sources read for these: `nicegui/testing/user_plugin.py`, `general_fixtures.py`, `user_simulation.py`,
`user_interaction.py` in the installed package — re-read them if the API looks different in a newer
release.

## Layout of a throwaway probe

```
<scratch>/ng-probe/
  pyproject.toml     # [tool.pytest.ini_options] main_file = "<abs path to app main.py>"
  conftest.py        # one of the variants below
  probe_main.py      # only for the isolated variant / when testing a stand-in page
  test_x.py
```

Run it with the target repo's interpreter, so the frontend package resolves to that repo's source:

```bash
cd <scratch>/ng-probe && BACKEND_URL=http://127.0.0.1:9 \
  /path/to/repo/.venv/bin/python -m pytest -q
```

`main_file` is a pytest ini option; it is resolved as `config.inipath.parent / main_file`, and can also be
set per test with `@pytest.mark.nicegui_main_file("path/to/main.py")`.

## Variant A — keep `asyncio_mode = "strict"` (preferred for the user's repos)

`tests/frontend/conftest.py`:

```python
from collections.abc import AsyncGenerator

import pytest_asyncio
from nicegui.testing.general_fixtures import (
    get_path_to_main_file,
    pytest_addoption,  # noqa: F401  # registers the `main_file` ini option
    pytest_configure,  # noqa: F401  # isolated storage path for the session
)
from nicegui.testing.user import User
from nicegui.testing.user_simulation import user_simulation


@pytest_asyncio.fixture
async def user(request) -> AsyncGenerator[User]:
    async with user_simulation(main_file=get_path_to_main_file(request)) as user:
        yield user
```

Tests keep the repo's existing style and must carry the marker:

```python
import pytest
from nicegui.testing.user import User


@pytest.mark.asyncio
async def test_page_boots(user: User) -> None:
    await user.open("/")
    await user.should_see("Training Mode")
```

The wrapper drops the plugin fixture's caplog ERROR check; add it back if wanted:

```python
    logs = [r for r in caplog.get_records("call") if r.levelname == "ERROR"]
    if logs:
        pytest.fail("There were unexpected ERROR logs.", pytrace=False)
```

## Variant B — `asyncio_mode = "auto"`, use the plugin fixture directly

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
main_file = "jym-frontend/src/jym_frontend/main.py"
```

```python
# conftest.py
pytest_plugins = ["nicegui.testing.user_plugin"]
```

```python
async def test_page_boots(user) -> None:  # the user fixture is async; no marker needed under auto
    await user.open("/")
    await user.should_see("Training Mode")
```

Verified: switching a repo to `auto` leaves tests that use an explicit `@pytest.mark.asyncio` and plain
async fixtures passing.

`pytest_plugins = ["nicegui.testing.plugin"]` instead pulls in the plugin *and* the Selenium `Screen`
fixture — only do that where a real browser is available.

## Variant C — isolated component test, no main file, no app import

Best for component-level tests (and the only clean way to read state your component mutates):

```python
from collections.abc import AsyncGenerator

import pytest
from nicegui import ui
from nicegui.testing.user import User
from nicegui.testing.user_simulation import user_simulation

CALLBACKS: list[str] = []


def selector_root() -> None:
    selector = create_exercise_selector(lambda name: CALLBACKS.append(name))
    selector.exercises = ExerciseList(exercises=[...])   # inject data, no backend
    selector.create_selector_ui()


@pytest.fixture
async def isolated_user() -> AsyncGenerator[User]:
    CALLBACKS.clear()
    async with user_simulation(root=selector_root) as user:
        yield user


async def test_selecting_an_exercise(isolated_user: User) -> None:
    await isolated_user.open("/")
    await isolated_user.should_see("Select Exercise")
    isolated_user.find(kind=ui.card).trigger("click")   # the element owning the handler
    assert CALLBACKS == ["squat"]
```

Under `asyncio_mode = "strict"` decorate this fixture with `@pytest_asyncio.fixture` as in Variant A.
`user_simulation(root=...)` calls `prepare_simulation()` + `ui.run(root, storage_secret="simulated secret")`<!-- pragma: allowlist secret -->
internally, so no `ui.run()` guard is needed on `root` — but a `main_file` app does need it
(`if __name__ in {"__main__", "__mp_main__"}: ui.run()`), because runpy loads it as `__main__`.

## Interaction API worth knowing

- `await user.open("/[path]")`, `await user.should_see("text")`, `await user.should_not_see(...)`,
  `user.find("text")` / `user.find(kind=ui.card)` / `user.find(marker="...")`.
- On a found element: `.click()`, `.trigger("click")`, `.trigger("keydown.enter")`, `.type("text")`,
  `.clear()`. `trigger` walks only that element's own `_event_listeners`, which is why the element must be
  the one carrying the handler.
- `os.environ["NICEGUI_USER_SIMULATION"]` is set while the harness runs; the app's `ui.run()` returns
  immediately instead of serving.

## What the probes measured (NiceGUI 3.17.1, Python 3.13, headless container)

- 4 tests including two `user`-driven ones: 0.34 s total; one page test on its own: 0.20 s.
- Same set with `--numprocesses=2`: 2.32 s (worker startup dominates) — xdist-safe.
- A page test reproduced an `ImportError` from the app's `main.py` at fixture setup, i.e. before any
  assertion ran — that is the boot-smoke-test value.

## Shipping the tests into a repo that also has non-harness tests

Layout that worked (jym, `tests/frontend/` — one structure, no test file left in `tests/`):

```
tests/frontend/
  conftest.py             # fixtures only (no tests)
  test_main_page.py       # page boot + in-page interaction, driven through main_file
  test_<component>.py     # component behaviour, isolated root= with injected data
  test_<smoke>.py         # a pre-existing end-to-end server smoke test, moved in
```

- Inject data through the component's own models; never import the app's main module to read state.
- One fixture per scenario (`selector_user` with data, `empty_selector_user` without) beats flags on a
  single fixture — each fixture then reads as one test setup.
- After the move, run the directory serial *and* `--numprocesses=4`: the move changes collection order, and
  that is what exposes order-dependence.

```python
@pytest_asyncio.fixture
async def selector_user(selections: list[str]) -> AsyncIterator[User]:
    def root() -> None:
        selector = create_exercise_selector(selections.append)
        selector.exercises = EXERCISES          # injected, no backend
        selector.selected_exercise = "pushup"
        selector.create_selector_ui()

    async with user_simulation(root=root) as user:
        yield user
```

with a plain sync fixture for the observable:

```python
@pytest.fixture
def selections() -> list[str]:
    return []
```

Then `selector_user.find(kind=ui.card).trigger("click")` followed by
`assert selections == ["squat"]` (the found cards without a click handler are no-ops, so triggering on the
whole set is safe) and `await selector_user.should_see("Selected: Squats")`.

### The non-harness test that asserts on the global `app`

`user_simulation` calls `nicegui_reset_globals`, so a pre-existing assertion like

```python
assert "/" in [str(route.path) for route in app.routes]
```

holds only while it runs before the harness tests. Make it self-sufficient instead of order-dependent:

```python
def test_main_page_is_registered() -> None:
    import importlib

    import jym_frontend.main
    from nicegui import app

    importlib.reload(jym_frontend.main)  # re-register the pages on the reset app
    assert "/" in [str(route.path) for route in app.routes]
```

## Reproducing a CI-only fixture error locally (A/B)

```bash
uv run pytest tests/<file>.py --noconftest -o addopts="" -q
```

`--noconftest` drops the conftest whose hook turns "service unreachable" into a skip, and `-o addopts=""`
drops the repo's `--strict-markers`/`-m` addopts that would reject the now-unregistered markers. Expected
pair on an async fixture that is wired wrong vs fixed:

- before: `ERROR at setup of test_x` — *"requested an async fixture 'cleanup_db' with autouse=True, with no
  plugin or hook that handled it"*
- after: the same test runs, and the only failure is the missing service —
  `ERROR at teardown of test_x — pymongo.errors.ServerSelectionTimeoutError: localhost:27017: [Errno 111]
  Connection refused`

The second one is the pass condition for the fixture fix; never report it as verified because "CI has
MongoDB".
