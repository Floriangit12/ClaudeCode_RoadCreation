"""Pilote du lot « ouvrages » (L8 du plan, étape E07 de la chaîne ; hython Houdini 22) : ponts, passages inférieurs,
viaducs.

    hython recon/generateur/fabriquer_ouvrages.py SCENE.yaml [SCENE.yaml ...] [--sortie DOSSIER] [--rendus]
                                                  [--construire-hda] [--vues dessus,oblique,conducteur]

Chaîne (une scène) :
  1. description (clé « ouvrages », FORMAT_DESCRIPTION.md § 17) -> modèle (description_vers_modele + description/ouvrages.py :
     ouvrages[], profil en long et couche des routes) ; contrôles bloquants comme pour toute scène (commun/conformite.py) ;
  2. une COUCHE par route (sous-modèle filtré, sans ouvrage ni profil en long) fabriquée par la chaîne de l'étape 2
     (fabriquer_generateur.fabriquer --l2b : sol, bordures, caniveaux, peinture, rg::autoroute s'il y a un séparateur) :
     deux routes qui se croisent à des niveaux différents ne partagent pas le HeightField de rg::nivellement, qui n'a
     qu'un Z par (x, y) ; sorties de chaque couche dans <scene>/couches/<scene>__<route>/ ;
  3. rg::ouvrages (hda/rg_ouvrages) sur les couches figées (bgeo) : profil en long appliqué aux routes portées,
     tabliers, appuis, culées, joints, garde-corps / BN4, terrain (remblais, talus, talweg, déblais), points ;
  4. exports <scene>/ouvrages/ : scene_ouvrages.usdc (Z haut ; /Monde/Routes, /Monde/Ouvrages, /Monde/Terrain),
     points_ouvrages.json (garde-corps et BN4), maillages_*.npz (contrôle indépendant), ouvrages.json, manifeste ;
  5. rendus (option --rendus) : route seule sur un terrain neutre (sol, talus et talweg gris neutre, aucune végétation,
     aucun bâti), ciel clair et soleil (rendu/rendu_l2b.py réutilisé sans modification), 3 vues (dessus, oblique 3/4,
     conducteur), planche <= 1092 px.
Rien n'est écrit sur C: (dossiers temporaires dans recon/generateur/tmp/hython). Documentation : hda/README_RG.md § 16.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent                 # recon/generateur
DEPOT = ICI.parents[1]
TMP = ICI / "tmp" / "hython"
SORTIE_DEFAUT = DEPOT / "recon" / "out" / "generateur"

if os.environ.get("RG_PILOTE_ENV") != "1":
    TMP.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, RG_PILOTE_ENV="1", PYTHONDONTWRITEBYTECODE="1", TEMP=str(TMP), TMP=str(TMP),
               HOUDINI_TEMP_DIR=str(TMP).replace("\\", "/"), HOUDINI_VEX_DISABLE_JIT="1")
    sys.exit(subprocess.call([sys.executable] + sys.argv, env=env))

import tempfile  # noqa: E402

tempfile.tempdir = str(TMP)
import hou  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI / "hda" / "commun"))
sys.path.insert(0, str(ICI / "rendu"))
import rg_hda_outils as R  # noqa: E402
import fabriquer_generateur as FG  # noqa: E402

VERSION = "fabriquer_ouvrages/1.0 (lot ouvrages)"
REPRENDRE = False
COUCHES = ("Sol", "BEV", "Bordures", "Caniveaux", "Avaloirs", "Equipements", "Marquages")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _r(x, n=4):
    v = round(float(x), n)
    return 0.0 if v == 0 else v


def _ecrire(f, d):
    Path(f).parent.mkdir(parents=True, exist_ok=True)
    Path(f).write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------------------- HDA
def construire_hda(forcer=False):
    d = ICI / "hda" / "rg_ouvrages"
    cible = d / "rg_ouvrages.hdalc"
    if forcer or not cible.exists():
        spec = importlib.util.spec_from_file_location("construire_rg_ouvrages", d / "construire.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cible = mod.construire(d)
    else:
        hou.hda.installFile(str(cible))
    return {f"rg::ouvrages::{R.VERSION}": R.signature(cible)}


# --------------------------------------------------------------------------------------------------- couches
def sous_modele(m, rid, zone):
    """Modèle d'une seule route (couche) : route sans profil en long, couche ni ouvrage ; ses nœuds ; ses profils ;
    les objets, marquages et signaux qui la citent. La chaîne de l'étape 2 la fabrique comme une route seule."""
    r = next(x for x in m["routes"] if x["id"] == rid)
    r2 = {k: v for k, v in r.items() if k not in ("profil_long", "layer", "ouvrages")}
    r2["prov"] = {k: v for k, v in (r.get("prov") or {}).items() if k not in ("profil_long", "layer")}
    out = {k: v for k, v in m.items() if k not in ("routes", "noeuds", "ouvrages", "marquages", "objets", "signaux",
                                                   "zones", "ilots", "carrefours", "controleurs", "graphe_voies")}
    out["meta"] = dict(m["meta"], zone=zone)
    out["routes"] = [r2]
    out["noeuds"] = [dict(n, routes=[rid]) for n in m["noeuds"] if n["id"] in (r["noeud_debut"], r["noeud_fin"])]
    utilises = {sec["profil"] for sec in r["sections"]}
    out["profils"] = [p for p in m["profils"] if p["id"] in utilises]   # familles de la couche (séparateurs) : les siens
    for cle in ("marquages", "objets", "signaux"):
        ids = set(r.get(cle) or [])
        lst = [x for x in m.get(cle) or [] if x.get("id") in ids or x.get("route") == rid]
        if lst:
            out[cle] = lst
    for cle in ("zones", "ilots"):
        lst = [x for x in m.get(cle) or [] if x.get("route") == rid]
        if lst:
            out[cle] = lst
    return out


def figer(geo, couche, route):
    g = hou.Geometry()
    g.merge(geo)
    for nom in ("couche_rendu", "route"):
        if g.findPrimAttrib(nom) is None:
            g.addAttrib(hou.attribType.Prim, nom, "")
    n = len(g.prims())
    g.setPrimStringAttribValues("couche_rendu", [couche] * n)
    g.setPrimStringAttribValues("route", [route] * n)
    return g


# ---- intégration de l'étape 4 : couches de plusieurs routes (groupes reliés par un carrefour du modèle)
VEX_ROUTE_PRIM = r'''
// route d'une primitive d'une couche de plusieurs routes (intégration de l'étape 4) : la route portée d'un ouvrage si
// la primitive est dans son couloir (|t| <= demi-largeur maximale de sa plate-forme + 0,5 m), sinon la route dont la
// référence est la plus proche. Seule la route portée est déformée par rg::ouvrages (profil en long).
vector c = set(@P.x, 0, @P.z);
string r = "";
int pp = (PORTEE != "") ? findattribval(1, "prim", "id", PORTEE) : -1;
if (pp >= 0) {
    int pr; vector uv;
    float d = xyzdist(1, itoa(pp), c, pr, uv);
    float s = primuv(1, "s", pr, uv);
    if (d <= COULOIR && s > 1e-3 && s < LPORTEE - 1e-3) r = PORTEE;
}
if (r == "") {
    int pr; vector uv;
    xyzdist(1, c, pr, uv);
    r = prim(1, "id", pr);
}
s@route = r;
'''


