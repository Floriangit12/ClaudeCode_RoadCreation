"""Code VEX de l'HDA rg::marquages_carrefour::1.0 (lot L4 : marquages, trajectoires, conflits, zone de conflit des
carrefours plans). Chaque chaîne est le corps d'un Attribute Wrangle ; l'en-tête L4_H est recopié en tête de chacun
(après rg_geometrie.h, rg_niveau.h, rg_marquage.h et rg_carrefour.h : #include "opdef:" impossible).

Repère : local (x, y) = (Houdini x, −Houdini z) ; t positif à gauche ; s le long de la ligne de référence de la route ;
branches tracées vers le centre (extrémité « fin », limite du lot L3).
Entrées des wrangles « détail » : 0 flux courant (lecture du modèle puis résultats), 1 SOLVEUR (rg::carrefours,
sortie 3), 2 NIVEAUX (rg::nivellement, sortie 1), 3 références échantillonnées (rg::graphe, sortie 1).
"""

L4_H = r"""
// ---------------------------------------------------------------- rg_l4 (lot L4)
#define L4_EPS 1e-9
function int l4_ref(int gr; string rid)
{
    int prs[] = findattribval(gr, "prim", "id", rid);
    foreach (int pr; prs) if (inprimgroup(gr, "echantillonnees", pr)) return pr;
    return -1;
}
// point « sections » de NIVEAUX qui porte s sur la route rid
function int l4_section(int gr; int pr; int gn; string rid; float s)
{
    float SEC0[] = prim(gr, "sec_s0", pr);
    return rg_point_section(gn, rid, rg_indice_section(SEC0, s));
}
// limites gauche (tg) et droite (td) de la bande en s ; indice de la bande, −1 si absente
function int l4_bande_t(int gr; int pr; int gn; string rid; string bande; float s; export float tg; export float td)
{
    tg = 0.0; td = 0.0;
    int sp = l4_section(gr, pr, gn, rid, s);
    if (sp < 0) return -1;
    string bid[] = point(gn, "b_id", sp);
    int b = find(bid, bande);
    if (b < 0) return -1;
    float T[] = rg_t_limites(gn, sp, s);
    tg = T[b]; td = T[b + 1];
    return b;
}
function vector2 l4_tan(int gr; int pr; float s)
{
    float L = prim(gr, "longueur_m", pr);
    float a = max(0.0, s - 0.01), b = min(L, s + 0.01);
    return normalize(rg_local_st(gr, pr, b, 0.0) - rg_local_st(gr, pr, a, 0.0));
}
// écart (°) entre deux azimuts et l'opposition (0 : branches opposées)
function float l4_ecart180(float a; float b)
{
    float d = (a - b) % 360.0;
    if (d < 0) d += 360.0;
    return abs(180.0 - d);
}
function float l4_ang(vector2 a; vector2 b) { return degrees(atan2(a.x * b.y - a.y * b.x, dot(a, b))); }
function vector2 l4_rot(vector2 v; float deg)
{
    float c = cos(radians(deg)), s = sin(radians(deg));
    return set(c * v.x - s * v.y, s * v.x + c * v.y);
}
// intersection des droites (P, d) et (Q, e)
function int l4_inter(vector2 P; vector2 d; vector2 Q; vector2 e; export vector2 X)
{
    float den = d.x * e.y - d.y * e.x;
    X = P;
    if (abs(den) < 1e-12) return 0;
    float u = ((Q.x - P.x) * e.y - (Q.y - P.y) * e.x) / den;
    X = P + u * d;
    return 1;
}
// arc de centre C et de rayon R de l'angle a0 à a1 (degrés) : pas angulaire ≤ dmax et flèche ≤ f
function vector2[] l4_arc(vector2 C; float R; float a0; float a1; float dmax; float f)
{
    float da = a1 - a0;
    float st = dmax;
    if (R > f) st = min(st, degrees(2.0 * acos(1.0 - f / R)));
    int n = max(1, int(ceil(abs(da) / st - 1e-9)));
    vector2 out[];
    for (int i = 0; i <= n; i++) {
        float a = radians(a0 + da * float(i) / n);
        push(out, C + R * set(cos(a), sin(a)));
    }
    return out;
}
// distance signée à une polyligne (> 0 à gauche du sens de parcours) ; u : abscisse du pied
function float l4_dist_signee(vector2 Q[]; vector2 p; export float u)
{
    float sc, cote;
    float d = rc_dist_poly(Q, p, sc, cote);
    u = sc;
    return cote >= 0 ? d : -d;
}
// intersection de deux segments [a, b] et [c, d] ; ua : paramètre sur [a, b]
function int l4_seg_inter(vector2 a; vector2 b; vector2 c; vector2 d; export vector2 X; export float ua)
{
    vector2 r = b - a, q = d - c;
    float den = r.x * q.y - r.y * q.x;
    X = a; ua = 0.0;
    if (abs(den) < 1e-14) return 0;
    float t = ((c.x - a.x) * q.y - (c.y - a.y) * q.x) / den;
    float u = ((c.x - a.x) * r.y - (c.y - a.y) * r.x) / den;
    if (t < -1e-9 || t > 1.0 + 1e-9 || u < -1e-9 || u > 1.0 + 1e-9) return 0;
    X = a + t * r; ua = t;
    return 1;
}
function float l4_aire(vector2 Q[])
{
    float a = 0.0;
    int n = len(Q);
    for (int i = 0; i < n; i++) { vector2 p = Q[i], q = Q[(i + 1) % n]; a += p.x * q.y - q.x * p.y; }
    return 0.5 * a;
}
function vector2[] l4_pts_prim(int geo; int pr)
{
    vector2 out[];
    int pp[] = primpoints(geo, pr);
    foreach (int p; pp) push(out, rc_xy(point(geo, "P", p)));
    return out;
}
function vector2 l4_point_u(vector2 Q[]; float S[]; float u)
{
    int n = len(Q);
    for (int i = 0; i + 1 < n; i++) {
        if (u <= S[i + 1] + 1e-12 || i == n - 2) {
            float L = S[i + 1] - S[i];
            float a = L > 1e-12 ? clamp((u - S[i]) / L, 0.0, 1.0) : 0.0;
            return Q[i] + (Q[i + 1] - Q[i]) * a;
        }
    }
    return Q[-1];
}
// sous-polyligne de Q entre les abscisses u0 et u1 (sommets de Q gardés, densifiée au pas dl)
function vector2[] l4_sous(vector2 Q[]; float u0; float u1; float dl)
{
    float S[] = rc_cumul(Q);
    float U[];
    push(U, u0);
    for (int i = 1; i + 1 < len(Q); i++) if (S[i] > u0 + 1e-6 && S[i] < u1 - 1e-6) push(U, S[i]);
    push(U, u1);
    vector2 out[];
    for (int k = 0; k + 1 < len(U); k++) {
        int m = max(1, int(ceil((U[k + 1] - U[k]) / dl - 1e-9)));
        for (int j = 0; j < m; j++) push(out, l4_point_u(Q, S, U[k] + (U[k + 1] - U[k]) * float(j) / m));
    }
    push(out, l4_point_u(Q, S, u1));
    return out;
}
// bande de largeur w autour de la polyligne Q (côtés décalés par les normales moyennes ; Q va de « début » à « fin »),
// partie = 0 : bande entière ; 1 : moitié gauche ; 2 : moitié droite (demi-empreintes de part et d'autre de l'axe)
function vector2[] l4_ruban(vector2 Q[]; float w; int partie)
{
    int n = len(Q);
    vector2 G[], D[];
    for (int i = 0; i < n; i++) {
        vector2 t0 = i > 0 ? normalize(Q[i] - Q[i - 1]) : normalize(Q[1] - Q[0]);
        vector2 t1 = i < n - 1 ? normalize(Q[i + 1] - Q[i]) : t0;
        vector2 tm = normalize(t0 + t1);
        vector2 nn = set(-tm.y, tm.x);
        float k = 1.0 / max(0.2, dot(nn, set(-t0.y, t0.x)));
        float hg = partie == 2 ? 0.0 : 0.5 * w;
        float hd = partie == 1 ? 0.0 : 0.5 * w;
        push(G, Q[i] + hg * k * nn);
        push(D, Q[i] - hd * k * nn);
    }
    vector2 out[];
    foreach (vector2 v; D) push(out, v);
    for (int i = n - 1; i >= 0; i--) push(out, G[i]);
    return out;
}
// attributs du contrat de pj::marquage_solide (+ traçabilité) d'une empreinte du lot L4
function void l4_marque(int np; string ent; string id; string classe; string type; string gab; string mat; float us;
                        int partie; int anneau; string route; string cle; string mod; float larg; float s0; float s1;
                        int rang; int ligne)
{
    rg_m_attributs(np, ent, id, classe, type, gab, mat, "blanc", us, partie, anneau, route, cle, mod, larg, s0, s1,
                   rang, -1, ligne);
    setprimattrib(0, "pj_region", np, -1);
    setprimattrib(0, "pj_surface", np, 0);
    setprimattrib(0, "couverture", np, 1.0);
    setprimattrib(0, "rg_l4", np, 1);
}
function void l4_attributs_marques()
{
    string S[] = {"pj_entite", "id", "classe", "type", "gabarit", "materiau_id", "couleur", "route", "cle", "modulation"};
    foreach (string a; S) addprimattrib(0, a, "");
    addprimattrib(0, "usure", 0.0); addprimattrib(0, "couverture", 1.0); addprimattrib(0, "graine", 0);
    addprimattrib(0, "partie", 0); addprimattrib(0, "anneau", 0); addprimattrib(0, "pj_region", -1);
    addprimattrib(0, "pj_surface", 0); addprimattrib(0, "largeur_m", 0.0); addprimattrib(0, "s0", 0.0);
    addprimattrib(0, "s1", 0.0); addprimattrib(0, "rang", 0); addprimattrib(0, "bande_sol", -1);
    addprimattrib(0, "rg_ligne", 0); addprimattrib(0, "rg_l4", 0);
}
// lignes du SOLVEUR : abscisse du centre (s du modèle), largeur, étendue en t
function float l4_largeur_ligne(string gab; float WL[]) { return gab == "EFFET_FEUX" ? WL[0] : (gab == "CEDEZ" ? WL[1] : (gab == "STOP" ? WL[2] : 0.0)); }

// ligne la plus en amont qui couvre la voie [tg, td] (amont = 1) ou la plus en aval (amont = 0) ; s de son bord amont
// (amont = 1) ou aval (amont = 0) ; -1e18 si aucune
function float l4_ligne_voie(string car; string bid; string rid; int pr; float tg; float td; int amont; float WL[];
                             export float sc)
{
    float best = amont ? 1e18 : -1e18;
    sc = -1e18;
    foreach (int q; expandprimgroup(1, "ligne")) {
        if (string(prim(1, "branche", q)) != bid || string(prim(1, "route", q)) != rid) continue;
        vector2 L[] = l4_pts_prim(1, q);
        float s0, t0, s1, t1;
        rg_st_local(3, pr, L[0].x, L[0].y, s0, t0);
        rg_st_local(3, pr, L[-1].x, L[-1].y, s1, t1);
        float lo = min(t0, t1), hi = max(t0, t1);
        float ov = min(hi, tg) - max(lo, td);
        if (ov < 0.5 * (tg - td)) continue;
        float s = 0.5 * (s0 + s1);
        float w = l4_largeur_ligne(string(prim(1, "gabarit", q)), WL);
        if (amont && s < best) { best = s; sc = s - 0.5 * w; }
        if (!amont && s > best) { best = s; sc = s + 0.5 * w; }
    }
    return best;
}
// bords de la chaussée (limite gauche de la première bande basse, droite de la dernière) en s, section sp de NIVEAUX
function int l4_bords(int gn; int sp; float s; export float tg; export float td)
{
    int cls[] = point(gn, "b_cls", sp);
    float T[] = rg_t_limites(gn, sp, s);
    int i0 = -1, i1 = -1;
    for (int b = 0; b < len(cls); b++) if (cls[b] == 0) { if (i0 < 0) i0 = b; i1 = b; }
    if (i0 < 0) return 0;
    tg = T[i0]; td = T[i1 + 1];
    return 1;
}
// axe réel d'une bande (milieu de ses limites) en s, son vecteur unitaire (sens des s croissants) et une polyligne de
// l'axe de s0 à s1 (s0 > s1 : parcours vers les s décroissants), pas ≤ pas
function vector2 l4_axe_pt(int gr; int pr; int gn; string rid; string bande; float s)
{
    float L = prim(gr, "longueur_m", pr);
    float sc = clamp(s, 0.0, L - 1e-4);
    float tg, td;
    int b = l4_bande_t(gr, pr, gn, rid, bande, sc, tg, td);
    float t = b >= 0 ? 0.5 * (tg + td) : 0.0;
    return rg_local_st(gr, pr, sc, t);
}
function vector2 l4_axe_tan(int gr; int pr; int gn; string rid; string bande; float s)
{
    float L = prim(gr, "longueur_m", pr);
    float a = clamp(s - 0.05, 0.0, L - 1e-4), b = clamp(s + 0.05, 0.0, L - 1e-4);
    if (b - a < 1e-3) a = max(0.0, b - 0.1);
    return normalize(l4_axe_pt(gr, pr, gn, rid, bande, b) - l4_axe_pt(gr, pr, gn, rid, bande, a));
}
function vector2[] l4_axe_poly(int gr; int pr; int gn; string rid; string bande; float s0; float s1; float pas)
{
    vector2 out[];
    int n = max(1, int(ceil(abs(s1 - s0) / pas - 1e-9)));
    for (int k = 0; k <= n; k++) push(out, l4_axe_pt(gr, pr, gn, rid, bande, s0 + (s1 - s0) * float(k) / n));
    return out;
}
// point br4 de la branche (flux 0)
function int l4_br(string car; string bid)
{
    int pts[] = findattribval(0, "point", "branche", bid);
    foreach (int p; pts) if (inpointgroup(0, "br4", p) && string(point(0, "carrefour", p)) == car) return p;
    return -1;
}
// point voie (flux 0) : branche, bande, entrante (1) ou sortante (0)
function int l4_voie(string car; string bid; string bande; int ent)
{
    int pts[] = findattribval(0, "point", "bande", bande);
    foreach (int p; pts)
        if (inpointgroup(0, "voie", p) && string(point(0, "carrefour", p)) == car && string(point(0, "branche", p)) == bid
            && int(point(0, "entrante", p)) == ent) return p;
    return -1;
}
"""

