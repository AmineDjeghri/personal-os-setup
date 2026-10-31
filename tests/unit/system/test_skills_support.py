"""Isolated filesystem checks for shared agent skill deployment."""

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def support():
    path = (
        Path(__file__).resolve().parents[3]
        / "src/personal_os_setup/config/chezmoi/dot_claude/skills_support.py"
    )
    spec = importlib.util.spec_from_file_location("skills_support", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_skill(root, name="example"):
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Example fixture\n---\nInstructions.\n"
    )
    return directory


@pytest.fixture
def installation(tmp_path):
    roots = {"claude-code": tmp_path / "claude", "codex": tmp_path / "codex"}
    for root in roots.values():
        write_skill(root)
    data = {
        "version": 3,
        "skills": {"example": {"source": "example/repo", "skillFolderHash": "fixture-tree"}},
    }
    lock = tmp_path / "lock.json"
    live = tmp_path / "live.json"
    for path in (lock, live):
        path.write_text(json.dumps(data))
    return lock, live, tmp_path / "receipts.json", list(roots), roots


def test_authored_links_are_repeatable_and_follow_updates(support, tmp_path):
    source, claude, codex = [tmp_path / name for name in ("source", "claude", "codex")]
    write_skill(source)
    write_skill(claude)
    support.link_authored(source, claude, codex)
    support.link_authored(source, claude, codex)
    updated = claude / "example/SKILL.md"
    updated.write_text(updated.read_text() + "Updated.\n")
    assert (codex / "example").is_symlink()
    assert (codex / "example/SKILL.md").read_text() == updated.read_text()
    support.link_authored(source, claude, codex, check=True)


@pytest.mark.parametrize("conflict", ["directory", "wrong-link", "broken-link"])
def test_authored_conflict_preserves_every_destination(support, tmp_path, conflict):
    source, claude, codex = [tmp_path / name for name in ("source", "claude", "codex")]
    for name in ("aaa", "zzz"):
        write_skill(source, name)
        write_skill(claude, name)
    codex.mkdir()
    destination = codex / "zzz"
    if conflict == "directory":
        write_skill(codex, "zzz")
    else:
        destination.symlink_to(tmp_path / conflict, target_is_directory=True)
    with pytest.raises(ValueError, match="CONFLICT"):
        support.link_authored(source, claude, codex)
    assert not (codex / "aaa").exists()
    assert destination.exists() or destination.is_symlink()


def test_link_preflight_allows_fresh_deploy_and_check_rejects_missing(support, tmp_path):
    source, claude, codex = [tmp_path / name for name in ("source", "claude", "codex")]
    write_skill(source)
    support.link_authored(source, claude, codex, preflight=True)
    assert not codex.exists()
    with pytest.raises(ValueError, match="MISSING"):
        support.link_authored(source, claude, codex, check=True)


def test_matching_locks_do_not_prove_content_is_installed(support, installation):
    lock, live, receipts, agents, roots = installation
    (roots["codex"] / "example/SKILL.md").unlink()
    with pytest.raises(OSError):
        support.verify_installations(lock, live, receipts, agents, roots)


def test_receipts_are_required_for_existing_installs(support, installation):
    with pytest.raises(ValueError, match="MISSING content receipts"):
        support.verify_installations(*installation)


def test_record_then_verify_both_agents(support, installation):
    support.verify_installations(*installation, record=True)
    support.verify_installations(*installation)


@pytest.mark.parametrize("agent", ["claude-code", "codex"])
def test_edited_supporting_file_fails_verification(support, installation, agent):
    support.verify_installations(*installation, record=True)
    directory = installation[-1][agent] / "example"
    (directory / "reference.md").write_text("Local edit.\n")
    with pytest.raises(ValueError, match=f"DRIFT {agent}/example"):
        support.verify_installations(*installation)


def test_record_refuses_lock_drift(support, installation):
    lock, live, receipts, agents, roots = installation
    data = json.loads(live.read_text())
    data["skills"]["example"]["skillFolderHash"] = "changed-tree"
    live.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="live lock differs"):
        support.verify_installations(lock, live, receipts, agents, roots, record=True)
    assert not receipts.exists()


def test_manifest_name_must_match_directory(support, installation):
    directory = installation[-1]["codex"] / "example"
    (directory / "SKILL.md").write_text("---\nname: other\ndescription: Example\n---\n")
    with pytest.raises(ValueError, match="name/description mismatch"):
        support.verify_installations(*installation, record=True)


def test_third_party_symlinks_are_not_copy_installs(support, installation, tmp_path):
    roots = installation[-1]
    original = roots["codex"] / "example"
    moved = tmp_path / "elsewhere"
    original.rename(moved)
    original.symlink_to(moved, target_is_directory=True)
    with pytest.raises(ValueError, match="real --copy installation"):
        support.verify_installations(*installation, record=True)


@pytest.mark.parametrize("value", ["*", "hermes-agent", "codex hermes-agent", ""])
def test_agent_selection_rejects_duplicate_hermes_routes(support, value):
    with pytest.raises(ValueError, match="agents must be"):
        support.selected_agents(value)


def test_agent_selection_supports_both_and_deduplicates(support):
    assert support.selected_agents("claude-code codex codex") == ["claude-code", "codex"]


def test_lock_path_traversal_is_rejected(support, tmp_path):
    path = tmp_path / "lock.json"
    path.write_text(json.dumps({"version": 3, "skills": {"../escape": {}}}))
    with pytest.raises(ValueError, match="invalid skill name"):
        support.load_skills(path)


def test_single_agent_receipt_update_preserves_other_agent(support, installation):
    lock, live, receipts, agents, roots = installation
    support.verify_installations(*installation, record=True)
    support.verify_installations(lock, live, receipts, ["codex"], roots, record=True)
    support.verify_installations(lock, live, receipts, agents, roots)
