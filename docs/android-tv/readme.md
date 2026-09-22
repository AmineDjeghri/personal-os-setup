# TV Setup (googletv / android tv)

One of the best TV OS is Google TV. Here are some reasons why you should consider using Google TV:
- Sideloading apps is straightforward on Google TV. You can install apps like Stremio, SmartTube, and others.
- It's not as responsive as Apple TV, but you can tweak it to make it faster.
- You can use alternative launchers like 'Projectivy'.

This page covers the TV side: picture settings, performance, apps and the launcher. The streaming side — Nuvio/Stremio, AIOStreams, debrid and the addons — lives on its own page: **[Nuvio / Stremio + AIOStreams](nuvio-stremio-aiostreams.md)**.

**Table of contents**
<!-- TOC -->
* [TV Setup (googletv / android tv)](#tv-setup-googletv--android-tv)
  * [All TV types:](#all-tv-types)
  * [Google TV OS:](#google-tv-os)
    * [Best google TV apps:](#best-google-tv-apps)
      * [What is Stremio / Nuvio ?](#what-is-stremio--nuvio-)
<!-- TOC -->

## All TV types:
- My first advice is to never use the standard mode on your TV. Always use the cinema/ filmaker or movie mode. The
  standard mode is too bright and the colors are not accurate. Use the cinema or movie mode when watching movies or
  series.
- Here is a [video](https://www.youtube.com/watch?v=dY3M_h30HYc) explaining TV modes.
  And [this video](https://www.youtube.com/watch?v=nTO2Wmw1NKA) for changing the settings of your TV taking into
  account different modes (SDR, HDR, Dolby). (You can refer to reddit guides or YouTube videos
  or [rtings.com](https://rtings.com) to find the best settings).
- If your TV supports multiple content types (SDR, HDR, DOLBY), the mode needs to be activated on each content type.
- On some TVs like the Hisense U7k, you need to enable enhanced HDMI mode to access dolby vision & 60HZ on your
  Chromecast and other HDMI inputs.
- If you play video games, use the game mode. It will reduce the input lag and improve the gaming experience.

## Google TV OS:
- (Important) Enhance the performance of your Google TV by following
  this [tutorial](https://www.slashgear.com/1321192/tricks-make-chromecast-google-tv-run-faster/)
- Chromecast google TV
  4k [video settings](https://www.reddit.com/r/Chromecast/comments/1ct77ai/a_fix_for_washed_out_colors_and_performance/)
- Chromecast google TV remote: you can use your iPhone or android to remotely control google tv and use your
  phone's keyboard, for example. You need either Google TV app or Goohle home app on you phone. on your google
  TV, the feature is disabled by default: you need to go to system-> keyboard -> manage keyboards -> check
  virtual remote. You can now use your phone to type things rapidely
- Windows 11 with 4K HDR TV: follow this [tutorial 1](https://www.pcmag.com/how-to/set-up-gaming-pc-on-4k-tv)
  and [tutorial 2](https://www.pcmag.com/how-to/how-to-play-games-watch-videos-in-hdr-on-windows-10)
- recommended TV apps for Google TV: Projectivy launcher, Stremio, Nuvio, Smart Tube, YouTube atv. update the channels in
the Projectivy and add Stremio and Nuvio there. Also make it the default launcher for your tv.

### Best google TV apps:
- [SmartTube](https://smartyoutubetv.github.io/): A free Android TV app alternative to YouTube with no ads, designed for TV screens, up to 8K video resolution, supports youtube accounts.
- [Projectivy Launcher](https://play.google.com/store/apps/details?id=com.spocky.projengmenu&hl=en&pli=1):  an alternative app launcher for Android TV devices that provides users with a different home screen and method for navigation and opening apps.
    -  Remember to export your settings: https://www.reddit.com/r/Projectivy_Launcher/comments/1cdt00f/tell_me_about_exporting_these_launcher_settings/
    -  You can create channels in the menu and add stremio, smartube, spotify to the home screen.
- [Stremio](https://www.stremio.com/) / [Nuvio](https://nuvioapp.space/)

#### What is Stremio / Nuvio ?

![nuvio-ios](nuvio-ios.png)

- Nuvio (a new Stremio app-like) is an opensource streaming application that allows you to watch and organize video content from different services,
  including movies, series, live TV and video channels. The content is aggregated by an addon system providing streams
  from various sources. And with its commitment to security, Nuvio is the ultimate choice for a worry-free,
  high-quality streaming experience.
- Nuvio is available on all platforms: Web, Windows, Mac, Linux, Android, iOS, Android TV, Apple TV...
- Addons...etc will be synchronized between all your devices.
- For the streams themselves you will use a **debrid service** (AllDebrid, Real-Debrid, TorBox…), which is what makes playback instant and means you never need a VPN. The [streaming page](nuvio-stremio-aiostreams.md) explains it and sets it all up.

Keep going with the streaming setup: **[Nuvio / Stremio + AIOStreams](nuvio-stremio-aiostreams.md)** — create a Nuvio account, subscribe to a debrid service, load a ready-made AIOStreams configuration and you are watching.
