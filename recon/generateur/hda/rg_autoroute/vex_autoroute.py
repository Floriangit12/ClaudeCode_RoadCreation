"""Code VEX de l'HDA rg::autoroute::1.0 (lot « autoroutes ») : recopié dans les wrangles par construire.py.

Repère : local (x, y) = Lambert-93 − origine ; Houdini (x, z = −y), Y haut (README_RG § 1). Une route est repérée par
sa ligne de référence échantillonnée (rg::graphe, sortie 1 : points s, gauche) ; (s, t) avec t positif à gauche.
Houdini n'invente rien : contours des dispositifs de retenue et pièces des glissières = catalogue route_fr (paramètres
écrits par construire.py depuis assets/specs/route/catalogue_assets_route.json, sources citées dans l'aide) ; positions
= limites « separateur » du modèle ; musoirs = îlots du modèle (îlot peint, terre-plein latéral) et bords des
plates-formes ; hachures et chevrons = DEF-020, RF-MQ-HACH-01 à -03, RF-MQ-MUS-01 (dossier 08, chevrons_zone).
"""

VEX_COMMUN = r"""
// ---------------------------------------------------------------- rg::autoroute : fonctions communes
function vector2 ra_xy(vector P) { return set(P.x, -P.z); }
function vector ra_h(vector2 q; float h) { return set(q.x, h, -q.y); }
function vector2 ra_gauche(vector2 d) { return set(-d.y, d.x); }

// repère d'une route : primitive de la référence échantillonnée (s, gauche)
function void ra_repere(int gr; int pr; export float S[]; export vector2 X[]; export vector2 G[])
{
    resize(S, 0); resize(X, 0); resize(G, 0);
    int pts[] = primpoints(gr, pr);
    foreach (int p; pts) {
        float s = point(gr, "s", p);
        if (len(S) > 0 && s <= S[-1] + 1e-9) continue;
        push(S, s);
        push(X, ra_xy(point(gr, "P", p)));
        vector g = point(gr, "gauche", p);
        push(G, normalize(set(g.x, -g.z)));
    }
}

// point (s, t) -> (x, y) local (prolongé par les tangentes hors de [0, L])
function vector2 ra_pt(float S[]; vector2 X[]; vector2 G[]; float s; float t)
{
    int n = len(S);
    int lo = 0, hi = n - 1;
    while (hi - lo > 1) { int m = (lo + hi) / 2; if (S[m] <= s) lo = m; else hi = m; }
    float u = (s - S[lo]) / max(S[hi] - S[lo], 1e-12);
    vector2 g = normalize(G[lo] + clamp(u, 0.0, 1.0) * (G[hi] - G[lo]));
    return X[lo] + u * (X[hi] - X[lo]) + t * g;
}

// (x, y) local -> (s, t) de la route (projection sur la polyligne la plus proche)
function vector2 ra_st(float S[]; vector2 X[]; vector2 G[]; vector2 Q)
{
    float best = 1e30;
    vector2 r = set(0.0, 0.0);
    int n = len(S);
    for (int i = 0; i < n - 1; i++) {
        vector2 a = X[i], d = X[i + 1] - X[i];
        float l2 = dot(d, d);
        if (l2 < 1e-12) continue;
        float u = dot(Q - a, d) / l2;
        float uc = clamp(u, 0.0, 1.0);
        if ((i == 0 && u < 0) || (i == n - 2 && u > 1)) uc = u;      // prolongement aux bouts
        vector2 q = a + uc * d;
        float dd = length(Q - q);
        if (dd < best) {
            best = dd;
            vector2 g = normalize(G[i] + clamp(uc, 0.0, 1.0) * (G[i + 1] - G[i]));
            r = set(S[i] + uc * (S[i + 1] - S[i]), dot(Q - q, g));
        }
    }
    return r;
}

// t d'une limite (polyligne de rg::profils, points s, t) à l'abscisse s
function float ra_lim_t(int gl; int pr; float s)
{
    int pts[] = primpoints(gl, pr);
    int n = len(pts);
    float sa = point(gl, "s", pts[0]);
    if (s <= sa) return point(gl, "t", pts[0]);
    for (int i = 0; i < n - 1; i++) {
        float s0 = point(gl, "s", pts[i]), s1 = point(gl, "s", pts[i + 1]);
        if (s <= s1) {
            float u = (s - s0) / max(s1 - s0, 1e-12);
            return lerp(float(point(gl, "t", pts[i])), float(point(gl, "t", pts[i + 1])), u);
        }
    }
    return point(gl, "t", pts[n - 1]);
}

// limite d'une route à l'abscisse s : la plus à droite (cote < 0, t minimal) ou la plus à gauche (cote > 0) ;
// marque = 1 : parmi les limites qui portent un marquage. Renvoie le numéro de primitive (−1 si aucune).
function int ra_limite(int gl; string rid; float s; int cote; int marque)
{
    float best = cote < 0 ? 1e30 : -1e30;
    int res = -1;
    for (int pr = 0; pr < nprimitives(gl); pr++) {
        if (prim(gl, "route", pr) != rid) continue;
        float s0 = prim(gl, "s0", pr), s1 = prim(gl, "s1", pr);
        if (s < s0 - 1e-7 || s > s1 + 1e-7) continue;
        string mq = prim(gl, "marquages", pr);
        if (marque && (mq == "" || mq == "[]")) continue;
        float t = ra_lim_t(gl, pr, s);
        if ((cote < 0 && t < best) || (cote > 0 && t > best)) { best = t; res = pr; }
    }
    return res;
}

// Z du sol fabriqué sous (x, y) sur la route rid (rayon vertical, toutes les surfaces ; la plus proche de zref)
function float ra_z_sol(int gs; string rid; vector2 q; float zref; export int ok; export string mat)
{
    vector pos[]; int prs[]; vector uvw[];
    int n = intersect_all(gs, "", ra_h(q, zref + 50.0), set(0.0, -100.0, 0.0), pos, prs, uvw, 1e-5, 1e-5);
    ok = 0;
    mat = "";
    float best = 1e30, z = zref;
    for (int k = 0; k < n; k++) {
        if (rid != "" && prim(gs, "route", prs[k]) != rid) continue;
        if (prim(gs, "visible", prs[k]) == 0) continue;
        float d = abs(pos[k].y - zref);
        if (d < best) { best = d; z = pos[k].y; ok = 1; mat = prim(gs, "materiau_id", prs[k]); }
    }
    return z;
}

// découpe de Sutherland-Hodgman d'un polygone par un polygone CONVEXE orienté dans le sens trigonométrique
function vector2 ra_inter(vector2 p; vector2 q; vector2 a; vector2 b)
{
    float x1 = p.x, y1 = p.y, x2 = q.x, y2 = q.y, x3 = a.x, y3 = a.y, x4 = b.x, y4 = b.y;
    float den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4);
    if (abs(den) < 1e-15) return q;
    float t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den;
    return set(x1 + t * (x2 - x1), y1 + t * (y2 - y1));
}
function vector2[] ra_decouper(vector2 poly[]; vector2 clip[])
{
    vector2 out[] = poly;
    int nc = len(clip);
    for (int i = 0; i < nc; i++) {
        vector2 a = clip[i], b = clip[(i + 1) % nc];
        vector2 entree[] = out;
        resize(out, 0);
        int ne = len(entree);
        if (ne == 0) break;
        vector2 S = entree[ne - 1];
        foreach (vector2 E; entree) {
            int e_in = ((b.x - a.x) * (E.y - a.y) - (b.y - a.y) * (E.x - a.x)) >= -1e-12;
            int s_in = ((b.x - a.x) * (S.y - a.y) - (b.y - a.y) * (S.x - a.x)) >= -1e-12;
            if (e_in) {
                if (!s_in) push(out, ra_inter(S, E, a, b));
                push(out, E);
            } else if (s_in) push(out, ra_inter(S, E, a, b));
            S = E;
        }
    }
    return out;
}
function float ra_aire(vector2 P[])
{
    float a = 0;
    int n = len(P);
    for (int i = 0; i < n; i++) { vector2 p = P[i], q = P[(i + 1) % n]; a += p.x * q.y - q.x * p.y; }
    return 0.5 * a;
}
function float[] ra_nombres(string s)
{
    float r[];
    foreach (string w; split(s)) push(r, atof(w));
    return r;
}
// interpolation linéaire d'une table (XS croissant)
function float ra_interp(float XS[]; float YS[]; float x)
{
    int n = len(XS);
    if (x <= XS[0]) return YS[0];
    if (x >= XS[n - 1]) return YS[n - 1];
    int lo = 0, hi = n - 1;
    while (hi - lo > 1) { int m = (lo + hi) / 2; if (XS[m] <= x) lo = m; else hi = m; }
    return lerp(YS[lo], YS[hi], (x - XS[lo]) / max(XS[hi] - XS[lo], 1e-12));
}
// tri de deux tables selon la première
function void ra_trier(export float A[]; export float B[])
{
    int o[] = argsort(A);
    float a2[], b2[];
    foreach (int i; o) { push(a2, A[i]); push(b2, B[i]); }
    A = a2; B = b2;
}
// matériau de peinture de la bibliothèque (même règle que rg::marquages, rg_marquage.h : rg_m_materiau)
function string ra_peinture(string coul; float us)
{
    int c = clamp(int(ceil(3.0 * us - 1e-9)), 0, 3);
    return sprintf("peinture_%s_u%d", coul == "" ? "blanc" : coul, c);
}
"""

