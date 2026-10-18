"""Code VEX de l'HDA rg::giratoires_sol (îlots posés des giratoires : couronne franchissable, îlot central, dôme du
mini-giratoire, îlots séparateurs ; bordures, dessus, BEV, marques de l'anneau). Lot L5 giratoires.

Importé par construire.py. Entrées des wrangles : 0 géométrie en cours ; GIRATOIRES (rg::giratoires, sortie 4) ; sol
sans îlots (sol des branches + sol du cœur, rg::sol et rg::carrefours_sol) ; faces de bordure.
"""

FONCTIONS_FACES = r"""
// abaissés d'une file de face Q (abscisses U) : intersections avec les bandes de passage (axe ± largeur / 2, étendue de
// l'axe ± marge), vue DEF-031, rampants réduits aux bouts de la file (≥ rampant minimal sinon signalé) ; même loi que
// rg::carrefours_sol (domaine).
function void rgi_abaisses(vector2 Q[]; float U[]; vector2 PA0[]; vector2 PA1[]; float PW[]; string PID[];
                           float va; float ra; float ramin; float mpp; string ref;
                           export float A0[]; export float A1[]; export float AV[]; export float AR[];
                           export string AP[]; export string avert[])
{
    float Lt = U[-1];
    for (int k = 0; k < len(PA0); k++) {
        vector2 ax = PA1[k] - PA0[k];
        float la = length(ax);
        if (la < 1e-6) continue;
        vector2 cdir = ax / la, rdir = rc_gauche(cdir);
        float hw = 0.5 * PW[k];
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

// face (polyligne fermée, sens trigonométrique, îlot à gauche) : points u ; renvoie la primitive (groupe face)
function int rgi_face(vector2 Q[]; string kind; string ref; string cid)
{
    float U[] = rc_cumul(Q);
    int fq[];
    foreach (int i; vector2 v; Q) { int p = addpoint(0, rc_h(v, 0.0)); setpointattrib(0, "u", p, U[i]); push(fq, p); }
    int pf = addprim(0, "polyline", fq);
    setprimgroup(0, "face", pf, 1);
    setprimattrib(0, "kind", pf, kind);
    setprimattrib(0, "ref", pf, ref);
    setprimattrib(0, "carrefour", pf, cid);
    setprimattrib(0, "longueur", pf, U[-1]);
    return pf;
}
"""

