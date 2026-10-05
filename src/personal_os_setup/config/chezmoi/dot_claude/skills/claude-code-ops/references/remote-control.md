# Claude Code remote control — headless-container runbook (verified Sep 2026)

Goal: run a Claude Code session on an HA addon container and steer it from the Claude mobile app (Code tab) or claude.ai/code.

## Prerequisites (all three bite, in order)

1. **tmux installed.** `claude remote-control` (and the interactive TUI generally) renders a full-screen interface that a raw PTY cannot drive — theme-picker prompts visibly do not advance on Enter. Install: `apt-get install -y tmux`. tmux lives in the overlay → reinstall after every addon update.
2. **Workspace trust accepted for the target directory.** remote-control refuses untrusted dirs with `Error: Workspace not trusted. Please run claude in <dir> first…`. `claude -p` runs skip the trust dialog but do NOT record trust. Trust is stored in `~/.claude.json`:
   ```json
   "projects": { "/abs/dir/path": { "hasTrustDialogAccepted": true, … } }
   ```
   Accepting interactively requires surviving the first-run onboarding TUI (theme picker → forced OAuth login screen even when credentials exist) — fragile in a pty. The reliable path: patch `hasTrustDialogAccepted` to `true` for each directory you will remote-control.
3. **Account pairing.** Auth must be a Claude account (Pro/Max) login — API-key/console auth does not pair with the mobile app. Verify: `claude auth status` → `Login method: Claude (Pro|Max) account`.

## Launch

```sh
# inside tmux (persists across chat disconnects; dies on container restart)
tmux new-session -d -s claude-rc -x 140 -y 40 "cd <workdir>; HOME=<persistent-home> <persistent-home>/.local/bin/claude remote-control --name <label>"
```

It answers two interactive prompts: `Enable Remote Control? (y/n)` → `y`; then spawn mode `[1] same-dir / [2] worktree` → `1` (same-dir; worktree creates isolated git worktrees per session). Ready banner: `✔︎ Ready · <project> · <branch>` + `Capacity: 0/32` + a `claude.ai/code?environment=…` URL. Drive prompts with `tmux send-keys`, monitor with `tmux capture-pane -t claude-rc -p -S -N`.

## Pairing & use

- User opens the Claude mobile app → **Code tab** → the machine/session appears; or browses to the printed `claude.ai/code?environment=…` URL.
- Sessions spawn in the remote-control workdir; user can start tasks, watch, steer, and approve permission prompts from the phone. Superpowers (plugin) is active in these sessions.
- The tmux window holds the server; kill with `tmux kill-session -t claude-rc`.

## Traps

- The OAuth URL Claude prints wraps across pane lines at its own width — `tmux capture-pane -J` still won't join it (hard newlines). Grab it from the pane before the prompt overwrites, or re-run `claude auth login` for a clean single-line device flow instead.
- Interactive first-run onboarding forces a login-method screen even with valid credentials on disk — do not complete it; `claude auth login` (device flow) is the supported path (see `auth-device-flow.md`).
- remote-control sessions belong to the directory they started in; move between projects by starting another remote-control in that directory (or `--spawn=worktree` per session).
