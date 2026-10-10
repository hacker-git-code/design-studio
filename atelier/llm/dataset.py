"""Fine-tuning data for the brief -> Brand DNA model.

Three sources, all producing chat-format JSONL:

1. Synthetic (always): sample a Brand DNA first, then *write* a brief from it
   with a combinatorial grammar (openers, sector phrases, intensity-graded
   adjectives, colour words, audiences, cultural references, casual noise).
   Because the label exists before the text, every pair is consistent.

2. Your references (optional): `atelier taste train` writes per-image design
   features; with a captions CSV (e.g. your pin descriptions or board names)
   each image becomes "caption -> DNA measured from the image". This grounds
   the model's language in the visual taste you collected.

3. Paraphrases (optional): rewrite a slice of briefs with Claude so the model
   sees real human phrasing. Costs a few dollars for a few thousand briefs.
"""

from __future__ import annotations

import csv
import json
import math
import random
from pathlib import Path

from ..brief import SYSTEM_PROMPT
from ..color import COLOR_WORDS
from ..dna import AXES, MARK_FAMILIES, SECTORS, BrandDNA

WORDS = {
    "geometric": (["geometric", "precise", "structured", "architectural", "modular", "grid-based"],
                  ["organic", "hand-drawn", "fluid", "natural", "soft-edged", "handmade"]),
    "minimal": (["minimal", "clean", "understated", "simple", "quiet", "pared-back"],
                ["bold", "maximal", "expressive", "loud", "eclectic", "busy in a good way"]),
    "warmth": (["warm", "earthy", "sunny", "cozy"], ["cool", "crisp", "icy", "clinical"]),
    "luxury": (["luxurious", "premium", "refined", "elegant", "high-end", "exclusive"],
               ["affordable", "everyday", "accessible", "down-to-earth", "unpretentious"]),
    "energy": (["energetic", "vibrant", "dynamic", "punchy", "electric"], ["calm", "serene", "slow", "gentle", "still"]),
    "heritage": (["timeless", "vintage", "classic", "heritage", "old-school"],
                 ["futuristic", "modern", "cutting-edge", "next-gen", "forward-looking"]),
    "playful": (["playful", "fun", "quirky", "cheeky", "joyful"], ["serious", "professional", "trustworthy", "corporate", "grown-up"]),
    "edge": (["edgy", "raw", "rebellious", "gritty", "underground"], ["friendly", "approachable", "soft", "welcoming", "kind"]),
}
INTENSITY = [(0.38, ["very", "really", "super", "extremely", ""]), (0.25, ["", "", "pretty", "quite"]), (0.0, ["slightly", "a bit", "somewhat", "a little"])]

SUBJECTS = {
    "streetwear": ["a streetwear label", "a skate-inspired clothing brand", "an underground hoodie brand", "a limited-drop streetwear brand", "a graphic tee brand"],
    "fashion": ["a clothing brand", "a womenswear label", "a menswear brand", "a slow-fashion label", "an apparel brand"],
    "luxury": ["a jewellery house", "a luxury fragrance brand", "a couture label", "a watch brand", "a leather goods maison"],
    "athletic": ["an activewear brand", "a running apparel company", "a fitness studio", "a performance sportswear brand"],
    "saas": ["a B2B SaaS tool", "a productivity app", "an analytics platform", "a project management tool", "a CRM startup"],
    "ai": ["an AI startup", "an AI agent platform", "a machine learning company", "an AI writing assistant"],
    "fintech": ["a fintech app", "a neobank", "a payments startup", "an investing platform", "a budgeting app"],
    "devtools": ["a developer tool", "an API platform", "a cloud infrastructure startup", "an open-source database company"],
    "food": ["a restaurant", "a bakery", "a snack brand", "a pizza place", "a plant-based food brand"],
    "coffee": ["a coffee roastery", "a specialty coffee shop", "a tea brand", "a neighbourhood cafe"],
    "wellness": ["a yoga studio", "a wellness brand", "a meditation app", "a supplements company", "a spa"],
    "beauty": ["a skincare brand", "a clean beauty line", "a candle company", "a hair salon"],
    "studio": ["a design studio", "a creative agency", "an architecture practice", "a photography studio"],
    "gaming": ["an indie game studio", "an esports team", "a gaming peripherals brand"],
    "outdoor": ["an outdoor gear brand", "a hiking apparel company", "a surf shop", "an adventure travel company"],
    "music": ["a record label", "a music festival", "a podcast", "a DJ collective"],
    "general": ["a new brand", "a small business", "a startup", "a personal brand"],
}
AUDIENCES = {
    "streetwear": ["for Gen Z creatives", "for skaters", "for the late-night crowd", "for city kids"],
    "fashion": ["for women 25-40", "for people who buy less but better", "for modern professionals"],
    "luxury": ["for collectors", "for a discerning clientele", "for people who value craft"],
    "saas": ["for remote teams", "for product managers", "for small businesses", "for operations teams"],
    "ai": ["for knowledge workers", "for developers", "for enterprises"],
    "fintech": ["for freelancers", "for first-time investors", "for small businesses", "for Gen Z"],
    "devtools": ["for backend engineers", "for platform teams", "for indie hackers"],
    "food": ["for families", "for the neighbourhood", "for health-conscious snackers"],
    "coffee": ["for early risers", "for coffee nerds", "for remote workers"],
    "wellness": ["for busy parents", "for burnt-out professionals", "for beginners"],
    "beauty": ["for sensitive skin", "for minimalists", "for people who hate fuss"],
}
OPENERS = ["", "", "I'm launching", "We're building", "Need branding for", "Design a brand identity for", "Create a logo and visual identity for",
           "hey, can you make a brand for", "Looking for a full identity for", "Brief:", "Help me brand", "Make me a brand kit for"]
