"""Construit l'HDA du lot L4 (marquages, trajectoires, conflits et zone de conflit des carrefours plans) :
rg::marquages_carrefour::1.0 (« RG Marquages des carrefours (trajectoires, guidage, zone de conflit) ») ; hython 22.

    hython recon/generateur/hda/rg_marquages_carrefour/construire.py

PLAN_GENERATEUR § 2.4, étapes 7 à 10 :
    entrées 1 SOLVEUR (rg::carrefours, sortie 3), 2 NIVEAUX (rg::nivellement, sortie 1), 3 références échantillonnées
    (rg::graphe, sortie 1), 4 LIGNES et MARQUES de la section courante (rg::marquages, sorties 1 et 2 fusionnées)
      -> lecture (Python SOP, module lecteur_marquages_carrefour.py : branches, consignes de flèches, mouvements et
         guidage décrits, phases des feux)
      -> voies (VEX : voies de chaque branche à l'embouchure)
      -> guidage (VEX : lignes de guidage des TAG à l'indonésienne décrits, RF-MQ-CAR-03)
      -> trajectoires (VEX : droite – arc tangent – droite, rayon ≥ véhicule de projet, RF-GV-TRJ-006)
      -> conflits (VEX : croisements, convergences, divergences)
      -> zone (VEX : zone de conflit = cœur + approches jusqu'aux lignes d'arrêt)
      -> fleches (VEX : flèches d'affectation au gabarit exact du dossier 08, figurines des sas)
      -> axe (VEX : discontinue axiale de la route prioritaire prolongée, RF-MQ-CAR-01)
      -> tirets (VEX : tirets T'2 des lignes de guidage)
      -> filtre (VEX : lignes de section retirées dans la zone de conflit et rives au droit des affluentes)
    sorties 1 LIGNES (section courante filtrée + guidage + axe prolongé ; contrat pj::marquage_solide), 2 MARQUES (flèches,
    figurines), 3 DONNÉES (voies, trajectoires, conflits, zone, guidage, table des marques), 4 CONTRÔLES (LIGNES d'entrée
    marquées : rg_l4_retire, rg_l4_raison).
"""
import json
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
GEN = ICI.parents[1]
sys.path.insert(0, str(ICI.parent / "commun"))
sys.path.insert(0, str(GEN))
sys.path.insert(0, str(ICI))
import rg_hda_outils as R  # noqa: E402
import regles  # noqa: E402
import vex_l4 as V  # noqa: E402

VEX_C = (GEN / "hda" / "rg_carrefours" / "vex" / "rg_carrefour.h").read_text(encoding="utf-8") + "\n" + V.L4_H + "\n"
SPEC = (GEN / "hda" / "rg_marquages" / "gabarits_iisr7_pj.json").as_posix()


def _vehicule():
    """Véhicule de projet des trajectoires (lot L3a) : VL ; rayon d'axe minimal guidé et largeur de caisse."""
    sys.path.insert(0, str(GEN))
    from vehicules import balayage as B
    d = json.loads((GEN / "vehicules" / "vehicules_projet.json").read_text(encoding="utf-8"))
    vl = d["vehicules"]["vl"]
    return float(B.rayon_min("vl")), float(vl["dimensions"]["largeur_caisse"]["valeur"])


R_VL, L_VL = _vehicule()


def _garde_guidage():
    """Garde entre la caisse du VL et le bord de la peinture d'une ligne de guidage (correction après le contrôle de
    l'étape 2) : les deux enveloppes balayées des TAG opposés guidés doivent rester séparées de la garde minimale de
    RF-GV-TRJ-006 (1,25 m), la ligne au milieu ; chaque enveloppe (largeur rétroviseurs compris, 2,10 m, VU p. 142)
    reste donc à (1,25 − largeur de la ligne) / 2 du bord de la peinture, soit, pour la caisse (1,80 m) :
    (1,25 − 0,10) / 2 + (2,10 − 1,80) / 2 = 0,725 m."""
    d = json.loads((GEN / "vehicules" / "vehicules_projet.json").read_text(encoding="utf-8"))
    dims = d["vehicules"]["vl"]["dimensions"]
    g_env = float(regles.valeur("RF-GV-TRJ-006", "garde_min_enveloppe"))
    w_gui = float(regles.valeur("RF-MQ-GUI-01", "largeur"))
    return round((g_env - w_gui) / 2.0 + (float(dims["largeur_retroviseurs"]["valeur"]) -
                                          float(dims["largeur_caisse"]["valeur"])) / 2.0, 4)


