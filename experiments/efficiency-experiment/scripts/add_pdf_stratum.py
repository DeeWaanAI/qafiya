#!/usr/bin/env python3
"""Add a text-layer PDF stratum to the frozen efficiency corpus: render the
prose reports to PDF (same content, token-heavy container), update manifest.
Deterministic layout (fixed font/positions)."""
import hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
from reportlab.lib.pagesizes import letter  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402


def md_to_pdf(md_path: Path, pdf_path: Path):
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    y = 750
    for line in md_path.read_text().splitlines():
        if not line.strip():
            y -= 12
            continue
        # simple fixed-width wrap, deterministic
        words, cur = line.split(), ""
        for w in words:
            if len(cur) + len(w) > 95:
                c.drawString(72, y, cur); y -= 14
                cur = w
                if y < 72:
                    c.showPage(); y = 750
            else:
                cur = f"{cur} {w}".strip()
        if cur:
            c.drawString(72, y, cur); y -= 14
        if y < 72:
            c.showPage(); y = 750
    c.save()


def main():
    d = ROOT / "corpus" / "pdf"
    d.mkdir(parents=True, exist_ok=True)
    manifest_p = ROOT / "corpus" / "manifest.json"
    manifest = json.loads(manifest_p.read_text())
    existing = {x["file"] for x in manifest["docs"]}
    added = 0
    for md in sorted((ROOT / "corpus" / "prose").glob("*.md")):
        name = md.stem + ".pdf"
        if f"pdf/{name}" in existing:
            continue
        pdf = d / name
        md_to_pdf(md, pdf)
        manifest["docs"].append({
            "stratum": "pdf", "file": f"pdf/{name}",
            "size_param": md.stat().st_size, "bytes": pdf.stat().st_size,
            "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "rendered_from": f"prose/{md.name}"})
        added += 1
    manifest_p.write_text(json.dumps(manifest, indent=2))
    print(f"added {added} PDFs; corpus now {len(manifest['docs'])} docs")


if __name__ == "__main__":
    sys.exit(main())
