"""Typography: a curated library of open-licensed (OFL) Google Fonts with
personality vectors, an on-demand fetch cache, and text-to-outline conversion
(HarfBuzz shaping, so kerning and ligatures are real). Logos ship as outlined
vector paths, exactly like a professional identity handoff."""

from __future__ import annotations

import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

AXES = ("geometric", "minimal", "warmth", "luxury", "energy", "heritage", "playful", "edge")

CACHE = Path(os.environ.get("ATELIER_CACHE", Path.home() / ".cache" / "atelier")) / "fonts"


@dataclass(frozen=True)
class FontSpec:
    family: str
    category: str              # sans | serif | display | mono | rounded | blackletter | condensed | wide
    weights: tuple[int, ...]
    traits: dict = field(default_factory=dict, hash=False, compare=False)
    text_ok: bool = False      # comfortable for body copy
    case: str = "any"          # preferred wordmark case: upper | lower | title | any

    def vector(self):
        return [self.traits.get(a, 0.5) for a in AXES]


def _F(family, category, weights, text_ok=False, case="any", **traits):
    return FontSpec(family, category, tuple(weights), traits, text_ok, case)


LIBRARY: list[FontSpec] = [
    # --- grotesk / geometric sans
    _F("Inter", "sans", (400, 500, 600, 700, 800), True, geometric=.6, minimal=.85, luxury=.3, energy=.4, heritage=.2, playful=.3, edge=.2, warmth=.4),
    _F("Manrope", "sans", (400, 500, 600, 700, 800), True, geometric=.75, minimal=.8, heritage=.1, playful=.35, edge=.25, luxury=.4),
    _F("Space Grotesk", "sans", (400, 500, 600, 700), True, geometric=.7, minimal=.55, heritage=.15, energy=.6, playful=.45, edge=.65),
    _F("Sora", "sans", (400, 500, 600, 700, 800), True, geometric=.9, minimal=.7, heritage=.05, energy=.55, playful=.4, edge=.4),
    _F("Syne", "wide", (400, 500, 600, 700, 800), False, "upper", geometric=.6, minimal=.25, energy=.85, playful=.55, edge=.75, heritage=.15, luxury=.45),
    _F("Unbounded", "wide", (400, 500, 600, 700, 800, 900), False, "lower", geometric=.85, minimal=.35, energy=.9, playful=.65, edge=.6, heritage=.05),
    _F("DM Sans", "sans", (400, 500, 600, 700), True, geometric=.85, minimal=.75, playful=.45, warmth=.5, heritage=.2),
    _F("Plus Jakarta Sans", "sans", (400, 500, 600, 700, 800), True, geometric=.7, minimal=.7, warmth=.55, heritage=.2, playful=.4),
    _F("Outfit", "sans", (300, 400, 500, 600, 700, 800), True, "lower", geometric=.95, minimal=.8, playful=.5, heritage=.1),
    _F("Bricolage Grotesque", "sans", (400, 500, 600, 700, 800), True, geometric=.35, minimal=.3, playful=.75, edge=.55, warmth=.65, energy=.65, heritage=.4),
    _F("Instrument Sans", "sans", (400, 500, 600, 700), True, geometric=.6, minimal=.85, luxury=.55, heritage=.3, energy=.35),
    _F("Hanken Grotesk", "sans", (300, 400, 500, 600, 700, 800), True, geometric=.6, minimal=.8, luxury=.45, heritage=.3),
    _F("Figtree", "sans", (300, 400, 500, 600, 700, 800, 900), True, geometric=.7, minimal=.7, playful=.55, warmth=.6),
    _F("Familjen Grotesk", "sans", (400, 500, 600, 700), True, geometric=.4, minimal=.55, edge=.55, heritage=.45, energy=.55),
    _F("Schibsted Grotesk", "sans", (400, 500, 600, 700, 800, 900), True, geometric=.55, minimal=.6, heritage=.5, edge=.4, luxury=.4),
    _F("Archivo Black", "display", (400,), False, "upper", geometric=.6, minimal=.45, energy=.9, edge=.75, playful=.4, heritage=.35),
    _F("Poppins", "sans", (300, 400, 500, 600, 700, 800), True, "lower", geometric=.95, minimal=.65, playful=.55, warmth=.5, heritage=.15),
    # --- condensed / industrial / street
    _F("Bebas Neue", "condensed", (400,), False, "upper", geometric=.65, minimal=.55, energy=.8, edge=.8, heritage=.45, playful=.3),
    _F("Anton", "condensed", (400,), False, "upper", geometric=.6, minimal=.4, energy=.95, edge=.9, heritage=.35, playful=.3),
    _F("Big Shoulders Display", "condensed", (400, 500, 600, 700, 800, 900), False, "upper", geometric=.7, minimal=.55, energy=.75, edge=.85, heritage=.55),
    _F("Oswald", "condensed", (400, 500, 600, 700), False, "upper", geometric=.6, minimal=.55, energy=.7, edge=.65, heritage=.5),
    _F("Dela Gothic One", "display", (400,), False, "upper", geometric=.7, minimal=.3, energy=.95, edge=.9, playful=.55, heritage=.2),
    _F("Rubik Mono One", "display", (400,), False, "upper", geometric=.85, minimal=.4, energy=.85, playful=.75, edge=.6),
    # --- tech / wide
    _F("Chakra Petch", "sans", (400, 500, 600, 700), False, "upper", geometric=.95, minimal=.5, energy=.7, edge=.7, heritage=0.0, playful=.3),
    _F("Michroma", "wide", (400,), False, "upper", geometric=.95, minimal=.75, luxury=.55, heritage=0.0, energy=.5, edge=.5),
    # --- serifs
    _F("Fraunces", "serif", (300, 400, 500, 600, 700, 800, 900), True, "title", geometric=.2, minimal=.35, warmth=.85, luxury=.55, heritage=.75, playful=.7, energy=.5),
    _F("Playfair Display", "serif", (400, 500, 600, 700, 800, 900), False, "title", geometric=.2, minimal=.5, luxury=.85, heritage=.8, energy=.45, warmth=.55),
    _F("Cormorant Garamond", "serif", (300, 400, 500, 600, 700), False, "upper", geometric=.15, minimal=.65, luxury=.95, heritage=.9, energy=.1, warmth=.55),
    _F("Instrument Serif", "serif", (400,), False, "title", geometric=.25, minimal=.7, luxury=.75, heritage=.6, energy=.35, edge=.35),
    _F("DM Serif Display", "serif", (400,), False, "title", geometric=.3, minimal=.5, luxury=.75, heritage=.7, energy=.55, warmth=.6),
    _F("EB Garamond", "serif", (400, 500, 600, 700, 800), True, geometric=.1, minimal=.6, luxury=.75, heritage=.95, energy=.2, warmth=.6),
    _F("Newsreader", "serif", (300, 400, 500, 600, 700, 800), True, geometric=.25, minimal=.65, luxury=.55, heritage=.75, energy=.3),
    _F("Gloock", "serif", (400,), False, "title", geometric=.35, minimal=.45, luxury=.8, heritage=.6, energy=.65, edge=.5),
    _F("Young Serif", "serif", (400,), False, "title", geometric=.3, minimal=.45, warmth=.85, heritage=.7, playful=.6, energy=.45),
    _F("Bodoni Moda", "serif", (400, 500, 600, 700, 800, 900), False, "upper", geometric=.4, minimal=.6, luxury=.95, heritage=.8, energy=.5, edge=.35),
    _F("Italiana", "serif", (400,), False, "upper", geometric=.4, minimal=.95, luxury=.95, heritage=.55, energy=.1, edge=.2),
    _F("Marcellus", "serif", (400,), False, "upper", geometric=.35, minimal=.8, luxury=.85, heritage=.9, energy=.2),
    _F("Cinzel", "serif", (400, 500, 600, 700, 800, 900), False, "upper", geometric=.35, minimal=.6, luxury=.8, heritage=1.0, energy=.3),
    _F("Libre Caslon Text", "serif", (400, 700), True, geometric=.15, minimal=.6, luxury=.7, heritage=.9, warmth=.6),
    # --- blackletter (streetwear staple)
    _F("Grenze Gotisch", "blackletter", (400, 500, 600, 700, 800, 900), False, "title", geometric=.2, minimal=.2, luxury=.5, heritage=.95, energy=.75, edge=.95, playful=.3),
    _F("UnifrakturMaguntia", "blackletter", (400,), False, "title", geometric=.1, minimal=.15, heritage=1.0, energy=.6, edge=.9, luxury=.55),
    # --- rounded / friendly
    _F("Nunito", "rounded", (400, 500, 600, 700, 800, 900), True, "lower", geometric=.55, minimal=.6, warmth=.8, playful=.85, edge=.05, energy=.5),
    _F("Fredoka", "rounded", (400, 500, 600, 700), False, "lower", geometric=.6, minimal=.45, warmth=.85, playful=.95, edge=.05, energy=.65),
    _F("Quicksand", "rounded", (400, 500, 600, 700), True, "lower", geometric=.8, minimal=.8, warmth=.7, playful=.7, edge=.05, energy=.3),
    _F("Baloo 2", "rounded", (400, 500, 600, 700, 800), False, "lower", geometric=.4, minimal=.35, warmth=.85, playful=1.0, edge=.1, energy=.8),
    # --- mono
    _F("JetBrains Mono", "mono", (400, 500, 600, 700, 800), True, geometric=.75, minimal=.7, heritage=.1, edge=.5, energy=.5),
    _F("IBM Plex Mono", "mono", (400, 500, 600, 700), True, geometric=.6, minimal=.7, heritage=.35, edge=.4),
    _F("Space Mono", "mono", (400, 700), True, geometric=.7, minimal=.5, heritage=.3, edge=.65, playful=.45, energy=.55),
    _F("DM Mono", "mono", (300, 400, 500), True, geometric=.8, minimal=.85, heritage=.2, edge=.35),
]

