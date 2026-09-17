# Community Health File Templates

Ready-to-paste content for the five standard GitHub files. Replace the placeholders
in `<angle brackets>` with the repo URL and project conventions.

> **Privacy rule: NEVER put the *personal* email
> (user@example.com) in any public repo file or commit metadata.** Default
> contact = GitHub private vulnerability reporting. A **dedicated public email** the
> user explicitly provides (e.g. `contact@example.com`) IS fine to include in
> SECURITY.md. Set the commit author to the GitHub noreply email
> (`<numeric-id>+<username>@users.noreply.github.com`), never the personal email.
>
> **FUNDING.yml is optional** — this user declined it. Offer, don't bundle.
>
> **Monorepo CONTRIBUTING:** in a multi-add-on repo where a sub-project (e.g.
> `addons/personal-app`) has its own Makefile/uv/pre-commit/CONTRIBUTING.md, make the
> root CONTRIBUTING a lean umbrella that defers to it; only document repo-wide tooling.
> gh-pages branch existing ≠ live site — phrase as "may be published in the future."

## SECURITY.md

```markdown
# Security Policy

## Reporting a Vulnerability

We take security issues seriously and appreciate responsible disclosure.
**Please do NOT open a public issue or pull request for security vulnerabilities.**

Report privately via **GitHub private vulnerability reporting** (do NOT include a
personal email):
- https://github.com/<OWNER>/<REPO>/security/advisories/new

Optionally add a **dedicated public contact email** the user supplies (e.g.
`contact@<domain>.com`) — never the personal Gmail.

Include: description + impact, affected add-on(s)/version(s), reproduction steps,
suggested remediation (if known). Expect a response within **48 hours**.

## Supported Versions
Security updates are only provided for the latest released version.

## Disclosure Policy
- Acknowledgment within 48h; investigate, fix in a future release, and credit you if
  you wish. Do not publicly disclose until a fix is published.

## Security Best Practices
Keep software up to date; do not expose admin interfaces directly to the internet
without a reverse proxy + auth; use strong unique passwords / 2FA.
```

## LICENSE (MIT)

```markdown
MIT License

Copyright (c) <YEAR> <AUTHOR NAME>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## CONTRIBUTING.md (adapt to project)

Sections to include: Code of Conduct link; Development setup (fork, clone, install
pre-commit, layout of addons/); Reporting bugs (search first, use bug template,
include version/logs); Requesting features (use feature template, explain use case);
Submitting changes (branch from main, focused commits, run `pre-commit run --all-files`,
open PR against main, keep description 1–2 lines); Commit conventions (Conventional
Commits / commitizen if the project uses it); Branch strategy; Release process
(python-semantic-release etc.); Style guide (shellcheck / set -euo pipefail for bash,
HA add-on YAML conventions).

## CODE_OF_CONDUCT.md

Use the **Contributor Covenant v2.1** text verbatim:
https://www.contributor-covenant.org/version/2/1/code_of_conduct.html
Set the enforcement contact to **GitHub private vulnerability reporting** (see
SECURITY.md) — NOT a personal email. Standard sections: Our Pledge, Our Standards,
Enforcement Responsibilities, Scope, Enforcement, Attribution.

## .github/FUNDING.yml (OPTIONAL — this user declines it)

```yaml
# Supported funding model platforms
github: # Replace with up to 4 GitHub Sponsors usernames, e.g. [user1, user2]
patreon: # Replace with a single Patreon username
open_collective: # Replace with a single Open Collective username
ko_fi: # Replace with a single Ko-fi username
tidelift: # Replace with a single Tidelift platform-name/package-name, e.g. npm/babel
community_bridge: # Replace with a single Community Bridge project-name, e.g. cloud-foundry
liberapay: # Replace with a single Liberapay username
issuehunt: # Replace with a single IssueHunt username
otechie: # Replace with a single Otechie username
lfx_crowdfunding: # Replace with a single LFX Crowdfunding project-name, e.g. cloud-foundry
custom: # Replace with up to 4 custom sponsorship URLs, e.g. ['link1', 'link2']
```

## Note: issue template health-check gap

YAML forms in `.github/ISSUE_TEMPLATE/` alone leave `issue_template` flagged as
missing. Add a `.github/ISSUE_TEMPLATE/config.yml` (chooser) or legacy
`ISSUE_TEMPLATE.md` to fully clear it.
