"""Décor du rendu soigné (lot L2b, corrigé après contrôle ; hython) : arbres procéduraux AUX DIMENSIONS DU MODÈLE,
prolongements de la route hors de l'emprise, sol de décor raccordé, fond de montagnes. Construction par nœuds SOP et
VEX (script de construction) ; rien de ce décor n'est une donnée de la route.

ÉTAPE 1 (décision de l'utilisateur, 17/10/2026 : « il ne doit pas générer la montagne : il doit générer les routes, la
chaussée, etc. dans un premier temps ; la végétation, c'est dans un deuxième temps ») : par défaut, le rendu ne pose
RIEN de ce décor (ni arbres, ni montagnes, ni prairie, ni prolongements) ; il n'utilise que le SOCLE de présentation
(`socle_jupe`, `sol_plat`) : la route fabriquée s'arrête à la limite extérieure de son profil (abords du modèle non
rendus) et en s = 0 et s = L par une coupe verticale nette jusqu'à un sol plat, neutre et uni. Le code du décor
(arbres, prolongements, sol de décor, montagnes) est gardé tel quel pour l'étape 2 (option `--decor-etape2` du pilote).

Arbres (correction après contrôle : le gabarit fixe — fût 3,4 m, cartes de feuilles de 0,55 m, houppier ignoré — est
remplacé) : chaque arbre du modèle (objets_le_long, famille vegetation) porte son essence (asset_id, fiche de
assets/specs/vegetation.json), sa hauteur, le rayon de son houppier et la hauteur de ses premières branches (fut_m,
gabarit RF-OSM-VEG-001 : 3,80 m au-dessus de la chaussée, 2,50 m au-dessus d'un trottoir), posés par le compilateur
(description_vers_modele.gabarit_arbre). Le VEX construit : tronc conique lissé (14 côtés, empattement), charpentières
insérées à partir du fût et toujours montantes, branches secondaires et rameaux, le tout contenu dans l'ellipsoïde du
houppier (rayon horizontal = houppier_rayon_m, de fut_m à hauteur_m) ; grappes de feuilles en cartes de 0,08 à 0,15 m
(taille de la feuille de la fiche) le long des rameaux, aucune sous le fût ; saison lue dans meta.date (hiver : nu).
Arbres de décor (hors emprise) : feuillu générique de la fiche (10 m, fût 2,5 m, houppier 3 m), variations ± 15 %.

Prolongements : le profil d'extrémité du sol fabriqué (sol, bordures, caniveaux : rayons verticaux au pas de 2 cm) est
extrudé tout droit selon la tangente de la référence sur 400 m de chaque côté (sans marquage : décor), et le trou du
sol de décor suit le sol et ses prolongements : la route ne s'arrête plus net dans le champ, sans couture.
Fond : anneau de relief de 4,5 à 12 km (hauteurs 300-1 600 m, bruit déterministe), voile d'atmosphère dans l'albédo.
"""
import json
import math
from pathlib import Path

import hou

DEPOT = Path(__file__).resolve().parents[3]
VEGETATION_JSON = DEPOT / "assets" / "specs" / "vegetation.json"
PROLONGEMENT_M = 400.0

