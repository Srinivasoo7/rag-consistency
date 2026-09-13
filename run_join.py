"""Milestone 2: version-joined retriever + extractive citation stage.

For every scenario x join-config in {off, drop@0s, drop@5s, drop@60s,
flag@0s, repair@0s}:
  - retrieval metrics with the join applied (stale-hit@5, missed-fresh
    split, recall@5, p95 INCLUDING the join cost)
  - extractive citation: emit the top-1 joined-fresh span (top-1 raw ANN
    hit when the join is off); report stale-citation / abstention /
    answer-correct rates, overall and by query kind.

Writes data/join_results.json, data/join_before_after.md,
data/citation_before_after.md, data/delay_sla_curve.md.

Language discipline: stale-hit@5 is the RETRIEVAL-layer metric;
stale-citation rate is the GENERATION-layer metric over emitted answers.
They are different numbers; the paper's claim is the second.
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
from joiner import VersionJoiner
import metrics
import pipeline
import cite as cite_mod


# (policy, delta_s, overfetch); policy None = join off (naive RAG baseline)
JOIN_CONFIGS = [
    (None, None, 1),
    ("drop", 0, 3),
    ("drop", 5, 3),
    ("drop", 60, 3),
    ("flag", 0, 1),
    ("repair", 0, 3),
]

SINGLE_FAULTS = ["competent", "drop-10pct", "no-tombstone", "partial-2of3",
                 "crash-mid-batch", "all-faults"]
DELAY_SCENARIOS = ["delay-1s", "delay-30s", "delay-5m", "delay-1h"]


def _cfg_name(policy, delta):
    return "off" if policy is None else f"{policy}@d{delta}s"


def run_one(name, policy, delta, overfetch, embedder, backend, data_dir,
            n_docs, vec_cache):
    ctx = pipeline.prepare_scenario(name, embedder, backend, data_dir,
                                    n_docs, vec_cache)
    ctx["rows"] = ctx["store"].get_all()  # immutable query-phase snapshot
    joiner = VersionJoiner(ctx["store"], ctx["index"], rows=ctx["rows"])
    join_cfg = None if policy is None else {
        "joiner": joiner, "policy": policy, "delta": delta}
    recs = pipeline.run_queries(ctx, k=TOP_K,
                                overfetch=overfetch, join_cfg=join_cfg)
    # retrieval metrics on the FINAL (post-policy) hits; hits are 3-tuples
    # when the join is off, 5-tuples (cid, score, meta, ok, action) when on
    triples = [(r["query"],
                [(cid, s, m) for cid, s, m, *_ in r["hits"]],
                r["latency_ms"] / 1000.0) for r in recs]
    m = metrics.evaluate(triples, ctx["index"], ctx["store"], TOP_K,
                         denoms=ctx["denoms"], rows=ctx["rows"])
    # extractive citation on the FINAL hits
    cites = [cite_mod.extractive_cite(r, ctx["store"], ctx["index"],
                                      join_applied=policy is not None,
                                      rows=ctx["rows"])
             for r in recs]
    c = cite_mod.summarize(cites)
    ctx["store"].close()
    return {
        "scenario": name, "join": _cfg_name(policy, delta),
        "policy": policy, "delta_s": delta, "overfetch": overfetch,
        "embedder": embedder.backend,
        "retrieval": {
            "stale_hit_rate": m["stale_hit_rate"],
            "missed_fresh_rate": m["missed_fresh_rate"],
            "missed_fresh_coherent_rate": m["missed_fresh_coherent_rate"],
            "missed_fresh_staleindex_rate": m["missed_fresh_staleindex_rate"],
            "recall_at_k": m["recall_at_k"],
            "ndcg_at_k": m["ndcg_at_k"],
            "p50_latency_ms": m["p50_latency_ms"],
            "p95_latency_ms": m["p95_latency_ms"],
        },
        "citation": c,
        "join_info_totals": _sum_join_info(recs),
    }


def _sum_join_info(recs):
    tot = {"n_dropped": 0, "n_flagged": 0, "n_repaired": 0}
    for r in recs:
        ji = r["join_info"]
        if ji:
            for k in tot:
                tot[k] += ji[k]
    return tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default=",".join(SCENARIOS))
    ap.add_argument("--backend", default="auto",
                    choices=["auto", "sqlite", "postgres"])
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--docs", type=int, default=1000)
    ap.add_argument("--tag", default="",
                    help="suffix for output files, e.g. 'hash' -> "
                         "join_results_hash.json")
    args = ap.parse_args()

    os.makedirs(args.data_dir, exist_ok=True)
    embedder = Embedder()
    print(f"[join] embedder backend: {embedder.backend} (dim={embedder.dim})",
          flush=True)
    vec_cache: dict = {}
    names = [s for s in args.scenarios.split(",") if s in SCENARIOS]

    rows = []
    for name in names:
        for policy, delta, overfetch in JOIN_CONFIGS:
            cfg = _cfg_name(policy, delta)
            print(f"[join] {name} x {cfg} ...", flush=True)
            rows.append(run_one(name, policy, delta, overfetch, embedder,
                                args.backend, args.data_dir, args.docs,
                                vec_cache))

    suffix = f"_{args.tag}" if args.tag else ""
    path = os.path.join(args.data_dir, f"join_results{suffix}.json")
    with open(path, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"[join] wrote {path}")
    write_before_after(rows, args.data_dir, suffix)
    write_citation_table(rows, args.data_dir, suffix)
    write_delay_sla_curve(rows, args.data_dir, suffix)


def _row_for(rows, scenario, join):
    for r in rows:
        if r["scenario"] == scenario and r["join"] == join:
            return r
    return None


def write_before_after(rows, data_dir, suffix=""):
    """The paper's key figure: single-fault scenarios x join configs.
    Retrieval-layer stale-hit@5 before/after, with the recall/p95 tax."""
    cfgs = ["off", "drop@d5s", "drop@d60s", "repair@d0s", "flag@d0s"]
    lines = [
        "# Version-joined retriever: before/after (retrieval layer)",
        "",
        "> stale-hit@5 here is the RETRIEVAL-layer metric (fraction of top-5",
        "> hits failing the source-version join). The generation-layer",
        "> stale-citation rate is in citation_before_after.md. p95 includes",
        "> the join cost. `drop@d0s` is the extreme point (delta=0 demands a",
        "> zero-lag pipeline — unenforceable even by the competent worker);",
        "> the operating points are delta=5s and delta=60s.",
        "> `all-faults` is the explicitly-labeled upper bound per FAULT_MIX.md.",
        "",
        "| scenario | join | stale-hit@5 | missed-fresh (coherent \\| stale-idx) | "
        "recall@5 | p95 ms |",
        "|---|---|---|---|---|---|",
    ]
    for name in SINGLE_FAULTS:
        for cfg in cfgs:
            r = _row_for(rows, name, cfg)
            if not r:
                continue
            t = r["retrieval"]
            lines.append(
                f"| {name} | {cfg} | {t['stale_hit_rate']} | "
                f"{t['missed_fresh_coherent_rate']} \\| {t['missed_fresh_staleindex_rate']} | "
                f"{t['recall_at_k']} | {t['p95_latency_ms']} |")
    path = os.path.join(data_dir, f"join_before_after{suffix}.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[join] wrote {path}")


def write_citation_table(rows, data_dir, suffix=""):
    """Generation-layer metric: extractive stale-citation rate before/after."""
    cfgs = ["off", "drop@d5s", "drop@d60s", "repair@d0s", "flag@d0s"]
    lines = [
        "# Extractive stale-citation rate: before/after (generation layer)",
        "",
        "> The generator emits the top-1 joined-fresh span (top-1 raw ANN hit",
        "> when the join is off). stale-citation = emitted span fails the",
        "> source-version join (stale or deleted). This is NOT stale-hit@5.",
        "",
        "| scenario | join | stale-citation | abstention | answer-correct |",
        "|---|---|---|---|---|",
    ]
    for name in SINGLE_FAULTS:
        for cfg in cfgs:
            r = _row_for(rows, name, cfg)
            if not r:
                continue
            c = r["citation"]
            lines.append(
                f"| {name} | {cfg} | {c['stale_citation_rate']:.4f} | "
                f"{c['abstention_rate']:.4f} | {c['answer_correct_rate']:.4f} |")
    lines += ["", "## by query kind (join off vs drop@d5s)",
              "",
              "| scenario | join | kind | stale-citation | abstention | answer-correct |",
              "|---|---|---|---|---|---|"]
    for name in SINGLE_FAULTS:
        for cfg in ["off", "drop@d5s"]:
            r = _row_for(rows, name, cfg)
            if not r:
                continue
            for kind, b in r["citation"]["by_kind"].items():
                lines.append(
                    f"| {name} | {cfg} | {kind} | {b['stale_citation_rate']:.4f} | "
                    f"{b['abstention_rate']:.4f} | {b['answer_correct_rate']:.4f} |")
    path = os.path.join(data_dir, f"citation_before_after{suffix}.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[join] wrote {path}")


def write_delay_sla_curve(rows, data_dir, suffix=""):
    """Delay scenarios x SLA delta: the SLA is enforceable iff delta >= lag."""
    lines = [
        "# Delay scenarios x freshness SLA (the enforceability curve)",
        "",
        "> A freshness SLA delta is enforceable only when delta >= the",
        "> pipeline lag T. Below that, drop@delta removes coherent hits and",
        "> recall collapses — that collapse IS the measurement (the tax of",
        "> demanding an SLA your pipeline cannot meet).",
        "",
        "| scenario (T) | join | stale-hit@5 | recall@5 | p95 ms |",
        "|---|---|---|---|---|",
    ]
    for name in DELAY_SCENARIOS:
        for cfg in ["off", "drop@d0s", "drop@d5s", "drop@d60s"]:
            r = _row_for(rows, name, cfg)
            if not r:
                continue
            t = r["retrieval"]
            lines.append(f"| {name} | {cfg} | {t['stale_hit_rate']} | "
                         f"{t['recall_at_k']} | {t['p95_latency_ms']} |")
    path = os.path.join(data_dir, f"delay_sla_curve{suffix}.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[join] wrote {path}")


if __name__ == "__main__":
    main()
