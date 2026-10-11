"""Outils communs des scripts de construction des HDA pj::* (hython Houdini 22, licence Indie).

Utilisé par hda/*/construire.py (ce dossier et ceux des branches) et par recon/pcg/houdini/fabriquer_hda.py :

    import pj_hda_outils as O
    sub = O.sous_reseau("pj_lire_description")          # subnet de travail dans /obj/_construction
    ... hou.createNode / setInput / parm().set() dans sub ...
    chemin = O.creer_hda(sub, "lire_description", "PJ Lire la description", parms, dossier, entrees=(0, 0),
                         sorties=2, aide=..., module_python=...)   # -> <dossier>/pj_lire_description.hdalc/ (développé)
    O.vex("pj_niveau.h", "pj_repere.h")                 # texte VEX à recopier en tête d'un wrangle
    O.installer_tout()                                  # installe toutes les HDA développées de hda/**
    O.empaqueter(fichier)                               # paquet unique (toutes les définitions pj::*) pour UE

Format versionné : dossier développé `<fichier>.hdalc/` (hou.hda.expandToDirectory), réseau non compressé, installable
tel quel. Le .hdalc compact n'est produit que dans le paquet (recon/out/.../fabrique_hda/hda/).
"""
import hashlib
import os
import re
import shutil
import tempfile
from pathlib import Path

import hou

HDA = Path(__file__).resolve().parents[1]                  # recon/pcg/houdini/hda
RACINE = HDA.parents[3]                                     # racine du dépôt
VEX = HDA / "commun" / "vex"
ESPACE = "pj"
VERSION = "1.0"


def nom_type(nom):
    return f"{ESPACE}::{nom}::{VERSION}"


def vex(*fichiers):
    """Texte des bibliothèques VEX communes, à recopier en tête du code d'un wrangle (#include opdef: impossible)."""
    return "".join((VEX / f).read_text(encoding="utf-8") + "\n" for f in fichiers)


def sous_reseau(nom, contexte="sop"):
    """Subnet vide pour construire le réseau d'une HDA (SOP : dans /obj/_construction ; LOP : dans /stage)."""
    if contexte == "sop":
        obj = hou.node("/obj/_construction") or hou.node("/obj").createNode("geo", "_construction")
        for c in obj.children():
            if c.name() == nom:
                c.destroy()
        return obj.createNode("subnet", nom)
    st = hou.node("/stage")
    for c in st.children():
        if c.name() == nom:
            c.destroy()
    return st.createNode("subnet", nom)


def sortie(sub, source, index, nom=None):
    """Output SOP d'index donné branché sur `source`."""
    o = sub.createNode("output", nom or f"sortie_{index + 1}")
    o.parm("outputidx").set(index)
    o.setInput(0, source)
    return o


def wrangle(sub, nom, code, classe="point", entree=None, entrees=(), bibliotheques=()):
    """Attribute Wrangle : classe point | primitive | sommet | detail ; code VEX précédé des bibliothèques."""
    w = sub.createNode("attribwrangle", nom)
    w.parm("class").set({"detail": 0, "primitive": 1, "point": 2, "sommet": 3}[classe])
    w.parm("snippet").set((vex(*bibliotheques) if bibliotheques else "") + code)
    if entree is not None:
        w.setInput(0, entree)
    for k, e in enumerate(entrees):
        if e is not None:
            w.setInput(k + 1, e)
    return w


def ranger(sub):
    """Disposition lisible du réseau (ordre déterministe)."""
    sub.layoutChildren()


def _aide_wiki(etiquette, resume, parms, details=""):
    lignes = [f"= {etiquette} =", "", f'"""{resume}"""', ""]
    if details:
        lignes += [details, ""]
    lignes += ["@parameters", ""]

    def parcourir(tpls):
        for t in tpls:
            if isinstance(t, hou.FolderParmTemplate):
                lignes.append(f"== {t.label()} ==")
                lignes.append("")
                parcourir(t.parmTemplates())
            elif not isinstance(t, (hou.SeparatorParmTemplate, hou.LabelParmTemplate)):
                lignes.append(f"{t.label()}:")
                lignes.append(f"    #id: {t.name()}")
                lignes.append(f"    {t.help() or ''}")
                lignes.append("")
    parcourir(parms)
    return "\n".join(lignes) + "\n"


