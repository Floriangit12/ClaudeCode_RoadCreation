// rg_niveau.h : modèle de nivellement analytique du générateur (lot L2), recopié en tête des wrangles après
// rg_geometrie.h (#include "opdef:" impossible, README_HDA § 1). Pas de struct ; VEX 64 bits.
//
// Un seul modèle de Z (TQ-SOL-013), évalué en (s, t) le long de la ligne de référence d'une route :
//   (1) chaussée (bandes de référence « chaussee ») : chaque groupe de bandes continues est ancré à Z = 0 en t = 0 (ou
//       à sa limite la plus proche de la ligne de référence), puis dévers de chaque bande (+ = descend vers la droite,
//       schéma 0.1) ; + dz(s) des ralentisseurs (plateau, dos-d'âne : d'un trottoir à l'autre, rg_dz_chaussee) ;
//   (2) caniveau : arête côté chaussée au Z de la chaussée, fil d'eau = arête − Δh du profil (CS2 : 0,025 m) ;
//   (3) pied de face d'une bordure = fil d'eau (sinon chaussée au droit de la face), hors ralentisseur (le
//       ralentisseur relève la chaussée contre la face, la bordure ne bouge pas) ;
//   (4) tête = pied + vue (vue courante ; abaissés avec rampants, sauf abaissé réalisé par un ralentisseur) ;
//   (5) trottoir, quai, séparateur, piste au niveau du trottoir : tête − 4 mm à l'arrière de la bordure, puis dévers
//       (TQ-SOL-013 (6)) ; terre-plein ou bande plantée isolés entre bordures : tête − 4 cm (TQ-SOL-013 (7)) ;
//   (6) bande haute sans dévers dit : plan tendu entre ses deux appuis (bordure, bande voisine), sinon horizontale.
// Les bandes « hautes » (référence trottoir ou propre) sont séparées des bandes basses par une bordure réelle, ou par
// une bordure « virtuelle » : même limite (mêmes bandes de part et d'autre) bordée dans une autre section de la route
// (avancées de trottoir : le trottoir garde son niveau d'une section à l'autre).
//
// Données précalculées par rg::nivellement (géométrie « sections », un point par section de route) :
//   b_cls[] (0 basse, 1 haute), b_has_g[], b_g[] (dZ/dt = dévers/100), b_retrait[], b_type[], b_mat[] ;
//   l_bord[] (0 aucune, 1 réelle, 2 virtuelle), l_h[] (+1 : côté haut à gauche), l_base[], l_H[], l_vue[],
//   l_prof[], l_wc[] (largeur du caniveau, 0 : aucun), l_dhc[] (Δh arête − fil d'eau), l_cprof[] ;
//   a_lim[], a_s0[], a_s1[], a_vue[], a_r[], a_couvert[] (abaissés) ; r_s0[], r_s1[] (ralentisseurs de la route).
#ifndef RG_NIVEAU_H
#define RG_NIVEAU_H

#define RG_RETRAIT_TROTTOIR 0.004
#define RG_RETRAIT_PLANTE 0.04
#define RG_EXT_BAS 0.03
#define RG_RECOUV_HAUT 0.012
#define RG_PROF_EMPRISE 0.20

// Point de la géométrie « sections » (entrée gs) pour la section k de la route rid ; −1 sinon.
function int rg_point_section(int gs; string rid; int k)
{
    int pts[] = findattribval(gs, "point", "route", rid);
    foreach (int p; pts)
        if (point(gs, "section", p) == k) return p;
    return -1;
}

// Vue effective d'une limite l en s : vue courante, abaissée (abaissés non couverts par un ralentisseur, rampants
// linéaires de part et d'autre de [s0, s1], ARR2007 / DEF-031).
function float rg_vue_effective(int gs; int sp; int l; float s)
{
    float vn[] = point(gs, "l_vue", sp);
    float v = vn[l];
    int al[] = point(gs, "a_lim", sp);
    float a0[] = point(gs, "a_s0", sp);
    float a1[] = point(gs, "a_s1", sp);
    float av[] = point(gs, "a_vue", sp);
    float ar[] = point(gs, "a_r", sp);
    int ac[] = point(gs, "a_couvert", sp);
    for (int i = 0; i < len(al); i++) {
        if (al[i] != l || ac[i]) continue;
        float va = av[i];
        float r = max(ar[i], 1e-6);
        float w;
        if (s >= a0[i] && s <= a1[i]) w = va;
        else if (s < a0[i]) w = (s <= a0[i] - r) ? v : va + (v - va) * (a0[i] - s) / r;
        else w = (s >= a1[i] + r) ? v : va + (v - va) * (s - a1[i]) / r;
        v = min(v, w);
    }
    return v;
}

