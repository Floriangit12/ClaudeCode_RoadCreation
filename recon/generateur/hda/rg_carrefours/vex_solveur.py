"""Code VEX de l'HDA rg::carrefours (solveur des carrefours plans, lot L3 : étapes 1 à 4 du plan § 2.4).

Importé par construire.py. Repère : local (x, y) ; Houdini (x, 0, −y). Branches tracées vers le centre.
"""

VEX_BRANCHES = r"""
// branches (détail ; entrée 0 : carrefours lus, entrée 1 : routes de rg::lire_modele, entrée 2 : profils) :
// repère de chaque branche à la limite de la chaussée abordée (s_front), bords de chaussée (première et dernière
// bande « chaussee »), largeurs extérieures (trottoir, berme), îlots de la bande médiane ; retrait du nez des îlots
// au premier contact des balayages des véhicules (lot L3a) + marge (RF-GV-ILO-015, plan § 3 L3) ; fin de route s_end.
float rn_def = chf("../nez_rayon");
float marge = chf("../marge_balayage");
float pas_nez = chf("../pas_retrait_nez");
string noms_f[] = {"s_end", "t_g", "t_d", "t_ext_g", "t_ext_d", "nez_c", "nez_retrait", "nez_intrusion_x",
                   "w_g", "w_d", "vue_g", "vue_d", "g_ext_g", "g_ext_d", "L_route"};
foreach (string nm; noms_f) addpointattrib(0, nm, 0.0);
addpointattrib(0, "lim_g", 0); addpointattrib(0, "lim_d", 0); addpointattrib(0, "n_ilots", 0);
addpointattrib(0, "nez_retrait_requis", 0.0); addpointattrib(0, "nez_limite_refuge", 0);
addpointattrib(0, "Pf", {0, 0, 0}); addpointattrib(0, "dir", {0, 0, 0}); addpointattrib(0, "nrm", {0, 0, 0});
addpointattrib(0, "Pe", {0, 0, 0});
string noms_s[] = {"bordure_g", "bordure_d", "mat_ext_g", "mat_ext_d", "ref_ext_g", "ref_ext_d", "type_ext_g",
                   "type_ext_d", "profil_front", "nez_balayage"};
foreach (string nm; noms_s) addpointattrib(0, nm, "");
int brs[] = expandpointgroup(0, "branche");
foreach (int p; brs) {
    string rid = string(point(0, "route", p));
    int pr = rc_prim_route(1, rid);
    if (pr < 0) error("branche %s : route %s absente", string(point(0, "branche", p)), rid);
    string ext = point(0, "extremite", p);
    if (ext != "fin") error("branche %s : extrémité « %s » non prise en charge (branches tracées vers le centre)",
                            string(point(0, "branche", p)), ext);
    float L = prim(1, "longueur_m", pr);
    float sf = float(point(0, "s_front", p));
    if (sf <= 0.0 || sf > L + 1e-6) error("branche %s : s_frontiere %g hors de [0, %g]", string(point(0, "branche", p)), sf, L);
    float S0[] = prim(1, "sec_s0", pr);
    string SP[] = prim(1, "sec_profil", pr);
    int k = rg_indice_section(S0, sf - 1e-6);
    int pp = rg_point_profil(2, SP[k]);
    if (pp < 0) error("profil %s absent", SP[k]);
    float T[] = rg_t_limites(2, pp, sf);
    int iL, iR;
    rc_bords(2, pp, iL, iR);
    if (iL < 0) error("branche %s : aucune bande de chaussée", string(point(0, "branche", p)));
    int nb = len(T) - 1;
    vector2 P, d, n;
    rc_repere(1, pr, sf, P, d, n);
    string ref[] = point(2, "niv_reference", pp);
    string lb[] = point(2, "lim_bordure", pp);
    float lv[] = point(2, "lim_vue", pp);
    string bm[] = point(2, "bande_materiau", pp);
    string bt[] = point(2, "bande_type", pp);
    float dv[] = point(2, "niv_devers", pp);
    setpointattrib(0, "L_route", p, L);
    setpointattrib(0, "lim_g", p, iL);
    setpointattrib(0, "lim_d", p, iR);
    setpointattrib(0, "t_g", p, T[iL]);
    setpointattrib(0, "t_d", p, T[iR]);
    setpointattrib(0, "t_ext_g", p, T[0]);
    setpointattrib(0, "t_ext_d", p, T[nb]);
    setpointattrib(0, "w_g", p, T[0] - T[iL]);
    setpointattrib(0, "w_d", p, T[iR] - T[nb]);
    setpointattrib(0, "bordure_g", p, lb[iL]);
    setpointattrib(0, "bordure_d", p, lb[iR]);
    setpointattrib(0, "vue_g", p, lv[iL]);
    setpointattrib(0, "vue_d", p, lv[iR]);
    setpointattrib(0, "profil_front", p, SP[k]);
    if (iL > 0) {
        setpointattrib(0, "mat_ext_g", p, bm[iL - 1]); setpointattrib(0, "ref_ext_g", p, ref[iL - 1]);
        setpointattrib(0, "type_ext_g", p, bt[iL - 1]);
        setpointattrib(0, "g_ext_g", p, dv[iL - 1] / 100.0);             // s'éloigner du bord = +t
    }
    if (iR < nb) {
        setpointattrib(0, "mat_ext_d", p, bm[iR]); setpointattrib(0, "ref_ext_d", p, ref[iR]);
        setpointattrib(0, "type_ext_d", p, bt[iR]);
        setpointattrib(0, "g_ext_d", p, -dv[iR] / 100.0);                // s'éloigner du bord = −t
    }
    setpointattrib(0, "Pf", p, set(P.x, P.y, 0));
    setpointattrib(0, "dir", p, set(d.x, d.y, 0));
    setpointattrib(0, "nrm", p, set(n.x, n.y, 0));
    // îlots de la bande médiane (bandes non « chaussee » entre les bords) : nez arrondi au rayon du modèle
    int ib[];
    float tl[], tr[];
    for (int b = iL; b < iR; b++) if (ref[b] != "chaussee") { push(ib, b); push(tl, T[b]); push(tr, T[b + 1]); }
    setpointattrib(0, "n_ilots", p, len(ib));
    float rn = rn_def;
    int ils[] = expandprimgroup(0, "ilot");
    foreach (int q; ils) if (prim(0, "pp_route", q) == rid && float(prim(0, "nez_rayon", q)) > 0) rn = float(prim(0, "nez_rayon", q));
    float c = len(ib) ? rn : 0.0;
    float delta = 0.0;
    float xout = 1e9;
    string qui = "";
    if (len(ib)) {
        // premier contact des balayages (véhicules faisables du lot L3a) avec la bande de l'îlot prolongée vers le
        // centre : abscisse x (le long de d, depuis s_front) la plus en arrière des parties de balayage dans la bande
        string cid = string(point(0, "carrefour", p));
        int bal[] = expandprimgroup(0, "balayage");
        foreach (int q; bal) {
            if (prim(0, "faisable", q) == 0 || string(prim(0, "carrefour", q)) != cid) continue;
            int qp[] = primpoints(0, q);
            int nq = len(qp);
            for (int i = 0; i < nq; i++) {
                vector2 A = rc_xy(point(0, "P", qp[i])), B = rc_xy(point(0, "P", qp[(i + 1) % nq]));
                float xa = dot(A - P, d), ya = dot(A - P, n), xb = dot(B - P, d), yb = dot(B - P, n);
                for (int j = 0; j < len(ib); j++) {
                    float lo = tr[j], hi = tl[j];
                    float cand = 1e9;
                    if (ya >= lo && ya <= hi) cand = xa;
                    float yls[] = array(lo, hi);
                    foreach (float yl; yls) {
                        if ((ya - yl) * (yb - yl) < 0.0) {
                            float u = (yl - ya) / (yb - ya);
                            cand = min(cand, xa + u * (xb - xa));
                        }
                    }
                    if (cand > -c - 5.0 && cand < xout) { xout = cand; qui = string(prim(0, "trajectoire", q)) + " " + string(prim(0, "vehicule", q)); }
                }
            }
        }
        if (xout < 1e8) delta = max(0.0, marge - xout);
        delta = ceil(delta / pas_nez - 1e-9) * pas_nez;
        // plafond : un passage qui traverse l'îlot garde son refuge (bande du passage + rampants des abaissés, DEF-031)
        float dmax = 1e9;
        foreach (int q; expandpointgroup(0, "passage")) {
            if (point(0, "route", q) != rid) continue;
            float sp_ = point(0, "s", q), wp = point(0, "largeur", q);
            if (sp_ < sf - 25.0 || sp_ > sf) continue;
            dmax = min(dmax, sf - c - (sp_ + 0.5 * wp + chf("../rampant_refuge")));
        }
        setpointattrib(0, "nez_retrait_requis", p, delta);
        if (delta > dmax) { delta = max(dmax, 0.0); setpointattrib(0, "nez_limite_refuge", p, 1); }
    }
    float s_end = sf - c - delta;
    setpointattrib(0, "nez_c", p, c);
    setpointattrib(0, "nez_retrait", p, delta);
    setpointattrib(0, "nez_intrusion_x", p, xout < 1e8 ? xout : 999.0);
    setpointattrib(0, "nez_balayage", p, qui);
    setpointattrib(0, "s_end", p, s_end);
    vector2 Pe, de, ne;
    rc_repere(1, pr, s_end, Pe, de, ne);
    setpointattrib(0, "Pe", p, set(Pe.x, Pe.y, 0));
}
"""

