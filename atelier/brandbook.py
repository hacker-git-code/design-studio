"""Brand guidelines as a single self-contained HTML page (inline SVG)."""

from __future__ import annotations

import html
import math

from .dna import AXES, AXIS_HELP
from .svg import document, el, f


def _inner(svg: str) -> str:
    return svg


def _lockup_tile(idt, kind, mode, bg, h=180):
    d, b, w, hh = idt.lockup(kind, mode, bg, 40)
    pad = 40 * 0.9
    W, H = w + 2 * pad, hh + 2 * pad
    return document(W, H, f'<g transform="translate({f(pad)} {f(pad)})">{b}</g>', defs=d)


def _construction(idt) -> str:
    """Symbol on its 10x10 construction grid with ink bounds and clear-space."""
    p = idt.palette
    S = 520
    pad = 80
    inner = S - 2 * pad
    grid = []
    for i in range(11):
        x = pad + inner * i / 10
        grid.append(el("line", x1=f(x), y1=pad, x2=f(x), y2=S - pad, stroke=p.primary.hex, stroke_opacity="0.18", stroke_width=1))
        grid.append(el("line", x1=pad, y1=f(x), x2=S - pad, y2=f(x), stroke=p.primary.hex, stroke_opacity="0.18", stroke_width=1))
    grid.append(el("circle", cx=S / 2, cy=S / 2, r=inner / 2, fill="none", stroke=p.primary.hex, stroke_opacity="0.25", stroke_dasharray="4 6"))
    d, g = idt.mark.place(pad, pad, inner, fg=p.ink, fg2=p.ink, fg3=p.ink, bg=p.paper, mono=True)
    clear = el("rect", x=pad * 0.35, y=pad * 0.35, width=S - pad * 0.7, height=S - pad * 0.7, fill="none",
               stroke=p.accent.hex, stroke_width=1.5, stroke_dasharray="8 6")
    return document(S, S, "".join(grid) + el("g", g, opacity="0.92") + clear, defs=d, bg=p.paper.hex)


def _contrast_badge(r):
    if r >= 7:
        return "AAA"
    if r >= 4.5:
        return "AA"
    if r >= 3:
        return "AA Large"
    return "—"


def type_scale(idt, n=6):
    ratio = 1.2 + 0.25 * idt.dna.energy + 0.1 * idt.dna.luxury
    return round(ratio, 3), [round(16 * ratio ** i, 1) for i in range(n)]