BY_NAME = {f.family: f for f in LIBRARY}


def nearest_weight(spec: FontSpec, w: int) -> int:
    return min(spec.weights, key=lambda x: abs(x - w))


# -------------------------------------------------------------------- fetch

_UA = "Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101"  # old UA -> TTF urls


def font_path(family: str, weight: int = 400) -> Path:
    spec = BY_NAME.get(family)
    if spec:
        weight = nearest_weight(spec, weight)
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{re.sub(r'[^A-Za-z0-9]', '', family)}-{weight}.ttf"
    if p.exists() and p.stat().st_size > 1000:
        return p
    q = urllib.parse.quote(family)
    url = f"https://fonts.googleapis.com/css2?family={q}:wght@{weight}"
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        css = urllib.request.urlopen(req, timeout=20).read().decode()
        m = re.search(r"url\((https://[^)]+\.ttf)\)", css)
        if not m:
            raise RuntimeError("no ttf in css response")
        data = urllib.request.urlopen(m.group(1), timeout=30).read()
        p.write_bytes(data)
        return p
    except Exception as e:  # pragma: no cover - network dependent
        fb = _fallback_font()
        if fb:
            return fb
        raise RuntimeError(f"Could not fetch font {family} {weight}: {e}. "
                           "Connect to the internet once so fonts can be cached.") from e


