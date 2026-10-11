"""Comparaison de séances le long d'un axe : pour chaque position cible, la prise la plus proche de chaque
séance, vue dans un azimut donné (grille). Lignes = positions, colonnes = séances.
Sortie : photos_non_versionnees/sequences/ (jamais versionné).

python sequences.py <nom> <azimut> <séances séparées par ,> x1,y1 x2,y2 ... [--dmax 7] [--tangage -10] [--fov 75]
  séance = date (AAAA-MM-JJ) éventuellement suffixée :mapillary ou :panoramax.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from chrono import candidats  # noqa: E402
from commun_chg import PHOTOS_NV, ecrire_json, police, rel  # noqa: E402
from paires import vue_dir  # noqa: E402


def voit(c, az, fov):
    """Une photo à plat ne montre l'azimut demandé que s'il est dans son champ."""
    if c["is360"]:
        return True
    d = (az - c["cam"].pose[3] + 180) % 360 - 180
    return abs(d) < 25


def sequences(nom, az, seances, positions, dmax=7.0, tangage=-10.0, fov=75.0, wh=(400, 290)):
    cands = candidats()
    grille, meta = [], []
    for (x, y) in positions:
        ligne = []
        for s in seances:
            date, _, src = s.partition(":")
            best = None
            for c in cands:
                if c["date"] != date or (src and c["src"] != src) or not voit(c, az, fov):
                    continue
                d = math.hypot(c["cam"].C[0] - x, c["cam"].C[1] - y)
                if d <= dmax and (best is None or d < best[0]):
                    best = (d, c)
            if best is None:
                ligne.append(None)
                continue
            c = best[1]
            lac = az if c["is360"] else float(c["cam"].pose[3])
            im = vue_dir(c, lac, tangage, fov, wh)
            cad = Image.new("RGB", (wh[0], wh[1] + 18), (20, 20, 20))
            cad.paste(im, (0, 18))
            cx, cy = c["cam"].C[:2]
            ImageDraw.Draw(cad).text((3, 1), f"{c['dt'][:16].replace('T', ' ')} {c['src'][:4]} {c['id'][:9]} ({cx:+.0f};{cy:+.0f}) az {lac:.0f}",
                                      fill=(255, 255, 255), font=police(12))
            ligne.append(cad)
            meta.append(dict(position_cible=[x, y], seance=s, src=c["src"], id=c["id"], date=c["dt"], lien=c["lien"],
                             auteur=c["auteur"], statut_pose=c["statut"], position_local=[round(float(cx), 1), round(float(cy), 1)]))
        grille.append(ligne)
    W, H = wh[0], wh[1] + 18
    pl = Image.new("RGB", (len(seances) * W + (len(seances) - 1) * 4, len(grille) * H + (len(grille) - 1) * 4 + 22), (70, 70, 70))
    for i, ligne in enumerate(grille):
        for j, im in enumerate(ligne):
            if im is not None:
                pl.paste(im, (j * (W + 4), 22 + i * (H + 4)))
    ImageDraw.Draw(pl).text((4, 3), f"{nom} : azimut {az:.0f}, colonnes {', '.join(seances)} — photos CC-BY-SA (non versionnées)",
                            fill=(255, 255, 255), font=police(14))
    out = PHOTOS_NV / "sequences"
    out.mkdir(parents=True, exist_ok=True)
    s = out / f"{nom}.jpg"
    pl.save(s, quality=86)
    ecrire_json(out / f"{nom}.json", {"azimut": az, "seances": seances, "vues": meta})
    print(rel(s))
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("nom")
    ap.add_argument("az", type=float)
    ap.add_argument("seances")
    ap.add_argument("pos", nargs="+")
    ap.add_argument("--dmax", type=float, default=7.0)
    ap.add_argument("--tangage", type=float, default=-10.0)
    ap.add_argument("--fov", type=float, default=75.0)
    g = ap.parse_args()
    sequences(g.nom, g.az, g.seances.split(","), [tuple(float(v) for v in p.split(",")) for p in g.pos], g.dmax, g.tangage, g.fov)
