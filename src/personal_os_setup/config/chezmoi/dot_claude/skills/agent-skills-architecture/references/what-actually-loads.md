# What actually loads (summary — probes and internals in the audit skill)

Precedence: project → local own store → `skills.create_dir` → `external_dirs`; a project skill shadows a same-named local/external one. Project skills need a candidate dir at the repo root
AND that root in `skills.trusted_project_dirs` (exact resolved path, no globs, no parent rules) — and the session
must resolve that root at all, which a global `terminal.cwd` (HOME, no `.git` above it) prevents, so trust stays
silently inert for chat sessions. For a repo runbook both agents must see from a
`/config`-rooted session, list its `.agents/skills` in `external_dirs` or promote it to the authored tree. `config.yaml`
refuses file-tool writes ("use 'hermes config' instead") → `hermes config set skills.external_dirs '["/config/.claude/skills","<repo>/.agents/skills"]'`
(read it back with `hermes config get`; effective only in the NEXT session), or hand the user the fenced block when
the path is the user's to approve. Full chain and decisive probes: `hermes-instance-audit` → `references/skill-loading-resolution.md`.
