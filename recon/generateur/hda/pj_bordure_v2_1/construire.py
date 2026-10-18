"""Construit l'HDA pj::bordure::2.1 (lot bordures, 17/10/2026 ; pj::bordure::1.0 et ::2.0 restent intactes) ; hython 22.

    hython recon/generateur/hda/pj_bordure_v2_1/construire.py

Même réseau que pj::bordure::2.0 (recon/generateur/hda/pj_bordure_v2/construire.py : réseau de pj::bordure::1.0 et
correctif des angles vifs, importés sans modification). Seul changement : la table des profils figée dans le module
Python de l'HDA (TABLE_EMBARQUEE) est la table étendue de recon/generateur/commun/bordures_catalogue.py :
table de pj::bordure (assets/specs/bordures.json + bordures_elements.json, inchangée pour ses profils) complétée des
profils du catalogue route_fr qui lui manquaient (cotes des règles RF-AS-profil_* de regles_route_fr.json) : T4, I3, I4,
P4, GR_T1, GR_T2, GR_P1, T2_basse, T2_surbaissee, T3_basse, T3_surbaissee, P1_basse, ACCESBUS (et CS4 pour
pj::caniveau::2.2). Les poses (pas, coupes, joints, chartières, angles) sont celles de 2.0, pour tous les profils.
"""
import importlib.util
import json
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
GEN = ICI.parents[1]
PJ_BORDURE = GEN.parents[1] / "recon" / "pcg" / "houdini" / "hda" / "pj_bordure"
sys.path.insert(0, str(GEN / "hda" / "commun"))
sys.path.insert(0, str(GEN / "commun"))
import rg_hda_outils as R  # noqa: E402
import bordures_catalogue as BC  # noqa: E402


def module_python_etendu():
    """Module embarqué : profils.py (pj_bordure, lecture seule) + table étendue figée (TABLE_EMBARQUEE)."""
    table, src = BC.construire_table_etendue()
    js = json.dumps({"profils": table, "source": {"dossier": "assets/specs + assets/specs/route/regles_route_fr.json "
                                                             "(RF-AS-profil_*)", "sha256": src}},
                    sort_keys=True, ensure_ascii=False)
    return (PJ_BORDURE / "profils.py").read_text(encoding="utf-8") + f"\n\nTABLE_EMBARQUEE = r'''{js}'''\n"


def _v2():
    spec = importlib.util.spec_from_file_location("construire_pj_bordure_v2", GEN / "hda" / "pj_bordure_v2" / "construire.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def construire(dossier=ICI):
    V2 = _v2()
    sys.path.insert(0, str(PJ_BORDURE))
    import construire as B  # noqa: E402  (pj_bordure/construire.py, lecture seule)
    sub = R.sous_reseau("pj_bordure_v2_1")
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(B.parametres("bordure")))
    B.reseau(sub, "bordure")
    d = sub.node("disposer")
    code = d.parm("snippet").eval()
    if code.count(V2.ANCIEN) != 1 or code.count(V2.ANCIEN_COINS) != 1:
        raise SystemExit("pj::bordure : bloc des angles vifs introuvable (réseau de pj_bordure modifié ?)")
    d.parm("snippet").set(code.replace(V2.ANCIEN_COINS, V2.NOUVEAU_COINS).replace(V2.ANCIEN, V2.NOUVEAU))
    # (prototypes espacés de 1 m comme en 2.0 : toutes les bordures font moins de 0,5 m de large, QUAI_BUS 0,35)
    aide = B.AIDE + (" Version 2.0 : un angle vif confondu avec un changement d'intervalle (avancée, îlot) est posé "
                     "comme angle (deux éléments sur mesure en onglet : pièce d'angle) au lieu d'un joint ouvert. "
                     "Version 2.1 (lot bordures) : table des profils étendue aux profils du catalogue route_fr "
                     "(T4, I3, I4, P4, GR_T1, GR_T2, GR_P1, T2_basse, T2_surbaissee, T3_basse, T3_surbaissee, P1_basse, "
                     "ACCESBUS, CS4 ; cotes RF-AS-profil_*)).")
    return R.creer_hda(sub, "bordure", "PJ Bordures (éléments préfabriqués) v2.1", B.parametres("bordure"), dossier,
                       entrees=(1, 3), sorties=3, aide=aide, details_aide=B.DETAILS, module_python=module_python_etendu(),
                       icone="SOP_sweep", etiquettes_entrees=("Bordures (courbes)", "Nivellement (HeightField)",
                                                               "Contexte (facultatif)"),
                       etiquettes_sorties=("Maillages", "Points d'instances", "Prototypes"), version="2.1", espace="pj",
                       fichier="pj_bordure_2.1.hdalc")


if __name__ == "__main__":
    print(construire())