def groupes_couches(m):
    """Groupes de routes fabriqués ensemble en une couche : routes reliées par un carrefour du modèle (carrefour plan,
    giratoire, bifurcation de bretelle : nœuds carrefours[].noeuds) ; sinon une route seule (lot « ouvrages » :
    une couche par route, inchangé). Deux routes d'une même couche ne doivent pas se superposer en plan
    (rg::nivellement : un seul Z par (x, y)). Ordre : première route de chaque groupe dans l'ordre du modèle."""
    ids = [r["id"] for r in m["routes"]]
    parent = {i: i for i in ids}

    def racine(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    noeuds = {n["id"]: n for n in m.get("noeuds") or []}
    for c in m.get("carrefours") or []:
        rs = []
        for nid in c.get("noeuds") or []:
            rs += [r for r in (noeuds.get(nid) or {}).get("routes") or [] if r in parent]
        rs += [b.get("route") for b in c.get("branches") or [] if b.get("route") in parent]
        for a, b in zip(rs, rs[1:]):
            parent[racine(a)] = racine(b)
    groupes = {}
    for i in ids:
        groupes.setdefault(racine(i), []).append(i)
    return sorted(groupes.values(), key=lambda g: ids.index(g[0]))


def nom_groupe(g):
    return g[0] if len(g) == 1 else "+".join(g)


def _routes_citees(x, ids, acc):
    if isinstance(x, str):
        if x in ids:
            acc.add(x)
    elif isinstance(x, dict):
        for v in x.values():
            _routes_citees(v, ids, acc)
    elif isinstance(x, list):
        for v in x:
            _routes_citees(v, ids, acc)
    return acc


def sous_modele_groupe(m, groupe, zone):
    """Modèle d'une couche de plusieurs routes (intégration de l'étape 4) : ses routes (sans profil en long, couche ni
    ouvrage), ses nœuds, ses profils, les carrefours et contrôleurs dont toutes les routes sont dans le groupe, et les
    objets (marquages, objets, signaux, îlots, zones, voies) qui ne citent aucune route d'une autre couche."""
    if len(groupe) == 1:
        return sous_modele(m, groupe[0], zone)
    ids = {r["id"] for r in m["routes"]}
    g = set(groupe)
    out = {k: v for k, v in m.items() if k not in ("routes", "noeuds", "ouvrages", "marquages", "objets", "signaux",
                                                   "zones", "ilots", "carrefours", "controleurs", "graphe_voies")}
    out["meta"] = dict(m["meta"], zone=zone)
    routes = []
    for r in m["routes"]:
        if r["id"] in g:
            r2 = {k: v for k, v in r.items() if k not in ("profil_long", "layer", "ouvrages")}
            r2["prov"] = {k: v for k, v in (r.get("prov") or {}).items() if k not in ("profil_long", "layer")}
            routes.append(r2)
    out["routes"] = routes
    nds = {nid for r in routes for nid in (r["noeud_debut"], r["noeud_fin"])}
    out["noeuds"] = [dict(n, routes=[x for x in n.get("routes") or [] if x in g]) for n in m["noeuds"] if n["id"] in nds]
    utilises = {sec["profil"] for r in routes for sec in r["sections"]}
    out["profils"] = [p for p in m["profils"] if p["id"] in utilises]
    car = [c for c in m.get("carrefours") or [] if _routes_citees(c.get("branches"), ids, set()) <= g
           and set(c.get("noeuds") or []) <= nds]
    if car:
        out["carrefours"] = car
    cids = {c["id"] for c in car}
    ctl = [c for c in m.get("controleurs") or [] if c.get("carrefour") in cids]
    if ctl:
        out["controleurs"] = ctl
    for cle in ("marquages", "objets", "signaux", "zones", "ilots", "graphe_voies"):
        v = m.get(cle)
        if isinstance(v, list):
            lst = [x for x in v if _routes_citees(x, ids, set()) <= g
                   and ((x.get("carrefour") in cids) if isinstance(x, dict) and x.get("carrefour") else True)]
            if lst:
                out[cle] = lst
        elif v is not None and cle == "graphe_voies":
            out[cle] = v
    return out


def portee_du_groupe(m, groupe):
    """(route portée d'un ouvrage dans le groupe, ouvrage) ou (None, None)."""
    for o in m.get("ouvrages") or []:
        c = o.get("construction") or {}
        if c.get("route_portee") in groupe:
            return c["route_portee"], o
    return None, None


def couloir_portee(courbes, rid):
    """Demi-largeur maximale de la plate-forme d'une route (limites extrêmes de toutes ses sections, l1) + 0,5 m."""
    r = next(x for x in courbes["routes"] if x["id"] == rid)
    tm = 0.0
    for sec in r["sections"]:
        for lim in (sec["limites"][0], sec["limites"][-1]):
            tm = max(tm, max(abs(t) for t in lim["t"]))
    return tm + 0.5, float(r["longueur_m"])


def attribuer_routes(geo, refs, portee, couloir, L):
    """Attribut de primitive route d'une couche de plusieurs routes : VEX_ROUTE_PRIM dans un réseau temporaire
    (/obj/attribution_routes : deux Stash et un Attribute Wrangle VEX 64 bits), détruit après la cuisson."""
    code = (VEX_ROUTE_PRIM.replace("LPORTEE", f"{L:.6f}").replace("PORTEE", f'"{portee or ""}"')
            .replace("COULOIR", f"{couloir:.6f}"))
    obj = hou.node("/obj/attribution_routes") or hou.node("/obj").createNode("geo", "attribution_routes")
    for c in obj.children():
        c.destroy()
    s0 = obj.createNode("stash", "couche")
    s0.parm("stash").set(geo)
    s1 = obj.createNode("stash", "references")
    s1.parm("stash").set(refs)
    w = obj.createNode("attribwrangle", "route")
    w.parm("class").set(1)
    w.parm("vex_precision").set("64")
    w.parm("snippet").set(code)
    w.setInput(0, s0)
    w.setInput(1, s1)
    try:
        w.cook(force=True)
    except hou.OperationFailed:
        pass
    if w.errors():
        raise SystemExit("attribution des routes : " + " ; ".join(w.errors()))
    out = w.geometry().freeze()
    obj.destroy()
    return out


def collecter_couche(rid, groupe=None, modele=None, dossier_couche=None):
    """Géométrie fabriquée de la dernière scène de /obj/generateur_l1 (chaîne de l'étape 2) : couches de rendu.
    Couche de plusieurs routes (groupe, étape 4) : route de chaque primitive (attribuer_routes)."""
    obj = hou.node("/obj/generateur_l1")
    sol = obj.node("sol_total") or obj.node("sol")
    pieces = [("Sol", sol, 0), ("BEV", sol, 1), ("Bordures", obj.node("bordures"), 0),
              ("Caniveaux", obj.node("caniveaux"), 0), ("Avaloirs", obj.node("vers_entites"), 2),
              ("Equipements", obj.node("autoroute"), 1), ("Marquages", obj.node("peinture"), 0)]
    tout = hou.Geometry()
    comptes = {}
    for nom, n, k in pieces:
        if n is None:
            continue
        g = n.geometry(k)
        if g is None or not len(g.prims()):
            continue
        tout.merge(figer(g, nom, rid))
        comptes[nom] = len(g.prims())
    refs = hou.Geometry()
    refs.merge(obj.node("graphe").geometry(0))
    if groupe is not None and len(groupe) > 1:
        portee, _o = portee_du_groupe(modele, groupe)
        couloir, L = 0.0, 0.0
        if portee:
            courbes = json.loads((Path(dossier_couche) / "l1" / "courbes_controle.json").read_text(encoding="utf-8"))
            couloir, L = couloir_portee(courbes, portee)
        tout = attribuer_routes(tout, refs, portee, couloir, L)
    return tout, refs, comptes


class Rampe:
    """Raccord vertical d'une jonction de couches (intégration de l'étape 4, choix [G]) : la route A qui finit à la
    jonction (couche de la route portée : par exemple une bretelle mise au niveau de la voie de décélération par
    rg::autoroute, raccord « parallèle ») est relevée de dz × (s − s_m) / (L − s_m) entre s_m (fin des îlots de sa
    bifurcation + 5 m) et la jonction, où elle rejoint le niveau de la route B de l'autre couche. Points concernés : à
    moins de la demi-largeur de A + 0,5 m de sa référence."""

    def __init__(self, modele, rid, dz, s_m, couloir):
        org = modele["repere"]["origine_l93"]
        r = next(x for x in modele["routes"] if x["id"] == rid)
        self.g = np.array([[p[0] - org[0], p[1] - org[1]] for p in r["ligne_reference"]["geometrie"]], dtype=np.float64)
        seg = self.g[1:] - self.g[:-1]
        self.seg, self.lg = seg, np.hypot(seg[:, 0], seg[:, 1])
        self.acc = np.concatenate([[0.0], np.cumsum(self.lg)])
        self.L = float(self.acc[-1])
        self.rid, self.dz, self.s_m, self.couloir = rid, float(dz), float(s_m), float(couloir)

    def st(self, xy):
        """(s, distance) de points (n, 2) sur la référence (projection sur le segment le plus proche)."""
        best_d = np.full(len(xy), np.inf)
        best_s = np.zeros(len(xy))
        for i in range(len(self.lg)):
            a = self.g[i]
            u = np.clip(((xy - a) @ self.seg[i]) / max(self.lg[i] ** 2, 1e-12), 0.0, 1.0)
            pr = a + u[:, None] * self.seg[i]
            d = np.hypot(*(xy - pr).T)
            m = d < best_d
            best_d[m] = d[m]
            best_s[m] = self.acc[i] + u[m] * self.lg[i]
        return best_s, best_d

    def dz_xy(self, xy):
        s, d = self.st(xy)
        f = np.clip((s - self.s_m) / max(self.L - self.s_m, 1e-9), 0.0, 1.0)
        return np.where(d <= self.couloir, self.dz * f, 0.0)

    def appliquer(self, geo):
        """Déforme la géométrie Houdini (x, z = −y) ; renvoie le nombre de points relevés."""
        P = np.array(geo.pointFloatAttribValues("P"), dtype=np.float64).reshape(-1, 3)
        xy = np.stack([P[:, 0], -P[:, 2]], axis=1)
        lo, hi = self.g.min(0) - self.couloir - 1.0, self.g.max(0) + self.couloir + 1.0
        cand = np.nonzero((xy[:, 0] >= lo[0]) & (xy[:, 0] <= hi[0]) & (xy[:, 1] >= lo[1]) & (xy[:, 1] <= hi[1]))[0]
        n = 0
        for k0 in range(0, len(cand), 200000):
            idx = cand[k0:k0 + 200000]
            dz = self.dz_xy(xy[idx])
            m = dz != 0.0
            P[idx[m], 1] += dz[m]
            n += int(m.sum())
        geo.setPointFloatAttribValues("P", P.reshape(-1).tolist())
        return n


def _z_sol(geo_sol, x, y):
    pos, nrm, uvw = hou.Vector3(), hou.Vector3(), hou.Vector3()
    if geo_sol.intersect(hou.Vector3(x, 1000.0, -y), hou.Vector3(0, -1, 0), pos, nrm, uvw) >= 0:
        return pos[1]
    return None


def _sol_seul(geo):
    g = hou.Geometry()
    g.merge(geo)
    g.deletePrims([p for p, c in zip(g.prims(), g.primStringAttribValues("couche_rendu")) if c != "Sol"],
                  keep_points=False)
    return g


def raccorder_couches(modele, d, groupes, scene):
    """Jonctions de couches (route A d'un groupe qui finit au début d'une route B d'un autre groupe, sans nœud commun) :
    écart de niveau mesuré sur les sols fabriqués à 0,50 m de part et d'autre (sur la référence et à ± 1 m), rampe sur A
    (Rampe) si l'écart dépasse 1 mm ; couche de A réécrite. Renvoie [raccords] (écrits dans couche.json)."""
    org = modele["repere"]["origine_l93"]
    routes = {r["id"]: r for r in modele["routes"]}
    grp = {rid: tuple(g) for g in groupes for rid in g}
    out = []
    for a in modele["routes"]:
        ga = np.array(a["ligne_reference"]["geometrie"][-1][:2])
        for b in modele["routes"]:
            if grp[a["id"]] == grp[b["id"]]:
                continue
            gb = np.array(b["ligne_reference"]["geometrie"][0][:2])
            if np.hypot(*(ga - gb)) > 0.01 or a["noeud_fin"] == b["noeud_debut"]:
                continue
            na, nb = nom_groupe(list(grp[a["id"]])), nom_groupe(list(grp[b["id"]]))
            geo_a, geo_b = hou.Geometry(), hou.Geometry()
            geo_a.loadFromFile(str(d / na / "couche.bgeo.sc"))
            geo_b.loadFromFile(str(d / nb / "couche.bgeo.sc"))
            sa, sb = _sol_seul(geo_a), _sol_seul(geo_b)
            ra = Rampe(modele, a["id"], 0.0, 0.0, 0.0)
            rb = Rampe(modele, b["id"], 0.0, 0.0, 0.0)

            def pt(r, s, t):
                i = int(np.clip(np.searchsorted(r.acc, s, side="right") - 1, 0, len(r.lg) - 1))
                u = r.seg[i] / r.lg[i]
                p = r.g[i] + (s - r.acc[i]) * u
                return p[0] - t * u[1], p[1] + t * u[0]
            dzs = []
            for t in (-1.0, 0.0, 1.0):
                za = _z_sol(sa, *pt(ra, ra.L - 0.5, t))
                zb = _z_sol(sb, *pt(rb, 0.5, t))
                if za is not None and zb is not None:
                    dzs.append(zb - za)
            if not dzs:
                continue
            dz = float(np.median(dzs))
            if abs(dz) <= 0.001:
                out.append({"de": a["id"], "vers": b["id"], "ecart_m": round(dz, 4), "rampe": None})
                continue
            # fin des îlots des bifurcations de A (la rampe commence 5 m après) ; 0 sinon
            s_m = 0.0
            cars = {c["id"] for c in modele.get("carrefours") or []
                    if c.get("type") == "bifurcation" and a["id"] in [x.get("route") for x in c.get("branches") or []]}
            for il in modele.get("ilots") or []:
                if il.get("carrefour") in cars:
                    pg = (il.get("polygone") or {}).get("exterieur") or []
                    if pg:
                        s_, _d = ra.st(np.array([[p[0] - org[0], p[1] - org[1]] for p in pg]))
                        s_m = max(s_m, float(s_.max()) + 5.0)
            couloir, _L = couloir_portee(json.loads((d / f"{scene}__{na}" / "l1" / "courbes_controle.json")
                                                    .read_text(encoding="utf-8")), a["id"])
            rp = Rampe(modele, a["id"], dz, s_m, couloir)
            n = rp.appliquer(geo_a)
            geo_a.saveToFile(str(d / na / "couche.bgeo.sc"))
            pente = abs(dz) / max(rp.L - s_m, 1e-9)
            r_ = {"de": a["id"], "vers": b["id"], "ecart_m": round(dz, 4), "couche_relevee": na,
                  "rampe": {"s0": round(s_m, 2), "s1": round(rp.L, 2), "pente_pct": round(100 * pente, 3),
                            "points": n}, "regle": "[G] raccord vertical des couches (README_RG § 18)"}
            out.append(r_)
            print(f"jonction de couches {a['id']} -> {b['id']} : écart {dz:+.3f} m, rampe sur {a['id']} de s = {s_m:.1f} "
                  f"à {rp.L:.1f} ({100 * pente:.2f} %), {n} points")
            if pente > 0.02:
                print(f"ATTENTION : rampe de raccord de {100 * pente:.2f} % sur {a['id']} (plus de 2 %)")
    return out


def fabriquer_couches(modele, chemin_modele, scene, dsc, signatures):
    d = dsc / "couches"
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for groupe in groupes_couches(modele):
        rid = nom_groupe(groupe)
        zone = f"{scene}__{rid}"
        sm = sous_modele_groupe(modele, groupe, zone)
        f = d / rid / "modele_voie.json"
        fg = d / rid / "couche.bgeo.sc"
        fr = d / rid / "references.bgeo.sc"
        fc = d / rid / "couche.json"
        texte = json.dumps(sm, ensure_ascii=False, indent=1) + "\n"
        if REPRENDRE and fg.exists() and fr.exists() and fc.exists() and f.exists() and \
                f.read_text(encoding="utf-8") == texte:
            comptes = json.loads(fc.read_text(encoding="utf-8"))["faces"]     # couche inchangée : reprise (essais)
        else:
            _ecrire(f, sm)
            FG.fabriquer([str(f)], str(d), signatures, l2=True, l2b=True, rendus=False, signalisation="non")
            geo, refs, comptes = collecter_couche(rid, groupe, modele, d / zone)
            geo.saveToFile(str(fg))
            refs.saveToFile(str(fr))
            _ecrire(fc, {"route": rid, "faces": comptes} if len(groupe) == 1 else
                    {"route": rid, "routes": groupe, "faces": comptes})
        c = {"route": rid, "couche": zone, "modele": FG.rel(f), "geometrie": FG.rel(fg), "references": FG.rel(fr),
             "faces": comptes, "layer": next(r for r in modele["routes"] if r["id"] == groupe[0]).get("layer", 0)}
        if len(groupe) > 1:
            c["routes"] = groupe
        out.append(c)
        print(f"{scene} : couche {rid} fabriquée ({sum(comptes.values())} faces : {comptes})")
    # intégration de l'étape 4 : raccord vertical des jonctions de couches (aucune jonction dans D1 à D4)
    groupes = groupes_couches(modele)
    if any(len(g) > 1 for g in groupes) or len(groupes) > 2:
        raccords = raccorder_couches(modele, d, groupes, scene)
        for c in out:
            r_ = [x for x in raccords if x.get("couche_relevee") == c["route"]]
            if r_:
                c["raccords"] = r_
                fc = d / c["route"] / "couche.json"
                j = json.loads(fc.read_text(encoding="utf-8"))
                j["raccords"] = r_
                _ecrire(fc, j)
    return out


# --------------------------------------------------------------------------------------------------- rg::ouvrages
def reseau(scene, couches, chemin_modele):
    obj = hou.node("/obj/ouvrages") or hou.node("/obj").createNode("geo", "ouvrages")
    for c in obj.children():
        c.destroy()
    mr = obj.createNode("merge", "couches")
    mf = obj.createNode("merge", "references")
    for k, c in enumerate(couches):
        a = obj.createNode("file", f"couche_{k}")
        a.parm("file").set(str(DEPOT / c["geometrie"]).replace("\\", "/"))
        mr.setInput(k, a)
        b = obj.createNode("file", f"references_{k}")
        b.parm("file").set(str(DEPOT / c["references"]).replace("\\", "/"))
        mf.setInput(k, b)
    ou = obj.createNode(R.nom_type("ouvrages"), "ouvrages")
    ou.setInput(0, mr)
    ou.setInput(1, mf)
    ou.parm("fichier").set(str(chemin_modele).replace("\\", "/"))
    obj.layoutChildren()
    for k in range(5):                                   # chaque sortie (terrain, points…) est cuite et contrôlée
        try:
            ou.geometry(k)
        except hou.OperationFailed:
            pass
    for c in ou.allSubChildren():
        try:
            c.cook()
        except hou.OperationFailed:
            pass
    err = [f"{c.path()} : {e}" for c in (ou,) + ou.allSubChildren() for e in c.errors()]
    if err:
        raise SystemExit(f"{scene} : erreurs de cuisson de rg::ouvrages\n" + "\n".join(err[:20]))
    return ou


# --------------------------------------------------------------------------------------------------- exports
def _tris(geo, attrs_prim=(), attrs_point=()):
    """(P (n, 3) Z haut, triangles (m, 3), {attr: valeurs par triangle}, {attr: valeurs par point})."""
    P = np.array(geo.pointFloatAttribValues("P"), dtype=np.float64).reshape(-1, 3)
    Pz = np.stack([P[:, 0], -P[:, 2], P[:, 1]], axis=1)
    tri, par = [], {a: [] for a in attrs_prim}
    vals = {a: (geo.primStringAttribValues(a) if geo.findPrimAttrib(a) and geo.findPrimAttrib(a).dataType() ==
                hou.attribData.String else None) for a in attrs_prim}
    for i, pr in enumerate(geo.prims()):
        idx = [v.point().number() for v in pr.vertices()]
        if len(idx) < 3:
            continue
        for k in range(1, len(idx) - 1):
            tri.append((idx[0], idx[k], idx[k + 1]))
            for a in attrs_prim:
                par[a].append(vals[a][i] if vals[a] is not None else "")
    pts = {a: np.array(geo.pointFloatAttribValues(a)) if geo.findPointAttrib(a) else None for a in attrs_point}
    return Pz, np.array(tri, dtype=np.int64).reshape(-1, 3), par, pts


def exporter(ou, modele, chemin_modele, scene, dsc, info, signatures, couches):
    import rendre_l2 as RL
    from pxr import Usd, UsdGeom
    d = dsc / "ouvrages"
    d.mkdir(parents=True, exist_ok=True)
    g_routes, g_ouv, g_ter, g_pts, g_lus = (ou.geometry(k) for k in range(5))
    # maillages pour le contrôle indépendant (validation/controler_ouvrages.py)
    P, T, par, _ = _tris(g_routes, ("route", "couche_rendu", "materiau_id"))
    np.savez_compressed(d / "maillage_routes.npz", P=P, T=T, route=np.array(par["route"]),
                        couche=np.array(par["couche_rendu"]), materiau=np.array(par["materiau_id"]))
    P, T, par, _ = _tris(g_ouv, ("partie", "ouvrage", "materiau_id"))
    np.savez_compressed(d / "maillage_ouvrages.npz", P=P, T=T, partie=np.array(par["partie"]),
                        ouvrage=np.array(par["ouvrage"]), materiau=np.array(par["materiau_id"]))
    P, T, par, pts = _tris(g_ter, ("partie",), ("zone",))
    np.savez_compressed(d / "maillage_terrain.npz", P=P, T=T, partie=np.array(par["partie"]),
                        zone=pts["zone"] if pts["zone"] is not None else np.zeros(len(P)))
    # points d'instances (garde-corps, BN4), repère local Z haut
    pts_out = []
    for p in g_pts.points():
        x, y, z = p.position()
        q = p.attribValue("orient")
        pts_out.append({"id": f"{p.attribValue('ouvrage')}:{p.attribValue('cote')}:{p.number():04d}",
                        "asset": p.attribValue("asset_id"), "famille": p.attribValue("pj_famille"),
                        "P": [_r(x), _r(-z), _r(y)], "orient_xyzw": [_r(q[0], 6), _r(-q[2], 6), _r(q[1], 6), _r(q[3], 6)],
                        "scale": [1.0, 1.0, _r(p.attribValue("echelle_z"), 4)], "hauteur_m": _r(p.attribValue("hauteur_m"), 3),
                        "longueur_m": _r(p.attribValue("longueur_m"), 3), "s": _r(p.attribValue("s"), 3)})
    _ecrire(d / "points_ouvrages.json", {"schema": "pj_points/0.1", "famille": "ouvrages", "scene": scene,
                                         "repere": "local (Lambert-93 - origine du modèle), Z haut, quaternion xyzw",
                                         "origine_l93": modele["repere"]["origine_l93"], "points": pts_out})
    # USD d'échange : routes déformées, ouvrages, terrain (matériaux par materiau_id, bibliothèque route_fr)
    f = d / "scene_ouvrages.usdc"
    if f.exists():
        f.unlink()
    stage = Usd.Stage.CreateNew(str(f))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.Xform.Define(stage, "/Monde")
    couches_usd = couches_geo(g_routes, g_ouv, g_ter)
    ids = set()
    data = {}
    for chemin, geo in couches_usd:
        data[chemin] = RL.maillages(geo, chemin)
        ids |= set(data[chemin])
    liaisons, sources = RL.materiaux(stage, ids, d, racine="/Monde/Looks")
    for chemin, dd in data.items():
        RL.ecrire_couche(stage, chemin, dd, liaisons)
    stage.SetDefaultPrim(stage.GetPrimAtPath("/Monde"))
    stage.GetRootLayer().Save()
    # résumé de l'ouvrage (modèle) et comptes
    parties = {}
    for pr, v in zip(g_ouv.prims(), g_ouv.primStringAttribValues("partie")):
        parties[v] = parties.get(v, 0) + 1
    res = {"schema": "rg_ouvrages/0.1", "scene": scene, "modele": FG.rel(chemin_modele),
           "ouvrages": [{k: o[k] for k in ("id", "type", "routes_portees", "franchit", "tablier", "dispositifs_retenue",
                                            "joints_chaussee_s", "construction") if k in o} for o in modele.get("ouvrages", [])],
           "faces_par_partie": dict(sorted(parties.items())), "points_instances": len(pts_out),
           "faces_routes": len(g_routes.prims()), "faces_terrain": len(g_ter.prims())}
    _ecrire(d / "ouvrages.json", res)
    fichiers = {p.name: sha256(p) for p in sorted(d.iterdir()) if p.is_file() and p.name != "manifest_ouvrages.json"}
    _ecrire(d / "manifest_ouvrages.json", {"schema": "rg_manifest_ouvrages/0.1", "pilote": VERSION, "scene": scene,
                                           "entree": info, "houdini": hou.applicationVersionString(), "hda": signatures,
                                           "couches": couches, "usd_materiaux": sources, "fichiers": fichiers})
    return res


def couches_geo(g_routes, g_ouv, g_ter):
    """[(chemin USD, géométrie)] : /Monde/Routes/<route>/<couche>, /Monde/Ouvrages/<partie>, /Monde/Terrain."""
    out = []
    routes = sorted(set(g_routes.primStringAttribValues("route")))
    for rid in routes:
        for c in COUCHES:
            g = hou.Geometry()
            g.merge(g_routes)
            vr = g.primStringAttribValues("route")
            vc = g.primStringAttribValues("couche_rendu")
            supp = [pr for pr, a, b in zip(g.prims(), vr, vc) if a != rid or b != c]
            g.deletePrims(supp, keep_points=False)
            if len(g.prims()):
                out.append((f"/Monde/Routes/{rid.replace('-', '_')}/{c}", g))
    for partie in sorted(set(g_ouv.primStringAttribValues("partie"))):
        g = hou.Geometry()
        g.merge(g_ouv)
        supp = [pr for pr, a in zip(g.prims(), g.primStringAttribValues("partie")) if a != partie]
        g.deletePrims(supp, keep_points=False)
        out.append((f"/Monde/Ouvrages/{partie}", g))
    out.append(("/Monde/Terrain", g_ter))
    return out


# --------------------------------------------------------------------------------------------------- rendus
ALBEDO_BETON = {"oa_beton_coule": 1.55, "oa_beton_corniche": 1.85}     # × albédo de beton_prefa_lisse (0,242) [G]
SIMPLES_OA = {"oa_terrain": ((0.50, 0.485, 0.445), 0.95),              # = SOL_NEUTRE du rendu route seule
              "oa_joint": ((0.055, 0.052, 0.050), 0.75), "oa_elastomere": ((0.045, 0.045, 0.045), 0.6)}


def looks_ouvrages(stage, ids, racine="/Looks"):
    """Matériaux de rendu des ouvrages : béton coulé et corniches (bibliothèque beton_prefa_lisse, albédo recalé [G]),
    acier galvanisé (bibliothèque), terrain neutre, joints et élastomère (UsdPreviewSurface)."""
    import rendu_l2b as RB
    from pxr import Gf, Sdf, UsdShade
    liaisons, sources = {}, {}
    for mid in sorted(ids):
        chemin = f"{racine}/{mid}"
        if mid in ALBEDO_BETON:
            f = RB._fichier_bib("route", "beton_prefa_lisse")
            m = UsdShade.Material.Define(stage, chemin)
            m.GetPrim().GetReferences().AddReference(f.as_posix())
            k = ALBEDO_BETON[mid]
            alb = stage.OverridePrim(chemin + "/Albedo")
            alb.CreateAttribute("inputs:scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(k, k * 0.985, k * 0.95, 1))
            if stage.GetPrimAtPath(chemin + "/Normale"):
                nm = stage.OverridePrim(chemin + "/Normale")
                nm.CreateAttribute("inputs:scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(0.7, 0.7, 2, 1))
                nm.CreateAttribute("inputs:bias", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(-0.35, -0.35, -1, 0))
            sources[mid] = f"{f.relative_to(DEPOT).as_posix()} (albédo × {k} [G])"
        elif mid in SIMPLES_OA:
            col, rug = SIMPLES_OA[mid]
            m = UsdShade.Material.Define(stage, chemin)
            sh = UsdShade.Shader.Define(stage, chemin + "/Surface")
            sh.CreateIdAttr("UsdPreviewSurface")
            sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*col))
            sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(rug)
            m.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
            sources[mid] = f"UsdPreviewSurface {list(col)}"
        else:
            continue
        liaisons[mid] = UsdShade.Material(stage.GetPrimAtPath(chemin))
    return liaisons, sources


def _frame(modele, rid, s, t=0.0):
    """(x, y) local, tangente (tx, ty) de la route rid en (s, t)."""
    r = next(x for x in modele["routes"] if x["id"] == rid)
    ox, oy = modele["repere"]["origine_l93"][:2]
    g = r["ligne_reference"]["geometrie"]
    acc = 0.0
    for a, b in zip(g, g[1:]):
        l = math.hypot(b[0] - a[0], b[1] - a[1])
        if acc + l >= s - 1e-9 or b is g[-1]:
            u = (s - acc) / l
            tx, ty = (b[0] - a[0]) / l, (b[1] - a[1]) / l
            return (a[0] + u * (b[0] - a[0]) - t * ty - ox, a[1] + u * (b[1] - a[1]) + t * tx - oy), (tx, ty)
        acc += l


def z_surface(geo_routes, x, y, rid=None):
    """Z (haut) de la surface du sol de route le plus haut à la verticale de (x, y) local."""
    best = None
    pos, nrm, uvw = hou.Vector3(), hou.Vector3(), hou.Vector3()
    h = geo_routes.intersect(hou.Vector3(x, 1000.0, -y), hou.Vector3(0, -1, 0), pos, nrm, uvw)
    if h >= 0:
        best = pos[1]
    return best


def vues_scene(modele, g_routes, vues_demandees):
    """Caméras : dessus (centré sur l'ouvrage), oblique 3/4, conducteur (1,20 m dans la voie de droite)."""
    o = modele["ouvrages"][0]
    c = o["construction"]
    rp = c["route_portee"]
    sab0, sab1 = c["s_abouts"]
    s_m = 0.5 * (sab0 + sab1)
    (xm, ym), (tx, ty) = _frame(modele, rp, s_m)
    zc = c["profil_en_long"]["sommet_z_rel"]
    ext = (c["culees"] or {}).get("murs_retour_longueur_m", 0.0) + 2.0
    larg = (sab1 - sab0) + 2 * ext + 46.0
    nx, ny = ty, -tx                                     # normale à droite de la route portée
    L = sab1 - sab0
    dist = max(55.0, 0.95 * L + 30.0)
    vues = {}
    vues["dessus"] = ("dessus", (xm, ym), larg)
    # intégration de l'étape 4 : scène qui compose un ouvrage et des carrefours (scène vitrine) : la vue de dessus
    # couvre l'ouvrage et les carrefours (centres + 45 m), la vue oblique recule au-delà du carrefour le plus éloigné
    ox_, oy_ = modele["repere"]["origine_l93"][:2]
    cars = [(c["centre"][0] - ox_, c["centre"][1] - oy_) if abs(c["centre"][0]) > 1e5 else tuple(c["centre"][:2])
            for c in modele.get("carrefours") or [] if c.get("type") != "bifurcation" and c.get("centre")]
    if cars:
        xs_ = [xm] + [p[0] for p in cars]
        ys_ = [ym] + [p[1] for p in cars]
        vues["dessus"] = ("dessus", (0.5 * (min(xs_) + max(xs_)), 0.5 * (min(ys_) + max(ys_))),
                          max(larg, max(xs_) - min(xs_) + 90.0, max(ys_) - min(ys_) + 90.0))
        dist = max(dist, 1.35 * max(math.hypot(p[0] - xm, p[1] - ym) for p in cars))
    # vue oblique basse (0,15 × distance au-dessus de la route) : tablier, appuis et terrain se lisent de côté
    eye = (xm - 0.55 * dist * tx + 0.80 * dist * nx, ym - 0.55 * dist * ty + 0.80 * dist * ny, zc + 0.15 * dist)
    cible = (xm, ym, zc - 0.55 * max(4.0, c["hc_m"]))
    vues["oblique"] = ("cam", eye, cible, 26.0)
    if cars:
        # scène composée (étape 4) : vue 3/4 haute visant le milieu de l'ouvrage et du carrefour le plus éloigné, depuis
        # l'arrière de la route portée et le côté du carrefour : carrefour au premier plan, ouvrage derrière [G]
        xc, yc = max(cars, key=lambda p: math.hypot(p[0] - xm, p[1] - ym))
        dmax = math.hypot(xc - xm, yc - ym)
        ux, uy = (xc - xm) / max(dmax, 1e-9), (yc - ym) / max(dmax, 1e-9)
        D = 1.6 * dmax + 40.0
        tgt = (0.5 * (xm + xc), 0.5 * (ym + yc))
        eye = (tgt[0] + D * (-0.75 * tx + 0.45 * ux), tgt[1] + D * (-0.75 * ty + 0.45 * uy), 0.22 * D)
        vues["oblique"] = ("cam", eye, (tgt[0], tgt[1], 1.5), 26.0)
    # conducteur : route franchie pour un passage inférieur (on passe sous l'ouvrage), route portée sinon
    if c["fonction"] == "PI" and c.get("route_franchie"):
        rf = c["route_franchie"]
        s_y = c["gabarit"]["s_franchie"]
        cp = c["coupe_franchie"]
        t_v = min((b for b in cp if b[4] == "voie_circulation"), key=lambda b: (b[0] + b[2]))
        t_c = 0.5 * (t_v[0] + t_v[2])
        (xo, yo), _ = _frame(modele, rf, max(1.0, s_y - 45.0), t_c)
        (xt, yt), _ = _frame(modele, rf, s_y + 15.0, t_c)
        rid_c = rf
    else:
        cp = c["coupe_portee"]
        t_v = min((b for b in cp if b[4] == "voie_circulation"), key=lambda b: (b[0] + b[2]))
        t_c = 0.5 * (t_v[0] + t_v[2])
        (xo, yo), _ = _frame(modele, rp, max(1.0, sab0 - 32.0), t_c)
        (xt, yt), _ = _frame(modele, rp, c["s_croisement"] + 6.0, t_c)
        rid_c = rp
    zo = z_surface(g_routes, xo, yo) or 0.0
    zt = z_surface(g_routes, xt, yt) or 0.0
    vues["conducteur"] = ("cam", (xo, yo, zo + 1.20), (xt, yt, zt + 0.80), 24.0)
    return {k: v for k, v in vues.items() if k in vues_demandees}, {"route_conducteur": rid_c}


def composer_signalisation(stage, d, signalisation, scene):
    """Références de la signalisation des couches (l6/signalisation.usda, positions déjà remontées par le profil en
    long) sous /Monde/Signalisation/<couche> ; caméra du conducteur du lot L6 (fabriquer_signalisation.cameras) face à
    l'ensemble désigné par le complément de la scène (vue_conducteur.ensemble), dans la couche qui le porte."""
    import fabriquer_signalisation as FS
    sys.path.insert(0, str(ICI / "description"))
    import yaml_simple as Y
    cpl_f = FS.complement_de(scene)
    cpl = (Y.lire(cpl_f) or {}) if cpl_f else {}
    vc = (cpl.get("vue_conducteur") or {}).get("ensemble")
    cam = None
    for couche, dz_ in signalisation:
        f = Path(dz_) / "l6" / "signalisation.usda"
        if not f.exists():
            continue
        nom = "".join(ch if ch.isalnum() else "_" for ch in couche)
        prim = stage.DefinePrim(f"/Monde/Signalisation/{nom}", "Xform")
        prim.GetReferences().AddReference(os.path.relpath(f, d).replace("\\", "/"))
        ens = json.loads((Path(dz_) / "l6" / "ensembles.json").read_text(encoding="utf-8"))["ensembles"]
        plan = json.loads((Path(dz_) / "l6" / "plan_signalisation.json").read_text(encoding="utf-8"))
        if cam is None and vc and any(e["id"] == vc for e in ens):
            c = FS.cameras(stage, ens, plan, cpl, {}, dz_)
            cam = dict(c["l6_conducteur"], couche=couche)
    return cam


def rendre(ou, modele, scene, dsc, vues_demandees=("dessus", "oblique", "conducteur"), signalisation=()):
    """Rendu route seule (terrain neutre). Intégration de l'étape 4 : signalisation des couches (l6/signalisation.usda
    de chaque couche, référencée sous /Monde/Signalisation/<couche>) et, si le complément de la scène désigne un ensemble
    (vue_conducteur), la vue du conducteur face à cet ensemble (caméra du lot L6) au lieu de la vue « conducteur »."""
    import time
    import ciel as CI
    import planches as PL
    import rendre_l2 as RL
    import rendu_l2b as RB
    from pxr import Gf, Usd, UsdGeom, UsdRender
    t0 = time.time()
    d = dsc / "rendus"
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.png"):
        f.unlink()
    g_routes, g_ouv, g_ter = ou.geometry(0), ou.geometry(1), ou.geometry(2)
    usd = d / "scene_rendu.usdc"
    if usd.exists():
        usd.unlink()
    stage = Usd.Stage.CreateNew(str(usd))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    monde = stage.DefinePrim("/Monde", "Xform")
    data = {}
    for chemin, geo in couches_geo(g_routes, g_ouv, g_ter):
        data[chemin] = (RL.maillages(geo, chemin), geo)
    ids = set()
    for v, _g in data.values():
        ids |= set(v)
    ids_oa = {m for m in ids if m in ALBEDO_BETON or m in SIMPLES_OA}
    commun = Path(dsc).parent / "_rendu_commun" / "textures"
    tex, stats_tex = RB.textures_rendu(commun, set(), route_seule=True)
    liaisons, sources = RB.creer_looks(stage, ids - ids_oa, tex, route_seule=True, scene=scene)
    l2, s2 = looks_ouvrages(stage, ids_oa)
    liaisons.update(l2)
    sources.update(s2)
    for chemin, (dd, geo) in data.items():
        RL.ecrire_couche(stage, chemin, dd, liaisons)
        for mid in dd:
            UsdGeom.Mesh(stage.GetPrimAtPath(f"{chemin}/{RB._nom_usd(mid)}")).CreateDoubleSidedAttr(True)
        if chemin.endswith("/Sol") and geo.findPointAttrib("s") and geo.findPointAttrib("t"):
            RB.st_route(stage, geo, chemin)          # cartes d'usure du sol en (s, t) de sa route
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            RB.uv_secours(prim)
    # ciel clair et soleil (route seule) ; aucun sol de présentation : le terrain s'étend à 2 km
    ciel = d / "ciel.exr"
    info_ciel = CI.ciel_exr(ciel, RB.SOLEIL_ELEVATION, RB.SOLEIL_AZIMUT, RB.TURBIDITE, RB.PART_CIEL, RB.SOLEIL,
                            nuages=0.0, voile=0.92, teinte_voile=RB.VOILE_ROUTE_SEULE)
    e_tot = RB.SOLEIL * math.sin(math.radians(RB.SOLEIL_ELEVATION)) * (1.0 + RB.PART_CIEL)
    l_sol = [c * e_tot / math.pi / RB.CIEL_FOND * t for c, t in zip(RB.SOL_NEUTRE, (0.985, 0.965, 0.93))]
    ciel_fond = d / "ciel_fond.exr"
    CI.ciel_exr(ciel_fond, RB.SOLEIL_ELEVATION, RB.SOLEIL_AZIMUT, RB.TURBIDITE, RB.PART_CIEL, RB.SOLEIL, nuages=0.0,
                sol_radiance=l_sol, voile=0.92, teinte_voile=RB.VOILE_ROUTE_SEULE)
    RB.lumieres(stage, ciel, ciel_fond, sol_sans_ombre=None)
    vues, info_v = vues_scene(modele, g_routes, vues_demandees)
    res, cams = {}, {}
    cam_l6 = None
    if signalisation:
        cam_l6 = composer_signalisation(stage, d, signalisation, scene)
        if cam_l6 is not None and "conducteur" in vues:
            vues.pop("conducteur")
            res["l6_conducteur"] = RB.RES
            cams["l6_conducteur"] = cam_l6
            info_v = {"conducteur": "lot L6 (complément de la scène, vue_conducteur)", "ensemble": cam_l6["ensemble"],
                      "couche": cam_l6["couche"]}
    for nom, v in vues.items():
        if v[0] == "dessus":
            (xc, yc), larg = v[1], v[2]
            zc = z_surface(g_routes, xc, yc) or 0.0
            cams[nom] = RB._dessus(stage, (xc, yc), zc, larg, RB.RES_DESSUS)
            res[nom] = RB.RES_DESSUS
        else:
            _k, oeil, cible, foc = v
            RB._camera(stage, nom, oeil, cible, foc, RB.RES)
            cams[nom] = {"oeil": [round(x, 3) for x in oeil], "cible": [round(x, 3) for x in cible], "focale_mm": foc}
            res[nom] = RB.RES
    rs = UsdRender.Settings.Define(stage, "/Render/reglages")
    rs.CreateResolutionAttr(Gf.Vec2i(*RB.RES))
    stage.SetDefaultPrim(monde)
    stage.GetRootLayer().Save()
    pngs = RB.rendre(usd, res, d)
    tu = {}
    for nom, png in pngs.items():
        m = RL.tuiles(png, d / "tuiles" / nom)
        tu[nom] = [x["fichier"] for x in m.get("tuiles", [])]
    o = modele["ouvrages"][0]["construction"]
    leg = {"dessus": f"dessus ({vues['dessus'][2]:.0f} m de large)" if "dessus" in vues else "",
           "oblique": "vue oblique 3/4 de l'ouvrage",
           "conducteur": "conducteur à 1,20 m (" + ("sous l'ouvrage" if o["fonction"] == "PI" else "vers l'ouvrage") + ")"}
    if cam_l6 is not None:
        leg["l6_conducteur"] = f"conducteur (1,20 m) face à {cam_l6['ensemble']}"
        if signalisation:
            leg["dessus"] += ", signalisation posée"
    planche = PL.planche_vues(scene, pngs, [v for v in ("dessus", "oblique", "conducteur", "l6_conducteur") if v in pngs],
                              d / f"planche_{scene}.png", legendes=leg)
    RL.nettoyer_rat()
    dyn = {k: RB.dynamique(v) for k, v in pngs.items()}
    man = {"schema": "rg_rendus_ouvrages/0.1", "scene": scene, "moteur": "Karma XPU (husk)", "echantillons": RB.ECHANTILLONS,
           "mode": "route seule sur terrain neutre (sol, talus, talweg : gris neutre ; aucune végétation, aucun bâti)",
           "ciel": info_ciel, "soleil": {"elevation_deg": RB.SOLEIL_ELEVATION, "azimut_deg": RB.SOLEIL_AZIMUT,
                                         "normalize": True},
           "cameras": cams, "conducteur": info_v, "images": {k: v.name for k, v in pngs.items()}, "tuiles": tu,
           "planche": planche.name if planche else None, "materiaux": sources, "L1": dyn,
           "duree_s": round(time.time() - t0, 1)}
    if signalisation:
        man["signalisation"] = [FG.rel(Path(dz_) / "l6" / "signalisation.usda") for _c, dz_ in signalisation]
    _ecrire(d / "manifest_rendus.json", man)
    print(f"{scene} : {len(pngs)} rendus ({round(time.time() - t0)} s) -> {d}")
    return man


# --------------------------------------------------------------------------------------------------- signalisation
def dz_portee(modele, rid, couloir):
    """dz(x, y) local : profil en long de la route portée rid (routes[].profil_long, z NGF − z de l'origine) à
    l'abscisse du point projeté sur sa référence, si le point est à moins de couloir + 10 m de la référence et
    dans le tronçon ; 0 ailleurs (signalisation des autres routes de la couche, au niveau du terrain)."""
    r = next(x for x in modele["routes"] if x["id"] == rid)
    pl = (r.get("profil_long") or {}).get("z") or []
    if not pl:
        return None
    z0 = float(modele["repere"]["origine_l93"][2])
    S = np.array([p[0] for p in pl], dtype=np.float64)
    Z = np.array([p[1] for p in pl], dtype=np.float64) - z0
    ox, oy = modele["repere"]["origine_l93"][:2]
    g = np.array([[p[0] - ox, p[1] - oy] for p in r["ligne_reference"]["geometrie"]], dtype=np.float64)
    seg = g[1:] - g[:-1]
    lg = np.hypot(seg[:, 0], seg[:, 1])
    acc = np.concatenate([[0.0], np.cumsum(lg)])
    L = float(acc[-1])

    def dz(x, y):
        q = np.array([x, y], dtype=np.float64)
        u = np.clip(((q - g[:-1]) * seg).sum(1) / np.maximum(lg * lg, 1e-12), 0.0, 1.0)
        pr = g[:-1] + seg * u[:, None]
        d = np.hypot(*(q - pr).T)
        k = int(np.argmin(d))
        s = acc[k] + u[k] * lg[k]
        if d[k] > couloir + 10.0 or s <= 0.0 or s >= L:
            return 0.0
        return float(np.interp(s, S, Z))
    return dz


def signalisation_couches(modele, scene, dsc, couches, sortie, sig_l6):
    """Signalisation verticale et feux (lot L6) de chaque couche, avec le complément de la scène : posée sur le sol
    plat de la couche, remontée par le profil en long de la route portée de la couche (dz_portee) ; le modèle de la
    couche est recopié dans son dossier de scène (lu par le plan). Renvoie [(couche, dossier de la couche)]."""
    import fabriquer_signalisation as FS
    cpl = FS.complement_de(scene)
    faits = []
    for c in couches:
        dz_ = dsc / "couches" / c["couche"]
        groupe = c.get("routes") or [c["route"]]
        (dz_ / "modele_voie.json").write_bytes((DEPOT / c["modele"]).read_bytes())
        portee, _o = portee_du_groupe(modele, groupe)
        fonctions = []
        courbes = json.loads((dz_ / "l1" / "courbes_controle.json").read_text(encoding="utf-8"))
        if portee:
            f_p = dz_portee(modele, portee, couloir_portee(courbes, portee)[0])
            if f_p is not None:
                fonctions.append(f_p)
        for rc in c.get("raccords") or []:                  # rampe de raccord de la jonction de couches
            if rc.get("rampe"):
                rp = Rampe(modele, rc["de"], rc["ecart_m"], rc["rampe"]["s0"], couloir_portee(courbes, rc["de"])[0])
                fonctions.append(lambda x, y, rp=rp: float(rp.dz_xy(np.array([[x, y]], dtype=np.float64))[0]))
        corr = (lambda x, y: sum(fn(x, y) for fn in fonctions)) if fonctions else None
        FS.fabriquer_scene(str(dz_), sortie, sig_l6, rendus=False, complement=cpl, correction_z=corr)
        faits.append((c["couche"], dz_))
    return faits


# --------------------------------------------------------------------------------------------------- scène
def fabriquer_scene_preparee(scene, chemin_modele, info, entree, sortie, signatures, rendus=False,
                             vues=("dessus", "oblique", "conducteur"), sig_l6=None):
    """Une scène à ouvrages déjà compilée (fabriquer_generateur.fabriquer, intégration de l'étape 4) : couches, rg::ouvrages,
    exports ; signalisation des couches si sig_l6 (HDA rg::signalisation installée) ; rendus (avec la signalisation)."""
    modele = json.loads(Path(chemin_modele).read_text(encoding="utf-8"))
    if not modele.get("ouvrages"):
        raise SystemExit(f"{scene} : aucun ouvrage dans le modèle")
    dsc = Path(sortie) / scene
    couches = fabriquer_couches(modele, chemin_modele, scene, dsc, signatures)
    ou = reseau(scene, couches, chemin_modele)
    res = exporter(ou, modele, chemin_modele, scene, dsc, info, signatures, couches)
    print(f"{scene} : ouvrages {res['faces_par_partie']}, {res['points_instances']} points -> {FG.rel(dsc / 'ouvrages')}")
    sig = []
    if sig_l6:
        sig = signalisation_couches(modele, scene, dsc, couches, sortie, sig_l6)
    if rendus:
        rendre(ou, modele, scene, dsc, vues, signalisation=sig)
    return dsc


def fabriquer_scene(entree, sortie, signatures, rendus=False, vues=("dessus", "oblique", "conducteur")):
    scene, chemin_modele, info = FG.preparer_entree(entree, sortie)
    return fabriquer_scene_preparee(scene, chemin_modele, info, entree, sortie, signatures, rendus=rendus, vues=vues)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("entrees", nargs="*")
    ap.add_argument("--sortie", default=str(SORTIE_DEFAUT))
    ap.add_argument("--construire-hda", action="store_true")
    ap.add_argument("--rendus", action="store_true")
    ap.add_argument("--vues", default="dessus,oblique,conducteur")
    ap.add_argument("--reprendre-couches", action="store_true",
                    help="essais : reprendre les couches déjà fabriquées si leur sous-modèle est inchangé")
    a = ap.parse_args()
    global REPRENDRE
    REPRENDRE = a.reprendre_couches
    signatures = FG.construire_hda(forcer=False, l2=True)
    signatures.update(construire_hda(forcer=a.construire_hda))
    print("HDA :", ", ".join(f"{k} ({v[:12]})" for k, v in signatures.items() if "ouvrages" in k))
    for e in a.entrees:
        fabriquer_scene(e, a.sortie, signatures, rendus=a.rendus, vues=tuple(x for x in a.vues.split(",") if x))
    return 0


if __name__ == "__main__":
    sys.exit(main())
