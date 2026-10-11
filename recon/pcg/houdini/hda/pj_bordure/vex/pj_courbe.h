// pj_courbe.h : courbes régularisées de la description (droites et arcs tangents, GQ-PRI-001, GQ-CON-001) en VEX.
// Recopié en tête des wrangles par les scripts de construction (hda/pj_bordure/construire.py : vex_f1()).
//
// Une courbe est le tableau geometrie_reguliere.primitives (dict[]) d'une entité, en repère LOCAL Z haut
// (pj::lire_description réécrit x0 / y0 en local) :
//     {type: "droite" | "arc", s0, s1, x0, y0, cap0_rad, k0, coin?}
// cap(s) = cap0 + k0·(s − s0) ; arc : x = x0 + (sin cap − sin cap0) / k0, y = y0 − (cos cap − cos cap0) / k0.
// Sans primitives (courbe tracée à la main, spline Unreal), pj_cb_prims() bâtit des « droites » depuis la polyligne.
//
//     dict cb[] = pj_cb_prims(0, @primnum);        // primitives (repli : polyligne)
//     float cap, k;
//     vector2 p = pj_cb_point(cb, s, cap, k);       // position locale, cap (rad), courbure signée (+ à gauche)
//     float ss[] = pj_cb_abscisses(cb, 0.002);      // échantillonnage adaptatif : flèche de corde <= 2 mm
//     float s = pj_cb_projeter(cb, x, y, d);        // abscisse du point le plus proche, d = écart signé (+ à gauche)
#ifndef PJ_COURBE_H
#define PJ_COURBE_H

// Polyligne Houdini (Y haut, (x, z, −y) locaux) -> primitives « droite » (repli quand geometrie_reguliere manque).
function dict[] pj_cb_depuis_polyligne(int geo; int pr)
{
    dict out[];
    int pts[] = primpoints(geo, pr);
    float s = 0;
    for (int k = 0; k + 1 < len(pts); k++) {
        vector a = point(geo, "P", pts[k]);
        vector b = point(geo, "P", pts[k + 1]);
        float dx = b.x - a.x, dy = -(b.z - a.z);
        float l = sqrt(dx * dx + dy * dy);
        if (l < 1e-6) continue;
        dict d;
        d["type"] = "droite";
        d["s0"] = s;
        d["s1"] = s + l;
        d["x0"] = a.x;
        d["y0"] = -a.z;
        d["cap0_rad"] = atan2(dy, dx);
        d["k0"] = 0.0;
        append(out, d);
        s += l;
    }
    return out;
}

function dict[] pj_cb_prims(int geo; int pr)
{
    dict out[];
    if (haspointattrib(geo, "P") && hasprimattrib(geo, "geometrie_reguliere")) {
        dict gr = prim(geo, "geometrie_reguliere", pr);
        if (isvalidindex(gr, "primitives")) {
            dict ps[] = gr["primitives"];
            out = ps;
        }
    }
    if (len(out) == 0) out = pj_cb_depuis_polyligne(geo, pr);
    return out;
}

function float pj_cb_longueur(dict cb[])
{
    if (len(cb) == 0) return 0;
    float s1 = cb[len(cb) - 1]["s1"];
    return s1;
}

function int pj_cb_index(dict cb[]; float s)
{
    int k = 0;
    for (int i = 1; i < len(cb); i++) {
        float s0 = cb[i]["s0"];
        if (s >= s0 - 1e-9) k = i;
    }
    return k;
}

// Position (x, y) locale à l'abscisse s, cap (rad) et courbure signée ; hors [0, L] : prolongement par la tangente.
function vector2 pj_cb_point(dict cb[]; float s; float cap; float k)
{
    cap = 0;
    k = 0;
    if (len(cb) == 0) return set(0.0, 0.0);
    float L = pj_cb_longueur(cb);
    float sc = clamp(s, 0.0, L);
    int i = pj_cb_index(cb, sc);
    dict p = cb[i];
    string ty = p["type"];
    float s0 = p["s0"], x0 = p["x0"], y0 = p["y0"], c0 = p["cap0_rad"], k0 = p["k0"];
    float t = sc - s0;
    float x, y;
    if (ty == "arc" && abs(k0) > 1e-9) {
        cap = c0 + k0 * t;
        x = x0 + (sin(cap) - sin(c0)) / k0;
        y = y0 - (cos(cap) - cos(c0)) / k0;
        k = k0;
    } else {
        cap = c0;
        x = x0 + t * cos(c0);
        y = y0 + t * sin(c0);
    }
    float e = s - sc;                       // prolongement tangent aux bouts
    x += e * cos(cap);
    y += e * sin(cap);
    return set(x, y);
}

function vector2 pj_cb_tangente(dict cb[]; float s)
{
    float cap, k;
    vector2 p = pj_cb_point(cb, s, cap, k);
    return set(cos(cap), sin(cap));
}

