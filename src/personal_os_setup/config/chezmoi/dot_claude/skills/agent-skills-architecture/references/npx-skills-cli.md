# `npx skills` — verified surface and semantics

Install flags, `--copy`, `-a claude-code` only, the lock location, replay and update-is-broken: `skill-deployment`.
Only what that skill doesn't carry is here.

## Sources accepted by `add`

`owner/repo`; a bare name resolved through skills.sh; a GitHub URL or a webpage URL. **No local path** — a
machine with no network and no clone gets nothing through this channel.

## Commands

| Command | Does |
|---|---|
| `add <pkg>` (`a`) | install |
| `remove [skills]` | uninstall (does not remove it from a mirror or another agent's dir — check every root) |
| `list` / `ls` | what this machine has installed |
| `find [query]` | interactive search; `--owner <owner>` restricts it |
| `use <pkg>@<skill>` | generate a prompt for one skill **without installing it** |
| `update` | nominally updates — can report "up to date" when it is not; re-add instead |
| `experimental_install` | restore from a `skills-lock.json` — a *different* file name from the one a normal install writes |
| `experimental_sync` | copy skills found in `node_modules` into agent dirs |
| `init [name]` | scaffold `<name>/SKILL.md` |

Other `add` flags: `-g` user-level, `-s <skills>` (`'*'` = all), `-l` list what the source offers and install
nothing, `-y` skip prompts, `--subagent <names>`, `--metadata <json>` (install telemetry).
`-l` first confirms a source exists and what its skills are called.

**Discovery is location-limited.** `-l` sees only skills in conventional places: pointed at a repo whose skills
live under a dotfiles source path, it listed that repo's own `.claude/skills` and *none* of the authored tree.
"Make my own skills installable" needs a conventional layout or a manifest — run `-l` before promising it.

## Lock file

`~/.agents/.skill-lock.json` (v3; newer CLIs: `$XDG_STATE_HOME/skills/`). Per skill: `source`, `sourceType`,
`sourceUrl`, `skillPath`, `skillFolderHash` (an upstream git tree SHA — "what to re-fetch", never "what to
reproduce" or a local-integrity check). Only the lock lives in `~/.agents/`; skill files land in the agent's
own dir, so `~/.agents/skills` is not a canonical store. Keep the committed copy out of a dotfiles source that
would overwrite the live lock.

## Behaviour worth knowing

- A supply-chain panel (Gen / Socket / Snyk) runs before install; record its verdict next to the lock entry.
- No dependency-automation support: currency = scheduled replay or manual re-add, never a Renovate-style manager.
- Before installing, check the name against every root (`store-reconciliation.md` → Sweep).
