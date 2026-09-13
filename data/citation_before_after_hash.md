# Extractive stale-citation rate: before/after (generation layer)

> The generator emits the top-1 joined-fresh span (top-1 raw ANN hit
> when the join is off). stale-citation = emitted span fails the
> source-version join (stale or deleted). This is NOT stale-hit@5.
> `stale | emitted` conditions on emitted answers only; it equals
> stale-citation when abstention is ~0 and diverges under flag.

| scenario | join | stale-citation | stale \| emitted | abstention | answer-correct |
|---|---|---|---|---|---|
| competent | off | 0.0000 | 0.0000 | 0.0000 | 0.4970 |
| competent | drop@d5s | 0.0000 | 0.0000 | 0.0000 | 0.4970 |
| competent | drop@d60s | 0.0000 | 0.0000 | 0.0000 | 0.4970 |
| competent | repair@d0s | 0.0000 | 0.0000 | 0.0000 | 0.3430 |
| competent | flag@d0s | 0.0000 | 0.0000 | 0.1020 | 0.3480 |
| drop-10pct | off | 0.0680 | 0.0680 | 0.0000 | 0.4770 |
| drop-10pct | drop@d5s | 0.0000 | 0.0000 | 0.0000 | 0.4870 |
| drop-10pct | drop@d60s | 0.0000 | 0.0000 | 0.0000 | 0.4870 |
| drop-10pct | repair@d0s | 0.0000 | 0.0000 | 0.0000 | 0.3630 |
| drop-10pct | flag@d0s | 0.0000 | 0.0000 | 0.1030 | 0.3470 |
| no-tombstone | off | 0.1970 | 0.1970 | 0.0000 | 0.4790 |
| no-tombstone | drop@d5s | 0.0000 | 0.0000 | 0.0000 | 0.4970 |
| no-tombstone | drop@d60s | 0.0000 | 0.0000 | 0.0000 | 0.4970 |
| no-tombstone | repair@d0s | 0.0000 | 0.0000 | 0.0170 | 0.3450 |
| no-tombstone | flag@d0s | 0.0000 | 0.0000 | 0.2240 | 0.3850 |
| partial-2of3 | off | 0.0950 | 0.0950 | 0.0000 | 0.4970 |
| partial-2of3 | drop@d5s | 0.0000 | 0.0000 | 0.0000 | 0.5240 |
| partial-2of3 | drop@d60s | 0.0000 | 0.0000 | 0.0000 | 0.5240 |
| partial-2of3 | repair@d0s | 0.0000 | 0.0000 | 0.0000 | 0.3190 |
| partial-2of3 | flag@d0s | 0.0000 | 0.0000 | 0.1020 | 0.3480 |
| crash-mid-batch | off | 0.3710 | 0.3710 | 0.0000 | 0.3690 |
| crash-mid-batch | drop@d5s | 0.0000 | 0.0000 | 0.0000 | 0.4250 |
| crash-mid-batch | drop@d60s | 0.0000 | 0.0000 | 0.0000 | 0.4250 |
| crash-mid-batch | repair@d0s | 0.0000 | 0.0000 | 0.0000 | 0.4790 |
| crash-mid-batch | flag@d0s | 0.0000 | 0.0000 | 0.1960 | 0.3640 |
| all-faults | off | 0.4600 | 0.4600 | 0.0000 | 0.3590 |
| all-faults | drop@d5s | 0.0000 | 0.0000 | 0.0070 | 0.4290 |
| all-faults | drop@d60s | 0.0000 | 0.0000 | 0.0070 | 0.4290 |
| all-faults | repair@d0s | 0.0000 | 0.0000 | 0.0000 | 0.4810 |
| all-faults | flag@d0s | 0.0000 | 0.0000 | 0.2370 | 0.3840 |

## by query kind (join off vs drop@d5s)

| scenario | join | kind | stale-citation | stale \| emitted | abstention | answer-correct |
|---|---|---|---|---|---|---|
| competent | off | mutated | 0.0000 | 0.0000 | 0.0000 | 0.5020 |
| competent | off | control | 0.0000 | 0.0000 | 0.0000 | 0.7434 |
| competent | off | deleted | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| competent | drop@d5s | mutated | 0.0000 | 0.0000 | 0.0000 | 0.5020 |
| competent | drop@d5s | control | 0.0000 | 0.0000 | 0.0000 | 0.7434 |
| competent | drop@d5s | deleted | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| drop-10pct | off | mutated | 0.1086 | 0.1086 | 0.0000 | 0.4611 |
| drop-10pct | off | control | 0.0000 | 0.0000 | 0.0000 | 0.7434 |
| drop-10pct | off | deleted | 0.0867 | 0.0867 | 0.0000 | 0.0000 |
| drop-10pct | drop@d5s | mutated | 0.0000 | 0.0000 | 0.0000 | 0.4816 |
| drop-10pct | drop@d5s | control | 0.0000 | 0.0000 | 0.0000 | 0.7434 |
| drop-10pct | drop@d5s | deleted | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| no-tombstone | off | mutated | 0.0676 | 0.0676 | 0.0000 | 0.4816 |
| no-tombstone | off | control | 0.0354 | 0.0354 | 0.0000 | 0.7198 |
| no-tombstone | off | deleted | 0.8786 | 0.8786 | 0.0000 | 0.0000 |
| no-tombstone | drop@d5s | mutated | 0.0000 | 0.0000 | 0.0000 | 0.5020 |
| no-tombstone | drop@d5s | control | 0.0000 | 0.0000 | 0.0000 | 0.7434 |
| no-tombstone | drop@d5s | deleted | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| partial-2of3 | off | mutated | 0.1475 | 0.1475 | 0.0000 | 0.5020 |
| partial-2of3 | off | control | 0.0147 | 0.0147 | 0.0000 | 0.7434 |
| partial-2of3 | off | deleted | 0.1040 | 0.1040 | 0.0000 | 0.0000 |
| partial-2of3 | drop@d5s | mutated | 0.0000 | 0.0000 | 0.0000 | 0.5533 |
| partial-2of3 | drop@d5s | control | 0.0000 | 0.0000 | 0.0000 | 0.7493 |
| partial-2of3 | drop@d5s | deleted | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| crash-mid-batch | off | mutated | 0.5041 | 0.5041 | 0.0000 | 0.2520 |
| crash-mid-batch | off | control | 0.0442 | 0.0442 | 0.0000 | 0.7257 |
| crash-mid-batch | off | deleted | 0.6358 | 0.6358 | 0.0000 | 0.0000 |
| crash-mid-batch | drop@d5s | mutated | 0.0000 | 0.0000 | 0.0000 | 0.3463 |
| crash-mid-batch | drop@d5s | control | 0.0000 | 0.0000 | 0.0000 | 0.7552 |
| crash-mid-batch | drop@d5s | deleted | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| all-faults | off | mutated | 0.5820 | 0.5820 | 0.0000 | 0.2377 |
| all-faults | off | control | 0.0560 | 0.0560 | 0.0000 | 0.7168 |
| all-faults | off | deleted | 0.9075 | 0.9075 | 0.0000 | 0.0000 |
| all-faults | drop@d5s | mutated | 0.0000 | 0.0000 | 0.0143 | 0.3545 |
| all-faults | drop@d5s | control | 0.0000 | 0.0000 | 0.0000 | 0.7552 |
| all-faults | drop@d5s | deleted | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
