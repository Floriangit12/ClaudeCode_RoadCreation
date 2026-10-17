// rg_geometrie.h : géométrie du générateur de routes (HDA rg::*, lot L1), recopiée en tête des wrangles
// (#include "opdef:" impossible, README_HDA § 1). Pas de struct ; fonctions à tableaux déclarées par « function ».
// Les wrangles qui l'utilisent sont en VEX 64 bits (vex_precision = 64) : flèche ≤ 0,5 mm, écarts ≤ 1 mm.
//
// Conventions du modèle modele_voie/0.1 (meta.conventions) :
//   s   abscisse curviligne absolue le long de la ligne de référence (m) : primitives, sections, lois de largeur ;
//   t   décalage latéral (m), positif à gauche du sens de la ligne de référence ;
//   cap OpenDRIVE en radians (0 = est, sens trigonométrique) ; courbure > 0 = virage à gauche ;
//   repère local (x, y) = Lambert-93 − repere.origine_l93 ; Houdini (x, z, −y), Y haut (README_HDA § 2).
#ifndef RG_GEOMETRIE_H
#define RG_GEOMETRIE_H

#define RG_DROITE 0
#define RG_ARC 1
#define RG_CLOTHOIDE 2
#define RG_PANNEAU_GL 0.5

// Gauss-Legendre à 8 nœuds sur [0, 1] (nœuds et poids de [-1, 1] ramenés).
function float[] rg_gl_x()
{
    return array(0.019855071751231856, 0.10166676129318664, 0.2372337950418355, 0.4082826787521751,
                 0.5917173212478249, 0.7627662049581645, 0.8983332387068134, 0.9801449282487681);
}
function float[] rg_gl_w()
{
    return array(0.050614268145188129, 0.11119051722668724, 0.15685332293894364, 0.18134189168918100,
                 0.18134189168918100, 0.15685332293894364, 0.11119051722668724, 0.050614268145188129);
}

// Point (x, y) local, cap th (rad) et courbure k à l'abscisse locale u ∈ [0, lg] d'une primitive régulière
// (OpenDRIVE <line>, <arc>, <spiral>). Clothoïde : courbure linéaire de k0 à k1 ; position par intégration de
// Gauss-Legendre composite (panneaux ≤ 0,5 m, 8 nœuds : erreur < 1e-12 m pour les courbures routières).
function void rg_primitive(int typ; float x0; float y0; float cap; float k0; float k1; float lg; float u;
                           export float x; export float y; export float th; export float k)
{
    if (typ == RG_DROITE) {
        x = x0 + u * cos(cap);
        y = y0 + u * sin(cap);
        th = cap;
        k = 0.0;
    } else if (typ == RG_ARC) {
        x = x0 + (sin(cap + k0 * u) - sin(cap)) / k0;
        y = y0 - (cos(cap + k0 * u) - cos(cap)) / k0;
        th = cap + k0 * u;
        k = k0;
    } else {
        float c = (k1 - k0) / lg;
        float gx[] = rg_gl_x();
        float gw[] = rg_gl_w();
        int n = max(1, int(ceil(u / RG_PANNEAU_GL)));
        float h = u / n;
        float sx = 0.0;
        float sy = 0.0;
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < 8; j++) {
                float v = (i + gx[j]) * h;
                float a = cap + k0 * v + 0.5 * c * v * v;
                sx += gw[j] * cos(a);
                sy += gw[j] * sin(a);
            }
        }
        x = x0 + sx * h;
        y = y0 + sy * h;
        th = cap + k0 * u + 0.5 * c * u * u;
        k = k0 + c * u;
    }
}

// Indice de la primitive qui porte s : la dernière dont s0 ≤ s (à un raccord, la primitive suivante, dont le
// point de départ est celui du modèle ; s = L : la dernière).
function int rg_indice_primitive(float S0[]; float s)
{
    int k = 0;
    for (int i = 1; i < len(S0); i++)
        if (S0[i] <= s + 1e-9) k = i;
    return k;
}

// Ligne de référence de la route pr (attributs de primitive geo_* de l'entrée geo) à l'abscisse s.
function void rg_reference(int geo; int pr; float s; export float x; export float y; export float th; export float k)
{
    int T[] = prim(geo, "geo_type", pr);
    float S0[] = prim(geo, "geo_s0", pr);
    float LG[] = prim(geo, "geo_longueur", pr);
    float X0[] = prim(geo, "geo_x0", pr);
    float Y0[] = prim(geo, "geo_y0", pr);
    float C0[] = prim(geo, "geo_cap", pr);
    float K0[] = prim(geo, "geo_k0", pr);
    float K1[] = prim(geo, "geo_k1", pr);
    int g = rg_indice_primitive(S0, s);
    float u = clamp(s - S0[g], 0.0, LG[g]);
    rg_primitive(T[g], X0[g], Y0[g], C0[g], K0[g], K1[g], LG[g], u, x, y, th, k);
}

