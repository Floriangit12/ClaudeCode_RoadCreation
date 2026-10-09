"""V2 — correspondance entre les PROTOTYPES de la scène USD (paquet v1) et les NOMS D'ASSETS du catalogue.

Constat (2026-10-09) : la scène recon/out/paquet_jardin/package/paquet_jardin_2026.usda nomme ses prototypes
d'après l'atelier objets (lampadaire_crosse_double, banc, corbeille, feu_tete_R11v...) et, pour les arbres,
d'après l'essence et une classe de taille calculée par recon/assemble.py (petit < 8 m, moyen < 15 m, grand
au-delà) — et non d'après les classes du catalogue (jeune < 5, petit 5-10, moyen 10-20, grand 20-30 m).
Or package/substituer_assets.py ne cherche dans la librairie que le nom EXACT du prototype : un asset livré
sous son nom de catalogue (candelabre_double_crosse, arbre_populus_nigra_moyen...) ne serait pas substitué.

Ce module lit la scène (pxr) et produit, pour chaque prototype : l'asset du catalogue majoritaire, la
répartition par instance (un prototype de scène peut regrouper plusieurs assets du catalogue, ex.
lampadaire_mat_droit = candelabre_mat_droit_led ×23 + candelabre_mat_droit_shp ×4) et la table par
identifiant d'instance. assets/specs/outils_mobilier_vegetation/alias_librairie.py s'en sert sur le PC.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

from commun import OBJETS, REPO

SCENE = REPO / "recon" / "out" / "paquet_jardin" / "package" / "paquet_jardin_2026.usda"

FEUX = {"feu_mat": "mat_feu_d114", "feu_tete_R11v": "feu_R11v", "feu_tete_R11v_rep": "feu_R11v_repetiteur",
        "feu_tete_R12": "feu_R12", "feu_tete_R13c": "feu_R13c", "panonceau_M12": "panneau_M12a", "panonceau_AB3a": "panneau_AB3a"}
SIMPLES = {"abri_bus_JCDecaux": "abri_bus_m_reso", "poteau_arret_bus": "poteau_arret_m_reso", "totem_PR": "totem_pr_smmag",
           "banc": "banc_bois_metal", "corbeille": "corbeille_cylindrique", "potelet": "potelet_noir",
           "barriere_levante": "barriere_levante", "poteau_incendie": "poteau_incendie", "balise_J11": "balise_J11",
           "conteneur_verre": "conteneur_verre", "boite_aux_lettres": "boite_aux_lettres_poste", "fontaine": "borne_fontaine",
           "chicane": "chicane_cycles", "portail": "portail_prive", "mobilier_publicitaire": "mupi_publicitaire",
           "panneau_information": "panneau_information_plan", "panneau_M9": "panneau_M9c", "souche": "souche_arbre",
           "arbuste_bosquet": "massif_arbustif"}
D21 = {"pan_D21_1": "panneau_D21a_la_reviree_college", "pan_D21_2": "panneau_D21a_commerces_reviree",
       "pan_D21_3": "panneau_D21a_jalonnement_generique"}      # 3 lames de jalonnement au texte non lu (hors catalogue)
COURTS = {"B21a1", "J5"}


def lire_scene(scene: Path = SCENE):
    """[(instancer, prototype, id, hauteur_cible_m)] ; None si pxr ou la scène manquent."""
    try:
        from pxr import Usd, UsdGeom
    except ImportError:
        return None
    if not scene.exists():
        return None
    st = Usd.Stage.Open(str(scene))
    out = []
    for prim in st.Traverse():
        if not prim.IsA(UsdGeom.PointInstancer):
            continue
        pi = UsdGeom.PointInstancer(prim)
        protos = [t.name for t in pi.GetPrototypesRel().GetTargets()]
        idx = pi.GetProtoIndicesAttr().Get() or []
        pv = UsdGeom.PrimvarsAPI(prim)
        ids = pv.GetPrimvar("id").Get() if pv.HasPrimvar("id") else [None] * len(idx)
        hs = pv.GetPrimvar("hauteur_cible_m").Get() if pv.HasPrimvar("hauteur_cible_m") else [None] * len(idx)
        for i, k in enumerate(idx):
            out.append((str(prim.GetPath()), protos[k], ids[i], None if hs[i] is None else round(float(hs[i]), 2)))
    return out


def _charger(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def resolveur(asset_mobilier, asset_vegetation):
    """Fonction (prototype, id) -> asset du catalogue. asset_mobilier(props) et asset_vegetation(props) viennent
    de construire_specs / donnees_vegetation (mêmes règles que les fiches)."""
    mob = {f["properties"]["id"]: f["properties"] for f in (_charger(OBJETS / "mobilier.geojson") or {}).get("features", [])}
    arb = {f["properties"]["id"]: f["properties"] for f in (_charger(OBJETS / "arbres.geojson") or {}).get("features", [])}
    inst = (_charger(OBJETS / "instances.json") or {}).get("instances", [])
    enfants = collections.defaultdict(list)
    for e in inst:
        if e.get("parent"):
            enfants[e["parent"]].append(e.get("code") or e["prototype"].split("_", 1)[-1])

    def f(proto, iid):
        if proto in FEUX:
            return FEUX[proto]
        if proto == "panneau_D21":
            return D21.get(iid, "panneau_D21a_la_reviree_college")
        if proto in SIMPLES:
            return SIMPLES[proto]
        if proto == "poteau_panneau":
            codes = set(enfants.get(iid, []))
            return "mat_panneau_ilot_court" if codes and codes <= COURTS else "mat_panneau_d60"
        if proto.startswith("panneau_"):
            return proto
        if proto.startswith("arbre"):
            p = arb.get(iid)
            return asset_vegetation(p) if p else None
        p = mob.get(iid)
        if p:
            return asset_mobilier(p)
        return None
    return f


NOTES_PROTO = {
    "stationnement_velos": ("1 instance de la scène = 1 GROUPE OSM (capacité/2 arceaux, voir mobilier.json › arceau_velo › positions › nb_arceaux) : "
                            "à éclater en nb_arceaux arceaux alignés (entraxe 1,0 m) ; les groupes « autres » (pinces-roues, guidons) restent hors catalogue"),
    "poteau_panneau": "hauteur du mât portée par l'échelle Z de l'instance dans la scène (1,0-3,05) : la substitution remet l'échelle à 1 (mobilier) → livrer mat_panneau_d60 à 3,0 m",
    "panneau_D21": "pan_D21_3 = 3 lames de jalonnement au texte non lu (hors catalogue : panneau_D21a_jalonnement_generique proposé)",
    "arbre_populus_nigra_petit": "peuplier d'Italie arbre_363 : probablement recépé/abattu (LiDAR 3,0 m, MNH 4,1 m) — voir vegetation.json",
}


def construire(lignes, resoudre, filtre, hauteurs_retenues=None, catalogue=None, priorite=None, reaffectations=None):
    """Section JSON « correspondance_scene_v1 » pour les instanceurs retenus par filtre(instancer).
    Asset retenu pour l'alias d'un prototype : le plus fréquent parmi les noms du catalogue des besoins
    (à défaut parmi tous), départagé par la priorité du catalogue (1 avant 3)."""
    catalogue = set(catalogue or [])
    priorite = priorite or {}
    par_proto = collections.defaultdict(collections.Counter)
    instances = {}
    for inst, proto, iid, h in lignes:
        if not filtre(inst):
            continue
        a = resoudre(proto, iid) or "(aucun asset du catalogue)"
        par_proto[proto][a] += 1
        e = {"prototype_scene": proto, "asset": a}
        if h is not None:
            e["hauteur_scene_m"] = h
        if reaffectations and iid in reaffectations:
            e["reaffectation"] = reaffectations[iid][1]
        if hauteurs_retenues and iid in hauteurs_retenues:
            hr, raison, _ = hauteurs_retenues[iid]
            e["hauteur_retenue_m"] = hr
            e["raison"] = raison
        instances[iid] = e
    protos = []
    for proto, cnt in sorted(par_proto.items()):
        maj = sorted(cnt, key=lambda k: (k not in catalogue, -cnt[k], priorite.get(k, 9), k))[0]
        d = {"prototype_scene": proto, "instances": sum(cnt.values()), "asset_catalogue": maj,
             "asset_dans_catalogue_besoins": maj in catalogue, "nom_identique": proto == maj}
        if proto in NOTES_PROTO:
            d["note"] = NOTES_PROTO[proto]
        if len(cnt) > 1:
            d["repartition"] = dict(cnt.most_common())
            d["instances_divergentes"] = [{"id": i, "asset": e["asset"]} for i, e in instances.items()
                                          if e["prototype_scene"] == proto and e["asset"] != maj]
        protos.append(d)
    majoritaire = {p["prototype_scene"]: p["asset_catalogue"] for p in protos}
    return {
        "prototypes": protos,
        "resume": {"prototypes_scene": len(protos), "noms_identiques": sum(1 for p in protos if p["nom_identique"]),
                   "instances": len(instances),
                   "instances_exactes_avec_alias_majoritaire": sum(1 for e in instances.values()
                                                                  if e["asset"] == majoritaire[e["prototype_scene"]]),
                   "instances_sans_asset_catalogue": sum(1 for e in instances.values() if e["asset"].startswith("(aucun"))},
        "par_instance": dict(sorted(instances.items())),
    }
