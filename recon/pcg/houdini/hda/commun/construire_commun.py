"""Construit les HDA communes (hython Houdini 22) :

    pj::niveau_z::1.0          requête du modèle de nivellement (VEX pj_niveau.h) sur des points
    pj::preparer_export::1.0   maillages d'une branche (Y haut) -> géométrie prête pour SOP Import (contrat pj_usd/0.1)
    pj::exporter_points::1.0   points d'instances -> pj_points/0.1 (repère local Z haut ; Python SOP de sérialisation)

    hython recon/pcg/houdini/hda/commun/construire_commun.py
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import pj_hda_outils as O  # noqa: E402

T = hou

# ------------------------------------------------------------------------------------------------ pj::niveau_z
VEX_NIVEAU_Z = r"""
// Z du modèle de nivellement unique (TQ-SOL-013, CF-26) : interpolation restreinte à la région (pj_niv_z).
float g[] = pj_niv_grille(1);
int reg = -1;
if (chs("../mode_region") == "attribut") {
    string a = chs("../attribut_region");
    if (haspointattrib(0, a)) {
        reg = point(0, a, @ptnum);
    } else if (hasprimattrib(0, a)) {
        int prs[] = pointprims(0, @ptnum);
        if (len(prs) > 0) reg = prim(0, a, prs[0]);
    }
}
float z = pj_niv_z(g, @P.x, -@P.z, reg);
int absent = z < 0.5 * PJ_NIV_ABSENT;
if (absent) {
    i@niv_absent = 1;
    z = chs("../si_absent") == "zero" ? 0.0 : @P.y - ch("../decalage");
}
z += ch("../decalage");
if (chs("../sortie") == "P") @P.y = z;
else setpointattrib(0, chs("../nom_attribut"), @ptnum, z);
"""


def niveau_z(dossier):
    parms = [
        T.MenuParmTemplate("mode_region", "Région de nivellement", menu_items=("attribut", "proprietaire"),
                           menu_labels=("Attribut (point ou primitive)", "Nœud propriétaire le plus proche"),
                           default_value=0,
                           help="Région du modèle dans laquelle interpoler (les marches de bordure ne sont jamais lissées). "
                                "Attribut absent ou −1 : nœud propriétaire."),
        T.StringParmTemplate("attribut_region", "Attribut de région", 1, default_value=("region_niveau",),
                             help="Entier : region_niveau (surfaces, îlots, bordures côté bas) ou region_haute."),
        T.MenuParmTemplate("sortie", "Écrire dans", menu_items=("P", "attribut"),
                           menu_labels=("Position (P.y)", "Attribut flottant"), default_value=0),
        T.StringParmTemplate("nom_attribut", "Nom de l'attribut", 1, default_value=("z_niv",)),
        T.FloatParmTemplate("decalage", "Décalage (m)", 1, default_value=(0.0,), min=-1.0, max=1.0,
                            help="Ajouté au Z du modèle (ex. +0,003 pour une peinture posée)."),
        T.MenuParmTemplate("si_absent", "Hors modèle", menu_items=("garder", "zero"),
                           menu_labels=("Garder le Z d'entrée", "z = 0"), default_value=0,
                           help="Points hors du modèle : attribut niv_absent = 1."),
    ]
    parms[3].setConditional(T.parmCondType.HideWhen, "{ sortie != attribut }")
    parms[1].setConditional(T.parmCondType.HideWhen, "{ mode_region != attribut }")
    sub = O.sous_reseau("pj_niveau_z")
    sub.setParmTemplateGroup(T.ParmTemplateGroup(parms))
    ent = sub.indirectInputs()
    w = O.wrangle(sub, "niveau", VEX_NIVEAU_Z, "point", ent[0], entrees=(ent[1],), bibliotheques=("pj_niveau.h",))
    O.sortie(sub, w, 0, "sortie")
    O.ranger(sub)
    return O.creer_hda(sub, "niveau_z", "PJ Niveau Z (nivellement)", parms, dossier, entrees=(2, 2), sorties=1,
                       aide="Lit le Z du modèle de nivellement unique (TQ-SOL-013) pour chaque point : portage VEX "
                            "exact de nivellement_requete.Nivellement.z (écart < 0,4 mm, float32).",
                       icone="SOP_heightfield", etiquettes_entrees=("Géométrie", "Nivellement (HeightField)"))


# ------------------------------------------------------------------------------------------------ pj::preparer_export
VEX_VERIFIER = r"""
// Contrat pj_usd/0.1 (recon/pcg/ue/CONTRAT_EXPORT.md) : attributs attendus d'une branche.
string requis[] = {"materiau_id", "pj_entite"};
foreach (string a; requis) {
    if (!hasprimattrib(0, a)) warning("attribut de primitive %s absent (README_HDA.md § 4)", a);
}
if (hasvertexattrib(0, "N")) setattribtypeinfo(0, "vertex", "N", "normal");
if (haspointattrib(0, "N")) setattribtypeinfo(0, "point", "N", "normal");
"""

VEX_UV_SECOURS = r"""
// UV de secours en mètres (E3) : projection sur le plan dominant de la face, coordonnées locales Z haut
// (horizontal : (x, y) ; vertical : (abscisse horizontale, z)). Jamais de projection de dessus sur une face verticale.
vector n = normalize(prim_normal(0, @primnum, {0.5, 0.5, 0}));
vector p = point(0, "P", vertexpoint(0, @vtxnum));
vector l = set(p.x, -p.z, p.y);
vector nl = set(n.x, -n.z, n.y);
vector a = abs(nl);
if (a.z >= a.x && a.z >= a.y) v@uv = set(l.x, l.y, 0);
else if (a.x >= a.y) v@uv = set(l.y, l.z, 0);
else v@uv = set(l.x, l.z, 0);
"""

VEX_CHEMINS = r"""
// Hiérarchie du contrat (§ 2) : /World/<couche>/<entité>/<maillage> ; matériau /World/Looks/<materiau_id> (E5) ;
// MI Unreal (Houdini Engine) /Game/PJ/Materials/MI_<id>.MI_<id>.
string couche = hasprimattrib(0, "pj_couche") ? prim(0, "pj_couche", @primnum) : "";
if (couche == "") couche = chs("../couche_defaut");
string ent = hasprimattrib(0, "pj_entite") ? prim(0, "pj_entite", @primnum) : "";
if (ent == "") ent = hasprimattrib(0, "id") ? prim(0, "id", @primnum) : "sans_id";
string mid = hasprimattrib(0, "materiau_id") ? prim(0, "materiau_id", @primnum) : "";
if (mid == "") mid = chs("../materiau_defaut");
string mai = hasprimattrib(0, "pj_maillage") ? prim(0, "pj_maillage", @primnum) : "";
if (mai == "") mai = mid;
s@materiau_id = mid;
s@path = "/World/" + pj_nom_prim(couche) + "/" + pj_nom_prim(ent) + "/" + pj_nom_prim(mai);
s@usdmaterialpath = "/World/Looks/" + mid;          // liaison créée par SOP Import (bindmaterials = bind)
s@unreal_material = "/Game/PJ/Materials/MI_" + mid + ".MI_" + mid;
s@unreal_output_name = "SM_" + pj_nom_prim(ent);
"""

VEX_COULEURS = r"""
// Couleur de sommet du contrat (§ 3) : R usure, G salissure, B graine (0-1).
float u = hasprimattrib(0, "usure") ? prim(0, "usure", @primnum) : 0.0;
float s = hasprimattrib(0, "salissure") ? prim(0, "salissure", @primnum) : 0.0;
int gr = hasprimattrib(0, "graine") ? prim(0, "graine", @primnum) : 0;
v@Cd = set(u, s, (gr % 1000) / 999.0);
"""


def preparer_export(dossier):
    parms = [
        T.StringParmTemplate("couche_defaut", "Couche par défaut", 1, default_value=("PJ_Divers",),
                             help="Prim group sous /World quand pj_couche manque (PJ_Sol, PJ_Bordures…)."),
        T.StringParmTemplate("materiau_defaut", "Matériau par défaut", 1, default_value=("PJ_Neutre",),
                             help="materiau_id des faces qui n'en ont pas (signalé)."),
        T.MenuParmTemplate("calculer_normales", "Normales", menu_items=("si_absentes", "toujours", "jamais"),
                           menu_labels=("Calculer si absentes", "Toujours recalculer", "Garder celles d'entrée"),
                           default_value=0,
                           help="Normales par sommet de face (faceVarying) avec angle de rupture (E2)."),
        T.FloatParmTemplate("cusp", "Angle de rupture (°)", 1, default_value=(30.0,), min=0.0, max=180.0,
                            help="pj:cusp_deg du calque (30° par défaut, CONTRAT_EXPORT.md § 3)."),
        T.ToggleParmTemplate("uv_secours", "UV de secours en mètres si absentes", default_value=True,
                             help="Projection sur le plan dominant de chaque face (E3) ; une branche doit fournir ses UV."),
        T.ToggleParmTemplate("couleurs", "Couleur de sommet (usure, salissure, graine)", default_value=False),
        T.ToggleParmTemplate("vers_zup", "Passer en Z haut (USD)", default_value=True,
                             help="Transform rx = +90° : (x, y, z) Houdini -> (x, −z, y) = repère local Z haut."),
    ]
    sub = O.sous_reseau("pj_preparer_export")
    sub.setParmTemplateGroup(T.ParmTemplateGroup(parms))
    ent = sub.indirectInputs()[0]
    ver = O.wrangle(sub, "verifier", VEX_VERIFIER, "detail", ent)
    net = sub.createNode("clean", "nettoyer")
    net.setInput(0, ver)
    net.parm("fusepts").set(0)
    net.parm("deldegengeo").set(1)
    net.parm("delunusedpts").set(1)
    net.parm("orientpoly").set(0)
    nor = sub.createNode("normal", "normales")
    nor.setInput(0, net)
    nor.parm("type").set("typevertex")                       # normales par sommet de face (E2)
    nor.parm("cuspangle").setExpression('ch("../cusp")')
    sw_n = sub.createNode("switch", "choix_normales")
    sw_n.setInput(0, net)
    sw_n.setInput(1, nor)
    sw_n.parm("input").setExpression(
        'if(ch("../calculer_normales") == 1, 1, if(ch("../calculer_normales") == 2, 0, '
        'if(hasvertexattrib(opinputpath(".", 0), "N") || haspointattrib(opinputpath(".", 0), "N"), 0, 1)))')
    uv = O.wrangle(sub, "uv_secours", VEX_UV_SECOURS, "sommet", sw_n)
    sw_uv = sub.createNode("switch", "choix_uv")
    sw_uv.setInput(0, sw_n)
    sw_uv.setInput(1, uv)
    sw_uv.parm("input").setExpression(
        'ch("../uv_secours") && !hasvertexattrib(opinputpath(".", 0), "uv") && '
        '!haspointattrib(opinputpath(".", 0), "uv")')
    che = O.wrangle(sub, "chemins", VEX_CHEMINS, "primitive", sw_uv, bibliotheques=("pj_repere.h",))
    coul = O.wrangle(sub, "couleurs", VEX_COULEURS, "primitive", che)
    sw_c = sub.createNode("switch", "choix_couleurs")
    sw_c.setInput(0, che)
    sw_c.setInput(1, coul)
    sw_c.parm("input").setExpression('ch("../couleurs")')
    zup = sub.createNode("xform", "vers_zup")
    zup.setInput(0, sw_c)
    zup.parm("rx").setExpression('if(ch("../vers_zup"), 90, 0)')
    att = sub.createNode("attribdelete", "garder_attributs")
    att.setInput(0, zup)
    att.parm("negate").set(1)                                # supprime tout sauf :
    att.parm("ptdel").set("uv")
    att.parm("vtxdel").set("N uv")
    att.parm("primdel").set("path usdmaterialpath materiau_id unreal_material unreal_output_name Cd")
    att.parm("dtldel").set("")
    grp = sub.createNode("groupdelete", "retirer_groupes")
    grp.setInput(0, att)
    grp.parm("group1").set("*")
    O.sortie(sub, grp, 0, "sortie")
    O.ranger(sub)
    return O.creer_hda(sub, "preparer_export", "PJ Préparer l'export USD", parms, dossier, entrees=(1, 1),
                       sorties=1,
                       aide="Prépare les maillages d'une branche pour SOP Import selon le contrat pj_usd/0.1 : "
                            "nettoyage, normales à angle de rupture (E2), UV en mètres (E3), chemins "
                            "/World/<couche>/<entité>/<maillage> (E6), matériau /World/Looks/<materiau_id> (E5), "
                            "attributs Unreal, passage en Z haut.",
                       icone="SOP_xform", etiquettes_entrees=("Maillages (Y haut)",))


# ------------------------------------------------------------------------------------------------ pj::exporter_points
VEX_POINTS_LOCAL = r"""
// Repère local Z haut du contrat pj_points/0.1 (§ 7) : p, q [x, y, z, w] (w >= 0), rpy_deg (ZYX intrinsèques), s.
v@pj_p = pj_vers_local(@P);
vector4 q = {0, 0, 0, 1};
if (haspointattrib(0, "orient")) q = p@orient;
vector4 ql = pj_quat_vers_local(q);
p@pj_q = ql;
v@pj_rpy = pj_rpy_local(ql);
vector s = {1, 1, 1};
if (haspointattrib(0, "scale")) s = v@scale;
if (haspointattrib(0, "pscale")) s *= f@pscale;
v@pj_s = s;
"""

MODULE_POINTS = r'''"""pj::exporter_points : sérialisation pj_points/0.1 (Python SOP) et écriture (bouton, pilote)."""
import json
import os

import hou

REPERE = "local (L93 − O, z = NGF − 216,30), m, Z haut"
CONVENTION_RPY = ("rpy_deg = [r, p, y] ZYX intrinsèques, R = Rz(y)·Ry(p)·Rx(r), rotations directes (p > 0 abaisse "
                  "l'avant +X ; y trigo depuis +x) : convention de recon/pcg/ue/pj_tools/pj_tools/repere.py ; UE : "
                  "Rotator(roll = r, pitch = −p, yaw = −y) ; q = [x, y, z, w] prioritaire")


def _r(v, n):
    return [round(float(x), n) + 0.0 for x in v]


def serialiser(sop):
    """Détail pj_points_json : texte JSON du fichier (une ligne par point, tri par id)."""
    hda = sop.parent()
    geo = sop.geometry()
    pa = {a.name() for a in geo.pointAttribs()}
    def val(p, nom, defaut):
        return p.attribValue(nom) if nom in pa else defaut
    pts = []
    for p in geo.points():
        ident = val(p, "id", "") or f"pt{p.number()}"
        asset = val(p, "asset", "") or val(p, "unreal_instance", "")
        d = {"id": ident, "asset": asset, "p": _r(p.attribValue("pj_p"), 4), "q": _r(p.attribValue("pj_q"), 6),
             "rpy_deg": _r(p.attribValue("pj_rpy"), 3), "s": _r(p.attribValue("pj_s"), 4),
             "graine": int(val(p, "graine", 0))}
        cd = val(p, "cd", ())
        d["cd"] = _r(cd, 4) if cd else []
        x = val(p, "x", {})
        if x:
            d["x"] = x
        pts.append(d)
    pts.sort(key=lambda d: d["id"])
    entete = {"schema": "pj_points/0.1", "famille": hda.evalParm("famille"),
              "source_hash": hda.evalParm("source_hash") or (geo.attribValue("pj_hash_description")
                                                             if geo.findGlobalAttrib("pj_hash_description") else ""),
              "repere": REPERE, "convention_rpy": CONVENTION_RPY, "pivot": hda.evalParm("pivot"),
              "bibliotheque": hda.evalParm("bibliotheque"), "cd": hda.evalParm("doc_cd"),
              "generateur": "pj::exporter_points::1.0 (Houdini 22)", "n": len(pts)}
    corps = json.dumps(entete, ensure_ascii=False)[:-1] + ',\n"points": [\n'
    corps += ",\n".join(json.dumps(d, ensure_ascii=False, sort_keys=False, separators=(",", ":")) for d in pts)
    corps += "\n]}\n"
    geo.addAttrib(hou.attribType.Global, "pj_points_json", "")
    geo.setGlobalAttribValue("pj_points_json", corps)


def ecrire(node):
    """Écrit le fichier pj_points/0.1 (bouton « Écrire » ou pilote fabriquer_hda.py) ; renvoie son chemin."""
    chemin = node.evalParm("fichier")
    geo = node.node("serialiser").geometry()
    texte = geo.attribValue("pj_points_json") if geo.findGlobalAttrib("pj_points_json") else ""
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.write(texte)
    return chemin
'''


def exporter_points(dossier):
    parms = [
        T.StringParmTemplate("famille", "Famille", 1, default_value=("bordures",),
                             help="Champ famille du fichier (bordures, symboles…)."),
        T.StringParmTemplate("fichier", "Fichier pj_points/0.1", 1,
                             default_value=("$HIP/fabrique_hda/points/bordures.json",),
                             string_type=T.stringParmType.FileReference, file_type=T.fileType.Any),
        T.StringParmTemplate("source_hash", "Hash de la description", 1, default_value=("",),
                             help="Vide : attribut de détail pj_hash_description de l'entrée."),
        T.StringParmTemplate("pivot", "Pivot des prototypes", 1,
                             default_value=("base centrée, +X vers l'avant (assets/bibliotheque.json)",)),
        T.StringParmTemplate("bibliotheque", "Bibliothèque", 1,
                             default_value=("asset = asset_id de assets/bibliotheque.json ou nom de prototype",)),
        T.StringParmTemplate("doc_cd", "Sens de cd", 1, default_value=("",)),
        T.ButtonParmTemplate("ecrire", "Écrire le fichier",
                             script_callback="hou.phm().ecrire(kwargs['node'])",
                             script_callback_language=T.scriptLanguage.Python),
    ]
    sub = O.sous_reseau("pj_exporter_points")
    sub.setParmTemplateGroup(T.ParmTemplateGroup(parms))
    ent = sub.indirectInputs()[0]
    loc = O.wrangle(sub, "vers_local", VEX_POINTS_LOCAL, "point", ent, bibliotheques=("pj_repere.h",))
    ser = sub.createNode("python", "serialiser")
    ser.setInput(0, loc)
    ser.parm("python").set("# Sérialisation pj_points/0.1 (module de l'HDA)\n"
                           "hou.pwd().parent().hdaModule().serialiser(hou.pwd())\n")
    O.sortie(sub, ser, 0, "sortie")
    O.ranger(sub)
    return O.creer_hda(sub, "exporter_points", "PJ Exporter les points (pj_points/0.1)", parms, dossier,
                       entrees=(1, 1), sorties=1, module_python=MODULE_POINTS,
                       aide="Convertit des points d'instances (Houdini Y haut : P, orient, scale, pscale, id, asset ou "
                            "unreal_instance, graine, cd, x) au format pj_points/0.1 du contrat (repère local Z haut, "
                            "q [x, y, z, w], rpy_deg) ; le texte est dans le détail pj_points_json, écrit par le bouton.",
                       icone="SOP_file", etiquettes_entrees=("Points d'instances",))


def construire(dossier=ICI):
    return [niveau_z(dossier), preparer_export(dossier), exporter_points(dossier)]


if __name__ == "__main__":
    for c in construire():
        print(c)
