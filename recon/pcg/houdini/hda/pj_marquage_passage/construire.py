"""Construit l'HDA pj::passage_pieton::1.0 (branche passages : zébras et traversées cyclables MP-*) ; hython 22.

    hython recon/pcg/houdini/hda/pj_marquage_passage/construire.py

Réseau (README_HDA.md § 7) :
    normaliser (VEX : paramètres MQ-PP-003/004, MQ-CHR-001, valeurs déduites si absentes)
      -> bandes (VEX : rectangles 0,50 x longueur au pas de l'axe, hors coupures ; tuiles des files cyclables posées
         depuis le gabarit lu par pj::gabarits_iisr) -> attributs (Attribute Copy)
    decoupes (VEX 64 bits : polygones decoupes[].polygone_l93 de props) -> prismes (PolyExtrude)
    pour chaque passage : Boolean (bandes moins prismes de dégagement) -> solide (pj::marquage_solide)
Entrées : 1 = passages (axe A -> B des centres de bandes ; une partie par file cyclable), 2 = nivellement.
Sortie : maillages Y haut, un component par passage (pj_entite = id).
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "pj_marquage_commun"))
import pj_marquage_outils as M  # noqa: E402

O = M.O
T = hou
NOM = "passage_pieton"

VEX_NORMALISER = r"""
// Paramètres d'un passage (description ou axe tracé à la main ; A -> B = centres des bandes extrêmes) :
//   zébra : bande 0,50 m (MQ-PP-004) ; longueur de bande : longueur_bande_m, sinon 3,00 m (MQ-PP-003, défaut déduit
//   du site) ; pas : pas_axe_m, sinon bande + intervalle_m, sinon MQ-PP-004 (g le plus proche de 0,50 m) ;
//   bandes parallèles à l'axe de la chaussée (MQ-PP-005) : cap_bandes_deg, sinon perpendiculaires à A -> B ;
//   nombre : nb_emplacements, sinon arrondi de |AB| / pas + 1 ; coupures (indices, MQ-PP-006 refuge) ;
//   traversée cyclable : file = files[partie] (nb, pas_m, absents, cap_deg, couleur, gabarit ou tuile_m ; MQ-CHR-001).
int pts[] = primpoints(0, @primnum);
vector a3 = point(0, "P", pts[0]);
vector b3 = point(0, "P", pts[len(pts) - 1]);
vector2 A = pj_m_xy(a3);
vector2 B = pj_m_xy(b3);
v@pj_A = set(A.x, A.y, 0);
v@pj_B = set(B.x, B.y, 0);
float lax = length(B - A);
vector2 ax = lax > 1e-6 ? (B - A) / lax : set(1.0, 0.0);
string ty = hasprimattrib(0, "type") ? s@type : "";
i@pj_cyclable = (ty == "traversee_cyclable") ? 1 : 0;
if (s@pj_entite == "") s@pj_entite = s@id;
if (!i@pj_cyclable) {
    float bande = hasprimattrib(0, "largeur_bande_m") ? f@largeur_bande_m : 0.0;
    if (bande <= 0) bande = ch("../bande_defaut");
    float lg = hasprimattrib(0, "longueur_bande_m") ? f@longueur_bande_m : 0.0;
    if (lg <= 0) lg = ch("../longueur_defaut");
    float pas = hasprimattrib(0, "pas_axe_m") ? f@pas_axe_m : 0.0;
    if (pas <= 0 && hasprimattrib(0, "intervalle_m") && f@intervalle_m > 0) pas = bande + f@intervalle_m;
    if (pas <= 0) {
        // MQ-PP-004 : W = 0,50 n + g (n + 1) avec W = |AB| + bande + 2 g ; n = floor(W - 0,5) avec g = 0,50
        float W = lax + bande + 2 * 0.5;
        int n = max(1, int(floor(W - 0.5)));
        float g = (W - bande * n) / (n + 1);
        pas = bande + clamp(g, 0.5, 0.8);
    }
    int nb = hasprimattrib(0, "nb_emplacements") ? i@nb_emplacements : 0;
    if (nb <= 0 && hasprimattrib(0, "nb_bandes")) nb = i@nb_bandes;
    if (nb <= 0) nb = int(rint(lax / pas)) + 1;
    float cap = hasprimattrib(0, "cap_bandes_deg") ? f@cap_bandes_deg : -1000.0;
    if (cap < -999 || (cap == 0 && !hasprimattrib(0, "nb_bandes"))) cap = degrees(atan2(ax.y, ax.x)) + 90.0;
    f@pj_bande = bande;
    f@pj_longueur = lg;
    f@pj_pas = pas;
    i@pj_nb = nb;
    f@pj_cap = cap;
}
"""

VEX_BANDES = r"""
// Bandes (zébra) et tuiles (traversée cyclable), polygones fermés dans le plan, une partie par bande ou tuile.
int src = @primnum;
vector A3 = v@pj_A;
vector B3 = v@pj_B;
vector2 A = set(A3.x, A3.y);
vector2 B = set(B3.x, B3.y);
float lax = length(B - A);
vector2 ax = lax > 1e-6 ? (B - A) / lax : set(1.0, 0.0);
int rang = 0;
if (!i@pj_cyclable) {
    float cp[];
    if (hasprimattrib(0, "coupures")) cp = f[]@coupures;
    vector2 u = pj_m_dir(f@pj_cap);
    for (int k = 0; k < i@pj_nb; k++) {
        if (find(cp, float(k)) >= 0) continue;
        vector2 c = A + ax * (k * f@pj_pas);
        vector2 r[] = pj_m_rectangle(c, u, f@pj_longueur, f@pj_bande);
        int np = pj_m_poly(0, r);
        setprimattrib(0, "pj_source", np, src);
        setprimattrib(0, "partie", np, rang);
        setprimattrib(0, "anneau", np, 0);
        setprimattrib(0, "pj_rang", np, k);
        rang++;
    }
} else {
    dict fls[];
    if (hasprimattrib(0, "files")) fls = d[]@files;
    int ip = hasprimattrib(0, "partie") ? i@partie : 0;
    dict fl;
    if (ip < len(fls)) fl = fls[ip];
    int nb = 0;
    if (isvalidindex(fl, "nb")) nb = fl["nb"];
    float pas = 0.6;                                                            // MQ-CHR-001 : pas 0,60
    if (isvalidindex(fl, "pas_m")) pas = fl["pas_m"];
    float cap = degrees(atan2(ax.y, ax.x));
    if (isvalidindex(fl, "cap_deg")) cap = fl["cap_deg"];
    float abs_[];
    if (isvalidindex(fl, "absents")) abs_ = fl["absents"];
    if (nb <= 0) nb = int(rint(lax / pas)) + 1;
    string gab = "";
    if (isvalidindex(fl, "gabarit")) gab = fl["gabarit"];
    float tx = 0.0, ty = 0.0;
    if (isvalidindex(fl, "tuile_m")) { dict tm = fl["tuile_m"]; tx = tm["perp_file"]; ty = tm["le_long_file"]; }
    if (gab == "" && tx <= 0) gab = chs("../gabarit_tuile_defaut");
    vector2 d = pj_m_dir(cap);
    string coul = s@couleur;
    if (isvalidindex(fl, "couleur")) coul = fl["couleur"];
    for (int k = 0; k < nb; k++) {
        if (find(abs_, float(k)) >= 0) continue;
        vector2 c = A + d * (pas * k);
        if (gab != "") {
            // gabarit IISR / site (pj::gabarits_iisr, entrée 2) posé : origine = centre de la tuile, y le long de la file
            int ng = nprimitives(1);
            for (int g = 0; g < ng; g++) {
                if (prim(1, "gabarit", g) != gab) continue;
                int gp[] = primpoints(1, g);
                vector2 q[];
                foreach (int p; gp) {
                    vector P = point(1, "P", p);
                    append(q, pj_m_poser(set(P.x, -P.z), c, cap, 1.0));
                }
                int np = pj_m_poly(0, q);
                setprimattrib(0, "pj_source", np, src);
                int gpart = prim(1, "partie", g);
                int gann = prim(1, "anneau", g);
                setprimattrib(0, "partie", np, rang * 16 + gpart);
                setprimattrib(0, "anneau", np, gann);
                setprimattrib(0, "pj_rang", np, k);
                setprimattrib(0, "pj_couleur_file", np, coul);
            }
        } else {
            vector2 r[];
            append(r, pj_m_poser(set(-tx / 2, -ty / 2), c, cap, 1.0));
            append(r, pj_m_poser(set(tx / 2, -ty / 2), c, cap, 1.0));
            append(r, pj_m_poser(set(tx / 2, ty / 2), c, cap, 1.0));
            append(r, pj_m_poser(set(-tx / 2, ty / 2), c, cap, 1.0));
            int np = pj_m_poly(0, r);
            setprimattrib(0, "pj_source", np, src);
            setprimattrib(0, "partie", np, rang * 16);
            setprimattrib(0, "anneau", np, 0);
            setprimattrib(0, "pj_rang", np, k);
            setprimattrib(0, "pj_couleur_file", np, coul);
        }
        rang++;
    }
}
removeprim(0, @primnum, 1);
"""

VEX_COULEUR = r"""
// Couleur de la file (traversées cyclables : jaune Chronovélo MQ-CHR-001 ou blanc) -> matériau de peinture
if (s@pj_couleur_file != "" && s@pj_couleur_file != s@couleur) {
    s@materiau_id = re_replace("PJ_Peinture_[a-z]+_", "PJ_Peinture_" + s@pj_couleur_file + "_", s@materiau_id);
    s@couleur = s@pj_couleur_file;
}
"""

VEX_DECOUPES = r"""
// Dégagements décrits (decoupes[].polygone_l93 : 2u des bordures, marque voisine ; MQ-DET-010) lus dans props
// (JSON, Lambert-93 en float64), ramenés au repère local ; une primitive fermée par découpe (groupe decoupe).
if (!hasprimattrib(0, "props") || (hasprimattrib(0, "partie") && i@partie > 0)) { removeprim(0, @primnum, 1); return; }
string js = s@props;
if (find(js, "\"decoupes\"") < 0) { removeprim(0, @primnum, 1); return; }
dict d = json_loads(js, 0);
dict dec[] = d["decoupes"];
float OX = 917279.43, OY = 6460289.98;
foreach (dict c; dec) {
    string poly[] = c["polygone_l93"];
    vector2 q[];
    foreach (string s; poly) {
        float v[] = pj_m_nombres(s);
        if (len(v) >= 2) append(q, set(v[0] - OX, v[1] - OY));
    }
    if (len(q) < 3) continue;
    float a = 0;
    for (int i = 0; i < len(q); i++) { vector2 u = q[i]; vector2 w = q[(i + 1) % len(q)]; a += u.x * w.y - w.x * u.y; }
    if (a > 0) q = reverse(q);                    // horaire vu de dessus : normale +Y, extrusion vers le haut
    int np = pj_m_poly(0, q);
    setprimattrib(0, "id", np, s@id);
    setprimgroup(0, "decoupe", np, 1);
}
removeprim(0, @primnum, 1);
"""

VEX_FILTRE_DECOUPES = r"""
// prismes de dégagement du passage traité par cette itération (même id que la pièce, entrée 2)
if (s@id != prim(1, "id", 0)) removeprim(0, @primnum, 1);
"""


def parametres():
    geo = [
        T.FloatParmTemplate("bande_defaut", "Largeur de bande par défaut (m)", 1, default_value=(0.5,), min=0.1, max=1.0,
                            help="MQ-PP-004 : bandes de 0,50 m."),
        T.FloatParmTemplate("longueur_defaut", "Longueur de bande par défaut (m)", 1, default_value=(3.0,), min=1.0,
                            max=10.0, help="MQ-PP-003 : 3,00 m pour un passage déduit sur le site (2,50 m minimum)."),
        T.StringParmTemplate("gabarit_tuile_defaut", "Gabarit des tuiles cyclables par défaut", 1,
                             default_value=("CARRE_TRAVERSEE_CYCLABLE",),
                             help="Gabarit de marquages_geometrie.json pour une file sans gabarit ni tuile_m."),
        T.StringParmTemplate("spec", "Spécification des marquages", 1, default_value=(M.SPEC_DEFAUT,),
                             string_type=T.stringParmType.FileReference, file_type=T.fileType.Any),
        T.ToggleParmTemplate("decouper", "Appliquer les dégagements décrits (decoupes)", default_value=True,
                             help="Boolean : bandes moins les polygones decoupes de la description (props)."),
    ]
    sol = [
        T.FloatParmTemplate("epaisseur", "Épaisseur au-dessus du sol (m)", 1, default_value=(0.003,), min=0.0, max=0.02),
        T.FloatParmTemplate("enfouissement", "Enfouissement des flancs (m)", 1, default_value=(0.005,), min=0.0,
                            max=0.05),
        T.FloatParmTemplate("chanfrein", "Chanfrein des arêtes du dessus (m)", 1, default_value=(0.001,), min=0.0,
                            max=0.005),
        T.FloatParmTemplate("pas_maillage", "Pas du maillage de drapé (m)", 1, default_value=(0.25,), min=0.02,
                            max=5.0),
        T.ToggleParmTemplate("draper", "Draper sur le nivellement (entrée 2)", default_value=True),
        T.MenuParmTemplate("mode_region", "Région de drapé", menu_items=("piece", "attribut", "point"),
                           menu_labels=("Région majoritaire de la pièce", "Attribut pj_region",
                                        "Région de chaque sommet (suit les marches)"), default_value=0),
        T.FloatParmTemplate("seuil_franchissement", "Seuil de franchissement (m)", 1, default_value=(0.02,), min=0.0,
                            max=0.2),
        T.StringParmTemplate("couche", "Couche USD (pj_couche)", 1, default_value=(M.COUCHE,)),
        T.FloatParmTemplate("cusp", "Angle de rupture des normales (°)", 1, default_value=(30.0,), min=0.0, max=180.0),
    ]
    return [T.FolderParmTemplate("f_passage", "Passage", parm_templates=geo, folder_type=T.folderType.Tabs),
            T.FolderParmTemplate("f_solide", "Peinture (solide)", parm_templates=sol, folder_type=T.folderType.Tabs)]


def construire(dossier=ICI):
    L = M.charger(ICI.parent / "pj_marquage_ligne" / "construire.py", "construire_ligne")
    M.installer_commun()
    sub = O.sous_reseau("pj_" + NOM)
    sub.setParmTemplateGroup(T.ParmTemplateGroup(parametres()))
    ent, niv, sol_fab = sub.indirectInputs()[0], sub.indirectInputs()[1], sub.indirectInputs()[2]
    gab = sub.createNode("pj::gabarits_iisr::1.0", "gabarits")
    gab.parm("spec").set('`chs("../spec")`')
    gab.parm("filtre").set("PAVE_* CARRE_* DAMIER_*")
    nor = M.wrangle_m(sub, "normaliser", VEX_NORMALISER, "primitive", ent)
    bandes = M.wrangle_m(sub, "bandes", VEX_BANDES, "primitive", nor, entrees=(gab,))
    att = L.copie_attributs(sub, "attributs_bandes", bandes, nor, exclus="pj_source partie anneau pj_rang")
    coul = M.wrangle_m(sub, "couleur_file", VEX_COULEUR, "primitive", att, bibliotheques=False)
    dec = M.wrangle_m(sub, "decoupes", VEX_DECOUPES, "primitive", ent, precision64=True)
    pri = sub.createNode("polyextrude::2.0", "prismes")
    pri.setInput(0, dec)
    for p, v in (("splittype", "components"), ("dist", 2.0), ("outputback", 1), ("outputfront", 1),
                 ("outputside", 1)):
        pri.parm(p).set(v)
    pri_b = sub.createNode("xform", "prismes_centres")
    pri_b.setInput(0, pri)
    pri_b.parm("ty").set(-1.0)

    def corps(debut):
        filt = M.wrangle_m(sub, "decoupes_du_passage", VEX_FILTRE_DECOUPES, "primitive", pri_b, entrees=(debut,),
                           bibliotheques=False)
        bo = sub.createNode("boolean::2.0", "degager")
        bo.setInput(0, debut)
        bo.setInput(1, filt)
        bo.parm("asurface").set("surface")
        bo.parm("booleanop").set("subtract")
        sw = M.interrupteur(sub, "choix_decoupe", (debut, bo),
                            'ch("../decouper") && nprims("../decoupes_du_passage") > 0')
        return sw

    _, fin = M.boucle_par_attribut(sub, coul, "pj_entite", corps, nom="par_passage")
    sol = sub.createNode("pj::marquage_solide::1.0", "solide")
    sol.setInput(0, fin)
    sol.setInput(1, niv)
    sol.setInput(2, sol_fab)               # sol fabriqué (pj::sol) : drapé sur le sol maillé (TQ-MQG-005)
    L.relier_solide(sol)
    sol.parm("pas_maillage").setExpression('ch("../pas_maillage")')
    out = sub.createNode("null", "MAILLAGES")
    out.setInput(0, sol)
    O.sortie(sub, out, 0, "sortie")
    O.ranger(sub)
    return O.creer_hda(sub, NOM, "PJ Marquage : passages piétons et traversées cyclables", parametres(), dossier,
                       entrees=(1, 3), sorties=1, icone="SOP_grid",
                       aide="Zébras (bandes de 0,50 m au pas de l'axe, parallèles à l'axe de la chaussée, égales, hors "
                            "coupures) et traversées cyclables (tuiles du gabarit posées le long de chaque file), "
                            "dégagements décrits retirés par Boolean, puis peinture extrudée et drapée "
                            "(pj::marquage_solide).",
                       details_aide="== Entrées ==\n\n1. Passages : axe A -> B (centres des bandes extrêmes), attributs "
                                    "largeur_bande_m, longueur_bande_m, pas_axe_m, cap_bandes_deg, nb_emplacements, "
                                    "coupures ; traversées : files (dict[]) et une partie par file.\n2. Nivellement.\n\n"
                                    "Règles : MQ-PP-003, MQ-PP-004, MQ-PP-005, MQ-PP-006, MQ-CHR-001, MQ-DET-010. "
                                    "Contrat : README_HDA.md § 7.",
                       etiquettes_entrees=("Passages (axes)", "Nivellement (HeightField)",
                                           "Sol fabriqué (facultatif)"),
                       etiquettes_sorties=("Maillages (Y haut)",))


if __name__ == "__main__":
    print(construire())