# --------------------------------------------------------------------------------------------- raccord des bretelles
VEX_RACCORD = r"""
// raccord (détail ; entrée 0 : sol des routes, entrée 1 : contexte = références (groupe ref), zones (groupe zone),
// nœuds (groupe noeud)) : pour chaque nœud « fourche » (bifurcation du modèle : bretelle d'entrée ou de sortie), décalage
// vertical dz de la bretelle pour que sa chaussée rejoigne celle de la principale au point de jonction (chaque route a
// son propre modèle de Z, ancré à Z = 0 sur sa ligne de référence, rg_niveau.h ; le schéma 0.1 n'exploite pas de profil
// en long) : dz = Z(principale) − Z(bretelle) au point de jonction, mesuré 0,50 m à l'intérieur de chaque chaussée sur
// le sol fabriqué. Profil en long de la bretelle parallèle (choix [G], déclaré).
string rb[]; float dzb[]; string rp[]; string noeuds[]; string genres[];
float decal = chf("../mesure_raccord");
foreach (int pn; expandpointgroup(1, "noeud")) {
    if (point(1, "type", pn) != "fourche") continue;
    string nid = point(1, "id", pn);
    string rr[] = point(1, "routes", pn);
    vector2 J = ra_xy(point(1, "P", pn));
    string b = "", p = "";
    int prb = -1, prp = -1;
    int genre = 0;                       // 1 : entrée (la bretelle finit au nœud), 2 : sortie (elle en part)
    foreach (int pr; expandprimgroup(1, "ref")) {
        string id = prim(1, "id", pr);
        if (find(rr, id) < 0) continue;
        string nd = prim(1, "noeud_debut", pr), nf = prim(1, "noeud_fin", pr);
        if (nf == nid) { b = id; prb = pr; genre = 1; }
        else if (nd == nid) { b = id; prb = pr; genre = 2; }
    }
    foreach (int pr; expandprimgroup(1, "ref")) {
        string id = prim(1, "id", pr);
        if (find(rr, id) >= 0 && id != b) { p = id; prp = pr; }
    }
    if (prb < 0 || prp < 0) continue;
    float SB[], SP[]; vector2 XB[], XP[], GB[], GP[];
    ra_repere(1, prb, SB, XB, GB);
    ra_repere(1, prp, SP, XP, GP);
    float sb = genre == 1 ? SB[-1] - decal : SB[0] + decal;
    vector2 QB = ra_pt(SB, XB, GB, sb, 0.0);
    vector2 stJ = ra_st(SP, XP, GP, ra_pt(SB, XB, GB, genre == 1 ? SB[-1] : SB[0], 0.0));
    vector2 QP = ra_pt(SP, XP, GP, stJ.x + (genre == 1 ? decal : -decal), stJ.y);
    int okb, okp; string mb, mp;
    float zb = ra_z_sol(0, b, QB, 0.0, okb, mb);
    float zp = ra_z_sol(0, p, QP, 0.0, okp, mp);
    if (!okb || !okp) { warning("raccord %s : sol introuvable (bretelle %d, principale %d)", nid, okb, okp); continue; }
    push(rb, b); push(dzb, zp - zb); push(rp, p); push(noeuds, nid); push(genres, genre == 1 ? "entree" : "sortie");
}
s[]@ra_bretelles = rb;
f[]@ra_dz = dzb;
s[]@ra_principales = rp;
s[]@ra_noeuds = noeuds;
s[]@ra_genres = genres;
"""

VEX_APPLIQUER = r"""
// appliquer (point) : Z des points du sol de chaque bretelle décalé de dz (détail ra_dz du raccord).
string rb[] = detail(0, "ra_bretelles");
if (len(rb) == 0) return;
float dz[] = detail(0, "ra_dz");
int prs[] = pointprims(0, @ptnum);
if (len(prs) == 0) return;
int k = find(rb, prim(0, "route", prs[0]));
if (k >= 0) @P.y += dz[k];
"""

