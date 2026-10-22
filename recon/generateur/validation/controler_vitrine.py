# -*- coding: utf-8 -*-
"""Contrôle indépendant de la scène vitrine de l'étape 4 (et de toute scène à ouvrages de plusieurs couches) — Python
du système, numpy, sans Houdini : mesures sur les maillages exportés (ouvrages/maillage_*.npz) et sur les instances de
signalisation posées dans chaque couche (couches/<couche>/l6/instances.json).

    python recon/generateur/validation/controler_vitrine.py [recon/out/generateur/<scene> ...] [--json SORTIE]

Critères (intégration de l'étape 4), chacun avec sa valeur, son seuil et sa raison :
  V1 terrain_sous_toutes_routes  au centre de chaque triangle du sol (couche Sol) de TOUTES les routes (portée, franchie
                                 et routes à niveau : bretelle, carrefour), le terrain est sous le sol d'au moins 5 mm
                                 (le contrôle du lot « ouvrages » ne vérifie que la route portée et la route franchie) ;
  V2 jonction_des_couches        deux tronçons qui se suivent dans deux couches (fin de l'un = début de l'autre) : écart
                                 de Z du sol de part et d'autre de la jonction, sur la largeur commune, ≤ 5 mm ;
  V3 bifurcation_en_palier       les routes non portées n'ont pas été déformées : Z du sol de la route portée au droit de
                                 la fin du dernier objet qui la relie à une autre route (bifurcation) = 0 à 1 mm (profil
                                 en long du modèle) ;
  V4 supports_au_sol             pied de chaque support de signalisation et de feux (instances « support ») : la plus haute
                                 surface sous lui (sol des routes, terrain) est à ± 5 cm du pied ; support posé sur
                                 l'abord, hors de l'emprise fabriquée (motif du lot L6) : le lot le descend de 0,40 m
                                 sous le sol supposé [G], la surface doit être entre le bas du support et le pied + 5 cm
                                 — ni en l'air, ni enterré au-delà de sa fiche ;
  V5 signalisation_sans_echec    ensembles de chaque couche : 0 en échec de placement (statut du lot L6).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
SORTIE = DEPOT / "recon" / "out" / "generateur"
sys.path.insert(0, str(ICI))
from controler_ouvrages import Maillage, Route  # noqa: E402

SCENES = ("V01_demi_echangeur_voie_rapide",)


def _r(x, n=4):
    return None if x is None else (0.0 if round(float(x), n) == 0 else round(float(x), n))


def controler(dsc):
    dsc = Path(dsc)
    m = json.loads((dsc / "modele_voie.json").read_text(encoding="utf-8"))
    org = m["repere"]["origine_l93"]
    o = dsc / "ouvrages"
    r = np.load(o / "maillage_routes.npz")
    t = np.load(o / "maillage_terrain.npz")
    res = {"scene": dsc.name, "criteres": {}}
    K = res["criteres"]
    ter = Maillage(t["P"], t["T"], t["partie"] == "terrain")
    # ---- V1 : terrain sous le sol de toutes les routes (centres des triangles du sol)
    sol_mask = r["couche"] == "Sol"
    T = r["T"][sol_mask]
    P = r["P"]
    cen = P[T].mean(axis=1)
    rid = r["route"][sol_mask]
    rng = np.random.default_rng(0)                       # échantillon déterministe : 4000 triangles par route au plus
    viol, n, pire, par_route = 0, 0, -1e9, {}
    for route in sorted(set(rid.tolist())):
        idx = np.nonzero(rid == route)[0]
        if len(idx) > 4000:
            idx = np.sort(rng.choice(idx, 4000, replace=False))
        v_r = 0
        for i in idx:
            x, y, z = cen[i]
            zt = ter.z(x, y)
            if not len(zt):
                continue
            n += 1
            dz = zt.max() - z
            pire = max(pire, dz)
            if dz > -0.005:
                v_r += 1
        par_route[route] = {"echantillons": int(len(idx)), "violations": v_r}
        viol += v_r
    K["V1_terrain_sous_toutes_routes"] = {"valeur": viol, "seuil": "0 point où le terrain affleure le sol (terrain <= sol "
                                          "- 5 mm)", "atteint": viol == 0 and n > 0, "echantillons": n,
                                          "pire_m": _r(pire, 3), "par_route": par_route}
    # ---- V2 : jonctions de couches (fin d'un tronçon = début d'un autre, sans nœud commun)
    routes = {x["id"]: x for x in m["routes"]}
    sol = Maillage(P, r["T"], sol_mask)
    jonctions = []
    for a in m["routes"]:
        ga = np.array(a["ligne_reference"]["geometrie"][-1][:2])
        for b in m["routes"]:
            if a is b:
                continue
            gb = np.array(b["ligne_reference"]["geometrie"][0][:2])
            if np.hypot(*(ga - gb)) < 0.01 and a["noeud_fin"] != b["noeud_debut"]:
                jonctions.append((a["id"], b["id"]))
    j_out = []
    ecart = 0.0
    for ida, idb in jonctions:
        ra, rb = Route(routes[ida], org), Route(routes[idb], org)
        la = ra.s[-1]
        dzs = []
        for tt in np.linspace(-3.0, 3.0, 13):
            xa, ya = ra.xy(la - 0.05, tt)
            xb, yb = rb.xy(0.05, tt)
            za = Maillage(P, r["T"], sol_mask & (r["route"] == ida)).z(xa, ya)
            zb = Maillage(P, r["T"], sol_mask & (r["route"] == idb)).z(xb, yb)
            if len(za) and len(zb):
                dzs.append(abs(za.max() - zb.max()))
        e = max(dzs) if dzs else None
        j_out.append({"de": ida, "vers": idb, "ecart_z_max_m": _r(e, 4), "points": len(dzs)})
        if e is not None:
            ecart = max(ecart, e)
    K["V2_jonction_des_couches"] = {"valeur": _r(ecart, 4), "seuil": "<= 0,005 m", "jonctions": j_out,
                                    "atteint": bool(j_out) and all(j["ecart_z_max_m"] is not None and
                                                                   j["ecart_z_max_m"] <= 0.005 for j in j_out)}
    # ---- V3 : bifurcations en palier
    v3 = []
    for c in m.get("ouvrages") or []:
        cc = c["construction"]
        rp = cc["route_portee"]
        pl = {round(s, 3): z - org[2] for s, z in routes[rp]["profil_long"]["z"]}
        s_debut = next(e["s1"] for e in cc["profil_en_long"]["elements"] if e["type"] == "palier" and "s1" in e)
        for car in m.get("carrefours") or []:
            if car.get("type") != "bifurcation" or rp not in [b["route"] for b in car["branches"]]:
                continue
            ilots = [i for i in m.get("ilots") or [] if i.get("carrefour") == car["id"]]
            ra = Route(routes[rp], org)
            s_max = 0.0
            for il in ilots:
                pg = il.get("polygone") or {}
                for p in (pg.get("exterieur") or []) if isinstance(pg, dict) else pg:
                    s_, _t = ra.st(p[0] - org[0], p[1] - org[1])
                    s_max = max(s_max, s_)
            zmax = max(abs(z) for s, z in pl.items() if s <= s_max + 1e-6) if pl else None
            v3.append({"ouvrage": c["id"], "bifurcation": car["id"], "fin_des_ilots_s": _r(s_max, 2),
                       "debut_du_raccordement_s": _r(s_debut, 2), "z_profil_max_m": _r(zmax, 4)})
    K["V3_bifurcation_en_palier"] = {"valeur": v3, "seuil": "fin des îlots de la bifurcation avant le début du "
                                     "raccordement ; z du profil = 0 (± 1 mm)",
                                     "atteint": bool(v3) and all(x["fin_des_ilots_s"] < x["debut_du_raccordement_s"] and
                                                                 x["z_profil_max_m"] <= 0.001 for x in v3)}
    # ---- V4 / V5 : signalisation des couches
    surf = Maillage(np.concatenate([P, t["P"]]), np.concatenate([r["T"][np.isin(r["couche"], ["Sol", "Bordures"])],
                                                                 t["T"][t["partie"] == "terrain"] + len(P)]))
    sup, ecarts, statuts = 0, [], {}
    for d in sorted((dsc / "couches").glob("*__*")):
        fi = d / "l6" / "instances.json"
        if not fi.exists():
            continue
        ens = {e["id"]: e for e in json.loads((d / "l6" / "ensembles.json").read_text(encoding="utf-8"))["ensembles"]}
        for e in ens.values():
            statuts[e["statut"]] = statuts.get(e["statut"], 0) + 1
        for x in json.loads(fi.read_text(encoding="utf-8"))["instances"]:
            if x["kind"] != "support":
                continue
            zs = surf.z(x["p"][0], x["p"][1])
            if not len(zs):
                continue
            sup += 1
            fiche = 0.40 if "hors de l'emprise fabriquée" in (ens.get(x["ensemble"]) or {}).get("motif", "") else 0.0
            dz = zs.max() - x["p"][2]                     # > 0 : surface au-dessus du pied ; < 0 : pied au-dessus
            hors = max(dz - (fiche + 0.05), -(dz + 0.05), 0.0)   # pied du lot L6 : déjà descendu de la fiche
            ecarts.append((hors, round(float(dz), 3), fiche, x["ensemble"], d.name))
    emax = max(ecarts, default=(None, None, 0.0, "", ""))
    K["V4_supports_au_sol"] = {"valeur": _r(emax[0], 3), "seuil": "surface sous le support dans [pied - fiche - 0,05 ; "
                               "pied + 0,05] m (fiche 0,40 m hors de l'emprise fabriquée, 0 sinon) : dépassement 0",
                               "supports": sup, "pire": {"ecart_surface_pied_m": emax[1], "fiche_m": emax[2],
                                                         "ensemble": emax[3], "couche": emax[4]},
                               "atteint": bool(sup > 0 and emax[0] is not None and emax[0] <= 1e-9)}
    K["V5_signalisation_sans_echec"] = {"valeur": statuts.get("echec", 0), "seuil": "0 ensemble en échec",
                                        "statuts": statuts, "atteint": statuts.get("echec", 0) == 0 and bool(statuts)}
    for v in K.values():
        v["atteint"] = bool(v["atteint"])
    res["atteint"] = all(v["atteint"] for v in K.values())
    return res


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--json")
    a = ap.parse_args()
    out = []
    for d in [Path(s) for s in a.scenes] or [SORTIE / s for s in SCENES]:
        r = controler(d)
        out.append(r)
        print(r["scene"], "atteint" if r["atteint"] else "NON ATTEINT")
        for k, v in r["criteres"].items():
            print(f"  {k}: {json.dumps(v['valeur'], ensure_ascii=False)[:200]} (seuil {v['seuil']}) -> "
                  f"{'oui' if v['atteint'] else 'NON'}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
