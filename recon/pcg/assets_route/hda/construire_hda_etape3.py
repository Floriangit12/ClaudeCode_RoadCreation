"""HDA de l'étape 3 de la bibliothèque route_fr (hython Houdini 22, licence Indie) : route::assemblage et route::panneau.

    hython recon/pcg/assets_route/hda/construire_hda_etape3.py           # construit et développe les 2 HDA

route::assemblage   « kit de pièces » : un texte décrit des pièces cotées (boîtes, tubes à rayon variable le long d'une
                    polyligne, profils balayés le long d'une polyligne, ellipsoïdes, faces et disques à UV 0-1) ; le
                    wrangle VEX fabrique les pièces fermées, orientées, à UV en mètres, avec un matériau par pièce.
                    Sert au mobilier, à l'assainissement, à l'éclairage, aux équipements de retenue, aux feux du site,
                    aux potences et portiques, aux balises.
route::panneau      plaque de signalisation à bord tombé : un ou plusieurs contours (convexes, ou réels si non convexes, relevés sur l'emprise
                    opaque des faces officielles) ; face avant à UV 0-1 sur l'image de la face, bord tombé, revers creux
                    à rebord, rails de fixation au dos (un ou deux selon la hauteur de la plaque).

Repère des descriptions : celui de l'USD (X, Y, Z haut, mètres). Le VEX convertit vers Houdini (X, Y haut, Z = −Y) ;
l'export (fabriquer_assets_route.vers_usd) refait (x, y, z) → (x, −z, y). Toutes les faces sont orientées vers
l'extérieur (règle de Houdini : sommets en sens horaire vus de l'extérieur), contrôlé par le volume positif.
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import hda_route_outils as O  # noqa: E402

F = hou.FloatParmTemplate
I = hou.IntParmTemplate
S = hou.StringParmTemplate
TG = hou.ToggleParmTemplate

VEX_COMMUN = r"""
vector H(vector u) { return set(u.x, u.z, -u.y); }          // USD (Z haut) -> Houdini (Y haut)

// polygone : points neufs, orienté pour que sa normale (convention Houdini) suive nh (repère Houdini), UV par sommet
int poly(vector P[]; vector UV[]; vector nh; string mat) {
    int k = len(P);
    if (k < 3) return -1;
    vector n = 0;
    for (int i = 0; i < k; i++) {
        vector a = P[i], b = P[(i + 1) % k];
        n += set((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y));
    }
    int ordre[];
    for (int i = 0; i < k; i++) push(ordre, i);
    if (dot(-n, nh) < 0) ordre = reverse(ordre);
    int pts[];
    foreach (int i; ordre) push(pts, addpoint(0, P[i]));
    int pr = addprim(0, "poly", pts);
    for (int q = 0; q < k; q++) setvertexattrib(0, "uv", pr, q, UV[ordre[q]]);
    setprimattrib(0, "materiau", pr, mat);
    return pr;
}
"""

VEX_ASSEMBLAGE = VEX_COMMUN + r"""
// ---------------------------------------------------------------- boîte (centre, tailles, rotation autour de Z)
void boite(vector c; vector t; float rz; string mat) {
    float a = radians(rz);
    vector ex = set(cos(a), sin(a), 0), ey = set(-sin(a), cos(a), 0), ez = {0, 0, 1};
    vector h = t * 0.5;
    // 6 faces : normale locale, deux axes de la face (u, v) et leurs demi-tailles
    vector N[] = array(ex, -ex, ey, -ey, ez, -ez);
    vector U[] = array(ey, ey, ex, ex, ex, ex);
    vector V[] = array(ez, ez, ez, ez, ey, ey);
    float hn[] = array(h.x, h.x, h.y, h.y, h.z, h.z);
    float hu[] = array(h.y, h.y, h.x, h.x, h.x, h.x);
    float hv[] = array(h.z, h.z, h.z, h.z, h.y, h.y);
    for (int f = 0; f < 6; f++) {
        vector P[], UV[];
        float su[] = array(-1.0, 1.0, 1.0, -1.0), sv[] = array(-1.0, -1.0, 1.0, 1.0);
        for (int q = 0; q < 4; q++) {
            vector p = c + N[f] * hn[f] + U[f] * su[q] * hu[f] + V[f] * sv[q] * hv[f];
            push(P, H(p));
            push(UV, set(su[q] * hu[f], sv[q] * hv[f], 0));
        }
        poly(P, UV, H(N[f]), mat);
    }
}

