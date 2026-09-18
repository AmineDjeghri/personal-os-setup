# Skill loading: how a configured skill dir still resolves to nothing

Depth for the "Skills: what's on disk vs what actually loads" section. Authority = `agent/skill_utils.py`
in the installed checkout — read it there when a detail matters.

## The tiers as they exist on this box
| Tier | Canonical location | Read by |
|---|---|---|
| Hermes own store | `/config/.hermes/skills/<category>/<name>/` | Hermes (always) |
| Shared (Track 1) — source | `personal-os-setup/src/personal_os_setup/config/chezmoi/dot_claude/skills/` | both agents, via deploy |
| Shared — deployed | `/config/.claude/skills/` (`make skills-deploy`) | Claude Code (global) + Hermes `external_dirs` |
| Repo runbooks | `<repo>/.claude/skills/` (+ `.agents/skills/` symlinks via `make skills-link`) | Claude in-repo; Hermes only via `external_dirs` or a session rooted there |
| Track 2 (not skill files) | `~/.claude/plugins/`, `$HERMES_HOME/mcp-tokens/` | Claude plugins; Hermes MCP servers |

## What loads, in order
- `get_skills_dirs()` = local `$HERMES_HOME/skills/` → the create dir → every EXISTING `skills.external_dirs`
  entry. External dirs are unconditional: the same list in every session, whatever the working directory.
- Project skills are a separate list (`get_project_skills_dirs()`) that wins on a name clash. They live at the
  project root only: `<root>/.hermes/skills/` and `<root>/.agents/skills/`. A repo that keeps its canonical
  skills in `.claude/skills/` and symlinks `.agents/skills/<name> -> ../../.claude/skills/<name>` is covered —
  the `.agents` view is what counts.
- Later tiers shadow earlier names; `skills.project_discovery: false` (default on) short-circuits the project
  tier entirely.

## Root resolution — the part that silently yields nothing
`find_project_root()`:
1. start dir = the session's own cwd override if one is set, else `TERMINAL_CWD` — **not** the process cwd.
   `TERMINAL_CWD` is the runtime carrier for `terminal.cwd` in config.yaml (`.` = HERMES_HOME), so a global
   value there supplies the start dir for EVERY session.
2. walk up (bounded) to the nearest ancestor containing `.git` (dir or worktree file); a match equal to
   `$HOME` is deliberately treated as "not a project".
3. the root is trusted only when its **resolved path equals** an entry of `skills.trusted_project_dirs`
   (entries get `~` / `${VAR}` expanded, then compared for equality — no globs, no prefix matching, and no
   parent-covers-descendants).
4. `_candidate_project_skills_dirs()` keeps only dirs that exist and are not the profile's own skills dir.
   A non-existent dir is dropped SILENTLY: no CLI warning, and `hermes config check` never inspects skill dirs.

Only ONE root is ever in play, and cwd + trust are fixed at session start (so the skills index stays
byte-stable) — moving around with `cd` mid-session adds no skills.

## Consequences to check BEFORE promising anything
- **A global `terminal.cwd` overrides the session's own cwd**, so the root resolves outside every repo and
  project skills never load — trusted or not. That is a known UPSTREAM DEFECT (project-local discovery
  ignoring the effective session cwd), not user misconfiguration: search upstream for the symptom before
  proposing config churn, then report "known bug, fix in review" + the no-edit workarounds.
- **A trust list of N repos costs nothing until you are in one.** Only the current root's skills are
  enumerated; every other entry is an inert permission.
- **Cost model**: the prompt carries the skill INDEX (name + description, ~1 line each); a body enters
  context only when the skill is opened. Keep `external_dirs` small, and put always-on skills in the shared
  deployed dir — never accumulate per-repo `external_dirs` lines.
- **Path entries resolve literally.** A real install carried `/addon_configs/<repo>_<slug>/.claude/skills`
  plus `/addon_configs/<repo>_<slug>/workspace/<repo>` while the container's HOME is `/config` and
  `/addon_configs` does not exist inside it → the shared skills AND the repo skills loaded for neither agent,
  with no warning anywhere. Audit form: `ls -d <each entry>`, then re-point at `/config/...`. Keep both
  spellings listed only when the same `config.yaml` is read from the webui add-on (its HOME *is* `/addon_configs/...`).
- `skills.external_dirs` must hold CONTAINER paths — `/config/.claude/skills` (plus
  `/config/workspace/personal-os-setup/.agents/skills` when the repo tier must load). The five shared skills
  only appeared after the switch off the `/addon_configs/...` form.

## Upstream tracking (re-check, don't design around it)
The root-resolution behavior above is an open upstream defect — the effective session cwd is supposed to win,
but `find_project_root()` reads only the scoped/global `TERMINAL_CWD`. Handles:

