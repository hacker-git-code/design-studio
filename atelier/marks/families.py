"""Procedural symbol families.

Every generator is a constrained design system rather than random noise:
a small vocabulary of primitives, a symmetry group, a proportion system and
DNA-driven parameter ranges. Constraints are what make the output look
designed instead of generated.
"""

from __future__ import annotations

import math

from ..svg import (circle_path, el, f, poly_path, polar, rect_path, regular_polygon,
                   smooth_closed_path, superellipse_pts, uid)
from .base import Mark
from .letters import SKELETON, word_paths

PHI = (1 + 5 ** 0.5) / 2
C = 50.0  # centre of the 100x100 box


def pick(rng, options, weights=None):
    if weights is None:
        return options[int(rng.integers(len(options)))]
    w = [max(1e-6, x) for x in weights]
    s = sum(w)
    return options[int(rng.choice(len(options), p=[x / s for x in w]))]


def lerp(a, b, t):
    return a + (b - a) * t


def _rot(deg, cx=C, cy=C):
    return f"rotate({f(deg)} {f(cx)} {f(cy)})"


def _shape_path(kind: str, r: float, cx=C, cy=C, rad=0.22) -> str:
    if kind == "circle":
        return circle_path(cx, cy, r)
    if kind == "squircle":
        return poly_path(superellipse_pts(cx, cy, r, r, 4.6, 160))
    if kind == "square":
        return rect_path(cx - r, cy - r, 2 * r, 2 * r, r * rad)
    if kind == "hexagon":
        from ..svg import rounded_polyline
        return rounded_polyline(regular_polygon(cx, cy, r * 1.06, 6, -90), r * 0.12, closed=True)
    if kind == "triangle":
        from ..svg import rounded_polyline
        pts = regular_polygon(cx, cy + r * 0.18, r * 1.22, 3, -90)
        return rounded_polyline(pts, r * 0.16, closed=True)
    if kind == "shield":
        return (f"M{f(cx - r)} {f(cy - r)}H{f(cx + r)}V{f(cy)}"
                f"C{f(cx + r)} {f(cy + r * .7)} {f(cx + r * .3)} {f(cy + r * .95)} {f(cx)} {f(cy + r * 1.1)}"
                f"C{f(cx - r * .3)} {f(cy + r * .95)} {f(cx - r)} {f(cy + r * .7)} {f(cx - r)} {f(cy)}Z")
    raise ValueError(kind)


def _mask(content: str, base: str | None = None) -> tuple[str, str]:
    mid = uid("m")
    base = base if base is not None else el("rect", x=-50, y=-50, width=200, height=200, fill="white")
    return mid, el("mask", base + content, id=mid, maskUnits="userSpaceOnUse", x=-50, y=-50, width=200, height=200)


# ------------------------------------------------------------------- monogram

RIGHT_STEM = set("HIMNU")
LEFT_STEM = set("BDEFHIKLMNPRU")


def letter_style(rng, dna) -> dict:
    """Shared lettering parameters so monograms, emblems and patterns agree."""
    e, g, p, edge, lux = dna.energy, dna.geometric, dna.playful, dna.edge, dna.luxury
    weight = lerp(1.05, 2.5, 0.55 * e + 0.35 * edge + 0.2 * p - 0.35 * lux) + rng.uniform(-0.15, 0.15)
    weight = max(0.8, min(2.7, weight))
    rr = pick(rng, [0.0, 0.5, 1.4, 2.4, 3.4], [0.6 + 1.4 * edge * g, 0.6 + edge, 1.0, 0.6 + p + (1 - edge), 0.3 + 1.6 * p + 0.6 * (1 - edge)])
    cap = pick(rng, ["butt", "square", "round"], [0.6 + 1.2 * lux + dna.heritage, 0.4 + edge + g, 0.2 + 1.6 * p + (1 - edge) * 0.4])
    if rr >= 2.4 and cap == "square":
        cap = "round"
    width = lerp(0.85, 1.25, rng.random() * 0.6 + 0.4 * (1 - lux))
    return dict(weight=round(weight, 2), radius=rr, cap=cap, width=round(width, 2))


def monogram(rng, dna, ctx) -> Mark:
    text = ctx.get("initials") or "A"
    if len(text) > 1 and rng.random() < 0.35 * dna.minimal:
        text = text[0]
    st = letter_style(rng, dna)
    w, rr, cap, ws = st["weight"], st["radius"], st["cap"], st["width"]
    gap = w * 1.35
    if len(text) == 2 and text[0] in RIGHT_STEM and text[1] in LEFT_STEM and rng.random() < 0.6:
        gap = -w  # shared stem ligature
    ds, W = word_paths(text, rr, w, ws, gap=gap)
    style = pick(rng, ["solid", "inline", "container", "outline", "slit"],
                 [1.2 + dna.minimal, 0.4 + dna.heritage + dna.luxury * 0.6, 0.6 + dna.energy + dna.edge * 0.5,
                  0.3 + dna.playful * 0.6, 0.2 + dna.energy * dna.edge * 1.5])
    if len(text) == 2 and style == "container" and W > 13:
        style = "solid"
    if len(text) == 1 and text in "OIL0C" and style == "solid":
        # a lone O/I/L is a plain shape, not a mark: give it a device
        style = pick(rng, ["container", "inline", "slit"], [1.2, 1.0 + dna.luxury, 0.6 + dna.energy])
    join = "round" if cap == "round" else "miter"
    tail = 0.6 if "Q" in text else 0.0
    ink_w, ink_h = W + w, 10 + w + tail
    defs = ""
    shape = None
    if style == "container":
        shape = pick(rng, ["circle", "squircle", "square", "hexagon", "shield"],
                     [1 + dna.playful + (1 - dna.edge), 1 + dna.geometric, 0.6 + dna.edge, 0.4 * dna.geometric, 0.4 * dna.heritage * dna.edge])
        box = 44.0
        s = min(box / ink_w, box / ink_h) * (0.92 if shape in ("circle", "hexagon") else 1.0)
    else:
        s = min(80 / ink_w, 80 / ink_h)
    tx = C - (W * s) / 2
    ty = C - (10 * s) / 2 - tail * s / 2
    strokes = lambda width, color: "".join(
        el("path", d=d, fill="none", stroke=color, stroke_width=f(width), stroke_linecap=cap,
           stroke_linejoin=join, stroke_miterlimit=8) for d in ds)
    tr = f"translate({f(tx)} {f(ty)}) scale({f(s)})"
    if style == "solid":
        body = el("g", strokes(w, "§fg§"), transform=tr)
    elif style in ("inline", "outline"):
        t = w * (0.24 if style == "inline" else 0.26)
        mid, mdef = _mask(el("g", strokes(w - 2 * t if style == "outline" else t, "black"), transform=tr))
        if style == "inline":
            mid, mdef = _mask(el("g", strokes(t, "black"), transform=tr))
            body = el("g", el("g", strokes(w, "§fg§"), transform=tr), mask=f"url(#{mid})")
        else:
            body = el("g", el("g", strokes(w, "§fg§"), transform=tr), mask=f"url(#{mid})")
        defs = mdef
    elif style == "slit":
        ang = pick(rng, [-24, -12, 0, 18])
        gw = w * s * 0.32
        cut = el("rect", x=-20, y=C - gw / 2 + rng.uniform(-6, 6), width=140, height=gw, fill="black", transform=_rot(ang))
        mid, defs = _mask(cut)
        body = el("g", el("g", strokes(w, "§fg§"), transform=tr), mask=f"url(#{mid})")
    else:  # container knockout
        r = 40 if shape != "square" else 38
        base = el("path", d=_shape_path(shape, r), fill="white")
        mid, defs = _mask(el("g", strokes(w, "black"), transform=tr), base=base)
        body = el("rect", x=0, y=0, width=100, height=100, fill="§fg§", mask=f"url(#{mid})")
        st["shape"] = shape
    st.update(text=text, style=style, gap=round(gap, 2))
    return Mark("monogram", style, st, body, defs)


