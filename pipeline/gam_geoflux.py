"""Vecteurs open data de Grenoble-Alpes Métropole (GeoServer « geoflux »)
sur l'emprise de Meylan : levés topographiques 3D (marquages au sol lignes et
symboles, bordures, caniveaux, limites de revêtement, arbres...), PCRS vecteur
(limites de voirie, changements de revêtement...), graphe de voirie,
aménagements cyclables, arrêts TC, parkings relais, ouvrages d'art.

Les objets sont demandés en Lambert-93 (avec Z) puis convertis en WGS84 (Z
conservé) pour rester homogènes avec les autres couches.

Usage : python3 pipeline/gam_geoflux.py
"""
from __future__ import annotations

import json
import math

from common import DATA, http_get, to_wgs84
from ortho import bbox_l93_for_commune

WFS = "https://geoflux.grenoblealpesmetropole.fr/geoserver/wfs"
LAYERS = [
    # levés topographiques (fichier Meylan_Topo) — géométrie fine de la chaussée
    *[f"donnees_referentielles_topo:topo_sol_{n}" for n in (
        "signalisation_horizontale_lin", "signalisation_horizontale_pct",
        "bordure_lin", "bordure_pct", "caniveau_lin", "limite_revetement_lin",
        "seuil_lin", "glissiere_lin", "rambarde_lin", "mur_de_soutenement_lin",
        "escalier_rampe_lin", "ouvrage_art_lin", "talus_haut_lin", "talus_bas_lin",
        "arbre_lin", "arbre_pct", "vegetation_lin", "clotures_lin", "fosse_lin",
        "tram_rail_lin", "batiment_lin", "batiment_pct")],
    # PCRS vecteur
    *[f"d_ref_pcrs_vecteur:{n}" for n in (
        "limite_voirie_pcrs", "changement_revetements_pcrs", "accotement_pcrs",
        "marche_escalier_pcrs", "mur_pcrs", "seuil_pcrs", "facade_pcrs", "rail_pcrs")],
    # réseau et mobilité
    "voiries_public_opendata:v_graphe_troncon",
    "voiries_public_opendata:v_graphe_plo",
    "voiries_public_opendata:gl_nom_voies",
    "voirie_cycles_public_opendata:v_amenagements_cyclables_grand_public",
    "dmtcep:intermodalite_parkings_relais",
    "ouvrages_art:ouvrage_art_referentiel",
    "voiries_public:voiries_eclairage_public_sectorisation",
]
PAGE = 5000


def to_wgs(coords):
    if not coords:  # géométrie vide renvoyée par le serveur
        return coords
    if isinstance(coords[0], (int, float)):
        lon, lat = to_wgs84(coords[0], coords[1])
        return [round(lon, 8), round(lat, 8), *coords[2:]]
    return [to_wgs(c) for c in coords]


def fetch_cql(layer, cql):
    """Filtre attributaire (ex. fichier='Meylan_Topo.dwg') : beaucoup plus rapide
    que les requêtes par emprise pour les levés topographiques."""
    feats, start = [], 0
    while True:
        r = http_get(WFS, params={
            "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
            "TYPENAMES": layer, "SRSNAME": "EPSG:2154", "OUTPUTFORMAT": "application/json",
            "CQL_FILTER": cql, "COUNT": PAGE, "STARTINDEX": start}, timeout=(30, 90), retries=8)
        page = r.json().get("features", [])
        feats += page
        if len(page) < PAGE:
            return feats
        start += PAGE


def filter_view(layer, feats):
    """Le CQL_FILTER remplace le filtre interne des vues *_lin / *_pct du
    serveur (qui partagent la même table) : on reproduit ce filtre ici d'après
    le type d'objet DAO d'origine (type_geom)."""
    pts = ("fme_point", "fme_text")
    if layer.endswith("_pct"):
        return [f for f in feats if f["properties"].get("type_geom") in pts]
    if layer.endswith("_lin"):
        return [f for f in feats if f["properties"].get("type_geom") not in pts]
    return feats


def fetch(layer, bbox, step=1000.0):
    """Requêtes par dalles de 1 km (les grosses requêtes paginées sont très
    lentes côté serveur), dédoublonnage par identifiant d'objet."""
    out = {}
    x0, y0 = math.floor(bbox[0] / step) * step, math.floor(bbox[1] / step) * step
    nx, ny = math.ceil((bbox[2] - x0) / step), math.ceil((bbox[3] - y0) / step)
    for i in range(nx):
        for j in range(ny):
            b = (x0 + i * step, y0 + j * step, x0 + (i + 1) * step, y0 + (j + 1) * step)
            for f in fetch_bbox(layer, b):
                out[f.get("id") or json.dumps(f["properties"], sort_keys=True)] = f
    return list(out.values())


def fetch_bbox(layer, bbox, depth=0):
    """Une requête par emprise SANS STARTINDEX (certaines vues sans clé primaire
    refusent la pagination : HTTP 400) ; si la page est pleine, l'emprise est
    découpée en 4 (quadtree)."""
    r = http_get(WFS, params={
        "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
        "TYPENAMES": layer, "SRSNAME": "EPSG:2154", "OUTPUTFORMAT": "application/json",
        "BBOX": ",".join(f"{v:.1f}" for v in bbox) + ",EPSG:2154",
        "COUNT": PAGE}, timeout=(30, 90), retries=8)
    page = r.json().get("features", [])
    if len(page) < PAGE or depth >= 6:
        return page
    x0, y0, x1, y1 = bbox
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    out = []
    for b in ((x0, y0, xm, ym), (xm, y0, x1, ym), (x0, ym, xm, y1), (xm, ym, x1, y1)):
        out += fetch_bbox(layer, b, depth + 1)
    return out


def main():
    out = DATA / "vector" / "gam"
    out.mkdir(parents=True, exist_ok=True)
    bbox = bbox_l93_for_commune()
    for layer in LAYERS:
        name = layer.split(":")[1]
        if (out / f"{name}.geojson").exists():
            continue
        try:
            if layer.startswith("donnees_referentielles_topo:"):
                fs = filter_view(layer, fetch_cql(layer, "fichier='Meylan_Topo.dwg'"))
            else:
                fs = fetch(layer, bbox)
        except Exception as e:  # noqa: BLE001
            print(f"{layer:70s} ERREUR {str(e)[:120]}")
            continue
        for f in fs:
            if f.get("geometry"):
                f["geometry"]["coordinates"] = to_wgs(f["geometry"]["coordinates"])
        (out / f"{name}.geojson").write_text(json.dumps(
            {"type": "FeatureCollection", "features": fs}, ensure_ascii=False))
        print(f"{layer:70s} {len(fs):6d}")


if __name__ == "__main__":
    main()
