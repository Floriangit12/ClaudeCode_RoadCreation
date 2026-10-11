"""Comparaisons du pilote : géométrie ajustée sur l'ortho 2022 contre (a) le levé GAM là où l'entité GAM est
présente à l'identique en 2022, (b) la BD ORTHO 2024 recalée (persistance et décalage 2022 -> 2024).

GAM : bandes de zébra = polylignes fermées à 4 sommets distincts ; flèches = polylignes fermées de 7 à 30 sommets
(périmètre 6-16 m, longueur 2,5-6,5 m) ; lignes = polylignes ouvertes.
"""
from __future__ import annotations

import math

import numpy as np

import commun_pilote as C


def _rect_params(P):
    Q = P[:-1] if C.ferme(P) else P
    if len(Q) != 4:
        return None
    e = np.diff(np.vstack([Q, Q[:1]]), axis=0)
    lens = np.linalg.norm(e, axis=1)
    i = int(np.argmax(lens))
    ang = math.atan2(e[i][1], e[i][0])
    return {"centre": Q.mean(0), "angle_rad": ang, "longueur_m": float((lens[i] + lens[(i + 2) % 4]) / 2),
            "largeur_m": float((lens[(i + 1) % 4] + lens[(i + 3) % 4]) / 2), "poly": Q}


def gam_rectangles(X0, Y0, X1, Y1):
    out = []
    for p, P in C.gam_dans(X0, Y0, X1, Y1):
        if len(P) == 5 and C.ferme(P):
            r = _rect_params(P)
            if r and 0.3 <= r["largeur_m"] <= 0.75 and 1.5 <= r["longueur_m"] <= 7:
                out.append(r)
    return out


def gam_fleches(X0, Y0, X1, Y1):
    out = []
    for p, P in C.gam_dans(X0, Y0, X1, Y1):
        if not (len(P) >= 8 and C.ferme(P)):
            continue
        per = float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())
        Q = P[:-1]
        c = Q.mean(0)
        cov = np.cov((Q - c).T)
        w, v = np.linalg.eigh(cov)
        ax = v[:, 1]
        u = (Q - c) @ ax
        if 6 <= per <= 16 and 2.5 <= u.max() - u.min() <= 6.5:
            out.append({"poly": Q, "perimetre_m": per, "longueur_m": float(u.max() - u.min())})
    return out


def centroide_surface(poly):
    x, y = poly[:, 0], poly[:, 1]
    xs, ys = np.roll(x, -1), np.roll(y, -1)
    cr = x * ys - xs * y
    A = cr.sum() / 2
    return np.array([((x + xs) * cr).sum() / (6 * A), ((y + ys) * cr).sum() / (6 * A)]), abs(A)


def iou_polygones(polysA, polysB, res=0.01):
    P = np.vstack([r for poly in polysA + polysB for r in poly])
    x0, y0 = P.min(0) - 0.1
    x1, y1 = P.max(0) + 0.1
    geo = (x0, y1)
    shape = (int((y1 - y0) / res) + 1, int((x1 - x0) / res) + 1)
    A = C.rasteriser(polysA, geo, shape, res=res, ss=1) > 0.5
    B = C.rasteriser(polysB, geo, shape, res=res, ss=1) > 0.5
    return float((A & B).sum() / max((A | B).sum(), 1))


def comparer_zebras(passages_polys, rects):
    """passages_polys : [{passage, indice, anneau (4 pts), regularise}] -> écarts aux rectangles GAM appariés."""
    out = []
    for b in passages_polys:
        Q = np.asarray(b["anneau"])
        r = _rect_params(np.vstack([Q, Q[:1]]))
        best = None
        for g in rects:
            d = np.linalg.norm(r["centre"] - g["centre"])
            if d < 0.6 and abs(C.ecart_axial(r["angle_rad"], g["angle_rad"])) < math.radians(10):
                if best is None or d < best[0]:
                    best = (d, g)
        if best is None:
            continue
        g = best[1]
        th = r["angle_rad"]
        eu = np.array([math.cos(th), math.sin(th)])
        ev = np.array([-math.sin(th), math.cos(th)])
        dc = r["centre"] - g["centre"]
        out.append({"passage": b["passage"], "indice": b["indice"], "regularise": b["regularise"],
                    "ecart_centre_m": float(np.linalg.norm(dc)), "ecart_long_bande_m": float(dc @ eu),
                    "ecart_travers_m": float(dc @ ev), "ecart_angle_deg": float(math.degrees(C.ecart_axial(r["angle_rad"], g["angle_rad"]))),
                    "largeur_ortho_m": r["largeur_m"], "largeur_gam_m": g["largeur_m"],
                    "longueur_ortho_m": r["longueur_m"], "longueur_gam_m": g["longueur_m"],
                    "iou": iou_polygones([[Q]], [[g["poly"]]])})
    return out


