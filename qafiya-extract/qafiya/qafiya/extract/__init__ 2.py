"""Qāfiya extract — per-format importers.

Routing (spec §2, ingestion strategy):
  .csv/.tsv          -> csv_importer    deterministic, no deps, no token
  .md/.txt           -> text_importer   deterministic, no deps, no token
  .pdf (text layer)  -> pdf_importer    needs pdfplumber
  .docx              -> docx_importer   needs python-docx
  .pdf (scanned)/img -> vlm_importer    needs TOGETHER_API_KEY (document VLM)
"""
from .csv_importer import import_csv
from .text_importer import import_text
from .pdf_importer import import_pdf, MissingDep as PdfMissingDep
from .docx_importer import import_docx, MissingDep as DocxMissingDep
from .vlm_importer import import_scan, MissingToken, NotWired
