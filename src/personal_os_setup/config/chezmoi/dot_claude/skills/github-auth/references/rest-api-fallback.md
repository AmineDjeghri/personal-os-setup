# GitHub REST API fallback (no `gh`) — the single fallback for the whole GitHub family

Use only when `gh` cannot be installed; otherwise install `gh` (see `../SKILL.md`) and use `gh api` / the `gh` one-liners
in the other GitHub skills. The other GitHub skills point here.

## Setup

- `source scripts/gh-env.sh` (relative to the `github-auth` skill) sets `GH_AUTH_METHOD`, `GITHUB_TOKEN`, `GH_OWNER`, `GH_REPO`.
- Every `gh api <path>` maps to `curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/<path>`
  (endpoint reference: https://docs.github.com/rest).

## Traps

- **Merge methods:** `PUT /repos/$GH_OWNER/$GH_REPO/pulls/<n>/merge` with `{"merge_method": "merge|squash|rebase"}`.
- **Auto-merge is GraphQL-only** (REST has no endpoint, and the repo must have it enabled): read the PR's `node_id`, then
  `POST https://api.github.com/graphql` with `mutation { enablePullRequestAutoMerge(input: {pullRequestId: "<node_id>", mergeMethod: SQUASH}) { clientMutationId } }`.
- **Review `event` values:** an atomic review (`POST /pulls/<n>/reviews`) takes `event: APPROVE|REQUEST_CHANGES|COMMENT`,
  the PR head `commit_id` and a `comments[]` array of `{path, line, body}`.
- **`line` = the line number in the NEW file** (`side: RIGHT`, the default); `side: LEFT` for a deleted line. A single
  inline comment (`POST /pulls/<n>/comments`) needs `commit_id` + `path` + `line` + `side`.
- **Release assets upload to `uploads.github.com`**, not the API host (`https://uploads.github.com/repos/$GH_OWNER/$GH_REPO/releases/<id>/assets?name=<file>`).
- **Commit statuses and check-runs are separate endpoints** (`/commits/<sha>/statuses` vs `/commits/<sha>/check-runs`) — read both to judge CI state.
- **`GET /issues` also returns pull requests** — drop items that carry a `pull_request` key.
- **Branch protection has no `gh` subcommand** — REST only (`gh api -X PUT repos/{o}/{r}/branches/{b}/protection` with this body):

```bash
curl -s -X PUT -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$GH_OWNER/$GH_REPO/branches/main/protection \
  -d '{
    "required_status_checks": {"strict": true, "contexts": ["ci/test", "ci/lint"]},
    "enforce_admins": false,
    "required_pull_request_reviews": {"required_approving_review_count": 1},
    "restrictions": null
  }'
```
