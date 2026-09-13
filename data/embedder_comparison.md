# Embedder comparison: hashed TF-IDF vs all-MiniLM-L6-v2

> Same 1k corpus, same faults, same seeds — only the embedder
> differs. The claim under test: cross-scenario deltas
> (stale-hit@5 per fault scenario) do not flip. Absolute recall@5
> is expected to rise with MiniLM (better semantic matching).

| scenario | stale-hit@5 (hash \| minilm) | recall@5 (hash \| minilm) | delta-flip? |
|---|---|---|---|
| competent | 0.0 \| 0.0 | 0.5897 \| 0.1794 | ok |
| delay-1s | 0.0 \| 0.0 | 0.5897 \| 0.1794 | ok |
| delay-30s | 0.0 \| 0.0 | 0.5897 \| 0.1794 | ok |
| delay-5m | 0.0 \| 0.0 | 0.5897 \| 0.1794 | ok |
| delay-1h | 0.0 \| 0.0 | 0.5897 \| 0.1794 | ok |
| drop-10pct | 0.0734 \| 0.0504 | 0.5925 \| 0.1798 | ok |
| no-tombstone | 0.2428 \| 0.2042 | 0.5599 \| 0.1685 | ok |
| partial-2of3 | 0.1214 \| 0.0 | 0.5897 \| 0.1794 | FLIP |
| crash-mid-batch | 0.3892 \| 0.3766 | 0.5897 \| 0.1818 | ok |
| all-faults | 0.4922 \| 0.4492 | 0.5836 \| 0.1765 | ok |

**Result: FLIPS in: partial-2of3**
