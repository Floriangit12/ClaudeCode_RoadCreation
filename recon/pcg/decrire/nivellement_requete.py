"""Requête du modèle de nivellement v2 (TQ-SOL-013) : z(x, y, surface_id). Python + numpy seuls,
aucune dépendance au reste de `decrire/` : à copier ou importer tel quel dans hython (Houdini 22) ou
dans le Python de l'éditeur UE.

    from nivellement_requete import Nivellement
    niv = Nivellement("recon/out/paquet_jardin/v2/description/base")   # nivellement.json + _grille.npz
    z = niv.z(x, y, "S-0213a")             # z LOCAL (m) ; tableaux acceptés ; NaN hors modèle
    z = niv.z(x, y)                        # sans surface : région propriétaire de chaque point
    zb = niv.z_bordure("K-0385", s)        # pied (fil d'eau / pied de face), tête et arête arrière

Grille : nœuds (x0 + i·pas, y0 + j·pas), i, j = 0..n-1, pas 0,10 m, ligne j = y croissant.
Couches : z0 / r0 = région propriétaire du nœud ; z1 / r1 et z2 / r2 = valeurs prolongées (2 nœuds au plus)
des régions voisines (de l'autre côté d'une arête arrière de bordure, d'un bâtiment...). Une surface
appartient à une région de nivellement (surfaces[].region) ; la requête n'interpole qu'entre des valeurs
de SA région : aucune marche de bordure n'est jamais lissée par l'interpolation.
Z local = NGF − 216,30.
"""
import json
from pathlib import Path

import numpy as np


class Nivellement:
    def __init__(self, dossier):
        d = Path(dossier)
        self.meta = json.loads((d / "nivellement.json").read_text(encoding="utf-8"))
        g = np.load(d / "nivellement_grille.npz")
        self.x0, self.y0, self.pas = float(g["x0"]), float(g["y0"]), float(g["pas"])
        self.z_c = [g["z0"], g["z1"], g["z2"]]
        self.r_c = [g["r0"], g["r1"], g["r2"]]
        self.n = self.z_c[0].shape
        self.region = {s["id"]: s["region"] for s in self.meta["surfaces"]}
        self.bordures = {b["id"]: b for b in self.meta["bordures"]}

    def _valeurs(self, j, i, reg):
        """Valeur au nœud (j, i) pour la région reg (NaN si absente)."""
        out = np.full(len(j), np.nan, dtype=np.float64)
        ok = (j >= 0) & (j < self.n[0]) & (i >= 0) & (i < self.n[1])
        jj, ii = np.where(ok, j, 0), np.where(ok, i, 0)
        for zc, rc in zip(self.z_c, self.r_c):
            m = ok & np.isnan(out) & (rc[jj, ii] == reg)
            out[m] = zc[jj[m], ii[m]]
        return out

    def z(self, x, y, surface_id=None):
        x = np.atleast_1d(np.asarray(x, dtype=np.float64))
        y = np.atleast_1d(np.asarray(y, dtype=np.float64))
        fi = (x - self.x0) / self.pas
        fj = (y - self.y0) / self.pas
        i0, j0 = np.floor(fi).astype(int), np.floor(fj).astype(int)
        ti, tj = fi - i0, fj - j0
        if surface_id is None:
            jn = np.clip(np.rint(fj).astype(int), 0, self.n[0] - 1)
            inn = np.clip(np.rint(fi).astype(int), 0, self.n[1] - 1)
            reg = self.r_c[0][jn, inn]
        else:
            reg = np.full(len(x), self.region[surface_id])
        num = np.zeros(len(x))
        den = np.zeros(len(x))
        for dj, di, w in ((0, 0, (1 - ti) * (1 - tj)), (0, 1, ti * (1 - tj)), (1, 0, (1 - ti) * tj), (1, 1, ti * tj)):
            v = self._valeurs(j0 + dj, i0 + di, reg)
            ok = np.isfinite(v)
            num[ok] += w[ok] * v[ok]
            den[ok] += w[ok]
        out = np.where(den > 1e-9, num / np.maximum(den, 1e-12), np.nan)
        return out

    def z_bordure(self, bordure_id, s):
        """(z_pied, z_tete, z_arriere) locaux de la bordure aux abscisses s (description, m)."""
        b = self.bordures[bordure_id]
        s = np.atleast_1d(np.asarray(s, dtype=np.float64))
        S = np.asarray(b["s"])
        return (np.interp(s, S, b["z_pied"]), np.interp(s, S, b["z_tete"]), np.interp(s, S, b["z_arriere"]))
