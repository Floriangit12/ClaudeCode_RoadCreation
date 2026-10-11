"""Diagnostic topologique de la description v2 2026 (recon/out/paquet_jardin/v2/description/base), lecture seule :
  - partition du sol : recouvrements (centre de pixel couvert par ≥ 2 surfaces) et trous (centre couvert par aucune
    surface, hors bâtiments BD TOPO) à 0,05 m, remplissage exact par balayage (règle pair-impair aux centres :
    deux surfaces qui partagent une arête ne comptent pas en recouvrement) ; fissures fines (< 0,3 m) / trous francs ;
  - bordures orphelines : bordure qu'aucune surface ne cite dans `bords`, ou dont un côté n'a pas de surface ;
  - îlots : nombre de surfaces et de bordures de ceinture, fermeture de la ceinture (plus grand écart entre
    extrémités), part de l'îlot couverte par sa surface ;
  - mêmes mesures restreintes aux zones pilotes A et B.
Sorties : ../diagnostic_v2_2026.json, ../planches/diag_v2_<zone>.jpg
Usage : python -I partition_v2.py
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image, ImageDraw

import commun_sol as C
import geom_contours as G

RES = 0.05
SITE = (-150.0, -150.0, 150.0, 150.0)
ZONES = {"A": (-4.0, -34.0, 20.0, -6.0), "B": (8.0, -8.0, 28.0, 12.0), "coeur": (-40.0, -40.0, 40.0, 40.0)}


def anneaux_local(geom):
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    return [[np.asarray(r, float)[:, :2] - C.O for r in p] for p in polys]


def main():
    base = C.V2 / "description/base"
    S = C.lire_json(base / "surfaces.geojson")["features"]
    K = C.lire_json(base / "bordures.geojson")["features"]
    I = C.lire_json(base / "ilots.geojson")["features"]
    x0, y0, x1, y1 = SITE
    W, H = int((x1 - x0) / RES), int((y1 - y0) / RES)
    cpt = np.zeros((H, W), np.uint8)
    lab = np.full((H, W), -1, np.int32)
    classes = []
    for k, f in enumerate(S):
        classes.append(f["properties"].get("classe"))
        for anneaux in anneaux_local(f["geometry"]):
            r0, c0, m = G.remplir_scanline(anneaux, x0, y1, RES, W, H)
            if not m.size:
                continue
            r1, c1 = r0 + m.shape[0], c0 + m.shape[1]
            sub = cpt[r0:r1, c0:c1]
            sub[m] = np.minimum(sub[m] + 1, 250)
            sl = lab[r0:r1, c0:c1]
            sl[m] = k
    # bâtiments (BD TOPO) : exclus des trous
    bat = np.zeros((H, W), bool)
    for f in C.lire_json(C.SITE / "vector/bdtopo_batiment.geojson")["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for p in polys:
            r = C.wgs_vers_l93(np.asarray(p[0], float)[:, :2]) - C.O
            im = Image.new("1", (W, H), 0)
            ImageDraw.Draw(im).polygon(list(zip(((r[:, 0] - x0) / RES).tolist(), ((y1 - r[:, 1]) / RES).tolist())), fill=1)
            bat |= np.asarray(im, bool)
    rec = cpt >= 2
    trou = (cpt == 0) & ~bat
    # bord du site exclu (1 m)
    b = int(1.0 / RES)
    trou[:b] = trou[-b:] = False
    trou[:, :b] = trou[:, -b:] = False
    px = RES * RES
    out = {"resolution_m": RES, "n_surfaces": len(S), "aire_recouvrements_m2": round(float(rec.sum() * px), 1),
           "aire_trous_hors_batiments_m2": round(float(trou.sum() * px), 1)}
    # composantes des trous : fissures fines (largeur < 0,3 m) vs trous francs
    t_er = G.eroder(trou, 3)                      # érosion de 0,15 m : ne reste que ce qui est plus large que 0,3 m
    out["trous_larges_plus_de_0_3m_m2"] = round(float(G.dilater(t_er, 3)[trou].sum() * px), 1)
    out["trous_fins_fissures_m2"] = round(float((trou & ~G.dilater(t_er, 3)).sum() * px), 1)
    # composantes des trous (grille 0,25 m) : aire, centre, classe GAM/v1 voisine inconnue -> centre local
    k5 = 5
    tb = trou[:H - H % k5, :W - W % k5].reshape(H // k5, k5, W // k5, k5).sum((1, 3))
    labt, nt = G.composantes(tb > 0)
    comp = []
    for j in range(1, nt + 1):
        rr, cc = np.nonzero(labt == j)
        a = float(tb[rr, cc].sum() * px)
        if a >= 1.0:
            comp.append({"aire_m2": round(a, 1), "centre_local": [round(float(x0 + (cc.mean() + 0.5) * k5 * RES), 1),
                                                                   round(float(y1 - (rr.mean() + 0.5) * k5 * RES), 1)]})
    comp.sort(key=lambda c: -c["aire_m2"])
    out["trous_composantes_sup_1m2"] = comp[:25]
    out["trous_n_composantes_sup_1m2"] = len(comp)
    r_er = G.eroder(rec, 3)
    out["recouvrements_larges_plus_de_0_3m_m2"] = round(float(G.dilater(r_er, 3)[rec].sum() * px), 1)
    out["recouvrements_fins_m2"] = round(float((rec & ~G.dilater(r_er, 3)).sum() * px), 1)
    # paires de classes en recouvrement (échantillonnage : on refait le comptage par paires sur les pixels concernés)
    # -> classe du dernier polygone peint + classe dominante dessous non disponible : on note la classe peinte
    out["recouvrements_par_classe_peinte_m2"] = {k: round(v * px, 1) for k, v in
                                                 Counter([classes[i] for i in lab[rec]]).most_common(8)}
    # ---- bordures orphelines
    citees = set()
    for f in S:
        for bd in f["properties"].get("bords") or []:
            citees.add(bd.get("bordure"))
    orph, cote_vide = [], []
    for f in K:
        p = f["properties"]
        P = np.asarray(f["geometry"]["coordinates"], float)[:, :2] - C.O
        if len(P) < 2:
            continue
        Q, s, T = C.reechantillonner(P, 0.5)
        N = np.c_[-T[:, 1], T[:, 0]]
        vide = 0
        for sg in (1, -1):
            q = Q + sg * 0.35 * N
            c = np.clip(((q[:, 0] - x0) / RES).astype(int), 0, W - 1)
            r = np.clip(((y1 - q[:, 1]) / RES).astype(int), 0, H - 1)
            vide = max(vide, float(((cpt[r, c] == 0) & ~bat[r, c]).mean()))
        if p["id"] not in citees:
            orph.append((p["id"], round(p["longueur_m"], 1)))
        if vide >= 0.5:
            cote_vide.append((p["id"], round(p["longueur_m"], 1), round(vide, 2)))
    out["bordures"] = {"n": len(K), "non_citees_par_une_surface": len(orph),
                       "longueur_non_citee_m": round(sum(l for _, l in orph), 1),
                       "exemples_non_citees": orph[:15],
                       "avec_un_cote_sans_surface_sur_50pct": len(cote_vide), "exemples_cote_vide": cote_vide[:15]}
    # ---- îlots
    kid = {f["properties"]["id"]: np.asarray(f["geometry"]["coordinates"], float)[:, :2] - C.O for f in K}
    sid = {f["properties"]["id"]: k for k, f in enumerate(S)}
    il = []
    for f in I:
        p = f["properties"]
        ce = [kid[c] for c in p.get("ceinture") or [] if c in kid]
        ext = []
        for P in ce:
            ext += [P[0], P[-1]]
        ecart = 0.0
        if ext:
            E = np.asarray(ext)
            dmin = []
            for i, e in enumerate(E):
                autres = np.delete(E, [i, i ^ 1], axis=0) if len(E) > 2 else E[[i ^ 1]]
                dmin.append(np.hypot(*(autres - e).T).min())
            ecart = float(max(dmin))
        A = []
        for anneaux in anneaux_local(f["geometry"]):
            A.append(abs(G.aire(anneaux[0])))
        il.append({"id": p["id"], "type": p.get("type"), "n_surfaces": len(p.get("surface") or []),
                   "n_bordures_ceinture": len(ce), "ecart_max_entre_extremites_de_ceinture_m": round(ecart, 2),
                   "aire_m2": round(float(sum(A)), 2), "remplissage": (p.get("remplissage") or {}).get("materiau_id")})
    out["ilots"] = il
    # ---- zones pilotes
    zz = {}
    for nom, (a0, b0, a1, b1) in ZONES.items():
        c0, c1 = int((a0 - x0) / RES), int((a1 - x0) / RES)
        r0, r1 = int((y1 - b1) / RES), int((y1 - b0) / RES)
        cl = Counter([classes[i] for i in lab[r0:r1, c0:c1][lab[r0:r1, c0:c1] >= 0]])
        zz[nom] = {"recouvrements_m2": round(float(rec[r0:r1, c0:c1].sum() * px), 2),
                   "trous_m2": round(float(trou[r0:r1, c0:c1].sum() * px), 2),
                   "n_surfaces": int(len(set(lab[r0:r1, c0:c1][lab[r0:r1, c0:c1] >= 0].tolist()))),
                   "aire_par_classe_m2": {k: round(v * px, 1) for k, v in cl.most_common()}}
        # planche
        R = C.sources_raster()
        X, Y = C.grille((a0, b0, a1, b1), RES)
        im = Image.fromarray(R["ortho2022"].echantillonner(X, Y)).convert("RGB")
        a = np.asarray(im).astype(float)
        sub_rec, sub_tr = rec[r0:r1, c0:c1], trou[r0:r1, c0:c1]
        h_, w_ = min(a.shape[0], sub_rec.shape[0]), min(a.shape[1], sub_rec.shape[1])
        a = a[:h_, :w_]
        a[sub_rec[:h_, :w_]] = a[sub_rec[:h_, :w_]] * 0.3 + np.array([255, 0, 255]) * 0.7
        a[sub_tr[:h_, :w_]] = a[sub_tr[:h_, :w_]] * 0.2 + np.array([255, 0, 0]) * 0.8
        im = Image.fromarray(a.astype(np.uint8))
        dr = ImageDraw.Draw(im)
        for f in S:
            for anneaux in anneaux_local(f["geometry"]):
                for r in anneaux:
                    if ((r[:, 0] > a0) & (r[:, 0] < a1) & (r[:, 1] > b0) & (r[:, 1] < b1)).any():
                        C.tracer(dr, np.r_[r, r[:1]], (a0, b0, a1, b1), RES, (255, 255, 255), 1)
        for f in K:
            P = np.asarray(f["geometry"]["coordinates"], float)[:, :2] - C.O
            if ((P[:, 0] > a0) & (P[:, 0] < a1) & (P[:, 1] > b0) & (P[:, 1] < b1)).any():
                C.tracer(dr, P, (a0, b0, a1, b1), RES, (255, 255, 0) if f["properties"]["id"] in citees else (0, 255, 255), 2)
        C.cartouche(im, f"v2 2026 {nom} sur ortho 2022 | blanc surfaces | jaune bordures citees | cyan bordures orphelines | magenta recouvrement | rouge trou", 12)
        C.echelle(im, RES, 5 if (a1 - a0) > 40 else 2)
        im.save(C.SORTIE / "planches" / f"diag_v2_{nom}.jpg", quality=90)
    out["zones"] = zz
    C.ecrire_json(C.SORTIE / "diagnostic_v2_2026.json", out)
    print(C.json.dumps({k: v for k, v in out.items() if k != "ilots"}, ensure_ascii=False, indent=1)[:5000])
    print(C.json.dumps(out["ilots"], ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
