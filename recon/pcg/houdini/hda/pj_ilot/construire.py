"""Construit l'HDA pj::ilot::1.0 (remplissages d'îlots sous la ceinture de bordures, éclats de BRF et de concassé) ;
hython Houdini 22.

    hython recon/pcg/houdini/hda/pj_ilot/construire.py                 # construit et enregistre pj_ilot.hdalc/
    hython recon/pcg/houdini/hda/pj_ilot/construire.py --essai [site|pilote]

Réseau (README_HDA.md § « pj::ilot ») :
  contexte (surfaces) -> surfaces_ilots (VEX : surfaces de chaque îlot, remplissage, retrait, bombement) ; îlots sans
  surface décrite -> PolyExpand2D (retrait sous la ceinture) ; -> aplatir -> Resample par arête -> boucle compilée
  Triangulate 2D (pj_sol/reseau_sol.py) -> altitude_ilot (VEX : tête de ceinture − retrait + bombement, TQ-SOL-013 (7),
  GA-ARB-003) -> Fuse -> Normal -> UV -> export ;
  couverture dense (option) : Scatter (densité par matériau) -> couverture (VEX) -> Copy to Points des prototypes ;
  éclats épars (débordement sur la chaussée) : eclats_debordement (VEX) -> sortie 2 (points d'instances) ;
  prototypes : Box / Sphere -> Copy to Points par variante -> prototypes_eclats (VEX) -> Normal -> sortie 3.
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
HDA = ICI.parent
sys.path.insert(0, str(HDA / "commun"))
sys.path.insert(0, str(HDA / "pj_sol"))
import pj_hda_outils as O  # noqa: E402
import reseau_sol as R  # noqa: E402

NOM = "ilot"
VEX = ICI / "vex"


def corps(section):
    return R.corps("ilot.vfl", section, VEX)


def parametres():
    T = hou
    F = T.FloatParmTemplate
    tg = T.ToggleParmTemplate
    rem = [
        T.MenuParmTemplate("mode_altitude", "Altitude du remplissage", menu_items=("ceinture", "nivellement"),
                           menu_labels=("Tête de ceinture − retrait + bombement (TQ-SOL-013 (7))",
                                        "Modèle de nivellement (pj_niv_z)"), default_value=0),
        F("dome_m", "Distance du bombement (m)", 1, default_value=(0.8,), min=0.05, max=5.0,
          help="Le bombement atteint sa hauteur à cette distance de l'arête arrière de la ceinture."),
        F("base_ceinture", "Largeur de la ceinture (m)", 1, default_value=(0.15,), min=0.0, max=0.5,
          help="Distance de l'arête avant à l'arête arrière des bordures de ceinture (T2 : 0,15 m)."),
        F("trou_min_m2", "Trous comblés sous (m²)", 1, default_value=(2.0,), min=0.0, max=20.0,
          help="Trous (anneau ≥ 1) plus petits, sans surface décrite dedans (mâts portés) : comblés par le remplissage."),
        F("retrait_defaut", "Retrait du polygone d'îlot (m)", 1, default_value=(0.15,), min=0.0, max=1.0,
          help="Îlots sans surface décrite : polygone réduit de la largeur de la ceinture (PolyExpand2D)."),
        F("pas_bords", "Pas des bords (m)", 1, default_value=(0.25,), min=0.05, max=5.0),
        F("arete_chaussee", "Arête cible revêtu (m)", 1, default_value=(0.25,), min=0.05, max=5.0),
        F("arete_trottoir", "Arête cible trottoir (m)", 1, default_value=(0.25,), min=0.05, max=5.0),
        F("arete_parking", "Arête cible parking (m)", 1, default_value=(0.25,), min=0.05, max=5.0),
        F("arete_vert", "Arête cible remplissage (m)", 1, default_value=(0.2,), min=0.05, max=5.0,
          help="TQ-SOL-002 : 0,25 m sur les îlots (bombement lisse)."),
        F("angle_min", "Angle minimal (°)", 1, default_value=(25.0,), min=0.0, max=33.0),
        F("souder_mm", "Soudure des coutures (mm)", 1, default_value=(0.1,), min=0.0, max=5.0),
    ]
    ecl = [
        tg("couverture_dense", "Couverture dense d'éclats", default_value=False,
           help="BRF 1 800 /m², concassé 3 000 /m² (aperçu Karma ; dans UE, déplacement Nanite du matériau)."),
        F("densite_facteur", "Facteur de densité de la couverture", 1, default_value=(1.0,), min=0.0, max=2.0),
        F("debordement_facteur", "Facteur des éclats épars", 1, default_value=(1.0,), min=0.0, max=5.0,
          help="Éclats devant la ceinture, sur la chaussée (remplissage.debordement)."),
    ]
    sor = [T.StringParmTemplate("couche", "Couche USD", 1, default_value=("PJ_Ilots",)),
           T.StringParmTemplate("couche_bibliotheque", "Couche USD des prototypes", 1, default_value=("PJ_Lib_Ilots",)),
           T.StringParmTemplate("pivot_prototypes", "Pivot des prototypes", 1, default_value=(
               "centre de l'éclat ; taille unitaire (plus grande dimension 1), échelle = taille en m ; Z haut",)),
           T.StringParmTemplate("sens_cd", "Sens de cd", 1, default_value=("[teinte, 0, 0]",))]
    return [T.FolderParmTemplate("f_rem", "Remplissage", parm_templates=rem, folder_type=T.folderType.Tabs),
            T.FolderParmTemplate("f_ecl", "Éclats", parm_templates=ecl, folder_type=T.folderType.Tabs),
            T.FolderParmTemplate("f_sor", "Sorties", parm_templates=sor, folder_type=T.folderType.Tabs)]


def reseau(sub):
    blast = R.blast
    ent = sub.createNode("null", "ENTREE_ILOTS")
    ent.setInput(0, sub.indirectInputs()[0])
    niv = sub.createNode("null", "ENTREE_NIVEAU")
    niv.setInput(0, sub.indirectInputs()[1])
    ctx = sub.createNode("null", "ENTREE_CONTEXTE")
    ctx.setInput(0, sub.indirectInputs()[2])
    ilots = O.wrangle(sub, "ilots", r"""
