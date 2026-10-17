"""Outils des scripts de construction des HDA rg::* du générateur (hython Houdini 22, licence Indie).

Même outillage que les HDA pj::* (recon/pcg/houdini/hda/commun/pj_hda_outils.py, README_HDA § 1) : réseau construit
par hou.createNode dans un subnet, converti en HDA, enregistré en dossier développé `<nom>.hdalc/` (réseau non
compressé), signature de construction rangée dans la section `RgSignature` ; si la signature ne change pas, le dossier
existant est gardé tel quel (une HDA Indie n'est jamais identique à l'octet : marques de licence et dates).

    import rg_hda_outils as R
    sub = R.sous_reseau("rg_graphe")
    w = R.wrangle(sub, "echantillonner", code, "detail", entree, bibliotheques=("rg_geometrie.h",))
    R.creer_hda(sub, "graphe", "RG Graphe", parms, dossier, entrees=(1, 4), sorties=2, ...)

Différences avec pj_hda_outils : espace `rg`, fichiers `rg_<nom>.hdalc`, bibliothèques VEX lues dans
recon/generateur/hda/commun/vex (et, à défaut, dans celles du dépôt pj), wrangles en VEX 64 bits par défaut (les
lois de position du lot L1 exigent la double précision : flèche ≤ 0,5 mm, écarts ≤ 1 mm). Les fichiers temporaires
de Houdini vont dans recon/generateur/tmp/ (D:), jamais dans le dossier temporaire du système (C:).
"""
import hashlib
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import hou

HDA = Path(__file__).resolve().parents[1]                  # recon/generateur/hda
GEN = HDA.parent                                            # recon/generateur
RACINE = GEN.parents[1]                                     # racine du dépôt
VEX = HDA / "commun" / "vex"
VEX_PJ = RACINE / "recon" / "pcg" / "houdini" / "hda" / "commun" / "vex"
TMP = GEN / "tmp" / "hda"
ESPACE = "rg"
VERSION = "1.0"
VERSION_OUTILS = "1"                                        # dans la signature

sys.path.insert(0, str(RACINE / "recon" / "pcg" / "houdini" / "hda" / "commun"))
import pj_hda_outils as PJ  # noqa: E402  (sortie, ranger : réutilisés tels quels)

sortie = PJ.sortie
ranger = PJ.ranger


def nom_type(nom, version=VERSION):
    return f"{ESPACE}::{nom}::{version}"


def vex(*fichiers):
    """Texte des bibliothèques VEX (rg puis pj), à recopier en tête d'un wrangle (#include "opdef:" impossible)."""
    out = []
    for f in fichiers:
        p = VEX / f
        if not p.exists():
            p = VEX_PJ / f
        out.append(p.read_text(encoding="utf-8") + "\n")
    return "".join(out)


def sous_reseau(nom):
    """Subnet SOP vide, seul dans /obj/_construction_rg : drapeaux d'affichage et de rendu posés explicitement (ils
    entrent dans asCode, donc dans la signature ; sans cela, un subnet créé après la construction d'une autre HDA dans
    la même session avait ses drapeaux à faux et changeait de signature d'une session à l'autre)."""
    obj = hou.node("/obj/_construction_rg") or hou.node("/obj").createNode("geo", "_construction_rg")
    for c in obj.children():
        c.destroy()
    sub = obj.createNode("subnet", nom)
    sub.setDisplayFlag(True)
    sub.setRenderFlag(True)
    return sub


def wrangle(sub, nom, code, classe="point", entree=None, entrees=(), bibliotheques=(), precision="64"):
    """Attribute Wrangle : classe point | primitive | sommet | detail ; VEX 64 bits par défaut."""
    w = sub.createNode("attribwrangle", nom)
    w.parm("class").set({"detail": 0, "primitive": 1, "point": 2, "sommet": 3}[classe])
    w.parm("snippet").set((vex(*bibliotheques) if bibliotheques else "") + code)
    w.parm("vex_precision").set(precision)
    if entree is not None:
        w.setInput(0, entree)
    for k, e in enumerate(entrees):
        if e is not None:
            w.setInput(k + 1, e)
    return w


def _dossier_tmp():
    TMP.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(TMP)
    return Path(tempfile.mkdtemp(prefix="rg_hda_", dir=str(TMP)))


