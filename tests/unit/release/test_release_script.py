"""Run release control flow with explicit Git, uv, Make and GitHub stubs; no remote mutations."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(
    os.name == "nt" or not shutil.which("bash"),
    reason="POSIX release shell; archive/source/parser checks also run on Windows",
)

# Each external command has an explicit stateful fixture implementation. Unknown calls fail.
STUB = r"""import json, os, pathlib, shutil, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
root = pathlib.Path(os.environ['FIXTURE_ROOT'])
with (root / 'calls.jsonl').open('a') as stream:
    stream.write(json.dumps([name, args]) + '\n')
state_path = root / 'state.json'
state = json.loads(state_path.read_text())
remote = root / 'remote'
if name == 'git':
    if args == ['rev-parse', '--abbrev-ref', 'HEAD']:
        print(os.environ.get('STUB_BRANCH', 'main'))
    elif args == ['status', '--porcelain']:
        print(os.environ.get('STUB_DIRTY', ''), end='')
    elif args[:1] == ['fetch']:
        pass
    elif args[:1] == ['rev-parse']:
        ref = args[-1]
        if ref == 'HEAD': print('head')
        elif ref == 'origin/main': print('other' if os.environ.get('STUB_DIVERGED') else 'head')
        elif ref == 'FETCH_HEAD^{commit}': print(os.environ.get('STUB_REMOTE_TAG', 'head'))
        elif ref.startswith('refs/tags/'):
            if not state['tagged']: sys.exit(1)
            print('old' if os.environ.get('STUB_TAG_OTHER') else 'head')
        else: raise AssertionError(args)
    elif args[:1] == ['config']:
        print('Fixture' if args[-1] == 'user.name' else 'fixture@example.invalid')
    else: raise AssertionError(args)
elif name == 'uv':
    if args == ['version', '--short']:
        print(state['version'])
    elif 'scripts/check_artifacts.py' in args:
        index = args.index('scripts/check_artifacts.py')
        os.execv(sys.executable, [sys.executable, os.environ['ARTIFACT_CHECK'], *args[index+1:]])
    elif 'scripts/check_release_source.py' in args:
        if os.environ.get('STUB_SOURCE_FAILURE'): sys.exit(1)
    elif 'semantic-release' in args and '--print' in args:
        print(os.environ.get('STUB_NEXT', state['version']))
    elif 'semantic-release' in args:
        assert '--no-vcs-release' in args, args
        state.update(tagged=True, version=os.environ['STUB_NEXT'])
        state_path.write_text(json.dumps(state))
    else: raise AssertionError(args)
elif name == 'make':
    assert args in (['--no-print-directory', 'build-package'], ['--no-print-directory', 'test-wheel']), args
elif name == 'gh':
    assert args[0] == 'release', args
    action = args[1]
    if action == 'view':
        if not remote.exists(): sys.exit(1)
        if args[args.index('--json')+1] == 'assets':
            print('\n'.join(p.name for p in remote.iterdir() if p.name != '.draft'))
        else:
            print(str((remote / '.draft').exists()).lower())
    elif action == 'create':
        assert '--draft' in args and '--verify-tag' in args, args
        remote.mkdir()
        (remote / '.draft').touch()
    elif action == 'download':
        asset = remote / args[args.index('--pattern')+1]
        shutil.copyfile(asset, pathlib.Path(args[args.index('--dir')+1]) / asset.name)
    elif action == 'upload':
        assert '--clobber' not in args
        if os.environ.get('STUB_UPLOAD_FAILURE'): sys.exit(1)
        for file in args[3:]: shutil.copyfile(file, remote / pathlib.Path(file).name)
    elif action == 'edit':
        assert '--draft=false' in args, args
        (remote / '.draft').unlink()
    else: raise AssertionError(args)