VEX_ARBRE = r"""
// arbre v2 (détail) : dimensions du modèle ; paramètres de l'hôte. Y haut, pied du tronc à l'origine.
function float ell(vector p; float R; float a; float yc) { return (p.x * p.x + p.z * p.z) / (R * R) + (p.y - yc) * (p.y - yc) / (a * a); }
// distance de p à la surface de l'ellipsoïde selon d (p intérieur)
function float vers_bord(vector p; vector d; float R; float a; float yc) {
    vector q = set(p.x / R, (p.y - yc) / a, p.z / R);
    vector e = set(d.x / R, d.y / a, d.z / R);
    float A = dot(e, e), B = 2 * dot(q, e), C = dot(q, q) - 1;
    float D = B * B - 4 * A * C;
    if (D < 0 || A < 1e-12) return 0.0;
    return max(0.0, (-B + sqrt(D)) / (2 * A));
}
function void tube(vector C[]; float RR[]; int nr; string mat) {
    int prev[];
    float lc = 0;
    vector ax0 = {1, 0, 0};
    for (int k = 0; k < len(C); k++) {
        vector t = normalize(k < len(C) - 1 ? C[k + 1] - C[k] : C[k] - C[k - 1]);
        vector ax = normalize(ax0 - dot(ax0, t) * t);              // repère transporté (pas de torsion brusque)
        if (length(ax) < 1e-6) ax = normalize(cross(t, {0, 0, 1}));
        ax0 = ax;
        vector bx = cross(t, ax);
        if (k > 0) lc += length(C[k] - C[k - 1]);
        int ring[];
        for (int j = 0; j <= nr; j++) {
            float th = 2 * PI * j / nr;
            push(ring, addpoint(0, C[k] + RR[k] * (cos(th) * ax + sin(th) * bx)));
        }
        if (k > 0) {
            float lk = length(C[k] - C[k - 1]);
            for (int j = 0; j < nr; j++) {
                int f = addprim(0, "poly", prev[j], ring[j], ring[j + 1], prev[j + 1]);
                setprimattrib(0, "materiau_id", f, mat);
                float c0 = 2 * PI * RR[k - 1], c1 = 2 * PI * RR[k];
                setvertexattrib(0, "uv", f, 0, set(c0 * j / nr, lc - lk, 0));
                setvertexattrib(0, "uv", f, 1, set(c1 * j / nr, lc, 0));
                setvertexattrib(0, "uv", f, 2, set(c1 * (j + 1) / nr, lc, 0));
                setvertexattrib(0, "uv", f, 3, set(c0 * (j + 1) / nr, lc - lk, 0));
            }
        }
        prev = ring;
    }
}
function void carte(vector c; vector n0; float s; string mat; int g) {
    vector nn = normalize(n0);
    vector ta = normalize(cross(nn, abs(nn.y) < 0.9 ? set(0, 1, 0) : set(1, 0, 0)));
    float rot = 2 * PI * rand(g * 13 + 5);
    ta = normalize(ta * cos(rot) + cross(nn, ta) * sin(rot));
    vector tb = cross(nn, ta);
    int a0 = addpoint(0, c - 0.5 * s * ta - 0.5 * s * tb);
    int a1 = addpoint(0, c + 0.5 * s * ta - 0.5 * s * tb);
    int a2 = addpoint(0, c + 0.5 * s * ta + 0.5 * s * tb);
    int a3 = addpoint(0, c - 0.5 * s * ta + 0.5 * s * tb);
    int f = addprim(0, "poly", a0, a1, a2, a3);
    setprimattrib(0, "materiau_id", f, mat);
    setvertexattrib(0, "uv", f, 0, {0, 0, 0});
    setvertexattrib(0, "uv", f, 1, {1, 0, 0});
    setvertexattrib(0, "uv", f, 2, {1, 1, 0});
    setvertexattrib(0, "uv", f, 3, {0, 1, 0});
}
int seed = chi("graine");
float H = chf("hauteur"), F = chf("fut"), R = chf("houppier"), r0 = chf("rayon_tronc"), TF = chf("taille_feuilles");
int avec_feuilles = chi("feuilles");
string mat_e = chs("materiau_ecorce"), mat_f = chs("materiau_feuilles");
addprimattrib(0, "materiau_id", "");
addvertexattrib(0, "uv", {0, 0, 0});
float a = 0.5 * (H - F);
float yc = F + a;
int g = seed * 104729 + 17;
// ---- tronc conique lissé (empattement au pied), légère inclinaison
float ytop = F + 0.72 * (H - F);
vector Ct[];
float Rt[];
int nt = 14;
vector lean = 0.025 * set(rand(g + 1) - 0.5, 0, rand(g + 2) - 0.5);
for (int k = 0; k <= nt; k++) {
    float u = float(k) / nt;
    float y = ytop * u;
    push(Ct, set(0, y, 0) + lean * y + 0.04 * set(sin(7.1 * u + seed), 0, cos(5.3 * u + seed)) * u);
    float rr = r0 * (1.0 - 0.72 * u);
    if (y < 0.5) rr *= 1.0 + 0.35 * (1.0 - y / 0.5) * (1.0 - y / 0.5);
    push(Rt, rr);
}
tube(Ct, Rt, 14, mat_e);
// ---- charpentières : insérées de F à F + 0,55 (H − F), montantes
int N = 5 + (seed % 3);
for (int i = 0; i < N; i++) {
    g += 31;
    float yi = F + (H - F) * (0.02 + 0.55 * float(i) / max(N - 1, 1)) + 0.15 * (rand(g) - 0.5) * (H - F) / N;
    yi = max(yi, F);
    float ui = clamp(yi / ytop, 0.0, 1.0);
    vector Pi = set(0, yi, 0) + lean * yi;
    float rp = r0 * (1.0 - 0.72 * ui);
    float phi = i * 2.39996 + 2 * PI * rand(seed * 3 + 1) + 0.4 * (rand(g + 1) - 0.5);
    float th = radians(28 + 32 * float(i) / max(N - 1, 1) + 10 * (rand(g + 2) - 0.5));
    vector d = normalize(set(cos(th) * cos(phi), sin(th), cos(th) * sin(phi)));
    float Lc = 0.92 * vers_bord(Pi, d, R, a, yc);
    if (Lc < 0.6) continue;
    vector Cc[];
    float Rc[];
    int ns = 7;
    vector q = Pi;
    vector dd = d;
    float rb = rp * 0.58;
    push(Cc, q); push(Rc, rb);
    for (int k = 1; k <= ns; k++) {
        g++;
        dd = normalize(dd + set(0, 0.06, 0) + 0.10 * (set(rand(g), rand(g + 3), rand(g + 5)) - 0.5));
        q += dd * Lc / ns;
        push(Cc, q); push(Rc, rb * (1.0 - 0.8 * float(k) / ns) + 0.006);
    }
    tube(Cc, Rc, 8, mat_e);
    if (avec_feuilles) {
        for (float u3 = 0.45; u3 <= 1.0; u3 += 0.03) {
            g += 3;
            int k3 = clamp(int(u3 * ns), 0, ns - 1);
            vector c = lerp(Cc[k3], Cc[k3 + 1], u3 * ns - k3) + 0.25 * set(rand(g + 1) - 0.5, rand(g + 2) - 0.5, rand(g + 3) - 0.5);
            if (c.y < F + 0.15 || ell(c, R, a, yc) > 1.0) continue;
            carte(c, set(rand(g + 4) - 0.5, 0.6, rand(g + 6) - 0.5), TF * fit01(rand(g + 7), 0.8, 1.25), mat_f, g);
        }
    }
    // secondaires
    int M = 10 + int(5 * rand(g + 7));
    for (int m = 0; m < M; m++) {
        g += 7;
        float fr = 0.25 + 0.7 * float(m) / M + 0.05 * rand(g);
        int ks = clamp(int(fr * ns), 0, ns - 1);
        vector Ps = lerp(Cc[ks], Cc[ks + 1], fr * ns - ks);
        vector pd = normalize(Cc[ks + 1] - Cc[ks]);
        vector ax = normalize(cross(pd, set(rand(g + 1) - 0.5, rand(g + 2) - 0.5, rand(g + 3) - 0.5)));
        vector sd = normalize(qrotate(quaternion(radians(30 + 30 * rand(g + 4)), ax), pd) + set(0, 0.15, 0));
        if (sd.y < 0.05) sd = normalize(sd + set(0, 0.25, 0));
        float Ls = clamp(0.75 * vers_bord(Ps, sd, R, a, yc), 0.0, 0.55 * Lc + 0.6);
        if (Ls < 0.25) continue;
        vector Cs[];
        float Rs[];
        int nss = 4;
        vector qs = Ps;
        float rs = max(Rc[ks] * 0.5, 0.008);
        push(Cs, qs); push(Rs, rs);
        for (int k = 1; k <= nss; k++) {
            g++;
            sd = normalize(sd + 0.12 * (set(rand(g), rand(g + 3), rand(g + 5)) - 0.5) + set(0, 0.03, 0));
            qs += sd * Ls / nss;
            push(Cs, qs); push(Rs, rs * (1.0 - 0.75 * float(k) / nss) + 0.003);
        }
        tube(Cs, Rs, 5, mat_e);
        // rameaux et feuilles
        int T = 9 + int(5 * rand(g + 9));
        for (int tq = 0; tq < T; tq++) {
            g += 5;
            float ft = 0.3 + 0.7 * float(tq) / T;
            int kt = clamp(int(ft * nss), 0, nss - 1);
            vector Pt = lerp(Cs[kt], Cs[kt + 1], ft * nss - kt);
            vector td = normalize(Cs[kt + 1] - Cs[kt]);
            vector ax2 = normalize(cross(td, set(rand(g + 1) - 0.5, rand(g + 2) - 0.5, rand(g + 3) - 0.5)));
            vector tdd = normalize(qrotate(quaternion(radians(35 + 35 * rand(g + 4)), ax2), td) + set(0, 0.1, 0));
            float Lt = min(0.25 + 0.5 * rand(g + 6), 0.9 * vers_bord(Pt, tdd, R, a, yc));
            if (Lt < 0.08) continue;
            vector Ce[];
            float Re[];
            push(Ce, Pt); push(Re, 0.006);
            push(Ce, Pt + tdd * Lt); push(Re, 0.003);
            tube(Ce, Re, 3, mat_e);
            if (!avec_feuilles) continue;
            int nf = int(Lt / 0.02) + 8;
            for (int jf = 0; jf < nf; jf++) {
                g += 3;
                vector c = Pt + tdd * Lt * (0.1 + 0.9 * float(jf) / nf)
                           + 0.11 * set(rand(g + 1) - 0.5, rand(g + 2) - 0.5, rand(g + 3) - 0.5);
                if (c.y < F + 0.15 || ell(c, R, a, yc) > 1.0) continue;
                vector nn = set(rand(g + 4) - 0.5, rand(g + 5) * 0.8 + 0.2, rand(g + 6) - 0.5);
                carte(c, nn, TF * fit01(rand(g + 7), 0.8, 1.25), mat_f, g);
            }
        }
        // grappes le long de la moitié extérieure de la secondaire
        if (avec_feuilles) {
            for (float u2 = 0.35; u2 <= 1.0; u2 += 0.04) {
                g += 3;
                int k2 = clamp(int(u2 * nss), 0, nss - 1);
                vector c = lerp(Cs[k2], Cs[k2 + 1], u2 * nss - k2) + 0.12 * set(rand(g + 1) - 0.5, rand(g + 2) - 0.5, rand(g + 3) - 0.5);
                if (c.y < F + 0.15 || ell(c, R, a, yc) > 1.0) continue;
                carte(c, set(rand(g + 4) - 0.5, 0.7, rand(g + 6) - 0.5), TF * fit01(rand(g + 7), 0.8, 1.25), mat_f, g);
            }
        }
    }
}
// cime : prolongement du tronc en flèche fine
vector Cf[];
float Rf[];
push(Cf, Ct[-1]); push(Rf, Rt[-1]);
push(Cf, set(0, F + 0.92 * (H - F), 0) + lean * H); push(Rf, 0.01);
tube(Cf, Rf, 6, mat_e);
"""

