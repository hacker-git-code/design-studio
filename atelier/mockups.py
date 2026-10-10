"""Applications: the identity placed on real-world surfaces.

Each mockup is pure vector (SVG): apparel, packaging, print and digital
product surfaces, with soft studio lighting done with gradients + shadows.
"""

from __future__ import annotations

import zlib

import numpy as np

from . import copywriting as copy
from .color import Color
from .patterns import pattern_svg
from .svg import document, el, f, rect_path, superellipse_pts, poly_path, uid
from .typeset import fit_size, paragraph, text


# --------------------------------------------------------------------- helpers


def _shadow(blur=18, dy=14, op=0.2):
    fid = uid("sh")
    return fid, (f'<filter id="{fid}" x="-30%" y="-30%" width="160%" height="160%">'
                 f'<feDropShadow dx="0" dy="{dy}" stdDeviation="{blur}" flood-color="#000" flood-opacity="{op}"/></filter>')


def _shade_grad(kind="v", a=0.10, b=0.10):
    gid = uid("gr")
    if kind == "v":
        return gid, (f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
                     f'<stop offset="0" stop-color="#fff" stop-opacity="{a}"/><stop offset="0.55" stop-color="#fff" stop-opacity="0"/>'
                     f'<stop offset="1" stop-color="#000" stop-opacity="{b}"/></linearGradient>')
    return gid, (f'<radialGradient id="{gid}" cx="0.35" cy="0.25" r="0.9">'
                 f'<stop offset="0" stop-color="#fff" stop-opacity="{a}"/><stop offset="1" stop-color="#000" stop-opacity="{b}"/></radialGradient>')


def _studio(idt) -> Color:
    p = idt.palette
    base = p.muted if not p.dark else p.paper.with_(L=min(0.3, p.paper.L + 0.06))
    return base


def place_lockup(idt, kind, cx, cy, w_max, h_max, mode="color", on=None, cap=40.0):
    d, b, w, h = idt.lockup(kind, mode, on, cap)
    s = min(w_max / w, h_max / h)
    return d, f'<g transform="translate({f(cx - w * s / 2)} {f(cy - h * s / 2)}) scale({f(s)})">{b}</g>'


def place_symbol(idt, cx, cy, size, mode="color", on=None):
    return idt.symbol(size, cx - size / 2, cy - size / 2, mode, on)


def place_badge(idt, cx, cy, size, mode="mono", on=None):
    c = idt.colors(mode, on)
    return idt.badge.place(cx - size / 2, cy - size / 2, size, **idt._mark_colors(c))


def _fabric(idt, rng):
    p = idt.palette
    opts = [p.ink, p.paper, p.primary, p.paper.with_(L=0.93)]
    w = [0.6 + 1.5 * idt.dna.edge + 2 * (p.dark), 1.0 + idt.dna.minimal, 0.6 + idt.dna.energy, 0.4 + idt.dna.warmth]
    w = np.array(w) / sum(w)
    return opts[int(rng.choice(len(opts), p=w))]


# --------------------------------------------------------------------- apparel

TEE = ("M392 112C430 158 570 158 608 112L758 160C800 176 836 214 862 262L904 334C912 348 906 362 892 368L800 404"
       "C788 409 776 404 770 392L748 352L752 882C752 896 742 906 728 907C576 918 424 918 272 907C258 906 248 896 248 882"
       "L252 352L230 392C224 404 212 409 200 404L108 368C94 362 88 348 96 334L138 262C164 214 200 176 242 160Z")


