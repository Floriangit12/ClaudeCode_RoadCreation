"""Comparaisons photo à positions homologues entre séances (2022 -> 2025), vues perspectives orientées
dans le repère local (azimut grille absolu) : une ligne par séance, une colonne par azimut.
Sortie : photos_non_versionnees/paires/ (jamais versionné ; photos CC-BY-SA, attribution dans le .json).

python paires.py <nom> <az1,az2,...> <cle1> <cle2> [...] [--tangage -12] [--fov 80]
  cle = id8 Panoramax (8 car.) ou m<id Mapillary> ; l'ordre des lignes est celui des clés.
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
from commun_chg import PHOTOS_NV, ecrire_json, police, rel  # noqa: E402
from projection import camera_virtuelle, reechantillonner  # noqa: E402


def par_cle():
    return {c["cle"]: c for c in candidats()}


def vue_dir(c, lacet, tangage=-12.0, fov=80.0, wh=(480, 340)):
    cv = camera_virtuelle(c["cam"], lacet, tangage, fov, wh)
    img = reechantillonner(c["cam"], image_de(c).astype(np.float32), cv)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def paires(nom, azs, cles, tangage=-12.0, fov=80.0, wh=(480, 340), dossier="paires"):
    idx = par_cle()
    lignes, meta = [], []
    for k in cles:
        c = idx.get(k) or next((v for kk, v in idx.items() if kk.startswith(k)), None)
        if c is None:
            print("clé inconnue", k)
            continue
        cel = []
        for az in azs:
            im = vue_dir(c, az, tangage, fov, wh)
            cad = Image.new("RGB", (wh[0], wh[1] + 18), (20, 20, 20))
            cad.paste(im, (0, 18))
            x, y = c["cam"].C[:2]
            ImageDraw.Draw(cad).text((3, 1), f"{c['dt'][:16].replace('T', ' ')} {c['src'][:4]} {c['id'][:10]} ({x:+.0f};{y:+.0f}) az {az:.0f}",
                                      fill=(255, 255, 255), font=police(12))
            cel.append(cad)
        lignes.append(cel)
        meta.append(dict(src=c["src"], id=c["id"], date=c["dt"], statut_pose=c["statut"], auteur=c["auteur"], lien=c["lien"],
                         position_local=[round(float(c["cam"].C[0]), 1), round(float(c["cam"].C[1]), 1)]))
    W, H = wh[0], wh[1] + 18
    pl = Image.new("RGB", (len(azs) * W + (len(azs) - 1) * 4, len(lignes) * H + (len(lignes) - 1) * 4 + 22), (70, 70, 70))
    for i, cel in enumerate(lignes):
        for j, im in enumerate(cel):
            pl.paste(im, (j * (W + 4), 22 + i * (H + 4)))
    ImageDraw.Draw(pl).text((4, 3), f"{nom} : azimuts grille {', '.join(f'{a:.0f}' for a in azs)} ; tangage {tangage} ; photos CC-BY-SA (non versionnées)",
                            fill=(255, 255, 255), font=police(14))
    out = PHOTOS_NV / dossier
    out.mkdir(parents=True, exist_ok=True)
    s = out / f"{nom}.jpg"
    pl.save(s, quality=88)
    ecrire_json(out / f"{nom}.json", {"azimuts": azs, "tangage": tangage, "fov": fov, "photos": meta})
    print(rel(s))
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("nom")
    ap.add_argument("azs")
    ap.add_argument("cles", nargs="+")
    ap.add_argument("--tangage", type=float, default=-12.0)
    ap.add_argument("--fov", type=float, default=80.0)
    g = ap.parse_args()
    paires(g.nom, [float(a) for a in g.azs.split(",")], g.cles, g.tangage, g.fov)
