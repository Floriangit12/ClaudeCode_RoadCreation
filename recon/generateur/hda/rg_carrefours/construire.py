"""Construit les HDA du lot L3 (carrefours plans) : rg::carrefours::1.0 (solveur et coupes) et rg::carrefours_sol::1.0
(fabrication de l'intérieur des carrefours) ; hython Houdini 22.

    hython recon/generateur/hda/rg_carrefours/construire.py

rg::carrefours (« RG Carrefours (solveur, coupes) », PLAN_GENERATEUR § 2.4, étapes 1 à 4) :
    entrées 1 routes, 2 profils de rg::lire_modele (sorties 1 et 5)
      -> carrefours (Python SOP, module lecteur_carrefours.py : carrefours, îlots, passages, lignes, balayages L3a)
      -> branches (VEX : repère, bords de chaussée, îlots, retrait des nez au premier contact des balayages + marge,
         plafonné par les refuges)
      -> coins (VEX : congés tangents aux bords réels, rayon du modèle ou DEF-010, amorces, coupes des trottoirs,
         frontière fermée)
      -> nez (VEX : nez arrondis des îlots du profil, embouchures)
      -> couper_routes (VEX : routes raccourcies à s_end, sections et profils réduits « ~cG / ~cD / ~cGD »)
      -> profils_reduits (VEX : points de profil réduits)
    sorties 1 routes coupées, 2 profils (+ réduits), 3 SOLVEUR (branches, coins, nez, embouchures, frontière, îlots,
    passages, lignes, balayages).
rg::carrefours_sol (« RG Carrefours (sol, bordures, marques) », étapes 5 et 6 et sol étanche) :
    entrées 1 NIVEAUX (rg::nivellement), 2 profils (rg::carrefours, sortie 2), 3 SOLVEUR (rg::carrefours, sortie 3),
    4 références (rg::graphe)
      -> domaine (VEX : faces de bordure, abaissés, lignes de contrainte, régions, contour) -> Triangulate 2D contraint
      -> classer -> scinder (marches, murs) -> altitude (Z imposés du modèle unique, trottoirs, nez) -> initialiser
      -> lissage harmonique des points bas libres -> pied des faces -> dessus des îlots -> orienter -> finir
    sorties 1 SOL du carrefour, 2 BEV du carrefour, 3 ENTITÉS des bordures du carrefour (contrat pj::bordure),
    4 MARQUES du carrefour (contrat pj::marquage_solide), 5 CONTRÔLES (faces de bordure).
Le pilote (fabriquer_carrefours.py) fusionne sol et BEV avec ceux de rg::sol, entités avec rg::vers_entites, marques
avec rg::marquages (README_RG.md § 9).
"""
import importlib.util
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
import vex_solveur as VS  # noqa: E402
import vex_sol as VL  # noqa: E402

VEX_C = (ICI / "vex" / "rg_carrefour.h").read_text(encoding="utf-8") + "\n"


def _wr(sub, nom, code, classe, entree, entrees=()):
    return R.wrangle(sub, nom, VEX_C + code, classe, entree, entrees=entrees,
                     bibliotheques=("rg_geometrie.h", "rg_niveau.h"))


