"""Exercise integration reporting using only synthetic, temporary pytest modules."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("source", "options", "status", "message"),
    [
        (
            "def test_ok(): pass\ndef test_other_platform(): pytest.skip('other OS')",
            [],
            0,
            "complete",
        ),
        (
            "def test_other_platform(): pytest.skip('other OS')",
            [],
            1,
            "zero integration tests passed",
        ),
        ("def test_ok(): pass", ["-k", "absent"], 1, "deselection removed every integration case"),
        ("", [], 1, "zero integration tests passed"),
        ("def test_bad(): assert False", [], 1, "1 test(s) failed"),
        (
            "@pytest.fixture(autouse=True)\ndef cleanup():\n    yield\n    assert False\ndef test_ok(): pass",
            [],
            1,
            "1 test(s) failed",
        ),
        ("def test_ok(): pass", ["--collect-only"], 0, ""),
    ],
)
def test_execution_boundary(tmp_path, source, options, status, message):
    module = tmp_path / "tests/integration/test_fixture.py"
    module.parent.mkdir(parents=True)
    module.write_text("import pytest\n" + source + "\n")
    summary = tmp_path / "summary.md"
    env = dict(
        os.environ,
        PYTHONPATH=str(REPO),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        GITHUB_STEP_SUMMARY=str(summary),
    )
    env.pop("PYTEST_ADDOPTS", None)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "scripts.integration_results",
            str(module),
            *options,
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == status, result.stdout + result.stderr
    if message:
        assert message in summary.read_text()
    else:
        assert not summary.exists(), "collection is diagnostic, not completed validation"