def render(idt, mockups: dict[str, str], patterns: dict[str, str], files_prefix: str = "", direction: int = 1,
           others: list | None = None) -> str:
    p = idt.palette
    t = idt.type
    esc = html.escape
    name = esc(idt.dna.name)
    css_fonts = t.css_url()
    on_primary = p.on(p.primary)
    ratio, scale = type_scale(idt)
    upper = "uppercase" if t.case == "upper" else "none"

    cover = _lockup_tile(idt, "stacked", "mono", p.primary)
    tiles = [
        ("Primary lockup", _lockup_tile(idt, "horizontal", "color", p.paper), p.paper),
        ("Stacked", _lockup_tile(idt, "stacked", "color", p.paper), p.paper),
        ("Reversed", _lockup_tile(idt, "horizontal", "mono", p.primary), p.primary),
        ("On light" if p.dark else "On dark", _lockup_tile(idt, "horizontal", "color", p.ink), p.ink),
        ("Wordmark", _lockup_tile(idt, "wordmark", "color", p.paper), p.paper),
        ("Symbol", idt.mark.svg(300, pad=40, **idt._mark_colors(idt.colors("color")), background=None), p.paper),
    ]
    tile_html = "".join(
        f'<figure class="tile" style="background:{bg.hex}"><div class="art">{svg}</div><figcaption style="color:{p.on(bg).hex}">{cap}</figcaption></figure>'
        for cap, svg, bg in tiles)

    badge_html = ""
    if idt.badge is not None:
        b1 = idt.badge_svg(420, "mono", p.paper, background=False)
        b2 = idt.badge_svg(420, "mono", p.primary, background=False)
        badge_html = f"""
<section><h2>Badge</h2><p class="lede">A secondary seal built around the symbol — for labels, stickers, packaging and back prints.</p>
<div class="two"><div class="panel" style="background:{p.paper.hex}">{b1}</div><div class="panel" style="background:{p.primary.hex}">{b2}</div></div></section>"""

    swatches = []
    total = {"paper": 60, "primary": 22, "ink": 8, "secondary": 5, "accent": 3, "muted": 2}
    for role, c in p.roles().items():
        fg = p.on(c)
        checks = []
        for other in ("ink", "paper"):
            if other != role:
                r = c.contrast(p.roles()[other])
                checks.append(f"vs {other} {r:.1f}:1 {_contrast_badge(r)}")
        swatches.append(
            f'<div class="sw" style="background:{c.hex};color:{fg.hex}"><b>{role.title()}</b>'
            f'<span>{c.hex.upper()}</span><span>{c.css_oklch()}</span>'
            f'<span class="small">{" · ".join(checks)}</span></div>')
    bar = "".join(f'<div style="flex:{v};background:{p.roles()[k].hex}" title="{k} {v}%"></div>' for k, v in total.items())
    ramp = "".join(f'<div style="background:{c.hex};color:{(p.ink if c.L > 0.6 else p.paper).hex}"><span>{k}</span></div>'
                   for k, c in p.scale("primary").items())

    pat_html = "".join(f'<figure class="pat">{svg}<figcaption>{esc(k)}</figcaption></figure>' for k, svg in patterns.items())
    mock_html = "".join(f'<figure class="mock">{svg}<figcaption>{esc(k.replace("-", " "))}</figcaption></figure>' for k, svg in mockups.items())

    dna_rows = "".join(
        f'<div class="axis"><span>{a}</span><div class="track"><div class="fill" style="width:{idt.dna.axes[a] * 100:.0f}%"></div></div>'
        f'<span class="small">{esc(AXIS_HELP[a])}</span></div>' for a in AXES)
    kw = " · ".join(esc(k) for k in idt.dna.keywords) or "—"
    scale_html = "".join(
        f'<div class="ts" style="font-size:{min(s, 96)}px">{esc(idt.dna.name if i > 3 else "The quick brown fox")} <small>{s}px</small></div>'
        for i, s in reversed(list(enumerate(scale))))

    nav_others = ""
    if others:
        nav_others = "<nav class='dirs'>" + "".join(
            f'<a href="../{o}/brandbook.html" class="{"on" if i + 1 == direction else ""}">Direction {i + 1}</a>' for i, o in enumerate(others)) + "</nav>"

    dl = [("Symbol", "logo/symbol.svg"), ("Horizontal lockup", "logo/lockup-horizontal.svg"), ("Stacked lockup", "logo/lockup-stacked.svg"),
          ("Wordmark", "logo/wordmark.svg"), ("Badge", "logo/badge.svg"), ("Mono / reversed", "logo/"), ("Design tokens (CSS)", "color/tokens.css"),
          ("Tailwind theme", "color/tailwind.config.js"), ("Palette JSON", "color/palette.json"), ("Brand spec (reproducible)", "brand.json")]
    dl_html = "".join(f'<a href="{files_prefix}{u}">{esc(n)}</a>' for n, u in dl)

    mono = t.mono or "ui-monospace"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} — Brand Guidelines</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="{css_fonts}" rel="stylesheet">
