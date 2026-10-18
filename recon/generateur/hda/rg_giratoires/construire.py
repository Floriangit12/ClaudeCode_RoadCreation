"""Construit les HDA du lot L5 (partie giratoires) : rg::giratoires::1.0 (solveur des giratoires) et
rg::giratoires_sol::1.0 (îlots posés : couronne franchissable, îlot central, dôme du mini-giratoire, îlots séparateurs ;
marques de l'anneau) ; hython Houdini 22.

    hython recon/generateur/hda/rg_giratoires/construire.py

rg::giratoires (« RG Giratoires (solveur) », PLAN_GENERATEUR § 2.4 étape 4 « giratoire ») branché après rg::carrefours :
    entrées 1 routes, 2 profils, 3 SOLVEUR de rg::carrefours (sorties 1, 2, 3)
      -> giratoires (Python SOP, module lecteur_giratoires.py : anneau, raccordements, branches, îlots, passages,
         profil de la route d'anneau)
      -> anneaux (VEX : rayons des limites du profil de l'anneau, bord extérieur R0 de la chaussée annulaire)
      -> branches (VEX : repère, bords de chaussée, congés d'entrée Re et de sortie Rs tangents au bord réel et au
         cercle R0, coupes des trottoirs)
      -> coins (VEX : faces de bordure amorce + congé de sortie + anneau + congé d'entrée + amorce, frontière fermée)
      -> embouchures (VEX de rg::carrefours, VEX_NEZ)
      -> couper_routes (VEX de rg::carrefours) -> sans_anneaux (routes d'anneau retirées) ; profils_reduits (VEX de
         rg::carrefours, profils déjà présents gardés)
      -> SOLVEUR fusionné : SOLVEUR des carrefours plans (îlots des giratoires retirés) + branches, coins, embouchures,
         frontières et passages des giratoires (contrat de rg::carrefours : rg::carrefours_sol fabrique le cœur)
    sorties 1 routes coupées (sans anneaux), 2 profils (+ réduits), 3 SOLVEUR fusionné, 4 GIRATOIRES.
rg::giratoires_sol (« RG Giratoires (îlots posés, marques de l'anneau) ») :
    entrées 1 GIRATOIRES (rg::giratoires, sortie 4), 2 sol sans îlots (rg::sol + rg::carrefours_sol)
      -> faces (bordures : couronne, îlot central, îlots séparateurs ; abaissés ; pied sur le sol posé)
      -> dessus polaires (couronne en pente, îlot central, dôme) + dessus des îlots séparateurs (Triangulate 2D) ; jupes
      -> contrat de rg::sol ; BEV (code de rg::carrefours_sol) ; ENTITÉS (code de rg::carrefours_sol) ; MARQUES
    sorties 1 SOL des îlots, 2 BEV, 3 ENTITÉS (contrat pj::bordure), 4 MARQUES (contrat pj::marquage_solide),
    5 CONTRÔLES (faces de bordure, pied, abaissés).
"""
import importlib.util
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
GEN = ICI.parents[1]
CAR = ICI.parent / "rg_carrefours"
sys.path.insert(0, str(ICI.parent / "commun"))
sys.path.insert(0, str(GEN))
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(CAR))
import rg_hda_outils as R  # noqa: E402
import regles  # noqa: E402
import vex_solveur as VS  # noqa: E402  (rg::carrefours : coupes, profils réduits, embouchures)
import vex_sol as VL  # noqa: E402      (rg::carrefours_sol : BEV, entités)
import vex_giratoires as VG  # noqa: E402
import vex_giratoires_sol as VGS  # noqa: E402

VEX_C = ((CAR / "vex" / "rg_carrefour.h").read_text(encoding="utf-8") + "\n"
         + (ICI / "vex" / "rg_giratoire.h").read_text(encoding="utf-8") + "\n")

D31 = regles.defaut("DEF-031")["valeur"]
D11 = regles.defaut("DEF-011")["valeur"]


def _wr(sub, nom, code, classe, entree, entrees=()):
    return R.wrangle(sub, nom, VEX_C + code, classe, entree, entrees=entrees,
                     bibliotheques=("rg_geometrie.h", "rg_niveau.h"))


