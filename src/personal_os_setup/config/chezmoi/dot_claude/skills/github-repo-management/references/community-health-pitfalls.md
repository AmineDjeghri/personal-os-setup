# Community health files — pitfalls

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
