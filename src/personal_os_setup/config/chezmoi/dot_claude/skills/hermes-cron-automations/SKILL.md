---
name: hermes-cron-automations
description: "Use when building a recurring automation on the Hermes box."
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Recurring automations on the Hermes box

Class of task: "every day/hour, go get X from the internet and tell me about it" — news and feed digests, source
monitors, listing scouts, periodic scrapes. Source-specific access facts: `references/feed-sources.md`.

## When to Use

- "Send me news/feeds/deals every morning", or any *every-day-get-me-X* recurring job.
- Deciding where a scheduled personal automation should live (cron vs add-on vs new repo),
  or being asked to adopt a third-party tool for it.
- Writing or editing the collector/digest scripts or the source list behind such a job.
- Being asked to consult another model for a build-or-adopt opinion (§4).

## 0. Decide first: Hermes cron, not a new service

| Want | Build it as |
|---|---|
| Scheduled fetch/filter/summarize/deliver | **Hermes cron job(s)** — no daemon, container or new repo |
| Reusable procedure the job follows | a **skill** in the shared authored tree |
| Non-trivial fetch/normalize/dedupe logic | a **PEP 723 script** in the repo, run via `uv run --no-project` |
| A page to look at it | *only then* consider a UI — an add-on, or the user's existing app |

- **No new HA add-on for a scheduled job the agent can run directly.** The user's one general-purpose UI add-on
  (NiceGUI + FastAPI + Ollama) is unauthenticated and LAN-only by design, with its own tooling and release
  pipeline; scheduling a personal push inside it buys a service to maintain.
- **No third-party "capability layer"/CLI stack whose value is the logged-in browser route.** This is a headless
  container with no desktop browser profile, and cookie/exported-session routes risk account bans. Take the two
  ideas (ordered backend list per source class; a `doctor` probe command) and skip the dependency — the agent
  already has `web_search`, `web_extract`, a headless browser, `curl` and `uv`.
- **Never a self-hosted aggregator suite** (RSS-to-everything servers, feed readers, workflow engines): the user
  refuses to run a service to baby-sit for something they only consume. Library deps in the script
  (`feedparser`-class) are fine.

## 1. Answer the architecture question with a verdict

- On "what is the best choice?" give **one recommendation and the reason**, rejected options compressed to a line
  each. A pick-one menu is for choices that are genuinely the user's (which sources, which shops), not for a
  technical judgement they asked you to make.
- Asked for a second opinion from another model: do it and relay it, with what you verified yourself on this box
  alongside (§4) — the delegate's suggestions are claims, not findings.
- State the placement decision and file layout *before* writing code, and wait. The source list is the user's
  input: ask for real URLs/subreddits/shops rather than inventing a plausible list.

## 2. The two-tier cron pattern

Two jobs, one ledger. Tier 1 is free; tier 2 costs exactly one bounded LLM call.

**Tier 1 — collector (zero tokens, no LLM).**

```bash
hermes cron create "every 1d at 06:30" \
  --name "<name>-collect" \
  --script collect.py --no-agent
```

- `--script` must point at a file **under `~/.hermes/scripts/`** (`.sh`/`.bash` → bash, anything else
  → Python). Only the *wrapper* needs to live there; the real implementation stays in the repo and
  the wrapper calls it.
- `--no-agent` is the load-bearing flag: the script **is** the job, its stdout is delivered
  verbatim, there is no agent loop and **no LLM call at all**. Empty stdout = silent run.
- The script fetches every configured source, dedupes against state, appends new items to a
  **daily ledger file**, and prints a short health report (or nothing when all is well and nothing
  is new).

**Tier 2 — digest (agentic, once a day).**

```bash
hermes cron create "every 1d at 07:00" \
  --name "<name>-digest" \
  --skill <name>-digest \
  --workdir /config/workspace/<repo> \
  --deliver telegram
```

- The job prompt must be **self-contained** — a cron run is a fresh session with no memory of this
  conversation; name the ledger path, the state path and the delivery format in the prompt itself.
- Attach the workflow skill with `--skill` instead of pasting the procedure into the prompt.
- `--workdir` loads that directory's `AGENTS.md`/`CLAUDE.md` and pins the file/terminal/code tools
  to it. Omit it for pure fetch-and-summarize jobs.
- Cap the work: N items per source and a character cap per item, enforced *in code*, and **skip the
  LLM entirely when the ledger is empty** (send nothing, or one line) — that is what keeps a daily
  digest cheap.
- Delivery: `--deliver origin` for the chat that asked, `telegram` for the home channel,
  `platform:chat_id` to target elsewhere. `--failure-deliver` routes run failures separately;
  `local` suppresses failure notices (state stays visible in `hermes cron list`).
- Per-run model pinning exists (`--model` / `--provider` / `--pin`, or `cron.model` for the whole
  fleet) and a per-job `--reasoning-effort`; neither applies to `no_agent` jobs.

**Ledger and health rules.**

- Update state (seen IDs / content hashes) **only after delivery succeeds**, so a failed send
  repeats instead of silently dropping a day's items.
- End every digest with a **health footer**: each source that failed, by name, with the reason, and
  a "dead since <date>" marker once it has failed repeatedly. A collector that can only ever say
  "nothing new" is indistinguishable from a broken one.
