#!/usr/bin/env python3
"""Construit les faces de panneaux (PNG RGBA) de la librairie : assets/specs/panneaux/faces/<code>.png

Sources
  - SVG de Wikimedia Commons (catégories « <code> (road sign, France) ») : le manifeste
    faces/sources.json donne pour chaque face l'URL, l'empreinte SHA-1, l'auteur et la licence.
    Les SVG sont mis en cache dans data/raw/assets_src/svg/ (non versionné) ; s'ils manquent, ils
    sont téléchargés poliment (User-Agent explicite, une requête à la fois, respect de Retry-After).
  - Compositions « maison » (texte vectoriel, fonds) écrites dans svg_maison/ par ce script :
    panneaux de direction D21a, plaque de rue, panneau à chevrons de chantier, B2b sur fond jaune.

Sortie : PNG RGBA (fond transparent hors du panneau), côté le plus long = 1024 px
(2048 px pour les grands formats : D21a), espace sRGB. La face couvre exactement le contour
physique du panneau (cotes en mm dans sources.json et ../panneaux.json) : à plaquer en UV 0-1
sur la face avant (+Y) d'une plaque aux cotes indiquées.

Usage : python3 assets/specs/panneaux/construire_faces.py [--seulement B1,AB3a] [--hors-ligne]
Dépendances : cairosvg, Pillow, numpy (pip install cairosvg pillow numpy).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import colorsys

import cairosvg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
CACHE_SVG = RACINE / "data/raw/assets_src/svg"
FACES = ICI / "faces"
SVG_MAISON = ICI / "svg_maison"
MANIFESTE = FACES / "sources.json"
UA = "ClaudeCode-RoadCreation/1.0 (simulateur ADAS Meylan ; faces de panneaux FR ; contact : propriétaire du dépôt)"

# Polices : la police réglementaire (alphabets L1/L4 de l'IISR) n'est pas libre ; on utilise
# DejaVu Sans Bold avec une compression horizontale calée sur les photos du site. Sur le PC,
# remplacer font-family dans svg_maison/*.svg par la police réglementaire si elle est disponible.
POLICE_TTF = [Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
              Path("C:/Windows/Fonts/DejaVuSans-Bold.ttf")]
POLICE_SVG = "DejaVu Sans"
HAUTEUR_CAPITALE = 0.729  # hauteur des capitales de DejaVu Sans Bold en fraction du corps

# Palette de référence (sRGB indicatif des teintes RAL usuelles de la signalisation française ;
# la conformité réglementaire est définie par les coordonnées chromatiques de la NF EN 12899-1).
PALETTE = {
    "rouge": "#C1121C",   # ≈ RAL 3020 rouge signalisation
    "bleu": "#005387",    # ≈ RAL 5017 bleu signalisation
    "blanc": "#F2F2F2",   # ≈ RAL 9016 blanc signalisation (albédo de film rétroréfléchissant)
    "noir": "#1E1E1E",    # ≈ RAL 9017 noir signalisation
    "jaune": "#F7B500",   # ≈ RAL 1023 jaune signalisation (temporaire, pictogrammes)
    "vert": "#308446",    # ≈ RAL 6024 vert signalisation
}
NOIR, BLANC, ROUGE, BLEU, JAUNE = (PALETTE[k] for k in ("noir", "blanc", "rouge", "bleu", "jaune"))


def _police():
    for p in POLICE_TTF:
        if p.exists():
            return ImageFont.truetype(str(p), 1000)
    raise SystemExit("Police DejaVuSans-Bold.ttf introuvable (installer fonts-dejavu)")


def largeur_texte_mm(texte: str, hc_mm: float) -> float:
    """Largeur d'encre (mm) du texte en DejaVu Sans Bold pour une hauteur de capitale hc_mm."""
    b = _police().getbbox(texte)
    corps = hc_mm / HAUTEUR_CAPITALE
    return (b[2] - b[0]) / 1000.0 * corps


def texte_svg(texte, x, y_base, hc, couleur, largeur_cible=None, ancre="start"):
    """Élément <text> : hauteur de capitale hc (mm), compression horizontale pour tenir largeur_cible."""
    corps = hc / HAUTEUR_CAPITALE
    sx = 1.0
    if largeur_cible:
        sx = min(1.0, largeur_cible / largeur_texte_mm(texte, hc))
    return (f'<text transform="translate({x:.1f},{y_base:.1f}) scale({sx:.4f},1)" '
            f'font-family="{POLICE_SVG}" font-weight="bold" font-size="{corps:.2f}" '
            f'text-anchor="{ancre}" fill="{couleur}">{texte}</text>')