// Loi de s aplatie (attributs larg_* d'un profil) : typ 0 nombre (V[j0]) ; 1 points linéaire ; 2 points palier
// (valeur du dernier point d'abscisse ≤ s) ; 4 poly3 OpenDRIVE (a + b ds + c ds² + d ds³, ds = s − s0 du morceau,
// s0 absolu). Hors des points : valeur du premier ou du dernier point (loi prolongée constante).
function float rg_loi(int typ; float LS[]; float LV[]; int i0; int j0; int n; float s)
{
    if (typ == 0 || n <= 0) return LV[j0];
    if (typ == 4) {
        int m = 0;
        for (int q = 1; q < n; q++)
            if (LS[i0 + q] <= s + 1e-12) m = q;
        float ds = s - LS[i0 + m];
        int b = j0 + 4 * m;
        return LV[b] + LV[b + 1] * ds + LV[b + 2] * ds * ds + LV[b + 3] * ds * ds * ds;
    }
    if (s <= LS[i0]) return LV[j0];
    if (s >= LS[i0 + n - 1]) return LV[j0 + n - 1];
    int q = 0;
    while (q < n - 2 && s >= LS[i0 + q + 1]) q++;
    float sa = LS[i0 + q];
    float sb = LS[i0 + q + 1];
    if (typ == 2) return (s >= sb) ? LV[j0 + q + 1] : LV[j0 + q];
    float a = (s - sa) / (sb - sa);
    return LV[j0 + q] + (LV[j0 + q + 1] - LV[j0 + q]) * a;
}

// Largeurs des bandes du profil (point pp de l'entrée geo) à l'abscisse s.
function float[] rg_largeurs(int geo; int pp; float s)
{
    int lt[] = point(geo, "larg_type", pp);
    int ls0[] = point(geo, "larg_s0", pp);
    int lv0[] = point(geo, "larg_v0", pp);
    int ln[] = point(geo, "larg_n", pp);
    float LS[] = point(geo, "larg_s", pp);
    float LV[] = point(geo, "larg_v", pp);
    float w[];
    resize(w, len(lt));
    for (int b = 0; b < len(lt); b++)
        w[b] = rg_loi(lt[b], LS, LV, ls0[b], lv0[b], ln[b], s);
    return w;
}

// Positions t (m, + gauche) des n + 1 limites du profil à l'abscisse s : la limite de référence est à
// t = −reference.decalage_m ; les autres par cumul des largeurs vers la gauche et vers la droite.
function float[] rg_t_limites(int geo; int pp; float s)
{
    int r = point(geo, "ref_limite", pp);
    float d = point(geo, "ref_decalage", pp);
    float w[] = rg_largeurs(geo, pp, s);
    int nb = len(w);
    float t[];
    resize(t, nb + 1);
    t[r] = -d;
    for (int i = r - 1; i >= 0; i--) t[i] = t[i + 1] + w[i];
    for (int i = r + 1; i <= nb; i++) t[i] = t[i - 1] - w[i - 1];
    return t;
}

// Point du profil (entrée geo) de nom pid ; -1 s'il manque.
function int rg_point_profil(int geo; string pid)
{
    return findattribval(geo, "point", "profil", pid);
}

// Indice de la section de la route qui porte s (sections contiguës ; à une jonction, la section suivante).
function int rg_indice_section(float SEC0[]; float s)
{
    int k = 0;
    for (int i = 1; i < len(SEC0); i++)
        if (SEC0[i] <= s + 1e-9) k = i;
    return k;
}

// Surélévation de la chaussée dz(s) (m) et majorant de |dz''| : plateaux trapézoïdaux (longueur totale et hauteur
// du modèle, rampes à rampe_pct, DEF-034) et dos-d'âne circulaires (corde = longueur, flèche = hauteur,
// RF-MA-RAL-001) rattachés à la route (entrée geo : ponctuels).
function float rg_dz_chaussee(int geo; string route; float s; float rampe_pct; export float d2)
{
    float dz = 0.0;
    d2 = 0.0;
    int pts[] = findattribval(geo, "point", "route", route);
    foreach (int p; pts) {
        string ty = point(geo, "type", p);
        if (ty != "plateau" && ty != "dos_d_ane") continue;
        float sc = point(geo, "s", p);
        float lg = point(geo, "longueur_m", p);
        float h = point(geo, "hauteur_m", p);
        float u = s - sc;
        if (abs(u) >= lg / 2.0 || h <= 0.0) continue;
        if (ty == "plateau") {
            float rampe = h / (rampe_pct / 100.0);
            dz += h * min(1.0, (lg / 2.0 - abs(u)) / rampe);
        } else {
            float R = (lg * lg / 4.0 + h * h) / (2.0 * h);
            dz += sqrt(R * R - u * u) - (R - h);
            d2 = max(d2, R * R / pow(R * R - u * u, 1.5));
        }
    }
    return dz;
}

// Abscisses remarquables de la loi verticale de la route (pieds et hauts de rampe des plateaux ; bornes et
// sommet des dos-d'âne).
function float[] rg_bornes_verticales(int geo; string route; float rampe_pct)
{
    float out[];
    int pts[] = findattribval(geo, "point", "route", route);
    foreach (int p; pts) {
        string ty = point(geo, "type", p);
        if (ty != "plateau" && ty != "dos_d_ane") continue;
        float sc = point(geo, "s", p);
        float lg = point(geo, "longueur_m", p);
        float h = point(geo, "hauteur_m", p);
        push(out, sc - lg / 2.0);
        push(out, sc + lg / 2.0);
        if (ty == "dos_d_ane") push(out, sc);                 // sommet du dos-d'âne
        if (ty == "plateau" && h > 0.0) {
            float rampe = h / (rampe_pct / 100.0);
            push(out, sc - lg / 2.0 + rampe);
            push(out, sc + lg / 2.0 - rampe);
        }
    }
    return out;
}

// Local (x, y, z) -> Houdini (x, z, −y) (README_HDA § 2 ; même convention que pj_repere.h).
function vector rg_vers_houdini(float x; float y; float z) { return set(x, z, -y); }

#endif
