"""Tests for qafiya-extract provenance + value-in-span proof. Stdlib unittest (no deps).
Run:  python -m unittest discover -s tests   (from the qafiya_extract/ dir)"""
import os, sys, json, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qafiya.extract import import_csv, import_text
from qafiya.validate import validate_dataset, validate_document
from qafiya.io import read_text, atomic_write_text, read_jsonl, write_jsonl


class TestCsv(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.src = os.path.join(self.d, "exp.csv")
        atomic_write_text(self.src, "date,amount,category\n2026-07-05,42.00,travel\n2026-08-19,33.75,food\n")
        self.out = os.path.join(self.d, "out", "exp")

    def test_import_and_validate(self):
        s = import_csv(self.src, self.out)
        self.assertEqual(s["records"], 2)
        ok, issues = validate_dataset(self.out)
        self.assertTrue(ok, issues)

    def test_typed_coercion(self):
        import_csv(self.src, self.out)
        recs = read_jsonl(os.path.join(self.out, "data.jsonl"))
        self.assertEqual(recs[0]["amount"], 42.0)          # number, not string
        self.assertIsInstance(recs[0]["amount"], float)
        self.assertEqual(recs[0]["category"], "travel")    # string

    def test_value_in_span_catches_silent_edit(self):
        import_csv(self.src, self.out)
        dp = os.path.join(self.out, "data.jsonl")
        recs = read_jsonl(dp)
        recs[0]["amount"] = 999.0                          # tamper without touching source
        write_jsonl(dp, recs)
        ok, issues = validate_dataset(self.out)
        self.assertFalse(ok)
        self.assertTrue(any("value != source" in str(i) for i in issues))

    def test_non_destructive(self):
        before = read_text(self.src)
        import_csv(self.src, self.out)
        self.assertEqual(read_text(self.src), before)      # original never modified
        self.assertTrue(os.path.exists(os.path.join(self.out, "source", "exp.csv")))


class TestText(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.src = os.path.join(self.d, "n.md")
        atomic_write_text(self.src, "# Title\n\nA paragraph here.\n\n- one\n- two\n")
        self.out = os.path.join(self.d, "out", "n")

    def test_blocks_and_validate(self):
        s = import_text(self.src, self.out)
        self.assertGreaterEqual(s["blocks"], 3)            # heading, paragraph, list
        ok, issues = validate_document(self.out)
        self.assertTrue(ok, issues)

    def test_span_exact(self):
        import_text(self.src, self.out)
        blocks = read_jsonl(os.path.join(self.out, "blocks.jsonl"))
        src = read_text(os.path.join(self.out, "source", "n.md"))
        for b in blocks:
            self.assertEqual(src[b["_prov"]["start"]:b["_prov"]["end"]], b["content"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
