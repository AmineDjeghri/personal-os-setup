"""Validate the exact wheel/sdist pair and bundled resources before installation or publication."""

import argparse
from email.parser import BytesParser
from pathlib import Path
import tarfile
import tomllib
import zipfile

from packaging.utils import canonicalize_name
from packaging.version import Version

REQUIRED_RESOURCES = (
    "config/packages.yaml",
    "frontend/app.tcss",
    "config/chezmoi/dot_zshrc",
    "config/chezmoi/dot_p10k.zsh",
    "config/chezmoi/dot_claude/run_after_replay-third-party-skills.sh",
    "config/chezmoi/dot_claude/skills/coding-workflow/SKILL.md",
)


def check_metadata(data: bytes, name: str, version: str) -> None:
    """Reject an archive whose embedded identity disagrees with the project."""
    metadata = BytesParser().parsebytes(data)
    if canonicalize_name(metadata["Name"] or "") != canonicalize_name(name):
        raise ValueError("artifact package name does not match pyproject.toml")
    if Version(metadata["Version"] or "0") != Version(version):
        raise ValueError("artifact version does not match pyproject.toml")


def check_artifacts(
    project: Path = Path("pyproject.toml"), dist: Path = Path("dist")
) -> tuple[Path, Path]:
    """Check filenames, archive metadata and resources without extracting or starting the app."""
    config = tomllib.loads(project.read_text(encoding="utf-8"))["project"]
    name, version = config["name"], str(Version(config["version"]))
    normalized = canonicalize_name(name).replace("-", "_")
    stem = f"{normalized}-{version}"
    wheel, sdist = dist / f"{stem}-py3-none-any.whl", dist / f"{stem}.tar.gz"
    actual = set(dist.glob("*.whl")) | set(dist.glob("*.tar.gz"))
    if actual != {wheel, sdist} or not all(p.is_file() for p in (wheel, sdist)):
        raise ValueError(f"expected only the complete current artifact pair: {wheel}, {sdist}")
    with zipfile.ZipFile(wheel) as archive:
        check_metadata(archive.read(f"{stem}.dist-info/METADATA"), name, version)
        for resource in REQUIRED_RESOURCES:
            if not archive.read(f"personal_os_setup/{resource}"):
                raise ValueError(f"empty bundled resource in wheel: {resource}")
    with tarfile.open(sdist, "r:gz") as archive:
        metadata = archive.extractfile(f"{stem}/PKG-INFO")
        if metadata is None:
            raise ValueError("sdist has no PKG-INFO")
        check_metadata(metadata.read(), name, version)
        for resource in REQUIRED_RESOURCES:
            member = archive.extractfile(f"{stem}/src/personal_os_setup/{resource}")
            if member is None or not member.read():
                raise ValueError(f"missing or empty bundled resource in sdist: {resource}")
    return wheel, sdist


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--wheel", action="store_true")
    output.add_argument("--version", action="store_true")
    output.add_argument("--prerelease", action="store_true")
    args = parser.parse_args()
    wheel, sdist = check_artifacts()
    version = Version(
        tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    )
    if args.wheel:
        print(wheel)
    elif args.version:
        print(version)
    elif args.prerelease:
        print(str(version.is_prerelease).lower())
    else:
        print(wheel, sdist, sep="\n")