# --------------------------------------------------------------------------------------------------------- voies
VEX_VOIES = r"""
// (1) branches et voies (détail) : repère du SOLVEUR recopié sur les points br4 ; une voie (point du groupe « voie »)
// par bande de circulation ou cyclable à l'embouchure (s_end) : axe, bords, sens (entrante : vers le centre).
string avert[];
addpointattrib(0, "Pe", {0, 0, 0}); addpointattrib(0, "dir", {0, 0, 0}); addpointattrib(0, "nrm", {0, 0, 0});
addpointattrib(0, "centre", {0, 0, 0});
foreach (string a; {"s_end", "s_front", "s_tan_g", "s_tan_d", "t_g", "t_d", "azimut", "rayon_coin_g", "rayon_coin_d",
                    "t_axe", "t0", "t1", "largeur"}) addpointattrib(0, a, 0.0);
foreach (string a; {"coin_g", "coin_d", "type"}) addpointattrib(0, a, "");
foreach (string a; {"lim_g", "lim_d", "entrante", "rang", "droit_g", "droit_d"}) addpointattrib(0, a, 0);
addpointattrib(0, "h", {0, 0, 0});
int BR[] = expandpointgroup(0, "br4");
foreach (int p; BR) {
    string car = point(0, "carrefour", p);
    string bid = point(0, "branche", p);
    int q = -1;
    int cand[] = findattribval(1, "point", "branche", bid);
    foreach (int c; cand) if (inpointgroup(1, "branche", c) && string(point(1, "carrefour", c)) == car) q = c;
    if (q < 0) { push(avert, sprintf("%s %s : branche absente du SOLVEUR", car, bid)); continue; }
    if (string(point(0, "extremite", p)) != "fin") push(avert, sprintf("%s %s : extrémité « début » non prise en charge", car, bid));
    foreach (string a; {"s_end", "s_front", "s_tan_g", "s_tan_d", "t_g", "t_d", "azimut"})
        setpointattrib(0, a, p, float(point(1, a, q)));
    foreach (string a; {"coin_g", "coin_d"}) setpointattrib(0, a, p, string(point(1, a, q)));
    foreach (string a; {"lim_g", "lim_d", "rang"}) setpointattrib(0, a, p, int(point(1, a, q)));
    foreach (string a; {"Pe", "dir", "nrm", "centre"}) setpointattrib(0, a, p, vector(point(1, a, q)));
    // coins voisins : rayon (0 si bords alignés, « droit »)
    foreach (string cote; {"g", "d"}) {
        string cn = point(1, "coin_" + cote, q);
        float rc = 0.0;
        int dr = 1;
        int cp[] = findattribval(1, "prim", "coin", cn);
        foreach (int c; cp) if (inprimgroup(1, "coin", c)) { rc = prim(1, "rayon", c); dr = prim(1, "droit", c); }
        setpointattrib(0, "rayon_coin_" + cote, p, rc);
        setpointattrib(0, "droit_" + cote, p, dr);
    }
    string rid = point(0, "route", p);
    int pr = l4_ref(3, rid);
    if (pr < 0) { push(avert, sprintf("%s %s : route %s absente des références", car, bid, rid)); continue; }
    float se = point(1, "s_end", q);
    float sq = se - 1e-4;
    int sp = l4_section(3, pr, 2, rid, sq);
    if (sp < 0) { push(avert, sprintf("%s %s : section absente en s_end", car, bid)); continue; }
    string bids[] = point(2, "b_id", sp);
    string btyp[] = point(2, "b_type", sp);
    float T[] = rg_t_limites(2, sp, sq);
    string mids[] = point(0, "bandes_ids", p);
    string msens[] = point(0, "bandes_sens", p);
    string ent[] = point(0, "entrantes", p);
    string sor[] = point(0, "sortantes", p);
    vector2 d = l4_tan(3, pr, se);
    for (int b = 0; b < len(bids); b++) {
        string ty = btyp[b];
        if (!(startswith(ty, "voie") || ty == "bande_cyclable")) continue;
        string sens = "";
        int k = find(mids, bids[b]);
        if (k >= 0) sens = msens[k];
        int e = -1;
        if (find(ent, bids[b]) >= 0) e = 1;
        else if (find(sor, bids[b]) >= 0) e = 0;
        else if (sens == "avant") e = 1;
        else if (sens == "arriere") e = 0;
        if (e < 0) continue;
        float ta = 0.5 * (T[b] + T[b + 1]);
        vector2 P = rg_local_st(3, pr, se, ta);
        int v = addpoint(0, rc_h(P, 0.0));
        setpointgroup(0, "voie", v, 1);
        setpointattrib(0, "carrefour", v, car); setpointattrib(0, "branche", v, bid); setpointattrib(0, "route", v, rid);
        setpointattrib(0, "bande", v, bids[b]); setpointattrib(0, "type", v, ty); setpointattrib(0, "entrante", v, e);
        setpointattrib(0, "t_axe", v, ta); setpointattrib(0, "t0", v, T[b]); setpointattrib(0, "t1", v, T[b + 1]);
        setpointattrib(0, "largeur", v, T[b] - T[b + 1]); setpointattrib(0, "s_end", v, se);
        vector2 hh = e ? d : -d;
        setpointattrib(0, "h", v, set(hh.x, hh.y, 0.0));
    }
}
setdetailattrib(0, "rg_l4_avertissements", avert, "append");
"""

