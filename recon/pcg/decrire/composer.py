"""Composition de la description v2 de la zone pilote, puis validation.

Usage :
    python recon/pcg/decrire/composer.py [--sortie DOSSIER] [--png PLANCHE.png] [--sans-validation]
Sorties (défaut recon/out/paquet_jardin/v2/description) :
    base/bordures.geojson, base/surfaces.geojson, base/ilots.geojson, base/ponctuels_sol.geojson
        FeatureCollection Lambert-93 / NGF, une entité par ligne, triées par id
    description_scene_v2.json
        manifeste : site, origine O, date d'état, saison, références (sha256), zone pilote,
        couches (sha256), comptes, statistiques, index des preuves, règles a priori, hash global
Déterministe : aucune date d'exécution, flottants arrondis au mm, identifiants stables ; deux
exécutions sur les mêmes entrées donnent des fichiers identiques à l'octet.
"""
import argparse
import collections
import hashlib
import platform
import sys
from pathlib import Path

import numpy as np

import bordures
import contexte as ctx
import ilots
import marquages
import surfaces
from commun import (DONNEES, MATERIAUX, MNT, RACINE, SCHEMA, SCHEMA_ID, SORTIE, SPECS, VECTEURS, ZONE,
                    arrondi, ecrire_geojson, ecrire_json, lire_geojson, rel, repere, sha256)

ICI = Path(__file__).resolve().parent
REFERENCES = {
    "bordures_hauteurs": (DONNEES / "relief/bordures_hauteurs.geojson", "tronçons de bordure de 1 m (h_vue, statut, fil d'eau 2021)"),
    "relief_zones": (DONNEES / "relief/relief_zones_2026.geojson", "traversées abaissées, chaussée 2026"),
    "mnt_2026": (DONNEES / "relief/heightmap_3025_10cm.png", "sol nu octobre 2026, 10 cm (Z de toute la description)"),
    "mnt_2026_echelle": (DONNEES / "relief/heightmap_3025_10cm.json", "décodage de la heightmap"),
    "surfaces_v1": (DONNEES / "surfaces/surfaces_2026.geojson", "polygones de surface v1"),
    "marquages_v1": (DONNEES / "marquages/marquages_2026.geojson", "bandes de passages piétons"),
    "mobilier_v1": (DONNEES / "objets/mobilier.geojson", "objets portés par les îlots"),
    "arbres_v1": (DONNEES / "objets/arbres.geojson", "plantations des îlots"),
    "gam_bordure_pct": (VECTEURS / "etat_2026/bordure_pct_L93.geojson", "blocs CHARTIERE du levé GAM"),
    "osm_crossings": (VECTEURS / "vector/osm_crossings.geojson", "tactile_paving des traversées"),
    "panoramax_index": (VECTEURS / "panoramax_pictures.geojson", "photos Panoramax du site"),
    "constats": (ctx.CONSTATS_JSON, "constats vérifiés (deux vérificateurs)"),
    "spec_bordures": (SPECS / "bordures.json", "profils NF, regles_affectation, abaissés"),
    "spec_mobilier": (SPECS / "mobilier.json", "BEV (bev_podotactile)"),
    "spec_peinture": (SPECS / "peinture.json", "aspect des marquages (non utilisé en 0.1)"),
    "manifeste_cc0": (RACINE / "assets/manifeste_cc0.json", "librairie de matériaux CC0"),
    "materiaux_description": (MATERIAUX, "identifiants de matériaux de la description"),
    "schema": (SCHEMA, "schéma description_scene_v2/0.1"),
    "zone_pilote": (ZONE, "emprise de la zone pilote"),
}
SCRIPTS = ["commun.py", "contexte.py", "bordures.py", "surfaces.py", "ilots.py", "composer.py", "valider.py", "apercu.py"]
REFERENCES.update(marquages.REFERENCES)                 # famille marquages (schéma 0.2, site complet)
SCRIPTS += marquages.SCRIPTS + ["marquages_controles.py"]
REGLES_PCG = [
    {"id": "R-joints-herbe", "cible": {"famille": "bordures", "attribut": "aspect.herbe_joints"},
     "action": "dispersion_joints", "densite_par_joint": "aspect.herbe_joints", "asset": "herbe_joint_*"},
    {"id": "R-joints-mousse", "cible": {"famille": "bordures", "attribut": "aspect.mousse_joints"},
     "action": "decal_joints", "intensite": "aspect.mousse_joints"},
    {"id": "R-debordement-ilots", "cible": {"famille": "ilots", "attribut": "remplissage.debordement"},
     "action": "dispersion_bord_chaussee", "largeur_m": "remplissage.debordement.largeur_m",
     "densite": "remplissage.debordement.densite", "asset": "copeaux_* | gravillons_*"},
    {"id": "R-feuilles-automne", "cible": {"famille": "surfaces"}, "action": "feuilles_mortes",
     "densite": "site.saison.feuilles_mortes_sol", "exclusion": "chaussee hors fil d'eau"},
    {"id": "R-visibilite-traversees", "type": "exclusion", "zone": "2 m autour des abaissés de type traversee",
     "h_max_m": 0.6},
]


