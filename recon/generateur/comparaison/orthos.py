"""Kit multi-orthos de la comparaison v2 : extraits de PLUSIEURS orthos (plusieurs dates, plusieurs résolutions) sur la
MÊME emprise et au MÊME cadrage, pour que le modèle (Claude) fusionne lui-même, en les regardant, la vue générale du
site avec les photos (principe de l'utilisateur, 18/10/2026 : « c'est de la fusion, mais directement dans ton modèle »).
Aucun algorithme ne remplace la lecture : le kit prépare des images bien cadrées, datées et découpées en tuiles natives.

Couches (ordre de lecture ; une couche vide sur l'emprise est notée et sautée) :
- `pcrs2022` : PCRS 5 cm Grenoble-Alpes Métropole (CRAIG, 10/05/2022, dalles locales `decoupe.SOURCES_ORTHO`), gardé
  dès qu'il couvre au moins 50 % de l'emprise (le reste en gris) ;
- `ign2024`, `ign2021`, `ign2018`, `ign2015` : IGN BD ORTHO 20 cm par millésime (WMS Géoplateforme
  `ORTHOIMAGERY.ORTHOPHOTOS<année>`), date de prise de vue lue sur le graphe de mosaïquage (WFS) au centre et aux
  coins de l'emprise ;
- `pleiades2025` : IGN ORTHO-SAT Pléiades 50 cm 2025 (date d'image non publiée) ;
- `irc2024` : BD ORTHO infrarouge fausses couleurs 2024 (végétation en rouge : herbe / pavés / enrobé des îlots) ;
- `planign` : Plan IGN v2, carte courante, en PLAN DE CONTEXTE seulement (`contexte_planign.png` : emprise du site
  élargie à 320 m au moins, 0,6 m/px, échelle où le plan montre les noms des voies et des bâtiments et les sens
  uniques ; à 5-25 cm/px il ne montre que des limites cadastrales).
Licences : PCRS — Licence Ouverte (CRAIG / Grenoble-Alpes Métropole) ; IGN — Licence Ouverte Etalab 2.0. Images
diffusables (aucune photo de tiers).

Produits (sous <site>/orthos/, manifeste `kit.json`) — chaque image entre sans réduction et porte un bandeau avec la
couche, la DATE de prise de vue, le pas, l'emprise et la licence :
- `site_<couche>.png` : vue générale du site, toutes couches au même pas commun (grand côté ≈ 1 050 px) et sur la même
  emprise L93 (nord en haut) : même cadrage d'une couche à l'autre ;
- `centre_<couche>.png` : ZOOM DU CENTRE (zone de conflit, anneau, îlots et passages proches), même règle ; une couche
  plus grossière que le pas commun y est agrandie (bicubique, indiqué dans le bandeau) ;
- `tuiles_natives/<emprise>_<couche>_tNN.png` : tuiles au pas NATIF (1 050 px, recouvrement 20 %) pour les couches plus
  fines que le pas commun (PCRS 5 cm surtout) ;
- `planche_dates_<emprise>_pNN.png` : planches 2 × 2 (quatre dates côte à côte, même cadrage) pour voir d'un coup
  d'œil ce qui change d'une date à l'autre ;
- `brut/<emprise>_<couche>.png` + `.pgw` : extraits au pas natif, sans bandeau (géoréférencés L93).
Les réponses du WMS sont en cache sous <sortie>/_orthos/ (non versionné), par couche, emprise et pas.
"""
import hashlib
import io
import json
import math
import time
import urllib.parse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import dessus as DS
import planches as PL

