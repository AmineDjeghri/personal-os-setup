# Pruning the Hermes source checkout (refs, tags, packs)

The add-on's checkout is both its source and its history; it accumulates refs from old fetches and one pack per
update. This is the safe sequence — it never re-clones and never touches the worktree.

## Why it piles up
- The original clone/fetch used the stock wildcard refspec `+refs/heads/*:refs/remotes/origin/*`, so every upstream
  branch (canary, feature, per-commit branches) stays as a remote-tracking ref. Observed on an install that had
  never pruned: **3,290 remote refs + 179 tags, `.git` 915 MB**.
- Current code fetches `--no-tags` and a single branch/commit — Hermes' installer and the add-on selector alike
  (`git fetch --no-tags origin <branch|commit>` → `merge --ff-only FETCH_HEAD`) — so new bloat stops, but nothing
  prunes existing refs, and the wildcard refspec re-creates them on the next plain `git fetch`.

## Sequence (only on an explicit go-ahead, run from inside `<install>`)
1. **Backup refs** (the restore lever, not optional):
   `git for-each-ref --format='%(objectname) %(refname)' > $HERMES_HOME/backups/git-refs-<date>.txt`, with
   `git rev-parse HEAD` and `git stash list` prepended. Restore one ref with `git update-ref <ref> <sha>`.
2. **Fix the refspec first**, or step 3 undoes itself on the next fetch:
   `git config --replace-all remote.origin.fetch '+refs/heads/main:refs/remotes/origin/main'`.
3. **Drop stale remote refs, keep `origin/main`**:
   `git for-each-ref --format='%(refname)' refs/remotes/origin | grep -v '^refs/remotes/origin/main$' | while read -r r; do git update-ref -d "$r"; done`
   then **verify** `git rev-parse origin/main` — a loop like this can drop it too (`origin/HEAD` included).
4. **Tags**: keep only those reachable from HEAD (`git tag --merged main` lists the keepers) and delete the rest;
   deleting ALL tags is wrong because `hermes_cli/version_info.py` renders the version from `git describe --tags`,
   and ~117 release tags cost almost nothing.
5. **Repack**: `git reflog expire --expire=now --all && git gc --prune=now --quiet`, then re-measure.
6. **Prove the install is unchanged**: same `git rev-parse HEAD`; `git status --porcelain` still lists exactly the
   two add-on patch files (`web/src/lib/api.ts`, `web/vite.config.ts`); `hermes --version` identical.

## Measured expectations (calibrate, never promise more)
- refs 3,471 → 120 · `.git` 915 MB → 714 MB · repo 2.0 GB → 1.8 GB · gc 11 s on a 24-pack / 900 MB `.git`.
- The remaining pack is `main`'s own history plus the commits `origin/main` is ahead: **refs were never the bulk**.
  Do not offer multi-GB savings, and do not propose a shallow re-clone over a live install (it drops the
  venv/node_modules layout and the add-on's patches).
- On larger/older checkouts the same `gc` can exceed a foreground tool cap — then run it
  `background=true, notify=true`; a partial pass is harmless and the repo stays consistent.

## Verifying afterwards
- `git count-objects -vH` (`in-pack`, `size-pack`), `git for-each-ref | wc -l`, `git tag | wc -l`.
- `git describe --tags HEAD` still resolves when step 4 kept reachable tags.
- `hermes --version` unchanged and the gateway untouched — no live process reads these refs.

## After refs
Regenerable caches (`cache/uv`, log rotations, `state-snapshots`) and what to leave alone (`venv`, `node_modules`,
`installs/*/environments`): `hermes-addon-lifecycle` → Cleanup answers.
