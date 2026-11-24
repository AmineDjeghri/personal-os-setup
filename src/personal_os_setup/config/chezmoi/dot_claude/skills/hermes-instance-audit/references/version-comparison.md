# Version & release comparison

- Local first: `.update_check` (`behind`) + `<install>/pyproject.toml` `version =` — the install is often already current.
- git install (cheapest "latest vs mine"): `git fetch origin && git rev-list --count HEAD..origin/main` (`0` = the checkout IS main tip), `git tag --sort=-creatordate | head -5`, `git rev-list --count <tag>..HEAD`. HEAD can be AHEAD of the newest tag (main tip) — report both.
- Tag ↔ version: check `git tag --sort=-creatordate | head` rather than assuming a scheme; patch notes may be rolled into the next minor.
- **A new version in `pyproject.toml`/`--version` does NOT mean the new code is live.** `hermes update` never restarts the gateway or dashboard: `hermes status` prints "manual restart still pending" for the stale owner and that process keeps serving pre-update code. Compare `ps -o lstart` of the gateway pid against the install mtime before explaining any post-upgrade behaviour. Procedure + per-feature evidence: `release-verification.md`.
- Manifest vs repo: `.bundled_manifest` should equal `<install>/skills/**/SKILL.md` 1:1.
