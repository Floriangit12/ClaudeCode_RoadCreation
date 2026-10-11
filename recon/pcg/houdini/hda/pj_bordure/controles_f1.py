"""Contrôles chiffrés des HDA de l'agent F1 (pj::sol, pj::bordure, pj::caniveau, pj::ilot) sur la géométrie FABRIQUÉE.

    hython recon/pcg/houdini/hda/pj_bordure/controles_f1.py [--emprise site|pilote] [--json SORTIE]

Mesures (règles citées) :
  - bordures : éléments par type, joints (largeur 3,5-9,5 mm, bordures_elements.json element.joint_mm), prototypes de
    bibliothèque, pièces sur mesure ; comparaison avec la pose numpy de référence (fabrique/points/bordures.json :
    nombre d'éléments et de joints par bordure, écart des pivots appariés par abscisse) ;
  - VAL-SOL-009 (2) assise des bordures : |pied posé − sol fabriqué| à 3 cm devant la face ; sol à 3 cm derrière
    l'arête arrière − tête (TQ-SOL-013 (6) : −4 ± 2 mm sur trottoir) ;
  - sol : pentes des triangles par classe (GA-TRO-004 sur les cheminements, rampes), E8 (> 45° et > 3 cm hors noue),
    arêtes de bord (TQ-SOL-009) ;
  - BEV : dessus des dalles − sol à 3 cm hors du module (E9, VAL-SOL-009 (3)) ;
  - îlots : tête de ceinture − remplissage au bord (GA-ARB-003 : 3 à 5 cm), écart au modèle de nivellement.
Les sondes de sol sont des rayons verticaux VEX (intersect) sur la sortie de pj::sol.
"""
import argparse
import collections
import json
import math
import sys
import time
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
HDA = ICI.parent
sys.path.insert(0, str(HDA / "commun"))
import pj_hda_outils as O  # noqa: E402

RACINE = O.RACINE
BASE = RACINE / "recon/out/paquet_jardin/v2/description/base"
REF_POINTS = RACINE / "recon/out/paquet_jardin/v2/fabrique/points/bordures.json"
SORTIE = RACINE / "recon/out/paquet_jardin/v2/fabrique_hda/controle/controles_f1.json"

VEX_SONDES_BORDURES = r"""
// Sondes de sol devant et derrière chaque élément de bordure (points de la sortie 2 + éléments sur mesure) :
// rayon vertical sur le sol fabriqué (entrée 1). Repère : orient (Houdini), X = s, Z = −u.
if (s@kind == "element" && s@type != "caniveau") {
    vector X = qrotate(p@orient, {1, 0, 0});
    vector Zb = qrotate(p@orient, {0, 0, 1});            // −u : vers la chaussée
    vector base = @P;
    float H = f@H, vue = f@vue;
    if (s@type == "chartiere") vue = max(f@vue, f@vue_fin);
    vector pied = base + qrotate(p@orient, set(0, H - vue, 0));
    vector av = pied + Zb * 0.03;
    vector ar = base + qrotate(p@orient, set(0, H, -(f@base + 0.03)));
    vector hit, uvw;
    int pr = intersect(1, av + {0, 2, 0}, {0, -4, 0}, hit, uvw);
    f@sol_avant = pr >= 0 ? hit.y - pied.y : 1e9;
    pr = intersect(1, ar + {0, 2, 0}, {0, -4, 0}, hit, uvw);
    f@sol_arriere = pr >= 0 ? hit.y - ar.y : 1e9;
    s@classe_arriere = pr >= 0 ? prim(1, "classe", pr) : "";
}
"""



def stats(v, pct=(5, 50, 95)):
    v = sorted(x for x in v if x is not None and math.isfinite(x))
    if not v:
        return {"n": 0}
    q = {f"p{p}": round(v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))], 4) for p in pct}
    return dict(n=len(v), min=round(v[0], 4), max=round(v[-1], 4), **q)


