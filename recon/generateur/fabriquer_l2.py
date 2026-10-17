"""Lot L2 du pilote (hython) : sol, bordures et caniveaux fabriqués sur le modèle de nivellement unique.

Appelé par fabriquer_generateur.py (option --l2) après la chaîne du lot L1 :
    rg::nivellement (modèle de Z unique, files de bordures)  -> rg::sol (nappe étanche, BEV)
                                                              -> rg::vers_entites -> pj::bordure, pj::caniveau
Écrit dans <sortie>/<scene>/l2/ (non versionné) :
    sol_points.npy (x, y, z, s, t : repère local Z haut), sol_faces.npy, sol_comptes.npy, sol_attributs.npy
    (z_type, section, bande, classe, matériau, visible par face) et sol_vocabulaire.json ;
    niveaux.json (sections du modèle de Z, files de bordures : pied, tête, vue, chaussée au droit de la face) ;
    heightfield.json (HeightField de nivellement, sortie 2 de rg::nivellement : descripteur, régions, empreintes) ;
    elements.json (éléments et joints de bordure et de caniveau posés : pj::bordure / pj::caniveau, sortie 2) ;
    bev.json, vegetation.json ; mesures_l2.json (sondes verticales et rayons des joints, géométrie fabriquée) ;
    route_l2.usda (couches sol, BEV, bordures, caniveaux, Z haut, matériaux par materiau_id) ; manifest_l2.json.
Aucune date ni durée n'est écrite : deux exécutions donnent les mêmes octets.
"""
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

import hou

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[1]
sys.path.insert(0, str(ICI / "rendu"))
sys.path.insert(0, str(DEPOT / "recon" / "pcg" / "houdini" / "hda" / "commun"))
import pj_hda_outils as PJ  # noqa: E402
sys.path.insert(0, str(ICI))
from commun import determinisme as DET  # noqa: E402

HDAS_L2 = ("nivellement", "sol", "vers_entites")
VEX_RG = ICI / "hda" / "commun" / "vex"
VEX_PJ = DEPOT / "recon" / "pcg" / "houdini" / "hda" / "commun" / "vex"

# Contrôle du HeightField (sortie 2 de rg::nivellement) : Z lu par pj_niv_z (bibliothèque du lecteur, inchangée) aux
# points des faces visibles de bande du sol, dans la région (nappe) de la bande, contre le Z du sol fabriqué.
VEX_CONTROLE_HF = r"""
f@ecart_hf = 0; i@hf_teste = 0; i@hf_absent = 0; i@hf_sous_bordure = 0;
float s = point(0, "s", @ptnum), t = point(0, "t", @ptnum);
float rampe = detail(2, "rg_rampe_plateau_pct");
int rang = -1, pr2 = -1;
float z0, z1, z2;
int n0, n1, n2;
string msg;
int prs[] = pointprims(0, @ptnum);
int ok = 0, kk = 0, bb = 0;
string rid = "";
foreach (int pr; prs)
    if (prim(0, "z_type", pr) == 0 && prim(0, "visible", pr) == 1) {
        ok = 1; rid = prim(0, "route", pr); kk = prim(0, "section", pr); bb = prim(0, "bande", pr);
    }
if (ok) {
    for (int q = 0; q < nprimitives(3); q++) {
        if (!inprimgroup(3, "echantillonnees", q)) continue;
        rang++;
        if (prim(3, "id", q) == rid) { pr2 = q; break; }
    }
    int sp = rg_point_section(2, rid, kk);
    if (!rg_hf_noeud(2, sp, rid, s, t, rampe, 0.0, z0, n0, z1, n1, z2, n2, msg)) error("%s", msg);
    // nappe de la bande du triangle (milieu de la bande) : un sommet au-delà de la frontière est sous une bordure
    float T[] = rg_t_limites(2, sp, s);
    float tm = (bb >= 0) ? 0.5 * (T[bb] + T[bb + 1]) : t;
    float y0, y1, y2;
    int m0, m1, m2;
    if (!rg_hf_noeud(2, sp, rid, s, tm, rampe, 0.0, y0, m0, y1, m1, y2, m2, msg)) error("%s", msg);
    if (m0 != n0) { i@hf_sous_bordure = 1; ok = 0; }
}
if (ok) {
    float g[] = pj_niv_grille(1);
    float zh = pj_niv_z(g, @P.x, -@P.z, 100 * rang + n0);
    i@hf_teste = 1;
    if (zh < -1e29) i@hf_absent = 1;
    else f@ecart_hf = zh - @P.y;
}
"""
VERSION_L2 = "fabriquer_l2/1.0 (lot L2)"


