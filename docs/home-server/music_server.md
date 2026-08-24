# Music server

## Navidrome + Octo-Fiesta + Narjo/Feishin Music Stack

This setup combines **Navidrome**, a **Subsonic-compatible music server**, with **Octo-Fiesta**, a proxy that extends your library using Deezer.  

The goal of this stack is to combine:

- the **control and ownership of self-hosted music**

- the **convenience of streaming services**

- an **automatically growing music library**

Is this legal ? YES

Is this free ? YES

You can search and play **any song or album**, even if it is not in your collection yet.

---
## Components

### 1. Navidrome (Music Server)

Navidrome is a **self-hosted music streaming server** that implements the **Subsonic API**.

It is responsible for:

- storing your music files

- organizing them into artists, albums, and tracks

- providing streaming access to clients

Navidrome **only knows about files that exist in your library folder**.  It does not download music by itself.

---
### 2. Subsonic Clients (Narjo, Symfonium, Subplayer, etc.)

A **Subsonic client** is the application used to browse and play your music. Examples include: Narjo, Feishin..

These clients: connect to a Subsonic-compatible server,  display artists, albums, playlists,  allow searching and streaming tracks.

Normally the client connects **directly to Navidrome**.

Client → Navidrome

---
### 3. Octo-Fiesta (Auto-Download songs)

Octo-Fiesta is a **proxy server** that sits between the client and Navidrome.

Instead of connecting the client directly to Navidrome, you connect it to Octo-Fiesta.

Client → Octo-Fiesta → Navidrome

Octo-Fiesta intercepts requests from the client and decides how to handle them.

It extends your music library by using **TIDAL** when a song is missing for free.

### 4. Behavior

- If a song **exists in your Navidrome library**, Octo-Fiesta forwards the request normally.

- If the song **does NOT exist locally**, Octo-Fiesta searches TIDAL for example, and show you albums, tracks, artists that contains the name of the song. It streams the track immediately, downloads the track to your library and organizes it with metadata.
- When you play a song, the client only downloads the requested song. However, the album’s metadata is downloaded in the client (like Narjo) and shows you other songs from the same album without downloading them.