VEX_POSER = r"""
// pose des arbres (point) : Z du sol fabriqué ou du décor sous l'arbre (rayon vertical, entrée 1) ; lacet déterministe
// (graine = hachage de l'identifiant), prototype par la graine ; échelle 1 pour les arbres du modèle (dimensions exactes),
// ± 15 % pour le décor
vector hit, uvw;
int pr = intersect(1, set(@P.x, 100.0, @P.z), {0, -200, 0}, hit, uvw);
if (pr >= 0) @P.y = hit.y;
int g = random_shash(s@id) & 0x7fffffff;
f@pscale = chi("modele") ? 1.0 : fit01(rand(g % 100003), 0.85, 1.15);
f@lacet = 2 * PI * rand((g + 7) % 100003);
p@orient = quaternion(f@lacet, {0, 1, 0});
s@variante = sprintf("v%d", g % 3);
"""

VEX_DECOR = r"""
// positions des arbres de décor (détail) : hors de l'emprise du modèle (au-delà des abords + marge), le long de la route
// et de ses prolongements ; espacement irrégulier déterministe ; « campagne » : plus épars ; second rang plus loin.
float L = chf("longueur"), P = chf("prolongement");
float tg = chf("t_gauche"), td = chf("t_droite");
float marge = chf("marge");
int rural = chi("rural");
addpointattrib(0, "id", "");
addpointattrib(0, "s", 0.0);
addpointattrib(0, "t", 0.0);
for (int rang = 0; rang < 2; rang++) {
    for (int cote = 0; cote < 2; cote++) {
        float pas = (rural ? 22.0 : 14.0) * (rang ? 0.8 : 1.0);
        int n = int(ceil((L + 2 * P) / pas));
        for (int k = 0; k <= n; k++) {
            int g = 7919 * (k + 1) + 104729 * (cote + 1) + 15485863 * (rang + 1) + chi("graine");
            if (rand(g) < (rural ? 0.35 : 0.15)) continue;
            float s = -P + k * pas + (rand(g + 1) - 0.5) * pas * 0.8;
            float dt = rang == 0 ? (cote == 0 ? marge - 1.0 + 3.0 * rand(g + 2) : marge + 6.0 + 4.0 * rand(g + 2))
                                 : 18.0 + 25.0 * rand(g + 2);
            float t = cote == 0 ? tg + dt : td - dt;
            if (rang == 0 && cote == 1 && s > chf("s_libre") - 16.0 && s < chf("s_libre") + 20.0) continue;
            int p = addpoint(0, set(0, 0, 0));
            setpointattrib(0, "id", p, sprintf("decor_%d_%d_%03d", rang, cote, k));
            setpointattrib(0, "s", p, s);
            setpointattrib(0, "t", p, t);
        }
    }
}
"""

VEX_ST_XY = r"""
// (s, t) -> (x, y) : référence prolongée par ses tangentes au-delà des bouts (entrée 1 : références de rg::graphe)
int pts[] = primpoints(1, 0);
int n = len(pts);
float s = f@s;
float L = point(1, "s", pts[n - 1]);
int i = 0;
while (i < n - 2 && point(1, "s", pts[i + 1]) <= s) i++;
float sa = point(1, "s", pts[i]), sb = point(1, "s", pts[i + 1]);
float a = (s - sa) / max(sb - sa, 1e-9);
vector P = lerp(vector(point(1, "P", pts[i])), vector(point(1, "P", pts[i + 1])), a);
vector g = normalize(lerp(vector(point(1, "gauche", pts[i])), vector(point(1, "gauche", pts[i + 1])), a));
@P = P + f@t * g;
"""

