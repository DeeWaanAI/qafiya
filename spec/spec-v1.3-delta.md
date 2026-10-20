# Qafiya spec v1.3 delta — hash-chained history (monitor proposal)

**Status:** proposal for owner confirmation → then integration into spec v1.1 → v1.3.
**Motivation (INTEGRATION-AUDIT-1, G1):** Layers 3 and 4 independently invented
tamper-evident hash chains; the substrate should own the mechanism once.

## The delta (everything else in v1.1 unchanged)

1. **Chained history.** Every entry appended to `history.jsonl` MUST carry:
   `prev_hash` (sha256 of the previous entry's canonical JSON; genesis = 64 zeros)
   and `entry_hash` (sha256 over `prev_hash ‖ canonical_json(entry)`).
   Canonical JSON = `json.dumps(obj, sort_keys=True, separators=(",", ":"))`.
2. **Verification.** `qafiya_core.chain.verify(history.jsonl)` recomputes the chain;
   any mismatch = tamper → reported, never repaired silently. The Layer-1 gate
   SHOULD run chain verification as part of quarantine checks.
3. **Honesty boundary (stated in spec §5, added as limit 5):** the chain detects
   *modification* of history; it cannot survive an attacker who rewrites the store
   AND recomputes the chain — mitigation (external anchoring / replication) is
   future work, reported as a limit, exactly the formulation Layer 4 already uses.

## Reference implementation

`chain.py` (this package) is drop-in for qafiya-core: `store.append_history` gains
two fields; `chain.verify` walks any dataset. Tests included. Migration of existing
stores: one pass appends hashes to existing entries (hash of content unchanged —
history semantics untouched).

## Integration notes per layer

- **qafiya-core repo (GitHub):** add `chain.py`, patch `store.append_history`,
  run the migration helper on `experiments/` frozen stores; the defect-eval spine
  then also verifies chains (one line).
- **Layer 3:** delete its §3 local chain code; consume `qafiya_core.chain`
  (`verify_chain.py` becomes a thin call). Paper: mechanism unchanged, citation
  moves to "Qafiya v1.3 substrate" — strengthens, not weakens, the layer story.
- **Layer 4:** same — §2 becomes "inherits Qafiya v1.3 chained history"; keep its
  proof-of-absence (that's memory-specific and stays).