# --------------------------------------------------------------------------------------------------------- guidage
VEX_GUIDAGE = r"""
// (2) lignes de guidage (détail) : seulement pour les mouvements dont le modèle dit guidage.materialise (ARB-08,
// RF-OSM-MRQ-041) ; TAG à l'indonésienne de deux branches opposées (RF-MQ-GUI-01, RF-MQ-CAR-03, IISR7 p. 36) :
// prolongement du bord droit de chaque voie de TAG (côté voies directes), segment oblique à 45° reliant les deux
// prolongements à travers la zone centrale (les deux courants passent l'un devant l'autre, de part et d'autre de la
// ligne) ; raccords par arcs tangents de rayon maximal tenant entre l'embouchure et l'oblique, plafonné au rayon d'axe
// du véhicule de projet (DEF-021) : choix [G], l'IISR ne cote pas les rayons (RF-MQ-GUI-03).
addprimattrib(0, "id", ""); addprimattrib(0, "carrefour", ""); addprimattrib(0, "modulation", "");
addprimattrib(0, "mouvements", ""); addprimattrib(0, "largeur_m", 0.0); addprimattrib(0, "rayon_raccord", 0.0);
addprimattrib(0, "angle_oblique_deg", 0.0); addprimattrib(0, "longueur", 0.0);
addpointattrib(0, "guidage", "");
string avert[];
float rmax = chf("../r_min_vehicule");
int MV[] = expandpointgroup(0, "mv");
int fait[];
foreach (int i; MV) {
    if (int(point(0, "guide", i)) != 1 || find(fait, i) >= 0) continue;
    string car = point(0, "carrefour", i);
    if (string(point(0, "mouvement", i)) != "TAG") {
        push(avert, sprintf("%s : guidage demandé hors TAG (%s) non pris en charge", car, string(point(0, "id", i))));
        continue;
    }
    int pa = l4_br(car, point(0, "de_branche", i));
    int j = -1;
    foreach (int k; MV) {
        if (k == i || find(fait, k) >= 0 || int(point(0, "guide", k)) != 1 || string(point(0, "mouvement", k)) != "TAG") continue;
        if (string(point(0, "carrefour", k)) != car) continue;
        int pb = l4_br(car, point(0, "de_branche", k));
        float dz = pb >= 0 ? l4_ecart180(point(0, "azimut", pa), point(0, "azimut", pb)) : 999.0;
        if (pb >= 0 && dz < 20.0) { j = k; break; }
    }
    if (j < 0) { push(avert, sprintf("%s : TAG guidé %s sans TAG opposé guidé", car, string(point(0, "id", i)))); continue; }
    push(fait, i); push(fait, j);
    int va = l4_voie(car, point(0, "de_branche", i), point(0, "de_bande", i), 1);
    int vb = l4_voie(car, point(0, "de_branche", j), point(0, "de_bande", j), 1);
    if (va < 0 || vb < 0) { push(avert, sprintf("%s : voie de TAG guidée absente", car)); continue; }
    int pb = l4_br(car, point(0, "de_branche", j));
    // bords droits des voies de TAG à l'embouchure (t1 : limite droite d'une voie entrante)
    vector Pa3 = point(0, "Pe", pa), na3 = point(0, "nrm", pa), Pb3 = point(0, "Pe", pb), nb3 = point(0, "nrm", pb);
    vector2 Ea = set(Pa3.x, Pa3.y) + float(point(0, "t1", va)) * set(na3.x, na3.y);
    vector2 Eb = set(Pb3.x, Pb3.y) + float(point(0, "t1", vb)) * set(nb3.x, nb3.y);
    vector h3 = point(0, "h", va);
    vector2 e = normalize(set(h3.x, h3.y));
    vector2 nn = rc_gauche(e);
    vector c3 = point(0, "centre", pa);
    vector2 C = set(c3.x, c3.y);
    float oa = dot(Ea - C, nn), ob = dot(Eb - C, nn);
    float dl = abs(ob - oa);
    vector2 q1 = C + oa * nn - 0.5 * dl * e;
    vector2 q2 = C + ob * nn + 0.5 * dl * e;
    float L1 = dot(q1 - Ea, e), L2 = dot(Eb - q2, e), Lo = length(q2 - q1);
    float delta = abs(l4_ang(e, normalize(q2 - q1)));
    float tg = tan(radians(0.5 * delta));
    float rho = min(min(L1, L2), 0.5 * Lo) / max(tg, 1e-9);
    rho = min(rho, rmax);
    if (L1 < -1e-6 || L2 < -1e-6) push(avert, sprintf("%s : oblique de guidage en amont d'une embouchure", car));
    // polyligne : Ea -> raccord 1 -> oblique -> raccord 2 -> Eb
    vector2 Q[];
    float T = rho * tg;
    vector2 u = normalize(q2 - q1);
    push(Q, Ea);
    vector2 a1 = q1 - T * e, b1 = q1 + T * u;
    float sg = l4_ang(e, u) > 0 ? 1.0 : -1.0;
    vector2 C1 = a1 + sg * rho * rc_gauche(e);
    vector2 arc1[] = l4_arc(C1, rho, degrees(atan2(a1.y - C1.y, a1.x - C1.x)),
                            degrees(atan2(a1.y - C1.y, a1.x - C1.x)) + sg * delta, 1.0, 0.0005);
    foreach (vector2 v; arc1) push(Q, v);
    vector2 a2 = q2 - T * u, b2 = q2 + T * e;
    vector2 C2 = a2 - sg * rho * rc_gauche(u);
    vector2 arc2[] = l4_arc(C2, rho, degrees(atan2(a2.y - C2.y, a2.x - C2.x)),
                            degrees(atan2(a2.y - C2.y, a2.x - C2.x)) - sg * delta, 1.0, 0.0005);
    foreach (vector2 v; arc2) push(Q, v);
    push(Q, Eb);
    // nettoyage : sommets confondus
    vector2 R[];
    foreach (vector2 v; Q) if (len(R) == 0 || length(v - R[-1]) > 1e-5) push(R, v);
    int pts[];
    foreach (vector2 v; R) push(pts, addpoint(0, rc_h(v, 0.0)));
    int g = addprim(0, "polyline", pts);
    setprimgroup(0, "guidage", g, 1);
    string gid = sprintf("G-%s.%s_%s", re_replace("^C-", "", car), re_replace("^B-", "", string(point(0, "de_branche", i))),
                         re_replace("^B-", "", string(point(0, "de_branche", j))));
    setprimattrib(0, "id", g, gid); setprimattrib(0, "carrefour", g, car);
    setprimattrib(0, "modulation", g, string(point(0, "guide_mod", i)));
    float lg = point(0, "guide_larg", i);
    setprimattrib(0, "largeur_m", g, lg > 0 ? lg : chf("../guidage_largeur"));
    setprimattrib(0, "mouvements", g, sprintf("%s %s", string(point(0, "id", i)), string(point(0, "id", j))));
    setprimattrib(0, "rayon_raccord", g, rho); setprimattrib(0, "angle_oblique_deg", g, delta);
    float S[] = rc_cumul(R);
    setprimattrib(0, "longueur", g, S[-1]);
    setpointattrib(0, "guidage", i, gid); setpointattrib(0, "guidage", j, gid);
}
setdetailattrib(0, "rg_l4_avertissements", avert, "append");
"""

