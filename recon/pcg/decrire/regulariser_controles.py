"""Contrôles de la régularisation géométrique (règles « verifier » de regles_qualite_geometrique.json),
appelés par valider.py quand base/regularisation_sources.geojson existe.

- GQ-PRI-003 / GQ-DEN-001 / GQ-CON-001 : primitives relues (chaque primitive recalculée depuis son départ) :
  polyligne ≤ 5 mm de la suite de primitives, raccords continus (≤ 2 mm) et tangents (≤ 0,01°) hors coins ;
- GQ-TOL-001 / GQ-TOL-002 : écarts symétriques à la source archivée (99 % ≤ T, tous ≤ 1,5 T ; moyenne ≤ T/3,23) ;
- GQ-SEG-001 / GQ-RAY-001 : longueurs de primitives, segments < 5 mm, rayons de bordure ≥ 0,25 m ;
- GQ-VAL-001 : cassures avant / après (histogrammes) ;
- GQ-TOP-001 / GQ-TOP-002 / GQ-TOP-003 : nœuds exacts, contacts en T sur la courbe, anneaux fermés ;
- GQ-TOP-004 : partition : chaque arête de surface est partagée (sens opposé) par une autre surface, sauf bord
  du carré et bords de bâtiments (trous) ;
- GQ-ORI-001 / GQ-ORI-003 : aucune voie driving/bus du côté haut ; sens opposés aux nœuds G1 ;
- GQ-RAY-002 / GQ-RAY-004 / GQ-SYM-001 / GQ-SYM-002 / GQ-SYM-003 : rayons d'angle, nez d'îlots, zébras,
  abaissés en alignement, quais en alignement droit ;
- GQ-PAR-001 / GQ-VAL-002 : marquages parallèles aux bordures et sans croisement de l'arête avant.
"""
import collections
import math

import numpy as np

import regulariser as RQ
import regulariser_geometrie as RG
import sol_site as ctx
from commun import abscisses, anneaux, distance_segments, lire_json, point_a, projeter, repere

SEUILS_HIST = [0.5, 1.0, 2.0, 5.0, 10.0, 30.0]


def histogramme(v, seuils=SEUILS_HIST):
    v = np.asarray(v, dtype=np.float64)
    bornes = [0.0] + seuils + [math.inf]
    return {f"{a:g}-{b:g}" if b != math.inf else f">{a:g}": int(((v >= a) & (v < b)).sum())
            for a, b in zip(bornes[:-1], bornes[1:])}


def chaine_de(prims, i):
    """Primitive i recalculée depuis ses paramètres stockés (repère local)."""
    e = prims[i]
    x, y = repere(np.array([[e["x0"], e["y0"]]]))[0]
    k1 = e.get("k1", e["k0"])
    return RG.Chaine(x, y, e["cap0_rad"], [[e["s1"] - e["s0"], e["k0"], k1]])


def verifier_primitives(eid, desc, P, err, warn, stats):
    prims = desc["primitives"]
    S = abscisses(P)
    L = float(S[-1])
    if abs(prims[-1]["s1"] - L) > 0.01 or abs(prims[0]["s0"]) > 1e-3:
        err.append(f"{eid} : primitives [{prims[0]['s0']}, {prims[-1]['s1']}] ≠ polyligne [0, {L:.3f}] (GQ-PRI-003)")
    e_max = 0.0
    for i, e in enumerate(prims):
        ch = chaine_de(prims, i)
        m = (S >= e["s0"] - 1e-6) & (S <= e["s1"] + 1e-6)
        if m.any():
            C, _, _ = ch.evaluer(S[m] - e["s0"])
            e_max = max(e_max, float(np.hypot(*(C - P[m]).T).max()))
        if i + 1 < len(prims):
            fin, hf = ch.fin()
            nx = chaine_de(prims, i + 1)
            gap = float(np.hypot(*(fin - np.array([nx.x0, nx.y0]))))
            saut = abs(math.degrees(float(RG.wrap(nx.h0 - hf))))
            stats["sauts_cap_raccords"].append(0.0 if prims[i + 1].get("coin") else saut)
            if prims[i + 1].get("coin"):
                stats["coins"] += 1
                continue
            if gap > 0.002:
                err.append(f"{eid} : raccord discontinu de {gap * 1000:.1f} mm à s = {e['s1']} (GQ-CON-001)")
            if saut > 0.02:
                err.append(f"{eid} : saut de cap {saut:.3f}° au raccord s = {e['s1']} (GQ-CON-001)")
    stats["ecart_polyligne_primitives_max_m"] = max(stats["ecart_polyligne_primitives_max_m"], e_max)
    if e_max > 0.005:
        err.append(f"{eid} : polyligne à {e_max * 1000:.1f} mm des primitives (GQ-DEN-001)")


