# Version-joined retriever: before/after (retrieval layer)

> stale-hit@5 here is the RETRIEVAL-layer metric (fraction of top-5
> hits failing the source-version join). The generation-layer
> stale-citation rate is in citation_before_after.md. p95 includes
> the join cost. `drop@d0s` is the extreme point (delta=0 demands a
> zero-lag pipeline — unenforceable even by the competent worker);
> the operating points are delta=5s and delta=60s.
> `all-faults` is the explicitly-labeled upper bound per FAULT_MIX.md.

| scenario | join | stale-hit@5 | missed-fresh (coherent \| stale-idx) | recall@5 | p95 ms |
|---|---|---|---|---|---|
| competent | off | 0.0 | 0.8206 \| 0.0 | 0.1794 | 0.19 |
| competent | drop@d5s | 0.0 | 0.8206 \| 0.0 | 0.1794 | 0.35 |
| competent | drop@d60s | 0.0 | 0.8206 \| 0.0 | 0.1794 | 0.2 |
| competent | repair@d0s | 0.0 | 0.8996 \| 0.0 | 0.1004 | 0.22 |
| competent | flag@d0s | 0.0 | 0.8206 \| 0.0 | 0.1794 | 0.29 |
| drop-10pct | off | 0.0504 | 0.769 \| 0.0512 | 0.1798 | 0.19 |
| drop-10pct | drop@d5s | 0.0 | 0.765 \| 0.0605 | 0.1745 | 0.2 |
| drop-10pct | drop@d60s | 0.0 | 0.765 \| 0.0605 | 0.1745 | 0.21 |
| drop-10pct | repair@d0s | 0.0 | 0.8424 \| 0.048 | 0.1096 | 68.3 |
| drop-10pct | flag@d0s | 0.0504 | 0.769 \| 0.0512 | 0.1798 | 0.16 |
| no-tombstone | off | 0.2042 | 0.8315 \| 0.0 | 0.1685 | 0.19 |
| no-tombstone | drop@d5s | 0.0 | 0.8206 \| 0.0 | 0.1794 | 0.24 |
| no-tombstone | drop@d60s | 0.0 | 0.8206 \| 0.0 | 0.1794 | 0.21 |
| no-tombstone | repair@d0s | 0.0 | 0.9004 \| 0.0 | 0.0996 | 0.25 |
| no-tombstone | flag@d0s | 0.2042 | 0.8315 \| 0.0 | 0.1685 | 0.18 |
| partial-2of3 | off | 0.0 | 0.6239 \| 0.1967 | 0.1794 | 0.16 |
| partial-2of3 | drop@d5s | 0.0 | 0.6239 \| 0.1967 | 0.1794 | 0.58 |
| partial-2of3 | drop@d60s | 0.0 | 0.6239 \| 0.1967 | 0.1794 | 0.23 |
| partial-2of3 | repair@d0s | 0.0 | 0.7029 \| 0.1927 | 0.1044 | 4.92 |
| partial-2of3 | flag@d0s | 0.0 | 0.6239 \| 0.1967 | 0.1794 | 0.27 |
| crash-mid-batch | off | 0.3766 | 0.5792 \| 0.239 | 0.1818 | 0.32 |
| crash-mid-batch | drop@d5s | 0.0 | 0.5659 \| 0.2971 | 0.137 | 0.36 |
| crash-mid-batch | drop@d60s | 0.0 | 0.5659 \| 0.2971 | 0.137 | 0.35 |
| crash-mid-batch | repair@d0s | 0.0 | 0.6155 \| 0.2338 | 0.1507 | 113.18 |
| crash-mid-batch | flag@d0s | 0.3766 | 0.5792 \| 0.239 | 0.1818 | 0.45 |
| all-faults | off | 0.4492 | 0.4849 \| 0.3386 | 0.1765 | 0.21 |
| all-faults | drop@d5s | 0.0 | 0.468 \| 0.3974 | 0.1346 | 0.28 |
| all-faults | drop@d60s | 0.0 | 0.468 \| 0.3974 | 0.1346 | 0.29 |
| all-faults | repair@d0s | 0.0 | 0.5159 \| 0.3289 | 0.1552 | 112.83 |
| all-faults | flag@d0s | 0.4492 | 0.4849 \| 0.3386 | 0.1765 | 0.25 |
