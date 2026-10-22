"""Code VEX et Python de l'HDA rg::ouvrages::1.0 (lot « ouvrages », L8 du plan, E07 de la chaîne).

Repère Houdini (x, z, −y), Y haut (README_RG § 1). Toutes les cotes viennent du modèle (ouvrages[].construction, écrit
par description/ouvrages.py avec ses provenances) ; les seuls choix de fabrication sont déclarés « [G] » ici :
- bossage (plinthe) sous chaque appareil d'appui : il comble l'espace de visite de 0,30 m entre le dessus de l'appui et
  l'intrados (OA-ESP-001) moins la hauteur de l'appareil ;
- chanfrein à 45° de la nervure d'un PSIDP à larges encorbellements ; larmier de 3 × 5 cm de la corniche ;
- talon des poutres PRAD de 0,20 m de haut ; joints posés à 3 mm au-dessus du revêtement ;
- garde-corps S8 : sections de RF-AS-garde_corps_S8 (main courante 120 × 55, montants 80 × 40 tous les 1,50 m, lisse
  basse 60 × 30 à 0,10 m, barreaux 30 × 30 à 0,14 m d'entraxe) ; BN4 : OA-BN4-001 (lisses 100 × 100 à 1,00 et 0,65 m
  [G], 85 × 70 à 0,35 m [G], poteaux 0,10 × 0,15 [G] tous les 2,50 m) ;
- terrain : maillage à 1,00 m (0,50 m autour de l'ouvrage), lignes imposées au droit des faces des murs.
"""

LIB = r'''
// =============================================================== bibliothèque rg_ouvrage (lot ouvrages)
// entrée OA_REFS : références de rg::graphe (polylignes, s@id route, f@s) ; OA_OUV : points de rg::ouvrages/lire
#define OA_REFS 1
#define OA_OUV 2
#define OA_R_COIN 1.0      // [G] rayon des coins des plates-formes et des massifs dans le calcul des talus
#define OA_CONGE 0.6       // [G] largeur (en hauteur) du raccord adouci pied de talus / terrain

float oa_interp(float xs[]; float ys[]; float x) {
    int n = len(xs);
    if (n == 0) return 0.0;
    if (x <= xs[0]) return ys[0];
    if (x >= xs[n - 1]) return ys[n - 1];
    int lo = 0; int hi = n - 1;
    while (hi - lo > 1) { int m = (lo + hi) / 2; if (xs[m] <= x) lo = m; else hi = m; }
    float f = (x - xs[lo]) / max(xs[hi] - xs[lo], 1e-12);
    return lerp(ys[lo], ys[hi], f);
}

int oa_prim_route(string r) { return findattribval(OA_REFS, "prim", "id", r); }

void oa_cadre(int pr; float s; export vector P; export vector T; export vector G) {
    int pts[] = primpoints(OA_REFS, pr);
    int n = len(pts);
    float s0 = point(OA_REFS, "s", pts[0]);
    float s1 = point(OA_REFS, "s", pts[n - 1]);
    float sc = clamp(s, s0, s1);
    int lo = 0; int hi = n - 1;
    while (hi - lo > 1) { int m = (lo + hi) / 2; if (point(OA_REFS, "s", pts[m]) <= sc) lo = m; else hi = m; }
    float sa = point(OA_REFS, "s", pts[lo]);
    float sb = point(OA_REFS, "s", pts[hi]);
    vector A = point(OA_REFS, "P", pts[lo]);
    vector B = point(OA_REFS, "P", pts[hi]);
    A.y = 0; B.y = 0;
    float f = (sb > sa) ? (sc - sa) / (sb - sa) : 0.0;
    T = normalize(B - A);
    P = A + f * (B - A) + T * (s - sc);
    G = normalize(cross({0, 1, 0}, T));
}

// abscisse s et décalage t (positif à gauche) d'une position, sur la référence de la route pr
float oa_station(int pr; vector p; export float t) {
    vector q = set(p.x, 0, p.z);
    int prim; vector uv;
    xyzdist(OA_REFS, itoa(pr), q, prim, uv);
    float s = primuv(OA_REFS, "s", prim, uv);
    vector P, T, G;
    oa_cadre(pr, s, P, T, G);
    float ds = dot(q - P, T);
    if (abs(ds) > 1e-7) { s += ds; oa_cadre(pr, s, P, T, G); }
    t = dot(q - P, G);
    return s;
}

// profil en long analytique (description/ouvrages.py, ProfilEnLong) : palier z0, rentrant Rr, rampe g, saillant Rs
float oa_zprof(float sc; float zc; float z0; float g; float Rs; float Rr; float s) {
    float H = zc - z0;
    if (H <= 1e-9 || g <= 0) return z0;
    float Ls = g * Rs; float Lr = g * Rr;
    float Lt = max(0.0, (H - g * g * Rs / 2.0 - g * g * Rr / 2.0) / g);
    float demi = Ls + Lt + Lr;
    float d = abs(s - sc);
    if (d <= Ls) return zc - d * d / (2.0 * Rs);
    float z1 = zc - Ls * Ls / (2.0 * Rs);
    if (d <= Ls + Lt) return z1 - g * (d - Ls);
    if (d <= demi) { float u = demi - d; return z0 + u * u / (2.0 * Rr); }
    return z0;
}

float oa_dprof(float sc; float zc; float z0; float g; float Rs; float Rr; float s) {
    float H = zc - z0;
    if (H <= 1e-9 || g <= 0) return 0.0;
    float Ls = g * Rs; float Lr = g * Rr;
    float Lt = max(0.0, (H - g * g * Rs / 2.0 - g * g * Rr / 2.0) / g);
    float demi = Ls + Lt + Lr;
    float d = abs(s - sc);
    float sg = (s < sc) ? 1.0 : -1.0;          // monte avant le sommet, descend après
    if (d <= Ls) return sg * d / Rs;
    if (d <= Ls + Lt) return sg * g;
    if (d <= demi) return sg * (demi - d) / Rr;
    return 0.0;
}

// Z relatif de la coupe en travers (bandes [t_g, z_g] - [t_d, z_d], t décroissant), linéaire dans chaque bande ;
// sur une limite commune à deux bandes (marche d'une bordure), le plus bas des deux
float oa_coupe_z(float tg[]; float zg[]; float td[]; float zd[]; float t) {
    float z = 1e9;
    for (int i = 0; i < len(tg); i++) {
        if (t <= tg[i] + 1e-6 && t >= td[i] - 1e-6) {
            float f = (tg[i] - t) / max(tg[i] - td[i], 1e-9);
            z = min(z, lerp(zg[i], zd[i], clamp(f, 0.0, 1.0)));
        }
    }
    if (z > 1e8) z = (t > tg[0]) ? zg[0] : zd[len(zd) - 1];
    return z;
}

int oa_point_profil(string r) { return findattribval(OA_OUV, "point", "pl_route", r); }

float oa_zl(string r; float s) {
    int ip = oa_point_profil(r);
    if (ip < 0) return 0.0;
    return oa_zprof(point(OA_OUV, "pl_sc", ip), point(OA_OUV, "pl_zc", ip), point(OA_OUV, "pl_z0", ip),
                    point(OA_OUV, "pl_g", ip), point(OA_OUV, "pl_rs", ip), point(OA_OUV, "pl_rr", ip), s);
}

float oa_dzl(string r; float s) {
    int ip = oa_point_profil(r);
    if (ip < 0) return 0.0;
    return oa_dprof(point(OA_OUV, "pl_sc", ip), point(OA_OUV, "pl_zc", ip), point(OA_OUV, "pl_z0", ip),
                    point(OA_OUV, "pl_g", ip), point(OA_OUV, "pl_rs", ip), point(OA_OUV, "pl_rr", ip), s);
}

// position monde (Houdini) au point (s, t) de la route portée, à dz au-dessus de son axe profilé
vector oa_pt(int pr; string r; float s; float t; float dz) {
    vector P, T, G;
    oa_cadre(pr, s, P, T, G);
    return P + t * G + set(0, oa_zl(r, s) + dz, 0);
}

// maximum adouci de rayon h (pente du résultat <= la plus forte des deux pentes) : raccord en congé du pied d'un
// talus sur le terrain naturel ou sur la berge d'un talweg ; sans lui, les facettes qui chevauchent l'arête sont plus
// raides que les deux talus
float oa_smax(float a; float b; float h) {
    float u = max(h - abs(a - b), 0.0) / h;
    return max(a, b) + u * u * h * 0.25;
}

// distance d'un point (s, t) à un rectangle [sa, sb] x [td, tg] dont les coins sont arrondis au rayon R (0 dedans) ;
// sans arrondi, le talus en « cône » autour d'un coin a un sommet où les facettes de la grille sont plus raides que lui
float oa_dist_rect(float s; float t; float sa; float sb; float td; float tg) {
    float R = min(OA_R_COIN, 0.5 * min(sb - sa, tg - td));
    float ds = max(max(sa + R - s, s - (sb - R)), 0.0);
    float dt = max(max(td + R - t, t - (tg - R)), 0.0);
    return max(sqrt(ds * ds + dt * dt) - R, 0.0);
}

// ---------------------------------------------------------------- routes à niveau (intégration de l'étape 4)
// Scène qui compose un ouvrage et d'autres routes au niveau du terrain (bretelle, branches d'un carrefour) : entrée 3
// du nœud « terrain » = sol des routes là où le profil en long est nul (palier), aplati (y = 0, f@zs = z du sol aux
// points) ; vide pour les scènes dont toutes les routes sont portées ou franchies (scènes du lot « ouvrages » : terrain
// inchangé). Remblai autour de ce sol : 5 cm sous le sol dans son emprise ; au-dehors, maximum des cônes de talus
// (OA-TAL-001) issus du point du sol le plus proche (2 cm sous lui) et de tous les points du sol à moins de
// OA_NIVEAU_R : le maximum de cônes est continu et sa pente ne dépasse pas celle des talus, même à l'angle de deux routes
// de niveaux différents (le seul point le plus proche y saute d'une route à l'autre). Le terrain naturel est 0,65 m sous
// le plus bas des bords (description/ouvrages.py) : maximum simple (pas de congé, qui remonterait au bord des
// plates-formes). Le nœud « terrain » seul définit OA_AVEC_NIVEAU.
#define OA_NIVEAU 3
#define OA_NIVEAU_DMAX 25.0
#define OA_NIVEAU_R 2.5        // [G] rayon de recherche des points du sol (au-delà, leur cône est sous le terrain naturel)
float oa_niveau(vector p; float z; float k; export int zone) {
    if (npoints(OA_NIVEAU) == 0) return z;
    vector q = set(p.x, 0, p.z);
    int pr; vector uv;
    float d = xyzdist(OA_NIVEAU, q, pr, uv, OA_NIVEAU_DMAX);
    if (pr < 0) return z;
    float zs = primuv(OA_NIVEAU, "zs", pr, uv);
    float za;
    if (d < 1e-4) za = zs - 0.05;
    else {
        za = zs - 0.02 - k * d;
        int pts[] = pcfind(OA_NIVEAU, "P", q, OA_NIVEAU_R, 8192);
        foreach (int ip; pts) {
            vector pp = point(OA_NIVEAU, "P", ip);
            float di = distance(set(pp.x, 0, pp.z), q);
            za = max(za, point(OA_NIVEAU, "zs", ip) - 0.02 - k * di);
        }
    }
    if (za > z) { z = za; zone = 6; }
    return z;
}

// ---------------------------------------------------------------- terrain (terrain naturel, talweg, remblais, déblais)
// Un seul champ de Z (le terrain) : naturel ; talweg dit ; remblais de la route portée hors de l'ouvrage (pente du
// talus OA-TAL-001, « cône » autour des bords de plate-forme) ; massif sous le sommier des culées ; déblais : la
// plate-forme de la route portée (cône de déblai hors de l'ouvrage) et de la route franchie (pour un portique, couloir
// vertical entre les piédroits et les murs en aile).
float oa_terrain(vector p; export int zone) {
    int n = npoints(OA_OUV);
    float z = 0.0;
    int premier = 1;
    zone = 0;
    for (int io = 0; io < n; io++) {
        if (!inpointgroup(OA_OUV, "ouvrage", io)) continue;
        if (premier) { z = point(OA_OUV, "z_nat", io); premier = 0; }
        if (point(OA_OUV, "talweg", io)) {
            int pr = oa_prim_route(point(OA_OUV, "route_portee", io));
            float t; float s = oa_station(pr, p, t);
            float u = abs(s - point(OA_OUV, "s_x", io)) * sin(radians(point(OA_OUV, "biais", io)));
            float df = point(OA_OUV, "tw_fond", io) / 2.0;
            float zt = (u <= df) ? -point(OA_OUV, "tw_prof", io)
                                 : min(0.0, -point(OA_OUV, "tw_prof", io) + (u - df) / point(OA_OUV, "tw_pente", io));
            if (zt < z) { z = zt; zone = 4; }
        }
    }
    // remblais de la route portée et massifs des culées
    for (int io = 0; io < n; io++) {
        if (!inpointgroup(OA_OUV, "ouvrage", io)) continue;
        string r = point(OA_OUV, "route_portee", io);
        int pr = oa_prim_route(r);
        float k = 1.0 / point(OA_OUV, "talus", io);
        float t; float s = oa_station(pr, p, t);
        float L = point(OA_OUV, "L_portee", io);
        float tg = point(OA_OUV, "plat_g", io); float td = point(OA_OUV, "plat_d", io);
        float zpg = point(OA_OUV, "z_plat_g", io); float zpd = point(OA_OUV, "z_plat_d", io);
        float zmin = point(OA_OUV, "z_min_surf", io);
        float sa0 = point(OA_OUV, "s_terre0", io); float sa1 = point(OA_OUV, "s_terre1", io);
        float zA = -1e9;
        float zC = 1e9;                                   // déblai : la plate-forme portée sous le terrain naturel
        // au-delà des bouts de la route (limite de scène), ni remblai ni déblai : la jupe de bout masque la marche
        if (s < 0.0 || s > L) { zA = -1e9; zC = 1e9; }
        else
        for (int piece = 0; piece < 2; piece++) {
            float lo = (piece == 0) ? 0.0 : sa1;          // plate-forme bornée aux bouts de la route
            float hi = (piece == 0) ? sa0 : L;
            float sc = clamp(s, lo, hi);
            float dt = (t > tg) ? t - tg : ((t < td) ? td - t : 0.0);
            float d = oa_dist_rect(s, t, lo, hi, td, tg);
            float zlc = oa_zl(r, sc);
            float top = (dt > 0) ? zlc + ((t > 0) ? zpg : zpd) - 0.02 : zlc + zmin - 0.05;
            zA = max(zA, top - k * d);
            zC = min(zC, top + k * d);
        }
        if (!point(OA_OUV, "portique", io)) {
            for (int c = 0; c < 2; c++) {
                float sb0 = point(OA_OUV, (c == 0) ? "massif0_s0" : "massif1_s0", io);
                float sb1 = point(OA_OUV, (c == 0) ? "massif0_s1" : "massif1_s1", io);
                float topb = point(OA_OUV, (c == 0) ? "massif0_z" : "massif1_z", io);
                // massif élargi de R autour du sommier : l'arrondi ne découvre pas le dessous du sommier
                float d = oa_dist_rect(s, t, sb0 - OA_R_COIN, sb1 + OA_R_COIN, point(OA_OUV, "B_d", io) - OA_R_COIN,
                                       point(OA_OUV, "B_g", io) + OA_R_COIN);
                zA = max(zA, topb - k * d);
            }
        }
#ifdef OA_AVEC_NIVEAU
        // routes à niveau (étape 4) : remblai de la route portée en maximum simple, comme celui des routes à niveau
        // (le congé rendrait ce remblai plus haut que celui du même sol au-delà des bouts de la route : marche)
        if (npoints(OA_NIVEAU) > 0) { if (zA > z) { z = zA; zone = 1; } }
        else if (zA > z - OA_CONGE) { if (zA > z) zone = 1; z = oa_smax(z, zA, OA_CONGE); }
        z = oa_niveau(p, z, k, zone);                     // avant les déblais
#else
        if (zA > z - OA_CONGE) { if (zA > z) zone = 1; z = oa_smax(z, zA, OA_CONGE); }
#endif
        if (zC < z) { z = zC; zone = 2; }
        // sol abaissé sous le tablier : entre les fronts des appuis d'extrémité, le terrain (remblais compris) reste à la
        // revanche sous l'intrados (RF-GV-PON-012), talus OA-TAL-001 autour ; un portique est traité par son couloir
        if (!point(OA_OUV, "portique", io)) {
            float l0 = point(OA_OUV, "s_libre0", io); float l1 = point(OA_OUV, "s_libre1", io);
            float sl = clamp(s, l0, l1);
            float zi = oa_zl(r, sl) + point(OA_OUV, "z_dessus", io) - point(OA_OUV, "e", io) - point(OA_OUV, "revanche", io) - 0.05;   // + 5 cm de discrétisation [G]
            float dl = oa_dist_rect(s, t, l0, l1, point(OA_OUV, "B_d", io), point(OA_OUV, "B_g", io));
            float zl_cut = zi + k * dl;
            if (zl_cut < z) { z = zl_cut; zone = 5; }
        }
    }
    // déblais : plate-forme de la route franchie (couloir vertical sous un portique, cône de déblai sinon)
    for (int io = 0; io < n; io++) {
        if (!inpointgroup(OA_OUV, "ouvrage", io)) continue;
        string rf = point(OA_OUV, "route_franchie", io);
        if (rf == "") continue;
        int pf = oa_prim_route(rf);
        if (pf < 0) continue;
        float k = 1.0 / point(OA_OUV, "talus", io);
        float t2; float s2 = oa_station(pf, p, t2);
        float cft[] = point(OA_OUV, "cf_mt", io);       // − t croissant
        float cfz[] = point(OA_OUV, "cf_z", io);
        float fg = point(OA_OUV, "fr_g", io); float fd = point(OA_OUV, "fr_d", io);
        float Lf = point(OA_OUV, "L_franchie", io);
        float s2c = clamp(s2, 0.0, Lf);
        float zl2 = oa_zl(rf, s2c);
        float dsf = abs(s2 - s2c);
        if (t2 <= fg + 1e-3 && t2 >= fd - 1e-3 && dsf < 1e-6) {     // tolérance : nœuds des lignes imposées
            float btg[] = point(OA_OUV, "cfb_tg", io); float bzg[] = point(OA_OUV, "cfb_zg", io);
            float btd[] = point(OA_OUV, "cfb_td", io); float bzd[] = point(OA_OUV, "cfb_zd", io);
            float zs = zl2 + oa_coupe_z(btg, bzg, btd, bzd, t2) - 0.05;
            if (zs < z) { z = zs; zone = 3; }
        } else if (!point(OA_OUV, "portique", io)) {
            float d = oa_dist_rect(s2, t2, 0.0, Lf, fd, fg);
            float ze = zl2 + ((t2 > 0) ? cfz[0] : cfz[len(cfz) - 1]) - 0.02 + k * d;
            if (ze < z) { z = ze; zone = 2; }
        }
    }
    return z;
}
'''

