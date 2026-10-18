"""DOCX -> blocks (provenance anchored to the extracted paragraph text).
Optional dependency: python-docx."""
import os, json
from ..io import write_jsonl, atomic_write_text, sha256_text
from ..model import new_block


class MissingDep(Exception):
    pass


def import_docx(src_path: str, out_dir: str) -> dict:
    try:
        import docx  # noqa
    except ImportError:
        raise MissingDep("DOCX import needs: pip install python-docx")
    d = __import__("docx").Document(src_path)
    paras = [p.text for p in d.paragraphs if p.text.strip()]
    text = "\n\n".join(paras)
    src_rel = f"source/{os.path.basename(src_path)}.txt"
    os.makedirs(os.path.join(out_dir, "source"), exist_ok=True)
    atomic_write_text(os.path.join(out_dir, src_rel), text)
    blocks, pos = [], 0
    for para in paras:
        cs = text.index(para, pos); ce = cs + len(para); pos = ce
        btype = "heading" if para.lower().startswith(("heading", "title")) else "paragraph"
        blocks.append(new_block(btype, para, {"doc": src_rel, "start": cs, "end": ce, "verbatim": para}))
    atomic_write_text(os.path.join(out_dir, "doc.json"), json.dumps({
        "document": os.path.splitext(os.path.basename(src_path))[0],
        "source": {"path": src_rel, "original": os.path.abspath(src_path), "sha256": sha256_text(text)},
    }, ensure_ascii=False, indent=1) + "\n")
    write_jsonl(os.path.join(out_dir, "blocks.jsonl"), blocks)
    return {"document": os.path.splitext(os.path.basename(src_path))[0], "blocks": len(blocks), "out": out_dir}
