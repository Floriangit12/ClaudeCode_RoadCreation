"""Famille `surfaces` de la description v2 : polygones de la zone pilote, classe, revêtement
(materiau_id de recon/pcg/schema/materiaux_description.json), niveau tiré du MNT 2026 et bords
(bordures attenantes, côté arrière = surface derrière la bordure, côté avant = devant la face vue).

Source : surfaces_2026.geojson du paquet v1 (lecture seule), découpé par la zone pilote. Les
limites d'origine raster sont signalées (`limite_raster`) pour recalage sur l'arête arrière des
bordures à la fabrication. Les bâtiments sont exclus (ce ne sont pas des sols).
"""
import collections

import numpy as np

import contexte as ctx
from commun import (abscisses, aire_signee, arrondi, couper_polygone, dans_polygone, distance_segments,
                    echantillons_interieurs, geom_polygones, normale_gauche, point_a, repere)

PAS_NIVEAU = 0.5
NOUE_DZ, NOUE_AIRE = -0.30, 50.0   # massif 2025 en creux sous le fil d'eau voisin et assez grand : noue
# correspondance (classe, matériau v1, état v1) -> materiau_id ; None = toutes valeurs
CORRESPONDANCE = [
    (("trottoir", "enrobe", None), "enrobe_trottoir"),
    (("trottoir", "beton", None), "beton_balaye"),
    (("trottoir", "paves", None), "paves_beton"),
    (("trottoir", "stabilise", None), "stabilise_beige"),
    (("chaussee", "enrobe", "modifie_2025"), "enrobe_bbsg_neuf_2025"),
    (("chaussee", "enrobe", None), "enrobe_bbsg_ancien"),
    (("piste_cyclable", "enrobe", None), "enrobe_piste_cyclable"),
    (("parking", "enrobe", "modifie_2025"), "enrobe_bbsg_neuf_2025"),
    (("parking", "enrobe", None), "enrobe_bbsg_ancien"),
    (("acces_riverain", "enrobe", "modifie_2025"), "enrobe_bbsg_neuf_2025"),
    (("acces_riverain", "enrobe", None), "enrobe_bbsg_ancien"),
    (("ilot", "beton", None), "beton_balaye"),
    (("ilot", "enrobe", None), "enrobe_trottoir"),
    (("quai_bus", "beton", None), "beton_balaye"),
    ((None, "massif_plante", "modifie_2025"), "brf_bois_concasse"),
    ((None, "massif_plante", None), "terre_nue"),
    ((None, "herbe", None), "gazon_tondu"),
    ((None, "terre", None), "terre_nue"),
    ((None, "stabilise", None), "stabilise_beige"),
    ((None, "beton", None), "beton_balaye"),
    ((None, "paves", None), "paves_beton"),
    ((None, "enrobe", None), "enrobe_bbsg_ancien"),
]
APPAREILLAGE = {
    "paves_beton": {"appareillage": "panneresse", "module_cm": [20, 10], "joint_mm": 5},
    "beton_balaye": {"appareillage": "dalle_coulee", "joints_scies_m": 3.5},
    "brf_bois_concasse": {"appareillage": "vrac", "granulometrie_mm": [20, 50], "epaisseur_m": 0.08},
}
AGE = {"inchange_2022": ("ancien", 0.5), "construit_2023_2024": ("recent", 0.3), "modifie_2025": ("neuf_2025", 0.15)}

# Constats qui corrigent la classe ou le revêtement v1 (id v1 -> correction)
CORRECTIONS = {
    "surf_0121": {"materiau_id": "herbe_haute", "constat": "p2025_05_360-32",
                  "note": "accotement enherbé non tondu de l'approche NE, l'herbe déborde sur la bordure"},
    "surf_0344": {"classe": "chaussee", "sous_classe": "terre_plein_peint", "materiau_id": "enrobe_bbsg_ancien",
                  "constat": "p2025_05_360-06",
                  "note": "au-delà du nez du TPC NE : terre-plein PEINT (deux lignes) ; aucune bordure GAM 2026 ; v1 le donnait en îlot surélevé de 0,16 m",
                  "arasement": "le MNT 2026 garde ici le relief LiDAR 2021 d'un ancien prolongement du TPC (+0,16 m) ; la photo du 18/05/2025 montre un terre-plein peint à niveau : araser au niveau de la chaussée adjacente",
                  "preuve_niveau": "panoramax:9834f494/r01_c01"},
}


def materiau_v1(p):
    for (cl, mat, et), mid in CORRESPONDANCE:
        if (cl is None or cl == p["classe"]) and mat == p["materiau"] and (et is None or et == p["etat"]):
            return mid
    return None


