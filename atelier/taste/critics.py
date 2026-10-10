"""Built-in design critics: the rules a senior designer applies on sight.
They work with zero training data and are combined with the learned taste."""

from __future__ import annotations

import math

import numpy as np

from ..color import Color


def _alpha(svg, res):
    from ..render import to_image

    return np.asarray(to_image(svg, res))[..., 3].astype(np.float32) / 255.0


def mark_metrics(idt) -> dict:
    m = idt.mark
    k = Color(0.2, 0, 0)
    svg_hi = m.svg(256, fg=k, fg2=k, fg3=k, mono=True)
    a = _alpha(svg_hi, 256)
    ys, xs = np.nonzero(a > 0.5)
    if len(xs) == 0:
        return dict(coverage=0, balance=1, aspect=1, mush=1, legibility=0)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    box = a[y0:y1, x0:x1]
    coverage = float(box.mean())
    cy, cx = np.average(np.indices(box.shape), axis=(1, 2), weights=box + 1e-9)
    balance = math.hypot(cx / box.shape[1] - 0.5, cy / box.shape[0] - 0.5)
    aspect = max(box.shape) / max(1, min(box.shape))
    # small-size legibility: render at favicon size, compare with a downsample of the big render
    small = _alpha(m.svg(24, fg=k, fg2=k, fg3=k, mono=True), 24)
    mush = float(((small > 0.2) & (small < 0.8)).mean() / max(1e-3, (small > 0.2).mean()))
    from PIL import Image

    ref = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((24, 24), Image.LANCZOS), dtype=np.float32) / 255
    legibility = float(np.corrcoef(ref.ravel(), small.ravel())[0, 1]) if small.std() > 0 and ref.std() > 0 else 0.0
    return dict(coverage=coverage, balance=balance, aspect=aspect, mush=mush, legibility=legibility)


def wordmark_density(idt) -> float:
    from ..svg import document

    run = idt.wordmark_run(80)
    if not run.ink:
        return 0.3
    x0, y0, x1, y1 = run.ink
    svg = document(x1 - x0 + 2, y1 - y0 + 2, run.svg(1 - x0, 1 - y0, "#000"))
    a = _alpha(svg, int(min(600, (x1 - x0 + 2) * 2)))
    return float(a.mean())


def critique(idt) -> dict:
    """Returns component scores in 0..1 (higher is better) plus a weighted total."""
    mm = mark_metrics(idt)
    p = idt.palette
    s = {}
    # coverage: marks between ~25% and ~65% ink read as confident and balanced
    c = mm["coverage"]
    s["coverage"] = float(np.exp(-((c - 0.45) / 0.22) ** 2))
    s["balance"] = float(np.clip(1 - mm["balance"] / 0.12, 0, 1))
    s["aspect"] = float(np.clip(1 - (mm["aspect"] - 1.25) / 1.2, 0, 1))
    s["small_size"] = float(np.clip(0.5 * (1 - mm["mush"]) + 0.5 * max(0.0, mm["legibility"]), 0, 1))
    # colour
    s["contrast"] = float(np.clip((p.mark_color().contrast(p.paper) - 2.0) / 3.0, 0, 1) * 0.5 +
                          np.clip((p.ink.contrast(p.paper) - 7) / 7, 0, 1) * 0.5)
    chromas = sorted([p.primary.C, p.secondary.C, p.accent.C])
    s["harmony"] = float(np.clip(1 - max(0.0, chromas[0] - 0.12) * 6, 0, 1))  # three loud colours = noise
    # mark/wordmark visual weight harmony
    wd = wordmark_density(idt)
    ratio = (c + 1e-3) / (wd + 1e-3)
    s["weight_match"] = float(np.exp(-(math.log(ratio / 1.4)) ** 2 / 0.9))
    w = dict(coverage=1.0, balance=0.8, aspect=0.6, small_size=1.2, contrast=1.0, harmony=0.6, weight_match=0.8)
    s["total"] = sum(s[k] * w[k] for k in w) / sum(w.values())
    s["_metrics"] = {k: round(v, 3) for k, v in mm.items()} | {"word_density": round(wd, 3)}
    return s
