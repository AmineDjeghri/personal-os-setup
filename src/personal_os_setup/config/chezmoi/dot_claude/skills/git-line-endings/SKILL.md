---
name: git-line-endings
description: "Use when CRLF/LF churn breaks git diffs in a repo."
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Git Line Endings (.gitattributes / CRLF-LF normalization)

Use when a one-line edit diffs the whole file.

## Diagnose first — never guess

- `git ls-files --eol` is authoritative: per tracked file it shows index/worktree endings (`i/lf w/lf`, `i/crlf`, `i/mixed`). Contaminated blobs = `git ls-files --eol | grep -E 'i/(crlf|mixed)'`.
- Do NOT byte-scan working-tree files (od/python open) to judge blob state — confusing. `--eol` settles it.
- A clean `git status` proves NOTHING: blobs can be consistently CRLF, or `text=auto` silently tolerates CRLF worktrees that round-trip clean.

## Root cause (the WHY)

`.gitattributes` governs future commits only — it never rewrites existing blobs. Adding or editing it leaves legacy CRLF/mixed blobs untouched until a renormalize. Symptom: the first edit that writes LF lines into a legacy-CRLF file normalizes the whole file at commit → entire-file diff for a one-line change.

## Fix — normalize once, per repo

1. Sync the base first: fetch, then `git switch main` and `git pull --ff-only`.
2. Branch `chore/normalize-line-endings` and commit `chore: normalize line endings to LF` — `chore:` keeps semantic-release repos from bumping on non-user-visible maintenance.
3. Author/extend `.gitattributes` — `* text=auto`; `eol=lf` for shell scripts and CI workflow files; `eol=crlf` ONLY for Windows-runtime extensions that actually exist in the repo (`.bat`/`.cmd`/`.ps1`/`.reg`). Repos without any `.gitattributes` get the full file.
4. `git add --renormalize .` — stages only blobs whose content actually changes; a pure EOL swap shows equal insertions/deletions in `--stat`.
5. Force the worktree to LF too: `git checkout-index -f --all` — renormalize updates the index but disk copies can stay CRLF, so editors keep tripping.
6. Verify before commit: `git ls-files --eol | grep -E 'i/(crlf|mixed)'` → empty output.

## Pitfalls

- `git add --renormalize --dry-run .` overreports on older git (lists every text path); trust the real staged count after the actual renormalize, not the dry run.
- `eol=crlf` forces CRLF on checkout on EVERY platform, Linux included — intended only for Windows-runtime files; future Linux edits to those few files are CRLF by design.
- If the hook's venv is missing, commit with `--no-verify` and DISCLOSE it (CI/dev machine runs the real hooks).
- After the merge, other clones self-heal on `git pull`: `text=auto` makes a CRLF worktree compare clean against the new LF blobs — no manual renormalize needed on other machines.

## Report to the user

- Evidence of zero content change: staged file count + symmetric N/N insertion/deletion stat.
- State explicitly which repo steps are local-only vs pushed/PR'd (per-repo AGENTS.md governs push/PR consent).
- Disclose every `--no-verify` deviation.
