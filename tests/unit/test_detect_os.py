"""Unit tests for OS/distro detection and package-catalog resolution."""

from __future__ import annotations

CACHYOS_RELEASE = """NAME="CachyOS Linux"
PRETTY_NAME="CachyOS"
ID=cachyos
ID_LIKE=arch
BUILD_ID=rolling
"""


def _detect_with_release(text: str, tmp_path):
    """Run the real detect_os() against a real os-release file on disk."""
    from personal_os_setup import detect_os

    os_release_path = tmp_path / "os-release"
    os_release_path.write_text(text, encoding="utf-8")
    return detect_os.detect_os(system="Linux", os_release_path=os_release_path, is_wsl=False)


class TestDetectOS:
    """Tests for distro identification."""

    def test_cachyos_is_detected_directly(self, tmp_path):
        """CachyOS's own /etc/os-release ID is used as-is -- no normalization needed."""
        info = _detect_with_release(CACHYOS_RELEASE, tmp_path)
        assert info.family == "linux"
        assert info.distro == "cachyos"


class TestPackageCatalog:
    """Tests for catalog resolution."""

    CATALOG = {
        "packages": {
            "cachyos": {
                "pacman": {
                    "core": ["git", "curl"],
                    "apps": ["vlc"],
                },
                "paru": {"Browsers": ["brave-browser"]},
            },
        }
    }

    def _catalog(self):
        from personal_os_setup.detect_os import PackageCatalog

        return PackageCatalog(data=self.CATALOG)

    def test_for_distro_returns_the_matching_block(self):
        block = self._catalog().for_distro("cachyos")
        assert block["pacman"]["core"] == ["git", "curl"]
        assert block["pacman"]["apps"] == ["vlc"]
        assert block["paru"]["Browsers"] == ["brave-browser"]

    def test_unknown_distro_returns_empty(self):
        assert self._catalog().for_distro("plan9") == {}


class TestPackagesYaml:
    """Tests against the real packaged catalog."""

    def _catalog(self):
        from importlib import resources

        import yaml

        from personal_os_setup.detect_os import PackageCatalog

        pkg = resources.files("personal_os_setup")
        data = yaml.safe_load((pkg / "config" / "packages.yaml").read_text(encoding="utf-8"))
        return PackageCatalog(data=data)

    def test_every_manager_has_a_backend(self):
        """Each manager named in the catalog must resolve to a real backend."""
        from personal_os_setup.tasks.factory import get_package_manager

        catalog = self._catalog()
        for distro in ("ubuntu", "darwin", "windows", "cachyos"):
            for manager in catalog.for_distro(distro):
                assert get_package_manager(distro=distro, manager=manager) is not None, (
                    f"no backend registered for {distro}/{manager}"
                )
