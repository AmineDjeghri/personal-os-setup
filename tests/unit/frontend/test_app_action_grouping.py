"""Unit tests for `PersonalOsSetupApp._group_actions_into_rows` (pure function, no Textual pilot)."""

from __future__ import annotations

from personal_os_setup.frontend.app import PersonalOsSetupApp
from personal_os_setup.tasks.factory import SystemAction
from personal_os_setup.tasks.task import TaskResult


def _fake_action(label: str, group: str | None = None) -> SystemAction:
    return SystemAction(label=label, run=lambda: TaskResult(ok=True, summary=""), group=group)


def test_group_actions_into_rows_merges_adjacent_same_group_actions():
    actions = [
        _fake_action("detect nvidia", "nvidia"),
        _fake_action("setup nvidia", "nvidia"),
        _fake_action("detect cuda", "cuda"),
    ]
    rows = PersonalOsSetupApp._group_actions_into_rows(actions)
    assert [[a.label for a in row] for row in rows] == [
        ["detect nvidia", "setup nvidia"],
        ["detect cuda"],
    ]


def test_group_actions_into_rows_keeps_ungrouped_actions_on_separate_rows():
    actions = [_fake_action("a"), _fake_action("b"), _fake_action("c")]
    rows = PersonalOsSetupApp._group_actions_into_rows(actions)
    assert [[a.label for a in row] for row in rows] == [["a"], ["b"], ["c"]]


def test_group_actions_into_rows_does_not_merge_non_adjacent_same_group():
    actions = [
        _fake_action("update", "apt"),
        _fake_action("open documentation site", None),
        _fake_action("cleanup", "apt"),
    ]
    rows = PersonalOsSetupApp._group_actions_into_rows(actions)
    assert [[a.label for a in row] for row in rows] == [
        ["update"],
        ["open documentation site"],
        ["cleanup"],
    ]
