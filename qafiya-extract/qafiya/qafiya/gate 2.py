"""Qāfiya Layer-1 gate (deterministic proof) — spec §3.1 / §6.

Adapts the mapping paper's two-way verifier to Qāfiya bindings:
  * recompute_check : eval(derivation, records) must equal binding.value  (value drift)
  * superlative/direction claim checks : recompute both sides, compare to the assertion
  * transitive_invalidate : an edit marks every binding that depends on it PENDING
  * quarantine_check : a binding pointing at a superseded artifact fails by construction
No model, no token — this half is a proof."""
import os, re, json
from .io import read_text, read_jsonl, write_jsonl, atomic_write_text

_AGG = re.compile(r"^\s*(sum|avg|count|min|max)\((\w*)\)(?:\s+where\s+(.+?))?\s*$", re.I)
_GRP = re.compile(r"^\s*(sum|avg|count|min|max)\((\w+)\)\s+groupby\s+(\w+)\s*$", re.I)


def load_dataset(out_dir: str):
    schema = json.loads(read_text(os.path.join(out_dir, "schema.json")))
    return schema, read_jsonl(os.path.join(out_dir, "data.jsonl"))


def _match_where(rec, clause: str) -> bool:
    for part in re.split(r"\s+and\s+", clause, flags=re.I):
        m = re.match(r"^\s*(\w+)\s*=\s*['\"]?([^'\"]+?)['\"]?\s*$", part)
        if not m:
            return False
        col, val = m.group(1), m.group(2)
        if str(rec.get(col)) != val:
            return False
    return True


def agg(expr: str, records):
    m = _AGG.match(expr)
    if not m:
        raise ValueError(f"unsupported derivation: {expr!r}")
    fn, field, where = m.group(1).lower(), m.group(2), m.group(3)
    rows = [r for r in records if (not where or _match_where(r, where))]
    if fn == "count":
        return float(len(rows))
    vals = [float(r[field]) for r in rows if r.get(field) is not None]
    if not vals:
        return None
    return {"sum": sum, "avg": lambda v: sum(v) / len(v), "min": min, "max": max}[fn](vals)


def group_agg(expr: str, records):
    m = _GRP.match(expr)
    if not m:
        raise ValueError(f"unsupported group derivation: {expr!r}")
    fn, field, key = m.group(1).lower(), m.group(2), m.group(3)
    out = {}
    for r in records:
        out.setdefault(str(r.get(key)), []).append(r)
    return {k: agg(f"{fn}({field})", v) for k, v in out.items()}


def recompute_check(binding, records):
    """Layer-1 value proof for a view binding."""
    got = agg(binding["derivation"], records)
    want = binding.get("value")
    if got is None or want is None:
        return "FAIL", "no value"
    ok = abs(float(got) - float(want)) <= float(binding.get("tolerance", 1e-6))
    return ("PASS" if ok else "FAIL"), f"recomputed={got} bound={want}"


def check_claim(binding, records):
    """Deterministic part of Layer 2 (mechanical where the sentence allows, spec §3.2)."""
    a = binding["assertion"]
    pred = a.get("predicate")
    if pred == "superlative":
        g = group_agg(a["metric"], records)
        top = max(g, key=lambda k: g[k] or float("-inf"))
        ok = top == a["subject"]
        return ("PASS" if ok else "FLAG"), f"top={top} claimed={a['subject']} values={g}"
    if pred == "direction":
        a0 = agg(a["metric"], [r for r in records if str(r.get(a["key"])) == a["from"]])
        a1 = agg(a["metric"], [r for r in records if str(r.get(a["key"])) == a["to"]])
        actual = (a1 - a0) / a0 if a0 else None
        ok = actual is not None and abs(actual - a["expected"]) <= a.get("tolerance", 0.02)
        return ("PASS" if ok else "FLAG"), f"actual={actual:.3f} claimed={a['expected']}"
    return "N/A", "predicate not mechanically checkable (needs human/model flag)"


def transitive_invalidate(changed_dataset: str, bindings):
    """Any binding sourcing from the changed dataset goes PENDING (spec §6)."""
    for b in bindings:
        if any(s.get("dataset") == changed_dataset for s in b.get("sources", [])):
            b.setdefault("check", {})["provenance"] = "PENDING"
    return bindings


def quarantine_check(binding, superseded: set):
    return binding.get("authoritative_artifact") not in superseded


def apply_edit(out_dir: str, record_id: str, field: str, new_value):
    """Atomic write-back + append-only history (spec §6). Returns the old value."""
    recs = read_jsonl(os.path.join(out_dir, "data.jsonl"))
    old = None
    for r in recs:
        if r["id"] == record_id:
            old = r.get(field); r[field] = new_value; break
    else:
        raise KeyError(record_id)
    hist_path = os.path.join(out_dir, "history.jsonl")
    entry = {"record_id": record_id, "field": field, "old": old, "new": new_value}
    prior = read_text(hist_path) if os.path.exists(hist_path) else ""
    atomic_write_text(hist_path, prior + json.dumps(entry, ensure_ascii=False) + "\n")
    write_jsonl(os.path.join(out_dir, "data.jsonl"), recs)
    return old
