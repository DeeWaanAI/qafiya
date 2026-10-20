#!/usr/bin/env python3
"""Selective loading over DOCUMENTS (prose md + text-PDF strata).

Scenario: "deck about travel" across all prose+PDF documents.
  Baseline: stuff ALL raw documents into context.
  Qāfiya: block-level filter (blocks whose text mentions the topic) across
          all extracted documents — serve only those blocks.
Documents select at block granularity; datasets select at record granularity.
Writes results/raw/selective_docs.json.
"""
import json, re, sys
from pathlib import Path
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parent.parent
TOK = Tokenizer.from_file(str(ROOT / "tokenizer" / "qwen25_tokenizer.json"))
TOPIC = "travel"

def ntok(s): return len(TOK.encode(s).ids)

def raw_text_of(doc: Path) -> str:
    if doc.suffix.lower() == ".pdf":
        import pdfplumber
        with pdfplumber.open(doc) as pdf:
            return "\n\n".join(p.extract_text() or "" for p in pdf.pages)
    return doc.read_text()

def main():
    raw_tpl = (ROOT / "prompts" / "deck_raw.txt").read_text()
    data_tpl = (ROOT / "prompts" / "deck_data.txt").read_text()
    manifest = json.loads((ROOT / "corpus" / "manifest.json").read_text())
    docs = [d for d in manifest["docs"] if d["stratum"] in ("prose", "pdf")]

    raw_all, sel_blocks, n_blocks = [], [], 0
    for d in docs:
        doc = ROOT / "corpus" / d["file"]
        raw_all.append(raw_text_of(doc))
        blocks_p = ROOT / "qafiya" / doc.stem / "blocks.jsonl"
        for line in blocks_p.read_text().splitlines():
            b = json.loads(line)
            n_blocks += 1
            if re.search(rf"\b{TOPIC}\b", b["content"], re.I):
                sel_blocks.append(b["content"])

    t_baseline = ntok(raw_tpl.replace("{DOCUMENT}", "\n\n".join(raw_all)))
    t_qafiya = ntok(data_tpl.replace("{SCHEMA}", f"block filter: topic={TOPIC}")
                            .replace("{DATA}", "\n\n".join(sel_blocks)))

    out = {
        "scenario": f"deck about '{TOPIC}' across {len(docs)} documents (prose + text-PDF)",
        "n_docs": len(docs), "n_blocks_total": n_blocks, "n_blocks_selected": len(sel_blocks),
        "T_baseline_all_docs": t_baseline,
        "T_qafiya_selected_blocks": t_qafiya,
        "ratio": round(t_qafiya / t_baseline, 4),
        "saving": f"{(1 - t_qafiya / t_baseline) * 100:.1f}%",
        "note": "documents select at block granularity; saving grows with corpus size and topic selectivity",
    }
    (ROOT / "results" / "raw" / "selective_docs.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    sys.exit(main())
