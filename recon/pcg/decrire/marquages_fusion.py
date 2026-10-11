"""Fusion multi-sources des marquages (regles_conception.fusion_detection_inference) : GAM 2026 > plan 2025 > ortho 2022
> règles > indices v1 (FUS-SRC-001).

Étapes (ordre_application, étapes 2 à 4) :
1. hypothèses : entités GAM (marquages_gam_entites), détections libres (detection_fleches, detection_zebras,
   detection_lignes) et indices v1 paramétrés (marquages_indices_v1) ;
2. appariement par classe avec portes de distance puis affectation hongroise (FUS-ASS-003) : flèche 1,0 m (2,0 m pour un
   bloc GAM ponctuel) et 15° ; zébra : axes à 1,0 m et 10° ; symbole 0,8 m ; ligne : recouvrement ≥ 0,7 à 0,30 m ;
3. score par hypothèse S = r × c × v (FUS-SCO-002), existence P = 1 − Π(1 − S) ; la géométrie vient de l'hypothèse
   admissible la plus prioritaire, accrochée à la norme (FUS-SNP-004) ;
4. indice v1 non apparié : détection guidée sur le raster admissible de sa zone (detection_indices) ; confirmé
   (c ≥ 0,5) -> entité de source image (pose mesurée, forme normative) ; infirmé par une image admissible (c < 0,2)
   -> rejeté (S = 0,1) ; invérifiable (aucun raster admissible) -> S = 0,3 (a_verifier) ; formes d'origine raster
   (aplats, surfaces colorées, bandes isolées, contours redressés) et fantômes : jamais posés (pas de géométrie
   vectorielle ; fantôme sans preuve d'effacement postérieure aux travaux : retiré, TQ-MQG-012) ;
5. conflits (FUS-CON-005) : type de flèche levé ou détecté (c ≥ 0,6) ≠ type déduit des manœuvres 2026 -> la géométrie
   observée est gardée, étiquette conflit_norme et les deux hypothèses sont notées.
"""
import collections
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import detection_indices as DI  # noqa: E402
import marquages_commun as M  # noqa: E402
import marquages_sources as S  # noqa: E402
from commun import abscisses, densifier, distance_segments, point_a, projeter  # noqa: E402

PORTES = {"fleche": (1.0, 15.0), "fleche_bloc": (2.0, 15.0), "zebra": (1.0, 10.0), "symbole": (0.8, 30.0)}  # FUS-ASS-003
TYPES_RASTER = ("aplat", "surface_coloree", "bande_isolee", "divers")


