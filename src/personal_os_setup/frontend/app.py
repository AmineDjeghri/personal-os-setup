"""Textual-based terminal UI for personal-os-setup.

This module wires together:
- package selection + install (from the packages catalog)
- system actions (from the tasks factory), one tab per section
- a Textual background worker to keep the UI responsive during installs/actions
"""

from __future__ import annotations

import itertools
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Collapsible,
    Footer,
    Header,
    Label,
    LoadingIndicator,
    ProgressBar,
    RichLog,
    SelectionList,
    TabbedContent,
    TabPane,
)
from textual.widgets.selection_list import Selection

from personal_os_setup.detect_os import PackageRef, build_packages_for_os
from personal_os_setup.frontend.dialogs import ConfirmScreen, PromptScreen
from personal_os_setup.settings import logger
from personal_os_setup.tasks import commands
from personal_os_setup.tasks.factory import (
    SystemAction,
    get_package_manager,
    get_system_action_sections,
)
from personal_os_setup.tasks.system.chezmoi import (
    chezmoi_apply,
    chezmoi_diff,
    chezmoi_forget,
    chezmoi_managed_paths,
    chezmoi_re_add,
)
from personal_os_setup.tasks.task import TaskResult

_CSS_PATH = Path(__file__).with_name("app.tcss")
_LOGS_TAB_LABEL = "📋 Logs"
_DOTFILES_SECTION_NAME = "Sync dotfiles"