# --------------------------------------------------------------------- radial


def _petal(kind, r0, r1, w):
    """Petal along +x from radius r0 to r1 (local coords, centre at origin)."""
    if kind == "lens":
        a, s = (r1 - r0) / 2, w / 2
        R = (a * a + s * s) / (2 * s)
        return f"M{f(r0)} 0A{f(R)} {f(R)} 0 0 1 {f(r1)} 0A{f(R)} {f(R)} 0 0 1 {f(r0)} 0Z"
    if kind == "circle":
        rr = (r1 - r0) / 2
        return circle_path((r0 + r1) / 2, 0, rr)
    if kind == "capsule":
        return rect_path(r0, -w / 2, r1 - r0, w, w / 2)
    if kind == "drop":
        rr = min(w / 2, (r1 - r0) * 0.45)
        c = r1 - rr
        D = c - r0
        phi = math.asin(min(0.999, rr / D))
        tx, ty = c - rr * math.sin(phi), rr * math.cos(phi)
        return f"M{f(r0)} 0L{f(tx)} {f(ty)}A{f(rr)} {f(rr)} 0 1 0 {f(tx)} {f(-ty)}Z"
    if kind == "square":
        m = (r0 + r1) / 2
        h = (r1 - r0) / 2
        return rect_path(m - h, -h, 2 * h, 2 * h, h * 0.3)
    raise ValueError(kind)


def _arc_sector(r0, r1, a0, a1, cx=C, cy=C):
    p1, p2 = polar(cx, cy, r1, a0), polar(cx, cy, r1, a1)
    p3, p4 = polar(cx, cy, r0, a1), polar(cx, cy, r0, a0)
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return (f"M{f(p1[0])} {f(p1[1])}A{f(r1)} {f(r1)} 0 {large} 1 {f(p2[0])} {f(p2[1])}"
            f"L{f(p3[0])} {f(p3[1])}A{f(r0)} {f(r0)} 0 {large} 0 {f(p4[0])} {f(p4[1])}Z")


def radial(rng, dna, ctx) -> Mark:
    n = pick(rng, [3, 4, 5, 6, 8, 12], [1 + dna.minimal, 1.2, 0.6, 1.0, 0.8 * (1 - dna.minimal) + 0.2, 0.5 * (1 - dna.minimal) * dna.energy])
    kind = pick(rng, ["lens", "circle", "capsule", "drop", "square", "arc"],
                [1 + dna.luxury + (1 - dna.geometric), 0.8 + dna.playful, 0.7 + dna.geometric, 0.5 + dna.playful * 0.8, 0.4 + dna.edge, 0.8 + dna.geometric])
    mode = pick(rng, ["xor", "union", "duo"], [1.2 + dna.geometric * 0.5, 0.8 + dna.minimal, 0.3 + dna.playful + dna.energy * 0.5])
    rot = pick(rng, [-90, 0, 45 / n * 2, 15])
    paths = []
    if kind == "arc":
        span = 360 / n * rng.uniform(0.55, 0.82)
        r1 = 44
        r0 = r1 * rng.uniform(0.35, 0.62)
        for i in range(n):
            a = rot + 360 * i / n
            paths.append(_arc_sector(r0, r1, a - span / 2, a + span / 2))
        params = dict(n=n, kind=kind, span=round(span, 1), r0=round(r0, 1), mode=mode)
    else:
        if kind == "circle":
            r1 = 44
            r0 = rng.uniform(0, 22) if n > 3 else rng.uniform(4, 18)
        else:
            r1 = 45
            r0 = rng.uniform(0, 16) if mode != "xor" else rng.uniform(-14, 6)
        w = (r1 - r0) * rng.uniform(0.35, 0.7) * (1.3 if n <= 4 else 1.0)
        if kind == "square":
            r0 = max(r0, 4)
        petal = _petal(kind, r0, r1, w)
        for i in range(n):
            a = rot + 360 * i / n
            paths.append(f'<path d="{petal}" transform="translate(50 50) rotate({f(a)})"/>')
        params = dict(n=n, kind=kind, r0=round(r0, 1), w=round(w, 1), mode=mode)
    if kind == "arc":
        if mode == "xor" or mode == "union":
            body = el("path", d="".join(paths), fill="§fg§")
        else:
            body = "".join(el("path", d=p, fill="§fg§" if i % 2 == 0 else "§fg2§") for i, p in enumerate(paths))
        return Mark("radial", kind, params, body)
    if mode == "xor":
        # single path, even-odd => overlaps punch through (classic geometric logo look)
        ds = []
        for i in range(n):
            a = rot + 360 * i / n
            ds.append((a,))
        petal_d = _petal(kind, params.get("r0", 0), 45 if kind != "circle" else 44, params["w"])
        body = el("path", d="".join(_transform_d(petal_d, a) for (a,) in ds), fill="§fg§", fill_rule="evenodd")
    elif mode == "union":
        body = el("g", "".join(paths), fill="§fg§")
    else:
        body = "".join(p.replace("<path ", f'<path fill="{"§fg§" if i % 2 == 0 else "§fg2§"}" fill-opacity="§op:0.6§" ', 1)
                       for i, p in enumerate(paths))
    return Mark("radial", kind, params, body)


def _transform_d(d: str, angle: float) -> str:
    """Rotate a path (local coords, centre origin) by angle and move to centre.
    Supports the M/L/A/Z subset produced by our primitives."""
    import re

    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    cx = cy = 0.0
    for cmd, args in re.findall(r"([MLAZHVC])([^MLAZHVC]*)", d):
        nums = [float(x) for x in re.findall(r"-?\d*\.?\d+(?:e-?\d+)?", args)]
        if cmd == "H":
            cmd, nums = "L", [nums[-1], cy]
        elif cmd == "V":
            cmd, nums = "L", [cx, nums[-1]]
        if cmd in "ML":
            res = []
            for i in range(0, len(nums), 2):
                x, y = nums[i], nums[i + 1]
                cx, cy = x, y
                res += [C + x * ca - y * sa, C + x * sa + y * ca]
            out.append(cmd + " ".join(f(v) for v in res))
        elif cmd == "A":
            res = []
            for i in range(0, len(nums), 7):
                rx, ry, rotx, la, sw, x, y = nums[i:i + 7]
                cx, cy = x, y
                res += [rx, ry, rotx + angle, int(la), int(sw), C + x * ca - y * sa, C + x * sa + y * ca]
            out.append("A" + " ".join(f(v) for v in res))
        elif cmd == "Z":
            out.append("Z")
        else:
            raise ValueError(f"unsupported command {cmd}")
    return "".join(out)


# ----------------------------------------------------------------------- grid

