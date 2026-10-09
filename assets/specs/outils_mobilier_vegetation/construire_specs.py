"""Construit les spécifications du lot « mobilier, bordures, végétation, correspondances CARLA » :

  assets/specs/mobilier.json        fiches du mobilier réellement présent (cotes, couleurs RAL,
                                    matériaux, quantités, positions, photos de référence, gabarits)
  assets/specs/bordures.json        profils normalisés en polylignes 2D (m) pour Sweep Houdini,
                                    règles « quel profil où », statistiques sur le site
  assets/specs/vegetation.json      essences, nombres, classes, port, feuillage saisonnier,
                                    gabarits de génération, sources recommandées, positions
  assets/carla_correspondances.json équivalents CARLA (chemins documentés) pour les 122 assets

Usage :  python3 assets/specs/outils_mobilier_vegetation/construire_specs.py
Entrées : assets/catalogue_besoins.json ; recon/out/paquet_jardin/objets/{mobilier,arbres}.geojson,
instances.json ; recon/out/paquet_jardin/relief/bordures_hauteurs.geojson ; data/sites/paquet_jardin/
vector/{gam_topo_sol_bordure_pct,gam_topo_sol_caniveau_lin,osm_crossings}.geojson (les positions
sont omises si ces fichiers manquent).
"""
from __future__ import annotations

import collections
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import (ASSETS, COULEURS, DATE, O_L93, OBJETS, ORIENTATION, RELIEF, SPECS, VECT, charger,  # noqa: E402
                    ecrire_json, r2, yaw_asset)
import donnees_bordures as DB  # noqa: E402
import donnees_carla as DC  # noqa: E402
import donnees_mobilier as DM  # noqa: E402
import donnees_vegetation as DV  # noqa: E402
import correspondance_scene as CS  # noqa: E402

VERSION = 2
HISTORIQUE = [
    {"version": 1, "date": "2026-10-09", "contenu": "première version (fiches, profils, essences, correspondances CARLA)"},
    {"version": 2, "date": DATE, "contenu": ("contrôle visuel des 8 planches V1 et recoupements photo/normes : correspondance prototypes de la scène → "
                                              "noms du catalogue (+ script noms_catalogue_scene.py), hauteurs d'arbres aberrantes corrigées, 2 essences "
                                              "ajoutées (arbre pourpre, peuplier blanc), cyprès n°1 triangulé dans l'emprise (instance à ajouter), arceaux anthracite 0,65 x 0,82 m, positions des BEV, "
                                              "profils de bordures vérifiés sur les plans cotés Celtys, bordure_T3 explicite, identifiants CARLA revérifiés")},
]


def catalogue_info():
    cat = charger(ASSETS / "catalogue_besoins.json") or {}
    noms = set(cat.get("noms_assets", []))
    prio = {it["id"]: it.get("priorite", 9) for v in cat.get("categories", {}).values() for it in v}
    return noms, prio


def _asset_veg(p):
    if p.get("id") in DV.REAFFECTATIONS:
        return DV.REAFFECTATIONS[p["id"]][0]
    ess = p.get("essence") or p.get("type")
    return DV.asset_pour(ess.split(" (")[0].replace("?", "").strip() if ess else ess, p.get("hauteur_classe_inventaire"),
                         p.get("statut_2026"), p.get("essence_code"))


_LIGNES = None


def lignes_scene():
    global _LIGNES
    if _LIGNES is None:
        _LIGNES = CS.lire_scene() or []
    return _LIGNES


def correspondance(vegetation: bool, fichier_prec: Path):
    """Section « correspondance_scene_v1 » (lue dans la scène USD ; à défaut, version précédente du fichier)."""
    L = lignes_scene()
    if not L:
        return (charger(fichier_prec) or {}).get("correspondance_scene_v1")
    noms, prio = catalogue_info()
    res = CS.resolveur(asset_mobilier, _asset_veg)
    filtre = (lambda i: i.startswith("/World/Vegetation")) if vegetation else (lambda i: not i.startswith("/World/Vegetation"))
    sec = CS.construire(L, res, filtre, DV.HAUTEURS_RETENUES if vegetation else None, noms, prio, DV.REAFFECTATIONS if vegetation else None)
    sec = {
        "scene": str(CS.SCENE.relative_to(ASSETS.parent)) + " (paquet v1 du 2026-10-09)",
        "probleme": ("les prototypes de la scène portent les noms de l'atelier objets" + (" et des classes de taille calculées par recon/assemble.py "
                     "(petit < 8 m, moyen < 15 m, grand au-delà ≠ classes du catalogue jeune < 5, petit 5-10, moyen 10-20, grand 20-30 m)" if vegetation else "")
                     + " ; package/substituer_assets.py ne cherche que le nom exact du prototype → un asset livré sous son nom de catalogue ne serait pas substitué"),
        "solution_pc": ("hython assets/specs/outils_mobilier_vegetation/noms_catalogue_scene.py --scene <paquet>/paquet_jardin_2026.usda, PUIS substituer_assets.py : "
                        "la couche layers/noms_catalogue.usda réaffecte chaque instance au prototype nommé comme son asset (table par_instance)"
                        + (" et ajoute le primvar hauteur_m (lu par substituer_assets.py, absent de la scène v1 qui ne porte que hauteur_cible_m), "
                           "avec les hauteurs retenues ci-dessous à la place des hauteurs aberrantes" if vegetation else "")),
        "solution_durable": "recon/assemble.py devrait nommer directement les prototypes avec ces noms (table par_instance) dans le paquet v2",
        **sec,
    }
    return sec

