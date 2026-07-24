from __future__ import annotations

from personal_os_setup.tasks.task import TaskResult


def show_commands() -> TaskResult:
    lines = [
        "============ Commands ============",
        "1. ls",
        "2. cat",
        "3. top",
        "4. fz or CTRL+F",
        "5. Tab, control tab etc.. for autocomplete",
        "6. folder selection with arrow when navigating",
        "7. history with arrow up",
        "8. neofetch",
    ]
    return TaskResult(ok=True, summary="commands: shown", details="\n".join(lines))
