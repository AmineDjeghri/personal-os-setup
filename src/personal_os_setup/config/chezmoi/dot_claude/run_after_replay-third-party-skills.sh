#!/bin/bash
# Replay the committed third-party (npx) skill lock: third-party-skills.lock.json at the repo root.
#
# ONE implementation for both callers: chezmoi (run_after_, every apply) and `make skills-thirdparty-replay`.
# Plain shell on purpose -- no chezmoi template variables -- so `bash <this file>` behaves the same
# either way.
#
# NOTE: there is deliberately NO run_ script that copies the authored skills. They are ordinary
# managed files under dot_claude/skills/, so `chezmoi apply` already deploys them. The only thing
# chezmoi cannot do is install the npx-tracked skills; that is all this script does. Do not add
# a second script for the copy.
#
# Why run_after_ and NOT run_onchange_: chezmoi keys run_onchange_ on the script's own content, and a
# template-free file never changes, so it would run once and never again -- a lock edit would not
# reach `chezmoi apply` (verified with chezmoi 2.72). So chezmoi runs this on every apply and the
# script decides: it hashes the lock (plus AGENT) at runtime and compares it with a stamp file;
# unchanged -> do nothing, exit 0. The stamp is written only after every entry was replayed, so a
# failure (or an entry with no source) is retried on the next apply. FORCE=1 ignores the stamp (the
# make target sets it: an explicit replay always replays). Hand-deleted skills are NOT restored by
# a plain apply -- run `make skills-thirdparty-replay` for that.
#
# No notify() helper, unlike the desktop scripts in dot_config/: those notify-send for a user at
# the desktop; this one also runs on headless boxes, so it only logs (warnings to stderr).
# Needs the lock reachable by walking up from the chezmoi source dir, i.e. the source must live
# inside the repo checkout; otherwise set LOCK=<path>.
#
# Env: AGENT  target agent for `npx skills add -a` (default claude-code)
#      LOCK   lock path (default: found by walking up from the chezmoi source dir / this script)
#      FORCE  1 = skip the stamp check
#      STAMP  stamp path (default ~/.cache/personal-os-setup/skills-replay.stamp)
set -eu

# Windows (Git Bash/MSYS/Cygwin): nothing to do. A template guard on .chezmoi.os is impossible here.
case "$(uname -s 2>/dev/null)" in MINGW*|MSYS*|CYGWIN*) exit 0 ;; esac

AGENT=${AGENT:-claude-code}
FORCE=${FORCE:-0}
STAMP=${STAMP:-${XDG_CACHE_HOME:-$HOME/.cache}/personal-os-setup/skills-replay.stamp}

log() { printf 'third-party-skills: %s\n' "$*"; }
warn() { log "$*" >&2; }

# Walk up from $1 until a directory holds the lock; print the lock path.
find_lock() {
	dir=$1
	while [ -n "$dir" ]; do
		if [ -f "$dir/third-party-skills.lock.json" ]; then
			printf '%s/third-party-skills.lock.json\n' "$dir"
			return 0
		fi
		[ "$dir" = / ] && break
		parent=$(dirname "$dir")
		[ "$parent" = "$dir" ] && break
		dir=$parent
	done
	return 1
}

if [ -z "${LOCK:-}" ]; then
	# chezmoi runs a COPY of this script from a temp dir, so ${0%/*} is useless there; it exports
	# CHEZMOI_SOURCE_DIR instead. From make, ${0%/*} is the real location in the repo.
	here=$(cd "${0%/*}" 2>/dev/null && pwd -P) || here=
	LOCK=$(find_lock "${CHEZMOI_SOURCE_DIR:-$here}" || { [ -n "$here" ] && find_lock "$here"; }) || LOCK=
fi

# Nothing to replay without Node (the webui container ships none). Exit 0: there is nothing this
# script can do there, and the lock hash re-triggers it on a machine that has npx.
if ! command -v npx >/dev/null 2>&1; then
	warn "WARNING npx not found -- skipping third-party skills replay on this machine"
	exit 0
fi
command -v jq >/dev/null 2>&1 || { warn "jq is required to read the lock but is not installed"; exit 1; }
[ -n "$LOCK" ] && [ -f "$LOCK" ] || { warn "lock not found (set LOCK=<path>)"; exit 1; }

sum=$(sha256sum "$LOCK" | cut -d' ' -f1)-$AGENT
if [ "$FORCE" != 1 ] && [ -f "$STAMP" ] && [ "$(cat "$STAMP")" = "$sum" ]; then
	log "lock unchanged since last successful replay -- nothing to do"
	exit 0
fi

rc=0
skipped=0
for name in $(jq -r '.skills | keys[]' "$LOCK"); do
	src=$(jq -r --arg n "$name" '.skills[$n].source // .skills[$n].sourceUrl // empty' "$LOCK")
	if [ -z "$src" ]; then
		warn "SKIP $name (no source recorded)"
		skipped=1
		continue
	fi
	if npx -y skills add "$src" -s "$name" -a "$AGENT" -g -y --copy; then
		log "OK $name"
	else
		warn "FAIL $name"
		rc=1
	fi
done

# Stamp only a fully clean run; an unwritable cache dir must not fail a successful replay.
if [ "$rc" -eq 0 ] && [ "$skipped" -eq 0 ]; then
	{ mkdir -p "$(dirname "$STAMP")" && printf '%s\n' "$sum" >"$STAMP"; } 2>/dev/null ||
		warn "WARNING cannot write stamp $STAMP -- the replay will repeat on every apply"
fi
exit "$rc"
