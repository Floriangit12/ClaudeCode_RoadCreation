// pj_pose.h : disposition des éléments préfabriqués le long d'une bordure (VEX).
// Portage de recon/pcg/houdini/pj_bordure_pose.py (référence numpy) sur les courbes régularisées (pj_courbe.h) :
//   - points durs : abaissé > angle vif > changement de profil > extrémité > coupe de zone
//     (assets/specs/bordures_elements.json, pose.points_durs) ;
//   - pas selon le rayon (bordures_elements.json regle_pas_rayon, TQ-BOR-002) : le plus long de 1,00 / 0,50 dont la
//     flèche de corde reste <= fleche_max (10,5 mm), le coin de joint (base x déviation) <= coin_max (6 mm) et le coin
//     vertical (H x changement de pente du fil d'eau) <= coin_v_max (4 mm) ; sinon pièce courbe sur mesure (arc <= 1 m,
//     <= quart de cercle) ; bateaux : 1,00 / 0,50 / 0,33 / 0,25 droits ; hystérésis 60 % ;
//   - file partant du point dur prioritaire en éléments entiers, finie par une coupe >= 0,20 m (sinon deux coupes
//     égales) ; file multiple du pas à ±1 % : éléments égaux sans coupe (tolérance NF EN 1340) ;
//   - chartière : un élément de raccord par intervalle « chartiere » (GA-CHR-002, GA-ABA-004), sur mesure en courbe.
// Recopié en tête des wrangles avec pj_courbe.h et pj_niveau.h.
#ifndef PJ_POSE_H
#define PJ_POSE_H

#define PJ_COUPE_MIN 0.20

function int pj_prio(string t)
{
    if (t == "abaisse") return 3;
    if (t == "angle") return 2;
    if (t == "profil") return 1;
    if (t == "extremite") return 0;
    return -1;                                  // coupe_zone
}

// Point dur : abscisse arrondie à 0,1 mm ; garde le type le plus prioritaire.
function void pj_dur_ajouter(float hs[]; string ht[]; float s; string t)
{
    float r = rint(s * 10000.0) / 10000.0;
    for (int i = 0; i < len(hs); i++) {
        if (abs(hs[i] - r) < 1e-7) {
            if (pj_prio(t) > pj_prio(ht[i])) ht[i] = t;
            return;
        }
    }
    append(hs, r);
    append(ht, t);
}

// Intervalle de la description qui contient s (même règle que le lecteur : premier s1 >= s, sinon le dernier).
function int pj_iv_index(dict ivs[]; float s)
{
    int n = len(ivs);
    for (int k = 0; k < n; k++) {
        float s1 = ivs[k]["s1"];
        if (s <= s1 + 1e-6) return k;
    }
    return max(0, n - 1);
}

// Fil d'eau (pied) en s : profil en long du modèle unique (niv_s, niv_z_pied).
function float pj_zfe(float s; float S[]; float Z[])
{
    if (len(S) == 0) return 0;
    return pj_interp(s, S, Z);
}

function int pj_pente_ok(dict cb[]; float a; float b; float H; float S[]; float Z[]; float coin_v_max)
{
    float L = pj_cb_longueur(cb);
    float lo = max(min(a, b), 0.0), hi = min(max(a, b), L);
    if (hi - lo < 0.05 || len(S) == 0) return 1;
    float m = 0.5 * (lo + hi);
    float z0 = pj_zfe(lo, S, Z), zm = pj_zfe(m, S, Z), z1 = pj_zfe(hi, S, Z);
    return H * abs((z1 - zm) - (zm - z0)) / (0.5 * (hi - lo)) <= coin_v_max;
}

// Élément droit admis sur [a, b] (k < 1 : seuils réduits, hystérésis).
function int pj_droit_ok(dict cb[]; float a; float b; float base; float k; float H; float S[]; float Z[];
                         float fleche_max; float coin_max; float coin_v_max)
{
    float L = pj_cb_longueur(cb);
    float lo = max(min(a, b), 0.0), hi = min(max(a, b), L);
    if (hi - lo < 1e-6) return 1;
    if (pj_cb_fleche(cb, lo, hi) > k * fleche_max) return 0;
    if (base * pj_cb_deviation(cb, lo, hi) > k * coin_max) return 0;
    if (H > 0 && !pj_pente_ok(cb, lo, hi, H, S, Z, coin_v_max)) return 0;
    return 1;
}

