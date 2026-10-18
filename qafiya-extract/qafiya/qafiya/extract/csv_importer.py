"""CSV/TSV -> Qāfiya dataset (deterministic, no dependencies).

Produces a self-contained, frozen bundle:
  <out>/schema.json      field types + source provenance
  <out>/data.jsonl       one typed record per line, each field with _prov (doc,row,column,verbatim)
  <out>/source/<file>    a checksummed copy of the original (original file is never modified)
"""
import os, shutil
from ..io import read_text, write_jsonl, atomic_write_text, parse_csv_rows, sha256_text
from ..schema import infer_schema, coerce
from ..model import new_record

DERIVATIONS = ["sum", "avg", "count", "min", "max", "groupby", "filter"]


def import_csv(src_path: str, out_dir: str) -> dict:
    text = read_text(src_path)
    rows = parse_csv_rows(text)
    if not rows:
        raise ValueError(f"empty CSV: {src_path}")
    header = [h.strip() for h in rows[0]]
    data = [r for r in rows[1:] if any(c.strip() for c in r)]
    schema = infer_schema(header, data)

    # avoid collision with the synthetic record id
    rename = {}
    if "id" in [c.lower() for c in header]:
        for i, c in enumerate(header):
            if c.lower() == "id":
                rename[i] = "src_id"

    records = []
    for ridx, r in enumerate(data):
        fields, prov = {}, {}
        for cidx, col in enumerate(header):
            name = rename.get(cidx, col)
            cell = r[cidx] if cidx < len(r) else ""
            fields[name] = coerce(cell, schema["fields"][col])
            prov[name] = {"doc": f"source/{os.path.basename(src_path)}",
                          "row": ridx, "column": col, "verbatim": cell}
        records.append(new_record(fields, prov))

    src_rel = f"source/{os.path.basename(src_path)}"
    os.makedirs(os.path.join(out_dir, "source"), exist_ok=True)
    shutil.copy2(src_path, os.path.join(out_dir, src_rel))

    schema_doc = {
        "dataset": os.path.splitext(os.path.basename(src_path))[0],
        "id_field": "id",
        "fields": {rename.get(i, c): schema["fields"][c] for i, c in enumerate(header)},
        "derivations": DERIVATIONS,
        "source": {"path": src_rel, "original": os.path.abspath(src_path),
                   "sha256": sha256_text(text), "rows": len(records)},
    }
    atomic_write_text(os.path.join(out_dir, "schema.json"),
                      __import__("json").dumps(schema_doc, ensure_ascii=False, indent=1) + "\n")
    write_jsonl(os.path.join(out_dir, "data.jsonl"), records)
    return {"dataset": schema_doc["dataset"], "records": len(records),
            "fields": list(schema_doc["fields"].keys()), "out": out_dir}
