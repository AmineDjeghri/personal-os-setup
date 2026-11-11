# Delegating a repo task in print mode

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
