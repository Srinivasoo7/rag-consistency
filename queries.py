"""Query set: questions whose gold answer changes with the mutation,
plus unchanged controls (to measure recall cost of any mechanism later).

Each query: {qid, text, doc_id, gold_answer, gold_chunk_ids, kind}
kind in {'mutated', 'deleted', 'control'}.
"""
from __future__ import annotations

from common import CHUNKS_PER_DOC


def build_queries(docs, mutations):
    queries = []
    for d in docs:
        doc_id = d["doc_id"]
        mtype, new_answer = mutations[doc_id]
        chunk_ids = [f"{doc_id}#c{k}" for k in range(CHUNKS_PER_DOC)]
        base = dict(qid=f"q-{doc_id}", text=d["question"], doc_id=doc_id)
        if mtype in ("edit", "rewrite"):
            queries.append({**base, "gold_answer": new_answer,
                            "gold_chunk_ids": chunk_ids, "kind": "mutated"})
        elif mtype == "delete":
            queries.append({**base, "gold_answer": None,
                            "gold_chunk_ids": [], "kind": "deleted"})
        else:
            queries.append({**base, "gold_answer": d["answer"],
                            "gold_chunk_ids": chunk_ids, "kind": "control"})
    return queries
