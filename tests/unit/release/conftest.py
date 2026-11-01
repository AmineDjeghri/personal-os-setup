"""Small package archives used by artifact and publication regression tests."""

import io
import tarfile
import zipfile

import pytest
from packaging.version import Version

from scripts.check_artifacts import REQUIRED_RESOURCES


@pytest.fixture
def artifacts(tmp_path):
    def create(version="2.20.0", metadata_version=None, missing=None):
        project = tmp_path / "pyproject.toml"
        project.write_text(f'[project]\nname = "personal-os-setup"\nversion = "{version}"\n')
        dist = tmp_path / "dist"
        dist.mkdir(exist_ok=True)
        stem = f"personal_os_setup-{Version(version)}"
        data = (
            f"Name: personal-os-setup\nVersion: {metadata_version or Version(version)}\n".encode()
        )
        wheel = dist / f"{stem}-py3-none-any.whl"
        sdist = dist / f"{stem}.tar.gz"
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr(f"{stem}.dist-info/METADATA", data)
            for resource in REQUIRED_RESOURCES:
                if resource != missing:
                    archive.writestr(f"personal_os_setup/{resource}", b"fixture payload")
        with tarfile.open(sdist, "w:gz") as archive:
            payload = {f"{stem}/PKG-INFO": data}
            payload.update(
                {
                    f"{stem}/src/personal_os_setup/{r}": b"fixture payload"
                    for r in REQUIRED_RESOURCES
                    if r != missing
                }
            )
            for name, content in payload.items():
                member = tarfile.TarInfo(name)
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
        return project, dist, wheel, sdist

    return create