# ---------------------------------------------------------------- compositions maison
def svg_d21a(largeur, hauteur, lignes, pointe=0.45):
    """Panneau de direction D21a (fond blanc, listel noir, pointe à droite). lignes =
    [(texte, hc_mm, y_base_mm, largeur_cible_mm)] ; cotes en mm."""
    W, H = largeur, hauteur
    p = pointe * H
    m, e = 6.0, 9.0          # marge blanche extérieure, épaisseur du listel noir
    r = 22.0                 # rayon des angles côté talon

    def contour(d):
        # rectangle à angles arrondis à gauche + pointe à droite, rétréci de d
        x0, y0, x1, y1 = d, d, W - d * 1.9, H - d
        rr = max(r - d, 2)
        return (f"M{x0 + rr},{y0} L{x1 - p + d * 0.4},{y0} L{x1},{H / 2} L{x1 - p + d * 0.4},{y1} "
                f"L{x0 + rr},{y1} A{rr},{rr} 0 0 1 {x0},{y1 - rr} L{x0},{y0 + rr} "
                f"A{rr},{rr} 0 0 1 {x0 + rr},{y0} Z")
    x_gauche = m + e + 0.95 * max(hc for _, hc, _, _ in lignes)   # texte aligné à gauche
    t = "".join(texte_svg(tx, x_gauche, yb, hc, NOIR, lc) for tx, hc, yb, lc in lignes)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">'
            f'<path d="{contour(0)}" fill="{BLANC}"/>'
            f'<path d="{contour(m)}" fill="{NOIR}"/>'
            f'<path d="{contour(m + e)}" fill="{BLANC}"/>{t}</svg>')


def svg_plaque_rue():
    """Plaque de nom de rue de Meylan (relevé photo 2024-08 : bord blanc, fond bleu marine, capitales blanches).
    Teinte bleu marine observée (plaque communale, hors palette réglementaire)."""
    W, H, r = 530, 270, 22
    marine = "#233A7E"
    t = (texte_svg("AVENUE", W / 2, 108, 52, BLANC, 360, "middle")
         + texte_svg("DE", W / 2, 158, 24, BLANC, None, "middle")
         + texte_svg("VERDUN", W / 2, 228, 52, BLANC, 360, "middle"))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">'
            f'<rect x="0" y="0" width="{W}" height="{H}" rx="{r}" fill="{BLANC}"/>'
            f'<rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="{r - 7}" fill="{marine}"/>{t}</svg>')


def svg_chevrons(W=1000, H=350, n=3, vers_gauche=True):
    """Panneau à chevrons rouges et blancs de déport de chantier (type K8)."""
    pas = W / n
    ep = pas / 2
    poly = []
    for i in range(-1, n + 2):
        x = i * pas
        # chevron pointe à gauche : sommet à mi-hauteur
        pts = [(x + ep * 0.9, 0), (x + ep * 0.9 + ep, 0), (x + ep, H / 2), (x + ep * 0.9 + ep, H),
               (x + ep * 0.9, H), (x, H / 2)]
        if not vers_gauche:
            pts = [(W - a, b) for a, b in pts]
        poly.append('<polygon points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) + f'" fill="{ROUGE}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">'
            f'<defs><clipPath id="c"><rect x="0" y="0" width="{W}" height="{H}" rx="12"/></clipPath></defs>'
            f'<g clip-path="url(#c)"><rect x="0" y="0" width="{W}" height="{H}" fill="{BLANC}"/>'
            + "".join(poly) + "</g></svg>")