# --------------------------------------------------------------------------------------------- déformation
VEX_STATION = r'''
// point : abscisse et pente du profil en long de sa route (déformation verticale, profil en long du modèle)
string r = s@route;
int pr = oa_prim_route(r);
i@oa_ok = 0;
if (pr >= 0 && oa_point_profil(r) >= 0) {
    float t; float s = oa_station(pr, @P, t);
    vector P, T, G;
    oa_cadre(pr, s, P, T, G);
    f@oa_dz = oa_zl(r, s);
    f@oa_g = oa_dzl(r, s);
    v@oa_T = T;
    i@oa_ok = 1;
}
'''

VEX_DEFORMER = r'''
// z += z_long(s) : la coupe en travers et les marques posées sur la route suivent son profil en long
if (i@oa_ok) @P.y += f@oa_dz;
'''

VEX_NORMALES = r'''
// normale de sommet transformée par la déformation (J^-T) : n' = n − g n.y T
if (hasvertexattrib(0, "N")) {
    int pt = vertexpoint(0, @vtxnum);
    if (point(0, "oa_ok", pt)) {
        float g = point(0, "oa_g", pt);
        vector T = point(0, "oa_T", pt);
        vector n = vertex(0, "N", @vtxnum);
        setvertexattrib(0, "N", -1, @vtxnum, normalize(n - g * n.y * T), "set");
    }
}
'''

VEX_NORMALES_POINTS = r'''
if (haspointattrib(0, "N") && i@oa_ok) {
    vector n = point(0, "N", @ptnum);
    setpointattrib(0, "N", @ptnum, normalize(n - f@oa_g * n.y * v@oa_T), "set");
}
'''

