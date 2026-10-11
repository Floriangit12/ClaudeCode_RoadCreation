"""Bordures d'avant travaux absentes des sources vectorielles : crêtes de pente LiDAR 2021 (raster 15 cm, palette
décodée, rouge) du cœur (± 40 m) qui ne sont à moins de 0,6 m d'aucune ligne GAM SOL_BORDURE ni PCRS 2019
(bordures), dont le pourtour (0,15–1,05 m) est plat à plus de 60 % (bordure ou îlot isolé dans un sol plat), d'étendue
3,5 m au moins (les pieds de mâts font des anneaux de ≈ 2,5 m dans le TIN), d'aire ≤ 80 m² et minérale sur l'ortho
2022 (ExG médian ≤ 12 : exclut talus et massifs végétalisés).
Longueur estimée = aire des composantes / largeur médiane d'une crête de bordure (mesurée sur les crêtes
couvertes par une ligne). Sorties : ../cretes_sans_ligne.json, ../planches/cretes_sans_ligne_coeur.jpg
Usage : python -I cretes_sans_ligne.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image, ImageDraw

import commun_sol as C
import geom_contours as G

BBOX = (-40.0, -40.0, 40.0, 40.0)
RES = 0.15


def main():
    R = C.sources_raster()
    X, Y = C.grille(BBOX, RES)
    pn = C.pente_norm(R["pente2021"].echantillonner(X, Y))
    crete = pn >= 0.8
    rgb = R["ortho2022"].echantillonner(X, Y).astype(float)
    exg = 2 * rgb[..., 1] - rgb[..., 0] - rgb[..., 2]
    lig = []
    for chem, filtre in (("vector/gam_topo_sol_bordure_lin.geojson", None),
                         ("vector/gam_limite_voirie_pcrs.geojson", lambda p: "Bordure" in (p.get("calque") or ""))):
        lig += [P for _, _, P, _ in C.charger_lignes(C.SITE / chem, wgs=True, filtre=filtre)
                if ((P[:, 0] > BBOX[0] - 2) & (P[:, 0] < BBOX[2] + 2) & (P[:, 1] > BBOX[1] - 2) & (P[:, 1] < BBOX[3] + 2)).any()]
    xs, ys = X[0] - C.O[0], Y[:, 0] - C.O[1]
    Q = np.c_[np.repeat(xs[None], len(ys), 0).ravel(), np.repeat(ys[:, None], len(xs), 1).ravel()]
    sel = crete.ravel()
    d = np.full(len(Q), np.inf)
    idx = np.flatnonzero(sel)
    for P in lig:
        if len(P) >= 2:
            d[idx] = np.minimum(d[idx], C.dist_point_segments(Q[idx], P))
    d = d.reshape(crete.shape)
    couverte = crete & (d <= 0.6)
    libre = crete & (d > 0.6)
    lab, n = G.composantes(libre)
    comps = []
    px = RES * RES
    garde = np.zeros_like(libre)
    for k in range(1, n + 1):
        m = lab == k
        a = m.sum() * px
        rr, cc = np.nonzero(m)
        ext = max(np.ptp(rr), np.ptp(cc)) * RES
        if a < 0.5 or ext < 3.5 or a > 80:
            continue                                # pieds de mâts (trous du TIN), véhicules, bruit ; terrain
        if np.median(exg[m]) > 12:
            continue                                # végétation (talus, massifs) : crête du sol naturel
        # crête isolée dans un sol plat (bordure, îlot) et non crête diffuse (talus, chantier, végétation) :
        # anneau de 0,15–1,05 m autour de la composante plat (pente < 0,5) à plus de 60 %
        anneau = G.dilater(m, 7) & ~G.dilater(m, 1)
        if (pn[anneau] < 0.5).mean() < 0.6:
            continue
        garde |= m
        comps.append({"aire_m2": round(float(a), 2), "etendue_m": round(float(ext), 1),
                      "centre_local": [round(float(xs[int(cc.mean())]), 1), round(float(ys[int(rr.mean())]), 1)]})
    larg = 0.6
    out = {"bbox_local": BBOX, "seuil_distance_m": 0.6, "aire_cretes_couvertes_m2": round(float(couverte.sum() * px), 1),
           "aire_cretes_sans_ligne_retenues_m2": round(float(garde.sum() * px), 1),
           "largeur_crete_supposee_m": larg, "longueur_estimee_sans_ligne_m": round(float(garde.sum() * px / larg), 1),
           "n_composantes": len(comps), "composantes": sorted(comps, key=lambda c: -c["aire_m2"])[:20]}
    C.ecrire_json(C.SORTIE / "cretes_sans_ligne.json", out)
    a = R["ortho2022"].echantillonner(*C.grille(BBOX, 0.075)).astype(float)
    im = Image.fromarray(a.astype(np.uint8))
    up = np.kron(garde, np.ones((2, 2), bool))[:a.shape[0], :a.shape[1]]
    upc = np.kron(couverte, np.ones((2, 2), bool))[:a.shape[0], :a.shape[1]]
    b = np.asarray(im).astype(float)
    hh, ww = min(b.shape[0], up.shape[0]), min(b.shape[1], up.shape[1])
    b = b[:hh, :ww]
    b[upc[:hh, :ww]] = b[upc[:hh, :ww]] * 0.5 + np.array([0, 200, 0]) * 0.5
    b[up[:hh, :ww]] = b[up[:hh, :ww]] * 0.2 + np.array([255, 0, 0]) * 0.8
    im = Image.fromarray(b.astype(np.uint8))
    dr = ImageDraw.Draw(im)
    for P in lig:
        C.tracer(dr, P, BBOX, 0.075, (255, 255, 0), 1)
    C.cartouche(im, "coeur : crete LiDAR 2021 couverte par GAM/PCRS (vert) | sans ligne vectorielle (rouge) | jaune lignes GAM + PCRS", 13)
    C.echelle(im, 0.075, 5)
    im.save(C.SORTIE / "planches" / "cretes_sans_ligne_coeur.jpg", quality=90)
    print(out)


if __name__ == "__main__":
    main()
