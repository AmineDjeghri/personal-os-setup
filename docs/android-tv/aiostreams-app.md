# The AIOStreams app

AIOStreams is not only an addon for Nuvio and Stremio: it also has its own app, a good alternative client for every screen. It shows the catalogs and streams of your configuration, so nothing needs to be installed in another player. Get it from [aiostreams.org/download](https://aiostreams.org/download), or see the [app documentation](https://aiostreams.org/apps). Back to the [main guide](nuvio-stremio-aiostreams.md).

## Where to use it

- **In a browser**, from your instance's `/web` page or from [web.aiostreams.org](https://web.aiostreams.org): add your configuration's media server (or a Jellyfin server) and sign in. The server needs an `https://` address.
- **Android phones, tablets and Android TV**, **computers** and **LG and Samsung TVs**: install the app from the download page.

## On iOS

Nuvio is not available on iOS, so use the AIOStreams web app as an app on your phone:

1. Open the AIOStreams web app in Safari and sign in to your configuration.
2. Share → **Add to Home Screen** to install it as a PWA.
3. Use **VLC** as the external player for streams the browser cannot play.

## What the app offers

- **Live TV**: the channels from your addons on one page, with a programme guide, catch-up and reminders. The *Xtream* addon in the marketplace signs in to an XC API account; the same channels also show in Stremio and other Jellyfin clients.
- **A full player in the browser**: HEVC, Dolby Vision, TrueHD and DTS, audio track switching, a file's own subtitles and styled subtitles. It needs a browser with WebGPU (Chrome, Edge, Firefox) over HTTPS and a file host the browser can read: AIOStreams' proxy, its usenet streaming and TorBox do. Otherwise the browser's own player takes over, and **Settings → Playback → Player → Engine** switches to it for everything.
- **Comfort**: a mini player and picture-in-picture, anime upscaling, trailers that play by themselves, and scores from IMDb, Rotten Tomatoes, Metacritic and Letterboxd.
- **Who gets this**: on the configure page, give an addon or catalog to only some users without writing variants.
- **Languages**: pick yours under **Settings → Interface → Language**.
- **Watch Import**: [Watch Import](https://watch-import.viren070.me) brings your Stremio or Nuvio watch history, Continue Watching and library into AIOStreams.
- **Self-hosting**: if you run a public instance you want people to find, turn on **Allow search engine indexing** under **Settings → Branding**.