# --------------------------------------------------------------------------------------------------------- trajectoires
VEX_TRAJECTOIRES = r"""
// (3) trajectoires voie à voie (détail) : droite – arc tangent – droite le long des axes des voies (RF-GV-TRJ-006),
// rayon ≥ rayon d'axe minimal du véhicule de projet (lot L3a). Rayon : TAD = rayon du coin + écart de l'axe de voie au
// bord de chaussée (arc quasi concentrique au coin, RF-GV-TRJ-006) ; TAG non guidé = plus grand rayon dont les points
// de tangence restent dans les embouchures ; TAG guidé = plus petit rayon (pas de 1 cm) tel que la caisse du véhicule de
// projet (demi-largeur) reste de son côté de la ligne de guidage, à garde_guidage au moins du bord de la peinture
// (RF-MQ-CAR-03 : les deux courants passent de part et d'autre ; RF-GV-TRJ-006 : garde entre enveloppes) ; tout droit = droite. Un arc qui sort d'une embouchure (rayon minimal du véhicule) recule la limite de la
// jonction sur la branche (d_j) : toutes les trajectoires d'une branche commencent (ou finissent) au même point de voie.
// Vélos : bande cyclable entrante prolongée en droite vers la bande cyclable sortante alignée de la branche opposée
// ([G] : aucun mouvement cyclable n'est décrit).
foreach (string a; {"id", "carrefour", "mouvement", "de_branche", "de_bande", "vers_branche", "vers_bande", "vehicule",
                    "guidage", "tags", "regle_rayon"}) addprimattrib(0, a, "");
foreach (string a; {"rayon", "rayon_min", "longueur", "angle_deg", "ext_entree", "ext_sortie", "dev_entree",
                    "dev_sortie", "ecart_lateral", "garde_guidage", "rayon_ajuste"}) addprimattrib(0, a, 0.0);
addprimattrib(0, "guide", 0); addprimattrib(0, "priorite", 0); addprimattrib(0, "faisable", 1);
addpointattrib(0, "s_j", 0.0); addpointattrib(0, "d_j", 0.0);
string avert[];
float RMIN = ceil(chf("../r_min_vehicule") * 100.0 - 1e-6) / 100.0;
float W2 = 0.5 * chf("../largeur_vehicule");
// garde entre la caisse et le bord de la peinture de la ligne de guidage (correction après le contrôle de l'étape 2 :
// la caisse ne faisait que ne pas toucher la peinture, garde 3 mm, balayages des deux TAG guidés de J5 recouverts) :
// paramètre garde_guidage, calculé à la construction depuis RF-GV-TRJ-006 et VU p. 142 (construire.py)
float GARDE_G = chf("../garde_guidage");
float ATD = chf("../angle_tout_droit");
float FL = chf("../fleche_arc"), DA = chf("../pas_angulaire_arc");
int MV[] = expandpointgroup(0, "mv");
// mouvements cyclables ajoutés (bande cyclable entrante -> bande cyclable sortante alignée de la branche opposée)
string M_id[], M_car[], M_de[], M_deb[], M_vers[], M_versb[], M_mv[], M_tags[];
int M_src[];
foreach (int i; MV) {
    push(M_id, string(point(0, "id", i))); push(M_car, string(point(0, "carrefour", i)));
    push(M_de, string(point(0, "de_branche", i))); push(M_deb, string(point(0, "de_bande", i)));
    push(M_vers, string(point(0, "vers_branche", i))); push(M_versb, string(point(0, "vers_bande", i)));
    push(M_mv, string(point(0, "mouvement", i))); push(M_tags, "vehicule"); push(M_src, i);
}
int VO[] = expandpointgroup(0, "voie");
foreach (int v; VO) {
    if (string(point(0, "type", v)) != "bande_cyclable" || int(point(0, "entrante", v)) != 1) continue;
    vector h3 = point(0, "h", v); vector2 hv = set(h3.x, h3.y); vector2 Pv = rc_xy(point(0, "P", v));
    int best = -1; float bd = 1.0;
    foreach (int w; VO) {
        if (string(point(0, "type", w)) != "bande_cyclable" || int(point(0, "entrante", w)) != 0) continue;
        if (string(point(0, "carrefour", w)) != string(point(0, "carrefour", v)) || string(point(0, "branche", w)) == string(point(0, "branche", v))) continue;
        vector g3 = point(0, "h", w); vector2 hw = set(g3.x, g3.y);
        if (dot(hv, hw) < cos(radians(ATD))) continue;
        float lat = abs(rc_croix(hv, rc_xy(point(0, "P", w)) - Pv));
        if (lat < bd) { bd = lat; best = w; }
    }
    if (best < 0) continue;
    string bd0 = point(0, "branche", v);
    push(M_id, sprintf("T-%s.%s.TD_velo", re_replace("^B-", "", bd0), string(point(0, "bande", v))));
    push(M_car, string(point(0, "carrefour", v))); push(M_de, bd0); push(M_deb, string(point(0, "bande", v)));
    push(M_vers, string(point(0, "branche", best))); push(M_versb, string(point(0, "bande", best)));
    push(M_mv, "TD"); push(M_tags, "velo"); push(M_src, -1);
}
int n = len(M_id);
// géométrie de chaque mouvement, itérée sur l'axe réel des voies : PA, hA (axe d'entrée en sA), PB, hB (axe de sortie
// en sB) ; arc (S1, S2, C, R) ; sA (sB) = s_end, ou l'abscisse du point de tangence s'il est en amont de l'embouchure
// (l'arc commence alors sur l'axe réel de la voie, même si la voie se décale plus loin)
vector2 PA[], HA[], PB[], HB[], S1[], S2[], CC[];
float RR[], DEL[], EXI[], EXO[], LAT[], GAR[], SA[], SB[];
int OK[], VA[], VB[], TYP[];       // TYP : 0 droite, 1 arc
string REG[];
for (int m = 0; m < n; m++) {
    int va = l4_voie(M_car[m], M_de[m], M_deb[m], 1);
    int vb = l4_voie(M_car[m], M_vers[m], M_versb[m], 0);
    push(VA, va); push(VB, vb);
    vector2 z = {0, 0};
    if (va < 0 || vb < 0) {
        push(avert, sprintf("%s : voie d'entrée ou de sortie absente", M_id[m]));
        push(OK, 0); push(PA, z); push(HA, z); push(PB, z); push(HB, z); push(S1, z); push(S2, z); push(CC, z);
        push(RR, 0.0); push(DEL, 0.0); push(EXI, 0.0); push(EXO, 0.0); push(TYP, 0); push(REG, ""); push(LAT, 0.0);
        push(GAR, 0.0); push(SA, 0.0); push(SB, 0.0);
        continue;
    }
    string ra = point(0, "route", va), rb = point(0, "route", vb);
    string ba = point(0, "bande", va), bb = point(0, "bande", vb);
    int pra = l4_ref(3, ra), prb = l4_ref(3, rb);
    float sea = point(0, "s_end", va), seb = point(0, "s_end", vb);
    float sA = sea, sB = seb;
    vector2 pa = l4_axe_pt(3, pra, 2, ra, ba, sA - 1e-4), pb = l4_axe_pt(3, prb, 2, rb, bb, sB - 1e-4);
    vector2 ha = l4_axe_tan(3, pra, 2, ra, ba, sA - 1e-4), hb = -l4_axe_tan(3, prb, 2, rb, bb, sB - 1e-4);
    float dlt = l4_ang(ha, hb);
    vector2 I;
    if (abs(dlt) < ATD || !l4_inter(pa, ha, pb, hb, I)) {
        push(OK, 1); push(PA, pa); push(HA, ha); push(PB, pb); push(HB, hb); push(DEL, dlt);
        push(LAT, rc_croix(ha, pb - pa));
        push(TYP, 0); push(S1, pa); push(S2, pb); push(CC, z); push(RR, 0.0); push(EXI, 0.0); push(EXO, 0.0);
        push(REG, "droite"); push(GAR, 0.0); push(SA, sea); push(SB, seb);
        continue;
    }
    int guide = M_src[m] >= 0 ? point(0, "guide", M_src[m]) : 0;
    string gid = M_src[m] >= 0 ? string(point(0, "guidage", M_src[m])) : "";
    int gpr = -1;
    if (guide && gid != "") {
        int gp[] = findattribval(0, "prim", "id", gid);
        foreach (int g; gp) if (inprimgroup(0, "guidage", g)) gpr = g;
    }
    float R = 0.0, gar = 0.0, T = 0.0;
    string reg = "";
    vector2 s1, s2, c;
    for (int it = 0; it < 6; it++) {
        pa = l4_axe_pt(3, pra, 2, ra, ba, sA - 1e-4);
        ha = l4_axe_tan(3, pra, 2, ra, ba, sA - 1e-4);
        pb = l4_axe_pt(3, prb, 2, rb, bb, sB - 1e-4);
        hb = -l4_axe_tan(3, prb, 2, rb, bb, sB - 1e-4);
        dlt = l4_ang(ha, hb);
        l4_inter(pa, ha, pb, hb, I);
        float ta = dot(I - pa, ha), tb = dot(pb - I, hb);
        float tg = tan(radians(0.5 * abs(dlt)));
        // embouchures prises à la frontière du carrefour (s_front), et non à la fin des branches (s_end) : s_end recule
        // avec les nez des îlots, eux-mêmes placés par les balayages de ces trajectoires (correction après le contrôle
        // de l'étape 2 : une seule source de trajectoires, point fixe) ; les points de tangence restent dans le carrefour
        float sfa = point(0, "s_front", l4_br(M_car[m], M_de[m])), sfb = point(0, "s_front", l4_br(M_car[m], M_vers[m]));
        float taf = ta - max(0.0, sfa - sA), tbf = tb - max(0.0, sfb - sB);
        R = max(0.0, min(taf, tbf)) / max(tg, 1e-9);
        reg = "rayon tenant dans les embouchures (frontière du carrefour)";
        if (M_mv[m] == "TAD" && dlt < 0) {
            int pa_ = l4_br(M_car[m], M_de[m]), pb_ = l4_br(M_car[m], M_vers[m]);
            float rc = point(0, "rayon_coin_d", pa_);
            int dr = point(0, "droit_d", pa_);
            if (rc > 0 && !dr) {
                float oin = abs(float(point(0, "t_axe", va)) - float(point(0, "t_d", pa_)));
                float oout = abs(float(point(0, "t_g", pb_)) - float(point(0, "t_axe", vb)));
                R = rc + min(oin, oout);
                reg = "coin + écart de l'axe de voie au bord (RF-GV-TRJ-006)";
            }
        }
        if (R < RMIN) { R = RMIN; reg = "rayon minimal du véhicule de projet arrondi au cm (lot L3a)"; }
        float sg = dlt > 0 ? 1.0 : -1.0;
        if (gpr >= 0) {
            // TAG guidé : plus petit rayon (pas de 1 cm) tel que la caisse reste de son côté de la ligne sans toucher la
            // peinture
            vector2 GQ[] = l4_pts_prim(0, gpr);
            // partie centrale de la ligne (raccords et oblique, sans les prolongements droits des bords de voie) : la
            // garde garde_guidage s'y applique (les deux courants s'y croisent) ; le long des prolongements, la caisse
            // reste dans le prolongement de sa voie (ne touche pas la peinture) ; sans cette distinction le rayon
            // dépendait de la fin de la branche (s_end), donc du nez des îlots : pas de point fixe
            vector2 GQo[];
            for (int z = 1; z + 1 < len(GQ); z++) push(GQo, GQ[z]);
            if (len(GQo) < 2) GQo = GQ;
            float wl2 = 0.5 * float(prim(0, "largeur_m", gpr));
            float u0;
            float cote = l4_dist_signee(GQ, pa, u0) >= 0 ? 1.0 : -1.0;
            float Rt = RMIN;
            int trouve = 0;
            for (int k = 0; k < 4000 && !trouve; k++) {
                float Tt = Rt * tg;
                vector2 a1 = I - Tt * ha, a2 = I + Tt * hb;
                vector2 cc = a1 + sg * Rt * rc_gauche(ha);
                float a0 = degrees(atan2(a1.y - cc.y, a1.x - cc.x));
                vector2 A[] = l4_arc(cc, Rt, a0, a0 + dlt, 1.0, 0.002);
                push(A, a2 + 30.0 * hb);
                insert(A, 0, a1 - 30.0 * ha);
                vector2 Ad[] = rc_densifier(A, 0.05);
                float mn = 1e18, mo = 1e18;
                foreach (vector2 q; Ad) {
                    float uu;
                    mn = min(mn, cote * l4_dist_signee(GQ, q, uu));
                    mo = min(mo, cote * l4_dist_signee(GQo, q, uu));
                }
                if (mn >= W2 + wl2 && mo >= W2 + wl2 + GARDE_G) { trouve = 1; gar = mo - W2 - wl2; R = Rt; }
                else Rt += 0.01;
            }
            if (!trouve) push(avert, sprintf("%s : aucun rayon ne garde la caisse du côté de la ligne de guidage", M_id[m]));
            reg = "TAG guidé : plus petit rayon gardant la caisse du véhicule de projet de son côté de la ligne, sans toucher la peinture (RF-MQ-CAR-03)";
        }
        T = R * tg;
        s1 = I - T * ha; s2 = I + T * hb;
        c = s1 + sg * R * rc_gauche(ha);
        // abscisses des points de tangence en amont des embouchures (sur l'axe réel de la voie)
        vector2 pa0 = l4_axe_pt(3, pra, 2, ra, ba, sea - 1e-4), ha0 = l4_axe_tan(3, pra, 2, ra, ba, sea - 1e-4);
        vector2 pb0 = l4_axe_pt(3, prb, 2, rb, bb, seb - 1e-4), hb0 = -l4_axe_tan(3, prb, 2, rb, bb, seb - 1e-4);
        float din = dot(s1 - pa0, ha0), dout = dot(s2 - pb0, hb0);
        float nsA = din < 0 ? max(0.5, sea + din) : sea;
        float nsB = dout > 0 ? max(0.5, seb - dout) : seb;
        if (abs(nsA - sA) < 1e-5 && abs(nsB - sB) < 1e-5) break;
        sA = nsA; sB = nsB;
    }
    push(OK, 1); push(PA, pa); push(HA, ha); push(PB, pb); push(HB, hb); push(DEL, dlt);
    push(LAT, rc_croix(ha, pb - pa));
    push(TYP, 1); push(S1, s1); push(S2, s2); push(CC, c); push(RR, R); push(REG, reg);
    push(EXI, sea - sA); push(EXO, seb - sB); push(GAR, gar); push(SA, sA); push(SB, sB);
}
// TAG opposés non guidés (deux branches opposées, même carrefour) : ils tournent l'un devant l'autre sans que leurs axes
// se croisent (convention des points de conflit du CU p. 120-122 : 16 croisements pour une croix) ; plus petit rayon
// commun (pas de 5 cm) ≥ celui de la règle qui sépare les deux axes, tant que l'écart latéral de l'arc au droit de
// chaque embouchure reste ≤ demi-voie − demi-caisse (le véhicule reste dans sa voie au droit des nez d'îlots) ; sinon
// rayon de la règle gardé et croisement signalé.
for (int m1 = 0; m1 < n; m1++) {
    if (!OK[m1] || TYP[m1] != 1 || M_mv[m1] != "TAG" || M_tags[m1] != "vehicule") continue;
    if (M_src[m1] >= 0 && int(point(0, "guide", M_src[m1]))) continue;
    for (int m2 = m1 + 1; m2 < n; m2++) {
        if (!OK[m2] || TYP[m2] != 1 || M_mv[m2] != "TAG" || M_car[m2] != M_car[m1] || M_tags[m2] != "vehicule") continue;
        if (M_src[m2] >= 0 && int(point(0, "guide", M_src[m2]))) continue;
        int b1 = l4_br(M_car[m1], M_de[m1]), b2 = l4_br(M_car[m2], M_de[m2]);
        if (l4_ecart180(point(0, "azimut", b1), point(0, "azimut", b2)) > 20.0) continue;
        // TAG opposés de phases disjointes (feux : jamais simultanés, ex. J5 P3 nord / P4 sud) : pas de séparation
        // cherchée (correction après le contrôle de l'étape 2)
        if (M_src[m1] >= 0 && M_src[m2] >= 0) {
            string ph1[] = point(0, "phases", M_src[m1]), ph2[] = point(0, "phases", M_src[m2]);
            int commun = len(ph1) == 0 || len(ph2) == 0;
            foreach (string x; ph1) if (find(ph2, x) >= 0) commun = 1;
            if (!commun) continue;
        }
        int MM[] = array(m1, m2);
        float R0 = max(RR[m1], RR[m2]);
        int trouve = 0;
        float Rsel = R0;
        for (float Rt = R0; Rt <= 40.0 && !trouve; Rt += 0.05) {
            vector2 AX[], BX[];
            int ok = 1;
            for (int z = 0; z < 2; z++) {
                int m = MM[z];
                vector2 pa0 = l4_axe_pt(3, l4_ref(3, string(point(0, "route", VA[m]))), 2, string(point(0, "route", VA[m])),
                                        string(point(0, "bande", VA[m])), float(point(0, "s_end", VA[m])) - 1e-4);
                vector2 pb0 = l4_axe_pt(3, l4_ref(3, string(point(0, "route", VB[m]))), 2, string(point(0, "route", VB[m])),
                                        string(point(0, "bande", VB[m])), float(point(0, "s_end", VB[m])) - 1e-4);
                vector2 I;
                l4_inter(pa0, HA[m], pb0, HB[m], I);
                float tg = tan(radians(0.5 * abs(DEL[m])));
                float T = Rt * tg;
                float ta = dot(I - pa0, HA[m]), tb = dot(pb0 - I, HB[m]);
                float ei = max(0.0, T - ta), eo = max(0.0, T - tb);
                int va = VA[m], vb = VB[m];
                float lim_i = 0.5 * float(point(0, "largeur", va)) - W2, lim_o = 0.5 * float(point(0, "largeur", vb)) - W2;
                if (Rt - sqrt(max(0.0, Rt * Rt - ei * ei)) > lim_i + 1e-6 || Rt - sqrt(max(0.0, Rt * Rt - eo * eo)) > lim_o + 1e-6) ok = 0;
                vector2 s1 = I - T * HA[m], s2 = I + T * HB[m];
                float sg = DEL[m] > 0 ? 1.0 : -1.0;
                vector2 c = s1 + sg * Rt * rc_gauche(HA[m]);
                float a0 = degrees(atan2(s1.y - c.y, s1.x - c.x));
                vector2 A[] = l4_arc(c, Rt, a0, a0 + DEL[m], 1.0, 0.002);
                insert(A, 0, s1 - 40.0 * HA[m]);
                push(A, s2 + 40.0 * HB[m]);
                if (z == 0) AX = A; else BX = A;
            }
            if (!ok) break;
            int croise = 0;
            for (int i = 0; i + 1 < len(AX) && !croise; i++)
                for (int j = 0; j + 1 < len(BX) && !croise; j++) {
                    vector2 Y; float ua;
                    croise = l4_seg_inter(AX[i], AX[i + 1], BX[j], BX[j + 1], Y, ua);
                }
            if (!croise) { trouve = 1; Rsel = Rt; }
        }
        if (!trouve) {
            push(avert, sprintf("%s / %s : TAG opposés qui se croisent (aucun rayon ne les sépare en gardant chaque véhicule dans sa voie au droit des embouchures)", M_id[m1], M_id[m2]));
            continue;
        }
        if (Rsel <= R0 + 1e-9) continue;
        for (int z = 0; z < 2; z++) {
            int m = MM[z];
            vector2 pa0 = l4_axe_pt(3, l4_ref(3, string(point(0, "route", VA[m]))), 2, string(point(0, "route", VA[m])),
                                    string(point(0, "bande", VA[m])), float(point(0, "s_end", VA[m])) - 1e-4);
            vector2 pb0 = l4_axe_pt(3, l4_ref(3, string(point(0, "route", VB[m]))), 2, string(point(0, "route", VB[m])),
                                    string(point(0, "bande", VB[m])), float(point(0, "s_end", VB[m])) - 1e-4);
            vector2 I;
            l4_inter(pa0, HA[m], pb0, HB[m], I);
            float tg = tan(radians(0.5 * abs(DEL[m])));
            float T = Rsel * tg;
            vector2 s1 = I - T * HA[m], s2 = I + T * HB[m];
            float sg = DEL[m] > 0 ? 1.0 : -1.0;
            RR[m] = Rsel; S1[m] = s1; S2[m] = s2; CC[m] = s1 + sg * Rsel * rc_gauche(HA[m]);
            float ta = dot(I - pa0, HA[m]), tb = dot(pb0 - I, HB[m]);
            float ei = max(0.0, T - ta), eo = max(0.0, T - tb);
            float sea = point(0, "s_end", VA[m]), seb = point(0, "s_end", VB[m]);
            EXI[m] = ei; EXO[m] = eo; SA[m] = sea - ei; SB[m] = seb - eo;
            REG[m] = "TAG opposés : plus petit rayon commun qui sépare les deux axes (CU p. 120-122)";
        }
    }
}
// limite de la jonction sur chaque branche : d_j = plus grande sortie d'un arc hors de l'embouchure
int BR[] = expandpointgroup(0, "br4");
float DJ[];
foreach (int p; BR) {
    float dj = 0.0;
    for (int m = 0; m < n; m++) {
        if (!OK[m] || M_car[m] != string(point(0, "carrefour", p))) continue;
        if (M_de[m] == string(point(0, "branche", p))) dj = max(dj, EXI[m]);
        if (M_vers[m] == string(point(0, "branche", p))) dj = max(dj, EXO[m]);
    }
    dj = ceil(dj / 0.05 - 1e-9) * 0.05;
    push(DJ, dj);
    setpointattrib(0, "d_j", p, dj);
    setpointattrib(0, "s_j", p, float(point(0, "s_end", p)) - dj);
}
// points de voie à la limite de la jonction (positions rangées : le wrangle relit son entrée, pas ses écritures)
vector2 VJP[];
float VSJ[];
foreach (int v; VO) {
    int p = l4_br(string(point(0, "carrefour", v)), string(point(0, "branche", v)));
    int k = find(BR, p);
    float dj = k >= 0 ? DJ[k] : 0.0;
    string rid = point(0, "route", v);
    int pr = l4_ref(3, rid);
    float sj = float(point(0, "s_end", v)) - dj;
    vector2 Pj = l4_axe_pt(3, pr, 2, rid, string(point(0, "bande", v)), sj - 1e-4);
    setpointattrib(0, "s_j", v, sj);
    setpointattrib(0, "d_j", v, dj);
    setpointattrib(0, "P", v, rc_h(Pj, 0.0));
    push(VJP, Pj); push(VSJ, sj);
}
// axes des voies, de la limite de jonction vers l'extrémité libre de la route (graphe de voies) : pas de 1 m, tant que
// la bande garde au moins la moitié de sa largeur à la jonction ; sens de circulation (entrante : vers la jonction)
foreach (string a; {"v_type", "branche", "route", "bande"}) addprimattrib(0, a, "");
addprimattrib(0, "v_entrante", 0); addprimattrib(0, "s0", 0.0); addprimattrib(0, "s1", 0.0);
foreach (int v; VO) {
    string rid = point(0, "route", v);
    int pr = l4_ref(3, rid);
    float sj = VSJ[find(VO, v)];
    string bande = point(0, "bande", v);
    float w0 = point(0, "largeur", v);
    vector2 Q[];
    float s = sj, s_min = sj;
    for (int it = 0; it < 100000; it++) {
        float a, b;
        float sq = it == 0 ? sj - 1e-4 : max(s, 0.0);
        int bb = l4_bande_t(3, pr, 2, rid, bande, sq, a, b);
        if (bb < 0 || (a - b) < 0.5 * w0) break;
        push(Q, rg_local_st(3, pr, max(s, 0.0), 0.5 * (a + b)));
        s_min = max(s, 0.0);
        if (s <= 0.0) break;
        s = max(0.0, s - 1.0);
    }
    if (len(Q) < 2) continue;
    if (point(0, "entrante", v)) Q = reverse(Q);
    int pts[];
    foreach (vector2 q; Q) push(pts, addpoint(0, rc_h(q, 0.0)));
    int pa = addprim(0, "polyline", pts);
    setprimgroup(0, "voie_axe", pa, 1);
    setprimattrib(0, "carrefour", pa, string(point(0, "carrefour", v)));
    setprimattrib(0, "branche", pa, string(point(0, "branche", v)));
    setprimattrib(0, "route", pa, rid); setprimattrib(0, "bande", pa, bande);
    setprimattrib(0, "v_type", pa, string(point(0, "type", v)));
    setprimattrib(0, "v_entrante", pa, int(point(0, "entrante", v)));
    setprimattrib(0, "s0", pa, s_min); setprimattrib(0, "s1", pa, sj);
}
// polylignes : axe réel de la voie d'entrée de s_j à sA, arc (et droites dans le cœur), axe réel de la voie de sortie
// de sB à s_j
for (int m = 0; m < n; m++) {
    if (!OK[m]) continue;
    string ra = point(0, "route", VA[m]), rb = point(0, "route", VB[m]);
    string ba = point(0, "bande", VA[m]), bb = point(0, "bande", VB[m]);
    int pra = l4_ref(3, ra), prb = l4_ref(3, rb);
    float sja = VSJ[find(VO, VA[m])], sjb = VSJ[find(VO, VB[m])];
    vector2 Q[];
    vector2 Qa[] = l4_axe_poly(3, pra, 2, ra, ba, sja, SA[m], 1.0);
    foreach (vector2 q; Qa)
        if ((len(Q) == 0 || length(q - Q[-1]) > 1e-4) && (TYP[m] == 0 || len(Q) == 0 || dot(q - S1[m], HA[m]) < -1e-4)) push(Q, q);
    if (TYP[m] == 1) {
        if (length(S1[m] - Q[-1]) > 1e-4) push(Q, S1[m]);
        float a0 = degrees(atan2(S1[m].y - CC[m].y, S1[m].x - CC[m].x));
        vector2 A[] = l4_arc(CC[m], RR[m], a0, a0 + DEL[m], DA, FL);
        for (int k = 1; k + 1 < len(A); k++) push(Q, A[k]);
        push(Q, S2[m]);
    }
    vector2 Qb[] = l4_axe_poly(3, prb, 2, rb, bb, SB[m], sjb, 1.0);
    foreach (vector2 q; Qb)
        if (length(q - Q[-1]) > 1e-4 && (TYP[m] == 0 || dot(q - S2[m], HB[m]) > 1e-4)) push(Q, q);
    int pts[];
    foreach (vector2 q; Q) push(pts, addpoint(0, rc_h(q, 0.0)));
    int t = addprim(0, "polyline", pts);
    setprimgroup(0, "trajectoire_l4", t, 1);
    setprimattrib(0, "id", t, M_id[m]); setprimattrib(0, "carrefour", t, M_car[m]);
    setprimattrib(0, "mouvement", t, M_mv[m]); setprimattrib(0, "de_branche", t, M_de[m]);
    setprimattrib(0, "de_bande", t, M_deb[m]); setprimattrib(0, "vers_branche", t, M_vers[m]);
    setprimattrib(0, "vers_bande", t, M_versb[m]); setprimattrib(0, "tags", t, M_tags[m]);
    setprimattrib(0, "vehicule", t, M_tags[m] == "velo" ? "velo" : chs("../vehicule"));
    setprimattrib(0, "rayon", t, RR[m]); setprimattrib(0, "rayon_min", t, M_tags[m] == "velo" ? 0.0 : RMIN);
    setprimattrib(0, "angle_deg", t, DEL[m]); setprimattrib(0, "ext_entree", t, EXI[m]);
    setprimattrib(0, "ext_sortie", t, EXO[m]); setprimattrib(0, "regle_rayon", t, REG[m]);
    setprimattrib(0, "ecart_lateral", t, LAT[m]); setprimattrib(0, "garde_guidage", t, GAR[m]);
    float de = 0.0, ds = 0.0;
    if (TYP[m] == 1) {
        if (EXI[m] > 0) de = RR[m] - sqrt(max(0.0, RR[m] * RR[m] - EXI[m] * EXI[m]));
        if (EXO[m] > 0) ds = RR[m] - sqrt(max(0.0, RR[m] * RR[m] - EXO[m] * EXO[m]));
    }
    setprimattrib(0, "dev_entree", t, de); setprimattrib(0, "dev_sortie", t, ds);
    float S[] = rc_cumul(Q);
    setprimattrib(0, "longueur", t, S[-1]);
    if (M_src[m] >= 0) {
        setprimattrib(0, "guide", t, int(point(0, "guide", M_src[m])));
        setprimattrib(0, "guidage", t, string(point(0, "guidage", M_src[m])));
        setprimattrib(0, "priorite", t, int(point(0, "priorite", M_src[m])));
        string ph[] = point(0, "phases", M_src[m]);
        setprimattrib(0, "phases", t, ph);
    }
    setprimattrib(0, "faisable", t, (M_tags[m] == "velo" || TYP[m] == 0 || RR[m] >= RMIN - 1e-6) ? 1 : 0);
}
setdetailattrib(0, "rg_l4_avertissements", avert, "append");
"""

