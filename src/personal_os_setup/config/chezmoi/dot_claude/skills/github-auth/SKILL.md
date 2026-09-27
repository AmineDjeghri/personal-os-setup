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

This skill sets up authentication so the agent can work with GitHub repositories, PRs, issues, and
CI. **`gh` CLI is the default path — ask to install it if it's missing, don't reach for a personal access
token instead.** One `gh auth login` wires both API access and git credentials in a single step, no
manual scope-picking, no long-lived secret to store on disk. The git-only PAT/SSH method further
down exists only for the rare case where `gh` genuinely cannot be installed.

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

# Linux with a package manager + sudo available
sudo apt install gh          # Debian/Ubuntu (may need the cli.github.com apt repo first)
sudo dnf install gh          # Fedora
sudo pacman -S github-cli    # Arch/CachyOS

# macOS
brew install gh

# Windows
winget install --id GitHub.cli
```

Verify with `gh --version` before moving on. If none of these are possible (fully offline, no
package manager, no write access to extract a binary anywhere on `PATH`) — that's the actual trigger
for "Method 2: Git-only" below, not just "gh happens to not be installed yet."

---

## Method 1: gh CLI Authentication

If `gh` is installed (see above if it isn't), it handles both API access and git credentials in one
step — this is the default for every scenario, interactive or headless.

### Interactive Browser Login (Desktop)

```bash
gh auth login
# Select: GitHub.com
# Select: HTTPS
# Authenticate via browser
```

### Device Code Flow (Headless / Remote Servers)

```bash
gh auth login
```
**Agent Pattern:** Since this is interactive, run it in the background and redirect output to a log
file (e.g., `gh auth login > /tmp/gh_auth.log 2>&1`) using `terminal(background=true)`. This allows
the agent to retrieve and share the device code with the user without blocking the session.

1. Run `gh auth login`.
2. Choose `GitHub.com` -> `HTTPS` -> `Login with a web browser`.
3. The CLI will output a one-time device code and a link to `github.com/login/device`.
4. Share the code with the user; they authorize the session in their browser.
5. Run `gh auth setup-git` to link the authentication to git.

### Token-Based Login (only when a token already exists — e.g. a CI secret)

```bash
echo "<THEIR_TOKEN>" | gh auth login --with-token
gh auth setup-git
```

This is for wiring an *already-issued* token (a scoped CI secret, a fine-grained PAT someone already
created for automation) into `gh` — it is not a reason to go generate a new PAT for a human's own
setup when the browser/device flow above is available.

### Verify

```bash
gh auth status
```

---

## Method 2: Git-Only Authentication (last resort — `gh` cannot be installed)

This works on any machine with `git` installed. No root access needed.

### Option A: HTTPS with Personal Access Token

Only reach for this when `gh` truly cannot be installed (see the Detection Flow above) — a PAT is a
long-lived, manually-scoped secret that a human has to create, remember to rotate, and store on
disk, none of which `gh auth login` requires.

**Step 1: Create a personal access token**

Classic PAT with `repo` + `workflow` scopes (add `read:org` for org repos) at **https://github.com/settings/tokens**.

**Step 2: Configure git to store the token**

```bash
# Set up the credential helper to cache credentials
git config --global credential.helper store
```

⚠️ **`store` saves the token to `~/.git-credentials` in PLAINTEXT** — anyone who can read that file
has the token. The `cache` alternative below avoids writing it to disk at all; prefer it unless the
credentials need to persist across reboots.

```bash

# Now do a test operation that triggers auth — git will prompt for credentials
# Username: <their-github-username>
# Password: <paste the personal access token, NOT their GitHub password>
git ls-remote https://github.com/<their-username>/<any-repo>.git
```

After entering credentials once, they're saved and reused for all future operations.

**Alternative: cache helper (credentials expire from memory)**

```bash
# Cache in memory for 8 hours (28800 seconds) instead of saving to disk
git config --global credential.helper 'cache --timeout=28800'
```

**Alternative: set the token directly in the remote URL (per-repo)**

```bash
# Embed token in the remote URL (avoids credential prompts entirely)
git remote set-url origin https://<username>:<token>@github.com/<owner>/<repo>.git
```

**Step 3: Configure git identity** — owned by the `repo-conventions` skill.

**Step 4: Verify**

```bash
# Test push access (this should work without any prompts now)
git ls-remote https://github.com/<their-username>/<any-repo>.git

# Verify identity
git config --global user.name
git config --global user.email
```

### Option B: SSH Key Authentication

Good for users who prefer SSH or already have keys set up.

**Step 1: Check for existing SSH keys**

```bash
ls -la ~/.ssh/id_*.pub 2>/dev/null || echo "No SSH keys found"
```

**Step 2: Generate a key if needed**

```bash
# Generate an ed25519 key (modern, secure, fast)
ssh-keygen -t ed25519 -C "their-email@example.com" -f ~/.ssh/id_ed25519 -N ""

# Display the public key for them to add to GitHub
cat ~/.ssh/id_ed25519.pub
```

Add the public key at **https://github.com/settings/keys**.

**Step 3: Test the connection**

```bash
ssh -T git@github.com
# Expected: "Hi <username>! You've successfully authenticated..."
```

**Step 4: Configure git to use SSH for GitHub**

```bash
# Rewrite HTTPS GitHub URLs to SSH automatically
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

**Step 5: Configure git identity** — owned by the `repo-conventions` skill.

---

## Using the GitHub API Without gh

Only needed once `gh` is confirmed uninstallable (see the Detection Flow above) — otherwise install
`gh` and use `gh api` instead. Genuine fallback: `references/rest-api-fallback.md`.

### Helper: Detect Auth Method

Use this pattern at the start of any GitHub workflow:

```bash
# Try gh first, fall back to git + curl
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  echo "AUTH_METHOD=gh"
elif [ -n "$GITHUB_TOKEN" ]; then
  echo "AUTH_METHOD=curl"
elif [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
  export GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
  echo "AUTH_METHOD=curl"
elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
  export GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
  echo "AUTH_METHOD=curl"
else
  echo "AUTH_METHOD=none"
  echo "Need to set up authentication first"
fi
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `git push` asks for password | GitHub disabled password auth. Use a personal access token as the password, or switch to SSH |
| `remote: Permission to X denied` | Token may lack `repo` scope — regenerate with correct scopes |
| `fatal: Authentication failed` | Cached credentials may be stale — run `git credential reject` then re-authenticate |
| `ssh: connect to host github.com port 22: Connection refused` | Try SSH over HTTPS port: add `Host github.com` with `Port 443` and `Hostname ssh.github.com` to `~/.ssh/config` |
| Credentials not persisting | Check `git config --global credential.helper` — must be `store` or `cache` |
| Multiple GitHub accounts | Use SSH with different keys per host alias in `~/.ssh/config`, or per-repo credential URLs |
| `gh: command not found` | Install it — see "Installing `gh`" above, no sudo required (prebuilt binary to `~/.local/bin`) |