# --------------------------------------------------------------------------------------------- musoirs
VEX_MUSOIRS = r"""
// musoirs (détail ; entrée 0 vide, 1 limites (rg::profils), 2 sol des routes raccordées, 3 contexte) : pour chaque
// bifurcation (nœud « fourche ») :
//  - SOL du musoir : surface entre le bord de la plate-forme de la principale et celui de la bretelle, de la jonction
//    jusqu'au bout du terre-plein latéral du modèle (îlot « musoir ») ; revêtement de la chaussée voisine entre la
//    jonction et le point à 5,00 m (étendue de l'îlot peint du modèle), celui de la berme voisine au-delà (terre-plein
//    latéral de plain-pied : sur autoroute, pas de bordure, bordure_par_contexte("autoroute"), RF-GV-PON-005) ; Z
//    raccordés aux deux sols fabriqués ;
//  - MARQUES : zone intérieure aux deux lignes de contour (rives de la principale et de la bretelle, bord intérieur
//    du trait) réduite de 2u (RF-MQ-MUS-01) jusqu'au point à 5,00 m ; aplat là où elle a moins de 0,30 m
//    (RF-MQ-HACH-03), chevrons ailleurs (RF-MQ-HACH-02 : deux familles symétriques par rapport à la bissectrice,
//    inclinées 2 pour 1 sur elle, pointe vers le conducteur ; bandes de 0,50 espacées de 1,35, DEF-020 ; algorithme du
//    dossier 08, geometrie_gabarits.chevrons_zone).
float ds = chf("../pas_musoir");
float degu = chf("../degagement_u");
float aplat = chf("../hach_aplat");
float bande = chf("../hach_bande");
float vide = chf("../hach_espacement");
float pente = tan(radians(chf("../hach_angle")));     // 1/2 : « 2 pour 1 »
float pas = bande + vide;
string attrs_s[] = {"pj_entite", "id", "classe", "type", "gabarit", "materiau_id", "couleur", "route", "cle", "modulation",
                    "bande_id", "pj_couche", "pj_maillage", "partie_musoir", "carrefour"};
foreach (string a; attrs_s) addprimattrib(0, a, "");
addprimattrib(0, "usure", 0.0); addprimattrib(0, "couverture", 1.0); addprimattrib(0, "graine", 0);
addprimattrib(0, "partie", 0); addprimattrib(0, "anneau", 0); addprimattrib(0, "pj_region", -1);
addprimattrib(0, "largeur_m", 0.0); addprimattrib(0, "s0", 0.0); addprimattrib(0, "s1", 0.0);
addprimattrib(0, "rang", 0); addprimattrib(0, "bande_sol", -1); addprimattrib(0, "rg_ligne", 0);
addprimattrib(0, "z_type", 0); addprimattrib(0, "visible", 1); addprimattrib(0, "section", -1); addprimattrib(0, "bande", -1);
addprimattrib(0, "priorite", 0); addprimattrib(0, "chaine", -1);
addpointattrib(0, "s", 0.0); addpointattrib(0, "t", 0.0); addpointattrib(0, "N", {0, 1, 0});
int g_sol = 0;
string c_noeuds[], c_genres[], c_cles[];
float c_sJ[], c_s5[], c_sfar[], c_sa[], c_send[], c_aire_sol[], c_aire_tpl[], c_n_chev[], c_aire_aplat[], c_angle[];
float c_u[], c_wP[], c_wB[];

foreach (int pn; expandpointgroup(3, "noeud")) {
    if (point(3, "type", pn) != "fourche") continue;
    string nid = point(3, "id", pn);
    string cid = point(3, "carrefour", pn);
    string rr[] = point(3, "routes", pn);
    string b = "", p = "";
    int prb = -1, prp = -1, genre = 0;
    foreach (int pr; expandprimgroup(3, "ref")) {
        string id = prim(3, "id", pr);
        if (find(rr, id) < 0) continue;
        if (prim(3, "noeud_fin", pr) == nid) { b = id; prb = pr; genre = 1; }
        else if (prim(3, "noeud_debut", pr) == nid) { b = id; prb = pr; genre = 2; }
    }
    foreach (int pr; expandprimgroup(3, "ref")) {
        string id = prim(3, "id", pr);
        if (find(rr, id) >= 0 && id != b) { p = id; prp = pr; }
    }
    if (prb < 0 || prp < 0) continue;
    float SP[], SB[]; vector2 XP[], GP[], XB[], GB[];
    ra_repere(3, prp, SP, XP, GP);
    ra_repere(3, prb, SB, XB, GB);
    // jonction (extrémité de la bretelle) dans le repère de la principale ; côté de la bretelle
    vector2 stJ = ra_st(SP, XP, GP, ra_pt(SB, XB, GB, genre == 1 ? SB[-1] : SB[0], 0.0));
    float sJ = stJ.x;
    int cote = stJ.y < 0 ? -1 : 1;                 // bretelle à droite (−1) ou à gauche (+1) de la principale
    int dir = genre == 1 ? -1 : 1;                 // de la jonction vers le musoir, le long de la principale
    int sens_trafic = cote < 0 ? 1 : -1;           // circulation à droite : le musoir longe le sens « avant » si à droite
    // étendue du musoir : îlot peint (point à 5,00 m) et terre-plein latéral (îlot « musoir ») du modèle
    float s5 = sJ, sfar = sJ;
    foreach (int pz; expandprimgroup(3, "zone")) {
        string props = prim(3, "props", pz);
        if (find(props, "\"carrefour\":\"" + cid + "\"") < 0) continue;
        string ty = prim(3, "type", pz);
        foreach (int q; primpoints(3, pz)) {
            vector2 st = ra_st(SP, XP, GP, ra_xy(point(3, "P", q)));
            if (ty == "ilot_peint") { if (dir * (st.x - s5) > 0) s5 = st.x; }
            if (dir * (st.x - sfar) > 0) sfar = st.x;
        }
    }
    if (abs(s5 - sJ) < 1.0) { warning("musoir %s : îlot peint absent du modèle", cid); continue; }
    // le point à 5,00 m de l'îlot peint (échantillonné au pas du compilateur) est ramené sur la borne de section de la
    // principale la plus proche à moins de 0,50 m (reprise de la BAU au nez : la zone peinte s'arrête où la BAU reprend)
    {
        float best = 0.5;
        float s5b = s5;
        for (int pr = 0; pr < nprimitives(1); pr++) {
            if (prim(1, "route", pr) != p) continue;
            float bs[] = array(float(prim(1, "s0", pr)), float(prim(1, "s1", pr)));
            foreach (float v; bs) if (abs(v - s5) < best) { best = abs(v - s5); s5b = v; }
        }
        s5 = s5b;
    }
    // bords de la bretelle (plate-forme : limite extrême côté principale ; ligne de contour : limite marquée extrême)
    // ramenés dans le repère de la principale
    int coteB = -1;                                 // côté de la bretelle tourné vers la principale
    {
        vector2 stPB = ra_st(SB, XB, GB, ra_pt(SP, XP, GP, sJ + dir * 5.0, stJ.y));
        vector2 stPP = ra_st(SB, XB, GB, ra_pt(SP, XP, GP, sJ + dir * 5.0, stJ.y - cote * 10.0));
        coteB = (stPP.y - stPB.y) > 0 ? 1 : -1;
    }
    float BOs[], BOt[], BRs[], BRt[], BRw[];
    float wB = 0.0, usB = 0.0; string coulB = "blanc";
    for (int pr = 0; pr < nprimitives(1); pr++) {
        if (prim(1, "route", pr) != b) continue;
        int pts[] = primpoints(1, pr);
        float sm = 0.5 * (float(prim(1, "s0", pr)) + float(prim(1, "s1", pr)));
        int ext = ra_limite(1, b, sm, coteB, 0) == pr;
        int mar = ra_limite(1, b, sm, coteB, 1) == pr;
        if (!ext && !mar) continue;
        if (mar) {
            dict D = json_loads("{\"m\":" + string(prim(1, "marquages", pr)) + "}", 0);
            dict E[] = D["m"];
            if (len(E) > 0) {
                float um = isvalidindex(E[0], "u_m") ? float(E[0]["u_m"]) : chf("../u_defaut");
                wB = max(wB, float(E[0]["largeur_u"]) * um);
                if (isvalidindex(E[0], "usure")) usB = float(E[0]["usure"]);
                if (isvalidindex(E[0], "couleur")) coulB = E[0]["couleur"];
            }
        }
        foreach (int q; pts) {
            vector2 st = ra_st(SP, XP, GP, ra_xy(point(1, "P", q)));
            if (dir * (st.x - sJ) < -2.0 || dir * (st.x - sfar) > 2.0) continue;
            if (ext) { push(BOs, st.x); push(BOt, st.y); }
            if (mar) { push(BRs, st.x); push(BRt, st.y); }
        }
    }
    ra_trier(BOs, BOt);
    ra_trier(BRs, BRt);
    if (len(BOs) < 2 || len(BRs) < 2) { warning("musoir %s : bords de la bretelle introuvables", cid); continue; }
    // ligne de contour de la principale : largeur et usure
    float wP = 0.0, usP = 0.0; string coulP = "blanc";
    {
        int prr = ra_limite(1, p, 0.5 * (sJ + s5), cote, 1);
        if (prr >= 0) {
            dict D = json_loads("{\"m\":" + string(prim(1, "marquages", prr)) + "}", 0);
            dict E[] = D["m"];
            if (len(E) > 0) {
                float um = isvalidindex(E[0], "u_m") ? float(E[0]["u_m"]) : chf("../u_defaut");
                wP = float(E[0]["largeur_u"]) * um;
                if (isvalidindex(E[0], "usure")) usP = float(E[0]["usure"]);
                if (isvalidindex(E[0], "couleur")) coulP = E[0]["couleur"];
            }
        }
    }
    float u2 = degu * (wP > 0 ? wP / 3.0 : chf("../u_defaut"));     // 2u (u de la ligne de contour 3u)
    // ------------------------------------------------------------ sol du musoir
    // abscisses : pas régulier, bornes des sections de la principale, point à 5 m, bouts
    float lo = min(sJ, sfar), hi = max(sJ, sfar);
    float BK[];
    for (float s = lo; s < hi; s += ds) push(BK, s);
    push(BK, hi); push(BK, s5);
    for (int pr = 0; pr < nprimitives(1); pr++) {
        if (prim(1, "route", pr) != p) continue;
        float a0 = prim(1, "s0", pr), a1 = prim(1, "s1", pr);
        if (a0 > lo && a0 < hi) push(BK, a0);
        if (a1 > lo && a1 < hi) push(BK, a1);
    }
    BK = sort(BK);
    float aire_sol = 0.0, aire_tpl = 0.0;
    for (int k = 0; k < len(BK) - 1; k++) {
        float a = BK[k], bb = BK[k + 1];
        if (bb - a < 1e-4) continue;
        float eps = min(1e-4, 0.25 * (bb - a));
        int la = ra_limite(1, p, a + eps, cote, 0), lb_ = ra_limite(1, p, bb - eps, cote, 0);
        if (la < 0 || lb_ < 0) continue;
        float tpa = ra_lim_t(1, la, a + eps), tpb = ra_lim_t(1, lb_, bb - eps);
        // bord de la bretelle à l'abscisse (interpolation sur les points triés)
        float TB[] = array(ra_interp(BOs, BOt, a), ra_interp(BOs, BOt, bb));
        // largeurs (côté de la bretelle : t décroissant si cote < 0)
        float wa = cote < 0 ? tpa - TB[0] : TB[0] - tpa;
        float wb = cote < 0 ? tpb - TB[1] : TB[1] - tpb;
        if (wa <= 1e-4 && wb <= 1e-4) continue;
        if (wa < 0) TB[0] = tpa;
        if (wb < 0) TB[1] = tpb;
        int peint = (dir * ((a + bb) * 0.5 - s5) < 0);       // entre la jonction et le point à 5 m
        float sm = 0.5 * (a + bb);
        // matériau : revêtement de la principale le long du bord (chaussée ou berme)
        int okm; string mat;
        float tm = ra_lim_t(1, ra_limite(1, p, sm, cote, 0), sm);
        ra_z_sol(2, p, ra_pt(SP, XP, GP, sm, tm - cote * 0.05), 0.0, okm, mat);
        if (mat == "") mat = peint ? "enrobe_bbsg_ancien" : "gazon_tondu";
        vector2 Q[] = array(set(a, tpa), set(bb, tpb), set(bb, TB[1]), set(a, TB[0]));
        int ids[];
        for (int q = 0; q < 4; q++) {
            vector2 st = Q[q];
            vector2 xy = ra_pt(SP, XP, GP, st.x, st.y);
            int ok; string mm;
            float z;
            if (q < 2) z = ra_z_sol(2, p, ra_pt(SP, XP, GP, st.x, st.y - cote * 0.02), 0.0, ok, mm);
            else {
                // intérieur de la bretelle : 2 cm au-delà de son bord, dans la direction opposée à la principale
                z = ra_z_sol(2, b, ra_pt(SP, XP, GP, st.x, st.y + cote * 0.02), 0.0, ok, mm);
                if (!ok) z = ra_z_sol(2, p, ra_pt(SP, XP, GP, st.x, Q[q == 2 ? 1 : 0].y - cote * 0.02), 0.0, ok, mm);
            }
            int pt = addpoint(0, ra_h(xy, z));
            setpointattrib(0, "s", pt, st.x);
            setpointattrib(0, "t", pt, st.y);
            push(ids, pt);
        }
        int pr = addprim(0, "poly", ids);
        setprimgroup(0, "sol_musoir", pr, 1);
        string part = peint ? "musoir" : "terre_plein_lateral";
        setprimattrib(0, "classe", pr, part);
        setprimattrib(0, "partie_musoir", pr, part);
        setprimattrib(0, "materiau_id", pr, mat);
        setprimattrib(0, "z_type", pr, 10);
        setprimattrib(0, "visible", pr, 1);
        setprimattrib(0, "route", pr, cid);
        setprimattrib(0, "carrefour", pr, cid);
        setprimattrib(0, "bande_id", pr, part);
        setprimattrib(0, "pj_couche", pr, "PJ_Sol");
        setprimattrib(0, "pj_entite", pr, "SOL_" + re_replace("[^A-Za-z0-9]", "_", cid));
        setprimattrib(0, "pj_maillage", pr, mat);
        float ar = abs(ra_aire(Q));
        if (peint) aire_sol += ar; else aire_tpl += ar;
    }
    // ------------------------------------------------------------ marques : zone intérieure aux contours, réduite de 2u
    // bord intérieur des deux lignes : t_hi (côté principale), t_lo (côté bretelle) ; repère : t croissant vers la
    // principale (sg = −cote)
    float sg = -cote;
    float s_end = s5 - dir * u2;
    float ZS[], ZH[], ZL[];
    float l0 = min(sJ, s_end), l1 = max(sJ, s_end);
    for (float s = l0; s < l1; s += 0.5) push(ZS, s);
    push(ZS, l1);
    ZS = sort(ZS);
    foreach (float s; ZS) {
        int lp = ra_limite(1, p, s + dir * 1e-4, cote, 1);
        float tp = lp >= 0 ? ra_lim_t(1, lp, s + dir * 1e-4) : 0.0;
        float tb = ra_interp(BRs, BRt, s);
        // dans le repère t' = sg·t : principale en haut
        push(ZH, sg * tp - 0.5 * wP - u2);
        push(ZL, sg * tb + 0.5 * wB + u2);
    }
    // début de la zone (largeur > 0), puis de la partie hachurée (largeur ≥ aplat)
    float sa = -1e30, s0z = -1e30;
    int nz = len(ZS);
    // parcours depuis la jonction
    int i0 = dir > 0 ? 0 : nz - 1, i1 = dir > 0 ? nz : -1;
    for (int i = i0; i != i1; i += dir) {
        float w = ZH[i] - ZL[i];
        if (s0z < -1e29 && w > 0) {
            int j = i - dir;
            float wj = (j >= 0 && j < nz) ? ZH[j] - ZL[j] : 0.0;
            s0z = (j >= 0 && j < nz) ? lerp(ZS[j], ZS[i], (0 - wj) / max(w - wj, 1e-9)) : ZS[i];
        }
        if (sa < -1e29 && w >= aplat) {
            int j = i - dir;
            float wj = (j >= 0 && j < nz) ? ZH[j] - ZL[j] : 0.0;
            sa = (j >= 0 && j < nz) ? lerp(ZS[j], ZS[i], (aplat - wj) / max(w - wj, 1e-9)) : ZS[i];
        }
    }
    if (s0z < -1e29 || sa < -1e29) { warning("musoir %s : zone de chevrons vide", cid); continue; }
    string mat_p = ra_peinture(coulP, max(usP, usB));
    float us_p = max(usP, usB);
    string base_id = "MQ_" + re_replace("[^A-Za-z0-9]", "_", cid);
    int rang = 0;
    // ---- aplat : de s0z à sa (largeur < 0,30 m)
    {
        float AS[];
        float a0 = min(s0z, sa), a1 = max(s0z, sa);
        for (float s = a0; s < a1; s += 0.5) push(AS, s);
        push(AS, a1);
        vector2 POL[];
        foreach (float s; AS) push(POL, set(s, ra_interp(ZS, ZL, s)));
        for (int i = len(AS) - 1; i >= 0; i--) push(POL, set(AS[i], max(ra_interp(ZS, ZH, AS[i]), ra_interp(ZS, ZL, AS[i]))));
        if (len(POL) >= 3 && abs(ra_aire(POL)) > 1e-5) {
            int ids[];
            foreach (vector2 v; POL) {
                vector2 xy = ra_pt(SP, XP, GP, v.x, sg * v.y);
                int pt = addpoint(0, ra_h(xy, 0.0));
                setpointattrib(0, "s", pt, v.x); setpointattrib(0, "t", pt, sg * v.y);
                push(ids, pt);
            }
            if (sg < 0) ids = reverse(ids);           // sens trigonométrique en (x, y)
            int pr = addprim(0, "poly", ids);
            setprimgroup(0, "marques_musoir", pr, 1);
            string ent = base_id + "_aplat";
            setprimattrib(0, "pj_entite", pr, ent); setprimattrib(0, "id", pr, ent);
            setprimattrib(0, "classe", pr, "aplat"); setprimattrib(0, "type", pr, "aplat_pointe");
            setprimattrib(0, "materiau_id", pr, mat_p); setprimattrib(0, "couleur", pr, coulP);
            setprimattrib(0, "usure", pr, us_p); setprimattrib(0, "graine", pr, random_shash(ent) & 0x7fffffff);
            setprimattrib(0, "route", pr, p); setprimattrib(0, "carrefour", pr, cid);
            setprimattrib(0, "s0", pr, a0); setprimattrib(0, "s1", pr, a1); setprimattrib(0, "rang", pr, rang++);
            push(c_aire_aplat, abs(ra_aire(POL)));
        } else push(c_aire_aplat, 0.0);
    }
    // ---- chevrons : de sa à s_end ; bissectrice = milieu de la zone (corde) orientée dans le sens de circulation
    float c0 = min(sa, s_end), c1 = max(sa, s_end);
    vector2 M0 = set(c0, 0.5 * (ra_interp(ZS, ZH, c0) + ra_interp(ZS, ZL, c0)));
    vector2 M1 = set(c1, 0.5 * (ra_interp(ZS, ZH, c1) + ra_interp(ZS, ZL, c1)));
    vector2 ax = normalize(M1 - M0) * sens_trafic;               // repère (s, t') : t' = sg·t
    // en repère (s, t'), le sens trigonométrique est conservé si sg > 0 ; sinon l'axe t' est retourné : on calcule en
    // (s, t') puis on revient à (s, t) en fin
    vector2 qv = ra_gauche(ax);
    vector2 sommet = sens_trafic > 0 ? M0 : M1;                  // ancrage : pointe amont de la zone (début des chevrons)
    // tranches convexes de la zone : demi-zones haute (côté principale) et basse, coupées au pas de 1 m
    float CS[];
    for (float s = c0; s < c1; s += 1.0) push(CS, s);
    push(CS, c1);
    int nch = 0;
    float ang_mes = 0.0;
    int familles[] = {1, -1};
    foreach (int famille; familles) {
        // direction des bandes : 2·axe + famille·q (miroir pour la seconde famille)
        vector2 d = normalize(pente > 0 ? (ax / pente + famille * qv) : ax);
        if (famille < 0) d = -d;
        vector2 nrm = ra_gauche(d);
        ang_mes = degrees(acos(clamp(abs(dot(d, ax)), 0.0, 1.0)));
        // bornes des projections de la zone
        float pmin = 1e30, pmax = -1e30, emin = 1e30, emax = -1e30;
        for (int k = 0; k < len(CS); k++) {
            float s = CS[k];
            vector2 hh = set(s, ra_interp(ZS, ZH, s)), ll = set(s, ra_interp(ZS, ZL, s));
            vector2 hl[] = array(hh, ll);
            foreach (vector2 v; hl) {
                pmin = min(pmin, dot(v, nrm)); pmax = max(pmax, dot(v, nrm));
                emin = min(emin, dot(v, d)); emax = max(emax, dot(v, d));
            }
        }
        emin -= 1.0; emax += 1.0;
        float o = dot(sommet, nrm);
        float sb = o + floor((pmin - o) / pas) * pas - pas;
        int kb = 0;
        while (sb < pmax) {
            vector2 band[] = array(sb * nrm + emin * d, (sb + bande) * nrm + emin * d,
                                   (sb + bande) * nrm + emax * d, sb * nrm + emax * d);
            if (ra_aire(band) < 0) band = reverse(band);
            string ent = sprintf("%s_chevron_%s%03d", base_id, famille > 0 ? "h" : "b", kb);
            int pieces = 0;
            for (int k = 0; k < len(CS) - 1; k++) {
                float sA = CS[k], sB = CS[k + 1];
                float hA = ra_interp(ZS, ZH, sA), hB = ra_interp(ZS, ZH, sB);
                float lA = ra_interp(ZS, ZL, sA), lB = ra_interp(ZS, ZL, sB);
                float mA = 0.5 * (hA + lA), mB = 0.5 * (hB + lB);
                // demi-zone de la famille : au-dessus (famille > 0 si q pointe vers la principale) ou au-dessous
                int haut = (dot(qv, set(0.0, 1.0)) > 0) == (famille > 0);
                vector2 cl[] = haut ? array(set(sA, mA), set(sB, mB), set(sB, hB), set(sA, hA))
                                    : array(set(sA, lA), set(sB, lB), set(sB, mB), set(sA, mA));
                if (ra_aire(cl) < 0) cl = reverse(cl);
                if (abs(ra_aire(cl)) < 1e-6) continue;
                vector2 pc[] = ra_decouper(band, cl);
                if (len(pc) < 3 || abs(ra_aire(pc)) < 1e-4) continue;
                int ids[];
                foreach (vector2 v; pc) {
                    vector2 xy = ra_pt(SP, XP, GP, v.x, sg * v.y);
                    int pt = addpoint(0, ra_h(xy, 0.0));
                    setpointattrib(0, "s", pt, v.x); setpointattrib(0, "t", pt, sg * v.y);
                    push(ids, pt);
                }
                if (sg < 0) ids = reverse(ids);
                int pr = addprim(0, "poly", ids);
                setprimgroup(0, "marques_musoir", pr, 1);
                setprimattrib(0, "pj_entite", pr, ent); setprimattrib(0, "id", pr, sprintf("%s_%02d", ent, pieces));
                setprimattrib(0, "classe", pr, "chevron"); setprimattrib(0, "type", pr, famille > 0 ? "chevron_haut" : "chevron_bas");
                setprimattrib(0, "materiau_id", pr, mat_p); setprimattrib(0, "couleur", pr, coulP);
                setprimattrib(0, "usure", pr, us_p); setprimattrib(0, "graine", pr, random_shash(ent) & 0x7fffffff);
                setprimattrib(0, "route", pr, p); setprimattrib(0, "carrefour", pr, cid);
                setprimattrib(0, "largeur_m", pr, bande); setprimattrib(0, "rang", pr, rang);
                setprimattrib(0, "s0", pr, sA); setprimattrib(0, "s1", pr, sB);
                pieces++;
            }
            if (pieces > 0) { nch++; rang++; }
            sb += pas;
            kb++;
        }
    }
    // ---- demi-lignes de contour côté musoir : rg::marquages ne peint que la moitié intérieure d'une ligne posée sur la
    // limite extérieure d'un profil (rien au-delà) ; la moitié côté musoir est posée ici sur le sol du musoir, là où la
    // ligne de contour est le bord de la plate-forme (principale : de la jonction au point à 5 m ; bretelle : de la
    // jonction au bout du terre-plein latéral). Largeur : moitié de la ligne (3u/2), continue (RF-MQ-MUS-01).
    {
        string qui[] = array("P", "B");
        foreach (string q; qui) {
            float wq = q == "P" ? wP : wB;
            if (wq <= 0) continue;
            float e0 = min(sJ, sfar), e1 = max(sJ, sfar);
            float SQ[];
            for (float sv = e0; sv < e1; sv += 1.0) push(SQ, sv);
            push(SQ, e1);
            int run[];             // indices consécutifs où la demi-ligne existe
            float TL[], GAP[];
            for (int k = 0; k < len(SQ); k++) {
                float sv = SQ[k];
                float tl = 0.0;
                int ok = 0;
                // bord de la plate-forme principale (même s'il ne porte pas la demi-ligne) et bord de la bretelle
                float se = sv + dir * 1e-4;
                int lm = ra_limite(1, p, se, cote, 1), lo_ = ra_limite(1, p, se, cote, 0);
                float tp = (lm >= 0 && lm == lo_) ? ra_lim_t(1, lm, se) : 1e30;
                // écart borné aussi par la limite marquée extrême de la principale quand elle n'est pas le bord de la
                // plate-forme (voie d'insertion ouverte au-delà) : la demi-ligne de la bretelle ne déborde pas sur sa rive
                float tpm = lm >= 0 ? ra_lim_t(1, lm, se) : 1e30;
                float tb = ra_interp(BRs, BRt, sv);
                if (q == "P") {
                    if (tp < 1e29 && dir * (sv - s5) <= 1e-6) { ok = 1; tl = tp; }
                } else {
                    ok = 1;
                    tl = tb;
                }
                push(TL, ok ? tl : 1e30);
                // écart signé : nul (et non plus grand) une fois les deux bords croisés au-delà de la jonction
                push(GAP, tpm < 1e29 ? max(0.0, cote * (tb - tpm)) : 1e30);
            }
            int pieces = 0;
            for (int k = 0; k < len(SQ) - 1; k++) {
                if (TL[k] > 1e29 || TL[k + 1] > 1e29) continue;
                // côté du musoir : principale -> vers la bretelle (cote) ; bretelle -> vers la principale (−cote) ;
                // demi-largeur bornée à la moitié de l'écart entre les deux bords (correction après le contrôle de
                // l'étape 2 : près de la jonction les deux demi-lignes se recouvraient entre elles et recouvraient la
                // rive de l'autre chaussée ; elles se rejoignent maintenant au milieu de l'écart)
                float sg_ = q == "P" ? cote : -cote;
                float o0 = sg_ * min(0.5 * wq, 0.5 * GAP[k]), o1 = sg_ * min(0.5 * wq, 0.5 * GAP[k + 1]);
                if (abs(o0) < 1e-3 && abs(o1) < 1e-3) continue;
                vector2 POL[] = array(set(SQ[k], TL[k]), set(SQ[k + 1], TL[k + 1]), set(SQ[k + 1], TL[k + 1] + o1), set(SQ[k], TL[k] + o0));
                if (ra_aire(POL) < 0) POL = reverse(POL);
                int ids[];
                foreach (vector2 v; POL) {
                    vector2 xy = ra_pt(SP, XP, GP, v.x, v.y);
                    int pt = addpoint(0, ra_h(xy, 0.0));
                    setpointattrib(0, "s", pt, v.x); setpointattrib(0, "t", pt, v.y);
                    push(ids, pt);
                }
                int pr = addprim(0, "poly", ids);
                setprimgroup(0, "marques_musoir", pr, 1);
                string ent = base_id + "_contour_" + q;
                setprimattrib(0, "pj_entite", pr, ent); setprimattrib(0, "id", pr, sprintf("%s_%03d", ent, pieces));
                setprimattrib(0, "classe", pr, "ligne_contour"); setprimattrib(0, "type", pr, "demi_ligne_continue");
                setprimattrib(0, "modulation", pr, "continue");
                setprimattrib(0, "materiau_id", pr, mat_p); setprimattrib(0, "couleur", pr, coulP);
                setprimattrib(0, "usure", pr, us_p); setprimattrib(0, "graine", pr, random_shash(ent) & 0x7fffffff);
                setprimattrib(0, "route", pr, q == "P" ? p : b); setprimattrib(0, "carrefour", pr, cid);
                setprimattrib(0, "largeur_m", pr, 0.5 * wq);
                setprimattrib(0, "s0", pr, SQ[k]); setprimattrib(0, "s1", pr, SQ[k + 1]);
                pieces++;
            }
        }
    }
    push(c_noeuds, nid); push(c_genres, genre == 1 ? "entree" : "sortie"); push(c_cles, cid + "|" + p + "|" + b);
    push(c_sJ, sJ); push(c_s5, s5); push(c_sfar, sfar); push(c_sa, sa); push(c_send, s_end);
    push(c_aire_sol, aire_sol); push(c_aire_tpl, aire_tpl); push(c_n_chev, float(nch)); push(c_angle, ang_mes);
    push(c_u, wP / 3.0); push(c_wP, wP); push(c_wB, wB);
}
s[]@ra_m_noeuds = c_noeuds; s[]@ra_m_genres = c_genres; s[]@ra_m_cles = c_cles;
f[]@ra_m_sJ = c_sJ; f[]@ra_m_s5 = c_s5; f[]@ra_m_sfar = c_sfar; f[]@ra_m_s_aplat = c_sa; f[]@ra_m_s_fin_chevrons = c_send;
f[]@ra_m_aire_musoir = c_aire_sol; f[]@ra_m_aire_tpl = c_aire_tpl; f[]@ra_m_chevrons = c_n_chev;
f[]@ra_m_aire_aplat = c_aire_aplat; f[]@ra_m_angle_bissectrice_deg = c_angle;
f[]@ra_m_u = c_u; f[]@ra_m_largeur_contour_principale = c_wP; f[]@ra_m_largeur_contour_bretelle = c_wB;
"""

