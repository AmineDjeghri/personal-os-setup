# Agent skill governance — judgement calls

The rules live in `AGENTS.md` § "Skills & plugins"; deploy/npx mechanics in `skill-deployment`; layout and
wiring in `SKILL.md`. This file holds the judgement calls that go wrong: collisions, re-sourcing, promotion,
delegated audits, provisioning scripts.

## When to Use

- A skill is added, installed, removed, deployed or audited on a machine with more than one coding agent.
- A skill name stops loading, or a listing/deploy report disagrees with what the loader does.
- You are about to install a third-party pack, or to provision skills onto another machine.

## 1. One rule: a name must be reachable by each agent exactly once

Hermes reads its own store (`~/.hermes/skills/`) **and** `~/.claude/skills` (external dir); Claude Code reads
`~/.claude/skills`; Codex reads only its own dir. Two copies of a name in two roots *one agent* reads make the
name **unloadable**:

```
Ambiguous skill name '<name>': 2 skills match across your local skills dir and external_dirs. Refusing to guess.
```

The trap: `hermes skills list` still shows one row and the deploy **succeeds** — it fails only at load time.
**Verify with the loader, not the lister:** after any placement change, load the bare name by hand.
Which combinations break (`-a claude-code -a hermes-agent`, `-a '*'`, symlinks, backups under a scanned root):
`multi-agent-reach.md`.

- **Migrate a name between roots add-then-remove, in one `mv`:** keeper in place first, then `mv` the old copy to
  a backup dir *outside every scanned root* (not copy-then-`rm`: a stalled approval can't leave it half-applied).
  Re-load the bare name afterwards — only the loader says which window you are in.
- Walk each root recursively when comparing names; the account-sync subtree is `synced/<uuid>/<name>/`.

## 2. Re-sourcing, and not rewriting what isn't ours

- **Re-sourcing a shipped skill** is allowed: delete the agent's copy (the sync records the deletion), install it
  from the shared root like a third-party pack. Cost: no longer version-matched to the build, and the delete is a
  provisioning step on every NEW machine (boot sync re-seeds). Benefit: a name in an external dir is refused by
  the background-review writer, so it is protected. Procedure: `store-reconciliation.md` Pitfalls.
- **Probe before rewriting a live file in place.** `hermes skills list-modified` / `hermes skills diff <name>`
  settle whether it is a tracked bundled copy (editing freezes its sync forever → put the addition in a `*-ops`
  addendum) or the only copy of a skill we author. The listing's `Source` column does not settle it (`official`
  can still have no stock version). A repo that once shipped its own copy may have deleted it, leaving the live
  store as the only home — establish which case you are in before the edit.
- Run `npx skills add … -l` against your authored repo before proposing npx as its transport: discovery is
  location-limited and may list none of the authored tree. Install flags and the third-party flow: `skill-deployment`.

## 3. The lock is a name list, not a pin

`skillFolderHash` is the upstream git tree SHA, not a hash of your files; to pin, record `owner/repo#<commit>`.
**A CHANGED line means upstream moved, not a local fault** — the hash is stable for a given folder, so it is the
de-facto update notification now that `update` can't be trusted. Re-record the lock; don't hunt for a local cause.
Lock location, replay and CLI surface: `npx-skills-cli.md`, `skill-deployment`.

## 4. Auditing and promoting

Audit a library via `store-reconciliation.md`. Report a **keep** list with reasons ("nothing to delete, and
here is why" is a result). Protected skills — pinned, external-dir, shipped, user-authored — are not yours to
rewrite: recommend adoption.

**Promoting a live-only skill** (no git backing → a wiped home takes it): decide per skill, never in a batch;
report three buckets — promote, keep private, retire — with a reason each.

1. Read the frontmatter before the body: `origin: agent` = created by this agent, ours to promote; no marker =
   predates the convention, needs a content judgement. Quote size and reference count first (a 23 KB skill with
   20+ files is a project, not a note).
2. Scan for personal detail (the repo is public): recipe in `sanitizing-skills-for-public-repos.md`.
   Any hit keeps it live-only — no invented `service.<domain>` stand-ins; that is the same defect in a mask.
3. **Merge before promoting.** Grep the tree for the skill's name and one distinctive heading from its body: zero
   references *plus* overlapping content → fold the unique parts in and retire the copy; no rule gets two homes.
4. Promote as a repo operation on the branch already moving that tree: flat `<authored-tree>/<name>/`,
   `origin: repo:<repo-name>`, then deploy and pin. Never hand-copy into the live root.
5. Retire the live copy only after the deploy lands, and name it: the deploy never deletes, so a dropped name
   keeps loading until removed by hand.

## 5. Changing shared state: independent verification

- An author is blind to their own side effects: have a **fresh** read-only delegate try to falsify the measured
  facts, handing it the single most doubtful claim to settle *by experiment*. Route fixes back to the author's
  session (resume it). Then re-run the check that would have caught the defect (load the name; re-run the
  differ), not just the command that reported success.
- Delegate the **coding pass** too (brief it; keep recon reads and final verification for yourself). The second
  pass must **compare the new artefact with sibling ones** (shebang, guards, helpers, naming, mode, placement) — a
  delegate that reads only its own file can't see a convention.
- Mark any **derived** value in a brief (path depth, index, count) as derived and tell the delegate to recompute
  it; a wrong derivation otherwise surfaces as a lookup that works from one entry point and fails in the other.
- Library-wide audit or slimming pass: brief per `delegated-library-audit.md`.

## 6. Provisioning: ask what already deploys the tree before writing a script

`chezmoi --source <src> managed` printing `<root>/skills/<name>/SKILL.md` means `chezmoi apply` already writes it;
a copy script is then a second implementation (check `.chezmoiignore` too). The real gap is third-party/npx
installs, which chezmoi can't run. When one script must serve both chezmoi and a Makefile target:

- **Template-free** (a `.tmpl` needs rendering, breaking a direct `bash`/`make` call).
- **Locate data by walking up, not counting `../`; never via `$0`.** chezmoi runs `run_` scripts from a **temp
  copy** with cwd = the destination subdir, so `$0` points at the temp dir. Read **`CHEZMOI_SOURCE_DIR`** first,
  fall back to `$0`'s dir (the repo path under `make`), then walk up.
- A `run_` script's path **is** its declared target (`dot_config/x/run_after_y.sh` → `~/.config/x/y.sh`): file it
  in the tree it acts on (`dot_claude/` for skills), confirm with `chezmoi --source <src> managed --include=scripts`.
- `run_` vs `run_onchange_`, and a script firing only when its own path is part of the apply: `chezmoi-scripts`.
  Use plain `run_` + a runtime hash stamp for data-driven re-fire.
- **Test the re-fire path:** scratch source + scratch HOME + a stub binary that appends its args to a counter
  file; apply three times (fresh, unchanged, data edited). Only the third catches a tracker that can never re-fire.

## References

- `npx-skills-cli.md` — CLI surface, lock schema, verified commands
- `multi-agent-reach.md` — which agent reads which root; safe/unsafe targeting
- `delegated-library-audit.md` — briefing, running, applying and verifying a library-wide pass
