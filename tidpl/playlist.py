import json
import random
import re
import time as time_module
from logging import getLogger
from pathlib import Path

from .vendor.tiddl.core.api import TidalAPI
from .vendor.tiddl.core.api.client import API_URL
from .vendor.tiddl.core.api.models.resources import Track
from .vendor.tiddl.core.api.models.base import MixItems, PlaylistItems

log = getLogger(__name__)

# ── Shared helpers from tiddl export ─────────────────────────────


def _extract_id(raw: str) -> str:
    if "/" in raw:
        return raw.rsplit("/", 1)[-1].strip()
    return raw


def _detect_type(raw_url: str, resource_id: str) -> tuple[str, str]:
    lower = raw_url.lower()
    if "/mix/" in lower or lower.startswith("mix/"):
        return "mix", resource_id
    return "playlist", resource_id


def _get_mix_tracks(api: TidalAPI, mix_id: str) -> list[Track]:
    from .vendor.tiddl.core.api.api import Limits

    tracks: list[Track] = []
    offset = 0
    limit = Limits.MIX_ITEMS_MAX

    while True:
        page: MixItems = api.get_mix_items(mix_id, limit=limit, offset=offset)
        for item in page.items:
            tracks.append(item.item)
        if offset + limit >= page.totalNumberOfItems:
            break
        offset += limit

    return tracks


def _get_playlist_tracks(api: TidalAPI, playlist_uuid: str, total: int) -> list[Track]:
    from .vendor.tiddl.core.api.api import Limits

    tracks: list[Track] = []
    offset = 0
    limit = Limits.PLAYLIST_ITEMS_MAX

    while offset < total:
        page: PlaylistItems = api.get_playlist_items(
            playlist_uuid, limit=limit, offset=offset
        )
        for item in page.items:
            if item.type == "track":
                tracks.append(item.item)
        offset += limit

    return tracks


