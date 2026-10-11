"""Construit l'HDA pj::marquage_zone::1.0 (branche zones : hachures, zigzags, damiers, chevrons, contours MZ-*) ;
hython Houdini 22.

    hython recon/pcg/houdini/hda/pj_marquage_zone/construire.py

Réseau (README_HDA.md § 7) :
    normaliser (VEX 64 bits : genre, origine des bandes lue dans props, valeurs normatives si absentes)
      -> motifs (VEX : bandes de hachures, chevrons, carrés de damier, segments et joints de zigzag ; groupe motif)
      -> attributs (Attribute Copy)
      -> pour chaque zone (For-Each) : contour intérieur (PolyExpand2D) -> prisme (PolyExtrude)
         -> Boolean (motifs ∩ zone, contour peint = zone − retrait 3u)
      -> solide (pj::marquage_solide)
Entrées : 1 = zones (polygone de zone ; axe A -> B pour un zigzag), 2 = nivellement.
Sortie : maillages Y haut, un component par zone (pj_entite = id).
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "pj_marquage_commun"))
import pj_marquage_outils as M  # noqa: E402

O = M.O
T = hou
NOM = "marquage_zone"


def vex_normaliser():
    h = M.spec()["hachures"]
    z = M.spec()["zigzag_bus"]
    d = M.spec()["zones"]["damier_bus"]
    return r"""
