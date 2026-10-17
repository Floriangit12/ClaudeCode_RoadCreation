# -*- coding: utf-8 -*-
"""Rapport du lot L1 (lecture, graphe, profils) : rejoue tout et écrit rapport_L1.json et RAPPORT_L1.md.

    python recon/generateur/validation/faire_rapport_L1.py [--sans-dessins]

Étapes (aucune date ni durée écrite : deux exécutions donnent les mêmes rapports) :
1. HDA rg::lire_modele, rg::graphe, rg::profils construites deux fois (--construire-hda) : signatures et empreintes
   des dossiers développés identiques ;
2. fabrication des 27 descriptions (S01-S12 du catalogue, 12 exemples du format, 3 essais du lot : clothoïdes,
   courbe en S avec rabattement et ralentisseurs, courbe serrée) avec --verifier-determinisme (deux processus) ;
3. robustesse, entrée modèle : inférence OSM réelle du site (69 routes, polylignes) puis fabrication ;
4. contrôles indépendants (controler_L1.py) ;
5. témoins négatifs : le contrôle doit détecter une flèche de 5 mm, un sommet déplacé de 3 mm, une jonction non
   déclarée et une bande inversée ;
6. plans de contrôle et tuiles natives (dessiner_L1.py) ; constats visuels relus dans constats_visuels_L1.json ;
7. critères du lot L1 (PLAN_GENERATEUR § 3).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
OUT = DEPOT / "recon" / "out" / "generateur"
TMP = GEN / "tmp" / "l1"
HYTHON = os.environ.get("HYTHON", "C:/Program Files/Side Effects Software/Houdini 22.0.459/bin/hython.exe")
PILOTE = GEN / "fabriquer_generateur.py"
sys.path.insert(0, str(ICI))
import controler_L1 as C  # noqa: E402

DESCRIPTIONS = (sorted((GEN / "scenes_simples").glob("S*.yaml")) + sorted((GEN / "description" / "exemples").glob("*.yaml"))
                + sorted((ICI / "essais_L1").glob("*.yaml")))


def rel(p):
    return str(Path(p).resolve().relative_to(DEPOT)).replace("\\", "/")


def lancer(cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(DEPOT), env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8"), **kw)
    return r.returncode, r.stdout, r.stderr


HDA_L1 = ("rg_lire_modele", "rg_graphe", "rg_profils")      # les HDA du lot L2 (rg_nivellement, ...) sont hors lot


def empreinte_hda():
    h = hashlib.sha256()
    for f in sorted(x for n in HDA_L1 for x in (GEN / "hda").glob(f"{n}/{n}.hdalc/**/*")):
        if f.is_file():
            h.update(rel(f).encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def signatures(sortie):
    lig = [x for x in sortie.splitlines() if x.startswith("HDA :")]
    return lig[-1][6:].strip() if lig else ""


def scenes_produites(sortie):
    return [x.split(" -> ")[-1].strip() for x in sortie.splitlines() if " -> recon/out/" in x or " -> recon\\out" in x]


# ------------------------------------------------------------------------------------------------ témoins négatifs
def temoins():
    """Chaque témoin fabrique ou modifie une sortie fausse ; le contrôle indépendant doit la refuser."""
    out = []
    base = TMP / "temoins"
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    # 1. flèche de 5 mm demandée à rg::graphe (S11 arc, E1 clothoïdes)
    code, so, se = lancer([HYTHON, PILOTE, GEN / "scenes_simples" / "S11_rue_courbe_R60.yaml",
                           ICI / "essais_L1" / "E1_rue_clothoides.yaml", "--sortie", base / "fleche_5mm", "--fleche", "0.005"])
    fl = [C.controler_scene(base / "fleche_5mm" / n) for n in ("S11", "E1_rue_clothoides")]
    v = max(max(r["fleche_max_m"] for r in s["par_type"].values()) for s in fl)
    out.append({"temoin": "rg::graphe réglé à une flèche de 5 mm (S11, E1)", "mesure": f"flèche mesurée {v * 1000:.3f} mm",
                "detecte": code == 0 and v > C.SEUIL_FLECHE})
    # 2. un sommet d'une limite déplacé de 3 mm vers la gauche (S09, section 1, limite 2)
    d = base / "sommet_3mm" / "S09" / "l1"
    d.mkdir(parents=True)
    c = json.loads((OUT / "S09" / "l1" / "courbes_controle.json").read_text(encoding="utf-8"))
    c["routes"][0]["sections"][1]["limites"][2]["y"][5] += 0.003
    (d / "courbes_controle.json").write_text(json.dumps(c), encoding="utf-8")
    r = C.controler_scene(d.parent)
    v = max(x["sommet_max_m"] for x in r["par_type"].values())
    m = max(x["milieu_max_m"] for x in r["par_type"].values())
    out.append({"temoin": "sommet d'une limite déplacé de 3 mm (S09)", "mesure": f"sommet {v * 1000:.3f} mm, milieu de "
                f"corde {m * 1000:.3f} mm", "detecte": m > C.SEUIL_MILIEU})
    # 3. jonction instantanée non déclarée (ex10 : transition_entree retirée du modèle)
    d = base / "jonction" / "ex10" / "l1"
    d.mkdir(parents=True)
    c = json.loads((OUT / "ex10_changement_de_profil" / "l1" / "courbes_controle.json").read_text(encoding="utf-8"))
    mod = json.loads((DEPOT / c["modele"]["fichier"]).read_text(encoding="utf-8"))
    for s in mod["routes"][0]["sections"]:
        s.pop("transition_entree", None)
    fm = d.parent / "modele_voie.json"
    fm.write_text(json.dumps(mod, ensure_ascii=False), encoding="utf-8")
    c["modele"] = {"fichier": rel(fm), "sha256": hashlib.sha256(fm.read_bytes()).hexdigest()}
    (d / "courbes_controle.json").write_text(json.dumps(c), encoding="utf-8")
    r = C.controler_scene(d.parent)
    v = max([j["ecart_m"] for j in r["jonctions"] if not j["instantanee"]] or [0.0])
    out.append({"temoin": "changement instantané d'ex10 sans « transition_entree : instantanee »",
                "mesure": f"jonction non déclarée de {v:.3f} m", "detecte": v > C.SEUIL_CONTINUITE})
    # 4. limite 1 de S02 portée 0,5 m à droite de la limite 2 (bande inversée, rubans qui se recouvrent)
    d = base / "inversion" / "S02" / "l1"
    d.mkdir(parents=True)
    c = json.loads((OUT / "S02" / "l1" / "courbes_controle.json").read_text(encoding="utf-8"))
    sec = c["routes"][0]["sections"][0]
    l1, l2 = sec["limites"][1], sec["limites"][2]
    l1["y"] = [y - 0.5 for y in l2["y"]]
    l1["t"] = [t - 0.5 for t in l2["t"]]
    (d / "courbes_controle.json").write_text(json.dumps(c), encoding="utf-8")
    r = C.controler_scene(d.parent)
    out.append({"temoin": "limite de S02 déplacée au-delà de sa voisine",
                "mesure": f"{r['largeurs_negatives']} largeurs négatives, recouvrement {r['chevauchement_m2']:.1f} m²",
                "detecte": r["largeurs_negatives"] > 0 and r["chevauchement_m2"] > 1e-6})
    return out


# ------------------------------------------------------------------------------------------------ rapport
def mm(v):
    return f"{v * 1000:.3f} mm".replace(".", ",")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-dessins", action="store_true")
    a = ap.parse_args()
    TMP.mkdir(parents=True, exist_ok=True)
    rapport = {"lot": "L1", "plan": "recon/generateur/PLAN_GENERATEUR.md § 3 (L1) et § 2.3", "etapes": {}}

    # 1. HDA
    e0 = empreinte_hda()
    c1, o1, s1 = lancer([HYTHON, PILOTE, "--construire-hda"])
    e1 = empreinte_hda()
    c2, o2, s2 = lancer([HYTHON, PILOTE, "--construire-hda"])
    e2 = empreinte_hda()
    hda = {"construction": [c1, c2], "signatures": signatures(o2), "signatures_stables": signatures(o1) == signatures(o2),
           "dossiers_identiques": e1 == e2, "empreinte_dossiers": e2, "inchangee_depuis_avant": e0 == e2,
           "dossiers": [rel(p) for n in HDA_L1 for p in sorted((GEN / "hda").glob(f"{n}/{n}.hdalc"))]}
    rapport["etapes"]["hda"] = hda
    print("HDA :", hda["signatures"], "stables" if hda["dossiers_identiques"] else "INSTABLES")

    # 2. fabrication des 27 descriptions, deux processus
    code, so, se = lancer([HYTHON, PILOTE] + DESCRIPTIONS + ["--verifier-determinisme"])
    produits = scenes_produites(so)
    det = "déterminisme : identique" in so
    rapport["etapes"]["fabrication"] = {"descriptions": [rel(p) for p in DESCRIPTIONS], "code": code,
                                        "scenes": [Path(p).parent.name for p in produits], "deterministe": det,
                                        "fichiers_compares": 2 * len(produits)}
    print("fabrication :", len(produits), "scènes ;", "déterministe" if det else "NON DÉTERMINISTE")
    if code:
        print(so[-3000:], se[-3000:])

    # 3. robustesse : inférence OSM réelle puis fabrication (entrée modèle)
    v = DEPOT / "data" / "sites" / "paquet_jardin" / "vector"
    osm = TMP / "osm"
    co, oo, eo = lancer([sys.executable, "-B", GEN / "inference" / "osm_vers_modele.py", v / "osm_roads.geojson",
                         v / "osm_crossings.geojson", "--sortie", osm, "--agglomeration", "oui", "--nom", "osm_paquet_jardin"])
    cf, of, ef = lancer([HYTHON, PILOTE, osm / "modele_voie.json"])
    rapport["etapes"]["osm"] = {"inference": co, "fabrication": cf, "sortie": [x for x in of.splitlines() if " -> " in x]}

    # 4. contrôles indépendants
    scenes = [C.controler_scene(OUT / n) for n in rapport["etapes"]["fabrication"]["scenes"]]
    bil = C.bilan(scenes)
    (ICI / "controles_L1.json").write_text(json.dumps(C.arrondir({"bilan": bil, "scenes": scenes}), ensure_ascii=False,
                                                      indent=1) + "\n", encoding="utf-8")
    r_osm = C.controler_scene(OUT / "osm_paquet_jardin") if cf == 0 else None
    rapport["etapes"]["controles"] = {"fichier": "recon/generateur/validation/controles_L1.json", "bilan": C.arrondir(
        {k: v for k, v in bil.items() if k != "jonctions_continues"})}
    if r_osm:
        rapport["etapes"]["osm"]["controles"] = C.arrondir({k: r_osm[k] for k in (
            "largeurs_negatives", "largeurs_nulles_hors_biseau", "replis", "inversions", "rubans_invalides",
            "chevauchement_m2", "sections_contigues", "polyligne_ecart_max_m", "reference_polyligne_ecart_max_m")})
        rapport["etapes"]["osm"]["routes"] = len(r_osm["routes"])

    # 5. témoins négatifs
    tem = temoins()
    rapport["etapes"]["temoins"] = tem

    # 6. dessins et tuiles
    if not a.sans_dessins:
        cd, od, ed = lancer([sys.executable, "-B", ICI / "dessiner_L1.py", "--tuiles"])
        rapport["etapes"]["dessins"] = {"code": cd, "images": [x for x in od.splitlines() if x.strip()]}
    tuiles = sorted(rel(p) for p in OUT.glob("*/l1/tuiles/*/*.png"))
    constats = json.loads((ICI / "constats_visuels_L1.json").read_text(encoding="utf-8"))
    vues = {t for c_ in constats["constats"] for t in c_["tuiles"]}
    rapport["etapes"]["revue_visuelle"] = {"tuiles_produites": len(tuiles), "tuiles_regardees": len(vues),
                                           "tuiles_regardees_existantes": len(vues & set(tuiles)),
                                           "fichier": "recon/generateur/validation/constats_visuels_L1.json"}

    # 7. critères
    pt = bil["par_type"]
    fl = max(v_["fleche_max_m"] for v_ in list(pt.values()) + list(bil["reference_par_type"].values()))
    mil = {t: pt[t]["milieu_max_m"] for t in ("droite", "arc", "clothoide") if t in pt}
    jc = bil["jonctions_continues"]
    ji = bil["jonctions_instantanees"]
    s_ok = {Path(p).parent.name for p in produits}
    n_s = sum(1 for p in DESCRIPTIONS if p.parent.name == "scenes_simples")
    s_scenes = sorted(n for n in s_ok if n.startswith("S"))
    regard_s = {t.split("/")[3] for t in vues if t.split("/")[3].startswith("S")}
    fl_txt = ", ".join(k + " " + mm(v_["fleche_max_m"]) for k, v_ in sorted(pt.items()))
    n_cordes = sum(v_["cordes"] for v_ in pt.values())
    crit = [
        {"id": "L1-1 HDA rg::lire_modele, rg::graphe, rg::profils (dossiers .hdalc développés, signature stable, "
               "reconstruction identique à l'octet)",
         "valeur": f"{len(hda['dossiers'])} / 3 ; signatures {'stables' if hda['signatures_stables'] else 'instables'}, "
                   f"dossiers {'identiques' if hda['dossiers_identiques'] else 'différents'}",
         "seuil": "3 / 3", "atteint": len(hda["dossiers"]) == 3 and hda["signatures_stables"] and hda["dossiers_identiques"]
         and c1 == 0 and c2 == 0},
        {"id": "L1-2 pilote fabriquer_generateur.py : entrées description simple et modèle fabriquées sans erreur",
         "valeur": f"descriptions {len(produits)} / {len(DESCRIPTIONS)} (S01-S12, 12 exemples, 3 essais) ; modèle OSM réel "
                   f"{'1 / 1' if cf == 0 else '0 / 1'} (69 routes)",
         "seuil": "100 %", "atteint": code == 0 and len(produits) == len(DESCRIPTIONS) and cf == 0},
        {"id": "L1-3 échantillonnage à flèche ≤ 0,5 mm (référence et limites décalées, mesure indépendante)",
         "valeur": f"max {mm(fl)} ({fl_txt} ; {n_cordes} cordes de limites)",
         "seuil": "≤ 0,5 mm", "atteint": fl <= C.SEUIL_FLECHE},
        {"id": "L1-4 écart des limites décalées à la position analytique, mesuré au milieu des cordes (droite, arc, "
               "clothoïde)",
         "valeur": " ; ".join(f"{t} {mm(v_)}" for t, v_ in mil.items()) + f" (sommets : max "
                   f"{mm(max(v_['sommet_max_m'] for v_ in pt.values()))})",
         "seuil": "≤ 1 mm pour chaque type", "atteint": len(mil) == 3 and max(mil.values()) <= C.SEUIL_MILIEU},
        {"id": "L1-5 0 bande de largeur négative ou nulle (hors extrémité de biseau : bande qui naît ou disparaît)",
         "valeur": f"{bil['largeurs_negatives']} négative, {bil['largeurs_nulles_hors_biseau']} nulle ; "
                   f"{bil['extremites_de_biseau']} extrémités de biseau",
         "seuil": "0", "atteint": bil["largeurs_negatives"] == 0 and bil["largeurs_nulles_hors_biseau"] == 0},
        {"id": "L1-6 0 chevauchement (réunion des rubans = somme des aires, 0 repli 1 − tκ ≤ 0, 0 limite inversée)",
         "valeur": f"recouvrement max {bil['chevauchement_max_m2']:.1e} m² (bruit numérique) ; {bil['replis']} repli ; "
                   f"{bil['inversions']} inversion ; {bil['rubans_invalides']} ruban invalide",
         "seuil": "0 (recouvrement ≤ 1e-6 m²)", "atteint": bil["chevauchement_max_m2"] <= 1e-6 and bil["replis"] == 0
         and bil["inversions"] == 0 and bil["rubans_invalides"] == 0},
        {"id": "L1-7 sections contiguës de 0 à L (modèle et sorties)",
         "valeur": f"{bil['sections_contigues']} / {bil['scenes']} scènes",
         "seuil": "100 %", "atteint": bil["sections_contigues"] == bil["scenes"]},
        {"id": "L1-8 transitions de profil continues (bords d'une même bande, bande qui naît ou disparaît) aux jonctions "
               "de sections",
         "valeur": f"{len(jc)} jonctions, écart max {mm(bil['jonction_ecart_max_m'])} ; "
                   f"{len(ji)} changement instantané déclaré (« transition_entree : instantanee ») : "
                   + ", ".join(f"{j['route']} s = {j['s']:g} m, {j['ecart_m']:.2f} m ({j['bande']})" for j in ji),
         "seuil": "≤ 1 mm", "atteint": bil["jonction_ecart_max_m"] <= C.SEUIL_CONTINUITE},
        {"id": "L1-9 transitions verticales (plateaux, dos-d'âne) : dz exporté contre analytique ; flèche du profil en long",
         "valeur": f"écart max {mm(bil['dz_ecart_max_m'])} ; flèche max {mm(bil['dz_fleche_max_m'])}",
         "seuil": "≤ 1 mm ; ≤ 0,5 mm", "atteint": bil["dz_ecart_max_m"] <= C.SEUIL_DZ and bil["dz_fleche_max_m"] <= C.SEUIL_FLECHE},
        {"id": "L1-10 sommets obligatoires présents (raccords, sections, lois de largeur, évènements des limites, "
               "ralentisseurs)",
         "valeur": f"{bil['sommets_obligatoires_manquants']} manquant", "seuil": "0",
         "atteint": bil["sommets_obligatoires_manquants"] == 0},
        {"id": "L1-11 déterminisme (deux processus identiques à l'octet)",
         "valeur": f"{2 * len(produits)} fichiers (courbes_controle.json, manifest_l1.json) : "
                   f"{'identiques' if det else 'différents'} ; HDA reconstruites : "
                   f"{'identiques' if hda['dossiers_identiques'] else 'différentes'}",
         "seuil": "100 %", "atteint": det and hda["dossiers_identiques"]},
        {"id": "L1-12 S01-S12 en courbes de contrôle, regardées en tuiles natives",
         "valeur": f"{len(s_scenes)} / {n_s} fabriquées ; {len(regard_s)} / {n_s} regardées ; "
                   f"{len(vues & set(tuiles))} tuiles regardées sur {len(tuiles)}",
         "seuil": "12 / 12", "atteint": len(s_scenes) == n_s == 12 and len(regard_s) == 12},
        {"id": "L1-13 témoins négatifs détectés par le contrôle indépendant",
         "valeur": f"{sum(t['detecte'] for t in tem)} / {len(tem)} : " + " ; ".join(f"{t['temoin']} → {t['mesure']}"
                                                                               for t in tem),
         "seuil": "100 %", "atteint": all(t["detecte"] for t in tem)},
    ]
    rapport["criteres"] = crit
    rapport["informations"] = C.arrondir({
        "aire_rubans_ecart_relatif_max": bil["aire_ecart_rel_max"], "raccords_primitives_max_m": bil["raccord_max_m"],
        "raccords_primitives_cap_max_deg": bil["raccord_cap_max_deg"],
        "longueur_m_contre_somme_des_primitives_max_m": bil["ecart_longueur_primitives_max_m"],
        "reference_par_type": bil["reference_par_type"], "limites_par_type": bil["par_type"]})
    rapport["statut"] = "ok" if all(c_["atteint"] for c_ in crit) else "partiel"
    (ICI / "rapport_L1.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for c_ in crit:
        print("ATTEINT" if c_["atteint"] else "NON ATTEINT", c_["id"], "|", c_["valeur"], "| seuil", c_["seuil"])
    print("statut :", rapport["statut"])


if __name__ == "__main__":
    main()
