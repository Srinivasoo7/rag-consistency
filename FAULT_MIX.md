# Fault-mix card

## all-faults (constructed stress composition — an upper bound, NOT a realistic mix)

`all-faults` composes four fault operators on the same mutation event stream
(edits+rewrites+deletes over 1000 docs x 3 chunks, committed to the source at
virtual t=60, drained by the worker at t=61), applied in this exact order
(`faults.py::SyncWorker.drain`, mode `"all_faults"`, worker rng seed 7):

1. **drop 10% of upserts** — each `upsert` event is discarded with p=0.10
   (seeded rng, so the dropped set is deterministic and identical across
   runs); deletes are unaffected by this operator.
2. **no tombstones** — all `delete` events are discarded; deleted chunks are
   never purged from the index (they linger as retrievable stale vectors).
3. **partial k=2/3** — per doc, only the first 2 of 3 chunk upserts
   (by chunk_idx) are kept; the third chunk's new version never reaches
   the index.
4. **crash at 50%** — the surviving event list is split in half; the first
   half is applied, the second half stays pending forever (the worker never
   recovers in this scenario).

Net effect on a 1000-doc corpus (300 updated+rewritten docs x 3 chunks):
roughly 10% of chunk upserts vanish silently, all deletes linger, one chunk
per updated doc keeps its old version, and half of everything that survived
operators 1–3 never gets applied at all.

## Language rule

Report numbers from this scenario only as "under this fault mix (defined in
FAULT_MIX.md)". Never "under a realistic fault mix", never as an incidence
estimate. The single-fault scenarios (drop-10pct, no-tombstone, partial-2of3,
crash-mid-batch) are the interpretable results; all-faults is the
explicitly-labeled upper bound of what the fault set can compose.

## Single-fault operators (for reference)

| scenario | operator |
|---|---|
| competent | no fault; worker drains every event at t=61 (models a healthy ~1s pipeline) |
| delay-T (T in 1s, 30s, 5m, 1h) | each change applied at updated_at + T (honest due time, virtual clock) |
| drop-10pct | p=0.10 of upserts silently dropped (seeded rng) |
| no-tombstone | delete events discarded; stale vectors linger |
| partial-2of3 | first 2 of 3 chunk upserts per doc kept |
| crash-mid-batch | first half of the batch applied; rest pending forever |
