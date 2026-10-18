#!/usr/bin/env python3
"""H3 scenario — selective loading over a multi-doc corpus.

Scenario: "make a deck about TRAVEL spend" across the whole tabular corpus.
  Baseline (direct): must stuff ALL raw documents into context.
  Qāfiya: schema-guided filter (category='travel') over the datasets,
          serve ONLY the relevant records, compact CSV rendering.

This is where the substrate should win (efficiency-plan §5 H3): structured
data allows selective loading; the baseline pays full context or hits the ceiling.
Writes results/raw/selective.json.
"""
import json, sys
from pathlib import Path
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parent.parent
TOK = Tokenizer.from_file(str(ROOT / "tokenizer" / "qwen25_tokenizer.json"))
QUERY_CATEGORY = "travel"

def ntok(s): return len(TOK.encode(s).ids)

def main():
    raw_tpl = (ROOT / "prompts" / "deck_raw.txt").read_text()
    data_tpl = (ROOT / "prompts" / "deck_data.txt").read_text()
    manifest = json.loads((ROOT / "corpus" / "manifest.json").read_text())
    tabular = [d for d in manifest["docs"] if d["stratum"] == "tabular"]

    raw_all, sel_records, fields = [], [], None
    for d in tabular:
        raw_all.append((ROOT / "corpus" / d["file"]).read_text())
        data_p = ROOT / "qafiya" / Path(d["file"]).stem / "data.jsonl"
        for line in data_p.read_text().splitlines():
            r = json.loads(line)
            if r.get("category") == QUERY_CATEGORY:
                r.pop("_prov", None); r.pop("src_id", None)
                fields = fields or list(r.keys())
                sel_records.append(r)

    t_baseline = ntok(raw_tpl.replace("{DOCUMENT}", "\n\n".join(raw_all)))
    compact = "\n".join([",".join(fields)] +
                        [",".join(str(r.get(f, "")) for f in fields) for r in sel_records])
    t_qafiya = ntok(data_tpl.replace("{SCHEMA}", f"filtered: category={QUERY_CATEGORY}")
                            .replace("{DATA}", compact))

    out = {
        "scenario": f"deck about '{QUERY_CATEGORY}' spend across {len(tabular)} datasets",
        "n_docs": len(tabular), "n_selected_records": len(sel_records),
        "T_baseline_all_docs": t_baseline,
        "T_qafiya_selected": t_qafiya,
        "ratio": round(t_qafiya / t_baseline, 4),
        "saving": f"{(1 - t_qafiya / t_baseline) * 100:.1f}%",
        "note": "saving grows with corpus size and query selectivity (H3)",
    }
    (ROOT / "results" / "raw" / "selective.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    sys.exit(main())
