"""Priorité des sources des marquages (état octobre 2026) : ordre, admissibilité par zone, scores et décision.

Règles appliquées (assets/specs/regles_conception.json) :
- FUS-SRC-001 : ordre de priorité par attribut (existence, géométrie, type) :
    1. gam        levé vectoriel GAM 2026 (Meylan_Topo.dwg, SOL_SIGNALISATION_HORIZONTALE lin + pct) : fait foi pour
                  l'état 2026 là où il existe (r = 0,95) ;
    2. plan2025   détection sur le raster du plan projet 2025 calé (glyphes CAO), seulement dans la zone des
                  travaux 2025 et pour ce que le GAM n'a pas (r = 0,85 ; projet, ± 0,30 m) ;
    3. ortho2022  détection sur l'ortho PCRS 5 cm 2022, seulement HORS des zones refaites ou construites après
                  2022 (r = 0,80 ; zone « refait à l'identique » : v_temporelle 0,8) ;
    4. regle:<ID> inférence par une règle « deduire_si_absent » (score de la confiance de la règle : haute 0,7,
                  moyenne 0,5, faible 0,3), seulement si l'élément manque après fusion des observations ;
    5. v1         paquet v1 : indice sémantique seulement (existence, type, couleur, usure) ; jamais une géométrie ;
                  une marque v1 non confirmée par une source 1-3 n'est posée que si une règle l'exige.
- FUS-SCO-002 : S = r_source × c_detection × v_temporelle ; P = 1 − Π(1 − S_i) ; P ≥ 0,5 posé, 0,3 ≤ P < 0,5 posé
  « a_verifier », P < 0,3 rejeté (sauf règle deduire_si_absent, posé avec la confiance de la règle).
- Zones (zone de travaux, admissibilité FUS-SRC-001) : raster local de 0,25 m :
    neuf_2025               aire dessinée du plan projet 2025 (calques CAO colorés, dilatés de 3 m puis fermés), surfaces
                            v1 « modifie_2025 », marques v1 de zone « refait_2025 » (dilatées de 2 m) ;
    construit_2023_2024     surfaces v1 « construit_2023_2024 » (l'ortho 2022 ne les montre pas) ;
    refait_2025_identique   marques v1 de zone « resurface_2025 » (dilatées de 2 m) hors des deux précédentes ;
    conserve                ailleurs.
  L'état v1 des surfaces et des marques sert ici d'indice sémantique de zone (aucune géométrie de marque v1 posée).
"""
import functools
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import DONNEES, anneaux, lire_geojson, repere  # noqa: E402

SOURCES = {
    "gam": {"rang": 1, "r": 0.95, "libelle": "levé vectoriel GAM 2026 (Meylan_Topo.dwg)"},
    "plan2025": {"rang": 2, "r": 0.85, "libelle": "détection sur le plan projet 2025 calé (zone des travaux)"},
    "ortho2022": {"rang": 3, "r": 0.80, "libelle": "détection sur l'ortho PCRS 5 cm 2022 (zones conservées)"},
    "regle": {"rang": 4, "r": None, "libelle": "inférence par règle deduire_si_absent (regles_conception)"},
    "v1": {"rang": 5, "r": 0.30, "libelle": "paquet v1 : indice sémantique (jamais une géométrie)"},
}
CONFIANCE_REGLE = {"haute": 0.7, "moyenne": 0.5, "faible": 0.3}          # fusion_detection_inference.confiance_regle_score
SEUIL_POSE, SEUIL_A_VERIFIER = 0.5, 0.3                                 # FUS-SCO-002
ETATS = ("conserve", "refait_2025_identique", "neuf_2025", "construit_2023_2024")
# v_temporelle par (source, état de zone) : 0 = source inadmissible (FUS-SRC-001)
V_TEMPORELLE = {
    "gam": {"conserve": 1.0, "refait_2025_identique": 1.0, "neuf_2025": 1.0, "construit_2023_2024": 1.0},
    "plan2025": {"conserve": 0.0, "refait_2025_identique": 1.0, "neuf_2025": 1.0, "construit_2023_2024": 0.0},
    "ortho2022": {"conserve": 1.0, "refait_2025_identique": 0.8, "neuf_2025": 0.0, "construit_2023_2024": 0.0},
    "v1": {"conserve": 1.0, "refait_2025_identique": 1.0, "neuf_2025": 1.0, "construit_2023_2024": 1.0},
}
RES_ZONE = 0.25
EMPRISE = (-152.0, -152.0, 152.0, 152.0)


def src_base(src):
    return "regle" if src.startswith("regle:") else src


def rang(src):
    return SOURCES[src_base(src)]["rang"]


def score(src, c_detection=1.0, etat="conserve", confiance_regle=None):
    """FUS-SCO-002 : S = r_source × c_detection × v_temporelle (règle : score de sa confiance)."""
    b = src_base(src)
    if b == "regle":
        return CONFIANCE_REGLE.get(confiance_regle or "moyenne", 0.5)
    return SOURCES[b]["r"] * float(c_detection) * V_TEMPORELLE[b].get(etat, 0.0)


def existence(scores):
    """FUS-SCO-002 : P = 1 − Π(1 − S_i)."""
    p = 1.0
    for s in scores:
        p *= (1.0 - max(0.0, min(1.0, s)))
    return 1.0 - p


