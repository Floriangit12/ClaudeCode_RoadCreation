"""Outils des scripts de construction des HDA de marquage (hda/pj_marquage_*, agent F2) ; hython Houdini 22.

    import pj_marquage_outils as M
    M.O                                   # hda/commun/pj_hda_outils (créer, développer, installer)
    M.vex_m()                             # pj_niveau.h + pj_repere.h + pj_marquage.h, à recopier en tête d'un wrangle
    M.wrangle_m(sub, nom, code, classe, entree, entrees=(...), precision64=False)
    M.boucle_par_attribut(sub, entree, "pj_entite", corps)   # For-Each (pièces nommées) ; corps(debut) -> dernier nœud
    M.SPEC_MARQUAGES, M.MODULATIONS       # assets/specs/marquages_geometrie.json (lue à la construction)

Les règles appliquées sont citées dans le code VEX des HDA (identifiants MQ-*, FUS-*, GQ-*, TQ-*).
"""
import importlib.util
import json
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
HDA = ICI.parent
sys.path.insert(0, str(HDA / "commun"))
import pj_hda_outils as O  # noqa: E402

RACINE = O.RACINE
SPEC_MARQUAGES = RACINE / "assets/specs/marquages_geometrie.json"
SPEC_DEFAUT = SPEC_MARQUAGES.as_posix()
COUCHE = "PJ_Marquages"
COUCHE_LIB = "PJ_Lib_Marquages"
LIB_UE = "/Game/PJ/Lib/Marquages"


def spec():
    return json.loads(SPEC_MARQUAGES.read_text(encoding="utf-8"))


def modulations():
    """Table IISR des modulations (marquages_geometrie.modulations.table, art. 113-1 B) : nom -> (trait, vide)."""
    t = spec()["modulations"]["table"]
    return {k: (float(v["trait_m"]), float(v["vide_m"])) for k, v in sorted(t.items())}


def vex_m(*autres):
    """Bibliothèques VEX : nivellement (pj_niveau.h), repères (pj_repere.h), marquages (pj_marquage.h)."""
    return O.vex("pj_niveau.h", "pj_repere.h") + (ICI / "vex" / "pj_marquage.h").read_text(encoding="utf-8") + "\n" + \
        "".join(autres)


def wrangle_m(sub, nom, code, classe="point", entree=None, entrees=(), precision64=False, bibliotheques=True):
    """Attribute Wrangle dont le code est précédé des bibliothèques VEX du projet (vex_m)."""
    w = sub.createNode("attribwrangle", nom)
    w.parm("class").set({"detail": 0, "primitive": 1, "point": 2, "sommet": 3}[classe])
    w.parm("snippet").set((vex_m() if bibliotheques else "") + code)
    if precision64:
        w.parm("vex_precision").set("64")       # coordonnées Lambert-93 lues dans props (JSON) : float64
    if entree is not None:
        w.setInput(0, entree)
    for k, e in enumerate(entrees):
        if e is not None:
            w.setInput(k + 1, e)
    return w


def boucle_par_attribut(sub, entree, attribut, corps, nom="boucle"):
    """For-Each « pièces nommées » : block_begin (piece) -> corps(debut) -> block_end (merge, primitive, attribut)."""
    debut = sub.createNode("block_begin", f"{nom}_debut")
    fin = sub.createNode("block_end", f"{nom}_fin")
    debut.setInput(0, entree)
    debut.parm("method").set("piece")
    debut.parm("blockpath").set(f"../{fin.name()}")
    dernier = corps(debut)
    fin.setInput(0, dernier)
    fin.parm("itermethod").set("pieces")
    fin.parm("method").set("merge")
    fin.parm("class").set("primitive")
    fin.parm("useattrib").set(1)
    fin.parm("attrib").set(attribut)
    fin.parm("blockpath").set(f"../{debut.name()}")
    fin.parm("templatepath").set(f"../{debut.name()}")
    return debut, fin


def blast(sub, nom, entree, groupe, garder=True):
    b = sub.createNode("blast", nom)
    b.setInput(0, entree)
    b.parm("group").set(groupe)
    b.parm("grouptype").set("prims")
    b.parm("negate").set(1 if garder else 0)
    return b


def interrupteur(sub, nom, entrees, expression):
    s = sub.createNode("switch", nom)
    for k, e in enumerate(entrees):
        s.setInput(k, e)
    s.parm("input").setExpression(expression)
    return s


def installer_commun():
    """Installe toutes les HDA de hda/** ; construit pj::marquage_solide et pj::gabarits_iisr s'ils manquent."""
    O.installer_tout()
    manque = [n for n in ("marquage_solide", "gabarits_iisr")
              if hou.nodeType(hou.sopNodeTypeCategory(), O.nom_type(n)) is None]
    if manque:
        charger(ICI / "construire.py", "construire_marquage_commun").construire()
        O.installer_tout()


def charger(chemin, nom):
    """Module Python chargé par son chemin (plusieurs construire.py dans hda/**)."""
    if nom in sys.modules:
        return sys.modules[nom]
    sp = importlib.util.spec_from_file_location(nom, str(chemin))
    m = importlib.util.module_from_spec(sp)
    sys.modules[nom] = m
    sp.loader.exec_module(m)
    return m
