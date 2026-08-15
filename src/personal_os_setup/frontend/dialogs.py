"""Modal dialog screens for the Textual frontend."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class ConfirmScreen(ModalScreen[bool]):
    """A Yes/No confirmation dialog.

    Dismisses with ``True`` if the user selects **Yes**, ``False`` otherwise
    (including pressing **Escape**).
    """

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }
    ConfirmScreen > Vertical {
        width: 60%;
        max-width: 80;
        height: auto;
        border: thick $accent;
        background: $panel;
        padding: 1 2;
    }
    ConfirmScreen #confirm-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    ConfirmScreen #confirm-text {
        width: 1fr;
        height: auto;
    }
    ConfirmScreen #confirm-buttons {
        margin-top: 1;
        height: auto;
        align: right middle;
    }
    ConfirmScreen Button {
        margin-left: 1;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, *, title: str, text: str) -> None:
        super().__init__()
        self._title = title
        self._text = text

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._title, id="confirm-title")
            yield Label(self._text, id="confirm-text")
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes", id="confirm-yes", variant="success")
                yield Button("No", id="confirm-no", variant="error")

    @on(Button.Pressed, "#confirm-yes")
    def _yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#confirm-no")
    def _no(self) -> None:
        self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


class PromptScreen(ModalScreen[str | None]):
    """A single-line text prompt dialog.

    Dismisses with the entered text if the user clicks **OK**, or ``None``
    if the user cancels (including pressing **Escape**).
    """

    DEFAULT_CSS = """
    PromptScreen {
        align: center middle;
    }
    PromptScreen > Vertical {
        width: 70%;
        max-width: 90;
        height: auto;
        border: thick $accent;
        background: $panel;
        padding: 1 2;
    }
    PromptScreen #prompt-label {
        margin-bottom: 1;
    }
    PromptScreen #prompt-buttons {
        margin-top: 1;
        height: auto;
        align: right middle;
    }
    PromptScreen Button {
        margin-left: 1;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, *, title: str, label: str, initial: str) -> None:
        super().__init__()
        self._title = title
        self._label = label
        self._initial = initial

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._title, id="prompt-title")
            yield Label(self._label, id="prompt-label")
            yield Input(self._initial, id="prompt-input")
            with Horizontal(id="prompt-buttons"):
                yield Button("OK", id="prompt-ok", variant="success")
                yield Button("Cancel", id="prompt-cancel", variant="error")

    def on_mount(self) -> None:
        self.query_one("#prompt-input", Input).focus()

    @on(Input.Submitted, "#prompt-input")
    def _submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    @on(Button.Pressed, "#prompt-ok")
    def _ok(self) -> None:
        self.dismiss(self.query_one("#prompt-input", Input).value)

    @on(Button.Pressed, "#prompt-cancel")
    def _cancel(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)
