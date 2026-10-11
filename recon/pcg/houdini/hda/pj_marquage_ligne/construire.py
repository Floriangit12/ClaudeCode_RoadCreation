"""Construit l'HDA pj::marquage_ligne::1.0 (branche marquages_lignes : lignes ML-* et transversales MT-*) ; hython 22.

    hython recon/pcg/houdini/hda/pj_marquage_ligne/construire.py

Réseau (README_HDA.md § 7) :
    normaliser (VEX : largeur, modulation IISR, phase, interruptions)
      -> [courbes régularisées] echantillonner_primitives (VEX : droites / arcs / clothoïdes, corde <= 2 mm)
         [courbes brutes, tracées à la main]  reechantillonner (Resample) -> abscisses (VEX)
      -> attributs (Attribute Copy, par élément source) -> tirets (VEX : découpe par abscisse, tronçons <= 20 m)
      -> attributs_tirets (Attribute Copy) -> largeur (VEX pscale) -> ruban (Sweep, ruban de largeur exacte, haut +Y)
      -> faces (VEX pj_surface) -> solide (pj::marquage_solide : extrusion 3 mm, chanfrein 1 mm, drapé, UV, normales)
Entrées : 1 = courbes (attributs de la description ou tracées à la main), 2 = nivellement (HeightField).
Sortie : maillages Y haut, un component par ligne ou par tronçon <= 20 m (pj_entite = id ou id_cNN).
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "pj_marquage_commun"))
import pj_marquage_outils as M  # noqa: E402

O = M.O
T = hou
NOM = "marquage_ligne"


def vex_normaliser():
    mods = M.modulations()
    noms = ", ".join(f'"{k}"' for k in mods)
    traits = ", ".join(f"{v[0]}" for v in mods.values())
    vides = ", ".join(f"{v[1]}" for v in mods.values())
    return r"""