REFS = [  # (phrase, condition on DNA)
    ("think Japanese minimalism", lambda d: d["minimal"] > .7 and d["energy"] < .5),
    ("Swiss modernist vibes", lambda d: d["geometric"] > .7 and d["minimal"] > .55),
    ("Y2K energy", lambda d: d["playful"] > .6 and d["energy"] > .6 and d["heritage"] < .5),
    ("old apothecary feel", lambda d: d["heritage"] > .7 and d["luxury"] > .5),
    ("brutalist", lambda d: d["edge"] > .7 and d["minimal"] < .55),
    ("Scandinavian calm", lambda d: d["minimal"] > .65 and d["edge"] < .35 and d["energy"] < .45),
    ("70s retro warmth", lambda d: d["heritage"] > .6 and d["warmth"] > .6),
    ("Bauhaus-inspired", lambda d: d["geometric"] > .75 and d["playful"] > .4),
    ("quiet luxury", lambda d: d["luxury"] > .75 and d["minimal"] > .7),
    ("90s rave flyer energy", lambda d: d["energy"] > .75 and d["edge"] > .6 and d["minimal"] < .45),
    ("Tokyo street culture", lambda d: d["edge"] > .65 and d["energy"] > .55),
    ("cyberpunk", lambda d: d["heritage"] < .2 and d["edge"] > .6),
    ("Mediterranean summer", lambda d: d["warmth"] > .7 and d["playful"] > .45),
]
SYL_A = ["no", "ve", "lu", "ka", "ori", "ze", "mi", "ta", "sol", "ar", "vi", "el", "fi", "qu", "ry", "ox", "ae", "ni", "pa", "lo", "be", "cy"]
SYL_B = ["ra", "lin", "va", "ko", "nde", "ta", "x", "lo", "ma", "ri", "on", "sa", "via", "no", "ly", "ra", "mo", "se", "ix", "ent"]
ADJ = ["Golden", "Quiet", "Wild", "Little", "North", "Common", "Second", "Salt", "Stone", "Field", "Night", "Paper", "Iron", "Blue", "Ember", "Juniper", "Atlas"]
NOUN = ["Oak", "Fox", "House", "Supply", "Studio", "Club", "Works", "Moon", "Harbor", "Hour", "Room", "Kitchen", "Lab", "Collective", "Bloom", "Garden"]


def make_name(r: random.Random) -> str:
    k = r.random()
    if k < 0.45:
        n = r.choice(SYL_A) + r.choice(SYL_B) + (r.choice(SYL_B) if r.random() < 0.3 else "")
        return n.upper() if r.random() < 0.25 else n.capitalize()
    if k < 0.75:
        return f"{r.choice(ADJ)} {r.choice(NOUN)}"
    if k < 0.88:
        return f"{r.choice(ADJ)} & {r.choice(NOUN)}"
    return r.choice(SYL_A).capitalize() + r.choice(NOUN).lower()


