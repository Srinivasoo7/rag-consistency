# Retrieval-layer stale-hit@5 — single-fault scenarios

> Retrieval-layer metric only: fraction of top-5 hits whose indexed
> version is older than the source version (or whose source row is
> deleted). No answers are generated in this run, so this is NOT a
> stale-citation rate. See run_join.py for the citation stage.
> Fault mixes are described 'under this fault mix (defined in
> FAULT_MIX.md)'.

| scenario | stale-hit@5 | missed-fresh (coherent \| stale-idx) | recall@5 | nDCG@5 | ttv mean (n) | never_vis | ttp mean (n) | never_purged | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| competent | 0.0 | 0.8206 \| 0.0 | 0.1794 | 0.2035 | 1.0 (1464) | 0 | 1.0 (519) | 0 | 0.16 |
| drop-10pct | 0.0504 | 0.769 \| 0.0512 | 0.1798 | 0.2053 | 1.0 (1314) | 150 | 1.0 (519) | 0 | 0.18 |
| no-tombstone | 0.2042 | 0.8315 \| 0.0 | 0.1685 | 0.1905 | 1.0 (1464) | 0 | None (0) | 519 | 0.2 |
| partial-2of3 | 0.0 | 0.6239 \| 0.1967 | 0.1794 | 0.2035 | 1.0 (976) | 488 | 1.0 (519) | 0 | 0.15 |
| crash-mid-batch | 0.3766 | 0.5792 \| 0.239 | 0.1818 | 0.2103 | 1.0 (727) | 737 | 1.0 (264) | 255 | 0.15 |

## Upper bound (constructed stress composition, NOT a realistic mix)

> `all-faults` = drop 10% of upserts + no tombstones + partial k=2/3
> + crash at 50%, composed per FAULT_MIX.md. This is an
> explicitly-labeled upper bound on what the fault set can do, not
> an incidence estimate.

| scenario | stale-hit@5 | missed-fresh (coherent \| stale-idx) | recall@5 | nDCG@5 | p95 ms |
|---|---|---|---|---|---|
| all-faults | 0.4492 | 0.4849 \| 0.3386 | 0.1765 | 0.2054 | 0.17 |