def tee(idt, rng, side="front") -> str:
    W = H = 1000
    bg = _studio(idt)
    fabric = _fabric(idt, rng)
    ink = idt.palette.on(fabric)
    fid, fdef = _shadow(22, 18, 0.22)
    gid, gdef = _shade_grad("r", 0.08, 0.16)
    defs = fdef + gdef
    body = el("path", d=TEE, fill=fabric.hex, filter=f"url(#{fid})")
    body += el("path", d=TEE, fill=f"url(#{gid})")
    # rib collar + seams
    body += el("path", d="M392 112C430 158 570 158 608 112", fill="none", stroke=fabric.mix(Color(0, 0, 0), 0.12).hex, stroke_width=14, stroke_linecap="round")
    body += el("path", d="M252 352L248 882M748 352L752 882", fill="none", stroke="#000", stroke_opacity="0.05", stroke_width=3)
    mode = "mono" if fabric in (idt.palette.ink, idt.palette.paper) and rng.random() < 0.5 else "color"
    on = fabric
    if side == "front":
        style = rng.choice(["chest", "center", "badge-chest"], p=[0.45, 0.4, 0.15])
        if style == "chest":
            d, g = place_lockup(idt, "horizontal", 640, 300, 130, 60, mode, on)
        elif style == "badge-chest":
            d, g = place_badge(idt, 640, 300, 90, "mono", on)
        else:
            d, g = place_lockup(idt, "stacked" if rng.random() < 0.5 else "wordmark", 500, 400, 300, 200, mode, on)
        defs += d
        body += g
    else:
        if idt.badge is not None and rng.random() < 0.55:
            d, g = place_badge(idt, 500, 470, 380, "mono" if rng.random() < .6 else "color", on)
        else:
            d, g = place_symbol(idt, 500, 440, 300, mode, on)
            t, _ = text(idt, idt.dna.name, 46, 500, 680, ink.hex, "display", case=idt.type.case if idt.type.case != "lower" else "upper", anchor="middle", tracking=0.18)
            g += t
        defs += d
        body += g
        lbl, _ = text(idt, copy.headline(idt.dna, 1), 18, 500, 780, ink.hex, "mono" if idt.type.mono else "text", anchor="middle", tracking=0.12, case="upper", opacity="0.75")
        body += lbl
    return document(W, H, body, defs=defs, bg=bg.hex)


def hangtag(idt, rng) -> str:
    W, H = 1000, 1000
    bg = _studio(idt)
    p = idt.palette
    card = rng.choice([p.ink, p.primary, p.paper]) if not p.dark else rng.choice([p.ink, p.paper])
    ink = p.on(card)
    fid, fdef = _shadow(16, 12, 0.22)
    defs = fdef
    x, y, w, h = 360, 220, 300, 560
    body = el("path", d="M510 40C470 120 560 160 510 250", fill="none", stroke=p.secondary.hex, stroke_width=4)
    body += el("path", d=rect_path(x, y, w, h, 14), fill=card.hex, filter=f"url(#{fid})")
    body += el("circle", cx=510, cy=262, r=13, fill=bg.hex)
    body += el("circle", cx=510, cy=262, r=13, fill="none", stroke=ink.hex, stroke_opacity="0.25", stroke_width=2)
    d, g = place_symbol(idt, 510, 440, 130, "color" if card == p.paper else "mono", card)
    defs += d
    body += g
    t, _ = text(idt, idt.dna.name, fit_size(idt, idt.wordmark_text, 230, 34, tracking=idt.type.tracking), 510, 600, ink.hex, "display",
                anchor="middle", case=idt.type.case, tracking=idt.type.tracking)
    body += t
    body += el("line", x1=400, y1=640, x2=620, y2=640, stroke=ink.hex, stroke_opacity="0.3")
    role = "mono" if idt.type.mono else "text"
    for i, ln in enumerate(["100% ORGANIC COTTON", "HEAVYWEIGHT · 280 GSM", "DESIGNED IN-HOUSE"]):
        t, _ = text(idt, ln, 13, 510, 676 + i * 24, ink.hex, role, anchor="middle", tracking=0.1, opacity="0.8")
        body += t
    return document(W, H, body, defs=defs, bg=bg.hex)


def neck_label(idt, rng) -> str:
    W, H = 1000, 1000
    p = idt.palette
    fabric = _fabric(idt, rng)
    lab = p.ink if fabric != p.ink else p.paper
    ink = p.on(lab)
    gid, gdef = _shade_grad("v", 0.06, 0.14)
    fid, fdef = _shadow(10, 6, 0.25)
    defs = gdef + fdef
    body = el("rect", width=W, height=H, fill=fabric.hex)
    body += el("rect", width=W, height=H, fill=f"url(#{gid})")
    body += el("path", d="M-20 330C200 420 800 420 1020 330", fill="none", stroke=fabric.mix(Color(0, 0, 0), 0.15).hex, stroke_width=46)
    body += el("path", d=rect_path(330, 380, 340, 170, 6), fill=lab.hex, filter=f"url(#{fid})")
    # woven texture
    body += "".join(el("line", x1=330, y1=f(380 + i * 4), x2=670, y2=f(380 + i * 4), stroke="#000", stroke_opacity="0.05") for i in range(43))
    d, g = place_lockup(idt, "wordmark", 500, 450, 250, 60, "mono", lab)
    defs += d
    body += g
    t, _ = text(idt, "M", 26, 500, 525, ink.hex, "text", weight=idt.type.text_bold, anchor="middle")
    body += t
    return document(W, H, body, defs=defs)


