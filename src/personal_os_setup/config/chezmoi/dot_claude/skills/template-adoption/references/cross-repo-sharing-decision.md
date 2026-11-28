# Should the three sibling repos share their gate stack?

Recurring question: "stop copy-pasting actions / makefiles / python tests across the repos — publish a shared
`gh-actions` repo, or a helper package?" Answer it with measurement and constraints, not with DRY instinct. The
analysis below was done on the three repos (`personal-os-setup`, `generative-ai-project-template`,
`python-package-template`) and the verdict is recorded so it is not re-litigated from scratch.

## 1. Measure first

- Compare **committed refs** (`origin/<default>`), never working trees: local checkouts are routinely several
  commits behind and a dirty tree hides the real state.
- "Byte-identical" = equal git blob SHAs (`git ls-tree <ref> -- <path>`). Check for CR bytes first
  (`git grep -lP '\r' <ref>`) or "differs" verdicts turn out to be CRLF artefacts.
- A branch that is N commits "ahead" may already be on main through a squash merge. Prove emptiness with
  `git diff origin/main...origin/<branch>`; zero diff means nothing left to port or revive.
- Class every managed path: `identical-all` · `identical-between-templates` · `equivalent` (same intent,
  cosmetic drift) · `divergent-by-design` (record the reason and the commit that made it so).
- `scripts/cross_repo_drift.py` (this skill) prints that table for a path manifest.

Beware the brief you were given: file lists in a task description are hypotheses. Check which workflow files
actually exist (`release.yml` may live only in the templates, `docker.yml` nowhere) and which scripts only exist
on an unmerged branch.

## 2. Three constraints decide the answer more than the diff does

1. **GitHub Actions cannot host `makefiles/*.mk`.** CI in these repos is a thin YAML wrapper over `make` targets
   (`install-<profile>`, `pre-commit`, `test-all`, `release-version`, `build-package`, `deploy-doc-gh`), and the same
   targets are the local entry points. An actions repo absorbs only the YAML wrapper; the release guards, install
   profiles and test orchestration stay duplicated, and `make release` / `make test-all` are not covered at all.
2. **The two templates are public repos meant to be forked standalone.** Any runtime dependency on a third repo —
   a composite action behind a mutable `@v1`, or an installed helper package — breaks that promise and puts
   release code (`contents: write`) behind an external ref. A stranger's fork would have to fork the actions repo
   too just to change CI.
3. **Reusable workflows cannot raise the caller's permissions**, and `uses: ./…` inside a called workflow resolves
   against the *caller's* checkout — so triggers, `concurrency` and `permissions:` stay in every repo no matter what.

Two further facts that shrink the payoff: **Renovate already automates the version-bump class of drift** in all
three repos (hook revs, action versions, lockfile maintenance), and the truly shareable Python is a few dozen
lines (`emoji_commit_parser`, the doc-stub generators) while the rest is either domain-bound (the real repo's
`release.sh` + `check_*.py`) or deliberately opposite (`integration_results.py` fails on zero passed tests in one
repo and tolerates full skip in the other).

## 3. Options and their real cost

| Option | What actually moves | Cost that decides it |
|---|---|---|
| Composite actions + reusable workflows in one public repo | the install action, the release workflow body, the PR-title job (~100–150 YAML lines) | mutable ref / SHA pin + a bump PR per consumer per release; every local `uses: ./` must become `owner/repo/...@ref`; Makefiles stay duplicated |
| Published Python helper package | the scripts + a pytest plugin | new release process + PyPI trusted publishing (none exists today, no OIDC anywhere); tests that read repo files by path must be rewritten; version skew with consumers' locked tooling |
| Mechanical copy: drift manifest + checker, then `copier` | nothing at runtime | a few hours for the checker; `copier update` does three-way merges, output stays committed so the templates stay standalone |
| Mix | one self-contained job shared, copy for the rest | two mechanisms to maintain |

## 4. Recommended order

1. **Drift manifest + read-only checker**, owned by the non-template repo so strangers do not inherit it. It lists
   the managed paths, classifies them, and compares blob SHAs across the repos. Adopt a direction rule (the
   package template is upstream for generic pieces, the generative template follows it, the real repo pulls from
   both) and backport what the checker flags instead of rediscovering it.
2. **`copier` for the two templates** (not cookiecutter — `copier update` merges) only if cross-repo ports keep
   recurring, e.g. three or more in a month or a handful of unclassified files per run. Template only the common
   core; keep the real repo outside.
3. **Optional experiment, last:** one shared repo holding a single job that needs no `make`, no checkout and no
   secrets (PR-title validation is the canonical one), consumed by the non-template repo only, abandoned if it
   saves nothing.

**Never** a shared pytest "harness": there is nothing generic in it. Fixtures are bound to repo files and domain
constants (`ROOT/"makefiles/release.mk"`, `scripts/*.py`) and break the moment the code moves out of the repo.

## 5. Do-not-share list

- every `makefiles/*.mk`, including `release.mk` (they are the local↔CI parity contract);
- `scripts/integration_results.py` (opposite skip rules by design — its header says not to "fix" it back);
- the real repo's release stack (`release.sh`, `check_artifacts.py`, `check_installation.py`, `check_release_source.py`);
- product-specific workflows and their makefiles (Ollama, docker, `vm.mk`, `skills.mk`, the OS matrix, `check_config.py`);
- `on:` triggers, `concurrency:` and `permissions:` blocks — especially `contents: write` on a release path;
- `pyproject.toml` content: `requires-python`, dependency pins, semantic-release branches/`build_command`, coverage
  sources, pytest markers;
- hook `rev` pins and `renovate.json` rules — Renovate owns them per repo.

## 6. Reporting it

Deliver a one-paragraph verdict first ("don't extract; start with a drift check"), then the inventory, the option
costs, the staged plan and the do-not-share list. Numbers that make the verdict land: how many paths are actually
identical, how many YAML lines a shared repo would save, and which files exist in only one repo.