VEX_COINS = r"""
// coins (détail ; entrée 0 : branches résolues, entrée 1 : routes, entrée 2 : profils) : pour deux branches
// consécutives (ordre trigonométrique), bord droit de A et bord gauche de B ; congé de rayon R (coin_droit de A,
// DEF-010) tangent aux deux bords (droites de la chaussée près du carrefour), amorces droites de part et d'autre
// (paramètre « amorce », [G]) ; bords alignés (angle > 179°) : bordure droite d'une embouchure à l'autre. Sorties :
// polyligne de la face de bordure (groupe coin, côté haut à gauche, de B vers A ; points u, partie), coupes des
// trottoirs (s_cut_g de B, s_cut_d de A), frontière fermée du carrefour (groupe frontiere : joints et voies).
float amorce = chf("../amorce");
float rdef = chf("../rayon_defaut");
float fl = chf("../fleche");
addpointattrib(0, "s_cut_g", -1.0); addpointattrib(0, "s_cut_d", -1.0);
addpointattrib(0, "s_tan_g", -1.0); addpointattrib(0, "s_tan_d", -1.0);
addpointattrib(0, "coin_g", ""); addpointattrib(0, "coin_d", "");
addpointattrib(0, "u", 0.0); addpointattrib(0, "partie", 0);
addprimattrib(0, "coin", ""); addprimattrib(0, "branche_a", ""); addprimattrib(0, "branche_b", "");
addprimattrib(0, "route_a", ""); addprimattrib(0, "route_b", ""); addprimattrib(0, "carrefour", "");
addprimattrib(0, "rayon", 0.0); addprimattrib(0, "droit", 0); addprimattrib(0, "rayon_defaut", 0);
addprimattrib(0, "w_a", 0.0); addprimattrib(0, "w_b", 0.0); addprimattrib(0, "bordure", "");
addprimattrib(0, "vue", 0.0); addprimattrib(0, "mat_ext", ""); addprimattrib(0, "ref_ext", "");
addprimattrib(0, "type_ext", ""); addprimattrib(0, "g_a", 0.0); addprimattrib(0, "g_b", 0.0);
addprimattrib(0, "s_cut_a", 0.0); addprimattrib(0, "s_cut_b", 0.0); addprimattrib(0, "longueur", 0.0);
addprimattrib(0, "centre_arc", {0, 0, 0}); addprimattrib(0, "angle_deg", 0.0); addprimattrib(0, "tangente_hors", 0);
addprimattrib(0, "segment", "");
// carrefours dans l'ordre de première apparition
string cids[];
int brs[] = expandpointgroup(0, "branche");
foreach (int p; brs) { string c = string(point(0, "carrefour", p)); if (find(cids, c) < 0) push(cids, c); }
foreach (string cid; cids) {
    int bp[];
    foreach (int p; brs) if (point(0, "carrefour", p) == cid) push(bp, p);
    int rg_[];
    foreach (int p; bp) push(rg_, int(point(0, "rang", p)));
    int ord[] = argsort(rg_);
    int sb[];
    foreach (int o; ord) push(sb, bp[o]);
    int nbk = len(sb);
    if (nbk < 2) continue;
    // frontière : embouchures et voies (polyligne fermée)
    vector2 FR[];
    int FT[];                                       // 0 joint, 1 voie
    for (int k = 0; k < nbk; k++) {
        if (nbk == 2 && k == 1) break;
        int pa = sb[k], pb = sb[(k + 1) % nbk];
        vector Pfa = point(0, "Pf", pa), Pfb = point(0, "Pf", pb), da3 = point(0, "dir", pa), db3 = point(0, "dir", pb);
        vector na3 = point(0, "nrm", pa), nb3 = point(0, "nrm", pb);
        vector2 da = set(da3.x, da3.y), db = set(db3.x, db3.y), nA = set(na3.x, na3.y), nB = set(nb3.x, nb3.y);
        float sfa = float(point(0, "s_front", pa)), sfb = float(point(0, "s_front", pb));
        float sea = float(point(0, "s_end", pa)), seb = float(point(0, "s_end", pb));
        float tda = float(point(0, "t_d", pa)), tgb = float(point(0, "t_g", pb));
        vector2 Pa = set(Pfa.x, Pfa.y) + tda * nA;               // bord droit de A en s_front
        vector2 Pb = set(Pfb.x, Pfb.y) + tgb * nB;               // bord gauche de B en s_front
        string ra_ = point(0, "route", pa), rb_ = point(0, "route", pb);
        int pra = rc_prim_route(1, ra_), prb = rc_prim_route(1, rb_);
        vector2 Pa_e = rc_bord(1, pra, 2, sea, 0), Pb_e = rc_bord(1, prb, 2, seb, 1);   // en s_end
        vector2 ua = -da, ub = -db;
        float R = point(0, "rayon_coin", pa);
        int rdf = 0;
        float cphi = clamp(dot(ua, ub), -1.0, 1.0);
        int droit = cphi < -cos(radians(1.0));
        if (R <= 0.0 && !droit) { R = rdef; rdf = 1; }
        vector2 Q[];
        int PART[];
        float scut_a = sea, scut_b = seb, stan_a = sea, stan_b = seb;
        vector2 Cc = {0, 0};
        float angle = 0.0;
        int hors = 0;
        vector2 BA[], BB[];                                       // bords : A de s_end à Ta, B de Tb à s_end
        if (droit) {
            push(Q, Pb_e); push(PART, 0);
            push(Q, Pa_e); push(PART, 2);
        } else {
            // congé tangent aux bords réels (lois de largeur) : droites locales du bord au point de tangence (itéré)
            float sa = sfa, sb = sfb;
            vector2 Ta, Tb, ea, eb;
            float phi = 0, dt = 0;
            for (int it = 0; it < 6; it++) {
                vector2 A0 = rc_bord(1, pra, 2, min(sa, sea), 0), B0 = rc_bord(1, prb, 2, min(sb, seb), 1);
                ea = -rc_bord_dir(1, pra, 2, min(sa, sea - 0.05), 0, 0.05);
                eb = -rc_bord_dir(1, prb, 2, min(sb, seb - 0.05), 1, 0.05);
                vector2 w = B0 - A0;
                float den = rc_croix(ea, eb);
                float a = rc_croix(w, eb) / den, b = rc_croix(w, ea) / den;
                vector2 X = A0 + a * ea;
                float cp = clamp(dot(ea, eb), -1.0, 1.0);
                phi = acos(cp);
                dt = R / tan(phi / 2.0);
                Ta = X + dt * ea; Tb = X + dt * eb;
                Cc = X + (R / sin(phi / 2.0)) * normalize(ea + eb);
                float na_ = sfa + dot(Ta - set(Pfa.x, Pfa.y), da), nb_ = sfb + dot(Tb - set(Pfb.x, Pfb.y), db);
                if (abs(na_ - sa) < 1e-7 && abs(nb_ - sb) < 1e-7) { sa = na_; sb = nb_; break; }
                sa = na_; sb = nb_;
            }
            stan_a = sa; stan_b = sb;
            if (stan_a > sea + 1e-6 || stan_b > seb + 1e-6) hors = 1;   // tangence en avant de l'embouchure
            scut_a = min(stan_a, sea) - amorce;
            scut_b = min(stan_b, seb) - amorce;
            // amorce de B (bord réel de s_cut à s_tan), arc, amorce de A (bord réel de s_tan à s_cut)
            float sbb[] = rc_abscisses_bord(1, prb, scut_b, min(stan_b, seb), 0.5);
            for (int i = 0; i < len(sbb) - 1; i++) { push(Q, rc_bord(1, prb, 2, sbb[i], 1)); push(PART, 0); }
            push(Q, Tb); push(PART, 1);
            vector2 v0 = Tb - Cc, v1 = Ta - Cc;
            angle = atan2(rc_croix(v0, v1), dot(v0, v1));
            float pas = min(2.0 * acos(clamp(1.0 - fl / R, -1.0, 1.0)), radians(chf("../pas_angulaire_max")));
            int ns = max(2, int(ceil(abs(angle) / pas - 1e-9)));
            for (int i = 1; i < ns; i++) {
                float t = angle * i / ns;
                vector2 v = set(v0.x * cos(t) - v0.y * sin(t), v0.x * sin(t) + v0.y * cos(t));
                push(Q, Cc + v); push(PART, 1);
            }
            push(Q, Ta); push(PART, 1);
            float saa[] = rc_abscisses_bord(1, pra, scut_a, min(stan_a, sea), 0.5);
            for (int i = len(saa) - 2; i >= 0; i--) { push(Q, rc_bord(1, pra, 2, saa[i], 0)); push(PART, 2); }
            // bords réels entre l'embouchure et les points de tangence
            if (stan_a < sea - 1e-6) {
                float s1[] = rc_abscisses_bord(1, pra, stan_a, sea, 0.5);
                for (int i = len(s1) - 1; i >= 0; i--) push(BA, rc_bord(1, pra, 2, s1[i], 0));
            }
            if (stan_b < seb - 1e-6) {
                float s2[] = rc_abscisses_bord(1, prb, stan_b, seb, 0.5);
                foreach (float x; s2) push(BB, rc_bord(1, prb, 2, x, 1));
            }
        }
        // polyligne de face (côté haut à gauche : de B vers A)
        int qq[];
        float acc = 0.0;
        for (int i = 0; i < len(Q); i++) {
            if (i > 0) acc += length(Q[i] - Q[i - 1]);
            int q = addpoint(0, rc_h(Q[i], 0.0));
            setpointattrib(0, "u", q, acc);
            setpointattrib(0, "partie", q, PART[i]);
            push(qq, q);
        }
        int pl = addprim(0, "polyline", qq);
        setprimgroup(0, "coin", pl, 1);
        string coin = sprintf("%s.c%d", cid, k);
        setprimattrib(0, "coin", pl, coin);
        setprimattrib(0, "carrefour", pl, cid);
        setprimattrib(0, "branche_a", pl, string(point(0, "branche", pa)));
        setprimattrib(0, "branche_b", pl, string(point(0, "branche", pb)));
        setprimattrib(0, "route_a", pl, string(point(0, "route", pa)));
        setprimattrib(0, "route_b", pl, string(point(0, "route", pb)));
        setprimattrib(0, "rayon", pl, droit ? 0.0 : R);
        setprimattrib(0, "droit", pl, droit);
        setprimattrib(0, "rayon_defaut", pl, rdf);
        setprimattrib(0, "w_a", pl, float(point(0, "w_d", pa)));
        setprimattrib(0, "w_b", pl, float(point(0, "w_g", pb)));
        string bo = point(0, "bordure_d", pa);
        float vu = point(0, "vue_d", pa);
        if (bo == "") { bo = point(0, "bordure_g", pb); vu = point(0, "vue_g", pb); }
        setprimattrib(0, "bordure", pl, bo);
        setprimattrib(0, "vue", pl, vu);
        string me = point(0, "mat_ext_d", pa), re = point(0, "ref_ext_d", pa), te = point(0, "type_ext_d", pa);
        if (me == "") { me = point(0, "mat_ext_g", pb); re = point(0, "ref_ext_g", pb); te = point(0, "type_ext_g", pb); }
        setprimattrib(0, "mat_ext", pl, me);
        setprimattrib(0, "ref_ext", pl, re);
        setprimattrib(0, "type_ext", pl, te);
        setprimattrib(0, "g_a", pl, float(point(0, "g_ext_d", pa)));
        setprimattrib(0, "g_b", pl, float(point(0, "g_ext_g", pb)));
        setprimattrib(0, "s_cut_a", pl, scut_a);
        setprimattrib(0, "s_cut_b", pl, scut_b);
        setprimattrib(0, "longueur", pl, acc);
        setprimattrib(0, "centre_arc", pl, set(Cc.x, Cc.y, 0));
        setprimattrib(0, "angle_deg", pl, degrees(angle));
        setprimattrib(0, "tangente_hors", pl, hors);
        vector BAv[], BBv[];
        foreach (vector2 v; BA) push(BAv, set(v.x, v.y, 0));
        foreach (vector2 v; BB) push(BBv, set(v.x, v.y, 0));
        setprimattrib(0, "bord_a", pl, BAv);
        setprimattrib(0, "bord_b", pl, BBv);
        // directions extérieures des coupes des trottoirs (normales des branches, perpendiculaires à l'axe)
        setprimattrib(0, "n_a", pl, set(-nA.x, -nA.y, 0));
        setprimattrib(0, "n_b", pl, set(nB.x, nB.y, 0));
        setpointattrib(0, "s_cut_d", pa, scut_a);
        setpointattrib(0, "s_cut_g", pb, scut_b);
        setpointattrib(0, "s_tan_d", pa, stan_a);
        setpointattrib(0, "s_tan_g", pb, stan_b);
        setpointattrib(0, "coin_d", pa, coin);
        setpointattrib(0, "coin_g", pb, coin);
        // frontière : embouchure de A (bord gauche -> bord droit en s_end), bord droit de A jusqu'au point de
        // tangence, arc, bord gauche de B jusqu'à s_end
        vector Pe3 = point(0, "Pe", pa);
        float tga = float(point(0, "t_g", pa));
        push(FR, rc_bord(1, pra, 2, sea, 1)); push(FT, 0);
        push(FR, Pa_e); push(FT, 1);
        if (!droit) {
            foreach (vector2 v; BA) { push(FR, v); push(FT, 1); }
            for (int i = len(Q) - 1; i >= 0; i--) if (PART[i] == 1) { push(FR, Q[i]); push(FT, 1); }
            foreach (vector2 v; BB) { push(FR, v); push(FT, 1); }
        }
        push(FR, Pb_e); push(FT, 0);
    }
    if (len(FR) > 2) {
        int fq[];
        foreach (int i; vector2 v; FR) {
            int q = addpoint(0, rc_h(v, 0.0));
            setpointattrib(0, "partie", q, FT[i]);
            push(fq, q);
        }
        int pf = addprim(0, "poly", fq);
        setprimgroup(0, "frontiere", pf, 1);
        setprimattrib(0, "carrefour", pf, cid);
    }
}
"""

