"""Construit l'HDA rg::graphe::1.0 (échantillonnage des lignes de référence, branches aux nœuds) ; hython Houdini 22.

    hython recon/generateur/hda/rg_graphe/construire.py

Réseau (recon/generateur/hda/README_RG.md § 3) :
    entrée 1 routes, 2 profils, 3 ponctuels (rg::lire_modele)
      -> echantillonner (VEX 64 bits, détail) -> garder (Blast des polylignes du modèle)
      -> attributs_route (Attribute Copy, par id) -> REFERENCES
    entrée 4 nœuds -> branches (VEX, entrée 2 : REFERENCES) -> NOEUDS
Échantillonnage (PLAN_GENERATEUR § 2.3) : sommets obligatoires aux raccords des primitives, aux bornes des sections,
aux points des lois de largeur, aux évènements des limites (abaissés, intervalles et interruptions de marquage) et
aux bornes des ralentisseurs ; entre deux sommets obligatoires, pas uniforme h = min(pas_max, √(8 f / B)), B majorant
de |P''| sur toutes les limites décalées de l'intervalle (et de |dz''| de la loi verticale), f = flèche maximale ×
marge. Pour un arc de rayon R et une limite à t : B = (1 + |t|/R)/R, soit h = √(8 f R²/(R + |t|)).
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "commun"))
sys.path.insert(0, str(ICI.parents[1]))                  # recon/generateur : regles.py
import rg_hda_outils as R  # noqa: E402
import regles  # noqa: E402

NOM = "graphe"

VEX_ECHANTILLONNER = r"""
// Échantillonnage des lignes de référence à flèche ≤ f sur toutes les limites décalées (rg::graphe, lot L1).
// Entrées : 0 routes, 1 profils, 2 ponctuels. Sortie : une polyligne par route (groupe echantillonnees), points
// s, cap_rad, courbure, T, gauche (normale à gauche ; onglet aux sommets d'une polyligne), obligatoire, route.
float f = chf("../fleche_max") * chf("../marge_fleche");
float pas_max = chf("../pas_max");
float rampe = chf("../rampe_plateau_pct");
int avec_evts = chi("../sommets_evenements");

addpointattrib(0, "s", 0.0);
addpointattrib(0, "cap_rad", 0.0);
addpointattrib(0, "courbure", 0.0);
addpointattrib(0, "T", {0, 0, 0}, "vector");
addpointattrib(0, "gauche", {0, 0, 0}, "vector");
addpointattrib(0, "obligatoire", 0);
addpointattrib(0, "route", "");
addprimattrib(0, "n_echantillons", 0);
addprimattrib(0, "n_obligatoires", 0);
addprimattrib(0, "pas_min_m", 0.0);
addprimattrib(0, "fleche_majorant_m", 0.0);
addprimattrib(0, "longueur_polyligne_m", 0.0);

