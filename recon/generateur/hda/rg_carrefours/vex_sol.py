"""Code VEX de l'HDA rg::carrefours_sol (fabrication de l'intérieur des carrefours plans, lot L3 : étapes 1 à 6).

Importé par construire.py. Entrées des wrangles : 0 SOLVEUR (rg::carrefours, sortie 6) ou la géométrie en cours ;
NIVEAUX (rg::nivellement, sortie 1 : références échantillonnées et sections) ; profils coupés (rg::carrefours, sortie 5).
"""

VEX_DOMAINE = r"""
// domaine (détail ; entrée 0 : SOLVEUR, 1 : NIVEAUX, 2 : profils) : faces de bordure du carrefour (coins, nez des
// îlots du profil, îlots du cœur), abaissés des passages qui les traversent (DEF-031), lignes de contrainte (face,
// arrière de la bordure, bord extérieur du trottoir), régions de classement, segments à Z imposé (embouchures, bords
// de chaussée des branches, coupes des trottoirs), contour fermé du domaine (groupe contour).
float rampe = 7.0;
float rh = chf("../recouvrement_tete");
float va = chf("../abaisse_vue"), ra = chf("../abaisse_rampant"), ramin = chf("../abaisse_rampant_min");
float mpp = chf("../passage_marge");
float base_def = chf("../base_defaut");
addprimattrib(0, "kind", ""); addprimattrib(0, "zone", ""); addprimattrib(0, "ref", ""); addprimattrib(0, "priorite", 0);
addprimattrib(0, "base", 0.0); addprimattrib(0, "pied_a", 0.0); addprimattrib(0, "pied_b", 0.0);
addprimattrib(0, "u_tb", 0.0); addprimattrib(0, "u_ta", 0.0); addprimattrib(0, "gl_a", 0.0); addprimattrib(0, "gl_b", 0.0); addprimattrib(0, "materiau_bordure", "");
addprimattrib(0, "retrait", 0.0); addprimattrib(0, "materiau_top", "");
addprimattrib(0, "s", 0.0); addprimattrib(0, "t", 0.0); addprimattrib(0, "dkind", "");
addprimattrib(0, "vue_nominale", 0.0); addprimattrib(0, "zone_ext", "");
addpointattrib(0, "u", 0.0);

// ---- passages : axe et longueur des bandes (modèle ; passages sans route : repère de la voie la plus proche)
vector2 PA0[], PA1[];
float PW[];
string PID[];
foreach (int p; expandpointgroup(0, "passage")) {
    vector a = point(0, "axe0", p), b = point(0, "axe1", p);
    push(PA0, set(a.x, a.y)); push(PA1, set(b.x, b.y)); push(PW, float(point(0, "largeur", p))); push(PID, string(point(0, "id", p)));
}
int coins[] = expandprimgroup(0, "coin");
foreach (int q; expandprimgroup(0, "passage_libre")) {
    int qp[] = primpoints(0, q);
    vector2 V[];
    vector2 G = {0, 0};
    foreach (int p; qp) { vector2 v = rc_xy(point(0, "P", p)); push(V, v); G += v; }
    G /= len(V);
    // direction de circulation : tangente de la face de bordure de coin la plus proche
    float best = 1e18;
    vector2 r = {1, 0};
    foreach (int c; coins) {
        int cp[] = primpoints(0, c);
        for (int i = 0; i + 1 < len(cp); i++) {
            vector2 A = rc_xy(point(0, "P", cp[i])), B = rc_xy(point(0, "P", cp[i + 1]));
            float u;
            float dd = rc_dist_seg(G, A, B, u);
            if (dd < best && length(B - A) > 1e-6) { best = dd; r = normalize(B - A); }
        }
    }
    vector2 cc = rc_gauche(r);
    float rmin = 1e18, rmax = -1e18, cmin = 1e18, cmax = -1e18;
    foreach (vector2 v; V) {
        rmin = min(rmin, dot(v - G, r)); rmax = max(rmax, dot(v - G, r));
        cmin = min(cmin, dot(v - G, cc)); cmax = max(cmax, dot(v - G, cc));
    }
    vector2 g0 = G + 0.5 * (rmin + rmax) * r;
    push(PA0, g0 + cmin * cc); push(PA1, g0 + cmax * cc); push(PW, rmax - rmin); push(PID, string(prim(0, "id", q)));
}

// ---- base d'une bordure : table des sections de rg::nivellement, sinon paramètre (table de pj::bordure)
string bases_tab[] = split(chs("../table_bases"), ",");

// abaissés d'une file de face Q (abscisses U) : intersections avec les bandes de passage (axe ± largeur / 2,
// étendue de l'axe ± marge), vue DEF-031, rampants réduits aux bouts de la file (≥ rampant minimal sinon signalé)
int nface = 0;
string avert[];
// coins (tableaux aplatis) : face, extérieur, droit, u_ta, u_tb ; nez : t des bouts par route
string CR[]; int CQo[], CQn[], COo[], COn[], CDR[], CAo[], CAn[], CBo[], CBn[]; float CUTA[], CUTB[];
vector CQV[], COV[], CAV[], CBV[];
string NR[]; float NTV[];

// ===================================================================================== faces de bordure
int faces_src[] = expandprimgroup(0, "coin");
foreach (int q; expandprimgroup(0, "nez")) push(faces_src, q);
foreach (int q; expandprimgroup(0, "ilot")) if (prim(0, "porte", q) == 0) push(faces_src, q);
foreach (int q; faces_src) {
    int estcoin = inprimgroup(0, "coin", q), estnez = inprimgroup(0, "nez", q);
    int qp[] = primpoints(0, q);
    vector2 Q[];
    foreach (int p; qp) push(Q, rc_xy(point(0, "P", p)));
    string kind = estcoin ? "coin" : (estnez ? "nez" : "ilot");
    string ref = estcoin || estnez ? string(prim(0, "coin", q)) : string(prim(0, "id", q));
    string bord = "";
    float vue = 0.0;
    if (kind == "ilot") {
        // îlot du cœur : sens trigonométrique (îlot à gauche), boucle ouverte en un sommet aligné
        float aire = 0;
        for (int i = 0; i < len(Q); i++) aire += rc_croix(Q[i], Q[(i + 1) % len(Q)]);
        if (aire < 0) Q = reverse(Q);
        // densifiée (pied et abaissés suivent le sol), ouverte en un sommet aligné hors des bandes de passage
        push(Q, Q[0]);
        Q = rc_densifier(Q, 0.5);
        removeindex(Q, len(Q) - 1);
        int n0 = len(Q), k0 = 0;
        float bestal = -2;
        for (int i = 0; i < n0; i++) {
            vector2 a = Q[(i - 1 + n0) % n0], b = Q[i], c = Q[(i + 1) % n0];
            if (length(b - a) < 1e-6 || length(c - b) < 1e-6) continue;
            int dans_pp = 0;
            for (int k = 0; k < len(PA0); k++) {
                vector2 ax = PA1[k] - PA0[k];
                float la = length(ax);
                if (la < 1e-6) continue;
                vector2 cd = ax / la, rd = rc_gauche(cd);
                float rr = dot(b - PA0[k], rd), cc = dot(b - PA0[k], cd);
                if (abs(rr) <= 0.5 * PW[k] + ra + 0.5 && cc >= -mpp && cc <= la + mpp) dans_pp = 1;
            }
            float al = dot(normalize(b - a), normalize(c - b)) - 2.0 * dans_pp;
            if (al > bestal + 1e-9) { bestal = al; k0 = i; }
        }
        vector2 R[];
        for (int j = 0; j <= n0; j++) push(R, Q[(k0 + j) % n0]);
        Q = R;
        bord = string(prim(0, "ceinture", q));
        if (bord == "") bord = chs("../bordure_ilot_defaut");
        vue = prim(0, "ceinture_vue", q);
        if (vue <= 0) vue = prim(0, "surelevation", q);
    } else {
        bord = string(prim(0, "bordure", q));
        vue = float(prim(0, "vue", q));
    }
    float U[] = rc_cumul(Q);
    float Lt = U[-1];
    float base = 0.0;
    string matb = "";
    if (bord != "") {
        base = base_def;
        foreach (string e; bases_tab) { string kv[] = split(e, ":"); if (len(kv) == 2 && kv[0] == bord) base = atof(kv[1]); }
        foreach (int sp; expandpointgroup(1, "sections")) {
            string lp[] = point(1, "l_prof", sp);
            float lbs[] = point(1, "l_base", sp);
            string lm[] = point(1, "l_mat", sp);
            int i = find(lp, bord);
            if (i >= 0) { base = lbs[i]; matb = lm[i]; break; }
        }
    }
    if (matb == "") matb = chs("../materiau_bordure_defaut");
    // abaissés
    float A0[], A1[], AV[], AR[];
    string AP[];
    if (bord != "") {
        for (int k = 0; k < len(PA0); k++) {
            vector2 ax = PA1[k] - PA0[k];
            float la = length(ax);
            if (la < 1e-6) continue;
            vector2 cdir = ax / la, rdir = rc_gauche(cdir);
            float hw = 0.5 * PW[k];
            // parcours de la file : intervalles où |r| <= hw et la projection sur l'axe est dans [−marge, la + marge]
            float in0 = -1;
            int dedans_prec = 0;
            float x0[], x1[];
            for (int i = 0; i + 1 < len(Q); i++) {
                int nsub = max(1, int(ceil((U[i + 1] - U[i]) / 0.02)));
                for (int j = (i == 0 ? 0 : 1); j <= nsub; j++) {
                    float f = float(j) / nsub;
                    vector2 v = Q[i] + f * (Q[i + 1] - Q[i]);
                    float uu = U[i] + f * (U[i + 1] - U[i]);
                    float rr = dot(v - PA0[k], rdir), cc = dot(v - PA0[k], cdir);
                    int dedans = abs(rr) <= hw + 1e-9 && cc >= -mpp && cc <= la + mpp;
                    if (dedans && !dedans_prec) in0 = uu;
                    if (!dedans && dedans_prec) { push(x0, in0); push(x1, uu); }
                    dedans_prec = dedans;
                }
            }
            if (dedans_prec) { push(x0, in0); push(x1, Lt); }
            for (int j = 0; j < len(x0); j++) {
                if (x1[j] - x0[j] < 0.5) continue;
                float r = ra;
                r = min(r, x0[j]);
                r = min(r, Lt - x1[j]);
                if (r < ramin - 1e-6) push(avert, sprintf("%s : rampant de %.2f m < %.2f m (abaissé %s)", ref, r, ramin, PID[k]));
                push(A0, x0[j]); push(A1, x1[j]); push(AV, va); push(AR, max(r, 0.05)); push(AP, PID[k]);
            }
        }
    }
    // face (nouvelle primitive, groupe face)
    int fq[];
    foreach (int i; vector2 v; Q) { int p = addpoint(0, rc_h(v, 0.0)); setpointattrib(0, "u", p, U[i]); push(fq, p); }
    int pf = addprim(0, "polyline", fq);
    setprimgroup(0, "face", pf, 1);
    setprimattrib(0, "kind", pf, kind);
    setprimattrib(0, "ref", pf, ref);
    setprimattrib(0, "carrefour", pf, string(prim(0, "carrefour", q)));
    setprimattrib(0, "bordure", pf, bord);
    setprimattrib(0, "vue", pf, vue);
    setprimattrib(0, "vue_nominale", pf, vue);
    setprimattrib(0, "base", pf, base);
    setprimattrib(0, "materiau_bordure", pf, matb);
    setprimattrib(0, "ab0", pf, A0); setprimattrib(0, "ab1", pf, A1);
    setprimattrib(0, "abv", pf, AV); setprimattrib(0, "abr", pf, AR); setprimattrib(0, "ab_passage", pf, AP);
    setprimattrib(0, "longueur", pf, Lt);
    nface++;
    // pied : coins = bords de chaussée des branches (Z bas du modèle unique en s_tan), linéaire sur l'arc
    if (kind == "coin") {
        string ras[] = array(string(prim(0, "route_a", q)), string(prim(0, "route_b", q)));
        float pz[];
        foreach (int j; string rid; ras) {
            int pr = rc_prim_route(1, rid);
            int bpt = findattribval(0, "point", "route", rid);
            float s = j == 0 ? point(0, "s_tan_d", bpt) : point(0, "s_tan_g", bpt);
            float se = float(point(0, "s_end", bpt));
            if (s < 0 || s > se) s = se;
            float tt = j == 0 ? float(point(0, "t_d", bpt)) : float(point(0, "t_g", bpt));
            float S0[] = prim(1, "sec_s0", pr);
            string SP[] = prim(1, "sec_profil", pr);
            int k = rg_indice_section(S0, min(s, se - 1e-4));
            int sp = rg_point_section(1, rid, k);
            int pp = rg_point_profil(2, SP[k]);
            float T[], A[], G[], PIE[], TEE[], VU[], dz;
            int CLS[];
            string msg;
            if (!rg_coupe(2, pp, 1, sp, 2, rid, min(s, se - 1e-4), rampe, T, A, G, CLS, PIE, TEE, VU, dz, msg)) error("%s", msg);
            // bord de chaussée pris dans la coupe en s (et non le t du bord en s_end) : sur un bord évasé (loi de
            // largeur), le t de s_end ne correspond à aucune limite en s_tan, la pente gl restait nulle et le dessous
            // de bordure du coin était plat (marche de 1,7 mm de J4 et G3 ; correction connue du lot giratoires,
            // appliquée après le contrôle de l'étape 2)
            int dedans = 0;
            foreach (float tv; T) if (abs(tv - tt) < 1e-5) dedans = 1;
            if (!dedans) {
                // limite la plus proche dont la bande côté chaussée est basse (bord de chaussée en s)
                float tb = tt, eb = 1e9;
                for (int bb = 0; bb < len(CLS); bb++) {
                    if (CLS[bb] != 0) continue;
                    float tc = j == 0 ? T[bb + 1] : T[bb];
                    if (abs(tc - tt) < eb) { eb = abs(tc - tt); tb = tc; }
                }
                tt = tb;
            }
            push(pz, rc_z_bas(T, A, G, CLS, dz, tt));
            // pente de la chaussée prolongée sous la bordure (dZ / distance à la face, vers le trottoir)
            float gl = 0.0;
            for (int bb = 0; bb + 1 < len(T); bb++) {
                if (CLS[bb] != 0) continue;
                if (j == 0 && abs(T[bb + 1] - tt) < 1e-5) gl = -G[bb];
                if (j == 1 && abs(T[bb] - tt) < 1e-5) gl = G[bb];
            }
            push(pz, gl);
        }
        setprimattrib(0, "pied_a", pf, pz[0]);
        setprimattrib(0, "pied_b", pf, pz[2]);
        // pied de chaque sommet : bord réel de la branche sur les amorces (Z bas du modèle unique), linéaire sur l'arc
        int qp_[] = primpoints(0, q);
        int i_tb = -1, i_ta = -1;
        for (int i = 0; i < len(qp_); i++) {
            int pa_ = point(0, "partie", qp_[i]);
            if (pa_ == 1 && i_tb < 0) i_tb = i;
            if (pa_ == 1) i_ta = i;
        }
        int droit_ = prim(0, "droit", q);
        if (droit_) { i_tb = 0; i_ta = len(Q) - 1; }
        float PZv[];
        resize(PZv, len(Q));
        for (int i = 0; i < len(Q); i++) {
            if (i > i_tb && i < i_ta) continue;
            string rid = i <= i_tb ? ras[1] : ras[0];
            int pr = rc_prim_route(1, rid);
            float sv, tv;
            rg_st_local(1, pr, Q[i].x, Q[i].y, sv, tv);
            float Lr = prim(1, "longueur_m", pr);
            sv = clamp(sv, 0.0, Lr - 1e-4);
            float S0[] = prim(1, "sec_s0", pr);
            string SP[] = prim(1, "sec_profil", pr);
            int k = rg_indice_section(S0, sv);
            int sp = rg_point_section(1, rid, k);
            int pp = rg_point_profil(2, SP[k]);
            float T[], A[], G[], PIE[], TEE[], VU[], dz;
            int CLS[];
            string msg;
            if (!rg_coupe(2, pp, 1, sp, 2, rid, sv, rampe, T, A, G, CLS, PIE, TEE, VU, dz, msg)) error("%s", msg);
            PZv[i] = rc_z_bas(T, A, G, CLS, dz, tv);
        }
        for (int i = i_tb + 1; i < i_ta; i++)
            PZv[i] = PZv[i_tb] + (PZv[i_ta] - PZv[i_tb]) * (U[i] - U[i_tb]) / max(U[i_ta] - U[i_tb], 1e-9);
        setprimattrib(0, "pied_z", pf, PZv);
        setprimattrib(0, "gl_a", pf, pz[1]);
        setprimattrib(0, "gl_b", pf, pz[3]);
        int droit = prim(0, "droit", q);
        setprimattrib(0, "u_tb", pf, U[i_tb]);
        setprimattrib(0, "u_ta", pf, U[i_ta]);
        string noms_cs[] = {"route_a", "route_b", "branche_a", "branche_b", "mat_ext", "ref_ext", "type_ext"};
        foreach (string a; noms_cs) {
            string v = prim(0, a, q); setprimattrib(0, a, pf, v);
        }
        string noms_cf[] = {"w_a", "w_b", "g_a", "g_b", "s_cut_a", "s_cut_b", "rayon"};
        foreach (string a; noms_cf) {
            float v = prim(0, a, q); setprimattrib(0, a, pf, v);
        }
        setprimattrib(0, "droit", pf, droit);
        setprimattrib(0, "retrait", pf, RG_RETRAIT_TROTTOIR);
    } else if (kind == "nez") {
        string noms_ns[] = {"route", "branche"};
        foreach (string a; noms_ns) { string v = prim(0, a, q); setprimattrib(0, a, pf, v); }
        string noms_nf[] = {"s_end", "t_g", "t_d", "rayon"};
        foreach (string a; noms_nf) { float v = prim(0, a, q); setprimattrib(0, a, pf, v); }
        setprimattrib(0, "materiau_top", pf, string(prim(0, "materiau", q)));
    } else {
        string mt = string(prim(0, "materiau", q));
        if (mt == "") mt = "beton_balaye";
        setprimattrib(0, "materiau_top", pf, mt);
        // terre-plein isolé entre bordures : tête − 4 cm s'il est planté, − 4 mm sinon (TQ-SOL-013 (5), (7))
        setprimattrib(0, "retrait", pf, (find(mt, "gazon") >= 0 || find(mt, "terre") >= 0) ? RG_RETRAIT_PLANTE : RG_RETRAIT_TROTTOIR);
    }
    // ---- lignes de contrainte et régions
    float Wb[];
    foreach (float u; U) push(Wb, base - rh);
    vector2 Bk[] = rc_decaler(Q, Wb);
    if (kind == "coin") {
        float wa = float(prim(0, "w_a", q)), wb = float(prim(0, "w_b", q));
        float Wo[];
        foreach (float u; U) push(Wo, wb + (wa - wb) * (Lt > 0 ? u / Lt : 0.0));
        vector2 O[] = rc_decaler(Q, Wo);
        vector na3 = prim(0, "n_a", q), nb3 = prim(0, "n_b", q);
        if (!prim(0, "droit", q)) {
            O[0] = Q[0] + wb * set(nb3.x, nb3.y);
            O[-1] = Q[-1] + wa * set(na3.x, na3.y);
        }
        // le bord extérieur est sur le contour ; face et arrière en lignes
        int l1[];
        foreach (vector2 v; Q) push(l1, addpoint(0, rc_h(v, 0.0)));
        int pl1 = addprim(0, "polyline", l1); setprimgroup(0, "lignes", pl1, 1);
        string zext = prim(0, "ref_ext", q) == "trottoir" || bord != "" ? "trottoir" : "accotement";
        setprimattrib(0, "zone_ext", pf, zext);
        if (bord != "") {
            int l2[];
            foreach (vector2 v; Bk) push(l2, addpoint(0, rc_h(v, 0.0)));
            int pl2 = addprim(0, "polyline", l2); setprimgroup(0, "lignes", pl2, 1);
            // région « sous la bordure » (face -> arrière) et « trottoir » (arrière -> extérieur)
            int r1[];
            foreach (vector2 v; Q) push(r1, addpoint(0, rc_h(v, 0.0)));
            for (int i = len(Bk) - 1; i >= 0; i--) push(r1, addpoint(0, rc_h(Bk[i], 0.0)));
            int pr1 = addprim(0, "poly", r1); setprimgroup(0, "regions", pr1, 1);
            setprimattrib(0, "zone", pr1, "sous_bordure"); setprimattrib(0, "ref", pr1, ref); setprimattrib(0, "priorite", pr1, 1);
            int r2[];
            foreach (vector2 v; Bk) push(r2, addpoint(0, rc_h(v, 0.0)));
            for (int i = len(O) - 1; i >= 0; i--) push(r2, addpoint(0, rc_h(O[i], 0.0)));
            int pr2 = addprim(0, "poly", r2); setprimgroup(0, "regions", pr2, 1);
            setprimattrib(0, "zone", pr2, zext); setprimattrib(0, "ref", pr2, ref); setprimattrib(0, "priorite", pr2, 1);
        } else {
            int r2[];
            foreach (vector2 v; Q) push(r2, addpoint(0, rc_h(v, 0.0)));
            for (int i = len(O) - 1; i >= 0; i--) push(r2, addpoint(0, rc_h(O[i], 0.0)));
            int pr2 = addprim(0, "poly", r2); setprimgroup(0, "regions", pr2, 1);
            setprimattrib(0, "zone", pr2, zext); setprimattrib(0, "ref", pr2, ref); setprimattrib(0, "priorite", pr2, 1);
        }
        // bord extérieur rangé sur la face (contour)
        vector Ov[], Qv[];
        foreach (vector2 v; O) push(Ov, set(v.x, v.y, 0));
        foreach (vector2 v; Q) push(Qv, set(v.x, v.y, 0));
        setprimattrib(0, "exterieur", pf, Ov);
        push(CR, ref); push(CQo, len(CQV)); push(CQn, len(Qv)); push(COo, len(COV)); push(COn, len(Ov));
        foreach (vector v; Qv) push(CQV, v);
        foreach (vector v; Ov) push(COV, v);
        push(CDR, int(prim(0, "droit", q)));
        vector ba_[] = prim(0, "bord_a", q), bb_[] = prim(0, "bord_b", q);
        push(CAo, len(CAV)); push(CAn, len(ba_)); foreach (vector v; ba_) push(CAV, v);
        push(CBo, len(CBV)); push(CBn, len(bb_)); foreach (vector v; bb_) push(CBV, v);
        // segments à Z imposé le long des bords réels des branches (embouchure -> point de tangence)
        string ras_[] = array(string(prim(0, "route_a", q)), string(prim(0, "route_b", q)));
        for (int j = 0; j < 2; j++) {
            vector bv[] = j == 0 ? ba_ : bb_;
            for (int i = 0; i + 1 < len(bv); i++) {
                int sq[] = array(addpoint(0, set(bv[i].x, 0, -bv[i].y)), addpoint(0, set(bv[i + 1].x, 0, -bv[i + 1].y)));
                int ps = addprim(0, "polyline", sq); setprimgroup(0, "dseg", ps, 1);
                setprimattrib(0, "dkind", ps, "bord"); setprimattrib(0, "route", ps, ras_[j]);
            }
        }
        {
            int qp2[] = primpoints(0, q);
            int itb = -1, ita = -1;
            for (int i = 0; i < len(qp2); i++) { int pa_ = point(0, "partie", qp2[i]); if (pa_ == 1 && itb < 0) itb = i; if (pa_ == 1) ita = i; }
            push(CUTA, ita >= 0 ? U[ita] : Lt); push(CUTB, itb >= 0 ? U[itb] : 0.0);
        }
        // segments à Z imposé : coupes des trottoirs (amorces) et bords de chaussée des branches
        string ra_ = string(prim(0, "route_a", q)), rb_ = string(prim(0, "route_b", q));
        vector2 segs[] = array(Q[-1], O[-1], Q[0], O[0]);
        string sr[] = array(ra_, rb_);
        float ss[] = array(float(prim(0, "s_cut_a", q)), float(prim(0, "s_cut_b", q)));
        for (int j = 0; j < 2; j++) {
            int sq[] = array(addpoint(0, rc_h(segs[2 * j], 0.0)), addpoint(0, rc_h(segs[2 * j + 1], 0.0)));
            int ps = addprim(0, "polyline", sq); setprimgroup(0, "dseg", ps, 1);
            setprimattrib(0, "dkind", ps, "coupe"); setprimattrib(0, "route", ps, sr[j]); setprimattrib(0, "s", ps, ss[j]);
        }
    } else {
        // nez et îlots : bordure (face -> arrière, priorité 2), dessus (dans l'arrière, priorité 3)
        int r1[];
        foreach (vector2 v; Q) push(r1, addpoint(0, rc_h(v, 0.0)));
        int pr1 = addprim(0, "poly", r1); setprimgroup(0, "regions", pr1, 1);
        setprimattrib(0, "zone", pr1, "sous_bordure_ilot"); setprimattrib(0, "ref", pr1, ref); setprimattrib(0, "priorite", pr1, 2);
        int r2[];
        foreach (vector2 v; Bk) push(r2, addpoint(0, rc_h(v, 0.0)));
        int pr2 = addprim(0, "poly", r2); setprimgroup(0, "regions", pr2, 1);
        setprimattrib(0, "zone", pr2, "ilot"); setprimattrib(0, "ref", pr2, ref); setprimattrib(0, "priorite", pr2, 3);
        int l1[], l2[];
        foreach (vector2 v; Q) push(l1, addpoint(0, rc_h(v, 0.0)));
        foreach (vector2 v; Bk) push(l2, addpoint(0, rc_h(v, 0.0)));
        int pl1 = addprim(0, "polyline", l1); setprimgroup(0, "lignes", pl1, 1);
        int pl2 = addprim(0, "polyline", l2); setprimgroup(0, "lignes", pl2, 1);
        vector Bv[];
        foreach (vector2 v; Bk) push(Bv, set(v.x, v.y, 0));
        setprimattrib(0, "arriere", pf, Bv);
        if (kind == "nez") {
            string rid_ = prim(0, "route", q);
            int bpt = findattribval(0, "point", "route", rid_);
            vector P3 = point(0, "Pe", bpt), n3 = point(0, "nrm", bpt);
            vector2 Pe_ = set(P3.x, P3.y), ne_ = set(n3.x, n3.y);
            float tl[] = array(dot(Q[0] - Pe_, ne_), dot(Q[-1] - Pe_, ne_), dot(Bk[0] - Pe_, ne_), dot(Bk[-1] - Pe_, ne_));
            foreach (float x; tl) { push(NR, rid_); push(NTV, x); }
        }
    }
}

// ===================================================================================== contour du domaine
foreach (int ce; expandprimgroup(0, "frontiere")) {
    string cid = string(prim(0, "carrefour", ce));
    int bp[];
    int rg_[];
    foreach (int p; expandpointgroup(0, "branche")) if (point(0, "carrefour", p) == cid) { push(bp, p); push(rg_, int(point(0, "rang", p))); }
    int ord[] = argsort(rg_);
    int nbk = len(bp);
    vector2 C[];
    for (int kk = 0; kk < nbk; kk++) {
        int p = bp[ord[kk]];
        string rid = string(point(0, "route", p));
        // embouchure : sommets des limites + bouts des nez (face et arrière) triés par t décroissant
        int pe = -1;
        foreach (int q; expandprimgroup(0, "embouchure")) if (prim(0, "route", q) == rid) pe = q;
        vector P3 = point(0, "Pe", p), n3 = point(0, "nrm", p);
        vector2 Pe = set(P3.x, P3.y), ne = set(n3.x, n3.y);
        float ts[];
        foreach (int v; primpoints(0, pe)) push(ts, float(point(0, "t", v)));
        for (int i = 0; i < len(NR); i++) if (NR[i] == rid) push(ts, NTV[i]);
        ts = reverse(sort(ts));
        float tp = 1e18;
        foreach (float t; ts) { if (abs(t - tp) > 1e-6) push(C, Pe + t * ne); tp = t; }
        // coin vers la branche suivante (A = cette branche, côté droit)
        string coin = point(0, "coin_d", p);
        int ic = find(CR, coin);
        if (ic < 0) continue;
        vector2 Q[];
        vector Ov[];
        for (int i = 0; i < CQn[ic]; i++) { vector v = CQV[CQo[ic] + i]; push(Q, set(v.x, v.y)); }
        for (int i = 0; i < COn[ic]; i++) push(Ov, COV[COo[ic] + i]);
        int droit = CDR[ic];
        float U[] = rc_cumul(Q);
        if (!droit) {
            // bord réel de A de l'embouchure au point de tangence Ta, puis amorce (Ta -> Ta')
            for (int i = 0; i < CAn[ic]; i++) { vector v = CAV[CAo[ic] + i]; push(C, set(v.x, v.y)); }
            float uta = CUTA[ic];
            int i_ta = len(Q) - 2;
            for (int i = len(Q) - 1; i >= 0; i--) if (abs(U[i] - uta) < 1e-3) { i_ta = i; break; }
            for (int i = i_ta; i < len(Q); i++) push(C, Q[i]);
        } else push(C, Q[-1]);
        for (int i = len(Ov) - 1; i >= 0; i--) push(C, set(Ov[i].x, Ov[i].y));
        if (!droit) {
            float utb = CUTB[ic];
            int i_tb = 1;
            for (int i = 0; i < len(Q); i++) if (abs(U[i] - utb) < 1e-3) { i_tb = i; break; }
            for (int i = 0; i <= i_tb; i++) push(C, Q[i]);
            for (int i = 0; i < CBn[ic]; i++) { vector v = CBV[CBo[ic] + i]; push(C, set(v.x, v.y)); }
        } else push(C, Q[0]);
    }
    // contour sans doublons consécutifs
    int cq[];
    vector2 prec = set(1e18, 1e18);
    foreach (vector2 v; C) {
        if (length(v - prec) < 1e-7) continue;
        push(cq, addpoint(0, rc_h(v, 0.0)));
        prec = v;
    }
    if (len(cq) > 2 && length(rc_xy(point(0, "P", cq[0])) - rc_xy(point(0, "P", cq[-1]))) < 1e-7) removepoint(0, cq[-1]);
    int pc = addprim(0, "poly", cq);
    setprimgroup(0, "contour", pc, 1);
    setprimattrib(0, "carrefour", pc, cid);
    // segments à Z imposé : embouchures (s_end) et bords de chaussée (de s_end au point de tangence)
    foreach (int p; bp) {
        string rid = string(point(0, "route", p));
        foreach (int q; expandprimgroup(0, "embouchure")) {
            if (prim(0, "route", q) != rid) continue;
            int ep[] = primpoints(0, q);
            int sq[] = array(addpoint(0, vector(point(0, "P", ep[0]))), addpoint(0, vector(point(0, "P", ep[-1]))));
            int ps = addprim(0, "polyline", sq); setprimgroup(0, "dseg", ps, 1);
            setprimattrib(0, "dkind", ps, "embouchure"); setprimattrib(0, "route", ps, rid);
            setprimattrib(0, "s", ps, float(point(0, "s_end", p)));
        }
    }
}
s[]@rg_carrefours_avertissements = avert;
i@rg_carrefours_faces = nface;
"""