### 5. (optional) Beets
- [Beets](https://beets.readthedocs.io/en/stable/index.html): a music library manager that can import your music files, organize them, and add metadata. `uv pip install "beets[fetchart,lastgenre,embedart,titlecase,chroma]"`

  - beet import /home/amine/haos_media/music  -> interactive mode
  - beet import -q /home/amine/haos_media/music -> quiet mode

The following section summarizes the key concepts and behaviors of **Beets** regarding importing, tagging, configuration options, and command-line flags.
Understanding these terms helps clarify how Beets works internally.


in the [config.yaml](../../src/personal_os_setup/config/unix/beets/config.yaml) file (I disabled copy and move because i use Octo-Fiesta and i don't care about messing with the original files) :

```yaml
# import settings, check https://beets.readthedocs.io/en/stable/reference/config.html#importer-options
import:
  write: yes                        # if yes, write metadata into the files.
  copy: no                          # if yes, copy files into the Beets library directory.
  move: no                          # if yes, ignore copy and move files into the Beets library directory. if both are no, it will write metadata into the files.
  quite: yes                        # if yes, skip silently when importer is unsure. If no, ask for a manual decision from the user when the importer is unsure how to proceed (will use the match section to proceed)
  quiet_fallback: skip              # (requires quiet: yes), if skip, skip files that are already in the library
  timid: no                        # if yes, ask for confirmation on every autotagging match, even the ones that seem very close.
  autotag: yes                      # if yes, enable autotagging
  duplicate_action: remove          # remove duplicate files
  incremental: no                  # if yes, don't reimport a directory we already imported
  incremental_skip_later: no       # if yes, don't reimport an album/track that was skipped (if incremental is yes, this has no effect)
  resume: ask                       # Resume interrupted imports?
```

Whenever you run `beet import /music` with this config, it will:

* Files **stay in place** (no copy, no move)
* Already imported folders are skipped
* Duplicate tracks are removed
* Imports can resume if interrupted


**Importing** means scanning music files and adding them to the **Beets library database** (`library.db`).

Important:

> Importing does **not necessarily modify the music files**.
> It primarily registers them in the Beets database. Modifying the files is controlled by other settings like `write`, `copy`, `move`, etc.

**Tagging** means assigning metadata to music files.

Typical metadata fields:

* Artist
* Album
* Track title
* Track number
* Release year
* Genre
* MusicBrainz IDs

Tagging is usually done automatically via **MusicBrainz**.

**Autotagging** means automatically searching metadata databases and matching your music files and adding metadata to them.
Beets computes a **match distance score** to determine the best candidate using the match section.

#### Workflow:
- My [config.yaml](../../src/personal_os_setup/config/unix/beets/config.yaml)
What I advise to play with is:
- Use `-v` to see the output or `-vv` to see the details.
- Use `autotag: yes` with `write: no` will not write metadata into the files. This is useful to preview the changes.
- Use `autotag: yes` with `write: yes` , `timid: yes` and `quiet: no`  to validate manually when using the autotag the recommendations that are below the threshold
- finally full auto silently: `autotag: yes` and  `timid: no` and `quiet: yes`.  Quiet will skip (check quiet_fallback) tracks bellow the threshold.
- You can also play with  incremental and incremental_skip_later to skip some albums and tracks

#### Manual validation (review each album yourself)

Beets now runs in the **HA Beets addon**, so run the interactive review from the **Advanced SSH & Web Terminal** addon (web terminal — it has docker access). This overrides `quiet`/`timid` for this run only; the addon's automatic imports stay quiet/headless:

```bash
docker exec -it app_ffaaaf16_beets sh -c \
  'printf "import:\n  quiet: no\n  timid: yes\n" > /tmp/interactive.yaml && \
   /usr/local/bin/beet -c /data/beets/config.yaml -c /tmp/interactive.yaml import /media/music'
```

What you get, per album:

- The match with every change highlighted: `≠ Album: … -> …`, `≠ (#1) Title -> Title` (green = added, red = removed)
- The choice prompt: `[A]pply, More candidates, Skip, Use as-is, as Tracks, Group albums`
- Perfect to manually validate titles/artists/genres before accepting — press `a` to apply, `s` to skip

Notes:

- Container name is `app_ffaaaf16_beets` — the new supervisor names app containers `app_` (not `addon_`)
- Use the full path `/usr/local/bin/beet` — bare `beet` is not on PATH in docker exec shells
- After reviewing, the automatic quiet import keeps handling new downloads as usual

Add these commands to your crontab with `crontab -e`  to run it:
**Run every day (incremental import)**
`0 3 * * * flock -n /tmp/beets.lock ~/.venv/bin/beet -vv import ~/haos_media/music --incremental > ~/beets-cron.log 2>&1`

**Run every 5 minutes (no incremental)**
`*/5 * * * * flock -n /tmp/beets.lock ~/.venv/bin/beet -vv import ~/haos_media/music --noincremental > ~/beets-cron.log 2>&1`

You can also create a script to trigger them everytime your folder is updated.


### Finding duplicates:
Run this command :`beet duplicates -k title -k albumartist --full -p`

or to delete : `beet duplicates -k title -k albumartist --delete`

Add this to your crontab with `crontab -e`  to run it every 12 hours
```bash
0 */12 * * * date >> ~/beets-duplicates.log && echo "Running duplicates..." >> ~/beets-duplicates.log && ~/.venv/bin/beet duplicates -k title -k albumartist --delete >> ~/beets-duplicates.log 2>&1
```

[Chroma ](https://beets.readthedocs.io/en/stable/plugins/chroma.html#chromaprint-acoustid-plugin) :

**Chromaprint :**
wget https://github.com/acoustid/chromaprint/releases/download/v1.6.0/chromaprint-fpcalc-1.6.0-linux-x86_64.tar.gz
tar xvf chromaprint-*-Linux.tar.gz
tar xvf chromaprint-fpcalc-1.6.0-linux-x86_64.tar.gz
sudo mv chromaprint-*/fpcalc /usr/local/bin/\nsudo chmod +x /usr/local/bin/fpcalc
fpcalc -version


**gstreamer1.0:**
sudo apt-get update
sudo apt-get install -y \
libgstreamer-plugins-bad1.0-dev \
libgstreamer-plugins-base1.0-dev \
libgstreamer1.0-dev \
libglib2.0-dev \
libssl-dev \
libgirepository1.0-dev \
libcairo2-dev \
libportaudio2 \
libnice10 \
gstreamer1.0-plugins-good \
gstreamer1.0-alsa \
gstreamer1.0-plugins-bad \
gstreamer1.0-nice \
python3-gi \
python3-gi-cairo

**PyGObject, FFmpeg:**
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0
sudo apt install ffmpeg -y


Test it with :
fpcalc "path_to_file.flac"