# version des outils de construction (dans la signature) : « 2 » = libellés d'entrées sans les défauts du subnet
VERSION_OUTILS = "2"


def creer_hda(sub, nom, etiquette, parms, dossier, entrees=(0, 1), sorties=1, aide="", details_aide="",
              module_python=None, icone="SOP_subnet", etiquettes_entrees=(), etiquettes_sorties=()):
    """Convertit le subnet `sub` en HDA pj::<nom>::1.0, l'enregistre et la développe en <dossier>/pj_<nom>.hdalc/.

    parms : liste de hou.ParmTemplate (dossiers compris), libellés en français, posée comme interface de l'HDA.
    Renvoie le chemin du dossier développé (installé dans la session)."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    cible = dossier / f"pj_{nom}.hdalc"
    # Signature de construction : réseau (asCode), interface, module, aide, version de Houdini. Une HDA Indie n'est
    # jamais identique à l'octet (marques de licence HouLC et dates dans Contents) : si la signature est inchangée,
    # le dossier développé existant est gardé tel quel (aucun diff parasite).
    signature = hashlib.sha256("\n".join([
        hou.applicationVersionString(), sub.asCode(brief=False, recurse=True),
        hou.ParmTemplateGroup(parms).asDialogScript(), module_python or "", aide, details_aide,
        repr((entrees, sorties, icone, tuple(etiquettes_entrees), tuple(etiquettes_sorties))),
        VERSION_OUTILS]).encode("utf-8")
    ).hexdigest()
    existante = [f for f in cible.glob("*/PjSignature")] if cible.exists() else []
    if existante and existante[0].read_text(encoding="utf-8").strip() == signature:
        sub.destroy()
        hou.hda.installFile(str(cible))
        return cible
    tmp = Path(tempfile.mkdtemp(prefix="pj_hda_")) / f"pj_{nom}.hdalc"
    ptg = hou.ParmTemplateGroup(parms)
    nt = nom_type(nom)
    # une définition déjà installée sous ce nom (version précédente) est retirée de la session
    ancien = hou.nodeType(hou.sopNodeTypeCategory() if sub.type().category() == hou.sopNodeTypeCategory()
                          else sub.type().category(), nt)
    if ancien is not None and ancien.definition() is not None:
        for d in ancien.allInstalledDefinitions():
            try:
                hou.hda.uninstallFile(d.libraryFilePath())
            except hou.OperationFailed:
                pass
    for k, t in enumerate(etiquettes_entrees):          # libellés d'entrées du subnet (Houdini Engine, broches PCG)
        if sub.parm(f"label{k + 1}") is not None:
            sub.parm(f"label{k + 1}").set(t)
    noeud = sub.createDigitalAsset(name=nt, hda_file_name=str(tmp), description=etiquette,
                                   min_num_inputs=entrees[0], max_num_inputs=entrees[1],
                                   ignore_external_references=True, change_node_type=True,
                                   create_backup=False)
    d = noeud.type().definition()
    d.setParmTemplateGroup(ptg)
    d.setMaxNumOutputs(max(1, sorties))
    d.setIcon(icone)
    d.setVersion(VERSION)
    d.setComment(f"{etiquette} (recon/pcg/houdini/hda, projet Paquet Jardin)")
    d.setExtraInfo("")
    if module_python:
        d.addSection("PythonModule", module_python)
        d.setExtraFileOption("PythonModule/IsPython", True)
    d.addSection("Help", _aide_wiki(etiquette, aide, parms, details_aide))
    d.addSection("PjSignature", signature + "\n")
    opts = d.options()
    opts.setCompressContents(False)
    opts.setLockContents(True)
    opts.setSaveInitialParmsAndContents(False)
    opts.setUnlockNewInstances(False)
    opts.setCheckForExternalLinks(True)
    d.setOptions(opts)
    if etiquettes_entrees or etiquettes_sorties:
        lignes = []
        for k, t in enumerate(etiquettes_entrees):
            lignes.append(f"    inputlabel\t{k + 1}\t\"{t}\"")
        for k, t in enumerate(etiquettes_sorties):
            lignes.append(f"    outputlabel\t{k + 1}\t\"{t}\"")
        ds = d.sections()["DialogScript"].contents()
        # libellés par défaut du subnet (« Sub-Network Input #n ») retirés : écrits après les nôtres, ils les remplaçaient
        # (Houdini Engine et les broches du nœud PCG affichaient « Sub-Network Input #1 »)
        ds = re.sub(r'\n[ \t]*inputlabel[ \t]+\d+[ \t]+"Sub-Network Input #\d+"', "", ds)
        ds = re.sub(r"(\{\s*\n\s*name\s+[^\n]+\n)", lambda m: m.group(1) + "\n".join(lignes) + "\n", ds, count=1)
        d.sections()["DialogScript"].setContents(ds)
    d.updateFromNode(noeud)
    d.save(str(tmp), noeud, opts)
    for f in (cible, tmp):
        try:
            hou.hda.uninstallFile(str(f))
        except hou.OperationFailed:
            pass
    if cible.exists():
        shutil.rmtree(cible)
    hou.hda.expandToDirectory(str(tmp), str(cible))
    shutil.rmtree(tmp.parent, ignore_errors=True)
    _normaliser_developpe(cible)
    hou.hda.installFile(str(cible))
    return cible


def _normaliser_developpe(cible):
    """Diffs stables : rien à faire tant que la comparaison de deux constructions ne montre pas de champ volatil
    (vérifié par fabriquer_hda.py --construire-hda --verifier-determinisme)."""
    return cible


def compter_noeuds(type_complet, categorie=None):
    """Nœuds du réseau interne d'une HDA : enfants directs (le réseau visible) par type, et total récursif (les
    wrangles contiennent un VOP compilé). Le contenu d'une HDA verrouillée n'est chargé qu'à la cuisson."""
    cat = categorie or hou.sopNodeTypeCategory()
    obj = hou.node("/obj/_comptage") or hou.node("/obj").createNode("geo", "_comptage")
    parent = obj if cat == hou.sopNodeTypeCategory() else hou.node("/stage")
    n = parent.createNode(type_complet)
    try:
        n.cook(force=True)
    except hou.OperationFailed:
        pass                                           # entrées absentes : le contenu est tout de même chargé
    par_type = {}
    for c in n.children():
        par_type[c.type().name()] = par_type.get(c.type().name(), 0) + 1
    res = {"noeuds": len(n.children()), "recursif": len(n.allSubChildren()), "par_type": dict(sorted(par_type.items()))}
    n.destroy()
    return res


