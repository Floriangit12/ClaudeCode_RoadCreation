"""Affiche le texte d'une ou plusieurs pages d'un PDF : python -I page.py fichier.pdf 12 13"""
import sys, fitz
doc = fitz.open(sys.argv[1])
for p in sys.argv[2:]:
    i = int(p)
    print(f"===== page PDF {i} / {len(doc)} =====")
    print(doc[i-1].get_text())
