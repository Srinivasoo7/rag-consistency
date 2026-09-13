# Denominators (identical across scenarios; fixed seeds)

- docs: 1000 x 3 chunks = 3000 chunks
- updated docs (edit+rewrite): 488
- deleted docs: 173
- noop docs: 339
- fraction of corpus mutated: 0.661
- mutation mix: {'edit': 0.3, 'rewrite': 0.2, 'delete': 0.15, 'noop': 0.35}
- queries: 1000 (uniform-per-doc: exactly 1 query per doc; kind=mutated (edit/rewrite, gold=new answer), kind=deleted (gold=None), kind=control (gold=original answer))
- query kinds: {'mutated': 488, 'control': 339, 'deleted': 173}

## Provenance

- {'seed': 20260912, 'worker_seed': 7, 'embedder_backend': 'minilm', 'embedder_dim': 384, 'embedder_spec': 'all-MiniLM-L6-v2, frozen, CPU, normalize_embeddings=True', 'faiss_index': 'IndexIDMap2(IndexFlatIP) — exact search (flat)', 'store_backend': 'postgres'}
