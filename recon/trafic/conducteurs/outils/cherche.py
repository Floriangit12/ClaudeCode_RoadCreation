"""Recherche plein texte page par page dans des PDF (non fiables) : python -I cherche.py motif fichier1.pdf [...]
Affiche: fichier, page PDF (1-based), extrait."""
import sys, re
import fitz
motif = re.compile(sys.argv[1], re.I)
ctx = 220
for f in sys.argv[2:]:
    try:
        doc = fitz.open(f)
    except Exception as e:
        print("ERR", f, e); continue
    import os; name = os.path.basename(f)
    for i, page in enumerate(doc):
        t = page.get_text().replace('\n', ' ')
        for m in motif.finditer(t):
            a = max(0, m.start()-ctx); b = min(len(t), m.end()+ctx)
            print(f"[{name} p.{i+1}] ...{t[a:b]}...")
            print()