def svg_c13a_portrait(W=250, H=400):
    """C13a « impasse » au format portrait observé sur le candélabre n° 0456 (photo 2026-07-28 ded07efa) :
    fond bleu à listel blanc, barre rouge cernée de blanc, fût blanc."""
    lb = 9   # listel blanc
    rw, rh, ry = 0.40 * W, 0.22 * H, 0.13 * H
    sw = 0.18 * W
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">'
            f'<rect x="0" y="0" width="{W}" height="{H}" rx="14" fill="{BLANC}"/>'
            f'<rect x="{lb}" y="{lb}" width="{W - 2 * lb}" height="{H - 2 * lb}" rx="8" fill="{BLEU}"/>'
            f'<rect x="{(W - sw) / 2}" y="{ry + rh - 2}" width="{sw}" height="{0.87 * H - ry - rh}" fill="{BLANC}"/>'
            f'<rect x="{(W - rw) / 2 - 6}" y="{ry - 6}" width="{rw + 12}" height="{rh + 12}" fill="{BLANC}"/>'
            f'<rect x="{(W - rw) / 2}" y="{ry}" width="{rw}" height="{rh}" fill="{ROUGE}"/></svg>')


MAISON = {
    "C13a_portrait": svg_c13a_portrait,
    "D21a_la_reviree_college": lambda: svg_d21a(1100, 360, [("LA REVIRÉE", 80, 166, 713),
                                                              ("Collège L. Terray", 66, 298, 802)]),
    "D21a_commerces_reviree": lambda: svg_d21a(1150, 215, [("Commerces de LA REVIREE", 62.5, 140, 987)]),
    "plaque_rue_avenue_de_verdun": svg_plaque_rue,
    "K8_chevrons": svg_chevrons,
}


