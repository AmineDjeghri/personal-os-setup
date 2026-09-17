# Deploying dot_claude → /config/.claude/skills (HA container)

Verified Aug/Sep 2026 on the Hermes HA addon container. Deploy ONLY the shared skills dir — never a full
chezmoi apply here.

## Working invocation (2026-09 — the repo-level form now works)

The `.chezmoiroot` fix landed in the repo, so the git-backed SOURCE ROOT + a target name resolves:

```bash
REPO=/config/workspace/personal-os-setup
cd ~ && chezmoi apply -v --force --source "$REPO" .claude
```

- `--source` = the repo ROOT (never the nested `config/chezmoi` dir) and run it from HOME — relative targets
  resolve against CWD.
- This is the form the repo's `make skills-deploy` mirrors for machines without chezmoi.
- The nested `config/chezmoi` dir must never carry its own `.chezmoiroot`: the TUI passes that dir directly as
  `--source`, so a second redirect breaks the app's deploy path.

## File-level fallback (non-git sources)

```bash
S=/config/workspace/personal-os-setup/src/personal_os_setup/config/chezmoi
chezmoi --source "$S" apply -v --force --parent-dirs --refresh-externals=never \
  --source-path "$S/dot_claude/skills/coding-workflow/SKILL.md" \
  --source-path "$S/dot_claude/skills/repo-conventions/SKILL.md"
```

- FILE-level targets + `--source-path` + ABSOLUTE source paths work on any source dir.
- If it hangs mid-apply (observed once with `--parent-dirs` creating dirs), retry the missing file alone without
  `--parent-dirs` (the dirs already exist).
- `chezmoi managed --source "$S"` lists entries (live scan); `chezmoi cat`/`apply <target>` consult target
  resolution, which is what fails on a non-git source.
- Idempotent: re-run for the skills changed by a `git pull`.

## Why the scoped forms failed (debugging trail — don't redo it)

1. `chezmoi apply --source $S .claude` → "not managed" (target-path form)
2. `chezmoi apply --source $S dot_claude` → "not managed" (source-name form)
3. `--source-path dot_claude` / `--source-path $S/dot_claude` (dir-level) → EMPTY (silently no-op)
4. Removing the state DB (~/.config/chezmoi/chezmoistate.boltdb, backed up as .bak-<ts>) → NO change: red herring.
   Even OLD entries (dot_zshrc) fail target lookup on such a source.
5. FILE-level `--source-path $S/dot_claude/skills/<name>/SKILL.md` → WORKS (shows a create diff, applies cleanly).

Conclusion at the time: chezmoi v2.72.0 target-argument resolution fails for every entry with a non-git nested
source dir; file-level `--source-path` bypasses it. The 2026-09 `.chezmoiroot` fix removes the constraint for the
repo root, but the file-level form stays the fallback wherever the source dir is not a git repo.

## Never full-apply in the container

The package source also contains the user's desktop config: `dot_config/hypr` (Hyprland), ghostty, mpv, OpenRGB,
coolercontrol, gpu-screen-recorder, mimeapps… A full apply would dump all of it into `/config`.

## Notes

- The TUI (`tasks/system/chezmoi.py`) invokes
  `chezmoi --source <chezmoi_source_dir()> apply -v --force --parent-dirs --refresh-externals=never <targets>`,
  where `chezmoi_source_dir()` = the nested source dir via importlib.resources.
- `/config/.claude/` also holds Claude Code's own credentials/sessions — deploy only into the `skills/` subdir,
  never touch the rest.
- chezmoi binary: `/config/.local/bin/chezmoi` (v2.72.0).
