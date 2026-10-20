#!/usr/bin/env python3
"""Unit tests for qafiya-core — each maps to a spec §7 invariant."""
import shutil, tempfile, unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qafiya_core import derivations, engine, semantic, store


def make_store(root: Path):
    ds = root / "datasets" / "expenses"
    ds.mkdir(parents=True)
    store.atomic_write_jsonl(ds / store.DATA, [
        {"id": "r_1", "period": "Q2", "amount": 500.0},
        {"id": "r_2", "period": "Q2", "amount": 500.0},
        {"id": "r_3", "period": "Q3", "amount": 880.0},
    ])
    engine.save_bindings(root, [{
        "id": "b_v", "kind": "view",
        "sources": [{"dataset": "ds:expenses", "filter": "period=Q3", "field": "amount"}],
        "derivation": "sum(amount) where period='Q3'", "value": 880.0,
        "authoritative_artifact": "datasets/expenses/data.jsonl",
    }])


class Base(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        make_store(self.root)

    def tearDown(self):
        shutil.rmtree(self.root)


class TestDerivations(unittest.TestCase):
    def test_closed_set(self):
        with self.assertRaises(derivations.DerivationError):
            derivations.parse("median(x)")          # not in the closed set
        with self.assertRaises(derivations.DerivationError):
            derivations.parse("sum(x); DROP TABLE")  # injection rejected
        with self.assertRaises(derivations.DerivationError):
            derivations.parse("sum(x) where a=1")    # unquoted value rejected

    def test_empty_selection_raises(self):
        with self.assertRaises(derivations.DerivationError):
            derivations.evaluate("sum(amount) where period='Q9'", [])


class TestEngine(Base):
    def test_gate_pass_and_fail(self):  # invariant 3
        self.assertEqual(engine.provenance_gate(self.root), 0)
        b = engine.load_bindings(self.root)[0]
        b["value"] = 999.0
        engine.save_bindings(self.root, [b])
        self.assertEqual(engine.provenance_gate(self.root), 1)

    def test_atomic_writeback_and_history(self):  # invariants 7, §6
        edit = {"id": "b_e", "kind": "edit",
                "writeback": {"dataset": "ds:expenses", "record_id": "r_3",
                              "field": "amount", "op": "set", "value": 480.0}}
        rec, n = engine.apply_edit(self.root, edit)
        self.assertEqual(rec["amount"], 480.0)
        self.assertEqual(n, 1)  # the Q3-sum binding depends on r_3 -> PENDING
        hist = store.read_jsonl(self.root / "datasets" / "expenses" / store.HISTORY)
        self.assertEqual(hist[0]["prior"], 880.0)  # prior state retained

    def test_transitive_invalidation(self):  # §6
        edit = {"id": "b_e", "kind": "edit",
                "writeback": {"dataset": "ds:expenses", "record_id": "r_1",
                              "field": "amount", "op": "set", "value": 1.0}}
        _, n = engine.apply_edit(self.root, edit)
        self.assertEqual(n, 0)  # r_1 is Q2; the Q3 binding does NOT depend on it
        b = engine.load_bindings(self.root)[0]
        self.assertNotEqual(b.get("check", {}).get("provenance"), "PENDING")

    def test_quarantine_fails_by_construction(self):  # invariant 5
        store.supersede(self.root, "datasets/expenses/data.jsonl")
        self.assertEqual(engine.provenance_gate(self.root), 1)

    def test_refresh_then_gate(self):
        edit = {"id": "b_e", "kind": "edit",
                "writeback": {"dataset": "ds:expenses", "record_id": "r_3",
                              "field": "amount", "op": "set", "value": 480.0}}
        engine.apply_edit(self.root, edit)
        self.assertEqual(engine.provenance_gate(self.root), 1)  # stale cache FAILs
        self.assertEqual(engine.refresh_values(self.root), 1)
        self.assertEqual(engine.provenance_gate(self.root), 0)  # re-resolved PASSes


class TestSemantic(Base):
    def test_direction_flag(self):  # §3.2 S1
        engine.save_bindings(self.root, [{
            "id": "b_c", "kind": "claim",
            "sources": [{"dataset": "ds:expenses", "field": "amount"}],
            "derivation": "sum(amount) where period='Q3'", "value": 880.0,
            "assertion": {"statement": "Q3 fell 12% vs Q2", "predicate": "direction",
                          "expected": -0.12, "tolerance": 0.005,
                          "both_sides": {"Q2": {"derivation": "sum(amount) where period='Q2'"},
                                         "Q3": {"derivation": "sum(amount) where period='Q3'"}}},
        }])
        self.assertEqual(semantic.semantic_sweep(self.root), 0)  # -12% is true: PASS
        edit = {"id": "b_e", "kind": "edit",
                "writeback": {"dataset": "ds:expenses", "record_id": "r_3",
                              "field": "amount", "op": "set", "value": 950.0}}
        engine.apply_edit(self.root, edit)
        self.assertEqual(semantic.semantic_sweep(self.root), 1)  # now -5%: FLAG
        b = engine.load_bindings(self.root)[0]
        self.assertEqual(b["check"]["semantic"], "FLAG")

    def test_causal_never_autopasses(self):  # R6
        engine.save_bindings(self.root, [{
            "id": "b_x", "kind": "claim",
            "sources": [{"dataset": "ds:expenses", "field": "amount"}],
            "derivation": "sum(amount) where period='Q3'", "value": 880.0,
            "assertion": {"statement": "remote work caused the drop", "predicate": "causal"},
        }])
        semantic.semantic_sweep(self.root)
        b = engine.load_bindings(self.root)[0]
        self.assertEqual(b["check"]["semantic"], "PENDING")  # human judgment, never PASS


if __name__ == "__main__":
    unittest.main()