// ilots : polygones fermés de la famille ilots (ou sans famille : polygones tracés dans UE).
string fam = hasprimattrib(0, "famille") ? s@famille : "ilots";
if (fam != "ilots" || !primintrinsic(0, "closed", @primnum)) removeprim(0, @primnum, 1);
""", "primitive", ent)
    surf = blast(sub, "surfaces", ctx, "@famille=surfaces")
    bords = blast(sub, "bordures", ctx, "@famille=bordures")
    si = O.wrangle(sub, "surfaces_ilots", corps("surfaces_ilots"), "primitive", surf, entrees=(ilots,))
    # îlots sans surface décrite (tracés dans UE) : polygone réduit de la largeur de la ceinture
    sans = O.wrangle(sub, "ilots_sans_surface", r"""
// ilots_sans_surface : îlots dont aucune surface n'est décrite dans le contexte (entrée 1).
if (findattribval(1, "prim", "ilot", s@id) >= 0) removeprim(0, @primnum, 1);
else @P.y = 0;
""", "primitive", ilots, entrees=(si,))
    apl0 = O.wrangle(sub, "aplatir_ilots", "@P.y = 0;", "point", sans)
    pe = sub.createNode("polyexpand2d", "retrait_ceinture")
    pe.setInput(0, apl0)
    for p, v in (("planepossrc", 1), ("planenormalx", 0), ("planenormaly", 1), ("planenormalz", 0), ("output", 1),
                 ("outputinside", 1), ("outputoutside", 0)):
        pe.parm(p).set(v)
    pe.parm("offset").setExpression('ch("../retrait_defaut")')
    rep = O.wrangle(sub, "attributs_repli", r"""
