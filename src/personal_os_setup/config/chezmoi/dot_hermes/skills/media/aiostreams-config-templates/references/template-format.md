# AIOStreams template format & sharing routes

Condensed from `docs.aiostreams.viren070.me/reference/templates`, `/guides/config-profiles`, `/changelog/v2.32`–`v2.34`. Re-fetch the reference page if a field here no longer loads.

## Skeleton
```json
{
  "metadata": {
    "id": "author.my-template",
    "name": "Display name",
    "description": "Markdown allowed",
    "author": "handle",
    "category": "Debrid",
    "version": "1.0.0",
    "source": "external",
    "services": ["alldebrid"],
    "serviceRequired": true,
    "sourceUrl": "https://raw.githubusercontent.com/<owner>/<repo>/main/template.json",
    "changelogUrl": "https://raw.githubusercontent.com/<owner>/<repo>/main/CHANGELOG.md",
    "inputs": [ /* see below */ ]
  },
  "config": { /* partial config — same keys as a UI export */ }
}
```

## metadata
| Field | Notes |
| --- | --- |
| `id` | namespaced form `author.my-template`; a UUID is generated when omitted |
| `name` / `description` / `author` / `category` | **required**; author and category are short strings |
| `version` | semver, defaults `1.0.0`, used for update comparisons |
| `source` | `builtin` (default) / `custom` / `external` — user imports are `external` |
| `services`, `serviceRequired` | control the service screen (below) |
| `sourceUrl` | where it was fetched from — enables auto-update |
| `setToSaveInstallMenu` | default `true`; redirects the UI to Save & Install after load |
| `changelog` / `changelogUrl` | inline history, or remote `CHANGELOG.md` (url wins) |
| `inputs` | user-fillable options shown before loading |

## Service handling
| metadata | Behaviour |
| --- | --- |
| `services` unset | all services offered |
| `services: []` | service screen skipped |
| `services: ["alldebrid", "torbox"]` | only those offered |
| one service + `serviceRequired: true` | skipped, credentials asked for directly |
| `serviceRequired` absent/false | a **Skip** button is offered |

At load time selected services are readable as `services.<id>`; bare `services` is truthy when at least one is selected (the debrid-vs-P2P switch).

## inputs (`metadata.inputs`)
Fields: `id`, `name`, `description`, `type` (all required), `required`, `default`, `options: [{value,label}]`, `showInSimpleMode` (default true; `advanced: true` is shorthand for false), `constraints: {min,max,forceInUi}`, `__if` (only `services.<id>`), `intent` (alert), `socials`.

Types: `string` · `password` · `number` · `boolean` · `select` · `select-with-custom` · `multi-select` · `url` · `alert` · `socials` · `subsection` (modal of `subOptions`, values via `inputs.<id>.<sub>`; `subsectionIntent` = default|block|inline|pill|link|banner) · `nab-endpoint` (Newznab/Torznab `url` + `apiKey` pair with a server-side probe).

## Directives
- `{{...}}` string interpolation; `{{inputs.x}}`, `{{services.id.key}}`, `{{services}}`. A whole-value `{{...}}` keeps its type (arrays spread into the parent array).
- `__if` on an object inside an array (item included when true) or as `{"__if": cond, "__value": X}` when it is a key's value.
- `__switch: "<expr>"` with `cases` / `default` replaces a whole object (`""` is the no-service case for `services`).
- `__value` injects values into a parent array; `__remove: true` drops a key (pair it with a `__switch` case that means "leave unchanged").
- Placeholders for fields the user fills after load: `<template_placeholder>` / `<required_template_placeholder>` / `<optional_template_placeholder>`.

## Conditions
Bare reference (truthy unless `false`/`null`/`""`/`[]`; `0` is truthy) · `!x` · `x == premium` · `x != none` · `arr includes "dv"` · `n > 5` (also `>=`, `<`, `<=`) · `services` / `!services` / `services.alldebrid` · `inputs.proxy.url` · `a and b` · `a or b` · `a xor b` (precedence and > xor > or).

Validation: missing required metadata, a bad `source`, or malformed `__if`/`__switch` block loading; a `{{inputs.x}}` reference with no matching input is only a warning.

## CHANGELOG.md format (when `changelogUrl` is used)
`# Changelog`, then `## <semver> (<YYYY-MM-DD>)` newest first, notes as bullets (a `###` sub-heading is allowed).

## Sharing routes
- Instance `templates` folder in the data dir (`/app/data/templates` in the upstream image), or `TEMPLATE_URLS` = JSON array of URLs.
- Deep link: `<instance>/stremio/configure?template=<url>` (add `&templateId=author.my-template` to preselect in a multi-template file); the importer sees a trust warning.
- v2.34 community sharing: `COMMUNITY_TEMPLATES` / `COMMUNITY_FORMATTERS`, moderation in Dashboard → Community, federation via `/community/export.json` (`COMMUNITY_PUBLIC_EXPORT`) and `COMMUNITY_REMOTE_SOURCES`. Templates upload as written apart from credentials/API keys/addon passwords.
- `MAX_JSON_BODY_SIZE` (default 256 KiB) can reject a large template or config on save.

## Neighbouring features (don't mix them up)
- **Profiles / aliases (v2.32)**: a profile stores a config against an account sign-in (needs `AIOSTREAMS_AUTH` or SSO); an alias publishes it at `/stremio/u/<alias>/manifest.json` — 2–64 chars, `a-z0-9._-`, globally unique. Instance-wide **Aliased configurations** (`ALIASED_CONFIGURATIONS`) resolve first and win.
- **Variants (v2.33)**: CEL-style script inside the config (`set`, `merge`, `add`/`prepend`/`remove`, `unset`/`clear`, `enable`/`disable`, `use formatter`), path selectors such as `presets[type=torrentio]` and `services[id=realdebrid].credentials.apiKey`; selected in the URL, or auto-applied via an activation condition over `userAgent`, `resource`, `type`, `id`, `query('x')`, `header('x')`, `health('id')`. Limits: 10 per config, 4 combined per request, 4000 chars, `VARIANT_ACCESS` = all|trusted|none. Not inherited from a parent config.
- **Parent/child config**: child inherits everything except the sections it overrides (merge strategies in the UI); costs a second UUID/password; unlike a variant it is genuinely the holder's own config with their own credentials. Use a variant first for a one-line difference; parent/child only for a real second owner.
