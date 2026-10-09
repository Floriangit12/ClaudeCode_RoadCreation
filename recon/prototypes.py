"""Prototypes génériques (volumes provisoires) des objets instanciés de la scène.

Conventions (identiques à assets/CONVENTIONS.md) : mètres, Z vers le haut, FACE AVANT VERS +Y,
pivot au pied pour les supports (mâts, poteaux, arbres, mobilier), au CENTRE pour les têtes de
feux, panonceaux et panneaux (comme recon/out/paquet_jardin/objets/instances.json).
Les dimensions nominales sont celles de instances.json (meta.prototypes) : l'échelle d'instance
[sx, sy, sz] s'applique à ces dimensions (ex. arbre_feuillu 10 m x couronne 6 m, feu_mat 1 m).
NB : instances.json oriente la face selon +X (yaw trigonométrique depuis l'Est) ; l'assemblage
applique donc une rotation (yaw - 90°) à ces prototypes orientés +Y.

Chaque prototype = liste de parties (materiau, trimesh, uv | None). Les faces de panneaux sont
texturées par assets/specs/panneaux/faces/<code>.png quand elles existent (sinon couleur unie).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import trimesh

REPO = Path(__file__).resolve().parents[1]
FACES = REPO / "assets" / "specs" / "panneaux" / "faces"

COULEURS_PROTO = {
    "galva": (0.62, 0.63, 0.64), "gris_feu": (0.25, 0.27, 0.28), "noir_mat": (0.05, 0.05, 0.05),
    "feu_rouge": (0.55, 0.05, 0.04), "feu_orange": (0.60, 0.35, 0.02), "feu_vert": (0.05, 0.45, 0.25),
    "bois": (0.36, 0.27, 0.18), "beton_mobilier": (0.68, 0.67, 0.64), "blanc_panneau": (0.90, 0.90, 0.88),
    "rouge_panneau": (0.70, 0.08, 0.10), "bleu_panneau": (0.05, 0.25, 0.60), "jaune_panneau": (0.95, 0.75, 0.05),
    "vert_mobilier": (0.15, 0.30, 0.22),
}


def _cyl(r, h, z0=0.0, sections=12, x=0.0, y=0.0):
    m = trimesh.creation.cylinder(radius=r, height=h, sections=sections)
    m.apply_translation([x, y, z0 + h / 2])
    return m


def _box(sx, sy, sz, c):
    m = trimesh.creation.box([sx, sy, sz])
    m.apply_translation(c)
    return m


def _ellipsoid(rx, ry, rz, c, sub=2):
    m = trimesh.creation.icosphere(subdivisions=sub, radius=1.0)
    m.apply_scale([rx, ry, rz])
    m.apply_translation(c)
    return m


def _disc_y(r, y, z, n=24):
    """Disque vertical face +Y (lentille de feu)."""
    m = trimesh.creation.cylinder(radius=r, height=0.01, sections=n)
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    m.apply_translation([0, y, z])
    return m


def _shape_outline(forme, w, h):
    """Contour 2D (x, z) centré d'une plaque de panneau."""
    if forme == "disque":
        a = np.linspace(0, 2 * math.pi, 40, endpoint=False)
        return np.c_[np.cos(a) * w / 2, np.sin(a) * w / 2]
    if forme == "triangle_haut":
        hh = w * math.sqrt(3) / 2
        return np.array([[-w / 2, -hh / 3], [w / 2, -hh / 3], [0, 2 * hh / 3]])
    if forme == "triangle_bas":
        hh = w * math.sqrt(3) / 2
        return np.array([[-w / 2, hh / 3], [0, -2 * hh / 3], [w / 2, hh / 3]])
    if forme == "octogone":
        a = np.linspace(0, 2 * math.pi, 8, endpoint=False) + math.pi / 8
        return np.c_[np.cos(a), np.sin(a)] * (w / 2 / math.cos(math.pi / 8))
    return np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]])


def _plaque(forme, w, h, ep=0.02):
    """Face avant (y = 0, normale +Y, UV planaires) + dos et chants (y = -ep)."""
    P = _shape_outline(forme, w, h)
    n = len(P)
    # face avant : éventail (contours convexes)
    Vf = np.c_[P[:, 0], np.zeros(n), P[:, 1]]
    Vf = np.vstack([[0, 0, 0], Vf])
    Ff = np.array([[0, i + 1, (i + 1) % n + 1] for i in range(n)])
    # normale +Y : (x, z) CCW vu depuis +Y -> vérifier l'ordre
    t = trimesh.Trimesh(Vf, Ff, process=False)
    if t.face_normals[:, 1].mean() < 0:
        Ff = Ff[:, ::-1]
        t = trimesh.Trimesh(Vf, Ff, process=False)
    xmin, zmin = P.min(0)
    xmax, zmax = P.max(0)
    uv = np.c_[(Vf[:, 0] - xmin) / (xmax - xmin), (Vf[:, 2] - zmin) / (zmax - zmin)]
    # dos + chants
    Vb = np.vstack([Vf, Vf + [0, -ep, 0]])
    Fb = [[n + 1 + 0, n + 1 + ((i + 1) % n + 1), n + 1 + (i + 1)] for i in range(n)]   # dos (inversé)
    for i in range(n):
        a, b = i + 1, (i + 1) % n + 1
        Fb += [[a, a + n + 1, b + n + 1], [a, b + n + 1, b]]
    back = trimesh.Trimesh(Vb, np.array(Fb), process=False)
    if back.face_normals[: n, 1].mean() > 0:
        back = trimesh.Trimesh(Vb, np.array(Fb)[:, ::-1], process=False)
    return t, uv, back


