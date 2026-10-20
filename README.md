# Qafiya — the provenance-first data model

Companion code and frozen experimental artifacts for the paper:

> **Qafiya: A Provenance-First Data Model for Trustworthy AI-Generated Views over Personal Data**
> Youssef Hariri · DeeWaanAI

In Qafiya, every rendered value or claim is tied to its source by a **binding** — one
record that is simultaneously the render-source of a generated view, the target of a
durable edit, and the audit-pointer for a two-layer check (deterministic proof for
numbers, advisory flags for interpretations). "Trust me" becomes "re-run it yourself."

## Layout

| Path | What it is |
|---|---|
| `qafiya-core/` | The binding engine: derivations, atomic store, edit/invalidation/quarantine, Layer-1 gate, mechanical Layer-2 sweep. Zero dependencies. `python3 demo.py` runs the paper's §5 loop; 9 unit tests. |
| `qafiya-extract/` | Importers (CSV/TSV, Markdown, text-PDF, DOCX) that turn documents into the Qafiya model, every value born with a provenance pointer to its source span. 12 tests. |
| `experiments/defect-eval/` | Integrity track: frozen corpus, 68 labeled injected defects, 4 arms, self-verifying spine → every headline number in §6. |
| `experiments/efficiency-experiment/` | Efficiency track: exact token accounting, selective-loading savings, frozen live-API runs → every number in §7. |
| `spec/` | The normative specification (v1.1), the v1.2 formula-audit extension note, and the v1.3 hash-chained-history delta (integrated in `qafiya_core.chain`). |

## Quickstart

```bash
# the paper's §5 worked loop, end to end
cd qafiya-core && python3 demo.py

# extract your own file into the Qafiya model
cd qafiya-extract && python3 -m qafiya.cli examples/expenses.csv

# reproduce the paper's §6 numbers (deterministic, no model calls)
cd experiments/defect-eval && python3 scripts/gen_corpus.py && python3 scripts/inject.py \
  && python3 scripts/run_arms.py && python3 scripts/spine.py

# reproduce §7's token accounting (needs the Qwen2.5 tokenizer, ~7 MB:
# curl -L -o tokenizer/qwen25_tokenizer.json \
#   https://huggingface.co/Qwen/Qwen2.5-7B-Instruct/resolve/main/tokenizer.json)
cd experiments/efficiency-experiment && python3 scripts/generate_corpus.py \
  && python3 scripts/count_tokens.py && python3 scripts/crossover.py
```

Optional dependencies for PDF/DOCX importers: `pip install pdfplumber python-docx`.
Everything else is Python standard library only.

## Install as a library

```bash
pip install git+https://github.com/DeeWaanAI/qafiya.git
```

## License

AGPL-3.0 — see `LICENSE`.