def tote(idt, rng) -> str:
    W = H = 1000
    bg = _studio(idt)
    p = idt.palette
    fabric = rng.choice([p.paper.with_(L=0.9, C=0.025, H=85), p.ink, p.primary])
    ink = p.on(fabric)
    fid, fdef = _shadow(20, 16, 0.2)
    gid, gdef = _shade_grad("r", 0.06, 0.14)
    defs = fdef + gdef
    body = el("path", d="M380 360C380 150 620 150 620 360", fill="none", stroke=fabric.mix(Color(0, 0, 0), 0.1).hex, stroke_width=26)
    body += el("path", d="M260 340H740L760 900H240Z", fill=fabric.hex, filter=f"url(#{fid})")
    body += el("path", d="M260 340H740L760 900H240Z", fill=f"url(#{gid})")
    if rng.random() < 0.5:
        d, g = place_lockup(idt, "stacked", 500, 610, 330, 330, "mono", fabric)
    else:
        d, g = place_symbol(idt, 500, 580, 250, "mono", fabric)
        t, _ = text(idt, copy.headline(idt.dna), fit_size(idt, copy.headline(idt.dna), 380, 26, "display"), 500, 800, ink.hex, "display", anchor="middle")
        g += t
    defs += d
    body += g
    return document(W, H, body, defs=defs, bg=bg.hex)


# ----------------------------------------------------------------------- print


def business_cards(idt, rng) -> str:
    W, H = 1200, 800
    p = idt.palette
    bg = _studio(idt)
    fid, fdef = _shadow(14, 12, 0.22)
    defs = fdef
    cw, ch = 525, 300
    front = p.primary if p.primary.contrast(p.on(p.primary)) > 4 and rng.random() < 0.6 else p.ink if not p.dark else p.paper
    back = p.paper if not p.dark else p.ink
    body = ""
    # back card (details)
    bx, by = 590, 410
    body += el("g", el("path", d=rect_path(bx, by, cw, ch, 8), fill=back.hex, filter=f"url(#{fid})"), transform=f"rotate(-4 {bx + cw / 2} {by + ch / 2})")
    ink = p.on(back)
    role_mono = "mono" if idt.type.mono else "text"
    g = ""
    t, _ = text(idt, "Alex Rivera", 26, bx + 40, by + 70, ink.hex, "display", weight=None)
    g += t
    t, _ = text(idt, "Founder", 15, bx + 40, by + 98, ink.hex, "text", opacity="0.7")
    g += t
    slug = "".join(ch_ for ch_ in idt.dna.name.lower() if ch_.isalnum()) or "brand"
    for i, ln in enumerate([f"alex@{slug}.com", "+1 (555) 014 2290", f"{slug}.com"]):
        t, _ = text(idt, ln, 14, bx + 40, by + 200 + i * 24, ink.hex, role_mono)
        g += t
    d, s = place_symbol(idt, bx + cw - 80, by + 80, 70, "color", back)
    defs += d
    g += s
    body += el("g", g, transform=f"rotate(-4 {bx + cw / 2} {by + ch / 2})")
    # front card
    fx, fy = 100, 110
    gfront = el("path", d=rect_path(fx, fy, cw, ch, 8), fill=front.hex, filter=f"url(#{fid})")
    d, l = place_lockup(idt, "horizontal" if rng.random() < 0.6 else "stacked", fx + cw / 2, fy + ch / 2, cw * 0.62, ch * 0.5,
                        "mono" if front != p.paper else "color", front)
    defs += d
    body += el("g", gfront + l, transform=f"rotate(3 {fx + cw / 2} {fy + ch / 2})")
    return document(W, H, body, defs=defs, bg=bg.hex)


