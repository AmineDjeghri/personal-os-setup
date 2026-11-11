# Pitfalls

- Approval gates: `AGENTS.md`/`CLAUDE.md` and `config.yaml` writes come back BLOCKED on timeout → STOP, report, and
  let the user say "prompt me again" to re-fire the exact patch; never retry it and never route the same edit
  through terminal or another file. Name any blocked call instead of quietly substituting.
- `git commit`/`git push` need per-action approval every time (also in `AGENTS.md`); commit email must match existing commits, never invented.
- Keep shell calls single-purpose — no `$(…)`, `for`, `;`/`&&` chains or `python3 -c …` bundles: one gated link takes the
  whole sequence down, so split a verification bundle into separate calls UP FRONT. Run multi-source research as direct
  `web_extract`/`terminal` calls, not a batch through `execute_code`.
- Destructive cleanup (`rm -rf`, `git clean -f`, a `tar` into a protected path) raises its OWN approval prompt, and a
  timed-out prompt is not consent either → stop, report, re-fire only when the user says so. Keep the backup and the
  delete in ONE command with the backup first, so a timeout leaves nothing half-applied, and state the exact
  file/dir list before each step — deletions are approved per step, not per plan.
- **Ambiguity window breaks loads.** While a live copy and the repo copy co-exist, name-based loading FAILS
  (`Ambiguous skill name '<n>': 2 skills match across your local skills dir and external_dirs`) and the listing
  hides it — verify with `find -L <every root> -path "*<name>/SKILL.md"` (exactly one hit; plain `find` misses a
  skill reached through a `.agents/skills` symlink, so an empty result is not "the skill vanished").
- **Copied scripts and templates must pass the target repo's hooks before the commit** — a verbatim copy routinely
  fails lint/format/YAML hooks (`references/repo-hook-gate.md`), and the staged copy is a SNAPSHOT, and live moves while you port: an edit after staging is not in the port,
  so re-copy if the live file moved on and re-run `make skills-status` immediately before committing.
- **Check BOTH path bases before calling a supporting-file reference broken.** `references/…`/`scripts/…` written
  with a slash are skill-relative; a bare `scripts/<name>.py` in prose is usually the REPO root's own directory —
  test `<skill-dir>/<rel>` and `<repo-root>/<rel>` before calling one broken.
- The webui container has NO Node.js by design — `npx skills` and node CLIs do not exist there (the AGENT container
  does). Deploy authored skills via chezmoi/`make skills-personal-repo-to-live` or install plugin packs with `claude plugin`; do not install Node for this.
- Do not adopt a skill manager that keeps its own library or sync (a second source of truth parallel to the repo → `.claude/skills` flow).
- **A lesson such a pass produces for a deployed skill is SOURCE work.** Repo-deployed names carry `created_by:
  agent`, so its write to the live copy goes through — and then the next deploy either ABORTS on the fresh
  `DIFFERS` or a `FORCE=1` run overwrites the lesson. Write it in the source tree instead, name any drift you
  caused with its file, and if every relevant skill is genuinely protected, report "Nothing to save" PLUS the exact
  edits the repo still needs — never a new overlapping curator skill.
- **A file the source tree no longer has is not automatically stale live content to port back.** Compare size and
  mtime per FILE and ask whether the source-side edit was deliberate: a deleted install snapshot or context dump must
  be dropped (force-deploy), while a live-only reference the source never had is the one to port in.
