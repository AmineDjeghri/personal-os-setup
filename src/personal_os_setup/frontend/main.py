"""Public entry point for launching the terminal UI."""

from __future__ import annotations

from pathlib import Path

import TermTk as ttk
from TermTk import TTkString

from personal_os_setup.settings import logger
from personal_os_setup.frontend.controller import AppController
from personal_os_setup.frontend.runner import JobRunner
from personal_os_setup.detect_os import build_packages_for_os
from personal_os_setup.tasks.factory import get_system_action_sections, SystemAction
from personal_os_setup.tasks.sudo import sudo_preauth


def run_app() -> None:
    """Entry point for launching the terminal UI."""
    system, distro, info, packages = build_packages_for_os()
    info = f" info:{info}" if info else ""
    root = ttk.TTk()
    win = ttk.TTkWindow(
        parent=root,
        title="Personal OS Setup",
        size=(150, 50),
        border=True,
        layout=ttk.TTkVBoxLayout(),
    )

    # header
    header = ttk.TTkFrame(parent=win, layout=ttk.TTkHBoxLayout())
    ttk.TTkLabel(
        parent=header,
        text=f"OS: {system} | Distro: {distro} | {info}",
        color=ttk.TTkColor.fg("#00ff00"),
        maxHeight=2,
    )

    # body — limit height so footer action buttons remain visible
    body = ttk.TTkFrame(parent=win, layout=ttk.TTkHBoxLayout(), maxHeight=25)

    # left: packages list (native TermTk list widget, multi-select)
    left = ttk.TTkFrame(parent=body, title=TTkString("Packages"), layout=ttk.TTkVBoxLayout())

    ttk.TTkLabel(parent=left, text="[ MultiSelect ]", maxHeight=1)
    package_list = ttk.TTkList(parent=left, selectionMode=ttk.TTkK.MultiSelection)

    # Map list labels back to PackageRef so we can install selections.
    label_to_pkg: dict[str, object] = {}
    for p in sorted(packages, key=lambda x: (x.category, x.manager, x.name)):
        label = f"[{p.category}] {p.name} ({p.manager})"
        package_list.addItem(label)
        label_to_pkg[label] = p

    def _get_selected_packages() -> list[object]:
        out: list[object] = []
        for l in package_list.selectedLabels():
            pkg = label_to_pkg.get(str(l))
            if pkg is not None:
                out.append(pkg)
        return out

    # right
    right = ttk.TTkFrame(parent=body, title=TTkString("Log"), layout=ttk.TTkVBoxLayout())
    log = ttk.TTkTextEdit(parent=right, readOnly=True)
    right.layout().addWidget(log)  # type: ignore[call-arg]

    # footer
    footer = ttk.TTkFrame(parent=win, layout=ttk.TTkVBoxLayout())

    # Display install button
    install_row = ttk.TTkFrame(parent=footer, layout=ttk.TTkHBoxLayout())
    install_btn = ttk.TTkButton(parent=install_row, text=TTkString("Install selected"))

    action_buttons: list[ttk.TTkButton] = []

    runner = JobRunner()
    runner.start()

    poll_timer = ttk.TTkTimer()

    controller = AppController(
        win=win,
        log=log,
        distro=distro,
        get_selected_packages=_get_selected_packages,  # type: ignore[arg-type]
        install_btn=install_btn,
        action_buttons=action_buttons,
        runner=runner,
        poll_timer=poll_timer,
    )

    install_btn.clicked.connect(controller.install_selected_clicked)

    if distro == "unknown":
        controller.ui_log("Unsupported OS")

    # Display actions buttons
    for section_name, actions in get_system_action_sections(
        system=system, distro=distro, info=info
    ):
        row = ttk.TTkFrame(parent=footer, layout=ttk.TTkHBoxLayout())
        ttk.TTkLabel(parent=row, text=f"{section_name}:", maxWidth=14)
        for action in actions:
            btn = ttk.TTkButton(parent=row, text=TTkString(action.label))
            action_buttons.append(btn)

            def _on_action_clicked(
                *_args: object, _action: SystemAction = action, _section_name: str = section_name
            ) -> None:
                controller.action_clicked(_action, _section_name)

            btn.clicked.connect(_on_action_clicked)

    poll_timer.timeout.connect(controller.on_poll)
    poll_timer.start(0.1)

    try:
        root.mainloop()
    finally:
        controller.shutdown()


def main():
    if not Path.cwd().name == "personal-os-setup":
        logger.warning(
            "You are launching the UI from a directory that does not look like the repo root. "
            "For the intended workflow, run it from the repo root (or use install_unix.sh / make)."
        )
    sudo_preauth()
    run_app()


if __name__ == "__main__":
    main()
