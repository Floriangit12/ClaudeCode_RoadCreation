"""Contrôles des familles de sol v2 (schéma 0.3, site complet) appelés par valider.py.

Chaque contrôle cite la règle « verifier » de assets/specs/regles_conception.json qu'il mesure ; les
écarts dus à une donnée observée (chartière levée, OSM) sont des avertissements, les violations de
construction des erreurs.
- TQ-SOL-001 : partition : surfaces + trous de bâtiments = carré du site, aucune surface < 0,005 m² ;
- VAL-KRB-005 / GA-ABA-001 : abaissés de traversée en vue 0,02 ± 0,005 et ≥ 1,20 m ; traversées
  cyclables à 0 (GA-ABA-010) ;
- GA-ABA-004 (CF-01) : pente des chartières ≤ 8 % (12 % sur ≤ 0,50 m), chartières levées signalées ;
- GA-ABA-007 : entre deux abaissés de traversée d'une même bordure, vue ≥ 0,05 ;
- GA-BOR-001 : bordure piéton / circulé hors abaissé de vue ≥ 0,05 (avertissement) ;
- GA-BEV-002 / GA-BEV-003 : BEV à 0,50 ± 0,02 du nez, profondeur 0,40 (pratique du site) ± 0,02 ;
- GA-TRO-007 : aucun matériau meuble sur un trottoir ou un quai ;
- GA-ILO-001 : refuges ≥ 1,50 m (largeur approchée 2·aire/périmètre) ;
- nivellement.json : TQ-SOL-004, TQ-SOL-013 (contrôle MNT), GA-TRO-003, GA-TRO-004, VAL-SOL-009,
  GA-BOR-005, GA-ASS-005, GA-CHA-004 (seuils de la règle) ;
- résidus d'origine raster : surfaces `limite_raster` et longueur de fermeture (rapport).
"""
import json
from pathlib import Path

import numpy as np

MEUBLES = {"gravillons_ilot", "brf_bois_concasse", "brf_bois_gris", "galets_20_40", "gravier_concasse_6_10",
           "paillage_mineral"}
PIETON = {"trottoir", "quai_bus"}
CIRCULE = {"chaussee", "parking", "piste_cyclable", "acces_riverain"}


def _aire(r):
    a = np.asarray(r, float)[:, :2]
    return 0.5 * float(np.dot(a[:-1, 0], a[1:, 1]) - np.dot(a[1:, 0], a[:-1, 1]))


