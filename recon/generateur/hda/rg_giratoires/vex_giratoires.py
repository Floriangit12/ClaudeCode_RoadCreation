"""Code VEX de l'HDA rg::giratoires (solveur des giratoires, lot L5 giratoires).

Importé par construire.py. Repère : local (x, y) ; Houdini (x, 0, −y). Branches tracées vers le centre. Les coupes des
routes, les profils réduits et les embouchures reprennent tels quels le code du solveur des carrefours plans
(hda/rg_carrefours/vex_solveur.py : VEX_COUPER_ROUTES, VEX_PROFILS_REDUITS, VEX_NEZ) ; la sortie SOLVEUR suit le contrat
de rg::carrefours (README_RG § 9) pour que rg::carrefours_sol fabrique le sol de l'anneau, des bouches et des coins.
"""

VEX_ANNEAUX = r"""
// anneaux (détail ; entrée 0 : lecture) : rayons des limites du profil de l'anneau posés depuis le bord intérieur de la
// chaussée annulaire r_ci = Rg − la (anneau du modèle, RF-GV-GIR-004), largeurs des bandes du profil de la route
// d'anneau ; R0 = bord extérieur de la chaussée (bandes « chaussee » : voie, bande dérasée) : cercle des raccordements.
addpointattrib(0, "r_ci", 0.0); addpointattrib(0, "R0", 0.0);
addpointattrib(0, "b0", -1); addpointattrib(0, "b1", -1);
string avert[];
foreach (int g; expandpointgroup(0, "giratoire")) {
    float Rg = point(0, "Rg", g), la = point(0, "la", g);
    string aref[] = point(0, "a_ref", g);
    float al[] = point(0, "a_larg", g);
    int b0 = -1, b1 = -1;
    for (int b = 0; b < len(aref); b++) if (aref[b] == "chaussee") { if (b0 < 0) b0 = b; b1 = b; }
    float r_ci = Rg - la;
    float R0 = Rg;
    float rl[];
    if (b0 >= 0) {
        resize(rl, len(al) + 1);
        rl[b0] = r_ci;
        for (int k = b0 - 1; k >= 0; k--) rl[k] = rl[k + 1] - al[k];
        for (int k = b0 + 1; k <= len(al); k++) rl[k] = rl[k - 1] + al[k - 1];
        R0 = rl[b1 + 1];
        float lv = 0;
        string aty[] = point(0, "a_type", g);
        for (int b = b0; b <= b1; b++) if (aty[b] == "voie_circulation") lv += al[b];
        if (abs(lv - la) > 1e-3)
            push(avert, sprintf("%s : voies du profil de l'anneau = %.2f m, anneau du modèle = %.2f m", string(point(0, "id", g)), lv, la));
        if (abs(R0 - Rg) > 1e-3)
            push(avert, sprintf("%s : bord extérieur de la chaussée annulaire R0 = %.2f m (bandes du profil depuis Rg − la) ; Rg = %.2f m", string(point(0, "id", g)), R0, Rg));
    } else {
        resize(rl, 2); rl[0] = r_ci; rl[1] = Rg;
        push(avert, sprintf("%s : profil d'anneau sans bande de chaussée : Rg − la, Rg", string(point(0, "id", g))));
    }
    setpointattrib(0, "r_lim", g, rl);
    setpointattrib(0, "r_ci", g, r_ci);
    setpointattrib(0, "R0", g, R0);
    setpointattrib(0, "b0", g, b0);
    setpointattrib(0, "b1", g, b1);
}
s[]@rg_giratoires_avertissements = avert;
"""

