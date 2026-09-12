"""Compare milestone-1 suite across embedders (milestone 2.1).

Usage: python3 compare_embedders.py <hash_json> <minilm_json>
Writes data/embedder_comparison.md. The check that matters: cross-scenario
*deltas* (stale-hit@5 per fault vs competent) must not flip between
embedders. Absolute recall@5 is expected to be higher with MiniLM.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load(path):
    with open(path) as f:
        rows = json.load(f)
    return {r["scenario"]: r for r in rows}


def main():
    hash_rows = load(sys.argv[1])
    mini_rows = load(sys.argv[2])
    lines = [
        "# Embedder comparison: hashed TF-IDF vs all-MiniLM-L6-v2",
        "",
        "> Same 1k corpus, same faults, same seeds — only the embedder",
        "> differs. The claim under test: cross-scenario deltas",
        "> (stale-hit@5 per fault scenario) do not flip. Absolute recall@5",
        "> is expected to rise with MiniLM (better semantic matching).",
        "",
        "| scenario | stale-hit@5 (hash \\| minilm) | recall@5 (hash \\| minilm) | "
        "delta-flip? |",
        "|---|---|---|---|",
    ]
    flips = []
    for name in hash_rows:
        h, m = hash_rows[name], mini_rows[name]
        # delta vs competent within each embedder
        dh = h["stale_hit_rate"] - hash_rows["competent"]["stale_hit_rate"]
        dm = m["stale_hit_rate"] - mini_rows["competent"]["stale_hit_rate"]
        flip = "FLIP" if abs(dh - dm) > 0.05 else "ok"
        if flip == "FLIP":
            flips.append(name)
        lines.append(f"| {name} | {h['stale_hit_rate']} \\| {m['stale_hit_rate']} | "
                     f"{h['recall_at_k']} \\| {m['recall_at_k']} | {flip} |")
    lines += ["",
              f"**Result: {'NO flips' if not flips else 'FLIPS in: ' + ', '.join(flips)}**"]
    out = os.path.join("data", "embedder_comparison.md")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[compare] wrote {out}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