// Pas de l'élément qui commence à t (depuis s_dep, sens ±1) : renvoie le pas, genre = "droit" | "courbe".
function float pj_classe_pas(dict cb[]; float s_dep; float sens; float t; int droit_seul; float prec; float base;
                             float H; float S[]; float Z[]; float fleche_max; float coin_max; float coin_v_max;
                             string genre)
{
    float pas[] = droit_seul ? array(1.0, 0.5, 0.33, 0.25) : array(1.0, 0.5);
    for (int i = 0; i < len(pas); i++) {
        float p = pas[i];
        float a = s_dep + sens * t, b = s_dep + sens * (t + p);
        if (p == 1.0 && prec > 0 && prec < 1.0) {
            float c = s_dep + sens * (t + p), d = s_dep + sens * (t + 2 * p);
            if (pj_droit_ok(cb, a, b, base, 0.6, H, S, Z, fleche_max, coin_max, coin_v_max) &&
                pj_droit_ok(cb, c, d, base, 0.6, H, S, Z, fleche_max, coin_max, coin_v_max)) {
                genre = "droit";
                return p;
            }
            continue;
        }
        if (pj_droit_ok(cb, a, b, base, 1.0, H, S, Z, fleche_max, coin_max, coin_v_max) ||
            (droit_seul && i == len(pas) - 1)) {
            genre = "droit";
            return p;
        }
    }
    // pièce courbe : arc d'au plus 1 m et d'au plus un quart de cercle
    float p = 1.0;
    float a = s_dep + sens * t;
    while (p > 0.3 && (pj_cb_deviation(cb, a, s_dep + sens * (t + p)) > 0.5 * PI ||
                       !pj_pente_ok(cb, a, s_dep + sens * (t + p), H, S, Z, coin_v_max)))
        p *= 0.85;
    genre = "courbe";
    return max(0.3, p);
}

// Découpe d'une file de longueur D depuis s_dep (sens ±1) : t0[], longueur réelle[], genre[], coupe[].
function void pj_remplir(dict cb[]; float s_dep; float sens; float D; float joint; int droit_seul; float base;
                         float H; float S[]; float Z[]; float fleche_max; float coin_max; float coin_v_max;
                         float o_t0[]; float o_l[]; string o_g[]; int o_c[])
{
    resize(o_t0, 0); resize(o_l, 0); resize(o_g, 0); resize(o_c, 0);
    string g0, gk;
    float p0 = pj_classe_pas(cb, s_dep, sens, 0.0, droit_seul, -1, base, H, S, Z, fleche_max, coin_max, coin_v_max, g0);
    int n = int(rint(D / p0));
    if (n >= 1 && abs(D - n * p0) <= 0.01 * n * p0) {          // file multiple du pas : éléments égaux, sans coupe
        int ok = 1;
        for (int k = 1; k < n && ok; k++) {
            float pk = pj_classe_pas(cb, s_dep, sens, k * p0, droit_seul, p0, base, H, S, Z, fleche_max, coin_max,
                                     coin_v_max, gk);
            if (pk != p0 || gk != g0) ok = 0;
        }
        if (ok) {
            float Lk = D / n;
            for (int k = 0; k < n; k++) {
                append(o_t0, k * Lk); append(o_l, Lk - joint); append(o_g, g0); append(o_c, 0);
            }
            return;
        }
    }
    float t = 0, prec = -1;
    int garde = 0;
    while (D - t > 1e-6 && garde < 100000) {
        garde++;
        float reste = D - t;
        string g;
        float p = pj_classe_pas(cb, s_dep, sens, t, droit_seul, prec, base, H, S, Z, fleche_max, coin_max,
                                coin_v_max, g);
        prec = p;
        if (reste >= p + PJ_COUPE_MIN + joint) {
            append(o_t0, t); append(o_l, p - joint); append(o_g, g); append(o_c, 0);
            t += p;
        } else if (reste > p + 0.003) {                         // deux coupes égales
            float h = reste / 2;
            append(o_t0, t); append(o_l, h - joint); append(o_g, g); append(o_c, 1);
            append(o_t0, t + h); append(o_l, h - joint); append(o_g, g); append(o_c, 1);
            t = D;
        } else if (reste >= p - 0.01) {                         // élément entier (à 1 cm près)
            append(o_t0, t); append(o_l, reste - joint); append(o_g, g); append(o_c, 0);
            t = D;
        } else if (reste - joint >= PJ_COUPE_MIN || len(o_t0) == 0) {
            if (reste - joint >= 0.05) {                        // coupe finale (ou file plus courte qu'une coupe)
                append(o_t0, t); append(o_l, reste - joint); append(o_g, g); append(o_c, 1);
            }
            t = D;
        } else {                                                // coupe trop courte : deux coupes égales
            int last = len(o_t0) - 1;
            float t0 = o_t0[last], l0 = o_l[last];
            string gl = o_g[last];
            removeindex(o_t0, last); removeindex(o_l, last); removeindex(o_g, last); removeindex(o_c, last);
            float h = (l0 + joint + reste) / 2;
            append(o_t0, t0); append(o_l, h - joint); append(o_g, gl); append(o_c, 1);
            append(o_t0, t0 + h); append(o_l, h - joint); append(o_g, gl); append(o_c, 1);
            t = D;
        }
    }
}

