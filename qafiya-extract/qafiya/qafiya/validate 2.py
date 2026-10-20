"""Value-in-span validation — the ingestion-time Layer 1 (deterministic proof, spec §3.1).

Re-opens the frozen source copy and proves every extracted field/block still equals the
exact span it claims. A mismatch is a bug or a silent edit, not a caveat."""
import os, json
from .io import read_text, read_jsonl, parse_csv_rows
from .schema import coerce


def validate_dataset(out_dir: str):
    schema = json.loads(read_text(os.path.join(out_dir, "schema.json")))
    records = read_jsonl(os.path.join(out_dir, "data.jsonl"))
    src_rel = schema["source"]["path"]  # e.g. source/expenses.csv (relative to out_dir)
    rows = parse_csv_rows(read_text(os.path.join(out_dir, src_rel)))
    header = [h.strip() for h in rows[0]]
    data = rows[1:]
    issues = []
    for rec in records:
        for field, prov in rec.get("_prov", {}).items():
            col = prov["column"]
            if col not in header:
                issues.append((rec["id"], field, "column not in source header")); continue
            cidx = header.index(col)
            ridx = prov["row"]
            if ridx >= len(data) or cidx >= len(data[ridx]):
                issues.append((rec["id"], field, "span out of range")); continue
            cell = data[ridx][cidx]
            if cell != prov["verbatim"]:
                issues.append((rec["id"], field, f"verbatim drift: source={cell!r} prov={prov['verbatim']!r}"))
                continue
            expected = coerce(cell, schema["fields"].get(field, "string"))
            if rec.get(field) != expected:
                issues.append((rec["id"], field, f"value != source: rec={rec.get(field)!r} source={expected!r}"))
    return (len(issues) == 0), issues


def validate_document(out_dir: str):
    meta = json.loads(read_text(os.path.join(out_dir, "doc.json")))
    blocks = read_jsonl(os.path.join(out_dir, "blocks.jsonl"))
    src = read_text(os.path.join(out_dir, meta["source"]["path"]))
    issues = []
    for b in blocks:
        prov = b["_prov"]
        sl = src[prov["start"]:prov["end"]]
        if sl != b["content"]:
            issues.append((b["id"], b["type"], "content != cited span"))
        if prov["verbatim"] != b["content"]:
            issues.append((b["id"], b["type"], "verbatim != content"))
    return (len(issues) == 0), issues
