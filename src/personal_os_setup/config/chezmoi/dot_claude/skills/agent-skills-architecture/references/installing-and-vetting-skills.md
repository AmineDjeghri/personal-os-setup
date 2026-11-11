# Installing and vetting community skills and plugins

Three unrelated channels. Pick by WHO should see the result: `npx skills` installs one copy under
`~/.agents/skills` and links it into `~/.claude/skills` (both agents, via the shared dir); the Hermes hub installs straight into the own store
(Hermes-only, tool-managed); a Claude plugin is Claude-only. Never treat them as the same pipeline, and use one
channel per pack per agent.

## Path 1 — `npx skills` (shared dir, both agents)

Commands, targeting rules (`-a claude-code` only) and the committed lock: `skill-deployment` → "Third-party skills".

- The installer may write into repo-relative paths when run from a project dir — run from a neutral cwd for global installs.

## Path 2 — Claude Code plugin (Claude-only)

Claude reads `.claude.json`, credentials and plugins from `$HOME` — always run it with the persistent home as
HOME and by absolute path (the gateway PATH omits `~/.local/bin`):

```bash
export P=/addon_configs/<repo>_<slug>          # the addon's persistent home (== /config)
HOME=$P $P/.local/bin/claude plugin marketplace add <owner>/<repo>
HOME=$P $P/.local/bin/claude plugin marketplace list   # registered name may differ from the repo name
HOME=$P $P/.local/bin/claude plugin install <name>@<marketplace> -y
HOME=$P $P/.local/bin/claude plugin list
```

- Installs land in `~/.claude/plugins/` and do NOT touch `~/.claude/skills` — the Hermes `external_dirs` index
  stays clean.
- **Never point Hermes at a Claude plugin's cached subtree**
  (`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/skills`) — the version segment changes on every
  plugin update and old versions are swept.
- Invoke claude WITHOUT `--bare` when plugins must load — bare mode skips plugins and skills.
- Never commit plugin-install state (marketplace registrations, `~/.claude/plugins/`, `known_marketplaces.json`) —
  machine-local, re-registered per machine.

### A vendor bundle that ships BOTH skills and MCP servers

Some vendors publish one bundle for several agents (e.g. `cloudflare/skills` is simultaneously a Claude plugin
marketplace and a plain `skills/<name>/SKILL.md` tree). Give each agent its NATIVE mechanism — two sources of
the same skill name confuse the model:

- **Claude Code** → the plugin (`plugin marketplace add` + `plugin install`). The vendor's plugin manifest can
  carry its MCP server too (`.claude-plugin/plugin.json` → `mcpServers`), so nothing else is needed that side.
- **Hermes** → the skills CLI (`vercel-labs/skills`, npm package `skills`):
  `npx -y skills add <owner>/<repo> -s <skill> -a claude-code -g -y`. `-a claude-code` already reaches Hermes
  (it reads `~/.claude/skills`); never add `-a hermes-agent` (two roots Hermes reads → ambiguous names);
  `-a claude-code -a codex` is safe, never `-a '*'`. If the plugin already serves Claude, expect the skills twice —
  one canal per pack per agent. Destination is chosen by agent + scope alone — no `--dir` flag.
- **Hermes MCP servers** → `hermes mcp add <name> --url <url> --auth oauth`, the `trust: untrusted` write gate,
  and scoped tokens over account-wide OAuth.

## Path 3 — Hermes hub discovery (own-store install, Hermes-only)

### Where the community lives

- Hub state sits in `$HERMES_HOME/skills/.hub/` (`taps.json`, `index-cache/`, `lock.json`, `quarantine/`,
  `audit.log`). `{"taps": []}` means no custom tap is registered — the built-in sources still work, so an empty
  tap list is not "no community available".
- Installs land in the own store: Hermes-only, hub-owned, and a name that collides with an authored or `npx`-installed skill
  gives two copies of one name. Use `npx` into the shared dir instead when both agents should see it.

### Querying the registry when the CLI is absent