Image.MAX_IMAGE_PIXELS = None
ETALAB = "Licence Ouverte Etalab 2.0 — IGN, Géoplateforme (data.geopf.fr)"
COTE = 1050             # grand côté des vues « même cadrage » et des tuiles natives (+ bandeau ≤ 1092 px)
BANDEAU = 40
CELLULE = 520           # cellule des planches 2 × 2
COUCHES = (
    {"nom": "pcrs2022", "source": "pcrs", "pas": 0.05, "libelle": "PCRS 5 cm Grenoble-Alpes Métropole (CRAIG)",
     "date": "2022-05-10", "licence": "Licence Ouverte (CRAIG / Grenoble-Alpes Métropole)"},
    {"nom": "ign2024", "couche": "ORTHOIMAGERY.ORTHOPHOTOS2024", "pas": 0.20, "libelle": "IGN BD ORTHO 20 cm 2024",
     "graphe": "ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE-MOSAIQUAGE:graphe_bdortho", "annee": 2024},
    {"nom": "pleiades2025", "couche": "ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2025", "pas": 0.50,
     "libelle": "IGN ORTHO-SAT Pléiades 50 cm 2025", "annee": 2025,
     "note_date": "2025, date d'image non publiée (couche non interrogeable, pas de graphe de mosaïquage)"},
    {"nom": "ign2021", "couche": "ORTHOIMAGERY.ORTHOPHOTOS2021", "pas": 0.20, "libelle": "IGN BD ORTHO 20 cm 2021",
     "graphe": "ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE.2021-2023:graphe_bdortho", "annee": 2021},
    {"nom": "ign2018", "couche": "ORTHOIMAGERY.ORTHOPHOTOS2018", "pas": 0.20, "libelle": "IGN BD ORTHO 20 cm 2018",
     "graphe": "ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE.2016-2020:graphe_bdortho", "annee": 2018},
    {"nom": "ign2015", "couche": "ORTHOIMAGERY.ORTHOPHOTOS2015", "pas": 0.20, "libelle": "IGN BD ORTHO 2015",
     "graphe": "ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE.2011-2015:graphe_bdortho", "annee": 2015},
    {"nom": "irc2024", "couche": "ORTHOIMAGERY.ORTHOPHOTOS.IRC.2024", "pas": 0.20,
     "libelle": "IGN BD ORTHO IRC 20 cm 2024 (infrarouge fausses couleurs : végétation en rouge)",
     "graphe": "ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE-MOSAIQUAGE:graphe_bdortho", "annee": 2024},
    {"nom": "planign", "couche": "GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2", "pas": 0.6, "contexte": True,
     "libelle": "Plan IGN v2 (noms des voies et des bâtiments, sens uniques)",
     "note_date": "carte courante (consultée le jour de l'extraction)"},
)
CONTEXTE_M = 320.0      # côté minimal de l'emprise du plan de contexte (Plan IGN lisible à 0,6 m/px)


# ------------------------------------------------------------------------------------------------ sources
def date_graphe(graphe, x, y, annee=None, cache=None):
    """Dates de prise de vue (AAAA-MM-JJ) des polygones du graphe de mosaïquage (WFS) qui contiennent (x, y) L93 ;
    celles de l'année `annee` d'abord. Liste vide si le service ne répond pas. Réponses en cache (dates.json)."""
    from shapely.geometry import Point, shape
    cle = f"{graphe}|{x:.0f}|{y:.0f}|{annee}"
    fc = Path(cache) / "dates_graphes.json" if cache else None
    memo = json.loads(fc.read_text(encoding="utf-8")) if fc and fc.exists() else {}
    if cle in memo:
        return memo[cle]
    p = {"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature", "TYPENAMES": graphe, "SRSNAME": "EPSG:2154",
         "BBOX": f"{x - 3:.1f},{y - 3:.1f},{x + 3:.1f},{y + 3:.1f},EPSG:2154", "OUTPUTFORMAT": "application/json",
         "COUNT": 50}
    try:
        d = json.loads(DS._get(DS.WFS + "?" + urllib.parse.urlencode(p), timeout=60)[0])
    except Exception:  # service indisponible : date inconnue (pas mise en cache)
        return []
    out = []
    for f in d.get("features", []):
        try:
            if not shape(f["geometry"]).contains(Point(x, y)):
                continue
        except Exception:  # géométrie illisible
            continue
        dv = str(f["properties"].get("date_vol") or "")[:10]
        if dv and dv not in out:
            out.append(dv)
    if annee:
        out = sorted(out, key=lambda v: (v[:4] != str(annee), v))
    if fc:
        memo[cle] = out
        fc.parent.mkdir(parents=True, exist_ok=True)
        fc.write_text(json.dumps(memo, ensure_ascii=False, indent=0), encoding="utf-8")
    return out