VEX_CLASSER = r"""
// classer (primitive ; entrée 1 : domaine) : zone de chaque triangle par son centre (régions par priorité décroissante) :
// ilot (dessus d'îlot ou de nez), sous_bordure_ilot, trottoir / accotement / sous_bordure (coins), sinon chaussee.
vector c = prim(0, "P", @primnum);
vector2 x = rc_xy(c);
int best = -1;
string zone = "chaussee", ref = "";
foreach (int r; expandprimgroup(1, "regions")) {
    int pr = prim(1, "priorite", r);
    if (pr <= best) continue;
    int rp[] = primpoints(1, r);
    vector2 Q[];
    foreach (int p; rp) push(Q, rc_xy(point(1, "P", p)));
    if (rc_dans(Q, x)) { best = pr; zone = string(prim(1, "zone", r)); ref = string(prim(1, "ref", r)); }
}
s@zone = zone;
s@ref = ref;
i@haut = (zone == "trottoir" || zone == "ilot") ? 1 : 0;
s@carrefour_id = "";
foreach (int r; expandprimgroup(1, "contour")) {
    int rp[] = primpoints(1, r);
    vector2 Q[];
    foreach (int p; rp) push(Q, rc_xy(point(1, "P", p)));
    if (rc_dans(Q, x)) s@carrefour_id = string(prim(1, "carrefour", r));
}
"""

