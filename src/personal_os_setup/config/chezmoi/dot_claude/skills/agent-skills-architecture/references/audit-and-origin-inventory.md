# Auditing the library and inventorying origins

### Audit — "too many skills, which can I delete?" (an inventory pass)

- **Telemetry covers only what Hermes loaded.** `hermes curator usage` carries no counters for Track 1 or
  repo-scoped skills, so their demand reads `unverified` — never downgrade that absence into "0 uses" or a delete
  signal, and never quote a count the CLI did not print.
- **Real usage outranks size**: demand + no repo backing = *port* candidate, not a delete candidate.
- **Mid-move state**: while a live copy and a repo copy co-exist, `hermes skills list` shows one row per name and
  the total drops by one per collision — a falling count is NOT a missing skill.
- **Sweep the platform's own mutations before reporting** (seeding on update, origin-hash freezing, curator
  archiving, the unreviewed `pending/` backlog): one read-only pass over `hermes skills list-modified`, the
  manifest count, `.no-bundled-skills`, `pending/` counts and the relevant `hermes config get` keys — semantics in
  `references/platform-lifecycle-and-gates.md`.

Classify from bookkeeping, never from the category directory a skill sits in: `hermes skills list` prints the Source
(`local` = own store, `builtin` = shipped in the addon tree) plus a Status column; `.usage.json` carries
`created_by` / `use_count` / `state` / `pinned`; the addon's read-only `skills/` tree is ground truth for "shipped";
`.curator_backups/` holds pre-run snapshots for rollback.

- Agent-authored + box-specific → the only promotable kind; port it into git (next section) if it must survive a
  reinstall.
- Shipped / hub-installed → NEVER vendor into a Track-1 tree; keep while used, otherwise delete the own-store copy
  (a deleted bundled skill is not re-seeded; `hermes skills reset <name> --restore` brings stock back).
- Live-only with 0 uses, superseded by a newer skill, or `state: stale` → delete.
- A skill dir that is a symlink into a repo → keep the symlink, never add a second copy.
- A DISABLED skill leaves the index AND is unreadable/unpatchable through the skill tools (`skill_view` refuses) —
  re-enable it before trying to edit it.
- Deleting files inside a skill dir leaves dangling `references/`/`scripts/` pointers in its SKILL.md: grep the live
  skills for the removed filenames afterwards (the deploy clears them when the source version does not reference them).
- Inventory pitfalls: `find -name SKILL.md` does not descend into symlinked skill dirs (use `ls -la`, `find -L`);
  `hermes skills list` truncates long names with `…`, so never diff name lists off that table; `.curator_ledger.jsonl`
  records curator/agent mutations only — a user-side deletion or disable leaves no entry, so an unexplained drop in the
  count means ask the user before suspecting the tooling.


## Origin inventory — "list my skills with their origin"

### Origin inventory — "list my skills with their origin"

Answer in TIERS with the arithmetic reconciled (every indexed name lands in exactly one tier); a flat list is the
wrong shape and a single total for the whole box is always wrong, because the tiers overlap in name only.

One read-only pass over the sources: repo `dot_claude/skills` (the only authored tree); the live shared dir
`/config/.claude/skills`; the own store `$HERMES_HOME/skills/**` (via `find -L`, so symlinked skills count); the
addon's shipped trees (`skills/` active, `optional-skills/` inactive); `.bundled_manifest`; `.usage.json`
(`created_by`, `pinned`); and every repo's `.claude/skills` + `.agents/skills`.

Tiers: **shared curated** (repo → deployed, both agents) · **repo-scoped** (that repo's sessions only) ·
**live-only agent-authored** (no repo backing — the deletable class) ·
**addon-shipped with a live copy**. Answer from the FILESYSTEM: `.usage.json` keeps rows for skills already deleted
from disk, so report those dead rows in one line and never let them inflate the count. A live name ABSENT from
`.bundled_manifest` is a copy that differs from the shipped one — state that as a fact, never as "broken". Columns
that worked: skill(s) | origin (repo → path) | tier/owner, grouped by tier, with the reconciliation stated once. Each
row's `metadata.hermes.origin` (above) must agree with the tier the bookkeeping puts it in — a disagreement means one
of the two moved without the other.
