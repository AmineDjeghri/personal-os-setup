"""Check the installed distribution and entry point without starting the application."""

from importlib.metadata import distribution
from importlib.resources import files
from pathlib import Path
import sys

# Executed from the repository's scripts directory, also in an isolated uv environment.
from check_artifacts import REQUIRED_RESOURCES


def check_installation(expected_version: str) -> None:
    """Load the console callable and check its resources in the installed wheel."""
    installed = distribution("personal-os-setup")
    assert installed.version == expected_version, (installed.version, expected_version)
    entry = next(ep for ep in installed.entry_points if ep.name == "personal-os-setup")
    assert entry.value == "personal_os_setup.frontend.main:main", entry.value
    assert callable(entry.load())
    import personal_os_setup

    assert (
        Path(personal_os_setup.__file__)
        .resolve()
        .is_relative_to(Path(installed.locate_file("personal_os_setup")).resolve())
    ), "import must come from the installed wheel"
    for resource in REQUIRED_RESOURCES:
        assert files("personal_os_setup").joinpath(resource).read_bytes(), resource
    print(f"OK personal-os-setup {installed.version}: entry point and bundled resources")


if __name__ == "__main__":
    check_installation(sys.argv[1])
