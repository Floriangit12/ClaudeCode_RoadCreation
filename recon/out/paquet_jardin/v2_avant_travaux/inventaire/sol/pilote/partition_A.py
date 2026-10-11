"""Pilote A, suite : partition du sol AVANT travaux de la zone A sans recouvrement ni trou, largeur de tête des
bordures mesurée sur l'ortho 2022, et comparaison avec la description v2 2026 (îlots I-0390 / I-0629, surfaces).

Faces (anneaux partagés, aucune arête dupliquée à la main) :
  chaussée  = rectangle de la zone − anneaux « arête avant » des îlots ;
  emprise_bordure(i) = anneau arête avant − anneau arête arrière (décalé vers l'intérieur de la largeur de tête
                       mesurée, médiane par îlot) ;
  remplissage(i) = intérieur de l'arête arrière (galets, vu sur photo Panoramax 2025-05-18 et ortho 2022).
Contrôle : rasterisation exacte (centres de pixels, 2 cm) -> recouvrement, trou, somme des aires = aire de la zone.
Sorties : ../pilote_A/partition_A.geojson (L93), ../pilote_A/comparaison_v2_A.json, ../planches/A_partition.jpg
Usage : python -I partition_A.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image, ImageDraw

import commun_sol as C
import geom_contours as G

BBOX = (-4.0, -34.0, 20.0, -6.0)
RES = 0.02


def ring(geom):
    return np.asarray(geom["coordinates"][0], float)[:-1, :2] - C.O


def largeur_tete(src, P):
    """Distance entre l'arête extérieure (P) et l'arête intérieure tête claire / remplissage plus sombre."""
    T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    N = np.c_[T[:, 1], -T[:, 0]]
    offs = np.arange(-0.45, 0.0001, 0.01)
    Gq = P[:, None, :] + offs[None, :, None] * N[:, None, :]
    L = C.luminance(src.echantillonner(Gq[..., 0] + C.O[0], Gq[..., 1] + C.O[1]))
    k = 5
    cs = np.c_[np.zeros(len(L)), np.cumsum(L, 1)]
    cand = np.arange(k, len(offs) - k)
    dedans = (cs[:, cand] - cs[:, cand - k]) / k            # côté intérieur (remplissage)
    dehors = (cs[:, cand + k] - cs[:, cand]) / k            # côté tête
    sc = dehors - dedans
    i = np.argmax(sc[:, :len(cand) - 3], 1)                 # au moins 3 cm de tête
    w = -(offs[cand[i]])
    return w, sc[np.arange(len(sc)), i]


def decaler(P, d):
    T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    N = np.c_[T[:, 1], -T[:, 0]]
    return P - d * N


def iou(A, B, res=0.02):
    allp = np.vstack([A, B])
    x0, y1 = allp[:, 0].min() - 0.1, allp[:, 1].max() + 0.1
    W = int((allp[:, 0].max() + 0.1 - x0) / res) + 1
    H = int((y1 - allp[:, 1].min() + 0.1) / res) + 1
    ma = np.zeros((H, W), bool)
    mb = np.zeros((H, W), bool)
    for P, m in ((A, ma), (B, mb)):
        r0, c0, mm = G.remplir_scanline([P], x0, y1, res, W, H)
        m[r0:r0 + mm.shape[0], c0:c0 + mm.shape[1]] = mm
    return float((ma & mb).sum() / max(1, (ma | mb).sum())), float(ma.sum() * res * res), float(mb.sum() * res * res)


def main():
    R = C.sources_raster()
    F = C.lire_json(C.SORTIE / "pilote_A/ilots_avant_travaux.geojson")["features"]
    x0, y0, x1, y1 = BBOX
    cadre = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
    faces = [("chaussee", "enrobe_bbsg_ancien", [cadre] + [ring(f["geometry"]) for f in F])]
    mesures = {}
    for f in F:
        P = ring(f["geometry"])
        if G.aire(P) < 0:
            P = P[::-1]
        w, force = largeur_tete(R["ortho2022"], P)
        ok = force > 15
        wm = float(np.median(w[ok])) if ok.any() else 0.15
        Pi = decaler(P, wm)
        g1i = G.controles_g1(G.reechantillonner_ferme(Pi, 0.10)[0], 0.10)
        faces.append((f"emprise_bordure {f['properties']['id']}", "beton_bordure_blanc", [P, Pi]))
        faces.append((f"remplissage {f['properties']['id']}", "galets_20_40", [Pi]))
        mesures[f["properties"]["id"]] = {"largeur_tete_m": {"p25": round(float(np.percentile(w[ok], 25)), 3), "p50": round(wm, 3),
                                                              "p75": round(float(np.percentile(w[ok], 75)), 3), "part_mesurable": round(float(ok.mean()), 2)},
                                          "anneau_arriere_G1": g1i}
    # contrôle de partition
    W, H = int((x1 - x0) / RES), int((y1 - y0) / RES)
    cpt = np.zeros((H, W), np.uint8)
    aires = {}
    for nom, mat, anneaux in faces:
        r0, c0, m = G.remplir_scanline(anneaux, x0, y1, RES, W, H)
        cpt[r0:r0 + m.shape[0], c0:c0 + m.shape[1]] += m
        aires[nom] = round(float(m.sum() * RES * RES), 3)
    part = {"recouvrement_m2": round(float((cpt >= 2).sum() * RES * RES), 4), "trou_m2": round(float((cpt == 0).sum() * RES * RES), 4),
            "somme_des_aires_m2": round(sum(aires.values()), 2), "aire_zone_m2": round((x1 - x0) * (y1 - y0), 2),
            "aires_par_face_m2": aires}
    # ---- comparaison v2 2026
    I = C.lire_json(C.V2 / "description/base/ilots.geojson")["features"]
    K = {f["properties"]["id"]: f for f in C.lire_json(C.V2 / "description/base/bordures.geojson")["features"]}
    comp = []
    for f in F:
        P = ring(f["geometry"])
        best = None
        for g in I:
            Q = np.asarray(g["geometry"]["coordinates"][0], float)[:-1, :2] - C.O
            if np.hypot(*(Q.mean(0) - P.mean(0))) < 8:
                j, a, b = iou(P, Q)
                if best is None or j > best[0]:
                    vues = []
                    for kid in g["properties"].get("ceinture") or []:
                        if kid in K:
                            vues += [iv["vue_m"] for iv in K[kid]["properties"]["intervalles"]]
                    best = (j, g["properties"]["id"], a, b, g["properties"]["type"], g["properties"]["remplissage"]["materiau_id"],
                            vues, float(np.hypot(*(Q.mean(0) - P.mean(0)))))
        if best:
            comp.append({"avant": f["properties"]["id"], "v2_2026": best[1], "iou": round(best[0], 3), "aire_avant_m2": round(best[2], 2),
                         "aire_v2_m2": round(best[3], 2), "type_v2": best[4], "remplissage_v2": best[5], "remplissage_avant": "galets_20_40",
                         "vues_ceinture_v2_m": sorted(set(round(v, 3) for v in best[6])), "decalage_centres_m": round(best[7], 2)})
    out = {"partition_avant": part, "bordures_ilots": mesures, "comparaison_ilots_v2": comp}
    C.ecrire_json(C.SORTIE / "pilote_A/comparaison_v2_A.json", out)
    feats = [{"type": "Feature", "properties": {"face": nom, "materiau_id": mat, "aire_m2": aires[nom], "date_etat": "2021-08..2025-06"},
              "geometry": {"type": "Polygon", "coordinates": [np.round(np.r_[r, r[:1]] + C.O, 3).tolist() for r in anneaux]}}
             for nom, mat, anneaux in faces]
    C.ecrire_json(C.SORTIE / "pilote_A/partition_A.geojson", {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2154"}}, "features": feats})
    # planche : partition avant (couleurs) | v2 2026 (contours)
    X, Y = C.grille(BBOX, RES)
    a = R["ortho2022"].echantillonner(X, Y).astype(float)
    coul = {"chaussee": (90, 90, 90), "emprise_bordure": (255, 255, 255), "remplissage": (160, 120, 60)}
    for nom, mat, anneaux in faces:
        r0, c0, m = G.remplir_scanline(anneaux, x0, y1, RES, W, H)
        sub = a[r0:r0 + m.shape[0], c0:c0 + m.shape[1]]
        sub[m] = sub[m] * 0.55 + np.array(coul[nom.split()[0]]) * 0.45
    im = Image.fromarray(a.astype(np.uint8))
    dr = ImageDraw.Draw(im)
    for g in I:
        Q = np.asarray(g["geometry"]["coordinates"][0], float)[:, :2] - C.O
        if ((Q[:, 0] > x0) & (Q[:, 0] < x1) & (Q[:, 1] > y0) & (Q[:, 1] < y1)).any():
            C.tracer(dr, Q, BBOX, RES, (255, 0, 255), 3)
    for kf in K.values():
        P = np.asarray(kf["geometry"]["coordinates"], float)[:, :2] - C.O
        if ((P[:, 0] > x0) & (P[:, 0] < x1) & (P[:, 1] > y0) & (P[:, 1] < y1)).any():
            C.tracer(dr, P, BBOX, RES, (0, 255, 255), 2)
    C.cartouche(im, "A partition avant travaux : gris chaussee | blanc emprise bordure (tete mesuree) | brun galets ; magenta ilots v2 2026, cyan bordures v2 2026", 13)
    C.echelle(im, RES, 2)
    im.save(C.SORTIE / "planches" / "A_partition.jpg", quality=90)
    print(C.json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
