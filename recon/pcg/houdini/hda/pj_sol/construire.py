"""Construit l'HDA pj::sol::1.0 (sol du site : surfaces triangulées sur le modèle de nivellement unique) ; hython 22.

    hython recon/pcg/houdini/hda/pj_sol/construire.py                  # construit et enregistre pj_sol.hdalc/
    hython recon/pcg/houdini/hda/pj_sol/construire.py --essai [pilote|site|boite x0 y0 x1 y1]

Réseau (README_HDA.md § « pj::sol ») :
  entrée 1 (polygones de surfaces + trous, BEV) -> selectionner -> aplatir -> densifier (Resample par arête, bords
  identiques des deux côtés d'une limite partagée) -> indexer (surf_index, arête cible par classe) -> echelle
  -> boucle compilée par surface (For-Each id) : Triangulate 2D contraint (Refine, angle min 25°, arête cible ; bords
  non découpés) -> trous -> attributs -> echelle_inverse -> altitude (VEX : modèle de nivellement, nœuds valides
  seulement, pj_sol.h) -> altitude_emprise (sol sous bordure au pied) -> Fuse (coutures soudées) -> Normal (cusp 30°)
  -> UV (mètres, monde) -> export (tuiles de 50 m) ;
  BEV : bev_dalles (VEX, dalles trapézoïdales le long de l'arc) -> bev_altitude -> plots (Tube + Copy to Points).
Sortie : maillages Y haut (materiau_id, pj_couche = PJ_Sol, pj_entite = tuile ou BEV, N, uv).
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
HDA = ICI.parent
sys.path.insert(0, str(HDA / "commun"))
sys.path.insert(0, str(ICI))
import pj_hda_outils as O  # noqa: E402
import reseau_sol as R  # noqa: E402

NOM = "sol"
VEX = ICI / "vex"
VEX_B = HDA / "pj_bordure" / "vex"


corps = R.corps
entetes = R.entetes
blast = R.blast


def parametres():
    T = hou
    F = T.FloatParmTemplate
    tg = T.ToggleParmTemplate
    sel = [
        tg("exclure_ilots", "Exclure les surfaces d'îlots", default_value=True,
           help="Surfaces listées par un îlot (attribut ilots) : fabriquées par pj::ilot (remplissage sous la ceinture)."),
        tg("emprises", "Sol sous les bordures (emprises)", default_value=True,
           help="Classe emprise_bordure : sol au pied de face, caché par les éléments (TQ-BOR-007)."),
        T.StringParmTemplate("classes_exclues", "Classes exclues", 1, default_value=("",),
                             help="Classes de surfaces à ne pas fabriquer, séparées par des espaces."),
        tg("bev", "Bandes d'éveil (BEV)", default_value=True, help="Dalles podotactiles 3D (ponctuels_sol type bev)."),
    ]
    tri = [
        F("pas_bords", "Pas des bords (m)", 1, default_value=(0.5,), min=0.05, max=5.0,
          help="Bords redécoupés arête par arête (même découpe des deux côtés d'une limite partagée)."),
        F("arete_chaussee", "Arête cible chaussée (m)", 1, default_value=(0.5,), min=0.05, max=5.0,
          help="TQ-SOL-002 : 0,5 m sur la chaussée et les parkings."),
        F("arete_trottoir", "Arête cible trottoirs, pistes, quais (m)", 1, default_value=(0.35,), min=0.05, max=5.0,
          help="Cheminements plans (dévers) ; TQ-SOL-002 vise 0,25 m : les rampes et talus restent à arete_rampe."),
        F("arete_rampe", "Arête cible rampes et talus (m)", 1, default_value=(0.25,), min=0.05, max=5.0,
          help="TQ-SOL-002 : 0,25 m (plans inclinés d'abaissés, talus de noue)."),
        F("arete_emprise", "Arête cible sous les bordures (m)", 1, default_value=(1.0,), min=0.05, max=5.0,
          help="Sol caché sous les éléments : aucun raffinement utile."),
        F("arete_parking", "Arête cible parkings (m)", 1, default_value=(0.75,), min=0.05, max=5.0),
        F("arete_vert", "Arête cible espaces verts (m)", 1, default_value=(1.2,), min=0.05, max=5.0),
        F("angle_min", "Angle minimal (°)", 1, default_value=(25.0,), min=0.0, max=33.0, help="TQ-SOL-002 : 25°."),
        F("pente_marche_deg", "Marches : pente limite (°)", 1, default_value=(40.0,), min=10.0, max=89.0,
          help="Triangles plus raides (et de plus de 2 cm de dénivelé) adoucis par flou de Z (VAL-SOL-009, E8)."),
        T.IntParmTemplate("marches_iterations", "Marches : itérations du flou", 1, default_value=(40,), min=0, max=500),
        F("trou_min_m2", "Trous comblés sous (m²)", 1, default_value=(2.0,), min=0.0, max=20.0,
          help="Trous (anneau ≥ 1) plus petits, sans surface décrite dedans (mâts, armoires) : comblés par la surface."),
        F("souder_mm", "Soudure des coutures (mm)", 1, default_value=(0.1,), min=0.0, max=5.0,
          help="Points confondus (même XY, même Z) soudés : normales continues d'une surface à l'autre (TQ-SOL-008)."),
        F("emprise_sous_pied_mm", "Sol sous bordure : sous le pied (mm)", 1, default_value=(0.0,), min=0.0, max=50.0),
    ]
    rac = [
        F("raccord_avant_m", "Raccord au pied de face (m)", 1, default_value=(0.3,), min=0.0, max=2.0,
          help="Chaussée raccordée au pied de face de la bordure (TQ-SOL-013 (4), VAL-SOL-009 (2)) ; 0 : aucun."),
        F("raccord_arriere_m", "Raccord derrière la tête (m)", 1, default_value=(1.0,), min=0.0, max=4.0,
          help="Toute surface derrière l'arête arrière : tête − 4 mm (TQ-SOL-013 (6)) ; 0 : aucun."),
        F("raccord_pente_avant_pct", "Pente max du raccord avant (%)", 1, default_value=(10.0,), min=1.0, max=100.0),
        F("raccord_pente_arriere_pct", "Pente max du raccord arrière (%)", 1, default_value=(8.0,), min=1.0, max=100.0,
          help="GA-TRO-004 : 8 % sur 2 m au plus."),
        F("raccord_max_m", "Longueur max d'un raccord (m)", 1, default_value=(3.0,), min=0.1, max=10.0),
        F("raccord_lissage_m", "Lissage de l'écart le long des bordures (m)", 1, default_value=(0.5,), min=0.0,
          max=5.0, help="Moyenne glissante de ± cette longueur sur l'écart bordure / sol (grille en escalier)."),
        F("sous_caniveau_mm", "Chaussée sous les caniveaux (mm)", 1, default_value=(10.0,), min=0.0, max=50.0,
          help="Devant une bordure à caniveau, la chaussée passe sous l'élément CS (TQ-BOR-007, pas de z-fighting)."),
    ]
    sor = [
        T.StringParmTemplate("couche", "Couche USD", 1, default_value=("PJ_Sol",)),
        T.MenuParmTemplate("format_usd", "Format du fichier USD", menu_items=("usdc", "usda"),
                           menu_labels=("Binaire (.usdc)", "Texte (.usda)"), default_value=0,
                           help="Lu par fabriquer_hda.py : le sol du site (plus d'un million de triangles) en binaire."),
        F("tuile_m", "Taille des tuiles (m)", 1, default_value=(50.0,), min=8.0, max=300.0,
          help="TQ-SOL-010 : tuiles de 50 m (64 m au plus) depuis le coin SO (−150, −150)."),
        tg("bev_chants", "BEV : chants enterrés", default_value=False,
           help="Chants verticaux sous le dessus des dalles (sur une rampe, E8 les compte comme sol raide)."),
        F("bev_epaisseur_mm", "BEV : épaisseur sous le sol (mm)", 1, default_value=(25.0,), min=5.0, max=29.0,
          help="Profondeur des chants enterrés."),
        F("bev_dessus_mm", "BEV : dessus au-dessus du sol (mm)", 1, default_value=(3.0,), min=0.0, max=5.0,
          help="E9 : dessus des dalles à moins de 5 mm du sol."),
    ]
    return [T.FolderParmTemplate("f_sel", "Sélection", parm_templates=sel, folder_type=T.folderType.Tabs),
            T.FolderParmTemplate("f_tri", "Triangulation", parm_templates=tri, folder_type=T.folderType.Tabs),
            T.FolderParmTemplate("f_rac", "Raccords aux bordures", parm_templates=rac, folder_type=T.folderType.Tabs),
            T.FolderParmTemplate("f_sor", "Sorties", parm_templates=sor, folder_type=T.folderType.Tabs)]


def _iv_index():
    """pj_iv_index (pj_pose.h) : intervalle de la description qui contient s."""
    t = (HDA / "pj_bordure" / "vex" / "pj_pose.h").read_text(encoding="utf-8")
    a = t.index("function int pj_iv_index(")
    b = t.index(chr(10) + "}" + chr(10), a) + 3
    return t[a:b] + chr(10)


def boucle_tuiles(sub, entree, axe):
    """For-Each par nombre (rétroaction) : Clip SOP « les deux côtés » sur la ligne de tuile k (k = 1 .. n − 1,
    n = ceil(300 / tuile_m)) de l'axe local x (plan X Houdini) ou y (plan Z Houdini, z = −y)."""
    fb = sub.createNode("block_begin", f"tuiles_{axe}_debut")
    fb.parm("method").set("feedback")
    meta = sub.createNode("block_begin", f"tuiles_{axe}_meta")
    meta.parm("method").set("metadata")
    cl = sub.createNode("clip", f"couper_tuiles_{axe}")
    cl.setInput(0, fb)
    cl.parm("clipop").set("both")
    k = f'(detail("../{meta.name()}", "iteration", 0) + 1) * ch("../tuile_m") - 150'
    if axe == "x":
        cl.parm("originx").setExpression(k)
        cl.parmTuple("dir").set((1.0, 0.0, 0.0))
    else:
        cl.parm("originz").setExpression("-(" + k + ")")
        cl.parmTuple("dir").set((0.0, 0.0, 1.0))
    fe = sub.createNode("block_end", f"tuiles_{axe}_fin")
    fe.setInput(0, cl)
    fe.parm("itermethod").set("count")
    fe.parm("method").set("feedback")
    fe.parm("iterations").setExpression('max(0, ceil(300 / ch("../tuile_m")) - 1)')
    fe.parm("blockpath").set(f"../{fb.name()}")
    fe.parm("templatepath").set(f"../{fb.name()}")
    fb.setInput(0, entree)
    fb.parm("blockpath").set(f"../{fe.name()}")
    meta.parm("blockpath").set(f"../{fe.name()}")
    meta.setInput(0, entree)
    return fe