def src_limites(source):
    s = source.split(";")[0]
    if "gam" in s:
        return "gam", "moyenne"
    if "plan_projet" in s:
        return "plan2025", "moyenne"
    if "raster" in s:
        return "ortho2022", "faible"
    if "osm" in s or "bdtopo" in s:
        return "osm", "faible"
    return "a_priori:limite_imposee_v1", "faible"


def niveau(poly, mnt):
    Q = echantillons_interieurs(poly, PAS_NIVEAU)
    z = mnt(*(repere(Q, "l93").T))
    out = {"ref": "mnt_2026", "z_med_ngf": float(np.median(z)), "z_min_ngf": float(z.min()),
           "z_max_ngf": float(z.max()), "devers_pct": None, "devers_azimut_deg": None}
    if len(Q) >= 6:
        A = np.c_[Q - Q.mean(axis=0), np.ones(len(Q))]
        (gx, gy, _), *_ = np.linalg.lstsq(A, z, rcond=None)
        out["devers_pct"] = float(np.hypot(gx, gy) * 100)
        out["devers_azimut_deg"] = float(np.degrees(np.arctan2(-gx, -gy)) % 360)   # sens de la descente
    return out, z


def bords(poly, bordures_loc):
    """Bordures attenantes : sondes à 0,40 m derrière (gauche) et 0,30 m devant (droite) la ligne."""
    out = []
    x0, y0 = poly[0].min(axis=0) - 1.0
    x1, y1 = poly[0].max(axis=0) + 1.0
    for kid, P in bordures_loc:
        if P[:, 0].max() < x0 or P[:, 0].min() > x1 or P[:, 1].max() < y0 or P[:, 1].min() > y1:
            continue
        L = abscisses(P)[-1]
        s = np.arange(0.25, L, 0.5) if L > 0.5 else np.array([L / 2])
        q, tg = point_a(P, s)
        n = normale_gauche(tg)
        arr = dans_polygone(q + n * 0.40, poly)
        avt = dans_polygone(q - n * 0.30, poly)
        for cote, m in (("arriere", arr), ("avant", avt)):
            lg = float(m.sum() * (L / len(s)))
            if lg >= 0.75:
                out.append({"bordure": kid, "cote": cote, "longueur_m": lg})
    return sorted(out, key=lambda b: (b["bordure"], b["cote"]))


def z_alentour(poly, mnt, largeur=1.5):
    """Altitude médiane du MNT dans une bande extérieure de `largeur` m autour du polygone."""
    a = poly[0]
    x0, y0 = a.min(axis=0) - largeur
    x1, y1 = a.max(axis=0) + largeur
    X, Y = np.meshgrid(np.arange(x0, x1, 0.25), np.arange(y0, y1, 0.25))
    Q = np.c_[X.ravel(), Y.ravel()]
    Q = Q[~dans_polygone(Q, poly)]
    d, _, _ = distance_segments(Q, a, np.roll(a, -1, axis=0))
    Q = Q[d <= largeur]
    return float(np.median(mnt(*(repere(Q, "l93").T)))) if len(Q) else None


def completer_bords(feats, bordures_feats):
    """(Re)calcule bords, dz_bordure_m et dz_fil_eau_m (après ajout des bordures de raccord)."""
    bl = [(f["properties"]["id"], repere(np.asarray(f["geometry"]["coordinates"])[:, :2])) for f in bordures_feats]
    vues = {f["properties"]["id"]: f["properties"]["intervalles"] for f in bordures_feats}
    fil = {f["properties"]["id"]: float(np.median([c[2] for c in f["geometry"]["coordinates"]])) for f in bordures_feats}
    for f in feats:
        p = f["properties"]
        g = f["geometry"]
        rings = g["coordinates"] if g["type"] == "Polygon" else g["coordinates"][0]
        poly = [repere(np.asarray(r, dtype=float)[:-1, :2]) for r in rings]
        bd = bords(poly, bl)
        arr = [b["bordure"] for b in bd if b["cote"] == "arriere"]
        vues_arr = [it["vue_m"] for k in arr for it in vues[k] if it["role"] == "courant"]
        p["bords"] = arrondi(bd)
        p["niveau"]["dz_bordure_m"] = arrondi(float(np.median(vues_arr))) if vues_arr else None
        tous = [b["bordure"] for b in bd]
        p["niveau"]["dz_fil_eau_m"] = (arrondi(p["niveau"]["z_med_ngf"] - float(np.median([fil[k] for k in tous])))
                                       if tous else None)


