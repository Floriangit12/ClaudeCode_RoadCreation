"""Pilote B : trottoir de l'angle E (Verdun NE / Vercors) avec l'abaissé de la traversée piétonne de Verdun NE,
état avant travaux (2021-2025), et la bordure posée en 2025 sur l'ancienne voie de tourne-à-droite (à écarter).

1. Chaîne G1 de la bordure de rive, assemblée à partir de morceaux ordonnés de sources différentes (GAM, PCRS 2019) :
   chaque morceau est orienté sur la fin du précédent ; un morceau marqué « coupé » est arrêté au premier
   échantillon daté « absente_avant », « apparue_2022_2024 » ou « relief_seul » par dater_gam.py (partie
   redessinée en 2025) ; jonctions mesurées
   (écart, angle), assemblage, rééchantillonnage 0,25 m, lissage σ 0,25 m -> contrôle G1.
2. Vue le long de la chaîne tous les 0,25 m : MNT 2021 JPEG décodé, heightmap v1 (= modèle 2026 ; valable hors
   zones modifiées), points LiDAR 2021 (bordures_hauteurs, tronçons de 1 m des lignes GAM et PCRS) ; abaissés =
   vue < 0,04 m sur ≥ 0,8 m (MNT JPEG moyenné sur 1,25 m), comparés aux chartières GAM et aux abaissés v2 2026.
3. Matériaux : bandes de 0,3 m devant et 0,5–1,5 m derrière sur l'ortho 2022.
Sorties : ../pilote_B/{bordure_rive_B.geojson, mesures_B.json}, planches ../planches/B_*.jpg, B_profil_vue.png
Usage : python -I trottoir_abaisse.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image, ImageDraw

import commun_sol as C
from dtm_jpg import MNT2021Jpg

BBOX = (8.0, -8.0, 28.0, 12.0)
MARGE = 4.0
# morceaux ordonnés de la bordure de rive avant travaux : (source, indice, coupe_par_datation)
MORCEAUX = [("gam", 369, False), ("gam", 385, True), ("pcrs2019", 28, False)]


def dans(P, bb=BBOX, m=0.0):
    return (P[:, 0] > bb[0] - m) & (P[:, 0] < bb[2] + m) & (P[:, 1] > bb[1] - m) & (P[:, 1] < bb[3] + m)


def abscisse_sur(Q, P):
    """Abscisse curviligne de la projection de chaque point Q sur la polyligne P, et distance signée (gauche +)."""
    A, B = P[:-1], P[1:]
    AB = B - A
    L2 = np.maximum((AB ** 2).sum(1), 1e-12)
    S = C.abscisses(P)
    t = np.clip(((Q[:, None, :] - A[None]) * AB[None]).sum(-1) / L2[None], 0, 1)
    proj = A[None] + t[..., None] * AB[None]
    d = np.sqrt(((Q[:, None, :] - proj) ** 2).sum(-1))
    i = d.argmin(1)
    s = S[i] + t[np.arange(len(Q)), i] * np.sqrt(L2[i])
    ab = AB[i]
    cr = ab[:, 0] * (Q[:, 1] - A[i, 1]) - ab[:, 1] * (Q[:, 0] - A[i, 0])
    return s, np.sign(cr) * d[np.arange(len(Q)), i]


def construire_chaine(D, lignes):
    pieces, jonctions, coupes = [], [], []
    fin = None
    for src, idx, couper in MORCEAUX:
        P = lignes[src][idx][1]
        Q, _, _ = C.reechantillonner(P, 0.1)
        if fin is not None and np.hypot(*(Q[-1] - fin)) < np.hypot(*(Q[0] - fin)):
            Q = Q[::-1]
        garde = dans(Q, m=MARGE)
        if couper:
            mauvais = np.zeros(len(Q), bool)
            for f in D:
                pp = f["properties"]
                if pp["source"] == src and pp["indice"] == idx and pp["classe"] in ("absente_avant", "apparue_2022_2024", "relief_seul"):
                    Pd = np.asarray(f["geometry"]["coordinates"], float)[:, :2] - C.O
                    mauvais |= C.dist_point_segments(Q, Pd) < 0.30
            k = np.flatnonzero(mauvais & garde)
            if len(k):
                coupes.append({"morceau": f"{src}:{idx}", "coupe_a_s_m": round(float(k[0]) * 0.1, 2),
                               "longueur_ecartee_dans_la_zone_m": round(float((garde[k[0]:]).sum()) * 0.1, 2)})
                garde[k[0]:] = False
        Q = Q[garde]
        tronque = 0.0
        if pieces and len(Q):
            # raccord : le morceau précédent est tronqué au point le plus proche du début du suivant (≤ 3 m de sa fin)
            prev = pieces[-1]
            n3 = min(len(prev), 30)
            dd = np.hypot(*(prev[-n3:] - Q[0]).T)
            j = int(dd.argmin())
            if dd[j] < 1.5:
                tronque = round((n3 - 1 - j) * 0.1, 2)
                pieces[-1] = prev[:len(prev) - n3 + j + 1]
            fin = pieces[-1][-1]
        if fin is not None and len(Q):
            d = float(np.hypot(*(Q[0] - fin)))
            prev = pieces[-1]
            t0 = prev[-1] - prev[max(0, len(prev) - 6)]
            t1 = Q[min(5, len(Q) - 1)] - Q[0]
            ang = float(np.degrees(np.arccos(np.clip(np.dot(t0, t1) / (np.linalg.norm(t0) * np.linalg.norm(t1) + 1e-12), -1, 1))))
            jonctions.append({"vers": f"{src}:{idx}", "ecart_m": round(d, 3), "angle_deg": round(ang, 1),
                              "troncature_du_precedent_m": tronque})
        pieces.append(Q)
        fin = Q[-1]
    chaine = np.concatenate(pieces)
    chaine = chaine[np.r_[True, np.hypot(*np.diff(chaine, axis=0).T) > 0.02]]
    brute = chaine.copy()
    chaine, _, _ = C.reechantillonner(chaine, 0.25)
    w = np.exp(-0.5 * (np.arange(-3, 4) / 1.0) ** 2)
    w /= w.sum()
    sm = chaine.copy()
    for i in range(3, len(chaine) - 3):
        sm[i] = (chaine[i - 3:i + 4] * w[:, None]).sum(0)
    chaine = sm
    ec_lissage = C.dist_point_segments(chaine, brute)
    dev = np.degrees(np.abs(np.diff(np.unwrap(np.arctan2(*np.diff(chaine, axis=0).T[::-1])))))
    g1 = {"morceaux": [f"{s_}:{i_}" + (" (coupé par datation)" if c_ else "") for s_, i_, c_ in MORCEAUX],
          "coupes_par_datation": coupes, "jonctions": jonctions,
          "longueur_chaine_m": round(float(C.abscisses(chaine)[-1]), 2),
          "ecart_lissage_max_m": round(float(ec_lissage.max()), 3),
          "virage_max_deg_par_0_25m": round(float(dev.max()), 2), "virages_sup_10deg": int((dev > 10).sum())}
    return chaine, pieces, g1


def main():
    R = C.sources_raster()
    jpg, hm, zm = MNT2021Jpg(), C.Heightmap(), C.ZonesModifiees()
    out = C.SORTIE / "pilote_B"
    out.mkdir(exist_ok=True)
    D = C.lire_json(C.SORTIE / "datation/gam_bordures_datation.geojson")["features"]
    lignes = {"gam": {i: (p, P) for i, p, P, _ in C.charger_lignes(C.SITE / "vector/gam_topo_sol_bordure_lin.geojson", wgs=True)},
              "pcrs2019": {i: (p, P) for i, p, P, _ in C.charger_lignes(C.SITE / "vector/gam_limite_voirie_pcrs.geojson", wgs=True)}}
    chaine, pieces, g1 = construire_chaine(D, lignes)
    # chartières GAM (blocs CHARTIERE_*) projetées sur la chaîne
    chart = []
    for f in C.lire_json(C.SITE / "vector/gam_topo_sol_bordure_pct.geojson")["features"]:
        b_ = f["properties"].get("bloc") or ""
        if b_.startswith("CHARTIERE"):
            pq = C.wgs_vers_l93(np.atleast_2d(np.asarray(f["geometry"]["coordinates"], float))[:, :2]) - C.O
            if dans(pq).any():
                sc_, dc_ = abscisse_sur(pq, chaine)
                chart.append({"bloc": b_, "s_m": round(float(sc_[0]), 2), "distance_m": round(float(abs(dc_[0])), 3)})
    g1["chartieres_gam"] = chart
    # ---- vue le long de la chaîne
    Q, s, T = C.reechantillonner(chaine, 0.25)
    N = np.c_[-T[:, 1], T[:, 0]]
    # côté haut (trottoir, îlot) décidé localement : z à ± 0,5 m, moyenne glissante sur 4 m
    dzc = jpg(*(Q + 0.5 * N + C.O).T) - jpg(*(Q - 0.5 * N + C.O).T)
    dzc = np.convolve(np.pad(dzc, 8, mode="edge"), np.ones(17) / 17, mode="valid")
    N = N * np.where(dzc >= 0, 1.0, -1.0)[:, None]
    oh = np.arange(0.25, 0.601, 0.05)
    ob = np.arange(0.10, 0.601, 0.05)
    H = Q[:, None, :] + oh[None, :, None] * N[:, None, :]
    B = Q[:, None, :] - ob[None, :, None] * N[:, None, :]

    def vue(src):
        return (np.median(src(H[..., 0] + C.O[0], H[..., 1] + C.O[1]), 1) - np.median(src(B[..., 0] + C.O[0], B[..., 1] + C.O[1]), 1))
    vj, vh = vue(jpg), vue(hm)
    zh = zm(H[..., 0], H[..., 1]).max(1)
    zb = zm(B[..., 0], B[..., 1]).max(1)
    hm_ok = (zh == 0) & (zb <= 1)
    vj_l = np.convolve(np.pad(vj, 2, mode="edge"), np.ones(5) / 5, mode="valid")
    # points LiDAR 2021 (bordures_hauteurs) des lignes GAM / PCRS le long de la chaîne
    BH = C.lire_json(C.PAQUET / "relief/bordures_hauteurs.geojson")["features"]
    vpts = np.full(len(Q), np.nan)
    st_pts = np.full(len(Q), "", dtype=object)
    for fb in BH:
        Pb = np.asarray(fb["geometry"]["coordinates"], float)[:, :2] - C.O
        if not dans(Pb, m=1).any():
            continue
        pm = Pb.mean(0)
        d = np.hypot(*(Q - pm).T)
        i = int(d.argmin())
        if d[i] < 0.4 and fb["properties"].get("h_lidar_2021_m") is not None and fb["properties"].get("statut") != "estimee":
            sel = np.abs(s - s[i]) <= 0.5
            vpts[sel] = fb["properties"]["h_lidar_2021_m"]
            st_pts[sel] = fb["properties"].get("statut")
    # abaissés
    bas = vj_l < 0.04
    ab = []
    i = 0
    while i < len(bas):
        if bas[i]:
            j = i
            while j + 1 < len(bas) and bas[j + 1]:
                j += 1
            if (j - i + 1) * 0.25 >= 0.8:
                ab.append({"s0": round(float(s[i]), 2), "s1": round(float(s[j]), 2), "longueur_m": round((j - i + 1) * 0.25, 2),
                           "vue_jpg_p50_m": round(float(np.median(vj[i:j + 1])), 3),
                           "vue_points_p50_m": (round(float(np.nanmedian(vpts[i:j + 1])), 3) if np.isfinite(vpts[i:j + 1]).any() else None),
                           "centre_local": np.round(Q[(i + j) // 2], 2).tolist()})
            i = j + 1
        else:
            i += 1
    # ---- v2 2026 voisines
    V2 = []
    for f in C.lire_json(C.V2 / "description/base/bordures.geojson")["features"]:
        P = np.asarray(f["geometry"]["coordinates"], float)[:, :2] - C.O
        if not dans(P, m=0).any():
            continue
        d = C.dist_point_segments(P, chaine)
        p = f["properties"]
        abp = []
        Sv = C.abscisses(P)
        for a_ in p["abaisses"]:
            xa = np.c_[np.interp([a_["s0"], a_["s1"]], Sv, P[:, 0]), np.interp([a_["s0"], a_["s1"]], Sv, P[:, 1])]
            sa, da = abscisse_sur(xa, chaine)
            abp.append({"type": a_["type"], "vue_m": a_["vue_m"], "s_chaine_m": [round(float(v), 2) for v in sa],
                        "distance_a_la_chaine_m": [round(float(abs(v)), 2) for v in da]})
        V2.append({"id": p["id"], "longueur_m": round(p["longueur_m"], 2), "part_a_moins_de_0_3m_de_la_chaine": round(float((d < 0.3).mean()), 2),
                   "src_geometrie": str(p.get("prov", ""))[:60], "abaisses": abp,
                   "intervalles": [(round(v["s0"], 2), round(v["s1"], 2), v["profil"], v["vue_m"], v.get("role")) for v in p["intervalles"]],
                   "statut_hauteur": p["source"].get("statut_hauteur"), "zone_travaux_2025": p["zone_travaux_2025"]})
    mat = materiaux_bandes(R["ortho2022"], Q, N)
    res = {"zone_bbox_local": BBOX, "chaine_G1": g1,
           "vue_m": {"jpg_p50": round(float(np.median(vj)), 3),
                     "points_lidar2021_p50": round(float(np.nanmedian(vpts)), 3) if np.isfinite(vpts).any() else None,
                     "heightmap_v1_2026_p50_hors_zones": round(float(np.median(vh[hm_ok])), 3) if hm_ok.any() else None,
                     "part_heightmap_valable": round(float(hm_ok.mean()), 3),
                     "ecart_jpg_moins_points_p50": round(float(np.nanmedian(vj - vpts)), 3) if np.isfinite(vpts).any() else None,
                     "ecart_jpg_moins_points_abs_p90": round(float(np.nanpercentile(np.abs(vj - vpts), 90)), 3) if np.isfinite(vpts).any() else None,
                     "ecart_heightmap_moins_points_hors_zones_abs_p50": (round(float(np.nanmedian(np.abs(vh - vpts)[hm_ok])), 3) if (hm_ok & np.isfinite(vpts)).any() else None)},
           "abaisses_2021": ab, "statuts_points": {k: int((st_pts == k).sum()) for k in set(st_pts) if k},
           "bordures_v2_2026": V2, "materiaux_ortho2022": mat}
    C.ecrire_json(out / "mesures_B.json", res)
    C.ecrire_json(out / "bordure_rive_B.geojson", {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2154"}},
                  "features": [{"type": "Feature", "properties": {"id": "KB-1", "ligne_ref": "arete_avant_haute",
                                                                     "src": "+".join(g1["morceaux"]), "abaisses_2021": ab},
                                "geometry": {"type": "LineString", "coordinates": np.round(chaine + C.O, 3).tolist()}}]})
    planches(R, chaine, Q, N, s, vj, vh, vpts, hm_ok, ab, lignes, chart)
    print(C.json.dumps(res, ensure_ascii=False, indent=1)[:9000])


def materiaux_bandes(src, Q, N):
    out = []
    for nom, o in (("devant_0_0_3m", np.arange(-0.30, -0.0, 0.05)), ("derriere_0_5_1_5m", np.arange(0.5, 1.51, 0.05))):
        G_ = Q[:, None, :] + o[None, :, None] * N[:, None, :]
        rgb = src.echantillonner(G_[..., 0] + C.O[0], G_[..., 1] + C.O[1]).astype(float)
        L = C.luminance(rgb)
        out.append({"bande": nom, "lum_med": round(float(np.median(L)), 1), "lum_ecart_type": round(float(L.std()), 1),
                    "rgb_med": [int(v) for v in np.median(rgb.reshape(-1, 3), 0)],
                    "exg_med": round(float(np.median(2 * rgb[..., 1] - rgb[..., 0] - rgb[..., 2])), 1)})
    return out


def planches(R, chaine, Q, N, s, vj, vh, vpts, hm_ok, ab, lignes, chart):
    res = 0.025
    X, Y = C.grille(BBOX, res)
    for fond in ("ortho2022", "ortho2024", "pente2021", "plan2025"):
        im = Image.fromarray(R[fond].echantillonner(X, Y))
        dr = ImageDraw.Draw(im)
        for src_, coul in (("pcrs2019", (0, 230, 255)), ("gam", (255, 0, 0))):
            for _, (pp, P) in lignes[src_].items():
                if dans(P, m=1).any() and (src_ == "gam" or "Bordure" in (pp.get("calque") or "")):
                    C.tracer(dr, P, BBOX, res, coul, 1)
        for v in C.lire_json(C.V2 / "description/base/bordures.geojson")["features"]:
            P = np.asarray(v["geometry"]["coordinates"], float)[:, :2] - C.O
            if dans(P).any():
                C.tracer(dr, P + 0.0, BBOX, res, (255, 0, 255), 1)
        C.tracer(dr, chaine, BBOX, res, (255, 255, 0), 3)
        for a in ab:
            sel = (s >= a["s0"]) & (s <= a["s1"])
            C.tracer(dr, Q[sel] + 0.3 * N[sel], BBOX, res, (0, 255, 0), 6)
        for k in range(0, len(Q), 8):
            (u, v), = C.vers_px(Q[k][None], BBOX, res)
            dr.text((u + 4, v + 4), f"{s[k]:.0f}", fill=(255, 255, 0), font=C.police(12))
        C.cartouche(im, f"B {fond} | jaune chaine G1 avant travaux (abscisse en m) | rouge GAM | cyan PCRS 2019 | vert abaisse 2021 (vue<4 cm) | magenta bordures v2 2026", 12)
        C.echelle(im, res, 2)
        im.save(C.SORTIE / "planches" / f"B_{fond}.jpg", quality=90)
    # profil de vue
    W, Hh = 1000, 440
    im = Image.new("RGB", (W, Hh), (255, 255, 255))
    dr = ImageDraw.Draw(im)
    f = C.police(13)
    smax = s.max()

    def px(si, v):
        return 60 + (si / smax) * (W - 80), Hh - 50 - (v + 0.05) / 0.35 * (Hh - 90)
    for v in np.arange(-0.05, 0.301, 0.05):
        dr.line([px(0, v), px(smax, v)], fill=(225, 225, 225))
        dr.text((5, px(0, v)[1] - 7), f"{v*100:.0f} cm", fill=(0, 0, 0), font=f)
    for a in ab:
        dr.rectangle([px(a["s0"], 0.30), px(a["s1"], -0.05)], fill=(215, 255, 215))
    for c in chart:
        x_, _ = px(c["s_m"], 0)
        dr.line([(x_, px(0, 0.30)[1]), (x_, px(0, -0.05)[1])], fill=(255, 0, 255), width=2)
    for vals, col in ((vh, (240, 200, 160)), (np.where(hm_ok, vh, np.nan), (230, 120, 0)), (vj, (0, 90, 220)), (vpts, (200, 0, 0))):
        pts = [(px(si, v), ok) for si, v, ok in zip(s, vals, np.isfinite(vals))]
        for (a_, oa), (b_, ob_) in zip(pts, pts[1:]):
            if oa and ob_:
                dr.line([a_, b_], fill=col, width=2)
    y = 30
    for col, nom in (((0, 90, 220), "MNT 2021 JPEG decode"), ((200, 0, 0), "points LiDAR 2021 (bordures_hauteurs, 1 m)"),
                     ((230, 120, 0), "heightmap v1 (modele 2026) hors zones modifiees"), ((240, 200, 160), "heightmap v1 (modele 2026) partout"),
                     ((255, 0, 255), "chartiere GAM")):
        dr.line([(W - 360, y + 7), (W - 330, y + 7)], fill=col, width=3)
        dr.text((W - 325, y), nom, fill=(0, 0, 0), font=f)
        y += 18
    dr.text((60, Hh - 30), f"abscisse le long de la chaine G1 (0 -> {smax:.1f} m) ; fond vert : abaisse 2021 detecte (vue < 4 cm sur >= 0,8 m)", fill=(0, 0, 0), font=f)
    C.cartouche(im, "B profil de vue de la bordure de rive avant travaux (m)", 14)
    im.save(C.SORTIE / "planches" / "B_profil_vue.png")


if __name__ == "__main__":
    main()