VEX_UV = r'''
// coordonnées de texture en mètres, projection sur le plan le plus proche de la face (béton, acier, terrain)
vector n = abs(v@N);
if (n.y >= n.x && n.y >= n.z) v@uv = set(@P.x, -@P.z, 0);
else if (n.x >= n.z) v@uv = set(-@P.z, @P.y, 0);
else v@uv = set(@P.x, @P.y, 0);
'''

# --------------------------------------------------------------------------------------------- structures
VEX_STRUCTURES = r'''
// ================================================================ ouvrages : tablier, corniches, appuis, équipements
addprimattrib(0, "materiau_id", "");
addprimattrib(0, "partie", "");
addprimattrib(0, "ouvrage", "");
addprimattrib(0, "pj_couche", "");
addprimattrib(0, "pj_entite", "");
addprimattrib(0, "dehors", {0, 0, 0});


int face(int pts[]; vector dehors; string tg[]) {
    int p = addprim(0, "poly", pts);
    setprimattrib(0, "materiau_id", p, tg[0]);
    setprimattrib(0, "partie", p, tg[1]);
    setprimattrib(0, "ouvrage", p, tg[2]);
    setprimattrib(0, "pj_couche", p, "ouvrages");
    setprimattrib(0, "pj_entite", p, tg[2] + ":" + tg[1]);
    setprimattrib(0, "dehors", p, dehors);
    return p;
}

// boîte à 8 sommets c[0..3] dessous (sens quelconque, contour), c[4..7] dessus (mêmes ordres)
void boite(vector c[]; string tg[]) {
    int q[];
    for (int i = 0; i < 8; i++) append(q, addpoint(0, c[i]));
    vector m = (c[0] + c[1] + c[2] + c[3] + c[4] + c[5] + c[6] + c[7]) / 8.0;
    face(array(q[0], q[1], q[2], q[3]), {0, -1, 0}, tg);
    face(array(q[4], q[5], q[6], q[7]), {0, 1, 0}, tg);
    for (int i = 0; i < 4; i++) {
        int j = (i + 1) % 4;
        vector mid = (c[i] + c[j] + c[i + 4] + c[j + 4]) / 4.0;
        face(array(q[i], q[j], q[j + 4], q[i + 4]), mid - m, tg);
    }
}

// boîte orientée : centre bas cb, axes unitaires a (longueur la), b (largeur lb), hauteur h (vers +Y)
void boite_axes(vector cb; vector a; vector b; float la; float lb; float h; string tg[]) {
    vector c[];
    vector u = a * la * 0.5; vector v = b * lb * 0.5; vector up = set(0, h, 0);
    append(c, cb - u - v); append(c, cb + u - v); append(c, cb + u + v); append(c, cb - u + v);
    for (int i = 0; i < 4; i++) append(c, c[i] + up);
    boite(c, tg);
}

// cylindre vertical (poteau) : centre bas, rayon, hauteur, 16 côtés
void poteau(vector cb; float r; float h; string tg[]) {
    int nb = 16; int bas[]; int haut[];
    for (int i = 0; i < nb; i++) {
        float a = 2 * PI * i / nb;
        vector d = set(cos(a), 0, sin(a));
        append(bas, addpoint(0, cb + r * d));
        append(haut, addpoint(0, cb + r * d + set(0, h, 0)));
    }
    face(bas, {0, -1, 0}, tg); face(haut, {0, 1, 0}, tg);
    for (int i = 0; i < nb; i++) {
        int j = (i + 1) % nb;
        float a = 2 * PI * (i + 0.5) / nb;
        face(array(bas[i], bas[j], haut[j], haut[i]), set(cos(a), 0, sin(a)), tg);
    }
}

// balayage d'une section (t[k], dz[k], polygone fermé) le long de la route portée de s0 à s1 (pas <= ds) ;
// dz relatif à l'axe profilé ; bouts fermés
void balayer(int pr; string r; float st[]; float sz[]; float s0; float s1; float dsmax; string tg[]) {
    int nk = len(st);
    int ns = max(1, int(ceil((s1 - s0) / dsmax)));
    float tc = 0; float zc = 0;
    for (int k = 0; k < nk; k++) { tc += st[k]; zc += sz[k]; }
    tc /= nk; zc /= nk;
    int prev[]; int first[];
    for (int i = 0; i <= ns; i++) {
        float s = s0 + (s1 - s0) * i / ns;
        vector P, T, G;
        oa_cadre(pr, s, P, T, G);
        float zl = oa_zl(r, s);
        int cur[];
        for (int k = 0; k < nk; k++) append(cur, addpoint(0, P + st[k] * G + set(0, zl + sz[k], 0)));
        if (i == 0) { first = cur; face(reverse(cur), -T, tg); }
        else {
            for (int k = 0; k < nk; k++) {
                int j = (k + 1) % nk;
                float tm = 0.5 * (st[k] + st[j]); float zm = 0.5 * (sz[k] + sz[j]);
                vector dh = (tm - tc) * G + set(0, zm - zc, 0);
                face(array(prev[k], prev[j], cur[j], cur[k]), dh, tg);
            }
        }
        if (i == ns) face(cur, T, tg);
        prev = cur;
    }
}

// mur le long de la route portée : t dans [ta, tb], sommet ztop (relatif à l'axe profilé), pied au terrain - enfouissement
void mur_long(int pr; string r; float ta; float tb; float s0; float s1; float ztop_rel; float zbas_min_rel; float enf; string tg[]) {
    int ns = max(1, int(ceil(abs(s1 - s0) / 0.5)));
    int prev[];
    for (int i = 0; i <= ns; i++) {
        float s = s0 + (s1 - s0) * i / ns;
        vector P, T, G;
        oa_cadre(pr, s, P, T, G);
        float zl = oa_zl(r, s);
        int zn;
        float zt = oa_terrain(P + 0.5 * (ta + tb) * G, zn);
        float zb = min(zt - enf, zl + zbas_min_rel);
        int cur[];
        append(cur, addpoint(0, P + ta * G + set(0, zb, 0)));
        append(cur, addpoint(0, P + tb * G + set(0, zb, 0)));
        append(cur, addpoint(0, P + tb * G + set(0, zl + ztop_rel, 0)));
        append(cur, addpoint(0, P + ta * G + set(0, zl + ztop_rel, 0)));
        vector dir = (s1 > s0) ? T : -T;
        if (i == 0) face(cur, -dir, tg);
        else {
            face(array(prev[0], prev[1], cur[1], cur[0]), {0, -1, 0}, tg);
            face(array(prev[1], prev[2], cur[2], cur[1]), (tb > ta) ? G : -G, tg);
            face(array(prev[2], prev[3], cur[3], cur[2]), {0, 1, 0}, tg);
            face(array(prev[3], prev[0], cur[0], cur[3]), (tb > ta) ? -G : G, tg);
        }
        if (i == ns) face(cur, dir, tg);
        prev = cur;
    }
}

int no = npoints(2);
for (int io = 0; io < no; io++) {
    if (!inpointgroup(2, "ouvrage", io)) continue;
    string OUV = point(2, "id", io);
    string MAT = "oa_beton_coule"; string PARTIE = "tablier";
    string r = point(2, "route_portee", io);
    int pr = oa_prim_route(r);
    if (pr < 0) { warning("route portée absente des références : %s", r); continue; }
    string fam = point(2, "famille", io);
    string structure = point(2, "structure", io);
    int portique = point(2, "portique", io);
    float sapp[] = point(2, "s_appuis", io);
    float sab0 = point(2, "s_ab0", io); float sab1 = point(2, "s_ab1", io);
    float e = point(2, "e", io);
    float ztop = point(2, "z_dessus", io);                    // dessus du béton du tablier (relatif)
    float Bg = point(2, "B_g", io); float Bd = point(2, "B_d", io);
    float tcen = 0.5 * (Bg + Bd);
    float pg = point(2, "plat_g", io); float pd = point(2, "plat_d", io);
    float zpg = point(2, "z_plat_g", io); float zpd = point(2, "z_plat_d", io);
    float intrados = ztop - e;                                // intrados le plus bas (relatif)
    float espace = point(2, "esp_appui", io);                 // 0,30 m (OA-ESP-001)
    // ---------------------------------------------------------------- tablier
    MAT = "oa_beton_coule"; PARTIE = "tablier";
    float st[]; float sz[];
    if (structure == "dalle" || structure == "portique" || structure == "cadre") {
        float c = point(2, "enc_l", io);
        if (c > 0) {
            float e0 = point(2, "enc_e0", io); float e1 = point(2, "enc_e1", io);
            float ch = max(e - e1, 0.0);                      // chanfrein à 45° [G]
            st = array(Bg, Bd, Bd, Bd + c, Bd + c + ch, Bg - c - ch, Bg - c, Bg);
            sz = array(ztop, ztop, ztop - e0, ztop - e1, ztop - e, ztop - e, ztop - e1, ztop - e0);
        } else {
            st = array(Bg, Bd, Bd, Bg);
            sz = array(ztop, ztop, ztop - e, ztop - e);
        }
        balayer(pr, r, st, sz, sab0, sab1, 0.5, array(MAT, PARTIE, OUV));
    } else if (structure == "caisson") {
        float bi = point(2, "cai_binf", io); float bs = point(2, "cai_ames", io);
        float eh = point(2, "cai_hourdis", io); float et = point(2, "cai_ext", io);
        st = array(Bg, Bd, Bd, tcen - bs / 2, tcen - bi / 2, tcen + bi / 2, tcen + bs / 2, Bg);
        sz = array(ztop, ztop, ztop - et, ztop - eh, ztop - e, ztop - e, ztop - eh, ztop - et);
        balayer(pr, r, st, sz, sab0, sab1, 0.5, array(MAT, PARTIE, OUV));
    } else if (structure == "poutre") {
        float hh = point(2, "pt_hourdis", io);
        st = array(Bg, Bd, Bd, Bg);
        sz = array(ztop, ztop, ztop - hh, ztop - hh);
        balayer(pr, r, st, sz, sab0, sab1, 0.5, array(MAT, PARTIE, OUV));
        int nbp = point(2, "pt_n", io);
        float bw = point(2, "pt_ame", io); float tl = point(2, "pt_talon", io);
        float marge = max(tl, bw);
        for (int ib = 0; ib < nbp; ib++) {
            float tb = (Bd + marge) + (Bg - Bd - 2 * marge) * ib / max(nbp - 1, 1);
            for (int kk = 0; kk < len(sapp) - 1; kk++) {
                float a0 = (kk == 0) ? sab0 : sapp[kk] + 0.03;
                float a1 = (kk == len(sapp) - 2) ? sab1 : sapp[kk + 1] - 0.03;
                float stb[] = array(tb + bw / 2, tb - bw / 2, tb - bw / 2, tb - tl / 2, tb - tl / 2, tb + tl / 2, tb + tl / 2, tb + bw / 2);
                float szb[] = array(ztop - hh, ztop - hh, ztop - e + 0.20, ztop - e + 0.20, ztop - e, ztop - e, ztop - e + 0.20, ztop - e + 0.20);
                balayer(pr, r, stb, szb, a0, a1, 0.5, array(MAT, PARTIE, OUV));
            }
        }
    }
    // ---------------------------------------------------------------- corniches (et longrines des BN4)
    float hc = point(2, "cor_h", io); float wc = point(2, "cor_l", io); float deb = point(2, "cor_debord", io);
    float lext = point(2, "l_ext", io);                       // prolongement le long des murs en retour
    float s_c0 = sab0 - lext; float s_c1 = sab1 + lext;
    for (int cote = 0; cote < 2; cote++) {
        float sg = (cote == 0) ? 1.0 : -1.0;
        float tp = (cote == 0) ? pg : pd;
        float zp = (cote == 0) ? zpg : zpd;
        float Be = (cote == 0) ? Bg : Bd;
        string eq = point(2, (cote == 0) ? "eq_g" : "eq_d", io);
        float zc_top = zp + ((eq == "BN4") ? point(2, "bn4_longrine", io) : 0.0);
        if (hc <= 0) continue;
        MAT = "oa_beton_corniche"; PARTIE = "corniche";
        float ext = Be + sg * deb;
        // sur le tablier : corniche en L qui habille la rive ; larmier de 3 x 5 cm [G]
        float stc[] = array(tp, ext, ext, ext - sg * 0.03, ext - sg * 0.03, Be, Be, tp);
        float szc[] = array(zc_top, zc_top, zc_top - hc + 0.05, zc_top - hc + 0.05, zc_top - hc, zc_top - hc, ztop, ztop);
        if (zc_top - hc > ztop - 0.02) {                      // corniche plus courte que la marche au-dessus du tablier
            stc = array(tp, ext, ext, tp);
            szc = array(zc_top, zc_top, ztop, ztop);
        }
        balayer(pr, r, stc, szc, sab0, sab1, 0.5, array(MAT, PARTIE, OUV));
        if (lext > 0) {                                       // sur les murs en retour (culées) : section pleine
            float stm[] = array(tp, ext, ext, tp);
            float szm[] = array(zc_top, zc_top, zc_top - hc, zc_top - hc);
            balayer(pr, r, stm, szm, s_c0, sab0 - 1e-3, 0.5, array(MAT, PARTIE, OUV));
            balayer(pr, r, stm, szm, sab1 + 1e-3, s_c1, 0.5, array(MAT, PARTIE, OUV));
        }
    }
    // ---------------------------------------------------------------- appuis : piles, culées, piédroits
    MAT = "oa_beton_coule";
    int na = len(sapp);
    vector P, T, G;
    for (int ia = 0; ia < na; ia++) {
        float sa = sapp[ia];
        oa_cadre(pr, sa, P, T, G);
        float zl = oa_zl(r, sa);
        float zi = zl + intrados;                             // intrados au droit de l'appui
        int zn;
        int extreme = (ia == 0 || ia == na - 1);
        if (portique) {
            if (!extreme) continue;
            PARTIE = "piedroit";
            float ep = point(2, "pd_ep", io);
            float sg = (ia == 0) ? -1.0 : 1.0;
            vector cb = P + tcen * G;
            float zt = oa_terrain(cb, zn);
            float zb = min(zt, zl + point(2, "z_franchie_bord", io)) - 0.5;
            boite_axes(cb + set(0, zb, 0), T, G, ep, Bg - Bd, zi - zb, array(MAT, PARTIE, OUV));
            // murs en aile dans le plan des piédroits, de part et d'autre de la tête (parallèles à la voie franchie)
            PARTIE = "mur_aile";
            float ema = point(2, "ma_ep", io);
            float s_in = sa - sg * ep / 2.0;                  // face intérieure du piédroit
            float s_m = s_in + sg * ema / 2.0;                // axe du mur, face intérieure alignée sur celle du piédroit
            for (int cote = 0; cote < 2; cote++) {
                float sgt = (cote == 0) ? 1.0 : -1.0;
                float t0 = (cote == 0) ? Bg : Bd;
                int nseg = 0; float tt = t0;
                int prevm[];
                vector P2, T2, G2;
                oa_cadre(pr, s_m, P2, T2, G2);
                float zl2 = oa_zl(r, s_m);
                // sommet du mur : talus du remblai lu à l'extérieur du couloir + 0,10 m ; fin au terrain naturel
                for (int it = 0; it < 400; it++) {
                    float tcur = t0 + sgt * 0.5 * it;
                    vector pe = P2 + tcur * G2 + T2 * sg * (ema / 2.0 + 0.6);      // côté remblai
                    int zn2;
                    float zemb = oa_terrain(pe, zn2);
                    float ztop_m = (it == 0) ? zl2 + point(2, (cote == 0) ? "z_plat_g" : "z_plat_d", io) - point(2, "cor_h", io) : zemb + 0.10;
                    float zbas = point(2, "z_nat", io) - 0.5;
                    if (it > 0 && zemb < point(2, "z_nat", io) + 0.15) break;
                    vector base = P2 + tcur * G2;
                    int cur[];
                    append(cur, addpoint(0, base - T2 * ema / 2.0 + set(0, zbas, 0)));
                    append(cur, addpoint(0, base + T2 * ema / 2.0 + set(0, zbas, 0)));
                    append(cur, addpoint(0, base + T2 * ema / 2.0 + set(0, ztop_m, 0)));
                    append(cur, addpoint(0, base - T2 * ema / 2.0 + set(0, ztop_m, 0)));
                    if (it == 0) face(cur, -sgt * G2, array(MAT, PARTIE, OUV));
                    else {
                        face(array(prevm[0], prevm[1], cur[1], cur[0]), {0, -1, 0}, array(MAT, PARTIE, OUV));
                        face(array(prevm[1], prevm[2], cur[2], cur[1]), T2, array(MAT, PARTIE, OUV));
                        face(array(prevm[2], prevm[3], cur[3], cur[2]), {0, 1, 0}, array(MAT, PARTIE, OUV));
                        face(array(prevm[3], prevm[0], cur[0], cur[3]), -T2, array(MAT, PARTIE, OUV));
                    }
                    prevm = cur; nseg = it;
                }
                if (len(prevm)) face(prevm, sgt * G2, array(MAT, PARTIE, OUV));
            }
            // dalle de transition sur corbeau, derrière le piédroit (OA-PIPO-001, OA-DDT-001)
            float ddt_lp = point(2, "ddt_l", io);
            if (ddt_lp > 0) {
                PARTIE = "dalle_transition";
                float s_ext = sa + sg * ep / 2.0;
                float stdp[] = array(pg, pd, pd, pg);
                float szdp[] = array(ztop, ztop, ztop - point(2, "ddt_e", io), ztop - point(2, "ddt_e", io));
                balayer(pr, r, stdp, szdp, min(s_ext, s_ext + sg * ddt_lp), max(s_ext, s_ext + sg * ddt_lp), 0.5, array(MAT, PARTIE, OUV));
            }
            continue;
        }
        // appareils d'appui (et bossages) sous l'intrados
        int napp = point(2, "app_n", io);
        float aa = point(2, "app_a", io); float ab = point(2, "app_b", io); float ah = point(2, "app_h", io);
        float zsup = zi - espace;                             // dessus de l'appui (OA-ESP-001)
        float tapp[];
        if (structure == "poutre") {
            int nbp = point(2, "pt_n", io);
            float bw = point(2, "pt_ame", io); float tl = point(2, "pt_talon", io);
            float marge = max(tl, bw);
            for (int ib = 0; ib < nbp; ib++) append(tapp, (Bd + marge) + (Bg - Bd - 2 * marge) * ib / max(nbp - 1, 1));
        } else {
            float lu = (structure == "caisson") ? point(2, "cai_binf", io) - 0.6 :
                       ((point(2, "enc_l", io) > 0) ? (Bg - Bd - 2 * point(2, "enc_l", io)) - 0.6 : (Bg - Bd) - 1.2);
            for (int ib = 0; ib < napp; ib++) append(tapp, tcen - lu / 2 + lu * ib / max(napp - 1, 1));
        }
        float lignes[];
        if (structure == "poutre" && !extreme) lignes = array(sa - 0.35, sa + 0.35);
        else if (structure == "poutre" && ia == 0) lignes = array(sa);
        else lignes = array(sa);
        foreach (float sl; lignes) {
            vector Pl, Tl, Gl;
            oa_cadre(pr, sl, Pl, Tl, Gl);
            float zil = oa_zl(r, sl) + intrados;
            foreach (float ta; tapp) {
                PARTIE = "bossage"; MAT = "oa_beton_coule";
                boite_axes(Pl + ta * Gl + set(0, zil - espace, 0), Tl, Gl, aa + 0.10, ab + 0.10, espace - ah, array(MAT, PARTIE, OUV));
                PARTIE = "appareil_appui"; MAT = "oa_elastomere";
                boite_axes(Pl + ta * Gl + set(0, zil - ah, 0), Tl, Gl, aa, ab, ah, array(MAT, PARTIE, OUV));
            }
        }
        MAT = "oa_beton_coule";
        if (!extreme) {
            string ptyp = point(2, "pile_type", io);
            vector cb = P + tcen * G;
            if (ptyp == "voiles") {
                PARTIE = "pile";
                float ep = point(2, "pile_ep", io); float lw = point(2, "pile_larg", io);
                float zt = oa_terrain(cb, zn);
                boite_axes(cb + set(0, zt - 1.0, 0), T, G, ep, lw, zsup - (zt - 1.0), array(MAT, PARTIE, OUV));
            } else {
                PARTIE = "chevetre";
                float chh = point(2, "chev_h", io); float chl = point(2, "chev_l", io); float chL = point(2, "chev_L", io);
                boite_axes(cb + set(0, zsup - chh, 0), T, G, chl, chL, chh, array(MAT, PARTIE, OUV));
                PARTIE = "pile";
                int npo = point(2, "pile_n", io);
                float dia = point(2, "pile_diam", io); float ent = point(2, "pile_entraxe", io);
                for (int ip = 0; ip < npo; ip++) {
                    vector c = cb + (-ent * (npo - 1) / 2.0 + ent * ip) * G;
                    float zt = oa_terrain(c, zn);
                    poteau(c + set(0, zt - 1.0, 0), dia / 2.0, (zsup - chh) - (zt - 1.0), array(MAT, PARTIE, OUV));
                }
            }
            continue;
        }
        // culée perchée : sommier, garde-grève, murs en retour, dalle de transition
        float sgn = (ia == 0) ? -1.0 : 1.0;                   // côté du remblai
        float gap = point(2, "esp_about", io);
        float gg = point(2, "gg_ep", io);
        float s_about = (ia == 0) ? sab0 : sab1;
        float s_ggf = s_about + sgn * gap;                    // face avant du garde-grève
        float s_ggb = s_ggf + sgn * gg;                       // face arrière
        float s_front = sa - sgn * point(2, "som_l", io) / 2.0;
        float som_h = point(2, "som_h", io);
        PARTIE = "sommier";
        {
            vector Pm, Tm, Gm;
            float smid = 0.5 * (s_front + s_ggb);
            oa_cadre(pr, smid, Pm, Tm, Gm);
            boite_axes(Pm + tcen * Gm + set(0, zsup - som_h, 0), Tm, Gm, abs(s_front - s_ggb), Bg - Bd, som_h, array(MAT, PARTIE, OUV));
        }
        PARTIE = "garde_greve";
        {
            float stg[] = array(Bg, Bd, Bd, Bg);
            float szg[] = array(ztop, ztop, intrados - espace, intrados - espace);
            balayer(pr, r, stg, szg, min(s_ggf, s_ggb), max(s_ggf, s_ggb), 0.5, array(MAT, PARTIE, OUV));
        }
        PARTIE = "mur_retour";
        float mre = point(2, "mr_ep", io); float mrl = point(2, "mr_l", io);
        float zbas_rel = intrados - espace - som_h;
        float smr0 = s_front; float smr1 = s_ggb + sgn * mrl;
        float zcb_g = zpg + ((point(2, "eq_g", io) == "BN4") ? point(2, "bn4_longrine", io) : 0.0) - hc;
        float zcb_d = zpd + ((point(2, "eq_d", io) == "BN4") ? point(2, "bn4_longrine", io) : 0.0) - hc;
        mur_long(pr, r, Bg - mre, Bg, smr0, smr1, zcb_g, zbas_rel, 0.5, array(MAT, PARTIE, OUV));
        mur_long(pr, r, Bd, Bd + mre, smr0, smr1, zcb_d, zbas_rel, 0.5, array(MAT, PARTIE, OUV));
        float ddt_l = point(2, "ddt_l", io);
        if (ddt_l > 0) {
            PARTIE = "dalle_transition";
            float std[] = array(pg, pd, pd, pg);
            float szd[] = array(ztop, ztop, ztop - point(2, "ddt_e", io), ztop - point(2, "ddt_e", io));
            balayer(pr, r, std, szd, min(s_ggb, s_ggb + sgn * ddt_l), max(s_ggb, s_ggb + sgn * ddt_l), 0.5, array(MAT, PARTIE, OUV));
        }
    }
    // ---------------------------------------------------------------- dispositifs de retenue (garde-corps S8, BN4)
    MAT = "acier_galvanise";
    for (int cote = 0; cote < 2; cote++) {
        string eq = point(2, (cote == 0) ? "eq_g" : "eq_d", io);
        float h = point(2, (cote == 0) ? "h_g" : "h_d", io);
        float sg = (cote == 0) ? 1.0 : -1.0;
        float tp = (cote == 0) ? pg : pd;
        float zp = (cote == 0) ? zpg : zpd;
        float a0 = s_c0 + 0.10; float a1 = s_c1 - 0.10;
        if (eq == "garde_corps") {
            PARTIE = "garde_corps";
            float tg_ = tp + sg * wc * 0.5;                   // axe sur la corniche
            int nm = max(1, int(ceil((a1 - a0) / 1.5)));
            float pas = (a1 - a0) / nm;
            float smc[]; float zmc[];
            for (int i = 0; i <= nm; i++) {
                float s = a0 + pas * i;
                vector Pq, Tq, Gq;
                oa_cadre(pr, s, Pq, Tq, Gq);
                float zb = oa_zl(r, s) + zp;
                boite_axes(Pq + tg_ * Gq + set(0, zb, 0), Tq, Gq, 0.08, 0.04, h, array(MAT, PARTIE, OUV));       // montant 80 x 40
            }
            float stm[] = array(tg_ + 0.0275, tg_ - 0.0275, tg_ - 0.0275, tg_ + 0.0275);
            float szm[] = array(zp + h, zp + h, zp + h - 0.12, zp + h - 0.12);          // main courante 120 x 55
            balayer(pr, r, stm, szm, a0 - 0.04, a1 + 0.04, 1.5, array(MAT, PARTIE, OUV));
            float stl[] = array(tg_ + 0.015, tg_ - 0.015, tg_ - 0.015, tg_ + 0.015);
            float szl[] = array(zp + 0.16, zp + 0.16, zp + 0.10, zp + 0.10);              // lisse basse 60 x 30
            balayer(pr, r, stl, szl, a0, a1, 1.5, array(MAT, PARTIE, OUV));
            for (int i = 0; i < nm; i++) {                     // barreaux 30 x 30 à 0,14 m d'entraxe (vide 0,11)
                float sA = a0 + pas * i + 0.04; float sB = a0 + pas * (i + 1) - 0.04;
                int nbx = max(1, int(floor((sB - sA) / 0.14)));
                float pb = (sB - sA) / (nbx + 1);
                for (int j = 1; j <= nbx; j++) {
                    float s = sA + pb * j;
                    vector Pq, Tq, Gq;
                    oa_cadre(pr, s, Pq, Tq, Gq);
                    float zb = oa_zl(r, s) + zp;
                    boite_axes(Pq + tg_ * Gq + set(0, zb + 0.16, 0), Tq, Gq, 0.03, 0.03, h - 0.12 - 0.16, array(MAT, PARTIE, OUV));
                }
            }
        } else if (eq == "BN4") {
            PARTIE = "bn4";
            float lg = point(2, "bn4_longrine", io);
            // file d'au moins 30 m (OA-BN4-001), centrée sur l'ouvrage ; hors de l'ouvrage, longrine béton au bord de
            // la plate-forme (largeur de la bande d'équipement, 0,30 m sous le sol)
            float smil = 0.5 * (a0 + a1);
            float lmin = point(2, "bn4_lmin", io);
            float b0 = min(a0, smil - lmin / 2.0); float b1 = max(a1, smil + lmin / 2.0);
            if (b0 < a0 - 1e-3 || b1 > a1 + 1e-3) {
                string pp = PARTIE; string mm = MAT;
                PARTIE = "longrine"; MAT = "oa_beton_corniche";
                float tz = tp + sg * point(2, "bn4_zone", io);
                float stl2[] = array(tp, tz, tz, tp);
                float szl2[] = array(zp + lg, zp + lg, zp - 0.30, zp - 0.30);
                if (b0 < a0 - 1e-3) balayer(pr, r, stl2, szl2, b0, s_c0, 1.0, array(MAT, PARTIE, OUV));
                if (b1 > a1 + 1e-3) balayer(pr, r, stl2, szl2, s_c1, b1, 1.0, array(MAT, PARTIE, OUV));
                PARTIE = pp; MAT = mm;
            }
            a0 = b0; a1 = b1;
            float tl = tp + sg * 0.05;                         // face des lisses côté chaussée
            float tpo = tp + sg * (0.10 + 0.075);              // poteaux 0,10 x 0,15 [G] derrière les lisses
            int nm = max(1, int(ceil((a1 - a0) / 2.5)));
            float pas = (a1 - a0) / nm;
            for (int i = 0; i <= nm; i++) {
                float s = a0 + pas * i;
                vector Pq, Tq, Gq;
                oa_cadre(pr, s, Pq, Tq, Gq);
                float zb = oa_zl(r, s) + zp + lg;
                boite_axes(Pq + tpo * Gq + set(0, zb, 0), Tq, Gq, 0.10, 0.15, 1.0, array(MAT, PARTIE, OUV));
            }
            float hl[] = array(1.0, 0.65, 0.35);               // lisse supérieure 1,00 (OA-BN4-001), autres [G]
            float hh[] = array(0.10, 0.10, 0.085);
            float ll[] = array(0.10, 0.10, 0.07);
            for (int k = 0; k < 3; k++) {
                float t1 = tl; float t2 = tl + sg * ll[k];
                float stb[] = array(t1, t2, t2, t1);
                float zt1 = zp + lg + hl[k]; float zt0 = zt1 - hh[k];
                float szb[] = array(zt1, zt1, zt0, zt0);
                balayer(pr, r, stb, szb, a0 - 0.05, a1 + 0.05, 1.0, array(MAT, PARTIE, OUV));
            }
        }
    }
}
'''

