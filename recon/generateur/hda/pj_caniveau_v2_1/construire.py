"""Construit l'HDA pj::caniveau::2.1 (nouvelle version ; pj::caniveau::1.0 et ::2.0 restent intactes) ; hython 22.

    hython recon/generateur/hda/pj_caniveau_v2_1/construire.py

Même réseau que pj::caniveau::1.0 (recon/pcg/houdini/hda/pj_bordure/construire.py, mode « caniveau », importé sans
modification) ; deux correctifs dans le nœud disposer :
1. (2.0) intervalles du caniveau lus dans props avec des groupes non capturants dans re_findall (voir
   recon/generateur/hda/pj_caniveau_v2/construire.py) ;
2. (2.1, correction après le second contrôle de l'étape 1) pièce de caniveau gardée dès 5 mm au lieu de 5 cm à la
   coupe d'un élément de bordure par une borne d'intervalle : l'avaloir remplace désormais le caniveau qu'il occupe
   (rg::vers_entites coupe le caniveau à s0 de l'avaloir) ; une coupe de 1 à 5 cm entre le dernier joint et l'avaloir
   était abandonnée et laissait un trou dans la file (S03 : 5,3 cm devant chaque avaloir de poche) ;
3. (2.1) une coupe de moins de 0,20 m à une borne d'intervalle (TQ-BOR-002 : éléments rigides, coupe ≥ 0,20 m ; S03 :
   4,7 cm devant chaque avaloir) est partagée avec l'élément voisin de la même file (joint ≤ 2 cm) : les deux pièces
   prennent chacune la moitié de leur longueur totale (≥ 0,20 m chacune) ; le joint du caniveau quitte alors celui de la
   bordure à cet endroit seulement.
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
GEN = ICI.parents[1]
PJ_BORDURE = GEN.parents[1] / "recon" / "pcg" / "houdini" / "hda" / "pj_bordure"
sys.path.insert(0, str(GEN / "hda" / "commun"))
import rg_hda_outils as R  # noqa: E402

CORRECTIFS = (
    (r're_findall("-?[0-9]+(\.[0-9]+)?([eE]-?[0-9]+)?", t)', r're_findall("-?[0-9]+(?:\.[0-9]+)?(?:[eE]-?[0-9]+)?", t)'),
    ("        if (hi - lo < 0.05) continue;\n", "        if (hi - lo < 0.005) continue;\n"),
    ("int n = len(c0);\n",
     "// 2.1 : coupe de moins de 0,20 m (TQ-BOR-002) partagée avec l'élément voisin de la même file (joint ≤ 2 cm)\n"
     "for (int i = 0; i < len(c0); i++) {\n"
     "    if (c1[i] - c0[i] >= 0.20 - 1e-4) continue;\n"
     "    int j = -1;\n"
     "    if (i > 0 && c0[i] - c1[i - 1] < 0.02) j = i - 1;\n"
     "    else if (i + 1 < len(c0) && c0[i + 1] - c1[i] < 0.02) j = i + 1;\n"
     "    if (j < 0) continue;\n"
     "    int a = min(i, j), b = max(i, j);\n"
     "    float g = c0[b] - c1[a];\n"
     "    float tot = c1[b] - c0[a] - g;\n"
     "    if (tot < 0.40) continue;\n"
     "    c1[a] = c0[a] + 0.5 * tot;\n"
     "    c0[b] = c1[a] + g;\n"
     "    ccoupe[a] = 1;\n"
     "    ccoupe[b] = 1;\n"
     "    csur[a] = csur[a] || pj_cb_fleche(cb, c0[a], c1[a]) > 0.002;\n"
     "    csur[b] = csur[b] || pj_cb_fleche(cb, c0[b], c1[b]) > 0.002;\n"
     "}\n"
     "int n = len(c0);\n"),
)


def construire(dossier=ICI):
    sys.path.insert(0, str(PJ_BORDURE))
    import construire as B  # noqa: E402  (pj_bordure/construire.py, lecture seule)
    sub = R.sous_reseau("pj_caniveau_v2_1")
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(B.parametres("caniveau")))
    B.reseau(sub, "caniveau")
    d = sub.node("disposer")
    code = d.parm("snippet").eval()
    for ancien, nouveau in CORRECTIFS:
        if code.count(ancien) != 1:
            raise SystemExit(f"pj::caniveau : « {ancien.strip()} » trouvé {code.count(ancien)} fois (réseau de pj_bordure modifié ?)")
        code = code.replace(ancien, nouveau)
    d.parm("snippet").set(code)
    aide = B.AIDE_CANIVEAU + (" Version 2.1 : intervalles du caniveau (props) correctement lus (groupes non capturants "
                              "dans re_findall) ; pièce gardée dès 5 mm à une borne d'intervalle (caniveau coupé à "
                              "l'avaloir sans trou) ; une coupe de moins de 0,20 m est partagée avec l'élément voisin "
                              "(deux pièces de même longueur, TQ-BOR-002).")
    return R.creer_hda(sub, "caniveau", "PJ Caniveaux (éléments préfabriqués) v2.1", B.parametres("caniveau"), dossier,
                       entrees=(1, 3), sorties=3, aide=aide, details_aide=B.DETAILS, module_python=B.module_python(),
                       icone="SOP_sweep", etiquettes_entrees=("Bordures à caniveau (courbes)", "Nivellement (HeightField)",
                                                               "Contexte (facultatif)"),
                       etiquettes_sorties=("Maillages", "Points d'instances", "Prototypes"), version="2.1", espace="pj",
                       fichier="pj_caniveau_2.1.hdalc")


if __name__ == "__main__":
    print(construire())
