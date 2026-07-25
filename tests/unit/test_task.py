"""Unit tests for tasks/task.py — TaskResult, Task, run_tasks()."""

from __future__ import annotations


from personal_os_setup.tasks.task import Task, TaskResult, run_tasks


def _make_task(*, ok: bool, already_applied: bool = False) -> Task:
    return Task(
        id="test-task",
        title="Test Task",
        requires_admin=False,
        check=lambda: already_applied,
        run=lambda: TaskResult(ok=ok, summary="done" if ok else "failed", details=""),
    )


class TestTaskResult:
    """Tests for the TaskResult value object."""

    def test_ok_true(self):
        """Details should default to an empty string."""
        r = TaskResult(ok=True, summary="success")
        assert r.ok is True
        assert r.summary == "success"
        assert r.details == ""

    def test_ok_false_with_details(self):
        """Details field should be stored verbatim."""
        r = TaskResult(ok=False, summary="fail", details="something went wrong")
        assert r.ok is False
        assert r.details == "something went wrong"


class TestRunTasks:
    """Tests for the run_tasks() orchestrator."""

    def test_successful_task(self):
        """A task whose run() returns ok=True should produce an ok result."""
        task = _make_task(ok=True)
        results = run_tasks([task])
        assert len(results) == 1
        assert results[0].ok is True

    def test_failed_task(self):
        """A task whose run() returns ok=False should produce a failed result."""
        task = _make_task(ok=False)
        results = run_tasks([task])
        assert len(results) == 1
        assert results[0].ok is False

    def test_already_applied_is_skipped(self):
        """A task whose check() returns True should be skipped without calling run()."""
        task = _make_task(ok=True, already_applied=True)
        results = run_tasks([task])
        assert len(results) == 1
        assert results[0].ok is True
        assert "already applied" in results[0].summary

    def test_exception_is_caught(self):
        """An exception raised inside run() should be caught and stored in details."""

        def _raise() -> TaskResult:
            raise RuntimeError("boom")

        task = Task(
            id="boom",
            title="Boom",
            requires_admin=False,
            check=lambda: False,
            run=_raise,
        )
        results = run_tasks([task])
        assert len(results) == 1
        assert results[0].ok is False
        assert "boom" in results[0].details

    def test_empty_tasks(self):
        """An empty iterable should return an empty list."""
        assert run_tasks([]) == []