- issue `NousResearch/hermes-agent#103423` — "Project-local skills discovery ignores session.cwd when
  TERMINAL_CWD is set" (P2; a second reporter named `find_project_root()` at the buggy lines on Linux/TUI).
- fix PR `#103424` — "fix(skills): honor session cwd during project discovery" (targets `main`, in review).
- related: one-shot CLI resolving project context against `$HOME` (#95577), linked git worktrees of an
  already-trusted repo (#99566), and the EPIC reworking project-local state with consent gating (#48970).

Re-check after each `hermes update`:

```bash
gh issue view 103423 -R NousResearch/hermes-agent --json state,comments -q '.state'
gh search prs "session cwd project discovery" --repo NousResearch/hermes-agent -L 5
```

…or test the installed loader directly: grep `find_project_root` in `agent/skill_utils.py` — a start dir
taken from `scope_terminal_cwd()` alone means the bug is still present. Until it is fixed, the always-on
route stays the shared deployed dir, never a per-repo `external_dirs` line.

## Decisive probes (read-only)
Run from the repo under test with the install's own interpreter; a heredoc may hit the approval gate, so
write the probe to a file and invoke it by path when that happens.

```python
import sys; sys.path.insert(0, "/config/.hermes/hermes-agent")   # the hermes-agent checkout
from agent import skill_utils as su
print("project_discovery:", su._skills_cfg_get("project_discovery"))   # False => nothing below can load
print("root:", su.find_project_root())                                 # None => no project, by construction
print("trusted:", sorted(str(p) for p in su._project_trusted_dirs_from_config()))
print("dirs:", [str(p) for p in su.get_project_skills_dirs()])          # the final answer
print("untrusted:", su.get_untrusted_project_skills_root())            # (root, count) when the cwd's repo has skills but is untrusted
```

Interpretation: `root=None` + `dirs=[]` while a trust entry exists = the SURFACE CWD, not the trust list, is
the problem. `dirs=[]` with a NON-empty `get_untrusted_project_skills_root()` = mismatch between entry and
resolved path (then hunt symlinked/renamed paths: the same tree reached as `/config/...` and
`/addon_configs/...` will not match). `get_project_skills_dirs() == []` **and**
`get_untrusted_project_skills_root() is None` together mean "no project root was found" — NOT "found but
untrusted". Read `find_project_root()` before touching the trust list.

CLI side: `hermes skills list [--source all|local]` shows builtin/local/hub only — never project skills,
never `external_dirs` skills — so absence proves nothing (its footer totals are still the fastest count).
`hermes skills inspect <name>` resolves across sources and is the cheap end-to-end check.
`hermes config check` validates nothing about skill dirs, so a dead path stays silent.

## The working config block
```yaml
skills:
  external_dirs:
    - /config/.claude/skills
    - /config/workspace/personal-os-setup/.agents/skills
  trusted_project_dirs:
    - /config/workspace/personal-os-setup
```

`trusted_project_dirs` is kept for sessions that genuinely run inside the repo; `external_dirs` is what makes
the repo runbooks visible from a `/config`-rooted session. Verified after the switch: the five shared skills
and the ten repo skills all report `enabled` under `--source local`.

## Loading a repo's skills without hand-editing config
- `hermes skills trust [path]` — the CLI writes the `trusted_project_dirs` entry itself.
- Any surface whose workdir IS the repo: a cron job (`hermes cron add … --workdir <repo>` — the documented
  route for non-interactive surfaces), the WebUI's `default_workspace` option, or a CLI session launched
  from the repo (works only while no global `terminal.cwd` is set).
- Otherwise: read the `SKILL.md` on demand (a repo's AGENTS.md index usually points at it) or promote those
  skills into the shared deployed dir so they are always-on.

## Add-on path duality (why host paths appear in this file's history)
The agent add-on's HOME is the app-config tree mounted at `/config`; the same directory is
`/addon_configs/<repo>_<slug>` (renamed `/app_configs/...` on newer Home Assistant) from the host and from
add-ons that map `all_addon_configs`. The WebUI add-on symlinks `/config` to that view on every start, so
`/config/...` resolves identically in both containers — always write `/config/...` in agent-side config, and
probe both spellings in add-on scripts.

## Reporting rule
Name the missing layer before proposing a fix: path form (container-native vs host-side), root resolution
(`terminal.cwd` / cwd), trust entry, or session-start timing. A corrected dir or trust entry takes effect in
the NEXT session — never claim immediate effect, and never conclude "nothing is configured" from a listing
that structurally cannot show the thing you are looking for.
