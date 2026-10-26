#!/usr/bin/env python3
"""Live-arm spine: recomputes the live headline numbers from frozen raw artifacts
(provider usage JSON + runs.jsonl + reasoning_battery/*), plus the prompt-caching
breakdown. Nothing is typed by hand. Exit 0 only if all checks hold.
"""
import json, statistics, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "derived"


def main():
    rows = [json.loads(l) for l in open(ROOT / "results/raw/live/runs.jsonl")]
    valid = [r for r in rows if r.get("usage") and r.get("accuracy") is not None]
    per = {}
    for r in valid:
        k = (r["model"], r["scenario"], r["arm"])
        per.setdefault(k, []).append(r)

    summary, savings = {}, {}
    for (m, s, a), rs in sorted(per.items()):
        u = [r["usage"] for r in rs]
        pin = sorted({x.get("prompt_tokens") for x in u})
        summary[f"{m}|{s}|{a}"] = {
            "reps": len(rs),
            "prompt_tokens": pin[0] if len(pin) == 1 else pin,
            "cached_prompt_tokens": [x.get("cached_tokens", 0) or
                                     (x.get("prompt_tokens_details") or {}).get("cached_tokens", 0) for x in u],
            "accuracy_pass": sum(all((r.get("accuracy") or {}).values()) for r in rs),
        }
    for m in {r["model"] for r in valid}:
        try:
            raw = summary[f"{m}|S2|raw"]["prompt_tokens"]
            qaf = summary[f"{m}|S2|qafiya"]["prompt_tokens"]
            savings[m] = round(1 - qaf / raw, 4)
        except KeyError:
            pass

    # reasoning battery
    batt = []
    for f in sorted((ROOT / "results/raw/reasoning_battery").glob("*.json")):
        d = json.loads(f.read_text())
        m = d["choices"][0]
        batt.append({"file": f.name, "model": d["model"],
                     "finish_reason": m["finish_reason"],
                     "completion_tokens": d["usage"]["completion_tokens"],
                     "content_len": len(m["message"].get("content") or "")})
    big = [b for b in batt if "_big_" in b["file"]]
    assert big and all(b["finish_reason"] == "length" and b["content_len"] == 0 for b in big)

    out = {
        "frozen_inputs": ["results/raw/live/runs.jsonl", "results/raw/live/*.json",
                          "results/raw/reasoning_battery/*.json"],
        "S2_input_saving": savings,
        "per_config": summary,
        "reasoning_battery": {
            "n_big_calls": len(big),
            "all_big_exhausted_budget_without_answer": True,
            "note": "claim is scoped to exactly these frozen runs: 2 thinking-capable models × 2 calls on the large tabular S2-raw prompt, max_tokens=8000, reasoning enabled; both models answer the short control immediately (finish_reason=stop). Larger budgets untested.",
            "calls": batt,
        },
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "live_spine.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({"savings": savings,
                      "reasoning_big_calls": len(big),
                      "accuracy": {k: v["accuracy_pass"] for k, v in summary.items()}}, indent=2))
    print("wrote", OUT / "live_spine.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
