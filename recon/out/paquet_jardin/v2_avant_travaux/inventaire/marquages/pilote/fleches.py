"""Flèches directionnelles : ajustement des gabarits IISR (assets/specs/marquages_geometrie.json, annexe B) sur la
carte de probabilité de peinture de l'ortho 5 cm.

Pour chaque composante candidate (classe « fleche_candidate », ou « symbole_ou_autre » de 0,4 à 2,6 m2 et de 2,5 à
6,5 m de long), et pour chaque gabarit G parmi TD, TAD, TAG, TD_TAD, TD_TAG et TRIDENT (union TD_TAD + TD_TAG,
hors IISR mais présent sur le site) :
  - initialisation : barycentre du gabarit sur le barycentre de la composante, cap = axe principal (deux sens) ;
  - critère : IoU « douce » sum(min(T, p)) / sum(max(T, p)) entre la couverture du gabarit rastérisé
    (sur-échantillonnage x4) et p, p limité à la composante et au gabarit dilaté de 0,30 m (un tiret collé
    à la flèche ne pénalise que sa partie proche) ;
  - ajustement 1 (pose normée) : (x, y, cap) à échelle 1 -> pose du static mesh IISR ;
  - ajustement 2 (mesure) : (x, y, cap, sx, sy) libres -> dimensions réellement peintes ;
  - optimiseur : Nelder-Mead déterministe (numpy), deux départs (cap et cap + 180°).
Le type retenu est celui de meilleure IoU sur toute la composante (étape 1 ou pose affinée) ; l'écart au second
type mesure la sûreté du typage. Acceptation : IoU restreinte normée >= 0,60.
"""
from __future__ import annotations

import math

import numpy as np

import commun_pilote as C

TYPES = ("TD", "TAD", "TAG", "TD_TAD", "TD_TAG", "TRIDENT")


def gabarit(t):
    g = C.spec()["gabarits"]
    if t == "VELO":
        v = g["VELO"]
        return [[np.asarray(v["polygone"], float)]] + [[np.asarray(v["parties"][k]["polygone"], float)] for k in ("roue_arriere", "roue_avant")]
    if t == "TRIDENT":
        return [[np.asarray(g["TD_TAD"]["polygone"], float)], [np.asarray(g["TD_TAG"]["polygone"], float)]]
    return [[np.asarray(g[t]["polygone"], float)]]


def centre_gabarit(polys):
    P = np.vstack([p[0] for p in polys])
    # barycentre surfacique approché par rastérisation fine
    x0, y0 = P.min(0) - 0.05
    x1, y1 = P.max(0) + 0.05
    geo = (x0, y1)
    H, W = int((y1 - y0) / 0.01) + 1, int((x1 - x0) / 0.01) + 1
    cov = C.rasteriser([[p[0]] for p in polys], geo, (H, W), res=0.01, ss=1)
    rr, cc = np.nonzero(cov > 0.5)
    return float(x0 + (cc.mean() + 0.5) * 0.01), float(y1 - (rr.mean() + 0.5) * 0.01)


def poser_gabarit(polys, x, y, cap, sx=1.0, sy=1.0, centre=(0.0, 0.0)):
    """Pose : le point `centre` du gabarit (coordonnées gabarit, avant échelle) en (x, y)."""
    out = []
    for poly in polys:
        rings = []
        for ring in poly:
            R = (np.asarray(ring, float) - centre)
            rings.append(C.poser(R, x, y, cap, sx, sy))
        out.append(rings)
    return out