def _table_bases():
    spec = importlib.util.spec_from_file_location("construire_rg_nivellement_tab", GEN / "hda" / "rg_nivellement" / "construire.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    lignes, src = m.table_profils()
    return ",".join(f"{n}:{b:.4f}" for n, fam, b, H, hfe, dhc in lignes if fam != "caniveau"), src


D31 = regles.defaut("DEF-031")["valeur"]
D10 = regles.defaut("DEF-010")["valeur"]
D11 = regles.defaut("DEF-011")["valeur"]


def F(nom, lab, v, aide, mn=0.0, mx=10.0):
    return hou.FloatParmTemplate(nom, lab, 1, default_value=(v,), min=mn, max=mx, help=aide)


def S(nom, lab, v, aide):
    return hou.StringParmTemplate(nom, lab, 1, default_value=(v,), help=aide)


def parms_solveur():
    T = hou
    return [
        T.StringParmTemplate("fichier", "Modèle (modele_voie.json)", 1, default_value=("",),
                             string_type=T.stringParmType.FileReference,
                             help="Même fichier que rg::lire_modele (le pilote y renvoie son paramètre) : carrefours, "
                                  "îlots, passages et lignes transversales sont lus ici (rg::lire_modele ne les lit pas)."),
        T.StringParmTemplate("balayages", "Balayages des véhicules (JSON, lot L3a)", 1, default_value=("",),
                             string_type=T.stringParmType.FileReference,
                             help="Enveloppes balayées des trajectoires du modèle, calculées par le pilote avec "
                                  "vehicules/balayage.py (lot L3a) : {balayages: [{trajectoire, vehicule, carrefour, "
                                  "faisable, exterieur: [[x, y], …] locaux]}}. Vide : nez à la frontière."),
        F("amorce", "Amorce droite des bordures de coin (m)", 3.0,
          "Longueur droite de la bordure de coin de part et d'autre du congé, prise sur la branche (le trottoir de la "
          "branche est coupé d'autant) : place des rampants d'abaissé (DEF-031 : 2,40 m à 5 %) d'un passage proche du "
          "coin dans la même file. Choix de fabrication [G] (aucune règle).", 0.0, 10.0),
        F("rayon_defaut", "Rayon de coin par défaut (m)", float(D10["bus_PL_occasionnels"]),
          "Rayon d'un coin dont le modèle ne dit rien (coin_droit absent) et dont les bords ne sont pas alignés : "
          "DEF-010 bus / PL occasionnels (signalé dans le solveur).", 1.0, 50.0),
        F("fleche", "Flèche maximale des arcs (m)", 0.0005,
          "Échantillonnage des congés : flèche ≤ 0,5 mm (critère L1 du plan, RF-OSM-CAR-001).", 1e-5, 0.01),
        F("pas_angulaire_max", "Pas angulaire maximal des arcs (°)", 0.8,
          "Angle entre deux cordes consécutives d'un congé ≤ 0,8° : la rupture de la polyligne au point de tangence (demi-pas) "
          "reste sous 0,5° (critère « coins tangents, rupture ≤ 0,5° », PLAN_GENERATEUR § 3 L3).", 0.05, 5.0),
        F("nez_rayon", "Rayon des nez d'îlot par défaut (m)", 0.5,
          "Nez d'un îlot du profil sans rayon dans le modèle : RF-GV-ILO-015 (nez 0,50 à 1,50 m).", 0.1, 2.0),
        F("marge_balayage", "Marge au premier contact des balayages (m)", 0.30,
          "Nez des îlots au premier contact des balayages des véhicules (lot L3a) + 0,30 m (PLAN_GENERATEUR § 3, L3).",
          0.0, 2.0),
        F("pas_retrait_nez", "Pas du retrait des nez (m)", 0.05, "Retrait arrondi au pas supérieur [G].", 0.001, 1.0),
        F("rampant_refuge", "Longueur gardée après un passage (m)", float(D31["rampant_5pct"]),
          "Le nez d'un îlot traversé par un passage n'est pas reculé au-delà de la bande du passage + le rampant de "
          "l'abaissé (DEF-031 : 2,40 m) : le refuge est gardé (DEF-022) ; le balayage non dégagé est signalé.", 0.0, 10.0),
    ]


def parms_sol(table):
    return [
        F("amorce", "Amorce droite des bordures de coin (m)", 3.0, "Même valeur que rg::carrefours (le pilote la relie).",
          0.0, 10.0),
        F("recouvrement_tete", "Recouvrement du trottoir sous la tête (m)", 0.012,
          "La chaussée passe sous la bordure jusqu'à l'arrière moins 12 mm, le trottoir sous la tête sur 12 mm "
          "(TQ-BOR-007 ; même valeur que rg::sol, RG_RECOUV_HAUT).", 0.0, 0.05),
        F("abaisse_vue", "Vue des abaissés (m)", float(D31["vue"]), "DEF-031 (RF-MA-ABA-001).", 0.0, 0.1),
        F("abaisse_rampant", "Rampant des abaissés (m)", float(D31["rampant_5pct"]), "DEF-031 : 2,40 m à 5 %.", 0.0, 5.0),
        F("abaisse_rampant_min", "Rampant minimal (m)", float(D31["rampant_8pct"]),
          "DEF-031 : 1,50 m à 8 % ; un rampant plus court (bout de file) est signalé.", 0.0, 5.0),
        F("passage_marge", "Marge de l'axe d'un passage (m)", 2.0,
          "Une bordure reçoit l'abaissé d'un passage si elle coupe la bande du passage (axe ± longueur des bandes / 2) "
          "à moins de cette distance des bouts de l'axe du modèle [G].", 0.0, 10.0),
        F("base_defaut", "Base d'une bordure absente des tables (m)", 0.15, "Secours ; la table de pj::bordure prime.",
          0.05, 0.5),
        S("table_bases", "Table des bases (profil:base)", table,
          "Bases des profils de bordure (table de pj::bordure, assets/specs/bordures.json, lue à la construction)."),
        S("bordure_ilot_defaut", "Bordure d'îlot par défaut", "I2", "Îlot du cœur sans ceinture : I2 (DEF-005 îlot)."),
        S("materiau_bordure_defaut", "Matériau des bordures par défaut", "beton_bordure_gris",
          "Même défaut que rg::vers_entites."),
        F("arete_cible", "Arête cible de la triangulation (m)", 0.5, "Triangulate 2D raffiné [G].", 0.05, 5.0),
        F("angle_min", "Angle minimal (°)", 25.0, "TQ-SOL-002 (rg::sol).", 5.0, 33.0),
        hou.IntParmTemplate("iterations_lissage", "Itérations du lissage harmonique", 1, default_value=(400,), min=0,
                            max=10000, help="Gauss-Seidel sur-relaxé des Z de chaussée libres (choix de fabrication [G])."),
        F("relaxation", "Sur-relaxation", 1.8, "Facteur ω du Gauss-Seidel (1 < ω < 2).", 1.0, 1.99),
        S("materiau_chaussee", "Matériau de la chaussée du carrefour", "enrobe_bbsg_ancien",
          "Revêtement des voies des branches (bande voie_circulation des J1-J5)."),
        F("bev_recul", "BEV : recul au nez (m)", float(D31["BEV_recul_nez"]), "DEF-031, RF-MA-BEV-002.", 0.0, 2.0),
        F("bev_profondeur", "BEV : profondeur (m)", float(D31["BEV_profondeur"]), "DEF-031.", 0.1, 2.0),
        F("bev_profondeur_reduite", "BEV : profondeur réduite (m)", float(D31["BEV_reduite_si_trottoir_lt_1_90"]),
          "DEF-031 : trottoir de moins de 1,90 m.", 0.1, 2.0),
        F("bev_seuil_trottoir", "BEV : largeur de trottoir du seuil (m)", 1.90, "DEF-031.", 0.0, 5.0),
        S("pieces_abaisse", "Pièces d'abaissé (profil:pièce, …)", "T2:T2_bateau",
          "Même table que rg::vers_entites (bordures_elements.json, abaisses.traversee)."),
        S("materiau_peinture", "Matériau de la peinture", "peinture_blanc_u1",
          "Peinture blanche, classe d'usure 1 (usure légère 0,2 : rg_m_materiau de rg::marquages)."),
        F("usure_peinture", "Usure de la peinture", 0.2, "Usure légère des scènes J (description : marquages.usure).",
          0.0, 1.0),
        F("stop_largeur", "Ligne STOP : largeur (m)", float(regles.valeur("RF-MQ-STOP-01", "largeur")),
          "RF-MQ-STOP-01 : continue de 0,50 m.", 0.1, 1.0),
        F("cedez_largeur", "Ligne CÉDEZ : largeur (m)", float(regles.valeur("RF-MQ-CED-01", "largeur")),
          "RF-MQ-CED-01 : T'2 de 0,50 m.", 0.1, 1.0),
        F("effet_largeur", "Ligne d'effet des feux : largeur (m)", float(regles.valeur("RF-MQ-FEU-01", "largeur")),
          "RF-MQ-FEU-01 : T'2 de 0,15 m.", 0.05, 1.0),
        F("tp2_trait", "T'2 : trait (m)", float(regles.valeur("RF-MQ-MOD-T'2", "trait")), "RF-MQ-MOD-T'2.", 0.1, 2.0),
        F("tp2_intervalle", "T'2 : intervalle (m)", float(regles.valeur("RF-MQ-MOD-T'2", "intervalle")),
          "RF-MQ-MOD-T'2.", 0.1, 2.0),
        F("passage_bande", "Passage : largeur des bandes (m)", float(D11["bande"]), "DEF-011.", 0.1, 1.0),
    ]


def construire_solveur(dossier=ICI):
    sub = R.sous_reseau("rg_carrefours")
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parms_solveur()))
    e = sub.indirectInputs()[:2]
    module = (ICI / "lecteur_carrefours.py").read_text(encoding="utf-8")
    py = sub.createNode("python", "carrefours")
    py.parm("python").set("# Lecture des carrefours du modèle (module lecteur_carrefours.py embarqué dans l'HDA)\n"
                          "hou.pwd().parent().hdaModule().lire(hou.pwd())\n")
    br = _wr(sub, "branches", VS.VEX_BRANCHES, "detail", py, entrees=(e[0], e[1]))
    co = _wr(sub, "coins", VS.VEX_COINS, "detail", br, entrees=(e[0], e[1]))
    nz = _wr(sub, "nez", VS.VEX_NEZ, "detail", co, entrees=(e[0], e[1]))
    cr = _wr(sub, "couper_routes", VS.VEX_COUPER_ROUTES, "primitive", e[0], entrees=(nz,))
    pr = _wr(sub, "profils_reduits", VS.VEX_PROFILS_REDUITS, "detail", e[1], entrees=(cr,))
    sorties = ((cr, "ROUTES"), (pr, "PROFILS"), (nz, "SOLVEUR"))
    for k, (n, nom) in enumerate(sorties):
        nul = sub.createNode("null", nom)
        nul.setInput(0, n)
        R.sortie(sub, nul, k, f"sortie_{nom.lower()}")
        nul.setDisplayFlag(k == 2)
    R.ranger(sub)
    aide = ("Solveur des carrefours plans (lot L3, PLAN_GENERATEUR § 2.4 étapes 1 à 4) branché à la place de "
            "rg::lire_modele : coins tangents de rayon DEF-010 (ou du modèle), coupes des routes à la fin de leur "
            "chaussée (nez des îlots compris), trottoirs coupés à l'amorce des coins, frontière fermée, nez des îlots du "
            "profil arrondis et reculés au premier contact des balayages des véhicules (lot L3a) + 0,30 m.")
    det = ("== Entrées ==\n\n1. Routes, 2. Profils (rg::lire_modele, sorties 1 et 5).\n\n== Sorties ==\n\n"
           "1. Routes coupées (s_end ; sections et profils réduits ~cG / ~cD / ~cGD au-delà de s_cut).\n"
           "2. Profils (+ profils réduits : bandes extérieures retirées, bord de chaussée sans "
           "bordure ni marquage).\n3. SOLVEUR : points branche (repère, bords, s_end, s_cut_g / s_cut_d, s_tan_g / "
           "s_tan_d, retrait du nez) ; polylignes coin (face de bordure, côté haut à gauche, u, partie), nez, "
           "embouchure ; polygone frontiere ; îlots, passages, lignes, balayages lus.\n\n"
           "Règles : DEF-010, RF-GV-RAY-001, RF-GV-ILO-015, RF-OSM-CAR-001 ; choix [G] : amorce, pas du retrait. "
           "Branches tracées vers le centre (extrémité « fin ») ; routes droites près du carrefour.")
    return R.creer_hda(sub, "carrefours", "RG Carrefours (solveur, coupes)", parms_solveur(), dossier, entrees=(2, 2),
                       sorties=3, aide=aide, details_aide=det, module_python=module, icone="SOP_intersectionanalysis",
                       etiquettes_entrees=("Routes (rg::lire_modele, sortie 1)", "Profils (rg::lire_modele, sortie 5)"),
                       etiquettes_sorties=("Routes coupées", "Profils (+ réduits)", "Solveur"))


