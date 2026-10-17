---
name: github-code-review
description: "Review PRs: diffs, inline comments via gh or REST."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [GitHub, Code-Review, Pull-Requests, Git, Quality]
    related_skills: [github-auth, github-pr-workflow]
---

# GitHub Code Review

Plain `git` for local review; `gh` for PRs. No `gh`? Install it (see `github-auth`) — fallback: `github-auth/references/rest-api-fallback.md`.

## Prerequisites

```bash
OWNER_REPO=$(git remote get-url origin | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1); REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
```

---

## 1. Reviewing Local Changes (Pre-Push)

Pure `git` — works everywhere, no API needed.

### Review Strategy

1. **Scope first:** `git diff main...HEAD --stat` and `git log main..HEAD --oneline`.
2. **File by file:** read the changed files for context, `git diff main...HEAD -- <path>` for one file, `git diff main...HEAD --name-only` to list files, `git diff --staged` for staged-only work.
3. **Check the diff for common issues:**

```bash
git diff main...HEAD | grep -n "print(\|console\.log\|TODO\|FIXME\|HACK\|XXX\|debugger"
git diff main...HEAD --stat | sort -t'|' -k2 -rn | head -10   # large files accidentally staged
git diff main...HEAD | grep -in "password\|secret\|api_key\|token.*=\|private_key"
git diff main...HEAD | grep -n "<<<<<<\|>>>>>>\|======="      # merge conflict markers
```

4. **Present structured feedback** in the format owned by `references/review-output-template.md` (output format, severity guide, verdict rule).

---

## 2. Reviewing a Pull Request on GitHub

### View PR Details

```bash
gh pr view 123
gh pr diff 123
gh pr diff 123 --name-only
```

### Check Out PR Locally for Full Review

```bash
gh pr checkout 123   # then read the changed files, run the tests
git diff main...HEAD
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

## 4. PR Review Workflow

PR review: §2 to gather/check out, run tests/lint, apply the §3 checklist, then post inline comments + a verdict (format and verdict rule: `references/review-output-template.md`).
