#!/bin/bash
# Shared by chezmoi and make. Authored files remain ordinary chezmoi-managed files.
# Installs only what is missing, broken, unlinked or out of step with the lock (FORCE=1: everything).
# Each skill is installed with ONE npx call naming every selected agent: only then does npx keep a
# canonical copy under ~/.agents/skills and link ~/.claude/skills/<name> to it (a single-agent call
# writes an independent copy and replaces an existing link). STRICT=1 (make) fails on missing
# tooling, the optional chezmoi replay SKIPs instead. Every install is checked afterwards.
set -eu
set -o pipefail

log() { printf 'third-party-skills: %s\n' "$*"; }
fail_or_skip() {
    if [ "${STRICT:-0}" = 1 ]; then log "ERROR $*" >&2; exit 1; fi
    log "SKIPPED $* (no successful installation recorded)" >&2
    exit 0
}

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
if [ -z "${LOCK:-}" ]; then
    dir=$source_dir
    while [ ! -f "$dir/third-party-skills.lock.json" ]; do
        [ "$dir" != / ] || fail_or_skip "repository lock not found (set LOCK=<path>)"
        dir=$(dirname "$dir")
    done
    LOCK=$dir/third-party-skills.lock.json
fi
PYTHON=${SKILLS_PYTHON:-python3}
command -v "$PYTHON" >/dev/null 2>&1 || fail_or_skip "python3 is required"
agents=$("$PYTHON" "$helper" agents --agents "${AGENT:-${AGENTS:-claude-code codex}}")
claude=${SKILLS_DST:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills}
codex=${SKILLS_CODEX_DST:-$HOME/.agents/skills}
state=${XDG_STATE_HOME:-$HOME/.local/state}
find_live() {
    live=${LIVE_SKILLS_LOCK:-}
    if [ -z "$live" ]; then
        live=$state/skills/.skill-lock.json
        [ -f "$live" ] || live=$HOME/.agents/.skill-lock.json
    fi
}
find_live
helper_run() {
    command=$1; shift
    "$PYTHON" "$helper" "$command" --lock "$LOCK" --live-lock "$live" \
        --agents "$agents" --claude "$claude" --codex "$codex" "$@"
}
todo_args=()
[ "${FORCE:-0}" != 1 ] || todo_args+=(--all)
pending=$(helper_run todo ${todo_args[@]+"${todo_args[@]}"})
if [ -z "$pending" ]; then
    log "all third-party skills are installed -- nothing to do"
    exit 0
fi
command -v npx >/dev/null 2>&1 || fail_or_skip "npx is required"
# Validate the lock before interpolating any of its names into installation paths.
helper_run plan
agent_args=()
for agent in $agents; do agent_args+=(-a "$agent"); done
rc=0
while IFS=$'\t' read -r name src; do
    [ -n "$name" ] || continue
    # npx must not read the loop's stdin; it also exits 0 when it cancels, so check the result.
    if npx -y skills add "$src" -s "$name" "${agent_args[@]}" -g -y </dev/null &&
        "$PYTHON" "$helper" installed --agents "$agents" --name "$name" \
            --claude "$claude" --codex "$codex"; then
        log "OK $name ($agents)"
    else
        log "FAIL $name ($agents)" >&2
        rc=1
    fi
done <<< "$pending"
[ "$rc" -eq 0 ] || exit "$rc"
# The CLI writes its live lock during install; locate it again on a fresh machine.
[ -n "${LIVE_SKILLS_LOCK:-}" ] || find_live
helper_run verify
