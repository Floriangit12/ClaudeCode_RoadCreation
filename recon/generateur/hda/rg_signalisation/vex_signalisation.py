"""Code VEX de l'HDA rg::signalisation (lot L6) : classes du sol fabriqué, zones interdites, placement des supports par
la règle ARB-20, empilement des plaques, têtes de feux, instances et contrôles ; plaques des faces composées.

Repère Houdini (Y haut) ; le sol fabriqué (rg::sol + carrefours + giratoires + autoroute) porte l'attribut de
primitive « classe ». Rien n'est inventé : les distances viennent des paramètres de l'HDA, dont les défauts sont écrits
par construire.py depuis DEF-025, DEF-026, DEF-027, ARB-20, RF-SV-GEN.*, RF-MA-TRO-001 et les compléments L6-*.
"""

# ------------------------------------------------------------------------------------------- classes du sol
VEX_CLASSER = r'''
// cl : 1 chaussée (référence de la rive, RF-SV-GEN.DISTANCE_RIVE) ; 2 autre surface circulée ou circulable (BDD, BAU,
// piste, accotement revêtu, couronne franchissable : aucun support) ; 3 piéton (trottoir : cheminement de 1,40 m) ;
// 4 îlot ou terre-plein bordé ; 5 accotement non revêtu, berme, bande plantée, terre-plein latéral ; 6 abord (hors
// emprise décrite) ; 7 interdit (corps de bordure, mur, refuge revêtu…) ; 0 inconnu (interdit). Détail : listes lues une fois.
string noms[];
int vals[];
string listes[] = {"classes_chaussee", "classes_circulees", "classes_pietons", "classes_ilots", "classes_accotements",
                   "classes_abords", "classes_interdites"};
for (int k = 0; k < len(listes); k++) {
    string mots[] = split(chs("../" + listes[k]), " ");
    foreach (string m; mots) { append(noms, m); append(vals, k + 1); }
}
string fr[] = split(chs("../materiaux_franchissables"), " ");
string rf[] = split(chs("../materiaux_refuges"), " ");
int n = nprimitives(0);
int CL[];
resize(CL, n);
for (int p = 0; p < n; p++) {
    string c = prim(0, "classe", p);
    int k = find(noms, c);
    int v = k >= 0 ? vals[k] : 0;
    if (v == 4 && (c == "giratoire_ilot" || c == "carrefour_ilot")) {
        string mt = prim(0, "materiau_id", p);
        if (find(fr, mt) >= 0) v = 2;
        else if (find(rf, mt) >= 0) v = 7;
    }
    CL[p] = v;
    setprimattrib(0, "cl", p, v, "set");
    setprimgroup(0, "sol", p, 1);
}
// chaussée cachée sous une autre surface (sol du carrefour ou du giratoire sous les îlots posés dessus) : ni rive,
// ni surface admise (cl 8) — un rayon vertical au centre de la face touche d'abord la surface du dessus
for (int p = 0; p < n; p++) {
    if (CL[p] != 1) continue;                        // (les écritures de ce nœud ne sont pas relues par prim())
    vector c = prim(0, "P", p);
    vector h, uvw;
    int q = intersect(0, set(c.x, 100.0, c.z), {0, -200, 0}, h, uvw);
    if (q >= 0 && q != p && h.y > c.y + 0.002) setprimattrib(0, "cl", p, 8, "set");
}
'''

VEX_RIVE_PLAT = r'''
// chaussée seule, à plat (y = 0) : xyzdist donne la distance horizontale à la rive ; y0 garde l'altitude
if (i@cl != 1) removeprim(0, @primnum, 1);
'''

VEX_APLATIR = r'''
f@y0 = @P.y;
@P.y = 0.0;
'''

VEX_EXCLUSIONS = r'''
// abaissés et bateaux (bordures fabriquées, rôle bateau / chartière) : bande de part et d'autre de la face, à plat
int np = nprimitives(1);
for (int k = 0; k < np; k++) {
    int pts[] = primpoints(1, k);
    int n = len(pts);
    if (n < 2) continue;
    float pr = prim(1, "profondeur", k);
    vector g[], dr[];
    for (int j = 0; j < n; j++) {
        vector a = point(1, "P", pts[max(0, j - 1)]);
        vector b = point(1, "P", pts[min(n - 1, j + 1)]);
        vector t = normalize(set(b.x - a.x, 0.0, b.z - a.z));
        vector gauche = set(t.z, 0.0, -t.x);
        vector p = point(1, "P", pts[j]);
        p.y = 0.0;
        append(g, p + gauche * pr);
        append(dr, p - gauche * pr);
    }
    int poly = addprim(0, "poly");
    for (int j = 0; j < n; j++) addvertex(0, poly, addpoint(0, dr[j]));
    for (int j = n - 1; j >= 0; j--) addvertex(0, poly, addpoint(0, g[j]));
    setprimgroup(0, "interdit_plat", poly, 1);
    setprimattrib(0, "motif", poly, "abaisse", "set");
}
'''