def sample_dna(r: random.Random) -> tuple[BrandDNA, list[str]]:
    sector = r.choice([s for s in SECTORS if s != "general"] + ["general"] * 1)
    prior = SECTORS[sector]
    axes = {a: min(1, max(0, prior["axes"][a] + r.gauss(0, 0.04))) for a in AXES}
    mentioned = r.sample(AXES, r.randint(2, 5))
    for a in mentioned:
        target = r.choice([r.uniform(0.0, 0.25), r.uniform(0.75, 1.0)])
        axes[a] = round(target, 2)
    dark = prior["dark"]
    if r.random() < 0.3:
        dark = r.choice([0.05, 0.9])
    hue = None
    hue2 = None
    colors = []
    if r.random() < 0.55:
        cw = r.sample(sorted(COLOR_WORDS), r.choice([1, 1, 2]))
        colors = cw
        hue = float(COLOR_WORDS[cw[0]])
        if len(cw) > 1 and abs(COLOR_WORDS[cw[1]] - hue) > 20:
            hue2 = float(COLOR_WORDS[cw[1]])
    fams = []
    if r.random() < 0.15:
        fams = [r.choice([m for m in MARK_FAMILIES])]
    name = make_name(r)
    tagline = ""
    kw = []
    for a in mentioned:
        hi, lo = WORDS[a]
        kw.append(r.choice(hi if axes[a] >= 0.5 else lo))
    dna = BrandDNA(name=name, sector=sector, tagline=tagline, axes={k: round(v, 2) for k, v in axes.items()}, dark=round(dark, 2),
                   hue=hue, hue_secondary=hue2, mark_families=fams, keywords=kw[:8] + colors)
    return dna, mentioned


def write_brief(r: random.Random, dna: BrandDNA, mentioned: list[str]) -> str:
    d = dna.axes
    adjs = []
    for a in mentioned:
        hi, lo = WORDS[a]
        v = d[a]
        dist = abs(v - 0.5)
        word = r.choice(hi if v >= 0.5 else lo)
        intens = next(opts for th, opts in INTENSITY if dist >= th)
        mod = r.choice(intens)
        adjs.append(f"{mod} {word}".strip())
    r.shuffle(adjs)
    subj = r.choice(SUBJECTS.get(dna.sector, SUBJECTS["general"]))
    name_clause = r.choice([f"called {dna.name}", f"named {dna.name}", f'"{dna.name}"', f"— {dna.name}", f"called {dna.name}"])
    parts = []
    opener = r.choice(OPENERS)
    style = r.random()
    if style < 0.5:
        s = f"{opener} {subj} {name_clause}".strip()
        if adjs:
            s += ", " + (", ".join(adjs[:-1]) + " and " + adjs[-1] if len(adjs) > 1 else adjs[0])
        parts.append(s)
    elif style < 0.8:
        parts.append(f"{dna.name}: {subj}.")
        parts.append("Vibe: " + ", ".join(adjs) + ".")
    else:
        parts.append(f"{opener} {subj} {name_clause}.".strip())
        if adjs:
            parts.append(f"It should feel {', '.join(adjs[:-1]) + ' and ' + adjs[-1] if len(adjs) > 1 else adjs[0]}.")
    colors = [k for k in dna.keywords if k in COLOR_WORDS]
    if colors:
        parts.append(r.choice([f"Colours: {' and '.join(colors)}.", f"mostly {' and '.join(colors)}", f"I love {' + '.join(colors)}.",
                               f"palette around {colors[0]}"]))
    if dna.dark > 0.8:
        parts.append(r.choice(["dark mode", "dark and moody", "black backgrounds", "night-time feel"]))
    elif dna.dark < 0.1:
        parts.append(r.choice(["light and airy", "bright, white space", "light backgrounds"]))
    if dna.sector in AUDIENCES and r.random() < 0.4:
        parts.append(r.choice(AUDIENCES[dna.sector]))
    refs = [p for p, cond in REFS if cond(d)]
    if refs and r.random() < 0.45:
        parts.append(r.choice(refs))
    if dna.mark_families:
        fam = dna.mark_families[0]
        parts.append(r.choice([f"maybe a {fam} style logo", f"I'd like a {fam} mark", f"logo idea: {fam}"]))
    text = " ".join(p if p.endswith((".", "!", "?")) or i == len(parts) - 1 else p + "." for i, p in enumerate(parts))
    if r.random() < 0.2:
        text = text.lower()
    return " ".join(text.split())


