# What Hermes itself does to the library — and the gates that stop it

## Mutations nobody asked for

- **Bundled seeding.** Install and *every* `hermes update` copy newly bundled skills into the live store: new
  upstream skills appear in the library whether or not the user wants them. `hermes skills opt-out` writes the
  marker `~/.hermes/.no-bundled-skills` (stops future seeding, deletes nothing); `hermes skills opt-in --sync`
  reverses it. Offer this knob whenever the complaint is "we cannot keep up with upstream's skills".
- **The origin hash.** `~/.hermes/skills/.bundled_manifest` stores each bundled skill's origin content hash. Edit a
  bundled copy and every later sync SKIPS it — your edits are never stomped, and never updated again. That is what
  strands a skill between upstream and local: `hermes skills list-modified` names the frozen ones ("everything
  tracks upstream" means none are), and `hermes skills reset <name>` clears the entry so upstream changes flow again
  (keeps your copy); `hermes skills reset <name> --restore` replaces it with the pristine bundled file.
- **Hub-installed skills.** `hermes skills check` / `hermes skills update`; locally edited ones are skipped unless
  `--force`. `~/.hermes/skills/.lock.json` is the provenance for these.
- **Curator archiving.** The LLM review only touches agent-created skills, but the deterministic inactivity walk also
  acts on inactive bundled skills (`curator.prune_builtins`), archiving past `stale_after_days`/`archive_after_days`
  (14/30 on this box). Archiving is restorable and a pin (`hermes curator pin <name>`) exempts a name from every
  transition, so a skill that "disappeared" was usually archived — check before calling it lost.
- **Where NEW agent-created skills land.** The live store, unless `skills.create_dir` points elsewhere. This is the
  standing explanation for "a skill I never placed showed up outside my repos"; when new skills must be versioned
  from birth, point `create_dir` at a git-tracked path.

## The platform's own "too long" alarms (write-time lints)

- `oversized-body` — SKILL.md body beyond roughly 24k chars.
- `references-sprawl` — more than ~60 files in `references/`.
- `incident-log-shape` — dated narrative where a rule belongs.

These thresholds are the contract behind progressive disclosure: thin SKILL.md with always-on rules, topical
reference files for depth, and re-runnable or copyable artifacts in their own support directories. Keeping under them is the
cheapest defence against "skills get heavy and too long". `/learn` on a topic that already has a skill folds the new
material into that skill rather than adding a duplicate — the same rule this library applies by hand.

## Gates that make library changes reviewable

- `skills.write_approval: true` and `memory.write_approval: true` make the post-turn background review **stage**
  every skill/memory change instead of applying it. In practice this is the answer to "I cannot follow what the agent
  changes": `/skills pending`, `/skills diff <id>`, `/skills approve|reject`, `/skills approval on|off`; memory:
  `/memory pending`, `/memory approve|reject`. Staged skill writes are one JSON per change under
  `~/.hermes/pending/skills/`; staged memory writes are one file per change under `~/.hermes/pending/memory/`.
- Background-review knobs: `auxiliary.background_review.enabled` (`false` = no automatic post-turn forks; a manual
  `/refine` still works), `.model` (route the review to a cheap model), `.max_input_tokens`, `.defer`;
  `display.memory_notifications: off|on|verbose` only changes the chat line, never the writes.
- **Staged is not applied.** A backlog in `pending/` means the learning loop is queued, not live: count it in every
  audit and review it with the user instead of assuming memory is current. Both gates ship **off**, so an ungated box
  applies background skill edits silently — check the value before reasoning about how a skill changed.

## Memory: bounded, frozen, never synced

- `~/.hermes/memories/MEMORY.md` (2,200 chars) and `USER.md` (1,375) are injected as a **frozen snapshot** at session
  start — a write made mid-session appears in the *next* session, not the running one.
- **No auto-compaction.** An over-limit write returns an error and the agent must consolidate or remove entries in
  the same turn; `replace` overwrites the whole matched entry (`old_text` only locates it). Limits are config keys
  (`memory.memory_char_limit`, `memory.user_char_limit`) — read them, don't assume the defaults.
- `hermes update` never touches memory: there is no bundled memory and no sync pass. Its only writers are the
  `memory` tool and the background review. So "memory got heavier after an update" is a misdiagnosis — look at the
  review's staged writes instead.
- Prune and correct with `hermes journey list|delete|edit` (`/journey` in chat and the desktop panel). Deleting a
  skill node archives it; deleting a memory chunk removes it.
- Route facts deliberately: durable facts that apply to every session go to memory; anything a *task* needs belongs
  in a skill, which loads only when relevant and does not compete for the character budget.

## One read-only sweep that uses all of this

```
hermes skills list-modified          # bundled copies frozen by local edits
wc -l < ~/.hermes/skills/.bundled_manifest   # seeded count
ls -la ~/.hermes/.no-bundled-skills  # seeding disabled?
ls ~/.hermes/pending/skills ~/.hermes/pending/memory | wc -l   # unreviewed backlog
hermes config get skills.write_approval; hermes config get memory.write_approval
hermes config get curator.stale_after_days; hermes config get curator.prune_builtins
hermes config get skills.create_dir; hermes config get skills.external_dirs
```

Report the findings as knobs, not as work: `opt-out`, `create_dir` and the two `write_approval` flags are one-line
`hermes config set` changes the user can take or leave. Never fold them into an unrelated change, and never hand-edit
`config.yaml` — the CLI is the only supported write path.
