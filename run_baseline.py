"""Milestone 1 baseline (corrected): local split store + mutations + faults +
retrieval metrics. No LLM: stale-citation rate comes from run_join.py's
extractive stage. Reporting follows the reviewer corrections:
  - single-fault table leads; all-faults is a separate labeled upper bound
  - delay scenarios are reported via time-to-visible/purge CDFs, never as a
    "0.00 stale-hit" row implying delay is harmless
  - denominators + provenance in every JSON row
Usage: python3 run_baseline.py [--scenarios ...] [--backend auto|sqlite|postgres]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import TOP_K
from index.embedder import Embedder
from faults import SCENARIOS
import metrics
import pipeline


SINGLE_FAULTS = ["competent", "drop-10pct", "no-tombstone", "partial-2of3",
                 "crash-mid-batch"]
DELAY_SCENARIOS = ["delay-1s", "delay-30s", "delay-5m", "delay-1h"]
UPPER_BOUND = ["all-faults"]


def _provenance(embedder, store_backend):
    return {
        "seed": 20260912,
        "worker_seed": 7,
        "embedder_backend": embedder.backend,
        "embedder_dim": embedder.dim,
        "embedder_spec": ("all-MiniLM-L6-v2, frozen, CPU, normalize_embeddings=True"
                          if embedder.backend == "minilm" else
                          "HashEmbedder: unigrams+bigrams, md5 buckets, dim=384, "
                          "TF-IDF fitted on corpus, L2-normalized"),
        "faiss_index": "IndexIDMap2(IndexFlatIP) — exact search (flat)",
        "store_backend": store_backend,
    }


def _cdf_summary(xs):
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    q = lambda p: s[min(int(p * n), n - 1)]
    return {"n": n, "min": s[0], "p25": q(0.25), "p50": q(0.5),
            "p75": q(0.75), "max": s[-1]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default=",".join(SCENARIOS))
    ap.add_argument("--backend", default="auto",
                    choices=["auto", "sqlite", "postgres"])
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--docs", type=int, default=1000)
    ap.add_argument("--out", default="baseline_metrics.json")
    args = ap.parse_args()

    os.makedirs(args.data_dir, exist_ok=True)
    embedder = Embedder()
    print(f"[run] embedder backend: {embedder.backend} (dim={embedder.dim})",
          flush=True)
    vec_cache: dict = {}
    names = [s for s in args.scenarios.split(",") if s in SCENARIOS]

    rows = []
    for name in names:
        print(f"[run] scenario {name} ...", flush=True)
        ctx = pipeline.prepare_scenario(name, embedder, args.backend,
                                        args.data_dir, args.docs, vec_cache)
        recs = pipeline.run_queries(ctx, k=TOP_K)
        triples = [(r["query"], r["hits_raw"], r["latency_ms"] / 1000.0)
                   for r in recs]
        m = metrics.evaluate(
            triples, ctx["index"], ctx["store"], TOP_K,
            denoms=ctx["denoms"],
            provenance=_provenance(embedder, ctx["store"].backend))
        m["scenario"] = name
        m["fault"] = ctx["fault"].get("mode")
        m["applied"] = ctx["applied"]
        m["pending"] = ctx["pending"]
        m["ttv_cdf_summary"] = _cdf_summary(m.pop("time_to_visible_cdf_s"))
        m["ttp_cdf_summary"] = _cdf_summary(m.pop("time_to_purge_cdf_s"))
        rows.append(m)
        ctx["store"].close()
        print(f"[run]   stale_hit@5={m['stale_hit_rate']} "
              f"missed_fresh(coherent|staleidx)=({m['missed_fresh_coherent_rate']}|"
              f"{m['missed_fresh_staleindex_rate']}) "
              f"recall@{TOP_K}={m['recall_at_k']} p95={m['p95_latency_ms']}ms",
              flush=True)

    out_path = os.path.join(args.data_dir, args.out)
    with open(out_path, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"\n[run] wrote {out_path}")

    write_single_fault_table(rows, args.data_dir)
    write_delay_cdf_table(rows, args.data_dir)
    write_denominators(rows, args.data_dir)


def write_single_fault_table(rows, data_dir):
    """Single-fault scenarios lead. all-faults is a separate, explicitly
    labeled upper bound — never 'a realistic fault mix'."""
    lines = [
        "# Retrieval-layer stale-hit@5 — single-fault scenarios",
        "",
        "> Retrieval-layer metric only: fraction of top-5 hits whose indexed",
        "> version is older than the source version (or whose source row is",
        "> deleted). No answers are generated in this run, so this is NOT a",
        "> stale-citation rate. See run_join.py for the citation stage.",
        "> Fault mixes are described 'under this fault mix (defined in",
        "> FAULT_MIX.md)'.",
        "",
        "| scenario | stale-hit@5 | missed-fresh (coherent \\| stale-idx) | "
        "recall@5 | nDCG@5 | ttv mean (n) | never_vis | ttp mean (n) | "
        "never_purged | p95 ms |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    by_name = {r["scenario"]: r for r in rows}
    for name in SINGLE_FAULTS:
        if name not in by_name:
            continue
        m = by_name[name]
        lines.append(
            f"| {name} | {m['stale_hit_rate']} | "
            f"{m['missed_fresh_coherent_rate']} \\| {m['missed_fresh_staleindex_rate']} | "
            f"{m['recall_at_k']} | {m['ndcg_at_k']} | "
            f"{m['time_to_visible_mean_s']} ({m['time_to_visible_n']}) | "
            f"{m['never_visible_chunks']} | {m['time_to_purge_mean_s']} "
            f"({m['time_to_purge_n']}) | {m['never_purged_chunks']} | "
            f"{m['p95_latency_ms']} |")
    lines += [
        "",
        "## Upper bound (constructed stress composition, NOT a realistic mix)",
        "",
        "> `all-faults` = drop 10% of upserts + no tombstones + partial k=2/3",
        "> + crash at 50%, composed per FAULT_MIX.md. This is an",
        "> explicitly-labeled upper bound on what the fault set can do, not",
        "> an incidence estimate.",
        "",
        "| scenario | stale-hit@5 | missed-fresh (coherent \\| stale-idx) | "
        "recall@5 | nDCG@5 | p95 ms |",
        "|---|---|---|---|---|---|",
    ]
    for name in UPPER_BOUND:
        if name not in by_name:
            continue
        m = by_name[name]
        lines.append(
            f"| {name} | {m['stale_hit_rate']} | "
            f"{m['missed_fresh_coherent_rate']} \\| {m['missed_fresh_staleindex_rate']} | "
            f"{m['recall_at_k']} | {m['ndcg_at_k']} | {m['p95_latency_ms']} |")
    path = os.path.join(data_dir, "single_fault_table.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[run] wrote {path}")


def write_delay_cdf_table(rows, data_dir):
    """Delay faults are reported via time-to-visible / time-to-purge CDFs.
    A 0.00 eval-time stale-hit row would wrongly imply 'delay is harmless';
    the CDF is the result for these scenarios."""
    lines = [
        "# Delay faults — time-to-visible / time-to-purge CDFs",
        "",
        "> These scenarios converge by eval time (eval-time stale-hit@5 = 0),",
        "> so the CDF of the staleness window is the result, not the",
        "> eval-time row. All chunks converge: never_visible = 0.",
        "",
        "| scenario (T) | ttv: min / p25 / p50 / p75 / max (s), n | "
        "ttp: min / p25 / p50 / p75 / max (s), n | never_purged |",
        "|---|---|---|---|",
    ]
    by_name = {r["scenario"]: r for r in rows}
    for name in DELAY_SCENARIOS:
        if name not in by_name:
            continue
        m = by_name[name]
        def fmt(c):
            return (f"{c['min']}/{c['p25']}/{c['p50']}/{c['p75']}/{c['max']}, "
                    f"n={c['n']}" if c else "—")
        lines.append(f"| {name} | {fmt(m['ttv_cdf_summary'])} | "
                     f"{fmt(m['ttp_cdf_summary'])} | {m['never_purged_chunks']} |")
    path = os.path.join(data_dir, "delay_cdf_table.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[run] wrote {path}")


def write_denominators(rows, data_dir):
    m0 = rows[0]
    d = m0["denominators"]
    lines = [
        "# Denominators (identical across scenarios; fixed seeds)",
        "",
        f"- docs: {d['n_docs']} x {d['chunks_per_doc']} chunks = {d['n_chunks']} chunks",
        f"- updated docs (edit+rewrite): {d['n_docs_updated']}",
        f"- deleted docs: {d['n_docs_deleted']}",
        f"- noop docs: {d['n_docs_noop']}",
        f"- fraction of corpus mutated: {d['frac_corpus_mutated']}",
        f"- mutation mix: {d['mutation_mix']}",
        f"- queries: {d['n_queries']} ({d['query_targeting']})",
        f"- query kinds: {d['query_kinds']}",
        "",
        "## Provenance",
        "",
        f"- {m0['provenance']}",
    ]
    path = os.path.join(data_dir, "denominators.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[run] wrote {path}")


if __name__ == "__main__":
    main()
