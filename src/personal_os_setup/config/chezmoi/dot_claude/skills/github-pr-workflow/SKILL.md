---
name: github-pr-workflow
description: "GitHub issues and PR lifecycle: file/triage issues, carry an issue to a verified PR, branch, commit, open, CI, merge."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [GitHub, Issues, Pull-Requests, CI/CD, Git, Automation, Merge]
    related_skills: [github-auth, github-code-review, systematic-debugging, test-driven-development, requesting-code-review]
---

# GitHub issues → pull requests (lifecycle)

Issue → branch → commits → PR → CI → merge with the `gh` CLI. No `gh`? Install it (see `github-auth`) —
fallback: `github-auth/references/rest-api-fallback.md`. Needs `gh` auth inside a git repo with a GitHub remote.
Reviewing someone else's PR, or answering a code question with no requested change: not this skill
(`github-code-review`).

## 1. Issues

```bash
gh issue list --state open --label "bug"            # also: --assignee @me, --search "auth error" --state all
gh issue list --label "needs-triage" --state open   # untriaged
gh issue view 42 --comments
gh issue create --title "Login redirect ignores ?next=" --body "After login users land on /dashboard; expected /settings." --label "bug,backend" --assignee "username"
gh issue edit 42 --add-label "priority:high,bug"    # --remove-label; --add-assignee @me
gh issue comment 42 --body "Root cause is in auth middleware."
gh issue close 42 --reason "not planned"            # reopen: gh issue reopen 42
gh issue develop 42 --checkout                      # branch from an issue
gh issue list --label "wontfix" --json number --jq '.[].number' | xargs -I {} gh issue close {} --reason "not planned"   # bulk
```

`Closes #42` / `Fixes #42` / `Resolves #42` in the PR body closes the issue on merge.

## 2. Carrying an issue to a verified PR

End-to-end discipline — premise validation, duplicate sweeps, class-level fixes, honest CI reporting. Each step
ends with a "done when".

1. **Read the live issue — body AND full thread** (`gh issue view <N> --comments`). The body is a filing-time snapshot; the newest comments carry partial fixes already merged, new root causes, maintainer decisions, or questions aimed at you. Also read `AGENTS.md`/contribution docs. Done when requested behavior, non-goals and unanswered thread questions are known.
2. **Sweep for existing and duplicate work.** `gh pr list --search "#<N>" --state all` plus at least two keyword/synonym variants (`gh pr list --search "<subsystem> <symptom>" --state open`), and `git log --oneline -20 -- <relevant files>` for a recent fix. Done when every open PR/recent commit touching it is known, or none exist.
3. **Validate the premise against current code — and design intent.** Reproduce on the current default branch with a failing test/fixture and trace the reported path. Then ask whether the "bug" is deliberate: `git log -p -S "<symbol>"` and read the original commit's intent — a missing link or restriction is often the feature. Challenge stale or flawed issue prose instead of implementing it blindly.
4. **Define acceptance and risk**: criteria, interfaces, migrations/state, compatibility, security/privacy, rollout, rollback; map every criterion to a test or explicit verification. Done when review has a finite contract.
5. **Implement the smallest complete change — and fix the class.** Isolated branch or worktree; regression tests first (load `systematic-debugging` / `test-driven-development` when the bug class calls for them). Then search sibling call sites for the same bug shape and fix the whole class in this PR — an incomplete fix leaving known siblings broken is worse than none. Every changed line traces to the issue; no drive-by cleanup. Done when targeted tests pass, the original failure no longer reproduces, and siblings are fixed or ruled out.
6. **Prove the regression test bites (sabotage run).** Temporarily restore the old behavior of the function under test, confirm the new test FAILS, restore the fix, confirm it passes. A test that passes with and without the fix proves nothing.
7. **Run the repo's gates, then open the PR immediately.** Formatter, lint, typecheck, canonical test entrypoint on affected areas; `requesting-code-review` on the diff. Push and open the PR right away (CI latency is the long pole) — **once the user has approved the push and the PR** (a yes to the task is not a yes to push; never bundle `commit && push`). Body: problem, approach, tests, risk, exclusions, issue link. Read the PR back: head SHA, base, title, files. Done when the PR exists with the intended diff and CI is running.
8. **Shepherd CI honestly and close the loop.** Inspect live checks and failure logs (§5). Separate failures your diff introduced from baseline/infra failures — reproduce on the default branch when unsure, rerun once only for genuine infra flakes. Never say "green", "merged" or "released" without live evidence of that exact state. When the PR lands, comment on the issue with the PR link and a one-line explanation.

Checklist: full thread read · duplicate sweep (issue number + 2 variants) · premise reproduced + design intent checked ·
test fails without the fix · siblings fixed or ruled out · every line traces to the issue · CI state from live evidence only.

## 3. Branch and commits

```bash
git fetch origin && git checkout main && git pull origin main
git checkout -b feat/add-user-authentication
git add src/auth.py tests/test_auth.py          # stage specific files
git commit -m "feat: add JWT-based user authentication"
```

Branch prefixes: `feat/` · `fix/` · `refactor/` · `docs/` · `ci/`. Conventional Commits (`type(scope): short
description`, body wrapped at 72); types `feat fix refactor docs test ci chore perf`; `!` or a `BREAKING CHANGE:`
footer for majors. Mandatory pre-push checklist: `coding-workflow` § 5 (line endings: `git-line-endings`).

## 4. Push and open the PR

```bash
git push -u origin HEAD
gh pr create --title "feat: add JWT-based user authentication" --body "## Summary
- Adds login and register API endpoints

## Test Plan
- [ ] Unit tests pass

Closes #42"
```

Follow-up commits: confirm where the open PR's branch is checked out first (`gh pr list --state open`, `git worktree list`) — never push leftover commits of a branch whose PR is already merged.

## 5. CI status and auto-fixing failures

```bash
gh pr checks [--watch]                                          # one-shot / poll until done
gh run list --branch $(git branch --show-current) --limit 5     # recent runs on this branch
gh run view <RUN_ID> --log-failed
```

Loop: check CI → read failure logs → fix → **ask for approval to commit, and separately to push** (never fold `git add`/`commit`/`push` into one command) → re-check. After 3 failed attempts, stop and ask. Facts worth checking:
- a missing `permissions:` block, or secrets fork PRs never get (by design) — needs the user;
- a hung job → add `timeout-minutes:` to the step;
- `ModuleNotFoundError` in CI = a dependency missing in CI; compare local vs CI Python/Node version;
- triggers firing wrong or not at all → `github-actions-trigger-gotchas`.

## 6. Merging

Needs the user's per-action approval.

```bash
gh pr merge --squash --delete-branch           # cleanest for feature branches
gh pr merge --auto --squash --delete-branch    # merges when all checks pass
```
