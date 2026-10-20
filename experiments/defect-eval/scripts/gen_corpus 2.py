#!/usr/bin/env python3
"""Generate the frozen defect-injection corpus: 6 datasets + a pool of
known-correct claims (bindings) that the injector will corrupt per class.

Deterministic (seeded). Writes corpus/ + clean/bindings.jsonl + manifest.
"""
import hashlib, json, random, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT.parent / "qafiya-core"
sys.path.insert(0, str(CORE))
from qafiya_core import derivations, store  # noqa: E402

SEED = 20261015
PERIODS = ["Q2", "Q3"]
CATS = ["travel", "food", "tools"]


def gen_dataset(rng, name):
    ds = ROOT / "corpus" / "datasets" / name
    ds.mkdir(parents=True, exist_ok=True)
    recs = []
    i = 0
    for p in PERIODS:
        for c in CATS:
            for _ in range(rng.randint(3, 6)):
                # Q3 deliberately lower for travel in most datasets (true trends)
                base = rng.uniform(20, 400)
                if c == "travel" and p == "Q3":
                    base *= 0.8
                recs.append({"id": f"{name}_r{i}", "period": p, "category": c,
                             "amount": round(base, 2)})
                i += 1
    store.atomic_write_jsonl(ds / store.DATA, recs)
    return recs


def claim_bidirectional(ds, name):
    """A correct direction claim for travel spend Q2→Q3."""
    der2, der3 = ("sum(amount) where period='Q2' and category='travel'",
                  "sum(amount) where period='Q3' and category='travel'")
    _, recs = store.load_dataset(ROOT / "corpus", name)
    v2, v3 = derivations.evaluate(der2, recs), derivations.evaluate(der3, recs)
    change = (v3 - v2) / v2
    return {
        "id": f"c_dir_{name}", "kind": "claim", "dataset": name,
        "sources": [{"dataset": f"ds:{name}", "field": "amount"}],
        "derivation": der3, "value": round(v3, 2), "statistic": "sum",
        "authoritative_artifact": f"datasets/{name}/data.jsonl",
        "assertion": {
            "statement": f"travel spend in {name} moved {change:+.1%} from Q2 to Q3",
            "predicate": "direction", "expected": round(change, 4), "tolerance": 0.005,
            "both_sides": {"Q2": {"derivation": der2}, "Q3": {"derivation": der3}},
        },
    }


def claim_value(ds, name, field_filter, label):
    der = f"sum(amount) where {field_filter}"
    _, recs = store.load_dataset(ROOT / "corpus", name)
    v = derivations.evaluate(der, recs)
    return {
        "id": f"c_val_{label}_{name}", "kind": "claim", "dataset": name,
        "sources": [{"dataset": f"ds:{name}", "field": "amount"}],
        "derivation": der, "value": round(v, 2), "statistic": "sum",
        "authoritative_artifact": f"datasets/{name}/data.jsonl",
        "assertion": {"statement": f"total {label} spend in {name} is {v:.0f}",
                      "predicate": "value", "expected": round(v, 2), "tolerance": 0.5},
    }


def claim_scope(ds, name):
    """'All categories fell' — checked by per-group enumeration."""
    _, recs = store.load_dataset(ROOT / "corpus", name)
    sides = {}
    n_fell = 0
    for c in CATS:
        d2 = f"sum(amount) where period='Q2' and category='{c}'"
        d3 = f"sum(amount) where period='Q3' and category='{c}'"
        v2, v3 = derivations.evaluate(d2, recs), derivations.evaluate(d3, recs)
        sides[c] = {"Q2": {"derivation": d2}, "Q3": {"derivation": d3}}
        if v3 < v2:
            n_fell += 1
    # the CLEAN claim must state the truth — the checker verifies it
    if n_fell == len(CATS):
        stmt, quant = f"every category in {name} fell in Q3", "all"
    elif n_fell > len(CATS) / 2:
        stmt, quant = f"most categories in {name} fell in Q3", "most"
    else:
        stmt, quant = f"several categories in {name} rose in Q3", "some"
    return {
        "id": f"c_scope_{name}", "kind": "claim", "dataset": name,
        "sources": [{"dataset": f"ds:{name}", "field": "amount"}],
        "derivation": "sum(amount) where period='Q3'",
        "value": round(derivations.evaluate("sum(amount) where period='Q3'", recs), 2),
        "statistic": "sum",
        "authoritative_artifact": f"datasets/{name}/data.jsonl",
        "assertion": {"statement": stmt, "predicate": "scope", "quantifier": quant,
                      "per_group": sides, "group_field": "category",
                      "_true_answer": n_fell},
    }


def main():
    rng = random.Random(SEED)
    if (ROOT / "corpus").exists():
        shutil.rmtree(ROOT / "corpus")
    if (ROOT / "clean").exists():
        shutil.rmtree(ROOT / "clean")
    (ROOT / "clean").mkdir(parents=True)

    datasets, claims, files = [], [], []
    for i in range(6):
        name = f"dept_{i}"
        recs = gen_dataset(rng, name)
        datasets.append(name)
        p = ROOT / "corpus" / "datasets" / name / store.DATA
        files.append({"dataset": name, "records": len(recs),
                      "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
        claims.append(claim_bidirectional(None, name))
        claims.append(claim_value(None, name, "category='travel'", "travel"))
        claims.append(claim_value(None, name, "period='Q3'", "q3"))
        claims.append(claim_scope(None, name))

    # an analysis registry for S5 (exploratory results must not sound confirmed)
    registry = [{"analysis_id": "a_seasonality", "dataset": "dept_0", "status": "confirmed"},
                {"analysis_id": "a_anomaly", "dataset": "dept_1", "status": "exploratory"},
                {"analysis_id": "a_forecast", "dataset": "dept_2", "status": "failed_gate"}]
    (ROOT / "corpus" / "registry.json").write_text(json.dumps(registry, indent=2))

    for c in claims:
        c["assertion"].pop("_true_answer", None)
    store.atomic_write_jsonl(ROOT / "clean" / "bindings.jsonl", claims)
    manifest = {"seed": SEED, "frozen": "2026-10-15", "datasets": files,
                "n_clean_claims": len(claims)}
    (ROOT / "corpus" / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"corpus: {len(datasets)} datasets, {len(claims)} clean claims")


if __name__ == "__main__":
    main()