VEX_JOINTS = r'''
// joints de chaussée : bande de largeur dite posée à 3 mm au-dessus du revêtement (entrée 3 : sol et bordures déformés), sur toute
// la largeur de la plate-forme, trottoirs compris (RF-GV-PON-011, OA-JNT-001)
addprimattrib(0, "materiau_id", "");
addprimattrib(0, "partie", "");
addprimattrib(0, "ouvrage", "");
addprimattrib(0, "pj_couche", "");
addprimattrib(0, "pj_entite", "");
addprimattrib(0, "dehors", {0, 0, 0});
int no = npoints(2);
for (int io = 0; io < no; io++) {
    if (!inpointgroup(2, "ouvrage", io)) continue;
    string id = point(2, "id", io);
    string r = point(2, "route_portee", io);
    int pr = oa_prim_route(r);
    float sj[] = point(2, "s_joints", io);
    float lj = point(2, "jnt_l", io);
    float pg = point(2, "plat_g", io); float pd = point(2, "plat_d", io);
    int nt = int(ceil((pg - pd) / 0.10));
    foreach (int kj; float sc; sj) {
        int lignes[];
        for (int a = 0; a < 3; a++) {
            float s = sc - lj / 2 + lj * a / 2.0;
            vector P, T, G;
            oa_cadre(pr, s, P, T, G);
            int ligne[];
            for (int i = 0; i <= nt; i++) {
                float t = pd + (pg - pd) * i / nt;
                vector q = P + t * G;
                vector o = q + set(0, 500, 0);
                vector pos; vector uvw;
                int hit = intersect(3, o, set(0, -1000, 0), pos, uvw);
                float z = (hit >= 0) ? pos.y : oa_zl(r, s);
                append(ligne, addpoint(0, set(q.x, z + 0.003, q.z)));
            }
            append(lignes, ligne);
        }
        for (int a = 0; a < 2; a++) {
            for (int i = 0; i < nt; i++) {
                int b0 = a * (nt + 1); int b1 = (a + 1) * (nt + 1);
                int p = addprim(0, "poly", array(lignes[b0 + i], lignes[b0 + i + 1], lignes[b1 + i + 1], lignes[b1 + i]));
                setprimattrib(0, "materiau_id", p, "oa_joint");
                setprimattrib(0, "partie", p, "joint");
                setprimattrib(0, "ouvrage", p, id);
                setprimattrib(0, "pj_couche", p, "ouvrages");
                setprimattrib(0, "pj_entite", p, id + ":joint" + itoa(kj));
                setprimattrib(0, "dehors", p, {0, 1, 0});
            }
        }
    }
}
'''

