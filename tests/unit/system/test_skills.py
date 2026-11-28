"""Tests for the TUI Skills tab backend, on isolated temp directories."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from personal_os_setup.tasks.system import skills


def _skill(root, name, body="Instructions."):
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(f"---\nname: {name}\ndescription: fixture\n---\n{body}\n")
    return directory


@pytest.fixture
def env(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    authored = repo / "skills-src"
    live = tmp_path / "home" / ".claude" / "skills"
    codex = tmp_path / "home" / ".agents" / "skills"
    authored.mkdir(parents=True)
    live.mkdir(parents=True)
    (repo / "third-party-skills.lock.json").write_text(
        json.dumps({"version": 3, "skills": {"vendor": {"source": "o/r", "skillFolderHash": "h"}}})
    )
    monkeypatch.setattr(skills, "authored_dir", lambda: authored)
    monkeypatch.setattr(skills, "live_dir", lambda: live)
    monkeypatch.setattr(skills, "codex_dir", lambda: codex)
    monkeypatch.setattr(skills, "repo_root", lambda: repo)
    monkeypatch.setattr(skills, "live_lock_path", lambda: tmp_path / "state" / "lock.json")
    return repo, authored, live, codex


def _age(path, seconds):
    stamp = path.stat().st_mtime + seconds
    os.utime(path, (stamp, stamp))


class TestStatus:
    def test_classifies_ok_missing_and_live_edited(self, env):
        _, authored, live, _ = env
        for name in ("same", "gone", "edited"):
            _skill(authored, name)
        _skill(live, "same")
        edited = _skill(live, "edited", body="changed live")
        _age(edited / "SKILL.md", 100)

        state = {name: skills._compare(name)[0] for name in ("same", "gone", "edited")}
        assert state == {"same": "ok", "gone": "missing", "edited": "live-newer"}

    def test_repo_newer_is_not_a_problem_but_needs_deploy(self, env):
        _, authored, live, _ = env
        _skill(live, "a", body="old")
        newer = _skill(authored, "a", body="new")
        _age(newer / "SKILL.md", 100)
        assert skills._compare("a")[0] == "repo-newer"

    def test_ignores_tool_litter(self, env):
        _, authored, live, _ = env
        _skill(authored, "a")
        _skill(live, "a")
        (live / "a" / ".DS_Store").write_text("x")
        assert skills._compare("a")[0] == "ok"

    def test_status_fails_when_a_live_skill_was_edited(self, env):
        _, authored, live, _ = env
        _skill(authored, "a")
        _age(_skill(live, "a", body="edited") / "SKILL.md", 100)
        result = skills.skills_status()
        assert result.ok is False
        assert "LIVE NEWER" in result.details


class TestDeploy:
    def test_copies_and_links_for_codex(self, env):
        _, authored, live, codex = env
        _skill(authored, "a")
        result = skills.skills_deploy()
        assert result.ok is True, result.details
        assert (live / "a" / "SKILL.md").is_file()
        assert (codex / "a").is_symlink() and (codex / "a").resolve() == (live / "a").resolve()

    def test_refuses_to_overwrite_newer_live_edits_unless_forced(self, env):
        _, authored, live, _ = env
        _skill(authored, "a", body="repo")
        _age(_skill(live, "a", body="live edit") / "SKILL.md", 100)

        refused = skills.skills_deploy()
        assert refused.ok is False and "a" in refused.details
        assert "live edit" in (live / "a" / "SKILL.md").read_text()

        forced = skills.skills_deploy(force=True)
        assert forced.ok is True, forced.details
        assert "repo" in (live / "a" / "SKILL.md").read_text()

    def test_files_deleted_from_the_repo_are_removed_live(self, env):
        _, authored, live, _ = env
        source = _skill(authored, "a")
        (source / "old.md").write_text("stale")
        assert skills.skills_deploy().ok is True
        (source / "old.md").unlink()

        result = skills.skills_deploy()

        assert result.ok is True, result.details
        assert not (live / "a" / "old.md").exists()
        assert skills._compare("a")[0] == "ok"
        assert not list(live.glob(".*.staging"))

    def test_codex_link_conflict_copies_nothing(self, env):
        _, authored, live, codex = env
        _skill(authored, "a")
        codex.mkdir(parents=True)
        (codex / "a").mkdir()  # a real directory where a link is expected
        result = skills.skills_deploy()
        assert result.ok is False and "conflict" in result.summary
        assert not (live / "a").exists()


class TestSaveLive:
    def test_all_saves_unlisted_live_skills_but_not_third_party_or_links(self, env):
        repo, authored, live, _ = env
        _skill(live, "mine")
        _skill(live, "vendor")  # listed in the third-party lock
        _skill(live, "known")
        (repo / "skills.keep").write_text("# kept\nknown\n")
        elsewhere = _skill(repo, "npx-canonical")
        (live / "npx-link").symlink_to(elsewhere, target_is_directory=True)

        result = skills.skills_save_live("all")

        assert result.ok is True, result.details
        assert (authored / "mine" / "SKILL.md").is_file()
        assert not (authored / "vendor").exists() and not (authored / "npx-link").exists()
        assert (repo / "skills.keep").read_text().splitlines() == ["# kept", "known", "mine"]

    def test_named_skill_must_exist_live(self, env):
        result = skills.skills_save_live("nope")
        assert result.ok is False and "SKIPPED nope" in result.details

    def test_named_save_mirrors_live_deletions_into_the_repo(self, env):
        _, authored, live, _ = env
        (_skill(authored, "a") / "old.md").write_text("stale")
        _skill(live, "a")
        result = skills.skills_save_live("a")
        assert result.ok is True, result.details
        assert not (authored / "a" / "old.md").exists()

    @pytest.mark.parametrize("bad", ["../escape", "a/b", ".hidden", ".."])
    def test_rejects_paths_and_dot_names(self, env, bad):
        result = skills.skills_save_live(bad)
        assert result.ok is False and "not a skill name" in result.summary

    def test_needs_a_repo_checkout(self, env, monkeypatch):
        monkeypatch.setattr(skills, "repo_root", lambda: None)
        assert skills.skills_save_live("").ok is False


class TestThirdParty:
    def test_save_lock_copies_the_live_lock(self, env):
        repo, *_ = env
        live_lock = skills.live_lock_path()
        live_lock.parent.mkdir(parents=True)
        live_lock.write_text(
            json.dumps({"version": 3, "skills": {"a": {"source": "é", "skillFolderHash": "x"}}})
        )
        result = skills.skills_thirdparty_save_lock()
        assert result.ok is True
        saved = (repo / "third-party-skills.lock.json").read_text()
        assert saved.endswith("}\n") and '"é"' in saved

    def test_save_lock_without_a_live_lock_fails(self, env):
        assert skills.skills_thirdparty_save_lock().ok is False

    @pytest.mark.parametrize(
        ("code", "ok", "warning"), [(0, True, False), (2, True, True), (1, False, False)]
    )
    def test_install_maps_exit_codes(self, env, code, ok, warning):
        replay = MagicMock(returncode=code, stdout="", stderr="skills: boom")
        clean_drift = MagicMock(returncode=0, stdout="", stderr="")
        with (
            patch.object(skills, "_support", return_value=clean_drift),
            patch.object(skills, "run", return_value=replay) as fake_run,
        ):
            result = skills.skills_thirdparty_install()
        assert (result.ok, result.warning) == (ok, warning)
        assert fake_run.call_args.kwargs["env"]["STRICT"] == "1"

    def test_install_aborts_when_installed_copies_were_edited(self, env):
        edited = MagicMock(returncode=1, stdout="", stderr="DIFFERS vendor: edited since install")
        with (
            patch.object(skills, "_support", return_value=edited),
            patch.object(skills, "run") as fake_run,
        ):
            result = skills.skills_thirdparty_install()
        assert result.ok is False and "aborted" in result.summary
        fake_run.assert_not_called()