// attributs_repli : remplissage de l'îlot sur le polygone réduit (entrée 1 : îlots).
int k = findattribval(1, "prim", "id", s@id);
if (k < 0) k = 0;
dict r = prim(1, "remplissage", k);
string m = "gazon_tondu";
if (isvalidindex(r, "materiau_id")) { string x = r["materiau_id"]; m = x; }
s@ilot = prim(1, "id", k);
s@classe = "ilot";
s@materiau_id = m;
s@remplissage_mat = m;
i@rempli = 1;
f@retrait = isvalidindex(r, "retrait_sous_bordure_m") ? 0.04 : 0.04;
if (isvalidindex(r, "retrait_sous_bordure_m")) { float x = r["retrait_sous_bordure_m"]; f@retrait = x; }
f@bombement = 0.02;
if (isvalidindex(r, "bombement_m")) { float x = r["bombement_m"]; f@bombement = x; }
i@region_niveau = prim(1, "region_niveau", k);
i@anneau = 0;
s@id = s@ilot + "_remplissage";
""", "primitive", pe, entrees=(ilots,))
    fus0 = sub.createNode("merge", "toutes_surfaces")
    fus0.setInput(0, si)
    fus0.setInput(1, rep)
    apl = O.wrangle(sub, "aplatir", R.corps("sol.vfl", "aplatir"), "point", fus0)
    den = sub.createNode("resample", "densifier")
    den.setInput(0, apl)
    for p, v in (("edge", 1), ("dolength", 1), ("allequal", 1)):
        den.parm(p).set(v)
    den.parm("length").setExpression('ch("../pas_bords")')
    ext = blast(sub, "anneaux_exterieurs", den, "@anneau=0")
    # petits trous sans surface décrite dedans (emprise de mât porté par l'îlot, « bâtiment » v1 : trou carré noir de
    # 0,21 m dans I-0332, revue réalisme du 11/10/2026) : comblés par le remplissage (le mât est posé par Unreal)
    ext_tous = blast(sub, "anneaux_exterieurs_tous", surf, "@anneau=0")
    ptr = O.wrangle(sub, "petits_trous", R.corps("sol.vfl", "petits_trous"), "primitive", den, entrees=(ext_tous,))
    idx = O.wrangle(sub, "indexer", R.corps("sol.vfl", "indexer"), "primitive", ptr, entrees=(ext,))
    ech = O.wrangle(sub, "echelle", R.corps("sol.vfl", "echelle"), "point", idx)
    inv = R.boucle_triangulation(sub, ech)
    alt = O.wrangle(sub, "altitude_ilot", R.entetes(courbe=True) + corps("altitude_ilot"), "point", inv,
                    entrees=(ilots, bords, niv))
    fu = sub.createNode("fuse::2.0", "souder_coutures")
    fu.setInput(0, alt)
    fu.parm("tol3d").setExpression('ch("../souder_mm") / 1000')
    nm = sub.createNode("normal", "normales")
    nm.setInput(0, fu)
    nm.parm("type").set(1)
    nm.parm("cuspangle").set(30.0)
    uv = O.wrangle(sub, "uv", "v@uv = set(@P.x, -@P.z, 0);", "sommet", nm)
    exp = O.wrangle(sub, "export", r"""
// export : couche PJ_Ilots, component = îlot, Mesh par materiau_id (README_HDA.md § 4).
s@pj_couche = chs("../couche");
s@pj_entite = s@ilot;
s@pj_maillage = s@materiau_id;
""", "primitive", uv)
    remplissage = sub.createNode("null", "REMPLISSAGES")
    remplissage.setInput(0, exp)
    # ---- prototypes d'éclats
    var = O.wrangle(sub, "variantes", r"""
// variantes : un point par prototype (12 copeaux de BRF, 8 pierres de concassé), espacés de 2 m.
for (int k = 0; k < 20; k++) {
    int brf = k < 12;
    int v = brf ? k : k - 12;
    vector o = set(2.0 * k, 0, 0);
    int p = addpoint(0, o);
    setpointattrib(0, "variante", p, v + (brf ? 0 : 100));
    setpointattrib(0, "famille_eclat", p, brf ? "brf" : "gravier");
    setpointattrib(0, "origine", p, o);
    string nom = sprintf("eclat_%s_v%02d", brf ? "brf" : "gravier", v);
    setpointattrib(0, "name", p, nom);
    setpointattrib(0, "asset", p, nom);
    setpointattrib(0, "materiau_id", p, brf ? "eclat_brf" : "eclat_gravier");
}
""", "detail", None)
    copeau = sub.createNode("box", "copeau")
    # type « polymesh » : faces fermées ; le type « poly » avec divisions donne des polygones ouverts, exportés en
    # BasisCurves (prototypes/ilots.usda : 12 courbes au lieu de maillages, revue conformité 11/10/2026)
    copeau.parm("type").set("polymesh")
    for p, v in (("sizex", 1.0), ("sizey", 0.06), ("sizez", 0.32), ("dodivs", 1), ("divsx", 6), ("divsy", 2),
                 ("divsz", 3)):
        copeau.parm(p).set(v)
    pierre = sub.createNode("sphere", "pierre")
    pierre.parm("type").set(1)
    pierre.parm("freq").set(2)
    vb = blast(sub, "variantes_brf", var, "@famille_eclat=brf", points=True)
    vg = blast(sub, "variantes_gravier", var, "@famille_eclat=gravier", points=True)
    cps = []
    for nom_c, forme, cible in (("copier_copeaux", copeau, vb), ("copier_pierres", pierre, vg)):
        c = sub.createNode("copytopoints::2.0", nom_c)
        c.setInput(0, forme)
        c.setInput(1, cible)
        c.parm("targetattribs").set(2)
        c.parm("applyto1").set(0)
        c.parm("applyattribs1").set("variante famille_eclat origine")
        c.parm("applyto2").set(2)
        c.parm("applyattribs2").set("name asset materiau_id")
        cps.append(c)
    m = sub.createNode("merge", "formes")
    m.setInput(0, cps[0])
    m.setInput(1, cps[1])
    pe2 = O.wrangle(sub, "prototypes_eclats", corps("prototypes_eclats"), "point", m)
    nm2 = sub.createNode("normal", "normales_eclats")
    nm2.setInput(0, pe2)
    nm2.parm("type").set(1)
    nm2.parm("cuspangle").set(35.0)
    uv2 = O.wrangle(sub, "uv_eclats", r"""
