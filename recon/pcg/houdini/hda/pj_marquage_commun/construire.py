"""Construit les HDA communes des marquages (agent F2) ; hython Houdini 22 :

    pj::gabarits_iisr::1.0    lecteur des gabarits normatifs (assets/specs/marquages_geometrie.json) -> polygones
    pj::marquage_solide::1.0  empreintes planes -> maillage statique : triangulation contrainte, extrusion 3 mm,
                              chanfrein 1 mm, drapé sur le nivellement (région de la pièce), UV en mètres, normales

    hython recon/pcg/houdini/hda/pj_marquage_commun/construire.py

Contrat d'entrée de pj::marquage_solide (README_HDA.md § 7) : polygones fermés plans (Y ignoré), une ou plusieurs
primitives par entité, attributs de primitive pj_entite (maillage / component USD), id, materiau_id, couleur, classe,
type, usure, couverture, graine ; partie / anneau (0 = extérieur, >= 1 = trou de la même partie) ; pj_surface = 1 pour
des faces déjà maillées (rubans de lignes) ; pj_region facultatif (région de nivellement imposée).
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import pj_marquage_outils as M  # noqa: E402

O = M.O
T = hou

# ============================================================================================ pj::gabarits_iisr
MODULE_GABARITS = r'''"""pj::gabarits_iisr : lecture des gabarits de assets/specs/marquages_geometrie.json (JSON -> polygones).
Seul code Python de l'HDA (lecture de fichier) ; repère du gabarit (x latéral droite, y longitudinal) -> Houdini (x, 0, -y)."""
import fnmatch
import hashlib
import json
import os

import hou

_CACHE = {}


def _lire(chemin):
    st = os.stat(chemin)
    cle = (st.st_mtime_ns, st.st_size)
    e = _CACHE.get(chemin)
    if e is None or e[0] != cle:
        with open(chemin, "rb") as f:
            b = f.read()
        e = (cle, json.loads(b), hashlib.sha256(b).hexdigest())
        _CACHE[chemin] = e
    return e[1], e[2]


def lire_gabarits(sop):
    hda = sop.parent()
    geo = sop.geometry()
    chemin = hou.text.expandString(hda.evalParm("spec")).replace("\\", "/")
    if not os.path.exists(chemin):
        raise hou.NodeError(f"spécification absente : {chemin}")
    d, h = _lire(chemin)
    motifs = hda.evalParm("filtre").split()
    for nom, typ, defaut in (("gabarit", "s", ""), ("famille", "s", ""), ("couleur", "s", ""), ("partie", "i", 0),
                             ("anneau", "i", 0), ("longueur_m", "f", 0.0), ("largeur_m", "f", 0.0),
                             ("aire_m2", "f", 0.0), ("origine", "s", ""), ("source", "s", "")):
        geo.addAttrib(hou.attribType.Prim, nom, defaut)
    for nom in sorted(d["gabarits"]):
        if motifs and not any(fnmatch.fnmatchcase(nom, m) for m in motifs):
            continue
        g = d["gabarits"][nom]
        anneaux = [(0, 0, g["polygone"])] + [(0, k + 1, t) for k, t in enumerate(g.get("trous", []))]
        k = 0
        for _, part in sorted((g.get("parties") or {}).items()):
            if isinstance(part, dict) and "polygone" in part:
                k += 1
                anneaux.append((k, 0, part["polygone"]))
                anneaux += [(k, j + 1, t) for j, t in enumerate(part.get("trous", []))]
        aire = g.get("aire_m2")
        if aire is None and isinstance(g.get("parties"), dict):
            aire = g["parties"].get("aire_totale_m2", 0.0)
        src = g.get("source") or {}
        for partie, anneau, r in anneaux:
            pts = [geo.createPoint() for _ in r]
            for p, c in zip(pts, r):
                p.setPosition((float(c[0]), 0.0, -float(c[1])))
            pr = geo.createPolygon()
            for p in pts:
                pr.addVertex(p)
            for a, v in (("gabarit", nom), ("famille", g.get("famille", "")), ("couleur", g.get("couleur", "")),
                         ("partie", partie), ("anneau", anneau), ("longueur_m", float(g.get("longueur_m") or 0)),
                         ("largeur_m", float(g.get("largeur_m") or 0)), ("aire_m2", float(aire or 0)),
                         ("origine", g.get("origine", "")),
                         ("source", (src.get("texte", "") + (f" p. {src['page']}" if src.get("page") else "")))):
                pr.setAttribValue(a, v)
    geo.addAttrib(hou.attribType.Global, "pj_spec_hash", "")
    geo.setGlobalAttribValue("pj_spec_hash", h)
    geo.addAttrib(hou.attribType.Global, "pj_spec_schema", "")
    geo.setGlobalAttribValue("pj_spec_schema", str(d.get("schema", "")))