def poster(idt, rng) -> str:
    W, H = 800, 1100
    p = idt.palette
    kind = rng.choice(["pattern", "symbol"], p=[0.5, 0.5])
    bgc = p.primary if rng.random() < 0.5 else (p.ink if not p.dark else p.paper)
    ink = p.on(bgc)
    defs, body = "", el("rect", width=W, height=H, fill=bgc.hex)
    if kind == "pattern":
        from .patterns import choose_patterns

        pk = choose_patterns(rng, idt, 1)[0]
        ps = pattern_svg(pk, idt, 800, 700, seed=int(rng.integers(1e6)), invert=bgc == p.primary)
        inner = ps[ps.index(">", ps.index("<svg")) + 1: ps.rindex("</svg>")]
        cid = uid("c")
        defs += el("clipPath", el("rect", x=0, y=0, width=800, height=700), id=cid)
        body += el("g", inner, clip_path=f"url(#{cid})")
        body += el("rect", y=700, width=W, height=400, fill=bgc.hex)
    else:
        d, g = place_symbol(idt, W / 2, 360, 420, "color" if bgc == p.paper else "mono", bgc)
        defs += d
        body += g
    hl = copy.headline(idt.dna)
    size = fit_size(idt, hl, W - 120, 64, "display")
    t, hh = paragraph(idt, hl, min(64, size * 1.6), 60, 800, W - 120, ink.hex, "display", leading=1.05, max_lines=2,
                      case="upper" if idt.type.case == "upper" else None)
    body += t
    d, l = place_lockup(idt, "horizontal", 200, 1030, 260, 44, "mono", bgc)
    defs += d
    body += l
    t, _ = text(idt, "2026 · " + idt.dna.sector.upper(), 14, W - 60, 1036, ink.hex, "mono" if idt.type.mono else "text", anchor="end", tracking=0.12)
    body += t
    return document(W, H, body, defs=defs)


def packaging(idt, rng) -> str:
    """A stand-up pouch (coffee/food) or a dropper bottle (beauty/wellness)."""
    W = H = 1000
    p = idt.palette
    bg = _studio(idt)
    fid, fdef = _shadow(22, 18, 0.22)
    gid, gdef = _shade_grad("r", 0.12, 0.2)
    defs = fdef + gdef
    body = ""
    if idt.dna.sector in ("beauty", "wellness", "luxury"):
        glass = p.primary.with_(L=max(0.3, p.primary.L - 0.1))
        body += el("path", d=rect_path(440, 170, 120, 150, 18), fill=p.ink.hex, filter=f"url(#{fid})")
        body += el("path", d=rect_path(330, 300, 340, 560, 60), fill=glass.hex, filter=f"url(#{fid})")
        body += el("path", d=rect_path(330, 300, 340, 560, 60), fill=f"url(#{gid})")
        body += el("path", d=rect_path(360, 480, 280, 300, 6), fill=p.paper.hex)
        d, l = place_lockup(idt, "stacked", 500, 600, 200, 150, "color", p.paper)
        defs += d
        body += l
        t, _ = text(idt, "30 ML · 1 FL OZ", 12, 500, 760, p.ink.hex, "text", anchor="middle", tracking=0.14)
        body += t
    else:
        bag = rng.choice([p.primary, p.ink, p.paper.with_(L=0.9)])
        ink = p.on(bag)
        pouch = "M300 200H700L716 830C717 858 700 876 672 878C557 886 443 886 328 878C300 876 283 858 284 830Z"
        body += el("path", d=pouch, fill=bag.hex, filter=f"url(#{fid})")
        body += el("rect", x=300, y=200, width=400, height=34, fill=bag.mix(Color(0, 0, 0), 0.15).hex)
        body += el("path", d=pouch, fill=f"url(#{gid})")
        band = p.paper if bag != p.paper.with_(L=0.9) else p.primary
        body += el("rect", x=330, y=420, width=340, height=280, rx=4, fill=band.hex)
        d, l = place_lockup(idt, "stacked", 500, 530, 230, 150, "color" if band == p.paper else "mono", band)
        defs += d
        body += l
        t, _ = text(idt, "SINGLE ORIGIN · 250G" if idt.dna.sector == "coffee" else "SMALL BATCH · 250G", 13, 500, 670, p.on(band).hex,
                    "mono" if idt.type.mono else "text", anchor="middle", tracking=0.14)
        body += t
        t, _ = text(idt, copy.headline(idt.dna, 2), fit_size(idt, copy.headline(idt.dna, 2), 330, 18), 500, 790, ink.hex, "text", anchor="middle", opacity="0.85")
        body += t
    return document(W, H, body, defs=defs, bg=bg.hex)


# --------------------------------------------------------------------- digital