def wms(couche, e_l93, pas, cache):
    """Extrait WMS (PNG) d'une couche sur l'emprise L93 au pas donné ; cache par (couche, emprise, pas)."""
    x0, y0, x1, y1 = e_l93
    cle = hashlib.sha256(json.dumps([round(v, 2) for v in e_l93] + [pas, couche]).encode()).hexdigest()[:14]
    cache = Path(cache)
    f = cache / f"wms_{cle}.png"
    if f.exists():
        return Image.open(f).convert("RGB")
    W, H = int(round((x1 - x0) / pas)), int(round((y1 - y0) / pas))
    im = Image.new("RGB", (W, H), (255, 255, 255))
    bloc = 2000
    for j0 in range(0, H, bloc):
        for i0 in range(0, W, bloc):
            w, h = min(bloc, W - i0), min(bloc, H - j0)
            bx0, by1 = x0 + i0 * pas, y1 - j0 * pas
            p = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": couche, "STYLES": "",
                 "FORMAT": "image/png", "CRS": "EPSG:2154", "WIDTH": w, "HEIGHT": h,
                 "BBOX": f"{bx0:.3f},{by1 - h * pas:.3f},{bx0 + w * pas:.3f},{by1:.3f}"}
            b, ct = DS._get(DS.WMS + "?" + urllib.parse.urlencode(p))
            if not ct.startswith("image"):
                raise RuntimeError(f"WMS {couche} : " + b[:200].decode("utf-8", "replace"))
            t = Image.open(io.BytesIO(b))
            if t.mode in ("RGBA", "LA", "P"):
                t = t.convert("RGBA")
                fond = Image.new("RGBA", t.size, (255, 255, 255, 255))
                t = Image.alpha_composite(fond, t)
            im.paste(t.convert("RGB"), (i0, j0))
    cache.mkdir(parents=True, exist_ok=True)
    im.save(f)
    return im


def part_vide(im):
    """Part des pixels vides (blanc ou noir uniforme : hors couverture de la couche)."""
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    blanc = (a >= 250).all(axis=2)
    noir = (a <= 4).all(axis=2)
    return float((blanc | noir).mean())


def extraire(c, e_l93, cache):
    """Extrait d'une couche au pas natif : (image PIL, métadonnées) ou (None, motif)."""
    x0, y0, x1, y1 = e_l93
    if c.get("source") == "pcrs":
        import decoupe
        motif = decoupe.SOURCES_ORTHO["pcrs2022"][0]
        if not decoupe.dalles(motif):
            return None, "dalles PCRS absentes"
        img, vu = decoupe.mosaique(motif, x0, y0, x1, y1, c["pas"])
        cv = float(vu.mean())
        if cv < 0.5:
            return None, f"PCRS : {cv:.0%} de l'emprise couverte (< 50 %)"
        img[~vu] = (128, 128, 128)
        return Image.fromarray(img), {"date": c["date"], "couverture": round(cv, 3), "source": motif,
                                      "licence": c["licence"]}
    try:
        im = wms(c["couche"], e_l93, c["pas"], cache)
    except Exception as e:  # service indisponible ou couche refusée
        return None, f"WMS indisponible ({str(e)[:120]})"
    v = part_vide(im)
    if v > 0.85 and c["nom"] != "planign":
        return None, f"couche vide sur l'emprise ({v:.0%} de pixels vides)"
    meta = {"source": f"{DS.WMS} {c['couche']}", "licence": ETALAB, "couverture": round(1.0 - v, 3)}
    if c.get("graphe"):
        pts = [((x0 + x1) / 2, (y0 + y1) / 2), (x0 + 1, y0 + 1), (x1 - 1, y0 + 1), (x0 + 1, y1 - 1), (x1 - 1, y1 - 1)]
        dates = []
        for k, (x, y) in enumerate(pts):
            dd = date_graphe(c["graphe"], x, y, c.get("annee"), cache)
            dd = [v_ for v_ in dd if v_[:4] == str(c.get("annee"))] or dd
            if k == 0:
                meta["date"] = dd[0] if dd else None
            dates += [v_ for v_ in dd[:1] if v_ not in dates]
        meta["dates_emprise"] = sorted(dates)
        if not meta.get("date"):
            meta["date"] = str(c.get("annee"))
            meta["note_date"] = "date de vol introuvable sur le graphe de mosaïquage : année de la couche"
    else:
        meta["date"] = str(c.get("annee")) if c.get("annee") else None
        meta["note_date"] = c.get("note_date")
    return im, meta


