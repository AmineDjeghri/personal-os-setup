"""Public entry point for launching the terminal UI."""

from __future__ import annotations

import sys

from personal_os_setup.tasks.self_update import self_update


def main() -> None:
    try:
        self_update()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error

    # Import only after bootstrap: an update can change application code and dependencies.
    from personal_os_setup.frontend.app import PersonalOsSetupApp
    from personal_os_setup.tasks.sudo import sudo_preauth

    sudo_preauth()
    PersonalOsSetupApp().run()


if __name__ == "__main__":
    main()
