"""Outlined typesetting helpers used by mockups and the brand book."""

from __future__ import annotations

from functools import lru_cache

from . import fonts as F


def _face(idt, role, weight):
    t = idt.type
    if role == "display":
        return t.display, weight or t.display_weight
    if role == "mono":
        return (t.mono or "JetBrains Mono"), weight or 400
    return t.text, weight or t.text_weight


@lru_cache(maxsize=4096)
def _run(s, family, weight, size, tracking):
    return F.outline(s, family, weight, size, tracking)


def measure(idt, s, size, role="text", weight=None, tracking=0.0) -> float:
    fam, w = _face(idt, role, weight)
    return _run(s, fam, w, round(size, 2), tracking).width


def text(idt, s: str, size: float, x: float, y: float, fill: str, role="text", weight=None,
         anchor="start", tracking=0.0, case=None, opacity=None) -> tuple[str, float]:
    """Baseline at y. Returns (svg, width)."""
    if case:
        s = F.apply_case(s, case)
    fam, w = _face(idt, role, weight)
    run = _run(s, fam, w, round(size, 2), tracking)
    if anchor == "middle":
        x -= run.width / 2
    elif anchor == "end":
        x -= run.width
    extra = {"opacity": opacity} if opacity is not None else {}
    return run.svg(x, y, fill, **extra), run.width


def paragraph(idt, s: str, size: float, x: float, y: float, width: float, fill: str, role="text",
              weight=None, leading=1.45, tracking=0.0, anchor="start", max_lines=None, case=None) -> tuple[str, float]:
    """Greedy word wrap. y is the first baseline. Returns (svg, total height)."""
    if case:
        s = F.apply_case(s, case)
    words = s.split()
    lines, cur = [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if measure(idt, trial, size, role, weight, tracking) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;") + "…"
    out = []
    for i, ln in enumerate(lines):
        ax = x + (width / 2 if anchor == "middle" else width if anchor == "end" else 0)
        svg, _ = text(idt, ln, size, ax, y + i * size * leading, fill, role, weight, anchor, tracking)
        out.append(svg)
    return "".join(out), len(lines) * size * leading


def fit_size(idt, s, max_width, size, role="display", weight=None, tracking=0.0, min_size=8) -> float:
    w = measure(idt, s, size, role, weight, tracking)
    if w <= max_width:
        return size
    return max(min_size, size * max_width / w)