VEX_NEZ = r"""
// nez des îlots de la bande médiane (détail) : chaque îlot du profil coupé en s_end reçoit un nez arrondi (rayon du
// modèle, RF-GV-ILO-015 : 0,50 m ; demi-largeur si l'îlot est plus étroit) de longueur égale au rayon, sa pointe à
// s_front − retrait (premier contact des balayages + marge) ; face de bordure (groupe nez) de la limite droite à la
// limite gauche de l'îlot (îlot à gauche) ; embouchures (groupe embouchure : bord gauche -> bord droit en s_end, un
// sommet par limite).
addprimattrib(0, "branche", ""); addprimattrib(0, "route", ""); addprimattrib(0, "s_end", 0.0);
addprimattrib(0, "t_g", 0.0); addprimattrib(0, "t_d", 0.0); addprimattrib(0, "bande", "");
addprimattrib(0, "bordure_g", ""); addprimattrib(0, "bordure_d", ""); addprimattrib(0, "vue", 0.0);
addprimattrib(0, "materiau", ""); addprimattrib(0, "rayon", 0.0);
addpointattrib(0, "t", 0.0); addpointattrib(0, "limite", -1);
int brs[] = expandpointgroup(0, "branche");
foreach (int p; brs) {
    string rid = string(point(0, "route", p));
    int pr = rc_prim_route(1, rid);
    float se = float(point(0, "s_end", p));
    float S0[] = prim(1, "sec_s0", pr);
    string SP[] = prim(1, "sec_profil", pr);
    int k = rg_indice_section(S0, se - 1e-6);
    int pp = rg_point_profil(2, SP[k]);
    float T[] = rg_t_limites(2, pp, se);
    int iL, iR;
    rc_bords(2, pp, iL, iR);
    vector2 P, d, n;
    rc_repere(1, pr, se, P, d, n);
    string ref[] = point(2, "niv_reference", pp);
    string lb[] = point(2, "lim_bordure", pp);
    float lv[] = point(2, "lim_vue", pp);
    string bm[] = point(2, "bande_materiau", pp);
    string bid[] = point(2, "bande_id", pp);
    // embouchure
    int eq[];
    for (int l = iL; l <= iR; l++) {
        int q = addpoint(0, rc_h(P + T[l] * n, 0.0));
        setpointattrib(0, "t", q, T[l]);
        setpointattrib(0, "limite", q, l);
        push(eq, q);
    }
    int pe = addprim(0, "polyline", eq);
    setprimgroup(0, "embouchure", pe, 1);
    setprimattrib(0, "branche", pe, string(point(0, "branche", p)));
    setprimattrib(0, "route", pe, rid);
    setprimattrib(0, "s_end", pe, se);
    setprimattrib(0, "carrefour", pe, string(point(0, "carrefour", p)));
    float c = float(point(0, "nez_c", p));
    for (int b = iL; b < iR; b++) {
        if (ref[b] == "chaussee") continue;
        float tL = T[b], tR = T[b + 1];
        float r = min(c, 0.5 * (tL - tR));
        vector2 Q[];
        push(Q, P + tR * n);
        int na = 12;
        // quart de cercle droit : centre (c − r, tR + r), de −90° à 0°
        vector2 c1 = P + (c - r) * d + (tR + r) * n;
        for (int i = 0; i <= na; i++) {
            float a = radians(-90.0 + 90.0 * i / na);
            push(Q, c1 + r * cos(a) * d + r * sin(a) * n);
        }
        vector2 c2 = P + (c - r) * d + (tL - r) * n;
        for (int i = 0; i <= na; i++) {
            float a = radians(90.0 * i / na);
            vector2 v = c2 + r * cos(a) * d + r * sin(a) * n;
            if (length(v - Q[-1]) > 1e-6) push(Q, v);
        }
        push(Q, P + tL * n);
        int qq[];
        float acc = 0.0;
        for (int i = 0; i < len(Q); i++) {
            if (i > 0) acc += length(Q[i] - Q[i - 1]);
            int q = addpoint(0, rc_h(Q[i], 0.0));
            setpointattrib(0, "u", q, acc);
            push(qq, q);
        }
        int pl = addprim(0, "polyline", qq);
        setprimgroup(0, "nez", pl, 1);
        setprimattrib(0, "coin", pl, sprintf("%s.nez.%s", string(point(0, "branche", p)), bid[b]));
        setprimattrib(0, "carrefour", pl, string(point(0, "carrefour", p)));
        setprimattrib(0, "branche", pl, string(point(0, "branche", p)));
        setprimattrib(0, "route", pl, rid);
        setprimattrib(0, "s_end", pl, se);
        setprimattrib(0, "t_g", pl, tL);
        setprimattrib(0, "t_d", pl, tR);
        setprimattrib(0, "bande", pl, bid[b]);
        setprimattrib(0, "bordure_g", pl, lb[b]);
        setprimattrib(0, "bordure_d", pl, lb[b + 1]);
        setprimattrib(0, "bordure", pl, lb[b + 1] != "" ? lb[b + 1] : lb[b]);
        setprimattrib(0, "vue", pl, lb[b + 1] != "" ? lv[b + 1] : lv[b]);
        setprimattrib(0, "materiau", pl, bm[b]);
        setprimattrib(0, "rayon", pl, r);
        setprimattrib(0, "longueur", pl, acc);
    }
}
"""

