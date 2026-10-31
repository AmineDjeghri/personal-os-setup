"""Exercise the configured release build with harmless, failing command stubs."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

import pytest

REPO = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(
    os.name == "nt" or not shutil.which("bash"), reason="POSIX release build shell"
)


@pytest.mark.parametrize("failure", ["uv", "git", "make", ""])
def test_release_build_stops_at_first_failure(tmp_path, failure):
    log = tmp_path / "calls"
    for name in ("uv", "git", "make"):
        command = tmp_path / name
        command.write_text(
            f"#!{sys.executable}\n"
            "import os, pathlib, sys\n"
            "name = pathlib.Path(sys.argv[0]).name\n"
            "with pathlib.Path(os.environ['BUILD_LOG']).open('a') as stream:\n"
            "    stream.write(name + '\\n')\n"
            "sys.exit(23 if name == os.environ['BUILD_FAILURE'] else 0)\n"
        )
        command.chmod(0o755)
    config = tomllib.loads((REPO / "pyproject.toml").read_text())
    result = subprocess.run(
        [shutil.which("bash"), "-c", config["tool"]["semantic_release"]["build_command"]],
        cwd=tmp_path,
        env=dict(
            os.environ,
            PATH=str(tmp_path) + os.pathsep + os.environ["PATH"],
            BUILD_LOG=str(log),
            BUILD_FAILURE=failure,
        ),
        capture_output=True,
        text=True,
    )
    order = ["uv", "git", "make"]
    assert result.returncode == (23 if failure else 0), result.stderr
    assert log.read_text().splitlines() == (order[: order.index(failure) + 1] if failure else order)
