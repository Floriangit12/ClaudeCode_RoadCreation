"""Découpe des images en tuiles à la taille native de l'entrée image de Claude, avec recouvrement.

Une image plus grande que l'entrée native est réduite avant d'être vue : un trait de 15 cm sur
l'ortho 5 cm (3 px) ou un panneau lointain disparaît. On découpe donc toute image à analyser en
tuiles qui tiennent dans l'entrée native SANS réduction, et qui se recouvrent pour qu'un objet
coupé par un bord soit entier dans la tuile voisine.

Entrée native (documentation Anthropic, vision) : pas de réduction si le grand côté est
≤ 1568 px et l'aire ≤ ~1,19 Mpx (≈ 1 600 jetons). Tuile par défaut : 1092 × 1092 px (1:1).
Recouvrement par défaut : 20 % (pas de 874 px), à porter à ≥ la taille du plus grand objet
cherché, en pixels.

Commandes :
  python recon/pcg/vision/decoupe.py image  SOURCE SORTIE [--taille 1092] [--recouvrement 0.2]
  python recon/pcg/vision/decoupe.py ortho  SORTIE --emprise X0 Y0 X1 Y1 [--repere local|l93]
                                            [--source pcrs2022|ign2024|GLOB] [--pas 0.05]
  python recon/pcg/vision/decoupe.py equirect PHOTO SORTIE [--fov auto|DEG] [--tangages -35,0]
  python recon/pcg/vision/decoupe.py verifier IMAGE...

Chaque découpe écrit les tuiles (PNG sans perte) et un manifeste tuiles.json : boîte de chaque
tuile dans la source (pixels), géoréférencement (ortho : coins local et L93, pas) ou visée
(équirectangulaire : lacet, tangage, fov dans le repère de l'image). Aucune annotation n'est
dessinée sur les tuiles : les pixels restent ceux de la source.

Photos de tiers (Panoramax, Mapillary) : la SORTIE doit être sous un dossier
photos_non_versionnees/ (ignoré par git) ; la commande refuse sinon.
"""
import argparse
import glob
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

RACINE = Path(__file__).resolve().parents[3]
O_L93 = (917279.43, 6460289.98)

TAILLE_NATIVE = 1092                 # côté d'une tuile carrée sans réduction
GRAND_COTE_MAX = 1568                # grand côté maximal sans réduction
AIRE_MAX = TAILLE_NATIVE * TAILLE_NATIVE
RECOUVREMENT = 0.20

SOURCES_ORTHO = {
    "pcrs2022": ("data/sites/paquet_jardin/ortho5cm_2022/pcrs5cm_*.jpg", 0.05, "PCRS 5 cm GAM, 10/05/2022"),
    "ign2024": ("data/raw/ortho_recentes/craig_ortho_2024_20cm/*.jpg", 0.20, "IGN BD ORTHO 20 cm, 09/08/2024"),
}


# --------------------------------------------------------------------------- outils
def native(w, h):
    """Vrai si une image w × h entre sans réduction."""
    return max(w, h) <= GRAND_COTE_MAX and w * h <= AIRE_MAX + 1


def positions(n, taille, recouvrement):
    """Origines des tuiles sur un axe de n px : pas = taille·(1 − recouvrement), dernière tuile
    calée sur le bord (recouvrement effectif ≥ demandé)."""
    if n <= taille:
        return [0]
    pas = max(1, int(math.floor(taille * (1.0 - recouvrement))))
    k = math.ceil((n - taille) / pas)
    return [int(round(i * (n - taille) / k)) for i in range(k + 1)]


def grille(w, h, taille=TAILLE_NATIVE, recouvrement=RECOUVREMENT):
    """Boîtes (x0, y0, x1, y1) couvrant une image w × h."""
    return [(x, y, min(x + taille, w), min(y + taille, h))
            for y in positions(h, taille, recouvrement) for x in positions(w, taille, recouvrement)]