VEX_BRANCHES_G = r"""
// branches des giratoires (détail ; entrée 0 : lecture + anneaux, 1 : routes, 2 : profils) : repère de chaque branche
// à la frontière (s_front : bord de l'anneau sur l'axe), bords de chaussée (première et dernière bande « chaussee »),
// extérieurs (trottoir, berme) ; congés de raccordement tangents au bord réel de la branche et au bord extérieur de la
// chaussée annulaire (cercle R0) : entrée Re à droite si la branche a des voies entrantes, sortie Rs à gauche
// (raccordements du modèle, ACI tableau 1, RF-GV-GIR-003) ; coupes des trottoirs : amorce droite [G] avant le point de
// tangence, reculée pour qu'un passage proche garde ses rampants d'abaissé sur la bordure de coin (DEF-031).
float amorce = chf("../amorce");
float ram = chf("../rampant_passage");
float garde = chf("../garde_passage");
string noms_f[] = {"s_end", "t_g", "t_d", "t_ext_g", "t_ext_d", "nez_c", "nez_retrait", "nez_intrusion_x",
                   "w_g", "w_d", "vue_g", "vue_d", "g_ext_g", "g_ext_d", "L_route", "Rf_g", "Rf_d"};
foreach (string nm; noms_f) addpointattrib(0, nm, 0.0);
string noms_m[] = {"s_cut_g", "s_cut_d", "s_tan_g", "s_tan_d"};
foreach (string nm; noms_m) addpointattrib(0, nm, -1.0);
addpointattrib(0, "lim_g", 0); addpointattrib(0, "lim_d", 0); addpointattrib(0, "n_ilots", 0);
addpointattrib(0, "nez_retrait_requis", 0.0); addpointattrib(0, "nez_limite_refuge", 0);
string noms_v[] = {"Pf", "dir", "nrm", "Pe", "T_g", "T_d", "C_g", "C_d", "K_g", "K_d"};
foreach (string nm; noms_v) addpointattrib(0, nm, {0, 0, 0});
string noms_s[] = {"bordure_g", "bordure_d", "mat_ext_g", "mat_ext_d", "ref_ext_g", "ref_ext_d", "type_ext_g",
                   "type_ext_d", "profil_front", "nez_balayage", "coin_g", "coin_d"};
foreach (string nm; noms_s) addpointattrib(0, nm, "");
string avert[] = detail(0, "rg_giratoires_avertissements");
foreach (int p; expandpointgroup(0, "branche")) {
    string bid = point(0, "branche", p);
    string rid = string(point(0, "route", p));
    string cid = string(point(0, "carrefour", p));
    int g = rgi_giratoire(0, cid);
    vector o3 = point(0, "centre", g);
    vector2 O = set(o3.x, o3.y);
    float R0 = point(0, "R0", g);
    int pr = rc_prim_route(1, rid);
    if (pr < 0) error("branche %s : route %s absente", bid, rid);
    if (point(0, "extremite", p) != "fin") error("branche %s : extrémité « %s » non prise en charge (branches tracées vers le centre)", bid, string(point(0, "extremite", p)));
    float L = prim(1, "longueur_m", pr);
    float sf = float(point(0, "s_front", p));
    if (sf <= 0.0 || sf > L + 1e-6) error("branche %s : s_frontiere %g hors de [0, %g]", bid, sf, L);
    float S0[] = prim(1, "sec_s0", pr);
    string SP[] = prim(1, "sec_profil", pr);
    int k = rg_indice_section(S0, sf - 1e-6);
    int pp = rg_point_profil(2, SP[k]);
    if (pp < 0) error("profil %s absent", SP[k]);
    float T[] = rg_t_limites(2, pp, sf);
    int iL, iR;
    rc_bords(2, pp, iL, iR);
    if (iL < 0) error("branche %s : aucune bande de chaussée", bid);
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
        setpointattrib(0, "g_ext_g", p, dv[iL - 1] / 100.0);
    }
    if (iR < nb) {
        setpointattrib(0, "mat_ext_d", p, bm[iR]); setpointattrib(0, "ref_ext_d", p, ref[iR]);
        setpointattrib(0, "type_ext_d", p, bt[iR]);
        setpointattrib(0, "g_ext_d", p, -dv[iR] / 100.0);
    }
    setpointattrib(0, "Pf", p, set(P.x, P.y, 0));
    setpointattrib(0, "Pe", p, set(P.x, P.y, 0));
    setpointattrib(0, "dir", p, set(d.x, d.y, 0));
    setpointattrib(0, "nrm", p, set(n.x, n.y, 0));
    setpointattrib(0, "s_end", p, sf);
    // raccordements : entrée (Re) à droite si voies entrantes, sortie (Rs) à gauche si voies sortantes
    float Re = point(0, "Re", p), Rs = point(0, "Rs", p);
    int ne = point(0, "n_entrantes", p), ns = point(0, "n_sortantes", p);
    if (Re <= 0) Re = Rs;
    if (Rs <= 0) Rs = Re;
    if (Re <= 0) error("branche %s : raccordements absents du modèle (anneau.construction.raccordements)", bid);
    float Rcote[] = array(ne > 0 || ns == 0 ? Re : Rs, ns > 0 || ne == 0 ? Rs : Re);   // [droite, gauche]
    string cote[] = {"d", "g"};
    for (int j = 0; j < 2; j++) {
        float st;
        vector2 Tt, Cc, Kk;
        if (!rgi_conge(1, pr, 2, sf, j, O, R0, Rcote[j], st, Tt, Cc, Kk))
            error("branche %s : congé de rayon %g impossible côté %s", bid, Rcote[j], j ? "gauche" : "droit");
        // coupe du trottoir : amorce [G] ; un passage proche garde ses rampants (DEF-031) sur la bordure de coin
        float sc = st - amorce;
        foreach (int q; expandpointgroup(0, "passage")) {
            if (point(0, "route", q) != rid) continue;
            float sp = point(0, "s", q), wp = point(0, "largeur", q);
            if (sp + 0.5 * wp > sc - ram && sp - 0.5 * wp < sf) sc = min(sc, sp - 0.5 * wp - ram - garde);
        }
        if (sc < 0.5) { push(avert, sprintf("branche %s : coupe du trottoir ramenée de %.2f à 0,50 m", bid, sc)); sc = 0.5; }
        setpointattrib(0, "Rf_" + cote[j], p, Rcote[j]);
        setpointattrib(0, "s_tan_" + cote[j], p, st);
        setpointattrib(0, "s_cut_" + cote[j], p, sc);
        setpointattrib(0, "T_" + cote[j], p, set(Tt.x, Tt.y, 0));
        setpointattrib(0, "C_" + cote[j], p, set(Cc.x, Cc.y, 0));
        setpointattrib(0, "K_" + cote[j], p, set(Kk.x, Kk.y, 0));
    }
}
s[]@rg_giratoires_avertissements = avert;
"""