else: raise AssertionError((name,args))
"""


@pytest.fixture
def release_shell(tmp_path, artifacts):
    _, _, wheel, sdist = artifacts()
    bins = tmp_path / "bin"
    bins.mkdir()
    for name in ("git", "uv", "make", "gh"):
        path = bins / name
        path.write_text(f"#!{sys.executable}\n" + STUB)
        path.chmod(0o755)
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"version": "2.20.0", "tagged": True}))
    log = tmp_path / "calls.jsonl"
    outputs = tmp_path / "outputs"
    env = dict(
        os.environ,
        PATH=str(bins) + os.pathsep + os.environ["PATH"],
        UV=str(bins / "uv"),
        GH_TOKEN="fixture-token",
        RELEASE_SHA="tested",
        FIXTURE_ROOT=str(tmp_path),
        ARTIFACT_CHECK=str(REPO / "scripts/check_artifacts.py"),
        GITHUB_OUTPUT=str(outputs),
    )

    def run(action, **updates):
        log.write_text("")
        outputs.write_text("")
        result = subprocess.run(
            [shutil.which("bash"), str(REPO / "scripts/release.sh"), action],
            cwd=tmp_path,
            env=dict(env, **updates),
            text=True,
            capture_output=True,
        )
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        return result, calls

    return SimpleNamespace(
        run=run,
        root=tmp_path,
        remote=tmp_path / "remote",
        wheel=wheel,
        sdist=sdist,
        state=state,
        outputs=outputs,
    )


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        ({"STUB_BRANCH": "feature/example"}, "main only"),
        ({"STUB_DIRTY": " M source.py"}, "uncommitted changes"),
        ({"STUB_DIVERGED": "1"}, "not in sync"),
        ({"RELEASE_SHA": ""}, "revision that passed required CI"),
    ],
)
def test_version_guards_precede_release_commands(release_shell, settings, message):
    result, calls = release_shell.run("version", **settings)
    assert result.returncode != 0 and message in result.stderr
    assert not any(name == "gh" or "semantic-release" in args for name, args in calls)


def test_new_untested_tip_is_rejected_before_versioning(release_shell):
    result, calls = release_shell.run("version", STUB_SOURCE_FAILURE="1")
    assert result.returncode != 0
    assert not any(name == "gh" or "semantic-release" in args for name, args in calls)


def test_existing_head_tag_resumes_instead_of_reporting_no_release(release_shell):
    result, _ = release_shell.run("version")
    assert result.returncode == 0, result.stderr
    assert "released=true" in release_shell.outputs.read_text()
    assert "version=2.20.0" in release_shell.outputs.read_text()


def test_new_version_defers_public_release(release_shell):
    release_shell.state.write_text(json.dumps({"version": "2.20.0", "tagged": False}))
    result, calls = release_shell.run("version", STUB_NEXT="2.21.0")
    assert result.returncode == 0, result.stderr
    assert any("--no-vcs-release" in args for _, args in calls)
    assert not any(name == "gh" for name, _ in calls)


def test_no_releasable_commits_remains_successful(release_shell):
    result, calls = release_shell.run("version", STUB_TAG_OTHER="1")
    assert result.returncode == 0, result.stderr
    assert "released=false" in release_shell.outputs.read_text()
    assert not any(name == "gh" for name, _ in calls)


def test_complete_pair_is_verified_before_draft_publication(release_shell):
    result, calls = release_shell.run("assets")
    assert result.returncode == 0, result.stdout + result.stderr
    actions = [args[1] for name, args in calls if name == "gh"]
    assert actions.index("upload") < actions.index("download") < actions.index("edit")
    assert not (release_shell.remote / ".draft").exists()
    assert (
        release_shell.remote / release_shell.wheel.name
    ).read_bytes() == release_shell.wheel.read_bytes()


def test_partial_upload_retry_only_uploads_missing_asset(release_shell):
    release_shell.remote.mkdir()
    (release_shell.remote / ".draft").touch()
    shutil.copyfile(release_shell.wheel, release_shell.remote / release_shell.wheel.name)
    result, calls = release_shell.run("release")
    assert result.returncode == 0, result.stdout + result.stderr
    uploads = [args[3:] for name, args in calls if name == "gh" and args[1] == "upload"]
    assert uploads == [[f"dist/{release_shell.sdist.name}"]]
    assert any(name == "make" for name, _ in calls), "retry must rerun artifact/runtime validation"
    result, calls = release_shell.run("assets")
    assert result.returncode == 0, result.stderr
    assert not any(name == "gh" and args[1] in ("upload", "edit") for name, args in calls)


def test_different_existing_asset_is_never_overwritten(release_shell):
    release_shell.remote.mkdir()
    (release_shell.remote / release_shell.wheel.name).write_bytes(b"different published artifact")
    result, calls = release_shell.run("assets")
    assert result.returncode != 0 and "existing release asset differs" in result.stderr
    assert not any(name == "gh" and args[1] in ("upload", "edit") for name, args in calls)


def test_failed_upload_leaves_draft_and_retry_finishes(release_shell):
    result, _ = release_shell.run("assets", STUB_UPLOAD_FAILURE="1")
    assert result.returncode != 0
    assert (release_shell.remote / ".draft").exists()
    result, _ = release_shell.run("assets")
    assert result.returncode == 0, result.stderr
    assert not (release_shell.remote / ".draft").exists()


@pytest.mark.parametrize("damage", ["missing-sdist", "dirty-tree", "remote-tag"])
def test_assets_reject_invalid_inputs_before_github(release_shell, damage):
    settings = {}
    if damage == "missing-sdist":
        release_shell.sdist.unlink()
    elif damage == "dirty-tree":
        settings["STUB_DIRTY"] = " M source.py"
    else:
        settings["STUB_REMOTE_TAG"] = "other"
    result, calls = release_shell.run("assets", **settings)
    assert result.returncode != 0
    assert not any(name == "gh" for name, _ in calls)