// uv_eclats (sommet) : projection sur le plan dominant (unité = taille de l'éclat).
vector n = prim_normal(0, @primnum, {0.5, 0.5, 0});
vector P = @P - point(0, "origine", @ptnum);
if (abs(n.y) >= max(abs(n.x), abs(n.z))) v@uv = set(P.x, P.z, 0);
else if (abs(n.x) >= abs(n.z)) v@uv = set(P.z, P.y, 0);
else v@uv = set(P.x, P.y, 0);
""", "sommet", nm2)
    rec0 = O.wrangle(sub, "recentrer_eclats", "@P -= v@origine;", "point", uv2)
    rec = O.wrangle(sub, "attributs_prototypes", r"""
// attributs_prototypes : component USD par prototype (pj_entite = asset), couche de bibliothèque.
s@pj_couche = chs("../couche_bibliotheque");
s@pj_entite = s@asset;
s@pj_maillage = s@materiau_id;
""", "primitive", rec0)
    protos = sub.createNode("null", "PROTOTYPES")
    protos.setInput(0, rec)
    # ---- couverture dense (option)
    fill = O.wrangle(sub, "densites", r"""
// densites (primitive) : éclats par m² selon le remplissage (ex-pj_ilot ECLATS : BRF 1 800, concassé 3 000, galets
// 1 200) ; 0 ailleurs (gazon, revêtus).
string m = s@materiau_id;
float d = 0;
if (startswith(m, "brf")) d = 1800;
else if (startswith(m, "gravier") || startswith(m, "gravillons")) d = 3000;
else if (startswith(m, "galets")) d = 1200;
f@density = d * chf("../densite_facteur");
if (d <= 0) removeprim(0, @primnum, 1);
""", "primitive", remplissage)
    sc = sub.createNode("scatter::2.0", "semer")
    sc.setInput(0, fill)
    for p, v in (("generateby", 0), ("usedensityattrib", 1), ("densityattrib", "density"), ("densityscale", 1.0),
                 ("forcetotal", 0), ("relaxpoints", 0), ("primattribs", "materiau_id ilot"), ("useemergencylimit", 1),
                 ("emergencylimit", 5000000), ("seed", 7.0)):
        sc.parm(p).set(v)
    cov = O.wrangle(sub, "couverture", corps("couverture"), "point", sc)
    cpc = sub.createNode("copytopoints::2.0", "copier_couverture")
    cpc.setInput(0, protos)
    cpc.setInput(1, cov)
    cpc.parm("useidattrib").set(1)
    cpc.parm("idattrib").set("asset")
    cpc.parm("pack").set(0)                   # copies directes (pas d'instances empaquetées à dépaqueter)
    cpc.parm("targetattribs").set(1)
    cpc.parm("applyto1").set(2)
    cpc.parm("applyattribs1").set("ilot graine materiau_id")
    upc = cpc
    cexp = O.wrangle(sub, "export_couverture", r"""