PRIMS = {
    "qc": "M0 1L0 0A1 1 0 0 1 1 1Z",
    "arch": "M0 1V0.5A0.5 0.5 0 0 1 1 0.5V1Z",
    "circle": "M0 0.5A0.5 0.5 0 1 0 1 0.5A0.5 0.5 0 1 0 0 0.5Z",
    "square": "M0 0H1V1H0Z",
    "tri": "M0 0L1 1H0Z",
    "leaf": "M0 1A1 1 0 0 1 1 0A1 1 0 0 1 0 1Z",
    "dot": "M0.25 0.5A0.25 0.25 0 1 0 0.75 0.5A0.25 0.25 0 1 0 0.25 0.5Z",
    "half": "M0 1A0.5 0.5 0 0 1 1 1Z",
    "qring": "M0 1L0 0A1 1 0 0 1 1 1H0.5A0.5 0.5 0 0 0 0 0.5Z",
}
SYM_SAFE = {"circle", "square", "dot"}


def grid(rng, dna, ctx) -> Mark:
    N = pick(rng, [2, 3], [1 + dna.minimal * 1.5, 0.6 + (1 - dna.minimal) * 1.2])
    sym = pick(rng, ["mirror", "rot4", "rot2", "none"], [1.0 + dna.heritage * 0.5, 1.0 + dna.geometric, 0.8, 0.25 + dna.edge * 0.6 + dna.playful * 0.3])
    vocab_all = ["qc", "arch", "circle", "square", "tri", "leaf", "dot", "half", "qring"]
    vw = [1.6 + dna.playful, 1.0 + (1 - dna.edge), 0.8 + dna.playful, 0.6 + dna.edge + dna.minimal * 0.5,
          0.3 + dna.edge * 1.4, 0.6 + dna.luxury + (1 - dna.geometric) * 0.6, 0.3, 0.5, 0.4 + dna.geometric * 0.4]
    k = 2 if dna.minimal > 0.55 else pick(rng, [2, 3], [1, 1])
    vocab = []
    while len(vocab) < k:
        p = pick(rng, vocab_all, vw)
        if p not in vocab:
            vocab.append(p)
    gap = pick(rng, [0.0, 0.0, 3.0, 5.0], [1 + dna.geometric, 1, 0.6 + dna.minimal, 0.4])
    color_mode = pick(rng, ["mono", "duo", "spark"], [1 + dna.minimal * 1.4, 0.4 + dna.playful + dna.energy * 0.6, 0.6 + dna.energy * 0.4])
    size = 84.0
    s = (size - gap * (N - 1)) / N
    x0 = (100 - size) / 2

    def g_apply(op, cell, k_, m_):
        cx, cy = cell
        if op == "X":
            return (N - 1 - cx, cy), (-k_) % 4, 1 - m_
        if op == "R":  # 90 deg clockwise about grid centre
            return (N - 1 - cy, cx), (k_ + 1) % 4, m_
        return cell, k_, m_

    groups = {"none": [[]], "mirror": [[], ["X"]], "rot2": [[], ["R", "R"]], "rot4": [[], ["R"], ["R", "R"], ["R", "R", "R"]]}[sym]
    cells: dict = {}
    for attempt in range(60):
        cells = {}
        for row in range(N):
            for col in range(N):
                if (col, row) in cells:
                    continue
                orbit = []
                for ops in groups:
                    c, kk, mm = (col, row), 0, 0
                    for op in ops:
                        c, kk, mm = g_apply(op, c, kk, mm)
                    orbit.append((c, kk, mm))
                fixed = sum(1 for c, _, _ in orbit if c == (col, row)) > 1
                choices = [p for p in vocab if (not fixed or p in SYM_SAFE)] or ["circle"]
                prim = pick(rng, choices + ["empty"], [1.0] * len(choices) + [0.12 + 0.2 * dna.minimal])
                k0, m0 = int(rng.integers(4)), int(rng.integers(2))
                if fixed:
                    k0, m0 = 0, 0
                col_tok = "§fg§"
                if color_mode == "duo" and rng.random() < 0.45:
                    col_tok = "§fg2§"
                for ops in groups:
                    c, kk, mm = (col, row), k0, m0
                    for op in ops:
                        c, kk, mm = g_apply(op, c, kk, mm)
                    cells.setdefault(c, (prim, kk, mm, col_tok))
        filled = [c for c, v in cells.items() if v[0] != "empty"]
        rows_ok = all(any((c, r) in filled for c in range(N)) for r in range(N))
        cols_ok = all(any((c, r) in filled for r in range(N)) for c in range(N))
        dist = len({v[0] for v in cells.values() if v[0] != "empty"})
        if rows_ok and cols_ok and len(filled) >= math.ceil(N * N * 0.6) and (dist >= 2 or N == 2):
            break
    if color_mode == "spark":
        filled = sorted(c for c, v in cells.items() if v[0] != "empty")
        if filled:
            c = filled[int(rng.integers(len(filled)))]
            p, kk, mm, _ = cells[c]
            cells[c] = (p, kk, mm, "§fg3§")
    parts = []
    for (col, row), (prim, kk, mm, tok) in sorted(cells.items()):
        if prim == "empty":
            continue
        x, y = x0 + col * (s + gap), x0 + row * (s + gap)
        tr = (f"translate({f(x)} {f(y)}) scale({f(s)}) translate(0.5 0.5) rotate({kk * 90})"
              f"{' scale(-1 1)' if mm else ''} translate(-0.5 -0.5)")
        parts.append(el("path", d=PRIMS[prim], transform=tr, fill=tok))
    params = dict(N=N, sym=sym, vocab=vocab, gap=gap, color=color_mode,
                  cells={f"{c[0]},{c[1]}": list(v) for c, v in cells.items()})
    return Mark("grid", f"{N}x{N}-{sym}", params, "".join(parts))


# ---------------------------------------------------------------------- lines