VEX_PROLONGEMENTS = r"""
// prolongements (détail) : aux deux bouts de la route, profil du dessus fabriqué (entrée 1 : sol + bordures +
// caniveaux, rayons verticaux à 2 cm à l'intérieur du bout, pas de 2 cm en t, de la rive gauche à la rive droite du
// sol) extrudé tout droit selon la tangente de la référence (entrée 2) sur D mètres ; marches > 5 mm en murs
// verticaux ; materiau_id de la surface touchée (mur : celui du haut) ; UV en mètres (x, y).
float D = chf("longueur");
float pas = chf("pas_t");
addprimattrib(0, "materiau_id", "");
addprimattrib(0, "bout", 0);
addvertexattrib(0, "uv", {0, 0, 0});
int rp[] = primpoints(2, 0);
int n = len(rp);
float L = point(2, "s", rp[n - 1]);
for (int bout = 0; bout < 2; bout++) {
    int i0 = bout ? n - 1 : 0, i1 = bout ? n - 2 : 1;
    vector P0 = point(2, "P", rp[i0]);
    vector G = normalize(vector(point(2, "gauche", rp[i0])));
    vector T = normalize(vector(point(2, "P", rp[i0])) - vector(point(2, "P", rp[i1])));   // vers l'extérieur
    // bornes en t du sol à ce bout (points du sol, entrée 1 non : entrée 3 = sol seul)
    float tmin = 1e9, tmax = -1e9;
    for (int p = 0; p < npoints(3); p++) {
        float sp = point(3, "s", p);
        if (abs(sp - (bout ? L : 0.0)) > 1e-4) continue;
        float tp = point(3, "t", p);
        tmin = min(tmin, tp); tmax = max(tmax, tp);
    }
    if (tmax <= tmin) continue;
    int ns = int(ceil((tmax - tmin) / pas));
    float tt[], zz[];
    string mm[];
    for (int k = 0; k <= ns; k++) {
        float t = tmax - (tmax - tmin) * k / ns;
        vector Q = P0 + t * G - T * 0.02;
        vector hit, uvw;
        int pr = intersect(1, set(Q.x, Q.y + 50.0, Q.z), {0, -100, 0}, hit, uvw);
        if (pr < 0) continue;
        string mt = prim(1, "materiau_id", pr);
        push(tt, t); push(zz, hit.y); push(mm, mt);
    }
    // polyligne du profil avec marches verticales
    float vt[], vz[];
    string vm[];
    for (int k = 0; k < len(tt); k++) {
        if (k > 0 && abs(zz[k] - zz[k - 1]) > 0.005) {
            push(vt, tt[k]); push(vz, zz[k - 1]); push(vm, zz[k] > zz[k - 1] ? mm[k] : mm[k - 1]);
        }
        push(vt, tt[k]); push(vz, zz[k]); push(vm, mm[k]);
    }
    // tronçons de longueur croissante (1 m près du bout, 25 m au-delà de 100 m) : aucune face longue et effilée
    float SL[];
    float sl = 0;
    while (sl < D - 1e-6) { push(SL, sl); sl += sl < 20 ? 1.0 : (sl < 100 ? 5.0 : 25.0); }
    push(SL, D);
    int prev[];
    foreach (int js; float dl; SL) {
        int row[];
        foreach (int k; float t; vt) {
            vector A = P0 + t * G + T * dl;
            A.y = vz[k];
            push(row, addpoint(0, A));
        }
        if (js > 0) {
            for (int k = 0; k + 1 < len(vt); k++) {
                int f = bout ? addprim(0, "poly", prev[k], prev[k + 1], row[k + 1], row[k])
                             : addprim(0, "poly", prev[k], row[k], row[k + 1], prev[k + 1]);
                setprimattrib(0, "materiau_id", f, vm[k + 1]);
                setprimattrib(0, "bout", f, bout);
            }
        }
        prev = row;
    }
}
"""

VEX_UV_XY = r"""
// UV en mètres (x, y locaux)
v@uv = set(@P.x, -@P.z, 0);
"""