// Dimensions (base, H) d'un profil dans la table des profils (sortie de lire_profils) ; repli T2.
function int pj_profil_index(string noms[]; string p)
{
    int i = find(noms, p);
    if (i < 0) i = find(noms, "T2");
    return i;
}

// Disposition complète d'une bordure. Sorties parallèles (une entrée par élément, triées par s0) :
//   e_s0, e_s1, e_type (droit | courbe | bateau | chartiere | muret), e_coupe, e_iv (intervalle), e_angle_debut,
//   e_angle_fin, e_sur (pièce sur mesure : courbe, chartière en courbe, muret).
function void pj_disposer(dict cb[]; dict ivs[]; float S[]; float Z[]; string noms[]; float bases[]; float Hs[];
                          float joint; int cz_debut; int cz_fin; float fleche_max; float coin_max; float coin_v_max;
                          float pas_muret;
                          float e_s0[]; float e_s1[]; string e_type[]; int e_coupe[]; int e_iv[];
                          int e_ad[]; int e_af[]; int e_sur[])
{
    resize(e_s0, 0); resize(e_s1, 0); resize(e_type, 0); resize(e_coupe, 0); resize(e_iv, 0);
    resize(e_ad, 0); resize(e_af, 0); resize(e_sur, 0);
    float L = pj_cb_longueur(cb);
    if (L < 0.05 || len(ivs) == 0) return;
    float hs[];
    string ht[];
    pj_dur_ajouter(hs, ht, 0.0, cz_debut ? "coupe_zone" : "extremite");
    pj_dur_ajouter(hs, ht, L, cz_fin ? "coupe_zone" : "extremite");
    for (int k = 1; k < len(ivs); k++) {
        string r0 = ivs[k - 1]["role"], r1 = ivs[k]["role"];
        float s0 = ivs[k]["s0"];
        if (s0 <= 1e-4 || s0 >= L - 1e-4) continue;
        pj_dur_ajouter(hs, ht, s0, (r0 != "courant" || r1 != "courant") ? "abaisse" : "profil");
    }
    float coins[] = pj_cb_coins(cb);
    foreach (float sc; coins) {
        if (sc < 0.3 || sc > L - 0.3) continue;
        int libre = 1;
        foreach (float x; hs) if (abs(sc - x) < 0.25) libre = 0;    // pas de file minuscule près d'un autre point dur
        if (libre) pj_dur_ajouter(hs, ht, sc, "angle");
    }
    int ordre[] = argsort(hs);
    float hs2[]; string ht2[];
    foreach (int i; ordre) { append(hs2, hs[i]); append(ht2, ht[i]); }
    float h = joint / 2;                                          // demi-joint de part et d'autre de chaque case
    for (int q = 0; q + 1 < len(hs2); q++) {
        float a = hs2[q], b = hs2[q + 1];
        if (b - a < 1e-4) continue;
        string ta = ht2[q], tb = ht2[q + 1];
        int iv = pj_iv_index(ivs, 0.5 * (a + b));
        string role = ivs[iv]["role"];
        string pf = ivs[iv]["profil"];
        int ip = pj_profil_index(noms, pf);
        float base = bases[ip], H = Hs[ip];
        int n0 = len(e_s0);
        if (pf == "MURET_TALUS") {                                // muret : pièces coulées de pas_muret au plus
            int n = max(1, int(ceil((b - a) / pas_muret - 1e-6)));
            for (int k = 0; k < n; k++) {
                append(e_s0, a + (b - a) * k / n + h); append(e_s1, a + (b - a) * (k + 1) / n - h);
                append(e_type, "muret"); append(e_coupe, 0); append(e_iv, iv); append(e_ad, 0); append(e_af, 0);
                append(e_sur, 1);
            }
        } else if (role == "chartiere") {
            // raccord de vue : éléments de 1,00 m au plus (catalogue : chartières de 1,00 m ; descentes de fin de file
            // et raccords de profil plus longs en plusieurs éléments, vue linéaire, GA-CHR-002, GA-BOR-005)
            int nc = max(1, int(ceil((b - a) / 1.0 - 0.02)));
            for (int k = 0; k < nc; k++) {
                float c0 = a + (b - a) * k / nc + h, c1 = a + (b - a) * (k + 1) / nc - h;
                append(e_s0, max(c0, 0.0)); append(e_s1, min(c1, L));
                append(e_type, "chartiere"); append(e_coupe, 0); append(e_iv, iv); append(e_ad, 0); append(e_af, 0);
                append(e_sur, pj_droit_ok(cb, c0, c1, base, 1.0, 0.0, S, Z, fleche_max, coin_max, coin_v_max) ? 0 : 1);
            }
        } else {
            int depart_fin = pj_prio(tb) > pj_prio(ta);
            float sens = depart_fin ? -1.0 : 1.0;
            float s_dep = depart_fin ? b : a;
            int bateau = role == "bateau";
            float t0[], ln[]; string g[]; int c[];
            pj_remplir(cb, s_dep, sens, b - a, joint, bateau, base, H, S, Z, fleche_max, coin_max, coin_v_max,
                       t0, ln, g, c);
            for (int k = 0; k < len(t0); k++) {
                float s0, s1;
                if (depart_fin) { s1 = b - t0[k] - h; s0 = s1 - ln[k]; }
                else { s0 = a + t0[k] + h; s1 = s0 + ln[k]; }
                s0 = max(s0, 0.0); s1 = min(s1, L);
                string ty = bateau ? "bateau" : g[k];
                int sur = g[k] == "courbe";
                if (!sur && !pj_droit_ok(cb, s0, s1, base, 1.0, H, S, Z, fleche_max, coin_max, coin_v_max)) {
                    sur = 1;                                      // coupe tombée dans une courbe serrée
                    if (!bateau) ty = "courbe";
                }
                append(e_s0, s0); append(e_s1, s1); append(e_type, ty); append(e_coupe, c[k]); append(e_iv, iv);
                append(e_ad, 0); append(e_af, 0); append(e_sur, sur);
            }
        }
        // angle vif : about en onglet sur l'élément qui touche l'angle
        if (len(e_s0) > n0) {
            if (ta == "angle") {
                int im = n0; for (int k = n0; k < len(e_s0); k++) if (e_s0[k] < e_s0[im]) im = k;
                e_ad[im] = 1;
            }
            if (tb == "angle") {
                int iM = n0; for (int k = n0; k < len(e_s0); k++) if (e_s1[k] > e_s1[iM]) iM = k;
                e_af[iM] = 1;
            }
        }
    }
    // tri par s0 (stable)
    int o[] = argsort(e_s0);
    float a0[] = e_s0, a1[] = e_s1; string at[] = e_type; int ac[] = e_coupe, ai[] = e_iv, ad[] = e_ad, af[] = e_af;
    int asur[] = e_sur;
    for (int k = 0; k < len(o); k++) {
        e_s0[k] = a0[o[k]]; e_s1[k] = a1[o[k]]; e_type[k] = at[o[k]]; e_coupe[k] = ac[o[k]]; e_iv[k] = ai[o[k]];
        e_ad[k] = ad[o[k]]; e_af[k] = af[o[k]]; e_sur[k] = asur[o[k]];
    }
}

