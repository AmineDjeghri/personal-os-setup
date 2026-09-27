---
name: github-code-review
description: "Review PRs: diffs, inline comments via gh or REST."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Code-Review, Pull-Requests, Git, Quality]
    related_skills: [github-auth, github-pr-workflow]
---

# GitHub Code Review

Review local changes before pushing, or review open PRs on GitHub. Plain `git` covers local work;
`gh` covers PR-level interactions — without it, use the REST fallbacks in
`references/rest-api-fallback.md`.

## Prerequisites

- Authenticated with GitHub (see `github-auth` skill)
- Inside a git repository

```bash
OWNER_REPO=$(git remote get-url origin | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1); REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
```

---

## 1. Reviewing Local Changes (Pre-Push)

Pure `git` — works everywhere, no API needed.

### Review Strategy

1. **Scope first:** `git diff main...HEAD --stat` and `git log main..HEAD --oneline`.
2. **File by file:** `read_file` for context, `git diff main...HEAD -- <path>` for one file, `git diff main...HEAD --name-only` to list files, `git diff --staged` for staged-only work.
3. **Check the diff for common issues:**

```bash
git diff main...HEAD | grep -n "print(\|console\.log\|TODO\|FIXME\|HACK\|XXX\|debugger"
git diff main...HEAD --stat | sort -t'|' -k2 -rn | head -10   # large files accidentally staged
git diff main...HEAD | grep -in "password\|secret\|api_key\|token.*=\|private_key"
git diff main...HEAD | grep -n "<<<<<<\|>>>>>>\|======="      # merge conflict markers
```

4. **Present structured feedback** in the format below.

### Review Output Format

When reviewing local changes, present findings in this structure:

```
## Code Review Summary

### Critical
- **src/auth.py:45** — SQL injection: user input passed directly to query.
  Suggestion: Use parameterized queries.

### Warnings
- **src/models/user.py:23** — Password stored in plaintext. Use bcrypt or argon2.
- **src/api/routes.py:112** — No rate limiting on login endpoint.

### Suggestions
- **src/utils/helpers.py:8** — Duplicates logic in `src/core/utils.py:34`. Consolidate.
- **tests/test_auth.py** — Missing edge case: expired token test.

### Looks Good
- Clean separation of concerns in the middleware layer
- Good test coverage for the happy path
```

---

## 2. Reviewing a Pull Request on GitHub

No `gh`? Install it (see `github-auth`) — genuine fallback: `references/rest-api-fallback.md`.

### View PR Details

```bash
gh pr view 123
gh pr diff 123
gh pr diff 123 --name-only
```

### Check Out PR Locally for Full Review

```bash
git fetch origin pull/123/head:pr-123
git checkout pr-123
# shortcut: gh pr checkout 123; then read_file, search_files, run the tests
git diff main...pr-123
```

### Comment, Inline Comment, and Formal Review

```bash
gh pr comment 123 --body "Overall looks good, a few suggestions below."
```

```bash
HEAD_SHA=$(gh pr view 123 --json headRefOid --jq '.headRefOid')

gh api repos/$OWNER/$REPO/pulls/123/comments \
  --method POST \
  -f body="This could be simplified with a list comprehension." \
  -f path="src/auth/login.py" \
  -f commit_id="$HEAD_SHA" \
  -f line=45 \
  -f side="RIGHT"
```

```bash
gh pr review 123 --approve --body "LGTM!"
gh pr review 123 --request-changes --body "See inline comments."
gh pr review 123 --comment --body "Some suggestions, nothing blocking."
```

REST review event values: `"APPROVE"`, `"REQUEST_CHANGES"`, `"COMMENT"`. The `line` field refers to the line number in the *new* version of the file; for deleted lines use `"side": "LEFT"`.

---

## 3. Review Checklist

When performing a code review (local or PR), systematically check:

### Correctness
- Does the code do what it claims?
- Edge cases handled (empty inputs, nulls, large data, concurrent access)?
- Error paths handled gracefully?

### Security
- No hardcoded secrets, credentials, or API keys
- Input validation on user-facing inputs
- No SQL injection, XSS, or path traversal
- Auth/authz checks where needed

### Code Quality
- Clear naming (variables, functions, classes)
- No unnecessary complexity or premature abstraction
- DRY — no duplicated logic that should be extracted
- Functions are focused (single responsibility)

### Testing
- New code paths tested?
- Happy path and error cases covered?
- Tests readable and maintainable?

### Performance
- No N+1 queries or unnecessary loops
- Appropriate caching where beneficial
- No blocking operations in async code paths

### Documentation
- Public APIs documented
- Non-obvious logic has comments explaining "why"
- README updated if behavior changed

---

## 4. Pre-Push Review Workflow

When the user asks you to "review the code" or "check before pushing": run `git diff main...HEAD --stat`
then `git diff main...HEAD`, `read_file` the changed files, apply the section 3 checklist, and present
findings in the section 1 output format.

---

## 5. PR Review Workflow (End-to-End)

When the user asks you to "review PR #N", "look at this PR", or gives you a PR URL:

1. Set up the environment — see **Prerequisites** above.
2. Gather PR context (description, changed files) — **section 2, View PR Details**.
3. Check the PR out locally and read the diff — **section 2, Check Out PR Locally**.
4. Run the project's tests and linter on the branch, if it has any.
5. Apply the **section 3 checklist** to every changed file.
6. Post the review via the comment and review commands in **section 2** — inline comments plus an approve / request-changes / comment verdict.

### Decision: Approve vs Request Changes vs Comment

- **Approve** — no critical or warning-level issues, only minor suggestions or all clear
- **Request Changes** — any critical or warning-level issue that should be fixed before merge
- **Comment** — observations and suggestions, but nothing blocking (use when you're unsure or the PR is a draft)
