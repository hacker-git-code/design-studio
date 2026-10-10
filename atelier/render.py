"""SVG -> raster via resvg (self-contained, no system deps)."""

from __future__ import annotations

import io
from pathlib import Path



def png_bytes(svg: str, width: int | None = None) -> bytes:
    import resvg_py

    # all text is outlined to paths, so skip font discovery (it dominates render time)
    kw = {"svg_string": svg, "skip_system_fonts": True}
    if width:
        kw["width"] = int(width)
    return bytes(resvg_py.svg_to_bytes(**{k: v for k, v in kw.items() if v is not None}))


def to_image(svg: str, width: int | None = None):
    from PIL import Image

    return Image.open(io.BytesIO(png_bytes(svg, width))).convert("RGBA")


def to_array(svg: str, width: int = 128, background=(255, 255, 255)):
    import numpy as np
    from PIL import Image

    im = to_image(svg, width)
    bg = Image.new("RGBA", im.size, background + (255,))
    bg.alpha_composite(im)
    return np.asarray(bg.convert("RGB"), dtype=np.float32) / 255.0


def save_png(svg: str, path: Path, width: int | None = None):
    Path(path).write_bytes(png_bytes(svg, width))


def contact_sheet(svgs: list[str], cols: int = 6, cell: int = 220, pad: int = 10, bg=(245, 244, 240), labels=None):
    from PIL import Image, ImageDraw

    rows = (len(svgs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (cell + pad) + pad, rows * (cell + pad) + pad), bg)
    draw = ImageDraw.Draw(sheet)
    for i, s in enumerate(svgs):
        im = to_image(s, cell)
        x, y = pad + (i % cols) * (cell + pad), pad + (i // cols) * (cell + pad)
        sheet.paste(im, (x, y), im)
        if labels:
            draw.text((x + 4, y + cell - 14), labels[i], fill=(120, 120, 120))
    return sheet


def _job(args):
    svg, path, width = args
    save_png(svg, Path(path), width)
    return path


def save_many(jobs: list[tuple[str, Path, int | None]], workers: int | None = None):
    """Render many SVGs to PNG in parallel processes (resvg holds the GIL)."""
    import os
    from concurrent.futures import ProcessPoolExecutor

    workers = workers or min(8, os.cpu_count() or 2)
    if workers <= 1 or len(jobs) < 4:
        for j in jobs:
            _job(j)
        return
    try:
        with ProcessPoolExecutor(workers) as ex:
            list(ex.map(_job, [(s, str(p), w) for s, p, w in jobs], chunksize=2))
    except Exception:  # restricted environments without multiprocessing
        for j in jobs:
            _job(j)
