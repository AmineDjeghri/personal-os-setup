# AGENTS.md

Canonical working rules for ALL AI agents in this repository (Claude Code, Hermes, Codex, ...).
CLAUDE.md imports this file and adds Claude-specific depth — don't duplicate rules here and there.

## What this is

- **`personal-os-setup`**: cross-platform Textual TUI app — OS/distro detection → package catalog →
  manager backends → system actions. Code in `src/personal_os_setup/`.
- **`docs/`**: documentation hub published via properdocs/mkdocs.
- `src/awesome_os/` is dead — ignore it.

## Safety: confirm before system-mutating actions (MANDATORY)

- Package installs/upgrades/removals, `chezmoi apply`, shell changes, driver/VM/WSL setup, `sudo` steps:
  **explicit, per-action user approval before running**. A prior "yes" is not standing approval.
- Destructive: `make vm-clean`, `make deploy-doc-gh` (pushes gh-pages). Never bypass the TUI's
  confirm dialogs (`SystemAction.confirm=False`).
- **Git: NEVER run `git commit` or `git push` without the user's explicit approval.** Both are
  approved per action, every single time. A task description, a plan, "do the work", a previous
  approval, or an earlier push on the same branch is NOT permission. Ask, wait for the yes, then
  run exactly the action that was approved. The same applies to `--force`, PR creation/merge and
  release-branch actions. **If an approval prompt times out, STOP** — silence is not consent; say
  "prompt me again" is the user's call, not yours.

## Commands

| Command | Purpose |
|---|---|
| `make test` | unit tests (`uv run pytest tests/unit`; exit 5 = success) |
| `make pre-commit` | ruff, detect-secrets, commitizen, yaml/json/toml, uv-lock — CI runs this exact command |
| `make install-dev` | full dev env (use this, not `uv pip install -e .`) |
| `make lint` / `make format` | ruff directly |
| `make test-integration` | **never locally** (CI-only; installs real packages) |

Run `make test` + `make pre-commit` before any PR — local pass == CI pass.

## Conventions

- **Branch:** from `main` (the `dev` branch is retired). `feature/<name>` / `bugfix/<name>`.
- **Commits:** Conventional Commits, gitmoji optional. `feat`→minor · `fix`/`perf`→patch ·
  `feat!`/`BREAKING CHANGE:`→major · others→no release. **Never bump `pyproject.toml`; never
  create tags** — semantic-release does it. commitizen validates only at `git commit`
  (commit-msg hook), not in `make pre-commit`.
- **PRs:** target `main`, squash-merge, title must be conventional (= the release commit message).
- **Secrets:** inline `# pragma: allowlist secret`, never whole-file excludes.
- **Renovate:** 7-day cooldown on dependency PRs; `uv.lock` regenerated, not pinned.

## Index

| Topic | Where |
|---|---|
| Deep architecture (frontend, tasks, managers) | `CLAUDE.md` |
| PR flow / ship process | `.claude/skills/ship-feature` |
| Documented-vs-reality drift | `.claude/skills/repo-gotchas` |
| Tests & coverage | `.claude/skills/run-tests` |
| Docs site gotchas | `.claude/skills/docs-site` |
| Repo skill layout / adding skills | `.claude/skills/skill-layout` |
| New TUI action / package-manager backend | `.claude/skills/add-system-action` |
| Chezmoi dotfiles source scripts | `.claude/skills/chezmoi-scripts` |
| VM test lab (CachyOS host) | `.claude/skills/vm-lab` |
| Forking this repo for your own setup | `.claude/skills/fork-and-customize` |

## Skills & plugins — one rule: authored → the repo tree, third-party → npx

- **Authored skills** live in ONE tree, repo `dot_claude/skills/` → `~/.claude/skills` (`make skills-deploy`).
  Hermes reads `~/.claude/skills` too (`skills.external_dirs`), so nothing is duplicated into
  `~/.hermes/skills` — a name in both roots is unloadable (`Ambiguous skill name … Refusing to guess`);
  `make skills-status` flags it. The saved set is listed in `skills.keep`; save a live skill into the
  repo with `make skills-keep NAME=<name>`.
- **Private content stays out:** an `exposure: private` skill is live only (`hermes curator pin`) —
  **this repo is PUBLIC**.
- **Third-party, skills-only:** `npx skills add <owner>/<repo> -s <skill> -a <agent> -g -y --copy`;
  `--copy` makes the agent dir hold a **real directory** regardless of the CLI's symlink default; the
  lock (`~/.agents/.skill-lock.json`) is copied into the repo (`make skills-thirdparty-save`;
  `make skills-thirdparty-replay [AGENT=codex]` reinstalls).
- **Never vendored:** agent-shipped (bundled / official optional) skills, plugin packs (that harness's
  own channel, one install per harness), and the Claude account sync (`~/.claude/skills/synced/`).
  Agent-created (Curator) skills are live only until triaged: promote, pin-private, or delete.

- **Corollaries:** no third-party pack vendored as a copy; no upstream-shipped skill forked into
  the repo; no agent-created name left untriaged. **One canal per pack per agent** — never plugin
  *and* npx for the same agent (the model then sees one name twice).
- **Transport for our own content is git + `make` only** — our skills never go through npx, a
  plugin, or a lock file; a tool that owns a directory must not own ours.
- **npx targeting — one name must be reachable by each agent exactly once.** `-a claude-code` alone
  already reaches Hermes (it reads `~/.claude/skills`), so never add `-a hermes-agent`: two roots
  Hermes reads → `Ambiguous skill name … Refusing to guess`. `-a claude-code -a codex` is safe
  (disjoint readers); **never `-a '*'`**, which expands to that bad pair. Keep third-party names
  disjoint from shipped/deployed ones, and check before installing.
- **Three former entries are no longer in this repo:** `skill-creator` was vendored from
  `anthropics/skills` and is now served only by the Claude account sync — a second copy of that name
  collides with it and makes the name **unloadable in Hermes**. `hermes-s6-container-supervision` was
  a stale fork of the agent's official optional skill and is now installed from there instead
  (`hermes skills repair-official <name> --restore --yes`), not from this repo.
  `nicegui-frontend-testing` was removed as unused.
- **Bundled (addon-shipped) skills are read-only:** an edited copy is skipped by the sync forever;
  put local additions in a skill we own instead and run `hermes skills reset <name>` to unfreeze —
  see `.claude/skills/skill-deployment`.

## Known drift (trust nothing blindly)

- `make help` Development section broken (greps nonexistent `makefiles/dev.mk`)
- `make install` installs zero dev/docs deps → use `make install-dev`
- actionlint/zizmor/pip-audit hooks are commented out in `.pre-commit-config.yaml`
- `make docker-prod`/`docker-dev` don't exist
- Docs said `_PRIMARY_MANAGERS_BY_DISTRO` — the real constant is `_UI_VISIBLE_MANAGERS_BY_DISTRO`
- `properdocs.yml` uses `docs_dir: .` — new top-level dirs must join the exclude glob or they
  get crawled into the published site
