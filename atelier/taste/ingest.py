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


def explode_pdf(pdf: Path, out: Path, min_side: int = 160) -> list[Path]:
    """Reference PDFs (moodboards, Pinterest exports, brand decks): pull out every
    embedded image; pages with no usable embedded image are rendered whole."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw

    out.mkdir(parents=True, exist_ok=True)
    done = sorted(out.glob("*.png"))
    if done:
        return done
    files = []
    doc = pdfium.PdfDocument(str(pdf))
    for i, page in enumerate(doc):
        found = 0
        for j, obj in enumerate(page.get_objects(filter=[raw.FPDF_PAGEOBJ_IMAGE], max_depth=3)):
            try:
                im = obj.get_bitmap(render=True).to_pil()
            except Exception:
                continue
            if min(im.size) >= min_side:
                f = out / f"p{i + 1:03d}-img{j + 1:02d}.png"
                im.convert("RGB").save(f)
                files.append(f)
                found += 1
        if not found:
            f = out / f"p{i + 1:03d}-page.png"
            page.render(scale=1.5).to_pil().convert("RGB").save(f)
            files.append(f)
    return files


def iter_images(root: Path):
    for p in sorted(root.rglob("*")):
        if not p.is_file() or ".pdf_cache" in p.parts:
            continue
        if p.suffix.lower() == ".pdf":
            yield from explode_pdf(p, p.parent / ".pdf_cache" / p.stem)
        elif p.suffix.lower() in EXTS:
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
        rel = [x for x in p.relative_to(root).parts if x != ".pdf_cache"]
        tags.append(rel[0] if len(rel) > 1 else "")
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
