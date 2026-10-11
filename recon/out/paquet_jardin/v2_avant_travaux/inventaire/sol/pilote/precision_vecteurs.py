"""Cohérence planimétrique GAM SOL_BORDURE / PCRS 2019 et justesse du Z du PCRS 2019 (seule source vectorielle
avec altitude) par rapport au sol nu LiDAR 2021 (heightmap v1, hors zones modifiées).

- Planimétrie : pour chaque échantillon (0,5 m) d'une bordure PCRS 2019 classée « relief_2021 » par dater_gam.py,
  distance à la ligne GAM la plus proche ; on ne garde que < 0,5 m (même bordure).
- Altimétrie : chaque sommet PCRS (Z NGF) comparé au sol LiDAR 2021 à ± 0,4 m de part et d'autre de la ligne
  (dessus = côté haut, pied = côté bas) ; on retient l'écart au plus proche des deux (le PCRS ne dit pas quelle
  arête est levée) et l'on compte laquelle.
Sortie : ../precision_vecteurs.json
Usage : python -I precision_vecteurs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np

import commun_sol as C


def q(e):
    e = np.asarray(e, float)
    a = np.abs(e)
    return {"n": int(len(e)), "biais_m": round(float(np.median(e)), 3), "abs_p50_m": round(float(np.median(a)), 3),
            "abs_p90_m": round(float(np.percentile(a, 90)), 3)}


def main():
    hm, zm = C.Heightmap(), C.ZonesModifiees()
    gam = [P for _, _, P, _ in C.charger_lignes(C.SITE / "vector/gam_topo_sol_bordure_lin.geojson", wgs=True) if len(P) >= 2]
    D = C.lire_json(C.SORTIE / "datation/gam_bordures_datation.geojson")["features"]
    pc = [np.asarray(f["geometry"]["coordinates"], float)[:, :2] - C.O for f in D
          if f["properties"]["source"] == "pcrs2019" and f["properties"]["classe"] == "relief_2021"]
    dist = []
    for P in pc:
        Q, _, _ = C.reechantillonner(P, 0.5) if len(P) >= 2 else (P, None, None)
        d = np.full(len(Q), np.inf)
        for G_ in gam:
            if np.hypot(*(G_.mean(0) - Q.mean(0))) < 80:
                d = np.minimum(d, C.dist_point_segments(Q, G_))
        dist += d[d < 0.5].tolist()
    dist = np.asarray(dist)
    plan = {"n_echantillons": int(len(dist)), "p50_m": round(float(np.median(dist)), 3), "p90_m": round(float(np.percentile(dist, 90)), 3),
            "part_sous_5cm": round(float((dist < 0.05).mean()), 3)}
    # altimétrie PCRS
    e_haut, e_bas, choix = [], [], []
    for _, p, P, z in C.charger_lignes(C.SITE / "vector/gam_limite_voirie_pcrs.geojson", wgs=True,
                                       filtre=lambda p: "Bordure" in (p.get("calque") or "")):
        if z is None or len(P) < 2:
            continue
        T = np.gradient(P, axis=0)
        T /= np.maximum(np.linalg.norm(T, axis=1)[:, None], 1e-9)
        N = np.c_[-T[:, 1], T[:, 0]]
        A, B = P + 0.4 * N, P - 0.4 * N
        ok = (zm(A[:, 0], A[:, 1]) == 0) & (zm(B[:, 0], B[:, 1]) == 0) & (zm(P[:, 0], P[:, 1]) == 0)
        za, zb = hm(*(A + C.O).T), hm(*(B + C.O).T)
        zh, zl = np.maximum(za, zb), np.minimum(za, zb)
        marche = (zh - zl) > 0.05
        k = ok & marche & (z > 100)
        if not k.any():
            continue
        dh, dl = z[k] - zh[k], z[k] - zl[k]
        e_haut += dh.tolist()
        e_bas += dl.tolist()
        choix += np.where(np.abs(dh) < np.abs(dl), "dessus", "pied").tolist()
    e_haut, e_bas, choix = np.asarray(e_haut), np.asarray(e_bas), np.asarray(choix)
    alti = {"n_sommets": int(len(choix)), "part_plus_proche_du_dessus": round(float((choix == "dessus").mean()), 3),
            "ecart_au_dessus": q(e_haut), "ecart_au_pied": q(e_bas),
            "ecart_au_plus_proche": q(np.where(np.abs(e_haut) < np.abs(e_bas), e_haut, e_bas))}
    out = {"planimetrie_pcrs2019_vs_gam": plan, "altimetrie_pcrs2019_vs_lidar2021": alti}
    C.ecrire_json(C.SORTIE / "precision_vecteurs.json", out)
    print(out)


if __name__ == "__main__":
    main()
