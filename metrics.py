"""Retrieval metrics (milestone 1: no LLM, so no stale-citation rate yet).

Chunk-level (two-store coherence):
  time_to_visible_*   indexed_at(new version) - updated_at(source commit),
                      over upserted chunks that propagated
  never_visible       upserted chunks whose new version never reached the index
  time_to_purge_*     purged_at - deleted_at, over deletes that were tombstoned
  never_purged        deleted chunks still present in the index at eval

Query-level (top-k against the *current* source snapshot):
  stale_hit_rate      fraction of top-k hits with index.version < source.version
                      or source.deleted=1
  missed_fresh_rate   fraction of current-version gold chunks absent from top-k
  recall_at_k / ndcg  against current gold chunks (deleted docs skipped)
  p50/p95_latency_ms  wall-clock retrieval latency
"""
from __future__ import annotations

import math
import statistics


def _ndcg(hits, gold_ids, k):
    gold = set(gold_ids)
    dcg = sum(1.0 / math.log2(i + 2) for i, (cid, _, _) in enumerate(hits[:k])
              if cid in gold)
    ideal = min(len(gold), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal))
    return dcg / idcg if idcg else 0.0


def evaluate(results, index, store, k, denoms=None, provenance=None):
    """results: list of (query, hits, latency_s).
    denoms: dict of corpus/query denominators, passed through to output.
    provenance: dict {seed, embedder_backend, embedder_dim, faiss_index,
                     store_backend}, passed through to output.

    Language discipline (reviewer-mandated): stale_hit_rate is the
    RETRIEVAL-LAYER stale-hit@k. No answers are generated in milestone 1,
    so stale-hit != stale-citation rate.
    """
    # ---- chunk-level coherence -------------------------------------
    ttv, never_visible = [], 0
    ttp, never_purged = [], 0
    purge_at = {p["chunk_id"]: p["purged_at"] for p in index.purge_log}
    for cid in store.all_chunk_ids():
        row = store.get_chunk(cid)
        meta = index.meta.get(cid)
        if row["deleted"]:
            if cid in purge_at:
                ttp.append(purge_at[cid] - row["updated_at"])
            else:
                never_purged += 1
        elif row["source_version"] > 1:
            if meta and meta["source_version"] >= row["source_version"]:
                ttv.append(meta["indexed_at"] - row["updated_at"])
            else:
                never_visible += 1

    # ---- query-level -------------------------------------------------
    stale_hits = total_hits = 0
    missed = missed_coherent = missed_staleindex = 0.0
    recall_sum, ndcg_sum, n_scored = 0.0, 0.0, 0
    lat = []
    for q, hits, dt in results:
        lat.append(dt * 1000)
        for cid, _score, meta in hits:
            total_hits += 1
            row = store.get_chunk(cid)
            if row is None:
                stale_hits += 1  # in index, gone from source entirely
            elif row["deleted"] or row["source_version"] > meta["source_version"]:
                stale_hits += 1
        gold = [c for c in q["gold_chunk_ids"]
                if not (store.get_chunk(c) or {}).get("deleted")]
        if gold:
            got = {cid for cid, _, _ in hits}
            n_scored += 1
            recall_sum += len(set(gold) & got) / len(gold)
            ndcg_sum += _ndcg(hits, gold, k)
            for c in gold:
                if c in got:
                    continue
                missed += 1 / len(gold)
                # Split: is the miss caused by the fault (index stale for
                # this chunk) or by the embedder (index coherent but the
                # chunk wasn't retrieved)? Reviewer-mandated so embedder
                # weakness can't be misread as a coherence bug.
                row = store.get_chunk(c)
                meta = index.meta.get(c)
                coherent = (meta is not None
                            and meta["source_version"] == row["source_version"]
                            and meta["content_hash"] == row["content_hash"])
                if coherent:
                    missed_coherent += 1 / len(gold)
                else:
                    missed_staleindex += 1 / len(gold)

    def _stats(xs):
        return (round(statistics.mean(xs), 3) if xs else None,
                round(max(xs), 3) if xs else None, len(xs))

    ttv_mean, ttv_max, ttv_n = _stats(ttv)
    ttp_mean, ttp_max, ttp_n = _stats(ttp)
    lat_sorted = sorted(lat)
    p50 = lat_sorted[len(lat_sorted) // 2] if lat_sorted else None
    p95 = lat_sorted[int(len(lat_sorted) * 0.95)] if lat_sorted else None

    out = {
        "n_queries": len(results),
        "time_to_visible_mean_s": ttv_mean,
        "time_to_visible_max_s": ttv_max,
        "time_to_visible_n": ttv_n,
        "time_to_visible_cdf_s": sorted(round(x, 3) for x in ttv),
        "never_visible_chunks": never_visible,
        "time_to_purge_mean_s": ttp_mean,
        "time_to_purge_max_s": ttp_max,
        "time_to_purge_n": ttp_n,
        "time_to_purge_cdf_s": sorted(round(x, 3) for x in ttp),
        "never_purged_chunks": never_purged,
        # RETRIEVAL-LAYER stale-hit@k (no answers generated; != stale-citation).
        "stale_hit_rate": round(stale_hits / total_hits, 4) if total_hits else None,
        "missed_fresh_rate": round(missed / n_scored, 4) if n_scored else None,
        "missed_fresh_coherent_rate": (round(missed_coherent / n_scored, 4)
                                       if n_scored else None),
        "missed_fresh_staleindex_rate": (round(missed_staleindex / n_scored, 4)
                                          if n_scored else None),
        "recall_at_k": round(recall_sum / n_scored, 4) if n_scored else None,
        "ndcg_at_k": round(ndcg_sum / n_scored, 4) if n_scored else None,
        "p50_latency_ms": round(p50, 2) if p50 else None,
        "p95_latency_ms": round(p95, 2) if p95 else None,
    }
    if denoms:
        out["denominators"] = denoms
    if provenance:
        out["provenance"] = provenance
    return out
