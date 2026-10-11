"""Pilote A : îlots du cœur AVANT travaux (refuge triangulaire de la traversée de Vercors et îlot allongé au sud),
absents du levé GAM (qui porte la « goutte » de 2025) et du PCRS 2019.

Chaîne « le LiDAR détecte, l'ortho précise » :
  1. crêtes de pente LiDAR 2021 (raster 15 cm) -> composantes en anneau -> masque d'îlot rempli ;
  2. contour initial = bord du masque rempli érodé de 0,30 m (≈ milieu de la bande de crête), lissé ;
  3. affinage sur l'ortho PCRS 2022 5 cm : le long de la normale, filtre adapté « tête de bordure claire sur
     0,15 m / extérieur plus sombre sur 0,15 m » (enrobé, ombre portée) ; médiane glissante sur 1 m, rejet des
     écarts > 0,12 m, lissage σ 0,10 m -> anneau fermé (G0) ; contrôle G1 ;
  4. répétabilité : même affinage sur la BD ORTHO 2024 (20 cm, recalée), écart entre les deux anneaux ;
  5. hauteurs : profils perpendiculaires tous les 0,5 m (dessus 0,25-0,6 m dedans, fil d'eau 0,1-0,6 m dehors) sur
     le MNT 2021 JPEG décodé (la heightmap v1 est arasée ici) ; même profil sur la heightmap v1 (= modèle 2026) ;
  6. matériaux : statistiques couleur / texture de l'intérieur (érodé de 0,35 m) et de la bande de bordure.
Sorties : ../pilote_<nom>/ilots_avant_travaux.geojson (L93), ../pilote_<nom>/mesures_<nom>.json,
planches ../planches/<nom>_*.jpg
Usage : python -I ilot_coeur.py                       (zone A, îlots disparus en 2025)
        python -I ilot_coeur.py x0 y0 x1 y1 nom       (autre zone ; si le levé GAM y porte des bordures d'avant
                                                       travaux, l'écart contour extrait / levé GAM est mesuré)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image, ImageDraw

import commun_sol as C
import geom_contours as G
from dtm_jpg import MNT2021Jpg

BBOX = (-4.0, -34.0, 20.0, -6.0)
NOM = "A"
if len(sys.argv) >= 6:
    BBOX = tuple(float(v) for v in sys.argv[1:5])
    NOM = sys.argv[5]
RES_P = 0.15


def masque_pente(R, bbox):
    X, Y = C.grille(bbox, RES_P)
    pn = C.pente_norm(R["pente2021"].echantillonner(X, Y))
    return pn >= 0.75, X, Y


def vers_local_rc(rc, bbox, res):
    x0, y0, x1, y1 = bbox
    return np.c_[x0 + (rc[:, 1] + 0.5) * res, y1 - (rc[:, 0] + 0.5) * res]


def profil_lum(src, P, N, offs):
    Gq = P[:, None, :] + offs[None, :, None] * N[:, None, :]
    rgb = src.echantillonner(Gq[..., 0] + C.O[0], Gq[..., 1] + C.O[1])
    return C.luminance(rgb)


def affiner(src, P0, pas_px, fen=0.30, pas=0.025, decal=-0.20, bande=0.15, demi_med=0.5):
    """P0 anneau CCW (local), ≈ milieu de bande de crête LiDAR. Filtre adapté « tête de bordure claire / extérieur
    plus sombre » : score(d) = moyenne(L sur [d − bande, d]) − moyenne(L sur [d, d + bande]) le long de la normale
    extérieure, d dans decal ± fen ; meilleur score ≥ 8 niveaux, médiane glissante sur 2·demi_med, rejet > 0,12 m."""
    T = np.roll(P0, -1, 0) - np.roll(P0, 1, 0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    N = np.c_[T[:, 1], -T[:, 0]]                       # extérieur pour un anneau CCW
    offs = np.arange(decal - fen - bande, decal + fen + bande + 1e-9, pas)
    L = profil_lum(src, P0, N, offs)
    kb = max(1, int(round(bande / pas)))
    cs = np.c_[np.zeros(len(L)), np.cumsum(L, 1)]
    cand = np.arange(kb, len(offs) - kb)
    dedans = (cs[:, cand] - cs[:, cand - kb]) / kb
    dehors = (cs[:, cand + kb] - cs[:, cand]) / kb
    score = dedans - dehors
    i = np.argmax(score, 1)
    d = offs[cand[i]] - pas / 2
    force = score[np.arange(len(score)), i]
    dm = G.mediane_glissante_fermee(d, max(1, int(round(demi_med / 0.10))))
    ok = (np.abs(d - dm) <= 0.12) & (force >= 8.0)
    dr = np.where(ok, d, dm)
    dl = G.lisser_ferme(dr, 1.0)
    P = P0 + dl[:, None] * N
    return P, d, ok, force, N


def distance_anneaux(A, B):
    d = C.dist_point_segments(A, np.r_[B, B[:1]])
    return d


BH = C.lire_json(C.PAQUET / "relief/bordures_hauteurs.geojson")["features"]


def main():
    R = C.sources_raster()
    jpg, hm = MNT2021Jpg(), C.Heightmap()
    out_dir = C.SORTIE / f"pilote_{NOM}"
    out_dir.mkdir(exist_ok=True)
    m, X, Y = masque_pente(R, BBOX)
    lab, n = G.composantes(m)
    ilots = []
    H, W = m.shape
    for k in range(1, n + 1):
        mk = lab == k
        rr, cc = np.nonzero(mk)
        if rr.min() == 0 or cc.min() == 0 or rr.max() == H - 1 or cc.max() == W - 1:
            continue                                     # touche le bord : bordure de rive, pas un îlot
        f = G.remplir(mk)
        trou = f & ~mk
        if f.sum() * RES_P ** 2 < 3.0 or trou.sum() * RES_P ** 2 < 0.10:
            continue                                     # pas d'anneau : poteau, véhicule, bruit
        ilots.append(f)
    res = {"zone_bbox_local": BBOX, "n_composantes_pente": int(n), "ilots": []}
    feats = []
    anneaux = []
    for num, f in enumerate(ilots, 1):
        fe = G.eroder(f, 2)                              # 0,30 m
        rc = G.contour_moore(fe)
        P0 = vers_local_rc(rc, BBOX, RES_P)
        if G.aire(P0) < 0:
            P0 = P0[::-1]
        P0, per0 = G.reechantillonner_ferme(P0, 0.10)
        P0 = G.lisser_ferme(P0, 2.0)
        P22, d22, ok22, force22, N = affiner(R["ortho2022"], P0, 0.05)
        P22, per = G.reechantillonner_ferme(P22, 0.10)
        P22 = G.lisser_ferme(P22, 1.0)
        P24, d24, ok24, _, _ = affiner(R["ortho2024"], P0, 0.20, fen=0.35, pas=0.05, bande=0.20)
        g1 = G.controles_g1(P22, 0.10)
        dp = G.douglas_peucker(np.r_[P22, P22[:1]], 0.01)
        e2224 = distance_anneaux(P24, P22)
        # écart entre le contour affiné et le milieu de bande de crête (biais ortho / LiDAR)
        ecart_crete = distance_anneaux(P0, P22)
        # résidu de l'affinage autour de la courbe lissée (bruit planimétrique)
        resid = np.abs(d22 - G.lisser_ferme(np.where(ok22, d22, G.mediane_glissante_fermee(d22, 3)), 1.0))[ok22]
        # ---- hauteurs (profils perpendiculaires tous les 0,5 m)
        Pq, perq = G.reechantillonner_ferme(P22, 0.5)
        T = np.roll(Pq, -1, 0) - np.roll(Pq, 1, 0)
        T /= np.linalg.norm(T, axis=1)[:, None]
        Nq = np.c_[T[:, 1], -T[:, 0]]
        o_in = np.arange(0.25, 0.601, 0.05)
        o_out = np.arange(0.10, 0.601, 0.05)
        Pin = Pq[:, None, :] - o_in[None, :, None] * Nq[:, None, :]
        Pout = Pq[:, None, :] + o_out[None, :, None] * Nq[:, None, :]
        hj = (np.median(jpg(Pin[..., 0] + C.O[0], Pin[..., 1] + C.O[1]), 1)
              - np.median(jpg(Pout[..., 0] + C.O[0], Pout[..., 1] + C.O[1]), 1))
        hh = (np.median(hm(Pin[..., 0] + C.O[0], Pin[..., 1] + C.O[1]), 1)
              - np.median(hm(Pout[..., 0] + C.O[0], Pout[..., 1] + C.O[1]), 1))
        zf = np.median(jpg(Pout[..., 0] + C.O[0], Pout[..., 1] + C.O[1]), 1)
        # ---- écart au levé GAM (si des bordures GAM d'avant travaux bordent l'îlot)
        gam = [Pg for _, _, Pg, _ in C.charger_lignes(C.SITE / "vector/gam_topo_sol_bordure_lin.geojson", wgs=True)
               if (np.hypot(*(Pg - P22.mean(0)).T) < 30).any()]
        dg = np.full(len(P22), np.inf)
        for Pg in gam:
            if len(Pg) >= 2:
                dg = np.minimum(dg, C.dist_point_segments(P22, Pg))
        proche = dg < 0.5
        # ---- hauteurs v1 « points » le long des bordures GAM voisines (bordures_hauteurs, LiDAR 2021 points)
        hpts = []
        for fb in BH:
            Pb = np.asarray(fb["geometry"]["coordinates"], float)[:, :2] - C.O
            if fb["properties"].get("statut") in ("mesuree", "abaissee_mesuree") and                     C.dist_point_segments(Pb.mean(0)[None], np.r_[P22, P22[:1]])[0] < 0.4:
                hpts.append(fb["properties"]["h_lidar_2021_m"])
        # ---- matériaux
        rgb_in, rgb_bande, rgb_route = materiaux(R["ortho2022"], P22)
        A = abs(G.aire(P22))
        cx, cy = P22.mean(0)
        info = {
            "id": f"I{NOM}-{num}", "centre_local": [round(float(cx), 2), round(float(cy), 2)],
            "aire_m2": round(A, 2), "perimetre_m": round(float(per), 2),
            "controle_G1": g1, "sommets_douglas_peucker_1cm": int(len(dp) - 1),
            "affinage_ortho2022": {"part_retenue": round(float(ok22.mean()), 3),
                                   "residu_p50_m": round(float(np.median(resid)), 3) if len(resid) else None,
                                   "residu_p90_m": round(float(np.percentile(resid, 90)), 3) if len(resid) else None,
                                   "force_chute_p50": round(float(np.median(force22)), 1)},
            "ecart_contour_2022_vs_2024_m": {"p50": round(float(np.median(e2224)), 3), "p90": round(float(np.percentile(e2224, 90)), 3)},
            "ecart_contour_ortho_vs_crete_lidar_m": {"p50": round(float(np.median(ecart_crete)), 3), "p90": round(float(np.percentile(ecart_crete, 90)), 3)},
            "vue_lidar2021_jpg_m": {"p10": round(float(np.percentile(hj, 10)), 3), "p50": round(float(np.median(hj)), 3),
                                    "p90": round(float(np.percentile(hj, 90)), 3), "n_profils": int(len(hj))},
            "vue_heightmap_v1_2026_m": {"p50": round(float(np.median(hh)), 3), "p90": round(float(np.percentile(hh, 90)), 3)},
            "ecart_au_leve_gam_m": ({"part_du_contour_a_moins_de_0_5m": round(float(proche.mean()), 3),
                                     "p50": round(float(np.median(dg[proche])), 3),
                                     "p90": round(float(np.percentile(dg[proche], 90)), 3)} if proche.any() else None),
            "vue_points_lidar2021_bordures_hauteurs_m": ({"n_troncons_1m": len(hpts), "p50": round(float(np.median(hpts)), 3),
                                                          "p10": round(float(np.percentile(hpts, 10)), 3),
                                                          "p90": round(float(np.percentile(hpts, 90)), 3)} if hpts else None),
            "z_fil_eau_lidar2021_jpg_ngf": {"min": round(float(zf.min()), 3), "max": round(float(zf.max()), 3)},
            "materiaux_ortho2022": {"interieur": rgb_in, "bande_bordure_0_18m": rgb_bande, "enrobe_voisin_0_5_1_5m": rgb_route},
        }
        res["ilots"].append(info)
        anneaux.append((info["id"], P22, P24, P0, Pq, hj))
        feats.append({"type": "Feature", "properties": {k: v for k, v in info.items() if k in ("id", "aire_m2", "perimetre_m")}
                      | {"ligne_ref": "arete_avant_haute", "src": "ortho2022+lidar2021", "date_etat": "2021-08..2025-06"},
                      "geometry": {"type": "Polygon", "coordinates": [np.round(np.r_[P22, P22[:1]] + C.O, 3).tolist()]}})
    C.ecrire_json(out_dir / "ilots_avant_travaux.geojson", {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2154"}}, "features": feats})
    C.ecrire_json(out_dir / f"mesures_{NOM}.json", res)
    planches(R, anneaux)
    print(C.json.dumps(res, ensure_ascii=False, indent=1)[:6000])


def stats_rgb(a):
    a = a.reshape(-1, 3).astype(float)
    L = C.luminance(a)
    exg = 2 * a[:, 1] - a[:, 0] - a[:, 2]
    return {"n_px": int(len(a)), "rgb_med": [int(v) for v in np.median(a, 0)], "lum_med": round(float(np.median(L)), 1),
            "lum_ecart_type": round(float(L.std()), 1), "exg_med": round(float(np.median(exg)), 1),
            "r_moins_b_med": round(float(np.median(a[:, 0] - a[:, 2])), 1)}


def materiaux(src, P):
    x0, y0 = P.min(0) - 2
    x1, y1 = P.max(0) + 2
    bb = (x0, y0, x1, y1)
    X, Y = C.grille(bb, 0.05)
    rgb = src.echantillonner(X, Y)
    xl, yl = X - C.O[0], Y - C.O[1]
    Q = np.c_[xl.ravel(), yl.ravel()]
    d = C.dist_point_segments(Q, np.r_[P, P[:1]]).reshape(X.shape)
    im = Image.new("1", (X.shape[1], X.shape[0]), 0)
    ImageDraw.Draw(im).polygon(C.vers_px(P, bb, 0.05), fill=1)
    dedans = np.asarray(im, bool)
    # texture : écart-type local 3x3 de la luminance (grain du gravier / joints de pavés)
    return (stats_rgb(rgb[dedans & (d > 0.35)]), stats_rgb(rgb[dedans & (d < 0.18)]),
            stats_rgb(rgb[~dedans & (d > 0.5) & (d < 1.5)]))


def planches(R, anneaux):
    res = 0.02
    for fond in ("ortho2022", "ortho2024", "pente2021", "plan2025"):
        X, Y = C.grille(BBOX, res)
        im = Image.fromarray(R[fond].echantillonner(X, Y))
        dr = ImageDraw.Draw(im)
        for iid, P22, P24, P0, Pq, hj in anneaux:
            C.tracer(dr, np.r_[P0, P0[:1]], BBOX, res, (255, 0, 255), 2)
            if fond != "pente2021":
                C.tracer(dr, np.r_[P24, P24[:1]], BBOX, res, (0, 120, 255), 2)
            C.tracer(dr, np.r_[P22, P22[:1]], BBOX, res, (255, 255, 0), 2)
            (u, v), = C.vers_px(P22.mean(0)[None], BBOX, res)
            dr.text((u - 15, v), iid, fill=(255, 255, 0), font=C.police(16))
        for _, _, P, _ in C.charger_lignes(C.SITE / "vector/gam_topo_sol_bordure_lin.geojson", wgs=True):
            if ((P[:, 0] > BBOX[0] - 2) & (P[:, 0] < BBOX[2] + 2) & (P[:, 1] > BBOX[1] - 2) & (P[:, 1] < BBOX[3] + 2)).any():
                C.tracer(dr, P, BBOX, res, (255, 0, 0), 1)
        C.cartouche(im, f"{NOM} {fond} | jaune contour avant travaux (ortho 2022 + LiDAR 2021) | bleu idem ortho 2024 | magenta milieu de crete LiDAR | rouge GAM (2025)", 13)
        C.echelle(im, res, 2)
        im.save(C.SORTIE / "planches" / f"{NOM}_{fond}.jpg", quality=90)
    # hauteurs mesurées (pastilles colorées sur l'ortho 2022)
    X, Y = C.grille(BBOX, res)
    im = Image.fromarray(R["ortho2022"].echantillonner(X, Y))
    dr = ImageDraw.Draw(im)
    for iid, P22, P24, P0, Pq, hj in anneaux:
        for p, h in zip(Pq, hj):
            (u, v), = C.vers_px(p[None], BBOX, res)
            t = np.clip(h / 0.20, 0, 1)
            col = (int(255 * t), int(255 * (1 - abs(t - 0.5) * 2)), int(255 * (1 - t)))
            dr.ellipse([u - 6, v - 6, u + 6, v + 6], fill=col, outline=(0, 0, 0))
    C.cartouche(im, f"{NOM} vue mesuree LiDAR 2021 (MNT JPEG decode, +/- 6 cm p90) : bleu 0 cm -> vert 10 cm -> rouge >= 20 cm", 13)
    C.echelle(im, res, 2)
    im.save(C.SORTIE / "planches" / f"{NOM}_hauteurs.jpg", quality=90)


if __name__ == "__main__":
    main()