def website(idt, rng) -> str:
    W, H = 1440, 900
    p = idt.palette
    page = p.paper
    ink = p.ink
    defs = ""
    body = el("rect", width=W, height=H, fill="#e9e8e4" if not p.dark else "#0b0b0d")
    # browser chrome
    fid, fdef = _shadow(30, 20, 0.25)
    defs += fdef
    body += el("path", d=rect_path(60, 50, 1320, 820, 14), fill=page.hex, filter=f"url(#{fid})")
    body += el("path", d="M60 64A14 14 0 0 1 74 50H1366A14 14 0 0 1 1380 64V96H60Z", fill=page.mix(ink, 0.06).hex)
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        body += el("circle", cx=88 + i * 22, cy=73, r=6, fill=c)
    body += el("path", d=rect_path(560, 62, 320, 22, 11), fill=page.hex)
    slug = "".join(ch for ch in idt.dna.name.lower() if ch.isalnum())
    t, _ = text(idt, f"{slug}.com", 12, 720, 78, ink.hex, "text", anchor="middle", opacity="0.6")
    body += t
    # nav
    d, l = place_lockup(idt, "horizontal", 210, 140, 200, 34, "color", page)
    defs += d
    body += l
    x = 820
    for item in copy.nav(idt.dna):
        t, w = text(idt, item, 15, x, 146, ink.hex, "text", opacity="0.75")
        body += t
        x += w + 36
    btn_c = p.primary
    body += el("path", d=rect_path(1210, 120, 130, 40, 20 if idt.dna.playful > .4 else 6), fill=btn_c.hex)
    t, _ = text(idt, "Get started", 14, 1275, 145, p.on(btn_c).hex, "text", weight=idt.type.text_bold, anchor="middle")
    body += t
    # hero copy
    hl = copy.headline(idt.dna)
    hsize = 64
    t, hh = paragraph(idt, hl, hsize, 140, 330, 600, ink.hex, "display", leading=1.05, max_lines=3,
                      tracking=min(0.02, idt.type.tracking) if idt.type.case != "upper" else 0.02,
                      case="upper" if idt.type.case == "upper" else None)
    body += t
    y = 330 + hh + 10
    t, sh = paragraph(idt, copy.subline(idt.dna), 19, 140, y, 520, ink.hex, "text", leading=1.5)
    body += el("g", t, opacity="0.72")
    y += sh + 30
    r = 26 if idt.dna.playful > .4 else 8
    body += el("path", d=rect_path(140, y, 190, 54, r), fill=btn_c.hex)
    t, _ = text(idt, "Start for free", 16, 235, y + 33, p.on(btn_c).hex, "text", weight=idt.type.text_bold, anchor="middle")
    body += t
    body += el("path", d=rect_path(346, y, 170, 54, r), fill="none", stroke=ink.hex, stroke_opacity="0.25", stroke_width=1.5)
    t, _ = text(idt, "Book a demo", 16, 431, y + 33, ink.hex, "text", anchor="middle")
    body += t
    # hero visual: pattern panel + floating card
    from .patterns import choose_patterns

    pk = choose_patterns(rng, idt, 1)[0]
    ps = pattern_svg(pk, idt, 560, 620, seed=int(rng.integers(1e6)), invert=True)
    inner = ps[ps.index(">", ps.index("<svg")) + 1: ps.rindex("</svg>")]
    cid = uid("c")
    defs += el("clipPath", el("path", d=rect_path(780, 210, 540, 600, 24)), id=cid)
    body += el("g", f'<g transform="translate(770 200)">{inner}</g>', clip_path=f"url(#{cid})")
    card_bg = p.paper if not p.dark else p.paper.with_(L=p.paper.L + 0.06)
    fid2, fdef2 = _shadow(24, 16, 0.25)
    defs += fdef2
    body += el("path", d=rect_path(840, 560, 360, 200, 16), fill=card_bg.hex, filter=f"url(#{fid2})")
    t, _ = text(idt, "This week", 14, 868, 600, ink.hex, "text", opacity="0.6")
    body += t
    t, _ = text(idt, "+38.2%", 34, 868, 644, ink.hex, "display")
    body += t
    vals = np.clip(0.3 + np.cumsum(rng.normal(0.08, 0.12, 12)), 0.15, 1.3)
    vals = vals / vals.max()
    for i, v in enumerate(vals):
        h = 70 * v
        body += el("rect", x=f(868 + i * 26), y=f(735 - h), width=16, height=f(h), rx=3, fill=(p.primary if i == len(vals) - 1 else p.primary.with_(L=min(0.92, p.primary.L + 0.25), C=p.primary.C * 0.5)).hex)
    return document(W, H, body, defs=defs)