VEX_FACES = r"""
// faces de bordure des îlots posés (détail ; entrée 1 : GIRATOIRES, 2 : sol sans îlots) :
//   couronne franchissable (bande « terre_plein » du profil de l'anneau, contre la chaussée annulaire : cercle de rayon
//   Rg − la, bordure et vue de la limite du profil, RF-GV-GIR-006) ;
//   îlot central (cercle de rayon Ri_infranchissable de l'anneau du modèle ; ceinture du modèle ; pied sur la couronne)
//   ou dôme franchissable du mini-giratoire (pas de bordure, RF-GV-GIR-016) ;
//   îlots séparateurs (polygones du modèle, ceinture du modèle, abaissés des passages : refuge, DEF-031).
float fl = chf("../fleche");
float pasmax = radians(chf("../pas_angulaire_max"));
float rh = chf("../recouvrement_tete");
float va = chf("../abaisse_vue"), ra = chf("../abaisse_rampant"), ramin = chf("../abaisse_rampant_min");
float mpp = chf("../passage_marge");
float base_def = chf("../base_defaut");
float aire_min = chf("../aire_min_ilot");
float pente_c = chf("../couronne_pente_pct") / 100.0;
float a0 = radians(chf("../angle_depart"));
string bases_tab[] = split(chs("../table_bases"), ",");
string ps_[] = {"kind", "ref", "carrefour", "bordure", "materiau_bordure", "materiau_top", "type_ilot", "sous", "contour"};
foreach (string a; ps_) addprimattrib(0, a, "");
string pf_[] = {"vue", "vue_nominale", "base", "retrait", "longueur", "rayon", "pente", "w_bev", "dome_h", "dome_relief",
                "a0", "r_dessus_ext", "r_dessus_int", "u_m"};
foreach (string a; pf_) addprimattrib(0, a, 0.0);
addprimattrib(0, "centre", {0, 0, 0});
addpointattrib(0, "u", 0.0);
string avert[];
// passages (modèle)
vector2 PA0[], PA1[];
float PW[];
string PID[];
foreach (int p; expandpointgroup(1, "passage")) {
    vector a = point(1, "axe0", p), b = point(1, "axe1", p);
    push(PA0, set(a.x, a.y)); push(PA1, set(b.x, b.y)); push(PW, float(point(1, "largeur", p))); push(PID, string(point(1, "id", p)));
}
foreach (int g; expandpointgroup(1, "giratoire")) {
    string cid = point(1, "id", g);
    vector o3 = point(1, "centre", g);
    vector2 O = set(o3.x, o3.y);
    float Ri_inf = point(1, "Ri_inf", g), Ri = point(1, "Ri", g);
    string aty[] = point(1, "a_type", g), afr[] = point(1, "a_franch", g), amat[] = point(1, "a_mat", g);
    float rl[] = point(1, "r_lim", g), lvue[] = point(1, "l_vue", g);
    string lbord[] = point(1, "l_bord", g);
    int b0 = point(1, "b0", g);
    string cent = point(1, "ilot_central", g);
    float um = point(1, "u_m", g);
    // ---------------------------------------------------------------- couronne franchissable
    int a_cour = b0 > 0 && aty[b0 - 1] == "terre_plein" && lbord[b0] != "";
    float Uc[], PZc[];
    float rc_ = 0, vue_c = 0, base_c = 0, rback_c = 0;
    int pf_cour = -1;
    if (a_cour) {
        rc_ = rl[b0];
        vector2 Q[] = rgi_cercle(O, rc_, a0, fl, pasmax);
        int pf = rgi_face(Q, "couronne", cid + ".couronne", cid);
        pf_cour = pf;
        string bord = lbord[b0];
        vue_c = lvue[b0];
        base_c = rgi_base(bases_tab, bord, base_def);
        rback_c = rc_ - (base_c - rh);
        setprimattrib(0, "bordure", pf, bord);
        setprimattrib(0, "vue", pf, vue_c); setprimattrib(0, "vue_nominale", pf, vue_c);
        setprimattrib(0, "base", pf, base_c);
        setprimattrib(0, "materiau_top", pf, amat[b0 - 1]);
        setprimattrib(0, "retrait", pf, RG_RETRAIT_TROTTOIR);
        setprimattrib(0, "pente", pf, pente_c);
        setprimattrib(0, "rayon", pf, rc_);
        setprimattrib(0, "a0", pf, a0);
        setprimattrib(0, "centre", pf, set(O.x, O.y, 0));
        setprimattrib(0, "sous", pf, "sol");
        setprimattrib(0, "type_ilot", pf, "couronne_franchissable");
        setprimattrib(0, "r_dessus_ext", pf, rback_c);
        Uc = rc_cumul(Q);
        foreach (vector2 v; Q) { int ok; push(PZc, rgi_z_sol(2, v, ok)); }
        setprimattrib(0, "pied_z", pf, PZc);
        float vide[]; string svide[];
        setprimattrib(0, "ab0", pf, vide); setprimattrib(0, "ab1", pf, vide); setprimattrib(0, "abv", pf, vide);
        setprimattrib(0, "abr", pf, vide); setprimattrib(0, "ab_passage", pf, svide);
    }
    // ---------------------------------------------------------------- îlot central
    int ic = -1;
    foreach (int q; expandprimgroup(1, "ilot_g")) if (prim(1, "id", q) == cent) ic = q;
    if (ic >= 0) {
        string fr = prim(1, "franchissable", ic);
        float bomb = prim(1, "bombement", ic), sur = prim(1, "surelevation", ic);
        // rayon du polygone du modèle (contrôle) : moyenne des distances au centre
        float rm = 0;
        int ipts[] = primpoints(1, ic);
        foreach (int v; ipts) rm += length(rc_xy(point(1, "P", v)) - O);
        rm /= max(1, len(ipts));
        if ((fr == "" || fr == "non") && bomb <= 0) {
            float R = Ri_inf > 0 ? Ri_inf : rm;
            if (abs(R - rm) > 0.05) push(avert, sprintf("%s : rayon de l'îlot central %.3f m (anneau) ; polygone du modèle %.3f m", cid, R, rm));
            vector2 Q[] = rgi_cercle(O, R, a0, fl, pasmax);
            int pf = rgi_face(Q, "central", cent, cid);
            string bord = prim(1, "ceinture", ic);
            if (bord == "") bord = chs("../bordure_ilot_defaut");
            float vue = prim(1, "ceinture_vue", ic);
            if (vue <= 0) vue = sur;
            float base = rgi_base(bases_tab, bord, base_def);
            string mt = prim(1, "materiau", ic);
            if (mt == "") mt = "gazon_tondu";
            setprimattrib(0, "bordure", pf, bord);
            setprimattrib(0, "vue", pf, vue); setprimattrib(0, "vue_nominale", pf, vue);
            setprimattrib(0, "base", pf, base);
            setprimattrib(0, "materiau_top", pf, mt);
            setprimattrib(0, "retrait", pf, (find(mt, "gazon") >= 0 || find(mt, "terre") >= 0) ? RG_RETRAIT_PLANTE : RG_RETRAIT_TROTTOIR);
            setprimattrib(0, "rayon", pf, R);
            setprimattrib(0, "a0", pf, a0);
            setprimattrib(0, "centre", pf, set(O.x, O.y, 0));
            setprimattrib(0, "type_ilot", pf, "central_infranchissable");
            setprimattrib(0, "sous", pf, a_cour ? "couronne" : "sol");
            setprimattrib(0, "r_dessus_ext", pf, R - (base - rh));
            float PZ[];
            float U[] = rc_cumul(Q);
            foreach (int i; vector2 v; Q) {
                if (a_cour) {
                    // pied sur la couronne : tête de la couronne − 4 mm à l'arrière de sa bordure, puis pente vers le centre
                    float uc = U[i] * rc_ / R;
                    float pc = rc_interp(Uc, PZc, uc);
                    push(PZ, pc + vue_c - RG_RETRAIT_TROTTOIR + pente_c * (rback_c - R));
                } else { int ok; push(PZ, rgi_z_sol(2, v, ok)); }
            }
            setprimattrib(0, "pied_z", pf, PZ);
            float vide[]; string svide[];
            setprimattrib(0, "ab0", pf, vide); setprimattrib(0, "ab1", pf, vide); setprimattrib(0, "abv", pf, vide);
            setprimattrib(0, "abr", pf, vide); setprimattrib(0, "ab_passage", pf, svide);
            // la couronne s'arrête sous la bordure de l'îlot central (arrière − 12 mm, TQ-BOR-007)
            if (pf_cour >= 0) setprimattrib(0, "r_dessus_int", pf_cour, R - (base - rh));
        } else {
            // dôme franchissable (mini-giratoire, RF-GV-GIR-016 : dôme 10-15 cm, relief dissuasif 1-3 cm)
            float R = Ri > 0 ? Ri : rm;
            vector2 Q[] = rgi_cercle(O, R, a0, fl, pasmax);
            int pf = rgi_face(Q, "dome", cent, cid);
            string mt = prim(1, "materiau", ic);
            if (mt == "") mt = "beton_balaye";
            setprimattrib(0, "materiau_top", pf, mt);
            setprimattrib(0, "dome_h", pf, bomb > 0 ? bomb : sur);
            setprimattrib(0, "dome_relief", pf, chf("../dome_relief"));
            setprimattrib(0, "rayon", pf, R);
            setprimattrib(0, "a0", pf, a0);
            setprimattrib(0, "centre", pf, set(O.x, O.y, 0));
            setprimattrib(0, "type_ilot", pf, "central_franchissable");
            setprimattrib(0, "sous", pf, "sol");
            setprimattrib(0, "contour", pf, string(prim(1, "contour", ic)));
            setprimattrib(0, "u_m", pf, um);
            float PZ[];
            foreach (vector2 v; Q) { int ok; push(PZ, rgi_z_sol(2, v, ok)); }
            setprimattrib(0, "pied_z", pf, PZ);
            if (abs(R - rm) > 0.05) push(avert, sprintf("%s : rayon du dôme %.3f m (anneau) ; polygone du modèle %.3f m", cid, R, rm));
        }
    }
    // ---------------------------------------------------------------- îlots séparateurs
    foreach (int q; expandprimgroup(1, "ilot_g")) {
        if (prim(1, "carrefour", q) != cid || prim(1, "id", q) == cent) continue;
        string iid = prim(1, "id", q);
        int qp[] = primpoints(1, q);
        vector2 Q[];
        foreach (int p; qp) push(Q, rc_xy(point(1, "P", p)));
        float aire = 0;
        for (int i = 0; i < len(Q); i++) aire += rc_croix(Q[i], Q[(i + 1) % len(Q)]);
        aire *= 0.5;
        if (abs(aire) < aire_min) {
            push(avert, sprintf("%s : îlot du modèle dégénéré (%.3f m² < %.2f m²) : non fabriqué (l'enveloppe peinte du profil reste)", iid, abs(aire), aire_min));
            continue;
        }
        if (aire < 0) Q = reverse(Q);
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
        int pf = rgi_face(R, "ilot", iid, cid);
        string bord = prim(1, "ceinture", q);
        if (bord == "") bord = chs("../bordure_ilot_defaut");
        float vue = prim(1, "ceinture_vue", q);
        if (vue <= 0) vue = prim(1, "surelevation", q);
        float base = rgi_base(bases_tab, bord, base_def);
        string mt = prim(1, "materiau", q);
        if (mt == "") mt = "beton_balaye";
        setprimattrib(0, "bordure", pf, bord);
        setprimattrib(0, "vue", pf, vue); setprimattrib(0, "vue_nominale", pf, vue);
        setprimattrib(0, "base", pf, base);
        setprimattrib(0, "materiau_top", pf, mt);
        setprimattrib(0, "retrait", pf, (find(mt, "gazon") >= 0 || find(mt, "terre") >= 0) ? RG_RETRAIT_PLANTE : RG_RETRAIT_TROTTOIR);
        setprimattrib(0, "type_ilot", pf, string(prim(1, "type", q)));
        setprimattrib(0, "sous", pf, "sol");
        setprimattrib(0, "contour", pf, string(prim(1, "contour", q)));
        float rl_ = prim(1, "refuge_largeur", q);
        setprimattrib(0, "w_bev", pf, rl_ > 0 ? 0.5 * rl_ : 0.0);
        float U[] = rc_cumul(R);
        float A0[], A1[], AV[], AR[];
        string AP[];
        rgi_abaisses(R, U, PA0, PA1, PW, PID, va, ra, ramin, mpp, iid, A0, A1, AV, AR, AP, avert);
        setprimattrib(0, "ab0", pf, A0); setprimattrib(0, "ab1", pf, A1); setprimattrib(0, "abv", pf, AV);
        setprimattrib(0, "abr", pf, AR); setprimattrib(0, "ab_passage", pf, AP);
        float PZ[];
        foreach (vector2 v; R) { int ok; push(PZ, rgi_z_sol(2, v, ok)); }
        setprimattrib(0, "pied_z", pf, PZ);
    }
}
s[]@rg_giratoires_sol_avertissements = avert;
"""

