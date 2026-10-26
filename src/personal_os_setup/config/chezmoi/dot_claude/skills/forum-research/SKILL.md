---
name: forum-research
description: Use when researching what Reddit/other forums say about X.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Forum & community research (Reddit, Hacker News, project forums)

## When to Use

- "Search Reddit and other forums carefully", "is there a simpler alternative to X", "is X worth using", "does X
  actually work in practice" — the *community verdict and real-world experience*, not the project's own docs.

## Procedure

1. **Search the pain, not the product.** Query the constraint that made the user look ("simpler than virt-manager", "no root", "instead of a VM", "no libvirt", "throwaway VM") — the product name alone returns release announcements and one-line praise. Run the name query plus 2-3 pain queries.
2. **Reach the sources through their APIs, not their HTML** (exact URLs + a copy-paste fetcher: `references/community-apis.md`):
   - Reddit → the PullPush API (submission search, comment search, and `link_id=t3_<id>` for one thread's comments).
   - Hacker News → the Algolia API (`tags=comment|story`, then `/api/v1/items/<id>` for the whole thread).
   - Project/vendor forums, AUR comment threads, GitHub issues and wikis → ordinary `web_search` + `web_extract`; this is where version-specific breakage and packaging caveats live (the ones worth reading directly are listed at the end of `references/community-apis.md`).
3. **Fetch with `curl`/`python3` in the terminal**, one query per request, each response written to a JSON file under the scratch dir; aggregate and filter in a second pass (`curl`, `python3`, `jq` are all present).
   - Don't loop fetches inside one `browser_exec` `js()` await — the CDP timeout (~5 s) kills it mid-loop; batch work belongs in the terminal.
   - Keep the query list as `(name, kind, query)` tuples and call the fetcher inside the loop. Splatting a dict of *results* back into the fetcher silently feeds a 25-element list as positional args and wastes the run.
4. **Filter before printing** so context isn't flooded: top items by score as `subreddit + score + ≤300-char body`, dropping bodies under ~60 chars (link-only noise). Keep the raw JSON on disk so a follow-up question re-reads it instead of re-fetching.
5. **Report short.** Lead with the answer ("yes — X, and it removes A and B"), then 2-4 ranked bullets: option → what it removes → one community quote as evidence → the tradeoff. The long tail (full quotes, links, command recipes) goes into the repo doc or skill, never the chat — this user reads a few sentences per point, not paragraphs.

## Pitfalls

- **The site itself may be network-blocked from this box** — a "blocked by network security" page instead of
  content, in the browser and in the page extractor alike. Try the API recipe in `references/community-apis.md`
  first (that is what it exists for); if the host is unreachable end to end, stop retrying HTML and take the
  report from search-result snippets plus the sources that do extract cleanly: Hacker News threads, the project's
  own wiki and man pages, vendor/support forums, AUR comment threads, GitHub issues. For "does X actually work",
  the project's *Known issues* wiki section and its issue tracker outrank any forum thread.
- **Score ≠ correctness.** The valuable comments name a concrete breakage, command or version ("X 4.9.7 is broken with QEMU 10"), not the upvoted praise. Search for those terms explicitly.
- **Check packaging and version caveats before recommending.** AUR / GitHub comment threads surface dependency-version breakage the project README never mentions; on a rolling distro, read the comment thread of the package you are about to suggest.
- **Community claim vs upstream docs will disagree; settle it in the docs.** Does the tool need root? a daemon? group membership plus a re-login? Those mechanics *are* the simplification the user is asking about — verify them in the project's own docs before asserting them.
- **Rank for this user:** prefer options that keep remote access and add no new service to maintain; order by how much they remove from what already exists (smallest-change option first), and say plainly when nothing simpler exists instead of padding the list.
- **Simpler for the user's repo ≠ interesting in general.** An alternative that leaves existing make targets, inventory or CI silently out of sync is not simpler — name the migration cost with the option.
