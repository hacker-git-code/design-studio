"""Design features extracted from any image: a reference you love (a Pinterest
pin, a Behance shot, a photo of packaging) or one of our own renders. The
same features feed the taste model and the critics, so the system learns what
"good" looks like from your references and measures candidates on that scale.

Only statistics are kept (palette structure, composition), never pixels."""

from __future__ import annotations

import math

import numpy as np

from ..color import Color, oklab_array_to_oklch, srgb_array_to_oklab

FEATURE_NAMES = (
    "bg_L",          # background lightness
    "bg_C",          # background chroma
    "n_colors",      # significant distinct colours
    "max_C",         # most saturated significant colour
    "mean_C",        # area-weighted chroma
    "L_range",       # lightness range of significant colours
    "hue_spread",    # circular spread of chromatic hues
    "accent_share",  # area of the most chromatic colour
    "ink_cov",       # non-background coverage (negative space = 1 - this)
    "edge_density",  # mean gradient energy
    "symmetry",      # left/right mirror similarity
    "com_offset",    # visual centre-of-mass offset from centre
    "complexity",    # share of pixels on edges
    "contrast",      # log max contrast between significant colours
)


def load_image(path, max_side=160) -> np.ndarray:
    from PIL import Image, ImageOps

    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        im = bg
    im = im.convert("RGB")
    im.thumbnail((max_side, max_side))
    return np.asarray(im, dtype=np.float32) / 255.0


def kmeans(X: np.ndarray, k: int = 6, iters: int = 14, seed: int = 0):
    rng = np.random.default_rng(seed)
    # k-means++ init
    C = [X[rng.integers(len(X))]]
    for _ in range(1, k):
        d = np.min(((X[:, None, :] - np.array(C)[None]) ** 2).sum(-1), axis=1)
        if d.sum() <= 0:
            C.append(X[rng.integers(len(X))])
            continue
        C.append(X[rng.choice(len(X), p=d / d.sum())])
    C = np.array(C)
    for _ in range(iters):
        lab = np.argmin(((X[:, None, :] - C[None]) ** 2).sum(-1), axis=1)
        for j in range(k):
            m = lab == j
            if m.any():
                C[j] = X[m].mean(0)
    w = np.bincount(lab, minlength=k) / len(X)
    return C, w, lab


def palette(img: np.ndarray, k: int = 6, merge: float = 0.05):
    """Dominant colours as (OKLab centres, weights), merged and sorted by area."""
    px = img.reshape(-1, 3)
    if len(px) > 6000:
        px = px[np.random.default_rng(0).choice(len(px), 6000, replace=False)]
    lab = srgb_array_to_oklab(px)
    C, w, _ = kmeans(lab, k)
    # merge near-identical clusters
    order = np.argsort(-w)
    cs, ws = [], []
    for i in order:
        for j, c in enumerate(cs):
            if np.linalg.norm(c - C[i]) < merge:
                ws[j] += w[i]
                cs[j] = (cs[j] * (ws[j] - w[i]) + C[i] * w[i]) / ws[j]
                break
        else:
            cs.append(C[i].copy())
            ws.append(float(w[i]))
    return np.array(cs), np.array(ws)


def _lab_to_color(lab) -> Color:
    lch = oklab_array_to_oklch(np.asarray(lab)[None])[0]
    return Color(float(lch[0]), float(lch[1]), float(lch[2]))


def palette_structure(cs, ws) -> dict | None:
    """Assign roles (paper/ink/primary/secondary/accent) to a reference's palette."""
    cols = [_lab_to_color(c) for c in cs]
    sig = [(c, w) for c, w in zip(cols, ws) if w > 0.02]
    if len(sig) < 2:
        return None
    paper = sig[0][0]
    rest = sig[1:]
    ink = max(rest, key=lambda cw: paper.contrast(cw[0]))[0]
    chrom = sorted([cw for cw in rest if cw[0] is not ink], key=lambda cw: -cw[0].C * (0.5 + cw[1]))
    if not chrom:
        return None
    primary = chrom[0][0]
    secondary = chrom[1][0] if len(chrom) > 1 else primary.with_(L=min(0.9, primary.L + 0.2), C=primary.C * 0.6)
    accent = max(chrom, key=lambda cw: cw[0].C)[0] if len(chrom) > 2 else secondary
    if primary.C < 0.03:
        return None
    from ..color import palette_from_structure_roles

    return palette_from_structure_roles({"paper": paper, "ink": ink, "primary": primary, "secondary": secondary,
                                         "accent": accent, "muted": paper.mix(ink, 0.1)})


def features(img: np.ndarray, with_structure=False):
    cs, ws = palette(img)
    lch = oklab_array_to_oklch(cs)
    sig = ws > 0.03
    bg = cs[0]
    bgc = lch[0]
    chroma = lch[sig, 1]
    hues = lch[sig & (lch[:, 1] > 0.04), 2]
    if len(hues) > 1:
        a = np.radians(hues)
        wv = ws[sig & (lch[:, 1] > 0.04)]
        R = np.hypot((np.cos(a) * wv).sum(), (np.sin(a) * wv).sum()) / wv.sum()
        hue_spread = math.sqrt(max(0.0, -2 * math.log(max(R, 1e-6)))) / math.pi
    else:
        hue_spread = 0.0
    chrom_idx = np.argmax(lch[:, 1] * (ws > 0.01))
    lab = srgb_array_to_oklab(img)
    dist = np.linalg.norm(lab - bg[None, None], axis=-1)
    ink = dist > 0.09
    cov = float(ink.mean())
    L = lab[..., 0]
    gy, gx = np.gradient(L)
    g = np.hypot(gx, gy)
    edge_density = float(g.mean() * 10)
    complexity = float((g > 0.04).mean())
    if ink.any():
        ys, xs = np.nonzero(ink)
        h, w = ink.shape
        com = math.hypot(xs.mean() / w - 0.5, ys.mean() / h - 0.5)
        sym = 1.0 - float(np.abs(ink.astype(float) - ink[:, ::-1].astype(float)).mean() / max(cov, 1e-3) / 2)
    else:
        com, sym = 0.0, 1.0
    sig_cols = [_lab_to_color(c) for c in cs[sig]]
    cmax = max((a.contrast(b) for i, a in enumerate(sig_cols) for b in sig_cols[i + 1:]), default=1.0)
    vec = np.array([
        bgc[0], bgc[1], float(sig.sum()), float(chroma.max() if len(chroma) else 0), float((lch[:, 1] * ws).sum()),
        float(np.ptp(lch[sig, 0]) if sig.sum() > 1 else 0), hue_spread, float(ws[chrom_idx]), cov, edge_density,
        max(0.0, sym), com, complexity, math.log(cmax),
    ], dtype=np.float64)
    if with_structure:
        return vec, palette_structure(cs, ws)
    return vec
