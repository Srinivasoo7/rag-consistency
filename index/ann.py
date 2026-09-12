"""ANN index side (the eventually-consistent replica).

Each entry carries {doc_id, source_version, content_hash, indexed_at}
per the harness spec. Backed by faiss IndexIDMap2 over IndexFlatIP
(normalized vectors => cosine similarity). Tombstones are real removals;
purge events are logged so time-to-purge is measurable.
"""
from __future__ import annotations

import faiss
import numpy as np


class AnnIndex:
    def __init__(self, dim: int):
        self.dim = dim
        self._faiss = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))
        self.meta: dict[str, dict] = {}      # chunk_id -> {doc_id, source_version, content_hash, indexed_at}
        self.payload: dict[str, str] = {}    # chunk_id -> text AS INDEXED (stale payloads persist until upserted)
        self._id_of: dict[str, int] = {}
        self._chunk_of: dict[int, str] = {}
        self._next_id = 1
        self.purge_log: list[dict] = []      # {chunk_id, purged_at}

    def add(self, chunk_id: str, vector: np.ndarray, doc_id: str,
            source_version: int, chash: str, indexed_at: float, text: str = ""):
        vec = np.ascontiguousarray(vector.astype(np.float32)).reshape(1, -1)
        faiss.normalize_L2(vec)
        if chunk_id in self._id_of:
            self.remove(chunk_id, purged_at=indexed_at, silent=True)
        iid = self._next_id
        self._next_id += 1
        self._faiss.add_with_ids(vec, np.array([iid], dtype=np.int64))
        self._id_of[chunk_id] = iid
        self._chunk_of[iid] = chunk_id
        self.meta[chunk_id] = {
            "doc_id": doc_id,
            "source_version": source_version,
            "content_hash": chash,
            "indexed_at": indexed_at,
        }
        self.payload[chunk_id] = text

    def remove(self, chunk_id: str, purged_at: float, silent: bool = False):
        if chunk_id not in self._id_of:
            return
        iid = self._id_of.pop(chunk_id)
        self._chunk_of.pop(iid, None)
        self.meta.pop(chunk_id, None)
        self.payload.pop(chunk_id, None)
        self._faiss.remove_ids(
            faiss.IDSelectorBatch(np.array([iid], dtype=np.int64)))
        if not silent:
            self.purge_log.append({"chunk_id": chunk_id, "purged_at": purged_at})

    def search(self, query_vec: np.ndarray, k: int):
        q = np.ascontiguousarray(query_vec.astype(np.float32)).reshape(1, -1)
        faiss.normalize_L2(q)
        k = min(k, self._faiss.ntotal)
        if k <= 0:
            return []
        D, I = self._faiss.search(q, k)
        out = []
        for score, iid in zip(D[0], I[0]):
            if iid < 0:
                continue
            cid = self._chunk_of.get(int(iid))
            if cid is None:
                continue
            out.append((cid, float(score), self.meta[cid]))
        return out

    def __len__(self):
        return self._faiss.ntotal
