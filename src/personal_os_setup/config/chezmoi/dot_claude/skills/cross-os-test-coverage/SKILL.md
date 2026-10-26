---
name: cross-os-test-coverage
description: Use when adding or auditing test coverage for another OS.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Cross-OS test coverage

Use when the question is whether (and where) each OS in an app's support matrix is tested — "are there VMs for
macOS and Windows to test?", "add Windows CI", "is this covered on macOS?" — or when adding coverage for one
more OS. Applies to any repo; the per-guest VM mechanics live in that repo's own VM skill (`vm-lab`), the
suites in `run-tests` — read those for mechanics, this file for the method.

## 1. Answer the coverage question from evidence, never from memory

```bash
grep -rn "runs-on:" .github/workflows/     # what CI actually runs on
grep -rln "skipif\|pytestmark" tests/      # per-OS skip markers = which module covers which OS
grep -rn "^cmd_\|usage:" scripts/vm.sh     # which local VM guests exist
```

Answer as a matrix — OS | CI job | local VM | test module — and say "untested" where the only evidence is
supporting code. **Support is not coverage:** package-manager backends, install scripts and OS branches can
exist for an OS with no runner, no module and no VM target, so every code path for it is exercised by hand
only. That distinction is the whole answer; do not soften it.

## 2. Pick the cheapest honest coverage per OS, in this order

1. **Hosted CI runner on the real OS** — free for public repos, the only thing that proves the code path. A new
   per-OS job mirrors an existing one (~20 lines); almost always the right first move.
2. **Local VM guest** — when the user wants to click through the flow by hand. Costs a script function + make
   target + help/docs lines + the mirrored package-catalogue entry; quote that cost when asked "can we test it?".
3. **Container** (Linux only). 4. **Unit tests with the OS faked** — never counted as integration coverage.

**Coverage parity is two halves.** Where every other OS has a CI job *and* a `vm-*` guest, "can we test OS X?" asks
for both — the user verifies OS-setup flows by booting a VM and clicking through. Deliver or explicitly scope both
halves and say why the other is out; a CI-job-only answer gets corrected mid-task.
Third-party VM project proposed instead: read its fetch script first — the blocker you remember may not exist, and
it may not fit an ISO+`virt-install` flow (`references/guest-os-images.md`).

## 3. Before writing a hosted-runner job, verify the runner's toolset

A job can't be validated locally — the push is the test — so a step using a tool the image lacks fails only after
dispatch. The image manifest is authoritative (query and verified facts: `references/hosted-runner-toolset.md`).

- **Runner OSes are not interchangeable.** On `windows-latest` there is no GNU make (MSYS2 is on disk, off `PATH`)
  and no `uv`: call the test entrypoint directly and install uv with an action (pinned exact — no floating major tag).
- `shell: bash` exists on Windows runners (Git Bash).
- **Confirm the label → image mapping from a live run, never from memory** (`gh run view --job <id> --log | grep -E
  "Image Release|Operating System"`); labels drift past the OS the docs still name.

## 4. Test module shape for a newly covered OS

- **Module-level skip keyed on the OS actually running** (the repo's detector or `platform.system()`), mirroring
  the sibling modules — never an env var or CI marker.
- **Read-only, runner-safe assertions**: OS detection, factory/wiring resolution, `cleanup()` no-ops,
  `is_installed("<clearly fake id>") is False`, version queries tolerating an absent tool. No installs, reboots or
  interactive flows. Gate tool-dependent cases with a `skipif` evaluated **at runtime against the tool**
  (`shutil.which(...)`), never against what you believe the image ships — a Server SKU is not proof a client tool
  is missing.
- **Read the skip condition before reading a result as a pass.** A `SKIPPED` under an inverted guard (skip *when
  the tool is absent*) is evidence the tool IS present — and that the test never exercised its target path.
- **Prove it skips where you are**: `uv run --frozen pytest tests/integration -q` → `N skipped`, existing suite unchanged.
- Use `uv run --frozen` for local proof runs: a newer local `uv` rewrites the lockfile revision. A gate that
  installs deps (`make pre-commit` runs `uv sync --all-groups`) dirties it again — `git restore <lockfile>`
  before staging, or the commit carries dependency churn nobody asked for.

## 5. Local VM guests: sourcing differs per OS

| OS | Image source | Note |
|---|---|---|
| Linux | official URL + checksum, downloaded by the script | unchanged path |
| Windows | **user-supplied path** (`WIN_ISO=...`) | Microsoft's links expire behind a browser session — never invent or scrape a URL; fail with a clear message |
| macOS | fetchable from Apple's CDN (no Mac needed) via a community project | a QEMU wrapper is **not libvirt**, so it drops out of `virsh` list/clean; the EULA restricts macOS guests to Apple hardware — state it, let the user decide |

A guest needing extra host packages goes in the VM dependency list **and** the mirrored package catalogue (every
package-manager branch, not just the one you use) — manual mirrors of each other. Update the repo's VM/test skill
and VM docs in the same change, or the new target exists but nobody finds it. Windows-11 flags, no-TPM fallback,
macOS routes: `references/guest-os-images.md`.

## 6. Split the report by what was actually proved

Three buckets, never merged: **proved locally** (command + observed output), **provable only by a push** (the job,
the runner's tooling, the OS-specific run), **provable only by booting** (the VM path against a real ISO). A job
that has never run is "written, unverified" — offer the push as the next step, don't assume approval for it.

## Pitfalls

- Ruling a local VM out from memory before reading the project's own fetch script.
- Claiming coverage because the supporting code exists.
- A runner job calling the Linux/macOS entrypoint (`make …`) on Windows.
- A guest dependency added in one list only, or only in the package-manager branch you use.
- EULA-walled guests: implement and flag; never ship silently or fake the download.
- Reporting a delegate's summary as verified state — check the artifact (diff, test output, manifest).
- **Delegated coverage work: create the branch before the run** (`git fetch origin <default> && git switch -c
  <name> origin/<default>`, repo naming convention). Delegated work returns uncommitted, so on the user's active
  branch it would mix into whatever PR is open there.