PANNEAUX = {  # code -> (forme, largeur, hauteur, couleur de repli)
    "B21a1": ("disque", 0.45, 0.45, "bleu_panneau"), "B1": ("disque", 0.65, 0.65, "rouge_panneau"),
    "B2a": ("disque", 0.65, 0.65, "rouge_panneau"), "B2b": ("disque", 0.65, 0.65, "rouge_panneau"),
    "B6a1": ("disque", 0.65, 0.65, "rouge_panneau"), "B14": ("disque", 0.65, 0.65, "rouge_panneau"),
    "AB3a": ("triangle_bas", 0.70, 0.70, "rouge_panneau"), "AB4": ("octogone", 0.70, 0.70, "rouge_panneau"),
    "A17": ("triangle_haut", 1.00, 1.00, "rouge_panneau"), "C113": ("carre", 0.50, 0.50, "bleu_panneau"),
    "C114": ("carre", 0.50, 0.50, "bleu_panneau"), "C13a": ("carre", 0.50, 0.50, "bleu_panneau"),
    "J5": ("rect", 0.30, 0.80, "bleu_panneau"), "D21": ("rect", 1.20, 0.75, "blanc_panneau"),
    "M9": ("rect", 0.50, 0.15, "blanc_panneau"), "M12": ("triangle_bas", 0.35, 0.35, "rouge_panneau"),
    "AB3a_panonceau": ("triangle_bas", 0.35, 0.35, "rouge_panneau"),
}

# hauteur nominale des prototypes « mis à l'échelle en hauteur » (échelle sz x nominal = hauteur réelle)
HAUTEUR_NOMINALE = {
    "arbre_feuillu": 10.0, "arbre_conifere": 12.0, "arbre_jeune_tuteure": 4.5, "arbuste_bosquet": 3.0,
    "souche": 0.4, "feu_mat": 1.0, "poteau_panneau": 1.0, "lampadaire_crosse_simple": 10.0,
    "lampadaire_crosse_double": 10.0, "lampadaire_mat_droit": 6.0, "poteau_reseau": 9.0, "mat_camera": 6.0,
    "poteau_arret_bus": 2.8, "totem_PR": 2.8,
}

GENERIQUES = {  # nom -> (largeur X, profondeur Y, hauteur nominale, materiau, forme)
    "banc": (1.8, 0.6, 1.8, "bois", "box"), "corbeille": (0.5, 0.5, 0.6, "vert_mobilier", "cyl"),
    "stationnement_velos": (2.0, 0.6, 0.8, "galva", "box"), "distributeur": (0.8, 0.6, 1.8, "gris_feu", "box"),
    "conteneur_verre": (1.5, 1.5, 1.8, "vert_mobilier", "box"), "fontaine": (0.6, 0.6, 1.1, "gris_feu", "cyl"),
    "boite_aux_lettres": (0.5, 0.4, 1.3, "jaune_panneau", "box"),
    "panneau_information": (1.2, 0.15, 2.2, "gris_feu", "box"),
    "mobilier_publicitaire": (1.3, 0.25, 2.6, "gris_feu", "box"), "armoire": (1.0, 0.4, 1.4, "gris_feu", "box"),
    "mat_camera": (0.2, 0.2, 6.0, "galva", "cyl"), "poteau_incendie": (0.2, 0.2, 0.9, "rouge_panneau", "cyl"),
    "potelet": (0.1, 0.1, 1.0, "gris_feu", "cyl"), "portail": (3.0, 0.08, 1.6, "galva", "box"),
    "barriere_levante": (0.3, 0.3, 1.1, "blanc_panneau", "box"), "chicane": (2.0, 0.08, 1.1, "galva", "box"),
    "balise_J11": (0.1, 0.1, 1.0, "blanc_panneau", "cyl"),
}


def code_of(proto):
    if proto.startswith("panneau_"):
        return proto[len("panneau_"):]
    if proto.startswith("panonceau_"):
        c = proto[len("panonceau_"):]
        return c if c != "AB3a" else "AB3a_panonceau"
    return None


def face_png(code):
    for c in (code, code.split("_")[0]):
        for f in (FACES / f"{c}.png", FACES / f"{c.lower()}.png"):
            if f.exists():
                return f
    return None