VEX_OBSTACLES = r'''
// dispositifs de retenue (rg::autoroute, sortie 2) : emprise au sol, à plat (P14-4 : aucun support dans l'emprise)
@P.y = 0.0;
i@group_interdit_plat = 1;
i@group_obstacle = 1;
s@motif = "retenue";
'''

# ------------------------------------------------------------------------------------------- placement
VEX_ANCRER = r'''
// Point et tangente de la référence en s (entrée 1 : prims « id », points « s »), et point 8 m en amont (rive prolongée)
// référence : point et tangente en s (prim dont « id » = route)
function int ref_prim(string rid) {
    for (int k = 0; k < nprimitives(1); k++) if (prim(1, "id", k) == rid) return k;
    return -1;
}
function vector ref_pt(int pr; float s; vector tan) {
    int pts[] = primpoints(1, pr);
    int n = len(pts);
    int lo = 0, hi = n - 1;
    float s0 = point(1, "s", pts[0]), s1 = point(1, "s", pts[n - 1]);
    float sc = clamp(s, s0, s1);
    while (hi - lo > 1) {
        int m = (lo + hi) / 2;
        if (point(1, "s", pts[m]) <= sc) lo = m; else hi = m;
    }
    vector a = point(1, "P", pts[lo]), b = point(1, "P", pts[hi]);
    float sa = point(1, "s", pts[lo]), sb = point(1, "s", pts[hi]);
    float u = sb > sa ? (sc - sa) / (sb - sa) : 0.0;
    tan = normalize(set(b.x - a.x, 0.0, b.z - a.z));
    vector p = lerp(a, b, u);
    p.y = 0.0;
    return p;
}

if (s@anc_type != "xy") {
    int pr = ref_prim(s@route);
    if (pr < 0) { error("route %s absente des références", s@route); }
    vector tan, tu;
    v@P0 = ref_pt(pr, f@s, tan);
    v@T0 = tan * i@sens;
    v@P0u = ref_pt(pr, f@s - i@sens * 8.0, tu);
}
'''

