"""Datation du levé GAM de la signalisation horizontale (Meylan_Topo.dwg, calque SOL_SIGNALISATION_HORIZONTALE)
par confrontation de chaque entité aux peintures visibles sur l'ortho PCRS 2022 (5 cm) et la BD ORTHO 2024 (20 cm,
recalée sur le PCRS).

Pour chaque polyligne GAM (409) :
- polygone fermé (bande de zébra, flèche, carré...) : pixels intérieurs (rastérisation au pas de 5 cm) ;
  polyligne ouverte (ligne, tiret, axe) : points tous les 5 cm ;
- support(s) = moyenne de p (probabilité de peinture, max 3 x 3 = tolérance +/- 5 cm) sur ces points, translatés de
  s, s parcourant +/- 1,2 m au pas de 5 cm ;
- statut : « present_identique » si support(0) >= 0,6 ; « deplace » si max support >= 0,6, |s*| >= 0,15 m et gain
  >= 0,25 ; « absent » si max support < 0,35 ; « incertain » sinon (dont les marques usées ou masquées).
Sortie : datation_gam.json (statistiques par secteur et par type) + datation_gam.geojson (statut par entité) +
planche planches/datation_gam_2022.jpg.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import carte_site as CS  # noqa: E402
import commun_pilote as C  # noqa: E402

DEMI = 1.2
SECTEURS = {  # secteurs (L93) : coeur = carré de 50 m autour du centre du carrefour, puis branches
    "coeur": lambda x, y: abs(x - 917280) <= 25 and abs(y - 6460285) <= 25,
    "verdun_ne": lambda x, y: (x - 917280) + (y - 6460285) > 35 and x > 917280,
    "verdun_sw": lambda x, y: (x - 917280) + (y - 6460285) < -35 and y < 6460285 and x < 917260,
    "vercors_s": lambda x, y: y < 6460260 and 917270 <= x <= 917330,
    "reviree_n": lambda x, y: y > 6460300 and x < 917280,
}


def secteur(x, y):
    for k, f in SECTEURS.items():
        if f(x, y):
            return k
    return "autre"


def points_entite(P, geo, shape):
    ferme = len(P) >= 4 and C.ferme(P)
    if ferme:
        x0, y0 = P.min(0)
        x1, y1 = P.max(0)
        # rastérisation sur la grille du site
        r0, c0 = C.l93_vers_px(x0, y1, geo)
        r1, c1 = C.l93_vers_px(x1, y0, geo)
        r0, c0 = int(math.floor(r0)) - 1, int(math.floor(c0)) - 1
        r1, c1 = int(math.ceil(r1)) + 2, int(math.ceil(c1)) + 2
        if r0 < 0 or c0 < 0 or r1 > shape[0] or c1 > shape[1]:
            return None, ferme
        sub_geo = (geo[0] + c0 * C.PX, geo[1] - r0 * C.PX)
        cov = C.rasteriser([[P]], sub_geo, (r1 - r0, c1 - c0), ss=2)
        rr, cc = np.nonzero(cov >= 0.5)
        if len(rr) < 4:
            # polygone très fin : on le traite comme une ligne
            ferme = False
        else:
            return (rr + r0, cc + c0), ferme
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]
    if s[-1] < 0.05:
        return None, ferme
    t = np.arange(0, s[-1] + 1e-9, 0.05)
    x = np.interp(t, s, P[:, 0])
    y = np.interp(t, s, P[:, 1])
    r, c = C.l93_vers_px(x, y, geo)
    r, c = np.round(r).astype(int), np.round(c).astype(int)
    ok = (r >= 0) & (c >= 0) & (r < shape[0]) & (c < shape[1])
    if ok.sum() < 2:
        return None, ferme
    return (r[ok], c[ok]), ferme


def supports(pm, rc, demi=DEMI):
    rr, cc = rc
    k = int(round(demi / C.PX))
    H, W = pm.shape
    best, arg = -1.0, (0, 0)
    s0 = None
    grid = np.zeros((2 * k + 1, 2 * k + 1), np.float32)
    for i, dr in enumerate(range(-k, k + 1)):
        r = np.clip(rr + dr, 0, H - 1)
        for j, dc in enumerate(range(-k, k + 1)):
            v = float(pm[r, np.clip(cc + dc, 0, W - 1)].mean())
            grid[i, j] = v
    s0 = float(grid[k, k])
    # égalités (ligne translatée le long d'elle-même) : on préfère le plus petit décalage (pénalité 0,02 / m)
    ii, jj = np.mgrid[-k:k + 1, -k:k + 1]
    pen = grid - 0.02 * np.hypot(ii, jj) * C.PX
    i, j = np.unravel_index(int(np.argmax(pen)), grid.shape)
    best = float(grid[i, j])
    # décalage (L93) : colonne +1 = x + 5 cm ; ligne +1 = y - 5 cm
    dx, dy = (j - k) * C.PX, -(i - k) * C.PX
    return s0, best, (dx, dy)


def statut(s0, best, sh):
    d = math.hypot(*sh)
    if s0 >= 0.6:
        return "present_identique"
    if best >= 0.6 and d >= 0.15 and best - s0 >= 0.25:
        return "deplace"
    if best < 0.35:
        return "absent"
    return "incertain"


def main():
    cache = Path(os.environ.get("PJ_CACHE_MARQUAGES", CS.CACHE))
    res = {}
    cartes = {}
    for mil in ("2022", "2024"):
        d = CS.charger(mil, cache)
        p = d["p_blanc"].astype(np.float32) / 255.0
        pj = d["p_jaune"].astype(np.float32) / 255.0
        p = np.maximum(p, pj)
        cartes[mil] = (C.max_filtre(p * 255, 3) / 255.0, tuple(d["geo"].tolist()))
    feats = []
    for props, P in C.gam_lignes():
        e = {"type_geom": props.get("type_geom"), "n_sommets": int(len(P)),
             "longueur_m": float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())}
        cx, cy = P.mean(0)
        e["secteur"] = secteur(cx, cy)
        for mil, (pm, geo) in cartes.items():
            rc, ferme = points_entite(P, geo, pm.shape)
            e["ferme"] = bool(ferme)
            if rc is None:
                e[mil] = None
                continue
            s0, best, sh = supports(pm, rc)
            e[mil] = {"support0": round(s0, 3), "support_max": round(best, 3), "decalage_m": [round(sh[0], 2), round(sh[1], 2)],
                      "statut": statut(s0, best, sh)}
        feats.append((e, P))
    # statistiques
    stats = {}
    for mil in ("2022", "2024"):
        for sect in list(SECTEURS) + ["autre", "tout"]:
            sel = [e for e, _ in feats if e.get(mil) and (sect == "tout" or e["secteur"] == sect)]
            if not sel:
                continue
            L = sum(e["longueur_m"] for e in sel)
            st = {}
            for k in ("present_identique", "deplace", "incertain", "absent"):
                ss = [e for e in sel if e[mil]["statut"] == k]
                st[k] = {"n": len(ss), "part_longueur": round(sum(e["longueur_m"] for e in ss) / max(L, 1e-9), 3)}
            stats.setdefault(mil, {})[sect] = {"n": len(sel), "longueur_m": round(L, 1), "statuts": st}
    # décalages des entités déplacées en 2022 (même décalage partout = recalage ; décalages variés = repeinte)
    dep = [e["2022"]["decalage_m"] for e, _ in feats if e.get("2022") and e["2022"]["statut"] == "deplace"]
    ident = [e["2022"]["decalage_m"] for e, _ in feats if e.get("2022") and e["2022"]["statut"] == "present_identique"]
    out = {"methode": __doc__.strip(), "n_entites": len(feats), "statistiques": stats,
           "decalages_deplaces_2022_m": dep,
           "decalage_optimal_median_identiques_2022_m": [float(np.median([d[0] for d in ident])) if ident else None,
                                                         float(np.median([d[1] for d in ident])) if ident else None],
           "sources": {"gam": str(C.GAM_LIN.relative_to(C.RACINE)), "ortho2022": str(C.PCRS.relative_to(C.RACINE)),
                       "bdortho2024": str(C.BDO24.relative_to(C.RACINE)), "recalage_2024": list(C.decalage_2024())}}
    C.ecrire_json(C.SORTIE / "datation_gam.json", out)
    gj = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2154"}},
          "features": [{"type": "Feature", "properties": e, "geometry": {"type": "LineString", "coordinates": np.round(P, 3).tolist()}}
                       for e, P in feats]}
    (C.SORTIE / "datation_gam.geojson").write_text(json.dumps(gj, ensure_ascii=False), encoding="utf-8")
    planche(feats)
    return out


def planche(feats):
    from PIL import Image, ImageDraw
    X0, Y0, X1, Y1 = 917150, 6460150, 917410, 6460420
    res = 0.10
    rgb, geo = C.mosaique_2022(X0, Y0, X1, Y1)
    W, H = int((X1 - X0) / res), int((Y1 - Y0) / res)
    im = Image.fromarray(rgb).resize((W, H), Image.BOX)
    im = Image.blend(im, Image.new("RGB", im.size, (0, 0, 0)), 0.35)
    d = ImageDraw.Draw(im)
    cols = {"present_identique": (0, 255, 0), "deplace": (255, 160, 0), "incertain": (255, 255, 0), "absent": (255, 0, 255)}
    for e, P in feats:
        if not e.get("2022"):
            continue
        d.line([((x - X0) / res, (Y1 - y) / res) for x, y in P], fill=cols[e["2022"]["statut"]], width=2)
    y = 10
    for k, c in cols.items():
        d.rectangle([10, y, 30, y + 14], fill=c)
        d.text((36, y), {"present_identique": "GAM = peinture 2022 (meme position)", "deplace": "GAM decale (> 15 cm) par rapport a 2022",
                         "incertain": "incertain (use, masque)", "absent": "absent de l'ortho 2022 (posterieur)"}[k], fill=(255, 255, 255))
        y += 20
    d.text((10, H - 20), "Leve GAM SOL_SIGNALISATION_HORIZONTALE sur ortho PCRS 5 cm du 10/05/2022 (fond assombri) - 1 px = 10 cm", fill=(255, 255, 255))
    (C.SORTIE / "planches").mkdir(exist_ok=True)
    im.save(C.SORTIE / "planches/datation_gam_2022.jpg", quality=90)


if __name__ == "__main__":
    o = main()
    print(json.dumps(o["statistiques"], ensure_ascii=False, indent=1)[:6000])
    print("decalage median identiques", o["decalage_optimal_median_identiques_2022_m"])