// Caniveau de la limite l présent en s (déclaré, et hors ralentisseur : relevé d'un trottoir à l'autre).
function int rg_caniveau_present(int gs; int sp; int l; float s)
{
    float wc[] = point(gs, "l_wc", sp);
    if (wc[l] <= 0.0) return 0;
    float r0[] = point(gs, "r_s0", sp);
    float r1[] = point(gs, "r_s1", sp);
    for (int i = 0; i < len(r0); i++)
        if (s > r0[i] && s < r1[i]) return 0;
    return 1;
}

// Caniveau déclaré de la limite l relevé en s par un ralentisseur (plateau, dos-d'âne) : le fil d'eau y est continué
// par un caniveau à grille dans l'emprise du caniveau (décret 94-447, annexe art. 4 : « ne doit pas nuire à
// l'écoulement des eaux », source de RF-MA-RAL-001 ; moyen constructif [G], règle demandée au propriétaire de la base).
function int rg_caniveau_releve(int gs; int sp; int l; float s)
{
    float wc[] = point(gs, "l_wc", sp);
    if (wc[l] <= 0.0) return 0;
    return !rg_caniveau_present(gs, sp, l, s);
}

// Résolution de la coupe en travers de la section (point de profil pp, point de section sp) à l'abscisse s.
// Sorties : T[] (n + 1 limites), A[], G[] (Z nominal d'une bande = A + G·t, sans dz), CLS[] (0 basse, 1 haute),
// PIED[], TETE[], VUE[] (bordures réelles ou virtuelles ; −1e9 sinon), dz (ralentisseurs, à ajouter aux basses).
// Renvoie 1 si toutes les bandes sont résolues, 0 sinon (erreur décrite dans msg).
function int rg_coupe(int gp; int pp; int gs; int sp; int gpon; string rid; float s; float rampe;
                      export float T[]; export float A[]; export float G[]; export int CLS[];
                      export float PIED[]; export float TETE[]; export float VUE[]; export float dz; export string msg)
{
    msg = "";
    T = rg_t_limites(gp, pp, s);
    int nb = len(T) - 1;
    float d2;
    dz = rg_dz_chaussee(gpon, rid, s, rampe, d2);
    int cls[] = point(gs, "b_cls", sp);
    int hasg[] = point(gs, "b_has_g", sp);
    float gg[] = point(gs, "b_g", sp);
    float ret[] = point(gs, "b_retrait", sp);
    int lb[] = point(gs, "l_bord", sp);
    int lh[] = point(gs, "l_h", sp);
    float lbase[] = point(gs, "l_base", sp);
    float lwc[] = point(gs, "l_wc", sp);
    float ldhc[] = point(gs, "l_dhc", sp);
    CLS = cls;
    resize(A, nb);
    resize(G, nb);
    int det[];
    resize(det, nb);
    resize(PIED, nb + 1);
    resize(TETE, nb + 1);
    resize(VUE, nb + 1);
    for (int l = 0; l <= nb; l++) { PIED[l] = -1e9; TETE[l] = -1e9; VUE[l] = -1e9; }

    // ---- (1) groupes bas : bandes basses consécutives non séparées par une bordure réelle
    int b = 0;
    while (b < nb) {
        if (cls[b] != 0) { b++; continue; }
        int b0 = b;
        int b1 = b;
        while (b1 + 1 < nb && cls[b1 + 1] == 0 && lb[b1 + 1] != 1) b1++;
        // ancrage : t = 0 dans le groupe, sinon la limite du groupe la plus proche de la ligne de référence
        int ba = -1;
        float ta = 0.0;
        if (T[b1 + 1] <= 1e-9 && T[b0] >= -1e-9) {
            for (int c = b0; c <= b1; c++) if (T[c + 1] <= 1e-9 && T[c] >= -1e-9) { ba = c; break; }
            ta = 0.0;
        } else {
            float best = 1e18;
            for (int l = b0; l <= b1 + 1; l++) {
                if (abs(T[l]) < best) { best = abs(T[l]); ba = (l <= b1) ? l : b1; ta = T[l]; }
            }
        }
        G[ba] = hasg[ba] ? gg[ba] : 0.0;
        A[ba] = -G[ba] * ta;
        det[ba] = 1;
        for (int c = ba + 1; c <= b1; c++) {
            float zl = A[c - 1] + G[c - 1] * T[c];
            G[c] = hasg[c] ? gg[c] : 0.0;
            A[c] = zl - G[c] * T[c];
            det[c] = 1;
        }
        for (int c = ba - 1; c >= b0; c--) {
            float zl = A[c + 1] + G[c + 1] * T[c + 1];
            G[c] = hasg[c] ? gg[c] : 0.0;
            A[c] = zl - G[c] * T[c + 1];
            det[c] = 1;
        }
        b = b1 + 1;
    }

    // ---- (2) bordures (réelles et virtuelles) : pied, tête
    float at_t[], at_z[];
    int at_b[];
    for (int l = 1; l < nb; l++) {
        if (lb[l] == 0) continue;
        int h = lh[l];
        int hb = (h > 0) ? l - 1 : l;                     // bande haute
        // bande basse la plus proche côté bas (prolongée jusqu'à la face)
        int bb = -1;
        if (h > 0) { for (int c = l; c < nb; c++) if (cls[c] == 0 && det[c]) { bb = c; break; } }
        else { for (int c = l - 1; c >= 0; c--) if (cls[c] == 0 && det[c]) { bb = c; break; } }
        if (bb < 0 || cls[hb] != 1) {
            if (lb[l] == 1) { msg = sprintf("route %s s=%g : bordure de la limite %d sans bande basse ou haute", rid, s, l); return 0; }
            continue;
        }
        float pied;
        if (lwc[l] > 0.0) {
            float tc = T[l] - h * lwc[l];
            pied = A[bb] + G[bb] * tc - ldhc[l];
        } else {
            pied = A[bb] + G[bb] * T[l];
        }
        float vue = rg_vue_effective(gs, sp, l, s);
        PIED[l] = pied;
        VUE[l] = vue;
        TETE[l] = pied + vue;
        push(at_t, T[l] + h * lbase[l]);
        push(at_z, pied + vue - ret[hb]);
        push(at_b, hb);
    }

    // ---- (3) bandes hautes : appuis aux bordures, continuité aux limites sans bordure réelle
    for (int passe = 0; passe < 2 * nb + 2; passe++) {
        int change = 0;
        for (int fallback = 0; fallback < 2; fallback++) {
            for (int c = 0; c < nb; c++) {
                if (det[c] || cls[c] != 1) continue;
                float ct[], cz[];
                for (int i = 0; i < len(at_b); i++) if (at_b[i] == c) { push(ct, at_t[i]); push(cz, at_z[i]); }
                if (c > 0 && det[c - 1] && lb[c] != 1 && cls[c - 1] == 1) {
                    push(ct, T[c]);
                    push(cz, A[c - 1] + G[c - 1] * T[c]);
                }
                if (c + 1 < nb && det[c + 1] && lb[c + 1] != 1 && cls[c + 1] == 1) {
                    push(ct, T[c + 1]);
                    push(cz, A[c + 1] + G[c + 1] * T[c + 1]);
                }
                if (len(ct) == 0) continue;
                if (hasg[c]) {
                    G[c] = gg[c];
                    A[c] = cz[0] - G[c] * ct[0];
                    det[c] = 1;
                } else if (len(ct) >= 2) {
                    int i0 = 0, i1 = 1;
                    float dmax = -1.0;
                    for (int i = 0; i < len(ct); i++)
                        for (int j = i + 1; j < len(ct); j++)
                            if (abs(ct[i] - ct[j]) > dmax) { dmax = abs(ct[i] - ct[j]); i0 = i; i1 = j; }
                    if (dmax < 1e-6) { G[c] = 0.0; A[c] = cz[i0]; }
                    else { G[c] = (cz[i1] - cz[i0]) / (ct[i1] - ct[i0]); A[c] = cz[i0] - G[c] * ct[i0]; }
                    det[c] = 1;
                } else if (fallback) {
                    G[c] = 0.0;
                    A[c] = cz[0];
                    det[c] = 1;
                } else continue;
                change = 1;
            }
            if (change) break;
        }
        if (!change) break;
    }
    for (int c = 0; c < nb; c++) {
        if (!det[c]) { msg = sprintf("route %s s=%g : bande %d sans niveau (aucun appui)", rid, s, c); return 0; }
    }
    return 1;
}

