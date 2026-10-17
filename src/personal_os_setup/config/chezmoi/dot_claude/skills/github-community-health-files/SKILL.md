---
name: github-community-health-files
description: "Detect missing GitHub community/health files (SECURITY.md, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, FUNDING) and generate them."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [GitHub, SECURITY, LICENSE, CONTRIBUTING, Repository, Health]
    related_skills: [github-repo-management, github-pr-workflow, github-auth]
---

# GitHub Community Health Files

Detect which GitHub community/health files a repo is missing, then generate them from the templates.

## Trigger conditions

- User asks about "missing files", "SECURITY.md", "LICENSE", "CONTRIBUTING",
  "CODE_OF_CONDUCT", or "standard GitHub files" for a repo.
- User wants the repo to look professional / pass GitHub's community-profile check.

## 1. Detect missing files (authoritative)

Use GitHub's own community-profile API — do NOT guess:

```bash
# Missing files (value == null)
gh api repos/$OWNER/$REPO/community/profile \
  --jq '.files | to_entries | map(select(.value == null)) | map(.key)'
# Present files
gh api repos/$OWNER/$REPO/community/profile \
  --jq '.files | to_entries | map(select(.value != null)) | .[].key'
```

The `.files` keys are: `code_of_conduct`, `code_of_conduct_file`, `contributing`,
`issue_template`, `license`, `pull_request_template`, `readme`.

Always also list the repo root to confirm (some files like `SECURITY.md` and
`.github/FUNDING.yml` are not all in the community-profile `.files` set):

```bash
gh api repos/$OWNER/$REPO/contents --jq '.[] | .name'
gh api repos/$OWNER/$REPO/contents/.github --jq '.[] | .name'
```

## 2. Files to add for a public repo

| File | Content |
|---|---|
| `SECURITY.md` | Private vuln reporting (GitHub security advisories; add a dedicated public email only if the user supplies one), supported versions, no-public-disclosure policy, 48h response SLA. |
| `LICENSE` | MIT is the common OSS default; Apache-2.0 if preferred. |
| `CONTRIBUTING.md` | Dev setup, bug/feature reporting, branch/PR workflow, commit conventions, release process. |
| `CODE_OF_CONDUCT.md` | Contributor Covenant v2.1 (GitHub standard). |
| `.github/FUNDING.yml` | GitHub Sponsors / Ko-fi placeholder comments for user to fill. |

Tailor the repo-specific bits (maintainer email, repo URL, commit conventions,
release tooling) to the actual project — read README / repository.yaml / CI first.

## 3. Pitfalls

- **Privacy rule: NEVER put a personal email in any public repo file or commit metadata.** Contact = GitHub private
  vulnerability reporting, plus a dedicated public email only if the user supplies one; commit as
  `<id>+<login>@users.noreply.github.com` (id/login from `gh api user`). If one leaked, removing it is urgent.
  ```bash
  git config user.name "Your Name"
  git config user.email "12345678+your-username@users.noreply.github.com"
  ```
- **"Match another repo's templates" = adapt, don't verbatim-copy.** The other repo's CONTRIBUTING often references tooling the target lacks
  (make/uv/pyproject.toml, a `dev` branch, gh-pages docs); adapt to the target's actual stack, same structure. The LICENSE can be copied.
- **Removing an email trace from a pushed PR.** Contents AND commit author carry it:
  - `gh pr close <N> --delete-branch` (no commit reaches the remote)
  - verify PR body, issue comments (`/issues/<N>/comments`), review comments (`/pulls/<N>/comments`), the diff (`gh pr diff`) and the commit `%ae`
  - re-branch from `main` so only one clean commit ships — the branch switch removed the working-tree files, so re-create them on the new branch
- **FUNDING.yml is optional** — offer, don't bundle; the user has declined it before.
- **Monorepo / multi-add-on repo → lean umbrella CONTRIBUTING, not a tooling dump.** The root CONTRIBUTING defers to a sub-project's own guide
  and documents only repo-wide tooling; inspect `git ls-tree -r --name-only HEAD | grep <subdir>` first.
- **A `gh-pages` branch is not proof of a live site** — say "may be published", never "is deployed".
- **Issue templates don't fully clear the health check.** Having only YAML forms in
  `.github/ISSUE_TEMPLATE/` (no legacy `ISSUE_TEMPLATE.md` and no `config.yml` chooser)
  still flags `issue_template` as missing. Add a `config.yml` or the legacy file if
  the user wants it green. Minor — the YAML forms still work.
- **Destructive git ops are consent-gated** (`git reset --hard`, `git clean -fd`, `rm -rf` time out with no response) — don't reset a stale clone; clone fresh and set the identity before committing:
  ```bash
  D="repo-$$"; gh repo clone owner/repo "$D"; cd "$D"
  git config user.name "..."; git config user.email "..."
  ```

## Support files

- `references/community-health-files.md` — ready-to-paste template content for all
  five files (SECURITY.md, MIT LICENSE, CONTRIBUTING.md, CODE_OF_CONDUCT.md, FUNDING.yml).
