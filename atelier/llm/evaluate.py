"""Score any brief parser on the held-out set: JSON validity, sector accuracy,
per-axis mean absolute error. Run it for `rules` first to get the baseline the
fine-tuned model has to beat."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from ..dna import AXES


def evaluate(val: Path, backend: str = "rules", limit: int = 200):
    from ..brief import call_llm, parse_rules, sanitize

    rows = [json.loads(line) for line in Path(val).read_text().splitlines()][:limit]
    errs, sector_ok, valid, dark_err = [], 0, 0, []
    t0 = time.time()
    for row in rows:
        brief = row["messages"][1]["content"].removeprefix("Brief: ")
        gold = json.loads(row["messages"][2]["content"])
        base = parse_rules(brief)
        if backend == "rules":
            pred = base
            valid += 1
        else:
            try:
                pred = sanitize(call_llm(brief, backend), base)
                valid += 1
            except Exception:
                pred = base
        errs.append([abs(pred.axes[a] - gold["axes"][a]) for a in AXES])
        dark_err.append(abs(pred.dark - gold["dark"]))
        sector_ok += pred.sector == gold["sector"]
    e = np.array(errs)
    n = len(rows)
    report = {"backend": backend, "n": n, "json_valid": round(valid / n, 3), "sector_acc": round(sector_ok / n, 3),
              "axis_mae": round(float(e.mean()), 4), "dark_mae": round(float(np.mean(dark_err)), 4),
              "per_axis_mae": {a: round(float(v), 3) for a, v in zip(AXES, e.mean(0))},
              "seconds": round(time.time() - t0, 1)}
    print(json.dumps(report, indent=2))
    return report
