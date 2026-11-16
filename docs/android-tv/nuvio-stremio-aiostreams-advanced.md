# 3 — Nuvio and Stremio + AIOStreams: advanced setup

This page holds what you only need after the [quick start](nuvio-stremio-aiostreams.md): how AIOStreams works, parent and child configurations, variants, extra addons, posters and the proxy. Everything here is optional.

## 3.1 🧩 What is AIOStreams?

AIOStreams is an all-in-one **addon manager**: it groups your addons behind a single manifest, applies your filters, sorting and stream formatting, and installs in Nuvio/Stremio as one addon.

It also saves your configuration online, linked to a **UUID** and a **password**, so you can restore it anywhere. Everything in this part is optional — the quick start works without it.

## 3.2 🧾 Reading the stream list

![nuvio-ios](nuvio_streams_ios.png)

The streams display clean, readable, emoji-enhanced information instead of raw file names:

- 🎞️ **Resolution badges** (best to worst): ⚜️ 4K for 2160p, 📀 1440p, 📀 1080p…, ⚪ N/A when the resolution is missing.
- 🏷️ **Quality labels** (best to worst): 📀 REMUX, 💿 Blu-ray, 🌐 WEB-DL, 🖥️ WEBRip, 💾 HDRip / DVDRip / HDTV / TS / TC, ⚪ N/A when there is no quality tag.
- **Cached streams**: `[AD⚡️]` means cached — pick those. ⏳ means not cached: the debrid service has to download it first, and if there are no seeders you will not be able to watch it.
- If everything shows ⏳, your debrid IP has not been validated — see step 7.

## 3.3 🔗 Template or parent config?

AIOStreams gives you three ways to run more than one setup. This page helps you pick one and explains how a child configuration inherits from its parent.

| You want…                                           | Use          | Why                                                                                     |
|-----------------------------------------------------|--------------|-----------------------------------------------------------------------------------------|
| To share your setup with someone else               | Template     | They import a JSON file and get their own configuration and credentials                 |
| Several configurations that follow one base         | Parent/child | Change the parent once and every child follows; each child keeps its own debrid account |
| One configuration with small per-device differences | Variant      | A few lines of script, a diff preview before you save, no second configuration          |

- **Template** — for sharing your setup with others, or when you do not want to maintain the configuration afterwards. You publish a JSON file; anyone can import it and gets their own configuration with their own credentials. Nothing links back to yours and there is nothing to keep in sync.
- **Parent config** — for someone who maintains several configurations. One base config holds everything, the others point at its UUID and inherit it, overriding only the sections you choose; change the base once and they all follow. It stays your setup, with your credentials. You will find it in **Miscellaneous → Parent Config** (Advanced mode).
    - You cannot inherit from a configuration that is itself inheriting another one — a configuration can only inherit from the parent directly.

## 3.4 🌱 Setting up a child configuration

If the child must have different settings, import the template first, then point the configuration at its parent, delete the addons you do not want to keep locally, and choose a strategy per section. If the only thing that will differ is your debrid account, do not import the template at all: create the configuration and point it at the parent, and everything is inherited.

The per-section strategies decide, section by section, where a child configuration gets its values:

- **Inherit from parent** — use the parent's addons, filters, sorting, formatting… The child's own values for that section are ignored.
- **Extend parent (add mine)** — start from the parent's list and add your own entries. Entries are matched by their internal id, so *your* version of an addon replaces the parent's while the rest keeps inheriting. This is the mode to use when the child only differs by one or two addons.
- **Override with mine** — ignore the parent entirely for that section: the child's own list is used as is.

Two things worth knowing:

- Under *extend*, an addon you add by hand gets a **new internal id** (shown only in a config export), so it is added next to the parent's instead of replacing it — the parent's copy keeps running, even with the same name. An addon that comes from the same template as the parent's keeps the template's id, so the child's copy *replaces* the parent's.
- **Variants are not inherited**: a variant only sees its own configuration's addons, so create it in the configuration you install from.
- Services behave the other way round: a **disabled** service in the child is ignored, so the parent's stays enabled. To switch an inherited debrid account off, use *override* on the Services section.