def nelder_mead(f, x0, pas, iters=220, tol=1e-5):
    n = len(x0)
    S = [np.asarray(x0, float)]
    for i in range(n):
        v = np.array(x0, float)
        v[i] += pas[i]
        S.append(v)
    F = [f(s) for s in S]
    for _ in range(iters):
        o = np.argsort(F)
        S = [S[i] for i in o]
        F = [F[i] for i in o]
        if abs(F[-1] - F[0]) < tol:
            break
        c = np.mean(S[:-1], axis=0)
        xr = c + (c - S[-1])
        fr = f(xr)
        if fr < F[0]:
            xe = c + 2 * (c - S[-1])
            fe = f(xe)
            if fe < fr:
                S[-1], F[-1] = xe, fe
            else:
                S[-1], F[-1] = xr, fr
        elif fr < F[-2]:
            S[-1], F[-1] = xr, fr
        else:
            xc = c + 0.5 * (S[-1] - c)
            fc = f(xc)
            if fc < F[-1]:
                S[-1], F[-1] = xc, fc
            else:
                for i in range(1, len(S)):
                    S[i] = S[0] + 0.5 * (S[i] - S[0])
                    F[i] = f(S[i])
    i = int(np.argmin(F))
    return S[i], F[i]


def candidats(det):
    out = []
    for d in det["comps"]:
        if d["classe"] == "fleche_candidate" or (d["classe"] in ("symbole_ou_autre", "ligne_courbe") and 0.4 <= d["aire_m2"] <= 3.2 and 2.5 <= d["long_m"] <= 7.5 and d["larg_m"] <= 2.1):
            out.append(d)
    return out


def candidats_velo(det):
    return [d for d in det["comps"] if d["classe"] in ("symbole_ou_autre", "ligne_courbe", "tache") and 0.5 <= d["long_m"] <= 1.7
            and 0.25 <= d["larg_m"] <= 1.1 and 0.06 <= d["aire_m2"] <= 0.6]


