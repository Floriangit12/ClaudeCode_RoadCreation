"""construire_obs.py : saisie de la revue visuelle (saisie_obs.py) -> obs_ortho_B.json (format OBS).

- position : pixel continu (u, v) lu sur les vues de overlay.py (grille en pixels de dalle), affiné
  si demandé (af="sombre" | "clair" : centroïde de la tache contrastée la plus proche dans ±r px) ;
- valide_2026 : déduit des zones (relief_zones_2026 : ancienne chaussée rehaussée / trottoir par
  défaut / traversée abaissée ; surfaces_2026 etat modifie_2025 ou construit_2023_2024 ; emprise
  de la description), sauf valeur imposée dans la saisie ;
- preuve : vignette brut | description (2x) avec repère, dans preuves/, pour toute observation
  qui n'est pas une simple confirmation (ou si pr=True).

python construire_obs.py [--sans-vignettes]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from overlay import O, PAS, Dalle, _lire, DONNEES, charger, rendre  # noqa: E402
from saisie_obs import OBS  # noqa: E402

SORTIE = ICI.parent / "obs_ortho_B.json"
EMPRISE = (917129.43, 6460139.98, 917429.43, 6460439.98)   # emprise de la description (300 m)
DATE = "2022-05-10"


def dans(pt, anneau):
    x, y = pt
    a = np.asarray(anneau)
    xi, yi, xj, yj = a[:-1, 0], a[:-1, 1], a[1:, 0], a[1:, 1]
    c = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi)
    return bool(c.sum() % 2)


def dans_geom(pt, g):
    if g["type"] == "Polygon":
        return dans(pt, g["coordinates"][0]) and not any(dans(pt, r) for r in g["coordinates"][1:])
    if g["type"] == "MultiPolygon":
        return any(dans(pt, p[0]) and not any(dans(pt, r) for r in p[1:]) for p in g["coordinates"])
    return False


ZONES = [f for f in _lire(DONNEES / "relief/relief_zones_2026.geojson")
         if f["properties"].get("zone") in ("ancienne_chaussee_rehaussee_2025", "ancienne_chaussee_trottoir_par_defaut",
                                            "traversee_bordure_abaissee")]
SURF = _lire(DONNEES / "surfaces/surfaces_2026.geojson")
MARQ = {f["properties"]["id"]: f["properties"] for f in _lire(ICI.parents[2] / "description/base/marquages.geojson")}
IDS = set()
for _f in ("bordures", "surfaces", "ilots", "ponctuels_sol", "marquages"):
    IDS |= {f["properties"]["id"] for f in _lire(ICI.parents[2] / f"description/base/{_f}.geojson")}
IDS |= {f["properties"]["id"] for f in _lire(ICI.parents[6] / "recon/out/paquet_jardin/package/donnees/objets/mobilier.geojson")}
IDS |= {f["properties"]["id"] for f in _lire(ICI.parents[6] / "recon/out/paquet_jardin/package/donnees/objets/arbres.geojson")}


def valide(pt, ob):
    if ob.get("va") is not None:
        v, r = ob["va"]
        return {"valeur": v, "raison": r}
    x, y = pt
    if not (EMPRISE[0] <= x <= EMPRISE[2] and EMPRISE[1] <= y <= EMPRISE[3]):
        return {"valeur": "incertain", "raison": "hors emprise de la description (carré de 300 m) ; élément non daté après 2022"}
    for f in ZONES:
        if dans_geom(pt, f["geometry"]):
            z = f["properties"]["zone"]
            return {"valeur": False, "raison": f"dans la zone de travaux 2025 (relief_zones_2026 : {z}) : l'état 2022 a été remplacé"}
    lien = ob.get("l")
    if lien in MARQ and MARQ[lien].get("etat") == "fantome":
        return {"valeur": False, "raison": f"marquage {lien} effacé en 2025 (etat fantome) : au plus une trace en 2026"}
    for f in SURF:
        p = f["properties"]
        if dans_geom(pt, f["geometry"]):
            if p.get("etat") == "modifie_2025":
                if ob["c"] in ("arbre", "batiment", "cloture", "haie", "massif"):
                    return {"valeur": "incertain", "raison": f"surface {p['id']} ({p['classe']}) modifiée en 2025 : élément conservé ou non"}
                return {"valeur": False, "raison": f"surface {p['id']} ({p['classe']}) modifiée par les travaux 2025 (surfaces_2026 etat modifie_2025)"}
            if p.get("etat") == "construit_2023_2024":
                return {"valeur": False, "raison": f"secteur construit en 2023-2024 ({p['id']}, {p['classe']}), postérieur à l'image"}
            break
    return {"valeur": True, "raison": "hors zones de travaux 2025 et des constructions 2023-2024 : élément présumé inchangé depuis 2022"}


def affiner(D, u, v, mode, r=12):
    """Centroïde de la tache sombre/claire la plus proche de (u, v) dans ±r px (fond = médiane ±3r)."""
    a = np.asarray(D.img, np.float32)
    L = a @ np.array([0.299, 0.587, 0.114], np.float32)
    R = 3 * r
    u0, v0 = int(max(0, u - R)), int(max(0, v - R))
    w = L[v0:int(min(1000, v + R)), u0:int(min(1000, u + R))]
    med = np.median(w)
    yy, xx = np.mgrid[0:w.shape[0], 0:w.shape[1]]
    d = np.hypot(xx + u0 - u, yy + v0 - v)
    if mode == "sombre":
        m = (w < med - max(15, 0.35 * (med - np.percentile(w, 3)))) & (d <= r)
    else:
        m = (w > med + max(20, 0.35 * (np.percentile(w, 97) - med))) & (d <= r)
    if m.sum() < 4:
        return u, v, False
    # composante la plus proche du point donné (croissance depuis le pixel actif le plus proche)
    act = set(zip(*np.nonzero(m)))
    dmin = min(act, key=lambda q: d[q])
    pile, comp = [dmin], {dmin}
    while pile:
        y, x = pile.pop()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                q = (y + dy, x + dx)
                if q in act and q not in comp:
                    comp.add(q)
                    pile.append(q)
    c = np.array(list(comp))
    return float(c[:, 1].mean() + u0 + 0.5), float(c[:, 0].mean() + v0 + 0.5), True


def segment(D, bb, mode="clair"):
    """Segment peint (ou sombre) dans la bbox (u0, v0, u1, v1) : ACP des pixels contrastés -> extrémités."""
    from controles import peinture
    u0, v0, u1, v1 = [int(round(c)) for c in bb]
    sous = D.img.crop((max(0, u0 - 25), max(0, v0 - 25), min(1000, u1 + 25), min(1000, v1 + 25)))
    blanc, jaune = peinture(sous)
    m = blanc | jaune
    ox, oy = max(0, u0 - 25), max(0, v0 - 25)
    ys, xs = np.nonzero(m)
    xs, ys = xs + ox, ys + oy
    k = (xs >= u0) & (xs <= u1) & (ys >= v0) & (ys <= v1)
    xs, ys = xs[k] + 0.5, ys[k] + 0.5
    if len(xs) < 8:
        return None
    P = np.stack([xs, ys], 1)
    c = P.mean(0)
    w, V = np.linalg.eigh(np.cov((P - c).T))
    d = V[:, -1]
    t = (P - c) @ d
    a, b = np.percentile(t, 1), np.percentile(t, 99)
    larg = 4 * np.sqrt(max(w[0], 1e-6))
    return [list(c + a * d), list(c + b * d)], float(larg), int(len(xs))


def vignette(t, u, v, chemin, taille=160, bbox=None):
    s = taille
    u0 = int(min(max(0, u - s / 2), 1000 - s))
    v0 = int(min(max(0, v - s / 2), 1000 - s))
    a, _ = rendre(t, u0, v0, s, s, 2.0, brut=True, titre=True)
    b, _ = rendre(t, u0, v0, s, s, 2.0, brut=False, titre=False)
    can = Image.new("RGB", (a.width + b.width + 6, a.height), (30, 30, 30))
    can.paste(a, (0, 0))
    can.paste(b, (a.width + 6, a.height - b.height))
    dr = ImageDraw.Draw(can)
    M, T = 44, 18
    for ox, oy in ((0, T), (a.width + 6, a.height - b.height)):
        cx, cy = ox + M + (u - u0) * 2, oy + M + (v - v0) * 2
        dr.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], outline=(0, 255, 255), width=2)
        if bbox:
            dr.rectangle([ox + M + (bbox[0] - u0) * 2, oy + M + (bbox[1] - v0) * 2,
                          ox + M + (bbox[2] - u0) * 2, oy + M + (bbox[3] - v0) * 2], outline=(0, 255, 255))
    can.save(chemin, quality=88)


def construire(vignettes=True):
    out, dalles = [], {}
    for n, ob in enumerate(OBS, 1):
        t = ob["t"]
        D = dalles.setdefault(t, Dalle(t))
        u, v = ob["u"], ob["v"]
        meth = "pixel_ortho"
        aff = None
        if ob.get("af"):
            u2, v2, ok = affiner(D, u, v, ob["af"], ob.get("r", 12))
            if ok and np.hypot(u2 - u, v2 - v) <= ob.get("r", 12):
                aff = [round(u2 - u, 1), round(v2 - v, 1)]
                u, v = u2, v2
        segm = None
        if ob.get("seg"):
            r = segment(D, ob["seg"])
            if r:
                segm = r
                (a0, a1), lpx, npx = r
                u, v = (a0[0] + a1[0]) / 2, (a0[1] + a1[1]) / 2
                ob = dict(ob, geom=[a0, a1], bb=ob["seg"])
        x, y = (float(c) for c in D.px_vers_l93([u, v]))
        oid = f"ORTHO-B-{n:03d}"
        q = f"q{int(v >= 500)}{int(u >= 500)}"
        preuve = {"fichier": f"recon/out/paquet_jardin/v2/enrichi/recensement/ortho_B/vues/{t}_{q}_brut.jpg",
                  "vue_description": f"recon/out/paquet_jardin/v2/enrichi/recensement/ortho_B/vues/{t}_{q}_ov.jpg",
                  "pixels_dalle": [round(u, 1), round(v, 1)]}
        if ob.get("bb"):
            preuve["bbox_dalle"] = ob["bb"]
        if ob["s"] != "confirme" or ob.get("pr"):
            f = ICI / "preuves" / f"{oid}_{t}.jpg"
            if vignettes:
                vignette(t, u, v, f, ob.get("vt", 160), ob.get("bb"))
            preuve["fichier"] = f"recon/out/paquet_jardin/v2/enrichi/recensement/ortho_B/preuves/{f.name}"
        attrs = dict(ob.get("a", {}))
        if ob.get("n"):
            attrs["note"] = ob["n"]
        absents = [x for x in ([ob.get("l")] if ob.get("l") else []) + list(attrs.get("liens") or []) if x not in IDS]
        if absents:
            attrs["liens_absents_description_courante"] = absents
        pos = {"l93": [round(x, 2), round(y, 2)], "local": [round(x - O[0], 2), round(y - O[1], 2)],
               "precision_m": ob.get("p", 0.15 if ob.get("af") else 0.25), "methode": "pixel_ortho"}
        if aff:
            pos["affinage_px"] = aff
        if ob.get("geom"):
            pos["geometrie_l93"] = [[round(float(c), 2) for c in D.px_vers_l93(p)] for p in ob["geom"]]
        if segm:
            (a0, a1), lpx, npx = segm
            attrs["longueur_m"] = round(float(np.hypot(a1[0] - a0[0], a1[1] - a0[1])) * PAS, 2)
            attrs["largeur_estimee_m"] = round(lpx * PAS, 2)
            pos["precision_m"] = ob.get("p", 0.1)
            pos["methode"] = "pixel_ortho"
        out.append({
            "id": oid, "source": f"ortho2022:{t}", "date_image": DATE, "classe": ob["c"],
            "sous_type": ob.get("st"), "attributs": attrs, "position": pos,
            "lien_description": ob.get("l"), "statut": ob["s"], "valide_2026": valide((x, y), ob),
            "confiance": ob.get("k", "moyenne"), "preuve": preuve})
    out += automatiques(out, len(out))
    with open(SORTIE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


def automatiques(manuelles, n0):
    """Confirmations automatiques relues sur les vues : marquages « conserve / refait_2025_identique »
    couverts à >= 50 % par de la peinture, arbres dont le point porte une couronne en feuille
    (part verte >= 0,6 dans 1,5 m), non déjà cités par une observation manuelle."""
    deja = set()
    for o in manuelles:
        if o["lien_description"]:
            deja.add(o["lien_description"])
        for k in ("liens", "confirmes"):
            deja.update(o["attributs"].get(k) or [])
    out, n = [], n0
    import glob
    for f in sorted(glob.glob(str(ICI / "controles" / "9*_6*0.json"))):
        r = json.load(open(f, encoding="utf-8"))
        t = r["tuile"]
        D = Dalle(t)
        cand = []
        for m in r["marquages"]:
            if m["id"] in deja or m["etat"] not in ("conserve", "refait_2025_identique"):
                continue
            u, v = m["uv"]
            if not (0 <= u < 1000 and 0 <= v < 1000) or m["blanc"] + m["jaune"] < 0.5:
                continue
            cand.append(("marquage", f"{m['classe']}_{m['type']}", m["id"], u, v,
                         f"peinture présente sur {100 * (m['blanc'] + m['jaune']):.0f} % de l'empreinte décrite (contrôle automatique relu sur les vues)",
                         {"couverture_peinture_2022": round(m["blanc"] + m["jaune"], 2), "etat_description": m["etat"]}))
        for a in r["arbres"]:
            if a["id"] in deja or a["vert"] < 0.6:
                continue
            cand.append(("arbre", a["type"], a["id"], a["uv"][0], a["uv"][1],
                         f"couronne en feuille au point (part verte {a['vert']:.2f} dans 1,5 m ; contrôle automatique relu sur les vues)",
                         {"part_verte_2022": a["vert"], "hauteur_decrite_m": a["h"], "couronne_decrite_m": a["couronne"]}))
        for c, st, lid, u, v, note, at in cand:
            deja.add(lid)
            n += 1
            x, y = (float(q) for q in D.px_vers_l93([u, v]))
            at = dict(at, note=note, verification="automatique")
            q = f"q{int(v >= 500)}{int(u >= 500)}"
            out.append({"id": f"ORTHO-B-{n:03d}", "source": f"ortho2022:{t}", "date_image": DATE, "classe": c,
                        "sous_type": st, "attributs": at,
                        "position": {"l93": [round(x, 2), round(y, 2)], "local": [round(x - O[0], 2), round(y - O[1], 2)],
                                     "precision_m": 0.5 if c == "arbre" else 0.2, "methode": "projection_description"},
                        "lien_description": lid, "statut": "confirme",
                        "valide_2026": valide((x, y), {"c": c, "l": lid}),
                        "confiance": "moyenne",
                        "preuve": {"fichier": f"recon/out/paquet_jardin/v2/enrichi/recensement/ortho_B/vues/{t}_{q}_brut.jpg",
                                   "vue_description": f"recon/out/paquet_jardin/v2/enrichi/recensement/ortho_B/vues/{t}_{q}_ov.jpg",
                                   "pixels_dalle": [round(u, 1), round(v, 1)]}})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-vignettes", action="store_true")
    a = ap.parse_args()
    r = construire(not a.sans_vignettes)
    from collections import Counter
    print(len(r), "observations")
    print(Counter(o["classe"] for o in r))
    print(Counter(o["statut"] for o in r))