VEX_ANNEAU = r"""
// sol de décor (détail ; entrée 1 : sol fabriqué, entrée 2 : références) : bord extérieur du sol chaîné en boucle ; les
// deux bouts (points d'abscisse 0 et L) sont remplacés par l'emprise des prolongements (rectangle de longueur D selon
// la tangente) ; carré de demi-côté R avec cette boucle en trou (Triangulate 2D ensuite) ; Z de la boucle = Z exact du
// bord du sol, Z du carré = moyenne de la boucle
int src[], dst[];
for (int h = 0; h < nvertices(1); h++) {
    if (!hedge_isvalid(1, h)) continue;
    if (hedge_equivcount(1, h) != 1) continue;
    push(src, hedge_srcpoint(1, h));
    push(dst, hedge_dstpoint(1, h));
}
if (len(src) < 3) return;
int vu[];
resize(vu, len(src));
int best[];
for (int i0 = 0; i0 < len(src); i0++) {
    if (vu[i0]) continue;
    int boucle[];
    int i = i0;
    while (i >= 0 && !vu[i]) {
        vu[i] = 1;
        push(boucle, src[i]);
        i = find(src, dst[i]);
    }
    if (len(boucle) > len(best)) best = boucle;
}
float D = chf("prolongement");
int rp[] = primpoints(2, 0);
int nr = len(rp);
float L = point(2, "s", rp[nr - 1]);
vector Td[];
push(Td, normalize(vector(point(2, "P", rp[0])) - vector(point(2, "P", rp[1]))));
push(Td, normalize(vector(point(2, "P", rp[nr - 1])) - vector(point(2, "P", rp[nr - 2]))));
// boucle de positions, bouts remplacés
vector Pb[];
int nb = len(best);
// point de départ hors des bouts
int dep = 0;
for (int i = 0; i < nb; i++) {
    float s = point(1, "s", best[i]);
    if (s > 1e-4 && s < L - 1e-4) { dep = i; break; }
}
int i = 0;
while (i < nb) {
    int p = best[(dep + i) % nb];
    float s = point(1, "s", p);
    int bout = s <= 1e-4 ? 0 : (s >= L - 1e-4 ? 1 : -1);
    if (bout < 0 || D <= 0) { push(Pb, vector(point(1, "P", p))); i++; continue; }
    int j = i;
    while (j + 1 < nb) {
        float s2 = point(1, "s", best[(dep + j + 1) % nb]);
        if ((bout == 0 && s2 > 1e-4) || (bout == 1 && s2 < L - 1e-4)) break;
        j++;
    }
    vector A = point(1, "P", p), B = point(1, "P", best[(dep + j) % nb]);
    push(Pb, A); push(Pb, A + Td[bout] * D); push(Pb, B + Td[bout] * D); push(Pb, B);
    i = j + 1;
}
float R = chf("demi_cote");
vector c = 0;
float zm = 0;
foreach (vector P; Pb) { c += P; zm += P.y; }
c /= len(Pb);
zm /= len(Pb);
int ext[];
push(ext, addpoint(0, set(c.x - R, zm, c.z - R)));
push(ext, addpoint(0, set(c.x + R, zm, c.z - R)));
push(ext, addpoint(0, set(c.x + R, zm, c.z + R)));
push(ext, addpoint(0, set(c.x - R, zm, c.z + R)));
int pe = addprim(0, "poly", ext);
setprimattrib(0, "anneau", pe, 0);
float aire = 0;
for (int k = 0; k < len(Pb); k++) {
    vector A = Pb[k], B = Pb[(k + 1) % len(Pb)];
    aire += A.x * B.z - B.x * A.z;
}
if (aire <= 0) Pb = reverse(Pb);
int trou[];
foreach (vector P; Pb) push(trou, addpoint(0, P));
int pt = addprim(0, "poly", trou);
setprimattrib(0, "anneau", pt, 1);
// points de Steiner en grilles graduées autour de l'emprise (2 m jusqu'à 30 m, 10 m jusqu'à 200 m, 50 m jusqu'à
// 1 km, 250 m au-delà) : triangles de taille bornée (un triangle de plusieurs kilomètres, long et effilé, n'est pas
// rendu par Karma XPU : stries diagonales dans l'herbe du décor, essai tmp/correction/essai_crenelage.py)
vector bmin = Pb[0], bmax = Pb[0];
foreach (vector P; Pb) { bmin = min(bmin, P); bmax = max(bmax, P); }
float PAS[] = array(2.0, 10.0, 50.0, 250.0);
float MARGE[] = array(30.0, 200.0, 1000.0, R);
for (int k = 0; k < len(PAS); k++) {
    float x0 = max(c.x - R, bmin.x - MARGE[k]), x1 = min(c.x + R, bmax.x + MARGE[k]);
    float z0 = max(c.z - R, bmin.z - MARGE[k]), z1 = min(c.z + R, bmax.z + MARGE[k]);
    float xi0 = k > 0 ? bmin.x - MARGE[k - 1] : 1e18, xi1 = k > 0 ? bmax.x + MARGE[k - 1] : -1e18;
    float zi0 = k > 0 ? bmin.z - MARGE[k - 1] : 1e18, zi1 = k > 0 ? bmax.z + MARGE[k - 1] : -1e18;
    for (float x = x0 + 0.5 * PAS[k]; x < x1; x += PAS[k])
        for (float z = z0 + 0.5 * PAS[k]; z < z1; z += PAS[k]) {
            if (x > xi0 && x < xi1 && z > zi0 && z < zi1) continue;      // déjà couvert par la grille plus fine
            if (abs(x - c.x) > R - 1 || abs(z - c.z) > R - 1) continue;
            // trop près de la boucle : pas de point (triangles plats)
            float dmin = 1e18;
            if (k == 0) foreach (vector P; Pb) dmin = min(dmin, (P.x - x) * (P.x - x) + (P.z - z) * (P.z - z));
            if (dmin < 0.25 * PAS[k] * PAS[k]) continue;
            addpoint(0, set(x, zm, z));
        }
}
"""

VEX_ANNEAU_TROU = r"""
// triangles sous le sol fabriqué ou sous un prolongement retirés (entrée 1) : rayon vertical au centre du triangle
int pts[] = primpoints(0, @primnum);
vector cc = 0;
foreach (int p; pts) cc += point(0, "P", p);
cc /= max(1, len(pts));
vector hit, uvw;
int pr = intersect(1, set(cc.x, cc.y + 50.0, cc.z), {0, -100, 0}, hit, uvw);
if (pr >= 0) removeprim(0, @primnum, 1);
"""

VEX_COTE_ABORD = r"""
// matériau du sol de décor de chaque côté de la route : celui de l'abord du modèle (rive gauche / droite) : même
// matériau et mêmes UV (mètres) que l'abord, aucune couture (relecture adverse)
int pts[] = primpoints(0, @primnum);
vector cc = 0;
foreach (int p; pts) cc += point(0, "P", p);
cc /= max(1, len(pts));
int rp[] = primpoints(1, 0);
float best = 1e18; int ib = 0;
for (int i = 0; i < len(rp); i++) {
    vector P = point(1, "P", rp[i]);
    float d = (P.x - cc.x) * (P.x - cc.x) + (P.z - cc.z) * (P.z - cc.z);
    if (d < best) { best = d; ib = i; }
}
vector P = point(1, "P", rp[ib]);
vector G = point(1, "gauche", rp[ib]);
s@materiau_id = dot(cc - P, G) >= 0 ? chs("mat_gauche") : chs("mat_droite");
"""