def parcourir_prov(obj, ou, sortie):
    """Collecte (src, conf, attribut, entité) dans tous les dictionnaires prov / prov_entree."""
    if isinstance(obj, dict):
        if "src" in obj and "conf" in obj and isinstance(obj["src"], str):
            sortie.append((obj["src"], ou[0], ou[1], obj.get("ref", "")))
        for k, v in obj.items():
            parcourir_prov(v, (ou[0], k if k not in ("prov",) else ou[1]), sortie)
    elif isinstance(obj, list):
        for v in obj:
            parcourir_prov(v, ou, sortie)


def preuves_et_apriori(couches):
    trouve = []
    for fam, feats in couches.items():
        for f in feats:
            p = f["properties"]
            for attr, pr in p.get("prov", {}).items():
                trouve.append((pr["src"], p["id"], attr, pr.get("ref", "")))
            for a in p.get("abaisses", []):
                if a.get("bev"):
                    pr = a["bev"]["prov"]
                    trouve.append((pr["src"], a["id"], "bev", pr.get("ref", "")))
    pnx = {f["properties"]["id"][:8]: f["properties"] for f in lire_geojson(VECTEURS / "panoramax_pictures.geojson")}
    preuves = {}
    for src, ent, attr, ref in trouve:
        if src.startswith("constat:"):
            cid = src.split(":", 1)[1]
            c = ctx.constat(cid)
            preuves[src] = {"type": "constat", "ref": cid, "date": c.get("date_source"),
                            "texte": c["texte"][:300], "fichier": rel(ctx.CONSTATS_JSON)}
        elif src.startswith("panoramax:"):
            pid, tuile = src.split(":", 1)[1].split("/")
            ph = pnx.get(pid, {})
            nom = f"{ph.get('datetime', '')[:10]}_{ph.get('id', pid)}_hd"
            preuves[src] = {"type": "panoramax", "ref": f"{ph.get('id', pid)} {tuile}", "date": ph.get("datetime", "")[:10] or None,
                            "texte": f"licence {ph.get('license')}, producteur {ph.get('producer')}, azimut {ph.get('azimuth')}",
                            "fichier": f"data/raw/panoramax/paquet_jardin/tiles/{nom}/{nom}_{tuile}.jpg"}
        elif src.startswith("osm"):
            preuves[src] = {"type": "osm", "ref": src.split(":", 1)[-1], "date": None, "texte": ref[:200],
                            "fichier": rel(VECTEURS / "vector/osm_crossings.geojson")}
        elif src.startswith("norme:"):
            preuves[src] = {"type": "norme", "ref": src.split(":", 1)[1], "date": None, "texte": ref[:200], "fichier": None}
        elif src == "photo_utilisateur":
            preuves[src] = {"type": "photo_utilisateur", "ref": "photos de référence de l'utilisateur (bordures béton en éléments, BRF, gravier)",
                            "date": "2026-10", "texte": "références de rendu, pas des observations du site", "fichier": None}
    groupes = collections.defaultdict(set)
    for src, ent, attr, ref in trouve:
        if src.startswith("a_priori:") or src == "photo_utilisateur":
            groupes[(src, attr)].add(ent)
    a_priori = [{"src": s, "attribut": a, "entites": sorted(e)} for (s, a), e in sorted(groupes.items())]
    return dict(sorted(preuves.items())), a_priori


