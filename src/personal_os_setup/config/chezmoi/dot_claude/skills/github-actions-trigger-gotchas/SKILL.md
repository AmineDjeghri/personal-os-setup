---
name: github-actions-trigger-gotchas
description: Use when GitHub Actions triggers fire wrong or not at all.
---

# GitHub Actions trigger & scheduling gotchas

False runs on Renovate/branch pushes, duplicated checks, jobs cancelled by concurrency, or a step that silently
never executes. Diagnose with real evidence before editing YAML:

```bash
gh run list --branch <branch> --limit 20 --json workflowName,event,headBranch,createdAt,conclusion
gh api repos/O/R/actions/runs/<run-id>/jobs --jq '.jobs[]|"\(.name) \(.conclusion)"'
gh api repos/O/R/actions/runs/<run-id>/jobs --jq '.jobs[]|select(.name|test("X"))|.steps[]|"\(.number) \(.name) -> \(.conclusion)"'
gh pr checks <n>          # duplicate identical check names = two runs (push + pull_request)
gh api repos/O/R/branches/main/protection ; gh api repos/O/R/rulesets   # what actually gates merges
```

## 1. `push` + `paths` fires for unrelated diffs after a force-push

On a rebase/force-push (Renovate does this), GitHub evaluates the push path filter against everything the branch
*gained* relative to its previous tip — including files `main` picked up since the branch was created. Symptom: an
add-on CI fires on a `renovate/*` push whose PR only touches one unrelated folder; correlation is exact (only the
folders added to `main` after the branch was cut fire).

**Fix:** scope the push trigger to the branch that matters (`push: branches: [main]`), keep validation on
`pull_request` (whose `paths` uses the PR diff, correctly). Do not add `paths-ignore` hacks.

Same pattern causes **double CI on every PR** (`push` + `pull_request` both match). Pick one trigger — usually drop
`push` unless a push without a PR must be validated. Check first whether protection/rulesets require those checks
(often none).

## 2. Job-level `concurrency` cancels a run's OWN sibling jobs

`jobs.<id>.concurrency` with the default queue holds **one running + one pending** per group: each newly queued job
**cancels the pending one** (`cancel-in-progress: false` only protects the *running* job). With N jobs starting
together (cron, fan-out), all but ~2 get cancelled every run — worse than the race you were fixing.
`queue: max` (up to 100 pending) fixes it, but an unsupported key invalidates the whole workflow file (all runs stop),
so for a critical job prefer mechanisms with no new syntax.

**Preferred fix for parallel jobs pushing to the same ref:** a `needs:` chain + `if: always()` (deterministic
ordering, a failure in one job doesn't skip the rest), plus a bounded rebase/push retry:

```bash
pushed=0
for attempt in 1 2 3 4 5; do
  if git pull --rebase --autostash origin main && git push; then pushed=1; break; fi
  echo "push attempt ${attempt} rejected (main moved?) - retrying"; sleep 5
done
[ "$pushed" = 1 ] || { echo "::error::could not push"; exit 1; }
```

The retry is the load-bearing part: it also covers cross-workflow races (another workflow or a human merging into
the same branch), which a concurrency group scoped to one workflow never covers. A single `git push` with no retry
in a scheduled job loses its commit silently-but-redly ("cannot lock ref 'refs/heads/main': is at X but expected Y").

## 3. A step gated on a step id that does not exist never runs

`if: steps.changed.outputs.changed == 'true'` where the producing step has **no `id: changed`** (or the id is
misspelled) evaluates false forever. Symptom: the step shows `skipped` in every run, even when its own guard script
computes true; downstream steps gated on its outputs are skipped too — and a "success" workflow hides it.

**Verify before blaming logic:** `grep -n 'id:' .github/workflows/x.yml`, then demand a run where the condition must
have been true (find a commit that changed the file the guard tests) and check that step's `conclusion`.

## 4. Rules of thumb

- Never trust a workflow file's *intent* comments — read the triggers, the `if:` guards and the step ids.
- Two runs with the same check name from different events = duplication, not flakiness.
- After changing triggers, verify with `gh run list --branch <branch>`: the fix is visible immediately (no push-event
  run appears on the branch you push).
- A red nightly run nobody noticed means the fix must also *fail loudly* (annotations/`::error::`) and be verified
  with a `workflow_dispatch` run once merged.