def comparer_fleches(fleches_polys, gfl):
    """fleches_polys : [{id, type, polys (pose normée), polys_libre}] -> écarts aux contours GAM appariés."""
    out = []
    for f in fleches_polys:
        ext = np.vstack([p[0] for p in f["polys"]])
        cf = ext.mean(0)
        best = None
        for g in gfl:
            d = np.linalg.norm(g["poly"].mean(0) - cf)
            if d < 2.0 and (best is None or d < best[0]):
                best = (d, g)
        if best is None:
            continue
        g = best[1]
        cg, ag = centroide_surface(g["poly"])
        # centroïde surfacique du gabarit (union approchée par rastérisation)
        P = np.vstack([r for poly in f["polys"] for r in poly])
        x0, y0 = P.min(0) - 0.05
        x1, y1 = P.max(0) + 0.05
        cov = C.rasteriser(f["polys"], (x0, y1), (int((y1 - y0) / 0.01) + 1, int((x1 - x0) / 0.01) + 1), res=0.01, ss=1) > 0.5
        rr, cc = np.nonzero(cov)
        ct = np.array([x0 + (cc.mean() + 0.5) * 0.01, y1 - (rr.mean() + 0.5) * 0.01])
        cap = f["cap_rad"]
        eu = np.array([math.cos(cap), math.sin(cap)])
        ev = np.array([-math.sin(cap), math.cos(cap)])
        # dimensions GAM dans le repère de la flèche ajustée
        ug = (g["poly"] - cg) @ eu
        vg = (g["poly"] - cg) @ ev
        dc = ct - cg
        rec = {"id": f["id"], "type": f["type"], "ecart_centroide_m": float(np.linalg.norm(dc)),
               "ecart_longitudinal_m": float(dc @ eu), "ecart_lateral_m": float(dc @ ev),
               "iou_gabarit_norme_gam": iou_polygones(f["polys"], [[g["poly"]]]),
               "longueur_gam_m": float(ug.max() - ug.min()), "largeur_gam_m": float(vg.max() - vg.min()),
               "aire_gam_m2": float(ag), "aire_gabarit_m2": float(cov.sum() * 1e-4)}
        if f.get("polys_libre"):
            rec["iou_gabarit_libre_gam"] = iou_polygones(f["polys_libre"], [[g["poly"]]])
        out.append(rec)
    return out


def comparer_lignes(lignes, X0, Y0, X1, Y1, tol=0.5):
    """Écart latéral (signé, m) des axes ajustés aux polylignes GAM ouvertes quasi parallèles (< 10°) à < tol."""
    gl = [P for p, P in C.gam_dans(X0, Y0, X1, Y1) if not (len(P) >= 4 and C.ferme(P))]
    out = []
    for ln in lignes:
        A = np.asarray(ln["axe_l93"])
        ds = []
        for q in A:
            best = None
            for P in gl:
                a, b = P[:-1], P[1:]
                ab = b - a
                L2 = np.maximum((ab ** 2).sum(1), 1e-12)
                t = np.clip(((q - a) * ab).sum(1) / L2, 0, 1)
                pr = a + t[:, None] * ab
                dd = np.linalg.norm(q - pr, axis=1)
                k = int(np.argmin(dd))
                if dd[k] > tol:
                    continue
                ang_g = math.atan2(ab[k][1], ab[k][0])
                k2 = min(len(A) - 1, max(1, int(np.argmin(np.linalg.norm(A - q, axis=1)))))
                ang_l = math.atan2(A[k2][1] - A[k2 - 1][1], A[k2][0] - A[k2 - 1][0])
                if abs(C.ecart_axial(ang_g, ang_l)) > math.radians(10):
                    continue
                if best is None or dd[k] < best:
                    best = dd[k]
            if best is not None:
                ds.append(best)
        if len(ds) >= 3:
            out.append({"composante": ln["composante"], "n_points": len(ds), "part_appariee": len(ds) / len(A),
                        "ecart_median_m": float(np.median(ds)), "ecart_p90_m": float(np.percentile(ds, 90))})
    return out


