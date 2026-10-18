// rg_carrefour.h : géométrie des carrefours plans (lot L3, HDA rg::carrefours et rg::carrefours_sol), recopiée en tête
// des wrangles après rg_geometrie.h et rg_niveau.h (#include "opdef:" impossible, README_HDA § 1). VEX 64 bits.
//
// Conventions : repère local (x, y) = Lambert-93 − origine ; Houdini (x, z, −y) ; les branches sont tracées VERS le
// centre (extrémité « fin ») ; t positif à gauche de la ligne de référence ; une file de bordure a son côté haut à
// gauche (contrat pj::bordure).
#ifndef RG_CARREFOUR_H
#define RG_CARREFOUR_H

function vector2 rc_xy(vector P) { return set(P.x, -P.z); }
function vector rc_h(vector2 q; float z) { return set(q.x, z, -q.y); }
function float rc_croix(vector2 a; vector2 b) { return a.x * b.y - a.y * b.x; }
function vector2 rc_gauche(vector2 d) { return set(-d.y, d.x); }

// Primitive « échantillonnée » de la route rid (géométrie geo : sortie de rg::graphe ou NIVEAUX) ; −1 sinon.
function int rc_prim_route(int geo; string rid)
{
    int prs[] = findattribval(geo, "prim", "id", rid);
    foreach (int p; prs) if (inprimgroup(geo, "echantillonnees", p)) return p;
    foreach (int p; prs) if (inprimgroup(geo, "routes", p)) return p;
    return len(prs) ? prs[0] : -1;
}

// Point dans un polygone (nombre de croisements).
function int rc_dans(vector2 Q[]; vector2 p)
{
    int n = len(Q);
    int c = 0;
    for (int i = 0, j = n - 1; i < n; j = i++) {
        vector2 a = Q[i], b = Q[j];
        if (((a.y > p.y) != (b.y > p.y)) && (p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x)) c = !c;
    }
    return c;
}

// Distance d'un point à un segment, paramètre u ∈ [0, 1] du pied.
function float rc_dist_seg(vector2 p; vector2 a; vector2 b; export float u)
{
    vector2 ab = b - a;
    float l2 = dot(ab, ab);
    u = l2 > 1e-18 ? clamp(dot(p - a, ab) / l2, 0.0, 1.0) : 0.0;
    return length(p - (a + u * ab));
}

// Distance d'un point à une polyligne, abscisse curviligne du pied (sc) et côté (> 0 : à gauche du sens de parcours).
function float rc_dist_poly(vector2 Q[]; vector2 p; export float sc; export float cote)
{
    float best = 1e18, acc = 0.0;
    sc = 0.0;
    cote = 0.0;
    for (int i = 0; i + 1 < len(Q); i++) {
        float u;
        float d = rc_dist_seg(p, Q[i], Q[i + 1], u);
        float li = length(Q[i + 1] - Q[i]);
        if (d < best - 1e-12) {
            best = d;
            sc = acc + u * li;
            cote = rc_croix(Q[i + 1] - Q[i], p - Q[i]);
        }
        acc += li;
    }
    return best;
}

// Longueurs cumulées d'une polyligne.
function float[] rc_cumul(vector2 Q[])
{
    float S[];
    float acc = 0.0;
    for (int i = 0; i < len(Q); i++) {
        if (i > 0) acc += length(Q[i] - Q[i - 1]);
        push(S, acc);
    }
    return S;
}

// Décalage d'une polyligne à gauche d'une distance variable W[i] (onglet aux sommets).
function vector2[] rc_decaler(vector2 Q[]; float W[])
{
    vector2 out[];
    int n = len(Q);
    for (int i = 0; i < n; i++) {
        vector2 na = {0, 0}, nb = {0, 0};
        if (i > 0) na = rc_gauche(normalize(Q[i] - Q[i - 1]));
        if (i < n - 1) nb = rc_gauche(normalize(Q[i + 1] - Q[i]));
        if (i == 0) na = nb;
        if (i == n - 1) nb = na;
        float den = 1.0 + dot(na, nb);
        vector2 m = den > 1e-6 ? (na + nb) / den : na;
        push(out, Q[i] + W[i] * m);
    }
    return out;
}

// Valeur interpolée linéairement d'une table (S croissant), prolongée constante.
function float rc_interp(float S[]; float V[]; float x)
{
    int n = len(S);
    if (n == 0) return 0.0;
    if (x <= S[0]) return V[0];
    if (x >= S[n - 1]) return V[n - 1];
    for (int i = 0; i + 1 < n; i++)
        if (x >= S[i] && x <= S[i + 1])
            return V[i] + (V[i + 1] - V[i]) * (x - S[i]) / max(S[i + 1] - S[i], 1e-12);
    return V[n - 1];
}

// Vue d'une bordure à l'abscisse u de sa file : vue nominale v0, abaissés [A0[i], A1[i]] de vue AV[i] et rampants
// linéaires AR[i] de part et d'autre (DEF-031, RF-MA-ABA-004) ; même loi que rg_vue_effective (rg_niveau.h).
function float rc_vue(float v0; float A0[]; float A1[]; float AV[]; float AR[]; float u)
{
    float v = v0;
    for (int i = 0; i < len(A0); i++) {
        float va = AV[i];
        float r = max(AR[i], 1e-6);
        float w;
        if (u >= A0[i] && u <= A1[i]) w = va;
        else if (u < A0[i]) w = (u <= A0[i] - r) ? v0 : va + (v0 - va) * (A0[i] - u) / r;
        else w = (u >= A1[i] + r) ? v0 : va + (v0 - va) * (u - A1[i]) / r;
        v = min(v, w);
    }
    return v;
}