def target_json(dna: BrandDNA) -> str:
    d = dna.to_dict()
    d.pop("kit", None)
    d["axes"] = {k: round(v, 2) for k, v in d["axes"].items()}
    return json.dumps(d, ensure_ascii=False)


def example(brief: str, dna: BrandDNA) -> dict:
    return {"messages": [{"role": "system", "content": SYSTEM_PROMPT},
                         {"role": "user", "content": f"Brief: {brief}"},
                         {"role": "assistant", "content": target_json(dna)}]}


# ------------------------------------------------------------- from images

def dna_from_features(feat: list[float], caption: str) -> BrandDNA:
    """Measure DNA from a reference image's features, language from its caption."""
    from ..brief import parse_rules
    from ..taste.features import FEATURE_NAMES

    f = dict(zip(FEATURE_NAMES, feat))
    base = parse_rules(caption)
    ax = dict(base.axes)
    ax["minimal"] = 0.5 * ax["minimal"] + 0.5 * float(min(1, max(0, 1.1 - 1.4 * f["ink_cov"] - 1.2 * f["complexity"])))
    ax["energy"] = 0.5 * ax["energy"] + 0.5 * float(min(1, max(0, f["max_C"] / 0.22 * 0.7 + (f["contrast"] / 3.0) * 0.3)))
    dark = 0.9 if f["bg_L"] < 0.35 else 0.1 if f["bg_L"] > 0.8 else 0.4
    base.axes = {k: round(min(1, max(0, v)), 2) for k, v in ax.items()}
    base.dark = dark
    return base


def from_images(image_index: Path, captions: Path | None) -> list[dict]:
    caps = {}
    if captions and captions.exists():
        with captions.open() as fh:
            for row in csv.reader(fh):
                if len(row) >= 2:
                    caps[Path(row[0]).name] = row[1]
    out = []
    for line in image_index.read_text().splitlines():
        rec = json.loads(line)
        name = Path(rec["path"]).name
        cap = caps.get(name) or (f"{rec.get('tag') or 'brand'} identity like this reference" if not caps else None)
        if not cap:
            continue
        dna = dna_from_features(rec["features"], cap)
        out.append(example(cap, dna))
    return out


# -------------------------------------------------------------- paraphrase

def paraphrase(briefs: list[str], model: str = "claude-opus-5-5", workers: int = 4) -> list[str]:
    import anthropic
    from concurrent.futures import ThreadPoolExecutor

    client = anthropic.Anthropic()
    sys_p = ("Rewrite the user's brand brief the way a real founder might type it: vary length, tone and wording. "
             "Keep every fact (name, industry, colours, mood, references) and do not add new ones. Reply with the rewritten brief only.")

    def one(b):
        try:
            r = client.messages.create(model=model, max_tokens=400, system=sys_p, output_config={"effort": "low"},
                                       messages=[{"role": "user", "content": b}])
            if r.stop_reason == "refusal":
                return b
            t = "".join(x.text for x in r.content if x.type == "text").strip()
            return t or b
        except anthropic.APIError:
            return b

    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(one, briefs))


# ------------------------------------------------------------------- build

def build_dataset(out: Path, n: int = 6000, image_index: Path | None = None, captions: Path | None = None,
                  paraphrase_n: int = 0, seed: int = 0, val_frac: float = 0.05) -> tuple[Path, Path]:
    r = random.Random(seed)
    rows = []
    pairs = []
    for _ in range(n):
        dna, mentioned = sample_dna(r)
        pairs.append((write_brief(r, dna, mentioned), dna))
    if paraphrase_n:
        idx = r.sample(range(len(pairs)), min(paraphrase_n, len(pairs)))
        print(f"[llm] paraphrasing {len(idx)} briefs with Claude...")
        new = paraphrase([pairs[i][0] for i in idx])
        for i, t in zip(idx, new):
            pairs.append((t, pairs[i][1]))
    rows = [example(b, d) for b, d in pairs]
    if image_index:
        img_rows = from_images(Path(image_index), captions)
        print(f"[llm] {len(img_rows)} examples from your reference images")
        rows += img_rows * 3  # upweight real taste
    r.shuffle(rows)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    k = max(1, int(len(rows) * val_frac))
    tr, va = out / "train.jsonl", out / "val.jsonl"
    with tr.open("w") as fh:
        for row in rows[k:]:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with va.open("w") as fh:
        for row in rows[:k]:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[llm] {len(rows) - k} train / {k} val examples -> {out}")
    return tr, va
