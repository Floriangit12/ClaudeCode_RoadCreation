"""Lot L2b du pilote (hython) : marquages au sol de la section courante, peints sur le sol fabriqué du lot L2.

Appelé par fabriquer_generateur.py (option --l2b, qui implique --l2) après la chaîne des lots L1 et L2 :
    rg::marquages (empreintes exactes, découpées aux lignes de rupture du sol) -> pj::marquage_solide::1.0 x 2
    (lignes longitudinales 2 mm, autres marques 3 mm : TQ-MQG-002 ; drapé sur le sol de rg::sol : TQ-MQG-005)
Écrit dans <sortie>/<scene>/l2b/ (non versionné) :
    empreintes.json          polygones des empreintes (x, y locaux) et attributs (classe, type, id, gabarit, route,
                             clé de limite, modulation, largeur, s0, s1, bande du sol)
    table_marques.json       une ligne par marque (tiret, passage, flèche, symbole, inscription, figurine, hachure,
                             aplat) : définition (s0, s1, t, cap, gabarit, n, e, W) et règles citées
    peinture_points.npy (x, y, z locaux Z haut), peinture_faces.npy, peinture_comptes.npy, peinture_attributs.npy
    (entité, classe, dessus) et peinture_vocabulaire.json : maillage de peinture fabriqué
    mesures_l2b.json, mesures_l2b.npz : dessus de la peinture − sol fabriqué (rayon vertical) aux sommets du dessus
                             et aux centres des faces du dessus ; contrôles de pj::marquage_solide
    route_l2b.usda           couche Marquages (Z haut, matériaux de peinture de la bibliothèque) ; manifest_l2b.json
Aucune date ni durée n'est écrite : deux exécutions donnent les mêmes octets.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

import hou

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[1]
sys.path.insert(0, str(ICI / "rendu"))
sys.path.insert(0, str(ICI / "hda" / "commun"))
import rg_hda_outils as R  # noqa: E402
sys.path.insert(0, str(ICI))
from commun import determinisme as DET  # noqa: E402

VERSION_L2B = "fabriquer_l2b/1.0 (lot L2b)"
EPAISSEURS = {"lignes": 0.002, "marques": 0.003}      # TQ-MQG-002 : peinture 2 mm (lignes), enduit 3 mm (autres)
ANCRAGE = 0.002                                         # TQ-MQG-002 : jupe enfouie de 2 mm
PAS_MAILLAGE = {"lignes": 0.25, "marques": 0.10}        # Triangulate 2D (raffinement) : drapé sur le sol

VEX_MESURE_POINTS = r"""
// dessus de la peinture − sol fabriqué (entrée 1, BEV exclues) sous chaque point : rayon vertical, impact le plus proche
// du point par en dessous (le sol est sous la peinture de 2 ou 3 mm)
vector pos[];
int prs[];
vector uvw[];
int n = intersect_all(1, "", @P + {0, 0.3, 0}, {0, -0.6, 0}, pos, prs, uvw, 1e-6, 1e-6);
float best = 1e9;
f@z_sol = -1e9;
for (int k = 0; k < n; k++) {
    if (prim(1, "materiau_id", prs[k]) == "bev_podotactile") continue;
    float d = @P.y - pos[k].y;
    if (d > -0.004 && d < best) { best = d; f@z_sol = pos[k].y; }
}
f@au_dessus = (f@z_sol > -1e8) ? @P.y - f@z_sol : -1e9;
// point du dessus : sommet d'une face du dessus (groupe dessus de pj::marquage_solide, normale verticale : les faces
// du chanfrein, à 45°, en sont exclues)
int pp[] = pointprims(0, @ptnum);
i@dessus = 0;
foreach (int q; pp) if (inprimgroup(0, "dessus", q) && prim_normal(0, q, {0.333, 0.333, 0}).y > 0.95) i@dessus = 1;
"""

VEX_MESURE_FACES = r"""
// même mesure au centre de chaque face du dessus (entre les sommets : la peinture plane suit-elle le sol ?)
i@dessus = inprimgroup(0, "dessus", @primnum) && prim_normal(0, @primnum, {0.333, 0.333, 0}).y > 0.95;
f@au_dessus_centre = -1e9;
if (!i@dessus) return;
vector c = prim(0, "P", @primnum);
vector pos[];
int prs[];
vector uvw[];
int n = intersect_all(1, "", c + {0, 0.3, 0}, {0, -0.6, 0}, pos, prs, uvw, 1e-6, 1e-6);
float best = 1e9;
for (int k = 0; k < n; k++) {
    if (prim(1, "materiau_id", prs[k]) == "bev_podotactile") continue;
    float d = c.y - pos[k].y;
    if (d > -0.004 && d < best) best = d;
}
f@au_dessus_centre = best < 1e8 ? best : -1e9;
"""


def _r(x, n=6):
    v = round(float(x), n)
    return 0.0 if v == 0 else v


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def construire_hda(forcer=False):
    """rg::marquages::1.0 (construite si absente ou si --construire-hda) ; renvoie {nom: signature}."""
    import importlib.util
    d = ICI / "hda" / "rg_marquages"
    cible = d / "rg_marquages.hdalc"
    if True:                                         # construction à chaque passe : dossier gardé si signature inchangée
        sys.path.insert(0, str(d))
        spec = importlib.util.spec_from_file_location("construire_rg_marquages", d / "construire.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cible = mod.construire(d)
    else:
        hou.hda.installFile(str(cible))
    f = list(Path(r"D:/ClaudeCode_RoadCreation/recon/pcg/houdini/hda/pj_marquage_commun/pj_marquage_solide.hdalc").glob(
        "*/PjSignature"))
    return {f"rg::marquages::{R.VERSION}": R.signature(cible),
            "pj::marquage_solide::1.0": f[0].read_text(encoding="utf-8").strip() if f else "",
            "pj::gabarits_iisr::1.0": next((p.read_text(encoding="utf-8").strip() for p in Path(
                r"D:/ClaudeCode_RoadCreation/recon/pcg/houdini/hda/pj_marquage_commun/pj_gabarits_iisr.hdalc").glob(
                "*/PjSignature")), "")}


def reseau(obj, lire, graphe, noeuds_l2):
    mq = obj.createNode(R.nom_type("marquages"), "marquages")
    for k, (n, o) in enumerate(((graphe, 0), (noeuds_l2["nivellement"], 0), (lire, 4), (lire, 3))):
        mq.setInput(k, n, o)
    out = {"marquages": mq}
    for k, nom in enumerate(("lignes", "marques")):
        s = obj.createNode("pj::marquage_solide::1.0", f"peinture_{nom}")
        s.setInput(0, mq, k)
        s.setInput(1, noeuds_l2["nivellement"], 1)       # HeightField de nivellement (région de chaque pièce)
        s.setInput(2, noeuds_l2["sol"], 0)               # sol fabriqué : drapé sur le sol réellement maillé
        s.parm("epaisseur").set(EPAISSEURS[nom])
        s.parm("enfouissement").set(ANCRAGE)
        s.parm("pas_maillage").set(PAS_MAILLAGE[nom])
        s.parm("couche").set("Marquages")
        out[f"peinture_{nom}"] = s
    fus = obj.createNode("merge", "peinture")
    fus.setInput(0, out["peinture_lignes"])
    fus.setInput(1, out["peinture_marques"])
    mp = R.wrangle(obj, "mesure_points", VEX_MESURE_POINTS, "point", fus, entrees=(noeuds_l2["sol"],))
    mf = R.wrangle(obj, "mesure_faces", VEX_MESURE_FACES, "primitive", mp, entrees=(noeuds_l2["sol"],))
    out["peinture"] = fus
    out["mesure"] = mf
    obj.layoutChildren()
    return out


def cuire(noeuds, scene):
    mq = noeuds["marquages"]
    try:
        mq.cook(force=True)
    except hou.OperationFailed:
        pass
    # marquages des carrefours (lot L4, intégration de l'étape 2) : rg::marquages_carrefour cuite et contrôlée d'abord
    mc = noeuds.get("marquages_carrefour")
    if mc is not None:
        try:
            mc.cook(force=True)
        except hou.OperationFailed:
            pass
        err = [f"{c.path()} : {e}" for c in (mc,) + mc.allSubChildren() for e in c.errors()]
        if err:
            raise SystemExit(f"{scene} : erreurs de cuisson (lot L4)" + chr(10) + chr(10).join(err[:20]))
    # scène sans marque d'une famille : pj::marquage_solide contourné (entrée vide transmise telle quelle) ; décidé sur
    # l'entrée réelle du nœud (marques des carrefours, des giratoires et des musoirs fusionnées comprises ; intégration
    # de l'étape 2 : lots L4 et autoroutes) — pour la chaîne simple, l'entrée est la sortie de rg::marquages
    for k, nom in enumerate(("peinture_lignes", "peinture_marques")):
        cx = noeuds[nom].inputConnections()
        src = cx[0].inputNode() if cx else None
        if src is not None and src != mq:
            try:
                src.cook(force=True)
            except hou.OperationFailed:
                pass
            g = src.geometry(cx[0].outputIndex())
        else:
            g = mq.geometry(k)
        noeuds[nom].bypass(g is None or len(g.prims()) == 0)
    for nom in ("marquages", "peinture_lignes", "peinture_marques", "mesure"):
        n = noeuds[nom]
        try:
            n.cook(force=True)
        except hou.OperationFailed:
            pass
        err = [f"{c.path()} : {e}" for c in (n,) + n.allSubChildren() for e in c.errors()]
        if err:
            raise SystemExit(f"{scene} : erreurs de cuisson (lot L2b)" + chr(10) + chr(10).join(err[:20]))


def _attr(o, nom, defaut=None):
    try:
        v = o.attribValue(nom)
    except hou.OperationFailed:
        return defaut
    return v


def exporter_empreintes(mq, dossier):
    out = []
    for k, famille in ((0, "lignes"), (1, "marques")):
        g = mq.geometry(k)
        noms = [a.name() for a in g.primAttribs()]
        for pr in g.prims():
            d = {"famille": famille, "xy": [[_r(p.position()[0]), _r(-p.position()[2])] for p in pr.points()]}
            for n in ("pj_entite", "id", "classe", "type", "gabarit", "materiau_id", "route", "cle", "modulation",
                      "largeur_m", "s0", "s1", "rang", "bande_sol", "partie", "anneau"):
                if n in noms:
                    v = pr.attribValue(n)
                    d[n] = _r(v) if isinstance(v, float) else v
            out.append(d)
    (dossier / "empreintes.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    t = mq.geometry(2)
    tab = []
    noms = [a.name() for a in t.pointAttribs()]
    for p in t.points():
        d = {"x": _r(p.position()[0]), "y": _r(-p.position()[2])}
        for n in noms:
            if n.startswith("m_"):
                v = p.attribValue(n)
                d[n[2:]] = _r(v) if isinstance(v, float) else v
        tab.append(d)
    det = {}
    g0 = mq.geometry(0)
    for n in ("rg_marquages_sur_bordure", "rg_marquages_traversant_rupture", "rg_marquages_hors_bande",
              "rg_marquages_sans_gabarit", "rg_marquages_degagements", "rg_marquages_avertissements"):
        v = _attr(g0, n)
        det[n[13:]] = list(v) if isinstance(v, tuple) else v
    (dossier / "table_marques.json").write_text(json.dumps({"schema": "rg_table_marques/0.1", "controles": det,
                                                            "marques": tab}, ensure_ascii=False, indent=1) + "\n",
                                                encoding="utf-8")
    return {"empreintes": len(out), "marques": len(tab), "controles": det}


def exporter_peinture(geo, dossier):
    P = np.array(geo.pointFloatAttribValues("P"), dtype=np.float64).reshape(-1, 3)
    pts = np.column_stack([P[:, 0], -P[:, 2], P[:, 1]]) + 0.0
    comptes, faces, attrs = [], [], []
    voc = {"pj_entite": [], "classe": []}
    idx = {k: {} for k in voc}
    for pr in geo.prims():
        vs = [v.point().number() for v in pr.vertices()]
        comptes.append(len(vs))
        faces += vs
        ligne = []
        for k in ("pj_entite", "classe"):
            v = pr.attribValue(k)
            if v not in idx[k]:
                idx[k][v] = len(voc[k])
                voc[k].append(v)
            ligne.append(idx[k][v])
        ligne.append(int(pr.attribValue("dessus")))
        attrs.append(ligne)
    np.save(dossier / "peinture_points.npy", pts)
    np.save(dossier / "peinture_faces.npy", np.array(faces, dtype=np.int32))
    np.save(dossier / "peinture_comptes.npy", np.array(comptes, dtype=np.int32))
    np.save(dossier / "peinture_attributs.npy", np.array(attrs, dtype=np.int32).reshape(-1, 3))
    (dossier / "peinture_vocabulaire.json").write_text(json.dumps(
        {"colonnes": ["pj_entite", "classe", "dessus"], **voc}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"points": len(pts), "faces": len(comptes), "entites": len(voc["pj_entite"])}


def mesurer(noeuds, dossier):
    g = noeuds["mesure"].geometry()
    au = np.array(g.pointFloatAttribValues("au_dessus"))
    de = np.array(g.pointIntAttribValues("dessus"))
    auc = np.array(g.primFloatAttribValues("au_dessus_centre"))
    dpr = np.array(g.primIntAttribValues("dessus"))
    # épaisseur nominale par point : classe de la première face
    lig = np.zeros(len(au), dtype=np.int8)
    ent_cl = {}
    for pr in g.prims():
        c = pr.attribValue("classe")
        ent_cl[pr.attribValue("pj_entite")] = c
    np.savez(dossier / "mesures_l2b.npz", au_dessus=au.astype(np.float64), dessus=de.astype(np.int8),
             au_dessus_centre=auc.astype(np.float64), dessus_face=dpr.astype(np.int8))
    ctl = {}
    for nom in ("peinture_lignes", "peinture_marques"):
        try:
            ctl[nom] = {} if noeuds[nom].isBypassed() else noeuds[nom].geometry().attribValue("pj_marquage_controles")
        except hou.OperationFailed:
            ctl[nom] = {}
    m = {"schema": "rg_mesures_l2b/0.1",
         "points_dessus": int(de.sum()), "faces_dessus": int(dpr.sum()),
         "sans_sol_points_dessus": int(((au < -1e8) & (de == 1)).sum()),
         "controles_marquage_solide": {k: {kk: (list(vv) if isinstance(vv, tuple) else vv) for kk, vv in v.items()}
                                       for k, v in ctl.items()},
         "note": "au_dessus = dessus de la peinture − sol fabriqué (rayon vertical, BEV exclues) ; détail par point "
                 "et par face dans mesures_l2b.npz (ordre de peinture_points.npy / peinture_comptes.npy)"}
    (dossier / "mesures_l2b.json").write_text(json.dumps(m, ensure_ascii=False, indent=1, default=str) + "\n",
                                               encoding="utf-8")
    del lig, ent_cl
    return m


def ecrire_usd(noeuds, dossier):
    """Couche USD (Z haut) des marquages : maillages de peinture par materiau_id (matériaux peinture_<couleur>_u<n>
    de assets/lib/route_fr/materiaux/peinture_routiere)."""
    import rendre_l2 as RL
    from pxr import Usd, UsdGeom
    f = dossier / "route_l2b.usda"
    if f.exists():
        f.unlink()
    stage = Usd.Stage.CreateNew(str(f))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    d = RL.maillages(noeuds["peinture"].geometry(), "Marquages")
    UsdGeom.Xform.Define(stage, "/Monde")
    liaisons, sources = RL.materiaux(stage, set(d), dossier, racine="/Monde/Looks")
    RL.ecrire_couche(stage, "/Monde/Marquages", d, liaisons)
    stage.SetDefaultPrim(stage.GetPrimAtPath("/Monde"))
    stage.GetRootLayer().Save()
    return {"fichier": f.name, "materiaux": sources}


def fabriquer_scene(noeuds, scene, dossier_scene, signatures, info):
    d = Path(dossier_scene) / "l2b"
    d.mkdir(parents=True, exist_ok=True)
    cuire(noeuds, scene)
    comptes = {"empreintes": exporter_empreintes(noeuds["marquages"], d),
               "peinture": exporter_peinture(noeuds["mesure"].geometry(), d)}
    comptes["mesures"] = mesurer(noeuds, d)
    usd = ecrire_usd(noeuds, d)
    fichiers = {p.name: sha256(p) for p in sorted(d.iterdir()) if p.is_file() and p.name != "manifest_l2b.json"
                and p.suffix in (".npy", ".npz", ".json", ".usda")}
    man = {"schema": "rg_manifest_l2b/0.1", "pilote": VERSION_L2B, "scene": scene, "entree": info,
           "houdini": hou.applicationVersionString(), "vex_jit": os.environ.get("HOUDINI_VEX_DISABLE_JIT") != "1",
           "hda": signatures, "parametres": {"epaisseur_m": EPAISSEURS, "ancrage_m": ANCRAGE,
                                             "pas_maillage_m": PAS_MAILLAGE,
                                             "regles": ["TQ-MQG-002", "TQ-MQG-005", "TQ-MQG-014", "MQ-DET-010"]},
           "comptes": {k: v for k, v in comptes.items() if k != "mesures"}, "usd": usd,
           "avertissements": DET.avertissements_stables(noeuds.values()),
           "fichiers": fichiers}
    (d / "manifest_l2b.json").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return d, man
