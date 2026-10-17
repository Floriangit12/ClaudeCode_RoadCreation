#!/usr/bin/env python
"""Relevé Meylan : carte des sites en SVG, sans photo (fond : limite communale BD TOPO, routes OSM).

  python -I carte_sites.py            → recon/generateur/meylan/carte_sites.svg
                                        + aperçu PNG de contrôle (non versionné) recon/out/generateur/meylan/carte_sites_apercu.png

Sites : tout dossier de recon/generateur/meylan/ qui contient un mesures.json avec « repere.origine_l93 » (lot A :
carrefours et rues ; lot B : dossiers auto_* et axe_*, tracés en gris). Sources du fond : BD TOPO IGN (commune,
Licence Ouverte), OpenStreetMap (routes, ODbL), extraits locaux de data/vector_gz/.
"""
import gzip
import json
from pathlib import Path
from xml.sax.saxutils import escape

from pyproj import Transformer

RACINE = Path(__file__).resolve().parents[4]
MEY = RACINE / "recon/generateur/meylan"
VG = RACINE / "data/vector_gz"
T = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
W, H, MARGE = 1000, 760, 30
GENRES = {  # dossier → (libellé court, couleur)
    "paquet_jardin": ("feux", "#c0392b"), "verdun_centre_feux": ("feux", "#c0392b"),
    "verdun_lycee_feux": ("feux", "#c0392b"), "vieux_chene_taillefer_feux": ("feux + îlots", "#c0392b"),
    "vieux_chene_inovallee_piste": ("piste + feux", "#1e8449"), "rp_lycee": ("giratoire", "#1f5fa8"),
    "rp_didcot": ("giratoire", "#1f5fa8"), "avenue_7_laux_separateur": ("avenue séparée", "#8e44ad"),
}
DECALAGES = {  # position des étiquettes (px) pour éviter les chevauchements
    "rp_lycee": (20, -40), "verdun_lycee_feux": (-40, -30), "avenue_7_laux_separateur": (25, -70),
    "verdun_centre_feux": (-40, -10), "paquet_jardin": (-40, 15), "vieux_chene_taillefer_feux": (-40, 45),
    "rp_didcot": (-40, -60), "vieux_chene_inovallee_piste": (20, -30),
}
LIBELLES = {
    "paquet_jardin": "M01 Paquet Jardin", "verdun_centre_feux": "M17 Verdun × Buclos",
    "verdun_lycee_feux": "M08 Verdun × Chamrousse", "vieux_chene_taillefer_feux": "M07 Vieux Chêne × Taillefer",
    "vieux_chene_inovallee_piste": "M16 Vieux Chêne Inovallée", "rp_lycee": "M02 RP du Lycée",
    "rp_didcot": "M03 RP de Didcot", "avenue_7_laux_separateur": "Av. des 7 Laux",
}


def lignes_l93(geom):
    t = geom["type"]
    if t == "LineString":
        return [geom["coordinates"]]
    if t == "MultiLineString":
        return geom["coordinates"]
    if t == "Polygon":
        return geom["coordinates"]
    if t == "MultiPolygon":
        return [r for p in geom["coordinates"] for r in p]
    return []