VEX_SCINDER = r"""
// scinder (détail) : chaque point commun à des faces hautes et basses est dédoublé (copie pour les faces hautes) ;
// arêtes de marche (arête d'une face haute partagée avec une face basse) -> murs verticaux entre les deux copies (fermés,
// cachés sous la bordure : TQ-BOR-007).
int np = npoints(0);
int haut_pt[], bas_pt[];
resize(haut_pt, np); resize(bas_pt, np);
for (int pr = 0; pr < nprimitives(0); pr++) {
    int h = prim(0, "haut", pr);
    foreach (int p; primpoints(0, pr)) { if (h) haut_pt[p] = 1; else bas_pt[p] = 1; }
}
addpointattrib(0, "haut", 0);
addpointattrib(0, "orig", -1);
addprimattrib(0, "mur_dir", {0, 0, 0});
int copie[];
resize(copie, np);
for (int p = 0; p < np; p++) {
    copie[p] = -1;
    setpointattrib(0, "orig", p, p);
    if (haut_pt[p] && !bas_pt[p]) setpointattrib(0, "haut", p, 1);
    if (haut_pt[p] && bas_pt[p]) {
        int q = addpoint(0, p);
        setpointattrib(0, "haut", q, 1);
        setpointattrib(0, "orig", q, p);
        copie[p] = q;
    }
}
// murs : arête (a, b) d'une face haute dont les deux bouts sont dédoublés et partagée avec une face basse
int npr = nprimitives(0);
for (int pr = 0; pr < npr; pr++) {
    if (!prim(0, "haut", pr)) continue;
    int vs[] = primpoints(0, pr);
    int n = len(vs);
    for (int i = 0; i < n; i++) {
        int a = vs[i], b = vs[(i + 1) % n];
        if (copie[a] < 0 || copie[b] < 0) continue;
        int pa[] = pointprims(0, a), pb[] = pointprims(0, b);
        int bas_commun = 0;
        foreach (int x; pa) if (!prim(0, "haut", x) && find(pb, x) >= 0) bas_commun = 1;
        if (!bas_commun) continue;
        int m = addprim(0, "poly", array(a, b, copie[b], copie[a]));
        setprimattrib(0, "zone", m, "mur");
        setprimattrib(0, "haut", m, -1);
        // côté bas : à droite de (a, b) dans le sens de la face haute (le sens est corrigé ensuite si besoin)
        vector A = point(0, "P", a), B = point(0, "P", b);
        setprimattrib(0, "mur_dir", m, set(A.z - B.z, 0, B.x - A.x));
    }
}
// faces hautes recâblées sur les copies
for (int pr = 0; pr < npr; pr++) {
    if (!prim(0, "haut", pr)) continue;
    int nv = primvertexcount(0, pr);
    for (int i = 0; i < nv; i++) {
        int vx = primvertex(0, pr, i);
        int p = vertexpoint(0, vx);
        if (copie[p] >= 0) setvertexpoint(0, pr, i, copie[p]);
    }
}
"""