VEX_ORIENTER = r'''
vector n = prim_normal(0, @primnum, {0.5, 0.5, 0});
if (length(v@dehors) > 0 && dot(n, v@dehors) < 0) i@group_a_inverser = 1;
'''

# --------------------------------------------------------------------------------------------- terrain
VEX_GRILLE = r'''
// grille du terrain : emprise des routes (+ marge), pas de 1,00 m (0,50 m autour des ouvrages), lignes imposées
float x0 = detail(2, "ter_x0"); float x1 = detail(2, "ter_x1");
float z0 = detail(2, "ter_z0"); float z1 = detail(2, "ter_z1");
float fx0 = detail(2, "fin_x0"); float fx1 = detail(2, "fin_x1");
float fz0 = detail(2, "fin_z0"); float fz1 = detail(2, "fin_z1");
float imx[] = detail(2, "imp_x"); float imz[] = detail(2, "imp_z");
float pas = ch("../pas_terrain"); float fin = ch("../pas_terrain_fin");
float xs[]; float zs[];
for (int axe = 0; axe < 2; axe++) {
    float a0 = (axe == 0) ? x0 : z0; float a1 = (axe == 0) ? x1 : z1;
    float f0 = (axe == 0) ? fx0 : fz0; float f1 = (axe == 0) ? fx1 : fz1;
    float imp[] = (axe == 0) ? imx : imz;
    float v[];
    float ext = ch("../etendue_terrain");
    float A0 = min(a0, f0); float A1 = max(a1, f1);    // emprise des routes et zone fine de l'ouvrage
    float a = A0 - ext;
    while (a < A1 + ext - 1e-6) {
        append(v, a);
        float dh = max(A0 - a, a - A1);                 // distance hors de l'emprise
        float st = (a >= f0 - 1e-6 && a < f1 - 1e-6) ? fin : pas;
        if (dh > 0) st = max(st, 0.25 * dh);
        a += st;
    }
    append(v, A1 + ext);
    foreach (float x; imp) if (x > A0 - ext && x < A1 + ext) append(v, x);
    v = sort(v);
    float w[];
    foreach (float x; v) if (len(w) == 0 || x - w[len(w) - 1] > 0.05) append(w, x);
    if (axe == 0) xs = w; else zs = w;
}
int nx = len(xs); int nz = len(zs);
for (int j = 0; j < nz; j++)
    for (int i = 0; i < nx; i++) addpoint(0, set(xs[i], 0, zs[j]));
setdetailattrib(0, "nx", nx);
setdetailattrib(0, "nz", nz);
'''

