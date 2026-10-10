"""Tiny SVG authoring layer + path geometry helpers."""

from __future__ import annotations

import itertools
import math
from html import escape

_ids = itertools.count(1)


def uid(prefix="a") -> str:
    return f"{prefix}{next(_ids)}"


def f(x: float) -> str:
    """Compact number formatting."""
    s = f"{x:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def attrs(**kw) -> str:
    out = []
    for k, v in kw.items():
        if v is None or v is False:
            continue
        k = k.rstrip("_").replace("_", "-")
        if isinstance(v, float):
            v = f(v)
        out.append(f'{k}="{escape(str(v), quote=True)}"')
    return " ".join(out)


def el(tag: str, children: str | list | None = None, **kw) -> str:
    a = attrs(**kw)
    head = f"<{tag} {a}" if a else f"<{tag}"
    if children is None or children == "" or children == []:
        return head + "/>"
    if isinstance(children, list):
        children = "".join(children)
    return f"{head}>{children}</{tag}>"


def g(children, **kw) -> str:
    return el("g", children, **kw)


def document(width: float, height: float, body: str, defs: str = "", bg: str | None = None,
             title: str | None = None) -> str:
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(width)} {f(height)}" '
             f'width="{f(width)}" height="{f(height)}">']
    if title:
        parts.append(f"<title>{escape(title)}</title>")
    if defs:
        parts.append(f"<defs>{defs}</defs>")
    if bg:
        parts.append(el("rect", width=width, height=height, fill=bg))
    parts.append(body)
    parts.append("</svg>")
    return "".join(parts)


# ------------------------------------------------------------------ geometry


def polar(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def circle_path(cx, cy, r) -> str:
    return (f"M{f(cx - r)} {f(cy)}A{f(r)} {f(r)} 0 1 0 {f(cx + r)} {f(cy)}"
            f"A{f(r)} {f(r)} 0 1 0 {f(cx - r)} {f(cy)}Z")


def rect_path(x, y, w, h, r=0.0) -> str:
    r = max(0.0, min(r, w / 2, h / 2))
    if r <= 1e-6:
        return f"M{f(x)} {f(y)}H{f(x + w)}V{f(y + h)}H{f(x)}Z"
    return (f"M{f(x + r)} {f(y)}H{f(x + w - r)}A{f(r)} {f(r)} 0 0 1 {f(x + w)} {f(y + r)}"
            f"V{f(y + h - r)}A{f(r)} {f(r)} 0 0 1 {f(x + w - r)} {f(y + h)}"
            f"H{f(x + r)}A{f(r)} {f(r)} 0 0 1 {f(x)} {f(y + h - r)}"
            f"V{f(y + r)}A{f(r)} {f(r)} 0 0 1 {f(x + r)} {f(y)}Z")


def superellipse_pts(cx, cy, rx, ry, n=4.0, steps=96, rot=0.0):
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        c, s = math.cos(t), math.sin(t)
        x = rx * math.copysign(abs(c) ** (2 / n), c)
        y = ry * math.copysign(abs(s) ** (2 / n), s)
        if rot:
            a = math.radians(rot)
            x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        pts.append((cx + x, cy + y))
    return pts


def poly_path(pts, closed=True) -> str:
    if not pts:
        return ""
    d = f"M{f(pts[0][0])} {f(pts[0][1])}" + "".join(f"L{f(x)} {f(y)}" for x, y in pts[1:])
    return d + ("Z" if closed else "")


def smooth_closed_path(pts, tension=1.0) -> str:
    """Catmull-Rom spline through points, converted to cubic Beziers."""
    n = len(pts)
    d = f"M{f(pts[0][0])} {f(pts[0][1])}"
    for i in range(n):
        p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6 * tension, p1[1] + (p2[1] - p0[1]) / 6 * tension)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6 * tension, p2[1] - (p3[1] - p1[1]) / 6 * tension)
        d += f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}"
    return d + "Z"


def regular_polygon(cx, cy, r, n, rot=-90.0):
    return [polar(cx, cy, r, rot + 360 * i / n) for i in range(n)]


def rounded_polyline(pts, radius, closed=False) -> str:
    """Polyline whose interior corners are filleted with circular arcs where
    possible (perfect for constructed letterforms: r=0 -> squared, r=max ->
    geometric round)."""
    pts = [(p[0], p[1]) for p in pts]
    n = len(pts)
    if n < 2:
        return ""
    if closed:
        corners = range(n)
    else:
        corners = range(1, n - 1)

    def seg_len(a, b):
        return math.dist(a, b)

    fillets = {}
    for i in corners:
        p0, p1, p2 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
        v1 = (p0[0] - p1[0], p0[1] - p1[1])
        v2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1, l2 = math.hypot(*v1), math.hypot(*v2)
        if l1 < 1e-9 or l2 < 1e-9:
            continue
        u1, u2 = (v1[0] / l1, v1[1] / l1), (v2[0] / l2, v2[1] / l2)
        cosang = max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))
        ang = math.acos(cosang)
        if ang < 1e-3 or abs(ang - math.pi) < 1e-3:
            continue
        # acute corners get proportionally tighter fillets, otherwise the
        # fillet swallows the whole diagonal (N, A, V turn into waves)
        r_here = radius * min(1.0, (ang / (math.pi / 2)) ** 2.2)
        t = r_here / math.tan(ang / 2)
        lim1 = l1 / 2 if (closed or i - 1 > 0) else l1
        lim2 = l2 / 2 if (closed or i + 1 < n - 1) else l2
        t = min(t, lim1, lim2)
        r_eff = t * math.tan(ang / 2)
        if t < 1e-6:
            continue
        a = (p1[0] + u1[0] * t, p1[1] + u1[1] * t)
        b = (p1[0] + u2[0] * t, p1[1] + u2[1] * t)
        cross = u1[0] * u2[1] - u1[1] * u2[0]
        sweep = 1 if cross < 0 else 0
        fillets[i] = (a, b, r_eff, sweep)

    def P(p):
        return f"{f(p[0])} {f(p[1])}"

    if closed:
        start = fillets[0][1] if 0 in fillets else pts[0]
        d = "M" + P(start)
        for k in range(1, n + 1):
            i = k % n
            if i in fillets:
                a, b, r, sw = fillets[i]
                d += f"L{P(a)}A{f(r)} {f(r)} 0 0 {sw} {P(b)}"
            else:
                d += f"L{P(pts[i])}"
        return d + "Z"
    d = "M" + P(pts[0])
    for i in range(1, n):
        if i in fillets:
            a, b, r, sw = fillets[i]
            d += f"L{P(a)}A{f(r)} {f(r)} 0 0 {sw} {P(b)}"
        else:
            d += f"L{P(pts[i])}"
    return d