VEX_MONTAGNES = r"""
// fond de relief (détail) : anneaux de 3,5 à 13 km autour du centre (24 anneaux) ; ligne de crête vers 7-9 km, hauteur
// 500-1 900 m (bruit « ridged » périodique en azimut) modulée par un bruit 2D (azimut, rayon) : croupes, vallons et
// ravines qui accrochent la lumière ; graine fixe ; décor, aucune donnée.
vector c = chv("centre");
int N = 1440, M = 24;
float R0 = 3500.0, R1 = 13000.0;
addprimattrib(0, "materiau_id", "");
addvertexattrib(0, "uv", {0, 0, 0});
function float b1(int x; int g) { return rand(x * 7919 + g); }
function float bruit_az(float u; int graine; float f0; int oct; float pers) {
    float h = 0, amp = 1.0, tot = 0;
    for (int o = 0; o < oct; o++) {
        float f = f0 * pow(2, o);
        float x = u * f;
        int x0 = int(floor(x));
        float t = x - x0;
        t = t * t * (3 - 2 * t);
        int fi = int(f);
        h += amp * lerp(b1(x0 % fi, o * 104729 + graine), b1((x0 + 1) % fi, o * 104729 + graine), t);
        tot += amp;
        amp *= pers;
    }
    return h / tot;
}
function float bruit_2d(float u; float v; int graine; float fu; float fv; int oct) {
    float h = 0, amp = 1.0, tot = 0;
    for (int o = 0; o < oct; o++) {
        float su = fu * pow(2, o), sv = fv * pow(2, o);
        float x = u * su, y = v * sv;
        int x0 = int(floor(x)), y0 = int(floor(y));
        float tx = x - x0, ty = y - y0;
        tx = tx * tx * (3 - 2 * tx); ty = ty * ty * (3 - 2 * ty);
        int fi = int(su);
        float a = rand((x0 % fi) * 7919 + y0 * 104729 + o * 15485863 + graine);
        float b = rand(((x0 + 1) % fi) * 7919 + y0 * 104729 + o * 15485863 + graine);
        float cc = rand((x0 % fi) * 7919 + (y0 + 1) * 104729 + o * 15485863 + graine);
        float d = rand(((x0 + 1) % fi) * 7919 + (y0 + 1) * 104729 + o * 15485863 + graine);
        h += amp * lerp(lerp(a, b, tx), lerp(cc, d, tx), ty);
        tot += amp;
        amp *= 0.55;
    }
    return h / tot;
}
int ids[];
for (int k = 0; k <= M; k++) {
    float v = float(k) / M;
    float rr = R0 + (R1 - R0) * v;
    // profil radial : pied (k = 0) au sol, crête vers 40 % (≈ 7 km), décroissance au-delà
    float prof = (k == 0) ? 0.0 : smooth(0.0, 0.40, v) * (1.0 - 0.55 * smooth(0.45, 1.0, v));
    for (int i = 0; i <= N; i++) {
        float u = float(i % N) / N;
        float h = bruit_az(u, chi("graine"), 9.0, 7, 0.55);
        float cr = 1.0 - abs(2.0 * h - 1.0);
        float H = 500 + 1400 * pow(clamp(0.5 * h + 0.5 * cr, 0, 1), 1.5);
        // croupes plus larges, ravines moins marquées et plus courtes en rayon (revue des tuiles : « peigne » de
        // stries verticales)
        float rel = bruit_2d(u, v, chi("graine") + 77, 48.0, 12.0, 5);
        float rav = 1.0 - abs(2.0 * bruit_2d(u, v, chi("graine") + 91, 192.0, 12.0, 3) - 1.0);
        float y = (k == 0) ? -2.0 : H * prof * (0.78 + 0.30 * rel) * (0.96 + 0.04 * rav);
        float ph = 2 * PI * u;
        push(ids, addpoint(0, c + set(cos(ph) * rr, y, -sin(ph) * rr)));
    }
}
for (int k = 0; k < M; k++) {
    for (int i = 0; i < N; i++) {
        int a0 = ids[k * (N + 1) + i], a1 = ids[k * (N + 1) + i + 1];
        int b0 = ids[(k + 1) * (N + 1) + i], b1_ = ids[(k + 1) * (N + 1) + i + 1];
        int f = addprim(0, "poly", a0, b0, b1_, a1);
        setprimattrib(0, "materiau_id", f, "montagne");
        int pts[] = array(a0, b0, b1_, a1);
        foreach (int j; int q; pts) {
            vector P = point(0, "P", q);
            float uu = (j == 0 || j == 1) ? 24.0 * i / N : 24.0 * (i + 1) / N;   // tuile ≈ 1,8 km × 1,9 km
            setvertexattrib(0, "uv", f, j, set(uu, clamp((P.y - c.y) / 1900.0, 0.0, 0.999), 0));
        }
    }
}
"""


# ------------------------------------------------------------------------------------------- utilitaires
def _wrangle(parent, nom, code, classe, entree=None, entrees=()):
    w = parent.node(nom) or parent.createNode("attribwrangle", nom)
    w.parm("class").set({"detail": 0, "primitive": 1, "point": 2, "sommet": 3}[classe])
    w.parm("snippet").set(code)
    if entree is not None:
        w.setInput(0, entree)
    for k, e in enumerate(entrees):
        w.setInput(k + 1, e)
    return w


def _parms(w, entiers=(), flottants=(), chaines=(), vecteurs=()):
    tg = w.parmTemplateGroup()
    for n, v in entiers:
        if tg.find(n) is None:
            tg.append(hou.IntParmTemplate(n, n, 1, default_value=(int(v),)))
    for n, v in flottants:
        if tg.find(n) is None:
            tg.append(hou.FloatParmTemplate(n, n, 1, default_value=(float(v),)))
    for n, v in chaines:
        if tg.find(n) is None:
            tg.append(hou.StringParmTemplate(n, n, 1, default_value=(str(v),)))
    for n, v in vecteurs:
        if tg.find(n) is None:
            tg.append(hou.FloatParmTemplate(n, n, 3, default_value=tuple(float(x) for x in v)))
    w.setParmTemplateGroup(tg)
    return w


# ------------------------------------------------------------------------------------------- arbres
_FICHES = None


def fiche(asset):
    """Fiche d'essence de assets/specs/vegetation.json (lecture seule) : couleur d'été / d'automne, rayon du tronc,
    taille des feuilles (cartes : environ 2 feuilles), fût et dimensions par défaut."""
    global _FICHES
    if _FICHES is None:
        _FICHES = {e["asset"]: e for e in json.loads(VEGETATION_JSON.read_text(encoding="utf-8"))["essences"]}
    e = _FICHES.get(asset) or _FICHES["arbre_feuillu_generique_moyen"]
    import re
    tr = re.findall(r"(\d+,\d+)", e.get("tronc") or "")
    d = [float(x.replace(",", ".")) for x in tr[:2]]
    r0 = (sum(d) / len(d) / 2.0) if d else 0.17
    fc = re.findall(r"(\d+)", str((e.get("gabarit") or {}).get("feuille_cm") or ""))
    feuille = (sum(float(x) for x in fc[:2]) / len(fc[:2]) / 100.0) if fc else 0.06
    carte = min(max(2.0 * feuille, 0.08), 0.15)
    g = e.get("gabarit") or {}

    def nb(v, d):
        try:
            return float(str(v).replace(",", "."))
        except (TypeError, ValueError):
            return d
    return {"asset": e["asset"], "ete": (e.get("feuillage") or {}).get("ete_srgb", "#4C7A30"),
            "automne": (e.get("feuillage") or {}).get("automne_srgb", "#B8962E"), "rayon_tronc": round(r0, 4),
            "carte_feuilles": round(carte, 4), "hauteur": nb(g.get("hauteur"), 10.0), "fut": nb(g.get("fut_nu"), 2.5),
            "houppier": nb(g.get("couronne_diametre"), 6.0) / 2.0}


def saison(date):
    """Saison du rendu tirée de meta.date du modèle (AAAA-MM-JJ) : hiver (déc.-fév. : arbres nus), automne
    (oct.-nov.), été sinon (pas de date : été)."""
    try:
        m = int(str(date)[5:7])
    except (TypeError, ValueError):
        return "ete"
    return "hiver" if m in (12, 1, 2) else ("automne" if m in (10, 11) else "ete")


