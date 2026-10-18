# -*- coding: utf-8 -*-
"""Contrôle du lot « scenes » (17/10/2026) : carrefours (J1-J5), giratoires (G1-G3), autoroutes (A1-A4).

    python recon/generateur/validation/controler_scenes.py [--determinisme] [--json validation/rapport_scenes.json]

1. Chaque scène compile en modèle valide (validateur, provenance exigée : 0 erreur ; 0 non-conformité bloquante).
2. Les « attendus » déclarés dans chaque scène sont mesurés sur le modèle et le rapport de compilation (valeur
   mesurée, attendu, tolérance, atteint) — écrits d'après les règles citées dans la scène, pas recopiés des sorties.
3. Cohérence géométrique : îlots hors des voies (surface d'îlot en saillie sur les voies motorisées des routes),
   branches qui se rejoignent (écart longitudinal des extrémités au centre), îlots de giratoire dans leur enveloppe.
4. Rétrocompatibilité : S01-S12, exemples et scènes de Meylan compilent à l'octet comme avant le lot (empreintes
   tmp/scenes/empreintes_avant.json, prises avant toute modification).
5. Déterminisme (option) : deux compilations de J5 et G1 donnent des modèles identiques à l'octet.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
sys.path.insert(0, str(GEN))
from commun import profil as PF  # noqa: E402
from description import description_vers_modele as D  # noqa: E402
from description import yaml_simple  # noqa: E402
from description.plan_reseau import TraceModele  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

SCENES = sorted((GEN / "scenes_carrefours").glob("J*.yaml")) + sorted((GEN / "scenes_giratoires").glob("G*.yaml")) \
    + sorted((GEN / "scenes_autoroutes").glob("A*.yaml"))


def compiler(f: Path):
    octets = f.read_bytes()
    d = yaml_simple.charger(octets.decode("utf-8"))
    src = str(f.relative_to(DEPOT)).replace("\\", "/")
    m, r = D.compiler(copy.deepcopy(d), src, hashlib.sha256(octets).hexdigest())
    return m, r, d


def octets(m):
    return (json.dumps(m, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


# ---------------------------------------------------------------------------------------------------- géométrie
def polygones_voies(m):
    """Emprise des voies motorisées de toutes les routes (polygones shapely), échantillonnage 1 m."""
    prof = {p["id"]: p for p in m["profils"]}
    out = []
    for r in m["routes"]:
        tr = TraceModele(r["ligne_reference"]["geometrie_reguliere"])
        for sec in r["sections"]:
            p = prof[sec["profil"]]
            n = max(2, int((sec["s1"] - sec["s0"]) / 1.0) + 1)
            ss = [sec["s0"] + (sec["s1"] - sec["s0"]) * k / (n - 1) for k in range(n)]
            for i, b in enumerate(p["bandes"]):
                if b["type"] not in PF.VOIES_MOTORISEES:
                    continue
                T = [D.t_limites(p, s) for s in ss]
                g = [tr.point_st(s, t[i]) for s, t in zip(ss, T)]
                d = [tr.point_st(s, t[i + 1]) for s, t in zip(ss, T)]
                poly = Polygon(g + d[::-1]).buffer(0)
                if not poly.is_empty and poly.area > 1e-6:
                    out.append((r["id"], b["id"], poly))
    return out


def ilots_hors_voies(m):
    """Surface (m²) de chaque îlot en saillie (entité, hors îlots portés par un profil et hors îlots peints) posée sur
    une voie motorisée d'une route. Seuil : 0,05 m² (tolérance de discrétisation)."""
    voies = polygones_voies(m)
    res = []
    for il in m.get("ilots", []):
        if il.get("porte_par_profil") or il["terre_plein"].get("franchissable") == "peint" or il["type"] == "central_giratoire":
            continue
        ext = il["polygone"]["exterieur"]
        P = Polygon(ext).buffer(0)
        sur = 0.0
        for rid, bid, v in voies:
            if v.intersects(P):
                sur += v.intersection(P).area
        res.append((il["id"], round(sur, 3)))
    return res


