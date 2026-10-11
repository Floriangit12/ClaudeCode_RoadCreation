"""Contrôles de support des marquages NON levés (revues conformité et réalisme du 11/10/2026), appliqués par
marquages.construire après l'ancrage final (une ligne d'appel) :

- VAL-FLE-001 / INF-FLE-004 : flèche directionnelle non GAM (ortho 2022, plan 2025, indice v1) dont le cap s'oppose au
  sens de circulation de la voie OpenDRIVE qui la porte (écart > 90°), ou posée sur l'axe d'une chaussée à double sens
  (centre à moins de 0,5 m de la limite entre voies de sens opposés) : non fabriquée, a_verifier, conflit_norme
  (MF-0286 : cap 123° sur l'axe de la route 5 dont la voie 1 circule à 305°) ;
- MQ-DET-010 / FUS-CON-005 : marque surfacique non GAM (passage, zone, symbole) traversée par une bordure levée GAM
  2026 hors abaissé (≥ 0,20 m de bordure dans l'empreinte) : la marque de l'ortho 2022 ou du plan 2025 contredit le
  levé 2026 ; non fabriquée (et non découpée), a_verifier, conflit_norme (MP-0875 : 5 découpes de dégagement).

Les entités restent dans la description (hypothèses) ; le devenir de leurs marquages v1 passe à garde_non_fabrique.
Python + numpy, déterministe (tri par identifiant).
"""
import math

import numpy as np

from commun import SORTIE, abscisses, dans_polygone, densifier, lire_geojson, repere

SEUIL_AXE_M = 0.5
SEUIL_CAP_DEG = 90.0
LONGUEUR_TRAVERSEE_M = 0.20
MARGE_ABAISSE_M = 0.30