# --------------------------------------------------------------------------------------------------------- conflits
VEX_CONFLITS = r"""
// (4) points de conflit (détail) : pour chaque paire de trajectoires, divergence (même voie d'entrée), convergence (même
// voie de sortie), croisement (intersection géométrique des axes ; une paire comptée une fois, premier point le long
// de la première). Liste complète des mouvements autorisés (plan § 2.4 étape 8 ; CU p. 120-122).
foreach (string a; {"type", "a", "b", "carrefour", "famille"}) addpointattrib(0, a, "");
addpointattrib(0, "n_points", 0); addpointattrib(0, "meme_phase", 0);
int TR[] = expandprimgroup(0, "trajectoire_l4");
int nc = 0, nv = 0, nd = 0, ncv = 0, nvv = 0, ndv = 0, ncp = 0;
for (int x = 0; x < len(TR); x++) {
    int i = TR[x];
    vector2 A[] = l4_pts_prim(0, i);
    for (int y = x + 1; y < len(TR); y++) {
        int j = TR[y];
        if (string(prim(0, "carrefour", i)) != string(prim(0, "carrefour", j))) continue;
        vector2 B[] = l4_pts_prim(0, j);
        int memeE = string(prim(0, "de_branche", i)) == string(prim(0, "de_branche", j)) && string(prim(0, "de_bande", i)) == string(prim(0, "de_bande", j));
        int memeS = string(prim(0, "vers_branche", i)) == string(prim(0, "vers_branche", j)) && string(prim(0, "vers_bande", i)) == string(prim(0, "vers_bande", j));
        string ty = "";
        vector2 X = {0, 0};
        int np = 0;
        if (memeE && memeS) continue;
        if (memeE) {
            ty = "divergence";
            vector2 Ad[] = rc_densifier(A, 0.05);
            X = Ad[0];
            foreach (vector2 q; Ad) { float u; if (abs(l4_dist_signee(B, q, u)) > 0.10) { X = q; break; } }
            np = 1;
        } else if (memeS) {
            ty = "convergence";
            vector2 Ad[] = rc_densifier(A, 0.05);
            X = Ad[-1];
            for (int k = len(Ad) - 1; k >= 0; k--) { float u; if (abs(l4_dist_signee(B, Ad[k], u)) > 0.10) { X = Ad[k]; break; } }
            np = 1;
        } else {
            float best = 1e18;
            float acc = 0.0;
            for (int a = 0; a + 1 < len(A); a++) {
                for (int b = 0; b + 1 < len(B); b++) {
                    vector2 Y; float ua;
                    if (l4_seg_inter(A[a], A[a + 1], B[b], B[b + 1], Y, ua)) {
                        float sa = acc + ua * length(A[a + 1] - A[a]);
                        int dup = 0;
                        if (np > 0 && abs(sa - best) < 1e-6) dup = 1;
                        if (!dup) np++;
                        if (sa < best) { best = sa; X = Y; }
                    }
                }
                acc += length(A[a + 1] - A[a]);
            }
            if (np > 0) ty = "croisement";
        }
        if (ty == "") continue;
        int p = addpoint(0, rc_h(X, 0.0));
        setpointgroup(0, "conflit", p, 1);
        setpointattrib(0, "type", p, ty);
        setpointattrib(0, "a", p, string(prim(0, "id", i))); setpointattrib(0, "b", p, string(prim(0, "id", j)));
        setpointattrib(0, "carrefour", p, string(prim(0, "carrefour", i)));
        string fa = string(prim(0, "tags", i)) == "velo" || string(prim(0, "tags", j)) == "velo" ? "velo" : "vl_vl";
        setpointattrib(0, "famille", p, fa);
        setpointattrib(0, "n_points", p, np);
        string pi[] = prim(0, "phases", i), pj[] = prim(0, "phases", j);
        int mp = 0;
        foreach (string s; pi) if (s != "" && find(pj, s) >= 0) mp = 1;
        setpointattrib(0, "meme_phase", p, mp);
        if (fa == "vl_vl") {
            if (ty == "croisement") ncv++; else if (ty == "convergence") nvv++; else ndv++;
            if (ty == "croisement" && mp) ncp++;
        }
        if (ty == "croisement") nc++; else if (ty == "convergence") nv++; else nd++;
    }
}
setdetailattrib(0, "rg_l4_conflits", sprintf("croisements %d, convergences %d, divergences %d (VL/VL : %d, %d, %d ; croisements dans une même phase : %d)",
                                              nc, nv, nd, ncv, nvv, ndv, ncp));
"""