def prototypes_arbre(parent, cle, spec, sai):
    """Trois prototypes (v0, v1, v2) d'un arbre de dimensions données (spec : hauteur, fut, houppier, rayon_tronc,
    carte_feuilles, asset). Nœud de sortie (attribut name = variante)."""
    nom = f"arbres_{cle}_prototypes"
    if parent.node(nom) is not None:
        return parent.node(nom)
    fus = parent.createNode("merge", nom)
    for v in range(3):
        w = _wrangle(parent, f"arbre_{cle}_v{v}", VEX_ARBRE, "detail")
        _parms(w, entiers=(("graine", 11 + 37 * v + sum(map(ord, cle)) % 997),
                           ("feuilles", 0 if sai == "hiver" else 1)),
               flottants=(("hauteur", spec["hauteur"]), ("fut", spec["fut"]), ("houppier", spec["houppier"]),
                          ("rayon_tronc", spec["rayon_tronc"]), ("taille_feuilles", spec["carte_feuilles"])),
               chaines=(("materiau_ecorce", "ecorce"), ("materiau_feuilles", f"feuillage_{spec['asset']}_{sai}")))
        nm = _wrangle(parent, f"arbre_{cle}_v{v}_nom", f's@name = "v{v}";', "primitive", w)
        fus.setInput(v, nm)
    return fus


def poser(parent, points, sol, nom, modele):
    pos = _wrangle(parent, f"poser_{nom}", VEX_POSER, "point", points, entrees=(sol,))
    _parms(pos, entiers=(("modele", int(modele)),))
    return pos


def points_decor(parent, nom, longueur, t_gauche, t_droite, marge, rural, route_geo, graine=3, s_libre=-1e6):
    """Points des arbres de décor en (s, t), convertis en (x, y) par la référence (entrée : références de rg::graphe)."""
    w = _wrangle(parent, f"decor_{nom}", VEX_DECOR, "detail")
    _parms(w, entiers=(("rural", int(rural)), ("graine", graine)),
           flottants=(("longueur", longueur), ("t_gauche", t_gauche), ("t_droite", t_droite), ("marge", marge),
                      ("s_libre", s_libre), ("prolongement", PROLONGEMENT_M * 0.5)))
    return _wrangle(parent, f"decor_{nom}_xy", VEX_ST_XY, "point", w, entrees=(route_geo,))


# ------------------------------------------------------------------------------------------- sols
def prolongements(parent, sol, bordures, caniveaux, route_geo):
    """Prolongements de la route aux deux bouts (profil du dessus extrudé, PROLONGEMENT_M) ; UV en mètres."""
    if parent.node("decor_prolongements") is not None:
        return parent.node("decor_prolongements")
    fus = parent.createNode("merge", "decor_dessus_fabrique")
    for k, n in enumerate((sol, bordures, caniveaux)):
        fus.setInput(k, n)
    vide = parent.createNode("null", "decor_prolongements_vide")
    bl = parent.createNode("blast", "decor_prolongements_rien")
    bl.setInput(0, sol)
    bl.parm("group").set("*")
    vide.setInput(0, bl)
    w = _wrangle(parent, "decor_prolongements_vex", VEX_PROLONGEMENTS, "detail", vide, entrees=(fus, route_geo, sol))
    _parms(w, flottants=(("longueur", PROLONGEMENT_M), ("pas_t", 0.05)))
    uv = _wrangle(parent, "decor_prolongements_uv", VEX_UV_XY, "sommet", w)
    nr = parent.createNode("normal", "decor_prolongements")
    nr.setInput(0, uv)
    nr.parm("type").set(1)
    return nr


def sol_decor(parent, sol, route_geo, prolong, mat_gauche, mat_droite, demi_cote=6000.0):
    """Sol de décor : anneau triangulé du bord du sol fabriqué et de ses prolongements jusqu'à un carré de demi-côté
    donné ; matériau de l'abord de chaque côté ; UV en mètres."""
    if parent.node("decor_sol") is not None:
        return parent.node("decor_sol")
    vide = parent.createNode("null", "decor_sol_vide")
    bl = parent.createNode("blast", "decor_sol_rien")
    bl.setInput(0, sol)
    bl.parm("group").set("*")
    vide.setInput(0, bl)
    a = _wrangle(parent, "decor_sol_contour", VEX_ANNEAU, "detail", vide, entrees=(sol, route_geo))
    _parms(a, flottants=(("demi_cote", demi_cote), ("prolongement", PROLONGEMENT_M)))
    tri = parent.createNode("triangulate2d::3.0", "decor_sol_triangules")
    tri.setInput(0, a)
    for p, v in (("useconstrpolys", 1), ("constrpolys", "*"), ("restorepos", 1),
                 ("removeduplicatepoints", 1), ("allowconstrsplit", 0)):
        tri.parm(p).set(v)
    sous = parent.createNode("merge", "decor_sol_sous")
    sous.setInput(0, sol)
    sous.setInput(1, prolong)
    tr = _wrangle(parent, "decor_sol_trou", VEX_ANNEAU_TROU, "primitive", tri, entrees=(sous,))
    cote = _wrangle(parent, "decor_sol_cote", VEX_COTE_ABORD, "primitive", tr, entrees=(route_geo,))
    _parms(cote, chaines=(("mat_gauche", mat_gauche), ("mat_droite", mat_droite)))
    uv = _wrangle(parent, "decor_sol_uv", VEX_UV_XY, "sommet", cote)
    nr = parent.createNode("normal", "decor_sol")
    nr.setInput(0, uv)
    nr.parm("type").set(1)
    return nr


def montagnes(parent, centre, graine=19):
    if parent.node("decor_montagnes") is not None:
        return parent.node("decor_montagnes")
    w = _wrangle(parent, "decor_montagnes_vex", VEX_MONTAGNES, "detail")
    _parms(w, entiers=(("graine", graine),), vecteurs=(("centre", centre),))
    nr = parent.createNode("normal", "decor_montagnes")
    nr.setInput(0, w)
    nr.parm("type").set(1)
    return nr


