"""Family selection: sector preferences x DNA affinities x user preferences."""

from __future__ import annotations

from ..dna import SECTORS
from .base import Mark
from .families import GENERATORS, pick

AFFINITY = {
    # family: weight as a function of DNA
    "monogram": lambda d: 0.8 + d.heritage * 0.6 + d.luxury * 0.6 + d.edge * 0.3,
    "radial": lambda d: 0.6 + d.geometric * 0.6 + d.luxury * 0.3 + (1 - d.edge) * 0.3,
    "grid": lambda d: 0.5 + d.geometric * 0.9 + d.playful * 0.4 + d.energy * 0.2,
    "lines": lambda d: 0.5 + d.heritage * 0.4 + d.luxury * 0.4 + d.warmth * 0.2,
    "cut": lambda d: 0.6 + d.geometric * 0.6 + d.energy * 0.3 + d.minimal * 0.3,
    "bars": lambda d: 0.3 + d.energy * 0.6 + (1 - d.heritage) * 0.3,
    "organic": lambda d: 0.3 + (1 - d.geometric) * 1.2 + d.warmth * 0.3 + d.playful * 0.3,
    "orbit": lambda d: 0.3 + (1 - d.heritage) * 0.6 + d.geometric * 0.2,
    "isometric": lambda d: 0.25 + d.geometric * 0.6 + (1 - d.heritage) * 0.4,
    "emblem": lambda d: 0.2 + d.heritage * 1.0 + d.edge * 0.4,
    "spiral": lambda d: 0.3 + d.luxury * 0.5 + d.heritage * 0.2,
    "stack": lambda d: 0.35 + d.energy * 0.5 + d.geometric * 0.3,
}


def family_weights(dna) -> dict[str, float]:
    pref = set(dna.mark_families or ())
    sector = set(SECTORS.get(dna.sector, SECTORS["general"])["marks"])
    out = {}
    for fam in GENERATORS:
        if fam == "emblem":
            continue  # badges are built around the primary symbol, see identity.build
        w = AFFINITY[fam](dna)
        if fam in sector:
            w *= 2.2
        if pref:
            w *= 4.0 if fam in pref else 0.15
        out[fam] = w
    return out


def choose_family(rng, dna, exclude=()) -> str:
    w = {k: v for k, v in family_weights(dna).items() if k not in exclude}
    return pick(rng, list(w), list(w.values()))


def generate_mark(rng, dna, ctx, family: str | None = None) -> Mark:
    family = family or choose_family(rng, dna)
    return GENERATORS[family](rng, dna, ctx)


def inner_symbol(rng, dna, ctx) -> Mark:
    """Centre piece for emblems: a monogram or a simple symbol."""
    fam = pick(rng, ["monogram", "radial", "cut", "organic", "spiral", "grid"],
               [2.0 + dna.heritage, 0.8, 0.6, 0.5 + dna.warmth * 0.5, 0.4, 0.5])
    m = GENERATORS[fam](rng, dna, ctx)
    if m.family == "monogram" and m.variant == "container":
        return GENERATORS["monogram"](rng, dna, ctx)
    return m
