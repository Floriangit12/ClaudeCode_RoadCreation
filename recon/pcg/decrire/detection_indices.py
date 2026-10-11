"""Détection guidée par indice (DET-FLE-007 en fenêtre réduite, VAL-IMG-007) : une marque v1 n'est qu'un INDICE
(existence, type, couleur) ; elle n'entre dans la description que si une source image admissible la confirme
(FUS-SRC-001 : ortho 2022 hors des zones refaites ou construites, plan 2025 dans la zone des travaux), avec la pose
mesurée sur l'image et la forme normative de l'indice (FUS-SNP-004).

- Marques surfaciques (zébras, flèches, figurines, glyphes, damiers, hachures, zigzags) : empreinte normative
  rastérisée (5 cm) corrélée (NCC) au top-hat du raster (DET-PRE-002) dans une fenêtre de translation de ± 0,30 m ;
  c_detection = clip((NCC − 0,55) / 0,30) sur l'ortho, clip((NCC − 0,60) / 0,25) sur le plan (FUS-SCO-002).
- Lignes : profil peint le long de l'axe (detection_lignes.detecter, couloir ± 0,25 m) ; c_detection = part de la
  longueur peinte modélisée vue peinte (FUS-SCO-002 : « fraction de longueur avec crête »).
- Zone sans raster admissible (construit_2023_2024, hors plan) : indice invérifiable (c = None).
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import detection_commun as D  # noqa: E402
import detection_lignes as DL  # noqa: E402
import marquages_sources as S  # noqa: E402
from commun import abscisses, point_a, sous_polyligne  # noqa: E402

RES = 0.05
RECHERCHE = 0.30


def c_detection(src, ncc):
    if ncc is None:
        return None
    if src == "ortho2022":
        return D.clip01((ncc - 0.55) / 0.30)
    return D.clip01((ncc - 0.60) / 0.25)


def c_empreinte(src, mes):
    """c_detection d'une empreinte : formule NCC de FUS-SCO-002, ou contraste top-hat intérieur − extérieur (DET-PRE-002)
    clip((contraste − 8) / 20) quand la NCC reste ≥ 0,30 (petites marques répétées : pavés, carrés, barres, que le flou
    du raster pénalise en NCC) ; la plus forte des deux."""
    c1 = c_detection(src, mes["ncc"])
    c2 = D.clip01((mes["contraste_dn"] - 8.0) / 20.0) if mes["ncc"] >= 0.30 else 0.0
    return max(c1, c2)


def raster_pour(etat):
    """Raster admissible pour un état de zone (ordre FUS-SRC-001 : plan 2025 d'abord dans les zones refaites)."""
    if S.admissible("plan2025", etat):
        return "plan2025"
    if S.admissible("ortho2022", etat):
        return "ortho2022"
    return None


def rasters_pour(etat):
    """Rasters admissibles d'un état de zone, par ordre de priorité (FUS-SRC-001)."""
    return [r for r in ("plan2025", "ortho2022") if S.admissible(r, etat)]


def verifier_zebra(raster, e, balayage_deg=10.0):
    """DET-ZEB-009 guidé : profil du top-hat le long de l'axe du passage (± 2 m au-delà des bandes extrêmes), moyenné sur
    60 % de la longueur de bande, pour des directions de bandes à ± balayage_deg ; pic du spectre dans [0,8 ; 1,6] m.
    -> {pic_sur_fond, pas_m, pas_ok (± 0,10 m du pas décrit), ecart_cap_deg} ou None."""
    import detection_zebras as DZ_
    A, B = e["geom"][1][:2]
    L = float(np.hypot(*(B - A)))
    if L < 1e-6:
        return None
    ax0 = (B - A) / L
    c = 0.5 * (A + B)
    lb = float(e["longueur_bande_m"])
    best = None
    for da in np.arange(-balayage_deg, balayage_deg + 1e-9, 2.0):
        a = math.radians(da)
        ax = np.array([ax0[0] * math.cos(a) - ax0[1] * math.sin(a), ax0[0] * math.sin(a) + ax0[1] * math.cos(a)])
        u = np.array([-ax[1], ax[0]])
        s = np.arange(-L / 2 - 2.0, L / 2 + 2.0, 0.02)
        w = np.linspace(-0.3 * lb, 0.3 * lb, 13)
        Q = c[None, None, :] + s[:, None, None] * ax[None, None, :] + w[None, :, None] * u[None, None, :]
        v = D.RASTERS[raster](Q.reshape(-1, 2)).reshape(len(s), len(w))
        if np.isnan(v).mean() > 0.3:
            return None
        v = np.where(np.isnan(v), np.nanmedian(v), v)
        th = D.tophat(v.T.astype(np.float32), se_m=1.2, px=0.02).T
        per, pf = DZ_.spectre(th.mean(axis=1), 0.02)
        if per is not None and (best is None or pf > best[0]):
            best = (pf, per, da)
    if best is None:
        return None
    pf, per, da = best
    return {"pic_sur_fond": round(pf, 2), "pas_m": round(per, 3), "pas_ok": abs(per - float(e["pas_axe_m"])) <= 0.10,
            "ecart_cap_deg": da}


def verifier_empreinte(raster, polys, recherche=RECHERCHE, res=RES):
    """NCC maximale (translation ± recherche) entre l'empreinte et le top-hat du raster -> dict ou None (hors raster)."""
    from commun import dans_polygones
    P = np.vstack([r for poly in polys for r in poly])
    m = recherche + 0.8
    x0, y0 = P.min(axis=0) - m
    x1, y1 = P.max(axis=0) + m
    Q, H, W = D.grille(x0, y0, x1, y1, res)
    v = D.RASTERS[raster](Q)
    if np.isnan(v).mean() > 0.2:
        return None
    img = np.where(np.isnan(v), np.nanmedian(v), v).reshape(H, W).astype(np.float32)
    th = D.tophat(img, px=res)
    # empreinte (sur-échantillonnée par la grille elle-même : test du centre de pixel)
    msk = dans_polygones(Q, polys).reshape(H, W).astype(np.float32)
    k = int(round(recherche / res))
    core = msk[k:H - k, k:W - k]
    if core.sum() < 4:
        return None
    t = core - core.mean()
    tn = float(np.sqrt((t * t).sum()))
    best = None
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            win = th[k + dy:H - k + dy, k + dx:W - k + dx]
            w = win - win.mean()
            wn = float(np.sqrt((w * w).sum()))
            if wn < 1e-6:
                continue
            c = float((w * t).sum()) / (wn * tn)
            if best is None or c > best[0] + 1e-9:
                best = (c, dx, dy)
    if best is None:
        return None
    c, dx, dy = best
    win = th[k + dy:H - k + dy, k + dx:W - k + dx]
    dedans = float(win[core > 0.5].mean())
    dehors = float(win[core < 0.5].mean())
    # dx > 0 : l'image est décalée vers +x (colonnes) ; dy > 0 : vers le sud (lignes)
    return {"ncc": round(c, 3), "dx": round(dx * res, 3), "dy": round(-dy * res, 3), "contraste_dn": round(dedans - dehors, 1)}


def verifier_ligne(raster, P, pieces, couloir=0.25):
    """Part de la longueur peinte modélisée vue peinte le long de l'axe P -> dict ou None."""
    det = DL.detecter(raster, P, couloir=couloir)
    sig, peint, valide = det["sig"], det["peint"], det["valide"]
    m = np.zeros(len(sig), bool)
    for a, b in pieces:
        m |= (sig >= a) & (sig <= b)
    mv = m & valide
    if mv.sum() < 10:
        return None
    frac = float((peint & mv).sum() / mv.sum())
    tc = det.get("t_crete")
    t_med = float(np.median(tc[peint & mv])) if (peint & mv).any() else None
    # fond : part peinte hors des pièces (fausse alarme)
    hors = (~m) & valide
    fa = float((peint & hors).sum() / hors.sum()) if hors.sum() > 20 else None
    return {"fraction": round(frac, 3), "t_median": None if t_med is None else round(t_med, 3),
            "fausse_alarme": None if fa is None else round(fa, 3), "n": int(mv.sum())}
