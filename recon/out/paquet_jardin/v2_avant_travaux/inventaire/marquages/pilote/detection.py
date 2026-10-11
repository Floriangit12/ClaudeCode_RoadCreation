"""Détection libre des marques sur l'ortho PCRS 5 cm 2022 (indépendante du réseau OpenDRIVE 2026).

Chaîne :
1. cartes() : luminance L (Rec. 601) ; fond local = 30e percentile sur 2,6 m (calculé à 20 cm), séparément dans
   les ombres portées et au soleil (masque_ombre : Otsu sur l'éclairement lissé) ; contraste TH = L - fond ;
   saturation ; même chose pour le « jaune » (b* approché : (R+G)/2 - B) ;
2. probabilite_peinture() : p in [0, 1] par rampe linéaire sur TH (seuil adaptatif : max(22 DN, 0,15 x fond)) ;
3. masques blanc / jaune : p >= 0,5, saturation basse pour le blanc ; nettoyage des taches < 0,01 m2 ;
4. composantes() : étiquetage 8-connexe, moments d'ordre 2 (centre, axe, longueur/largeur équivalentes d'un
   rectangle : sqrt(12 lambda)), remplissage, luminance moyenne -> classement géométrique grossier
   (bande de zébra, tiret/ligne, flèche candidate, carré, pavé jaune, symbole/autre).
Tout est déterministe. numpy + Pillow.
"""
from __future__ import annotations

import math

import numpy as np

import commun_pilote as C

FOND_M = 2.6
FOND_RANG = 0.30


