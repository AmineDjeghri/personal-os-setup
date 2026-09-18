---
name: skill-deployment
description: Use when deploying the shared agent skills via chezmoi, or fixing "not managed" errors.
---

# Skill Deployment via chezmoi

Shared skills: repo `src/personal_os_setup/config/chezmoi/dot_claude/skills/` → `~/.claude/skills`
(Claude Code + Hermes external_dirs). Desktops: TUI dotfiles tab. Container/CLI:

> Scope: this deploys only the **general/shared** skills. Repo-specific skills are NOT part of it —
> they live in the repo itself under `.claude/skills/` (Claude Code reads those natively) with
> git-symlink mirrors in `.agents/skills/` for other agents, kept in sync by `skills.mk`
> (`make skills-link` / `make skills-check`; see the `skill-layout` skill).

**Two loading paths — don't confuse them:**

- **Shared (Track 1)** → `skills.external_dirs` in the Hermes config: always in the index, every
  session, any cwd. That one entry (`~/.claude/skills`) is what both agents load.
- **Repo-scoped** → `<repo>/.hermes/skills` + `.agents/skills` load *only* when the session's
  working dir resolves to the repo's git root **and** that root is in `skills.trusted_project_dirs`.
  A session rooted at HOME (global `terminal.cwd`) resolves no repo, so nothing loads — upstream
  Hermes bug #103423, fix in review as PR #103424. Never park repo skills in `external_dirs`
  (N repos × M skills doesn't scale): promote a repo's skills to Track 1 if they must be
  always-on, otherwise they're read on demand.

```bash
REPO=/config/workspace/personal-os-setup
cd ~ && chezmoi apply -v --force --source "$REPO" .claude    # deploy ONLY the skills
```

**No chezmoi (HA container/CLI):** `cd <repo> && make skills-deploy` — copies the same source
to `~/.claude/skills`. The make target lives in `makefiles/skills.mk` (same file as
`skills-link`/`skills-check`).

Two gotchas (both previously caused "not managed"):
1. `--source` = repo **ROOT** (git-backed, `.chezmoiroot` points at the nested dir) — never the nested dir
2. Run from **HOME** — targets resolve against CWD

⚠️ The nested `config/chezmoi` dir must **never** contain its own `.chezmoiroot`: the app
(`src/personal_os_setup/tasks/system/chezmoi.py`) passes that dir directly as `--source`, so a
nested `.chezmoiroot` would double-redirect and break the app's deploy path.

Refresh after `git pull`. On the container deploy only `.claude` (full apply would dump desktop dotfiles).

**Hermes-only (not Track 1):** `dot_hermes/skills/<category>/<skill>/` → `~/.hermes/skills/`,
deployed by the same `make skills-deploy` (mode 644 dirs preserved). Renaming a skill does NOT
hide it from Claude Code — only living under `dot_hermes/` does; the shared Track-1 list no
longer includes the coding workflow (now `hermes-coding-workflow`, Hermes-only). The deployed
names are protected from the Curator: bundled/hub-installed skills are never touched by it, only
agent-created ones — exactly this promoted set. Pin them per machine after each deploy:
`hermes curator pin <skill>` (`unpin`/`status`/`run`/`pause`/`list-unmanaged` also exist).

**Sync direction — repo → live, one way.** The repo copy is the truth; `make skills-deploy` is
copy-only: it overwrites whatever is live and deletes nothing.

- A skill edited in place (foreground agent, `hermes skills` editor) is reverted by the next
  deploy — copy it back into the source tree first, then deploy.
- The Curator and the background-review pass patch agent-created skills in place, so unpinned
  promoted skills drift and the deploy silently wins. Pin every deployed name.
- `hermes update` needs no action here: these names are not bundled (absent from
  `.bundled_manifest`), and the bundled sync never overwrites a same-named local skill — it warns
  and keeps yours.
- Deleting a skill in the repo does not delete it live: `rm` the deployed dir by hand.
- Never deploy a skill that already lives elsewhere in the repo and is symlinked into the store
  (e.g. a `docs/...`-hosted one): `cp -R` follows the symlink and writes through it into the
  tracked source. Keep the symlink, don't duplicate the directory.

**Checking drift (read-only, no deploy):** `make skills-diff` compares repo vs live for both
trees and exits non-zero on any MISSING/DIFFERS. `make skills-status` lists every git-managed
skill plus any live `~/.hermes/skills` copy that duplicates a now-git-managed name (leftover from
before promotion — safe to remove, the next deploy overwrites it anyway).

**`skills-deploy` refuses on drift.** Before copying, it runs `make skills-drift` — same scan as
`skills-diff` but MISSING (never deployed yet) is fine; only a DIFFERS aborts the deploy, so an
in-place edit isn't silently reverted. Run `make skills-diff` for a full report or `make
skills-drift` to just check the gate. Fix a DIFFERS by porting the live edit into the repo (PR)
first, then deploy; or force the overwrite with `make skills-deploy SKILLS_FORCE=1`.

GNU Make gotcha: `export VAR = x   # comment` keeps the comment's leading whitespace inside the
value, so keep such comments on their own line.

## Bundled (addon-shipped) skills are read-only

Bundled skills sync from the addon with a per-directory hash manifest, so a copy we edited is skipped
forever and upstream improvements never reach us. Never edit one. When we want a local addition:

1. `hermes skills diff <name>` — see exactly what our copy adds.
2. Move that content into a skill we own (a `*-ops` addendum, e.g. `claude-code-ops` for the container
   facts about the `claude-code` skill).
3. `hermes skills reset <name>` — clears the "user-modified" flag so updates work again; it does not
   touch the content. `hermes skills reset <name> --restore` also reverts to stock.
4. Confirm with `hermes skills list-modified`; the next addon update brings the stock version.

Local additions we dropped when un-freezing (kept here for reference; upstream may adopt them):
`pdf` (scanned-PDF hand-off to `ocr-and-documents`, `--meta` inspect step, `related_skills` frontmatter),
`grounded-citations` (hand-off to `research-paper-writing`), `hermes-agent` (`/background`, `/busy` rows,
the OPT-IN plugin note), `hermes-agent-skill-authoring` (`related_skills` line). `claude-code`'s additions
live in `claude-code-ops`. `docx` / `xlsx` were already identical to stock.
