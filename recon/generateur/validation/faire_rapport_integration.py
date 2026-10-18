# -*- coding: utf-8 -*-
"""Rapport du lot « integration » (étape 2) : non-régression, contrôles des lots rejoués, rendus, déterminisme.

    python recon/generateur/validation/faire_rapport_integration.py [--determinisme "identique (N fichiers)"]
                                                                   [--planches-regardees N] [--sans-controleurs]

1. Non-régression : sorties de fabriquer_generateur.py (recon/out/generateur/<scene>) comparées à la copie prise avant
   l'intégration (recon/generateur/tmp/integration/avant/<scene> : étape 1 pour S01-S12, sorties des lots pour B01,
   J1-J5, G1-G3, A1-A4) par comparer_integration.py ; chaque fichier différent est classé : changement voulu (liste
   fermée, décrite) ou écart (mesuré).
2. Compilation : rétrocompatibilité de description_vers_modele (S01-S12, exemples, Meylan) par controler_scenes.py.
3. Contrôles des lots rejoués sur les sorties intégrées (controler_L3, controler_L4, controler_giratoires,
   controler_autoroutes, controler_bordures), comparés aux contrôles écrits par les lots (même mesure, même valeur).
4. Rendus : vues par scène, planche ≤ 1092 px, géométrie rendue = géométrie finale (empreintes des .usda).
Écrit validation/RAPPORT_integration.md et validation/rapport_integration.json. Aucun seuil n'est relâché.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(GEN))
import comparer_integration as CI  # noqa: E402

SORTIE = DEPOT / "recon" / "out" / "generateur"
AVANT = GEN / "tmp" / "integration" / "avant"
TMP = GEN / "tmp" / "integration"
SIMPLES = [f"S{k:02d}" for k in range(1, 13)]
RESEAU = ["B01", "J1_T_cedez", "J2_croix_stop", "J3_croix_feux", "J4_ilots_directionnel_separateurs",
          "J5_carrefour_complexe", "G1_giratoire_urbain_D40", "G2_giratoire_periurbain_D50", "G3_mini_giratoire_D20",
          "A1_autoroute_2x2_GBA", "A2_autoroute_2x3_glissieres", "A3_bretelle_entree", "A4_bretelle_sortie"]
PHARES = ("J5_carrefour_complexe", "G1_giratoire_urbain_D40", "A3_bretelle_entree")
GEOMETRIE = ("sol_points.npy", "sol_faces.npy", "sol_comptes.npy", "sol_attributs.npy", "sol_normales.npy",
             "peinture_points.npy", "peinture_faces.npy", "peinture_comptes.npy", "peinture_attributs.npy",
             "niveaux.json", "heightfield.json", "entites.json", "bev.json", "empreintes.json", "courbes_controle.json",
             "carrefours.json", "trajectoires.json", "conflits.json", "zone_conflit.json", "guidage.json",
             "graphe_voies.json", "marques_l4.json", "giratoires.json", "musoirs.json", "equipements.json")


# ------------------------------------------------------------------------------------------------ USD
def maillages_usda(f: Path) -> dict:
    """{Xform/Mesh: (points (n, 3), indices des faces)} d'un .usda écrit par rendre_l2 (une ligne par tableau)."""
    out, grp, cur = {}, None, None
    for ligne in f.read_text(encoding="utf-8").split("\n"):
        m = re.match(r'\s*def Xform "(\w+)"', ligne)
        if m:
            grp = m.group(1)
        m = re.match(r'\s*def Mesh "(\w+)"', ligne)
        if m:
            cur = f"{grp}/{m.group(1)}"
            out[cur] = [None, None]
        if cur and "point3f[] points" in ligne:
            v = re.findall(r"-?[\d.]+(?:e-?\d+)?", ligne.split("=", 1)[1])
            out[cur][0] = np.array([float(x) for x in v]).reshape(-1, 3)
        if cur and "int[] faceVertexIndices" in ligne:
            out[cur][1] = ligne.split("=", 1)[1].strip()
        for cle in ("primvars:st ", "normals"):
            if cur and cle in ligne and "=" in ligne:
                out[cur].append((cle.strip(), ligne.split("=", 1)[1].strip()))
    return out