VEX_ALTITUDE = r"""
// altitude (point ; entrée 1 : domaine, 2 : NIVEAUX, 3 : profils) : Z imposé ou calculé.
//   bas : embouchures et bords de chaussée des branches (modèle unique, rg_coupe), coins (pied de la bordure, linéaire
//         sur l'arc entre les bords des deux branches), accotements de coin (pied + dévers) ; ailleurs libre (i@libre :
//         interpolation harmonique ensuite) ;
//   haut : trottoir de coin = tête − 4 mm + dévers depuis l'arrière de la bordure (TQ-SOL-013 (5)), coupe des trottoirs
//          au Z du modèle de la branche ; dessus des nez au Z de la bande d'îlot de la branche ; îlots du cœur : ensuite.
float rampe = 7.0;
int haut = i@haut;
vector2 x = rc_xy(@P);
i@libre = 0;
i@fixe_ilot = 0;
float z = 0.0;
int fait = 0;
// segments à Z imposé
foreach (int sgm; expandprimgroup(1, "dseg")) {
    int sp_[] = primpoints(1, sgm);
    vector2 a = rc_xy(point(1, "P", sp_[0])), b = rc_xy(point(1, "P", sp_[1]));
    float u;
    if (rc_dist_seg(x, a, b, u) > 2e-4) continue;
    string dk = string(prim(1, "dkind", sgm));
    if (dk == "coupe" && !haut) continue;
    string rid = string(prim(1, "route", sgm));
    int pr = rc_prim_route(2, rid);
    float s, t;
    rg_st_local(2, pr, x.x, x.y, s, t);
    float L = prim(2, "longueur_m", pr);
    if (dk == "coupe") s = float(prim(1, "s", sgm)) - 1e-4;
    s = clamp(s, 0.0, L - 1e-5);
    float S0[] = prim(2, "sec_s0", pr);
    string SP[] = prim(2, "sec_profil", pr);
    int k = rg_indice_section(S0, s);
    int spt = rg_point_section(2, rid, k);
    int pp = rg_point_profil(3, SP[k]);
    float T[], A[], G[], PIE[], TEE[], VU[], dz;
    int CLS[];
    string msg;
    if (!rg_coupe(3, pp, 2, spt, 3, rid, s, rampe, T, A, G, CLS, PIE, TEE, VU, dz, msg)) error("%s", msg);
    z = haut ? rc_z_haut(T, A, G, CLS, dz, t) : rc_z_bas(T, A, G, CLS, dz, t);
    fait = 1;
    break;
}
// faces de bordure de coin : pied, tête (abaissés), trottoir et accotement
if (!fait) {
    float best = 1e18;
    int fb = -1;
    float ub = 0, cb = 0;
    foreach (int f; expandprimgroup(1, "face")) {
        if (prim(1, "kind", f) != "coin") continue;
        if (haut && s@zone_pt == "ilot") continue;
        int fp[] = primpoints(1, f);
        vector2 Q[];
        foreach (int p; fp) push(Q, rc_xy(point(1, "P", p)));
        float sc, co;
        float d = rc_dist_poly(Q, x, sc, co);
        if (co < -1e-7 && d > 1e-6) continue;                 // côté chaussée : pas concerné
        if (d < best) { best = d; fb = f; ub = sc; }
    }
    if (fb >= 0) {
        float base = float(prim(1, "base", fb)), Lt = float(prim(1, "longueur", fb));
        int fpp[] = primpoints(1, fb);
        vector2 Qf[];
        foreach (int v; fpp) push(Qf, rc_xy(point(1, "P", v)));
        float Uf[] = rc_cumul(Qf);
        float PZf[] = prim(1, "pied_z", fb);
        float pied = rc_interp(Uf, PZf, ub);
        string zext = prim(1, "zone_ext", fb);
        float ga = prim(1, "g_a", fb), gb = prim(1, "g_b", fb);
        float g = gb + (ga - gb) * (Lt > 0 ? ub / Lt : 0.0);
        if (!haut) {
            float gla = prim(1, "gl_a", fb), glb = prim(1, "gl_b", fb);
            float gl = glb + (gla - glb) * (Lt > 0 ? ub / Lt : 0.0);
            if (s@zone_pt == "accotement") { z = pied + g * best; fait = 1; }
            else if (best <= base + 1e-4) { z = pied + gl * best; fait = 1; }
        } else if (best >= base - chf("../recouvrement_tete") - 1e-4) {
            float A0[] = prim(1, "ab0", fb), A1[] = prim(1, "ab1", fb), AV[] = prim(1, "abv", fb), AR[] = prim(1, "abr", fb);
            float vue = rc_vue(prim(1, "vue", fb), A0, A1, AV, AR, ub);
            z = pied + vue - float(prim(1, "retrait", fb)) + g * (best - base);
            fait = 1;
        }
    }
}
// dessus des nez : bande d'îlot de la branche en s_end
if (!fait && haut) {
    foreach (int f; expandprimgroup(1, "face")) {
        if (prim(1, "kind", f) != "nez") continue;
        vector Bv[] = prim(1, "arriere", f);
        vector2 Q[];
        foreach (vector v; Bv) push(Q, set(v.x, v.y));
        float sc, co;
        float d = rc_dist_poly(Q, x, sc, co);
        if (!rc_dans(Q, x) && d > 2e-4) continue;
        string rid = string(prim(1, "route", f));
        int pr = rc_prim_route(2, rid);
        float se = float(prim(1, "s_end", f));
        float s, t;
        rg_st_local(2, pr, x.x, x.y, s, t);
        s = se - 1e-4;
        float S0[] = prim(2, "sec_s0", pr);
        string SP[] = prim(2, "sec_profil", pr);
        int k = rg_indice_section(S0, s);
        int spt = rg_point_section(2, rid, k);
        int pp = rg_point_profil(3, SP[k]);
        float T[], A[], G[], PIE[], TEE[], VU[], dz;
        int CLS[];
        string msg;
        if (!rg_coupe(3, pp, 2, spt, 3, rid, s, rampe, T, A, G, CLS, PIE, TEE, VU, dz, msg)) error("%s", msg);
        z = rc_z_haut(T, A, G, CLS, dz, clamp(t, float(prim(1, "t_d", f)), float(prim(1, "t_g", f))));
        fait = 1;
        break;
    }
}
if (!fait) {
    if (haut) i@fixe_ilot = 1; else i@libre = 1;
}
@P.y = z;
f@zz = z;
"""

