"""Pilote mesuré « marquages vectoriels exacts de l'état avant travaux » sur deux zones de l'ortho PCRS 5 cm 2022.

Zone A (vercors_fleches)  : branche Vercors, approche nord vers le carrefour, 917280-917320 x 6460225-6460261,5 :
                            4 flèches (2 TAG, 2 tridents), tirets T3, ligne continue courbe.
Zone B (coeur_zebras)     : cœur du carrefour, 917253-917307 x 6460261,5-6460312 : passages piétons,
                            files de pavés jaunes (Chronovélo 2022), carrés blancs de traversée cyclable, flèches.

Chaîne (aucune dépendance au réseau OpenDRIVE 2026) : detection (fond 30e percentile, seuil adaptatif) ->
zebras (bandes sous-pixel, pas régulier) -> fleches (gabarits IISR, Nelder-Mead sur IoU) -> lignes (tirets,
lignes courbes, files, modulation) -> damiers (pavés jaunes par périodicité, carrés blancs) -> comparaisons
(GAM là où il coïncide avec 2022, BD ORTHO 2024 recalée, v1) -> GeoJSON + JSON + planches.

Usage : python -I pilote.py   (PJ_CACHE_MARQUAGES : dossier de cache des cartes du site, hors dépôt)
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun_pilote as C  # noqa: E402
import comparer as CP  # noqa: E402
import damiers as DM  # noqa: E402
import detection as D  # noqa: E402
import fleches as F  # noqa: E402
import lignes as LG  # noqa: E402
import zebras as Z  # noqa: E402

ZONES = {
    "A_vercors_fleches": (917280.0, 6460225.0, 917320.0, 6460261.5),
    "B_coeur_zebras": (917253.0, 6460261.5, 917307.0, 6460312.0),
}
SEUIL_FLECHE = 0.60
V1 = C.RACINE / "recon/out/paquet_jardin/package/donnees/marquages/marquages_2026.geojson"


def local(x, y):
    return [round(x - C.O[0], 3), round(y - C.O[1], 3)]


def r3(v):
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, dict):
        return {k: r3(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [r3(x) for x in v]
    if isinstance(v, (np.floating,)):
        return round(float(v), 4)
    if isinstance(v, (np.integer,)):
        return int(v)
    return v


def dans_polys(pt, polys):
    from comparer import iou_polygones  # noqa: F401
    x, y = pt
    for poly in polys:
        R = np.asarray(poly[0])
        inside = False
        j = len(R) - 1
        for i in range(len(R)):
            if ((R[i, 1] > y) != (R[j, 1] > y)) and (x < (R[j, 0] - R[i, 0]) * (y - R[i, 1]) / (R[j, 1] - R[i, 1] + 1e-12) + R[i, 0]):
                inside = not inside
            j = i
        if inside:
            return True
    return False


def traiter_zone(nom, emprise):
    t0 = time.time()
    X0, Y0, X1, Y1 = emprise
    m = 2.0
    rgb, geo = C.mosaique_2022(X0 - m, Y0 - m, X1 + m, Y1 + m)
    det = D.detecter(rgb, geo)

    def dans_zone(x, y):
        return X0 <= x <= X1 and Y0 <= y <= Y1

    feats, res = [], {"emprise_l93": emprise, "composantes": len(det["comps"])}
    # ------------------------------------------------------------- passages piétons
    passages = []
    for g in Z.regrouper(D.germes_zebra(det)):
        for p in Z.mesurer_passage(g, det, geo):
            c = np.mean([b["v_centre"] for b in p["bandes"]])
            cx = p["centre_ref"][0] + np.mean([b["u_centre"] for b in p["bandes"]]) * p["eu"][0] + c * p["ev"][0]
            cy = p["centre_ref"][1] + np.mean([b["u_centre"] for b in p["bandes"]]) * p["eu"][1] + c * p["ev"][1]
            if dans_zone(cx, cy):
                p["centre_l93"] = [float(cx), float(cy)]
                passages.append(p)
    passages.sort(key=lambda p: (-p["centre_l93"][1], p["centre_l93"][0]))
    bandes_polys, zeb_out = [], []
    for k, p in enumerate(passages):
        pid = f"{nom[0]}-PP{k + 1:02d}"
        p["id"] = pid
        reg = Z.polygones_passage(p, regularise=True, largeur=0.50)
        brut = Z.polygones_passage(p, regularise=False)
        for q in reg:
            bandes_polys.append({"passage": pid, "indice": q["indice"], "anneau": q["anneau"], "regularise": True})
            yaw = math.degrees(p["theta_rad"])
            L = p["ligne_fin"][0] * (p["c0_m"] + p["pas_m"] * q["indice"]) + p["ligne_fin"][1] - (p["ligne_debut"][0] * (p["c0_m"] + p["pas_m"] * q["indice"]) + p["ligne_debut"][1])
            feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [np.round(np.vstack([q["anneau"], q["anneau"][:1]]), 3).tolist()]},
                          "properties": {"id": f"{pid}-B{q['indice']:02d}", "famille": "passage_pieton", "gabarit": "BANDE_PASSAGE_PIETON",
                                         "passage": pid, "indice": q["indice"], "largeur_m": 0.50, "longueur_m": round(float(L), 3),
                                         "pose_locale": {"centre": local(*q["centre"]), "yaw_trigo_deg": round(yaw % 360, 3)},
                                         "src": "ortho2022", "date_preuve": "2022-05-10", "regularise": True,
                                         "largeur_mesuree_m": round(p["largeur_mediane_m"], 3), "pas_m": round(p["pas_m"], 3)}})
        for q in brut:
            bandes_polys.append({"passage": pid, "indice": q["indice"], "anneau": q["anneau"], "regularise": False})
        zeb_out.append({k2: v for k2, v in p.items() if k2 != "bandes"} | {"bandes": [{kk: b[kk] for kk in ("indice", "largeur_m", "longueur_m", "rms_bords_m", "residu_pas_m", "angle_bande_rel_deg", "contraste_DN")} for b in p["bandes"]]})
    res["passages"] = zeb_out
    # ------------------------------------------------------------- flèches
    fl_out, fl_polys = [], []
    for d in F.candidats(det):
        if not dans_zone(d["cx"], d["cy"]):
            continue
        a = F.ajuster(d, det, geo)
        a["accepte"] = a["iou_norme"] >= SEUIL_FLECHE
        if a["accepte"]:
            fid = f"{nom[0]}-FL{len(fl_polys) + 1:02d}"
            a["id"] = fid
            polys = F.polygones(a)
            fl_polys.append({"id": fid, "type": a["type"], "polys": polys, "polys_libre": F.polygones(a, libre=True), "cap_rad": a["pose_norme"][2]})
            for poly in polys:
                feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [np.round(np.vstack([poly[0], poly[0][:1]]), 3).tolist()]},
                              "properties": {"id": fid, "famille": "fleche", "gabarit": a["type"], "iisr": a["type"] != "TRIDENT",
                                             "pose_locale": {"origine": local(*a["origine_l93"]), "yaw_trigo_deg": round(a["cap_trigo_deg"], 3)},
                                             "azimut_deg": round(a["azimut_deg"], 2), "iou_norme": round(a["iou_norme"], 3),
                                             "echelle_libre": [round(x, 3) for x in a["echelle_libre"]], "marge_type": round(a["marge_type"], 3),
                                             "src": "ortho2022", "date_preuve": "2022-05-10"}})
        fl_out.append(a)
    res["fleches"] = fl_out
    # ------------------------------------------------------------- lignes
    exclus = [b for b in bandes_polys if b["regularise"]]
    ex_polys = [[np.asarray(b["anneau"])] for b in exclus] + [p for f in fl_polys for p in f["polys"]]
    lignes = []
    for d in det["comps"]:
        if not dans_zone(d["cx"], d["cy"]):
            continue
        if d["classe"] == "trait":
            mm = LG.mesurer_trait(d, det, geo)
        elif d["classe"] == "ligne_courbe":
            mm = LG.mesurer_ligne_courbe(d, det, geo)
            if mm and not (mm["bruit_local_m"] <= 0.03 and mm["dissymetrie_fond_DN"] <= 20 and 0.08 <= mm["largeur_m"] <= 0.35):
                mm = None
        else:
            continue
        if mm is None or dans_polys(mm["milieu"], ex_polys):
            continue
        lignes.append(mm)
    files_ = LG.regrouper(lignes)
    lig_out = []
    for k, fl_ in enumerate(sorted(files_, key=lambda g: -sum(x["longueur_m"] for x in g))):
        mo = LG.modulation(fl_)
        lid = f"{nom[0]}-LG{k + 1:02d}"
        for x in fl_:
            x["file"] = lid
            feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": np.round(np.asarray(x["axe_l93"]), 3).tolist()},
                          "properties": {"id": f"{lid}-C{x['composante']}", "famille": "ligne", "file": lid,
                                         "largeur_mesuree_m": round(x["largeur_m"], 3), "longueur_m": round(x["longueur_m"], 3),
                                         "modulation": mo["modulation_proche"] if mo else ("continue" if x["longueur_m"] > 6 else "isole"),
                                         "rms_axe_m": round(x["rms_axe_m"], 4), "src": "ortho2022", "date_preuve": "2022-05-10"}})
        lig_out.append({"file": lid, "n": len(fl_), "longueur_totale_m": sum(x["longueur_m"] for x in fl_), "modulation": mo,
                        "largeurs_m": [x["largeur_m"] for x in fl_], "rms_axe_m": [x["rms_axe_m"] for x in fl_],
                        "bruit_local_m": [x.get("bruit_local_m") for x in fl_ if x.get("courbe")]})
    res["lignes"] = lig_out
    # ------------------------------------------------------------- damiers
    jaunes = [f for f in DM.files_jaunes_periodiques(det, geo) if f["autocorrelation_pic"] >= 0.5 and dans_zone(*f["centre"])]
    for k, f in enumerate(jaunes):
        jid = f"{nom[0]}-PJ{k + 1:02d}"
        f["id"] = jid
        for c in f["centres"]:
            th = f["axe_rad"]
            eu = np.array([math.cos(th), math.sin(th)])
            ev = np.array([-math.sin(th), math.cos(th)])
            Lp, Wp = f["plein_m"], f["largeur_bande_m"] or 0.5
            Q = [np.array(c) + su * Lp / 2 * eu + sv * Wp / 2 * ev for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [np.round(np.vstack([Q, Q[:1]]), 3).tolist()]},
                          "properties": {"id": jid, "famille": "damier", "gabarit": "PAVE_JAUNE_2022 (mesure ; PAVE_CHRONOVELO 0,70 x 0,37 en 2025)",
                                         "pose_locale": {"centre": local(*c), "yaw_trigo_deg": round(math.degrees(th + math.pi / 2) % 360, 3)},
                                         "dimensions_mesurees_m": [round(Wp, 3), round(Lp, 3)], "pas_m": round(f["pas_m"], 3),
                                         "src": "ortho2022", "date_preuve": "2022-05-10"}})
    res["paves_jaunes"] = [{k: v for k, v in f.items() if k not in ("centres", "angles_rad")} for f in jaunes]
    carres = [f for f in DM.files(DM.paves(det, ("carre_050",))) if dans_zone(*f["centre"])]
    res["carres_blancs"] = [{k: v for k, v in f.items() if k not in ("centres", "angles_rad")} for f in carres]
    for k, f in enumerate(carres):
        for poly in DM.polygones_file(f, 0.5, 0.5):
            Q = poly[0]
            feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [np.round(np.vstack([Q, Q[:1]]), 3).tolist()]},
                          "properties": {"id": f"{nom[0]}-CB{k + 1:02d}", "famille": "damier", "gabarit": "CARRE_TRAVERSEE_CYCLABLE",
                                         "pas_m": round(f["pas_m"], 3), "src": "ortho2022", "date_preuve": "2022-05-10"}})
    # ------------------------------------------------------------- comparaisons
    rects = CP.gam_rectangles(X0 - 2, Y0 - 2, X1 + 2, Y1 + 2)
    cz = CP.comparer_zebras(bandes_polys, rects)
    gfl = CP.gam_fleches(X0 - 2, Y0 - 2, X1 + 2, Y1 + 2)
    cf = CP.comparer_fleches(fl_polys, gfl) + CP.comparer_fleches_segments(fl_polys)
    cl = CP.comparer_lignes(lignes, X0, Y0, X1, Y1)
    res["comparaison_gam"] = {"rectangles_gam_zone": len(rects), "fleches_gam_zone": len(gfl), "bandes": cz, "fleches": cf, "lignes": cl}
    # 2024
    p24 = []
    for p in passages:
        polys = [[np.asarray(q["anneau"])] for q in Z.polygones_passage(p, regularise=True, largeur=0.5)]
        p24.append({"passage": p["id"]} | CP.persistance_2024(polys))
    for f in fl_polys:
        p24.append({"fleche": f["id"]} | CP.persistance_2024(f["polys"]))
    res["persistance_2024"] = p24
    # v1 (paquet 2026 : bandes de passage issues de l'ortho 2022)
    try:
        v1 = json.loads(V1.read_text(encoding="utf-8"))["features"]
        v1b = []
        for f in v1:
            pr = f["properties"]
            if pr.get("type") not in ("passage_pieton_bande", "fantome") or not f.get("geometry"):
                continue
            g = f["geometry"]
            ring = np.asarray(g["coordinates"][0] if g["type"] == "Polygon" else g["coordinates"][0][0])[:, :2]
            if C.ferme(ring):
                ring = ring[:-1]          # sommet de fermeture : sinon le barycentre des sommets est biaisé
            c = ring.mean(0)
            if X0 <= c[0] <= X1 and Y0 <= c[1] <= Y1:
                v1b.append((pr, ring))
        cv1 = []
        for b in bandes_polys:
            if not b["regularise"]:
                continue
            cb = np.asarray(b["anneau"]).mean(0)
            best = min(v1b, key=lambda t: np.linalg.norm(t[1].mean(0) - cb), default=None)
            if best is not None and np.linalg.norm(best[1].mean(0) - cb) < 0.6:
                cv1.append({"passage": b["passage"], "indice": b["indice"], "ecart_centre_m": float(np.linalg.norm(best[1].mean(0) - cb)),
                            "n_sommets_v1": int(len(best[1])), "source_v1": best[0].get("source"), "etat_v1": best[0].get("etat"), "type_v1": best[0].get("type"),
                            "iou_v1": CP.iou_polygones([[np.asarray(b["anneau"])]], [[best[1]]])})
        res["comparaison_v1"] = {"bandes_v1_zone": len(v1b), "appariees": cv1}
    except Exception as e:  # pragma: no cover
        res["comparaison_v1"] = {"erreur": str(e)}
    res["duree_s"] = time.time() - t0
    return res, feats, (rgb, geo, det, passages, fl_polys, lignes, jaunes, carres, bandes_polys)


def stats(v):
    v = np.asarray([x for x in v if x is not None], float)
    if not len(v):
        return None
    a = np.abs(v)
    return {"n": int(len(v)), "moyenne": float(v.mean()), "mediane_abs": float(np.median(a)), "p90_abs": float(np.percentile(a, 90)), "max_abs": float(a.max())}


def synthese(res):
    s = {}
    for nom, r in res.items():
        z = {}
        P = r["passages"]
        z["passages"] = {"n": len(P), "n_bandes": int(sum(p["n_bandes"] for p in P)),
                         "largeur_bande_m": stats([b["largeur_m"] for p in P for b in p["bandes"]]),
                         "pas_m": stats([p["pas_m"] for p in P]),
                         "longueur_bande_m": stats([p["longueur_mediane_m"] for p in P]),
                         "rms_bords_m": stats([b["rms_bords_m"] for p in P for b in p["bandes"]]),
                         "residu_pas_m": stats([b["residu_pas_m"] for p in P for b in p["bandes"]])}
        A = [a for a in r["fleches"] if a["accepte"]]
        z["fleches"] = {"candidats": len(r["fleches"]), "acceptees": len(A), "types": {t: sum(1 for a in A if a["type"] == t) for t in sorted({a["type"] for a in A})},
                        "iou_norme": stats([a["iou_norme"] for a in A]), "marge_type": stats([a["marge_type"] for a in A]),
                        "echelle_libre_x": stats([a["echelle_libre"][0] for a in A]), "echelle_libre_y": stats([a["echelle_libre"][1] for a in A]),
                        "rejetees_iou_max": max([a["iou_norme"] for a in r["fleches"] if not a["accepte"]], default=None)}
        Lg = r["lignes"]
        z["lignes"] = {"files": len(Lg), "longueur_totale_m": float(sum(x["longueur_totale_m"] for x in Lg)),
                       "largeur_m": stats([w for x in Lg for w in x["largeurs_m"]]), "rms_axe_m": stats([w for x in Lg for w in x["rms_axe_m"]]),
                       "modulations": [x["modulation"] and {k: x["modulation"][k] for k in ("n_traits", "trait_median_m", "vide_median_m", "modulation_proche")} for x in Lg]}
        cg = r["comparaison_gam"]
        bz = [b for b in cg["bandes"] if b["regularise"]]
        z["gam_bandes"] = {"appariees": len(bz), "ecart_centre_m": stats([b["ecart_centre_m"] for b in bz]),
                           "ecart_travers_m": stats([b["ecart_travers_m"] for b in bz]), "ecart_long_bande_m": stats([b["ecart_long_bande_m"] for b in bz]),
                           "ecart_angle_deg": stats([b["ecart_angle_deg"] for b in bz]), "iou": stats([b["iou"] for b in bz]),
                           "largeur_gam_m": stats([b["largeur_gam_m"] for b in bz]), "longueur_gam_moins_ortho_m": stats([b["longueur_gam_m"] - b["longueur_ortho_m"] for b in bz])}
        par_passage = {}
        for b in bz:
            par_passage.setdefault(b["passage"], []).append(b)
        z["gam_par_passage"] = {k: {"bandes_appariees": len(v), "ecart_centre_median_m": float(np.median([b["ecart_centre_m"] for b in v])),
                                    "ecart_travers_median_m": float(np.median([b["ecart_travers_m"] for b in v])),
                                    "ecart_long_bande_median_m": float(np.median([b["ecart_long_bande_m"] for b in v])),
                                    "ecart_angle_median_deg": float(np.median([b["ecart_angle_deg"] for b in v])),
                                    "iou_median": float(np.median([b["iou"] for b in v]))} for k, v in sorted(par_passage.items())}
        coinc = [b for k, v in par_passage.items() if np.median([x["ecart_centre_m"] for x in v]) < 0.20 for b in v]
        z["gam_bandes_passages_coincidents"] = {"definition": "passages dont l'écart médian des centres de bandes GAM / ortho 2022 est < 0,20 m (non repeints ni déplacés)",
                                                "passages": sorted({b["passage"] for b in coinc}), "bandes": len(coinc),
                                                "ecart_centre_m": stats([b["ecart_centre_m"] for b in coinc]),
                                                "ecart_travers_m": stats([b["ecart_travers_m"] for b in coinc]),
                                                "ecart_long_bande_m": stats([b["ecart_long_bande_m"] for b in coinc]),
                                                "ecart_angle_deg": stats([b["ecart_angle_deg"] for b in coinc]),
                                                "iou": stats([b["iou"] for b in coinc]),
                                                "longueur_gam_moins_ortho_m": stats([b["longueur_gam_m"] - b["longueur_ortho_m"] for b in coinc])}
        z["gam_fleches"] = cg["fleches"]
        z["gam_lignes"] = {"n": len(cg["lignes"]), "ecart_median_m": stats([x["ecart_median_m"] for x in cg["lignes"]])}
        z["persistance_2024"] = r["persistance_2024"]
        v1 = r.get("comparaison_v1", {}).get("appariees", [])
        z["v1"] = {"appariees": len(v1), "ecart_centre_m": stats([x["ecart_centre_m"] for x in v1]), "iou": stats([x["iou_v1"] for x in v1]),
                   "n_sommets_v1": stats([x["n_sommets_v1"] for x in v1])}
        z["paves_jaunes"] = {"files": len(r["paves_jaunes"]), "paves": int(sum(f["n_paves"] for f in r["paves_jaunes"])),
                             "pas_m": stats([f["pas_m"] for f in r["paves_jaunes"]]), "plein_m": stats([f["plein_m"] for f in r["paves_jaunes"]]),
                             "largeur_bande_m": stats([f["largeur_bande_m"] for f in r["paves_jaunes"]])}
        z["duree_s"] = r["duree_s"]
        s[nom] = z
    return s


def main():
    import planches as PL
    res, feats = {}, []
    for nom, emp in ZONES.items():
        r, f, ctx = traiter_zone(nom, emp)
        res[nom] = r
        feats += f
        PL.planches_zone(nom, emp, ctx, r)
    syn = synthese(res)
    out = {"schema": "pj_marquages_pilote/0.1", "date": "2026-10-11", "source_image": "ortho PCRS 5 cm Grenoble-Alpes Métropole du 10/05/2022 (data/sites/paquet_jardin/ortho5cm_2022)",
           "methode": __doc__.strip(), "synthese": r3(syn), "zones": r3(res)}
    C.ecrire_json(C.SORTIE / "pilote_resultats.json", out)
    gj = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2154"}},
          "repere_local": "local = L93 - (917279.43, 6460289.98) ; UE : X = x*100, Y = -y*100, yaw_UE = -yaw_trigo", "features": feats}
    (C.SORTIE / "marquages_pilote_2022.geojson").write_text(json.dumps(gj, ensure_ascii=False, default=C._conv), encoding="utf-8")
    return out


if __name__ == "__main__":
    o = main()
    print(json.dumps(o["synthese"], ensure_ascii=False, indent=1, default=C._conv)[:12000])
