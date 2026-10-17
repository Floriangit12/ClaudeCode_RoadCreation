"""Construit l'HDA pj::caniveau::2.0 (nouvelle version de pj::caniveau::1.0, l'ancienne reste intacte) ; hython 22.

    hython recon/generateur/hda/pj_caniveau_v2/construire.py

Même réseau que pj::caniveau::1.0 (recon/pcg/houdini/hda/pj_bordure/construire.py, mode « caniveau », importé sans
modification), un seul correctif dans le nœud disposer : les intervalles du caniveau lus dans props
("caniveau": {"intervalles": [[s0, s1], ...]}) étaient extraits par re_findall avec des groupes capturants ; en VEX,
re_findall renvoie aussi les groupes (constat du lot L2 : [[0, 54], [58, 100]] lu {0, 0, 0, 54, 0, 0, 58, ...}),
si bien qu'un caniveau interrompu (ralentisseur, avancée de trottoir) était posé sur toute la bordure. Groupes non
capturants (?:...) : {0, 54, 58, 100}.
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
GEN = ICI.parents[1]
PJ_BORDURE = GEN.parents[1] / "recon" / "pcg" / "houdini" / "hda" / "pj_bordure"
sys.path.insert(0, str(GEN / "hda" / "commun"))
import rg_hda_outils as R  # noqa: E402

ANCIEN = 're_findall("-?[0-9]+(\\.[0-9]+)?([eE]-?[0-9]+)?", t)'
NOUVEAU = 're_findall("-?[0-9]+(?:\\.[0-9]+)?(?:[eE]-?[0-9]+)?", t)'


def construire(dossier=ICI):
    sys.path.insert(0, str(PJ_BORDURE))
    import construire as B  # noqa: E402  (pj_bordure/construire.py, lecture seule)
    sub = R.sous_reseau("pj_caniveau_v2")
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(B.parametres("caniveau")))
    B.reseau(sub, "caniveau")
    d = sub.node("disposer")
    code = d.parm("snippet").eval()
    if ANCIEN not in code:
        raise SystemExit("pj::caniveau : expression des intervalles introuvable (réseau de pj_bordure modifié ?)")
    d.parm("snippet").set(code.replace(ANCIEN, NOUVEAU))
    aide = B.AIDE_CANIVEAU + (" Version 2.0 : intervalles du caniveau (props) correctement lus (groupes non capturants "
                              "dans re_findall).")
    return R.creer_hda(sub, "caniveau", "PJ Caniveaux (éléments préfabriqués) v2", B.parametres("caniveau"), dossier,
                       entrees=(1, 3), sorties=3, aide=aide, details_aide=B.DETAILS, module_python=B.module_python(),
                       icone="SOP_sweep", etiquettes_entrees=("Bordures à caniveau (courbes)", "Nivellement (HeightField)",
                                                               "Contexte (facultatif)"),
                       etiquettes_sorties=("Maillages", "Points d'instances", "Prototypes"), version="2.0", espace="pj",
                       fichier="pj_caniveau_2.0.hdalc")


if __name__ == "__main__":
    print(construire())
