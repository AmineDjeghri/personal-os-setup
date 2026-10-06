---
name: github-auth
description: "GitHub auth setup: gh CLI login (default), git-only PAT/SSH as a last resort."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [GitHub, Authentication, Git, gh-cli, SSH, Setup]
    related_skills: [github-pr-workflow, github-code-review, github-issues, github-repo-management]
---

# GitHub Authentication Setup

**`gh` CLI is the default path — ask to install it if it's missing, don't reach for a personal access token instead.** A PAT/SSH key (Method 2) is only for when `gh` genuinely cannot be installed.

## Detection Flow

When a user asks you to work with GitHub, run this check first:

```bash
# Check what's available
git --version
gh --version 2>/dev/null || echo "gh not installed"

# Check if already authenticated
gh auth status 2>/dev/null || echo "gh not authenticated"
```

**Decision tree:**
1. `gh auth status` shows authenticated → use `gh` for everything.
2. `gh` is installed but not authenticated → "Method 1: gh CLI" below.
3. **`gh` is not installed → ask to install it first**, then go to step 2. Only fall through to "Method 2:
   Git-only" if installation genuinely isn't possible (no package manager, no network access to
   fetch the binary, no permission to execute a downloaded binary at all).

### Installing `gh` (no sudo needed on any platform)

```bash
# Linux: prebuilt binary, no root — extract and add to PATH
curl -fsSL https://github.com/cli/cli/releases/latest/download/gh_*_linux_amd64.tar.gz \
  | tar -xz -C ~/.local --strip-components=1   # lands at ~/.local/bin/gh
gh --version
# Linux package managers — pick one (Debian/Ubuntu may need the cli.github.com apt repo):
sudo apt install gh
sudo dnf install gh
sudo pacman -S github-cli
brew install gh                  # macOS
winget install --id GitHub.cli   # Windows
```

---

## Method 1: gh CLI Authentication

If `gh` is installed (see above if it isn't), it handles both API access and git credentials in one
step — this is the default for every scenario, interactive or headless.

### Login (browser or device code)

```bash
gh auth login   # GitHub.com -> HTTPS -> Login with a web browser; prints a one-time code for github.com/login/device
gh auth setup-git   # link the authentication to git
```

**Agent Pattern:** Since this is interactive, run it in the background and redirect output to a log
file (e.g., `gh auth login > /tmp/gh_auth.log 2>&1`) using `terminal(background=true)`. This allows
the agent to retrieve and share the device code with the user without blocking the session.

### Token-Based Login (only when a token already exists — e.g. a CI secret)

```bash
echo "<THEIR_TOKEN>" | gh auth login --with-token   # only for an already-issued token
gh auth setup-git
```

---

## Method 2: Git-Only Authentication (last resort — `gh` cannot be installed)

This works on any machine with `git` installed. No root access needed.

### Option A: HTTPS with Personal Access Token

Classic PAT with `repo` + `workflow` scopes (add `read:org` for org repos) at **https://github.com/settings/tokens**. Then run one
auth-triggering operation (`git ls-remote https://github.com/<their-username>/<any-repo>.git`; username = their GitHub
username, password = the PAT, NOT their GitHub password) after setting a credential helper:

```bash
git config --global credential.helper store
```

⚠️ **`store` saves the token to `~/.git-credentials` in PLAINTEXT** — anyone who can read that file
has the token. The `cache` alternative below avoids writing it to disk at all; prefer it unless the
credentials need to persist across reboots.

```bash
# Cache in memory for 8 hours (28800 seconds) instead of saving to disk
git config --global credential.helper 'cache --timeout=28800'
```

**Alternative: set the token directly in the remote URL (per-repo)**

```bash
# Embed token in the remote URL (avoids credential prompts entirely)
git remote set-url origin https://<username>:<token>@github.com/<owner>/<repo>.git
```

### Option B: SSH Key Authentication

```bash
ssh-keygen -t ed25519 -C "their-email@example.com" -f ~/.ssh/id_ed25519 -N ""   # then add ~/.ssh/id_ed25519.pub at https://github.com/settings/keys
ssh -T git@github.com   # expected: "Hi <username>! You've successfully authenticated..."
git config --global url."git@github.com:".insteadOf "https://github.com/"   # use SSH for GitHub URLs
```

---

## Using the GitHub API Without gh

Only needed once `gh` is confirmed uninstallable (see the Detection Flow above) — otherwise install
`gh` and use `gh api` instead. Genuine fallback: `references/rest-api-fallback.md`.

`source scripts/gh-env.sh` sets `GH_AUTH_METHOD`/`GITHUB_TOKEN`/`GH_OWNER`/`GH_REPO`. `references/rest-api-fallback.md` is the single REST fallback for the whole GitHub family.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `fatal: Authentication failed` | Cached credentials may be stale — run `git credential reject` then re-authenticate |
| `ssh: connect to host github.com port 22: Connection refused` | Try SSH over HTTPS port: add `Host github.com` with `Port 443` and `Hostname ssh.github.com` to `~/.ssh/config` |
| Multiple GitHub accounts | Use SSH with different keys per host alias in `~/.ssh/config`, or per-repo credential URLs |