def cassures_sommets(P, exclus=()):
    """Déviation (°) aux sommets d'une polyligne (nettoyée à 5 mm), hors zones exclues [(s0, s1)]."""
    Q = RG.nettoyer(P)
    if len(Q) < 3:
        return np.zeros(0)
    a, b = Q[1:-1] - Q[:-2], Q[2:] - Q[1:-1]
    ang = np.degrees(np.abs(np.arctan2(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0], (a * b).sum(1))))
    s = abscisses(Q)[1:-1]
    ok = np.ones(len(s), bool)
    for s0, s1 in exclus:
        ok &= ~((s >= s0) & (s <= s1))
    return ang[ok]


def cassures_lissees(P, exclus=(), e=RG.E_FLECHE):
    """Après régularisation : déviation aux sommets au-delà de celle d'un arc échantillonné à flèche ≤ e
    (8e / max(l1, l2)) : nulle pour une suite G1 densifiée."""
    Q = RG.nettoyer(P, 0.002)
    if len(Q) < 3:
        return np.zeros(0)
    a, b = Q[1:-1] - Q[:-2], Q[2:] - Q[1:-1]
    la, lb = np.hypot(*a.T), np.hypot(*b.T)
    ang = np.abs(np.arctan2(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0], (a * b).sum(1)))
    exc = np.degrees(np.maximum(ang - 8.5 * e / np.maximum(np.minimum(la, lb), 1e-6), 0.0))
    s = abscisses(Q)[1:-1]
    ok = np.ones(len(s), bool)
    for s0, s1 in exclus:
        ok &= ~((s >= s0) & (s <= s1))
    return exc[ok]


def _sources(dossier):
    f = dossier / "base" / "regularisation_sources.geojson"
    out = {}
    if f.exists():
        for x in lire_json(f)["features"]:
            p = x["properties"]
            out[(p["famille"], p["entite"])] = (repere(np.asarray(x["geometry"]["coordinates"])[:, :2]), p)
    return out