// Vue de l'intervalle en s (linéaire de vue_m à vue_m_fin sur une chartière).
function float pj_vue_iv(dict iv; float s)
{
    float v0 = iv["vue_m"];
    if (!isvalidindex(iv, "vue_m_fin")) return v0;
    float v1 = iv["vue_m_fin"], s0 = iv["s0"], s1 = iv["s1"];
    return lerp(v0, v1, clamp((s - s0) / max(s1 - s0, 1e-9), 0.0, 1.0));
}

// Profil de l'extrémité basse d'une chartière : intervalle voisin du côté bas (sinon le même profil).
function string pj_profil_bas(dict ivs[]; int iv)
{
    float v0 = ivs[iv]["vue_m"];
    float v1 = v0;
    if (isvalidindex(ivs[iv], "vue_m_fin")) { float x = ivs[iv]["vue_m_fin"]; v1 = x; }
    string p = ivs[iv]["profil"];
    int j = (v1 < v0) ? iv + 1 : iv - 1;                         // descendante : bas en fin ; montante : bas au début
    if (j >= 0 && j < len(ivs)) {
        string pj = ivs[j]["profil"];
        if (pj != "MURET_TALUS") p = pj;
    }
    return p;
}

// Directions d'about d'un élément (plan local) : corde (élément droit) ou tangente de la face (pièce sur mesure).
function vector2 dir_debut(dict cb[]; float s0; float s1; int sur)
{
    if (sur) return pj_cb_tangente(cb, s0);
    float c, k;
    return normalize(pj_cb_point(cb, s1, c, k) - pj_cb_point(cb, s0, c, k));
}