# --------------------------------------------------------------------------------------------- séparateurs
VEX_SEPARATEURS = r"""
// séparateurs (détail ; entrée 0 vide, 1 limites (rg::profils), 2 sol des routes raccordées) : dispositifs de retenue
// le long des limites « separateur » du modèle :
//  - GBA de largeur ≥ 0,55 m ou DBA : séparateur béton double (contour retenue_DBA du catalogue : base 0,60, H 0,81),
//    centré sur la limite ; GBA plus étroite : séparateur simple (contour retenue_GBA : base 0,48), face au trafic ;
//  - glissière : modèle du séparateur s'il est dit (GS2, GS4, DE2), sinon paramètre « glissière par défaut » (choix
//    [G]) ; pièces du catalogue (lisse profil A balayée en continu le long de la limite ; supports C100, écarteurs,
//    boulons et recouvrements par module de 4 m), face de la lisse sur la limite, côté du trafic (surface revêtue de la
//    chaussée : BDG, BAU, voie) ; supports derrière.
// Z : sol fabriqué au droit de la limite. Base des contours béton descendue de « encastrement » (cachée dans le sol).
addprimattrib(0, "materiau_id", ""); addprimattrib(0, "classe", ""); addprimattrib(0, "id", "");
addprimattrib(0, "pj_entite", ""); addprimattrib(0, "pj_couche", ""); addprimattrib(0, "pj_maillage", "");
addprimattrib(0, "route", ""); addprimattrib(0, "modele", ""); addprimattrib(0, "limite", -1);
addpointattrib(0, "s", 0.0);
string c_ids[], c_modeles[], c_routes[], c_cotes[];
float c_l[], c_n_mod[], c_base[], c_haut[], c_pas[], c_dt[];
float enc = chf("../encastrement");
string trafic[] = split(chs("../classes_trafic"), " ,");
for (int pr = 0; pr < nprimitives(1); pr++) {
    string sep = prim(1, "separateur", pr);
    if (sep == "") continue;
    dict D = json_loads(sep, 0);
    string ty = isvalidindex(D, "type") ? string(D["type"]) : "";
    float larg = isvalidindex(D, "largeur_m") ? float(D["largeur_m"]) : -1.0;
    string mod = isvalidindex(D, "modele") ? string(D["modele"]) : "";
    string rid = prim(1, "route", pr);
    int lim = prim(1, "limite", pr);
    int pts[] = primpoints(1, pr);
    int n = len(pts);
    if (n < 2) continue;
    vector2 C[]; float S[], Z[];
    foreach (int q; pts) { push(C, ra_xy(point(1, "P", q))); push(S, float(point(1, "s", q))); }
    // tangentes et normales à gauche
    vector2 T[], NL[];
    for (int i = 0; i < n; i++) {
        vector2 t = i == 0 ? C[1] - C[0] : (i == n - 1 ? C[n - 1] - C[n - 2] : normalize(C[i] - C[i - 1]) + normalize(C[i + 1] - C[i]));
        t = normalize(t);
        push(T, t); push(NL, ra_gauche(t));
    }
    // côté du trafic : classe du sol à 0,50 m de part et d'autre (milieu de la limite)
    int im = n / 2;
    int pg = -1, pd = -1;
    vector pos; vector uvw;
    pg = intersect(2, ra_h(C[im] + 0.5 * NL[im], 50.0), set(0, -100, 0), pos, uvw);
    pd = intersect(2, ra_h(C[im] - 0.5 * NL[im], 50.0), set(0, -100, 0), pos, uvw);
    string clg = pg >= 0 ? prim(2, "classe", pg) : "", cld = pd >= 0 ? prim(2, "classe", pd) : "";
    int tg = find(trafic, clg) >= 0, td = find(trafic, cld) >= 0;
    int face = tg && !td ? 1 : (td && !tg ? -1 : 0);        // trafic à gauche (1), à droite (−1), des deux côtés (0)
    // Z au droit de la limite
    for (int i = 0; i < n; i++) {
        int ok; string mm;
        float z = ra_z_sol(2, rid, C[i], 0.0, ok, mm);
        if (!ok) z = i > 0 ? Z[i - 1] : 0.0;
        push(Z, z);
    }
    // repère de pose : « dos » B = côté opposé au trafic (simple), normale à droite pour un séparateur double
    vector2 B[];
    for (int i = 0; i < n; i++) push(B, face > 0 ? -NL[i] : NL[i] * (face < 0 ? 1.0 : -1.0));
    string id0 = sprintf("RET_%s_%s_L%d", re_replace("[^A-Za-z0-9]", "_", rid), itoa(prim(1, "section", pr)), lim);
    float L = 0.0;
    for (int i = 1; i < n; i++) L += length(C[i] - C[i - 1]);
    // ------------------------------------------------ béton : contour balayé
    if (ty == "GBA" || ty == "DBA" || ty == "LBA" || ty == "MVL") {
        string nom = ty;
        if (ty == "GBA" && larg >= chf("../largeur_dba_min")) nom = "DBA";
        string cont = chs("../contour_" + tolower(nom));
        if (cont == "") { warning("séparateur %s : contour %s absent", id0, nom); continue; }
        float cv[] = ra_nombres(cont);
        int k = len(cv) / 2;
        float U[], V[];
        float umin = 1e9, umax = -1e9, vmax = -1e9;
        for (int j = 0; j < k; j++) { umin = min(umin, cv[2 * j]); umax = max(umax, cv[2 * j]); vmax = max(vmax, cv[2 * j + 1]); }
        float cen = 0.5 * (umin + umax);
        for (int j = 0; j < k; j++) {
            push(U, cv[2 * j] - cen);                                   // centré sur la limite
            push(V, cv[2 * j + 1] <= 1e-9 ? -enc : cv[2 * j + 1]);       // base encastrée
        }
        int anneaux[];
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < k; j++) {
                vector2 xy = C[i] + B[i] * U[j];
                int pt = addpoint(0, ra_h(xy, Z[i] + V[j]));
                setpointattrib(0, "s", pt, S[i]);
                push(anneaux, pt);
            }
        }
        for (int i = 0; i < n - 1; i++) {
            for (int j = 0; j < k; j++) {
                int j2 = (j + 1) % k;
                int q[] = array(anneaux[i * k + j], anneaux[(i + 1) * k + j], anneaux[(i + 1) * k + j2], anneaux[i * k + j2]);
                int f = addprim(0, "poly", q);
                setprimattrib(0, "classe", f, "separateur_beton");
            }
        }
        // bouts : seulement aux extrémités de la route (une jonction de sections n'est pas un bout)
        float Lr = prim(1, "longueur_m", pr);
        int bouts[] = array(0, n - 1);
        foreach (int e; bouts) {
            int bout = (e == 0 && S[0] <= 1e-4) || (e == n - 1 && S[n - 1] >= Lr - 1e-4);
            if (!bout) continue;
            int q[];
            for (int j = 0; j < k; j++) push(q, anneaux[e * k + j]);
            if (e == 0) q = reverse(q);
            int f = addprim(0, "poly", q);
            setprimattrib(0, "classe", f, "separateur_beton");
        }
        // attributs des faces de ce séparateur
        push(c_ids, id0); push(c_modeles, nom); push(c_routes, rid); push(c_cotes, face == 0 ? "double" : (face > 0 ? "gauche" : "droite"));
        push(c_l, L); push(c_n_mod, 0.0); push(c_base, umax - umin); push(c_haut, vmax); push(c_pas, 0.0); push(c_dt, 0.0);
        setdetailattrib(0, "ra_dernier", id0 + "|" + nom + "|" + rid + "|" + chs("../materiau_beton"));
        continue;
    }
    // ------------------------------------------------ glissière : pièces du catalogue
    if (ty == "glissiere" || ty == "glissière") {
        string nom = mod != "" ? toupper(mod) : chs("../glissiere_defaut");
        string pieces = chs("../pieces_" + tolower(nom));
        if (pieces == "") { warning("glissière %s : pièces %s absentes", id0, nom); continue; }
        if (face == 0) face = 1;
        float mod_l = chf("../module_glissiere");
        // repère courbe : abscisse curviligne le long de la limite
        float A[]; push(A, 0.0);
        for (int i = 1; i < n; i++) push(A, A[-1] + length(C[i] - C[i - 1]));
        string lignes[] = split(re_replace("\n", ";", pieces), ";");
        int n_mod = int(floor(A[-1] / mod_l + 1e-6));
        float h_haut = 0.0;
        foreach (string ligne; lignes) {
            string tk[] = split(ligne);
            if (len(tk) < 2) continue;
            string typ = tk[0];
            // décomposition de la pièce en polygones dans le repère du module (x le long, y dos, z haut)
            vector PP[]; int NB[];         // sommets et taille de chaque polygone
            int continu = 0;
            if (typ == "Q") {
                int nq = atoi(tk[1]), kq = atoi(tk[2]), caps = atoi(tk[3]);
                vector up0 = set(atof(tk[5]), atof(tk[6]), atof(tk[7]));
                vector CQ[];
                int o = 8;
                for (int i = 0; i < nq; i++) { push(CQ, set(atof(tk[o]), atof(tk[o + 1]), atof(tk[o + 2]))); o += 3; }
                float UQ[], VQ[];
                for (int j = 0; j < kq; j++) { push(UQ, atof(tk[o])); push(VQ, atof(tk[o + 1])); o += 2; }
                vector tq = normalize(CQ[1] - CQ[0]);
                vector w = normalize(up0 - dot(up0, tq) * tq);
                vector bq = normalize(cross(w, tq));
                if (abs(tq.x) > 0.99 && abs(CQ[-1].x - CQ[0].x) >= mod_l - 1e-3) continu = 1;
                if (continu) {
                    // lisse continue : profil (u, v) -> (y, z) balayé le long de toute la limite
                    int ring[];
                    for (int i = 0; i < n; i++) {
                        for (int j = 0; j < kq; j++) {
                            vector off = CQ[0] + bq * UQ[j] + w * VQ[j];      // x ignoré (le long)
                            vector2 xy = C[i] + B[i] * off.y;
                            int pt = addpoint(0, ra_h(xy, Z[i] + off.z));
                            setpointattrib(0, "s", pt, S[i]);
                            push(ring, pt);
                        }
                    }
                    for (int i = 0; i < n - 1; i++)
                        for (int j = 0; j < kq; j++) {
                            int j2 = (j + 1) % kq;
                            int f = addprim(0, "poly", array(ring[i * kq + j], ring[(i + 1) * kq + j], ring[(i + 1) * kq + j2], ring[i * kq + j2]));
                            setprimattrib(0, "classe", f, "glissiere_lisse");
                        }
                    h_haut = max(h_haut, CQ[0].z + max(VQ));
                    continue;
                }
                // pièce discrète : balayage droit dans le repère du module
                for (int i = 0; i < nq - 1; i++)
                    for (int j = 0; j < kq; j++) {
                        int j2 = (j + 1) % kq;
                        push(PP, CQ[i] + bq * UQ[j] + w * VQ[j]); push(PP, CQ[i + 1] + bq * UQ[j] + w * VQ[j]);
                        push(PP, CQ[i + 1] + bq * UQ[j2] + w * VQ[j2]); push(PP, CQ[i] + bq * UQ[j2] + w * VQ[j2]);
                        push(NB, 4);
                    }
                int bq2[] = array(0, nq - 1);
                if (caps) foreach (int e; bq2) {
                    for (int j = 0; j < kq; j++) push(PP, CQ[e] + bq * UQ[j] + w * VQ[j]);
                    push(NB, kq);
                }
            } else if (typ == "B") {
                vector c = set(atof(tk[1]), atof(tk[2]), atof(tk[3]));
                vector h = 0.5 * set(atof(tk[4]), atof(tk[5]), atof(tk[6]));
                vector cn[] = array(set(-1, -1, -1), set(1, -1, -1), set(1, 1, -1), set(-1, 1, -1),
                                    set(-1, -1, 1), set(1, -1, 1), set(1, 1, 1), set(-1, 1, 1));
                int fa[] = array(0, 3, 2, 1, 4, 5, 6, 7, 0, 1, 5, 4, 1, 2, 6, 5, 2, 3, 7, 6, 3, 0, 4, 7);
                for (int f = 0; f < 6; f++) {
                    for (int q = 0; q < 4; q++) push(PP, c + cn[fa[4 * f + q]] * h);
                    push(NB, 4);
                }
            } else if (typ == "T") {
                int nt = atoi(tk[1]), nc = atoi(tk[2]), caps = atoi(tk[3]);
                vector CT[]; float RT[];
                for (int i = 0; i < nt; i++) { push(CT, set(atof(tk[5 + 4 * i]), atof(tk[6 + 4 * i]), atof(tk[7 + 4 * i]))); push(RT, atof(tk[8 + 4 * i])); }
                vector tq = normalize(CT[1] - CT[0]);
                vector w = abs(tq.z) < 0.9 ? set(0, 0, 1) : set(1, 0, 0);
                w = normalize(w - dot(w, tq) * tq);
                vector bq = normalize(cross(w, tq));
                for (int i = 0; i < nt - 1; i++)
                    for (int j = 0; j < nc; j++) {
                        float a0 = 2 * PI * j / nc, a1 = 2 * PI * (j + 1) / nc;
                        push(PP, CT[i] + (bq * cos(a0) + w * sin(a0)) * RT[i]); push(PP, CT[i + 1] + (bq * cos(a0) + w * sin(a0)) * RT[i + 1]);
                        push(PP, CT[i + 1] + (bq * cos(a1) + w * sin(a1)) * RT[i + 1]); push(PP, CT[i] + (bq * cos(a1) + w * sin(a1)) * RT[i]);
                        push(NB, 4);
                    }
                int bt2[] = array(0, nt - 1);
                if (caps) foreach (int e; bt2) {
                    for (int j = 0; j < nc; j++) { float a0 = 2 * PI * j / nc; push(PP, CT[e] + (bq * cos(a0) + w * sin(a0)) * RT[e]); }
                    push(NB, nc);
                }
            } else continue;
            // pose de la pièce discrète dans chaque module : x -> abscisse curviligne (centre du module + x)
            for (int m = 0; m < n_mod; m++) {
                float ac = (m + 0.5) * mod_l;
                int o = 0;
                foreach (int nb; NB) {
                    int ids[];
                    for (int q = 0; q < nb; q++) {
                        vector v = PP[o + q];
                        float a = clamp(ac + v.x, 0.0, A[-1]);
                        int i = 0;
                        while (i < n - 2 && A[i + 1] < a) i++;
                        float uu = (a - A[i]) / max(A[i + 1] - A[i], 1e-9);
                        vector2 c = C[i] + uu * (C[i + 1] - C[i]);
                        vector2 bb = normalize(B[i] + uu * (B[i + 1] - B[i]));
                        float z = lerp(Z[i], Z[i + 1], uu);
                        int pt = addpoint(0, ra_h(c + bb * v.y, z + v.z));
                        setpointattrib(0, "s", pt, lerp(S[i], S[i + 1], uu));
                        push(ids, pt);
                    }
                    int f = addprim(0, "poly", ids);
                    setprimattrib(0, "classe", f, typ == "B" ? "glissiere_ecarteur" : (typ == "T" ? "glissiere_boulon" : "glissiere_piece"));
                    o += nb;
                }
            }
        }
        push(c_ids, id0); push(c_modeles, nom); push(c_routes, rid); push(c_cotes, face > 0 ? "gauche" : "droite");
        push(c_l, A[-1]); push(c_n_mod, float(n_mod)); push(c_base, 0.0); push(c_haut, h_haut); push(c_pas, mod_l); push(c_dt, 0.0);
        setdetailattrib(0, "ra_dernier", id0 + "|" + nom + "|" + rid + "|" + chs("../materiau_acier"));
        continue;
    }
}
s[]@ra_s_ids = c_ids; s[]@ra_s_modeles = c_modeles; s[]@ra_s_routes = c_routes; s[]@ra_s_cotes = c_cotes;
f[]@ra_s_longueur = c_l; f[]@ra_s_modules = c_n_mod; f[]@ra_s_base = c_base; f[]@ra_s_hauteur = c_haut;
f[]@ra_s_pas_module = c_pas;
"""