def ajuster(d, det, geo, types=TYPES, marge=1.0, echelles_normees=(1.0,)):
    P = det["p"]
    half = 0.5 * d["long_m"] + marge
    X0, X1 = d["cx"] - half, d["cx"] + half
    Y0, Y1 = d["cy"] - half, d["cy"] + half
    r0, c0 = C.l93_vers_px(X0, Y1, geo)
    r1, c1 = C.l93_vers_px(X1, Y0, geo)
    r0, c0 = int(max(0, math.floor(r0))), int(max(0, math.floor(c0)))
    r1, c1 = int(min(P.shape[0], math.ceil(r1) + 1)), int(min(P.shape[1], math.ceil(c1) + 1))
    win = P[r0:r1, c0:c1].astype(np.float64)
    # composante seule (les marques voisines ne doivent pas attirer le gabarit) : p hors de la composante dilatée
    lab = det["lab"][r0:r1, c0:c1]
    proche = C.max_filtre((lab == d["id"]).astype(np.float32) * 255, 9) > 0
    win = np.where(proche, win, 0.0)
    wgeo = (geo[0] + c0 * C.PX, geo[1] - r0 * C.PX)
    shape = win.shape
    sp = win.sum()

    def iou(polys_l93, restreint=True):
        """IoU douce ; restreinte : p limité au gabarit dilaté de 0,30 m (un tiret ou une ligne collé à la flèche,
        dans la même composante, ne pénalise que sa partie proche du gabarit)."""
        T = C.rasteriser(polys_l93, wgeo, shape, ss=4).astype(np.float64)
        pw = np.where(C.rasteriser_tampon(polys_l93, wgeo, shape, 0.30), win, 0.0) if restreint else win
        inter = np.minimum(T, pw).sum()
        return inter / max(np.maximum(T, pw).sum(), 1e-9)

    res = {}
    for t0_, e0 in [(t, e) for t in types for e in echelles_normees]:
        t = t0_ if len(echelles_normees) == 1 else f"{t0_}@{e0:g}"
        polys = [[np.asarray(r, float) * e0 for r in poly] for poly in gabarit(t0_)]
        ctr = centre_gabarit(polys)
        best = None
        # étape 1 : IoU sur toute la composante (bassin d'attraction large), départs cap PCA +/- 20° et sens opposé
        for sens in (0.0, math.pi):
            for dc in (-20.0, 0.0, 20.0):
                cap0 = d["angle_rad"] + sens + math.radians(dc)

                def f0(v):
                    return -iou(poser_gabarit(polys, v[0], v[1], v[2], 1.0, 1.0, ctr), restreint=False)
                v0, f0v = nelder_mead(f0, [d["cx"], d["cy"], cap0], [0.15, 0.15, math.radians(6)], iters=120, tol=1e-4)
                if best is None or f0v < best[1]:
                    best = (v0, f0v)
        # étape 2 : affinage sur l'IoU restreinte

        def f1(v):
            return -iou(poser_gabarit(polys, v[0], v[1], v[2], 1.0, 1.0, ctr))
        v1, f1v = nelder_mead(f1, list(best[0]), [0.05, 0.05, math.radians(2)])

        def f2(v):
            if not (0.6 < v[3] < 1.5 and 0.6 < v[4] < 1.5):
                return 1.0
            return -iou(poser_gabarit(polys, v[0], v[1], v[2], v[3], v[4], ctr))
        v2, f2v = nelder_mead(f2, [v1[0], v1[1], v1[2], 1.0, 1.0], [0.08, 0.08, math.radians(3), 0.08, 0.08], iters=300)
        iou_comp = iou(poser_gabarit(polys, v1[0], v1[1], v1[2], 1.0, 1.0, ctr), restreint=False)
        res[t] = {"iou_norme": -f1v, "iou_composante": float(max(iou_comp, -best[1])), "pose_norme": [float(v1[0]), float(v1[1]), float(v1[2])],
                  "iou_libre": -f2v, "pose_libre": [float(v2[0]), float(v2[1]), float(v2[2])], "echelle_libre": [float(v2[3]), float(v2[4])],
                  "centre_gabarit": ctr}
    # typage sur l'IoU de toute la composante (l'IoU restreinte favorise les gabarits plus petits)
    ordre = sorted(res, key=lambda t: -res[t]["iou_composante"])
    t0 = ordre[0]
    r = res[t0]
    # origine IISR (milieu du pied de la tige) de la pose normée
    o = C.poser(np.array([[0.0, 0.0]]) - r["centre_gabarit"], *r["pose_norme"])[0]
    cap = r["pose_norme"][2]
    return {"composante": d["id"], "type": t0, "iou_norme": r["iou_norme"], "iou_libre": r["iou_libre"],
            "echelle_libre": r["echelle_libre"], "iou_composante": r["iou_composante"],
            "marge_type": r["iou_composante"] - res[ordre[1]]["iou_composante"], "second": ordre[1],
            "origine_l93": [float(o[0]), float(o[1])], "cap_trigo_deg": float(math.degrees(cap) % 360),
            "azimut_deg": float((90 - math.degrees(cap)) % 360),
            "pose_norme": r["pose_norme"], "pose_libre": r["pose_libre"], "centre_gabarit": r["centre_gabarit"],
            "ecart_pose_libre_norme_m": float(math.hypot(r["pose_libre"][0] - r["pose_norme"][0], r["pose_libre"][1] - r["pose_norme"][1])),
            "masse_p": float(sp * C.PX ** 2), "scores": {t: round(res[t]["iou_norme"], 3) for t in res},
            "scores_libres": {t: round(res[t]["iou_libre"], 3) for t in res},
            "scores_composante": {t: round(res[t]["iou_composante"], 3) for t in res}}


def polygones(a, libre=False):
    t, _, e = a["type"].partition("@")
    polys = [[np.asarray(r, float) * (float(e) if e else 1.0) for r in poly] for poly in gabarit(t)]
    if libre:
        return poser_gabarit(polys, *a["pose_libre"], *a["echelle_libre"], centre=a["centre_gabarit"])
    return poser_gabarit(polys, *a["pose_norme"], 1.0, 1.0, centre=a["centre_gabarit"])
