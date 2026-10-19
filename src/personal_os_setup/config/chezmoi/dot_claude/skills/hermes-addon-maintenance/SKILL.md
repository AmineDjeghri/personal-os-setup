---
name: hermes-addon-maintenance
description: "Use when pruning refs, tags or stashes in the Hermes HA add-on's source checkout."
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Hermes HA add-on: source-checkout pruning

Safe cleanup of the Hermes source checkout the add-on manages ("`.git` is huge", ref/tag pile-up, disk pressure).
Version/changelog triage, option gates and the expected-dirty tree are `hermes-addon-lifecycle` — read it first;
this skill only starts when the user has asked for the cleanup.

## Hard rules
- **Read-only until asked.** Deleting refs, tags, stashes or caches is a separate, explicitly approved action:
  state what you will delete and what it reclaims, then act.
- **Never re-clone over a live install** to "clean" it: that discards the live `venv`/`node_modules` state and the
  add-on's patches. Never delete ALL tags (see Pitfalls).
- **Short chat answer**: verdict, numbers, one caveat; no unrequested menus.
- Ref/tag bloat is the real item: neither `hermes update` nor the add-on selector prunes refs that already exist
  (they only stop new bloat with `--no-tags` + one ref). Procedure, numbers, restore path:
  `references/source-checkout-refs.md`.
- Stale `hermes-update-autostash` stashes: prove they hold only add-on patch files
  (`git stash show --name-only stash@{n}`), back the refs up, then drop.

## Pitfalls
- **Path-limited git commands hang on a promisor checkout** (`remote.origin.partialclonefilter=tree:0`,
  `[tree:0]` in `git remote -v`): `git log -- <path>`, `git diff <ref> -- <path>` and any pathspec history walk can
  pass a 180 s timeout. Use commit-only commands (`git log --oneline -1`, `rev-list --count`, `tag --merged main`)
  and explicit timeouts.
- **The version string is built from tags** (`hermes_cli/version_info.py`, `git describe --tags`): keep everything
  reachable from HEAD or `hermes --version` degrades for no space gain.
- **Bulk ref deletion can take `origin/main` with it.** After any `update-ref -d` loop re-verify
  `git rev-parse origin/main`; the ref backup you wrote first is the restore path, not a re-clone.
- **A narrow fetch refspec does not break updates**: the add-on selector and Hermes fetch explicit branches/commits
  into `FETCH_HEAD`, so `+refs/heads/main:refs/remotes/origin/main` is safe.

## References
- `references/source-checkout-refs.md` — verified pruning sequence, refspec fix, backup/restore, gc expectations.