def app_icon(idt, rng) -> str:
    W, H = 1200, 800
    p = idt.palette
    bg = _studio(idt)
    fid, fdef = _shadow(26, 20, 0.28)
    defs = fdef
    tile = p.primary if rng.random() < 0.6 else (p.ink if not p.dark else p.paper)
    mode = "mono" if tile != p.paper else "color"
    sq = poly_path(superellipse_pts(420, 400, 230, 230, 5.0, 200))
    body = el("path", d=sq, fill=tile.hex, filter=f"url(#{fid})")
    gid, gdef = _shade_grad("v", 0.18, 0.12)
    defs += gdef
    body += el("path", d=sq, fill=f"url(#{gid})")
    d, s = place_symbol(idt, 420, 400, 250, mode, tile)
    defs += d
    body += s
    x = 720
    for size in (170, 110, 60):
        cy = 400
        sq2 = poly_path(superellipse_pts(x + size / 2, cy, size / 2, size / 2, 5.0, 120))
        body += el("path", d=sq2, fill=tile.hex, filter=f"url(#{fid})")
        d, s = place_symbol(idt, x + size / 2, cy, size * 0.55, mode, tile)
        defs += d
        body += s
        x += size + 36
    t, _ = text(idt, idt.dna.name, 22, 420, 700, p.on(bg).hex, "text", weight=idt.type.text_bold, anchor="middle")
    body += t
    return document(W, H, body, defs=defs, bg=bg.hex)


def social_post(idt, rng, variant=0) -> str:
    W = H = 1080
    p = idt.palette
    defs = ""
    if variant == 0:
        bgc = p.primary
        ink = p.on(bgc)
        body = el("rect", width=W, height=H, fill=bgc.hex)
        hl = copy.headline(idt.dna, 1)
        t, hh = paragraph(idt, hl, 104, 90, 300, 900, ink.hex, "display", leading=1.02, max_lines=4,
                          case="upper" if idt.type.case == "upper" else None)
        body += t
        d, l = place_lockup(idt, "horizontal", 260, 960, 340, 60, "mono", bgc)
        defs += d
        body += l
        body += el("circle", cx=980, cy=960, r=14, fill=p.accent.hex if p.accent.contrast(bgc) > 1.5 else ink.hex)
    else:
        bgc = p.paper
        from .patterns import choose_patterns

        pk = choose_patterns(rng, idt, 1)[0]
        ps = pattern_svg(pk, idt, 1080, 1080, seed=int(rng.integers(1e6)), invert=True)
        inner = ps[ps.index(">", ps.index("<svg")) + 1: ps.rindex("</svg>")]
        body = inner
        body += el("path", d=rect_path(240, 340, 600, 400, 0 if idt.dna.edge > .6 else 24), fill=bgc.hex)
        d, l = place_lockup(idt, "stacked", 540, 540, 420, 260, "color", bgc)
        defs += d
        body += l
    return document(W, H, body, defs=defs)


