"""Contraintes de pose des marquages (actions « contraindre », étape 6) et mesures de contrôle associées.

- MQ-LIG-002 / art. 118 / MQ-DET-010 : les lignes longitudinales s'interrompent à 0,50 m de part et d'autre de tout
  passage piéton (emprise des bandes élargie de 0,50 m) et au droit des lignes d'effet peintes, des zigzags et des
  marques posées (flèches, figurines, glyphes : empreinte élargie de 0,10 m) ; aucune marque n'en chevauche une autre ;
- dégagement des bordures levées GAM 2026 (SOL_BORDURE, 622 polylignes) : une ligne s'interrompt là où son axe passe à
  moins de largeur / 2 + 2u (0,10 m) d'une arête de bordure (pas de tiret sur une bordure ; interruptions_bordures) ;
- MQ-LIG-001 : aucune ligne inférée dans l'aire du carrefour (les règles n'en créent que sur les routes hors jonction).
"""
import functools
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import marquages_commun as M  # noqa: E402
from commun import VECTEURS, abscisses, couper_polyligne, distance_segments, lire_geojson, repere  # noqa: E402

BORDURES_GAM = VECTEURS / "etat_2026/bordure_lin_L93.geojson"
DEGAGEMENT = 0.10


@functools.lru_cache(maxsize=None)
def bordures_gam():
    """Segments des arêtes de bordure levées GAM (local) : (A, B)."""
    A, B = [], []
    for f in lire_geojson(BORDURES_GAM):
        g = f["geometry"]
        lignes = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
        for c in lignes:
            P = repere(np.asarray(c, float)[:, :2])
            if len(P) >= 2:
                A.append(P[:-1])
                B.append(P[1:])
    return np.vstack(A), np.vstack(B)


def _fusion(iv):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1] + 1e-6:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def emprise_zebra(e, marge=0.5):
    A, B = e["geom"][1][:2]
    h = math.radians(e["cap_bandes_deg"])
    u = np.array([math.cos(h), math.sin(h)])
    n = np.array([-u[1], u[0]])
    pts = []
    for P in (A, B):
        for a in (-1, 1):
            for b in (-1, 1):
                pts.append(P + u * a * (e["longueur_bande_m"] / 2 + marge) + n * b * (e["largeur_bande_m"] / 2 + marge))
    return M.enveloppe_convexe(np.array(pts))


def interrompre(entites):
    """Interruptions des lignes (modifiées sur place) -> journal {ligne: [motifs]}."""
    import marquages_reprises as RP
    from commun import dans_polygone
    journal = {}
    zebras = [(e["id"], emprise_zebra(e)) for e in entites if e["classe"] == "passage" and e["type"] == "zebra"]
    bloquants = []
    for e in entites:
        if e["classe"] in ("fleche", "symbole") or (e["classe"] == "zone" and e["type"] in ("zigzag", "hachures")) or \
                (e["classe"] == "transversale" and not (e.get("fabrication") or {}).get("statut")) or \
                (e["classe"] == "passage" and e["type"] == "traversee_cyclable"):
            p = RP.empreinte(e)
            if p:
                P = np.vstack([r for poly in p for r in poly])
                bloquants.append((e["id"], p, (*P.min(axis=0) - 0.6, *P.max(axis=0) + 0.6)))
    KA, KB = bordures_gam()
    for e in entites:
        if e["classe"] != "ligne":
            continue
        P = e["geom"][1]
        L = float(abscisses(P)[-1])
        iv, motifs = [], []
        for zid, poly in zebras:
            for a, b in couper_polyligne(P, [poly]):
                iv.append([max(0.0, a), min(L, b)])
                motifs.append(zid)
        # échantillons de l'axe
        s = np.arange(0.0, L, 0.02)
        if len(s) == 0:
            continue
        from commun import point_a
        Q, _ = point_a(P, s)
        w = float(e["largeur_m"])
        lo, hi = Q.min(axis=0) - 1.0, Q.max(axis=0) + 1.0
        for bid, polys, bb in bloquants:
            if bb[2] < lo[0] or bb[0] > hi[0] or bb[3] < lo[1] or bb[1] > hi[1]:
                continue
            A = np.vstack([r for poly in polys for r in poly])
            B = np.vstack([np.roll(r, -1, axis=0) for poly in polys for r in poly])
            d, _, _ = distance_segments(Q, A, B)
            dedans = np.zeros(len(Q), bool)
            for poly in polys:
                dedans |= dans_polygone(Q, poly)
            m = dedans | (d < w / 2 + 0.10)
            if m.any():
                for a, b in _plages(s, m):
                    iv.append([max(0.0, a - 0.02), min(L, b + 0.02)])
                motifs.append(bid)
        # bordures levées GAM
        sel = (np.minimum(KA[:, 0], KB[:, 0]) < hi[0]) & (np.maximum(KA[:, 0], KB[:, 0]) > lo[0]) & \
              (np.minimum(KA[:, 1], KB[:, 1]) < hi[1]) & (np.maximum(KA[:, 1], KB[:, 1]) > lo[1])
        ib = []
        if sel.any():
            d, _, _ = distance_segments(Q, KA[sel], KB[sel])
            m = d < w / 2 + DEGAGEMENT
            if m.any() and m.mean() < 0.9:
                ib = [[max(0.0, a - 0.02), min(L, b + 0.02)] for a, b in _plages(s, m)]
            elif m.any():
                e["sur_bordure"] = round(float(m.mean()), 3)         # ligne posée le long d'une bordure sur toute sa longueur
        if iv or ib:
            e["interruptions"] = _fusion(e.get("interruptions", []) + [[round(a, 3), round(b, 3)] for a, b in iv + ib])
            if motifs:
                e["interruptions_marques"] = sorted(set(motifs))
            if ib:
                e["interruptions_bordures"] = [[round(a, 3), round(b, 3)] for a, b in _fusion(ib)]
            journal[e["id"]] = sorted(set(motifs)) + (["bordure_gam"] if ib else [])
    return journal


def _plages(s, m):
    out = []
    i = 0
    while i < len(m):
        if m[i]:
            j = i
            while j + 1 < len(m) and m[j + 1]:
                j += 1
            out.append((float(s[i]), float(s[j])))
            i = j + 1
        else:
            i += 1
    return out
