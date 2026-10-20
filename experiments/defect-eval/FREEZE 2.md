# FREEZE — Defect-Injection Evaluation (pre-registration + results record)

**Frozen:** 2026-10-15 · **Seed:** 20261015 · **Corpus:** 6 datasets, 24 clean claims, 68 injected defects
**Discipline:** injection manifest frozen before arms ran; spine recomputes every headline number from frozen raw logs, exit 0 required.

## Frozen artifacts

| Artifact | Path |
|---|---|
| Corpus (sha256 per dataset) | `corpus/manifest.json` |
| Clean claim pool (24, verified true) | `clean/bindings.jsonl` |
| Injection manifest (68 labeled defects) | `injection_manifest.json` |
| Per-arm raw results | `results/raw/arm_results.jsonl` |
| Headline numbers (the ONLY source for the paper) | `results/derived/paper_headline_numbers.json` |

## Arms that ran (eval-design §5)

A (Qāfiya full: Layer 1 + mechanical Layer 2), B (Layer 1 only), D (Statcheck-style internal consistency, no source binding), F (no check).
**Gated, not run:** C (human review) and E (external-corpus NLP) need people / model calls; LLM-judged predicates (causal etc.) are PENDING by design (R6). Their absence is documented, not hidden.

## Results — per-class recall

| Class | A full | B (L1 only) | D (internal) | F |
|---|---|---|---|---|
| N1 number-not-in-data | **1.00** | 1.00 | 1.00 | 0 |
| N2 stale-version | **1.00** | 1.00 | 0 | 0 |
| N3 hand-assembled cell | **1.00** | 1.00 | 1.00 | 0 |
| S1 reversed direction | **1.00** | 0 | 0 | 0 |
| S2 wrong label (internally consistent) | **1.00** | 0 | 0 | 0 |
| S3 over-claim ("all fell") | **1.00** | 0 | 0 | 0 |
| S4 phantom analysis | **1.00** | 0 | 0 | 0 |
| S5 exploratory-as-confirmed | **1.00** | 0 | 0 | 0 |
| I1 unverifiable | **1.00** (flagged, coverage) | 0 | 0 | 0 |
| I2 nothing-to-regenerate | **1.00** | 0 | 0 | 0 |
| X1 data shares the error | **0.00** | 0 | 0 | 0 |
| X2 below-rounding drift | **0.00** | 0 | 0 | 0 |

Precision: **1.00 on every arm that flags anything** (0 false positives on 24 clean claims).
Coverage: **93.5%** of claims bound to a recomputable source (I1 injections are the rest — by design, they lower coverage, they don't pass).

## Success criteria (eval-design §8) — verdict

- **SC1** Layer 1 catches 100% of N1/N3 at 0 FP — **met** (deterministic; a miss would be a bug).
- **SC2** Layer 2 S-class recall 1.00 vs B's 0.00 — **met** (margin is total on this corpus).
- **SC3** Arm B leaks ALL S/I-class defects — **met**: this is the substrate-level restatement of the mapping paper's "right numbers, wrong story."
- **SC4** N2 caught 100% via quarantine — **met**.
- **SC6** internal-consistency baseline (D) misses N2 and all semantic classes — **met in spirit** (E still gated).

## Honest limits (stated as results, not caveats)

- **X1/X2 recall is 0.00, as predicted by spec §5** — coherence ≠ truth; reported, not omitted.
- Defects are manufactured (detectability, not prevalence) — eval-design §9.
- S2 was injected in its hardest form (internally consistent; only label-vs-data catches it). A human reader with the source table open (arm C) remains the open baseline.
- Corpus is 6 synthetic datasets; per-class n=6 (n=2 for S3 — only 2 datasets genuinely had a non-falling category). Rates on n=6 are exact for this corpus, not population estimates.
