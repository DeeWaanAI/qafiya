"""Markdown/plain text -> Qāfiya document blocks, each bound to an exact char span.

Non-destructive: the original file is copied into <out>/source/ and never modified.
Every block's `content` equals source[start:end] exactly, so validate_document proves it."""
import os, shutil, json
from ..io import read_text, write_jsonl, atomic_write_text, sha256_text
from ..model import new_block

_LIST = ("- ", "* ", "+ ")


def _classify(lines):
    stripped = [l.strip() for l in lines]
    if stripped and all(s.startswith("#") for s in stripped if s):
        return "heading"
    if stripped and all(s.startswith(_LIST) or s == "" for s in stripped) and any(s for s in stripped):
        return "list"
    return "paragraph"


def import_text(src_path: str, out_dir: str) -> dict:
    text = read_text(src_path)
    # index lines by absolute offset
    lines, pos = [], 0
    for ln in text.splitlines(keepends=True):
        lines.append((ln, pos)); pos += len(ln)

    blocks, buf = [], []

    def flush():
        nonlocal buf
        if not buf:
            return
        raw = "".join(ln for ln, _ in buf)
        start = buf[0][1]
        lead = len(raw) - len(raw.lstrip())
        trail = len(raw) - len(raw.rstrip())
        cs, ce = start + lead, start + len(raw) - trail
        content = text[cs:ce]
        if content:
            btype = _classify([l for l, _ in buf])
            blocks.append(new_block(btype, content,
                                    {"doc": f"source/{os.path.basename(src_path)}",
                                     "start": cs, "end": ce, "verbatim": content}))
        buf = []

    for ln, off in lines:
        if ln.strip() == "":
            flush(); continue
        is_head = ln.lstrip().startswith("#")
        is_list = ln.lstrip().startswith(_LIST)
        boundary = is_head or (buf and ((_classify([l for l, _ in buf]) == "list") != is_list))
        if is_head:
            flush(); buf.append((ln, off)); flush(); continue
        if boundary:
            flush()
        buf.append((ln, off))
    flush()

    src_rel = f"source/{os.path.basename(src_path)}"
    os.makedirs(os.path.join(out_dir, "source"), exist_ok=True)
    shutil.copy2(src_path, os.path.join(out_dir, src_rel))
    atomic_write_text(os.path.join(out_dir, "doc.json"), json.dumps({
        "document": os.path.splitext(os.path.basename(src_path))[0],
        "source": {"path": src_rel, "original": os.path.abspath(src_path),
                   "sha256": sha256_text(text), "chars": len(text)},
    }, ensure_ascii=False, indent=1) + "\n")
    write_jsonl(os.path.join(out_dir, "blocks.jsonl"), blocks)
    return {"document": json.loads(read_text(os.path.join(out_dir, "doc.json")))["document"],
            "blocks": len(blocks), "out": out_dir}