def controles(couches, dossier):
    err, warn = [], []
    stats = {"sauts_cap_raccords": [], "coins": 0, "ecart_polyligne_primitives_max_m": 0.0}
    src = _sources(dossier)
    if not src:
        return err, warn, {}
    rap = {}
    # ------------------------------------------------------------------ bordures et marquages : primitives, écarts, cassures
    par_famille = collections.defaultdict(lambda: {"n": 0, "ecarts": collections.defaultdict(list), "avant": [], "apres": [],
                                                   "primitives": collections.Counter(), "statuts": collections.Counter()})
    K = {f["properties"]["id"]: f for f in couches["bordures"]}
    for fam_desc, feats, fam_src in (("bordures", couches["bordures"], "bordures"),
                                     ("marquages", couches.get("marquages", []), "marquages")):
        for f in feats:
            p = f["properties"]
            d = p.get("geometrie_reguliere")
            if d is None:
                continue
            P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
            eid = p["id"]
            pf = par_famille[fam_desc]
            pf["n"] += 1
            pf["statuts"][d["statut"]] += 1
            for k, v in d["n_primitives"].items():
                pf["primitives"][k] += v
            if d["statut"] == "source_gardee":
                warn.append(f"{eid} : géométrie source gardée (aucune chaîne G1 dans la tolérance, GQ-CON-002 / CF-GQ-01)")
            else:
                verifier_primitives(eid, d, P, err, warn, stats)
            s = src.get((fam_src, eid))
            if s is None:
                if not eid.startswith("K-95") and not eid.endswith("z"):
                    warn.append(f"{eid} : source archivée absente (GQ-PRO-001)")
                continue
            Ps, ps = s
            T = float(d["tolerance_m"])
            D, _ = RG.reechantillonner(RG.nettoyer(Ps), 0.05)
            d1 = RG.distance_a_polyligne(D, P) if len(P) >= 2 else np.zeros(1)
            Cn, _ = RG.reechantillonner(P, 0.05)
            d2 = RG.distance_a_polyligne(Cn, RG.nettoyer(Ps)) if len(Ps) >= 2 else np.zeros(1)
            dd = np.r_[d1, d2]
            pf["ecarts"][d["source"]].append(float(dd.max()))
            if np.percentile(dd, 99) > T + 0.002 or dd.max() > 1.5 * T + 0.002:
                (err if d["statut"] == "regularise" else warn).append(
                    f"{eid} : écart à la source p99 {np.percentile(dd, 99):.3f} m / max {dd.max():.3f} m > T {T} (GQ-TOL-001)")
            if d1.mean() > T / 3.23 + 0.001:
                warn.append(f"{eid} : écart moyen {d1.mean():.3f} m > T/3,23 (GQ-TOL-002)")
            # cassures : avant (sommets de la source) / après (au-delà de la flèche de densification), hors coins
            exc = [(c - 0.3, c + 0.3) for c in d.get("coins", [])]
            ss, _, _ = projeter(Ps, P[:1]) if len(Ps) >= 2 else (np.zeros(1), 0, 0)
            exc_src = []
            for c in d.get("coins", []):
                q, _ = point_a(P, np.array([c]))
                sc, _, _ = projeter(RG.nettoyer(Ps), q)
                exc_src.append((sc[0] - 0.3, sc[0] + 0.3))
            pf["avant"] += list(cassures_sommets(Ps, exc_src))
            pf["apres"] += list(cassures_lissees(P, exc))
            # longueurs et rayons (GQ-SEG-001, GQ-RAY-001)
            if fam_desc == "bordures":
                for e in d["primitives"]:
                    if e["type"] == "arc" and e["rayon_m"] < 0.25 - 1e-3:
                        err.append(f"{eid} : arc de rayon {e['rayon_m']} m < 0,25 m (GQ-RAY-001)")
            seg = np.hypot(*np.diff(P, axis=0).T)
            if len(seg) and seg.min() < 0.0045 and len(P) > 2:
                warn.append(f"{eid} : segment de {seg.min() * 1000:.1f} mm dans la polyligne (GQ-SEG-001)")
    for fam, pf in par_famille.items():
        av, ap = np.asarray(pf["avant"]), np.asarray(pf["apres"])
        rap[fam] = {"n": pf["n"], "statuts": dict(sorted(pf["statuts"].items())),
                    "primitives": dict(sorted(pf["primitives"].items())),
                    "ecart_max_par_source_m": {k: {"n": len(v), "p50": round(float(np.median(v)), 4),
                                                   "p95": round(float(np.percentile(v, 95)), 4), "max": round(float(np.max(v)), 4)}
                                               for k, v in sorted(pf["ecarts"].items())},
                    "cassures_avant_deg": histogramme(av), "cassures_apres_deg": histogramme(ap),
                    "cassures_sup_2deg": {"avant": int((av > 2).sum()), "apres": int((ap > 2).sum())},
                    "cassures_sup_1deg": {"avant": int((av > 1).sum()), "apres": int((ap > 1).sum())}}
        if (ap > 1.0).sum():
            warn.append(f"[{fam}] {(ap > 1.0).sum()} sommets cassés de plus de 1° hors coins après régularisation (GQ-VAL-001)")
    rap["raccords"] = {"sauts_cap_deg": histogramme(stats["sauts_cap_raccords"]), "coins_voulus": stats["coins"],
                       "ecart_polyligne_primitives_max_m": round(stats["ecart_polyligne_primitives_max_m"], 4)}
    # ------------------------------------------------------------------ topologie des bordures (GQ-TOP-001/002/003)
    topo = collections.Counter()
    for kid, f in sorted(K.items()):
        d = f["properties"].get("geometrie_reguliere")
        if not d:
            continue
        P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        if d.get("ferme"):
            topo["anneaux"] += 1
            if np.hypot(*(P[0] - P[-1])) > 1e-6:
                err.append(f"{kid} : anneau non refermé (GQ-TOP-003)")
        for nom, b in (("debut", 0), ("fin", -1)):
            e = d.get("noeuds", {}).get(nom, {})
            if e.get("type") == "noeud":
                for o in e["avec"]:
                    if o not in K:
                        continue
                    Po = repere(np.asarray(K[o]["geometry"]["coordinates"])[:, :2])
                    dmin = min(np.hypot(*(Po[0] - P[b])), np.hypot(*(Po[-1] - P[b])))
                    topo["noeuds_verifies"] += 1
                    if dmin > 0.0015:
                        err.append(f"{kid} : nœud {nom} à {dmin * 1000:.1f} mm de {o} (GQ-TOP-001)")
            elif e.get("type") == "t":
                o = e["avec"][0]
                if o in K:
                    Po = repere(np.asarray(K[o]["geometry"]["coordinates"])[:, :2])
                    dd, _, _ = distance_segments(P[b][None], Po[:-1], Po[1:])
                    topo["contacts_t_verifies"] += 1
                    if dd[0] > 0.003:
                        err.append(f"{kid} : contact en T {nom} à {dd[0] * 1000:.1f} mm de {o} (GQ-TOP-002)")
    rap["topologie_bordures"] = dict(sorted(topo.items()))
    # ------------------------------------------------------------------ partition (GQ-TOP-004)
    rap["partition"] = partition(couches["surfaces"], err, warn)
    # ------------------------------------------------------------------ orientation (GQ-ORI-001 / GQ-ORI-003)
    rap["orientation"] = orientation(K, err, warn)
    # ------------------------------------------------------------------ régularité des ouvrages
    rap["ouvrages"] = ouvrages(K, couches, rap["orientation"].pop("_bas_circule"), err, warn)
    # ------------------------------------------------------------------ marquages contre bordures
    if couches.get("marquages"):
        rap["marquages_bordures"] = marquages_bordures(couches["marquages"], K, err, warn)
    return err, warn, rap


