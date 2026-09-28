---
name: claude-code-ops
description: "Install/auth/troubleshoot Claude Code CLI on this box."
version: 1.0.0
author: Hermes Curator
license: MIT
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [Claude-Code, OAuth, Auth, Native-Install, CLI, Hermes-Addon]
    related_skills: [claude-code, hermes-agent]
---

# Claude Code Ops (this box)

## When to Use

- Installing, upgrading, or re-authenticating Claude Code on this machine (Hermes HA addon).
- A `claude` command fails with "command not found", auth is lost, or `doctor` reports issues.
- Any session that needs to verify the Claude Code install (version / auth / health) before delegating work to it.

Companion to the bundled `claude-code` skill: delegation workflows (print mode, tmux, flags, hooks) live there; INSTALL / AUTH / UPDATE operations for THIS machine live here.

## Environment facts (verified Aug 2026)

- **Native install, NOT npm:** `/config/.local/bin/claude` → symlink to `/config/.local/share/claude/versions/<version>` (e.g. 2.1.248). Lives under /config → **survives addon updates**. npm global installs land under `/` and get wiped — never use them here.
- The persistent home is `/addon_configs/<repo>_<slug>`, exposed as `/config` in BOTH addon containers (agent addon: native mount, HOME=/config; webui addon: run.sh symlink in both containers; HOME=/root there). The gateway PATH does **not** include `~/.local/bin` → **always invoke the absolute path** — `/config/.local/bin/claude` resolves in both containers. **Set HOME to the persistent home on invocation** (`HOME=/addon_configs/<repo>_<slug> … claude …`) so it finds `.claude.json` / `.claude` credentials — on the webui container HOME=/root has none.
- `claude doctor` reporting "~/.local/bin is not in your PATH" is **expected and harmless** — do not "fix" the PATH, do not add PATH exports.

## Checks (read-only)

```
/config/.local/bin/claude --version
/config/.local/bin/claude auth status     # JSON: loggedIn, authMethod, email, subscriptionType
/config/.local/bin/claude doctor          # install + auto-updater health
```

