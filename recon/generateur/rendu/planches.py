"""Planches du catalogue rendu (lot L2b) : une planche par scène (quatre vues standard, ≤ 1092 px de côté) et des
planches d'ensemble (une vignette par scène, plusieurs fichiers pour rester ≤ 1092 px). PIL ; police Arial du système
(lecture seule), sinon police par défaut de PIL. Aucune date écrite dans les images.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

COTE_MAX = 1092
FOND = (28, 30, 33)
TEXTE = (235, 235, 230)
GRIS = (170, 172, 168)
POLICES = (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf")


def police(taille):
    for f in POLICES:
        if Path(f).exists():
            return ImageFont.truetype(f, taille)
    return ImageFont.load_default()


def _vignette(png, w, h):
    im = Image.open(png).convert("RGB")
    r = min(w / im.width, h / im.height)
    im = im.resize((max(1, int(im.width * r + 0.5)), max(1, int(im.height * r + 0.5))), Image.LANCZOS)
    fond = Image.new("RGB", (w, h), FOND)
    fond.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return fond


def titre_scene(scene):
    import json
    racine = Path(__file__).resolve().parents[3] / "recon" / "out" / "generateur" / scene / "modele_voie.json"
    try:
        return json.loads(racine.read_text(encoding="utf-8"))["meta"].get("titre", "")
    except (OSError, KeyError, ValueError):
        return ""


def planche_scene(scene, pngs, sortie, titre=None):
    """2 × 2 : oblique | dessus / conducteur | piéton ; 1092 × 792 px."""
    W = COTE_MAX
    m, cap, hdr = 8, 20, 46
    cw = (W - 3 * m) // 2
    ch = int(cw * 10 / 16)
    H = hdr + 2 * (ch + cap) + 3 * m
    img = Image.new("RGB", (W, H), FOND)
    dr = ImageDraw.Draw(img)
    titre = titre if titre is not None else titre_scene(scene)
    dr.text((m + 2, 8), f"{scene} — {titre}", fill=TEXTE, font=police(19))
    dr.text((m + 2, 30), "générateur procédural de routes françaises : Houdini (rg::*, pj::*), Karma XPU",
            fill=GRIS, font=police(12))
    ordre = (("oblique", "vue oblique 3/4 (~25 m)"), ("dessus", "vue de dessus"),
             ("conducteur", "conducteur (1,20 m)"), ("pieton", "piéton (1,60 m)"))
    for k, (nom, leg) in enumerate(ordre):
        if nom not in pngs:
            continue
        x = m + (k % 2) * (cw + m)
        y = hdr + m + (k // 2) * (ch + cap + m)
        img.paste(_vignette(pngs[nom], cw, ch), (x, y))
        dr.text((x + 2, y + ch + 3), leg, fill=GRIS, font=police(13))
    img.save(sortie)
    return Path(sortie)


LEGENDES = {"oblique": "vue oblique 3/4 (~25 m)", "dessus": "vue de dessus", "conducteur": "conducteur (1,20 m)",
            "pieton": "piéton (1,60 m)"}


def planche_vues(scene, pngs, vues, sortie, titre=None, legendes=None):
    """Planche d'une liste de vues (lot bordures : 2 vues par scène, vues rapprochées) : une vue très allongée (rapport
    > 2, vue de dessus d'une rue entière) occupe une rangée entière, les autres vont par deux ; 1092 px de large,
    hauteur ≤ 1092 px (vignettes réduites si besoin). Renvoie le chemin, ou None sans vue."""
    vues = [v for v in vues if v in pngs]
    if not vues:
        return None
    W = COTE_MAX
    m, cap, hdr = 8, 20, 46
    leg = dict(LEGENDES, **(legendes or {}))
    rangs, cur = [], []
    for v in vues:
        with Image.open(pngs[v]) as im:
            r = im.width / im.height
        if r > 2.0:
            if cur:
                rangs.append(cur)
                cur = []
            rangs.append([(v, r)])
        else:
            cur.append((v, r))
            if len(cur) == 2:
                rangs.append(cur)
                cur = []
    if cur:
        rangs.append(cur)

    def hauteurs(k):
        out = []
        for rg in rangs:
            n = len(rg)
            cw = (W - (n + 1) * m) // n
            out.append(int(min(cw / r for _, r in rg) * k))
        return out
    k = 1.0
    while hdr + sum(h + cap + m for h in hauteurs(k)) + m > COTE_MAX and k > 0.2:
        k -= 0.02
    hs = hauteurs(k)
    H = hdr + sum(h + cap + m for h in hs) + m
    img = Image.new("RGB", (W, H), FOND)
    dr = ImageDraw.Draw(img)
    t = titre if titre is not None else titre_scene(scene)
    dr.text((m + 2, 8), f"{scene} — {t}", fill=TEXTE, font=police(19))
    dr.text((m + 2, 30), "générateur procédural de routes françaises : Houdini (rg::*, pj::*), Karma XPU",
            fill=GRIS, font=police(12))
    y = hdr + m
    for rg, h in zip(rangs, hs):
        n = len(rg)
        cw = (W - (n + 1) * m) // n
        for j, (v, _r) in enumerate(rg):
            x = m + j * (cw + m)
            img.paste(_vignette(pngs[v], cw, h), (x, y))
            dr.text((x + 2, y + h + 3), leg.get(v, v.replace("_", " ")), fill=GRIS, font=police(13))
        y += h + cap + m
    img.save(sortie)
    return Path(sortie)


def planche_etiquettes(dessus_png, cam, etiquettes, sortie, x0, x1, titre, lignes_t=None):
    """Planche annotée (lot bordures, nuancier B01) : partie [x0, x1] (m, route droite le long de +x) de la vue de
    dessus quasi orthographique, à sa résolution native (1 px de l'image = 1 px de la planche, aucune réduction),
    avec le type de chaque tronçon écrit au-dessus de sa rangée. etiquettes : [{rangee, s0, s1, texte}] ; lignes_t :
    {rangee: t (m) de la ligne d'écriture}."""
    im = Image.open(dessus_png).convert("RGB")
    W, H = im.size
    mpp, (cx, cy) = cam["m_par_px"], cam["centre_xy"]
    c0 = int(round(W / 2 + (x0 - cx) / mpp))
    c1 = min(W, c0 + COTE_MAX)
    hdr = 30
    out = Image.new("RGB", (c1 - c0, H + hdr), FOND)
    out.paste(im.crop((c0, 0, c1, H)), (0, hdr))
    dr = ImageDraw.Draw(out)
    dr.text((6, 6), titre, fill=TEXTE, font=police(15))
    fnt = police(12)
    lignes_t = lignes_t or {}
    for e in etiquettes:
        sm = 0.5 * (e["s0"] + e["s1"])
        if not (x0 <= sm <= x1):
            continue
        t = lignes_t.get(e["rangee"], e.get("t", 0.0))
        px = W / 2 + (sm - cx) / mpp - c0
        py = H / 2 - (t - cy) / mpp + hdr
        for ligne_k, txt in enumerate(e["texte"].split("\n")):
            w = dr.textlength(txt, font=fnt)
            x, y = px - w / 2, py - 7 + 14 * ligne_k
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                dr.text((x + dx, y + dy), txt, fill=(20, 20, 20), font=fnt)
            dr.text((x, y), txt, fill=(255, 245, 160), font=fnt)
        # bornes du tronçon (tirets)
        for s in (e["s0"], e["s1"]):
            qx = W / 2 + (s - cx) / mpp - c0
            dr.line([(qx, py + 9 + 14 * (len(e["texte"].split(chr(10))) - 1)), (qx, py + 13 + 14 * (len(e["texte"].split(chr(10))) - 1))],
                    fill=(255, 245, 160), width=1)
    out.save(sortie)
    return Path(sortie)


def planches_ensemble(entrees, dossier, par_fichier=6, vue="oblique"):
    """entrees : [(scene, titre, dossier_rendus)] ; 3 colonnes × 2 rangées par fichier ; renvoie les chemins."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    W = COTE_MAX
    m, cap, hdr = 8, 34, 40
    cw = (W - 4 * m) // 3
    ch = int(cw * 10 / 16)
    out = []
    for f0 in range(0, len(entrees), par_fichier):
        lot = entrees[f0:f0 + par_fichier]
        rangs = (len(lot) + 2) // 3
        H = hdr + rangs * (ch + cap + m) + m
        img = Image.new("RGB", (W, H), FOND)
        dr = ImageDraw.Draw(img)
        dr.text((m + 2, 9), f"Catalogue des scènes simples — {lot[0][0]} à {lot[-1][0]} (vue {vue})", fill=TEXTE,
                font=police(19))
        for k, (scene, titre, d) in enumerate(lot):
            x = m + (k % 3) * (cw + m)
            y = hdr + (k // 3) * (ch + cap + m)
            png = Path(d) / f"{vue}.png"
            if png.exists():
                img.paste(_vignette(png, cw, ch), (x, y))
            dr.text((x + 2, y + ch + 2), scene, fill=TEXTE, font=police(14))
            t = titre if len(titre) <= 52 else titre[:50] + "…"
            dr.text((x + 2, y + ch + 18), t, fill=GRIS, font=police(11))
        f = dossier / f"ensemble_{f0 // par_fichier + 1}.png"
        img.save(f)
        out.append(f)
    return out


def _lignes(texte, fnt, largeur, dr):
    """Coupe un texte en lignes de largeur ≤ largeur px (mots entiers)."""
    out, cur = [], ""
    for mot in texte.split():
        essai = (cur + " " + mot).strip()
        if dr.textlength(essai, font=fnt) <= largeur or not cur:
            cur = essai
        else:
            out.append(cur)
            cur = mot
    if cur:
        out.append(cur)
    return out


def planches_ensemble_paires(entrees, dossier, par_fichier=3, prefixe="catalogue_dessus_oblique",
                             titre="Catalogue des scènes simples — étape 1 : la route seule"):
    """entrees : [(scene, titre, dossier_rendus)] ; une scène par rangée : légende | vue de dessus | vue oblique 3/4 ;
    par_fichier rangées par fichier (1092 px de large, ≤ 1092 px de haut) ; renvoie les chemins."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    W = COTE_MAX
    m, hdr, h = 8, 40, 300
    wd, wo = h, int(h * 1.6)
    wl = W - wd - wo - 4 * m
    out = []
    n_f = (len(entrees) + par_fichier - 1) // par_fichier
    for f0 in range(0, len(entrees), par_fichier):
        lot = entrees[f0:f0 + par_fichier]
        H = hdr + len(lot) * (h + m) + m
        img = Image.new("RGB", (W, H), FOND)
        dr = ImageDraw.Draw(img)
        k_f = f0 // par_fichier + 1
        dr.text((m + 2, 10), f"{titre} ({k_f}/{n_f}) — vues de dessus et obliques 3/4", fill=TEXTE, font=police(18))
        for k, (scene, t, d) in enumerate(lot):
            y = hdr + k * (h + m)
            dr.text((m + 2, y + 4), scene, fill=TEXTE, font=police(20))
            fnt = police(13)
            for j, ligne in enumerate(_lignes(t, fnt, wl - 6, dr)[:12]):
                dr.text((m + 2, y + 34 + 17 * j), ligne, fill=GRIS, font=fnt)
            for nom, x, w in (("dessus", m + wl + m, wd), ("oblique", m + wl + 2 * m + wd, wo)):
                png = Path(d) / f"{nom}.png"
                if png.exists():
                    img.paste(_vignette(png, w, h), (x, y))
        f = dossier / f"{prefixe}_{k_f}.png"
        img.save(f)
        out.append(f)
    return out


def planches_etape2(entrees, dossier, par_fichier=4, prefixe="etape2",
                    titre="Générateur de routes — étape 2 : routes, carrefours, giratoires, autoroutes (route seule)"):
    """Planches d'ensemble de l'intégration de l'étape 2 : une scène par rangée, légende | vue de dessus | vue
    conducteur (1,20 m). entrees : [(scene, titre, png_dessus, png_conducteur, legende_conducteur)] ; par_fichier
    rangées par fichier (1092 px de large, ≤ 1092 px de haut) ; renvoie les chemins."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    W = COTE_MAX
    m, hdr, h = 8, 40, 240
    wc = int(h * 1.6)
    wl = 200
    wd = W - wl - wc - 4 * m
    out = []
    n_f = (len(entrees) + par_fichier - 1) // par_fichier
    for f0 in range(0, len(entrees), par_fichier):
        lot = entrees[f0:f0 + par_fichier]
        H = hdr + len(lot) * (h + m) + m
        img = Image.new("RGB", (W, H), FOND)
        dr = ImageDraw.Draw(img)
        k_f = f0 // par_fichier + 1
        dr.text((m + 2, 10), f"{titre} ({k_f}/{n_f})", fill=TEXTE, font=police(17))
        for k, (scene, t, p_dessus, p_cond, leg_cond) in enumerate(lot):
            y = hdr + k * (h + m)
            dr.text((m + 2, y + 2), scene, fill=TEXTE, font=police(15))
            fnt = police(12)
            lignes = _lignes(t, fnt, wl - 6, dr)[:9] + [""] + _lignes(f"conducteur : {leg_cond}", fnt, wl - 6, dr)[:3]
            for j, ligne in enumerate(lignes):
                dr.text((m + 2, y + 24 + 15 * j), ligne, fill=GRIS, font=fnt)
            for png, x, w in ((p_dessus, m + wl + m, wd), (p_cond, m + wl + 2 * m + wd, wc)):
                if png and Path(png).exists():
                    img.paste(_vignette(png, w, h), (x, y))
        f = dossier / f"{prefixe}_{k_f}.png"
        img.save(f)
        out.append(f)
    return out
