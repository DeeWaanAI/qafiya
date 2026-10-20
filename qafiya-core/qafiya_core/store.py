#!/usr/bin/env python3
"""Store layer — spec §6/§8. Frozen data, atomic write-back, versioned history.

Guarantees implemented here (all testable):
  * write-temp-then-rename — a dataset file is never overwritten in place
  * every mutation appends the PRIOR state to history.jsonl (provenance survives edits)
  * SUPERSEDED.json quarantine list, read by the gate
"""
import json, os, tempfile
from pathlib import Path

BINDINGS = "bindings.jsonl"
DATA = "data.jsonl"
HISTORY = "history.jsonl"
SUPERSEDED = "SUPERSEDED.json"


def read_jsonl(path: Path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def atomic_write_jsonl(path: Path, rows):
    """Temp-file + fsync + rename: readers never see a torn file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomic on POSIX
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def append_history(ds_dir: Path, event: dict):
    """v1.3: history entries are hash-chained (prev_hash/entry_hash).
    Verify with qafiya_core.chain.verify(ds_dir / 'history.jsonl')."""
    from . import chain
    chain.append(ds_dir / HISTORY, event)


def load_dataset(root: Path, name: str):
    ds = root / "datasets" / name
    return ds, read_jsonl(ds / DATA)


def superseded_set(root: Path):
    p = root / SUPERSEDED
    return set(json.loads(p.read_text())["superseded"]) if p.exists() else set()


def supersede(root: Path, artifact: str):
    s = sorted(superseded_set(root) | {artifact})
    p = root / SUPERSEDED
    p.write_text(json.dumps({"superseded": s}, indent=2))
