"""Pilote du générateur de routes (hython Houdini 22) : description simple ou modèle -> fabrication par les HDA rg::*.

    hython recon/generateur/fabriquer_generateur.py ENTREE [ENTREE ...] [--sortie DOSSIER] [--construire-hda]
                                                    [--verifier-determinisme] [--hip] [--vex-jit]
                                                    [--l2] [--l2b] [--rendus] [--complet] [--vues V1,V2]

Étape 2 (intégration, 18/10/2026) : une seule commande, description -> rendu, quel que soit le type de scène :
    hython recon/generateur/fabriquer_generateur.py SCENE.yaml ... --complet      (= --l2b --rendus)
Avec --l2b, la chaîne est choisie d'après le modèle compilé (familles()) : rue ou route seule (chaîne de l'étape 1,
inchangée) ; carrefours plans (lots L3 et L4 : rg::carrefours, rg::carrefours_sol, rg::marquages_carrefour) ;
giratoires (L3 + L5 : rg::giratoires, rg::giratoires_sol) ; autoroutes et bretelles (rg::autoroute) ; familles
composées entre elles. Les pilotes des lots (fabriquer_carrefours.py, fabriquer_marquages_carrefour.py,
fabriquer_giratoires.py, fabriquer_autoroutes.py) servent de bibliothèques (insertions dans le réseau, exports,
caméras). Sorties en plus de l1/, l2/, l2b/ : l3/, l4/, l5/, autoroute/ ; rendus : 2 vues (dessus, conducteur
1,20 m), 3 pour J5, G1, A3 (+ oblique 3/4), planche <= 1092 px. Documentation : hda/README_RG.md § 14.

ENTREE : une description simple (.yaml, FORMAT_DESCRIPTION.md), compilée d'abord par
description/description_vers_modele.py (modele_voie.json et compilation.json dans recon/out/generateur/<scene>/),
ou un modèle modele_voie/0.1 (.json) déjà écrit (inférence OSM, scène décrite à la main).

Lot L1 (PLAN_GENERATEUR § 3) : rg::lire_modele -> rg::graphe -> rg::profils, sorties en courbes de contrôle :
    <sortie>/<scene>/l1/courbes_controle.json   références échantillonnées, limites (s, t, x, y), rubans (aires),
                                                profils d'extrémité, profil en long, nœuds, contrôles Houdini
    <sortie>/<scene>/l1/manifest_l1.json        entrée, modèle (sha256), signatures des HDA, paramètres, comptes,
                                                empreintes des fichiers écrits
    <sortie>/<scene>/l1/generateur_l1.hiplc     scène Houdini (option --hip, inspection interactive)
Sortie par défaut : recon/out/generateur/ (non versionné). Aucune date ni durée n'est écrite dans les fichiers :
deux exécutions donnent les mêmes octets (--verifier-determinisme relance un second processus et compare).

Le pilote se relance avec HOUDINI_VEX_DISABLE_JIT=1 (VEX interprété, déterministe, README_HDA § 9.2) et avec les
dossiers temporaires sur D: (recon/generateur/tmp/hython) : rien n'est écrit sur C:.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent                 # recon/generateur
DEPOT = ICI.parents[1]
TMP = ICI / "tmp" / "hython"
SORTIE_DEFAUT = DEPOT / "recon" / "out" / "generateur"

if os.environ.get("RG_PILOTE_ENV") != "1":
    TMP.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, RG_PILOTE_ENV="1", PYTHONDONTWRITEBYTECODE="1", TEMP=str(TMP), TMP=str(TMP),
               HOUDINI_TEMP_DIR=str(TMP).replace("\\", "/"))
    if "--vex-jit" not in sys.argv:
        env["HOUDINI_VEX_DISABLE_JIT"] = "1"
    sys.exit(subprocess.call([sys.executable] + sys.argv, env=env))

import tempfile  # noqa: E402

tempfile.tempdir = str(TMP)
import hou  # noqa: E402

sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI / "hda" / "commun"))
import rg_hda_outils as R  # noqa: E402

if __name__ == "__main__":                             # les pilotes des lots importent fabriquer_generateur :
    sys.modules.setdefault("fabriquer_generateur", sys.modules[__name__])   # un seul module

HDAS = ("lire_modele", "graphe", "profils")
HDAS_L2 = ("nivellement", "sol", "vers_entites")


GARDER_ENV = ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "HOMEDRIVE",
              "HOMEPATH", "USERNAME", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "TEMP", "TMP")


def env_systeme():
    """Environnement propre pour le Python du système : sans les variables de Houdini (sinon le Python 3.11 charge la
    bibliothèque standard du Python 3.13 de Houdini) ; PATH sans les dossiers de Houdini."""
    env = {k: os.environ[k] for k in GARDER_ENV if k in os.environ}
    env["PATH"] = os.pathsep.join(p for p in os.environ.get("PATH", "").split(os.pathsep)
                                  if "side effects" not in p.lower() and "sideef" not in p.lower())
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    return env


def python_systeme():
    """Python du système (description -> modèle ; le validateur exige jsonschema) : RG_PYTHON, sinon le premier
    python du PATH hors de Houdini (dans hython, « python » désigne le Python 3.13 de Houdini, sans jsonschema)."""
    import shutil
    if os.environ.get("RG_PYTHON"):
        return os.environ["RG_PYTHON"]
    env = env_systeme()
    for nom in ("python", "python3"):
        exe = shutil.which(nom, path=env["PATH"])
        if exe and subprocess.run([exe, "-c", "import jsonschema"], capture_output=True, env=env).returncode == 0:
            return exe
    raise SystemExit("Python du système avec jsonschema introuvable : définir RG_PYTHON")
VERSION_PILOTE = "fabriquer_generateur/1.0 (lot L1)"
VERSION_PILOTE_L2 = "fabriquer_generateur/1.1 (lots L1 et L2)"
VERSION_PILOTE_L2B = "fabriquer_generateur/1.2 (lots L1, L2 et L2b)"


def sha256(chemin):
    return hashlib.sha256(Path(chemin).read_bytes()).hexdigest()


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(DEPOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def construire_hda(forcer=False, l2=False):
    import importlib.util
    chemins = {}
    for nom in HDAS + (HDAS_L2 if l2 else ()):
        d = ICI / "hda" / f"rg_{nom}"
        cible = d / f"rg_{nom}.hdalc"
        if forcer or not cible.exists():
            spec = importlib.util.spec_from_file_location(f"construire_rg_{nom}", d / "construire.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cible = mod.construire(d)
        else:
            hou.hda.installFile(str(cible))
        chemins[nom] = cible
    return {f"rg::{n}::{R.VERSION}": R.signature(c) for n, c in chemins.items()}


def preparer_entree(entree, sortie):
    """(scène, chemin du modèle, info de compilation) ; une description .yaml est compilée d'abord."""
    entree = Path(entree).resolve()
    if entree.suffix.lower() in (".yaml", ".yml"):
        # compilation par le Python du système : le validateur exige jsonschema, absent du Python de hython (rien
        # n'est installé sur C:) ; sortie par défaut du compilateur : recon/out/generateur/<scene>/
        r = subprocess.run([python_systeme(), "-B", str(ICI / "description" / "description_vers_modele.py"),
                            str(entree)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=env_systeme(), cwd=str(DEPOT))
        lignes = [x for x in r.stdout.splitlines() if " → " in x]
        if r.returncode or not lignes or " 0 erreur(s) de validation" not in lignes[-1]:
            raise SystemExit(f"{entree.name} : compilation en échec\n{r.stdout}\n{r.stderr}")
        dossier = Path(lignes[-1].split(" → ")[-1].strip())
        if not dossier.is_absolute():
            dossier = DEPOT / dossier
        scene = lignes[-1].split(" : ")[0].strip()
        # contrôles de conformité du compilateur : un contrôle non conforme ou hors plage non admis par la
        # description (ecarts_admis) bloque la fabrication, comme une erreur de validation (commun/conformite.py)
        from commun import conformite as CF
        comp = json.loads((dossier / "compilation.json").read_text(encoding="utf-8"))
        if CF.erreurs(comp) or CF.bloquants(comp):
            raise SystemExit(f"{entree.name} : fabrication refusée\n{CF.resume(comp)}")
        return scene, dossier / "modele_voie.json", {"description": rel(entree), "sha256_description": sha256(entree),
                                                     "compilation": rel(dossier / "compilation.json")}
    m = json.loads(entree.read_text(encoding="utf-8"))
    scene = (m.get("meta") or {}).get("zone") or entree.parent.name
    return scene, entree, {"modele": rel(entree)}


def reseau():
    obj = hou.node("/obj/generateur_l1") or hou.node("/obj").createNode("geo", "generateur_l1")
    for c in obj.children():
        c.destroy()
    lire = obj.createNode(R.nom_type("lire_modele"), "lire_modele")
    graphe = obj.createNode(R.nom_type("graphe"), "graphe")
    for k, src in enumerate((0, 4, 3, 1)):
        graphe.setInput(k, lire, src)
    prof = obj.createNode(R.nom_type("profils"), "profils")
    prof.setInput(0, graphe, 0)
    prof.setInput(1, lire, 4)
    prof.setInput(2, lire, 3)
    prof.setDisplayFlag(True)
    obj.layoutChildren()
    return lire, graphe, prof


def _r(x, n=6):
    v = round(float(x), n)
    return 0.0 if v == 0 else v


def _pur(v):
    """Valeur d'attribut Houdini -> JSON (vecteurs en listes, dictionnaires triés)."""
    if isinstance(v, dict):
        return {str(k): _pur(v[k]) for k in sorted(v)}
    if isinstance(v, (list, tuple)) or type(v).__name__.startswith("Vector"):
        return [_pur(x) for x in v]
    if isinstance(v, float):
        return _r(v, 6)
    return v


def _local(p):
    return _r(p[0]), _r(-p[2])


def _attr(o, nom, defaut=None):
    try:
        return o.attribValue(nom)
    except hou.OperationFailed:
        return defaut


def extraire(lire, graphe, prof):
    g_ref = graphe.geometry(0)
    g_noe = graphe.geometry(1)
    g_lim = prof.geometry(0)
    g_ban = prof.geometry(1)
    g_ext = prof.geometry(2)
    g_pl = prof.geometry(3)
    routes = {}
    for pr in g_ref.prims():
        pts = pr.points()
        rid = pr.attribValue("id")
        routes[rid] = {"id": rid, "longueur_m": _r(pr.attribValue("longueur_m")),
                       "geometrie_reguliere": int(pr.attribValue("geometrie_reguliere")),
                       "n_echantillons": pr.attribValue("n_echantillons"),
                       "n_obligatoires": pr.attribValue("n_obligatoires"),
                       "pas_min_m": _r(pr.attribValue("pas_min_m")),
                       "fleche_majorant_m": _r(pr.attribValue("fleche_majorant_m"), 9),
                       "sections_modele": [{"s0": _r(a), "s1": _r(b), "profil": p, "transition_entree": t}
                                           for a, b, p, t in zip(pr.attribValue("sec_s0"), pr.attribValue("sec_s1"),
                                                                 pr.attribValue("sec_profil"),
                                                                 pr.attribValue("sec_transition"))],
                       "reference": {"s": [_r(p.attribValue("s")) for p in pts],
                                     "x": [_local(p.position())[0] for p in pts],
                                     "y": [_local(p.position())[1] for p in pts],
                                     "cap_rad": [_r(p.attribValue("cap_rad"), 9) for p in pts],
                                     "courbure": [_r(p.attribValue("courbure"), 9) for p in pts],
                                     "obligatoire": [p.attribValue("obligatoire") for p in pts]},
                       "sections": {}, "extremites": {}, "profil_long": None}
    for pr in g_lim.prims():
        rid = pr.attribValue("route")
        k = pr.attribValue("section")
        sec = routes[rid]["sections"].setdefault(k, {"indice": k, "s0": _r(pr.attribValue("s0")),
                                                     "s1": _r(pr.attribValue("s1")),
                                                     "profil": pr.attribValue("profil"),
                                                     "transition_entree": pr.attribValue("transition_entree"),
                                                     "s": None, "limites": [], "bandes": {}})
        pts = pr.points()
        if sec["s"] is None:
            sec["s"] = [_r(p.attribValue("s")) for p in pts]
        sec["limites"].append({"indice": pr.attribValue("limite"), "cle": pr.attribValue("cle"),
                               "nature": pr.attribValue("nature"), "bordure": pr.attribValue("bordure"),
                               "vue_m": _r(pr.attribValue("vue_m")), "est_reference": pr.attribValue("est_reference"),
                               "t": [_r(p.attribValue("t")) for p in pts],
                               "x": [_local(p.position())[0] for p in pts],
                               "y": [_local(p.position())[1] for p in pts]})
    for pr in g_ban.prims():
        rid = pr.attribValue("route")
        sec = routes[rid]["sections"][pr.attribValue("section")]
        b = sec["bandes"].setdefault(pr.attribValue("rang"), {
            "rang": pr.attribValue("rang"), "id": pr.attribValue("bande"), "type": pr.attribValue("type"),
            "sens": pr.attribValue("sens"), "materiau_id": pr.attribValue("materiau_id"),
            "niv_reference": pr.attribValue("niv_reference"), "largeur_min_m": _r(pr.attribValue("largeur_min_m")),
            "largeur_max_m": _r(pr.attribValue("largeur_max_m")), "n_quads": 0, "aire_m2": 0.0,
            "quads_normale_y_negative": 0})
        b["n_quads"] += 1
        b["aire_m2"] += pr.intrinsicValue("measuredarea")
        if pr.normal()[1] < 0 and pr.intrinsicValue("measuredarea") > 1e-9:
            b["quads_normale_y_negative"] += 1
    for pr in g_ext.prims():
        rid = pr.attribValue("route")
        routes[rid]["extremites"][pr.attribValue("extremite")] = {
            "noeud": pr.attribValue("noeud"), "x": [_local(p.position())[0] for p in pr.points()],
            "y": [_local(p.position())[1] for p in pr.points()]}
    for pr in g_pl.prims():
        pts = pr.points()
        routes[pr.attribValue("route")]["profil_long"] = {"s": [_r(p.attribValue("s")) for p in pts],
                                                          "dz": [_r(p.attribValue("dz_chaussee")) for p in pts]}
    sortie_routes = []
    for rid in sorted(routes):
        r = routes[rid]
        secs = []
        for k in sorted(r["sections"]):
            s = r["sections"][k]
            s["limites"].sort(key=lambda l: l["indice"])
            s["bandes"] = [dict(b, aire_m2=_r(b["aire_m2"])) for _, b in sorted(s["bandes"].items())]
            secs.append(s)
        r["sections"] = secs
        sortie_routes.append(r)
    noeuds = [{"id": p.attribValue("id"), "branches": list(p.attribValue("branches")),
               "extremites": list(p.attribValue("extremites")),
               "azimuts_deg": [_r(a, 4) for a in p.attribValue("azimuts_deg")], "valence": p.attribValue("valence")}
              for p in g_noe.points()]
    d = {}
    for nom in ("rg_n_sections", "rg_n_limites", "rg_n_rubans", "rg_largeur_min_m", "rg_largeurs_negatives",
                "rg_largeurs_nulles_hors_biseau", "rg_extremites_de_biseau", "rg_replis", "rg_sections_non_contigues",
                "rg_jonctions_discontinues", "rg_jonction_ecart_max_m", "rg_tolerance_continuite_m"):
        v = g_lim.attribValue(nom)
        d[nom[3:]] = _r(v, 9) if isinstance(v, float) else v
    d["jonctions"] = [{"route": a, "s": _r(b), "ecart_m": _r(c, 9), "instantanee": bool(e), "bande": f}
                      for a, b, c, e, f in zip(g_lim.attribValue("rg_jonction_route"), g_lim.attribValue("rg_jonction_s"),
                                               g_lim.attribValue("rg_jonction_ecart_m"),
                                               g_lim.attribValue("rg_jonction_instantanee"),
                                               g_lim.attribValue("rg_jonction_bande"))]
    graphe_param = {"fleche_max_m": _r(g_ref.attribValue("rg_graphe_fleche_max_m"), 9),
                    "marge": _r(g_ref.attribValue("rg_graphe_marge"), 6),
                    "pas_max_m": _r(g_ref.attribValue("rg_graphe_pas_max_m")),
                    "rampe_plateau_pct": _r(g_ref.attribValue("rg_rampe_plateau_pct"))}
    modele = lire.geometry(0).attribValue("rg_modele")
    comptes = {"routes": len(sortie_routes), "points_references": len(g_ref.points()),
               "limites": len(g_lim.prims()), "points_limites": len(g_lim.points()), "rubans": len(g_ban.prims()),
               "extremites": len(g_ext.prims()), "noeuds": len(noeuds)}
    return {"routes": sortie_routes, "noeuds": noeuds, "controles_houdini": d, "parametres": graphe_param,
            "rg_modele": {k: _pur(modele[k]) for k in ("schema", "sha256", "comptes", "non_lus", "origine_l93")},
            "comptes": comptes}


def avertissements(*noeuds):
    from commun import determinisme as DET
    return DET.avertissements_stables(noeuds)


# ------------------------------------------------------------------------------------------------------- étape 2
# Chaîne de réseau (intégration de l'étape 2) : les pilotes des lots (fabriquer_carrefours.py : L3, carrefours plans ;
# fabriquer_marquages_carrefour.py : L4, marquages, trajectoires et conflits des carrefours plans ; fabriquer_giratoires.py :
# L5, giratoires ; fabriquer_autoroutes.py : séparateurs, bretelles et musoirs) sont des bibliothèques : leurs
# insertions dans le réseau et leurs exports sont composés ici, d'après les familles d'objets du modèle.
VERSION_PILOTE_RESEAU = "fabriquer_generateur/2.0 (étape 2 : routes, carrefours plans, giratoires, autoroutes)"
VUES_SIMPLES = ("dessus", "conducteur")
SCENES_PHARES = ("J5_carrefour_complexe", "G1_giratoire_urbain_D40", "A3_bretelle_entree")
TYPES_GIRATOIRE = ("giratoire", "mini_giratoire")
TYPES_CARREFOUR_PLAN = ("plan_simple", "plan_ilots", "plan_feux")
SEPARATEURS_AUTOROUTE = ("GBA", "DBA", "LBA", "MVL", "glissiere")
HDA_RESEAU = {"carrefours": (("rg_carrefours", ("carrefours", "carrefours_sol")),
                             ("rg_marquages_carrefour", ("marquages_carrefour",))),
              "giratoires": (("rg_carrefours", ("carrefours", "carrefours_sol")),
                             ("rg_giratoires", ("giratoires", "giratoires_sol"))),
              "autoroute": (("rg_autoroute", ("autoroute",)),)}
TMP_RESEAU = ICI / "tmp" / "reseau"



def _reseau_simple(l2, l2b, signatures, construire, reglages):
    """Réseau de la chaîne simple (lots L1, L2, L2b ; étape 1, inchangé) : (lire, graphe, prof, n2, n2b, sig_l2, sig_l2b)."""
    lire, graphe, prof = reseau()
    noeuds_l2 = noeuds_l2b = None
    sig_l2 = sig_l2b = None
    if l2:
        import fabriquer_l2 as F2
        sig_pj = F2.installer_pj()
        noeuds_l2 = F2.reseau(lire.parent(), lire, graphe, R.nom_type)
        sig_l2 = {k: v for k, v in signatures.items()}
        sig_l2.update(sig_pj)
    if l2b:
        import fabriquer_l2b as F2B
        sig_l2b = dict(sig_l2)
        sig_l2b.update(F2B.construire_hda(forcer=construire))
        noeuds_l2b = F2B.reseau(lire.parent(), lire, graphe, noeuds_l2)
    for nom, v in (reglages or {}).items():          # paramètres de rg::graphe (témoins du rapport L1)
        if v is not None:
            graphe.parm(nom).set(v)
    return lire, graphe, prof, noeuds_l2, noeuds_l2b, sig_l2, sig_l2b


def fabriquer(entrees, sortie, signatures, hip=False, reglages=None, l2=False, rendus=False, l2b=False,
              construire=False, decor_etape2=False, vues=VUES_SIMPLES):
    """Fabrique chaque entrée. Avec --l2b, la chaîne est choisie d'après le modèle (familles()) : chaîne simple de
    l'étape 1 (rue, route : inchangée) ou chaîne de réseau (carrefours plans, giratoires, autoroutes et bretelles,
    composées entre elles). Sans --l2b : lots L1 (et L2) de l'étape 1, quel que soit le modèle."""
    preparees = [preparer_entree(e, sortie) for e in entrees]      # compilation d'abord (refus avant toute fabrication)
    fams = [familles(json.loads(Path(c).read_text(encoding="utf-8"))) if l2b else () for _, c, _ in preparees]
    sig_reseau = None
    if any(fams):
        sig_reseau = construire_hda_reseau(signatures, forcer=construire)
    produits = []
    for e, (scene, chemin_modele, info), fam in zip(entrees, preparees, fams):
        # réseau reconstruit pour CHAQUE scène (correction après le contrôle de l'étape 2 : les nœuds réutilisés d'une
        # scène à l'autre transmettaient leur état, d'où des avertissements de pj::marquage_solide qui dépendaient de
        # l'ordre des scènes dans le processus) ; les HDA ne sont installées qu'une fois
        if fam:
            noeuds = reseau_complet(fam)
            produits.append(fabriquer_scene_reseau(noeuds, fam, scene, chemin_modele, info, e, sortie,
                                                   signatures_familles(sig_reseau, fam), rendus=rendus,
                                                   decor_etape2=decor_etape2))
            continue
        simple = _reseau_simple(l2, l2b, signatures, construire and not produits, reglages)
        lire, graphe, prof, noeuds_l2, noeuds_l2b, sig_l2, sig_l2b = simple
        if l2:
            import fabriquer_l2 as F2
        if l2b:
            import fabriquer_l2b as F2B
        dossier = Path(sortie) / scene / "l1"
        dossier.mkdir(parents=True, exist_ok=True)
        lire.parm("fichier").set(str(chemin_modele).replace("\\", "/"))
        for n in (lire, graphe, prof):
            try:
                n.cook(force=True)
            except hou.OperationFailed:
                pass
            err = [f"{c.path()} : {e}" for c in (n,) + n.allSubChildren() for e in c.errors()]
            if err:
                raise SystemExit(f"{scene} : erreurs de cuisson" + chr(10) + chr(10).join(err))
        donnees = extraire(lire, graphe, prof)
        courbes = {"schema": "rg_courbes_controle/0.1", "scene": scene, "lot": "L1",
                   "modele": {"fichier": rel(chemin_modele), "sha256": sha256(chemin_modele)}}
        courbes.update(donnees)
        f_courbes = dossier / "courbes_controle.json"
        f_courbes.write_text(json.dumps(courbes, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")
        fichiers = {"courbes_controle.json": sha256(f_courbes)}
        if hip:
            f_hip = dossier / "generateur_l1.hiplc"
            hou.hipFile.save(str(f_hip))
        manifeste = {"schema": "rg_manifest/0.1", "pilote": VERSION_PILOTE, "scene": scene, "entree": info,
                     "modele": courbes["modele"], "houdini": hou.applicationVersionString(),
                     "vex_jit": os.environ.get("HOUDINI_VEX_DISABLE_JIT") != "1",
                     "hda": {k: v for k, v in signatures.items() if k.split("::")[1] in HDAS},
                     "parametres": donnees["parametres"], "comptes": donnees["comptes"],
                     "controles_houdini": {k: v for k, v in donnees["controles_houdini"].items() if k != "jonctions"},
                     "avertissements": sorted(set(avertissements(lire, graphe, prof))), "fichiers": fichiers}
        (dossier / "manifest_l1.json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=1) + "\n",
                                                  encoding="utf-8")
        if noeuds_l2 is not None:
            d2, man2 = F2.fabriquer_scene(noeuds_l2, scene, Path(sortie) / scene, sig_l2, info)
            ch = man2["controles_houdini"]
            print(f"{scene} : L2 sol {ch['faces_sol']} faces ({ch['murs']} murs, {ch['aretes_sans_paire']} arêtes de bord), "
                  f"bordures {ch['faces_bordures']} faces, caniveaux {ch['faces_caniveaux']} faces -> {rel(d2)}")
            if noeuds_l2b is not None:
                d2b, man2b = F2B.fabriquer_scene(noeuds_l2b, scene, Path(sortie) / scene, sig_l2b, info)
                c2b = man2b["comptes"]
                print(f"{scene} : L2b {c2b['empreintes']['empreintes']} empreintes, {c2b['empreintes']['marques']} marques, "
                      f"peinture {c2b['peinture']['faces']} faces ({c2b['peinture']['entites']} entités) -> {rel(d2b)}")
            if rendus and noeuds_l2b is not None:
                rendre_simple(noeuds_l2, noeuds_l2b, scene, Path(sortie) / scene, lire.parent(), e, vues,
                              decor_etape2=decor_etape2)
            elif rendus:
                import rendu_scenes as RS
                RS.rendre_scene(noeuds_l2, scene, Path(sortie) / scene, lire.parent())
        c = donnees["controles_houdini"]
        print(f"{scene} : {donnees['comptes']['routes']} route(s), {c['n_sections']} section(s), "
              f"{c['n_limites']} limites, {c['n_rubans']} rubans ; largeur min {c['largeur_min_m']:.4f} m, "
              f"jonctions discontinues {c['jonctions_discontinues']} -> {rel(dossier)}")
        produits.append(str(dossier))
    return produits


def familles(modele):
    """Familles d'objets de réseau du modèle : « carrefours » (carrefours plans : plan_simple, plan_ilots, plan_feux),
    « giratoires » (giratoire, mini_giratoire), « autoroute » (bifurcation de bretelle, ou séparateur DBA / GBA / LBA /
    MVL / glissière posé par rg::autoroute). Aucune : chaîne simple de l'étape 1."""
    types = {c.get("type") for c in modele.get("carrefours") or []}
    f = []
    if types & set(TYPES_CARREFOUR_PLAN):
        f.append("carrefours")
    if types & set(TYPES_GIRATOIRE):
        f.append("giratoires")
    seps = {(lim.get("separateur") or {}).get("type") for p in modele.get("profils") or []
            for lim in p.get("limites") or []}
    if "bifurcation" in types or seps & set(SEPARATEURS_AUTOROUTE):
        f.append("autoroute")
    inconnus = sorted(t for t in types if t not in TYPES_CARREFOUR_PLAN + TYPES_GIRATOIRE + ("bifurcation",))
    if inconnus:
        raise SystemExit(f"type de carrefour sans chaîne de fabrication : {inconnus}")
    return tuple(f)


def _charger_construire(dossier):
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"construire_{dossier}", ICI / "hda" / dossier / "construire.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def construire_hda_reseau(signatures, forcer=False):
    """HDA de toute la chaîne : L1, L2 (signatures), pj::* (F2.installer_pj), rg::marquages (L2b) et HDA de réseau
    (rg::carrefours, rg::carrefours_sol, rg::marquages_carrefour, rg::giratoires, rg::giratoires_sol, rg::autoroute) ;
    une HDA de réseau absente (ou --construire-hda) est construite, sinon installée telle quelle."""
    import fabriquer_l2 as F2
    import fabriquer_l2b as F2B
    sigs = dict(signatures)
    sigs.update(F2.installer_pj())
    sigs.update(F2B.construire_hda(forcer=forcer))
    faits = set()
    for fam in ("carrefours", "giratoires", "autoroute"):
        for dossier, noms in HDA_RESEAU[fam]:
            if dossier in faits:
                continue
            faits.add(dossier)
            cibles = [ICI / "hda" / dossier / f"rg_{n}.hdalc" for n in noms]
            if forcer or not all(c.exists() for c in cibles):
                res = _charger_construire(dossier).construire(ICI / "hda" / dossier)
                cibles = list(res) if isinstance(res, (tuple, list)) else [res]
            else:
                for c in cibles:
                    hou.hda.installFile(str(c))
            for n, c in zip(noms, cibles):
                sigs[f"rg::{n}::{R.VERSION}"] = R.signature(c)
    return sigs


def signatures_familles(sigs, fam):
    """Signatures des HDA utilisées par une scène : chaîne simple + HDA de ses familles."""
    reseau_ = {f"rg::{n}::{R.VERSION}" for f, v in HDA_RESEAU.items() for _, noms in v for n in noms}
    utiles = {f"rg::{n}::{R.VERSION}" for f in fam for _, noms in HDA_RESEAU[f] for n in noms}
    return {k: v for k, v in sigs.items() if k not in reseau_ or k in utiles}


def reseau_complet(fam):
    """Réseau d'une scène de réseau, composé d'après ses familles :
        carrefours / giratoires : réseau du lot L3 (fabriquer_carrefours.reseau : rg::carrefours, rg::carrefours_sol) ;
          giratoires : + rg::giratoires, rg::giratoires_sol (fabriquer_giratoires.inserer) ;
          carrefours : + rg::marquages_carrefour (fabriquer_marquages_carrefour.inserer) ;
        autoroute : rg::autoroute après le sol (fabriquer_autoroutes.inserer_sol, avant L2b) et marques des musoirs
          (inserer_marques) ; seule, sur la chaîne simple L1 + L2 + L2b.
    Renvoie {lire, graphe, prof, n2, n2b, carrefours, giratoires, autoroute}."""
    import fabriquer_l2 as F2
    import fabriquer_l2b as F2B
    N = {"carrefours": None, "giratoires": None, "autoroute": None}
    if "autoroute" in fam:
        import fabriquer_autoroutes as FA
    if "carrefours" in fam or "giratoires" in fam:
        import fabriquer_carrefours as FC
        crochet = None
        if "autoroute" in fam:
            def crochet(obj, lire, graphe, prof, n2):
                FA.inserer_sol(obj, lire, graphe, prof, n2)
        lire, car, graphe, prof, n2, n2b = FC.reseau(avant_l2b=crochet)
        N["carrefours"] = car
        if "giratoires" in fam:
            import fabriquer_giratoires as FGI
            N["giratoires"] = FGI.inserer(lire, car, graphe, prof, n2, n2b)
        if "carrefours" in fam:
            import fabriquer_marquages_carrefour as FM
            FM.inserer(lire, car, graphe, prof, n2, n2b)
    else:
        lire, graphe, prof = reseau()
        obj = lire.parent()
        n2 = F2.reseau(obj, lire, graphe, R.nom_type)
        FA.inserer_sol(obj, lire, graphe, prof, n2)
        n2b = F2B.reseau(obj, lire, graphe, n2)
    if "autoroute" in fam:
        FA.inserer_marques(lire.parent(), n2, n2b)
        N["autoroute"] = n2["autoroute"]
    if len(fam) > 1:
        print(f"composition de familles {list(fam)} : réseau composé (sans scène de contrôle dédiée à ce jour)")
    N.update(lire=lire, graphe=graphe, prof=prof, n2=n2, n2b=n2b)
    return N


def _cuire_amont(noeuds, scene):
    for n in noeuds:
        try:
            n.cook(force=True)
        except hou.OperationFailed:
            pass
        err = [f"{c.path()} : {x}" for c in (n,) + n.allSubChildren() for x in c.errors()]
        if err:
            raise SystemExit(f"{scene} : erreurs de cuisson" + chr(10) + chr(10).join(err[:20]))


def _ecrire(f, d):
    Path(f).write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _manifeste_lot(dossier, nom, schema, scene, info, signatures, extra):
    fichiers = {p.name: sha256(p) for p in sorted(Path(dossier).iterdir()) if p.is_file() and p.name != nom}
    _ecrire(Path(dossier) / nom, {"schema": schema, "pilote": VERSION_PILOTE_RESEAU, "scene": scene, "entree": info,
                                  "houdini": hou.applicationVersionString(), "hda": signatures, **extra,
                                  "fichiers": fichiers})


def _trajectoires_l4(N, scene):
    """Trajectoires finales du lot L4 (DONNÉES de rg::marquages_carrefour) et retraits des nez du solveur L3."""
    import fabriquer_marquages_carrefour as FM
    mc = N["n2b"]["marquages_carrefour"]
    _cuire_amont([N["lire"], N["carrefours"], N["graphe"], N["prof"], mc], scene)
    traj = FM._prims(mc.geometry(2), "trajectoire_l4", FM.ATTR_TRAJ)
    g = N["carrefours"].geometry(2)
    gb = g.findPointGroup("branche")
    nez = {p.attribValue("branche"): _r(p.attribValue("nez_retrait"), 6) for p in (gb.points() if gb else [])}
    return traj, nez


def empreinte_trajectoires(traj):
    """sha256 des trajectoires L4 (identifiant, points) : contrôle « une seule source » (balayages = trajectoires finales)."""
    return hashlib.sha256(json.dumps([(t["id"], t["points"]) for t in traj], sort_keys=True).encode()).hexdigest()


def balayages_trajectoires_l4(N, scene, chemin_modele, n_max=4, dossier=None):
    """Balayages du lot L3 calculés sur les trajectoires FINALES du lot L4 (correction après le contrôle de l'étape 2 :
    une seule source de trajectoires). Les nez des îlots dépendent des balayages, la fin des branches (s_end) des nez, et
    les trajectoires L4 de la fin des branches : point fixe. Passe 1 sans balayage ; chaque passe suivante reprend les
    balayages des trajectoires de la passe précédente, jusqu'à ce que les balayages ne changent plus (les trajectoires
    finales sont alors celles qui ont servi à les calculer). Renvoie (fichier, balayages, journal des passes)."""
    import fabriquer_carrefours as FC
    car = N["carrefours"]
    dossier = dossier or TMP_RESEAU / scene
    car.parm("balayages").set("")
    precedent, journal = None, []
    for k in range(n_max):
        traj, nez = _trajectoires_l4(N, scene)
        # un fichier par passe : le paramètre change, le lecteur de rg::carrefours relit les balayages
        fb, bal = FC.balayages_l4(chemin_modele, traj, dossier, nom=f"balayages_passe{k + 1}.json")
        cle = json.dumps(bal, sort_keys=True)
        journal.append({"passe": k + 1, "nez_retrait": nez, "balayages": len(bal),
                        "trajectoires": len(traj), "empreinte_trajectoires": empreinte_trajectoires(traj),
                        "identique_a_la_passe_precedente": cle == precedent})
        if cle == precedent:
            break
        precedent = cle
        car.parm("balayages").set(str(fb).replace("\\", "/"))
    else:
        print(f"{scene} : balayages L4 sans point fixe après {n_max} passes (dernière passe gardée)")
    # fichier final (même contenu que celui de la dernière passe cuite) : lu par la cuisson complète et par les contrôles
    fb, bal = FC.balayages_l4(chemin_modele, traj, dossier)
    return fb, bal, journal


def fabriquer_scene_reseau(N, fam, scene, chemin_modele, info, entree, sortie, signatures, rendus=False,
                           decor_etape2=False):
    """Une scène de réseau : L1 (routes coupées aux carrefours), L2, L2b, puis exports des familles (l3/, l4/, l5/,
    autoroute/) et rendus (2 vues ; 3 pour les scènes phares)."""
    import fabriquer_l2 as F2
    import fabriquer_l2b as F2B
    lire, graphe, prof, n2, n2b = N["lire"], N["graphe"], N["prof"], N["n2"], N["n2b"]
    car, gir, au = N["carrefours"], N["giratoires"], N["autoroute"]
    dsc = Path(sortie) / scene
    d1 = dsc / "l1"
    d1.mkdir(parents=True, exist_ok=True)
    info_bal = []
    lire.parm("fichier").set(str(chemin_modele).replace("\\", "/"))
    iter_bal = None
    # dossier temporaire des balayages propre à la sortie (deux processus vers deux sorties ne se gênent pas)
    tmp_b = TMP_RESEAU / scene if Path(sortie).resolve() == SORTIE_DEFAUT.resolve() else         TMP_RESEAU / ("_" + Path(sortie).resolve().name) / scene
    if car is not None:
        import fabriquer_carrefours as FC
        if "carrefours" in fam:
            fb, bal, iter_bal = balayages_trajectoires_l4(N, scene, chemin_modele, dossier=tmp_b)
        else:
            fb, bal = FC.balayages(chemin_modele, tmp_b)      # lot L3a : VL, bus standard 12 m
        car.parm("balayages").set(str(fb).replace("\\", "/"))
        info_bal = [{k: v for k, v in b.items() if k != "exterieur"} for b in bal]
    _cuire_amont([lire] + [x for x in (car, gir) if x is not None] + [graphe, prof], scene)
    donnees = extraire(lire, graphe, prof)
    coupes = [x for x, o in (("L3 : carrefours plans", "carrefours" in fam), ("L5 : giratoires", gir is not None)) if o]
    courbes = {"schema": "rg_courbes_controle/0.1", "scene": scene,
               "lot": "L1" + (f" (+ {', '.join(coupes)} : routes coupées)" if coupes else " (autoroutes)"),
               "modele": {"fichier": rel(chemin_modele), "sha256": sha256(chemin_modele)}}
    courbes.update(donnees)
    _ecrire(d1 / "courbes_controle.json", courbes)
    _ecrire(d1 / "manifest_l1.json", {
        "schema": "rg_manifest/0.1", "pilote": VERSION_PILOTE_RESEAU, "scene": scene, "familles": list(fam),
        "entree": info, "modele": courbes["modele"], "houdini": hou.applicationVersionString(),
        "vex_jit": os.environ.get("HOUDINI_VEX_DISABLE_JIT") != "1", "hda": signatures,
        "parametres": donnees["parametres"], "comptes": donnees["comptes"],
        "avertissements": avertissements(*[x for x in (lire, car, gir, graphe, prof) if x is not None]),
        "fichiers": {"courbes_controle.json": sha256(d1 / "courbes_controle.json")}})
    usure = None
    if gir is not None:
        import fabriquer_giratoires as FGI
        FGI.cuire(n2, scene)
    elif car is not None:
        FC.cuire(n2, scene)
    if "carrefours" in fam:
        # usure des marques du lot L4 : celle des lignes de rg::marquages (classe d'usure du modèle)
        mq = n2b["marquages"]
        try:
            mq.cook(force=True)
        except hou.OperationFailed:
            pass
        gl = mq.geometry(0)
        usure = gl.prims()[0].attribValue("usure") if gl is not None and gl.prims() else 0.0
        n2b["marquages_carrefour"].parm("usure_peinture").set(float(usure))
    if au is not None:
        _cuire_amont([au], scene)
    d2, man2 = F2.fabriquer_scene(n2, scene, dsc, signatures, info)
    d2b, man2b = F2B.fabriquer_scene(n2b, scene, dsc, signatures, info)
    resume = [f"L2 sol {man2['controles_houdini']['faces_sol']} faces, bordures "
              f"{man2['controles_houdini']['faces_bordures']} faces ; L2b {man2b['comptes']['peinture']['faces']} faces de peinture"]
    modele = json.loads(Path(chemin_modele).read_text(encoding="utf-8"))
    if car is not None:
        d3 = dsc / "l3"
        d3.mkdir(parents=True, exist_ok=True)
        c3 = FC.exporter_carrefours(n2, d3, info_bal)
        m3 = FC.mesurer_raccords(n2, d3)
        # balayages complets (enveloppes) à côté du solveur : ceux qui ont placé les nez, relus par les contrôles
        (d3 / "balayages.json").write_bytes(Path(car.parm("balayages").eval()).read_bytes()) if             car.parm("balayages").eval() else None
        extra3 = {"comptes": c3, "raccords": m3}
        if iter_bal is not None:
            extra3["balayages_passes"] = iter_bal
        _manifeste_lot(d3, "manifest_l3.json", "rg_manifest_l3/0.1", scene, info, signatures, extra3)
        resume.append(f"L3 {c3['coins']} coins, {c3['nez']} nez, raccords écart max {m3['ecart_max_m']} m, bords libres "
                      f"hors extérieur {m3['bords_libres_hors_exterieur']}")
    if "carrefours" in fam:
        import fabriquer_marquages_carrefour as FM
        d4 = dsc / "l4"
        d4.mkdir(parents=True, exist_ok=True)
        c4 = FM.exporter_l4(n2b, car.geometry(2), d4, modele, scene)
        if iter_bal:
            # une seule source : les trajectoires finales sont celles dont les balayages ont placé les nez
            fin = empreinte_trajectoires(FM._prims(n2b["marquages_carrefour"].geometry(2), "trajectoire_l4", FM.ATTR_TRAJ))
            c4["trajectoires_balayees_identiques"] = fin == iter_bal[-1]["empreinte_trajectoires"]
            if not c4["trajectoires_balayees_identiques"]:
                print(f"{scene} : ATTENTION trajectoires finales différentes de celles des balayages")
        m4 = FM.mesurer_peinture(n2b, d4)
        _manifeste_lot(d4, "manifest_l4.json", "rg_manifest_l4/0.1", scene, info, signatures,
                       {"comptes": c4, "peinture": m4["peinture"], "usure_peinture": _r(usure)})
        resume.append(f"L4 {c4['trajectoires']} trajectoires, {c4['conflits']} conflits, {c4['marques_l4']} marques")
    if gir is not None:
        d5 = dsc / "l5"
        d5.mkdir(parents=True, exist_ok=True)
        c5 = FGI.exporter_giratoires(n2, d5)
        m5 = FGI.mesurer_ilots(n2, d5)
        _manifeste_lot(d5, "manifest_l5.json", "rg_manifest_l5/0.1", scene, info, signatures, {"comptes": c5, "ilots": m5})
        resume.append(f"L5 {c5['giratoires']} giratoire(s), {c5['faces']} faces d'îlot, {c5['bev']} BEV")
    if au is not None:
        import fabriquer_autoroutes as FA
        da = dsc / "autoroute"
        ca = FA.exporter_autoroute(au, da)
        _manifeste_lot(da, "manifest_autoroute.json", "rg_manifest_autoroute/0.1", scene, info, signatures,
                       {"comptes": ca, "avertissements": sorted({w for c in (au,) + au.allSubChildren() for w in c.warnings()
                                                                if "mis-match of attributes" not in w})})
        resume.append(f"autoroute {ca['separateurs']} séparateur(s), {ca['musoirs']} musoir(s)")
    print(f"{scene} [{', '.join(fam)}] : " + " ; ".join(resume) + f" -> {rel(dsc)}")
    if rendus:
        rendre_reseau(N, fam, scene, dsc, modele, decor_etape2=decor_etape2)
    return str(d1)


LEGENDES = {"conducteur_carrefour": "conducteur (1,20 m)", "oblique_carrefour": "vue oblique 3/4 du carrefour",
            "conducteur_ouest_tag": "conducteur (1,20 m), artère ouest, voie de tourne-à-gauche",
            "conducteur": "conducteur (1,20 m)"}


def _rendre(n2, n2b, scene, dsc, parent, propres, noms, centre=None, largeur=None, legendes=None, res_dessus=None,
            sujet=None, decor_etape2=False):
    """Rendu Karma (rendu_l2b.rendre_scene) des seules vues noms ; vue de dessus centrée (centre, largeur) si donnés ;
    planche ≤ 1092 px de ces vues (planches.planche_vues)."""
    import rendu_l2b as RB
    import planches as PL
    dessus_origine, resd0 = RB._dessus, RB.RES_DESSUS
    if sujet is not None:
        RB.SUJET[scene] = sujet

    def dessus(stage, c, z, larg, res):
        return dessus_origine(stage, centre if centre is not None else c, z, largeur or larg, res)
    RB._dessus = dessus
    if res_dessus:
        RB.RES_DESSUS = tuple(res_dessus)
    try:
        RB.rendre_scene(n2, n2b, scene, dsc, parent, vues=propres or None, decor_etape2=decor_etape2,
                        seulement=list(noms))
    finally:
        RB._dessus, RB.RES_DESSUS = dessus_origine, resd0
    d = Path(dsc) / "rendus"
    pngs = {p.stem: p for p in d.glob("*.png") if not p.stem.startswith("planche")}
    PL.planche_vues(scene, pngs, [v for v in noms if v in pngs], d / f"planche_{scene}.png", legendes=legendes)
    return [v for v in noms if v in pngs]


def vues_description(entree):
    """Vues propres d'une description (<scene>.vues.json à côté du .yaml, lot bordures) : dessus (largeur, résolution),
    abscisse du sujet."""
    j = Path(entree).with_suffix(".vues.json")
    if Path(entree).suffix.lower() not in (".yaml", ".yml") or not j.exists():
        return {}
    return json.loads(j.read_text(encoding="utf-8"))


def rendre_simple(n2, n2b, scene, dsc, parent, entree, vues=VUES_SIMPLES, decor_etape2=False):
    """Rendus d'une scène de la chaîne simple : vues demandées (défaut : dessus et conducteur 1,20 m ; « toutes » :
    toutes les caméras de rendu_l2b, comme à l'étape 1) ; planche ≤ 1092 px."""
    import rendu_l2b as RB
    if tuple(vues) == ("toutes",):
        return RB.rendre_scene(n2, n2b, scene, dsc, parent, decor_etape2=decor_etape2)
    vj = vues_description(entree)
    ds = vj.get("dessus") or {}
    return _rendre(n2, n2b, scene, dsc, parent, None, vues, largeur=ds.get("largeur_m"), res_dessus=ds.get("resolution"),
                   sujet=vj.get("sujet_s"), legendes={"conducteur": "conducteur (1,20 m), voie de droite"},
                   decor_etape2=decor_etape2)


def rendre_reseau(N, fam, scene, dsc, modele, decor_etape2=False):
    """Rendus d'une scène de réseau : dessus centré sur l'objet et conducteur (1,20 m) dans une voie entrante ;
    + oblique 3/4 pour les scènes phares (J5, G1, A3). Caméras des lots (L3 / L4 : carrefours ; L5 : giratoires ;
    autoroutes : musoir)."""
    n2, n2b, graphe = N["n2"], N["n2b"], N["graphe"]
    parent = N["lire"].parent()
    phare = scene in SCENES_PHARES
    if N["giratoires"] is not None or "carrefours" in fam:
        import fabriquer_carrefours as FC
        vv = ("dessus", "conducteur", "oblique") if phare else ("dessus", "conducteur")
        if N["giratoires"] is not None:
            import fabriquer_giratoires as FGI
            propres, centre, largeur, bcond = FGI.vues_giratoire(modele, N["giratoires"].geometry(2), graphe.geometry(), vv)
        else:
            propres, centre, largeur, bcond = FC.vues_carrefour(modele, N["carrefours"].geometry(2), graphe.geometry(), vv)
        noms = ["dessus", "conducteur_carrefour"] + (["oblique_carrefour"] if phare else [])
        leg = dict(LEGENDES, conducteur_carrefour=f"conducteur (1,20 m), branche {bcond}")
        if phare and N["giratoires"] is None and scene.startswith("J5"):
            # J5 (lot L4) : conducteur dans la voie de tourne-à-gauche de l'artère ouest (guidage à l'indonésienne)
            import fabriquer_marquages_carrefour as FM
            v5 = FM.vues_j5(n2b["marquages_carrefour"].geometry(2), graphe.geometry())
            if "conducteur_ouest_tag" in v5:
                propres.pop("conducteur_carrefour", None)
                propres["conducteur_ouest_tag"] = v5["conducteur_ouest_tag"]
                noms = ["dessus", "conducteur_ouest_tag", "oblique_carrefour"]
        print(f"{scene} : rendus {noms} ; dessus {largeur:.1f} m")
        return _rendre(n2, n2b, scene, dsc, parent, propres, noms, centre=centre, largeur=largeur, legendes=leg,
                       decor_etape2=decor_etape2)
    import fabriquer_autoroutes as FA
    mus = json.loads((Path(dsc) / "autoroute" / "musoirs.json").read_text(encoding="utf-8"))["musoirs"]
    vv = ("dessus", "oblique", "conducteur") if phare else ("dessus", "conducteur")
    propres, centre, largeur, leg = FA.vues_scene(modele, graphe.geometry(), scene, mus)
    noms = [FA.NOMS.get(v, v) for v in vv]
    vp = {FA.NOMS[k]: v for k, v in propres.items() if k in FA.NOMS}
    print(f"{scene} : rendus {noms} ; dessus {largeur:.0f} m")
    return _rendre(n2, n2b, scene, dsc, parent, vp, noms, centre=centre, largeur=largeur, res_dessus=(1092, 546),
                   legendes={"dessus": f"dessus ({largeur:.0f} m de large)", "conducteur_autoroute": leg,
                             "oblique_autoroute": "vue oblique 3/4 du musoir (14 m de haut)"},
                   decor_etape2=decor_etape2)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("entrees", nargs="*", help="descriptions .yaml ou modèles .json")
    ap.add_argument("--sortie", default=str(SORTIE_DEFAUT))
    ap.add_argument("--construire-hda", action="store_true", help="reconstruire les HDA rg::* (signature inchangée : "
                                                                  "dossiers gardés tels quels)")
    ap.add_argument("--verifier-determinisme", action="store_true")
    ap.add_argument("--hip", action="store_true")
    ap.add_argument("--vex-jit", action="store_true", help="garder le JIT natif de VEX (non déterministe)")
    ap.add_argument("--fleche", type=float, help="flèche maximale de rg::graphe (m), défaut de l'HDA : 0,0005")
    ap.add_argument("--pas-max", type=float, help="pas maximal de rg::graphe (m), défaut de l'HDA : 1,0")
    ap.add_argument("--l2", action="store_true", help="lot L2 : nivellement, sol, bordures et caniveaux (sorties l2/)")
    ap.add_argument("--rendus", action="store_true", help="avec --l2 : rendus Karma XPU de contrôle (rendus/)")
    ap.add_argument("--l2b", action="store_true", help="lot L2b : marquages de la section courante (sorties l2b/) ; "
                                                       "implique --l2 ; chaîne de réseau choisie d'après le modèle "
                                                       "(carrefours, giratoires, autoroutes : sorties l3/, l4/, l5/, "
                                                       "autoroute/) ; avec --rendus : rendus et planche")
    ap.add_argument("--complet", action="store_true", help="description -> rendu, quel que soit le type de scène : "
                                                           "--l2b --rendus")
    ap.add_argument("--vues", default=",".join(VUES_SIMPLES),
                    help="vues des scènes simples (défaut : dessus,conducteur ; « toutes » : caméras de l'étape 1)")
    ap.add_argument("--decor-etape2", action="store_true",
                    help="avec --l2b --rendus : décor de l'étape 2 (arbres, prolongements, sol de décor, relief, nuages) ; "
                         "par défaut (étape 1, décision de l'utilisateur) : la route seule sur un socle neutre")
    a = ap.parse_args()
    if a.complet:
        a.l2b = a.rendus = True
    if a.l2b:
        a.l2 = True
    signatures = construire_hda(forcer=a.construire_hda, l2=a.l2)
    if a.l2b and not a.entrees:                      # construction seule : toutes les HDA (chaîne simple et réseau)
        signatures = construire_hda_reseau(signatures, forcer=a.construire_hda)
    print("HDA :", ", ".join(f"{k} ({v[:12]})" for k, v in signatures.items()))
    if not a.entrees:
        return 0
    reglages = {"fleche_max": a.fleche, "pas_max": a.pas_max}
    produits = fabriquer(a.entrees, a.sortie, signatures, hip=a.hip, reglages=reglages, l2=a.l2, rendus=a.rendus,
                         l2b=a.l2b, construire=a.construire_hda, decor_etape2=a.decor_etape2,
                         vues=tuple(v for v in a.vues.split(",") if v))
    if a.verifier_determinisme:
        autre = ICI / "tmp" / "l1" / "determinisme"
        opts = [x for k, v in (("--fleche", a.fleche), ("--pas-max", a.pas_max)) if v is not None for x in (k, str(v))]
        opts += ["--l2"] if a.l2 else []
        opts += ["--l2b"] if a.l2b else []
        r = subprocess.run([sys.executable, __file__] + a.entrees + ["--sortie", str(autre)] + opts,
                           env=dict(os.environ, RG_PILOTE_ENV=""), capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode:
            print(r.stdout[-3000:], r.stderr[-3000:])
            raise SystemExit("second processus en échec")
        from commun import determinisme as DET
        ecarts, n = DET.comparer(produits, autre, a.l2, a.l2b)
        # sorties des familles de réseau (lots L3, L4, L5, autoroutes) : JSON à l'octet, manifestes exclus (chemins)
        for p in produits:
            sc = Path(p).parent
            for lot in ("l3", "l4", "l5", "autoroute"):
                for f in sorted((sc / lot).glob("*.json")):
                    if f.name.startswith("manifest"):
                        continue
                    g = autre / sc.name / lot / f.name
                    n += 1
                    if not g.exists() or g.read_bytes() != f.read_bytes():
                        ecarts.append(f"{sc.name}/{lot}/{f.name}")
        print("déterminisme :", f"identique ({n} fichiers ; .usda : chemins relatifs des matériaux normalisés)"
              if not ecarts else f"DIFFÉRENT : {ecarts}")
        return 1 if ecarts else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