VEX_ZONE_POINTS = r"""
// zone portée par les points (détail) : point bas d'une face d'accotement -> « accotement » ; point haut -> zone de ses
// faces hautes (trottoir, ilot)
addpointattrib(0, "zone_pt", "");
for (int pr = 0; pr < nprimitives(0); pr++) {
    string z = string(prim(0, "zone", pr));
    int h = prim(0, "haut", pr);
    if (h == 1 || z == "accotement")
        foreach (int p; primpoints(0, pr)) setpointattrib(0, "zone_pt", p, z);
}
"""

VEX_IDW = r"""
// initialisation des points bas libres : moyenne pondérée (1/d²) des points bas à Z imposé (entrée 1 : même géométrie)
if (!i@libre) return;
float sw = 0, sz = 0;
int n = npoints(1);
for (int p = 0; p < n; p++) {
    if (point(1, "libre", p) || point(1, "haut", p) || point(1, "fixe_ilot", p)) continue;
    vector q = point(1, "P", p);
    float d2 = (q.x - @P.x) * (q.x - @P.x) + (q.z - @P.z) * (q.z - @P.z) + 1e-6;
    float w = 1.0 / (d2 * d2);
    sw += w;
    sz += w * q.y;
}
if (sw > 0) { @P.y = sz / sw; f@zz = @P.y; }
"""

VEX_LISSER = r"""
// lissage (détail) : interpolation harmonique des points bas libres (Gauss-Seidel sur-relaxé, ordre des points :
// déterministe) ; voisins par les arêtes des faces basses (murs et faces hautes exclus) ; Z imposés fixes.
int n = npoints(0);
int iters = chi("../iterations_lissage");
float w = chf("../relaxation");
int lib[];
float z[];
int off[], nbr[];
resize(lib, n); resize(z, n); resize(off, n + 1);
for (int p = 0; p < n; p++) {
    lib[p] = point(0, "libre", p);
    z[p] = point(0, "zz", p);
    off[p] = len(nbr);
    if (!lib[p]) continue;
    int nb[] = neighbours(0, p);
    foreach (int q; nb) if (!point(0, "haut", q)) push(nbr, q);
}
off[n] = len(nbr);
float ecart = 0;
for (int it = 0; it < iters; it++) {
    ecart = 0;
    for (int p = 0; p < n; p++) {
        if (!lib[p]) continue;
        int a = off[p], b = off[p + 1];
        if (b <= a) continue;
        float s = 0;
        for (int j = a; j < b; j++) s += z[nbr[j]];
        float zn = z[p] + w * (s / (b - a) - z[p]);
        ecart = max(ecart, abs(zn - z[p]));
        z[p] = zn;
    }
}
for (int p = 0; p < n; p++) if (lib[p]) { vector P = point(0, "P", p); setpointattrib(0, "zz", p, z[p]); setpointattrib(0, "P", p, set(P.x, z[p], P.z)); }
f@rg_lissage_dernier_ecart = ecart;
"""

