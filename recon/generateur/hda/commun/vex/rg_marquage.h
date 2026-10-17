// rg_marquage.h : empreintes des marquages au sol (lot L2b, HDA rg::marquages), recopiée en tête des wrangles après
// rg_geometrie.h et rg_niveau.h (#include "opdef:" impossible, README_HDA § 1). Pas de struct ; VEX 64 bits.
//
// Les empreintes sont construites dans le plan des paramètres (s, t) de la route (s abscisse de la ligne de référence,
// t positif à gauche), puis découpées en CELLULES : intervalles d'abscisses entre deux lignes de rupture du sol
// (bornes de sections, points des lois de largeur, pieds, hauts et sommets des ralentisseurs, abaissés) et bandes du
// profil (limites = lignes de rupture en travers : couronne, changements de dévers). Chaque morceau est ainsi plan sur
// le sol fabriqué (TQ-SOL-003 : lignes de rupture = arêtes du sol ; TQ-MQG-004 : seules les lignes de rupture qui
// traversent une marque y sont ajoutées comme contraintes) : drapée sommet par sommet par pj::marquage_solide, la
// peinture reste à son épaisseur partout, y compris sur la couronne et aux arêtes des rampes. Les corps de bordure et
// les caniveaux sont retirés des cellules (MQ-DET-010, TQ-MQG-014 : jamais de marque sur une bordure ni sur un
// caniveau).
#ifndef RG_MARQUAGE_H
#define RG_MARQUAGE_H

// aire signée d'un polygone (s, t) ou (x, y)
function float rg_m_aire(vector2 P[])
{
    float a = 0.0;
    int n = len(P);
    for (int i = 0; i < n; i++) {
        vector2 p = P[i];
        vector2 q = P[(i + 1) % n];
        a += p.x * q.y - q.x * p.y;
    }
    return 0.5 * a;
}

// demi-plan a·s + b·t + c >= 0 (Sutherland-Hodgman ; un point sur la droite est dedans)
function vector2[] rg_m_demi_plan(vector2 P[]; float a; float b; float c)
{
    vector2 out[];
    int n = len(P);
    float tol = 1e-11;
    for (int i = 0; i < n; i++) {
        vector2 p = P[i];
        vector2 q = P[(i + 1) % n];
        float fp = a * p.x + b * p.y + c;
        float fq = a * q.x + b * q.y + c;
        int ip = fp >= -tol;
        int iq = fq >= -tol;
        if (ip) push(out, p);
        if (ip != iq) {
            float r = fp / (fp - fq);
            push(out, p + r * (q - p));
        }
    }
    return out;
}

// sommets consécutifs confondus (< tol) retirés
function vector2[] rg_m_nettoyer(vector2 P[]; float tol)
{
    vector2 out[];
    foreach (vector2 p; P) {
        if (len(out) > 0 && length(p - out[-1]) < tol) continue;
        push(out, p);
    }
    while (len(out) > 1 && length(out[0] - out[-1]) < tol) pop(out);
    return out;
}

// intervalles [a0, b0, a1, b1...] moins [c0, c1]
function float[] rg_m_soustraire(float iv[]; float c0; float c1)
{
    float out[];
    for (int i = 0; i + 1 < len(iv); i += 2) {
        float a = iv[i];
        float b = iv[i + 1];
        if (b <= c0 + 1e-9 || a >= c1 - 1e-9) { push(out, a); push(out, b); continue; }
        if (c0 - a > 1e-6) { push(out, a); push(out, c0); }
        if (b - c1 > 1e-6) { push(out, c1); push(out, b); }
    }
    return out;
}