VEX_DESSUS_POLAIRES = r"""
// dessus des îlots circulaires (détail ; entrée 1 : faces, 2 : sol sans îlots) : maillages polaires (anneaux ≤ pas
// radial, mêmes angles que la face) ; couronne : tête − 4 mm à l'arrière de la bordure (TQ-SOL-013 (5)) puis pente vers
// le centre (RF-GV-GIR-006 : 4-6 %), jusque sous la bordure de l'îlot central ; îlot central : tête − retrait (− 4 cm
// planté, TQ-SOL-013 (7)) ; dôme : z = sol + relief + (h − relief)(1 − (ρ/R)²) [G], relief dissuasif au bord ; jupes
// (murs) du bord des dessus jusqu'à 5 cm sous le sol (cachées sous les bordures ; visible au bord du dôme : relief).
float pas_r = chf("../pas_radial");
addprimattrib(0, "zone", ""); addprimattrib(0, "ref", ""); addprimattrib(0, "carrefour", "");
addprimattrib(0, "materiau_top", ""); addprimattrib(0, "haut", 0); addprimattrib(0, "visible", 1);
addprimattrib(0, "mur_dir", {0, 0, 0});
foreach (int f; expandprimgroup(1, "face")) {
    string kind = prim(1, "kind", f);
    if (kind != "couronne" && kind != "central" && kind != "dome") continue;
    int fp[] = primpoints(1, f);
    int n = len(fp) - 1;                                    // face fermée : dernier point = premier
    vector c3 = prim(1, "centre", f);
    vector2 O = set(c3.x, c3.y);
    float R = prim(1, "rayon", f), a0 = prim(1, "a0", f);
    float PZ[] = prim(1, "pied_z", f);
    float vue = prim(1, "vue", f), ret = prim(1, "retrait", f), pente = prim(1, "pente", f);
    float r_ext = kind == "dome" ? R : float(prim(1, "r_dessus_ext", f));
    float r_int = kind == "couronne" ? float(prim(1, "r_dessus_int", f)) : 0.0;
    if (kind == "couronne" && r_int <= 0) r_int = r_ext - 1.0;
    float h = prim(1, "dome_h", f), rel = prim(1, "dome_relief", f);
    string ref = prim(1, "ref", f), cid = prim(1, "carrefour", f), mt = prim(1, "materiau_top", f);
    int nr = max(1, int(ceil((r_ext - r_int) / pas_r - 1e-9)));
    int grille[];
    vector GP[];
    for (int j = 0; j <= nr; j++) {
        float rho = r_ext - (r_ext - r_int) * j / nr;
        if (rho < 1e-6) {                                   // centre : un seul point (Z moyen de l'anneau précédent)
            float zm = 0;
            for (int i = 0; i < n; i++) zm += GP[(j - 1) * n + i].y;
            vector Pc = set(O.x, zm / n, -O.y);
            if (kind == "dome") { int ok; float zs = rgi_z_sol(2, O, ok); Pc.y = zs + h; }
            int pc = addpoint(0, Pc);
            for (int i = 0; i < n; i++) { push(grille, pc); push(GP, Pc); }
            break;
        }
        for (int i = 0; i < n; i++) {
            float t = a0 + 2.0 * PI * i / n;
            vector2 q = O + rho * set(cos(t), sin(t));
            float z;
            if (kind == "couronne") z = PZ[i] + vue - ret + pente * (r_ext - rho);
            else if (kind == "central") z = PZ[i] + vue - ret;
            else { int ok; float zs = rgi_z_sol(2, q, ok); z = zs + rel + (h - rel) * (1.0 - (rho / R) * (rho / R)); }
            vector P = rc_h(q, z);
            push(grille, addpoint(0, P));
            push(GP, P);
        }
    }
    int nrow = len(grille) / n;
    for (int j = 0; j + 1 < nrow; j++) {
        for (int i = 0; i < n; i++) {
            int a = grille[j * n + i], b = grille[j * n + (i + 1) % n], c = grille[(j + 1) * n + (i + 1) % n], d = grille[(j + 1) * n + i];
            int pr;
            if (c == d) pr = addprim(0, "poly", array(a, b, c));
            else pr = addprim(0, "poly", array(a, b, c, d));
            setprimattrib(0, "zone", pr, "ilot"); setprimattrib(0, "ref", pr, ref); setprimattrib(0, "carrefour", pr, cid);
            setprimattrib(0, "materiau_top", pr, mt); setprimattrib(0, "haut", pr, 1);
        }
    }
    // jupes : bord extérieur (et bord intérieur de la couronne) jusqu'à 5 cm sous le sol ; dôme : relief visible
    int rangs[] = array(0);
    if (kind == "couronne") push(rangs, nrow - 1);
    foreach (int j; rangs) {
        int bas[];
        for (int i = 0; i < n; i++) {
            vector P = GP[j * n + i];
            int ok;
            float zs = rgi_z_sol(2, set(P.x, -P.z), ok);
            push(bas, addpoint(0, set(P.x, (kind == "dome" ? zs - 0.02 : zs - 0.05), P.z)));
        }
        for (int i = 0; i < n; i++) {
            int a = grille[j * n + i], b = grille[j * n + (i + 1) % n];
            int pr = addprim(0, "poly", array(a, b, bas[(i + 1) % n], bas[i]));
            int vis = kind == "dome";
            setprimattrib(0, "zone", pr, vis ? "ilot" : "mur"); setprimattrib(0, "ref", pr, ref);
            setprimattrib(0, "carrefour", pr, cid); setprimattrib(0, "materiau_top", pr, vis ? mt : "sol_cache");
            setprimattrib(0, "haut", pr, vis ? 1 : -1); setprimattrib(0, "visible", pr, vis);
            vector A = GP[j * n + i], B = GP[j * n + (i + 1) % n];
            vector2 tng = normalize(set(B.x - A.x, -(B.z - A.z)));
            vector2 dehors = j == 0 ? -rc_gauche(tng) : rc_gauche(tng);
            setprimattrib(0, "mur_dir", pr, set(dehors.x, 0, -dehors.y));
        }
    }
}
"""