def _table_bases():
    spec = importlib.util.spec_from_file_location("construire_rg_nivellement_tab", GEN / "hda" / "rg_nivellement" / "construire.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    lignes, src = m.table_profils()
    return ",".join(f"{n}:{b:.4f}" for n, fam, b, H, hfe, dhc in lignes if fam != "caniveau"), src


def _table_modulations():
    out = []
    for m in ("T1", "T'1", "T2", "T'2", "T3", "T'3", "T4"):
        v = regles.regle("RF-MQ-MOD-" + m)["valeurs"]
        out.append(f"{m}:{float(v['trait']):.4f}:{float(v['intervalle']):.4f}")
    return ",".join(out)


def F(nom, lab, v, aide, mn=0.0, mx=10.0):
    return hou.FloatParmTemplate(nom, lab, 1, default_value=(v,), min=mn, max=mx, help=aide)


def S(nom, lab, v, aide):
    return hou.StringParmTemplate(nom, lab, 1, default_value=(v,), help=aide)


def parms_solveur():
    T = hou
    return [
        T.StringParmTemplate("fichier", "Modèle (modele_voie.json)", 1, default_value=("",),
                             string_type=T.stringParmType.FileReference,
                             help="Même fichier que rg::lire_modele (le pilote y renvoie son paramètre) : carrefours de "
                                  "type giratoire et mini_giratoire (anneau, raccordements), îlots, passages et profil de "
                                  "la route d'anneau sont lus ici."),
        F("amorce", "Amorce droite des bordures de coin (m)", 3.0,
          "Longueur droite de la bordure de coin avant le point de tangence du congé, prise sur la branche (le trottoir "
          "de la branche est coupé d'autant). Même choix de fabrication [G] que rg::carrefours.", 0.0, 10.0),
        F("rampant_passage", "Rampant gardé sur la bordure de coin (m)", float(D31["rampant_5pct"]),
          "Un passage qui touche le coin garde tout son abaissé et ses rampants (DEF-031 : 2,40 m à 5 %) sur la "
          "bordure de coin : la coupe du trottoir de la branche recule jusqu'avant le rampant.", 0.0, 10.0),
        F("garde_passage", "Garde avant le rampant (m)", 0.10,
          "Marge entre la coupe du trottoir et le début du rampant de l'abaissé (choix de fabrication [G]).", 0.0, 2.0),
        F("fleche", "Flèche maximale des arcs (m)", 0.0005,
          "Échantillonnage des congés et de l'anneau : flèche ≤ 0,5 mm (RF-OSM-CAR-001, critère L1).", 1e-5, 0.01),
        F("pas_angulaire_max", "Pas angulaire maximal des arcs (°)", 0.8,
          "Rupture au point de tangence ≤ 0,5° (demi-pas), comme rg::carrefours.", 0.05, 5.0),
    ]


def parms_sol(table):
    return [
        F("fleche", "Flèche maximale des arcs (m)", 0.0005, "Faces circulaires : flèche ≤ 0,5 mm (RF-OSM-CAR-001).",
          1e-5, 0.01),
        F("pas_angulaire_max", "Pas angulaire maximal des arcs (°)", 0.8, "Comme rg::giratoires.", 0.05, 5.0),
        F("angle_depart", "Angle de départ des faces circulaires (°)", -90.0,
          "Ouverture des files fermées (couronne, îlot central) : point le plus au sud [G].", -360.0, 360.0),
        F("recouvrement_tete", "Recouvrement sous la tête (m)", 0.012,
          "Le dessus d'un îlot passe sous la tête de sa bordure sur 12 mm (TQ-BOR-007, même valeur que rg::sol).",
          0.0, 0.05),
        F("couronne_pente_pct", "Pente de la couronne franchissable (%)", 5.0,
          "RF-GV-GIR-006 : bande franchissable en pente de 4 à 6 % vers l'anneau ; milieu de la plage [G].", 0.0, 15.0),
        F("pas_radial", "Pas radial des dessus circulaires (m)", 0.25, "Maillage polaire [G].", 0.02, 2.0),
        F("dome_relief", "Relief au bord du dôme (m)", 0.02,
          "RF-GV-GIR-016 : relief dissuasif de 1 à 3 cm au bord de l'îlot franchissable du mini-giratoire ; milieu [G].",
          0.0, 0.05),
        F("aire_min_ilot", "Aire minimale d'un îlot séparateur (m²)", 0.5,
          "Un polygone d'îlot plus petit est signalé et non fabriqué (îlot dégénéré du modèle) [G].", 0.0, 10.0),
        F("abaisse_vue", "Vue des abaissés (m)", float(D31["vue"]), "DEF-031 (RF-MA-ABA-001).", 0.0, 0.1),
        F("abaisse_rampant", "Rampant des abaissés (m)", float(D31["rampant_5pct"]), "DEF-031 : 2,40 m à 5 %.", 0.0, 5.0),
        F("abaisse_rampant_min", "Rampant minimal (m)", float(D31["rampant_8pct"]),
          "DEF-031 : 1,50 m à 8 % ; un rampant plus court est signalé.", 0.0, 5.0),
        F("passage_marge", "Marge de l'axe d'un passage (m)", 2.0,
          "Une bordure reçoit l'abaissé d'un passage si elle coupe la bande du passage à moins de cette distance des "
          "bouts de l'axe du modèle [G] (même valeur que rg::carrefours_sol).", 0.0, 10.0),
        F("base_defaut", "Base d'une bordure absente des tables (m)", 0.15, "Secours ; la table de pj::bordure prime.",
          0.05, 0.5),
        S("table_bases", "Table des bases (profil:base)", table,
          "Bases des profils de bordure (table de pj::bordure, assets/specs/bordures.json, lue à la construction)."),
        S("bordure_ilot_defaut", "Bordure d'îlot par défaut", "I2", "Îlot sans ceinture : I2 (DEF-005 îlot)."),
        S("pieces_abaisse", "Pièces d'abaissé (profil:pièce, …)", "T2:T2_bateau",
          "Même table que rg::vers_entites (bordures_elements.json, abaisses.traversee)."),
        F("bev_recul", "BEV : recul au nez (m)", float(D31["BEV_recul_nez"]), "DEF-031, RF-MA-BEV-002.", 0.0, 2.0),
        F("bev_profondeur", "BEV : profondeur (m)", float(D31["BEV_profondeur"]), "DEF-031.", 0.1, 2.0),
        F("bev_profondeur_reduite", "BEV : profondeur réduite (m)", float(D31["BEV_reduite_si_trottoir_lt_1_90"]),
          "DEF-031 : trottoir de moins de 1,90 m ; refuge : demi-largeur du refuge par côté [G].", 0.1, 2.0),
        F("bev_seuil_trottoir", "BEV : largeur de trottoir du seuil (m)", 1.90, "DEF-031.", 0.0, 5.0),
        S("materiau_peinture", "Matériau de la peinture", "peinture_blanc_u1",
          "Peinture blanche, classe d'usure 1 (usure légère 0,2), comme rg::carrefours_sol."),
        F("usure_peinture", "Usure de la peinture", 0.2, "Usure légère (description : marquages.usure).", 0.0, 1.0),
        S("modulations", "Modulations (nom:trait:intervalle)", _table_modulations(),
          "RF-MQ-MOD-* (regles_route_fr.json, lu à la construction)."),
    ]


VEX_BEV_G = VL.VEX_BEV.replace(
    'if (kind == "coin") wmin = min(prim(1, "w_a", f), float(prim(1, "w_b", f)));',
    'if (kind == "coin") wmin = min(prim(1, "w_a", f), float(prim(1, "w_b", f)));\n'
    '    else if (float(prim(1, "w_bev", f)) > 0) wmin = prim(1, "w_bev", f);      // refuge : demi-largeur par côté [G]')
VEX_PROFILS_REDUITS_G = VS.VEX_PROFILS_REDUITS.replace(
    "if (i < 0 || find(faits, nom) >= 0) continue;",
    "if (i < 0 || find(faits, nom) >= 0 || rg_point_profil(0, nom) >= 0) continue;   // déjà fait par rg::carrefours")
assert VEX_BEV_G != VL.VEX_BEV and VEX_PROFILS_REDUITS_G != VS.VEX_PROFILS_REDUITS


def construire_solveur(dossier=ICI):
    sub = R.sous_reseau("rg_giratoires")
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parms_solveur()))
    e = sub.indirectInputs()[:3]
    module = (ICI / "lecteur_giratoires.py").read_text(encoding="utf-8")
    py = sub.createNode("python", "giratoires")
    py.parm("python").set("# Lecture des giratoires du modèle (module lecteur_giratoires.py embarqué dans l'HDA)\n"
                          "hou.pwd().parent().hdaModule().lire(hou.pwd())\n")
    an = _wr(sub, "anneaux", VG.VEX_ANNEAUX, "detail", py)
    br = _wr(sub, "branches", VG.VEX_BRANCHES_G, "detail", an, entrees=(e[0], e[1]))
    co = _wr(sub, "coins", VG.VEX_COINS_G, "detail", br, entrees=(e[0], e[1]))
    nz = _wr(sub, "embouchures", VS.VEX_NEZ, "detail", co, entrees=(e[0], e[1]))
    cr = _wr(sub, "couper_routes", VS.VEX_COUPER_ROUTES, "primitive", e[0], entrees=(nz,))
    sa = _wr(sub, "sans_anneaux", VG.VEX_SANS_ANNEAUX, "primitive", cr, entrees=(py,))
    pr = _wr(sub, "profils_reduits", VEX_PROFILS_REDUITS_G, "detail", e[1], entrees=(sa,))
    sp = _wr(sub, "solveur_plan", VG.VEX_SOLVEUR_PLAN, "primitive", e[2], entrees=(py,))
    b1 = sub.createNode("blast", "sans_points_giratoire")
    b1.setInput(0, nz)
    b1.parm("group").set("giratoire")
    b1.parm("grouptype").set("points")
    b2 = sub.createNode("blast", "sans_ilots_giratoire")
    b2.setInput(0, b1)
    b2.parm("group").set("ilot_g")
    b2.parm("grouptype").set("prims")
    fus = sub.createNode("merge", "solveur_fusionne")
    fus.setInput(0, sp)
    fus.setInput(1, b2)
    sorties = ((sa, "ROUTES"), (pr, "PROFILS"), (fus, "SOLVEUR"), (nz, "GIRATOIRES"))
    for k, (n, nom) in enumerate(sorties):
        nul = sub.createNode("null", nom)
        nul.setInput(0, n)
        R.sortie(sub, nul, k, f"sortie_{nom.lower()}")
        nul.setDisplayFlag(k == 3)
    R.ranger(sub)
    aide = ("Solveur des giratoires (lot L5, PLAN_GENERATEUR § 2.4 étape 4) branché après rg::carrefours : congés "
            "d'entrée et de sortie (raccordements Re / Rs du modèle, ACI tableau 1) tangents au bord réel des branches et "
            "au bord extérieur de la chaussée annulaire, coins (amorce, congé, anneau, congé, amorce) au contrat de "
            "rg::carrefours, trottoirs des branches coupés, routes d'anneau retirées (l'anneau est fabriqué dans le cœur "
            "par rg::carrefours_sol et les îlots posés par rg::giratoires_sol), SOLVEUR fusionné avec celui des carrefours "
            "plans.")
    det = ("== Entrées ==\n\n1. Routes, 2. Profils, 3. SOLVEUR (rg::carrefours, sorties 1, 2, 3).\n\n== Sorties ==\n\n"
           "1. Routes coupées (giratoires : s_end = frontière, profils réduits ~cG / ~cD au-delà de s_cut), routes "
           "d'anneau retirées.\n2. Profils (+ réduits).\n3. SOLVEUR fusionné (contrat rg::carrefours : branches, coins, "
           "embouchures, frontières, passages ; îlots des giratoires retirés).\n4. GIRATOIRES : points giratoire (anneau, "
           "rayons des limites r_lim, R0), branches (T_g / T_d, C_g / C_d, K_g / K_d des congés), passages, îlots "
           "(ilot_g), coins.\n\nRègles : RF-GV-GIR-003, RF-GV-GIR-004, RF-OSM-CAR-001, DEF-031 ; choix [G] : amorce, "
           "garde avant le rampant.")
    return R.creer_hda(sub, "giratoires", "RG Giratoires (solveur)", parms_solveur(), dossier, entrees=(3, 3),
                       sorties=4, aide=aide, details_aide=det, module_python=module, icone="SOP_circle",
                       etiquettes_entrees=("Routes (rg::carrefours, sortie 1)", "Profils (rg::carrefours, sortie 2)",
                                           "Solveur (rg::carrefours, sortie 3)"),
                       etiquettes_sorties=("Routes coupées", "Profils (+ réduits)", "Solveur fusionné", "Giratoires"))