// abscisses de rupture du sol d'une route (références gref / primitive pr ; niveaux gniv) : 0, L, bornes de sections,
// points des lois de largeur, bornes des abaissés et de leurs rampants, pieds / hauts / sommets des ralentisseurs
function float[] rg_m_ruptures(int gref; int pr; int gniv; float rampe)
{
    string rid = prim(gref, "id", pr);
    float L = prim(gref, "longueur_m", pr);
    float S0[] = prim(gref, "sec_s0", pr);
    float S1[] = prim(gref, "sec_s1", pr);
    float tous[];
    push(tous, 0.0);
    push(tous, L);
    foreach (float x; S0) push(tous, x);
    foreach (float x; S1) push(tous, x);
    for (int k = 0; k < len(S0); k++) {
        int sp = rg_point_section(gniv, rid, k);
        if (sp < 0) continue;
        float LS[] = point(gniv, "larg_s", sp);
        foreach (float x; LS) push(tous, x);
        float a0[] = point(gniv, "a_s0", sp);
        float a1[] = point(gniv, "a_s1", sp);
        float ar[] = point(gniv, "a_r", sp);
        for (int i = 0; i < len(a0); i++) {
            push(tous, a0[i]); push(tous, a1[i]);
            push(tous, a0[i] - ar[i]); push(tous, a1[i] + ar[i]);
        }
    }
    float bv[] = rg_bornes_verticales(gniv, rid, rampe);
    foreach (float x; bv) push(tous, x);
    tous = sort(tous);
    float out[];
    foreach (float x; tous) {
        if (x < -1e-9 || x > L + 1e-9) continue;
        float y = clamp(x, 0.0, L);
        if (len(out) == 0 || y - out[-1] > 1e-6) push(out, y);
    }
    return out;
}

// zones à échantillonnage fin [a0, b0, ...] : dos-d'âne (sol courbe en long)
function float[] rg_m_zones_fines(int gniv; string rid)
{
    float out[];
    int pts[] = findattribval(gniv, "point", "route", rid);
    foreach (int p; pts) {
        string ty = point(gniv, "type", p);
        if (ty != "dos_d_ane") continue;
        float sc = point(gniv, "s", p);
        float lg = point(gniv, "longueur_m", p);
        push(out, sc - lg / 2.0);
        push(out, sc + lg / 2.0);
    }
    return out;
}

function int rg_m_dans_zones(float Z[]; float a; float b)
{
    for (int i = 0; i + 1 < len(Z); i += 2)
        if (b > Z[i] + 1e-9 && a < Z[i + 1] - 1e-9) return 1;
    return 0;
}

// arêtes d'un polygone (s, t) découpées : |Δs| <= ds (ds_fin dans les zones fines)
function vector2[] rg_m_densifier_st(vector2 P[]; float ds; float ds_fin; float Z[])
{
    vector2 out[];
    int n = len(P);
    for (int i = 0; i < n; i++) {
        vector2 p = P[i];
        vector2 q = P[(i + 1) % n];
        push(out, p);
        float d = rg_m_dans_zones(Z, min(p.x, q.x), max(p.x, q.x)) ? min(ds, ds_fin) : ds;
        int m = int(ceil(abs(q.x - p.x) / max(d, 1e-6) - 1e-9));
        for (int j = 1; j < m; j++) push(out, p + (q - p) * (float(j) / m));
    }
    return out;
}

// arêtes d'un polygone (x, y) découpées : longueur <= dl
function vector2[] rg_m_densifier_xy(vector2 P[]; float dl)
{
    vector2 out[];
    int n = len(P);
    for (int i = 0; i < n; i++) {
        vector2 p = P[i];
        vector2 q = P[(i + 1) % n];
        push(out, p);
        int m = int(ceil(length(q - p) / max(dl, 1e-6) - 1e-9));
        for (int j = 1; j < m; j++) push(out, p + (q - p) * (float(j) / m));
    }
    return out;
}

// indice de la limite de clé « bande gauche|bande droite » dans la section sp (−1 si absente)
function int rg_m_limite_cle(int gniv; int sp; string cle)
{
    string bid[] = point(gniv, "b_id", sp);
    int nb = len(bid);
    for (int l = 0; l <= nb; l++) {
        string c = (l > 0 ? bid[l - 1] : "^") + "|" + (l < nb ? bid[l] : "$");
        if (c == cle) return l;
    }
    return -1;
}

