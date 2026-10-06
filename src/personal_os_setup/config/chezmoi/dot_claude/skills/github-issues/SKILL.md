---
name: github-issues
description: "Create, triage, label, assign GitHub issues via gh or REST."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [GitHub, Issues, Project-Management, Bug-Tracking, Triage]
    related_skills: [github-auth, github-pr-workflow]
---

# GitHub Issues Management

Create, search, triage, and manage GitHub issues with `gh`. No `gh`? Install it (see `github-auth`) — fallback: `github-auth/references/rest-api-fallback.md`.

Needs `gh` auth (`github-auth`) inside a repo with a GitHub remote.

## 1. Viewing Issues

```bash
gh issue list
gh issue list --state open --label "bug"
gh issue list --assignee @me
gh issue list --search "authentication error" --state all
gh issue view 42
```

## 2. Creating Issues

```bash
gh issue create --title "Login redirect ignores ?next= parameter" --body "After login users always land on /dashboard; expected /settings (the ?next= target)." --label "bug,backend" --assignee "username"
```

## 3. Managing Issues

```bash
gh issue edit 42 --add-label "priority:high,bug"       # labels: --add-label / --remove-label
gh issue edit 42 --add-assignee @me                    # assignment
gh issue comment 42 --body "Investigated — root cause is in auth middleware."   # commenting
gh issue close 42 --reason "not planned"               # closing; reopen: gh issue reopen 42
```

### Linking Issues to PRs

Issues are automatically closed when a PR merges with the right keywords in the body: `Closes #42`, `Fixes #42`, `Resolves #42`.

To create a branch from an issue:

```bash
gh issue develop 42 --checkout
```

## 4. Issue Triage Workflow

List untriaged issues: `gh issue list --label "needs-triage" --state open`

## 5. Bulk Operations

For batch operations, combine API calls with shell scripting:

```bash
# Close all issues with a specific label
gh issue list --label "wontfix" --json number --jq '.[].number' | \
  xargs -I {} gh issue close {} --reason "not planned"
```