- Offer the same check on demand as a `--doctor` subcommand of the script (probe every source, print
  OK/FAIL with the reason). This is the only defence against source rot.

### The two lists (interest profile)

Every digest is split in two, and the split is driven by ONE profile shared by every source class:

- **`⭐ might interest you`** — matched items, each line saying *why* (`matched topic: mcp`).
- **`rest`** — everything else, one compact line each. Nothing is silently dropped.

- **One `interests.yaml`, never one per source type.** The same include/exclude engine (topics,
  keywords, language) scores a GitHub repo, a shop flyer and a blog post; source-specific extras hang
  off a `per_source:` key so the shared part stays shared. Tuning the profile once upgrades every
  source — that is the point of the file (the "what I like" list must serve supermarket
  catalogs as well as repos).
- **Matching runs in the collector, deterministically**, and each item is stored *pre-tagged* with its
  score and the rules that fired. Free (no LLM call per item), auditable, and the agentic tier then
  only writes prose and judges borderline items.
- **`exclude` demotes, it never hides**: an excluded item stays visible under `rest`.
- **The profile and the source list are personal data in a PUBLIC repo**: commit
  `interests.example.yaml` / `sources.example.yaml` (schema only) and keep the real files outside git,
  beside the state dir.

### Build order: one source end to end, then widen

The parts that fail are the parse, the dedupe key and the state update — not the message template.
Prove those on ONE source before wiring a second, or a wrong dedupe key reads as "the other sources
are broken".

1. **Collector first, one source.** Config + parse + state + a `--doctor` that prints per-source
   OK/FAIL. Run it twice by hand: the second run on unchanged input must report *nothing new*. If it
   re-sends, the dedupe key is wrong — fix it before five sources inherit the bug.
2. **Then the agentic tier on that same source**, and confirm one real message lands in the target
   chat. Break one URL on purpose once: the digest must still send, with a health footer naming that
   source. A digest that silently omits a dead source is the failure the design exists to prevent.
3. **Then add sources one at a time** — each a YAML entry plus at most one extractor — repeating the
   two-run check. Honour the user's scoping exactly: "v1: only this source, weekly" means build only that;
   the next source is later work, not a hidden extra in the first pass.
4. **Lead with `--doctor` output** whenever the user asks whether it still works: one command answering
   "which sources are alive" beats a narrative about what the code does.

## 3. File layout (repo canon + thin wrapper)

Mirror the existing YouTube-download pipeline:

```
<repo>/docs/<area>/<name>/          # canon, committed
  <name>.py                         # PEP 723 header → uv run --no-project <name>.py
  sources.yaml                      # the source list; adding a source is a YAML edit, never code
  README.md
~/.hermes/scripts/<name>_collect.py # 3-line wrapper the cron --script points at (outside git)
<state dir outside the repo>        # seen-IDs/hashes, ledger, logs
```

- **Never collapse the three roles into one folder inside the skill**, even when asked: the skill directory is
  *deployed* (overwritten by the next apply) and *committed to a public repo*, so live state inside it is
  clobbered and published, and often-changing code turns every tweak into an edit → deploy → pin cycle.
  Instructions in the skill, code + README in the repo's docs tree, state/profile/logs outside git — name which
  role each file plays so the split reads as deliberate.
- **Recon a site before writing its extractor**: robots.txt → sitemap.xml → embedded `application/ld+json` →
  what the page fetches at runtime. A JSON-LD `ItemList` beats a hand-rolled HTML parser and needs no key
  (`references/feed-sources.md`).
- Changing the source list is the only case needing the user's confirmation gate — not every scheduled run.
- State and logs stay **outside the repo**, so nothing personal is committed and a checkout/CI never resets
  what has been seen.
- The chezmoi source carries no scripts directory, so a small unmanaged wrapper under `~/.hermes/scripts/` is
  the normal arrangement, not a smell.

## 4. Second opinion from another model

Relay it with what you verified yourself on this box alongside; recipe (stdin brief, read-only tools, verify claims): `claude-code-ops` → "Advisory delegation".

## 5. Pitfalls

1. **A source returning zero items is a failure, not "no news"** — compare against its normal volume and surface
   it in the health footer.
2. **Never hand-edit `~/.hermes/cron/jobs.json`.** Create/edit through the `cronjob` tool, `hermes
   cron …`, or `/cron`; direct edits can be blocked by file-write safety and fail silently.
3. **Read `robots.txt` before wiring a source, and never bypass a paywall or login.** Treat a
   `Disallow` prefix as binding even when the endpoint answers 200 and even when the API behind it is a
   paid product — use the site's public page instead. If a source needs authentication you do not have,
   mark it dead and say so — no cookie escalation.
4. **Do not delete or rotate the state file casually** — it *is* the "already told you" memory; a
   lost state means a re-send of everything.
5. **Cron runs cannot create cron jobs** (Hermes disables cron management inside a run) — a job can
   never spawn its own follow-ups.
6. **A weekly source (promo flyers, catalogs) needs its own cadence** — and a text-hash diff, not a "last
   modified" header: pages that republish unchanged content re-trigger a digest with nothing new to say.

## 6. Reference

- `references/feed-sources.md` — recon recipe, per-source-class access routes, failure-mode guardrails, verified per-site notes (trendshift, Reddit).
