#!/usr/bin/env python3
"""Self-verifying spine (eval-design §7): reads ONLY frozen raw artifacts
(injection_manifest.json + arm_results.jsonl) and recomputes every headline
number into results/derived/paper_headline_numbers.json. Exit 0 required.
No number in the paper may exist outside this file.
"""
import json, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    manifest = json.loads((ROOT / "injection_manifest.json").read_text())
    results = [json.loads(l) for l in open(ROOT / "results" / "raw" / "arm_results.jsonl")]

    cls_of = {i["binding"]: i["class"] for i in manifest["injections"]}
    defective_ids = set(cls_of)
    clean_ids = set()
    for r in results:
        if r["binding"] not in defective_ids:
            clean_ids.add(r["binding"])

    per_class = defaultdict(lambda: defaultdict(lambda: {"injected": 0, "caught": 0}))
    fp = defaultdict(int)
    for inj in manifest["injections"]:
        per_class[inj["class"]]  # ensure class present
    for r in results:
        arm = r["arm"]
        if r["binding"] in defective_ids:
            cls = cls_of[r["binding"]]
            per_class[cls][arm]["injected"] += 1
            if r["flagged"]:
                per_class[cls][arm]["caught"] += 1
        elif r["flagged"]:
            fp[arm] += 1

    arms = sorted({r["arm"] for r in results})
    classes = sorted(per_class)
    table = {}
    for cls in classes:
        row = {}
        for arm in arms:
            d = per_class[cls][arm]
            if d["injected"]:
                row[arm] = {"recall": round(d["caught"] / d["injected"], 4),
                            "caught": d["caught"], "injected": d["injected"]}
        table[cls] = row

    n_clean = len(clean_ids)
    precision = {}
    for arm in arms:
        tp = sum(per_class[c][arm]["caught"] for c in classes)
        precision[arm] = {
            "true_catches": tp, "false_positives": fp[arm],
            "precision": round(tp / (tp + fp[arm]), 4) if tp + fp[arm] else None,
            "fpr_on_clean": round(fp[arm] / n_clean, 4) if n_clean else None,
        }

    # coverage (spec §4): share of claims bound to a resolvable source
    bindings_with_source = sum(1 for r in results if r["arm"] == "A_full")  # total
    n_unbound = len([i for i in manifest["injections"] if i["class"] == "I1"])
    total_claims = n_clean + len(manifest["injections"])
    coverage = round((total_claims - n_unbound) / total_claims, 4)

    def recall(cls, arm):
        return table.get(cls, {}).get(arm, {}).get("recall")

    out = {
        "frozen_inputs": ["injection_manifest.json", "results/raw/arm_results.jsonl"],
        "corpus": {"datasets": 6, "clean_claims": n_clean,
                   "injected_defects": len(manifest["injections"])},
        "coverage": coverage,
        "per_class_recall": table,
        "precision": precision,
        "headline": {
            "SC1_Layer1_N_class_recall": [recall("N1", "A_full"), recall("N3", "A_full")],
            "SC2_A_vs_B_on_S_class": {
                c: {"A": recall(c, "A_full"), "B": recall(c, "B_layer1_only")}
                for c in ["S1", "S2", "S3", "S4", "S5"]},
            "SC3_B_leaks_S_class": {
                c: recall(c, "B_layer1_only") for c in ["S1", "S2", "S3", "S4", "S5"]},
            "SC4_N2_quarantine_recall": recall("N2", "A_full"),
            "uncatchable_X1_X2_recall": {"X1": recall("X1", "A_full"),
                                          "X2": recall("X2", "A_full")},
        },
    }
    d = ROOT / "results" / "derived"
    d.mkdir(parents=True, exist_ok=True)
    (d / "paper_headline_numbers.json").write_text(json.dumps(out, indent=2))

    print(f"{'class':6s} " + " ".join(f"{a:>16s}" for a in arms))
    for cls in classes:
        print(f"{cls:6s} " + " ".join(
            f"{(table[cls].get(a) or {}).get('recall', float('nan')):>16.2f}" for a in arms))
    print("\nprecision:", json.dumps(precision, indent=2))
    print("coverage:", coverage)
    print(f"\nwrote {d/'paper_headline_numbers.json'}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
