"""Saisie de la revue visuelle des dalles ortho 2022 (agent VISION-ORTHO-B).

Une entrée par observation, rangée par dalle dans saisie/<dalle>.py, dans l'ordre de la revue
(ORDRE ; les identifiants ORTHO-B-<n> suivent cet ordre : n'ajouter qu'en fin de fichier et en fin
de liste). Coordonnées (u, v) en pixels de dalle (5 cm), lues sur les vues 2x de overlay.py.
Champs : t dalle, c classe, st sous-type, s statut, k confiance, l lien description,
a attributs, n note, p précision (m), af affinage ("sombre" | "clair"), r rayon d'affinage (px),
va (valeur, raison) imposée pour valide_2026, bb bbox (u0, v0, u1, v1), geom polyligne en
pixels, pr vignette forcée, vt taille de vignette.
"""
from pathlib import Path

OBS = []
ICI = Path(__file__).resolve().parent

ORDRE = ["917250_6460300", "917300_6460250", "917200_6460250", "917250_6460200", "917300_6460350",
         "917200_6460350", "917300_6460150", "917200_6460150", "917350_6460300", "917150_6460200",
         "917350_6460200", "917150_6460300", "917250_6460400", "917250_6460100", "917350_6460400",
         "917150_6460400", "917400_6460250", "917400_6460350", "917400_6460150", "917350_6460100",
         "917150_6460100", "917100_6460150", "917100_6460250", "917100_6460350"]


def o(t, u, v, c, st, s, k="moyenne", l=None, n=None, **kw):
    e = dict(t=t, u=u, v=v, c=c, st=st, s=s, k=k, l=l, n=n)
    a = kw.pop("a", {})
    e.update(kw)
    e["a"] = a
    OBS.append(e)


for _t in ORDRE:
    _f = ICI / "saisie" / f"{_t}.py"
    if _f.exists():
        exec(compile(_f.read_text(encoding="utf-8"), str(_f), "exec"), {"o": o, "T": _t})