def reseau(sub):
    ent = sub.createNode("null", "ENTREE_SURFACES")
    ent.setInput(0, sub.indirectInputs()[0])
    niv = sub.createNode("null", "ENTREE_NIVEAU")
    niv.setInput(0, sub.indirectInputs()[1])
    ctx = sub.createNode("null", "ENTREE_CONTEXTE")
    ctx.setInput(0, sub.indirectInputs()[2])
    bords = blast(sub, "bordures", ctx, "@famille=bordures")
    sel = O.wrangle(sub, "selectionner", corps("sol.vfl", "selectionner"), "primitive", ent)
    apl = O.wrangle(sub, "aplatir", corps("sol.vfl", "aplatir"), "point", sel)
    den = sub.createNode("resample", "densifier")
    den.setInput(0, apl)
    for p, v in (("edge", 1), ("dolength", 1), ("allequal", 1)):
        den.parm(p).set(v)
    den.parm("length").setExpression('ch("../pas_bords")')
    ext = blast(sub, "anneaux_exterieurs", den, "@anneau=0")
    # petits trous sans surface décrite dedans (emprises de mâts, armoires, plots : « bâtiments » de moins de
    # trou_min_m2) : comblés par la surface qui les entoure (pas de vide noir dans la chaussée ou l'îlot ; le mobilier
    # est posé par Unreal) ; les enclaves décrites restent des trous (TQ-SOL-009 : aucun recouvrement)
    surf_tous = blast(sub, "surfaces_toutes", ent, "@famille=surfaces")                      # îlots compris
    ext_tous = blast(sub, "anneaux_exterieurs_tous", surf_tous, "@anneau=0")
    pt_ = O.wrangle(sub, "petits_trous", corps("sol.vfl", "petits_trous"), "primitive", den, entrees=(ext_tous,))
    idx = O.wrangle(sub, "indexer", corps("sol.vfl", "indexer"), "primitive", pt_, entrees=(ext,))
    ech = O.wrangle(sub, "echelle", corps("sol.vfl", "echelle"), "point", idx)
    inv = R.boucle_triangulation(sub, ech)
    plat = sub.createNode("null", "SOL_PLAT")
    plat.setInput(0, inv)
    alt = O.wrangle(sub, "altitude", entetes(sol=True) + corps("sol.vfl", "altitude"), "point", plat,
                    entrees=(niv, plat, ext))
    alte = O.wrangle(sub, "altitude_emprise", entetes(courbe=True) + corps("sol.vfl", "altitude_emprise"), "point",
                     alt, entrees=(bords,))
    prac = O.wrangle(sub, "profils_raccord", entetes(courbe=True, sol=True) + _iv_index() +
                     corps("sol.vfl", "profils_raccord"), "primitive", bords, entrees=(niv, plat, ext))
    rac = O.wrangle(sub, "raccords_bordures", entetes(courbe=True, sol=True) + _iv_index() +
                    corps("sol.vfl", "raccords_bordures"), "point", alte, entrees=(prac, ext))
    rog = O.wrangle(sub, "rogner", r"""
// rogner (primitive) : triangles hors du modèle de nivellement retirés (sommet sans nœud de nivellement : entité
// chargée entière dont une partie dépasse le recadrage du HeightField de l'emprise ; jamais de Z inventé).
foreach (int p; primpoints(0, @primnum)) {
    if (point(0, "niv_absent", p)) { removeprim(0, @primnum, 1); break; }
}
""", "primitive", rac)
    # ---- limites partagées sans bordure : sommets de même XY de deux surfaces continues ramenés au même Z (moyenne),
    # puis soudés (Fuse) : aucune fissure entre deux surfaces qu'aucune bordure ne sépare
    zp = O.wrangle(sub, "z_a_plat", "f@zr = @P.y; @P.y = 0;", "point", rog)
    lim = O.wrangle(sub, "limites_partagees", entetes(sol=True) + corps("sol.vfl", "limites_partagees"), "point", rog,
                    entrees=(zp, ext))
    fu = sub.createNode("fuse::2.0", "souder_coutures")
    fu.setInput(0, lim)
    fu.parm("tol3d").setExpression('ch("../souder_mm") / 1000')
    # ---- marches résiduelles du modèle (VAL-SOL-009 (1), E8) : triangles de plus de pente_marche_deg et de plus de 2 cm
    # dans une même surface continue (la grille de 0,10 m en porte quelques milliers, nivellement.json controles ; aux
    # contacts de bordures, écarts de tête jusqu'à 19 cm, GA-BOR-005) : adoucies par flou de Z (Attribute Blur) sur
    # leurs sommets et 2, 4, 6 puis 8 anneaux voisins (passes 1 à 4 : bouts de bordure où le sol contourne l'about) ;
    # talus de noue (pente voulue) et BEV laissés en place.
    zr = fu
    for passe in (1, 2, 3, 4):                           # quatre passes : détection -> voisinage -> flou de Z
        mar = O.wrangle(sub, f"marches_{passe}", r"""
    // marches (primitive) : sommets des triangles trop raides (hors BEV) ; noue : au-delà de 25° seulement (talus
    // voulu à 1/3, 18,4° ; GA-ASS-005 : 329 triangles de noue à plus de 20°, jusqu'à 71°, revue du 11/10/2026)
    string m = s@materiau_id, cl = s@classe;
    float lim = m == "noue_plantee" ? 25.0 : chf("../pente_marche_deg");
    if (m != "bev_podotactile" && @numvtx == 3) {
        int pts[] = primpoints(0, @primnum);
        vector a = point(0, "P", pts[0]), b = point(0, "P", pts[1]), c = point(0, "P", pts[2]);
        vector nn = cross(b - a, c - a);
        float ln = length(nn);
        float dz = max(a.y, max(b.y, c.y)) - min(a.y, min(b.y, c.y));
        if (ln > 1e-8 && degrees(acos(clamp(abs(nn.y) / ln, 0.0, 1.0))) > lim && dz > 0.02)
            foreach (int p; pts) setpointgroup(0, "raides", p, 1);
    }
    """, "primitive", zr)
        ge = sub.createNode("groupexpand", f"voisins_marches_{passe}")
        ge.setInput(0, mar)
        for p, v in (("group", "raides"), ("grouptype", 3), ("outputgroup", "raides"), ("numsteps", 2 * passe)):
            ge.parm(p).set(v)
        zb = O.wrangle(sub, f"z_a_adoucir_{passe}", r"""
    // z_a_adoucir (point) : Z copié dans zb (seuls les sommets du groupe raides sont adoucis).
    f@zb = @P.y;
    """, "point", ge)
        bl = sub.createNode("attribblur", f"adoucir_marches_{passe}")
        bl.setInput(0, zb)
        for p, v in (("group", "raides"), ("attributes", "zb"), ("pinborder", 0), ("stepsize", 0.5)):
            bl.parm(p).set(v)
        bl.parm("iterations").setExpression('ch("../marches_iterations")')
        zr = O.wrangle(sub, f"z_adoucie_{passe}", "if (inpointgroup(0, \"raides\", @ptnum)) { @P.y = f@zb; setpointgroup(0, \"raides\", @ptnum, 0); }", "point", bl)
    # ---- falaises résiduelles (E8, VAL-SOL-009 (1)) : triangle encore à plus de 45° et de plus de 0,25 m de dénivelé
    # après les passes d'adoucissement = goulet entre deux plateaux du modèle (S-0161a vers (−138,6 ; −88,2) : un parking
    # qui passe de −0,1 à −0,9 m entre deux trous de bâtiment, révélé quand les trous sont réellement retirés) : retiré
    # et compté (détail pj_sol_falaises), plutôt qu'une paroi de sol (revue du 11/10/2026)
    zr = O.wrangle(sub, "falaises", r"""
string m = s@materiau_id;
if (m != "noue_plantee" && m != "bev_podotactile" && @numvtx >= 3) {
    int pts[] = primpoints(0, @primnum);
    vector a = point(0, "P", pts[0]), b = point(0, "P", pts[1]), c = point(0, "P", pts[2]);
    vector nn = cross(b - a, c - a);
    float ln = length(nn);
    float dz = max(a.y, max(b.y, c.y)) - min(a.y, min(b.y, c.y));
    if (ln > 1e-8 && degrees(acos(clamp(abs(nn.y) / ln, 0.0, 1.0))) > 45.0 && dz > 0.25) {
        removeprim(0, @primnum, 1);
        setdetailattrib(0, "pj_sol_falaises", 1, "add");
        warning("falaise de sol retirée (%g m de dénivelé) vers (%g ; %g)", dz, a.x, -a.z);
    }
}
""", "primitive", zr)
    # ---- coutures de tuiles (TQ-SOL-003, TQ-SOL-010) : sol coupé exactement aux lignes de tuile (x = −150 + k·T et
    # y = −150 + k·T) par deux boucles For-Each « par nombre » de Clip SOP (garder les deux côtés : points de coupe
    # partagés, normales continues d'une tuile à l'autre) ; chaque triangle n'appartient plus qu'à une tuile (débord
    # jusqu'à 0,83 m avant, revue conformité 11/10/2026).
    zr = boucle_tuiles(sub, zr, "x")
    zr = boucle_tuiles(sub, zr, "y")
    nm = sub.createNode("normal", "normales")
    nm.setInput(0, zr)
    nm.parm("type").set(1)
    nm.parm("cuspangle").set(30.0)
    uv0 = O.wrangle(sub, "uv", corps("sol.vfl", "uv"), "sommet", nm)
    # ---- contrôle des aires (TQ-SOL-001, TQ-SOL-009) : aire triangulée de chaque surface = aire décrite (aire_m2) à
    # 0,5 % près, sinon avertissement du nœud (trous non retirés = sol en double couche) ; détail pj_sol_controles.
    uv = O.wrangle(sub, "controle_aires", corps("sol.vfl", "controle_aires"), "detail", uv0, entrees=(plat, ext))
    # ---- BEV
    bev_in = blast(sub, "bev_entree", ent, "@famille=ponctuels_sol")
    dal = O.wrangle(sub, "bev_dalles", entetes(courbe=True) + corps("bev.vfl", "bev_dalles"), "detail", bev_in,
                    entrees=(bords,))
    balt = O.wrangle(sub, "bev_altitude", corps("bev.vfl", "bev_altitude"), "point", dal, entrees=(zr,))
    bhp = O.wrangle(sub, "bev_hors_pietons", corps("bev.vfl", "bev_hors_pietons"), "primitive", balt)
    bhq = O.wrangle(sub, "bev_plots_hors_pietons", corps("bev.vfl", "bev_plots_hors_pietons"), "point", bhp)
    dalles = blast(sub, "bev_dalles_seules", bhq, "dalles")
    plots_pts = blast(sub, "bev_plots_points", bhq, "plots", points=True)
    tube = sub.createNode("tube", "plot")
    for p, v in (("type", 1), ("cap", 1), ("rad1", 0.0125), ("rad2", 0.0085), ("height", 0.005), ("ty", 0.0025),
                 ("cols", 10), ("orient", 1)):
        tube.parm(p).set(v)
    cpp = sub.createNode("copytopoints::2.0", "copier_plots")
    cpp.setInput(0, tube)
    cpp.setInput(1, plots_pts)
    cpp.parm("targetattribs").set(1)
    cpp.parm("applyto1").set(2)
    cpp.parm("applyattribs1").set("id dalle")
    pm = sub.createNode("attribwrangle", "plots_materiau")
    pm.parm("class").set(1)
    pm.parm("snippet").set('s@materiau_id = "bev_podotactile";')
    pm.setInput(0, cpp)
    bev = sub.createNode("merge", "bev")
    bev.setInput(0, dalles)
    bev.setInput(1, pm)
    bnm = sub.createNode("normal", "bev_normales")
    bnm.setInput(0, bev)
    bnm.parm("type").set(1)
    bnm.parm("cuspangle").set(30.0)
    buv = O.wrangle(sub, "bev_uv", r"""
// bev_uv (sommet) : mètres (E3) ; dessus des dalles : (x, y) locaux ; chants et flancs des plots : projection sur le
// plan de la face (base orthonormée), jamais de projection de dessus sur une face verticale.
vector n = prim_normal(0, @primnum, {0.5, 0.5, 0});
if (n.y > 0.95) {
    v@uv = set(@P.x, -@P.z, 0);
} else {
    vector t = abs(n.y) < 0.95 ? normalize(cross({0, 1, 0}, n)) : {1, 0, 0};
    vector b = normalize(cross(n, t));
    v@uv = set(dot(@P, t), dot(@P, b), 0);
}
s@pj_entite = s@id;
""", "sommet", bnm)
    bpe = O.wrangle(sub, "bev_entite", 's@pj_entite = sprintf("%s", re_replace("[^A-Za-z0-9]", "_", s@id));',
                    "primitive", buv)
    sw = sub.createNode("switch", "si_bev")
    sw.setInput(0, sub.createNode("null", "VIDE"))
    sw.setInput(1, bpe)
    sw.parm("input").setExpression('ch("../bev")')
    fus = sub.createNode("merge", "fusion")
    fus.setInput(0, uv)
    fus.setInput(1, sw)
    exp = O.wrangle(sub, "export", corps("sol.vfl", "export"), "primitive", fus)
    nett = sub.createNode("attribdelete", "attributs_internes")
    nett.setInput(0, exp)
    nett.parm("ptdel").set("dz_rel niv_absent zb raccord_d")
    nett.parm("primdel").set("arete_cible surf_index anneau partie u_ref")
    out = sub.createNode("null", "SORTIE_MAILLAGES")
    out.setInput(0, nett)
    O.sortie(sub, out, 0, "sortie_maillages")
    out.setDisplayFlag(True)
    O.ranger(sub)
    return out


