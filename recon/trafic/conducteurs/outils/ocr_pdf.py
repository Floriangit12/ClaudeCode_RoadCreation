"""OCR d'un PDF scanne (pages choisies) -> texte par page, lecture par colonnes.
python -I ocr_pdf.py fichier.pdf sortie.txt [debut fin] [dpi]"""
import sys, site
sys.path.append(site.getusersitepackages())
import fitz, numpy as np
from rapidocr_onnxruntime import RapidOCR
src, out = sys.argv[1], sys.argv[2]
doc = fitz.open(src)
a = int(sys.argv[3]) if len(sys.argv) > 3 else 1
b = int(sys.argv[4]) if len(sys.argv) > 4 else len(doc)
dpi = int(sys.argv[5]) if len(sys.argv) > 5 else 200
eng = RapidOCR()
with open(out, 'w', encoding='utf-8') as fo:
    for i in range(a-1, b):
        pix = doc[i].get_pixmap(dpi=dpi)
        W = pix.w
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3].copy()
        res, _ = eng(img)
        fo.write(f"\n===== page PDF {i+1} =====\n")
        if not res:
            continue
        items = []
        for box, txt, conf in res:
            xs = [p[0] for p in box]; ys = [p[1] for p in box]
            x0, x1, y0 = min(xs), max(xs), min(ys)
            width = x1 - x0
            # colonne : 0 = gauche, 1 = droite, 2 = pleine largeur
            if width > 0.55 * W:
                col = 2
            else:
                col = 0 if (x0 + x1) / 2 < W / 2 else 1
            items.append((col, y0, x0, txt))
        two_cols = sum(1 for it in items if it[0] == 1) > 5 and sum(1 for it in items if it[0] == 0) > 5
        if two_cols:
            items.sort(key=lambda t: (1 if t[0] == 1 else 0, round(t[1] / 10), t[2]))
        else:
            items.sort(key=lambda t: (round(t[1] / 10), t[2]))
        for col, y, x, txt in items:
            fo.write(f"[c{col} y{int(y):4d}] {txt}\n")
        fo.flush()
        print('page', i + 1, len(res), flush=True)