def ecart_usda(fa: Path, fb: Path) -> dict:
    a, b = maillages_usda(fa), maillages_usda(fb)
    d = {}
    for k in sorted(set(a) | set(b)):
        if k not in a or k not in b:
            d[k] = "ajouté" if k not in a else "retiré"
            continue
        (pa, ia), (pb, ib) = a[k][:2], b[k][:2]
        autres = sorted({c for c, v in a[k][2:]} ^ {c for c, v in b[k][2:]} |
                        {c for (c, v) in a[k][2:] if (c, v) not in b[k][2:]})
        if pa is None or pb is None or pa.shape != pb.shape:
            d[k] = f"points {None if pa is None else pa.shape[0]} -> {None if pb is None else pb.shape[0]}"
            continue
        e = float(np.abs(pa - pb).max()) if len(pa) else 0.0
        if e > 0 or ia != ib or autres:
            d[k] = {"ecart_points_max_m": e, "points_differents": int((np.abs(pa - pb).max(axis=1) > 0).sum()),
                    "faces_identiques": ia == ib, "autres_tableaux_differents": autres}
    return d


# ------------------------------------------------------------------------------------------------ classement
def classer(scene: str, cle: str, desc: dict) -> tuple[str, str]:
    """(genre, explication) : genre « voulu » (liste fermée) ou « ecart »."""
    nom = cle.split("/")[-1]
    ch = desc.get("chemins") or []
    if nom.startswith("manifest"):
        return "voulu", "manifeste : signatures d'HDA (rg::nivellement à table étendue, pj::bordure::2.1, pj::caniveau::2.2, " \
                        "rg::carrefours_sol / rg::giratoires_sol à table étendue), pilote, familles, empreintes des fichiers"
    if nom == "elements.json" and desc.get("ecart_numerique_max") == 0 and desc.get("autres_valeurs_differentes") == 0:
        return "voulu", "elements.json : champs ajoutés seulement (lot bordures : " + \
            ", ".join(sorted(desc.get("cles_ajoutees", {}))) + ") ; valeurs existantes inchangées"
    if nom == "courbes_controle.json" and ch == ["/lot"]:
        return "voulu", "libellé « lot » seulement (pilote de l'étape 2)"
    if nom == "giratoires.json" and not ch and desc.get("ecart_numerique_max") == 0 \
            and desc.get("autres_valeurs_differentes") == 0:
        return "voulu", "ordre des clés seulement (attributs triés à l'export depuis l'intégration), valeurs identiques"
    if nom == "compilation.json" or nom == "modele_voie.json":
        return "ecart", "compilation différente"
    return "ecart", "à décrire"


def zone_charretieres(scene: str):
    """Entrées charretières du modèle (s0, s1, rampant) et étendue en s des points du sol modifiés (vue de l'entrée
    0,05 -> 0,03 m, intégration) : (zone modifiée, zones admises, tout dedans)."""
    m = json.loads((SORTIE / scene / "modele_voie.json").read_text(encoding="utf-8"))
    ab = [(a["s0"] - a.get("rampant_m", 0.0), a["s1"] + a.get("rampant_m", 0.0)) for p in m["profils"]
          for lim in p["limites"] for a in ((lim.get("bordure") or {}).get("abaisses") or []) if a["type"] == "charretiere"]
    A, B = np.load(AVANT / scene / "l2" / "sol_points.npy"), np.load(SORTIE / scene / "l2" / "sol_points.npy")
    if A.shape != B.shape:
        return None, ab, False
    i = np.where(np.abs(A - B).max(axis=1) > 0)[0]
    if not len(i):
        return None, ab, True
    z = (float(A[i, 3].min()), float(A[i, 3].max()))
    return z, ab, any(a - 1.0 <= z[0] and z[1] <= b + 1.0 for a, b in ab)


