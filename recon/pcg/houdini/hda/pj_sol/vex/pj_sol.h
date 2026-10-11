// pj_sol.h : altitude des sommets de sol sur le modèle de nivellement unique (TQ-SOL-013, CF-26), sans lissage des
// marches de bordure.
//
// La requête pj_niv_z (pj_niveau.h, portage de nivellement_requete.Nivellement.z) n'interpole qu'entre les nœuds de la
// région de la surface. Mais trottoir, emprise de bordure et chaussée appartiennent souvent à la MÊME région (région 0 :
// 1 295 surfaces) : les discontinuités « arête arrière » et « emprise » (nivellement.json discontinuites) passent alors
// entre deux nœuds de 0,10 m et l'interpolation bilinéaire relève la chaussée de quelques centimètres sur les 10 cm qui
// précèdent la face de la bordure (biseaux, « wedges » des captures 5-11). pj_sol_z n'utilise donc que les nœuds
// VALIDES pour la surface du sommet :
//   - nœud dans la même surface ;
//   - ou dans une surface voisine continue : ni une emprise de bordure, ni une surface de l'autre côté d'une même
//     bordure (bords[] : même bordure, côtés différents : avant / arrière / bout) ;
// poids bilinéaires renormalisés (comme Nivellement.z) ; si aucun des 4 nœuds n'est valide, nœuds valides du
// voisinage 4 x 4 pondérés par l'inverse du carré de la distance, puis requête brute.
// La surface d'un nœud se lit par xyzdist sur le sol triangulé à plat (entrée « geo_plat », un triangle porte
// surf_index = numéro de l'anneau extérieur de sa surface dans « geo_surf »).
#ifndef PJ_SOL_H
#define PJ_SOL_H

// Surface (numéro dans geo_surf) qui contient le point local (x, y) ; −1 hors sol.
function int pj_sol_surface_de(int geo_plat; float x; float y)
{
    int pr;
    vector uv;
    float d = xyzdist(geo_plat, set(x, 0.0, -y), pr, uv, 0.02);
    if (pr < 0 || d > 1e-3) return -1;
    return prim(geo_plat, "surf_index", pr);
}

// Le nœud de la surface t est-il utilisable pour un sommet de la surface own ?
function int pj_sol_valide(int geo_surf; int own; int t)
{
    if (t < 0) return 0;
    if (t == own) return 1;
    string ct = prim(geo_surf, "classe", t);
    if (ct == "emprise_bordure") return 0;
    dict bo[] = prim(geo_surf, "bords", own);
    dict bt[] = prim(geo_surf, "bords", t);
    foreach (dict a; bo) {
        string ka = a["bordure"];
        string ca = a["cote"];
        foreach (dict b; bt) {
            string kb = b["bordure"];
            string cb = b["cote"];
            if (ka == kb && ca != cb) return 0;          // de part et d'autre de la même bordure
        }
    }
    return 1;
}

// Anneau extérieur de la grille du site (x ou y = ±150 m) : z0 y est NaN mais le prolongement z1 / r1 vaut ≈ 0 dans
// la région 0 (nivellement_grille.npz) ; ces nœuds relevaient de 2,7 m les sommets du bord nord : ignorés.
function int pj_sol_anneau(float xn; float yn)
{
    return abs(xn) > 149.95 || abs(yn) > 149.95;
}

// z local du sommet (x, y) de la surface own (région reg) ; PJ_NIV_ABSENT hors modèle.
function float pj_sol_z(float g[]; int geo_plat; int geo_surf; int own; int reg; float x; float y)
{
    if (g[PJ_G_OK] < 0.5) return PJ_NIV_ABSENT;
    int r = reg;
    if (r < 0) r = pj_niv_region(g, x, y);
    float x0 = g[PJ_G_X0], y0 = g[PJ_G_Y0], pas = g[PJ_G_PAS];
    float fi = (x - x0) / pas, fj = (y - y0) / pas;
    int i0 = int(floor(fi)), j0 = int(floor(fj));
    float ti = fi - i0, tj = fj - j0;
    float w[] = array((1 - ti) * (1 - tj), ti * (1 - tj), (1 - ti) * tj, ti * tj);
    int di[] = array(0, 1, 0, 1), dj[] = array(0, 0, 1, 1);
    float num = 0, den = 0;
    for (int k = 0; k < 4; k++) {
        int i = i0 + di[k], j = j0 + dj[k];
        if (pj_sol_anneau(x0 + i * pas, y0 + j * pas)) continue;
        float v = pj_niv_noeud(g, i, j, r);
        if (v < 0.5 * PJ_NIV_ABSENT) continue;
        if (!pj_sol_valide(geo_surf, own, pj_sol_surface_de(geo_plat, x0 + i * pas, y0 + j * pas))) continue;
        num += w[k] * v;
        den += w[k];
    }
    if (den > 1e-9) return num / den;
    // repli : nœuds valides du voisinage 4 x 4
    for (int i = i0 - 1; i <= i0 + 2; i++) {
        for (int j = j0 - 1; j <= j0 + 2; j++) {
            if (pj_sol_anneau(x0 + i * pas, y0 + j * pas)) continue;
            float v = pj_niv_noeud(g, i, j, r);
            if (v < 0.5 * PJ_NIV_ABSENT) continue;
            if (!pj_sol_valide(geo_surf, own, pj_sol_surface_de(geo_plat, x0 + i * pas, y0 + j * pas))) continue;
            float dx = x0 + i * pas - x, dy = y0 + j * pas - y;
            float ww = 1.0 / max(dx * dx + dy * dy, 1e-6);
            num += ww * v;
            den += ww;
        }
    }
    if (den > 1e-12) return num / den;
    return pj_niv_z(g, x, y, r);
}

// Largeur de base (arête avant -> arête arrière) d'un profil de bordure (assets/specs/bordures.json, compléments).
function float pj_base_profil(string p)
{
    string n[] = array("T1", "T2", "T3", "T2_bateau", "A1", "A2", "P1", "P2", "P3", "I1", "I2", "IL", "QUAI_BUS", "TU",
                       "AC1", "PAVES_GRANIT", "MURET_TALUS");
    float b[] = array(0.12, 0.15, 0.17, 0.15, 0.20, 0.15, 0.08, 0.06, 0.08, 0.25, 0.25, 0.20, 0.35, 0.25, 0.35, 0.14, 0.20);
    int i = find(n, p);
    return i >= 0 ? b[i] : 0.15;
}

#endif
