# AIOStreams addons: custom, live sports and posters

Addons that go beyond the marketplace, the live sports addons in the full template, and the poster setup. Back to the [main guide](nuvio-stremio-aiostreams.md).

## (Optional) — Custom addons you can plug in

The addons below are in the **full** template and need **your own account or manifest URL**: they arrive **enabled with an empty URL**, and AIOStreams highlights those unfilled placeholders before you save. To use one: configure it on its own site, copy its manifest URL and paste it into that addon in AIOStreams (**Addons → Custom → URL**) — or switch that addon off if you do not want it. The **essentials** template leaves all of them out. Everything else the template enables (Torrentio, Comet, MediaFusion, Meteor, StremThru Store/Torz, OpenSubtitles, Cinemeta) needs no account beyond your debrid service.

| Addon                    | What it adds                                                                                                      | Configure it at                                                                 | Resources        | Format Passthrough | Result Passthrough | Stremio Addons page                                                          |
|--------------------------|-------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|------------------|--------------------|--------------------|------------------------------------------------------------------------------|
| *Cinemeta*               | Base metadata + Popular / New / Featured catalogs — **enabled by default**                                        | —                                                                               | `meta` `catalog` | —                  | —                  | —                                                                            |
| *Top-Streaming*          | Netflix, Prime Video, Disney+, HBO Max, Apple TV… Top 10 lists (US)                                               | <https://top-streaming.stream/configure?lang=en> — pick *Standard Posters*      | `catalog`        | —                  | —                  | [top-streaming](https://stremio-addons.net/addons/top-streaming)             |
| *Top-streaming (FR)*     | The same lists for France (Canal+, Netflix FR, Prime FR…)                                                         | <https://top-streaming.stream/configure?lang=fr> — pick *Standard Posters*      | `catalog`        | —                  | —                  | [top-streaming](https://stremio-addons.net/addons/top-streaming)             |
| *Trakt lists*            | Your Trakt lists, trending and genre lists                                                                        | <https://trakt.dexter21767.com> — log in with Trakt                             | `catalog`        | —                  | —                  | —                                                                            |
| *🏆 Nuvio Live Sports*   | Live football, NBA, NFL, NHL, F1                                                                                  | <https://nuvio.moaqeel6679.my.id>                                               | —                | ✅                 | ✅                 | [nuvio-live-sports](https://stremio-addons.net/addons/nuvio-live-sports)     |
| *Sports Streams*         | Live and upcoming matches — football, basketball, cricket, UFC, tennis…                                           | Your own manifest URL from the addon's site (private key — don't share)         | —                | —                  | —                  | —                                                                            |
| *CNCVerse Bridge · Main* | Live sports events and channels, merged into one *CNCVerse* TV catalog                                            | <https://cncverse.dpdns.org/configure> — your manifest URL has a private token  | —                | —                  | —                  | —                                                                            |
| *PenguPlay*              | Live football and sports channels (Live Now, Upcoming, Channels)                                                  | <https://pengu.uk/> — your manifest URL has a private token                     | —                | —                  | —                  | —                                                                            |
| *statusio (Amine)*       | Debrid account health card — provider, username, expiry, days left                                                | <https://statusio.elfhosted.com/configure>                                      | —                | ✅                 | ✅                 | [statusio](https://stremio-addons.net/addons/statusio)                       |
| *Lumio (Amine)*          | **Best for French content, with StreamFusion** — French VOD, torrent + direct download                            | <https://mylumio.tv> — manifest URL has a private key, keep it secret           | `stream`         | —                  | —                  | [lumio](https://stremio-addons.net/addons/lumio)                             |
| *Streamfusion (Amine)*   | **Best for French content, with Lumio** — 4K programs (StreamFusionReborn). Not in the marketplace                | <https://streamfusion.stremio-epsilon.ca> — needs a key from their Telegram bot | `stream`         | —                  | —                  | [streamfusionstremio](https://stremio-addons.net/addons/streamfusionstremio) |
| *AI Search*              | Recommendations from natural-language queries (needs an OpenAI-Compatible API Key + TMDB keys; better with Trakt) | <https://stremio.tomz.dev/aisearch/configure>                                   | —                | —                  | —                  | [ai-search](https://stremio-addons.net/addons/ai-search)                     |

**Seeders filter** — the template only applies the seeder minimum (≥1) to P2P and uncached torrents. Cached debrid, usenet, and live/HTTP addons (like the sports ones) report no seeders and would otherwise be counted as 0 and filtered out entirely.

**Resources** — leave blank unless you want to restrict what AIOStreams takes from the addon: `stream` = streams only, `catalog` = catalogs only.
**Format Passthrough** — whether to pass through the stream formatting. This means your formatting will not be applied and the original stream formatting is retained.
**Result Passthrough** — results from this addon are never filtered out; its streams always appear in the list.
**Force To Top** (Advanced, per addon) — pins this addon's results above everything else, overriding your sorting.

⚠️ **Catalogs won't show up until you fill in your own URL.** These addons ship in the template with a **placeholder/example URL**, not yours. Nuvio will not display their catalogs until you replace that URL with the manifest link generated from your own account (Example: *Trakt lists*, top-streaming)

## 📺 Live sports and live TV addons

Live addons have no seeders. The full template includes four of them as **Custom** addons with an empty URL: *🏆 Nuvio Live Sports*, *Sports Streams*, *CNCVerse Bridge · Main* (its five live-event catalogs are merged into one **CNCVerse** TV catalog) and *PenguPlay*. Fill in the manifest URL you get on each addon's own site, or switch the addon off. Other live addons work the same way: add them as a **Custom** addon. [NuvioHub](https://nuviohub.pages.dev/addons#live-sports-tv) lists more.

Since AIOStreams v2.38, channels from your addons also show on the **Live TV** page of the AIOStreams app.

## 🖼️ Custom posters (optional)

Both templates are preconfigured with a **custom poster URL** (poster service *Custom*) that points at a [Posters+](https://postersplus.elfhosted.com/) instance: **open source** and self-hostable, with ratings, awards and quality badges drawn on the poster. The URL carries only style settings and the `{tmdb_id}`, `{imdb_id}`, `{id}`, `{type}` and `{shape}` placeholders that AIOStreams fills in, and no key.

Every poster request goes to the host named in the URL, which sees the title IDs, and posters stop loading if that instance is down. To avoid both, switch the poster service to *None* or self-host Posters+.

To change the look, pick another preset on the Posters+ site and paste the URL it generates in the poster settings of your configuration, or switch the poster service to *None* to keep Cinemeta's posters. More poster services are listed on [NuvioHub](https://nuviohub.pages.dev/addons#posters): ExtendedRatings, TopPosters, Pictorium and RatingPosterDB (paid).

⚠️ A poster URL you generate yourself can embed your own keys (TMDB, MDBList, RPDB). Treat it like a password and never paste it in a public place.
