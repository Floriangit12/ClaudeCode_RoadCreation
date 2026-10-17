"""Construit l'HDA rg::profils::1.0 (limites décalées, rubans de bandes, profils d'extrémité, loi verticale) ;
hython Houdini 22.

    hython recon/generateur/hda/rg_profils/construire.py

Réseau (recon/generateur/hda/README_RG.md § 4) :
    entrée 1 références échantillonnées (rg::graphe), 2 profils, 3 ponctuels (rg::lire_modele)
      -> derouler (VEX 64 bits, détail) -> retirer_references (Blast) -> controles (VEX, détail)
      -> LIMITES / BANDES / EXTREMITES / PROFIL_LONG (Blast par groupe)
Pour chaque section [s0, s1] d'une route et chaque échantillon s de la référence (les échantillons aux bornes sont
dédoublés : chaque section a les siens), la limite i du profil est posée en P(s) + t_i(s) · gauche(s), avec
t_r = −reference.decalage_m pour la limite de référence r et t_i = cumul des largeurs w_b(s) (lois de s du modèle).
Transitions de profil : élargissement et rabattement par les lois de largeur des sections (continuité contrôlée aux
jonctions, sauf « transition_entree : instantanee » déclarée par le modèle) ; plateau et dos-d'âne par la loi
verticale dz_chaussee(s) (profil en long de la chaussée, rampe DEF-034, dos-d'âne circulaire RF-MA-RAL-001).
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "commun"))
import rg_hda_outils as R  # noqa: E402

NOM = "profils"

VEX_DEROULER = r"""
// Déroulement des profils le long des références échantillonnées (rg::profils, lot L1).
// Entrées : 0 références (rg::graphe), 1 profils, 2 ponctuels.
float rampe = detail(0, "rg_rampe_plateau_pct");
if (rampe <= 0.0) rampe = chf("../rampe_plateau_pct");
float tol = chf("../tolerance_continuite");

addpointattrib(0, "t", 0.0);
addpointattrib(0, "dz_chaussee", 0.0);
addpointattrib(0, "limite", -1);
addpointattrib(0, "section", -1);
string attr_s[] = array("route", "section_profil", "profil", "cle", "bande_gauche", "bande_droite", "nature",
                        "bordure", "vue_loi", "cote_haut", "caniveau", "marquages", "separateur", "limite_json",
                        "bande", "type", "sous_type", "sens", "materiau_id", "niv_reference", "niv_forme",
                        "bande_json", "extremite", "noeud", "transition_entree");
foreach (string a; attr_s) addprimattrib(0, a, "");
string attr_i[] = array("section", "limite", "rang", "est_reference", "n_points");
foreach (string a; attr_i) addprimattrib(0, a, -1);
string attr_f[] = array("vue_m", "niv_dz", "niv_devers", "s0", "s1", "largeur_min_m", "largeur_max_m");
foreach (string a; attr_f) addprimattrib(0, a, 0.0);

int n_sections = 0, n_limites = 0, n_rubans = 0, n_neg = 0, n_nulles = 0, n_biseaux = 0, n_replis = 0, n_trous = 0;
float wmin = 1e9;
string J_route[];
float J_s[];
float J_ecart[];
int J_inst[];
string J_detail[];

