"""Mutation generator + synthetic corpus.

1k docs x 3 chunks. Each doc has one key factoid (chunk 0) behind a
checkable question. Mutations: in-place edit, superseding rewrite,
delete, no-op control.
"""
from __future__ import annotations

import random

from common import MUTATION_MIX, N_DOCS, CHUNKS_PER_DOC, SEED, content_hash


# Each template: key(chunk0), key_alt (rephrased for rewrite), filler topics,
# question, slots, mutate(slot_dict, rng) -> new slot_dict
TEMPLATES = [
    dict(
        name="satellite",
        key="{name} is a communications satellite launched in {year} by {org}.",
        key_alt="Operated by {org}, the {name} communications satellite entered service with its launch in {year}.",
        fillers=["{name} provides broadband coverage across the region.",
                 "{org} operates a fleet of similar satellites.",
                 "Ground stations track {name} on every orbital pass."],
        question="In what year was {name} launched?",
        slots=dict(name=["Aurora X1", "Kepler Relay", "Nimbus 4", "Vega Link", "Orion Mesh"],
                   year=["2017", "2019", "2021", "2023"],
                   org=["Helios Corp", "Orbital Dynamics", "Skyline Space", "Meridian Aerospace"]),
        mutate_key="year",
        uniq="name",
    ),
    dict(
        name="drug",
        key="{drug} was approved in {year} for treating {cond}.",
        key_alt="Regulators cleared {drug} in {year} as a treatment for {cond}.",
        fillers=["{drug} is administered as a weekly injection.",
                 "Trials for {drug} enrolled patients with {cond}.",
                 "Physicians monitor liver function during {drug} therapy."],
        question="When was {drug} approved?",
        slots=dict(drug=["Nexavir", "Cortelix", "Zumabin", "Relvarto", "Osprea"],
                   year=["2016", "2018", "2020", "2022"],
                   cond=["migraine", "psoriasis", "asthma", "arthritis"]),
        mutate_key="year",
        uniq="drug",
    ),
    dict(
        name="metro",
        key="The {line} Line of the {city} metro opened in {year} with {n} stations.",
        key_alt="{city} opened its {line} Line metro service in {year}, initially serving {n} stations.",
        fillers=["The {line} Line connects the downtown core to the suburbs.",
                 "Trains on the {line} Line run every six minutes at peak.",
                 "{city} plans to extend the {line} Line next decade."],
        question="How many stations did the {city} {line} Line open with?",
        slots=dict(line=["Red", "Blue", "Green", "Orange"],
                   city=["Springfield", "Riverton", "Lakeside", "Fairview"],
                   year=["2015", "2018", "2021"],
                   n=["12", "18", "24", "31"]),
        mutate_key="n",
        uniq="line",
    ),
    dict(
        name="software",
        key="{prod} {ver} was released on {date}, adding {feat}.",
        key_alt="The {date} release of {prod} brought it to version {ver} with {feat}.",
        fillers=["{prod} runs on all major desktop platforms.",
                 "Users praised {feat} in early reviews of {prod}.",
                 "The {prod} team ships updates on a monthly cadence."],
        question="What is the latest released version of {prod}?",
        slots=dict(prod=["Northwind DB", "PixelForge", "CloudSync Pro", "DataLens"],
                   ver=["4.2", "5.0", "5.7", "6.1"],
                   date=["March 2024", "June 2024", "January 2025"],
                   feat=["offline mode", "dark theme", "AI search", "multi-user editing"]),
        mutate_key="ver",
        uniq="prod",
    ),
    dict(
        name="ceo",
        key="{person} became CEO of {co} in {year}.",
        key_alt="In {year}, {co} appointed {person} as chief executive.",
        fillers=["{co} reported record revenue under {person}.",
                 "{person} previously led product at a rival firm.",
                 "Analysts watch {co} closely since {person} took over."],
        question="Who became CEO of {co} in {year}?",
        slots=dict(person=["Amara Okafor", "Jonas Lindqvist", "Priya Raman", "Diego Fuentes"],
                   co=["Vertex Labs", "Bluepeak", "Novacore", "Stratos Inc"],
                   year=["2019", "2021", "2023"]),
        mutate_key="person",
        uniq="co",
    ),
    dict(
        name="stadium",
        key="{stad} in {city} has a seating capacity of {cap}.",
        key_alt="With seating for {cap}, {stad} is the largest venue in {city}.",
        fillers=["{stad} hosts concerts in the off-season.",
                 "The home team has played at {stad} for decades.",
                 "{city} funded renovations to {stad} last year."],
        question="What is the seating capacity of {stad}?",
        slots=dict(stad=["Grand Arena", "Harbor Stadium", "Summit Field", "Unity Park"],
                   city=["Springfield", "Riverton", "Lakeside", "Fairview"],
                   cap=["42000", "55000", "68000", "73000"]),
        mutate_key="cap",
        uniq="stad",
    ),
]


