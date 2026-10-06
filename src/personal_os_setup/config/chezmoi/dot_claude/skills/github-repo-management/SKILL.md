---
name: github-repo-management
description: "Clone/create/fork repos; manage remotes, releases."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [GitHub, Repositories, Git, Releases, Secrets, Configuration]
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
