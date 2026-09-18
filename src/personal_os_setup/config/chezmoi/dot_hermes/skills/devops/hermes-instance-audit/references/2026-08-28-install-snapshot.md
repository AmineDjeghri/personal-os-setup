# 2026-08-28 install snapshot + diff-sweep technique (Hermes v0.20.6)

Verified facts from a full audit of this install. Use as the "known-good baseline" when
answering "what do we have / what changed" — and rerun the sweep below to refresh it.

## Environment
- Hermes v0.20.6, git-installed at `/config/.hermes/hermes-agent` (HA addon, Debian 12 container).
- Checkout was at origin/main tip (`git rev-list --count HEAD..origin/main` = 0), 100 commits
  ahead of newest tag `v2026.8.27`; `.update_check` said `behind: 0` → up to date.
- Claude Code: native install v2.1.248 at `/config/.local/bin/claude` (symlink →
  `/config/.local/share/claude/versions/2.1.248`), OAuth-authed via claude.ai (Pro).
  - Login/re-auth: `claude auth login` prints a one-time authorize URL and waits for a pasted
    code (format `<code>#<state>`). Bare `claude` in a background PTY gets stuck on the first-run
    theme picker — prefer `claude auth login` for headless/agent-driven auth.
  - `claude doctor`'s "~/.local/bin not in PATH" warning is expected and harmless here; always
    invoke via the absolute path (gateway PATH lacks it).

## Skill inventory (on-disk 109 SKILL.md = 72 present bundled + 37 extras)
- **70/82 bundled: byte-identical** to latest repo stock (`diff -r`).
- **10 user-deleted** (all still in `.bundled_manifest` → synced once, then removed; respected by
  sync, never re-added): airtable, codex, huggingface-hub, llama-cpp, notion, openhue, powerpoint,
  teams-meeting-pipeline, touchdesigner-mcp, weights-and-biases.
- **2 differing** — read the direction before acting:
  - `github-auth` = **STALE stock** (older baked copy). Upstream since added
    `scripts/git-credential-token.py`, a curl-based manual device flow with polling, a headless
    `hosts.yml` fallback, HERMES_HOME-aware paths. No custom content → safe to refresh with
    `hermes skills reset github-auth --restore`.
  - `github-pr-workflow` = **USER-MODIFIED** (keep!): custom `§2.5 Pre-Push Checklist` section
    (git author email MUST be `12345678+your-username@users.noreply.github.com`, run pre-commit on
    changed files, conventional commit + PR title, CRLF/.gitattributes check, force-push
    etiquette) plus `python`→`python3` fixes. Sync skips it (protected); do NOT reset it.
- **37 extras** = 10 from optional-skills (hermes-s6-container-supervision, subagent-driven-development,
  polymarket, baoyu-article-illustrator, pixel-art, creative-ideation, baoyu-comic, heartmula,
  obliteratus, godmode) + 27 created locally in sessions (hermes-* / home-assistant-* / kanban-* /
  messaging-integration, webhook-subscriptions, personal-os-setup-repo, petdex,
  youtube-download-automation, macos-computer-use, writing-plans, web-scraping,
  advanced-web-scraping, debugging-hermes-tui-commands, native-mcp, web-research,
  github-community-health-files, hermes-context-usage, claude-code-ops, segment-anything, audiocraft).

## Config / curator state
- `skills.disabled:` 36 entries (some dead names: kanban-codex-lane, ideation,
  segment-anything-model, audiocraft-audio-generation — harmless dead config).
- `curator:` enabled, `interval_hours` 168 (weekly), `stale_after_days` 30, `archive_after_days` 90,
  `consolidate: false`. Weekly pre-run backups in `.curator_backups/<ts>/` (manifest.json +
  skills.tar.gz ~2.2 MB / 94 files). `.usage.json`: **35 active / 55 stale / 90 tracked**.
- No `.no-bundled-skills` marker (seeding active). `.bundled_manifest` = 82 entries (all bundled).

## Content sweep one-liner (passes the approval gate; execute_code does not, see SKILL.md step 4)
```bash
B=/config/.hermes/hermes-agent/skills; I=/config/.hermes/skills   # <repo>/skills vs ~/.hermes/skills
while IFS= read -r d; do rel=${d#$B/}; [ ! -d "$I/$rel" ] && echo "MISSING: $rel"; \
  diff -rq "$d" "$I/$rel" >/dev/null 2>&1 || echo "DIFFERS: $rel"; \
done < <(find "$B" -name SKILL.md -printf '%h\n')
```
MISSING = user-deleted (respected). DIFFERS = stale stock OR user-modified → `hermes skills diff <name>` decides.

## Delete vs disable (recommendation for "lean setup" questions)
- **Delete**: frees ~no disk; makes the skill INVISIBLE to the agent — nothing ever proposes
  reinstalling a skill it can't see. Restore is manual: `hermes skills reset <name>` + `hermes update`
  (or copy the dir from `<repo>/skills/`, offline-safe). Optional skills: `hermes skills repair-official <name> --restore`.
- **Disable** (`hermes skills config` / `skills.disabled:`): same zero runtime cost, reversible,
  keeps edits, still discoverable by the agent. Default recommendation: disable, delete only when sure.
- The curator already auto-prunes stale bundled skills (30 days idle) with backups — manual deletion
  is only needed for "definitely never" calls.

## Approval-gate behavior on this setup (verified 2026-08-28)
Read-only plain-shell one-liners (git fetch, find, diff -rq, md5sum, grep) passed the gate.
`execute_code` scripts and `python -c`/heredoc scripts were blocked by consent timeout → for audits,
prefer read-only shell one-liners and native file tools (read_file / search_files / web_extract);
never retry a blocked call.
