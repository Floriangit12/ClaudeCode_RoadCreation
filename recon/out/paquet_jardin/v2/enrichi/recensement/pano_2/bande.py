"""bande.py : bandes azimut/élévation d'une photo 360° avec la description superposée (contrôle de pose).

Dans la grille (azimut, élévation) du repère local, la projection des entités ne dépend que du centre C ;
un défaut de lacet décale la photo horizontalement, un défaut de position déforme selon la distance.
  python bande.py <id8> [--pose x y z lacet tangage roulis] [--el -25 20] [--pas 0.1] [--nom suffixe]
Sortie : crops/<id8>_bande_<k><suffixe>.jpg (k = 0 : azimuts 0-180°, 1 : 180-360°).
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import overlay_pnx as OV  # noqa: E402
from camera import camera, image_rgb, intrinseques, photo  # noqa: E402
from projection import fenetre_azel  # noqa: E402


def bandes(pid, pose=None, el0=-25.0, el1=20.0, pas=0.1, nom="", dmax=60.0):
    ph = photo(pid)
    if pose is None:
        cam, st = OV.camera_photo(ph.id8)
    else:
        cam, st = camera(ph, np.array(pose, float), intrinseques(ph)), "pose fournie"
    img = image_rgb(ph.id8).astype(np.float32)
    C = cam.C
    out = []
    for k, (a0, a1) in enumerate(((0.0, 180.0), (180.0, 360.0))):
        vals, az, el, ok = fenetre_azel(cam, img, a0, a1, el0, el1, pas)
        im = Image.fromarray(np.clip(vals, 0, 255).astype(np.uint8))
        dr = ImageDraw.Draw(im)
        fnt = OV._police(11)

        def px(P):
            d = P - C
            a = (np.degrees(np.arctan2(d[:, 0], d[:, 1])) % 360.0)
            e = np.degrees(np.arctan2(d[:, 2], np.hypot(d[:, 0], d[:, 1])))
            return np.c_[(a - a0) / pas, (el1 - e) / pas], a
        for e in OV.entites():
            if e["kind"] == "ligne":
                P = e["P"]
                dd = np.hypot(P[:, 0] - C[0], P[:, 1] - C[1])
                k_ = (dd < dmax) & (dd > 2.0)
                if k_.sum() < 2:
                    continue
                uv, a = px(P)
                for i in range(len(P) - 1):
                    if k_[i] and k_[i + 1] and abs(uv[i, 0] - uv[i + 1, 0]) < 200 and a0 <= a[i] < a1:
                        dr.line([tuple(uv[i]), tuple(uv[i + 1])], fill=e["coul"], width=1)
            elif e["kind"] in ("mat", "arbre"):
                f = e["foot"]
                dd = math.hypot(f[0] - C[0], f[1] - C[1])
                if dd > dmax or dd < 1.5:
                    continue
                uv, a = px(np.vstack([f, f + [0, 0, e["h"]]]))
                if not (a0 <= a[0] < a1):
                    continue
                dr.line([tuple(uv[0]), tuple(uv[1])], fill=e["coul"], width=2 if e["kind"] == "mat" else 1)
                if e["kind"] == "mat":
                    dr.text((uv[0, 0] + 3, uv[0, 1] - 12), e["id"][:22], fill=e["coul"], font=fnt)
        OV.cartouche(im, f"{ph.id8} {ph.date} az {a0:.0f}-{a1:.0f} el {el0:.0f}..{el1:.0f} | {st}")
        f_ = OV.CROPS / f"{ph.id8}_bande_{k}{nom}.jpg"
        im.save(f_, quality=88)
        out.append(f_.name)
    print(out)
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    pose = None
    if "--pose" in a:
        i = a.index("--pose")
        pose = [float(x) for x in a[i + 1:i + 7]]
    el = (-25.0, 20.0)
    if "--el" in a:
        i = a.index("--el")
        el = (float(a[i + 1]), float(a[i + 2]))
    nom = a[a.index("--nom") + 1] if "--nom" in a else ""
    bandes(a[0], pose, el[0], el[1], nom=nom)
