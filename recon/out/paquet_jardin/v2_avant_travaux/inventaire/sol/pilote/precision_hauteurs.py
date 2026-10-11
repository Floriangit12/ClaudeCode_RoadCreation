"""Précision mesurée des hauteurs de vue et du nivellement selon la source LiDAR 2021 disponible sur le PC.

Référence : bordures_hauteurs.geojson du paquet v1 (tronçons de 1 m, médianes des POINTS sol classe 2 du LiDAR
HD 2021 : dessus à 0,25–0,8 m derrière la ligne, fil d'eau à 0,1–0,6 m devant), statut « mesuree »,
≥ 5 points de chaque côté, hors zone de travaux et hors bordures créées après 2021.
Sources testées sur les mêmes profils perpendiculaires :
  hm  : heightmap 16 bits 10 cm du paquet v1 (TIN des points sol débruité), seulement si les deux côtés sont
        hors zones modifiées (côté bas en chaussée 2026 lissée admis) ;
  jpg : MNT 15 cm JPEG couleur décodé (dtm_jpg.py).
Sortie : ../precision_hauteurs.json
Usage : python -I precision_hauteurs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np

import commun_sol as C
from dtm_jpg import MNT2021Jpg


def q(e):
    e = np.asarray(e)
    e = e[np.isfinite(e)]
    if not len(e):
        return None
    a = np.abs(e)
    return {"n": int(len(e)), "biais_m": round(float(np.median(e)), 4), "abs_p50_m": round(float(np.median(a)), 4),
            "abs_p90_m": round(float(np.percentile(a, 90)), 4), "abs_p95_m": round(float(np.percentile(a, 95)), 4)}


def main():
    hm, jpg, zm = C.Heightmap(), MNT2021Jpg(), C.ZonesModifiees()
    F = C.lire_json(C.PAQUET / "relief/bordures_hauteurs.geojson")["features"]
    oh = np.arange(0.25, 0.801, 0.05)
    ob = np.arange(0.10, 0.601, 0.05)
    rec = {"hm": {"h": [], "z_fil": [], "z_dessus": []}, "jpg": {"h": [], "z_fil": [], "z_dessus": []}}
    href, hcl = [], []
    for f in F:
        p = f["properties"]
        if p.get("statut") != "mesuree" or p.get("zone_travaux_2025") or p.get("creee_apres_2021"):
            continue
        if (p.get("n_pts_dessus") or 0) < 5 or (p.get("n_pts_fil_eau") or 0) < 5:
            continue
        P = np.asarray(f["geometry"]["coordinates"], float)[:, :2]
        if len(P) < 2:
            continue
        m = P.mean(0)
        t = P[-1] - P[0]
        t /= max(np.linalg.norm(t), 1e-9)
        n = np.array([-t[1], t[0]]) * (1 if p.get("cote_haut") == "gauche" else -1)
        H = m + oh[:, None] * n
        B = m - ob[:, None] * n
        loc_h, loc_b = H - C.O, B - C.O
        ch, cb = zm(loc_h[:, 0], loc_h[:, 1]), zm(loc_b[:, 0], loc_b[:, 1])
        h_ref = p["h_lidar_2021_m"]
        href.append(h_ref)
        for nom, src, ok in (("hm", hm, (ch == 0).all() and (cb <= 1).all()), ("jpg", jpg, True)):
            if not ok:
                continue
            zh = float(np.median(src(H[:, 0], H[:, 1])))
            zb = float(np.median(src(B[:, 0], B[:, 1])))
            rec[nom]["h"].append((zh - zb) - h_ref)
            rec[nom]["z_fil"].append(zb - p["z_fil_eau_2021_m"])
            rec[nom]["z_dessus"].append(zh - p["z_dessus_2021_m"])
    out = {"reference": "bordures_hauteurs.geojson (points sol LiDAR 2021, statut mesuree, >= 5 points par cote)",
           "n_troncons_reference": len(href),
           "h_vue_reference_m": {"p10": round(float(np.percentile(href, 10)), 3), "p50": round(float(np.median(href)), 3),
                                 "p90": round(float(np.percentile(href, 90)), 3)}}
    for nom in rec:
        out[nom] = {k: q(v) for k, v in rec[nom].items()}
    C.ecrire_json(C.SORTIE / "precision_hauteurs.json", out)
    print(out)


if __name__ == "__main__":
    main()
