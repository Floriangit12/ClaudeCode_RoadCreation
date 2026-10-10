"""Bibliothèque d'enregistrement des observations ortho_A (scratch). Les fichiers obs_<tuile>.py appellent ob()."""
import json
import math
import sys
from pathlib import Path

ORTHO_A = Path("D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/enrichi/recensement/ortho_A")
sys.path.insert(0, str(ORTHO_A))
import overlay as ov  # noqa: E402

OBS = []
_TUILE = [None]


def tuile(t):
    _TUILE[0] = t


def ob(classe, sous_type, xy, statut, lien=None, attributs=None, conf="moyenne", prec=0.1,
       methode="pixel_ortho", valide=None, raison=None, preuve=False, geom=None, note=None, cote=10.0, tuile=None):
    t = tuile or _TUILE[0]
    a = dict(attributs or {})
    if geom:
        a["geometrie_l93"] = [[round(p[0], 2), round(p[1], 2)] for p in geom]
    if note:
        a["note"] = note
    OBS.append({"tuile": t, "classe": classe, "sous_type": sous_type, "xy": [float(xy[0]), float(xy[1])],
                "statut": statut, "lien": lien, "attributs": a, "conf": conf, "prec": prec, "methode": methode,
                "valide": valide, "raison": raison, "preuve": preuve, "cote": cote})
