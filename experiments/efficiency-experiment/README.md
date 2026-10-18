# Qāfiya — Efficiency Experiment (Arm A setup + first results)

Implements `deewaan-qafiyah/efficiency-plan.md` H1–H3 offline: exact input-token
measurement with the real Qwen2.5 tokenizer, no model calls required. `T_out`,
wall-clock, and dollars are measured later at the live backend run.

## Run it

```bash
python3 scripts/generate_corpus.py      # frozen seeded corpus -> corpus/ (+sha256 manifest)
python3 scripts/count_tokens.py         # qafiya-extract + T_raw/T_data (3 serving variants)
python3 scripts/measure_selective.py    # H3 multi-doc selective-loading scenario
python3 scripts/crossover.py            # -> results/derived/crossover.json + crossover.png
```

Re-running is deterministic; `corpus/manifest.json` checksums catch any drift.

## Results

See `FREEZE.md` (frozen 2026-10-15). Headline: no token win on single docs
(ratio ≥ 1.0 in the best serving form), **69% input-token saving** in the
multi-doc selective-loading scenario. Provenance inlined into the prompt costs
8.5× — it must stay on disk, addressable by id.

## Layout

```
corpus/         frozen synthetic corpus (seed 20261015) + manifest.json (sha256)
prompts/        fixed deck prompts for both arms
qafiya/         qafiya-extract outputs (validated, provenance-checked)
scripts/        generate_corpus / count_tokens / measure_selective / crossover
tokenizer/      Qwen2.5 tokenizer.json (the actual tokenizer — never chars/words)
results/raw/        frozen evidence (counts.jsonl, selective.json)
results/derived/    crossover.json, crossover.png
FREEZE.md       pre-registration record + results + reframed claims
```
