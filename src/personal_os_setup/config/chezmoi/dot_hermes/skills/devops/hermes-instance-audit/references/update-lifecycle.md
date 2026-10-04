# Hermes update lifecycle — run, monitor, verify

Depth for the "Update operations" section of SKILL.md: what `hermes update` does in order, how to
tell an update is already in flight, how to watch one to completion without starting a second,
and how to verify the result. The probes here are read-only; the update itself runs only when the
user asks for it.

## 1. Is a run already in flight?

- `$HERMES_HOME/.hermes-update-in-progress` exists exactly while a run is live. Contents are two
  lines: `<pid>` then the start epoch. Written when the run starts, removed when it completes — it
  is the launcher's own truth, so check it before doing anything else.
- While it exists, the launcher stub prints
  `hermes: source-update completion failed: an update is still running; wait for it to exit, then relaunch Hermes; running with the previous dependencies`
  on every new `hermes` launch, and `hermes update` refuses to start another run.
- Process shapes to recognise (one update = a runner plus a completion child):
  - runner: `python3 -I -c "import sys, runpy; sys.path.insert(0, '<install>'); sys.argv = ['<install>/venv/bin/hermes', 'update']; runpy.run_path(...)"`
  - completion: `<python> -I -S -u -X pycache_prefix=$HERMES_HOME/cache/scratch/hermes-completion-<id>/bytecode <install>/hermes_cli/update_completion.py <scratch>/request.json <scratch>/result.json [--prepared]`
  - the `--prepared` child runs under a prepared-environment interpreter:
    `$HERMES_HOME/installs/<sha16 of resolved project root>/environments/<id>/venv/bin/python`.
- Probes: `ls -la $HERMES_HOME/.hermes-update-in-progress`, `ps -o pid,ppid,etime,stat,cmd -p <pid>`,
  `ps -o pid,ppid,etime,stat,cmd --ppid <pid>`. The pid in the marker is the runner, not the
  completion child.
- Marker present with no live process is the case worth investigating (a run that died before its
  completion pass) — report it and let the user decide; do not silently launch a replacement run on
  top of an unfinished install.

## 2. Never run two at once

`logs/update.log` gains a header per attempt (`=== hermes update started <iso> ===`). A refused
attempt logs:

```
✗ Another Hermes update is already running (started 1m 7s ago, process 1092).
  Running two at once would corrupt the install. Wait for it to finish
  (watch `hermes logs`), or close the Desktop/dashboard window that
  started it, then run `hermes update` again.
```

So when the user asks for an update and one is already running, the job is to monitor and verify
that run — never to start a parallel one, and never to kill it.

## 3. Launcher phase (order of a run)

Landmarks, in the order they appear: fleet scan (`→ Fleet: N running service(s) across profiles:
<names>`) · npm lockfile churn discarded · `→ Update channel: <name>` · stale-autostash warning ·
fetch · `→ Local changes detected — stashing before update...` and
`Saved working directory and index state On main: hermes-update-autostash-<ts>` ·
`→ Found N new commit(s)` (or `✓ Already up to date.`) · pull · restore prompt
`Restore local changes now? [Y/n]` then the restore · `✓ Cleared N stale __pycache__ directories` ·
Node dependencies · TUI build (`ui-tui/dist/entry.js`) · web UI build (vite →
`hermes_cli/web_dist`) · `✓ Code updated!` · bundled-skills sync (user-modified skills are KEPT and
counted, with the `hermes skills list-modified` hint) · config-format migration
(`ℹ Updating config format (vN → vM)…`) · then
`✓ Update complete! (<old version> → <new version>) [<branch> @ <sha>]`.

Flags that matter here:

- `--yes/-y` accepts the config-migration and stash-restore prompts and skips API-key entry. The
  interactive `Restore local changes now? [Y/n]` prompt is exactly what stalls a non-interactive
  (agent-driven, PTY-less) update — pass `--yes` for those.
- `--gateway` routes prompts over file-based IPC instead of stdin (how a chat-platform `/update`
  drives the CLI, which has no TTY).
- `--keep-stash` updates but leaves the local changes parked instead of re-applying them.

## 4. Completion phase

After the launcher phase, `update_completion.py` re-installs Python dependencies into the prepared
environment. Visible landmarks: `→ Preparing pinned cua-driver (Computer Use)…` then the fleet
drain `→ <profile>: draining gateway PID N (up to <1995-2025>s)…` and
`✓ Handed gateway profile(s) back to their external supervisor: <profiles>`.

- The drain ceiling is roughly 2000 s (~33 min). A run that looks hung is usually waiting on the
  gateway to exit; read the log tail before concluding anything, and never kill it.
- The version string only moves at the end of this phase. `hermes --version` mid-run still reports
  the OLD version (often with a `.dirty` suffix) — that is not evidence of failure.

## 5. Logs and receipts

| Artifact | Contents |
|---|---|
| `logs/update.log` | launcher level: one header per attempt, guard refusals, stash prompts. First read for "what happened". |
| `logs/hermes-update.log` | the detailed run: builds, skills sync, config migration, version transition, fleet check. |
| `logs/update_receipts/` | receipts for updates triggered from a surface (not a TTY). |
| `telegram_update_receipts_<chat_id>.json` | per-chat map of platform message id → update id/timestamp for `/update` invocations. |

Tail, don't dump: `tail -c 1200 <log>` shows the current phase in one call (progress lines are
rewritten with `\r`, so line-oriented tail can look empty or repeated). `hermes logs` shows
`agent.log`, NOT `update.log` — tell the user the path when they ask why they see nothing.

## 6. Verify a finished run (in this order)

1. `ls $HERMES_HOME/.hermes-update-in-progress` → gone.
2. `hermes --version` → `Hermes Agent vX.Y.Z+<n>.g<sha>[.dirty] … · upstream <sha>`. This is the
   installed metadata, not `git describe`; a `.dirty` suffix means local edits were re-applied
   from the autostash. Expected on a customised checkout.
3. `git -C <install> log -1 --oneline` → matches the `Fleet version check: ✓ <profile> (pid N) @ <shortsha> — up to date` line from the log.
4. `hermes status` → `Gateway: ✓ running` plus the expected platforms.
5. `git -C <install> status --porcelain` → only the user's own files (the restored edits).
6. `git stash list` → `hermes-update-autostash-<ts>` entries. Report leftovers (the run itself
   warns about entries older than 7 days) and never drop one unasked.

## 7. Read-only pre-checks

- `hermes update --check` — behind/ahead and channel; changes nothing. Prints
  `→ Update channel: main` / `✓ Already up to date.`
- `hermes update --plan` — install kind (git/docker/nix), every running Hermes service across all
  profiles with its supervisor and running code version, and how each will be restarted. Read-only
  by design and safe on a live fleet.
- `hermes update --list-venv-holders` — the PIDs a Windows venv-holder guard would refuse on; always
  `[]` off Windows.

## 8. Pitfalls

- Never start a second update while one is in flight; the guard refuses it and two runners corrupt
  the install. Never kill one during the drain.
- A stale version string mid-run is normal — re-check after the completion child exits.
- `.dirty` after an update means the autostash was restored, not that the update failed.
- Report shape: version transition (old → new), gateway state, what came back dirty, what is parked
  (stale stashes) — short bullets, no narration of the steps taken.