def dossiers_hda(racine=HDA):
    """Toutes les HDA versionnées de hda/** : dossiers développés *.hdalc et fichiers .hdalc / .hda isolés."""
    out = []
    for p in sorted(Path(racine).rglob("*")):
        if p.suffix not in (".hdalc", ".hda", ".hdanc", ".otl"):
            continue
        if any(q.suffix in (".hdalc", ".hda") and (q / "houdini.hdalibrary").exists() for q in p.parents):
            continue                                           # fichier interne d'un dossier développé
        if p.is_dir() and not (p / "houdini.hdalibrary").exists():
            continue
        out.append(p)
    return out


def installer_tout(racine=HDA):
    """Installe dans la session toutes les HDA de hda/** ; renvoie la liste des types pj::* installés."""
    for p in dossiers_hda(racine):
        hou.hda.installFile(str(p))
    return sorted(t for t in types_pj())


def types_pj():
    """Noms complets des types pj::* installés (SOP et LOP)."""
    out = []
    for cat in (hou.sopNodeTypeCategory(), hou.lopNodeTypeCategory(), hou.objNodeTypeCategory()):
        for nom, t in cat.nodeTypes().items():
            if nom.startswith(ESPACE + "::") and t.definition() is not None:
                out.append((cat.name(), nom))
    return sorted(out)


def empaqueter(fichier):
    """Paquet .hdalc unique contenant toutes les définitions pj::* installées (import dans Unreal) : construit dans un
    dossier temporaire (copyToHDAFile y laisse ses sauvegardes), puis copié."""
    fichier = Path(fichier)
    fichier.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="pj_paquet_")) / fichier.name
    noms = []
    for cat_nom, nom in types_pj():
        cat = {"Sop": hou.sopNodeTypeCategory(), "Lop": hou.lopNodeTypeCategory(),
               "Object": hou.objNodeTypeCategory()}[cat_nom]
        d = hou.nodeType(cat, nom).definition()
        d.copyToHDAFile(str(tmp))
        noms.append(f"{cat_nom}/{nom}")
    shutil.copyfile(tmp, fichier)
    shutil.rmtree(tmp.parent, ignore_errors=True)
    return noms