VEX_COUPER_ROUTES = r"""
// couper_routes (primitive ; entrée 1 : solveur) : route d'une branche raccourcie à s_end (fin de la chaussée de la
// branche, nez des îlots compris) ; trottoirs (bandes extérieures au bord de chaussée) retirés au-delà de s_cut de
// chaque côté (le coin les remplace : congé, amorce et trottoir du coin) : sections coupées, profil réduit
// « <profil>~cG », « ~cD » ou « ~cGD » (transition instantanée), primitives de la ligne de référence coupées.
int bp = findattribval(1, "point", "route", s@id);
if (bp < 0 || !inpointgroup(1, "branche", bp)) return;
float se = float(point(1, "s_end", bp));
float cg = point(1, "s_cut_g", bp), cd = point(1, "s_cut_d", bp);
if (cg < 0) cg = se;
if (cd < 0) cd = se;
// coupes confondues (à 1 mm) : une seule abscisse ; coupe confondue avec une borne de section ou avec s_end : la borne
if (abs(cd - cg) < 1e-3) cd = cg;
float S0_[] = f[]@sec_s0, S1_[] = f[]@sec_s1;
foreach (float x; S0_) { if (abs(cg - x) < 1e-3) cg = x; if (abs(cd - x) < 1e-3) cd = x; }
foreach (float x; S1_) { if (abs(cg - x) < 1e-3) cg = x; if (abs(cd - x) < 1e-3) cd = x; }
if (abs(cg - se) < 1e-3) cg = se;
if (abs(cd - se) < 1e-3) cd = se;
// ligne de référence
int GT[] = i[]@geo_type;
float G0[] = f[]@geo_s0, GL[] = f[]@geo_longueur, GX[] = f[]@geo_x0, GY[] = f[]@geo_y0, GC[] = f[]@geo_cap;
float K0[] = f[]@geo_k0, K1[] = f[]@geo_k1;
int nT[]; float n0[], nL[], nX[], nY[], nC[], nK0[], nK1[];
for (int i = 0; i < len(G0); i++) {
    if (G0[i] >= se - 1e-9) continue;
    push(nT, GT[i]); push(n0, G0[i]); push(nL, min(GL[i], se - G0[i])); push(nX, GX[i]); push(nY, GY[i]);
    push(nC, GC[i]); push(nK0, K0[i]);
    // clothoïde coupée : courbure de fin au point de coupe
    float k1 = K1[i];
    if (GT[i] == 2 && GL[i] > 1e-9 && G0[i] + GL[i] > se) k1 = K0[i] + (K1[i] - K0[i]) * (se - G0[i]) / GL[i];
    push(nK1, k1);
}
i[]@geo_type = nT; f[]@geo_s0 = n0; f[]@geo_longueur = nL; f[]@geo_x0 = nX; f[]@geo_y0 = nY; f[]@geo_cap = nC;
f[]@geo_k0 = nK0; f[]@geo_k1 = nK1;
f@longueur_m = se;
// sections
float S0[] = f[]@sec_s0, S1[] = f[]@sec_s1;
string SP[] = s[]@sec_profil, ST[] = s[]@sec_transition;
float a0[], a1[];
string ap[], at[];
for (int k = 0; k < len(S0); k++) {
    float x0 = S0[k], x1 = min(S1[k], se);
    // section qui commencerait à moins de 1 mm de s_end : absorbée par la précédente (correction après le contrôle de
    // l'étape 2 : nez reculé jusqu'à la borne d'une section, tronçon de longueur nulle, « moins de deux échantillons »)
    if (x0 >= se - 1e-3) continue;
    if (k + 1 >= len(S0) || S0[k + 1] >= se - 1e-3) x1 = se;
    float cuts[] = array(x0);
    if (cg > x0 + 1e-6 && cg < x1 - 1e-6) push(cuts, cg);
    if (cd > x0 + 1e-6 && cd < x1 - 1e-6 && cd != cg) push(cuts, cd);
    push(cuts, x1);
    cuts = sort(cuts);
    for (int j = 0; j + 1 < len(cuts); j++) {
        float u0 = cuts[j], u1 = cuts[j + 1];
        int fg = (u0 >= cg - 1e-6) && cg < se - 1e-6;
        int fd = (u0 >= cd - 1e-6) && cd < se - 1e-6;
        string suf = fg && fd ? "~cGD" : (fg ? "~cG" : (fd ? "~cD" : ""));
        push(a0, u0); push(a1, u1); push(ap, SP[k] + suf);
        push(at, j == 0 ? ST[k] : "instantanee");
    }
}
f[]@sec_s0 = a0; f[]@sec_s1 = a1; s[]@sec_profil = ap; s[]@sec_transition = at;
// polyligne de la route : sommets au-delà de s_end retirés, point de fin ajouté
int pts[] = primpoints(0, @primnum);
float acc = 0.0;
vector q0 = point(0, "P", pts[0]);
int garde = 1;
for (int i = 1; i < len(pts); i++) {
    vector q = point(0, "P", pts[i]);
    acc += length(q - q0);
    q0 = q;
    if (acc >= se - 1e-6) { removepoint(0, pts[i]); }
}
float x, y, th, kk;
rg_reference(0, @primnum, se, x, y, th, kk);
int pfin = addpoint(0, set(x, 0.0, -y));
addvertex(0, @primnum, pfin);
"""

