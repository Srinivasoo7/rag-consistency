# Consistency classes (draft — slots into paper/body.md §4)

## System model

Two stores, no shared commit. The source of truth S is a relational
table `chunks(chunk_id, version, content_hash, deleted, updated_at)`; a
write is *source-committed* when it is durable in S. The ANN index I
holds entries `(chunk_id, version, content_hash, indexed_at, payload)`
written asynchronously by an indexing worker. A mutation commits to S at
`t_c = updated_at`; the worker later upserts the new entry into I with
`indexed_at = t_i`. The pipeline lag of an entry is `ℓ = t_i − t_c`
(ℓ = 0 for chunks never mutated). Queries rank entries by embedding
similarity only.

## The classes

For a chunk at eval time t:

1. **Index-available.** I contains an entry for the chunk — any version,
   including a stale one or a deleted row the worker never tombstoned.
2. **Version-coherent.** The entry matches the source row: equal version,
   equal content hash, and the source row is not deleted. This is exactly
   the join predicate J.
3. **Bounded-Δ.** `ℓ ≤ Δ`. A pure lag bound; it says nothing about *which*
   version was indexed. A promptly indexed stale write is bounded-Δ but
   incoherent.
4. **Fresh-Δ.** Version-coherent ∧ bounded-Δ. This is the SLA that
   `drop@Δ` enforces per query.

Inclusions: fresh-Δ ⇒ version-coherent ⇒ index-available. Bounded-Δ is
orthogonal to coherence — it constrains *when* the worker ran, not *what*
it wrote. The Δ=0 footgun (§Results) is the degenerate case: a bound
demanded with no regard for the pipeline's actual lag rejects
laggy-but-coherent hits and collapses recall on a healthy pipeline.

**Read-your-writes** is fresh-Δ with Δ ≥ T for the writer's own pipeline
lag T. The SLA curve (§Results) shows the boundary is sharp, not gradual:
Δ ≥ T preserves recall, Δ < T collapses it. Enforceability is a property
of the (Δ, T) pair, not of the mechanism.

## Why the classes are invisible to retrieval

The ANN ranking function is a function of embedding distance alone. None
of the four classes is a function of the embedding: a stale payload can
be the nearest neighbor at arbitrarily high similarity, and a deleted row
never stops being similar to the query that once matched it. Every silent
worker fault — dropped updates, missing tombstones, partial batches,
mid-batch crashes — therefore passes through ranking undetected and
surfaces only as a confident wrong answer. The competent pipeline is the
degenerate case where the worker commits no faults: the classes coincide
and staleness is zero by construction, which is why it is a sanity
control, not a result.

## What the classes give the metrics

- *stale-hit@k* (retrieval layer): fraction of top-k hits that are
  index-available but fail J — version-incoherent, or whose source row is
  deleted. No answers are generated; this diagnoses where the fault
  entered.
- *stale-citation rate* (generation layer): fraction of queries whose
  emitted span fails J; *stale | emitted* conditions on emitted answers.
  This is the paper's claim.

The two are different numbers because the generator's abstention and
span-selection policies sit between them: flag leaves stale-hit unchanged
while zeroing stale-citation, which is why the policies must not be
bundled.
