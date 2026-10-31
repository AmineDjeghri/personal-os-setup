---
name: repo-gotchas
description: Use when checking documented behavior against Make targets, quality gates or validation claims.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Tooling boundaries in personal-os-setup

- Bare `make` displays help. `make install-uv` installs only when missing; `make update-uv`
  explicitly updates. `make install` installs runtime dependencies; use `make install-dev` for tools.
- `make pre-commit` runs prepared tools without synchronization or hook installation. Setup hooks
  once with `make pre-commit-install`. New untracked files need explicit checking with
  `make pre-commit PRE_COMMIT_ARGS="--files <paths>"`; `--all-files` sees only tracked files.
- The strict docs hook calls `make docs-build`; `make check` then runs safe software/artifact checks.
  A local pass does not establish required hosted platform integration. See [[run-tests]].
- Installation smoke checks a real isolated wheel and loads the `personal-os-setup` callable;
  it does not run application startup. Artifact checks also require matching sdist metadata/resources.
- actionlint is enabled. zizmor, pip-audit, bandit and markdown-link-check remain commented out.
- commitizen runs at the commit-msg stage; a pre-commit pass alone says nothing about message format.
- detect-secrets is stateless. New false positives need inline allowlisting, not a whole-file exclusion.
  Existing exclusions are limited to generated payload/lock content and binary artifacts.
- Formatting hooks can rewrite files and fail on their first run. Recheck their final content.
- `properdocs.yml` uses `docs_dir: .`; new top-level output directories need exclusion. See [[docs-site]].
- `packages.yaml` manager registrations are checked by `tests/unit/test_detect_os.py::TestPackagesYaml`.
- The `dev` branch and its release workflow are retired. Only tested main revisions release;
  interrupted version/tag publication can resume verified asset uploads. See the release guide.
- `make act` launches platform workflows and may mutate its execution environment. It is not a safe
  test-local replacement. `tests/archlinux` is a manual interactive sandbox, not CachyOS validation.
