"""Planche 2022 | 2024 | 2025 d'une boîte locale : python zoom.py nom x0 y0 x1 y1 [px] [sources...]."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_chg import *  # noqa


def zoom(nom, x0, y0, x1, y1, px=600, sources=("2022", "2024", "2025"), dossier="revue_zoom", pas=None):
    b = boite_locale(x0, y0, x1, y1)
    L = x1 - x0
    pas = pas or (1.0 if L <= 20 else (5.0 if L <= 80 else 10.0))
    et = 5.0 if pas <= 1 else (10.0 if pas <= 5 else 50.0)
    pans = [Vue(k, b, px).grille(pas, et).im for k in sources]
    out = PLANCHES / dossier
    out.mkdir(parents=True, exist_ok=True)
    s = out / f"{nom}.jpg"
    assembler(pans, f"{nom} : local x {x0:+.0f}..{x1:+.0f}, y {y0:+.0f}..{y1:+.0f} (grille {pas:g} m) ; {L / px * 100:.1f} cm/px").save(s, quality=90)
    return s


if __name__ == "__main__":
    a = sys.argv[1:]
    nom, c = a[0], [float(v) for v in a[1:5]]
    px = int(a[5]) if len(a) > 5 else 600
    src = tuple(a[6:]) if len(a) > 6 else ("2022", "2024", "2025")
    print(zoom(nom, *c, px=px, sources=src))
