"""Outils d'enregistrement des observations de l'agent VISION-PANORAMAX-1.

- masque des zones modifiées (travaux 2025 / construit 2023-2024) pour décider `valide_2026` ;
- `obs(...)` : construit une observation au format du recensement (positions local + L93) ;
- journal JSONL (une observation par ligne) puis `finaliser()` -> obs_pano_1.json.
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

RACINE = Path("D:/ClaudeCode_RoadCreation")
ICI = Path(__file__).resolve().parent
O = (917279.43, 6460289.98, 216.30)
JOURNAL = ICI / "journal_obs.jsonl"
SORTIE = ICI.parent / "obs_pano_1.json"
AGENT = "VISION-PANORAMAX-1"

# grille locale du masque
X0, Y0, PAS, N = -260.0, -260.0, 0.25, 2080


def _lire(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _poly_px(r):
    a = np.asarray(r, dtype=np.float64)[:, :2] - np.array(O[:2])
    return [((x - X0) / PAS, (Y0 + N * PAS - y) / PAS) for x, y in a]


def _anneaux(g):
    if g["type"] == "Polygon":
        return [g["coordinates"][0]]
    if g["type"] == "MultiPolygon":
        return [p[0] for p in g["coordinates"]]
    return []


_M = {}


def masques():
    """{'travaux_2025': bool (N,N), 'construit_2023_2024': bool (N,N)} (lignes = y décroissant)."""
    if _M:
        return _M
    tr = Image.new("L", (N, N), 0)
    co = Image.new("L", (N, N), 0)
    dt, dc = ImageDraw.Draw(tr), ImageDraw.Draw(co)
    S = _lire(RACINE / "recon/out/paquet_jardin/package/donnees/surfaces/surfaces_2026.geojson")["features"]
    for f in S:
        e = f["properties"].get("etat")
        for r in _anneaux(f["geometry"]):
            if e == "modifie_2025":
                dt.polygon(_poly_px(r), fill=255)
            elif e == "construit_2023_2024":
                dc.polygon(_poly_px(r), fill=255)
    Z = _lire(RACINE / "recon/out/paquet_jardin/package/donnees/relief/relief_zones_2026.geojson")["features"]
    for f in Z:
        if f["properties"]["zone"] in ("ancienne_chaussee_rehaussee_2025", "traversee_bordure_abaissee",
                                       "ancienne_chaussee_trottoir_par_defaut"):
            for r in _anneaux(f["geometry"]):
                dt.polygon(_poly_px(r), fill=255)
    # marquages neufs 2025 / fantômes (bande de 1 m)
    M = _lire(RACINE / "recon/out/paquet_jardin/v2/description/base/marquages.geojson")["features"]
    for f in M:
        if f["properties"].get("etat") in ("neuf_2025", "fantome"):
            g = f["geometry"]
            rings = _anneaux(g) or ([g["coordinates"]] if g["type"] == "LineString" else
                                    (list(g["coordinates"]) if g["type"] == "MultiLineString" else []))
            for r in rings:
                dt.line(_poly_px(r), fill=255, width=int(2.0 / PAS))
    # bordures zone_travaux_2025
    B = _lire(RACINE / "recon/out/paquet_jardin/v2/description/base/bordures.geojson")["features"]
    for f in B:
        if f["properties"].get("zone_travaux_2025"):
            dt.line(_poly_px(f["geometry"]["coordinates"]), fill=255, width=int(2.0 / PAS))
    _M["travaux_2025"] = np.asarray(tr) > 0
    _M["construit_2023_2024"] = np.asarray(co) > 0
    return _M


def zone(xy_local, rayon=0.0):
    """Zones modifiées au point local (x, y) (rayon de tolérance en m) : liste de noms."""
    x, y = xy_local[:2]
    i = int((x - X0) / PAS)
    j = int((Y0 + N * PAS - y) / PAS)
    r = int(math.ceil(rayon / PAS))
    out = []
    for nom, m in masques().items():
        if 0 <= i < N and 0 <= j < N and m[max(0, j - r):j + r + 1, max(0, i - r):i + r + 1].any():
            out.append(nom)
    return out


SOL = {"bordure", "surface", "ilot", "marquage", "tampon", "avaloir", "bev", "massif"}


def validite(classe, xy_local, date_image, etat_entite=None):
    """(valide_2026, raison) selon la date de l'image, l'état déclaré de l'entité liée et les zones modifiées."""
    if date_image >= "2025-11-30":
        return True, "image postérieure aux travaux 2025"
    if etat_entite in ("neuf_2025", "planté 2025 (projet)", "2026 confirmé", "déduit 2026 (à vérifier)"):
        return False, f"élément posé ou refait en 2025 ({etat_entite}) : image du {date_image} antérieure"
    if etat_entite == "fantome":
        return False, "marquage effacé en 2025 (fantôme) : l'image montre l'état avant travaux"
    if etat_entite in ("absent 2026",):
        return False, "élément déclaré absent en 2026"
    if etat_entite == "refait_2025_identique":
        return "incertain", "marquage refait à l'identique en 2025 : géométrie valable, usure/état non"
    z = zone(xy_local, rayon=1.0) if xy_local is not None else []
    if "construit_2023_2024" in z and date_image < "2024-06-01":
        return False, f"zone construite en 2023-2024, image du {date_image} antérieure"
    if etat_entite in ("conserve", "existant (inchangé)", "inchange_2022", "existant"):
        if "travaux_2025" in z:
            return True, (f"élément déclaré conservé ({etat_entite}) mais dans/près de l'emprise des travaux 2025 :"
                          f" à recouper ; image du {date_image}")
        return True, f"élément conservé ({etat_entite}), hors emprise des travaux 2025 ; image du {date_image}"
    if xy_local is None:
        return "incertain", "position inconnue"
    if "travaux_2025" in z:
        if classe in SOL or classe in ("potelet", "mobilier", "abri_bus", "panneau", "feu", "cloture"):
            return False, f"dans l'emprise modifiée par les travaux 2025 ; image du {date_image}"
        return "incertain", f"dans l'emprise des travaux 2025 (élément vertical peut-être conservé) ; image du {date_image}"
    if classe == "arbre":
        return True, f"hors emprise des travaux 2025 ; arbre (croissance possible depuis {date_image[:4]})"
    return True, f"hors emprise des travaux 2025 ; élément inchangé présumé ({date_image})"