def construire(mnt, bordures_feats):
    zone = ctx.zone_pilote()["anneau"]
    fil = {f["properties"]["id"]: float(np.median([c[2] for c in f["geometry"]["coordinates"]])) for f in bordures_feats}
    bl = [(f["properties"]["id"], repere(np.asarray(f["geometry"]["coordinates"])[:, :2])) for f in bordures_feats]
    feats, rapport = [], collections.Counter()
    for sid, p, polys in ctx.surfaces_v1():
        if p["classe"] == "batiment":
            continue
        morceaux = []
        for poly in polys:
            morceaux += couper_polygone(poly, zone)
        morceaux = [m for m in morceaux if _aire(m) >= 0.05]
        if not morceaux:
            continue
        morceaux.sort(key=lambda m: (-_aire(m), round(float(m[0][:, 0].min()), 3)))
        corr = CORRECTIONS.get(sid, {})
        for k, poly in enumerate(morceaux):
            nid = f"S-{sid[5:]}" + ("" if len(morceaux) == 1 else "abcdefghijklmnopqrstuvwxyz"[k])
            classe = corr.get("classe", p["classe"])
            mid = corr.get("materiau_id") or materiau_v1(p)
            age, sal = AGE.get(p["etat"], ("inconnu", 0.4))
            niv, _ = niveau(poly, mnt)
            src_l, conf_l = src_limites(p["source"])
            prov = {
                "geometrie": {"src": src_l, "ref": f"{sid} ({p['source'][:90]})", "conf": conf_l},
                "classe": {"src": f"constat:{corr['constat']}" if "classe" in corr else src_classe(p["source"]),
                           "ref": corr.get("note", p["source"].split(";")[-1].strip())[:160],
                           "conf": "moyenne"},
                "revetement": ({"src": f"constat:{corr['constat']}", "ref": corr["note"][:160], "conf": "moyenne"}
                               if "materiau_id" in corr else
                               {"src": "a_priori:correspondance_materiau_v1",
                                "ref": f"v1 {p['classe']}/{p['materiau']}/{p['etat']} -> {mid}", "conf": "faible"}),
                "niveau": {"src": "a_priori:mnt_2026", "ref": "heightmap_3025_10cm (sol octobre 2026)", "conf": "moyenne"},
            }
            if corr.get("arasement"):
                z_ext = z_alentour(poly, mnt)
                niv["arasement"] = {"dz_mnt_m": niv["z_med_ngf"] - z_ext, "z_mnt_ngf": niv["z_med_ngf"],
                                    "motif": corr["arasement"]}
                niv["ref"], niv["z_med_ngf"] = "chaussee_adjacente", z_ext
                prov["niveau"] = {"src": corr["preuve_niveau"], "ref": corr["arasement"][:160], "conf": "moyenne"}
            if mid == "brf_bois_concasse" and "materiau_id" not in corr:
                voisins = [fil[b["bordure"]] for b in bords(poly, bl)]
                dzf = niv["z_med_ngf"] - float(np.median(voisins)) if voisins else 0.0
                if dzf < NOUE_DZ and _aire(poly) >= NOUE_AIRE:
                    mid = "noue_plantee"
                    prov["revetement"] = {"src": "a_priori:massif_2025_en_creux_noue",
                                          "ref": f"massif planté 2025 à {dzf:+.2f} m du fil d'eau voisin : noue (constat hist-16 : noue SE de 152 m²)",
                                          "conf": "faible"}
                else:
                    prov["revetement"] = {"src": "a_priori:massif_2025_paillage_bois",
                                          "ref": "massif planté en 2025 : paillage bois (BRF) usuel des plantations neuves (photo de référence utilisateur 2)",
                                          "conf": "faible"}
            rev = {"materiau_id": mid, "age": age, "salissure": sal}
            rev.update(APPAREILLAGE.get(mid, {}))
            props = {
                "id": nid, "famille": "surfaces", "classe": classe, "sous_classe": corr.get("sous_classe"),
                "revetement": rev, "niveau": niv, "bords": [], "ilots": [],
                "limite_raster": "raster" in p["source"].split(";")[0],
                "aire_m2": _aire(poly), "lien_v1": sid, "etat_v1": p["etat"], "prov": prov,
            }
            feats.append({"type": "Feature", "geometry": geom_polygones([[repere(r, "l93") for r in poly]]),
                          "properties": arrondi(props)})
            rapport[classe] += 1
    completer_bords(feats, bordures_feats)
    return feats, dict(rapport)


def src_classe(source):
    s = source.split(";")[-1]
    if "plan_projet" in s:
        return "plan2025"
    if "gam" in s:
        return "gam"
    if "osm" in s:
        return "osm"
    if "ortho" in s:
        return "ortho2022"
    return "lidar2021"


def _aire(poly):
    return abs(aire_signee(poly[0])) - sum(abs(aire_signee(t)) for t in poly[1:])