def persistance_2024(polys, demi=0.6):
    """Support de peinture 2024 (BD ORTHO 20 cm recalée, carte p du site) sous un polygone ajusté en 2022 :
    support à décalage nul et meilleur décalage (+/- demi, pas 5 cm)."""
    import carte_site as CS
    import os
    from pathlib import Path
    d = CS.charger("2024", Path(os.environ.get("PJ_CACHE_MARQUAGES", CS.CACHE)))
    pm = np.maximum(d["p_blanc"], d["p_jaune"]).astype(np.float32) / 255.0
    geo = tuple(d["geo"].tolist())
    P = np.vstack([r for poly in polys for r in poly])
    x0, y0 = P.min(0) - 0.1
    x1, y1 = P.max(0) + 0.1
    r0, c0 = C.l93_vers_px(x0, y1, geo)
    r0, c0 = int(math.floor(r0)), int(math.floor(c0))
    sub_geo = (geo[0] + c0 * C.PX, geo[1] - r0 * C.PX)
    h = int((y1 - y0) / C.PX) + 2
    w = int((x1 - x0) / C.PX) + 2
    cov = C.rasteriser(polys, sub_geo, (h, w), ss=2)
    rr, cc = np.nonzero(cov >= 0.5)
    rr, cc = rr + r0, cc + c0
    k = int(round(demi / C.PX))
    H, W = pm.shape
    grid = np.zeros((2 * k + 1, 2 * k + 1))
    for i, dr in enumerate(range(-k, k + 1)):
        for j, dc in enumerate(range(-k, k + 1)):
            grid[i, j] = pm[np.clip(rr + dr, 0, H - 1), np.clip(cc + dc, 0, W - 1)].mean()
    ii, jj = np.mgrid[-k:k + 1, -k:k + 1]
    i, j = np.unravel_index(int(np.argmax(grid - 0.02 * np.hypot(ii, jj) * C.PX)), grid.shape)
    return {"support0": float(grid[k, k]), "support_max": float(grid[i, j]),
            "decalage_m": [float((j - k) * C.PX), float(-(i - k) * C.PX)]}


def comparer_fleches_segments(fleches_polys, tampon=0.5, demi=0.5, pas=0.02):
    """Le levé GAM dessine les flèches en segments à 2 sommets (contour éclaté) : on rassemble les segments courts
    (< 2,5 m) entièrement dans la boîte du gabarit posé élargie de `tampon`, densifiés à 2 cm, et on mesure :
    distance des points GAM au contour du gabarit (moyenne, p90) ; translation (+/- demi, pas 2 cm) qui minimise
    la distance moyenne -> décalage GAM - ortho (m) et résidu de forme après translation."""
    segs = [P for p, P in C.gam_lignes() if len(P) == 2 and np.linalg.norm(P[1] - P[0]) < 2.5]
    out = []
    for f in fleches_polys:
        rings = [np.asarray(poly[0]) for poly in f["polys"]]
        allp = np.vstack(rings)
        x0, y0 = allp.min(0) - tampon
        x1, y1 = allp.max(0) + tampon
        pts = []
        for P in segs:
            if (P[:, 0] >= x0).all() and (P[:, 0] <= x1).all() and (P[:, 1] >= y0).all() and (P[:, 1] <= y1).all():
                n = max(2, int(np.linalg.norm(P[1] - P[0]) / 0.02) + 1)
                t = np.linspace(0, 1, n)[:, None]
                pts.append(P[0] + t * (P[1] - P[0]))
        if not pts:
            continue
        Q = np.vstack(pts)
        A = np.vstack([np.roll(r, 0, axis=0) for r in rings])
        B = np.vstack([np.roll(r, -1, axis=0) for r in rings])

        def dist(Qs):
            ab = B - A
            L2 = np.maximum((ab ** 2).sum(1), 1e-12)
            t = np.clip(((Qs[:, None, :] - A[None]) * ab[None]).sum(-1) / L2[None], 0, 1)
            pr = A[None] + t[..., None] * ab[None]
            return np.sqrt(((Qs[:, None, :] - pr) ** 2).sum(-1)).min(1)
        d0 = dist(Q)
        best = (d0.mean(), 0.0, 0.0)
        Qs = Q[:: max(1, len(Q) // 300)]
        for dx in np.arange(-demi, demi + 1e-9, 0.04):
            for dy in np.arange(-demi, demi + 1e-9, 0.04):
                m = dist(Qs - [dx, dy]).mean()
                if m < best[0]:
                    best = (m, dx, dy)
        # affinage au pas de 1 cm
        b0 = best
        for dx in np.arange(b0[1] - 0.04, b0[1] + 0.041, 0.01):
            for dy in np.arange(b0[2] - 0.04, b0[2] + 0.041, 0.01):
                m = dist(Qs - [dx, dy]).mean()
                if m < best[0]:
                    best = (m, dx, dy)
        d1 = dist(Q - [best[1], best[2]])
        cap = f["cap_rad"]
        eu = np.array([math.cos(cap), math.sin(cap)])
        ev = np.array([math.sin(cap), -math.cos(cap)])
        off = np.array([best[1], best[2]])
        out.append({"id": f["id"], "type": f["type"], "n_points_gam": int(len(Q)), "distance_moyenne_m": float(d0.mean()),
                    "distance_p90_m": float(np.percentile(d0, 90)), "decalage_gam_moins_ortho_m": [float(best[1]), float(best[2])],
                    "decalage_longitudinal_m": float(off @ eu), "decalage_lateral_droite_m": float(off @ ev),
                    "norme_decalage_m": float(np.hypot(best[1], best[2])), "residu_forme_moyen_m": float(d1.mean()),
                    "residu_forme_p90_m": float(np.percentile(d1, 90))})
    return out
