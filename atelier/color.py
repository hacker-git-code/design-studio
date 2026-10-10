"""Perceptual color science for palette generation.

All palette logic runs in OKLCH (Ottosson's OKLab in polar form), so that
"same lightness" actually *looks* the same lightness across hues and chroma
steps are perceptually even.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------- conversions


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def oklab_to_linear_rgb(L: float, a: float, b: float) -> tuple[float, float, float]:
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def linear_rgb_to_oklab(r: float, g: float, b: float) -> tuple[float, float, float]:
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def srgb_array_to_oklab(rgb: np.ndarray) -> np.ndarray:
    """Vectorised sRGB (0..1, shape (...,3)) -> OKLab (...,3)."""
    rgb = np.asarray(rgb, dtype=np.float64)
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                   [0.2119034982, 0.6806995451, 0.1073969566],
                   [0.0883024619, 0.2817188376, 0.6299787005]])
    M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                   [1.9779984951, -2.4285922050, 0.4505937099],
                   [0.0259040371, 0.7827717662, -0.8086757660]])
    lms = np.cbrt(lin @ M1.T)
    return lms @ M2.T


def oklab_array_to_oklch(lab: np.ndarray) -> np.ndarray:
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    C = np.hypot(a, b)
    H = np.degrees(np.arctan2(b, a)) % 360
    return np.stack([L, C, H], axis=-1)


def _in_gamut(rgb, eps=1e-4) -> bool:
    return all(-eps <= c <= 1 + eps for c in rgb)


@dataclass(frozen=True)
class Color:
    """A color stored as OKLCH. L in 0..1, C in 0..~0.37, H in degrees."""

    L: float
    C: float
    H: float

    # -- constructors
    @staticmethod
    def from_hex(hex_str: str) -> "Color":
        h = hex_str.lstrip("#")
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        L, a, bb = linear_rgb_to_oklab(_srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b))
        C = math.hypot(a, bb)
        H = math.degrees(math.atan2(bb, a)) % 360
        return Color(float(L), float(C), float(H))

    @staticmethod
    def oklch(L: float, C: float, H: float) -> "Color":
        return Color(L, C, H % 360).fit()

    # -- conversions
    def oklab(self) -> tuple[float, float, float]:
        h = math.radians(self.H)
        return self.L, self.C * math.cos(h), self.C * math.sin(h)

    def linear_rgb(self):
        return oklab_to_linear_rgb(*self.oklab())

    def rgb(self) -> tuple[float, float, float]:
        return tuple(min(1.0, max(0.0, _linear_to_srgb(min(1.0, max(0.0, c))))) for c in self.linear_rgb())

    @property
    def hex(self) -> str:
        return "#" + "".join(f"{round(c * 255):02x}" for c in self.rgb())

    def css_oklch(self) -> str:
        return f"oklch({self.L * 100:.1f}% {self.C:.3f} {self.H:.1f})"

    def in_gamut(self) -> bool:
        return _in_gamut(self.linear_rgb())

    def fit(self) -> "Color":
        """Map into sRGB by reducing chroma (keeps hue & lightness, the perceptually
        important parts)."""
        if self.in_gamut():
            return self
        lo, hi = 0.0, self.C
        for _ in range(24):
            mid = (lo + hi) / 2
            if _in_gamut(Color(self.L, mid, self.H).linear_rgb()):
                lo = mid
            else:
                hi = mid
        return Color(self.L, lo, self.H)

    # -- manipulation
    def with_(self, L=None, C=None, H=None) -> "Color":
        return Color.oklch(self.L if L is None else L, self.C if C is None else C, self.H if H is None else H)

    def mix(self, other: "Color", t: float) -> "Color":
        a1, b1, c1 = self.oklab()
        a2, b2, c2 = other.oklab()
        L, a, b = a1 + (a2 - a1) * t, b1 + (b2 - b1) * t, c1 + (c2 - c1) * t
        return Color(L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360).fit()

    # -- metrics
    def luminance(self) -> float:
        r, g, b = (_srgb_to_linear(c) for c in self.rgb())
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def contrast(self, other: "Color") -> float:
        a, b = self.luminance(), other.luminance()
        hi, lo = max(a, b), min(a, b)
        return (hi + 0.05) / (lo + 0.05)

    def delta_e(self, other: "Color") -> float:
        a, b = self.oklab(), other.oklab()
        return math.dist(a, b)

    def __str__(self):
        return self.hex


def hue_dist(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def max_chroma(L: float, H: float) -> float:
    return Color(L, 0.4, H).fit().C


# ------------------------------------------------------------------- palettes

HARMONIES = {
    # name: hue offsets for (secondary, accent) relative to primary
    "monochrome": (0, 0),
    "analogous": (28, -32),
    "complementary": (0, 180),
    "split": (150, 210),
    "triadic": (120, 240),
    "tetradic": (90, 180),
}

COLOR_WORDS = {
    "red": 27, "crimson": 20, "scarlet": 30, "ruby": 10, "burgundy": 15, "wine": 10, "maroon": 18,
    "orange": 55, "rust": 45, "terracotta": 42, "amber": 70, "coral": 35, "peach": 55, "copper": 50,
    "yellow": 100, "gold": 85, "golden": 85, "mustard": 90, "lemon": 105, "honey": 80, "sand": 80,
    "beige": 75, "cream": 90, "ochre": 78,
    "green": 145, "lime": 130, "olive": 115, "sage": 140, "forest": 150, "emerald": 160, "mint": 165,
    "moss": 125, "jade": 165, "khaki": 105,
    "teal": 195, "cyan": 210, "turquoise": 190, "aqua": 200,
    "blue": 255, "navy": 262, "cobalt": 262, "azure": 240, "sky": 235, "indigo": 275, "denim": 250,
    "ocean": 230, "sapphire": 265,
    "purple": 305, "violet": 295, "lavender": 300, "lilac": 310, "plum": 330, "magenta": 340,
    "pink": 355, "rose": 5, "blush": 15, "fuchsia": 345,
    "brown": 55, "chocolate": 45, "coffee": 55, "mocha": 50, "tan": 70, "earth": 60,
}


@dataclass
class Palette:
    """Role-based brand palette."""

    paper: Color          # dominant background
    ink: Color            # text / logo on paper
    primary: Color        # signature brand color
    secondary: Color
    accent: Color         # small doses only (the "10" of 60-30-10)
    muted: Color          # quiet supporting surface
    scheme: str = "monochrome"
    dark: bool = False
    meta: dict = field(default_factory=dict)

    def roles(self) -> dict[str, Color]:
        return {"paper": self.paper, "ink": self.ink, "primary": self.primary,
                "secondary": self.secondary, "accent": self.accent, "muted": self.muted}

    def on(self, bg: Color) -> Color:
        """Best foreground (ink or paper) for a background."""
        return self.ink if self.ink.contrast(bg) >= self.paper.contrast(bg) else self.paper

    def mark_color(self) -> Color:
        """Color the symbol uses on paper: primary when it holds contrast, else ink."""
        return self.primary if self.primary.contrast(self.paper) >= 2.6 else self.ink

    def to_dict(self) -> dict:
        d = {k: {"hex": c.hex, "oklch": c.css_oklch()} for k, c in self.roles().items()}
        d["_scheme"] = self.scheme
        d["_dark"] = self.dark
        return d

    def scale(self, role: str, steps=(50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950)) -> dict[int, Color]:
        """Tailwind-style tonal ramp, perceptually even in L, chroma tapering at the ends."""
        base = self.roles()[role]
        out = {}
        for s in steps:
            L = 0.985 - (s / 1000) * 0.80          # 50 -> .945, 950 -> .225
            taper = math.sin(math.pi * min(1.0, max(0.0, (0.985 - L) / 0.80))) ** 0.6
            C = max(0.004, base.C * (0.25 + 0.85 * taper))
            out[s] = Color.oklch(L, C, base.H)
        return out


def _jitter(rng, x, amt):
    return x + rng.uniform(-amt, amt)


def generate_palette(rng, *, hue: float, energy: float, luxury: float, minimal: float,
                     warmth: float, dark: bool, playful: float, scheme: str | None = None,
                     structure: dict | None = None) -> Palette:
    """Build a palette from brand DNA.

    `structure` is an optional learned palette prior (from the taste model): a
    dict of per-role L/C and relative hue offsets taken from a reference the
    user loves. It is *re-hued* to the brand's hue, so taste transfers without
    copying anyone's colors.
    """
    if scheme is None:
        weights = {
            "monochrome": 0.6 + 1.6 * minimal + 0.8 * luxury,
            "analogous": 1.0 + 0.6 * (1 - energy),
            "complementary": 0.4 + 1.6 * energy + 0.8 * playful,
            "split": 0.3 + 1.2 * playful,
            "triadic": 0.05 + 1.2 * playful * energy,
            "tetradic": 0.02 + 0.4 * playful * energy * (1 - minimal),
        }
        names = list(weights)
        p = np.array([weights[n] for n in names])
        scheme = names[rng.choice(len(names), p=p / p.sum())]
    off2, off3 = HARMONIES[scheme]

    # chroma budget: energetic brands saturate, luxury brands whisper
    cmax = 0.06 + 0.17 * energy - 0.07 * luxury + 0.04 * playful
    cmax = float(np.clip(cmax, 0.035, 0.24))

    if structure:
        s = structure
        pri = Color.oklch(s["primary"][0], s["primary"][1], hue)
        sec = Color.oklch(s["secondary"][0], s["secondary"][1], hue + s["secondary"][2])
        acc = Color.oklch(s["accent"][0], s["accent"][1], hue + s["accent"][2])
        paper_L, paper_C = s["paper"][0], s["paper"][1]
        ink_L, ink_C = s["ink"][0], s["ink"][1]
        dark = paper_L < 0.5
    else:
        pri_L = float(np.clip(_jitter(rng, 0.62 - 0.18 * luxury + 0.05 * playful, 0.06), 0.32, 0.78))
        # yellows/limes only read as themselves when light
        if 70 <= hue % 360 <= 125:
            pri_L = max(pri_L, 0.78)
        pri = Color.oklch(pri_L, cmax, hue)
        sec_hue = hue + off2 + rng.uniform(-8, 8)
        if scheme == "monochrome":
            sec = Color.oklch(np.clip(pri_L + (0.22 if pri_L < 0.6 else -0.25), 0.25, 0.9), cmax * 0.55, sec_hue)
        else:
            sec = Color.oklch(np.clip(pri_L + rng.uniform(-0.12, 0.12), 0.35, 0.82), cmax * rng.uniform(0.6, 0.9), sec_hue)
        acc_hue = hue + off3 + rng.uniform(-10, 10)
        if scheme == "monochrome":
            # a single warm or cool spark keeps monochrome from going flat
            acc_hue = hue + (180 if rng.random() < 0.5 + 0.3 * energy else 35)
            acc_C = min(0.22, cmax * (1.4 + energy))
        else:
            acc_C = min(0.25, cmax * 1.25)
        acc_L = 0.80 if 70 <= acc_hue % 360 <= 125 else rng.uniform(0.58, 0.74)
        acc = Color.oklch(acc_L, acc_C, acc_hue)
        paper_L = rng.uniform(0.955, 0.985) if not dark else rng.uniform(0.13, 0.19)
        paper_C = (0.004 + 0.018 * warmth * (1 - minimal * 0.5)) if not dark else 0.012 + 0.02 * luxury
        ink_L = rng.uniform(0.17, 0.24) if not dark else rng.uniform(0.94, 0.975)
        ink_C = 0.012 + 0.02 * luxury if not dark else 0.008

    # neutrals carry a whisper of the primary hue (warm cream vs cold paper)
    paper_hue = hue if warmth > 0.35 or dark else (hue + 200 if warmth < 0.2 else hue)
    if not dark and warmth > 0.55:
        paper_hue = 80  # cream
    paper = Color.oklch(paper_L, paper_C, paper_hue)
    ink = Color.oklch(ink_L, ink_C, hue)
    muted = Color.oklch(paper.L + (-0.07 if not dark else 0.08), min(0.04, pri.C * 0.3 + 0.01), hue)

    # guarantee the signature color can carry a logo on paper
    if not dark:
        while pri.contrast(paper) < 3.0 and pri.L > 0.25:
            pri = pri.with_(L=pri.L - 0.03)
    else:
        while pri.contrast(paper) < 3.0 and pri.L < 0.92:
            pri = pri.with_(L=pri.L + 0.03)

    return Palette(paper=paper, ink=ink, primary=pri, secondary=sec, accent=acc, muted=muted,
                   scheme=scheme, dark=dark)


def palette_from_structure_roles(roles: dict[str, Color]) -> dict:
    """Inverse of `structure`: turn a concrete palette into a hue-relative prior."""
    h = roles["primary"].H
    return {k: (round(c.L, 4), round(c.C, 4), round(((c.H - h + 180) % 360) - 180, 1)) for k, c in roles.items()}