## 3.5 🔀 Turning an addon off for one device (variant)

A variant is a short script that changes your own configuration for one device — no second configuration, no second link to share.

1. Open the configuration and go to **Miscellaneous → Variants** (Advanced mode).
2. Add a variant: give it an **Id** (`no-streamfusion` — lowercase letters, digits, `-` and `_` only) and a **Name** (`No StreamFusion`).
3. In the script box, write the change. To deactivate for example StreamFusion, that is `disable presets[options.name="Streamfusion (Amine)"]`.
4. Save the configuration.

Example — deactivate StreamFusion on a single device:

| Field  | Value                                                  |
|--------|--------------------------------------------------------|
| Id     | `no-streamfusion`                                      |
| Name   | `No StreamFusion`                                      |
| Script | `disable presets[options.name="Streamfusion (Amine)"]` |

To hide every custom addon that needs your own debrid account or key (Lumio, StreamFusion, Statusio) in one go, use a single variant (Id `no-personal-addons`) with one line that matches the `(Amine)` suffix they all share. These addons are tied to your own account, so a child configuration or another person cannot reuse them:

```text
disable presets[options.name*="(Amine)"]
```

- `*=` is a substring match: it disables every addon whose name contains `(Amine)`, so a personal addon you add to the parent later is covered without touching the variant.
- `=` is an exact match on the whole name: use it to disable a single addon, as in the StreamFusion example above.

💡 **Naming tip.** Give every personal-account addon in the parent the same suffix, `(Amine)`, and give a child's own copy of the same addon a different one (for example `Lumio (Sarah)`), so `*="(Amine)"` never catches it. Avoid matching on the addon name alone: `*="Lumio"` would disable both copies. Write the suffix exactly `(Amine)` everywhere, with the same capitalisation and brackets. Addons are merged by their internal `instanceId`, not by name, so a hand-added addon never replaces the inherited one and both stay in the list. Variants are not inherited either: create them in the configuration you install from.

Then go to **Save & Install**, select **No StreamFusion** in the variant list and choose the **path** form. When you copy the manifest URL it must show the selection, as in `…/stremio/<uuid>/<password>/v/no-streamfusion/manifest.json`. Install that URL as the addon on the device that should lose StreamFusion (remove the old one if you replaced it).

The same variant also disables an addon in a **child configuration** that inherited it from a **parent configuration** — the preview may report that the instruction matched nothing, and it still takes effect when you play.

Notes

- Use the **path** form, not `?v=`: clients rebuild the stream requests from the base URL and drop the query string, so only the first request would carry the variant.
- If the variant preview reports *some instructions matched nothing* for an addon that comes from a parent configuration, that is normal — the preview only sees your own configuration, while the script is applied to the merged one when you play.
- Select **Base config** on the Save & Install page to keep installing the unchanged configuration.

## 3.6 Custom addons you can plug in (optional)

The addons below are in the **full** template and need **your own account or manifest URL**: they arrive **enabled with an empty URL**, and AIOStreams highlights those unfilled placeholders before you save. To use one: configure it on its own site, copy its manifest URL and paste it into that addon in AIOStreams (**Addons → Custom → URL**) — or switch that addon off if you do not want it. The **essentials** template leaves all of them out. Everything else the template enables (Torrentio, Comet, MediaFusion, Meteor, StremThru Store/Torz, OpenSubtitles) needs no account beyond your debrid service.

The full template has **no Cinemeta**: *AIOMetadata* provides the metadata and the catalogs, so fill it in. If you skip AIOMetadata, add Cinemeta back as a **Custom** addon with `https://v3-cinemeta.strem.io/manifest.json`, otherwise titles have no metadata. The essentials template keeps Cinemeta.

