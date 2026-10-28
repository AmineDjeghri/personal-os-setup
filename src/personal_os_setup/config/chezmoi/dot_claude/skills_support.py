"""Link authored skills and verify agent-specific third-party installations.

The npx lock contains upstream Git tree IDs, not hashes of installed files (the
installer filters and transforms files). Keep local content receipts separately.
This module uses only the standard library so chezmoi can run it without uv sync.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys


def selected_agents(value):
    """Accept only agents whose global directories this deployment owns."""
    agents = list(dict.fromkeys(value.split()))
    if not agents or set(agents) - {"claude-code", "codex"}:
        raise ValueError("agents must be claude-code and/or codex (never '*' or hermes-agent)")
    return agents


def load_skills(path):
    """Read a v3 npx lock and reject names that could escape the skill root."""
    lock = json.loads(path.read_text())
    if lock.get("version") != 3 or not isinstance(lock.get("skills"), dict):
        raise ValueError(f"{path}: expected a version 3 skills lock")
    for name, entry in lock["skills"].items():
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", name):
            raise ValueError(f"invalid skill name: {name}")
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("source"), str)
            or not entry["source"]
        ):
            raise ValueError(f"{name}: missing source")
        if not isinstance(entry.get("skillFolderHash"), str) or not entry["skillFolderHash"]:
            raise ValueError(f"{name}: missing skillFolderHash")
    return lock["skills"]


def link_authored(source, claude, codex, *, check=False, preflight=False):
    """Preflight every destination before creating any authored Codex links."""
    manifests = sorted(source.glob("*/SKILL.md"))
    if not manifests:
        raise ValueError(f"no authored skills in {source}")
    for manifest in manifests:
        target = (claude / manifest.parent.name).absolute()
        link = codex / manifest.parent.name
        if link.is_symlink() and link.resolve() == target.resolve():
            pass
        elif link.exists() or link.is_symlink():
            raise ValueError(f"CONFLICT {link}: expected a link to {target}; reconcile manually")
        elif check:
            raise ValueError(f"MISSING {link}: run make skills-repo-to-live")
        if not preflight and not (target / "SKILL.md").is_file():
            raise ValueError(f"MISSING {target}/SKILL.md: deploy authored files first")
    if not check and not preflight:
        codex.mkdir(parents=True, exist_ok=True)
        for manifest in manifests:
            link = codex / manifest.parent.name
            if not link.is_symlink():
                link.symlink_to(
                    (claude / manifest.parent.name).absolute(), target_is_directory=True
                )
            print(f"LINKED {link}")


def content_hash(directory, name):
    """Hash installed paths, modes and bytes; require a matching skill manifest."""
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"MISSING {directory}: expected a real --copy installation")
    manifest = directory / "SKILL.md"
    if manifest.is_symlink():
        raise ValueError(f"INVALID {manifest}: manifest must be a regular file")
    text = manifest.read_text()
    sections = text.split("---", 2)
    if len(sections) != 3 or sections[0].strip():
        raise ValueError(f"INVALID {manifest}: missing frontmatter")
    metadata = sections[1]
    match = re.search(r"^name:\s*['\"]?([^'\"\r\n]+?)['\"]?\s*$", metadata, re.MULTILINE)
    if (
        not match
        or match.group(1) != name
        or not re.search(r"^description:\s*\S", metadata, re.MULTILINE)
    ):
        raise ValueError(f"INVALID {manifest}: name/description mismatch")
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.name == ".DS_Store":
            continue
        if path.is_symlink():
            raise ValueError(f"INVALID {path}: --copy installation contains a symlink")
        if path.is_file():
            relative = path.relative_to(directory).as_posix().encode()
            contents = path.read_bytes()
            executable = bool(path.stat().st_mode & 0o111)
            digest.update(f"{len(relative)}:{len(contents)}:{executable}:".encode())
            digest.update(relative)
            digest.update(contents)
    return digest.hexdigest()


def installed_snapshot(skills, agents, roots):
    """Collect content receipts for every requested agent and skill."""
    return {
        agent: {
            name: {
                "source": entry["source"],
                "upstream": entry["skillFolderHash"],
                "content": content_hash(roots[agent] / name, name),
            }
            for name, entry in skills.items()
        }
        for agent in agents
    }


def verify_installations(lock, live_lock, receipts, agents, roots, *, record=False):
    """Require matching lock identities and actual unchanged installed content."""
    expected = load_skills(lock)
    live = load_skills(live_lock)
    for name, entry in expected.items():
        have = live.get(name, {})
        if any(have.get(key) != entry[key] for key in ("source", "skillFolderHash")):
            raise ValueError(f"DRIFT {name}: live lock differs; review upstream and save the lock")
    if set(live) - set(expected):
        raise ValueError(
            "EXTRA skills in live lock: review and run make skills-thirdparty-live-to-repo"
        )
    snapshot = installed_snapshot(expected, agents, roots)
    if record:
        saved = json.loads(receipts.read_text()) if receipts.exists() else {}
        saved.update(snapshot)
        receipts.parent.mkdir(parents=True, exist_ok=True)
        temporary = receipts.with_suffix(".tmp")
        temporary.write_text(json.dumps(saved, indent=2) + "\n")
        temporary.replace(receipts)
    else:
        if not receipts.is_file():
            raise ValueError("MISSING content receipts: run make skills-thirdparty-repo-to-live")
        saved = json.loads(receipts.read_text())
        for agent in agents:
            for name, entry in snapshot[agent].items():
                if saved.get(agent, {}).get(name) != entry:
                    raise ValueError(
                        f"DRIFT {agent}/{name}: installed files changed or receipt missing"
                    )
    print(f"OK installed content for {', '.join(agents)} ({len(expected)} skills each)")


def main():
    """Run the shared Make/chezmoi helpers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["link", "verify", "record", "agents", "plan"])
    parser.add_argument("--source", type=Path)
    parser.add_argument(
        "--claude",
        type=Path,
        default=Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "skills",
    )
    parser.add_argument("--codex", type=Path, default=Path.home() / ".agents/skills")
    parser.add_argument(
        "--agents", default=os.environ.get("AGENT") or os.environ.get("AGENTS", "claude-code codex")
    )
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--live-lock", type=Path)
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    parser.add_argument(
        "--receipts", type=Path, default=state / "personal-os-setup/skills-installed.json"
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "link":
            if args.source is None:
                raise ValueError("--source is required")
            link_authored(
                args.source, args.claude, args.codex, check=args.check, preflight=args.preflight
            )
        else:
            agents = selected_agents(args.agents)
            if args.command == "agents":
                print(" ".join(agents))
                return 0
            if args.command == "plan":
                if args.lock is None:
                    raise ValueError("--lock is required")
                roots = {"claude-code": args.claude, "codex": args.codex}
                for name in load_skills(args.lock):
                    authored = Path(__file__).resolve().parent / "skills" / name
                    if authored.exists():
                        raise ValueError(f"CONFLICT {name}: third-party name is repo-authored")
                    for agent in agents:
                        if (roots[agent] / name).is_symlink():
                            raise ValueError(
                                f"CONFLICT {agent}/{name}: refusing to overwrite a symlink"
                            )
                return 0
            if args.lock is None or args.live_lock is None:
                raise ValueError("--lock and --live-lock are required")
            verify_installations(
                args.lock,
                args.live_lock,
                args.receipts,
                agents,
                {"claude-code": args.claude, "codex": args.codex},
                record=args.command == "record",
            )
    except (OSError, ValueError) as error:
        print(f"skills: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
