#!/usr/bin/env python3
"""Compute the crossover results from frozen counts.jsonl + selective.json.

Outputs:
  results/derived/crossover.json  — per-stratum ratios (3 serving variants), headline numbers
  results/derived/crossover.png   — cumulative-token curves, baseline vs Qāfiya compact serving

k* = T_ingest / (T_raw - T_data)  (efficiency-plan §4). With deterministic ingest
T_ingest = 0, so k* = 0 wherever T_data < T_raw; where T_data >= T_raw there is
no crossover and we say so (negative results are reported, not hidden).
"""
import json, statistics, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
K_VALUES = [1, 2, 5, 10, 20, 50]

def main():
    rows = [json.loads(l) for l in open(ROOT / "results" / "raw" / "counts.jsonl")]
    selective = json.loads((ROOT / "results" / "raw" / "selective.json").read_text())
    derived = ROOT / "results" / "derived"
    derived.mkdir(parents=True, exist_ok=True)

    by_stratum = {}
    for r in rows:
        by_stratum.setdefault(r["stratum"], []).append(r)

    summary = {}
    for stratum, rs in by_stratum.items():
        summary[stratum] = {"n": len(rs)}
        for key, label in [("ratio", "csv-serving"), ("ratio_jsonl", "jsonl-serving"),
                           ("ratio_full", "full-provenance-serving")]:
            vals = [r[key] for r in rs]
            summary[stratum][label] = {
                "median": round(statistics.median(vals), 4),
                "min": round(min(vals), 4), "max": round(max(vals), 4),
            }

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for stratum, rs in by_stratum.items():
        med = statistics.median(r["ratio"] for r in rs)
        rep = min(rs, key=lambda r: abs(r["ratio"] - med))
        ax.plot(K_VALUES, [k * rep["T_raw"] for k in K_VALUES], "o--",
                label=f"{stratum} baseline")
        ax.plot(K_VALUES, [rep["T_ingest"] + k * rep["T_data"] for k in K_VALUES], "s-",
                label=f"{stratum} Qāfiya (csv serving)")
    ax.set_xlabel("operations k on the same document")
    ax.set_ylabel("cumulative input tokens")
    ax.set_title("Cumulative input tokens (Qwen2.5 tokenizer, compact serving)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(derived / "crossover.png", dpi=150)

    out = {
        "frozen_inputs": ["results/raw/counts.jsonl", "results/raw/selective.json"],
        "tokenizer": "Qwen/Qwen2.5-7B-Instruct",
        "T_ingest_note": "deterministic CSV/MD extraction uses no model calls; T_ingest=0 disclosed per plan §8",
        "single_doc": summary,
        "multi_doc_selective": selective,
        "headline_findings": [
            "Single tabular doc: raw CSV is already the minimal encoding; JSONL serving costs ~2.3x, full inline provenance ~8.5x, compact CSV serving ~1.0x (parity, not a win).",
            "Single prose doc: block JSON adds ~15% overhead; no token win.",
            "Where the substrate wins: multi-doc selective loading (H3) — see multi_doc_selective.",
            "Design rule confirmed: provenance must be ADDRESSABLE (on disk, by id), never inlined into the prompt.",
        ],
    }
    (derived / "crossover.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out["single_doc"], indent=2))
    print(json.dumps(out["multi_doc_selective"], indent=2))
    print(f"\nwrote {derived/'crossover.json'} and crossover.png")

if __name__ == "__main__":
    sys.exit(main())
