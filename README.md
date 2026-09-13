# RAG two-store consistency — measurement harness

Research code for the locked paper: **define retrieval consistency for a
two-store RAG system, measure stale-hit rate under updates/deletes/faults,
and show a version-joined retriever that enforces a per-query freshness
bound.** This repo is a *harness*, not a framework.

## Language discipline (reviewer-mandated, applies to all outputs)

- **stale-hit@k** is the RETRIEVAL-layer metric: fraction of top-k hits whose
  indexed version is older than the source version (or whose source row is
  deleted). No answers are generated at retrieval time.
- **stale-citation rate** is the GENERATION-layer metric: fraction of
  *emitted* answers whose span fails the source-version join.
- These are different numbers. The paper's claim is the second.
- Fault mixes are described only as "under this fault mix (defined in
  FAULT_MIX.md)" — never "a realistic fault mix".

## Layout

- `source/store.py` — source-of-truth store (`chunks` table). PostgreSQL if
  reachable, else SQLite (see RUNLOG.md).
- `index/ann.py` — ANN index side (faiss `IndexIDMap2` over `IndexFlatIP`,
  exact search); entries carry `{doc_id, source_version, content_hash,
  indexed_at}` plus the indexed payload text (stale payloads persist until
  upserted — this is what a naive generator would cite).
- `index/embedder.py` — hashed TF-IDF (`HashEmbedder`, primary: best
  retrieval on this entity-centric corpus, matches milestone 1) or
  all-MiniLM-L6-v2 on CPU (`RAGC_EMBEDDER=minilm`; weaker here — see
  RUNLOG.md — kept as a robustness check, not the headline).
- `mutator.py` — synthetic corpus (1k docs x 3 chunks, factoid Q/A) and the
  mutation generator: in-place edit, superseding rewrite, delete, no-op.
- `faults.py` — first-class fault injector: drop update, no tombstone,
  partial chunks, worker delay T, crash mid-batch, all-faults (see
  FAULT_MIX.md).
- `queries.py` — query set: mutation-sensitive questions + unchanged
  controls (uniform-per-doc: exactly 1 query per doc).
- `metrics.py` — time-to-visible/purge (+CDFs) / retrieval-layer stale-hit@k /
  missed-fresh split (coherent-index vs stale-index) / recall@k / nDCG /
  p50-p95 latency.
- `pipeline.py` — shared scenario builder + query runner, so baseline, join,
  and citation runs measure identical worlds.
- `joiner.py` — version-joined retriever: post-retrieval join of each hit to
  the source row on `(source_version, content_hash, deleted)` plus a
  pipeline-lag freshness SLA delta; policies drop / flag / repair.
- `cite.py` — extractive citation stage: emits the top-1 joined-fresh span
  (top-1 raw hit when the join is off); stale-citation / abstention /
  answer-correct rates.
- `run_baseline.py` — milestone 1: retrieval metrics across fault scenarios.
- `run_join.py` — milestone 2: join on/off before/after (retrieval +
  citation), and the delay-x-SLA enforceability curve.

## Key docs / artifacts

- `FAULT_MIX.md` — the all-faults composition card (exact operators).
- `DETERMINISM.md` — seeds, embedder spec, FAISS index type.
- `data/single_fault_table.md` — headline retrieval table (single faults lead;
  all-faults as labeled upper bound).
- `data/delay_cdf_table.md` — delay faults via time-to-visible/purge CDFs.
- `data/denominators.md` — corpus/query denominators + provenance.
- `data/join_before_after_hash.md` — the paper's key figure (retrieval
  layer, primary embedder). `_minilm` variants are the robustness check.
- `data/citation_before_after_hash.md` — generation-layer stale-citation
  before/after, overall and by query kind.
- `data/delay_sla_curve_hash.md` — SLA enforceability: delta vs pipeline lag.
- `data/embedder_comparison.md` — hashed TF-IDF vs MiniLM: deltas hold
  except partial-2of3 (attenuated under MiniLM; see RUNLOG.md).

## Reproduce from a fresh shell

```bash
cd ~/workspace/rag-consistency
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# sentence-transformers is optional (robustness check only — the hashed
# embedder is primary on this corpus; see RUNLOG.md):
.venv/bin/pip install sentence-transformers
.venv/bin/python run_baseline.py --docs 1000   # milestone 1 (corrected)
RAGC_EMBEDDER=hash .venv/bin/python run_join.py --docs 1000 --tag hash  # milestone 2
```

Optional: point at Postgres instead of SQLite:

```bash
sudo apt-get install -y postgresql
sudo -u postgres psql -c "CREATE DATABASE ragc;"
export RAGC_PG_DSN="dbname=ragc user=postgres host=localhost"
.venv/bin/pip install "psycopg[binary]"
.venv/bin/python run_baseline.py --backend postgres
```

## What the baseline does

1. Builds 1k synthetic docs (3 chunks each), indexes v1 at virtual t=0.
2. Commits mutations to the source at t=60 (edit 30% / rewrite 20% /
   delete 15% / noop 35%).
3. Runs the indexing worker under each fault scenario on a virtual clock
   (delays of 1s–1h are *simulated*, not slept).
4. Runs 1k queries (one per doc) and writes metrics + md tables to `data/`.

All staleness windows are virtual seconds. Retrieval latency is real
wall-clock on this machine.

## Freshness SLA semantics (joiner)

A hit passes the join iff it is version-coherent AND its pipeline lag
(`indexed_at - source.updated_at`) is within delta. Delta bounds *pipeline
lag*, not time-since-indexing: an unchanged chunk has lag 0 and always
passes. delta=0 demands a zero-lag pipeline (unenforceable even by the
competent 1s-tick worker) and is reported as the extreme point of the curve.
