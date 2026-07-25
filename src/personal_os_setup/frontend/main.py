"""Public entry point for launching the terminal UI."""

from __future__ import annotations

from personal_os_setup.frontend.app import PersonalOsSetupApp
from personal_os_setup.tasks.self_update import self_update
from personal_os_setup.tasks.sudo import sudo_preauth


def main() -> None:
    self_update()
    sudo_preauth()
    PersonalOsSetupApp().run()


if __name__ == "__main__":
    main()
