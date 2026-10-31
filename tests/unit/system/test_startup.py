"""Verify bootstrap runs before importing the UI, using only synthetic application modules."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[3]
HARNESS = r"""
import json, runpy, sys, types
events = []
for name in ('personal_os_setup', 'personal_os_setup.frontend', 'personal_os_setup.tasks'):
    module = types.ModuleType(name)
    module.__path__ = []
    sys.modules[name] = module
bootstrap = types.ModuleType('personal_os_setup.tasks.self_update')
def update():
    events.append('update')
    assert 'personal_os_setup.frontend.app' not in sys.modules
    if sys.argv[2] == 'failure': raise RuntimeError('fixture sync failure')
    app = types.ModuleType('personal_os_setup.frontend.app')
    class UpdatedApp:
        def run(self): events.append('updated app')
    app.PersonalOsSetupApp = UpdatedApp
    sys.modules[app.__name__] = app
    sudo = types.ModuleType('personal_os_setup.tasks.sudo')
    sudo.sudo_preauth = lambda: events.append('sudo stub')
    sys.modules[sudo.__name__] = sudo
bootstrap.self_update = update
sys.modules[bootstrap.__name__] = bootstrap
entry = runpy.run_path(sys.argv[1], run_name='fixture_entry')
try:
    entry['main']()
finally:
    print(json.dumps(events))
"""


@pytest.mark.parametrize("failure", [False, True])
def test_only_start_sudo_and_updated_ui_after_successful_bootstrap(failure):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            HARNESS,
            str(REPO / "src/personal_os_setup/frontend/main.py"),
            "failure" if failure else "success",
        ],
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == int(failure), result.stderr
    assert json.loads(result.stdout) == (
        ["update"] if failure else ["update", "sudo stub", "updated app"]
    )
    if failure:
        assert "fixture sync failure" in result.stderr and "Traceback" not in result.stderr