def construire_sol(dossier=ICI):
    table, src = _table_bases()
    parms = parms_sol(table)
    sub = R.sous_reseau("rg_giratoires_sol")
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parms))
    e = list(sub.indirectInputs()[:2])
    vide = sub.createNode("add", "vide")
    fa = _wr(sub, "faces", VGS.FONCTIONS_FACES + VGS.VEX_FACES, "detail", vide, entrees=(e[0], e[1]))
    vide2 = sub.createNode("add", "vide_dessus")
    dp = _wr(sub, "dessus_polaires", VGS.VEX_DESSUS_POLAIRES, "detail", vide2, entrees=(fa, e[1]))
    vide3 = sub.createNode("add", "vide_contours")
    cs = _wr(sub, "contours_separateurs", VGS.VEX_CONTOURS_SEP, "detail", vide3, entrees=(fa,))
    tri = sub.createNode("triangulate2d::3.0", "trianguler")
    tri.setInput(0, cs)
    for p, v in (("planepossrc", 1), ("dirx", 0.0), ("diry", 1.0), ("dirz", 0.0), ("useconstrpolys", 1),
                 ("constrpolys", "contour_dessus"), ("removefromconstrpolys", 1), ("refine", 1), ("trianglesize", 2),
                 ("targetedgelength", 0.35), ("minangle", 25.0), ("minedgelength", 0.02), ("allowconstrsplit", 1),
                 ("useexactconstruction", 1), ("maxnewpts", 500000), ("updatenmls", 0), ("keepprims", 0),
                 ("removeunusedpoints", 1), ("removeduplicatepoints", 1)):
        tri.parm(p).set(v)
    nett = sub.createNode("attribdelete", "attributs_triangulation")
    nett.setInput(0, tri)
    nett.parm("ptdel").set("* ^P")
    nett.parm("primdel").set("*")
    nett.parm("dtldel").set("*")
    grp = sub.createNode("groupdelete", "groupes_triangulation")
    grp.setInput(0, nett)
    grp.parm("group1").set("*")
    ds = _wr(sub, "dessus_separateurs", VGS.VEX_DESSUS_SEP, "detail", grp, entrees=(fa, e[1]))
    mg = sub.createNode("merge", "dessus")
    mg.setInput(0, dp)
    mg.setInput(1, ds)
    ori = _wr(sub, "orienter", VGS.VEX_ORIENTER, "primitive", mg)
    rev = sub.createNode("reverse", "inverser")
    rev.setInput(0, ori)
    rev.parm("group").set("a_inverser")
    fin = _wr(sub, "finir", VGS.VEX_FINIR, "primitive", rev)
    stp = _wr(sub, "points_st", "f@s = 10000.0 + @P.x; f@t = -@P.z; i@pt_orig = @ptnum;", "point", fin)
    nm = sub.createNode("normal", "normales")
    nm.setInput(0, stp)
    nm.parm("type").set(1)
    nm.parm("cuspangle").set(30.0)
    uv = _wr(sub, "uv", "v@uv = set(@P.x, -@P.z, 0);", "sommet", nm)
    sol_c = sub.createNode("attribdelete", "contrat_sol")
    sol_c.setInput(0, uv)
    sol_c.parm("ptdel").set("* ^P ^s ^t ^pt_orig")
    sol_c.parm("vtxdel").set("* ^N ^uv")
    sol_c.parm("primdel").set("* ^materiau_id ^visible ^priorite ^z_type ^classe ^chaine ^pj_couche ^pj_entite ^section "
                              "^route ^bande ^bande_id ^pj_maillage ^haut ^zone ^ref")
    sol_c.parm("dtldel").set("*")
    sol_g = sub.createNode("groupdelete", "groupes_sol")
    sol_g.setInput(0, sol_c)
    sol_g.parm("group1").set("*")
    sol_n = sub.createNode("null", "SOL_ILOTS")
    sol_n.setInput(0, sol_g)
    vide4 = sub.createNode("add", "vide_bev")
    bev = _wr(sub, "bev", VEX_BEV_G, "detail", vide4, entrees=(fa, sol_n))
    bevc = sub.createNode("attribdelete", "contrat_bev")
    bevc.setInput(0, bev)
    bevc.parm("dtldel").set("*")
    ent = _wr(sub, "entites", VL.VEX_ENTITES, "primitive", fa)
    entc = sub.createNode("attribdelete", "contrat_pj")
    entc.setInput(0, ent)
    entc.parm("ptdel").set("* ^P")
    entc.parm("vtxdel").set("*")
    entc.parm("primdel").set("* ^id ^famille ^ligne_ref ^intervalles ^niv_s ^niv_z_pied ^niv_z_tete ^aspect ^caniveau "
                             "^props ^materiau_id ^route")
    entc.parm("dtldel").set("*")
    entg = sub.createNode("groupdelete", "groupes_entites")
    entg.setInput(0, entc)
    entg.parm("group1").set("*")
    entn = sub.createNode("add", "points_inutiles")
    entn.setInput(0, entg)
    entn.parm("remove").set(1)
    vide5 = sub.createNode("add", "vide_marques")
    mq = _wr(sub, "marques", VGS.VEX_MARQUES, "detail", vide5, entrees=(e[0], fa))
    mqc = sub.createNode("attribdelete", "contrat_marques")
    mqc.setInput(0, mq)
    mqc.parm("dtldel").set("*")
    sorties = ((sol_n, "SOL"), (bevc, "BEV"), (entn, "ENTITES"), (mqc, "MARQUES"), (fa, "CONTROLES"))
    for k, (n, nom) in enumerate(sorties):
        nul = sub.createNode("null", nom + "_SORTIE")
        nul.setInput(0, n)
        R.sortie(sub, nul, k, f"sortie_{nom.lower()}")
        nul.setDisplayFlag(k == 0)
    R.ranger(sub)
    aide = ("Îlots posés des giratoires (lot L5) : couronne franchissable (bordure et vue du profil de l'anneau, pente "
            "RF-GV-GIR-006 vers l'anneau), îlot central (cercle de l'anneau du modèle, ceinture du modèle, pied sur la "
            "couronne), dôme franchissable du mini-giratoire (RF-GV-GIR-016), îlots séparateurs (polygones du modèle) avec "
            "abaissés et BEV au droit des passages (refuge, DEF-031) ; dessus et jupes au contrat de rg::sol ; bordures au "
            "contrat de pj::bordure ; contour du dôme et lignes de l'anneau au contrat de pj::marquage_solide. Le pilote "
            "fusionne sol, BEV, entités et marques avec ceux des branches et du cœur.")
    det = ("== Entrées ==\n\n1. GIRATOIRES (rg::giratoires, sortie 4). 2. Sol sans îlots (rg::sol + rg::carrefours_sol, "
           "sortie 1).\n\n== Sorties ==\n\n1. SOL des îlots (contrat de rg::sol ; classes giratoire_ilot, murs z_type 14).\n"
           "2. BEV (groupe dalles).\n3. ENTITÉS des bordures des îlots (contrat pj::bordure).\n4. MARQUES (contrat "
           "pj::marquage_solide).\n5. CONTRÔLES (faces de bordure, pied, abaissés).\n\nRègles : RF-GV-GIR-006, "
           "RF-GV-GIR-016, RF-MQ-GIR-02, RF-MQ-GIR-04, RF-OSM-MRQ-021, TQ-SOL-013, TQ-BOR-007, DEF-031, RF-MA-BEV-002, "
           f"RF-MQ-MOD-*. Table des bases : {src}.")
    return R.creer_hda(sub, "giratoires_sol", "RG Giratoires (îlots posés, marques de l'anneau)", parms, dossier,
                       entrees=(2, 2), sorties=5, aide=aide, details_aide=det, icone="SOP_tube",
                       etiquettes_entrees=("Giratoires (rg::giratoires, sortie 4)", "Sol sans îlots"),
                       etiquettes_sorties=("Sol des îlots", "BEV des îlots", "Entités (bordures des îlots)",
                                           "Marques des giratoires", "Contrôles"))


def construire(dossier=ICI):
    return construire_solveur(dossier), construire_sol(dossier)


if __name__ == "__main__":
    print(construire())