s@pj_couche = chs("../couche");
s@pj_entite = s@ilot;
s@pj_maillage = s@materiau_id;
""", "primitive", upc)
    sw = sub.createNode("switch", "si_couverture")
    sw.setInput(0, sub.createNode("null", "VIDE"))
    sw.setInput(1, cexp)
    sw.parm("input").setExpression('ch("../couverture_dense")')
    fus = sub.createNode("merge", "fusion")
    fus.setInput(0, remplissage)
    fus.setInput(1, sw)
    nett = sub.createNode("attribdelete", "attributs_internes")
    nett.setInput(0, fus)
    nett.parm("ptdel").set("origine variante famille_eclat")
    nett.parm("primdel").set("arete_cible surf_index anneau partie density")
    out = sub.createNode("null", "SORTIE_MAILLAGES")
    out.setInput(0, nett)
    # ---- éclats épars (sortie 2)
    deb = O.wrangle(sub, "eclats_debordement", R.entetes(courbe=True) + corps("eclats_debordement"), "detail",
                    ilots, entrees=(bords,))
    pts = sub.createNode("null", "POINTS_INSTANCES")
    pts.setInput(0, deb)
    O.sortie(sub, out, 0, "sortie_maillages")
    O.sortie(sub, pts, 1, "sortie_points")
    O.sortie(sub, protos, 2, "sortie_prototypes")
    out.setDisplayFlag(True)
    O.ranger(sub)
    return out, pts, protos


AIDE = ("Remplissages d'îlots sous la ceinture de bordures (3 à 5 cm sous la tête, bombés ; GA-ARB-003, TQ-SOL-013 (7)) "
        "triangulés sur les surfaces de l'îlot, éclats épars de BRF et de concassé débordant sur la chaussée, couverture "
        "dense en option, prototypes d'éclats.")
DETAILS = """== Entrées ==

1. Îlots : polygones avec id, remplissage (dict : materiau_id, retrait_sous_bordure_m, bombement_m, debordement),
   ceinture (string[] : bordures), surface (string[]), region_niveau.
2. Nivellement (HeightField) : mode « nivellement ».
3. Contexte : surfaces (géométrie des remplissages) et bordures (têtes de la ceinture, niv_s, niv_z_tete, niv_z_pied).

== Sorties ==

1. Maillages Y haut : remplissage par îlot (pj_couche = PJ_Ilots, pj_entite = îlot, materiau_id, N, uv en mètres),
   plus la couverture dense si l'option est active.
2. Points d'instances (éclats épars) : asset eclat_<brf|gravier>_vNN, unreal_instance
   (/Game/PJ/Lib/Ilots/SM_<asset>), orient, scale, graine, cd, x.
3. Prototypes d'éclats (taille unitaire, centrés).

Règles : GA-ARB-003, TQ-SOL-013 (7), TQ-SOL-002, GA-ILO-003. Conventions : recon/pcg/houdini/hda/README_HDA.md."""


def construire(dossier=ICI):
    sub = O.sous_reseau("pj_" + NOM)
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres()))
    reseau(sub)
    return O.creer_hda(sub, NOM, "PJ Îlots (remplissages et éclats)", parametres(), dossier, entrees=(1, 3), sorties=3,
                       aide=AIDE, details_aide=DETAILS, icone="SOP_scatter",
                       etiquettes_entrees=("Îlots (polygones)", "Nivellement (HeightField)", "Contexte (entités)"),
                       etiquettes_sorties=("Maillages", "Points d'instances (éclats épars)", "Prototypes d'éclats"))


def essai(emprise="site"):
    import time
    O.installer_tout()
    obj = hou.node("/obj/_construction") or hou.node("/obj").createNode("geo", "_construction")
    lire = obj.createNode("pj::lire_description::1.0", "lire")
    lire.parm("emprise").set(emprise)
    bl = obj.createNode("blast", "b_ilots")
    bl.setInput(0, lire)
    bl.parm("group").set("b_ilots")
    bl.parm("negate").set(1)
    sub = O.sous_reseau("essai_ilot")
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres()))
    sub.setInput(0, bl)
    sub.setInput(1, lire, 1)
    sub.setInput(2, lire, 0)
    out, pts, protos = reseau(sub)
    t = time.time()
    for n in (protos, pts, out):
        try:
            n.cook(force=True)
        except hou.OperationFailed as e:
            print("ECHEC", n.path(), str(e)[:1500])
            for c in sub.allSubChildren():
                if c.errors():
                    print("  ", c.path(), str(c.errors())[:800])
            raise
    print(f"cuisson {time.time() - t:.1f} s : {len(out.geometry().prims())} primitives, {len(pts.geometry().points())} "
          f"éclats épars, {len(protos.geometry().prims())} faces de prototypes")
    return sub


if __name__ == "__main__":
    if "--essai" in sys.argv:
        a = sys.argv[sys.argv.index("--essai") + 1:]
        essai(a[0] if a else "site")
    else:
        print(construire())