# ------------------------------------------------------------------------------------------------ images
def _bandeau(im, lignes, couleur=(22, 22, 26)):
    """Image + bandeau de texte au-dessus (les pixels de l'image ne sont pas touchés)."""
    W, H = im.size
    out = Image.new("RGB", (W, H + BANDEAU), couleur)
    d = ImageDraw.Draw(out)
    for k, t in enumerate(lignes[:2]):
        d.text((5, 3 + 18 * k), t, fill=(240, 240, 240) if k == 0 else (200, 200, 200), font=PL.police(13 if k == 0 else 12))
    out.paste(im, (0, BANDEAU))
    return out


def _texte_date(meta, c):
    d = meta.get("date") or "date inconnue"
    de = meta.get("dates_emprise") or []
    if len(de) > 1:
        d += " (mosaïque : " + ", ".join(de) + ")"
    if meta.get("note_date") and c["nom"] != "pcrs2022":
        d += " — " + meta["note_date"]
    return d


def _pgw(f, pas, x0, y1):
    Path(f).with_suffix(".pgw").write_text("%.6f\n0.0\n0.0\n%.6f\n%.4f\n%.4f\n" % (pas, -pas, x0 + pas / 2, y1 - pas / 2))


def _boite_l93(ancrage, e_loc):
    """Boîte L93 alignée sur les axes (nord en haut) qui contient l'emprise e_loc du repère du modèle."""
    x0, y0, x1, y1 = e_loc
    xs, ys = ancrage.vers_l93(np.array([x0, x1, x0, x1], float), np.array([y0, y0, y1, y1], float))
    return (math.floor(float(np.min(xs))), math.floor(float(np.min(ys))), math.ceil(float(np.max(xs))),
            math.ceil(float(np.max(ys))))


def _contexte(c, b, org, site_nom, dossier, cache, absentes, journal):
    """Plan de contexte (Plan IGN) : emprise du site élargie à CONTEXTE_M de côté au moins, même centre, pas propre
    (le style du Plan IGN dépend de l'échelle : les noms n'apparaissent qu'à ≈ 0,6 m/px)."""
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    demi = max(CONTEXTE_M, b[2] - b[0], b[3] - b[1]) / 2
    e = (math.floor(cx - demi), math.floor(cy - demi), math.ceil(cx + demi), math.ceil(cy + demi))
    im, meta = extraire(c, e, cache)
    if im is None:
        absentes.setdefault(c["nom"], {}).update({"contexte": meta})
        return None
    f = Path(dossier) / f"contexte_{c['nom']}.png"
    es = [round(e[0] - org[0]), round(e[1] - org[1]), round(e[2] - org[0]), round(e[3] - org[1])]
    _bandeau(im, [f"{c['libelle']} — {meta.get('note_date') or ''}",
                  f"{site_nom} — contexte : x {es[0]} à {es[2]} m, y {es[1]} à {es[3]} m (repère du site), nord en haut, "
                  f"{c['pas'] * 100:.0f} cm/px — {meta['licence'][:40]}"]).save(f)
    _pgw(Path(dossier) / "brut" / f"contexte_{c['nom']}.png", c["pas"], e[0], e[3])
    im.save(Path(dossier) / "brut" / f"contexte_{c['nom']}.png")
    journal(f"    orthos contexte {c['nom']} : {im.size[0]} × {im.size[1]} px")
    return {"nom": c["nom"], "libelle": c["libelle"], "image": f.name, "emprise_l93": list(e), "emprise_site": es,
            "pas_m": c["pas"], "licence": meta["licence"], "source": meta["source"], "note_date": meta.get("note_date")}