VEX_PIED_FACES = r"""
// pied des faces de nez et d'îlots (primitive, groupe face ; entrée 1 : sol bas résolu) : Z du sol bas sous chaque
// sommet de la face (rayon vertical) ; coins : loi déjà connue.
string kind = s@kind;
int pts[] = primpoints(0, @primnum);
float PZ[];
foreach (int p; pts) {
    vector P = point(0, "P", p);
    float z;
    if (kind == "coin") {
        float PZc[] = f[]@pied_z;
        z = PZc[len(PZ)];
    } else {
        int prs[];
        vector hits[], uvw[];
        int nh = intersect_all(1, "", set(P.x, 50.0, P.z), {0, -100, 0}, hits, prs, uvw, 1e-6, 1e-6);
        z = 0.0;
        float best = -1e18;
        int ok = 0;
        for (int i = 0; i < nh; i++) {
            if (prim(1, "haut", prs[i]) != 0) continue;
            if (hits[i].y > best) { best = hits[i].y; ok = 1; }
        }
        if (ok) z = best;
        else {
            int ph; vector uv;
            float dd = xyzdist(1, set(P.x, 0, P.z), ph, uv);
            vector pz = primuv(1, "P", ph, uv); z = pz.y;
        }
    }
    push(PZ, z);
}
f[]@pied_z = PZ;
"""

VEX_ALTITUDE_ILOTS = r"""
// dessus des îlots du cœur (point, fixe_ilot ; entrée 1 : faces avec pied_z) : tête − retrait (tête = pied + vue,
// abaissés compris : le refuge est abaissé au droit du passage)
if (!i@fixe_ilot) return;
vector2 x = rc_xy(@P);
float best = 1e18;
float z = 0.0;
foreach (int f; expandprimgroup(1, "face")) {
    if (prim(1, "kind", f) != "ilot") continue;
    int fp[] = primpoints(1, f);
    vector2 Q[];
    foreach (int p; fp) push(Q, rc_xy(point(1, "P", p)));
    if (!rc_dans(Q, x)) continue;
    float sc, co;
    float d = rc_dist_poly(Q, x, sc, co);
    if (d < best) {
        best = d;
        float U[] = rc_cumul(Q);
        float PZ[] = prim(1, "pied_z", f);
        float pied = rc_interp(U, PZ, sc);
        float A0[] = prim(1, "ab0", f), A1[] = prim(1, "ab1", f), AV[] = prim(1, "abv", f), AR[] = prim(1, "abr", f);
        z = pied + rc_vue(prim(1, "vue", f), A0, A1, AV, AR, sc) - float(prim(1, "retrait", f));
    }
}
@P.y = z;
f@zz = z;
"""

VEX_FINIR = r"""
// finir (primitive) : attributs du contrat de rg::sol (materiau_id, classe, z_type, visible, route, section, bande,
// bande_id, pj_couche, pj_entite, pj_maillage, priorite, chaine) ; murs et sol sous les bordures invisibles.
string z = s@zone;
string mat = "enrobe_bbsg_ancien";
int vis = 1;
if (z == "chaussee") mat = chs("../materiau_chaussee");
else if (z == "trottoir" || z == "accotement") {
    // matériau du trottoir : celui de la bande extérieure de la branche (face de coin de la région)
    int f = -1;
    foreach (int g; expandprimgroup(1, "face")) if (prim(1, "ref", g) == s@ref) f = g;
    mat = f >= 0 ? string(prim(1, "mat_ext", f)) : "enrobe_trottoir";
    if (mat == "") mat = "enrobe_trottoir";
} else if (z == "ilot") {
    int f = -1;
    foreach (int g; expandprimgroup(1, "face")) if (prim(1, "ref", g) == s@ref) f = g;
    mat = f >= 0 ? string(prim(1, "materiau_top", f)) : "beton_balaye";
    if (mat == "") mat = "beton_balaye";
} else if (z == "sous_bordure" || z == "sous_bordure_ilot") { mat = chs("../materiau_chaussee"); vis = 0; }
else if (z == "mur") { mat = "sol_cache"; vis = 0; }
s@materiau_id = mat;
s@classe = z == "chaussee" ? "carrefour_chaussee" : (z == "mur" ? "mur" : (z == "sous_bordure" || z == "sous_bordure_ilot" ? "sous_bordure" : "carrefour_" + z));
i@z_type = z == "mur" ? 14 : 10;
i@visible = vis;
s@route = s@carrefour_id;
i@section = -1;
i@bande = -1;
s@bande_id = z;
s@pj_couche = "PJ_Sol";
s@pj_entite = "SOL_" + re_replace("[^A-Za-z0-9]", "_", s@carrefour_id);
s@pj_maillage = mat;
i@priorite = 0;
i@chaine = -1;
"""

VEX_ENTITES = r"""
// entités (primitive, groupe face ; bordures seulement) : contrat de pj::lire_description (rg::vers_entites) : courbe
// d'arête avant au pied (Houdini), côté haut à gauche ; intervalles courant / chartière / bateau (pièce d'abaissé
// T2 -> T2_bateau, paramètre pieces_abaisse) ; niv_s, niv_z_pied, niv_z_tete ; aspect, caniveau vide.
if (s@bordure == "") { removeprim(0, @primnum, 1); return; }
int pts[] = primpoints(0, @primnum);
float PZ[] = f[]@pied_z;
float A0[] = f[]@ab0, A1[] = f[]@ab1, AV[] = f[]@abv, AR[] = f[]@abr;
float v0 = f@vue;
// abscisses : sommets + bornes des abaissés et des rampants (vue linéaire par morceaux exacte)
float U[];
foreach (int p; pts) push(U, float(point(0, "u", p)));
float S[];
foreach (float u; U) push(S, u);
for (int i = 0; i < len(A0); i++) {
    float c[] = array(A0[i] - AR[i], A0[i], A1[i], A1[i] + AR[i]);
    foreach (float x; c) if (x > 1e-6 && x < U[-1] - 1e-6) push(S, x);
}
S = sort(S);
float S2[];
foreach (float x; S) if (len(S2) == 0 || x - S2[-1] > 1e-6) push(S2, x);
// nouvelle courbe (points aux abscisses S2)
vector2 Q[];
foreach (int p; pts) push(Q, rc_xy(point(0, "P", p)));
int nq[];
float ZP[], ZT[], V[];
foreach (float x; S2) {
    int i = 0;
    while (i < len(U) - 2 && U[i + 1] < x) i++;
    float f = (U[i + 1] - U[i]) > 1e-12 ? clamp((x - U[i]) / (U[i + 1] - U[i]), 0.0, 1.0) : 0.0;
    vector2 q = Q[i] + f * (Q[i + 1] - Q[i]);
    float zp = PZ[i] + f * (PZ[i + 1] - PZ[i]);
    float vv = rc_vue(v0, A0, A1, AV, AR, x);
    push(ZP, zp); push(ZT, zp + vv); push(V, vv);
    push(nq, addpoint(0, rc_h(q, zp)));
}
int np_ = addprim(0, "polyline", nq);
// intervalles
string prof = s@bordure;
string bateau = prof;
foreach (string paire; split(chs("../pieces_abaisse"), ",")) {
    string kv[] = split(paire, ":");
    if (len(kv) == 2 && strip(kv[0]) == prof) bateau = strip(kv[1]);
}
dict ivs[];
int i = 0, n = len(S2);
while (i < n - 1) {
    float dv = V[i + 1] - V[i];
    int j = i + 1;
    if (abs(dv) < 1e-6) {
        while (j < n - 1 && abs(V[j + 1] - V[j]) < 1e-6 && abs(V[j] - V[i]) < 1e-6) j++;
        dict d; d["s0"] = S2[i]; d["s1"] = S2[j]; d["vue_m"] = V[i];
        if (V[i] < v0 - 0.02) { d["profil"] = bateau; d["role"] = "bateau"; } else { d["profil"] = prof; d["role"] = "courant"; }
        push(ivs, d);
    } else {
        float pente = dv / max(S2[i + 1] - S2[i], 1e-9);
        while (j < n - 1 && abs((V[j + 1] - V[j]) / max(S2[j + 1] - S2[j], 1e-9) - pente) < 1e-4) j++;
        dict d; d["s0"] = S2[i]; d["s1"] = S2[j]; d["profil"] = prof; d["vue_m"] = V[i]; d["vue_m_fin"] = V[j];
        d["role"] = "chartiere";
        push(ivs, d);
    }
    i = j;
}
string id = "K-" + re_replace("[^A-Za-z0-9.]", "_", s@ref);
setprimattrib(0, "id", np_, id);
setprimattrib(0, "famille", np_, "bordures");
setprimattrib(0, "ligne_ref", np_, "arete_avant");
setprimattrib(0, "intervalles", np_, ivs);
setprimattrib(0, "niv_s", np_, S2);
setprimattrib(0, "niv_z_pied", np_, ZP);
setprimattrib(0, "niv_z_tete", np_, ZT);
dict asp;
asp["epaufrures"] = 0.1; asp["salissure"] = 0.2; asp["mousse_joints"] = 0.05; asp["herbe_joints"] = 0.0;
setprimattrib(0, "aspect", np_, asp);
dict can;
setprimattrib(0, "caniveau", np_, can);
setprimattrib(0, "props", np_, "{}");
setprimattrib(0, "materiau_id", np_, s@materiau_bordure);
setprimattrib(0, "route", np_, s@carrefour);
removeprim(0, @primnum, 1);
"""

