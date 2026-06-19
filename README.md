# tidpl — Tidal Playlist Maker

Create and maintain a **Tidal playlist** from your daily mix selection.

Fetches tracks from your Tidal mixes, picks a random daily selection, searches each track on Tidal, and pushes them into a playlist on your account — all automatically.

Uses the same auth and API as [tiddl](https://github.com/oskvr37/tiddl), but runs standalone.

---

## Quick Start

```bash
# One-off: export + push to "Deli Mix"
./run.sh run
```

---

## Commands

| Command | Description |
|---------|-------------|
| `run`  | Full pipeline: export daily selection from mixes → push to Tidal playlist |
| `export` | Only fetch tracks from mixes and generate `DailyTidal.txt` |
| `push`  | Only search tracks from a text file and push them to a Tidal playlist |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `-i, --input` | `data/mixes.txt` | File with mix/playlist URLs (one per line) |
| `-b, --blocklist` | `data/artist_blocklist.txt` | Artists to exclude |
| `-d, --daily` | `data/DailyTidal.txt` | Output daily selection file |
| `-o, --output` | `data/all_tracks.txt` | All collected tracks |
| `--history` | `data/daily_history.json` | Track selection history (dedup) |
| `-n, --count` | `100` | Number of tracks in daily selection |
| `--history-days` | `3` | Days to exclude a previously selected track |
| `--name` | `Deli Mix` | Tidal playlist name |
| `--desc` | `...` | Tidal playlist description |

### Examples

```bash
# Full pipeline with 50 tracks
./run.sh run --count 50

# Only export (no playlist changes)
./run.sh export --count 100

# Push an existing text file to a custom playlist
./run.sh push path/to/tracks.txt --name "My Mix"
```

---

## How It Works

1. **Export** — reads mix/playlist URLs from `data/mixes.txt`, fetches all tracks via Tidal API, removes duplicates and blocklisted artists, applies history dedup, and picks N random tracks.
2. **Push** — searches each `artist - title` on Tidal, creates a fresh playlist (deletes the old one if it exists), and adds all found tracks in batches of 100.

---

## Data Files

All data lives in `data/`:

| File | Purpose |
|------|---------|
| `auth.json` | Tidal auth token (required, see Setup) |
| `mixes.txt` | Mix/playlist URLs, one per line |
| `artist_blocklist.txt` | Blocked artist names |
| `DailyTidal.txt` | Generated daily selection |
| `all_tracks.txt` | All unique tracks from mixes |
| `daily_history.json` | History for dedup |
| `.last_run` | Marker for scheduler (last run timestamp) |

### mixes.txt example

```
https://tidal.com/mix/002031a111d26d855f13df60ef8035
https://tidal.com/mix/0020a08efcb74f0b86c8363bf5efae
```

### artist_blocklist.txt example

```
Taylor Swift
Eminem
```

### artist_aliases.txt (optional, placed in `data/`)

Format: `Name = Alias`, one per line.

```
Electric Callboy = Eskimo Callboy
```

---

## Scheduling

Three options:

### Option 1 — launchd (macOS native, recommended)

1. Copy `com.tidpl.scheduler.plist.example` to `com.tidpl.scheduler.plist` and edit the paths.
2. Run:

```bash
./service.sh install
./service.sh status
./service.sh uninstall
```

Runs `run-if-due.sh` every 6 hours, which only triggers `run` if 2+ days have passed since the last run.

### Option 2 — Persistent Python script

```bash
.venv/bin/python3 scheduler.py
```

Same logic, runs as a foreground process (Ctrl+C to stop). Checks every 6 hours.

### Option 3 — Cron

```bash
crontab -e
0 */6 * * * /ABSOLUTE/PATH/TO/tidpl/run-if-due.sh
```

---

## Setup

### Prerequisites

- Python 3.12+
- A Tidal HiFi or higher subscription
- `auth.json` in `data/` (Tidal session token)

### Getting auth.json

**If you have tiddl installed**, copy its auth file:

```bash
cp /path/to/tiddl/data/tiddl/auth.json data/
```

**Otherwise**, use tiddl's auth flow on this machine:

```bash
pip install tiddl
tiddl auth login
cp ~/.tiddl/auth.json /path/to/tidpl/data/
```

### First-time install

```bash
python3 -m venv .venv
.venv/bin/pip install -e .

# Create your mix list
cp data/mixes.txt.example data/mixes.txt    # then edit
cp data/artist_blocklist.txt.example data/artist_blocklist.txt  # optional, then edit

# Test
./run.sh run --count 10
```

---

## Project Structure

```
tidpl/
├── run.sh                 # Convenience launcher
├── run-if-due.sh          # Cron/launchd-friendly check-then-run
├── scheduler.py           # Persistent scheduler service
├── service.sh             # launchd management script
├── com.tidpl.scheduler.plist.example  # launchd config template
├── .gitignore
├── pyproject.toml
├── tidpl/
│   ├── cli.py             # Typer CLI
│   ├── auth.py            # Auth helpers
│   ├── playlist.py        # Export + playlist creation logic
│   └── vendor/            # Vendored tiddl modules (auth, API, models)
└── data/
    ├── auth.json          # (gitignored)
    ├── mixes.txt
    ├── artist_blocklist.txt
    ├── DailyTidal.txt
    ├── all_tracks.txt
    ├── daily_history.json
    └── scheduler.log
```

---

## Disclaimer

For personal use only. Not affiliated with Tidal. Ensure compliance with Tidal's Terms of Service.
