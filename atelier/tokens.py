"""Design-token exports: CSS custom properties, Tailwind theme, JSON."""

from __future__ import annotations

import json
from pathlib import Path


def write_tokens(idt, out: Path):
    p, t = idt.palette, idt.type
    out = Path(out)
    roles = p.roles()
    css = [":root {"]
    for k, c in roles.items():
        css.append(f"  --color-{k}: {c.hex}; /* {c.css_oklch()} */")
    for role in ("primary", "secondary", "accent"):
        for step, c in p.scale(role).items():
            css.append(f"  --{role}-{step}: {c.hex};")
    css += [f"  --font-display: '{t.display}', serif;", f"  --font-text: '{t.text}', system-ui, sans-serif;"]
    if t.mono:
        css.append(f"  --font-mono: '{t.mono}', ui-monospace, monospace;")
    css += [f"  --display-weight: {t.display_weight};", f"  --display-tracking: {t.tracking}em;",
            f"  --radius: {22 if idt.dna.playful > .45 else 8 if idt.dna.edge < .7 else 2}px;", "}",
            f"/* fonts: {t.css_url()} */"]
    (out / "tokens.css").write_text("\n".join(css) + "\n")
    colors = {k: c.hex for k, c in roles.items()}
    for role in ("primary", "secondary", "accent"):
        colors[role] = {str(s): c.hex for s, c in p.scale(role).items()} | {"DEFAULT": roles[role].hex}
    tw = {"theme": {"extend": {"colors": colors, "fontFamily": {
        "display": [t.display, "serif"], "sans": [t.text, "system-ui", "sans-serif"], **({"mono": [t.mono, "monospace"]} if t.mono else {})}}}}
    (out / "tailwind.config.js").write_text("/** @type {import('tailwindcss').Config} */\nmodule.exports = " + json.dumps(tw, indent=2) + ";\n")
    (out / "palette.json").write_text(json.dumps(p.to_dict(), indent=2))
