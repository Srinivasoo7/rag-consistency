"""Version-joined retriever (milestone 2): post-retrieval coherence join.

For each ANN hit, join chunk_id back to the source-of-truth row on
(source_version, content_hash, deleted). Freshness SLA delta: a hit passes
iff it is version-coherent AND its pipeline lag
(indexed_at - source.updated_at) is within delta.

Delta is a bound on *pipeline lag*, not on time-since-indexing: an
unchanged chunk has lag 0 and always passes. delta=0 therefore demands a
zero-lag pipeline — unenforceable even by the competent worker (1s tick) —
and is reported as the extreme point of the curve, not the headline.

Policies on divergence (stale version / deleted / lag > delta):
  drop    remove the hit; caller over-retrieves (k*overfetch) then truncates
  flag    keep the hit, annotated ok=False (the citation stage must skip it)
  repair  re-fetch + re-embed the current source text on the read path;
          the hit becomes fresh. Repair fires only on version-divergence
          (there is newer text to fetch); coherent-but-laggy hits already
          carry current content, so they are dropped/flagged like any other
          SLA violation. Deleted/missing hits are always dropped
          (flag annotates instead of dropping).
"""
from __future__ import annotations


class VersionJoiner:
    def __init__(self, store, index):
        self.store = store
        self.index = index

    def check(self, chunk_id, meta, delta):
        """Ground-truth coherence check. Returns (ok, reason)."""
        row = self.store.get_chunk(chunk_id)
        if row is None:
            return False, "missing-in-source"
        if row["deleted"]:
            return False, "source-deleted"
        if meta is None:
            return False, "not-indexed"
        if (meta["source_version"] != row["source_version"]
                or meta["content_hash"] != row["content_hash"]):
            return False, "version-diverged"
        lag = meta["indexed_at"] - row["updated_at"]
        if lag > delta:
            return False, f"lag-{lag:.1f}s>delta-{delta}s"
        return True, "ok"

    def apply(self, hits, k, delta, policy, embedder=None):
        """hits: [(cid, score, meta)] from ANN. Returns (final, info).
        final entries: (cid, score, meta, ok, action); truncated to k
        (except flag, which keeps the candidate list for the citation stage)."""
        checked = []
        for cid, score, meta in hits:
            ok, reason = self.check(cid, meta, delta)
            checked.append({"cid": cid, "score": score, "meta": meta,
                            "ok": ok, "reason": reason})
        n_dropped = n_flagged = n_repaired = 0
        if policy == "repair":
            assert embedder is not None, "repair needs an embedder"
            repairable = [c for c in checked
                          if not c["ok"] and c["reason"] == "version-diverged"]
            rows = [self.store.get_chunk(c["cid"]) for c in repairable]
            if rows:
                # Read-path re-embed cost lives inside the timed region;
                # the vectors are unused downstream (no re-search).
                embedder.encode([r["text"] for r in rows])
            for c, row in zip(repairable, rows):
                self.index.payload[c["cid"]] = row["text"]
                c["meta"] = {
                    "doc_id": row["doc_id"],
                    "source_version": row["source_version"],
                    "content_hash": row["content_hash"],
                    "indexed_at": self.index.meta[c["cid"]]["indexed_at"],
                }
                c["ok"] = True
                c["reason"] = "repaired:version-diverged"
                n_repaired += 1
        out = []
        for c in checked:
            if not c["ok"]:
                if policy == "drop" or policy == "repair":
                    n_dropped += 1
                    continue
                elif policy == "flag":
                    n_flagged += 1
                    out.append((c["cid"], c["score"], c["meta"], False,
                                "flagged:" + c["reason"]))
                    continue
                else:
                    raise ValueError(f"unknown policy {policy}")
            action = "pass" if c["reason"] == "ok" else c["reason"]
            out.append((c["cid"], c["score"], c["meta"], True, action))
        if policy != "flag":
            # drop/repair: truncate to k after backfill. flag keeps the full
            # candidate list; the citation stage filters flagged hits.
            out = out[:k]
        info = {"n_dropped": n_dropped, "n_flagged": n_flagged,
                "n_repaired": n_repaired, "policy": policy, "delta_s": delta}
        return out, info