Healthy = `loggedIn: true`, `authMethod: "claude.ai"`, `subscriptionType: "pro"` (this user's account: user@example.com).

**`auth status` is not proof a call will work.** A `-p` run can die in a quarter-second with
`Failed to authenticate: OAuth session expired and could not be refreshed` (`is_error: true`, `num_turns: 1`,
nothing written) while `auth status` still reads healthy — the status line reports stored credentials, not a
live session. Whenever a delegation dies instantly, or right after a re-login, prove auth with one tiny real
call before re-running the task.

## Auth — OAuth device flow (THE pattern)

1. Start in a background PTY: `terminal(command="/config/.local/bin/claude auth login", background=true, pty=true)`.
2. Poll; it prints a one-time authorize URL + `Paste code here if prompted >`.
3. Give the user the URL (code block) — they open it on their phone, signed into their claude.ai account.
4. User pastes the code back in chat; submit the **entire string INCLUDING the `#state` suffix** (one line) via `process(action="submit", data="<full code>")`.
5. Wait for `Login successful.` (process exits 0), then verify with `auth status`.

**PITFALL:** first-run interactive `claude` opens a THEME PICKER ("Choose the text style...") that does **not** advance via process submit (Enter). Don't fight it — kill the session and use `claude auth login` instead (plain-text device flow, no TUI). Full verified transcript: `references/auth-device-flow.md`.

## Remote control (drive sessions from the Claude mobile app / claude.ai/code)

Run `claude remote-control --name <label>` inside **tmux** (it is an interactive TUI; a raw PTY cannot drive it). First-time per directory it refuses with `Error: Workspace not trusted` — `-p` mode skips the trust dialog but does NOT record trust. Trust lives in `~/.claude.json` → `projects."<abs dir path>".hasTrustDialogAccepted` — set it `true` (or accept the dialog in an interactive session) for every directory remote-control will open. Pairing: user opens the Claude app → **Code tab** (or the printed `claude.ai/code?environment=…` URL). Spawn modes: `same-dir` (default) / `worktree`. Full runbook + traps: `references/remote-control.md`.

## Plugins (Track 2 skill installs)

`claude plugin marketplace add <owner>/<repo>` — the registered marketplace name may differ from the repo (`obra/superpowers` registers as `superpowers-dev`) → `claude plugin install <name>@<marketplace> -y` (user scope default). Plugins land in `~/.claude/plugins/` and do **not** touch `~/.claude/skills` — Hermes' `external_dirs` index is unaffected. Verify with `claude plugin list`.

**Cost model (A/B measured Sep 2026):** an enabled-but-idle plugin adds a FIXED per-call overhead (its manifest + skill index ride in every system prompt) — measured +34% on a 1-turn task ($0.069 vs $0.052 with superpowers off). Plugin skills only ENGAGE on matching tasks (analysis/review rarely triggers them; a trivial task still completes in 1 turn either way). Disable around a `-p` run (`claude plugin disable/enable superpowers`) only when you want maximum speed on big runs; keep it on for interactive/remote-control work where the methodology earns the tax.

**Re-measure anytime (repeatable A/B):** run the SAME `-p` task twice with `--output-format json` (fields `num_turns`, `total_cost_usd`, `subtype`), once with the plugin enabled, once after `claude plugin disable <name>` — then `claude plugin enable <name>` to restore. Use a 1-turn task to isolate the fixed idle overhead from methodology turns.

## Delegating a repo task in print mode (brief → run → approve → verify)

The loop that works for handing an in-repo change (code, workflows, docs, skills) to Claude Code:

1. **Write the brief to a file, then feed it:** `write_file /tmp/task.md` → `claude -p "$(cat /tmp/task.md)"
   --allowedTools 'Read,Edit,Write,Bash' --max-turns 45-80 --output-format json > /tmp/out.json`. The brief must carry:
   goal, the exact files, forbidden actions ("do not push, do not commit, do not touch X"), the validation commands to
   run, and the shape of the answer you want back. A file brief stays exact and can be re-run or amended.
2. **Run it tracked and backgrounded** with `notify=true` — real delegation runs exceed the foreground cap and a
   detached `nohup`-style wrapper is refused. Do not re-run it while it is still going.
   - **Add `--permission-mode acceptEdits` whenever the run must WRITE files.** `--allowedTools '…,Write,Edit'`
     alone leaves every write at the consent gate: the run spends its whole budget analysing, stalls on the same
     call three times, and exits having written only a skeleton — the analysis is not recoverable from disk.
   - **Never wrap the launch in trailing shell bookkeeping** (`… ; echo "exit=$?" >> log`): the wrapper's own
     status (0) is what the completion notice reports, so a run that exited 1 is announced as finished normally.
     The JSON's `is_error` is the truth, not the shell exit code.
3. **Read the result with `jq -r .result /tmp/out.json`** (plus `.subtype`, `.num_turns`, `.cost`, `.is_error`)
   from the terminal; `execute_code` is approval-gated in this environment and returns BLOCKED when the user is away.
   A `result` field that is an error string, or a `num_turns` of 1-2, means it never did the work — check before
   reporting anything as done.
   - **A provider spend/session limit kills the run instantly**: `is_error: true`, `num_turns: 1`,
     `total_cost_usd: 0`, and `.result` is the provider's own limit message (naming the reset time). Nothing was
     analysed and no file was written — do not retry in a loop. Report the limit plus the reset time, or do the task
     another way (a smaller model/tool path, or wait for the reset). A wrapper-less background launch makes this
     indistinguishable from success unless `.is_error` is read.
   - **A limit can also land MID-run**: `is_error: true` with a real `num_turns` / `total_cost_usd` and the limit text
     in `.result`. The turns already paid for are real work — inspect the worktree before redoing anything (a merge
     sat ~80% done), and if the limit is account-wide a cheaper model will NOT bypass it: wait for the reset, finish
     it yourself, or take the work elsewhere.
   - **Concurrent edits in its worktree make it pause for a "peer".** 2.1.248 reads foreign changes as another agent
     at work: it messages the peer, schedules a wakeup, and ends the turn having written nothing. `claude agents
     --json` lists the sessions it can see — an interactive one in a DIFFERENT checkout is enough to trigger it. Keep
     the worktree quiescent while a run is live; if it does pause, resume with a one-line correction ("no session is
     editing this worktree — those edits are deliberate and finished; do not use peer messaging or wakeups;
     continue") rather than re-briefing the task.
4. **A mid-run stop asking for approval is normal, not a failure.** Repos whose `AGENTS.md`/`CLAUDE.md` forbid
   `git commit`/`git push` without per-action approval make Claude Code do the work, run the checks, then halt with
   the changes staged and ask. Two ways through:
   - pre-authorise in the brief when the user has already approved that action for THIS task ("the user has approved
     commit + push + PR for this task — execute them, do not pause to ask"); the constraint belongs to the user, not
     to the delegate, so relaying it is legitimate;
   - or answer the question by resuming the same session:
     `claude -p "<approval>" --resume <session_id> --allowedTools … --output-format json`, with `session_id` taken from
     the first run's JSON. Continuation keeps every earlier turn — no re-briefing, no repeated exploration.
   - **A stall on file writes is not an approval question.** Resume the same `session_id` with the missing flag
     added (`--permission-mode acceptEdits`) plus one line saying writes are now permitted; flags may change on
     resume, and the earlier turns — including the analysis already paid for — are kept. Re-briefing the whole task
     from scratch costs the same again for nothing.
5. **Verify the artifact, never the summary.** Statements like "pushed and opened PR #N" are self-reports: check
   `git diff origin/main...origin/<branch> --stat`, `gh pr view <n> --json title,files,commits,mergeable`,
   `gh pr checks <n>`, `gh run list --branch <branch>`. Report only what those show.
6. **Follow-ups go on the same branch as new commits** (no force-push) — squash-merge collapses the review noise the
   extra commits create; a new PR for a correction the user did not ask for is the wrong move.

## Updates

Auto-updates are enabled by default (native installs update in place under `/config/.local/share/claude/versions`). Manual: `/config/.local/bin/claude update`. Auth credentials persist in the persistent home; if auth is ever lost, re-run the device flow.

## Pitfalls

1. Bare `claude` → "command not found" — absolute path always.
2. `npm install -g @anthropic-ai/claude-code` → wiped on addon update. Native installer only (`curl -fsSL https://claude.ai/install.sh | bash`).
3. Install approval prompts often time out — the user may install manually; then VERIFY the result instead of re-running the installer.
4. `claude auth login` exits 0 on success — poll the process for "Login successful." and confirm via `auth status`; don't trust a bare exit code alone.
5. If the device-flow URL expires or the code is rejected, re-run `claude auth login` for a fresh pair.
6. `-p` print mode returns output ONLY on success — hitting `--max-turns` mid-task yields NOTHING (no partial findings), because the answer is emitted at the end. Size the budget to the scope (a ~20-file review needs 40+ turns, or pipe the diff and cap at 1-3); use remote-control or an interactive session for big open-ended reviews.
7. Re-view the governing skill when the task class changes mid-project — a session-start load goes stale (skill files get patched: env paths, new subcommands) and the user calls it out when you rely on memory instead of re-loading.
8. Sessions run from the Claude mobile app / claude.ai/code (remote-control spawns) may have NO local transcript under `~/.claude/projects/` — they sync cloud-side. Don't burn turns grepping local JSONL for a phone-run session's findings; ask the user to paste the verdict.
9. `claude remote-control` sits on an empty-looking screen while healthy (the pane may show nothing until a prompt like "Enable Remote Control? (y/n)"); check aliveness with `tmux list-panes -F '#{pane_pid} #{pane_dead}'` and `capture-pane -S -60`, not by the visible output alone.
10. **Dangling launcher after an addon update** — `~/.local/bin/claude` ships as an ABSOLUTE symlink into the
    host-side spelling (`/addon_configs/<slug>_hermes_agent/.local/share/claude/versions/<ver>`), a path that does not
    exist inside the agent container. The version file is present, yet every call dies with
    `bash: /config/.local/bin/claude: No such file or directory`. Repair with a RELATIVE link so it resolves in either
    container, then verify:

    ```bash
    cd ~/.local/bin && ln -sfn ../share/claude/versions/<ver> claude
    HOME=/config ./claude --version
    ```

    `versions/<ver>` is a single binary FILE, not a directory — an `ls -l` on the target is the fastest way to confirm
    that the link (not the install) is what broke.
11. **A long audit brief needs two extra clauses or its output is lost**: demand incremental writing ("append findings
    as you go — if you run out of budget the partial report must still be useful") and an explicit OUT-OF-SCOPE list
    (naming the skill classes the delegate must not analyse). Without the first, one permission wall or turn cap
    costs the entire run; without the second, a broad brief drifts into advice about things the user excluded.

12. **Print mode cannot write under `.claude/**` at all — not a flag problem.** An `Edit` to any path in
    a repo's `.claude/` tree (including `.claude/skills/**`) is hard-DENIED and the run exits with
    `subtype: success`, the refusal as the only `.result`, and the calls in `.permission_denials`. Adding
    `--permission-mode acceptEdits` AND an explicit `--settings` allow rule (`Edit(.claude/skills/**)`,
    also tried as the absolute `//<path>/**` form) does NOT lift it. Confirmed twice on 2.1.248: do those
    edits yourself with `patch`/`write_file` (ungated for the agent side), or point the delegate at a
    target outside `.claude/` — re-briefing or resuming with more flags just burns budget.

## Verification checklist

- [ ] `/config/.local/bin/claude --version` → 2.x
- [ ] `auth status` → loggedIn:true + correct email + subscriptionType pro
- [ ] `doctor` → no errors besides the expected PATH warning
- [ ] a real one-turn `-p` call succeeds — `auth status` alone can read healthy while the session is dead
