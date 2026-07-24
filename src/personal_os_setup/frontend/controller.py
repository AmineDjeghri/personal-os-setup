"""TermTk-based interactive frontend.

This module wires together:
- package selection (from the packages catalog)
- system actions (from the tasks factory)
- a background worker thread (JobRunner) to keep the UI responsive
"""

from __future__ import annotations

from typing import Callable
from datetime import datetime
import shutil

import TermTk as ttk

from personal_os_setup.settings import logger
from personal_os_setup.detect_os import PackageRef
from personal_os_setup.tasks.factory import SystemAction, get_package_manager

from personal_os_setup.frontend.dialogs import confirm, prompt_text
from personal_os_setup.frontend.runner import JobRunner


class AppController:
    """Controller for handling UI events and dispatching background work.

    The controller is responsible for:
    - updating UI state (busy/disabled controls)
    - writing logs to the UI
    - enqueuing long-running work to :class:`~personal_os_setup.frontend.runner.JobRunner`
    """

    def __init__(
        self,
        *,
        win: ttk.TTkWindow,
        log: ttk.TTkTextEdit,
        distro: str,
        get_selected_packages: Callable[[], list[PackageRef]],
        install_btn: ttk.TTkButton,
        action_buttons: list[ttk.TTkButton],
        runner: JobRunner,
        poll_timer: ttk.TTkTimer,
    ) -> None:
        self._win = win
        self._log = log
        self._distro = distro
        self._get_selected_packages = get_selected_packages
        self._install_btn = install_btn
        self._action_buttons = action_buttons
        self._runner = runner
        self._poll_timer = poll_timer
        self._is_busy = False

    def ui_log(self, message: str) -> None:
        """Log to both the UI log panel and the Python logger."""
        self._log.append(message + "\n")
        logger.debug(message)

    def set_busy(self, busy: bool) -> None:
        """Enable/disable actions depending on whether a job is running."""
        self._is_busy = busy
        for btn in self._action_buttons:
            btn.setEnabled(not busy)
        self._install_btn.setEnabled(not busy)

    def on_poll(self) -> None:
        """Drain worker-thread events and re-arm the polling timer."""
        # JobRunner posts UI events from a background thread; we pull them on the UI thread.
        self._runner.drain_events(on_log=self.ui_log, on_busy=self.set_busy)
        self._poll_timer.start(0.1)

    def shutdown(self) -> None:
        """Stop background work and timers."""
        self._runner.stop()
        self._poll_timer.quit()

    def install_selected_clicked(self) -> None:
        """Install all packages whose checkboxes are selected."""
        if self._is_busy:
            self.ui_log("Busy: another task is running")
            return

        selected = list(self._get_selected_packages() or [])
        if not selected:
            self.ui_log("No packages selected")
            return

        def _job() -> None:
            for p in selected:
                pm = get_package_manager(distro=self._distro, manager=p.manager)
                if pm is None:
                    self._runner.ui_events.put(
                        (
                            "log",
                            f"No installer available for {p.manager} on {self._distro} (coming soon)",
                        )
                    )
                    continue

                if pm.is_installed(p.name):
                    self._runner.ui_events.put(("log", f"{p.name}: already installed"))
                    continue

                res = pm.install(p.name)
                self._runner.ui_events.put(("log", res.summary))
                if res.details:
                    self._runner.ui_events.put(("log", res.details))

        self._runner.enqueue("packages: install selected", _job)

    def action_clicked(self, action: SystemAction, section_name: str) -> None:
        """Handle a click on a system action button."""
        if self._is_busy:
            self.ui_log("Busy: another task is running")
            return

        name = f"{section_name}: {action.label}"

        def _enqueue_prompted_action(*, value: str) -> None:
            def _run_action() -> None:
                fn = action.run_with_prompt
                if fn is None:
                    res = action.run()
                else:
                    res = fn(value)
                self._runner.ui_events.put(("log", res.summary))
                if res.details:
                    self._runner.ui_events.put(("log", res.details))

            def _run_action_with_backup() -> None:
                target = action.backup_target
                if target is not None:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    default_backup = target.with_name(f"{target.name}_{ts}_backup")
                    try:
                        if target.exists():
                            default_backup.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(target, default_backup)
                            self._runner.ui_events.put(("log", f"backup created: {default_backup}"))
                    except Exception as e:  # noqa: BLE001
                        self._runner.ui_events.put(("log", f"backup: failed ({e})"))

                _run_action()

            if action.backup_target is not None:
                self._runner.enqueue(name, _run_action_with_backup)
            else:
                self._runner.enqueue(name, _run_action)

        def _maybe_prompt_then_enqueue() -> None:
            """Conditionally prompt the user for input before enqueuing a system action.

            If the system action has a non-None `run_with_prompt` and a non-None `prompt_label`,
            then prompt the user for input using `prompt_text`. Otherwise, if the system action
            has a non-None `backup_target`, then confirm with the user before enqueuing the
            action using `_confirm_with_optional_backup`. Otherwise, enqueue the action
            directly using `_enqueue_action`.


            """
            if action.run_with_prompt is not None and action.prompt_label is not None:
                prompt_text(
                    parent=self._win,
                    title="Input",
                    label=action.prompt_label,
                    initial=action.prompt_initial,
                    on_ok=lambda v: _enqueue_prompted_action(value=v),
                )
                return

            if action.backup_target is not None:
                self._confirm_with_optional_backup(action, name)
                return

            self._enqueue_action(action, name)

        if action.confirm:

            def _on_yes() -> None:
                _maybe_prompt_then_enqueue()

            confirm(
                parent=self._win,
                title="Confirm",
                text=action.confirm_message or f"Proceed with: {name}?",
                on_yes=_on_yes,
            )
            return

        _maybe_prompt_then_enqueue()

    def _enqueue_action(self, action: SystemAction, name: str) -> None:
        """Enqueue a system action into the background runner."""

        def _run_action() -> None:
            res = action.run()
            self._runner.ui_events.put(("log", res.summary))
            if res.details:
                self._runner.ui_events.put(("log", res.details))

        self._runner.enqueue(name, _run_action)

    def _confirm_with_optional_backup(self, action: SystemAction, name: str) -> None:
        """Optionally copy a backup of a target file first, then run the action."""
        target = action.backup_target
        if target is None:
            self._enqueue_action(action, name)
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Construct backup name: original_name_timestamp_backup.ext (or just original_name_timestamp_backup)
        if target.suffix:
            stem = target.stem
            default_backup = target.with_name(f"{stem}_{ts}_backup{target.suffix}")
        else:
            default_backup = target.with_name(f"{target.name}_{ts}_backup")

        def _run_action_with_backup() -> None:
            try:
                if target.exists():
                    # Ensure parent dirs exist before writing backup.
                    default_backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, default_backup)
                    self._runner.ui_events.put(("log", f"backup created: {default_backup}"))
            except Exception as e:  # noqa: BLE001
                self._runner.ui_events.put(("log", f"backup: failed ({e})"))

            res = action.run()
            self._runner.ui_events.put(("log", res.summary))
            if res.details:
                self._runner.ui_events.put(("log", res.details))

        self._runner.enqueue(name, _run_action_with_backup)


def _build_package_checkboxes(
    *,
    parent: ttk.TTkWidget,
    packages: list[PackageRef],
) -> list[tuple[PackageRef, ttk.TTkCheckbox]]:
    """Render a categorized list of packages into the left pane."""
    checks: list[tuple[PackageRef, ttk.TTkCheckbox]] = []

    by_cat: dict[str, list[PackageRef]] = {}
    for p in packages:
        by_cat.setdefault(p.category, []).append(p)

    parent_layout = parent.layout() if hasattr(parent, "layout") else None
    if parent_layout is None:
        # If no layout exists, we cannot reliably add widgets; return empty with no crash.
        return checks

    for cat in sorted(by_cat.keys()):
        label = ttk.TTkLabel(
            parent=parent,
            text=f"[{cat}]",
            color=ttk.TTkColor.fg("#ffaa00"),
            maxHeight=1,
        )
        parent_layout.addWidget(label)  # type: ignore[call-arg]
        for p in sorted(by_cat[cat], key=lambda x: x.name):
            cb = ttk.TTkCheckbox(parent=parent, text=f"{p.name} ({p.manager})")
            parent_layout.addWidget(cb)  # type: ignore[call-arg]
            checks.append((p, cb))

    return checks
