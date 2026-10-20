#!/usr/bin/env python3
"""Live backend run (efficiency-plan §2, cloud-API arm).

Two scenarios × two arms × N models × R reps, temperature 0:
  S1 single-doc : deck from expenses_large.csv  raw  vs  Qāfiya csv-serving
  S2 multi-doc  : travel deck over 6 datasets   raw-all vs Qāfiya selected records
Measured: provider usage tokens (frozen raw JSON per call), wall-clock, and a
mechanical accuracy check (correct ground-truth aggregates present in the deck).
Reads TOGETHER_AI_API_KEY from ../.env (never printed).
"""
import json, os, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT.parent / ".env"
MODELS = ["Qwen/Qwen3.5-9B", "meta-llama/Llama-3.3-70B-Instruct-Turbo"]
MAX_TOKENS = {"Qwen/Qwen3.5-9B": 24000}  # reasoning model needs budget to finish thinking
REPS = 3
API = "https://api.together.xyz/v1/chat/completions"


def load_key():
    for line in ENV.read_text().splitlines():
        if line.startswith("TOGETHER_AI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("TOGETHER_AI_API_KEY not found in .env")


def chat(key, model, prompt):
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": MAX_TOKENS.get(model, 8000),
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "User-Agent": "curl/8.0"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        payload = json.loads(r.read())
    return payload, time.time() - t0


def build_prompts():
    raw_tpl = (ROOT / "prompts" / "deck_raw.txt").read_text()
    data_tpl = (ROOT / "prompts" / "deck_data.txt").read_text()
    man = json.loads((ROOT / "corpus" / "manifest.json").read_text())
    tab = [d["file"] for d in man["docs"] if d["stratum"] == "tabular"]

    # S1
    s1_raw = raw_tpl.replace("{DOCUMENT}", (ROOT / "corpus" / "tabular/expenses_large.csv").read_text())
    q = ROOT / "qafiya" / "expenses_large"
    recs = [json.loads(l) for l in open(q / "data.jsonl")]
    for r in recs:
        r.pop("_prov", None)
    fields = ["id", "date", "amount", "category", "vendor"]
    csv_data = "\n".join([",".join(fields)] + [",".join(str(r[f]) for f in fields) for r in recs])
    s1_data = data_tpl.replace("{SCHEMA}", (q / "schema.json").read_text()).replace("{DATA}", csv_data)

    # S2 (travel across all datasets)
    raw_all = [ (ROOT / "corpus" / f).read_text() for f in tab ]
    sel = []
    for f in tab:
        for l in open(ROOT / "qafiya" / Path(f).stem / "data.jsonl"):
            r = json.loads(l)
            if r.get("category") == "travel":
                sel.append(r)
    fields2 = ["id", "date", "amount", "category", "vendor"]
    sel_csv = "\n".join([",".join(fields2)] + [",".join(str(r[f]) for f in fields2) for r in sel])
    s2_raw = raw_tpl.replace("{DOCUMENT}", "\n\n".join(raw_all)).replace(
        "Produce a 5-slide summary deck",
        "Produce a 5-slide summary deck FOCUSED ON TRAVEL EXPENSES")  # fairness: both arms know the topic (D5)
    s2_data = data_tpl.replace("{SCHEMA}", "filtered: category=travel across 6 datasets").replace(
        "Produce a 5-slide summary deck",
        "Produce a 5-slide summary deck FOCUSED ON TRAVEL EXPENSES").replace("{DATA}", sel_csv)
    return {"S1": {"raw": s1_raw, "qafiya": s1_data}, "S2": {"raw": s2_raw, "qafiya": s2_data}}


def ground_truth():
    """Correct aggregates the deck should state (computed from frozen corpus)."""
    man = json.loads((ROOT / "corpus" / "manifest.json").read_text())
    tab = [d["file"] for d in man["docs"] if d["stratum"] == "tabular"]
    travel = []
    for f in tab:
        for l in open(ROOT / "qafiya" / Path(f).stem / "data.jsonl"):
            r = json.loads(l)
            if r.get("category") == "travel":
                travel.append(float(r["amount"]))
    large = [json.loads(l) for l in open(ROOT / "qafiya" / "expenses_large" / "data.jsonl")]
    return {
        "S1": {"total": round(sum(float(r["amount"]) for r in large), 2)},
        "S2": {"travel_total": round(sum(travel), 2), "travel_n": len(travel)},
    }


def check(deck: str, gt: dict) -> dict:
    """Mechanical accuracy: is the correct total stated (any common rounding)?"""
    out = {}
    for k, v in gt.items():
        if isinstance(v, float):
            forms = {f"{v:.0f}", f"{v:,.0f}", f"{v:.2f}", f"{v:,.2f}"}
            out[k] = any(f in deck for f in forms)
    return out


def main():
    key = load_key()
    prompts = build_prompts()
    gt = ground_truth()
    out = ROOT / "results" / "raw" / "live"
    out.mkdir(parents=True, exist_ok=True)
    log = out / "runs.jsonl"
    for model in MODELS:
        mname = model.split("/")[-1]
        for scen, arms in prompts.items():
            for arm, prompt in arms.items():
                for rep in range(REPS):
                    rec = {"model": mname, "scenario": scen, "arm": arm, "rep": rep}
                    raw_file = out / f"{mname}_{scen}_{arm}_{rep}.json"
                    if raw_file.exists():
                        print(f"{mname} {scen} {arm} rep{rep}: cached")
                        continue
                    try:
                        payload, secs = chat(key, model, prompt)
                        msg = payload["choices"][0]["message"]
                        deck = msg.get("content") or msg.get("reasoning_content") or ""
                        rec.update({"usage": payload.get("usage"), "seconds": round(secs, 2),
                                    "accuracy": check(deck, gt[scen]), "deck_chars": len(deck)})
                        raw_file.write_text(
                            json.dumps({"request": {"model": model, "temperature": 0},
                                        "usage": payload.get("usage"), "deck": deck}, ensure_ascii=False, indent=1))
                    except Exception as e:
                        rec["error"] = str(e)[:200]
                    with open(log, "a") as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    print(f"{mname} {scen} {arm} rep{rep}: "
                          f"{rec.get('usage', {}).get('prompt_tokens', '?')} in-tokens, "
                          f"acc={rec.get('accuracy', rec.get('error'))}")
    print(f"\nfrozen raw -> {out}")


if __name__ == "__main__":
    main()
