"""Construit l'HDA pj::caniveau::2.2 (lot bordures, 17/10/2026 ; pj::caniveau::1.0, ::2.0 et ::2.1 restent intactes) ;
hython 22.

    hython recon/generateur/hda/pj_caniveau_v2_2/construire.py

Même réseau et mêmes correctifs que pj::caniveau::2.1 (recon/generateur/hda/pj_caniveau_v2_1/construire.py, importé
sans modification). Seul changement : table des profils figée étendue (recon/generateur/commun/bordures_catalogue.py,
comme pj::bordure::2.1) : le caniveau CS4 (RF-AS-profil_CS4, 300 × 190/160) s'ajoute à CS1, CS2, CS3, CC1, CC2 ; et
prototypes de bibliothèque espacés de 2 m (ESPACEMENT : défaut latent des versions précédentes avec le CC2 de 0,50 m).
"""
import importlib.util
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
GEN = ICI.parents[1]
PJ_BORDURE = GEN.parents[1] / "recon" / "pcg" / "houdini" / "hda" / "pj_bordure"
sys.path.insert(0, str(GEN / "hda" / "commun"))
import rg_hda_outils as R  # noqa: E402


def _charger(nom, chemin):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# 2.2 : prototypes de bibliothèque espacés de 2 m (au lieu de 1 m) pendant le Sweep et le Boolean des épaufrures.
# pj::bordure / pj::caniveau 1.0 décalent le prototype k de k m en Z et le retrouvent par floor(z + 0,5) (« aucun
# prototype n'est plus large que 0,5 m ») ; le caniveau CC2 fait exactement 0,50 m (z de k à k + 0,5) : son arête
# extérieure était rattachée au prototype suivant (attributs_pieces) et ramenée à −0,5 au lieu de +0,5 (recentrer).
# Constat du lot bordures (scène B01, premier emploi de CC2 et de CS1 voisins) : une face de 0,94 m posée à 2 cm
# au-dessus du caniveau CS1 (bande noire en vue de dessus) et un CC2 déformé. Défaut latent de 1.0 / 2.0 / 2.1.
ESPACEMENT = (
    ("dorsales_bib", "float pas_z = 1.0;", "float pas_z = 2.0;                          // 2.2 : prototypes jusqu'à 1 m de large"),
    ("attributs_pieces", "int k = int(floor(c.z + 0.5));", "int k = int(floor(c.z / 2.0 + 0.5));        // 2.2 : pas de 2 m"),
    ("recentrer", "@P.z -= floor(@P.z + 0.5);", "@P.z -= 2.0 * floor(@P.z / 2.0 + 0.5);      // 2.2 : pas de 2 m"),
)


def corriger_espacement(sub):
    """Correctif 2.2 des prototypes larges (ESPACEMENT) dans les wrangles du réseau."""
    for nom, ancien, nouveau in ESPACEMENT:
        w = sub.node(nom)
        code = w.parm("snippet").eval()
        if code.count(ancien) != 1:
            raise SystemExit(f"{nom} : « {ancien} » trouvé {code.count(ancien)} fois (réseau de pj_bordure modifié ?)")
        w.parm("snippet").set(code.replace(ancien, nouveau))


def construire(dossier=ICI):
    V21 = _charger("construire_pj_caniveau_v2_1", GEN / "hda" / "pj_caniveau_v2_1" / "construire.py")
    B21 = _charger("construire_pj_bordure_v2_1", GEN / "hda" / "pj_bordure_v2_1" / "construire.py")
    sys.path.insert(0, str(PJ_BORDURE))
    import construire as B  # noqa: E402  (pj_bordure/construire.py, lecture seule)
    sub = R.sous_reseau("pj_caniveau_v2_2")
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(B.parametres("caniveau")))
    B.reseau(sub, "caniveau")
    d = sub.node("disposer")
    code = d.parm("snippet").eval()
    for ancien, nouveau in V21.CORRECTIFS:
        if code.count(ancien) != 1:
            raise SystemExit(f"pj::caniveau : « {ancien.strip()} » trouvé {code.count(ancien)} fois (réseau de pj_bordure modifié ?)")
        code = code.replace(ancien, nouveau)
    d.parm("snippet").set(code)
    corriger_espacement(sub)
    aide = B.AIDE_CANIVEAU + (" Version 2.1 : intervalles du caniveau (props) correctement lus ; pièce gardée dès 5 mm à "
                              "une borne d'intervalle ; coupe de moins de 0,20 m partagée avec l'élément voisin. "
                              "Version 2.2 (lot bordures) : table des profils étendue (CS4, RF-AS-profil_CS4) ; prototypes "
                              "espacés de 2 m (CC2 de 0,50 m : arête rattachée au prototype voisin en 2.1).")
    return R.creer_hda(sub, "caniveau", "PJ Caniveaux (éléments préfabriqués) v2.2", B.parametres("caniveau"), dossier,
                       entrees=(1, 3), sorties=3, aide=aide, details_aide=B.DETAILS,
                       module_python=B21.module_python_etendu(), icone="SOP_sweep",
                       etiquettes_entrees=("Bordures à caniveau (courbes)", "Nivellement (HeightField)",
                                           "Contexte (facultatif)"),
                       etiquettes_sorties=("Maillages", "Points d'instances", "Prototypes"), version="2.2", espace="pj",
                       fichier="pj_caniveau_2.2.hdalc")


if __name__ == "__main__":
    print(construire())
