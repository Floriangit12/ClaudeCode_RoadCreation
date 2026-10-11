"""Construit l'HDA pj::symbole_iisr::1.0 (branche symboles : flèches MF-* et symboles MS-*) ; hython Houdini 22.

    hython recon/pcg/houdini/hda/pj_marquage_symbole/construire.py

Réseau (README_HDA.md § 7) :
    gabarits (pj::gabarits_iisr : polygones exacts de marquages_geometrie.json)
    poses (VEX : genre gabarit / paramétrique / glyphe, origine, cap, écart au gabarit, plan du sol, prototype)
      -> empreintes_prototypes (VEX, repère du gabarit) -> vers_repere_prototype (Transform : +X vers l'avant)
         -> prototypes (pj::marquage_solide, à plat) -> sortie 3 (bibliothèque /Game/PJ/Lib/Marquages/SM_<asset>)
      -> instances (VEX : un point par symbole, orient = plan du sol x cap, unreal_instance) -> sortie 2
      -> empreintes_drapees (VEX : symboles dont le plan s'écarte du sol, ou mode drapé) -> drape (pj::marquage_solide)
         -> sortie 1
      -> apercu (Copy to Points, instances empaquetées) -> sortie 4
Entrées : 1 = symboles (polygones décrits + pose, ou points avec gabarit et cap_deg), 2 = nivellement.
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "pj_marquage_commun"))
import pj_marquage_outils as M  # noqa: E402

O = M.O
T = hou
NOM = "symbole_iisr"

VEX_POSES = r"""
// Pose et prototype de chaque symbole (une passe par entité, attributs écrits sur toutes ses primitives) :
//   genre « gabarit » : flèches TD, TAD, TAG, TD_TAD, TD_TAG, RAB_*, CEDEZ_*, VELO : polygone exact de
//     marquages_geometrie.json (annexes B / D, FUS-SNP-004 : forme normative posée) si l'écart entre le contour décrit
//     et le gabarit posé <= « Tolérance d'écart au gabarit » ; sinon « glyphe » ;
//   genre « parametrique » : barre (rectangle, MQ-CHR-001), point (disque, corde 1 mm), dent de requin (triangle
//     base x hauteur, MQ-RAL-001), chevron (V à trait constant, MQ-ILO-003 / MQ-CYC-008) ;
//   genre « glyphe » : forme décrite (PMR, chiffres 30 / 50, figurine reconstruite), origine = centroïde ;
//   cap : pose.cap_deg (tangente de la voie, MQ-FLE-006 / FUS-SNP-004) ; origine du gabarit : centroïde décrit moins le
//   centroïde du gabarit tourné (recalages d'image compris : la géométrie décrite fait foi) ;
//   plan du sol : moindres carrés sur le contour posé dans la région majoritaire (TQ-SOL-013) ; résidu > tolérance ou
//   mode « drapé » : maillage drapé unique (sortie 1) au lieu d'une instance.
float tolg = ch("../tol_gabarit");
float tolp = ch("../tol_plan");
string mode = chs("../mode");
float corde = ch("../corde");
float g[] = pj_niv_grille(2);
int np = nprimitives(0);
string ids[];
for (int pr = 0; pr < np; pr++) {
    string id = prim(0, "id", pr);
    if (find(ids, id) < 0) append(ids, id);
}
string fournis[];
foreach (string id; ids) {
    int prs[] = findattribval(0, "prim", "id", id);
    int p0 = prs[0];
    string ty = prim(0, "type", p0);
    string gab = prim(0, "gabarit", p0);
    string mid = prim(0, "materiau_id", p0);
    float e = prim(0, "echelle", p0);
    if (e <= 0) e = 1.0;
    dict pose = prim(0, "pose", p0);
    float cap = 0;
    vector2 op = set(0.0, 0.0);
    int a_pose = 0;
    if (isvalidindex(pose, "cap_deg")) cap = pose["cap_deg"];
    else if (hasprimattrib(0, "cap_deg")) cap = prim(0, "cap_deg", p0);
    if (isvalidindex(pose, "point_local")) { op = pose["point_local"]; a_pose = 1; }
    // contour décrit : centroïde (aire des extérieurs moins les trous)
    float A = 0;
    vector2 C = set(0.0, 0.0);
    int nsom = 0;
    foreach (int r; prs) {
        vector2 q[] = pj_m_anneau(0, r);
        nsom += len(q);
        if (len(q) < 3) continue;
        vector c = pj_m_centroide_q(q);
        int an = prim(0, "anneau", r);
        float s = an == 0 ? 1.0 : -1.0;
        A += s * abs(c.z);
        C += s * abs(c.z) * set(c.x, c.y);
    }
    int decrit = A > 1e-6;
    if (decrit) C /= A;
    else if (a_pose) C = op;
    else { vector P0 = point(0, "P", primpoints(0, p0)[0]); C = set(P0.x, -P0.z); }
    string genre = "glyphe";
    string cle = "";
    float ecart = 0;
    vector2 o = C;
    // gabarit normatif
    int ng[] = findattribval(1, "prim", "gabarit", gab);
    if (gab != "" && len(ng) > 0) {
        float At = 0;
        vector2 Ct = set(0.0, 0.0);
        foreach (int r; ng) {
            vector2 q[] = pj_m_anneau(1, r);
            vector c = pj_m_centroide_q(q);
            int an = prim(1, "anneau", r);
            float s = an == 0 ? 1.0 : -1.0;
            At += s * abs(c.z);
            Ct += s * abs(c.z) * set(c.x, c.y);
        }
        Ct /= max(At, 1e-9);
        vector2 og = decrit ? C - pj_m_poser(Ct, set(0.0, 0.0), cap, e) : (a_pose ? op : C);
        float em = 0;
        if (decrit) {
            foreach (int r; prs) {
                vector2 q[] = pj_m_anneau(0, r);
                foreach (vector2 v; q) {
                    vector2 t = pj_m_deposer(v, og, cap, e);
                    float dm = 1e9;
                    foreach (int rg; ng) {
                        vector2 qt[] = pj_m_anneau(1, rg);
                        dm = min(dm, pj_m_dist_anneau(t, qt));
                    }
                    em = max(em, dm * e);
                }
            }
        }
        ecart = em;
        if (em <= tolg) {
            genre = "gabarit";
            o = og;
            cle = gab + (abs(e - 1) > 1e-3 ? sprintf("_e%03d", int(rint(e * 100))) : "");
        }
    }
    // formes paramétriques
    if (genre == "glyphe" && (ty == "barre" || ty == "point" || ty == "dent_requin" || ty == "chevron")) {
        string nd = ty == "barre" ? "rectangle" : (ty == "point" ? "disque" : (ty == "dent_requin" ? "triangle" : "chevron"));
        dict prm;
        if (hasprimattrib(0, nd)) prm = prim(0, nd, p0);
        if (len(keys(prm)) > 0) {
            vector2 qf[] = pj_m_forme(ty, prm, corde);
            vector cf = pj_m_centroide_q(qf);
            vector2 of = decrit ? C - pj_m_poser(set(cf.x, cf.y), set(0.0, 0.0), cap, 1.0) : (a_pose ? op : C);
            float em = 0;
            if (decrit) {
                foreach (int r; prs) {
                    vector2 q[] = pj_m_anneau(0, r);
                    foreach (vector2 v; q) em = max(em, pj_m_dist_anneau(pj_m_deposer(v, of, cap, 1.0), qf));
                }
            }
            genre = "parametrique";
            o = of;
            e = 1.0;
            ecart = em;
            cle = pj_m_cle_forme(ty, prm);
        }
    }
    // glyphe : forme décrite, origine au centroïde, clé = empreinte des sommets ramenés au gabarit (1 mm)
    if (genre == "glyphe") {
        o = C;
        e = 1.0;
        string sig = "";
        foreach (int r; prs) {
            vector2 q[] = pj_m_anneau(0, r);
            int an = prim(0, "anneau", r);
            sig += sprintf("|%d:", an);
            foreach (vector2 v; q) {
                vector2 t = pj_m_deposer(v, o, cap, 1.0);
                sig += sprintf("%d,%d;", int(rint(t.x * 1000)), int(rint(t.y * 1000)));
            }
        }
        int h = random_shash(sig) & 0x7fffffff;
        cle = sprintf("%s_%08x", toupper(ty != "" ? ty : "glyphe"), h);
    }
    string asset = cle + "__" + re_replace("^PJ_Peinture_", "", mid);
    // plan du sol sous le symbole posé (moindres carrés z = z0 + b dx + c dy, région majoritaire)
    vector2 smp[];
    append(smp, o);
    if (genre == "gabarit") {
        foreach (int rg; ng) { vector2 qt[] = pj_m_anneau(1, rg); foreach (vector2 v; qt) append(smp, pj_m_poser(v, o, cap, e)); }
    } else if (genre == "parametrique") {
        string nd = ty == "barre" ? "rectangle" : (ty == "point" ? "disque" : (ty == "dent_requin" ? "triangle" : "chevron"));
        dict prm = prim(0, nd, p0);
        vector2 qf[] = pj_m_forme(ty, prm, corde);
        foreach (vector2 v; qf) append(smp, pj_m_poser(v, o, cap, 1.0));
    } else {
        foreach (int r; prs) { vector2 q[] = pj_m_anneau(0, r); foreach (vector2 v; q) append(smp, v); }
    }
    dict cpt = {};
    int reg = -1, best = 0;
    foreach (vector2 v; smp) {
        int rr = pj_niv_region(g, v.x, v.y);
        if (rr < 0) continue;
        string k = itoa(rr);
        int c = 0;
        if (isvalidindex(cpt, k)) c = cpt[k];
        cpt[k] = c + 1;
        if (c + 1 > best || (c + 1 == best && rr < reg)) { best = c + 1; reg = rr; }
    }
    // (après le vote de région) TQ-MQG-006 : planéité contrôlée sous l'emprise + 0,25 m (grille de 0,25 m dans la boîte du contour élargie)
    {
        vector2 lo = smp[0], hi = smp[0];
        foreach (vector2 v; smp) { lo = min(lo, v); hi = max(hi, v); }
        for (float gx = lo.x - 0.25; gx <= hi.x + 0.25 + 1e-6; gx += 0.25)
            for (float gy = lo.y - 0.25; gy <= hi.y + 0.25 + 1e-6; gy += 0.25)
                append(smp, set(gx, gy));
    }
    float s1 = 0, sx = 0, sy = 0, sxx = 0, sxy = 0, syy = 0, sz = 0, sxz = 0, syz = 0;
    float zs[];
    vector2 ds[];
    foreach (vector2 v; smp) {
        float z = pj_niv_z(g, v.x, v.y, reg);
        if (z < 0.5 * PJ_NIV_ABSENT) z = pj_niv_z(g, v.x, v.y, -1);
        if (z < 0.5 * PJ_NIV_ABSENT) continue;
        // plan ajusté sur le SOL FABRIQUÉ (entrée 3, pj::sol) s'il est branché : résidu de planéité mesuré sur le sol
        // réellement maillé (TQ-MQG-006 : 37 symboles rigides sur un sol non plan, jusqu'à 41 mm ; revues 11/10/2026)
        if (nprimitives(3) > 0) { int ok = 0; z = pj_m_z_sol(3, v.x, v.y, z, 0.4, reg, ok); }
        vector2 dd = v - o;
        append(zs, z);
        append(ds, dd);
        s1 += 1; sx += dd.x; sy += dd.y; sxx += dd.x * dd.x; sxy += dd.x * dd.y; syy += dd.y * dd.y;
        sz += z; sxz += dd.x * z; syz += dd.y * z;
    }
    float z0 = 0, pb = 0, pc = 0, residu = 0;
    if (s1 >= 3) {
        matrix3 m = set(s1, sx, sy, sx, sxx, sxy, sy, sxy, syy);
        if (abs(determinant(m)) > 1e-9) {
            vector sol = set(sz, sxz, syz) * invert(m);
            z0 = sol.x; pb = sol.y; pc = sol.z;
        } else z0 = sz / s1;
        for (int k = 0; k < len(zs); k++) {
            vector2 dd = ds[k];
            residu = max(residu, abs(zs[k] - (z0 + pb * dd.x + pc * dd.y)));
        }
    } else if (s1 > 0) z0 = sz / s1;
    int drape = (mode == "drape") || (mode == "instances" && residu > tolp) || s1 == 0;
    if (mode == "instances" && ch("../glyphes_drapes") && genre == "glyphe") drape = 1;
    int proto = 0;
    if (!drape && find(fournis, asset) < 0) { proto = 1; append(fournis, asset); }
    foreach (int r; prs) {
        setprimattrib(0, "pj_genre", r, genre);
        setprimattrib(0, "pj_cle", r, cle);
        setprimattrib(0, "pj_asset", r, asset);
        setprimattrib(0, "pj_o", r, set(o.x, o.y, 0.0));
        setprimattrib(0, "pj_cap", r, cap);
        setprimattrib(0, "pj_e", r, e);
        setprimattrib(0, "pj_ecart_gabarit", r, ecart);
        setprimattrib(0, "pj_plan", r, set(z0, pb, pc));
        setprimattrib(0, "pj_residu_plan", r, residu);
        setprimattrib(0, "pj_region", r, reg);
        setprimattrib(0, "pj_drape", r, drape);
        setprimattrib(0, "pj_proto", r, proto);
    }
}
"""

VEX_EMPREINTES = r"""
// Empreintes d'un symbole (une fois par entité, depuis sa première primitive) :
//   repère « gabarit » (prototype de bibliothèque, à plat, origine du gabarit) ou « pose » (repère local, drapé).
string rep = chs("../__repere");                  // fixé par le nœud : gabarit | pose
int sel = rep == "gabarit" ? i@pj_proto : i@pj_drape;
int premier = findattribval(0, "prim", "id", s@id) == @primnum;
if (sel && premier) {
    string genre = s@pj_genre;
    vector o3 = v@pj_o;
    vector2 o = set(o3.x, o3.y);
    float cap = f@pj_cap;
    float e = f@pj_e;
    int nouv[];
    if (genre == "gabarit") {
        int ng[] = findattribval(1, "prim", "gabarit", s@gabarit);
        foreach (int rg; ng) {
            vector2 qt[] = pj_m_anneau(1, rg);
            vector2 q[];
            foreach (vector2 v; qt) append(q, rep == "gabarit" ? v * e : pj_m_poser(v, o, cap, e));
            int np = pj_m_poly(0, q);
            int pa = prim(1, "partie", rg);
            int an = prim(1, "anneau", rg);
            setprimattrib(0, "partie", np, pa);
            setprimattrib(0, "anneau", np, an);
            append(nouv, np);
        }
    } else if (genre == "parametrique") {
        string ty = s@type;
        string nd = ty == "barre" ? "rectangle" : (ty == "point" ? "disque" : (ty == "dent_requin" ? "triangle" : "chevron"));
        dict prm = prim(0, nd, @primnum);
        vector2 qf[] = pj_m_forme(ty, prm, ch("../corde"));
        vector2 q[];
        foreach (vector2 v; qf) append(q, rep == "gabarit" ? v : pj_m_poser(v, o, cap, 1.0));
        int np = pj_m_poly(0, q);
        setprimattrib(0, "partie", np, 0);
        setprimattrib(0, "anneau", np, 0);
        append(nouv, np);
    } else {
        int prs[] = findattribval(0, "prim", "id", s@id);
        foreach (int r; prs) {
            vector2 qd[] = pj_m_anneau(0, r);
            vector2 q[];
            foreach (vector2 v; qd) append(q, rep == "gabarit" ? pj_m_deposer(v, o, cap, 1.0) : v);
            int np = pj_m_poly(0, q);
            int pa = prim(0, "partie", r);
            int an = prim(0, "anneau", r);
            setprimattrib(0, "partie", np, pa);
            setprimattrib(0, "anneau", np, an);
            append(nouv, np);
        }
    }
    string nom = rep == "gabarit" ? s@pj_asset : s@id;
    foreach (int np; nouv) {
        setprimattrib(0, "pj_entite", np, nom);
        setprimattrib(0, "id", np, rep == "gabarit" ? s@pj_asset : s@id);
        setprimattrib(0, "pj_source", np, @primnum);
        setprimattrib(0, "pj_region", np, rep == "gabarit" ? -1 : i@pj_region);
        setprimattrib(0, "name", np, s@pj_asset);
    }
}
removeprim(0, @primnum, 1);
"""

VEX_INSTANCES = r"""
// Points d'instances (contrat pj_points/0.1, Houdini Engine : unreal_instance) : un point par symbole non drapé, à
// l'origine du gabarit sur le plan du sol ; orient = inclinaison du plan (normale) x lacet du cap (prototype : +X vers
// l'avant = sens de circulation, README_HDA.md § 7) ; cd = [couverture, usure] ; x = traçabilité.
int np = nprimitives(1);
string vus[];
for (int pr = 0; pr < np; pr++) {
    string id = prim(1, "id", pr);
    if (find(vus, id) >= 0) continue;
    append(vus, id);
    int dr = prim(1, "pj_drape", pr);
    if (dr) continue;
    vector o = prim(1, "pj_o", pr);
    vector pl = prim(1, "pj_plan", pr);
    float cap = prim(1, "pj_cap", pr);
    int pt = addpoint(0, set(o.x, pl.x, -o.y));
    vector nl = normalize(set(-pl.y, -pl.z, 1.0));
    vector nh = set(nl.x, nl.z, -nl.y);
    vector4 q = qmultiply(dihedral({0, 1, 0}, nh), quaternion(radians(cap), {0, 1, 0}));
    string asset = prim(1, "pj_asset", pr);
    setpointattrib(0, "orient", pt, q);
    setpointattrib(0, "scale", pt, set(1.0, 1.0, 1.0));
    setpointattrib(0, "id", pt, id);
    setpointattrib(0, "name", pt, asset);
    setpointattrib(0, "asset", pt, asset);
    string sm = "SM_" + pj_nom_prim(asset);
    setpointattrib(0, "unreal_instance", pt, chs("../bibliotheque_ue") + "/" + sm + "." + sm);
    int gr = prim(1, "graine", pr);
    setpointattrib(0, "graine", pt, gr);
    setpointattrib(0, "seed", pt, gr);
    setpointattrib(0, "density", pt, 1.0);
    float cd[];
    float cv = prim(1, "couverture", pr);
    float us = prim(1, "usure", pr);
    append(cd, cv);
    append(cd, us);
    setpointattrib(0, "cd", pt, cd);
    string classe = prim(1, "classe", pr);
    string typ = prim(1, "type", pr);
    string coul = prim(1, "couleur", pr);
    string mat = prim(1, "materiau_id", pr);
    string genre = prim(1, "pj_genre", pr);
    string forme = prim(1, "pj_cle", pr);
    string srcg = prim(1, "src", pr);
    float ec = prim(1, "pj_ecart_gabarit", pr);
    float rs = prim(1, "pj_residu_plan", pr);
    dict x;
    x["entite"] = id;
    x["classe"] = classe;
    x["type"] = typ;
    x["couleur"] = coul;
    x["materiau"] = mat;
    x["genre"] = genre;
    x["forme"] = forme;
    x["cap_deg"] = cap;
    x["ecart_gabarit_m"] = rint(ec * 10000) / 10000;
    x["residu_plan_m"] = rint(rs * 10000) / 10000;
    x["src"] = srcg;
    setpointattrib(0, "x", pt, x);
    setpointattrib(0, "materiau_id", pt, mat);
}
"""

VEX_CONTROLES = r"""
// Bilan de la branche (détail pj_symboles_controles) : genres, instances, drapés, prototypes, écarts au gabarit
// (FUS-SNP-004, VAL-FLE-001 : forme normative), résidus de plan.
int np = nprimitives(1);
string vus[];
dict genres;
int n_inst = 0, n_drape = 0;
float emax = 0, rmax = 0;
string emax_id = "", rmax_id = "";
string assets[];
for (int pr = 0; pr < np; pr++) {
    string id = prim(1, "id", pr);
    if (find(vus, id) >= 0) continue;
    append(vus, id);
    string gn = prim(1, "pj_genre", pr);
    int c = 0;
    if (isvalidindex(genres, gn)) c = genres[gn];
    genres[gn] = c + 1;
    int dr = prim(1, "pj_drape", pr);
    int pt = prim(1, "pj_proto", pr);
    string as = prim(1, "pj_asset", pr);
    if (dr) n_drape++; else n_inst++;
    if (pt) append(assets, as);
    float ec = prim(1, "pj_ecart_gabarit", pr);
    float rs = prim(1, "pj_residu_plan", pr);
    if (gn != "glyphe" && ec > emax) { emax = ec; emax_id = id; }
    if (rs > rmax) { rmax = rs; rmax_id = id; }
}
dict d;
d["entites"] = len(vus);
d["genres"] = genres;
d["instances"] = n_inst;
d["drapes"] = n_drape;
d["prototypes"] = len(assets);
d["ecart_gabarit_max_m"] = emax;
d["ecart_gabarit_max_id"] = emax_id;
d["residu_plan_max_m"] = rmax;
d["residu_plan_max_id"] = rmax_id;
string rg[] = {"FUS-SNP-004", "MQ-FLE-006", "MQ-RAL-001", "MQ-CHR-001", "MQ-ILO-003", "VAL-FLE-001", "TQ-SOL-013"};
d["regles"] = rg;
d@pj_symboles_controles = d;
"""


def parametres():
    sym = [
        T.MenuParmTemplate("mode", "Sortie des symboles", menu_items=("instances", "drape", "tout"),
                           menu_labels=("Instances de prototypes (repli drapé si le sol n'est pas plan)",
                                        "Maillages drapés uniques", "Les deux (contrôle)"), default_value=0,
                           help="Instances : un point par symbole (sortie 2) et un prototype par forme et peinture "
                                "(sortie 3) ; un symbole dont le sol s'écarte du plan de pose de plus de la tolérance "
                                "est drapé (sortie 1)."),
        T.FloatParmTemplate("tol_plan", "Tolérance de planéité du sol (m)", 1, default_value=(0.001,), min=0.0,
                            max=0.05, help="Résidu max du plan de pose (moindres carrés, sur le sol fabriqué s'il est "
                                           "branché) au-delà duquel le symbole est drapé. TQ-MQG-006 : prototype rigide "
                                           "seulement si le sol est plan à 1 mm près."),
        T.FloatParmTemplate("tol_gabarit", "Tolérance d'écart au gabarit (m)", 1, default_value=(0.03,), min=0.0,
                            max=0.5, help="Écart max entre le contour décrit et le gabarit IISR posé pour utiliser le "
                                          "gabarit exact (FUS-SNP-004) ; au-delà : forme décrite (glyphe)."),
        T.ToggleParmTemplate("glyphes_drapes", "Glyphes hors gabarit drapés", default_value=False,
                             help="Formes décrites sans gabarit (PMR, chiffres) en maillages drapés plutôt qu'en instances."),
        T.FloatParmTemplate("corde", "Erreur de corde des disques (m)", 1, default_value=(0.001,), min=0.0001,
                            max=0.01, help="marquages_geometrie.repere.discretisation : 1 mm."),
        T.StringParmTemplate("bibliotheque_ue", "Dossier Unreal des prototypes", 1, default_value=(M.LIB_UE,),
                             help="unreal_instance = <dossier>/SM_<asset>.SM_<asset>."),
        T.StringParmTemplate("couche_lib", "Couche USD des prototypes", 1, default_value=(M.COUCHE_LIB,)),
        T.StringParmTemplate("pivot_prototypes", "Pivot des prototypes (pj_points)", 1,
                             default_value=("origine du gabarit IISR (flèches : milieu du pied de la tige ; formes : centre ; "
                                            "dent de requin : milieu de la base ; chevron : pointe ; glyphes : centroïde), "
                                            "+X = sens de circulation, +Y à gauche, z = 0 au sol (peinture de -5 à +3 mm)",),
                             help="Recopié dans le champ pivot de points/symboles.json par le pilote."),
        T.StringParmTemplate("sens_cd", "Sens de cd (pj_points)", 1,
                             default_value=("cd = [couverture de peinture 0-1, usure 0-1 (classes IISR 0, 1, 2, 3, F -> 0, "
                                            "1/3, 2/3, 1, 1)]",),
                             help="Recopié dans le champ cd de points/symboles.json par le pilote."),
        T.StringParmTemplate("spec", "Spécification des marquages", 1, default_value=(M.SPEC_DEFAUT,),
                             string_type=T.stringParmType.FileReference, file_type=T.fileType.Any),
    ]
    sol = [
        T.FloatParmTemplate("epaisseur", "Épaisseur au-dessus du sol (m)", 1, default_value=(0.003,), min=0.0, max=0.02),
        T.FloatParmTemplate("enfouissement", "Enfouissement des flancs (m)", 1, default_value=(0.005,), min=0.0,
                            max=0.05),
        T.FloatParmTemplate("chanfrein", "Chanfrein des arêtes du dessus (m)", 1, default_value=(0.001,), min=0.0,
                            max=0.005),
        T.FloatParmTemplate("pas_maillage", "Pas du maillage de drapé (m)", 1, default_value=(0.25,), min=0.02,
                            max=5.0),
        T.ToggleParmTemplate("draper", "Draper sur le nivellement (entrée 2)", default_value=True),
        T.MenuParmTemplate("mode_region", "Région de drapé", menu_items=("piece", "attribut", "point"),
                           menu_labels=("Région majoritaire de la pièce", "Attribut pj_region (région du plan de pose)",
                                        "Région de chaque sommet (suit les marches)"), default_value=1),
        T.FloatParmTemplate("seuil_franchissement", "Seuil de franchissement (m)", 1, default_value=(0.02,), min=0.0,
                            max=0.2),
        T.StringParmTemplate("couche", "Couche USD (pj_couche)", 1, default_value=(M.COUCHE,)),
        T.FloatParmTemplate("cusp", "Angle de rupture des normales (°)", 1, default_value=(30.0,), min=0.0, max=180.0),
    ]
    return [T.FolderParmTemplate("f_symboles", "Symboles", parm_templates=sym, folder_type=T.folderType.Tabs),
            T.FolderParmTemplate("f_solide", "Peinture (solide)", parm_templates=sol, folder_type=T.folderType.Tabs)]


def construire(dossier=ICI):
    L = M.charger(ICI.parent / "pj_marquage_ligne" / "construire.py", "construire_ligne")
    M.installer_commun()
    sub = O.sous_reseau("pj_" + NOM)
    sub.setParmTemplateGroup(T.ParmTemplateGroup(parametres()))
    ent, niv, sol_fab = sub.indirectInputs()[0], sub.indirectInputs()[1], sub.indirectInputs()[2]
    gab = sub.createNode("pj::gabarits_iisr::1.0", "gabarits")
    gab.parm("spec").set('`chs("../spec")`')
    poses = M.wrangle_m(sub, "poses", VEX_POSES, "detail", ent, entrees=(gab, niv, sol_fab))

    def empreintes(nom, repere):
        w = M.wrangle_m(sub, nom, VEX_EMPREINTES.replace('chs("../__repere")', f'"{repere}"'), "primitive", poses,
                        entrees=(gab,))
        return w

    e_proto = empreintes("empreintes_prototypes", "gabarit")
    rot = sub.createNode("xform", "vers_repere_prototype")
    rot.setInput(0, e_proto)
    rot.parm("ry").set(-90.0)                      # gabarit (x droite, y avant) -> prototype +X avant, +Y gauche
    proto = sub.createNode("pj::marquage_solide::1.0", "prototypes")
    proto.setInput(0, rot)
    L.relier_solide(proto)
    proto.parm("draper").deleteAllKeyframes()
    proto.parm("draper").set(0)
    proto.parm("couche").set('`chs("../couche_lib")`')
    proto.parm("pas_maillage").setExpression('ch("../pas_maillage")')
    nom_p = M.wrangle_m(sub, "nom_prototypes", 's@name = s@pj_entite;\n', "primitive", proto, bibliotheques=False)

    vide = sub.createNode("null", "vide")
    vide_b = M.blast(sub, "geometrie_vide", ent, "*", garder=False)
    vide.setInput(0, vide_b)
    inst = M.wrangle_m(sub, "instances", VEX_INSTANCES, "detail", vide, entrees=(poses,), precision64=True)
    sw_i = M.interrupteur(sub, "choix_instances", (vide, inst), 'ch("../mode") != 1')

    e_drape = empreintes("empreintes_drapees", "pose")
    drape = sub.createNode("pj::marquage_solide::1.0", "drape")
    drape.setInput(0, e_drape)
    drape.setInput(1, niv)
    drape.setInput(2, sol_fab)               # sol fabriqué (pj::sol) : drapé sur le sol maillé (TQ-MQG-005)
    L.relier_solide(drape)
    drape.parm("pas_maillage").setExpression('ch("../pas_maillage")')
    tout = sub.createNode("attribwrangle", "tout_draper")
    tout.parm("class").set(1)
    tout.parm("snippet").set('// mode « les deux » : tous les symboles aussi en maillages drapés (contrôle)\ni@pj_drape = 1;\n')
    tout.setInput(0, poses)
    e_tout = M.wrangle_m(sub, "empreintes_toutes", VEX_EMPREINTES.replace('chs("../__repere")', '"pose"'),
                         "primitive", tout, entrees=(gab,))
    sw_d = M.interrupteur(sub, "choix_drapes", (e_drape, e_tout), 'ch("../mode") == 2')
    drape.setInput(0, sw_d)
    ctl = M.wrangle_m(sub, "controles", VEX_CONTROLES, "detail", drape, entrees=(poses,), bibliotheques=False)

    cp = sub.createNode("copytopoints::2.0", "apercu_instances")
    cp.setInput(0, nom_p)
    cp.setInput(1, sw_i)
    cp.parm("useidattrib").set(1)
    cp.parm("idattrib").set("name")
    cp.parm("pack").set(1)

    s1 = sub.createNode("null", "MAILLAGES_DRAPES")
    s1.setInput(0, ctl)
    s2 = sub.createNode("null", "INSTANCES")
    s2.setInput(0, sw_i)
    s3 = sub.createNode("null", "PROTOTYPES")
    s3.setInput(0, nom_p)
    s4 = sub.createNode("null", "APERCU_INSTANCES")
    s4.setInput(0, cp)
    for k, s in enumerate((s1, s2, s3, s4)):
        O.sortie(sub, s, k, f"sortie_{k + 1}")
    O.ranger(sub)
    return O.creer_hda(sub, NOM, "PJ Marquage : symboles IISR (flèches, figurines, pictogrammes)", parametres(),
                       dossier, entrees=(1, 3), sorties=4, icone="SOP_copytopoints",
                       aide="Flèches et symboles en maillages statiques : gabarits exacts de marquages_geometrie.json "
                            "(trous compris) ou formes paramétriques, extrudés et chanfreinés en prototypes de "
                            "bibliothèque ; un point d'instance par symbole (orient = plan du sol x cap, "
                            "unreal_instance) ; maillage drapé unique quand le sol n'est pas plan sous le symbole.",
                       details_aide="== Sorties ==\n\n1. Maillages drapés (symboles hors plan, ou mode drapé).\n"
                                    "2. Points d'instances (id, asset, unreal_instance, orient, scale, graine, cd, x).\n"
                                    "3. Prototypes à plat (pj_entite = asset ; repère +X vers l'avant, +Y à gauche, "
                                    "origine du gabarit).\n4. Aperçu : instances empaquetées (Copy to Points).\n\n"
                                    "Règles : FUS-SNP-004, MQ-FLE-006, MQ-RAL-001, MQ-CHR-001, MQ-ILO-003, VAL-FLE-001, "
                                    "TQ-SOL-013. Contrat : README_HDA.md § 7.",
                       etiquettes_entrees=("Symboles (polygones décrits ou points)", "Nivellement (HeightField)",
                                           "Sol fabriqué (facultatif)"),
                       etiquettes_sorties=("Maillages drapés (Y haut)", "Points d'instances", "Prototypes",
                                           "Aperçu (instances empaquetées)"))


if __name__ == "__main__":
    print(construire())