AIDE = ("Sol du site : chaque surface de la description triangulée (Triangulate 2D contraint, raffiné) et posée sur le "
        "modèle de nivellement unique (TQ-SOL-013) sans lissage des marches de bordure ; sol sous bordure au pied de "
        "face ; BEV en dalles 3D le long de l'arc ; tuiles de 50 m.")
DETAILS = """== Entrées ==

1. Surfaces : polygones (anneau 0 = extérieur, anneau >= 1 = trou, même id) avec id, classe, materiau_id,
   region_niveau, bords (dict[] : bordure, cote), bordure (emprises), ilots ; ponctuels_sol type bev (ancrage).
2. Nivellement (HeightField de pj::lire_description).
3. Contexte : entités (bordures pour le sol sous bordure et les BEV).

== Sortie ==

Maillages Y haut : materiau_id, pj_couche = PJ_Sol, pj_entite = T_<i>_<j> (tuile) ou id de BEV, pj_maillage, N (cusp
30°), uv = (x, y) locaux en mètres.

Règles : TQ-SOL-002, TQ-SOL-003, TQ-SOL-008, TQ-SOL-010, TQ-SOL-013, TQ-BOR-007, GA-BEV-002/003/004, VAL-SOL-009 (E8,
E9). Conventions : recon/pcg/houdini/hda/README_HDA.md."""


