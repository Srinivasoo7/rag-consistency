"""Shared primitives: virtual clock, hashing, config."""
from __future__ import annotations

import hashlib


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class VirtualClock:
    """Deterministic virtual-time clock. All staleness windows are measured
    in virtual seconds so fault scenarios with T=1h delays don't require
    real waiting. Wall-clock is used only for retrieval latency."""

    def __init__(self, t: float = 0.0):
        self.t = float(t)

    def now(self) -> float:
        return self.t

    def advance(self, dt: float) -> float:
        self.t += dt
        return self.t

    def set(self, t: float) -> float:
        self.t = float(t)
        return self.t


# Mutation mix for the 1k-doc baseline corpus.
MUTATION_MIX = {
    "edit": 0.30,      # in-place fact edit, version bump
    "rewrite": 0.20,   # superseding rewrite, version bump
    "delete": 0.15,    # source delete (tombstone expected)
    "noop": 0.35,      # control: untouched
}

N_DOCS = 1000
CHUNKS_PER_DOC = 3
TOP_K = 5
SEED = 20260912
