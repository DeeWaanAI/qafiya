"""Qāfiya core: stable ids, atomic writes, JSONL IO, file hashing. Stdlib only."""
import os, io, csv, json, uuid, hashlib, tempfile


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write_text(path: str, text: str) -> None:
    """Write temp-then-rename so a crash never leaves a half-written file (spec §6)."""
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def write_jsonl(path: str, rows) -> None:
    atomic_write_text(path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def read_jsonl(path: str):
    out = []
    for line in read_text(path).splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def parse_csv_rows(text: str):
    """Consistent CSV parsing used by BOTH import and validate (so row indices align)."""
    return list(csv.reader(io.StringIO(text, newline="")))
