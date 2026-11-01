"""Reject incomplete, stale and mismatched package artifacts."""

import pytest

from scripts.check_artifacts import check_artifacts


def test_complete_current_pair(artifacts):
    project, dist, wheel, sdist = artifacts()
    assert check_artifacts(project, dist) == (wheel, sdist)


def test_prerelease_filename_is_normalized_without_editing_project_version(artifacts):
    project, dist, wheel, _ = artifacts("2.21.0-rc.1")
    check_artifacts(project, dist)
    assert "2.21.0rc1" in wheel.name
    assert 'version = "2.21.0-rc.1"' in project.read_text()


def test_missing_sdist_fails(artifacts):
    project, dist, _, sdist = artifacts()
    sdist.unlink()
    with pytest.raises(ValueError, match="complete current artifact pair"):
        check_artifacts(project, dist)


def test_stale_extra_wheel_fails(artifacts):
    project, dist, _, _ = artifacts()
    (dist / "old.whl").write_bytes(b"stale")
    with pytest.raises(ValueError, match="complete current artifact pair"):
        check_artifacts(project, dist)


def test_mismatched_embedded_version_fails(artifacts):
    project, dist, _, _ = artifacts(metadata_version="1.0.0")
    with pytest.raises(ValueError, match="artifact version"):
        check_artifacts(project, dist)


def test_missing_bundled_resource_fails(artifacts):
    project, dist, _, _ = artifacts(missing="frontend/app.tcss")
    with pytest.raises(KeyError, match="app.tcss"):
        check_artifacts(project, dist)