def lines(rng, dna, ctx) -> Mark:
    variant = pick(rng, ["sunset", "arches", "letterlines", "waves", "rings"],
                   [0.6 + dna.warmth + dna.heritage * 0.5, 0.6 + (1 - dna.edge) + dna.warmth * 0.5,
                    0.8 + dna.luxury + dna.heritage * 0.5, 0.4 + (1 - dna.geometric) + dna.playful * 0.4,
                    0.5 + dna.geometric])
    defs = ""
    if variant == "sunset":
        cid = uid("c")
        shape = pick(rng, ["circle", "squircle", "arch"], [2, 1, 1 + dna.heritage])
        if shape == "arch":
            clip_d = "M10 92V50A40 40 0 0 1 90 50V92Z"
        else:
            clip_d = _shape_path(shape, 42)
        defs = el("clipPath", el("path", d=clip_d), id=cid)
        k = int(rng.integers(4, 8))
        split = rng.uniform(42, 56)
        y = split
        parts = [el("rect", x=0, y=0, width=100, height=split, fill="§fg§")]
        g0 = rng.uniform(1.4, 2.4)
        bar_total = 92 - split
        # gaps grow geometrically downward, bars shrink
        gaps = [g0 * (1.35 ** i) for i in range(k)]
        bar = (bar_total - sum(gaps)) / k
        if bar < 1.5:
            gaps = [g * 0.6 for g in gaps]
            bar = (bar_total - sum(gaps)) / k
        for i in range(k):
            y += gaps[i]
            h = bar * (1.25 - 0.5 * i / max(1, k - 1))
            parts.append(el("rect", x=0, y=y, width=100, height=h, fill="§fg§" if i % 2 == 0 or rng.random() < .7 else "§fg2§"))
            y += h
        body = el("g", "".join(parts), clip_path=f"url(#{cid})")
        params = dict(shape=shape, k=k, split=round(split, 1))
    elif variant == "arches":
        k = int(rng.integers(3, 6))
        t = rng.uniform(4.0, 7.5) * (4 / k)
        g = t * rng.uniform(0.55, 1.1)
        base = 84.0
        parts = []
        cap = "round" if dna.playful > .45 else "butt"
        for i in range(k):
            r = 40 - i * (t + g) - t / 2
            if r < 3:
                break
            d = f"M{f(C - r)} {f(base)}V{f(52)}A{f(r)} {f(r)} 0 0 1 {f(C + r)} 52V{f(base)}"
            tok = "§fg§" if i % 2 == 0 or k <= 3 else "§fg2§"
            parts.append(el("path", d=d, fill="none", stroke=tok, stroke_width=f(t), stroke_linecap=cap))
        body = "".join(parts)
        params = dict(k=k, t=round(t, 2), g=round(g, 2))
    elif variant == "letterlines":
        text = (ctx.get("initials") or "A")[0]
        n = int(rng.integers(2, 4))
        t = rng.uniform(0.32, 0.5)
        g = t * rng.uniform(0.8, 1.3)
        w = n * t + (n - 1) * g
        rr = pick(rng, [0.0, 1.5, 3.4], [dna.edge + .3, 1, dna.playful + .3 + (1 - dna.edge)])
        ds, W = word_paths(text, rr, w)
        s = min(80 / (W + w), 80 / (10 + w))
        tr = f"translate({f(C - W * s / 2)} {f(C - 5 * s)}) scale({f(s)})"
        cap = "round" if rr > 1 else "butt"
        stack = ""
        width = w
        white = True
        while width > 0.01:
            stack += "".join(el("path", d=d, fill="none", stroke="white" if white else "black",
                                stroke_width=f(width), stroke_linecap=cap, stroke_linejoin="round" if rr > 1 else "miter")
                             for d in ds)
            width -= t if white else g
            white = not white
        mid = uid("m")
        defs = el("mask", el("g", stack, transform=tr), id=mid, maskUnits="userSpaceOnUse", x=-50, y=-50, width=200, height=200)
        body = el("rect", x=0, y=0, width=100, height=100, fill="§fg§", mask=f"url(#{mid})")
        params = dict(text=text, n=n, t=round(t, 2), g=round(g, 2), radius=rr)
    elif variant == "waves":
        cid = uid("c")
        defs = el("clipPath", el("path", d=circle_path(C, C, 42)), id=cid)
        k = int(rng.integers(5, 9))
        amp = rng.uniform(3, 7)
        freq = rng.uniform(1.0, 2.0)
        t = 84 / k * rng.uniform(0.4, 0.6)
        parts = []
        for i in range(k):
            yb = 8 + (i + 0.5) * 84 / k
            pts = [(x, yb + amp * math.sin(2 * math.pi * freq * x / 100 + i * 0.5)) for x in range(0, 101, 4)]
            d = "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts)
            parts.append(el("path", d=d, fill="none", stroke="§fg§", stroke_width=f(t), stroke_linecap="round"))
        body = el("g", "".join(parts), clip_path=f"url(#{cid})")
        params = dict(k=k, amp=round(amp, 1), freq=round(freq, 2))
    else:  # rings: concentric rings, offset centres (ripple)
        k = int(rng.integers(3, 6))
        t = rng.uniform(3.0, 5.5)
        off = rng.uniform(0, 1.0)
        parts = []
        for i in range(k):
            r = 42 - i * (42 / k)
            cy = C + off * (42 - r) * 0.9
            parts.append(el("circle", cx=C, cy=f(cy), r=f(r - t / 2), fill="none", stroke="§fg§", stroke_width=f(t)))
        parts.append(el("circle", cx=C, cy=f(C + off * 42 * 0.9 * (1 - 1 / k) * 1.02), r=f(max(3, 42 / k - t)), fill="§fg3§"))
        body = "".join(parts)
        params = dict(k=k, t=round(t, 2), off=round(off, 2))
    return Mark("lines", variant, params, body, defs)


# ------------------------------------------------------------------------ cut


