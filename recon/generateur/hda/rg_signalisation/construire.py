"""Construit l'HDA rg::signalisation::1.0 (lot L6, étape E14 : signalisation verticale et feux) ; hython Houdini 22.

    hython recon/generateur/hda/rg_signalisation/construire.py

rg::signalisation (« RG Signalisation verticale et feux ») :
    entrées 1 SOL fabriqué (attribut de primitive « classe » : rg::sol + rg::carrefours_sol + rg::giratoires_sol +
            rg::autoroute), 2 RÉFÉRENCES (rg::graphe, sortie 1 : prims « id », points « s »), 3 OBSTACLES (facultatif :
            dispositifs de retenue, rg::autoroute sortie 2)
    paramètre « Plan de signalisation » : rg_plan_signalisation/0.1 (plan_signalisation.py, hors Houdini)
      -> lire_ensembles, lire_exclusions (Python SOP : seul Python, lecture du plan)
      -> classer (VEX : classes du sol), rive_plat (chaussée à plat), exclusions (abaissés), obstacles -> CONTEXTE
      -> placer (VEX : ARB-20, cheminement, rive, hauteur, orientation, empilement, feux, supports, contrôles)
      -> plaques (VEX : plaques des faces composées)
    sorties 1 ENSEMBLES (un point par support, contrôles), 2 INSTANCES (un point par plaque, tête de feu, balise ou
            support : asset, gamme, face, orient, échelle ; points pj_points), 3 PLAQUES (maillages des faces composées,
            uv), 4 CONTEXTE (sol classé, rive à plat, zones interdites : contrôle).

Houdini n'invente rien : chaque distance est un paramètre dont le défaut est écrit ici depuis la base fusionnée
(DEF-025, DEF-027, ARB-20, RF-SV-GEN.*, RF-MA-TRO-*, RF-FEU.*) ou les compléments du lot
(hda/rg_signalisation/regles_signalisation_l6.json), règle citée dans l'aide ; choix de fabrication marqués [G].
"""
import json
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
GEN = ICI.parents[1]
DEPOT = GEN.parents[1]
sys.path.insert(0, str(ICI.parent / "commun"))
sys.path.insert(0, str(GEN))
sys.path.insert(0, str(ICI))
import rg_hda_outils as R  # noqa: E402
import regles  # noqa: E402
import vex_signalisation as VS  # noqa: E402

NOM = "signalisation"
CATALOGUE = DEPOT / "assets" / "specs" / "route" / "catalogue_assets_route.json"
L6 = {r["id"]: r for r in json.loads((ICI / "regles_signalisation_l6.json").read_text(encoding="utf-8"))["regles"]}

CLASSES = {
    "classes_chaussee": ("voie_circulation voie_bus voie_tourne_gauche voie_tourne_droite voie_insertion "
                         "voie_deceleration voie_acceleration voie_stockage bande_cyclable stationnement livraison "
                         "chaussee_partagee carrefour_chaussee zone_neutralisee musoir sous_element caniveau_releve tampon",
                         "chaussée : référence de la rive (RF-SV-GEN.DISTANCE_RIVE) ; zone neutralisée = îlot peint "
                         "(jamais de support, RF-SV-GEN.EMPLACEMENT)"),
    "classes_circulees": ("bande_derasee bande_arret_urgence accotement_revetu surlargeur piste_cyclable voie_verte",
                          "surfaces circulées ou circulables hors chaussée : aucun support (PLAN_GENERATEUR L6)"),
    "classes_pietons": ("trottoir carrefour_trottoir quai_bus chemin_pieton",
                        "surfaces piétonnes : cheminement libre de 1,40 m (RF-MA-TRO-001, ARB-20)"),
    "classes_ilots": ("terre_plein carrefour_ilot giratoire_ilot separateur ilot",
                      "îlots et terre-pleins bordés (RF-SV-GEN.EMPLACEMENT : îlot, terre-plein central)"),
    "classes_accotements": ("berme carrefour_accotement accotement terre_plein_lateral bande_plantee talus fosse noue",
                            "accotements non revêtus (rase campagne : RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE)"),
    "classes_abords": ("abord", "abords du modèle, hors de l'emprise décrite (admis en rase campagne, signalé)"),
    "classes_interdites": ("sous_bordure mur sol_cache", "corps de bordure, murs, sols cachés"),
}


def catalogue():
    d = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    return {a["id"]: a for a in d["assets"]}