VEX_CONTOURS_SEP = r"""
// contours des dessus des îlots séparateurs (détail ; entrée 1 : faces) : face décalée vers l'îlot de base − 12 mm
// (le dessus passe sous la tête de la bordure, TQ-BOR-007) ; polygones plans (groupe contour_dessus) à trianguler.
float rh = chf("../recouvrement_tete");
addprimattrib(0, "ref", "");
foreach (int f; expandprimgroup(1, "face")) {
    if (prim(1, "kind", f) != "ilot") continue;
    int fp[] = primpoints(1, f);
    vector2 Q[];
    foreach (int p; fp) push(Q, rc_xy(point(1, "P", p)));
    float W[];
    float base = prim(1, "base", f);
    foreach (vector2 v; Q) push(W, base - rh);
    vector2 B[] = rc_decaler(Q, W);
    removeindex(B, len(B) - 1);
    int qq[];
    foreach (vector2 v; B) push(qq, addpoint(0, rc_h(v, 0.0)));
    int pr = addprim(0, "poly", qq);
    setprimgroup(0, "contour_dessus", pr, 1);
    setprimattrib(0, "ref", pr, string(prim(1, "ref", f)));
}
"""

VEX_DESSUS_SEP = r"""
// dessus des îlots séparateurs (détail ; entrée 0 : triangulation, 1 : faces, 2 : sol sans îlots) : Z = tête − retrait
// de la bordure la plus proche (abaissés compris : le refuge est abaissé au droit du passage, DEF-031) ; jupes du bord
// jusqu'à 5 cm sous le sol (cachées sous la bordure).
addprimattrib(0, "zone", ""); addprimattrib(0, "ref", ""); addprimattrib(0, "carrefour", "");
addprimattrib(0, "materiau_top", ""); addprimattrib(0, "haut", 0); addprimattrib(0, "visible", 1);
addprimattrib(0, "mur_dir", {0, 0, 0});
int faces[];
foreach (int f; expandprimgroup(1, "face")) if (prim(1, "kind", f) == "ilot") push(faces, f);
int np = npoints(0);
string refpt[];
resize(refpt, np);
for (int p = 0; p < np; p++) {
    vector P = point(0, "P", p);
    vector2 x = set(P.x, -P.z);
    float best = 1e18, z = 0;
    string rb = "";
    foreach (int f; faces) {
        int fp[] = primpoints(1, f);
        vector2 Q[];
        foreach (int v; fp) push(Q, rc_xy(point(1, "P", v)));
        float sc, co;
        float d = rc_dist_poly(Q, x, sc, co);
        if (d < best) {
            best = d;
            float U[] = rc_cumul(Q);
            float PZ[] = prim(1, "pied_z", f);
            float A0[] = prim(1, "ab0", f), A1[] = prim(1, "ab1", f), AV[] = prim(1, "abv", f), AR[] = prim(1, "abr", f);
            z = rc_interp(U, PZ, sc) + rc_vue(prim(1, "vue", f), A0, A1, AV, AR, sc) - float(prim(1, "retrait", f));
            rb = prim(1, "ref", f);
        }
    }
    setpointattrib(0, "P", p, set(P.x, z, P.z));
    refpt[p] = rb;
}
int npr = nprimitives(0);
for (int pr = 0; pr < npr; pr++) {
    int pp[] = primpoints(0, pr);
    string rf = refpt[pp[0]];
    int f = -1;
    foreach (int g; faces) if (prim(1, "ref", g) == rf) f = g;
    setprimattrib(0, "zone", pr, "ilot"); setprimattrib(0, "ref", pr, rf); setprimattrib(0, "haut", pr, 1);
    setprimattrib(0, "carrefour", pr, f >= 0 ? string(prim(1, "carrefour", f)) : "");
    setprimattrib(0, "materiau_top", pr, f >= 0 ? string(prim(1, "materiau_top", f)) : "beton_balaye");
}
// arêtes de bord -> jupes (un point bas par point du bord, partagé par les deux jupes voisines)
int bas[];
resize(bas, np);
for (int p = 0; p < np; p++) bas[p] = -1;
for (int pr = 0; pr < npr; pr++) {
    int vs[] = primpoints(0, pr);
    int n = len(vs);
    for (int i = 0; i < n; i++) {
        int a = vs[i], b = vs[(i + 1) % n];
        int pa[] = pointprims(0, a), pb[] = pointprims(0, b);
        int comm = 0;
        foreach (int x; pa) if (x != pr && x < npr && find(pb, x) >= 0) comm = 1;
        if (comm) continue;
        vector A = point(0, "P", a), B = point(0, "P", b);
        int ok;
        if (bas[a] < 0) bas[a] = addpoint(0, set(A.x, rgi_z_sol(2, set(A.x, -A.z), ok) - 0.05, A.z));
        if (bas[b] < 0) bas[b] = addpoint(0, set(B.x, rgi_z_sol(2, set(B.x, -B.z), ok) - 0.05, B.z));
        int m = addprim(0, "poly", array(a, b, bas[b], bas[a]));
        setprimattrib(0, "zone", m, "mur"); setprimattrib(0, "haut", m, -1); setprimattrib(0, "visible", m, 0);
        setprimattrib(0, "ref", m, refpt[a]); setprimattrib(0, "carrefour", m, string(prim(0, "carrefour", pr)));
        setprimattrib(0, "materiau_top", m, "sol_cache");
        vector2 tng = normalize(set(B.x - A.x, -(B.z - A.z)));
        vector2 dehors = -rc_gauche(tng);
        setprimattrib(0, "mur_dir", m, set(dehors.x, 0, -dehors.y));
    }
}
"""

