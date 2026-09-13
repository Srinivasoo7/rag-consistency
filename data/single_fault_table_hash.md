# Retrieval-layer stale-hit@5 — single-fault scenarios

> Retrieval-layer metric only: fraction of top-5 hits whose indexed
> version is older than the source version (or whose source row is
> deleted). No answers are generated in this run, so this is NOT a
> stale-citation rate. See run_join.py for the citation stage.
> Fault mixes are described 'under this fault mix (defined in
> FAULT_MIX.md)'.

| scenario | stale-hit@5 | missed-fresh (coherent \| stale-idx) | recall@5 | nDCG@5 | ttv mean (n) | never_vis | ttp mean (n) | never_purged | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| competent | 0.0 | 0.4103 \| 0.0 | 0.5897 | 0.6131 | 1.0 (1464) | 0 | 1.0 (519) | 0 | 1.05 |
| drop-10pct | 0.0734 | 0.3869 \| 0.0206 | 0.5925 | 0.6185 | 1.0 (1314) | 150 | 1.0 (519) | 0 | 0.17 |
| no-tombstone | 0.2428 | 0.4401 \| 0.0 | 0.5599 | 0.5822 | 1.0 (1464) | 0 | None (0) | 519 | 0.19 |
| partial-2of3 | 0.1214 | 0.3083 \| 0.102 | 0.5897 | 0.6131 | 1.0 (976) | 488 | 1.0 (519) | 0 | 0.17 |
| crash-mid-batch | 0.3892 | 0.3015 \| 0.1088 | 0.5897 | 0.6178 | 1.0 (727) | 737 | 1.0 (264) | 255 | 0.15 |

## Upper bound (constructed stress composition, NOT a realistic mix)

> `all-faults` = drop 10% of upserts + no tombstones + partial k=2/3
> + crash at 50%, composed per FAULT_MIX.md. This is an
> explicitly-labeled upper bound on what the fault set can do, not
> an incidence estimate.

| scenario | stale-hit@5 | missed-fresh (coherent \| stale-idx) | recall@5 | nDCG@5 | p95 ms |
|---|---|---|---|---|---|
| all-faults | 0.4922 | 0.2539 \| 0.1624 | 0.5836 | 0.6124 | 3.92 |
