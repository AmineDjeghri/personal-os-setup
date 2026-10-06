---
name: template-adoption
description: "Use when aligning an existing repo with a house template."
version: 1.0.0
author: Hermes Curator
license: MIT
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [Template, Repo-Audit, Refactor, CI, Line-Endings, Delegation]
    related_skills: [repo-conventions, coding-workflow]
---

# Aligning a repo with a house template

The deliverable is a verified gap matrix, the user's decisions, then the committed change.

## 1. Establish the facts before proposing anything

1. **Enumerate every candidate ref before comparing.** `git branch -r`, `gh pr list --state all`, and the root
   tree of each branch (`git ls-tree -r --name-only <ref>`). A branch whose name says nothing about the template
   can still carry the ported files; the branch that looks like the port can be stale.
2. **Compare file sets, not file names — and strip CR when either side may be CRLF:**
   `diff <(git show <ref>:$f | tr -d '\r') <(git -C $TPL show HEAD:$f)`. Byte identity (`md5sum`) is false the
   moment one side is CRLF: files can differ on every line and still be content-identical. Never repeat
   "already ported, byte-identical" until you know which claim is true.
3. **Check the port branch's position against its base first:**
   `git rev-list --left-right --count origin/main...HEAD`. A long-lived port branch is usually many commits
   behind and will not merge at all — that is the headline finding, ahead of any further adoption work.
4. **Dry-run the merges without touching the working tree:**
   `GIT_OBJECT_DIRECTORY=$(mktemp -d) GIT_ALTERNATE_OBJECT_DIRECTORIES=<repo>/.git/objects git merge-tree --write-tree --name-only --messages <A> <B>`.
   Run it for the base branch and for every other open branch, and report the conflict sets as measured.
5. **Verify the template's own files.** A file lifted from a template can be stale, wrong, or not from the
   template at all (confirm each candidate exists in the template today), and its contact details, emails and
   URLs are the template author's — adapt them, never copy them verbatim. The user's privacy rule applies: no
   real address, domain or tunnel placeholder in a repo; when the user asks for a placeholder rather than a real
   contact, use an obvious `*@example.invalid` plus a TODO comment.
6. **Report a gap matrix, not a narrative.** One row per item: name, present on each side, how it differs with
   the command behind the claim, action (adopt / adapt / skip) and WHY. Group the rows so the user can scan them.

## 2. The decisions to surface (each with a recommendation)

Ask before planning commits — these change which files are adopted:

- **Directory layout:** renaming package dirs to match the template invalidates the lockfile, Docker/compose
  paths and every other open branch. Recommend keeping the repo's names as a documented deviation.
- **Lint/format thresholds** (e.g. line length 100 vs 120): adopting the template's value reformats source,
  collides with other branches and buries the real diff. Keep the repo's value and say so.
- **Task runner** (`make` vs `just`): a genuine fork in the road — it decides which files are adopted, what CI
  calls, and the remaining conflicts. Get the decision first.
- **Docs tool** (mkdocs / properdocs / none): check whether the release workflow already calls a docs target — a
  job running `deploy-doc-gh` against a repo with no docs config is broken today, which is itself a finding.
- **Governance files** (`CONTRIBUTING`, `SECURITY`, `CODE_OF_CONDUCT`, `CHANGELOG` stub): adopt adapted, never
  verbatim.

## 3. Then delegate the execution

Every in-repo edit belongs to the coding delegate; this skill plans and verifies. Two-phase beats one long run:

1. **Phase 1 — plan-only brief.** Forbid commits and pushes. Make the artifact a plan file written INCREMENTALLY
   outside the repo (e.g. `../<topic>-plan.md`) holding the gap matrix, per-item risk, the decisions,
   the commit sequence with the validation command per commit, and an OUT-OF-SCOPE list. Require it to **verify
   the context you hand it, never trust it** — expect part of your premise to be wrong (a branch you assumed was
   current can be many commits behind and unmergeable; "byte-identical" can be CRLF-vs-LF). Budget ~45 turns.
2. **Between phases — the user decides.** Put the decisions in one form so the user can answer them together;
   recommend the first option in each.
3. **Phase 2 — resume the SAME session** with a short decisions brief (`--resume <session_id>`), so the analysis
   already paid for is kept. Budget `--max-turns 120`.
   - **Commits need their own explicit yes, separate from push** ("go ahead" is not commit approval); the brief is the delegate's only brake (`--permission-mode acceptEdits` prompts nothing) — name what is forbidden, not only what is allowed; push only after you verified the artifact yourself.

## 4. Verify the result yourself — and keep the write with the delegate

- **Re-derive the load-bearing claims.** A run's summary drifts from the filesystem, and its own commit list can
  name a target the files never contained. Re-check that the tree is conflict-free (`git ls-files -u` empty),
  that the lock resolves (`uv lock --check`), that the line endings actually moved, that guideline files and other
  branches are untouched, and that a dry-run merge against the base is clean. Report which checks you executed
  and which you only inspected.
- **A runner the box lacks is not a dead end.** Drive missing tools through uv rather than declaring the artifact
  unverifiable: `uv tool run --from rust-just -- just --list` (the PyPI package carrying the `just` binary),
  `uv tool run pre-commit run --all-files`, `uv run ruff format --check <files>` (the pinned venv version).
- **Line-ending hygiene is part of the port:** adopt the template's `.gitattributes` + `mixed-line-ending` hook; convert only files the PR introduced; exclude third-party CRLF assets (font licences).
- **Don't promise mergeability you did not measure.** Adoption can leave the conflict count with another open
  branch unchanged while changing only its nature (deletion conflicts become textual ones). State the measured
  sets and let the user pick the merge order.
- **Exception to the delegate rule:** a fix the user hands you in the moment ("yes, add that small style commit") — do exactly that one thing, then re-run the hooks yourself and report the CI state.
- **Check attribution before pushing anything.** `git log --format='%an <%ae>'` over the new commits must show the
  user's identity (set `user.name`/`user.email` in the clone first — an unset identity silently leaves whatever
  the repo had), and a coding agent stamps a `Co-Authored-By:` trailer by default: the author field reads clean
  while GitHub still lists the agent as a co-author on every commit and in the PR's contributors. Surface it to the
  user instead of letting them find it.

## 5. Porting the lint/format and dependency tooling

- **One ruff config file.** Ruff resolves `.ruff.toml` > `ruff.toml` > `[tool.ruff]`: delete the standalone file and confirm with `ruff check --show-settings <file>` (it must name the pyproject you edited).
- **A hook's `rev` and the dev-group pin must be the same version** — re-run `pre-commit run --all-files` until a clean second pass and include the reformat in the bump commit.
- **A dependency refresh is ONE commit** — `uv.lock`, pins and the `src/` compatibility fixes together.
- **A pin raise is verified only by CI's service-backed job** — locally skipped tests are unverified.
