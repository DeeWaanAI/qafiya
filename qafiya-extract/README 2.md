# qafiya-extract

Importer for **DeeWaanAI Qāfiya** — turns a user's documents into Qāfiya's provenance-first
data model. Every extracted value is born with a **binding to the exact span** it came from,
so the whole "re-run it yourself" guarantee holds from the very first import.

## What works now (zero dependencies, no token)

| Input | Output | Provenance |
|---|---|---|
| `.csv` / `.tsv` | `datasets/<name>/` — `schema.json` + `data.jsonl` | per-field `{doc,row,column,verbatim}` |
| `.md` / `.txt` | `documents/<name>/` — `doc.json` + `blocks.jsonl` | per-block `{doc,start,end}` char span |

Both are **non-destructive**: the original file is copied into `source/` (checksummed) and never modified.

## Usage

```bash
python3 -m qafiya.cli examples/expenses.csv          # -> out/expenses/  + validation
python3 -m qafiya.cli examples/notes.md out/notes
python3 -m unittest discover -s tests                # 6 tests
```

The CLI runs a **value-in-span check** after import and exits non-zero if any extracted value
no longer matches its cited source — the ingestion-time form of Qāfiya's Layer 1 (the proof).

```
{"dataset": "expenses", "records": 5, ...}
[validate] PASS — 0 provenance issue(s)
```

## Needs setup (not yet wired)

- **Text-layer PDF** → `pip install pdfplumber` (extracts to a frozen text layer, same span check).
- **DOCX** → `pip install python-docx`.
- **Scanned PDF / images** → a **document VLM**: add `TOGETHER_API_KEY=...` to `.env`
  (see `.env.example`). This is the only path that needs a model; the importer routes to it and
  currently reports "token detected — VLM call is the next build step."

## Design (spec v1.1)

- Deterministic extraction where structure exists (CSV/TSV/text); a model only where it doesn't (scans).
- Every record field / block carries `_prov`; `validate.py` re-opens the frozen source and proves
  `value == source[span]`. A silent edit or a wrong number fails loudly (see the tamper test).
- The routing + grounding + value-in-span rules mirror the `qafiya-extract` skill contract.

## Layout

```
qafiya/
  io.py schema.py model.py validate.py cli.py
  extract/ csv_importer.py text_importer.py pdf_importer.py docx_importer.py vlm_importer.py
tests/test_extract.py   examples/expenses.csv notes.md   .env.example
```
