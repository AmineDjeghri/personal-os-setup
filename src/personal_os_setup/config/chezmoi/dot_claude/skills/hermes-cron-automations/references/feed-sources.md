# Source access: what still works for a feed/news digest

Decision notes for choosing an access route per source class on this box. **Liveness facts age
fast** — treat the dates below as "verify before relying", and re-probe before promising a source
works. The probe is always the same shape:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -A "<tool>/<ver> (personal feed reader)" --max-time 20 "$URL"
```

A descriptive User-Agent matters on community sites; an empty/default one is what gets 403'd.

## Recon a new site before you wire it (10 minutes, saves the design)

1. **`robots.txt` first.** `Allow: /` plus `Disallow: /api/` is a common shape; a disallowed prefix is
   off-limits even when it answers 200, and even when the API behind it is a paid product. Note the
   allowed surface and build only on that.
2. **`sitemap.xml`** — the real page inventory, including which views exist per cadence
   (`/daily`-style vs `/weekly`, `/monthly`, `/yearly`).
3. **Grep the HTML for `application/ld+json`.** A site on a modern SSR framework (Next.js App Router
   shows up as `self.__next_f` in the markup; there is no `__NEXT_DATA__`) often embeds its entire
   listing as a schema.org `ItemList` — clean fields (name, description, canonical URL, language,
   topics, dates), no key, and nothing to re-parse when the card markup changes. Prefer it over
   scraping cards, and read it in the collector so the parse stays deterministic and free.
4. **No JSON-LD? Ask the page what it fetches.** In the browser tool:
   `js("performance.getEntriesByType('resource').map(e=>e.name).filter(n=>/api|json|graphql|feed|rss/.test(n))")`
   — then check that path against robots.txt before using it.
5. **Check for a *paid* API or MCP before concluding "no API".** Look for a `/signal`, `/pricing` or
   `/docs` page and run one web search on `<site> api`. A site with no free API is still usable when
   its public pages carry a structured payload — that is the sanctioned route.

## Route per source class

| Class | First route | Fallback | Notes |
|---|---|---|---|
| Blog / news site | its own RSS/Atom feed (`<link rel="alternate">` in the page head) | fetch + extract the HTML, then the headless browser for JS-only pages | RSS is the cheapest and the most stable; prefer it whenever it exists |
| Anything with no feed | `web_extract` on the article/page URL | `browser_exec` when the content only renders with JS | Keep the headline + snippet when a page is paywalled; never bypass the paywall |
| SSR listing page with JSON-LD | parse the embedded `ItemList` out of the page HTML | `web_extract` when only a summary is needed | No key, no HTML parser to maintain; cheap enough for the zero-token collector |
| Supermarket catalogs / promo flyers | the retailer's own promo page | the flyer PDF → text extraction; LLM vision on rendered pages if the PDF is image-only | No public flyer API exists. Flyers change weekly → weekly cadence + **text-hash diff**, not daily. Check the site's terms before depending on it |
| Aggregator sites | usable in principle | — | Their terms are usually unstated; verify before depending on them, and never make one the only route to a source you care about |
| Reddit | the subreddit's `.rss`/`new/.rss` feed | — | Works unauthenticated with a descriptive UA, but **Reddit is retiring RSS** (announced Sep 2026; feeds stop 2026-11-13, public API: no new requests after 2026-10-31, access removed from 2027-01-12, gone by Mar 2027). The unauthenticated `.json` endpoints return **403**. Design it as a source that will break, keep it last in the build order, and let the health footer report it going dark |
| X / Twitter | *no free, safe route* | keyword search over the public web as a lossy stand-in | The `nitter`-style privacy frontends were shut down by legal action and the survivors are unreliable; the official API is paid; cookie/session scraping risks the account. **Recommend dropping X**, or ask whether the followed accounts also publish a blog/newsletter/Mastodon-style feed, which does have RSS |

## Verified per-site notes

- **trendshift.io** (GitHub-trending lists): no RSS, no free API, no MCP server. There *is* a paid
  "Signal" API (about $9/month), and `robots.txt` disallows `/api/` and `/apikeys/` — do not build on
  that prefix. Every public listing page embeds `application/ld+json` → `ItemList` with 25 entries:
  `name` (owner/repo), `description`, `codeRepository`, `programmingLanguage`, `dateCreated`,
  `dateModified`, `keywords`. Verified on `/`, `/weekly`, `/monthly`, `/yearly` and `/live-mentions`.
  `/daily` is a 404 — the daily view *is* the homepage; `/github-trending-repositories` carries no
  JSON-LD (HTML parse only, skip it). `/live-mentions` is the valuable one for social signal: each
  item carries `discussionUrl` pointing at the real X/Reddit/Hacker News post plus a freshness
  timestamp — a sanctioned proxy for the X/Reddit signal that needs no cookies. Cadence: weekly for
  `/weekly`, dedupe on the repo slug so only repos newly entering the list get reported.

## Expected failure modes and the guardrail for each

| Failure | Guardrail |
|---|---|
| Paywall | Keep headline + snippet, mark the item "paywalled" — never bypass |
| JS-only page | Switch that source's backend to the headless browser |
| Rate limit / 429 | One retry with backoff, then fail loudly for that source — no hammering |
| Markup changed, extraction returns empty or tiny | Treat as a **failure**, not as "no news" |
| Structured payload disappears from the page | Treat as a failure: the site changed how it renders; re-recon rather than widening a regex |
| Image-only PDF flyer | Render pages and use vision, or flag the source as needing a manual look |
| Feed dead or empty for N days | Health footer says "no items in N days" / "dead since <date>" |
| Platform retired the feed (Reddit) | Reported dead in the footer; no automatic escalation to cookies or scraping |