// ---------------------------------------------------------------- repères le long d'une polyligne (transport parallèle)
void reperes(vector C[]; vector up0; export vector T[]; export vector Nn[]; export vector B[]; export float L[]; export float K[]) {
    int n = len(C);
    resize(T, n); resize(Nn, n); resize(B, n); resize(L, n); resize(K, n);
    for (int i = 0; i < n; i++) {
        vector t;
        if (i == 0) t = normalize(C[1] - C[0]);
        else if (i == n - 1) t = normalize(C[n - 1] - C[n - 2]);
        else t = normalize(normalize(C[i] - C[i - 1]) + normalize(C[i + 1] - C[i]));
        T[i] = t;
        float k = 1.0;
        if (i > 0 && i < n - 1) k = 1.0 / max(0.5, dot(t, normalize(C[i + 1] - C[i])));   // onglet
        K[i] = k;
        L[i] = (i == 0) ? 0.0 : L[i - 1] + distance(C[i], C[i - 1]);
    }
    vector w = up0 - dot(up0, T[0]) * T[0];
    if (length(w) < 1e-6) { w = abs(T[0].z) < 0.9 ? set(0, 0, 1) : set(1, 0, 0); w = w - dot(w, T[0]) * T[0]; }
    w = normalize(w);
    for (int i = 0; i < n; i++) {
        if (i > 0) { w = w - dot(w, T[i]) * T[i]; w = length(w) < 1e-6 ? Nn[i - 1] : normalize(w); }
        Nn[i] = w;                                  // axe v du profil (« haut »)
        B[i] = normalize(cross(w, T[i]));           // axe u du profil
    }
}

// ---------------------------------------------------------------- profil (u, v) balayé le long d'une polyligne
void balayage(vector C[]; vector up0; float U[]; float Vv[]; float R[]; int caps; string mat) {
    int n = len(C), k = len(U);
    vector T[], Nn[], B[]; float L[], K[];
    reperes(C, up0, T, Nn, B, L, K);
    float aire = 0;
    for (int j = 0; j < k; j++) { int j2 = (j + 1) % k; aire += U[j] * Vv[j2] - U[j2] * Vv[j]; }
    float sens = aire >= 0 ? 1.0 : -1.0;
    float per[]; float acc = 0;
    for (int j = 0; j <= k; j++) { push(per, acc); if (j < k) acc += distance(set(U[j], Vv[j], 0), set(U[(j + 1) % k], Vv[(j + 1) % k], 0)); }
    for (int i = 0; i < n - 1; i++) {
        for (int j = 0; j < k; j++) {
            int j2 = (j + 1) % k;
            vector P[], UV[];
            int ii[] = array(i, i, i + 1, i + 1), jj[] = array(j, j2, j2, j);
            for (int q = 0; q < 4; q++) {
                int a = ii[q], b = jj[q];
                float s = R[a] * K[a];
                push(P, H(C[a] + (B[a] * U[b] + Nn[a] * Vv[b]) * s));
                push(UV, set(per[b == j2 && j2 == 0 ? k : b], L[a], 0));
            }
            // normale extérieure de l'arête (u, v) dans le repère du segment
            vector2 e = set(U[j2] - U[j], Vv[j2] - Vv[j]);
            vector2 no = sens * set(e.y, -e.x);
            vector tm = normalize(T[i] + T[i + 1]);
            vector bm = normalize(B[i] + B[i + 1]), nm = normalize(Nn[i] + Nn[i + 1]);
            poly(P, UV, H(bm * no.x + nm * no.y), mat);
        }
    }
    for (int e = 0; e < 2; e++) {
        if (!(caps == 1 || (caps == 2 && e == 0) || (caps == 3 && e == 1))) continue;
        int i = e == 0 ? 0 : n - 1;
        vector P[], UV[];
        for (int j = 0; j < k; j++) {
            push(P, H(C[i] + (B[i] * U[j] + Nn[i] * Vv[j]) * R[i]));
            push(UV, set(U[j] * R[i], Vv[j] * R[i], 0));
        }
        poly(P, UV, H(e == 0 ? -T[i] : T[i]), mat);
    }
}