The webui container ships no CLI, so the registry gets queried over HTTP. skills.sh has no public API yet (a
browsable `/api/skills` endpoint is an open feature request, vercel-labs/skills#426) and its pages are a
client-side app, so fetching a search URL returns an empty shell. What works:

- `web_search` with `site:skills.sh <domain terms>` — result snippets carry the skill's own SKILL.md text, which is
  usually enough to judge it without opening the page.
- `web_extract https://www.skills.sh/<owner>/<repo>` — lists every skill in that repo with install counts.
- `web_extract` a single skill page for the full body plus its audit panel.

Run several domain searches in one batch (HA, containers, networking, media, the user's actual stack) rather than
paging a leaderboard.

## Vetting a candidate (applies to either path)

- Per skill page: installs, repo stars, first-seen date, and three independent security audits (Gen Agent Trust
  Hub / Socket / Snyk). `Pass` everywhere is the bar; a `Warn` on a skill that ships scripts is a real signal; any
  `Fail` means skip it.
- The all-time leaderboard is dominated by a few mega-suites (frontend design, vendor SDK packs, cloud vendors) and
  is not a shopping list for a homelab/infra library.
- Overlap first: bundled equivalent, an authored/`npx`-installed name, or a Claude plugin pack already covering it — drop
  those before ranking anything.

### Exclusion patterns

- **Machine-specific suites**: the body is "run `~/<repo>/skills/<x>/scripts/check.sh`" — it only works on the
  machine that authored it.
- **Maintainer-internal sets**: a repo whose skills are its OWN dev workflow (worktree helpers, issue analysis,
  PR checkers, eval harnesses) with ~1 install each — shipped for its contributors, not for users.
- **Mega-packs with a few gems**: 100+ entries that are mostly cloud/LLM filler; cherry-pick the handful that match
  and never recommend the suite as a whole.
- **Hype-only skills**: a title plus "generates production-ready code" and no procedure.

### Report shape

Ranked short list (5 max), one line each: `owner/repo/skill` — installs, audit verdict, and the concrete gap it
fills in THIS library. Then one "deliberately excluded" line naming the near-misses and why, so the user can see
what was considered and rejected. Give the exact install command, note where it lands, and if you could not run
it, say plainly that nothing was installed and the install path is unverified.

### Pitfalls

- **Pre-flight every identifier with `hermes skills inspect <id>` before it reaches the user.** The browsable
  listing and the install namespace disagree: `official/…` resolves for the optional catalog only, so a name that
  ships in the addon's active tree (seeded, never installed) answers "Could not find … in any source" while
  `browse --source official` lists the catalog around it. One inspect per candidate, and never hand over an
  `official/…` install for a bundled name — point at the re-seed instead.
- **Check the platform's own equivalent before recommending a third-party meta-skill.** An
  observation-logging meta-skill duplicates the Curator + `skill_manage` on the Hermes side, and a single-agent fork
  of a cross-platform framework is worth having only for its vendor-exclusive hooks. State the overlap (and which
  agent the thing actually reaches — plugins are Claude-only, hub installs are Hermes-only, the deployed shared dir
  is the one surface both read) rather than listing it as new capability.


## npx skills recipe

For a third-party repo that ships **only** a `skills/` tree (no plugin manifest per harness). Packs
that ship their own per-harness plugins (hooks, slash commands) are a different case — see the end
of this section.

```bash
npx skills add <owner>/<repo> -s <skill> -a claude-code -a codex -g -y   # one skill
npx skills add <owner>/<repo> -a claude-code -a codex -g -y                             # whole pack
```

- **Target `-a claude-code -a codex` — the Claude copy already reaches Hermes.** Hermes reads `~/.claude/skills` via
  `skills.external_dirs`, so the Claude installation serves Hermes too. Adding `-a hermes-agent` puts the same
  name in `~/.hermes/skills` AND under `~/.claude/skills` → two roots, one name, and Hermes refuses
  that name (`Ambiguous skill name … across your local skills dir and external_dirs`).
- **Lands as one canonical copy plus a symlink** (Linux/macOS) — only when ONE call names both agents (`-a claude-code -a codex`); a call naming one agent writes a copy and replaces an existing link: `~/.agents/skills/<name>` is real, `~/.claude/skills/<name>` links to it; check the filesystem, not the CLI's success message. Flat placement, so the entry shows a blank category in `hermes skills list`.
- **The lock is OUTSIDE any repo:** `$XDG_STATE_HOME/skills/.skill-lock.json` (older CLIs: `~/.agents/.skill-lock.json`; the Makefile checks both) (v3: `source`, `sourceType`,
  `sourceUrl`, `skillPath`, `skillFolderHash`). Portability = commit a COPY plus a replay command;
  the live lock is never the record we ship. Replay/drift: `make skills-thirdparty-repo-to-live` / `make skills-status` in
  `makefiles/skills.mk`.
- **Updating:** `npx skills update` is broken (vercel-labs/skills#484 — reports "up to date" while
  upstream moved). Re-add is the update path: `-s <name> -y` refetches and bumps the hash; diff the
  lock to see what moved. Renovate has no skills.sh manager yet (discussion #41841), so automation =
  a scheduled workflow that re-adds and opens a lock-bump PR.
- **Before installing, check the names.** Hermes has no namespacing, so a third-party name that
  collides with a shipped or deployed skill breaks that name for both. Compare against
  `<install>/skills/`, `optional-skills/` and the deployed sets; install a `-s` subset if needed.
- **Symlink regressions exist** → verify the entry actually resolves in
  each agent dir (`find -L … -name SKILL.md`), or fall back to `--copy` (not the default here). A symlink that exists is not
  proof the agent listed it.
- **Supply-chain panel runs pre-install** (Gen / Socket / Snyk). Record the verdict with the lock —
  a replay cannot re-prove it.
- **Node is only in the agent container.** The webui container ships no Node by design, so `npx`
  does not exist there.

**Packs that ship their own per-harness plugins are NOT this flow.** Install them per harness through
that harness's native channel, one canal per agent — never plugin *and* npx for the same agent.
Worked example, `obra/superpowers` (ships `.claude-plugin/`, `.codex-plugin/`, `.hermes-plugin/`,
`.cursor-plugin/`, … plus a SessionStart hook and a `pre_llm_call` bootstrap):

- Claude Code: `/plugin install superpowers@claude-plugins-official`
- Hermes: `hermes plugins install obra/superpowers` — registers every skill namespaced as
  `superpowers:<name>` (so no collision with shipped names) and injects the first-turn bootstrap
- Codex: its own plugin marketplace, `/plugins`
- `npx skills add obra/superpowers` on a harness that has the plugin = the same 15 skills twice, and
  it silently drops the bootstrap hook. Don't.
