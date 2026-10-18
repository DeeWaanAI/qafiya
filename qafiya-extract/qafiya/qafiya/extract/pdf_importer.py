"""Text-layer PDF -> blocks (provenance anchored to the extracted text layer).
Optional dependency: pdfplumber. Scanned PDFs belong in vlm_importer, not here."""
import os, shutil, json
from ..io import write_jsonl, atomic_write_text, sha256_text
from ..model import new_block


class MissingDep(Exception):
    pass


def import_pdf(src_path: str, out_dir: str) -> dict:
    try:
        import pdfplumber  # noqa
    except ImportError:
        raise MissingDep("Text-layer PDF needs: pip install pdfplumber")
    pages = []
    with __import__("pdfplumber").open(src_path) as pdf:
        for p in pdf.pages:
            pages.append(p.extract_text() or "")
    text = "\n\n".join(pages)
    src_rel = f"source/{os.path.basename(src_path)}.txt"
    os.makedirs(os.path.join(out_dir, "source"), exist_ok=True)
    atomic_write_text(os.path.join(out_dir, src_rel), text)
    blocks, pos = [], 0
    for para in text.split("\n\n"):
        content = para.strip()
        if not content:
            pos += len(para) + 2; continue
        cs = text.index(content, pos); ce = cs + len(content); pos = ce
        blocks.append(new_block("paragraph", content,
                                {"doc": src_rel, "start": cs, "end": ce, "verbatim": content}))
    atomic_write_text(os.path.join(out_dir, "doc.json"), json.dumps({
        "document": os.path.splitext(os.path.basename(src_path))[0],
        "source": {"path": src_rel, "original": os.path.abspath(src_path), "sha256": sha256_text(text)},
    }, ensure_ascii=False, indent=1) + "\n")
    write_jsonl(os.path.join(out_dir, "blocks.jsonl"), blocks)
    return {"document": os.path.splitext(os.path.basename(src_path))[0], "blocks": len(blocks), "out": out_dir}
