# RUNLOG — environment substitutions and decisions

## 2026-09-12: milestone 2

### Embeddings: MiniLM attempt via PyTorch CPU wheels (IN PROGRESS)
- `sentence-transformers` 6.0.1 installed successfully after retrying `pip`
  through the PyTorch CPU wheel index (`--index-url
  https://download.pytorch.org/whl/cpu`); torch 2.x CPU-only in the venv.
- `all-MiniLM-L6-v2` weight download initially failed: the sandbox's
  proxy env (`HTTP_PROXY=...hatch-egress-proxy:3128`) plus `no_proxy`
  entries like `[::1]` make `httpx` (via huggingface_hub) raise
  `InvalidURL: Invalid port: ':1]'` when building its client.
- Workaround that worked: keep the proxy vars (direct TLS egress is
  blocked: `SSL: WRONG_VERSION_NUMBER`) but sanitize `no_proxy` to
  `localhost,127.0.0.1`. Model downloaded and loads (dim=384).
- `index/embedder.py::Embedder` now honors `RAGC_EMBEDDER=hash|minilm|auto`
  so hash and MiniLM suites can be produced without uninstalling packages.

### MiniLM result on this corpus (SURPRISE — honest bad news)
- Full 1k-doc MiniLM baseline finished (2 min, postgres):
  recall@5 = 0.18 vs hashed TF-IDF 0.59. MiniLM is WORSE here.
- Cause (probed at 50 docs: perfect retrieval; degrades with scale):
  the corpus has ~143 docs per template with unique ID-like entity names
  (`Aurora X1-0000` vs `Aurora X1-0142`); MiniLM's subword embeddings
  barely discriminate the numeric suffix, while TF-IDF exact-matches it.
- Cross-scenario stale-hit deltas mostly hold (drop 0.0734->0.0504,
  no-tombstone 0.2428->0.2042, crash 0.3892->0.3766,
  all-faults 0.4922->0.4492) but partial-2of3 attenuates 0.1214->0.0:
  when the embedder can't retrieve the target doc, it retrieves
  coherent-but-irrelevant chunks and the coherence signal is masked.
- Decision: hashed TF-IDF is the PRIMARY embedder for the mechanism
  tables (cleanest signal, matches milestone 1); MiniLM is the
  robustness check. `compare_embedders.py` writes
  `data/embedder_comparison.md`.

### Postgres reinstall after VM replacement
- The VM was replaced mid-session: /usr, /etc/postgresql, /var/lib
  vanished. Reinstalled `postgresql` via apt, recreated database `ragc`,
  re-applied the localhost `trust` auth fix. Bulk snapshot optimization
  kept run times at ~2-3 min per 10-scenario suite.

