"""Référence réservée : tirage de tuiles de 10 x 10 m dans la chaussée du site (graine fixe), planches d'annotation
manuelle (ortho 2022 seule, aucune extraction dessinée) et mesure de l'extraction contre l'annotation.

Protocole (critère MQ1 / lot 1j du plan avant travaux) :
1. tirage : centres tirés uniformément (numpy RandomState(graine)) parmi les pixels de 0,25 m de la chaussée du site
   (paquet v1 surfaces_2026, classes chaussee / piste_cyclable / quai_bus, hors construit_2023_2024), privés des
   zones où l'ortho 2022 ne vaut pas pour les marquages à la date cible (polygones fournis par l'appelant) ;
   tuile acceptée si >= 50 % de sa surface est en chaussée et si elle ne recouvre aucune tuile déjà tirée ;
2. planches : ortho PCRS 2022 de la tuile (+ 1 m de marge), agrandie x4 (1,25 cm / px), en deux versions
   (brute et contraste étiré), quadrillage de 1 m en coordonnées de tuile (origine au coin sud-ouest) ;
3. annotation : faite à la main, en regardant ces planches seulement, avant toute mesure de l'extraction sur les
   tuiles ; enregistrée avec son sha256 ; jamais utilisée pour régler l'extraction ;
4. mesure (mesurer_tuiles) : longueur annotée reprise par l'extraction (tolérance latérale, orientation), par type ;
   phase des tirets (écart longitudinal des centres de tirets).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import raster as R

TAILLE = 10.0
MARGE = 1.0
ZOOM = 4
CLASSES_CHAUSSEE = ("chaussee", "piste_cyclable", "quai_bus")
SURF_V1 = R.RACINE / "recon/out/paquet_jardin/package/donnees/surfaces/surfaces_2026.geojson"


def _anneaux(g):
    if g["type"] == "Polygon":
        return [[np.asarray(r)[:, :2] for r in g["coordinates"]]]
    if g["type"] == "MultiPolygon":
        return [[np.asarray(r)[:, :2] for r in p] for p in g["coordinates"]]
    return []


def masque_chaussee_v1(emprise=R.EMPRISE_SITE, res=0.25):
    """Chaussée du paquet v1 (indice de tirage seulement), hors secteur construit en 2023-2024."""
    X0, Y0, X1, Y1 = emprise
    geo = (X0, Y1)
    shape = (int(round((Y1 - Y0) / res)), int(round((X1 - X0) / res)))
    polys = []
    for f in R.lire_json(SURF_V1)["features"]:
        pr = f["properties"]
        if pr.get("classe") in CLASSES_CHAUSSEE and pr.get("etat") != "construit_2023_2024" and f.get("geometry"):
            polys += _anneaux(f["geometry"])
    return R.rasteriser(polys, geo, shape, res=res, ss=2) >= 0.5, geo


def tirer_tuiles(zones_exclues, n=20, graine=4111, emprise=R.EMPRISE_SITE, res=0.25):
    """zones_exclues : liste de polygones L93 ([anneau ext, trous...]). -> liste de tuiles {id, x0, y0, x1, y1}."""
    m, geo = masque_chaussee_v1(emprise, res)
    if zones_exclues:
        m &= R.rasteriser(zones_exclues, geo, m.shape, res=res, ss=2) < 0.5
    H, W = m.shape
    X0, Y0, X1, Y1 = emprise
    h = int(round(TAILLE / 2 / res))
    interieur = np.zeros_like(m)
    interieur[h:H - h, h:W - h] = True
    cand = np.flatnonzero((m & interieur).ravel())
    rs = np.random.RandomState(graine)
    tuiles, essais = [], 0
    while len(tuiles) < n and essais < 20000:
        essais += 1
        i = int(cand[rs.randint(len(cand))])
        r, c = divmod(i, W)
        cx, cy = R.px_vers_l93(r, c, geo, res)
        cx, cy = round(float(cx), 2), round(float(cy), 2)
        x0, y0 = cx - TAILLE / 2, cy - TAILLE / 2
        if any(abs(cx - t["cx"]) < TAILLE and abs(cy - t["cy"]) < TAILLE for t in tuiles):
            continue
        sub = m[r - h:r + h, c - h:c + h]
        if sub.mean() < 0.5:
            continue
        tuiles.append({"id": f"T{len(tuiles) + 1:02d}", "cx": cx, "cy": cy, "x0": x0, "y0": y0, "x1": x0 + TAILLE, "y1": y0 + TAILLE,
                       "part_chaussee": round(float(sub.mean()), 3)})
    return {"graine": graine, "taille_m": TAILLE, "essais": essais, "tuiles": tuiles,
            "regle": "centres uniformes dans la chaussée v1 hors zones exclues ; >= 50 % de chaussée ; sans recouvrement"}


def _etirer(a):
    """Contraste étiré par canal de luminance (percentiles 2-99,5 de la tuile)."""
    f = a.astype(np.float32)
    L = f.mean(-1)
    lo, hi = np.percentile(L, 2), np.percentile(L, 99.5)
    g = np.clip((f - lo) / max(hi - lo, 1.0), 0, 1) ** 0.8
    return (g * 255).astype(np.uint8)


def planche_annotation(t, chemin):
    """Ortho 2022 de la tuile (+ marge) x4, brute | étirée, quadrillage 1 m en coordonnées de tuile."""
    x0, y0 = t["x0"] - MARGE, t["y0"] - MARGE
    x1, y1 = t["x1"] + MARGE, t["y1"] + MARGE
    rgb, geo = R.mosaique_2022(x0, y0, x1, y1)
    panneaux = []
    for img in (rgb, _etirer(rgb)):
        im = Image.fromarray(img).resize((img.shape[1] * ZOOM, img.shape[0] * ZOOM), Image.BICUBIC)
        d = ImageDraw.Draw(im, "RGBA")
        s = ZOOM / R.PX

        def px(xl, yl):
            return ((t["x0"] + xl - geo[0]) * s, (geo[1] - (t["y0"] + yl)) * s)
        for k in range(0, int(TAILLE) + 1):
            a, b = px(k, -0.3), px(k, TAILLE + 0.3)
            d.line([a, b], fill=(255, 0, 0, 110) if k % 5 else (255, 0, 0, 170), width=1)
            a, b = px(-0.3, k), px(TAILLE + 0.3, k)
            d.line([a, b], fill=(255, 0, 0, 110) if k % 5 else (255, 0, 0, 170), width=1)
            d.text(px(k + 0.03, -0.45), str(k), fill=(255, 255, 0, 255))
            d.text(px(-0.75, k + 0.08), str(k), fill=(255, 255, 0, 255))
        for k in np.arange(0, TAILLE + 1e-9, 0.25):
            for (a, b) in ((px(k, 0), px(k, -0.12)), (px(k, TAILLE), px(k, TAILLE + 0.12)), (px(0, k), px(-0.12, k)), (px(TAILLE, k), px(TAILLE + 0.12, k))):
                d.line([a, b], fill=(255, 255, 0, 200), width=1)
        panneaux.append(im)
    W = sum(p.size[0] for p in panneaux) + 10
    out = Image.new("RGB", (W, panneaux[0].size[1] + 18), (0, 0, 0))
    out.paste(panneaux[0], (0, 18))
    out.paste(panneaux[1], (panneaux[0].size[0] + 10, 18))
    ImageDraw.Draw(out).text((4, 3), f"{t['id']}  coin SO L93 ({t['x0']:.2f}, {t['y0']:.2f})  ortho PCRS 5 cm 2022-05-10, x{ZOOM}, grille 1 m (coord. tuile)", fill=(255, 255, 255))
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    out.save(chemin, quality=92)
    return chemin


def planche_fine(t, chemin, zoom=5, marge=0.4):
    """Tuile entière agrandie x5 (1 cm / px, 1080 px : entre sans réduction dans l'entrée image), contraste étiré, quadrillage 0,5 m (1 m appuyé), libellés de mètre
    en coordonnées de tuile sur les quatre bords."""
    x0, y0 = t["x0"] - marge, t["y0"] - marge
    x1, y1 = t["x1"] + marge, t["y1"] + marge
    rgb, geo = R.mosaique_2022(x0, y0, x1, y1)
    rgb = _etirer(rgb)
    im = Image.fromarray(rgb).resize((rgb.shape[1] * zoom, rgb.shape[0] * zoom), Image.BICUBIC)
    d = ImageDraw.Draw(im, "RGBA")
    s = zoom / R.PX

    def px(xl, yl):
        return ((t["x0"] + xl - geo[0]) * s, (geo[1] - (t["y0"] + yl)) * s)
    for k in np.arange(0, TAILLE + 1e-9, 0.5):
        fort = abs(k - round(k)) < 1e-6
        col = (255, 0, 0, 150) if fort else (255, 80, 80, 70)
        d.line([px(k, -0.3), px(k, TAILLE + 0.3)], fill=col, width=1)
        d.line([px(-0.3, k), px(TAILLE + 0.3, k)], fill=col, width=1)
        if fort:
            for (xa, ya) in ((k + 0.03, -0.35), (k + 0.03, TAILLE + 0.12), (-0.35, k + 0.04), (TAILLE + 0.1, k + 0.04)):
                d.text(px(xa, ya), f"{int(round(k))}", fill=(255, 255, 0, 255))
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    im.save(chemin, quality=92)
    return chemin


def mosaique_points(t, points, chemin, cote=1.2, zoom=16, par_ligne=3):
    """Agrandissements x16 (0,31 cm / px) autour de points de tuile (lecture des extrémités de tirets) :
    quadrillage 0,1 m, libellés au 0,5 m, en coordonnées de tuile. points : [(etiquette, xl, yl)]."""
    vignettes = []
    for (lab, xl, yl) in points:
        a, b = xl - cote / 2, yl - cote / 2
        rgb, geo = R.mosaique_2022(t["x0"] + a - 0.2, t["y0"] + b - 0.2, t["x0"] + a + cote + 0.2, t["y0"] + b + cote + 0.2)
        rgb = _etirer(rgb)
        im = Image.fromarray(rgb).resize((rgb.shape[1] * zoom, rgb.shape[0] * zoom), Image.BICUBIC)
        d = ImageDraw.Draw(im, "RGBA")
        s = zoom / R.PX

        def px(u, v):
            return ((t["x0"] + u - geo[0]) * s, (geo[1] - (t["y0"] + v)) * s)
        for k in np.arange(math.floor(a * 10) / 10, a + cote + 1e-9, 0.1):
            fort = abs(k * 2 - round(k * 2)) < 1e-6
            d.line([px(k, b - 0.1), px(k, b + cote + 0.1)], fill=(255, 0, 0, 170 if fort else 60), width=1)
            if fort:
                d.text(px(k + 0.005, b + cote + 0.08), f"{k:.1f}", fill=(255, 255, 0, 255))
        for k in np.arange(math.floor(b * 10) / 10, b + cote + 1e-9, 0.1):
            fort = abs(k * 2 - round(k * 2)) < 1e-6
            d.line([px(a - 0.1, k), px(a + cote + 0.1, k)], fill=(255, 0, 0, 170 if fort else 60), width=1)
            if fort:
                d.text(px(a - 0.08, k + 0.03), f"{k:.1f}", fill=(255, 255, 0, 255))
        d.text((4, 4), str(lab), fill=(0, 255, 255, 255))
        vignettes.append(im)
    if not vignettes:
        return None
    w, h = vignettes[0].size
    n = len(vignettes)
    cols = min(par_ligne, n)
    rows = (n + cols - 1) // cols
    out = Image.new("RGB", (cols * (w + 6), rows * (h + 6)), (0, 0, 0))
    for i, v in enumerate(vignettes):
        out.paste(v, ((i % cols) * (w + 6), (i // cols) * (h + 6)))
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    out.save(chemin, quality=92)
    return chemin


def planche_zoom(t, xl0, yl0, xl1, yl1, chemin, zoom=10):
    """Agrandissement d'une sous-fenêtre de tuile (coordonnées de tuile), quadrillage 0,25 m : lecture des
    extrémités de tirets."""
    x0, y0, x1, y1 = t["x0"] + xl0, t["y0"] + yl0, t["x0"] + xl1, t["y0"] + yl1
    rgb, geo = R.mosaique_2022(x0, y0, x1, y1)
    rgb = _etirer(rgb)
    im = Image.fromarray(rgb).resize((rgb.shape[1] * zoom, rgb.shape[0] * zoom), Image.BICUBIC)
    d = ImageDraw.Draw(im, "RGBA")
    s = zoom / R.PX

    def px(xl, yl):
        return ((t["x0"] + xl - geo[0]) * s, (geo[1] - (t["y0"] + yl)) * s)
    for k in np.arange(math.floor(xl0 * 4) / 4, xl1 + 1e-9, 0.25):
        d.line([px(k, yl0), px(k, yl1)], fill=(255, 0, 0, 160 if abs(k - round(k)) < 1e-6 else 70), width=1)
        if abs(k - round(k)) < 1e-6 or abs(k * 2 - round(k * 2)) < 1e-6:
            d.text(px(k + 0.01, yl1 - 0.08), f"{k:g}", fill=(255, 255, 0, 255))
    for k in np.arange(math.floor(yl0 * 4) / 4, yl1 + 1e-9, 0.25):
        d.line([px(xl0, k), px(xl1, k)], fill=(255, 0, 0, 160 if abs(k - round(k)) < 1e-6 else 70), width=1)
        if abs(k - round(k)) < 1e-6 or abs(k * 2 - round(k * 2)) < 1e-6:
            d.text(px(xl0 + 0.01, k + 0.06), f"{k:g}", fill=(255, 255, 0, 255))
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    im.save(chemin, quality=92)
    return chemin


# --------------------------------------------------------------------------- affinage de l'annotation
def _niveau50(x, y, niveau, depuis, sens):
    i = depuis
    n = len(y)
    while 0 <= i + sens < n:
        a, b = y[i], y[i + sens]
        if (a - niveau) * (b - niveau) <= 0 and a != b:
            return x[i] + (a - niveau) / (a - b) * (x[i + sens] - x[i])
        i += sens
    return None


def affiner_ligne(t, pts, extremites=False, pas=0.25, demi=0.30, contraste_min=10.0):
    """Lecture de profil le long d'une polyligne tracée à la main (coordonnées de tuile) : à chaque station, pic de
    luminance en travers (+/- demi), bords au niveau 50 % entre plateau et fond (0,18-0,35 m de part et d'autre),
    centre et largeur. Les extrémités (si demandé) : franchissement 50 % du profil axial à +/- 0,4 m des extrémités
    tracées. Le tracé à la main décide de l'existence, du type et de la topologie ; la lecture de profil ne fait que
    préciser la position (comme un accrochage de curseur). -> dict (points affinés en coordonnées de tuile)."""
    P = _tuile_l93(t, pts)
    rgb, geo = R.mosaique_2022(P[:, 0].min() - 1.5, P[:, 1].min() - 1.5, P[:, 0].max() + 1.5, P[:, 1].max() + 1.5)
    f = rgb.astype(np.float32)
    L = 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]
    Q, s = R.reechantillonner(P, pas)
    tg = np.gradient(Q, axis=0)
    tg /= np.maximum(np.linalg.norm(tg, axis=1, keepdims=True), 1e-9)
    nm = np.c_[-tg[:, 1], tg[:, 0]]
    vv = np.arange(-demi - 0.4, demi + 0.4 + 1e-9, 0.01)
    centres, largeurs, contrastes, garde = [], [], [], []
    for k in range(len(Q)):
        col = np.zeros_like(vv)
        for o in (-0.04, 0.0, 0.04):
            X = Q[k, 0] + o * tg[k, 0] + vv * nm[k, 0]
            Y = Q[k, 1] + o * tg[k, 1] + vv * nm[k, 1]
            col += R.echantillonner(L, geo, X, Y)
        col /= 3
        dedans = np.abs(vv) <= demi
        lis = np.convolve(np.nan_to_num(col), np.ones(5) / 5, mode="same")
        im = int(np.flatnonzero(dedans)[np.argmax(lis[dedans])])
        fg = np.nanmedian(col[(vv < vv[im] - 0.18) & (vv > vv[im] - 0.35)])
        fd = np.nanmedian(col[(vv > vv[im] + 0.18) & (vv < vv[im] + 0.35)])
        pl = np.nanmax(lis[max(0, im - 3):im + 4])
        fo = 0.5 * (fg + fd)
        c = pl - fo
        g = _niveau50(vv, col, 0.5 * (pl + fo), im, -1)
        d = _niveau50(vv, col, 0.5 * (pl + fo), im, +1)
        ok = np.isfinite(c) and c >= contraste_min and g is not None and d is not None and 0.05 <= d - g <= 0.45
        garde.append(bool(ok))
        centres.append(Q[k] + (0.5 * (g + d) if ok else 0.0) * nm[k])
        largeurs.append(d - g if ok else np.nan)
        contrastes.append(float(c) if np.isfinite(c) else np.nan)
    garde = np.array(garde)
    C = np.array(centres)
    res = {"n_stations": int(len(Q)), "n_valides": int(garde.sum()),
           "contraste_median_DN": round(float(np.nanmedian(np.array(contrastes)[garde])), 1) if garde.any() else None,
           "largeur_mediane_m": round(float(np.nanmedian(np.array(largeurs)[garde])), 3) if garde.any() else None}
    if garde.sum() < 2:
        res["pts"] = [list(map(float, p)) for p in np.asarray(pts, float)]
        res["affine"] = False
        return res
    if len(pts) == 2:
        # droite : moindres carrés sur les centres valides, extrémités = projections des extrémités tracées
        cg = C[garde]
        m = cg.mean(0)
        w, v = np.linalg.eigh(np.cov((cg - m).T))
        ax = v[:, 1]
        a = m + ((P[0] - m) @ ax) * ax
        b = m + ((P[-1] - m) @ ax) * ax
        Pa = np.vstack([a, b])
    else:
        # polyligne : polynôme v(u) (degré <= 3) dans le repère de la corde, ajusté sur les centres valides avec rejet
        # itératif des résidus > 2,5 sigma (évite les sauts sur un bord d'ombre ou une ligne voisine)
        cg = C[garde]
        o = P[0]
        u_ax = (P[-1] - P[0]) / max(np.linalg.norm(P[-1] - P[0]), 1e-9)
        v_ax = np.array([-u_ax[1], u_ax[0]])
        uu = (cg - o) @ u_ax
        vv2 = (cg - o) @ v_ax
        ok = np.ones(len(uu), bool)
        deg = int(min(3, max(1, len(P) - 1), ok.sum() - 1))
        for _ in range(4):
            coef = np.polyfit(uu[ok], vv2[ok], deg)
            r = vv2 - np.polyval(coef, uu)
            sig = max(float(np.std(r[ok])), 0.01)
            nouveau = np.abs(r) <= 2.5 * sig
            if nouveau.sum() < deg + 2 or (nouveau == ok).all():
                break
            ok = nouveau
        us = np.linspace((P[0] - o) @ u_ax, (P[-1] - o) @ u_ax, max(2, int(np.linalg.norm(P[-1] - P[0]) / 0.25) + 1))
        Pa = R.douglas_peucker(o + np.outer(us, u_ax) + np.outer(np.polyval(coef, us), v_ax), 0.01)
        res["rejets_polynome"] = int((~ok).sum())
    if extremites:
        u = Pa[-1] - Pa[0]
        Lseg = np.linalg.norm(u)
        u = u / max(Lseg, 1e-9)
        uu = np.arange(-0.5, Lseg + 0.5 + 1e-9, 0.01)
        prof = np.zeros_like(uu)
        nn = np.array([-u[1], u[0]])
        for o in (-0.03, 0.0, 0.03):
            prof += R.echantillonner(L, geo, Pa[0, 0] + uu * u[0] + o * nn[0], Pa[0, 1] + uu * u[1] + o * nn[1])
        prof /= 3
        ext = []
        for (u0, sens) in ((0.0, -1), (Lseg, +1)):
            i0 = int(np.argmin(np.abs(uu - (u0 - sens * 0.25))))
            pl = np.nanmedian(prof[(uu > 0.2) & (uu < Lseg - 0.2)]) if Lseg > 0.6 else np.nanmax(prof)
            hors = prof[(uu * sens > (u0 * sens + 0.25)) & (uu * sens < (u0 * sens + 0.5))] if sens > 0 else prof[(uu < u0 - 0.25) & (uu > u0 - 0.5)]
            fo = np.nanmedian(hors) if len(hors) else np.nan
            x50 = _niveau50(uu, prof, 0.5 * (pl + fo), i0, sens) if np.isfinite(fo) and pl - fo >= contraste_min else None
            ext.append(x50 if (x50 is not None and abs(x50 - u0) <= 0.4) else None)
        res["extremites_affinees"] = [e is not None for e in ext]
        a = Pa[0] + (ext[0] if ext[0] is not None else 0.0) * u
        b = Pa[0] + (ext[1] if ext[1] is not None else Lseg) * u
        Pa = np.vstack([a, b])
    res["pts"] = [[round(float(p[0] - t["x0"]), 3), round(float(p[1] - t["y0"]), 3)] for p in Pa]
    res["affine"] = True
    res["decalage_median_m"] = round(float(np.median(R.dist_point_polyligne(Q, Pa)[0])), 3)
    return res


def planche_annotation_superposee(t, lignes, chemin, zoom=5, marge=0.4):
    """Planche fine avec l'annotation (et elle seule) superposée : contrôle visuel de la référence."""
    planche_fine(t, chemin, zoom=zoom, marge=marge)
    im = Image.open(chemin).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    x0 = math.floor(round((t["x0"] - marge) / R.PX, 6)) * R.PX
    y1 = math.ceil(round((t["y1"] + marge) / R.PX, 6)) * R.PX
    s = zoom / R.PX
    cols = {"continue": (0, 255, 255, 230), "tiret": (255, 0, 255, 230), "tiret_court": (255, 140, 0, 230)}
    for k, ln in enumerate(lignes):
        P = np.asarray(ln["pts"], float)
        pts = [((t["x0"] + p[0] - x0) * s, (y1 - (t["y0"] + p[1])) * s) for p in P]
        col = cols.get(ln["type"], (255, 255, 0, 200))
        d.line(pts, fill=col, width=2)
        d.text((pts[0][0] + 4, pts[0][1] + 2), f"{k}:{ln['type'][:4]}", fill=col)
    im.save(chemin, quality=92)
    return chemin


# --------------------------------------------------------------------------- mesure
def _tuile_l93(t, P):
    P = np.asarray(P, float)
    return np.c_[P[:, 0] + t["x0"], P[:, 1] + t["y0"]]


def _couverture(seg, lignes_extraites, tol_lat, tol_ang_deg, pas=0.05):
    """Part de la polyligne `seg` (L93) à moins de tol_lat d'une ligne extraite d'orientation compatible."""
    Q, _ = R.reechantillonner(seg, pas)
    if len(Q) < 2:
        return 0.0, np.zeros(len(Q), bool)
    tg = np.gradient(Q, axis=0)
    ang = np.arctan2(tg[:, 1], tg[:, 0])
    ok = np.zeros(len(Q), bool)
    for P in lignes_extraites:
        P = np.asarray(P, float)
        if len(P) < 2:
            continue
        d, s = R.dist_point_polyligne(Q, P)
        near = d <= tol_lat
        if not near.any():
            continue
        seglen = np.linalg.norm(np.diff(P, axis=0), axis=1)
        s0 = np.r_[0, np.cumsum(seglen)]
        k = np.clip(np.searchsorted(s0, s[near], side="right") - 1, 0, len(P) - 2)
        a2 = np.arctan2(P[k + 1, 1] - P[k, 1], P[k + 1, 0] - P[k, 0])
        dang = np.abs((ang[near] - a2 + math.pi / 2) % math.pi - math.pi / 2)
        idx = np.flatnonzero(near)
        ok[idx[dang <= math.radians(tol_ang_deg)]] = True
    return float(ok.mean()), ok


def mesurer_tuiles(annotation, tuiles, lignes_extraites, tirets_extraits, tol_lat=0.15, tol_ang_deg=10.0):
    """annotation : {tuile_id: {"lignes": [{"type", "pts" (coord. tuile)}]}} ; lignes_extraites : polylignes L93 de
    l'extraction (toutes familles longitudinales, segments peints) ; tirets_extraits : [(debut, fin) L93] des tirets
    régularisés. -> reprise par type (longueur) et écarts de phase des tirets."""
    par_type, details, phases = {}, [], []
    tu = {t["id"]: t for t in tuiles}
    for tid, a in sorted(annotation.items()):
        t = tu[tid]
        bx = (t["x0"] - 0.5, t["y0"] - 0.5, t["x1"] + 0.5, t["y1"] + 0.5)
        loc = [P for P in lignes_extraites if len(P) and np.asarray(P)[:, 0].max() >= bx[0] and np.asarray(P)[:, 0].min() <= bx[2]
               and np.asarray(P)[:, 1].max() >= bx[1] and np.asarray(P)[:, 1].min() <= bx[3]]
        for k, ln in enumerate(a.get("lignes", [])):
            seg = _tuile_l93(t, ln["pts"])
            L = R.longueur(seg)
            part, _ = _couverture(seg, loc, tol_lat, tol_ang_deg)
            e = par_type.setdefault(ln["type"], {"longueur_m": 0.0, "reprise_m": 0.0, "n": 0})
            e["longueur_m"] += L
            e["reprise_m"] += L * part
            e["n"] += 1
            details.append({"tuile": tid, "k": k, "type": ln["type"], "longueur_m": round(L, 3), "part_reprise": round(part, 3)})
            if ln["type"] == "tiret":
                c = seg.mean(0)
                u = (seg[-1] - seg[0]) / max(np.linalg.norm(seg[-1] - seg[0]), 1e-9)
                best = None
                for (A, B) in tirets_extraits:
                    A, B = np.asarray(A, float), np.asarray(B, float)
                    m = 0.5 * (A + B)
                    v = B - A
                    if np.linalg.norm(v) < 1e-6:
                        continue
                    v = v / np.linalg.norm(v)
                    if abs(u @ v) < math.cos(math.radians(10)):
                        continue
                    lat = abs((m - c) @ np.array([-u[1], u[0]]))
                    lon = (m - c) @ u
                    if lat <= tol_lat and abs(lon) < 1.5 and (best is None or abs(lon) < abs(best[0])):
                        Lext = float(np.linalg.norm(B - A))
                        best = (lon, lat, Lext)
                if best is not None:
                    phases.append({"tuile": tid, "k": k, "ecart_centre_long_m": round(float(best[0]), 4), "ecart_lateral_m": round(float(best[1]), 4),
                                   "longueur_annotee_m": round(L, 3), "longueur_extraite_m": round(best[2], 3)})
                else:
                    phases.append({"tuile": tid, "k": k, "non_apparie": True, "longueur_annotee_m": round(L, 3)})
    for e in par_type.values():
        e["part_reprise"] = round(e["reprise_m"] / max(e["longueur_m"], 1e-9), 4)
        e["longueur_m"] = round(e["longueur_m"], 3)
        e["reprise_m"] = round(e["reprise_m"], 3)
    ap = [abs(p["ecart_centre_long_m"]) for p in phases if "ecart_centre_long_m" in p]
    return {"tolerance_laterale_m": tol_lat, "tolerance_angle_deg": tol_ang_deg, "par_type": par_type, "details": details,
            "phases_tirets": phases,
            "phase_tirets": {"n_annotes": len(phases), "n_apparies": len(ap),
                             "p50_m": round(float(np.percentile(ap, 50)), 4) if ap else None,
                             "p95_m": round(float(np.percentile(ap, 95)), 4) if ap else None,
                             "max_m": round(float(max(ap)), 4) if ap else None}}