def l93(P):
    return [round(P[0] + O[0], 3), round(P[1] + O[1], 3)]


def obs(source, date_image, classe, sous_type, attributs, P_local=None, precision_m=None, methode=None,
        lien=None, statut="confirme", confiance="moyenne", preuve=None, etat_entite=None, valide=None):
    """Construit une observation (sans id). P_local : (x, y[, z]) local."""
    pos = None
    if P_local is not None:
        P = [float(v) for v in P_local]
        pos = dict(local=[round(v, 3) for v in P], l93=l93(P), precision_m=precision_m, methode=methode)
    if valide is None:
        v, r = validite(classe, P_local, date_image[:10], etat_entite)
    else:
        v, r = valide
    return dict(source=source, date_image=date_image, classe=classe, sous_type=sous_type, attributs=attributs,
                position=pos, lien_description=lien, statut=statut,
                valide_2026=dict(valeur=v, raison=r), confiance=confiance, preuve=preuve or {})


JOURNAUX = ICI / "journal"


def ajouter(cle, *observations):
    """Écrit (remplace) le journal de la photo/clé : journal/<cle>.json."""
    JOURNAUX.mkdir(exist_ok=True)
    with open(JOURNAUX / f"{cle}.json", "w", encoding="utf-8") as f:
        json.dump(list(observations), f, ensure_ascii=False, indent=1)
    return len(observations)