# --------------------------------------------------------------------------------------------------------- zone
VEX_ZONE = r"""
// (5) zone de conflit (détail) : polygone du cœur du carrefour (frontière du SOLVEUR : embouchures au bord de la
// chaussée abordée et aux nez d'îlots, bords de chaussée et coins) prolongé, sur chaque branche munie d'une ligne
// d'arrêt ou d'effet (peinte, ou virtuelle : le passage piéton en tient lieu, ARB-01), jusqu'à cette ligne (bande de
// chaussée entre ses bords). RF-GV-TRJ-001, RF-MQ-CAR-02, RF-MQ-CAR-04 (aucune ligne longitudinale dedans sauf
// guidage) ; plan § 2.4 étape 10.
addprimattrib(0, "partie", ""); addprimattrib(0, "aire_m2", 0.0); addprimattrib(0, "branche", "");
addprimattrib(0, "s_arret", 0.0); addprimattrib(0, "route", "");
float WL[] = array(chf("../effet_largeur"), chf("../cedez_largeur"), chf("../stop_largeur"));
float aire = 0.0;
foreach (int f; expandprimgroup(1, "frontiere")) {
    vector2 Q[] = l4_pts_prim(1, f);
    int pts[];
    foreach (vector2 q; Q) push(pts, addpoint(0, rc_h(q, 0.0)));
    int z = addprim(0, "poly", pts);
    setprimgroup(0, "zone_conflit", z, 1);
    setprimattrib(0, "carrefour", z, string(prim(1, "carrefour", f)));
    setprimattrib(0, "partie", z, "coeur");
    float a = abs(l4_aire(Q));
    setprimattrib(0, "aire_m2", z, a);
    aire += a;
}
foreach (int p; expandpointgroup(0, "br4")) {
    float dist = point(0, "ligne_distance", p);
    string lt = point(0, "ligne_type", p);
    if (dist <= 0.0 && lt != "virtuelle") continue;
    float wl = lt == "EFFET_FEUX" ? WL[0] : (lt == "CEDEZ" ? WL[1] : (lt == "STOP" ? WL[2] : 0.0));
    float sf = point(0, "s_front", p), se = point(0, "s_end", p);
    float sa = sf - dist - wl;
    if (sa >= se - 1e-6) continue;
    string rid = point(0, "route", p);
    int pr = l4_ref(3, rid);
    vector2 Q[];
    float SSA[] = array(sa, se);
    foreach (float s; SSA) {
        int sp = l4_section(3, pr, 2, rid, s - 1e-4);
        float tg = point(0, "t_g", p), td = point(0, "t_d", p);
        l4_bords(2, sp, s - 1e-4, tg, td);
        if (s == sa) { push(Q, rg_local_st(3, pr, s, td)); push(Q, rg_local_st(3, pr, s, tg)); }
        else { push(Q, rg_local_st(3, pr, s, tg)); push(Q, rg_local_st(3, pr, s, td)); }
    }
    // Q : (sa, td), (sa, tg), (se, tg), (se, td)
    vector2 R[] = array(Q[0], Q[3], Q[2], Q[1]);
    int pts[];
    foreach (vector2 q; R) push(pts, addpoint(0, rc_h(q, 0.0)));
    int z = addprim(0, "poly", pts);
    setprimgroup(0, "zone_conflit", z, 1);
    setprimattrib(0, "carrefour", z, string(point(0, "carrefour", p)));
    setprimattrib(0, "partie", z, "approche");
    setprimattrib(0, "branche", z, string(point(0, "branche", p)));
    setprimattrib(0, "route", z, rid);
    setprimattrib(0, "s_arret", z, sa);
    float a = abs(l4_aire(R));
    setprimattrib(0, "aire_m2", z, a);
    aire += a;
}
setdetailattrib(0, "rg_l4_zone_m2", aire);
"""

