import json
import math

import numpy as np
import pytest

from atelier.brief import extract_name, parse_rules, sanitize
from atelier.color import Color, generate_palette
from atelier.dna import AXES, BrandDNA
from atelier.identity import build
from atelier.marks.families import GENERATORS
from atelier.render import to_image


def test_color_roundtrip_and_contrast():
    for hx in ("#000000", "#ffffff", "#1d2b53", "#e2725b", "#22cc88"):
        assert Color.from_hex(hx).hex == hx
    assert math.isclose(Color.from_hex("#000").contrast(Color.from_hex("#fff")), 21, rel_tol=1e-3)
    assert Color.oklch(0.7, 0.4, 140).in_gamut()


def test_palette_contrast_guarantee():
    for seed in range(30):
        rng = np.random.default_rng(seed)
        p = generate_palette(rng, hue=rng.uniform(0, 360), energy=rng.random(), luxury=rng.random(), minimal=rng.random(),
                             warmth=rng.random(), dark=bool(seed % 2), playful=rng.random())
        assert p.ink.contrast(p.paper) >= 7
        assert p.mark_color().contrast(p.paper) >= 2.6


@pytest.mark.parametrize("family", [f for f in GENERATORS if f != "emblem"])
def test_every_family_renders_ink(family):
    for seed in range(6):
        rng = np.random.default_rng(seed)
        dna = BrandDNA("Test Brand", axes={a: float(rng.random()) for a in AXES})
        m = GENERATORS[family](rng, dna, {"initials": "TB", "name": "Test Brand", "display_font": "Inter", "display_weight": 700})
        a = np.asarray(to_image(m.svg(96, fg=Color.from_hex("#111111")), 96))[..., 3]
        assert (a > 0).mean() > 0.03, f"{family} seed {seed} drew nothing"


def test_identity_is_deterministic():
    dna = parse_rules("minimal saas analytics tool called Fluxboard, blue")
    a, b = build(dna, 42), build(dna, 42)
    assert json.dumps(a.to_dict(), sort_keys=True) == json.dumps(b.to_dict(), sort_keys=True)
    assert a.mark.body == b.mark.body


def test_brief_parser():
    assert extract_name("a coffee roastery named Ember & Oak, warm") == "Ember & Oak"
    assert extract_name('label called "Maison Aurel"') == "Maison Aurel"
    d = parse_rules("a dark, raw, rebellious streetwear brand called NOCTA")
    assert d.name == "NOCTA" and d.sector == "streetwear" and d.dark > 0.7 and d.edge > 0.8
    d = parse_rules("calm minimal wellness app, not playful")
    assert d.sector == "wellness" and d.playful < 0.35 and d.minimal > 0.8


def test_sanitize_clamps_model_output():
    base = parse_rules("a brand")
    d = sanitize({"name": "X", "sector": "nope", "axes": {"energy": 7, "minimal": "bad"}, "hue": 400, "mark_families": ["grid", "zzz"]}, base)
    assert d.axes["energy"] == 1.0 and d.sector == base.sector and d.hue == 40 and d.mark_families == ["grid"]


def test_lockups_and_kit_end_to_end(tmp_path):
    from atelier.studio import run

    dna = parse_rules("playful bakery called Bun Club, warm pink")
    out = run(dna, tmp_path, n=4, k=1, png=False, verbose=False)
    d = out / "direction-1"
    for f in ("brandbook.html", "brand.json", "logo/symbol.svg", "logo/lockup-horizontal.svg", "color/tokens.css",
              "color/tailwind.config.js", "mockups/business-cards.svg"):
        assert (d / f).exists(), f
    assert (out / "index.html").exists()
    spec = json.loads((d / "brand.json").read_text())
    assert spec["dna"]["name"] == "Bun Club"


def test_taste_model_prefers_likes():
    from atelier.taste import TasteModel

    rng = np.random.default_rng(0)
    likes = rng.normal(0, 1, (60, 14))
    dislikes = rng.normal(3, 1, (60, 14))
    m = TasteModel.fit(likes, neg=dislikes)
    assert m.score(np.zeros(14))[0] > m.score(np.full(14, 3.0))[0]


def test_llm_dataset(tmp_path):
    from atelier.llm.dataset import build_dataset

    tr, va = build_dataset(tmp_path, n=200, seed=1)
    rows = [json.loads(line) for line in tr.read_text().splitlines()]
    assert len(rows) > 150
    for r in rows[:50]:
        dna = BrandDNA.from_dict(json.loads(r["messages"][2]["content"]))
        assert dna.name and set(dna.axes) == set(AXES)