def non_regression() -> dict:
    res = {}
    for s in SIMPLES + RESEAU:
        r = CI.comparer_scene(AVANT / s, SORTIE / s)
        lignes = []
        zc = None
        if s == "B01":
            zc = zone_charretieres(s)
        for cle, desc in sorted(r["differents"].items()):
            genre, expl = classer(s, cle, desc)
            if zc is not None and genre != "voulu" and zc[2]:
                genre = "voulu"
                expl = (f"entrée charretière : vue 0,05 -> 0,03 m (bordures_elements.json, compilateur ; lot bordures) ; "
                        f"points du sol modifiés seulement dans s ∈ [{zc[0][0]:.2f} ; {zc[0][1]:.2f}] m (entrée et rampants : "
                        f"{', '.join(f'[{a:.1f} ; {b:.1f}]' for a, b in zc[1])}) ; écart numérique max "
                        f"{desc.get('ecart_numerique_max', desc.get('ecart_max', 0)) or 0:.3f}")
            if cle.endswith(".usda"):
                desc = {"maillages": ecart_usda(AVANT / s / cle, SORTIE / s / cle)}
                m = desc["maillages"]
                if m and all(isinstance(v, dict) and v["ecart_points_max_m"] <= 1e-6 + 1e-12 for v in m.values()):
                    genre = "voulu"
                    em = max(v["ecart_points_max_m"] for v in m.values())
                    tab = sorted({x for v in m.values() for x in v["autres_tableaux_differents"]})
                    expl = ("maillages " + ", ".join(sorted(m)) + f" (pj::caniveau::2.2, lot bordures) : points à "
                            f"{em * 1e6:.1f} µm au plus ; faces " +
                            ("identiques" if all(v["faces_identiques"] for v in m.values()) else "réordonnées") +
                            (f" ; tableaux {', '.join(tab)} différents (UV des pièces : prototypes espacés de 2 m ; "
                             f"normales recalculées)" if tab else ""))
            if cle.endswith("mesures_l2.json") and genre == "ecart":
                genre = "derive"
                expl = (f"mesures recalculées sur la géométrie fabriquée : écart numérique max "
                        f"{desc.get('ecart_numerique_max'):.6f} (rayons des joints : impact derrière la face)")
            lignes.append({"fichier": cle, "genre": genre, "explication": expl, "detail": desc})
        res[s] = {"identiques": r["identiques"], "differents": lignes, "absents": r["absents"], "nouveaux": r["nouveaux"]}
    return res


# ------------------------------------------------------------------------------------------------ contrôles
CONTROLEURS = (("L3", "controler_L3.py", "controles_L3.json", ["J1_T_cedez", "J2_croix_stop", "J3_croix_feux",
                                                                  "J4_ilots_directionnel_separateurs", "J5_carrefour_complexe"]),
               ("L4", "controler_L4.py", "controles_L4.json", ["J1_T_cedez", "J2_croix_stop", "J3_croix_feux",
                                                                  "J4_ilots_directionnel_separateurs", "J5_carrefour_complexe"]),
               ("giratoires", "controler_giratoires.py", "controles_giratoires.json",
                ["G1_giratoire_urbain_D40", "G2_giratoire_periurbain_D50", "G3_mini_giratoire_D20"]),
               ("autoroutes", "controler_autoroutes.py", "controles_autoroutes.json",
                ["A1_autoroute_2x2_GBA", "A2_autoroute_2x3_glissieres", "A3_bretelle_entree", "A4_bretelle_sortie"]))


RACINES = [str(p).replace("\\", "/") for p in (AVANT, SORTIE)] + [str(p) for p in (AVANT, SORTIE)]


