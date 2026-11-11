"""Black box skill deployment tests: all destinations and installer calls are isolated."""

from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import pytest

pytestmark = pytest.mark.skipif(
    os.name == "nt" or not shutil.which("bash") or not shutil.which("jq"),
    reason="requires POSIX bash and jq; never installs host packages",
)

repo = Path(__file__).resolve().parents[2]
script = (
    repo / "src/personal_os_setup/config/chezmoi/dot_claude/run_after_replay-third-party-skills.sh"
)


FAKE_NPX = """import os, pathlib, shutil, sys
args = sys.argv
agents = [args[i + 1] for i, arg in enumerate(args) if arg == "-a"]
name = args[args.index("-s") + 1]
with open(os.environ.get("SMOKE_CALLS", os.devnull), "a") as calls:
    calls.write(",".join(agents) + "\\n")
if os.environ.get("SMOKE_FAIL") in agents:
    sys.exit(1)
roots = {
    "claude-code": pathlib.Path(os.environ["SKILLS_DST"]),
    "codex": pathlib.Path(os.environ["SKILLS_CODEX_DST"]),
}


def write(directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(
        f"---\\nname: {name}\\ndescription: Fixture\\n---\\nInstructions.\\n"
    )


def clear(path):
    if path.is_symlink():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


if {"claude-code", "codex"} <= set(agents):
    canonical = roots["codex"] / name
    write(canonical)
    link = roots["claude-code"] / name
    clear(link)
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(os.path.relpath(canonical, link.parent), target_is_directory=True)
else:
    for agent in agents:
        clear(roots[agent] / name)
        write(roots[agent] / name)
shutil.copyfile(os.environ["LOCK"], os.environ["LIVE_SKILLS_LOCK"])
"""


def install_fake_npx(bins):
    bins.mkdir()
    npx = bins / "npx"
    npx.write_text("#!" + sys.executable + "\n" + FAKE_NPX)
    npx.chmod(0o755)


