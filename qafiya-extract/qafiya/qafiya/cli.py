"""qafiya-extract CLI: route a file to the right importer, then prove provenance.

Usage:  python -m qafiya.cli <file> [out_dir]
Exit 0 = imported AND value-in-span validation passed."""
import os, sys, json
from .extract import import_csv, import_text, import_pdf, import_docx, import_scan
from .extract.vlm_importer import MissingToken, NotWired
from .extract.pdf_importer import MissingDep as PdfMissingDep
from .extract.docx_importer import MissingDep as DocxMissingDep
from .validate import validate_dataset, validate_document


def route(src: str, out: str):
    ext = os.path.splitext(src)[1].lower()
    if ext in (".csv", ".tsv"):
        return import_csv(src, out), "dataset"
    if ext in (".md", ".markdown", ".txt"):
        return import_text(src, out), "document"
    if ext == ".pdf":
        return import_pdf(src, out), "document"       # text-layer; scanned handled by vlm
    if ext == ".docx":
        return import_docx(src, out), "document"
    if ext in (".png", ".jpg", ".jpeg", ".webp", ".tiff"):
        return import_scan(src, out), "document"
    raise SystemExit(f"qafiya-extract: unsupported file type {ext!r}")


def main(argv):
    if len(argv) < 2:
        print("usage: python -m qafiya.cli <file> [out_dir]"); return 2
    src = argv[1]
    out = argv[2] if len(argv) > 2 else os.path.join("out", os.path.splitext(os.path.basename(src))[0])
    try:
        summary, kind = route(src, out)
    except (MissingToken, NotWired, PdfMissingDep, DocxMissingDep) as e:
        print(f"[qafiya-extract] needs setup:\n{e}"); return 3
    ok, issues = validate_dataset(out) if kind == "dataset" else validate_document(out)
    print(json.dumps(summary, ensure_ascii=False))
    print(f"[validate] {'PASS' if ok else 'FAIL'} — {len(issues)} provenance issue(s)")
    for it in issues[:10]:
        print("   -", it)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