VEX_PROFILS_REDUITS = r"""
// profils_reduits (détail ; entrée 0 : profils, entrée 1 : routes coupées) : un point de profil par profil réduit
// demandé (« <profil>~cG » : bandes extérieures retirées à gauche du bord de chaussée ; « ~cD » à droite ; « ~cGD » des
// deux côtés) ; le bord de chaussée devient la limite extérieure, sans bordure (le coin la porte), sans marquage de rive
// (interrompu au droit du carrefour) ; bandes et limites recopiées, lois de largeur conservées (indices).
string noms_b_i[] = {"larg_type", "larg_s0", "larg_v0", "larg_n"};
string noms_b_f[] = {"niv_dz", "niv_devers"};
string noms_b_s[] = {"bande_id", "bande_type", "bande_sous_type", "bande_sens", "bande_materiau", "niv_reference",
                     "niv_forme", "bande_json"};
string noms_l_f[] = {"lim_vue"};
string noms_l_s[] = {"lim_nature", "lim_bordure", "lim_vue_loi", "lim_cote_haut", "lim_caniveau", "lim_marquages",
                     "lim_separateur", "lim_json"};
string faits[];
for (int pr = 0; pr < nprimitives(1); pr++) {
    string SP[] = prim(1, "sec_profil", pr);
    foreach (string nom; SP) {
        int i = find(nom, "~c");
        if (i < 0 || find(faits, nom) >= 0) continue;
        push(faits, nom);
        string base = nom[0:i], suf = nom[i + 2:];
        int p0 = rg_point_profil(0, base);
        if (p0 < 0) error("profil %s absent", base);
        int iL, iR;
        rc_bords(0, p0, iL, iR);
        int nb = point(0, "n_bandes", p0);
        int b0 = (find(suf, "G") >= 0) ? iL : 0;
        int b1 = (find(suf, "D") >= 0) ? iR : nb;           // bandes gardées [b0, b1)
        int rl = point(0, "ref_limite", p0);
        if (rl < b0 || rl > b1) error("profil %s : référence hors de la chaussée", base);
        int np = addpoint(0, p0);
        setpointattrib(0, "profil", np, nom);
        setpointattrib(0, "n_bandes", np, b1 - b0);
        setpointattrib(0, "ref_limite", np, rl - b0);
        foreach (string a; noms_b_i) { int v[] = point(0, a, p0); setpointattrib(0, a, np, v[b0:b1]); }
        foreach (string a; noms_b_f) { float v[] = point(0, a, p0); setpointattrib(0, a, np, v[b0:b1]); }
        foreach (string a; noms_b_s) { string v[] = point(0, a, p0); setpointattrib(0, a, np, v[b0:b1]); }
        foreach (string a; noms_l_f) {
            float v[] = point(0, a, p0);
            float w[] = v[b0:b1 + 1];
            if (b0 > 0) w[0] = -1.0;
            if (b1 < nb) w[-1] = -1.0;
            setpointattrib(0, a, np, w);
        }
        foreach (string a; noms_l_s) {
            string v[] = point(0, a, p0);
            string w[] = v[b0:b1 + 1];
            string vide = a == "lim_nature" ? "virtuelle" : (a == "lim_json" ? "{\"nature\":[\"virtuelle\"]}" : "");
            if (b0 > 0) w[0] = vide;
            if (b1 < nb) w[-1] = vide;
            setpointattrib(0, a, np, w);
        }
    }
}
"""
