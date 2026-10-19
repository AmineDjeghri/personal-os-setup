---
name: skill-store-reconciliation
description: Use when auditing or reconciling the skill stores.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Skill store reconciliation

## When to Use

The recurring job: enumerate the skill stores, say what lives where, find what is orphaned, duplicated or drifted.
Triggers: "rescan the skills", "list skills per store", "what can we delete", "why won't this skill load", any
install / merge / removal of a skill. Where a skill belongs: `agent-skills-architecture` and `AGENTS.md`; this
skill is the operation.

## Sweep every root before you count

**A name is live if ANY root holds it.** A missing root silently inflates the "orphan" or "dead"
list — this is the single most common way this task goes wrong. Walk each root for `SKILL.md`:

| Root | Holds |
|---|---|
| the Hermes own store | live-only names: agent-created skills, and copies of what the agent ships (no repo-deployed tree lives here) |
| the shared store both agents read | the shared authored track, plus a nested account-synced subtree |
| the add-on's active skills tree | skills shipped by the agent |
| the add-on's optional/shipped tree | official skills that are *not* installed (not live — don't count them) |
| plugin caches / marketplaces | plugin-pack skills |
| the repo's chezmoi skill tree | the source of truth for authored skills — ONE tree, deployed to the one root both agents read |
| **every other repo's own `.claude/skills`** | repo-scoped skills — one parked in another repo is **not** an orphan |

Confirm other repos are cloned before calling their skills missing.

## Procedure

1. **Sweep** the roots above; build `name -> [roots]`.
2. **Classify** per the table in `references/store-sweep-and-prune.md` §2 (the repo's ONE authored tree is
   enumerated by `skills.keep`). Saving a live-only skill is a repo operation, not a hand copy.
3. **Identify which checkout the live root matches, then compare with the repo's own gates** — never by
   eyeballing. A repo can be checked out more than once on different branches (`git worktree list`), and
   the deployed tree may match a non-`main` worktree, so run `make skills-diff` / `make skills-drift` /
   `make skills-status` from the checkout that matches; from the other one they report spurious DIFFERS.
   The exit code is the truth, not the summary text. Collision test = load by bare name
   (`agent-skill-governance` §1).
   **When the live root matches neither checkout** (a reorganization in flight) compare per-skill
   directory hashes against both trees — reference §8; `MISSING` for names that migrated is not a defect.
4. **Report** (shape below), then **verify before deleting** anything.
5. After a removal or merge, **re-run the gates and grep the library for pointers** to the gone name.

## Pitfalls

- **`usage.json` rows are not an inventory** (rows survive deleted skills). Recompute against disk; prune per
  `references/store-sweep-and-prune.md` §5.
- **Dot-dirs inside a store are scanned.** `hermes skills repair-official <name> --restore` writes its backup
  inside the store — move it out at once (reference §7).
- **Retire = delete source AND live copy by hand**; drift gates stay quiet about a deleted source (reference §6).
- **Never delete a live copy of an agent-shipped skill unless the name is already re-sourced from a tracked
  channel** (published pack, in the lock). A bare delete drops it from the index with no reseed. A use count
  alone is no reason to keep a copy that has a tracked source.
- **The live tree can match a branch, not `main`.** Run `git worktree list`, `git branch --show-current` and
  `git rev-list --left-right --count origin/<base>...HEAD` for every worktree, then `diff -rq <live-root>
  <checkout>/<source-tree>`, before scoping any audit, slim or deploy. A tree parked on an unrelated branch gives
  a confident, wrong "current" answer; use `origin/<base>` for content comparisons, never a checkout's HEAD.
- **A live copy uniformly *bigger* than the branch is usually a pre-trim snapshot, not drift.** If the branch's own
  commits say they dropped duplication/history and nearly every skill shows a positive net delta, redeploy —
  don't "fold the live delta back", which re-merges content the branch deliberately deleted.
- **Verify collisions with the loader, not your own root list.** The nested account-synced subtree resolves as
  namespaced entries and the agent package's own checkout is not a root the loader reads, so a hand-built list
  flagged 16 "collisions" where the repo gate printed `(none)`. Take the count and uniqueness check from your own
  walk on full directory names — `hermes skills list` truncates long names and has no JSON mode, so it is good for
  row counts only. An over-count invents work and mis-tags clean copies.
- **Never call a copy stale from its mtime, and never say "newer" unqualified.** A deploy from another worktree
  rewrites timestamps without rewriting content. Hash the directory, diff it, name the differing line, and report
  the two axes separately ("later mtime, older content").
- **Read the clock before reasoning about "since last time".** A resumed session's start date can lag the
  filesystem clock by weeks; run `date` and `stat` a few live files first.
- Before writing a deploy script, check whether chezmoi already deploys the tree (`agent-skill-governance` §6).

## Reporting shape

The user asks for this as a table, not prose: markdown tables **per store or per category**, with a
column for what changed/drifted, and a one-line summary above them. Keep narrative out of the reply — one
line per finding, method and full evidence in this skill or a file, not in chat; say so in one clause when
something is unverifiable.

Split live-only names into **intentional** (in the third-party lock, or private by design) and
**orphaned** (the authored tree no longer ships them). The first bucket needs no action; the second needs
its live copy deleted by hand. One flat "live-only" list hides that difference and makes a clean store
look dirty.

## Related

- `references/store-sweep-and-prune.md` — copy-paste recipes: the sweep, the classification table, the
  gates, the collision test, prune-with-controls, retire, and de-fork.
- `agent-skill-governance` — the reach/collision rules, the channels, and the provisioning decision.
- `skill-deployment` — deploy targets, chezmoi mechanics, the third-party lock and its drift target.
