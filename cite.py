"""Extractive citation stage (milestone 2.3).

The generator emits the top-1 *joined-fresh* chunk's indexed payload text as
the answer context (the answer "may only use joined-fresh spans"). With no
join (baseline), it emits the top-1 raw ANN hit — what a naive RAG system
does. If no fresh span exists, it abstains.

Metrics (ground truth = the source-of-truth row at eval time):
  stale_cite      emitted chunk fails the version join (stale or deleted)
  abstain         nothing emitted
  answer_correct  emitted text contains the current gold answer
                  (deleted-doc queries: correct iff abstain)

Language discipline: stale-citation rate is a GENERATION-layer metric over
emitted answers. It is not the same as retrieval-layer stale-hit@k.
"""
from __future__ import annotations


def _ground_truth_stale(rows, cid, meta):
    row = rows.get(cid)
    if row is None or row["deleted"]:
        return True
    return (meta["source_version"] != row["source_version"]
            or meta["content_hash"] != row["content_hash"])


def extractive_cite(rec, store, index, join_applied: bool, rows=None):
    """rec: per-query record from pipeline.run_queries.
    Returns {kind, emitted_cid, abstain, stale_cite, answer_correct,
    emitted_text}."""
    if rows is None:
        rows = {cid: store.get_chunk(cid) for cid in store.all_chunk_ids()}
    q = rec["query"]
    hits = rec["hits"]
    if join_applied:
        # hits carry (cid, score, meta, ok, action); only fresh spans allowed
        cands = [h for h in hits if h[3]]
    else:
        cands = [(cid, score, meta, True, "raw") for cid, score, meta in hits]
    if not cands:
        return {"kind": q["kind"], "emitted_cid": None, "abstain": True,
                "stale_cite": False,
                "answer_correct": q["kind"] == "deleted", "emitted_text": ""}
    cid, score, meta, _ok, _action = cands[0]
    text = index.payload.get(cid, "")
    stale = _ground_truth_stale(rows, cid, meta)
    if q["kind"] == "deleted":
        correct = False  # any emission on a deleted doc is wrong
    else:
        correct = (q["gold_answer"] is not None
                   and q["gold_answer"] in text and not stale)
    return {"kind": q["kind"], "emitted_cid": cid, "abstain": False,
            "stale_cite": stale, "answer_correct": correct,
            "emitted_text": text}


def summarize(cites):
    """Aggregate citation records into rates (overall + by query kind)."""
    n = len(cites)
    out = {"n": n,
           "stale_citation_rate": sum(c["stale_cite"] for c in cites) / n,
           "abstention_rate": sum(c["abstain"] for c in cites) / n,
           "answer_correct_rate": sum(c["answer_correct"] for c in cites) / n}
    by_kind = {}
    for c in cites:
        by_kind.setdefault(c["kind"], []).append(c)
    for kind, cs in by_kind.items():
        m = len(cs)
        by_kind[kind] = {
            "n": m,
            "stale_citation_rate": sum(x["stale_cite"] for x in cs) / m,
            "abstention_rate": sum(x["abstain"] for x in cs) / m,
            "answer_correct_rate": sum(x["answer_correct"] for x in cs) / m,
        }
    out["by_kind"] = by_kind
    return out
