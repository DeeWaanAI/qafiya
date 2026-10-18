#!/usr/bin/env python3
"""Inject labeled defects across the 11-class taxonomy (spec §3.2) plus the
two provably-uncatchable classes (spec §5), which are injected too and
reported honestly at ~0 expected recall.

Output: evaluated/ (corpus copy + bindings.jsonl mixing clean + defective claims)
        injection_manifest.json — FROZEN before any arm runs {binding, class, correct, injected}
"""
import copy, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT.parent / "qafiya-core"
sys.path.insert(0, str(CORE))
from qafiya_core import derivations, store  # noqa: E402

DATASETS = [f"dept_{i}" for i in range(6)]
PER_CLASS = 6


def main():
    eval_dir = ROOT / "evaluated"
    if eval_dir.exists():
        shutil.rmtree(eval_dir)
    shutil.copytree(ROOT / "corpus", eval_dir)
    clean = store.read_jsonl(ROOT / "clean" / "bindings.jsonl")
    by_id = {c["id"]: c for c in clean}
    defective, manifest = [], []

    def rec(binding, cls, note, correct, injected):
        defective.append(binding)
        manifest.append({"binding": binding["id"], "class": cls, "note": note,
                         "correct": correct, "injected": injected})

    for i, ds in enumerate(DATASETS[:PER_CLASS]):
        _, recs = store.load_dataset(ROOT / "corpus", ds)

        # N1 — number-not-in-data: value silently changed
        b = copy.deepcopy(by_id[f"c_val_q3_{ds}"]); b["id"] = f"N1_{ds}"
        true_v = b["value"]; b["value"] = round(true_v * 1.37, 2)
        b["assertion"]["expected"] = b["value"]
        rec(b, "N1", "value cannot be recomputed from sources", true_v, b["value"])

        # N2 — stale-version: sources a superseded artifact
        b = copy.deepcopy(by_id[f"c_val_travel_{ds}"]); b["id"] = f"N2_{ds}"
        b["authoritative_artifact"] = f"datasets/{ds}/archive/data_v1.jsonl"
        rec(b, "N2", "correct-looking value from a retired artifact",
            f"datasets/{ds}/data.jsonl", b["authoritative_artifact"])

        # N3 — hand-assembled cell: value = pooled total, derivation = subgroup
        b = copy.deepcopy(by_id[f"c_val_travel_{ds}"]); b["id"] = f"N3_{ds}"
        pooled = derivations.evaluate("sum(amount)", recs)
        sub = b["value"]; b["value"] = round(pooled, 2)
        b["assertion"]["expected"] = b["value"]
        rec(b, "N3", "wrong denominator: pooled total presented as subgroup",
            sub, b["value"])

        # S1 — reversed direction: expected sign flipped relative to the data
        b = copy.deepcopy(by_id[f"c_dir_{ds}"]); b["id"] = f"S1_{ds}"
        true_e = b["assertion"]["expected"]
        flipped = -true_e if true_e != 0 else 0.15
        b["assertion"]["expected"] = round(flipped, 4)
        word = "rose" if flipped > 0 else "fell"
        b["assertion"]["statement"] = f"travel spend in {ds} {word} {abs(flipped):.1%} in Q3"
        rec(b, "S1", "prose points the way data don't", true_e, b["assertion"]["expected"])

        # S2 — wrong label: statement says travel, derivation reads food (value
        # matches the WRONG slice, so Layer 1 passes; only the label check sees it)
        b = copy.deepcopy(by_id[f"c_val_travel_{ds}"]); b["id"] = f"S2_{ds}"
        der_food = b["derivation"].replace("travel", "food")
        b["derivation"] = der_food
        b["value"] = round(derivations.evaluate(der_food, recs), 2)
        b["assertion"]["expected"] = b["value"]
        # statement keeps saying "travel" and now quotes the FOOD number —
        # internally consistent, Layer-1-clean; only the label-vs-data check sees it
        b["assertion"]["statement"] = f"total travel spend in {ds} is {b['value']:.0f}"
        rec(b, "S2", "right number, wrong thing (label/category mismatch)",
            "category=travel", "category=food")

        # S4 — phantom analysis: cites a test artifact that was never deposited
        b = copy.deepcopy(by_id[f"c_val_q3_{ds}"]); b["id"] = f"S4_{ds}"
        b["assertion"]["statement"] = f"a seasonality test on {ds} confirms the trend"
        b["assertion"]["predicate"] = "existence"
        b["assertion"]["evidence_artifact"] = f"datasets/{ds}/analysis/seasonality.json"
        rec(b, "S4", "cites an analysis that was never run/deposited",
            "artifact must exist", b["assertion"]["evidence_artifact"])

        # S5 — exploratory-as-confirmed: cites an exploratory/failed analysis confidently
        b = copy.deepcopy(by_id[f"c_val_q3_{ds}"]); b["id"] = f"S5_{ds}"
        b["assertion"]["statement"] = f"anomaly analysis confirms {ds} is stable"
        b["assertion"]["predicate"] = "registry_status"
        b["assertion"]["analysis_id"] = "a_anomaly" if i % 2 == 0 else "a_forecast"
        rec(b, "S5", "exploratory/failed-gate result stated with confident voice",
            "status=confirmed required", b["assertion"]["analysis_id"])

        # I1 — unverifiable: no bound source
        b = copy.deepcopy(by_id[f"c_val_q3_{ds}"]); b["id"] = f"I1_{ds}"
        b["sources"] = []
        rec(b, "I1", "no bound source exists", "non-empty sources", "[]")

        # I2 — nothing to regenerate: required input/config absent
        b = copy.deepcopy(by_id[f"c_val_q3_{ds}"]); b["id"] = f"I2_{ds}"
        b["assertion"]["predicate"] = "reproducibility"
        b["assertion"]["requires"] = f"datasets/{ds}/config/forecast.yaml"
        rec(b, "I2", "inputs/configs absent — cannot regenerate",
            "config present", b["assertion"]["requires"])

        # X1 — PROVABLY UNREACHABLE: the data itself shares the error
        b = copy.deepcopy(by_id[f"c_val_q3_{ds}"]); b["id"] = f"X1_{ds}"
        rec(b, "X1", "claim and data share the same upstream error — coherence intact",
            "unknowable from inside", "unknowable from inside")

        # X2 — PROVABLY UNREACHABLE: drift below printed precision/tolerance
        b = copy.deepcopy(by_id[f"c_val_travel_{ds}"]); b["id"] = f"X2_{ds}"
        tiny = round(b["assertion"]["expected"] + 0.0001, 4)
        b["assertion"]["expected"] = tiny
        rec(b, "X2", "drift hidden below tolerance (rounding)",
            "exact value", tiny)

    # S3 — over-claim: 'every category fell' where at least one did not
    n_s3 = 0
    for ds in DATASETS:
        _, recs = store.load_dataset(ROOT / "corpus", ds)
        fell = {}
        for c in ("travel", "food", "tools"):
            v2 = derivations.evaluate(f"sum(amount) where period='Q2' and category='{c}'", recs)
            v3 = derivations.evaluate(f"sum(amount) where period='Q3' and category='{c}'", recs)
            fell[c] = v3 < v2
        if not all(fell.values()) and n_s3 < PER_CLASS:
            b = copy.deepcopy(by_id[f"c_scope_{ds}"]); b["id"] = f"S3_{ds}"
            b["assertion"]["statement"] = f"every category in {ds} fell in Q3"
            b["assertion"]["quantifier"] = "all"
            rec(b, "S3", "universal quantifier contradicted by a group",
                {k: v for k, v in fell.items()}, "claims all fell")
            n_s3 += 1

    # quarantine the retired artifacts so N2 fires structurally
    for ds in DATASETS[:PER_CLASS]:
        store.supersede(eval_dir, f"datasets/{ds}/archive/data_v1.jsonl")

    allb = clean + defective
    store.atomic_write_jsonl(eval_dir / "bindings.jsonl", allb)
    (ROOT / "injection_manifest.json").write_text(json.dumps({
        "frozen": "2026-10-15", "seed": 20261015,
        "n_clean": len(clean), "n_defective": len(defective),
        "expected_uncatchable": ["X1", "X2"], "injections": manifest,
    }, indent=2))
    print(f"injected {len(defective)} defects over {len(clean)} clean claims; manifest frozen")


if __name__ == "__main__":
    main()
