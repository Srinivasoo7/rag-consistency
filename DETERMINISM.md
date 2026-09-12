# Determinism artifact

Every number in `data/` is reproducible from a fresh shell via
`README.md` (same machine class; wall-clock latencies will vary slightly).

- **Corpus seed:** `SEED = 20260912` (`common.py`) — doc generation and
  mutation assignment (`pick_mutations` uses `SEED + 1`). Same 1000 docs,
  same mutation per doc, every run.
- **Worker/fault rng seed:** `7` (`faults.py::SyncWorker`) — the drop-10%
  operator discards the identical chunk set on every run.
- **Embedder:** recorded per run in each JSON row's `provenance` block.
  - `minilm`: `all-MiniLM-L6-v2`, frozen weights, CPU, `normalize_embeddings=True`
    (384-dim output).
  - `hash`: `HashEmbedder` — unigrams+bigrams, md5 bucket hash, dim=384,
    TF-IDF weights fitted once on the corpus (`fit`), L2-normalized.
    Deterministic (no rng).
- **ANN index:** `faiss.IndexIDMap2(faiss.IndexFlatIP)` — **exact** search
  (flat), not HNSW. Recorded per run as `provenance.faiss_index`. Flat makes
  the competent=0 control almost easy by construction; HNSW + upsert races
  are a declared later stack, not this milestone.
- **Source store:** `provenance.store_backend` — `postgres` (PostgreSQL 16,
  `ragc` db, TRUNCATEd per scenario) or `sqlite` fallback.
- **Clock:** all staleness windows are virtual seconds (`VirtualClock`);
  only retrieval latency is wall-clock.
- **Query set:** 1 query per doc, fixed order (`queries.py`); query vectors
  are encoded once per run.

Re-run check (milestone 1, TF-IDF): re-running `run_baseline.py --docs 1000`
reproduces every metric bit-for-bit except `p50/p95_latency_ms`.