class PersonalOsSetupApp(App[None]):
    """Terminal UI for detecting the host OS and installing packages / running system actions."""

    TITLE = "Personal OS Setup"
    CSS_PATH = _CSS_PATH

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("i", "install_selected", "Install selected"),
        ("ctrl+l", "clear_log", "Clear log"),
    ]

    is_busy: reactive[bool] = reactive(False)

    def __init__(self) -> None:
        super().__init__()
        system, distro, info, packages = build_packages_for_os()
        self._system = system
        self._distro = distro
        self._info = info
        self._packages = packages
        self._buttons: list[Button] = []
        self._action_by_button_id: dict[str, tuple[str, SystemAction]] = {}
        self._button_id_counter = itertools.count()
        self._unread_log_count = 0

    def _grouped_packages(self) -> list[tuple[str, list[PackageRef]]]:
        """Group `self._packages` by category, "terminal_tools" first, then alphabetically."""
        groups: dict[str, list[PackageRef]] = {}
        for p in self._packages:
            groups.setdefault(p.category, []).append(p)
        for pkgs in groups.values():
            pkgs.sort(key=lambda p: (p.manager, p.name))
        return [
            (category, groups[category])
            for category in sorted(
                groups, key=lambda c: (0 if c.lower() == "terminal_tools" else 1, c.lower())
            )
        ]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="main-tabs"):
            with TabPane("📦 Packages", id="packages"):
                with Vertical():
                    with Horizontal(id="packages-toolbar"):
                        yield Button("Install selected", id="btn-install", variant="success")
                        yield Label("Ready", id="install-status")
                        yield ProgressBar(id="install-progress", show_eta=False)
                    with VerticalScroll(id="package-list-container"):
                        for category, pkgs in self._grouped_packages():
                            with Collapsible(
                                title=f"{category} ({len(pkgs)})",
                                collapsed=category.lower() != "terminal_tools",
                                classes="package-category",
                            ):
                                yield SelectionList[PackageRef](
                                    *[Selection(f"{p.name} ({p.manager})", p) for p in pkgs],
                                    classes="category-list",
                                )

            for section_name, actions in get_system_action_sections(
                system=self._system, distro=self._distro, info=self._info, packages=self._packages
            ):
                with TabPane(section_name, id=f"section-{next(self._button_id_counter)}"):
                    with Vertical(classes="action-pane"):
                        if section_name == _DOTFILES_SECTION_NAME:
                            with Horizontal(id="dotfiles-toolbar"):
                                yield Button("diff selected", id="btn-dotfiles-diff")
                                yield Button(
                                    "apply selected", id="btn-dotfiles-apply", variant="success"
                                )
                                yield Button("re-add selected", id="btn-dotfiles-readd")
                                yield Button(
                                    "forget selected", id="btn-dotfiles-forget", variant="error"
                                )
                            with VerticalScroll(id="dotfiles-list-container"):
                                yield SelectionList[Path](
                                    *[Selection(str(p), p) for p in chezmoi_managed_paths()],
                                    id="dotfiles-selection-list",
                                )
                        for action in actions:
                            button_id = f"action-btn-{next(self._button_id_counter)}"
                            self._action_by_button_id[button_id] = (section_name, action)
                            with Horizontal(classes="action-row"):
                                yield Button(action.label, id=button_id)

            with TabPane(_LOGS_TAB_LABEL, id="logs"):
                yield RichLog(id="log-widget", markup=False, wrap=True)

        with Horizontal(id="status-row"):
            yield LoadingIndicator(id="busy-indicator")
            yield Label("Ready", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        info = f" | info: {self._info}" if self._info else ""
        self.sub_title = f"OS: {self._system} | Distro: {self._distro}{info}"
        self._buttons = list(self.query(Button))
        self.query_one("#busy-indicator", LoadingIndicator).display = False

    # ── Reactive busy state ──────────────────────────────────────────────────

    def watch_is_busy(self, busy: bool) -> None:
        """Enable/disable actions and toggle the busy indicator when `is_busy` changes."""
        for btn in self._buttons:
            btn.disabled = busy
        self.query_one("#busy-indicator", LoadingIndicator).display = busy
        self.query_one("#status-bar", Label).update("Busy: running a job..." if busy else "Ready")

    # ── Logging ──────────────────────────────────────────────────────────────

    def _log(self, message: str) -> None:
        """Log to both the UI log panel and the Python logger."""
        self.query_one("#log-widget", RichLog).write(message)
        logger.debug(message)
        if self.query_one("#main-tabs", TabbedContent).active != "logs":
            self._unread_log_count += 1
            self._update_logs_tab_label()

    def _update_logs_tab_label(self) -> None:
        tab = self.query_one("#main-tabs", TabbedContent).get_tab("logs")
        if self._unread_log_count:
            tab.label = f"{_LOGS_TAB_LABEL} ({self._unread_log_count})"
        else:
            tab.label = _LOGS_TAB_LABEL

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if event.pane.id == "logs" and self._unread_log_count:
            self._unread_log_count = 0
            self._update_logs_tab_label()

    # ── Bindings ─────────────────────────────────────────────────────────────

    def action_install_selected(self) -> None:
        self._on_install_selected()

    def action_clear_log(self) -> None:
        self.query_one("#log-widget", RichLog).clear()
        self._unread_log_count = 0
        self._update_logs_tab_label()

    # ── Package install ──────────────────────────────────────────────────────

    def _on_install_selected(self) -> None:
        if self.is_busy:
            self.notify("Busy: another task is running", severity="warning")
            return

        selected: list[PackageRef] = []
        for selection_list in self.query_one("#package-list-container").query(SelectionList):
            selected.extend(selection_list.selected)
        if not selected:
            self.notify("No packages selected", severity="warning")
            return

        self.is_busy = True
        self._install_packages_worker(selected)

    @work(thread=True, exclusive=True, group="jobs")
    def _install_packages_worker(self, selected: list[PackageRef]) -> None:
        total = len(selected)
        succeeded = 0
        progress = self.query_one("#install-progress", ProgressBar)
        status = self.query_one("#install-status", Label)
        self.call_from_thread(progress.update, total=total, progress=0)

        token = commands.set_stream_sink(lambda line: self.call_from_thread(self._log, line))
        try:
            for i, p in enumerate(selected, start=1):
                pm = get_package_manager(distro=self._distro, manager=p.manager)
                if pm is None:
                    self.call_from_thread(
                        self._log,
                        f"No installer available for {p.manager} on {self._distro} (coming soon)",
                    )
                elif pm.is_installed(p.name):
                    succeeded += 1
                    self.call_from_thread(self._log, f"{p.name}: already installed")
                else:
                    res = pm.install(p.name)
                    succeeded += 1 if res.ok else 0
                    self.call_from_thread(self._log, res.summary)
                    if res.details:
                        self.call_from_thread(self._log, res.details)

                self.call_from_thread(progress.update, progress=i)
                self.call_from_thread(status.update, f"{i}/{total} installed")
        finally:
            commands.reset_stream_sink(token)
            self.call_from_thread(
                self.notify,
                f"Install job finished: {succeeded}/{total} packages ready",
                severity="information" if succeeded == total else "warning",
            )
            self.call_from_thread(setattr, self, "is_busy", False)

    # ── System actions ───────────────────────────────────────────────────────

    def _on_action_button(self, section_name: str, action: SystemAction) -> None:
        if self.is_busy:
            self.notify("Busy: another task is running", severity="warning")
            return

        name = f"{section_name}: {action.label}"

        def _after_prompt(value: str | None) -> None:
            if value is None:
                return
            self.is_busy = True
            self._run_action_worker(action, name, value)

        def _maybe_prompt() -> None:
            if action.run_with_prompt is not None and action.prompt_label is not None:
                self.push_screen(
                    PromptScreen(
                        title="Input", label=action.prompt_label, initial=action.prompt_initial
                    ),
                    _after_prompt,
                )
                return
            self.is_busy = True
            self._run_action_worker(action, name, None)

        if action.confirm:

            def _after_confirm(confirmed: bool) -> None:
                if confirmed:
                    _maybe_prompt()

            self.push_screen(
                ConfirmScreen(
                    title="Confirm", text=action.confirm_message or f"Proceed with: {name}?"
                ),
                _after_confirm,
            )
            return

        _maybe_prompt()

    @work(thread=True, exclusive=True, group="jobs")
    def _run_action_worker(self, action: SystemAction, name: str, prompt_value: str | None) -> None:
        token = commands.set_stream_sink(lambda line: self.call_from_thread(self._log, line))
        try:
            self.call_from_thread(self._log, f"Running: {name}...")

            target = action.backup_target
            if target is not None:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                default_backup = (
                    target.with_name(f"{target.stem}_{ts}_backup{target.suffix}")
                    if target.suffix
                    else target.with_name(f"{target.name}_{ts}_backup")
                )
                try:
                    if target.exists():
                        default_backup.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(target, default_backup)
                        self.call_from_thread(self._log, f"backup created: {default_backup}")
                except Exception as e:  # noqa: BLE001
                    self.call_from_thread(self._log, f"backup: failed ({e})")

            if prompt_value is not None and action.run_with_prompt is not None:
                res = action.run_with_prompt(prompt_value)
            else:
                res = action.run()

            self.call_from_thread(self._log, res.summary)
            if res.details:
                self.call_from_thread(self._log, res.details)
            self.call_from_thread(
                self.notify, res.summary, severity="information" if res.ok else "error"
            )
        except Exception as e:  # noqa: BLE001
            self.call_from_thread(self._log, f"{name}: failed")
            self.call_from_thread(self._log, str(e))
            self.call_from_thread(self.notify, f"{name}: failed", severity="error")
        finally:
            commands.reset_stream_sink(token)
            if name.startswith(f"{_DOTFILES_SECTION_NAME}:"):
                self.call_from_thread(self._apply_dotfiles_list, chezmoi_managed_paths())
            self.call_from_thread(setattr, self, "is_busy", False)

    # ── Dotfiles selection (chezmoi) ─────────────────────────────────────────
    def _dotfiles_action_specs(
        self,
    ) -> dict[str, tuple[str, Callable[[list[Path]], TaskResult], bool, str]]:
        return {
            "btn-dotfiles-diff": ("chezmoi: diff selected", chezmoi_diff, False, ""),
            "btn-dotfiles-apply": (
                "chezmoi: apply selected",
                chezmoi_apply,
                True,
                "This applies the selected dotfile(s) to your home directory. Run 'diff "
                "selected' first to preview. Proceed?",
            ),
            "btn-dotfiles-readd": (
                "chezmoi: re-add selected",
                chezmoi_re_add,
                True,
                "This pulls the selected dotfile(s) from your home directory back into the "
                "repo's chezmoi source dir, overwriting the vendored versions there. Proceed?",
            ),
            "btn-dotfiles-forget": (
                "chezmoi: forget selected",
                chezmoi_forget,
                True,
                "This stops tracking the selected dotfile(s) in the repo's chezmoi source dir. "
                "The live file(s) in your home directory are left untouched. Proceed?",
            ),
        }

    def _on_dotfiles_selected_action(
        self, spec: tuple[str, Callable[[list[Path]], TaskResult], bool, str]
    ) -> None:
        label, run_with_targets, confirm, confirm_message = spec
        selection_list = self.query_one("#dotfiles-selection-list", SelectionList)
        selected: list[Path] = list(selection_list.selected)
        if not selected:
            self.notify("No dotfiles selected", severity="warning")
            return

        action = SystemAction(
            label=label,
            run=lambda: run_with_targets(selected),
            confirm=confirm,
            confirm_message=confirm_message or None,
        )
        self._on_action_button(_DOTFILES_SECTION_NAME, action)

    def _apply_dotfiles_list(self, paths: list[Path]) -> None:
        selection_list = self.query_one("#dotfiles-selection-list", SelectionList)
        selection_list.clear_options()
        selection_list.add_options([Selection(str(p), p) for p in paths])

    # ── Event handlers ───────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-install":
            self._on_install_selected()
            return

        dotfiles_spec = self._dotfiles_action_specs().get(button_id or "")
        if dotfiles_spec is not None:
            self._on_dotfiles_selected_action(dotfiles_spec)
            return

        mapped = self._action_by_button_id.get(button_id or "")
        if mapped is not None:
            section_name, action = mapped
            self._on_action_button(section_name, action)
