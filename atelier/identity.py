"""Identity system: DNA + seed -> palette, typography, symbol, wordmark, lockups."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import fonts as F
from .color import COLOR_WORDS, Color, Palette, generate_palette
from .dna import AXES, BrandDNA
from .marks import Mark, generate_mark
from .svg import document, el, f

# ------------------------------------------------------------------ typography


@dataclass
class TypeSystem:
    display: str
    display_weight: int
    case: str
    tracking: float
    text: str
    text_weight: int = 400
    text_bold: int = 600
    mono: str | None = None

    def families(self) -> dict[str, set[int]]:
        out: dict[str, set[int]] = {}
        out.setdefault(self.display, set()).add(self.display_weight)
        out.setdefault(self.text, set()).update({self.text_weight, self.text_bold})
        if self.mono:
            out.setdefault(self.mono, set()).add(400)
        return out

    def css_url(self) -> str:
        return F.google_css_url(self.families())

    def to_dict(self):
        return dict(display=self.display, display_weight=self.display_weight, case=self.case,
                    tracking=self.tracking, text=self.text, text_weight=self.text_weight,
                    text_bold=self.text_bold, mono=self.mono)


def _font_scores(dna: BrandDNA, pool, temperature=0.08):
    v = np.array(dna.vector())
    # axes that matter most for type
    w = np.array([1.0, 0.8, 0.5, 1.4, 1.0, 1.3, 1.2, 1.2])
    scores = []
    for spec in pool:
        d = np.sum(w * (np.array(spec.vector()) - v) ** 2)
        bonus = 3.0 if spec.family in (dna.fonts or []) else 0.0
        scores.append(-d + bonus)
    s = np.array(scores) / temperature
    p = np.exp(s - s.max())
    return p / p.sum()


def choose_type(rng, dna: BrandDNA) -> TypeSystem:
    lib = F.LIBRARY
    display_pool = [s for s in lib if s.category != "mono"]
    p = _font_scores(dna, display_pool, temperature=0.12)
    disp = display_pool[int(rng.choice(len(display_pool), p=p))]

    # ---- weight
    target = 400 + 450 * (0.55 * dna.energy + 0.45 * dna.edge) - 250 * dna.luxury + 120 * dna.playful - 60 * dna.minimal
    target = float(np.clip(target + rng.uniform(-60, 60), 300, 900))
    dw = F.nearest_weight(disp, int(target))

    # ---- case
    if disp.case != "any":
        case = disp.case
    else:
        cw = {"upper": 0.3 + 1.4 * dna.luxury + 1.2 * dna.heritage + 1.1 * dna.edge,
              "lower": 0.3 + 1.4 * dna.playful + 1.2 * (1 - dna.heritage) * dna.geometric,
              "title": 0.6 + 0.6 * dna.warmth}
        keys = list(cw)
        pr = np.array([cw[k] for k in keys])
        case = keys[int(rng.choice(3, p=pr / pr.sum()))]

    # ---- tracking (em)
    if case == "upper":
        base = 0.04 + 0.26 * dna.luxury * (1 - 0.6 * dna.energy) + 0.06 * dna.minimal
        if disp.category in ("condensed", "wide", "blackletter", "display"):
            base = 0.02 + 0.06 * dna.luxury
        tracking = base + rng.uniform(-0.02, 0.03)
    elif case == "lower":
        tracking = -0.035 + 0.03 * dna.luxury + rng.uniform(-0.01, 0.01)
    else:
        tracking = -0.015 + 0.05 * dna.luxury + rng.uniform(-0.01, 0.015)
    if disp.category == "blackletter":
        tracking = 0.0

    # ---- text face
    text_pool = [s for s in lib if s.text_ok and s.category not in ("mono",)]
    if disp.category == "serif" and disp.text_ok and rng.random() < 0.35:
        text = disp
    elif disp.category == "sans" and disp.text_ok and rng.random() < 0.5:
        text = disp
    else:
        if disp.category == "serif":
            text_pool = [s for s in text_pool if s.category == "sans"] if rng.random() < 0.75 else text_pool
        elif disp.category in ("sans",):
            text_pool = [s for s in text_pool if s.family != disp.family and (s.category == "serif") == (rng.random() < 0.25 * dna.heritage)] or text_pool
        pt = _font_scores(dna, text_pool, temperature=0.15)
        text = text_pool[int(rng.choice(len(text_pool), p=pt))]
    tw = F.nearest_weight(text, 400)
    tb = F.nearest_weight(text, 600 if dna.energy < 0.7 else 700)

    mono = None
    if dna.sector in ("saas", "ai", "devtools", "fintech", "streetwear", "studio", "gaming", "athletic") or dna.edge > 0.6:
        mp = [s for s in lib if s.category == "mono"]
        pm = _font_scores(dna, mp, temperature=0.2)
        mono = mp[int(rng.choice(len(mp), p=pm))].family
    return TypeSystem(disp.family, dw, case, round(float(tracking), 3), text.family, tw, tb, mono)


# -------------------------------------------------------------------- identity


def ink_bbox(mark: Mark, res: int = 256) -> tuple[float, float, float, float]:
    """Tight bounds of the drawn symbol inside its 100x100 box (via raster)."""
    from .render import to_image

    m = Mark(mark.family, mark.variant, mark.params, mark.body, mark.defs)
    svg = m.svg(res, fg=Color(0.2, 0, 0), fg2=Color(0.4, 0, 0), fg3=Color(0.5, 0, 0))
    a = np.asarray(to_image(svg, res))[..., 3]
    ys, xs = np.nonzero(a > 8)
    if len(xs) == 0:
        return (0, 0, 100, 100)
    k = 100 / res
    x0, y0, x1, y1 = xs.min() * k, ys.min() * k, (xs.max() + 1) * k, (ys.max() + 1) * k
    return (x0, y0, x1 - x0, y1 - y0)


@dataclass
class Identity:
    dna: BrandDNA
    seed: int
    palette: Palette
    type: TypeSystem
    mark: Mark
    badge: Mark | None = None
    score: float = 0.0
    scores: dict = field(default_factory=dict)

    # --------------------------------------------------------------- text
    @property
    def wordmark_text(self) -> str:
        return F.apply_case(self.dna.name, self.type.case)

    def wordmark_run(self, size: float = 100.0):
        return F.outline(self.wordmark_text, self.type.display, self.type.display_weight, size, self.type.tracking)

    # ------------------------------------------------------------ lockups
    def colors(self, mode: str = "color", on: Color | None = None) -> dict:
        """Colour sets for mark/wordmark. mode: color | mono | reversed."""
        p = self.palette
        bg = on or p.paper
        if mode == "mono":
            ink = p.on(bg)
            return dict(fg=ink, fg2=ink, fg3=ink, bg=bg, mono=True, text=ink)
        if mode == "reversed":
            fg = p.paper if not p.dark else p.ink
            return dict(fg=fg, fg2=fg, fg3=fg, bg=bg, mono=True, text=fg)
        fg = p.mark_color() if bg == p.paper else (p.primary if p.primary.contrast(bg) > 2.6 else p.on(bg))
        fg2 = p.secondary if p.secondary.contrast(bg) > 1.6 else p.accent
        fg3 = p.accent if p.accent.contrast(bg) > 1.4 else fg2
        text = p.ink if bg == p.paper else p.on(bg)
        return dict(fg=fg, fg2=fg2, fg3=fg3, bg=bg, mono=False, text=text)

    def _mark_colors(self, c):
        return {k: c[k] for k in ("fg", "fg2", "fg3", "bg", "mono")}

    def symbol(self, size=100.0, x=0.0, y=0.0, mode="color", on=None) -> tuple[str, str]:
        c = self.colors(mode, on)
        return self.mark.place(x, y, size, **self._mark_colors(c))

    def wordmark(self, height_cap: float, x: float, y_baseline: float, mode="color", on=None) -> tuple[str, float]:
        c = self.colors(mode, on)
        run = self.wordmark_run(100)
        s = height_cap / run.cap
        run = self.wordmark_run(100 * s)
        return run.svg(x - (run.ink[0] if run.ink else 0), y_baseline, c["text"].hex), run.ink[2] - run.ink[0]

    def lockup(self, kind: str = "horizontal", mode: str = "color", on: Color | None = None,
               cap: float = 40.0) -> tuple[str, str, float, float]:
        """Returns (defs, body, width, height) of a lockup with origin top-left."""
        c = self.colors(mode, on)
        run = self.wordmark_run(100)
        s = cap / run.cap
        run = self.wordmark_run(100 * s)
        ink = run.ink or (0, -cap, run.width, 0)
        ww = ink[2] - ink[0]
        top_ink = -ink[1]          # ascent above baseline actually drawn
        bot_ink = ink[3]           # descent below baseline
        vx, vy, vw, vh = self.mark.view
        aspect = vw / vh
        if kind == "wordmark":
            body = run.svg(-ink[0], top_ink, c["text"].hex)
            return "", body, ww, top_ink + bot_ink
        if kind == "symbol":
            d, b = self.mark.place(0, 0, cap * 4, **self._mark_colors(c))
            return d, b, cap * 4, cap * 4
        if kind == "horizontal":
            mh = cap * (1.9 if aspect <= 1.15 else 1.6)
            mw = mh * aspect
            gap = max(cap * 0.55, mh * 0.32)
            H = max(mh, top_ink + bot_ink)
            # mark centred on the cap-height band
            cy = max(mh / 2, top_ink - cap / 2)
            my = cy - mh / 2
            base = cy + cap / 2
            d, b = self._place_mark(0, my, mw, mh, c)
            body = b + run.svg(mw + gap - ink[0], base, c["text"].hex)
            return d, body, mw + gap + ww, max(my + mh, base + bot_ink)
        if kind == "stacked":
            mh = cap * 3.2
            mw = mh * aspect
            gap = cap * 0.95
            W = max(mw, ww)
            d, b = self._place_mark((W - mw) / 2, 0, mw, mh, c)
            base = mh + gap + top_ink
            body = b + run.svg((W - ww) / 2 - ink[0], base, c["text"].hex)
            return d, body, W, base + bot_ink
        raise ValueError(kind)

    def _place_mark(self, x, y, w, h, c):
        defs, body = self.mark.resolve(**self._mark_colors(c))
        vx, vy, vw, vh = self.mark.view
        s = min(w / vw, h / vh)
        ox = x + (w - vw * s) / 2 - vx * s
        oy = y + (h - vh * s) / 2 - vy * s
        return defs, f'<g transform="translate({f(ox)} {f(oy)}) scale({s:.5f})">{body}</g>'

    def lockup_svg(self, kind="horizontal", mode="color", on=None, pad=None, cap=40.0, background=True) -> str:
        d, b, w, h = self.lockup(kind, mode, on, cap)
        pad = cap * 1.0 if pad is None else pad
        bg = (on or self.palette.paper).hex if background else None
        return document(w + 2 * pad, h + 2 * pad, f'<g transform="translate({f(pad)} {f(pad)})">{b}</g>', defs=d, bg=bg)

    @property
    def badge_primary(self) -> bool:
        return "emblem" in (self.dna.mark_families or [])

    def badge_svg(self, size=512, mode="color", on=None, background=True) -> str:
        c = self.colors(mode, on)
        bg = (on or self.palette.paper) if background else None
        return self.badge.svg(size, pad=size * 0.06, background=bg, **self._mark_colors(c))

    def to_dict(self) -> dict:
        return dict(seed=self.seed, dna=self.dna.to_dict(), palette=self.palette.to_dict(), type=self.type.to_dict(),
                    mark=self.mark.to_dict(), score=round(self.score, 4), scores=self.scores)


def base_hue(rng, dna: BrandDNA) -> float:
    if dna.hue is not None:
        return float(dna.hue) + rng.uniform(-6, 6)
    for k in dna.keywords:
        if k.lower() in COLOR_WORDS:
            return COLOR_WORDS[k.lower()] + rng.uniform(-6, 6)
    # warm brands live 20..95, cool brands 180..300; avoid muddy 95..140 unless asked
    if rng.random() < dna.warmth:
        return rng.uniform(15, 95)
    return rng.choice([rng.uniform(150, 200), rng.uniform(220, 300), rng.uniform(300, 350)], p=[0.25, 0.6, 0.15])


def build(dna: BrandDNA, seed: int, *, family: str | None = None, palette_structure: dict | None = None) -> Identity:
    rng = np.random.default_rng(seed)
    hue = base_hue(rng, dna)
    dark = rng.random() < dna.dark
    pal = generate_palette(rng, hue=hue, energy=dna.energy, luxury=dna.luxury, minimal=dna.minimal,
                           warmth=dna.warmth, dark=dark, playful=dna.playful, structure=palette_structure)
    ts = choose_type(rng, dna)
    ctx = dict(initials=dna.initials, name=dna.name, display_font=ts.display, display_weight=ts.display_weight,
               emblem_sub=_emblem_sub(dna, rng))
    if family == "emblem":
        family = None
    mark = generate_mark(rng, dna, ctx, family)
    mark.view = ink_bbox(mark)
    from .marks.families import emblem

    badge = emblem(np.random.default_rng(seed + 7), dna, dict(ctx, inner=mark))
    return Identity(dna, seed, pal, ts, mark, badge)


def _emblem_sub(dna: BrandDNA, rng) -> str:
    if dna.tagline and len(dna.tagline) <= 26:
        return dna.tagline
    opts = {"coffee": "Roasters", "food": "Kitchen", "streetwear": "Supply Co.", "outdoor": "Outfitters",
            "fashion": "Atelier", "luxury": "Maison", "music": "Records", "studio": "Studio", "athletic": "Athletics",
            "saas": "Software", "ai": "Intelligence", "fintech": "Finance", "devtools": "Engineering",
            "wellness": "Wellbeing", "beauty": "Skin & Body", "gaming": "Games"}
    year = int(rng.integers(2019, 2027))
    word = opts.get(dna.sector)
    if word and rng.random() < 0.55:
        return word
    return f"Est. {year}"
