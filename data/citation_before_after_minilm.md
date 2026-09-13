# Extractive stale-citation rate: before/after (generation layer)

> The generator emits the top-1 joined-fresh span (top-1 raw ANN hit
> when the join is off). stale-citation = emitted span fails the
> source-version join (stale or deleted). This is NOT stale-hit@5.
> `stale | emitted` conditions on emitted answers only; it equals
> stale-citation when abstention is ~0 and diverges under flag.

| scenario | join | stale-citation | stale \| emitted | abstention | answer-correct |
|---|---|---|---|---|---|
| competent | off | 0.0000 | 0.0000 | 0.0000 | 0.3550 |
| competent | drop@d5s | 0.0000 | 0.0000 | 0.0000 | 0.3550 |
| competent | drop@d60s | 0.0000 | 0.0000 | 0.0000 | 0.3550 |
| competent | repair@d0s | 0.0000 | 0.0000 | 0.0000 | 0.2920 |
| competent | flag@d0s | 0.0000 | 0.0000 | 0.0490 | 0.2910 |
| drop-10pct | off | 0.0450 | 0.0450 | 0.0000 | 0.3430 |
| drop-10pct | drop@d5s | 0.0000 | 0.0000 | 0.0000 | 0.3470 |
| drop-10pct | drop@d60s | 0.0000 | 0.0000 | 0.0000 | 0.3470 |
| drop-10pct | repair@d0s | 0.0000 | 0.0000 | 0.0000 | 0.3150 |
| drop-10pct | flag@d0s | 0.0000 | 0.0000 | 0.0500 | 0.2880 |
| no-tombstone | off | 0.2460 | 0.2460 | 0.0000 | 0.3140 |
| no-tombstone | drop@d5s | 0.0000 | 0.0000 | 0.0000 | 0.3550 |
| no-tombstone | drop@d60s | 0.0000 | 0.0000 | 0.0000 | 0.3550 |
| no-tombstone | repair@d0s | 0.0000 | 0.0000 | 0.0000 | 0.2920 |
| no-tombstone | flag@d0s | 0.0000 | 0.0000 | 0.1160 | 0.2990 |
| partial-2of3 | off | 0.0000 | 0.0000 | 0.0000 | 0.3550 |
| partial-2of3 | drop@d5s | 0.0000 | 0.0000 | 0.0000 | 0.3550 |
| partial-2of3 | drop@d60s | 0.0000 | 0.0000 | 0.0000 | 0.3550 |
| partial-2of3 | repair@d0s | 0.0000 | 0.0000 | 0.0000 | 0.2920 |
| partial-2of3 | flag@d0s | 0.0000 | 0.0000 | 0.0490 | 0.2910 |
| crash-mid-batch | off | 0.3340 | 0.3340 | 0.0000 | 0.2550 |
| crash-mid-batch | drop@d5s | 0.0000 | 0.0000 | 0.0000 | 0.3250 |
| crash-mid-batch | drop@d60s | 0.0000 | 0.0000 | 0.0000 | 0.3250 |
| crash-mid-batch | repair@d0s | 0.0000 | 0.0000 | 0.0000 | 0.3830 |
| crash-mid-batch | flag@d0s | 0.0000 | 0.0000 | 0.1250 | 0.2880 |
| all-faults | off | 0.4700 | 0.4700 | 0.0000 | 0.2290 |
| all-faults | drop@d5s | 0.0000 | 0.0000 | 0.0000 | 0.3230 |
| all-faults | drop@d60s | 0.0000 | 0.0000 | 0.0000 | 0.3230 |
| all-faults | repair@d0s | 0.0000 | 0.0000 | 0.0000 | 0.3860 |
| all-faults | flag@d0s | 0.0000 | 0.0000 | 0.1500 | 0.2940 |

## by query kind (join off vs drop@d5s)

| scenario | join | kind | stale-citation | stale \| emitted | abstention | answer-correct |
|---|---|---|---|---|---|---|
| competent | off | mutated | 0.0000 | 0.0000 | 0.0000 | 0.4201 |
| competent | off | control | 0.0000 | 0.0000 | 0.0000 | 0.4425 |
| competent | off | deleted | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| competent | drop@d5s | mutated | 0.0000 | 0.0000 | 0.0000 | 0.4201 |
| competent | drop@d5s | control | 0.0000 | 0.0000 | 0.0000 | 0.4425 |
| competent | drop@d5s | deleted | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| drop-10pct | off | mutated | 0.0635 | 0.0635 | 0.0000 | 0.3975 |
| drop-10pct | off | control | 0.0147 | 0.0147 | 0.0000 | 0.4395 |
| drop-10pct | off | deleted | 0.0520 | 0.0520 | 0.0000 | 0.0000 |
| drop-10pct | drop@d5s | mutated | 0.0000 | 0.0000 | 0.0000 | 0.4037 |
| drop-10pct | drop@d5s | control | 0.0000 | 0.0000 | 0.0000 | 0.4425 |
| drop-10pct | drop@d5s | deleted | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| no-tombstone | off | mutated | 0.1926 | 0.1926 | 0.0000 | 0.3709 |
| no-tombstone | off | control | 0.1947 | 0.1947 | 0.0000 | 0.3923 |
| no-tombstone | off | deleted | 0.4971 | 0.4971 | 0.0000 | 0.0000 |
| no-tombstone | drop@d5s | mutated | 0.0000 | 0.0000 | 0.0000 | 0.4201 |
| no-tombstone | drop@d5s | control | 0.0000 | 0.0000 | 0.0000 | 0.4425 |
| no-tombstone | drop@d5s | deleted | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| partial-2of3 | off | mutated | 0.0000 | 0.0000 | 0.0000 | 0.4201 |
| partial-2of3 | off | control | 0.0000 | 0.0000 | 0.0000 | 0.4425 |
| partial-2of3 | off | deleted | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| partial-2of3 | drop@d5s | mutated | 0.0000 | 0.0000 | 0.0000 | 0.4201 |
| partial-2of3 | drop@d5s | control | 0.0000 | 0.0000 | 0.0000 | 0.4425 |
| partial-2of3 | drop@d5s | deleted | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| crash-mid-batch | off | mutated | 0.3975 | 0.3975 | 0.0000 | 0.2418 |
| crash-mid-batch | off | control | 0.2212 | 0.2212 | 0.0000 | 0.4041 |
| crash-mid-batch | off | deleted | 0.3757 | 0.3757 | 0.0000 | 0.0000 |
| crash-mid-batch | drop@d5s | mutated | 0.0000 | 0.0000 | 0.0000 | 0.3299 |
| crash-mid-batch | drop@d5s | control | 0.0000 | 0.0000 | 0.0000 | 0.4838 |
| crash-mid-batch | drop@d5s | deleted | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| all-faults | off | mutated | 0.5164 | 0.5164 | 0.0000 | 0.2070 |
| all-faults | off | control | 0.3186 | 0.3186 | 0.0000 | 0.3776 |
| all-faults | off | deleted | 0.6358 | 0.6358 | 0.0000 | 0.0000 |
| all-faults | drop@d5s | mutated | 0.0000 | 0.0000 | 0.0000 | 0.3258 |
| all-faults | drop@d5s | control | 0.0000 | 0.0000 | 0.0000 | 0.4838 |
| all-faults | drop@d5s | deleted | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
