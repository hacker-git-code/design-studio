"""Text brief -> BrandDNA.

Two interchangeable backends:
  * `rules`  - a lexicon parser that works offline, instantly, for free.
  * `llm`    - the fine-tuned model (see atelier/llm), or any OpenAI-compatible /
               Ollama / Anthropic endpoint. It returns the same JSON schema; its
               output is validated and clamped, then merged over the rule parse.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request

from .color import COLOR_WORDS
from .dna import AXES, JSON_SCHEMA_HINT, MARK_FAMILIES, SECTORS, BrandDNA

# word -> axis nudges (applied on top of the sector prior)
LEXICON: dict[str, dict[str, float]] = {}


def _lex(words: str, **nudges):
    for w in words.split():
        LEXICON.setdefault(w, {}).update(nudges)


_lex("minimal minimalist minimalistic clean simple quiet reduced understated essential pure calm-looking restrained bare",
     minimal=+.35, energy=-.1)
_lex("maximal maximalist bold loud expressive layered busy chaotic eclectic wild", minimal=-.35, energy=+.25)
_lex("luxury luxurious premium exclusive elegant refined sophisticated opulent couture high-end upscale prestige classy",
     luxury=+.35, minimal=+.1, playful=-.1)
_lex("affordable accessible everyday budget friendly-priced mass", luxury=-.3)
_lex("playful fun cheeky quirky whimsical joyful cute silly goofy happy bubbly",
     playful=+.35, energy=+.1, edge=-.1)
_lex("serious corporate professional trustworthy institutional formal enterprise", playful=-.3, edge=-.15)
_lex("warm earthy cozy sunny organic natural rustic terracotta autumn", warmth=+.3)
_lex("cool cold icy clinical crisp arctic", warmth=-.3)
_lex("energetic vibrant dynamic fast loud punchy electric explosive bright neon",
     energy=+.35)
_lex("calm serene peaceful slow soft gentle tranquil zen mindful soothing", energy=-.35, edge=-.15)
_lex("geometric precise structured modular grid architectural technical engineered swiss bauhaus",
     geometric=+.35)
_lex("organic handmade fluid flowing natural hand-drawn crafted artisanal soft-edged",
     geometric=-.35)
_lex("vintage retro heritage classic timeless traditional old-school nostalgic artisanal established",
     heritage=+.35)
_lex("futuristic modern cutting-edge innovative next-gen sci-fi cyber digital tech high-tech",
     heritage=-.35)
_lex("edgy raw rebellious underground grunge punk street gritty dark brutal brutalist subversive gothic",
     edge=+.35)
_lex("friendly approachable safe welcoming kind inclusive", edge=-.3, playful=+.1)
_lex("feminine delicate graceful romantic", luxury=+.1, edge=-.2, geometric=-.15)
_lex("masculine rugged tough strong", edge=+.2, energy=+.1)

DARK_WORDS = {"dark", "night", "noir", "black", "midnight", "moody", "gothic", "shadow", "nocturnal", "obsidian"}
LIGHT_WORDS = {"light", "bright", "airy", "white", "fresh", "pastel", "sunny"}

SECTOR_WORDS = {
    "streetwear": "streetwear street-wear hype drops hoodies skate skateboard sneakers urban graphic-tees",
    "fashion": "fashion clothing apparel garments wardrobe label garment brand-clothing tailoring womenswear menswear",
    "luxury": "jewelry jewellery watches couture maison perfume fragrance haute",
    "athletic": "sport sports athletic athleisure fitness gym running training activewear performance",
    "saas": "saas software platform dashboard b2b productivity app startup workflow crm analytics tool",
    "ai": "ai artificial-intelligence ml machine-learning agents llm neural copilot",
    "fintech": "fintech finance banking payments bank invest investing wallet crypto money trading",
    "devtools": "developer developers devtools api cli infrastructure cloud database open-source devops",
    "food": "food restaurant bakery kitchen pizza burger snacks plant-based eatery grocery juice candy chocolate icecream ice-cream drinks soda",
    "coffee": "coffee roastery roasters espresso cafe tea",
    "wellness": "wellness yoga meditation spa health mindfulness therapy supplements retreat",
    "beauty": "beauty skincare cosmetics makeup salon haircare candles",
    "studio": "agency studio creative design-studio architecture photography branding",
    "gaming": "gaming game games esports arcade",
    "outdoor": "outdoor outdoors hiking camping adventure mountain travel surf",
    "music": "music label records band festival audio podcast dj",
}
SECTOR_INDEX = {w: s for s, ws in SECTOR_WORDS.items() for w in ws.split()}
SECTOR_INDEX.update({w.rstrip("s"): s for w, s in list(SECTOR_INDEX.items()) if w.endswith("s") and len(w) > 4})

FAMILY_WORDS = {
    "monogram": "monogram initials lettermark letter",
    "emblem": "badge emblem seal crest stamp patch",
    "radial": "flower star burst radial mandala symmetric",
    "grid": "bauhaus modular tiles blocks",
    "organic": "blob leaf plant organic-shape pebble",
    "orbit": "planet space orbit cosmic galaxy",
    "lines": "lines stripes waves linear",
    "bars": "soundwave waveform equalizer bars",
    "isometric": "cube 3d isometric blocks-3d",
    "spiral": "spiral golden-ratio fibonacci sunflower",
    "stack": "chevron arrows layers stack steps",
}
FAMILY_INDEX = {w: fam for fam, ws in FAMILY_WORDS.items() for w in ws.split()}


def _tokens(text: str) -> list[str]:
    t = text.lower().replace("’", "'")
    for multi in ("street wear", "high end", "next gen", "cutting edge", "old school", "hand drawn", "open source",
                  "machine learning", "artificial intelligence", "graphic tees", "design studio", "golden ratio", "sci fi"):
        t = t.replace(multi, multi.replace(" ", "-"))
    return re.findall(r"[a-z0-9][a-z0-9\-]*", t)


def extract_name(text: str) -> str | None:
    m = re.search(r"[\"“']([^\"”']{2,32})[\"”']", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"\b(?:called|named|name is|brand is|it's|its)\s+([A-Z0-9][\w&.\-]*(?:\s+(?:&\s+|and\s+)?[A-Z0-9][\w&.\-]*){0,2})", text)
    if m:
        return m.group(1).strip(" .,")
    m = re.search(r"\b(?:called|named)\s+([\w&.\-]+(?:\s+[\w&.\-]+)?)", text, re.I)
    if m:
        return m.group(1).strip(" .,").title()
    caps = re.findall(r"\b([A-Z][A-Z0-9]{2,})\b", text)
    if caps:
        return caps[0]
    return None


def extract_tagline(text: str) -> str:
    m = re.search(r"(?:tagline|slogan)\s*(?:is|:)?\s*[\"“']?([^\"”'\n.]{3,60})", text, re.I)
    return m.group(1).strip() if m else ""


def parse_rules(text: str, name: str | None = None) -> BrandDNA:
    toks = _tokens(text)
    sector_votes: dict[str, int] = {}
    for t in toks:
        s = SECTOR_INDEX.get(t) or SECTOR_INDEX.get(t.rstrip("s"))
        if s:
            sector_votes[s] = sector_votes.get(s, 0) + 1
    sector = max(sector_votes, key=sector_votes.get) if sector_votes else "general"
    # clothing + luxury words -> luxury-fashion; clothing + street words -> streetwear
    if sector == "fashion" and any(t in LEXICON and LEXICON[t].get("edge", 0) > 0 for t in toks):
        sector = "streetwear"
    prior = SECTORS[sector]
    axes = dict(prior["axes"])
    dark = prior["dark"]
    neg = False
    for i, t in enumerate(toks):
        if t in ("not", "no", "never", "without", "avoid", "less", "anti"):
            neg = True
            continue
        nudges = LEXICON.get(t) or LEXICON.get(t.rstrip("s"))
        if nudges:
            sign = -0.8 if neg else 1.0
            for a, v in nudges.items():
                axes[a] = axes[a] + sign * v
        if t in DARK_WORDS:
            dark = dark + (-0.4 if neg else 0.45)
        if t in LIGHT_WORDS:
            dark = dark - 0.3
        if not t.startswith(("not", "no")):
            neg = False if t not in ("very", "too", "so", "really") else neg
    hue = None
    hue2 = None
    kws = []
    for t in toks:
        if t in COLOR_WORDS:
            if hue is None:
                hue = COLOR_WORDS[t]
            elif hue2 is None and abs(COLOR_WORDS[t] - hue) > 20:
                hue2 = COLOR_WORDS[t]
        if t in LEXICON or t in COLOR_WORDS or t in DARK_WORDS:
            kws.append(t)
    if any(t in ("black", "monochrome", "monochromatic", "grayscale") for t in toks) and hue is None:
        axes["energy"] = axes["energy"] - 0.2
    fams = []
    for t in toks:
        fam = FAMILY_INDEX.get(t)
        if fam and fam not in fams:
            fams.append(fam)
    name = name or extract_name(text) or "Untitled"
    return BrandDNA(name=name, sector=sector, tagline=extract_tagline(text), axes=axes, dark=dark, hue=hue,
                    hue_secondary=hue2, mark_families=fams, keywords=list(dict.fromkeys(kws))[:8])


# ------------------------------------------------------------------ LLM backend

SYSTEM_PROMPT = (
    "You are a brand strategist that converts a creative brief into a Brand DNA JSON object. "
    "Respond with JSON only, no prose. Schema: " + json.dumps(JSON_SCHEMA_HINT)
)


def _extract_json(s: str) -> dict:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-z]*\n?|```$", "", s, flags=re.M).strip()
    i, j = s.find("{"), s.rfind("}")
    return json.loads(s[i:j + 1])


def _post(url, payload, headers):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())


def call_llm(text: str, backend: str) -> dict:
    """backend examples:
        ollama:atelier-dna            (local Ollama, after `ollama create`)
        openai:http://localhost:8000/v1:atelier   (vLLM / llama.cpp server / any OpenAI-compatible)
        hf:./checkpoints/atelier-dna  (transformers, local merged model)
        anthropic:claude-opus-5-5     (zero-shot via the Anthropic SDK; any model id works)
    """
    kind, _, rest = backend.partition(":")
    user = f"Brief: {text}"
    if kind == "ollama":
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        out = _post(f"{host}/api/chat", {"model": rest, "stream": False, "format": "json",
                                         "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                                      {"role": "user", "content": user}]}, {})
        return _extract_json(out["message"]["content"])
    if kind == "openai":
        base, _, model = rest.rpartition(":")
        key = os.environ.get("OPENAI_API_KEY", "none")
        out = _post(f"{base}/chat/completions", {"model": model, "temperature": 0.2,
                                                 "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                                              {"role": "user", "content": user}]},
                    {"Authorization": f"Bearer {key}"})
        return _extract_json(out["choices"][0]["message"]["content"])
    if kind == "anthropic":
        import anthropic

        model = rest or "claude-opus-5-5"
        kw = {}
        if model in ("claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"):
            # server-side refusal fallback: a declined request is re-run on a fallback model
            kw = dict(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        client = anthropic.Anthropic()  # ANTHROPIC_API_KEY or an `ant auth login` profile
        resp = client.beta.messages.create(
            model=model, max_tokens=2000, system=SYSTEM_PROMPT,
            output_config={"effort": "medium"},
            messages=[{"role": "user", "content": user}], **kw)
        if resp.stop_reason == "refusal":
            raise RuntimeError("model declined the brief")
        return _extract_json("".join(b.text for b in resp.content if b.type == "text"))
    if kind == "hf":
        from .llm.infer import generate_dna_json

        return _extract_json(generate_dna_json(rest, text))
    raise ValueError(f"unknown backend {backend}")


def sanitize(d: dict, fallback: BrandDNA) -> BrandDNA:
    """Validate/clamp model output; anything missing falls back to the rule parse."""
    out = fallback.to_dict()
    if isinstance(d.get("name"), str) and d["name"].strip() and fallback.name == "Untitled":
        out["name"] = d["name"].strip()[:40]
    if d.get("sector") in SECTORS:
        out["sector"] = d["sector"]
    if isinstance(d.get("tagline"), str):
        out["tagline"] = d["tagline"][:80]
    axes = d.get("axes") or {}
    for a in AXES:
        try:
            v = float(axes.get(a, out["axes"][a]))
            out["axes"][a] = min(1.0, max(0.0, v))
        except (TypeError, ValueError):
            pass
    for k in ("dark",):
        try:
            out[k] = min(1.0, max(0.0, float(d.get(k, out[k]))))
        except (TypeError, ValueError):
            pass
    for k in ("hue", "hue_secondary"):
        v = d.get(k, out[k])
        try:
            out[k] = None if v is None else float(v) % 360
        except (TypeError, ValueError):
            pass
    if isinstance(d.get("mark_families"), list):
        out["mark_families"] = [m for m in d["mark_families"] if m in MARK_FAMILIES] or out["mark_families"]
    if isinstance(d.get("keywords"), list):
        out["keywords"] = [str(k)[:24] for k in d["keywords"]][:8]
    if isinstance(d.get("fonts"), list):
        out["fonts"] = [str(x) for x in d["fonts"]][:3]
    out["kit"] = None
    return BrandDNA.from_dict(out)


def parse(text: str, name: str | None = None, backend: str | None = None) -> BrandDNA:
    base = parse_rules(text, name)
    backend = backend or os.environ.get("ATELIER_LLM")
    if not backend:
        return base
    try:
        return sanitize(call_llm(text, backend), base)
    except Exception as e:  # never let the model break generation
        print(f"[atelier] LLM backend '{backend}' failed ({e}); using rule parser.")
        return base
