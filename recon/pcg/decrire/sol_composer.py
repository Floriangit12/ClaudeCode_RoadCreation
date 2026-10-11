"""Composition des familles de sol v2 (schéma 0.3, site complet) : bordures, îlots, surfaces (partition
vectorielle), nivellement unique, BEV ; appelée par composer.py (une seule ligne) pour garder les
modifications du fichier partagé locales.

Ordre :
 1. bordures.construire : bordures levées (GAM 2026, PCRS 2019 en zone conservée, plan 2025), abaissés ;
 2. ilots.construire : îlots et bordures de raccord des ceintures (synthétiques) ;
 3. surfaces.construire : partition vectorielle (+ ponts entre bouts de bordure, bordures K-95nn) ;
 4. ilots.lier_surfaces ; nivellement.construire (TQ-SOL-013) ; contrôles ; Z des bordures = pied ;
 5. BEV (ponctuels_sol) posées sur le modèle de nivellement ;
 6. niveau des surfaces et des îlots tiré du modèle.
"""
import collections

import numpy as np

import bordures
import ilots
import nivellement
import regulariser
import sol_site as ctx
import surfaces
from commun import RACINE, VECTEURS, DONNEES, arrondi, coords_geojson, repere

REFERENCES = {
    "gam_2026_bordure_lin": (VECTEURS / "etat_2026/bordure_lin_L93.geojson", "bordures levées GAM 2026 (622 lignes, double arête)"),
    "gam_2026_limite_revetement": (VECTEURS / "etat_2026/limite_revetement_lin_L93.geojson", "limites de revêtement GAM 2026 (partition)"),
    "gam_2026_caniveau": (VECTEURS / "etat_2026/caniveau_lin_L93.geojson", "caniveaux GAM 2026 (CS2)"),
    "gam_topo_vegetation": (VECTEURS / "vector/gam_topo_sol_vegetation_lin.geojson", "limites de végétation (même levé, WGS84)"),
    "gam_topo_talus_haut": (VECTEURS / "vector/gam_topo_sol_talus_haut_lin.geojson", "hauts de talus (même levé, WGS84)"),
    "gam_topo_talus_bas": (VECTEURS / "vector/gam_topo_sol_talus_bas_lin.geojson", "bas de talus (même levé, WGS84)"),
    "gam_topo_clotures": (VECTEURS / "vector/gam_topo_sol_clotures_lin.geojson", "clôtures (largeur utile des trottoirs)"),
    "gam_topo_escalier_rampe": (VECTEURS / "vector/gam_topo_sol_escalier_rampe_lin.geojson", "escaliers et rampes (largeur utile)"),
    "batiments_v1": (DONNEES / "objets/batiments_local.geojson", "emprises de bâtiments (trous de la partition)"),
    "lanes_2026": (DONNEES / "opendrive/lanes_2026.geojson", "voies OpenDRIVE (indices de classe, Dirichlet de chaussée)"),
    "xodr_2026": (RACINE / "recon/out/paquet_jardin/package/paquet_jardin_2026.xodr", "elevation / superelevation / shape (TQ-SOL-004)"),
    "regles_conception": (RACINE / "assets/specs/regles_conception.json", "règles citées (GA-*, TQ-SOL-*, VAL-*)"),
}
SCRIPTS = ["sol_site.py", "sol_partition.py", "sol_geometrie.py", "sol_lacunes.py", "sol_composer.py", "sol_controles.py",
           "sol_apercu.py", "nivellement.py", "nivellement_xodr.py", "nivellement_requete.py"]


