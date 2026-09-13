# The Index Is Not the Source: Retrieval Consistency for Two-Store RAG

Draft for `paper/body.md`. Section 3 is merged from `paper/consistency_classes.md` (`cfeeb72`). Results live in `paper/results.md`. Numbers are the hash-embedder grid unless labeled MiniLM.

---

## Abstract

Retrieval-augmented generation is two stores pretending to be one: a strongly consistent document store (the source of truth) and an eventually consistent vector index (the retrieval layer). There is no shared commit. When a document is updated or deleted, the index lags — or never converges, if the embedding worker fails silently. During that window the retriever returns stale vectors and the generator cites text that is no longer current. This is a systems bug, not a model bug.

We make three contributions. First, we define retrieval consistency for the two-store case: four classes (index-available, version-coherent, bounded-Δ, fresh-Δ), and the distinction between retrieval-layer *stale-hit@k* and generation-layer *stale-citation*. Second, we measure both under controlled updates, deletes, and injected pipeline faults on a 1,000-document split store (Postgres + FAISS). A competent incremental upsert yields stale-hit@5 = 0; under single faults the rate is 0.07–0.39; under a constructed all-faults composition it is 0.49. Delay-only faults converge by evaluation time — the window is the result, reported as time-to-visible. Third, a version-joined retriever that drops hits failing a source-version join (or exceeding Δ) drives stale-hit@5 and extractive stale-citation to 0.0000 in every fault scenario we tested. The tax is recall (all-faults 0.58 → 0.39), not join latency. A freshness SLA Δ is enforceable if and only if Δ ≥ pipeline lag T; demanding Δ = 5s from a 30s pipeline collapses recall 0.59 → 0.27.

We do not claim hallucination-free RAG, temporal supersession of coexisting facts, or a production incidence rate. The result is a lower stale-citation rate plus an explicit freshness SLO.

---

## 1. Introduction

Production RAG systems ground an LLM in a corpus by retrieving nearest neighbors from a vector index and inserting them into the prompt. The operational reality is a split data layer: documents live in an object store or OLTP database; embeddings live in a purpose-built ANN service; an asynchronous worker copies one into the other. Writes commit in the source. Retrieval reads the index. Nothing atomic binds the two.

The failure is quiet. Standard RAG metrics — context recall, faithfulness, citation overlap against a frozen snapshot — score well while the index serves a policy that legal updated this morning, or a page that was deleted. The generator is faithful to the retrieved span. The span is wrong about the source.

Two different problems get filed under “staleness,” and they are not the same.

- **Problem A (this paper): index/source incoherence.** The source row moved. The index entry did not. This is a cache-coherence bug with an unbounded window if the worker drops the event.
- **Problem B (VersionRAG, MemStrata, temporal RAG): content-level validity.** Old and new facts both exist as first-class source rows. Embeddings cannot tell which value is current.

Problem B is crowded. Problem A is what split-stack RAG actually ships, and it is what we measure.

Section 2 states the threat model. Section 3 defines the classes. Section 4 describes the version-joined retriever. Section 5 is the experimental setup. Section 6 is results (`paper/results.md`). Section 7 is related work. Section 8 is limitations.

---

## 2. Threat model

**System.** Source of truth S holds chunk rows `(chunk_id, doc_id, source_version, content_hash, text, updated_at, deleted)`. ANN index I holds, for each indexed chunk, `(chunk_id, vector, source_version, content_hash, indexed_at, payload)`. A worker consumes source events (upsert, delete) and applies them to I. Retrieval is top-k over I. Generation, in this paper, is extractive: emit the payload of one retrieved chunk, or abstain.

**What the environment can do.**

- Commit an in-place edit, a superseding rewrite, or a delete in S.
- Delay the worker by a lag T.
- Drop a fraction of upsert events with no error returned to S.
- Apply only k of n chunk upserts for a document (partial reindex).
- Skip delete / tombstone events (deleted rows remain searchable).
- Crash after applying a prefix of a batch and never recover.

**What we do not model.** Concurrent writers on the same chunk with conflicting versions; embedding-model upgrades mid-index; HNSW graph-repair races; multi-tenant isolation; an LLM that paraphrases a stale span into a fluent answer. Extractive citation is a lower bound on a fluent model’s ability to launder stale text.

**Out of scope, on purpose.** Coexisting current and superseded *source* facts with similar embeddings (Problem B). A version join against S cannot retire a fact that S still considers live.

---

## 3. Consistency classes

