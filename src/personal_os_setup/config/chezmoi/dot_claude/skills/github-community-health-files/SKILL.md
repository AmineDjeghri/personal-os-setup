---
name: github-community-health-files
description: "Detect missing GitHub community/health files (SECURITY.md, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, FUNDING) and generate them."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, SECURITY, LICENSE, CONTRIBUTING, Repository, Health]
    related_skills: [github-repo-management, github-pr-workflow, github-auth]
---

# GitHub Community Health Files

Detect which GitHub standard/community files a repo is missing, then generate them
with ready-to-use templates and open a PR. Applies to any public (or private) repo
that should pass GitHub's community-profile health check.

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

- **Privacy rule: NEVER write a *personal* email into any public
  repo file or commit metadata.** The personal Gmail (user@example.com) must
  never appear. However a **dedicated public contact email** (e.g. `contact@example.com`)
  IS acceptable if the user explicitly provides one — ask or use one they supply. Contact
  points in SECURITY.md / CODE_OF_CONDUCT.md default to GitHub private vulnerability
  reporting; add the public email only if the user gives it. Set the commit author to the
  GitHub **noreply** email so the personal email never appears as git author:
  ```bash
  git config user.name "Your Name"
  git config user.email "12345678+your-username@users.noreply.github.com"
  ```
  (Derive the id+username from `gh api user --jq '.id'` + `.login` if unknown.) If the
  user says a personal email leaked, treat removing it as urgent.
- **"Match another repo's templates" = adapt, don't verbatim-copy.** When the user wants
  CONTRIBUTING/LICENSE "the same as <other-repo>", the other repo's CONTRIBUTING often
  references tooling the target repo lacks (make/uv/pyproject.toml, a `dev` branch,
  gh-pages docs, Polars). Copying verbatim ships wrong instructions. Adapt to the target
  repo's actual stack while keeping the same structure/style/sections. The LICENSE can
  usually be copied near-verbatim.
- **Removing an email trace from a pushed PR.** If the email leaked via a PR, the file
  contents AND the git commit author both carry it (the branch's commits contain the
  author email). Close + delete the remote branch in one step so no commit reaches the
  remote:
  ```bash
  gh pr close <N> --delete-branch
  ```
  Verify it's really gone: check `gh pr view <N> --json body` (body), issue comments
  (`/issues/<N>/comments`), review comments (`/pulls/<N>/comments`), the PR diff
  (`gh pr diff`), and that the commit's `%ae` on the pushed branch uses the noreply
  email. When you then recreate the files on a new branch, remember the old branch's
  working-tree files were removed by the branch switch — re-create them. Re-branch from
  `main` so only the single new clean commit ships.
- **FUNDING.yml is optional — don't assume the user wants it.** This user explicitly
  declined it ("we don't need funding file"). Offer it, don't bundle it by default, and
  drop it immediately if the user rejects it.
- **Monorepo / multi-add-on repo → lean umbrella CONTRIBUTING, not a tooling dump.**
  In a repo with several add-ons where ONE sub-project (e.g. `addons/personal-app`)
  ships its OWN Makefile / uv / pyproject.toml / pre-commit / CONTRIBUTING.md, the root
  CONTRIBUTING should be a short umbrella guide that DEFERS to that sub-project's own
  guide (via an overview table + "its guide wins" note) and only documents tooling that
  genuinely applies repo-wide (the shell-based add-ons). Don't restate the sub-project's
  Python tooling as if it were repo-wide. Before writing, inspect the tree
  (`git ls-tree -r --name-only HEAD | grep <subdir>`) to see which add-ons have their
  own tooling.
- **gh-pages branch existing ≠ a live site.** A `gh-pages` branch can exist with fully
  built MkDocs content but not actually be deployed/enabled. If the user says they don't
  have a live gh-pages site, don't claim it is deployed — phrase docs as "may be
  published to `gh-pages` in the future" and offer to enable GitHub Pages (Source:
  `gh-pages` branch) rather than asserting it's live.
- **Issue templates don't fully clear the health check.** Having only YAML forms in
  `.github/ISSUE_TEMPLATE/` (no legacy `ISSUE_TEMPLATE.md` and no `config.yml` chooser)
  still flags `issue_template` as missing. Add a `config.yml` or the legacy file if
  the user wants it green. Minor — the YAML forms still work.
- **Destructive git ops get blocked in the Hermes agent terminal.** `git reset --hard`,
  `git clean -fd`, and `rm -rf` are gated behind a consent prompt and time out with no
  user response. If a local clone is stale/behind origin, DON'T force-reset it — clone
  fresh into a new unique directory instead:
  ```bash
  D="repo-$$"; gh repo clone owner/repo "$D"; cd "$D"
  ```
  A fresh clone has no git identity — set it before committing:
  `git config user.name "..."; git config user.email "..."`
- **Work on a branch + PR.** Create a `docs/...` branch, commit with a conventional
  commit message, push, then `gh pr create`. Keep PR description to 1–2 lines.

## Support files

- `references/community-health-files.md` — ready-to-paste template content for all
  five files (SECURITY.md, MIT LICENSE, CONTRIBUTING.md, CODE_OF_CONDUCT.md, FUNDING.yml).