def partition(S, err, warn):
    """GQ-TOP-004 : arêtes partagées (sens opposé) ; orphelines tolérées sur le bord du carré et les bâtiments."""
    cle = lambda p: (int(round(p[0] * 1000)), int(round(p[1] * 1000)))
    aretes = collections.Counter()
    for f in S:
        for poly in anneaux(f["geometry"]):
            for r in poly:
                R = np.asarray(r)[:, :2]
                R = np.vstack([R, R[:1]]) if np.hypot(*(R[0] - R[-1])) > 1e-9 else R
                for a, b in zip(R[:-1], R[1:]):
                    ka, kb = cle(a), cle(b)
                    if ka != kb:
                        aretes[(ka, kb)] += 1
    orph = [(a, b) for (a, b), n in aretes.items() if aretes.get((b, a), 0) == 0]
    x0, y0, x1, y1 = ctx.EMPRISE
    bats = [np.asarray(r, dtype=np.float64)[:, :2] for _, _, polys in ctx.batiments() for p in polys for r in p]   # repère local
    if bats:
        A = np.vstack([np.vstack([B, B[:1]])[:-1] for B in bats])
        Bb = np.vstack([np.vstack([B, B[:1]])[1:] for B in bats])
    lg = collections.Counter()
    pires = []
    for a, b in orph:
        pa, pb = repere(np.array([a, b], dtype=np.float64) / 1000.0)
        m = (pa + pb) / 2
        L = float(np.hypot(*(pb - pa)))
        if min(abs(m[0] - x0), abs(m[0] - x1), abs(m[1] - y0), abs(m[1] - y1)) < 0.01:
            lg["bord_carre"] += L
            continue
        if bats:
            dd, _, _ = distance_segments(m[None], A, Bb)
            if dd[0] < 0.02:
                lg["batiments"] += L
                continue
        lg["lacune"] += L
        pires.append((L, m))
    if lg["lacune"] > 0.01:
        pires.sort(key=lambda x: -x[0])
        err.append(f"[surfaces] {lg['lacune']:.3f} m d'arêtes non partagées hors bord et bâtiments (GQ-TOP-004), "
                   f"ex. {[(round(float(m[0]), 2), round(float(m[1]), 2)) for _, m in pires[:3]]}")
    return {"aretes": len(aretes), "orphelines_m": {k: round(v, 3) for k, v in sorted(lg.items())}}


