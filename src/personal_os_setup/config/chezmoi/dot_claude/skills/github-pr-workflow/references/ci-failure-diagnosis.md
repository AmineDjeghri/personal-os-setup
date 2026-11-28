# CI failure diagnosis — commands and rules

Depth for `SKILL.md` §5. Repair of the shared lint/pre-commit/release tooling lives in `template-adoption`
(`references/tooling-stack-repair.md`); trigger questions in `github-actions-trigger-gotchas`.

## Runs, jobs, annotations

```bash
gh run list --branch <branch> --limit 20                       # why a branch keeps failing
gh pr checks <n> --json name,state,link                        # state is UPPERCASE: FAILURE / SUCCESS / SKIPPED
gh run list --branch <b> --limit 3 --json databaseId,event,status,conclusion   # newest run for the head SHA only
gh api repos/O/R/actions/runs/<run-id>/jobs --jq '.jobs[]|"\(.name) \(.conclusion)"'
gh run view --job <job-id> --log > /tmp/job.log                # whole log, then grep
gh api repos/O/R/actions/jobs/<job-id> --jq '.head_sha, .run_id'   # the SHA it really built
gh api "repos/O/R/contents/.github/workflows/x.yml?ref=<sha>" --jq .content | base64 -d
```

- `--log-failed` prints only post-step cleanup for composite actions (`UNKNOWN STEP` … "Cleaning up orphan
  processes"); the real output is earlier in the full job log.
- `gh pr checks` lists **cancelled** jobs as `fail`. A superseded duplicate run is noise.
- A PR can keep the OLD push-event run's red check after main moves on while its `pull_request` run is green: name
  which run each check belongs to and rebase/re-run instead of reporting the PR as green.
- Same code red on one event and green on the other (push vs pull_request) = flake: say so with both run IDs.

## Parse-time rejection: actionlint

```bash
curl -fsSL -o /tmp/al.tgz \
  https://github.com/rhysd/actionlint/releases/download/v1.7.7/actionlint_1.7.7_linux_amd64.tar.gz
tar xzf /tmp/al.tgz -C /tmp actionlint
cd <repo> && /tmp/actionlint -no-color -oneline
```

- Run from the repo root so `uses: ./.github/...` resolves. `-no-color`, not `-color=never` (parse error).
- One error can hide the rest: re-run until silent.
- `runner` context is legal only on a running step; a `workflow_call` workflow has an even smaller context set.
- actionlint's runner-label list lags GitHub (`ubuntu-26.04` "unknown"): pre-existing noise, don't "fix" it.

## Which commit, which branch

- `git rev-parse main origin/main` before reading YAML; read workflow and pre-commit files at the run's `head_sha`.
  After a force-push, local remote-tracking refs describe a file that no longer exists.
- A bot PR's title understates it: grouped bumps fold several tools into one PR. Read every pin at `head_sha`.
- Fix bot branches by fixing main: Renovate force-updates its own branch, so a commit pushed there can vanish.
- Renovate updates managed datasources only (`requires-python`, `uses:` refs, Dockerfiles); a matrix string in a
  workflow is never touched. Comment the coupling next to such a matrix entry and say a human must bump it.
- One checkout, one writer: if the tree changes under you (edits reverting, `git status` differing between two
  calls), another session owns the repo — stop writing and ask. `git fsck --connectivity-only` (dangling objects
  only = healthy) separates corruption from concurrent index churn.

## Interpreter and uv lock failures

- `The requested interpreter resolved to Python X.Y.Z, which is incompatible with the project's Python
  requirement`: a matrix entry written as a minor (`"3.14"`) resolves to the newest patch, which a patch-capped
  `requires-python` rejects. Pin the patch or widen the cap. Reproduce with the exact patch:

  ```bash
  mkdir -p /tmp/uvprobe && cd /tmp/uvprobe      # copy pyproject.toml (+ uv.lock) only
  UV_PYTHON=3.14.8 uv sync --frozen --no-install-project
  ```

  A local `3.14` can pass on a cached older patch: the CI log line is the authority.
- `No solution found when resolving dependencies for split (...)`: a wheel missing for one matrix entry — upstream,
  not a CI bug.
- **Freshness gate is `uv lock --check` / `UV_LOCKED=1`, never `--frozen`** (`--frozen` installs from a stale lock and
  exits 0). Put `UV_LOCKED: "1"` on the CI install step.
- A clean-tree guard failing seconds after the install step = the installer rewrote a tracked file (`uv sync`
  re-locked). Reproduce in a real `git clone` of the SHA (not a `git archive` copy):

  ```bash
  git clone --depth 1 -b <branch> <url> /tmp/drift && cd /tmp/drift
  uv lock --check ; echo "check=$?"         # rc 1 + "needs to be updated" = stale
  uv sync <the repo's own install flags> && git status --porcelain   # the rewritten path is the defect
  ```

- Stale lock on main while every PR check was green: a squash merge combined one side's `pyproject.toml` with the
  other side's `uv.lock`. Re-lock on main; the PR run proved nothing about the squash result.
- The `uv-lock` pre-commit hook (`pass_filenames: false`) rewrites the lock and still reports **Passed**: give it
  `args: ["--check"]`. Test it with `./.venv/bin/pre-commit run uv-lock --all-files`, not `uv run …` (which re-locks
  first), and confirm `uv.lock` stayed byte-identical.
- Moving the pinned interpreter: re-lock, then grep the literal in the Dockerfile `ARG`, README badge and docs.
  Collapsing a matrix to one interpreter is a support change: `refactor(python)!:` + `BREAKING CHANGE:`.

## Lint drift after a hook bump

```bash
sed -n '/markdownlint/,+3p' .pre-commit-config.yaml
npx --yes markdownlint-cli2@<old> "**/*.md" ; npx --yes markdownlint-cli2@<new> "**/*.md"
uv tool run --from ruff==<new> ruff format --check .
uv tool run pre-commit run <hook-id> --files <path>     # the pinned rev, as CI runs it
```

- Pass the glob explicitly: a config with `ignores:` but no `globs:` lints `0 files` and looks like a pass.
- A repo is safe only by its **pinned rev**: grep the pin in every sibling repo and run the candidate rev on each.
- Verify on a run that carries the new rev; a green run created before the bump proves nothing.
- Before relaxing a rule, test what it protects (`MD007: {indent: 4}` exists because Python-Markdown flattens 2/3-space
  nested lists silently). Offer the enforcement-preserving fix beside "disable it", measured.
- ruff formats Python fences inside Markdown: drift after a bump is often a docs-snippet fix, not a pin change.
- Never read an exit code through a pipe (`cmd | tail; echo $?` is `tail`'s status): use `${PIPESTATUS[0]}`.

## Process

- Commit type is part of the fix in a semantic-release repo: `fix(ci)` cuts a patch release, `chore`/`refactor`
  do not. Say in the PR body when merging will release.
- When the approach changes mid-review, rewrite the PR title and body in the same turn (the title is the squash
  commit).
- A test against a tiny local model (0.8B class) is a flake generator (echoes the schema, empty content): fix the
  model/`max_tokens`/marker, not the rerun count.
- Rebasing a PR needs `git push --force-with-lease` with its own approval; if the user edited the branch in the
  browser, the lease fails with `stale info` — fetch, re-apply on `origin/<branch>`, push normally.