// largeur d'une bande (identifiant) en s, section sp ; −1 si absente
function float rg_m_largeur_bande(int gniv; int sp; string bande; float s)
{
    string bid[] = point(gniv, "b_id", sp);
    int b = find(bid, bande);
    if (b < 0) return -1.0;
    float T[] = rg_t_limites(gniv, sp, s);
    return T[b] - T[b + 1];
}

// Découpe d'un polygone (s, t) en cellules (intervalle de ruptures RUP × bande), corps de bordure et caniveaux retirés
// (bordures réelles : corps côté haut sur la base du profil, caniveau côté bas sur sa largeur, s'il est présent) ;
// morceaux rangés à plat : OUT (sommets), DEB (premier sommet), NB (nombre), BAND (bande du morceau).
function void rg_m_cellules(vector2 P[]; int gniv; string rid; float SEC0[]; float RUP[]; float amin;
                            export vector2 OUT[]; export int DEB[]; export int NB[]; export int BAND[])
{
    float smin = 1e18;
    float smax = -1e18;
    foreach (vector2 p; P) { smin = min(smin, p.x); smax = max(smax, p.x); }
    for (int j = 0; j + 1 < len(RUP); j++) {
        float a = RUP[j];
        float b = RUP[j + 1];
        if (b <= smin + 1e-9 || a >= smax - 1e-9) continue;
        vector2 Q[] = rg_m_demi_plan(P, 1.0, 0.0, -a);
        Q = rg_m_demi_plan(Q, -1.0, 0.0, b);
        if (len(Q) < 3 || abs(rg_m_aire(Q)) < amin) continue;
        float sm = 0.5 * (a + b);
        int k = rg_indice_section(SEC0, sm);
        int sp = rg_point_section(gniv, rid, k);
        if (sp < 0) continue;
        float Ta[] = rg_t_limites(gniv, sp, a);
        float Tb[] = rg_t_limites(gniv, sp, b);
        int lb[] = point(gniv, "l_bord", sp);
        int lh[] = point(gniv, "l_h", sp);
        float lbase[] = point(gniv, "l_base", sp);
        float lwc[] = point(gniv, "l_wc", sp);
        int nb = len(Ta) - 1;
        // zones interdites autour de chaque bordure réelle : vers le bas (t décroissant) et vers le haut
        float DN[], UP[];
        resize(DN, nb + 1);
        resize(UP, nb + 1);
        for (int l = 0; l <= nb; l++) {
            DN[l] = 0.0;
            UP[l] = 0.0;
            if (l >= len(lb) || lb[l] != 1) continue;
            float wc = rg_caniveau_present(gniv, sp, l, sm) ? lwc[l] : 0.0;
            if (lh[l] > 0) { DN[l] = wc; UP[l] = lbase[l]; }     // haut à gauche : caniveau à droite (t < T)
            else { DN[l] = lbase[l]; UP[l] = wc; }
        }
        float ds = b - a;
        for (int c = 0; c < nb; c++) {
            vector2 R[] = Q;
            // t <= T[l] − DN[l] pour toute limite l <= c (dont le bord gauche de la bande, DN = 0 hors bordure)
            for (int l = 0; l <= c && len(R) >= 3; l++) {
                if (l < c && !(lb[l] == 1)) continue;
                float ha = Ta[l] - DN[l];
                float hb = Tb[l] - DN[l];
                float kh = (hb - ha) / ds;
                R = rg_m_demi_plan(R, kh, -1.0, ha - kh * a);
            }
            // t >= T[l] + UP[l] pour toute limite l >= c + 1
            for (int l = c + 1; l <= nb && len(R) >= 3; l++) {
                if (l > c + 1 && !(lb[l] == 1)) continue;
                float la = Ta[l] + UP[l];
                float lbb = Tb[l] + UP[l];
                float kl = (lbb - la) / ds;
                R = rg_m_demi_plan(R, -kl, 1.0, -(la - kl * a));
            }
            R = rg_m_nettoyer(R, 1e-7);
            if (len(R) < 3 || abs(rg_m_aire(R)) < amin) continue;
            push(DEB, len(OUT));
            push(NB, len(R));
            push(BAND, c);
            foreach (vector2 r; R) push(OUT, r);
        }
    }
}