def supports_ronds():
    """id:diamètre:hauteur des supports ronds du catalogue route_fr (IISR1 art. 6 B : Ø 48,3 / 60,3 / 76)."""
    out = []
    for aid, a in sorted(catalogue().items()):
        if (aid.startswith("support_rond_") and "platine" not in aid) or aid.startswith("mat_directionnel_"):
            dm = a.get("dimensions") or {}
            out.append(f"{aid}:{dm['d1_m']:.4f}:{dm['hauteur_m']:.2f}")
    return " ".join(out)


def parametres():
    F, S, I = hou.FloatParmTemplate, hou.StringParmTemplate, hou.IntParmTemplate
    d25, d27 = regles.valeur("DEF-025"), regles.valeur("DEF-027")
    a20 = regles.valeur("ARB-20")
    cat = catalogue()
    mod = cat["feu_R11v_D200"]["dimensions"]["module_h_m"]
    pp = [S("fichier", "Plan de signalisation", 1, default_value=("",), string_type=hou.stringParmType.FileReference,
            help="rg_plan_signalisation/0.1 écrit par hda/rg_signalisation/plan_signalisation.py (hors Houdini).")]
    for k, (v, h) in CLASSES.items():
        pp.append(S(k, k.replace("_", " ").capitalize(), 1, default_value=(v,), help=h))
    pp += [
        S("materiaux_franchissables", "Matériaux franchissables d'îlot", 1, default_value=("paves_beton paves_granit",),
          help="Îlot de giratoire ou de carrefour revêtu de ces matériaux : couronne ou bande franchissable "
               "(RF-GV-GIR-006) : surface circulable, aucun support."),
        S("materiaux_refuges", "Matériaux des refuges revêtus", 1, default_value=("",),
          help="Îlot de giratoire ou de carrefour revêtu de ces matériaux : refuge du passage (RF-OBS-ILO-01) : aucun support."),
        F("bord_rive", "Bord du panneau à la rive (m)", 1, default_value=(float(regles.valeur("RF-SV-GEN.DISTANCE_RIVE", "min_m")),),
          help="RF-SV-GEN.DISTANCE_RIVE (IISR1 art. 8 i, p. 18) ; DEF-025 bord_panneau_a_la_rive."),
        F("cheminement", "Cheminement libre (m)", 1, default_value=(float(a20["cheminement_libre_m"]),),
          help="ARB-20 ; RF-MA-TRO-001 (A2007 art. 1, 3°, p. 1)."),
        F("surplomb", "Passage libre sous une plaque en surplomb (m)", 1, default_value=(float(a20["surplomb_min_m"]),),
          help="ARB-20 (A2007 art. 1, 6° c-d, p. 2)."),
        F("support_rase_campagne", "Support à la rive en rase campagne (m)", 1,
          default_value=(float(regles.valeur("RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE", "support_min_m")),),
          help="RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE (IISR1 art. 8 i) : support à ≥ 2 m du bord (zone de récupération "
               "non décrite)."),
        F("ecart_plaques", "Écart entre plaques (m)", 1, default_value=(float(L6["L6-SV-EMPILEMENT.ECART"]["valeurs"]["ecart_m"]),),
          help="[G] L6-SV-EMPILEMENT.ECART."),
        F("depassement", "Dépassement du support (m)", 1,
          default_value=(float(L6["L6-SV-SUPPORT.DEPASSEMENT"]["valeurs"]["depassement_m"]),), help="[G] L6-SV-SUPPORT.DEPASSEMENT."),
        F("espacement", "Distance entre supports (m)", 1,
          default_value=(float(L6["L6-SV-ESPACEMENT.SUPPORTS"]["valeurs"]["min_m"]),), help="[G] L6-SV-ESPACEMENT.SUPPORTS."),
        F("pas", "Pas de la recherche (m)", 1, default_value=(0.05,), min=0.01, max=0.5,
          help="[G] pas des anneaux de recherche du point admissible le plus proche du point visé."),
        F("rayon_max", "Rayon de recherche (m)", 1, default_value=(6.0,), help="[G] rayon maximal de la recherche."),
        F("pas_marche", "Pas des marches latérales (m)", 1, default_value=(0.02,), help="[G] mesure de la rive."),
        F("trou_rive", "Îlot franchi pour trouver la rive (m)", 1, default_value=(5.0,),
          help="[G] la rive d'un panneau de droite est le bord extérieur de la chaussée du sens visé : un îlot ou "
               "terre-plein de moins de 5,00 m entre deux couloirs (îlot de TAG bordé) est franchi."),
        F("vue_abaisse", "Vue du fond d'un abaissé (m)", 1,
          default_value=(float(regles.valeur("DEF-031", "vue")) + 0.01,),
          help="DEF-031 (vue d'un abaissé 0,02) + 0,01 m [G] : fond de l'abaissé, aucun support. La zone d'attente "
               "derrière le bateau (1,20 m de part et d'autre de la face) est exclue par le plan (exclusions)."),
        F("collier", "Saillie du collier (m)", 1, default_value=(0.06,),
          help="Catalogue route_fr, panneaux : pose.accroche (face à Y = rayon du poteau + 0,06 m)."),
        F("lacet_ext", "Rotation vers l'extérieur (°)", 1, default_value=(float(d25["lacet_vers_exterieur_deg"]),),
          help="DEF-025 ; RF-SV-GEN.ORIENTATION.GENERATEUR (3 à 6°) ; RF-SV-GEN.ORIENTATION (IISR1 art. 8 a)."),
        F("axe_mat_feu", "Axe du mât de feux à la rive (m)", 1,
          default_value=(float(regles.valeur("RF-FEU.POSITION.GENERATEUR", "axe_mat_depuis_rive_m")),),
          help="RF-FEU.POSITION.GENERATEUR ; DEF-027 (0,70 [G] si 1,40 m restent libres, sinon ARB-20)."),
        F("bras_feu", "Avancée de la tête de feu (m)", 1, default_value=(0.30,),
          help="[G] dos du module feu_R11v_D200 (y = −0,265, catalogue) + 0,035 m de fixation."),
        F("retrait_min", "Retrait minimal du support (m)", 1, default_value=(0.15,),
          help="[G] distance minimale support - rive au cas 3 d'ARB-20 (axe réduit)."),
        F("axe_feu_max", "Axe du feu supérieur maximal (m)", 1,
          default_value=(float(regles.valeur("RF-FEU.HAUTEUR.TROTTOIR", "axe_feu_superieur_max_m")),),
          help="RF-FEU.HAUTEUR.TROTTOIR (IISR6 art. 109-4, fig. 16)."),
        F("bas_feu_min", "Gabarit sous le feu (m)", 1,
          default_value=(float(regles.valeur("RF-FEU.HAUTEUR.TROTTOIR", "gabarit_libre_sous_signal_min_m")),),
          help="RF-FEU.HAUTEUR.TROTTOIR (IISR6 art. 109-4, fig. 16)."),
        F("module_feu", "Hauteur d'un module de feu (m)", 1, default_value=(float(mod),),
          help="Catalogue route_fr feu_R11v_D200 (module_h_m)."),
        S("supports_ronds", "Supports ronds du catalogue", 1, default_value=(supports_ronds(),),
          help="id:diamètre:hauteur des supports support_rond_* du catalogue route_fr (IISR1 art. 6 B)."),
        F("epaisseur_plaque", "Épaisseur des plaques composées (m)", 1,
          default_value=(float(cat["panneau_A13a"]["params"]["bord_tombe"]),),
          help="Catalogue route_fr, panneaux : bord tombé de 25 mm."),
    ]
    return pp


