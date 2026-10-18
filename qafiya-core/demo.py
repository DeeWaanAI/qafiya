#!/usr/bin/env python3
"""The spec §9 worked example, as running code.

  1. seed the expenses dataset (Q2/Q3)
  2. model emits a view binding (Q3 total) + a claim binding ("fell 12% vs Q2")
  3. gate + semantic sweep -> PASS (data initially supports -12%)
  4. user edits a cell -> atomic write-back + history + transitive invalidation
  5. gate re-runs -> value PASS ... semantic FLAG: "recompute shows -8%, not -12%"
  6. quarantine the dataset -> the bindings FAIL by construction (N2 defense)

Run: python3 demo.py
"""
import shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from qafiya_core import engine, semantic, store

ROOT = Path(__file__).parent / "out" / "demo"
DATASET = "expenses"


def seed():
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ds = ROOT / "datasets" / DATASET
    ds.mkdir(parents=True)
    # Q2 sums to 1000, Q3 sums to 880  -> -12.0%, so the claim starts TRUE
    records = (
        [{"id": f"r_q2_{i}", "period": "Q2", "amount": a, "category": "travel"}
         for i, a in enumerate([400, 300, 200, 100])] +
        [{"id": f"r_q3_{i}", "period": "Q3", "amount": a, "category": "travel"}
         for i, a in enumerate([380, 260, 140, 100])]
    )
    store.atomic_write_jsonl(ds / store.DATA, records)
    bindings = [
        {  # view binding: the rendered Q3 total
            "id": "b_view_q3", "kind": "view",
            "target": {"view": "v_q3", "node": "cell:total"},
            "sources": [{"dataset": "ds:expenses", "filter": "period=Q3", "field": "amount"}],
            "derivation": "sum(amount) where period='Q3'",
            "value": 880.0, "statistic": "sum",
            "authoritative_artifact": "datasets/expenses/data.jsonl",
        },
        {  # claim binding: "Q3 spend fell 12% vs Q2"
            "id": "b_claim_trend", "kind": "claim",
            "target": {"view": "v_q3", "node": "text:trend"},
            "sources": [{"dataset": "ds:expenses", "field": "amount"}],
            "derivation": "sum(amount) where period='Q3'",
            "value": 880.0, "statistic": "sum",
            "authoritative_artifact": "datasets/expenses/data.jsonl",
            "assertion": {
                "statement": "Q3 spend fell 12% vs Q2",
                "predicate": "direction", "expected": -0.12, "tolerance": 0.005,
                "both_sides": {
                    "Q2": {"derivation": "sum(amount) where period='Q2'"},
                    "Q3": {"derivation": "sum(amount) where period='Q3'"},
                },
            },
        },
    ]
    engine.save_bindings(ROOT, bindings)


def main():
    print("— 1. seed dataset (Q2=1000, Q3=880 → claim 'fell 12%' is TRUE) —")
    seed()

    print("\n— 2. initial gate + semantic sweep —")
    assert engine.provenance_gate(ROOT) == 0
    assert semantic.semantic_sweep(ROOT) == 0
    print("[semantic] PASS — 'fell 12%' matches the data")

    print("\n— 3. user edits r_q3_0: 380 → 420 (Q3 now 920 → -8%) —")
    edit = {"id": "b_edit_1", "kind": "edit",
            "writeback": {"dataset": "ds:expenses", "record_id": "r_q3_0",
                          "field": "amount", "op": "set", "value": 420.0}}
    rec, n_invalidated = engine.apply_edit(ROOT, edit)
    print(f"write-back OK ({rec['id']}.amount = {rec['amount']}); "
          f"{n_invalidated} bindings marked PENDING (transitive invalidation)")

    print("\n— 4. view re-renders from data (values re-resolve), gate re-runs —")
    n = engine.refresh_values(ROOT)
    print(f"[render] {n} value caches re-resolved from current data (880 → 920)")
    assert engine.provenance_gate(ROOT) == 0, "values must still prove against source"
    flags = semantic.semantic_sweep(ROOT)
    claim = next(b for b in engine.load_bindings(ROOT) if b["id"] == "b_claim_trend")
    print(f"[semantic] {claim['check']['semantic']}: {claim['check'].get('detail')}")
    assert flags == 1 and claim["check"]["semantic"] == "FLAG"

    print("\n— 5. quarantine the dataset (SUPERSEDED) → bindings fail by construction —")
    store.supersede(ROOT, "datasets/expenses/data.jsonl")
    assert engine.provenance_gate(ROOT) == 1
    print("[gate] FAIL — quarantined source (N2 stale-version defense)")

    print("\n✓ §9 loop complete: PASS → edit → invalidate → recompute PASS → FLAG → quarantine FAIL")


if __name__ == "__main__":
    main()
