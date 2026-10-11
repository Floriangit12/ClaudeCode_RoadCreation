// pj_marquage.h : outils VEX des HDA de marquage (hda/pj_marquage_*, README_HDA.md § 7).
// Recopiés en tête des wrangles par pj_marquage_outils.vex_m() (#include "opdef:" impossible en Houdini 22).
// Repères : description / gabarits en (x, y) locaux Z haut ; Houdini Y haut : (x, y) -> (x, 0, -y).
// Gabarits (assets/specs/marquages_geometrie.json, repere.gabarits) : x latéral (positif à droite du sens de
// circulation), y longitudinal (sens de circulation) ; pose = origine + cap de l'axe +y (degrés, trigonométrique
// depuis +x local), comme decrire/marquages_commun.poser.
#ifndef PJ_MARQUAGE_H
#define PJ_MARQUAGE_H

#define PJ_M_ABSENT -1.0e30

function vector pj_m_h(float x; float y) { return set(x, 0.0, -y); }
function vector2 pj_m_xy(vector P) { return set(P.x, -P.z); }

function vector2 pj_m_dir(float cap_deg)
{
    float a = radians(cap_deg);
    return set(cos(a), sin(a));
}

// gabarit (x latéral droite, y longitudinal) -> local, origine o, cap de +y, échelle e (marquages_commun.poser)
function vector2 pj_m_poser(vector2 q; vector2 o; float cap_deg; float e)
{
    vector2 ey = pj_m_dir(cap_deg);
    vector2 ex = set(ey.y, -ey.x);
    return o + e * (q.x * ex + q.y * ey);
}

// inverse de pj_m_poser (marquages_commun.dans_repere)
function vector2 pj_m_deposer(vector2 p; vector2 o; float cap_deg; float e)
{
    vector2 ey = pj_m_dir(cap_deg);
    vector2 ex = set(ey.y, -ey.x);
    vector2 d = (p - o) / max(e, 1e-9);
    return set(dot(d, ex), dot(d, ey));
}

// nombres d'un texte JSON plat ou imbriqué ("[[1.85, 2.9], [3, 4]]") -> [1.85, 2.9, 3, 4]
function float[] pj_m_nombres(string s)
{
    float r[];
    string parts[] = split(s, "[], \t\n");
    foreach (string p; parts) {
        if (p != "") append(r, atof(p));
    }
    return r;
}

// ------------------------------------------------------------------------------------------- primitives régularisées
// Primitives de geometrie_reguliere (decrire/regulariser_geometrie.py, GQ-PRI-001/002) : droite (k = 0), arc (k0),
// clothoïde (courbure affine k0 -> k1 sur la longueur, évaluée en sous-arcs de 5 cm comme Chaine._preparer).
// Renvoie (x, y, cap) au point d'abscisse locale u (0 <= u <= s1 - s0). x0, y0 locaux (lecteur).
function vector pj_m_prim_xyc(dict pr; float u)
{
    float x0 = pr["x0"];
    float y0 = pr["y0"];
    float c0 = pr["cap0_rad"];
    float k0 = pr["k0"];
    string ty = pr["type"];
    float L = 0;
    float s0 = pr["s0"];
    float s1 = pr["s1"];
    L = s1 - s0;
    if (ty == "clothoide") {
        float k1 = pr["k1"];
        int m = max(1, int(ceil(L / 0.05)));
        float d = L / m;
        float x = x0, y = y0, h = c0, reste = u;
        for (int j = 0; j < m && reste > 1e-12; j++) {
            float k = k0 + (k1 - k0) * (j + 0.5) / m;
            float dd = min(d, reste);
            float a = k * dd / 2.0;
            float c = dd * (abs(a) > 1e-6 ? sin(a) / a : 1.0 - a * a / 6.0);
            x += c * cos(h + a);
            y += c * sin(h + a);
            h += k * dd;
            reste -= dd;
        }
        return set(x, y, h);
    }
    if (abs(k0) < 1e-12) return set(x0 + u * cos(c0), y0 + u * sin(c0), c0);
    float cc = c0 + k0 * u;
    return set(x0 + (sin(cc) - sin(c0)) / k0, y0 - (cos(cc) - cos(c0)) / k0, cc);
}

// nombre de segments d'une primitive : erreur de corde <= corde (GQ, chaîne de marquage 2 mm) et pas <= pas_max
function int pj_m_prim_segments(dict pr; float corde; float pas_max)
{
    float s0 = pr["s0"];
    float s1 = pr["s1"];
    float L = max(s1 - s0, 0.0);
    float k = abs(float(pr["k0"]));
    if (isvalidindex(pr, "k1")) k = max(k, abs(float(pr["k1"])));
    int n = max(1, int(ceil(L / max(pas_max, 1e-3))));
    if (k > 1e-9) {
        float R = 1.0 / k;
        float dth = corde < R ? 2.0 * acos(1.0 - corde / R) : PI / 2;
        n = max(n, int(ceil(L * k / max(dth, 1e-6))));
    }
    return n;
}