def decision(P, regle_exige=False):
    """-> (statut pose | a_verifier | rejete, étiquette)."""
    if P >= SEUIL_POSE:
        return "pose", None
    if P >= SEUIL_A_VERIFIER:
        return "pose", "a_verifier"
    return ("pose", "a_verifier") if regle_exige else ("rejete", None)


def confiance_de(P):
    return "haute" if P >= 0.8 else "moyenne" if P >= 0.5 else "faible"


# --------------------------------------------------------------------------- zones de travaux
def _poly_raster(dessin, polys, x0, y1, res, val):
    for poly in polys:
        for k, r in enumerate(poly):
            if len(r) >= 3:
                dessin.polygon([((x - x0) / res, (y1 - y) / res) for x, y in r], fill=val if k == 0 else 0)


@functools.lru_cache(maxsize=None)
def zones():
    """Raster des états de zone : dict {code (H, W) uint8 (indice dans ETATS), x0, y1, res}."""
    from PIL import Image, ImageDraw, ImageFilter
    import detection_commun as D
    x0, y0, x1, y1 = EMPRISE
    res = RES_ZONE
    Q, H, W = D.grille(x0, y0, x1, y1, res)
    cad = np.nan_to_num(D.plan_cad(Q)).reshape(H, W) > 0.5
    m = Image.fromarray((cad * 255).astype(np.uint8))
    k = int(round(3.0 / res)) | 1
    m = D._filtre_rep(m, ImageFilter.MaxFilter, k)
    m = D._filtre_rep(D._filtre_rep(m, ImageFilter.MaxFilter, k), ImageFilter.MinFilter, k)
    neuf = np.asarray(m) > 0
    im_n = Image.new("L", (W, H), 0)
    im_c = Image.new("L", (W, H), 0)
    im_r = Image.new("L", (W, H), 0)
    dn, dc, dr = ImageDraw.Draw(im_n), ImageDraw.Draw(im_c), ImageDraw.Draw(im_r)
    for f in sorted(lire_geojson(DONNEES / "surfaces/surfaces_2026.geojson"), key=lambda f: f["properties"]["id"]):
        e = f["properties"].get("etat")
        polys = [[repere(r) for r in poly] for poly in anneaux(f["geometry"])]
        if e == "modifie_2025":
            _poly_raster(dn, polys, x0, y1, res, 255)
        elif e == "construit_2023_2024":
            _poly_raster(dc, polys, x0, y1, res, 255)
    im_n2 = Image.new("L", (W, H), 0)
    dn2 = ImageDraw.Draw(im_n2)
    for f in sorted(lire_geojson(DONNEES / "marquages/marquages_2026.geojson"), key=lambda f: f["properties"]["id"]):
        z = f["properties"].get("zone")
        polys = [[repere(r) for r in poly] for poly in anneaux(f["geometry"])]
        if z == "refait_2025":
            _poly_raster(dn2, polys, x0, y1, res, 255)
        elif z == "resurface_2025":
            _poly_raster(dr, polys, x0, y1, res, 255)
    k2 = int(round(2.0 / res)) | 1
    neuf |= np.asarray(im_n) > 0
    neuf |= np.asarray(D._filtre_rep(im_n2, ImageFilter.MaxFilter, 2 * k2 - 1)) > 0
    constr = (np.asarray(im_c) > 0) & ~neuf
    refait = (np.asarray(D._filtre_rep(im_r, ImageFilter.MaxFilter, 2 * k2 - 1)) > 0) & ~neuf & ~constr
    code = np.zeros((H, W), np.uint8)
    code[refait] = 1
    code[neuf] = 2
    code[constr] = 3
    return {"code": code, "x0": x0, "y1": y1, "res": res, "H": H, "W": W}


def etat_zone(Q):
    """États de zone (ETATS) aux points locaux Q : tableau de str."""
    z = zones()
    Q = np.atleast_2d(np.asarray(Q, float))
    c = np.clip(((Q[:, 0] - z["x0"]) / z["res"]).astype(int), 0, z["W"] - 1)
    r = np.clip(((z["y1"] - Q[:, 1]) / z["res"]).astype(int), 0, z["H"] - 1)
    return np.array(ETATS, dtype=object)[z["code"][r, c]]


def etat_majoritaire(Q):
    e = list(etat_zone(Q))
    # en cas d'égalité, l'état le plus récent l'emporte (ordre de ETATS inversé)
    return max(ETATS, key=lambda k: (e.count(k), ETATS.index(k)))


def admissible(src, etat):
    b = src_base(src)
    return b == "regle" or V_TEMPORELLE[b].get(etat, 0.0) > 0.0


def doc():
    """Texte de la priorité des sources (rapport, manifeste)."""
    return {"ordre": [{"src": k, "rang": v["rang"], "r_source": v["r"], "libelle": v["libelle"]} for k, v in SOURCES.items()],
            "v_temporelle": V_TEMPORELLE, "decision": {"pose": SEUIL_POSE, "a_verifier": SEUIL_A_VERIFIER},
            "regles": ["FUS-SRC-001", "FUS-SCO-002", "FUS-ASS-003", "FUS-SNP-004", "FUS-CON-005"]}


def angle_diff(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def cap_de(u):
    return math.degrees(math.atan2(u[1], u[0])) % 360.0
