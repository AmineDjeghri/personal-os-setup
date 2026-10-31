# Contributing

Thanks for contributing! ❤️ Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md);
report unacceptable behavior by opening an issue. Team: the contributors of the repository.

1. **Pick an issue**: comment on it (or create it) and wait to be assigned, so two people don't
   work on the same thing. If the assignee seems inactive, ask them first.
2. **Set up** once: [Setup](docs/developer/1.setup.md).
3. **Branch** off `main` and follow the [Conventions](docs/developer/3.conventions.md).
4. **Check** before pushing: `make check` ([Testing](docs/developer/4.testing.md)).
5. **Open a pull request** to `main`. Its title follows the
   [commit convention](docs/developer/3.conventions.md#commit-convention): it becomes the squash
   commit and decides the next version ([Release](docs/developer/5.release.md)).

**Local checks:** `make check` runs static/docs hooks and safe software/artifact checks. Required
CI also runs platform integration on disposable hosts; a local pass does not establish a CI pass.
See [Testing](docs/developer/4.testing.md) before using `make act` or any integration harness.

Security issues: [SECURITY.md](SECURITY.md), never a public issue.