def construire_sol(dossier=ICI):
    table, src = _table_bases()
    parms = parms_sol(table)
    sub = R.sous_reseau("rg_carrefours_sol")
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parms))
    e = list(sub.indirectInputs()[:4])
    # NIVEAUX + références échantillonnées (rg::graphe) : sections d'abord (rg_point_section prend le premier point)
    nr = sub.createNode("merge", "niveaux_et_references")
    nr.setInput(0, e[0])
    nr.setInput(1, e[3])
    e[0] = nr
    dom = _wr(sub, "domaine", VL.VEX_DOMAINE, "detail", e[2], entrees=(e[0], e[1]))
    tin = sub.createNode("blast", "contour_et_lignes")
    tin.setInput(0, dom)
    tin.parm("group").set("contour lignes")
    tin.parm("grouptype").set("prims")
    tin.parm("negate").set(1)
    fu = sub.createNode("fuse::2.0", "souder")
    fu.setInput(0, tin)
    fu.parm("tol3d").set(1e-6)
    tri = sub.createNode("triangulate2d::3.0", "trianguler")
    tri.setInput(0, fu)
    for p, v in (("planepossrc", 1), ("dirx", 0.0), ("diry", 1.0), ("dirz", 0.0), ("useconstredges", 1),
                 ("constredges", "lignes"), ("useconstrpolys", 1), ("constrpolys", "contour"),
                 ("removefromconstrpolys", 1), ("refine", 1), ("trianglesize", 2), ("minedgelength", 0.02),
                 ("allowconstrsplit", 1), ("useexactconstruction", 1), ("maxnewpts", 1500000), ("updatenmls", 0),
                 ("keepprims", 0), ("removeunusedpoints", 1), ("removeduplicatepoints", 1)):
        tri.parm(p).set(v)
    tri.parm("targetedgelength").setExpression('ch("../arete_cible")')
    tri.parm("minangle").setExpression('ch("../angle_min")')
    nett = sub.createNode("attribdelete", "attributs_triangulation")
    nett.setInput(0, tri)
    nett.parm("ptdel").set("* ^P")
    nett.parm("primdel").set("*")
    nett.parm("dtldel").set("*")
    grp = sub.createNode("groupdelete", "groupes_triangulation")
    grp.setInput(0, nett)
    grp.parm("group1").set("*")
    cla = _wr(sub, "classer", VL.VEX_CLASSER, "primitive", grp, entrees=(dom,))
    sci = _wr(sub, "scinder", VL.VEX_SCINDER, "detail", cla)
    zpt = _wr(sub, "zones_points", VL.VEX_ZONE_POINTS, "detail", sci)
    alt = _wr(sub, "altitude", VL.VEX_ALTITUDE, "point", zpt, entrees=(dom, e[0], e[1]))
    idw = _wr(sub, "initialiser", VL.VEX_IDW, "point", alt, entrees=(alt,))
    lis = _wr(sub, "lissage", VL.VEX_LISSER, "detail", idw)
    faces = sub.createNode("blast", "faces")
    faces.setInput(0, dom)
    faces.parm("group").set("face")
    faces.parm("grouptype").set("prims")
    faces.parm("negate").set(1)
    pf = _wr(sub, "pied_faces", VL.VEX_PIED_FACES, "primitive", faces, entrees=(lis,))
    ail = _wr(sub, "altitude_ilots", VL.VEX_ALTITUDE_ILOTS, "point", lis, entrees=(pf,))
    ori = _wr(sub, "orienter", r"""
// faces vers +Y (Triangulate 2D les rend vers −Y dans le plan XZ) ; murs vers le côté bas (mur_dir)
vector n = prim_normal(0, @primnum, {0.333, 0.333, 0});
if (s@zone == "mur") { if (dot(n, v@mur_dir) < 0) i@group_a_inverser = 1; }
else if (n.y < 0) i@group_a_inverser = 1;
""", "primitive", ail)
    rev = sub.createNode("reverse", "inverser")
    rev.setInput(0, ori)
    rev.parm("group").set("a_inverser")
    fin = _wr(sub, "finir", VL.VEX_FINIR, "primitive", rev, entrees=(pf,))
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
    sol_n = sub.createNode("null", "SOL_CARREFOUR")
    sol_n.setInput(0, sol_g)
    vide = sub.createNode("blast", "vide")
    vide.setInput(0, e[2])
    vide.parm("group").set("*")
    bev = _wr(sub, "bev", VL.VEX_BEV, "detail", vide, entrees=(pf, sol_n))
    bevc = sub.createNode("attribdelete", "contrat_bev")
    bevc.setInput(0, bev)
    bevc.parm("dtldel").set("*")
    ent = _wr(sub, "entites", VL.VEX_ENTITES, "primitive", pf)
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
    mq = _wr(sub, "marques", VL.VEX_MARQUES, "detail", vide, entrees=(e[2],))
    mqc = sub.createNode("attribdelete", "contrat_marques")
    mqc.setInput(0, mq)
    mqc.parm("dtldel").set("*")
    sorties = ((sol_n, "SOL"), (bevc, "BEV"), (entn, "ENTITES"), (mqc, "MARQUES"), (pf, "CONTROLES"))
    for k, (n, nom) in enumerate(sorties):
        nul = sub.createNode("null", nom + "_SORTIE")
        nul.setInput(0, n)
        R.sortie(sub, nul, k, f"sortie_{nom.lower()}")
        nul.setDisplayFlag(k == 0)
    R.ranger(sub)
    aide = ("Fabrication de l'intérieur des carrefours plans (lot L3) : sol étanche du cœur, des coins et des nez "
            "(triangulation contrainte, Z imposés du modèle unique aux embouchures, aux bords des branches et aux coins, "
            "interpolation harmonique ailleurs, marches fermées par des murs sous les bordures), bordures des coins, des "
            "nez et des îlots du cœur avec les abaissés des passages (DEF-031) et leurs BEV, lignes transversales "
            "(CÉDEZ, STOP, effet des feux) et passages sans route. Le pilote fusionne sol et BEV avec ceux de rg::sol "
            "(README_RG.md § 9).")
    det = ("== Entrées ==\n\n1. NIVEAUX (rg::nivellement). 2. Profils (rg::carrefours, sortie 2). 3. SOLVEUR "
           "(rg::carrefours, sortie 3). 4. Références (rg::graphe).\n\n== Sorties ==\n\n"
           "1. SOL du carrefour (contrat de rg::sol ; classe carrefour_*, z_type 10, murs z_type 14).\n2. BEV.\n"
           "3. ENTITÉS des bordures du carrefour (contrat pj::bordure).\n4. MARQUES du carrefour (contrat "
           "pj::marquage_solide).\n5. CONTRÔLES (faces de bordure, pied, abaissés).\n\n"
           "Règles : TQ-SOL-013, TQ-BOR-007, DEF-031, RF-MA-BEV-002, RF-MQ-CED-01, RF-MQ-STOP-01, RF-MQ-FEU-01, "
           f"RF-MQ-MOD-T'2, DEF-011. Table des bases : {src}.")
    return R.creer_hda(sub, "carrefours_sol", "RG Carrefours (sol, bordures, marques)", parms, dossier, entrees=(4, 4),
                       sorties=5, aide=aide, details_aide=det, icone="SOP_triangulate2d",
                       etiquettes_entrees=("Niveaux (rg::nivellement)", "Profils (rg::carrefours, sortie 2)",
                                           "Solveur (rg::carrefours, sortie 3)", "Références (rg::graphe)"),
                       etiquettes_sorties=("Sol du carrefour", "BEV du carrefour", "Entités (bordures du carrefour)",
                                           "Marques du carrefour", "Contrôles"))


def construire(dossier=ICI):
    return construire_solveur(dossier), construire_sol(dossier)


if __name__ == "__main__":
    print(construire())
