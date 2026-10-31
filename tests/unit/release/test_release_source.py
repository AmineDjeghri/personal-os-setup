"""Retries may add release metadata, never untested code or dependency changes."""

import pytest

from scripts import check_release_source as checks


@pytest.fixture
def source(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    project = '[project]\nname = "personal-os-setup"\nversion = "2.20.0"\n'
    lock = '[[package]]\nname = "personal-os-setup"\nversion = "2.20.0"\n'
    state = {
        ("rev-parse", "--verify", "tested^{commit}"): "tested",
        ("rev-parse", "HEAD"): "release",
        ("rev-list", "--parents", "-n", "1", "HEAD"): "release tested",
        ("rev-parse", "refs/tags/v2.21.0^{commit}"): "release",
        ("log", "-1", "--format=%B"): "chore(release): v2.21.0 [skip ci]",
        ("diff", "--name-only", "tested", "HEAD"): "pyproject.toml\nuv.lock\nCHANGELOG.md",
        ("show", "tested:pyproject.toml"): project,
        ("show", "tested:uv.lock"): lock,
    }
    (tmp_path / "pyproject.toml").write_text(project.replace("2.20.0", "2.21.0"))
    (tmp_path / "uv.lock").write_text(lock.replace("2.20.0", "2.21.0"))
    monkeypatch.setattr(checks, "git", lambda *args: state[args])
    return state, tmp_path


def test_exact_tested_revision_is_accepted(source):
    state, _ = source
    state[("rev-parse", "HEAD")] = "tested"
    checks.check_release_source("tested")


def test_exact_metadata_release_retry_is_accepted(source):
    checks.check_release_source("tested")


@pytest.mark.parametrize(
    ("command", "value", "message"),
    [
        (("rev-list", "--parents", "-n", "1", "HEAD"), "release newer", "revision that passed CI"),
        (("rev-parse", "refs/tags/v2.21.0^{commit}"), "other", "version tag"),
        (("log", "-1", "--format=%B"), "fix: untested", "release commit message"),
        (("diff", "--name-only", "tested", "HEAD"), "src/new.py", "untested source"),
    ],
)
def test_untested_revision_is_rejected(source, command, value, message):
    state, _ = source
    state[command] = value
    with pytest.raises(ValueError, match=message):
        checks.check_release_source("tested")


def test_retry_cannot_change_project_dependencies(source):
    _, root = source
    with (root / "pyproject.toml").open("a") as stream:
        stream.write('dependencies = ["untested-package"]\n')
    with pytest.raises(ValueError, match="untested project configuration"):
        checks.check_release_source("tested")


def test_retry_cannot_change_locked_dependencies(source):
    _, root = source
    with (root / "uv.lock").open("a") as stream:
        stream.write('[[package]]\nname = "untested"\nversion = "1.0"\n')
    with pytest.raises(ValueError, match="untested dependency"):
        checks.check_release_source("tested")
