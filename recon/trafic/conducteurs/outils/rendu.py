"""Rend une page PDF en PNG a une resolution donnee : python -I rendu.py fichier.pdf page dpi sortie.png"""
import sys, fitz
doc = fitz.open(sys.argv[1]); p = int(sys.argv[2]); dpi = int(sys.argv[3])
pix = doc[p-1].get_pixmap(dpi=dpi)
pix.save(sys.argv[4]); print(sys.argv[4], pix.width, pix.height)
