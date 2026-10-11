"""Comptes, couverture photo et comparaison avec la description 2026 -> comparaison_2026.json (dossier objets/).

Usage : python -I comparaison.py
"""
from __future__ import annotations

import collections
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_at import O, RACINE, SORTIE, TELE, ecrire, lire, type_desc_2026  # noqa: E402

R2026 = RACINE / "recon/out/paquet_jardin/v2/description/resolue/objets"


def main():
    fa = lire(SORTIE / "objets_avant_travaux.geojson")["features"]
    fe = lire(SORTIE / "objets_exclus.geojson")["features"]
    st = lire(SORTIE / "inventaire_stats.json")
    P = [f["properties"] for f in fa]
    E = [f["properties"] for f in fe]

    def d0(p):
        return math.hypot(p["x_local"], p["y_local"])

    # ---- comptes par type
    comptes = {}
    for t in sorted({p["type"] for p in P}):
        L = [p for p in P if p["type"] == t]
        comptes[t] = {
            "n": len(L),
            "etat": collections.Counter(p["etat_avant_travaux"] for p in L),
            "confiance": collections.Counter(p.get("confiance") for p in L),
            "origine": collections.Counter(p["origine_position"] for p in L),
            "coeur_60m": sum(d0(p) <= 60 for p in L),
            "vus_2_photos_calees": sum(p["nb_photos_visibles"] >= 2 for p in L),
            "vus_2_photos_acceptees": sum(p["nb_photos_visibles_acceptees"] >= 2 for p in L),
            "vus_2_photos_toutes_poses": sum(p["nb_photos_visibles"] + p["nb_photos_visibles_a_priori"] >= 2 for p in L),
            "detectes_2_photos": sum(p["nb_photos_detecte"] >= 2 for p in L),
            "detectes_1_photo": sum(p["nb_photos_detecte"] >= 1 for p in L),
        }

    def couverture(L):
        n = len(L) or 1
        return {"n": len(L),
                "vus_2_photos_calees_pct": round(100 * sum(p["nb_photos_visibles"] >= 2 for p in L) / n, 1),
                "vus_2_photos_acceptees_pct": round(100 * sum(p["nb_photos_visibles_acceptees"] >= 2 for p in L) / n, 1),
                "vus_2_photos_toutes_poses_pct": round(100 * sum(p["nb_photos_visibles"] + p["nb_photos_visibles_a_priori"] >= 2 for p in L) / n, 1),
                "detectes_2_photos_pct": round(100 * sum(p["nb_photos_detecte"] >= 2 for p in L) / n, 1),
                "detectes_1_photo_pct": round(100 * sum(p["nb_photos_detecte"] >= 1 for p in L) / n, 1)}

    nonarb = [p for p in P if p["type"] not in ("arbre", "barriere")]
    cov = {"tous": couverture(P), "hors_arbres_et_clotures": couverture(nonarb),
           "coeur_60m": couverture([p for p in P if d0(p) <= 60]),
           "coeur_60m_hors_arbres_et_clotures": couverture([p for p in nonarb if d0(p) <= 60]),
           "zone_travaux_3m": couverture([p for p in P if p.get("d_zone_travaux_m") is not None and p["d_zone_travaux_m"] <= 3])}

    # ---- comparaison avec la description 2026
    d26 = {}
    for nom in ("mobilier.geojson", "arbres.geojson"):
        for f in lire(R2026 / nom)["features"]:
            p = f["properties"]
            d26[p["id"]] = p
    par_lien = collections.defaultdict(list)
    for p in P + E:
        if p.get("lien_2026"):
            par_lien[p["lien_2026"]].append(p)
        for fz in p.get("fusionnes") or []:
            if fz in d26:
                par_lien[fz].append(p)
    comp = collections.defaultdict(list)
    for oid, p26 in d26.items():
        L = par_lien.get(oid)
        if p26.get("type") in ("feuillu", "conifere", "arbuste") or oid.startswith(("arbre", "ENR-ARB")):
            t = "arbre"
        else:
            t = type_desc_2026(p26)[0]
        if not L:
            comp["hors_emprise_ou_non_traite"].append(oid)
            continue
        q = L[0]
        e = q["etat_avant_travaux"]
        if e in ("present", "present_presume"):
            if (q.get("ecart_position_2026_m") or 0) >= 5:
                comp["deplace_par_travaux"].append({"id": oid, "type": t, "d_m": q["ecart_position_2026_m"], "source": q.get("position_source")})
            elif (q.get("ecart_position_2026_m") or 0) >= 0.3:
                comp["position_avant_differente"].append({"id": oid, "type": t, "d_m": q["ecart_position_2026_m"], "source": q.get("position_source")})
            else:
                comp["conserve"].append({"id": oid, "type": t})
        elif e == "incertain":
            comp["incertain_avant"].append({"id": oid, "type": t, "raison": q.get("raison")})
        elif e in ("absent_avant_travaux",):
            comp["ajoute_par_travaux_ou_apres"].append({"id": oid, "type": t, "statut_2026": p26.get("statut_2026"), "raison": q.get("raison")})
        elif e == "disparu_avant_travaux":
            comp["disparu_avant_travaux_mais_dans_2026"].append({"id": oid, "type": t, "statut_2026": p26.get("statut_2026"), "raison": q.get("raison")})
        else:
            comp["autre_" + e].append({"id": oid, "type": t})
    # objets avant travaux absents de la description 2026
    for p in P:
        if p.get("lien_2026"):
            continue
        dz = p.get("d_zone_travaux_m")
        cat = "absent_2026_dans_emprise_travaux" if (dz is not None and dz <= 3) else "absent_de_la_description_2026"
        comp[cat].append({"id": p["id"], "type": p["type"], "sous_type": p.get("sous_type"), "code": p.get("code"),
                          "etat": p["etat_avant_travaux"], "confiance": p.get("confiance"), "d_zone_travaux_m": dz,
                          "l93": [round(p["x_local"] + O[0], 2), round(p["y_local"] + O[1], 2)]})
    # 2026 -> abattus / supprimés
    comp_comptes = {k: (len(v) if isinstance(v, list) else v) for k, v in comp.items()}
    comp_types = {k: collections.Counter(x["type"] if isinstance(x, dict) else "?" for x in v) for k, v in comp.items()
                  if k != "hors_emprise_ou_non_traite"}

    out = {"schema": "pj_objets_avant_travaux_comparaison/0.1", "n_avant_travaux": len(P), "n_exclus": len(E),
           "exclus_par_etat": collections.Counter(p["etat_avant_travaux"] for p in E),
           "exclus_par_type_etat": collections.Counter(f"{p['type']}|{p['etat_avant_travaux']}" for p in E),
           "comptes_par_type": comptes, "couverture_photo": cov,
           "cameras_2023_2025": st.get("cameras_fenetre"),
           "comparaison_2026_comptes": comp_comptes, "comparaison_2026_types": comp_types,
           "comparaison_2026": {k: v for k, v in comp.items() if k != "hors_emprise_ou_non_traite"},
           "osm": {"reference": st["osm"]["reference"], "disparus_avant_reference": st["osm"]["disparus_avant_reference"],
                   "supprimes_apres_reference": st["osm"]["supprimes_apres_reference"],
                   "deplacements": st.get("deplacements_osm")},
           "mapillary": st["mapillary"], "panoramax_annotations": st["panoramax_annotations"]}
    ecrire(SORTIE / "comparaison_2026.json", out)
    print("couverture", cov)
    print("comparaison", comp_comptes)
    for k, v in comp_types.items():
        print(" ", k, dict(v))


if __name__ == "__main__":
    main()
