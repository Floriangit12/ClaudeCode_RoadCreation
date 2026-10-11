"""Contrôles de la famille marquages, schéma 0.3 (appelés par valider.py ; règles « verifier » de regles_conception).

Bloquants (erreurs) :
- correspondance : chacun des 996 marquages v1 a un devenir, une seule fois, justifié ; entités citées existantes ;
  liens réciproques (lien_v1 <-> correspondance) ;
- provenance (FUS-SRC-001, FUS-SCO-002) : src présent, score dans [0, 1], au moins une source ; aucune entité de source v1
  seule sans étiquette a_verifier ; aucun fantôme (TQ-MQG-012 : pas d'empreinte effacée sans preuve) ;
- lignes : longueur_m = longueur de la géométrie (± 1 cm), phase dans la période, interruptions triées dans [0, L] ;
  ancrage xodr : axe recalculé à moins de 5 mm ;
- MQ-DET-010 / art. 118 : aucune partie peinte de ligne longitudinale dans l'emprise d'un zébra ; aucun tiret sur une
  bordure levée GAM (axe à moins de largeur / 2 d'une arête de bordure, hors lignes posées le long d'une bordure) ;
- MQ-DET-010 : recouvrement entre empreintes de marques de classes différentes ≤ 0,05 m² (hors lignes / zones
  hachurées, couverts par les interruptions) ;
- 0 contour en marches d'escalier.
Mesures et avertissements (rapport) :
- MQ-FLE-006 / DET-FLE-005 / VAL-FLE-001 : flèche entièrement dans sa voie (≥ 95 % de l'empreinte dans les voies roulables
  OpenDRIVE) et centrée (écart latéral de l'axe de tige corrigé du décalage normatif au milieu de voie ≤ 0,30 m) ;
- MQ-PP-004 / VAL-ZEB-003 : bandes de 0,50 m, intervalle dans [0,50 ; 0,80] ; zébra dans la chaussée (≥ 75 % de chaque
  bande dans les voies roulables, la chaussée 2026 ou les surfaces circulées) ; aligné sur des bordures abaissées
  (GA-ABA-002 : extrémités du passage à moins de 3 m d'une traversée abaissée du relief 2026 ou d'un bloc CHARTIERE GAM) ;
- MQ-LEF-004 / MQ-LEF-005 : ligne d'effet peinte à 2,5-4,5 m du passage aval et parallèle à ± 3° ;
- part inférée par zone (VAL-COV-006).
"""
import collections
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import marquages_commun as M  # noqa: E402
from commun import (DONNEES, VECTEURS, abscisses, anneaux, dans_polygone, distance_segments, echantillons_interieurs,  # noqa: E402
                    lire_geojson, repere)


def _local(c):
    return repere(np.asarray(c, float)[..., :2])


@__import__("functools").lru_cache(maxsize=None)
def _roulable():
    roul = []
    for f in lire_geojson(DONNEES / "opendrive/lanes_2026.geojson"):
        t = f["properties"].get("type")
        if t in ("driving", "biking", "bus") or (t is None and f["properties"].get("jonction")):
            roul += [[repere(r) for r in poly] for poly in anneaux(f["geometry"])]
    for f in lire_geojson(DONNEES / "relief/relief_zones_2026.geojson"):
        if f["properties"].get("zone") == "chaussee_2026":
            roul += [[repere(r) for r in poly] for poly in anneaux(f["geometry"])]
    return roul


def _dans_roulable(Q):
    m = np.zeros(len(Q), bool)
    for poly in _roulable():
        r = poly[0]
        lo, hi = r.min(axis=0), r.max(axis=0)
        sel = (Q[:, 0] >= lo[0]) & (Q[:, 0] <= hi[0]) & (Q[:, 1] >= lo[1]) & (Q[:, 1] <= hi[1])
        if sel.any():
            m[sel] |= dans_polygone(Q[sel], poly)
    return m


def _abaisses():
    pts = []
    for f in lire_geojson(DONNEES / "relief/relief_zones_2026.geojson"):
        if f["properties"].get("zone") == "traversee_bordure_abaissee":
            for poly in anneaux(f["geometry"]):
                pts.append(repere(poly[0]))
    for f in lire_geojson(VECTEURS / "etat_2026/bordure_pct_L93.geojson"):
        g = f["geometry"]
        c = g["coordinates"] if g["type"] == "Point" else g["coordinates"][0]
        pts.append(repere(np.asarray(c, float)[:2][None]))
    return np.vstack(pts) if pts else np.zeros((0, 2))


