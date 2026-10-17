---
name: claude-code-ops
description: "Hermes box: install/auth/model defaults for Claude Code CLI on this box (Sonnet, never Opus)."
version: 1.1.0
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

Install/upgrade/re-auth Claude Code here; `claude: command not found`; verify the install before delegating.
Delegation workflows live in the bundled `claude-code` skill (INSTALL / AUTH / UPDATE for THIS machine live here).

## Model defaults (cost rule — user's standing instruction)

- **Model = the newest Sonnet, always explicit:** `--model claude-sonnet-5-5` (or the alias
  `--model sonnet`, same family). The user's words: *"use Claude 5.5 sonnet per default … don't use
  opus because it is very expensive"*.
- **Never `--model opus`, any version.** The bundled `claude-code` skill's "`--model opus` for complex
  multi-step work" line is **superseded here** — buy reasoning with `--effort high|xhigh`, not with a
  pricier model. `--model haiku` is fine only for a trivial 1-turn task and as `--fallback-model haiku`.
- **Pass `--model` on every run** instead of relying on the account default, so a config/subscription
  change can never silently swap in an expensive model.
- **The newest Sonnet id only appears after `claude update`.** So when
  the user names a model you cannot find, update first, then re-check the binary:

  ```bash
  HOME=/config /config/.local/bin/claude update
  grep -aoE 'claude-(sonnet|opus|fable)-[0-9][a-z0-9.-]*' \
    $(readlink -f /config/.local/bin/claude) | sort -u | tail
  ```

  The updater rewrites `~/.local/bin/claude` as an ABSOLUTE symlink — re-link it relative afterwards (pitfall 4).

## Environment facts

- **Native install, NOT npm:** `/config/.local/bin/claude` → symlink to `/config/.local/share/claude/versions/<version>`. Lives under /config → **survives addon updates**. npm global installs land under `/` and get wiped — never use them here.
- The persistent home is `/addon_configs/<repo>_<slug>`, exposed as `/config` in BOTH addon containers (agent addon: native mount, HOME=/config; webui addon: run.sh symlink in both containers; HOME=/root there). The gateway PATH does **not** include `~/.local/bin` → **always invoke the absolute path** — `/config/.local/bin/claude` resolves in both containers. **Set HOME to the persistent home on invocation** (`HOME=/addon_configs/<repo>_<slug> … claude …`) so it finds `.claude.json` / `.claude` credentials — on the webui container HOME=/root has none.
- `claude doctor` reporting "~/.local/bin is not in your PATH" is **expected and harmless** — do not "fix" the PATH, do not add PATH exports.

## Checks (read-only)

```
/config/.local/bin/claude --version
/config/.local/bin/claude auth status     # JSON: loggedIn, authMethod, email, subscriptionType
/config/.local/bin/claude doctor          # install + auto-updater health
```

Healthy = `loggedIn: true`, `authMethod: "claude.ai"`, `subscriptionType: "pro"`.

**`auth status` is not proof a call will work.** A `-p` run can die in a quarter-second with `Failed to authenticate: OAuth session expired and could not be refreshed` (`is_error: true`, `num_turns: 1`) while `auth status` still reads healthy — after a re-login or an instant delegation death, prove auth with one tiny real call.

## Auth — OAuth device flow (THE pattern)

1. Start in a background PTY: `terminal(command="/config/.local/bin/claude auth login", background=true, pty=true)`.
2. Poll; it prints a one-time authorize URL + `Paste code here if prompted >`.
3. Give the user the URL (code block) — they open it on their phone, signed into their claude.ai account.
4. User pastes the code back in chat; submit the **entire string INCLUDING the `#state` suffix** (one line) via `process(action="submit", data="<full code>")`.
5. Wait for `Login successful.` (process exits 0), then verify with `auth status`.

The URL/code is **one-shot**: if it lapses or is rejected, re-run `claude auth login` for a fresh pair.

**PITFALL:** first-run interactive `claude` opens a THEME PICKER ("Choose the text style...") that does **not** advance via process submit (Enter). Don't fight it — kill the session and use `claude auth login` instead (plain-text device flow, no TUI).

## Remote control (drive sessions from the Claude mobile app / claude.ai/code)

Run `claude remote-control --name <label>` inside **tmux** (interactive TUI; a raw PTY cannot drive it); a directory must be trusted first (`Error: Workspace not trusted`). Pairing, spawn modes, trust setup and traps: `references/remote-control.md`.

## Plugins (plugin-based skill installs)

Install commands: `agent-skills-architecture` → `references/install-and-track-procedures.md`. **Cost rule:** an enabled-but-idle plugin adds fixed per-call overhead (its manifest + skill index ride in every system prompt); `claude plugin disable <name>` around big `-p` runs, re-enable after.

## Delegating a repo task in print mode (brief → run → approve → verify)

The loop that works for handing an in-repo change (code, workflows, docs, skills) to Claude Code:

1. **Write the brief to a file, then feed it:** `write_file /tmp/task.md` → `claude -p "$(cat /tmp/task.md)"
   --allowedTools 'Read,Edit,Write,Bash' --max-turns 45-80 --output-format json > /tmp/out.json`.
   - **Feed that file on stdin** — `claude -p "Execute the task in the document on stdin." < /tmp/task.md` —
     whenever the brief contains parentheses, quotes or backticks: pasted inline it dies in the SHELL before claude starts (`bash: syntax error near unexpected token '('`).
