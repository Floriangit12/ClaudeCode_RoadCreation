"""Construit l'HDA rg::nivellement::1.0 (modèle de nivellement analytique : sections, bordures, HeightField) ;
hython Houdini 22.

    hython recon/generateur/hda/rg_nivellement/construire.py

Réseau (recon/generateur/hda/README_RG.md § 5) :
    entrée 1 références échantillonnées (rg::graphe), 2 profils, 3 ponctuels (rg::lire_modele)
      -> sections (VEX 64 bits, détail : un point par section de route, tables du nivellement)
      -> bordures (VEX 64 bits, détail : files de bordures chaînées en (s, t), pied, tête, vue, caniveau)
      -> NIVEAUX (sortie 1 : groupes sections et bordures)
      -> heightfield (Volume Wrangle : height, r0, z1, r1, z2, r2 au pas de 0,10 m) -> NIVELLEMENT (sortie 2)
Le modèle de Z est unique (TQ-SOL-013) : bibliothèque VEX hda/commun/vex/rg_niveau.h (chaussée, caniveau, pied,
tête, trottoirs, bandes plantées) ; rg::sol, rg::vers_entites et le HeightField l'évaluent tous les trois.
Les cotes des profils de bordure et de caniveau viennent de la table de pj::bordure (assets/specs/bordures.json,
bordures_elements.json : autre équipe, lecture seule), figée dans les wrangles à la construction.
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "commun"))
sys.path.insert(0, str(ICI.parents[1]))                  # recon/generateur : regles.py
import rg_hda_outils as R  # noqa: E402
import regles  # noqa: E402

NOM = "nivellement"
PJ_BORDURE = R.RACINE / "recon" / "pcg" / "houdini" / "hda" / "pj_bordure"
SPECS = R.RACINE / "assets" / "specs"


def table_profils():
    """Table des profils (base, H ; caniveaux : h_fil_eau, Δh arête − fil d'eau) : celle de pj::bordure
    (profils.construire_table), complétée des hauteurs côté chaussée de bordures.json pour les caniveaux."""
    import json
    sys.path.insert(0, str(PJ_BORDURE))
    sys.path.insert(0, str(ICI.parents[1] / "commun"))
    import bordures_catalogue as BC  # noqa: E402
    # table étendue (lot bordures, intégration de l'étape 2) : table de pj::bordure inchangée pour ses profils, complétée
    # des profils du catalogue route_fr (RF-AS-profil_*) ; sans elle, un type ajouté est refusé (profil inconnu)
    table, src = BC.construire_table_etendue(SPECS)
    brut = json.loads((SPECS / "bordures.json").read_text(encoding="utf-8"))["profils"]
    lignes = []
    for nom in sorted(table):
        t = table[nom]
        dhc = 0.0
        if t["famille"] == "caniveau":
            b = brut.get(nom, {})
            if "h_cote_chaussee" in b and "h_cote_bordure" in b:
                dhc = float(b["h_cote_chaussee"]) - float(b["h_cote_bordure"])
            else:                                        # dessus prolongé jusqu'à u = 0
                c = t["contour"]
                hfe = t["h_fil_eau"]
                hauts = [p for p in c if p[0] < t["base"] - 1e-9 and p[1] > 1e-9]
                dhc = max(p[1] for p in hauts) - hfe if hauts else 0.0
        lignes.append((nom, t["famille"], float(t["base"]), float(t["H"]), float(t.get("h_fil_eau", 0.0)), round(dhc, 6)))
    return lignes, src


def vex_table():
    lignes, src = table_profils()
    q = lambda v: ", ".join(v)  # noqa: E731
    return f"""
// Table des profils de bordure et de caniveau (pj::bordure : assets/specs/bordures.json + bordures_elements.json,
// sha256 {src}) : base (m), H (m), h_fil_eau (caniveaux), Δh arête côté chaussée − fil d'eau (TQ-SOL-013 (3)).
function int rg_table_profil(string nom; export string famille; export float base; export float H; export float hfe;
                             export float dhc)
{{
    string N[] = array({q(f'"{l[0]}"' for l in lignes)});
    string F[] = array({q(f'"{l[1]}"' for l in lignes)});
    float B[] = array({q(repr(l[2]) for l in lignes)});
    float HH[] = array({q(repr(l[3]) for l in lignes)});
    float E[] = array({q(repr(l[4]) for l in lignes)});
    float D[] = array({q(repr(l[5]) for l in lignes)});
    int i = find(N, nom);
    if (i < 0) return 0;
    famille = F[i];
    base = B[i];
    H = HH[i];
    hfe = E[i];
    dhc = D[i];
    return 1;
}}
"""


VEX_SECTIONS = r"""
// sections (détail) : un point par section de route (groupe sections) portant les tables du modèle de nivellement
// (rg_niveau.h) ; bordures virtuelles : une limite non bordée dont la même paire de bandes est bordée dans une autre
// section de la route, et dont le côté haut est une bande haute (avancées : le trottoir garde son niveau).
// Entrées : 0 références (rg::graphe), 1 profils, 2 ponctuels.
float rampe = detail(0, "rg_rampe_plateau_pct");
if (rampe <= 0.0) rampe = chf("../rampe_plateau_pct");
setdetailattrib(0, "rg_rampe_plateau_pct", rampe);
string attr_si[] = array("b_cls", "b_has_g", "l_bord", "l_h", "a_lim", "a_couvert", "a_bev");
string attr_sf[] = array("b_g", "b_retrait", "b_dz", "l_base", "l_H", "l_vue", "l_wc", "l_dhc", "l_hfe", "a_s0", "a_s1",
                         "a_vue", "a_r", "r_s0", "r_s1");
string attr_ss[] = array("b_type", "b_mat", "b_id", "l_prof", "l_cprof", "l_mat", "r_type", "a_type");
int vide_i[];
float vide_f[];
string vide_s[];
foreach (string a; attr_si) addpointattrib(0, a, vide_i);
foreach (string a; attr_sf) addpointattrib(0, a, vide_f);
foreach (string a; attr_ss) addpointattrib(0, a, vide_s);
addpointattrib(0, "route", "");
addpointattrib(0, "section", -1);
addpointattrib(0, "profil", "");
addpointattrib(0, "transition", "");
addpointattrib(0, "s0", 0.0);
addpointattrib(0, "s1", 0.0);
addpointattrib(0, "n_bandes", 0);
addpointattrib(0, "abord_g", 0.0);
addpointattrib(0, "abord_d", 0.0);
addpointattrib(0, "abord_g_mat", "");
addpointattrib(0, "abord_d_mat", "");
int vi[];
float vf[];
string lai[] = array("larg_type", "larg_s0", "larg_v0", "larg_n");
string laf[] = array("larg_s", "larg_v");
foreach (string a; lai) addpointattrib(0, a, vi);
foreach (string a; laf) addpointattrib(0, a, vf);
addpointattrib(0, "ref_limite", 0);
addpointattrib(0, "ref_decalage", 0.0);
// ralentisseurs (plateaux, dos-d'âne) recopiés des ponctuels : groupe ralentisseurs (rg_dz_chaussee sur « niveaux »)
addpointattrib(0, "type", "");
addpointattrib(0, "s", 0.0);
addpointattrib(0, "longueur_m", 0.0);
addpointattrib(0, "hauteur_m", 0.0);
addpointattrib(0, "largeur_m", 0.0);
addpointattrib(0, "id", "");
for (int p = 0; p < npoints(2); p++) {
    string ty = point(2, "type", p);
    if (ty != "plateau" && ty != "dos_d_ane") continue;
    int q = addpoint(0, {0, 0, 0});
    setpointgroup(0, "ralentisseurs", q, 1);
    string rr = point(2, "route", p), ii = point(2, "id", p);
    float sv = point(2, "s", p), lg = point(2, "longueur_m", p), hh = point(2, "hauteur_m", p), la = point(2, "largeur_m", p);
    setpointattrib(0, "route", q, rr);
    setpointattrib(0, "type", q, ty);
    setpointattrib(0, "id", q, ii);
    setpointattrib(0, "s", q, sv);
    setpointattrib(0, "longueur_m", q, lg);
    setpointattrib(0, "hauteur_m", q, hh);
    setpointattrib(0, "largeur_m", q, la);
}
string vegetaux[] = array("gazon_tondu", "gazon_sec", "herbe_haute", "terre_nue", "paillage_mineral",
                          "brf_bois_concasse", "brf_bois_gris", "noue_plantee");
for (int pr = 0; pr < nprimitives(0); pr++) {
    if (!inprimgroup(0, "echantillonnees", pr)) continue;
    string rid = prim(0, "id", pr);
    float SEC0[] = prim(0, "sec_s0", pr);
    float SEC1[] = prim(0, "sec_s1", pr);
    string SP[] = prim(0, "sec_profil", pr);
    string ST[] = prim(0, "sec_transition", pr);
    int ns = len(SEC0);
    // ralentisseurs de la route (plateau, dos-d'âne : relèvent la chaussée d'un trottoir à l'autre)
    float r0[], r1[];
    string rty[];
    int ppts[] = findattribval(2, "point", "route", rid);
    foreach (int p; ppts) {
        string ty = point(2, "type", p);
        if (ty != "plateau" && ty != "dos_d_ane") continue;
        float sc = point(2, "s", p);
        float lg = point(2, "longueur_m", p);
        push(r0, sc - lg / 2.0);
        push(r1, sc + lg / 2.0);
        push(rty, ty);
    }
    // bordures réelles de toutes les sections (paires de bandes) : sources des bordures virtuelles
    int rb_k[], rb_h[];
    string rb_g[], rb_d[], rb_prof[], rb_cprof[], rb_mat[];
    float rb_vue[], rb_wc[], rb_dhc[], rb_hfe[], rb_base[], rb_H[];
    for (int k = 0; k < ns; k++) {
        int pp = rg_point_profil(1, SP[k]);
        if (pp < 0) error("route %s : profil %s absent", rid, SP[k]);
        string bid[] = point(1, "bande_id", pp);
        string lj[] = point(1, "lim_json", pp);
        for (int l = 1; l < len(lj) - 1; l++) {
            dict d = json_loads(lj[l], 0);
            if (!isvalidindex(d, "bordure")) continue;
            dict bo = d["bordure"];
            string prof = bo["profil"];
            string fam;
            float base, H, hfe, dhc;
            if (!rg_table_profil(prof, fam, base, H, hfe, dhc)) error("route %s : profil de bordure %s inconnu", rid, prof);
            if (typeid(bo, "vue_m") != 0 && typeid(bo, "vue_m") != 1)
                error("route %s section %d limite %d : vue en loi de s non prise en charge (lot L2)", rid, k, l);
            float vue = bo["vue_m"];
            string ch = bo["cote_haut"];
            float wc = 0.0, cdhc = 0.0, chfe = 0.0;
            string cprof = "";
            if (isvalidindex(bo, "caniveau")) {
                dict can = bo["caniveau"];
                string cp = can["profil"];
                if (cp != "" && cp != "aucun") {
                    string cote = isvalidindex(can, "cote") ? can["cote"] : "";
                    if (cote == ch) error("route %s section %d limite %d : caniveau du côté haut", rid, k, l);
                    string cf;
                    float cb, cH;
                    if (!rg_table_profil(cp, cf, cb, cH, chfe, cdhc)) error("route %s : profil de caniveau %s inconnu", rid, cp);
                    wc = cb;
                    cprof = cp;
                }
            }
            push(rb_k, k);
            push(rb_g, bid[l - 1]);
            push(rb_d, bid[l]);
            push(rb_h, ch == "gauche" ? 1 : -1);
            push(rb_prof, prof);
            push(rb_vue, vue);
            push(rb_wc, wc);
            push(rb_dhc, cdhc);
            push(rb_hfe, chfe);
            push(rb_cprof, cprof);
            push(rb_base, base);
            push(rb_H, H);
            push(rb_mat, isvalidindex(bo, "materiau_id") ? string(bo["materiau_id"]) : "");
        }
    }
    for (int k = 0; k < ns; k++) {
        int pp = rg_point_profil(1, SP[k]);
        int nb = point(1, "n_bandes", pp);
        string bid[] = point(1, "bande_id", pp);
        string bty[] = point(1, "bande_type", pp);
        string bma[] = point(1, "bande_materiau", pp);
        string bjs[] = point(1, "bande_json", pp);
        string lj[] = point(1, "lim_json", pp);
        int b_cls[], b_has_g[];
        float b_g[], b_ret[], b_dz[];
        for (int b = 0; b < nb; b++) {
            dict bj = json_loads(bjs[b], 0);
            dict niv;
            if (isvalidindex(bj, "niveau")) niv = bj["niveau"];
            string ref = isvalidindex(niv, "reference") ? string(niv["reference"]) : "chaussee";
            float dzm = isvalidindex(niv, "dz_m") ? float(niv["dz_m"]) : 0.0;
            if (isvalidindex(niv, "forme") && string(niv["forme"]) == "bombe")
                error("route %s section %d bande %s : forme bombée non prise en charge (lot L2)", rid, k, bid[b]);
            push(b_cls, ((ref == "trottoir" || ref == "propre") && dzm > 1e-6) ? 1 : 0);
            int hg = isvalidindex(niv, "devers_pct");
            push(b_has_g, hg);
            push(b_g, hg ? float(niv["devers_pct"]) / 100.0 : 0.0);
            push(b_dz, dzm);
            push(b_ret, 0.0);
        }
        int l_bord[], l_h[];
        float l_base[], l_H[], l_vue[], l_wc[], l_dhc[], l_hfe[];
        string l_prof[], l_cprof[], l_mat[];
        int a_lim[], a_couv[], a_bev[];
        float a_s0[], a_s1[], a_vue[], a_r[];
        string a_type[];
        for (int l = 0; l <= nb; l++) {
            int bord = 0, h = 0;
            float base = 0, H = 0, vue = -1, wc = 0, dhc = 0, hfe = 0;
            string prof = "", cprof = "", mat = "";
            if (l > 0 && l < nb) {
                dict d = json_loads(lj[l], 0);
                int src = -1;
                for (int i = 0; i < len(rb_k); i++)
                    if (rb_k[i] == k && rb_g[i] == bid[l - 1] && rb_d[i] == bid[l]) { src = i; bord = 1; break; }
                if (src < 0) {
                    // bordure virtuelle : même paire de bandes bordée dans la section la plus proche, côté haut haut
                    int best = 1000000;
                    for (int i = 0; i < len(rb_k); i++) {
                        if (rb_g[i] != bid[l - 1] || rb_d[i] != bid[l]) continue;
                        int hb = rb_h[i] > 0 ? l - 1 : l;
                        if (b_cls[hb] != 1) continue;
                        if (abs(rb_k[i] - k) < best) { best = abs(rb_k[i] - k); src = i; }
                    }
                    if (src >= 0) bord = 2;
                }
                if (src >= 0) {
                    h = rb_h[src]; prof = rb_prof[src]; base = rb_base[src]; H = rb_H[src]; vue = rb_vue[src];
                    wc = rb_wc[src]; dhc = rb_dhc[src]; hfe = rb_hfe[src]; cprof = rb_cprof[src]; mat = rb_mat[src];
                }
                if (bord == 1) {
                    dict bo = d["bordure"];
                    if (isvalidindex(bo, "abaisses")) {
                        dict abs_[] = bo["abaisses"];
                        foreach (dict ab; abs_) {
                            float s0 = ab["s0"], s1 = ab["s1"];
                            float va = isvalidindex(ab, "vue_m") ? float(ab["vue_m"]) : 0.02;
                            float rr = isvalidindex(ab, "rampant_m") ? float(ab["rampant_m"]) : 0.0;
                            int couv = 0;
                            for (int i = 0; i < len(r0); i++) if (s1 > r0[i] && s0 < r1[i]) couv = 1;
                            push(a_lim, l); push(a_s0, s0); push(a_s1, s1); push(a_vue, va); push(a_r, rr);
                            push(a_couv, couv);
                            push(a_bev, isvalidindex(ab, "bev") ? int(ab["bev"]) : 0);
                            push(a_type, isvalidindex(ab, "type") ? string(ab["type"]) : "traversee");
                        }
                    }
                }
                // une bande haute contre une bande basse exige une bordure (réelle ou virtuelle)
                if (bord == 0 && b_cls[l - 1] != b_cls[l])
                    error("route %s section %d : dénivelé sans bordure entre %s et %s", rid, k, bid[l - 1], bid[l]);
            }
            push(l_bord, bord); push(l_h, h); push(l_base, base); push(l_H, H); push(l_vue, vue); push(l_wc, wc);
            push(l_dhc, dhc); push(l_hfe, hfe); push(l_prof, prof); push(l_cprof, cprof); push(l_mat, mat);
        }
        // retrait sous la tête : TQ-SOL-013 (6) trottoir, quai, séparateur : 4 mm ; (7) bande plantée isolée entre
        // deux bordures réelles : 4 cm (3 à 5 cm, GA-ARB-003)
        for (int b = 0; b < nb; b++) {
            if (b_cls[b] != 1) continue;
            int plante = (bty[b] == "terre_plein" || bty[b] == "bande_plantee") && find(vegetaux, bma[b]) >= 0
                         && l_bord[b] == 1 && l_bord[b + 1] == 1;
            b_ret[b] = plante ? 0.04 : 0.004;
        }
        int p = addpoint(0, {0, 0, 0});
        setpointgroup(0, "sections", p, 1);
        // tables du profil recopiées (géométrie « niveaux » autonome : rg_t_limites sur le point de section)
        int lt[] = point(1, "larg_type", pp);
        int ls0[] = point(1, "larg_s0", pp);
        int lv0[] = point(1, "larg_v0", pp);
        int lnn[] = point(1, "larg_n", pp);
        float lss[] = point(1, "larg_s", pp);
        float lvv[] = point(1, "larg_v", pp);
        setpointattrib(0, "larg_type", p, lt);
        setpointattrib(0, "larg_s0", p, ls0);
        setpointattrib(0, "larg_v0", p, lv0);
        setpointattrib(0, "larg_n", p, lnn);
        setpointattrib(0, "larg_s", p, lss);
        setpointattrib(0, "larg_v", p, lvv);
        int rl = point(1, "ref_limite", pp);
        float rd = point(1, "ref_decalage", pp);
        setpointattrib(0, "ref_limite", p, rl);
        setpointattrib(0, "ref_decalage", p, rd);
        setpointattrib(0, "route", p, rid);
        setpointattrib(0, "section", p, k);
        setpointattrib(0, "profil", p, SP[k]);
        setpointattrib(0, "transition", p, ST[k]);
        setpointattrib(0, "s0", p, SEC0[k]);
        setpointattrib(0, "s1", p, SEC1[k]);
        setpointattrib(0, "n_bandes", p, nb);
        setpointattrib(0, "b_cls", p, b_cls);
        setpointattrib(0, "b_has_g", p, b_has_g);
        setpointattrib(0, "b_g", p, b_g);
        setpointattrib(0, "b_retrait", p, b_ret);
        setpointattrib(0, "b_dz", p, b_dz);
        setpointattrib(0, "b_type", p, bty);
        setpointattrib(0, "b_mat", p, bma);
        setpointattrib(0, "b_id", p, bid);
        setpointattrib(0, "l_bord", p, l_bord);
        setpointattrib(0, "l_h", p, l_h);
        setpointattrib(0, "l_base", p, l_base);
        setpointattrib(0, "l_H", p, l_H);
        setpointattrib(0, "l_vue", p, l_vue);
        setpointattrib(0, "l_wc", p, l_wc);
        setpointattrib(0, "l_dhc", p, l_dhc);
        setpointattrib(0, "l_hfe", p, l_hfe);
        setpointattrib(0, "l_prof", p, l_prof);
        setpointattrib(0, "l_cprof", p, l_cprof);
        setpointattrib(0, "l_mat", p, l_mat);
        setpointattrib(0, "a_lim", p, a_lim);
        setpointattrib(0, "a_s0", p, a_s0);
        setpointattrib(0, "a_s1", p, a_s1);
        setpointattrib(0, "a_vue", p, a_vue);
        setpointattrib(0, "a_r", p, a_r);
        setpointattrib(0, "a_couvert", p, a_couv);
        setpointattrib(0, "a_bev", p, a_bev);
        setpointattrib(0, "a_type", p, a_type);
        setpointattrib(0, "r_s0", p, r0);
        setpointattrib(0, "r_s1", p, r1);
        setpointattrib(0, "r_type", p, rty);
    }
}
"""

VEX_ABORDS = r"""
// abords (point, groupe sections) : largeur et matériau des zones d'abords du modèle (attributs cote, largeur_m,
// materiau_id) ; sans zone : pas d'abord (le sol s'arrête à la limite extérieure du profil).
string rid = s@route;
for (int pr = 0; pr < nprimitives(1); pr++) {
    string pz = prim(1, "props", pr);
    if (pz == "") continue;
    dict z = json_loads(pz, 0);
    // abords au sol (FORMAT_DESCRIPTION : pelouse, prairie, champ, massif, parking, forêt, haie) ; bâti : pas de sol
    string ty = isvalidindex(z, "type") ? string(z["type"]) : "";
    string sols[] = array("espace_vert", "friche", "champ", "massif", "parking", "foret", "haie");
    if (find(sols, ty) < 0) continue;
    if (!isvalidindex(z, "attributs")) continue;
    dict at = z["attributs"];
    string cote = isvalidindex(at, "cote") ? string(at["cote"]) : "";
    float lg = isvalidindex(at, "largeur_m") ? float(at["largeur_m"]) : 0.0;
    string mat = isvalidindex(at, "materiau_id") ? string(at["materiau_id"]) : "";
    if (mat == "") mat = ty == "foret" ? "terre_nue" : "gazon_tondu";
    string zr = isvalidindex(z, "route") ? string(z["route"]) : "";
    if (zr != "" && zr != rid) continue;
    if (cote == "gauche") { f@abord_g = lg; s@abord_g_mat = mat; }
    if (cote == "droite") { f@abord_d = lg; s@abord_d_mat = mat; }
}
"""

VEX_BORDURES = r"""
// bordures (détail) : files de bordures en (s, t), chaînées, côté haut à gauche (contrat de pj::bordure) ;
// pièces longitudinales (limites bordées réelles de chaque section) et transversales (retours de bordure aux
// changements de profil instantanés : différence des intervalles hauts de part et d'autre de la jonction).
// Entrées : 0 références, 1 profils, 2 ponctuels, 3 sections. Sortie : polylignes (groupe bordures) ; points :
// s_ref, t_ref, pied, tete, vue, zbf (chaussée au droit de la face, ralentisseurs compris), zemp (sol caché),
// can (caniveau présent), grille (caniveau déclaré relevé par un ralentisseur : caniveau à grille), k_bas, b_bas
// (bande basse), kind (0 longitudinale, 1 transversale), limite, section.
float rampe = detail(3, "rg_rampe_plateau_pct");
float pas_t = chf("../pas_transversal");
string attr_f[] = array("s_ref", "t_ref", "pied", "tete", "vue", "zbf", "zemp", "x", "y", "wcp", "dhcp", "kappa");
string attr_i[] = array("can", "k_bas", "b_bas", "kind", "limite", "section", "k_haut", "b_haut", "grille");
foreach (string a; attr_f) addpointattrib(0, a, 0.0);
foreach (string a; attr_i) addpointattrib(0, a, -1);
addprimattrib(0, "id", "");
addprimattrib(0, "route", "");
addprimattrib(0, "profil", "");
addprimattrib(0, "base", 0.0);
addprimattrib(0, "H", 0.0);
addprimattrib(0, "cprof", "");
addprimattrib(0, "wc", 0.0);
addprimattrib(0, "dhc", 0.0);
addprimattrib(0, "hfe", 0.0);
addprimattrib(0, "materiau_id", "");
addprimattrib(0, "fermee", 0);

for (int pr = 0; pr < nprimitives(0); pr++) {
    if (!inprimgroup(0, "echantillonnees", pr)) continue;
    string rid = prim(0, "id", pr);
    float SEC0[] = prim(0, "sec_s0", pr);
    float SEC1[] = prim(0, "sec_s1", pr);
    string SP[] = prim(0, "sec_profil", pr);
    int ns = len(SEC0);
    int rpts[] = primpoints(0, pr);
    float SR[];
    foreach (int p; rpts) { float sv = point(0, "s", p); push(SR, sv); }
    // pièces : points aplatis (offset, nombre), propriétés par pièce
    float P_s[], P_t[], P_pied[], P_tete[], P_vue[], P_zbf[], P_zemp[], P_wc[], P_dhc[];
    int P_can[], P_kb[], P_bb[], P_kind[], P_lim[], P_sec[], P_kh[], P_bh[], P_gri[];
    int Q_off[], Q_n[];
    string Q_prof[], Q_cprof[], Q_mat[];
    float Q_base[], Q_H[], Q_wc[], Q_dhc[], Q_hfe[];
    for (int k = 0; k < ns; k++) {
        int pp = rg_point_profil(1, SP[k]);
        int sp = rg_point_section(3, rid, k);
        int lb[] = point(3, "l_bord", sp);
        int lh[] = point(3, "l_h", sp);
        string lprof[] = point(3, "l_prof", sp);
        string lcprof[] = point(3, "l_cprof", sp);
        string lmat[] = point(3, "l_mat", sp);
        float lbase[] = point(3, "l_base", sp);
        float lH[] = point(3, "l_H", sp);
        float lwc[] = point(3, "l_wc", sp);
        float ldhc[] = point(3, "l_dhc", sp);
        float lhfe[] = point(3, "l_hfe", sp);
        int al[] = point(3, "a_lim", sp);
        float a0[] = point(3, "a_s0", sp);
        float a1[] = point(3, "a_s1", sp);
        float ar[] = point(3, "a_r", sp);
        float r0[] = point(3, "r_s0", sp);
        float r1[] = point(3, "r_s1", sp);
        float S0 = SEC0[k], S1 = SEC1[k];
        for (int l = 1; l < len(lb) - 1; l++) {
            if (lb[l] != 1) continue;
            // abscisses : échantillons de la référence dans la section + bornes des abaissés, rampants, ralentisseurs
            float ss[];
            foreach (float x; SR) if (x >= S0 - 1e-9 && x <= S1 + 1e-9) push(ss, x);
            push(ss, S0); push(ss, S1);
            for (int i = 0; i < len(al); i++) {
                if (al[i] != l) continue;
                float c[] = array(a0[i] - ar[i], a0[i], a1[i], a1[i] + ar[i]);
                foreach (float x; c) if (x > S0 && x < S1) push(ss, x);
            }
            for (int i = 0; i < len(r0); i++) {
                float c[] = array(r0[i], r1[i]);
                foreach (float x; c) if (x > S0 && x < S1) push(ss, x);
            }
            ss = sort(ss);
            float su[];
            foreach (float x; ss) if (len(su) == 0 || x - su[-1] > 1e-7) push(su, x);
            int h = lh[l];
            if (h < 0) su = reverse(su);                 // côté haut à gauche : sens −s si le haut est à droite
            push(Q_off, len(P_s));
            push(Q_n, len(su));
            push(Q_prof, lprof[l]); push(Q_cprof, lcprof[l]); push(Q_mat, lmat[l]); push(Q_base, lbase[l]);
            push(Q_H, lH[l]); push(Q_wc, lwc[l]); push(Q_dhc, ldhc[l]); push(Q_hfe, lhfe[l]);
            int bb = h > 0 ? l : l - 1;
            int hb = h > 0 ? l - 1 : l;
            foreach (float s; su) {
                float T[], A[], G[], PIED[], TETE[], VUE[], dz;
                int CLS[];
                string msg;
                if (!rg_coupe(1, pp, 3, sp, 2, rid, s, rampe, T, A, G, CLS, PIED, TETE, VUE, dz, msg)) error("%s", msg);
                push(P_s, s); push(P_t, T[l]);
                push(P_pied, PIED[l]); push(P_tete, TETE[l]); push(P_vue, VUE[l]);
                // chaussée visible au droit de la face : avec caniveau déclaré, fil d'eau (+ dz : sur un
                // ralentisseur le caniveau est remplacé par la même pente relevée) ; sinon chaussée prolongée
                push(P_zbf, lwc[l] > 0.0 ? PIED[l] + dz : rg_z_bande(A, G, CLS, dz, bb, T[l]));
                push(P_zemp, PIED[l] - 0.20);
                push(P_can, rg_caniveau_present(3, sp, l, s));
                push(P_gri, rg_caniveau_releve(3, sp, l, s));
                push(P_kb, k); push(P_bb, bb); push(P_kh, k); push(P_bh, hb);
                push(P_kind, 0); push(P_lim, l); push(P_sec, k);
                push(P_wc, lwc[l]); push(P_dhc, ldhc[l]);
            }
        }
    }
    // pièces transversales aux jonctions (différence des intervalles hauts) ; aux bouts de la route (correction après
    // le second contrôle, L2b-13), un élément répété coupé par le bout (profil de la première ou de la dernière section
    // repris plus loin entre deux sections d'un autre profil : avancée de S03 en [0 ; 2,5] et [97,5 ; 100]) a son côté
    // transversal construit contre le profil de la section voisine, supposé continuer au-delà du bout (le tronçon est
    // une coupe d'une rue plus longue) ; jonctions (section avant, section après, abscisse)
    int J_a[], J_b[];
    float J_s[];
    if (ns >= 3) {
        int rep0 = 0, rep1 = 0;
        for (int j = 1; j + 1 < ns; j++) {
            if (SP[j] == SP[0] && SP[j - 1] != SP[j] && SP[j + 1] != SP[j]) rep0 = 1;
            if (SP[j] == SP[ns - 1] && SP[j - 1] != SP[j] && SP[j + 1] != SP[j]) rep1 = 1;
        }
        if (rep0 && SP[1] != SP[0]) { push(J_a, 1); push(J_b, 0); push(J_s, SEC0[0]); }
        for (int k = 0; k + 1 < ns; k++) { push(J_a, k); push(J_b, k + 1); push(J_s, SEC1[k]); }
        if (rep1 && SP[ns - 2] != SP[ns - 1]) { push(J_a, ns - 1); push(J_b, ns - 2); push(J_s, SEC1[ns - 1]); }
    } else {
        for (int k = 0; k + 1 < ns; k++) { push(J_a, k); push(J_b, k + 1); push(J_s, SEC1[k]); }
    }
    for (int jq = 0; jq < len(J_s); jq++) {
        int ka = J_a[jq], kbb = J_b[jq];
        float sj = J_s[jq];
        int ppa = rg_point_profil(1, SP[ka]), ppb = rg_point_profil(1, SP[kbb]);
        int spa = rg_point_section(3, rid, ka), spb = rg_point_section(3, rid, kbb);
        float Ta[], Aa[], Ga[], Pa[], Ha[], Va[], dza, Tb[], Ab[], Gb[], Pb[], Hb[], Vb[], dzb;
        int Ca[], Cb[];
        string msg;
        if (!rg_coupe(1, ppa, 3, spa, 2, rid, sj, rampe, Ta, Aa, Ga, Ca, Pa, Ha, Va, dza, msg)) error("%s", msg);
        if (!rg_coupe(1, ppb, 3, spb, 2, rid, sj, rampe, Tb, Ab, Gb, Cb, Pb, Hb, Vb, dzb, msg)) error("%s", msg);
        // bornes candidates
        float bt[];
        foreach (float x; Ta) push(bt, x);
        foreach (float x; Tb) push(bt, x);
        bt = sort(bt);
        float tmin = max(Ta[-1], Tb[-1]), tmax = min(Ta[0], Tb[0]);
        float seg0[], seg1[];
        int segh[];
        for (int i = 0; i + 1 < len(bt); i++) {
            float lo = bt[i], hi = bt[i + 1];
            if (hi - lo < 1e-6 || lo < tmin - 1e-9 || hi > tmax + 1e-9) continue;
            float tm = 0.5 * (lo + hi);
            int ia = -1, ib = -1;
            for (int b = 0; b + 1 < len(Ta); b++) if (tm <= Ta[b] && tm >= Ta[b + 1]) ia = b;
            for (int b = 0; b + 1 < len(Tb); b++) if (tm <= Tb[b] && tm >= Tb[b + 1]) ib = b;
            if (ia < 0 || ib < 0) continue;
            int ha = Ca[ia], hb_ = Cb[ib];
            if (ha == hb_) continue;
            if (len(seg0) > 0 && abs(seg1[-1] - lo) < 1e-9 && segh[-1] == ha) { seg1[-1] = hi; continue; }
            push(seg0, lo); push(seg1, hi); push(segh, ha);
        }
        for (int q = 0; q < len(seg0); q++) {
            int haut_avant = segh[q];                    // 1 : haut avant la jonction (s < sj)
            float lo = seg0[q], hi = seg1[q];
            int nn = max(1, int(ceil((hi - lo) / pas_t - 1e-9)));
            float tt[];
            for (int i = 0; i <= nn; i++) push(tt, lo + (hi - lo) * i / nn);
            if (!haut_avant) tt = reverse(tt);         // haut après (s > sj) : sens −t ; haut avant : sens +t
            // profil : bordure réelle de la section haute à une extrémité
            int kh = haut_avant ? ka : kbb, kb = haut_avant ? kbb : ka;
            int sph = haut_avant ? spa : spb;
            float Tl[], Al[], Gl[], Tu[], Au[], Gu[], Th[];
            int Cl[], Cu[];
            float dzl;
            if (haut_avant) { Tl = Tb; Al = Ab; Gl = Gb; Cl = Cb; Tu = Ta; Au = Aa; Gu = Ga; Cu = Ca; dzl = dzb; }
            else { Tl = Ta; Al = Aa; Gl = Ga; Cl = Ca; Tu = Tb; Au = Ab; Gu = Gb; Cu = Cb; dzl = dza; }
            Th = Tu;
            float ret[] = point(3, "b_retrait", sph);
            int lbh[] = point(3, "l_bord", sph);
            string lph[] = point(3, "l_prof", sph);
            string lmh[] = point(3, "l_mat", sph);
            float lbs[] = point(3, "l_base", sph);
            float lHh[] = point(3, "l_H", sph);
            string prof = "";
            float base = 0, H = 0;
            string mat = "";
            for (int l = 0; l < len(Th); l++) {
                if (lbh[l] == 1 && (abs(Th[l] - lo) < 1e-6 || abs(Th[l] - hi) < 1e-6)) {
                    prof = lph[l]; base = lbs[l]; H = lHh[l]; mat = lmh[l]; break;
                }
            }
            if (prof == "") error("route %s s=%g : retour de bordure sans bordure voisine", rid, sj);
            push(Q_off, len(P_s));
            push(Q_n, len(tt));
            push(Q_prof, prof); push(Q_cprof, ""); push(Q_mat, mat); push(Q_base, base); push(Q_H, H);
            push(Q_wc, 0.0); push(Q_dhc, 0.0); push(Q_hfe, 0.0);
            foreach (float t; tt) {
                int bl = -1, bu = -1;
                for (int b = 0; b + 1 < len(Tl); b++) if (t <= Tl[b] + 1e-9 && t >= Tl[b + 1] - 1e-9 && Cl[b] == 0) { bl = b; break; }
                for (int b = 0; b + 1 < len(Tu); b++) if (t <= Tu[b] + 1e-9 && t >= Tu[b + 1] - 1e-9 && Cu[b] == 1) { bu = b; break; }
                if (bl < 0 || bu < 0) error("route %s s=%g t=%g : retour de bordure sans bande basse ou haute", rid, sj, t);
                float pied = Al[bl] + Gl[bl] * t;
                float tete = Au[bu] + Gu[bu] * t + ret[bu];
                push(P_s, sj); push(P_t, t);
                push(P_pied, pied); push(P_tete, tete); push(P_vue, tete - pied);
                push(P_zbf, pied + dzl); push(P_zemp, pied - 0.20); push(P_can, 0); push(P_gri, 0);
                push(P_kb, kb); push(P_bb, bl); push(P_kh, kh); push(P_bh, bu);
                push(P_kind, 1); push(P_lim, -1); push(P_sec, kh);
                push(P_wc, 0.0); push(P_dhc, 0.0);
            }
        }
    }
    // chaînage : fin d'une pièce = début d'une autre (même (s, t) à 1e-6 près)
    int nq = len(Q_off);
    int suiv[], prec[];
    resize(suiv, nq); resize(prec, nq);
    for (int i = 0; i < nq; i++) { suiv[i] = -1; prec[i] = -1; }
    for (int i = 0; i < nq; i++) {
        int ie = Q_off[i] + Q_n[i] - 1;
        for (int j = 0; j < nq; j++) {
            if (j == i || prec[j] >= 0) continue;
            int js = Q_off[j];
            if (abs(P_s[ie] - P_s[js]) < 1e-6 && abs(P_t[ie] - P_t[js]) < 1e-6) { suiv[i] = j; prec[j] = i; break; }
        }
    }
    int vu[];
    resize(vu, nq);
    int nchaine = 0;
    for (int pass = 0; pass < 2; pass++) {
        for (int i0 = 0; i0 < nq; i0++) {
            if (vu[i0] || (pass == 0 && prec[i0] >= 0)) continue;
            int ordre[];
            int i = i0;
            while (i >= 0 && !vu[i]) { push(ordre, i); vu[i] = 1; i = suiv[i]; }
            int fermee = (i == i0);
            int pts[];
            foreach (int qi; ordre) {
                for (int m = 0; m < Q_n[qi]; m++) {
                    // point de raccord : gardé pour chaque pièce (deux points confondus) : la vue, le pied et le
                    // caniveau changent à l'angle d'un retour de bordure
                    int o = Q_off[qi] + m;
                    vector2 xy = rg_local_st(0, pr, P_s[o], P_t[o]);
                    int np = addpoint(0, set(xy.x, P_pied[o], -xy.y));
                    setpointattrib(0, "s_ref", np, P_s[o]);
                    setpointattrib(0, "t_ref", np, P_t[o]);
                    setpointattrib(0, "x", np, xy.x);
                    setpointattrib(0, "y", np, xy.y);
                    setpointattrib(0, "pied", np, P_pied[o]);
                    setpointattrib(0, "tete", np, P_tete[o]);
                    setpointattrib(0, "vue", np, P_vue[o]);
                    setpointattrib(0, "zbf", np, P_zbf[o]);
                    setpointattrib(0, "zemp", np, P_zemp[o]);
                    setpointattrib(0, "can", np, P_can[o]);
                    setpointattrib(0, "grille", np, P_gri[o]);
                    setpointattrib(0, "k_bas", np, P_kb[o]);
                    setpointattrib(0, "b_bas", np, P_bb[o]);
                    setpointattrib(0, "k_haut", np, P_kh[o]);
                    setpointattrib(0, "b_haut", np, P_bh[o]);
                    setpointattrib(0, "kind", np, P_kind[o]);
                    setpointattrib(0, "limite", np, P_lim[o]);
                    setpointattrib(0, "section", np, P_sec[o]);
                    setpointattrib(0, "wcp", np, P_wc[o]);
                    setpointattrib(0, "dhcp", np, P_dhc[o]);
                    float xr, yr, thr, kr;
                    if (prim(0, "geometrie_reguliere", pr)) rg_reference(0, pr, P_s[o], xr, yr, thr, kr);
                    else kr = 0.0;
                    setpointattrib(0, "kappa", np, kr);
                    push(pts, np);
                }
            }
            if (fermee && len(pts) > 2) pts = pts[:-1];
            // (fermée : le dernier point double le premier)
            int np = addprim(0, fermee ? "poly" : "polyline", pts);
            setprimgroup(0, "bordures", np, 1);
            setprimattrib(0, "id", np, sprintf("K-%s-%02d", rid, nchaine));
            setprimattrib(0, "route", np, rid);
            setprimattrib(0, "fermee", np, fermee);
            int q0 = ordre[0];
            setprimattrib(0, "profil", np, Q_prof[q0]);
            setprimattrib(0, "base", np, Q_base[q0]);
            setprimattrib(0, "H", np, Q_H[q0]);
            string cp = "";
            float wc = 0, dhc = 0, hfe = 0;
            foreach (int qi; ordre) if (Q_cprof[qi] != "") { cp = Q_cprof[qi]; wc = Q_wc[qi]; dhc = Q_dhc[qi]; hfe = Q_hfe[qi]; }
            setprimattrib(0, "cprof", np, cp);
            setprimattrib(0, "wc", np, wc);
            setprimattrib(0, "dhc", np, dhc);
            setprimattrib(0, "hfe", np, hfe);
            setprimattrib(0, "materiau_id", np, Q_mat[q0]);
            nchaine++;
        }
    }
}
"""


VEX_EMPRISE = r"""
// emprise_hf (détail) : emprise du HeightField de nivellement (profils + abords de toutes les routes, + marge), nœuds
// calés sur les multiples du pas en coordonnées locales. Entrées : 0 niveaux, 1 références.
float pas = chf("../pas_heightfield"), m = chf("../marge_heightfield");
float xmin = 1e18, ymin = 1e18, xmax = -1e18, ymax = -1e18;
for (int pr = 0; pr < nprimitives(1); pr++) {
    if (!inprimgroup(1, "echantillonnees", pr)) continue;
    string rid = prim(1, "id", pr);
    float L = prim(1, "longueur_m", pr);
    float SEC0[] = prim(1, "sec_s0", pr);
    float SEC1[] = prim(1, "sec_s1", pr);
    float S[];
    int rpts[] = primpoints(1, pr);
    foreach (int p; rpts) { float sv = point(1, "s", p); push(S, sv); }
    foreach (float x; SEC0) push(S, x);
    push(S, L);
    for (int k = 0; k < len(SEC0); k++) {
        int sp = rg_point_section(0, rid, k);
        float ag = point(0, "abord_g", sp), ad = point(0, "abord_d", sp);
        foreach (float s; S) {
            if (s < SEC0[k] - 1e-9 || s > SEC1[k] + 1e-9) continue;
            float T[] = rg_t_limites(0, sp, s);
            float tt[] = array(T[0] + ag, T[-1] - ad);
            foreach (float t; tt) {
                vector2 q = rg_local_st(1, pr, s, t);
                xmin = min(xmin, q.x); xmax = max(xmax, q.x);
                ymin = min(ymin, q.y); ymax = max(ymax, q.y);
            }
        }
    }
}
float x0 = floor((xmin - m) / pas) * pas, y0 = floor((ymin - m) / pas) * pas;
int ni = int(rint((ceil((xmax + m) / pas) * pas - x0) / pas)) + 1;
int nj = int(rint((ceil((ymax + m) / pas) * pas - y0) / pas)) + 1;
f@hf_x0 = x0; f@hf_y0 = y0; f@hf_pas = pas;
i@hf_ni = ni; i@hf_nj = nj;
f@hf_sx = ni * pas; f@hf_sz = nj * pas;
f@hf_cx = x0 + 0.5 * (ni - 1) * pas;
f@hf_cz = -(y0 + 0.5 * (nj - 1) * pas);
"""

VEX_COUCHES = r"""
// couches (primitive) : six copies du volume height nommées comme le HeightField du lecteur (README_HDA § 2).
string noms[] = array("height", "r0", "z1", "r1", "z2", "r2");
s@name = noms[@primnum];
"""

VEX_HEIGHTFIELD = r"""
// heightfield (Volume Wrangle) : nœud (x, y) local = (P.x, −P.z) ; route la plus proche dont le domaine (s ∈ [0, L],
// t entre les abords, élargi d'un demi-pas pour que tout point du bord trouve ses nœuds) contient le nœud (|t|
// minimal), sinon région −1 et Z prolongé (affichage). Modèle de Z unique rg_niveau.h (rg_hf_noeud) : height = Z de
// la nappe propriétaire ; z1/r1, z2/r2 : prolongements à moins de deux nœuds des nappes voisines en travers
// (frontières des bordures), puis de la section voisine (jonctions, retours de bordure) si sa nappe diffère.
// Entrées : 0 couches, 1 niveaux, 2 références (Y = 0).
float rampe = detail(1, "rg_rampe_plateau_pct");
float pas = chf("../pas_heightfield");
float dmax = 2.0 * pas + 1e-6;
float x = @P.x, y = -@P.z;
float best = 1e30;
float hz = 0.0, hz1 = 0.0, hz2 = 0.0;
int hr = -1, hr1 = -1, hr2 = -1;
int rang = 0;
for (int pr = 0; pr < nprimitives(2); pr++) {
    if (!inprimgroup(2, "echantillonnees", pr)) continue;
    string rid = prim(2, "id", pr);
    float s, t;
    float ecart = rg_st_local(2, pr, x, y, s, t);
    float SEC0[] = prim(2, "sec_s0", pr);
    int k = rg_indice_section(SEC0, s);
    int sp = rg_point_section(1, rid, k);
    float T[] = rg_t_limites(1, sp, s);
    float ag = point(1, "abord_g", sp), ad = point(1, "abord_d", sp);
    float e = (ecart > 1e-4 ? ecart : 0.0) + max(0.0, max(t - (T[0] + ag), (T[-1] - ad) - t));
    float cle = e * 1e6 + abs(t);
    if (cle < best) {
        float z0, z1, z2;
        int n0, n1, n2;
        string msg;
        if (!rg_hf_noeud(1, sp, rid, s, t, rampe, dmax, z0, n0, z1, n1, z2, n2, msg)) error("%s", msg);
        // section voisine à moins de deux nœuds : sa nappe en t, si elle diffère, dans un prolongement libre
        float SEC1[] = prim(2, "sec_s1", pr);
        int kv[];
        if (k > 0 && s - SEC0[k] <= dmax) push(kv, k - 1);
        if (k + 1 < len(SEC0) && SEC1[k] - s <= dmax) push(kv, k + 1);
        foreach (int ko; kv) {
            int spo = rg_point_section(1, rid, ko);
            float w0, w1, w2;
            int m0, m1, m2;
            if (!rg_hf_noeud(1, spo, rid, s, t, rampe, 0.0, w0, m0, w1, m1, w2, m2, msg)) error("%s", msg);
            if (m0 == n0 || m0 == n1 || m0 == n2) continue;
            if (n1 < 0) { n1 = m0; z1 = w0; }
            else if (n2 < 0) { n2 = m0; z2 = w0; }
        }
        best = cle;
        int dedans = e <= 0.5 * pas + 1e-9;
        hz = z0; hr = dedans ? 100 * rang + n0 : -1;
        hz1 = (dedans && n1 >= 0) ? z1 : 0.0; hr1 = (dedans && n1 >= 0) ? 100 * rang + n1 : -1;
        hz2 = (dedans && n2 >= 0) ? z2 : 0.0; hr2 = (dedans && n2 >= 0) ? 100 * rang + n2 : -1;
    }
    rang++;
}
f@height = hz;
f@r0 = hr;
f@z1 = hz1;
f@r1 = hr1;
f@z2 = hz2;
f@r2 = hr2;
"""

VEX_DESCRIPTEUR = r"""
// descripteur (détail) : attributs du lecteur (README_HDA § 2) ; contrôle du rangement (axe 0 -> Z monde croissant,
// axe 1 -> X monde, voxel (nj − 1 − j, i)) et de la résolution contre l'emprise. Entrées : 0 couches, 1 emprise,
// 2 références.
float pas = detail(1, "hf_pas"), x0 = detail(1, "hf_x0"), y0 = detail(1, "hf_y0");
int ni = detail(1, "hf_ni"), nj = detail(1, "hf_nj");
vector r = volumeres(0, "height");
if (int(r.x) != nj || int(r.y) != ni) error("HeightField : résolution %g x %g, attendue %d x %d", r.x, r.y, nj, ni);
vector o = volumeindextopos(0, "height", set(nj - 1, 0, 0));
vector a0 = volumeindextopos(0, "height", set(1, 0, 0)) - volumeindextopos(0, "height", set(0, 0, 0));
vector a1 = volumeindextopos(0, "height", set(0, 1, 0)) - volumeindextopos(0, "height", set(0, 0, 0));
if (abs(o.x - x0) > 1e-3 || abs(-o.z - y0) > 1e-3 || abs(a0.z - pas) > 1e-5 || abs(a1.x - pas) > 1e-5)
    error("HeightField : rangement inattendu (origine %g %g, axes %g %g)", o.x, -o.z, a0.z, a1.x);
f@niv_x0 = x0;
f@niv_y0 = y0;
f@niv_pas = pas;
i@niv_ni = ni;
i@niv_nj = nj;
i@niv_i0 = 0;
i@niv_j0 = 0;
i@niv_sous_ech = 1;
s@niv_hash = "rg::nivellement";
string routes[];
for (int pr = 0; pr < nprimitives(2); pr++) if (inprimgroup(2, "echantillonnees", pr)) { string rid = prim(2, "id", pr); push(routes, rid); }
s[]@niv_routes = routes;
"""


def parametres():
    T = hou
    d = regles.valeur("DEF-034")
    return [
        T.FloatParmTemplate("rampe_plateau_pct", "Rampe des plateaux (%) si rg::graphe ne la donne pas", 1,
                            default_value=(float(d["rampe_pct"]),), min=1.0, max=20.0,
                            help="DEF-034 ; d'ordinaire lue sur le détail rg_rampe_plateau_pct de l'entrée 1."),
        T.FloatParmTemplate("pas_transversal", "Pas des retours de bordure (m)", 1, default_value=(0.25,), min=0.05,
                            max=2.0, help="Échantillonnage des retours de bordure (pied, tête) le long de t."),
        T.FloatParmTemplate("pas_heightfield", "Pas du HeightField (m)", 1, default_value=(0.10,), min=0.02, max=1.0,
                            help="README_HDA § 2 : HeightField de nivellement au pas de 0,10 m."),
        T.FloatParmTemplate("marge_heightfield", "Marge du HeightField (m)", 1, default_value=(1.0,), min=0.0,
                            max=20.0, help="Marge autour des profils et des abords."),
    ]


def construire(dossier=ICI):
    sub = R.sous_reseau("rg_" + NOM)
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres()))
    e1, e2, e3, e4 = sub.indirectInputs()[:4]
    libs = ("rg_geometrie.h", "rg_niveau.h")
    sec = R.wrangle(sub, "sections", vex_table() + VEX_SECTIONS, "detail", None, entrees=(e2, e3),
                    bibliotheques=libs)
    sec.setInput(0, e1)
    gs = sub.createNode("blast", "garder_sections")
    gs.setInput(0, sec)
    gs.parm("group").set("sections ralentisseurs")
    gs.parm("grouptype").set("points")
    gs.parm("negate").set(1)
    ab = R.wrangle(sub, "abords", VEX_ABORDS, "point", gs, entrees=(e4,))
    ab.parm("group").set("sections")
    bor = R.wrangle(sub, "bordures", vex_table() + VEX_BORDURES, "detail", e1, entrees=(e2, e3, ab),
                    bibliotheques=libs)
    gb = sub.createNode("blast", "garder_bordures")
    gb.setInput(0, bor)
    gb.parm("group").set("bordures")
    gb.parm("grouptype").set("prims")
    gb.parm("negate").set(1)
    fus = sub.createNode("merge", "fusion")
    fus.setInput(0, ab)
    fus.setInput(1, gb)
    out = sub.createNode("null", "NIVEAUX")
    out.setInput(0, fus)
    R.sortie(sub, out, 0, "sortie_niveaux")
    out.setDisplayFlag(True)
    # ---- HeightField de nivellement (sortie 2) : même modèle de Z, évalué aux nœuds
    emp = R.wrangle(sub, "emprise_hf", VEX_EMPRISE, "detail", out, entrees=(e1,), bibliotheques=libs)
    hf = sub.createNode("heightfield", "grille")
    hf.parm("gridspacing").setExpression('detail("../emprise_hf", "hf_pas", 0)')
    for p, a in (("sizex", "hf_sx"), ("sizey", "hf_sz"), ("tx", "hf_cx"), ("tz", "hf_cz")):
        hf.parm(p).setExpression(f'detail("../emprise_hf", "{a}", 0)')
    hfh = sub.createNode("blast", "garder_height")
    hfh.setInput(0, hf)
    hfh.parm("group").set("@name=height")
    hfh.parm("grouptype").set("prims")
    hfh.parm("negate").set(1)
    six = sub.createNode("merge", "six_couches")
    for k in range(6):
        six.setInput(k, hfh)
    cou = R.wrangle(sub, "couches", VEX_COUCHES, "primitive", six)
    plat = R.wrangle(sub, "references_plates", "@P.y = 0;", "point", e1)
    vw = sub.createNode("volumewrangle", "heightfield")
    vw.parm("snippet").set(R.vex(*libs) + VEX_HEIGHTFIELD)
    vw.parm("vex_precision").set("64")
    vw.setInput(0, cou)
    vw.setInput(1, out)
    vw.setInput(2, plat)
    desc = R.wrangle(sub, "descripteur", VEX_DESCRIPTEUR, "detail", vw, entrees=(emp, plat))
    hout = sub.createNode("null", "NIVELLEMENT")
    hout.setInput(0, desc)
    R.sortie(sub, hout, 1, "sortie_heightfield")
    R.ranger(sub)
    aide = ("Modèle de nivellement analytique unique (TQ-SOL-013) : tables par section (bandes hautes et basses, "
            "bordures réelles et virtuelles, caniveaux, abaissés, ralentisseurs, abords) et files de bordures chaînées "
            "en (s, t) avec pied, tête, vue et chaussée au droit de la face.")
    details = ("== Entrées ==\n\n1. Références échantillonnées (rg::graphe), 2. Profils, 3. Ponctuels, 4. Zones "
               "(rg::lire_modele, sorties 5, 4 et 3).\n\n== Sortie ==\n\nGroupe sections (un point par section : "
               "b_*, l_*, a_*, r_*, abords) et groupe bordures (polylignes en coordonnées Houdini au pied, côté haut à "
               "gauche ; points s_ref, t_ref, pied, tete, vue, zbf, zemp, can, grille, k_bas, b_bas, kind).\n\n"
               "Sortie 2 : HeightField au pas de 0,10 m rangé comme celui de pj::lire_description (height, r0, z1, r1, "
               "z2, r2 ; détail niv_x0, niv_y0, niv_pas, niv_ni, niv_nj) : région = 100 x rang de la route + nappe "
               "(nappe 0 à gauche, frontière au milieu du corps de bordure) ; Z lu par pj_niv_z.\n\n"
               "Retours de bordure : aux jonctions de sections (différence des intervalles hauts) et, aux bouts de la route, "
               "pour un élément répété coupé par le bout (avancée en [0 ; 2,5] de S03 : retour contre le profil de la "
               "section voisine, supposé continuer au-delà du bout).\n\n"
               "Règles : TQ-SOL-013, TQ-BOR-007, DEF-005, DEF-006, DEF-031, DEF-034, RF-MA-ABA-004, RF-GV-RAL-002.")
    return R.creer_hda(sub, NOM, "RG Nivellement (modèle de Z unique)", parametres(), dossier, entrees=(4, 4),
                       sorties=2, aide=aide, details_aide=details, icone="SOP_heightfield",
                       etiquettes_entrees=("Références échantillonnées", "Profils", "Ponctuels", "Zones"),
                       etiquettes_sorties=("Niveaux (sections, bordures)", "HeightField de nivellement"))


if __name__ == "__main__":
    print(construire())