### Milestone 2 mechanism results (hash embedder, 1k docs, postgres)
- `run_join.py` grid (6 configs x 10 scenarios) runs end-to-end in ~100s.
  Two interface bugs fixed (pipeline passed `eval_t` to `joiner.apply`
  which doesn't take it; run_one assumed 5-tuple hits when join is off).
- Retrieval layer (`data/join_before_after_hash.md`): drop@d5s and
  drop@d60s drive stale-hit@5 to 0.0000 in EVERY fault scenario
  (0.0734/0.2428/0.1214/0.3892/0.4922 -> 0). Recall tax is visible
  (crash 0.59->0.43, all-faults 0.58->0.39).
- Generation layer (`data/citation_before_after_hash.md`): extractive
  stale-citation rate -> 0.0000 in every fault scenario (crash
  0.371->0, all-faults 0.460->0); answer-correct improves (crash
  0.369->0.425, all-faults 0.359->0.429).
- SLA enforceability (`data/delay_sla_curve_hash.md`): drop@d{delta}
  preserves recall iff delta >= pipeline lag T; below that recall
  collapses (delay-30s: drop@d5s 0.27 vs drop@d60s 0.59). The collapse
  IS the measurement of an unenforceable SLA.
- MiniLM join grid running as robustness check (--tag minilm).
- MiniLM join grid DONE (11m45s): drop@d5s drives stale-hit@5 and
  stale-citation to 0.0000 in every scenario where they were nonzero
  (drop 0.0504->0, no-tombstone 0.2042->0, crash 0.3766->0, all-faults
  0.4492->0). Mechanism holds under both embedders.
- Determinism: join "off" configs exactly reproduce the standalone
  baseline (stale_hit_rate, recall_at_k, missed_fresh_rate all match).
- Qdrant NOT added: steps 1-3 are complete and clean, but the mechanism
  is validated on FAISS and the VM was already replaced once mid-session;
  a second vector store remains a later validation leg, explicitly
  deferred.

### Postgres TCP auth (FIXED)
- `SourceStore(backend="auto")` silently fell back to SQLite: TCP
  connections to 127.0.0.1:5432 as user `postgres` hit `scram-sha-256`
  in pg_hba.conf and hung on a password prompt (no password is set).
- Fix: set `host ... 127.0.0.1/32` and `::1/128` lines to `trust` and
  reloaded (localhost-only, synthetic data). Backup at
  `/etc/postgresql/16/main/pg_hba.conf.bak`.
- A 1k-doc baseline re-run on SQLite was killed mid-run (scenario 4/10,
  ~50 min projected); SQLite numbers would have been valid but the run
  was too slow and milestone 1 used Postgres.

### Bulk write/read optimization (harness speed only)
- `SourceStore.bulk_begin()/bulk_end()` wrap each scenario build in one
  transaction; `get_all()` bulk-fetches the immutable query-phase
  snapshot once; `metrics.evaluate`, `VersionJoiner`, and `cite.py` take
  the snapshot instead of per-hit PG round-trips.
- Effect: corrected 10-scenario TF-IDF baseline now finishes in ~3 min
  (was >11 min and killed). No measured number changed: the re-run
  reproduces milestone-1 stale-hit rates exactly (0.0000 / 0.0734 /
  0.2428 / 0.1214 / 0.3892 / 0.4922).

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

## 2026-09-12 — reviewer corrections (Sri, verified against c2555a6 + raw JSON)

- Cost language tightened: the version join is free (hash-grid max p95
  1.39 ms; drop/flag sub-ms); **repair is not** once the embedder is real
  (MiniLM repair@d0s p95 = 113 ms on crash/all-faults — read-path re-embed).
- Flag unbundled from drop: flag@d0s leaves stale-hit@5 unchanged
  (all-faults 0.4922 → 0.4922); it only zeroes stale-citation via
  abstention (0.237 on all-faults). Flag is a citation policy, drop is the
  retriever result.
- repair@d0s on the competent pipeline is a footgun: R@5 0.5897 → 0.2733,
  acc 0.497 → 0.343. Operating points are drop@5s/drop@60s and repair at a
  Δ the pipeline can meet — never Δ=0.
- Deleted-query finding: 173/1000 queries target deleted docs; under
  drop@5s the extractor cites a live neighbor (abstention 0.0000,
  correct 0.0000) — fresh-but-wrong, not stale. Correctness is reported
  **excluding deleted** (cap 1 − 0.173 = 0.827 under any answering policy);
  "missing source ⇒ abstain" left as the explicit next mechanism.
- cite.summarize now emits `stale_citation_rate_emitted` (stale | emitted
  answers); README language-discipline bullet corrected (rate is over all
  queries; the conditioned metric is the new column). Hash grid re-run
  2026-09-12 on Postgres reproduces all committed cells exactly.
- README headline table pointers fixed: un-suffixed single_fault_table.md /
  delay_cdf_table.md / denominators.md are MiniLM outputs (R@5 ~0.18);
  `_hash.md` files are the primary tables.
- ID-recall note: recall@k counts chunk_id v1 as a hit, so part of the
  drop recall tax is the metric no longer crediting stale ids. Stated next
  to the tax in paper/results.md.
- Environment: postgres kept dying on this VM and pg_hba had reverted to
  scram-sha-256 (TCP connects hang on password prompt); re-applied
  host-trust for 127.0.0.1/32 and ::1/128 and reloaded. The silent SQLite
  fallback masked this — consider failing loud when RAGC_PG_DSN is set.
