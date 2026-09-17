---
name: aiostreams-config-templates
description: Use when authoring or publishing an AIOStreams template.
---

# AIOStreams: configs, templates, variants, sharing

Trigger: "make a template", "let others use my config", "diff between config and template", "parent config", "share my setup" — for the self-hosted AIOStreams add-on in the Stremio/Nuvio stack.

## Start from these facts
- Instance = the `aiostreams` HA add-on (`workspace/ha-addons/addons/aiostreams`). Its `bootstrap.js` maps options onto `BASE_URL`, `SECRET_KEY`, `AIOSTREAMS_AUTH`, `AIOSTREAMS_AUTH_REQUIRED`, `LOG_LEVEL` only — no template-hosting env, so instance-level templates need a new add-on option first.
- Source config: `workspace/personal-os-setup/src/personal_os_setup/config/others/aiostreams-config.json` — a **UI config export** (15 presets, custom formatter, proxy disabled). Exported with *Exclude Credentials*: every `services[].credentials` is `{}`. Re-check before anything is published — a non-empty `credentials`/`apiKey` means it was not.
- Authoring truth is upstream's docs (`docs.aiostreams.viren070.me/reference/templates`, `guides/config-profiles`, `changelog/v2.32|v2.33|v2.34`). Community install guides (3holepunchmedia et al.) only describe importing *someone else's* published template — never the authoring format. Say so when he hands one over as "the tutorial".

## The mechanism, in one block
- **Config export** = the whole state of one configuration, imported as a unit (backup / transfer to another UUID). **Template** = `metadata` + a *partial* `config`, applied at setup ("Use a Template" → import from file or URL). Same JSON body — a template is an export wrapped in `metadata`, with the personal bits parameterized. Field/input/expression tables: `references/template-format.md`.
- **Variant** (v2.33) = a CEL script inside one config, selected per install URL (`/v/<id>/`). **Parent/child config** = a second config inheriting a parent UUID, with its own password and credentials. Distribution → template; one-line per-device/per-person difference → variant; someone needs a genuinely editable config of their own → parent/child.
- Credentials never ship in a template: declare `metadata.services` (+ `serviceRequired`) so the import prompts for them, and reference `{{services.<id>.<key>}}` where a preset needs a key.
- Field the follow-up "how do I make it a template?" as a small job: a metadata block plus de-personalizing, not a rewrite.

## Procedure: export → shareable template
1. Scope, his call in practice: ship the WHOLE setup. The formatter, filters and sort order are the thing being shared — what changes for a template is the service wiring and the personal strings, not the tuning.
2. Run `scripts/export-to-template.py` — the verified conversion (AIOStreams v2.34), never hand-editing 900 lines of JSON: it moves the export body under `config:`, adds `metadata` (`name`, `description`, `author`, `category` required; `id` namespaced `author.my-template`, `source: external`, `version`, inline `changelog`, `sourceUrl`), drops the per-user `trusted` flag, and prints a verification summary (key count, parameterized presets, every URL in the file, any non-empty credential) to read instead of the raw JSON.
3. Make it service-agnostic instead of AllDebrid-only — this is the point of a template and the export does not do it for you:
   - top-level `services`: one `{"__if": "services.<id>", "id": "<id>", "enabled": true, "credentials": {}}` entry per selectable debrid service, the rest left `enabled: false` (a service the user never picked simply drops out of the config);
   - `metadata.services` lists those ids, with `serviceRequired: false` so the wizard offers a **Skip** button for P2P-only users;
   - every preset that hardcoded a service-id list (`torrentio.options.services`, `stremthruStore`, `mediafusion`, ...) becomes `"services": "{{services}}"`.
4. Then de-personalize what is left: `addonDescription` (an export copied from someone else's instance carries their blurb and URL — replace with generic text), custom-preset `manifestUrl`s, TMDB/indexer keys → `inputs.*`, `<template_placeholder>`, `__if`, `__switch` or `__remove`.
5. Test on a throwaway configuration: import the file, then confirm every field the template left blank is flagged as an unfilled placeholder. Static checks cannot exercise `{{...}}` or `__if` — an import is the only proof, so hand him the branch raw URL as soon as it is pushed.
6. Publish, cheapest route first: (a) raw JSON in one of his repos + deep link `?template=<raw-url>`, with `metadata.sourceUrl` for auto-update — `sourceUrl` points at the **main**-branch raw URL while the URL handed over for testing points at the feature branch until it merges; (b) instance-level `templates/` dir or `TEMPLATE_URLS` — needs the add-on option above; (c) the v2.34 in-UI Community share (his instance only, likes, admin moderation, federation from a public instance's `/community/export.json`).

## Pitfalls
- **Never trim presets before grepping the public guide.** `personal-os-setup/docs/android-tv/readme.md` names the disabled optional addons in its optional-addons step (Baguettio, Streamfusion, Statusio, TVMio, AI Search, Top-Streaming) — dropping them from the template silently breaks documented steps. Ship them, disabled. The template and that guide belong in the SAME PR: its template step becomes "Use a Template → Import" with the raw URL, and the step that creates the password/UUID moves AFTER it (the wizard creates the account at the end, not before).
- `{{services}}` as a whole string value resolves to the array of selected service ids (arrays spread into a parent array). Per-service refs exist for credentials only (`{{services.<id>.<key>}}`) — do not invent `{{services.<id>}}` as a boolean for an `enabled` flag.
- Importing a template creates a NEW configuration and leaves his existing one untouched, so "import it right after we push" costs him nothing — offer it as the verification step.
- **Sharing placeholders credentials, API keys and addon passwords ONLY.** Addon URLs, regex patterns, variant scripts and every other free-text field go in as written — read the JSON for anything personal before it is uploaded.
- `metadata.version` + a changelog (`changelog`, or remote `CHANGELOG.md` via `changelogUrl`) is what drives the importer's "update available" notice. Omit both for a one-shot template; the version defaults to `1.0.0`.
- Conditions under `__if`/`__switch` understand `inputs.<id>` and `services[.<id>]` with `!`, `==`, `!=`, `includes`, numeric compares and `and`/`xor`/`or` — not a general expression language, so keep branching to real choices.
- Bare `services` is the debrid-vs-P2P switch (truthy once any service is selected); `services: []` skips the service screen entirely.
- Variants are per-config (10 per config, 4 combined per request, 4000 chars, `VARIANT_ACCESS`) and are **not** inherited from a parent config — they name that config's own addon instance ids and saved formatters.
- A deep-linked template shows the importer a trust warning; always say which source they are importing from.

## Related
- `references/template-format.md` — metadata/input/condition tables, the skeleton, and the sharing routes.
- `scripts/export-to-template.py` — export → template converter (metadata block, `trusted` dropped, `__if` services, `{{services}}` refs, all presets kept) with a verification summary; run it before any hand-edit.
- Add-on packaging for the instance itself: `home-assistant-addon-dev`. The repo holding the config export: `personal-os-setup-repo`.