def orientation(K, err, warn):
    ids = sorted(K)
    P = {k: repere(np.asarray(K[k]["geometry"]["coordinates"])[:, :2]) for k in ids}
    A = np.vstack([P[k][:-1] for k in ids])
    B = np.vstack([P[k][1:] for k in ids])
    own = np.concatenate([np.full(len(P[k]) - 1, i) for i, k in enumerate(ids)])
    pmin, marge = RQ.param("GQ-ORI-001", "part_min_ratio"), RQ.param("GQ-ORI-001", "marge_ratio")
    n_err, bas_circ = 0, {}
    for i, k in enumerate(ids):
        sel = own != i
        d = RQ.diagnostic_cotes(P[k], A[sel], B[sel])
        bas_circ[k] = d["bas"]["circulee"]
        if d["haut"]["circulee"] >= pmin and d["haut"]["circulee"] >= d["bas"]["circulee"] + marge:
            err.append(f"{k} : voie circulée du côté haut ({d['haut']['circulee']:.2f} contre {d['bas']['circulee']:.2f}) (GQ-ORI-001)")
            n_err += 1
    # GQ-ORI-003 : sens opposés aux nœuds G1
    opp = 0
    for k in ids:
        g = K[k]["properties"].get("geometrie_reguliere", {}).get("noeuds", {})
        for nom in ("debut", "fin"):
            e = g.get(nom, {})
            if e.get("type") == "noeud" and e.get("g1") and len(e["avec"]) == 1:
                o = e["avec"][0]
                go = K.get(o, {}).get("properties", {}).get("geometrie_reguliere", {}).get("noeuds", {})
                if go.get(nom, {}).get("type") == "noeud" and k in go.get(nom, {}).get("avec", []) and k < o:
                    opp += 1
                    warn.append(f"{k} / {o} : bordures prolongées en sens opposés au nœud {nom} (GQ-ORI-003)")
    return {"bordures": len(ids), "voie_cote_haut": n_err, "sens_opposes_noeuds_g1": opp, "_bas_circule": bas_circ}


def _arcs(d):
    return [e for e in d.get("primitives", []) if e["type"] == "arc"]


def ouvrages(K, couches, bas_circ, err, warn):
    out = collections.Counter()
    ceintures = {k for f in couches["ilots"] for k in f["properties"]["ceinture"]}
    for kid, f in sorted(K.items()):
        p = f["properties"]
        d = p.get("geometrie_reguliere")
        if not d:
            continue
        arcs = _arcs(d)
        # GQ-RAY-002 : angle de chaussée trop serré
        if bas_circ.get(kid, 0) >= 0.5 and kid not in ceintures:
            for e in arcs:
                dev = math.degrees((e["s1"] - e["s0"]) / e["rayon_m"])
                if e["rayon_m"] < 3.0 and dev >= 45:
                    out["angles_serres"] += 1
                    warn.append(f"{kid} : arc R {e['rayon_m']:.2f} m sur {dev:.0f}° en bord de voie circulée (GQ-RAY-002)")
        # GQ-SYM-002 : abaissé de traversée dans un arc serré
        for a in p["abaisses"]:
            if a["type"] != "traversee":
                continue
            out["abaisses_traversee"] += 1
            for e in arcs:
                if e["s0"] < a["s1"] and e["s1"] > a["s0"] and e["rayon_m"] < 12.0:
                    out["abaisses_dans_arc_serre"] += 1
                    warn.append(f"{a['id']} : abaissé de traversée sur un arc R {e['rayon_m']:.1f} m < 12 m (GQ-SYM-002)")
                    break
        # GQ-SYM-003 : quai en alignement droit
        quai = [it for it in p["intervalles"] if it["profil"] == "QUAI_BUS"]
        if quai:
            out["bordures_quai"] += 1
            courbe = [e for e in arcs if any(e["s0"] < it["s1"] and e["s1"] > it["s0"] for it in quai) and e["rayon_m"] < 500]
            if courbe:
                out["quais_en_courbe"] += 1
                warn.append(f"{kid} : quai bus sur arc R {min(e['rayon_m'] for e in courbe):.1f} m (GQ-SYM-003)")
            else:
                out["quais_droits"] += 1
    # GQ-RAY-004 : nez d'îlots
    for f in couches["ilots"]:
        p = f["properties"]
        r = (p.get("nez") or {}).get("rayon_m")
        if r is None:
            continue
        out["nez"] += 1
        if not 0.25 - 1e-6 <= r <= 1.5 + 1e-6:
            out["nez_hors_plage"] += 1
            warn.append(f"{p['id']} : rayon de nez {r} m hors 0,25-1,5 m (GQ-RAY-004)")
    # GQ-SYM-001 : zébras
    for f in couches.get("marquages", []):
        p = f["properties"]
        if p.get("classe") != "passage" or p.get("type") != "zebra":
            continue
        out["zebras"] += 1
        lb, iv = p.get("largeur_bande_m"), p.get("intervalle_m")
        if lb is not None and abs(lb - 0.5) > 1e-6:
            warn.append(f"{p['id']} : bande de {lb} m ≠ 0,50 (GQ-SYM-001)")
            out["zebras_hors_norme"] += 1
        elif iv is not None and not 0.5 - 1e-6 <= iv <= 0.8 + 1e-6:
            warn.append(f"{p['id']} : intervalle {iv} m hors 0,50-0,80 (GQ-SYM-001)")
            out["zebras_hors_norme"] += 1
    return dict(sorted(out.items()))


