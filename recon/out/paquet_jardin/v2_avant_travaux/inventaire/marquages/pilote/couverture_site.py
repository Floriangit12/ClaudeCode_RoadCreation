"""Estimation du taux de couverture sur tout le site (300 m x 300 m) : extraction automatique sur l'ortho PCRS
5 cm 2022 par blocs de 100 m (marges de 8 m, éléments gardés si leur centre est dans le cœur du bloc), puis :

1. masque des surfaces circulées (paquet v1 surfaces_2026 : chaussee, parking, piste_cyclable, acces_riverain,
   quai_bus ; état inchange_2022 / modifie_2025 / construit_2023_2024), rastérisé à 25 cm ;
2. lisibilité de l'ortho 2022 sur ce masque (25 cm) : houppier (indice de vert), ombre ou objet sombre (fond local
   < 80 DN), véhicule ou objet clair (tache claire compacte > 4 m2, ou saturation > 0,30 hors peinture jaune),
   dégagé ;
3. inventaire de référence : marques v1 (996) dont l'état est antérieur aux travaux (conserve, fantome,
   refait_2025_identique) : part visible sur l'ortho 2022 (support de peinture >= 0,4 dans le polygone v1) et part
   reprise par l'extraction automatique (>= 50 % de la surface du polygone v1 couverte par les produits de même
   famille, polygones dilatés de 0,20 m, axes épaissis à 0,60 m) ;
4. produits : marquages_site_2022_auto.geojson (non revu), couverture_site.json, planches/couverture_site.jpg.
Usage : python -I couverture_site.py [--sans-extraction]   (PJ_CACHE_MARQUAGES : cache des cartes, hors dépôt ;
--sans-extraction : relit marquages_site_2022_auto.geojson au lieu de refaire l'extraction, environ 15 min)
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import carte_site as CS  # noqa: E402
import commun_pilote as C  # noqa: E402
import damiers as DM  # noqa: E402
import detection as D  # noqa: E402
import fleches as F  # noqa: E402
import lignes as LG  # noqa: E402
import zebras as Z  # noqa: E402

EMPRISE = CS.EMPRISE
SURF = C.RACINE / "recon/out/paquet_jardin/package/donnees/surfaces/surfaces_2026.geojson"
V1 = C.RACINE / "recon/out/paquet_jardin/package/donnees/marquages/marquages_2026.geojson"
CIRCULEES = ("chaussee", "parking", "piste_cyclable", "acces_riverain", "quai_bus")
R25 = 0.25


def anneaux(g):
    if g["type"] == "Polygon":
        return [[np.asarray(r)[:, :2] for r in g["coordinates"]]]
    if g["type"] == "MultiPolygon":
        return [[np.asarray(r)[:, :2] for r in p] for p in g["coordinates"]]
    return []


def masque_circule():
    X0, Y0, X1, Y1 = EMPRISE
    geo = (X0, Y1)
    shape = (int((Y1 - Y0) / R25), int((X1 - X0) / R25))
    etats = {}
    for f in json.loads(SURF.read_text(encoding="utf-8"))["features"]:
        pr = f["properties"]
        if pr.get("classe") not in CIRCULEES or not f.get("geometry"):
            continue
        etats.setdefault(pr.get("etat"), []).extend(anneaux(f["geometry"]))
    out = {}
    for e, polys in etats.items():
        out[e] = C.rasteriser(polys, geo, shape, res=R25, ss=2) >= 0.5
    return out, geo, shape


def lisibilite(geo, shape):
    """Classes de lisibilité à 25 cm sur tout le site (ortho 2022)."""
    X0, Y0, X1, Y1 = EMPRISE
    rgb, g5 = C.mosaique_2022(X0, Y0, X1, Y1)
    H, W = shape
    small = np.asarray(Image.fromarray(rgb).resize((W, H), Image.BOX), np.float32)
    R, G, B = small[..., 0], small[..., 1], small[..., 2]
    L = 0.299 * R + 0.587 * G + 0.114 * B
    mx, mn = small.max(-1), small.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1)
    vert = G - (R + B) / 2
    cache = Path(os.environ.get("PJ_CACHE_MARQUAGES", CS.CACHE))
    cs = CS.charger("2022", cache)
    fond = np.asarray(Image.fromarray(cs["fond"]).resize((W, H), Image.BOX), np.float32)
    pj = np.asarray(Image.fromarray(cs["p_jaune"]).resize((W, H), Image.BOX), np.float32) / 255
    pb5 = cs["p_blanc"] >= 128
    # taches claires compactes > 4 m2 (toits de véhicules clairs)
    lab, n = C.etiqueter(np.asarray(Image.fromarray((pb5 * 255).astype(np.uint8)).resize((W, H), Image.BOX)) > 127)
    cnt = np.bincount(lab.ravel(), minlength=n + 1)
    grand = cnt * R25 * R25 > 4.0
    grand[0] = False
    clair = grand[lab]
    canopee = (vert > 10) & (sat > 0.15)
    # les ombres portées sont bleutées (saturation > 0,3) : la saturation ne signale un véhicule qu'au soleil
    vehicule = (clair | ((sat > 0.30) & (L > 100) & (fond >= 80) & (pj < 0.3))) & ~canopee
    sombre = ((fond < 80) | (L < 60)) & ~canopee & ~vehicule
    classe = np.zeros(shape, np.uint8)            # 0 dégagé
    classe[sombre] = 1                            # ombre / objet sombre
    classe[vehicule] = 2                          # véhicule / objet clair ou coloré
    classe[canopee] = 3                           # houppier
    return classe, small.astype(np.uint8)


def extraire_bloc(bx0, by0, bx1, by1, masque_fn, marge=8.0):
    rgb, geo = C.mosaique_2022(bx0 - marge, by0 - marge, bx1 + marge, by1 + marge)
    det = D.detecter(rgb, geo)

    def coeur(x, y):
        return bx0 <= x < bx1 and by0 <= y < by1
    feats = []
    nb = {"passages": 0, "bandes": 0, "fleches": 0, "fleches_candidates": 0, "lignes": 0, "longueur_lignes_m": 0.0, "files_paves": 0, "paves": 0}
    zpolys = []
    for g in Z.regrouper(D.germes_zebra(det)):
        try:
            ps = Z.mesurer_passage(g, det, geo)
        except (ValueError, IndexError, np.linalg.LinAlgError):
            nb["erreurs_mesure"] = nb.get("erreurs_mesure", 0) + 1
            continue
        for p in ps:
            c = np.mean([[p["centre_ref"][0] + b["u_centre"] * p["eu"][0] + b["v_centre"] * p["ev"][0],
                          p["centre_ref"][1] + b["u_centre"] * p["eu"][1] + b["v_centre"] * p["ev"][1]] for b in p["bandes"]], axis=0)
            if not coeur(*c):
                continue
            nb["passages"] += 1
            for q in Z.polygones_passage(p, regularise=True, largeur=0.5):
                nb["bandes"] += 1
                zpolys.append([np.asarray(q["anneau"])])
                feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [np.round(np.vstack([q["anneau"], q["anneau"][:1]]), 3).tolist()]},
                              "properties": {"famille": "passage_pieton", "gabarit": "BANDE_PASSAGE_PIETON", "pas_m": round(p["pas_m"], 3),
                                             "largeur_mesuree_m": round(p["largeur_mediane_m"], 3), "n_bandes": p["n_bandes"], "src": "ortho2022_auto"}})
    fpolys = []
    for d in F.candidats(det):
        if not coeur(d["cx"], d["cy"]) or not masque_fn(d["cx"], d["cy"]):
            continue
        nb["fleches_candidates"] += 1
        a = F.ajuster(d, det, geo)
        if a["iou_norme"] < 0.60:
            continue
        nb["fleches"] += 1
        polys = F.polygones(a)
        fpolys += polys
        for poly in polys:
            feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [np.round(np.vstack([poly[0], poly[0][:1]]), 3).tolist()]},
                          "properties": {"famille": "fleche", "gabarit": a["type"], "iou_norme": round(a["iou_norme"], 3),
                                         "marge_type": round(a["marge_type"], 3), "ambigu": a["marge_type"] < 0.05,
                                         "origine_l93": [round(v, 3) for v in a["origine_l93"]], "yaw_trigo_deg": round(a["cap_trigo_deg"], 2),
                                         "src": "ortho2022_auto"}})
    from pilote import dans_polys
    for d in det["comps"]:
        if not coeur(d["cx"], d["cy"]):
            continue
        try:
            if d["classe"] == "trait":
                m = LG.mesurer_trait(d, det, geo)
            elif d["classe"] == "ligne_courbe":
                m = LG.mesurer_ligne_courbe(d, det, geo)
                if m and not (m["bruit_local_m"] <= 0.03 and m["dissymetrie_fond_DN"] <= 20 and 0.08 <= m["largeur_m"] <= 0.35):
                    m = None
            else:
                continue
        except (ValueError, IndexError, np.linalg.LinAlgError):
            nb["erreurs_mesure"] = nb.get("erreurs_mesure", 0) + 1
            continue
        if m is None or not masque_fn(*m["milieu"]) or dans_polys(m["milieu"], zpolys + fpolys):
            continue
        nb["lignes"] += 1
        nb["longueur_lignes_m"] += m["longueur_m"]
        feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": np.round(np.asarray(m["axe_l93"]), 3).tolist()},
                      "properties": {"famille": "ligne", "largeur_mesuree_m": round(m["largeur_m"], 3), "longueur_m": round(m["longueur_m"], 3),
                                     "rms_axe_m": round(m["rms_axe_m"], 4), "src": "ortho2022_auto"}})
    for f in DM.files_jaunes_periodiques(det, geo):
        if f["autocorrelation_pic"] < 0.5 or not coeur(*f["centre"]) or not masque_fn(*f["centre"]):
            continue
        nb["files_paves"] += 1
        nb["paves"] += f["n_paves"]
        th = f["axe_rad"]
        eu = np.array([math.cos(th), math.sin(th)])
        ev = np.array([-math.sin(th), math.cos(th)])
        for c in f["centres"]:
            Q = [np.array(c) + su * f["plein_m"] / 2 * eu + sv * (f["largeur_bande_m"] or 0.5) / 2 * ev for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [np.round(np.vstack([Q, Q[:1]]), 3).tolist()]},
                          "properties": {"famille": "damier", "gabarit": "PAVE_JAUNE_2022", "pas_m": round(f["pas_m"], 3), "src": "ortho2022_auto"}})
    return feats, nb


def reference_v1(feats, res=0.10):
    """Marques v1 antérieures aux travaux (conserve, fantome, refait_2025_identique) : support de peinture 2022
    dans le polygone (visible si >= 0,4) et part de leur surface couverte par l'extraction automatique de même
    famille (polygones dilatés de 0,20 m, axes de lignes épaissis à 0,60 m) ; reprise si >= 50 %."""
    X0, Y0, X1, Y1 = EMPRISE
    W, H = int((X1 - X0) / res), int((Y1 - Y0) / res)
    cache = Path(os.environ.get("PJ_CACHE_MARQUAGES", CS.CACHE))
    cs = CS.charger("2022", cache)
    pm = np.maximum(cs["p_blanc"], cs["p_jaune"]).astype(np.float32) / 255
    pm = C.max_filtre(pm * 255, 3) / 255
    g5 = tuple(cs["geo"].tolist())
    cartes = {}
    for fam in ("passage_pieton", "fleche", "ligne", "damier"):
        im = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(im)
        for f in feats:
            if f["properties"]["famille"] != fam:
                continue
            g = f["geometry"]
            P = np.asarray(g["coordinates"][0] if g["type"] == "Polygon" else g["coordinates"])
            pts = list(zip(((P[:, 0] - X0) / res).tolist(), ((Y1 - P[:, 1]) / res).tolist()))
            if g["type"] == "Polygon":
                d.polygon(pts, fill=255)
                d.line(pts, fill=255, width=4)
            else:
                d.line(pts, fill=255, width=6)
        cartes[fam] = np.asarray(im) > 0
    corresp = {"passage_pieton_bande": "passage_pieton", "fleche": "fleche", "ligne_discontinue": "ligne",
               "ligne_continue": "ligne", "ligne_effet_feux": "ligne", "damier": "damier"}
    ref = {}
    for f in json.loads(V1.read_text(encoding="utf-8"))["features"]:
        pr = f["properties"]
        if pr.get("etat") not in ("conserve", "fantome", "refait_2025_identique") or not f.get("geometry"):
            continue
        polys = anneaux(f["geometry"])
        if not polys:
            continue
        P = polys[0][0]
        if C.ferme(P):
            P = P[:-1]
        c = P.mean(0)
        if not (X0 <= c[0] <= X1 and Y0 <= c[1] <= Y1):
            continue
        typ = pr.get("type")
        fam = corresp.get(typ)
        if typ == "fantome":
            src = (pr.get("source") or "").lower()
            if "zèbre" in src or "zebre" in src or "passage" in src:
                fam = "passage_pieton"
            elif "pav" in src or "damier" in src:
                fam = "damier"
            elif "flèche" in src or "fleche" in src:
                fam = "fleche"
            else:
                fam = "ligne"
        xmin, ymin = P.min(0) - 0.1
        xmax, ymax = P.max(0) + 0.1
        r0, c0 = C.l93_vers_px(xmin, ymax, g5)
        r0, c0 = int(math.floor(r0)), int(math.floor(c0))
        sub = (g5[0] + c0 * C.PX, g5[1] - r0 * C.PX)
        hh, ww = int((ymax - ymin) / C.PX) + 2, int((xmax - xmin) / C.PX) + 2
        cov = C.rasteriser([polys[0]], sub, (hh, ww), ss=2) >= 0.5
        rr, cc = np.nonzero(cov)
        if not len(rr):
            continue
        rr5, cc5 = rr + r0, cc + c0
        ok = (rr5 >= 0) & (cc5 >= 0) & (rr5 < pm.shape[0]) & (cc5 < pm.shape[1])
        sup = float(pm[rr5[ok], cc5[ok]].mean()) if ok.any() else 0.0
        part = None
        if fam in cartes:
            x, y = C.px_vers_l93(rr5, cc5, g5)
            r1 = ((Y1 - y) / res).astype(int)
            c1 = ((x - X0) / res).astype(int)
            ok1 = (r1 >= 0) & (c1 >= 0) & (r1 < H) & (c1 < W)
            part = float(cartes[fam][r1[ok1], c1[ok1]].mean()) if ok1.any() else 0.0
        ref.setdefault(typ, []).append({"support": sup, "part": part, "fam": fam})
    stats_ref = {}
    for typ, L in sorted(ref.items()):
        n = len(L)
        vis = [x for x in L if x["support"] >= 0.4]
        av = [x for x in L if x["part"] is not None]
        rep = [x for x in av if x["part"] >= 0.5]
        stats_ref[typ] = {"n": n, "visibles_ortho2022": len(vis), "part_visible": round(len(vis) / n, 3),
                          "repris_auto": len(rep) if av else None,
                          "part_reprise_auto": round(len(rep) / n, 3) if av else None,
                          "part_reprise_parmi_visibles": round(sum(1 for x in vis if x["part"] is not None and x["part"] >= 0.5) / max(len(vis), 1), 3) if av else None,
                          "support_median": round(float(np.median([x["support"] for x in L])), 3)}
    return stats_ref


def main(sans_extraction=False):
    t0 = time.time()
    masques, geo25, shape = masque_circule()
    tout = np.zeros(shape, bool)
    for m in masques.values():
        tout |= m

    def masque_fn(x, y):
        r, c = C.l93_vers_px(x, y, geo25, R25)
        r, c = int(round(float(r))), int(round(float(c)))
        if not (0 <= r < shape[0] and 0 <= c < shape[1]):
            return False
        return bool(tout[max(0, r - 4):r + 5, max(0, c - 4):c + 5].any())          # tolérance 1 m
    classe, small = lisibilite(geo25, shape)
    # 1. lisibilité par état de zone
    stats_l = {}
    a_px = R25 * R25
    for e, m in list(masques.items()) + [("tout", tout)]:
        tot = float(m.sum() * a_px)
        stats_l[e] = {"surface_m2": round(tot, 1)} | {k: round(float(((classe == i) & m).sum() * a_px) / max(tot, 1e-9), 4)
                                                       for i, k in enumerate(("degage", "ombre_ou_sombre", "vehicule_ou_objet", "houppier"))}
    # 2. extraction automatique par blocs
    feats, nbt = [], {}
    X0, Y0, X1, Y1 = EMPRISE
    if sans_extraction:
        prec = json.loads((C.SORTIE / "couverture_site.json").read_text(encoding="utf-8"))
        nbt = prec.get("extraction_auto", {})
        feats = json.loads((C.SORTIE / "marquages_site_2022_auto.geojson").read_text(encoding="utf-8"))["features"]
    for bx in (np.arange(X0, X1, 100.0) if not sans_extraction else []):
        for by in np.arange(Y0, Y1, 100.0):
            f, nb = extraire_bloc(bx, by, min(bx + 100, X1), min(by + 100, Y1), masque_fn)
            feats += f
            for k, v in nb.items():
                nbt[k] = nbt.get(k, 0) + v
    if not sans_extraction:
        gj = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2154"}},
              "remarque": "extraction automatique NON REVUE (ortho PCRS 5 cm du 10/05/2022) ; à valider zone par zone avant fabrication",
              "features": feats}
        (C.SORTIE / "marquages_site_2022_auto.geojson").write_text(json.dumps(gj, ensure_ascii=False, default=C._conv), encoding="utf-8")
    # 3. inventaire de référence v1
    stats_ref = reference_v1(feats)
    out = {"methode": __doc__.strip(), "emprise_l93": EMPRISE, "lisibilite_25cm": stats_l, "extraction_auto": nbt,
           "reference_v1_avant_travaux": stats_ref, "duree_s": round(time.time() - t0, 1),
           "sources": {"surfaces": str(SURF.relative_to(C.RACINE)), "v1": str(V1.relative_to(C.RACINE)), "ortho": str(C.PCRS.relative_to(C.RACINE))}}
    C.ecrire_json(C.SORTIE / "couverture_site.json", out)
    planche(classe, small, tout, masques, feats)
    return out


def planche(classe, small, tout, masques, feats):
    X0, Y0, X1, Y1 = EMPRISE
    im = Image.fromarray(small).convert("RGB")
    a = np.asarray(im).astype(np.float32) * 0.45
    cols = {0: (0, 200, 0), 1: (60, 60, 255), 2: (255, 60, 60), 3: (0, 120, 0)}
    for i, c in cols.items():
        m = (classe == i) & tout
        a[m] = a[m] * 0.4 + np.array(c) * 0.6
    if "construit_2023_2024" in masques:
        m = masques["construit_2023_2024"]
        a[m] = a[m] * 0.5 + np.array((255, 200, 0)) * 0.5
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for f in feats:
        g = f["geometry"]
        P = np.asarray(g["coordinates"][0] if g["type"] == "Polygon" else g["coordinates"])
        pts = list(zip(((P[:, 0] - X0) / R25).tolist(), ((Y1 - P[:, 1]) / R25).tolist()))
        d.line(pts, fill=(255, 255, 255) if f["properties"]["famille"] != "fleche" else (255, 0, 255), width=1)
    y = 6
    for c, t in (((0, 200, 0), "surface circulee, ortho 2022 degagee"), ((60, 60, 255), "ombre / objet sombre"), ((255, 60, 60), "vehicule / objet clair ou colore"),
                 ((0, 120, 0), "houppier"), ((255, 200, 0), "construit 2023-2024 (absent de l'ortho 2022)"), ((255, 255, 255), "extraction auto (bandes, lignes, paves)"), ((255, 0, 255), "fleches ajustees")):
        d.rectangle([6, y, 20, y + 10], fill=c)
        d.text((26, y - 1), t, fill=(255, 255, 255))
        y += 14
    d.text((6, im.size[1] - 14), "Couverture de l'ortho PCRS 5 cm (10/05/2022) sur les surfaces circulees - 1 px = 25 cm", fill=(255, 255, 255))
    im.save(C.SORTIE / "planches/couverture_site.jpg", quality=90)


if __name__ == "__main__":
    o = main(sans_extraction="--sans-extraction" in sys.argv)
    print(json.dumps({k: v for k, v in o.items() if k != "methode"}, ensure_ascii=False, indent=1, default=C._conv))
