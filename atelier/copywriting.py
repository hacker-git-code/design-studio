"""Placeholder brand copy for mockups (deterministic, template-based).
Replace with your real copy, or let the LLM backend write it."""

from __future__ import annotations

HEADLINES = {
    "streetwear": ["Made for the night shift.", "Built loud. Worn louder.", "No permission needed.", "From the street, for the street."],
    "fashion": ["Quiet pieces, made to last.", "Dressed in intention.", "The new uniform.", "Considered, not complicated."],
    "luxury": ["The art of less.", "Crafted beyond the season.", "Rare by design.", "Made slowly. Worn always."],
    "athletic": ["Move first. Think later.", "Every rep counts.", "Engineered for the long run.", "Faster than yesterday."],
    "saas": ["Work that flows.", "Your data, finally clear.", "Ship faster with less noise.", "One place for everything your team does."],
    "ai": ["Intelligence, on your terms.", "Think bigger. Build faster.", "Your work, amplified.", "Models that understand your world."],
    "fintech": ["Money, made simple.", "Finance that works for you.", "Clarity for every dollar.", "Built on trust. Designed for growth."],
    "devtools": ["Build without friction.", "From commit to production in minutes.", "Tools developers actually love.", "Infrastructure, simplified."],
    "food": ["Good food, honestly made.", "Fresh from our kitchen.", "Made to be shared.", "Flavour first. Always."],
    "coffee": ["Roasted slow, poured with care.", "Your daily ritual, refined.", "Small batch. Big character.", "Coffee worth waking up for."],
    "wellness": ["Breathe in. Slow down.", "Care for the whole you.", "Rituals for a calmer day.", "Gentle by nature."],
    "beauty": ["Skin, but better.", "Clean formulas. Real results.", "Your glow, uncomplicated.", "Rituals of radiance."],
    "studio": ["Ideas, made visible.", "We design what's next.", "Brands with a point of view.", "Craft meets curiosity."],
    "gaming": ["Press start.", "Level up together.", "Worlds worth exploring.", "Play without limits."],
    "outdoor": ["Further, together.", "Made for wild places.", "Gear for the long way round.", "Go outside."],
    "music": ["Turn it up.", "Sounds from the underground.", "Feel every frequency.", "Music first."],
    "general": ["Made with intention.", "Something new is here.", "Designed for what matters.", "Simply better."],
}

SUBS = {
    "digital": "Everything your team needs to plan, build and ship — in one beautifully simple workspace.",
    "apparel": "Limited runs, heavyweight fabrics and details you only notice up close.",
    "print": "Thoughtfully made, carefully sourced and designed to be enjoyed every day.",
}

NAV = {
    "digital": ["Product", "Pricing", "Customers", "Docs"],
    "apparel": ["Shop", "Collections", "Lookbook", "About"],
    "print": ["Menu", "Our Story", "Visit", "Shop"],
}


def headline(dna, i: int = 0) -> str:
    if dna.tagline and i == 0:
        return dna.tagline
    opts = HEADLINES.get(dna.sector, HEADLINES["general"])
    return opts[(i + dna.seed()) % len(opts)]


def subline(dna) -> str:
    return SUBS.get(dna.kit or "print", SUBS["print"])


def nav(dna) -> list[str]:
    return NAV.get(dna.kit or "print", NAV["print"])
