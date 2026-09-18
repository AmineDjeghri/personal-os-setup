# Sanitizing a skill before publishing it into a public repo

The shared / Track-1 dir is backed by a PUBLIC repository, so a promoted file is published the moment it is pushed.
The shared-dir rule already forbids personal identifiers; this is the procedure that makes a failing skill
publishable instead of dropping it.

## Placeholder mapping (keep one convention everywhere)

| Real value — never publish | Placeholder |
|---|---|
| personal email (`*.gmail.com`, private addresses) | `user@example.com` |
| the user's own domain or contact address | `contact@example.com` |
| the user's real name inside a command example | `Your Name` |
| numeric GitHub noreply id (`<id>+<login>@users.noreply.github.com`) | `12345678+your-username@users.noreply.github.com` |
| bare login in an email example | `your-username@users.noreply.github.com` |
| add-on slug, host paths, LAN/global IPs, MACs, SSIDs, tunnel hostnames, live exposure findings | `<repo>_<slug>`, `<host>`, `172.30.32.x`, `<device>` |

Use `example.com` for every domain — a domain the user actually owns is itself an identifier.

## Scan before copying, scan again after sanitizing

```bash
grep -rn "RealName\|real-login\|<personal-email>\|<numeric-id>\|@gmail\|<their-domain>" dot_claude/skills/<skill>
```

Run it over the whole folder: `references/` and `templates/` are where identifiers hide (worked examples, condensed
case studies, commit-author snippets), not the frontmatter. Zero matches is the acceptance test.

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