VEX_PLACER = r'''
// Placement des ensembles (un point par ensemble, entrée 0, ancrage P0 / T0 / P0u calculé par « ancrer ») sur le sol
// fabriqué classé (entrée 1), la chaussée à plat (entrée 2 : rive) et les zones interdites à plat (entrée 3 : abaissés,
// emprises des dispositifs de retenue, attribut « obstacle »).

function int cl_en(vector X; vector hit) {
    vector uvw;
    int pr = intersect(1, set(X.x, 100.0, X.z), {0, -200, 0}, hit, uvw);
    if (pr < 0) return -1;
    return prim(1, "cl", pr);
}
function string classe_en(vector X) {
    vector hit, uvw;
    int pr = intersect(1, set(X.x, 100.0, X.z), {0, -200, 0}, hit, uvw);
    if (pr < 0) return "";
    return prim(1, "classe", pr);
}
function int interdit_en(vector X; int ignorer_obstacles) {
    if (nprimitives(3) == 0) return 0;
    vector hit, uvw;
    int pr = intersect(3, set(X.x, 10.0, X.z), {0, -20, 0}, hit, uvw);
    if (pr < 0) return 0;
    if (ignorer_obstacles && prim(3, "obstacle", pr)) return 0;
    return 1;
}
function int admis(int c; string surf; int rural) {
    if (surf == "ilot") return c == 4;
    if (surf == "tpc") return c == 4 || c == 5;
    if (surf == "accotement") return c == 5 || c == 4 || c == 6 || c == -1;
    if (c == 3 || c == 4 || c == 5) return 1;
    if ((c == 6 || c == -1) && rural) return 1;          // abord, ou terrain hors de l'emprise fabriquée
    return 0;
}
// distance de la rive le long de D depuis P0 : dernière sortie de la chaussée de ce côté (les îlots et terre-pleins de
// moins de « trou » mètres entre deux couloirs sont franchis : la rive est le bord extérieur de la chaussée)
function float rive_le_long(vector P0; vector D; float dmax; float pas; float trou) {
    int vu = 0;
    float der = -1.0, hors = 0.0;
    vector h;
    for (float d = 0.0; d <= dmax; d += pas) {
        int c = cl_en(P0 + D * d, h);
        if (c == 1) { vu = 1; der = d; hors = 0.0; }
        else if (vu) { hors += pas; if (hors > trou) break; }
    }
    return vu ? der + pas : -1.0;
}
// distance de la première entrée dans la chaussée le long de D
function float entree_le_long(vector P0; vector D; float dmax; float pas) {
    vector h;
    for (float d = 0.0; d <= dmax; d += pas) if (cl_en(P0 + D * d, h) == 1) return d;
    return -1.0;
}
// largeur d'une surface de classe c le long de D depuis X
function float largeur_le_long(vector X; vector D; int c; float dmax; float pas) {
    vector h;
    for (float d = pas; d <= dmax; d += pas) if (cl_en(X + D * d, h) != c) return d - pas;
    return dmax;
}
// support rond du catalogue : plus petit H ≥ h (sinon le plus haut) au diamètre demandé ; s@ et f@ en sortie
function string support_rond(string ids[]; float diam; float h; float hasset) {
    string best = "";
    float hb = 1e9, hmax = -1.0;
    string idmax = "";
    foreach (string e; ids) {
        string f[] = split(e, ":");
        if (len(f) < 3) continue;
        float d = atof(f[1]), H = atof(f[2]);
        if (abs(d - diam) > 0.004) continue;
        if (H >= h - 1e-6 && H < hb) { hb = H; best = f[0]; }
        if (H > hmax) { hmax = H; idmax = f[0]; }
    }
    if (best == "") { best = idmax; hb = hmax; }
    hasset = hb;
    return best;
}
function float lacet_usd(vector F) { return degrees(atan2(-F.x, -F.z)); }
function vector4 orient_y(float lacet_deg) { return quaternion(radians(lacet_deg), {0, 1, 0}); }

float BORD = chf("../bord_rive"), CHEM = chf("../cheminement"), SURPL = chf("../surplomb"), RC = chf("../support_rase_campagne");
float GAP = chf("../ecart_plaques"), DEP = chf("../depassement"), ESP = chf("../espacement"), PAS = chf("../pas");
float VUE = chf("../vue_abaisse"), COL = chf("../collier"), LACET = chf("../lacet_ext"), MPAS = chf("../pas_marche");
float RMAX = chf("../rayon_max"), AXE_FEU = chf("../axe_mat_feu"), BRAS_FEU = chf("../bras_feu"), BOR_MIN = chf("../retrait_min");
float AXE_FEU_MAX = chf("../axe_feu_max"), BAS_FEU_MIN = chf("../bas_feu_min");
string SUP_IDS[] = split(chs("../supports_ronds"), " ");
float MOD_FEU = chf("../module_feu");
float TROU = chf("../trou_rive");
float PM1[] = {-1.0, 1.0};

int n_ens = npoints(0);
vector poses[];
int n_ok = 0, n_contrainte = 0, n_echec = 0;
for (int i = 0; i < n_ens; i++) {
    string id = point(0, "id", i), fam = point(0, "famille", i), at = point(0, "anc_type", i);
    string surf = point(0, "surface", i), cote = point(0, "cote", i), styp = point(0, "support_type", i);
    float r = point(0, "support_r", i), bas = point(0, "bas", i), lmax = point(0, "l_max", i);
    int dbl = point(0, "double", i);
    vector P0, T, D, Q;
    float fen0 = -1e9, fen1 = 1e9, rayon = point(0, "rayon", i);
    int rural = point(0, "rural_plan", i);
    string motif = "";
    if (at == "xy") {
        P0 = point(0, "P", i);
        T = normalize(point(0, "dir", i));
        D = set(-T.z, 0.0, T.x);
        Q = P0;
    } else {
        P0 = point(0, "P0", i);
        T = normalize(point(0, "T0", i));
        vector droite = set(-T.z, 0.0, T.x);
        D = cote == "gauche" ? -droite : droite;
        fen0 = point(0, "fen0", i); fen1 = point(0, "fen1", i);
        rayon = RMAX;
        float a1 = (fam == "feu") ? AXE_FEU : BORD + 0.5 * lmax;
        if (surf == "tpc") {
            // répétition à gauche sur le terre-plein central : rive gauche de la chaussée visée (côté droit de l'axe)
            float de = entree_le_long(P0, -D, 30.0, MPAS);
            Q = P0 - D * max(0.0, de - a1);
        } else {
            float dr = rive_le_long(P0, D, 40.0, MPAS, TROU);
            vector Pu = point(0, "P0u", i);
            float du = rive_le_long(Pu, D, 40.0, MPAS, TROU);
            if (dr < 0.0 || (du > 0.0 && dr > du + 1.0)) { dr = du; motif += "rive prolongée (coin) ; "; }
            vector h;
            int cb = cl_en(P0 + D * (dr + 0.3), h);
            rural = max(rural, (cb == 2 || cb == 5 || cb == 6) ? 1 : 0);
            if (rural && fam != "feu" && fam != "balise") a1 = max(RC, a1);
            Q = P0 + D * (dr + a1);
        }
    }
    // face : vers l'usager (opposée au trafic), tournée de LACET vers l'extérieur (DEF-025) ; ou visée / azimut décrits
    vector F = normalize(-T * cos(radians(LACET)) + D * sin(radians(LACET)));
    if (at == "xy" || at == "potence" || at == "portique") F = -T;     // surplomb : plan du profil en travers (IISR1 8 a)
    if (point(0, "a_vise", i)) { vector v = point(0, "vise", i); F = normalize(set(v.x - Q.x, 0.0, v.z - Q.z)); }
    if (point(0, "a_face_az", i)) { float az = radians(point(0, "face_az", i)); F = set(cos(az), 0.0, -sin(az)); }
    vector Uv = set(F.z, 0.0, -F.x);                  // à droite pour l'usager qui regarde la face
    float a_c1 = (fam == "feu") ? AXE_FEU : BORD + 0.5 * lmax;
    // ---- recherche du point admissible le plus proche de Q (ARB-20 : cas 1, puis 2, puis 3)
    int trouve[] = {0, 0, 0};
    vector best[] = {{0,0,0},{0,0,0},{0,0,0}};
    float bd[] = {1e9, 1e9, 1e9}, bds[] = {1e9, 1e9, 1e9};
    float b_dc[] = {0,0,0}, b_win[] = {0,0,0}, b_wout[] = {0,0,0};
    int b_c[] = {0,0,0};
    int ign = (surf == "tpc");
    float rm = min(rayon, RMAX);
    float r_repli = -1.0;                              // premier anneau où un cas de repli (2 ou 3) est trouvé
    float need1 = (rural && fam != "feu" && fam != "balise") ? max(RC, a_c1) : a_c1;
    float need3 = r + BOR_MIN;
    float cap = CHEM + r + 0.10;                       // marches bornées : seul « ≥ 1,40 + r » compte pendant la recherche
    for (float rr = 0.0; rr <= rm + 1e-6; rr += PAS) {
        if (trouve[0]) break;
        if (r_repli >= 0.0 && rr > r_repli + 1.5) break;   // au-delà, le cas 1 n'est plus « au plus près » [G]
        int na = max(1, (int)ceil(2.0 * PI * rr / PAS));
        for (int k = 0; k < na; k++) {
            float ang = 2.0 * PI * k / na;
            vector Xc = Q + set(cos(ang), 0.0, sin(ang)) * rr;
            Xc.y = 0.0;
            float ds = dot(Xc - P0, T);
            if (at != "xy") {
                if (ds < fen0 - 1e-6 || ds > fen1 + 1e-6) continue;
                if (surf != "tpc" && dot(Xc - P0, D) < 0.3) continue;
            }
            vector hit;
            int c = cl_en(Xc, hit);
            if (!admis(c, surf, rural)) continue;
            int prr; vector uvr;
            float dc = xyzdist(2, Xc, prr, uvr);
            float need2 = (c == 3) ? max(CHEM + r, a_c1) : ((rural || c == 5 || c == 6) ? a_c1 : 1e9);
            int utile = 0;
            if (!trouve[0] && dc >= need1 - 1e-6) utile = 1;
            if (!trouve[1] && dc >= need2 - 1e-6) utile = 1;
            if (!trouve[2] && dc >= need3 - 1e-6) utile = 1;
            if (!utile) continue;
            int libre = 1;
            foreach (vector q; poses) if (distance(q, Xc) < ESP) libre = 0;
            if (!libre) continue;
            if (interdit_en(Xc, ign)) continue;
            if (nprimitives(3) > 0) {
                int prx; vector uvx;
                float dex = xyzdist(3, Xc, prx, uvx);
                if (dex < r && !(ign && prim(3, "obstacle", prx))) continue;
            }
            if (c == 3) {
                float y_rive = primuv(2, "y0", prr, uvr);
                if (hit.y - y_rive < VUE) continue;     // trottoir abaissé (vue ≤ 0,05, RF-MA-TRO-015) : exclu
            }
            int ok = 1;
            for (int j = 0; j < 8 && ok; j++) {
                float a = 2.0 * PI * j / 8.0;
                vector h2;
                if (!admis(cl_en(Xc + set(cos(a), 0.0, sin(a)) * (r + 0.02), h2), surf, rural)) ok = 0;
            }
            if (dbl && ok) {
                vector h3;
                foreach (float sg; PM1) {
                    if (!admis(cl_en(Xc + Uv * sg * 0.3 * lmax, h3), surf, rural)) ok = 0;
                    if (interdit_en(Xc + Uv * sg * 0.3 * lmax, ign)) ok = 0;
                }
            }
            if (!ok) continue;
            float win = 0.0, wout = 0.0;
            if (c == 3) {
                vector pr_r = primuv(2, "P", prr, uvr);
                vector n = normalize(set(Xc.x - pr_r.x, 0.0, Xc.z - pr_r.z));
                wout = largeur_le_long(Xc, n, 3, cap, 0.04);
                win = largeur_le_long(Xc, -n, 3, cap, 0.04);
            }
            float dd = distance(Xc, Q);
            for (int ca = 0; ca < 3; ca++) {
                if (trouve[ca]) continue;
                int vcas = 0;
                if (ca == 0) vcas = dc >= need1 - 1e-6 && (c != 3 || wout - r >= CHEM - 1e-6);
                if (ca == 1) vcas = dc >= need2 - 1e-6 && (c != 3 || win - r >= CHEM - 1e-6);
                if (ca == 2) vcas = dc >= need3 - 1e-6 && (c != 3 || wout - r >= CHEM - 1e-6 || win - r >= CHEM - 1e-6
                                                             || win + wout < CHEM + 2.0 * r);
                if (!vcas) continue;
                if (dd < bd[ca] - 1e-9 || (abs(dd - bd[ca]) < 1e-9 && abs(ds) < bds[ca])) {
                    bd[ca] = dd; bds[ca] = abs(ds); best[ca] = Xc; b_dc[ca] = dc; b_win[ca] = win;
                    b_wout[ca] = wout; b_c[ca] = c;
                }
            }
        }
        for (int ca = 0; ca < 3; ca++) if (bd[ca] < 1e8) trouve[ca] = 1;
        if (r_repli < 0.0 && (trouve[1] || trouve[2])) r_repli = rr;
    }
    int cas = -1;
    for (int k = 0; k < 3; k++) if (trouve[k] && cas < 0) cas = k;
    string statut = "ok";
    vector X = Q;
    float dc = 0.0, win = 0.0, wout = 0.0;
    int csol = 0;
    if (cas < 0) {
        statut = "echec";
        motif += "aucun point admissible dans la fenêtre (surface, rive, cheminement, abaissés, espacement) ; ";
        vector h;
        csol = cl_en(X, h);
        int prr; vector uvr;
        dc = xyzdist(2, X, prr, uvr);
    } else {
        X = best[cas]; dc = b_dc[cas]; win = b_win[cas]; wout = b_wout[cas]; csol = b_c[cas];
        if (csol == 3) {
            int prr; vector uvr;
            xyzdist(2, X, prr, uvr);
            vector pr_r = primuv(2, "P", prr, uvr);
            vector n = normalize(set(X.x - pr_r.x, 0.0, X.z - pr_r.z));
            wout = largeur_le_long(X, n, 3, 8.0, 0.02);
            win = largeur_le_long(X, -n, 3, 8.0, 0.02);
        }
        if (cas == 1) motif += (csol == 3) ? "ARB-20 cas 2 : support côté façade, plaque en surplomb du cheminement ; "
                                           : "dégagement 0,70 + l/2 sans les 2 m de la rase campagne ; ";
        if (cas == 2) {
            statut = "contrainte";
            motif += (csol == 3) ? "ARB-20 cas 3 : axe réduit, « IISR1 8 i, contrainte » ; "
                                 : "dégagement réduit sous contrainte (IISR1 8 i ; îlot : IISR3 43-4 D « si possible ») ; ";
        }
        if (rural && cas == 1 && csol != 3 && fam != "balise")
            motif += "accotement étroit : support à moins de 2 m du bord, bord du panneau ≥ 0,70 m (exception de "
                     "RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE) ; ";
    }
    if (csol == 6 || csol == -1) motif += "support sur l'abord, hors de l'emprise fabriquée (rase campagne) ; ";
    if (ign && nprimitives(3) > 0) {
        int pro; vector uvo;
        float dob = xyzdist(3, X, pro, uvo);
        if (dob < r + 0.3 && prim(3, "obstacle", pro)) motif += "support fixé sur le séparateur du terre-plein central [G] ; ";
    }
    vector hit;
    int c_x = cl_en(X, hit);
    float zs = hit.y;
    float enterre = 0.0;
    if (c_x < 0) {
        int prr; vector uvr;
        xyzdist(2, X, prr, uvr);
        zs = primuv(2, "y0", prr, uvr) - 0.10;          // terrain non modélisé : 0,10 m sous la rive voisine [G]
        enterre = 0.40;                                  // pied du support descendu sous le sol neutre du rendu [G]
    }
    X.y = zs;
    if (at != "xy" && at != "potence" && at != "portique") {
        // la face suit la visée décrite ; sinon direction de la référence (inchangée)
    }
    if (point(0, "a_vise", i)) { vector v = point(0, "vise", i); F = normalize(set(v.x - X.x, 0.0, v.z - X.z)); Uv = set(F.z, 0.0, -F.x); }
    append(poses, set(X.x, 0.0, X.z));
    if (dbl) foreach (float sg; PM1) append(poses, set(X.x, 0.0, X.z) + Uv * sg * 0.3 * lmax);
    // ---- éléments : empilement (de bas en haut), têtes de feux, potence
    string codes[] = point(0, "el_code", i);
    string kinds[] = point(0, "el_kind", i);
    string assets[] = point(0, "el_asset", i);
    string gammes[] = point(0, "el_gamme", i);
    string faces[] = point(0, "el_face", i);
    float L[] = point(0, "el_l", i);
    float H[] = point(0, "el_h", i);
    float Z0[] = point(0, "el_zmin", i);
    float Z1[] = point(0, "el_zmax", i);
    float ZE[] = point(0, "el_z", i);
    float ROT[] = point(0, "el_rot", i);
    float UE[] = point(0, "el_u", i);
    float AZ[] = point(0, "el_azabs", i);
    int AAZ[] = point(0, "el_a_azabs", i);
    int VARR[] = point(0, "el_vise_arret", i);
    string SIG[] = point(0, "el_signal", i);
    float ECH[] = point(0, "el_echelle", i);
    float z_bas = zs + bas, haut = zs, bas_min = 1e9, bord_min = 1e9;
    float bas_feu = 1e9, axe_sup = -1e9;
    int n_r11 = 0;
    vector Pbase = X;
    float scale_sup = 1.0;
    float dlane = 0.0;
    float zref_pot = zs;
    int surplomb = (at == "potence" || at == "portique");
    float portee = point(0, "portee", i);
    string VOIES[] = point(0, "el_voie", i);
    if (at == "portique") {
        // portique : du pied (accotement de droite) jusqu'à l'axe de la chaussée séparée (terre-plein central) [G]
        portee = max(1.0, dot(set(X.x, 0.0, X.z) - P0, D));
    }
    if (surplomb) {
        float ba = point(0, "bas_asset", i);
        scale_sup = (at == "potence" && ba > 0.0) ? max(1.0, bas / ba) : 1.0;
    }
    for (int k = 0; k < len(codes); k++) {
        string kd = kinds[k];
        if (surplomb) {
            // centre de la voie visée sous la portée (L6-SV-ECHANGEUR.SUPPORTS) ; bras ou poutre vers la chaussée
            string voie = (len(VOIES) > k && VOIES[k] != "") ? VOIES[k] : point(0, "potence_voie", i);
            float d0 = -1.0, d1 = -1.0;
            for (float d = 0.0; d <= portee + 0.5; d += MPAS) {
                string cn = classe_en(X - D * d);
                if (cn == voie && d0 < 0.0) d0 = d;
                if (d0 >= 0.0 && cn != voie) { d1 = d; break; }
            }
            if (d0 >= 0.0 && d1 < 0.0) d1 = portee;
            dlane = (d0 >= 0.0 && d1 > d0) ? 0.5 * (d0 + d1) : 0.75 * portee;
            if (dlane > portee - 0.3) { motif += "voie hors de la portée du support ; "; statut = "echec"; }
            Pbase = X - D * dlane + F * ((at == "portique") ? 0.60 : 0.35);
            vector hp;
            cl_en(Pbase, hp);
            zref_pot = max(zs, hp.y);
        }
        vector Fk = F;
        if (AAZ[k]) { float az = radians(AZ[k]); Fk = set(cos(az), 0.0, -sin(az)); }
        if (ROT[k] != 0.0) { matrix3 m = ident(); rotate(m, radians(ROT[k]), {0, 1, 0}); Fk = normalize(Fk * m); }
        if (VARR[k]) {
            // répétiteur tourné vers le premier véhicule arrêté : 3 m en amont, au milieu de la voie de droite [G]
            vector cible = X - T * 3.0 - D * (dc + 1.5);
            Fk = normalize(set(cible.x - X.x, 0.0, cible.z - X.z));
        }
        vector Uk = set(Fk.z, 0.0, -Fk.x);
        float zpiv;
        if (surplomb) { zpiv = zref_pot + bas - Z0[k]; }
        else if (ZE[k] >= 0.0) zpiv = zs + ZE[k];
        else { zpiv = z_bas - Z0[k]; z_bas = zpiv + Z1[k] + GAP; }
        float avance = r + COL;
        if (kd == "feu") avance = r + BRAS_FEU;
        if (codes[k] == "bouton_appel") avance = r + 0.12;
        if (kd == "balise") avance = 0.0;
        vector Pk = surplomb ? Pbase + set(0, zpiv, 0) : X + Fk * avance + set(0.0, zpiv - zs, 0.0) + Uk * UE[k];
        if (surplomb) Pk.y = zpiv;
        int np = addpoint(0, Pk);
        setpointgroup(0, "instance", np, 1);
        setpointattrib(0, "ensemble", np, id, "set");
        setpointattrib(0, "code", np, codes[k], "set");
        setpointattrib(0, "kind", np, kd, "set");
        setpointattrib(0, "asset", np, assets[k], "set");
        setpointattrib(0, "gamme", np, gammes[k], "set");
        setpointattrib(0, "face", np, faces[k], "set");
        setpointattrib(0, "signal", np, SIG[k], "set");
        setpointattrib(0, "largeur", np, L[k], "set");
        setpointattrib(0, "hauteur", np, H[k], "set");
        setpointattrib(0, "lacet_usd", np, lacet_usd(Fk), "set");
        setpointattrib(0, "orient", np, orient_y(lacet_usd(Fk)), "set");
        float ek = len(ECH) > k ? ECH[k] : 1.0;
        setpointattrib(0, "echelle", np, set(ek, ek, ek), "set");
        setpointattrib(0, "face_dir", np, Fk, "set");
        float bk = zpiv + Z0[k] - zs, tk = zpiv + Z1[k] - zs;
        setpointattrib(0, "bas_m", np, bk, "set");
        setpointattrib(0, "haut_m", np, tk, "set");
        haut = max(haut, zpiv + Z1[k]);
        if (kd == "plaque" || kd == "plaque_composee") {
            bas_min = min(bas_min, bk);
            foreach (float sg; PM1) {
                vector E = Pk + Uk * sg * 0.5 * L[k];
                E.y = 0.0;
                int pe; vector ue;
                bord_min = min(bord_min, xyzdist(2, E, pe, ue));
            }
        }
        if (codes[k] == "R11v") {
            n_r11++;
            bas_feu = min(bas_feu, bk);
            axe_sup = max(axe_sup, (zpiv - zs) + 2.5 * MOD_FEU);   // axe du feu supérieur : 3 modules empilés
        }
    }
    // ---- support(s)
    float hsup = 0.0;
    if (styp != "aucun") {
        string sid = point(0, "support_asset", i);
        float hreq = (haut - zs) + DEP + enterre, hasset = 0.0;
        vector sc = {1, 1, 1};
        float lac = 0.0;
        if (styp == "potence" || styp == "portique") {
            // potence : allongée pour le gabarit (L6-SV-SURPLOMB.GABARIT) ; portique : poutre à la portée mesurée
            sc = (styp == "potence") ? set(1.0, 1.0, scale_sup) : set(portee / max(1.0, point(0, "portee_asset", i)), 1.0, 1.0);
            vector A = -D;
            lac = degrees(atan2(-A.z, A.x));
            hsup = 0.0;
        } else if (styp == "mat_feux") {
            float hm = point(0, "support_h", i);
            hsup = max(hm, hreq);
            hasset = (sid == "mat_feux_D114_H42") ? 4.2 : 3.4;
            sc = set(1.0, 1.0, hsup / hasset);
        } else {
            sid = support_rond(SUP_IDS, 2.0 * r, hreq, hasset);
            hsup = hreq;
            sc = set(1.0, 1.0, hreq / max(0.1, hasset));
        }
        int nsup = dbl ? 2 : 1;
        for (int k = 0; k < nsup; k++) {
            vector Ps = X;
            if (dbl) Ps = X + Uv * (k == 0 ? -1.0 : 1.0) * 0.3 * lmax;
            vector hh;
            if (cl_en(Ps, hh) >= 0) Ps.y = hh.y;
            else Ps.y = zs;
            Ps.y -= enterre;
            int np = addpoint(0, Ps);
            setpointgroup(0, "instance", np, 1);
            setpointattrib(0, "ensemble", np, id, "set");
            setpointattrib(0, "code", np, styp, "set");
            setpointattrib(0, "kind", np, "support", "set");
            setpointattrib(0, "asset", np, sid, "set");
            setpointattrib(0, "gamme", np, "", "set");
            setpointattrib(0, "face", np, "", "set");
            setpointattrib(0, "lacet_usd", np, (styp == "potence" || styp == "portique") ? lac : lacet_usd(F), "set");
            setpointattrib(0, "orient", np, orient_y((styp == "potence" || styp == "portique") ? lac : lacet_usd(F)), "set");
            setpointattrib(0, "echelle", np, sc, "set");
            setpointattrib(0, "face_dir", np, F, "set");
            setpointattrib(0, "largeur", np, 2.0 * r, "set");
            setpointattrib(0, "hauteur", np, (styp == "potence") ? 6.8 * scale_sup : ((styp == "portique") ? 7.6 : hsup), "set");
            setpointattrib(0, "bas_m", np, 0.0, "set");
            setpointattrib(0, "haut_m", np, (styp == "potence") ? 6.8 * scale_sup : ((styp == "portique") ? 7.6 : hsup), "set");
            setpointattrib(0, "portee", np, portee, "set");
        }
    }
    // ---- contrôles de l'ensemble
    float cheminement = (csol == 3) ? max(win - r, wout - r) : -1.0;
    int surplomb_ok = 1;
    if (csol == 3 && cas == 1 && bas_min < SURPL - 1e-6) { surplomb_ok = 0; statut = "echec"; motif += "plaque au-dessus du cheminement sous 2,20 m ; "; }
    if (fam == "feu" && n_r11 > 0) {
        if (bas_feu < BAS_FEU_MIN - 1e-6) { statut = "echec"; motif += "bas du boîtier sous 2,00 m (RF-FEU.HAUTEUR.TROTTOIR) ; "; }
        if (axe_sup > AXE_FEU_MAX + 1e-6) { statut = "echec"; motif += "axe du feu supérieur au-dessus de 4,20 m ; "; }
    }
    if (statut == "ok") n_ok++; else if (statut == "contrainte") n_contrainte++; else n_echec++;
    setpointattrib(0, "P", i, X);
    setpointgroup(0, "ensemble", i, 1);
    setpointattrib(0, "statut", i, statut, "set");
    setpointattrib(0, "motif", i, motif, "set");
    setpointattrib(0, "cas_arb20", i, cas + 1, "set");
    setpointattrib(0, "classe_sol", i, classe_en(X), "set");
    setpointattrib(0, "d_rive_axe", i, dc, "set");
    setpointattrib(0, "bord_rive", i, bord_min < 1e8 ? bord_min : -1.0, "set");
    setpointattrib(0, "w_cote_rive", i, win, "set");
    setpointattrib(0, "w_cote_facade", i, wout, "set");
    setpointattrib(0, "cheminement_libre", i, cheminement, "set");
    setpointattrib(0, "surplomb_ok", i, surplomb_ok, "set");
    setpointattrib(0, "ds", i, dot(X - P0, T), "set");
    setpointattrib(0, "dt", i, dot(set(X.x, 0, X.z) - P0, D), "set");
    setpointattrib(0, "ecart_q", i, distance(set(X.x, 0, X.z), set(Q.x, 0, Q.z)), "set");
    setpointattrib(0, "z_sol", i, zs, "set");
    setpointattrib(0, "bas_reel", i, bas_min < 1e8 ? bas_min : -1.0, "set");
    setpointattrib(0, "haut_m", i, haut - zs, "set");
    setpointattrib(0, "hauteur_support", i, hsup, "set");
    setpointattrib(0, "lacet_usd", i, lacet_usd(F), "set");
    setpointattrib(0, "face_dir", i, F, "set");
    setpointattrib(0, "trafic_dir", i, T, "set");
    setpointattrib(0, "n_r11", i, n_r11, "set");
    setpointattrib(0, "bas_feu", i, bas_feu < 1e8 ? bas_feu : -1.0, "set");
    setpointattrib(0, "axe_feu_sup", i, axe_sup > -1e8 ? axe_sup : -1.0, "set");
    setpointattrib(0, "rural", i, rural, "set");
    setpointattrib(0, "q", i, Q, "set");
}
setdetailattrib(0, "rg_l6_ensembles", n_ens, "set");
setdetailattrib(0, "rg_l6_ok", n_ok, "set");
setdetailattrib(0, "rg_l6_contrainte", n_contrainte, "set");
setdetailattrib(0, "rg_l6_echec", n_echec, "set");
'''

