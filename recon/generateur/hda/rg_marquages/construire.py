"""Construit l'HDA rg::marquages::1.0 (lot L2b : marquages au sol de la section courante, empreintes exactes) ;
hython Houdini 22.

    hython recon/generateur/hda/rg_marquages/construire.py

Réseau (recon/generateur/hda/README_RG.md § 6) :
    entrée 1 références (rg::graphe), 2 niveaux (rg::nivellement, sortie 1), 3 profils (rg::lire_modele, sortie 5),
    4 ponctuels (rg::lire_modele, sortie 4)
    gabarits (pj::gabarits_iisr::1.0, réutilisée telle quelle, spécification = gabarits_iisr7_pj.json : gabarits et
              glyphes du dossier 08) ─┐
    ponctuels ────────────────────────┴ fusion ─► marquages (VEX, détail) ─► LIGNES (empreintes, peinture 2 mm)
                                                                         ├► MARQUES (empreintes, enduit 3 mm)
                                                                         └► TABLE (un point par marque)
Les empreintes vont ensuite à pj::marquage_solide::1.0 (deux instances : épaisseur 2 mm et 3 mm, TQ-MQG-002), drapé sur
le sol fabriqué par rg::sol (entrée 3 : TQ-MQG-005).

Houdini n'invente rien : modulations (RF-MQ-MOD-*), largeurs (largeur_u × u_m du modèle), intervalles et interruptions
(modèle), passages (zone du modèle ; nombre de bandes et marges : DEF-011, RF-MQ-PP-05), flèches, triangles, figurines et
lettres (gabarits et glyphes exacts du dossier 08, posés à l'ancrage et au cap du modèle), hachures (DEF-020,
RF-MQ-HACH-01, RF-MQ-HACH-03, RF-MQ-MUS-01). Choix sans règle, déclarés « [G] » (comme le lot catalogue) : phase des
tirets (chaque tronçon commence par un trait ; un trait tronqué est gardé s'il fait au moins la moitié d'un trait) ;
dégagement de 2u bord à bord entre deux lignes qui convergent (la discontinue s'arrête, RF-MQ-MUS-01 par analogie).
"""
import json
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
GEN = ICI.parents[1]
sys.path.insert(0, str(ICI.parent / "commun"))
sys.path.insert(0, str(GEN))
import rg_hda_outils as R  # noqa: E402
import regles  # noqa: E402

NOM = "marquages"
SPEC = (ICI / "gabarits_iisr7_pj.json").as_posix()
MODULATIONS = ("T1", "T'1", "T2", "T'2", "T3", "T'3", "T4")


def table_modulations():
    """RF-MQ-MOD-<m> (IISR7 art. 113-1 B, tableau p. 6) : trait, intervalle."""
    out = []
    for m in MODULATIONS:
        v = regles.valeur(f"RF-MQ-MOD-{m}")
        out.append((m, float(v["trait"]), float(v["intervalle"])))
    return out


def vex_principal():
    """Corps du wrangle (marquages.vfl) avec la table des modulations RF-MQ-MOD-* recopiée de regles_route_fr.json."""
    mods = table_modulations()
    tab = ("string MODS[] = {" + ", ".join(f'"{m}"' for m, _, _ in mods) + "};\n"
           "float TRAITS[] = {" + ", ".join(f"{t!r}" for _, t, _ in mods) + "};\n"
           "float VIDES[] = {" + ", ".join(f"{v!r}" for _, _, v in mods) + "};\n")
    corps = (ICI / "marquages.vfl").read_text(encoding="utf-8-sig")
    return corps.replace("//@@MODULATIONS@@\n", tab)


