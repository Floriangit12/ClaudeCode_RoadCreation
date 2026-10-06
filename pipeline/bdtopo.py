"""Téléchargement BD TOPO v3 (IGN) sur l'emprise de Meylan via le WFS de la
Géoplateforme, export GeoJSON (WGS84) par classe.

Classes utiles à la chaussée : troncon_de_route (largeur de chaussée, nombre
de voies, nature, importance, sens, vitesse moyenne...), route_numerotee_ou_nommee,
voie_nommee, equipement_de_transport, non_communication, point_du_reseau,
batiment, zone_de_vegetation, haie, construction_*...

Usage : python3 pipeline/bdtopo.py
"""
from __future__ import annotations

import json

from common import CONFIG, DATA, http_get

WFS = "https://data.geopf.fr/wfs"
TYPES = [
    "troncon_de_route", "route_numerotee_ou_nommee", "voie_nommee",
    "equipement_de_transport", "non_communication", "point_du_reseau",
    "itineraire_autre", "batiment", "construction_lineaire",
    "construction_ponctuelle", "construction_surfacique", "zone_de_vegetation",
    "haie", "troncon_de_voie_ferree", "terrain_de_sport", "erp",
    "zone_d_activite_ou_d_interet", "toponymie", "cours_d_eau",
    "troncon_hydrographique", "surface_hydrographique", "point_d_acces",
    "zone_d_habitation", "commune",
]
PAGE = 5000


def fetch(typename, bbox, margin=0.003):
    x0, y0, x1, y1 = bbox
    b = f"{y0 - margin},{x0 - margin},{y1 + margin},{x1 + margin},urn:ogc:def:crs:EPSG::4326"
    feats, start = [], 0
    while True:
        r = http_get(WFS, params={
            "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
            "TYPENAMES": f"BDTOPO_V3:{typename}", "OUTPUTFORMAT": "application/json",
            "SRSNAME": "EPSG:4326", "BBOX": b, "COUNT": PAGE, "STARTINDEX": start,
        }, timeout=300)
        page = r.json().get("features", [])
        feats += page
        if len(page) < PAGE:
            return feats
        start += PAGE


def main():
    out = DATA / "vector" / "bdtopo"
    out.mkdir(parents=True, exist_ok=True)
    bbox = CONFIG["commune"]["bbox_wgs84"]
    for t in TYPES:
        try:
            fs = fetch(t, bbox)
        except Exception as e:  # noqa: BLE001
            print(f"{t:32s} ERREUR {e}")
            continue
        # GeoJSON WGS84 : axes lon/lat (le serveur renvoie bien x=lon en JSON)
        (out / f"{t}.geojson").write_text(json.dumps(
            {"type": "FeatureCollection", "features": fs}, ensure_ascii=False))
        print(f"{t:32s} {len(fs):6d} objets")


if __name__ == "__main__":
    main()
