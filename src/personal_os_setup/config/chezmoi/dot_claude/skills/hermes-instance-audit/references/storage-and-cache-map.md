# Storage audit of a Hermes HA add-on

Where the space actually goes, what is safe to remove, and what only LOOKS removable.
Sizes are orders of magnitude from a real audit (agent + webui sharing one tree) — re-measure,
never quote them as current.

## Frame the disk first
`df -h` answers a different question than the user asked: on HAOS the add-on config dir, `/media`,
`/share`, `/data` and the whole docker layer all sit on ONE partition (`/dev/sda8`), so "the add-on"
is a slice of a number that also contains his media library. Report which slice is his add-on's
(`du -sh /config`) and keep other tenants out of the cleanup list.

## Probe recipe (one plain call per line — loops and `$( )` substitutions block)
```
df -h
du -sh /config/* /config/.[a-z]* 2>/dev/null | sort -rh | head -40
du -sh /config/.hermes/* | sort -rh | head -25
du -sh /config/.cache/* /config/.local/share/* /config/workspace/* | sort -rh | head -30
find /config -xdev -type f -size +30M -printf '%s\t%p\n' | sort -rn | head -25
```
The last one is the one that finds the truth; the directory walk alone under-reports because a single
blob/blob-shaped file dominates its parent.

## Map: path → meaning → verdict

| Path (under `/config`) | Typical | What it is | Verdict |
|---|---|---|---|
| `.hermes/hermes-agent/.git` | ~1.9 G | git checkout history, 40+ packfiles | needs a decision — see below |
| `.hermes/hermes-agent/{venv,node_modules}` | ~700 M | the LIVE runtime the gateway runs from | keep |
| `.hermes/tools/*` | ~1.6 G | managed ffmpeg / chromium / node / python runtimes | keep |
| `.hermes/installs/<hash>/environments/<id>/venv` | ~380 M | PM dependency generation | needs a decision |
| `.hermes/state.db` | ~226 M | session/state history | data — vacuum, never delete |
| `.hermes/logs/` | ~77 M | `gateway-exit-diag.log` alone can be 40 M; `.1/.2/.3` are the rotations of a 5 MB-capped log | regenerable |
| `.hermes/cache/{uv,scratch,web}` | ~900 M | uv package cache; scratch self-prunes at 24 h | regenerable |
| `.hermes/skills/.curator_backups/*.tar.gz` | MBs | weekly curator snapshots | keep (restore path) |
| `.npm/_cacache`, `.npm/_npx` | ~1.0 G | npm caches | regenerable |
| `.cache/pre-commit` | ~660 M | per-hook virtualenvs | regenerable (rebuilt on next run) |
| `.cache/huggingface/hub/models--Systran--faster-whisper-*` | 75–465 M each | local STT models | partially regenerable — check config |
| `.cache/{electron,node-gyp,pip}`, `~/.local/share/uv/tools` | ~420 M | download/build caches | regenerable |
| `.local/share/uv/python/cpython-*` | ~100–115 M each | uv-managed interpreters | rebuildable, but referenced — check first |
| `.local/share/claude/versions/<ver>` | ~230 M each | full Claude Code CLI builds | keep newest only |
| `.local/state`, `.config`, `.gitconfig`, `.pki`, `.certs` | small | real user state | keep |
| `.linuxbrew`, `.oh-my-zsh`, `.go`, `.npm-global` | ~300 M | installed shell/tooling | keep |
| `workspace/*/.venv`, `workspace/.worktrees` | ~200 M / 100 M | repo dev envs and extra checkouts | rebuildable — ask |
| `workspace/*` repos, `workspace/jym/models/*.onnx` | 1.2 G | his source and model assets | data |

## Per-item rules (each one cost time to establish)

- **Check the consumer before deleting a model cache.** `stt.provider` + `stt.local.model` in
  `config.yaml` name the ONE faster-whisper size in use (e.g. `local` / `base`); the hub keeps every
  size as a separate `models--Systran--faster-whisper-*` repo, so the unused ones are pure weight.
- **`~/.local/share/claude/versions/` keeps every CLI build whole.** Resolve which one is live
  (`readlink -f <home>/.local/bin/claude`) and keep that one only; the rest are dead copies.
