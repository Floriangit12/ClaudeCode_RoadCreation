"""Journal de la résolution et outils de contexte (classe de surface, bordure la plus proche).

Le journal garde deux listes déterministes :
- appliquees : chaque modification de la description (avant, après, observations, règles, revue, confiance) ;
- non_resolues : propositions rejetées, conflits et incertitudes laissés tels que la base, avec la station terrain.
"""
import collections

import numpy as np

from commun import anneaux, arrondi, distance_segments, dans_polygone, repere
from resoudre_regles import station_pour


class Journal:
    def __init__(self):
        self.appliquees = []
        self.non_resolues = []
        self._cles = set()

    def appliquer(self, ident, famille, nature, *, avant, apres, regles, observations=(), revue=None, conf="moyenne",
                  motif="", xy_avant=None, xy_apres=None, portee=0.0, classe=None, extra=None):
        e = {"id": ident, "famille": famille, "classe": classe, "nature": nature, "avant": arrondi(avant),
             "apres": arrondi(apres), "regles": sorted(set(regles)), "observations": sorted(set(observations)),
             "revue": revue, "conf": conf, "motif": motif,
             "xy_avant_local": arrondi(list(xy_avant), 3) if xy_avant is not None else None,
             "xy_apres_local": arrondi(list(xy_apres), 3) if xy_apres is not None else None,
             "portee": round(float(portee), 3)}
        if extra:
            e.update(arrondi(extra))
        self.appliquees.append(e)
        return e

    def non_resolu(self, ident, famille, nature, *, motif, origine, regles=(), observations=(), revue=None, xy=None,
                   proposition=None, classe=None, station=None):
        cle = (ident, nature)
        if cle in self._cles:
            return None
        self._cles.add(cle)
        st = station or station_pour(xy)
        e = {"id": ident, "famille": famille, "classe": classe, "nature": nature, "origine": origine, "motif": motif,
             "regles": sorted(set(regles)), "observations": sorted(set(observations)), "revue": revue,
             "proposition": arrondi(proposition) if proposition is not None else None,
             "xy_local": arrondi(list(xy), 3) if xy is not None else None, "station": st}
        self.non_resolues.append(e)
        return e

    def trier(self):
        self.appliquees.sort(key=lambda e: (e["famille"], e["id"], e["nature"]))
        self.non_resolues.sort(key=lambda e: (e["famille"], e["id"], e["nature"]))

    def comptes(self):
        a = collections.Counter((e["famille"], e["nature"]) for e in self.appliquees)
        n = collections.Counter((e["famille"], e["origine"]) for e in self.non_resolues)
        st = collections.Counter((e["station"] or {}).get("station") or "aucune" for e in self.non_resolues)
        return {"appliquees_par_famille_nature": {f"{k[0]} / {k[1]}": v for k, v in sorted(a.items())},
                "appliquees": len(self.appliquees),
                "non_resolues_par_famille_origine": {f"{k[0]} / {k[1]}": v for k, v in sorted(n.items())},
                "non_resolues": len(self.non_resolues),
                "non_resolues_par_station": dict(sorted(st.items(), key=lambda kv: (-kv[1], kv[0])))}


class Contexte:
    """Classe de surface v2 et bordure levée la plus proche en un point local."""

    def __init__(self, surfaces, bordures):
        self.polys = []
        for f in surfaces:
            for poly in anneaux(f["geometry"]):
                P = [repere(r) for r in poly]
                lo, hi = P[0].min(axis=0), P[0].max(axis=0)
                self.polys.append((f["properties"]["id"], f["properties"]["classe"], lo, hi, P))
        A, B, ids, gam = [], [], [], []
        for f in bordures:
            P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
            A.append(P[:-1])
            B.append(P[1:])
            ids += [f["properties"]["id"]] * (len(P) - 1)
            gam += [str((f["properties"].get("prov") or {}).get("geometrie", {}).get("src", "")) == "gam"] * (len(P) - 1)
        self.KA, self.KB = np.vstack(A), np.vstack(B)
        self.kid = np.array(ids)
        self.kgam = np.array(gam, bool)

    def surface(self, xy):
        q = np.asarray([xy], float)
        for sid, cl, lo, hi, P in self.polys:
            if lo[0] <= xy[0] <= hi[0] and lo[1] <= xy[1] <= hi[1] and dans_polygone(q, P)[0]:
                return sid, cl
        return None, None

    def classes(self, Q):
        """Classe de surface de chaque point (None hors surfaces)."""
        Q = np.asarray(Q, float)
        out = np.array([None] * len(Q), dtype=object)
        for sid, cl, lo, hi, P in self.polys:
            sel = (Q[:, 0] >= lo[0]) & (Q[:, 0] <= hi[0]) & (Q[:, 1] >= lo[1]) & (Q[:, 1] <= hi[1]) & (out == None)  # noqa: E711
            if sel.any():
                m = dans_polygone(Q[sel], P)
                idx = np.where(sel)[0][m]
                out[idx] = cl
        return out

    def bordure_gam(self, xy):
        m = self.kgam
        if not m.any():
            return None, None
        d, j, _ = distance_segments(np.asarray([xy], float), self.KA[m], self.KB[m])
        return str(self.kid[m][j[0]]), float(d[0])
