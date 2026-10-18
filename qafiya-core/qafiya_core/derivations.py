#!/usr/bin/env python3
"""Deterministic derivation evaluator — the CLOSED set from spec §1.2.

Grammar (deliberately tiny so every binding.derivation is machine-recomputable):
    FUNC(field) [where col='val' [and col='val' ...]]
    FUNC ∈ {sum, avg, count, min, max}   (groupby/filter are view-level, not value-level)

No eval(), no arbitrary code — a derivation the parser rejects is invalid by construction.
"""
import re

FUNCS = ("sum", "avg", "count", "min", "max")
_PATTERN = re.compile(
    r"^\s*(?P<func>sum|avg|count|min|max)\((?P<field>[A-Za-z_][\w]*)\)"
    r"(?:\s+where\s+(?P<where>.+))?\s*$"
)
_CLAUSE = re.compile(r"([A-Za-z_]\w*)\s*=\s*'([^']*)'")


class DerivationError(ValueError):
    pass


def parse(derivation: str):
    m = _PATTERN.match(derivation)
    if not m:
        raise DerivationError(f"unparseable derivation: {derivation!r}")
    where = {}
    if m.group("where"):
        for col, val in _CLAUSE.findall(m.group("where")):
            where[col] = val
        # every clause must have matched — reject silently dropped text
        rebuilt = " and ".join(f"{c}='{v}'" for c, v in where.items())
        if rebuilt != m.group("where").strip():
            raise DerivationError(f"unsupported where-clause: {m.group('where')!r}")
    return m.group("func"), m.group("field"), where


def matches(record: dict, where: dict) -> bool:
    return all(str(record.get(col)) == val for col, val in where.items())


def evaluate(derivation: str, records) -> float:
    """Recompute a derivation over records. NaN is never hidden: empty selection
    on a numeric func raises (spec §3.1 — silence about missing values is where
    phantom numbers hide)."""
    func, field, where = parse(derivation)
    sel = [r for r in records if matches(r, where)]
    if func == "count":
        return float(len(sel))
    vals = [float(r[field]) for r in sel if r.get(field) is not None]
    if not vals:
        raise DerivationError(f"empty selection for {derivation!r} — no value to prove")
    return {
        "sum": sum(vals),
        "avg": sum(vals) / len(vals),
        "min": min(vals),
        "max": max(vals),
    }[func]
