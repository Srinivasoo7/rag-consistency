"""Fault injector: the indexing pipeline worker with first-class faults.

Fault modes (per harness spec):
  none          competent worker: every change applied promptly
  delay         worker applies each change T virtual-seconds late
  drop          p fraction of upserts silently dropped (never applied)
  no_tombstone  deletes are not propagated (stale vectors linger)
  partial       only k of n chunks per doc get their upsert
  crash         worker dies after applying half the batch; rest stay pending
  all_faults    drop 10% + no tombstones + partial k=2/3 + crash at 50%
                (a constructed stress composition; see FAULT_MIX.md —
                an explicitly-labeled upper bound, not a "realistic mix")

All timing uses the virtual clock; nothing really sleeps.
"""
from __future__ import annotations

import random
from collections import defaultdict


class SyncWorker:
    def __init__(self, store, index, embedder, clock, seed: int = 7,
                 vec_cache: dict | None = None):
        self.store = store
        self.index = index
        self.embedder = embedder
        self.clock = clock
        self.rng = random.Random(seed)
        self._vec_cache: dict[str, object] = vec_cache if vec_cache is not None else {}

    # -- initial bulk load ------------------------------------------------
    def sync_initial(self):
        now = self.clock.now()
        ids = self.store.all_chunk_ids()
        texts, metas = [], []
        for cid in ids:
            row = self.store.get_chunk(cid)
            texts.append(row["text"])
            metas.append(row)
        vecs = self._embed(texts)
        for row, v in zip(metas, vecs):
            self._vec_cache[row["text"]] = v
            self.index.add(row["chunk_id"], v, row["doc_id"],
                           row["source_version"], row["content_hash"], now,
                           row["text"])

    def _embed(self, texts):
        missing = [t for t in texts if t not in self._vec_cache]
        if missing:
            vecs = self.embedder.encode(missing)
            for t, v in zip(missing, vecs):
                self._vec_cache[t] = v
        return [self._vec_cache[t] for t in texts]

    # -- incremental drain -------------------------------------------------
    def drain(self, events, fault: dict, now: float | None = None):
        """Apply pending (op, chunk_id) events under a fault mode.
        Returns (n_applied, pending_events)."""
        now = self.clock.now() if now is None else now
        mode = fault.get("mode", "none")
        due, pending = [], []

        for op, cid in events:
            row = self.store.get_chunk(cid)
            if row is None:
                continue
            not_before = row["updated_at"]
            if mode == "delay":
                not_before += fault.get("T", 0)
            (due if not_before <= now else pending).append(
                (op, cid, row) if not_before <= now else (op, cid))

        # fault filtering on the due set
        if mode == "drop":
            p = fault.get("p", 0.1)
            due = [(op, cid, row) for op, cid, row in due
                   if not (op == "upsert" and self.rng.random() < p)]
        elif mode == "no_tombstone":
            due = [(op, cid, row) for op, cid, row in due if op != "delete"]
        elif mode == "partial":
            k = fault.get("k", 2)
            by_doc = defaultdict(list)
            for item in due:
                if item[0] == "upsert":
                    by_doc[item[2]["doc_id"]].append(item)
            keep = set()
            for doc_items in by_doc.values():
                doc_items.sort(key=lambda x: x[2]["chunk_idx"])
                keep.update(id(x) for x in doc_items[:k])
            due = [x for x in due if x[0] != "upsert" or id(x) in keep]
        elif mode == "all_faults":
            # Constructed stress composition — exact operators in FAULT_MIX.md:
            # drop 10% of upserts, no tombstones, partial k=2/3, crash at 50%.
            due = [(op, cid, row) for op, cid, row in due
                   if not (op == "upsert" and self.rng.random() < 0.10)]
            due = [(op, cid, row) for op, cid, row in due if op != "delete"]
            by_doc = defaultdict(list)
            for item in due:
                by_doc[item[2]["doc_id"]].append(item)
            keep = set()
            for doc_items in by_doc.values():
                ups = sorted([x for x in doc_items if x[0] == "upsert"],
                             key=lambda x: x[2]["chunk_idx"])
                keep.update(id(x) for x in ups[:2])
                keep.update(id(x) for x in doc_items if x[0] != "upsert")
            due = [x for x in due if id(x) in keep]
            half = len(due) // 2
            pending += [(op, cid) for op, cid, _ in due[half:]]
            due = due[:half]
        elif mode == "crash":
            half = len(due) // 2
            pending += [(op, cid) for op, cid, _ in due[half:]]
            due = due[:half]

        # apply (timestamped at the effective apply time, not eval time,
        # so delay faults produce honest time-to-visible numbers)
        texts = [row["text"] for op, cid, row in due if op == "upsert"]
        vecs = self._embed(texts)
        vi = iter(vecs)
        for op, cid, row in due:
            apply_at = (row["updated_at"] + fault.get("T", 0)
                        if mode == "delay" else now)
            if op == "upsert":
                self.index.add(cid, next(vi), row["doc_id"],
                               row["source_version"], row["content_hash"],
                               apply_at, row["text"])
            else:  # delete -> tombstone
                self.index.remove(cid, purged_at=apply_at)
        return len(due), pending


SCENARIOS = {
    # name: (fault, eval_time_offset_after_mutations)
    "competent": ({"mode": "none"}, 1),
    "delay-1s": ({"mode": "delay", "T": 1}, 3600),
    "delay-30s": ({"mode": "delay", "T": 30}, 3600),
    "delay-5m": ({"mode": "delay", "T": 300}, 7200),
    "delay-1h": ({"mode": "delay", "T": 3600}, 7200),
    "drop-10pct": ({"mode": "drop", "p": 0.10}, 3600),
    "no-tombstone": ({"mode": "no_tombstone"}, 3600),
    "partial-2of3": ({"mode": "partial", "k": 2}, 3600),
    "crash-mid-batch": ({"mode": "crash"}, 3600),
    # all-faults is a *constructed* stress composition (see FAULT_MIX.md):
    # an explicitly-labeled upper bound, never "a realistic fault mix".
    "all-faults": ({"mode": "all_faults"}, 7200),
}
