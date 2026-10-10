"""Build a taste model from a folder of reference images.

    refs/
      likes/          <- images you love (any sub-folders become style tags)
      dislikes/       <- optional: images you want to steer away from

Only feature statistics and palette structures are stored in the model."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .features import features, load_image
from .model import TasteModel

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def iter_images(root: Path):
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() in EXTS and p.is_file():
            yield p


def extract(root: Path, verbose=True):
    X, structs, tags, paths = [], [], [], []
    for i, p in enumerate(iter_images(root)):
        try:
            v, st = features(load_image(p), with_structure=True)
        except Exception as e:  # unreadable file
            if verbose:
                print(f"  skip {p.name}: {e}")
            continue
        X.append(v)
        if st:
            structs.append(st)
        rel = p.relative_to(root)
        tags.append(rel.parts[0] if len(rel.parts) > 1 else "")
        paths.append(str(p))
        if verbose and (i + 1) % 50 == 0:
            print(f"  {i + 1} images...")
    return np.array(X), structs, tags, paths


def train(refs: Path, out: Path, name: str | None = None, verbose=True) -> TasteModel:
    refs = Path(refs)
    likes = refs / "likes" if (refs / "likes").exists() else refs
    dislikes = refs / "dislikes"
    if verbose:
        print(f"[taste] reading likes from {likes}")
    X, structs, tags, paths = extract(likes, verbose)
    if len(X) < 3:
        raise SystemExit(f"Need at least 3 reference images in {likes} (found {len(X)}).")
    neg = None
    if dislikes.exists():
        if verbose:
            print(f"[taste] reading dislikes from {dislikes}")
        neg, _, _, _ = extract(dislikes, verbose)
    m = TasteModel.fit(X, structs, neg, sorted(set(t for t in tags if t)), name or Path(out).stem)
    m.save(out)
    # a sidecar with per-image features, handy for the LLM dataset builder
    side = Path(out).with_suffix(".images.jsonl")
    with side.open("w") as fh:
        for p, v, t in zip(paths, X, tags):
            fh.write(json.dumps({"path": p, "tag": t, "features": [round(float(a), 5) for a in v]}) + "\n")
    if verbose:
        print(f"[taste] {len(X)} likes, {0 if neg is None else len(neg)} dislikes, {len(structs)} palette structures -> {out}")
    return m
