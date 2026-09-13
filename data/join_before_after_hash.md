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
| competent | off | 0.0 | 0.4103 \| 0.0 | 0.5897 | 0.29 |
| competent | drop@d5s | 0.0 | 0.4103 \| 0.0 | 0.5897 | 0.23 |
| competent | drop@d60s | 0.0 | 0.4103 \| 0.0 | 0.5897 | 0.2 |
| competent | repair@d0s | 0.0 | 0.7267 \| 0.0 | 0.2733 | 0.21 |
| competent | flag@d0s | 0.0 | 0.4103 \| 0.0 | 0.5897 | 0.34 |
| drop-10pct | off | 0.0734 | 0.3869 \| 0.0206 | 0.5925 | 0.16 |
| drop-10pct | drop@d5s | 0.0 | 0.3789 \| 0.0605 | 0.5607 | 0.19 |
| drop-10pct | drop@d60s | 0.0 | 0.3789 \| 0.0605 | 0.5607 | 0.21 |
| drop-10pct | repair@d0s | 0.0 | 0.6711 \| 0.0169 | 0.312 | 0.4 |
| drop-10pct | flag@d0s | 0.0734 | 0.3869 \| 0.0206 | 0.5925 | 0.16 |
| no-tombstone | off | 0.2428 | 0.4401 \| 0.0 | 0.5599 | 0.21 |
| no-tombstone | drop@d5s | 0.0 | 0.4103 \| 0.0 | 0.5897 | 0.3 |
| no-tombstone | drop@d60s | 0.0 | 0.4103 \| 0.0 | 0.5897 | 0.27 |
| no-tombstone | repair@d0s | 0.0 | 0.7267 \| 0.0 | 0.2733 | 0.25 |
| no-tombstone | flag@d0s | 0.2428 | 0.4401 \| 0.0 | 0.5599 | 0.2 |
| partial-2of3 | off | 0.1214 | 0.3083 \| 0.102 | 0.5897 | 0.14 |
| partial-2of3 | drop@d5s | 0.0 | 0.2934 \| 0.1967 | 0.5099 | 0.21 |
| partial-2of3 | drop@d60s | 0.0 | 0.2934 \| 0.1967 | 0.5099 | 0.2 |
| partial-2of3 | repair@d0s | 0.0 | 0.5385 \| 0.0879 | 0.3736 | 0.59 |
| partial-2of3 | flag@d0s | 0.1214 | 0.3083 \| 0.102 | 0.5897 | 0.18 |
| crash-mid-batch | off | 0.3892 | 0.3015 \| 0.1088 | 0.5897 | 0.16 |
| crash-mid-batch | drop@d5s | 0.0 | 0.2765 \| 0.2971 | 0.4264 | 0.23 |
| crash-mid-batch | drop@d60s | 0.0 | 0.2765 \| 0.2971 | 0.4264 | 0.22 |
| crash-mid-batch | repair@d0s | 0.0 | 0.4454 \| 0.1012 | 0.4534 | 0.63 |
| crash-mid-batch | flag@d0s | 0.3892 | 0.3015 \| 0.1088 | 0.5897 | 0.19 |
| all-faults | off | 0.4922 | 0.2539 \| 0.1624 | 0.5836 | 0.26 |
| all-faults | drop@d5s | 0.0 | 0.216 \| 0.3974 | 0.3865 | 0.56 |
| all-faults | drop@d60s | 0.0 | 0.216 \| 0.3974 | 0.3865 | 0.31 |
| all-faults | repair@d0s | 0.0 | 0.3466 \| 0.1483 | 0.505 | 0.67 |
| all-faults | flag@d0s | 0.4922 | 0.2539 \| 0.1624 | 0.5836 | 0.19 |