int nr = nprimitives(0);
for (int pr = 0; pr < nr; pr++) {
    if (!inprimgroup(0, "routes", pr)) continue;
    string rid = prim(0, "id", pr);
    int reg = prim(0, "geometrie_reguliere", pr);
    float L = prim(0, "longueur_m", pr);
    float SEC0[] = prim(0, "sec_s0", pr);
    float SEC1[] = prim(0, "sec_s1", pr);
    string SP[] = prim(0, "sec_profil", pr);
    if (len(SEC0) == 0) error("route %s : aucune section", rid);

    // polyligne du modèle (routes sans géométrie régulière : droites par sommets, abscisse cumulée)
    int vp[] = primpoints(0, pr);
    vector VP[];
    float VS[];
    float acc = 0.0;
    for (int j = 0; j < len(vp); j++) {
        vector q = point(0, "P", vp[j]);
        if (j > 0) {
            vector a = VP[-1];
            float dl = length(set(q.x - a.x, 0, q.z - a.z));
            if (dl < 1e-9) continue;
            acc += dl;
        }
        push(VP, q);
        push(VS, acc);
    }
    if (L <= 0.0) L = reg ? 0.0 : acc;
    if (reg && L <= 0.0) {
        float GL[] = prim(0, "geo_longueur", pr);
        foreach (float x; GL) L += x;
    }

    // sommets obligatoires
    float B[] = array(0.0, L);
    if (reg) {
        float GS0[] = prim(0, "geo_s0", pr);
        foreach (float x; GS0) push(B, x);
    } else {
        foreach (float x; VS) push(B, x * (L / max(acc, 1e-9)));
    }
    for (int k = 0; k < len(SEC0); k++) {
        push(B, SEC0[k]);
        push(B, SEC1[k]);
        int pp = rg_point_profil(1, SP[k]);
        if (pp < 0) error("route %s : profil %s absent de l'entrée 2", rid, SP[k]);
        int lt[] = point(1, "larg_type", pp);
        float LS[] = point(1, "larg_s", pp);
        foreach (float x; LS) if (x > SEC0[k] && x < SEC1[k]) push(B, x);
        if (avec_evts) {
            float E[] = point(1, "evts_s", pp);
            foreach (float x; E) if (x > SEC0[k] && x < SEC1[k]) push(B, x);
        }
    }
    float VB[] = rg_bornes_verticales(2, rid, rampe);
    foreach (float x; VB) if (x > 0.0 && x < L) push(B, x);
    B = sort(B);
    float U[];
    foreach (float x; B) {
        float y = clamp(x, 0.0, L);
        if (len(U) == 0 || y - U[-1] > 1e-6) push(U, y);
    }
    if (L - U[-1] > 1e-9) push(U, L);

    // pas entre sommets obligatoires
    float S[];
    int OB[];
    float pas_min = 1e9;
    float fmaj = 0.0;
    for (int i = 0; i < len(U) - 1; i++) {
        float a = U[i];
        float b = U[i + 1];
        float dl = b - a;
        push(S, a);
        push(OB, 1);
        float km = 0.0;
        float kp = 0.0;
        if (reg) {
            int T[] = prim(0, "geo_type", pr);
            float GS0[] = prim(0, "geo_s0", pr);
            float K0[] = prim(0, "geo_k0", pr);
            float K1[] = prim(0, "geo_k1", pr);
            float GL[] = prim(0, "geo_longueur", pr);
            int g = rg_indice_primitive(GS0, 0.5 * (a + b));
            float c = (T[g] == 2) ? (K1[g] - K0[g]) / GL[g] : 0.0;
            float ka = K0[g] + c * (a - GS0[g]);
            float kb = K0[g] + c * (b - GS0[g]);
            km = max(abs(ka), abs(kb));
            kp = abs(c);
        }
        int sec = rg_indice_section(SEC0, 0.5 * (a + b));
        int pp = rg_point_profil(1, SP[sec]);
        int m = 4;
        float d = dl / m;
        float TT[];
        int nl = 0;
        for (int j = 0; j <= m; j++) {
            float tj[] = rg_t_limites(1, pp, a + j * d);
            nl = len(tj);
            foreach (float x; tj) push(TT, x);
        }
        float Bn = km;
        for (int l = 0; l < nl; l++) {
            float tmax = 0.0;
            float tp = 0.0;
            float tpp = 0.0;
            for (int j = 0; j <= m; j++) {
                tmax = max(tmax, abs(TT[j * nl + l]));
                if (j > 0) tp = max(tp, abs(TT[j * nl + l] - TT[(j - 1) * nl + l]) / d);
                if (j > 0 && j < m) tpp = max(tpp, abs(TT[(j + 1) * nl + l] - 2 * TT[j * nl + l] + TT[(j - 1) * nl + l]) / (d * d));
            }
            if (dl < 1e-3) { tp = 0.0; tpp = 0.0; }
            Bn = max(Bn, 2.0 * tp * km + tmax * kp + (1.0 + tmax * km) * km + tpp);
        }
        float d2a, d2m, d2b;
        rg_dz_chaussee(2, rid, a, rampe, d2a);
        rg_dz_chaussee(2, rid, 0.5 * (a + b), rampe, d2m);
        rg_dz_chaussee(2, rid, b, rampe, d2b);
        Bn = max(Bn, max(d2a, max(d2m, d2b)));
        float h = (Bn > 1e-12) ? min(pas_max, sqrt(8.0 * f / Bn)) : pas_max;
        int n = max(1, int(ceil(dl / h - 1e-9)));
        for (int j = 1; j < n; j++) {
            push(S, a + dl * j / n);
            push(OB, 0);
        }
        pas_min = min(pas_min, dl / n);
        fmaj = max(fmaj, Bn * (dl / n) * (dl / n) / 8.0);
    }
    push(S, U[-1]);
    push(OB, 1);

    // points
    int npts[];
    for (int j = 0; j < len(S); j++) {
        float x, y, th, k;
        vector gau;
        if (reg) {
            rg_reference(0, pr, S[j], x, y, th, k);
            gau = set(-sin(th), 0, -cos(th));
        } else {
            float sp = S[j] * (acc / max(L, 1e-9));
            int q = 0;
            while (q < len(VS) - 2 && sp >= VS[q + 1] - 1e-9) q++;
            vector A = VP[q];
            vector Bq = VP[q + 1];
            float u = clamp((sp - VS[q]) / max(VS[q + 1] - VS[q], 1e-12), 0.0, 1.0);
            vector P0 = lerp(A, Bq, u);
            x = P0.x;
            y = -P0.z;
            vector dlo = normalize(set(Bq.x - A.x, 0, Bq.z - A.z));
            th = atan2(-dlo.z, dlo.x);
            k = 0.0;
            gau = set(-sin(th), 0, -cos(th));
            // sommet intérieur : onglet (intersection des décalés des deux segments)
            int sommet = -1;
            if (abs(sp - VS[q]) < 1e-7 && q > 0) sommet = q;
            if (abs(sp - VS[q + 1]) < 1e-7 && q + 1 < len(VS) - 1) sommet = q + 1;
            if (sommet > 0) {
                vector d1 = normalize(set(VP[sommet].x - VP[sommet - 1].x, 0, VP[sommet].z - VP[sommet - 1].z));
                vector d2 = normalize(set(VP[sommet + 1].x - VP[sommet].x, 0, VP[sommet + 1].z - VP[sommet].z));
                vector n1 = set(d1.z, 0, -d1.x);
                vector n2 = set(d2.z, 0, -d2.x);
                vector mm = normalize(n1 + n2);
                gau = mm / dot(mm, n1);
                vector tg = normalize(d1 + d2);
                th = atan2(-tg.z, tg.x);
                x = VP[sommet].x;
                y = -VP[sommet].z;
            }
        }
        int p = addpoint(0, rg_vers_houdini(x, y, 0.0));
        setpointattrib(0, "s", p, S[j]);
        setpointattrib(0, "cap_rad", p, th);
        setpointattrib(0, "courbure", p, k);
        setpointattrib(0, "T", p, set(cos(th), 0, -sin(th)));
        setpointattrib(0, "gauche", p, gau);
        setpointattrib(0, "obligatoire", p, OB[j]);
        setpointattrib(0, "route", p, rid);
        push(npts, p);
    }
    int np = addprim(0, "polyline", npts);
    setprimattrib(0, "id", np, rid);
    setprimattrib(0, "n_echantillons", np, len(S));
    setprimattrib(0, "n_obligatoires", np, len(U));
    setprimattrib(0, "pas_min_m", np, pas_min);
    setprimattrib(0, "fleche_majorant_m", np, fmaj);
    setprimattrib(0, "longueur_polyligne_m", np, acc);
    setprimgroup(0, "echantillonnees", np, 1);
}
setdetailattrib(0, "rg_graphe_fleche_max_m", chf("../fleche_max"));
setdetailattrib(0, "rg_graphe_marge", chf("../marge_fleche"));
setdetailattrib(0, "rg_graphe_pas_max_m", pas_max);
setdetailattrib(0, "rg_rampe_plateau_pct", rampe);
"""

VEX_BRANCHES = r"""
// Branches d'un nœud triées par azimut (sens trigonométrique, 0° = est) : routes qui partent (cap en s = 0) et qui
// arrivent (cap en s = L + 180°) ; valence (RF-OSM-CAR-001 : nature du nœud du graphe).
string nid = s@id;
string br[];
string ex[];
float az[];
for (int pr = 0; pr < nprimitives(1); pr++) {
    string rid = prim(1, "id", pr);
    int pts[] = primpoints(1, pr);
    if (len(pts) < 2) continue;
    if (prim(1, "noeud_debut", pr) == nid) {
        float th = point(1, "cap_rad", pts[0]);
        push(br, rid);
        push(ex, "debut");
        push(az, (degrees(th) % 360.0 + 360.0) % 360.0);
    }
    if (prim(1, "noeud_fin", pr) == nid) {
        float th = point(1, "cap_rad", pts[-1]) + PI;
        push(br, rid);
        push(ex, "fin");
        push(az, (degrees(th) % 360.0 + 360.0) % 360.0);
    }
}
int o[] = argsort(az);
string b2[];
string e2[];
float a2[];
foreach (int k; o) {
    push(b2, br[k]);
    push(e2, ex[k]);
    push(a2, az[k]);
}
s[]@branches = b2;
s[]@extremites = e2;
f[]@azimuts_deg = a2;
i@valence = len(b2);
"""


def parametres():
    T = hou
    d34 = regles.valeur("DEF-034", "rampe_pct")
    return [
        T.FloatParmTemplate("fleche_max", "Flèche maximale (m)", 1, default_value=(0.0005,), min=1e-5, max=0.01,
                            help="Écart maximal entre une corde et la courbe (PLAN_GENERATEUR § 2.3, critère du lot L1 : "
                                 "0,5 mm), sur la ligne de référence et sur toutes les limites décalées."),
        T.FloatParmTemplate("marge_fleche", "Marge de calcul", 1, default_value=(0.9,), min=0.1, max=1.0,
                            help="Le pas vise flèche × marge (0,45 mm) : les sommets sont stockés en flottants 32 bits "
                                 "(± 1,5e-5 m à 200 m), la mesure indépendante doit rester sous 0,5 mm."),
        T.FloatParmTemplate("pas_max", "Pas maximal (m)", 1, default_value=(1.0,), min=0.05, max=20.0,
                            help="Pas en ligne droite à largeurs constantes (aucune règle : choix de fabrication, "
                                 "repris dans le manifeste)."),
        T.FloatParmTemplate("rampe_plateau_pct", "Rampe des plateaux (%)", 1, default_value=(float(d34),), min=1.0,
                            max=20.0, help="DEF-034 (rampe_pct = 7 %) : le schéma 0.1 ne porte que la longueur totale et "
                                           "la hauteur d'un plateau ; la rampe vient de cette règle."),
        T.ToggleParmTemplate("sommets_evenements", "Sommets aux évènements des limites", default_value=True,
                             help="Abaissés, intervalles et interruptions de marquage deviennent des sommets "
                                  "obligatoires (abscisses exactes pour les lots L2 et L4)."),
    ]


def construire(dossier=ICI):
    sub = R.sous_reseau("rg_" + NOM)
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres()))
    e1, e2, e3, e4 = sub.indirectInputs()[:4]
    ech = R.wrangle(sub, "echantillonner", VEX_ECHANTILLONNER, "detail", e1, entrees=(e2, e3),
                    bibliotheques=("rg_geometrie.h",))
    garder = sub.createNode("blast", "garder")
    garder.setInput(0, ech)
    garder.parm("group").set("echantillonnees")
    garder.parm("grouptype").set("prims")
    garder.parm("negate").set(1)
    cop = sub.createNode("attribcopy", "attributs_route")
    cop.setInput(0, garder)
    cop.setInput(1, e1)
    cop.parm("srcgrouptype").set("prims")
    cop.parm("destgrouptype").set("prims")
    cop.parm("attrib").set("otherattrib")
    cop.parm("attribname").set("* ^id ^n_echantillons ^n_obligatoires ^pas_min_m ^fleche_majorant_m "
                               "^longueur_polyligne_m")
    cop.parm("class").set("prims")
    cop.parm("matchbyattribute").set(1)
    cop.parm("attributetomatch").set("id")
    ref = sub.createNode("null", "REFERENCES")
    ref.setInput(0, cop)
    br = R.wrangle(sub, "branches", VEX_BRANCHES, "point", e4, entrees=(ref,))
    noe = sub.createNode("null", "NOEUDS")
    noe.setInput(0, br)
    R.sortie(sub, ref, 0, "sortie_references")
    R.sortie(sub, noe, 1, "sortie_noeuds")
    noe.setDisplayFlag(False)
    ref.setDisplayFlag(True)
    R.ranger(sub)
    aide = ("Graphe du générateur : lignes de référence échantillonnées à flèche ≤ 0,5 mm sur toutes les limites "
            "décalées (droites, arcs, clothoïdes ; polylignes en onglet), sommets obligatoires aux raccords, sections, "
            "lois de largeur, évènements et ralentisseurs ; branches des nœuds triées par azimut.")
    details = ("== Entrées ==\n\n1. Routes, 2. Profils, 3. Ponctuels, 4. Nœuds (sorties 1, 5, 4, 2 de rg::lire_modele).\n\n"
               "== Sorties ==\n\n1. Références : une polyligne par route (attributs de la route recopiés) ; points s, "
               "cap_rad, courbure, T, gauche, obligatoire ; primitives n_echantillons, pas_min_m, fleche_majorant_m.\n"
               "2. Nœuds : branches (ids triés dans le sens trigonométrique), extremites, azimuts_deg, valence.\n\n"
               "VEX 64 bits ; clothoïde par Gauss-Legendre composite (8 nœuds, panneaux de 0,5 m).")
    return R.creer_hda(sub, NOM, "RG Graphe (échantillonnage des lignes de référence)", parametres(), dossier,
                       entrees=(4, 4), sorties=2, aide=aide, details_aide=details, icone="SOP_resample",
                       etiquettes_entrees=("Routes", "Profils", "Ponctuels", "Nœuds"),
                       etiquettes_sorties=("Références échantillonnées", "Nœuds (branches triées)"))


if __name__ == "__main__":
    print(construire())