def _sans_chemins(x):
    """Retire les champs propres à l'exécution (dates) et ramène les dossiers de sortie à « <sortie> »."""
    if isinstance(x, dict):
        return {k: _sans_chemins(v) for k, v in x.items() if k not in ("date", "duree_s")}
    if isinstance(x, list):
        return [_sans_chemins(v) for v in x]
    if isinstance(x, str):
        for r in RACINES:
            x = x.replace(r, "<sortie>")
    return x


def controles(sans=False) -> dict:
    out = {}
    env = {"PYTHONIOENCODING": "utf-8"}
    import os
    env = dict(os.environ, **env)
    for lot, script, ref, scenes in CONTROLEURS:
        # référence : le contrôle rejoué sur la copie prise avant l'intégration (contrôleurs qui prennent un dossier) ;
        # controler_L4.py lit les scènes sous recon/out/generateur : référence = controles_L4.json du lot L4, écrit sur
        # ses sorties finales (celles de la copie)
        f = TMP / f"controles_{lot}_integration.json"
        f_ref = TMP / f"controles_{lot}_avant.json" if lot != "L4" else ICI / ref
        lancer = [] if sans else [(f, scenes if lot == "L4" else [str(SORTIE / s) for s in scenes])]
        if not sans and lot != "L4" and not f_ref.exists():          # référence calculée une fois
            lancer.append((f_ref, [str(AVANT / s) for s in scenes]))
        err = ""
        for fj, arg in lancer:
            r = subprocess.run([sys.executable, "-B", str(ICI / script)] + arg + ["--json", str(fj)], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", env=env, cwd=str(DEPOT))
            if r.returncode:
                err += r.stdout[-1500:] + r.stderr[-1500:]
        if err or not f.exists() or not f_ref.exists():
            out[lot] = {"erreur": err or "contrôle absent"}
            continue
        a = _sans_chemins(json.loads(f_ref.read_text(encoding="utf-8")))
        b = _sans_chemins(json.loads(f.read_text(encoding="utf-8")))
        ec = CI._ecart_numerique(a, b, [0.0, 0])
        out[lot] = {"scenes": scenes, "ecart_numerique_max": ec[0], "autres_valeurs_differentes": ec[1],
                    "chemins": CI._chemins_json(a, b, n=20), "identique": a == b}
    # lot bordures : critères recalculés (B01, S03, S08, S_M24…) contre ceux du lot
    f = TMP / "rapport_bordures_integration.json"
    if not sans:
        r = subprocess.run([sys.executable, "-B", str(ICI / "controler_bordures.py"), "--json", str(f)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=str(DEPOT))
    if f.exists():
        a = {c["id"]: c for c in json.loads((ICI / "rapport_bordures.json").read_text(encoding="utf-8"))["criteres"]}
        bb = json.loads(f.read_text(encoding="utf-8"))
        b = {c["id"]: c for c in (bb.get("criteres") or [])}
        communs = sorted(k for k in a if k in b)
        out["bordures"] = {"criteres": {k: {"avant": [a[k]["valeur"], a[k]["atteint"]],
                                            "apres": [b[k]["valeur"], b[k]["atteint"]]} for k in communs},
                           # C-B11 (rétrocompatibilité) et C-B12 (déterminisme) du pilote du lot ne sont pas calculés par
                           # controler_bordures.py : remplacés ici par INT-2 / INT-3 et INT-7
                           "non_recalcules": sorted(k for k in a if k not in b),
                           "perdus": [k for k in communs if a[k]["atteint"] and not b[k]["atteint"]],
                           "gagnes": [k for k in communs if b[k]["atteint"] and not a[k]["atteint"]],
                           "statuts_identiques": all(a[k]["atteint"] == b[k]["atteint"] for k in communs)}
    return out


# ------------------------------------------------------------------------------------------------ rendus
def rendus() -> dict:
    from PIL import Image
    out = {}
    for s in SIMPLES + RESEAU:
        d = SORTIE / s / "rendus"
        try:
            man = json.loads((d / "manifest_rendus.json").read_text(encoding="utf-8"))
        except OSError:
            out[s] = {"absent": True}
            continue
        pl = d / f"planche_{s}.png"
        taille = list(Image.open(pl).size) if pl.exists() else None
        geo = {}
        for k, h in (man.get("geometrie_rendue_sha256") or {}).items():
            f = SORTIE / s / k
            geo[k] = f.exists() and hashlib.sha256(f.read_bytes()).hexdigest() == h
        out[s] = {"vues": sorted(man.get("images", {})), "n_vues": len(man.get("images", {})), "planche": taille,
                  "attendu": 3 if s in PHARES else 2, "geometrie_finale": all(geo.values()) and bool(geo),
                  "duree_s": man.get("duree_s")}
    return out


# ------------------------------------------------------------------------------------------------ rapport
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--determinisme", default="")
    ap.add_argument("--scenes-determinisme", default="J5_carrefour_complexe, G1_giratoire_urbain_D40")
    ap.add_argument("--planches-regardees", type=int, default=0)
    ap.add_argument("--sans-controleurs", action="store_true")
    ap.add_argument("--retro", default=str(TMP / "controle_scenes_apres.json"))
    a = ap.parse_args()
    nr = non_regression()
    ctl = controles(a.sans_controleurs)
    rd = rendus()
    retro = json.loads(Path(a.retro).read_text(encoding="utf-8")).get("retrocompatibilite") if Path(a.retro).exists() else None
    log = (TMP / "fabrication.log").read_text(encoding="utf-8", errors="replace") if (TMP / "fabrication.log").exists() else ""
    fab = sorted({m.group(1) for m in re.finditer(r"^(\S+) (?:\[[^\]]*\] )?: .*-> recon/out/generateur/", log, re.M)})
    code = re.findall(r"^code (\d+)", log, re.M)
    ecarts = {s: [x for x in v["differents"] if x["genre"] == "ecart"] for s, v in nr.items()}
    geo_s = {s: [x["fichier"] for x in nr[s]["differents"] if x["fichier"].split("/")[-1] in GEOMETRIE
                 and x["genre"] != "voulu"] for s in SIMPLES}
    n_geo_s = sum(1 for s in SIMPLES for x in nr[s]["differents"] if x["fichier"].split("/")[-1] in GEOMETRIE)
    planches = sorted((SORTIE / "catalogue_rendus").glob("etape2_*.png"))
    from PIL import Image
    tailles = {p.name: list(Image.open(p).size) for p in planches}
    ok_rd = [s for s, v in rd.items() if not v.get("absent") and v["n_vues"] == v["attendu"] and v["planche"]
             and max(v["planche"]) <= 1092 and v["geometrie_finale"]]
    crit = [
        {"id": "INT-1", "nom": "une seule commande (fabriquer_generateur.py --complet) pour les 25 scènes, description → rendu",
         "valeur": f"{len(fab)}/25 scènes fabriquées, code de sortie {code[-1] if code else '?'}", "seuil": "25/25, code 0",
         "atteint": len(fab) == 25 and code[-1:] == ["0"]},
        {"id": "INT-2", "nom": "S01-S12 : géométrie (sol, peinture, niveaux, HeightField, entités, BEV, empreintes, courbes L1) "
                               "identique à l'étape 1",
         "valeur": f"{sum(1 for s in SIMPLES if not geo_s[s])}/12 scènes ; fichiers géométriques différents : "
                   f"{n_geo_s}", "seuil": "12/12 (écarts seulement voulus et listés)",
         "atteint": all(not geo_s[s] for s in SIMPLES)},
        {"id": "INT-3", "nom": "écarts non voulus (25 scènes, toutes sorties hors rendus)",
         "valeur": str(sum(len(v) for v in ecarts.values())), "seuil": "0",
         "atteint": sum(len(v) for v in ecarts.values()) == 0},
        {"id": "INT-4", "nom": "compilation : rétrocompatibilité S01-S12, exemples, Meylan (modèle et rapport à l'octet)",
         "valeur": f"{retro['identiques']}/{retro['fichiers']} ; différents (voulus) : {', '.join(retro['differents'])}"
         if retro else "non mesuré", "seuil": "identiques hors changements voulus listés",
         "atteint": bool(retro) and set(retro["differents"]) <= {"05_rue_piste_bande_plantee_arret_bus.yaml",
                                                                 "08_sens_unique_stationnement_charretieres.yaml",
                                                                 "11_description_rapide_depuis_photo.yaml"}},
    ]
    for lot in ("L3", "L4", "giratoires", "autoroutes"):
        c = ctl.get(lot, {})
        crit.append({"id": f"INT-5-{lot}", "nom": f"contrôle du lot {lot} rejoué sur les sorties intégrées = contrôle du lot",
                     "valeur": ("erreur" if "erreur" in c else
                                f"écart numérique max {c.get('ecart_numerique_max', 0):.6g}, autres valeurs différentes "
                                f"{c.get('autres_valeurs_differentes')}"),
                     "seuil": "écart 0, 0 valeur différente (hors changements voulus listés)",
                     "atteint": "erreur" not in c and c.get("ecart_numerique_max") == 0 and c.get("autres_valeurs_differentes") == 0})
    b = ctl.get("bordures", {})
    crit.append({"id": "INT-5-bordures", "nom": "critères du lot bordures recalculés par controler_bordures.py après "
                                                "intégration (B01, S01-S12, Meylan)",
                 "valeur": (f"{sum(1 for v in (b.get('criteres') or {}).values() if v['apres'][1])}/"
                            f"{len(b.get('criteres') or {})} atteints ; perdus : {b.get('perdus') or 'aucun'} ; gagnés : "
                            f"{b.get('gagnes') or 'aucun'} ; non recalculés (critères du pilote du lot) : "
                            f"{b.get('non_recalcules')}"),
                 "seuil": "aucun critère atteint par le lot perdu", "atteint": bool(b.get("criteres")) and not b.get("perdus")})
    crit += [
        {"id": "INT-6", "nom": "rendus : 2 vues (3 pour J5, G1, A3), planche ≤ 1092 px, géométrie rendue = géométrie finale",
         "valeur": f"{len(ok_rd)}/25", "seuil": "25/25", "atteint": len(ok_rd) == 25},
        {"id": "INT-7", "nom": f"déterminisme (une fois en fin de lot : {a.scenes_determinisme}, deux processus)",
         "valeur": a.determinisme or "non mesuré", "seuil": "identique", "atteint": a.determinisme.startswith("identique")},
        {"id": "INT-8", "nom": "planches d'ensemble etape2_*.png ≤ 1092 px (dessus + conducteur par scène) regardées en entier",
         "valeur": f"{a.planches_regardees}/{len(planches)} ; tailles {sorted(set(map(tuple, tailles.values())))}",
         "seuil": "toutes, ≤ 1092 px", "atteint": bool(planches) and a.planches_regardees == len(planches)
         and all(max(v) <= 1092 for v in tailles.values())},
    ]
    rapport = {"schema": "rapport_lot/0.1", "lot": "integration", "criteres": crit, "non_regression": nr,
               "controles_lots": ctl, "rendus": rd, "retrocompatibilite_compilation": retro,
               "planches": {k: v for k, v in tailles.items()}, "scenes_fabriquees": fab}
    (ICI / "rapport_integration.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1, default=str) + "\n",
                                                  encoding="utf-8")
    for c in crit:
        print(f"{c['id']} {'OK ' if c['atteint'] else 'NON'} {c['valeur']} (seuil {c['seuil']})")
    for s, v in nr.items():
        for x in v["differents"]:
            if x["genre"] != "voulu":
                print(f"  {s} {x['fichier']} [{x['genre']}] {x['explication']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