void tube(vector C[]; float R[]; int nc; int caps; string mat) {
    float U[], Vv[];
    for (int j = 0; j < nc; j++) { float a = 2 * PI * j / nc; push(U, cos(a)); push(Vv, sin(a)); }
    balayage(C, set(0, 0, 1), U, Vv, R, caps, mat);
}

void ellipsoide(vector c; vector r; int ns; string mat) {
    int nl = max(4, ns / 2);
    for (int i = 0; i < nl; i++) {
        float t0 = PI * i / nl - PI / 2, t1 = PI * (i + 1) / nl - PI / 2;
        for (int j = 0; j < ns; j++) {
            float p0 = 2 * PI * j / ns, p1 = 2 * PI * (j + 1) / ns;
            float tt[] = array(t0, t0, t1, t1), pp[] = array(p0, p1, p1, p0);
            vector P[], UV[]; vector cen = 0;
            for (int q = 0; q < 4; q++) {
                vector d = set(cos(tt[q]) * cos(pp[q]), cos(tt[q]) * sin(pp[q]), sin(tt[q]));
                vector p = c + d * r;
                push(P, H(p)); cen += d;
                push(UV, set(pp[q] * max(r.x, r.y), tt[q] * r.z, 0));
            }
            if (i == 0) { removeindex(P, 0); removeindex(UV, 0); }          // pôles : triangles
            else if (i == nl - 1) { removeindex(P, 2); removeindex(UV, 2); }
            poly(P, UV, H(normalize(cen)), mat);
        }
    }
}

void face(vector c; vector nv; vector upv; float w; float h; string mat) {
    vector n = normalize(nv), u = normalize(upv - dot(upv, n) * n), s = normalize(cross(u, n));
    vector P[], UV[];
    float su[] = array(-0.5, 0.5, 0.5, -0.5), sv[] = array(-0.5, -0.5, 0.5, 0.5);
    for (int q = 0; q < 4; q++) { push(P, H(c + s * su[q] * w + u * sv[q] * h)); push(UV, set(su[q] + 0.5, sv[q] + 0.5, 0)); }
    poly(P, UV, H(n), mat);
}

void disque(vector c; vector nv; float r; int ns; string mat) {
    vector n = normalize(nv);
    vector u = abs(n.z) < 0.9 ? set(0, 0, 1) : set(0, 1, 0);
    u = normalize(u - dot(u, n) * n); vector s = normalize(cross(u, n));
    vector P[], UV[];
    for (int j = 0; j < ns; j++) {
        float a = 2 * PI * j / ns;
        push(P, H(c + (s * cos(a) + u * sin(a)) * r)); push(UV, set(0.5 + 0.5 * cos(a), 0.5 + 0.5 * sin(a), 0));
    }
    poly(P, UV, H(n), mat);
}