// Indices des limites de bord de chaussée d'un profil (point pp de la géométrie des profils) : première et dernière
// bande de référence « chaussee » (voies, bandes cyclables, bandes dérasées, zones neutralisées…) ; iL = limite gauche
// de la première, iR = limite droite de la dernière. Les bandes au-delà (trottoir, berme, accotement) forment l'extérieur.
function void rc_bords(int gp; int pp; export int iL; export int iR)
{
    string ref[] = point(gp, "niv_reference", pp);
    int nb = len(ref);
    iL = -1;
    iR = -1;
    for (int b = 0; b < nb; b++) if (ref[b] == "chaussee") { iL = b; break; }
    for (int b = nb - 1; b >= 0; b--) if (ref[b] == "chaussee") { iR = b + 1; break; }
}

// Repère d'une branche à l'abscisse s (route pr de la géométrie geo, géométrie régulière) : point de la référence P,
// direction d (sens de la route, vers le centre) et normale gauche n.
function void rc_repere(int geo; int pr; float s; export vector2 P; export vector2 d; export vector2 n)
{
    float x, y, th, k;
    rg_reference(geo, pr, s, x, y, th, k);
    P = set(x, y);
    d = set(cos(th), sin(th));
    n = set(-sin(th), cos(th));
}

// Z bas (chaussée) d'une coupe résolue (rg_coupe) en t : plan de la bande basse qui contient t, sinon de la bande
// basse la plus proche, prolongé (chaussée prolongée sous une bordure, comme rg::sol).
function float rc_z_bas(float T[]; float A[]; float G[]; int CLS[]; float dz; float t)
{
    int nb = len(T) - 1;
    float best = 1e18;
    float z = 0.0;
    for (int b = 0; b < nb; b++) {
        if (CLS[b] != 0) continue;
        float lo = T[b + 1], hi = T[b];
        float e = (t < lo) ? lo - t : ((t > hi) ? t - hi : 0.0);
        if (e < best - 1e-12) { best = e; z = rg_z_bande(A, G, CLS, dz, b, t); }
    }
    return z;
}

// Z haut d'une coupe en t : bande haute qui contient t (sinon la plus proche), prolongée en plan.
function float rc_z_haut(float T[]; float A[]; float G[]; int CLS[]; float dz; float t)
{
    int nb = len(T) - 1;
    float best = 1e18;
    float z = 0.0;
    for (int b = 0; b < nb; b++) {
        if (CLS[b] == 0) continue;
        float lo = T[b + 1], hi = T[b];
        float e = (t < lo) ? lo - t : ((t > hi) ? t - hi : 0.0);
        if (e < best - 1e-12) { best = e; z = rg_z_bande(A, G, CLS, dz, b, t); }
    }
    return z;
}


// Point du bord de chaussée (gauche = 1 : limite iL ; 0 : limite iR) de la route pr (géométrie geo : primitive avec
// sec_s0, sec_profil et la géométrie régulière) à l'abscisse s, profil de la section qui porte s (profils : gp) : suit
// les lois de largeur (ouvertures, élargissements près du carrefour).
function vector2 rc_bord(int geo; int pr; int gp; float s; int gauche)
{
    float S0[] = prim(geo, "sec_s0", pr);
    string SP[] = prim(geo, "sec_profil", pr);
    int k = rg_indice_section(S0, s);
    int pp = rg_point_profil(gp, SP[k]);
    float T[] = rg_t_limites(gp, pp, s);
    int iL, iR;
    rc_bords(gp, pp, iL, iR);
    vector2 P, d, n;
    rc_repere(geo, pr, s, P, d, n);
    return P + (gauche ? T[iL] : T[iR]) * n;
}

// Direction du bord de chaussée en s (sens de la route), différence centrée sur ± h.
function vector2 rc_bord_dir(int geo; int pr; int gp; float s; int gauche; float h)
{
    vector2 a = rc_bord(geo, pr, gp, s - h, gauche), b = rc_bord(geo, pr, gp, s + h, gauche);
    return normalize(b - a);
}

// Abscisses d'échantillonnage du bord entre s0 et s1 (s0 < s1) : pas ≤ pas, bornes des sections comprises.
function float[] rc_abscisses_bord(int geo; int pr; float s0; float s1; float pas)
{
    float S0[] = prim(geo, "sec_s0", pr);
    float out[];
    int n = max(1, int(ceil((s1 - s0) / pas - 1e-9)));
    for (int i = 0; i <= n; i++) push(out, s0 + (s1 - s0) * i / n);
    foreach (float x; S0) if (x > s0 + 1e-6 && x < s1 - 1e-6) push(out, x);
    out = sort(out);
    float r[];
    foreach (float x; out) if (len(r) == 0 || x - r[-1] > 1e-6) push(r, x);
    return r;
}


// Polyligne densifiée (segments ≤ pas).
function vector2[] rc_densifier(vector2 Q[]; float pas)
{
    vector2 out[];
    for (int i = 0; i + 1 < len(Q); i++) {
        int n = max(1, int(ceil(length(Q[i + 1] - Q[i]) / pas - 1e-9)));
        for (int j = 0; j < n; j++) push(out, Q[i] + (Q[i + 1] - Q[i]) * float(j) / n);
    }
    if (len(Q)) push(out, Q[-1]);
    return out;
}

#endif