// Genre et paramètres d'une zone (marquages_geometrie.json, recopiés à la construction) :
//   hachures (art. 117-2 A, schéma C3 ; MQ-ILO-003) : bande """ + str(h["bande_m"]) + r""" m, pas perpendiculaire
//     """ + str(h["pas_perpendiculaire_m"]) + r""" m, contour 3u et espace non peint 2u si contour_peint ;
//     origine des bandes : origine_bandes_l93 (props, float64), sinon centroïde ;
//   zigzag (art. 118-3 C ; MQ-BUS-005) : amplitude """ + str(z["amplitude_m"]) + r""" m, période """ + str(z["periode_m"]) + r""" m,
//     trait 2u, traits d'extrémité perpendiculaires ;
//   damier (zones.damier_bus) : carré """ + str(d["carre_m"]["defaut"]) + r""" m, échiquier ;
//   chevrons (MQ-ILO-003 : mêmes dimensions que les hachures, inclinés sur la bissectrice, pointe vers le conducteur) ;
//   autres genres (divers, bande_isolee, t_stationnement...) : contour décrit (levé GAM ou glyphe) tel quel.
string ty = hasprimattrib(0, "type") ? s@type : "";
string genre = "contour";
if (ty == "hachures" || ty == "zebra_zone") genre = "hachures";
else if (ty == "zigzag") genre = "zigzag";
else if (ty == "damier" || ty == "damier_bus") genre = "damier";
else if (ty == "chevrons") genre = "chevrons";
if (!primintrinsic(0, "closed", @primnum) && genre != "zigzag") genre = "ignore";
s@pj_genre = genre;
if (s@pj_entite == "") s@pj_entite = s@id;
float u = ch("../u");
f@pj_bande = hasprimattrib(0, "bande_m") && f@bande_m > 0 ? f@bande_m : """ + str(h["bande_m"]) + r""";
f@pj_pas = hasprimattrib(0, "pas_m") && f@pas_m > 0 ? f@pas_m : """ + str(h["pas_perpendiculaire_m"]) + r""";
f@pj_cap = hasprimattrib(0, "cap_bandes_deg") ? f@cap_bandes_deg : (hasprimattrib(0, "cap_deg") ? f@cap_deg : 0.0);
f@pj_contour = hasprimattrib(0, "contour_peint") && i@contour_peint ? 3 * u : 0.0;
f@pj_retrait = f@pj_contour > 0 ? 5 * u : 0.0;
f@pj_amplitude = hasprimattrib(0, "amplitude_m") && f@amplitude_m > 0 ? f@amplitude_m : """ + str(z["amplitude_m"]) + r""";
f@pj_periode = hasprimattrib(0, "periode_m") && f@periode_m > 0 ? f@periode_m : """ + str(z["periode_m"]) + r""";
f@pj_trait = hasprimattrib(0, "trait_m") && f@trait_m > 0 ? f@trait_m : 2 * u;
i@pj_cote = hasprimattrib(0, "cote") && i@cote < 0 ? -1 : 1;
f@pj_carre = hasprimattrib(0, "carre_m") && f@carre_m > 0 ? f@carre_m : """ + str(d["carre_m"]["defaut"]) + r""";
f@pj_angle = ch("../angle_chevrons");
// origine des bandes (Lambert-93 -> local, float64)
vector2 c = set(0.0, 0.0);
if (primintrinsic(0, "closed", @primnum)) { vector cc = pj_m_centroide_q(pj_m_anneau(0, @primnum)); c = set(cc.x, cc.y); }
v@pj_origine = set(c.x, c.y, 0);
if (hasprimattrib(0, "props") && find(s@props, "origine_bandes_l93") >= 0) {
    dict d = json_loads(s@props, 0);
    float ob[] = d["origine_bandes_l93"];
    if (len(ob) >= 2) v@pj_origine = set(ob[0] - 917279.43, ob[1] - 6460289.98, 0);
}
"""


VEX_MOTIFS = r"""
// Motifs générés (groupe motif, coupés ensuite par la zone) et zigzags (segments + joints, réunis par le solide).
string genre = s@pj_genre;
int src = @primnum;
i@pj_source = @primnum;                      // primitive gardée : ses propres attributs (Attribute Copy)
int nouv[];
if (genre == "ignore") { removeprim(0, @primnum, 1); return; }
if (genre == "contour") return;
vector2 q[] = pj_m_anneau(0, @primnum);
vector o3 = v@pj_origine;
vector2 o = set(o3.x, o3.y);
if (genre == "hachures" || genre == "chevrons" || genre == "damier") {
    vector2 a = pj_m_dir(f@pj_cap);
    vector2 n = set(-a.y, a.x);
    float tmin = 1e9, tmax = -1e9, smin = 1e9, smax = -1e9;
    foreach (vector2 v; q) {
        tmin = min(tmin, dot(v - o, n)); tmax = max(tmax, dot(v - o, n));
        smin = min(smin, dot(v - o, a)); smax = max(smax, dot(v - o, a));
    }
    float diag = (tmax - tmin) + (smax - smin) + 2.0;
    if (genre == "hachures") {
        // bandes parallèles à a, de largeur bande, au pas perpendiculaire pas (C3 : 0,50 / 1,35)
        float pas = f@pj_pas;
        for (int k = int(floor((tmin - f@pj_bande) / pas)); k <= int(ceil((tmax + f@pj_bande) / pas)); k++) {
            vector2 c = o + n * (k * pas) + a * (0.5 * (smin + smax));
            append(nouv, pj_m_poly(0, pj_m_rectangle(c, a, (smax - smin) + 2.0, f@pj_bande)));
        }
    } else if (genre == "chevrons") {
        // chevrons : pointe vers le conducteur (direction a), branches inclinées de « angle » sur la bissectrice
        float pas = f@pj_pas;
        float th = radians(f@pj_angle);
        for (int k = int(floor((smin - diag) / pas)); k <= int(ceil((smax + diag) / pas)); k++) {
            vector2 tip = o + a * (k * pas);
            float sgs[] = {1.0, -1.0};
            foreach (float sg; sgs) {
                vector2 v = -a;
                vector2 d = normalize(set(v.x * cos(sg * th) - v.y * sin(sg * th), v.x * sin(sg * th) + v.y * cos(sg * th)));
                append(nouv, pj_m_poly(0, pj_m_rectangle(tip + d * (diag / 2), d, diag, f@pj_bande)));
            }
        }
    } else {
        // damier en échiquier, carrés de côté carre alignés sur a, origine au centroïde (zones.damier_bus)
        float cr = f@pj_carre;
        for (int i = int(floor(smin / cr)) - 1; i <= int(ceil(smax / cr)) + 1; i++)
            for (int j = int(floor(tmin / cr)) - 1; j <= int(ceil(tmax / cr)) + 1; j++)
                if ((i + j) % 2 == 0)
                    append(nouv, pj_m_poly(0, pj_m_rectangle(o + a * ((i + 0.5) * cr) + n * ((j + 0.5) * cr), a, cr, cr)));
    }
    foreach (int np; nouv) {
        setprimgroup(0, "motif", np, 1);
        setprimattrib(0, "pj_source", np, src);
    }
    return;
}
if (genre == "zigzag") {
    // axe A -> B le long de la bordure ; sommets aux pointes (amplitude à l'axe du trait), traits d'extrémité
    // perpendiculaires de longueur amplitude (MQ-BUS-005 : le motif commence et finit en sommet)
    int pts[] = primpoints(0, @primnum);
    vector PA = point(0, "P", pts[0]);
    vector PB = point(0, "P", pts[len(pts) - 1]);
    vector2 A = pj_m_xy(PA);
    vector2 B = pj_m_xy(PB);
    float L = length(B - A);
    vector2 u = (B - A) / max(L, 1e-9);
    vector2 n = set(-u.y, u.x) * i@pj_cote;
    int npe = max(1, int(rint(L / f@pj_periode)));
    float P = L / npe;
    float amp = f@pj_amplitude;
    vector2 Z[];
    append(Z, A);
    for (int k = 0; k <= npe; k++) {
        append(Z, A + u * (k * P) + n * amp);
        if (k < npe) append(Z, A + u * ((k + 0.5) * P));
    }
    append(Z, B);
    float h = f@pj_trait / 2;
    // ruban à onglets limités : UN SEUL polygone (décalages ±h de la polyligne Z, onglet borné à 3 h), sans
    // recouvrement ni encoche aux sommets (revue réalisme du 11/10/2026 : éclat en pointe au sommet de MZ-5299/5300 avec
    // l'ancienne réunion de rectangles et de biseaux ; MQ-BUS-005)
    int nz = len(Z);
    vector2 G[], D[];
    for (int i = 0; i < nz; i++) {
        vector2 t0 = i > 0 ? normalize(Z[i] - Z[i - 1]) : normalize(Z[1] - Z[0]);
        vector2 t1 = i + 1 < nz ? normalize(Z[i + 1] - Z[i]) : t0;
        vector2 n0 = set(-t0.y, t0.x);
        vector2 n1 = set(-t1.y, t1.x);
        vector2 m = n0 + n1;
        m = length(m) > 1e-9 ? normalize(m) : n0;
        float c = max(dot(m, n0), 1.0 / 3.0);
        append(G, Z[i] + m * (h / c));
        append(D, Z[i] - m * (h / c));
    }
    vector2 R[];
    foreach (vector2 q; G) append(R, q);
    for (int i = nz - 1; i >= 0; i--) append(R, D[i]);
    int np0 = pj_m_poly(0, R);
    setprimattrib(0, "partie", np0, 0);
    append(nouv, np0);
    foreach (int np; nouv) {
        setprimattrib(0, "pj_source", np, src);
        setprimattrib(0, "anneau", np, 0);
    }
    removeprim(0, @primnum, 1);
}
"""

VEX_PARTIES = r"""
// pièces de motif : une partie chacune (réunion par le solide) ; contour de zone : partie 0
if (inprimgroup(0, "motif", @primnum)) { i@partie = 1000 + @primnum; i@anneau = 0; }
"""


def parametres():
    z = [
        T.FloatParmTemplate("u", "Unité u (m)", 1, default_value=(0.05,), min=0.03, max=0.075,
                            help="Largeurs 2u, 3u, 5u (marquages_geometrie.unite_u ; contour 3u et espace 2u des "
                                 "hachures, trait 2u du zigzag)."),
        T.FloatParmTemplate("angle_chevrons", "Angle des chevrons sur la bissectrice (°)", 1, default_value=(63.435,),
                            min=10.0, max=85.0, help="Inclinaison 2 pour 1 des hachures (26,565° sur la rive)."),
        T.FloatParmTemplate("fragment_min", "Fragment de motif minimal (m²)", 1, default_value=(0.02,), min=0.0,
                            max=1.0, help="Morceaux de bande plus petits retirés après la coupe par la zone."),
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
                           menu_labels=("Région majoritaire de la pièce", "Attribut pj_region",
                                        "Région de chaque sommet (suit les marches)"), default_value=0),
        T.FloatParmTemplate("seuil_franchissement", "Seuil de franchissement (m)", 1, default_value=(0.02,), min=0.0,
                            max=0.2),
        T.StringParmTemplate("couche", "Couche USD (pj_couche)", 1, default_value=(M.COUCHE,)),
        T.FloatParmTemplate("cusp", "Angle de rupture des normales (°)", 1, default_value=(30.0,), min=0.0, max=180.0),
    ]
    return [T.FolderParmTemplate("f_zone", "Zones", parm_templates=z, folder_type=T.folderType.Tabs),
            T.FolderParmTemplate("f_solide", "Peinture (solide)", parm_templates=sol, folder_type=T.folderType.Tabs)]


VEX_FRAGMENTS = r"""
// fragments de motif trop petits après la coupe (pointes de hachures ; l'IISR prévoit un aplat sous 0,30 m)
float ar = primintrinsic(0, "measuredarea", @primnum);
if (ar < ch("../fragment_min")) removeprim(0, @primnum, 1);
"""


def construire(dossier=ICI):
    L = M.charger(ICI.parent / "pj_marquage_ligne" / "construire.py", "construire_ligne")
    M.installer_commun()
    sub = O.sous_reseau("pj_" + NOM)
    sub.setParmTemplateGroup(T.ParmTemplateGroup(parametres()))
    ent, niv, sol_fab = sub.indirectInputs()[0], sub.indirectInputs()[1], sub.indirectInputs()[2]
    nor = M.wrangle_m(sub, "normaliser", vex_normaliser(), "primitive", ent, precision64=True)
    mot = M.wrangle_m(sub, "motifs", VEX_MOTIFS, "primitive", nor)
    att = L.copie_attributs(sub, "attributs_motifs", mot, nor, exclus="pj_source partie anneau")
    par = M.wrangle_m(sub, "parties", VEX_PARTIES, "primitive", att, bibliotheques=False)

    def corps(debut):
        zone = M.blast(sub, "zone", debut, "motif | @pj_genre=zigzag", garder=False)
        motifs = M.blast(sub, "motifs_de_la_zone", debut, "motif", garder=True)
        autres = M.blast(sub, "contours_et_zigzags", debut, "motif | @pj_genre=hachures @pj_genre=chevrons "
                                                            "@pj_genre=damier", garder=False)
        # retrait intérieur (contour 3u + espace 2u) et bord intérieur du contour peint (3u) : PolyExpand2D
        ret = sub.createNode("polyexpand2d", "retrait_interieur")
        ret.setInput(0, zone)
        ret.parm("output").set("surfaces")
        ret.parm("outputinside").set(1)
        ret.parm("outputoutside").set(0)
        ret.parm("offset").setExpression('max(1e-4, prim("../zone", 0, "pj_retrait", 0))')
        sw_r = M.interrupteur(sub, "choix_retrait", (zone, ret), 'prim("../zone", 0, "pj_retrait", 0) > 0')
        pri = sub.createNode("polyextrude::2.0", "prisme_zone")
        pri.setInput(0, sw_r)
        for p, v in (("splittype", "components"), ("dist", 2.0), ("outputback", 1)):
            pri.parm(p).set(v)
        pri_c = sub.createNode("xform", "prisme_centre")
        pri_c.setInput(0, pri)
        pri_c.parm("ty").set(-1.0)
        inter = sub.createNode("boolean::2.0", "couper_motifs")
        inter.setInput(0, motifs)
        inter.setInput(1, pri_c)
        inter.parm("asurface").set("surface")
        inter.parm("booleanop").set("intersect")
        frag = M.wrangle_m(sub, "retirer_fragments", VEX_FRAGMENTS, "primitive", inter, bibliotheques=False)
        # contour peint : zone moins son retrait de 3u
        ret3 = sub.createNode("polyexpand2d", "bord_contour")
        ret3.setInput(0, zone)
        ret3.parm("output").set("surfaces")
        ret3.parm("outputinside").set(1)
        ret3.parm("outputoutside").set(0)
        ret3.parm("offset").setExpression('max(1e-4, prim("../zone", 0, "pj_contour", 0))')
        pri3 = sub.createNode("polyextrude::2.0", "prisme_contour")
        pri3.setInput(0, ret3)
        for p, v in (("splittype", "components"), ("dist", 2.0), ("outputback", 1)):
            pri3.parm(p).set(v)
        pri3_c = sub.createNode("xform", "prisme_contour_centre")
        pri3_c.setInput(0, pri3)
        pri3_c.parm("ty").set(-1.0)
        anneau = sub.createNode("boolean::2.0", "contour_peint")
        anneau.setInput(0, zone)
        anneau.setInput(1, pri3_c)
        anneau.parm("asurface").set("surface")
        anneau.parm("booleanop").set("subtract")
        vide = M.blast(sub, "sans_contour", zone, "*", garder=False)
        sw_c = M.interrupteur(sub, "choix_contour", (vide, anneau), 'prim("../zone", 0, "pj_contour", 0) > 0')
        fus = sub.createNode("merge", "fusion_zone")
        fus.setInput(0, autres)
        fus.setInput(1, frag)
        fus.setInput(2, sw_c)
        motif_seul = M.interrupteur(sub, "choix_genre", (debut, fus), 'npoints("../motifs_de_la_zone") > 0 || '
                                                                       'prim("../zone", 0, "pj_contour", 0) > 0')
        return motif_seul

    _, fin = M.boucle_par_attribut(sub, par, "pj_entite", corps, nom="par_zone")
    sol = sub.createNode("pj::marquage_solide::1.0", "solide")
    sol.setInput(0, fin)
    sol.setInput(1, niv)
    sol.setInput(2, sol_fab)               # sol fabriqué (pj::sol) : drapé sur le sol maillé (TQ-MQG-005)
    L.relier_solide(sol)
    sol.parm("pas_maillage").setExpression('ch("../pas_maillage")')
    out = sub.createNode("null", "MAILLAGES")
    out.setInput(0, sol)
    O.sortie(sub, out, 0, "sortie")
    O.ranger(sub)
    return O.creer_hda(sub, NOM, "PJ Marquage : zones (hachures, zigzags, damiers, chevrons)", parametres(), dossier,
                       entrees=(1, 3), sorties=1, icone="SOP_polyexpand2d",
                       aide="Zones de marquage depuis leurs paramètres : hachures (bandes 0,50 au pas perpendiculaire "
                            "1,85, inclinaison de la description, contour 3u et espace 2u), zigzags d'arrêt de bus, "
                            "damiers, chevrons, coupés par le polygone de zone (PolyExpand2D, Boolean) ; contours "
                            "décrits (levé GAM, glyphes) tels quels ; peinture extrudée et drapée (pj::marquage_solide).",
                       details_aide="== Entrées ==\n\n1. Zones : polygone (hachures, damier, chevrons, contour) ou axe "
                                    "A -> B (zigzag) ; attributs type, bande_m, pas_m, cap_bandes_deg, "
                                    "origine_bandes_l93 (props), contour_peint, amplitude_m, periode_m, trait_m, cote.\n"
                                    "2. Nivellement.\n\nRègles : MQ-ILO-003, MQ-BUS-005, MQ-DET-010. Contrat : "
                                    "README_HDA.md § 7.",
                       etiquettes_entrees=("Zones (polygones ou axes)", "Nivellement (HeightField)",
                                           "Sol fabriqué (facultatif)"),
                       etiquettes_sorties=("Maillages (Y haut)",))


if __name__ == "__main__":
    print(construire())
