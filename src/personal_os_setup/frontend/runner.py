"""Background job runner for the terminal UI.

TermTk is single-threaded; long-running operations (package install, system actions)
must not block the UI loop.

This module provides a minimal worker thread that:
- consumes jobs from a queue
- emits UI events (log lines, busy state) back to the UI via another queue
"""

from __future__ import annotations
import queue
import threading
from typing import Callable

from personal_os_setup.tasks import commands


UIEvent = tuple[str, str]
Job = tuple[str, Callable[[], None]]


class JobRunner:
    """Run submitted jobs on a daemon thread and publish UI events."""

    def __init__(self) -> None:
        self.ui_events: queue.Queue[UIEvent] = queue.Queue()
        self.jobs: queue.Queue[Job | None] = queue.Queue()
        self._thread = threading.Thread(
            target=self._worker, name="personal-os-setup-ui-worker", daemon=True
        )
        self._started = False

    def start(self) -> None:
        """Start the worker thread (idempotent)."""
        if self._started:
            return
        self._thread.start()
        self._started = True

    def stop(self) -> None:
        """Signal the worker thread to exit."""
        self.jobs.put(None)

    def enqueue(self, name: str, fn: Callable[[], None]) -> None:
        """Enqueue a named job for execution by the worker thread."""
        self.jobs.put((name, fn))

    def drain_events(
        self,
        *,
        on_log: Callable[[str], None],
        on_busy: Callable[[bool], None],
    ) -> None:
        """Drain queued UI events.

        This should be called on the UI thread.
        """
        while True:
            try:
                kind, payload = self.ui_events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                on_log(payload)
            elif kind == "busy":
                on_busy(payload == "1")

    def _post_log(self, line: str) -> None:
        """Post a log event for the UI thread to render."""
        self.ui_events.put(("log", line))

    def _post_busy(self, busy: bool) -> None:
        """Post a busy-state change event."""
        self.ui_events.put(("busy", "1" if busy else "0"))

    def _worker(self) -> None:
        """Worker thread loop."""
        while True:
            job = self.jobs.get()
            if job is None:
                return

            name, fn = job
            self._post_busy(True)
            self._post_log(f"Running: {name}...")
            token = commands.set_stream_sink(self._post_log)
            try:
                fn()
            except Exception as e:  # noqa: BLE001
                # Ensure exceptions are visible in the UI instead of silently killing the worker.
                self._post_log(f"{name}: failed")
                self._post_log(str(e))
            finally:
                commands.reset_stream_sink(token)
                self._post_busy(False)
