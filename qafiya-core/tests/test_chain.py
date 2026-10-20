#!/usr/bin/env python3
"""Tests for hash-chained history (spec v1.3)."""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from qafiya_core import chain, engine, store


class TestChain(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_append_and_verify(self):
        p = self.dir / "history.jsonl"
        chain.append(p, {"op": "set", "record": "r_1", "old": 1.0, "new": 2.0})
        chain.append(p, {"op": "set", "record": "r_2", "old": 5.0, "new": 6.0})
        ok, detail = chain.verify(p)
        self.assertTrue(ok, detail)

    def test_tamper_detected(self):
        p = self.dir / "history.jsonl"
        chain.append(p, {"op": "set", "record": "r_1", "old": 1.0, "new": 2.0})
        chain.append(p, {"op": "set", "record": "r_2", "old": 5.0, "new": 6.0})
        lines = p.read_text().splitlines()
        e = json.loads(lines[0]); e["new"] = 999.0
        lines[0] = json.dumps(e)
        p.write_text("\n".join(lines) + "\n")
        ok, _ = chain.verify(p)
        self.assertFalse(ok)

    def test_migrate_legacy(self):
        p = self.dir / "history.jsonl"
        p.write_text('{"op":"set","record":"r_9","old":0,"new":1}\n')
        self.assertEqual(chain.migrate(p), 1)
        ok, _ = chain.verify(p)
        self.assertTrue(ok)

    def test_store_append_history_is_chained(self):
        """store.append_history must produce chained, verifiable entries."""
        ds = self.dir / "datasets" / "expenses"
        ds.mkdir(parents=True)
        store.append_history(ds, {"op": "set", "record": "r_1", "new": 2.0})
        ok, detail = chain.verify(ds / store.HISTORY)
        self.assertTrue(ok, detail)


if __name__ == "__main__":
    unittest.main()
