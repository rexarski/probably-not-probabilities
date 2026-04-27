"""
One-shot scraper: pulls track URIs out of a public Spotify playlist embed
page, hits the unauthenticated oEmbed endpoint per track for the album-cover
thumbnail URL, and downloads each cover into web/static/data/covers/.

No Spotify API credentials required. Stdlib only.

Usage:
    uv run python/scrape_covers.py
    # or
    python python/scrape_covers.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

PLAYLIST_IDS = [
    "37i9dQZEVXbNG2KDcFcKOF",  # Top Songs - Global
    "5ABHKGoOzxkaa28ttQV9sE",  # second playlist
]
EMBED_TMPL = "https://open.spotify.com/embed/playlist/{playlist_id}"
OEMBED_TMPL = "https://open.spotify.com/oembed?url=https://open.spotify.com/track/{track_id}"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)

REPO = Path(__file__).resolve().parent.parent
COVERS_DIR = REPO / "web" / "static" / "data" / "covers"
MANIFEST = REPO / "web" / "static" / "data" / "covers.json"


def fetch(url: str, *, timeout: float = 20.0) -> bytes:
    req = Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urlopen(req, timeout=timeout) as r:
        return r.read()


def extract_tracks(embed_html: str) -> list[dict]:
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        embed_html,
        re.S,
    )
    if not m:
        raise RuntimeError("No __NEXT_DATA__ blob found in embed page")
    data = json.loads(m.group(1))
    track_list = data["props"]["pageProps"]["state"]["data"]["entity"]["trackList"]
    out = []
    for t in track_list:
        uri = t.get("uri", "")
        if not uri.startswith("spotify:track:"):
            continue
        out.append(
            {
                "id": uri.split(":")[-1],
                "title": t.get("title", ""),
                "subtitle": t.get("subtitle", ""),
            }
        )
    return out


def oembed_thumbnail(track_id: str) -> str | None:
    url = OEMBED_TMPL.format(track_id=quote(track_id, safe=""))
    try:
        body = fetch(url)
    except Exception as e:
        print(f"  oembed fail {track_id}: {e}", file=sys.stderr)
        return None
    try:
        return json.loads(body).get("thumbnail_url")
    except Exception:
        return None


def main() -> int:
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    seen_ids: set[str] = set()
    tracks: list[dict] = []
    for pid in PLAYLIST_IDS:
        print(f"Fetching embed page for playlist {pid} ...")
        try:
            embed_html = fetch(EMBED_TMPL.format(playlist_id=pid)).decode(
                "utf-8", errors="replace"
            )
        except Exception as e:
            print(f"  embed fetch fail for {pid}: {e}", file=sys.stderr)
            continue
        new = extract_tracks(embed_html)
        added = 0
        for t in new:
            if t["id"] in seen_ids:
                continue
            seen_ids.add(t["id"])
            tracks.append(t)
            added += 1
        print(f"  {len(new)} tracks ({added} new)")
    print(f"Total {len(tracks)} unique tracks. Resolving covers ...")

    manifest = []
    for i, t in enumerate(tracks, 1):
        thumb = oembed_thumbnail(t["id"])
        if not thumb:
            print(f"  [{i:02d}] {t['title'][:40]:40s}  (no thumb)")
            continue
        # Spotify thumbnails are JPEG. The path ends with the image hash.
        out_name = f"{t['id']}.jpg"
        out_path = COVERS_DIR / out_name
        if not out_path.exists():
            try:
                img = fetch(thumb)
                out_path.write_bytes(img)
            except Exception as e:
                print(f"  [{i:02d}] download fail: {e}")
                continue
        manifest.append(
            {
                "id": t["id"],
                "title": t["title"],
                "subtitle": t["subtitle"],
                "file": f"covers/{out_name}",
            }
        )
        print(f"  [{i:02d}] {t['title'][:40]:40s}  ✓")
        time.sleep(0.15)  # be polite

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\nWrote {len(manifest)} covers → {COVERS_DIR}")
    print(f"Wrote manifest → {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
