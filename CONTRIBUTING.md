# Contributing

1. Pick an issue and wait to be assigned; coordinate with any existing assignee.
2. Follow [Setup](docs/developer/1.setup.md), then branch from `main` using
   `feature/<name>` or `bugfix/<name>`.
3. Update the relevant docs and run `make check` ([Testing](docs/developer/4.testing.md)).
4. Open a PR to `main` with a [Conventional Commit title](docs/developer/3.conventions.md#commit-convention).
   PRs are squash-merged; the title determines the release version.

CI runs platform integration in addition to local checks. See [Release](docs/developer/5.release.md)
for publication and recovery.

Follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report security issues through
[SECURITY.md](SECURITY.md), never a public issue. Coding agents need separate approval for
commits, pushes, PRs and system changes; see `AGENTS.md`.
