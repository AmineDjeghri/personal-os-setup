"""Link authored skills and verify agent-specific third-party installations.

Third-party skills are installed by `npx skills` as symlinks: one canonical copy in
~/.agents/skills (read by Codex) and a link in ~/.claude/skills (read by Claude Code and
Hermes). The npx lock is the only record: it holds the upstream Git tree ID and the
install time of each skill, so a hand edit is detected as files newer than that time.
This module uses only the standard library so chezmoi can run it without uv sync.
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys

# Files may land a moment before npx stamps the lock; only later mtimes count as edits.
EDIT_SLACK_SECONDS = 2


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
            raise ValueError(f"MISSING {link}: run make skills-personal-repo-to-live")
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


def check_installed(directory, name):
    """Require a skill directory (or a link to one) with a matching SKILL.md manifest."""
    if not directory.is_dir():
        raise ValueError(f"MISSING {directory}: not installed")
    manifest = directory / "SKILL.md"
    if not manifest.is_file():
        raise ValueError(f"INVALID {manifest}: missing SKILL.md")
    sections = manifest.read_text().split("---", 2)
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


def read_live_lock(live_lock):
    """Read the npx lock, or an empty record when nothing was installed yet."""
    return load_skills(live_lock) if live_lock and live_lock.is_file() else {}


def pending_installs(lock, live_lock, agents, roots, *, everything=False):
    """List (agent, name, source) still to install: missing, broken or out of step with the lock."""
    live = read_live_lock(live_lock)
    pending = []
    for agent in agents:
        for name, entry in load_skills(lock).items():
            have = live.get(name, {})
            stale = any(have.get(key) != entry[key] for key in ("source", "skillFolderHash"))
            try:
                check_installed(roots[agent] / name, name)
                broken = False
            except ValueError:
                broken = True
            if everything or stale or broken:
                pending.append((agent, name, entry["source"]))
    return pending


def _stamp(moment):
    return datetime.fromtimestamp(moment).strftime("%Y-%m-%d %H:%M:%S")


def installed_drift(lock, live_lock, agents, roots):
    """List installed skills with files newer than the lock's record of the install."""
    live = read_live_lock(live_lock)
    drifted, seen = [], set()
    for name in load_skills(lock):
        recorded = live.get(name, {}).get("updatedAt") or live.get(name, {}).get("installedAt")
        if not recorded:
            continue
        installed_at = datetime.fromisoformat(recorded.replace("Z", "+00:00")).timestamp()
        for agent in agents:
            directory = roots[agent] / name
            if not directory.is_dir() or directory.resolve() in seen:
                continue
            seen.add(directory.resolve())
            files = [p.stat().st_mtime for p in directory.resolve().rglob("*") if p.is_file()]
            if files and max(files) > installed_at + EDIT_SLACK_SECONDS:
                drifted.append(
                    f"{name}: edited since install "
                    f"(files last modified {_stamp(max(files))}, lock updated {_stamp(installed_at)})"
                )
    return drifted


def newer_note(repo_entry, live_entry):
    """Describe which lock entry was updated last (ISO timestamps sort as text)."""
    repo_at = repo_entry.get("updatedAt") or repo_entry.get("installedAt") or "unknown"
    live_at = live_entry.get("updatedAt") or live_entry.get("installedAt") or "unknown"
    green, yellow, reset = ("\033[0;32m", "\033[0;33m", "\033[0m") if sys.stderr.isatty() else ("",) * 3
    if "unknown" in (repo_at, live_at) or repo_at == live_at:
        return f"repo {repo_at}, live {live_at}"
    repo_color, live_color = (yellow, green) if live_at > repo_at else (green, yellow)
    verdict = f"{green}{'live' if live_at > repo_at else 'repo'} is NEWER{reset}"
    return f"repo {repo_color}{repo_at}{reset}, live {live_color}{live_at}{reset} -> {verdict}"


def verify_installations(lock, live_lock, agents, roots):
    """Require matching lock identities and a usable installation per agent and skill."""
    expected = load_skills(lock)
    live = load_skills(live_lock)
    for name, entry in expected.items():
        have = live.get(name, {})
        if any(have.get(key) != entry[key] for key in ("source", "skillFolderHash")):
            raise ValueError(
                f"DRIFT {name}: live lock differs ({newer_note(entry, have)}); "
                "review upstream and save the lock"
            )
    if set(live) - set(expected):
        raise ValueError(
            "EXTRA skills in live lock: review and run make skills-thirdparty-live-to-repo"
        )
    for agent in agents:
        for name in expected:
            check_installed(roots[agent] / name, name)
    print(f"OK installed skills for {', '.join(agents)} ({len(expected)} skills each)")


def main():
    """Run the shared Make/chezmoi helpers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["link", "verify", "agents", "plan", "drift", "todo", "installed"],
    )
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
    parser.add_argument("--name")
    parser.add_argument("--all", action="store_true")
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
            roots = {"claude-code": args.claude, "codex": args.codex}
            if args.command == "installed":
                if args.name is None:
                    raise ValueError("--name is required")
                for agent in agents:
                    check_installed(roots[agent] / args.name, args.name)
                return 0
            if args.lock is None:
                raise ValueError("--lock is required")
            if args.command == "plan":
                for name in load_skills(args.lock):
                    authored = Path(__file__).resolve().parent / "skills" / name
                    if authored.exists():
                        raise ValueError(f"CONFLICT {name}: third-party name is repo-authored")
                    for agent in agents:
                        link = roots[agent] / name
                        # npx itself links the Claude copy to the canonical Codex-side one.
                        npx_link = agent == "claude-code" and (
                            link.resolve() == (roots["codex"] / name).resolve()
                        )
                        if link.is_symlink() and not npx_link:
                            raise ValueError(
                                f"CONFLICT {agent}/{name}: refusing to overwrite a foreign symlink"
                            )
                return 0
            if args.command == "todo":
                for pending in pending_installs(
                    args.lock, args.live_lock, agents, roots, everything=args.all
                ):
                    print("\t".join(pending))
                return 0
            if args.command == "drift":
                drifted = installed_drift(args.lock, args.live_lock, agents, roots)
                for line in drifted:
                    print(f"DIFFERS {line}", file=sys.stderr)
                return 1 if drifted else 0
            if args.live_lock is None:
                raise ValueError("--live-lock is required")
            verify_installations(args.lock, args.live_lock, agents, roots)
    except (OSError, ValueError) as error:
        print(f"skills: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