def statistiques(K, S, I, B, rk):
    lp, lm = collections.Counter(), collections.Counter()
    ab, ecarts = [], []
    for f in K:
        p = f["properties"]
        for it in p["intervalles"]:
            lp[it["profil"]] += it["s1"] - it["s0"]
        lm[p["materiau"]] += p["longueur_m"]
        if p["source"].get("ecart_fil_eau_2021_mnt_m") is not None:
            ecarts.append(p["source"]["ecart_fil_eau_2021_mnt_m"])
        for a in p["abaisses"]:
            ab.append({"id": a["id"], "bordure": p["id"], "type": a["type"], "s0": a["s0"], "s1": a["s1"],
                       "longueur_m": a["s1"] - a["s0"], "vue_m": a["vue_m"], "profil": a["profil"],
                       "chartieres": len(a["raccords"]), "bev": bool(a["bev"] and a["bev"]["present"]),
                       "sources": a["sources"]})
    sm = collections.Counter()
    for f in S:
        sm[f["properties"]["revetement"]["materiau_id"]] += f["properties"]["aire_m2"]
    rem = [{"ilot": f["properties"]["id"], "type": f["properties"]["type"],
            "materiau_id": f["properties"]["remplissage"]["materiau_id"], "aire_m2": f["properties"]["aire_m2"],
            "retrait_sous_bordure_m": f["properties"]["remplissage"]["retrait_sous_bordure_m"],
            "ceinture": f["properties"]["ceinture"], "src": f["properties"]["prov"]["remplissage"]["src"],
            "conf": f["properties"]["prov"]["remplissage"]["conf"]} for f in I]
    return arrondi({
        "longueur_bordures_m": sum(f["properties"]["longueur_m"] for f in K),
        "longueur_par_profil_m": dict(sorted(lp.items())),
        "longueur_par_materiau_m": dict(sorted(lm.items())),
        "abaisses": ab,
        "remplissages_ilots": rem,
        "surfaces_par_materiau_m2": dict(sorted(sm.items())),
        "bev_m": sum(f["properties"]["longueur_m"] for f in B),
        "dedoublonnage": {"decisions_par_critere": rk["appariement"], "orientation_par_critere": rk["orientation"],
                          "lignes_sources_supprimees": sorted({d for f in K for d in f["properties"]["source"]["doublons_supprimes"]})},
        "ecart_fil_eau_2021_mnt_m": {"mediane": float(np.median(ecarts)) if ecarts else None,
                                     "p90": float(np.percentile(ecarts, 90)) if ecarts else None, "n_bordures": len(ecarts)},
    })