VEX_BEV = r"""
// bev (détail ; entrée 1 : domaine (faces), 2 : sol du carrefour) : bandes d'éveil de vigilance derrière chaque
// abaissé d'une bordure de coin ou d'îlot (DEF-031 : à 0,50 m du nez, profondeur 0,5875 m, 0,40 m si le trottoir fait
// moins de 1,90 m ; RF-MA-BEV-002), sur la longueur de l'abaissé (vue constante) ; dalles 3 mm au-dessus du sol.
float recul = chf("../bev_recul"), prof = chf("../bev_profondeur"), prof_r = chf("../bev_profondeur_reduite");
float seuil = chf("../bev_seuil_trottoir");
addprimattrib(0, "materiau_id", ""); addprimattrib(0, "id", ""); addprimattrib(0, "route", "");
addprimattrib(0, "materiau_voisin", "");
addvertexattrib(0, "uv", {0, 0, 0});
foreach (int f; expandprimgroup(1, "face")) {
    if (prim(1, "bordure", f) == "") continue;
    float A0[] = prim(1, "ab0", f), A1[] = prim(1, "ab1", f);
    if (len(A0) == 0) continue;
    string kind = string(prim(1, "kind", f));
    int fp[] = primpoints(1, f);
    vector2 Q[];
    foreach (int p; fp) push(Q, rc_xy(point(1, "P", p)));
    float U[] = rc_cumul(Q);
    float wmin = 1e9;
    if (kind == "coin") wmin = min(prim(1, "w_a", f), float(prim(1, "w_b", f)));
    float dp = wmin < seuil ? prof_r : prof;
    string voisin = kind == "coin" ? string(prim(1, "mat_ext", f)) : string(prim(1, "materiau_top", f));
    for (int k = 0; k < len(A0); k++) {
        int nseg = max(1, int(ceil((A1[k] - A0[k]) / 0.25)));
        for (int j = 0; j < nseg; j++) {
            float ua = A0[k] + (A1[k] - A0[k]) * j / nseg, ub = A0[k] + (A1[k] - A0[k]) * (j + 1) / nseg;
            vector2 pa = {0, 0}, pb = {0, 0}, ta = {1, 0}, tb = {1, 0};
            for (int i = 0; i + 1 < len(Q); i++) {
                if (ua >= U[i] - 1e-9 && ua <= U[i + 1] + 1e-9) { float g = (ua - U[i]) / max(U[i + 1] - U[i], 1e-12); pa = Q[i] + g * (Q[i + 1] - Q[i]); ta = normalize(Q[i + 1] - Q[i]); }
                if (ub >= U[i] - 1e-9 && ub <= U[i + 1] + 1e-9) { float g = (ub - U[i]) / max(U[i + 1] - U[i], 1e-12); pb = Q[i] + g * (Q[i + 1] - Q[i]); tb = normalize(Q[i + 1] - Q[i]); }
            }
            vector2 c4[] = array(pa + recul * rc_gauche(ta), pb + recul * rc_gauche(tb),
                                 pb + (recul + dp) * rc_gauche(tb), pa + (recul + dp) * rc_gauche(ta));
            int qq[];
            foreach (vector2 v; c4) {
                // Z du sol haut sous le point (rayon vertical) + 3 mm
                vector hits[]; int prs[]; vector uvw[];
                int nh = intersect_all(2, "", set(v.x, 50.0, -v.y), {0, -100, 0}, hits, prs, uvw, 1e-6, 1e-6);
                float zt = -1e18;
                for (int h = 0; h < nh; h++) if (prim(2, "haut", prs[h]) == 1 && hits[h].y > zt) zt = hits[h].y;
                if (zt < -1e17) zt = 0.0;
                push(qq, addpoint(0, rc_h(v, zt + 0.003)));
            }
            int pr = addprim(0, "poly", qq);
            setprimattrib(0, "materiau_id", pr, "bev_podotactile");
            setprimattrib(0, "id", pr, sprintf("BEV-%s-%d", string(prim(1, "ref", f)), k));
            setprimattrib(0, "route", pr, string(prim(1, "carrefour", f)));
            setprimattrib(0, "materiau_voisin", pr, voisin);
            setprimgroup(0, "dalles", pr, 1);
            float u0 = ua - A0[k], u1 = ub - A0[k];
            setvertexattrib(0, "uv", pr, 0, set(u0, 0, 0));
            setvertexattrib(0, "uv", pr, 1, set(u1, 0, 0));
            setvertexattrib(0, "uv", pr, 2, set(u1, 1, 0));
            setvertexattrib(0, "uv", pr, 3, set(u0, 1, 0));
        }
    }
}
"""

