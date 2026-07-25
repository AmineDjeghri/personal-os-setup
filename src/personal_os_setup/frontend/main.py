"""Public entry point for launching the terminal UI."""

from __future__ import annotations

from personal_os_setup.frontend.app import PersonalOsSetupApp
from personal_os_setup.tasks.sudo import sudo_preauth


def main() -> None:
    sudo_preauth()
    PersonalOsSetupApp().run()


if __name__ == "__main__":
    main()