# --------------------------------------------------------------------------------------------------------- flèches, sas
VEX_FLECHES = r"""
// (6) flèches d'affectation et figurines des sas (détail ; entrée 0 : flux + gabarits du dossier 08 en groupe « gab »).
// Flèches (DEF-017, ARB-11, RF-MQ-DIR-02/-03/-04/-06/-09) : gabarit exact du dossier 08 (origine au pied de la tige, x à
// droite, y dans le sens de circulation), tige sur l'axe de la voie, orientée le long de la voie ; pointe de la dernière
// à « recul » (1,50 m) en amont du bord amont de la ligne d'arrêt / d'effet qui couvre la voie (sinon du passage
// piéton, sinon de l'embouchure) ; interdistance de pointe à pointe ; nombre réduit si la voie n'a pas sa largeur
// (≥ fraction de la largeur à l'embouchure) et n'est pas droite (déviation ≤ rectitude) sous toute la flèche (« 2 si
// la voie est courte », ARB-11).
// Sas vélos (RF-MQ-SAS-01, DEF-016) : figurine VELO dans l'axe de chaque voie de circulation couverte par la ligne
// avant du sas, centrée entre les deux lignes du sas.
l4_attributs_marques();
foreach (string a; {"m_classe", "m_id", "m_gabarit", "m_route", "m_branche", "m_bande", "m_regles", "m_carrefour"})
    addpointattrib(0, a, "");
foreach (string a; {"m_s0", "m_s1", "m_t", "m_cap_deg", "m_s_ligne", "m_largeur_voie", "m_recul"}) addpointattrib(0, a, 0.0);
addpointattrib(0, "m_rang", 0); addpointattrib(0, "m_n_demande", 0);
string avert[];
float FR = chf("../fleche_fraction_largeur");
float DENS = chf("../pas_densification");
float WL[] = array(chf("../effet_largeur"), chf("../cedez_largeur"), chf("../stop_largeur"));
float us = chf("../usure_peinture");
int GAB[] = expandprimgroup(0, "gab");
foreach (int f; expandpointgroup(0, "fl")) {
    string car = point(0, "carrefour", f), bid = point(0, "branche", f), bande = point(0, "bande", f);
    string gab = point(0, "gabarit", f);
    int pb = l4_br(car, bid);
    int v = l4_voie(car, bid, bande, 1);
    if (pb < 0 || v < 0) { push(avert, sprintf("%s %s %s : voie des flèches absente", car, bid, bande)); continue; }
    string rid = point(0, "route", pb);
    int pr = l4_ref(3, rid);
    float se = point(0, "s_end", pb);
    float tg0 = point(0, "t0", v), td0 = point(0, "t1", v);
    float w0 = tg0 - td0;
    float sl;
    float sc = -1e18;
    l4_ligne_voie(car, bid, rid, pr, tg0, td0, 1, WL, sc);
    string ref = "ligne";
    if (sc < -1e17) {
        // passage piéton de la route (le plus proche de l'embouchure)
        float bestd = 1e18;
        foreach (int q; expandpointgroup(1, "passage")) {
            if (string(point(1, "route", q)) != rid) continue;
            float s = point(1, "s", q), lg = point(1, "largeur", q);
            if (s > se + 1e-6 || se - s > bestd) continue;
            bestd = se - s; sc = s - 0.5 * lg; ref = "passage";
        }
    }
    if (sc < -1e17) { sc = se; ref = "embouchure"; }
    int gp[] = findattribval(0, "prim", "gabarit", gab);
    int gx[];
    foreach (int g; gp) if (inprimgroup(0, "gab", g)) push(gx, g);
    if (len(gx) == 0) { push(avert, sprintf("%s %s : gabarit %s absent", bid, bande, gab)); continue; }
    float Lg = prim(0, "longueur_m", gx[0]);
    float recul = point(0, "recul", f), iv = point(0, "intervalle", f);
    int nd = point(0, "nombre", f);
    float s_tip = sc - recul;
    for (int k = 0; k < nd; k++) {
        float sf = s_tip - Lg - k * iv;
        // la voie doit avoir sa largeur sous toute la flèche
        int ok = sf > 0.0;
        float ta[], ss[];
        float SSF[] = array(sf, sf + 0.5 * Lg, sf + Lg);
        foreach (float s; SSF) {
            float a, b;
            int bb = l4_bande_t(3, pr, 2, rid, bande, s, a, b);
            if (bb < 0 || (a - b) < FR * w0) ok = 0;
            push(ta, 0.5 * (a + b)); push(ss, s);
        }
        if (ok) {
            // voie droite sous la flèche (la flèche est rigide) : déviation de l'axe ≤ rectitude
            vector2 F0 = rg_local_st(3, pr, ss[0], ta[0]), Fm = rg_local_st(3, pr, ss[1], ta[1]), F1 = rg_local_st(3, pr, ss[2], ta[2]);
            if (abs(l4_ang(Fm - F0, F1 - Fm)) > chf("../fleche_rectitude")) ok = 0;
        }
        if (!ok) break;
        vector2 o = rg_local_st(3, pr, sf, ta[0]);
        vector2 pt = rg_local_st(3, pr, sf + Lg, ta[2]);
        vector2 ey = normalize(pt - o);
        vector2 ex = set(ey.y, -ey.x);
        string idm = sprintf("%s.%s.%s.fl%d", re_replace("^C-", "", car), re_replace("^B-", "", bid), bande, k + 1);
        string ent = "MQ_L4_" + re_replace("[^A-Za-z0-9]", "_", idm);
        foreach (int g; gx) {
            vector2 E0[];
            foreach (int p; primpoints(0, g)) { vector Pg = point(0, "P", p); push(E0, o + Pg.x * ex + (-Pg.z) * ey); }
            vector2 Ed[] = rg_m_densifier_xy(E0, DENS);
            int np = rg_m_poly(0, Ed);
            l4_marque(np, ent, idm, "fleche", gab, gab, rg_m_materiau("blanc", us), us, prim(0, "partie", g),
                      prim(0, "anneau", g), rid, "", "", 0.0, sf, sf + Lg, k, 0);
            setprimgroup(0, "marque_l4", np, 1);
        }
        int tp = addpoint(0, rc_h(o, 0.0));
        setpointgroup(0, "table_l4", tp, 1);
        setpointattrib(0, "m_classe", tp, "fleche"); setpointattrib(0, "m_id", tp, idm);
        setpointattrib(0, "m_gabarit", tp, gab); setpointattrib(0, "m_route", tp, rid);
        setpointattrib(0, "m_branche", tp, bid); setpointattrib(0, "m_bande", tp, bande);
        setpointattrib(0, "m_carrefour", tp, car);
        setpointattrib(0, "m_s0", tp, sf); setpointattrib(0, "m_s1", tp, sf + Lg); setpointattrib(0, "m_t", tp, ta[0]);
        setpointattrib(0, "m_cap_deg", tp, degrees(atan2(ey.y, ey.x))); setpointattrib(0, "m_s_ligne", tp, sc);
        setpointattrib(0, "m_largeur_voie", tp, w0); setpointattrib(0, "m_recul", tp, recul);
        setpointattrib(0, "m_rang", tp, k); setpointattrib(0, "m_n_demande", tp, nd);
        setpointattrib(0, "m_regles", tp, string(point(0, "regles", f)) + " RF-MQ-DIR-02 RF-MQ-DIR-03 RF-MQ-DIR-09 (réf. " + ref + ")");
    }
}
// sas vélos
int gv[] = findattribval(0, "prim", "gabarit", chs("../gabarit_sas"));
int gvx[];
foreach (int g; gv) if (inprimgroup(0, "gab", g)) push(gvx, g);
float bx0 = 1e18, bx1 = -1e18, by0 = 1e18, by1 = -1e18;
foreach (int g; gvx) foreach (int p; primpoints(0, g)) { vector Pg = point(0, "P", p); bx0 = min(bx0, Pg.x); bx1 = max(bx1, Pg.x); by0 = min(by0, -Pg.z); by1 = max(by1, -Pg.z); }
foreach (int pb; expandpointgroup(0, "br4")) {
    if (float(point(0, "sas_prof", pb)) <= 0.0) continue;
    if (len(gvx) == 0) { push(avert, "gabarit de figurine du sas absent"); break; }
    string car = point(0, "carrefour", pb), bid = point(0, "branche", pb), rid = point(0, "route", pb);
    int pr = l4_ref(3, rid);
    foreach (int v; expandpointgroup(0, "voie")) {
        if (string(point(0, "branche", v)) != bid || string(point(0, "carrefour", v)) != car || int(point(0, "entrante", v)) != 1) continue;
        if (!startswith(string(point(0, "type", v)), "voie")) continue;
        float tg0 = point(0, "t0", v), td0 = point(0, "t1", v);
        float sar, sav;
        float c_ar = l4_ligne_voie(car, bid, rid, pr, tg0, td0, 1, WL, sar);
        float c_av = l4_ligne_voie(car, bid, rid, pr, tg0, td0, 0, WL, sav);
        if (c_ar > 1e17 || c_av < -1e17 || c_av - c_ar < 1.0) continue;     // voie hors du sas
        // bords intérieurs du sas : aval de la ligne arrière, amont de la ligne avant
        float wr = sar;                                    // bord amont de la ligne arrière
        float s_in0 = c_ar + (c_ar - wr);                  // bord aval de la ligne arrière
        float s_in1 = c_av - (sav - c_av);                 // bord amont de la ligne avant
        float s_c = 0.5 * (s_in0 + s_in1);
        float a, b;
        l4_bande_t(3, pr, 2, rid, point(0, "bande", v), s_c, a, b);
        float ta = 0.5 * (a + b);
        vector2 c = rg_local_st(3, pr, s_c, ta);
        vector2 ey = l4_tan(3, pr, s_c);
        vector2 ex = set(ey.y, -ey.x);
        vector2 o = c - 0.5 * (bx0 + bx1) * ex - 0.5 * (by0 + by1) * ey;
        string idm = sprintf("%s.%s.%s.sas", re_replace("^C-", "", car), re_replace("^B-", "", bid), string(point(0, "bande", v)));
        string ent = "MQ_L4_" + re_replace("[^A-Za-z0-9]", "_", idm);
        foreach (int g; gvx) {
            vector2 E0[];
            foreach (int p; primpoints(0, g)) { vector Pg = point(0, "P", p); push(E0, o + Pg.x * ex + (-Pg.z) * ey); }
            int np = rg_m_poly(0, E0);
            l4_marque(np, ent, idm, "figurine", chs("../gabarit_sas"), chs("../gabarit_sas"), rg_m_materiau("blanc", us),
                      us, prim(0, "partie", g), prim(0, "anneau", g), rid, "", "", 0.0, s_c, s_c, 0, 0);
            setprimgroup(0, "marque_l4", np, 1);
        }
        int tp = addpoint(0, rc_h(c, 0.0));
        setpointgroup(0, "table_l4", tp, 1);
        setpointattrib(0, "m_classe", tp, "figurine_sas"); setpointattrib(0, "m_id", tp, idm);
        setpointattrib(0, "m_gabarit", tp, chs("../gabarit_sas")); setpointattrib(0, "m_route", tp, rid);
        setpointattrib(0, "m_branche", tp, bid); setpointattrib(0, "m_bande", tp, string(point(0, "bande", v)));
        setpointattrib(0, "m_carrefour", tp, car);
        setpointattrib(0, "m_s0", tp, s_in0); setpointattrib(0, "m_s1", tp, s_in1); setpointattrib(0, "m_t", tp, ta);
        setpointattrib(0, "m_cap_deg", tp, degrees(atan2(ey.y, ey.x)));
        setpointattrib(0, "m_largeur_voie", tp, a - b);
        setpointattrib(0, "m_regles", tp, "RF-MQ-SAS-01 DEF-016");
    }
}
setdetailattrib(0, "rg_l4_avertissements", avert, "append");
"""

# --------------------------------------------------------------------------------------------------------- tirets
VEX_TIRETS_GUIDAGE = r"""
// (7) tirets des lignes de guidage (détail ; entrée 1 : flux avec les lignes « guidage ») : T'2 (RF-MQ-MOD-T'2 :
// traits et intervalles de 0,50 m) de la largeur du modèle (0,10 m, RF-MQ-GUI-01, ARB-08) le long de la ligne courbe ;
// motif centré sur la longueur, un trait à chaque bout si la longueur le permet ([G], comme les lignes transversales du
// lot L3) ; chaque trait suit la courbe (sommets au pas de 5 cm). Entrée 0 : flux (lignes « guidage »).
l4_attributs_marques();
float tr = chf("../tp2_trait"), iv = chf("../tp2_intervalle");
float us = chf("../usure_peinture");
foreach (int g; expandprimgroup(0, "guidage")) {
    vector2 Q[] = l4_pts_prim(0, g);
    float S[] = rc_cumul(Q);
    float L = S[-1];
    float w = prim(0, "largeur_m", g);
    int nt = max(1, int(floor((L + iv) / (tr + iv) + 1e-9)));
    float tot = nt * tr + (nt - 1) * iv;
    float o = 0.5 * (L - tot);
    string gid = prim(0, "id", g);
    for (int k = 0; k < nt; k++) {
        float u0 = o + k * (tr + iv), u1 = u0 + tr;
        vector2 D[] = l4_sous(Q, u0, u1, 0.05);
        vector2 Pg[] = l4_ruban(D, w, 0);
        int np = rg_m_poly(0, Pg);
        string ent = sprintf("ML_L4_%s_t%03d", re_replace("[^A-Za-z0-9]", "_", gid), k);
        l4_marque(np, ent, sprintf("%s_t%03d", gid, k), "ligne", "tiret", "", rg_m_materiau("blanc", us), us, 0, 0, "",
                  "guidage", string(prim(0, "modulation", g)), w, u0, u1, k, 1);
        setprimattrib(0, "gabarit", np, "GUIDAGE");
        setprimgroup(0, "tirets_l4", np, 1);
    }
}
"""

