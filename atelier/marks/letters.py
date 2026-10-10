"""A constructed skeleton alphabet.

Each glyph is a set of centre-line polylines on a grid 10 units tall. Stroked
with a chosen weight, corner radius and cap, the same skeleton yields anything
from squared tech lettering (r=0) to round geometric (r=max) to stencil and
inline monograms, so every brand gets its own lettering, not a font.

Points can carry a third value 0 to keep that corner sharp regardless of r.
"""

from __future__ import annotations

from ..svg import rounded_polyline

H = 10.0

# (width, [polyline, ...]); polyline points are (x, y) with y down.
SKELETON: dict[str, tuple[float, list[list[tuple]]]] = {
    "A": (6.4, [[(0, 10), (3.2, 0), (6.4, 10)], [(1.12, 6.5), (5.28, 6.5)]]),
    "B": (5.8, [[(0, 0), (0, 10)], [(0, 0), (4.8, 0), (4.8, 4.8), (0, 4.8)], [(0, 4.8), (5.8, 4.8), (5.8, 10), (0, 10)]]),
    "C": (6.2, [[(6.2, 0), (0, 0), (0, 10), (6.2, 10)]]),
    "D": (6.4, [[(0, 0), (0, 10)], [(0, 0), (6.4, 0), (6.4, 10), (0, 10)]]),
    "E": (5.4, [[(5.4, 0), (0, 0), (0, 10), (5.4, 10)], [(0, 4.9), (4.6, 4.9)]]),
    "F": (5.2, [[(5.2, 0), (0, 0), (0, 10)], [(0, 4.9), (4.5, 4.9)]]),
    "G": (6.4, [[(6.4, 0), (0, 0), (0, 10), (6.4, 10), (6.4, 5), (3.4, 5)]]),
    "H": (6.2, [[(0, 0), (0, 10)], [(6.2, 0), (6.2, 10)], [(0, 5), (6.2, 5)]]),
    "I": (0.0, [[(0, 0), (0, 10)]]),
    "J": (5.2, [[(5.2, 0), (5.2, 10), (0, 10), (0, 7)]]),
    "K": (6.0, [[(0, 0), (0, 10)], [(6.0, 0), (0, 6.0)], [(2.3, 3.7), (6.0, 10)]]),
    "L": (5.0, [[(0, 0), (0, 10), (5.0, 10)]]),
    "M": (8.0, [[(0, 10), (0, 0), (4.0, 6.5), (8.0, 0), (8.0, 10)]]),
    "N": (6.2, [[(0, 10), (0, 0), (6.2, 10), (6.2, 0)]]),
    "O": (6.8, [[(0, 0), (6.8, 0), (6.8, 10), (0, 10)]]),  # closed
    "P": (5.8, [[(0, 10), (0, 0), (5.8, 0), (5.8, 5.4), (0, 5.4)]]),
    "Q": (6.8, [[(0, 0), (6.8, 0), (6.8, 10), (0, 10)], [(4.2, 7.2), (7.2, 10.6)]]),  # first closed
    "R": (5.8, [[(0, 10), (0, 0), (5.8, 0), (5.8, 5.4), (0, 5.4)], [(2.8, 5.4), (5.8, 10)]]),
    "S": (5.8, [[(5.8, 0), (0, 0), (0, 5), (5.8, 5), (5.8, 10), (0, 10)]]),
    "T": (6.0, [[(0, 0), (6.0, 0)], [(3.0, 0), (3.0, 10)]]),
    "U": (6.2, [[(0, 0), (0, 10), (6.2, 10), (6.2, 0)]]),
    "V": (6.4, [[(0, 0), (3.2, 10), (6.4, 0)]]),
    "W": (8.8, [[(0, 0), (2.2, 10), (4.4, 1.5), (6.6, 10), (8.8, 0)]]),
    "X": (6.2, [[(0, 0), (6.2, 10)], [(6.2, 0), (0, 10)]]),
    "Y": (6.4, [[(0, 0), (3.2, 5.2), (6.4, 0)], [(3.2, 5.2), (3.2, 10)]]),
    "Z": (6.0, [[(0, 0), (6.0, 0), (0, 10), (6.0, 10)]]),
    "0": (6.4, [[(0, 0), (6.4, 0), (6.4, 10), (0, 10)]]),
    "1": (3.0, [[(0, 2.2), (3.0, 0), (3.0, 10)]]),
    "2": (5.8, [[(0, 0), (5.8, 0), (5.8, 5), (0, 5), (0, 10), (5.8, 10)]]),
    "3": (5.8, [[(0, 0), (5.8, 0), (5.8, 10), (0, 10)], [(1.6, 5), (5.8, 5)]]),
    "4": (6.0, [[(4.6, 10), (4.6, 0), (0, 7), (6.0, 7)]]),
    "5": (5.8, [[(5.8, 0), (0, 0), (0, 5), (5.8, 5), (5.8, 10), (0, 10)]]),
    "6": (6.0, [[(6.0, 0), (0, 0), (0, 10), (6.0, 10), (6.0, 5), (0, 5)]]),
    "7": (5.8, [[(0, 0), (5.8, 0), (2.0, 10)]]),
    "8": (6.0, [[(0, 0), (6.0, 0), (6.0, 10), (0, 10)], [(0, 5), (6.0, 5)]]),
    "9": (6.0, [[(6.0, 5), (0, 5), (0, 0), (6.0, 0), (6.0, 10), (0, 10)]]),
}
CLOSED = {"O": {0}, "Q": {0}, "0": {0}, "8": {0}}


def glyph_paths(ch: str, radius: float, width_scale: float = 1.0, x0: float = 0.0, y0: float = 0.0,
                scale: float = 1.0) -> tuple[list[str], float]:
    """Return (list of svg path d for centre-lines, advance width) for a letter."""
    ch = ch.upper()
    if ch not in SKELETON:
        ch = "O"
    w, lines = SKELETON[ch]
    ds = []
    for i, pl in enumerate(lines):
        pts = [((p[0] * width_scale) * scale + x0, p[1] * scale + y0) for p in pl]
        closed = i in CLOSED.get(ch, set())
        ds.append(rounded_polyline(pts, radius * scale, closed=closed))
    return ds, w * width_scale * scale


def word_paths(text: str, radius: float, weight: float, width_scale: float = 1.0,
               gap: float | None = None) -> tuple[list[str], float]:
    """Centre-line paths for a short string in grid units, plus total width.
    Overall ink box: x in [-weight/2, width+weight/2], y in [-weight/2, 10+weight/2]."""
    gap = weight * 1.35 if gap is None else gap
    x = 0.0
    out = []
    for i, ch in enumerate(text):
        ds, adv = glyph_paths(ch, radius, width_scale, x0=x)
        out.extend(ds)
        x += adv + (weight + gap if i < len(text) - 1 else 0)
    return out, x
