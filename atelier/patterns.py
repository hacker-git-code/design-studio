"""Brand patterns: algorithmic surfaces derived from the identity's own mark,
palette and DNA (for packaging, apparel prints, backgrounds, socials)."""

from __future__ import annotations

import math

import numpy as np

from .marks.families import PRIMS, pick
from .svg import document, el, f

PATTERNS = ("monogram", "truchet", "stripes", "halftone", "contour", "modules")


def choose_patterns(rng, idt, k=2) -> list[str]:
    d = idt.dna
    w = {
        "monogram": 0.6 + d.luxury * 1.4 + d.heritage * 0.6,
        "truchet": 0.4 + d.playful + d.geometric * 0.5,
        "stripes": 0.4 + d.energy * 0.8 + d.edge * 0.4,
        "halftone": 0.3 + d.edge * 0.8 + d.energy * 0.4,
        "contour": 0.3 + (1 - d.geometric) * 1.0 + d.warmth * 0.3,
        "modules": 0.3 + d.geometric * 0.9 + d.playful * 0.4,
    }
    out = []
    while len(out) < k:
        p = pick(rng, list(w), list(w.values()))
        if p not in out:
            out.append(p)
    return out


def pattern_svg(kind: str, idt, W=800, H=800, seed=0, invert=False) -> str:
    rng = np.random.default_rng(seed)
    p = idt.palette
    bg = p.primary if invert else p.paper
    fg = p.on(bg) if invert else p.mark_color()
    alt = p.secondary if not invert else p.accent
    defs, body = "", ""
    if kind == "monogram":
        n = 5 if idt.dna.minimal > 0.6 else 7
        cell = W / n
        size = cell * 0.42
        parts, dd = [], []
        for r in range(int(H / cell) + 2):
            for c in range(n + 1):
                x = c * cell + (cell / 2 if r % 2 else 0) - cell / 2
                y = r * cell - cell / 2
                d_, g_ = idt.mark.place(x + (cell - size) / 2, y + (cell - size) / 2, size, fg=fg, fg2=fg, fg3=fg, bg=bg, mono=True)
                dd.append(d_)
                parts.append(g_)
                if (r + c) % 2 == 0:
                    parts.append(el("circle", cx=f(x + cell), cy=f(y + cell / 2), r=f(cell * 0.03), fill=fg.hex))
        defs, body = "".join(dict.fromkeys(dd)), el("g", "".join(parts), opacity="0.9")
    elif kind == "truchet":
        n = int(rng.integers(6, 11))
        s = W / n
        t = s * rng.uniform(0.18, 0.3)
        parts = []
        for r in range(int(H / s) + 1):
            for c in range(n):
                x, y = c * s, r * s
                flip = rng.random() < 0.5
                if not flip:
                    d = (f"M{f(x + s / 2)} {f(y)}A{f(s / 2)} {f(s / 2)} 0 0 1 {f(x)} {f(y + s / 2)}"
                         f"M{f(x + s)} {f(y + s / 2)}A{f(s / 2)} {f(s / 2)} 0 0 0 {f(x + s / 2)} {f(y + s)}")
                else:
                    d = (f"M{f(x + s / 2)} {f(y)}A{f(s / 2)} {f(s / 2)} 0 0 0 {f(x + s)} {f(y + s / 2)}"
                         f"M{f(x)} {f(y + s / 2)}A{f(s / 2)} {f(s / 2)} 0 0 1 {f(x + s / 2)} {f(y + s)}")
                parts.append(d)
        body = el("path", d="".join(parts), fill="none", stroke=fg.hex, stroke_width=f(t), stroke_linecap="butt")
    elif kind == "stripes":
        ang = pick(rng, [0, 0, -45, 90, -20])
        seq = [1, 1, 2, 3, 5, 8]
        unit = W / rng.uniform(26, 44)
        cols = [fg, alt, p.accent, fg]
        parts, x, i = [], -W, 0
        while x < 2 * W:
            w = seq[i % len(seq)] * unit
            if i % 2 == 0:
                parts.append(el("rect", x=f(x), y=-H, width=f(w), height=3 * H, fill=cols[(i // 2) % len(cols)].hex))
            x += w
            i += 1
        body = el("g", "".join(parts), transform=f"rotate({ang} {W / 2} {H / 2})")
    elif kind == "halftone":
        n = int(rng.integers(18, 30))
        s = W / n
        ang = rng.uniform(0, math.pi)
        parts = []
        for r in range(int(H / s) + 1):
            for c in range(n + 1):
                x, y = c * s + (s / 2 if r % 2 else 0), r * s
                u = (x * math.cos(ang) + y * math.sin(ang)) / (W * 1.2)
                v = 0.5 + 0.5 * math.sin(u * math.pi * 2 + 0.3)
                rad = s * 0.48 * v
                if rad > 0.6:
                    parts.append(el("circle", cx=f(x), cy=f(y), r=f(rad)))
        body = el("g", "".join(parts), fill=fg.hex)
    elif kind == "contour":
        k = int(rng.integers(14, 24))
        parts = []
        cx, cy = rng.uniform(0.2, 0.8) * W, rng.uniform(0.2, 0.8) * H
        ph = rng.uniform(0, 6.28, 3)
        for i in range(k):
            R = (i + 1) * (max(W, H) * 0.9 / k)
            pts = []
            for j in range(72):
                a = 2 * math.pi * j / 72
                rr = R * (1 + 0.09 * math.sin(3 * a + ph[0] + i * 0.15) + 0.05 * math.sin(5 * a + ph[1]) + 0.03 * math.sin(7 * a + ph[2] - i * 0.1))
                pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
            from .svg import smooth_closed_path

            parts.append(el("path", d=smooth_closed_path(pts), fill="none", stroke=fg.hex if i % 4 else alt.hex,
                            stroke_width=f(W * (0.006 if i % 4 else 0.01))))
        body = "".join(parts)
    else:  # modules
        n = int(rng.integers(4, 8))
        s = W / n
        vocab = pick(rng, [["qc", "circle", "square"], ["arch", "half", "qc"], ["leaf", "qc", "dot"], ["tri", "square", "qc"]])
        cols = [fg, alt, p.accent, p.muted if not invert else p.paper]
        parts = []
        for r in range(int(H / s) + 1):
            for c in range(n):
                prim = pick(rng, vocab + ["empty"], [1, 1, 1, 0.4])
                if prim == "empty":
                    continue
                k = int(rng.integers(4))
                tr = f"translate({f(c * s)} {f(r * s)}) scale({f(s)}) translate(0.5 0.5) rotate({k * 90}) translate(-0.5 -0.5)"
                parts.append(el("path", d=PRIMS[prim], transform=tr, fill=cols[int(rng.integers(len(cols)))].hex))
        body = "".join(parts)
    return document(W, H, body, defs=defs, bg=bg.hex)
