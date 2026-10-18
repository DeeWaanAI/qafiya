# Qāfiya — Defect-Injection Evaluation (Integrity track)

Implements the integrity track of `deewaan-qafiyah/eval-design.md`:
a frozen corpus of known-correct claims, 68 labeled injected defects across the
ten-class taxonomy covered by v1.1 (the mapping paper's eleventh, N4
formula-approximation, is the v1.2 extension), plus the two provably-uncatchable
classes, four arms, and a
self-verifying spine that recomputes every headline number from frozen logs.

## Run it (fully deterministic, no model calls)

```bash
python3 scripts/gen_corpus.py    # frozen corpus + 24 verified-clean claims
python3 scripts/inject.py        # 68 labeled defects; manifest frozen BEFORE arms run
python3 scripts/run_arms.py      # arms A (full), B (Layer-1), D (internal), F (none)
python3 scripts/spine.py         # -> results/derived/paper_headline_numbers.json (exit 0)
```

## Headline results (see FREEZE.md)

- Arm A (Qāfiya full): **100% recall on all 10 catchable classes, 0 false alarms**
- Arm B (Layer 1 only): catches the numbers (N1/N2/N3), **leaks every interpretive defect (S1–S5, I1–I2)** — the "right numbers, wrong story" result, now on a substrate
- Arm D (Statcheck-style): catches internal number mismatches only; blind to stale sources and every semantic class
- X1/X2 (provably uncatchable): 0% everywhere — coherence, not truth, by design
- Coverage metric: 93.5% (I1 defects visibly lower it instead of passing silently)

## Gated arms (not run)

C (human review) and E (external-corpus NLP, FActScore/AVeriTeC-style) require
people and model calls. LLM-judged predicates (causal/mechanism) are PENDING by
design (R6) — the mechanical Layer 2 is what runs here.

## Layout

```
corpus/      frozen datasets (sha256 manifest) + analysis registry
clean/       the 24 known-correct claims
evaluated/   corpus + injected bindings (what the arms see)
injection_manifest.json   frozen labels {binding, class, correct, injected}
scripts/     gen_corpus / inject / checks (mechanical Layer-2) / run_arms / spine
results/raw/       arm_results.jsonl (the only evidence)
results/derived/   paper_headline_numbers.json
FREEZE.md    pre-registration + results record
```

Depends on `qafiya-core` (the binding engine) for derivations, store, and gate logic.