HPS = {"9530354220", "9530354517", "12894141026", "12894130974"}   # OSM lamp_type=high_pressure_sodium


def _l93_local(c):
    x, y = c[0], c[1]
    if abs(x) < 180:
        from pyproj import Transformer
        x, y = Transformer.from_crs(4326, 2154, always_xy=True).transform(x, y)
    return x - O_L93[0], y - O_L93[1]


# ------------------------------------------------------------------------------------- mobilier
def asset_mobilier(p):
    t = p.get("type")
    pid = str(p.get("id", ""))
    if t == "lampadaire":
        osm = pid.split("_")[-1]
        st = p.get("sous_type") or ""
        if osm in HPS:
            return "candelabre_mat_droit_shp"
        if "crosse" in st:
            return "candelabre_double_crosse" if (p.get("nb_crosses") == 2 or pid == "lamp_9514795520") else "candelabre_crosse_simple"
        return "candelabre_mat_droit_led"
    if t == "armoire":
        return "armoire_commande_feux" if "feux" in pid else "armoire_technique"
    if t == "poteau_reseau":
        return "poteau_bois_reseau" if p.get("osm_material") == "wood" else "mat_illumination_cable"
    if t == "stationnement_velos":
        return "arceau_velo" if p.get("osm_bicycle_parking") == "stands" else "stationnement_velos_autre"
    if t == "mat_camera":
        return "mat_feu_crosse_camera" if "SW_TPC" in pid else "mat_camera_video"
    if t == "distributeur":
        return "distributeur_titres_m_reso" if p.get("osm_vending") == "public_transport_tickets" else "distributeur_sacs_canins"
    return {"abri_bus": "abri_bus_m_reso", "poteau_arret": "poteau_arret_m_reso", "totem_PR": "totem_pr_smmag",
            "corbeille": "corbeille_cylindrique", "barriere_levante": "barriere_levante", "poteau_incendie": "poteau_incendie",
            "banc": "banc_bois_metal", "potelet": "potelet_noir", "balise_J11": "balise_J11", "conteneur_verre": "conteneur_verre",
            "panneau_information": "panneau_information_plan", "mobilier_publicitaire": "mupi_publicitaire",
            "boite_aux_lettres": "boite_aux_lettres_poste", "fontaine": "borne_fontaine", "chicane": "chicane_cycles",
            "portail": "portail_prive", "cloture": "cloture_grillage_rigide"}.get(t)