def kit(site_nom, zones, ancrage, dossier, cache, couches=None, journal=print):
    """Kit multi-orthos du site ; renvoie le manifeste (écrit dans <dossier>/kit.json)."""
    import decoupe
    dossier = Path(dossier)
    for sd in ("", "brut", "tuiles_natives"):
        (dossier / sd).mkdir(parents=True, exist_ok=True)
    emp = DS.emprises(zones)
    org = ancrage.vers_l93(0.0, 0.0)
    org = (float(org[0]), float(org[1]))
    choix = [c for c in COUCHES if not couches or c["nom"] in couches]
    man = {"schema": "comparaison_orthos/0.1", "site": site_nom, "genere_le": time.strftime("%Y-%m-%d %H:%M"),
           "principe": "même emprise L93 et même cadrage (nord en haut) pour toutes les couches ; date de prise de vue "
                       "sur chaque image ; tuiles natives pour les couches plus fines que le pas commun ; lecture et "
                       "fusion par le modèle (aucune fusion algorithmique)",
           "repere_site": "x, y du site = L93 − origine " + str([round(v, 2) for v in org]),
           "emprises": [], "couches_absentes": []}
    absentes = {}
    for nom_e in ("centre", "site"):
        if nom_e not in emp:
            continue
        b = _boite_l93(ancrage, emp[nom_e])
        Wm, Hm = b[2] - b[0], b[3] - b[1]
        pas_c = max(0.05, max(Wm, Hm) / COTE)
        Wc, Hc = int(round(Wm / pas_c)), int(round(Hm / pas_c))
        ent = {"nom": nom_e, "emprise_l93": list(b), "emprise_site": [round(b[0] - org[0], 2), round(b[1] - org[1], 2),
                                                                         round(b[2] - org[0], 2), round(b[3] - org[1], 2)],
               "pas_commun_m": round(pas_c, 4), "taille_commune_px": [Wc, Hc], "couches": []}
        cellules = []
        for c in choix:
            if c.get("contexte"):
                if nom_e == "site":
                    man["contexte"] = _contexte(c, b, org, site_nom, dossier, cache, absentes, journal)
                continue
            im, meta = extraire(c, b, cache)
            if im is None:
                absentes.setdefault(c["nom"], {}).update({nom_e: meta})
                journal(f"    orthos {nom_e} {c['nom']} : absente ({meta})")
                continue
            f_b = dossier / "brut" / f"{nom_e}_{c['nom']}.png"
            im.save(f_b)
            _pgw(f_b, c["pas"], b[0], b[3])
            k = c["pas"] / pas_c
            imc = im.resize((Wc, Hc), Image.LANCZOS if k < 1 else Image.BICUBIC)
            dtxt = _texte_date(meta, c)
            mode = (f"agrandie ×{k:.1f} depuis {c['pas'] * 100:.0f} cm/px" if k > 1.05 else
                    f"réduite depuis {c['pas'] * 100:.0f} cm/px (voir tuiles natives)" if k < 0.95 else "pas natif")
            l1 = f"{c['libelle']} — PRISE DE VUE {dtxt}"
            l2 = (f"{site_nom} — {'ZOOM CENTRE' if nom_e == 'centre' else 'vue générale'} — x {ent['emprise_site'][0]:.0f} à "
                  f"{ent['emprise_site'][2]:.0f} m, y {ent['emprise_site'][1]:.0f} à {ent['emprise_site'][3]:.0f} m (repère du site), "
                  f"nord en haut — {pas_c * 100:.1f} cm/px ({mode}) — {meta['licence'][:40]}")
            f_c = dossier / f"{nom_e}_{c['nom']}.png"
            _bandeau(imc, [l1, l2]).save(f_c)
            tuiles = []
            if c["pas"] < 0.8 * pas_c:
                W, H = im.size
                for t, (px0, py0, px1, py1) in enumerate(decoupe.grille(W, H, COTE, 0.2)):
                    lx0, ly1 = b[0] - org[0] + px0 * c["pas"], b[3] - org[1] - py0 * c["pas"]
                    lx1, ly0 = b[0] - org[0] + px1 * c["pas"], b[3] - org[1] - py1 * c["pas"]
                    ft = dossier / "tuiles_natives" / f"{nom_e}_{c['nom']}_t{t:02d}.png"
                    _bandeau(im.crop((px0, py0, px1, py1)),
                             [f"{c['libelle']} — PRISE DE VUE {dtxt} — {c['pas'] * 100:.0f} cm/px natif",
                              f"{site_nom} — {nom_e} — tuile t{t:02d} : x {lx0:.1f} à {lx1:.1f} m, y {ly0:.1f} à {ly1:.1f} m "
                              "(repère du site), nord en haut"]).save(ft)
                    tuiles.append({"fichier": f"tuiles_natives/{ft.name}", "boite_px": [px0, py0, px1, py1],
                                   "site": [round(lx0, 2), round(ly0, 2), round(lx1, 2), round(ly1, 2)]})
            ent["couches"].append({"nom": c["nom"], "libelle": c["libelle"], "date": meta.get("date"),
                                   "dates_emprise": meta.get("dates_emprise"), "note_date": meta.get("note_date"),
                                   "pas_natif_m": c["pas"], "couverture": meta.get("couverture"), "licence": meta["licence"],
                                   "source": meta["source"], "image": f_c.name, "brut": f"brut/{f_b.name}",
                                   "tuiles_natives": tuiles})
            dcourt = (meta.get("date") or "date inconnue") + (" (mosaïque)" if len(meta.get("dates_emprise") or []) > 1 else "")
            cellules.append((imc, f"{c['nom']} — {dcourt}"[:60]))
            journal(f"    orthos {nom_e} {c['nom']} : {dtxt} ; {len(tuiles)} tuiles natives")
        # planches 2 × 2 (même cadrage, quatre dates)
        pages = []
        for p0 in range(0, len(cellules), 4):
            lot = cellules[p0:p0 + 4]
            kk = min(CELLULE / Wc, CELLULE / Hc)
            w, h = max(1, int(Wc * kk)), max(1, int(Hc * kk))
            pl = Image.new("RGB", (2 * w + 8, 2 * (h + 22) + 8 + 24), (22, 22, 26))
            d = ImageDraw.Draw(pl)
            d.text((5, 4), f"{site_nom} — {nom_e} — même emprise, même cadrage, nord en haut ({Wm} × {Hm} m ; "
                           f"{Wm / w * 100:.0f} cm/px) — lire les images seules pour le détail", fill=(235, 235, 235),
                   font=PL.police(12))
            for q, (imc, lg) in enumerate(lot):
                x, y = (q % 2) * (w + 8), 24 + (q // 2) * (h + 22 + 8)
                d.text((x + 4, y + 3), lg, fill=(255, 230, 120), font=PL.police(13))
                pl.paste(imc.resize((w, h), Image.LANCZOS), (x, y + 22))
            f_p = dossier / f"planche_dates_{nom_e}_p{p0 // 4 + 1:02d}.png"
            pl.save(f_p)
            pages.append(f_p.name)
        ent["planches_dates"] = pages
        man["emprises"].append(ent)
    man["couches_absentes"] = [{"nom": k, "motifs": v} for k, v in absentes.items()]
    (dossier / "kit.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    return man


def meilleure(man, emprise):
    """Couche la plus fine et la plus récente disponible pour une emprise (fond des plans d'index)."""
    for e in man.get("emprises", []):
        if e["nom"] == emprise and e["couches"]:
            ordre = {c["nom"]: k for k, c in enumerate(COUCHES)}
            return min(e["couches"], key=lambda c: (c["pas_natif_m"], ordre.get(c["nom"], 99))), e
    return None, None
