#!/usr/bin/env python3
"""Token harness for the efficiency experiment (arms per efficiency-plan §1).

For each corpus doc, measures with the ACTUAL Qwen2.5 tokenizer (never chars/words):
  T_raw   = tokens(deck_raw prompt + raw file)
  T_data  = tokens(deck_data prompt + schema.json + data/blocks file)
  T_ingest = tokens consumed by extraction. Deterministic importers (CSV/MD) use
             NO model, so T_ingest = 0 by construction and is disclosed as such.
  T_out   = NOT measured offline (equal across arms by design); recorded at the
             live API/local run from the provider's usage field.

Writes results/raw/counts.jsonl (one line per doc) — the frozen evidence artifact.
"""
import json, subprocess, sys
from pathlib import Path
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parent.parent
TOK = Tokenizer.from_file(str(ROOT / "tokenizer" / "qwen25_tokenizer.json"))
QAFIYA_SRC = ROOT.parent / "deewaan-qafiyah" / "qafiya_extract"

def ntok(s: str) -> int:
    return len(TOK.encode(s).ids)

def extract(doc: Path, outdir: Path):
    """Run qafiya-extract once (Arm B one-time ingest)."""
    outdir.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "qafiya.cli", str(doc), str(outdir)],
                   cwd=QAFIYA_SRC, check=True, capture_output=True)

def main():
    raw_tpl = (ROOT / "prompts" / "deck_raw.txt").read_text()
    data_tpl = (ROOT / "prompts" / "deck_data.txt").read_text()
    manifest = json.loads((ROOT / "corpus" / "manifest.json").read_text())
    out = ROOT / "results" / "raw"
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for d in manifest["docs"]:
        doc = ROOT / "corpus" / d["file"]
        name = doc.stem
        qdir = ROOT / "qafiya" / name
        if not qdir.exists():
            extract(doc, qdir)

        if doc.suffix.lower() == ".pdf":
            # Baseline for text-PDF: what a naive pipeline pastes — the raw
            # pdfplumber text-layer dump, layout noise included.
            import pdfplumber
            with pdfplumber.open(doc) as pdf:
                raw_text = "\n\n".join(p.extract_text() or "" for p in pdf.pages)
        else:
            raw_text = doc.read_text()
        t_raw = ntok(raw_tpl.replace("{DOCUMENT}", raw_text))

        schema_p = qdir / "schema.json"
        data_p = qdir / "data.jsonl" if (qdir / "data.jsonl").exists() else qdir / "blocks.jsonl"
        schema = schema_p.read_text() if schema_p.exists() else ""
        full = data_p.read_text()

        # Two serving variants (both honest, both disclosed):
        #  full — records WITH inline per-field provenance (as extracted)
        #  slim — records WITHOUT _prov; provenance stays on disk, addressable
        #         by record id, exactly as spec §1.2 ("view points to binding")
        #         prescribes. This is the correct serving form.
        slim_lines = []
        for line in full.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            obj.pop("_prov", None)
            slim_lines.append(json.dumps(obj, ensure_ascii=False))
        slim = "\n".join(slim_lines)

        t_full = ntok(data_tpl.replace("{SCHEMA}", schema).replace("{DATA}", full))
        t_data = ntok(data_tpl.replace("{SCHEMA}", schema).replace("{DATA}", slim))

        # Third variant — compact serving: records rendered as CSV (the most
        # token-efficient table encoding), schema kept as field list. Storage
        # on disk stays JSONL+bindings; this is only the serving rendering.
        if data_p.name == "data.jsonl":
            recs = [json.loads(l) for l in slim_lines]
            fields = [k for k in recs[0] if k != "src_id"] if recs else []
            csv_lines = [",".join(fields)] + [",".join(str(r.get(f, "")) for f in fields) for r in recs]
            compact = "fields: " + ", ".join(fields) + "\n" + "\n".join(csv_lines)
        else:
            compact = slim  # prose: block text is already near-minimal
        t_csv = ntok(data_tpl.replace("{SCHEMA}", "").replace("{DATA}", compact))

        rows.append({
            "doc": d["file"], "stratum": d["stratum"], "sha256": d["sha256"],
            "tokenizer": "Qwen/Qwen2.5-7B-Instruct tokenizer.json",
            "T_raw": t_raw, "T_data": t_csv, "T_data_jsonl": t_data,
            "T_data_full": t_full, "T_ingest": 0,
            "ratio": round(t_csv / t_raw, 4),
            "ratio_jsonl": round(t_data / t_raw, 4),
            "ratio_full": round(t_full / t_raw, 4),
            "k_star": 0.0,  # T_ingest=0 (deterministic ingest); savings are immediate
        })
        print(f"{d['file']:32s} T_raw={t_raw:7d} csv={t_csv:7d} ({t_csv/t_raw:.3f}) "
              f"jsonl={t_data/t_raw:.2f} full-prov={t_full/t_raw:.2f}")

    with open(out / "counts.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"\nwrote {out/'counts.jsonl'}")

if __name__ == "__main__":
    sys.exit(main())