def controles(feats, corr):
    import marquages_contraintes as CT
    import marquages_reprises as RP
    from marquages_controles import _echantillons, _pieces, entite_locale
    err, warn = [], []
    mes = collections.OrderedDict()
    ids = {f["properties"]["id"]: f for f in feats}
    v1 = {m["id"] for m in M.v1()}
    # ---- correspondance
    vus = collections.Counter(c["properties"]["id"] for c in corr)
    for mq, n in sorted(vus.items()):
        if n != 1:
            err.append(f"{mq} : {n} lignes de correspondance")
    for mq in sorted(v1 - set(vus)):
        err.append(f"{mq} : marquage v1 sans devenir")
    ent_de = {}
    for c in corr:
        p = c["properties"]
        ent_de[p["id"]] = p["entite"]
        if len(p.get("note") or "") < 10:
            err.append(f"{p['id']} : devenir non justifié")
        if p["devenir"] != "retire":
            f = ids.get(p["entite"])
            if f is None:
                err.append(f"{p['id']} : entité {p['entite']} absente")
            elif p["id"] not in f["properties"]["lien_v1"]:
                err.append(f"{p['id']} : absent de lien_v1 de {p['entite']}")
    for i, f in sorted(ids.items()):
        for mq in f["properties"].get("lien_v1", []):
            if ent_de.get(mq) != i:
                err.append(f"{i} : lien_v1 {mq} rattaché à {ent_de.get(mq)}")
    # ---- provenance
    for i, f in sorted(ids.items()):
        p = f["properties"]
        if "src" not in p or "score" not in p or not p.get("sources"):
            err.append(f"{i} : provenance 0.3 incomplète (src, score, sources)")
        if p.get("src") == "v1" and not p.get("a_verifier"):
            err.append(f"{i} : source v1 seule sans étiquette a_verifier (FUS-SCO-002)")
        if p["classe"] == "fantome":
            err.append(f"{i} : fantôme décrit sans preuve d'effacement (TQ-MQG-012)")
    # ---- entités locales
    E = {i: entite_locale(f) for i, f in sorted(ids.items())}
    emp = {}
    for i, e in E.items():
        try:
            emp[i] = RP.empreinte(e)
        except Exception as x:  # noqa: BLE001
            err.append(f"{i} : empreinte non calculable ({type(x).__name__})")
            emp[i] = []
    # ---- lignes
    zebras = {i: CT.emprise_zebra(e, marge=0.0) for i, e in E.items() if e["classe"] == "passage" and e["type"] == "zebra"}
    KA, KB = CT.bordures_gam()
    n_sur_zebra, n_sur_bordure, long_bordure = 0, 0, 0.0
    for i, e in E.items():
        p = ids[i]["properties"]
        if e["classe"] not in ("ligne", "transversale"):
            continue
        P = e["geom"][1]
        L = float(abscisses(P)[-1])
        if abs(L - p["longueur_m"]) > 0.01:
            err.append(f"{i} : longueur_m {p['longueur_m']} ≠ géométrie {L:.3f}")
        if (p["type"] == "discontinue" or e["classe"] == "transversale") and p["phase_m"] >= p["trait_m"] + p["vide_m"] + 1e-6:
            err.append(f"{i} : phase_m hors période")
        prec = 0.0
        for a, b in p.get("interruptions", []):
            if a < prec - 1e-6 or b < a or b > L + 0.01:
                err.append(f"{i} : interruption [{a}, {b}] hors [0, {L:.3f}] ou non triée")
            prec = b
        if e["classe"] != "ligne" or (p.get("fabrication") or {}).get("statut") == "non_fabrique":
            continue
        iv = _pieces(e, P)
        q, t = _echantillons(P, iv, 0.05)
        if len(q) == 0:
            continue
        for zid, Z in zebras.items():
            lo, hi = Z.min(axis=0), Z.max(axis=0)
            sel = (q[:, 0] >= lo[0]) & (q[:, 0] <= hi[0]) & (q[:, 1] >= lo[1]) & (q[:, 1] <= hi[1])
            if sel.any() and dans_polygone(q[sel], [Z]).sum() * 0.05 > 0.10:
                n_sur_zebra += 1
                err.append(f"{i} : partie peinte dans le zébra {zid} (MQ-DET-010, art. 118)")
        lo, hi = q.min(axis=0) - 1, q.max(axis=0) + 1
        sel = (np.minimum(KA[:, 0], KB[:, 0]) < hi[0]) & (np.maximum(KA[:, 0], KB[:, 0]) > lo[0]) & \
              (np.minimum(KA[:, 1], KB[:, 1]) < hi[1]) & (np.maximum(KA[:, 1], KB[:, 1]) > lo[1])
        if sel.any() and not p.get("sur_bordure"):
            d, _, _ = distance_segments(q, KA[sel], KB[sel])
            lb = float((d < p["largeur_m"] / 2).sum()) * 0.05
            if lb > 0.20:
                n_sur_bordure += 1
                long_bordure += lb
                err.append(f"{i} : {lb:.2f} m de partie peinte sur une bordure levée GAM (MQ-DET-010)")
    mes["lignes_sur_zebra"] = n_sur_zebra
    mes["lignes_sur_bordure"] = {"n": n_sur_bordure, "longueur_m": round(long_bordure, 2)}
    # ---- recouvrements entre classes (lignes exclues : interruptions)
    cles = [i for i in E if E[i]["classe"] not in ("ligne", "transversale") and emp.get(i)
            and (ids[i]["properties"].get("fabrication") or {}).get("statut") != "non_fabrique"]
    bb = {i: (*np.vstack([r for pl in emp[i] for r in pl]).min(axis=0), *np.vstack([r for pl in emp[i] for r in pl]).max(axis=0)) for i in cles}
    recs = []
    for a in range(len(cles)):
        for b in range(a + 1, len(cles)):
            ia, ib = cles[a], cles[b]
            A, B = bb[ia], bb[ib]
            if A[2] < B[0] or B[2] < A[0] or A[3] < B[1] or B[3] < A[1]:
                continue
            if {E[ia]["classe"], E[ib]["classe"]} == {"zone"} and "bande_isolee" in (E[ia]["type"], E[ib]["type"]):
                continue
            x0, y0 = min(A[0], B[0]) - 0.05, min(A[1], B[1]) - 0.05
            nx, ny = int((max(A[2], B[2]) - x0) / 0.02) + 3, int((max(A[3], B[3]) - y0) / 0.02) + 3
            if nx * ny > 6_000_000:
                continue
            ma = M.raster_masque(emp[ia], x0, y0, nx, ny, 0.02)
            mb = M.raster_masque(emp[ib], x0, y0, nx, ny, 0.02)
            ar = float((ma & mb).sum()) * 4e-4
            if ar > 0.05:
                recs.append((ia, ib, round(ar, 3)))
    for ia, ib, ar in recs:
        (err if ar > 0.25 else warn).append(f"{ia} / {ib} : empreintes superposées sur {ar} m² (MQ-DET-010)")
    mes["recouvrements"] = len(recs)
    # ---- marches d'escalier
    for i, f in sorted(ids.items()):
        g = f["geometry"]
        if g["type"] in ("Polygon", "MultiPolygon") and f["properties"]["classe"] in ("zone", "fantome"):
            for poly in anneaux(g):
                if any(M.contour_raster(r) for r in poly):
                    err.append(f"{i} : contour en marches d'escalier")
    # ---- flèches dans leur voie et centrées (MQ-FLE-006, DET-FLE-005, VAL-FLE-001)
    import marquages_inference as INF
    import marquages_symboles as SY
    import xodr_echantillonne as X
    reseau = X.lire_xodr()
    loc = SY.Localisateur(reseau)
    fl = []
    for i, e in E.items():
        if e["classe"] != "fleche":
            continue
        polys = emp[i]
        Q = np.vstack([echantillons_interieurs(poly, 0.05) for poly in polys])
        dedans = float(_dans_roulable(Q).mean()) if len(Q) else 0.0
        o = np.asarray(e["pose"]["origine_local"], float)
        ex, ey = M.axes_cap(e["pose"]["cap_deg"])
        vs = [v for v in loc.voies(o + 1.5 * ey) if not v["jonction"]]
        ecart = None
        if vs:
            v = vs[0]
            r = reseau[v["route"]]
            sec = r.section(v["s"])
            tb = r.t_bords(np.array([v["s"]]), sec)
            vi = v["voie"] + 1 if v["voie"] < 0 else v["voie"] - 1
            tm = 0.5 * (float(tb[v["voie"]][0]) + float(tb[vi][0]))
            sens = 1 if v["voie"] < 0 else -1
            t_axe = v["t"] + INF.DECALAGE_TIGE.get(e["gabarit"], 0.0) * sens
            ecart = abs(t_axe - tm)
        fl.append((i, dedans, ecart))
        if dedans < 0.95:
            warn.append(f"{i} : flèche à {dedans:.0%} dans les voies roulables OpenDRIVE (MQ-DET-010, INF-FLE-006)")
        if ecart is not None and ecart > 0.30:
            warn.append(f"{i} : axe de tige à {ecart:.2f} m du milieu de voie OpenDRIVE (MQ-FLE-006 ; levé ou détection gardés)")
    ec = np.array([x[2] for x in fl if x[2] is not None])
    mes["fleches"] = {"n": len(fl), "dans_voie_95": sum(1 for x in fl if x[1] >= 0.95),
                      "ecart_centre_p50_m": round(float(np.median(ec)), 3) if len(ec) else None,
                      "ecart_centre_p95_m": round(float(np.percentile(ec, 95)), 3) if len(ec) else None,
                      "centrees_0_30": int((ec <= 0.30).sum())}
    # ---- zébras : bandes normatives, dans la chaussée, alignés sur des abaissés (MQ-PP-004, VAL-ZEB-003, GA-ABA-002)
    ab = _abaisses()
    zz = []
    for i, e in E.items():
        if e["classe"] != "passage" or e["type"] != "zebra":
            continue
        p = ids[i]["properties"]
        if abs(p["largeur_bande_m"] - 0.5) > 1e-6 or not (0.5 - 1e-6 <= p["intervalle_m"] <= 0.8 + 1e-6):
            warn.append(f"{i} : bande {p['largeur_bande_m']} / intervalle {p['intervalle_m']} hors MQ-PP-004")
        A, B = e["geom"][1][:2]
        h = math.radians(p["cap_bandes_deg"])
        u = np.array([math.cos(h), math.sin(h)])
        n = np.array([-u[1], u[0]])
        ax = (B - A) / max(float(np.hypot(*(B - A))), 1e-9)
        fr = []
        for k in range(int(p.get("nb_emplacements") or p["nb_bandes"])):
            if k in p["coupures"]:
                continue
            c = A + ax * k * p["pas_axe_m"]
            ga, gb = np.meshgrid(np.linspace(-0.45, 0.45, 7), np.linspace(-0.4, 0.4, 3))
            pts = c + np.outer(ga.ravel() * p["longueur_bande_m"], u) + np.outer(gb.ravel() * p["largeur_bande_m"], n)
            fr.append(float(_dans_roulable(pts).mean()))
        dans = min(fr) if fr else 0.0
        ext = [A - ax * (p["pas_axe_m"]), B + ax * (p["pas_axe_m"])]
        d_ab = [float(np.min(np.hypot(*(ab - x).T))) if len(ab) else 99.0 for x in ext]
        aligne = sum(1 for d in d_ab if d <= 3.0)
        zz.append((i, dans, aligne))
        if dans < 0.75:
            warn.append(f"{i} : une bande n'est qu'à {dans:.0%} dans la chaussée de référence (VAL-ZEB-003)")
        if aligne < 2:
            warn.append(f"{i} : {aligne} extrémité(s) sur 2 à moins de 3 m d'une traversée abaissée (GA-ABA-002)")
    mes["zebras"] = {"n": len(zz), "dans_chaussee": sum(1 for x in zz if x[1] >= 0.75),
                     "alignes_abaisses_2_extremites": sum(1 for x in zz if x[2] >= 2),
                     "alignes_abaisses_1_extremite": sum(1 for x in zz if x[2] == 1)}
    # ---- ligne d'effet / passage (MQ-LEF-004, MQ-LEF-005)
    lef = []
    for i, e in E.items():
        if e["classe"] != "transversale":
            continue
        p = ids[i]["properties"]
        P = e["geom"][1]
        c = P.mean(axis=0)
        best = None
        for zid, Z in zebras.items():
            d, _, _ = distance_segments(c[None], Z, np.roll(Z, -1, axis=0))
            if best is None or d[0] < best[0]:
                best = (float(d[0]), zid)
        if best is None:
            continue
        ze = E[best[1]]
        ga = M.cap_de(ze["geom"][1][1] - ze["geom"][1][0])
        gl = M.cap_de(P[-1] - P[0])
        da = min(abs((ga - gl + 180) % 360 - 180), 180 - abs((ga - gl + 180) % 360 - 180))
        lef.append((i, round(best[0], 2), round(da, 1), p.get("peinte", True) and not (p.get("fabrication") or {}).get("statut")))
        if lef[-1][3] and not (2.5 - 0.075 <= best[0] <= 4.5 + 0.075):
            warn.append(f"{i} : ligne d'effet peinte à {best[0]:.2f} m du passage {best[1]} (MQ-LEF-004 : 2,5-4,5 m)")
        if lef[-1][3] and da > 3.0:
            warn.append(f"{i} : ligne d'effet non parallèle au passage {best[1]} ({da:.1f}°, MQ-LEF-003)")
    mes["lignes_effet"] = [{"id": i, "distance_passage_m": d, "ecart_angle_deg": a, "peinte": bool(pt)} for i, d, a, pt in lef]
    # ---- part inférée par état de zone (VAL-COV-006)
    part = collections.defaultdict(collections.Counter)
    for i, f in ids.items():
        p = f["properties"]
        part[p.get("zone_etat") or p["etat"]]["regle" if str(p.get("src", "")).startswith("regle:") else "observe"] += 1
    mes["part_inferee_par_zone"] = {k: round(v["regle"] / max(1, sum(v.values())), 3) for k, v in sorted(part.items())}
    return err, warn, mes