function vector2 dir_fin(dict cb[]; float s0; float s1; int sur)
{
    if (sur) return pj_cb_tangente(cb, s1);
    float c, k;
    return normalize(pj_cb_point(cb, s1, c, k) - pj_cb_point(cb, s0, c, k));
}

// Pied (fil d'eau) en s : mode 0 = profil en long du modèle unique (niv_s, niv_z_pied) ; mode 1 = volume de
// nivellement (pj_niv_z à 0,12 m devant la face, côté chaussée à droite, région basse), repli sur le profil.
function float pj_zpied(dict cb[]; float S[]; float ZP[]; float g[]; int mode; int reg; float s)
{
    if (mode == 0 && len(S) > 0) return pj_interp(s, S, ZP);
    float c, k;
    vector2 p = pj_cb_point(cb, s, c, k);
    vector2 q = p + set(sin(c), -cos(c)) * 0.12;
    float z = pj_niv_z(g, q.x, q.y, reg);
    if (z < 0.5 * PJ_NIV_ABSENT) z = len(S) > 0 ? pj_interp(s, S, ZP) : 0.0;
    return z;
}

// Repère de pose (Houdini Y haut) : lignes = images des axes du prototype (X = s, Y = v, Z = −u), c = pj_vers_houdini.
//   ex, ey, ez locaux (Z haut) : ex le long de l'élément (pente comprise), ey vers l'arrière (gauche), ez vers le haut.
function matrix3 pj_repere_houdini(vector ex; vector ey; vector ez)
{
    vector X = set(ex.x, ex.z, -ex.y);
    vector Y = set(ez.x, ez.z, -ez.y);
    vector Zh = set(-ey.x, -ey.z, ey.y);
    return set(X, Y, Zh);
}

// Axes locaux d'un élément : direction plane d (unitaire), pente dz / L, roulis (rad) autour de ex.
function void pj_axes(vector2 d; float pente; float roulis; vector ex; vector ey; vector ez)
{
    ex = normalize(set(d.x, d.y, pente));
    ey = normalize(cross({0, 0, 1}, ex));
    ez = cross(ex, ey);
    if (abs(roulis) > 1e-9) {
        vector4 q = quaternion(roulis, ex);
        ey = qrotate(q, ey);
        ez = qrotate(q, ez);
    }
}

#endif
