# Zone rules and provenance metadata

## Zone rules (companion to the zones table in `SKILL.md`)

- One Hermes brain runs in two HA addon containers (agent + webui) over ONE persistent home, mounted
  `/config` in both (the webui symlinks it at start). Always write `/config/...`; `/addon_configs/<repo>_<slug>`
  is the host spelling and does not exist inside the agent container.
- NEVER copy bundled Hermes skills into the shared dir: they are tool-coupled (`ha_*`/Hermes tools), auto-updated,
  and duplicate names collide. Extract the user's customizations into shared skills instead.
- Shared-dir skills must stay agent-agnostic: terminal/git/gh + stdlib, no Hermes tool references, no single
  repo's workflow, no personal identifiers (names, emails, numeric IDs, home paths). Public
  `github.com/<owner>/<repo>` reference URLs are the deliberate exception and stay as full links.

## Provenance metadata — who owns a skill

Every skill we own records its origin in its own frontmatter, so a reader can tell a repo skill from an
agent-authored one without reading the box:

```yaml
metadata:
  hermes:
    origin: repo:personal-os-setup   # agent | repo:<name> | vendored | hub
    exposure: private                # ONLY when the skill must never be published
```

- `agent` — created in the own store, no git backing (the only promotable kind).
- `repo:<name>` — the canonical copy lives in that repo and is deployed from it.
- `vendored` + `source: <owner>/<repo>` — a third-party copy.
- `hub` — installed from the skills hub; tool-managed.
- `exposure: private` — never promote or publish as-is; absent = publishable (the default).
- Bundled (addon-shipped) skills carry **no** marker: editing one freezes its sync forever, and
  `.bundled_manifest` already records them.
