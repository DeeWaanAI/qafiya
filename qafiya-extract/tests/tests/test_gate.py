"""Tests for the Layer-1 gate + render. Stdlib unittest. Run: python -m unittest discover -s tests"""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qafiya.extract import import_csv
from qafiya.gate import (load_dataset, agg, group_agg, recompute_check, check_claim,
                         transitive_invalidate, apply_edit)
from qafiya.render import render_deck
from qafiya.io import read_text, atomic_write_text


CSV = "date,amount,category\n2026-07-05,42.00,travel\n2026-08-02,120.00,tools\n2026-08-19,33.75,food\n"


class Gate(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.src = os.path.join(self.d, "e.csv")
        atomic_write_text(self.src, CSV)
        self.out = os.path.join(self.d, "out")
        import_csv(self.src, self.out)
        self.schema, self.records = load_dataset(self.out)

    def test_agg_and_group(self):
        self.assertAlmostEqual(agg("sum(amount) where category='travel'", self.records), 42.0)
        self.assertAlmostEqual(agg("sum(amount)", self.records), 195.75)
        g = group_agg("sum(amount) groupby category", self.records)
        self.assertEqual(g["tools"], 120.0)

    def test_recompute_pass_then_fail(self):
        b = {"derivation": "sum(amount) where category='tools'", "value": 120.0, "tolerance": 1e-6}
        self.assertEqual(recompute_check(b, self.records)[0], "PASS")
        b["value"] = 999.0
        self.assertEqual(recompute_check(b, self.records)[0], "FAIL")

    def test_superlative_pass_then_flag(self):
        a = {"predicate": "superlative", "metric": "sum(amount) groupby category", "subject": "tools"}
        self.assertEqual(check_claim({"assertion": a}, self.records)[0], "PASS")
        rec = next(r for r in self.records if r["category"] == "food")
        apply_edit(self.out, rec["id"], "amount", 500.0)
        _, recs = load_dataset(self.out)
        self.assertEqual(check_claim({"assertion": a}, recs)[0], "FLAG")

    def test_invalidate_sets_pending(self):
        b = {"sources": [{"dataset": "ds:e"}], "check": {"provenance": "PASS"}}
        transitive_invalidate("ds:e", [b])
        self.assertEqual(b["check"]["provenance"], "PENDING")

    def test_edit_writes_history(self):
        rec = next(r for r in self.records if r["category"] == "travel")
        old = apply_edit(self.out, rec["id"], "amount", 7.0)
        self.assertEqual(old, 42.0)
        self.assertIn('"new": 7.0', read_text(os.path.join(self.out, "history.jsonl")))


class Render(unittest.TestCase):
    def test_deck_has_provenance(self):
        d = tempfile.mkdtemp(); src = os.path.join(d, "e.csv"); atomic_write_text(src, CSV)
        out = os.path.join(d, "out"); import_csv(src, out)
        schema, records = load_dataset(out)
        html_path = os.path.join(d, "deck.html")
        render_deck(html_path, "t", schema, records, None, [])
        h = read_text(html_path)
        self.assertIn('data-prov=', h)
        self.assertIn("travel", h)


if __name__ == "__main__":
    unittest.main(verbosity=2)
