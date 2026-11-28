"""Isolated filesystem checks for shared agent skill deployment."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

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
    return lock, live, list(roots), roots


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


def test_matching_locks_do_not_prove_skill_is_installed(support, installation):
    lock, live, agents, roots = installation
    (roots["codex"] / "example/SKILL.md").unlink()
    with pytest.raises(ValueError, match="INVALID"):
        support.verify_installations(lock, live, agents, roots)


def drift_live_lock(live):
    data = json.loads(live.read_text())
    data["skills"]["example"]["skillFolderHash"] = "changed-tree"
    live.write_text(json.dumps(data))


def test_verify_refuses_lock_drift_with_a_distinct_error(support, installation, tmp_path):
    lock, live, agents, roots = installation
    npx_style_install(roots, tmp_path)
    drift_live_lock(live)
    with pytest.raises(support.DriftError, match="live lock differs"):
        support.verify_installations(lock, live, agents, roots)


def test_extra_live_entries_are_advisory_drift(support, installation, tmp_path):
    lock, live, agents, roots = installation
    npx_style_install(roots, tmp_path)
    data = json.loads(live.read_text())
    data["skills"]["other"] = {"source": "o/r", "skillFolderHash": "x"}
    live.write_text(json.dumps(data))
    with pytest.raises(support.DriftError, match="EXTRA"):
        support.verify_installations(lock, live, agents, roots)


def test_broken_installation_outranks_advisory_drift(support, installation):
    lock, live, agents, roots = installation
    drift_live_lock(live)
    with pytest.raises(ValueError, match="UNLINKED") as raised:
        support.verify_installations(lock, live, agents, roots)
    assert not isinstance(raised.value, support.DriftError)


def test_main_exits_2_for_drift_and_1_for_a_broken_install(
    support, installation, tmp_path, monkeypatch
):
    lock, live, agents, roots = installation

    def run_verify():
        argv = ["skills_support.py", "verify", "--lock", str(lock), "--live-lock", str(live)]
        argv += ["--agents", " ".join(agents)]
        argv += ["--claude", str(roots["claude-code"]), "--codex", str(roots["codex"])]
        monkeypatch.setattr("sys.argv", argv)
        return support.main()

    drift_live_lock(live)
    assert run_verify() == support.EXIT_FAILED  # not linked: a real failure
    npx_style_install(roots, tmp_path)
    assert run_verify() == support.EXIT_DRIFT


def test_manifest_name_must_match_directory(support, installation):
    directory = installation[-1]["codex"] / "example"
    (directory / "SKILL.md").write_text("---\nname: other\ndescription: Example\n---\n")
    with pytest.raises(ValueError, match="name/description mismatch"):
        support.verify_installations(*installation)


def npx_style_install(roots, tmp_path):
    """Mimic npx: one canonical copy on the Codex side, a link to it on the Claude side."""
    link = roots["claude-code"] / "example"
    shutil.rmtree(link)
    link.symlink_to(roots["codex"] / "example", target_is_directory=True)
    return link


def test_linked_claude_entry_is_a_valid_installation(support, installation, tmp_path):
    npx_style_install(installation[-1], tmp_path)
    support.verify_installations(*installation)


def test_independent_copies_are_not_a_valid_pair_installation(support, installation):
    with pytest.raises(ValueError, match="UNLINKED"):
        support.verify_installations(*installation)


def test_link_to_another_directory_is_not_the_canonical_link(support, installation, tmp_path):
    lock, live, agents, roots = installation
    other = write_skill(tmp_path / "other")
    link = roots["claude-code"] / "example"
    shutil.rmtree(link)
    link.symlink_to(other, target_is_directory=True)
    with pytest.raises(ValueError, match="UNLINKED"):
        support.verify_installations(lock, live, agents, roots)


@pytest.mark.parametrize("selected", [["codex"], ["claude-code"]])
def test_single_agent_selection_accepts_a_plain_copy(support, installation, selected):
    lock, live, _, roots = installation
    support.verify_installations(lock, live, selected, roots)


def test_pending_lists_one_entry_per_skill_that_needs_work(support, installation, tmp_path):
    lock, live, agents, roots = installation
    npx_style_install(roots, tmp_path)
    assert support.pending_installs(lock, live, agents, roots) == []
    shutil.rmtree(roots["codex"] / "example")  # the Claude link now dangles too
    assert support.pending_installs(lock, live, agents, roots) == [("example", "example/repo")]
    write_skill(roots["codex"])
    assert support.pending_installs(lock, live, agents, roots) == []
    data = json.loads(live.read_text())
    data["skills"]["example"]["skillFolderHash"] = "changed-tree"
    live.write_text(json.dumps(data))
    assert support.pending_installs(lock, live, agents, roots) == [("example", "example/repo")]


def test_pending_repairs_a_copy_by_relinking_it(support, installation):
    lock, live, agents, roots = installation
    assert support.pending_installs(lock, live, agents, roots) == [("example", "example/repo")]
    assert support.pending_installs(lock, live, ["codex"], roots) == []


def test_pending_everything_reinstalls_each_skill_once(support, installation, tmp_path):
    lock, live, agents, roots = installation
    npx_style_install(roots, tmp_path)
    assert support.pending_installs(lock, live, agents, roots, everything=True) == [
        ("example", "example/repo")
    ]


def stamp_lock(live, moment):
    data = json.loads(live.read_text())
    data["skills"]["example"]["updatedAt"] = moment
    live.write_text(json.dumps(data))


def test_drift_reports_a_hand_edit_once_for_a_linked_install(support, installation, tmp_path):
    lock, live, agents, roots = installation
    npx_style_install(roots, tmp_path)
    stamp_lock(live, "2000-01-01T00:00:00.000Z")
    drifted = support.installed_drift(lock, live, agents, roots)
    assert len(drifted) == 1
    assert drifted[0].startswith("example: edited since install")


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


REPLAY = (
    Path(__file__).resolve().parents[3]
    / "src/personal_os_setup/config/chezmoi/dot_claude/run_after_replay-third-party-skills.sh"
)


@pytest.mark.skipif(os.name == "nt", reason="POSIX shell harness (Windows `bash` is WSL)")
@pytest.mark.parametrize(
    ("strict", "expected"),
    [("0", 0), ("1", 2)],
    ids=["chezmoi-replay-warns-and-succeeds", "strict-reports-drift"],
)
def test_replay_script_treats_lock_drift_as_advisory(tmp_path, strict, expected):
    """Drift (verify exit 2) must not fail the chezmoi replay, or authored files never deploy."""
    stub = tmp_path / "python-stub"
    stub.write_text(
        "#!/bin/sh\n"
        'case "$1" in\n'
        "  *skills_support.py) shift ;;\n"
        "esac\n"
        'case "$1" in\n'
        '  agents) echo "claude-code codex" ;;\n'
        '  todo) printf "x\\to/r\\n" ;;\n'
        "  verify) echo 'skills: DRIFT x' >&2; exit 2 ;;\n"
        "esac\n"
    )
    stub.chmod(0o755)
    (tmp_path / "npx").write_text("#!/bin/sh\nexit 0\n")
    (tmp_path / "npx").chmod(0o755)
    lock = tmp_path / "lock.json"
    lock.write_text("{}")
    env = {
        "PATH": f"{tmp_path}:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "SKILLS_PYTHON": str(stub),
        "LOCK": str(lock),
        "LIVE_SKILLS_LOCK": str(tmp_path / "live.json"),
        "STRICT": strict,
    }
    result = subprocess.run(["bash", str(REPLAY)], env=env, capture_output=True, text=True)
    assert result.returncode == expected, result.stdout + result.stderr