VEX_FINIR_EQUIPEMENTS = r"""
// finir (primitive) : contrat des maillages (materiau_id, pj_couche, pj_entite, pj_maillage) ; béton : matériau du
// catalogue (retenue_*, beton_prefa_lisse) ; acier : acier_galvanise.
string c = s@classe;
s@materiau_id = (c == "separateur_beton") ? chs("../materiau_beton") : chs("../materiau_acier");
s@pj_couche = "PJ_Equipements";
s@pj_maillage = s@materiau_id;
s@pj_entite = "RET_" + (c == "separateur_beton" ? "BETON" : "GLISSIERE");
"""

VEX_UV_EQUIPEMENTS = r"""
// uv (sommet) en mètres : dessus projeté en (x, y) ; faces verticales (hauteur, abscisse s) : les stries de la texture
// de béton préfabriqué (verticales dans l'image) suivent la longueur du séparateur, comme un béton coulé en coffrage glissant
float s = point(0, "s", @ptnum);
v@uv = abs(v@N.y) > 0.9 ? set(@P.x, -@P.z, 0) : set(@P.y, s, 0);
"""

VEX_CONTROLES = r"""
// contrôles (détail) : détail des musoirs (entrée 0), des séparateurs (entrée 1) et du raccord (entrée 2)
string noms[] = {"ra_s_ids", "ra_s_modeles", "ra_s_routes", "ra_s_cotes"};
foreach (string a; noms) { string v[] = detail(1, a); setdetailattrib(0, a, v); }
string nf[] = {"ra_s_longueur", "ra_s_modules", "ra_s_base", "ra_s_hauteur", "ra_s_pas_module"};
foreach (string a; nf) { float v[] = detail(1, a); setdetailattrib(0, a, v); }
string rb[] = detail(2, "ra_bretelles"); setdetailattrib(0, "ra_bretelles", rb);
float dz[] = detail(2, "ra_dz"); setdetailattrib(0, "ra_dz", dz);
string rp[] = detail(2, "ra_principales"); setdetailattrib(0, "ra_principales", rp);
string gn[] = detail(2, "ra_genres"); setdetailattrib(0, "ra_genres", gn);
"""