def _ecart_cap(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _bordures_gam():
    """Bordures levées GAM 2026 (base/bordures.geojson) : [(id, points échantillonnés à 5 cm, s, intervalles libres)]."""
    out = []
    for f in sorted(lire_geojson(SORTIE / "base/bordures.geojson"), key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        if (p.get("prov") or {}).get("geometrie", {}).get("src") != "gam":
            continue
        P = repere(np.asarray(f["geometry"]["coordinates"], float)[:, :2])
        Q, s = densifier(P, 0.05)
        libre = np.ones(len(s), bool)
        for a in p.get("abaisses", []):
            s0 = min([a["s0"]] + [r["s0"] for r in a.get("raccords", [])]) - MARGE_ABAISSE_M
            s1 = max([a["s1"]] + [r["s1"] for r in a.get("raccords", [])]) + MARGE_ABAISSE_M
            libre &= ~((s >= s0) & (s <= s1))
        out.append((p["id"], Q, s, libre))
    return out


def _non_fabrique(e, raison, regle, devenir):
    e["fabrication"] = {"statut": "non_fabrique", "raison": raison}
    e["a_verifier"] = True
    e["conflit_norme"] = {"regle": regle, "detail": raison}
    e["regles"] = sorted(set(e.get("regles", [])) | set(regle.split(" / ")))
    for mq in e.get("lien_v1", []):
        devenir[mq] = ("garde_non_fabrique", e["id"], raison)


def fleches_sens(entites, loc, reseau, devenir):
    """VAL-FLE-001 : flèches non GAM à contresens ou sur l'axe d'une chaussée à double sens."""
    j = {}
    for e in sorted(entites, key=lambda e: e["id"]):
        if e["classe"] != "fleche" or e.get("type") != "directionnelle" or str(e.get("src", "")) == "gam":
            continue
        if (e.get("fabrication") or {}).get("statut") == "non_fabrique":
            continue
        o = np.asarray((e.get("pose") or {}).get("origine_local", [np.nan, np.nan]), float)
        cap = float((e.get("pose") or {}).get("cap_deg", np.nan))
        if not np.isfinite(o).all() or not np.isfinite(cap):
            continue
        import marquages_commun as M
        ey = np.asarray(M.axes_cap(cap)[1], float)
        c = o + 2.0 * ey * float(e.get("echelle", 1.0))          # milieu de la flèche (comme completer_ancrage)
        vs = [v for v in loc.voies(c, types=("driving", "bus", "biking")) if not v["jonction"]]
        if not vs:
            continue
        v = vs[0]
        cap_v = math.degrees(v["cap"]) % 360.0
        motif = None
        if _ecart_cap(cap, cap_v) > SEUIL_CAP_DEG:
            motif = (f"cap {cap:.1f}° opposé au sens de circulation de la voie {v['route']}/{v['voie']} ({cap_v:.1f}°)")
        r = reseau[v["route"]]
        sec = r.section(v["s"])
        tb = r.t_bords(np.array([v["s"]]), sec)
        t_axe = float(tb[0][0]) if 0 in tb else 0.0
        sens = {k for k in (1, -1) if k in sec.voies and sec.voies[k].type in ("driving", "bus")}
        if motif is None and sens == {1, -1} and abs(v["t"] - t_axe) < SEUIL_AXE_M:
            motif = (f"centre à {abs(v['t'] - t_axe):.2f} m de l'axe de la route {v['route']} à double sens "
                     f"(voies 1 et −1 de sens opposés) : voie porteuse ambiguë")
        if motif:
            raison = f"flèche {e['gabarit']} non levée ({e.get('src')}) : {motif} (VAL-FLE-001, INF-FLE-004)"
            _non_fabrique(e, raison, "VAL-FLE-001", devenir)
            j[e["id"]] = raison
    return j


def surfaciques_traverses(entites, devenir):
    """MQ-DET-010 / FUS-CON-005 : marques surfaciques non GAM traversées par une bordure GAM 2026 hors abaissé."""
    import marquages_reprises as RP
    kerbs = _bordures_gam()
    j = {}
    for e in sorted(entites, key=lambda e: e["id"]):
        if e["classe"] not in ("passage", "zone", "symbole") or str(e.get("src", "")) == "gam":
            continue
        if (e.get("fabrication") or {}).get("statut") == "non_fabrique":
            continue
        try:
            e_brut = dict(e)
            e_brut.pop("decoupes", None)                    # empreinte AVANT découpes de dégagement (MP-0875 : 5 découpes)
            polys = RP.empreinte(e_brut)
        except Exception:                                   # forme sans empreinte calculable : non contrôlée
            continue
        if not polys:
            continue
        pts = np.vstack([r for poly in polys for r in poly])
        lo, hi = pts.min(0) - 0.1, pts.max(0) + 0.1
        trav = []
        for kid, Q, s, libre in kerbs:
            sel = libre & (Q[:, 0] >= lo[0]) & (Q[:, 0] <= hi[0]) & (Q[:, 1] >= lo[1]) & (Q[:, 1] <= hi[1])
            if not sel.any():
                continue
            dedans = np.zeros(len(Q), bool)
            idx = np.nonzero(sel)[0]
            for poly in polys:
                dedans[idx] |= dans_polygone(Q[idx], poly)
            lg = float(dedans.sum()) * 0.05
            if lg >= LONGUEUR_TRAVERSEE_M:
                trav.append(f"{kid} ({lg:.2f} m)")
        if trav:
            raison = (f"marque {e['classe']} {e.get('type', '')} non levée ({e.get('src')}) traversée hors abaissé par la "
                      f"bordure levée GAM 2026 {', '.join(trav)} : contredit le levé 2026, non fabriquée ni découpée "
                      "(MQ-DET-010, FUS-CON-005)")
            _non_fabrique(e, raison, "MQ-DET-010 / FUS-CON-005", devenir)
            j[e["id"]] = raison
    return j


def controler(entites, loc, reseau, devenir):
    """-> journal {fleches_sens: {id: raison}, surfaciques_traverses: {id: raison}} (entités modifiées sur place)."""
    return {"fleches_sens": fleches_sens(entites, loc, reseau, devenir),
            "surfaciques_traverses": surfaciques_traverses(entites, devenir)}