GARDE_GUIDAGE = _garde_guidage()


def _wr(sub, nom, code, classe, entree, entrees=()):
    return R.wrangle(sub, nom, VEX_C + code, classe, entree, entrees=entrees,
                     bibliotheques=("rg_geometrie.h", "rg_niveau.h", "rg_marquage.h"))


def F(nom, lab, v, aide, mn=0.0, mx=10.0):
    return hou.FloatParmTemplate(nom, lab, 1, default_value=(v,), min=mn, max=mx, help=aide)


def S(nom, lab, v, aide):
    return hou.StringParmTemplate(nom, lab, 1, default_value=(v,), help=aide)


def parms():
    T = hou
    return [
        T.StringParmTemplate("fichier", "Modèle (modele_voie.json)", 1, default_value=("",),
                             string_type=T.stringParmType.FileReference,
                             help="Même fichier que rg::lire_modele (le pilote y renvoie son paramètre) : consignes de "
                                  "flèches, sas, mouvements autorisés, guidage décrit et phases des feux."),
        T.StringParmTemplate("spec", "Gabarits IISR (dossier 08, format pj)", 1, default_value=(SPEC,),
                             string_type=T.stringParmType.FileReference,
                             help="gabarits_iisr7_pj.json du lot L2b (gabarits et glyphes de "
                                  "D:/DocRoute/08_Marquages_Geometrie_IISR7/marquages_iisr7.json), lus par pj::gabarits_iisr."),
        S("vehicule", "Véhicule de projet des trajectoires", "vl",
          "Véhicule du lot L3a (vehicules/vehicules_projet.json) dont le rayon d'axe minimal borne les trajectoires "
          "(RF-GV-TRJ-006 ; plan § 3 L4 : « trajectoires de rayon ≥ véhicule de projet »)."),
        F("r_min_vehicule", "Rayon d'axe minimal du véhicule (m)", round(R_VL, 4),
          "vehicules/balayage.rayon_min('vl') (lot L3a : braquage maximal, empattement 2,875 m).", 1.0, 30.0),
        F("largeur_vehicule", "Largeur de caisse du véhicule (m)", L_VL, "VU p. 142 (vehicules_projet.json, vl).",
          0.5, 4.0),
        F("angle_tout_droit", "Écart angulaire d'un tout-droit (°)", 25.0,
          "Mouvement traité en droite si les directions d'entrée et de sortie diffèrent de moins de cet angle [G].",
          1.0, 60.0),
        F("fleche_arc", "Flèche maximale des arcs (m)", 0.0005, "Échantillonnage des arcs (RF-OSM-CAR-001).", 1e-5, 0.01),
        F("pas_angulaire_arc", "Pas angulaire maximal des arcs (°)", 0.8,
          "Échantillonnage des arcs : la première corde dévie de la tangente de la voie d'un demi-pas (0,4° ≤ 0,5°, tolérance d'orientation du plan § 3 L4) [G], comme les coins du lot L3.", 0.1, 5.0),
        F("garde_guidage", "Garde caisse / peinture de la ligne de guidage (m)", GARDE_GUIDAGE,
          "TAG guidés : la caisse du VL reste à cette distance au moins du bord de la peinture de la ligne de guidage ; "
          "(garde entre enveloppes RF-GV-TRJ-006 − largeur de la ligne RF-MQ-GUI-01) / 2 + (rétroviseurs − caisse) / 2 "
          "(VU p. 142) : les enveloppes balayées des deux TAG opposés restent séparées de la garde minimale (correction "
          "après le contrôle de l'étape 2).", 0.0, 3.0),
        F("guidage_largeur", "Largeur des lignes de guidage par défaut (m)",
          float(regles.valeur("RF-MQ-GUI-01", "largeur")), "RF-MQ-GUI-01, ARB-08 (le modèle prime).", 0.05, 0.3),
        F("tp2_trait", "T'2 : trait (m)", float(regles.valeur("RF-MQ-MOD-T'2", "trait")), "RF-MQ-MOD-T'2.", 0.1, 2.0),
        F("tp2_intervalle", "T'2 : intervalle (m)", float(regles.valeur("RF-MQ-MOD-T'2", "intervalle")),
          "RF-MQ-MOD-T'2.", 0.1, 2.0),
        F("effet_largeur", "Ligne d'effet des feux : largeur (m)", float(regles.valeur("RF-MQ-FEU-01", "largeur")),
          "RF-MQ-FEU-01 (bord amont des lignes : flèches, sas, zone de conflit).", 0.05, 1.0),
        F("cedez_largeur", "Ligne CÉDEZ : largeur (m)", float(regles.valeur("RF-MQ-CED-01", "largeur")),
          "RF-MQ-CED-01.", 0.1, 1.0),
        F("stop_largeur", "Ligne STOP : largeur (m)", float(regles.valeur("RF-MQ-STOP-01", "largeur")),
          "RF-MQ-STOP-01.", 0.1, 1.0),
        F("fleche_fraction_largeur", "Flèches : largeur de voie minimale (fraction)", 0.99,
          "Une flèche n'est posée que si la voie a au moins cette fraction de sa largeur à l'embouchure sous toute la "
          "flèche (voie de stockage formée, hors biseau d'ouverture) ; sinon la série s'arrête (« 2 si la voie est courte », ARB-11) [G].", 0.5, 1.0),
        F("fleche_rectitude", "Flèches : déviation maximale de la voie sous la flèche (°)", 0.5,
          "La flèche est rigide : la série s'arrête là où l'axe de la voie dévie de plus de cet angle sous la flèche "
          "(déport, biseau ; tolérance d'orientation du plan § 3 L4 : ± 0,5°) [G].", 0.05, 5.0),
        F("pas_densification", "Pas de densification des empreintes (m)", 0.25,
          "Arêtes des flèches et des tirets découpées pour le drapé sur le sol (pj::marquage_solide) [G].", 0.02, 1.0),
        F("pas_densification_lignes", "Pas de densification des tirets de l'axe prolongé (m)", 0.10,
          "Tirets de l'axe prioritaire prolongé dans le cœur (sol interpolé, triangulé à 0,5 m) : côtés découpés au pas de "
          "0,10 m pour que le dessus drapé reste à 2 ± 0,3 mm du sol (TQ-MQG-005) [G].", 0.02, 1.0),
        S("gabarit_sas", "Figurine des sas", "VELO", "Gabarit VELO du dossier 08 (RF-MQ-SAS-01 : figurine dans l'axe "
                                                       "de chaque voie de circulation du sas)."),
        F("usure_peinture", "Usure de la peinture", 0.2,
          "Usure des marques ajoutées (le pilote la lit sur les LIGNES de rg::marquages : classe d'usure du modèle).",
          0.0, 1.0),
    ]


