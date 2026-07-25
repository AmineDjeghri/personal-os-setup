"""Unit tests for the Textual frontend, using Textual's headless Pilot harness.

These tests never exercise real package-manager/system actions (no real `brew`,
`apt`, `winget`, etc. commands run) -- only synthetic `SystemAction`s built with
in-memory `run` callables, so nothing on the host system is touched.
"""

from __future__ import annotations

import pytest
from textual.widgets import Button, LoadingIndicator, ProgressBar, SelectionList

from personal_os_setup.frontend.app import PersonalOsSetupApp
from personal_os_setup.tasks.factory import SystemAction
from personal_os_setup.tasks.task import TaskResult

pytestmark = pytest.mark.asyncio


async def test_app_mounts_with_packages_and_logs_tabs():
    app = PersonalOsSetupApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        tab_ids = [t.id for t in app.query("TabPane")]
        assert "packages" in tab_ids
        assert "logs" in tab_ids
        lists = app.query(SelectionList)
        assert len(lists) > 0
        assert sum(lst.option_count for lst in lists) > 0


async def test_packages_are_grouped_by_category_into_collapsibles():
    app = PersonalOsSetupApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        categories = app._grouped_packages()
        collapsibles = app.query(".package-category")
        assert len(collapsibles) == len(categories)
        assert len(app.query(SelectionList)) == len(categories)


async def test_is_busy_watcher_disables_buttons_and_toggles_indicator():
    app = PersonalOsSetupApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        indicator = app.query_one("#busy-indicator", LoadingIndicator)
        assert indicator.display is False
        assert not any(b.disabled for b in app._buttons)

        app.is_busy = True
        await pilot.pause()
        assert indicator.display is True
        assert all(b.disabled for b in app._buttons)

        app.is_busy = False
        await pilot.pause()
        assert indicator.display is False
        assert not any(b.disabled for b in app._buttons)


async def test_install_selected_runs_worker_and_advances_progress():
    app = PersonalOsSetupApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        selection_list = app.query(SelectionList).first()
        selection_list.select(selection_list._options[0])
        await pilot.pause()

        await pilot.click("#btn-install")
        for _ in range(20):
            await pilot.pause(0.1)
            if not app.is_busy:
                break

        assert app.is_busy is False
        progress = app.query_one("#install-progress", ProgressBar)
        assert progress.progress == progress.total == 1


async def test_install_selected_with_nothing_selected_notifies_and_stays_idle():
    app = PersonalOsSetupApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#btn-install")
        await pilot.pause()
        assert app.is_busy is False


async def test_confirm_action_no_does_not_run_and_yes_does():
    app = PersonalOsSetupApp()
    async with app.run_test() as pilot:
        await pilot.pause()

        calls: list[int] = []
        dummy = SystemAction(
            label="dummy confirm action",
            run=lambda: (calls.append(1), TaskResult(ok=True, summary="dummy ran"))[1],
            confirm=True,
            confirm_message="Proceed with dummy?",
        )
        button_id = "test-dummy-btn"
        app._action_by_button_id[button_id] = ("dummy-section", dummy)
        button = Button("dummy", id=button_id)
        await app.query_one("#packages-toolbar").mount(button)
        app._buttons.append(button)
        await pilot.pause()

        # "No" should dismiss without running the action.
        await pilot.click(f"#{button_id}")
        await pilot.pause(0.2)
        await pilot.click("#confirm-no")
        await pilot.pause(0.2)
        assert calls == []
        assert app.is_busy is False

        # "Yes" should run it.
        await pilot.click(f"#{button_id}")
        await pilot.pause(0.2)
        await pilot.click("#confirm-yes")
        for _ in range(10):
            await pilot.pause(0.1)
            if not app.is_busy:
                break
        assert calls == [1]
        assert app.is_busy is False


async def test_clear_log_action_does_not_raise():
    app = PersonalOsSetupApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app._log("a message")
        await pilot.pause()
        await app.run_action("clear_log")
        await pilot.pause()
