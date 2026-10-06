# The Hermes own store — writers, the Curator and pins

`~/.hermes/skills/<category>/<skill>/SKILL.md` (= `/config/.hermes/skills/…`; per-profile under
`~/.hermes/profiles/<name>/`) is fed by three owners mixed into ONE flat `category/skill` namespace, with nothing on
the file saying who owns it. Establish provenance before touching anything:

- **Addon bundled sync** — names listed in `.bundled_manifest`; re-synced and updated by the add-on. Never build work
  on top of one of these (an edited copy is skipped by the sync forever — see the section below).
- **Hub / dashboard installs** — land in the SAME store (there is no separate install dir; `skills:` in `config.yaml`
  defines no install path), with the hub's bookkeeping in `.hub/` (taps, lock, audit, quarantine, catalog cache).
  Often identifiable from the frontmatter (`author: community`). Tool-managed → never vendor them into git.
- **Agent-authored** (`author: Hermes Agent`) — nothing manages them: no git, no history, no backup, no update path.
  These are the only ones worth versioning.

**Check order for "is this mine?"**: the addon's active tree `<install>/skills/<cat>/<name>/` → its optional tree
`optional-skills/` (shipped, NOT active — checking only the active tree yields a false "it's ours") →
`.bundled_manifest` → `created_by` in `.usage.json` (`agent` = ours, `null`/absent = shipped or hub-installed).
Counters come from `hermes curator usage`; where no CLI exists (the webui container ships none), read
`.usage.json` directly for `created_by`/`pinned`/`state` and say which path was used — never hand-reconstruct a
counter the CLI would print. A name in the optional tree exists on the box but is not in the index: state both
facts rather than guessing ownership.

**One authored tree, no Hermes-only placement.** `dot_claude/skills` → `/config/.claude/skills` is read by BOTH
agents, so every authored skill is visible to both; a Hermes-only intent is stated in the skill's `description`
(e.g. "Hermes-only: …"), not by placement. Never copy an authored name into `~/.hermes/skills` — two roots, one name
is unloadable; `make skills-status` flags it. Keep the curated set disjoint from bundled/hub names — one namespace,
so a collision silently overwrites — and keep the promoted names distinct enough to be recognisable as curated.

**The Curator edits this store in place** (`curator:` in `config.yaml` — interval, `stale_after_days`,
`archive_after_days`, `prune_builtins`, backups in `.curator_backups/`). Anything you deploy into the store from git
is therefore in a two-writer situation: the Curator — and the autonomous background-review pass — rewrites or
archives it, and the next `make skills-deploy` overwrites it. **The deploy is one-way and copy-only**: it replaces
files and DELETES NOTHING, so an in-place edit to a live skill is silently reverted by the next deploy (copy it back
into the source tree first) and a skill dropped in the repo keeps living in the store (rm the deployed dir by hand —
the audit is not finished while an orphan is still indexed).
Re-homing a skill between the two trees needs BOTH sides: deploy the new location AND delete the old live directory,
or one name ends up indexed from two sources with no way to tell which copy the agent reads.
The protection mechanism is the curator CLI, per machine, after the deploy:

```bash
hermes curator status                  # what it manages + activity per skill
hermes curator pin <skill>             # hands off: never rewritten, pruned or archived (unpin to release)
hermes curator usage                   # activity telemetry for ALL skills, with provenance
hermes curator {run,pause,resume,list-unmanaged,adopt,restore,ledger,backup,rollback}
```
- Bundled and hub-installed skills are **never touched** by the Curator — it only reviews agent-created ones, which is
exactly the promoted set, so pin every promoted name.
- A pin blocks CONTENT edits, not just lifecycle transitions: the Curator skips pinned names, and the autonomous
  background-review pass treats them as protected ("only the user, in a foreground session, can change a pinned
  skill"). Unpinned, a promoted skill gets rewritten in place and the next deploy silently wins the round.
- Promoted names need no defence against `hermes update`: the bundled sync only touches names in `.bundled_manifest`,
  and when a bundled name collides with an existing local skill it keeps YOUR copy and warns — swapping in the
  bundled version takes a deliberate `hermes skills reset <name>`.
- `hermes skills opt-out` is a DIFFERENT switch: it writes the `.no-bundled-skills` marker so the installer and
`hermes update` stop seeding bundled skills (optionally `--remove` unmodified ones). It is not a Curator pin.
- Say plainly which writer owns which file: git owns the promoted names, the hub owns its installs, the addon image
owns bundled ones.

## Background-review write guard

- **The refusal list IS the drift set, and it is scoped to one ACTOR.** `_background_review_write_guard`
  (`tools/skill_manager_guards.py`) returns immediately unless the write origin is `background_review`
  (`tools/skill_provenance.py` — a ContextVar), so the autonomous pass is refused on: pinned names, bundled and
  protected built-ins, hub installs, anything under `skills.external_dirs` (EVERY shared external-dir skill), and any
  name with no curator record (`created_by` absent or `None` — "not curator-managed … run `hermes curator adopt
  <name>`"). What it CAN write is therefore exactly the own-store `created_by: agent` unpinned names — the same set
  that drifts against the chezmoi source. Foreground actors (CLI, gateway, cron, subagent) are subject to none of
  it: a pinned skill can be edited there, and `_pinned_guard` blocks only its DELETION. Never describe "the
  curator" as one actor with one rulebook.
- **Test such a guard without touching a skill.** In a scratch script set
  `tools.skill_provenance.set_current_write_origin("background_review")`, call
  `skill_manager_guards._background_review_preflight(action, name)` for each name of interest, reset the token, then
  repeat in the default origin to prove the scope. It reads usage records and resolves paths and writes nothing —
  never test a write guard by attempting a real write to a live skill.