def parametres():
    T = hou
    F = T.FloatParmTemplate
    d20 = regles.valeur("DEF-020")
    d11 = regles.valeur("DEF-011")
    return [
        T.StringParmTemplate("spec", "Gabarits IISR (dossier 08, format pj)", 1, default_value=(SPEC,),
                             string_type=T.stringParmType.FileReference, file_type=T.fileType.Any,
                             help="gabarits_iisr7_pj.json (gabarits_iisr7.py) : gabarits et glyphes de "
                                  "D:/DocRoute/08_Marquages_Geometrie_IISR7/marquages_iisr7.json, lus par pj::gabarits_iisr."),
        F("fraction_trait", "Trait tronqué gardé (fraction du trait)", 1, default_value=(0.5,), min=0.0, max=1.0,
          help="[G] choix du catalogue (scenes_simples/description.py, FRACTION_TRAIT_TRONQUE) : chaque tronçon de ligne "
               "commence par un trait ; un trait tronqué en fin de tronçon est gardé s'il fait au moins cette fraction "
               "du trait (la phase n'est pas fixée par l'IISR)."),
        F("degagement_u", "Dégagement entre lignes et bordures (u)", 1, default_value=(2.0,), min=0.0, max=10.0,
          help="RF-MQ-MUS-01 : espace non peint de 2u (zébra ; lignes qui convergent, par analogie : choix [G])."),
        F("pp_bande", "Passage piéton : largeur des bandes (m)", 1, default_value=(float(d11["bande"]),), min=0.1,
          max=1.0, help="DEF-011 (RF-MQ-PP-02) : bandes de 0,50 m."),
        F("pp_marge_min", "Passage piéton : intervalle minimal e (m)", 1, default_value=(0.5,), min=0.1, max=1.0,
          help="RF-MQ-PP-05 / DEF-011 : e = (W − 0,50 n)/(n + 1) dans [0,50 ; 0,80], n maximal = floor(W − 0,50)."),
        F("hach_bande", "Hachures : largeur des bandes (m)", 1, default_value=(float(d20["bande"]),), min=0.1, max=1.0,
          help="DEF-020, RF-MQ-HACH-01 : 0,50."),
        F("hach_espacement", "Hachures : espacement entre parallèles (m)", 1, default_value=(float(d20["espacement"]),),
          min=0.1, max=5.0, help="DEF-020, RF-MQ-HACH-01 : 1,35."),
        F("hach_angle", "Hachures : angle avec la rive (°)", 1, default_value=(float(d20["angle_rive_deg"]),), min=1.0,
          max=89.0, help="DEF-020, RF-MQ-HACH-01 : 2 parallèlement à la rive pour 1 perpendiculairement (26,565°)."),
        F("hach_aplat", "Hachures : aplat sous la largeur (m)", 1, default_value=(float(d20["aplat_si_largeur_inf"]),),
          min=0.0, max=2.0, help="DEF-020, RF-MQ-HACH-03 : aplat (peinture uniforme) où la zone a moins de 0,30 m ; "
                                 "phase : une bande commence là où la zone atteint 0,30 m (dossier 08, "
                                 "parametres_generateur_par_defaut.hachures_phase)."),
        F("espacement_caracteres", "Inscriptions : espacement des caractères (m)", 1, default_value=(0.15,), min=0.0,
          max=1.0, help="IISR7 annexe D.2 p. 69 (dossier 08, glyphes.repere)."),
        F("pas_fin", "Pas en long sur un dos-d'âne (m)", 1, default_value=(0.05,), min=0.005, max=1.0,
          help="Sommets des empreintes sur un sol courbe en long (dos-d'âne, R ≈ 20 m) : la peinture drapée sommet par "
               "sommet s'écarte du sol de moins de 0,1 mm entre deux sommets."),
        F("pas_symboles", "Arêtes des symboles (m)", 1, default_value=(0.25,), min=0.01, max=5.0,
          help="Longueur maximale d'une arête de symbole (drapé)."),
        F("corde", "Flèche des arêtes en courbe (m)", 1, default_value=(0.0001,), min=1e-6, max=0.01,
          help="Pas en long des empreintes sur une route courbe : flèche ≤ 0,1 mm."),
        F("u_defaut", "u par défaut (m)", 1, default_value=(float(regles.valeur("DEF-001")["autres_routes"]),),
          min=0.01, max=0.1, help="DEF-001 : u = 0,05 m (autres routes), si le modèle ne le dit pas."),
    ]


