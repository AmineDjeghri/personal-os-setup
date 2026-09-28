# Sanitizing a skill before publishing it into a public repo

The shared / Track-1 dir is backed by a PUBLIC repository, so a promoted file is published the moment it is pushed.
The shared-dir rule already forbids personal identifiers; this is the procedure that makes a failing skill
publishable instead of dropping it.

## Scan for

- identity: the owner's first/last name, handle, numeric GitHub ID, any bare personal email
- machine identifiers (the ones a box skill actually accumulates):
  `/addon_configs/<6+ hex>`, `<hex8>_<addon>`, `app_<hex8>_<addon>`, private LAN IPs, the host/SSH username
- secret-shaped assignments: `token|api_key|secret|password|bearer` followed by a long literal
- long digit runs (10+) that could be a chat/user id

## Placeholder mapping (keep one convention everywhere)

| Real value — never publish | Placeholder |
|---|---|
| personal email (`*.gmail.com`, private addresses) | `user@example.com` |
| the user's own domain or contact address | `contact@example.com` |
| the user's real name inside a command example, or in prose/a handle | `Your Name`, the generic voice ("the user", "the repo owner") |
| `git config user.name "<real name>"` | `"<your name>"` |
| numeric GitHub noreply id (`<id>+<login>@users.noreply.github.com`) | `12345678+your-username@users.noreply.github.com` |
| bare login in an email example | `your-username@users.noreply.github.com` |
| a phantom/stranger address quoted as a cautionary example | `someone@users.noreply.github.com`, "a stranger's GitHub account" |
| add-on slug, host paths, LAN/global IPs, MACs, SSIDs, tunnel hostnames, live exposure findings | `<repo>_<slug>`, `<host>`, `172.30.32.x`, `<device>` |
| `/addon_configs/<hex>_<slug>` / `<hex8>_<addon>` / `app_<hex8>_<addon>` | `/addon_configs/<hash>_<addon>` / `<hash>_<addon>` / `app_<hash>_<addon>` |
| host username in a shell example | "the host user" |
| owner's own repo URL used as a self-reference | the bare repo name |

Use `example.com` for every domain — a domain the user actually owns is itself an identifier.

## What stays

- public third-party repo/documentation URLs — they are references, not PII
- `example.com`, `user@example.com`, `<repo>_<slug>`-style placeholders already in the text
- the HA default mDNS host in an SSH example (`root@<ha-host>`) and HA's own default names
- version numerals that merely look like IPs (`x.y.z.w` in prose about version comparison)

## Scan before copying, scan again after sanitizing

```bash
grep -rn "RealName\|real-login\|<personal-email>\|<numeric-id>\|@gmail\|<their-domain>" dot_claude/skills/<skill>
```

Run it over the whole folder: `references/` and `templates/` are where identifiers hide (worked examples, condensed
case studies, commit-author snippets), not the frontmatter. Zero matches is the acceptance test. Scan the STAGED
copy after the pass and report how many hits remain — the count is the evidence, an adjective is not.

## Rules that keep the change reviewable

- **Sanitize the REPO copy only.** The copy in `~/.hermes/skills/` is private and keeps the real values so the agent
  still recognises them in conversation; do not "fix" it to match.
- **Change values, not prose.** Replace the identifier, keep the sentence, heading and rule's substance — a sanitized
  skill that reads differently is a rewrite nobody signed off on.
- **Make user-specific wording agent-agnostic**: `Privacy (this user, non-negotiable)` → `Privacy rule`. A shared
  skill must not read as if it were written about one person.
- **Prove it with a diff, not a claim**: `diff -r ~/.hermes/skills/<category>/<skill> dot_claude/skills/<skill>` must
  show ONLY the substitutions; anything else in the diff is an unintended edit.
- A skill that is nothing but the user's own live findings (network topology, presence forensics, deployment
  internals) loses its value when sanitized — leave it in the own store and say why, instead of gutting it to make a
  promotion list look complete.
- **The skill's own scan recipe is the usual false positive.** Reword a rule that describes this check to name the
  CHECK ("the owner's name, handle, numeric ID, a personal email domain") instead of embedding the literal tokens,
  or every future scan reports a hit on the instructions themselves.
- **Genericize personal profile paths in examples** (`C:\Users\<user>`, `/home/<user>/…`) even when a rule says they
  are "documentation, not PII" — the repo is public and the same gate greps them.
- **Keep the recipe version that produced the clean scan with the report**, so the next port repeats the same scan.
