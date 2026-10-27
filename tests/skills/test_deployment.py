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


def test_replay_and_authored_deployment(tmp_path):
    tmp = tmp_path
    bins = tmp / "bin"
    bins.mkdir()
    fixture = tmp / "fixture"
    fixture.mkdir()
    (fixture / "SKILL.md").write_text(
        "---\nname: example\ndescription: Fixture\n---\nInstructions.\n"
    )
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
    npx = bins / "npx"
    npx.write_text(
        "#!"
        + sys.executable
        + "\n"
        + """import json,os,pathlib,shutil,sys
args=sys.argv
agent=args[args.index('-a')+1]
with open(os.environ['SMOKE_CALLS'],'a') as f: f.write(agent+'\\n')
if os.environ.get('SMOKE_FAIL')==agent: sys.exit(1)
root=os.environ['SKILLS_DST'] if agent=='claude-code' else os.environ['SKILLS_CODEX_DST']
shutil.copytree(os.environ['SMOKE_FIXTURE'],pathlib.Path(root)/'example',dirs_exist_ok=True)
shutil.copyfile(os.environ['LOCK'],os.environ['LIVE_SKILLS_LOCK'])
"""
    )
    npx.chmod(0o755)
    env = dict(
        os.environ,
        PATH=str(bins) + ":" + os.environ["PATH"],
        SKILLS_PYTHON=sys.executable,
        LOCK=str(lock),
        SKILLS_DST=str(tmp / "claude"),
        SKILLS_CODEX_DST=str(tmp / "codex"),
        LIVE_SKILLS_LOCK=str(tmp / "live.json"),
        SKILLS_RECEIPTS=str(tmp / "receipts.json"),
        STAMP=str(tmp / "stamp"),
        STRICT="1",
        SMOKE_CALLS=str(tmp / "calls"),
        SMOKE_FIXTURE=str(fixture),
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

    result = replay()
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (tmp / "calls").read_text().splitlines() == ["claude-code", "codex"]
    result = replay()
    assert result.returncode == 0 and "nothing to do" in result.stdout, result
    assert len((tmp / "calls").read_text().splitlines()) == 2
    (tmp / "codex/example/SKILL.md").unlink()
    result = replay()
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (tmp / "codex/example/SKILL.md").is_file()
    assert len((tmp / "calls").read_text().splitlines()) == 4
    result = replay(AGENT="codex", FORCE="1")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (tmp / "calls").read_text().splitlines()[-1] == "codex"
    failed_stamp = tmp / "failed-stamp"
    result = replay(FORCE="1", SMOKE_FAIL="codex", STAMP=str(failed_stamp))
    assert result.returncode != 0 and not failed_stamp.exists()
    no_tools = tmp / "no-tools"
    no_tools.mkdir()
    (no_tools / "dirname").symlink_to(shutil.which("dirname"))
    result = replay(PATH=str(no_tools), STAMP=str(tmp / "missing-tool-stamp"))
    assert result.returncode != 0 and "npx is required" in result.stderr, result
    result = replay(PATH=str(no_tools), STRICT="0", STAMP=str(tmp / "missing-tool-stamp"))
    assert (
        result.returncode == 0
        and "SKIPPED" in result.stderr
        and not (tmp / "missing-tool-stamp").exists()
    )
    result = replay(AGENTS="*")
    assert result.returncode != 0
    # A Windows uname used to skip all work. It must now still reach the installer.
    (bins / "uname").write_text("#!/bin/sh\necho MINGW64_NT\n")
    (bins / "uname").chmod(0o755)
    count = len((tmp / "calls").read_text().splitlines())
    result = replay(FORCE="1")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert len((tmp / "calls").read_text().splitlines()) == count + 2
    args = [
        "make",
        f"SKILLS_DST={tmp}/authored",
        f"SKILLS_CODEX_DST={tmp}/authored-codex",
        f"SKILLS_PYTHON={sys.executable}",
    ]
    for target in ["skills-deploy", "skills-deploy", "skills-diff", "skills-codex-check"]:
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
    bins.mkdir()
    npx = bins / "npx"
    npx.write_text(
        "#!"
        + sys.executable
        + "\n"
        + """import os,pathlib,shutil,sys
args=sys.argv
agent=args[args.index('-a')+1]; name=args[args.index('-s')+1]
root=os.environ['SKILLS_DST'] if agent=='claude-code' else os.environ['SKILLS_CODEX_DST']
skill=pathlib.Path(root)/name;skill.mkdir(parents=True,exist_ok=True)
(skill/'SKILL.md').write_text(f'---\\nname: {name}\\ndescription: Fixture\\n---\\nInstructions.\\n')
shutil.copyfile(os.environ['LOCK'],os.environ['LIVE_SKILLS_LOCK'])
"""
    )
    npx.chmod(0o755)
    env = dict(
        os.environ,
        PATH=str(bins) + ":" + os.environ["PATH"],
        SKILLS_PYTHON=sys.executable,
        SKILLS_DST=str(dest / ".claude/skills"),
        SKILLS_CODEX_DST=str(dest / ".agents/skills"),
        LIVE_SKILLS_LOCK=str(tmp / "live.json"),
        SKILLS_RECEIPTS=str(tmp / "receipts.json"),
        STAMP=str(tmp / "stamp"),
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
    assert (tmp / "stamp").is_file() and (tmp / "receipts.json").is_file()


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
        STAMP=str(tmp_path / "stamp"),
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
    assert not (tmp_path / "stamp").exists()
    for manifest in (source / "dot_claude/skills").glob("*/SKILL.md"):
        target = dest / ".agents/skills" / manifest.parent.name
        assert target.is_symlink() and (target / "SKILL.md").is_file()
