// pj_niveau.h : requête du modèle de nivellement unique (TQ-SOL-013, CF-26) en VEX.
// Portage exact de recon/pcg/decrire/nivellement_requete.py (Nivellement.z) et de np.interp (z_bordure).
// Recopié dans le code des wrangles par les scripts de construction (pj_hda_outils.vex) : #include "opdef:" ne
// fonctionne pas en Houdini 22, et les struct ne sont pas admises dans le code d'un wrangle (d'où le tableau g[]).
//
// Géométrie attendue (sortie 2 de pj::lire_description) : volumes 2D height (z0), r0, z1, r1, z2, r2, rangés comme un
// HeightField (axe 0 -> Z monde, axe 1 -> X monde) ; détail niv_x0, niv_y0, niv_pas, niv_ni, niv_nj.
// Nœud (i, j) de la grille = point local (niv_x0 + i·pas, niv_y0 + j·pas) = voxel (nj - 1 - j, i, 0).
// Les coordonnées passées aux fonctions sont LOCALES Z haut (x, y) : x = P.x, y = -P.z en Houdini.
//
//     float g[] = pj_niv_grille(1);                 // une fois par élément (entrée 2 = HeightField)
//     float z = pj_niv_z(g, @P.x, -@P.z, region);    // PJ_NIV_ABSENT hors modèle
#ifndef PJ_NIVEAU_H
#define PJ_NIVEAU_H

#define PJ_NIV_ABSENT -1.0e30
// indices du descripteur g[]
#define PJ_G_GEO 0
#define PJ_G_X0 1
#define PJ_G_Y0 2
#define PJ_G_PAS 3
#define PJ_G_NI 4
#define PJ_G_NJ 5
#define PJ_G_PH 6
#define PJ_G_PR0 7
#define PJ_G_PZ1 8
#define PJ_G_PR1 9
#define PJ_G_PZ2 10
#define PJ_G_PR2 11
#define PJ_G_OK 12

function float[] pj_niv_grille(int geo)
{
    float g[];
    resize(g, 13);
    g[PJ_G_GEO] = geo;
    g[PJ_G_X0] = detail(geo, "niv_x0");
    g[PJ_G_Y0] = detail(geo, "niv_y0");
    g[PJ_G_PAS] = detail(geo, "niv_pas");
    g[PJ_G_NI] = detail(geo, "niv_ni");
    g[PJ_G_NJ] = detail(geo, "niv_nj");
    g[PJ_G_PH] = findattribval(geo, "prim", "name", "height");
    g[PJ_G_PR0] = findattribval(geo, "prim", "name", "r0");
    g[PJ_G_PZ1] = findattribval(geo, "prim", "name", "z1");
    g[PJ_G_PR1] = findattribval(geo, "prim", "name", "r1");
    g[PJ_G_PZ2] = findattribval(geo, "prim", "name", "z2");
    g[PJ_G_PR2] = findattribval(geo, "prim", "name", "r2");
    g[PJ_G_OK] = (g[PJ_G_PAS] > 0 && g[PJ_G_NI] > 0 && g[PJ_G_NJ] > 0 && g[PJ_G_PH] >= 0 && g[PJ_G_PR0] >= 0) ? 1 : 0;
    return g;
}

// Région propriétaire du nœud le plus proche (requête sans surface : np.rint, bornée à la grille).
function int pj_niv_region(float g[]; float x; float y)
{
    if (g[PJ_G_OK] < 0.5) return -1;
    int geo = int(g[PJ_G_GEO]);
    int ni = int(g[PJ_G_NI]);
    int nj = int(g[PJ_G_NJ]);
    int i = clamp(int(rint((x - g[PJ_G_X0]) / g[PJ_G_PAS])), 0, ni - 1);
    int j = clamp(int(rint((y - g[PJ_G_Y0]) / g[PJ_G_PAS])), 0, nj - 1);
    return int(rint(volumeindex(geo, int(g[PJ_G_PR0]), set(nj - 1 - j, i, 0))));
}

// Valeur du nœud (i, j) pour la région reg : couche 0, puis prolongements 1 et 2 (PJ_NIV_ABSENT sinon).
function float pj_niv_noeud(float g[]; int i; int j; int reg)
{
    int ni = int(g[PJ_G_NI]);
    int nj = int(g[PJ_G_NJ]);
    if (i < 0 || j < 0 || i >= ni || j >= nj) return PJ_NIV_ABSENT;
    int geo = int(g[PJ_G_GEO]);
    vector vx = set(nj - 1 - j, i, 0);
    if (int(rint(volumeindex(geo, int(g[PJ_G_PR0]), vx))) == reg) return volumeindex(geo, int(g[PJ_G_PH]), vx);
    if (g[PJ_G_PR1] >= 0 && int(rint(volumeindex(geo, int(g[PJ_G_PR1]), vx))) == reg)
        return volumeindex(geo, int(g[PJ_G_PZ1]), vx);
    if (g[PJ_G_PR2] >= 0 && int(rint(volumeindex(geo, int(g[PJ_G_PR2]), vx))) == reg)
        return volumeindex(geo, int(g[PJ_G_PZ2]), vx);
    return PJ_NIV_ABSENT;
}

// z local au point (x, y) dans la région reg (reg < 0 : région propriétaire du nœud le plus proche).
// Bilinéaire sur les seuls nœuds de la région, poids renormalisés (comme Nivellement.z) ; PJ_NIV_ABSENT hors modèle.
function float pj_niv_z(float g[]; float x; float y; int reg)
{
    if (g[PJ_G_OK] < 0.5) return PJ_NIV_ABSENT;
    int r = reg;
    if (r < 0) r = pj_niv_region(g, x, y);
    if (r < 0) return PJ_NIV_ABSENT;
    float fi = (x - g[PJ_G_X0]) / g[PJ_G_PAS];
    float fj = (y - g[PJ_G_Y0]) / g[PJ_G_PAS];
    int i0 = int(floor(fi));
    int j0 = int(floor(fj));
    float ti = fi - i0;
    float tj = fj - j0;
    float num = 0, den = 0;
    float w[] = array((1 - ti) * (1 - tj), ti * (1 - tj), (1 - ti) * tj, ti * tj);
    int di[] = array(0, 1, 0, 1);
    int dj[] = array(0, 0, 1, 1);
    for (int k = 0; k < 4; k++) {
        float v = pj_niv_noeud(g, i0 + di[k], j0 + dj[k], r);
        if (v > 0.5 * PJ_NIV_ABSENT) {
            num += w[k] * v;
            den += w[k];
        }
    }
    if (den <= 1e-9) return PJ_NIV_ABSENT;
    return num / den;
}

// Interpolation linéaire bornée (np.interp) d'un profil en long (S croissant).
function float pj_interp(float s; float S[]; float Z[])
{
    int n = len(S);
    if (n == 0) return PJ_NIV_ABSENT;
    if (s <= S[0]) return Z[0];
    if (s >= S[n - 1]) return Z[n - 1];
    int k = 1;
    while (k < n - 1 && S[k] < s) k++;
    float t = (s - S[k - 1]) / max(S[k] - S[k - 1], 1e-12);
    return lerp(Z[k - 1], Z[k], t);
}

#endif