def _fallback_font() -> Path | None:
    for d in ("/usr/share/fonts", "/Library/Fonts", "C:/Windows/Fonts"):
        for p in Path(d).rglob("*.ttf") if Path(d).exists() else []:
            if "DejaVuSans" in p.name or "Arial" in p.name:
                return p
    return None


def google_css_url(families: dict[str, set[int]]) -> str:
    parts = []
    for fam, ws in families.items():
        spec = BY_NAME.get(fam)
        ws = sorted({nearest_weight(spec, w) if spec else w for w in ws})
        parts.append(f"family={urllib.parse.quote_plus(fam)}:wght@{';'.join(map(str, ws))}")
    return "https://fonts.googleapis.com/css2?" + "&".join(parts) + "&display=swap"


# ------------------------------------------------------------------ outlining


class LoadedFont:
    def __init__(self, path: Path):
        import uharfbuzz as hb
        from fontTools.ttLib import TTFont

        self.path = path
        self.tt = TTFont(str(path))
        self.upem = self.tt["head"].unitsPerEm
        self.glyphset = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        blob = hb.Blob.from_file_path(str(path))
        self.hb_face = hb.Face(blob)
        self.hb_font = hb.Font(self.hb_face)
        os2 = self.tt["OS/2"] if "OS/2" in self.tt else None
        hhea = self.tt["hhea"]
        self.ascender = hhea.ascent
        self.descender = hhea.descent
        cap = getattr(os2, "sCapHeight", 0) if os2 else 0
        xh = getattr(os2, "sxHeight", 0) if os2 else 0
        self.cap_height = cap or self._glyph_height("H") or self.upem * 0.7
        self.x_height = xh or self._glyph_height("x") or self.upem * 0.5
        self._cache: dict[int, str] = {}

    def _glyph_height(self, ch):
        from fontTools.pens.boundsPen import BoundsPen

        cmap = self.tt.getBestCmap()
        gn = cmap.get(ord(ch))
        if not gn:
            return 0
        bp = BoundsPen(self.glyphset)
        self.glyphset[gn].draw(bp)
        return bp.bounds[3] if bp.bounds else 0

    def glyph_d(self, gid: int) -> str:
        if gid in self._cache:
            return self._cache[gid]
        from fontTools.pens.svgPathPen import SVGPathPen

        pen = SVGPathPen(self.glyphset)
        self.glyphset[self.order[gid]].draw(pen)
        d = pen.getCommands()
        self._cache[gid] = d
        return d

    def shape(self, text: str, features=None):
        import uharfbuzz as hb

        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf, features or {"kern": True, "liga": True})
        return buf.glyph_infos, buf.glyph_positions