def sha256(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def controle_tiers(sortie, source):
    """Refuse d'écrire des tuiles de photos de tiers hors d'un dossier photos_non_versionnees/."""
    s = str(source).replace("\\", "/").lower()
    tiers = any(m in s for m in ("panoramax", "mapillary", "photos_non_versionnees"))
    if tiers and "photos_non_versionnees" not in Path(sortie).as_posix():
        sys.exit("refus : tuiles de photos de tiers hors d'un dossier photos_non_versionnees/")


def ecrire_manifeste(sortie, contenu):
    Path(sortie).mkdir(parents=True, exist_ok=True)
    with open(Path(sortie) / "tuiles.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(contenu, f, ensure_ascii=False, indent=1, sort_keys=True)


# --------------------------------------------------------------------------- image plane
def decouper_image(source, sortie, taille=TAILLE_NATIVE, recouvrement=RECOUVREMENT, prefixe=None):
    """Découpe une image quelconque (photo plane, planche, rendu) en tuiles natives."""
    controle_tiers(sortie, source)
    im = Image.open(source)
    im.load()
    w, h = im.size
    prefixe = prefixe or Path(source).stem
    Path(sortie).mkdir(parents=True, exist_ok=True)
    tuiles = []
    for i, (x0, y0, x1, y1) in enumerate(grille(w, h, taille, recouvrement)):
        nom = "%s_t%03d.png" % (prefixe, i)
        im.crop((x0, y0, x1, y1)).save(Path(sortie) / nom, optimize=False)
        tuiles.append({"fichier": nom, "boite_px": [x0, y0, x1, y1]})
    ecrire_manifeste(sortie, {"type": "image", "source": str(source), "source_sha256": sha256(source),
                              "taille_source": [w, h], "taille_tuile": taille,
                              "recouvrement": recouvrement, "tuiles": tuiles})
    return tuiles


# --------------------------------------------------------------------------- ortho géoréférencée
def dalles(motif):
    """Dalles raster avec fichier monde (.jgw/.pgw/.tfw) : liste de (chemin, affine a, e, c, f)."""
    out = []
    for p in sorted(glob.glob(str(RACINE / motif) if not Path(motif).is_absolute() else motif)):
        for ext in (".jgw", ".pgw", ".tfw", ".wld"):
            w = Path(p).with_suffix(ext)
            if w.exists():
                a, _, _, e, c, f = [float(v) for v in w.read_text().split()]
                out.append((p, a, e, c, f))
                break
    return out


def mosaique(motif, x0, y0, x1, y1, pas):
    """Rééchantillonne (plus proche voisin, sans flou) les dalles sur la grille L93 [x0,x1]×[y0,y1]
    au pas donné. Renvoie un tableau (H, W, 3) uint8 et le masque des pixels couverts."""
    W, H = int(round((x1 - x0) / pas)), int(round((y1 - y0) / pas))
    img = np.zeros((H, W, 3), np.uint8)
    vu = np.zeros((H, W), bool)
    cx = x0 + (np.arange(W) + 0.5) * pas
    cy = y1 - (np.arange(H) + 0.5) * pas
    for p, a, e, c, f in dalles(motif):
        im = Image.open(p)
        dw, dh = im.size
        bx0, bx1 = c - a / 2, c - a / 2 + a * dw
        by1, by0 = f - e / 2, f - e / 2 + e * dh
        jx = np.nonzero((cx >= bx0) & (cx < bx1))[0]
        jy = np.nonzero((cy >= by0) & (cy < by1))[0]
        if not len(jx) or not len(jy):
            continue
        t = np.asarray(im.convert("RGB"))
        col = np.clip(np.floor((cx[jx] - bx0) / a).astype(int), 0, dw - 1)
        row = np.clip(np.floor((by1 - cy[jy]) / -e).astype(int), 0, dh - 1)
        img[np.ix_(jy, jx)] = t[np.ix_(row, col)]
        vu[np.ix_(jy, jx)] = True
    return img, vu


def decouper_ortho(sortie, emprise, repere="local", source="pcrs2022", pas=None,
                   taille=TAILLE_NATIVE, recouvrement=RECOUVREMENT, prefixe=None):
    """Tuiles géoréférencées d'une ortho sur une emprise (x0, y0, x1, y1), au pas natif par défaut.
    Chaque tuile a son fichier monde (.pgw, L93) et sa boîte locale/L93 dans tuiles.json."""
    motif, pas_natif, libelle = SOURCES_ORTHO.get(source, (source, None, source))
    pas = pas or pas_natif
    if pas is None:
        sys.exit("pas inconnu pour la source %s : donner --pas" % source)
    x0, y0, x1, y1 = emprise
    if repere == "local":
        x0, x1, y0, y1 = x0 + O_L93[0], x1 + O_L93[0], y0 + O_L93[1], y1 + O_L93[1]
    img, vu = mosaique(motif, x0, y0, x1, y1, pas)
    H, W = vu.shape
    prefixe = prefixe or source
    Path(sortie).mkdir(parents=True, exist_ok=True)
    tuiles = []
    for i, (px0, py0, px1, py1) in enumerate(grille(W, H, taille, recouvrement)):
        if not vu[py0:py1, px0:px1].any():
            continue
        tx0, ty1 = x0 + px0 * pas, y1 - py0 * pas
        tx1, ty0 = x0 + px1 * pas, y1 - py1 * pas
        nom = "%s_x%+07.1f_y%+07.1f.png" % (prefixe, tx0 - O_L93[0], ty1 - O_L93[1])
        Image.fromarray(img[py0:py1, px0:px1]).save(Path(sortie) / nom)
        Path(sortie, nom).with_suffix(".pgw").write_text(
            "%.6f\n0.0\n0.0\n%.6f\n%.4f\n%.4f\n" % (pas, -pas, tx0 + pas / 2, ty1 - pas / 2))
        tuiles.append({"fichier": nom, "boite_px": [px0, py0, px1, py1],
                       "l93": [round(tx0, 3), round(ty0, 3), round(tx1, 3), round(ty1, 3)],
                       "local": [round(tx0 - O_L93[0], 3), round(ty0 - O_L93[1], 3),
                                 round(tx1 - O_L93[0], 3), round(ty1 - O_L93[1], 3)],
                       "couverture": round(float(vu[py0:py1, px0:px1].mean()), 4)})
    ecrire_manifeste(sortie, {"type": "ortho", "source": libelle, "motif": motif, "pas_m": pas,
                              "emprise_l93": [x0, y0, x1, y1], "taille_tuile": taille,
                              "recouvrement": recouvrement,
                              "note": "pixel (i, j) d'une tuile centré en (l93[0] + (i+0,5)·pas, l93[3] − (j+0,5)·pas)",
                              "tuiles": tuiles})
    return tuiles


# --------------------------------------------------------------------------- photo 360°
def vue_equirect(img, lacet, tangage, fov, taille=TAILLE_NATIVE):
    """Vue perspective (sténopé) d'une image équirectangulaire (H, W, 3) : lacet/tangage en degrés
    dans le repère de l'image (lacet 0 = centre de l'image, positif vers la droite ; tangage
    positif vers le haut), fov horizontal (deg). Interpolation bilinéaire."""
    H, W = img.shape[:2]
    f = (taille / 2.0) / math.tan(math.radians(fov) / 2.0)
    jj, ii = np.mgrid[0:taille, 0:taille].astype(np.float64)
    x = (ii + 0.5 - taille / 2.0) / f
    y = -(jj + 0.5 - taille / 2.0) / f
    d = np.stack([x, y, np.ones_like(x)], -1)
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    t, l = math.radians(tangage), math.radians(lacet)
    Rx = np.array([[1, 0, 0], [0, math.cos(t), math.sin(t)], [0, -math.sin(t), math.cos(t)]])
    Ry = np.array([[math.cos(l), 0, math.sin(l)], [0, 1, 0], [-math.sin(l), 0, math.cos(l)]])
    d = d @ (Ry @ Rx).T
    lon = np.arctan2(d[..., 0], d[..., 2])
    lat = np.arcsin(np.clip(d[..., 1], -1, 1))
    u = (lon / (2 * math.pi) + 0.5) * W - 0.5
    v = (0.5 - lat / math.pi) * H - 0.5
    u0 = np.floor(u).astype(int)
    v0 = np.clip(np.floor(v).astype(int), 0, H - 2)
    du, dv = (u - u0)[..., None], np.clip(v - v0, 0, 1)[..., None]
    u0 %= W
    u1 = (u0 + 1) % W
    src = img.astype(np.float32)
    val = (src[v0, u0] * (1 - du) * (1 - dv) + src[v0, u1] * du * (1 - dv)
           + src[v0 + 1, u0] * (1 - du) * dv + src[v0 + 1, u1] * du * dv)
    return Image.fromarray(np.clip(val + 0.5, 0, 255).astype(np.uint8))


def decouper_equirect(photo, sortie, fov=None, tangages=(-35.0, 0.0), taille=TAILLE_NATIVE,
                      recouvrement=RECOUVREMENT, prefixe=None):
    """Vues perspectives couvrant tout l'horizon d'une photo 360° équirectangulaire.
    fov « auto » : résolution angulaire de la source (taille / (W/360°)), bornée à [40°, 90°],
    pour ne perdre aucun détail. Pas de lacet = fov·(1 − recouvrement)."""
    controle_tiers(sortie, photo)
    im = Image.open(photo).convert("RGB")
    W, H = im.size
    if abs(W - 2 * H) > 2:
        sys.exit("%s n'est pas équirectangulaire (2:1) : utiliser la commande image" % photo)
    if fov is None:
        fov = min(90.0, max(40.0, taille / (W / 360.0)))
    img = np.asarray(im)
    pas = fov * (1.0 - recouvrement)
    n = int(math.ceil(360.0 / pas))
    prefixe = prefixe or Path(photo).stem
    Path(sortie).mkdir(parents=True, exist_ok=True)
    tuiles = []
    for t in tangages:
        for k in range(n):
            lacet = round((k * 360.0 / n + 180.0) % 360.0 - 180.0, 3)   # 0 = centre de l'image
            nom = "%s_l%+07.1f_t%+05.1f.png" % (prefixe, lacet, t)
            vue_equirect(img, lacet, t, fov, taille).save(Path(sortie) / nom)
            tuiles.append({"fichier": nom, "lacet_image_deg": lacet, "tangage_deg": t, "fov_deg": round(fov, 3)})
    ecrire_manifeste(sortie, {"type": "equirect", "source": str(photo), "source_sha256": sha256(photo),
                              "taille_source": [W, H], "taille_tuile": taille, "recouvrement": recouvrement,
                              "px_par_degre_source": round(W / 360.0, 3),
                              "px_par_degre_tuile": round(taille / fov, 3),
                              "note": "lacet relatif au centre de l'image (azimut réel = cap de la photo + lacet "
                                      "si l'image est centrée sur le cap) ; tangage positif vers le haut",
                              "tuiles": tuiles})
    return tuiles


# --------------------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("image")
    a.add_argument("source")
    a.add_argument("sortie")
    b = sp.add_parser("ortho")
    b.add_argument("sortie")
    b.add_argument("--emprise", nargs=4, type=float, required=True)
    b.add_argument("--repere", choices=("local", "l93"), default="local")
    b.add_argument("--source", default="pcrs2022")
    b.add_argument("--pas", type=float)
    c = sp.add_parser("equirect")
    c.add_argument("photo")
    c.add_argument("sortie")
    c.add_argument("--fov", default="auto")
    c.add_argument("--tangages", default="-35,0")
    d = sp.add_parser("verifier")
    d.add_argument("images", nargs="+")
    for p in (a, b, c):
        p.add_argument("--taille", type=int, default=TAILLE_NATIVE)
        p.add_argument("--recouvrement", type=float, default=RECOUVREMENT)
        p.add_argument("--prefixe")
    x = ap.parse_args()
    if x.cmd in ("image", "ortho", "equirect") and not native(x.taille, x.taille):
        sys.exit("taille %d > entrée native (%d px de côté au plus)" % (x.taille, TAILLE_NATIVE))
    if x.cmd == "image":
        t = decouper_image(x.source, x.sortie, x.taille, x.recouvrement, x.prefixe)
    elif x.cmd == "ortho":
        t = decouper_ortho(x.sortie, x.emprise, x.repere, x.source, x.pas, x.taille, x.recouvrement, x.prefixe)
    elif x.cmd == "equirect":
        fov = None if x.fov == "auto" else float(x.fov)
        tg = tuple(float(v) for v in x.tangages.split(","))
        t = decouper_equirect(x.photo, x.sortie, fov, tg, x.taille, x.recouvrement, x.prefixe)
    else:
        ko = 0
        for p in x.images:
            w, h = Image.open(p).size
            ok = native(w, h)
            ko += not ok
            print("%s %dx%d %s" % ("OK " if ok else "TROP GRANDE", w, h, p))
        sys.exit(1 if ko else 0)
    print("%d tuiles -> %s" % (len(t), x.sortie))


if __name__ == "__main__":
    main()