def cut(rng, dna, ctx) -> Mark:
    shape = pick(rng, ["circle", "squircle", "square", "hexagon", "triangle"],
                 [1.2 + dna.playful * 0.5 + dna.luxury * 0.5, 0.8 + dna.geometric, 0.6 + dna.edge, 0.3 + dna.geometric * 0.5, 0.15 + dna.edge * 0.5])
    variant = pick(rng, ["slash", "bite", "quarter", "split", "slits", "aperture", "knock"],
                   [0.8 + dna.energy, 0.8 + dna.playful, 0.6 + dna.geometric, 0.6 + dna.edge, 0.5 + dna.energy * dna.edge, 0.5 + dna.geometric * 0.5, 0.6 + dna.heritage * 0.3])
    if shape in ("hexagon", "triangle") and variant in ("bite", "quarter", "split"):
        variant = "slash" if shape == "hexagon" else "slits"
    r = 40.0 if shape not in ("square",) else 37.0
    base_d = _shape_path(shape, r)
    base = el("path", d=base_d, fill="white")
    extra = ""
    params = dict(shape=shape)
    if variant == "slash":
        ang = pick(rng, [-45, -30, -60, 30, 45, 90])
        gw = rng.uniform(4, 8) * (1.2 - dna.minimal * 0.4)
        off = rng.uniform(-10, 10)
        cutc = el("rect", x=-50, y=C - gw / 2 + off, width=200, height=gw, fill="black", transform=_rot(ang))
        params.update(angle=ang, gw=round(gw, 1), off=round(off, 1))
    elif variant == "bite":
        br = rng.uniform(13, 22)
        ang = pick(rng, [-45, -135, 45, 0, -90])
        d = r * rng.uniform(0.75, 1.0)
        bx, by = polar(C, C, d, ang)
        cutc = el("circle", cx=f(bx), cy=f(by), r=f(br + 4.5), fill="black")
        if rng.random() < 0.6 + dna.playful * 0.3:
            extra = el("circle", cx=f(bx), cy=f(by), r=f(br * 0.55), fill="§fg3§")
        params.update(angle=ang, br=round(br, 1))
    elif variant == "quarter":
        q = int(rng.integers(4))
        gap = rng.uniform(3, 6)
        qx = C + (gap / 2 if q in (0, 3) else -100 - gap / 2)
        qy = C + (gap / 2 if q in (0, 1) else -100 - gap / 2)
        cutc = el("rect", x=f(qx if q in (0, 3) else qx), y=f(qy), width=100, height=100, fill="black")
        cutc = el("rect", x=f(C - gap / 2 if q in (0, 3) else -50), y=f(C - gap / 2 if q in (0, 1) else -50),
                  width=f(100 + gap / 2 if q in (0, 3) else 100 + gap / 2), height=f(100 + gap / 2), fill="black")
        if rng.random() < 0.65:
            sx = 1 if q in (0, 3) else -1
            sy = 1 if q in (0, 1) else -1
            dr = r * 0.32
            extra = el("circle", cx=f(C + sx * (gap / 2 + r * 0.48)), cy=f(C + sy * (gap / 2 + r * 0.48)), r=f(dr), fill="§fg3§")
        params.update(q=q, gap=round(gap, 1))
    elif variant == "split":
        ang = pick(rng, [0, 90, -45, 45, -30])
        sh = rng.uniform(5, 11)
        gp = rng.uniform(2.5, 5)
        cid1, cid2 = uid("c"), uid("c")
        h1 = el("clipPath", el("rect", x=-50, y=-50, width=200, height=100 - gp / 2, transform=_rot(ang)), id=cid1)
        h2 = el("clipPath", el("rect", x=-50, y=C + gp / 2, width=200, height=100, transform=_rot(ang)), id=cid2)
        dx, dy = sh * math.cos(math.radians(ang)), sh * math.sin(math.radians(ang))
        body = (el("g", el("path", d=base_d, fill="§fg§", transform=f"translate({f(-dx / 2)} {f(-dy / 2)})"), clip_path=f"url(#{cid1})")
                + el("g", el("path", d=base_d, fill="§fg2§", transform=f"translate({f(dx / 2)} {f(dy / 2)})"), clip_path=f"url(#{cid2})"))
        params.update(angle=ang, shift=round(sh, 1), gap=round(gp, 1))
        return Mark("cut", f"{shape}-split", params, body, h1 + h2)
    elif variant == "slits":
        k = int(rng.integers(2, 5))
        th = rng.uniform(2.5, 4.5)
        y0 = rng.uniform(52, 60)
        cutc = "".join(el("rect", x=-10, y=f(y0 + i * th * 2.6), width=120, height=f(th), fill="black") for i in range(k))
        if rng.random() < 0.5:
            cutc = el("g", cutc, transform=f"rotate({pick(rng, [-20, 20, 0])} 50 50)")
        params.update(k=k, th=round(th, 1))
    elif variant == "aperture":
        ar = rng.uniform(9, 17)
        ox = rng.uniform(-10, 10)
        oy = rng.uniform(-10, 10)
        cutc = el("circle", cx=f(C + ox), cy=f(C + oy), r=f(ar), fill="black")
        if rng.random() < 0.5:
            cutc += el("rect", x=f(C + ox - 2), y=f(C + oy), width=4, height=60, fill="black")
        params.update(ar=round(ar, 1), ox=round(ox, 1), oy=round(oy, 1))
    else:  # knock: constructed initial knocked out
        text = (ctx.get("initials") or "A")[0]
        st = letter_style(rng, dna)
        ds, W = word_paths(text, st["radius"], st["weight"] * 1.15, st["width"])
        w = st["weight"] * 1.15
        s = min(44 / (W + w), 44 / (10 + w))
        tr = f"translate({f(C - W * s / 2)} {f(C - 5 * s + (6 if shape == 'triangle' else 0))}) scale({f(s)})"
        cutc = el("g", "".join(el("path", d=d, fill="none", stroke="black", stroke_width=f(w), stroke_linecap=st["cap"],
                                  stroke_linejoin="round" if st["cap"] == "round" else "miter") for d in ds), transform=tr)
        params.update(text=text, **st)
    mid, mdef = _mask(cutc, base=base)
    body = el("rect", x=0, y=0, width=100, height=100, fill="§fg§", mask=f"url(#{mid})") + extra
    return Mark("cut", f"{shape}-{variant}", params, body, mdef)


# ----------------------------------------------------------------------- bars


def bars(rng, dna, ctx) -> Mark:
    variant = pick(rng, ["wave", "peak", "rise", "ring"], [1 + dna.energy, 0.8, 0.6 + dna.luxury * 0.3 + dna.geometric * 0.4, 0.5 + dna.playful * 0.5])
    n = int(rng.integers(5, 10)) if dna.minimal < 0.6 else int(rng.integers(4, 7))
    round_caps = rng.random() < 0.4 + 0.5 * dna.playful + 0.3 * (1 - dna.edge)
    grad = rng.random() < 0.25 + dna.energy * 0.4 and dna.minimal < 0.8
    parts = []
    if variant == "ring":
        n = int(rng.integers(12, 25))
        r0 = rng.uniform(14, 22)
        w = rng.uniform(2.2, 4.0)
        ph = rng.uniform(0, 6.28)
        lobes = pick(rng, [2, 3, 4])
        for i in range(n):
            a = 360 * i / n - 90
            L = 8 + 14 * (0.5 + 0.5 * math.sin(i / n * 2 * math.pi * lobes + ph))
            L = min(L, 44 - r0)
            tok = f"§mix:{i / n:.2f}§" if grad else "§fg§"
            parts.append(el("rect", x=f(r0), y=f(-w / 2), width=f(L), height=f(w), rx=f(w / 2 if round_caps else 0),
                            fill=tok, transform=f"translate(50 50) rotate({f(a)})"))
        params = dict(n=n, r0=round(r0, 1), w=round(w, 1), grad=grad)
        return Mark("bars", variant, params, "".join(parts))
    total = 84.0
    gap_ratio = rng.uniform(0.45, 0.9)
    w = total / (n + (n - 1) * gap_ratio)
    g = w * gap_ratio
    ph = rng.uniform(0, math.pi)
    for i in range(n):
        t = i / (n - 1)
        if variant == "wave":
            h = 0.35 + 0.65 * abs(math.sin(math.pi * t * 1.5 + ph))
        elif variant == "peak":
            h = 0.25 + 0.75 * math.exp(-((t - 0.5) ** 2) / 0.06)
        else:
            h = 0.3 + 0.7 * t ** 1.2
        H = 84 * h
        x = 8 + i * (w + g)
        y = C - H / 2 if variant != "rise" else 92 - H
        tok = f"§mix:{t:.2f}§" if grad else "§fg§"
        parts.append(el("rect", x=f(x), y=f(y), width=f(w), height=f(H), rx=f(w / 2 if round_caps else 0), fill=tok))
    params = dict(n=n, w=round(w, 2), gap=round(g, 2), round=round_caps, grad=grad)
    return Mark("bars", variant, params, "".join(parts))


# -------------------------------------------------------------------- organic


def _blob(rng, cx, cy, R, k=10, amp=0.12, harmonics=(2, 3)):
    coeffs = [(rng.uniform(-amp, amp), rng.uniform(0, 6.28)) for _ in harmonics]
    pts = []
    for i in range(k):
        t = 2 * math.pi * i / k
        rr = R * (1 + sum(a * math.cos(h * t + p) for (a, p), h in zip(coeffs, harmonics)))
        pts.append((cx + rr * math.cos(t), cy + rr * math.sin(t)))
    return smooth_closed_path(pts)


