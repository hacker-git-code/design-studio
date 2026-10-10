"""The taste model: a kernel density over design features of references you
like (and optionally ones you dislike), plus a bank of palette structures.

Training is pure numpy, CPU-only, seconds for thousands of images."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .features import FEATURE_NAMES


def _logsumexp(a, axis=-1):
    m = np.max(a, axis=axis, keepdims=True)
    return (m + np.log(np.exp(a - m).sum(axis=axis, keepdims=True))).squeeze(axis)


@dataclass
class TasteModel:
    X: np.ndarray                         # (n, d) liked features
    mu: np.ndarray
    sd: np.ndarray
    h: float
    structures: list = field(default_factory=list)
    neg: np.ndarray | None = None         # disliked features
    calib: np.ndarray | None = None       # sorted leave-one-out scores, for percentiles
    tags: list = field(default_factory=list)
    name: str = "taste"

    # ---------------------------------------------------------------- fit
    @staticmethod
    def fit(X, structures=None, neg=None, tags=None, name="taste") -> "TasteModel":
        X = np.asarray(X, dtype=np.float64)
        mu = X.mean(0)
        sd = X.std(0) + 1e-3
        n, d = X.shape
        h = max(0.35, n ** (-1.0 / (d + 4)) * 1.06)
        m = TasteModel(X, mu, sd, h, list(structures or []), None if neg is None or len(neg) == 0 else np.asarray(neg, float),
                       None, list(tags or []), name)
        Z = (X - mu) / sd
        loo = []
        for i in range(min(n, 400)):
            others = np.delete(Z, i, axis=0) if n > 1 else Z
            loo.append(m._logp(Z[i:i + 1], others)[0] - (m._logp(Z[i:i + 1], (m.neg - mu) / sd)[0] if m.neg is not None else 0))
        m.calib = np.sort(np.array(loo))
        return m

    def _logp(self, Z, ref):
        d2 = ((Z[:, None, :] - ref[None]) ** 2).sum(-1) / (self.h ** 2)
        return _logsumexp(-0.5 * d2, axis=1) - math.log(len(ref))

    # -------------------------------------------------------------- score
    def raw(self, x) -> np.ndarray:
        x = np.atleast_2d(np.asarray(x, dtype=np.float64))
        Z = (x - self.mu) / self.sd
        s = self._logp(Z, (self.X - self.mu) / self.sd)
        if self.neg is not None:
            s = s - self._logp(Z, (self.neg - self.mu) / self.sd)
        return s

    def score(self, x) -> np.ndarray:
        """0..1: where a candidate falls among your own references (0.5 = typical)."""
        r = self.raw(x)
        if self.calib is None or len(self.calib) == 0:
            return 1 / (1 + np.exp(-r))
        return np.searchsorted(self.calib, r) / len(self.calib)

    def explain(self, x) -> dict:
        """Which features pull a candidate away from your taste (z-scores vs refs)."""
        z = (np.asarray(x) - self.mu) / self.sd
        return {k: round(float(v), 2) for k, v in sorted(zip(FEATURE_NAMES, z), key=lambda kv: -abs(kv[1]))[:5]}

    def sample_structure(self, rng, dark: bool | None = None):
        pool = self.structures
        if dark is not None:
            pool = [s for s in pool if (s["paper"][0] < 0.5) == dark] or pool
        if not pool:
            return None
        return pool[int(rng.integers(len(pool)))]

    # ------------------------------------------------------------ persist
    def save(self, path):
        d = dict(name=self.name, features=list(FEATURE_NAMES), X=self.X.round(5).tolist(), mu=self.mu.tolist(),
                 sd=self.sd.tolist(), h=self.h, structures=self.structures, tags=self.tags,
                 neg=None if self.neg is None else self.neg.round(5).tolist(),
                 calib=None if self.calib is None else self.calib.round(5).tolist())
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(d))

    @staticmethod
    def load(path) -> "TasteModel":
        d = json.loads(Path(path).read_text())
        return TasteModel(np.array(d["X"]), np.array(d["mu"]), np.array(d["sd"]), d["h"], d.get("structures", []),
                          None if d.get("neg") is None else np.array(d["neg"]),
                          None if d.get("calib") is None else np.array(d["calib"]), d.get("tags", []), d.get("name", "taste"))
