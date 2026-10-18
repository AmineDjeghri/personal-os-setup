---
name: github-repo-management
description: "Clone/create/fork repos; manage remotes, releases; detect and add missing community health files (SECURITY.md, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT)."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [GitHub, Repositories, Git, Releases, Secrets, Configuration, SECURITY, LICENSE, CONTRIBUTING]
    related_skills: [github-auth, github-pr-workflow, github-issues]
---

# GitHub Repository Management

Create, clone, fork, configure, and manage GitHub repositories.

No `gh`? Install it (see `github-auth`) — fallback: `github-auth/references/rest-api-fallback.md`.

`gh` authenticated with GitHub (see the `github-auth` skill); `$GH_USER` below comes from `gh api user --jq .login`.

---

## 1. Cloning Repositories

```bash
gh repo clone owner/repo-name
gh repo clone owner/repo-name -- --depth 1
```

## 2. Creating Repositories

```bash
# Create a public repo and clone it
gh repo create my-new-project --public --clone

# From existing local directory
cd /path/to/existing/project
gh repo create my-project --source . --public --push
```

### From a Template

```bash
gh repo create my-new-app --template owner/template-repo --public --clone
```

## 3. Forking Repositories

```bash
gh repo fork owner/repo-name --clone
```

### Keeping a Fork in Sync

```bash
gh repo sync $GH_USER/repo-name
```

## 4. Repository Information and Settings

```bash
gh repo edit --enable-auto-merge   # for the rest: gh repo view|list|edit --help
```

## 5. Branch Protection

REST-only operation — the `PUT` body is in `github-auth/references/rest-api-fallback.md`.

## 6. Secrets Management (GitHub Actions)

```bash
gh secret set API_KEY --body "your-secret-value"
gh secret set SSH_KEY < ~/.ssh/id_rsa
gh secret list
gh secret delete API_KEY
```

Note: For secrets, `gh secret set` is dramatically simpler. If setting secrets is needed and `gh` isn't available, recommend installing it for just that operation.

## 7. Releases

```bash
gh release create v1.0.0 --title "v1.0.0" --generate-notes   # others: gh release --help
```

## 8. GitHub Actions Workflows

```bash
gh run view <RUN_ID> --log-failed
gh workflow run ci.yml --ref main   # others: gh run|workflow --help
```

## 9. Community health files (SECURITY.md, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, FUNDING)

Use when the user asks about "missing files", SECURITY.md, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, "standard GitHub
files", or wants the repo to pass GitHub's community-profile check. Detect with GitHub's own API — do NOT guess:

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

### Files to add for a public repo

| File | Content |
|---|---|
| `SECURITY.md` | Private vuln reporting (GitHub security advisories; add a dedicated public email only if the user supplies one), supported versions, no-public-disclosure policy, 48h response SLA. |
| `LICENSE` | MIT is the common OSS default; Apache-2.0 if preferred. |
| `CONTRIBUTING.md` | Dev setup, bug/feature reporting, branch/PR workflow, commit conventions, release process. |
| `CODE_OF_CONDUCT.md` | Contributor Covenant v2.1 (GitHub standard). |
| `.github/FUNDING.yml` | GitHub Sponsors / Ko-fi placeholder comments for user to fill. |

Tailor the repo-specific bits (maintainer email, repo URL, commit conventions,
release tooling) to the actual project — read README / repository.yaml / CI first.

- **Privacy rule: NEVER put a personal email in any public repo file or commit metadata** — contact = GitHub private
  vulnerability reporting; commit as `<id>+<login>@users.noreply.github.com` (from `gh api user`).
- Template content: `references/community-health-files.md`. Pitfalls (matching another repo's templates, removing a
  leaked email from a pushed PR, FUNDING.yml, monorepos, issue-template health check, consent-gated git ops):
  `references/community-health-pitfalls.md`.
