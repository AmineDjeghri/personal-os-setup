#!/bin/bash
# Shared by chezmoi and make. Authored files remain ordinary chezmoi-managed files.
# Explicit make replay sets FORCE=1 and STRICT=1. Optional chezmoi replay may SKIP
# unavailable tooling, but never stamps a skipped/failed/unverified installation.
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
command -v npx >/dev/null 2>&1 || fail_or_skip "npx is required"
command -v jq >/dev/null 2>&1 || fail_or_skip "jq is required"
# No Windows no-op: Git Bash follows this same path and surfaces any tool failure.
agents=$("$PYTHON" "$helper" agents --agents "${AGENT:-${AGENTS:-claude-code codex}}")
claude=${SKILLS_DST:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills}
codex=${SKILLS_CODEX_DST:-$HOME/.agents/skills}
state=${XDG_STATE_HOME:-$HOME/.local/state}
live=${LIVE_SKILLS_LOCK:-}
if [ -z "$live" ]; then
    live=$state/skills/.skill-lock.json
    [ -f "$live" ] || live=$HOME/.agents/.skill-lock.json
fi
receipts=${SKILLS_RECEIPTS:-$state/personal-os-setup/skills-installed.json}
STAMP=${STAMP:-${XDG_CACHE_HOME:-$HOME/.cache}/personal-os-setup/skills-replay.stamp}
# Python supplies portable SHA-256 on macOS, Linux and Windows Git Bash.
sum=$("$PYTHON" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$LOCK")-$agents
verify() {
    "$PYTHON" "$helper" "$1" --lock "$LOCK" --live-lock "$live" \
        --agents "$agents" --claude "$claude" --codex "$codex" --receipts "$receipts"
}
# Even an unchanged lock must have every agent's installed files and receipts.
if [ "${FORCE:-0}" != 1 ] && [ -f "$STAMP" ] && [ "$(cat "$STAMP")" = "$sum" ] && verify verify; then
    log "lock and installed content unchanged -- nothing to do"
    exit 0
fi
# Validate the lock before interpolating any of its names into installation paths.
"$PYTHON" "$helper" plan --lock "$LOCK" --agents "$agents" --claude "$claude" --codex "$codex"
rc=0
for name in $(jq -r '.skills | keys[]' "$LOCK"); do
    src=$(jq -r --arg n "$name" '.skills[$n].source' "$LOCK")
    for agent in $agents; do
        if npx -y skills add "$src" -s "$name" -a "$agent" -g -y --copy; then
            log "OK $agent/$name"
        else
            log "FAIL $agent/$name" >&2
            rc=1
        fi
    done
done
[ "$rc" -eq 0 ] || exit "$rc"
# The CLI writes its live lock during install; locate it again on a fresh machine.
if [ -z "${LIVE_SKILLS_LOCK:-}" ]; then
    live=$state/skills/.skill-lock.json
    [ -f "$live" ] || live=$HOME/.agents/.skill-lock.json
fi
verify record
verify verify
{ mkdir -p "$(dirname "$STAMP")" && printf '%s\n' "$sum" > "$STAMP"; } 2>/dev/null ||
    log "WARNING cannot write stamp; replay will repeat" >&2
