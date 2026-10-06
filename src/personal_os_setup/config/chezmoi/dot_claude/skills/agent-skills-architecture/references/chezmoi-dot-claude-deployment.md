# Deploying dot_claude → /config/.claude/skills (HA container)

Deploy ONLY the shared skills dir — never a full chezmoi apply here. The working invocation (`--source` = repo
ROOT, run from HOME) is owned by the `skill-deployment` skill.

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
- Idempotent: re-run for the skills changed by a `git pull`. Needed only when the source dir is not a git repo.

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
