"""Amorce de la table d'événements de l'état avant travaux (PLAN § 2.1) : avant_travaux.evenements.geojson.

    python recon/pcg/etat/etats/amorcer_evenements.py [--planche]

Sources (lecture seule) :
- inventaire/changements/changements_2022_2025.geojson : CHG-001 à CHG-021 (géométries reprises au cm près),
  familles et corrections de dates du tableau du § 2.1 (CONSTR-EST <= 12/08/2021, CHG-004 <= 05/03/2022,
  CHG-018 / 021 jusqu'au 08/08/2025, fin de la fenêtre Pléiades) ;
- TRV-C1-2025 (emprise des travaux du carrefour) : union, sur un raster local de 0,25 m, des zones neuf_2025 et
  refait_2025_identique de decrire/marquages_sources.zones() (plan CAO 2025 dilaté de 3 m, surfaces v1
  modifie_2025, marques v1 refait_2025 / resurface_2025), des relief_zones_2026 reprises en 2025 et des tronçons
  zone_travaux_2025 de bordures_hauteurs (tamponnés de 1 m) ; marge de 3 m appliquée par E.valide ;
- TRV-VERCORS-TROTTOIRS : ±15 m autour de l'axe du Vercors (BD TOPO, enrichir/orthos_recentes.py:865), au sud de
  y = -15 m local.
Le lot 1b enrichit ce fichier (EVT-2019-*, SURF-0344, observe_post, observations négatives OBS-*) : format dans
etats/README.md. Sortie déterministe (entités triées par id, coordonnées au cm, aucune date d'exécution).
--planche : cartes de contrôle sur l'ortho PCRS 2022 (Licence Ouverte), versionnables, dans
recon/out/paquet_jardin/v2_avant_travaux/sources/p0/ (site à 0,28 m/px et cœur ±54 m à 0,10 m/px, chacune
au plus 1092 px de côté : vue sans réduction).
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[3]
os.environ.pop("PJ_ETAT", None)                  # l'emprise 2026 se lit hors état (zones de l'archive)
sys.path.insert(0, str(RACINE / "recon/pcg/decrire"))

O = (917279.43, 6460289.98)
CHANGEMENTS = RACINE / "recon/out/paquet_jardin/v2_avant_travaux/inventaire/changements/changements_2022_2025.geojson"
DONNEES = RACINE / "recon/out/paquet_jardin/package/donnees"
SORTIE = ICI / "avant_travaux.evenements.geojson"
PLANCHES = RACINE / "recon/out/paquet_jardin/v2_avant_travaux/sources/p0"
PLAN = "recon/out/paquet_jardin/v2_avant_travaux/inventaire/PLAN_AVANT_TRAVAUX.md"
RES = 0.25
VERCORS_AXE = [(1.1, -5.5), (3.9, -11.3), (14.6, -33.8), (38.0, -129.0), (41.3, -143.3)]   # local, BD TOPO

# familles touchées (PLAN § 2.1) et paramètres propres à chaque changement
FAMILLES_CHG = {
    "CHG-001": ["toutes"], "CHG-002": ["toutes"], "CHG-003": ["geometrie", "marquage", "objet"],
    "CHG-004": ["geometrie"], "CHG-005": ["objet"], "CHG-006": ["geometrie", "objet", "vegetation"],
    "CHG-007": ["geometrie", "objet", "vegetation"], "CHG-008": ["marquage"], "CHG-009": ["texture"],
    "CHG-010": ["texture"], "CHG-011": ["texture"], "CHG-012": ["apparence"], "CHG-013": ["vegetation"],
    "CHG-014": ["vegetation"], "CHG-015": ["vegetation"], "CHG-016": ["vegetation"], "CHG-017": ["vegetation"],
    "CHG-018": ["geometrie", "texture", "vegetation"], "CHG-019": ["toutes"], "CHG-020": ["apparence"],
    "CHG-021": ["geometrie", "texture", "vegetation"],
}
RAYON_CHG = {"CHG-007": (6.0, "accès riverain d'environ 5 m, position approchée"),
             "CHG-013": (7.5, "houppier d'environ 15 m"), "CHG-014": (6.0, "houppier d'environ 12 m"),
             "CHG-015": (4.0, "bosquet"), "CHG-016": (3.5, "massif d'environ 7 m"),
             "CHG-017": (1.5, "houppiers de 1 à 1,5 m")}
CORRECTIONS = {
    "CHG-001": {"date_min": "2021-08-12", "date_min_borne": "au_plus",
                "note": "PLAN § 2.1 : CONSTR-EST commence au plus tard le 12/08/2021 (terrain déjà remanié sur le LiDAR) ; date à resserrer par le lot 1b (BD ORTHO 21/08/2018 et 13/08/2021)"},
    "CHG-002": {"date_min": "2021-08-12", "date_min_borne": "au_plus",
                "note": "PLAN § 2.1 : CONSTR-EST commence au plus tard le 12/08/2021 (terrain déjà remanié sur le LiDAR) ; date à resserrer par le lot 1b"},
    "CHG-004": {"date_min": "2022-03-05", "date_min_borne": "au_plus",
                "note": "PLAN § 2.1 : rive est du Vercors déjà en chantier le 05/03/2022 (Mapillary)"},
    "CHG-018": {"date_max": "2025-08-08", "note": "PLAN § 2.1 : date_max = fin de la fenêtre Pléiades 2025 (date de prise inconnue, 03/05 -> 08/08/2025)"},
    "CHG-021": {"date_max": "2025-08-08", "note": "PLAN § 2.1 : date_max = fin de la fenêtre Pléiades 2025 (date de prise inconnue, 03/05 -> 08/08/2025)"},
}
EFFETS = {   # colonnes « effet pour T » du tableau du § 2.1 (résumé)
    "CHG-001": ("PCRS 2022 et 2019, LiDAR 2021 non valables ; IGN 2024, photos du 24/08/2024 et GAM daté valables", "idem, plus les photos du 18/05/2025 hors CHG-006"),
    "CHG-002": ("PCRS 2022 et 2019, LiDAR 2021 non valables ; IGN 2024, photos du 24/08/2024 et GAM daté valables", "idem, plus les photos du 18/05/2025 hors CHG-006"),
    "CHG-003": ("IGN 2024, photos du 24/08/2024 et du 12/01/2025", "IGN 2024, photos du 12/01/2025 ; incertain dans CHG-019"),
    "CHG-004": ("IGN 2024 et photos du 24/08/2024 ; pas le GAM (trottoirs refaits jusqu'au 30/01/2026)", "IGN 2024 et photos du 12/01/2025 ; incertain (CHG-019)"),
    "CHG-005": ("base vie présente", "base vie présente"),
    "CHG-006": ("état du jour : clôtures de chantier, bungalows ; photos de 2025 non valables", "haies et parkings ; photos de 2024 non valables"),
    "CHG-007": ("état du jour (portail de chantier) ; photos de 2025 non valables", "entrée de parking ; photos de 2024 non valables"),
    "CHG-008": ("PCRS 2022 non valable pour les marquages ; IGN 2024 et photos du 24/08/2024", "idem, plus les photos du 18/05/2025"),
    "CHG-009": ("aspect d'après l'IGN 2024 et les photos du 24/08/2024 ; âge récent", "idem, plus les photos du 18/05/2025"),
    "CHG-019": ("sans objet (T avant) ; photos du 18/05/2025 admises seulement dans la zone rognée par observation négative", "T dans l'intervalle : incertain, à rogner (lot 1b)"),
    "CHG-018": ("T 15 jours après date_min : état du 09/08/2024 retenu, confiance moyenne", "incertain : Pléiades et GAM daté, à vérifier"),
    "CHG-021": ("T 15 jours après date_min : état du 09/08/2024 retenu, confiance moyenne", "incertain : Pléiades et GAM daté, à vérifier"),
}
FORMAT = {
    "reference": "PLAN_AVANT_TRAVAUX.md § 2.1 ; documentation complète : recon/pcg/etat/etats/README.md",
    "crs": "Lambert-93 (EPSG:2154) ; repère local = L93 - (917279.43, 6460289.98)",
    "type": "evenement | observation_negative",
    "evenement": {
        "id": "identifiant unique (CHG-0xx, TRV-*, EVT-*, SURF-*)",
        "date_min": "AAAA-MM-JJ : dernier jour où l'état ANCIEN est certain (le changement a lieu après)",
        "date_min_borne": "facultatif, « au_plus » : la date réelle est antérieure ou égale (borne ouverte)",
        "date_max": "AAAA-MM-JJ : premier jour où l'état NOUVEAU est certain",
        "observe_post": "null | AAAA-MM-JJ | [{date, zone (géométrie GeoJSON L93)}] : première observation de l'état d'après (resserre date_max)",
        "familles": "sous-ensemble de geometrie, marquage, texture, objet, vegetation, apparence ; ou [toutes]",
        "observe": "true si le changement est constaté (image, document de récolement) ; false s'il est seulement annoncé",
        "confiance": "haute | moyenne | faible",
        "marge_m": "bande d'incertitude autour du bord de l'emprise (défaut : evenements.marge_defaut_m de la configuration)",
        "rayon_m": "facultatif : dilatation d'une emprise ponctuelle ou linéaire",
        "preuve": "liste de {source, ref | id | url, date, note}",
    },
    "observation_negative": {
        "id": "OBS-...",
        "date": "AAAA-MM-JJ : jour où la zone est vue inchangée (pose acceptée, visibilité calculée)",
        "familles": "familles que la vue prouve inchangées",
        "evenements": "facultatif : identifiants rognés (défaut : tous les événements non observés)",
        "geometrie": "polygone de visibilité (L93)",
        "effet": "dans la zone, date_min des événements visés := max(date_min, date) ; pour T <= date, zone retirée de l'événement",
    },
}


def rond(c, nd=2):
    if isinstance(c, (list, tuple)):
        return [rond(x, nd) for x in c]
    return round(float(c), nd) + 0.0


def preuves_courtes(pr):
    out = []
    for p in pr:
        q = {k: p[k] for k in ("source", "id", "ref", "url", "date", "note", "licence") if p.get(k) not in (None, "")}
        out.append(q)
    return out


# --------------------------------------------------------------------------- raster -> polygones
def _dp(P, tol):
    """Douglas-Peucker itératif sur une polyligne ouverte (N, 2) : indices gardés."""
    garde = np.zeros(len(P), bool)
    garde[0] = garde[-1] = True
    pile = [(0, len(P) - 1)]
    while pile:
        a, b = pile.pop()
        if b <= a + 1:
            continue
        A, B = P[a], P[b]
        d = B - A
        L = np.hypot(*d)
        Q = P[a + 1:b]
        dist = np.abs(d[0] * (Q[:, 1] - A[1]) - d[1] * (Q[:, 0] - A[0])) / L if L > 1e-12 else np.hypot(*(Q - A).T)
        k = int(np.argmax(dist))
        if dist[k] > tol:
            garde[a + 1 + k] = True
            pile += [(a, a + 1 + k), (a + 1 + k, b)]
    return garde


def simplifier_anneau(r, tol):
    r = np.asarray(r, float)
    if np.allclose(r[0], r[-1]):
        r = r[:-1]
    if len(r) <= 4:
        return np.vstack([r, r[:1]])
    i = int(np.argmax(np.hypot(*(r - r[0]).T)))          # coupe l'anneau en deux chaînes aux points éloignés
    c1, c2 = r[:i + 1], np.vstack([r[i:], r[:1]])
    s = np.vstack([c1[_dp(c1, tol)], c2[_dp(c2, tol)][1:-1]])
    return np.vstack([s, s[:1]]) if len(s) >= 3 else np.vstack([r, r[:1]])


def aire(r):
    r = np.asarray(r, float)
    return 0.5 * float(np.dot(r[:-1, 0], r[1:, 1]) - np.dot(r[1:, 0], r[:-1, 1]))


def polygoniser(masque, x0, y1, res, aire_min=2.0, tol=0.13):
    """Masque booléen (lignes du nord au sud) -> MultiPolygon GeoJSON en L93 (trous compris), au cm."""
    import rasterio.features
    from affine import Affine
    tr = Affine(res, 0.0, x0 + O[0], 0.0, -res, y1 + O[1])
    polys = []
    for g, v in rasterio.features.shapes(masque.astype(np.uint8), mask=masque, transform=tr, connectivity=4):
        if v != 1:
            continue
        anneaux = []
        for k, r in enumerate(g["coordinates"]):
            s = simplifier_anneau(r, tol)
            a = aire(s)
            if abs(a) < aire_min or len(s) < 4:
                if k == 0:
                    break
                continue
            if (k == 0) != (a > 0):                      # RFC 7946 : extérieur anti-horaire, trous horaires
                s = s[::-1]
            anneaux.append(rond(s.tolist()))
        if anneaux:
            polys.append(anneaux)
    polys.sort(key=lambda p: (p[0][0][0], p[0][0][1]))
    return {"type": "MultiPolygon", "coordinates": polys}


def emprise_trv_c1():
    from PIL import Image, ImageFilter
    import rasterio.features
    from affine import Affine
    import marquages_sources as S
    z = S.zones()
    code, x0, y1, res, H, W = z["code"], z["x0"], z["y1"], z["res"], z["H"], z["W"]
    assert abs(res - RES) < 1e-9
    m = np.isin(code, [S.ETATS.index("neuf_2025"), S.ETATS.index("refait_2025_identique")])
    n_zones = int(m.sum())
    tr = Affine(res, 0.0, x0 + O[0], 0.0, -res, y1 + O[1])
    rz = json.loads((DONNEES / "relief/relief_zones_2026.geojson").read_text(encoding="utf-8"))
    types_rz = ("ancienne_chaussee_rehaussee_2025", "traversee_bordure_abaissee", "ancienne_chaussee_trottoir_par_defaut")
    geoms = [f["geometry"] for f in rz["features"] if f["properties"]["zone"] in types_rz]
    m_rz = rasterio.features.rasterize([(g, 1) for g in geoms], out_shape=(H, W), transform=tr, dtype="uint8") > 0
    bh = json.loads((DONNEES / "relief/bordures_hauteurs.geojson").read_text(encoding="utf-8"))
    lignes = [f["geometry"] for f in bh["features"] if f["properties"].get("zone_travaux_2025")]
    m_l = rasterio.features.rasterize([(g, 1) for g in lignes], out_shape=(H, W), transform=tr, dtype="uint8",
                                      all_touched=True)
    k = int(round(1.0 / res)) * 2 + 1                      # tampon de 1 m
    m_l = np.asarray(Image.fromarray(m_l * 255).filter(ImageFilter.MaxFilter(k))) > 0
    tout = m | m_rz | m_l
    stats = {"zones_neuf_refait_m2": n_zones * res * res, "relief_zones_m2": float(m_rz.sum()) * res * res,
             "troncons_zone_travaux": len(lignes), "troncons_tampon_m2": float(m_l.sum()) * res * res,
             "union_m2": float(tout.sum()) * res * res,
             "hors_zones_m2": float((tout & ~m).sum()) * res * res}
    return polygoniser(tout, x0, y1, res), stats


def emprise_vercors(demi=15.0, y_max=-15.0):
    x0, y1, H, W = -175.0, 175.0, 1400, 1400
    xs = x0 + (np.arange(W) + 0.5) * RES
    ys = y1 - (np.arange(H) + 0.5) * RES
    X, Y = np.meshgrid(xs, ys)
    P = np.c_[X.ravel(), Y.ravel()]
    d = np.full(len(P), np.inf)
    ax = np.asarray(VERCORS_AXE)
    for A, B in zip(ax[:-1], ax[1:]):
        AB = B - A
        t = np.clip(((P - A) @ AB) / (AB @ AB), 0, 1)
        d = np.minimum(d, np.hypot(*(P - (A + t[:, None] * AB)).T))
    m = ((d <= demi) & (P[:, 1] < y_max)).reshape(H, W)
    return polygoniser(m, x0, y1, RES)


# --------------------------------------------------------------------------- table
def construire():
    chg = json.loads(CHANGEMENTS.read_text(encoding="utf-8"))
    feats = []
    for f in chg["features"]:
        p = f["properties"]
        cid = p["id"]
        cor = CORRECTIONS.get(cid, {})
        q = {"id": cid, "type": "evenement", "nature": p["nature"], "secteur": p["secteur"],
             "description": p["description"],
             "date_min": cor.get("date_min", p["date_min"]), "date_max": cor.get("date_max", p["date_max"])}
        if cor.get("date_min_borne"):
            q["date_min_borne"] = cor["date_min_borne"]
        q.update({"observe_post": None, "familles": FAMILLES_CHG[cid], "observe": str(p["observe"]).lower() == "true",
                  "confiance": p["confiance"], "marge_m": 1.0})
        if cid in RAYON_CHG:
            q["rayon_m"], q["rayon_note"] = RAYON_CHG[cid]
        q["effet_pcrs_2022"] = p["effet_pcrs_2022"]
        if cid in EFFETS:
            q["effet_T"] = {"2024-08-24": EFFETS[cid][0], "2025-05-18": EFFETS[cid][1]}
        q["preuve"] = preuves_courtes(p["preuve"])
        q["origine"] = {"fichier": CHANGEMENTS.relative_to(RACINE).as_posix(), "id": cid,
                        "dates_inventaire": [p["date_min"], p["date_max"]]}
        if cor.get("note"):
            q["origine"]["correction_plan"] = cor["note"]
        feats.append({"type": "Feature", "properties": q, "geometry": {"type": f["geometry"]["type"],
                                                                         "coordinates": rond(f["geometry"]["coordinates"])}})
    g_c1, st = emprise_trv_c1()
    feats.append({"type": "Feature", "properties": {
        "id": "TRV-C1-2025", "type": "evenement", "nature": "travaux_carrefour",
        "secteur": "coeur", "description": "Travaux du carrefour Verdun / Vercors (ligne C1) : carrefour refait, tourne-à-droite SE supprimé, arrêts La Revirée relogés, traversées à feux supprimées.",
        "date_min": "2025-06-22", "date_max": "2025-12-05", "observe_post": None, "familles": ["toutes"],
        "observe": True, "confiance": "haute", "marge_m": 3.0,
        "periode_travaux": ["2025-06-23", "2025-12-05"],
        "effet_T": {"2024-08-24": "toute preuve postérieure au 22/06/2025 non valable dans l'emprise",
                    "2025-05-18": "toute preuve postérieure au 22/06/2025 non valable dans l'emprise"},
        "emprise_construction": "decrire/marquages_sources.zones() (neuf_2025 et refait_2025_identique : plan CAO 2025 dilaté de 3 m, surfaces v1 modifie_2025, marques v1 refait_2025 / resurface_2025 dilatées de 2 m) ∪ relief_zones_2026 (ancienne_chaussee_rehaussee_2025, traversee_bordure_abaissee, ancienne_chaussee_trottoir_par_defaut) ∪ tronçons zone_travaux_2025 de bordures_hauteurs tamponnés de 1 m ; raster de 0,25 m, Douglas-Peucker 0,13 m",
        "emprise_m2": {k: round(v, 2) for k, v in st.items() if k.endswith("m2")},
        "preuve": [
            {"source": "document", "ref": "data/raw/docs_web/meylan_fr/Panneau-generique-travaux-d-amelioration-ligne-C1.pdf", "note": "1 Carrefour Verdun/Vercors juillet-octobre 2025"},
            {"source": "document", "ref": "data/raw/docs_web/meylan_fr/MMV-165.pdf", "note": "point travaux C1 oct.-nov. 2025"},
            {"source": "code", "ref": "recon/pcg/enrichir/orthos_recentes.py:47", "note": "DEBUT_TRAVAUX 2025-06-23, FIN_TRAVAUX 2025-12-05"},
            {"source": "plan", "ref": PLAN + " § 2.1", "note": "TRV-C1-2025, marge de 3 m"}],
        "origine": {"fichier": "recon/pcg/etat/etats/amorcer_evenements.py"}},
        "geometry": g_c1})
    feats.append({"type": "Feature", "properties": {
        "id": "TRV-VERCORS-TROTTOIRS", "type": "evenement", "nature": "travaux_trottoirs",
        "secteur": "vercors", "description": "Trottoirs et végétalisation de l'avenue du Vercors refaits avec les travaux C1, jusqu'au 30/01/2026.",
        "date_min": "2025-06-22", "date_max": "2026-01-30", "observe_post": None, "familles": ["geometrie", "texture"],
        "observe": True, "confiance": "moyenne", "marge_m": 1.0,
        "familles_note": "PLAN § 2.1 : géométrie ; texture ajoutée (revêtements de trottoir refaits)",
        "emprise_construction": "±15 m autour de l'axe BD TOPO du Vercors (recon/pcg/enrichir/orthos_recentes.py:865, VERCORS_AXE), au sud de y = -15 m local (orthos_recentes.py:1029)",
        "preuve": [
            {"source": "code", "ref": "recon/pcg/enrichir/orthos_recentes.py:47", "note": "FIN_TROTTOIRS_VERCORS = 2026-01-30"},
            {"source": "document", "ref": "data/raw/docs_web/meylan_fr/MMV-165.pdf", "note": "point travaux C1 oct.-nov. 2025"},
            {"source": "plan", "ref": PLAN + " § 2.1", "note": "TRV-VERCORS-TROTTOIRS, ±15 m autour de l'axe"}],
        "origine": {"fichier": "recon/pcg/etat/etats/amorcer_evenements.py"}},
        "geometry": emprise_vercors()})
    feats.sort(key=lambda f: f["properties"]["id"])
    tete = {"type": "FeatureCollection", "name": "avant_travaux.evenements",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2154"}},
            "meta": {"etat": "avant_travaux", "statut": "amorce de la phase 0 (lot P0) : à enrichir par le lot 1b",
                     "sources": [CHANGEMENTS.relative_to(RACINE).as_posix(), PLAN + " § 2.1",
                                 "recon/pcg/decrire/marquages_sources.py (zones)",
                                 "recon/out/paquet_jardin/package/donnees/relief/{relief_zones_2026,bordures_hauteurs}.geojson"],
                     "genere_par": "python recon/pcg/etat/etats/amorcer_evenements.py",
                     "a_ajouter_lot_1b": ["EVT-2019-COLAS", "EVT-2019-2022-RESEAUX", "SURF-0344", "observe_post par zone",
                                          "observations négatives OBS-* (rognage de CHG-019 par les vues du 18/05/2025)",
                                          "redatation de CHG-004 et CONSTR-EST"]},
            "format": FORMAT}
    return tete, feats, st


def ecrire(tete, feats, chemin):
    d = json.dumps(tete, ensure_ascii=False)[:-1]
    lignes = [d + ',\n"features": [']
    for i, f in enumerate(feats):
        lignes.append(json.dumps(f, ensure_ascii=False, separators=(",", ":")) + ("," if i < len(feats) - 1 else ""))
    lignes.append("]}")
    chemin.write_text("\n".join(lignes) + "\n", encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- planche de contrôle
def planche(feats, chemin, res=0.28, demi=152.0):
    from PIL import Image, ImageDraw, ImageFont
    W = int(round(2 * demi / res))
    X0, Y1 = O[0] - demi, O[1] + demi
    fond = Image.new("RGB", (W, W), (40, 40, 40))
    dos = RACINE / "data/sites/paquet_jardin/ortho5cm_2022"
    for tx in range(int(X0 // 50) * 50, int(X0 + 2 * demi) + 1, 50):
        for ty in range(int((Y1 - 2 * demi) // 50) * 50, int(Y1) + 1, 50):
            f = dos / f"pcrs5cm_{tx}_{ty}.jpg"
            if not f.exists():
                continue
            im = Image.open(f).convert("RGB")
            n = int(round(50 / res))
            im = im.resize((n, n), Image.LANCZOS)
            fond.paste(im, (int(round((tx - X0) / res)), int(round((Y1 - (ty + 50)) / res))))
    fond = Image.blend(fond, Image.new("RGB", fond.size, (255, 255, 255)), 0.35)
    calque = Image.new("RGBA", fond.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(calque)
    couleurs = {"TRV-C1-2025": (220, 20, 60), "TRV-VERCORS-TROTTOIRS": (255, 140, 0), "CHG-019": (148, 0, 211),
                "CHG-001": (30, 90, 200), "CHG-002": (30, 90, 200), "CHG-008": (0, 160, 0), "CHG-009": (120, 80, 40)}

    def px(c):
        return [((x - X0) / res, (Y1 - y) / res) for x, y in c]
    ordre = sorted(feats, key=lambda f: (f["properties"]["id"] in ("TRV-C1-2025", "CHG-019"), f["properties"]["id"]))
    for f in ordre:
        p, g = f["properties"], f["geometry"]
        col = couleurs.get(p["id"], (0, 120, 160))
        if g["type"] in ("Polygon", "MultiPolygon"):
            polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
            for poly in polys:
                dr.polygon(px(poly[0]), fill=col + (55,), outline=col + (255,), width=2)
                for h in poly[1:]:
                    dr.polygon(px(h), fill=(0, 0, 0, 0), outline=col + (255,), width=1)
        else:
            pts = [g["coordinates"]] if g["type"] == "Point" else g["coordinates"]
            r = (p.get("rayon_m") or 1.0) / res
            for x, y in pts:
                (u, v), = px([(x, y)])
                dr.ellipse([u - r, v - r, u + r, v + r], outline=col + (255,), width=2)
    img = Image.alpha_composite(fond.convert("RGBA"), calque).convert("RGB")
    d2 = ImageDraw.Draw(img)
    try:
        police = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        police = ImageFont.load_default()
    for f in feats:
        p, g = f["properties"], f["geometry"]
        cs = g["coordinates"]
        if g["type"] == "Point":
            cs = [cs]
        while isinstance(cs[0][0], list):
            cs = cs[0]
        a = np.asarray(cs, float)[:, :2]
        (u, v), = px([tuple(a.mean(axis=0))])
        if 0 <= u < W and 0 <= v < W:
            d2.text((u + 3, v - 8), p["id"].replace("CHG-0", "C"), fill=(0, 0, 0), font=police)
    d2.rectangle([0, 0, W, 24], fill=(20, 20, 20))
    d2.text((6, 4), "Table d'événements (amorce P0) sur l'ortho PCRS 5 cm du 10/05/2022 ; rouge TRV-C1-2025 (marge 3 m), "
                    f"orange TRV-VERCORS, violet CHG-019 ; local ±{demi:g} m, {res:g} m/px", fill=(255, 255, 255), font=police)
    pas = 50 if demi > 100 else 10
    for k in range(-int(demi // pas) * pas, int(demi) + 1, pas):     # repères (local)
        u = (O[0] + k - X0) / res
        v = (Y1 - (O[1] + k)) / res
        d2.line([(u, 24), (u, 34)], fill=(0, 0, 0), width=2)
        d2.line([(0, v), (10, v)], fill=(0, 0, 0), width=2)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    img.save(chemin, quality=88)
    return chemin


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--planche", action="store_true")
    ap.add_argument("--sortie", default=str(SORTIE))
    a = ap.parse_args()
    tete, feats, st = construire()
    ecrire(tete, feats, Path(a.sortie))
    print(f"{len(feats)} événements écrits dans {a.sortie}")
    print("TRV-C1-2025 :", json.dumps({k: round(v, 1) if isinstance(v, float) else v for k, v in st.items()}, ensure_ascii=False))
    if a.planche:
        print("planche :", planche(feats, PLANCHES / "carte_evenements_ortho2022.jpg"))
        print("planche :", planche(feats, PLANCHES / "carte_evenements_coeur_ortho2022.jpg", res=0.1, demi=54.0))


if __name__ == "__main__":
    main()
