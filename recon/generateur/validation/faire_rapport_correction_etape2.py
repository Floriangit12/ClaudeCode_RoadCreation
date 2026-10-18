# -*- coding: utf-8 -*-
"""Rapport du lot « correction de l'étape 2 » (18/10/2026) : rejoue les contrôles sur les sorties corrigées et écrit
validation/rapport_correction_etape2.json (le texte : RAPPORT_correction_etape2.md, écrit à la main d'après ce JSON).

    python recon/generateur/validation/faire_rapport_correction_etape2.py [--sans-controles-lots]

Contrôles rejoués : controler_L3.py (J1-J6), controler_L4.py (J1-J6), controler_giratoires.py (G1-G4),
controler_autoroutes.py (A1-A4), controler_correction_etape2.py (27 scènes : CE-1 à CE-5) ; TAG guidés (garde, balayages)
recalculés ici pour chaque ligne de guidage (J5, J6) ; trajectoires balayées = trajectoires finales (manifestes) ;
permutation et déterminisme (comparer_permutation.py) ; rendus (géométrie rendue = .usda finaux, planches ≤ 1092 px).
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
OUT = DEPOT / "recon" / "out" / "generateur"
TMP = GEN / "tmp" / "correction2"
sys.path.insert(0, str(GEN))
sys.path.insert(0, str(ICI))

J = ["J1_T_cedez", "J2_croix_stop", "J3_croix_feux", "J4_ilots_directionnel_separateurs", "J5_carrefour_complexe",
     "J6_carrefour_complexe_2x2"]
G = ["G1_giratoire_urbain_D40", "G2_giratoire_periurbain_D50", "G3_mini_giratoire_D20", "G4_giratoire_multivoie_D50"]
A = ["A1_autoroute_2x2_GBA", "A2_autoroute_2x3_glissieres", "A3_bretelle_entree", "A4_bretelle_sortie"]
S = [f"S{k:02d}" for k in range(1, 13)] + ["B01"]
TOUTES = S + J + G + A


def lire(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def r_(x, n=3):
    return None if x is None else round(float(x), n)


def critere(i, nom, valeur, seuil, atteint, **k):
    return dict({"id": i, "critere": nom, "valeur": valeur, "seuil": seuil, "atteint": bool(atteint)}, **k)


def py(script, *args):
    r = subprocess.run([sys.executable, "-X", "utf8", str(ICI / script), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(DEPOT))
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-3000:])
    return r.returncode


def tag_guides(scene):
    """Pour chaque ligne de guidage : garde caisse / ligne (distance des axes à la ligne − demi-caisse − demi-ligne),
    balayages du VL (lot L3a, rétroviseurs) des deux TAG : recouvrement, distance, contact avec les faces de bordure."""
    import numpy as np
    from shapely.geometry import LineString, Polygon
    from shapely.ops import unary_union
    from vehicules import balayage as B
    import controler_L4 as C4
    d = OUT / scene
    gu = lire(d / "l4" / "guidage.json")["lignes"]
    T = {t["id"]: t for t in lire(d / "l4" / "trajectoires.json")["trajectoires"]}
    l3 = lire(d / "l3" / "carrefours.json")
    bord = unary_union([LineString(C4.nettoyer(f["points"])) for f in l3["faces"] if len(f["points"]) >= 2])
    out = []
    for g in gu:
        Cg = LineString(C4.nettoyer(g["points"]))
        ids = g["mouvements"].split()
        env, gard = [], []
        for tid in ids:
            P = C4.nettoyer(T[tid]["points"])
            gard.append(LineString(P).distance(Cg) - 0.9 - 0.5 * float(g["largeur_m"]))
            u = np.subtract(P[1], P[0]); u = u / np.linalg.norm(u)
            v = np.subtract(P[-1], P[-2]); v = v / np.linalg.norm(v)
            axe = [tuple(np.array(P[0]) - 15.0 * u)] + P + [tuple(np.array(P[-1]) + 15.0 * v)]
            env.append(Polygon(B.balayage_detail("vl", axe)["polygone"].exterieur).buffer(0))
        out.append({"ligne": g["id"], "mouvements": ids, "rayons_m": [r_(T[t]["rayon"], 2) for t in ids],
                    "garde_caisse_peinture_min_m": r_(min(gard), 3),
                    "recouvrement_balayages_m2": r_(env[0].intersection(env[1]).area, 4),
                    "distance_balayages_m": r_(env[0].distance(env[1]), 3),
                    "contre_bordures_m": [r_(e.intersection(bord).length, 3) for e in env],
                    "croisement_axes": not LineString(C4.nettoyer(T[ids[0]]["points"])).intersection(
                        LineString(C4.nettoyer(T[ids[1]]["points"]))).is_empty})
    return out


def rendus(scene):
    d = OUT / scene / "rendus"
    man = d / "manifest_rendus.json"
    if not man.exists():
        return {"scene": scene, "manifeste": False}
    m = lire(man)
    geo = {k: (OUT / scene / k).exists() and hashlib.sha256((OUT / scene / k).read_bytes()).hexdigest() == h
           for k, h in (m.get("geometrie_rendue_sha256") or {}).items()}
    from PIL import Image
    pl = sorted(d.glob("planche_*.png"))
    taille = Image.open(pl[0]).size if pl else None
    vues = [p.stem for p in d.glob("*.png") if not p.stem.startswith("planche")]
    return {"scene": scene, "geometrie_rendue_identique": all(geo.values()) and bool(geo), "detail": geo,
            "planche": taille, "vues": sorted(vues)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-controles-lots", action="store_true")
    a = ap.parse_args()
    TMP.mkdir(parents=True, exist_ok=True)
    if not a.sans_controles_lots:
        py("controler_L3.py", "--json", str(TMP / "ctl_L3.json"))
        py("controler_L4.py", "--json", str(TMP / "ctl_L4.json"))
        py("controler_giratoires.py", "--json", str(TMP / "ctl_gir.json"))
        py("controler_autoroutes.py", "--json", str(TMP / "ctl_aut.json"))
        py("controler_correction_etape2.py", *TOUTES, "--json", str(TMP / "ctl_ce.json"))
    L3 = {r["scene"]: r for r in lire(TMP / "ctl_L3.json")["scenes"]}
    L4 = {r["scene"]: r for r in (lire(TMP / "ctl_L4.json") if isinstance(lire(TMP / "ctl_L4.json"), list)
                                  else lire(TMP / "ctl_L4.json")["scenes"])}
    GI = {r["scene"]: r for r in lire(TMP / "ctl_gir.json")["scenes"]}
    AU = lire(TMP / "ctl_aut.json")
    CE = {r["scene"]: r for r in lire(TMP / "ctl_ce.json")["scenes"]}
    cr = []
    # ------------------------------------------------------------------ J5, J6 : TAG guidés
    tg = {s: tag_guides(s) for s in ("J5_carrefour_complexe", "J6_carrefour_complexe_2x2") if (OUT / s / "l4").exists()}
    lig = [x for v in tg.values() for x in v]
    rec = max((x["recouvrement_balayages_m2"] for x in lig), default=None)
    gar = min((x["garde_caisse_peinture_min_m"] for x in lig), default=None)
    cb = max((max(x["contre_bordures_m"]) for x in lig), default=None)
    cr.append(critere("CE-J1", "TAG guidés (phase spéciale) : balayages du VL des deux courants disjoints (L4-13)",
                      f"recouvrement max {rec} m² ({len(lig)} lignes : J5 1, J6 2)", "0 m²", rec is not None and rec == 0,
                      detail=tg))
    cr.append(critere("CE-J2", "TAG guidés : garde caisse (1,80 m) / bord de la peinture de la ligne de guidage",
                      f"min {gar} m", "≥ 0,50 m", gar is not None and gar >= 0.5))
    cr.append(critere("CE-J3", "TAG guidés : balayages contre les faces de bordure (nez des TPC)", f"max {cb} m", "0 m",
                      cb is not None and cb == 0))
    cr.append(critere("CE-J4", "TAG guidés : axes sans croisement", f"{sum(1 for x in lig if x['croisement_axes'])} croisement(s)",
                      "0", not any(x["croisement_axes"] for x in lig)))
    # ------------------------------------------------------------------ L3-9 / L3-10 (balayages = trajectoires L4)
    for veh, lab in (("vl", "VL"), ("bus_standard_12m", "bus 12 m (mouvements desservis)")):
        ms = [(s, n["nez"], n["marge_par_vehicule_m"].get(veh)) for s, r in L3.items() for n in r["nez"]
              if "nez" in n and n["marge_par_vehicule_m"].get(veh) is not None]
        ok = sum(1 for m_ in ms if m_[2] >= 0.30)
        mn = min(ms, key=lambda x: x[2]) if ms else None
        nn = sum(1 for r in L3.values() for n in r["nez"] if "nez" in n)
        cr.append(critere(f"CE-L3-9-{veh}", f"nez des îlots au premier contact des balayages + 0,30 m ({lab}), J1-J6",
                          f"{ok}/{len(ms)} nez touchés dégagés ({nn} nez) ; marge min {r_(mn[2]) if mn else '—'} m "
                          f"({mn[0][:2] + ' ' + mn[1] if mn else ''})", "≥ 0,30 m pour chaque nez", ok == len(ms),
                          detail=[{"scene": s, "nez": n, "marge_m": m_} for s, n, m_ in ms]))
    il = [(s, n["ilot"], n["distance_min_balayage_m"], n["balayages_qui_coupent"]) for s, r in L3.items() for n in r["nez"]
          if "ilot" in n]
    dmin = min((x[2] for x in il), default=None)
    coupe = [x for x in il if x[3]]
    cr.append(critere("CE-L3-10", "îlots du cœur (directionnels) hors des balayages faisables, J1-J6",
                      f"distance min {r_(dmin)} m ({len(il)} îlots) ; balayages qui coupent un îlot : {sum(len(x[3]) for x in il)}",
                      "≥ 0,30 m, 0 coupe", dmin is not None and dmin >= 0.30 and not coupe, detail=il))
    tagb = {s: sorted({b["trajectoire"] + " " + b["vehicule"] for b in lire(OUT / s / "l3" / "balayages.json")["balayages"]
                       if b["mouvement"] == "TAG" and b["faisable"]}) for s in J if (OUT / s / "l3" / "balayages.json").exists()}
    cr.append(critere("CE-L3-src", "une seule source : balayages calculés sur les trajectoires finales du lot L4 (empreintes "
                                   "identiques), TAG compris", "; ".join(
        f"{s[:2]} {lire(OUT / s / 'l4' / 'manifest_l4.json')['comptes'].get('trajectoires_balayees_identiques')} "
        f"({len(tagb.get(s, []))} balayages de TAG)" for s in J), "identiques, ≥ 1 TAG balayé par carrefour à TAG",
        all(lire(OUT / s / "l4" / "manifest_l4.json")["comptes"].get("trajectoires_balayees_identiques") for s in J)
        and all(tagb.get(s) for s in J), detail=tagb))
    # ------------------------------------------------------------------ L4-16, croisements de TAG dans une même phase
    ec = {s: L4[s]["conflits"]["ecarts"] for s in J if s in L4}
    cr.append(critere("CE-L4-16", "conflits : géométrie (intersections des axes) = topologie (ordre des bouts) — rapporté",
                      "; ".join(f"{s[:2]} {len(v)}" for s, v in ec.items()), "0 écart",
                      all(not v for v in ec.values()), detail=ec))
    c5 = {s: CE[s]["CE-5"] for s in J if s in CE and "CE-5" in CE[s]}
    cr.append(critere("CE-5", "TAG qui se croisent dans une même phase (carrefours à feux)",
                      "; ".join(f"{s[:2]} {v['croisements_TAG_meme_phase']} ({len(v['phases'])} phases)" for s, v in c5.items()),
                      "0", all(v["croisements_TAG_meme_phase"] == 0 for v in c5.values()), detail=c5))
    # ------------------------------------------------------------------ CE-1 peintures
    c1 = {s: CE[s]["CE-1"] for s in CE}
    tot = sum(v["paires_au_dessus_du_seuil"] for v in c1.values())
    cr.append(critere("CE-1", "non-superposition des peintures (aire entre deux entités ≤ 1e-4 m²), toutes scènes",
                      f"{tot} paire(s) au-dessus du seuil ; " + "; ".join(
                          f"{s[:3]} {v['aire_totale_m2']} m²" for s, v in c1.items() if v["paires_au_dessus_du_seuil"]),
                      "0 paire", tot == 0, detail=c1))
    # ------------------------------------------------------------------ CE-2 / CE-3 passages
    pas = [(s, p) for s in CE for p in CE[s]["passages"]]
    meub = sum(p["points_meubles"] for _, p in pas)
    cr.append(critere("CE-2", "sol sous chaque passage et chaque refuge non meuble (ni gazon, ni terre)",
                      f"{meub} point(s) meuble(s) sur {len(pas)} passages", "0", meub == 0))
    ea = max((p["ecart_axe_max_m"] for _, p in pas if p["ecart_axe_max_m"] is not None), default=None)
    eg = max((p["ecart_max_m"] for _, p in pas if p["ecart_max_m"] is not None), default=None)
    cr.append(critere("CE-3a", "passages : dernière bande → bord de chaussée sur l'axe du passage (RF-MQ-PP-05)",
                      f"max {ea} m ({len(pas)} passages)", "≤ 0,80 m", ea is not None and ea <= 0.80 + 1e-6,
                      detail={f"{s}/{p['passage']}": p["ecart_axe_max_m"] for s, p in pas}))
    cr.append(critere("CE-3b", "passages : dernière bande → bord de chaussée sur toute la longueur des bandes (congés, bords "
                               "évasés) : pas de place pour une bande de plus", f"max {eg} m", "< 1,50 m (0,50 + 2 × 0,50)",
                      eg is not None and eg < 1.50, detail={f"{s}/{p['passage']}": p["ecart_max_m"] for s, p in pas}))
    # ------------------------------------------------------------------ CE-4 rives
    c4 = {s: CE[s]["CE-4"] for s in CE if "CE-4" in CE[s]}
    tr4 = sum(v["trous_au_dela_de_l_intervalle"] for v in c4.values())
    cr.append(critere("CE-4", "rives peintes continues (autoroutes, S01) : aucun tronçon sans peinture plus long que "
                              "l'intervalle de la modulation", f"{tr4} trou(s)", "0", tr4 == 0, detail=c4))
    # ------------------------------------------------------------------ giratoires
    for s in G:
        if s not in GI:
            continue
        for c in GI[s]["criteres"]:
            if c["id"] in ("GI-03", "GI-07", "GI-11", "GI-04", "GI-12"):
                cr.append(critere(f"{c['id']}-{s[:2]}", c["critere"], c["valeur"], c["seuil"], c["atteint"]))
    # rives de l'anneau G2 : modulation des lignes de l'anneau
    l5 = lire(OUT / "G2_giratoire_periurbain_D50" / "l5" / "giratoires.json")
    an = {k: v for k, v in (l5.get("marques") or {}).items() if ".anneau." in k}
    mods = sorted({v.get("modulation") for v in an.values()})
    cr.append(critere("CE-G2", "G2 : lignes de l'anneau (contour de l'îlot central, rive) en continue 3u (RF-MQ-GIR-01, -04)",
                      "; ".join(f"{k.split('.')[-2]} r = {v.get('rayon_m')} m : {v.get('modulation')} {v.get('largeur_m')} m"
                                for k, v in sorted(an.items())), "continue 0,15 m (3u)",
                      mods == ["continue"] and all(abs(float(v.get("largeur_m", 0)) - 0.15) < 1e-6 for v in an.values())))
    # ------------------------------------------------------------------ rendus
    rd = {s: rendus(s) for s in TOUTES}
    ok = [s for s, v in rd.items() if v.get("geometrie_rendue_identique") and v.get("planche") and v["planche"][0] <= 1092
          and v["planche"][1] <= 1092]
    cr.append(critere("CE-R", "rendus : géométrie rendue = .usda finaux, planche ≤ 1092 px (2 vues ; 3 pour J5, G1, A3)",
                      f"{len(ok)}/{len(rd)}", f"{len(rd)}/{len(rd)}", len(ok) == len(rd), detail=rd))
    # ------------------------------------------------------------------ permutation / déterminisme
    for nom in ("permutation_S02.json", "determinisme_J5.json"):
        f = TMP / nom
        if f.exists():
            v = lire(f)
            cr.append(critere(f"CE-D-{nom.split('_')[0]}", f"{'S02 seul / S02 après J5 (même processus)' if 'perm' in nom else 'J5 : deux processus'} : "
                              "sorties identiques à l'octet, manifestes compris", f"{v['fichiers']} fichiers, écarts {v['ecarts']}",
                              "identique", v["identique"]))
    out = {"schema": "rapport_correction_etape2/0.1", "lot": "correction de l'étape 2", "criteres": cr,
           "controles": {"autoroutes": AU}}
    (ICI / "rapport_correction_etape2.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n",
                                                         encoding="utf-8")
    for c in cr:
        print(f"{'OK ' if c['atteint'] else 'NON'} {c['id']} {c['critere'][:80]} : {str(c['valeur'])[:160]} (seuil {c['seuil']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
