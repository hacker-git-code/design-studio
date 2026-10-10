"""Mark container: a symbol drawn in a 100x100 box with colour *tokens*, so
one generated mark renders as full-colour, one-colour, reversed, etc."""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field

from ..color import Color
from ..svg import document

_inst = itertools.count(1)

TOKEN = re.compile(r"§([a-z0-9]+)(?::(-?[0-9.]+))?§")


@dataclass
class Mark:
    family: str
    variant: str
    params: dict
    body: str
    defs: str = ""
    view: tuple = (0, 0, 100, 100)   # viewBox of the symbol's ink area
    meta: dict = field(default_factory=dict)

    def resolve(self, fg: Color, fg2: Color | None = None, fg3: Color | None = None,
                bg: Color | None = None, mono: bool = False) -> tuple[str, str]:
        """Substitute colour tokens; returns (defs, body) with ids made unique."""
        fg2 = fg if (mono or fg2 is None) else fg2
        fg3 = fg if (mono or fg3 is None) else fg3

        def sub(m):
            tok, arg = m.group(1), m.group(2)
            if tok == "fg":
                return fg.hex
            if tok == "fg2":
                return fg2.hex
            if tok == "fg3":
                return fg3.hex
            if tok == "bg":
                return bg.hex if bg else "#ffffff"
            if tok == "mix":
                return fg.hex if mono else fg.mix(fg2, float(arg)).hex
            if tok == "tone":
                if mono:
                    return fg.hex
                return fg.with_(L=max(0.05, min(0.98, fg.L + float(arg)))).hex
            if tok == "op":   # opacity used only in mono mode to separate overlapping planes
                return arg if mono else "1"
            return m.group(0)

        defs = TOKEN.sub(sub, self.defs)
        body = TOKEN.sub(sub, self.body)
        k = next(_inst)
        ids = set(re.findall(r'id="([A-Za-z0-9_-]+)"', defs))
        for i in ids:
            defs = defs.replace(f'id="{i}"', f'id="{i}_{k}"').replace(f"url(#{i})", f"url(#{i}_{k})")
            body = body.replace(f"url(#{i})", f"url(#{i}_{k})")
        return defs, body

    def place(self, x: float, y: float, size: float, **colors) -> tuple[str, str]:
        """Return (defs, group) placing the symbol so its view box fits a size x size square
        whose top-left is (x, y), centred."""
        defs, body = self.resolve(**colors)
        vx, vy, vw, vh = self.view
        s = size / max(vw, vh)
        ox = x + (size - vw * s) / 2 - vx * s
        oy = y + (size - vh * s) / 2 - vy * s
        return defs, f'<g transform="translate({ox:.3f} {oy:.3f}) scale({s:.5f})">{body}</g>'

    def svg(self, size: float = 512, pad: float = 0.0, background: Color | None = None, **colors) -> str:
        defs, grp = self.place(pad, pad, size - 2 * pad, **colors)
        return document(size, size, grp, defs=defs, bg=background.hex if background else None)

    def to_dict(self) -> dict:
        return {"family": self.family, "variant": self.variant, "params": self.params}