def _write_tracks(tracks: list[Track] | list[dict], path: Path) -> None:
    lines = []
    for t in tracks:
        if isinstance(t, dict):
            artist = ", ".join(a["name"] for a in t.get("artists", []))
            lines.append(f"{artist} - {t['title']}")
        else:
            artist = ", ".join(a.name for a in t.artists)
            lines.append(f"{artist} - {t.title}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Export daily ─────────────────────────────────────────────────


def export_daily(
    api: TidalAPI,
    mixes_file: Path,
    blocklist_file: Path,
    output_all: Path,
    output_daily: Path,
    history_file: Path,
    count: int = 100,
    history_days: int = 3,
) -> list[Track]:
    urls = [
        line.strip()
        for line in mixes_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not urls:
        raise ValueError(f"No URLs found in {mixes_file}")

    blocked: set[str] = set()
    if blocklist_file.exists():
        blocked = {
            line.strip().lower()
            for line in blocklist_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

    all_tracks: list[Track] = []
    seen_ids: set[int] = set()

    for url in urls:
        raw_id = _extract_id(url)
        resource_type, resource_id = _detect_type(url, raw_id)
        try:
            if resource_type == "mix":
                tracks = _get_mix_tracks(api, resource_id)
            else:
                pl = api.get_playlist(resource_id)
                tracks = _get_playlist_tracks(api, resource_id, pl.numberOfTracks)
        except Exception as e:
            log.warning("Skipping %s: %s", url, e)
            continue
        for t in tracks:
            if t.id not in seen_ids:
                seen_ids.add(t.id)
                all_tracks.append(t)

    if blocked:
        all_tracks = [
            t
            for t in all_tracks
            if not any(a.name.lower() in blocked for a in t.artists)
        ]

    _write_tracks(all_tracks, output_all)

    pool = all_tracks
    if history_file.exists():
        hist = json.loads(history_file.read_text(encoding="utf-8"))
        now = time_module.time()
        pool = [
            t
            for t in all_tracks
            if str(t.id) not in hist
            or (now - hist[str(t.id)]["last_selected"]) / 86400 > history_days
        ]

    pick_count = min(count, len(pool))
    picked = random.sample(pool, pick_count)
    _write_tracks(picked, output_daily)

    now = time_module.time()
    hist = {}
    if history_file.exists():
        hist = json.loads(history_file.read_text(encoding="utf-8"))
    cutoff = now - history_days * 2 * 86400
    hist = {k: v for k, v in hist.items() if v.get("last_selected", 0) > cutoff}
    for t in picked:
        hist[str(t.id)] = {
            "artist": ", ".join(a.name for a in t.artists),
            "title": t.title,
            "last_selected": now,
        }
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.write_text(
        json.dumps(hist, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return picked


# ── Parse track lines ────────────────────────────────────────────


def parse_track_line(line: str) -> tuple[str, str]:
    line = re.sub(r"\.(mp3|flac|wav|m4a)$", "", line, flags=re.IGNORECASE).strip()
    if " - " in line:
        artist, title = line.split(" - ", 1)
        return artist.strip(), title.strip()
    return "", line.strip()


# ── Search ───────────────────────────────────────────────────────


def search_tracks(api: TidalAPI, lines: list[str]) -> list[Track]:
    found: list[Track] = []
    not_found: list[tuple[str, str]] = []

    for line in lines:
        artist, title = parse_track_line(line)
        if not artist or not title:
            not_found.append(("", line))
            continue
        try:
            results = api.get_search(query=f"{artist} {title}")
            hits = results.tracks.items
            if hits:
                found.append(hits[0])
            else:
                not_found.append((artist, title))
        except Exception:
            not_found.append((artist, title))

    if not_found:
        log.warning("Not found on Tidal (%d tracks):", len(not_found))
        for a, t in not_found[:10]:
            sep = " - " if a else ""
            log.warning("  %s%s%s", a, sep, t)
        if len(not_found) > 10:
            log.warning("  ... and %d more", len(not_found) - 10)

    return found


# ── Tidal playlist API ───────────────────────────────────────────

# Tidal v1 uses form-urlencoded for write endpoints, not JSON.


def _form_post(api: TidalAPI, endpoint: str, form_data: dict) -> dict:
    """POST with application/x-www-form-urlencoded data."""
    resp = api.client.session.post(
        f"{API_URL}/{endpoint}",
        data=form_data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "If-None-Match": "*",
        },
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Tidal API error {resp.status_code}: {resp.text}")
    if resp.text:
        return resp.json()
    return {}


def _client_delete(api: TidalAPI, endpoint: str) -> None:
    resp = api.client.session.delete(f"{API_URL}/{endpoint}")
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"Tidal API error {resp.status_code}: {resp.text}")


def create_playlist(api: TidalAPI, title: str, description: str = "") -> str:
    data = _form_post(
        api,
        f"users/{api.user_id}/playlists",
        {"title": title},
    )
    uuid = data.get("uuid")
    if not uuid:
        raise RuntimeError(f"Unexpected response creating playlist: {data}")
    return uuid


def add_tracks_to_playlist(
    api: TidalAPI, playlist_uuid: str, track_ids: list[int]
) -> None:
    if not track_ids:
        return
    ids_str = ",".join(str(tid) for tid in track_ids)
    _form_post(
        api,
        f"playlists/{playlist_uuid}/items",
        {"onArtifactNotFound": "FAIL", "trackIds": ids_str},
    )


def delete_playlist(api: TidalAPI, playlist_uuid: str) -> None:
    _client_delete(api, f"playlists/{playlist_uuid}")


def _get_user_playlists(
    api: TidalAPI, limit: int = 200
) -> list[dict]:
    resp = api.client.session.get(
        f"{API_URL}/users/{api.user_id}/playlists",
        params={"countryCode": api.country_code, "limit": limit, "offset": 0},
        expire_after=0,
    )
    if resp.status_code != 200:
        return []
    data = resp.json()
    total = data.get("totalNumberOfItems", 0)
    items: list[dict] = data.get("items", [])
    offset = limit
    while offset < total:
        resp = api.client.session.get(
            f"{API_URL}/users/{api.user_id}/playlists",
            params={"countryCode": api.country_code, "limit": limit, "offset": offset},
            expire_after=0,
        )
        if resp.status_code != 200:
            break
        page = resp.json()
        items.extend(page.get("items", []))
        offset += limit
    return items


def find_playlist_by_title(api: TidalAPI, title: str) -> str | None:
    playlists = _get_user_playlists(api)
    target = title.strip().lower()
    for pl in playlists:
        if pl.get("title", "").strip().lower() == target:
            return pl.get("uuid")
    return None


def make_deli_mix_playlist(
    api: TidalAPI,
    tracks: list[Track],
    playlist_title: str = "Deli Mix",
    playlist_description: str = "Daily Tidal selection — created by tidpl",
) -> str:
    found_tracks = search_tracks(api, [
        f"{', '.join(a.name for a in t.artists)} - {t.title}" for t in tracks
    ])

    if not found_tracks:
        raise RuntimeError("No tracks found on Tidal.")

    existing = find_playlist_by_title(api, playlist_title)
    if existing:
        log.info("Deleting existing playlist '%s' (uuid=%s)", playlist_title, existing)
        delete_playlist(api, existing)

    uuid = create_playlist(api, playlist_title, playlist_description)
    track_ids = [t.id for t in found_tracks]

    # Add in batches to avoid overly long requests
    batch_size = 100
    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i : i + batch_size]
        add_tracks_to_playlist(api, uuid, batch)
        log.info("Added batch %d–%d of %d", i + 1, min(i + batch_size, len(track_ids)), len(track_ids))

    return uuid


def make_deli_mix_from_file(
    api: TidalAPI,
    track_file: Path,
    playlist_title: str = "Deli Mix",
    playlist_description: str = "Daily Tidal selection — created by tidpl",
) -> str:
    lines = [
        l.strip()
        for l in track_file.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    if not lines:
        raise ValueError(f"No tracks found in {track_file}")

    tracks = search_tracks(api, lines)
    if not tracks:
        raise RuntimeError("No tracks found on Tidal.")

    existing = find_playlist_by_title(api, playlist_title)
    if existing:
        log.info("Deleting existing playlist '%s' (uuid=%s)", playlist_title, existing)
        delete_playlist(api, existing)

    uuid = create_playlist(api, playlist_title, playlist_description)
    track_ids = [t.id for t in tracks]

    batch_size = 100
    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i : i + batch_size]
        add_tracks_to_playlist(api, uuid, batch)
        log.info(
            "Added batch %d–%d of %d",
            i + 1,
            min(i + batch_size, len(track_ids)),
            len(track_ids),
        )

    return uuid
