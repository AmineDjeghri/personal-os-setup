---
name: hermes-addon-lifecycle
description: "Use when a Hermes HA add-on image update needs triage."
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Hermes HA add-on lifecycle (read-only triage)

Answers "the add-on updated / here is the changelog — do we need to do something or clean stuff?" about the
**Home Assistant add-on wrapper** around Hermes: image version, option-gated code paths in its entrypoint, the
source checkout it owns, and what that checkout costs on disk. This is a different lifecycle from `hermes update`
(which moves the checkout itself) and from a skills/plugins/config audit (`hermes-instance-audit`): the image
changes the wrapper; the wrapper decides whether the checkout moves at all. Pruning refs/tags: `hermes-addon-maintenance`.

## When to use
- A pasted add-on changelog with "do we need to do something?" · "which add-on version am I on / is there a newer build?"
- "Why is the Hermes checkout dirty/modified after a restart?" · "which update channel is this on?"
- "How do I clean space in the add-on?" — measurements, then stop.

## Hard rules
- **Lead with the verdict.** "No action" is the normal answer for a robustness-only changelog line: say it first,
  then the one or two facts that make it true. No walk through the bullets.
- **Read-only.** Never enable `auto_update`, edit `/data/options.json`, prune the checkout or touch the patch
  script. Cleanup is quoted as numbers and waits for a go-ahead.
- **Do not propose upgrades the user did not ask for.** If the answer is "nothing to do", don't close with a menu.
- **Check `hostname` before reading any option.** Two Hermes add-ons can share one `/config`, each with its own
  `/data/options.json` and slug; `<sha16>-hermes-agent` is the agent container.

## Procedure
1. **Pin the running add-on version** — never from `hermes --version` (core + checkout, with a `.dirty` suffix that
   refers only to the checkout). Supervisor API with the container's own token, response written to a file:

   ```bash
   curl -s -H "Authorization: Bearer $SUPERVISOR_TOKEN" -o /tmp/self.json http://supervisor/addons/self/info
   ```

   `version == version_latest` proves the changelog you were handed is the running image and no build is pending.
2. **Read the real options** (`/data/options.json`) and map each changelog bullet to a branch in the entrypoint:
   `grep -n "AUTO_UPDATE\|GIT_REF\|DESKTOP_BACKEND" /run.sh`. A bullet whose gate is closed here is not a to-do —
   that is the whole answer. Gate table: `references/wrapper-internals.md` §1.
3. **Explain the source state from facts**: `git -C $SRC_DIR log -1 --oneline`, `git status --porcelain`, the
   `source-checks` identity file for "how far behind". A checkout that is behind is NOT broken when
   `auto_update: false` — it is exactly what the option says.
4. **Attribute every modified file before calling it custom** (next section).
5. **Size the disk only if asked**: `df -h /config`, `du -sh $HERMES_HOME/*` sorted, then the checkout's numbers.
6. **One conditional worth knowing** (e.g. what happens if `auto_update` were turned on), in a single bullet.

## The dirty checkout is expected
- The image runs `/usr/local/bin/hermes-dashboard-patches` at every start; it rewrites `web/src/lib/api.ts` and
  `web/vite.config.ts` for HA Ingress and leaves `HA-ADDON-*` markers. Stock result: exactly those two files
  modified plus a `.dirty` version suffix.
- So `git status` there means "is the patch applied?", not "did the user customise it?". Grep the marker before
  judging a modified file; never clean these files or report them as local edits. The add-on stashes, updates and
  re-applies them by marker; stale `hermes-update-autostash` stashes are update bookkeeping (prove with
  `git stash show --name-only stash@{n}` before anyone drops one).
- Upstream drift in a patched pattern prints a `WARNING:` and startup continues by design; a changelog line about
  "unsafe source changes remain errors" concerns the stash/pull path, not this.

## Cleanup answers
- The biggest item is usually the checkout's `.git` (a legacy wildcard fetch leaves thousands of remote-tracking
  refs and every tag). Count refs (`git count-objects -vH`, `git tag | wc -l`, `git branch -a | wc -l`) and read
  `git remote -v` first: `[tree:0]` = partial clone, so no plain `git gc` advice. Measured expectations and the
  pruning sequence (on go-ahead only): `hermes-addon-maintenance`.
- Safe re-downloadable: `cache/uv`, rotated `logs/*.log.N`, `state-snapshots`. `installs/<sha16>/environments/**`
  is LIVE (prepared interpreters) — never label it stale.
- Offer with numbers and wait; do not execute.

## Pitfalls
- `python3 -c` / piping `curl` into `python3` trips the approval gate — write the response to a file, parse it with file tools.
- Quoting `hermes --version` as "the add-on version" is wrong.
- A changelog's "Verification" section describes what the AUTHOR tested; it is not a checklist for this install.
- A checkout ahead of/behind the newest tag can be normal on a branch channel; report both numbers (ahead of tag,
  behind upstream) rather than declaring drift.

## References
- `references/wrapper-internals.md` — option → code-path table for `/run.sh`, where the saved update channel is
  stored, the ingress patch script and its markers, probe commands.
