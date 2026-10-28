#!/usr/bin/env bash
# Release steps, shared by a laptop (make release*) and GitHub Actions (main-release.yml, dev-release.yml).
#
#   scripts/release.sh version   # guards, then semantic-release: version, CHANGELOG.md, commit, tag, push, GitHub release
#   scripts/release.sh assets    # attach dist/ wheel + sdist of the current version to the GitHub release
#   scripts/release.sh release   # version, then (if HEAD got the tag) make build-package, then assets
#
# GitHub token, in this order: GH_TOKEN, the `gh auth login` session, a hidden prompt (terminal only).
# The token is never printed; it only travels through the environment.
set -euo pipefail

: "${UV:=uv}"
GH_HOST="${GH_HOST:-${GITHUB_SERVER_URL:+${GITHUB_SERVER_URL#https://}}}"
GH_HOST="${GH_HOST:-github.com}"
export GH_HOST

die() { echo "ERROR: $*" >&2; exit 1; }
output() { [[ -z "${GITHUB_OUTPUT:-}" ]] || echo "$1" >>"$GITHUB_OUTPUT"; }

github_token() {
  [[ -z "${GH_TOKEN:-}" ]] || return 0
  GH_TOKEN="$(gh auth token --hostname "$GH_HOST" 2>/dev/null || true)"
  if [[ -z "$GH_TOKEN" ]]; then
    [[ -t 0 ]] || die "no GitHub token: set GH_TOKEN or run: gh auth login --hostname $GH_HOST"
    echo "Not logged in: run 'gh auth login --hostname $GH_HOST' once, or paste a token now."
    read -rsp "GitHub token for $GH_HOST (repo scope, input hidden): " GH_TOKEN
    echo
    [[ -n "$GH_TOKEN" ]] || die "no token given"
  fi
  export GH_TOKEN
}

cmd_version() {
  local branch version
  branch="$(git rev-parse --abbrev-ref HEAD)"
  case "$branch" in
    main | dev) ;;
    *) die "release from main or dev only (on $branch)" ;;
  esac
  [[ -z "$(git status --porcelain)" ]] || die "uncommitted changes: commit or stash them first"
  git fetch -q origin "$branch"
  [[ "$(git rev-parse HEAD)" == "$(git rev-parse "origin/$branch")" ]] ||
    die "$branch is not in sync with origin/$branch: pull or push first"
  github_token
  if [[ -z "${GIT_COMMIT_AUTHOR:-}" ]]; then
    GIT_COMMIT_AUTHOR="$(git config user.name) <$(git config user.email)>"
  fi
  export GIT_COMMIT_AUTHOR
  export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}." # the commit parser is scripts/emoji_commit_parser.py

  version="$("$UV" run --group dev semantic-release version --print 2>/dev/null | tr -d '[:space:]')"
  if [[ -z "$version" ]] || git rev-parse -q --verify "refs/tags/v$version" >/dev/null; then
    echo "No releasable commit since the last tag (only chore/docs/refactor/...): nothing to release."
    output "released=false"
    return 0
  fi
  # The release commit must not run the pre-commit hooks: disable them for this call only.
  GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null \
    "$UV" run --group dev semantic-release -v version
  echo "Released v$version"
  output "released=true"
  output "version=$version"
}

cmd_assets() {
  local version dist tag
  github_token
  version="$("$UV" version --short)"
  dist="$("$UV" version | awk '{print $1}' | tr - _)"
  tag="v$version"
  local files=("dist/$dist-$version-py3-none-any.whl" "dist/$dist-$version.tar.gz")
  for f in "${files[@]}"; do
    [[ -f "$f" ]] || die "$f not found: run make build-package"
  done
  if ! gh release view "$tag" >/dev/null 2>&1; then
    local flags=(--verify-tag --title "$tag" --generate-notes)
    if [[ "$version" == *-* ]]; then flags+=(--prerelease); fi
    gh release create "$tag" "${flags[@]}"
  fi
  gh release upload "$tag" "${files[@]}" --clobber
  echo "Attached to $tag: ${files[*]}"
}

cmd_release() {
  local version
  cmd_version
  version="$("$UV" version --short)"
  if ! git tag --points-at HEAD | grep -qx "v$version"; then
    echo "Nothing released: stopping."
    return 0
  fi
  make --no-print-directory build-package
  cmd_assets
}

case "${1:-}" in
  version) cmd_version ;;
  assets) cmd_assets ;;
  release) cmd_release ;;
  *) die "usage: $0 version|assets|release" ;;
esac
