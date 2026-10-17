"""Construit l'HDA rg::sol::1.0 (sol étanche du générateur : triangulation contrainte en (s, t), Z du modèle unique,
marches fermées sous les éléments) ; hython Houdini 22.

    hython recon/generateur/hda/rg_sol/construire.py

Réseau (recon/generateur/hda/README_RG.md § 5) :
    entrée 1 références (rg::graphe), 2 niveaux (rg::nivellement : sections, ralentisseurs, files de bordures)
      -> contraintes (VEX 64 bits, détail : plan des paramètres (s, −t) ; contour, lignes de rupture, zones sous les
         bordures et caniveaux) -> souder (Fuse) -> trianguler (Triangulate 2D contraint, raffiné, angle min 25°)
      -> classer (VEX : zone de chaque triangle : bande, abord, sol prolongé sous la bordure, surface de caniveau
         relevée, sol caché sous les éléments) -> altitude (VEX : Z du modèle unique, rg_niveau.h, par sommet)
      -> scinder (Split Points : marches) -> murs (VEX : faces verticales entre les deux copies d'une arête de
         marche) -> monde (VEX : (s, t, Z) -> Houdini) -> Normal (30°) -> uv (mètres) -> SOL
    BEV : bev (VEX : dalles et plots sur le trottoir des abaissés) -> BEV (sortie 2)
Sol « étanche » : une seule nappe 2-variété ; les arêtes de bord ne sont que sur le contour extérieur (TQ-SOL-009) ;
les marches de bordure sont fermées par des murs cachés dans les éléments (la chaussée passe sous la bordure jusqu'à
l'arrière moins 12 mm, le trottoir sous la tête sur 12 mm, TQ-BOR-007 ; sous un caniveau : sol caché 20 cm sous le
pied). Les lignes de rupture sont des arêtes contraintes (TQ-SOL-003).
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "commun"))
sys.path.insert(0, str(ICI.parents[1]))
import rg_hda_outils as R  # noqa: E402
import regles  # noqa: E402

NOM = "sol"

VEX_CONTRAINTES = r"""
// contraintes (détail) : plan des paramètres P = (s + décalage de la route, 0, −t). Groupes :
//   contour (polygone extérieur : profil + abords), lignes (polylignes de rupture et contours des zones),
//   zones (polygones des zones sous les bordures : z_type 1 sol bas prolongé sous la bordure, 2 surface de caniveau
//   relevée par un ralentisseur, 3 sol caché sous caniveau et bordure ; priorite 1, 2, 3 ; chaine : primitive de la
//   file de bordure dans l'entrée 3).
// Entrées : 0 références, 1 niveaux (rg::nivellement : sections, ralentisseurs, bordures).
float rampe = detail(1, "rg_rampe_plateau_pct");
float rh = chf("../recouvrement_tete");
addprimattrib(0, "route", "");
addprimattrib(0, "z_type", 0);
addprimattrib(0, "priorite", 0);
addprimattrib(0, "chaine", -1);
addpointattrib(0, "s", 0.0);
addpointattrib(0, "t", 0.0);
string R_id[];
float R_off[], R_L[];
float off = 0.0;
for (int pr = 0; pr < nprimitives(0); pr++) {
    if (!inprimgroup(0, "echantillonnees", pr)) continue;
    string rid = prim(0, "id", pr);
    float L = prim(0, "longueur_m", pr);
    float SEC0[] = prim(0, "sec_s0", pr);
    float SEC1[] = prim(0, "sec_s1", pr);
    string SP[] = prim(0, "sec_profil", pr);
    int ns = len(SEC0);
    push(R_id, rid); push(R_off, off); push(R_L, L);
    // abscisses : échantillons de la référence, bornes des sections, des abaissés (rampants) et des ralentisseurs
    float SB[];
    int rpts[] = primpoints(0, pr);
    foreach (int p; rpts) { float sv = point(0, "s", p); push(SB, sv); }
    foreach (float x; SEC0) push(SB, x);
    push(SB, L);
    float bv[] = rg_bornes_verticales(1, rid, rampe);
    foreach (float x; bv) if (x > 0 && x < L) push(SB, x);
    float TR[];                                   // lignes transversales de rupture (bords de rampe et de bateau)
    foreach (float x; bv) if (x > 0 && x < L) push(TR, x);
    for (int k = 0; k < ns; k++) {
        int sp = rg_point_section(1, rid, k);
        float a0[] = point(1, "a_s0", sp);
        float a1[] = point(1, "a_s1", sp);
        float ar[] = point(1, "a_r", sp);
        int ac[] = point(1, "a_couvert", sp);
        for (int i = 0; i < len(a0); i++) {
            float c[] = array(a0[i] - ar[i], a0[i], a1[i], a1[i] + ar[i]);
            if (ac[i]) c = array(a0[i], a1[i]);
            foreach (float x; c) if (x > 0 && x < L) { push(SB, x); push(TR, x); }
        }
    }
    SB = sort(SB);
    float S[];
    foreach (float x; SB) if (len(S) == 0 || x - S[-1] > 1e-7) push(S, x);
    // ---- contour : bord gauche (s croissant) puis bord droit (s décroissant), sections et abords
    vector cg[], cd[];
    for (int k = 0; k < ns; k++) {
        int sp = rg_point_section(1, rid, k);
        float ag = point(1, "abord_g", sp), ad = point(1, "abord_d", sp);
        foreach (float s; S) {
            if (s < SEC0[k] - 1e-9 || s > SEC1[k] + 1e-9) continue;
            float T[] = rg_t_limites(1, sp, s);
            push(cg, set(s + off, 0, -(T[0] + ag)));
            push(cd, set(s + off, 0, -(T[-1] - ad)));
        }
    }
    int pc[];
    foreach (vector v; cg) { int q = addpoint(0, v); setpointattrib(0, "s", q, v.x - off); setpointattrib(0, "t", q, -v.z); push(pc, q); }
    for (int i = len(cd) - 1; i >= 0; i--) { int q = addpoint(0, cd[i]); setpointattrib(0, "s", q, cd[i].x - off); setpointattrib(0, "t", q, -cd[i].z); push(pc, q); }
    int pcont = addprim(0, "poly", pc);
    setprimgroup(0, "contour", pcont, 1);
    setprimattrib(0, "route", pcont, rid);
    // ---- lignes longitudinales : limites sans bordure réelle (ruptures de dévers, changements de revêtement,
    // marquages, rives extérieures) ; les limites bordées sont remplacées par les contours des zones
    for (int k = 0; k < ns; k++) {
        int sp = rg_point_section(1, rid, k);
        int lb[] = point(1, "l_bord", sp);
        float ss[];
        foreach (float s; S) if (s >= SEC0[k] - 1e-9 && s <= SEC1[k] + 1e-9) push(ss, s);
        for (int l = 0; l < len(lb); l++) {
            if (lb[l] == 1) continue;
            int pts[];
            foreach (float s; ss) {
                float T[] = rg_t_limites(1, sp, s);
                int q = addpoint(0, set(s + off, 0, -T[l]));
                setpointattrib(0, "s", q, s); setpointattrib(0, "t", q, T[l]);
                push(pts, q);
            }
            int pl = addprim(0, "polyline", pts);
            setprimgroup(0, "lignes", pl, 1);
            setprimattrib(0, "route", pl, rid);
        }
    }
    // ---- lignes transversales : jonctions de sections et ruptures (pleine largeur)
    float TT[];
    for (int k = 1; k < ns; k++) push(TT, SEC0[k]);
    foreach (float x; TR) push(TT, x);
    foreach (float x; TT) {
        int k0 = rg_indice_section(SEC0, x - 1e-7);
        int k1 = rg_indice_section(SEC0, x + 1e-7);
        float tmax = -1e9, tmin = 1e9;
        int kk[] = array(k0, k1);
        foreach (int k; kk) {
            int sp = rg_point_section(1, rid, k);
            float ag = point(1, "abord_g", sp), ad = point(1, "abord_d", sp);
            float T[] = rg_t_limites(1, sp, x);
            tmax = max(tmax, T[0] + ag);
            tmin = min(tmin, T[-1] - ad);
        }
        int qa = addpoint(0, set(x + off, 0, -tmax));
        int qb = addpoint(0, set(x + off, 0, -tmin));
        setpointattrib(0, "s", qa, x); setpointattrib(0, "t", qa, tmax);
        setpointattrib(0, "s", qb, x); setpointattrib(0, "t", qb, tmin);
        int pl = addprim(0, "polyline", array(qa, qb));
        setprimgroup(0, "lignes", pl, 1);
        setprimattrib(0, "route", pl, rid);
    }
    // ---- zones sous les files de bordures (entrée 1, groupe bordures)
    for (int c = 0; c < nprimitives(1); c++) {
        string croute = prim(1, "route", c), cid = prim(1, "id", c);
        int cfermee = prim(1, "fermee", c);
        if (!inprimgroup(1, "bordures", c) || croute != rid) continue;
        // file fermée (îlot isolé : la bordure en fait le tour) : parcourue comme une file ouverte qui se referme sur
        // son premier point, onglet à la fermeture (correction après contrôle : sans zone, le sol du terre-plein passait
        // au travers de la bordure, dents de scie le long des chartières des îlots de S_M24 et S_M27)
        int cp0[] = primpoints(1, c);
        if (cfermee && len(cp0) > 2) push(cp0, cp0[0]);
        float base = prim(1, "base", c);
        float u2 = base - rh;
        vector2 Q[];
        float CW[], KA[];
        int CAN[], KIND[];
        int cp[];
        foreach (int p; cp0) {
            float sv = point(1, "s_ref", p), tv = point(1, "t_ref", p);
            float w = point(1, "wcp", p), ka = point(1, "kappa", p);
            int cn = point(1, "can", p), kd = point(1, "kind", p);
            // point de raccord doublé (angle d'un retour de bordure) : un seul point, caniveau s'il est posé d'un côté
            // (la suite à caniveau commence à l'angle), pièce longitudinale si l'une l'est
            if (len(Q) > 0 && length(set(sv, tv) - Q[-1]) < 1e-9) {
                CAN[-1] = max(CAN[-1], cn);
                KIND[-1] = min(KIND[-1], kd);
                CW[-1] = max(CW[-1], w);
                continue;
            }
            push(cp, p);
            push(Q, set(sv, tv));
            push(CW, w);
            push(KA, ka);
            push(CAN, cn);
            push(KIND, kd);
        }
        int n = len(cp);
        // normales à gauche (côté haut) en onglet
        vector2 M[];
        for (int i = 0; i < n; i++) {
            vector2 na = {0, 0}, nb_ = {0, 0};
            if (i > 0) { vector2 d = normalize(Q[i] - Q[i - 1]); na = set(-d.y, d.x); }
            if (i < n - 1) { vector2 d = normalize(Q[i + 1] - Q[i]); nb_ = set(-d.y, d.x); }
            if (i == 0) na = nb_;
            if (i == n - 1) nb_ = na;
            if (cfermee && n > 3) {
                if (i == 0) { vector2 d = normalize(Q[n - 1] - Q[n - 2]); na = set(-d.y, d.x); }
                if (i == n - 1) { vector2 d = normalize(Q[1] - Q[0]); nb_ = set(-d.y, d.x); }
            }
            float den = 1.0 + dot(na, nb_);
            push(M, den > 1e-6 ? (na + nb_) / den : na);
        }
        // segments : caniveau posé si les deux extrémités l'ont ; suites (runs) d'état constant. Zones d'une suite :
        //   bordure [0, u2] (normales en onglet, comme les décalés de la file) : sol caché (3) si caniveau posé,
        //   sinon sol bas prolongé sous la bordure (1) ;
        //   caniveau [−largeur (+ recouvrement en courbe), 0] (normales des segments aux extrémités de la suite :
        //   jamais de diagonale d'onglet du côté bas, qui croiserait la face d'un retour de bordure) : sol caché (3) si
        //   posé, surface de caniveau relevée (2) s'il est interrompu par un ralentisseur.
        int i0 = 0;
        while (i0 < n - 1) {
            int etat = CAN[i0] && CAN[i0 + 1];
            int i1 = i0 + 1;
            while (i1 < n - 1 && (CAN[i1] && CAN[i1 + 1]) == etat) i1++;
            int pz[];
            for (int i = i0; i <= i1; i++) {
                int q = addpoint(0, set(Q[i].x + off, 0, -Q[i].y)); setpointattrib(0, "s", q, Q[i].x); setpointattrib(0, "t", q, Q[i].y);
                push(pz, q);
            }
            for (int i = i1; i >= i0; i--) {
                vector2 x = Q[i] + u2 * M[i];
                int q = addpoint(0, set(x.x + off, 0, -x.y)); setpointattrib(0, "s", q, x.x); setpointattrib(0, "t", q, x.y);
                push(pz, q);
            }
            int z = addprim(0, "poly", pz);
            setprimgroup(0, "zones", z, 1);
            setprimattrib(0, "route", z, rid);
            setprimattrib(0, "z_type", z, etat ? 3 : 1);
            setprimattrib(0, "priorite", z, etat ? 3 : 1);
            setprimattrib(0, "chaine", z, c);
            // caniveau de la suite : toute la suite sur une pièce longitudinale à caniveau déclaré (pas les retours
            // de bordure, ni le point d'angle qu'une suite transversale partage avec la pièce à caniveau)
            int zc = 1;
            for (int i = i0; i <= i1; i++) if (CW[i] <= 0.0 || KIND[i] != 0) zc = 0;
            if (etat) zc = 1;
            if (zc) {
                int pw[];
                for (int i = i0; i <= i1; i++) {
                    vector2 nn = M[i];
                    if (i == i0) { vector2 d = normalize(Q[i + 1] - Q[i]); nn = set(-d.y, d.x); }
                    if (i == i1) { vector2 d = normalize(Q[i] - Q[i - 1]); nn = set(-d.y, d.x); }
                    float rc = 0.0;
                    if (etat && KA[i] != 0.0) {
                        // recouvrement du caniveau en courbe convexe côté chaussée : flèche d'une corde de 1 m
                        float Rc = abs(1.0 / KA[i] - Q[i].y);
                        rc = (KA[i] > 0.0) == (nn.y > 0.0) ? 1.0 / (8.0 * max(Rc, 1.0)) : 0.0;
                    }
                    vector2 x = Q[i] - (CW[i] - rc) * nn;
                    int q = addpoint(0, set(x.x + off, 0, -x.y)); setpointattrib(0, "s", q, x.x); setpointattrib(0, "t", q, x.y);
                    push(pw, q);
                }
                for (int i = i1; i >= i0; i--) {
                    int q = addpoint(0, set(Q[i].x + off, 0, -Q[i].y)); setpointattrib(0, "s", q, Q[i].x); setpointattrib(0, "t", q, Q[i].y);
                    push(pw, q);
                }
                int z2 = addprim(0, "poly", pw);
                setprimgroup(0, "zones", z2, 1);
                setprimattrib(0, "route", z2, rid);
                setprimattrib(0, "z_type", z2, etat ? 3 : 2);
                setprimattrib(0, "priorite", z2, etat ? 3 : 2);
                setprimattrib(0, "chaine", z2, c);
            }
            i0 = i1;
        }
    }
    off += L + 50.0;
}
setdetailattrib(0, "rg_routes", R_id);
setdetailattrib(0, "rg_decalages", R_off);
setdetailattrib(0, "rg_longueurs", R_L);
"""

VEX_LIGNES_ZONES = r"""
// lignes_zones (primitive, groupe zones) : contour de chaque zone recopié en polyligne fermée (groupe lignes) pour la
// triangulation contrainte (les zones elles-mêmes servent au classement des triangles).
int pts[] = primpoints(0, @primnum);
int q[];
foreach (int p; pts) push(q, addpoint(0, p));
push(q, q[0]);
int pl = addprim(0, "polyline", q);
setprimgroup(0, "lignes", pl, 1);
setprimgroup(0, "zones", pl, 0);
setprimattrib(0, "route", pl, s@route);
"""

VEX_CLASSER = r"""
// classer (primitive) : zone de chaque triangle (centre de gravité) : zones de bordure (entrée 1, priorité la plus
// haute), sinon bande de la section en s (limites en t), sinon abord gauche ou droit.
// Entrées : 0 triangles, 1 zones, 2 niveaux, 3 références.
vector c = @P;                                    // centre de gravité (wrangle de primitives)
string routes[] = detail(1, "rg_routes");
float offs[] = detail(1, "rg_decalages");
float Ls[] = detail(1, "rg_longueurs");
int ir = 0;
for (int i = 0; i < len(offs); i++) if (c.x >= offs[i] - 25.0) ir = i;
string rid = routes[ir];
float s = c.x - offs[ir], t = -c.z;
i@z_type = 0;
i@chaine = -1;
i@section = -1;
i@bande = -1;
s@route = rid;
vector hits[];
int hp[];
vector uvs[];
int nh = intersect_all(1, set(c.x, 1.0, c.z), {0, -2, 0}, hits, hp, uvs, 1e-6, 1e-6);
int best = 0;
for (int i = 0; i < nh; i++) {
    int pz = prim(1, "priorite", hp[i]);
    if (pz > best) { best = pz; i@z_type = prim(1, "z_type", hp[i]); i@chaine = prim(1, "chaine", hp[i]); }
}
int pr = findattribval(3, "prim", "id", rid);
float SEC0[] = prim(3, "sec_s0", pr);
string SP[] = prim(3, "sec_profil", pr);
int k = rg_indice_section(SEC0, s);
i@section = k;
int sp = rg_point_section(2, rid, k);
float T[] = rg_t_limites(2, sp, s);
string mats[] = point(2, "b_mat", sp);
string bids[] = point(2, "b_id", sp);
string btys[] = point(2, "b_type", sp);
int b = -1;
for (int i = 0; i + 1 < len(T); i++) if (t <= T[i] && t >= T[i + 1]) { b = i; break; }
if (b < 0) b = t > T[0] ? -1 : -2;
i@bande = b;
string mat = "";
if (b >= 0) { mat = mats[b]; s@bande_id = bids[b]; s@classe = btys[b]; }
else if (b == -1) { mat = point(2, "abord_g_mat", sp); s@bande_id = "abord_gauche"; s@classe = "abord"; }
else { mat = point(2, "abord_d_mat", sp); s@bande_id = "abord_droit"; s@classe = "abord"; }
if (i@z_type == 3) { mat = "sol_cache"; s@classe = "sous_element"; }
else if (i@z_type == 1) s@classe = "sous_bordure";
else if (i@z_type == 2) {
    // caniveau relevé par un ralentisseur : caniveau à grille dans l'emprise du caniveau, fil d'eau continu dessous
    // (décret 94-447 annexe art. 4, source de RF-MA-RAL-001 ; moyen [G], règle demandée au propriétaire de la base)
    s@classe = "caniveau_releve";
    mat = "grille_caniveau";
}
if (mat == "") mat = "PJ_Neutre";
s@materiau_id = mat;
i@visible = i@z_type == 0 || i@z_type == 2;
"""

VEX_ALTITUDE = r"""
// altitude (sommet) : Z du modèle unique au sommet, selon la zone du triangle (rg_niveau.h) ; f@zv (sommet).
// Entrées : 0 triangles classés, 1 niveaux, 2 références, 3 zones.
float rampe = detail(1, "rg_rampe_plateau_pct");
int pr = @primnum;
int pt = vertexpoint(0, @vtxnum);
vector P = point(0, "P", pt);
string rid = prim(0, "route", pr);
float offs[] = detail(3, "rg_decalages");
string routes[] = detail(3, "rg_routes");
float off = offs[find(routes, rid)];
float s = P.x - off, t = -P.z;
int zt = prim(0, "z_type", pr);
int k = prim(0, "section", pr);
int b = prim(0, "bande", pr);
int ch = prim(0, "chaine", pr);
int rp = findattribval(2, "prim", "id", rid);
string SP[] = prim(2, "sec_profil", rp);
float z = 0.0;
float T[], A[], G[], PIED[], TETE[], VUE[], dz;
int CLS[];
string msg;
if (zt == 0) {
    int sp = rg_point_section(1, rid, k);
    if (!rg_coupe(1, sp, 1, sp, 1, rid, s, rampe, T, A, G, CLS, PIED, TETE, VUE, dz, msg)) error("%s", msg);
    if (b >= 0) z = rg_z_bande(A, G, CLS, dz, b, t);
    else z = rg_z_abord(T, A, G, CLS, dz, b == -1);
} else {
    // point de la file de bordure le plus proche (plan des paramètres) : section et bande basse, limite, pied
    int cp[] = primpoints(1, ch);
    float dmin = 1e18;
    int im = 0;
    float um = 0.0;
    for (int i = 0; i + 1 < len(cp); i++) {
        float sa = point(1, "s_ref", cp[i]), ta = point(1, "t_ref", cp[i]);
        float sb = point(1, "s_ref", cp[i + 1]), tb = point(1, "t_ref", cp[i + 1]);
        vector2 a = set(sa, ta);
        vector2 bb = set(sb, tb);
        vector2 d = bb - a;
        float l2 = dot(d, d);
        float u = l2 > 0 ? clamp(dot(set(s, t) - a, d) / l2, 0.0, 1.0) : 0.0;
        float dd = length(set(s, t) - (a + u * d));
        if (dd < dmin) { dmin = dd; im = i; um = u; }
    }
    int p0 = cp[im], p1 = cp[min(im + 1, len(cp) - 1)];
    if (zt == 3) {
        float z0 = point(1, "zemp", p0), z1 = point(1, "zemp", p1);
        z = lerp(z0, z1, um);
    } else {
        int pc = um < 0.5 ? p0 : p1;
        int kb = point(1, "k_bas", pc), bb = point(1, "b_bas", pc), lim = point(1, "limite", pc);
        int kind = point(1, "kind", pc);
        float wc = point(1, "wcp", pc), dhc = point(1, "dhcp", pc);
        int sp = rg_point_section(1, rid, kb);
        if (!rg_coupe(1, sp, 1, sp, 1, rid, s, rampe, T, A, G, CLS, PIED, TETE, VUE, dz, msg)) error("%s", msg);
        if (zt == 1) {
            // sol bas prolongé sous la bordure : fil d'eau relevé (caniveau déclaré) ou chaussée prolongée
            z = (kind == 0 && wc > 0.0) ? PIED[lim] + dz : rg_z_bande(A, G, CLS, dz, bb, t);
        } else {
            // surface de caniveau relevée (ralentisseur) : de l'arête (u = −largeur, chaussée) au fil d'eau (face)
            int lh[] = point(1, "l_h", sp);
            float u = lh[lim] * (t - T[lim]);
            float a = clamp(-u / max(wc, 1e-6), 0.0, 1.0);
            z = PIED[lim] + dz + dhc * a;
        }
    }
}
f@zv = z;
"""

VEX_MOYENNE = r"""
// z_points (point) : Z du point = moyenne des Z de ses sommets (sommets d'un même point après scission : égaux à
// la tolérance près) ; P reste dans le plan des paramètres (y = Z).
int vs[] = pointvertices(0, @ptnum);
float sz = 0;
foreach (int v; vs) sz += vertex(0, "zv", v);
@P.y = sz / max(len(vs), 1);
"""

VEX_MURS = r"""
// murs (détail) : chaque arête de marche (scindée : deux arêtes de bord confondues en plan, d'orig a-b et b-a) est
// fermée par une face verticale entre ses deux copies ; nappe 2-variété, arêtes de bord sur le contour seulement.
int np = nprimitives(0);
dict vu;
int n_murs = 0;
// copies de chaque point d'origine (sommets scindés) : une marche entre deux copies doit passer par les copies
// intermédiaires (trois surfaces ou plus au même point : sinon arête verticale en T)
dict copies;
for (int p = 0; p < npoints(0); p++) {
    string k = itoa(point(0, "pt_orig", p));
    int l[];
    if (isvalidindex(copies, k)) l = copies[k];
    push(l, p);
    copies[k] = l;
}
for (int pr = 0; pr < np; pr++) {
    int pts[] = primpoints(0, pr);
    int n = len(pts);
    for (int i = 0; i < n; i++) {
        int a = pts[i], b = pts[(i + 1) % n];
        int h = pointhedge(0, a, b);
        if (h < 0 || hedge_equivcount(0, h) != 1) continue;   // arête intérieure partagée : pas de marche
        int oa = point(0, "pt_orig", a), ob = point(0, "pt_orig", b);
        string cle = sprintf("%d_%d", ob, oa);                  // arête opposée cherchée
        if (isvalidindex(vu, cle)) {
            // demi-arête opposée a_s -> b_s rangée : a_s copie de b, b_s copie de a. Mur (b, a, b_s, a_s) : contient
            // b -> a et b_s -> a_s (sens opposés aux deux demi-arêtes de bord), triangle si une copie est commune.
            int ab[] = vu[cle];
            int a_s = ab[0], b_s = ab[1];
            int q2[];
            push(q2, b); push(q2, a);
            // copies intermédiaires de a (entre a et b_s), puis de b (entre a_s et b), triées le long du mur
            vector pa = point(0, "P", a), pbs = point(0, "P", b_s), pas_ = point(0, "P", a_s), pb = point(0, "P", b);
            float za = pa.y, zbs = pbs.y;
            int ca[] = copies[itoa(point(0, "pt_orig", a))];
            float zs[];
            int ps[];
            foreach (int c; ca) {
                vector pc = point(0, "P", c);
                float zc = pc.y;
                if (c != a && c != b_s && zc > min(za, zbs) && zc < max(za, zbs)) { push(zs, abs(zc - za)); push(ps, c); }
            }
            int o[] = argsort(zs);
            foreach (int i; o) push(q2, ps[i]);
            if (b_s != a) push(q2, b_s);
            float zas = pas_.y, zb = pb.y;
            int cb[] = copies[itoa(point(0, "pt_orig", b))];
            resize(zs, 0);
            resize(ps, 0);
            foreach (int c; cb) {
                vector pc = point(0, "P", c);
                float zc = pc.y;
                if (c != b && c != a_s && zc > min(zas, zb) && zc < max(zas, zb)) { push(zs, abs(zc - zas)); push(ps, c); }
            }
            if (a_s != b) push(q2, a_s);
            o = argsort(zs);
            foreach (int i; o) push(q2, ps[i]);
            if (len(q2) >= 3) {
                int w = addprim(0, "poly", q2);
                setprimattrib(0, "z_type", w, 4);
                setprimattrib(0, "materiau_id", w, "sol_cache");
                setprimattrib(0, "classe", w, "mur");
                setprimattrib(0, "visible", w, 0);
                string rr = prim(0, "route", pr);
                setprimattrib(0, "route", w, rr);
                n_murs++;
            }
            removeindex(vu, cle);
        } else {
            int paire[] = array(a, b);
            vu[sprintf("%d_%d", oa, ob)] = paire;
        }
    }
}
setdetailattrib(0, "rg_sol_murs", n_murs);
setdetailattrib(0, "rg_sol_aretes_sans_paire", len(keys(vu)));
"""

VEX_MONDE = r"""
// monde (point) : (s, t, Z) du plan des paramètres -> Houdini (x, Z, −y), géométrie régulière exacte (rg_niveau.h).
// Entrées : 0 sol, 1 références, 2 zones (décalages des routes).
float offs[] = detail(2, "rg_decalages");
string routes[] = detail(2, "rg_routes");
int ir = 0;
for (int i = 0; i < len(offs); i++) if (@P.x >= offs[i] - 25.0) ir = i;
float s = @P.x - offs[ir], t = -@P.z;
int pr = findattribval(1, "prim", "id", routes[ir]);
vector2 xy = rg_local_st(1, pr, s, t);
f@s = s;
f@t = t;
@P = set(xy.x, @P.y, -xy.y);
"""

VEX_NORMALES = r"""
// normales_bandes (sommet) : TQ-SOL-008 — sur les faces de bande (z_type 0), normale issue du gradient analytique du
// modèle unique (rg_niveau.h) : dérivées de la position (rg_local_st) et du Z de la bande de la face, en s du côté de
// la face (cassures des rampes et des bateaux) et en t (dévers de la bande) ; murs, sol caché et abords gardent la
// normale du maillage (cusp 30°). Entrées : 0 sol, 1 niveaux, 2 références.
int pr = @primnum;
if (prim(0, "z_type", pr) == 0 && prim(0, "bande", pr) >= 0) {
    float rampe = detail(1, "rg_rampe_plateau_pct");
    string rid = prim(0, "route", pr);
    int k = prim(0, "section", pr);
    int b = prim(0, "bande", pr);
    int pt = vertexpoint(0, @vtxnum);
    float s = point(0, "s", pt), t = point(0, "t", pt);
    int pts[] = primpoints(0, pr);
    float sc = 0.0;
    foreach (int q; pts) { float sq = point(0, "s", q); sc += sq; }
    sc /= max(len(pts), 1);
    int rp = findattribval(2, "prim", "id", rid);
    float L = prim(2, "longueur_m", rp);
    int sp = rg_point_section(1, rid, k);
    float h = 0.005;
    float sa = s, sb = s;
    if (sc >= s) sb = min(s + h, L); else sa = max(s - h, 0.0);
    if (sb - sa < 1e-6) { sa = max(s - h, 0.0); sb = min(s + h, L); }
    float T[], A[], G[], PIED[], TETE[], VUE[], dz;
    int CLS[];
    string msg;
    if (!rg_coupe(1, sp, 1, sp, 1, rid, sa, rampe, T, A, G, CLS, PIED, TETE, VUE, dz, msg)) error("%s", msg);
    float za = rg_z_bande(A, G, CLS, dz, b, t);
    if (!rg_coupe(1, sp, 1, sp, 1, rid, sb, rampe, T, A, G, CLS, PIED, TETE, VUE, dz, msg)) error("%s", msg);
    float zb = rg_z_bande(A, G, CLS, dz, b, t);
    vector2 Ps = (rg_local_st(2, rp, sb, t) - rg_local_st(2, rp, sa, t)) / (sb - sa);
    vector2 Pt = (rg_local_st(2, rp, s, t + h) - rg_local_st(2, rp, s, t - h)) / (2.0 * h);
    vector ts = set(Ps.x, Ps.y, (zb - za) / (sb - sa));
    vector tt = set(Pt.x, Pt.y, G[b]);
    vector n = normalize(cross(ts, tt));
    v@N = set(n.x, n.z, -n.y);
}
"""

VEX_UV = r"""
// uv (sommet) : mètres (E3) ; faces de dessus : (x, y) locaux ; faces raides (murs) : plan de la face.
vector n = prim_normal(0, @primnum, {0.5, 0.5, 0});
if (abs(n.y) > 0.5) {
    v@uv = set(@P.x, -@P.z, 0);
} else {
    vector tt = normalize(cross({0, 1, 0}, n));
    v@uv = set(dot(@P, tt), @P.y, 0);
}
"""

VEX_EXPORT = r"""
// export (primitive) : attributs du contrat de branche (README_HDA § 4) : couche, entité, maillage.
s@pj_couche = chs("../couche");
s@pj_entite = sprintf("SOL_%s", re_replace("[^A-Za-z0-9]", "_", s@route));
s@pj_maillage = s@materiau_id;
"""

VEX_BEV = r"""
// bev (détail) : bandes d'éveil de vigilance (ARR2007 art. 1, 4° ; RF-MA-BEV-002, DEF-031) sur le trottoir des
// abaissés marqués « bev » : parallèles à la bordure, à 0,50 m du nez, profondeur 0,5875 m (0,40 si trottoir
// < 1,90 m), de s0 à s1 (jamais au-delà du marquage) ; dalle dont le dessus est 3 mm au-dessus du sol (E9), plots
// Ø 25 mm (h 5 mm) en quinconce au pas de 75 mm (pj::sol, GA-BEV-002/004). Sorties : polygones (dalles), points
// (plots, groupe plots) ; Z = surface haute du modèle unique (rg_niveau.h) + décalage.
// Entrées : 0 vide, 1 niveaux, 2 références.
float rampe = detail(1, "rg_rampe_plateau_pct");
float pas = chf("../bev_pas");
float dessus = chf("../bev_dessus_mm") / 1000.0;
float recul = chf("../bev_recul");
addprimattrib(0, "materiau_id", "");
addprimattrib(0, "id", "");
addprimattrib(0, "route", "");
addpointattrib(0, "id", "");
addvertexattrib(0, "uv", {0, 0, 0});
for (int pr = 0; pr < nprimitives(2); pr++) {
    if (!inprimgroup(2, "echantillonnees", pr)) continue;
    string rid = prim(2, "id", pr);
    float SEC0[] = prim(2, "sec_s0", pr);
    float SEC1[] = prim(2, "sec_s1", pr);
    string SP[] = prim(2, "sec_profil", pr);
    for (int k = 0; k < len(SEC0); k++) {
        int sp = rg_point_section(1, rid, k);
        int al[] = point(1, "a_lim", sp);
        float a0[] = point(1, "a_s0", sp);
        float a1[] = point(1, "a_s1", sp);
        int ab[] = point(1, "a_bev", sp);
        int lh[] = point(1, "l_h", sp);
        string bmat[] = point(1, "b_mat", sp);
        for (int i = 0; i < len(al); i++) {
            if (!ab[i]) continue;
            // BEV posée dans sa section seulement (correction après le second contrôle : un profil repris dans une autre
            // section reposait la même BEV hors de la section du passage)
            a0[i] = max(a0[i], SEC0[k]);
            a1[i] = min(a1[i], SEC1[k]);
            if (a1[i] - a0[i] < 0.05) continue;
            int l = al[i], h = lh[l];
            int hb = h > 0 ? l - 1 : l;
            string bid = sprintf("BEV-%s-%d-%d-%d", rid, k, l, i);
            // étendue : au droit de toute bordure de vue VISIBLE < 0,05 m, jamais au-delà du marquage (RF-MA-BEV-002) ;
            // vue visible = tête − chaussée au droit de la face (fil d'eau + dz si caniveau, ralentisseur compris) :
            // sur un plateau, les rampants laissent une vue de 0,02 à 0,12 m (correction après contrôle : BEV de S10
            // devant 0,055 m aux extrémités du marquage) ; bornes affinées par interpolation linéaire
            float vmax = chf("../bev_vue_max");
            int bbas = h > 0 ? l : l - 1;
            float lwcb[] = point(1, "l_wc", sp);
            float e0 = 1e9, e1 = -1e9, sp_ = 0.0, vp_ = 0.0;
            int nn = max(2, int(ceil((a1[i] - a0[i]) / 0.01)));
            for (int j = 0; j <= nn; j++) {
                float s = a0[i] + (a1[i] - a0[i]) * j / nn;
                float T[], A[], G[], PIED[], TETE[], VUE[], dz;
                int CLS[];
                string msg;
                if (!rg_coupe(1, sp, 1, sp, 1, rid, s, rampe, T, A, G, CLS, PIED, TETE, VUE, dz, msg)) error("%s", msg);
                float zb = lwcb[l] > 0.0 ? PIED[l] + dz : rg_z_bande(A, G, CLS, dz, bbas, T[l]);
                float vis = TETE[l] - zb;
                int dedans = vis < vmax - 1e-9;
                if (dedans) {
                    float sa = s;
                    if (j > 0 && vp_ >= vmax - 1e-9) sa = sp_ + (s - sp_) * (vp_ - vmax) / max(vp_ - vis, 1e-12);
                    e0 = min(e0, sa);
                    e1 = max(e1, s);
                } else if (j > 0 && vp_ < vmax - 1e-9) {
                    e1 = max(e1, sp_ + (s - sp_) * (vmax - vp_) / max(vis - vp_, 1e-12));
                }
                sp_ = s; vp_ = vis;
            }
            if (e1 - e0 < 0.05) continue;
            a0[i] = e0;
            a1[i] = e1;
            int nsg = max(2, int(ceil((a1[i] - a0[i]) / 0.10)));
            // largeur du trottoir au droit de l'abaissé (profondeur réduite si < 1,90 m, RF-MA-BEV-002)
            float Tm[] = rg_t_limites(1, sp, 0.5 * (a0[i] + a1[i]));
            float wtr = abs(Tm[hb] - Tm[hb + 1]);
            float prof = wtr < 1.90 ? 0.40 : 0.5875;
            float u0 = recul, u1 = recul + prof;
            int nu = max(2, int(ceil(prof / 0.10)));
            int grille[];
            vector guv[];
            for (int j = 0; j <= nsg; j++) {
                float s = a0[i] + (a1[i] - a0[i]) * j / nsg;
                float T[], A[], G[], PIED[], TETE[], VUE[], dz;
                int CLS[];
                string msg;
                if (!rg_coupe(1, sp, 1, sp, 1, rid, s, rampe, T, A, G, CLS, PIED, TETE, VUE, dz, msg)) error("%s", msg);
                for (int q = 0; q <= nu; q++) {
                    float u = u0 + (u1 - u0) * q / nu;
                    float t = T[l] + h * u;
                    float z = rg_z_bande(A, G, CLS, dz, hb, t) + dessus;
                    vector2 xy = rg_local_st(2, pr, s, t);
                    push(grille, addpoint(0, set(xy.x, z, -xy.y)));
                    // UV : u = longueur le long de la bordure depuis le début de la BEV (m), v = 0 côté nez à 1 au fond
                    // (dalles podotactiles le long de la bordure, quel que soit le tracé)
                    push(guv, set(s - a0[i], float(q) / nu, 0));
                }
            }
            for (int j = 0; j < nsg; j++) {
                for (int q = 0; q < nu; q++) {
                    int a = grille[j * (nu + 1) + q], b = grille[(j + 1) * (nu + 1) + q];
                    int c = grille[(j + 1) * (nu + 1) + q + 1], d = grille[j * (nu + 1) + q + 1];
                    int ia = j * (nu + 1) + q, ib = (j + 1) * (nu + 1) + q, ic = (j + 1) * (nu + 1) + q + 1, id_ = j * (nu + 1) + q + 1;
                    int ord[] = h > 0 ? array(ia, id_, ic, ib) : array(ia, ib, ic, id_);
                    int f = h > 0 ? addprim(0, "poly", array(a, d, c, b)) : addprim(0, "poly", array(a, b, c, d));
                    for (int w = 0; w < 4; w++) setvertexattrib(0, "uv", f, w, guv[ord[w]]);
                    setprimattrib(0, "materiau_id", f, "bev_podotactile");
                    setprimattrib(0, "id", f, bid);
                    setprimattrib(0, "route", f, rid);
                    // revêtement voisin (bande où la BEV est posée) : la teinte de la BEV en contraste avec lui
                    // (RF-MA-OBS-003, contraste ≥ 0,40 ; correction après le second contrôle)
                    setprimattrib(0, "materiau_voisin", f, bmat[hb]);
                    setprimgroup(0, "dalles", f, 1);
                }
            }
            // plots en quinconce (pas 75 mm) : demi-pas de marge aux bords
            int nps = int(floor((a1[i] - a0[i]) / pas));
            int npu = int(floor(prof / pas));
            float ms = 0.5 * ((a1[i] - a0[i]) - (nps - 1) * pas);
            for (int j = 0; j < nps; j++) {
                float s = a0[i] + ms + j * pas;
                float T[], A[], G[], PIED[], TETE[], VUE[], dz;
                int CLS[];
                string msg;
                if (!rg_coupe(1, sp, 1, sp, 1, rid, s, rampe, T, A, G, CLS, PIED, TETE, VUE, dz, msg)) error("%s", msg);
                for (int q = 0; q < npu; q++) {
                    float u = u0 + 0.5 * pas + q * pas + ((j % 2) ? 0.5 * pas : 0.0);
                    if (u > u1 - 0.3 * pas) continue;
                    float t = T[l] + h * u;
                    float z = rg_z_bande(A, G, CLS, dz, hb, t) + dessus;
                    vector2 xy = rg_local_st(2, pr, s, t);
                    int p = addpoint(0, set(xy.x, z, -xy.y));
                    setpointgroup(0, "plots", p, 1);
                    setpointattrib(0, "id", p, bid);
                }
            }
        }
    }
}
"""


def parametres():
    T = hou
    F = T.FloatParmTemplate
    d31 = regles.valeur("DEF-031")
    return [
        F("arete_cible", "Arête cible (m)", 1, default_value=(0.25,), min=0.05, max=2.0,
          help="Triangulate 2D, taille cible des triangles (TQ-SOL-002 : 0,25 m sur trottoirs, rampes et îlots, 0,5 m "
               "sur chaussée ; une seule valeur pour tout le sol, la plus fine). Arête minimale du raffinement : 0,02 m "
               "(TQ-SOL-002 ; évite les aiguilles au croisement rasant de deux contraintes, TQ-SOL-009)."),
        F("angle_min", "Angle minimal (°)", 1, default_value=(25.0,), min=0.0, max=33.0, help="TQ-SOL-002 : 25°."),
        F("recouvrement_tete", "Trottoir sous la tête de bordure (m)", 1, default_value=(0.012,), min=0.0, max=0.1,
          help="Le trottoir commence sous la tête de la bordure, à l'arrière moins cette longueur (TQ-BOR-007 : 12 mm) ; "
               "la chaussée passe sous la bordure jusqu'à ce point (mur caché dans l'élément)."),
        F("tolerance_marche", "Tolérance de marche (m)", 1, default_value=(1e-5,), min=0.0, max=0.01,
          help="Écart de Z au-dessous duquel deux sommets d'un même point sont confondus (Split Points)."),
        T.StringParmTemplate("couche", "Couche USD", 1, default_value=("PJ_Sol",)),
        F("bev_recul", "BEV : distance au nez (m)", 1, default_value=(float(d31["BEV_recul_nez"]),), min=0.0, max=1.0,
          help="DEF-031 : 0,50 m (pas de freinage, RF-MA-BEV-002)."),
        F("bev_pas", "BEV : pas des plots (m)", 1, default_value=(0.075,), min=0.02, max=0.2,
          help="Plots en quinconce au pas de 75 mm (pj::sol, GA-BEV-004)."),
        F("bev_dessus_mm", "BEV : dessus au-dessus du sol (mm)", 1, default_value=(3.0,), min=0.0, max=5.0,
          help="E9 : dessus des dalles à moins de 5 mm du sol (pj::sol)."),
        F("bev_vue_max", "BEV : vue visible maximale de la bordure (m)", 1,
          default_value=(float(regles.valeur("RF-MA-TRO-015", "min_detectable")),), min=0.0, max=0.2,
          help="RF-MA-BEV-002 : BEV au droit de toute bordure de vue < 0,05 m, jamais au-delà du marquage ; 0,05 = "
               "vue minimale détectable (RF-MA-TRO-015)."),
    ]


def construire(dossier=ICI):
    sub = R.sous_reseau("rg_" + NOM)
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres()))
    e1, e4 = sub.indirectInputs()[:2]
    libs = ("rg_geometrie.h", "rg_niveau.h")
    con = R.wrangle(sub, "contraintes", VEX_CONTRAINTES, "detail", None, entrees=(e4,), bibliotheques=libs)
    con.setInput(0, e1)
    vid = sub.createNode("blast", "vider")                    # entrée 0 du wrangle : les références (vidées ensuite)
    vid.setInput(0, con)
    vid.parm("group").set("contour lignes zones")
    vid.parm("grouptype").set("prims")
    vid.parm("negate").set(1)
    nett = sub.createNode("attribdelete", "nettoyer_references")
    nett.setInput(0, vid)
    nett.parm("ptdel").set("* ^s ^t ^P")
    nett.parm("primdel").set("* ^route ^z_type ^priorite ^chaine")
    zones = sub.createNode("blast", "zones")
    zones.setInput(0, nett)
    zones.parm("group").set("zones")
    zones.parm("grouptype").set("prims")
    zones.parm("negate").set(1)
    lz = R.wrangle(sub, "lignes_zones", VEX_LIGNES_ZONES, "primitive", nett)
    lz.parm("group").set("zones")
    tri_in = sub.createNode("blast", "contour_et_lignes")
    tri_in.setInput(0, lz)
    tri_in.parm("group").set("contour lignes")
    tri_in.parm("grouptype").set("prims")
    tri_in.parm("negate").set(1)
    fu = sub.createNode("fuse::2.0", "souder")
    fu.setInput(0, tri_in)
    fu.parm("tol3d").set(1e-6)
    tri = sub.createNode("triangulate2d::3.0", "trianguler")
    tri.setInput(0, fu)
    for p, v in (("planepossrc", 1), ("dirx", 0.0), ("diry", 1.0), ("dirz", 0.0), ("useconstredges", 1),
                 ("constredges", "lignes"), ("useconstrpolys", 1), ("constrpolys", "contour"),
                 ("removefromconstrpolys", 1), ("refine", 1), ("trianglesize", 2), ("minedgelength", 0.02),
                 ("allowconstrsplit", 1), ("useexactconstruction", 1), ("maxnewpts", 1500000), ("updatenmls", 0),
                 ("keepprims", 0), ("removeunusedpoints", 1), ("removeduplicatepoints", 1)):
        tri.parm(p).set(v)
    tri.parm("targetedgelength").setExpression('ch("../arete_cible")')
    tri.parm("minangle").setExpression('ch("../angle_min")')
    det = sub.createNode("attribdelete", "attributs_triangulation")
    det.setInput(0, tri)
    det.parm("ptdel").set("* ^P")
    cpd = R.wrangle(sub, "decalages", 's[]@rg_routes = detail(1, "rg_routes"); f[]@rg_decalages = detail(1, "rg_decalages");'
                    ' f[]@rg_longueurs = detail(1, "rg_longueurs");', "detail", det, entrees=(nett,))
    cla = R.wrangle(sub, "classer", VEX_CLASSER, "primitive", cpd, entrees=(zones, e4, e1), bibliotheques=libs)
    alt = R.wrangle(sub, "altitude", VEX_ALTITUDE, "sommet", cla, entrees=(e4, e1, zones), bibliotheques=libs)
    orig = R.wrangle(sub, "origine", "i@pt_orig = @ptnum;", "point", alt)
    sp = sub.createNode("splitpoints", "scinder")
    sp.setInput(0, orig)
    sp.parm("useattrib").set(1)
    sp.parm("attribname").set("zv")
    sp.parm("tol").setExpression('ch("../tolerance_marche")')
    moy = R.wrangle(sub, "z_points", VEX_MOYENNE, "point", sp)
    murs = R.wrangle(sub, "murs", VEX_MURS, "detail", moy)
    mon = R.wrangle(sub, "monde", VEX_MONDE, "point", murs, entrees=(e1, cpd), bibliotheques=libs)
    nm = sub.createNode("normal", "normales")
    nm.setInput(0, mon)
    nm.parm("type").set(1)
    nm.parm("cuspangle").set(30.0)
    nb = R.wrangle(sub, "normales_bandes", VEX_NORMALES, "sommet", nm, entrees=(e4, e1), bibliotheques=libs)
    uv = R.wrangle(sub, "uv", VEX_UV, "sommet", nb)
    exp = R.wrangle(sub, "export", VEX_EXPORT, "primitive", uv)
    fin = sub.createNode("attribdelete", "attributs_internes")
    fin.setInput(0, exp)
    fin.parm("vtxdel").set("zv")
    out = sub.createNode("null", "SOL")
    out.setInput(0, fin)
    R.sortie(sub, out, 0, "sortie_sol")
    out.setDisplayFlag(True)
    vide = sub.createNode("null", "VIDE")
    bev = R.wrangle(sub, "bev", VEX_BEV, "detail", vide, entrees=(e4, e1), bibliotheques=libs)
    bvn = sub.createNode("attribdelete", "bev_attributs")
    bvn.setInput(0, bev)
    bvn.parm("ptdel").set("* ^P ^id")
    bvn.parm("primdel").set("* ^materiau_id ^id ^route ^materiau_voisin")
    bout = sub.createNode("null", "BEV")
    bout.setInput(0, bvn)
    R.sortie(sub, bout, 1, "sortie_bev")
    vz = sub.createNode("null", "ZONES")
    vz.setInput(0, nett)
    R.sortie(sub, vz, 2, "sortie_zones")
    R.ranger(sub)
    aide = ("Sol étanche du générateur : triangulation contrainte en (s, t) (lignes de rupture, contours des zones sous "
            "les éléments), Z du modèle unique (rg_niveau.h) par sommet, marches fermées par des murs cachés ; BEV en "
            "dalles et plots.")
    details = ("== Entrées ==\n\n1. Références (rg::graphe), 2. Niveaux (rg::nivellement : sections, "
               "ralentisseurs, bordures).\n\n== Sorties ==\n\n1. Sol : triangles et murs (Y haut) ; primitives route, z_type "
               "(0 bande ou abord, 1 sous bordure, 2 caniveau relevé, 3 sous élément, 4 mur), section, bande, bande_id, "
               "classe, materiau_id, visible, pj_couche, pj_entite, pj_maillage ; points s, t, pt_orig ; sommets N, uv. "
               "Détail rg_sol_murs, rg_sol_aretes_sans_paire.\n2. BEV : dalles (groupe dalles) et points des plots "
               "(groupe plots) ; materiau_voisin = revêtement de la bande où la BEV est posée (teinte de la BEV en "
               "contraste, RF-MA-OBS-003) ; BEV posée dans sa section seulement.\n3. Zones et contraintes (plan des paramètres, contrôle).\n\n"
               "Règles : TQ-SOL-002, TQ-SOL-003, TQ-SOL-009, TQ-SOL-013, TQ-BOR-007, DEF-031, RF-MA-BEV-002.")
    return R.creer_hda(sub, NOM, "RG Sol (nappe étanche sur le modèle unique)", parametres(), dossier, entrees=(2, 2),
                       sorties=3, aide=aide, details_aide=details, icone="SOP_triangulate2d",
                       etiquettes_entrees=("Références échantillonnées", "Niveaux"),
                       etiquettes_sorties=("Sol", "BEV", "Zones (contrôle)"))


if __name__ == "__main__":
    print(construire())