VEX_A_NIVEAU = r'''
// intégration de l'étape 4 : sol (couche Sol) des routes là où le profil en long de leur route est nul, si le modèle a
// des routes ni portées ni franchies (détail rg_autres_routes de lire_ouvrages) ; sinon rien (terrain inchangé)
int garder = (detail(2, "rg_autres_routes") > 0) && (s@couche_rendu == "Sol");
if (garder) {
    int ip = oa_point_profil(s@route);
    if (ip >= 0) {
        int pr = oa_prim_route(s@route);
        foreach (int pt; primpoints(0, @primnum)) {
            float t; float s = oa_station(pr, point(0, "P", pt), t);
            if (abs(oa_zl(s@route, s)) > 1e-6) { garder = 0; break; }
        }
    }
}
if (!garder) removeprim(0, @primnum, 1);
'''

VEX_APLATIR = r'''
f@zs = @P.y;
@P.y = 0;
'''

VEX_TERRAIN = r'''
int zone;
@P.y = oa_terrain(@P, zone);
i@zone = zone;
'''

VEX_TRIANGULER = r'''
// triangulation de la grille du terrain : pour chaque maille, la diagonale qui plie le moins (les lignes de pied et
// de crête des talus ne sont plus en escalier)
int nx = detail(0, "nx"); int nz = detail(0, "nz");
addprimattrib(0, "materiau_id", "oa_terrain");
addprimattrib(0, "partie", "terrain");
addprimattrib(0, "pj_couche", "terrain");
void tri(int a; int b; int c) {
    int p = addprim(0, "poly", array(a, b, c));
    setprimattrib(0, "materiau_id", p, "oa_terrain");
    setprimattrib(0, "partie", p, "terrain");
    setprimattrib(0, "pj_couche", p, "terrain");
}
for (int j = 0; j < nz - 1; j++)
    for (int i = 0; i < nx - 1; i++) {
        int a = j * nx + i; int b = a + nx; int c = a + nx + 1; int d = a + 1;
        vector A = point(0, "P", a); vector B = point(0, "P", b); vector C = point(0, "P", c); vector D = point(0, "P", d);
        vector n1 = normalize(cross(B - A, C - A)); vector n2 = normalize(cross(C - A, D - A));
        vector n3 = normalize(cross(B - A, D - A)); vector n4 = normalize(cross(C - B, D - B));
        float p1 = max(sqrt(max(1 - n1.y * n1.y, 0)) / max(abs(n1.y), 1e-9), sqrt(max(1 - n2.y * n2.y, 0)) / max(abs(n2.y), 1e-9));
        float p2 = max(sqrt(max(1 - n3.y * n3.y, 0)) / max(abs(n3.y), 1e-9), sqrt(max(1 - n4.y * n4.y, 0)) / max(abs(n4.y), 1e-9));
        int premiere = (abs(p1 - p2) > 1e-4) ? (p1 < p2) : (dot(n1, n2) >= dot(n3, n4));
        if (premiere) { tri(a, b, c); tri(a, c, d); }
        else { tri(a, b, d); tri(b, c, d); }
    }
'''

VEX_JUPES = r'''
// jupes : bande verticale de 0,60 m sous les bords extérieurs des plates-formes posées sur le terrain (remblais et
// route franchie) et sous les bouts des routes ; elles masquent la jonction du maillage du terrain avec le bord du sol
addprimattrib(0, "materiau_id", "");
addprimattrib(0, "partie", "");
addprimattrib(0, "pj_couche", "");
void bande(int pr; string r; float t; float zrel; float s0; float s1) {
    if (s1 - s0 < 0.05) return;
    int ns = max(1, int(ceil((s1 - s0) / 1.0)));
    int prev[];
    for (int i = 0; i <= ns; i++) {
        float s = s0 + (s1 - s0) * i / ns;
        vector P, T, G;
        oa_cadre(pr, s, P, T, G);
        float zt = oa_zl(r, s) + zrel;
        int cur[];
        append(cur, addpoint(0, P + t * G + set(0, zt - 0.001, 0)));
        append(cur, addpoint(0, P + t * G + set(0, zt - 0.60, 0)));
        if (i > 0) {
            int p = addprim(0, "poly", array(prev[0], cur[0], cur[1], prev[1]));
            setprimattrib(0, "materiau_id", p, "oa_terrain");
            setprimattrib(0, "partie", p, "jupe");
            setprimattrib(0, "pj_couche", p, "terrain");
        }
        prev = cur;
    }
}
void bout(int pr; string r; float s; float cg[]; float cz[]) {
    vector P, T, G;
    oa_cadre(pr, s, P, T, G);
    float zl = oa_zl(r, s);
    int haut[]; int bas[];
    for (int k = 0; k < len(cg); k++) {
        append(haut, addpoint(0, P + cg[k] * G + set(0, zl + cz[k] - 0.001, 0)));
        append(bas, addpoint(0, P + cg[k] * G + set(0, zl + cz[k] - 0.60, 0)));
    }
    for (int k = 0; k < len(cg) - 1; k++) {
        int p = addprim(0, "poly", array(haut[k], haut[k + 1], bas[k + 1], bas[k]));
        setprimattrib(0, "materiau_id", p, "oa_terrain");
        setprimattrib(0, "partie", p, "jupe");
        setprimattrib(0, "pj_couche", p, "terrain");
    }
}
int no = npoints(2);
for (int io = 0; io < no; io++) {
    if (!inpointgroup(2, "ouvrage", io)) continue;
    string r = point(2, "route_portee", io);
    int pr = oa_prim_route(r);
    float L = point(2, "L_portee", io);
    float sa0 = point(2, "s_terre0", io); float sa1 = point(2, "s_terre1", io);
    float cpt[] = point(2, "cp_t", io); float cpz[] = point(2, "cp_z", io);
    int portique = point(2, "portique", io);
    float pgv = point(2, "plat_g", io); float pdv = point(2, "plat_d", io);
    float bords[] = array(pgv, pdv);
    foreach (int c; float t; bords) {
        float zpgv = point(2, "z_plat_g", io); float zpdv = point(2, "z_plat_d", io);
        float zr = (c == 0) ? zpgv : zpdv;
        bande(pr, r, t, zr, 0.0, sa0);
        bande(pr, r, t, zr, sa1, L);
    }
    bout(pr, r, 0.0, cpt, cpz);
    bout(pr, r, L, cpt, cpz);
    string rf = point(2, "route_franchie", io);
    if (rf != "") {
        int pf = oa_prim_route(rf);
        float Lf = point(2, "L_franchie", io);
        float cft[] = point(2, "cf_t", io); float cfz[] = point(2, "cf_z", io);
        float fgv = point(2, "fr_g", io); float fdv = point(2, "fr_d", io);
        float bords_f[] = array(fgv, fdv);
        foreach (int c; float t; bords_f) {
            float zr = (c == 0) ? cfz[0] : cfz[len(cfz) - 1];
            bande(pf, rf, t, zr, 0.0, Lf);
        }
        bout(pf, rf, 0.0, cft, cfz);
        bout(pf, rf, Lf, cft, cfz);
    }
}
'''

