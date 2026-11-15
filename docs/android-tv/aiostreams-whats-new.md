# AIOStreams v2.38: web app, iOS and what's new

Back to the [main guide](nuvio-stremio-aiostreams.md).

## 🌐 AIOStreams web app, iOS and what's new in v2.38

AIOStreams v2.38 ([full changelog](https://aiostreams.org/changelog/v2.38)) turns the app in a browser into a full player. It runs from your instance's `/web` page or from [web.aiostreams.org](https://web.aiostreams.org) (add your configuration's media server or a Jellyfin server and sign in; the server needs an `https://` address).

### On iOS (Nuvio no longer works there)

1. Open the AIOStreams web app in Safari and sign in to your configuration.
2. Share → **Add to Home Screen** to install it as a PWA.
3. Use **VLC** as the external player for streams the browser cannot play.

The built-in WebGPU engine needs a browser with WebGPU (Chrome, Edge, Firefox) over HTTPS, and a file host the browser can read: AIOStreams' proxy, its usenet streaming and TorBox do. Otherwise the browser's own player takes over. **Settings → Playback → Player → Engine** switches to it for everything.

### What else is new

- **Live TV**: channels from your addons on one page with a guide, catch-up and reminders. The new *Xtream* addon in the marketplace signs in to an XC API account; the same channels show in Stremio and other Jellyfin clients.
- **Player**: HEVC, Dolby Vision, TrueHD and DTS in the browser, audio track switching, a file's own subtitles and styled subtitles, a mini player and picture-in-picture, anime upscaling, trailers that play by themselves, and scores from IMDb, Rotten Tomatoes, Metacritic and Letterboxd.
- **Who gets this**: on the configure page, give an addon or catalog to only some users without writing variants.
- **Languages**: the apps come in 12 more languages (including French); pick yours under **Settings → Interface → Language**.
- **Watch Import**: [Watch Import](https://watch-import.viren070.me) brings your Stremio or Nuvio watch history, Continue Watching and library into AIOStreams.
- **Self-hosting**: instances now ask search engines not to list them; turn on **Allow search engine indexing** under **Settings → Branding** if you want yours found.