VEX_ORIENTER = r"""
// faces vers +Y ; murs vers l'extérieur (mur_dir)
vector n = prim_normal(0, @primnum, {0.333, 0.333, 0});
if (s@zone == "mur" || (i@haut == 1 && abs(n.y) < 0.3 && length(v@mur_dir) > 0)) { if (dot(n, v@mur_dir) < 0) i@group_a_inverser = 1; }
else if (n.y < 0) i@group_a_inverser = 1;
"""

VEX_FINIR = r"""
// contrat de rg::sol (materiau_id, classe, z_type, visible, route, section, bande, bande_id, pj_couche, pj_entite,
// pj_maillage, priorite, chaine)
string z = s@zone;
string mat = s@materiau_top;
if (mat == "") mat = "beton_balaye";
if (z == "mur" && i@visible == 0) mat = "sol_cache";
s@materiau_id = mat;
s@classe = z == "mur" ? "mur" : "giratoire_" + z;
i@z_type = z == "mur" ? 14 : 10;
s@route = s@carrefour;
i@section = -1;
i@bande = -1;
s@bande_id = z;
s@pj_couche = "PJ_Sol";
s@pj_entite = "SOL_" + re_replace("[^A-Za-z0-9]", "_", s@carrefour) + "_" + re_replace("[^A-Za-z0-9]", "_", s@ref);
s@pj_maillage = mat;
i@priorite = 0;
i@chaine = -1;
"""

