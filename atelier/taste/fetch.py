"""Collect reference images you are allowed to use.

* `fetch_urls`: download a plain list of image URLs (one per line, optional
  caption after a tab or " | ").
* `pinterest_board`: pull pins from *your own* Pinterest boards through the
  official API v5 (create an app at developers.pinterest.com, generate an
  access token with boards:read + pins:read). Pin titles/descriptions become
  captions for the LLM dataset.

The taste model stores only statistics (palette structure, composition), not
images, but respect each source's terms and the creators' rights anyway.
"""

from __future__ import annotations

import csv
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (compatible; atelier-taste/0.1)"


def _get(url, headers=None, timeout=30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    return urllib.request.urlopen(req, timeout=timeout).read()


def _ext(url: str, data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    return Path(urllib.parse.urlparse(url).path).suffix.lower() or ".jpg"


def fetch_urls(urls_file: Path, out: Path, delay: float = 1.0) -> int:
    out.mkdir(parents=True, exist_ok=True)
    caps_path = out / "captions.csv"
    rows = []
    n = 0
    for line in Path(urls_file).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        url, cap = (line.split("\t", 1) + [""])[:2] if "\t" in line else (line.split(" | ", 1) + [""])[:2]
        try:
            data = _get(url.strip())
        except Exception as e:
            print(f"  skip {url[:70]}: {e}")
            continue
        name = hashlib.sha1(url.encode()).hexdigest()[:16] + _ext(url, data)
        (out / name).write_bytes(data)
        rows.append((name, cap.strip()))
        n += 1
        time.sleep(delay)
    if any(c for _, c in rows):
        with caps_path.open("a", newline="") as fh:
            csv.writer(fh).writerows(rows)
    print(f"[fetch] {n} images -> {out}")
    return n


def pinterest_boards(token: str) -> list[dict]:
    out, bookmark = [], None
    while True:
        q = {"page_size": 100, **({"bookmark": bookmark} if bookmark else {})}
        d = json.loads(_get("https://api.pinterest.com/v5/boards?" + urllib.parse.urlencode(q), {"Authorization": f"Bearer {token}"}))
        out += [{"id": b["id"], "name": b.get("name", "")} for b in d.get("items", [])]
        bookmark = d.get("bookmark")
        if not bookmark:
            return out


def pinterest_board(token: str, board_id: str, out: Path, delay: float = 0.5, limit: int = 1000) -> int:
    """Download images + captions from one of your boards."""
    out.mkdir(parents=True, exist_ok=True)
    rows, bookmark, n = [], None, 0
    while n < limit:
        q = {"page_size": 100, **({"bookmark": bookmark} if bookmark else {})}
        d = json.loads(_get(f"https://api.pinterest.com/v5/boards/{board_id}/pins?" + urllib.parse.urlencode(q),
                            {"Authorization": f"Bearer {token}"}))
        for pin in d.get("items", []):
            imgs = (pin.get("media") or {}).get("images") or {}
            best = imgs.get("1200x") or imgs.get("originals") or imgs.get("600x") or next(iter(imgs.values()), None)
            if not best or not best.get("url"):
                continue
            try:
                data = _get(best["url"])
            except Exception:
                continue
            name = f"pin-{pin['id']}{_ext(best['url'], data)}"
            (out / name).write_bytes(data)
            cap = " — ".join(x for x in (pin.get("title"), pin.get("description")) if x)
            rows.append((name, " ".join(cap.split())[:300]))
            n += 1
            time.sleep(delay)
        bookmark = d.get("bookmark")
        if not bookmark:
            break
    with (out / "captions.csv").open("a", newline="") as fh:
        csv.writer(fh).writerows(rows)
    print(f"[pinterest] {n} pins -> {out}")
    return n
