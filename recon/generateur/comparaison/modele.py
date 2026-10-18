"""Lecture du modèle fabriqué par le générateur (recon/out/generateur/<scène>/) pour la comparaison multivues :
emprise, altitude du sol, bande sous un point, profil d'une section, et ARÊTES 3D projetables dans une photo.

Arêtes (échantillonnées tous les PAS m, avec leur tangente) :
- bordures : ligne du pied (fil d'eau) et arête haute avant, d'après l2/niveaux.json (`bordures[].points` :
  x, y, pied, tete) ;
- limites de matériau du sol fabriqué (l2/sol_*.npy) entre deux faces visibles de matériaux différents, hors abords
  (non rendus à l'étape 1), hors faces cachées (sous les bordures) et hors coupes de fin de tronçon ;
- contours des marquages (l2b/peinture_*.npy) : arêtes de bord de chaque entité peinte.
Aucune de ces données n'est modifiée.
"""
import json
import math
from pathlib import Path

import numpy as np

PAS = 0.15
TYPES = ("bordure_pied", "bordure_tete", "limite_materiau", "marquage")
COULEURS_CLASSES = {"voie_circulation": (92, 92, 96), "zone_neutralisee": (110, 110, 116), "terre_plein": (150, 140, 120),
                    "trottoir": (190, 186, 176), "piste_cyclable": (70, 74, 90), "bande_plantee": (96, 150, 80),
                    "bande_enherbee": (110, 160, 90), "accotement": (120, 165, 95), "chemin_pieton": (170, 160, 140),
                    "sous_bordure": (210, 210, 210)}


def _polygones(F, C):
    """Arêtes (a, b) de chaque polygone et indice du polygone."""
    off = np.concatenate([[0], np.cumsum(C)[:-1]])
    ea, eb, fi = [], [], []
    for n in np.unique(C):
        sel = np.nonzero(C == n)[0]
        for k in range(int(n)):
            ea.append(F[off[sel] + k])
            eb.append(F[off[sel] + (k + 1) % n])
            fi.append(sel)
    return np.concatenate(ea), np.concatenate(eb), np.concatenate(fi)


def _cles_sommets(P, q=100.0):
    _, vid = np.unique(np.round(P[:, :3] * q).astype(np.int64), axis=0, return_inverse=True)
    return vid.ravel()


def _echantillonner(A, B, pas=PAS):
    """Segments (A, B) (N, 3) -> points et tangentes unitaires, au pas donné (au moins un point par segment)."""
    d = B - A
    L = np.linalg.norm(d, axis=1)
    ok = L > 1e-4
    A, d, L = A[ok], d[ok], L[ok]
    n = np.maximum(1, np.round(L / pas).astype(int))
    rep = np.repeat(np.arange(len(A)), n)
    k = np.concatenate([np.arange(m) for m in n]) if len(n) else np.zeros(0, int)
    f = (k + 0.5) / n[rep]
    P = A[rep] + d[rep] * f[:, None]
    T = d[rep] / L[rep][:, None]
    return P, T


def _eclaircir(P, T, typ, pas=PAS):
    """Un point par cellule de pas/2 et par type (ordre stable) : supprime les suréchantillonnages des petits
    segments (triangulation fine)."""
    q = np.floor(P / (pas * 0.5)).astype(np.int64)
    cle = np.concatenate([q, typ[:, None]], axis=1)
    _, idx = np.unique(cle, axis=0, return_index=True)
    idx = np.sort(idx)
    return P[idx], T[idx], typ[idx]


