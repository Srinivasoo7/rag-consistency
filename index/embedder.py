"""Embeddings: sentence-transformers (all-MiniLM-L6-v2, CPU) if available,
else a deterministic hashed bag-of-words fallback (pure numpy).

The fallback is weaker semantically but keeps the harness runnable offline;
RUNLOG records which one was used. Staleness metrics don't depend on
embedding quality, only on version coherence between the two stores.
"""
from __future__ import annotations

import hashlib
import re

import numpy as np

DIM = 384
_TOKEN = re.compile(r"[a-z0-9]+")


class HashEmbedder:
    """Deterministic hashed TF-IDF embedder (unigrams+bigrams), L2-normalized."""

    def __init__(self, dim: int = DIM):
        self.dim = dim
        self.idf = np.ones(dim, dtype=np.float64)

    @staticmethod
    def _grams(text: str):
        toks = _TOKEN.findall(text.lower())
        return toks + [a + "_" + b for a, b in zip(toks, toks[1:])]

    def _bucket(self, g: str) -> int:
        return int(hashlib.md5(g.encode()).hexdigest(), 16) % self.dim

    def fit(self, texts):
        """Compute IDF buckets over the corpus (call once before indexing)."""
        df = np.zeros(self.dim, dtype=np.float64)
        texts = list(texts)
        for t in texts:
            for b in {self._bucket(g) for g in self._grams(t)}:
                df[b] += 1.0
        n = max(len(texts), 1)
        self.idf = np.log((n + 1.0) / (df + 1.0)) + 1.0

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float64)
        for g in self._grams(text):
            v[self._bucket(g)] += 1.0
        w = np.log1p(v) * self.idf
        n = np.linalg.norm(w)
        return (w / n).astype(np.float32) if n > 0 else w.astype(np.float32)

    def encode(self, texts):
        if isinstance(texts, str):
            return self._vec(texts)
        return np.stack([self._vec(t) for t in texts])


class Embedder:
    def __init__(self):
        self.backend = "hash"
        self.dim = DIM
        self._st = None
        try:
            from sentence_transformers import SentenceTransformer
            self._st = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
            self.dim = self._st.get_sentence_embedding_dimension()
            self.backend = "minilm"
        except Exception as e:  # offline / no torch / download failed
            print(f"[embedder] sentence-transformers unavailable ({e}); "
                  f"using hashed fallback")
            self._hash = HashEmbedder(DIM)

    def encode(self, texts):
        if self._st is not None:
            v = self._st.encode(texts, normalize_embeddings=True,
                                show_progress_bar=False)
            return np.asarray(v, dtype=np.float32)
        return self._hash.encode(texts)

    def fit(self, texts):
        """Fit IDF statistics (hashed fallback only; no-op for MiniLM)."""
        if self._st is None:
            self._hash.fit(texts)
