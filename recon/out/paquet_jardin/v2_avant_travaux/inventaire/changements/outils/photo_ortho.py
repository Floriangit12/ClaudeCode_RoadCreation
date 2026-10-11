"""Ortho-images de sol tirées des photos 360° calées d'une séance (2024-08-24, 2025-05-18...).

Chaque point d'une grille au sol (pas 5 cm, z = MNT du paquet) est projeté dans les photos 360° de la
séance dont la pose est calée (Panoramax « calee » ou Mapillary « calee_* ») ; on garde la photo la plus
proche à une distance horizontale de dmin..dmax m et sous une dépression < 19° (le capot masque en
dessous). Les objets en relief (voitures, mâts, végétation) sont « couchés » : seule la peinture et les
limites au sol sont lisibles. Erreur attendue : 0,1 à 0,3 m (pose ± 0,5°, MNT ± 5 cm).
Les images produites contiennent des pixels de photos de tiers : photos_non_versionnees/ seulement.

python photo_ortho.py <nom> <x0> <y0> <x1> <y1> [--dates 2024-08-24,2025-05-18] [--pas 0.05] [--dmax 14]
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from chrono import candidats, image_de  # noqa: E402
from commun_chg import PHOTOS_NV, Vue, assembler, boite_locale, ecrire_json, lire, rel  # noqa: E402
import camera as C  # noqa: E402

CALEES = ("calee", "calee_gcp", "calee_panoramax", "calee_bordures")


def ortho_seance(date, x0, y0, x1, y1, pas=0.05, dmin=5.5, dmax=14.0, dep_max=19.0):
    xs = np.arange(x0 + pas / 2, x1, pas)
    ys = np.arange(y1 - pas / 2, y0, -pas)
    X, Y = np.meshgrid(xs, ys)
    m = C.mnt()
    Z = np.asarray(m(X.ravel() + C.O[0], Y.ravel() + C.O[1]), float) - C.O[2]
    P = np.c_[X.ravel(), Y.ravel(), Z]
    best = np.full(len(P), np.inf)
    out = np.zeros((len(P), 3), np.float32)
    vues = []
    vu = set()
    for c in candidats():
        if c["date"] != date or not c["is360"] or c["statut"] not in CALEES:
            continue
        cam = c["cam"]
        cx, cy = cam.C[:2]
        if cx < x0 - dmax or cx > x1 + dmax or cy < y0 - dmax or cy > y1 + dmax:
            continue
        # même prise publiée sur Panoramax et Mapillary : une seule
        cle = (round(cx, 0), round(cy, 0))
        if cle in vu:
            continue
        vu.add(cle)
        dh = np.hypot(P[:, 0] - cx, P[:, 1] - cy)
        dep = np.degrees(np.arctan2(cam.C[2] - P[:, 2], dh))
        ok = (dh >= dmin) & (dh <= dmax) & (dep < dep_max) & (dh < best)
        if not ok.any():
            continue
        uv, _, _ = cam.projeter(P[ok])
        img = image_de(c)
        val = C.echantillonner(img.astype(np.float32), uv[:, 0], uv[:, 1], boucle=True)
        idx = np.nonzero(ok)[0]
        out[idx] = val
        best[idx] = dh[ok]
        vues.append(dict(src=c["src"], id=c["id"], date=c["dt"], statut_pose=c["statut"], lien=c["lien"],
                         position_local=[round(float(cx), 2), round(float(cy), 2)]))
    im = out.reshape(len(ys), len(xs), 3)
    im[~np.isfinite(best.reshape(len(ys), len(xs)))] = 0
    return Image.fromarray(np.clip(im, 0, 255).astype(np.uint8)), vues, float(np.isfinite(best).mean())


def planche(nom, x0, y0, x1, y1, dates=("2024-08-24", "2025-05-18"), pas=0.05, dmax=14.0, px=700):
    b = boite_locale(x0, y0, x1, y1)
    L = x1 - x0
    g = 1.0 if L <= 25 else 5.0
    pans = [Vue("2022", b, px).grille(g, 5 if g == 1 else 10).im]
    meta = {}
    for d in dates:
        im, vues, couv = ortho_seance(d, x0, y0, x1, y1, pas, dmax=dmax)
        im = im.resize((px, round(px * im.height / im.width)), Image.LANCZOS)
        v = Vue("2024", b, px, titre=f"photos 360° calées {d} (sol, couverture {couv:.0%})", im=im)
        pans.append(v.grille(g, 5 if g == 1 else 10).im)
        meta[d] = {"couverture": round(couv, 3), "photos": vues}
    pans.insert(1, Vue("2024", b, px).grille(g, 5 if g == 1 else 10).im)
    out = PHOTOS_NV / "photo_ortho"
    out.mkdir(parents=True, exist_ok=True)
    s = out / f"{nom}.jpg"
    assembler(pans, f"{nom} : PCRS 2022 | IGN 2024 | sol vu par les photos {' | '.join(dates)} (pixels de photos CC-BY-SA, non versionné)",
              ncol=2 if len(pans) == 4 else len(pans)).save(s, quality=88)
    ecrire_json(out / f"{nom}.json", {"boite_local": [x0, y0, x1, y1], "pas_m": pas, "seances": meta})
    print(rel(s), {d: meta[d]["couverture"] for d in meta})
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("nom")
    ap.add_argument("x0", type=float)
    ap.add_argument("y0", type=float)
    ap.add_argument("x1", type=float)
    ap.add_argument("y1", type=float)
    ap.add_argument("--dates", default="2024-08-24,2025-05-18")
    ap.add_argument("--pas", type=float, default=0.05)
    ap.add_argument("--dmax", type=float, default=14.0)
    ap.add_argument("--px", type=int, default=700)
    g = ap.parse_args()
    planche(g.nom, g.x0, g.y0, g.x1, g.y1, tuple(g.dates.split(",")), g.pas, g.dmax, g.px)