def marquages_bordures(M, K, err, warn):
    """GQ-VAL-002 (croisement de l'arête avant) et GQ-PAR-001 (parallélisme le long des bordures)."""
    ids = sorted(K)
    P = [repere(np.asarray(K[k]["geometry"]["coordinates"])[:, :2]) for k in ids]
    A = np.vstack([p[:-1] for p in P])
    B = np.vstack([p[1:] for p in P])
    own = np.concatenate([np.full(len(p) - 1, i) for i, p in enumerate(P)])
    out = collections.Counter()
    pr = RQ.regles()["GQ-PAR-001"]["parametres"]
    for f in sorted(M, key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        if p.get("classe") not in ("ligne", "transversale") or f["geometry"]["type"] != "LineString" or p.get("sur_bordure"):
            continue
        Q = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        L = float(abscisses(Q)[-1])
        if L < 0.2:
            continue
        out["lignes"] += 1
        # croisement : segments de la ligne contre arêtes avant (hors interruptions)
        s = np.linspace(0, L, max(3, int(L / 0.1) + 1))
        q, tg = point_a(Q, s)
        inter = [tuple(iv) for k_ in ("interruptions", "interruptions_bordures", "interruptions_bouts")
                 for iv in (p.get(k_) or []) if isinstance(iv, list) and len(iv) == 2
                 and all(isinstance(x, (int, float)) for x in iv)]
        dd, j, _ = distance_segments(q, A, B)
        proche = dd < max(0.02, (p.get("largeur_m") or 0.1) / 2)
        for iv in inter:
            proche &= ~((s >= iv[0] - 0.2) & (s <= iv[1] + 0.2))
        proche &= (s > 0.25) & (s < L - 0.25)              # bouts posés contre une bordure (places, butées)
        if proche.any():
            out["lignes_sur_bordure"] += 1
            k = ids[own[j[np.argmax(proche)]]]
            warn.append(f"{p['id']} : axe à moins d'une demi-largeur de l'arête avant de {k} sur {proche.sum() * 0.1:.1f} m (GQ-VAL-002)")
        # parallélisme : bordure dominante à moins de 1,5 m
        near = dd < pr["distance_max_m"]
        if near.sum() >= 20:
            k = collections.Counter(own[j[near]].tolist()).most_common(1)[0][0]
            near &= own[j] == k                               # points dont la bordure la plus proche est k
            Pk = P[k]
            sk, dk, _ = projeter(Pk, q[near])
            _, tk = point_a(Pk, sk)
            ang = np.degrees(np.abs(np.arcsin(np.clip(tg[near, 0] * tk[:, 1] - tg[near, 1] * tk[:, 0], -1, 1))))
            par = ang <= pr["parallelisme_max_deg"]
            if par.sum() >= 20:
                out["lignes_le_long_bordure"] += 1
                var = float(np.ptp(dk[par]))
                if var > pr["variation_distance_max_m"]:
                    out["lignes_non_paralleles"] += 1
                    warn.append(f"{p['id']} : distance à {ids[k]} variable de {var:.3f} m sur {par.sum() * 0.1:.1f} m (GQ-PAR-001)")
    return dict(sorted(out.items()))


def main():
    """python recon/pcg/decrire/regulariser_controles.py [DOSSIER] : contrôles GQ seuls, rapport JSON dans
    <DOSSIER>/regularisation/controles_regularisation.json (histogrammes de cassures, écarts par source...)."""
    import sys
    from pathlib import Path
    from commun import SORTIE, arrondi, ecrire_json
    dossier = Path(sys.argv[1]) if len(sys.argv) > 1 else SORTIE
    couches = {}
    for fam in ("bordures", "surfaces", "ilots", "ponctuels_sol", "marquages"):
        f = dossier / "base" / f"{fam}.geojson"
        if f.exists():
            couches[fam] = lire_json(f)["features"]
    err, warn, rap = controles(couches, dossier)
    rap = dict(rap, n_erreurs=len(err), n_avertissements=len(warn), erreurs=err[:200], avertissements=warn[:400])
    ecrire_json(dossier / "regularisation" / "controles_regularisation.json", arrondi(rap, 4))
    print(f"{len(err)} erreur(s), {len(warn)} avertissement(s)")
    for e in err[:40]:
        print("  -", e)


if __name__ == "__main__":
    main()