def build(name):
    """Liste de parties (materiau, trimesh, uv|None) du prototype générique « name »."""
    if name == "arbre_feuillu":
        return [("tronc", _cyl(0.25, 4.6, sections=10), None), ("feuillage", _ellipsoid(3, 3, 3.3, [0, 0, 6.7]), None)]
    if name == "arbre_conifere":
        cone = trimesh.creation.cone(radius=2.5, height=10.5, sections=14)
        cone.apply_translation([0, 0, 1.5])
        return [("tronc", _cyl(0.25, 2.0, sections=10), None), ("feuillage", cone, None)]
    if name == "arbre_jeune_tuteure":
        return [("tronc", _cyl(0.06, 2.6, sections=8), None), ("feuillage", _ellipsoid(0.9, 0.9, 1.1, [0, 0, 3.4], 1), None),
                ("bois", _cyl(0.03, 1.8, x=0.25, sections=6), None), ("bois", _cyl(0.03, 1.8, x=-0.25, sections=6), None)]
    if name == "arbuste_bosquet":
        return [("feuillage", _ellipsoid(1.25, 1.25, 1.45, [0, 0, 1.5], 1), None)]
    if name == "souche":
        return [("tronc", _cyl(0.3, 0.4, sections=10), None)]
    if name in ("feu_mat", "poteau_panneau"):
        return [("gris_feu" if name == "feu_mat" else "galva", _cyl(0.038 if name == "feu_mat" else 0.03, 1.0, sections=10), None)]
    if name.startswith("feu_tete_"):
        typ = name[len("feu_tete_"):]
        w, h, d, lentilles = {"R11v": (0.30, 0.95, 0.25, ["feu_rouge", "feu_orange", "feu_vert"]),
                              "R11v_rep": (0.15, 0.45, 0.20, ["feu_rouge", "feu_orange", "feu_vert"]),
                              "R12": (0.30, 0.65, 0.25, ["feu_rouge", "feu_vert"]),
                              "R13c": (0.15, 0.45, 0.20, ["feu_rouge", "feu_orange", "feu_vert"])}.get(typ, (0.3, 0.95, 0.25, ["feu_rouge", "feu_orange", "feu_vert"]))
        parts = [("noir_mat", _box(w, d, h, [0, 0, 0]), None)]           # pivot = centre du boîtier
        n = len(lentilles)
        for i, m in enumerate(lentilles):
            z = h / 2 - h * (i + 0.5) / n
            parts.append((m, _disc_y(min(w, h / n) * 0.36, d / 2 + 0.006, z), None))
        return parts
    if name.startswith("lampadaire_"):
        H = HAUTEUR_NOMINALE[name]
        parts = [("galva", _cyl(0.08 if H > 7 else 0.06, H, sections=10), None)]
        if name == "lampadaire_mat_droit":
            parts.append(("verre", _cyl(0.22, 0.5, z0=H - 0.2), None))
        else:
            for s in ((1,) if name == "lampadaire_crosse_simple" else (1, -1)):
                parts.append(("galva", _box(0.08, 1.5, 0.08, [0, s * 0.75, H - 0.05]), None))
                parts.append(("verre", _box(0.30, 0.55, 0.12, [0, s * 1.45, H - 0.15]), None))
        return parts
    if name.startswith("abri_bus"):
        return [("verre", _box(4.0, 0.03, 2.25, [0, -0.73, 1.15]), None), ("galva", _box(4.2, 1.6, 0.10, [0, 0, 2.45]), None),
                ("verre", _box(0.03, 1.2, 2.25, [-2.0, -0.15, 1.15]), None), ("verre", _box(0.03, 1.2, 2.25, [2.0, -0.15, 1.15]), None),
                ("galva", _box(0.05, 0.05, 2.4, [-2.05, -0.73, 1.2]), None), ("galva", _box(0.05, 0.05, 2.4, [2.05, -0.73, 1.2]), None),
                ("bois", _box(2.0, 0.4, 0.05, [0, -0.45, 0.45]), None), ("blanc_panneau", _box(1.25, 0.08, 1.8, [1.4, -0.68, 1.2]), None)]
    if name == "poteau_arret_bus":
        return [("galva", _cyl(0.04, 2.8, sections=10), None), ("blanc_panneau", _box(0.03, 0.5, 0.6, [0, 0.27, 2.45]), None)]
    if name == "totem_PR":
        return [("bleu_panneau", _box(0.6, 0.25, 2.8, [0, 0, 1.4]), None)]
    if name == "poteau_reseau":
        return [("bois", _cyl(0.125, 9.0, sections=10), None)]
    code = code_of(name)
    if code:
        forme, w, h, coul = PANNEAUX.get(code, PANNEAUX.get(code.split("_")[0], ("carre", 0.6, 0.6, "blanc_panneau")))
        front, uv, back = _plaque(forme, w, h)
        png = face_png(code)
        return [((f"face_{png.stem}" if png else coul), front, uv if png else None), ("galva", back, None)]
    if name in GENERIQUES:
        sx, sy, H, mat, forme = GENERIQUES[name]
        geo = _cyl(max(sx, sy) / 2, H, sections=12) if forme == "cyl" else _box(sx, sy, H, [0, 0, H / 2])
        return [(mat, geo, None)]
    return [("gris_feu", _box(0.4, 0.4, 1.0, [0, 0, 0.5]), None)]


def materiaux_utilises(parts_by_proto):
    return sorted({m for parts in parts_by_proto.values() for m, _, _ in parts})
