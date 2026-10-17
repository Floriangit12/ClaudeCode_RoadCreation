"""Construit l'HDA pj::bordure::2.0 (nouvelle version de pj::bordure::1.0, l'ancienne reste intacte) ; hython 22.

    hython recon/generateur/hda/pj_bordure_v2/construire.py

Même réseau que pj::bordure::1.0 (recon/pcg/houdini/hda/pj_bordure/construire.py, importé sans modification), un seul
correctif dans le nœud « disposer » (fonction pj_disposer de pj_pose.h, recopiée en tête du wrangle) :

Un angle vif de la courbe de bordure (coin de la polyligne) n'était posé comme point dur « angle » que s'il ne tombait
pas à moins de 0,25 m d'un autre point dur. Aux angles des avancées de trottoir et des îlots (S03 : retour en chartière
→ nez courant de l'avancée), l'angle coïncide exactement avec un changement d'intervalle (point dur « abaisse » ou
« profil ») : il était perdu. Les deux éléments de l'angle n'étaient alors ni marqués « angle », ni posés sur mesure en
onglet ; le joint calculé pour une petite déviation (w + base × φ / 2) ouvrait à 90° une fente de 0,12 m sur le nez
(about droit, ombre triangulaire, 1,58 m de « trous » dans elements.json pour S03 ; relecture adverse, défaut connu
du rapport L2).

Correction : (1) les sommets vifs de la courbe (déviation de cap de plus de 30° entre deux primitives : « angle vif
(déviation > 30° sur moins de 0,5 m) », assets/specs/bordures_elements.json, pose.points_durs) sont ajoutés aux coins
voulus (les courbes de rg::vers_entites sont des polylignes sans geometrie_reguliere.coins : aucun angle n'était
déclaré) ; (2) un angle confondu (à moins de 1 mm) avec un point dur de changement d'intervalle (« abaisse » ou
« profil ») transforme ce point dur en « angle » ; les deux éléments qui touchent l'angle deviennent sur mesure, aboutés
en onglet (plan bissecteur, joint de 3,5 à 9,5 mm comme aux autres angles vifs) : la paire forme la pièce d'angle.
Les extrémités et les coupes de zone gardent leur priorité.
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
GEN = ICI.parents[1]
PJ_BORDURE = GEN.parents[1] / "recon" / "pcg" / "houdini" / "hda" / "pj_bordure"
sys.path.insert(0, str(GEN / "hda" / "commun"))
import rg_hda_outils as R  # noqa: E402

ANCIEN_COINS = """    float coins[] = pj_cb_coins(cb);"""
NOUVEAU_COINS = """    float coins[] = pj_cb_coins(cb);
    // pj::bordure::2.0 : sommets vifs de la courbe (déviation de cap > 30° entre deux primitives : « angle vif »,
    // bordures_elements.json pose.points_durs) ajoutés aux coins voulus : les courbes de rg::vers_entites (polylignes,
    // sans geometrie_reguliere.coins) n'en déclaraient aucun
    for (int i = 1; i < len(cb); i++) {
        float ca = cb[i - 1]["cap0_rad"], ka = cb[i - 1]["k0"], sa0 = cb[i - 1]["s0"], sa1 = cb[i - 1]["s1"];
        float cbb = cb[i]["cap0_rad"], sb0 = cb[i]["s0"];
        float dv = cbb - (ca + ka * (sa1 - sa0));
        dv = atan2(sin(dv), cos(dv));
        if (abs(dv) <= radians(30.0)) continue;
        int deja = 0;
        foreach (float c0; coins) if (abs(c0 - sb0) < 1e-4) deja = 1;
        if (!deja) append(coins, sb0);
    }"""
ANCIEN = """        int libre = 1;
        foreach (float x; hs) if (abs(sc - x) < 0.25) libre = 0;    // pas de file minuscule près d'un autre point dur
        if (libre) pj_dur_ajouter(hs, ht, sc, "angle");"""
NOUVEAU = """        int libre = 1;
        for (int q = 0; q < len(hs); q++) {
            if (abs(sc - hs[q]) < 0.25) libre = 0;                   // pas de file minuscule près d'un autre point dur
            // pj::bordure::2.0 : angle confondu avec un changement d'intervalle (avancée, îlot) : le point dur devient
            // un angle (deux éléments sur mesure aboutés en onglet = pièce d'angle)
            if (abs(sc - hs[q]) < 1e-3 && (ht[q] == "abaisse" || ht[q] == "profil")) ht[q] = "angle";
        }
        if (libre) pj_dur_ajouter(hs, ht, sc, "angle");"""


def construire(dossier=ICI):
    sys.path.insert(0, str(PJ_BORDURE))
    import construire as B  # noqa: E402  (pj_bordure/construire.py, lecture seule)
    sub = R.sous_reseau("pj_bordure_v2")
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(B.parametres("bordure")))
    B.reseau(sub, "bordure")
    d = sub.node("disposer")
    code = d.parm("snippet").eval()
    if code.count(ANCIEN) != 1 or code.count(ANCIEN_COINS) != 1:
        raise SystemExit("pj::bordure : bloc des angles vifs introuvable (réseau de pj_bordure modifié ?)")
    d.parm("snippet").set(code.replace(ANCIEN_COINS, NOUVEAU_COINS).replace(ANCIEN, NOUVEAU))
    aide = B.AIDE + (" Version 2.0 : un angle vif confondu avec un changement d'intervalle (avancée, îlot) est posé "
                     "comme angle (deux éléments sur mesure en onglet : pièce d'angle) au lieu d'un joint ouvert.")
    return R.creer_hda(sub, "bordure", "PJ Bordures (éléments préfabriqués) v2", B.parametres("bordure"), dossier,
                       entrees=(1, 3), sorties=3, aide=aide, details_aide=B.DETAILS, module_python=B.module_python(),
                       icone="SOP_sweep", etiquettes_entrees=("Bordures (courbes)", "Nivellement (HeightField)",
                                                               "Contexte (facultatif)"),
                       etiquettes_sorties=("Maillages", "Points d'instances", "Prototypes"), version="2.0", espace="pj",
                       fichier="pj_bordure_2.0.hdalc")


if __name__ == "__main__":
    print(construire())