| Addon                    | What it adds                                                                                                                                                   | Configure it at                                                                                   | Resources | Format Passthrough | Result Passthrough | Stremio Addons page                                                          |
|--------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|-----------|--------------------|--------------------|------------------------------------------------------------------------------|
| *AIOMetadata*            | Metadata, search and MDBList / Trakt catalogs (Top 10 per service, genres, IMDb popular, upcoming) — see [below](#aiometadata-catalogs-from-mdblist-and-trakt) | <https://aiometadatafortheweebs.midnightignite.me/configure> — your manifest URL has a private ID | —         | —                  | —                  | [aiometadata](https://stremio-addons.net/addons/aiometadata-fortheweebs)     |
| *Top-streaming (FR)*     | The same lists for France (Canal+, Netflix FR, Prime FR…)                                                                                                      | <https://top-streaming.stream/configure?lang=fr> — pick *Standard Posters*                        | `catalog` | —                  | —                  | [top-streaming](https://stremio-addons.net/addons/top-streaming)             |
| *🏆 Nuvio Live Sports*   | Live football, NBA, NFL, NHL, F1                                                                                                                               | <https://nuviosports.xyz>                                                                         | —         | ✅                 | ✅                 | [nuvio-live-sports](https://stremio-addons.net/addons/nuvio-live-sports)     |
| *Sports Streams*         | Live and upcoming matches — football, basketball, cricket, UFC, tennis…                                                                                        | <https://sports.highfly.dev> — your manifest URL has a private key, don't share it                | —         | —                  | —                  | —                                                                            |
| *CNCVerse Bridge · Main* | Live sports events and channels, merged into one *CNCVerse* TV catalog                                                                                         | <https://cncverse.dpdns.org/configure> — your manifest URL has a private token                    | —         | —                  | —                  | —                                                                            |
| *PenguPlay*              | Live football and sports channels (Live Now, Upcoming, Channels)                                                                                               | <https://pengu.uk/> — your manifest URL has a private token                                       | —         | —                  | —                  | —                                                                            |
| *statusio (Amine)*       | Debrid account health card — provider, username, expiry, days left                                                                                             | <https://statusio.elfhosted.com/configure>                                                        | —         | ✅                 | ✅                 | [statusio](https://stremio-addons.net/addons/statusio)                       |
| *Lumio (Amine)*          | **Best for French content, with StreamFusion** — French VOD, torrent + direct download                                                                         | <https://mylumio.tv> — manifest URL has a private key, keep it secret                             | `stream`  | —                  | —                  | [lumio](https://stremio-addons.net/addons/lumio)                             |
| *Streamfusion (Amine)*   | **Best for French content, with Lumio** — 4K programs (StreamFusionReborn). Not in the marketplace                                                             | <https://streamfusion.stremio-epsilon.ca> — needs a key from their Telegram bot                   | `stream`  | —                  | —                  | [streamfusionstremio](https://stremio-addons.net/addons/streamfusionstremio) |
| *AI Search*              | Recommendations from natural-language queries (needs an OpenAI-Compatible API Key + TMDB keys; better with Trakt)                                              | <https://stremio.tomz.dev/aisearch/configure>                                                     | —         | —                  | —                  | [ai-search](https://stremio-addons.net/addons/ai-search)                     |

**Seeders filter** — the template only applies the seeder minimum (≥1) to P2P and uncached torrents. Cached debrid, usenet, and live/HTTP addons (like the sports ones) report no seeders and would otherwise be counted as 0 and filtered out entirely.

**Resources** — leave blank unless you want to restrict what AIOStreams takes from the addon: `stream` = streams only, `catalog` = catalogs only.
**Format Passthrough** — whether to pass through the stream formatting. This means your formatting will not be applied and the original stream formatting is retained.
**Result Passthrough** — results from this addon are never filtered out; its streams always appear in the list.
**Force To Top** (Advanced, per addon) — pins this addon's results above everything else, overriding your sorting.

⚠️ **Catalogs won't show up until you fill in your own URL.** These addons ship in the template with a **placeholder/example URL**, not yours. Nuvio will not display their catalogs until you replace that URL with the manifest link generated from your own account (for example *AIOMetadata* or *Top-streaming (FR)*).

### AIOMetadata: catalogs from MDBList and Trakt

[AIOMetadata](https://docs.elfhosted.com/app/aiometadata/) supplies metadata, search and catalogs built from MDBList and Trakt lists. In the full template it replaces *Cinemeta*, the US *Top-Streaming* addon and *Trakt lists*, which the full template no longer includes. The template already lists its catalogs in the AIOStreams **Catalogs** section, but they only appear once your own AIOMetadata configuration provides the same lists.

1. Open [aiometadatafortheweebs.midnightignite.me/configure](https://aiometadatafortheweebs.midnightignite.me/configure).
2. In the integrations settings, add your MDBList API key (you find it in your [MDBList](https://mdblist.com/) account settings), and connect Trakt if you use it.
3. Add the lists you want as catalogs. The full template expects these MDBList lists:
    - **Top 10 per service (US)**: Netflix, Amazon Prime, Apple TV+, Disney+, Paramount+, HBO Max — movies and shows.
    - **Popular by genre**: Action, Animated, Animation/Anime, Comedy, Crime, Documentary, Drama, Horror, KDrama, Romance, Sci-Fi, Thriller — movies and shows.
    - **Others**: *Upcoming Movies (Theaters)*, *Today's Most Popular Movies / Shows on IMDb*.
4. Save, copy the manifest URL and paste it into the *AIOMetadata* addon in AIOStreams (**Addons → Custom → URL**). Keep that URL private: it contains your configuration ID.
5. Check that the catalogs show in Nuvio.

The France Top 10 lists still come from *Top-streaming (FR)*, which the template keeps. To use these catalogs in Nuvio [collections](#312-collections), add them to a folder as addon catalogs; they show up under your AIOStreams addon.

## 3.7 📺 Live sports and live TV addons

Live addons have no seeders. The full template includes four of them as **Custom** addons with an empty URL: *🏆 Nuvio Live Sports*, *Sports Streams*, *CNCVerse Bridge · Main* (its five live-event catalogs are merged into one **CNCVerse** TV catalog) and *PenguPlay*. Fill in the manifest URL you get on each addon's own site, or switch the addon off. Other live addons work the same way: add them as a **Custom** addon. [NuvioHub](https://nuviohub.pages.dev/addons#live-sports-tv) lists more.

Channels from your addons also show on the **Live TV** page of the [AIOStreams app](nuvio-stremio-aiostreams.md#web-and-ios).

## 3.8 🖼️ Custom posters (optional)

Both templates are preconfigured with a **custom poster URL** (poster service *Custom*) that points at a [Posters+](https://postersplus.elfhosted.com/) instance: **open source** and self-hostable, with ratings, awards and quality badges drawn on the poster. The URL carries only style settings and the `{tmdb_id}`, `{imdb_id}`, `{id}`, `{type}` and `{shape}` placeholders that AIOStreams fills in, and no key.

Every poster request goes to the host named in the URL, which sees the title IDs, and posters stop loading if that instance is down. To avoid both, switch the poster service to *None* or self-host Posters+.

To change the look, pick another preset on the Posters+ site and paste the URL it generates in the poster settings of your configuration, or switch the poster service to *None* to keep the posters of your metadata addon. More poster services are listed on [NuvioHub](https://nuviohub.pages.dev/addons#posters): ExtendedRatings, TopPosters, Pictorium and RatingPosterDB (paid).

⚠️ A poster URL you generate yourself can embed your own keys (TMDB, MDBList, RPDB). Treat it like a password and never paste it in a public place.

## 3.9 🔌 Proxy (optional)

Some links only play through a proxy: the source needs a specific header, your ISP blocks it, or the debrid service refuses the direct link. AIOStreams can route streams through a proxy you configure, and you have two ways to get one: the proxy offered by the AIOStreams instance itself, or one you host yourself (for example MediaFlow).

If you host your own, AIOStreams asks for two addresses:

- the **local address** of your proxy, used by AIOStreams for its own calls — it stays on your network;
- a **public address**, because the player is the one that fetches the stream and a device outside your network cannot reach a local name.

Two consequences to keep in mind before hosting your own proxy:

- Playback is then relayed through your own connection for every remote client — your upload speed becomes the limit, and the traffic passes twice (in and out). A 4K remux will saturate a home fibre line.
- The proxy password travels inside the stream links, so it ends up in clients and logs. Treat it as semi-public and rotate it if it leaks.

## 3.10 👤 Profiles in Nuvio

Nuvio lets a profile **inherit settings from another profile**, which is very handy if you use multiple devices and don't want to configure each one separately. What you can inherit:

- **TV settings** — appearance, layout, playback, subtitles, and integration preferences used by NuvioTV.
- **Mobile settings** — appearance, cards, playback, metadata, and notification preferences used by Nuvio Mobile.
- **Desktop settings** — appearance, navigation, cards, playback, metadata, and notification preferences used by Nuvio Desktop.

Secondary profiles can also reuse the primary profile's addons and plugins:

- **Use primary profile addons**
- **Use primary profile plugins**

You can also **copy settings from one profile to another** directly (instead of setting up inheritance), which is useful for a one-off sync.

- Manage all of this at [nuvio.tv/account?tab=profiles](https://nuvio.tv/account?tab=profiles).

## 3.11 🗂️ Manage Nuvio from nuvio.tv (Website)

- It's preferable to manage your account, profiles and integrations from the [nuvio.tv](https://nuvio.tv) website rather than from the TV or mobile app — preferably from a computer. The website gives you a much better overview to handle account settings and integrations across all your systems (mobile, TV, desktop) at once.
- Catalogs sorting can be managed through the apps only (TV, mobile, desktop) — they are not available on the website.
- If you use Trakt, verify that it is being used in "Tracking" for all the platforms you use (TV, mobile, desktop), that your Trakt account is linked to Nuvio and that all items are using Trakt for tracking in "Tracking".
- After applying a change on the website, go check your TV or mobile app to confirm the change was actually applied there.

## 3.12 Collections

Collections allow you to organize your content into custom categories (Netflix, Apple TV, etc.) without needing additional addons.

- The order of your collections and catalogs is handled per-device (not per-profile) and is synced across your devices.
- **Install the default recommended collection**: go to [nuvio.tv/community-collections](https://nuvio.tv/community-collections) and click "Add to profile" to install a collection. I recommend this one: [Kaptain collection (sorted by popular, no-addon)](https://nuvio.tv/community-collections?sort=popular&readiness=no_addon&q=kaptain).
- ⚠️ Collections aren't synced between profiles — you need to add them to each profile individually.
- Once you're done adding/editing collections, sync your profiles at [nuvio.tv/account?tab=profiles](https://nuvio.tv/account?tab=profiles).

1. For detailed setup instructions, follow [this community tutorial](https://www.reddit.com/r/Nuvio/s/7bTcL9OcmZ) starting at 2:35
2. Go to [Nuvio Collections Manager](https://nuvioapp.space/account?tab=collections) (or use the mobile app, which is easier)
3. Create your custom collections with names like "Netflix", "Apple TV", "My Watchlist", etc and add catalogs and images

### Ready-made collections for the full template

The repo ships a collections file built on Kaptain's collections and wired to the **full** template's catalogs:

`https://raw.githubusercontent.com/AmineDjeghri/personal-os-setup/main/docs/android-tv/nuvio-collections-template.json`

| Collection              | What it holds                                                                                                                                                                                                                                                                                   |
|-------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Trending                | Trending movies and series (IMDb, today) and movies coming to theatres, from *AIOMetadata*                                                                                                                                                                                                      |
| Streaming Services      | Top 10 rows only. Netflix and Prime Video: France (*Top-streaming (FR)*) then US (*AIOMetadata*); Canal+: France; Disney+, HBO Max, Apple TV+, Paramount+: US (*AIOMetadata*); Starz, AMC+, MGM+, Mubi, Pluto TV, Shudder, Tubi: Kaptain's Top 10 lists. Services without a Top 10 are left out |
| Live TV                 | A *Football* folder with the live sports catalogs                                                                                                                                                                                                                                               |
| Genres                  | 25 genres, each with its *Top of the Year* movies and series (Martial Arts, which has none, keeps *Top All Time*)                                                                                                                                                                               |
| Awards, Kids and Family | Kaptain's folders, unchanged: Oscars, Cannes and Golden Globes winners, studio and kids' lists                                                                                                                                                                                                  |
| Actors                  | 159 actors, each with their *Popular* movies and, when there is one, *Popular* series                                                                                                                                                                                                           |

Rows that come from AIOStreams name your AIOStreams addon, and that name is personal, so the file holds a placeholder instead:

1. Find your addon ID: open your AIOStreams manifest URL (**Save & Install → Install**, then copy the link) in a browser and copy the `"id"` value. On this instance it is `aiostreamsfortheweebs.midnightignite.me.` followed by the first 12 characters of your UUID:

    ```text
    UUID:  1234abcd-5e6f-7a8b-…  (first 12 characters: 1234abcd-5e6)
    ID:    aiostreamsfortheweebs.midnightignite.me.1234abcd-5e6
    ```

2. Download the file and replace every `<your-aiostreams-addon-id>` with that ID, with *Replace all* in a text editor or with:

    ```bash
    sed -i 's/<your-aiostreams-addon-id>/aiostreamsfortheweebs.midnightignite.me.1234abcd-5e6/g' nuvio-collections-template.json
    ```

    Each row then reads `"addonId": "aiostreamsfortheweebs.midnightignite.me.1234abcd-5e6"`.

3. Import the file in the [Nuvio Collections Manager](https://nuvioapp.space/account?tab=collections).

Rows from AIOStreams only fill when the matching addons are filled in: *Top-streaming (FR)* and *AIOMetadata* (see [above](#aiometadata-catalogs-from-mdblist-and-trakt)), and for *Football* the [live sports addons](#37-live-sports-and-live-tv-addons). The other rows are TMDB and Trakt lists that Nuvio reads itself, with no addon.

You can customize how your collections look by adding cover images and configuring display settings:

**Cover Images (Logos)**:

- Find collection cover images here: [Netflix, Apple, and other logos](https://postimg.cc/gallery/y7V9gYX)
- Example: [Netflix logo](https://i.postimg.cc/WVXFgmRn/Netflix.png)
- **Important**: Make sure the URL includes the file extension (e.g., `.png`)
- Find genre images here: [Genre artwork gallery](https://postimg.cc/gallery/LhYL0YQ/)

**Display Settings**:

- **Tile Shape**: Set to "Landscape" for wider tiles
- **Show GIF When Configured**: Set to "False" to use static images
- **Hide Title**: Set to "True" to show only the cover image without text

After configuring these settings, add your collections to your home screen for easy access.

## 3.13 Useful Stremio and Nuvio Resources

- **Subreddits**: [r/Stremio](https://www.reddit.com/r/Stremio/) & [r/StremioAddons](https://www.reddit.com/r/StremioAddons/)
- **Addons Catalog**: [stremio-addons.net](https://stremio-addons.net/)
- **Nuvio directory**: [NuvioHub](https://nuviohub.pages.dev/) lists Nuvio apps and forks, addons and plugins (aggregators, HTTP streams, live sports and TV, subtitles, metadata, posters, catalogs), tools, debrid and usenet services, and community guides, with a mark for addons that need a debrid service or are paid.
- **French Community**:
    - [stremiofr.me](https://stremiofr.me/)
    - [r/Stremio_France](https://www.reddit.com/r/Stremio_France/)
    - [Discord Server](https://discord.gg/KN3vRqTHDa)
- **Another guide**: [numb3rs.stream — Streaming Perfect Setup, Full and Easy Total Beginner's Guide](https://numb3rs.stream/)
