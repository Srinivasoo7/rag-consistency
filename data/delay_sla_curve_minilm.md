# Delay scenarios x freshness SLA (the enforceability curve)

> A freshness SLA delta is enforceable only when delta >= the
> pipeline lag T. Below that, drop@delta removes coherent hits and
> recall collapses — that collapse IS the measurement (the tax of
> demanding an SLA your pipeline cannot meet).

| scenario (T) | join | stale-hit@5 | recall@5 | p95 ms |
|---|---|---|---|---|
| delay-1s | off | 0.0 | 0.1794 | 0.15 |
| delay-1s | drop@d0s | 0.0 | 0.1004 | 0.2 |
| delay-1s | drop@d5s | 0.0 | 0.1794 | 0.32 |
| delay-1s | drop@d60s | 0.0 | 0.1794 | 0.35 |
| delay-30s | off | 0.0 | 0.1794 | 0.19 |
| delay-30s | drop@d0s | 0.0 | 0.1004 | 0.2 |
| delay-30s | drop@d5s | 0.0 | 0.1004 | 0.23 |
| delay-30s | drop@d60s | 0.0 | 0.1794 | 0.22 |
| delay-5m | off | 0.0 | 0.1794 | 0.2 |
| delay-5m | drop@d0s | 0.0 | 0.1004 | 0.23 |
| delay-5m | drop@d5s | 0.0 | 0.1004 | 0.97 |
| delay-5m | drop@d60s | 0.0 | 0.1004 | 0.23 |
| delay-1h | off | 0.0 | 0.1794 | 0.14 |
| delay-1h | drop@d0s | 0.0 | 0.1004 | 0.38 |
| delay-1h | drop@d5s | 0.0 | 0.1004 | 0.29 |
| delay-1h | drop@d60s | 0.0 | 0.1004 | 0.34 |
