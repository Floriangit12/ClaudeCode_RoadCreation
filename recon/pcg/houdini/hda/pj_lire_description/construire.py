"""Construit l'HDA pj::lire_description::1.0 (lecteur unique de la description v2) ; hython Houdini 22.

    hython recon/pcg/houdini/hda/pj_lire_description/construire.py

Réseau (README_HDA.md § 3) :
    lire_entites (Python SOP, module lecteur.py) + entrée 1 facultative (supplementaires, VEX) -> fusion -> orienter (VEX) -> inverser (Reverse) -> nettoyer_groupes
      -> abscisses (VEX) -> profils (VEX) -> niveaux_bordures (VEX) -> altitude (VEX, entrée 2 : NIVEAU) -> ENTITES
    lire_nivellement (Python SOP) -> flou_comblement (Volume Blur) -> combler (Volume Wrangle) -> retirer_poids (Blast)
      -> NIVEAU
Sorties : 1 = entités (courbes, polygones, attributs), 2 = HeightField de nivellement (height, r0, z1, r1, z2, r2).
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "commun"))
import pj_hda_outils as O  # noqa: E402

NOM = "lire_description"
DEFAUT_DOSSIER = "D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/description/base"

VEX_SUPPLEMENTAIRES = r"""
// Entités supplémentaires (entrée 1, facultative : courbes ou polygones tracés à la main, splines Unreal via Houdini
// Engine) : mêmes groupes que les entités lues (README_HDA.md § 2 et § 4), à partir de famille et classe.
string fam = s@famille;
string cl = s@classe;
if (fam == "") fam = "supplementaire";
setprimgroup(0, "f_" + fam, @primnum, 1);
setprimgroup(0, "supplementaires", @primnum, 1);
string b = "";
if (fam == "bordures") b = "bordures";
else if (fam == "surfaces" || fam == "ponctuels_sol") b = "sol";
else if (fam == "ilots") b = "ilots";
else if (fam == "marquages") {
    if (cl == "ligne" || cl == "transversale") b = "marquages_lignes";
    else if (cl == "passage") b = "passages";
    else if (cl == "fleche" || cl == "symbole") b = "symboles";
    else b = "zones";
}
if (b != "") setprimgroup(0, "b_" + b, @primnum, 1);
if (i@graine == 0) i@graine = random_shash(s@id) & 0x7FFFFFFF;    // graine absente : hachage de l'id
if (!hasprimattrib(0, "region_niveau")) i@region_niveau = -1;
"""

VEX_ORIENTER = r"""
// Faces de sol à normale +Y (README_HDA.md § 2) : aire signée dans le plan XZ ; A < 0 -> normale -Y -> à retourner.
if (primintrinsic(0, "closed", @primnum) && @numvtx >= 3) {
    int pts[] = primpoints(0, @primnum);
    float a = 0;
    for (int k = 0; k < len(pts); k++) {
        vector p = point(0, "P", pts[k]);
        vector q = point(0, "P", pts[(k + 1) % len(pts)]);
        a += p.x * q.z - q.x * p.z;
    }
    if (a < 0) setprimgroup(0, "a_inverser", @primnum, 1);
}
"""

VEX_ABSCISSES = r"""
// Abscisse curviligne plane s (m) des courbes ouvertes : même s que les intervalles, abaissés et
// geometrie_reguliere de la description (longueur planimétrique).
if (!primintrinsic(0, "closed", @primnum)) {
    int pts[] = primpoints(0, @primnum);
    float s = 0;
    vector a = point(0, "P", pts[0]);
    setpointattrib(0, "s", pts[0], 0.0);
    for (int k = 1; k < len(pts); k++) {
        vector b = point(0, "P", pts[k]);
        s += length(set(b.x - a.x, 0, b.z - a.z));
        setpointattrib(0, "s", pts[k], s);
        a = b;
    }
}
"""

VEX_PROFILS = r"""
// Bordures : profil NF, vue (m) et rôle de l'intervalle qui contient s ; vue linéaire de vue_m à vue_m_fin
// (chartière, GA-CHR-002). Les points ne sont pas partagés entre primitives.
s@profil = "";
f@vue_m = 0;
s@role = "";
int pr = pointprims(0, @ptnum)[0];
string fam = prim(0, "famille", pr);
if (fam == "bordures") {
    dict iv[] = prim(0, "intervalles", pr);
    int n = len(iv);
    for (int k = 0; k < n; k++) {
        float s0 = iv[k]["s0"];
        float s1 = iv[k]["s1"];
        if (f@s <= s1 + 1e-6 || k == n - 1) {
            string pf = iv[k]["profil"];
            string ro = iv[k]["role"];
            float v0 = iv[k]["vue_m"];
            float v = v0;
            if (isvalidindex(iv[k], "vue_m_fin")) {
                float v1 = iv[k]["vue_m_fin"];
                v = lerp(v0, v1, clamp((f@s - s0) / max(s1 - s0, 1e-9), 0.0, 1.0));
            }
            s@profil = pf;
            s@role = ro;
            f@vue_m = v;
            break;
        }
    }
}
"""

VEX_NIVEAUX_BORDURES = r"""
// Bordures : pied, tête et arête arrière du modèle unique (nivellement.json bordures[], TQ-SOL-013), en s.
f@z_pied = f@z_decrit;
f@z_tete = f@z_decrit + f@vue_m;
f@z_arriere = f@z_tete;
int pr = pointprims(0, @ptnum)[0];
string fam = prim(0, "famille", pr);
if (fam == "bordures") {
    float S[] = prim(0, "niv_s", pr);
    if (len(S) > 0) {
        float zp[] = prim(0, "niv_z_pied", pr);
        float zt[] = prim(0, "niv_z_tete", pr);
        float za[] = prim(0, "niv_z_arriere", pr);
        f@z_pied = pj_interp(f@s, S, zp);
        f@z_tete = pj_interp(f@s, S, zt);
        f@z_arriere = pj_interp(f@s, S, za);
    }
}
"""

VEX_ALTITUDE = r"""
// Altitude des sommets (paramètre « Altitude ») :
//   decrite     : Z de la description si présent (bordures : pied ; ponctuels), sinon modèle de nivellement ;
//   nivellement : modèle unique (TQ-SOL-013, CF-26) : bordures -> z_pied (nivellement.json), autres -> pj_niv_z dans
//                 la région de l'entité (region_niveau ; -1 : nœud propriétaire) ;
//   plat        : z = 0.
string mode = chs("../altitude");
float g[] = pj_niv_grille(1);
int pr = pointprims(0, @ptnum)[0];
string fam = prim(0, "famille", pr);
float z = 0;
if (mode != "plat") {
    if (mode == "decrite" && i@a_z) {
        z = f@z_decrit;
    } else {
        float S[] = prim(0, "niv_s", pr);
        if (fam == "bordures" && len(S) > 0) {
            z = f@z_pied;
        } else {
            int reg = prim(0, "region_niveau", pr);
            z = pj_niv_z(g, @P.x, -@P.z, reg);
            if (z < 0.5 * PJ_NIV_ABSENT) z = i@a_z ? f@z_decrit : 0.0;
        }
    }
}
@P.y = z;
"""

VEX_COMBLER = r"""
// Trous du HeightField (r0 = -1 : bâtiments, hors modèle) comblés pour l'affichage par flou normalisé
// (height pondéré / poids, flous de même rayon). r0 reste à -1 : pj_niv_z n'utilise jamais ces nœuds.
// (f@ explicite : @w serait lu comme le vecteur de vitesse angulaire standard)
if (f@r0 < 0 && f@poids > 1e-6) f@height = f@zpond / f@poids;
"""


def parametres():
    T = hou
    dossier = T.StringParmTemplate("dossier", "Dossier de la description (base/)", 1, default_value=(DEFAUT_DOSSIER,),
                                   string_type=T.stringParmType.FileReference, file_type=T.fileType.Directory,
                                   help="Dossier base/ de la description v2 : bordures, surfaces, ilots, ponctuels_sol, "
                                        "marquages (.geojson, L93 / NGF), nivellement.json et nivellement_grille.npz.")
    fams = [T.ToggleParmTemplate(f"fam_{f}", lib, default_value=True,
                                 help=f"Charger la famille {f} ({f}.geojson).")
            for f, lib in (("bordures", "Bordures"), ("surfaces", "Surfaces"), ("ilots", "Îlots"),
                           ("ponctuels_sol", "Ponctuels de sol (BEV)"), ("marquages", "Marquages"))]
    nf = T.ToggleParmTemplate("marquages_non_fabriques", "Garder les marquages non fabriqués", default_value=False,
                              help="Lignes d'arrêt virtuelles et hypothèses non peintes (fabrication.statut = "
                                   "non_fabrique, MQ-LEF-002/011) : groupe non_fabrique, hors des branches.")
    props = T.ToggleParmTemplate("garder_props", "Garder les propriétés JSON (props)", default_value=True,
                                 help="Attribut de primitive props : propriétés complètes de l'entité en JSON (traçabilité).")
    filtre = T.StringParmTemplate("filtre_ids", "Filtre d'identifiants", 1, default_value=("",),
                                  help="Motifs séparés par des espaces (fnmatch), ex. « K-03* S-0213a ». Vide : tout.")
    f_desc = T.FolderParmTemplate("f_description", "Description", parm_templates=[dossier] + fams + [nf, props, filtre],
                                  folder_type=T.folderType.Tabs)
    emp = T.MenuParmTemplate("emprise", "Emprise", menu_items=("site", "pilote", "boite", "tuile"),
                             menu_labels=("Site complet (carré local de 300 m)", "Zone pilote ZP-01",
                                          "Boîte (repère local)", "Tuile du site"), default_value=0,
                             help="Entités gardées : celles dont la boîte englobante touche l'emprise (entières, "
                                  "non découpées).")
    bmin = T.FloatParmTemplate("boite_min", "Boîte : x, y min (m)", 2, default_value=(-11.0, -28.0),
                               help="Coin bas-gauche, repère local (L93 − O).")
    bmax = T.FloatParmTemplate("boite_max", "Boîte : x, y max (m)", 2, default_value=(60.0, 72.0))
    for t in (bmin, bmax):
        t.setConditional(T.parmCondType.HideWhen, "{ emprise != boite }")
    tt = T.FloatParmTemplate("tuile_taille", "Tuile : taille (m)", 1, default_value=(64.0,), min=1.0, max=300.0,
                             help="Tuiles carrées à partir du coin (−150, −150) du site.")
    ti = T.IntParmTemplate("tuile_index", "Tuile : indices i, j", 2, default_value=(2, 2), min=0, max=10)
    for t in (tt, ti):
        t.setConditional(T.parmCondType.HideWhen, "{ emprise != tuile }")
    marge = T.FloatParmTemplate("marge", "Marge (m)", 1, default_value=(0.0,), min=0.0, max=50.0,
                                help="Élargit l'emprise de chaque côté.")
    f_emp = T.FolderParmTemplate("f_emprise", "Emprise", parm_templates=[emp, bmin, bmax, tt, ti, marge],
                                 folder_type=T.folderType.Tabs)
    alt = T.MenuParmTemplate("altitude", "Altitude des sommets", menu_items=("decrite", "nivellement", "plat"),
                             menu_labels=("Décrite (Z de la description, sinon nivellement)",
                                          "Nivellement (modèle unique TQ-SOL-013)", "À plat (z = 0)"),
                             default_value=0,
                             help="Z des sommets en sortie 1 : bordures au pied de face ; surfaces, îlots et marquages "
                                  "sur le modèle de nivellement de leur région.")
    cn = T.ToggleParmTemplate("charger_nivellement", "Charger le nivellement (sortie 2)", default_value=True,
                              help="HeightField du modèle unique : height (z0), r0, z1, r1, z2, r2 (pas 0,10 m).")
    nm = T.FloatParmTemplate("niv_marge", "Marge du recadrage (m)", 1, default_value=(2.0,), min=0.0, max=50.0)
    npas = T.IntParmTemplate("niv_pas", "Sous-échantillonnage (1 = 0,10 m)", 1, default_value=(1,), min=1, max=10,
                             help="Aperçu seulement : au-delà de 1, la requête n'est plus exacte.")
    rc = T.FloatParmTemplate("comblement_rayon", "Rayon de comblement des trous (m)", 1, default_value=(30.0,),
                             min=0.0, max=100.0, help="Flou normalisé de la couche height sous les bâtiments (affichage).")
    f_niv = T.FolderParmTemplate("f_nivellement", "Altitude et nivellement", parm_templates=[alt, cn, nm, npas, rc],
                                 folder_type=T.folderType.Tabs)
    return [f_desc, f_emp, f_niv]


def construire(dossier=ICI):
    sub = O.sous_reseau("pj_" + NOM)
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres()))
    module = (ICI / "lecteur.py").read_text(encoding="utf-8")

    lire = sub.createNode("python", "lire_entites")
    lire.parm("python").set("# Lecteur de la description v2 (module lecteur.py embarqué dans l'HDA)\n"
                            "hou.pwd().parent().hdaModule().lire_entites(hou.pwd())\n")
    sup = O.wrangle(sub, "supplementaires", VEX_SUPPLEMENTAIRES, "primitive", sub.indirectInputs()[0])
    fus = sub.createNode("merge", "fusion")
    fus.setInput(0, lire)
    fus.setInput(1, sup)
    ori = O.wrangle(sub, "orienter", VEX_ORIENTER, "primitive", fus)
    inv = sub.createNode("reverse", "inverser")
    inv.setInput(0, ori)
    inv.parm("group").set("a_inverser")
    ng = sub.createNode("groupdelete", "nettoyer_groupes")
    ng.setInput(0, inv)
    ng.parm("group1").set("a_inverser")
    absc = O.wrangle(sub, "abscisses", VEX_ABSCISSES, "primitive", ng)
    prof = O.wrangle(sub, "profils", VEX_PROFILS, "point", absc)
    nivb = O.wrangle(sub, "niveaux_bordures", VEX_NIVEAUX_BORDURES, "point", prof, bibliotheques=("pj_niveau.h",))

    lniv = sub.createNode("python", "lire_nivellement")
    lniv.parm("python").set("# Modèle de nivellement (nivellement_grille.npz) -> volumes 2D (HeightField)\n"
                            "hou.pwd().parent().hdaModule().lire_nivellement(hou.pwd())\n")
    flou = sub.createNode("volumeblur", "flou_comblement")
    flou.setInput(0, lniv)
    flou.parm("group").set("@name=poids @name=zpond")
    flou.parm("radius").setExpression('ch("../comblement_rayon")')
    comb = sub.createNode("volumewrangle", "combler")
    comb.setInput(0, flou)
    comb.parm("snippet").set(VEX_COMBLER)
    retp = sub.createNode("blast", "retirer_poids")
    retp.setInput(0, comb)
    retp.parm("group").set("@name=poids @name=zpond")
    niveau = sub.createNode("null", "NIVEAU")
    niveau.setInput(0, retp)

    alt = O.wrangle(sub, "altitude", VEX_ALTITUDE, "point", nivb, entrees=(niveau,),
                    bibliotheques=("pj_niveau.h",))
    ent = sub.createNode("null", "ENTITES")
    ent.setInput(0, alt)
    O.sortie(sub, ent, 0, "sortie_entites")
    O.sortie(sub, niveau, 1, "sortie_nivellement")
    for n in (ent, niveau):
        n.setDisplayFlag(False)
    ent.setDisplayFlag(True)
    O.ranger(sub)
    aide = ("Lecteur unique de la description v2 du carrefour Paquet Jardin : familles GeoJSON (L93, NGF) converties "
            "en courbes et polygones Houdini (Y haut, (x, z, −y) locaux) avec tous leurs attributs, et modèle de "
            "nivellement unique (TQ-SOL-013) en HeightField.")
    details = ("== Sorties ==\n\n1. Entités : une primitive par anneau ou partie ; attributs normalisés (id, famille, "
               "classe, materiau_id, src, conf, usure, salissure, couverture, graine, region_niveau), propriétés brutes, "
               "groupes f_<famille> et b_<branche>.\n2. Nivellement : volumes height, r0, z1, r1, z2, r2 (pas 0,10 m), "
               "détail niv_x0, niv_y0, niv_pas, niv_ni, niv_nj.\n\nConventions : recon/pcg/houdini/hda/README_HDA.md.")
    return O.creer_hda(sub, NOM, "PJ Lire la description", parametres(), dossier, entrees=(0, 1), sorties=2,
                       aide=aide, details_aide=details, module_python=module, icone="SOP_file",
                       etiquettes_entrees=("Entités supplémentaires (facultatif)",),
                       etiquettes_sorties=("Entités", "Nivellement (HeightField)"))


if __name__ == "__main__":
    print(construire())
