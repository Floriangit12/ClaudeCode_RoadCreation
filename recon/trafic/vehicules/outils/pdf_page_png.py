"""Rend une page de PDF en PNG. usage: python -I pdf_page_png.py fichier.pdf page(1-based) dpi sortie.png"""
import sys, pymupdf
doc = pymupdf.open(sys.argv[1]); p = doc[int(sys.argv[2]) - 1]
pix = p.get_pixmap(dpi=int(sys.argv[3])); pix.save(sys.argv[4]); print(pix.width, pix.height)