# ---------------------------------------------------------------------------------------------------- mesures
def objets(r):
    return (r.get("reseau") or {}).get("objets", [])


def signaux_codes(m):
    out = {}
    for s in m.get("signaux", []):
        out[s["code"]] = out.get(s["code"], 0) + 1
        for p in s.get("panonceaux", []):
            out[p["code"]] = out.get(p["code"], 0) + 1
    return out


def ctrl(r, nom):
    return [c for c in (r.get("reseau") or {}).get("controles", []) if c["controle"] == nom]


def cmp(liste, scene, cle, attendu, mesure, tol=1e-3):
    if mesure is None:
        ok = False
    elif isinstance(attendu, (int, float)) and isinstance(mesure, (int, float)):
        ok = abs(float(attendu) - float(mesure)) <= tol + 1e-9
    else:
        ok = attendu == mesure
    liste.append({"scene": scene, "attendu": cle, "valeur_attendue": attendu, "valeur_mesuree": mesure, "tolerance": tol,
                  "atteint": bool(ok)})


def profil_extremite(m, rid):
    r = next(x for x in m["routes"] if x["id"] == rid)
    prof = {p["id"]: p for p in m["profils"]}
    return prof[r["sections"][0]["profil"]]


def attendus_scene(nom, m, r, d):
    """Attendus mesurables → [{attendu, valeur_attendue, valeur_mesuree, tolerance, atteint}]."""
    a = d.get("attendus") or {}
    out = []
    obs = objets(r)
    sig = signaux_codes(m)
    c0 = obs[0] if obs else {}
    if nom.startswith("J"):
        br = c0.get("branches", {})
        cmp(out, nom, "branches", a.get("branches"), len(br))
        for k, v in (a.get("frontiere_m") or {}).items():
            cmp(out, nom, f"frontiere_m.{k}", v, (br.get(k) or {}).get("frontiere_m"), 0.01)
        for k, v in (a.get("ligne") or {}).items():
            lg = (br.get(k) or {}).get("ligne") or {}
            if "type" in v:
                cmp(out, nom, f"ligne.{k}.type", v["type"], lg.get("type"))
            if "distance_au_centre_m" in v:
                cmp(out, nom, f"ligne.{k}.distance_au_centre_m", v["distance_au_centre_m"], lg.get("x0_m"), 0.01)
        for k, v in (a.get("passage") or {}).items():
            pp = (br.get(k) or {}).get("passage") or {}
            if "bord_proche_au_centre_m" in v:
                cmp(out, nom, f"passage.{k}.bord_proche", v["bord_proche_au_centre_m"], pp.get("x0_m"), 0.01)
            if "largeur_m" in v:
                cmp(out, nom, f"passage.{k}.largeur", v["largeur_m"], pp.get("largeur_m"), 0.01)
        for k, v in (a.get("sas") or {}).items():
            sa = (br.get(k) or {}).get("sas") or {}
            cmp(out, nom, f"sas.{k}.avant", v.get("avant_m"), sa.get("x_avant"), 0.01)
            cmp(out, nom, f"sas.{k}.arriere", v.get("arriere_m"), sa.get("x_arriere"), 0.01)
        car = next((c for c in m.get("carrefours", []) if c["id"] == c0.get("id")), {})
        for k, v in (a.get("continue_approche_m") or {}).items():
            b = next((b for b in car.get("branches", []) if b["id"] == f"B-{k}"), {})
            cmp(out, nom, f"continue_approche.{k}", v, (b.get("ligne_axiale_approche") or {}).get("longueur_m", 0))
        for k, v in (a.get("panneaux") or {}).items():
            cmp(out, nom, f"panneaux.{k}", v, sig.get(k, 0))
        if "trajectoires" in a:
            cmp(out, nom, "trajectoires", a["trajectoires"], c0.get("trajectoires"))
        for k, v in (a.get("conflits") or {}).items():
            cmp(out, nom, f"conflits.{k}", v, (c0.get("conflits") or {}).get(k))
        if "zone_conflit_m2" in a:
            cmp(out, nom, "zone_conflit_m2", a["zone_conflit_m2"], c0.get("zone_conflit_m2"), 0.5)
        if "coins_rayon_m" in a and isinstance(a["coins_rayon_m"], (int, float)):
            rs = sorted({b["coin_droit"]["rayon_m"] for b in car.get("branches", []) if b.get("coin_droit")})
            cmp(out, nom, "coins_rayon_m", [float(a["coins_rayon_m"])], rs)
        if isinstance(a.get("coins_rayon_m"), dict):
            rs = sorted(b["coin_droit"]["rayon_m"] for b in car.get("branches", []) if b.get("coin_droit"))
            cmp(out, nom, "coins_rayon_m.sud_est", float(a["coins_rayon_m"]["sud_est"]),
                next((b["coin_droit"]["rayon_m"] for b in car["branches"] if b["id"] == "B-sud"), None))
        if "ilots" in a:
            typ = {}
            for i in m.get("ilots", []):
                t = "directionnel" if i["type"] == "directionnel" else "separateur"
                typ[t] = typ.get(t, 0) + 1
            for k, v in a["ilots"].items():
                cmp(out, nom, f"ilots.{k}", v, typ.get(k, 0))
        if "refuges_min_m" in a:
            refs = [c["valeur"] for c in ctrl(r, "refuge_largeur")]
            cmp(out, nom, "refuges_min_m (≥)", True, bool(refs) and min(refs) >= a["refuges_min_m"] - 1e-6)
            out[-1]["valeur_mesuree"] = min(refs) if refs else None
        if "traversee_hors_refuge_max_m" in a or (a.get("controles") or {}).get("traversee_hors_refuge_max_m"):
            v = max((c["valeur"] for c in ctrl(r, "traversee_hors_refuge")), default=None)
            cmp(out, nom, "traversee_hors_refuge_max (≤ 12)", True, v is not None and v <= 12.0)
            out[-1]["valeur_mesuree"] = v
        if "ilot_directionnel_surface_min_m2" in a:
            v = min((c["valeur"] for c in ctrl(r, "ilot_directionnel_surface")), default=None)
            cmp(out, nom, "ilot_directionnel_surface (≥ 5)", True, v is not None and v >= 5.0)
            out[-1]["valeur_mesuree"] = v
        if a.get("feux"):
            f = a["feux"]
            fe = c0.get("feux") or {}
            if "phases" in f:
                cmp(out, nom, "feux.phases", f["phases"], len(fe.get("phases", [])))
            if "R11" in f:
                cmp(out, nom, "feux.R11", f["R11"], sig.get("R11v", 0))
            if "R12" in f:
                cmp(out, nom, "feux.R12", f["R12"], sig.get("R12", 0))
            if "jaune_s" in f:
                cmp(out, nom, "feux.jaune_s", f["jaune_s"], (fe.get("phases") or [{}])[0].get("jaune_s"))
            if "R11_par_approche_artere" in f:
                n = sum(1 for s in m["signaux"] if s["code"] == "R11v" and (s.get("applicabilite") or {}).get("branche") == "B-ouest")
                cmp(out, nom, "feux.R11_approche_ouest", f["R11_par_approche_artere"], n)
            if "tag_phase_speciale" in f:
                ph = fe.get("phases", [])
                spec = [p for p in ph if p["mouvements"] and all(".TAG" in t for t in p["mouvements"])]
                cmp(out, nom, "feux.phase_speciale_TAG", True, len(spec) == 1)
        if "cycle_s" in a:
            cmp(out, nom, "cycle_s", a["cycle_s"], (c0.get("feux") or {}).get("cycle_s"), 0.01)
        if a.get("guidage"):
            g = a["guidage"]
            gd = c0.get("guidage") or {}
            cmp(out, nom, "guidage.lignes", g["lignes"], len(gd.get("lignes", [])))
            n = sum(1 for t in car.get("trajectoires", []) if (t.get("guidage") or {}).get("materialise"))
            cmp(out, nom, "guidage.trajectoires_guidees", g["trajectoires_guidees"], n)
            v = [c["valeur"] for c in ctrl(r, "TAG_opposes_sans_croisement")]
            cmp(out, nom, "guidage.croisement_TAG_opposes", g["croisement_TAG_opposes"], max(v) if v else None)
        if a.get("controles"):
            for k in ("TAG_indonesienne_phase_speciale", "mouvements_servis"):
                if k in a["controles"]:
                    v = [c["valeur"] if isinstance(c["valeur"], (int, float)) else 0 for c in ctrl(r, k)]
                    cmp(out, nom, f"controle.{k}", a["controles"][k], max(v) if v else None)
        if "voies_directes_alignees" in a:
            # TD de l'artère : décalage latéral entre l'entrée et la sortie (trajectoire droite parallèle à l'axe)
            ec = []
            for t in car.get("trajectoires", []):
                if t["mouvement"] == "TD" and t["de"]["branche"] in ("B-ouest", "B-est"):
                    (x0, y0), (x1, y1) = t["geometrie"][0], t["geometrie"][-1]
                    ec.append(abs(y1 - y0))
            cmp(out, nom, "voies_directes_alignees.ecart_lateral_max_m", a["voies_directes_alignees"]["ecart_lateral_max_m"],
                round(max(ec), 3) if ec else None, a["voies_directes_alignees"]["ecart_lateral_max_m"])
        if "zone_conflit_longueur_max_m" in a:
            v = max((c["valeur"] for c in ctrl(r, "zone_conflit_longueur")), default=None)
            cmp(out, nom, "zone_conflit_longueur (≤ 40, avertissement)", True, v is not None and v <= 40.0)
            out[-1]["valeur_mesuree"] = v
    elif nom.startswith("G"):
        g = c0
        for k, cle in (("Rg_m", "Rg_m"), ("anneau_m", "anneau_m"), ("couronne_m", "couronne_m"),
                       ("Ri_infranchissable_m", "Ri_infranchissable_m"), ("Ri_m", "Ri_m")):
            if k in a:
                cmp(out, nom, k, a[k], g.get(cle), 0.01)
        if "Rext_m" in a:
            cmp(out, nom, "Rext_m", a["Rext_m"], g.get("Rg_m"), 0.01)
        if "Ri_franchissable_m" in a:
            cmp(out, nom, "Ri_franchissable_m", a["Ri_franchissable_m"], g.get("Ri_m"), 0.01)
        if "entree_m" in a:
            v = sorted({b["largeur_entree_m"] for b in g["branches"].values()})
            cmp(out, nom, "entree_m", [a["entree_m"]], v)
        if "sortie_m" in a:
            v = sorted({b["largeur_sortie_m"] for b in g["branches"].values()})
            cmp(out, nom, "sortie_m", [a["sortie_m"]], v)
        if "passage_retrait_m" in a:
            v = sorted({b["passage"]["retrait_m"] for b in g["branches"].values() if b.get("passage")})
            cmp(out, nom, "passage_retrait_m", [a["passage_retrait_m"]], v)
        if "deflexion_max_m" in a:
            v = max(x for x in g["deflexion_m"].values() if x is not None) if g.get("deflexion_m") else None
            cmp(out, nom, "deflexion (≤ 100)", True, v is not None and v <= a["deflexion_max_m"])
            out[-1]["valeur_mesuree"] = v
        if "refuges_min_m" in a:
            refs = [c["valeur"] for c in ctrl(r, "refuge_largeur")]
            cmp(out, nom, "refuges_min_m (≥)", True, bool(refs) and min(refs) >= a["refuges_min_m"] - 1e-6)
            out[-1]["valeur_mesuree"] = min(refs) if refs else None
        for k, v in (a.get("panneaux") or {}).items():
            cmp(out, nom, f"panneaux.{k}", v, sig.get(k, 0))
        for k, v in (a.get("conflits") or {}).items():
            cmp(out, nom, f"conflits.{k}", v, (g.get("conflits") or {}).get(k))
        car = next(c for c in m["carrefours"] if c["id"] == g["id"])
        if "lignes_cedez" in a:
            n = sum(1 for b in car["branches"] if (b.get("ligne_arret") or {}).get("type") == "CEDEZ")
            cmp(out, nom, "lignes_cedez", a["lignes_cedez"], n)
        if "raccordements_m" in a:
            rr = car["anneau"]["construction"]["raccordements"]
            cmp(out, nom, "raccordements.entree", [a["raccordements_m"]["entree"]], sorted({v["entree_m"] for v in rr.values()}))
            cmp(out, nom, "raccordements.sortie", [a["raccordements_m"]["sortie"]], sorted({v["sortie_m"] for v in rr.values()}))
        if "ilots_separateurs" in a:
            # longueur (H) et largeur (B) des îlots en saillie : H − 1 (retrait) − saillie, B − 2 × saillie au plus
            hs = [c for c in ctrl(r, "ilot_dans_enveloppe")]
            cmp(out, nom, "ilots_dans_enveloppe (≤ 0,05 m²)", True, bool(hs) and max(c["valeur"] for c in hs) <= 0.05)
            out[-1]["valeur_mesuree"] = max(c["valeur"] for c in hs) if hs else None
        if "dome_m" in a:
            ic = next(i for i in m["ilots"] if i["type"] == "central_giratoire")
            cmp(out, nom, "dome_m", a["dome_m"], ic["terre_plein"].get("surelevation_m"), 0.005)
        if "ilot_separateur_largeur_m" in a:
            ok = [c["valeur"] for c in ctrl(r, "ilot_mini_largeur")]
            cmp(out, nom, "ilot_separateur_largeur_m", a["ilot_separateur_largeur_m"], ok[0] if ok else None, 0.01)
        if "angles_branches_deg" in a:
            v = sorted({round(c["valeur"]) for c in ctrl(r, "angle_branches")})
            cmp(out, nom, "angles_branches_deg", [a["angles_branches_deg"]], v)
    elif nom.startswith("A"):
        p = profil_extremite(m, "R-1")
        T = D.t_limites(p, 0.0)
        if "largeur_plateforme_m" in a:
            cmp(out, nom, "largeur_plateforme_m", a["largeur_plateforme_m"], round(T[0] - T[-1], 3), 0.01)
        if "largeur_tpc_m" in a:
            w = sum(PF.nombre(b["largeur"]) for b in p["bandes"]
                    if b["type"] == "terre_plein" or (b["type"] == "bande_derasee" and b.get("sous_type") == "bande_derasee_gauche"))
            cmp(out, nom, "largeur_tpc_m", a["largeur_tpc_m"], round(w, 3), 0.01)
        if "voies" in a:
            n = {"avant": 0, "arriere": 0}
            for b in p["bandes"]:
                if b["type"] == "voie_circulation":
                    n[b["sens"]] += 1
            cmp(out, nom, "voies", a["voies"], n)
        if "u_m" in a:
            cmp(out, nom, "u_m", a["u_m"], p["u_m"], 1e-6)
        if "lignes" in a:
            mods = []
            for l in p["limites"]:
                for mq in l.get("marquages", []):
                    mods.append(f"{mq['modulation']} {int(mq['largeur_u'])}u")
            cmp(out, nom, "lignes.delimitation", a["lignes"]["delimitation"] in mods, True)
            cmp(out, nom, "lignes.rive_BAU", a["lignes"]["rive_BAU"] in mods, True)
            cmp(out, nom, "lignes.rive_TPC", a["lignes"]["rive_TPC"] in mods, True)
        if "separateur" in a:
            sp = [l["separateur"] for l in p["limites"] if l.get("separateur")]
            cmp(out, nom, "separateur", a["separateur"], {k: sp[0][k] for k in ("type", "largeur_m")} if sp else None)
        if "separateurs" in a:
            sp = [l["separateur"]["type"] for l in p["limites"] if l.get("separateur")]
            cmp(out, nom, "separateurs.glissiere", a["separateurs"]["glissiere"], sp.count("glissiere"))
        if "bordures" in a:
            cmp(out, nom, "bordures", a["bordures"], sum(1 for l in p["limites"] if "bordure" in l["nature"]))
        if obs:
            o = obs[0]
            if "obliquite" in a:
                cmp(out, nom, "obliquite", a["obliquite"], o.get("obliquite"), 0.001)
            if "point_1m_m" in a:
                cmp(out, nom, "point_1m_m", a["point_1m_m"], o.get("point_1m_depuis_jonction_m"), 0.5)
            if "point_5m_m" in a:
                cmp(out, nom, "point_5m_m", a["point_5m_m"], o.get("point_5m_depuis_jonction_m"), 0.5)
            if a.get("voie_insertion"):
                v = a["voie_insertion"]
                cmp(out, nom, "voie_insertion.debut_s", v["debut_s"], o["voie_auxiliaire_s"][0], 0.5)
                cmp(out, nom, "voie_insertion.fin_s", v["fin_s"], o["voie_auxiliaire_s"][1], 0.5)
            if a.get("voie_deceleration"):
                v = a["voie_deceleration"]
                cmp(out, nom, "voie_deceleration.debut_s", v["debut_s"], o["voie_auxiliaire_s"][0], 0.5)
                cmp(out, nom, "voie_deceleration.divergence_s", v["divergence_s"], o["voie_auxiliaire_s"][1], 0.5)
            lig = a.get("ligne_insertion") or a.get("ligne_deceleration")
            if lig:
                aux = o["voie_auxiliaire"]
                trouve = False
                for pp in m["profils"]:
                    ids = [b["id"] for b in pp["bandes"]]
                    if aux in ids:
                        k = ids.index(aux)
                        mq = (pp["limites"][k].get("marquages") or [{}])[0]
                        trouve = trouve or f"{mq.get('modulation')} {int(mq.get('largeur_u', 0))}u" == lig
                cmp(out, nom, "ligne_voie_auxiliaire", True, trouve)
            if a.get("musoir"):
                mus = a["musoir"]
                cmp(out, nom, "musoir.chevrons", True, any(x["type"] == "chevrons" for x in m.get("marquages", [])))
                cmp(out, nom, "musoir.balise", mus["balise"], next((s["code"] for s in m["signaux"] if s["code"] == "J14a"), None))
                ip = next((i for i in m["ilots"] if i["type"] == "ilot_peint"), {})
                mc = (ip.get("terre_plein") or {}).get("marquage_contour") or {}
                cmp(out, nom, "musoir.contour", mus["contour"], f"{mc.get('modulation')} {mc.get('largeur_u')}u")
            if a.get("bau_interrompue_s"):
                r1 = next(x for x in m["routes"] if x["id"] == "R-1")
                prof = {pp["id"]: pp for pp in m["profils"]}
                sans = [(s["s0"], s["s1"]) for s in r1["sections"]
                        if sum(1 for b in prof[s["profil"]]["bandes"] if b["type"] == "bande_arret_urgence") < 2]
                v = [round(sans[0][0], 1), round(sans[-1][1], 1)] if sans else None
                cmp(out, nom, "bau_interrompue_s", [float(x) for x in a["bau_interrompue_s"]], v)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(GEN / "tmp" / "scenes" / "rapport_scenes.json"))
    ap.add_argument("--determinisme", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    res = {"scenes": [], "attendus": [], "coherence": [], "retrocompatibilite": None, "determinisme": None}
    for f in SCENES:
        nom = f.stem.split("_")[0]
        try:
            m, r, d = compiler(f)
        except Exception as e:  # noqa: BLE001
            res["scenes"].append({"scene": f.stem, "fichier": str(f.relative_to(DEPOT)), "exception": f"{type(e).__name__}: {e}"})
            continue
        ctl = (r.get("reseau") or {}).get("controles", [])
        ligne = {"scene": f.stem, "fichier": str(f.relative_to(DEPOT)).replace("\\", "/"),
                 "erreurs_validation": r["validation"]["nb_erreurs"], "non_conformites": len(r["non_conformites"]),
                 "controles_reseau": len(ctl), "controles_non_conformes": [c for c in ctl if c["statut"] not in ("conforme", "avertissement")],
                 "avertissements_controles": [c["controle"] for c in ctl if c["statut"] == "avertissement"],
                 "routes": len(m["routes"]), "profils": len(m["profils"]), "carrefours": len(m.get("carrefours", [])),
                 "ilots": len(m.get("ilots", [])), "signaux": len(m.get("signaux", [])), "marquages": len(m.get("marquages", [])),
                 "controleurs": len(m.get("controleurs", [])), "sha256_modele": hashlib.sha256(octets(m)).hexdigest(),
                 "avertissements": sum(len(t["avertissements"]) for t in r["troncons"]) + len(r["avertissements"]),
                 "prov_manquantes": r["validation"].get("prov_manquantes")}
        res["scenes"].append(ligne)
        res["attendus"] += attendus_scene(nom, m, r, d)
        # cohérence : îlots hors des voies ; extrémités des branches
        for iid, sur in ilots_hors_voies(m):
            res["coherence"].append({"scene": f.stem, "controle": "ilot_hors_voies", "ilot": iid, "valeur_m2": sur,
                                     "seuil_m2": 0.05, "atteint": sur <= 0.05})
        for c in ctl:
            if c["controle"] in ("ilot_dans_enveloppe", "bretelle_dans_voie_auxiliaire", "branche_vers_centre"):
                res["coherence"].append({"scene": f.stem, "controle": c["controle"], "valeur": c["valeur"],
                                         "plage": c["plage"], "atteint": c["statut"] == "conforme"})
    # rétrocompatibilité
    ref = GEN / "tmp" / "scenes" / "empreintes_avant.json"
    if ref.exists():
        avant = json.loads(ref.read_text(encoding="utf-8"))
        fichiers = sorted((GEN / "scenes_simples").glob("S*.yaml")) + sorted((GEN / "description" / "exemples").glob("*.yaml")) \
            + sorted((GEN / "scenes_meylan").glob("*.yaml"))
        diff = []
        for f in fichiers:
            o = f.read_bytes()
            d = yaml_simple.charger(o.decode("utf-8"))
            src = str(f.relative_to(DEPOT)).replace("\\", "/")
            m, r = D.compiler(copy.deepcopy(d), src, hashlib.sha256(o).hexdigest())
            h = hashlib.sha256(json.dumps(m, ensure_ascii=False, indent=1).encode("utf-8")).hexdigest()
            hr = hashlib.sha256(json.dumps(r, ensure_ascii=False, indent=1, default=str).encode("utf-8")).hexdigest()
            if avant.get(f.name, {}).get("modele") != h or avant.get(f.name, {}).get("rapport") != hr:
                diff.append(f.name)
        res["retrocompatibilite"] = {"fichiers": len(fichiers), "identiques": len(fichiers) - len(diff), "differents": diff}
    if a.determinisme:
        det = []
        for f in SCENES:
            if f.stem.split("_")[0] not in ("J5", "G1"):
                continue
            m1, _, _ = compiler(f)
            m2, _, _ = compiler(f)
            det.append({"scene": f.stem, "identique": octets(m1) == octets(m2),
                        "sha256": hashlib.sha256(octets(m1)).hexdigest()})
        res["determinisme"] = det
    att = res["attendus"]
    res["bilan"] = {
        "scenes": len(SCENES), "compilees_sans_erreur": sum(1 for s in res["scenes"] if s.get("erreurs_validation") == 0),
        "non_conformites": sum(s.get("non_conformites", 0) for s in res["scenes"]),
        "attendus": len(att), "attendus_atteints": sum(1 for x in att if x["atteint"]),
        "coherence": len(res["coherence"]), "coherence_ok": sum(1 for x in res["coherence"] if x["atteint"])}
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res["bilan"], ensure_ascii=False))
    for x in att:
        if not x["atteint"]:
            print("ATTENDU NON ATTEINT", x["scene"], x["attendu"], x["valeur_attendue"], x["valeur_mesuree"])
    for x in res["coherence"]:
        if not x["atteint"]:
            print("COHERENCE", x)
    print("rétrocompatibilité :", res["retrocompatibilite"])
    print("déterminisme :", res["determinisme"])
    for s in res["scenes"]:
        if s.get("exception") or s.get("erreurs_validation") or s.get("non_conformites") or s.get("controles_non_conformes"):
            print("SCENE", s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
