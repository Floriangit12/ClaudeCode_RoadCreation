"""Construit l'HDA rg::ouvrages::1.0 (lot « ouvrages » : L8 du plan, étape E07 de la chaîne) ; hython Houdini 22.

    hython recon/generateur/hda/rg_ouvrages/construire.py

rg::ouvrages (« RG Ouvrages (tabliers, appuis, retenues, terrain) ») :
    entrées 1 ROUTES fabriquées par la chaîne L1 + L2 + L2b (+ rg::autoroute) de chaque couche (sol, BEV, bordures,
            caniveaux, avaloirs, équipements, peinture ; attributs de primitive route, couche_rendu, materiau_id),
            2 RÉFÉRENCES (rg::graphe, sortie 1, de chaque route : polylignes s@id, f@s)
    paramètre fichier : modèle modele_voie (ouvrages[].construction, routes[].profil_long) lu par un Python SOP
    (entrée-sortie seulement) ; toute la géométrie est construite en VEX (vex_ouvrages.py).
      -> lire_ouvrages (Python) : un point par ouvrage, un point par profil en long ; emprise du terrain
      -> routes : briques de 1 m (Divide) sur les routes profilées, z += z_long(s) (profil en long du modèle), normales
         transformées (J^-T) : la coupe, les bordures, les caniveaux et la peinture suivent le profil (marquages continus
         sur l'ouvrage, profil courant conservé)
      -> structures (VEX) : tablier balayé sous la section de la route portée (dalle, dalle à larges encorbellements,
         portique, caisson, poutres + hourdis), corniches, piles (voiles, poteaux + chevêtre), bossages et appareils
         d'appui, culées (sommier, garde-grève, murs en retour), dalles de transition, piédroits et murs en aile des
         portiques, garde-corps S8 et barrières BN4 fabriqués ; joints de chaussée drapés sur le sol déformé
      -> terrain (VEX) : grille, terrain naturel, talweg, remblais (talus OA-TAL-001), massifs des culées, déblai de la
         route franchie (couloir vertical sous un portique) ; jupes sous les bords des plates-formes ; intégration de
         l'étape 4 : remblai autour du sol des routes à niveau (ni portées ni franchies : bretelle, carrefour)
      -> points : garde-corps (modules du catalogue route_fr mis à la hauteur du modèle) et BN4, au contrat pj_points
    sorties 1 ROUTES DÉFORMÉES, 2 OUVRAGES (maillages : materiau_id, partie, ouvrage, pj_couche, pj_entite, N, uv),
            3 TERRAIN (maillage ; zone), 4 POINTS (instances), 5 OUVRAGES LUS (points de lire_ouvrages, contrôle).
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "commun"))
sys.path.insert(0, str(ICI))
import rg_hda_outils as R  # noqa: E402
import vex_ouvrages as VO  # noqa: E402

NOM = "ouvrages"


def parametres():
    F, S = hou.FloatParmTemplate, hou.StringParmTemplate
    return [
        S("fichier", "Modèle (modele_voie.json)", 1, default_value=("",), string_type=hou.stringParmType.FileReference,
          help="modèle compilé : ouvrages[].construction (description/ouvrages.py) et routes[].profil_long"),
        F("brique", "Brique de déformation (m)", 1, default_value=(1.0,),
          help="[G] : les polygones des routes profilées sont découpés en briques de 1 m avant la déformation verticale "
               "(flèche d'une corde de 1 m sur un rentrant de 800 m : 0,16 mm, sous l'épaisseur de la peinture)"),
        F("pas_terrain", "Pas du terrain (m)", 1, default_value=(1.0,), help="[G] maillage du terrain"),
        F("pas_terrain_fin", "Pas du terrain près des ouvrages (m)", 1, default_value=(0.5,),
          help="[G] maillage du terrain dans l'emprise de l'ouvrage + 30 m ; ≤ épaisseur des murs en aile"),
        F("etendue_terrain", "Étendue du terrain au-delà des routes (m)", 1, default_value=(2000.0,),
          help="[G] le terrain (naturel, talweg) continue jusqu'à 2 km au-delà de l'emprise des routes, mailles "
               "croissantes (quart de la distance) : horizon sans couture au rendu"),
    ]


def _wr(sub, nom, code, classe, entree, entrees=()):
    return R.wrangle(sub, nom, VO.LIB + code, classe, entree, entrees=entrees)


def construire(dossier=ICI):
    sub = R.sous_reseau("rg_" + NOM)
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres()))
    e1, e2 = sub.indirectInputs()[:2]
    lire = sub.createNode("python", "lire_ouvrages")
    lire.parm("python").set(VO.PY_LIRE)
    vide = sub.createNode("null", "vide")                       # entrée 0 (vide) des wrangles de détail
    # ---- routes déformées
    grp = _wr(sub, "a_profiler", 'i@group_a_profiler = (oa_point_profil(s@route) >= 0);', "primitive", e1, (e2, lire))
    div = sub.createNode("divide", "briques")
    div.setInput(0, grp)
    div.parm("group").set("a_profiler")
    div.parm("convex").set(0)
    div.parm("brick").set(1)
    for a in ("sizex", "sizez"):
        div.parm(a).setExpression('ch("../brique")')
    div.parm("sizey").set(10000.0)
    prom = sub.createNode("attribpromote", "route_aux_points")
    prom.setInput(0, div)
    prom.parm("inname").set("route")
    prom.parm("inclass").set(1)                                  # primitive
    prom.parm("outclass").set(2)                                 # point
    prom.parm("deletein").set(0)
    sta = _wr(sub, "station", VO.VEX_STATION, "point", prom, (e2, lire))
    nv = R.wrangle(sub, "normales_sommets", VO.VEX_NORMALES, "sommet", sta)
    npt = R.wrangle(sub, "normales_points", VO.VEX_NORMALES_POINTS, "point", nv)
    dfm = R.wrangle(sub, "deformer", VO.VEX_DEFORMER, "point", npt)
    net = sub.createNode("attribdelete", "nettoyer_routes")
    net.setInput(0, dfm)
    net.parm("ptdel").set("oa_* route")
    sansn = R.wrangle(sub, "sans_normales", 'i@group_sans_n = 0; int vs[] = primvertices(0, @primnum); '
                      'foreach (int v; vs) if (length(vector(vertex(0, "N", v))) < 1e-6) i@group_sans_n = 1;',
                      "primitive", net)
    nrm = sub.createNode("normal", "normales_manquantes")
    nrm.setInput(0, sansn)
    nrm.parm("group").set("sans_n")
    nrm.parm("type").set(1)                                      # sommets
    nrm.parm("cuspangle").set(40.0)
    gdel = sub.createNode("groupdelete", "groupes_routes")
    gdel.setInput(0, nrm)
    gdel.parm("group1").set("a_profiler sans_n")
    # sol et bordures déformés (joints drapés sur le revêtement et par-dessus les bordures)
    sol = sub.createNode("blast", "sol_et_bordures_deformes")
    sol.setInput(0, gdel)
    sol.parm("group").set('@couche_rendu=Sol @couche_rendu=Bordures')
    sol.parm("grouptype").set("prims")
    sol.parm("negate").set(1)
    # ---- structures et joints
    st = _wr(sub, "structures", VO.VEX_STRUCTURES, "detail", vide, (e2, lire))
    jt = _wr(sub, "joints", VO.VEX_JOINTS, "detail", vide, (e2, lire, sol))
    mg = sub.createNode("merge", "ouvrages_bruts")
    mg.setInput(0, st)
    mg.setInput(1, jt)
    ori = R.wrangle(sub, "orienter", VO.VEX_ORIENTER, "primitive", mg)
    rev = sub.createNode("reverse", "inverser")
    rev.setInput(0, ori)
    rev.parm("group").set("a_inverser")
    nm = sub.createNode("normal", "normales_ouvrages")
    nm.setInput(0, rev)
    nm.parm("type").set(1)                                       # sommets
    nm.parm("cuspangle").set(40.0)
    uv = R.wrangle(sub, "uv_ouvrages", VO.VEX_UV, "sommet", nm)
    fin_o = sub.createNode("attribdelete", "nettoyer_ouvrages")
    fin_o.setInput(0, uv)
    fin_o.parm("primdel").set("dehors")
    g2 = sub.createNode("groupdelete", "groupes_ouvrages")
    g2.setInput(0, fin_o)
    g2.parm("group1").set("a_inverser")
    # ---- terrain
    gr = _wr(sub, "grille", VO.VEX_GRILLE, "detail", vide, (e2, lire))
    # intégration de l'étape 4 : sol des routes à niveau (vide si toutes les routes sont portées ou franchies)
    niv = _wr(sub, "routes_a_niveau", VO.VEX_A_NIVEAU, "primitive", gdel, (e2, lire))
    apl = R.wrangle(sub, "aplatir", VO.VEX_APLATIR, "point", niv)
    ter = R.wrangle(sub, "terrain", "#define OA_AVEC_NIVEAU 1" + chr(10) + VO.LIB + VO.VEX_TERRAIN, "point", gr,
                    entrees=(e2, lire, apl))
    trg = R.wrangle(sub, "trianguler", VO.VEX_TRIANGULER, "detail", ter)
    jp = _wr(sub, "jupes", VO.VEX_JUPES, "detail", vide, (e2, lire))
    mt = sub.createNode("merge", "terrain_et_jupes")
    mt.setInput(0, trg)
    mt.setInput(1, jp)
    ori_t = R.wrangle(sub, "orienter_terrain", 'if (s@partie == "terrain" && prim_normal(0, @primnum, {0.5, 0.5, 0}).y '
                      '< -1e-6) i@group_a_inverser = 1;', "primitive", mt)
    rev_t = sub.createNode("reverse", "inverser_terrain")
    rev_t.setInput(0, ori_t)
    rev_t.parm("group").set("a_inverser")
    nmt = sub.createNode("normal", "normales_terrain")
    nmt.setInput(0, rev_t)
    nmt.parm("type").set(1)
    nmt.parm("cuspangle").set(60.0)
    uvt = R.wrangle(sub, "uv_terrain", VO.VEX_UV, "sommet", nmt)
    g3 = sub.createNode("groupdelete", "groupes_terrain")
    g3.setInput(0, uvt)
    g3.parm("group1").set("a_inverser")
    # ---- points
    pts = _wr(sub, "points", VO.VEX_POINTS, "detail", vide, (e2, lire))
    for k, (n, nom) in enumerate(((gdel, "ROUTES"), (g2, "OUVRAGES"), (g3, "TERRAIN"), (pts, "POINTS"),
                                  (lire, "OUVRAGES_LUS"))):
        o = sub.createNode("null", nom)
        o.setInput(0, n)
        R.sortie(sub, o, k, f"sortie_{k + 1}")
    sub.layoutChildren()
    aide = ("Ouvrages d'art du générateur (lot L8 / étape E07) : profil en long des routes portées, tabliers balayés sous "
            "la section courante, appuis, culées, joints, garde-corps et BN4, terrain (remblais, talus 3/2, talweg, déblai "
            "de la route franchie). Cotes du modèle (description/ouvrages.py) ; choix [G] déclarés dans vex_ouvrages.py.")
    return R.creer_hda(sub, NOM, "RG Ouvrages (tabliers, appuis, retenues, terrain)", parametres(), dossier,
                       entrees=(2, 2), sorties=5, aide=aide,
                       etiquettes_entrees=("routes fabriquées", "références (rg::graphe)"),
                       etiquettes_sorties=("routes déformées", "ouvrages", "terrain", "points", "ouvrages lus"))


if __name__ == "__main__":
    print(construire())