# --------------------------------------------------------------------------------------------- points (instances)
VEX_POINTS = r'''
// points pj_points/0.1 des garde-corps (modules du catalogue route_fr, mis à la hauteur du modèle) et des BN4
addpointattrib(0, "asset_id", "");
addpointattrib(0, "pj_famille", "");
addpointattrib(0, "ouvrage", "");
addpointattrib(0, "cote", "");
addpointattrib(0, "hauteur_m", 0.0);
addpointattrib(0, "echelle_z", 1.0);
addpointattrib(0, "longueur_m", 0.0);
addpointattrib(0, "orient", {0, 0, 0, 1});
addpointattrib(0, "s", 0.0);
int no = npoints(2);
for (int io = 0; io < no; io++) {
    if (!inpointgroup(2, "ouvrage", io)) continue;
    string id = point(2, "id", io);
    string r = point(2, "route_portee", io);
    int pr = oa_prim_route(r);
    float a0 = point(2, "s_ab0", io) - point(2, "l_ext", io) + 0.10;
    float a1 = point(2, "s_ab1", io) + point(2, "l_ext", io) - 0.10;
    for (int cote = 0; cote < 2; cote++) {
        string eq = point(2, (cote == 0) ? "eq_g" : "eq_d", io);
        float sg = (cote == 0) ? 1.0 : -1.0;
        float tp = point(2, (cote == 0) ? "plat_g" : "plat_d", io);
        float zp = point(2, (cote == 0) ? "z_plat_g" : "z_plat_d", io);
        float h = point(2, (cote == 0) ? "h_g" : "h_d", io);
        string asset = point(2, (cote == 0) ? "asset_g" : "asset_d", io);
        float ha = point(2, (cote == 0) ? "h_asset_g" : "h_asset_d", io);
        float lm = (eq == "BN4") ? 2.5 : 3.0;
        float c0 = a0; float c1 = a1;
        if (eq == "BN4") {
            float smil = 0.5 * (a0 + a1); float lmin = point(2, "bn4_lmin", io);
            c0 = min(a0, smil - lmin / 2.0); c1 = max(a1, smil + lmin / 2.0);
        }
        float tq = (eq == "BN4") ? tp + sg * 0.175 : tp + sg * point(2, "cor_l", io) * 0.5;
        if (eq == "BN4") zp += point(2, "bn4_longrine", io);
        int nm = max(1, int(floor((c1 - c0) / lm)));
        for (int i = 0; i < nm; i++) {
            float s = c0 + lm * i;
            vector P, T, G;
            oa_cadre(pr, s, P, T, G);
            int p = addpoint(0, P + tq * G + set(0, oa_zl(r, s) + zp, 0));
            setpointattrib(0, "asset_id", p, (eq == "BN4") ? "BN4_fabrique_rg_ouvrages" : asset);
            setpointattrib(0, "pj_famille", p, (eq == "BN4") ? "retenue" : "garde_corps");
            setpointattrib(0, "ouvrage", p, id);
            setpointattrib(0, "cote", p, (cote == 0) ? "gauche" : "droite");
            setpointattrib(0, "hauteur_m", p, h);
            setpointattrib(0, "echelle_z", p, (eq == "BN4" || ha <= 0) ? 1.0 : h / ha);
            setpointattrib(0, "longueur_m", p, lm);
            vector a = normalize(oa_pt(pr, r, s + lm, tq, zp) - oa_pt(pr, r, s, tq, zp));
            setpointattrib(0, "orient", p, quaternion(maketransform(normalize(cross(a, {0, 1, 0})), {0, 1, 0})));
            setpointattrib(0, "s", p, s);
        }
    }
}
'''

