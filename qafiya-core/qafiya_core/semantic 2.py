#!/usr/bin/env python3
"""Layer 2 — the semantic map, mechanical half (spec §3.2).

Only what can be checked WITHOUT trusting prose is automated here:
  * direction / comparison claims: both sides are recomputed from current data,
    the actual change is derived, and the claim's `expected` is compared within
    `tolerance`. A mismatch is a FLAG (never silent), with the recomputed value
    shown — "re-run it yourself."
Mechanism/causal claims are NEVER auto-passed (R6): they get PENDING for a human.
"""
from pathlib import Path

from . import derivations, store
from .engine import load_bindings, save_bindings

MECHANICAL = {"direction", "comparison", "value"}


def semantic_sweep(root: Path) -> int:
    """Returns number of FLAGs raised (informational; Layer 2 is advisory)."""
    bindings = load_bindings(root)
    flags = 0
    for b in bindings:
        if b.get("kind") != "claim" or "assertion" not in b:
            continue
        chk = b.setdefault("check", {})
        a = b["assertion"]
        pred = a.get("predicate")
        if pred not in MECHANICAL:
            chk["semantic"] = "PENDING"  # causal/mechanism: human judgment (R6)
            chk["detail"] = f"predicate '{pred}' is not mechanically checkable"
            continue
        sides = a.get("both_sides") or {}
        if len(sides) != 2:
            chk["semantic"] = "PENDING"
            chk["detail"] = "comparison lacks both_sides derivations"
            continue
        (k1, s1), (k2, s2) = sorted(sides.items())  # chronological order assumed by key
        dataset = b["sources"][0]["dataset"].removeprefix("ds:")
        _, records = store.load_dataset(root, dataset)
        v1 = derivations.evaluate(s1["derivation"], records)
        v2 = derivations.evaluate(s2["derivation"], records)
        actual = (v2 - v1) / v1 if v1 else float("nan")
        expected = float(a.get("expected"))
        tol = float(a.get("tolerance", 0.005))
        if abs(actual - expected) <= tol:
            chk["semantic"] = "PASS"
            chk.pop("detail", None)
        else:
            chk["semantic"] = "FLAG"
            chk["detail"] = (f"recompute shows {actual:+.1%}, "
                             f"claim says {expected:+.1%} "
                             f"({k1}={v1}, {k2}={v2})")
            flags += 1
    save_bindings(root, bindings)
    return flags