def construire(dossier=ICI):
    pt = parms()
    sub = R.sous_reseau("rg_marquages_carrefour")
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(pt))
    e = list(sub.indirectInputs()[:4])
    module = (ICI / "lecteur_marquages_carrefour.py").read_text(encoding="utf-8")
    py = sub.createNode("python", "lecture")
    py.parm("python").set("# Lecture du modèle (module lecteur_marquages_carrefour.py embarqué dans l'HDA)\n"
                          "hou.pwd().parent().hdaModule().lire(hou.pwd())\n")
    gab = sub.createNode("pj::gabarits_iisr::1.0", "gabarits")
    gab.parm("spec").set('`chs("../spec")`')
    gabg = _wr(sub, "groupe_gabarits", 'setprimgroup(0, "gab", @primnum, 1);', "primitive", gab)
    vo = _wr(sub, "voies", V.VEX_VOIES, "detail", py, entrees=(e[0], e[1], e[2]))
    gu = _wr(sub, "guidage", V.VEX_GUIDAGE, "detail", vo, entrees=(e[0], e[1], e[2]))
    tr = _wr(sub, "trajectoires", V.VEX_TRAJECTOIRES, "detail", gu, entrees=(e[0], e[1], e[2]))
    co = _wr(sub, "conflits", V.VEX_CONFLITS, "detail", tr)
    zo = _wr(sub, "zone", V.VEX_ZONE, "detail", co, entrees=(e[0], e[1], e[2]))
    mg = sub.createNode("merge", "flux_et_gabarits")
    mg.setInput(0, zo)
    mg.setInput(1, gabg)
    fl = _wr(sub, "fleches", V.VEX_FLECHES, "detail", mg, entrees=(e[0], e[1], e[2]))
    ax = _wr(sub, "axe", V.VEX_AXE, "detail", fl, entrees=(e[3], e[1], e[2]))
    ti = _wr(sub, "tirets", V.VEX_TIRETS_GUIDAGE, "detail", ax)
    fi = _wr(sub, "filtre", V.VEX_FILTRE, "detail", e[3], entrees=(ti, e[1], e[2]))

    def blast(nom, src, groupe, garder):
        b = sub.createNode("blast", nom)
        b.setInput(0, src)
        b.parm("group").set(groupe)
        b.parm("grouptype").set("prims")
        b.parm("negate").set(1 if garder else 0)
        a = sub.createNode("add", nom + "_points")
        a.setInput(0, b)
        a.parm("remove").set(1)
        return a

    gardees = blast("section_gardee", fi, "@rg_l4_retire=1 @rg_l4_retire=2", False)
    lig_sec = blast("lignes_section", gardees, "@classe=ligne", True)
    mar_sec = blast("marques_section", gardees, "@classe=ligne", False)
    nouvelles = blast("lignes_l4", ti, "axe_l4 tirets_l4", True)
    lig = sub.createNode("merge", "lignes")
    lig.setInput(0, lig_sec)
    lig.setInput(1, nouvelles)
    mar_l4 = blast("marques_l4", ti, "marque_l4", True)
    mar = sub.createNode("merge", "marques")
    mar.setInput(0, mar_sec)
    mar.setInput(1, mar_l4)
    don = sub.createNode("blast", "donnees")
    don.setInput(0, ti)
    don.parm("group").set("marque_l4 axe_l4 tirets_l4 gab")
    don.parm("grouptype").set("prims")
    sorties = ((lig, "LIGNES"), (mar, "MARQUES"), (don, "DONNEES"), (fi, "CONTROLES"))
    for k, (n, nom) in enumerate(sorties):
        nul = sub.createNode("null", nom)
        nul.setInput(0, n)
        R.sortie(sub, nul, k, f"sortie_{nom.lower()}")
        nul.setDisplayFlag(k == 0)
    R.ranger(sub)
    aide = ("Marquages, trajectoires, conflits et zone de conflit des carrefours plans (lot L4, PLAN_GENERATEUR § 2.4 "
            "étapes 7 à 10) : flèches d'affectation au gabarit exact du dossier 08 (pointe de la dernière à 1,50 m de la "
            "ligne, interdistance 20 m), figurines des sas, trajectoires voie à voie droite – arc – droite de rayon ≥ "
            "véhicule de projet, points de conflit, lignes de guidage T'2 0,10 seulement si le modèle les décrit (TAG "
            "à l'indonésienne), zone de conflit sans ligne longitudinale, discontinue axiale de la route prioritaire "
            "prolongée, rives interrompues au droit des affluentes.")
    det = ("== Entrées ==\n\n1. SOLVEUR (rg::carrefours, sortie 3). 2. NIVEAUX (rg::nivellement, sortie 1). "
           "3. Références (rg::graphe, sortie 1). 4. LIGNES + MARQUES (rg::marquages, sorties 1 et 2 fusionnées : classe « ligne » ou autre).\n\n== Sorties ==\n\n"
           "1. LIGNES (contrat pj::marquage_solide : section courante filtrée, guidage, axe prolongé).\n"
           "2. MARQUES (marques de section filtrées : passages hors terre-pleins ; flèches et figurines des sas du lot).\n3. DONNÉES : points br4 / fl / mv (modèle), voie (embouchure, "
           "limite de jonction s_j), conflit, table_l4 ; polylignes trajectoire_l4 et guidage ; polygones "
           "zone_conflit.\n4. CONTRÔLES : LIGNES d'entrée avec rg_l4_retire (1 zone de conflit, 2 rive) et "
           "rg_l4_raison.\n\nRègles : RF-GV-TRJ-006, RF-MQ-GUI-01, RF-MQ-GUI-03, RF-MQ-CAR-01 à -04, RF-MQ-SC-11, "
           "DEF-017, DEF-021, ARB-08, ARB-11, RF-MQ-DIR-02/-03/-04/-09, RF-MQ-SAS-01, DEF-016 ; choix [G] : rayon "
           "des raccords de la ligne de guidage, phase des tirets, répartition des tirets de l'axe prolongé, fraction "
           "de largeur des flèches, flèches cyclables absentes, vélos en tout droit.")
    return R.creer_hda(sub, "marquages_carrefour", "RG Marquages des carrefours (trajectoires, guidage, zone de conflit)",
                       pt, dossier, entrees=(4, 4), sorties=4, aide=aide, details_aide=det, module_python=module,
                       icone="SOP_attribwrangle",
                       etiquettes_entrees=("Solveur (rg::carrefours, sortie 3)", "Niveaux (rg::nivellement, sortie 1)",
                                           "Références (rg::graphe, sortie 1)", "Lignes et marques (rg::marquages, sorties 1 + 2)"),
                       etiquettes_sorties=("Lignes", "Marques", "Données", "Contrôles"))


if __name__ == "__main__":
    print(construire())