def test_replay_and_authored_deployment(tmp_path):
    tmp = tmp_path
    bins = tmp / "bin"
    install_fake_npx(bins)
    lock = tmp / "lock.json"
    lock.write_text(
        json.dumps(
            {
                "version": 3,
                "skills": {
                    "example": {"source": "example/fixture", "skillFolderHash": "fixture-tree"}
                },
            }
        )
    )
    env = dict(
        os.environ,
        PATH=str(bins) + ":" + os.environ["PATH"],
        SKILLS_PYTHON=sys.executable,
        LOCK=str(lock),
        SKILLS_DST=str(tmp / "claude"),
        SKILLS_CODEX_DST=str(tmp / "codex"),
        LIVE_SKILLS_LOCK=str(tmp / "live.json"),
        STRICT="1",
        SMOKE_CALLS=str(tmp / "calls"),
    )
    env.pop("AGENT", None)
    env.pop("AGENTS", None)

    def replay(**updates):
        return subprocess.run(
            [shutil.which("bash"), str(script)],
            env=dict(env, **updates),
            cwd=repo,
            text=True,
            capture_output=True,
        )

    claude_entry, canonical = tmp / "claude/example", tmp / "codex/example"

    def calls():
        return (tmp / "calls").read_text().splitlines()

    # One call names both agents, so the Claude entry is a link to the canonical copy.
    result = replay()
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert calls() == ["claude-code,codex"]
    assert claude_entry.is_symlink() and claude_entry.resolve() == canonical.resolve()
    result = replay()
    assert result.returncode == 0 and "nothing to do" in result.stdout, result
    assert len(calls()) == 1
    # A broken canonical copy is repaired, again with one call.
    (canonical / "SKILL.md").unlink()
    result = replay()
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (canonical / "SKILL.md").is_file() and len(calls()) == 2
    # An independent copy (what single-agent installs leave behind) is turned back into a link.
    claude_entry.unlink()
    shutil.copytree(canonical, claude_entry)
    result = replay()
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert claude_entry.is_symlink() and len(calls()) == 3
    # Selecting one agent installs only it and leaves the other agent's link alone.
    result = replay(AGENT="codex", FORCE="1")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert calls()[-1] == "codex" and claude_entry.is_symlink()
    result = replay(FORCE="1", SMOKE_FAIL="codex")
    assert result.returncode != 0 and "FAIL example (claude-code codex)" in result.stderr
    no_tools = tmp / "no-tools"
    no_tools.mkdir()
    (no_tools / "dirname").symlink_to(shutil.which("dirname"))
    result = replay(PATH=str(no_tools), FORCE="1")
    assert result.returncode != 0 and "npx is required" in result.stderr, result
    result = replay(PATH=str(no_tools), FORCE="1", STRICT="0")
    assert result.returncode == 0 and "SKIPPED" in result.stderr
    result = replay(AGENTS="*")
    assert result.returncode != 0
    # A Windows uname used to skip all work. It must now still reach the installer.
    (bins / "uname").write_text("#!/bin/sh\necho MINGW64_NT\n")
    (bins / "uname").chmod(0o755)
    count = len(calls())
    result = replay(FORCE="1")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert len(calls()) == count + 1
    args = [
        "make",
        f"SKILLS_DST={tmp}/authored",
        f"SKILLS_CODEX_DST={tmp}/authored-codex",
        f"SKILLS_PYTHON={sys.executable}",
        f"HERMES_SKILLS_LIVE={tmp}/hermes",
        f"LIVE_SKILLS_LOCK={tmp}/no-live-lock.json",
    ]
    for target in ["skills-personal-repo-to-live", "skills-personal-repo-to-live", "skills-status"]:
        result = subprocess.run(args + [target], cwd=repo, text=True, capture_output=True)
        assert result.returncode == 0, (target, result.stdout, result.stderr)
    source = repo / "src/personal_os_setup/config/chezmoi/dot_claude/skills"
    assert {p.parent.name for p in (tmp / "authored-codex").glob("*/SKILL.md")} == {
        p.parent.name for p in source.glob("*/SKILL.md")
    }
    env.update(
        SKILLS_DST=str(tmp / "authored"),
        SKILLS_CODEX_DST=str(tmp / "authored-codex"),
        CHEZMOI_SOURCE_DIR=str(repo / "src/personal_os_setup/config/chezmoi"),
    )
    (tmp / "authored-codex/coding-workflow").unlink()
    result = subprocess.run(
        [shutil.which("bash"), str(script.with_name("run_after_zz-link-authored-skills.sh"))],
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (tmp / "authored-codex/coding-workflow").is_symlink()


@pytest.mark.skipif(not shutil.which("chezmoi"), reason="chezmoi is not installed")
def test_fresh_chezmoi_folder_apply(tmp_path):
    tmp = tmp_path
    dest = tmp / "destination"
    dest.mkdir()
    config = tmp / "config.toml"
    config.write_text("")
    bins = tmp / "bin"
    install_fake_npx(bins)
    env = dict(
        os.environ,
        PATH=str(bins) + ":" + os.environ["PATH"],
        SKILLS_PYTHON=sys.executable,
        SKILLS_DST=str(dest / ".claude/skills"),
        SKILLS_CODEX_DST=str(dest / ".agents/skills"),
        LIVE_SKILLS_LOCK=str(tmp / "live.json"),
        LOCK=str(repo / "third-party-skills.lock.json"),
        STRICT="1",
    )
    env.pop("AGENT", None)
    env.pop("AGENTS", None)
    args = [
        "chezmoi",
        "--source",
        str(repo),
        "--destination",
        str(dest),
        "--config",
        str(config),
        "--cache",
        str(tmp / "cache"),
        "--persistent-state",
        str(tmp / "state.boltdb"),
        "--refresh-externals=never",
        "apply",
        "--force",
        str(dest / ".claude"),
    ]
    for _ in range(2):
        result = subprocess.run(args, cwd=dest, env=env, text=True, capture_output=True)

        assert result.returncode == 0, (result.stdout[-10000:], result.stderr)
    source = repo / "src/personal_os_setup/config/chezmoi/dot_claude/skills"
    authored = {p.parent.name for p in source.glob("*/SKILL.md")}
    third_party = set(json.loads((repo / "third-party-skills.lock.json").read_text())["skills"])
    assert {
        p.parent.name for p in (dest / ".agents/skills").glob("*/SKILL.md")
    } == authored | third_party
    assert {p.name for p in (dest / ".agents/skills").iterdir() if p.is_symlink()} == authored
    for name in authored:
        assert (dest / ".agents/skills" / name).resolve() == dest / ".claude/skills" / name
    for name in third_party:
        entry = dest / ".claude/skills" / name
        assert entry.is_symlink() and entry.resolve() == dest / ".agents/skills" / name


@pytest.mark.skipif(not shutil.which("chezmoi"), reason="chezmoi is not installed")
def test_packaged_chezmoi_source_links_authored_without_checkout(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(repo / "src/personal_os_setup/config/chezmoi/dot_claude", source / "dot_claude")
    dest = tmp_path / "destination"
    dest.mkdir()
    config = tmp_path / "config.toml"
    config.write_text("")
    env = dict(
        os.environ,
        SKILLS_PYTHON=sys.executable,
        SKILLS_DST=str(dest / ".claude/skills"),
        SKILLS_CODEX_DST=str(dest / ".agents/skills"),
        STRICT="0",
    )
    env.pop("LOCK", None)
    result = subprocess.run(
        [
            "chezmoi",
            "--source",
            str(source),
            "--destination",
            str(dest),
            "--config",
            str(config),
            "--cache",
            str(tmp_path / "cache"),
            "--persistent-state",
            str(tmp_path / "state.boltdb"),
            "--refresh-externals=never",
            "apply",
            "--force",
            str(dest / ".claude"),
        ],
        cwd=dest,
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "SKIPPED repository lock not found" in result.stderr
    for manifest in (source / "dot_claude/skills").glob("*/SKILL.md"):
        target = dest / ".agents/skills" / manifest.parent.name
        assert target.is_symlink() and (target / "SKILL.md").is_file()
