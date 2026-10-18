#!/usr/bin/env python3
"""Mechanical Layer-2 checkers (spec §3.2). Each returns (state, detail) or None.
These check prose against DATA — never trust the sentence. Causal/mechanism
claims are never auto-passed (R6): PENDING for a human.
"""
import json, re
from pathlib import Path

from qafiya_core import derivations, store

MECHANICAL_WORDS = {"travel", "food", "tools"}


def check_direction(b, recs):
    a = b["assertion"]
    sides = a.get("both_sides") or {}
    if len(sides) != 2:
        return "PENDING", "comparison lacks both_sides"
    (k1, s1), (k2, s2) = sorted(sides.items())
    v1 = derivations.evaluate(s1["derivation"], recs)
    v2 = derivations.evaluate(s2["derivation"], recs)
    actual = (v2 - v1) / v1 if v1 else float("nan")
    exp, tol = float(a["expected"]), float(a.get("tolerance", 0.005))
    if abs(actual - exp) <= tol:
        return "PASS", ""
    return "FLAG", f"recompute shows {actual:+.1%}, claim says {exp:+.1%}"


def check_value(b, recs):
    a = b["assertion"]
    v = derivations.evaluate(b["derivation"], recs)
    if abs(v - float(a["expected"])) <= float(a.get("tolerance", 0.005)):
        return "PASS", ""
    return "FLAG", f"recompute={v}, claim says {a['expected']}"


def check_label(b, recs):
    """S2: the category named in the sentence must be the category in the filter."""
    stmt = b["assertion"].get("statement", "").lower()
    said = {w for w in MECHANICAL_WORDS if re.search(rf"\b{w}\b", stmt)}
    _, _, where = derivations.parse(b["derivation"])
    used = {v for k, v in where.items() if k == "category"}
    if said and used and said != used:
        return "FLAG", f"statement says {sorted(said)} but data filter reads {sorted(used)}"
    return "PASS", ""


def check_scope(b, recs):
    """S3: quantifier claims die by enumeration — 'all' fails if one group
    contradicts; 'most' fails if no majority."""
    a = b["assertion"]
    q = a.get("quantifier")
    if q not in ("all", "most"):
        return "PASS", ""
    fell, rose = [], []
    for g, sides in (a.get("per_group") or {}).items():
        v2 = derivations.evaluate(sides["Q2"]["derivation"], recs)
        v3 = derivations.evaluate(sides["Q3"]["derivation"], recs)
        (fell if v3 < v2 else rose).append(g)
    if q == "all" and rose:
        return "FLAG", f"claim says 'all fell' but {rose} did not"
    if q == "most" and len(fell) <= len(rose):
        return "FLAG", f"claim says 'most fell' but only {fell} of {len(fell)+len(rose)} did"
    return "PASS", ""


def check_existence(root, b):
    """S4: an existence claim requires the artifact on disk."""
    art = b["assertion"].get("evidence_artifact")
    if not art:
        return "PENDING", "no bound artifact"
    if not (root / art).exists():
        return "FAIL", f"phantom analysis: {art} does not exist"
    return "PASS", ""


def check_registry(root, b):
    """S5: an analysis cited as confirmed must be 'confirmed' in the registry."""
    aid = b["assertion"].get("analysis_id")
    reg = {r["analysis_id"]: r for r in json.loads((root / "registry.json").read_text())}
    status = reg.get(aid, {}).get("status")
    if status != "confirmed":
        return "FLAG", f"analysis {aid} status is '{status}', not confirmed"
    return "PASS", ""


def check_reproducibility(root, b):
    """I2: required inputs/configs must exist."""
    req = b["assertion"].get("requires")
    if req and not (root / req).exists():
        return "FAIL", f"nothing to regenerate: {req} missing"
    return "PASS", ""


PREDICATE_CHECKS = {
    "direction": check_direction, "comparison": check_direction,
    "value": check_value, "scope": check_scope,
}


def semantic_check(root, b):
    """Full Layer-2 sweep for one binding. Returns (state, detail)."""
    a = b.get("assertion", {})
    if not b.get("sources"):
        return "FLAG", "I1 unverifiable: no bound source"
    if not b.get("derivation"):
        return "PENDING", "no derivation"
    _, recs = store.load_dataset(root, b["sources"][0]["dataset"].removeprefix("ds:"))
    pred = a.get("predicate")
    if pred in ("existence",):
        return check_existence(root, b)
    if pred in ("registry_status",):
        return check_registry(root, b)
    if pred in ("reproducibility",):
        return check_reproducibility(root, b)
    if pred in ("causal", "mechanism"):
        return "PENDING", "causal claims never auto-pass (R6)"
    fn = PREDICATE_CHECKS.get(pred)
    if not fn:
        return "PENDING", f"predicate '{pred}' not mechanically checkable"
    state, detail = fn(b, recs)
    if state == "PASS" and pred == "value":
        state, detail = check_label(b, recs)  # label check rides along on value claims
    return state, detail