// ------------------------------------------------------------------------------------------- polygones plans
// point (x, y) local dans la primitive fermée pr de geo (plan XZ Houdini) : règle pair-impair
function int pj_m_dans(int geo; int pr; float x; float y)
{
    int pts[] = primpoints(geo, pr);
    int n = len(pts);
    int c = 0;
    int j = n - 1;
    for (int i = 0; i < n; i++) {
        vector a = point(geo, "P", pts[i]);
        vector b = point(geo, "P", pts[j]);
        float ay = -a.z;
        float by = -b.z;
        if ((ay > y) != (by > y)) {
            float xi = (b.x - a.x) * (y - ay) / (by - ay) + a.x;
            if (x < xi) c = 1 - c;
        }
        j = i;
    }
    return c;
}

// aire signée (local, trigonométrique > 0) d'une primitive fermée
function float pj_m_aire(int geo; int pr)
{
    int pts[] = primpoints(geo, pr);
    int n = len(pts);
    float a = 0;
    for (int i = 0; i < n; i++) {
        vector p = point(geo, "P", pts[i]);
        vector q = point(geo, "P", pts[(i + 1) % n]);
        a += p.x * (-q.z) - q.x * (-p.z);
    }
    return 0.5 * a;
}

// polygone fermé (local (x, y)) -> primitive Houdini ; renvoie le numéro de primitive
function int pj_m_poly(int geo; vector2 q[])
{
    int pts[];
    foreach (vector2 p; q) append(pts, addpoint(geo, pj_m_h(p.x, p.y)));
    return addprim(geo, "poly", pts);
}

// rectangle centré en c, grand côté L selon u (unitaire), largeur W -> 4 sommets trigonométriques
function vector2[] pj_m_rectangle(vector2 c; vector2 u; float L; float W)
{
    vector2 v = set(-u.y, u.x);
    vector2 r[];
    append(r, c - u * L / 2 - v * W / 2);
    append(r, c + u * L / 2 - v * W / 2);
    append(r, c + u * L / 2 + v * W / 2);
    append(r, c - u * L / 2 + v * W / 2);
    return r;
}

// disque de diamètre d, erreur de corde <= corde (marquages_geometrie.repere.discretisation : 1 mm)
function vector2[] pj_m_disque(vector2 c; float d; float corde)
{
    float r = d / 2;
    int n = max(16, int(ceil(PI / acos(max(-1.0, 1.0 - corde / r)))));
    vector2 out[];
    for (int k = 0; k < n; k++) {
        float a = 2 * PI * k / n;
        append(out, c + set(r * cos(a), r * sin(a)));
    }
    return out;
}

// anneau d'une primitive (local (x, y))
function vector2[] pj_m_anneau(int geo; int pr)
{
    int pts[] = primpoints(geo, pr);
    vector2 q[];
    foreach (int p; pts) {
        vector P = point(geo, "P", p);
        append(q, set(P.x, -P.z));
    }
    return q;
}

// centroïde (x, y) et aire signée (z) d'un anneau
function vector pj_m_centroide_q(vector2 q[])
{
    int n = len(q);
    float a = 0, cx = 0, cy = 0;
    for (int i = 0; i < n; i++) {
        vector2 p = q[i];
        vector2 r = q[(i + 1) % n];
        float c = p.x * r.y - r.x * p.y;
        a += c;
        cx += (p.x + r.x) * c;
        cy += (p.y + r.y) * c;
    }
    a *= 0.5;
    if (abs(a) < 1e-12) return set(0.0, 0.0, 0.0);
    return set(cx / (6 * a), cy / (6 * a), a);
}

function float pj_m_dist_seg(vector2 p; vector2 a; vector2 b)
{
    vector2 ab = b - a;
    float t = clamp(dot(p - a, ab) / max(dot(ab, ab), 1e-12), 0.0, 1.0);
    return length(p - (a + t * ab));
}

function float pj_m_dist_anneau(vector2 p; vector2 q[])
{
    float d = 1e9;
    int n = len(q);
    for (int i = 0; i < n; i++) d = min(d, pj_m_dist_seg(p, q[i], q[(i + 1) % n]));
    return d;
}