// Paramètres d'une ligne (description ou courbe tracée à la main) :
//   largeur : largeur_m, sinon 2u (u = 0,05 m ; MQ-LIG-003, marquages_geometrie.unite_u) ;
//   modulation : trait_m / vide_m décrits, sinon table IISR art. 113-1 B (marquages_geometrie.modulations, recopiée à la
//   construction) ; « continue » : un seul trait ;
//   phase : phase_m (abscisse du début du premier trait) ; absente (-1) : ancrage à l'aval, trait plein au contact
//   (MQ-DET-011) ;
//   interruptions : interruptions_json (lecteur) ou tableau interruptions_s [a0, b0, a1, b1...] (passages, bordures,
//   marques ; MQ-DET-010 coupure à 0,50 m, portée par la description).
string MODS[] = {""" + noms + r"""};
float TRAITS[] = {""" + traits + r"""};
float VIDES[] = {""" + vides + r"""};
float w = hasprimattrib(0, "largeur_m") ? prim(0, "largeur_m", @primnum) : 0.0;
if (w <= 0) w = ch("../largeur_defaut");
f@pj_largeur = w;
string mod = hasprimattrib(0, "modulation") ? prim(0, "modulation", @primnum) : "";
if (mod == "") mod = chs("../modulation_defaut");
float tr = hasprimattrib(0, "trait_m") ? prim(0, "trait_m", @primnum) : 0.0;
float vi = hasprimattrib(0, "vide_m") ? prim(0, "vide_m", @primnum) : 0.0;
if (mod != "continue" && (tr <= 0 || vi <= 0)) {
    int k = find(MODS, mod);
    if (k >= 0) { tr = TRAITS[k]; vi = VIDES[k]; }
}
if (mod == "continue" || tr <= 0 || vi <= 0) { tr = 0; vi = 0; }
f@pj_trait = tr;
f@pj_vide = vi;
f@pj_phase = hasprimattrib(0, "phase_m") ? prim(0, "phase_m", @primnum) : -1.0;
s@pj_modulation = mod;
float cut[];
if (hasprimattrib(0, "interruptions_json")) cut = pj_m_nombres(prim(0, "interruptions_json", @primnum));
if (hasprimattrib(0, "interruptions_s")) {
    float c2[] = prim(0, "interruptions_s", @primnum);
    foreach (float c; c2) append(cut, c);
}
f[]@pj_coupures = cut;
// courbe régularisée ? (geometrie_reguliere.primitives, GQ-PRI-001/002)
i@pj_n_primitives = 0;
if (hasprimattrib(0, "geometrie_reguliere")) {
    dict gr = prim(0, "geometrie_reguliere", @primnum);
    if (isvalidindex(gr, "primitives")) {
        dict prs[] = gr["primitives"];
        i@pj_n_primitives = len(prs);
    }
}
if (s@pj_entite == "") s@pj_entite = s@id;
"""


VEX_ECHANTILLONNER = r"""
// Échantillonnage adaptatif des primitives régularisées (droites, arcs, clothoïdes ; GQ-PRI-001/002, G1 par
// construction) : erreur de corde <= « Erreur de corde » (2 mm) et pas <= « Pas max » (drapé). Sommets exactement aux
// jonctions de primitives (coins voulus gardés vifs). Nouvelle polyligne, attributs recopiés ensuite (pj_source).
float corde = ch("../corde");
float pasmax = ch("../pas_max");
dict gr = prim(0, "geometrie_reguliere", @primnum);
dict prs[] = gr["primitives"];
int pts[];
for (int k = 0; k < len(prs); k++) {
    dict pr = prs[k];
    int n = pj_m_prim_segments(pr, corde, pasmax);
    float s0 = pr["s0"];
    float s1 = pr["s1"];
    float L = s1 - s0;
    for (int i = (k == 0 ? 0 : 1); i <= n; i++) {
        float u = L * i / n;
        vector q = pj_m_prim_xyc(pr, u);
        int p = addpoint(0, pj_m_h(q.x, q.y));
        setpointattrib(0, "s", p, s0 + u);
        append(pts, p);
    }
}
if (len(pts) >= 2) {
    int np = addprim(0, "polyline", pts);
    setprimattrib(0, "pj_source", np, @primnum);
}
removeprim(0, @primnum, 1);
"""

VEX_ABSCISSES = r"""
// Abscisse curviligne plane s (m) d'une courbe brute rééchantillonnée (même s que interruptions et phase_m).
int pts[] = primpoints(0, @primnum);
float s = 0;
vector a = point(0, "P", pts[0]);
setpointattrib(0, "s", pts[0], 0.0);
for (int k = 1; k < len(pts); k++) {
    vector b = point(0, "P", pts[k]);
    s += length(set(b.x - a.x, 0, b.z - a.z));
    setpointattrib(0, "s", pts[k], s);
    a = b;
}
i@pj_source = @primnum;
"""

VEX_SOURCE = r"""
// numéro de la courbe source (les nouvelles primitives reprennent ses attributs par Attribute Copy, « vers l'élément »)
i@pj_source = @primnum;
"""

VEX_COUPURES_MARCHES = r"""
// MQ-DET-010 (« jamais sur une bordure ») et TQ-SOL-013 : là où l'axe franchit une marche du modèle de nivellement
// (région propriétaire différente de celle de la ligne et écart d'altitude > « Seuil de marche »), la ligne est
// interrompue, élargie du dégagement (2u, marquages_geometrie.largeurs_par_ligne : espace non peint de 2u le long d'une
// bordure). Région de la ligne : région majoritaire de ses échantillons (pas de 5 cm). Les abaissés (vue <= 2 cm)
// restent sous le seuil de 3 cm : la ligne les traverse.
i@pj_coupures_auto = 0;
i@pj_marches_ambigues = 0;
if (!ch("../couper_marches")) return;
float g[] = pj_niv_grille(1);
if (g[PJ_G_OK] < 0.5) return;
int pts[] = primpoints(0, @primnum);
int n = len(pts);
if (n < 2) return;
float S[];
vector2 Q[];
foreach (int p; pts) {
    float sv = point(0, "s", p);
    vector pv = point(0, "P", p);
    append(S, sv);
    append(Q, set(pv.x, -pv.z));
}
float L = S[n - 1];
int m = max(2, int(ceil(L / 0.05)) + 1);
float T[];
vector2 X[];
int j = 0;
for (int k = 0; k < m; k++) {
    float t = L * k / (m - 1);
    while (j < n - 2 && S[j + 1] < t) j++;
    float u = clamp((t - S[j]) / max(S[j + 1] - S[j], 1e-9), 0.0, 1.0);
    append(T, t);
    append(X, lerp(Q[j], Q[j + 1], u));
}
dict cpt = {};
int reg = -1, best = 0;
foreach (vector2 x; X) {
    int r = pj_niv_region(g, x.x, x.y);
    if (r < 0) continue;
    string kk = itoa(r);
    int c = 0;
    if (isvalidindex(cpt, kk)) c = cpt[kk];
    cpt[kk] = c + 1;
    if (c + 1 > best || (c + 1 == best && r < reg)) { best = c + 1; reg = r; }
}
i@pj_region = reg;
if (reg < 0) return;
float seuil = ch("../seuil_marche");
float deg = ch("../degagement_marche");
float cut[] = f[]@pj_coupures;
int dans = 0;
float sa = 0;
for (int k = 0; k < m; k++) {
    vector2 x = X[k];
    float zo = pj_niv_z(g, x.x, x.y, -1);
    float zl = pj_niv_z(g, x.x, x.y, reg);
    int r = pj_niv_region(g, x.x, x.y);
    int marche = r != reg && zo > 0.5 * PJ_NIV_ABSENT && (zl < 0.5 * PJ_NIV_ABSENT || abs(zl - zo) > seuil);
    if (marche && !dans) { dans = 1; sa = T[k]; }
    if ((!marche || k == m - 1) && dans) {
        dans = 0;
        float sb = marche ? T[k] : T[k - 1];
        if (sb - sa >= ch("../longueur_min_marche") || sa <= 1e-6 || sb >= L - 1e-6) {
            append(cut, max(0.0, sa - deg));
            append(cut, min(L, sb + deg));
            i@pj_coupures_auto += 1;
        } else i@pj_marches_ambigues += 1;                 // ligne posée sur la limite : signalée, non coupée
    }
}
f[]@pj_coupures = cut;
"""

VEX_TIRETS = r"""
// Parties peintes d'une ligne (marquages_lignes / ancien pj_marquages.intervalles) :
//   tirets [phase + k (trait + vide), + trait] ∩ [0, L] (modulation IISR, phase décrite ou ancrée à l'aval MQ-DET-011),
//   moins les interruptions décrites (MQ-DET-010 : coupure à 0,50 m des passages, bordures, autres marques),
//   puis découpe en tronçons <= « Longueur max d'un maillage » (20 m) aux abscisses k x 20 m (maillages uniques,
//   pj_entite = id ou id_cNN). Bouts perpendiculaires à l'axe (sous-courbe exacte de l'axe échantillonné).
int src = i@pj_source;
int pts[] = primpoints(0, @primnum);
int n = len(pts);
removeprim(0, @primnum, 1);
if (n < 2) return;
float S[];
vector P[];
foreach (int p; pts) {
    float sv = point(0, "s", p);
    vector pv = point(0, "P", p);
    append(S, sv);
    append(P, pv);
}
float L = S[n - 1];
float tr = f@pj_trait, vi = f@pj_vide, ph = f@pj_phase;
float iv[];
if (tr <= 0 || vi <= 0) {
    append(iv, 0.0); append(iv, L);
} else {
    float per = tr + vi;
    if (ph < -0.5) ph = (L - tr) - per * floor((L - tr) / per);       // MQ-DET-011 : trait plein au contact aval
    int k0 = int(floor(-ph / per)) - 1;
    int k1 = int(ceil((L - ph) / per)) + 1;
    for (int k = k0; k <= k1; k++) {
        float a = max(ph + k * per, 0.0);
        float b = min(ph + k * per + tr, L);
        if (b - a > 1e-4) { append(iv, a); append(iv, b); }
    }
}
float cut[] = f[]@pj_coupures;
for (int c = 0; c + 1 < len(cut); c += 2) {
    float a0 = cut[c], b0 = cut[c + 1];
    float out[];
    for (int i = 0; i + 1 < len(iv); i += 2) {
        float a = iv[i], b = iv[i + 1];
        if (b <= a0 || a >= b0) { append(out, a); append(out, b); }
        else {
            if (a < a0) { append(out, a); append(out, a0); }
            if (b > b0) { append(out, b0); append(out, b); }
        }
    }
    iv = out;
}
float Tm = max(ch("../troncon_max"), 0.5);
float lmin = ch("../longueur_min");
int nch = max(1, int(ceil(L / Tm - 1e-6)));
string id = s@pj_entite != "" ? s@pj_entite : s@id;
int rang = 0;
for (int i = 0; i + 1 < len(iv); i += 2) {
    float a = iv[i], b = iv[i + 1];
    while (a < b - 1e-6) {
        int ch_ = int(floor(a / Tm + 1e-9));
        float bb = min(b, (ch_ + 1) * Tm);
        if (bb - a >= lmin) {
            // sous-courbe [a, bb] : extrémités interpolées, sommets intérieurs gardés
            int q[];
            int j = 0;
            while (j < n - 2 && S[j + 1] <= a) j++;
            float t = (a - S[j]) / max(S[j + 1] - S[j], 1e-12);
            int p0 = addpoint(0, lerp(P[j], P[j + 1], t));
            setpointattrib(0, "s", p0, a);
            append(q, p0);
            for (int m = j + 1; m < n && S[m] < bb - 0.002; m++) {
                if (S[m] <= a + 0.002) continue;           // pas de segment < 2 mm aux bouts (faces dégénérées)
                int pm = addpoint(0, P[m]);
                setpointattrib(0, "s", pm, S[m]);
                append(q, pm);
            }
            int jb = j;
            while (jb < n - 2 && S[jb + 1] < bb) jb++;
            float tb = (bb - S[jb]) / max(S[jb + 1] - S[jb], 1e-12);
            int p1 = addpoint(0, lerp(P[jb], P[jb + 1], tb));
            setpointattrib(0, "s", p1, bb);
            append(q, p1);
            int np = addprim(0, "polyline", q);
            setprimattrib(0, "pj_source", np, src);
            setprimattrib(0, "pj_entite", np, nch > 1 ? sprintf("%s_c%02d", id, ch_) : id);
            setprimattrib(0, "pj_tiret", np, rang);
            setprimattrib(0, "pj_s0", np, a);
            setprimattrib(0, "pj_s1", np, bb);
            rang++;
        }
        a = bb;
    }
}
"""

VEX_LARGEUR = r"""
// largeur du ruban : pscale des points (Sweep, largeur 1 x pscale) ; dessus = faces déjà maillées (pj_surface)
int prs[] = pointprims(0, @ptnum);
f@pscale = prim(0, "pj_largeur", prs[0]);
"""

VEX_FACES = r"""
// faces du ruban : surface déjà maillée (pj::marquage_solide ne la retriangule pas, Divide en triangles)
i@pj_surface = 1;
i@partie = 0;
i@anneau = 0;
"""


def parametres():
    geo = [
        T.FloatParmTemplate("corde", "Erreur de corde max (m)", 1, default_value=(0.002,), min=0.0001, max=0.05,
                            help="Échantillonnage des arcs et clothoïdes régularisés (≤ 2 mm sur la peinture)."),
        T.FloatParmTemplate("pas_max", "Pas max le long de l'axe (m)", 1, default_value=(0.25,), min=0.05, max=10.0,
                            help="Sommets intermédiaires des droites : le ruban suit le profil en long du sol fabriqué "
                                 "(0,25 m : moitié de l'arête de la chaussée, TQ-MQG-005 entre les sommets)."),
        T.FloatParmTemplate("largeur_defaut", "Largeur par défaut (m)", 1, default_value=(0.10,), min=0.01, max=1.0,
                            help="Sans largeur_m : 2u, u = 0,05 m (MQ-LIG-003, unite_u)."),
        T.FloatParmTemplate("troncon_max", "Longueur max d'un maillage (m)", 1, default_value=(20.0,), min=1.0,
                            max=500.0, help="Lignes plus longues découpées en tronçons (pj_entite = id_cNN)."),
        T.FloatParmTemplate("longueur_min", "Morceau peint minimal (m)", 1, default_value=(0.01,), min=0.0, max=1.0),
        T.ToggleParmTemplate("couper_marches", "Interrompre aux marches de bordure", default_value=True,
                             help="MQ-DET-010 : jamais de peinture sur une bordure ; coupure là où l'axe franchit une "
                                  "marche du modèle de nivellement."),
        T.FloatParmTemplate("seuil_marche", "Seuil de marche (m)", 1, default_value=(0.03,), min=0.0, max=0.3,
                            help="Écart d'altitude entre la région de la ligne et la région propriétaire (> vue d'un "
                                 "abaissé, 2 cm)."),
        T.FloatParmTemplate("degagement_marche", "Dégagement à la marche (m)", 1, default_value=(0.10,), min=0.0,
                            max=1.0, help="Espace non peint de 2u de part et d'autre de la marche."),
        T.FloatParmTemplate("longueur_min_marche", "Franchissement minimal coupé (m)", 1, default_value=(0.2,), min=0.0,
                            max=2.0, help="Franchissements plus courts (ligne posée sur une limite de région, va-et-vient) : "
                                          "non coupés, signalés (pj_marches_ambigues)."),
    ]
    mod = [
        T.StringParmTemplate("modulation_defaut", "Modulation par défaut", 1, default_value=("continue",),
                             menu_items=("continue", "T1", "T'1", "T2", "T'2", "T3", "T'3", "T4"),
                             menu_type=T.menuType.StringReplace,
                             help="Courbes sans attribut modulation (table IISR art. 113-1 B)."),
    ]
    sol = [
        T.FloatParmTemplate("epaisseur", "Épaisseur au-dessus du sol (m)", 1, default_value=(0.002,), min=0.0, max=0.02,
                            help="TQ-MQG-002 / TQ-MQG-011 : lignes longitudinales en peinture, 2 mm (roadMark height "
                                 "OpenDRIVE) ; les autres marques (enduit) restent à 3 mm."),
        T.FloatParmTemplate("enfouissement", "Enfouissement des flancs (m)", 1, default_value=(0.005,), min=0.0,
                            max=0.05),
        T.FloatParmTemplate("chanfrein", "Chanfrein des arêtes du dessus (m)", 1, default_value=(0.001,), min=0.0,
                            max=0.005),
        T.ToggleParmTemplate("draper", "Draper sur le nivellement (entrée 2)", default_value=True),
        T.MenuParmTemplate("mode_region", "Région de drapé", menu_items=("piece", "attribut", "point"),
                           menu_labels=("Région majoritaire de la pièce", "Attribut pj_region",
                                        "Région de chaque sommet (suit les marches)"), default_value=0),
        T.FloatParmTemplate("seuil_franchissement", "Seuil de franchissement (m)", 1, default_value=(0.02,), min=0.0,
                            max=0.2),
        T.StringParmTemplate("couche", "Couche USD (pj_couche)", 1, default_value=(M.COUCHE,)),
        T.FloatParmTemplate("cusp", "Angle de rupture des normales (°)", 1, default_value=(30.0,), min=0.0, max=180.0),
    ]
    return [T.FolderParmTemplate("f_geometrie", "Géométrie", parm_templates=geo, folder_type=T.folderType.Tabs),
            T.FolderParmTemplate("f_modulation", "Modulation", parm_templates=mod, folder_type=T.folderType.Tabs),
            T.FolderParmTemplate("f_solide", "Peinture (solide)", parm_templates=sol, folder_type=T.folderType.Tabs)]


def relier_solide(solide):
    """Paramètres de pj::marquage_solide pilotés par ceux de l'HDA englobante (mêmes noms)."""
    for p in ("epaisseur", "enfouissement", "chanfrein", "seuil_franchissement", "cusp"):
        solide.parm(p).setExpression(f'ch("../{p}")')
    for p in ("draper",):
        solide.parm(p).setExpression(f'ch("../{p}")')
    solide.parm("mode_region").setExpression('ch("../mode_region")')
    solide.parm("couche").set('`chs("../couche")`')


