"""Retries may add release metadata, never untested code or dependency changes."""

import subprocess

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
        ("show-ref", "--verify", "--quiet", "refs/tags/v2.21.0"): "",
        ("rev-parse", "refs/tags/v2.21.0^{commit}"): "release",
        ("log", "-1", "--format=%B"): "chore(release): v2.21.0 [skip ci]",
        ("diff", "--name-only", "tested", "HEAD"): "pyproject.toml\nuv.lock\nCHANGELOG.md",
        ("show", "tested:pyproject.toml"): project,
        ("show", "tested:uv.lock"): lock,
    }
    (tmp_path / "pyproject.toml").write_text(project.replace("2.20.0", "2.21.0"))
    (tmp_path / "uv.lock").write_text(lock.replace("2.20.0", "2.21.0"))

    def git(*args):
        result = state[args]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(checks, "git", git)
    return state, tmp_path


def test_exact_tested_revision_is_accepted(source):
    state, _ = source
    state[("rev-parse", "HEAD")] = "tested"
    assert checks.check_release_source("tested") == "source"


def test_exact_metadata_release_retry_is_accepted(source):
    assert checks.check_release_source("tested") == "release"


def test_metadata_release_without_local_tag_can_resume(source):
    state, _ = source
    command = ("show-ref", "--verify", "--quiet", "refs/tags/v2.21.0")
    state[command] = subprocess.CalledProcessError(1, ["git", *command])
    assert checks.check_release_source("tested") == "release"


def test_missing_tag_does_not_allow_untested_dependencies(source):
    state, root = source
    command = ("show-ref", "--verify", "--quiet", "refs/tags/v2.21.0")
    state[command] = subprocess.CalledProcessError(1, ["git", *command])
    with (root / "uv.lock").open("a") as stream:
        stream.write('[[package]]\nname = "untested"\nversion = "1.0"\n')
    with pytest.raises(ValueError, match="untested dependency"):
        checks.check_release_source("tested")


def test_tag_lookup_error_is_not_treated_as_missing_tag(source):
    state, _ = source
    command = ("show-ref", "--verify", "--quiet", "refs/tags/v2.21.0")
    state[command] = subprocess.CalledProcessError(128, ["git", *command])
    with pytest.raises(subprocess.CalledProcessError):
        checks.check_release_source("tested")


@pytest.mark.parametrize(
    ("command", "value", "message"),
    [
        (("rev-list", "--parents", "-n", "1", "HEAD"), "release newer", "revision that passed CI"),
        (
            ("rev-list", "--parents", "-n", "1", "HEAD"),
            "release tested other",
            "revision that passed CI",
        ),
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


@pytest.mark.parametrize("version", ["2.20.0", "2.22.0"])
def test_retry_requires_root_lock_version_to_match_project(source, version):
    _, root = source
    (root / "uv.lock").write_text(
        f'[[package]]\nname = "personal-os-setup"\nversion = "{version}"\n'
    )
    with pytest.raises(ValueError, match="root lock version"):
        checks.check_release_source("tested")


def test_tested_source_also_requires_a_consistent_root_lock(source):
    state, root = source
    state[("rev-parse", "HEAD")] = "tested"
    (root / "uv.lock").write_text('[[package]]\nname = "personal-os-setup"\nversion = "2.20.0"\n')
    with pytest.raises(ValueError, match="root lock version"):
        checks.check_release_source("tested")


@pytest.mark.parametrize("roots", [0, 2])
def test_retry_requires_exactly_one_root_lock_entry(source, roots):
    _, root = source
    (root / "uv.lock").write_text(
        "package = []\n"
        if roots == 0
        else '[[package]]\nname = "personal-os-setup"\nversion = "2.21.0"\n' * roots
    )
    with pytest.raises(ValueError, match="exactly one root package"):
        checks.check_release_source("tested")


def test_release_child_must_increase_the_version(source):
    state, _ = source
    for name in ("pyproject.toml", "uv.lock"):
        key = ("show", f"tested:{name}")
        state[key] = state[key].replace("2.20.0", "2.21.0")
    with pytest.raises(ValueError, match="increased release version"):
        checks.check_release_source("tested")


def test_prerelease_root_lock_uses_normalized_python_version(source):
    state, root = source
    (root / "pyproject.toml").write_text(
        '[project]\nname = "personal-os-setup"\nversion = "2.21.0-rc.1"\n'
    )
    (root / "uv.lock").write_text(
        '[[package]]\nname = "personal-os-setup"\nversion = "2.21.0rc1"\n'
    )
    state[("show-ref", "--verify", "--quiet", "refs/tags/v2.21.0-rc.1")] = ""
    state[("rev-parse", "refs/tags/v2.21.0-rc.1^{commit}")] = "release"
    state[("log", "-1", "--format=%B")] = "chore(release): v2.21.0-rc.1 [skip ci]"
    assert checks.check_release_source("tested") == "release"
