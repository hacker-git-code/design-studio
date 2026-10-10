"""Orchestration: brief -> many candidates -> critics + learned taste -> best,
diverse directions -> full identity kits on disk."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import numpy as np

from .dna import BrandDNA
from .identity import Identity, build
from .svg import document


def board_svg(idt: Identity, on="paper", size=320) -> str:
    """A compact brand board, the kind of image people pin: lockup on a brand surface."""
    p = idt.palette
    bg = p.paper if on == "paper" else p.primary
    mode = "color" if on == "paper" else "mono"
    d, b, w, h = idt.lockup("stacked", mode, bg, 40)
    s = min(size * 0.62 / w, size * 0.62 / h)
    body = f'<g transform="translate({(size - w * s) / 2:.2f} {(size - h * s) / 2:.2f}) scale({s:.4f})">{b}</g>'
    return document(size, size, body, defs=d, bg=bg.hex)


def score(idt: Identity, taste=None) -> Identity:
    from .render import to_array
    from .taste.critics import critique
    from .taste.features import features

    crit = critique(idt)
    total = crit["total"]
    sc = {k: round(v, 3) for k, v in crit.items() if not k.startswith("_")}
    if taste is not None:
        feats = [features(to_array(board_svg(idt, on), 160)) for on in ("paper", "primary")]
        learned = float(np.mean(taste.score(np.array(feats))))
        sc["taste"] = round(learned, 3)
        sc["taste_explain"] = taste.explain(feats[0])
        total = 0.45 * total + 0.55 * learned
    idt.scores = sc
    idt.score = float(total)
    return idt


def explore(dna: BrandDNA, n: int = 24, k: int = 3, taste=None, families=None, verbose=True) -> list[Identity]:
    base = dna.seed() % 10_000_000
    cands = []
    t0 = time.time()
    for i in range(n):
        seed = base + i * 7919
        struct = None
        rng = np.random.default_rng(seed + 1)
        if taste is not None and taste.structures and rng.random() < 0.6:
            struct = taste.sample_structure(rng, dark=bool(rng.random() < dna.dark))
        fam = families[i % len(families)] if families else None
        try:
            idt = build(dna, seed, family=fam, palette_structure=struct)
            cands.append(score(idt, taste))
        except Exception as e:  # a bad candidate never kills the run
            if verbose:
                print(f"  candidate {i} failed: {e}")
    if verbose:
        print(f"[atelier] scored {len(cands)} candidates in {time.time() - t0:.1f}s")
    cands.sort(key=lambda c: -c.score)
    # diversity: greedy pick, penalise repeating symbol family / display face
    chosen: list[Identity] = []
    for c in cands:
        if len(chosen) >= k:
            break
        if any(c.mark.family == o.mark.family for o in chosen) and len(cands) - cands.index(c) > k - len(chosen):
            continue
        if any(c.type.display == o.type.display for o in chosen) and len(cands) - cands.index(c) > k - len(chosen):
            continue
        chosen.append(c)
    for c in cands:
        if len(chosen) >= k:
            break
        if c not in chosen:
            chosen.append(c)
    return chosen


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "brand"


def export(idt: Identity, out: Path, direction=1, others=None, png=True, mockup_png=True) -> Path:
    from . import brandbook
    from .mockups import render_kit
    from .patterns import choose_patterns, pattern_svg
    from .render import save_many
    from .tokens import write_tokens

    out = Path(out)
    for sub in ("logo", "color", "patterns", "mockups"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    p = idt.palette
    logos = {
        "symbol": idt.mark.svg(1024, pad=96, **idt._mark_colors(idt.colors("color"))),
        "symbol-mono": idt.mark.svg(1024, pad=96, **idt._mark_colors(idt.colors("mono"))),
        "symbol-reversed": idt.mark.svg(1024, pad=96, background=p.primary, **idt._mark_colors(idt.colors("mono", p.primary))),
        "lockup-horizontal": idt.lockup_svg("horizontal"),
        "lockup-horizontal-mono": idt.lockup_svg("horizontal", "mono"),
        "lockup-horizontal-reversed": idt.lockup_svg("horizontal", "mono", p.primary),
        "lockup-stacked": idt.lockup_svg("stacked"),
        "lockup-stacked-reversed": idt.lockup_svg("stacked", "mono", p.primary),
        "wordmark": idt.lockup_svg("wordmark"),
        "favicon": idt.mark.svg(64, pad=4, **idt._mark_colors(idt.colors("color"))),
    }
    if idt.badge is not None:
        logos["badge"] = idt.badge_svg(1024, "mono")
        logos["badge-color"] = idt.badge_svg(1024, "color")
    jobs = []
    for k, svg in logos.items():
        (out / "logo" / f"{k}.svg").write_text(svg)
        if png and k != "favicon":
            jobs.append((svg, out / "logo" / f"{k}.png", 1600 if "lockup" in k or "wordmark" in k else 1024))
    if png:
        jobs.append((logos["favicon"], out / "logo" / "favicon-32.png", 32))
    rng = np.random.default_rng(idt.seed + 99)
    pats = {}
    for i, kind in enumerate(choose_patterns(rng, idt, 3)):
        svg = pattern_svg(kind, idt, 800, 800, seed=idt.seed + i, invert=i == 1)
        pats[kind] = svg
        (out / "patterns" / f"{kind}.svg").write_text(svg)
    mocks = render_kit(idt, idt.seed)
    for k, svg in mocks.items():
        (out / "mockups" / f"{k}.svg").write_text(svg)
        if mockup_png:
            jobs.append((svg, out / "mockups" / f"{k}.png", 1400))
    save_many(jobs)
    write_tokens(idt, out / "color")
    (out / "brand.json").write_text(json.dumps(idt.to_dict(), indent=2))
    (out / "brandbook.html").write_text(brandbook.render(idt, mocks, pats, "", direction, others))
    return out


def overview_html(name: str, dirs: list[tuple[str, Identity]]) -> str:
    import html

    from .studio import board_svg as _b

    cards = []
    for i, (d, idt) in enumerate(dirs):
        p = idt.palette
        sw = "".join(f'<i style="background:{c.hex}"></i>' for c in p.roles().values())
        cards.append(f'<a class="card" href="{d}/brandbook.html"><div class="b">{_b(idt, "paper", 420)}</div><div class="b">{_b(idt, "primary", 420)}</div>'
                     f'<div class="m"><b>Direction {i + 1}</b><span>{html.escape(idt.mark.family)} · {html.escape(idt.type.display)} · {p.scheme}</span>'
                     f'<span>score {idt.score:.2f}</span><div class="sw">{sw}</div></div></a>')
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(name)} — Directions</title><style>
body{{margin:0;font-family:ui-sans-serif,system-ui,sans-serif;background:#f4f3ef;color:#151515}} @media (prefers-color-scheme:dark){{body{{background:#121212;color:#eee}}}}
h1{{font-weight:600;letter-spacing:-.02em;margin:40px 32px 8px}} p{{margin:0 32px 24px;opacity:.6}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:20px;padding:0 32px 48px}}
.card{{display:grid;grid-template-columns:1fr 1fr;border-radius:16px;overflow:hidden;text-decoration:none;color:inherit;background:rgba(127,127,127,.08)}}
.b svg{{width:100%;height:auto;display:block}} .m{{grid-column:1/3;padding:14px 16px;display:flex;flex-direction:column;gap:2px;font-size:13px}}
.m span{{opacity:.6}} .sw{{display:flex;gap:4px;margin-top:6px}} .sw i{{width:22px;height:22px;border-radius:6px;display:block;border:1px solid rgba(127,127,127,.2)}}
</style></head><body><h1>{html.escape(name)}</h1><p>{len(dirs)} directions, ranked by the critics and your taste model. Open one for the full brand book.</p>
<div class="grid">{"".join(cards)}</div></body></html>"""


def run(dna: BrandDNA, out_root: Path, n=24, k=3, taste=None, png=True, verbose=True) -> Path:
    out = Path(out_root) / slugify(dna.name)
    out.mkdir(parents=True, exist_ok=True)
    dirs = explore(dna, n, k, taste, verbose=verbose)
    names = [f"direction-{i + 1}" for i in range(len(dirs))]
    for i, idt in enumerate(dirs):
        t = time.time()
        export(idt, out / names[i], i + 1, names, png=png, mockup_png=png)
        if verbose:
            print(f"  direction {i + 1}: {idt.mark.family}/{idt.mark.variant} · {idt.type.display} {idt.type.display_weight} · "
                  f"{idt.palette.scheme}{' dark' if idt.palette.dark else ''} · score {idt.score:.2f} ({time.time() - t:.1f}s)")
    (out / "index.html").write_text(overview_html(dna.name, list(zip(names, dirs))))
    (out / "dna.json").write_text(dna.to_json(indent=2))
    return out