Two stores, no shared commit. A write is *source-committed* when it is durable in S. A mutation commits to S at `t_c = updated_at`; the worker later upserts the new entry into I with `indexed_at = t_i`. Pipeline lag of an entry is `ℓ = t_i − t_c` (ℓ = 0 for chunks never mutated). Queries rank entries by embedding similarity only.

### The classes

For a chunk at evaluation time t:

1. **Index-available.** I contains an entry for the chunk — any version, including a stale one or a deleted row the worker never tombstoned.
2. **Version-coherent.** The entry matches the source row: equal version, equal content hash, and the source row is not deleted. This is exactly the join predicate J.
3. **Bounded-Δ.** `ℓ ≤ Δ`. A pure lag bound; it says nothing about *which* version was indexed. A promptly indexed stale write is bounded-Δ but incoherent.
4. **Fresh-Δ.** Version-coherent ∧ bounded-Δ. This is the SLA that `drop@Δ` enforces per query.

Inclusions: fresh-Δ ⇒ version-coherent ⇒ index-available. Bounded-Δ is orthogonal to coherence — it constrains *when* the worker ran, not *what* it wrote. The Δ=0 footgun (results) is the degenerate case: a bound demanded with no regard for the pipeline’s actual lag rejects laggy-but-coherent hits and collapses recall on a healthy pipeline.

**Read-your-writes** for embeddings is fresh-Δ with Δ ≥ T for the writer’s own pipeline lag T. We do not implement a session cache; the SLA curve shows the boundary is sharp, not gradual: Δ ≥ T preserves recall, Δ < T collapses it. Enforceability is a property of the (Δ, T) pair, not of the join mechanism.

### Why the classes are invisible to retrieval

The ANN ranking function is a function of embedding distance alone. None of the four classes is a function of the embedding: a stale payload can be the nearest neighbor at arbitrarily high similarity, and a deleted row never stops being similar to the query that once matched it. Every silent worker fault — dropped updates, missing tombstones, partial batches, mid-batch crashes — therefore passes through ranking undetected and surfaces only as a confident wrong answer. The competent pipeline is the degenerate case where the worker commits no faults: the classes coincide and staleness is zero by construction, which is why it is a sanity control, not a result.

### What the classes give the metrics

- *stale-hit@k* (retrieval): fraction of top-k hits that are index-available but fail J — version-incoherent, or whose source row is deleted. No answers are generated; this diagnoses where the fault entered.
- *stale-citation* (generation): fraction of all queries whose emitted span fails J. *stale | emitted* conditions on emitted answers. This is the paper’s claim.

The two are different numbers because the generator’s abstention and span-selection policies sit between them: flag leaves stale-hit unchanged while zeroing stale-citation, which is why the policies must not be bundled.

Recall@k in this paper is ID-recall against current gold chunk ids. Retrieving the stale v1 of the same id still counts. Missed-fresh is split into *index was coherent* (embedder miss) versus *index was stale* (pipeline miss). Time-to-visible / time-to-purge are `indexed_at − updated_at` over upserts that landed and `purged_at − updated_at` over deletes that were tombstoned.

---

## 4. Version-joined retriever

At query time, ANN returns a candidate list of size k × overfetch. Each candidate is joined to S on chunk_id. A hit **passes** iff it satisfies J and ℓ ≤ Δ.

Three policies on failure:

- **drop** — discard the hit; fill from the over-fetched tail; truncate to k. This is the retriever result. It enforces fresh-Δ.
- **flag** — keep the hit, mark ok=false. Citation must skip it. Stale-hit@k does not move. This is a citation policy.
- **repair** — if the failure is version-diverged, re-fetch the current source text and re-embed on the read path; deleted / missing hits are still dropped. Repair at Δ=0 on a healthy 1s pipeline is a footgun: laggy-but-coherent hits are not repaired, they are dropped.

The join is a primary-key lookup. Repair is an embed.

---

## 5. Experimental setup

**Stores.** Source is PostgreSQL 16 (`chunks` table) when reachable; an explicit `RAGC_PG_DSN` that cannot be reached raises rather than falling back to SQLite. Index is FAISS `IndexIDMap2(IndexFlatIP)` — exact inner-product search, not HNSW. Payload text is stored beside the vector so a naive generator can cite a stale span.

**Corpus.** 1,000 synthetic documents × 3 chunks. Each document has one checkable factoid (chunk 0) and two fillers. Entity names are unique per document (`Aurora X1-0000` vs `Aurora X1-0142`). Templates cover satellites, drugs, metro lines, software releases, and executives.