@lru_cache(maxsize=64)
def load(family: str, weight: int = 400) -> LoadedFont:
    return LoadedFont(font_path(family, weight))


@dataclass
class TextRun:
    d: list[tuple[str, float, float]]   # (glyph path in font units, x offset units, y offset units)
    width: float                        # px at the requested size
    size: float
    font: LoadedFont
    ink: tuple[float, float, float, float] | None = None  # x0,y0,x1,y1 relative to baseline origin

    @property
    def cap(self):
        return self.font.cap_height / self.font.upem * self.size

    @property
    def xh(self):
        return self.font.x_height / self.font.upem * self.size

    def svg(self, x: float, y: float, fill: str, **extra) -> str:
        """Place with baseline-left origin at (x,y)."""
        s = self.size / self.font.upem
        from .svg import f as F

        parts = []
        for d, gx, gy in self.d:
            if not d:
                continue
            parts.append(f'<path transform="matrix({F(s)} 0 0 {F(-s)} {F(x + gx * s)} {F(y - gy * s)})" d="{d}"/>')
        ex = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in extra.items())
        return f'<g fill="{fill}" {ex}>{"".join(parts)}</g>'


def outline(text: str, family: str, weight: int, size: float, tracking: float = 0.0,
            features=None) -> TextRun:
    """Shape `text` and return outlined glyphs. tracking is in em (e.g. 0.12)."""
    from fontTools.pens.boundsPen import BoundsPen

    fnt = load(family, weight)
    infos, poss = fnt.shape(text, features)
    track_u = tracking * fnt.upem
    x = 0.0
    glyphs = []
    x0 = y0 = float("inf")
    x1 = y1 = float("-inf")
    for i, (info, pos) in enumerate(zip(infos, poss)):
        gid = info.codepoint
        gx, gy = x + pos.x_offset, pos.y_offset
        glyphs.append((fnt.glyph_d(gid), gx, gy))
        bp = BoundsPen(fnt.glyphset)
        fnt.glyphset[fnt.order[gid]].draw(bp)
        if bp.bounds:
            bx0, by0, bx1, by1 = bp.bounds
            x0, x1 = min(x0, gx + bx0), max(x1, gx + bx1)
            y0, y1 = min(y0, gy + by0), max(y1, gy + by1)
        x += pos.x_advance + (track_u if i < len(infos) - 1 else 0)
    s = size / fnt.upem
    ink = None
    if x0 != float("inf"):
        # in px, y-up converted to y-down relative to baseline
        ink = (x0 * s, -y1 * s, x1 * s, -y0 * s)
    return TextRun(glyphs, x * s, size, fnt, ink)


def apply_case(text: str, case: str) -> str:
    if case == "upper":
        return text.upper()
    if case == "lower":
        return text.lower()
    if case == "title":
        return " ".join(w[:1].upper() + w[1:] for w in text.split(" "))
    return text