- **uv-managed interpreters are referenced by pin.** Repo venvs and pre-commit hook envs pin a minor
  (a project may pin `==3.13.*`, hooks may ask for `python3.11`), so read the `pyvenv.cfg` files before
  calling an interpreter stale. Deleting one is recoverable but not free — pre-commit re-downloads.
- **The live runtime is off-limits**: the gateway process runs from `<install>/venv/bin/python`, so
  `<install>/venv`, `<install>/node_modules` and `.hermes/tools/*` are never cleanup candidates.
- **PM install generations**: state is `installs/<sha16>/pm-runtime/selected.json`; the generation it
  names is live, older roots are candidates. Never delete an install root before reading `selected.json`
  and the newest `source-completion-pending` / `.install.lock` timestamps.
- **`<install>/.git` is the single biggest item and the price of `hermes update`.** Measure before
  promising savings: a repack (`git gc`) may reclaim a share of the packs; a shallow re-clone is the
  real lever but destroys local modifications and drops the checkout far behind upstream — check
  `git status` and `git rev-list --count HEAD..origin/main` and present it as a decision, not a fix.
- **`installs/<sha16>/environments/<id>/` is LEASED, not selected.** `pm-runtime/selected.json` names only a pm-runtime generation, so an environments read against it makes the env look orphaned. The keeper is `.lease-managed` + a `.leases/` dir with a recent mtime (observed: a 380 MB env whose `.leases` was written the day before = LIVE). Check `.leases` freshness before ever proposing that dir.
- **A nightly-updated install's `.git` is a partial (promisor) clone that accumulates one pack per update.** (`remote.origin.partialclonefilter = tree:0`, `promisor = true`; observed 45 packs / 1.78 GiB, 18 packs from the last 9 days, 428 loose objects, `prune-packable: 51`, 753 commits behind `origin/main`.) Deleting is off the table — `hermes update` needs it; `git gc` / `git repack -ad` is the non-destructive lever, re-measure after, and read `git status` first (user edits live in that tree and a shallow re-clone destroys them).
- **uv interpreters: prove "unused" against the pre-commit hook envs, which pin minors the project venvs do not.** Observed 3.11.15 / 3.13.15 / 3.14.7 ALL referenced by `py_env-python3.11|3.13|3.14` dirs under `.cache/pre-commit/*/` while both live project venvs were 3.14 — so "keep 3.14 only" is wrong. Grep `pyvenv.cfg` under the pre-commit cache before calling any interpreter stale.
- **Version-matched caches are the free half of a "keep the newest" item.** `.cache/electron/<hash>/electron-v<ver>.zip` and `.cache/node-gyp/<node-ver>/` hold one entry per version ever built: diff them against the consumer's pin (`apps/desktop/package.json` electron pin; the managed node under `.hermes/tools/node-*`) and drop only the non-matching entries.
- **A formula-less Homebrew is dead weight.** `.linuxbrew/Homebrew` at ~195 MB with an empty `Cellar` and a 4 KB `bin/brew` shim = brew installed and used for nothing — ask before calling it cleanup.
- **That gc does not fit in a foreground call.** Run it with `background=true, notify=true`: a 1.8 GiB / 48-pack checkout exceeded a 420 s tool cap mid-repack (harmless — the repo stays consistent, and the partial pass had already merged 48 → 19 packs). Verified reclaim on one such checkout: **1.9 GB → 832 MB** (`in-pack` 637 119 → 479 836 objects, 48 → 7 packs, loose 435 → 3), with `HEAD`, the worktree's local edits and the promisor remote all intact and no stale locks.
- **`state.db` is history, not a cache.** ~200 MB is normal for a used install; compaction is a
  maintenance choice, deletion loses sessions.
- **Log rotations are safe; the one-off diagnostic is the surprise.** `gateway-exit-diag.log` grows to
  tens of MB from a single boot-loop investigation and is never rotated — always name it explicitly.
- Hermes' own tracker (`disk-cleanup/tracked.json` + `cleanup.log`) records temp files it will reclaim;
  read it before hand-pruning scratch so the report and the tracker agree.

## Delivering the answer
Lead with: total for the add-on's tree, free space on the partition, and the reclaimable total.
Then two buckets — regenerable-now (each item + size) and needs-a-decision (the levers, each with why
it is not free). Close by offering to execute the safe bucket item by item. Keep the table and the
commands here; his chat answer is a handful of lines.
