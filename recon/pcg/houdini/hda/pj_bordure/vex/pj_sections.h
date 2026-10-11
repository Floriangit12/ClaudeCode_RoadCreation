// pj_sections.h : sections (contours de profils) pour le Sweep des éléments de bordure et de caniveau (VEX).
// Géométrie « profils » (sortie de lire_profils) : un polygone fermé par profil dans le plan XY (x = u, y = v), sens
// horaire, premier point = coin avant bas ; primitive : profil, base, H, i_top, k_back ; détail pj_profils_noms[].
// Le Sweep (Houdini 22) pose la section avec X_section = haut × tangente (= arrière de la bordure, u) et
// Y_section = haut (v) : une section (u, v) se pose donc telle quelle (README_HDA.md, repère Y haut).
#ifndef PJ_SECTIONS_H
#define PJ_SECTIONS_H

function int pj_sec_prim(int geo; string profil)
{
    int p = findattribval(geo, "prim", "profil", profil);
    if (p < 0) p = findattribval(geo, "prim", "profil", "T2");
    return p;
}

// Contour du profil (u[], v[]) et indices clés.
function void pj_sec_contour(int geo; int pr; float u[]; float v[]; int i_top; int k_back)
{
    resize(u, 0);
    resize(v, 0);
    int pts[] = primpoints(geo, pr);
    foreach (int p; pts) {
        vector P = point(geo, "P", p);
        append(u, P.x);
        append(v, P.y);
    }
    i_top = prim(geo, "i_top", pr);
    k_back = prim(geo, "k_back", pr);
}

function float[] pj_sec_abscisse_rel(float u[]; float v[])
{
    float s[];
    append(s, 0.0);
    float acc = 0;
    for (int i = 1; i < len(u); i++) {
        acc += length(set(u[i] - u[i - 1], v[i] - v[i - 1]));
        append(s, acc);
    }
    for (int i = 0; i < len(s); i++) s[i] /= max(acc, 1e-12);
    return s;
}

// Rééchantillonne la chaîne (u, v) aux abscisses relatives t (interpolation linéaire par morceaux).
function void pj_sec_reech(float u[]; float v[]; float t[]; float ou[]; float ov[])
{
    resize(ou, 0);
    resize(ov, 0);
    float s[] = pj_sec_abscisse_rel(u, v);
    foreach (float x; t) {
        int k = 1;
        while (k < len(s) - 1 && s[k] < x) k++;
        float f = clamp((x - s[k - 1]) / max(s[k] - s[k - 1], 1e-12), 0.0, 1.0);
        append(ou, lerp(u[k - 1], u[k], f));
        append(ov, lerp(v[k - 1], v[k], f));
    }
}

function void pj_sec_sous(float u[]; float v[]; int i0; int i1; float ou[]; float ov[])
{
    resize(ou, 0);
    resize(ov, 0);
    for (int i = i0; i <= i1; i++) {
        append(ou, u[i]);
        append(ov, v[i]);
    }
}

// Deux contours ramenés à la même topologie (chaînes avant, tête, arrière ; échantillonnées sur l'union de leurs
// abscisses relatives) pour un loft (chartière : pj_bordure_prototypes.contours_communs).
function void pj_sec_communs(float ua[]; float va[]; int ita; int kba; float ub[]; float vb[]; int itb; int kbb;
                             float oua[]; float ova[]; float oub[]; float ovb[]; int oc[])
{
    resize(oua, 0); resize(ova, 0); resize(oub, 0); resize(ovb, 0); resize(oc, 0);
    int ma = len(ua), mb = len(ub);
    int ia0[] = array(0, ita, kba), ia1[] = array(ita, kba, ma - 1);
    int ib0[] = array(0, itb, kbb), ib1[] = array(itb, kbb, mb - 1);
    for (int c = 0; c < 3; c++) {
        float cua[], cva[], cub[], cvb[];
        pj_sec_sous(ua, va, ia0[c], ia1[c], cua, cva);
        pj_sec_sous(ub, vb, ib0[c], ib1[c], cub, cvb);
        float t[];
        foreach (float x; pj_sec_abscisse_rel(cua, cva)) append(t, rint(x * 1e6) / 1e6);
        foreach (float x; pj_sec_abscisse_rel(cub, cvb)) append(t, rint(x * 1e6) / 1e6);
        t = sort(t);
        float tu[];
        foreach (float x; t) if (len(tu) == 0 || x - tu[len(tu) - 1] > 1e-6) append(tu, x);
        float rua[], rva[], rub[], rvb[];
        pj_sec_reech(cua, cva, tu, rua, rva);
        pj_sec_reech(cub, cvb, tu, rub, rvb);
        int n = len(tu);
        int fin = (c < 2) ? n - 1 : n;                           // le dernier point est le premier de la chaîne suivante
        for (int i = 0; i < fin; i++) {
            append(oua, rua[i]); append(ova, rva[i]);
            append(oub, rub[i]); append(ovb, rvb[i]);
            append(oc, (c < 2 || i == 0) ? 0 : 1);             // 0 : face vue et tête (abouts chanfreinés)
        }
    }
}