for (int pr = 0; pr < nprimitives(0); pr++) {
    if (!inprimgroup(0, "echantillonnees", pr)) continue;
    string rid = prim(0, "id", pr);
    string nd = prim(0, "noeud_debut", pr);
    string nf = prim(0, "noeud_fin", pr);
    float L = prim(0, "longueur_m", pr);
    float SEC0[] = prim(0, "sec_s0", pr);
    float SEC1[] = prim(0, "sec_s1", pr);
    string SP[] = prim(0, "sec_profil", pr);
    string ST[] = prim(0, "sec_transition", pr);
    int pts[] = primpoints(0, pr);
    float S[];
    vector P[];
    vector G[];
    float K[];
    foreach (int p; pts) {
        float sv = point(0, "s", p);
        vector pv = point(0, "P", p);
        vector gv = point(0, "gauche", p);
        float kv = point(0, "courbure", p);
        push(S, sv);
        push(P, pv);
        push(G, gv);
        push(K, kv);
    }
    // sections contiguës de 0 à L
    if (abs(SEC0[0]) > 1e-6 || abs(SEC1[-1] - L) > 1e-6) n_trous++;
    for (int k = 1; k < len(SEC0); k++) if (abs(SEC0[k] - SEC1[k - 1]) > 1e-6) n_trous++;

    // profil en long de la chaussée (loi verticale des ralentisseurs)
    float DZ[];
    int plg[];
    for (int j = 0; j < len(S); j++) {
        float d2;
        float dz = rg_dz_chaussee(2, rid, S[j], rampe, d2);
        push(DZ, dz);
        int p = addpoint(0, P[j] + set(0, dz, 0));
        setpointattrib(0, "s", p, S[j]);
        setpointattrib(0, "dz_chaussee", p, dz);
        setpointattrib(0, "route", p, rid);
        push(plg, p);
    }
    int ppl = addprim(0, "polyline", plg);
    setprimattrib(0, "route", ppl, rid);
    setprimgroup(0, "profil_long", ppl, 1);

    float Tprec[];
    string Bprec[];
    float sprec = -1.0;
    int LPdeb[];
    int LPfin[];
    for (int k = 0; k < len(SEC0); k++) {
        int pp = rg_point_profil(1, SP[k]);
        if (pp < 0) error("route %s : profil %s absent", rid, SP[k]);
        int nb = point(1, "n_bandes", pp);
        int nl = nb + 1;
        int rref = point(1, "ref_limite", pp);
        string bid[] = point(1, "bande_id", pp);
        int J[];
        for (int j = 0; j < len(S); j++)
            if (S[j] >= SEC0[k] - 1e-7 && S[j] <= SEC1[k] + 1e-7) push(J, j);
        int ns = len(J);
        if (ns < 2) error("route %s section %d : moins de deux échantillons", rid, k);
        n_sections++;
        float TT[];
        for (int q = 0; q < ns; q++) {
            float tq[] = rg_t_limites(1, pp, S[J[q]]);
            foreach (float x; tq) push(TT, x);
            for (int b = 0; b < nb; b++) {
                float w = tq[b] - tq[b + 1];
                wmin = min(wmin, w);
                if (w < -1e-9) n_neg++;
                else if (w <= 1e-6) {
                    if (q == 0 || q == ns - 1) n_biseaux++;
                    else n_nulles++;
                }
            }
            for (int l = 0; l < nl; l++) if (1.0 - tq[l] * K[J[q]] <= 0.0) n_replis++;
        }
        // continuité à la jonction avec la section précédente (mêmes bandes : mêmes bords ; bande nouvelle ou
        // disparue : largeur nulle à la jonction)
        if (k > 0) {
            float t0[];
            for (int l = 0; l < nl; l++) push(t0, TT[l]);
            float ec = 0.0;
            string det = "";
            for (int b = 0; b < nb; b++) {
                int i = find(Bprec, bid[b]);
                float e = (i >= 0) ? max(abs(Tprec[i] - t0[b]), abs(Tprec[i + 1] - t0[b + 1])) : abs(t0[b] - t0[b + 1]);
                if (e > ec) { ec = e; det = bid[b]; }
            }
            for (int i = 0; i < len(Bprec); i++) {
                if (find(bid, Bprec[i]) < 0) {
                    float e = abs(Tprec[i] - Tprec[i + 1]);
                    if (e > ec) { ec = e; det = Bprec[i]; }
                }
            }
            push(J_route, rid);
            push(J_s, SEC0[k]);
            push(J_ecart, ec);
            push(J_inst, ST[k] == "instantanee");
            push(J_detail, det);
        }
        // points des limites (partagés par les polylignes et les rubans)
        int LP[];
        resize(LP, nl * ns);
        for (int q = 0; q < ns; q++) {
            int j = J[q];
            for (int l = 0; l < nl; l++) {
                float t = TT[q * nl + l];
                int p = addpoint(0, P[j] + t * G[j]);
                setpointattrib(0, "s", p, S[j]);
                setpointattrib(0, "t", p, t);
                setpointattrib(0, "dz_chaussee", p, DZ[j]);
                setpointattrib(0, "limite", p, l);
                setpointattrib(0, "section", p, k);
                setpointattrib(0, "route", p, rid);
                LP[l * ns + q] = p;
            }
        }
        string nat[] = point(1, "lim_nature", pp);
        string bor[] = point(1, "lim_bordure", pp);
        float vue[] = point(1, "lim_vue", pp);
        string vloi[] = point(1, "lim_vue_loi", pp);
        string ch[] = point(1, "lim_cote_haut", pp);
        string can[] = point(1, "lim_caniveau", pp);
        string mq[] = point(1, "lim_marquages", pp);
        string sep[] = point(1, "lim_separateur", pp);
        string lj[] = point(1, "lim_json", pp);
        for (int l = 0; l < nl; l++) {
            int lp[];
            for (int q = 0; q < ns; q++) push(lp, LP[l * ns + q]);
            int np = addprim(0, "polyline", lp);
            setprimgroup(0, "limites", np, 1);
            string bg = l > 0 ? bid[l - 1] : "";
            string bd = l < nb ? bid[l] : "";
            setprimattrib(0, "route", np, rid);
            setprimattrib(0, "section", np, k);
            setprimattrib(0, "profil", np, SP[k]);
            setprimattrib(0, "limite", np, l);
            setprimattrib(0, "cle", np, bg + "|" + bd);
            setprimattrib(0, "bande_gauche", np, bg);
            setprimattrib(0, "bande_droite", np, bd);
            setprimattrib(0, "est_reference", np, l == rref);
            setprimattrib(0, "nature", np, nat[l]);
            setprimattrib(0, "bordure", np, bor[l]);
            setprimattrib(0, "vue_m", np, vue[l]);
            setprimattrib(0, "vue_loi", np, vloi[l]);
            setprimattrib(0, "cote_haut", np, ch[l]);
            setprimattrib(0, "caniveau", np, can[l]);
            setprimattrib(0, "marquages", np, mq[l]);
            setprimattrib(0, "separateur", np, sep[l]);
            setprimattrib(0, "limite_json", np, lj[l]);
            setprimattrib(0, "s0", np, SEC0[k]);
            setprimattrib(0, "s1", np, SEC1[k]);
            setprimattrib(0, "n_points", np, ns);
            setprimattrib(0, "transition_entree", np, ST[k]);
            n_limites++;
        }
        // rubans des bandes : quadrilatères entre les limites b et b + 1 (normale +Y)
        string bty[] = point(1, "bande_type", pp);
        string bst[] = point(1, "bande_sous_type", pp);
        string bse[] = point(1, "bande_sens", pp);
        string bma[] = point(1, "bande_materiau", pp);
        string nre[] = point(1, "niv_reference", pp);
        string nfo[] = point(1, "niv_forme", pp);
        float ndz[] = point(1, "niv_dz", pp);
        float ndv[] = point(1, "niv_devers", pp);
        string bjs[] = point(1, "bande_json", pp);
        for (int b = 0; b < nb; b++) {
            float w0 = 1e9, w1 = -1e9;
            for (int q = 0; q < ns; q++) {
                float w = TT[q * nl + b] - TT[q * nl + b + 1];
                w0 = min(w0, w);
                w1 = max(w1, w);
            }
            for (int q = 0; q < ns - 1; q++) {
                int quad[] = array(LP[b * ns + q], LP[b * ns + q + 1], LP[(b + 1) * ns + q + 1], LP[(b + 1) * ns + q]);
                int np = addprim(0, "poly", quad);
                setprimgroup(0, "bandes", np, 1);
                setprimattrib(0, "route", np, rid);
                setprimattrib(0, "section", np, k);
                setprimattrib(0, "profil", np, SP[k]);
                setprimattrib(0, "rang", np, b);
                setprimattrib(0, "bande", np, bid[b]);
                setprimattrib(0, "type", np, bty[b]);
                setprimattrib(0, "sous_type", np, bst[b]);
                setprimattrib(0, "sens", np, bse[b]);
                setprimattrib(0, "materiau_id", np, bma[b]);
                setprimattrib(0, "niv_reference", np, nre[b]);
                setprimattrib(0, "niv_forme", np, nfo[b]);
                setprimattrib(0, "niv_dz", np, ndz[b]);
                setprimattrib(0, "niv_devers", np, ndv[b]);
                setprimattrib(0, "bande_json", np, bjs[b]);
                setprimattrib(0, "largeur_min_m", np, w0);
                setprimattrib(0, "largeur_max_m", np, w1);
                setprimattrib(0, "s0", np, SEC0[k]);
                setprimattrib(0, "s1", np, SEC1[k]);
                n_rubans++;
            }
        }
        if (k == 0) for (int l = 0; l < nl; l++) push(LPdeb, LP[l * ns]);
        if (k == len(SEC0) - 1) for (int l = 0; l < nl; l++) push(LPfin, LP[l * ns + ns - 1]);
        resize(Tprec, 0);
        for (int l = 0; l < nl; l++) push(Tprec, TT[(ns - 1) * nl + l]);
        Bprec = bid;
    }
    // profils d'extrémité (coupe transversale de gauche à droite en s = 0 et s = L : frontière des carrefours)
    int e0 = addprim(0, "polyline", LPdeb);
    setprimattrib(0, "route", e0, rid);
    setprimattrib(0, "extremite", e0, "debut");
    setprimattrib(0, "noeud", e0, nd);
    setprimgroup(0, "extremites", e0, 1);
    int e1 = addprim(0, "polyline", LPfin);
    setprimattrib(0, "route", e1, rid);
    setprimattrib(0, "extremite", e1, "fin");
    setprimattrib(0, "noeud", e1, nf);
    setprimgroup(0, "extremites", e1, 1);
}
int n_disc = 0;
float ecmax = 0.0;
for (int i = 0; i < len(J_ecart); i++) {
    if (!J_inst[i]) {
        ecmax = max(ecmax, J_ecart[i]);
        if (J_ecart[i] > tol) n_disc++;
    }
}
setdetailattrib(0, "rg_n_sections", n_sections);
setdetailattrib(0, "rg_n_limites", n_limites);
setdetailattrib(0, "rg_n_rubans", n_rubans);
setdetailattrib(0, "rg_largeur_min_m", wmin);
setdetailattrib(0, "rg_largeurs_negatives", n_neg);
setdetailattrib(0, "rg_largeurs_nulles_hors_biseau", n_nulles);
setdetailattrib(0, "rg_extremites_de_biseau", n_biseaux);
setdetailattrib(0, "rg_replis", n_replis);
setdetailattrib(0, "rg_sections_non_contigues", n_trous);
setdetailattrib(0, "rg_jonctions_discontinues", n_disc);
setdetailattrib(0, "rg_jonction_ecart_max_m", ecmax);
setdetailattrib(0, "rg_jonction_route", J_route);
setdetailattrib(0, "rg_jonction_s", J_s);
setdetailattrib(0, "rg_jonction_ecart_m", J_ecart);
setdetailattrib(0, "rg_jonction_instantanee", J_inst);
setdetailattrib(0, "rg_jonction_bande", J_detail);
setdetailattrib(0, "rg_tolerance_continuite_m", tol);
"""


def parametres():
    T = hou
    return [
        T.FloatParmTemplate("tolerance_continuite", "Tolérance de continuité (m)", 1, default_value=(0.001,), min=0.0,
                            max=0.1, help="Écart maximal des bords d'une même bande de part et d'autre d'une jonction "
                                          "de sections (critère du lot L1 : 1 mm). Les jonctions déclarées "
                                          "« instantanee » par le modèle sont comptées à part."),
        T.FloatParmTemplate("rampe_plateau_pct", "Rampe des plateaux (%) si rg::graphe ne la donne pas", 1,
                            default_value=(7.0,), min=1.0, max=20.0,
                            help="DEF-034 ; d'ordinaire lue sur le détail rg_rampe_plateau_pct de l'entrée 1."),
    ]


def construire(dossier=ICI):
    sub = R.sous_reseau("rg_" + NOM)
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres()))
    e1, e2, e3 = sub.indirectInputs()[:3]
    der = R.wrangle(sub, "derouler", VEX_DEROULER, "detail", e1, entrees=(e2, e3), bibliotheques=("rg_geometrie.h",))
    ret = sub.createNode("blast", "retirer_references")
    ret.setInput(0, der)
    ret.parm("group").set("echantillonnees")
    ret.parm("grouptype").set("prims")
    nuls = []
    for k, (g, nom) in enumerate((("limites", "LIMITES"), ("bandes", "BANDES"), ("extremites", "EXTREMITES"),
                                   ("profil_long", "PROFIL_LONG"))):
        b = sub.createNode("blast", "garder_" + g)
        b.setInput(0, ret)
        b.parm("group").set(g)
        b.parm("grouptype").set("prims")
        b.parm("negate").set(1)
        n = sub.createNode("null", nom)
        n.setInput(0, b)
        R.sortie(sub, n, k, "sortie_" + g)
        nuls.append(n)
    for n in nuls:
        n.setDisplayFlag(False)
    nuls[1].setDisplayFlag(True)
    R.ranger(sub)
    aide = ("Profils en travers déroulés le long des références : une polyligne par limite et par section (décalage "
            "t(s) = cumul des lois de largeur), rubans de bandes, profils d'extrémité et profil en long de la "
            "chaussée (plateaux, dos-d'âne) ; contrôles de largeur, de repli et de continuité aux jonctions.")
    details = ("== Entrées ==\n\n1. Références échantillonnées (rg::graphe, sortie 1), 2. Profils, 3. Ponctuels "
               "(rg::lire_modele, sorties 5 et 4).\n\n== Sorties ==\n\n"
               "1. Limites : polylignes ; primitives route, section, profil, limite, cle (bande gauche|droite), "
               "nature, bordure, vue_m, cote_haut, caniveau, marquages (JSON), separateur, limite_json, "
               "est_reference, transition_entree ; points s, t, dz_chaussee.\n"
               "2. Bandes : quadrilatères (normale +Y) ; bande, type, sens, materiau_id, niv_*, largeur_min_m, "
               "largeur_max_m, bande_json.\n3. Profils d'extrémité : coupes en s = 0 et s = L (route, extremite, "
               "noeud).\n4. Profil en long : polyligne (x, dz, −y) de la chaussée.\n\n"
               "Détail : rg_largeur_min_m, rg_largeurs_negatives, rg_largeurs_nulles_hors_biseau, "
               "rg_extremites_de_biseau, rg_replis, rg_sections_non_contigues, rg_jonction_* (écarts aux jonctions, "
               "jonctions instantanées déclarées).")
    return R.creer_hda(sub, NOM, "RG Profils (limites, bandes, transitions)", parametres(), dossier, entrees=(3, 3),
                       sorties=4, aide=aide, details_aide=details, icone="SOP_polyexpand2d",
                       etiquettes_entrees=("Références échantillonnées", "Profils", "Ponctuels"),
                       etiquettes_sorties=("Limites", "Bandes (rubans)", "Profils d'extrémité", "Profil en long"))


if __name__ == "__main__":
    print(construire())