def _r(x, n=6):
    v = round(float(x), n)
    return 0.0 if v == 0 else v


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def installer_pj(forcer=False):
    """HDA pj::* du dépôt (installées telles quelles) et nouvelles versions du générateur (les anciennes restent
    intactes) : pj::caniveau::2.0 (recon/generateur/hda/pj_caniveau_v2 : lecture des intervalles du caniveau corrigée),
    pj::caniveau::2.1 (pj_caniveau_v2_1 : pièce gardée dès 5 mm à une borne d'intervalle, avaloir sans trou) ;
    pj::bordure::2.0 (recon/generateur/hda/pj_bordure_v2 : angle vif confondu avec un changement d'intervalle posé en
    onglet, pièces d'angle des avancées et des îlots ; étape 1, correction après contrôle)."""
    import importlib.util
    PJ.installer_tout()
    sigs = {}
    for dossier, fichier, cle in (("pj_caniveau_v2", "pj_caniveau_2.0.hdalc", "pj::caniveau::2.0"),
                                  ("pj_caniveau_v2_1", "pj_caniveau_2.1.hdalc", "pj::caniveau::2.1"),
                                  ("pj_bordure_v2", "pj_bordure_2.0.hdalc", "pj::bordure::2.0")):
        d = ICI / "hda" / dossier
        cible = d / fichier
        if forcer or not cible.exists():
            spec = importlib.util.spec_from_file_location(f"construire_{dossier}", d / "construire.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cible = mod.construire(d)
        else:
            hou.hda.installFile(str(cible))
        f = list(Path(cible).glob("*/RgSignature"))
        sigs[cle] = f[0].read_text(encoding="utf-8").strip() if f else ""
    return sigs


def reseau(obj, lire, graphe, nom_type):
    niv = obj.createNode(nom_type("nivellement"), "nivellement")
    for k, (n, o) in enumerate(((graphe, 0), (lire, 4), (lire, 3), (lire, 2))):
        niv.setInput(k, n, o)
    sol = obj.createNode(nom_type("sol"), "sol")
    sol.setInput(0, graphe, 0)
    sol.setInput(1, niv, 0)
    ent = obj.createNode(nom_type("vers_entites"), "vers_entites")
    ent.setInput(0, niv, 0)
    ent.setInput(1, lire, 4)
    ent.setInput(2, graphe, 0)
    chf = obj.createNode("attribwrangle", "controle_heightfield")
    chf.parm("class").set(2)
    chf.parm("vex_precision").set("64")
    chf.parm("snippet").set("".join((VEX_RG / f).read_text(encoding="utf-8") + chr(10) for f in
                                    ("rg_geometrie.h", "rg_niveau.h"))
                            + (VEX_PJ / "pj_niveau.h").read_text(encoding="utf-8") + chr(10) + VEX_CONTROLE_HF)
    chf.setInput(0, sol, 0)
    chf.setInput(1, niv, 1)
    chf.setInput(2, niv, 0)
    chf.setInput(3, graphe, 0)
    bor = obj.createNode("pj::bordure::2.0", "bordures")
    bor.setInput(0, ent, 0)
    # pj::caniveau::2.1 (correction après le second contrôle : l'avaloir remplace le caniveau, pièce gardée dès 5 mm à
    # la borne de l'intervalle, sans trou devant l'avaloir) ; 2.0 gardée intacte
    can = obj.createNode("pj::caniveau::2.1", "caniveaux")
    can.setInput(0, ent, 0)
    # contrat de branche (README_HDA § 4) : entrée 2 = HeightField de nivellement ; le pied reste lu sur le profil en
    # long niv_z_pied (paramètre altitude = profil, défaut des HDA pj), tiré du même modèle de Z
    for n in (bor, can):
        n.setInput(1, niv, 1)
    # jitter de hauteur des éléments : 1 mm (défaut pj : 2 mm) pour rester dans la tolérance de TQ-SOL-013 (6)
    # (trottoir = tête − 4 mm ± 2 mm) et de la vue (± 5 mm) ; lacet, latéral et roulis inchangés
    for n in (bor, can):
        n.parm("jit_hauteur_mm").set(1.0)
    obj.layoutChildren()
    return {"nivellement": niv, "sol": sol, "vers_entites": ent, "bordures": bor, "caniveaux": can,
            "controle_heightfield": chf}


def cuire(noeuds, scene):
    for nom in ("nivellement", "sol", "vers_entites", "bordures", "caniveaux", "controle_heightfield"):
        n = noeuds[nom]
        try:
            n.cook(force=True)
        except hou.OperationFailed:
            pass
        err = [f"{c.path()} : {e}" for c in (n,) + n.allSubChildren() for e in c.errors()]
        if err:
            raise SystemExit(f"{scene} : erreurs de cuisson (lot L2)" + chr(10) + chr(10).join(err[:20]))


# -------------------------------------------------------------------------------------------------- exports
def _loc(p):
    return (p[0], -p[2], p[1])


def exporter_sol(geo, dossier):
    P = np.array(geo.pointFloatAttribValues("P"), dtype=np.float64).reshape(-1, 3)
    S = np.array(geo.pointFloatAttribValues("s"), dtype=np.float64)
    T = np.array(geo.pointFloatAttribValues("t"), dtype=np.float64)
    # + 0.0 : zéro signé ramené à +0,0 (t = −P.z vaut −0,0 ou +0,0 selon le processus sur les points de la référence,
    # même nombre : seul le signe du zéro variait, contrôle de déterminisme S10, S11)
    pts = np.column_stack([P[:, 0], -P[:, 2], P[:, 1], S, T]) + 0.0
    comptes, faces = [], []
    voc = {"classe": [], "materiau_id": [], "bande_id": []}
    idx = {k: {} for k in voc}
    attrs = []
    for pr in geo.prims():
        vs = [v.point().number() for v in pr.vertices()]
        comptes.append(len(vs))
        faces += vs
        ligne = [pr.attribValue("z_type"), pr.attribValue("section"), pr.attribValue("bande"), pr.attribValue("visible")]
        for k in ("classe", "materiau_id", "bande_id"):
            v = pr.attribValue(k)
            if v not in idx[k]:
                idx[k][v] = len(voc[k])
                voc[k].append(v)
            ligne.append(idx[k][v])
        attrs.append(ligne)
    np.save(dossier / "sol_points.npy", pts)
    np.save(dossier / "sol_faces.npy", np.array(faces, dtype=np.int32))
    np.save(dossier / "sol_comptes.npy", np.array(comptes, dtype=np.int32))
    np.save(dossier / "sol_attributs.npy", np.array(attrs, dtype=np.int32))
    # normales de sommet (ordre de sol_faces.npy), repère local Z haut (TQ-SOL-008)
    nv = np.array(geo.vertexFloatAttribValues("N"), dtype=np.float32).reshape(-1, 3) if geo.findVertexAttrib("N")         else np.zeros((len(faces), 3), np.float32)
    np.save(dossier / "sol_normales.npy", (np.column_stack([nv[:, 0], -nv[:, 2], nv[:, 1]]) + 0.0).astype(np.float32))
    (dossier / "sol_vocabulaire.json").write_text(json.dumps(
        {"colonnes": ["z_type", "section", "bande", "visible", "classe", "materiau_id", "bande_id"], **voc},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"points": len(pts), "faces": len(comptes)}


def exporter_niveaux(geo, dossier):
    secs, chaines = [], []
    gs = geo.findPointGroup("sections")
    noms_s = [a.name() for a in geo.pointAttribs()]
    for p in (gs.points() if gs else []):
        d = {}
        for n in ("route", "section", "profil", "s0", "s1", "n_bandes", "b_cls", "b_has_g", "b_g", "b_retrait", "b_type",
                  "b_mat", "b_id", "l_bord", "l_h", "l_prof", "l_base", "l_H", "l_vue", "l_wc", "l_dhc", "l_cprof",
                  "a_lim", "a_s0", "a_s1", "a_vue", "a_r", "a_couvert", "a_bev", "r_s0", "r_s1", "abord_g", "abord_d",
                  "abord_g_mat", "abord_d_mat"):
            if n in noms_s:
                v = p.attribValue(n)
                d[n] = [_r(x) if isinstance(x, float) else x for x in v] if isinstance(v, tuple) else (
                    _r(v) if isinstance(v, float) else v)
        secs.append(d)
    gb = geo.findPrimGroup("bordures")
    for pr in (gb.prims() if gb else []):
        pts = []
        for p in pr.points():
            P = p.position()
            pts.append({"x": _r(P[0]), "y": _r(-P[2]), "s_ref": _r(p.attribValue("s_ref")), "t_ref": _r(p.attribValue("t_ref")),
                        "pied": _r(p.attribValue("pied")), "tete": _r(p.attribValue("tete")), "vue": _r(p.attribValue("vue")),
                        "zbf": _r(p.attribValue("zbf")), "can": p.attribValue("can"), "kind": p.attribValue("kind"),
                        "limite": p.attribValue("limite"), "section": p.attribValue("section"),
                        "k_bas": p.attribValue("k_bas"), "b_bas": p.attribValue("b_bas")})
        chaines.append({"id": pr.attribValue("id"), "route": pr.attribValue("route"), "profil": pr.attribValue("profil"),
                        "base": _r(pr.attribValue("base")), "H": _r(pr.attribValue("H")), "cprof": pr.attribValue("cprof"),
                        "wc": _r(pr.attribValue("wc")), "dhc": _r(pr.attribValue("dhc")), "fermee": pr.attribValue("fermee"),
                        "points": pts})
    d = {"schema": "rg_niveaux/0.1", "rampe_plateau_pct": _r(geo.attribValue("rg_rampe_plateau_pct")),
         "sections": secs, "bordures": chaines}
    (dossier / "niveaux.json").write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"sections": len(secs), "files_de_bordures": len(chaines)}


def exporter_heightfield(geo, dossier):
    """Résumé du HeightField de nivellement (sortie 2 de rg::nivellement) : descripteur du lecteur, résolution,
    nœuds par région, sha256 des voxels de chaque couche (déterminisme) -> heightfield.json."""
    couches, regions = {}, {}
    for pr in geo.prims():
        nom = pr.attribValue("name")
        brut = pr.allVoxelsAsString()
        couches[nom] = {"resolution": list(pr.resolution()), "sha256": hashlib.sha256(brut).hexdigest(),
                        "mode": pr.intrinsicValue("volumevisualmode")}
        v = np.frombuffer(brut, dtype=np.float32)
        if nom == "height":
            couches[nom]["min"], couches[nom]["max"] = _r(v.min()), _r(v.max())
        if nom in ("r0", "r1", "r2"):
            u, c = np.unique(v, return_counts=True)
            regions[nom] = {str(int(a)): int(b) for a, b in zip(u, c)}
    desc = {}
    for a in geo.globalAttribs():
        if a.name().startswith("niv_"):
            v = geo.attribValue(a.name())
            desc[a.name()] = list(v) if isinstance(v, tuple) else (_r(v) if isinstance(v, float) else v)
    h = {"schema": "rg_heightfield_l2/0.1", "descripteur": dict(sorted(desc.items())), "couches": couches,
         "noeuds_par_region": regions,
         "note": "région = 100 x rang de la route + nappe (nappe 0 à gauche) ; Z lu par pj_niv_z (README_HDA § 2)"}
    (dossier / "heightfield.json").write_text(json.dumps(h, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
    return {"resolution": couches.get("height", {}).get("resolution"),
            "regions": len([k for k in regions.get("r0", {}) if k != "-1"])}


def exporter_entites(geo, dossier):
    out = []
    for pr in geo.prims():
        pts = [_loc(p.position()) for p in pr.points()]
        out.append({"id": pr.attribValue("id"), "intervalles": [{k: (_r(v) if isinstance(v, float) else v)
                                                                 for k, v in sorted(iv.items())}
                                                                for iv in pr.attribValue("intervalles")],
                    "niv_s": [_r(x) for x in pr.attribValue("niv_s")], "niv_z_pied": [_r(x) for x in pr.attribValue("niv_z_pied")],
                    "props": pr.attribValue("props"), "materiau_id": pr.attribValue("materiau_id"),
                    "xy": [[_r(p[0]), _r(p[1])] for p in pts]})
    (dossier / "entites.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return len(out)


def _points_instances(geo, famille):
    noms = [a.name() for a in geo.pointAttribs()]
    out = []
    for p in geo.points():
        d = {"famille": famille}
        for n in ("kind", "type", "id", "bordure", "profil", "profil_bas", "role", "s0", "s1", "longueur", "vue", "vue_fin",
                  "base", "H", "sur_mesure", "coupe", "materiau_id"):
            if n in noms:
                v = p.attribValue(n)
                d[n] = _r(v) if isinstance(v, float) else v
        P = p.position()
        d["xyz"] = [_r(P[0]), _r(-P[2]), _r(P[1])]
        if "orient" in noms:
            q = p.attribValue("orient")
            d["orient"] = [_r(x) for x in q]
        out.append(d)
    return out


def _points_poses(noeud):
    """Points de pose de pj::bordure / pj::caniveau : TOUS les éléments et joints posés, y compris les pièces sur
    mesure (coudes, angles, retours, courbes serrées : sur_mesure = 1), lus sur le nœud interne « poser » de l'HDA
    (avant la séparation bibliothèque / sur mesure). La sortie 2 de l'HDA (points d'instances de la bibliothèque) ne
    porte que les pièces de bibliothèque : elements.json la complétait mal (relecture adverse : 2 × 1 m manquants aux
    coudes de S09, 13,2 m dans S03, absents des contrôles TQ-BOR et du placement dans Unreal)."""
    n = noeud.node("poser")
    return n.geometry() if n is not None else noeud.geometry(1)


def _grilles_avaloirs(ent):
    """Caniveaux à grille (au droit des ralentisseurs) et grilles d'avaloir (au pied des rampes de plateau) : éléments
    de la famille caniveau lus sur les entités de rg::vers_entites (intervalles grille_s, sortie 3 pour les avaloirs) ;
    radier (fil d'eau) aux extrémités = pied de la file (niv_s, niv_z_pied : le ralentisseur ne relève pas le fil
    d'eau)."""
    out = []
    for pr in ent.geometry(0).prims():
        gs = list(pr.attribValue("grille_s")) if ent.geometry(0).findPrimAttrib("grille_s") else []
        S = list(pr.attribValue("niv_s"))
        Z = list(pr.attribValue("niv_z_pied"))
        kid = pr.attribValue("id")
        for k in range(0, len(gs) - 1, 2):
            a, b = gs[k], gs[k + 1]
            out.append({"famille": "caniveau", "kind": "element", "type": "grille", "id": f"{kid}/G{k // 2:02d}",
                        "bordure": kid, "s0": _r(a), "s1": _r(b), "longueur": _r(b - a), "sur_mesure": 1,
                        "radier": [_r(float(np.interp(a, S, Z))), _r(float(np.interp(b, S, Z)))],
                        "materiau_id": "grille_caniveau"})
    vus = set()
    g2 = ent.geometry(2)
    partie = g2.findPrimAttrib("partie") is not None
    for pr in g2.prims():
        i = pr.attribValue("id")
        if i in vus:
            continue
        vus.add(i)
        # position de l'élément : centre de la grille (le corps de l'avaloir, sous la grille, n'est pas compté)
        pts = [_loc(v.point().position()) for p in g2.prims() if p.attribValue("id") == i
               and (not partie or p.attribValue("partie") != "corps") for v in p.vertices()]
        c = np.mean(np.array(pts), axis=0)
        out.append({"famille": "caniveau", "kind": "element", "type": "avaloir", "id": i, "bordure": pr.attribValue("bordure"),
                    "s0": _r(pr.attribValue("s0")), "s1": _r(pr.attribValue("s1")),
                    "longueur": _r(pr.attribValue("s1") - pr.attribValue("s0")), "sur_mesure": 0,
                    "xyz": [_r(x) for x in c], "materiau_id": pr.attribValue("materiau_id")})
    return out


def _retours(ent):
    """{file de bordure: [(s0, s1)]} des intervalles « retour » (retours transversaux à vue variable) de rg::vers_entites."""
    out = {}
    if ent is None:
        return out
    for pr in ent.geometry(0).prims():
        for iv in pr.attribValue("intervalles"):
            if iv.get("usage") == "retour":
                out.setdefault(pr.attribValue("id"), []).append((float(iv["s0"]), float(iv["s1"])))
    return out


def exporter_elements(bor, can, dossier, ent=None):
    el = _points_instances(_points_poses(bor), "bordure") + _points_instances(_points_poses(can), "caniveau")
    ret = _retours(ent)
    for e in el:
        e.setdefault("sur_mesure", 0)
        # retour transversal d'avancée ou d'îlot (vue variable) : même pièce de raccord de vue que la chartière pour
        # pj::bordure, typée « raccord_vue », rôle « retour » (correction après le second contrôle : confondu au
        # placement avec la chartière d'un abaissé)
        if e["famille"] == "bordure" and e.get("type") == "chartiere" and "s0" in e:
            sm = 0.5 * (e["s0"] + e["s1"])
            if any(a - 1e-6 <= sm <= b + 1e-6 for a, b in ret.get(e.get("bordure"), [])):
                e["type"], e["role"] = "raccord_vue", "retour"
    if ent is not None:
        el += _grilles_avaloirs(ent)
    (dossier / "elements.json").write_text(json.dumps(el, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"bordure": sum(1 for e in el if e["famille"] == "bordure"), "caniveau": sum(1 for e in el if e["famille"] == "caniveau"),
            "sur_mesure": sum(1 for e in el if e.get("sur_mesure") and e.get("kind") == "element"),
            "raccords_vue_retours": sum(1 for e in el if e.get("type") == "raccord_vue"),
            "caniveau_grille": sum(1 for e in el if e.get("type") == "grille"),
            "avaloirs": sum(1 for e in el if e.get("type") == "avaloir")}


def exporter_bev_vegetation(sol, ent, dossier):
    import rendu_l2b as RB                         # règle de teinte de la BEV (contraste avec le revêtement voisin)
    g = sol.geometry(1)
    voisin = g.findPrimAttrib("materiau_voisin") is not None
    bev = {}
    for pr in g.prims():
        d = bev.setdefault(pr.attribValue("id"), {"dalles": [], "plots": 0})
        d["dalles"].append([[_r(c) for c in _loc(v.point().position())] for v in pr.vertices()])
        if voisin and "materiau_voisin" not in d:
            # revêtement où la BEV est posée et teinte de la BEV en contraste avec lui (RF-MA-OBS-003 : contraste de
            # luminance ≥ 0,40 ; correction après le second contrôle)
            d["materiau_voisin"] = pr.attribValue("materiau_voisin")
            d["teinte"] = RB.variante_bev(d["materiau_voisin"])
    gp = g.findPointGroup("plots")
    for p in (gp.points() if gp else []):
        bev.setdefault(p.attribValue("id"), {"dalles": [], "plots": 0})["plots"] += 1
    (dossier / "bev.json").write_text(json.dumps(bev, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    gv = ent.geometry(1)
    noms = [a.name() for a in gv.pointAttribs()]
    veg = [dict({"id": p.attribValue("id"), "route": p.attribValue("route"), "type": p.attribValue("type"),
                 "bande": p.attribValue("bande"), "s": _r(p.attribValue("s")), "t": _r(p.attribValue("t")),
                 "x": _r(p.position()[0]), "y": _r(-p.position()[2])},
                **{k: (_r(p.attribValue(k)) if k != "asset_id" else p.attribValue(k))
                   for k in ("asset_id", "hauteur_m", "houppier_rayon_m", "fut_m") if k in noms})
           for p in gv.points()]
    # étape 1 (la route seule, décision de l'utilisateur) : les arbres du modèle sont exportés pour l'étape 2 et marqués
    # comme tels (correction après le second contrôle : 53 arbres exportés sans marque, que le placement aurait posés) ;
    # le placement de l'étape 1 ne lit pas « arbres » tant que « etape » vaut 2
    doc = {"schema": "rg_vegetation/0.2", "etape": 2,
           "usage": "étape 2 (végétation) : à ne pas placer à l'étape 1, la route seule (décision de l'utilisateur du "
                    "17/10/2026) ; rendu : --decor-etape2", "arbres": veg}
    (dossier / "vegetation.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"bev": len(bev), "arbres_etape2": len(veg)}


# -------------------------------------------------------------------------------------------------- mesures
def _courbe(xy):
    xy = np.asarray(xy, float)
    d = np.hypot(*np.diff(xy, axis=0).T)
    return xy, np.concatenate([[0.0], np.cumsum(d)])


def _en(xy, S, s):
    """Point et tangente unitaire de la polyligne en l'abscisse s."""
    i = int(np.clip(np.searchsorted(S, s, side="right") - 1, 0, len(S) - 2))
    a, b = xy[i], xy[i + 1]
    u = (s - S[i]) / max(S[i + 1] - S[i], 1e-12)
    t = (b - a) / max(np.linalg.norm(b - a), 1e-12)
    return a + u * (b - a), t


def _sonde(geo, x, y):
    """Z du premier impact d'un rayon vertical descendant en (x, y) local (None : rien)."""
    pos, nrm, uvw = hou.Vector3(), hou.Vector3(), hou.Vector3()
    pr = geo.intersect(hou.Vector3(x, 50.0, -y), hou.Vector3(0, -1, 0), pos, nrm, uvw, None, 0, 1e9, 1e-6)
    return float(pos[1]) if pr >= 0 else None


def mesurer(noeuds, dossier):
    """Mesures sur la géométrie fabriquée : sondes verticales autour de chaque élément de bordure (dessus, devant la
    face, derrière l'arrière, sol sous l'élément), affleurement des caniveaux, rayons à travers les joints
    (TQ-BOR-005). Les valeurs attendues sont calculées à part, par le contrôle indépendant (validation/)."""
    sol = noeuds["sol"].geometry(0)
    bor_m = noeuds["bordures"].geometry(0)
    can_m = noeuds["caniveaux"].geometry(0)
    vis = hou.Geometry()
    vis.merge(sol)
    tous = hou.Geometry()
    tous.merge(sol)
    tous.merge(bor_m)
    tous.merge(can_m)
    devant = hou.Geometry()
    devant.merge(sol)
    devant.merge(can_m)
    # grilles d'avaloir : elles remplacent le caniveau qu'elles occupent (second contrôle), surface devant la face
    devant.merge(noeuds["vers_entites"].geometry(2))
    ent = {pr.attribValue("id"): pr for pr in noeuds["vers_entites"].geometry(0).prims()}
    courbes = {}
    for k, pr in ent.items():
        xy = [(p.position()[0], -p.position()[2]) for p in pr.points()]
        courbes[k] = _courbe(xy)
    caniv = {}
    for k, pr in ent.items():
        props = json.loads(pr.attribValue("props") or "{}")
        caniv[k] = props.get("caniveau", {})
    out_el, out_j, out_c = [], [], []
    pts = _points_poses(noeuds["bordures"]).points()     # liste complète (pièces sur mesure comprises)
    for p in pts:
        kind = p.attribValue("kind")
        k = p.attribValue("bordure")
        if k not in courbes:
            continue
        xy, S = courbes[k]
        s0, s1 = p.attribValue("s0"), p.attribValue("s1")
        base = p.attribValue("base")
        if kind == "element":
            for f in (0.25, 0.5, 0.75):
                sm = s0 + f * (s1 - s0)
                F, tg = _en(xy, S, sm)
                n = np.array([-tg[1], tg[0]])                    # côté haut (trottoir) à gauche
                q_top = F + 0.07 * n
                q_dev = F - 0.004 * n
                q_arr = F + (base + 0.03) * n
                z_top = _sonde(bor_m, *q_top)
                z_dev = _sonde(devant, *q_dev)
                z_arr = _sonde(vis, *q_arr)
                sous = [_sonde(vis, *(F + u * n)) for u in (0.006, 0.012)]
                out_el.append({"bordure": k, "id": p.attribValue("id"), "type": p.attribValue("type"),
                               "profil": p.attribValue("profil"), "s": _r(sm), "f": f, "x": _r(F[0]), "y": _r(F[1]),
                               "z_dessus": None if z_top is None else _r(z_top), "z_devant": None if z_dev is None else _r(z_dev),
                               "z_arriere": None if z_arr is None else _r(z_arr),
                               "sol_sous": [None if z is None else _r(z) for z in sous]})
        elif kind == "joint":
            sm = s0
            F, tg = _en(xy, S, sm)
            n = np.array([-tg[1], tg[0]])
            # joint d'angle (retour de bordure) : la visée sur la seule normale amont longe la face de la pièce
            # suivante (rayon rasant, coplanaire) ; on vise et on recule selon la bissectrice des deux normales,
            # 4 mm derrière chacune des deux faces
            _, t1 = _en(xy, S, sm - 0.05)
            _, t2 = _en(xy, S, sm + 0.05)
            ang = math.degrees(math.acos(float(np.clip(np.dot(t1, t2), -1.0, 1.0))))
            dv = 0.004 * n
            if ang > 30.0:
                n1, n2 = np.array([-t1[1], t1[0]]), np.array([-t2[1], t2[0]])
                dv = 0.004 * (n1 + n2)
                n = (n1 + n2) / max(np.linalg.norm(n1 + n2), 1e-12)
            z_dev = _sonde(devant, *(F - 0.004 * n)) or 0.0
            z_top = _sonde(bor_m, *(F + 0.07 * n))
            vue = (z_top - z_dev) if z_top is not None else p.attribValue("vue")
            # visée : milieu de la partie vue de la face (sol relevé par un ralentisseur compris)
            cible = hou.Vector3(F[0] + dv[0], z_dev + 0.5 * vue, -(F[1] + dv[1]))
            res = []
            for h in (1.2, 1.6):
                for d in (2.0, 5.0, 10.0):
                    C = F - d * n
                    o = hou.Vector3(C[0], z_dev + h, -C[1])
                    dirv = (cible - o).normalized()
                    pos, nrm, uvw = hou.Vector3(), hou.Vector3(), hou.Vector3()
                    pr = tous.intersect(o, dirv, pos, nrm, uvw, None, 0, 1e9, 1e-6)
                    if pr < 0:
                        res.append({"h": h, "d": d, "impact": False})
                        continue
                    hp = np.array([pos[0], -pos[2]])
                    derriere = float(np.dot(hp - F, n))
                    res.append({"h": h, "d": d, "impact": True, "derriere_m": _r(derriere)})
            out_j.append({"bordure": k, "id": p.attribValue("id"), "s": _r(sm), "largeur_mm": _r(1000 * p.attribValue("longueur"), 3),
                          "angle_deg": _r(ang, 3), "rayons": res})
    # caniveaux : arête côté chaussée contre l'enrobé (TQ-BOR-007, ±3 mm)
    for p in _points_poses(noeuds["caniveaux"]).points():
        if p.attribValue("kind") != "element":
            continue
        k = p.attribValue("bordure")
        if k not in courbes:
            continue
        xy, S = courbes[k]
        sm = 0.5 * (p.attribValue("s0") + p.attribValue("s1"))
        F, tg = _en(xy, S, sm)
        n = np.array([-tg[1], tg[0]])
        wc = p.attribValue("base")
        z_can = _sonde(can_m, *(F - (wc - 0.02) * n))
        z_enr = _sonde(vis, *(F - (wc + 0.01) * n))
        out_c.append({"bordure": k, "id": p.attribValue("id"), "s": _r(sm), "largeur": _r(wc),
                      "z_caniveau_2cm": None if z_can is None else _r(z_can), "z_enrobe_1cm": None if z_enr is None else _r(z_enr)})
    # HeightField : pj_niv_z aux points des faces visibles de bande, contre le Z du sol fabriqué
    gh = noeuds["controle_heightfield"].geometry()
    te = np.array(gh.pointIntAttribValues("hf_teste"))
    ab = np.array(gh.pointIntAttribValues("hf_absent"))
    eh = np.abs(np.array(gh.pointFloatAttribValues("ecart_hf")))[(te == 1) & (ab == 0)]
    hf = {"points_testes": int(te.sum()), "absents": int(ab.sum()),
          "sous_bordure_ecartes": int(sum(gh.pointIntAttribValues("hf_sous_bordure"))),
          "ecart_max_m": _r(eh.max() if len(eh) else 0.0, 7),
          "ecart_p99_m": _r(np.percentile(eh, 99) if len(eh) else 0.0, 7),
          "ecart_moyen_m": _r(eh.mean() if len(eh) else 0.0, 7)}
    m = {"schema": "rg_mesures_l2/0.1", "elements": out_el, "joints": out_j, "caniveaux": out_c, "heightfield": hf,
         "note": "sondes verticales (rayon descendant) et rayons des joints sur la géométrie fabriquée (Houdini intersect)"}
    (dossier / "mesures_l2.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"elements_sondes": len(out_el), "joints": len(out_j), "caniveaux": len(out_c), "heightfield": hf}


def ecrire_usd(noeuds, dossier):
    """Couches USD (Z haut) de la route fabriquée : sol, BEV, bordures, caniveaux ; matériaux par materiau_id
    (références aux .usda de la bibliothèque, chemins relatifs)."""
    import rendre_l2 as RL
    from pxr import Usd, UsdGeom
    f = dossier / "route_l2.usda"
    if f.exists():
        f.unlink()
    stage = Usd.Stage.CreateNew(str(f))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    couches, ids = {}, set()
    for nom, geo in (("Sol", noeuds["sol"].geometry(0)), ("BEV", noeuds["sol"].geometry(1)),
                     ("Bordures", noeuds["bordures"].geometry(0)), ("Caniveaux", noeuds["caniveaux"].geometry(0)),
                     ("Avaloirs", noeuds["vers_entites"].geometry(2))):
        if not len(geo.prims()):
            continue
        couches[nom] = RL.maillages(geo, nom)
        ids |= set(couches[nom])
    UsdGeom.Xform.Define(stage, "/Monde")
    liaisons, sources = RL.materiaux(stage, ids, dossier, racine="/Monde/Looks")
    for nom, d in couches.items():
        RL.ecrire_couche(stage, f"/Monde/{nom}", d, liaisons)
    stage.SetDefaultPrim(stage.GetPrimAtPath("/Monde"))
    stage.GetRootLayer().Save()
    return {"fichier": f.name, "materiaux": sources}


def controles_houdini(noeuds):
    g = noeuds["sol"].geometry(0)
    return {"murs": g.attribValue("rg_sol_murs"), "aretes_sans_paire": g.attribValue("rg_sol_aretes_sans_paire"),
            "faces_sol": len(g.prims()), "points_sol": len(g.points()),
            "faces_bordures": len(noeuds["bordures"].geometry(0).prims()),
            "faces_caniveaux": len(noeuds["caniveaux"].geometry(0).prims())}


def fabriquer_scene(noeuds, scene, dossier_scene, signatures, info):
    d = Path(dossier_scene) / "l2"
    d.mkdir(parents=True, exist_ok=True)
    cuire(noeuds, scene)
    comptes = {"sol": exporter_sol(noeuds["sol"].geometry(0), d),
               "niveaux": exporter_niveaux(noeuds["nivellement"].geometry(0), d),
               "heightfield": exporter_heightfield(noeuds["nivellement"].geometry(1), d),
               "entites_bordures": exporter_entites(noeuds["vers_entites"].geometry(0), d),
               "elements": exporter_elements(noeuds["bordures"], noeuds["caniveaux"], d, noeuds["vers_entites"]),
               **exporter_bev_vegetation(noeuds["sol"], noeuds["vers_entites"], d)}
    comptes["mesures"] = mesurer(noeuds, d)
    usd = ecrire_usd(noeuds, d)
    fichiers = {p.name: sha256(p) for p in sorted(d.iterdir()) if p.is_file() and p.name != "manifest_l2.json"
                and p.suffix in (".npy", ".json", ".usda")}
    man = {"schema": "rg_manifest_l2/0.1", "pilote": VERSION_L2, "scene": scene, "entree": info,
           "houdini": hou.applicationVersionString(), "vex_jit": os.environ.get("HOUDINI_VEX_DISABLE_JIT") != "1",
           "hda": signatures, "comptes": comptes, "controles_houdini": controles_houdini(noeuds), "usd": usd,
           "avertissements": DET.avertissements_stables(noeuds.values()),
           "fichiers": fichiers}
    (d / "manifest_l2.json").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return d, man