def familles_sol(mnt, dossier_base):
    """(K, S, I, B, rk, rs, ri, extra) ; écrit base/nivellement.json et base/nivellement_grille.npz."""
    K, bev_cand, rk = bordures.construire(mnt)
    K, bev_cand, _ = regulariser.bordures(K, bev_cand, mnt)   # GQ-* (regles_qualite_geometrique) : orientation, nœuds, droites/arcs
    I, R, ri = ilots.construire(mnt, K)
    K = K + R
    S, part, rs = surfaces.construire(mnt, K)
    ajouts = part["bordures_ajoutees"]
    K = regulariser.decrire_ajouts(K + ajouts)               # GQ-PRI-003 : primitives des ponts et ceintures (sans déplacement)
    for f in ajouts:                                      # bateaux déduits des ponts (GA-ABA-001)
        P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        for a in f["properties"]["abaisses"]:
            if a.get("bev") and a["bev"]["present"]:
                bev_cand.append((f["properties"]["id"], P, a))
    ilots.lier_surfaces(I, S)
    niv = nivellement.construire(K, S, part, I, mnt)
    ctrl = nivellement.controles(niv, K, S, part)
    nivellement.reecrire_bordures(K, niv)
    f_json, f_npz = nivellement.ecrire(dossier_base, niv, K, S, part, ctrl)
    # surfaces : niveau et modèle tirés du nivellement
    import json
    doc = json.loads(f_json.read_text(encoding="utf-8"))
    par_s = {s["id"]: s for s in doc["surfaces"]}
    for f in S:
        p = f["properties"]
        e = par_s.get(p["id"])
        if not e:
            continue
        p["region_niveau"] = e["region"]
        p["modele_z"] = e["modele"]
        if "z_med" in e:
            p["niveau"].update({"ref": "nivellement_2026", "z_med_ngf": round(e["z_med"] + nivellement.Z_O, 3),
                                "z_min_ngf": round(e["z_min"] + nivellement.Z_O, 3),
                                "z_max_ngf": round(e["z_max"] + nivellement.Z_O, 3)})
    # îlots : dessus de ceinture et remplissage (modèle)
    pieds = {b["id"]: b for b in doc["bordures"]}
    for f in I:
        p = f["properties"]
        tetes = [float(np.median(pieds[k]["z_tete"])) for k in p["ceinture"] if k in pieds]
        if tetes:
            zt = float(np.median(tetes)) + nivellement.Z_O
            p["niveau"] = {"z_dessus_bordure_ngf": round(zt, 3),
                           "z_remplissage_ngf": round(zt - p["remplissage"]["retrait_sous_bordure_m"], 3)}
    # BEV posées sur le modèle (z de la région du trottoir)
    exclusions = [[repere(np.asarray(r, dtype=float)[:-1, :2]) for r in poly]
                  for f in I for poly in ([f["geometry"]["coordinates"]] if f["geometry"]["type"] == "Polygon"
                                          else f["geometry"]["coordinates"])]
    B = bordures.bev(bev_cand, mnt, exclusions)
    import nivellement_requete as NR
    q = NR.Nivellement(dossier_base)
    for f in B:
        C = np.asarray(f["geometry"]["coordinates"][0], dtype=np.float64)
        L = repere(C[:, :2])
        z = q.z(L[:, 0], L[:, 1])
        z = np.where(np.isfinite(z), z, C[:, 2] - nivellement.Z_O)
        f["geometry"]["coordinates"] = [coords_geojson(np.c_[C[:, :2], z + nivellement.Z_O])]
    extra = {"partition": rs, "nivellement": {"json": f_json, "npz": f_npz, "controles": ctrl,
                                              "regions": len(doc["regions"]), "descentes": len(doc["descentes_fin_de_file"])},
             "ponts": len(ajouts), "raccords_ilots": len(R)}
    return K, S, I, B, rk, rs, ri, extra


def statistiques_sol(K, S, I, B, extra):
    """Comptes et statistiques des familles de sol (manifeste, statistiques.sol)."""
    lp = collections.Counter()
    for f in K:
        for it in f["properties"]["intervalles"]:
            lp[it["profil"]] += it["s1"] - it["s0"]
    ab = collections.Counter()
    ab_l = collections.Counter()
    cfg = collections.Counter()
    for f in K:
        for a in f["properties"]["abaisses"]:
            ab[a["type"]] += 1
            ab_l[a["type"]] += a["s1"] - a["s0"]
            cfg[f"{a['type']}/{a.get('configuration', '-')}"] += 1
    sc = collections.Counter()
    sn = collections.Counter()
    for f in S:
        sc[f["properties"]["classe"]] += f["properties"]["aire_m2"]
        sn[f["properties"]["classe"]] += 1
    il = collections.Counter(f["properties"]["remplissage"]["materiau_id"] for f in I)
    src = collections.Counter()
    for f in K:
        src[f["properties"]["prov"]["geometrie"]["src"]] += f["properties"]["longueur_m"]
    return arrondi({
        "emprise_site_local_m": dict(zip(("x_min", "y_min", "x_max", "y_max"), ctx.EMPRISE)),
        "longueur_bordures_par_profil_m": dict(sorted(lp.items())),
        "longueur_bordures_par_source_m": dict(sorted(src.items())),
        "abaisses_par_type": dict(sorted(ab.items())),
        "abaisses_longueur_m": dict(sorted(ab_l.items())),
        "abaisses_configuration": dict(sorted(cfg.items())),
        "surfaces_aire_par_classe_m2": dict(sorted(sc.items())),
        "surfaces_nombre_par_classe": dict(sorted(sn.items())),
        "ilots_par_remplissage": dict(sorted(il.items())),
        "bev": len(B),
        "partition": extra["partition"],
        "ponts_bordures": extra["ponts"], "raccords_ilots": extra["raccords_ilots"],
        "nivellement_regions": extra["nivellement"]["regions"],
        "nivellement_descentes_fin_de_file": extra["nivellement"]["descentes"],
        "nivellement_controles": extra["nivellement"]["controles"],
    }, 3)