# ---------------------------------------------------------------- téléchargement poli
def telecharger(url: str, dest: Path, sha1: str | None, attente_max: int = 120):
    """Téléchargement poli ; abandonne (SystemExit) si Wikimedia impose une attente > attente_max s."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for essai in range(8):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503):
                raise
            ra = e.headers.get("Retry-After")
            attente = int(ra) + 5 if ra and ra.isdigit() else 60 * (essai + 1)
            if attente > attente_max:
                raise SystemExit(f"limite de débit (Retry-After {attente} s) pour {url}")
            print(f"  HTTP {e.code} : attente {attente} s (limite de débit Wikimedia)")
            time.sleep(attente)
    else:
        raise SystemExit(f"échec du téléchargement {url}")
    if sha1 and hashlib.sha1(data).hexdigest() != sha1:
        print(f"  ATTENTION : empreinte différente pour {dest.name} (fichier Commons modifié depuis ?)")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    time.sleep(5)


# ---------------------------------------------------------------- rasterisation
def svg_vers_png(svg: bytes, cote_px: int, viewbox: list | None = None) -> Image.Image:
    s = svg.decode("utf-8")
    if viewbox:  # recadrage (ex. AB3a sans son panonceau M9c)
        vb = " ".join(f"{v:g}" for v in viewbox)
        s = re.sub(r'viewBox="[^"]*"', f'viewBox="{vb}"', s, count=1)
        s = re.sub(r'(<svg[^>]*?)\swidth="[^"]*"', r"\1", s, count=1)
        s = re.sub(r'(<svg[^>]*?)\sheight="[^"]*"', r"\1", s, count=1)
        s = s.replace("<svg", f'<svg width="{viewbox[2]}" height="{viewbox[3]}"', 1)
    m = re.search(r'viewBox="\s*([-\d.e]+)[\s,]+([-\d.e]+)[\s,]+([-\d.e]+)[\s,]+([-\d.e]+)', s)
    if not m:  # SVG sans viewBox : rendu proportionnel puis mise à l'échelle
        im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=s.encode("utf-8"), output_width=cote_px))).convert("RGBA")
        return a_l_echelle(im, cote_px)
    w, h = float(m.group(3)), float(m.group(4))
    if w >= h:
        ow, oh = cote_px, round(cote_px * h / w)
    else:
        ow, oh = round(cote_px * w / h), cote_px
    png = cairosvg.svg2png(bytestring=s.encode("utf-8"), output_width=ow, output_height=oh)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def fond_carre(face: Image.Image, couleur: str, rapport: float, cote_px: int) -> Image.Image:
    """Pose une face (disque) sur un fond carré de couleur à angles arrondis (signalisation temporaire)."""
    k = 4
    N = cote_px * k
    fond = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    ImageDraw.Draw(fond).rounded_rectangle((0, 0, N - 1, N - 1), radius=int(N * 0.04), fill=couleur)
    fond = fond.resize((cote_px, cote_px), Image.LANCZOS)
    d = round(cote_px * rapport)
    f = face.resize((d, d), Image.LANCZOS)
    o = (cote_px - d) // 2
    fond.alpha_composite(f, (o, o))
    return fond


def _hex(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32)


def _classe(rgb):
    """Classe une couleur dominante dans la palette (teinte/saturation/valeur)."""
    r, g, b = (rgb / 255.0)
    mx, mn = max(r, g, b), min(r, g, b)
    v, sat = mx, (0 if mx == 0 else (mx - mn) / mx)
    if sat < 0.25:
        return "blanc" if v > 0.75 else ("noir" if v < 0.35 else None)
    h = colorsys.rgb_to_hsv(r, g, b)[0] * 360
    if h < 15 or h >= 330:
        return "rouge"
    if h < 70:
        return "jaune"
    if h < 170:
        return "vert"
    if h < 260:
        return "bleu"
    return None


def normaliser_couleurs(im: Image.Image, retirer_contour_noir: bool) -> Image.Image:
    """Remplace les aplats des dessins Commons (teintes hétérogènes : #FF0000, #EA190E, #0000FF...)
    par la palette de référence, en conservant l'anticrénelage : chaque pixel est projeté sur le
    segment entre les deux couleurs dominantes les plus proches, puis réinterpolé entre leurs
    remplaçantes. Option : supprime le filet noir de dessin qui entoure certains panneaux
    (absent des panneaux réels, dont le bord est le listel blanc)."""
    a = np.asarray(im.convert("RGBA")).astype(np.float32)
    rgb, al = a[..., :3], a[..., 3]
    opaque = rgb[al > 250].astype(np.uint8)
    cols, cnt = np.unique(opaque, axis=0, return_counts=True)
    dom = [c for c, n in zip(cols, cnt) if n > 0.003 * cnt.sum()]
    src, dst = [], []
    for c in dom:
        k = _classe(c.astype(np.float32))
        src.append(c.astype(np.float32))
        dst.append(_hex(PALETTE[k]) if k else c.astype(np.float32))
    src, dst = np.array(src), np.array(dst)
    P = rgb.reshape(-1, 3)
    best_d = np.full(len(P), np.inf, dtype=np.float32)
    out = P.copy()
    n = len(src)
    paires = [(i, j) for i in range(n) for j in range(i + 1, n)] or [(0, 0)]
    for i, j in paires:
        seg = src[j] - src[i]
        L2 = float(seg @ seg) or 1.0
        t = np.clip(((P - src[i]) @ seg) / L2, 0, 1)
        proj = src[i] + t[:, None] * seg
        d = np.sum((P - proj) ** 2, axis=1)
        m = d < best_d
        best_d[m] = d[m]
        out[m] = dst[i] + t[m, None] * (dst[j] - dst[i])
    rgb2 = out.reshape(rgb.shape)
    if retirer_contour_noir:
        H, W = al.shape
        r = max(2, round(0.012 * max(H, W)))
        m = np.pad((al > 128).astype(np.uint8) * 255, r + 1)   # marge transparente : la forme touche le cadre
        masque = np.asarray(Image.fromarray(m).filter(ImageFilter.MinFilter(2 * r + 1)))[r + 1:-r - 1, r + 1:-r - 1]
        bord = (masque == 0) & (al > 0)
        sombre = rgb.max(axis=2) < 110
        al = al.copy()
        al[bord & sombre] = 0
        # demi-teintes du filet : ramenées au blanc du listel
        demi = bord & ~sombre & (rgb.min(axis=2) < 200) & (np.abs(rgb[..., 0] - rgb[..., 2]) < 30)
        rgb2[demi] = _hex(PALETTE["blanc"])
    res = np.dstack([np.clip(rgb2, 0, 255), al]).astype(np.uint8)
    return Image.fromarray(res, "RGBA")


def recadrer(im: Image.Image, frac):
    """Recadrage en fractions [x0, y0, x1, y1] de l'image source (ex. AB3a sans son panonceau M9c)."""
    if not frac:
        return im
    W, H = im.size
    return im.crop((round(frac[0] * W), round(frac[1] * H), round(frac[2] * W), round(frac[3] * H)))


def a_l_echelle(im: Image.Image, cote_px: int) -> Image.Image:
    W, H = im.size
    k = cote_px / max(W, H)
    return im.resize((max(1, round(W * k)), max(1, round(H * k))), Image.LANCZOS)


def construire(entree: dict, hors_ligne: bool) -> Image.Image:
    code, cote = entree["code"], entree["px"]
    if entree["source"] == "maison":
        svg = MAISON[entree["generateur"]]().encode("utf-8")
        SVG_MAISON.mkdir(parents=True, exist_ok=True)
        (SVG_MAISON / f"{code}.svg").write_bytes(svg)
        return svg_vers_png(svg, cote)
    if entree["source"] == "composition":
        base = next(e for e in json.loads(MANIFESTE.read_text())["faces"] if e["code"] == entree["base"])
        disque = construire(base, hors_ligne)
        return fond_carre(disque, entree["couleur_fond"], entree["rapport_disque"], cote)
    # Wikimedia : SVG original de préférence (rasterisé ici) ; à défaut, rendu PNG 1280 px de
    # Wikimedia (même fichier, rasterisé par le serveur Commons), recadré puis réduit.
    svg = CACHE_SVG / entree["fichier_cache"]
    png = CACHE_SVG / "thumbs1280" / entree["fichier_cache"].replace(".svg", "_1280.png")
    if not svg.exists() and not png.exists() and not hors_ligne:
        try:
            print(f"  téléchargement {entree['url']}")
            telecharger(entree["url"], svg, entree.get("sha1"))
        except SystemExit:
            print("  original indisponible : rendu PNG Wikimedia 1280 px")
            telecharger(entree["url_rendu_1280"], png, None)
    if svg.exists():
        brut = svg_vers_png(svg.read_bytes(), round(cote * 2.5))
        entree["_rasterisation"] = "SVG original rasterisé (cairosvg)"
    elif png.exists():
        brut = Image.open(png).convert("RGBA")
        entree["_rasterisation"] = "rendu PNG 1280 px de Wikimedia (librsvg), réduit"
    else:
        raise SystemExit(f"{code} : ni {svg} ni {png} (mode hors ligne)")
    im = a_l_echelle(recadrer(brut, entree.get("recadrage_frac")), cote)
    if entree.get("normaliser_couleurs", True):
        im = normaliser_couleurs(im, entree.get("retirer_contour_noir", False))
    if entree.get("listel_blanc_frac"):
        im = ajouter_listel(im, entree["listel_blanc_frac"])
    return im


def ajouter_listel(im: Image.Image, f: float) -> Image.Image:
    """Ajoute un listel blanc de largeur f (fraction du côté) : la face est réduite et posée sur
    sa propre silhouette en blanc (cas de la balise J5 réelle, bordée d'un liseré blanc)."""
    W, H = im.size
    fond = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    blanc = Image.new("RGBA", (W, H), tuple(int(PALETTE["blanc"][i:i + 2], 16) for i in (1, 3, 5)) + (255,))
    fond.paste(blanc, (0, 0), im.getchannel("A"))
    k = 1 - 2 * f
    petit = im.resize((round(W * k), round(H * k)), Image.LANCZOS)
    fond.alpha_composite(petit, ((W - petit.size[0]) // 2, (H - petit.size[1]) // 2))
    return fond


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seulement", help="codes séparés par des virgules")
    ap.add_argument("--hors-ligne", action="store_true")
    a = ap.parse_args()
    man = json.loads(MANIFESTE.read_text())
    garder = set(a.seulement.split(",")) if a.seulement else None
    FACES.mkdir(parents=True, exist_ok=True)
    for e in man["faces"]:
        if garder and e["code"] not in garder:
            continue
        im = construire(e, a.hors_ligne)
        sortie = FACES / f"{e['code']}.png"
        im.save(sortie, optimize=True)
        e["sortie"] = {"fichier": f"faces/{e['code']}.png", "px": list(im.size),
                       "sha1": hashlib.sha1(sortie.read_bytes()).hexdigest(),
                       "rasterisation": e.pop("_rasterisation", "composition maison (cairosvg/Pillow)")}
        print(f"{e['code']:30s} {im.size[0]}x{im.size[1]} px  {e['largeur_mm']}x{e['hauteur_mm']} mm  -> {sortie.relative_to(RACINE)}")
    MANIFESTE.write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