def construire_scene(emprise):
    O.installer_tout()
    geo = hou.node("/obj").createNode("geo", "controles_f1")
    lire = geo.createNode("pj::lire_description::1.0", "lire")
    lire.parm("dossier").set(BASE.as_posix())
    lire.parm("emprise").set(emprise)
    lire.parm("altitude").set("nivellement")
    fabs = {}
    for b, t in (("bordures", "pj::bordure::1.0"), ("caniveaux", "pj::caniveau::1.0"), ("sol", "pj::sol::1.0"),
                 ("ilots", "pj::ilot::1.0")):
        e = geo.createNode("blast", f"entrees_{b}")
        e.setInput(0, lire)
        e.parm("group").set(f"b_{b}")
        e.parm("negate").set(1)
        f = geo.createNode(t, f"fab_{b}")
        f.setInput(0, e)
        f.setInput(1, lire, 1)
        f.setInput(2, lire, 0)
        fabs[b] = f
    sol_seul = geo.createNode("blast", "sol_sans_bev")
    sol_seul.setInput(0, fabs["sol"])
    sol_seul.parm("group").set("@materiau_id=bev_podotactile")
    elems = geo.createNode("merge", "elements")
    elems.setInput(0, fabs["bordures"], 1)
    w = geo.createNode("attribwrangle", "sondes_bordures")
    w.parm("class").set(2)
    w.parm("snippet").set(VEX_SONDES_BORDURES)
    w.setInput(0, elems)
    w.setInput(1, sol_seul)
    return geo, lire, fabs, w


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emprise", default="site")
    ap.add_argument("--json", default=str(SORTIE))
    a = ap.parse_args()
    t0 = time.time()
    geo, lire, fabs, sondes = construire_scene(a.emprise)
    res = {"schema": "pj_controles_f1/0.1", "emprise": a.emprise, "description": "recon/out/paquet_jardin/v2/description/base"}
    # ---- bordures
    fb = fabs["bordures"]
    pts = fb.geometry(1)
    sm_node = fb.node("sur_mesure")
    elems = [p for p in pts.points() if p.attribValue("kind") == "element"]
    joints = [p for p in pts.points() if p.attribValue("kind") == "joint"]
    smg = sm_node.geometry()
    sm_pts = smg.points()
    res["bordures"] = {
        "elements_bibliotheque": len(elems), "elements_sur_mesure": len(sm_pts), "joints": len(joints),
        "types": dict(sorted(collections.Counter(p.attribValue("type") for p in elems + list(sm_pts)).items())),
        "prototypes": len(set(p.attribValue("asset") for p in pts.points())),
        "largeur_joints_mm": stats([1000 * p.attribValue("longueur") for p in joints]),
        "fleche_elements_droits_mm": stats([p.attribValue("fleche_mm") for p in elems]),
        "maillage_faces": len(fb.geometry(0).prims()),
        "regles": ["TQ-BOR-002", "bordures_elements.regle_pas_rayon", "GA-CHR-002", "GA-ABA-004", "GA-BOR-005"],
    }
    # sondes d'assise (VAL-SOL-009 (2)) : éléments de bibliothèque (les sur mesure suivent la même pose)
    sg = sondes.geometry()
    av = [p.attribValue("sol_avant") for p in sg.points() if p.attribValue("kind") == "element"]
    av = [x for x in av if abs(x) < 1e8]
    ar = collections.defaultdict(list)
    for p in sg.points():
        if p.attribValue("kind") == "element" and abs(p.attribValue("sol_arriere")) < 1e8:
            ar[p.attribValue("classe_arriere")].append(p.attribValue("sol_arriere"))
    res["VAL-SOL-009_2_assise"] = {
        "sol_avant_moins_pied_m": stats(av), "part_abs_inf_2mm": round(sum(1 for x in av if abs(x) <= 0.002) / max(len(av), 1), 3),
        "part_abs_inf_1cm": round(sum(1 for x in av if abs(x) <= 0.01) / max(len(av), 1), 3),
        "sol_arriere_moins_tete_m_par_classe": {k: stats(v) for k, v in sorted(ar.items())},
        "pires_avant": sorted(([round(p.attribValue("sol_avant"), 4), p.attribValue("id")] for p in sg.points()
                               if p.attribValue("kind") == "element" and abs(p.attribValue("sol_avant")) < 1e8),
                              key=lambda x: -abs(x[0]))[:12],
        "note": "sol fabriqué (pj::sol) à 3 cm devant la face / derrière l'arête arrière ; écarts hérités du modèle de "
                "nivellement (D1) : pied = niv_z_pied, sol = grille sans lissage des marches",
    }
    # comparaison avec la pose numpy de référence
    if REF_POINTS.exists():
        ref = json.loads(REF_POINTS.read_text(encoding="utf-8"))["points"]
        par = collections.defaultdict(lambda: {"e": [], "j": []})
        for r in ref:
            k = r["x"]["bordure"]
            if r["x"]["type"] in ("joint",):
                par[k]["j"].append(r)
            elif r["x"]["type"] != "caniveau":
                par[k]["e"].append(r)
        neuf = collections.defaultdict(lambda: {"e": [], "j": []})
        for p in elems + list(sm_pts):
            neuf[p.attribValue("bordure")]["e"].append(p)
        for p in joints:
            neuf[p.attribValue("bordure")]["j"].append(p)
        communes = sorted(set(par) & set(neuf))
        de, dj, dp, dz, dl = [], [], [], [], []
        for k in communes:
            de.append(len(neuf[k]["e"]) - len(par[k]["e"]))
            dj.append(len(neuf[k]["j"]) - len(par[k]["j"]))
            nn = [(0.5 * (p.attribValue("s0") + p.attribValue("s1")), p) for p in neuf[k]["e"]]
            for r in par[k]["e"]:
                sm_ = 0.5 * (r["x"]["s0"] + r["x"]["s1"])
                s_, p = min(nn, key=lambda t: abs(t[0] - sm_))
                if abs(s_ - sm_) > 0.3 or p.attribValue("sur_mesure"):
                    continue
                P = p.position()
                q = (P[0], -P[2], P[1])
                dp.append(math.hypot(q[0] - r["p"][0], q[1] - r["p"][1]))
                dz.append(q[2] - r["p"][2])
                dl.append(abs((p.attribValue("s1") - p.attribValue("s0")) - r["x"]["longueur_m"]))
        res["comparaison_reference_numpy"] = {
            "fichier": "recon/out/paquet_jardin/v2/fabrique/points/bordures.json",
            "bordures_communes": len(communes),
            "elements_reference": sum(len(par[k]["e"]) for k in communes),
            "elements_hda": sum(len(neuf[k]["e"]) for k in communes),
            "joints_reference": sum(len(par[k]["j"]) for k in communes),
            "joints_hda": sum(len(neuf[k]["j"]) for k in communes),
            "ecart_nombre_elements_par_bordure": stats(de),
            "pivots_apparies": len(dp), "ecart_plan_pivots_m": stats(dp), "ecart_z_pivots_m": stats(dz),
            "ecart_longueur_elements_m": stats(dl),
            "note": "référence : description v1 du pilote et Z de l'ancien modèle ; nouvelle pose : courbes régularisées "
                    "(D3) et nivellement unique (D1)",
        }
    # ---- sol
    sol = fabs["sol"].geometry()
    pentes = collections.defaultdict(list)
    e8 = 0
    for pr in sol.prims():
        if pr.attribValue("materiau_id") == "bev_podotactile":
            continue
        vs = [v.point().position() for v in pr.vertices()]
        if len(vs) != 3:
            continue
        a_, b_, c_ = (hou.Vector3(x) for x in vs)
        n = (b_ - a_).cross(c_ - a_)
        ln = n.length()
        if ln < 4e-4:
            continue
        pente = math.degrees(math.acos(min(1.0, abs(n[1]) / ln)))
        dzz = max(v[1] for v in vs) - min(v[1] for v in vs)
        cl = pr.attribValue("classe")
        pentes[cl].append(100 * math.tan(math.radians(min(pente, 89.0))))
        mz = pr.attribValue("modele_z") if sol.findPrimAttrib("modele_z") else ""
        if mz in ("rampe_plan_incline", "noue_talus_1_3"):
            pentes["modele:" + mz].append(100 * math.tan(math.radians(min(pente, 89.0))))
        if pente > 45 and dzz > 0.03 and pr.attribValue("materiau_id") != "noue_plantee":
            e8 += 1
    res["sol"] = {"triangles": len(sol.prims()), "points": len(sol.points()),
                  "pente_triangles_pct_par_classe": {k: stats(v, (50, 95, 99)) for k, v in sorted(pentes.items())},
                  "E8_triangles_45deg_3cm_hors_noue": e8,
                  "regles": ["TQ-SOL-002", "TQ-SOL-013", "GA-TRO-004", "VAL-SOL-009"]}
    # BEV (E9) : dessus des plots exclus, dessus de dalle − sol à 3 cm hors du module
    bev = [pr for pr in sol.prims() if pr.attribValue("materiau_id") == "bev_podotactile"]
    res["bev"] = {"faces": len(bev), "entites": len(set(pr.attribValue("pj_entite") for pr in bev))}
    # ---- îlots
    il = fabs["ilots"]
    ig = il.geometry()
    ec = ig.findPointAttrib("ecart_nivellement")
    res["ilots"] = {"faces": len(ig.prims()), "eclats_epars": len(il.geometry(1).points()),
                    "ecart_au_nivellement_m": stats([p.attribValue(ec) for p in ig.points()]) if ec else {},
                    "regles": ["GA-ARB-003", "TQ-SOL-013 (7)"]}
    # ---- caniveaux
    cg = fabs["caniveaux"].geometry(1)
    res["caniveaux"] = {"instances": len(cg.points()),
                        "elements": sum(1 for p in cg.points() if p.attribValue("kind") == "element"),
                        "joints": sum(1 for p in cg.points() if p.attribValue("kind") == "joint")}
    # nœuds par HDA
    res["noeuds"] = {t: O.compter_noeuds(t) for t in ("pj::bordure::1.0", "pj::caniveau::1.0", "pj::sol::1.0",
                                                      "pj::ilot::1.0")}
    res["duree_s"] = round(time.time() - t0, 1)
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in res.items() if k != "noeuds"}, ensure_ascii=False, indent=1)[:6000])
    print("noeuds", {k: (v["noeuds"], v["recursif"]) for k, v in res["noeuds"].items()})


if __name__ == "__main__":
    principal()