'''

VEX_GABARITS_CONTROLE = r"""
// Contrôle des gabarits : aire calculée (anneaux extérieurs - trous) comparée à aire_m2 de la spécification
// (repere.polygones : extérieur trigonométrique, trous horaires ; tolérance 1 %). Attribut de détail pj_gabarits_ecarts.
int np = nprimitives(0);
dict aires;
for (int pr = 0; pr < np; pr++) {
    string g = prim(0, "gabarit", pr);
    float a = abs(pj_m_aire(0, pr)) * (prim(0, "anneau", pr) > 0 ? -1.0 : 1.0);
    float v = 0;
    if (isvalidindex(aires, g)) v = aires[g];
    aires[g] = v + a;
}
string ecarts[];
string ks[] = keys(aires);
ks = sort(ks);
foreach (string g; ks) {
    int pr = findattribval(0, "prim", "gabarit", g);
    float ref = prim(0, "aire_m2", pr);
    float a = aires[g];
    if (ref > 0 && abs(a - ref) > 0.01 * ref) append(ecarts, sprintf("%s : aire %.4f m2, spec %.4f m2", g, a, ref));
}
s[]@pj_gabarits_ecarts = ecarts;
i@pj_gabarits_n = len(ks);
"""


def gabarits_iisr(dossier):
    parms = [
        T.StringParmTemplate("spec", "Spécification des marquages", 1, default_value=(M.SPEC_DEFAUT,),
                             string_type=T.stringParmType.FileReference, file_type=T.fileType.Any,
                             help="assets/specs/marquages_geometrie.json (gabarits IISR 7e partie, annexes B et D)."),
        T.StringParmTemplate("filtre", "Filtre de gabarits", 1, default_value=("",),
                             help="Motifs fnmatch séparés par des espaces (TD TA* VELO) ; vide : tous."),
    ]
    sub = O.sous_reseau("pj_gabarits_iisr")
    sub.setParmTemplateGroup(T.ParmTemplateGroup(parms))
    lire = sub.createNode("python", "lire_gabarits")
    lire.parm("python").set("# Gabarits normatifs (module de l'HDA : lecture JSON)\n"
                            "hou.pwd().parent().hdaModule().lire_gabarits(hou.pwd())\n")
    ctl = M.wrangle_m(sub, "controle_aires", VEX_GABARITS_CONTROLE, "detail", lire)
    out = sub.createNode("null", "GABARITS")
    out.setInput(0, ctl)
    O.sortie(sub, out, 0, "sortie")
    O.ranger(sub)
    return O.creer_hda(sub, "gabarits_iisr", "PJ Gabarits IISR (marquages)", parms, dossier, entrees=(0, 0),
                       sorties=1, module_python=MODULE_GABARITS, icone="SOP_file",
                       aide="Lit les gabarits normatifs de assets/specs/marquages_geometrie.json (flèches TD, TAD, TAG, "
                            "TD_TAD, TD_TAG, RAB_*, triangles CEDEZ, figurine VELO, damiers) : un polygone par anneau "
                            "dans le repère du gabarit (x latéral à droite, y dans le sens de circulation) placé en "
                            "Houdini (x, 0, −y) ; attributs gabarit, partie, anneau (trous ≥ 1), dimensions, source.",
                       etiquettes_sorties=("Gabarits (polygones)",))


# ============================================================================================ pj::marquage_solide
ATTRIBUTS_GARDES = ("id pj_entite pj_maillage materiau_id couleur classe type usure couverture graine pj_region "
                    "pj_surface partie anneau region_niveau src conf pj_coupures_auto pj_marches_ambigues")

VEX_DEFAUTS = r"""
// Attributs attendus (README_HDA.md § 7) : valeurs par défaut quand une entrée tracée à la main ne les porte pas.
if (s@pj_entite == "") s@pj_entite = s@id != "" ? s@id : sprintf("piece_%d", @primnum);
if (!hasprimattrib(0, "pj_region")) i@pj_region = -1;
if (!hasprimattrib(0, "pj_surface")) i@pj_surface = 0;
if (!hasprimattrib(0, "partie")) i@partie = 0;
if (!hasprimattrib(0, "anneau")) i@anneau = 0;
if (s@materiau_id == "") s@materiau_id = "PJ_Peinture_" + (s@couleur != "" ? s@couleur : "blanc") + "_u1";
"""

VEX_APLATIR = r"""
// Empreintes posées à plat sous le sol : le dessus sera à +épaisseur, les flancs descendent à -enfouissement
// (le drapé décale ensuite chaque sommet de l'altitude du sol sous lui).
@P.y = -ch("../enfouissement");
"""

VEX_ANNEAUX = r"""
// Orientation des anneaux avant Triangulate 2D (règle d'enroulement non nul) : extérieurs trigonométriques (vus de
// dessus, repère local), trous horaires (repere.polygones de marquages_geometrie.json) : parties qui se recouvrent
// réunies, trous retirés, quel que soit le sens de saisie.
float a = pj_m_aire(0, @primnum);
int trou = i@anneau > 0;
if ((!trou && a < 0) || (trou && a > 0)) setprimgroup(0, "a_retourner", @primnum, 1);
"""

VEX_TROUS = r"""
// Triangle gardé s'il est dans l'anneau extérieur d'une partie et hors des trous de cette partie : réunion des parties
// (roues de la figurine vélo, segments d'un zigzag, bandes qui se touchent), trous respectés (CEDEZ, PMR, chiffres).
int pts[] = primpoints(0, @primnum);
vector c = 0;
foreach (int p; pts) c += point(0, "P", p);
c /= max(1, len(pts));
float x = c.x, y = -c.z;
int np = nprimitives(1);
int garde = 0;
for (int r = 0; r < np && !garde; r++) {
    if (prim(1, "anneau", r) != 0) continue;
    if (!pj_m_dans(1, r, x, y)) continue;
    int part = prim(1, "partie", r);
    int trou = 0;
    for (int h = 0; h < np; h++) {
        if (prim(1, "anneau", h) > 0 && prim(1, "partie", h) == part && pj_m_dans(1, h, x, y)) { trou = 1; break; }
    }
    if (!trou) garde = 1;
}
if (!garde) removeprim(0, @primnum, 1);
"""

VEX_ATTRIBUTS = r"""
// Attributs de l'entité recopiés depuis son anneau extérieur (Triangulate 2D ne garde pas les attributs de primitive).
int r = findattribval(1, "prim", "anneau", 0);
if (r < 0) r = 0;
s@id = prim(1, "id", r);
s@pj_entite = prim(1, "pj_entite", r);
s@materiau_id = prim(1, "materiau_id", r);
s@couleur = prim(1, "couleur", r);
s@classe = prim(1, "classe", r);
s@type = prim(1, "type", r);
s@pj_maillage = prim(1, "pj_maillage", r);
f@usure = prim(1, "usure", r);
f@couverture = prim(1, "couverture", r);
i@graine = prim(1, "graine", r);
i@pj_region = prim(1, "pj_region", r);
i@pj_surface = 0;
"""

VEX_ORIENTER = r"""
// Faces du dessus vers +Y (Triangulate 2D les rend vers -Y dans le plan XZ).
if (prim_normal(0, @primnum, {0.5, 0.5, 0}).y < 0) setprimgroup(0, "a_inverser", @primnum, 1);
"""

VEX_REGION_SOMMETS = r"""
// Région de nivellement propriétaire du nœud le plus proche (TQ-SOL-013 : un seul modèle de Z).
float g[] = pj_niv_grille(1);
i@pj_reg = pj_niv_region(g, @P.x, -@P.z);
"""

VEX_REGION_PIECES = r"""
// Région de drapé de chaque pièce (composante connexe) : région majoritaire de ses sommets, sauf région imposée
// (pj_region >= 0) en mode « attribut ». Une pièce est drapée dans UNE région : elle ne suit jamais une marche de
// bordure (TQ-SOL-013, CF-26 ; MQ-DET-010 : marques sur la chaussée, jamais sur une bordure).
string mode = chs("../mode_region");
int np = nprimitives(0);
dict cpt;
for (int pr = 0; pr < np; pr++) {
    int pc = prim(0, "pj_piece", pr);
    int pts[] = primpoints(0, pr);
    foreach (int p; pts) {
        int r = point(0, "pj_reg", p);
        if (r < 0) continue;
        string k = sprintf("%d:%d", pc, r);
        int c = 0;
        if (isvalidindex(cpt, k)) c = cpt[k];
        cpt[k] = c + 1;
    }
}
dict meil;
dict nmax;
string ks[] = keys(cpt);
ks = sort(ks);
foreach (string k; ks) {
    string a[] = split(k, ":");
    string pc = a[0];
    int c = cpt[k];
    int m = -1;
    if (isvalidindex(nmax, pc)) m = nmax[pc];
    if (c > m) { nmax[pc] = c; meil[pc] = atoi(a[1]); }
}
for (int pr = 0; pr < np; pr++) {
    int imp = prim(0, "pj_region", pr);
    if (mode == "attribut" && imp >= 0) continue;
    string pc = itoa(prim(0, "pj_piece", pr));
    int r = -1;
    if (isvalidindex(meil, pc)) r = meil[pc];
    setprimattrib(0, "pj_region", pr, mode == "point" ? -1 : r);
}
"""

VEX_ARETES_DESSUS = r"""
// Arêtes vives du dessus (entre une face du dessus et un flanc) : groupe bord_dessus, chanfreinées ensuite.
int nh = nvertices(0);
for (int h = 0; h < nh; h++) {
    if (!hedge_isvalid(0, h) || !hedge_isprimary(0, h)) continue;
    int h2 = hedge_nextequiv(0, h);
    if (h2 == h) continue;
    int p1 = hedge_prim(0, h);
    int p2 = hedge_prim(0, h2);
    if (inprimgroup(0, "dessus", p1) != inprimgroup(0, "dessus", p2))
        setedgegroup(0, "bord_dessus", hedge_srcpoint(0, h), hedge_dstpoint(0, h), 1);
}
"""

VEX_COMPLETER = r"""
// Faces créées par le chanfrein sans attributs (coins de PolyBevel) : attributs d'une face voisine (sommet partagé).
if (s@pj_entite != "") return;
int pts[] = primpoints(0, @primnum);
foreach (int p; pts) {
    int prs[] = pointprims(0, p);
    foreach (int q; prs) {
        if (q == @primnum) continue;
        string e = prim(0, "pj_entite", q);
        if (e == "") continue;
        s@pj_entite = e;
        s@id = prim(0, "id", q);
        s@materiau_id = prim(0, "materiau_id", q);
        s@couleur = prim(0, "couleur", q);
        s@classe = prim(0, "classe", q);
        s@type = prim(0, "type", q);
        s@pj_maillage = prim(0, "pj_maillage", q);
        f@usure = prim(0, "usure", q);
        f@couverture = prim(0, "couverture", q);
        i@graine = prim(0, "graine", q);
        i@pj_region = prim(0, "pj_region", q);
        i@pj_piece = prim(0, "pj_piece", q);
        return;
    }
}
"""

VEX_DRAPER = r"""
// Drapé (TQ-SOL-013, CF-26) : chaque sommet est décalé de l'altitude du modèle de nivellement sous lui, lue dans la
// région de sa pièce (pj_niv_z : bilinéaire restreinte à la région, prolongements z1/z2). Les flancs restent
// verticaux (mêmes (x, y) en haut et en bas). Hors région : altitude propre du nœud (pj_hors_region).
// Franchissement : écart à l'altitude du nœud propriétaire > seuil (marque à cheval sur une marche de bordure).
// Sol fabriqué (entrée 3, pj::sol) : l'altitude est ensuite celle du sol réellement maillé sous le sommet (rayon
// vertical autour du modèle, région de la pièce d'abord ; pj_m_z_sol) : pj::sol modifie le modèle par ses raccords
// aux bordures et l'adoucissement des marches (p99 11,5 cm), la peinture drapée sur le seul modèle était enterrée ou
// flottante (ML-0405 à −66 mm ; TQ-MQG-005, revues du 11/10/2026).
float g[] = pj_niv_grille(1);
if (g[PJ_G_OK] < 0.5) { i@pj_hors_region = 0; i@pj_franchit = 0; f@pj_z_sol = 0; return; }
int prs[] = pointprims(0, @ptnum);
int r = len(prs) > 0 ? prim(0, "pj_region", prs[0]) : -1;
float x = @P.x, y = -@P.z;
float zp = pj_niv_z(g, x, y, -1);
float z = r >= 0 ? pj_niv_z(g, x, y, r) : zp;
i@pj_hors_region = 0;
if (z < 0.5 * PJ_NIV_ABSENT) { z = zp; i@pj_hors_region = 1; }
if (z < 0.5 * PJ_NIV_ABSENT) { z = 0; i@pj_hors_region = 2; }
i@pj_franchit = (zp > 0.5 * PJ_NIV_ABSENT && abs(z - zp) > ch("../seuil_franchissement")) ? 1 : 0;
f@pj_z_modele = z;
i@pj_sur_sol = 0;
if (chi("../sur_sol") && nprimitives(2) > 0) {
    int ok = 0;
    float zs = pj_m_z_sol(2, x, y, z, chf("../portee_sol"), r, ok);
    if (ok > 0) { z = zs; i@pj_sur_sol = ok; }
}
f@pj_z_sol = z;
@P.y += z;
"""

VEX_UV = r"""
// UV en mètres (contrat pj_usd/0.1, E3) : dessus (|n.z| > 0,9) projeté en (x, y) locaux, ancré au monde (motifs
// d'usure continus d'un tiret à l'autre) ; flancs et chanfreins : base orthonormée de la face (u horizontal le long
// de la face, v dans la pente) : jamais de projection de dessus sur une face verticale.
vector n = normalize(prim_normal(0, @primnum, {0.5, 0.5, 0}));
vector P = point(0, "P", vertexpoint(0, @vtxnum));
vector l = set(P.x, -P.z, P.y);
vector nl = set(n.x, -n.z, n.y);
if (abs(nl.z) > 0.9) {
    v@uv = set(l.x, l.y, 0);
} else {
    vector t = normalize(set(-nl.y, nl.x, 0));
    vector b = normalize(cross(nl, t));
    v@uv = set(dot(l, t), dot(l, b), 0);
}
"""

VEX_SORTIE = r"""
// Attributs du contrat d'une branche (README_HDA.md § 4) : couche, entité (component USD), maillage ; attributs
// Houdini Engine pour un usage direct dans Unreal (un StaticMesh par entité, MI_<materiau_id>, sans ombre portée :
// 3 mm de peinture).
s@pj_couche = chs("../couche");
if (s@pj_maillage == "") s@pj_maillage = s@materiau_id;
s@unreal_material = "/Game/PJ/Materials/MI_" + s@materiau_id + ".MI_" + s@materiau_id;
s@unreal_output_name = "SM_" + re_replace("[^A-Za-z0-9_]", "_", s@pj_entite);
i@unreal_uproperty_CastShadow = ch("../ombre");
if (@primnum == 0) setdetailattrib(0, "unreal_split_attr", "pj_entite");
"""

VEX_CONTROLES = r"""
// Contrôles (détail pj_marquage_controles) : pièces, triangles, aire du dessus, sommets hors région, pièces qui
// franchissent une marche du modèle (MQ-DET-010 : jamais sur une bordure ; seuil « Seuil de franchissement »).
int np = nprimitives(0);
float aire = 0;
dict pieces;
dict franch;
for (int pr = 0; pr < np; pr++) {
    string pc = itoa(prim(0, "pj_piece", pr));
    pieces[pc] = 1;
    if (inprimgroup(0, "dessus", pr)) aire += primintrinsic(0, "measuredarea", pr);
}
int hors = 0, sur_sol = 0;
for (int p = 0; p < npoints(0); p++) {
    if (point(0, "pj_hors_region", p) > 0) hors++;
    if (point(0, "pj_sur_sol", p) > 0) sur_sol++;
    if (point(0, "pj_franchit", p) > 0) {
        int prs[] = pointprims(0, p);
        franch[prim(0, "pj_entite", prs[0])] = 1;
    }
}
string fr[] = keys(franch);
fr = sort(fr);
dict d;
d["pieces"] = len(keys(pieces));
d["primitives"] = np;
d["points"] = npoints(0);
d["aire_dessus_m2"] = aire;
d["sommets_hors_region"] = hors;
d["sommets_sur_sol_fabrique"] = sur_sol;
d["entites_franchissement"] = fr;
string rg[] = {"TQ-SOL-013", "CF-26", "MQ-DET-010", "TQ-MQG-005"};
d["regles"] = rg;
d@pj_marquage_controles = d;
"""


def marquage_solide(dossier):
    forme = [
        T.FloatParmTemplate("epaisseur", "Épaisseur au-dessus du sol (m)", 1, default_value=(0.003,), min=0.0,
                            max=0.02, help="Dessus de la peinture au-dessus du sol (marquages_geometrie.repere.gabarits : "
                                           "posé à +3 mm)."),
        T.FloatParmTemplate("enfouissement", "Enfouissement des flancs (m)", 1, default_value=(0.005,), min=0.0,
                            max=0.05, help="Les flancs descendent sous le sol : aucun jour entre peinture et chaussée "
                                           "même si le maillage du sol s'écarte de quelques mm du modèle."),
        T.FloatParmTemplate("chanfrein", "Chanfrein des arêtes du dessus (m)", 1, default_value=(0.001,), min=0.0,
                            max=0.005, help="PolyBevel sur les arêtes vives du dessus (0 : aucun)."),
        T.FloatParmTemplate("pas_maillage", "Pas du maillage de drapé (m)", 1, default_value=(0.25,), min=0.02,
                            max=5.0, help="Longueur d'arête cible de Triangulate 2D (raffinement) : le dessus suit le "
                                          "bombement et le dévers de la chaussée."),
    ]
    drape = [
        T.ToggleParmTemplate("draper", "Draper sur le nivellement (entrée 2)", default_value=True,
                             help="Sans entrée 2 ou décoché : maillage à plat (prototype de bibliothèque)."),
        T.MenuParmTemplate("mode_region", "Région de drapé", menu_items=("piece", "attribut", "point"),
                           menu_labels=("Région majoritaire de la pièce", "Attribut pj_region (sinon majoritaire)",
                                        "Région de chaque sommet (suit les marches)"), default_value=0,
                           help="Une pièce drapée dans une seule région ne franchit jamais une marche de bordure "
                                "(TQ-SOL-013)."),
        T.FloatParmTemplate("seuil_franchissement", "Seuil de franchissement (m)", 1, default_value=(0.02,), min=0.0,
                            max=0.2, help="Écart entre l'altitude de la pièce et celle du nœud propriétaire au-delà "
                                          "duquel l'entité est signalée (détail pj_marquage_controles)."),
        T.ToggleParmTemplate("sur_sol", "Draper sur le sol fabriqué (entrée 3)", default_value=True,
                             help="Altitude lue sur le sol maillé par pj::sol (rayon vertical, région de la pièce "
                                  "d'abord) au lieu du seul modèle de nivellement (TQ-MQG-005). Sans entrée 3 : modèle."),
        T.FloatParmTemplate("portee_sol", "Portée de la recherche du sol (m)", 1, default_value=(0.4,), min=0.01,
                            max=2.0, help="Demi-hauteur du rayon vertical centré sur l'altitude du modèle."),
    ]
    sortie = [
        T.StringParmTemplate("couche", "Couche USD (pj_couche)", 1, default_value=(M.COUCHE,)),
        T.FloatParmTemplate("cusp", "Angle de rupture des normales (°)", 1, default_value=(30.0,), min=0.0, max=180.0,
                            help="Normal SOP par sommet (contrat E2, pj:cusp_deg)."),
        T.ToggleParmTemplate("ombre", "Ombre portée dans Unreal", default_value=False,
                             help="unreal_uproperty_CastShadow (Houdini Engine)."),
    ]
    parms = [T.FolderParmTemplate("f_forme", "Forme", parm_templates=forme, folder_type=T.folderType.Tabs),
             T.FolderParmTemplate("f_drape", "Drapé", parm_templates=drape, folder_type=T.folderType.Tabs),
             T.FolderParmTemplate("f_sortie", "Sortie", parm_templates=sortie, folder_type=T.folderType.Tabs)]
    sub = O.sous_reseau("pj_marquage_solide")
    sub.setParmTemplateGroup(T.ParmTemplateGroup(parms))
    ent, niv, sol_fab = sub.indirectInputs()[0], sub.indirectInputs()[1], sub.indirectInputs()[2]

    garder = sub.createNode("attribdelete", "garder_attributs")
    garder.setInput(0, ent)
    garder.parm("negate").set(1)                      # supprime tout sauf la liste (géométrie légère)
    garder.parm("ptdel").set("")
    garder.parm("vtxdel").set("")
    garder.parm("primdel").set(ATTRIBUTS_GARDES)
    garder.parm("dtldel").set("pj_*")
    defauts = M.wrangle_m(sub, "defauts", VEX_DEFAUTS, "primitive", garder, bibliotheques=False)
    aplat = M.wrangle_m(sub, "aplatir", VEX_APLATIR, "point", defauts, bibliotheques=False)
    surf = M.blast(sub, "faces_maillees", aplat, "@pj_surface==1", garder=True)
    surf_tri = sub.createNode("divide", "trianguler_faces")
    surf_tri.setInput(0, surf)
    surf_tri.parm("convex").set(1)
    surf_tri.parm("usemaxsides").set(1)
    surf_tri.parm("numsides").set(3)
    emp0 = M.blast(sub, "empreintes", aplat, "@pj_surface==1", garder=False)
    ann = M.wrangle_m(sub, "orienter_anneaux", VEX_ANNEAUX, "primitive", emp0)
    ret = sub.createNode("reverse", "retourner_anneaux")
    ret.setInput(0, ann)
    ret.parm("group").set("a_retourner")
    emp = sub.createNode("groupdelete", "oublier_retournement")
    emp.setInput(0, ret)
    emp.parm("group1").set("a_retourner")

    def corps(debut):
        tri = sub.createNode("triangulate2d::3.0", "trianguler")
        tri.setInput(0, debut)
        for p, v in (("useconstrpolys", 1), ("constrpolys", "*"), ("removefromconstrpolys", 1), ("refine", 1),
                     ("trianglesize", "settargetedgelength"), ("maxnewpts", 200000), ("removeduplicatepoints", 1),
                     ("allowconstrsplit", 1)):
            tri.parm(p).set(v)
        tri.parm("targetedgelength").setExpression('ch("../pas_maillage")')
        trous = M.wrangle_m(sub, "retirer_trous", VEX_TROUS, "primitive", tri, entrees=(debut,))
        att = M.wrangle_m(sub, "attributs_entite", VEX_ATTRIBUTS, "primitive", trous, entrees=(debut,),
                          bibliotheques=False)
        return att

    _, fin = M.boucle_par_attribut(sub, emp, "pj_entite", corps, nom="par_entite")
    fus = sub.createNode("merge", "fusion")
    fus.setInput(0, fin)
    fus.setInput(1, surf_tri)
    ori = M.wrangle_m(sub, "orienter", VEX_ORIENTER, "primitive", fus, bibliotheques=False)
    inv = sub.createNode("reverse", "inverser")
    inv.setInput(0, ori)
    inv.parm("group").set("a_inverser")
    gd = sub.createNode("groupdelete", "oublier_inversion")
    gd.setInput(0, inv)
    gd.parm("group1").set("a_inverser")
    conn = sub.createNode("connectivity", "pieces")
    conn.setInput(0, gd)
    conn.parm("connecttype").set("prim")
    conn.parm("attribname").set("pj_piece")
    regs = M.wrangle_m(sub, "region_sommets", VEX_REGION_SOMMETS, "point", conn, entrees=(niv,))
    regp = M.wrangle_m(sub, "region_pieces", VEX_REGION_PIECES, "detail", regs, bibliotheques=False)
    ext = sub.createNode("polyextrude::2.0", "extruder")
    ext.setInput(0, regp)
    for p, v in (("splittype", "components"), ("outputback", 0), ("outputfront", 1), ("outputside", 1),
                 ("outputfrontgrp", 1), ("frontgrp", "dessus"), ("outputsidegrp", 1), ("sidegrp", "flancs"),
                 ("genuvs", 0)):
        ext.parm(p).set(v)
    ext.parm("dist").setExpression('ch("../epaisseur") + ch("../enfouissement")')
    ar = M.wrangle_m(sub, "aretes_dessus", VEX_ARETES_DESSUS, "detail", ext, bibliotheques=False)
    bev = sub.createNode("polybevel::3.0", "chanfrein")
    bev.setInput(0, ar)
    for p, v in (("group", "bord_dessus"), ("grouptype", "edges"), ("filletshape", "chamfer"), ("divisions", 1)):
        bev.parm(p).set(v)
    bev.parm("offset").setExpression('ch("../chanfrein")')
    comp = M.wrangle_m(sub, "completer_attributs", VEX_COMPLETER, "primitive", bev, bibliotheques=False)
    sw_b = M.interrupteur(sub, "choix_chanfrein", (ar, comp), 'ch("../chanfrein") > 0')
    drp = M.wrangle_m(sub, "draper", VEX_DRAPER, "point", sw_b, entrees=(niv, sol_fab))
    sw_d = M.interrupteur(sub, "choix_drape", (sw_b, drp), 'ch("../draper")')
    tri_f = sub.createNode("divide", "faces_planes")
    tri_f.setInput(0, sw_d)                           # triangles : faces planes après drapé (contrat § 3, E2 cohérent)
    tri_f.parm("convex").set(1)
    tri_f.parm("usemaxsides").set(1)
    tri_f.parm("numsides").set(3)
    uv = M.wrangle_m(sub, "uv_metres", VEX_UV, "sommet", tri_f, bibliotheques=False)
    nor = sub.createNode("normal", "normales")
    nor.setInput(0, uv)
    nor.parm("type").set("typevertex")
    nor.parm("cuspangle").setExpression('ch("../cusp")')
    srt = M.wrangle_m(sub, "attributs_sortie", VEX_SORTIE, "primitive", nor, bibliotheques=False)
    ctl = M.wrangle_m(sub, "controles", VEX_CONTROLES, "detail", srt, bibliotheques=False)
    net = sub.createNode("attribdelete", "nettoyer")
    net.setInput(0, ctl)
    net.parm("ptdel").set("pj_reg pj_franchit pj_sur_sol pj_z_modele")
    net.parm("primdel").set("pj_surface anneau partie")
    out = sub.createNode("null", "MAILLAGES")
    out.setInput(0, net)
    O.sortie(sub, out, 0, "sortie")
    O.ranger(sub)
    return O.creer_hda(sub, "marquage_solide", "PJ Marquage solide (empreintes -> maillage)", parms, dossier,
                       entrees=(1, 3), sorties=1, icone="SOP_polyextrude",
                       aide="Transforme des empreintes planes de marquage en maillages statiques : triangulation "
                            "contrainte (Triangulate 2D, trous et réunion des parties), extrusion de la peinture "
                            "(3 mm au-dessus du sol, flancs enfouis), chanfrein des arêtes du dessus, drapé sur le "
                            "modèle de nivellement dans la région de chaque pièce (TQ-SOL-013) puis sur le sol "
                            "fabriqué s'il est branché (TQ-MQG-005), UV en mètres, normales à angle de rupture.",
                       details_aide="== Entrées ==\n\n1. Empreintes : polygones fermés (pj_entite, id, materiau_id, "
                                    "partie, anneau, pj_surface).\n2. Nivellement (HeightField de pj::lire_description), "
                                    "facultatif.\n3. Sol fabriqué (sortie de pj::sol, Y haut), facultatif : la peinture "
                                    "suit le sol réellement maillé.\n\nContrat : recon/pcg/houdini/hda/README_HDA.md § 7.",
                       etiquettes_entrees=("Empreintes (polygones plans)", "Nivellement (HeightField)",
                                           "Sol fabriqué (facultatif)"),
                       etiquettes_sorties=("Maillages (Y haut)",))


def construire(dossier=ICI):
    return [gabarits_iisr(dossier), marquage_solide(dossier)]


if __name__ == "__main__":
    for c in construire():
        print(c)