def construire(dossier=ICI):
    sub = O.sous_reseau("pj_" + NOM)
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres()))
    reseau(sub)
    return O.creer_hda(sub, NOM, "PJ Sol (surfaces sur le nivellement)", parametres(), dossier, entrees=(1, 3),
                       sorties=1, aide=AIDE, details_aide=DETAILS, icone="SOP_triangulate2d",
                       etiquettes_entrees=("Surfaces (polygones)", "Nivellement (HeightField)", "Contexte (entités)"),
                       etiquettes_sorties=("Maillages",))


def essai(emprise="pilote", boite=None):
    import time
    O.installer_tout()
    obj = hou.node("/obj/_construction") or hou.node("/obj").createNode("geo", "_construction")
    lire = obj.createNode("pj::lire_description::1.0", "lire")
    lire.parm("emprise").set(emprise if boite is None else "boite")
    if boite is not None:
        lire.parmTuple("boite_min").set(boite[:2])
        lire.parmTuple("boite_max").set(boite[2:])
    bl = obj.createNode("blast", "b_sol")
    bl.setInput(0, lire)
    bl.parm("group").set("b_sol")
    bl.parm("negate").set(1)
    sub = O.sous_reseau("essai_sol")
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres()))
    sub.setInput(0, bl)
    sub.setInput(1, lire, 1)
    sub.setInput(2, lire, 0)
    out = reseau(sub)
    t = time.time()
    try:
        out.cook(force=True)
    except hou.OperationFailed as e:
        print("ECHEC", str(e)[:1500])
        for c in sub.allSubChildren():
            if c.errors():
                print("  ", c.path(), str(c.errors())[:800])
        raise
    print(f"cuisson {time.time() - t:.1f} s, {len(out.geometry().prims())} primitives")
    return sub


if __name__ == "__main__":
    if "--essai" in sys.argv:
        a = sys.argv[sys.argv.index("--essai") + 1:]
        if a and a[0] == "boite":
            essai(boite=[float(x) for x in a[1:5]])
        else:
            essai(a[0] if a else "pilote")
    else:
        print(construire())
