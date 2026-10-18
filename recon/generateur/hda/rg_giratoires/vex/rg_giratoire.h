// rg_giratoire.h : géométrie des giratoires (lot L5 giratoires, HDA rg::giratoires et rg::giratoires_sol), recopiée en
// tête des wrangles après rg_geometrie.h, rg_niveau.h et rg_carrefour.h (#include "opdef:" impossible, README_HDA § 1).
// VEX 64 bits. Repère local (x, y) = Lambert-93 − origine ; Houdini (x, z, −y).
#ifndef RG_GIRATOIRE_H
#define RG_GIRATOIRE_H

// Pas angulaire d'un arc de rayon R : flèche ≤ fl et pas ≤ pasmax (radians).
function float rgi_pas(float R; float fl; float pasmax)
{
    float a = 2.0 * acos(clamp(1.0 - fl / max(R, 1e-6), -1.0, 1.0));
    return min(a, pasmax);
}

// Points intérieurs d'un arc de centre Cc de a vers b (rayon |a − Cc|) ; sens = 0 : arc le plus court ; sens = −1 :
// horaire ; sens = 1 : trigonométrique. Les bouts a et b ne sont pas rendus.
function vector2[] rgi_arc(vector2 Cc; vector2 a; vector2 b; int sens; float fl; float pasmax)
{
    vector2 v0 = a - Cc, v1 = b - Cc;
    float R = length(v0);
    float ang = atan2(rc_croix(v0, v1), dot(v0, v1));
    if (sens < 0 && ang > 0) ang -= 2.0 * PI;
    if (sens > 0 && ang < 0) ang += 2.0 * PI;
    float pas = rgi_pas(R, fl, pasmax);
    int ns = max(2, int(ceil(abs(ang) / pas - 1e-9)));
    vector2 out[];
    for (int i = 1; i < ns; i++) {
        float t = ang * i / ns;
        push(out, Cc + set(v0.x * cos(t) - v0.y * sin(t), v0.x * sin(t) + v0.y * cos(t)));
    }
    return out;
}

// Cercle fermé (sens trigonométrique, premier point répété à la fin) de centre O et de rayon R, départ à l'angle a0.
function vector2[] rgi_cercle(vector2 O; float R; float a0; float fl; float pasmax)
{
    float pas = rgi_pas(R, fl, pasmax);
    int n = max(12, int(ceil(2.0 * PI / pas - 1e-9)));
    vector2 out[];
    for (int i = 0; i <= n; i++) {
        float t = a0 + 2.0 * PI * (i % n) / n;
        push(out, O + R * set(cos(t), sin(t)));
    }
    return out;
}

// Congé de raccordement de rayon Rf tangent au bord de chaussée d'une branche (gauche = 1 : limite iL ; 0 : iR) de
// la route pr (routes : geo, profils : gp) et tangent extérieurement au cercle (O, R0) du bord extérieur de l'anneau
// (ACI : rayons d'entrée Re et de sortie Rs, RF-GV-GIR-003) ; droite locale du bord au point de tangence, itérée (lois
// de largeur : évasement de l'entrée et de la sortie). Sorties : abscisse s_tan et point T de tangence sur le bord,
// centre C, point K de tangence sur le cercle. Renvoie 0 si le congé n'existe pas.
function int rgi_conge(int geo; int pr; int gp; float sf; int gauche; vector2 O; float R0; float Rf;
                       export float s_tan; export vector2 T; export vector2 C; export vector2 K)
{
    float s = sf;
    int ok = 0;
    for (int it = 0; it < 40; it++) {
        float sc = clamp(s, 0.06, sf);
        vector2 E = rc_bord(geo, pr, gp, sc, gauche);
        vector2 u = -rc_bord_dir(geo, pr, gp, min(sc, sf - 0.05), gauche, 0.05);    // vers l'extérieur du carrefour
        vector2 m = gauche ? rc_gauche(-u) : -rc_gauche(-u);                          // hors de la chaussée
        vector2 D = E + Rf * m - O;
        float b = dot(D, u), c = dot(D, D) - (R0 + Rf) * (R0 + Rf);
        float disc = b * b - c;
        if (disc < 0) return 0;
        float x = -b + sqrt(disc);
        T = E + x * u;
        C = T + Rf * m;
        float sv, tv;
        rg_st_local(geo, pr, T.x, T.y, sv, tv);
        ok = 1;
        if (abs(sv - s) < 1e-8) { s = sv; break; }
        s = sv;
    }
    s_tan = s;
    K = O + R0 * normalize(C - O);
    return ok && s_tan > 0.0;
}

// Base (largeur au sol) d'un profil de bordure : table « profil:base, … » (table de pj::bordure), sinon défaut.
function float rgi_base(string tab[]; string prof; float defaut)
{
    foreach (string e; tab) {
        string kv[] = split(e, ":");
        if (len(kv) == 2 && kv[0] == prof) return atof(kv[1]);
    }
    return defaut;
}

// Modulation (trait, intervalle) d'une table « nom:trait:intervalle, … » ; continue : (0, 0).
function int rgi_modulation(string tab[]; string nom; export float tr; export float iv)
{
    tr = 0.0;
    iv = 0.0;
    foreach (string e; tab) {
        string kv[] = split(e, ":");
        if (len(kv) == 3 && kv[0] == nom) { tr = atof(kv[1]); iv = atof(kv[2]); return 1; }
    }
    return nom == "continue";
}

// Point d'un giratoire (groupe « giratoire ») par identifiant ; −1 sinon.
function int rgi_giratoire(int geo; string cid)
{
    foreach (int p; expandpointgroup(geo, "giratoire")) if (point(geo, "id", p) == cid) return p;
    return -1;
}

// Altitude du sol posé sous (x, y) : plus haute intersection verticale avec une face visible (hors BEV) ; ok = 0 sinon.
function float rgi_z_sol(int geo; vector2 q; export int ok)
{
    vector hits[], uvw[];
    int prs[];
    int nh = intersect_all(geo, "", set(q.x, 50.0, -q.y), {0, -100, 0}, hits, prs, uvw, 1e-6, 1e-6);
    float best = -1e18;
    ok = 0;
    int av = hasprimattrib(geo, "visible");
    int am = hasprimattrib(geo, "materiau_id");
    for (int i = 0; i < nh; i++) {
        if (av && prim(geo, "visible", prs[i]) == 0) continue;
        if (am && prim(geo, "materiau_id", prs[i]) == "bev_podotactile") continue;
        if (hits[i].y > best) { best = hits[i].y; ok = 1; }
    }
    if (!ok) {
        int ph;
        vector uv;
        xyzdist(geo, set(q.x, 0, -q.y), ph, uv);
        vector pz = primuv(geo, "P", ph, uv);
        return pz.y;
    }
    return best;
}

#endif
