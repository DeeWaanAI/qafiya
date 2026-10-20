# qafiya-core — the binding engine (spec v1.1 §2, §3, §6 made runnable)

The minimal, tested core of Qāfiya: the **Binding** primitive plus the two-layer check.
No model, no dependencies — pure Python stdlib. This is the code behind the paper's
§9 worked example and the durability track of the evaluation.

## What it proves in code

| Spec claim | Where |
|---|---|
| Closed, machine-recomputable derivation set (`sum/avg/count/min/max ... where`) — anything else is invalid by construction | `qafiya_core/derivations.py` |
| Atomic write-back (temp → rename), prior state kept in a hash-chained, tamper-evident `history.jsonl` (v1.3) | `qafiya_core/store.py`, `engine.apply_edit`, `chain.py` |
| Transitive invalidation: editing a record marks every dependent binding `PENDING` — stale-but-passing is impossible | `engine.invalidate` |
| Layer 1 provenance gate: `value == eval(derivation, current data)`, quarantine via `SUPERSEDED.json`; binary exit 0/1 | `engine.provenance_gate` |
| Re-render: views re-resolve values from data (the view stores no number); the claim's text is never touched | `engine.refresh_values` |
| Layer 2 mechanical flag: direction/comparison claims recomputed from both sides; causal claims never auto-pass (R6) | `qafiya_core/semantic.py` |

## Run it

```bash
python3 demo.py                          # the §9 loop, end to end
python3 -m unittest discover -s tests    # 9 tests
```

Demo output:

```
[gate] PASS — 2/2 bindings clean
[semantic] PASS — 'fell 12%' matches the data
write-back OK (r_q3_0.amount = 420.0); 2 bindings marked PENDING
[render] 2 value caches re-resolved from current data (880 → 920)
[gate] PASS — 2/2 bindings clean
[semantic] FLAG: recompute shows -8.0%, claim says -12.0% (Q2=1000.0, Q3=920.0)
[gate] FAIL — quarantined source (N2 stale-version defense)
```

## One design correction discovered while building

The spec's §9 narrative says "edit → provenance recompute → PASS". In running code
that ordering FAILs first: the edit makes the cached value stale, which is exactly
what the gate is for. The correct loop is **edit → invalidate (PENDING) → view
re-renders from data → gate PASS → semantic FLAG**. The engine implements it; the
paper's §9 should show this ordering.

## Layout

```
qafiya_core/  derivations.py  store.py  engine.py  semantic.py
demo.py       spec §9 worked example (PASS → edit → invalidate → PASS → FLAG → quarantine FAIL)
tests/        9 tests, each mapped to a §7 invariant
```
