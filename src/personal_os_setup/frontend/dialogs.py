"""Small dialog helpers for the TermTk frontend."""

from __future__ import annotations
from typing import Callable

import TermTk as ttk
from TermTk import TTkString


def _center_over_parent(*, widget: ttk.TTkWidget, parent: ttk.TTkWidget) -> None:
    pw, ph = parent.width(), parent.height()
    ww, wh = widget.width(), widget.height()
    x = max(0, (pw - ww) // 2)
    y = max(0, (ph - wh) // 5)
    widget.move(x, y)
    widget.raiseWidget()


def confirm(
    *,
    parent: ttk.TTkWidget,
    title: str,
    text: str,
    on_yes: Callable[[], None],
) -> None:
    """Show a Yes/No confirmation dialog.

    Calls `on_yes` only when the user selects **Yes**.
    """
    mb = ttk.TTkMessageBox(
        parent=parent,
        title=TTkString(f" {title} ", ttk.TTkColor.fg("#00ff00") + ttk.TTkColor.bg("#004400")),
        icon=ttk.TTkMessageBox.Icon.Question,
        text=TTkString(text),
        standardButtons=(
            ttk.TTkMessageBox.StandardButton.Yes | ttk.TTkMessageBox.StandardButton.No
        ),
        defaultButton=ttk.TTkMessageBox.StandardButton.No,
    )

    _center_over_parent(widget=mb, parent=parent)

    def _on_selected(sb: ttk.TTkMessageBox.StandardButton) -> None:
        if sb == ttk.TTkMessageBox.StandardButton.Yes:
            on_yes()

    mb.buttonSelected.connect(_on_selected)


def prompt_text(
    *,
    parent: ttk.TTkWidget,
    title: str,
    label: str,
    initial: str,
    on_ok: Callable[[str], None],
) -> None:
    """Prompt the user for a single line of text.

    Calls `on_ok` with the user's input when the user clicks **OK**.
    """
    dialog = ttk.TTkWindow(
        parent=parent,
        title=TTkString(f" {title} ", ttk.TTkColor.fg("#00aaff") + ttk.TTkColor.bg("#003355")),
        size=(80, 18),
        border=True,
        layout=ttk.TTkVBoxLayout(),
    )
    _center_over_parent(widget=dialog, parent=parent)
    ttk.TTkLabel(parent=dialog, text=label, maxHeight=2)
    edit = ttk.TTkLineEdit(parent=dialog)
    edit.setText(initial)

    buttons = ttk.TTkFrame(parent=dialog, layout=ttk.TTkHBoxLayout())
    ok_btn = ttk.TTkButton(parent=buttons, text=TTkString("OK"))
    cancel_btn = ttk.TTkButton(parent=buttons, text=TTkString("Cancel"))

    def _accept() -> None:
        value = edit.text()
        dialog.close()
        # TermTk returns a TTkString-like object; normalize it to a plain str for callers.
        on_ok(str(value))

    def _cancel() -> None:
        dialog.close()

    ok_btn.clicked.connect(_accept)
    cancel_btn.clicked.connect(_cancel)
