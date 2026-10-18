"""End-to-end Qāfiya demo, fully deterministic (no model, no token):
  doc -> dataset -> bindings -> deck  ...  then a data edit that the gate CATCHES.

Run:  python3 -m qafiya.demo   (from qafiya_extract/)"""
import os
from .extract import import_csv, import_text
from .gate import load_dataset, agg, recompute_check, check_claim, transitive_invalidate, apply_edit, group_agg
from .render import render_deck

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = "ds:expenses"


def _view(derivation, value, filter_):
    return {"id": "b_view_food", "kind": "view", "derivation": derivation, "value": value,
            "statistic": "sum", "authoritative_artifact": "datasets/expenses/data.jsonl",
            "sources": [{"dataset": DS, "filter": filter_, "field": "amount"}]}


def _claim():
    return {"id": "b_claim_top", "kind": "claim", "sources": [{"dataset": DS}],
            "assertion": {"predicate": "superlative", "metric": "sum(amount) groupby category", "subject": "tools"}}


def run():
    src = os.path.join(BASE, "examples", "expenses.csv")
    out = os.path.join(BASE, "out", "expenses")
    notes = os.path.join(BASE, "examples", "notes.md")
    out_doc = os.path.join(BASE, "out", "notes")
    import_csv(src, out)
    import_text(notes, out_doc)
    schema, records = load_dataset(out)
    from .io import read_jsonl
    blocks = read_jsonl(os.path.join(out_doc, "blocks.jsonl"))

    view = _view("sum(amount) where category='food'", agg("sum(amount) where category='food'", records), "category='food'")
    claim = _claim()
    bindings = [view, claim]

    def status(view, claim, records):
        view["_status"] = recompute_check(view, records)
        claim["_status"] = check_claim(claim, records)

    print("STEP 1 — import: {} records, {} blocks; deck rendered".format(len(records), len(blocks)))
    status(view, claim, records)
    print("  before edit:  view={}  claim={}".format(view["_status"][0], claim["_status"][0]))
    render_deck(os.path.join(BASE, "out", "deck_before.html"), "Qāfiya — before edit",
                schema, records, blocks, bindings)

    # a user edits one food expense (500.00) — write-back to the record
    food = next(r for r in records if r.get("category") == "food")
    old = apply_edit(out, food["id"], "amount", 500.0)
    print("STEP 2 — edit record {}: {}.amount {} -> {}".format(food["id"], food["category"], old, 500.0))

    _, records = load_dataset(out)
    transitive_invalidate(DS, bindings)
    print("STEP 3 — transitive invalidation: bindings -> PENDING")
    status(view, claim, records)
    print("  after edit:   view={} ({})   claim={} ({})".format(
        view["_status"][0], view["_status"][1], claim["_status"][0], claim["_status"][1]))
    print("  group sums now:", group_agg("sum(amount) groupby category", records))
    render_deck(os.path.join(BASE, "out", "deck_after.html"), "Qāfiya — after edit (defects caught)",
                schema, records, blocks, bindings)
    print("STEP 4 — decks written: out/deck_before.html  out/deck_after.html")
    print("\nResult: the stale figure FAILs Layer 1 (proof); the now-false superlative FLAGs Layer 2 (check).")


if __name__ == "__main__":
    run()
