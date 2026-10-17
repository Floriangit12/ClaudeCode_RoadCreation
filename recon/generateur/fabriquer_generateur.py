"""Pilote du générateur de routes (hython Houdini 22) : description simple ou modèle -> fabrication par les HDA rg::*.

    hython recon/generateur/fabriquer_generateur.py ENTREE [ENTREE ...] [--sortie DOSSIER] [--construire-hda]
                                                    [--verifier-determinisme] [--hip] [--vex-jit]

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


def fabriquer(entrees, sortie, signatures, hip=False, reglages=None, l2=False, rendus=False, l2b=False,
              construire=False, decor_etape2=False):
    lire, graphe, prof = reseau()
    noeuds_l2 = noeuds_l2b = None
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
    produits = []
    for e in entrees:
        scene, chemin_modele, info = preparer_entree(e, sortie)
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
                import rendu_l2b as RB
                RB.rendre_scene(noeuds_l2, noeuds_l2b, scene, Path(sortie) / scene, lire.parent(),
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
                                                       "implique --l2 ; avec --rendus : rendus soignés et planches")
    ap.add_argument("--decor-etape2", action="store_true",
                    help="avec --l2b --rendus : décor de l'étape 2 (arbres, prolongements, sol de décor, relief, nuages) ; "
                         "par défaut (étape 1, décision de l'utilisateur) : la route seule sur un socle neutre")
    a = ap.parse_args()
    if a.l2b:
        a.l2 = True
    signatures = construire_hda(forcer=a.construire_hda, l2=a.l2)
    if a.l2b and not a.entrees:                      # construction seule : rg::marquages et HDA pj:: réutilisées
        import fabriquer_l2 as F2
        import fabriquer_l2b as F2B
        F2.installer_pj()
        signatures.update(F2B.construire_hda(forcer=a.construire_hda))
    print("HDA :", ", ".join(f"{k} ({v[:12]})" for k, v in signatures.items()))
    if not a.entrees:
        return 0
    reglages = {"fleche_max": a.fleche, "pas_max": a.pas_max}
    produits = fabriquer(a.entrees, a.sortie, signatures, hip=a.hip, reglages=reglages, l2=a.l2, rendus=a.rendus,
                         l2b=a.l2b, construire=a.construire_hda, decor_etape2=a.decor_etape2)
    if a.verifier_determinisme:
        autre = ICI / "tmp" / "l1" / "determinisme"
        opts = [x for k, v in (("--fleche", a.fleche), ("--pas-max", a.pas_max)) if v is not None for x in (k, str(v))]
        opts += ["--l2"] if a.l2 else []
        opts += ["--l2b"] if a.l2b else []
        r = subprocess.run([sys.executable, __file__] + a.entrees + ["--sortie", str(autre)] + opts,
                           env=dict(os.environ, RG_PILOTE_ENV=""), capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode:
            print(r.stdout, r.stderr)
            raise SystemExit("second processus en échec")
        from commun import determinisme as DET
        ecarts, n = DET.comparer(produits, autre, a.l2, a.l2b)
        print("déterminisme :", f"identique ({n} fichiers ; .usda : chemins relatifs des matériaux normalisés)"
              if not ecarts else f"DIFFÉRENT : {ecarts}")
        return 1 if ecarts else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
