# Community skills — two independent discovery paths

There are two unrelated ways to pull in a community skill. Pick by WHO should see it: the Vercel
`skills` CLI installs a real directory into `~/.claude/skills` (both agents, via the shared dir); the Hermes hub installs straight
into the own store (Hermes-only, tool-managed). Never treat them as the same pipeline.

## Path 1 — `npx skills` (shared dir, both agents)

Install per `AGENTS.md` (`npx skills add <owner>/<repo> -s <skill> -a claude-code -g -y --copy`); `--copy` makes the agent dir hold a real directory.

### Known pitfalls

- Installer may write into repo-relative paths when run from a project dir — run from a neutral cwd for global installs.

## Path 2 — Hermes hub discovery (own-store install, Hermes-only)

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