// Z d'une bande (avec dz des ralentisseurs pour les bandes basses) en t.
function float rg_z_bande(float A[]; float G[]; int CLS[]; float dz; int b; float t)
{
    return A[b] + G[b] * t + (CLS[b] == 0 ? dz : 0.0);
}

// Z des abords (au-delà des limites extérieures) : horizontaux au niveau du bord de la bande extérieure.
function float rg_z_abord(float T[]; float A[]; float G[]; int CLS[]; float dz; int gauche)
{
    int nb = len(T) - 1;
    if (gauche) return rg_z_bande(A, G, CLS, dz, 0, T[0]);
    return rg_z_bande(A, G, CLS, dz, nb - 1, T[nb]);
}

// Point local (x, y) de la route (entrée geo des références, primitive pr) en (s, t) ; géométrie régulière exacte,
// sinon interpolation des échantillons (P, gauche).
function vector2 rg_local_st(int geo; int pr; float s; float t)
{
    if (prim(geo, "geometrie_reguliere", pr)) {
        float x, y, th, k;
        rg_reference(geo, pr, s, x, y, th, k);
        return set(x - t * sin(th), y + t * cos(th));
    }
    int pts[] = primpoints(geo, pr);
    int n = len(pts);
    int i = 0;
    while (i < n - 2 && point(geo, "s", pts[i + 1]) <= s) i++;
    float sa = point(geo, "s", pts[i]);
    float sb = point(geo, "s", pts[i + 1]);
    float a = (sb > sa) ? clamp((s - sa) / (sb - sa), 0.0, 1.0) : 0.0;
    vector P = lerp(vector(point(geo, "P", pts[i])), vector(point(geo, "P", pts[i + 1])), a);
    vector gv = lerp(vector(point(geo, "gauche", pts[i])), vector(point(geo, "gauche", pts[i + 1])), a);
    return set(P.x + t * gv.x, -(P.z + t * gv.z));
}