// Contour convexe décalé vers l'intérieur de d (sommets sur les bissectrices, cosinus borné à 0,3).
function void pj_sec_inset(float u[]; float v[]; float d; float ou[]; float ov[])
{
    resize(ou, 0);
    resize(ov, 0);
    int m = len(u);
    for (int i = 0; i < m; i++) {
        int ia = (i + m - 1) % m, ie = (i + 1) % m;
        vector2 a = set(u[ia], v[ia]), b = set(u[i], v[i]), e = set(u[ie], v[ie]);
        vector2 t0 = normalize(b - a), t1 = normalize(e - b);
        vector2 n0 = set(-t0.y, t0.x), n1 = set(-t1.y, t1.x);            // normales sortantes (contour horaire)
        vector2 nm = normalize(n0 + n1);
        float cs = max(dot(nm, n0), 0.3);
        vector2 q = b - nm * d / cs;
        append(ou, q.x);
        append(ov, q.y);
    }
}

// Ajoute une section (polygone fermé dans le plan XY, chaîne de chaque sommet) ; renvoie son numéro de primitive.
function int pj_sec_ajouter_ch(int geo; float u[]; float v[]; int ch[]; string nom)
{
    int pts[];
    int m = len(u);
    float acc = 0;
    float cum[];
    for (int i = 0; i < m; i++) {
        append(cum, acc);
        int j = (i + 1) % m;
        acc += length(set(u[j] - u[i], v[j] - v[i]));
    }
    for (int i = 0; i < m; i++) {
        int p = addpoint(geo, set(u[i], v[i], 0.0));
        setpointattrib(geo, "u_cs", p, u[i]);
        setpointattrib(geo, "v_cs", p, v[i]);
        setpointattrib(geo, "chaine", p, i < len(ch) ? ch[i] : 1);
        setpointattrib(geo, "rang", p, i);
        setpointattrib(geo, "p_cs", p, cum[i]);          // abscisse sur le périmètre (UV en mètres)
        setpointattrib(geo, "perim", p, acc);
        append(pts, p);
    }
    int pr = addprim(geo, "poly", pts);
    setprimattrib(geo, "profil", pr, nom);
    return pr;
}

function int pj_sec_ajouter(int geo; float u[]; float v[]; string nom)
{
    int ch[];
    return pj_sec_ajouter_ch(geo, u, v, ch, nom);
}

// Arête avant haute (épaufrures) : sommet de la chaîne avant maximisant v − u/4, et bissectrice sortante.
function void pj_sec_arete(float u[]; float v[]; int i_top; vector2 A; vector2 nb)
{
    int k = 0;
    float best = -1e9;
    for (int i = 0; i <= i_top; i++) {
        float f = v[i] - 0.25 * u[i];
        if (f > best) { best = f; k = i; }
    }
    int m = len(u);
    k = clamp(k, 1, m - 2);
    vector2 d0 = set(u[k] - u[k - 1], v[k] - v[k - 1]);
    vector2 d1 = set(u[k + 1] - u[k], v[k + 1] - v[k]);
    vector2 n0 = normalize(set(-d0.y, d0.x)), n1 = normalize(set(-d1.y, d1.x));
    A = set(u[k], v[k]);
    nb = normalize(n0 + n1);
}

#endif
