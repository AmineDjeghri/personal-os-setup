# Which agent reads which root

| Agent | Roots it reads |
|---|---|
| Claude Code | `~/.claude/skills` (native), its plugin dir, the account-sync mirror under that; **not** `~/.hermes/skills` |
| Hermes | `~/.hermes/skills` **and** `~/.claude/skills` (`skills.external_dirs`), plus each profile's own dir |
| Codex | its own dir only — a second copy there is harmless |

## Combinations

| Combination | Verdict |
|---|---|
| `-a claude-code` | safe — serves Claude natively and Hermes via the external dir |
| `-a codex` / `-a claude-code -a codex` | safe — no agent reads both copies |
| `-a claude-code -a hermes-agent` | **breaks the name** — Hermes reads both roots |
| `-a '*'` | **breaks the name** — expands to the pair above |
| symlink `~/.hermes/skills/<n>` → `~/.claude/skills/<n>` | **breaks the name** |
| a backup/archive left under a scanned root | **breaks the name** |
| `.agents/skills/<n>` → `.claude/skills/<n>` (repo-scoped) | safe — no agent reads both sides |

## Detecting and removing a duplicate

The `matches:` list in the refusal names the copy to remove; loading by `category/skill-name` is a diagnostic
workaround, not a fix.

1. Decide the keeper (deployed/authored, or upstream-sourced).
2. Confirm the keeper is complete (file count, `SKILL.md` present) **before** deleting the other — a name the
   agent never shipped has no reseed path, so deleting the wrong copy can drop it from the library.
3. Delete, then load the bare name to prove it resolves.