def fond_rang(A, fenetre_m=FOND_M, rang=FOND_RANG, sous=4):
    """Fond local : percentile `rang` sur une fenêtre carrée de `fenetre_m`, calculé à 20 cm (sous-échantillonnage
    x4 par moyenne) puis ré-interpolé bilinéairement à 5 cm. Le 30e percentile reste sur l'enrobé même dans un zébra
    (bandes 0,50 / vides 0,50 à 0,80 : 38 à 50 % de peinture)."""
    from PIL import Image, ImageFilter
    H, W = A.shape
    k = int(round(fenetre_m / (C.PX * sous))) | 1
    small = Image.fromarray(np.clip(A, 0, 255).astype(np.uint8)).resize((max(1, W // sous), max(1, H // sous)), Image.BOX)
    B = small.filter(ImageFilter.RankFilter(k, int(k * k * rang)))
    return np.asarray(B.resize((W, H), Image.BILINEAR), np.float32)


def masque_ombre(L):
    """Ombres portées : luminance d'éclairement (L écrêtée à fond_1m + 15 pour effacer la peinture, flou gaussien
    0,2 m), seuil d'Otsu ; retenu seulement si les deux classes diffèrent nettement (écart des moyennes >= 40 DN
    et médiane ombre < 0,7 x médiane soleil), sinon aucun pixel n'est en ombre. -> (masque, médiane ombre, médiane soleil)."""
    from PIL import Image, ImageFilter
    Lc = np.minimum(L, fond_rang(L, 1.0, 0.5) + 15)
    Ls = np.asarray(Image.fromarray(np.clip(Lc, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)), np.float32)
    h, _ = np.histogram(Ls, 256, (0, 256))
    w = np.cumsum(h)
    m = np.cumsum(h * np.arange(256))
    best, thr, mu = 0.0, 0, (0.0, 0.0)
    for t in range(20, 230):
        w0, w1 = w[t], w[-1] - w[t]
        if w0 == 0 or w1 == 0:
            continue
        m0, m1 = m[t] / w0, (m[-1] - m[t]) / w1
        v = w0 * w1 * (m0 - m1) ** 2
        if v > best:
            best, thr, mu = v, t, (m0, m1)
    S = Ls < thr
    if not S.any() or S.all():
        return np.zeros_like(S), None, None
    msh, msun = float(np.median(L[S])), float(np.median(L[~S]))
    if mu[1] - mu[0] < 40 or msh > 0.7 * msun:
        return np.zeros_like(S), None, None
    return S, msh, msun


def cartes(rgb, ombres=True):
    """ombres : fond calculé séparément dans les ombres portées et au soleil (sinon le bord d'une ombre d'arbre
    passe pour de la peinture sur 1 à 2 m de large)."""
    f = rgb.astype(np.float32)
    R, G, B = f[..., 0], f[..., 1], f[..., 2]
    L = 0.299 * R + 0.587 * G + 0.114 * B
    S = np.zeros(L.shape, bool)
    if ombres:
        S, msh, msun = masque_ombre(L)
    if S.any():
        fond = np.where(S, fond_rang(np.where(S, L, msh)), fond_rang(np.where(S, msun, L)))
    else:
        fond = fond_rang(L)
    TH = L - fond
    mx, mn = f.max(-1), f.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1.0)
    jaune = np.clip((R + G) / 2 - B, 0, 255)
    TJ = jaune - fond_rang(jaune)
    return {"L": L, "TH": TH, "fond": fond, "sat": sat, "jaune": jaune, "TJ": TJ, "ombre": S}


def seuil_adaptatif(fond):
    """Contraste minimal d'une peinture : 22 DN, ou 15 % du fond (enrobé clair au soleil)."""
    return np.maximum(22.0, 0.15 * fond)


def probabilite_peinture(c):
    """p = rampe (TH - 0,5 s) / s sur [0, 1] avec s le seuil adaptatif : 0,5 au seuil, 1 à 1,5 s."""
    s = seuil_adaptatif(c["fond"])
    p = np.clip((c["TH"] - 0.5 * s) / s, 0, 1)
    p = np.where(c["sat"] > 0.30, 0.0, p)
    return p.astype(np.float32)


def probabilite_jaune(c):
    p = np.clip((c["TJ"] - 12.0) / 24.0, 0, 1)
    p = np.where((c["jaune"] > 30) & (c["L"] > 80), p, 0.0)
    return p.astype(np.float32)


def nettoyer(m, aire_min_px=4):
    lab, n = C.etiqueter(m)
    cnt = np.bincount(lab.ravel(), minlength=n + 1)
    garde = cnt >= aire_min_px
    garde[0] = False
    return garde[lab]


def mesurer(rr, cc, geo, c=None):
    """Moments d'une composante (pixels rr, cc) -> dict (L93)."""
    x, y = C.px_vers_l93(rr, cc, geo)
    n = len(x)
    cx, cy = float(x.mean()), float(y.mean())
    dx, dy = x - cx, y - cy
    cov = np.array([[np.mean(dx * dx), np.mean(dx * dy)], [np.mean(dx * dy), np.mean(dy * dy)]])
    cov += np.eye(2) * C.PX ** 2 / 12.0
    w, v = np.linalg.eigh(cov)
    l1, l2 = max(w[1], 1e-9), max(w[0], 1e-9)
    ax = v[:, 1]
    ang = math.atan2(ax[1], ax[0])
    # étendues réelles le long des axes
    u = dx * ax[0] + dy * ax[1]
    t = -dx * ax[1] + dy * ax[0]
    Lr = float(u.max() - u.min() + C.PX)
    Wr = float(t.max() - t.min() + C.PX)
    aire = n * C.PX ** 2
    d = {"n_px": int(n), "aire_m2": aire, "cx": cx, "cy": cy, "angle_rad": ang,
         "long_eq_m": math.sqrt(12 * l1), "larg_eq_m": math.sqrt(12 * l2),
         "long_m": Lr, "larg_m": Wr, "remplissage": aire / max(Lr * Wr, 1e-9)}
    if c is not None:
        d["TH_moy"] = float(c["TH"][rr, cc].mean())
        d["L_moy"] = float(c["L"][rr, cc].mean())
    return d


def classer(d, couleur="blanc"):
    L, W, A, f = d["long_m"], d["larg_m"], d["aire_m2"], d["remplissage"]
    if couleur == "jaune":
        if 0.25 <= W <= 0.55 and 0.45 <= L <= 0.95 and f > 0.6:
            return "pave_jaune"
        if W <= 0.3 and L > 1.0:
            return "ligne_jaune"
        return "autre_jaune"
    if 0.38 <= W <= 0.70 and 1.6 <= L <= 6.5 and f > 0.70:
        return "bande_zebra"
    if W <= 0.38 and L >= 0.7 and f > 0.55:
        return "trait"
    if 0.38 <= W <= 0.65 and 0.38 <= L <= 0.65 and f > 0.7:
        return "carre_050"
    if 0.75 <= W <= 1.3 and 0.75 <= L <= 1.3 and f > 0.7:
        return "carre_100"
    if 2.5 <= L <= 6.5 and 0.45 <= W <= 1.6 and 0.5 <= A <= 2.6 and f < 0.75:
        return "fleche_candidate"
    if A < 0.03:
        return "tache"
    if d.get("largeur_ruban_m", 1.0) <= 0.30 and d.get("longueur_ruban_m", 0.0) >= 2.0 and L >= 1.5:
        return "ligne_courbe"
    return "symbole_ou_autre"


def detecter(rgb, geo, couleur="blanc", c=None):
    c = c or cartes(rgb)
    p = probabilite_peinture(c) if couleur == "blanc" else probabilite_jaune(c)
    m = nettoyer(p >= 0.5)
    lab, n = C.etiqueter(m)
    # pixels de bord (masque moins son érodé 3 x 3) : largeur moyenne d'un ruban = 2 aire / périmètre
    bord = m & ~(C.min_filtre(m.astype(np.float32) * 255, 3) > 127)
    nb = np.bincount(lab[bord], minlength=n + 1)
    comps = []
    for i, (rr, cc) in enumerate(C.composantes(lab, n), start=1):
        d = mesurer(rr, cc, geo, c)
        d["id"] = i
        perim = max(nb[i], 1) * C.PX
        d["largeur_ruban_m"] = 2 * d["aire_m2"] / perim + C.PX
        d["longueur_ruban_m"] = perim / 2
        d["classe"] = classer(d, couleur)
        d["couleur"] = couleur
        comps.append(d)
    out = {"cartes": c, "p": p, "masque": m, "lab": lab, "comps": comps}
    if couleur == "blanc":
        # germes sur le masque érodé de 2 px (0,10 m) : sépare les bandes de zébra des carrés ou tirets qui les
        # touchent par un coin ; dimensions remises à l'échelle (+ 0,20 m)
        me = C.min_filtre(m.astype(np.float32) * 255, 5) > 127
        labe, ne = C.etiqueter(me)
        ce = []
        for rr, cc in C.composantes(labe, ne):
            if len(rr) < 20:
                continue
            d = mesurer(rr, cc, geo, c)
            d["long_m"] += 0.2
            d["larg_m"] += 0.2
            d["remplissage"] = (d["aire_m2"] + 0.2 * (d["long_m"] + d["larg_m"])) / max(d["long_m"] * d["larg_m"], 1e-9)
            d["classe"] = classer(d, couleur)
            d["couleur"] = couleur
            d["erode"] = True
            ce.append(d)
        out["comps_erodes"] = ce
    return out


def germes_zebra(det):
    """Germes de bandes de zébra : composantes « bande_zebra » du masque et du masque érodé, sans doublon (0,3 m)."""
    g = [d for d in det["comps"] if d["classe"] == "bande_zebra"]
    for d in det.get("comps_erodes", []):
        if d["classe"] != "bande_zebra":
            continue
        if any(math.hypot(d["cx"] - e["cx"], d["cy"] - e["cy"]) < 0.3 for e in g):
            continue
        g.append(d)
    return g