def main():
    com = [f for f in json.load(gzip.open(VG / "bdtopo/commune.geojson.gz", "rt", encoding="utf-8"))["features"]
           if f["properties"].get("code_insee") == "38229"][0]
    anneaux = [[T.transform(x, y) for x, y, *_ in r] for r in lignes_l93(com["geometry"])]
    sites = []
    for d in sorted(MEY.iterdir()):
        fm = d / "mesures.json"
        if not fm.exists():
            continue
        try:
            o = json.loads(fm.read_text(encoding="utf-8")).get("repere", {}).get("origine_l93")
        except Exception:
            o = None
        if o:
            sites.append((d.name, o[0], o[1], d.name in GENRES))
    # emprise : les sites + 350 m (la commune s'étend loin au nord, sur la Chartreuse)
    xs = [s[1] for s in sites]
    ys = [s[2] for s in sites]
    x0, x1, y0, y1 = min(xs) - 350, max(xs) + 350, min(ys) - 350, max(ys) + 350
    k = min((W - 2 * MARGE) / (x1 - x0), (H - 2 * MARGE - 40) / (y1 - y0))

    def px(x, y):
        return MARGE + (x - x0) * k, MARGE + 40 + (y1 - y) * k

    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
           'font-family="Arial, sans-serif">' % (W, H, W, H),
           '<rect width="100%" height="100%" fill="#ffffff"/>',
]
    for r in anneaux:
        d = " ".join("%.1f,%.1f" % px(*p) for p in r)
        out.append('<polygon points="%s" fill="#f4f6f0" stroke="#7a8a6a" stroke-width="1.2"/>' % d)
    styles = {"motorway": ("#e67e22", 2.4), "trunk": ("#e67e22", 2.0), "motorway_link": ("#e67e22", 1.0),
              "trunk_link": ("#e67e22", 1.0), "primary": ("#555", 1.6), "secondary": ("#777", 1.2),
              "tertiary": ("#999", 0.9), "primary_link": ("#777", 0.8), "secondary_link": ("#999", 0.7)}
    for f in json.load(gzip.open(VG / "osm/roads.geojson.gz", "rt", encoding="utf-8"))["features"]:
        st = styles.get(f["properties"].get("highway"))
        if not st:
            continue
        for l in lignes_l93(f["geometry"]):
            pts = [px(*T.transform(x, y)) for x, y, *_ in l]
            if all(not (MARGE <= u <= W - MARGE and MARGE + 40 <= v <= H - MARGE) for u, v in pts):
                continue
            out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%.1f"/>'
                       % (" ".join("%.1f,%.1f" % p for p in pts), st[0], st[1]))
    for nom, x, y, lot_a in sites:
        u, v = px(x, y)
        if lot_a:
            lib, col = GENRES[nom]
            out.append('<circle cx="%.1f" cy="%.1f" r="7" fill="%s" stroke="#fff" stroke-width="1.5"/>' % (u, v, col))
            dx, dy = DECALAGES.get(nom, (9, -6))
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="0.8"/>' % (u, v, u + dx, v + dy, col))
            ancre = "start" if dx >= 0 else "end"
            out.append('<text x="%.1f" y="%.1f" text-anchor="%s" font-size="12" fill="#111" stroke="#fff" stroke-width="3" '
                       'paint-order="stroke">%s</text>' % (u + dx + (3 if dx >= 0 else -3), v + dy + 4, ancre,
                                                           escape(LIBELLES.get(nom, nom))))
        else:
            out.append('<rect x="%.1f" y="%.1f" width="9" height="9" fill="#9a9a9a" stroke="#fff"/>' % (u - 4.5, v - 4.5))
            out.append('<text x="%.1f" y="%.1f" font-size="10" fill="#666" stroke="#fff" stroke-width="3" '
                       'paint-order="stroke">%s</text>' % (u + 7, v + 12, escape(nom)))
    ly = H - 110
    for i, (lib, col) in enumerate([("carrefour à feux", "#c0392b"), ("giratoire", "#1f5fa8"),
                                    ("rue à piste cyclable", "#1e8449"), ("avenue à chaussées séparées", "#8e44ad")]):
        out.append('<circle cx="%d" cy="%d" r="6" fill="%s"/>' % (MARGE + 8, ly + i * 20, col))
        out.append('<text x="%d" y="%d" font-size="12" fill="#222">%s</text>' % (MARGE + 20, ly + i * 20 + 4, lib))
    out.append('<rect x="%d" y="%d" width="9" height="9" fill="#9a9a9a"/>' % (MARGE + 3, ly + 75))
    out.append('<text x="%d" y="%d" font-size="12" fill="#222">site du lot B (autoroute, axes)</text>' % (MARGE + 20, ly + 84))
    # échelle 500 m
    sx = W - MARGE - 500 * k
    out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#222" stroke-width="2"/>' % (sx, H - 40, W - MARGE, H - 40))
    out.append('<text x="%.1f" y="%d" font-size="12" fill="#222">500 m</text>' % (sx, H - 46))
    out.append('<text x="%d" y="%d" font-size="10" fill="#666">Fond : limite communale BD TOPO © IGN (Licence Ouverte) ; '
               'routes © contributeurs OpenStreetMap (ODbL). Lambert-93, nord en haut. Aucune photo.</text>' % (MARGE, H - 12))
    out.append('<rect x="0" y="0" width="%d" height="40" fill="#ffffff"/>' % W)
    out.append('<text x="%d" y="26" font-size="18" fill="#222">Relevé Meylan — sites décrits (lot A : carrefours et rues ; '
               'lot B : autoroute et axes, en gris)</text>' % MARGE)
    out.append("</svg>")
    (MEY / "carte_sites.svg").write_text("\n".join(out), encoding="utf-8")
    apercu(out)
    print(MEY / "carte_sites.svg", len(sites), "sites")


def apercu(lignes):
    """Rasterise les primitives simples du SVG (polygon, polyline, circle, rect, text) avec PIL, pour le contrôle."""
    import re
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(im)
    try:
        fo = ImageFont.truetype("arial.ttf", 12)
    except Exception:
        fo = ImageFont.load_default()
    att = lambda s, k: (re.search(r'%s="([^"]*)"' % k, s) or [None, None])[1]  # noqa: E731
    for s in lignes:
        if s.startswith("<polygon") or s.startswith("<polyline"):
            pts = [tuple(map(float, q.split(","))) for q in att(s, "points").split()]
            if len(pts) < 2:
                continue
            if s.startswith("<polygon"):
                dr.polygon(pts, fill=att(s, "fill"), outline=att(s, "stroke"))
            else:
                dr.line(pts, fill=att(s, "stroke"), width=max(1, int(round(float(att(s, "stroke-width"))))))
        elif s.startswith("<circle"):
            cx, cy, r = float(att(s, "cx")), float(att(s, "cy")), float(att(s, "r"))
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=att(s, "fill"))
        elif s.startswith("<rect x="):
            x, y, w, h = (float(att(s, k)) for k in ("x", "y", "width", "height"))
            dr.rectangle([x, y, x + w, y + h], fill=att(s, "fill"))
        elif s.startswith("<line"):
            dr.line([(float(att(s, "x1")), float(att(s, "y1"))), (float(att(s, "x2")), float(att(s, "y2")))],
                    fill=att(s, "stroke"), width=max(1, int(round(float(att(s, "stroke-width"))))))
        elif s.startswith("<text"):
            txt = re.sub(r"<[^>]+>", "", s).replace("&amp;", "&")
            x = float(att(s, "x"))
            if att(s, "text-anchor") == "end":
                x -= dr.textlength(txt, font=fo)
            dr.text((x, float(att(s, "y")) - 11), txt, fill=att(s, "fill"), font=fo)
    d = RACINE / "recon/out/generateur/meylan"
    d.mkdir(parents=True, exist_ok=True)
    im.save(d / "carte_sites_apercu.png")


if __name__ == "__main__":
    main()
