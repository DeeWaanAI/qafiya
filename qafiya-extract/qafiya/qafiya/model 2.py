"""Qāfiya data model (spec v1.1 §1-2). Lightweight dicts + constructors.

Provenance-at-birth: every extracted field/block carries an `_prov` pointing at the
exact span in the frozen source copy it came from, so the value-in-span check (validate.py)
can prove it — this is the ingestion-time form of Layer 1 (the deterministic proof)."""
from .io import make_id


def new_record(fields: dict, prov: dict) -> dict:
    """fields: typed values; prov: {field: {doc,row,column,verbatim}}."""
    rec = {"id": make_id("r")}
    rec.update(fields)
    rec["_prov"] = prov
    return rec


def new_block(btype: str, content: str, prov: dict) -> dict:
    """prose block; prov: {doc,start,end,verbatim}."""
    return {"id": make_id("blk"), "type": btype, "content": content, "_prov": prov}


def new_value_binding(dataset: str, derivation: str, sources: list, value,
                      statistic: str = "n/a", device: str = "n/a",
                      artifact: str = "") -> dict:
    """A render-source binding (spec §2 job 1): value MUST equal eval(derivation, sources)."""
    return {
        "id": make_id("b"),
        "kind": "view",
        "target": {"dataset": dataset, "node": derivation},
        "sources": sources,
        "derivation": derivation,
        "value": value,
        "statistic": statistic,
        "device": device,
        "authoritative_artifact": artifact,
        "superseded_by": [],
    }


def new_claim_binding(statement: str, predicate: str, expected, sources: list,
                      both_sides: dict = None, tolerance: float = 0.0) -> dict:
    """An audit-pointer binding (spec §2 job 3): a claim bound to its evidence."""
    return {
        "id": make_id("b"),
        "kind": "claim",
        "sources": sources,
        "assertion": {
            "statement": statement,
            "predicate": predicate,   # one of the 11 classes' predicates (spec §3.2)
            "expected": expected,
            "tolerance": tolerance,
            "both_sides": both_sides or {},
        },
    }
