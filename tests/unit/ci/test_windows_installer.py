"""Run the Windows bootstrap with fake Git/winget/Make commands and temporary paths."""

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

REPO = Path(__file__).resolve().parents[3]
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
pytestmark = pytest.mark.skipif(POWERSHELL is None, reason="requires a PowerShell runtime")

HARNESS = r"""
$script:Fixture = $env:INSTALL_FIXTURE
$script:Scenario = $env:INSTALL_SCENARIO
$script:GitInstalled = $script:Scenario -notin @('no-git', 'git-install-failure')
$global:LASTEXITCODE = 0

function Record-Command {
    param([string]$Name, [string[]]$Arguments)
    $record = @{ name = $Name; arguments = @($Arguments) } | ConvertTo-Json -Compress
    [System.IO.File]::AppendAllText(
        (Join-Path $script:Fixture 'calls.jsonl'), $record + [System.Environment]::NewLine
    )
}

function Get-Command {
    param([string]$Name, [string]$ErrorAction)
    switch ($Name) {
        'git' { if ($script:GitInstalled) { return [pscustomobject]@{ Source = 'Fixture-Git' } } }
        'winget' { return [pscustomobject]@{ Source = 'Fixture-Winget' } }
        'make' { return [pscustomobject]@{ Source = 'Fixture-Make' } }
        'bash' { return [pscustomobject]@{ Source = 'Fixture-Bash' } }
        'chezmoi' { return [pscustomobject]@{ Source = 'Fixture-Chezmoi' } }
    }
    return $null
}

function Fixture-Git {
    Record-Command 'git' $args
    $global:LASTEXITCODE = 0
    if ($args[0] -eq 'rev-parse') {
        if ($args[1] -eq '--is-inside-work-tree') { return 'true' }
        if ($args[1] -eq '--show-toplevel') { return $script:Fixture }
    }
    if ($args[0] -eq 'pull') {
        if ($script:Scenario -eq 'pull-failure') { $global:LASTEXITCODE = 17 }
        return
    }
    throw "Unexpected Git command: $args"
}

function Fixture-Winget {
    Record-Command 'winget' $args
    if ($args -notcontains 'Git.Git') { throw "Unexpected installation: $args" }
    $global:LASTEXITCODE = 0
    if ($script:Scenario -eq 'git-install-failure') {
        $global:LASTEXITCODE = 23
    } else {
        $script:GitInstalled = $true
    }
}

function Fixture-Make {
    Record-Command 'make' $args
    $global:LASTEXITCODE = 0
    if ($args -contains 'install' -and $script:Scenario -eq 'install-failure') {
        $global:LASTEXITCODE = 23
    }
    if ($args -contains 'run' -and $script:Scenario -eq 'run-failure') {
        $global:LASTEXITCODE = 29
    }
}

. $env:INSTALL_SCRIPT
"""


@pytest.mark.parametrize(
    ("scenario", "targets", "code"),
    [
        ("existing-git", ["install", "run"], None),
        ("no-git", ["install", "run"], None),
        ("git-install-failure", [], "23"),
        ("pull-failure", [], "17"),
        ("install-failure", ["install"], "23"),
        ("run-failure", ["install", "run"], "29"),
    ],
)
def test_bootstrap_never_continues_after_critical_command_failure(
    tmp_path, scenario, targets, code
):
    root = tmp_path / "personal-os-setup"
    root.mkdir()
    log = root / "calls.jsonl"
    log.write_text("")
    harness = tmp_path / "harness.ps1"
    harness.write_text(HARNESS, encoding="utf-8")
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(harness)],
        cwd=root,
        env=dict(
            os.environ,
            INSTALL_FIXTURE=str(root),
            INSTALL_SCRIPT=str(REPO / "install_windows.ps1"),
            INSTALL_SCENARIO=scenario,
        ),
        capture_output=True,
        text=True,
        timeout=20,
    )
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8-sig").splitlines()]
    assert [call["arguments"][-1] for call in calls if call["name"] == "make"] == targets
    if code:
        assert result.returncode != 0
        assert code in result.stderr, result.stdout + result.stderr
        assert "Done" not in result.stdout
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Done" in result.stdout
    if scenario == "no-git":
        assert calls[0]["name"] == "winget" and "Git.Git" in calls[0]["arguments"]
