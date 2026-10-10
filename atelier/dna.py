"""Brand DNA: the compact parameter vector that drives every design decision.

The text brief (via the rule parser or the fine-tuned LLM) only ever produces
a BrandDNA. Everything visual is derived from it algorithmically.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

AXES = ("geometric", "minimal", "warmth", "luxury", "energy", "heritage", "playful", "edge")

AXIS_HELP = {
    "geometric": "0 = organic, hand-made, fluid  ->  1 = geometric, constructed, precise",
    "minimal": "0 = expressive, maximal, layered  ->  1 = minimal, reduced, quiet",
    "warmth": "0 = cool, clinical, icy  ->  1 = warm, earthy, sunny",
    "luxury": "0 = accessible, everyday  ->  1 = premium, exclusive, refined",
    "energy": "0 = calm, slow, still  ->  1 = loud, fast, vibrant",
    "heritage": "0 = futuristic, new-tech  ->  1 = classic, crafted, timeless",
    "playful": "0 = serious, corporate  ->  1 = playful, fun, cheeky",
    "edge": "0 = soft, friendly, safe  ->  1 = raw, rebellious, underground",
}

MARK_FAMILIES = ("monogram", "radial", "grid", "lines", "cut", "bars", "organic", "orbit",
                 "isometric", "emblem", "spiral", "stack")

SECTORS: dict[str, dict] = {
    # axis priors, preferred mark families, application kit
    "streetwear": dict(axes=dict(geometric=.55, minimal=.45, warmth=.4, luxury=.45, energy=.8, heritage=.45, playful=.45, edge=.9),
                       dark=.65, marks=("monogram", "emblem", "cut", "grid", "lines", "stack"), kit="apparel"),
    "fashion": dict(axes=dict(geometric=.5, minimal=.75, warmth=.5, luxury=.75, energy=.35, heritage=.55, playful=.25, edge=.45),
                    dark=.35, marks=("monogram", "lines", "cut", "spiral", "emblem"), kit="apparel"),
    "luxury": dict(axes=dict(geometric=.45, minimal=.85, warmth=.5, luxury=.95, energy=.2, heritage=.75, playful=.1, edge=.2),
                   dark=.45, marks=("monogram", "spiral", "lines", "emblem", "radial"), kit="apparel"),
    "athletic": dict(axes=dict(geometric=.75, minimal=.55, warmth=.45, luxury=.4, energy=.95, heritage=.3, playful=.4, edge=.65),
                     dark=.5, marks=("cut", "stack", "monogram", "bars", "lines"), kit="apparel"),
    "saas": dict(axes=dict(geometric=.85, minimal=.75, warmth=.35, luxury=.4, energy=.55, heritage=.1, playful=.4, edge=.3),
                 dark=.3, marks=("grid", "radial", "isometric", "cut", "bars", "orbit", "monogram", "stack"), kit="digital"),
    "ai": dict(axes=dict(geometric=.8, minimal=.7, warmth=.4, luxury=.5, energy=.6, heritage=.05, playful=.35, edge=.4),
               dark=.5, marks=("radial", "orbit", "organic", "grid", "spiral", "lines"), kit="digital"),
    "fintech": dict(axes=dict(geometric=.85, minimal=.8, warmth=.3, luxury=.6, energy=.45, heritage=.25, playful=.2, edge=.25),
                    dark=.35, marks=("cut", "grid", "monogram", "isometric", "stack", "bars"), kit="digital"),
    "devtools": dict(axes=dict(geometric=.9, minimal=.7, warmth=.3, luxury=.3, energy=.6, heritage=.1, playful=.45, edge=.6),
                     dark=.7, marks=("grid", "bars", "monogram", "isometric", "stack", "cut"), kit="digital"),
    "food": dict(axes=dict(geometric=.4, minimal=.4, warmth=.85, luxury=.4, energy=.65, heritage=.6, playful=.7, edge=.25),
                 dark=.15, marks=("organic", "emblem", "radial", "monogram", "lines"), kit="print"),
    "coffee": dict(axes=dict(geometric=.45, minimal=.55, warmth=.85, luxury=.5, energy=.45, heritage=.7, playful=.45, edge=.35),
                   dark=.3, marks=("emblem", "organic", "monogram", "radial", "lines"), kit="print"),
    "wellness": dict(axes=dict(geometric=.35, minimal=.8, warmth=.65, luxury=.6, energy=.2, heritage=.4, playful=.35, edge=.05),
                     dark=.1, marks=("organic", "radial", "lines", "spiral", "monogram"), kit="print"),
    "beauty": dict(axes=dict(geometric=.4, minimal=.8, warmth=.6, luxury=.75, energy=.3, heritage=.45, playful=.35, edge=.15),
                   dark=.15, marks=("monogram", "organic", "radial", "spiral", "lines"), kit="print"),
    "studio": dict(axes=dict(geometric=.6, minimal=.55, warmth=.5, luxury=.55, energy=.6, heritage=.35, playful=.55, edge=.6),
                   dark=.4, marks=("grid", "cut", "monogram", "spiral", "lines", "stack"), kit="print"),
    "gaming": dict(axes=dict(geometric=.75, minimal=.3, warmth=.4, luxury=.3, energy=.95, heritage=.1, playful=.75, edge=.75),
                   dark=.75, marks=("cut", "isometric", "grid", "monogram", "radial"), kit="digital"),
    "outdoor": dict(axes=dict(geometric=.5, minimal=.55, warmth=.65, luxury=.4, energy=.55, heritage=.75, playful=.35, edge=.45),
                    dark=.35, marks=("emblem", "lines", "organic", "cut", "monogram"), kit="apparel"),
    "music": dict(axes=dict(geometric=.55, minimal=.4, warmth=.5, luxury=.45, energy=.85, heritage=.35, playful=.55, edge=.75),
                  dark=.7, marks=("bars", "radial", "lines", "monogram", "orbit"), kit="print"),
    "general": dict(axes=dict(geometric=.6, minimal=.65, warmth=.5, luxury=.5, energy=.5, heritage=.4, playful=.4, edge=.4),
                    dark=.3, marks=MARK_FAMILIES, kit="print"),
}


@dataclass
class BrandDNA:
    name: str
    sector: str = "general"
    tagline: str = ""
    axes: dict = field(default_factory=lambda: {a: 0.5 for a in AXES})
    dark: float = 0.3                     # probability of a dark-mode identity
    hue: float | None = None              # hint, degrees in OKLCH
    hue_secondary: float | None = None
    mark_families: list = field(default_factory=list)  # preferences (empty = sector defaults)
    fonts: list = field(default_factory=list)          # preferred families
    keywords: list = field(default_factory=list)
    kit: str | None = None                # apparel | digital | print

    def __post_init__(self):
        for a in AXES:
            self.axes[a] = float(min(1.0, max(0.0, self.axes.get(a, 0.5))))
        self.dark = float(min(1.0, max(0.0, self.dark)))
        if self.sector not in SECTORS:
            self.sector = "general"
        if self.kit is None:
            self.kit = SECTORS[self.sector]["kit"]
        self.mark_families = [m for m in self.mark_families if m in MARK_FAMILIES]

    def __getattr__(self, item):
        # dna.energy etc.
        if item in AXES:
            axes = self.__dict__.get("axes")
            if axes is not None:
                return axes[item]
        raise AttributeError(item)

    @property
    def initials(self) -> str:
        words = [w for w in "".join(c if c.isalnum() else " " for c in self.name).split() if w]
        if not words:
            return "A"
        if len(words) == 1:
            return words[0][0].upper()
        return (words[0][0] + words[1][0]).upper()

    def seed(self) -> int:
        h = hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()
        return int(h[:12], 16)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, **kw) -> str:
        return json.dumps(self.to_dict(), **kw)

    @staticmethod
    def from_dict(d: dict) -> "BrandDNA":
        known = {k: d[k] for k in ("name", "sector", "tagline", "axes", "dark", "hue", "hue_secondary",
                                   "mark_families", "fonts", "keywords", "kit") if k in d}
        known.setdefault("name", "Untitled")
        return BrandDNA(**known)

    def vector(self) -> list[float]:
        return [self.axes[a] for a in AXES]


JSON_SCHEMA_HINT = {
    "name": "string (brand name)",
    "sector": "one of " + ", ".join(SECTORS),
    "tagline": "short string or empty",
    "axes": {a: f"float 0..1 ({AXIS_HELP[a]})" for a in AXES},
    "dark": "float 0..1, how strongly the identity should be dark-mode",
    "hue": "float 0..360 OKLCH hue of the signature color, or null",
    "hue_secondary": "float 0..360 or null",
    "mark_families": "subset of " + ", ".join(MARK_FAMILIES),
    "fonts": "optional list of font family names",
    "keywords": "list of 3-8 mood keywords",
}
