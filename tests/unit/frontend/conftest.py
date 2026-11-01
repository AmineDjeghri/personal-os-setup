"""Keep every frontend mount independent of host tools, the real catalog and dotfiles."""

import pytest

from personal_os_setup.detect_os import PackageRef
from personal_os_setup.frontend import app as frontend


@pytest.fixture(autouse=True)
def isolated_frontend(monkeypatch, tmp_path):
    packages = [
        PackageRef(name="fixture-terminal", manager="fixture", category="terminal_tools"),
        PackageRef(name="fixture-editor", manager="fixture", category="editors"),
    ]
    monkeypatch.setattr(
        frontend, "build_packages_for_os", lambda: ("linux", "ubuntu", {}, packages)
    )
    monkeypatch.setattr(
        frontend, "get_system_action_sections", lambda **kwargs: [("Sync dotfiles", [])]
    )
    monkeypatch.setattr(frontend, "chezmoi_managed_paths", lambda: [tmp_path / ".zshrc"])

    def unexpected(*args, **kwargs):
        pytest.fail("frontend test attempted a real manager/system action")

    monkeypatch.setattr(frontend, "get_package_manager", unexpected)
    for name in ("chezmoi_apply", "chezmoi_diff", "chezmoi_forget", "chezmoi_re_add"):
        monkeypatch.setattr(frontend, name, unexpected)
