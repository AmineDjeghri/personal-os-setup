# Community APIs that work from this box

## Reddit — PullPush (Pushshift successor)

```
GET https://api.pullpush.io/reddit/search/submission/?q=<urlencoded>&size=25&sort=desc&sort_type=score
GET https://api.pullpush.io/reddit/search/comment/?q=<urlencoded>&size=25&sort=desc&sort_type=score
GET https://api.pullpush.io/reddit/search/comment/?link_id=t3_<submission_id>&size=25   # one whole thread
```

- submission fields: `subreddit`, `title`, `selftext`, `score`, `num_comments`, `id`
- comment fields: `subreddit`, `body`, `score`, `link_title`
- send a `User-Agent` header; sleep ~1 s between queries.

Fetcher pattern (write to the scratch dir, run with `python3`):

```python
import json, urllib.request, urllib.parse, time

def pp(kind, q, size=25, **kw):
    url = (f"https://api.pullpush.io/reddit/search/{kind}/?q={urllib.parse.quote(q)}"
           f"&size={size}&sort=desc&sort_type=score")
    for k, v in kw.items():
        url += f"&{k}={v}"
    req = urllib.request.Request(url, headers={"User-Agent": "research/1.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)["data"]

for name, kind, q in [("sub_quickemu", "submission", "quickemu"),
                      ("com_noroot", "comment", '"simpler than" "no root"')]:
    json.dump(pp(kind, q), open(f"/path/to/scratch/{name}.json", "w"))
    time.sleep(1.2)
```

## Hacker News — Algolia

```
GET https://hn.algolia.com/api/v1/search?query=<q>&tags=comment&hitsPerPage=10   # tags=story for submissions
GET https://hn.algolia.com/api/v1/items/<objectID>                              # full thread
```

- search hit fields: `story_title` / `title`, `author`, `comment_text` (strip tags, unescape `&#x2F;` etc.)
- a thread's comments arrive as nested `children[].text`; slice to the first ~12 and truncate each.
- `story` hits carry `points`, `num_comments`, `url` — useful for judging whether a project is actually used.

## Fallbacks when a source refuses a direct fetch

- `www.reddit.com` / `old.reddit.com` JSON and HTML can answer 403 to this box, and the redlib/libreddit mirrors can fail to resolve. Route Reddit reads through PullPush first; retrying the HTML endpoints wastes calls.
- If PullPush has no body for a thread that matters, `web_search` snippets over `site:reddit.com` still carry usable comment text to quote.
- `web_extract` on `news.ycombinator.com/item?id=…` sometimes returns nothing; the Algolia `/api/v1/items/<id>` endpoint is the reliable read for the same thread.

## Project / vendor sources worth a direct `web_extract`

AUR and distro Discourse forum threads, project wikis (GitHub wiki pages render poorly through extractors — prefer a manpage mirror such as `manpages.debian.org/<pkg>/<page>`), and `archlinux.org/packages` / `aur.archlinux.org/packages` for packaging status.
