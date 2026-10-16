"""Construit les HDA route::* de la bibliothèque d'assets de la route (hython Houdini 22, licence Indie).

    hython recon/pcg/assets_route/hda/construire_hda_route.py            # construit et développe les 6 HDA
    hython recon/pcg/assets_route/hda/construire_hda_route.py --essai    # + cuisson d'essai et bilan (points, faces, boîtes)

HDA (dossiers développés versionnés recon/pcg/assets_route/hda/route_<nom>.hdalc/) :
  route::extrusion_profil  éléments de bordure et de caniveau : droit, rampant (raccord A → B), quart de rond ou courbe
                           (face convexe ou concave), angle sortant ou rentrant (onglet par Clip + Mirror) ;
  route::revolution        potelets et bornes (profil tourné, bandes de matériau en hauteur) ;
  route::poteau            supports de signalisation ronds ou rectangulaires, bouchon, bande contrastée, platines ;
  route::dalle             dalles, pavés, dalles podotactiles (BEV) à plots en quinconce ;
  route::feu               signaux lumineux R11v, R12, R13, répétiteurs (boîtiers, optiques, visières, pattes) ;
  route::ossature          garde-corps (S8 Setra, urbain), barrières (croix de Saint-André, Lyon 1530), potence.

Repère (Houdini, Y haut) : X = long de l'élément ; Y = haut ; Z = −u (u = profondeur depuis la face vue vers l'arrière)
pour les bordures ; optiques des feux vers −Z. Conversion vers USD (Z haut) à l'export : (x, y, z) → (x, −z, y).
Toutes les sorties portent : uv (sommet, en mètres), N (sommet), materiau (primitive).
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import hda_route_outils as O  # noqa: E402

T = hou
F = hou.FloatParmTemplate
I = hou.IntParmTemplate
S = hou.StringParmTemplate
M = hou.MenuParmTemplate
TG = hou.ToggleParmTemplate


# ================================================================================================ extrusion_profil
VEX_SECTIONS = r"""
// Sections d'un élément de bordure ou de caniveau et faces (VEX, détail). Repère : X long, Y haut, Z = -u.
string sa = chs("../contour_a"), sb = chs("../contour_b");
float A[], B[];
foreach (string t; split(sa)) push(A, atof(t));
foreach (string t; split(sb)) push(B, atof(t));
int mode = chi("../mode");
int n = len(A) / 2;
if (n < 3) return;
if (mode != 1 || len(B) != len(A)) B = A;
float L = chf("../longueur"), R = chf("../rayon"), ang = radians(chf("../angle_deg"));
int ns = 2;
if (mode == 1) ns = max(2, chi("../sections"));
if (mode == 2 || mode == 3) ns = max(max(2, chi("../sections")), int(ceil(ang / radians(7.5))) + 1);
float base = 0;
for (int i = 0; i < n; i++) base = max(base, max(A[2*i], B[2*i]));
float x0 = 0, lx = L;
if (mode <= 1 && chi("../centrer")) x0 = -0.5 * L;
if (mode == 5) { x0 = -base; lx = L + base; }
// UV en mètres : v = coordonnée de périmètre de CHAQUE section (contour interpolé A -> B, sinon les rampants s'étirent),
// u = abscisse réelle de chaque point (x pour les éléments droits, arc th × rayon propre du point pour les courbes)
float PC[], PERIM[], SP[];
addvertexattrib(0, "uv", {0, 0, 0});
setattribtypeinfo(0, "vertex", "uv", "texturecoord");
addprimattrib(0, "materiau", "");
string mat = chs("../materiau");
int P[]; float Sk[];
for (int k = 0; k < ns; k++) {
    float t = float(k) / (ns - 1);
    float s;
    float acc = 0;
    for (int i = 0; i < n; i++) {
        float u = lerp(A[2*i], B[2*i], t), v = lerp(A[2*i+1], B[2*i+1], t);
        int j = (i + 1) % n;
        push(PC, acc);
        acc += distance(set(u, v, 0), set(lerp(A[2*j], B[2*j], t), lerp(A[2*j+1], B[2*j+1], t), 0));
        vector p;
        if (mode == 2) { float th = t * ang; float d = R - u; p = set(d * sin(th), v, -R + d * cos(th)); s = th * d; }
        else if (mode == 3) { float th = t * ang; float d = R + u; p = set(d * sin(th), v, R - d * cos(th)); s = th * d; }
        else { float x = x0 + t * lx; p = set(x, v, -u); s = x; }
        push(SP, s);
        push(P, addpoint(0, p));
    }
    push(PERIM, acc);
    push(Sk, s);
}
// faces latérales (quads), sens : normale vers l'extérieur (vérifié par --essai : volume > 0)
for (int k = 0; k < ns - 1; k++) {
    for (int i = 0; i < n; i++) {
        int j = (i + 1) % n;
        int pts[] = array(P[k*n+i], P[k*n+j], P[(k+1)*n+j], P[(k+1)*n+i]);
        if (chi("../inverser")) pts = array(P[k*n+i], P[(k+1)*n+i], P[(k+1)*n+j], P[k*n+j]);
        int pr = addprim(0, "poly", pts);
        float v0 = PC[k*n+i], v1 = PC[(k+1)*n+i];
        float w0 = (j == 0) ? PERIM[k] : PC[k*n+j], w1 = (j == 0) ? PERIM[k+1] : PC[(k+1)*n+j];
        float a0 = SP[k*n+i], a1 = SP[k*n+j], b0 = SP[(k+1)*n+i], b1 = SP[(k+1)*n+j];
        vector uvs[];
        if (chi("../inverser")) uvs = array(set(a0, v0, 0), set(b0, v1, 0), set(b1, w1, 0), set(a1, w0, 0));
        else uvs = array(set(a0, v0, 0), set(a1, w0, 0), set(b1, w1, 0), set(b0, v1, 0));
        for (int q = 0; q < 4; q++) setvertexattrib(0, "uv", pr, q, uvs[q]);
        setprimattrib(0, "materiau", pr, mat);
    }
}
// abouts (bouchons) : contour plan, UV = (u, v)
for (int e = 0; e < 2; e++) {
    int k = e == 0 ? 0 : ns - 1;
    int pts[];
    for (int i = 0; i < n; i++) push(pts, P[k*n+i]);
    if ((e == 0) != (chi("../inverser") == 1)) pts = reverse(pts);
    int pr = addprim(0, "poly", pts);
    for (int q = 0; q < n; q++) {
        int idx = find(P, pts[q]) - k * n;
        float u = lerp(A[2*idx], B[2*idx], float(k) / (ns - 1)), v = lerp(A[2*idx+1], B[2*idx+1], float(k) / (ns - 1));
        setvertexattrib(0, "uv", pr, q, set(u, v, 0));
    }
    setprimattrib(0, "materiau", pr, mat);
}
"""


def hda_extrusion_profil():
    sub = O.sous_reseau("extrusion_profil")
    sec = O.wrangle(sub, "sections", VEX_SECTIONS, "detail")
    # pièces d'angle : onglet à 45° (Clip) puis symétrie (Mirror) ; sortant : plan de normale (1,0,1), rentrant : (1,0,-1)
    clip = sub.createNode("clip::2.0", "onglet_45")
    clip.setInput(0, sec)
    clip.parm("clipop").set("above")
    clip.parm("dirx").set(1.0)
    clip.parm("diry").set(0.0)
    clip.parm("dirz").setExpression('if(ch("../mode") == 4, 1, -1)')
    mir = sub.createNode("mirror", "symetrie_45")
    mir.setInput(0, clip)
    mir.parm("dirx").set(1.0)
    mir.parm("diry").set(0.0)
    mir.parm("dirz").setExpression('if(ch("../mode") == 4, 1, -1)')
    mir.parm("keepOriginal").set(1)
    fus = sub.createNode("fuse::2.0", "souder_onglet")
    fus.setInput(0, mir)
    fus.parm("tol3d").set(1e-5)
    sw = sub.createNode("switch", "si_angle")
    sw.setInput(0, sec)
    sw.setInput(1, fus)
    sw.parm("input").setExpression('ch("../mode") >= 4')
    bev = sub.createNode("polybevel::3.0", "chanfreins")
    bev.setInput(0, sw)
    bev.parm("grouptype").set("edges")
    bev.parm("ignoreflatedges").set(1)
    bev.parm("flatangle").setExpression('ch("../angle_plat")')
    bev.parm("offset").setExpression('ch("../chanfrein")')
    bev.parm("filletshape").set("chamfer")
    bev.parm("divisions").set(1)
    swb = sub.createNode("switch", "si_chanfrein")
    swb.setInput(0, sw)
    swb.setInput(1, bev)
    swb.parm("input").setExpression('ch("../chanfrein") > 0')
    O.chaine_finale(sub, swb)
    sub.layoutChildren()
    parms = [
        S("contour_a", "Contour A (u v …, m)", 1, help="Coins du profil : u depuis la face vue vers l'arrière, v depuis le dessous "
                                                         "(assets/specs/bordures_elements.json « repere »), contour fermé."),
        S("contour_b", "Contour B (rampant)", 1, help="Profil d'arrivée du rampant (même nombre de points que A)."),
        M("mode", "Pièce", menu_items=("0", "1", "2", "3", "4", "5"),
          menu_labels=("Élément droit", "Rampant A → B (raccord de bateau)", "Courbe / quart de rond, face convexe",
                       "Courbe / quart de rond, face concave", "Angle sortant (onglet 45°)", "Angle rentrant (onglet 45°)"),
          default_value=0),
        F("longueur", "Longueur (m)", 1, default_value=(0.994,), min=0.01, max=5.0,
          help="Longueur réelle (pas de pose − joint) ; pour les angles : longueur de chaque branche sur la face."),
        F("rayon", "Rayon de la face (m)", 1, default_value=(0.5,), min=0.05, max=50.0),
        F("angle_deg", "Angle de la courbe (°)", 1, default_value=(90.0,), min=1.0, max=180.0),
        I("sections", "Sections (rampant, courbes)", 1, default_value=(12,), min=2, max=200),
        TG("centrer", "Pivot au milieu de la longueur", default_value=True),
        TG("inverser", "Inverser l'orientation des faces", default_value=False),
        F("chanfrein", "Cassure des arêtes vives (m)", 1, default_value=(0.002,), min=0.0, max=0.02,
          help="PolyBevel en chanfrein sur les arêtes vives (abouts, arête arrière) : joints lisibles en V."),
        F("angle_plat", "Angle sous lequel une arête n'est pas cassée (°)", 1, default_value=(25.0,), min=0.0, max=90.0),
    ] + O.parms_communs(cusp=35.0, materiau="beton_bordure")
    return O.creer_hda(sub, "extrusion_profil", "Route Extrusion de profil (bordures, caniveaux)", parms,
                       aide="Élément préfabriqué de bordure ou de caniveau à partir d'un profil coté (catalogues NF).")


# ================================================================================================ revolution
VEX_PROFIL_REV = r"""
// Profil (r, h) en polyligne ouverte dans le plan XY, coordonnée de longueur « pc » (m) et rayon de référence
string s = chs("../profil");
float V[];
foreach (string t; split(s)) push(V, atof(t));
int n = len(V) / 2;
if (n < 2) return;
int pts[]; float acc = 0; float rmax = 0;
for (int i = 0; i < n; i++) {
    int p = addpoint(0, set(V[2*i], V[2*i+1], 0));
    if (i > 0) acc += distance(set(V[2*i], V[2*i+1], 0), set(V[2*i-2], V[2*i-1], 0));
    setpointattrib(0, "pc", p, acc);
    rmax = max(rmax, V[2*i]);
    push(pts, p);
}
addprim(0, "polyline", pts);
setdetailattrib(0, "rref", rmax);
"""

VEX_UV_REV = r"""
// UV cylindriques en mètres : u = angle x rayon de référence (raccord de la couture), v = longueur de profil
float rref = detail(0, "rref");
vector c = 0; int pp[] = primpoints(0, @primnum);
foreach (int q; pp) c += point(0, "P", q);
c /= max(1, len(pp));
float th = atan2(@P.z, @P.x);
float tc = atan2(c.z, c.x);
if (th - tc > PI) th -= 2 * PI;
if (tc - th > PI) th += 2 * PI;
v@uv = set(th * rref, point(0, "pc", @ptnum), 0);
"""

VEX_BANDES = r"""
// Matériau par bandes de hauteur : « h0 h1 matériau ; … » (centre de la face)
string mat = chs("../materiau");
string b[] = split(chs("../bandes"));
vector c = 0; int pp[] = primpoints(0, @primnum);
foreach (int q; pp) c += point(0, "P", q);
float y = c.y / max(1, len(pp));
for (int i = 0; i + 2 < len(b); i += 3) {
    if (y >= atof(b[i]) && y <= atof(b[i+1])) mat = b[i+2];
}
s@materiau = mat;
"""


def hda_revolution():
    sub = O.sous_reseau("revolution")
    prof = O.wrangle(sub, "profil", VEX_PROFIL_REV, "detail")
    rev = sub.createNode("revolve::2.0", "tourner")
    rev.setInput(0, prof)
    rev.parm("dirx").set(0.0)
    rev.parm("diry").set(1.0)
    rev.parm("dirz").set(0.0)
    rev.parm("divs").setExpression('ch("../divisions")')
    rev.parm("type").set("closed")
    rev.parm("surftype").set("quads")
    rev.parm("primtype").set("poly")
    inv = sub.createNode("reverse", "orienter_faces")
    inv.setInput(0, rev)
    fus = sub.createNode("fuse::2.0", "souder_axe")
    fus.setInput(0, inv)
    fus.parm("tol3d").set(1e-6)
    uv = O.wrangle(sub, "uv_metres", VEX_UV_REV, "sommet", entree=fus)
    ban = O.wrangle(sub, "bandes_materiaux", VEX_BANDES, "primitive", entree=uv)
    O.chaine_finale(sub, ban)
    sub.layoutChildren()
    parms = [
        S("profil", "Profil (r h …, m)", 1, help="Polyligne (rayon, hauteur) de l'axe en bas à l'axe en haut ; h = 0 au sol."),
        S("bandes", "Bandes de matériau (h0 h1 matériau …)", 1, help="Ex. « 0.87 1.01 blanc_ral9010 » : tête contrastée."),
        I("divisions", "Divisions en tour", 1, default_value=(24,), min=6, max=128),
    ] + O.parms_communs(cusp=30.0, materiau="acier_thermolaque_7016")
    return O.creer_hda(sub, "revolution", "Route Révolution (potelets, bornes)", parms,
                       aide="Objet de révolution à partir d'un profil coté (potelets, bornes).")


# ================================================================================================ poteau
VEX_POTEAU = r"""
// Support de signalisation : fût rond ou rectangulaire, bouchon, bande contrastée, platine, platine de serrage
int rond = chs("../section") == "rond";
float a = chf("../d1"), b = chf("../d2"), H = chf("../hauteur");
int nd = rond ? chi("../divisions") : 4;
addvertexattrib(0, "uv", {0, 0, 0});
setattribtypeinfo(0, "vertex", "uv", "texturecoord");
addprimattrib(0, "materiau", "");
string mat = chs("../materiau");
float hs[] = array(0.0, H);
string ms[] = array(mat);
if (chi("../bande_contrastee") && H > 1.4) {          // arrêté du 15/01/2007 : bande ≥ 10 cm entre 1,20 et 1,40 m
    hs = array(0.0, 1.25, 1.35, H);
    ms = array(mat, "blanc_ral9010", mat);
}
// anneaux
int R[];
float per = 0;
vector ring[];
for (int i = 0; i < nd; i++) {
    vector q;
    if (rond) { float t = 2 * PI * i / nd; q = set(0.5 * a * cos(t), 0, 0.5 * a * sin(t)); }
    else {
        vector c4[] = array(set(-0.5*a, 0, -0.5*b), set(0.5*a, 0, -0.5*b), set(0.5*a, 0, 0.5*b), set(-0.5*a, 0, 0.5*b));
        q = c4[i];
    }
    push(ring, q);
}
float ul[];
float accu = 0;
for (int i = 0; i <= nd; i++) { push(ul, accu); accu += distance(ring[i % nd], ring[(i + 1) % nd]); }
int rows[];
for (int r = 0; r < len(hs); r++) for (int i = 0; i < nd; i++) push(rows, addpoint(0, ring[i] + set(0, hs[r], 0)));
for (int r = 0; r < len(hs) - 1; r++) {
    for (int i = 0; i < nd; i++) {
        int j = (i + 1) % nd;
        int pts[] = array(rows[r*nd+i], rows[(r+1)*nd+i], rows[(r+1)*nd+j], rows[r*nd+j]);
        int pr = addprim(0, "poly", pts);
        vector uvs[] = array(set(ul[i], hs[r], 0), set(ul[i], hs[r+1], 0), set(ul[i+1], hs[r+1], 0), set(ul[i+1], hs[r], 0));
        for (int q = 0; q < 4; q++) setvertexattrib(0, "uv", pr, q, uvs[q]);
        setprimattrib(0, "materiau", pr, ms[r]);
    }
}
// fond (sous le sol, fermé)
{ int pts[]; for (int i = 0; i < nd; i++) push(pts, rows[i]); int pr = addprim(0, "poly", pts); setprimattrib(0, "materiau", pr, mat); }
// bouchon : chapeau plastique noir (cylindre aplati, 1,15 x le fût, 25 mm) ou dessus plan
int top = (len(hs) - 1) * nd;
if (chi("../bouchon")) {
    float e = 0.025, k = 1.12;
    int t0[], t1[];
    for (int i = 0; i < nd; i++) push(t0, addpoint(0, ring[i] * k + set(0, H - 0.015, 0)));
    for (int i = 0; i < nd; i++) push(t1, addpoint(0, ring[i] * k * 0.92 + set(0, H + e - 0.015, 0)));
    for (int i = 0; i < nd; i++) {
        int j = (i + 1) % nd;
        int pr = addprim(0, "poly", array(t0[i], t1[i], t1[j], t0[j]));
        setprimattrib(0, "materiau", pr, "plastique_noir_feux");
        int pb = addprim(0, "poly", array(t0[i], t0[j], rows[top + j], rows[top + i]));
        setprimattrib(0, "materiau", pb, "plastique_noir_feux");
    }
    int pr = addprim(0, "poly", reverse(t1));
    setprimattrib(0, "materiau", pr, "plastique_noir_feux");
} else {
    int pts[]; for (int i = 0; i < nd; i++) push(pts, rows[top + i]);
    int pr = addprim(0, "poly", reverse(pts)); setprimattrib(0, "materiau", pr, mat);
}
"""

VEX_PLATINES = r"""
// Platine carrée (côté c, épaisseur e) avec 4 boulons, et/ou platine de serrage circulaire (Ø d, épaisseur e)
function void boite(vector c; vector t; string m) {
    vector s[] = array(set(-1,-1,-1), set(1,-1,-1), set(1,-1,1), set(-1,-1,1), set(-1,1,-1), set(1,1,-1), set(1,1,1), set(-1,1,1));
    int p[];
    foreach (vector q; s) push(p, addpoint(0, c + q * t * 0.5));
    int f[] = array(3,2,1,0, 4,5,6,7, 1,5,4,0, 2,6,5,1, 3,7,6,2, 0,4,7,3);
    for (int i = 0; i < 6; i++) {
        int pr = addprim(0, "poly", array(p[f[4*i]], p[f[4*i+1]], p[f[4*i+2]], p[f[4*i+3]]));
        setprimattrib(0, "materiau", pr, m);
    }
}
function void disque(vector c; float r; float e; int nd; string m) {
    int a[], b[];
    for (int i = 0; i < nd; i++) {
        float t = 2 * PI * i / nd;
        push(a, addpoint(0, c + set(r * cos(t), 0, r * sin(t))));
        push(b, addpoint(0, c + set(r * cos(t), e, r * sin(t))));
    }
    for (int i = 0; i < nd; i++) {
        int j = (i + 1) % nd;
        int pr = addprim(0, "poly", array(a[j], b[j], b[i], a[i]));
        setprimattrib(0, "materiau", pr, m);
    }
    int pr = addprim(0, "poly", b); setprimattrib(0, "materiau", pr, m);
    pr = addprim(0, "poly", reverse(a)); setprimattrib(0, "materiau", pr, m);
}
string mat = chs("../materiau");
if (chi("../platine")) {
    float c = chf("../platine_cote"), e = chf("../platine_ep");
    boite(set(0, -0.5 * e, 0), set(c, e, c), mat);               // dessus de platine au niveau du sol (h = 0)
    float d = 0.5 * c - 0.03;
    for (int i = 0; i < 4; i++) {
        float sx = (i & 1) ? 1 : -1, sz = (i & 2) ? 1 : -1;
        disque(set(sx * d, 0, sz * d), 0.012, 0.012, 6, mat);     // écrous (estimés M16)
    }
}
if (chi("../serrage")) disque(set(0, 0, 0), 0.5 * chf("../serrage_diam"), chf("../serrage_ep"), 32, mat);
"""


def hda_poteau():
    sub = O.sous_reseau("poteau")
    fut = O.wrangle(sub, "fut", VEX_POTEAU, "detail")
    fut_inv = sub.createNode("reverse", "orienter_fut")
    fut_inv.setInput(0, fut)
    pla = O.wrangle(sub, "platines", VEX_PLATINES, "detail", entree=fut_inv)
    uvp = O.wrangle(sub, "uv_platines", "if (length(v@uv) == 0) {" + O.VEX_UV_BOITE + "}", "sommet", entree=pla)
    O.chaine_finale(sub, uvp)
    sub.layoutChildren()
    parms = [
        M("section", "Section", menu_items=("rond", "rect"), menu_labels=("Ronde (tube)", "Rectangulaire"), default_value=0),
        F("d1", "Diamètre ou largeur (m)", 1, default_value=(0.0603,), min=0.02, max=0.5),
        F("d2", "Profondeur (m, rectangulaire)", 1, default_value=(0.0603,), min=0.02, max=0.5),
        F("hauteur", "Hauteur hors sol (m)", 1, default_value=(3.0,), min=0.3, max=12.0),
        I("divisions", "Divisions (rond)", 1, default_value=(24,), min=6, max=64),
        TG("bouchon", "Bouchon en tête", default_value=True),
        TG("bande_contrastee", "Bande contrastée 1,25-1,35 m (arrêté du 15/01/2007)", default_value=True),
        TG("platine", "Platine carrée", default_value=False),
        F("platine_cote", "Côté de la platine (m)", 1, default_value=(0.2,)),
        F("platine_ep", "Épaisseur de la platine (m)", 1, default_value=(0.003,)),
        TG("serrage", "Platine de serrage circulaire", default_value=False),
        F("serrage_diam", "Diamètre de la platine de serrage (m)", 1, default_value=(0.155,)),
        F("serrage_ep", "Épaisseur de la platine de serrage (m)", 1, default_value=(0.0027,)),
    ] + O.parms_communs(cusp=40.0, materiau="acier_galvanise")
    return O.creer_hda(sub, "poteau", "Route Poteau de signalisation", parms,
                       aide="Support de panneau (IISR 1re partie art. 6) : fût, bouchon, bande contrastée, platines.")


# ================================================================================================ dalle
VEX_PLOTS = r"""
// Points des plots en quinconce sur le dessus d'une dalle (entraxe e, marge m), y = épaisseur
if (!chi("../plots")) return;
float L = chf("../longueur"), l = chf("../largeur"), ep = chf("../epaisseur");
float e = chf("../plot_entraxe"), m = chf("../plot_marge");
int nr = int(floor((l - 2 * m) / (e * 0.5) + 1e-6)) + 1;
for (int r = 0; r < nr; r++) {
    float z = -0.5 * l + m + r * 0.5 * e;
    float dx = (r % 2) ? 0.5 * e : 0.0;
    for (float x = -0.5 * L + m + dx; x <= 0.5 * L - m + 1e-6; x += e) addpoint(0, set(x, ep, z));
}
"""


def hda_dalle():
    sub = O.sous_reseau("dalle")
    box = sub.createNode("box", "bloc")
    box.parm("type").set("poly")
    for a, e in (("sizex", "longueur"), ("sizey", "epaisseur"), ("sizez", "largeur")):
        box.parm(a).setExpression(f'ch("../{e}")')
    box.parm("ty").setExpression('ch("../epaisseur") / 2')
    bev = sub.createNode("polybevel::3.0", "chanfreins")
    bev.setInput(0, box)
    bev.parm("grouptype").set("edges")
    bev.parm("offset").setExpression('ch("../chanfrein")')
    bev.parm("filletshape").set("chamfer")
    bev.parm("divisions").set(1)
    swb = sub.createNode("switch", "si_chanfrein")
    swb.setInput(0, box)
    swb.setInput(1, bev)
    swb.parm("input").setExpression('ch("../chanfrein") > 0')
    pts = O.wrangle(sub, "points_plots", VEX_PLOTS, "detail")
    plot = sub.createNode("tube", "plot")
    plot.parm("type").set("poly")
    plot.parm("cap").set(1)
    plot.parm("rad1").setExpression('ch("../plot_diam_base") / 2')
    plot.parm("rad2").setExpression('ch("../plot_diam_haut") / 2')
    plot.parm("height").setExpression('ch("../plot_hauteur")')
    plot.parm("ty").setExpression('ch("../plot_hauteur") / 2')
    plot.parm("cols").set(12)
    plot.parm("rows").set(2)
    cp = sub.createNode("copytopoints::2.0", "copier_plots")
    cp.setInput(0, plot)
    cp.setInput(1, pts)
    fus = sub.createNode("merge", "assembler")
    fus.setInput(0, swb)
    fus.setInput(1, cp)
    uv = O.wrangle(sub, "uv_metres", O.VEX_UV_BOITE, "sommet", entree=fus)
    mat = O.wrangle(sub, "materiau", 's@materiau = chs("../materiau");', "primitive", entree=uv)
    O.chaine_finale(sub, mat)
    sub.layoutChildren()
    parms = [
        F("longueur", "Longueur (m)", 1, default_value=(0.2,)), F("largeur", "Largeur (m)", 1, default_value=(0.1,)),
        F("epaisseur", "Épaisseur (m)", 1, default_value=(0.08,)), F("chanfrein", "Chanfrein des arêtes (m)", 1, default_value=(0.005,)),
        TG("plots", "Plots podotactiles (BEV)", default_value=False),
        F("plot_diam_base", "Plot : diamètre de base (m)", 1, default_value=(0.035,)),
        F("plot_diam_haut", "Plot : diamètre du sommet (m)", 1, default_value=(0.025,)),
        F("plot_hauteur", "Plot : hauteur (m)", 1, default_value=(0.005,)),
        F("plot_entraxe", "Plot : entraxe (m)", 1, default_value=(0.075,)),
        F("plot_marge", "Plot : marge au bord (m)", 1, default_value=(0.0375,)),
    ] + O.parms_communs(cusp=40.0, materiau="paves_beton_rect")
    return O.creer_hda(sub, "dalle", "Route Dalle / pavé / BEV", parms,
                       aide="Pavés, dalles et dalles podotactiles (plots en quinconce).")


# ================================================================================================ feu
VEX_GABARIT_FEU = r"""
// Points d'implantation des modules (haut → bas, ou gauche → droite VU DE FACE), couleur et pictogramme par module.
// Les optiques regardent −Z : pour l'usager qui fait face au signal, sa gauche est +X (IISR 6, art. 109-3 : R12 « vert
// et rouge, dans cet ordre de droite à gauche » -> couleurs « pieton_rouge pieton_vert » = rouge à gauche, vert à droite).
// diametre_haut > 0 : module du haut agrandi (ensemble mixte rouge 300 sur jaune et vert 200, IISR 6 art. 109-4).
int n = chi("../nb_feux");
int horiz = chi("../disposition");
float w = chf("../boitier_l"), h = chf("../boitier_h");
float dh = chf("../diametre_haut");
float s0 = (dh > 0 && !horiz) ? dh / chf("../diametre") : 1.0;
string c[] = split(chs("../couleurs")), p[] = split(chs("../pictos"));
for (int i = 0; i < n; i++) {
    vector pos = horiz ? set((0.5 * (n - 1) - i) * w, 0, 0) : set(0, (n - 1 - i) * h, 0);
    if (!horiz && i == 0) pos.y += 0.5 * (s0 - 1.0) * h;
    int pt = addpoint(0, pos);
    setpointattrib(0, "pscale", pt, i == 0 ? s0 : 1.0);
    setpointattrib(0, "couleur", pt, i < len(c) ? c[i] : "rouge");
    setpointattrib(0, "picto", pt, i < len(p) ? p[i] : "");
}
"""

VEX_MAT_FEU = r"""
string piece = s@piece;
if (piece == "lentille") s@materiau = "feu_lentille_" + s@couleur;
else if (piece == "corps") s@materiau = chs("../materiau_corps");
else s@materiau = chs("../materiau");
if (piece == "lentille" && s@picto != "") s@materiau += "_" + s@picto;
"""

VEX_PATTES = r"""
// Pattes de fixation (haut et bas) et console arrière vers le mât (+Z), boîtes
function void boite(vector c; vector t; string m) {
    vector s[] = array(set(-1,-1,-1), set(1,-1,-1), set(1,-1,1), set(-1,-1,1), set(-1,1,-1), set(1,1,-1), set(1,1,1), set(-1,1,1));
    int p[];
    foreach (vector q; s) push(p, addpoint(0, c + q * t * 0.5));
    int f[] = array(3,2,1,0, 4,5,6,7, 1,5,4,0, 2,6,5,1, 3,7,6,2, 0,4,7,3);
    for (int i = 0; i < 6; i++) {
        int pr = addprim(0, "poly", array(p[f[4*i]], p[f[4*i+1]], p[f[4*i+2]], p[f[4*i+3]]));
        setprimattrib(0, "materiau", pr, m);
        setprimattrib(0, "piece", pr, "patte");
    }
}
int n = chi("../nb_feux"), horiz = chi("../disposition");
float w = chf("../boitier_l"), h = chf("../boitier_h"), d = chf("../boitier_p");
float dh = chf("../diametre_haut");
float s0 = (dh > 0 && !horiz) ? dh / chf("../diametre") : 1.0;
float H = horiz ? h : (n - 1 + s0) * h, W = horiz ? n * w : w;
float yb = horiz ? -0.5 * h : -0.5 * h, yt = yb + H;
float xc = 0;
string m = chs("../materiau");
boite(set(xc, yt + 0.035, 0.5 * d), set(0.06, 0.07, 0.04), m);
boite(set(xc, yb - 0.035, 0.5 * d), set(0.06, 0.07, 0.04), m);
boite(set(xc, yt + 0.06, 0.5 * d + 0.06), set(0.05, 0.02, 0.16), m);
boite(set(xc, yb - 0.06, 0.5 * d + 0.06), set(0.05, 0.02, 0.16), m);
"""


def hda_feu():
    sub = O.sous_reseau("feu")
    # --- module : boîtier, lentille, collerette, visière
    boit = sub.createNode("box", "boitier")
    boit.parm("type").set("poly")
    boit.parm("sizex").setExpression('ch("../boitier_l")')
    boit.parm("sizey").setExpression('ch("../boitier_h")')
    boit.parm("sizez").setExpression('ch("../boitier_p")')
    boit.parm("tz").setExpression('ch("../boitier_p") / 2')
    bbev = sub.createNode("polybevel::3.0", "boitier_arrondi")
    bbev.setInput(0, boit)
    bbev.parm("grouptype").set("edges")
    bbev.parm("offset").setExpression('min(0.02, ch("../boitier_l") * 0.06)')
    bbev.parm("filletshape").set("round")
    bbev.parm("divisions").set(3)
    bpiece = O.wrangle(sub, "piece_corps", 's@piece = "corps";', "primitive", entree=bbev)
    lent = sub.createNode("tube", "lentille")
    lent.parm("type").set("poly")
    lent.parm("orient").set("z")
    lent.parm("cap").set(1)
    lent.parm("rad1").setExpression('ch("../diametre") / 2')
    lent.parm("rad2").setExpression('ch("../diametre") / 2 * 0.97')
    lent.parm("height").set(0.012)
    lent.parm("tz").set(-0.004)
    lent.parm("cols").set(40)
    lpiece_r = O.wrangle(sub, "piece_lentille", 's@piece = "lentille";', "primitive", entree=lent)
    # optique carrée (R12 : figurines dans un carré, IISR 6e partie fig. 2)
    lentc = sub.createNode("box", "lentille_carree")
    lentc.parm("type").set("poly")
    lentc.parm("sizex").setExpression('ch("../diametre")')
    lentc.parm("sizey").setExpression('ch("../diametre")')
    lentc.parm("sizez").set(0.012)
    lentc.parm("tz").set(-0.004)
    lpiece_c = O.wrangle(sub, "piece_lentille_carree", 's@piece = "lentille";', "primitive", entree=lentc)
    lsw = sub.createNode("switch", "si_optique_carree")
    lsw.setInput(0, lpiece_r)
    lsw.setInput(1, lpiece_c)
    lsw.parm("input").setExpression('ch("../optique_carree")')
    lpiece = lsw
    vis = sub.createNode("tube", "visiere")
    vis.parm("type").set("poly")
    vis.parm("orient").set("z")
    vis.parm("cap").set(0)
    vis.parm("rad1").setExpression('ch("../diametre") / 2 + 0.012')
    vis.parm("rad2").setExpression('ch("../diametre") / 2 + 0.03')
    vis.parm("height").setExpression('ch("../visiere")')
    vis.parm("tz").setExpression('-ch("../visiere") / 2')
    vis.parm("cols").set(40)
    vclip = sub.createNode("clip::2.0", "visiere_ouverte_en_bas")
    vclip.setInput(0, vis)
    vclip.parm("clipop").set("above")
    vclip.parm("dirx").set(0.0)
    vclip.parm("diry").set(1.0)
    vclip.parm("dirz").set(0.0)
    vclip.parm("dist").setExpression('-0.25 * ch("../diametre")')
    vext = sub.createNode("polyextrude::2.0", "visiere_epaisseur")
    vext.setInput(0, vclip)
    vext.parm("dist").set(0.003)
    vext.parm("outputback").set(1)
    vpiece_r = O.wrangle(sub, "piece_visiere", 's@piece = "visiere";', "primitive", entree=vext)
    # visière carrée : caisson ouvert devant, derrière et en bas
    visc = sub.createNode("box", "visiere_carree")
    visc.parm("type").set("poly")
    visc.parm("sizex").setExpression('ch("../diametre") + 0.04')
    visc.parm("sizey").setExpression('ch("../diametre") + 0.04')
    visc.parm("sizez").setExpression('ch("../visiere")')
    visc.parm("tz").setExpression('-ch("../visiere") / 2')
    vouv = O.wrangle(sub, "visiere_carree_ouverte",
                     'vector n = prim_normal(0, @primnum, {0.5, 0.5}); '
                     'if (abs(n.z) > 0.5 || n.y < -0.5) removeprim(0, @primnum, 1);', "primitive", entree=visc)
    vextc = sub.createNode("polyextrude::2.0", "visiere_carree_epaisseur")
    vextc.setInput(0, vouv)
    vextc.parm("dist").set(0.003)
    vextc.parm("outputback").set(1)
    vpiece_c = O.wrangle(sub, "piece_visiere_carree", 's@piece = "visiere";', "primitive", entree=vextc)
    vsw = sub.createNode("switch", "si_visiere_carree")
    vsw.setInput(0, vpiece_r)
    vsw.setInput(1, vpiece_c)
    vsw.parm("input").setExpression('ch("../optique_carree")')
    vpiece = vsw
    mod = sub.createNode("merge", "module")
    for k, e in enumerate((bpiece, lpiece, vpiece)):
        mod.setInput(k, e)
    gab = O.wrangle(sub, "gabarit_modules", VEX_GABARIT_FEU, "detail")
    cp = sub.createNode("copytopoints::2.0", "empiler_modules")
    cp.setInput(0, mod)
    cp.setInput(1, gab)
    cp.parm("targetattribs").set(1)
    cp.parm("useapply1").set(1)
    cp.parm("applyto1").set("prims")           # attributs ponctuels du gabarit -> primitives des copies
    cp.parm("applymethod1").set("copy")
    cp.parm("applyattribs1").set("couleur picto")
    pat = O.wrangle(sub, "pattes_console", VEX_PATTES, "detail")
    asm = sub.createNode("merge", "assembler")
    asm.setInput(0, cp)
    asm.setInput(1, pat)
    mat = O.wrangle(sub, "materiaux", VEX_MAT_FEU, "primitive", entree=asm)
    uv = O.wrangle(sub, "uv_metres", O.VEX_UV_BOITE, "sommet", entree=mat)
    O.chaine_finale(sub, uv)
    sub.layoutChildren()
    parms = [
        I("nb_feux", "Nombre de feux", 1, default_value=(3,), min=1, max=4),
        M("disposition", "Disposition", menu_items=("0", "1"), menu_labels=("Verticale (haut → bas)", "Horizontale (gauche → droite vu de face)"),
          default_value=0),
        F("diametre", "Diamètre des optiques (m)", 1, default_value=(0.2,), help="IISR 6e partie : 200 ou 300 mm ; répétiteurs 90 mm."),
        TG("optique_carree", "Optique carrée (R12 piétons)", default_value=False),
        F("diametre_haut", "Diamètre de l'optique du haut (m, 0 = identique)", 1, default_value=(0.0,),
          help="Ensemble mixte (IISR 6e partie, art. 109-4) : rouge 300 mm sur jaune et vert 200 mm ; module du haut mis à l'échelle."),
        S("couleurs", "Couleurs (haut → bas)", 1, default_value=("rouge jaune vert",)),
        S("pictos", "Pictogrammes", 1, default_value=("",), help="R12 : pieton_arret pieton_marche ; R13c : cycle ; R13b : bus."),
        F("boitier_l", "Module : largeur (m)", 1, default_value=(0.265,)),
        F("boitier_h", "Module : hauteur (m)", 1, default_value=(0.24,)),
        F("boitier_p", "Module : profondeur (m)", 1, default_value=(0.25,)),
        F("visiere", "Visière : longueur (m)", 1, default_value=(0.2,)),
        S("materiau_corps", "Matériau du corps", 1, default_value=("plastique_noir_feux",),
          help="plastique_noir_feux (monobloc) ou feu_corps_gris (modules gris RAL 7035 observés au carrefour)."),
    ] + O.parms_communs(cusp=40.0, materiau="plastique_noir_feux")
    return O.creer_hda(sub, "feu", "Route Signal lumineux (R11v, R12, R13)", parms,
                       aide="Signal lumineux de circulation : modules à optique circulaire, visières, pattes, console.")


# ================================================================================================ ossature
VEX_MEMBRES = r"""
// Membrures (segments) d'un garde-corps, d'une barrière ou d'une potence : prim attrs forme (0 rect, 1 rond),
// w, h (section, m), haut (vecteur), materiau.
function void membre(vector a; vector b; int forme; float w; float h; vector up; string m) {
    int p0 = addpoint(0, a), p1 = addpoint(0, b);
    int pr = addprim(0, "polyline", p0, p1);
    setprimattrib(0, "forme", pr, forme);
    setprimattrib(0, "w", pr, w);
    setprimattrib(0, "h", pr, h);
    setprimattrib(0, "haut", pr, up);
    setprimattrib(0, "materiau", pr, m);
}
int mod = chi("../modele");
float L = chf("../longueur"), H = chf("../hauteur"), em = chf("../entraxe_montants"), eb = chf("../entraxe_barreaux");
float lb = chf("../lisse_basse");
string m = chs("../materiau");
vector Y = {0, 1, 0}, Zv = {0, 0, 1};
addprimattrib(0, "forme", 0); addprimattrib(0, "w", 0.0); addprimattrib(0, "h", 0.0);
addprimattrib(0, "haut", {0, 1, 0}); addprimattrib(0, "materiau", "");
if (mod == 0) {          // garde-corps S8 (Setra GC 1997) : MC 120x55, montants 80x40 / 1,50 m, lisse inf 60x30, barreaux 30x30
    float hmc = 0.055, xm = 0;
    for (xm = 0; xm <= L + 1e-6; xm += em) membre(set(xm, 0, 0), set(xm, H - hmc, 0), 0, 0.080, 0.040, Zv, m);
    membre(set(-0.04, H - 0.5 * hmc, 0), set(L + 0.04, H - 0.5 * hmc, 0), 0, 0.055, 0.120, Y, m);
    membre(set(-0.02, lb, 0), set(L + 0.02, lb, 0), 0, 0.030, 0.060, Y, m);
    for (float x = 0.5 * eb; x < L - 0.04; x += eb) {
        if (abs(x - em * rint(x / em)) < 0.06) continue;
        membre(set(x, lb + 0.015, 0), set(x, H - hmc, 0), 0, 0.030, 0.030, Zv, m);
    }
} else if (mod == 1) {   // garde-corps urbain (Angers) : montants plats 40x15, barreaux ronds Ø20, main courante plat 40x10
    for (float xm = 0; xm <= L + 1e-6; xm += em) membre(set(xm, 0, 0), set(xm, H - 0.03, 0), 0, 0.040, 0.015, Zv, m);
    membre(set(-0.02, H - 0.025, 0), set(L + 0.02, H - 0.025, 0), 0, 0.020, 0.020, Y, m);
    membre(set(-0.03, H - 0.005, 0), set(L + 0.03, H - 0.005, 0), 0, 0.010, 0.040, Y, m);
    membre(set(-0.01, lb, 0), set(L + 0.01, lb, 0), 0, 0.040, 0.010, Zv, m);
    for (float x = 0.5 * eb; x < L - 0.03; x += eb) {
        if (abs(x - em * rint(x / em)) < 0.04) continue;
        membre(set(x, lb + 0.02, 0), set(x, H - 0.035, 0), 1, 0.020, 0.020, Zv, m);
    }
} else if (mod == 2) {   // barrière à croix de Saint-André : montants 50x50, cadre 0,10-1,00 m, croix Ø25
    float c = 0.05;
    membre(set(0, -0.0, 0), set(0, H, 0), 0, c, c, Zv, m);
    membre(set(L, -0.0, 0), set(L, H, 0), 0, c, c, Zv, m);
    membre(set(0, H - 0.02, 0), set(L, H - 0.02, 0), 0, 0.04, 0.03, Y, m);
    membre(set(0, lb, 0), set(L, lb, 0), 0, 0.04, 0.03, Y, m);
    membre(set(0.5 * c, lb + 0.02, 0), set(L - 0.5 * c, H - 0.04, 0), 1, 0.025, 0.025, Zv, m);
    membre(set(0.5 * c, H - 0.04, 0), set(L - 0.5 * c, lb + 0.02, 0), 1, 0.025, 0.025, Zv, m);
} else if (mod == 3) {   // barrière Lyon 1530 : montants Ø60, croisillons Ø20, anneau central Ø140, main courante débordante
    float r = 0.07;
    membre(set(0, 0, 0), set(0, H, 0), 1, 0.06, 0.06, Zv, m);
    membre(set(L, 0, 0), set(L, H, 0), 1, 0.06, 0.06, Zv, m);
    membre(set(-0.14, H + 0.02, 0), set(L + 0.03, H + 0.02, 0), 1, 0.05, 0.05, Zv, m);
    membre(set(0, lb, 0), set(L, lb, 0), 1, 0.03, 0.03, Zv, m);
    vector c = set(0.5 * L, 0.5 * (H + lb), 0);
    vector k[] = array(set(0.03, H - 0.01, 0), set(L - 0.03, H - 0.01, 0), set(0.03, lb + 0.01, 0), set(L - 0.03, lb + 0.01, 0));
    foreach (vector q; k) membre(q, c + normalize(q - c) * r, 1, 0.02, 0.02, Zv, m);
    for (int i = 0; i < 16; i++) {
        float t0 = 2 * PI * i / 16, t1 = 2 * PI * (i + 1) / 16;
        membre(c + set(r * cos(t0), r * sin(t0), 0), c + set(r * cos(t1), r * sin(t1), 0), 1, 0.02, 0.02, Zv, m);
    }
} else if (mod == 4) {   // potence de feux : mât, crosse, tirant (géométrie de principe)
    membre(set(0, 0, 0), set(0, H, 0), 1, 0.168, 0.168, Zv, m);
    membre(set(0, H - 0.3, 0), set(L, H - 0.3, 0), 1, 0.114, 0.114, Zv, m);
    membre(set(0, H - 1.2, 0), set(0.45 * L, H - 0.32, 0), 1, 0.06, 0.06, Zv, m);
}
"""

VEX_HABILLAGE = r"""
// Habillage de chaque membrure en boîte (rect) ou en tube à 12 côtés (rond), UV en mètres ; lignes retirées
int np = nprimitives(0);
addvertexattrib(0, "uv", {0, 0, 0});
setattribtypeinfo(0, "vertex", "uv", "texturecoord");
for (int pr = 0; pr < np; pr++) {
    int pts[] = primpoints(0, pr);
    vector a = point(0, "P", pts[0]), b = point(0, "P", pts[1]);
    int forme = prim(0, "forme", pr);
    float w = prim(0, "w", pr), h = prim(0, "h", pr);
    vector up = prim(0, "haut", pr);
    string m = prim(0, "materiau", pr);
    vector d = normalize(b - a);
    if (abs(dot(d, up)) > 0.99) up = abs(d.y) > 0.9 ? set(0, 0, 1) : set(0, 1, 0);
    vector sd = normalize(cross(d, up));
    up = normalize(cross(sd, d));
    float len_ = distance(a, b);
    int nd = forme == 1 ? 12 : 4;
    vector ring[];
    for (int i = 0; i < nd; i++) {
        float t = 2 * PI * (i + (forme == 1 ? 0 : 0.5)) / nd;
        float cx = forme == 1 ? 0.5 * w * cos(t) : 0.5 * w * sign(cos(t));
        float cy = forme == 1 ? 0.5 * h * sin(t) : 0.5 * h * sign(sin(t));
        push(ring, sd * cx + up * cy);
    }
    int A[], B[];
    for (int i = 0; i < nd; i++) { push(A, addpoint(0, a + ring[i])); push(B, addpoint(0, b + ring[i])); }
    float acc = 0;
    for (int i = 0; i < nd; i++) {
        int j = (i + 1) % nd;
        float seg = distance(ring[i], ring[j]);
        int f = addprim(0, "poly", A[i], A[j], B[j], B[i]);
        setvertexattrib(0, "uv", f, 0, set(acc, 0, 0)); setvertexattrib(0, "uv", f, 1, set(acc + seg, 0, 0));
        setvertexattrib(0, "uv", f, 2, set(acc + seg, len_, 0)); setvertexattrib(0, "uv", f, 3, set(acc, len_, 0));
        setprimattrib(0, "materiau", f, m);
        acc += seg;
    }
    int c0 = addprim(0, "poly", reverse(A)); setprimattrib(0, "materiau", c0, m);
    int c1 = addprim(0, "poly", B); setprimattrib(0, "materiau", c1, m);
    for (int q = 0; q < nd; q++) {
        setvertexattrib(0, "uv", c0, q, set(dot(ring[nd - 1 - q], sd), dot(ring[nd - 1 - q], up), 0));
        setvertexattrib(0, "uv", c1, q, set(dot(ring[q], sd), dot(ring[q], up), 0));
    }
    removeprim(0, pr, 1);
}
"""


def hda_ossature():
    sub = O.sous_reseau("ossature")
    mem = O.wrangle(sub, "membrures", VEX_MEMBRES, "detail")
    hab = O.wrangle(sub, "habillage", VEX_HABILLAGE, "detail", entree=mem)
    O.chaine_finale(sub, hab)
    sub.layoutChildren()
    parms = [
        M("modele", "Modèle", menu_items=("0", "1", "2", "3", "4"),
          menu_labels=("Garde-corps de pont S8 (Setra)", "Garde-corps urbain (Angers)", "Barrière à croix de Saint-André",
                       "Barrière Lyon 1530", "Potence de feux (principe)"), default_value=0),
        F("longueur", "Longueur / portée (m)", 1, default_value=(3.0,)),
        F("hauteur", "Hauteur (m)", 1, default_value=(1.0,)),
        F("entraxe_montants", "Entraxe des montants (m)", 1, default_value=(1.5,)),
        F("entraxe_barreaux", "Entraxe des barreaux (m)", 1, default_value=(0.14,)),
        F("lisse_basse", "Hauteur de la lisse basse (m)", 1, default_value=(0.10,)),
    ] + O.parms_communs(cusp=40.0, materiau="acier_galvanise")
    return O.creer_hda(sub, "ossature", "Route Ossature (garde-corps, barrières, potence)", parms,
                       aide="Assemblages de membrures en profilés : garde-corps, barrières, potence.")


CONSTRUCTEURS = dict(extrusion_profil=hda_extrusion_profil, revolution=hda_revolution, poteau=hda_poteau, dalle=hda_dalle,
                     feu=hda_feu, ossature=hda_ossature)


def construire(noms=None):
    out = {}
    for n, f in CONSTRUCTEURS.items():
        if noms and n not in noms:
            continue
        out[n] = f()
        print("HDA", n, "->", out[n])
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--hda", nargs="*")
    a = ap.parse_args()
    construire(a.hda)