// formes paramétriques dans le repère du gabarit (x droite, y sens de circulation), origine comme l'ancien
// pj_marquages._symbole_param : barre = rectangle centré (grand côté selon y) ; point = disque centré ;
// dent_requin = base centrée sur l'origine, pointe en (0, h) (MQ-RAL-001) ; chevron = pointe à l'origine, branches
// vers l'arrière, trait constant (MQ-ILO-003 / MQ-CYC-008).
function vector2[] pj_m_forme(string ty; dict prm; float corde)
{
    vector2 q[];
    if (ty == "barre") {
        float L = prm["longueur_m"];
        float W = prm["largeur_m"];
        q = pj_m_rectangle(set(0.0, 0.0), set(0.0, 1.0), L, W);
    } else if (ty == "point") {
        float d = prm["diametre_m"];
        q = pj_m_disque(set(0.0, 0.0), d, corde);
    } else if (ty == "dent_requin") {
        float b = prm["base_m"];
        float h = prm["hauteur_m"];
        append(q, set(-b / 2, 0.0));
        append(q, set(b / 2, 0.0));
        append(q, set(0.0, h));
    } else if (ty == "chevron") {
        float lb = prm["branche_m"];
        float ouv = radians(float(prm["ouverture_deg"]));
        float tr = prm["trait_m"];
        float h = ouv / 2;
        vector2 e1 = set(sin(h), -cos(h)) * lb;
        vector2 e2 = set(-sin(h), -cos(h)) * lb;
        vector2 n1 = set(-cos(h), -sin(h));
        vector2 n2 = set(cos(h), -sin(h));
        vector2 ic = set(0.0, -tr / sin(h));
        append(q, set(0.0, 0.0));
        append(q, e2);
        append(q, e2 + n2 * tr);
        append(q, ic);
        append(q, e1 + n1 * tr);
        append(q, e1);
    }
    return q;
}

// nom de prototype d'une forme paramétrique (dimensions en mm)
function string pj_m_cle_forme(string ty; dict prm)
{
    if (ty == "barre") return sprintf("BARRE_%04dx%04d", int(rint(float(prm["longueur_m"]) * 1000)),
                                      int(rint(float(prm["largeur_m"]) * 1000)));
    if (ty == "point") return sprintf("POINT_%04d", int(rint(float(prm["diametre_m"]) * 1000)));
    if (ty == "dent_requin") return sprintf("TRIANGLE_%04dx%04d", int(rint(float(prm["base_m"]) * 1000)),
                                            int(rint(float(prm["hauteur_m"]) * 1000)));
    if (ty == "chevron") return sprintf("CHEVRON_b%04d_o%04d_t%03d", int(rint(float(prm["branche_m"]) * 1000)),
                                        int(rint(float(prm["ouverture_deg"]) * 10)),
                                        int(rint(float(prm["trait_m"]) * 1000)));
    return "";
}

#endif

// ------------------------------------------------------------------------------------------- sol fabriqué
// Altitude du SOL FABRIQUÉ (géométrie de pj::sol, Y haut, entrée geo) sous (x, y) locaux : intersections d'un rayon
// vertical de zref + portee à zref − portee ; parmi elles (hors BEV), celle de la région de nivellement « region »
// (attribut region_niveau des triangles de sol) la plus proche de zref, sinon la plus proche toutes régions. Renvoie
// zref et ok = 0 sans intersection. La peinture suit ainsi le sol réellement posé (raccords aux bordures, marches
// adoucies) et non le seul modèle (TQ-SOL-013, CF-26 ; TQ-MQG-005 : dessus − sol dans [0,5 ; 6] mm).
function float pj_m_z_sol(int geo; float x; float y; float zref; float portee; int region; int ok)
{
    ok = 0;
    if (nprimitives(geo) == 0) return zref;
    vector pos[];
    int prs[];
    vector uvw[];
    int n = intersect_all(geo, "", set(x, zref + portee, -y), set(0.0, -2.0 * portee, 0.0), pos, prs, uvw, 1e-5, 1e-5);
    float z_reg = zref, z_tout = zref, d_reg = 1e9, d_tout = 1e9;
    int a_reg = hasprimattrib(geo, "region_niveau");
    for (int k = 0; k < n; k++) {
        string m = prim(geo, "materiau_id", prs[k]);
        if (m == "bev_podotactile") continue;
        float d = abs(pos[k].y - zref);
        if (d < d_tout) { d_tout = d; z_tout = pos[k].y; }
        if (a_reg && region >= 0 && prim(geo, "region_niveau", prs[k]) == region && d < d_reg) { d_reg = d; z_reg = pos[k].y; }
    }
    if (d_reg < 1e8) { ok = 2; return z_reg; }
    if (d_tout < 1e8) { ok = 1; return z_tout; }
    return zref;
}
