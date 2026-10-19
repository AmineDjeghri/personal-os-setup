# What GitHub-hosted runners actually provide

Re-verify before relying on any value here — images roll monthly and a job that fails at its first step is
usually a tool that moved or was never there.

## The manifest query (works for every image)

```bash
gh api repos/actions/runner-images/contents/images/<windows|macos|ubuntu>/<Image>Readme.md \
  --jq .content | base64 -d | grep -iE "<tool>"
```

Grepping the rendered markdown settles presence; the tool tables list exact versions.

**The label → image mapping is not stable** (a `latest` macOS label has already moved past the OS the docs still
name): take it from a live run (`gh run view --job <id> --log | grep -E "Image Release|Operating System"`) or the
image readme's announcements. A guest default meant to match CI must track what the log says.

## Windows (`windows-latest`)

Verified against the Windows Server 2025 image:

- **No GNU make.** MSYS2 is installed on disk but its `bin` is not on `PATH`, so `make` is not callable in a
  `shell: bash` step. Any job line inherited from a Linux/macOS job that starts with `make` must be replaced
  by the underlying command (e.g. `uv run pytest …`).
- **No `uv`** — install it with `astral-sh/setup-uv`; that action publishes **no floating major tag**, so pin an
  exact `vX.Y.Z`.
- **`winget` IS present** on the current Server image, despite being a client-OS feature. Do not write tool
  absence into a test from the manifest: gate the backend cases on the tool at runtime, assert the
  graceful-failure path only when it really is absent, and read the pass/skip counts afterwards to learn which
  branch actually ran.
- **Git Bash is present**, so `shell: bash` works, and preinstalled Python is older than what modern projects
  pin — `uv` fetches the pinned interpreter.
- The image is a **Server** SKU: no Store, no desktop apps, no WSL distro.

## macOS (`macos-latest`)

- `make` and the system Python are present, so the existing `make <target>` job line works as-is.
- Real Homebrew work (formula/cask install, cleanup) is possible here — this is the cheapest real-OS coverage
  for anything that shells out to a Unix package manager.

## Ubuntu (`ubuntu-latest`, `ubuntu-XX.YY`)

`make` present; use a version-pinned label when the distro version itself is under test.

## Reusable composite-action trap

A shared install action that assumes a POSIX shell silently breaks the new OS. Branch it on
`if: runner.os == 'Windows'` / `!= 'Windows'` and make the non-Windows path run exactly the same command the
repo's own `make` target runs, so the delegate env on the new OS matches the others.