// (s, t) du point local (x, y) pour la route (primitive pr des références) : projection sur la polyligne échantillonnée
// puis Newton sur rg_local_st (géométrie exacte) ; s borné à [0, L]. Renvoie l'écart résiduel (> 0 au-delà des bouts).
function float rg_st_local(int geo; int pr; float x; float y; export float s; export float t)
{
    int ph;
    vector uvw;
    xyzdist(geo, itoa(pr), set(x, 0.0, -y), ph, uvw);
    float L = prim(geo, "longueur_m", pr);
    vector2 X = set(x, y);
    s = clamp(primuv(geo, "s", ph, uvw), 0.0, L);
    vector2 Q = rg_local_st(geo, pr, s, 0.0);
    t = dot(X - Q, normalize(rg_local_st(geo, pr, s, 1.0) - Q));
    float h = 0.01;
    for (int it = 0; it < 5; it++) {
        Q = rg_local_st(geo, pr, s, t);
        vector2 d = X - Q;
        if (length(d) < 1e-8) break;
        float sa = max(s - h, 0.0), sb = min(s + h, L);
        vector2 Qs = (rg_local_st(geo, pr, sb, t) - rg_local_st(geo, pr, sa, t)) / max(sb - sa, 1e-9);
        vector2 Qt = (rg_local_st(geo, pr, s, t + h) - rg_local_st(geo, pr, s, t - h)) / (2.0 * h);
        float det = Qs.x * Qt.y - Qs.y * Qt.x;
        if (abs(det) < 1e-12) break;
        s = clamp(s + (d.x * Qt.y - d.y * Qt.x) / det, 0.0, L);
        t += (Qs.x * d.y - Qs.y * d.x) / det;
    }
    return length(X - rg_local_st(geo, pr, s, t));
}

// ---------------------------------------------------------------- HeightField de nivellement (sortie 2)
// Nappes : surfaces de niveau continu entre deux bordures (réelles, ou virtuelles entre bande haute et bande basse) ;
// frontière au milieu du corps de la bordure (T[l] + h·base/2). Nappe 0 : la plus à gauche. Région du HeightField = 100 × rang de la route +
// nappe (README_HDA § 2 : height, r0, z1, r1, z2, r2).

