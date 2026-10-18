"""Construit l'HDA rg::autoroute::1.0 (lot « autoroutes » : équipements et bifurcations des autoroutes) ; hython
Houdini 22.

    hython recon/generateur/hda/rg_autoroute/construire.py

rg::autoroute (« RG Autoroute (retenues, musoirs, raccord des bretelles) ») :
    entrées 1 limites (rg::profils, sortie 1), 2 sol des routes (rg::sol, sortie 1), 3 zones et îlots + nœuds
            (rg::lire_modele, sorties 3 et 2 fusionnées), 4 références (rg::graphe, sortie 1)
      -> contexte (références groupe ref, zones groupe zone, nœuds groupe noeud)
      -> raccord (VEX : décalage vertical dz de chaque bretelle au point de jonction) -> appliquer (VEX, points)
      -> musoirs (VEX : sol du musoir et du terre-plein latéral, aplat de pointe et chevrons)
      -> separateurs (VEX : GBA / DBA béton balayées, glissières GS2 / GS4 / DE2 en pièces du catalogue)
    sorties 1 SOL (routes raccordées + musoirs ; contrat de rg::sol), 2 ÉQUIPEMENTS (maillages des dispositifs de
            retenue ; materiau_id, pj_couche, pj_entite), 3 MARQUES (aplats et chevrons des musoirs ; contrat de
            pj::marquage_solide), 4 CONTRÔLES (détail : bifurcations, séparateurs).

Houdini n'invente rien : les contours béton (retenue_DBA, retenue_GBA, retenue_LBA, retenue_MVL) et les pièces des
glissières (retenue_glissiere_GS2/GS4/DE2_module_L400) sont recopiés de assets/specs/route/catalogue_assets_route.json
(sources : Cerema, Dispositifs de retenue, tableaux 15 et 16 p. 32 (NF P98-426) ; fiches Aximum GS2, GS4+, DE2 ; Setra
BVL 2001 p. 30) ; positions : limites « separateur » du modèle ; musoirs : îlots du modèle (C-<id> : îlot peint et
terre-plein latéral) et bords des plates-formes ; marques : DEF-020, RF-MQ-HACH-01 à -03, RF-MQ-MUS-01 (dossier 08).
Choix [G] déclarés dans l'aide des paramètres : glissière par défaut, seuil GBA / DBA, encastrement des contours béton,
profil en long de la bretelle parallèle à celui de la principale à partir de la jonction.
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
import vex_autoroute as VA  # noqa: E402

NOM = "autoroute"
CATALOGUE = DEPOT / "assets" / "specs" / "route" / "catalogue_assets_route.json"
CONTOURS = {"dba": "retenue_DBA_L100", "gba": "retenue_GBA_L100", "lba": "retenue_LBA_L100", "mvl": "retenue_MVL_L100"}
GLISSIERES = {"gs2": "retenue_glissiere_GS2_module_L400", "gs4": "retenue_glissiere_GS4_module_L400",
              "de2": "retenue_glissiere_DE2_module_L400"}


def catalogue():
    d = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    return {a["id"]: a for a in d["assets"]}


def _src(a):
    return " ; ".join(f"{s.get('doc')} p. {s.get('page')} ({s.get('note', '')})" for s in a.get("sources", []))


def parametres():
    T = hou
    F, S = T.FloatParmTemplate, T.StringParmTemplate
    cat = catalogue()
    d20 = regles.valeur("DEF-020")
    pp = []
    for k, aid in CONTOURS.items():
        a = cat[aid]
        pp.append(S(f"contour_{k}", f"Contour {k.upper()} (catalogue)", 1, default_value=(a["params"]["contour_a"],),
                    help=f"{aid} : {a.get('type')} ; contour (largeur, hauteur) en m, base au sol. {a.get('note', '')}. "
                         f"Sources : {_src(a)}."))
    for k, aid in GLISSIERES.items():
        a = cat[aid]
        pp.append(S(f"pieces_{k}", f"Pièces {k.upper()} (catalogue)", 1, default_value=(a["params"]["pieces"],),
                    help=f"{aid} : {a.get('type')} ; module de {a['params'].get('longueur', 4.0) if False else 4.0} m "
                         f"(x le long, y vers l'arrière, z haut ; syntaxe route::assemblage Q / B / T). {a.get('note', '')}. "
                         f"Sources : {_src(a)}."))
    mod = cat[GLISSIERES["gs2"]].get("pose", {}).get("pas_m", 4.0)
    pp += [
        S("glissiere_defaut", "Glissière par défaut", 1, default_value=("GS2",),
          help="[G] choix déclaré : modèle posé quand le modèle dit « glissière » sans modèle (GS2 : supports tous les "
               "2 m, niveau N2, Setra BVL 2001 p. 30 ; GS4 : tous les 4 m)."),
        F("module_glissiere", "Module de glissière (m)", 1, default_value=(float(mod),), min=1.0, max=8.0,
          help="Pas des modules du catalogue (pose.pas_m : lisse de 4,315 m, recouvrement 0,315 m)."),
        F("largeur_dba_min", "Largeur minimale d'une DBA (m)", 1, default_value=(0.55,), min=0.3, max=1.0,
          help="[G] seuil déclaré : une « GBA » de largeur ≥ 0,55 m est posée en séparateur double DBA (base 0,60 m, "
               "Cerema DR p. 32) ; en dessous, GBA simple (base 0,48 m)."),
        F("encastrement", "Encastrement de la base béton (m)", 1, default_value=(0.05,), min=0.0, max=0.3,
          help="[G] base des contours béton descendue sous le sol fabriqué (coulé en place sur la chaussée : aucune "
               "lumière sous le talon quand le sol a un dévers)."),
        S("classes_trafic", "Classes de sol circulées", 1,
          default_value=("voie_circulation voie_insertion voie_deceleration voie_bus bande_derasee bande_arret_urgence",),
          help="Classes de rg::sol qui désignent le côté du trafic d'une limite (face de la glissière)."),
        S("materiau_beton", "Matériau béton", 1, default_value=(cat[CONTOURS["dba"]]["materiau"],),
          help="Catalogue route_fr : matériau des séparateurs béton."),
        S("materiau_acier", "Matériau acier", 1, default_value=(cat[GLISSIERES["gs2"]]["materiau"],),
          help="Catalogue route_fr : matériau des glissières."),
        F("mesure_raccord", "Raccord des bretelles : distance de mesure (m)", 1, default_value=(0.5,), min=0.05, max=5.0,
          help="Z de chaque chaussée mesuré à cette distance à l'intérieur de la chaussée, de part et d'autre du point "
               "de jonction (dz = Z principale − Z bretelle ; profil en long de la bretelle parallèle, [G])."),
        F("pas_musoir", "Pas du sol du musoir (m)", 1, default_value=(1.0,), min=0.1, max=10.0,
          help="Pas en long des bandes du sol du musoir (bornes des sections et point à 5,00 m ajoutés)."),
        F("degagement_u", "Espace non peint (u)", 1, default_value=(2.0,), min=0.0, max=10.0,
          help="RF-MQ-MUS-01 : 2u entre la ligne de contour 3u et les hachures ou chevrons."),
        F("hach_bande", "Chevrons : largeur des bandes (m)", 1, default_value=(float(d20["bande"]),), min=0.1, max=1.0,
          help="DEF-020, RF-MQ-HACH-01 et -02 (chevrons : dimensions des hachures) : 0,50."),
        F("hach_espacement", "Chevrons : espacement entre parallèles (m)", 1, default_value=(float(d20["espacement"]),),
          min=0.1, max=5.0, help="DEF-020, RF-MQ-HACH-01 : 1,35."),
        F("hach_angle", "Chevrons : angle avec la bissectrice (°)", 1, default_value=(float(d20["angle_rive_deg"]),),
          min=1.0, max=89.0, help="RF-MQ-HACH-02 : 2 pour 1 par rapport à la bissectrice (26,565°)."),
        F("hach_aplat", "Aplat sous la largeur (m)", 1, default_value=(float(d20["aplat_si_largeur_inf"]),),
          min=0.0, max=2.0, help="RF-MQ-HACH-03, DEF-020 : pointe effilée de moins de 0,30 m peinte en aplat."),
        F("u_defaut", "u par défaut (m)", 1, default_value=(float(regles.valeur("RF-MQ-U-01")["u"]),), min=0.01, max=0.1,
          help="RF-MQ-U-01 : u = 7,5 cm sur autoroute (si la ligne de contour ne le dit pas)."),
    ]
    return pp


def construire(dossier=ICI):
    sub = R.sous_reseau("rg_" + NOM)
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres()))
    e1, e2, e3, e4 = sub.indirectInputs()[:4]
    C = VA.VEX_COMMUN
    g_ref = R.wrangle(sub, "groupe_ref", 'i@group_ref = 1;', "primitive", e4, precision="64")
    g_zone = R.wrangle(sub, "groupe_zone", 'i@group_zone = 1;', "primitive", e3, precision="64")
    g_nd = R.wrangle(sub, "groupe_noeud", 'if (s@type != "") i@group_noeud = 1;', "point", g_zone, precision="64")
    ctx = sub.createNode("merge", "contexte")
    ctx.setInput(0, g_ref)
    ctx.setInput(1, g_nd)
    rac = R.wrangle(sub, "raccord", C + VA.VEX_RACCORD, "detail", e2, entrees=(ctx,))
    app = R.wrangle(sub, "appliquer", VA.VEX_APPLIQUER, "point", rac)
    vide = sub.createNode("blast", "vide")
    vide.setInput(0, e1)
    vide.parm("group").set("*")
    vide.parm("grouptype").set("prims")
    vide2 = sub.createNode("blast", "vide_points")
    vide2.setInput(0, vide)
    vide2.parm("group").set("*")
    vide2.parm("grouptype").set("points")
    mus = R.wrangle(sub, "musoirs", C + VA.VEX_MUSOIRS, "detail", vide2, entrees=(e1, app, ctx))
    sep = R.wrangle(sub, "separateurs", C + VA.VEX_SEPARATEURS, "detail", vide2, entrees=(e1, app))
    # ---- sol : routes raccordées + musoirs (faces orientées vers le haut, normales et uv au sommet comme rg::sol)
    gore = sub.createNode("blast", "sol_musoirs")
    gore.setInput(0, mus)
    gore.parm("group").set("sol_musoir")
    gore.parm("grouptype").set("prims")
    gore.parm("negate").set(1)
    ori = R.wrangle(sub, "orienter_sol", 'if (prim_normal(0, @primnum, {0.5, 0.5, 0}).y < 0) i@group_a_inverser = 1;',
                    "primitive", gore)
    rev = sub.createNode("reverse", "inverser_sol")
    rev.setInput(0, ori)
    rev.parm("group").set("a_inverser")
    nm = sub.createNode("normal", "normales_sol")
    nm.setInput(0, rev)
    nm.parm("type").set(1)          # sommets
    nm.parm("cuspangle").set(30.0)
    uv = R.wrangle(sub, "uv_sol", "v@uv = set(@P.x, -@P.z, 0);", "sommet", nm)
    nett = sub.createNode("groupdelete", "groupes_musoir")
    nett.setInput(0, uv)
    nett.parm("group1").set("sol_musoir marques_musoir a_inverser")
    msol = sub.createNode("merge", "sol_total")
    msol.setInput(0, app)
    msol.setInput(1, nett)
    # ---- marques des musoirs (orientation des polygones comme rg::marquages : normale vers le haut)
    mq = sub.createNode("blast", "marques_musoirs")
    mq.setInput(0, mus)
    mq.parm("group").set("marques_musoir")
    mq.parm("grouptype").set("prims")
    mq.parm("negate").set(1)
    orm = R.wrangle(sub, "orienter_marques", 'if (prim_normal(0, @primnum, {0.5, 0.5, 0}).y < 0) i@group_a_inverser = 1;',
                    "primitive", mq)
    revm = sub.createNode("reverse", "inverser_marques")
    revm.setInput(0, orm)
    revm.parm("group").set("a_inverser")
    nett2 = sub.createNode("groupdelete", "groupes_marques")
    nett2.setInput(0, revm)
    nett2.parm("group1").set("sol_musoir marques_musoir a_inverser")
    # ---- équipements
    fin = R.wrangle(sub, "finir_equipements", VA.VEX_FINIR_EQUIPEMENTS, "primitive", sep)
    nme = sub.createNode("normal", "normales_equipements")
    nme.setInput(0, fin)
    nme.parm("type").set(1)
    nme.parm("cuspangle").set(40.0)
    uve = R.wrangle(sub, "uv_equipements", VA.VEX_UV_EQUIPEMENTS, "sommet", nme)
    # ---- contrôles : détail des musoirs, des séparateurs (entrée 1) et du raccord des bretelles (entrée 2)
    ctl = sub.createNode("merge", "controles_fusion")
    ctl.setInput(0, mus)
    ctl.setInput(1, sep)
    ctlv = sub.createNode("blast", "controles")
    ctlv.setInput(0, ctl)
    ctlv.parm("group").set("*")
    ctlv.parm("grouptype").set("prims")
    cdet = R.wrangle(sub, "controles_detail", VA.VEX_CONTROLES, "detail", ctlv, entrees=(sep, rac))
    outs = []
    for k, (n, nom) in enumerate(((msol, "SOL"), (uve, "EQUIPEMENTS"), (nett2, "MARQUES"), (cdet, "CONTROLES"))):
        o = sub.createNode("null", nom)
        o.setInput(0, n)
        R.sortie(sub, o, k, f"sortie_{k + 1}")
        outs.append(o)
    outs[0].setDisplayFlag(True)
    R.ranger(sub)
    aide = ("Autoroutes : dispositifs de retenue des terre-pleins (GBA / DBA béton, glissières) le long des limites "
            "« separateur » du modèle ; bifurcations (bretelles) : raccord vertical de la bretelle, sol du musoir et du "
            "terre-plein latéral, aplat de pointe et chevrons.")
    details = ("== Entrées ==\n\n1. Limites (rg::profils, sortie 1), 2. Sol (rg::sol, sortie 1), 3. Zones et îlots "
               "(rg::lire_modele, sortie 3), 4. Nœuds (rg::lire_modele, sortie 2), 5. Références (rg::graphe, sortie 1)."
               "\n\n== Sorties ==\n\n1. SOL : sol des routes (bretelles décalées de dz) + sol des musoirs (contrat de "
               "rg::sol).\n2. ÉQUIPEMENTS : maillages des dispositifs de retenue.\n3. MARQUES : aplats et chevrons "
               "(contrat de pj::marquage_solide).\n4. CONTRÔLES : détail (ra_m_* : bifurcations ; ra_s_* : séparateurs ; "
               "ra_bretelles, ra_dz).\n\nRègles : RF-GV-TPC-002, -003, -008 ; RF-MQ-MUS-01 ; RF-MQ-HACH-01 à -03 ; "
               "DEF-020 ; RF-MQ-U-01 ; catalogue route_fr (retenue_*).")
    return R.creer_hda(sub, NOM, "RG Autoroute (retenues, musoirs, raccord des bretelles)", parametres(), dossier,
                       entrees=(4, 4), sorties=4, aide=aide, details_aide=details, icone="SOP_sweep",
                       etiquettes_entrees=("Limites (rg::profils)", "Sol (rg::sol)",
                                           "Zones, îlots et nœuds (rg::lire_modele)", "Références (rg::graphe)"),
                       etiquettes_sorties=("Sol (routes raccordées + musoirs)", "Équipements", "Marques des musoirs",
                                           "Contrôles"))


if __name__ == "__main__":
    print(construire())