class Modele:
    def __init__(self, dossier):
        self.dossier = Path(dossier)
        d = self.dossier
        self.voc = json.loads((d / "l2" / "sol_vocabulaire.json").read_text(encoding="utf-8"))
        self.P = np.load(d / "l2" / "sol_points.npy")
        self.F = np.load(d / "l2" / "sol_faces.npy")
        self.C = np.load(d / "l2" / "sol_comptes.npy")
        self.A = np.load(d / "l2" / "sol_attributs.npy")
        self.niveaux = json.loads((d / "l2" / "niveaux.json").read_text(encoding="utf-8"))
        col = {c: i for i, c in enumerate(self.voc["colonnes"])}
        self.col = col
        cls = np.array(self.voc["classe"])[self.A[:, col["classe"]]]
        mat = np.array(self.voc["materiau_id"])[self.A[:, col["materiau_id"]]]
        bid = np.array(self.voc["bande_id"])[self.A[:, col["bande_id"]]]
        vis = self.A[:, col["visible"]] == 1
        self.classe_face, self.mat_face, self.bande_face, self.vis_face = cls, mat, bid, vis
        off = np.concatenate([[0], np.cumsum(self.C)[:-1]])
        self._off = off
        # centroïdes des faces
        cen = np.zeros((len(self.C), 3))
        for n in np.unique(self.C):
            sel = np.nonzero(self.C == n)[0]
            cen[sel] = np.mean([self.P[self.F[off[sel] + k], :3] for k in range(int(n))], axis=0)
        self.centres = cen
        utile = vis & (cls != "abord")
        self.utile = utile
        pu = cen[utile]
        self.s_min, self.s_max = float(pu[:, 0].min()), float(pu[:, 0].max())
        self.t_min, self.t_max = float(pu[:, 1].min()), float(pu[:, 1].max())
        self.longueur = self.s_max - self.s_min
        from scipy.spatial import cKDTree
        self._arbre = cKDTree(cen[utile][:, :2])
        self._idx_utile = np.nonzero(utile)[0]
        self._aretes = None

    # ---------------------------------------------------------------------------------------------- requêtes
    def face_sous(self, x, y):
        _, i = self._arbre.query([x, y])
        return int(self._idx_utile[i])

    def z_sol(self, x, y):
        return float(self.centres[self.face_sous(x, y), 2])

    def bande_sous(self, x, y):
        """(classe, bande_id, distance au centre de face le plus proche) au point (x, y)."""
        d, i = self._arbre.query([x, y])
        f = int(self._idx_utile[i])
        dans = (self.s_min - 0.5 <= x <= self.s_max + 0.5) and (self.t_min - 0.5 <= y <= self.t_max + 0.5) and d < 1.5
        return (str(self.classe_face[f]) if dans else "hors_modele", str(self.bande_face[f]) if dans else "")

    def chaussee(self, pas=1.0):
        """Intervalle en t de la chaussée (voies de circulation) par tranche de s (pas en m) : tableau (N, 3)
        s0, t_min, t_max (NaN si aucune voie)."""
        if getattr(self, "_chaussee", None) is None:
            voie = self.utile & (self.classe_face == "voie_circulation")
            c = self.centres[voie]
            bornes = np.arange(math.floor(self.s_min), math.ceil(self.s_max) + pas, pas)
            out = []
            for a in bornes[:-1]:
                sel = (c[:, 0] >= a) & (c[:, 0] < a + pas)
                out.append((a, c[sel, 1].min() - 0.3, c[sel, 1].max() + 0.3) if sel.any() else (a, np.nan, np.nan))
            self._chaussee = np.array(out)
        return self._chaussee

    def distance_chaussee(self, s, t, marge=0.8):
        """Distance (m) d'un point (s, t) à la chaussée rétrécie de `marge` (0 dedans)."""
        ch = self.chaussee()
        i = int(np.clip(np.searchsorted(ch[:, 0], s, side="right") - 1, 0, len(ch) - 1))
        a, lo, hi = ch[i]
        if np.isnan(lo):
            return 0.0
        ds = max(0.0, self.s_min - s, s - self.s_max)
        dt = max(0.0, (lo + marge) - t, t - (hi - marge))
        return float(math.hypot(ds, dt)) if ds > 0 else float(dt)

    def profil(self, s):
        """Profil de la section qui contient s : bandes de gauche (t max) à droite, largeurs mesurées sur le sol."""
        sec = None
        for x in self.niveaux["sections"]:
            if x["s0"] - 1e-6 <= s <= x["s1"] + 1e-6:
                sec = x
                break
        sec = sec or self.niveaux["sections"][0]
        out = []
        prox = np.abs(self.centres[:, 0] - s) < 0.6
        for bid, typ, mat in zip(sec["b_id"], sec["b_type"], sec["b_mat"]):
            sel = prox & (self.bande_face == bid)
            lar = None
            if sel.any():
                ts = self.P[np.unique(self.F[np.concatenate([self._off[np.nonzero(sel)[0]] + k for k in range(3)])]), 1]
                lar = round(float(ts.max() - ts.min()), 2)
            out.append({"bande": bid, "type": typ, "materiau": mat, "largeur_m": lar})
        bord = [{"entre": [sec["b_id"][i - 1] if i > 0 else None, sec["b_id"][i] if i < len(sec["b_id"]) else None],
                 "profil": sec["l_prof"][i], "vue_m": sec["l_vue"][i]}
                for i in range(len(sec["l_bord"])) if sec["l_bord"][i]]
        return {"section": sec["section"], "s0": sec["s0"], "s1": sec["s1"], "bandes": out, "bordures": bord}

    # ---------------------------------------------------------------------------------------------- arêtes
    def aretes(self, pas=PAS):
        """Points (N, 3), tangentes (N, 3), types (N,) des arêtes projetables du modèle."""
        if self._aretes is not None:
            return self._aretes
        Ps, Ts, ty = [], [], []
        # bordures
        for b in self.niveaux.get("bordures", []):
            pts = b["points"]
            if len(pts) < 2:
                continue
            xy = np.array([[p["x"], p["y"]] for p in pts])
            for k, cle in ((0, "pied"), (1, "tete")):
                z = np.array([p[cle] for p in pts])
                Q = np.c_[xy, z]
                P, T = _echantillonner(Q[:-1], Q[1:], pas)
                if b.get("fermee") and len(Q) > 2:
                    P2, T2 = _echantillonner(Q[-1:], Q[:1], pas)
                    P, T = np.concatenate([P, P2]), np.concatenate([T, T2])
                Ps.append(P)
                Ts.append(T)
                ty.append(np.full(len(P), k))
        # limites de matériau du sol
        ea, eb, fi = _polygones(self.F, self.C)
        vid = _cles_sommets(self.P)
        E = np.stack([vid[ea], vid[eb]], 1)
        E.sort(axis=1)
        cle = E[:, 0].astype(np.int64) * (int(vid.max()) + 1) + E[:, 1]
        o = np.argsort(cle, kind="stable")
        ks = cle[o]
        _, idx, cnt = np.unique(ks, return_index=True, return_counts=True)
        deux = idx[cnt == 2]
        f1, f2 = fi[o[deux]], fi[o[deux + 1]]
        ok = (self.vis_face[f1] & self.vis_face[f2] & (self.mat_face[f1] != self.mat_face[f2])
              & (self.classe_face[f1] != "abord") & (self.classe_face[f2] != "abord")
              & (self.mat_face[f1] != "sol_cache") & (self.mat_face[f2] != "sol_cache"))
        ia, ib = ea[o[deux[ok]]], eb[o[deux[ok]]]
        A, B = self.P[ia, :3], self.P[ib, :3]
        fin = ((np.minimum(A[:, 0], B[:, 0]) < self.s_min + 0.2) & (np.abs(A[:, 0] - B[:, 0]) < 1e-3)) | \
              ((np.maximum(A[:, 0], B[:, 0]) > self.s_max - 0.2) & (np.abs(A[:, 0] - B[:, 0]) < 1e-3))
        P, T = _echantillonner(A[~fin], B[~fin], pas)
        Ps.append(P)
        Ts.append(T)
        ty.append(np.full(len(P), 2))
        # marquages
        dp = self.dossier / "l2b"
        if (dp / "peinture_points.npy").exists():
            PP = np.load(dp / "peinture_points.npy")
            FF = np.load(dp / "peinture_faces.npy")
            CC = np.load(dp / "peinture_comptes.npy")
            AA = np.load(dp / "peinture_attributs.npy")
            ea, eb, fi = _polygones(FF, CC)
            vid = _cles_sommets(PP, 200.0)
            E = np.stack([vid[ea], vid[eb]], 1)
            E.sort(axis=1)
            ent = AA[fi, 0].astype(np.int64)
            n = int(vid.max()) + 1
            cle = (ent * n + E[:, 0]) * n + E[:, 1]
            o = np.argsort(cle, kind="stable")
            _, idx, cnt = np.unique(cle[o], return_index=True, return_counts=True)
            un = o[idx[cnt == 1]]
            P, T = _echantillonner(PP[ea[un], :3], PP[eb[un], :3], pas)
            Ps.append(P)
            Ts.append(T)
            ty.append(np.full(len(P), 3))
        P, T, typ = np.concatenate(Ps), np.concatenate(Ts), np.concatenate(ty)
        P, T, typ = _eclaircir(P, T, typ, pas)
        self._aretes = (P, T, typ)
        return self._aretes

    # ---------------------------------------------------------------------------------------------- plan
    def faces_plan(self):
        """Polygones 2D (s, t) des faces utiles et leur classe, pour le plan du site."""
        out = []
        for n in np.unique(self.C):
            sel = np.nonzero(self.C == n)[0]
            sel = sel[self.utile[sel]]
            pts = np.stack([self.P[self.F[self._off[sel] + k], :2] for k in range(int(n))], 1)
            for p, c in zip(pts, self.classe_face[sel]):
                out.append((p, str(c)))
        return out


def resume_aretes(modele):
    P, T, typ = modele.aretes()
    return {TYPES[k]: int((typ == k).sum()) for k in range(len(TYPES))}