def organic(rng, dna, ctx) -> Mark:
    variant = pick(rng, ["blob", "pebbles", "leaf", "sprout", "bloom"],
                   [1.0 + dna.playful, 0.8 + dna.playful, 0.8 + dna.warmth * 0.5, 0.6 + (1 - dna.edge) * 0.5, 0.6 + dna.luxury * 0.4])
    defs = ""
    if variant == "blob":
        d = _blob(rng, C, C, 38, k=9, amp=0.09 + 0.06 * dna.playful)
        hole = rng.random() < 0.55
        body = el("path", d=d, fill="§fg§")
        if hole:
            hr = rng.uniform(7, 13)
            hx, hy = C + rng.uniform(-10, 10), C + rng.uniform(-12, 4)
            if rng.random() < 0.5:
                body = el("path", d=d + circle_path(hx, hy, hr), fill="§fg§", fill_rule="evenodd")
            else:
                body += el("circle", cx=f(hx), cy=f(hy), r=f(hr), fill="§fg3§")
        params = dict(hole=hole)
    elif variant == "pebbles":
        k = int(rng.integers(2, 4))
        parts = []
        spots = [(C - 12, C + 6, 27), (C + 15, C - 12, 20), (C + 14, C + 20, 13)][:k]
        for i, (x, y, R) in enumerate(spots):
            parts.append(el("path", d=_blob(rng, x, y, R, k=8, amp=0.1), fill=["§fg§", "§fg2§", "§fg3§"][i],
                            fill_opacity="§op:0.75§" if i else None))
        body = "".join(parts)
        params = dict(k=k)
    elif variant == "leaf":
        w = rng.uniform(26, 40)
        a, s = 42.0, w / 2
        R = (a * a + s * s) / (2 * s)
        ang = pick(rng, [-45, -30, 0, 45])
        leaf = f"M{f(C - a)} {f(C)}A{f(R)} {f(R)} 0 0 1 {f(C + a)} {f(C)}A{f(R)} {f(R)} 0 0 1 {f(C - a)} {f(C)}Z"
        vein = el("path", d=f"M{f(C - a * 0.7)} {f(C)}Q{f(C)} {f(C - w * 0.12)} {f(C + a * 0.75)} {f(C)}", stroke="black",
                  stroke_width=f(rng.uniform(2.2, 3.6)), fill="none", stroke_linecap="round")
        mid, defs = _mask(vein, base=el("path", d=leaf, fill="white"))
        body = el("g", el("rect", x=0, y=0, width=100, height=100, fill="§fg§", mask=f"url(#{mid})"), transform=_rot(ang))
        params = dict(w=round(w, 1), angle=ang)
    elif variant == "sprout":
        parts = []
        for side in (-1, 1):
            w = rng.uniform(18, 24)
            a, s = 22.0, w / 2
            R = (a * a + s * s) / (2 * s)
            leaf = f"M{f(-a)} 0A{f(R)} {f(R)} 0 0 1 {f(a)} 0A{f(R)} {f(R)} 0 0 1 {f(-a)} 0Z"
            ang = -40 if side > 0 else -140
            parts.append(el("path", d=leaf, fill="§fg§" if side > 0 else "§fg2§",
                            transform=f"translate({f(C + side * 16)} {f(C - 6)}) rotate({ang + 180 if side < 0 else ang})"))
        parts.append(el("rect", x=f(C - 2.6), y=f(C + 4), width=5.2, height=36, rx=2.6, fill="§fg§"))
        body = "".join(parts)
        params = {}
    else:  # bloom: soft petals around a core
        n = pick(rng, [5, 6, 8])
        pr = rng.uniform(13, 17)
        d0 = rng.uniform(22, 26)
        parts = [el("path", d=_blob(rng, *polar(C, C, d0, 360 * i / n - 90), pr, k=8, amp=0.06), fill="§fg§") for i in range(n)]
        parts.append(el("circle", cx=C, cy=C, r=f(rng.uniform(10, 15)), fill="§fg3§"))
        body = "".join(parts)
        params = dict(n=n)
    return Mark("organic", variant, params, body, defs)


# ---------------------------------------------------------------------- orbit


def orbit(rng, dna, ctx) -> Mark:
    variant = pick(rng, ["saturn", "satellite", "eclipse", "signal"], [1, 1, 0.8 + dna.luxury * 0.4, 0.6 + dna.geometric * 0.4])
    defs = ""
    if variant == "saturn":
        pr = rng.uniform(20, 26)
        tilt = pick(rng, [-24, -18, -30, 20])
        rx, ry = 46.0, rng.uniform(10, 15)
        t = rng.uniform(3.5, 5.5)
        gapw = rng.uniform(3.5, 5)
        ring = el("ellipse", cx=C, cy=C, rx=f(rx - t / 2), ry=f(ry), fill="none", stroke="§fg§", stroke_width=f(t), transform=_rot(tilt))
        # ring hidden behind the planet's upper half, planet cut where the ring passes in front
        hide = el("g", el("circle", cx=C, cy=C, r=f(pr + gapw), fill="black")
                  + el("rect", x=-50, y=C, width=200, height=100, fill="white", transform=_rot(tilt)))
        m1, d1 = _mask(hide)
        cutp = el("g", el("ellipse", cx=C, cy=C, rx=f(rx - t / 2), ry=f(ry), fill="none", stroke="black", stroke_width=f(t + 2 * gapw), transform=_rot(tilt))
                  + el("rect", x=-50, y=-50, width=200, height=100, fill="white", transform=_rot(tilt)))
        m2, d2 = _mask(cutp)
        defs = d1 + d2
        body = el("g", ring, mask=f"url(#{m1})") + el("circle", cx=C, cy=C, r=f(pr), fill="§fg§", mask=f"url(#{m2})")
        params = dict(pr=round(pr, 1), tilt=tilt, t=round(t, 1))
    elif variant == "satellite":
        pr = rng.uniform(16, 24)
        t = rng.uniform(2.5, 4.5)
        rr = 42 - t / 2
        ang = rng.uniform(-80, -10)
        sx, sy = polar(C, C, rr, ang)
        sr = rng.uniform(6, 8.5)
        mid, defs = _mask(el("circle", cx=f(sx), cy=f(sy), r=f(sr + 4), fill="black"))
        body = (el("circle", cx=C, cy=C, r=f(rr), fill="none", stroke="§fg§", stroke_width=f(t), mask=f"url(#{mid})")
                + el("circle", cx=C, cy=C, r=f(pr), fill="§fg§") + el("circle", cx=f(sx), cy=f(sy), r=f(sr), fill="§fg3§"))
        params = dict(pr=round(pr, 1), angle=round(ang))
    elif variant == "eclipse":
        r = 40.0
        off = rng.uniform(12, 22)
        ang = pick(rng, [-45, -135, 0, -90])
        ox, oy = polar(C, C, off, ang)
        mid, defs = _mask(el("circle", cx=f(ox), cy=f(oy), r=f(r - 2), fill="black"), base=el("circle", cx=C, cy=C, r=f(r), fill="white"))
        body = el("rect", x=0, y=0, width=100, height=100, fill="§fg§", mask=f"url(#{mid})")
        if rng.random() < 0.6:
            body += el("circle", cx=f(ox), cy=f(oy), r=f(rng.uniform(6, 11)), fill="§fg3§")
        params = dict(off=round(off, 1), angle=ang)
    else:  # signal: concentric arcs + dot
        k = int(rng.integers(2, 4))
        span = rng.uniform(80, 110)
        t = 84 / (2 * (1.1 + k * 2.1) + 1.0) * 0.98
        a0 = -90 - span / 2
        cx, cy = C, C + (1.1 + k * 2.1) * t * 0.5
        parts = [el("circle", cx=cx, cy=cy, r=f(t * 1.1), fill="§fg§")]
        for i in range(k):
            r = t * 1.1 + (i + 1) * t * 2.1
            p1, p2 = polar(cx, cy, r, a0), polar(cx, cy, r, a0 + span)
            parts.append(el("path", d=f"M{f(p1[0])} {f(p1[1])}A{f(r)} {f(r)} 0 0 1 {f(p2[0])} {f(p2[1])}", fill="none",
                            stroke="§fg§" if i < k - 1 else "§fg3§", stroke_width=f(t), stroke_linecap="round"))
        body = "".join(parts)
        params = dict(k=k, t=round(t, 1), span=round(span))
    return Mark("orbit", variant, params, body, defs)