def finaliser(ordre=None):
    """Fusionne journal/*.json (dans l'ordre donné, sinon alphabétique) -> obs_pano_1.json avec ids stables."""
    fichiers = sorted(JOURNAUX.glob("*.json"))
    if ordre:
        rang = {k: i for i, k in enumerate(ordre)}
        fichiers.sort(key=lambda f: (rang.get(f.stem, 10 ** 6), f.stem))
    out = []
    for fch in fichiers:
        for o in json.load(open(fch, encoding="utf-8")):
            out.append({"id": f"{AGENT}-{len(out) + 1}", **o})
    with open(SORTIE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return len(out)


# --------------------------------------------------------------------------- accès aux entités
_IDX = {}


def index():
    """{id: (famille, propriétés, xy local)} pour mobilier, arbres, marquages, bordures, îlots, surfaces."""
    if _IDX:
        return _IDX
    OBJ = RACINE / "recon/out/paquet_jardin/package/donnees/objets"
    for f, fam in (("mobilier.geojson", "mobilier"), ("arbres.geojson", "arbre")):
        for ft in _lire(OBJ / f)["features"]:
            p = ft["properties"]
            xy = (p.get("x_local"), p.get("y_local"))
            _IDX[p["id"]] = (fam, p, xy)
    B = RACINE / "recon/out/paquet_jardin/v2/description/base"
    for f in ("marquages", "bordures", "ilots", "surfaces", "ponctuels_sol"):
        for ft in _lire(B / f"{f}.geojson")["features"]:
            p = ft["properties"]
            _IDX[p["id"]] = (f, p, None)
    return _IDX


def etat(eid):
    fam, p, _ = index()[eid]
    if fam in ("mobilier", "arbre"):
        return p.get("statut_2026")
    if fam == "marquages":
        return p.get("etat")
    if fam == "bordures":
        return "existant" if not p.get("zone_travaux_2025") else None
    if fam == "surfaces":
        return {"inchange_2022": "inchange_2022"}.get(p.get("etat_v1"))
    return None


def pos(eid):
    fam, p, xy = index()[eid]
    if xy and xy[0] is not None:
        return (xy[0], xy[1], p.get("z_local") or 0.0)
    return None


def _dans_poly(x, y, r):
    r = np.asarray(r)[:, :2]
    xs, ys = r[:, 0], r[:, 1]
    c = False
    j = len(r) - 1
    for i in range(len(r)):
        if ((ys[i] > y) != (ys[j] > y)) and (x < (xs[j] - xs[i]) * (y - ys[i]) / (ys[j] - ys[i] + 1e-12) + xs[i]):
            c = not c
        j = i
    return c


def surface_a(xy_local):
    """Surface v2 (base/surfaces.geojson, zone pilote) puis surfaces_2026 du paquet contenant le point."""
    x, y = xy_local[0] + O[0], xy_local[1] + O[1]
    for f in _lire(RACINE / "recon/out/paquet_jardin/v2/description/base/surfaces.geojson")["features"]:
        for r in _anneaux(f["geometry"]):
            if _dans_poly(x, y, r):
                return f["properties"]["id"], f["properties"].get("classe"), f["properties"].get("etat_v1")
    for f in _lire(RACINE / "recon/out/paquet_jardin/package/donnees/surfaces/surfaces_2026.geojson")["features"]:
        for r in _anneaux(f["geometry"]):
            if _dans_poly(x, y, r):
                return f["properties"]["id"], f["properties"].get("classe"), f["properties"].get("etat")
    return None, None, None


def preuve(fichier, pixels=None, bbox=None, tuile=None, note=None):
    p = Path(fichier)
    if not p.is_absolute():
        p = ICI / "preuves" / fichier
    d = dict(fichier=p.relative_to(RACINE).as_posix())
    if pixels is not None:
        d["pixels"] = pixels
    if bbox is not None:
        d["bbox"] = bbox
    if tuile is not None:
        d["tuile"] = tuile
    if note:
        d["note"] = note
    return d