// Abscisses d'échantillonnage sur [a, b] : bouts des primitives, arcs découpés pour une flèche de corde <= e.
function float[] pj_cb_abscisses_ab(dict cb[]; float a; float b; float e)
{
    float out[];
    append(out, a);
    for (int i = 0; i < len(cb); i++) {
        float s0 = cb[i]["s0"], s1 = cb[i]["s1"], k0 = cb[i]["k0"];
        string ty = cb[i]["type"];
        float lo = max(s0, a), hi = min(s1, b);
        if (hi <= lo + 1e-9) continue;
        if (lo > a + 1e-9) append(out, lo);
        if (ty == "arc" && abs(k0) > 1e-9) {
            float R = 1.0 / abs(k0);
            float dth = 2.0 * acos(clamp(1.0 - e / R, -1.0, 1.0));      // angle maximal d'une corde
            int n = max(1, int(ceil(abs(k0) * (hi - lo) / max(dth, 1e-6) - 1e-9)));
            for (int j = 1; j < n; j++) append(out, lo + (hi - lo) * j / n);
        }
    }
    append(out, b);
    return out;
}

function float[] pj_cb_abscisses(dict cb[]; float e)
{
    return pj_cb_abscisses_ab(cb, 0.0, pj_cb_longueur(cb), e);
}

// Flèche max (m) de la courbe par rapport à la corde [a, b] (échantillonnée finement).
function float pj_cb_fleche(dict cb[]; float a; float b)
{
    float c, k;
    vector2 pa = pj_cb_point(cb, a, c, k);
    vector2 pb = pj_cb_point(cb, b, c, k);
    vector2 d = pb - pa;
    float L = max(length(d), 1e-9);
    vector2 y = set(-d.y / L, d.x / L);
    float m = 0;
    for (int j = 1; j < 10; j++) {
        vector2 q = pj_cb_point(cb, a + (b - a) * j / 10.0, c, k);
        m = max(m, abs(dot(q - pa, y)));
    }
    return m;
}

// Écart signé (+ = à gauche de la corde) au milieu de [a, b].
function float pj_cb_ecart_milieu(dict cb[]; float a; float b)
{
    float c, k;
    vector2 pa = pj_cb_point(cb, a, c, k);
    vector2 pb = pj_cb_point(cb, b, c, k);
    vector2 pm = pj_cb_point(cb, 0.5 * (a + b), c, k);
    vector2 d = pb - pa;
    float L = max(length(d), 1e-9);
    return dot(pm - pa, set(-d.y / L, d.x / L));
}

// Déviation (rad, absolue) des tangentes entre a et b, coins compris.
function float pj_cb_deviation(dict cb[]; float a; float b)
{
    vector2 ta = pj_cb_tangente(cb, min(a, b));
    vector2 tb = pj_cb_tangente(cb, max(a, b));
    return abs(atan2(ta.x * tb.y - ta.y * tb.x, dot(ta, tb)));
}

// Rayon minimal (m) des arcs qui touchent [a, b] (1e6 sur une droite).
function float pj_cb_rayon_min(dict cb[]; float a; float b)
{
    float r = 1e6;
    for (int i = 0; i < len(cb); i++) {
        float s0 = cb[i]["s0"], s1 = cb[i]["s1"], k0 = cb[i]["k0"];
        if (s1 < a - 1e-9 || s0 > b + 1e-9) continue;
        if (abs(k0) > 1e-9) r = min(r, 1.0 / abs(k0));
    }
    return r;
}

// Abscisses des coins voulus (geometrie_reguliere.coins, ou primitives marquées coin).
function float[] pj_cb_coins(dict cb[])
{
    float out[];
    for (int i = 1; i < len(cb); i++) {
        if (isvalidindex(cb[i], "coin")) {
            int c = cb[i]["coin"];
            if (c) {
                float s0 = cb[i]["s0"];
                append(out, s0);
            }
        }
    }
    return out;
}

// Projection du point local (x, y) sur la courbe : abscisse du point le plus proche, écart signé d (+ = à gauche).
function float pj_cb_projeter(dict cb[]; float x; float y; float d)
{
    float best = 1e30, sb = 0;
    d = 0;
    vector2 q = set(x, y);
    for (int i = 0; i < len(cb); i++) {
        dict p = cb[i];
        string ty = p["type"];
        float s0 = p["s0"], s1 = p["s1"], x0 = p["x0"], y0 = p["y0"], c0 = p["cap0_rad"], k0 = p["k0"];
        float s;
        if (ty == "arc" && abs(k0) > 1e-9) {
            vector2 c = set(x0 - sin(c0) / k0, y0 + cos(c0) / k0);          // centre du cercle
            vector2 r = q - c;
            float ang = atan2(r.y, r.x);
            float a0 = atan2(y0 - c.y, x0 - c.x);
            float da = ang - a0;
            if (k0 < 0) da = -da;
            da = da - 2 * PI * floor((da + PI) / (2 * PI));       // ramené dans [−π, π[
            s = s0 + da / abs(k0);
        } else {
            s = s0 + dot(q - set(x0, y0), set(cos(c0), sin(c0)));
        }
        float lo = (i == 0) ? -1e9 : s0;
        float hi = (i == len(cb) - 1) ? 1e9 : s1;
        s = clamp(s, lo, hi);
        float cc, kk;
        vector2 pp = pj_cb_point(cb, s, cc, kk);
        float dd = length(q - pp);
        if (dd < best) {
            best = dd;
            sb = s;
            vector2 t = set(cos(cc), sin(cc));
            d = (t.x * (q.y - pp.y) - t.y * (q.x - pp.x)) >= 0 ? dd : -dd;
        }
    }
    return sb;
}

// Point Houdini (Y haut) d'un point local (x, y) et d'une altitude z.
function vector pj_cb_houdini(vector2 p; float z) { return set(p.x, z, -p.y); }

#endif