def construire(dossier=ICI):
    sub = R.sous_reseau("rg_" + NOM)
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres()))
    e1, e2, e3 = sub.indirectInputs()[:3]
    lecteur = (ICI / "lecteur_signalisation.py").read_text(encoding="utf-8")
    pys = {}
    for fn in ("lire_ensembles", "lire_exclusions"):
        py = sub.createNode("python", fn)
        py.parm("python").set(f"# Lecteur du plan (module lecteur_signalisation.py embarqué dans l'HDA)\n"
                              f"hou.pwd().parent().hdaModule().{fn}(hou.pwd())\n")
        pys[fn] = py
    cla = R.wrangle(sub, "classer", VS.VEX_CLASSER, "detail", e1)
    riv = R.wrangle(sub, "rive", VS.VEX_RIVE_PLAT, "primitive", cla)
    riv_p = R.wrangle(sub, "rive_a_plat", VS.VEX_APLATIR, "point", riv)
    riv_g = R.wrangle(sub, "rive_groupe", "i@group_rive_plat = 1;\ni@group_sol = 0;", "primitive", riv_p)
    vide = sub.createNode("blast", "vide")
    vide.setInput(0, pys["lire_exclusions"])
    vide.parm("group").set("*")
    vide.parm("grouptype").set("points")
    exc = R.wrangle(sub, "exclusions", VS.VEX_EXCLUSIONS, "detail", vide, entrees=(pys["lire_exclusions"],))
    obs_p = R.wrangle(sub, "obstacles_a_plat", "@P.y = 0.0;", "point", e3)
    obs = R.wrangle(sub, "obstacles", 'i@obstacle = 1;\ns@motif = "retenue";', "primitive", obs_p)
    interdits = sub.createNode("merge", "interdits")
    interdits.setInput(0, exc)
    interdits.setInput(1, obs)
    ctx = sub.createNode("merge", "contexte")
    for k, n in enumerate((cla, riv_g, interdits)):
        ctx.setInput(k, n)
    anc = R.wrangle(sub, "ancrer", VS.VEX_ANCRER, "point", pys["lire_ensembles"], entrees=(e2,))
    pla = R.wrangle(sub, "placer", VS.VEX_PLACER, "detail", anc, entrees=(cla, riv_p, interdits))
    ens = sub.createNode("blast", "ensembles")
    ens.setInput(0, pla)
    ens.parm("group").set("instance")
    ens.parm("grouptype").set("points")
    ins = sub.createNode("blast", "instances")
    ins.setInput(0, pla)
    ins.parm("group").set("instance")
    ins.parm("grouptype").set("points")
    ins.parm("negate").set(1)
    vide2 = sub.createNode("blast", "vide_plaques")
    vide2.setInput(0, ins)
    vide2.parm("group").set("*")
    vide2.parm("grouptype").set("points")
    pla2 = R.wrangle(sub, "plaques", VS.VEX_PLAQUES, "detail", vide2, entrees=(ins,))
    ctl = R.wrangle(sub, "controles", VS.VEX_CONTROLES, "detail", ens)
    outs = []
    for k, (n, nom) in enumerate(((ctl, "ENSEMBLES"), (ins, "INSTANCES"), (pla2, "PLAQUES"), (ctx, "CONTEXTE"))):
        o = sub.createNode("null", nom)
        o.setInput(0, n)
        R.sortie(sub, o, k, f"sortie_{k + 1}")
        outs.append(o)
    outs[0].setDisplayFlag(True)
    R.ranger(sub)
    aide = ("Signalisation verticale et feux (lot L6, étape E14) : place les ensembles du plan de signalisation sur le "
            "sol fabriqué par la règle de placement ARB-20 (bord du panneau à 0,70 m de la rive si 1,40 m de "
            "cheminement restent libres ; sinon support côté façade et plaque en surplomb à ≥ 2,20 m ; sinon axe réduit "
            "signalé « IISR1 8 i, contrainte »), refuse toute surface circulée, îlot peint, abaissé ou emprise de "
            "retenue, empile les plaques depuis la hauteur réglementaire, pose les têtes de feux et oriente les faces "
            "vers l'usager.")
    details = ("== Entrées ==\n\n1. Sol fabriqué (attribut « classe »).\n2. Références (rg::graphe, sortie 1).\n"
               "3. Obstacles (dispositifs de retenue, facultatif).\n\n== Sorties ==\n\n1. ENSEMBLES : un point par "
               "support ; statut (ok, contrainte, echec), motif, cas_arb20, d_rive_axe, bord_rive, cheminement_libre, "
               "bas_reel, ds, dt, z_sol, lacet_usd.\n2. INSTANCES : asset du catalogue route_fr, gamme, face, "
               "orient, echelle, lacet_usd.\n3. PLAQUES : faces composées (materiau_id « face:<png> », uv).\n"
               "4. CONTEXTE : sol classé (cl), rive à plat, zones interdites.\n\nRègles : DEF-025, DEF-026, DEF-027, "
               "ARB-04, ARB-05, ARB-14, ARB-19, ARB-20, RF-SV-GEN.*, RF-FEU.*, RF-MA-TRO-001, RF-MA-TRO-015 ; "
               "compléments L6-* (regles_signalisation_l6.json).")
    return R.creer_hda(sub, NOM, "RG Signalisation verticale et feux", parametres(), dossier, entrees=(2, 3), sorties=4,
                       aide=aide, details_aide=details, module_python=lecteur, icone="SOP_copytopoints",
                       etiquettes_entrees=("Sol fabriqué (classe)", "Références (rg::graphe)", "Obstacles (retenue)"),
                       etiquettes_sorties=("Ensembles (supports, contrôles)", "Instances (assets)", "Plaques composées",
                                           "Contexte"))


if __name__ == "__main__":
    print(construire())