def ui_kit(idt, rng) -> str:
    W, H = 1200, 800
    p = idt.palette
    page = p.paper
    ink = p.ink
    body = el("rect", width=W, height=H, fill=page.hex)
    r = 22 if idt.dna.playful > .45 else 8 if idt.dna.edge < .7 else 2
    t, _ = text(idt, "Components", 40, 80, 120, ink.hex, "display")
    body += t
    # buttons
    x = 80
    for label, fill, txt, outline in (("Primary", p.primary, p.on(p.primary), False), ("Secondary", p.secondary, p.on(p.secondary), False),
                                      ("Ghost", page, ink, True)):
        w = 170
        body += el("path", d=rect_path(x, 170, w, 52, r), fill=fill.hex, stroke=ink.hex if outline else None,
                   stroke_opacity="0.2" if outline else None, stroke_width=1.5 if outline else None)
        t, _ = text(idt, label, 16, x + w / 2, 202, txt.hex, "text", weight=idt.type.text_bold, anchor="middle")
        body += t
        x += w + 20
    # input
    body += el("path", d=rect_path(80, 260, 530, 56, r * 0.6), fill=page.mix(ink, 0.03).hex, stroke=ink.hex, stroke_opacity="0.15")
    t, _ = text(idt, "you@company.com", 16, 104, 294, ink.hex, "text", opacity="0.45")
    body += t
    # toggle + checkbox + badge chips
    body += el("path", d=rect_path(80, 350, 64, 36, 18), fill=p.primary.hex)
    body += el("circle", cx=126, cy=368, r=13, fill=p.on(p.primary).hex)
    body += el("path", d=rect_path(170, 352, 32, 32, 7), fill=p.primary.hex)
    body += el("path", d="M178 368l6 6 11-12", fill="none", stroke=p.on(p.primary).hex, stroke_width=3, stroke_linecap="round", stroke_linejoin="round")
    cx = 230
    for lab, c in (("Active", p.primary), ("New", p.accent), ("Beta", p.secondary)):
        tw = len(lab) * 9 + 30
        soft = c.with_(L=min(0.95, max(c.L, 0.9)), C=c.C * 0.35) if not p.dark else c.with_(L=0.3, C=c.C * 0.6)
        body += el("path", d=rect_path(cx, 352, tw, 32, 16), fill=soft.hex)
        t, _ = text(idt, lab, 13, cx + tw / 2, 373, (c.with_(L=0.35) if not p.dark else c.with_(L=0.85)).hex, "text", weight=idt.type.text_bold, anchor="middle")
        body += t
        cx += tw + 10
    # card w/ chart
    fid, fdef = _shadow(18, 10, 0.12)
    card = page if not p.dark else page.with_(L=page.L + 0.05)
    body += el("path", d=rect_path(680, 100, 440, 300, 18), fill=card.hex, filter=f"url(#{fid})")
    t, _ = text(idt, "Revenue", 15, 710, 145, ink.hex, "text", opacity="0.6")
    body += t
    t, _ = text(idt, "$48,290", 36, 710, 190, ink.hex, "display")
    body += t
    pts = np.clip(0.4 + np.cumsum(rng.normal(0.04, 0.1, 14)), 0.1, 1)
    xs = np.linspace(710, 1090, len(pts))
    ys = 370 - pts / pts.max() * 140
    d = "M" + "L".join(f"{f(x)} {f(y)}" for x, y in zip(xs, ys))
    body += el("path", d=d + f"L1090 372L710 372Z", fill=p.primary.hex, fill_opacity="0.12")
    body += el("path", d=d, fill="none", stroke=p.primary.hex, stroke_width=3, stroke_linejoin="round")
    # type ramp + scale swatches
    t, _ = text(idt, "Aa", 120, 80, 600, ink.hex, "display")
    body += t
    t, _ = paragraph(idt, f"{idt.type.display} for headlines, {idt.type.text} for interface and long-form text.", 17, 280, 520, 330, ink.hex, "text")
    body += t
    sc = p.scale("primary")
    for i, (k, c) in enumerate(sc.items()):
        body += el("rect", x=f(680 + i * 40), y=470, width=40, height=90, fill=c.hex)
        t, _ = text(idt, str(k), 10, 700 + i * 40, 580, ink.hex, "text", anchor="middle", opacity="0.6")
        body += t
    return document(W, H, body, defs=fdef)


KITS = {
    "apparel": [("tee-front", lambda i, r: tee(i, r, "front")), ("tee-back", lambda i, r: tee(i, r, "back")),
                ("hangtag", hangtag), ("neck-label", neck_label), ("tote", tote),
                ("social-1", lambda i, r: social_post(i, r, 0)), ("social-2", lambda i, r: social_post(i, r, 1)),
                ("business-cards", business_cards), ("poster", poster)],
    "digital": [("website", website), ("app-icon", app_icon), ("ui-kit", ui_kit),
                ("social-1", lambda i, r: social_post(i, r, 0)), ("social-2", lambda i, r: social_post(i, r, 1)),
                ("business-cards", business_cards), ("tee-front", lambda i, r: tee(i, r, "front"))],
    "print": [("business-cards", business_cards), ("packaging", packaging), ("poster", poster),
              ("social-1", lambda i, r: social_post(i, r, 0)), ("social-2", lambda i, r: social_post(i, r, 1)),
              ("tote", tote), ("website", website)],
}


def render_kit(idt, seed=0) -> dict[str, str]:
    out = {}
    for name, fn in KITS.get(idt.dna.kit or "print", KITS["print"]):
        rng = np.random.default_rng(seed + zlib.crc32(name.encode()) % 10000)
        out[name] = fn(idt, rng)
    return out
