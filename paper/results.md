# Results (draft)

## A source-version join eliminates stale retrieval and stale citation

We evaluate the version-joined retriever of §3 on the fault suite of §4
(hashed TF-IDF primary; MiniLM robustness in Appendix A). The operating
point is `drop@Δ`: join each ANN hit to its source row on
`(source_version, content_hash, deleted)` and drop hits that fail the join
or exceed the pipeline-lag bound Δ. Table 1 reports the before/after on
single faults and on the labeled all-faults upper bound
("under this fault mix (defined in FAULT_MIX.md)" — we make no claim about
production incidence).

**Table 1.** Retrieval-layer stale-hit@5, generation-layer stale-citation
rate, answer correctness, and recall@5, join off vs `drop@5s`.
Correctness is reported *excluding* the 173/1000 queries that target deleted
documents (see §5.4); overall accuracy is capped at 0.827 under any
answering policy.

| scenario | stale-hit@5 off → drop | stale-cite off → drop | correct (ex-del) off → drop | recall@5 off → drop |
|---|---|---|---|---|
| competent | 0 → 0 | 0 → 0 | 0.601 → 0.601 | 0.5897 → 0.5897 |
| drop-10pct | 0.0734 → 0 | 0.068 → 0 | 0.577 → 0.589 | 0.5925 → 0.5607 |
| no-tombstone | 0.2428 → 0 | 0.197 → 0 | 0.579 → 0.601 | 0.5599 → 0.5897 |
| partial-2of3 | 0.1214 → 0 | 0.095 → 0 | 0.601 → 0.634 | 0.5897 → 0.5099 |
| crash-mid-batch | 0.3892 → 0 | 0.371 → 0 | 0.446 → 0.514 | 0.5897 → 0.4264 |
| all-faults | 0.4922 → 0 | 0.460 → 0 | 0.434 → 0.519 | 0.5836 → 0.3865 |

Three observations. First, the join is decisive: `drop@5s` drives
retrieval stale-hit@5 to **0.0000** in every fault scenario, and the
extractive stale-citation rate — the paper's claim — to **0.0000** as well.
Correctness does not merely stop degrading; it improves (all-faults
0.434 → 0.519 ex-deleted), because citations now draw on fresh spans.
Second, the competent row is a sanity control, not a finding: a pipeline
that finishes before evaluation has nothing stale to serve, and the join
correctly changes nothing (all deltas 0). Third, `drop@60s` is identical to
`drop@5s` on every non-delay scenario: evaluation runs long after the
competent 1s indexing tick, so 5s and 60s are the same operating point.
The Δ parameter only bites on the delay grid (§5.3).

## The tax is recall, not latency

Drop converts stale hits into misses — it cannot conjure chunks the
pipeline never indexed. The missed-fresh split makes this explicit:
conditional on a coherent index, missed-fresh barely moves (all-faults
0.2539 → 0.2160); conditional on a stale index it rises sharply
(0.1624 → 0.3974), because the dropped stale hit had been masking a
missing fresh chunk. Recall@5 falls accordingly (all-faults 0.5836 →
0.3865; crash 0.5897 → 0.4264). Two qualifications. Recall is measured
against chunk identity, so retrieving the stale v1 of a chunk still counts
as a hit under `off` — part of the 0.58 → 0.39 drop is the metric no
longer crediting the stale ids the join removed. And the tax is not
uniformly negative: under no-tombstone, recall *rises* (0.5599 → 0.5897),
because retained deleted rows had been occupying top-5 slots that fresh
chunks now reclaim.

Latency is not the tax. The join is a primary-key lookup per hit: worst
p95 across the hash grid is 1.39 ms, and drop/flag stay sub-millisecond.
**The version join is free; repair is not, once the embedder is real.**
`repair@d0s` re-resolves diverged hits against the source and re-embeds,
reaching 113 ms p95 under MiniLM on crash/all-faults. Any latency claim
for repair must be stated per-embedder.

## Policies are not interchangeable

`drop`, `flag`, and `repair` solve different problems and must not be
bundled. **Drop** is the retriever result: it zeroes stale-hit@5. **Flag**
leaves stale-hit@5 unchanged (all-faults 0.4922 → 0.4922); it only zeroes
*stale-citation*, by refusing to emit flagged spans, and it pays
abstention (0.24 on all-faults). Flag is a citation policy, not a
retrieval fix. **Repair** also zeroes stale-hit@5 and recovers recall
better than drop on the harsh faults (all-faults R@5 0.505 vs 0.3865;
correctness ex-deleted 0.582 vs 0.519 — within striking distance of the
competent 0.601), but `repair@d0s` on a healthy pipeline is a footgun:
competent R@5 collapses 0.5897 → 0.2733 and correctness 0.497 → 0.343,
because Δ=0 demands a zero-lag pipeline and drops laggy-but-coherent
hits (competent correctness ex-deleted 0.601 → 0.415). The paper's operating points are `drop@5s`/`drop@60s` and repair at
a Δ the pipeline can actually meet — never Δ=0.

## A freshness SLA is enforceable iff Δ ≥ pipeline lag T

The delay grid varies the indexing worker's lag T ∈ {1s, 30s, 5m, 1h} and
the SLA Δ ∈ {0, 5s, 60s}. The result is a step function (Figure 1):
`drop@Δ` preserves recall exactly when Δ ≥ T and collapses it otherwise.
At delay-30s, `drop@5s` recall is 0.2733 while `drop@60s` holds 0.5897;
at delay-5m and delay-1h every Δ collapses to 0.2733, because T > 60s.
Δ bounds *pipeline lag* (`indexed_at − source.updated_at`), not
time-since-indexing — an unchanged chunk has lag 0 and always passes —
and the Δ=0 column is the deliberately unenforceable extreme that
validates the semantics: it rejects even the competent 1s-tick worker.
The collapse below the step is the measurement, not a bug: it is the tax
of demanding an SLA the pipeline cannot meet.

## Limitation: deleted entities are answered, not abstained

173 of 1000 queries target deleted documents. Under `drop@5s` the joiner
drops the deleted row, the extractor cites a *live neighbor*, abstention
stays 0.0000, and correctness on those queries stays 0.0000. That is
fresh-but-wrong, not stale — the join solved the coherence problem it was
asked to solve, and the answering policy created a new one. We report
correctness excluding deleted queries throughout; the alternative is a
"missing source ⇒ abstain" policy, which we leave as the explicit next
mechanism. Either way, the limitation belongs in the paper, not in a
rounding error.

## Robustness (Appendix A)

Under all-MiniLM-L6-v2 the mechanism still drives stale-hit and
stale-citation to 0 wherever they were nonzero. Absolute recall is far
lower (0.18 vs 0.59: the corpus's ID-like entity names defeat subword
embeddings while hashed TF-IDF exact-matches them), and the partial-2of3
delta attenuates to 0 (0.1214 → 0.0000) because weak retrieval masks the
coherence signal. Cross-scenario deltas otherwise hold, which is why the
hash embedder is primary and MiniLM is the robustness check.
