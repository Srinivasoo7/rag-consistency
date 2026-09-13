# Delay faults — time-to-visible / time-to-purge CDFs

> These scenarios converge by eval time (eval-time stale-hit@5 = 0),
> so the CDF of the staleness window is the result, not the
> eval-time row. All chunks converge: never_visible = 0.

| scenario (T) | ttv: min / p25 / p50 / p75 / max (s), n | ttp: min / p25 / p50 / p75 / max (s), n | never_purged |
|---|---|---|---|
| delay-1s | 1.0/1.0/1.0/1.0/1.0, n=1464 | 1.0/1.0/1.0/1.0/1.0, n=519 | 0 |
| delay-30s | 30.0/30.0/30.0/30.0/30.0, n=1464 | 30.0/30.0/30.0/30.0/30.0, n=519 | 0 |
| delay-5m | 300.0/300.0/300.0/300.0/300.0, n=1464 | 300.0/300.0/300.0/300.0/300.0, n=519 | 0 |
| delay-1h | 3600.0/3600.0/3600.0/3600.0/3600.0, n=1464 | 3600.0/3600.0/3600.0/3600.0/3600.0, n=519 | 0 |