# ------------------------------------------------------------------------------------------- étape 1 : socle
VEX_SOCLE_JUPE = r"""
// jupe du socle (détail ; entrée 1 : sol fabriqué sans ses abords) : sous chaque arête de bord du sol (limite extérieure
// du profil le long de la route, coupe en travers en s = 0 et s = L), une face verticale jusqu'au sol plat (z_sol) ;
// arête sous z_sol ignorée (poche sous un élément : l'élément la couvre), arête verticale ignorée (mur). Fin de tronçon :
// coupe nette, rien n'est prolongé ni inventé au-delà de l'emprise de la route.
float zg = chf("z_sol");
addprimattrib(0, "materiau_id", "");
addvertexattrib(0, "uv", {0, 0, 0});
for (int h = 0; h < nvertices(1); h++) {
    if (!hedge_isvalid(1, h)) continue;
    if (hedge_equivcount(1, h) != 1) continue;
    vector A = point(1, "P", hedge_srcpoint(1, h)), B = point(1, "P", hedge_dstpoint(1, h));
    if (max(A.y, B.y) <= zg + 1e-4) continue;
    vector d = B - A;
    d.y = 0;
    float l = length(d);
    if (l < 1e-5) continue;
    vector At = set(A.x, max(A.y, zg), A.z), Bt = set(B.x, max(B.y, zg), B.z);
    vector Ab = set(A.x, zg, A.z), Bb = set(B.x, zg, B.z);
    int f = addprim(0, "poly", addpoint(0, At), addpoint(0, Bt), addpoint(0, Bb), addpoint(0, Ab));
    setprimattrib(0, "materiau_id", f, chs("materiau"));
    setvertexattrib(0, "uv", f, 0, set(0, At.y, 0));
    setvertexattrib(0, "uv", f, 1, set(l, Bt.y, 0));
    setvertexattrib(0, "uv", f, 2, set(l, zg, 0));
    setvertexattrib(0, "uv", f, 3, set(0, zg, 0));
}
"""

VEX_SOL_PLAT = r"""
// sol plat neutre (détail) : carrés emboîtés autour du centre, mailles de 2 / 8 / 32 / 128 / 512 m jusqu'à 64 / 256 /
// 1 024 / 4 096 / 16 384 m (aucun triangle long et effilé : Karma XPU 22 ne rend pas les triangles de plusieurs
// kilomètres, essai tmp/correction/essai_crenelage.py) ; Z = z_sol ; UV en mètres (x, y).
vector c = chv("centre");
float zg = chf("z_sol");
float C[] = array(2.0, 8.0, 32.0, 128.0, 512.0);
float E[] = array(64.0, 256.0, 1024.0, 4096.0, 16384.0);
addprimattrib(0, "materiau_id", "");
addvertexattrib(0, "uv", {0, 0, 0});
for (int k = 0; k < len(C); k++) {
    float cc = C[k], e = E[k];
    float ei = k > 0 ? E[k - 1] : -1.0;
    int n = int(rint(2 * e / cc));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            float x0 = -e + i * cc, x1 = -e + (i + 1) * cc, z0 = -e + j * cc, z1 = -e + (j + 1) * cc;
            if (k > 0 && x0 >= -ei - 1e-6 && x1 <= ei + 1e-6 && z0 >= -ei - 1e-6 && z1 <= ei + 1e-6) continue;
            int a = addpoint(0, set(c.x + x0, zg, c.z + z0));
            int b = addpoint(0, set(c.x + x0, zg, c.z + z1));
            int d = addpoint(0, set(c.x + x1, zg, c.z + z1));
            int g = addpoint(0, set(c.x + x1, zg, c.z + z0));
            int f = addprim(0, "poly", a, b, d, g);
            setprimattrib(0, "materiau_id", f, chs("materiau"));
            setvertexattrib(0, "uv", f, 0, set(c.x + x0, -(c.z + z0), 0));
            setvertexattrib(0, "uv", f, 1, set(c.x + x0, -(c.z + z1), 0));
            setvertexattrib(0, "uv", f, 2, set(c.x + x1, -(c.z + z1), 0));
            setvertexattrib(0, "uv", f, 3, set(c.x + x1, -(c.z + z0), 0));
        }
    }
}
"""


def socle_jupe(parent, sol, z_sol, materiau="sol_neutre", t_route=None):
    """Jupe verticale du socle sous le bord du sol fabriqué, abords du modèle retirés (étape 1). t_route = (tmin, tmax) :
    emprise de la route en t ; un mur du sol entièrement hors de cette emprise (marche entre deux abords de sections
    voisines) est retiré avec les abords (correction après le second contrôle : liaison abaissée de S_M27, murs des
    abords et leur jupe visibles en traits sur le sol neutre)."""
    nom = "socle_jupe"
    if parent.node(nom) is not None:
        for n in [c for c in parent.children() if c.name().startswith("socle_jupe")]:
            n.destroy()
    tmin, tmax = t_route if t_route else (-1e9, 1e9)
    sans = _wrangle(parent, "socle_jupe_sans_abords", r"""
if (s@classe == "abord") removeprim(0, @primnum, 1);
else if (s@classe == "mur") {
    int pts[] = primpoints(0, @primnum);
    float tc = 0;
    foreach (int p; pts) tc += float(point(0, "t", p));
    tc /= max(len(pts), 1);
    if (tc > chf("tmax") + 1e-3 || tc < chf("tmin") - 1e-3) removeprim(0, @primnum, 1);
}
""", "primitive", sol)
    _parms(sans, flottants=(("tmin", tmin), ("tmax", tmax)))
    sans.parm("tmin").set(tmin)
    sans.parm("tmax").set(tmax)
    vide = parent.createNode("blast", "socle_jupe_vide")
    vide.setInput(0, sol)
    vide.parm("group").set("*")
    w = _wrangle(parent, "socle_jupe_vex", VEX_SOCLE_JUPE, "detail", vide, entrees=(sans,))
    _parms(w, flottants=(("z_sol", z_sol),), chaines=(("materiau", materiau),))
    w.parm("z_sol").set(z_sol)
    nr = parent.createNode("normal", nom)
    nr.setInput(0, w)
    nr.parm("type").set(1)
    return nr


def sol_plat(parent, centre, z_sol, materiau="sol_neutre"):
    """Sol plat, neutre et uni sous et autour de la route (étape 1) ; centre (x, y, z) Houdini."""
    nom = "socle_sol_plat"
    if parent.node(nom) is not None:
        for n in [c for c in parent.children() if c.name().startswith("socle_sol_plat")]:
            n.destroy()
    w = _wrangle(parent, "socle_sol_plat_vex", VEX_SOL_PLAT, "detail")
    _parms(w, flottants=(("z_sol", z_sol),), chaines=(("materiau", materiau),), vecteurs=(("centre", centre),))
    w.parm("z_sol").set(z_sol)
    w.parmTuple("centre").set(centre)
    nr = parent.createNode("normal", nom)
    nr.setInput(0, w)
    nr.parm("type").set(1)
    return nr
