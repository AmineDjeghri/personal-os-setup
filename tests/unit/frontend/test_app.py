"""Unit tests for the Textual frontend, using Textual's headless Pilot harness.

These tests never exercise real package-manager/system actions (no real `brew`,
`apt`, `winget`, etc. commands run) -- only synthetic `SystemAction`s built with
in-memory `run` callables, so nothing on the host system is touched. Tests that
touch the "Sync dotfiles" tab patch `chezmoi_managed_paths`/`chezmoi_*` at their
`personal_os_setup.frontend.app` import site so they never shell out to the real
`chezmoi` binary or depend on this machine's actual tracked dotfiles.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from textual.widgets import (
    Button,
    LoadingIndicator,
    ProgressBar,
    SelectionList,
    TabbedContent,
    TabPane,
    Tree,
)

from personal_os_setup.frontend.app import PersonalOsSetupApp
from personal_os_setup.frontend.dotfiles_tree import DotfileTreeNode
from personal_os_setup.tasks.factory import SystemAction
from personal_os_setup.tasks.managers.base import InstallResult
from personal_os_setup.tasks.task import TaskResult

pytestmark = pytest.mark.asyncio

_FAKE_MANAGED_PATHS = [Path("/home/user/.p10k.zsh"), Path("/home/user/.zshrc")]


async def _activate_dotfiles_tab(app: PersonalOsSetupApp, pilot) -> None:
    """Switch to the (dynamically-id'd) "Sync dotfiles" TabPane so its buttons are clickable.

    TabbedContent only routes clicks to the active pane; the dotfiles pane's id is
    assigned from a shared counter (not a fixed id like "packages"), so we find it by
    walking up from the selection list it contains instead of guessing the id.
    """
    node = app.query_one("#dotfiles-selection-list")
    while node is not None and not isinstance(node, TabPane):
        node = node.parent
    assert node is not None, "could not find the 'Sync dotfiles' TabPane"
    app.query_one("#main-tabs", TabbedContent).active = node.id
    await pilot.pause()


def _all_leaf_paths(node) -> set[Path]:
    """Every file path in a dotfiles-tree node's subtree, gathered recursively."""
    data: DotfileTreeNode | None = node.data
    paths: set[Path] = set()
    if data is not None and data.is_file:
        paths.add(data.path)
    for child in node.children:
        paths |= _all_leaf_paths(child)
    return paths


def _find_dotfiles_node(app: PersonalOsSetupApp, path: Path):
    """Find the leaf tree node for `path` in the mounted dotfiles tree."""
    tree = app.query_one("#dotfiles-selection-list", Tree)

    def _walk(node):
        if node.data is not None and node.data.path == path:
            return node
        for child in node.children:
            found = _walk(child)
            if found is not None:
                return found
        return None

    found = _walk(tree.root)
    assert found is not None, f"no tree node for {path}"
    return found


def _check_dotfiles_path(app: PersonalOsSetupApp, path: Path) -> None:
    """Simulate the user checking a single file in the dotfiles tree."""
    node = _find_dotfiles_node(app, path)
    app.on_tree_node_selected(Tree.NodeSelected(node))


def _check_all_dotfiles(app: PersonalOsSetupApp) -> None:
    """Simulate the user checking the whole dotfiles tree (its root folder)."""
    tree = app.query_one("#dotfiles-selection-list", Tree)
    app.on_tree_node_selected(Tree.NodeSelected(tree.root))


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
        package_lists = app.query_one("#package-list-container").query(SelectionList)
        assert len(package_lists) == len(categories)


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
    """Uses a fake package manager -- never a real apt/brew/winget/etc. subprocess call."""
    app = PersonalOsSetupApp()
    fake_pm = type(
        "FakePM",
        (),
        {
            "is_installed": lambda self, name: False,
            "install": lambda self, name: InstallResult(ok=True, summary=f"Installed {name}"),
        },
    )()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "packages"
        await pilot.pause()
        selection_list = app.query_one("#package-list-container").query(SelectionList).first()
        selection_list.select(selection_list._options[0])
        await pilot.pause()

        with patch("personal_os_setup.frontend.app.get_package_manager", return_value=fake_pm):
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
        app.query_one("#main-tabs", TabbedContent).active = "packages"
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


async def test_dotfiles_list_is_populated_with_nothing_pre_selected():
    """Files are listed but unchecked by default -- the user opts in to what they sync."""
    with patch(
        "personal_os_setup.frontend.app.chezmoi_managed_paths",
        return_value=_FAKE_MANAGED_PATHS,
    ):
        app = PersonalOsSetupApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            tree = app.query_one("#dotfiles-selection-list", Tree)
            assert _all_leaf_paths(tree.root) == set(_FAKE_MANAGED_PATHS)
            assert app._dotfiles_selected == set()


async def test_dotfiles_action_with_nothing_selected_notifies_and_stays_idle():
    with patch(
        "personal_os_setup.frontend.app.chezmoi_managed_paths",
        return_value=_FAKE_MANAGED_PATHS,
    ):
        app = PersonalOsSetupApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await _activate_dotfiles_tab(app, pilot)
            await pilot.click("#btn-dotfiles-diff")
            await pilot.pause()
            assert app.is_busy is False


async def test_dotfiles_diff_selected_runs_with_the_checked_paths_only():
    with patch(
        "personal_os_setup.frontend.app.chezmoi_managed_paths",
        return_value=_FAKE_MANAGED_PATHS,
    ):
        app = PersonalOsSetupApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await _activate_dotfiles_tab(app, pilot)
            _check_dotfiles_path(app, _FAKE_MANAGED_PATHS[0])
            await pilot.pause()

            mock_diff = TaskResult(ok=True, summary="chezmoi diff: no changes")
            with patch(
                "personal_os_setup.frontend.app.chezmoi_diff", return_value=mock_diff
            ) as fake_diff:
                await pilot.click("#btn-dotfiles-diff")
                for _ in range(20):
                    await pilot.pause(0.1)
                    if not app.is_busy:
                        break

            assert app.is_busy is False
            fake_diff.assert_called_once_with([_FAKE_MANAGED_PATHS[0]])


async def test_dotfiles_apply_selected_requires_confirmation():
    with patch(
        "personal_os_setup.frontend.app.chezmoi_managed_paths",
        return_value=_FAKE_MANAGED_PATHS,
    ):
        app = PersonalOsSetupApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await _activate_dotfiles_tab(app, pilot)
            _check_all_dotfiles(app)
            await pilot.pause()

            mock_apply = TaskResult(ok=True, summary="chezmoi apply: ok")
            with patch(
                "personal_os_setup.frontend.app.chezmoi_apply", return_value=mock_apply
            ) as fake_apply:
                # "No" should dismiss without applying anything.
                await pilot.click("#btn-dotfiles-apply")
                await pilot.pause(0.2)
                await pilot.click("#confirm-no")
                await pilot.pause(0.2)
                fake_apply.assert_not_called()
                assert app.is_busy is False

                # "Yes" should apply the (still fully-selected) list.
                await pilot.click("#btn-dotfiles-apply")
                await pilot.pause(0.2)
                await pilot.click("#confirm-yes")
                for _ in range(20):
                    await pilot.pause(0.1)
                    if not app.is_busy:
                        break

            # Selected paths come from a set, so compare unordered.
            fake_apply.assert_called_once()
            assert set(fake_apply.call_args.args[0]) == set(_FAKE_MANAGED_PATHS)
            assert app.is_busy is False


async def test_dotfiles_forget_selected_refreshes_the_list():
    """The checklist should refresh after a mutating action (forget) completes.

    It should reflect the now-current set of chezmoi-managed paths rather than the
    stale one it mounted with.
    """
    refreshed_paths = [_FAKE_MANAGED_PATHS[0]]
    with patch(
        "personal_os_setup.frontend.app.chezmoi_managed_paths",
        side_effect=[_FAKE_MANAGED_PATHS, refreshed_paths],
    ):
        app = PersonalOsSetupApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await _activate_dotfiles_tab(app, pilot)
            _check_all_dotfiles(app)
            await pilot.pause()

            mock_forget = TaskResult(ok=True, summary="chezmoi forget: ok")
            with patch("personal_os_setup.frontend.app.chezmoi_forget", return_value=mock_forget):
                await pilot.click("#btn-dotfiles-forget")
                await pilot.pause(0.2)
                await pilot.click("#confirm-yes")
                for _ in range(20):
                    await pilot.pause(0.1)
                    if not app.is_busy:
                        break

            tree = app.query_one("#dotfiles-selection-list", Tree)
            assert _all_leaf_paths(tree.root) == set(refreshed_paths)