# ------------------------------------------------------------------ isometric


def isometric(rng, dna, ctx) -> Mark:
    variant = pick(rng, ["cube", "slabs", "tri"], [1, 1, 0.7])
    gap = rng.uniform(1.2, 3.0)
    cos30 = math.cos(math.radians(30))

    def faces(cx, cy, a, h=None):
        """Top, left, right faces of an iso box with edge a and height h."""
        h = a if h is None else h
        top = [(cx, cy - a), (cx + a * cos30, cy - a / 2), (cx, cy), (cx - a * cos30, cy - a / 2)]
        left = [(cx - a * cos30, cy - a / 2), (cx, cy), (cx, cy + h), (cx - a * cos30, cy + h - a / 2)]
        right = [(cx, cy), (cx + a * cos30, cy - a / 2), (cx + a * cos30, cy + h - a / 2), (cx, cy + h)]
        return top, left, right

    def shrink(poly, d):
        cx = sum(p[0] for p in poly) / 4
        cy = sum(p[1] for p in poly) / 4
        out = []
        for x, y in poly:
            vx, vy = x - cx, y - cy
            L = math.hypot(vx, vy)
            out.append((x - vx / L * d, y - vy / L * d))
        return out

    parts = []
    tones = ("§tone:0.12§", "§fg§", "§tone:-0.14§")
    ops = ("§op:0.45§", "1", "§op:0.75§")
    if variant == "cube":
        a = 40.0
        for poly, tok, op in zip(faces(C, C, a), tones, ops):
            parts.append(el("path", d=poly_path(shrink(poly, gap)), fill=tok, fill_opacity=op))
        if rng.random() < 0.4:
            parts[0] = el("path", d=poly_path(shrink(faces(C, C, a)[0], gap)), fill="§fg3§")
    elif variant == "slabs":
        k = int(rng.integers(2, 4))
        a = 38.0
        h = rng.uniform(7, 10)
        step = h + gap * 2.4
        y0 = C - (k - 1) * step / 2 + a / 4 - h / 2
        for i in range(k):
            cy = y0 + i * step
            top, left, right = faces(C, cy, a, h)
            for poly, tok, op in zip((top, left, right), tones, ops):
                if i > 0 and poly is top:
                    continue
                parts.append(el("path", d=poly_path(shrink(poly, gap * 0.6)), fill=tok, fill_opacity=op))
        params = dict(k=k, h=round(h, 1))
        return Mark("isometric", variant, params, "".join(parts[::-1]))
    else:
        a = 20.0
        centers = [(C, C - 14), (C - a * cos30, C + 16), (C + a * cos30, C + 16)]
        for cx, cy in centers:
            for poly, tok, op in zip(faces(cx, cy, a), tones, ops):
                parts.append(el("path", d=poly_path(shrink(poly, gap * 0.7)), fill=tok, fill_opacity=op))
    return Mark("isometric", variant, dict(gap=round(gap, 2)), "".join(parts))


# --------------------------------------------------------------------- spiral


def spiral(rng, dna, ctx) -> Mark:
    variant = pick(rng, ["golden", "nautilus", "ripple"], [1 + dna.luxury, 0.8 + dna.playful * 0.5, 0.7 + dna.geometric * 0.4])
    parts = []
    if variant == "golden":
        steps = int(rng.integers(5, 8))
        W = 88.0
        Hh = W / PHI
        x, y, w, h = (100 - W) / 2, (100 - Hh) / 2, W, Hh
        filled = True
        gap = rng.uniform(0.8, 2.0)
        for i in range(steps):
            side = i % 4
            if side == 0:      # square on the left of a landscape rect
                s = h; sq = (x, y, s); cen = (x + s, y + s); a0 = 180; x += s; w -= s
            elif side == 1:    # top of a portrait rect
                s = w; sq = (x, y, s); cen = (x, y + s); a0 = 270; y += s; h -= s
            elif side == 2:    # right
                s = h; sq = (x + w - s, y, s); cen = (x + w - s, y); a0 = 0; w -= s
            else:              # bottom
                s = w; sq = (x, y + h - s, s); cen = (x + s, y + h - s); a0 = 90; h -= s
            p1, p2 = polar(cen[0], cen[1], s, a0), polar(cen[0], cen[1], s, a0 + 90)
            if filled:
                rr = s - gap
                q1, q2 = polar(cen[0], cen[1], rr, a0), polar(cen[0], cen[1], rr, a0 + 90)
                tok = "§fg§" if i % 2 == 0 else "§fg2§"
                parts.append(el("path", d=f"M{f(cen[0])} {f(cen[1])}L{f(q1[0])} {f(q1[1])}A{f(rr)} {f(rr)} 0 0 1 {f(q2[0])} {f(q2[1])}Z", fill=tok,
                                transform=f"translate({f((sq[0] + s / 2 - cen[0]) * gap / max(s, 1) )} {f((sq[1] + s / 2 - cen[1]) * gap / max(s, 1))})"))
            else:
                parts.append(el("path", d=f"M{f(p1[0])} {f(p1[1])}A{f(s)} {f(s)} 0 0 1 {f(p2[0])} {f(p2[1])}", fill="none", stroke="§fg§",
                                stroke_width=f(max(1.6, s * 0.09)), stroke_linecap="round"))
        params = dict(steps=steps, filled=filled)
        return Mark("spiral", variant, params, "".join(parts), view=((100 - W) / 2 - 2, (100 - Hh) / 2 - 2, W + 4, Hh + 4))
    if variant == "nautilus":
        # phyllotaxis: seeds at the golden angle, the sunflower's packing rule
        n = int(rng.integers(34, 90)) if dna.minimal < 0.6 else int(rng.integers(21, 40))
        ga = 137.50776
        cmax = 42.0
        c = cmax / math.sqrt(n)
        grow = rng.uniform(0.25, 0.6)
        for i in range(1, n + 1):
            r = c * math.sqrt(i)
            x, y = polar(C, C, r, i * ga)
            t = i / n
            dot = c * 0.78 * (1 - grow + grow * t)
            parts.append(el("circle", cx=f(x), cy=f(y), r=f(dot), fill=f"§mix:{t:.2f}§"))
        return Mark("spiral", "phyllotaxis", dict(n=n, grow=round(grow, 2)), "".join(parts))
    k = int(rng.integers(4, 7))
    t = rng.uniform(3.5, 5.5)
    parts = []
    for i in range(k):
        r = 6 + i * (36 / (k - 1)) if k > 1 else 30
        a0 = -90 + i * rng.uniform(25, 50)
        span = rng.uniform(200, 290)
        p1, p2 = polar(C, C, r, a0), polar(C, C, r, a0 + span)
        parts.append(el("path", d=f"M{f(p1[0])} {f(p1[1])}A{f(r)} {f(r)} 0 1 1 {f(p2[0])} {f(p2[1])}", fill="none",
                        stroke="§fg§" if i < k - 1 else "§fg3§", stroke_width=f(t), stroke_linecap="round"))
    return Mark("spiral", variant, dict(k=k, t=round(t, 1)), "".join(parts))


