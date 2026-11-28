---
name: pre-install-audit
description: Use before installing an AUR package, GitHub repo, script or app. Static-audits it first.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Pre-install audit

Reads third-party install code BEFORE it runs and returns OK / REVIEW / AVOID with the exact trigger lines.
Fetch-and-read only: it never builds, installs or executes the target. Static checks lower the risk, they do not
remove it (an attacker can hide code in the upstream tarball or ship it later in an update).

## When to use
- "Is this AUR package / repo / install script safe?" — before `yay`, `paru`, `makepkg`, `git clone && ./install.sh`,
  `curl | sh`, `pip install git+…`, `npm i <unknown>`.
- Adding a third-party pacman repo or key: no script covers that — read the repo's signing-key owner and `pacman.conf`
  snippet by hand and treat it as a separate trust decision.
- Not for: official distro packages, or a runtime/malware scan of something already installed.

## Run it

```bash
S=~/.claude/skills/pre-install-audit/scripts/audit.py
python3 $S aur <package>            # PKGBUILD, .install, git history, RPC metadata
python3 $S github <owner/repo>      # shallow clone + repo/owner metadata + install-hook scan
python3 $S url <https://…/install.sh>   # download to a temp dir, scan, print sha256
python3 $S path <dir-or-file>       # local checkout
# add --json for machine output; exit code 0=OK, 1=REVIEW, 2=AVOID
```

## What it checks
- **Hard flags (AVOID):** download piped to a shell, decoded payload executed, reverse-shell patterns, raw-IP URLs,
  plain-HTTP downloads, unknown AUR package.
- **Review flags:** URL shorteners and paste hosts, `base64`/`eval`, network calls, setuid bits, systemd/cron/autostart/
  shell-rc persistence, credential/browser/wallet paths, `sudo` inside install logic, long encoded blobs, npm lifecycle
  scripts, `SKIP` checksums on non-VCS sources, unpinned VCS sources, source hosts that are not a known forge.
- **AUR metadata:** maintainer or orphan state, votes, popularity, package age, several git authors (maintainer change).
- **GitHub metadata:** stars, repo and owner age, fork-of-another-repo, archived.
- On GitHub repos and URLs only install-time files (Makefile, `*.sh`, `setup.py`, `package.json`, Dockerfile, units…)
  are scanned for review flags; tests/docs dirs are skipped.

## Procedure
1. Run the matching mode. Completion: a verdict line printed.
2. **AVOID** → do not install; tell the user the line. **REVIEW** → open each flagged file at the flagged line and decide
   whether the use is expected for that project (e.g. `sudo` in a package manager's installer is). **OK** → still check
   the upstream URL is the project's real homepage.
3. Report: verdict, the lines that decided it, and anything the scan cannot see (upstream tarball contents).
4. Only after the user agrees, hand back the install command. Never run it as part of the audit.

## Pitfalls
- A clean scan is not a safety proof: it reads install scripts, not the compiled/vendored code they fetch.
- Findings repeat per file as `(+N more)`: open the file for the full list.
- GitHub API rate limits drop the metadata block (scan still runs); set no token, just retry later.
- For AUR, `paru`'s own PKGBUILD review prompt stays on (`SkipReview` off): this skill pre-digests, it does not replace it.
- Pin what you audited: record the commit or sha256 and reinstall only that revision, since AUR/VCS sources can change.

## Verification
`python3 $S aur <known-good>` returns a verdict and `scanned:` lists PKGBUILD; `python3 $S aur no-such-pkg-xyz` exits 2.
Tests: `tests/skills/test_pre_install_audit.py`.
