#!/usr/bin/env bash
# Shared release implementation: main/dev; checked artifacts precede public publication.
set -euo pipefail
: "${UV:=uv}"
GH_HOST="${GH_HOST:-${GITHUB_SERVER_URL:+${GITHUB_SERVER_URL#https://}}}"
export GH_HOST="${GH_HOST:-github.com}"
RELEASE_READY=false
ARTIFACTS_CHECKED=false

die() { echo "ERROR: $*" >&2; exit 1; }
output() { [[ -z "${GITHUB_OUTPUT:-}" ]] || echo "$1" >>"$GITHUB_OUTPUT"; }
clean_tree() {
  local status
  status="$(git status --porcelain)" || die "could not check working tree status"
  [[ -z "$status" ]] || die "uncommitted changes (a release commit would carry them): commit or stash them first:
$status"
}

github_token() {
  [[ -z "${GH_TOKEN:-}" ]] || return 0
  GH_TOKEN="$(gh auth token --hostname "$GH_HOST" 2>/dev/null || true)"
  if [[ -z "$GH_TOKEN" ]]; then
    [[ -t 0 ]] || die "no GitHub token: set GH_TOKEN or run: gh auth login --hostname $GH_HOST"
    read -rsp "GitHub token for $GH_HOST (input hidden): " GH_TOKEN
    echo
    [[ -n "$GH_TOKEN" ]] || die "no token given"
  fi
  export GH_TOKEN
}

version_tag() {
  VERSION="$("$UV" version --short)"
  TAG="v$VERSION" # Keep the semantic-release spelling; Python artifact names use PEP 440.
}

check_tag() {
  local head local_tag remote_tag
  head="$(git rev-parse HEAD)" || die "could not resolve HEAD"
  local_tag="$(git rev-parse --verify "refs/tags/$TAG^{commit}")" || die "could not resolve local $TAG"
  [[ "$local_tag" == "$head" ]] ||
    die "$TAG must point at the clean checkout being published"
  git fetch -q origin "refs/tags/$TAG"
  remote_tag="$(git rev-parse 'FETCH_HEAD^{commit}')" || die "could not resolve remote $TAG"
  [[ "$remote_tag" == "$head" ]] ||
    die "remote $TAG does not match this checkout"
}

resume_release_tag() {
  local status head local_tag
  # The source guard has already verified the metadata-only release child.
  # A tag lookup error is not evidence that the tag is absent.
  if git ls-remote --exit-code origin "refs/tags/$TAG" >/dev/null; then
    git fetch -q origin "refs/tags/$TAG:refs/tags/$TAG"
  else
    status=$?
    [[ "$status" == 2 ]] || die "could not check remote $TAG"
    make --no-print-directory test-installation
    clean_tree
    if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
      head="$(git rev-parse HEAD)" || die "could not resolve HEAD"
      local_tag="$(git rev-parse "refs/tags/$TAG^{commit}")" || die "could not resolve local $TAG"
      [[ "$local_tag" == "$head" ]] ||
        die "local $TAG does not match the verified release commit"
    else
      status=$?
      [[ "$status" == 1 ]] || die "could not check local $TAG"
      GIT_COMMITTER_NAME="$(git log -1 --format=%cn)" \
        GIT_COMMITTER_EMAIL="$(git log -1 --format=%ce)" \
        GIT_COMMITTER_DATE="$(git log -1 --format=%cI)" \
        git tag -a "$TAG" -m "$TAG" HEAD
    fi
    github_token
    git push origin "refs/tags/$TAG"
    ARTIFACTS_CHECKED=true
  fi
  check_tag
}