// ---------------------------------------------------------------- lecture de la description
addvertexattrib(0, "uv", {0, 0, 0});
setattribtypeinfo(0, "vertex", "uv", "texturecoord");
addprimattrib(0, "materiau", "");
string texte = chs("../pieces");
string lignes[] = split(re_replace("\n", ";", texte), ";");
foreach (string ligne; lignes) {
    string t[] = split(ligne);
    if (len(t) < 2) continue;
    string ty = t[0];
    if (ty == "B") {                       // B cx cy cz sx sy sz rz mat
        boite(set(atof(t[1]), atof(t[2]), atof(t[3])), set(atof(t[4]), atof(t[5]), atof(t[6])), atof(t[7]), t[8]);
    } else if (ty == "T") {                // T n nc caps mat (x y z r) * n
        int n = atoi(t[1]), nc = atoi(t[2]), caps = atoi(t[3]);
        vector C[]; float R[];
        for (int i = 0; i < n; i++) { push(C, set(atof(t[5 + 4*i]), atof(t[6 + 4*i]), atof(t[7 + 4*i]))); push(R, atof(t[8 + 4*i])); }
        tube(C, R, nc, caps, t[4]);
    } else if (ty == "Q") {                // Q n k caps mat upx upy upz (x y z) * n (u v) * k
        int n = atoi(t[1]), k = atoi(t[2]), caps = atoi(t[3]);
        vector up0 = set(atof(t[5]), atof(t[6]), atof(t[7]));
        vector C[]; float R[], U[], Vv[];
        int o = 8;
        for (int i = 0; i < n; i++) { push(C, set(atof(t[o]), atof(t[o + 1]), atof(t[o + 2]))); push(R, 1.0); o += 3; }
        for (int j = 0; j < k; j++) { push(U, atof(t[o])); push(Vv, atof(t[o + 1])); o += 2; }
        balayage(C, up0, U, Vv, R, caps, t[4]);
    } else if (ty == "E") {                // E cx cy cz rx ry rz ns mat
        ellipsoide(set(atof(t[1]), atof(t[2]), atof(t[3])), set(atof(t[4]), atof(t[5]), atof(t[6])), atoi(t[7]), t[8]);
    } else if (ty == "F") {                // F cx cy cz nx ny nz ux uy uz w h mat
        face(set(atof(t[1]), atof(t[2]), atof(t[3])), set(atof(t[4]), atof(t[5]), atof(t[6])),
             set(atof(t[7]), atof(t[8]), atof(t[9])), atof(t[10]), atof(t[11]), t[12]);
    } else if (ty == "G") {                // G cx cy cz nx ny nz r ns mat
        disque(set(atof(t[1]), atof(t[2]), atof(t[3])), set(atof(t[4]), atof(t[5]), atof(t[6])), atof(t[7]), atoi(t[8]), t[9]);
    }
}
"""


def hda_assemblage():
    sub = O.sous_reseau("assemblage")
    w = O.wrangle(sub, "pieces", VEX_ASSEMBLAGE, "detail")
    fus = sub.createNode("fuse::2.0", "souder_coincidents")
    fus.setInput(0, w)
    fus.parm("tol3d").set(1e-5)
    div = sub.createNode("divide", "polygones_convexes")
    div.setInput(0, fus)
    div.parm("convex").set(1)
    O.chaine_finale(sub, div)
    sub.layoutChildren()
    parms = [
        S("pieces", "Pièces (une par ligne ou séparées par « ; »)", 1,
          help="B cx cy cz sx sy sz rz mat | T n nc caps mat (x y z r)×n | Q n k caps mat upx upy upz (x y z)×n (u v)×k | "
               "E cx cy cz rx ry rz ns mat | F cx cy cz nx ny nz ux uy uz w h mat | G cx cy cz nx ny nz r ns mat. "
               "Repère USD (Z haut, m). caps : 0 aucun, 1 deux bouts, 2 début, 3 fin."),
    ] + O.parms_communs(cusp=40.0, materiau="acier_galvanise")
    return O.creer_hda(sub, "assemblage", "Route Assemblage de pièces cotées", parms,
                       aide="Mobilier, assainissement, éclairage, retenue, feux, potences : pièces cotées décrites en texte.")


VEX_PANNEAU = VEX_COMMUN + r"""
// Plaque(s) de signalisation à bord tombé. Contours convexes dans le plan de la face (x à droite, z en haut, m), face
// avant à Y = 0 tournée vers +Y (USD), corps vers −Y. UV de la face : position rapportée à l'image de la face
// (origine img_x0, img_z0 ; taille img_l × img_h) -> la même image sert à toutes les plaques d'un même dessin.
addvertexattrib(0, "uv", {0, 0, 0});
setattribtypeinfo(0, "vertex", "uv", "texturecoord");
addprimattrib(0, "materiau", "");
float x0 = chf("../img_x0"), z0 = chf("../img_z0"), il = chf("../img_l"), ih = chf("../img_h");
float d = chf("../bord_tombe"), lip = chf("../rebord"), tole = chf("../tole");
string mf = chs("../materiau_face"), mr = chs("../materiau_revers");
string blocs[] = split(chs("../contours"), "|");
foreach (string bloc; blocs) {
    string t[] = split(bloc);
    int n = len(t) / 2;
    if (n < 3) continue;
    vector2 Q[];
    for (int i = 0; i < n; i++) push(Q, set(atof(t[2*i]), atof(t[2*i + 1])));
    // sens trigonométrique (vu de face)
    float aire = 0;
    for (int i = 0; i < n; i++) { vector2 a = Q[i], b = Q[(i + 1) % n]; aire += a.x * b.y - b.x * a.y; }
    if (aire < 0) Q = reverse(Q);
    // contour intérieur (rebord) : décalage vers l'intérieur par les bissectrices
    vector2 Qi[];
    for (int i = 0; i < n; i++) {
        vector2 a = Q[(i + n - 1) % n], b = Q[i], c = Q[(i + 1) % n];
        vector2 e1 = normalize(b - a), e2 = normalize(c - b);
        vector2 n1 = set(-e1.y, e1.x), n2 = set(-e2.y, e2.x);          // normales intérieures (sens trigo)
        vector2 bis = normalize(n1 + n2);
        float cs = max(0.3, dot(bis, n1));
        push(Qi, b + bis * lip / cs);
    }
    float zmin = 1e9, zmax = -1e9, xmin = 1e9, xmax = -1e9;
    foreach (vector2 q; Q) { zmin = min(zmin, q.y); zmax = max(zmax, q.y); xmin = min(xmin, q.x); xmax = max(xmax, q.x); }
    // face avant
    vector P[], UV[];
    foreach (vector2 q; Q) { push(P, H(set(q.x, 0, q.y))); push(UV, set((q.x - x0) / il, (q.y - z0) / ih, 0)); }
    poly(P, UV, H({0, 1, 0}), mf);
    // bord tombé (flancs), rebord arrière, flancs intérieurs, revers
    for (int i = 0; i < n; i++) {
        int j = (i + 1) % n;
        vector2 a = Q[i], b = Q[j], ai = Qi[i], bi = Qi[j];
        vector2 e = normalize(b - a);
        vector no = set(e.y, 0, -e.x);                                     // normale extérieure (USD, plan x-z)
        float s0 = 0, s1 = length(b - a);
        vector Pf[] = array(H(set(a.x, 0, a.y)), H(set(b.x, 0, b.y)), H(set(b.x, -d, b.y)), H(set(a.x, -d, a.y)));
        vector Uf[] = array(set(s0, 0, 0), set(s1, 0, 0), set(s1, d, 0), set(s0, d, 0));
        poly(Pf, Uf, H(set(no.x, 0, no.z)), mr);
        vector Pl[] = array(H(set(a.x, -d, a.y)), H(set(b.x, -d, b.y)), H(set(bi.x, -d, bi.y)), H(set(ai.x, -d, ai.y)));
        vector Ul[] = array(set(a.x, a.y, 0), set(b.x, b.y, 0), set(bi.x, bi.y, 0), set(ai.x, ai.y, 0));
        poly(Pl, Ul, H({0, -1, 0}), mr);
        vector Pi[] = array(H(set(ai.x, -d, ai.y)), H(set(bi.x, -d, bi.y)), H(set(bi.x, -tole, bi.y)), H(set(ai.x, -tole, ai.y)));
        vector Ui[] = array(set(s0, 0, 0), set(s1, 0, 0), set(s1, d - tole, 0), set(s0, d - tole, 0));
        poly(Pi, Ui, H(set(-no.x, 0, -no.z)), mr);
    }
    vector Pr[], Ur[];
    foreach (vector2 q; Qi) { push(Pr, H(set(q.x, -tole, q.y))); push(Ur, set(q.x, q.y, 0)); }
    poly(Pr, Ur, H({0, -1, 0}), mr);
    // rails de fixation au dos (profilés horizontaux) : 2 si la plaque dépasse rail_seuil de haut, sinon 1
    if (chi("../rails")) {
        float hh = zmax - zmin;
        float zs[];
        if (hh > chf("../rail_seuil")) zs = array(zmin + 0.25 * hh, zmin + 0.75 * hh); else zs = array(zmin + 0.5 * hh);
        float rh = chf("../rail_h"), rp = chf("../rail_p");
        foreach (float zr; zs) {
            // largeur du rail = 80 % de la largeur intérieure de la plaque à cette hauteur
            float gx = 1e9, dx = -1e9;
            for (int i = 0; i < n; i++) {
                vector2 a = Qi[i], b = Qi[(i + 1) % n];
                if ((a.y - zr) * (b.y - zr) <= 0 && abs(b.y - a.y) > 1e-9) {
                    float xx = a.x + (zr - a.y) / (b.y - a.y) * (b.x - a.x);
                    gx = min(gx, xx); dx = max(dx, xx);
                }
            }
            if (dx <= gx) continue;
            float cx = 0.5 * (gx + dx), lx = 0.8 * (dx - gx);
            float yb = -tole, yf = -tole - rp;
            vector c4[] = array(set(cx - lx/2, yb, zr - rh/2), set(cx + lx/2, yb, zr - rh/2), set(cx + lx/2, yb, zr + rh/2), set(cx - lx/2, yb, zr + rh/2));
            vector c5[] = array(set(cx - lx/2, yf, zr - rh/2), set(cx + lx/2, yf, zr - rh/2), set(cx + lx/2, yf, zr + rh/2), set(cx - lx/2, yf, zr + rh/2));
            vector Pb[], Ub[];
            foreach (vector q; c5) { push(Pb, H(q)); push(Ub, set(q.x, q.z, 0)); }
            poly(Pb, Ub, H({0, -1, 0}), mr);
            vector nrm[] = array(set(0, 0, -1), set(1, 0, 0), set(0, 0, 1), set(-1, 0, 0));
            for (int f = 0; f < 4; f++) {
                int g = (f + 1) % 4;
                vector Pq[] = array(H(c4[f]), H(c4[g]), H(c5[g]), H(c5[f]));
                vector Uq[] = array(set(0, 0, 0), set(distance(c4[f], c4[g]), 0, 0), set(distance(c4[f], c4[g]), rp, 0), set(0, rp, 0));
                poly(Pq, Uq, H(nrm[f]), mr);
            }
        }
    }
}
"""


def hda_panneau():
    sub = O.sous_reseau("panneau")
    w = O.wrangle(sub, "plaques", VEX_PANNEAU, "detail")
    fus = sub.createNode("fuse::2.0", "souder_coincidents")
    fus.setInput(0, w)
    fus.parm("tol3d").set(1e-6)
    div = sub.createNode("divide", "polygones_convexes")      # plaques non convexes : faces triangulées proprement
    div.setInput(0, fus)
    div.parm("convex").set(1)
    O.chaine_finale(sub, div)
    sub.layoutChildren()
    parms = [
        S("contours", "Contours convexes (x z …, m ; plaques séparées par « | »)", 1,
          help="Contours relevés sur l'emprise opaque de la face officielle, à l'échelle de la gamme ; repère de la face."),
        F("img_x0", "Image : x du bord gauche (m)", 1, default_value=(0.0,)),
        F("img_z0", "Image : z du bord bas (m)", 1, default_value=(0.0,)),
        F("img_l", "Image : largeur (m)", 1, default_value=(1.0,)),
        F("img_h", "Image : hauteur (m)", 1, default_value=(1.0,)),
        F("bord_tombe", "Profondeur du bord tombé (m)", 1, default_value=(0.025,)),
        F("rebord", "Largeur du rebord arrière (m)", 1, default_value=(0.012,)),
        F("tole", "Épaisseur de la tôle (m)", 1, default_value=(0.002,)),
        TG("rails", "Rails de fixation au dos", default_value=True),
        F("rail_seuil", "Hauteur de plaque au-delà de laquelle on pose 2 rails (m)", 1, default_value=(0.45,)),
        F("rail_h", "Rail : hauteur (m)", 1, default_value=(0.03,)),
        F("rail_p", "Rail : saillie (m)", 1, default_value=(0.022,)),
        S("materiau_face", "Matériau de la face", 1, default_value=("face_panneau",)),
        S("materiau_revers", "Matériau du revers et du bord tombé", 1, default_value=("revers_panneau",)),
    ] + O.parms_communs(cusp=30.0, materiau="revers_panneau")
    return O.creer_hda(sub, "panneau", "Route Panneau de signalisation (plaque à bord tombé)", parms,
                       aide="Plaque(s) à bord tombé, face à UV 0-1 sur la face officielle, revers creux, rails de fixation.")


CONSTRUCTEURS = dict(assemblage=hda_assemblage, panneau=hda_panneau)


def construire(noms=None):
    out = {}
    for n, f in CONSTRUCTEURS.items():
        if noms and n not in noms:
            continue
        out[n] = f()
        print("HDA", n, "->", out[n])
    return out


if __name__ == "__main__":
    construire()