# --------------------------------------------------------------------------- appariement (FUS-ASS-003)
def hongrois(C):
    """Affectation de coût minimal (méthode hongroise, O(n³)) d'une matrice rectangulaire (inf = interdit) :
    [(i, j)] des couples finis."""
    C = np.asarray(C, float)
    n, m = C.shape
    if n == 0 or m == 0:
        return []
    N = max(n, m)
    grand = 1e6
    A = np.full((N, N), grand)
    A[:n, :m] = np.where(np.isfinite(C), C, grand)
    u, v = np.zeros(N + 1), np.zeros(N + 1)
    p, way = np.zeros(N + 1, int), np.zeros(N + 1, int)
    for i in range(1, N + 1):
        p[0] = i
        j0 = 0
        minv = np.full(N + 1, np.inf)
        used = np.zeros(N + 1, bool)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta, j1 = np.inf, -1
            for j in range(1, N + 1):
                if not used[j]:
                    cur = A[i0 - 1, j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(N + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    out = []
    for j in range(1, N + 1):
        i = p[j]
        if i and i <= n and j <= m and np.isfinite(C[i - 1, j - 1]):
            out.append((i - 1, j - 1))
    return sorted(out)


def _origine(e):
    return np.asarray(e["pose"]["origine_local"], float)


def apparier_poses(A, B, porte_m, porte_deg, cap_libre=False):
    """Couples (i, j) d'entités posées (origine, cap) : coût = distance / porte, hongrois."""
    C = np.full((len(A), len(B)), np.inf)
    for i, a in enumerate(A):
        for j, b in enumerate(B):
            d = float(np.hypot(*(_origine(a) - _origine(b))))
            dc = S.angle_diff(a["pose"]["cap_deg"], b["pose"]["cap_deg"])
            if cap_libre:
                dc = min(dc, 180.0 - dc)
            if d <= porte_m and dc <= porte_deg:
                C[i, j] = d / porte_m + 0.1 * dc / porte_deg
    return hongrois(C)


def _centre_zebra(e):
    A, B = e["geom"][1][:2]
    return 0.5 * (A + B), M.cap_de(B - A)


def _emprise(e):
    import marquages_contraintes as CT
    return CT.emprise_zebra(e, marge=0.0)


def apparier_zebras(A, B, porte_m=PORTES["zebra"][0], porte_deg=PORTES["zebra"][1]):
    """Zébras (FUS-ASS-003) : axes à moins de 1,0 m et 10°, ou emprises des bandes qui se recouvrent sur au moins 30 % de
    la plus petite (même passage décrit avec une autre orientation de bandes ou une autre étendue)."""
    from commun import dans_polygone, echantillons_interieurs
    C = np.full((len(A), len(B)), np.inf)
    for i, a in enumerate(A):
        ca, ga = _centre_zebra(a)
        Pa = a["geom"][1][:2]
        Ea = _emprise(a)
        for j, b in enumerate(B):
            cb, gb = _centre_zebra(b)
            Pb = b["geom"][1][:2]
            if float(np.hypot(*(ca - cb))) > 15.0:
                continue
            da = min(S.angle_diff(ga, gb), 180.0 - S.angle_diff(ga, gb))
            _, d1, _ = projeter(Pa, cb[None])
            _, d2, _ = projeter(Pb, ca[None])
            d = float(min(d1[0], d2[0]))
            if da <= porte_deg and d <= porte_m:
                C[i, j] = d / porte_m + 0.1 * da / porte_deg
                continue
            Eb = _emprise(b)
            qa = echantillons_interieurs([Ea], 0.1)
            qb = echantillons_interieurs([Eb], 0.1)
            if len(qa) == 0 or len(qb) == 0:
                continue
            fa = float(dans_polygone(qa, [Eb]).mean())
            fb = float(dans_polygone(qb, [Ea]).mean())
            if max(fa, fb) >= 0.3:
                C[i, j] = 1.0 + (1.0 - max(fa, fb))
    return hongrois(C)


# --------------------------------------------------------------------------- lignes : recouvrement
def peint_ligne(e, pas=0.25):
    """Points des parties peintes d'une ligne (local) et tangentes."""
    from marquages_controles import _echantillons, _pieces
    P = e["geom"][1]
    q = dict(e, type="discontinue") if e["classe"] == "transversale" else e
    iv = _pieces(q, P)
    return _echantillons(P, iv, pas)


def segments_ligne(e):
    from marquages_controles import _pieces, _segments
    P = e["geom"][1]
    q = dict(e, type="discontinue") if e["classe"] == "transversale" else e
    return _segments(P, _pieces(q, P))


def recouvrement(e_ind, refs, porte=0.30):
    """Part des points peints de e_ind situés à moins de `porte` d'une partie peinte d'une ligne de refs (quasi
    parallèle, cos ≥ 0,9) et liste des lignes concernées."""
    q, t = peint_ligne(e_ind)
    if len(q) == 0:
        return 0.0, [], np.zeros(0, bool)
    couvert = np.zeros(len(q), bool)
    qui = []
    for r in refs:
        A, B = r["_seg"]
        if len(A) == 0:
            continue
        bb = r["_bb"]
        dedans = (q[:, 0] > bb[0] - porte) & (q[:, 0] < bb[2] + porte) & (q[:, 1] > bb[1] - porte) & (q[:, 1] < bb[3] + porte)
        if not dedans.any():
            continue
        d, j, _ = distance_segments(q[dedans], A, B)
        sg = B[j] - A[j]
        sg /= np.maximum(np.hypot(*sg.T), 1e-12)[:, None]
        par = np.abs(np.einsum("ij,ij->i", sg, t[dedans])) >= 0.9
        ok = (d <= porte) & par
        if ok.any():
            idx = np.where(dedans)[0][ok]
            couvert[idx] = True
            qui.append(r["id"])
    return float(couvert.mean()), sorted(set(qui)), couvert


def preparer_refs(lignes):
    for r in lignes:
        A, B = segments_ligne(r)
        r["_seg"] = (A, B)
        P = np.vstack([A, B]) if len(A) else r["geom"][1]
        r["_bb"] = (*P.min(axis=0), *P.max(axis=0))
    return lignes


# --------------------------------------------------------------------------- scores et provenance
def ajouter_source(e, src, ref, c=1.0, etat=None, conf_regle=None, lien=None):
    etat = etat or e.get("etat_zone", "conserve")
    s = S.score(src, c, etat, conf_regle)
    e.setdefault("sources", []).append({"src": src, "ref": ref, "c": None if c is None else round(float(c), 3), "S": round(s, 3)})
    if lien:
        e["lien_v1"] = sorted(set(e.get("lien_v1", [])) | set(lien))
    return s


def finaliser_score(e, regle_exige=False):
    P = S.existence([x["S"] for x in e.get("sources", [])])
    statut, etiquette = S.decision(P, regle_exige)
    e["score"] = round(P, 3)
    e["confiance"] = S.confiance_de(P)
    if etiquette:
        e["a_verifier"] = True
    return statut


def semantique_v1(e, ind):
    """Attributs sémantiques repris de l'indice v1 apparié (couleur, usure, couverture, groupe) — jamais la géométrie."""
    if ind.get("couleur") and ind["couleur"] != e.get("couleur"):
        e["couleur"] = ind["couleur"]
        e["prov"]["couleur"] = {"src": "a_priori:indice_v1", "ref": f"couleur de l'indice v1 {ind['id']}", "conf": "moyenne"}
    if e.get("etat_zone") == "conserve" and ind.get("usure") is not None:
        e["usure"], e["couverture"] = str(ind["usure"]), ind.get("couverture", e.get("couverture"))
        e["prov"]["usure"] = {"src": "a_priori:indice_v1", "ref": f"usure de l'indice v1 {ind['id']} (ortho 2022)", "conf": "moyenne"}
    if ind.get("groupe"):
        e.setdefault("groupes_v1", [])
        e["groupes_v1"] = sorted(set(e["groupes_v1"]) | {ind["groupe"]})
