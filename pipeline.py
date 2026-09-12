"""Shared scenario pipeline (milestone 2).

Builds the two-store world once per scenario — source-of-truth store,
ANN index, mutations, fault injection, query set — so the baseline,
version-joined retriever, and extractive-citation runs all measure the
*same* worlds. Deterministic given the seeds in common.py.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import N_DOCS, SEED, TOP_K, CHUNKS_PER_DOC, MUTATION_MIX, VirtualClock
from source.store import SourceStore
from index.ann import AnnIndex
from mutator import generate_corpus, pick_mutations, seed_source, apply_mutations
from faults import SyncWorker, SCENARIOS
from queries import build_queries


def compute_denominators(docs, mutations, queries):
    """Corpus/query denominators (reviewer-mandated). Scenario-independent
    given the fixed seeds, but recorded per run for the JSON."""
    n_upd = sum(1 for d in docs if mutations[d["doc_id"]][0] in ("edit", "rewrite"))
    n_del = sum(1 for d in docs if mutations[d["doc_id"]][0] == "delete")
    kinds = {}
    for q in queries:
        kinds[q["kind"]] = kinds.get(q["kind"], 0) + 1
    return {
        "n_docs": len(docs),
        "chunks_per_doc": CHUNKS_PER_DOC,
        "n_chunks": len(docs) * CHUNKS_PER_DOC,
        "n_docs_updated": n_upd,
        "n_docs_deleted": n_del,
        "n_docs_noop": len(docs) - n_upd - n_del,
        "frac_corpus_mutated": round((n_upd + n_del) / len(docs), 4),
        "mutation_mix": dict(MUTATION_MIX),
        "query_targeting": ("uniform-per-doc: exactly 1 query per doc; "
                            "kind=mutated (edit/rewrite, gold=new answer), "
                            "kind=deleted (gold=None), "
                            "kind=control (gold=original answer)"),
        "n_queries": len(queries),
        "query_kinds": kinds,
    }


def prepare_scenario(name, embedder, backend="auto", data_dir="data",
                     n_docs=N_DOCS, vec_cache=None):
    """Build one fault-injected world. Returns a ctx dict."""
    fault, eval_offset = SCENARIOS[name]
    clock = VirtualClock(0)
    store = SourceStore(backend=backend,
                        path=os.path.join(data_dir, f"source-{name}.db"))
    docs = generate_corpus(n_docs, SEED)
    mutations = pick_mutations(docs, SEED + 1)
    embedder.fit([c for d in docs for c in d["chunks"]])  # IDF for hash fallback

    seed_source(store, docs, clock)                    # t=0
    index = AnnIndex(embedder.dim)
    worker = SyncWorker(store, index, embedder, clock, vec_cache=vec_cache)
    worker.sync_initial()

    clock.set(60)                                     # t=60: source commits
    events = apply_mutations(store, docs, mutations, clock)

    # t=61: pipeline tick. Delay faults aren't due yet; they get a second
    # drain at their honest due time (updated_at + T) so time-to-visible
    # measures pipeline lag, not "when we bothered to run the worker".
    applied, pending = worker.drain(events, fault, now=61)
    if fault.get("mode") == "delay":
        a2, pending = worker.drain(pending, fault, now=60 + fault["T"])
        applied += a2

    eval_t = 60 + eval_offset  # virtual; queries run after everything settled
    clock.set(eval_t)

    queries = build_queries(docs, mutations)
    denoms = compute_denominators(docs, mutations, queries)
    return {
        "name": name, "fault": fault, "eval_offset": eval_offset,
        "store": store, "index": index, "queries": queries,
        "eval_t": eval_t, "applied": applied, "pending": len(pending),
        "denoms": denoms, "embedder": embedder, "clock": clock,
    }


def run_queries(ctx, k=TOP_K, overfetch=1, join_cfg=None):
    """Retrieve top-k (overfetch*k candidates when a drop-policy join needs
    backfill). join_cfg: None or {joiner, policy, delta}.
    Returns per-query records; per-query latency INCLUDES the join cost."""
    embedder = ctx["embedder"]
    index = ctx["index"]
    queries = ctx["queries"]
    eval_t = ctx["eval_t"]
    qvecs = embedder.encode([q["text"] for q in queries])
    out = []
    for q, qv in zip(queries, qvecs):
        t0 = time.perf_counter()
        raw = index.search(qv, k * overfetch)
        final, join_info = raw, None
        if join_cfg is not None:
            final, join_info = join_cfg["joiner"].apply(
                raw, k=k, eval_t=eval_t, delta=join_cfg["delta"],
                policy=join_cfg["policy"], embedder=embedder)
        dt = (time.perf_counter() - t0) * 1000.0
        out.append({"query": q, "hits_raw": raw, "hits": final,
                    "latency_ms": dt, "join_info": join_info})
    return out
