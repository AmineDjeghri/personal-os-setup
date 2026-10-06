# Community Health File Templates

Ready-to-paste content for the five standard GitHub files; replace the `<angle brackets>` placeholders.

## SECURITY.md

```markdown
# Security Policy

## Reporting a Vulnerability

We take security issues seriously and appreciate responsible disclosure.
**Please do NOT open a public issue or pull request for security vulnerabilities.**

Report privately via **GitHub private vulnerability reporting** (never a personal email):
- https://github.com/<OWNER>/<REPO>/security/advisories/new

Optionally add a **dedicated public contact email** the user supplies (e.g. `contact@<domain>.com`).

Include: description + impact, affected add-on(s)/version(s), reproduction steps,
suggested remediation (if known). Expect a response within **48 hours**.

## Supported Versions
Security updates are only provided for the latest released version.

## Disclosure Policy
- Acknowledgment within 48h; investigate, fix in a future release, and credit you if
  you wish. Do not publicly disclose until a fix is published.
```

## LICENSE (MIT)

MIT: `gh api licenses/mit --jq .body` (fill `<YEAR> <AUTHOR NAME>`) or https://choosealicense.com/licenses/mit/

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
github: # your-sponsors-username
```