def construire(dossier=ICI):
    import gabarits_iisr7 as G
    G.ecrire()                                       # spécification dérivée à jour (même octets si inchangée)
    sub = R.sous_reseau("rg_" + NOM)
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres()))
    e1, e2, e3, e4 = sub.indirectInputs()[:4]
    gab = sub.createNode("pj::gabarits_iisr::1.0", "gabarits")
    gab.parm("spec").set('`chs("../spec")`')
    fus = sub.createNode("merge", "ponctuels_et_gabarits")
    fus.setInput(0, e4)
    fus.setInput(1, gab)
    w = R.wrangle(sub, "marquages", vex_principal(), "detail", e3, entrees=(e1, e2, fus),
                  bibliotheques=("rg_geometrie.h", "rg_niveau.h", "rg_marquage.h"))
    mat = w
    lig = sub.createNode("blast", "lignes")
    lig.setInput(0, mat)
    lig.parm("group").set("@rg_ligne==1")
    lig.parm("grouptype").set("prims")
    lig.parm("negate").set(1)
    aut = sub.createNode("blast", "autres_marques")
    aut.setInput(0, mat)
    aut.parm("group").set("@rg_ligne==1")
    aut.parm("grouptype").set("prims")
    tab = sub.createNode("blast", "table")
    tab.setInput(0, mat)
    tab.parm("group").set("*")
    tab.parm("grouptype").set("prims")
    tab2 = sub.createNode("blast", "table_points")
    tab2.setInput(0, tab)
    tab2.parm("group").set("table")
    tab2.parm("grouptype").set("points")
    tab2.parm("negate").set(1)
    outs = []
    for k, (n, nom) in enumerate(((lig, "LIGNES"), (aut, "MARQUES"), (tab2, "TABLE"))):
        o = sub.createNode("null", nom)
        o.setInput(0, n)
        R.sortie(sub, o, k, f"sortie_{k + 1}")
        outs.append(o)
    outs[0].setDisplayFlag(True)
    R.ranger(sub)
    aide = ("Empreintes exactes des marquages de la section courante (lignes à modulation IISR, passages piétons, "
            "flèches, triangles de dos-d'âne, figurines, inscriptions, zébras), découpées aux lignes de rupture du "
            "sol et hors bordures et caniveaux ; à extruder et draper par pj::marquage_solide.")
    details = ("== Entrées ==\n\n1. Références (rg::graphe), 2. Niveaux (rg::nivellement, sortie 1), 3. Profils "
               "(rg::lire_modele, sortie 5), 4. Ponctuels (rg::lire_modele, sortie 4).\n\n== Sorties ==\n\n"
               "1. Lignes longitudinales (polygones plans, peinture 2 mm, TQ-MQG-002).\n2. Autres marques (enduit 3 mm).\n"
               "3. Table : un point par marque (classe, id, route, clé de limite, modulation, s0, s1, t, cap, gabarit, "
               "n, e, W).\n\nRègles : RF-MQ-MOD-*, RF-MQ-LAR-*, DEF-011, RF-MQ-PP-02 à -05, DEF-017, RF-MQ-RAB-*, "
               "RF-MQ-RAL-01, DEF-020, RF-MQ-HACH-01, -03, RF-MQ-MUS-01, RF-MA-CYC-012, RF-MQ-TC-03, MQ-DET-010, "
               "TQ-MQG-014 ; gabarits du dossier 08 (IISR7 annexes B et D).")
    return R.creer_hda(sub, NOM, "RG Marquages (empreintes de la section courante)", parametres(), dossier,
                       entrees=(4, 4), sorties=3, aide=aide, details_aide=details, icone="SOP_polyextrude",
                       etiquettes_entrees=("Références échantillonnées", "Niveaux", "Profils", "Ponctuels"),
                       etiquettes_sorties=("Lignes (empreintes)", "Autres marques (empreintes)", "Table des marques"))


if __name__ == "__main__":
    sys.path.insert(0, str(ICI))
    print(construire())
