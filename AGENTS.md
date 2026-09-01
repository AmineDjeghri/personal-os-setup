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
- Git/GitHub: committing locally is fine once asked; **pushing, PRs, and release-branch actions need
  explicit confirmation**.

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
| Contributor guide | `CONTRIBUTING.md` |

## Known drift (trust nothing blindly)

- `make help` Development section broken (greps nonexistent `makefiles/dev.mk`)
- `make install` installs zero dev/docs deps → use `make install-dev`
- actionlint/zizmor/pip-audit hooks are commented out in `.pre-commit-config.yaml`
- `make docker-prod`/`docker-dev` don't exist
- Docs said `_PRIMARY_MANAGERS_BY_DISTRO` — the real constant is `_UI_VISIBLE_MANAGERS_BY_DISTRO`
- `properdocs.yml` uses `docs_dir: .` — new top-level dirs must join the exclude glob or they
  get crawled into the published site
