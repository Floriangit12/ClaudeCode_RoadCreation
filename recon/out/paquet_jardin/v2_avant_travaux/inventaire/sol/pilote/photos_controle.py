"""Contrôle photo (Panoramax 2024-2025, avant le 23/06/2025) des géométries et matériaux du pilote.

Pour chaque cible (îlots IA-1 / IA-2 de la zone A, abaissé et îlot de la zone B), on cherche les photos
calées et acceptées (poses.json) d'avant travaux qui la voient à moins de 30 m, on extrait une découpe
perspective (outil recon/pcg/enrichir/projection.py, lecture seule) et on y projette le contour extrait du
pilote (z = MNT 2021 JPEG + vue mesurée). Vignettes de photos de tiers : écrites UNIQUEMENT dans
../photos_non_versionnees/ (ignoré par git).
Usage : python -I photos_controle.py
"""
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import numpy as np
from PIL import ImageDraw

import commun_sol as C

sys.path.insert(1, str(C.RACINE / "recon/pcg/enrichir"))
import projection as PR  # noqa: E402
from camera import charger_poses  # noqa: E402
from dtm_jpg import MNT2021Jpg  # noqa: E402

DEBUT_TRAVAUX = "2025-06-23"
SORTIE = C.SORTIE / "photos_non_versionnees"


def cibles():
    out = []
    for f in C.lire_json(C.SORTIE / "pilote_A/ilots_avant_travaux.geojson")["features"]:
        P = np.asarray(f["geometry"]["coordinates"][0], float)[:, :2] - C.O
        out.append((f["properties"]["id"], P, 0.15))
    for f in C.lire_json(C.SORTIE / "pilote_B/bordure_rive_B.geojson")["features"]:
        P = np.asarray(f["geometry"]["coordinates"], float)[:, :2] - C.O
        out.append(("KB-1", P, 0.0))
    return out


def main():
    SORTIE.mkdir(exist_ok=True)
    jpg = MNT2021Jpg()
    poses = charger_poses()
    ok = [p for p in poses.values() if p.get("accepte") and p.get("date", "9") < DEBUT_TRAVAUX]
    bilan = []
    for cid, P, dz in cibles():
        c = P.mean(0)
        cands = []
        for p in ok:
            pose = p.get("pose") or {}
            if not pose:
                continue
            d = float(np.hypot(pose["x"] - c[0], pose["y"] - c[1]))
            if d < 30:
                cands.append((d, p))
        cands.sort(key=lambda t: t[0])
        for d, p in cands[:2]:
            pid = p["id8"]
            cam, statut = PR.camera_calee(pid)
            z = jpg(P[:, 0] + C.O[0], P[:, 1] + C.O[1]) - C.ZO + dz
            P3 = np.c_[P, z]
            lacet = float(np.degrees(np.arctan2(c[0] - cam.C[0], c[1] - cam.C[1])))
            dist = float(np.hypot(c[0] - cam.C[0], c[1] - cam.C[1]))
            tang = float(np.degrees(np.arctan2(-(cam.C[2] - z.mean()), dist)))
            fov = float(np.clip(np.degrees(2 * np.arctan2(np.ptp(P, 0).max() * 0.8 + 2, dist)), 30, 90))
            img, cv = PR.decoupe_perspective(pid, lacet, tang, fov, (1000, 750), cam=cam)
            uv, devant, _ = cv.projeter(P3)
            dr = ImageDraw.Draw(img)
            pts = [tuple(q) for q, v in zip(uv.tolist(), devant) if v]
            if len(pts) > 1:
                dr.line(pts, fill=(255, 255, 0), width=2)
            dr.rectangle([0, 0, 1000, 22], fill=(0, 0, 0))
            dr.text((4, 4), f"{cid} | Panoramax {p['date']} {pid} ({statut}) | jaune : contour avant travaux du pilote | d = {dist:.1f} m",
                    fill=(255, 255, 255), font=C.police(13))
            nom = f"{cid}_{p['date']}_{pid}.jpg"
            img.save(SORTIE / nom, quality=88)
            bilan.append({"cible": cid, "photo": pid, "date": p["date"], "distance_m": round(dist, 1), "fichier": nom})
    C.ecrire_json(SORTIE / "bilan_photos.json", bilan)
    print(bilan)


if __name__ == "__main__":
    main()