# --------------------------------------------------------------------------------------------- lecture du modèle
PY_LIRE = r'''
# Python SOP (seul Python géométrique admis : entrée-sortie) : ouvrages[].construction et profils en long du modèle
# -> un point par ouvrage (groupe « ouvrage ») et un point par profil en long (attribut pl_route) ; détail : emprise du
# terrain. Aucune géométrie construite ici.
import json
import math
node = hou.pwd()
geo = node.geometry()
geo.clear()
chemin = node.parent().parm("fichier").evalAsString()
m = json.load(open(chemin, encoding="utf-8"))
z0 = float(m["repere"]["origine_l93"][2])
ox, oy = float(m["repere"]["origine_l93"][0]), float(m["repere"]["origine_l93"][1])
routes = {r["id"]: r for r in m.get("routes", [])}

def attr(nom, defaut, classe=hou.attribType.Point):
    if isinstance(defaut, list):
        if geo.findPointAttrib(nom) is None:
            geo.addArrayAttrib(classe, nom, hou.attribData.Float, 1)
    elif geo.findPointAttrib(nom) is None:
        geo.addAttrib(classe, nom, defaut)

def poser(pt, d):
    for k, v in d.items():
        attr(k, v)
        pt.setAttribValue(k, v)

g_ouv = geo.createPointGroup("ouvrage")
g_pl = geo.createPointGroup("profil")
xs, zs = [], []
fins = []
imp_x, imp_z = [], []
for r in m.get("routes", []):
    for p in r["ligne_reference"]["geometrie"]:
        xs.append(p[0] - ox)
        zs.append(-(p[1] - oy))
for o in m.get("ouvrages", []):
    c = o.get("construction") or {}
    rp = routes[c["route_portee"]]
    rf = routes.get(c.get("route_franchie") or "")
    tab = c["tablier"]
    enc = tab.get("encorbellement") or {}
    cai = tab.get("caisson") or {}
    pou = tab.get("poutres") or {}
    cor = c.get("corniche") or {}
    eqg, eqd = c["equipements"]["gauche"], c["equipements"]["droite"]
    pil = c.get("piles") or {}
    chv = pil.get("chevetre") or {}
    cul = c.get("culees") or {}
    pdr = c.get("piedroits") or {}
    ma = c.get("murs_aile") or {}
    app = c.get("appareils_appui") or {}
    jnt = c.get("joints") or {}
    ddt = c.get("dalles_transition") or {}
    ter = c.get("terrain") or {}
    tw = ter.get("talweg") or {}
    cp = c["coupe_portee"]
    portique = tab["structure"] in ("portique", "cadre")
    sapp = c["s_appuis"]
    e = float(tab["epaisseur_m"])
    ztop = float(tab["z_dessus_rel"])
    esp_appui = 0.30                                             # OA-ESP-001 (chevêtre / intrados)
    esp_about = float(jnt.get("vide_about_garde_greve_m", 0.40))  # OA-ESP-001 (about / garde-grève)
    gg = float(cul.get("garde_greve_epaisseur_m", 0.0))
    mrl = float(cul.get("murs_retour_longueur_m", 0.0))
    sab0, sab1 = c["s_abouts"]
    if portique:
        s_terre0 = sapp[0] - float(pdr["epaisseur_m"]) / 2.0
        s_terre1 = sapp[-1] + float(pdr["epaisseur_m"]) / 2.0
        l_ext = 0.0
    else:
        s_terre0 = sab0 - esp_about                                  # face avant du garde-grève : remblai derrière
        s_terre1 = sab1 + esp_about
        l_ext = esp_about + gg + mrl
    # massif sous le sommier des culées (dessous du sommier)
    def massif(ia, sg):
        if portique:
            return 0.0, 0.0, -1e9
        som_l, som_h = float(cul["sommier_largeur_m"]), float(cul["sommier_hauteur_m"])
        s_front = sapp[ia] - sg * som_l / 2.0
        s_ggb = (sab0 if ia == 0 else sab1) + sg * (esp_about + gg)
        return min(s_front, s_ggb), max(s_front, s_ggb), None
    pel = c["profil_en_long"]
    g_eff = float(rp.get("profil_long", {}).get("pente_max_pct", 0.0)) / 100.0
    def zlong(s):
        H = pel["sommet_z_rel"] - pel["z0_rel"]
        if H <= 1e-9 or g_eff <= 0:
            return pel["z0_rel"]
        Rs, Rr, g = pel["rayon_saillant_m"], pel["rayon_rentrant_m"], g_eff
        Ls, Lr = g * Rs, g * Rr
        Lt = max(0.0, (H - g * g * Rs / 2 - g * g * Rr / 2) / g)
        d = abs(s - c["s_croisement"])
        if d <= Ls:
            return pel["sommet_z_rel"] - d * d / (2 * Rs)
        z1 = pel["sommet_z_rel"] - Ls * Ls / (2 * Rs)
        if d <= Ls + Lt:
            return z1 - g * (d - Ls)
        dm = Ls + Lt + Lr
        if d <= dm:
            return pel["z0_rel"] + (dm - d) ** 2 / (2 * Rr)
        return pel["z0_rel"]
    ms = []
    for ia, sg in ((0, -1.0), (len(sapp) - 1, 1.0)):
        a, b, _ = massif(ia, sg)
        if portique:
            ms.append((0.0, 0.0, -1e9))
        else:
            zt = zlong(sapp[ia]) + ztop - e - esp_appui - float(cul["sommier_hauteur_m"])
            ms.append((a, b, zt))
    cf = c.get("coupe_franchie") or []
    cf_t = ([b[0] for b in cf] + [cf[-1][2]]) if cf else []
    cf_z = ([b[1] for b in cf] + [cf[-1][3]]) if cf else []
    cp_t = [b[0] for b in cp] + [cp[-1][2]]
    cp_z = [b[1] for b in cp] + [cp[-1][3]]
    pt = geo.createPoint()
    g_ouv.add(pt)
    poser(pt, {
        "id": o["id"], "route_portee": rp["id"], "route_franchie": rf["id"] if rf else "",
        "famille": tab["type"], "structure": tab["structure"], "portique": int(portique),
        "s_x": float(c["s_croisement"]), "biais": float(c["biais_deg"]), "s_appuis": [float(x) for x in sapp],
        "s_ab0": float(sab0), "s_ab1": float(sab1), "e": e, "z_dessus": ztop,
        "B_g": float(tab["t_gauche"]), "B_d": float(tab["t_droite"]),
        "plat_g": float(cp[0][0]), "plat_d": float(cp[-1][2]), "z_plat_g": float(cp[0][1]), "z_plat_d": float(cp[-1][3]),
        "z_min_surf": float(min(min(b[1], b[3]) for b in cp)),
        "cp_t": [float(x) for x in cp_t], "cp_z": [float(x) for x in cp_z],
        "enc_l": float(enc.get("longueur_m", 0.0)), "enc_e0": float(enc.get("epaisseur_extremite_m", 0.0)),
        "enc_e1": float(enc.get("epaisseur_racine_m", 0.0)),
        "cai_binf": float(cai.get("largeur_inferieure", 0.0)), "cai_ames": float(cai.get("ecart_ames", 0.0)),
        "cai_hourdis": float(cai.get("hourdis", 0.0)), "cai_ext": float(cai.get("epaisseur_extremite", 0.0)),
        "pt_n": int(pou.get("nombre", 0)), "pt_ame": float(pou.get("largeur_ame_m", 0.0)),
        "pt_talon": float(pou.get("talon_m", 0.0)), "pt_hourdis": float(pou.get("hourdis_m", 0.0)),
        "cor_h": float(cor.get("hauteur_m", 0.0)), "cor_l": float(cor.get("largeur_m", 0.0)),
        "cor_debord": float(cor.get("debord_m", 0.0)), "l_ext": float(l_ext),
        "eq_g": eqg["type"], "eq_d": eqd["type"], "h_g": float(eqg["hauteur_m"]), "h_d": float(eqd["hauteur_m"]),
        "asset_g": eqg.get("asset_id") or "", "asset_d": eqd.get("asset_id") or "",
        "h_asset_g": float(eqg.get("hauteur_asset_m") or 0.0), "h_asset_d": float(eqd.get("hauteur_asset_m") or 0.0),
        "bn4_longrine": float((eqg if eqg["type"] == "BN4" else eqd).get("longrine_hauteur_m", 0.15)),
        "bn4_zone": float((eqg if eqg["type"] == "BN4" else eqd).get("zone_m", 0.70)),
        "bn4_lmin": float((eqg if eqg["type"] == "BN4" else eqd).get("longueur_file_min_m", 30.0)),
        "pile_type": pil.get("type", ""), "pile_ep": float(pil.get("epaisseur_m", 0.0)),
        "pile_larg": float(pil.get("largeur_m", 0.0)), "pile_n": int(pil.get("nombre", 0)),
        "pile_diam": float(pil.get("diametre_m", 0.0)), "pile_entraxe": float(pil.get("entraxe_m", 0.0)),
        "chev_h": float(chv.get("hauteur_m", 0.0)), "chev_l": float(chv.get("largeur_m", 0.0)),
        "chev_L": float(chv.get("longueur_m", 0.0)),
        "som_h": float(cul.get("sommier_hauteur_m", 0.0)), "som_l": float(cul.get("sommier_largeur_m", 0.0)),
        "gg_ep": gg, "mr_l": mrl, "mr_ep": float(cul.get("murs_retour_epaisseur_m", 0.0)),
        "pd_ep": float(pdr.get("epaisseur_m", 0.0)), "ma_ep": float(ma.get("epaisseur_m", 0.0)),
        "app_a": float(app.get("a_m", 0.0)), "app_b": float(app.get("b_m", 0.0)), "app_h": float(app.get("hauteur_m", 0.0)),
        "app_n": int(app.get("nombre", 0)), "esp_appui": esp_appui, "esp_about": esp_about,
        "s_joints": [float(x) for x in jnt.get("s", [])], "jnt_l": float(jnt.get("largeur_m") or 0.0),
        "ddt_l": float(ddt.get("longueur_m", 0.0)), "ddt_e": float(ddt.get("epaisseur_m", 0.0)),
        "talus": float(c["talus"]["pente_h_sur_v"]), "z_nat": float(ter.get("z_naturel_rel", 0.0)),
        "talweg": int(bool(tw)), "tw_prof": float(tw.get("profondeur_m", 0.0)), "tw_fond": float(tw.get("largeur_fond_m", 0.0)),
        "tw_pente": float(tw.get("pente_versants_h_sur_v", 1.0)),
        "s_terre0": float(s_terre0), "s_terre1": float(s_terre1),
        "s_libre0": float(sapp[0] + (float(cul.get("sommier_largeur_m", 0.0)) / 2.0 if not portique else 0.0)),
        "s_libre1": float(sapp[-1] - (float(cul.get("sommier_largeur_m", 0.0)) / 2.0 if not portique else 0.0)),
        "revanche": float(ter.get("revanche_intrados_terrain_m", 0.10)),
        "massif0_s0": ms[0][0], "massif0_s1": ms[0][1], "massif0_z": ms[0][2],
        "massif1_s0": ms[1][0], "massif1_s1": ms[1][1], "massif1_z": ms[1][2],
        "L_portee": float(rp["ligne_reference"]["longueur_m"]),
        "L_franchie": float(rf["ligne_reference"]["longueur_m"]) if rf else 0.0,
        "cf_t": [float(x) for x in cf_t], "cf_mt": [-float(x) for x in cf_t], "cf_z": [float(x) for x in cf_z],
        "fr_g": float(cf_t[0]) if cf_t else 0.0, "fr_d": float(cf_t[-1]) if cf_t else 0.0,
        "cfb_tg": [float(b[0]) for b in cf], "cfb_zg": [float(b[1]) for b in cf],
        "cfb_td": [float(b[2]) for b in cf], "cfb_zd": [float(b[3]) for b in cf],
        "z_franchie_bord": float(min(cf_z)) if cf_z else 0.0,
    })
    # zone fine du terrain : emprise de l'ouvrage + 30 m ; lignes imposées (faces intérieures des piédroits et faces
    # extérieures des plates-formes franchies) quand les routes sont parallèles aux axes
    def xy(route, s, t):
        g = route["ligne_reference"]["geometrie"]
        acc = 0.0
        for a, b in zip(g, g[1:]):
            l = math.hypot(b[0] - a[0], b[1] - a[1])
            if acc + l >= s - 1e-9 or b is g[-1]:
                u = (s - acc) / l if l > 0 else 0.0
                tx, ty = (b[0] - a[0]) / l, (b[1] - a[1]) / l
                x = a[0] + u * (b[0] - a[0]) - t * ty
                y = a[1] + u * (b[1] - a[1]) + t * tx
                return x - ox, -(y - oy), (tx, ty)
            acc += l
    lx, lz, (tx, ty) = xy(rp, c["s_croisement"], 0.0)
    demi = (sab1 - sab0) / 2.0 + l_ext + 30.0
    fins.append((lx - demi, lx + demi, lz - demi, lz + demi))
    # bords des plates-formes (route portée et route franchie) : une maille ne chevauche pas le bord (pas de liseré
    # de terrain sur la chaussée au raccord à niveau)
    for route, coupe in ((rp, cp), (rf, cf)):
        if not route or not coupe:
            continue
        for tb in (coupe[0][0], coupe[-1][2]):
            px, pz, (tx, ty) = xy(route, 1.0, tb)
            if abs(ty) < 1e-6:
                imp_z.append(pz)
            elif abs(tx) < 1e-6:
                imp_x.append(px)
    if portique and rf:
        for s in (sapp[0] + float(pdr["epaisseur_m"]) / 2.0, sapp[-1] - float(pdr["epaisseur_m"]) / 2.0):
            px, pz, (tx, ty) = xy(rp, s, 0.0)
            if abs(ty) < 1e-6:
                imp_x.append(px)
            elif abs(tx) < 1e-6:
                imp_z.append(pz)
for r in m.get("routes", []):
    pl = r.get("profil_long")
    if not pl:
        continue
    ouv = next((o for o in m.get("ouvrages", []) if (o.get("construction") or {}).get("route_portee") == r["id"]), None)
    if ouv is None:
        continue
    pel = ouv["construction"]["profil_en_long"]
    pt = geo.createPoint()
    g_pl.add(pt)
    poser(pt, {"pl_route": r["id"], "pl_sc": float(ouv["construction"]["s_croisement"]),
               "pl_zc": float(pel["sommet_z_rel"]), "pl_z0": float(pel["z0_rel"]),
               "pl_g": float(pl.get("pente_max_pct", 0.0)) / 100.0,
               "pl_rs": float(pel.get("rayon_saillant_m") or 1.0), "pl_rr": float(pel.get("rayon_rentrant_m") or 1.0)})
for nom, v in (("ter_x0", min(xs)), ("ter_x1", max(xs)), ("ter_z0", min(zs)), ("ter_z1", max(zs)),
               ("fin_x0", min(f[0] for f in fins) if fins else 0.0), ("fin_x1", max(f[1] for f in fins) if fins else 0.0),
               ("fin_z0", min(f[2] for f in fins) if fins else 0.0), ("fin_z1", max(f[3] for f in fins) if fins else 0.0)):
    geo.addAttrib(hou.attribType.Global, nom, 0.0)
    geo.setGlobalAttribValue(nom, float(v))
for nom, v in (("imp_x", imp_x), ("imp_z", imp_z)):
    geo.addArrayAttrib(hou.attribType.Global, nom, hou.attribData.Float, 1)
    geo.setGlobalAttribValue(nom, [float(x) for x in v])
# intégration de l'étape 4 : routes ni portées ni franchies par un ouvrage (routes à niveau : bretelle, carrefour)
lies = set()
for o in m.get("ouvrages", []):
    c = o.get("construction") or {}
    lies |= {c.get("route_portee"), c.get("route_franchie")}
n_autres = sum(1 for r in m.get("routes", []) if r["id"] not in lies)
geo.addAttrib(hou.attribType.Global, "rg_autres_routes", 0)
geo.setGlobalAttribValue("rg_autres_routes", n_autres)
if n_autres:
    # lignes imposées aux bouts des routes perpendiculaires aux axes : le remblai des routes à niveau, qui fait le
    # tour des bouts de route, part d'une ligne de la grille (sans elle, une maille à cheval sur le bout est plus raide)
    for r in m.get("routes", []):
        g = r["ligne_reference"]["geometrie"]
        for a, b in ((g[0], g[1]), (g[-1], g[-2])):
            dx, dy = b[0] - a[0], b[1] - a[1]
            if abs(dy) < 1e-6 * max(abs(dx), 1e-9):
                imp_x.append(a[0] - ox)
            elif abs(dx) < 1e-6 * max(abs(dy), 1e-9):
                imp_z.append(-(a[1] - oy))
    geo.setGlobalAttribValue("imp_x", [float(x) for x in imp_x])
    geo.setGlobalAttribValue("imp_z", [float(x) for x in imp_z])
geo.addAttrib(hou.attribType.Global, "rg_ouvrages_modele", "")
geo.setGlobalAttribValue("rg_ouvrages_modele", chemin.replace(chr(92), "/"))
'''
