"""Extrait le texte d'un PDF page par page (lecture seule). usage: python -I pdf_texte.py fichier.pdf sortie.txt"""
import sys
import pymupdf
doc = pymupdf.open(sys.argv[1])
with open(sys.argv[2], "w", encoding="utf-8") as f:
    for i, page in enumerate(doc):
        f.write(f"\n===== page {i+1}\n")
        f.write(page.get_text())
print("pages", doc.page_count)
