# Agent Skills Architecture (shared Hermes ↔ Claude Code)

Multi-agent skill-sharing design for this setup — one git-managed source, both agents read it.

## The zones (verified layout 2026-09)
1. **Hermes-only**: `/config/.hermes/skills/` (bundled + user skills; incl. the `claude-code` orchestration skill).
2. **Shared SOURCE OF TRUTH**: `personal-os-setup` repo → `src/personal_os_setup/config/chezmoi/dot_claude/skills/` (`coding-workflow`, `repo-conventions`, `skill-deployment`). chezmoi `dot_` prefix → `~/.claude/skills/`.
3. **Deployed shared**: `~/.claude/skills/` (= `/config/.claude/skills` here) — Claude Code reads it natively; Hermes reads it via `skills.external_dirs`, **wired 2026-09 to `["/config/.claude/skills"]` ONLY** — deliberate: repo paths in external_dirs don't scale to new clones; repo context reaches Hermes via AGENTS.md (native) + project-local skills, never external_dirs.
4. **Repo-specific**: each repo's `.claude/skills/` — canonical files, Claude Code auto-loads in-project (personal-os-setup: 9 incl. `skill-layout`). NEW 2026-09: `.agents/skills/` at the git root holds **git symlinks → `../../.claude/skills/<name>`** — cross-tool view (Hermes project-local, Codex, OpenCode). `make skills-link` (create/refresh) + `make skills-check` (verify) in makefiles/skills.mk. **Symlink target must be `../../`** — from `.agents/skills/`, one `../` only reaches `.agents/` (real bug hit 2026-09; `git ls-files -s` shows symlinks as mode 120000).
5. **Community**: vendored INTO the shared dir (git-tracked), never installed per-machine.

## Division of labor
Hermes: HA, gateway/admin, cron, memory, audits, container ops. Claude Code: in-repo code, features, PRs (Hermes delegates via `/config/.local/bin/claude`). Shared-dir skills MUST be agent-agnostic (terminal/git/gh only — no `ha_*` or hermes-CLI references).

## Hermes project-local skills (trust gate — verified in skill_utils.py 2026-09)
- Roots at a repo's git root: `<root>/.hermes/skills/` OR `<root>/.agents/skills/`; active only for sessions whose cwd/TERMINAL_CWD is inside that repo (walk-up to first `.git`; home dir itself is never a project).
- **TRUST GATE**: skills are load-on-demand PROCEDURES → auto-sourcing from any cloned repo is a prompt-injection vector. Project skills only load when the repo is in `skills.trusted_project_dirs` (config) — `hermes skills trust <repo>` / `untrust`. AGENTS.md (plain text) is read WITHOUT trust.
- **PRECEDENCE**: inside a trusted repo, the repo's version of a skill overrides same-named global/shared skills (vendored wins in its repo).
- Claude Code's equivalent is BROADER: a whole-project trust dialog on first run in a folder (gates CLAUDE.md, `.claude/skills`, MCP, command execution) + trusted dirs in settings. Headless `claude -p` in an untrusted workspace may stall on the prompt → pre-trust repos in Claude Code settings before delegation.

## Community skills — `npx skills` (Vercel Labs, verified 2026-09)
- Registry = GitHub: any repo with a `SKILL.md` at root is installable; works with 70+ agents.
- Commands: `find [q]` · `add <owner/repo> [--skill <n>] [-a claude-code] [-g] [-y] [--list] [--all] [--copy]` · `list` · `remove <n>` · `check` · `update` · `init <n>`.
- **Update loop**: `npx skills check` (lock-file hashes vs source) → `npx skills update` (reinstalls ONLY changed skills). Pull-to-update; never auto-changes.
- **Lock file** `skills-lock.json` tracks sourceUrl + skillFolderHash (npm-lock analog).
- **Symlink bug**: `-a claude-code` installs to `~/.agents/skills/` and symlinks into `~/.claude/skills/`; symlink creation has regressed (vercel-labs/skills #851, #1355) — verify files landed, or use `--copy`.
- **Supply chain**: pin versions — `npx skills add owner/repo@<commit>`; `gh skill install owner/repo name --pin <sha>` also exists.
- Known packs: `grill-me` from `mattpocock/skills` (interview the user relentlessly about a plan — fits the plan-first rule).
- Vendoring loop: install → copy dir into the shared chezmoi source → commit `feat(skills): update <name>` → PR → all devices via chezmoi; Hermes via external_dirs.

## AGENTS.md / CLAUDE.md best practices (researched + applied 2026-09)
- Claude Code does NOT read AGENTS.md natively → `CLAUDE.md` starts with `@AGENTS.md` (import) + Claude-specific depth below (Red Hat pattern).
- AGENTS.md is sent with EVERY prompt: keep <150 lines, act as an INDEX (orientation table), record silent invariants/gotchas only. Bloated auto-generated context files HURT performance (ETH Zürich study).
- NEVER duplicate rules across AGENTS.md and CLAUDE.md — divergence is the #1 failure mode.
- Skills: SKILL.md <500 lines + progressive disclosure (`references/` `scripts/` `assets/` loaded on demand). User prefers SHARED skills SMALL (~15–20 lines core).
- **Sanitize PII in public repo content**: no real name, username, numeric GitHub ID, or email (user scrubbed these from the shared skills 2026-09; a numeric GitHub ID survived one pass — grep explicitly for the owner's name, handle and numeric ID).

## Deployment on the Hermes addon container
- Native Claude Code install → `/config/.local/bin/claude` (absolute path; gateway PATH may not include it).
- **Login**: the first-run theme picker may not advance via PTY `submit` — use `claude auth login` instead (prints device-flow URL + code as plain text; user opens URL on phone, pastes code back).
- **Skills deploy via chezmoi, NOT copy**: repo root has `.chezmoiroot` → `cd ~ && chezmoi apply -v --force --source <repo-root> .claude`. Git-backed source (`--source` = repo ROOT, not the nested non-git dir) AND HOME cwd are both required — see main SKILL.md for the failure modes ("not managed" on non-git sources; CWD-relative target resolution).
