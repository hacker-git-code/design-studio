"""atelier: algorithmic brand-identity studio.

  atelier new "minimal dark streetwear brand called NOCTA"     full identity kit (3 directions)
  atelier dna "..."                                           show the parsed Brand DNA
  atelier remix out/nocta/direction-1/brand.json --vary mark  variations of a direction
  atelier marks --family grid -n 32                           explore a symbol family
  atelier taste train refs/ -o taste_models/me.json           learn your taste from images
  atelier taste score some.png -m taste_models/me.json        how well an image fits it
  atelier fetch urls.txt refs/likes                           download a list of image URLs
  atelier llm dataset -o llm_data/                            build the fine-tuning dataset
  atelier serve                                               local web studio
  atelier fonts                                               pre-download the font library
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _taste(path):
    if not path:
        default = Path("taste_models/taste.json")
        path = default if default.exists() else None
    if not path:
        return None
    from .taste import TasteModel

    print(f"[atelier] using taste model {path}")
    return TasteModel.load(path)


def cmd_new(a):
    from .brief import parse
    from .studio import run

    dna = parse(a.brief, a.name, a.llm)
    if a.family:
        dna.mark_families = a.family.split(",")
    if a.dark is not None:
        dna.dark = 1.0 if a.dark else 0.0
    print(f"[atelier] {dna.name} · sector={dna.sector} · " + " ".join(f"{k}={v:.2f}" for k, v in dna.axes.items()))
    out = run(dna, Path(a.out), n=a.n, k=a.k, taste=_taste(a.taste), png=not a.no_png)
    print(f"\n  open {out / 'index.html'}\n")


def cmd_dna(a):
    from .brief import parse

    print(parse(a.brief, a.name, a.llm).to_json(indent=2))


def cmd_remix(a):
    import numpy as np

    from .dna import BrandDNA
    from .identity import build
    from .studio import export, score

    spec = json.loads(Path(a.spec).read_text())
    dna = BrandDNA.from_dict(spec["dna"])
    base = spec["seed"]
    out = Path(a.out or Path(a.spec).parent.parent / "remix")
    taste = _taste(a.taste)
    cands = []
    for i in range(a.n):
        rng = np.random.default_rng(base * 31 + i)
        seed = base if a.vary == "none" else int(rng.integers(1, 2**31))
        idt = build(dna, seed, family=spec["mark"]["family"] if a.vary in ("palette", "type") else None)
        if a.vary in ("palette", "type"):
            # keep the symbol, swap the requested layer
            orig = build(dna, base)
            idt.mark, idt.badge = orig.mark, orig.badge
            if a.vary == "palette":
                idt.type = orig.type
            else:
                idt.palette = orig.palette
        elif a.vary == "mark":
            orig = build(dna, base)
            idt.palette, idt.type = orig.palette, orig.type
        cands.append(score(idt, taste))
    cands.sort(key=lambda c: -c.score)
    names = [f"remix-{i + 1}" for i in range(min(a.k, len(cands)))]
    for i, idt in enumerate(cands[:a.k]):
        export(idt, out / names[i], i + 1, names, png=not a.no_png)
        print(f"  {out / names[i] / 'brandbook.html'}  score {idt.score:.2f}")


def cmd_marks(a):
    import numpy as np

    from .color import Color
    from .dna import AXES, BrandDNA
    from .marks.families import GENERATORS
    from .render import contact_sheet

    fams = a.family.split(",") if a.family else [f for f in GENERATORS if f != "emblem"]
    svgs, labels = [], []
    fg, fg2, fg3 = Color.from_hex(a.fg), Color.from_hex(a.fg2), Color.from_hex(a.fg3)
    for fam in fams:
        for i in range(a.n):
            rng = np.random.default_rng(a.seed + i)
            dna = BrandDNA(a.name, axes={x: float(rng.random()) for x in AXES})
            m = GENERATORS[fam](rng, dna, {"initials": dna.initials, "name": a.name, "display_font": "Inter", "display_weight": 700})
            svgs.append(m.svg(240, pad=16, fg=fg, fg2=fg2, fg3=fg3, background=Color.from_hex("#f7f5f0")))
            labels.append(f"{fam}:{m.variant}")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    contact_sheet(svgs, cols=8, cell=240, labels=labels).save(out)
    print(out)


def cmd_taste(a):
    from .taste.ingest import train

    if a.action == "train":
        train(Path(a.path), Path(a.out), a.name)
    else:
        from .taste import TasteModel, features, load_image

        m = TasteModel.load(a.model)
        v = features(load_image(a.path))
        print(json.dumps({"score": float(m.score(v)[0]), "explain": m.explain(v)}, indent=2))


def cmd_fetch(a):
    from .taste.fetch import fetch_urls

    fetch_urls(Path(a.urls), Path(a.out), delay=a.delay)


def cmd_llm(a):
    from .llm.dataset import build_dataset

    build_dataset(Path(a.out), n=a.n, image_index=Path(a.images) if a.images else None, captions=Path(a.captions) if a.captions else None,
                  paraphrase=a.paraphrase, seed=a.seed)


def cmd_serve(a):
    from .server import serve

    serve(a.host, a.port, Path(a.out), taste_path=a.taste)


def cmd_fonts(a):
    from concurrent.futures import ThreadPoolExecutor

    from . import fonts as F

    jobs = [(s.family, w) for s in F.LIBRARY for w in s.weights]
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda fw: F.font_path(*fw), jobs))
    print(f"{len(jobs)} font files cached in {F.CACHE}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="atelier", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("new", help="generate a full identity from a brief")
    p.add_argument("brief")
    p.add_argument("--name")
    p.add_argument("--out", default="out")
    p.add_argument("-n", type=int, default=24, help="candidates to explore")
    p.add_argument("-k", type=int, default=3, help="directions to export")
    p.add_argument("--taste", help="taste model json (default: taste_models/taste.json if present)")
    p.add_argument("--llm", help="brief parser backend, e.g. ollama:atelier-dna (default: rules)")
    p.add_argument("--family", help="force symbol families, comma separated")
    p.add_argument("--dark", type=lambda s: s.lower() in ("1", "true", "yes"), default=None)
    p.add_argument("--no-png", action="store_true")
    p.set_defaults(fn=cmd_new)

    p = sp.add_parser("dna", help="print the Brand DNA parsed from a brief")
    p.add_argument("brief")
    p.add_argument("--name")
    p.add_argument("--llm")
    p.set_defaults(fn=cmd_dna)

    p = sp.add_parser("remix", help="variations of an exported direction")
    p.add_argument("spec", help="path to brand.json")
    p.add_argument("--vary", choices=["all", "mark", "palette", "type", "none"], default="all")
    p.add_argument("-n", type=int, default=16)
    p.add_argument("-k", type=int, default=3)
    p.add_argument("--out")
    p.add_argument("--taste")
    p.add_argument("--no-png", action="store_true")
    p.set_defaults(fn=cmd_remix)

    p = sp.add_parser("marks", help="contact sheet of symbol families")
    p.add_argument("--family")
    p.add_argument("-n", type=int, default=16)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--name", default="Atelier")
    p.add_argument("--fg", default="#1d2b53")
    p.add_argument("--fg2", default="#e2725b")
    p.add_argument("--fg3", default="#f2b134")
    p.add_argument("-o", "--out", default="out/marks.png")
    p.set_defaults(fn=cmd_marks)

    p = sp.add_parser("taste", help="train or query a taste model")
    p.add_argument("action", choices=["train", "score"])
    p.add_argument("path", help="refs folder (train) or image (score)")
    p.add_argument("-o", "--out", default="taste_models/taste.json")
    p.add_argument("-m", "--model", default="taste_models/taste.json")
    p.add_argument("--name")
    p.set_defaults(fn=cmd_taste)

    p = sp.add_parser("fetch", help="download images from a list of URLs (only ones you may use)")
    p.add_argument("urls")
    p.add_argument("out")
    p.add_argument("--delay", type=float, default=1.0)
    p.set_defaults(fn=cmd_fetch)

    p = sp.add_parser("llm", help="LLM fine-tuning helpers")
    p.add_argument("action", choices=["dataset"])
    p.add_argument("-o", "--out", default="llm_data")
    p.add_argument("-n", type=int, default=6000)
    p.add_argument("--images", help="taste_models/<name>.images.jsonl from `atelier taste train`")
    p.add_argument("--captions", help="CSV of image filename,caption (e.g. your pin descriptions)")
    p.add_argument("--paraphrase", type=int, default=0, help="rewrite N briefs with Claude for variety (needs ANTHROPIC_API_KEY)")
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_llm)

    p = sp.add_parser("serve", help="local web studio")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--out", default="out")
    p.add_argument("--taste")
    p.set_defaults(fn=cmd_serve)

    p = sp.add_parser("fonts", help="download the curated font library")
    p.set_defaults(fn=cmd_fonts)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