# --------------------------------------------------------------------------------------------------------- axe prioritaire
VEX_AXE = r"""
// (8) discontinue axiale de la route prioritaire prolongée dans le carrefour (détail ; entrée 0 : flux, 1 : LIGNES de
// rg::marquages, 2 : NIVEAUX, 3 : références) : RF-MQ-CAR-01 / RF-GV-TRJ-002 (IISR7 117-1 p. 36 : les discontinues
// de la route prioritaire ne sont ni interrompues ni remplacées par une continue au droit de l'intersection). Deux
// branches « prioritaire » opposées (azimuts à 180 ± 20°) : ligne de la limite entre la dernière bande sortante et la
// première bande entrante (axe) ; entre le dernier tiret de chacune, n tirets de la même modulation (trait, largeur,
// matériau lus sur les tirets peints), n = arrondi((G − i) / (t + i)), intervalles égaux ([G] : les motifs des deux
// branches ne se raccordent pas exactement ; l'écart à l'intervalle nominal est rangé). Chaque tiret est fait de deux
// demi-empreintes de part et d'autre de son axe (comme rg::marquages : couronne).
l4_attributs_marques();
string rap[];
float DENS = chf("../pas_densification_lignes");
int BR[] = expandpointgroup(0, "br4");
foreach (int a; BR) {
    if (string(point(0, "regime", a)) != "prioritaire") continue;
    foreach (int b; BR) {
        if (b <= a || string(point(0, "regime", b)) != "prioritaire" || string(point(0, "carrefour", b)) != string(point(0, "carrefour", a))) continue;
        if (l4_ecart180(point(0, "azimut", a), point(0, "azimut", b)) > 20.0) continue;
        vector2 PX[];
        float TT[], II[], WW[], US[];
        string MOD[], MAT[], CLE[];
        int ok = 1;
        int PAB[] = array(a, b);
        foreach (int p; PAB) {
            string ids[] = point(0, "bandes_ids", p), sens[] = point(0, "bandes_sens", p);
            string cle = "";
            int kg = -1;
            for (int k = 0; k + 1 < len(ids); k++) if (sens[k] == "arriere" && sens[k + 1] == "avant") { cle = ids[k] + "|" + ids[k + 1]; kg = k; }
            string rid = point(0, "route", p);
            float se = point(0, "s_end", p);
            int prs[] = findattribval(1, "prim", "route", rid);
            string ENT[];
            float L0[], L1[];
            string mod = "", mat = "";
            float wl = 0.0, us = 0.0;
            foreach (int q; prs) {
                if (string(prim(1, "cle", q)) != cle || string(prim(1, "classe", q)) != "ligne") continue;
                string ent = prim(1, "pj_entite", q);
                float s0 = prim(1, "s0", q), s1 = prim(1, "s1", q);
                int ke = find(ENT, ent);
                if (ke < 0) { push(ENT, ent); push(L0, s0); push(L1, s1); }
                else { L0[ke] = min(L0[ke], s0); L1[ke] = max(L1[ke], s1); }
                mod = prim(1, "modulation", q); mat = prim(1, "materiau_id", q); wl = prim(1, "largeur_m", q);
                us = prim(1, "usure", q);
            }
            int o[] = argsort(L0);
            float tr = 0.0, iv = 1e18, last = -1e18;
            for (int k = 0; k < len(o); k++) {
                tr = max(tr, L1[o[k]] - L0[o[k]]);
                if (k > 0) iv = min(iv, L0[o[k]] - L1[o[k - 1]]);
                if (L1[o[k]] <= se + 1e-6) last = max(last, L1[o[k]]);
            }
            if (cle == "" || len(o) < 2 || mod == "continue" || last < -1e17) { ok = 0; break; }
            int pr = l4_ref(3, rid);
            int sp = l4_section(3, pr, 2, rid, last - 1e-4);
            string bid[] = point(2, "b_id", sp);
            float T[] = rg_t_limites(2, sp, last - 1e-4);
            int kb = find(bid, ids[kg]);
            float tl = kb >= 0 ? T[kb + 1] : 0.0;
            push(PX, rg_local_st(3, pr, last, tl));
            push(TT, tr); push(II, iv); push(WW, wl); push(US, us); push(MOD, mod); push(MAT, mat); push(CLE, cle);
        }
        string ba = re_replace("^B-", "", string(point(0, "branche", a))), bb = re_replace("^B-", "", string(point(0, "branche", b)));
        if (!ok || len(PX) < 2) { push(rap, sprintf("%s / %s : pas de discontinue axiale à prolonger", ba, bb)); continue; }
        vector2 P0 = PX[0], P1 = PX[1];
        float t = TT[0], iv = II[0];
        float G = length(P1 - P0);
        int n = max(0, int(rint((G - iv) / (t + iv))));
        float gap = (G - n * t) / (n + 1);
        vector2 u = normalize(P1 - P0);
        string gid = sprintf("%s_axe_%s_%s", re_replace("[^A-Za-z0-9]", "_", string(point(0, "carrefour", a))), ba, bb);
        for (int k = 0; k < n; k++) {
            float u0 = gap + k * (t + gap), u1 = u0 + t;
            vector2 D2[] = array(P0 + u0 * u, P0 + u1 * u);
            vector2 D[] = rc_densifier(D2, DENS);
            for (int h = 1; h <= 2; h++) {
                vector2 Pg[] = l4_ruban(D, WW[0], h);
                int np = rg_m_poly(0, Pg);
                l4_marque(np, sprintf("ML_L4_%s_t%03d", gid, k), sprintf("%s_t%03d", gid, k), "ligne", "tiret", "",
                          MAT[0], US[0], h - 1, 0, "", "axe_prioritaire:" + CLE[0], MOD[0], WW[0], u0, u1, k, 1);
                setprimgroup(0, "axe_l4", np, 1);
            }
        }
        push(rap, sprintf("%s / %s : %s %s, écart entre les derniers tirets %.3f m, %d tiret(s) de %.2f m, intervalles %.3f m (nominal %.2f m)",
                          ba, bb, CLE[0], MOD[0], G, n, t, gap, iv));
    }
}
setdetailattrib(0, "rg_l4_axe", rap);
"""

# --------------------------------------------------------------------------------------------------------- filtre
VEX_FILTRE = r"""
// (9) lignes de la section courante dans le carrefour (détail sur les LIGNES et MARQUES de rg::marquages ; entrée 1 : flux
// (zones, br4, voies), 2 : NIVEAUX, 3 : références). RF-MQ-CAR-02, RF-MQ-CAR-04 (aucune ligne longitudinale dans
// l'intersection sauf guidage) : morceau retiré si son centre est dans le cœur ; sur une approche munie d'une ligne
// d'arrêt / d'effet, morceau retiré s'il est en aval du bord amont de la ligne, coupé à ce bord s'il le chevauche
// (les sommets en aval sont ramenés en s_arret à leur t : les morceaux sont des quadrilatères (s, t) de la route).
// RF-MQ-SC-11, RF-OSM-MRQ-021 : rive d'une branche prioritaire retirée au droit d'une chaussée affluente, du point de
// tangence du coin à l'embouchure, au-delà de l'axe de la voie de circulation extrême du côté du coin.
addprimattrib(0, "rg_l4_retire", 0);
addprimattrib(0, "rg_l4_raison", "");
int ZC[], ZA[];
foreach (int z; expandprimgroup(1, "zone_conflit")) { if (string(prim(1, "partie", z)) == "coeur") push(ZC, z); else push(ZA, z); }
for (int pr = 0; pr < nprimitives(0); pr++) {
    vector2 Q[] = l4_pts_prim(0, pr);
    vector2 c = {0, 0};
    foreach (vector2 q; Q) c += q;
    c /= max(1, len(Q));
    int fait = 0;
    string cl = prim(0, "classe", pr);
    if (cl != "ligne") {
        // marques de section : bande de passage peinte sur un terre-plein (refuge) retirée (le passage ne se peint que
        // sur la chaussée, RF-MQ-PP-01 ; DEF-022 : refuge au niveau du trottoir ou abaissé)
        string rid0 = prim(0, "route", pr);
        if (cl != "passage" || rid0 == "") continue;
        int prr0 = l4_ref(3, rid0);
        float s0_, t0_;
        rg_st_local(3, prr0, c.x, c.y, s0_, t0_);
        int sp0 = l4_section(3, prr0, 2, rid0, s0_);
        if (sp0 < 0) continue;
        string bty[] = point(2, "b_type", sp0);
        float T0[] = rg_t_limites(2, sp0, s0_);
        for (int b = 0; b + 1 < len(T0); b++)
            if (t0_ <= T0[b] && t0_ >= T0[b + 1] && (bty[b] == "terre_plein" || bty[b] == "separateur")) {
                setprimattrib(0, "rg_l4_retire", pr, 1); setprimattrib(0, "rg_l4_raison", pr, "bande de passage sur un terre-plein (refuge)");
            }
        continue;
    }
    foreach (int z; ZC) {
        vector2 Z[] = l4_pts_prim(1, z);
        if (rc_dans(Z, c)) { setprimattrib(0, "rg_l4_retire", pr, 1); setprimattrib(0, "rg_l4_raison", pr, "cœur du carrefour"); fait = 1; break; }
    }
    if (fait) continue;
    string rid = prim(0, "route", pr);
    if (rid == "") continue;
    int prr = l4_ref(3, rid);
    float S[], T[];
    float smin = 1e18, smax = -1e18;
    foreach (vector2 q; Q) { float ss, tt; rg_st_local(3, prr, q.x, q.y, ss, tt); push(S, ss); push(T, tt); smin = min(smin, ss); smax = max(smax, ss); }
    foreach (int z; ZA) {
        if (string(prim(1, "route", z)) != rid) continue;
        float sa = prim(1, "s_arret", z);
        if (smax <= sa + 1e-6) continue;
        if (smin >= sa - 1e-6) {
            setprimattrib(0, "rg_l4_retire", pr, 1); setprimattrib(0, "rg_l4_raison", pr, "approche en aval de la ligne d'arrêt");
            fait = 1; break;
        }
        int pp[] = primpoints(0, pr);
        for (int k = 0; k < len(pp); k++)
            if (S[k] > sa) setpointattrib(0, "P", pp[k], rc_h(rg_local_st(3, prr, sa, T[k]), 0.0));
        setprimattrib(0, "rg_l4_retire", pr, 3); setprimattrib(0, "rg_l4_raison", pr, "coupé au bord amont de la ligne d'arrêt");
        fait = 1; break;
    }
    if (fait) continue;
    foreach (int p; expandpointgroup(1, "br4")) {
        if (string(point(1, "route", p)) != rid || string(point(1, "regime", p)) != "prioritaire") continue;
        float s = 0.5 * (smin + smax), t = 0.0;
        foreach (float tt; T) t += tt;
        t /= max(1, len(T));
        foreach (string cote; {"g", "d"}) {
            float rc = point(1, "rayon_coin_" + cote, p);
            int dr = point(1, "droit_" + cote, p);
            if (rc <= 0.0 || dr) continue;
            if (s < float(point(1, "s_tan_" + cote, p)) - 1e-3) continue;
            float tax = cote == "g" ? -1e18 : 1e18;
            foreach (int v; expandpointgroup(1, "voie")) {
                if (string(point(1, "branche", v)) != string(point(1, "branche", p)) || string(point(1, "carrefour", v)) != string(point(1, "carrefour", p))) continue;
                if (!startswith(string(point(1, "type", v)), "voie")) continue;
                float ta = point(1, "t_axe", v);
                if (cote == "g") tax = max(tax, ta); else tax = min(tax, ta);
            }
            if ((cote == "g" && t > tax) || (cote == "d" && t < tax)) {
                setprimattrib(0, "rg_l4_retire", pr, 2);
                setprimattrib(0, "rg_l4_raison", pr, "rive au droit d'une chaussée affluente (" + cote + ")");
                break;
            }
        }
    }
}
"""