def copie_attributs(sub, nom, dest, src, exclus="pj_entite pj_source pj_tiret pj_s0 pj_s1"):
    """Attribute Copy « vers l'élément » : attributs de primitive de la courbe source pj_source."""
    ac = sub.createNode("attribcopy", nom)
    ac.setInput(0, dest)
    ac.setInput(1, src)
    for p, v in (("srcgrouptype", "prims"), ("destgrouptype", "prims"), ("matchbyattribute", 1),
                 ("matchbyattributemethod", "toelement"), ("attributetomatch", "pj_source"),
                 ("attrib", "otherattrib"), ("attribname", "* " + " ".join("^" + e for e in exclus.split())),
                 ("class", "prims"), ("copyp", 0)):
        ac.parm(p).set(v)
    return ac


def construire(dossier=ICI):
    M.installer_commun()
    sub = O.sous_reseau("pj_" + NOM)
    sub.setParmTemplateGroup(T.ParmTemplateGroup(parametres()))
    ent, niv, sol_fab = sub.indirectInputs()[0], sub.indirectInputs()[1], sub.indirectInputs()[2]
    nor = M.wrangle_m(sub, "normaliser", vex_normaliser(), "primitive", ent)

    reg = M.blast(sub, "courbes_regularisees", nor, "@pj_n_primitives>0", garder=True)
    ech = M.wrangle_m(sub, "echantillonner_primitives", VEX_ECHANTILLONNER, "primitive", reg)
    ech_a = copie_attributs(sub, "attributs_regularisees", ech, reg, exclus="pj_source")
    brut = M.blast(sub, "courbes_brutes", nor, "@pj_n_primitives>0", garder=False)
    src_b = M.wrangle_m(sub, "source_brutes", VEX_SOURCE, "primitive", brut, bibliotheques=False)
    rs = sub.createNode("resample", "reechantillonner")
    rs.setInput(0, src_b)
    rs.parm("treatpolysas").set("straight")
    rs.parm("last").set(1)
    rs.parm("length").setExpression('ch("../pas_max")')
    absc = M.wrangle_m(sub, "abscisses", VEX_ABSCISSES, "primitive", rs, bibliotheques=False)
    fus = sub.createNode("merge", "courbes")
    fus.setInput(0, ech_a)
    fus.setInput(1, absc)
    src = M.wrangle_m(sub, "source_courbes", VEX_SOURCE, "primitive", fus, bibliotheques=False)
    mar = M.wrangle_m(sub, "coupures_marches", VEX_COUPURES_MARCHES, "primitive", src, entrees=(niv,))
    tir = M.wrangle_m(sub, "tirets", VEX_TIRETS, "primitive", mar, bibliotheques=False)
    tir_a = copie_attributs(sub, "attributs_tirets", tir, mar)
    larg = M.wrangle_m(sub, "largeur", VEX_LARGEUR, "point", tir_a, bibliotheques=False)
    sw = sub.createNode("sweep::2.0", "ruban")
    sw.setInput(0, larg)
    for p, v in (("surfaceshape", "ribbon"), ("width", 1.0), ("cols", 1), ("upvectortype", "y"),
                 ("surfacetype", "quads"), ("endcaptype", "none"), ("computeuvs", 0)):
        sw.parm(p).set(v)
    faces = M.wrangle_m(sub, "faces", VEX_FACES, "primitive", sw, bibliotheques=False)
    sol = sub.createNode("pj::marquage_solide::1.0", "solide")
    sol.setInput(0, faces)
    sol.setInput(1, niv)
    sol.setInput(2, sol_fab)               # sol fabriqué (pj::sol) : drapé sur le sol maillé (TQ-MQG-005)
    relier_solide(sol)
    out = sub.createNode("null", "MAILLAGES")
    out.setInput(0, sol)
    O.sortie(sub, out, 0, "sortie")
    O.ranger(sub)
    return O.creer_hda(sub, NOM, "PJ Marquage : lignes", parametres(), dossier, entrees=(1, 3), sorties=1,
                       icone="SOP_sweep",
                       aide="Lignes longitudinales et transversales (ML-*, MT-*) en maillages statiques : axe "
                            "régularisé échantillonné à 2 mm de corde, tirets découpés par abscisse curviligne "
                            "(modulation IISR, phase, interruptions), ruban de largeur exacte (Sweep), peinture "
                            "extrudée de 3 mm avec chanfrein de 1 mm, drapée sur le nivellement, tronçons de 20 m au plus.",
                       details_aide="== Entrées ==\n\n1. Courbes : attributs id, largeur_m, modulation, trait_m, vide_m, "
                                    "phase_m, interruptions_json ou interruptions_s, geometrie_reguliere (facultatif), "
                                    "materiau_id.\n2. Nivellement (HeightField).\n\nContrat : README_HDA.md § 7.",
                       etiquettes_entrees=("Lignes (courbes)", "Nivellement (HeightField)",
                                           "Sol fabriqué (facultatif)"),
                       etiquettes_sorties=("Maillages (Y haut)",))


if __name__ == "__main__":
    print(construire())