def _render(tpl: str, slots: dict) -> str:
    return tpl.format(**slots)


def generate_corpus(n_docs: int = N_DOCS, seed: int = SEED):
    rng = random.Random(seed)
    docs = []
    for i in range(n_docs):
        t = TEMPLATES[i % len(TEMPLATES)]
        slots = {k: rng.choice(v) for k, v in t["slots"].items()}
        # Unique entity per doc: otherwise questions are ambiguous (the same
        # name repeats across ~30 docs) and recall measures ambiguity, not
        # retrieval. Real RAG corpora have unique entities.
        slots[t["uniq"]] = f"{slots[t['uniq']]}-{i:04d}"
        doc_id = f"d{i:04d}"
        chunks = [_render(t["key"], slots)]
        fillers = rng.sample(t["fillers"], 2)
        chunks += [_render(f, slots) for f in fillers]
        assert len(chunks) == CHUNKS_PER_DOC
        docs.append({
            "doc_id": doc_id,
            "template": t["name"],
            "slots": slots,
            "chunks": chunks,
            "question": _render(t["question"], slots),
            "answer": slots[t["mutate_key"]],
            "mutate_key": t["mutate_key"],
        })
    return docs


def pick_mutations(docs, seed: int = SEED + 1):
    """Assign one mutation type per doc from MUTATION_MIX. Returns
    {doc_id: (mtype, new_answer_or_None)}."""
    rng = random.Random(seed)
    types = list(MUTATION_MIX)
    weights = [MUTATION_MIX[t] for t in types]
    out = {}
    for d in docs:
        mtype = rng.choices(types, weights=weights)[0]
        new_answer = None
        if mtype in ("edit", "rewrite"):
            t = next(x for x in TEMPLATES if x["name"] == d["template"])
            key = d["mutate_key"]
            choices = [c for c in t["slots"][key] if c != d["slots"][key]]
            new_answer = rng.choice(choices)
        out[d["doc_id"]] = (mtype, new_answer)
    return out


def seed_source(store, docs, clock):
    """Initial load: version 1 for every chunk, indexed_at handled by caller."""
    t = clock.now()
    for d in docs:
        for k, text in enumerate(d["chunks"]):
            cid = f"{d['doc_id']}#c{k}"
            store.upsert_chunk(cid, d["doc_id"], k, text, 1,
                               content_hash(text), t)


def apply_mutations(store, docs, mutations, clock):
    """Apply mutations to the source of truth. Returns change events:
    list of (op, chunk_id) with op in {'upsert','delete'}."""
    t = clock.now()
    events = []
    by_id = {d["doc_id"]: d for d in docs}
    for doc_id, (mtype, new_answer) in mutations.items():
        d = by_id[doc_id]
        tplt = next(x for x in TEMPLATES if x["name"] == d["template"])
        if mtype == "edit":
            slots = dict(d["slots"])
            slots[d["mutate_key"]] = new_answer
            # doc-level versioning: chunk 0 text changes, all chunks bump
            # version (this is what makes partial-chunk faults meaningful)
            for k in range(CHUNKS_PER_DOC):
                cid = f"{doc_id}#c{k}"
                text = _render(tplt["key"], slots) if k == 0 else d["chunks"][k]
                store.upsert_chunk(cid, doc_id, k, text, 2, content_hash(text), t)
                events.append(("upsert", cid))
            d["slots"] = slots  # keep doc record current
        elif mtype == "rewrite":
            slots = dict(d["slots"])
            slots[d["mutate_key"]] = new_answer
            for k in range(CHUNKS_PER_DOC):
                cid = f"{doc_id}#c{k}"
                text = _render(tplt["key_alt"], slots) if k == 0 else d["chunks"][k]
                store.upsert_chunk(cid, doc_id, k, text, 2, content_hash(text), t)
                events.append(("upsert", cid))
            d["slots"] = slots
        elif mtype == "delete":
            for k in range(CHUNKS_PER_DOC):
                cid = f"{doc_id}#c{k}"
                store.mark_deleted(cid, t)
                events.append(("delete", cid))
        # noop: nothing
    return events
