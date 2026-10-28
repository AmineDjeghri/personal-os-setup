#!/bin/bash
# Link only repo-authored names after chezmoi has deployed their ordinary files.
# The zz name also sorts after skills/ during targeted per-entry application.
# Select the whole .claude folder so this script is included in targeted applies.
set -eu
here=$(cd "${0%/*}" && pwd -P)
source_dir=${CHEZMOI_SOURCE_DIR:-$here}
if [ -f "$source_dir/dot_claude/skills_support.py" ]; then
    source_dir=$source_dir/dot_claude
elif [ -f "$source_dir/src/personal_os_setup/config/chezmoi/dot_claude/skills_support.py" ]; then
    source_dir=$source_dir/src/personal_os_setup/config/chezmoi/dot_claude
elif [ -f "$here/skills_support.py" ]; then
    source_dir=$here
else
    echo 'skills: shared helper not found in chezmoi source' >&2
    exit 1
fi
helper=$source_dir/skills_support.py
exec "${SKILLS_PYTHON:-python3}" "$helper" link \
    --source "$source_dir/skills" \
    --claude "${SKILLS_DST:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills}" \
    --codex "${SKILLS_CODEX_DST:-$HOME/.agents/skills}"