<style>
:root{{--paper:{p.paper.hex};--ink:{p.ink.hex};--primary:{p.primary.hex};--secondary:{p.secondary.hex};--accent:{p.accent.hex};--muted:{p.muted.hex};
--display:'{t.display}',serif;--text:'{t.text}',system-ui,sans-serif;--mono:'{mono}',ui-monospace,monospace}}
*{{box-sizing:border-box}}html,body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--text);font-size:16px;line-height:1.55}}
.wrap{{max-width:1180px;width:100%;margin:0 auto;padding:0 32px}}
header.cover{{background:var(--primary);color:{on_primary.hex};min-height:82vh;display:flex;flex-direction:column;justify-content:space-between;padding:32px 0}}
header .art{{display:flex;justify-content:center;align-items:center;flex:1}} header .art svg{{width:min(520px,80vw);height:auto}}
.meta{{display:flex;justify-content:space-between;font-family:var(--mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;opacity:.85}}
h1,h2,h3{{font-family:var(--display);font-weight:{t.display_weight};letter-spacing:{t.tracking if t.case == "upper" else min(t.tracking, 0)}em;text-transform:{upper};line-height:1.05;margin:0 0 .4em}}
h2{{font-size:clamp(28px,4vw,44px)}} section{{padding:72px 0;border-top:1px solid color-mix(in oklab,var(--ink) 12%,transparent)}}
.lede{{max-width:640px;opacity:.75;margin:0 0 28px}} .small{{font-size:12px;opacity:.75}}
.grid3{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}}
.tile{{margin:0;border-radius:14px;padding:24px;min-height:220px;display:flex;flex-direction:column;justify-content:space-between;border:1px solid color-mix(in oklab,var(--ink) 8%,transparent)}}
.tile .art{{flex:1;display:flex;align-items:center;justify-content:center}} .tile svg{{max-width:100%;max-height:160px;height:auto;width:auto}}
figcaption{{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;opacity:.7;margin-top:10px}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} .panel{{border-radius:14px;padding:32px;display:flex;justify-content:center}} .panel svg{{width:min(320px,100%);height:auto}}
.cons{{display:grid;grid-template-columns:minmax(0,520px) 1fr;gap:32px;align-items:center}} .cons svg{{width:100%;height:auto;border-radius:14px}}
.sws{{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px}}
.sw{{border-radius:14px;padding:18px;min-height:180px;display:flex;flex-direction:column;gap:2px;font-family:var(--mono);font-size:12px;border:1px solid color-mix(in oklab,var(--ink) 8%,transparent)}}
.sw b{{font-family:var(--text);font-size:15px;margin-bottom:auto}}
.bar{{display:flex;height:48px;border-radius:10px;overflow:hidden;margin:20px 0 8px;border:1px solid color-mix(in oklab,var(--ink) 15%,transparent)}}
.ramp{{display:flex;border-radius:10px;overflow:hidden;margin-top:12px}} .ramp div{{flex:1;height:64px;display:flex;align-items:flex-end;padding:6px;font-family:var(--mono);font-size:10px}}
.spec{{display:grid;grid-template-columns:1fr 1fr;gap:32px}} .aa{{font-family:var(--display);font-weight:{t.display_weight};font-size:160px;line-height:1}}
.ts{{font-family:var(--display);font-weight:{t.display_weight};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.2}} .ts small{{font-family:var(--mono);font-size:11px;opacity:.5}}
.axis{{display:grid;grid-template-columns:110px 1fr 1.4fr;gap:16px;align-items:center;margin:8px 0;font-family:var(--mono);font-size:13px}}
.track{{height:8px;border-radius:4px;background:color-mix(in oklab,var(--ink) 10%,transparent)}} .fill{{height:100%;border-radius:4px;background:var(--primary)}}
.pats{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}} .pat{{margin:0}} .pat svg{{width:100%;height:auto;border-radius:14px;display:block}}
.mocks{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:20px}} .mock{{margin:0}} .mock svg{{width:100%;height:auto;border-radius:14px;display:block}}
.dl{{display:flex;flex-wrap:wrap;gap:10px}} .dl a{{color:var(--ink);text-decoration:none;border:1px solid color-mix(in oklab,var(--ink) 20%,transparent);padding:10px 16px;border-radius:999px;font-size:14px}}
.dl a:hover{{background:var(--primary);color:{on_primary.hex};border-color:transparent}}
.dirs{{display:flex;gap:8px}} .dirs a{{color:inherit;text-decoration:none;font-family:var(--mono);font-size:12px;padding:6px 12px;border-radius:999px;border:1px solid currentColor;opacity:.7}} .dirs a.on{{opacity:1;background:{on_primary.hex};color:var(--primary)}}
footer{{padding:48px 0;font-family:var(--mono);font-size:12px;opacity:.6}}
@media (max-width:760px){{.two,.cons,.spec{{grid-template-columns:1fr}} .axis{{grid-template-columns:90px 1fr}} .axis .small{{display:none}} .aa{{font-size:110px}} .wrap{{padding:0 16px}}}}
</style></head><body>
<header class="cover"><div class="wrap meta"><span>{name} — Brand Guidelines</span>{nav_others}<span>Direction {direction:02d}</span></div>
<div class="art">{cover}</div>
<div class="wrap meta"><span>{esc(idt.dna.tagline or idt.dna.sector)}</span><span>Seed {idt.seed}</span></div></header>
<main class="wrap">
<section><h2>Brand DNA</h2><p class="lede">Every decision in this identity is derived from these eight values. Change them and the whole system re-composes.</p>
{dna_rows}<p class="small" style="margin-top:16px">Sector: {esc(idt.dna.sector)} · Mood: {kw} · Taste score: {idt.score:.2f}</p></section>
<section><h2>Logo</h2><p class="lede">A {esc(idt.mark.family)} symbol ({esc(idt.mark.variant)}) paired with a {esc(t.display)} wordmark set in {t.case} case at {t.tracking:+.3f}em tracking. All artwork is outlined vector.</p>
<div class="grid3">{tile_html}</div></section>
<section><h2>Construction</h2><div class="cons">{_construction(idt)}<div><p class="lede">The symbol is drawn on a 10 × 10 module grid. Keep a clear space equal to one third of the symbol's width on every side (dashed line). Never stretch, recolour outside the palette, add effects, or rebuild the wordmark in live type.</p>
<p class="small">Minimum size: symbol 16px / 5mm · lockup 96px / 25mm wide.</p></div></div></section>
{badge_html}
<section><h2>Colour</h2><p class="lede">{esc(p.scheme.title())} palette built in OKLCH for perceptually even steps. Use it in roughly these proportions.</p>
<div class="sws">{"".join(swatches)}</div><div class="bar">{bar}</div><p class="small">Paper 60 · Primary 22 · Ink 8 · Secondary 5 · Accent 3 · Muted 2</p>
<h3 style="margin-top:32px;font-size:20px">Primary tonal scale</h3><div class="ramp">{ramp}</div></section>
<section><h2>Typography</h2><div class="spec"><div><div class="aa">Aa</div><p><b>{esc(t.display)}</b> — display, {t.display_weight}<br>
<span class="small">ABCDEFGHIJKLMNOPQRSTUVWXYZ<br>abcdefghijklmnopqrstuvwxyz 0123456789</span></p></div>
<div><p style="font-family:var(--text);font-size:20px">{esc(t.text)} — text, {t.text_weight} / {t.text_bold}</p>
<p style="max-width:520px">Body copy is set in {esc(t.text)} at 16–18px with a 1.5 line height. Headlines use {esc(t.display)} on a {ratio} modular scale.{(" Labels, specs and code use " + esc(t.mono) + ".") if t.mono else ""}</p>
{f'<p style="font-family:var(--mono);font-size:13px;letter-spacing:.06em">SPEC · 280 GSM · {esc(t.mono).upper()}</p>' if t.mono else ""}</div></div>
<div style="margin-top:32px">{scale_html}</div></section>
<section><h2>Patterns</h2><p class="lede">Generated from the identity's own geometry and palette. Use as backgrounds, packaging and print surfaces.</p><div class="pats">{pat_html}</div></section>
<section><h2>Applications</h2><div class="mocks">{mock_html}</div></section>
<section><h2>Files</h2><div class="dl">{dl_html}</div></section>
</main><footer class="wrap">Generated algorithmically by Atelier — no AI image generation. Reproduce with <code>atelier remix brand.json</code>.</footer>
</body></html>"""