cmd_version() {
  local branch next source head remote_head release_sha
  branch="$(git rev-parse --abbrev-ref HEAD)"
  [[ "$branch" == main || "$branch" == dev ]] || die "release from main or dev only (on $branch)"
  clean_tree
  git fetch -q origin "$branch"
  head="$(git rev-parse HEAD)" || die "could not resolve HEAD"
  remote_head="$(git rev-parse "origin/$branch")" || die "could not resolve origin/$branch"
  [[ "$head" == "$remote_head" ]] ||
    die "$branch is not in sync with origin/$branch (ahead/behind: $(git rev-list --left-right --count "$branch...origin/$branch")):
pull or push first"
  if [[ "${GITHUB_ACTIONS:-}" == true ]]; then
    release_sha="${GITHUB_SHA:-}"
    [[ -n "$release_sha" ]] || die "GitHub Actions requires GITHUB_SHA"
  else
    release_sha="$head"
  fi
  source="$("$UV" run --no-sync python scripts/check_release_source.py "$release_sha")"
  [[ "$source" == source || "$source" == release ]] || die "unknown release source state"
  version_tag
  # Branch and tag pushes are separate: recover the tag before resuming asset publication.
  if [[ "$source" == release ]]; then
    resume_release_tag
    RELEASE_READY=true
    echo "Resuming $TAG: verify artifacts and finish publication."
  elif [[ "$(git rev-parse -q --verify "refs/tags/$TAG^{commit}" || true)" == "$(git rev-parse HEAD)" ]]; then
    check_tag
    RELEASE_READY=true
    echo "Resuming $TAG: verify artifacts and finish publication."
  else
    github_token
    export GIT_COMMIT_AUTHOR="${GIT_COMMIT_AUTHOR:-$(git config user.name) <$(git config user.email)>}"
    export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}."
    next="$(env -u GITHUB_OUTPUT "$UV" run --no-sync semantic-release version --print)"
    if [[ -z "$next" ]] || git rev-parse -q --verify "refs/tags/v$next" >/dev/null; then
      echo "No releasable commits since the last tag."
      output "released=false"
      return
    fi
    # build_command updates the lock and runs make test-installation before commit/tag/push.
    GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null \
      env -u GITHUB_OUTPUT "$UV" run --no-sync semantic-release -v version --no-vcs-release
    version_tag
    [[ "$VERSION" == "$next" ]] || die "semantic-release version differs from its preview"
    clean_tree
    check_tag
    RELEASE_READY=true
    ARTIFACTS_CHECKED=true
  fi
  output "released=true"
  output "version=$VERSION"
}

cmd_assets() (
  clean_tree
  version_tag
  check_tag
  local paths file name names asset_tmp draft
  local files=() missing=()
  paths="$("$UV" run --no-sync python scripts/check_artifacts.py)"
  while IFS= read -r file; do files+=("$file"); done <<< "$paths"
  if [[ "$ARTIFACTS_CHECKED" != true ]]; then make --no-print-directory test-wheel; fi
  github_token
  if ! names="$(gh release view "$TAG" --json assets --jq '.assets[].name')"; then
    local flags=(--draft --verify-tag --title "$TAG" --generate-notes)
    if [[ "$("$UV" run --no-sync python scripts/check_artifacts.py --prerelease)" == true ]]; then
      flags+=(--prerelease)
    fi
    gh release create "$TAG" "${flags[@]}"
    names="$(gh release view "$TAG" --json assets --jq '.assets[].name')"
  fi
  draft="$(gh release view "$TAG" --json isDraft --jq '.isDraft')"
  asset_tmp="$(mktemp -d)"
  trap 'rm -rf -- "$asset_tmp"' EXIT
  # Compare all existing assets first. Never replace a different published artifact.
  for file in "${files[@]}"; do
    name="${file##*/}"
    if printf '%s\n' "$names" | grep -Fxq "$name"; then
      gh release download "$TAG" --pattern "$name" --dir "$asset_tmp"
      cmp -s "$file" "$asset_tmp/$name" || die "existing release asset differs: $name"
    else
      missing+=("$file")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    gh release upload "$TAG" "${missing[@]}"
  fi
  # Download and compare the complete remote pair before publishing a draft.
  for file in "${files[@]}"; do
    name="${file##*/}"
    if [[ ! -f "$asset_tmp/$name" ]]; then
      gh release download "$TAG" --pattern "$name" --dir "$asset_tmp"
    fi
    cmp -s "$file" "$asset_tmp/$name" || die "uploaded release asset differs: $name"
  done
  if [[ "$draft" == true ]]; then gh release edit "$TAG" --draft=false; fi
  echo "Verified release $TAG: ${files[*]}"
)

cmd_release() {
  cmd_version
  [[ "$RELEASE_READY" == true ]] || return 0
  if [[ "$ARTIFACTS_CHECKED" != true ]]; then make --no-print-directory build-package; fi
  cmd_assets
}

case "${1:-}" in
  version) cmd_version ;;
  assets) cmd_assets ;;
  release) cmd_release ;;
  *) die "usage: $0 version|assets|release" ;;
esac
