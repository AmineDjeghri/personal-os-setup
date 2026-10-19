# Claude Code remote control — headless-container runbook

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

- User opens the Claude mobile app → **Code tab** (or the printed `claude.ai/code?environment=…` URL) and can start tasks, watch, steer and approve permission prompts from the phone; kill the server with `tmux kill-session -t claude-rc`.

## Traps

- Interactive first-run onboarding forces a login screen even with valid credentials on disk — do not complete it; use `claude auth login`.
- remote-control sessions belong to the directory they started in; move between projects by starting another remote-control in that directory (or `--spawn=worktree` per session).
- Sessions run from the Claude mobile app / claude.ai/code (remote-control spawns) may have NO local transcript under `~/.claude/projects/` — they sync cloud-side. Don't burn turns grepping local JSONL for a phone-run session's findings; ask the user to paste the verdict.
- `claude remote-control` sits on an empty-looking screen while healthy (the pane may show nothing until a prompt like "Enable Remote Control? (y/n)"); check aliveness with `tmux list-panes -F '#{pane_pid} #{pane_dead}'` and `capture-pane -S -60`, not by the visible output alone.