VEX_MARQUES = r"""
// marques (détail ; entrée 1 : solveur) : lignes transversales du modèle (CÉDEZ T'2 0,50 ; STOP continue 0,50 ;
// EFFET_FEUX T'2 0,15 : RF-MQ-CED-01, RF-MQ-STOP-01, RF-MQ-FEU-01, modulation RF-MQ-MOD-T'2) et bandes des passages sans
// route (traversée d'une voie directe : DEF-011, RF-MQ-PP-05), au contrat de pj::marquage_solide (polygones à plat).
string mat = chs("../materiau_peinture");
float us = chf("../usure_peinture");
string attrs_s[] = {"pj_entite", "id", "classe", "type", "gabarit", "materiau_id", "couleur", "route", "cle", "modulation"};
foreach (string a; attrs_s) addprimattrib(0, a, "");
addprimattrib(0, "usure", 0.0); addprimattrib(0, "couverture", 1.0); addprimattrib(0, "graine", 0);
addprimattrib(0, "partie", 0); addprimattrib(0, "anneau", 0); addprimattrib(0, "pj_region", -1);
addprimattrib(0, "largeur_m", 0.0); addprimattrib(0, "s0", 0.0); addprimattrib(0, "s1", 0.0);
addprimattrib(0, "rang", 0); addprimattrib(0, "bande_sol", -1); addprimattrib(0, "rg_ligne", 0);
foreach (int q; expandprimgroup(1, "ligne")) {
    string gab = prim(1, "gabarit", q);
    float larg = 0.5;
    int tirets = 1;
    if (gab == "STOP") { larg = chf("../stop_largeur"); tirets = 0; }
    else if (gab == "CEDEZ") larg = chf("../cedez_largeur");
    else if (gab == "EFFET_FEUX") larg = chf("../effet_largeur");
    else continue;
    float tr = chf("../tp2_trait"), iv = chf("../tp2_intervalle");
    int qp[] = primpoints(1, q);
    vector2 A = rc_xy(point(1, "P", qp[0])), B = rc_xy(point(1, "P", qp[-1]));
    float L = length(B - A);
    if (L < 1e-3) continue;
    vector2 e = (B - A) / L, nn = rc_gauche(e);
    float D0[], D1[];
    if (!tirets) { push(D0, 0.0); push(D1, L); }
    else {
        // traits de 0,50 m, intervalles de 0,50 m, motif centré ; un trait à chaque bout si la longueur le permet ([G])
        int nt = max(1, int(floor((L + iv) / (tr + iv) + 1e-9)));
        float tot = nt * tr + (nt - 1) * iv;
        float o = 0.5 * (L - tot);
        for (int k = 0; k < nt; k++) { push(D0, o + k * (tr + iv)); push(D1, o + k * (tr + iv) + tr); }
    }
    string idm = string(prim(1, "id", q));
    for (int k = 0; k < len(D0); k++) {
        vector2 c4[] = array(A + D0[k] * e - 0.5 * larg * nn, A + D1[k] * e - 0.5 * larg * nn,
                             A + D1[k] * e + 0.5 * larg * nn, A + D0[k] * e + 0.5 * larg * nn);
        int qq[];
        foreach (vector2 v; c4) push(qq, addpoint(0, rc_h(v, 0.0)));
        int pr = addprim(0, "poly", qq);
        string ent = sprintf("MQ_%s_t%03d", re_replace("[^A-Za-z0-9]", "_", idm), k);
        setprimattrib(0, "pj_entite", pr, ent); setprimattrib(0, "id", pr, sprintf("%s_t%03d", idm, k));
        setprimattrib(0, "classe", pr, "ligne_transversale"); setprimattrib(0, "type", pr, gab);
        setprimattrib(0, "gabarit", pr, gab); setprimattrib(0, "materiau_id", pr, mat);
        setprimattrib(0, "couleur", pr, string(prim(1, "couleur", q))); setprimattrib(0, "usure", pr, us);
        setprimattrib(0, "graine", pr, random_shash(ent) & 0x7fffffff);
        setprimattrib(0, "route", pr, string(prim(1, "route", q))); setprimattrib(0, "modulation", pr, tirets ? "T'2" : "continue");
        setprimattrib(0, "largeur_m", pr, larg); setprimattrib(0, "s0", pr, D0[k]); setprimattrib(0, "s1", pr, D1[k]);
        setprimattrib(0, "rang", pr, k);
    }
}
// passages sans route : repère de la voie (tangente de la face de coin la plus proche) ; n = floor((W − 0,5) / 1,0),
// e = (W − 0,5 n) / (n + 1) le long de l'axe (DEF-011) ; bandes de la longueur du passage
int coins[] = expandprimgroup(1, "coin");
foreach (int q; expandprimgroup(1, "passage_libre")) {
    int qp[] = primpoints(1, q);
    vector2 V[];
    vector2 G = {0, 0};
    foreach (int p; qp) { vector2 v = rc_xy(point(1, "P", p)); push(V, v); G += v; }
    G /= len(V);
    float best = 1e18;
    vector2 r = {1, 0};
    foreach (int c; coins) {
        int cp[] = primpoints(1, c);
        for (int i = 0; i + 1 < len(cp); i++) {
            vector2 a = rc_xy(point(1, "P", cp[i])), b = rc_xy(point(1, "P", cp[i + 1]));
            float u;
            float dd = rc_dist_seg(G, a, b, u);
            if (dd < best && length(b - a) > 1e-6) { best = dd; r = normalize(b - a); }
        }
    }
    vector2 cc = rc_gauche(r);
    float rmin = 1e18, rmax = -1e18, cmin = 1e18, cmax = -1e18;
    foreach (vector2 v; V) {
        rmin = min(rmin, dot(v - G, r)); rmax = max(rmax, dot(v - G, r));
        cmin = min(cmin, dot(v - G, cc)); cmax = max(cmax, dot(v - G, cc));
    }
    float W = cmax - cmin;
    float bande = chf("../passage_bande");
    int n = int(floor((W - bande) / (2.0 * bande) + 1e-9));
    float e = (W - bande * n) / (n + 1);
    string idm = string(prim(1, "id", q));
    for (int b = 0; b < n; b++) {
        float c0 = cmin + e + b * (bande + e), c1 = c0 + bande;
        vector2 c4[] = array(G + rmin * r + c0 * cc, G + rmax * r + c0 * cc, G + rmax * r + c1 * cc, G + rmin * r + c1 * cc);
        int qq[];
        foreach (vector2 v; c4) push(qq, addpoint(0, rc_h(v, 0.0)));
        int pr = addprim(0, "poly", qq);
        string ent = sprintf("MQ_%s_b%02d", re_replace("[^A-Za-z0-9]", "_", idm), b);
        setprimattrib(0, "pj_entite", pr, ent); setprimattrib(0, "id", pr, sprintf("%s_b%02d", idm, b));
        setprimattrib(0, "classe", pr, "passage"); setprimattrib(0, "type", pr, "bande");
        setprimattrib(0, "materiau_id", pr, mat); setprimattrib(0, "couleur", pr, string(prim(1, "couleur", q)));
        setprimattrib(0, "usure", pr, us); setprimattrib(0, "graine", pr, random_shash(ent) & 0x7fffffff);
        setprimattrib(0, "largeur_m", pr, bande); setprimattrib(0, "rang", pr, b);
    }
}
// passages des branches dont la bordure s'écarte dans un congé de coin (correction après le contrôle de l'étape 2 :
// bandes arrêtées au bord de chaussée de la section, 0,8 à 3 m d'enrobé non marqué devant la bordure du congé) :
// la série de bandes de chaque groupe extrême du passage (zones du modèle, rg::marquages : n = floor((W − e) / (b + e)),
// e = (W − b n) / (n + 1), RF-MQ-PP-05, DEF-011) est prolongée au-delà du bord, même pas, chaque bande découpée à la
// distance e de la face de bordure du congé (polyligne « coin ») ; tranches de 5 cm le long des bandes [G].
{
    float bpp = chf("../passage_bande");
    float emin = 0.5;
    float pasu = 0.05;
    int obst[] = coins;
    foreach (int c; expandprimgroup(1, "nez")) push(obst, c);
    foreach (int c; expandprimgroup(1, "ilot")) push(obst, c);
    foreach (int q; expandpointgroup(1, "passage")) {
        float zxy[] = point(1, "pp_zxy", q);
        int zn[] = point(1, "pp_zn", q);
        if (len(zn) == 0) continue;
        vector a3 = point(1, "axe0", q), b3 = point(1, "axe1", q);
        vector2 V = normalize(set(b3.x - a3.x, b3.y - a3.y));
        vector2 U = set(V.y, -V.x);
        vector2 O = set(a3.x, a3.y);
        // entités nommées d'après le marquage de chaque groupe (MQ_<id>_x…) : mêmes séries que celles de rg::marquages
        string zid[] = point(1, "pp_zid", q);
        // bords extérieurs de la traversée (toutes zones) : seuls les côtés extrêmes sont prolongés vers une bordure de
        // congé ; un côté de groupe qui fait face à un refuge, un îlot ou un TPC ne l'est jamais
        float vlo = 1e18, vhi = -1e18;
        for (int i = 0; i < len(zxy) / 2; i++) {
            float vv = dot(set(zxy[2 * i], zxy[2 * i + 1]) - O, V);
            vlo = min(vlo, vv); vhi = max(vhi, vv);
        }
        int k0 = 0, nx = 0;
        foreach (int iz; int nz; zn) {
            string idm = iz < len(zid) ? zid[iz] : string(point(1, "id", q));
            float umin = 1e18, umax = -1e18, vmin = 1e18, vmax = -1e18;
            for (int i = k0; i < k0 + nz; i++) {
                vector2 w = set(zxy[2 * i], zxy[2 * i + 1]) - O;
                umin = min(umin, dot(w, U)); umax = max(umax, dot(w, U));
                vmin = min(vmin, dot(w, V)); vmax = max(vmax, dot(w, V));
            }
            k0 += nz;
            float W = vmax - vmin;
            int n = int(floor((W - emin) / (bpp + emin) + 1e-9));
            if (n < 1) continue;
            float e = (W - bpp * n) / (n + 1);
            for (int cote = -1; cote <= 1; cote += 2) {
                float bord = cote > 0 ? vmax : vmin;
                if (abs(bord - (cote > 0 ? vhi : vlo)) > 1e-3) continue;
                // distance libre au-delà du bord, à chaque tranche : jusqu'à la face de bordure d'un congé, moins e
                int nu = max(2, int(ceil((umax - umin) / pasu)));
                float U_[], Lb[];
                int touche = 0;
                for (int k = 0; k <= nu; k++) {
                    float uu = umin + (umax - umin) * k / nu;
                    vector2 A = O + uu * U + bord * V, B = A + cote * 8.0 * V;
                    float dmin = 1e18;
                    // obstacles : faces de bordure des congés (coin), des nez et des îlots du cœur (îlot directionnel) :
                    // la bande s'arrête devant le premier rencontré
                    foreach (int c; obst) {
                        int cp[] = primpoints(1, c);
                        int ferme = inprimgroup(1, "ilot", c);
                        for (int i = 0; i + 1 < len(cp) + ferme; i++) {
                            vector2 c0 = rc_xy(point(1, "P", cp[i])), c1 = rc_xy(point(1, "P", cp[(i + 1) % len(cp)]));
                            vector2 r = B - A, sg = c1 - c0;
                            float den = rc_croix(r, sg);
                            if (abs(den) < 1e-12) continue;
                            float t = rc_croix(c0 - A, sg) / den, w_ = rc_croix(c0 - A, r) / den;
                            if (t >= 0 && t <= 1 && w_ >= 0 && w_ <= 1) dmin = min(dmin, t * 8.0);
                        }
                    }
                    push(U_, uu);
                    push(Lb, dmin < 1e17 ? dmin - e : -1.0);
                    if (dmin < 1e17 && dmin - e > 0.02) touche = 1;
                }
                if (!touche) continue;
                for (int j = 1; j <= 20; j++) {
                    float a0 = (j - 1) * (bpp + e), a1 = a0 + bpp;
                    // tranches où la bande existe (haut découpé à la bordure moins e), suites contiguës
                    int k = 0;
                    int faite = 0;
                    while (k <= nu) {
                        while (k <= nu && min(a1, Lb[k]) - a0 <= 0.02) k++;
                        if (k > nu) break;
                        int kd = k;
                        while (k <= nu && min(a1, Lb[k]) - a0 > 0.02) k++;
                        int kf = k - 1;
                        if (kf <= kd) continue;
                        vector2 Pb[], Ph[];
                        for (int z = kd; z <= kf; z++) {
                            push(Pb, O + U_[z] * U + (bord + cote * a0) * V);
                            push(Ph, O + U_[z] * U + (bord + cote * min(a1, Lb[z])) * V);
                        }
                        int qq[];
                        foreach (vector2 v; Pb) push(qq, addpoint(0, rc_h(v, 0.0)));
                        for (int z = len(Ph) - 1; z >= 0; z--) push(qq, addpoint(0, rc_h(Ph[z], 0.0)));
                        if (cote < 0) qq = reverse(qq);
                        int pr = addprim(0, "poly", qq);
                        string ent = sprintf("MQ_%s_x%s%02d", re_replace("[^A-Za-z0-9]", "_", idm), cote > 0 ? "g" : "d", nx);
                        setprimattrib(0, "pj_entite", pr, ent); setprimattrib(0, "id", pr, ent);
                        setprimattrib(0, "classe", pr, "passage"); setprimattrib(0, "type", pr, "bande");
                        setprimattrib(0, "materiau_id", pr, mat); setprimattrib(0, "couleur", pr, "blanc");
                        setprimattrib(0, "usure", pr, us); setprimattrib(0, "graine", pr, random_shash(ent) & 0x7fffffff);
                        setprimattrib(0, "largeur_m", pr, bpp); setprimattrib(0, "rang", pr, j);
                        setprimattrib(0, "route", pr, string(point(1, "route", q)));
                        nx++;
                        faite = 1;
                    }
                    if (!faite) break;
                }
            }
        }
    }
}
"""
