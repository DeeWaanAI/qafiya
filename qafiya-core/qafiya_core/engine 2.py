#!/usr/bin/env python3
"""The binding engine — spec §2, §3.1, §6.

Three operations:
  apply_edit()      — an `edit` binding writes back to its target record,
                      atomically, with history, then triggers transitive
                      invalidation (§6).
  invalidate()      — every binding whose sources transitively include the
                      changed record -> provenance=PENDING, semantic=PENDING.
                      This is what stops stale-but-passing claims.
  provenance_gate() — Layer 1, the PROOF. For each binding: quarantine check,
                      then value == eval(derivation, current data). Binary:
                      exit 0 or it does not. (spec §3.1)
"""
import json, sys
from datetime import datetime, timezone
from pathlib import Path

from . import derivations, store


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_bindings(root: Path):
    return store.read_jsonl(root / store.BINDINGS)


def save_bindings(root: Path, bindings):
    store.atomic_write_jsonl(root / store.BINDINGS, bindings)


def _binding_touches_record(binding, dataset, record):
    """Transitive inclusion: a binding depends on a record if it sources the
    dataset AND the record satisfies the binding's where-filter."""
    for s in binding.get("sources", []):
        if s.get("dataset") in (dataset, f"ds:{dataset}"):
            where = dict(derivations.parse(binding["derivation"])[2]) \
                if binding.get("derivation") else {}
            # source-level filter string "period=Q3" is honored too
            src_filter = s.get("filter")
            if src_filter:
                col, _, val = src_filter.partition("=")
                where.setdefault(col.strip(), val.strip())
            if derivations.matches(record, where):
                return True
    return False


def apply_edit(root: Path, edit_binding: dict):
    """Apply an edit binding's writeback. Returns the updated record."""
    wb = edit_binding["writeback"]
    dataset = wb["dataset"].removeprefix("ds:")
    ds_dir, records = store.load_dataset(root, dataset)
    target = None
    for r in records:
        if r["id"] == wb["record_id"]:
            target = r
            break
    if target is None:
        raise KeyError(f"writeback target {wb['record_id']} not found in {dataset}")

    prior = dict(target)
    if wb.get("op", "set") != "set":
        raise ValueError(f"unsupported op {wb.get('op')!r} (v1: set only)")
    target[wb["field"]] = wb["value"]

    store.atomic_write_jsonl(ds_dir / store.DATA, records)
    store.append_history(ds_dir, {
        "ts": _now(), "op": "set", "record_id": wb["record_id"],
        "field": wb["field"], "prior": prior[wb["field"]], "new": wb["value"],
        "edit_binding": edit_binding["id"],
    })
    n = invalidate(root, dataset, target)
    return target, n


def invalidate(root: Path, dataset: str, record: dict) -> int:
    """Transitive invalidation (§6): every dependent binding -> PENDING."""
    bindings = load_bindings(root)
    n = 0
    for b in bindings:
        if b.get("derivation") and _binding_touches_record(b, dataset, record):
            chk = b.setdefault("check", {})
            if chk.get("provenance") != "PENDING":
                chk["provenance"] = "PENDING"
                if b.get("kind") == "claim":
                    chk["semantic"] = "PENDING"
                n += 1
    if n:
        save_bindings(root, bindings)
    return n


def refresh_values(root: Path) -> int:
    """Re-render pass: derived value caches re-resolve from current data
    (spec §2 job 1 — the view stores no number, it re-follows the derivation).
    Only the cached `value` is refreshed; a claim's assertion text/expected is
    NEVER touched — that is what the semantic layer then flags. Returns count."""
    bindings = load_bindings(root)
    n = 0
    for b in bindings:
        if not b.get("derivation"):
            continue
        dataset = b["sources"][0]["dataset"].removeprefix("ds:")
        _, records = store.load_dataset(root, dataset)
        recomputed = derivations.evaluate(b["derivation"], records)
        if recomputed != b.get("value"):
            b["value"] = recomputed
            n += 1
    if n:
        save_bindings(root, bindings)
    return n


def provenance_gate(root: Path) -> int:
    """Layer 1 — deterministic proof. Returns process exit code (0 = PASS)."""
    bindings = load_bindings(root)
    quarantined = store.superseded_set(root)
    failures = []
    for b in bindings:
        if not b.get("derivation"):
            continue
        artifact = b.get("authoritative_artifact", "")
        if artifact and artifact in quarantined:
            b.setdefault("check", {})["provenance"] = "FAIL"
            b["check"]["detail"] = f"quarantined source: {artifact}"
            failures.append((b["id"], b["check"]["detail"]))
            continue
        ok = True
        for s in b.get("sources", []):
            dataset = s["dataset"].removeprefix("ds:")
            _, records = store.load_dataset(root, dataset)
            try:
                recomputed = derivations.evaluate(b["derivation"], records)
            except derivations.DerivationError as e:
                ok, detail = False, str(e)
                break
            if abs(recomputed - float(b["value"])) > 1e-9:
                ok = False
                detail = f"recompute={recomputed} != value={b['value']}"
                break
        else:
            detail = ""
        b.setdefault("check", {})["provenance"] = "PASS" if ok else "FAIL"
        b["check"]["checked_at"] = _now()
        if not ok:
            b["check"]["detail"] = detail
            failures.append((b["id"], detail))
    save_bindings(root, bindings)
    for bid, d in failures:
        print(f"[gate] FAIL {bid}: {d}", file=sys.stderr)
    print(f"[gate] {'PASS' if not failures else 'FAIL'} — "
          f"{len(bindings) - len(failures)}/{len(bindings)} bindings clean")
    return 0 if not failures else 1
