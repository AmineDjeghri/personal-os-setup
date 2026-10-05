# Skills sync semantics + the diff-sweep technique

## skills_sync.py — manifest-based bundling (from tools/skills_sync.py docstring)

Manifest: `~/.hermes/skills/.bundled_manifest`, format `skill_name:origin_hash` (MD5 of the
bundled skill at last sync). v1 manifests (plain names) auto-migrate to v2.

Update logic:
- **NEW** (not in manifest): copied to user dir, hash recorded.
- **EXISTING** (in manifest, present): bundled still matches hash → skip; bundled changed + user
  copy untouched → safe update; bundled changed + user copy differs → **user customized, SKIP**.
- **DELETED by user** (in manifest, absent from user dir): **respected, never re-added**. ← explains
  "missing bundled skills"
- **REMOVED from bundled** (in manifest, gone from repo): cleaned from manifest.

Opt-out marker: `~/.hermes/.no-bundled-skills` (written by installer `--no-skills` or `hermes
profile create --no-skills`). When present, sync is a no-op — delete the file to opt back in.

Bundled dir resolution: `HERMES_BUNDLED_SKILLS` env var first, else `<repo>/skills/` relative to
the source file.

Curator interplay: bundled + hub-installed skills are off-limits to the curator
(`tools/skill_usage.py` `off_limits = bundled | hub_installed`); it only marks stale/reactivates.
User-deleted bundled skills are NOT re-added by sync.

## Repo layout

| Zone | Content | Synced to user dir? |
|---|---|---|
| `<repo>/skills/` | bundled skills | Yes (manifest-based) |
| `<repo>/optional-skills/` | optional skills | No (installed on demand) |
| `<repo>/plugins/` | bundled plugins (browser, context_engine, cron_providers, dashboard_auth, disk-cleanup, google_meet, hermes-achievements, image_gen, kanban, memory backends, model-providers, observability, platforms, security-guidance, spotify, teams_pipeline, video_gen, web backends) | Loaded from repo; `~/.hermes/plugins/` is for user plugins |

Exact bundled/optional counts drift every release — don't hardcode them here; `skills_list`
(session tool) or `ls <repo>/skills | wc -l` gets the live number.

## Running a diff sweep (the reusable technique — rerun this, don't re-paste old output)

**Content sweep one-liner** (passes the approval gate; `execute_code` does not — prefer this over a
python script for an audit):

```bash
B=/config/.hermes/hermes-agent/skills; I=/config/.hermes/skills   # <repo>/skills vs ~/.hermes/skills
while IFS= read -r d; do rel=${d#$B/}; [ ! -d "$I/$rel" ] && echo "MISSING: $rel"; \
  diff -rq "$d" "$I/$rel" >/dev/null 2>&1 || echo "DIFFERS: $rel"; \
done < <(find "$B" -name SKILL.md -printf '%h\n')
```

MISSING = user-deleted (respected). DIFFERS = stale stock OR user-modified → `hermes skills diff
<name>` decides which.

**Delete vs disable** (the answer to "should I clean this up?"):
- **Delete**: frees ~no disk; makes the skill INVISIBLE to the agent — nothing ever proposes
  reinstalling a skill it can't see. Restore is manual: `hermes skills reset <name>` + `hermes
  update` (or copy the dir from `<repo>/skills/`, offline-safe). Optional skills: `hermes skills
  repair-official <name> --restore`.
- **Disable** (`hermes skills config` / `skills.disabled:`): same zero runtime cost, reversible,
  keeps edits, still discoverable by the agent. Default recommendation: disable, delete only when
  sure.
- The curator already auto-prunes stale bundled skills (idle past `stale_after_days`) with backups
  in `.curator_backups/<ts>/` — manual deletion is only needed for "definitely never" calls.

**Approval-gate behavior for audits**: read-only plain-shell one-liners (git fetch, find, diff -rq,
md5sum, grep) pass the gate; `execute_code` scripts and `python -c`/heredoc scripts get blocked by
consent timeout. For an audit, prefer read-only shell one-liners and native file tools (read_file /
search_files / web_extract) over scripted checks — never retry a blocked call.

## Release-note grepping tip

GitHub release JSON via `web_extract` lands as ONE giant line in the cache file —
`read_file`/grep by line fails. Use `execute_code` with `re.finditer` over the raw text and slice
`[i-150:i+220]` for context.
