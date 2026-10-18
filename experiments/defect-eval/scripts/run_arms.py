#!/usr/bin/env python3
"""Run the evaluation arms over the frozen defective corpus.

Arms (eval-design §5; C human and E external-NLP are gated — documented):
  A  Qāfiya full  = Layer 1 (proof) + Layer 2 (mechanical semantic checks)
  B  Layer 1 only = numeric recompute + quarantine, no semantic sweep
  D  Statcheck-style internal consistency (stated numbers vs each other,
     no source binding)
  F  No check

Writes results/raw/arm_results.jsonl — one line per (arm, binding) with
{flagged: bool, state, detail}. This is the ONLY evidence spine.py reads.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT.parent / "qafiya-core"
sys.path.insert(0, str(CORE))
sys.path.insert(0, str(Path(__file__).parent))
from qafiya_core import derivations, store  # noqa: E402
import checks  # noqa: E402

EVAL = ROOT / "evaluated"


def layer1(b):
    """Deterministic proof: quarantine + value == eval(derivation, current data)."""
    if not b.get("derivation"):
        return None  # not checkable at this layer
    art = b.get("authoritative_artifact", "")
    if art and art in store.superseded_set(EVAL):
        return ("FAIL", f"quarantined source: {art}")
    if not b.get("sources"):
        return None  # I1 is a coverage matter, not a Layer-1 fail
    try:
        _, recs = store.load_dataset(EVAL, b["sources"][0]["dataset"].removeprefix("ds:"))
        recomputed = derivations.evaluate(b["derivation"], recs)
    except derivations.DerivationError as e:
        return ("FAIL", str(e))
    if abs(recomputed - float(b["value"])) > 1e-9:
        return ("FAIL", f"recompute={recomputed} != value={b['value']}")
    return ("PASS", "")


def internal_consistency(b):
    """Arm D: numbers inside the claim must agree with each other — no data access."""
    a = b.get("assertion", {})
    stmt = a.get("statement", "")
    m = re.search(r"([+-]?\d+(?:\.\d+)?)%", stmt)
    if m and "expected" in a and abs(float(a["expected"])) < 1:
        if abs(abs(float(m.group(1))) / 100 - abs(float(a["expected"]))) > 0.005:
            return ("FLAG", "statement % disagrees with expected field")
    m2 = re.search(r"is\s+([0-9]+(?:\.[0-9]+)?)", stmt)
    if m2 and a.get("predicate") == "value":
        if abs(float(m2.group(1)) - float(a["expected"])) > 1.0:
            return ("FLAG", "statement value disagrees with expected field")
    return ("PASS", "")


def arm_full(b):
    r = layer1(b)
    if r and r[0] == "FAIL":
        return r
    return checks.semantic_check(EVAL, b)


ARMS = {
    "A_full": arm_full,
    "B_layer1_only": lambda b: layer1(b) or ("PASS", ""),
    "D_internal_only": internal_consistency,
    "F_none": lambda b: ("PASS", ""),
}


def flagged(state):
    return state in ("FAIL", "FLAG")


def main():
    bindings = store.read_jsonl(EVAL / "bindings.jsonl")
    out = ROOT / "results" / "raw"
    out.mkdir(parents=True, exist_ok=True)
    n_flag = {}
    with open(out / "arm_results.jsonl", "w") as f:
        for arm, fn in ARMS.items():
            for b in bindings:
                res = fn(b)
                state, detail = res if res else ("N/A", "")
                f.write(json.dumps({"arm": arm, "binding": b["id"],
                                    "state": state, "flagged": flagged(state),
                                    "detail": detail}, ensure_ascii=False) + "\n")
                n_flag[(arm, state)] = n_flag.get((arm, state), 0) + 1
    for (arm, state), n in sorted(n_flag.items()):
        print(f"{arm:16s} {state:8s} {n}")
    print(f"\nwrote {out/'arm_results.jsonl'}")


if __name__ == "__main__":
    main()