2. **Run it tracked and backgrounded** with `notify=true` — real delegation runs exceed the foreground cap and a
   detached `nohup`-style wrapper is refused. Do not re-run it while it is still going.
   - **Add `--permission-mode acceptEdits` whenever the run must WRITE files** — `--allowedTools` alone leaves every write at the consent gate and the run stalls.
   - **Never wrap the launch in trailing shell bookkeeping** (`… ; echo "exit=$?" >> log`): the wrapper's status (0) is what the completion notice reports; the JSON's `is_error` is the truth.
3. **Read the result with `jq -r .result /tmp/out.json`** (plus `.subtype`, `.num_turns`, `.cost`, `.is_error`)
   from the terminal; `execute_code` is approval-gated in this environment and returns BLOCKED when the user is away.
   A `result` field that is an error string, or a `num_turns` of 1-2, means it never did the work — check before
   reporting anything as done.
   - **A provider spend/session limit kills the run instantly**: `is_error: true`, `num_turns: 1`,
     `total_cost_usd: 0`, and `.result` is the provider's own limit message (naming the reset time). Nothing was
     analysed and no file was written — do not retry in a loop. Report the limit plus the reset time, or do the task
     another way (a smaller model/tool path, or wait for the reset) — if the limit is account-wide a cheaper model will NOT bypass it. A wrapper-less background launch makes this
     indistinguishable from success unless `.is_error` is read.
   - **When the action was already approved by the user, ask ONCE whether to do the edit inline yourself instead of
     stalling until the reset** — a cap can sit hours away. If they say yes, run the same gates you would have asked
     the delegate for, and state plainly in the report that the change came from Hermes, not the delegate: the
     delegation rule is the user's, so only the user can waive it for a run. A limit can also land mid-run (`is_error: true` with real `num_turns`) — inspect the worktree before redoing anything.
   - **Concurrent edits in its worktree make it pause for a "peer".** 2.1.248 reads foreign changes as another agent
     at work: it messages the peer, schedules a wakeup, and ends the turn having written nothing. `claude agents
     --json` lists the sessions it can see — an interactive one in a DIFFERENT checkout is enough to trigger it. Keep
     the worktree quiescent while a run is live; if it does pause, resume with a one-line correction ("no session is
     editing this worktree — those edits are deliberate and finished; do not use peer messaging or wakeups;
     continue") rather than re-briefing the task.
4. **A mid-run stop asking for approval is normal, not a failure.** Repos whose `AGENTS.md`/`CLAUDE.md` forbid
   `git commit`/`git push` without per-action approval make Claude Code halt with the changes staged and ask. Either
   pre-authorise in the brief when the user has already approved that action for THIS task (the constraint belongs to
   the user, so relaying it is legitimate), or resume the same session:
   `claude -p "<approval>" --resume <session_id> --allowedTools … --output-format json` (`session_id` from the first run's JSON; every earlier turn is kept).
   - **A stall on file writes is not an approval question.** Resume the same `session_id` with `--permission-mode acceptEdits`
     plus one line saying writes are now permitted — re-briefing from scratch costs the same again.
5. Statements like "pushed and opened PR #N" are self-reports: check
   `git diff origin/main...origin/<branch> --stat`, `gh pr view <n> --json title,files,commits,mergeable`,
   `gh pr checks <n>`, `gh run list --branch <branch>`. Report only what those show.
   - `git status` the worktree and revert edits the brief did not authorise; treat a delegate's verdict as a claim — re-check each named defect against the primary source.

## Pitfalls

1. Bare `claude` → "command not found" — absolute path always.
2. `npm install -g @anthropic-ai/claude-code` → wiped on addon update. Native installer only (`curl -fsSL https://claude.ai/install.sh | bash`); install approval prompts often time out — the user may install manually, then VERIFY the result instead of re-running the installer.
3. `-p` print mode returns output ONLY on success — hitting `--max-turns` mid-task yields NOTHING. Size the budget to the scope (a ~20-file review needs 40+ turns, or pipe the diff and cap at 1-3); use remote-control or an interactive session for big open-ended reviews.
4. **Dangling launcher after an addon update** — `~/.local/bin/claude` ships as an ABSOLUTE symlink into the
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
5. **A long audit brief needs incremental writing** ("append findings as you go — if you run out of budget the partial report must still be useful") **and an explicit OUT-OF-SCOPE list**, or one permission wall or turn cap costs the entire run and the delegate drifts into topics the user excluded.

6. **Print mode cannot write under `.claude/**` at all — not a flag problem.** An `Edit` to any path in
    a repo's `.claude/` tree (including `.claude/skills/**`) is hard-DENIED and the run exits with
    `subtype: success`, the refusal as the only `.result`, and the calls in `.permission_denials`. Adding
    `--permission-mode acceptEdits` AND an explicit `--settings` allow rule (`Edit(.claude/skills/**)`,
    also tried as the absolute `//<path>/**` form) does NOT lift it. Confirmed twice on 2.1.248: do those
    edits yourself with `patch`/`write_file` (ungated for the agent side), or point the delegate at a
    target outside `.claude/` — re-briefing or resuming with more flags just burns budget.

7. **Never pipe a gate through `head`/`tail` inside an `&&` chain** — the pager's exit status (0) hides a gate that never ran. Run the gate as its own command and check its status; if the worktree env lacks the tool: `uv run --with pre-commit pre-commit run --files <paths>`.

## Verification checklist

- [ ] `/config/.local/bin/claude --version` → 2.x
- [ ] `auth status` → loggedIn:true + correct email + subscriptionType pro
- [ ] `doctor` → no errors besides the expected PATH warning