**Mutations**, committed together at virtual t=60: edit 30%, rewrite 20%, delete 15%, no-op 35%. Realized counts: 488 updated, 173 deleted, 339 controls. All three chunks of an updated document bump `source_version` together.

**Queries.** Exactly one query per document (1,000 total): mutated queries gold-bind the new answer; controls gold-bind the original; deleted queries have no gold answer. Targeting is uniform-per-doc, not popularity-skewed.

**Worker and clock.** A virtual clock drives lag. Delay faults are simulated, never slept. The competent worker drains at t=61 (1s after commit). Evaluation is later (1h–2h of virtual time), so delay-only scenarios have eval-time stale-hit = 0 by construction; their result is the time-to-visible value T, which feeds the SLA curve.

**Faults.** Single operators: drop 10% of upserts; no tombstones; partial 2-of-3 chunk upserts; crash after 50% of the due batch. `all-faults` composes those four in that order (`FAULT_MIX.md`). It is a constructed upper bound, not an incidence estimate.

**Embedders.** Primary: hashed unigram+bigram TF-IDF, 384-d, L2-normalized, IDF fitted on the corpus. Robustness: all-MiniLM-L6-v2. On this entity-id corpus MiniLM recall@5 is 0.18 vs 0.59 for hash; subword embeddings do not separate numeric suffixes. Mechanism tables use hash. MiniLM is Appendix A. An explicit `RAGC_EMBEDDER=minilm` that cannot load the model fails loud.

**Generator.** Extractive: emit the top-1 passing span’s payload, or abstain. No LLM.

**Seeds.** Corpus seed 20260912, mutation seed +1, worker RNG seed 7. Re-runs reproduce every metric except wall-clock p50/p95.

---

## 6. Results

See `paper/results.md`. Headline: `drop@5s` drives stale-hit@5 and extractive stale-citation to 0.0000 on every single fault and on the labeled all-faults bound; the tax is recall and neighbor-substitution on deleted entities, not join latency; a freshness SLA is a step function of Δ versus T.

The repair@0s footgun on a competent pipeline is recall@5 0.5897 → 0.2733 and correctness ex-deleted 0.601 → 0.415.

---

## 7. Related work

**Problem B, not this paper.** VersionRAG reports 58% → 90% on 100 version-sensitive questions over 34 technical documents (Huwiler, Fürst, Stockinger, arXiv:2510.08109). MemStrata reports naive RAG serving superseded values in 15–40% of forced-answer cases on templated evolving facts (Yadav, arXiv:2606.26511). Both attack coexisting facts in the source. A source-version join does not help if both values are live rows.

**Unified stores.** Budigi and Sirigiri (arXiv:2605.03275) measure a 3.54 ms mean window between two Postgres tables merged in application code, and 0 ms when document and embedding share a transaction, on 50k documents. That result is “atomic co-location can zero the window inside one engine.” It is not a measurement of object-store + remote ANN lag, and it is not a refutation of a split-stack study. Production RAG at scale is still usually split; residual windows after competent CDC (dropped events, untombstoned deletes, partial batches) are the measurement target here.

**Industry practice.** Incremental reindex, CDC, content hashes, tombstones, alias swaps, and `valid_from` filters are known. They are the competent row of our table (stale-hit = 0 when the worker finishes). This paper is the residual under silent failure, plus a query-time join that does not trust the worker.

**Other “consistency” in RAG.** Output-stability across paraphrases, multilingual context use, and position-bias regularization are generator properties. They are unrelated to two-store coherence.

---

## 8. Limitations

- Synthetic factoid corpus, unique entity ids, one query per document. Not an enterprise wiki or ticket corpus.
- Exact FAISS Flat, not HNSW; no remote ANN (Qdrant / Pinecone deferred).
- Extractive citation, not an LLM. A generator can still ignore a fresh span or invent a citation.
- Deleted-entity queries are answered from live neighbors under drop (173/1000). Fresh-but-wrong. Missing-source ⇒ abstain is future work.
- `all-faults` is a composed stress bound, not a production mix.
- Delay “CDFs” are degenerate (every chunk lands at exactly T). They exist to feed the SLA curve.
- ID-recall credits stale ids under `join off`. Part of the drop tax is the metric becoming honest.

---

## 9. Conclusion

RAG’s retrieval layer is an eventually consistent cache of a source of truth. Without a join, that fact is invisible to the generator. With a version join and a lag bound the pipeline can actually meet, stale-hit and extractive stale-citation go to zero on the faults we can inject, and the bill arrives as recall and as answers about deleted entities drawn from their neighbors. That is a freshness SLO, not a claim that the model stopped hallucinating.