def creer_hda(sub, nom, etiquette, parms, dossier, entrees=(0, 1), sorties=1, aide="", details_aide="",
              module_python=None, icone="SOP_subnet", etiquettes_entrees=(), etiquettes_sorties=(), version=VERSION,
              espace=ESPACE, fichier=None):
    """Convertit le subnet `sub` en HDA <espace>::<nom>::<version> (rg par défaut), l'enregistre et la développe en
    <dossier>/<fichier> (rg_<nom>.hdalc par défaut ; installée dans la session). Renvoie le chemin du dossier
    développé. espace = "pj" : nouvelle version d'une HDA pj::* (l'ancienne reste intacte, README_HDA)."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    cible = dossier / (fichier or f"rg_{nom}.hdalc")
    signature = hashlib.sha256("\n".join([
        hou.applicationVersionString(), sub.asCode(brief=False, recurse=True),
        hou.ParmTemplateGroup(parms).asDialogScript(), module_python or "", aide, details_aide,
        repr((entrees, sorties, icone, tuple(etiquettes_entrees), tuple(etiquettes_sorties), version)),
        VERSION_OUTILS]).encode("utf-8")).hexdigest()
    if os.environ.get("RG_DEBUG_ASCODE"):
        TMP.mkdir(parents=True, exist_ok=True)
        (TMP / f"ascode_{nom}_{signature[:12]}.txt").write_text(sub.asCode(brief=False, recurse=True), encoding="utf-8")
    existante = [f for f in cible.glob("*/RgSignature")] if cible.exists() else []
    if existante and existante[0].read_text(encoding="utf-8").strip() == signature:
        sub.destroy()
        hou.hda.installFile(str(cible))
        return cible
    tmpd = _dossier_tmp()
    tmp = tmpd / (fichier or f"rg_{nom}.hdalc")
    ptg = hou.ParmTemplateGroup(parms)
    nt = f"{espace}::{nom}::{version}"
    ancien = hou.nodeType(hou.sopNodeTypeCategory(), nt)
    if ancien is not None and ancien.definition() is not None:
        for d in ancien.allInstalledDefinitions():
            try:
                hou.hda.uninstallFile(d.libraryFilePath())
            except hou.OperationFailed:
                pass
    for k, t in enumerate(etiquettes_entrees):
        if sub.parm(f"label{k + 1}") is not None:
            sub.parm(f"label{k + 1}").set(t)
    noeud = sub.createDigitalAsset(name=nt, hda_file_name=str(tmp), description=etiquette,
                                   min_num_inputs=entrees[0], max_num_inputs=entrees[1],
                                   ignore_external_references=True, change_node_type=True, create_backup=False)
    d = noeud.type().definition()
    d.setParmTemplateGroup(ptg)
    d.setMaxNumOutputs(max(1, sorties))
    d.setIcon(icone)
    d.setVersion(version)
    d.setComment(f"{etiquette} (recon/generateur/hda, générateur de routes françaises)")
    d.setExtraInfo("")
    if module_python:
        d.addSection("PythonModule", module_python)
        d.setExtraFileOption("PythonModule/IsPython", True)
    d.addSection("Help", PJ._aide_wiki(etiquette, aide, parms, details_aide))
    d.addSection("RgSignature", signature + "\n")
    opts = d.options()
    opts.setCompressContents(False)
    opts.setLockContents(True)
    opts.setSaveInitialParmsAndContents(False)
    opts.setUnlockNewInstances(False)
    opts.setCheckForExternalLinks(True)
    d.setOptions(opts)
    if etiquettes_entrees or etiquettes_sorties:
        lignes = [f"    inputlabel\t{k + 1}\t\"{t}\"" for k, t in enumerate(etiquettes_entrees)]
        lignes += [f"    outputlabel\t{k + 1}\t\"{t}\"" for k, t in enumerate(etiquettes_sorties)]
        ds = d.sections()["DialogScript"].contents()
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
    shutil.rmtree(tmpd, ignore_errors=True)
    hou.hda.installFile(str(cible))
    return cible


def signature(cible):
    f = [p for p in Path(cible).glob("*/RgSignature")]
    return f[0].read_text(encoding="utf-8").strip() if f else ""


def dossiers_hda(racine=HDA):
    """HDA rg::* et nouvelles versions d'HDA pj::* (dossiers pj_*_v<n>/) construites ici."""
    ps = sorted(Path(racine).glob("rg_*/rg_*.hdalc")) + sorted(Path(racine).glob("pj_*_v*/pj_*.hdalc"))
    return [p for p in ps if (p / "houdini.hdalibrary").exists()]


def installer_tout(racine=HDA):
    for p in dossiers_hda(racine):
        hou.hda.installFile(str(p))
    return sorted(n for n, t in hou.sopNodeTypeCategory().nodeTypes().items()
                  if n.startswith(ESPACE + "::") and t.definition() is not None)