# ------------------------------------------------------------------------------------------- plaques composées
VEX_PLAQUES = r'''
// Plaques des faces composées : boîte de l × h × e (e = épaisseur), face avant texturée (uv 0-1), revers et chants
// « revers_panneau » ; pivot au milieu du bord inférieur de la face, face vers face_dir (comme les assets du catalogue).
float E = chf("../epaisseur_plaque");
for (int p = 0; p < npoints(1); p++) {
    if (point(1, "kind", p) != "plaque_composee") continue;
    vector P = point(1, "P", p), F = point(1, "face_dir", p);
    float l = point(1, "largeur", p), h = point(1, "hauteur", p);
    string face = point(1, "face", p), ens = point(1, "ensemble", p);
    vector U = set(-F.z, 0.0, F.x);                 // à gauche de la face vue de devant (repère des assets : x)
    vector up = {0, 1, 0};
    vector c[];
    float YY[];
    append(YY, 0.0);
    append(YY, -E);
    foreach (float yy; YY) {
        vector o = P + F * yy;
        append(c, o - U * 0.5 * l);
        append(c, o + U * 0.5 * l);
        append(c, o + U * 0.5 * l + up * h);
        append(c, o - U * 0.5 * l + up * h);
    }
    int ids[];
    foreach (vector q; c) append(ids, addpoint(1, q));
    // face avant (normale +F) : sommets dans le sens horaire vu de devant (convention des faces Houdini)
    int f0 = addprim(0, "poly", ids[0], ids[3], ids[2], ids[1]);
    setprimattrib(0, "materiau_id", f0, "face:" + face, "set");
    setprimattrib(0, "ensemble", f0, ens, "set");
    // u croît vers la droite de la face vue de devant (−U), v vers le haut (sommets d'une primitive créée ici :
    // adressés par (primitive, rang du sommet))
    vector uvs[] = {{1, 0, 0}, {1, 1, 0}, {0, 1, 0}, {0, 0, 0}};
    for (int j = 0; j < 4; j++) setvertexattrib(0, "uv", f0, j, uvs[j], "set");
    int quads[] = {4, 5, 6, 7,  0, 1, 5, 4,  1, 2, 6, 5,  2, 3, 7, 6,  3, 0, 4, 7};
    for (int q = 0; q < 5; q++) {
        int f = addprim(0, "poly", ids[quads[4 * q]], ids[quads[4 * q + 1]], ids[quads[4 * q + 2]], ids[quads[4 * q + 3]]);
        setprimattrib(0, "materiau_id", f, "revers_panneau", "set");
        setprimattrib(0, "ensemble", f, ens, "set");
        for (int j = 0; j < 4; j++) setvertexattrib(0, "uv", f, j, {0, 0, 0}, "set");
    }
}
'''

VEX_CONTROLES = r'''
// détail : synthèse des ensembles (entrée 0 : ENSEMBLES)
int n = npoints(0), ok = 0, ct = 0, ec = 0, chem = 0, circ = 0;
for (int i = 0; i < n; i++) {
    string st = point(0, "statut", i);
    if (st == "ok") ok++; else if (st == "contrainte") ct++; else ec++;
    float c = point(0, "cheminement_libre", i);
    if (c >= 0.0 && c < chf("../cheminement") - 1e-6) chem++;
}
setdetailattrib(0, "rg_l6_ensembles", n, "set");
setdetailattrib(0, "rg_l6_ok", ok, "set");
setdetailattrib(0, "rg_l6_contrainte", ct, "set");
setdetailattrib(0, "rg_l6_echec", ec, "set");
setdetailattrib(0, "rg_l6_cheminement_insuffisant", chem, "set");
'''