// Z de la nappe n en t, surface finie (dessus du caniveau compris), prolongée au-delà de ses frontières : sous la
// bordure, fil d'eau (caniveau déclaré) ou chaussée prolongée côté bas, plan de la bande haute côté haut ; abords
// horizontaux au-delà des limites extérieures.
function float rg_hf_z_nappe(float T[]; float A[]; float G[]; int CLS[]; float PIED[]; float dz; int lh[];
                             float lwc[]; float ldhc[]; int FL[]; int n; float t)
{
    int nb = len(T) - 1;
    int nf = len(FL);
    int bL = (n == 0) ? 0 : FL[n - 1];
    int bR = (n == nf) ? nb - 1 : FL[n] - 1;
    if (t >= T[bL]) {
        if (n == 0) return rg_z_bande(A, G, CLS, dz, 0, T[0]);
        int l = FL[n - 1];
        if (lh[l] > 0 && lwc[l] > 0.0) return PIED[l] + dz;
        return rg_z_bande(A, G, CLS, dz, bL, t);
    }
    if (t <= T[bR + 1]) {
        if (n == nf) return rg_z_bande(A, G, CLS, dz, nb - 1, T[nb]);
        int l = FL[n];
        if (lh[l] < 0 && lwc[l] > 0.0) return PIED[l] + dz;
        return rg_z_bande(A, G, CLS, dz, bR, t);
    }
    int b = bL;
    while (b < bR && t < T[b + 1]) b++;
    float z = rg_z_bande(A, G, CLS, dz, b, t);
    // dessus du caniveau : de l'arête côté chaussée (Z de la chaussée) au fil d'eau contre la face
    if (n > 0) {
        int l = FL[n - 1];
        if (lh[l] > 0 && lwc[l] > 0.0 && T[l] - t <= lwc[l]) z = PIED[l] + dz + ldhc[l] * (T[l] - t) / lwc[l];
    }
    if (n < nf) {
        int l = FL[n];
        if (lh[l] < 0 && lwc[l] > 0.0 && t - T[l] <= lwc[l]) z = PIED[l] + dz + ldhc[l] * (t - T[l]) / lwc[l];
    }
    return z;
}

// Nœud du HeightField en (s, t) (section sp de la route rid) : nappe propriétaire n0 et son Z z0 ; prolongements
// (n1, z1), (n2, z2) des nappes voisines dont la frontière est à moins de dmax (−1 sinon). 0 si la coupe échoue.
function int rg_hf_noeud(int gs; int sp; string rid; float s; float t; float rampe; float dmax;
                         export float z0; export int n0; export float z1; export int n1; export float z2;
                         export int n2; export string msg)
{
    float T[], A[], G[], PIED[], TETE[], VUE[], dz;
    int CLS[];
    if (!rg_coupe(gs, sp, gs, sp, gs, rid, s, rampe, T, A, G, CLS, PIED, TETE, VUE, dz, msg)) return 0;
    int nb = len(T) - 1;
    int lb[] = point(gs, "l_bord", sp);
    int lh[] = point(gs, "l_h", sp);
    float lbase[] = point(gs, "l_base", sp);
    float lwc[] = point(gs, "l_wc", sp);
    float ldhc[] = point(gs, "l_dhc", sp);
    int FL[];
    float FT[];
    // frontière : bordure réelle, ou virtuelle entre une bande haute et une bande basse (marche) ; une bordure
    // virtuelle entre deux bandes hautes (avancée prolongeant le trottoir) n'en est pas une
    for (int l = 1; l < nb; l++)
        if (PIED[l] > -1e8 && (lb[l] == 1 || (lb[l] == 2 && CLS[l - 1] != CLS[l])))
            { push(FL, l); push(FT, T[l] + lh[l] * 0.5 * lbase[l]); }
    int n = 0;
    foreach (float ft; FT) if (ft > t) n++;
    n0 = n;
    z0 = rg_hf_z_nappe(T, A, G, CLS, PIED, dz, lh, lwc, ldhc, FL, n, t);
    n1 = -1; n2 = -1; z1 = 0.0; z2 = 0.0;
    float dg = (n > 0) ? FT[n - 1] - t : 1e18;
    float dd = (n < len(FT)) ? t - FT[n] : 1e18;
    int ca = -1, cb = -1;
    if (dg <= dmax && dd <= dmax) { ca = (dg <= dd) ? n - 1 : n + 1; cb = (dg <= dd) ? n + 1 : n - 1; }
    else if (dg <= dmax) ca = n - 1;
    else if (dd <= dmax) ca = n + 1;
    if (ca >= 0) { n1 = ca; z1 = rg_hf_z_nappe(T, A, G, CLS, PIED, dz, lh, lwc, ldhc, FL, ca, t); }
    if (cb >= 0) { n2 = cb; z2 = rg_hf_z_nappe(T, A, G, CLS, PIED, dz, lh, lwc, ldhc, FL, cb, t); }
    return 1;
}

#endif