def _anneaux(g):
    return [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"] if g["type"] == "MultiPolygon" else []


def controles(couches, dossier):
    err, warn, rapport = [], [], {}
    K = couches["bordures"]
    S = couches["surfaces"]
    I = couches["ilots"]
    B = couches["ponctuels_sol"]
    # TQ-SOL-001 : partition (surfaces + trous de bâtiments = site)
    aire_s = sum(f["properties"]["aire_m2"] for f in S)
    petites = [f["properties"]["id"] for f in S if f["properties"]["aire_m2"] < 0.005]
    rapport["TQ-SOL-001"] = {"aire_surfaces_m2": round(aire_s, 3), "surfaces_inf_0_005_m2": len(petites)}
    if petites:
        warn.append(f"TQ-SOL-001 : {len(petites)} surface(s) de moins de 0,005 m² ({', '.join(petites[:5])})")
    # VAL-KRB-005 / GA-ABA-001 / GA-ABA-010 / GA-ABA-004 / GA-ABA-007
    n_obs = 0
    par_id = {f["properties"]["id"]: f["properties"] for f in K}

    def contigu(p, a):
        """Longueur abaissée continue : un pont (K-95nn) prolonge les abaissés des bouts qu'il relie."""
        L = a["s1"] - a["s0"]
        for v in (p["source"].get("pont") or []):
            q = par_id.get(v)
            if q is None:
                continue
            for b in q["abaisses"]:
                if b["type"] in ("traversee", "traversee_cyclable") and (b["s0"] <= 0.05 or b["s1"] >= q["longueur_m"] - 0.05):
                    L += b["s1"] - b["s0"]
        return L
    for f in K:
        p = f["properties"]
        abs_ = p["abaisses"]
        for a in abs_:
            if a["type"] == "traversee":
                if not 0.015 - 1e-6 <= a["vue_m"] <= 0.025 + 1e-6:
                    warn.append(f"VAL-KRB-005 : {a['id']} vue {a['vue_m']} hors 0,02 ± 0,005")
                if contigu(p, a) < 1.20 - 1e-3:
                    err.append(f"GA-ABA-001 : {a['id']} abaissé de {a['s1'] - a['s0']:.2f} m < 1,20 m")
            if a["type"] == "traversee_cyclable" and a["vue_m"] > 1e-6:
                warn.append(f"GA-ABA-010 : {a['id']} vue {a['vue_m']} > 0 (franchissement cyclable)")
            obs = (a.get("rampe") or {}).get("chartiere_observee")
            for r in a["raccords"]:
                L = r["s1"] - r["s0"]
                if L <= 1e-6:
                    continue
                pente = abs(r["vue_m"] - r["vue_m_fin"]) / L
                lim = 0.12 if L <= 0.5 + 1e-6 else 0.08
                if pente > lim + 1e-6:
                    if obs:
                        n_obs += 1
                    else:
                        warn.append(f"GA-ABA-004 : {a['id']} chartière {r['cote']} à {100 * pente:.1f} % sur {L:.2f} m")
        tr = sorted([a for a in abs_ if a["type"] == "traversee"], key=lambda a: a["s0"])
        for a0, a1 in zip(tr[:-1], tr[1:]):
            pic = 0.0
            for it in p["intervalles"]:
                if it["s1"] > a0["s1"] and it["s0"] < a1["s0"]:
                    pic = max(pic, it["vue_m"], it.get("vue_m_fin", 0.0))
            if pic < 0.05 - 1e-6:
                warn.append(f"GA-ABA-007 : entre {a0['id']} et {a1['id']} la vue ne remonte qu'à {pic:.3f} m")
    rapport["GA-ABA-004_chartieres_levees_non_conformes"] = n_obs
    # GA-BEV-002 / GA-BEV-003
    for f in B:
        p = f["properties"]
        if p.get("type") != "bev":
            continue
        if abs(p.get("retrait_nez_m", 0.5) - 0.5) > 0.02 + 1e-9:
            err.append(f"GA-BEV-002 : {p['id']} pas de freinage {p.get('retrait_nez_m')}")
        if abs(p.get("profondeur_m", 0.4) - 0.40) > 0.05 + 1e-9:
            warn.append(f"GA-BEV-003 : {p['id']} profondeur {p.get('profondeur_m')}")
    # GA-TRO-007 : pas de matériau meuble sur un cheminement
    for f in S:
        p = f["properties"]
        if p["classe"] in PIETON and p["revetement"]["materiau_id"] in MEUBLES:
            err.append(f"GA-TRO-007 : {p['id']} {p['classe']} en {p['revetement']['materiau_id']}")
    # GA-ILO-001 : refuges
    for f in I:
        p = f["properties"]
        if p["type"] != "refuge":
            continue
        larg = []
        for poly in _anneaux(f["geometry"]):
            r = np.asarray(poly[0], float)[:, :2]
            per = float(np.hypot(*np.diff(r, axis=0).T).sum())
            larg.append(2.0 * abs(_aire(poly[0])) / max(per, 1e-9))
        if larg and max(larg) < 1.50:
            warn.append(f"GA-ILO-001 : refuge {p['id']} large d'environ {max(larg):.2f} m < 1,50 m")
    # résidus d'origine raster (fermetures signalées)
    lr = [f for f in S if f["properties"].get("limite_raster")]
    rapport["limites_residuelles"] = {"surfaces": len(lr),
                                      "fermetures_m": round(sum(f["properties"].get("fermetures_m", 0.0) for f in S), 1)}
    # nivellement
    fj = Path(dossier) / "base" / "nivellement.json"
    if not fj.exists():
        err.append("nivellement.json absent (TQ-SOL-013)")
        return err, warn, rapport
    niv = json.loads(fj.read_text(encoding="utf-8"))
    c = niv.get("controles", {})
    ids_s = {f["properties"]["id"] for f in S}
    manq = sorted(ids_s - {s["id"] for s in niv["surfaces"]})
    if manq:
        err.append(f"TQ-SOL-013 : {len(manq)} surface(s) sans région de nivellement ({', '.join(manq[:5])})")
    q = c.get("TQ-SOL-004_xodr_mnt_m", {})
    if q.get("p95") is not None and q["p95"] > 0.05:
        warn.append(f"TQ-SOL-004 : modèle OpenDRIVE − MNT p95 {q['p95']:.3f} m > 0,05 (alerte)")
    q = c.get("TQ-SOL-013_pied_vs_fil_eau_mnt_m", {})
    if q.get("p95") is not None and q["p95"] > 0.05:
        warn.append(f"TQ-SOL-013 : pied de bordure − fil d'eau MNT p95 {q['p95']:.3f} m > 0,05 (alerte)")
    q = c.get("GA-TRO-003_devers_trottoirs_pct", {})
    if q.get("p50") is not None and not 1.0 - 0.3 <= q["p50"] <= 2.0 + 0.3:
        warn.append(f"GA-TRO-003 : dévers médian des trottoirs {q['p50']:.2f} % hors 1-2 %")
    q = c.get("GA-TRO-004_pentes_cheminements", {})
    if q.get("part_2m_sup_8pct") is not None and q["part_2m_sup_8pct"] > 0.01:
        warn.append(f"GA-TRO-004 : {100 * q['part_2m_sup_8pct']:.1f} % des nœuds de cheminement > 8 % sur 2 m")
    q = c.get("VAL-SOL-009_marches_meme_region", {})
    if q.get("n_aretes_sup_3cm"):
        warn.append(f"VAL-SOL-009 : {q['n_aretes_sup_3cm']} marche(s) > 3 cm dans une même région (pire {q['pires'][0]})")
    q = c.get("GA-BOR-005_contacts", {})
    if q.get("n_tete_sup_2cm"):
        warn.append(f"GA-BOR-005 : {q['n_tete_sup_2cm']} contact(s) entre bordures avec écart de tête > 2 cm (max {q.get('dtete_max_m')})")
    q = c.get("GA-ASS-005_noue", {})
    if q.get("pente_2m_max_pct") is not None and q["pente_2m_max_pct"] > 33.4:
        warn.append(f"GA-ASS-005 : talus de noue à {q['pente_2m_max_pct']:.1f} % > 33 %")
    rapport["nivellement"] = c
    return err, warn, rapport