// polygone local (x, y) -> primitive Houdini (x, 0, −y)
function int rg_m_poly(int geo; vector2 Q[])
{
    int pts[];
    foreach (vector2 q; Q) push(pts, addpoint(geo, set(q.x, 0.0, -q.y)));
    return addprim(geo, "poly", pts);
}

// matériau de peinture de la bibliothèque (assets/lib/route_fr/materiaux/peinture_routiere) : couleur et classe
// d'usure IISR 0 à 3 (usure du modèle 0-1 ; classe = ceil(3 × usure) : légère 0,2 -> u1, moyenne 0,4 -> u2)
function string rg_m_materiau(string coul; float us)
{
    int c = clamp(int(ceil(3.0 * us - 1e-9)), 0, 3);
    return sprintf("peinture_%s_u%d", coul == "" ? "blanc" : coul, c);
}

// point de la table des marques (groupe table) ; renvoie son numéro
function int rg_m_table(vector2 xy; string classe; string id; string route)
{
    int p = addpoint(0, set(xy.x, 0.0, -xy.y));
    setpointgroup(0, "table", p, 1);
    setpointattrib(0, "m_classe", p, classe);
    setpointattrib(0, "m_id", p, id);
    setpointattrib(0, "m_route", p, route);
    return p;
}

// attributs d'une primitive d'empreinte (contrat de pj::marquage_solide + traçabilité)
function void rg_m_attributs(int np; string ent; string id; string classe; string type; string gab; string mat;
                             string coul; float us; int partie; int anneau; string route; string cle; string mod;
                             float larg; float s0; float s1; int rang; int bande; int ligne)
{
    setprimattrib(0, "pj_entite", np, ent);
    setprimattrib(0, "id", np, id);
    setprimattrib(0, "classe", np, classe);
    setprimattrib(0, "type", np, type);
    setprimattrib(0, "gabarit", np, gab);
    setprimattrib(0, "materiau_id", np, mat);
    setprimattrib(0, "couleur", np, coul);
    setprimattrib(0, "usure", np, us);
    setprimattrib(0, "graine", np, random_shash(id) & 0x7fffffff);
    setprimattrib(0, "partie", np, partie);
    setprimattrib(0, "anneau", np, anneau);
    setprimattrib(0, "route", np, route);
    setprimattrib(0, "cle", np, cle);
    setprimattrib(0, "modulation", np, mod);
    setprimattrib(0, "largeur_m", np, larg);
    setprimattrib(0, "s0", np, s0);
    setprimattrib(0, "s1", np, s1);
    setprimattrib(0, "rang", np, rang);
    setprimattrib(0, "bande_sol", np, bande);
    setprimattrib(0, "rg_ligne", np, ligne);
}

// valeur interpolée linéairement d'une fonction tabulée (S croissant)
function float rg_m_interp(float S[]; float V[]; float x)
{
    for (int i = 0; i + 1 < len(S); i++)
        if (x >= S[i] - 1e-12 && x <= S[i + 1] + 1e-12)
            return V[i] + (V[i + 1] - V[i]) * (x - S[i]) / max(S[i + 1] - S[i], 1e-12);
    return V[-1];
}

// nombres d'un fragment JSON qui suit « "cle": » (tableaux imbriqués de nombres : [[x, y], ...]) ; vide si absent
function float[] rg_m_nombres_apres(string js; string cle)
{
    float out[];
    int i = find(js, "\"" + cle + "\"");
    if (i < 0) return out;
    int d = find(js, "[", i);
    if (d < 0) return out;
    int prof = 0;
    int f = d;
    for (int j = d; j < len(js); j++) {
        string c = js[j];
        if (c == "[") prof++;
        else if (c == "]") { prof--; if (prof == 0) { f = j; break; } }
    }
    string parts[] = split(js[d:f + 1], "[], \t\n");
    foreach (string p; parts) if (p != "") push(out, atof(p));
    return out;
}

#endif