def composer(sortie, png=None):
    sortie = Path(sortie)
    mnt = MNT()
    K, bev_cand, rk = bordures.construire(mnt)
    S, rs = surfaces.construire(mnt, K)
    I, R, ri = ilots.construire(mnt, K, S)
    K = K + R
    surfaces.completer_bords(S, K)
    exclusions = [[repere(np.asarray(r, dtype=float)[:-1, :2]) for r in poly]
                  for f in I for poly in ([f["geometry"]["coordinates"]] if f["geometry"]["type"] == "Polygon"
                                          else f["geometry"]["coordinates"])]
    B = bordures.bev(bev_cand, mnt, exclusions)
    entete = lambda fam: {"schema": SCHEMA_ID, "famille": fam, "zone_pilote": ctx.zone_pilote()["props"]["id"],
                          "repere": "EPSG:2154 + NGF-IGN69 ; local = L93 - (917279.43, 6460289.98, 216.30)"}
    couches = {"bordures": K, "surfaces": S, "ilots": I, "ponctuels_sol": B}
    info = {}
    for fam, feats in couches.items():
        f = sortie / "base" / f"{fam}.geojson"
        ecrire_geojson(f, feats, fam, entete(fam))
        info[fam] = {"fichier": f"base/{fam}.geojson", "n": len(feats), "sha256": sha256(f)}
    # famille marquages (site complet) : marquages.geojson + table de correspondance des 996 marquages v1
    feats_m, corr_m, rap_m = marquages.construire()
    for fam, f in zip(("marquages", "marquages_correspondance"), marquages.ecrire(sortie / "base", feats_m, corr_m)):
        info[fam] = {"fichier": f"base/{f.name}", "n": len(feats_m if fam == "marquages" else corr_m), "sha256": sha256(f)}
    preuves, a_priori = preuves_et_apriori(dict(couches, marquages=feats_m))
    zp = ctx.zone_pilote()["props"]
    x0, y0, x1, y1 = ctx.zone_pilote()["emprise"]
    from pyproj import Transformer
    t84 = Transformer.from_crs(4326, 2154, always_xy=True)
    pnx = [t84.transform(f["properties"]["lon"], f["properties"]["lat"])
           for f in lire_geojson(VECTEURS / "panoramax_pictures.geojson")]
    n_pnx = int(sum(1 for x, y in repere(np.array(pnx)) if x0 <= x <= x1 and y0 <= y <= y1))
    abs_ = [a for f in K for a in f["properties"]["abaisses"]]
    man = {
        "schema": marquages.SCHEMA_ID,
        "site": {"id": "paquet_jardin", "nom": "carrefour Paquet Jardin, Meylan (Isère)", "crs": "EPSG:2154",
                 "altitudes": "NGF-IGN69", "origine_l93_ngf": [917279.43, 6460289.98, 216.3],
                 "repere_local": "local = L93 - O ; z = NGF - 216,30 ; m, Z haut, X est, Y nord (Unreal : X = x·100, Y = -y·100, Z = z·100)",
                 "unites": "m", "date_etat": "2026-10",
                 "saison": {"nom": "automne", "mois": 10, "feuillage": "automne, jaunissement en cours",
                            "jaunissement": 0.4, "feuilles_mortes_sol": 0.3}},
        "references": {k: {"fichier": rel(p), "sha256": sha256(p), "role": r} for k, (p, r) in REFERENCES.items()},
        "zone_pilote": {"fichier": rel(ZONE), "id": zp["id"], "emprise_local_m": zp["emprise_local_m"],
                        "emprise_l93": zp["emprise_l93"], "photos_panoramax": n_pnx},
        "couches": info,
        "comptes": {"bordures": len(K), "bordures_synthetiques": len(R),
                    "abaisses_traversee": sum(a["type"] == "traversee" for a in abs_),
                    "abaisses_charretiere": sum(a["type"] == "charretiere" for a in abs_),
                    "chartieres": sum(len(a["raccords"]) for a in abs_),
                    "bev": len(B), "surfaces": len(S), "ilots": len(I), "preuves": len(preuves),
                    "marquages": len(feats_m), "marquages_v1": len(corr_m)},
        "statistiques": dict(statistiques(K, S, I, B, rk), marquages=rap_m),
        "preuves": preuves,
        "a_priori": a_priori,
        "regles_pcg": REGLES_PCG,
        "generateur": {"commande": "python recon/pcg/decrire/composer.py",
                       "scripts": {f"recon/pcg/decrire/{s}": sha256(ICI / s) for s in SCRIPTS},
                       "interpreteur": f"CPython {platform.python_version()} ; numpy {np.__version__}"},
    }
    sol = [k for k in sorted(info) if not k.startswith("marquages")]
    h = hashlib.sha256("".join(info[k]["sha256"] for k in sol).encode()).hexdigest()
    man["hash_description"] = h                          # couches de sol (inchangé par la famille marquages)
    man["hash_marquages"] = hashlib.sha256("".join(info[k]["sha256"] for k in sorted(info) if k.startswith("marquages")).encode()).hexdigest()
    ecrire_json(sortie / "description_scene_v2.json", man)
    if png:
        import apercu
        apercu.planche(png, sortie / "base", res=0.05, etiquettes=True)
    return man


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sortie", default=str(SORTIE))
    ap.add_argument("--png", help="planche de contrôle PNG (vue de dessus sur l'ortho)")
    ap.add_argument("--sans-validation", action="store_true")
    a = ap.parse_args()
    man = composer(a.sortie, a.png)
    print(f"description v2 écrite dans {a.sortie} : {man['comptes']}")
    print(f"hash_description {man['hash_description']}")
    if not a.sans_validation:
        import valider
        err, warn, n = valider.valider_dossier(a.sortie)
        for e in err[:100]:
            print("  -", e)
        if err:
            print(f"ÉCHEC de la validation : {len(err)} erreur(s)")
            sys.exit(1)
        print("validation : OK (schéma + contrôles géométriques)")


if __name__ == "__main__":
    main()