# ---------------------------------------------------------------------- stack


def stack(rng, dna, ctx) -> Mark:
    variant = pick(rng, ["chevrons", "layers", "steps", "slant"], [0.8 + dna.energy, 0.8 + dna.geometric, 0.6 + dna.energy * 0.5, 0.7 + dna.edge])
    parts = []
    if variant == "chevrons":
        k = int(rng.integers(2, 4))
        t = rng.uniform(8, 12)
        cap = "round" if dna.playful > .5 else "butt"
        span = 30.0
        step = t * 1.9
        x0 = C - (k - 1) * step / 2 - span / 2 + 6
        for i in range(k):
            x = x0 + i * step
            d = f"M{f(x)} {f(C - span)}L{f(x + span * 0.62)} {f(C)}L{f(x)} {f(C + span)}"
            parts.append(el("path", d=d, fill="none", stroke=f"§mix:{i / max(1, k - 1):.2f}§", stroke_width=f(t),
                            stroke_linecap=cap, stroke_linejoin="round" if cap == "round" else "miter", stroke_miterlimit=10))
        params = dict(k=k, t=round(t, 1))
    elif variant == "layers":
        k = 3
        gap = rng.uniform(9, 14)
        for i in range(k):
            cy = C - gap + i * gap
            pts = [(C, cy - 18), (C + 38, cy), (C, cy + 18), (C - 38, cy)]
            from ..svg import rounded_polyline
            parts.append(el("path", d=rounded_polyline(pts, 3.5, closed=True), fill=f"§mix:{i / 2:.2f}§",
                            fill_opacity="§op:0.55§" if i else None, stroke="§bg§" if False else None))
        parts = parts[::-1]
        params = dict(gap=round(gap, 1))
    elif variant == "steps":
        k = int(rng.integers(3, 5))
        w = 80 / k
        gp = rng.uniform(1.5, 4)
        rr = w * 0.2 if dna.playful > .45 else 0
        for i in range(k):
            h = 84 * (i + 1) / k
            parts.append(el("rect", x=f(10 + i * w + gp / 2), y=f(92 - h), width=f(w - gp), height=f(h), rx=f(rr), fill=f"§mix:{i / (k - 1):.2f}§"))
        params = dict(k=k)
    else:
        k = int(rng.integers(3, 5))
        sk = rng.uniform(14, 24)
        w = rng.uniform(9, 13)
        gp = w * rng.uniform(0.5, 0.8)
        total = k * w + (k - 1) * gp
        x0 = C - total / 2
        for i in range(k):
            x = x0 + i * (w + gp)
            hh = 70 if i % 2 == 0 or rng.random() < 0.5 else 52
            y0 = C - hh / 2
            pts = [(x + sk / 2, y0), (x + w + sk / 2, y0), (x + w - sk / 2, y0 + hh), (x - sk / 2, y0 + hh)]
            parts.append(el("path", d=poly_path(pts), fill="§fg§" if i < k - 1 else "§fg3§"))
        params = dict(k=k, skew=round(sk, 1))
    return Mark("stack", variant, params, "".join(parts))


# --------------------------------------------------------------------- emblem


def text_on_circle(text, family, weight, size, radius, center_deg, tracking=0.12, bottom=False) -> str:
    """Glyphs placed along a circle. Top text reads clockwise, bottom text reads
    left-to-right along the lower arc (counter-clockwise), both upright."""
    from ..fonts import outline

    run = outline(text, family, weight, size, tracking)
    fnt = run.font
    s = size / fnt.upem
    cap = run.cap
    R = radius - cap / 2 if not bottom else radius + cap / 2
    total = run.width
    out = []
    for d, gx, gy in run.d:
        if not d:
            continue
        # glyph advance centre is unknown per glyph; use origin + half of local width estimate
        x_px = gx * s
        arc = x_px - total / 2
        if not bottom:
            ang = center_deg + math.degrees(arc / R)
            px, py = polar(C, C, R, ang)
            rot = ang + 90
        else:
            ang = center_deg - math.degrees(arc / R)
            px, py = polar(C, C, R, ang)
            rot = ang - 90
        out.append(f'<path transform="translate({f(px)} {f(py)}) rotate({f(rot)}) matrix({f(s)} 0 0 {f(-s)} 0 0)" d="{d}"/>')
    return "".join(out)


def emblem(rng, dna, ctx) -> Mark:
    from .registry import inner_symbol

    name = (ctx.get("name") or "Brand").upper()
    sub = (ctx.get("emblem_sub") or "").upper()
    fam = ctx.get("display_font", "Inter")
    wgt = ctx.get("display_weight", 700)
    outer_t = rng.uniform(1.6, 3.2)
    double = rng.random() < 0.5 + dna.heritage * 0.3
    band = rng.uniform(15, 18)
    R_out = 47.0
    R_in = R_out - band
    parts = [el("circle", cx=C, cy=C, r=f(R_out - outer_t / 2), fill="none", stroke="§fg§", stroke_width=f(outer_t))]
    if double:
        parts.append(el("circle", cx=C, cy=C, r=f(R_out - outer_t - 1.4), fill="none", stroke="§fg§", stroke_width=0.7))
    parts.append(el("circle", cx=C, cy=C, r=f(R_in), fill="none", stroke="§fg§", stroke_width=f(outer_t * 0.6)))
    mid_r = (R_out - outer_t + R_in) / 2
    size = band * 0.48
    max_arc = math.pi * mid_r * (0.82 if sub else 1.15)
    from ..fonts import outline

    trk = 0.18
    run = outline(name, fam, wgt, size, trk)
    if run.width > max_arc:
        size *= max_arc / run.width
    parts.append(el("g", text_on_circle(name, fam, wgt, size, mid_r, -90, trk), fill="§fg§"))
    if sub:
        ssz = size * 0.78
        srun = outline(sub, fam, wgt, ssz, 0.22)
        if srun.width > math.pi * mid_r * 0.62:
            ssz *= math.pi * mid_r * 0.62 / srun.width
        parts.append(el("g", text_on_circle(sub, fam, wgt, ssz, mid_r, 90, 0.22, bottom=True), fill="§fg§"))
        for ang in (180, 0):
            x, y = polar(C, C, mid_r, ang)
            parts.append(el("circle", cx=f(x), cy=f(y), r=f(1.5), fill="§fg§"))
    inner = ctx.get("inner") or inner_symbol(rng, dna, ctx)
    idefs, ibody = inner.defs, inner.body
    vx, vy, vw, vh = inner.view
    box = (R_in - 5.5) * 2 * 0.72
    s = box / max(vw, vh)
    ox, oy = C - (vx + vw / 2) * s, C - (vy + vh / 2) * s
    parts.append(f'<g transform="translate({f(ox)} {f(oy)}) scale({f(s)})">{ibody}</g>')
    params = dict(double=double, band=round(band, 1), inner=inner.to_dict())
    return Mark("emblem", inner.family, params, "".join(parts), idefs)


GENERATORS = {
    "monogram": monogram, "radial": radial, "grid": grid, "lines": lines, "cut": cut, "bars": bars,
    "organic": organic, "orbit": orbit, "isometric": isometric, "emblem": emblem, "spiral": spiral, "stack": stack,
}