VEX_MARQUES = r"""
// marques des giratoires (détail ; entrée 1 : GIRATOIRES, 2 : faces) au contrat de pj::marquage_solide :
//   contour de l'îlot central franchissable du mini-giratoire (marquage_contour du modèle : T'2 3u, RF-MQ-GIR-02),
//   autour du dôme, motif fermé [G] ;
//   lignes de l'anneau (limites du profil de l'anneau qui portent un marquage : rive T2 3u des giratoires
//   interurbains, RF-OSM-MRQ-021, RF-MQ-GIR-04) : sur la chaussée (rive intérieure décalée d'une demi-largeur vers
//   l'anneau, rive extérieure vers l'intérieur [G]), interrompues au droit des bouches (entre les points de tangence
//   des congés sur le cercle R0) ; motif depuis la fin de chaque bouche [G].
string mat = chs("../materiau_peinture");
float us = chf("../usure_peinture");
float fl = chf("../fleche");
float pasmax = radians(chf("../pas_angulaire_max"));
string tabmod[] = split(chs("../modulations"), ",");
string attrs_s[] = {"pj_entite", "id", "classe", "type", "gabarit", "materiau_id", "couleur", "route", "cle", "modulation"};
foreach (string a; attrs_s) addprimattrib(0, a, "");
addprimattrib(0, "usure", 0.0); addprimattrib(0, "couverture", 1.0); addprimattrib(0, "graine", 0);
addprimattrib(0, "partie", 0); addprimattrib(0, "anneau", 0); addprimattrib(0, "pj_region", -1);
addprimattrib(0, "largeur_m", 0.0); addprimattrib(0, "s0", 0.0); addprimattrib(0, "s1", 0.0);
addprimattrib(0, "rang", 0); addprimattrib(0, "bande_sol", -1); addprimattrib(0, "rg_ligne", 0);
addprimattrib(0, "rayon_m", 0.0);
string avert[];
// lignes à poser : (centre, rayon, largeur, modulation, intervalles angulaires [a, b] trigonométriques, fermée)
foreach (int g; expandpointgroup(1, "giratoire")) {
    string cid = point(1, "id", g);
    vector o3 = point(1, "centre", g);
    vector2 O = set(o3.x, o3.y);
    float um = point(1, "u_m", g);
    float rl[] = point(1, "r_lim", g);
    string lmod[] = point(1, "l_mmod", g);
    float lmlu[] = point(1, "l_mlu", g), lmum[] = point(1, "l_mum", g);
    int b0 = point(1, "b0", g), b1 = point(1, "b1", g);
    // bouches : secteurs [K_g, K_d] (sens trigonométrique) de chaque branche
    float BG[], BD[];
    foreach (int p; expandpointgroup(1, "branche")) {
        if (point(1, "carrefour", p) != cid) continue;
        vector kg = point(1, "K_g", p), kd = point(1, "K_d", p);
        push(BG, atan2(kg.y - O.y, kg.x - O.x)); push(BD, atan2(kd.y - O.y, kd.x - O.x));
    }
    string LID[], LMOD[];
    float LR[], LW[];
    int LF[];
    float LA[], LB[];          // intervalles (aplatis)
    int LO[], LN[];
    // contour du dôme
    foreach (int f; expandprimgroup(2, "face")) {
        if (prim(2, "kind", f) != "dome" || prim(2, "carrefour", f) != cid) continue;
        string cj = prim(2, "contour", f);
        if (cj == "") continue;
        dict C = json_loads(cj, 0);
        string mod = isvalidindex(C, "modulation") ? string(C["modulation"]) : "aucune";
        if (mod == "aucune" || mod == "") continue;
        float wu = isvalidindex(C, "largeur_u") ? float(C["largeur_u"]) : 3.0;
        float ru = isvalidindex(C, "retrait_u") ? float(C["retrait_u"]) : 0.0;
        float w = wu * um;
        float R = prim(2, "rayon", f);
        push(LID, sprintf("M-%s.contour", re_replace("[^A-Za-z0-9.]", "_", string(prim(2, "ref", f)))));
        push(LMOD, mod); push(LR, R + ru * um + 0.5 * w); push(LW, w); push(LF, 1);
        float a0f = prim(2, "a0", f);
        push(LO, len(LA)); push(LN, 1); push(LA, a0f); push(LB, a0f + 2.0 * PI);
    }
    // lignes de l'anneau
    for (int k = 0; k < len(lmod); k++) {
        if (lmod[k] == "") continue;
        int imq = 0;
        {
            string mod = lmod[k];
            float wu = lmlu[k] > 0 ? lmlu[k] : 2.0;
            float u_ = lmum[k] > 0 ? lmum[k] : um;
            float w = wu * u_;
            float r = rl[k];
            if (k == b0) r += 0.5 * w;
            else if (k == b1 + 1) r -= 0.5 * w;
            push(LID, sprintf("M-%s.anneau.l%d.%d", cid, k, imq));
            push(LMOD, mod); push(LR, r); push(LW, w);
            if (k == b0) { push(LF, 1); push(LO, len(LA)); push(LN, 1); push(LA, -0.5 * PI); push(LB, 1.5 * PI); }
            else {
                // complément des bouches : de K_d d'une bouche à K_g de la suivante (sens trigonométrique)
                int nb = len(BG);
                int ord[] = argsort(BD);
                push(LF, 0); push(LO, len(LA)); push(LN, nb);
                for (int j = 0; j < nb; j++) {
                    float a = BD[ord[j]];
                    float b = BG[ord[(j + 1) % nb]];
                    while (b <= a) b += 2.0 * PI;
                    push(LA, a); push(LB, b);
                }
            }
            imq++;
        }
    }
    // pose
    for (int l = 0; l < len(LID); l++) {
        float tr, iv;
        if (!rgi_modulation(tabmod, LMOD[l], tr, iv)) { push(avert, sprintf("%s : modulation %s inconnue", LID[l], LMOD[l])); continue; }
        float r = LR[l], w = LW[l];
        int rang = 0;
        for (int j = LO[l]; j < LO[l] + LN[l]; j++) {
            float a = LA[j], b = LB[j];
            float Lt = r * (b - a);
            float D0[], D1[];
            if (tr <= 0) { push(D0, 0.0); push(D1, Lt); }
            else if (LF[l]) {
                // motif fermé : période ajustée pour un nombre entier de traits sur le tour [G]
                int nt = max(1, int(rint(Lt / (tr + iv))));
                float per = Lt / nt;
                for (int k = 0; k < nt; k++) { push(D0, k * per); push(D1, k * per + tr); }
            } else {
                int nt = max(1, int(floor((Lt + iv) / (tr + iv) + 1e-9)));
                float tot = nt * tr + (nt - 1) * iv;
                float o = 0.5 * (Lt - tot);
                for (int k = 0; k < nt; k++) { push(D0, o + k * (tr + iv)); push(D1, o + k * (tr + iv) + tr); }
            }
            for (int k = 0; k < len(D0); k++) {
                float t0 = a + D0[k] / r, t1 = a + D1[k] / r;
                float pas = min(rgi_pas(r + 0.5 * w, fl, pasmax), radians(5.0));
                int ns = max(1, int(ceil((t1 - t0) / pas - 1e-9)));
                // découpe en pièces de 2 m au plus (drapé)
                int npiece = max(1, int(ceil((D1[k] - D0[k]) / 2.0 - 1e-9)));
                for (int pc = 0; pc < npiece; pc++) {
                    float ta = t0 + (t1 - t0) * pc / npiece, tb = t0 + (t1 - t0) * (pc + 1) / npiece;
                    int nsp = max(1, int(ceil(ns / float(npiece))));
                    int qq[];
                    for (int i = 0; i <= nsp; i++) { float t = ta + (tb - ta) * i / nsp; push(qq, addpoint(0, rc_h(O + (r - 0.5 * w) * set(cos(t), sin(t)), 0.0))); }
                    for (int i = nsp; i >= 0; i--) { float t = ta + (tb - ta) * i / nsp; push(qq, addpoint(0, rc_h(O + (r + 0.5 * w) * set(cos(t), sin(t)), 0.0))); }
                    int pr = addprim(0, "poly", qq);
                    string ent = sprintf("MQ_%s_t%03d", re_replace("[^A-Za-z0-9]", "_", LID[l]), rang);
                    setprimattrib(0, "pj_entite", pr, ent); setprimattrib(0, "id", pr, sprintf("%s_t%03d", LID[l], rang));
                    setprimattrib(0, "classe", pr, "ligne_giratoire"); setprimattrib(0, "type", pr, LF[l] ? "contour" : "rive");
                    setprimattrib(0, "gabarit", pr, LMOD[l]); setprimattrib(0, "materiau_id", pr, mat);
                    setprimattrib(0, "couleur", pr, "blanc"); setprimattrib(0, "usure", pr, us);
                    setprimattrib(0, "graine", pr, random_shash(ent) & 0x7fffffff);
                    setprimattrib(0, "route", pr, cid); setprimattrib(0, "modulation", pr, LMOD[l]);
                    setprimattrib(0, "largeur_m", pr, w); setprimattrib(0, "s0", pr, D0[k]); setprimattrib(0, "s1", pr, D1[k]);
                    setprimattrib(0, "rang", pr, rang); setprimattrib(0, "partie", pr, pc); setprimattrib(0, "rayon_m", pr, r);
                }
                rang++;
            }
        }
    }
}
s[]@rg_giratoires_marques_avertissements = avert;
"""