VEX_COINS_G = r"""
// coins des giratoires (détail ; entrée 0 : branches résolues, 1 : routes, 2 : profils) : pour deux branches
// consécutives A puis B (ordre trigonométrique), face de bordure de B vers A (côté haut à gauche, contrat de
// rg::carrefours) : amorce de B (bord gauche réel, partie 0), congé de sortie Rs de B, bord extérieur de l'anneau (cercle
// R0, sens horaire), congé d'entrée Re de A (partie 1), amorce de A (bord droit réel, partie 2) ; frontière fermée.
float fl = chf("../fleche");
float pasmax = radians(chf("../pas_angulaire_max"));
addpointattrib(0, "u", 0.0); addpointattrib(0, "partie", 0);
string ps_[] = {"coin", "branche_a", "branche_b", "route_a", "route_b", "carrefour", "bordure", "mat_ext", "ref_ext",
                "type_ext", "segment"};
foreach (string a; ps_) addprimattrib(0, a, "");
string pf_[] = {"rayon", "rayon_b", "rayon_anneau", "w_a", "w_b", "vue", "g_a", "g_b", "s_cut_a", "s_cut_b", "longueur",
                "angle_deg", "u_Kb", "u_Ka", "u_Tb", "u_Ta"};
foreach (string a; pf_) addprimattrib(0, a, 0.0);
addprimattrib(0, "droit", 0); addprimattrib(0, "rayon_defaut", 0); addprimattrib(0, "tangente_hors", 0);
addprimattrib(0, "giratoire", 0);
addprimattrib(0, "centre_arc", {0, 0, 0}); addprimattrib(0, "centre_arc_b", {0, 0, 0}); addprimattrib(0, "centre_anneau", {0, 0, 0});
addprimattrib(0, "n_a", {0, 0, 0}); addprimattrib(0, "n_b", {0, 0, 0});
foreach (int g; expandpointgroup(0, "giratoire")) {
    string cid = point(0, "id", g);
    vector o3 = point(0, "centre", g);
    vector2 O = set(o3.x, o3.y);
    float R0 = point(0, "R0", g);
    int bp[], rg_[];
    foreach (int p; expandpointgroup(0, "branche")) if (point(0, "carrefour", p) == cid) { push(bp, p); push(rg_, int(point(0, "rang", p))); }
    int ord[] = argsort(rg_);
    int sb[];
    foreach (int o; ord) push(sb, bp[o]);
    int nbk = len(sb);
    if (nbk < 2) continue;
    vector2 FR[];
    int FT[];
    for (int k = 0; k < nbk; k++) {
        int pa = sb[k], pb = sb[(k + 1) % nbk];
        string ra_ = point(0, "route", pa), rb_ = point(0, "route", pb);
        int pra = rc_prim_route(1, ra_), prb = rc_prim_route(1, rb_);
        float sea = point(0, "s_end", pa), seb = point(0, "s_end", pb);
        float stan_a = point(0, "s_tan_d", pa), stan_b = point(0, "s_tan_g", pb);
        float scut_a = point(0, "s_cut_d", pa), scut_b = point(0, "s_cut_g", pb);
        vector t3a = point(0, "T_d", pa), c3a = point(0, "C_d", pa), k3a = point(0, "K_d", pa);
        vector t3b = point(0, "T_g", pb), c3b = point(0, "C_g", pb), k3b = point(0, "K_g", pb);
        vector2 Ta = set(t3a.x, t3a.y), Ca = set(c3a.x, c3a.y), Ka = set(k3a.x, k3a.y);
        vector2 Tb = set(t3b.x, t3b.y), Cb = set(c3b.x, c3b.y), Kb = set(k3b.x, k3b.y);
        vector2 Q[];
        int PART[];
        float sbb[] = rc_abscisses_bord(1, prb, scut_b, stan_b, 0.5);
        for (int i = 0; i < len(sbb) - 1; i++) { push(Q, rc_bord(1, prb, 2, sbb[i], 1)); push(PART, 0); }
        int iTb = len(Q);
        push(Q, Tb); push(PART, 1);
        foreach (vector2 v; rgi_arc(Cb, Tb, Kb, 0, fl, pasmax)) { push(Q, v); push(PART, 1); }
        int iKb = len(Q);
        push(Q, Kb); push(PART, 1);
        vector2 arcA[] = rgi_arc(O, Kb, Ka, -1, fl, pasmax);
        foreach (vector2 v; arcA) { push(Q, v); push(PART, 1); }
        int iKa = len(Q);
        push(Q, Ka); push(PART, 1);
        foreach (vector2 v; rgi_arc(Ca, Ka, Ta, 0, fl, pasmax)) { push(Q, v); push(PART, 1); }
        int iTa = len(Q);
        push(Q, Ta); push(PART, 1);
        float saa[] = rc_abscisses_bord(1, pra, scut_a, stan_a, 0.5);
        for (int i = len(saa) - 2; i >= 0; i--) { push(Q, rc_bord(1, pra, 2, saa[i], 0)); push(PART, 2); }
        vector2 BA[], BB[];
        if (stan_a < sea - 1e-6) {
            float s1[] = rc_abscisses_bord(1, pra, stan_a, sea, 0.5);
            for (int i = len(s1) - 1; i >= 0; i--) push(BA, rc_bord(1, pra, 2, s1[i], 0));
        }
        if (stan_b < seb - 1e-6) {
            float s2[] = rc_abscisses_bord(1, prb, stan_b, seb, 0.5);
            foreach (float x; s2) push(BB, rc_bord(1, prb, 2, x, 1));
        }
        int qq[];
        float acc = 0.0;
        float U[];
        for (int i = 0; i < len(Q); i++) {
            if (i > 0) acc += length(Q[i] - Q[i - 1]);
            int q = addpoint(0, rc_h(Q[i], 0.0));
            setpointattrib(0, "u", q, acc);
            setpointattrib(0, "partie", q, PART[i]);
            push(qq, q);
            push(U, acc);
        }
        int pl = addprim(0, "polyline", qq);
        setprimgroup(0, "coin", pl, 1);
        string coin = sprintf("%s.c%d", cid, k);
        setprimattrib(0, "coin", pl, coin);
        setprimattrib(0, "carrefour", pl, cid);
        setprimattrib(0, "giratoire", pl, 1);
        setprimattrib(0, "branche_a", pl, string(point(0, "branche", pa)));
        setprimattrib(0, "branche_b", pl, string(point(0, "branche", pb)));
        setprimattrib(0, "route_a", pl, ra_);
        setprimattrib(0, "route_b", pl, rb_);
        setprimattrib(0, "rayon", pl, float(point(0, "Rf_d", pa)));
        setprimattrib(0, "rayon_b", pl, float(point(0, "Rf_g", pb)));
        setprimattrib(0, "rayon_anneau", pl, R0);
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
        setprimattrib(0, "centre_arc", pl, set(Ca.x, Ca.y, 0));
        setprimattrib(0, "centre_arc_b", pl, set(Cb.x, Cb.y, 0));
        setprimattrib(0, "centre_anneau", pl, set(O.x, O.y, 0));
        setprimattrib(0, "u_Tb", pl, U[iTb]); setprimattrib(0, "u_Kb", pl, U[iKb]);
        setprimattrib(0, "u_Ka", pl, U[iKa]); setprimattrib(0, "u_Ta", pl, U[iTa]);
        vector2 v0 = Kb - O, v1 = Ka - O;
        float ang = atan2(rc_croix(v0, v1), dot(v0, v1));
        if (ang > 0) ang -= 2.0 * PI;
        setprimattrib(0, "angle_deg", pl, degrees(ang));
        vector BAv[], BBv[];
        foreach (vector2 v; BA) push(BAv, set(v.x, v.y, 0));
        foreach (vector2 v; BB) push(BBv, set(v.x, v.y, 0));
        setprimattrib(0, "bord_a", pl, BAv);
        setprimattrib(0, "bord_b", pl, BBv);
        vector na3 = point(0, "nrm", pa), nb3 = point(0, "nrm", pb);
        setprimattrib(0, "n_a", pl, set(-na3.x, -na3.y, 0));
        setprimattrib(0, "n_b", pl, set(nb3.x, nb3.y, 0));
        setpointattrib(0, "coin_d", pa, coin);
        setpointattrib(0, "coin_g", pb, coin);
        // frontière : embouchure de A, bord droit de A jusqu'à Ta, congés et anneau (de A vers B), bord gauche de B
        push(FR, rc_bord(1, pra, 2, sea, 1)); push(FT, 0);
        push(FR, rc_bord(1, pra, 2, sea, 0)); push(FT, 1);
        foreach (vector2 v; BA) { push(FR, v); push(FT, 1); }
        for (int i = len(Q) - 1; i >= 0; i--) if (PART[i] == 1) { push(FR, Q[i]); push(FT, 1); }
        foreach (vector2 v; BB) { push(FR, v); push(FT, 1); }
        push(FR, rc_bord(1, prb, 2, seb, 1)); push(FT, 0);
    }
    if (len(FR) > 2) {
        int fq[];
        vector2 prec = set(1e18, 1e18);
        foreach (int i; vector2 v; FR) {
            if (length(v - prec) < 1e-7) continue;
            int q = addpoint(0, rc_h(v, 0.0));
            setpointattrib(0, "partie", q, FT[i]);
            push(fq, q);
            prec = v;
        }
        int pf = addprim(0, "poly", fq);
        setprimgroup(0, "frontiere", pf, 1);
        setprimattrib(0, "carrefour", pf, cid);
    }
}
"""

VEX_SANS_ANNEAUX = r"""
// routes d'anneau retirées (primitive ; entrée 1 : lecture) : l'anneau est fabriqué par rg::carrefours_sol (chaussée
// annulaire dans le cœur du giratoire) et rg::giratoires_sol (îlot central, couronne).
string an[] = detail(1, "rg_anneaux");
if (find(an, s@id) >= 0) removeprim(0, @primnum, 1);
"""

VEX_SOLVEUR_PLAN = r"""
// îlots des giratoires retirés du SOLVEUR des carrefours plans (primitive ; entrée 1 : lecture) : rg::carrefours lit tous
// les îlots du modèle ; ceux d'un giratoire sont posés par rg::giratoires_sol.
if (!inprimgroup(0, "ilot", @primnum)) return;
string ids[] = detail(1, "rg_giratoires_ids");
if (find(ids, s@carrefour) >= 0) removeprim(0, @primnum, 1);
"""
