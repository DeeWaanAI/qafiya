# Qāfiya v1.2 Extension Note — Formula Auditing (the N4 check)

**Status:** extension note only — v1.1 is unaffected and stays submittable.
**Method source:** the mapping paper's class **N4 formula-approximation** (observed:
personas-paper Bayes Factor — stated JZS procedure [Rouder et al. 2009], executed
`exp(−t²/2)·√(n/2)`; every value-level check passed because none read the computation).

## 1. What v1.1 checks vs. what N4 needs

v1.1 proves **claim-to-data coherence**: the value equals its derivation over its
sources. N4 is **method-to-description coherence**: the derivation (or analysis code)
computes something *other* than the formula the prose names. The personas case shows
why value checks are structurally blind to it — the number reproduced from code, the
citation resolved, and the two still disagreed.

## 2. Spec delta (minimal)

One new optional field on `assertion`:

```jsonc
"assertion": {
  "statement": "evidence strength quantified by Bayes Factor (Rouder et al., 2009)",
  "predicate": "method",
  "method": {
    "stated": "jzs-bayes-factor",          // names the claimed procedure + citation
    "citation": "Rouder et al. 2009",
    "executed_artifact": "analysis/bf.py", // code available → extract & compare
    "regenerate_from_prose": false          // code absent → weaker check, see §3
  }
}
```

And one new closed set, same philosophy as §1.2's closed derivation set — the
**auditable-statistics registry**: `{t-test:student, t-test:welch, chi2, ols,
pooled-rate, jzs-bayes-factor, t-to-bf-conversion, ...}`. A `method.stated` value
outside the registry is PENDING-by-design, never auto-passed. Open-ended "is this
code correct" is undecidable and stays out.

## 3. The two check strategies (asymmetric, stated honestly)

- **Code available** — extract the computation the artifact actually executes and
  compare against the registry definition of `stated`. Mechanical where the statistic
  is in the closed set. Catches the personas case: `t-to-bf-conversion ≠ jzs-bayes-factor`.
- **Code unavailable** — regenerate the statistic from its prose description over the
  same data and compare *outputs*. Strictly weaker: identical output on one dataset
  does not prove identical formula. **It can catch, never prove.**

Both inherit the mapping paper's **convention-sweep discipline**: before any mismatch
verdict, sweep plausible conventions (ddof, rounding, truncation) — a false
formula-attribution already exists in the auditor's own retraction log (ETC paper).

## 4. Placement in the two-layer architecture

**Layer 2, never Layer 1.** Layer 1 remains the binary proof of value-against-data.
Formula audit is advisory (FLAG/PENDING) because "is this the *appropriate* test" is
judgment (R6) — the mechanical part is only "does the computation match the named
formula." Where the check cannot run (statistic outside registry, no code, no data),
the binding's coverage score drops (I1), exactly as spec §4 prescribes.

## 5. Evaluation hook (for the v1.2 eval round)

Add an N4 injection class to `defect-eval`: claims whose derivation/artifact computes
a *different member of the registry* than `method.stated` (e.g. stated Welch, executed
Student; stated JZS, executed t-to-BF), plus convention-sweep controls to measure the
false-attribution rate. Expected: code-available recall ~1.0; prose-only recall < 1.0
with the asymmetry reported as a result, not a caveat.

## 6. Non-goals

Not a statistical-review oracle; not open-ended code verification; not a Layer-1
guarantee. v1.2 certifies **that the named method is the executed method** — within
the closed registry and the stated asymmetry — nothing more.

---
*Depends on: mapping paper v0.8 (N4 class definition), Qāfiya spec v1.1 (§2 binding, §3 two-layer check, §4 coverage), qafiya-core (registry mechanics mirror derivations.py).*