def positions_mobilier():
    mob = charger(OBJETS / "mobilier.geojson")
    out = collections.defaultdict(list)
    if not mob:
        return out
    for f in mob["features"]:
        p = f["properties"]
        if p.get("x_local") is None or p.get("type") in ("support_feux", "panneau", "feu"):
            continue
        a = asset_mobilier(p)
        if not a:
            continue
        e = {"id": p.get("id"), "x": r2(p.get("x_local")), "y": r2(p.get("y_local")), "z": r2(p.get("z_local")),
             "yaw_atelier_deg": r2(p.get("yaw_deg"), 1), "yaw_asset_deg": yaw_asset(p.get("yaw_deg")),
             "hauteur_m": r2(p.get("hauteur_m")), "statut_2026": p.get("statut_2026"), "confiance": p.get("confiance")}
        if p.get("ref"):
            e["ref"] = p["ref"]
        if a == "arceau_velo":
            cap = p.get("osm_capacity")
            e["nb_arceaux"] = max(1, int(cap) // 2) if cap and str(cap).isdigit() else None
        if p.get("remarque"):
            e["remarque"] = p["remarque"][:160]
        out[a].append({k: v for k, v in e.items() if v is not None})
    return out


def alias_prototypes():
    inst = charger(OBJETS / "instances.json")
    cnt = collections.Counter(e.get("prototype") for e in (inst or {}).get("instances", []))
    table = {
        "arbre_feuillu": "arbre_<genre>_<espece>_<classe> si l'essence est connue (voir vegetation.json), sinon arbre_feuillu_generique_moyen",
        "arbre_conifere": "arbre_cedrus_atlantica_grand si Cedrus, sinon arbre_conifere_generique_moyen (cyprès / pins privés : voir vegetation.json)",
        "arbre_jeune_tuteure": "arbre_<essence>_jeune selon essence_code (Alc, As, Ce, Ul, Oc/Qc, Gt, Ca, Ac, Aca), sinon arbre_jeune_tuteure_generique",
        "souche": "souche_arbre (proposé, hors catalogue)",
        "feu_mat": "mat_feu_d114", "feu_tete_R11v": "feu_R11v", "feu_tete_R11v_rep": "feu_R11v_repetiteur", "feu_tete_R12": "feu_R12",
        "feu_tete_R13c": "feu_R13c", "panonceau_M12": "panneau_M12a", "panonceau_AB3a": "panneau_AB3a (sous la tête de feu)",
        "poteau_panneau": "mat_panneau_d60 (ou mat_panneau_ilot_court pour B21a1/J5)", "panneau_D21": "panneau_D21a_la_reviree_college + panneau_D21a_commerces_reviree",
        "lampadaire_crosse_double": "candelabre_double_crosse", "lampadaire_crosse_simple": "candelabre_crosse_simple (sauf réf. 2350 → candelabre_double_crosse)",
        "lampadaire_mat_droit": "candelabre_mat_droit_led (candelabre_mat_droit_shp pour les 4 lanternes sodium OSM)",
        "abri_bus_JCDecaux": "abri_bus_m_reso", "poteau_arret_bus": "poteau_arret_m_reso", "totem_PR": "totem_pr_smmag", "banc": "banc_bois_metal",
        "corbeille": "corbeille_cylindrique", "stationnement_velos": "arceau_velo (× nb_arceaux, groupes « stands » ; autres groupes : supports muraux, hors catalogue)",
        "armoire": "armoire_commande_feux (armoire_feux_VERC) / armoire_technique", "poteau_reseau": "poteau_bois_reseau (bois) / mat_illumination_cable (acier, OSM material=steel)",
        "mat_camera": "mat_feu_crosse_camera (mat_camera_SW_TPC) / mat_camera_video (proposé)", "poteau_incendie": "poteau_incendie", "potelet": "potelet_noir",
        "barriere_levante": "barriere_levante", "balise_J11": "balise_J11 (proposé)", "distributeur": "distributeur_titres_m_reso / distributeur_sacs_canins (proposés)",
        "conteneur_verre": "conteneur_verre (proposé)", "panneau_information": "panneau_information_plan (proposé)",
        "mobilier_publicitaire": "mupi_publicitaire = caisson de l'abri (proposé, ne pas doubler)", "boite_aux_lettres": "boite_aux_lettres_poste (proposé)",
        "fontaine": "borne_fontaine (proposé)", "chicane": "chicane_cycles (proposé)", "portail": "portail_prive (proposé)",
    }
    for k in list(table):
        if k.startswith("panneau_") and k not in ("panneau_D21", "panneau_information"):
            pass
    lignes = []
    for proto, n in sorted(cnt.items(), key=lambda kv: -kv[1]):
        cible = table.get(proto) or (proto if proto and proto.startswith("panneau_") else None)
        lignes.append({"prototype_atelier": proto, "instances": n, "asset_catalogue": cible or "(à définir)"})
    return lignes


def abaisses_bev():
    """V2 : abaissés des traversées = paires de chartières GAM (droite + gauche à moins de 7 m) ; une BEV par abaissé."""
    ch = chartieres()
    dr = [c for c in ch if "DROITE" in c["bloc"]]
    ga = [c for c in ch if "GAUCHE" in c["bloc"]]
    out, pris = [], set()
    for d in dr:
        best = None
        for j, g in enumerate(ga):
            if j in pris:
                continue
            dd = ((d["x"] - g["x"]) ** 2 + (d["y"] - g["y"]) ** 2) ** 0.5
            if dd < 7.0 and (best is None or dd < best[0]):
                best = (dd, j, g)
        if best:
            dd, j, g = best
            pris.add(j)
            out.append({"x": round((d["x"] + g["x"]) / 2, 2), "y": round((d["y"] + g["y"]) / 2, 2), "ecart_chartieres_m": round(dd, 2),
                        "rotation_gam_deg": d.get("rotation_gam_deg"), "longueur_bev_m": round(max(1.2, dd - 0.4), 2),
                        "source": "paire CHARTIERE_DROITE/GAUCHE du levé GAM 2025"})
    seules = len(dr) + len(ga) - 2 * len(out)
    tv = [t for t in traversees_bev() if t.get("type") in ("traffic_signals", "uncontrolled", "marked", "unmarked") or t.get("tactile_paving") == "yes"]
    return {"note": (f"{len(out)} abaissés appariés ({seules} chartière(s) isolée(s)) ; BEV posée derrière le nez de l'abaissé, première rangée de plots à 0,50 m, "
                     "sur toute la largeur de l'abaissé (longueur_bev_m ≈ écart des chartières − 0,4 m, ≥ 1,20 m) ; les refuges reçoivent 2 bandes dos à dos ; "
                     f"{len(tv)} traversées OSM dans l'emprise (dont {sum(1 for t in tv if t.get('tactile_paving') == 'yes')} tactile_paving=yes) : "
                     "voir bordures.json › abaisses › traversees_osm pour celles hors levé GAM"),
            "abaisses": out}


def construire_mobilier():
    pos = positions_mobilier()
    fiches = []
    for f in DM.FICHES:
        f = dict(f)
        if f["asset"] == "bev_podotactile":
            f["positions_abaisses"] = abaisses_bev()
        ps = pos.get(f["asset"], [])
        if ps:
            f["positions"] = ps
            n = sum(p.get("nb_arceaux", 1) for p in ps) if f["asset"] == "arceau_velo" else len(ps)
            f["quantite"] = dict(f["quantite"], positions_connues=n)
        else:
            f["positions"] = []
        fiches.append(f)
    comps = []
    for c in DM.COMPLEMENTS:
        c = dict(c)
        ps = pos.get(c["asset_propose"], [])
        if ps:
            c["positions"] = ps
        comps.append(c)
    autres = pos.get("stationnement_velos_autre", [])
    data = {
        "meta": {
            "site": "paquet_jardin (Meylan) — carrefour avenue de Verdun RD1090 / chemin de la Revirée / avenue du Vercors",
            "etat": "octobre 2026 (dernières photos du cœur : 2025-08-31 ; abords sud : 2026-07-28) — modèles 2026 supposés identiques à 2025",
            "date": DATE, "role": "cahier des charges vérifié du mobilier (fabrication finale sur le PC : Houdini 22 / Unreal 5.8 ; voir carla_correspondances.json)",
            "conventions_asset": ORIENTATION,
            "methode_cotes": ("photos Panoramax équirectangulaires 5760 x 2880 (16 px/°), tuiles 1000 x 1000 natives ; horizon à y = 440 dans les tuiles "
                              "r01 ; hauteur de caméra 1,6-1,9 m (GoPro sur toit, calée sur une tête R11v ≈ 1 m) ; distance par le GPS de la photo et la "
                              "position de l'objet ; h = h_cam + d·tan(élévation). Recoupements : LiDAR HD 2021 (hauteurs de mâts), ortho 5 cm 2022, OSM 2026, "
                              "plan projet 2025, objets de taille connue (personne 1,7 m, voiture, tête de feu, panneau normalisé)."),
            "references": ["NF EN 40 (candélabres)", "NF EN 13201 (éclairage public)", "NF P98-351 (dispositifs podotactiles)",
                           "arrêté du 15 janvier 2007 (accessibilité de la voirie)", "NF EN 14384 (poteaux d'incendie)", "IISR 8e partie (signalisation temporaire)"],
            "sources_donnees": ["recon/out/paquet_jardin/objets/mobilier.geojson (positions, hauteurs LiDAR, OSM)", "data/raw/panoramax/paquet_jardin/tiles (photos)",
                                "data/sites/paquet_jardin/vector/osm_*.geojson", "data/raw/docs/panneau_150dpi.png (plan projet 2025)"],
            "controle_visuel": ["assets/qa/mobilier_vegetation_carla/qa_01_eclairage.jpg", "assets/qa/mobilier_vegetation_carla/qa_02_transport.jpg",
                                "assets/qa/mobilier_vegetation_carla/qa_03_mobilier.jpg", "assets/qa/mobilier_vegetation_carla/qa_08_carla_vs_reel.jpg",
                                "assets/qa/mobilier_vegetation_carla/qa_09_v2_corrections.jpg"],
            "hors_lot": "feux, mâts de feux, mât à crosse caméra et panneaux : assets/specs/feux.json et panneaux.json (la correspondance avec la scène les inclut pour être complète)",
            "version": VERSION, "historique": HISTORIQUE,
        },
        "couleurs": COULEURS,
        "alias_prototypes_atelier": {
            "probleme": ("les prototypes de l'atelier objets (instances.json) ne portent pas les noms du catalogue (ex. lampadaire_crosse_double ≠ "
                         "candelabre_double_crosse) et orientent leur face selon +X. V2 : recon/assemble.py lit désormais « prototype » et « yaw_deg » "
                         "(rotation yaw − 90°, faces +Y) ; reste le renommage → voir correspondance_scene_v1 (table complète par instance, lue dans la scène)."),
            "table": alias_prototypes(),
        },
        "correspondance_scene_v1": correspondance(False, SPECS / "mobilier.json"),
        "modeles": fiches,
        "fiches_complementaires": comps,
        "stationnements_velos_autres_modeles": {"note": "groupes OSM non « stands » (pinces-roues murales, guidons, potelets) : hors catalogue, priorité 3", "positions": autres},
        "non_retenus": DM.NON_RETENUS,
    }
    return ecrire_json(SPECS / "mobilier.json", data), fiches, comps


# ------------------------------------------------------------------------------------- bordures
def stats_bordures():
    d = charger(RELIEF / "bordures_hauteurs.geojson")
    if not d:                                   # atelier relief en cours de régénération : on garde la version précédente
        prec = charger(SPECS / "bordures.json")
        return (prec or {}).get("statistiques_site")
    L = collections.defaultdict(float)
    Lc = collections.defaultdict(float)
    H = collections.defaultdict(list)
    for f in d["features"]:
        p = f["properties"]
        h = p.get("h_vue_m")
        pr = DB.regle(p.get("contexte"), p.get("traversee"), h)
        if pr is None:
            continue
        L[pr] += p.get("longueur_m") or 0
        Lc[(pr, p.get("contexte"))] += p.get("longueur_m") or 0
        H[pr].append(h)

    def q(v, x):
        v = sorted(v)
        return round(v[min(len(v) - 1, int(x * len(v)))], 3)

    return {
        "source": "recon/out/paquet_jardin/relief/bordures_hauteurs.geojson (tronçons de 1 m des bordures GAM, vue h_vue_m : LiDAR 2021 + standards 2025)",
        "longueur_par_profil_m": {k: round(v) for k, v in sorted(L.items(), key=lambda kv: -kv[1])},
        "longueur_par_profil_et_contexte_m": [{"profil": a, "contexte": b, "longueur_m": round(v)} for (a, b), v in sorted(Lc.items(), key=lambda kv: -kv[1])],
        "vue_par_profil_m": {k: {"p10": q(v, 0.1), "p50": q(v, 0.5), "p90": q(v, 0.9)} for k, v in H.items()},
    }


def chartieres():
    d = charger(VECT / "gam_topo_sol_bordure_pct.geojson")
    out = []
    for f in (d or {}).get("features", []):
        p = f["properties"]
        if not p.get("bloc"):
            continue
        g = f["geometry"]
        c = g["coordinates"][0] if g["type"] == "MultiPoint" else g["coordinates"]
        x, y = _l93_local(c)
        out.append({"bloc": p["bloc"], "x": round(x, 2), "y": round(y, 2), "rotation_gam_deg": r2(p.get("rotation"), 1), "echelle": p.get("echelle_bloc")})
    return out


def traversees_bev():
    d = charger(VECT / "osm_crossings.geojson")
    out = []
    for f in (d or {}).get("features", []):
        p = f["properties"]
        x, y = _l93_local(f["geometry"]["coordinates"])
        out.append({"osm_id": p.get("osm_id"), "x": round(x, 2), "y": round(y, 2), "type": p.get("crossing"),
                    "tactile_paving": p.get("tactile_paving"), "kerb": p.get("kerb")})
    return out


def longueur_caniveaux():
    d = charger(VECT / "gam_topo_sol_caniveau_lin.geojson")
    if not d:
        return None
    from shapely.geometry import shape
    tot = 0.0
    for f in d["features"]:
        g = shape(f["geometry"])
        c = list(g.coords) if g.geom_type == "LineString" else [pt for gg in g.geoms for pt in gg.coords]
        if c and abs(c[0][0]) < 180:
            from shapely.ops import transform
            from pyproj import Transformer
            tr = Transformer.from_crs(4326, 2154, always_xy=True)
            g = transform(tr.transform, g)
        tot += g.length
    return round(tot, 1)


def construire_bordures():
    profils = {}
    for k, p in DB.PROFILS.items():
        p = dict(p)
        c = p["contour"]
        if k.startswith("CS") or k.startswith("CC"):
            hz = c[1][1] + 0.005 if k.startswith("CS") else c[1][1] + 0.005
            vue = None
        else:
            hz = None
            vue = p.get("vue_courante")
        if vue:
            v = round(sum(vue) / 2, 3)
            H = max(pt[1] for pt in c)
            p["pose_exemple"] = {"vue_m": v, "translation_v_m": round(-(H - v), 4),
                                 "contour_pose": [[pt[0], round(pt[1] - (H - v), 4)] for pt in c],
                                 "lecture": "origine = pied de la face vue au niveau de la chaussée (fil d'eau) ; v = 0 = chaussée"}
        elif hz is not None:
            p["pose_exemple"] = {"translation_v_m": round(-hz, 4), "contour_pose": [[pt[0], round(pt[1] - hz, 4)] for pt in c],
                                 "lecture": "origine = arête côté chaussée au niveau de la chaussée"}
        p["nb_points"] = len(c)
        p["source_cotes"] = DB.SOURCES_PROFILS.get(k, "voir meta.sources")
        profils[k] = p
    data = {
        "meta": {
            "date": DATE, "role": "profils exacts des bordures et caniveaux béton français, prêts pour un Sweep (Houdini 22) ou BP_Spline (CARLA/Unreal), et affectation sur le site",
            "normes": ["NF EN 1340 (bordures et caniveaux en béton : exigences)", "NF P98-340/CN (complément national : profils T, A, C, P, I et tolérances)",
                       "NF P98-351 (BEV)", "arrêté du 15 janvier 2007 (abaissés, ressauts)"],
            "repere_profil": DB.__doc__.strip().split("\n\n")[1],
            "unites": "mètres",
            "longueur_element": "1,00 m (joints de 3-5 mm, éléments de 0,50 m en courbe serrée ; éléments courbes R 25 en nez d'îlot)",
            "tolerances_nf": "faces vues : ± 3 mm (< 100 mm), ± 3 % (100-170 mm), ± 5 mm (> 170 mm) ; longueur ± 1 %",
            "sources": DB.SOURCES,
            "controle_visuel": ["assets/qa/mobilier_vegetation_carla/qa_04_bordures_profils.jpg", "assets/qa/mobilier_vegetation_carla/qa_05_bordures_site.jpg",
                                "assets/qa/mobilier_vegetation_carla/qa_09_v2_corrections.jpg (bordure_T3)"],
            "verification_v2": DB.VERIFICATION_V2,
            "version": VERSION, "historique": HISTORIQUE,
        },
        "profils": profils,
        "assets": DB.ASSETS,
        "regles_affectation": DB.REGLES,
        "statistiques_site": stats_bordures(),
        "usage_site": DB.USAGE_SITE,
        "abaisses": {
            "principe": ("élément T2 bateau (vue 0,02 m) sur la largeur de la traversée (≥ 1,20 m ; 2-4 m sur le site), encadré de deux chartières de 1,00 m "
                         "(raccord gauche / droite) où la vue varie linéairement de la vue courante à 0,02 m ; trottoir raccordé en pente ≤ 5 % (8 % sur ≤ 2 m) ; "
                         "BEV derrière (voir mobilier.json : bev_podotactile, première ligne de plots à 0,50 m du nez)"),
            "houdini": "Sweep du profil T2 avec un attribut de point « vue » interpolé sur la courbe ; translation v = −(H − vue) par point (Point Wrangle avant Sweep : @P.y += ...), ou PolyLoft entre profils T2 et T2_bateau",
            "chartieres_gam": chartieres(),
            "traversees_osm": traversees_bev(),
        },
        "caniveaux": {"longueur_gam_m": longueur_caniveaux(), "profil": "CS2 (25 cm) au pied des T2 ; CS1 en variante ; caniveau à fente (grille continue Ø fente 2-3 cm) le long du quai SE"},
        "houdini_sweep": {
            "script": "assets/specs/outils_mobilier_vegetation/bordures_profil_sop.py (Python SOP : lit ce fichier et crée le profil choisi dans le plan XY, X = u, Y = v)",
            "chaine": ["Object Merge des courbes de bordures (GAM / atelier relief, Z-up converti en Y-up)", "Resample 0,25 m (courbes) / 1 m (droites)",
                       "Python SOP (profil, vue) → Sweep (Surface Type : Ribbon/Columns ; Cross Section : second input ; Up Vector : +Y monde)",
                       "si la face vue regarde le trottoir : Reverse sur la courbe (ou « Reverse Cross Sections »)",
                       "UV : U le long de la courbe en mètres (joints tous les 1 m dans le matériau), V = abscisse du contour",
                       "matériau beton_bordure (manifeste_cc0.json) ; option masque d'usure (épaufrures sur l'arête avant, mousses dans les joints)"],
            "unreal": "export USD (Z-up, m) puis import ; ou maillage d'un élément de 1 m + BP_Spline CARLA (/Game/Carla/Blueprints/LevelDesign) / Spline Mesh Component",
        },
    }
    return ecrire_json(SPECS / "bordures.json", data)


# ------------------------------------------------------------------------------------- végétation
def construire_vegetation():
    d = charger(OBJETS / "arbres.geojson")
    par = collections.defaultdict(list)
    for f in (d or {}).get("features", []):
        p = f["properties"]
        ess = p.get("essence") or p.get("type")
        a = DV.asset_pour(ess.split(" (")[0].replace("?", "").strip() if ess else ess, p.get("hauteur_classe_inventaire"),
                          p.get("statut_2026"), p.get("essence_code"))
        if a:
            par[a].append(p)
    ess_out = []
    for e in DV.ESSENCES:
        e = dict(e)
        tous = par.get(e["asset"], [])
        garder = e["asset"] == "arbre_populus_alba_grand"            # V2 : « à vérifier » mais houppier vu en 2025
        ps = [p for p in tous if garder or "vérifier" not in str(p.get("statut_2026"))]
        av = [p for p in tous if not garder and "vérifier" in str(p.get("statut_2026"))]

        def _h(p):
            if "planté 2025" in str(p.get("statut_2026")):
                return p.get("hauteur_m")
            return p.get("hauteur_lidar_2021_m") or p.get("hauteur_m")
        hs = [_h(p) for p in ps if _h(p)]
        cs = [p.get("diametre_couronne_m") for p in ps if p.get("diametre_couronne_m")]
        e["nombre_2026"] = len(ps) if ps else e.get("nombre_2026")
        if hs:
            e["hauteurs_mesurees_m"] = {"min": round(min(hs), 1), "mediane": round(statistics.median(hs), 1), "max": round(max(hs), 1),
                                        "source": "LiDAR HD 2021 / MNH (atelier objets) ; plan projet pour les jeunes sujets (4,5 m type)"}
        if cs:
            e["couronne_mesuree_m"] = {"mediane": round(statistics.median(cs), 1), "max": round(max(cs), 1)}
        if av:
            e["a_verifier"] = {"nombre": len(av), "note": "statut « à vérifier » dans l'atelier objets (fiche abattue à l'inventaire mais houppier encore présent au LiDAR 2021, ou position incertaine)",
                               "ids": [p.get("id") for p in av]}
        if ps and not e["asset"].endswith("generique_moyen"):
            e["positions"] = [{k: v for k, v in {"id": p.get("id"), "x": r2(p.get("x_local")), "y": r2(p.get("y_local")), "z": r2(p.get("z_local")),
                                                 "hauteur_m": r2(p.get("hauteur_m"), 1), "couronne_m": r2(p.get("diametre_couronne_m"), 1),
                                                 "circonference_cm": p.get("circonference_cm"), "code_plan": p.get("essence_code"),
                                                 "zone": p.get("zone_plantation"),
                                                 "hauteur_retenue_m": DV.HAUTEURS_RETENUES.get(p.get("id"), (None,))[0],
                                                 "hauteur_suspecte": DV.HAUTEURS_RETENUES[p["id"]][1] if p.get("id") in DV.HAUTEURS_RETENUES else None,
                                                 }.items() if v is not None} for p in ps]
        elif ps:
            e["positions"] = f"{len(ps)} instances : recon/out/paquet_jardin/objets/arbres.geojson (essence vide, type {ps[0].get('type')})"
        reaff = [p for p in ps if p.get("id") in DV.REAFFECTATIONS]
        if reaff:
            e["nombre_2026"] = len(ps) - len(reaff)
            e["reaffectations_v2"] = [{"id": p["id"], "asset": DV.REAFFECTATIONS[p["id"]][0], "raison": DV.REAFFECTATIONS[p["id"]][1]} for p in reaff]
        if hs and any(p.get("id") in DV.HAUTEURS_RETENUES for p in ps):
            hr = [DV.HAUTEURS_RETENUES[p["id"]][0] if p.get("id") in DV.HAUTEURS_RETENUES else _h(p) for p in ps if _h(p)]
            e["hauteurs_retenues_m"] = {"min": round(min(hr), 1), "mediane": round(statistics.median(hr), 1), "max": round(max(hr), 1),
                                        "note": "V2 : hauteurs mesurées aberrantes (arbre voisin capté par le LiDAR, sujet recépé) remplacées ; voir positions › hauteur_suspecte"}
        if e["asset"] in ("arbre_cupressus_sempervirens_grand", "arbre_pinus_sylvestris_moyen", "arbre_cedrus_deodara_grand"):
            e["nombre_2026"] = {"arbre_cupressus_sempervirens_grand": 2, "arbre_pinus_sylvestris_moyen": 2, "arbre_cedrus_deodara_grand": 1}[e["asset"]]
        if e["asset"] in ("haie_taillee_persistante",):
            e["nombre_2026"] = "≈ 650 m (500-900)"
        if e["asset"] == "massif_arbustif":
            e["nombre_2026"] = "surface ≈ 9 900 m² (BD TOPO)"
        if e["asset"] == "arbre_jeune_tuteure_generique":
            e["nombre_2026"] = "repli pour les 15 jeunes sujets 2025 si l'essence n'est pas confirmée"
        ess_out.append(e)
    n_jeunes = sum(1 for v in par.values() for p in v if "planté 2025" in str(p.get("statut_2026")))
    data = {
        "meta": {"date": DATE, "etat": "mi-octobre 2026 (feuillage d'automne en cours) ; variantes été / hiver décrites pour les autres scénarios",
                 "classes_taille": {"jeune": "< 5 m", "petit": "5-10 m", "moyen": "10-20 m", "grand": "20-30 m"},
                 "conventions_asset": "mètres, Z vers le haut, pivot au pied du tronc au niveau du sol, < 30 000 triangles en LOD0 (assets/CONVENTIONS.md) ; "
                                      "la substitution met chaque instance à l'échelle de sa hauteur mesurée",
                 "sources": ["data/context/arbres_metropole.geojson (68 fiches dans l'emprise : 52 présentes, 16 abattues)",
                             "recon/out/paquet_jardin/objets/arbres.geojson (470 arbres : GAM, LiDAR, inventaire, plan projet)",
                             "plan projet 2025 (data/raw/docs/panneau_150dpi.png, codes d'essences relus à 150 dpi)", "photos Panoramax 2023-2026"],
                 "controle_visuel": ["assets/qa/mobilier_vegetation_carla/qa_06_vegetation.jpg", "assets/qa/mobilier_vegetation_carla/qa_07_plan_jeunes_sujets.jpg",
                                     "assets/qa/mobilier_vegetation_carla/qa_09_v2_corrections.jpg"],
                 "version": VERSION, "historique": HISTORIQUE,
                 "classes_scene_v1": ("attention : recon/assemble.py (paquet v1) nomme les prototypes d'arbres avec ses propres classes (petit < 8 m, moyen < 15 m, "
                                      "grand au-delà) et l'essence brute : voir correspondance_scene_v1 pour la table prototype de scène → asset"),
                 "lecture_plan_2025": ("codes relus à 150 dpi : TPC planté SO « Alc, As, Ce/Cs, Alc, As » ; noue SE « Ul, Qc/Oc, Qc/Oc, Ul » ; bande NO « Gt, Aca, Ac, Gt, Ac » ; "
                                       "angle NO « Ca » → 15 sujets (dont « Aca », cercle orange en tirets : sujet existant conservé probable). Écarts avec le catalogue des besoins : "
                                       "« As » et « Gt » sont 2 chacun (et non 1) ; « Qc » peut se lire « Oc » (Ostrya carpinifolia, retenu par l'atelier objets).")},
        "sources_production": DV.SOURCES_PROD,
        "generateur_jeune_sujet": {"hda_propose": "jeune_sujet.hda (Houdini 22) : tronc conique + 5-8 charpentières + rameaux (Labs Tree Branch Generator) + cartes de feuilles par essence + tripode bois",
                                   "parametres": ["essence (atlas de feuilles, couleur été/automne)", "hauteur 3,5-5 m", "Ø tige 0,05-0,08 m", "Ø couronne 1,5-2,5 m",
                                                  "état saisonnier 0-1 (vert → coloré → chute)", "tuteurage on/off (tripode 3 x Ø 0,08 x 2,2 m + demi-rondins)", "paillage Ø 1,5-2 m"]},
        "correspondance_scene_v1": dict(correspondance(True, SPECS / "vegetation.json") or {},
                                        instances_a_ajouter=[dict(i, asset=e["asset"]) for e in ess_out for i in e.get("instances_a_ajouter", [])]),
        "essences": ess_out,
        "synthese": {"arbres_inventaire_presents": sum(1 for a, v in par.items() if "generique" not in a and a != "arbre_prunus_cerasifera_pissardii_moyen"
                                                       for p in v if "planté 2025" not in str(p.get("statut_2026")) and "vérifier" not in str(p.get("statut_2026"))),
                     "jeunes_sujets_2025": n_jeunes,
                     "complements_v2": {e["asset"]: e.get("nombre_2026") for e in ess_out if e.get("hors_catalogue_v1")},
                     "note": ("les 3 érables champêtres du plan 2025 (« Ac » ×2, « Aca ») sont comptés dans arbre_acer_campestre_jeune ; "
                              "arbres_inventaire_presents = fiches de l'inventaire présentes (hors « à vérifier », hors compléments V2)")},
        "non_retenus": DV.NON_RETENUS,
    }
    return ecrire_json(SPECS / "vegetation.json", data)


# ------------------------------------------------------------------------------------- CARLA
def construire_carla():
    cat = charger(ASSETS / "catalogue_besoins.json")
    noms = cat["noms_assets"]
    idx = {it["id"]: it for v in cat["categories"].values() for it in v}
    rows = []
    for n in noms:
        cand, adeq, just, reco = DC.corr(n)
        it = idx.get(n, {})
        r = {"asset": n, "categorie": it.get("categorie"), "priorite": it.get("priorite"), "carla": cand, "adequation": adeq,
             "justification": just, "recommandation": reco}
        vus = [DC.CONSTATS_VIGNETTES[c["blueprint_id"]] for c in cand if c.get("blueprint_id") in DC.CONSTATS_VIGNETTES]
        if vus:
            r["constat_vignette_officielle"] = vus
        if it.get("source_recommandee"):
            r["source_recommandee_catalogue"] = it["source_recommandee"]
        rows.append(r)
    for c in DM.COMPLEMENTS:
        cand, adeq, just, reco = DC.corr(c["asset_propose"])
        if c["asset_propose"] == "conteneur_verre":
            cand, adeq, just, reco = [DC.prop("static.prop.glasscontainer")], "proche", "colonne à verre en cloche verte", "CARLA ou maison"
        elif c["asset_propose"] == "boite_aux_lettres_poste":
            cand, adeq, just, reco = [DC.prop("static.prop.mailbox")], "à éviter", "boîte USPS américaine", "maison"
        elif c["asset_propose"] == "borne_fontaine":
            cand, adeq, just, reco = [DC.prop("static.prop.streetfountain")], "proche", "fontaine sur pied", "CARLA ou maison"
        elif c["asset_propose"] == "mupi_publicitaire":
            cand, adeq, just, reco = [DC.prop("static.prop.advertisement")], "proche", "caisson publicitaire sur pied", "intégré à l'abri"
        rows.append({"asset": c["asset_propose"], "categorie": "complement (hors catalogue)", "priorite": c.get("priorite"), "carla": cand,
                     "adequation": adeq, "justification": just, "recommandation": reco})
    # V2 : compléments ajoutés aux spécifications (bordures, végétation, panneau de jalonnement de la scène)
    for nom, cat_, prio in (("bordure_T3", "bordures", 1), ("arbre_prunus_cerasifera_pissardii_moyen", "vegetation", 2),
                            ("arbre_populus_alba_grand", "vegetation", 2), ("panneau_D21a_jalonnement_generique", "signalisation_verticale", 3)):
        cand, adeq, just, reco = DC.corr(nom)
        rows.append({"asset": nom, "categorie": "complement (hors catalogue)", "categorie_lib": cat_, "priorite": prio, "carla": cand,
                     "adequation": adeq, "justification": just, "recommandation": reco, "ajout": "V2"})
    resume = collections.Counter(r["adequation"] for r in rows if r["categorie"] != "complement (hors catalogue)")
    data = {
        "meta": {
            "date": DATE,
            "role": "équivalents du contenu CARLA pour chaque asset de la librairie (doublures, outils de pose) ; rien de CARLA n'est versionné ici",
            "documentation": DC.DOC,
            "version_doc": "carla.readthedocs.io « latest » (consultée le 2026-10-09) + pages 0.9.15 pour la personnalisation des cartes",
            "limite": ("la documentation publie les identifiants des props (static.prop.*) et les DOSSIERS de contenu (feux, panneaux, végétation, poteaux, "
                       "décals, matériaux, blueprints de pose), pas la liste des static meshes : les chemins /Game/... exacts sont complétés sur le PC par "
                       "assets/carla_resoudre_chemins.py (Default.Package.json + inventaire des .uasset), qui écrit carla_correspondances_resolues.json"),
            "adequation": {"identique": "utilisable tel quel (aucun cas : CARLA ne contient pas de mobilier français)",
                           "proche": "doublure acceptable (silhouette, typologie) à retexturer / mettre à l'échelle",
                           "à éviter": "objet étranger trompeur pour la perception (feux et panneaux américains, signalisation temporaire US)",
                           "à vérifier": "dossier pertinent mais essence/modèle exact inconnu : lire les candidats du script de résolution",
                           "aucun équivalent": "rien de comparable dans le contenu documenté"},
            "recommandation": {"maison": "Houdini 22 d'après assets/specs", "CC0": "manifeste_cc0.json / telecharger_cc0.py", "CARLA": "contenu CARLA (export USD)",
                               "Fab": "Fab / Megascans (compte utilisateur)", "SpeedTree": "SpeedTree (compte utilisateur)"},
            "nombre_assets": len(noms), "resume_adequation": dict(resume),
            "nombre_complements_hors_catalogue": len(DM.COMPLEMENTS) + 4,
            "resume_adequation_complements": dict(collections.Counter(r["adequation"] for r in rows if r["categorie"] == "complement (hors catalogue)")),
            "note_decompte": (f"{len(noms)} assets du catalogue des besoins + {len(DM.COMPLEMENTS)} compléments vus sur les photos (mobilier.json › "
                              f"fiches_complementaires) + 4 compléments V2 (bordure_T3, 2 arbres, D21a de jalonnement) = {len(rows)} lignes ; "
                              "resume_adequation ne compte que les assets du catalogue"),
            "controle_visuel": "assets/qa/mobilier_vegetation_carla/qa_08_carla_vs_reel.jpg (vignettes officielles du catalogue des props vs photos du site)",
            "verification_v2": DC.VERIFICATION_V2,
            "version": VERSION, "historique": HISTORIQUE,
            "utilisation_pc": ["python assets/carla_resoudre_chemins.py --carla <racine du dépôt CARLA> [--content <dossier Content>] → assets/carla_correspondances_resolues.json",
                               "pour utiliser une doublure CARLA comme asset de la librairie : Unreal (projet CARLA) › clic droit sur le static mesh › Asset Actions › Export › .usd "
                               "dans assets/lib/<categorie>/<asset>/<asset>.usd(a) ; substituer_assets.py convertit cm / axes ; vérifier la face +Y (sinon tourner l'asset)",
                               "pour la simulation CARLA : garder les blueprints de feux (logique) et remplacer leur mesh par feu_R11v / feu_R12"],
        },
        "dossiers_documentes": DC.DOSSIERS,
        "props_documentes_utiles": DC.PROPS,
        "correspondances": rows,
    }
    return ecrire_json(ASSETS / "carla_correspondances.json", data), rows


if __name__ == "__main__":
    p1, fiches, comps = construire_mobilier()
    p2 = construire_bordures()
    p3 = construire_vegetation()
    p4, rows = construire_carla()
    for p in (p1, p2, p3, p4):
        print(p.relative_to(ASSETS.parent), p.stat().st_size, "octets")
    print(len(fiches), "fiches mobilier,", len(comps), "compléments ;", len(rows), "correspondances CARLA")
