# RUNLOG — environment substitutions and decisions

## 2026-09-12: initial build (milestone 1)

### Source-of-truth store: PostgreSQL 16 (no substitution needed)
- `sudo apt-get install -y postgresql` succeeded (one mirror failed, install
  completed anyway). Cluster 16/main started on :5432, database `ragc` created.
- `SourceStore` auto-detects Postgres via `RAGC_PG_DSN`; falls back to SQLite.
- Baseline run used Postgres. SQLite path is tested and works (smoke test).

### Embeddings: hashed bag-of-words fallback (SUBSTITUTION)
- `pip install sentence-transformers` failed twice: the torch wheel download
  breaks through this network (proxy resets on large files; same flakiness
  hit one apt mirror).
- Per the task spec, fell back to the deterministic hashed unigram/bigram
  embedder (`index/embedder.py::HashEmbedder`, dim=384, L2-normalized).
- Impact: absolute recall@k/nDCG are lower than MiniLM would give, but every
  scenario uses the same embedder, so cross-scenario *deltas* (the thing the
  paper claims) are unaffected. Staleness/coherence metrics don't depend on
  embedding quality at all. Re-run with `pip install sentence-transformers`
  on a better network to get publication-grade recall numbers.

### Python env: project venv (PEP 668)
- System pip refuses installs (`externally-managed-environment`), so the
  harness uses `~/workspace/rag-consistency/.venv` (faiss-cpu 1.15.0,
  psycopg[binary], numpy 1.26.4).

### Timing model
- All staleness windows use a virtual clock; fault delays (1s–1h) are
  simulated, never slept. Retrieval latency (p50/p95) is real wall-clock.
- "Competent" pipeline applies changes at t=61 (1s after source commit),
  so time-to-visible ≈ 1s there — it models a healthy ~1s pipeline, not
  zero.
- Delay faults: changes are timestamped at their honest due time
  (`updated_at + T`), not at eval time.

### Scope discipline (milestone 1)
- Built: local split store + mutation generator + retrieval metrics on 1k docs.
- NOT built (per spec): LLM wiring / stale-citation rate, version-joined
  retriever mechanism. Those are phase 2.
- `time_to_visible` is index-level (new version retrievable), not
  "first appears in top-k of a live query stream" — the index only changes
  at drain events, so the two coincide at eval time. Noted for the paper's
  methods section.

### Corpus fixes during build (both caught by measurement, not by reading)
- Entity names are unique per doc (`{base}-{i:04d}`). First cut reused 5
  names per template, making questions genuinely ambiguous (~33 docs per
  name) — recall measured ambiguity, not retrieval. Real RAG corpora have
  unique entities.
- Mutations bump versions doc-wide (all 3 chunks), not just the edited
  chunk. First cut only versioned chunk 0, which made the partial-chunk
  fault a no-op. Doc-level versioning is also what real pipelines do.
- Hashed fallback uses TF-IDF weighting (`HashEmbedder.fit` over the corpus),
  as the task spec anticipated ("hashed TF-IDF"). Without IDF, template
  boilerplate drowned entity discriminators.
