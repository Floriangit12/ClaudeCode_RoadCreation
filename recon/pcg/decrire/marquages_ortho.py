"""Ortho PCRS 5 cm 2022 (data/sites/paquet_jardin/ortho5cm_2022, dalles 50 m) : preuve photographique
des marques présentes en 2022 (états « conserve » et « refait_2025_identique »).

- luminance(Q) : luminance (0-255) bilinéaire aux points locaux Q ; NaN hors des dalles ;
- phase_ortho(P, p) : décalage δ de la phase des tirets d'une ligne (trait, vide, phase, interruptions de
  la description) qui maximise la corrélation entre la luminance le long de l'axe (pas 2 cm) et le motif
  binaire des tirets, δ ∈ [−P/2, P/2] au cm ; pic net si la corrélation maximale ≥ 0,3 ;
- recaler(polys, origine, cap, ...) : translation (latérale ± 0,5 m, longitudinale ± 2,5 m) d'un gabarit
  posé (cap gardé) qui maximise la corrélation luminance / masque du gabarit (grille 3 cm).
Diagnostic (lecture seule) : python recon/pcg/decrire/marquages_ortho.py [--base DOSSIER] [--json SORTIE]
  -> décalage de phase de chaque ligne discontinue conservée (≥ 2 tirets) contre l'ortho.
"""
import argparse
import functools
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import O, SORTIE, VECTEURS, abscisses, lire_geojson, point_a, repere  # noqa: E402

DALLES = VECTEURS / "ortho5cm_2022"
PX = 0.05
PIC_NET = 0.3                 # pic net (contrôle) : corrélation maximale ≥ 0,3
PIC_RECALAGE = 0.25           # corrélation maximale minimale pour recaler une phase
ETATS_2022 = ("conserve", "refait_2025_identique")


@functools.lru_cache(maxsize=None)
def dalles():
    """{(x0, y1) L93 du coin haut-gauche : chemin .jpg}."""
    out = {}
    for j in sorted(DALLES.glob("*.jgw")):
        v = [float(x) for x in j.read_text().split()]
        out[(int(round(v[4] - PX / 2)), int(round(v[5] + PX / 2)))] = j.with_suffix(".jpg")
    return out


@functools.lru_cache(maxsize=None)
def _image(chemin):
    from PIL import Image
    return np.asarray(Image.open(chemin).convert("L"), dtype=np.float32)


def luminance(Q):
    """Luminance bilinéaire (0-255) aux points locaux Q (N, 2) ; NaN hors des dalles."""
    Q = np.atleast_2d(np.asarray(Q, float))
    X, Y = Q[:, 0] + O[0], Q[:, 1] + O[1]
    out = np.full(len(Q), np.nan)
    tx = (np.floor(X / 50.0) * 50.0).astype(np.int64)
    ty = (np.ceil(Y / 50.0) * 50.0).astype(np.int64)
    d = dalles()
    for cle in sorted(set(zip(tx.tolist(), ty.tolist()))):
        f = d.get(cle)
        if f is None:
            continue
        im = _image(f)
        m = (tx == cle[0]) & (ty == cle[1])
        c = (X[m] - cle[0]) / PX - 0.5
        r = (cle[1] - Y[m]) / PX - 0.5
        n = im.shape[0] - 2
        c0 = np.clip(np.floor(c).astype(int), 0, n)
        r0 = np.clip(np.floor(r).astype(int), 0, n)
        a, b = np.clip(c - c0, 0, 1), np.clip(r - r0, 0, 1)
        out[m] = (im[r0, c0] * (1 - a) + im[r0, c0 + 1] * a) * (1 - b) + (im[r0 + 1, c0] * (1 - a) + im[r0 + 1, c0 + 1] * a) * b
    return out


def pieces(p, L, phase=None):
    """Parties peintes (σ0, σ1) d'une ligne (sémantique de la description) ; phase imposée possible."""
    T, V = p["trait_m"], p["vide_m"]
    ph = p["phase_m"] if phase is None else phase
    per = T + V
    k0 = math.floor(-ph / per) - 1
    iv = [(ph + k * per, ph + k * per + T) for k in range(k0, int((L - ph) / per) + 2)]
    iv = [(max(0.0, a), min(L, b)) for a, b in iv if b > 0 and a < L]
    for a0, b0 in p.get("interruptions", []):
        out = []
        for a, b in iv:
            if b <= a0 or a >= b0:
                out.append((a, b))
            else:
                if a < a0:
                    out.append((a, a0))
                if b > b0:
                    out.append((b0, b))
        iv = out
    return [(a, b) for a, b in iv if b - a > 1e-3]


def _masque(s, iv):
    m = np.zeros(len(s))
    for a, b in iv:
        m[(s >= a) & (s < b)] = 1.0
    return m


def _corr(lum, m):
    if m.std() < 1e-6:
        return None
    return float(np.mean(lum * (m - m.mean()) / m.std()))


def phase_ortho(P, p, pas=0.02, pas_delta=0.01):
    """Recalage de phase d'une ligne discontinue sur l'ortho : {delta_m, corr_max, corr_v2, n_tirets} ou None
    (hors ortho, motif constant). P : axe local ; p : trait_m, vide_m, phase_m, interruptions."""
    L = float(abscisses(P)[-1])
    s = np.arange(0.0, L, pas)
    if len(s) < 10:
        return None
    q, _ = point_a(P, s)
    lum = luminance(q)
    if np.isnan(lum).any():
        return None
    lum = (lum - lum.mean()) / max(float(lum.std()), 1e-6)
    per = p["trait_m"] + p["vide_m"]
    c0 = _corr(lum, _masque(s, pieces(p, L)))
    if c0 is None:
        return None
    best = None
    for d in np.round(np.arange(-per / 2, per / 2 + 1e-9, pas_delta), 4):
        c = _corr(lum, _masque(s, pieces(p, L, (p["phase_m"] + d) % per)))
        if c is not None and (best is None or c > best[1] + 1e-9):
            best = (float(d), c)
    if best is None:
        return None
    n = sum(1 for a, b in pieces(p, L) if b - a >= 0.5 * p["trait_m"])
    return {"delta_m": round(best[0], 3), "corr_max": round(best[1], 3), "corr_v2": round(c0, 3), "n_tirets": n}


def recaler(polys, origine, cap_deg, echelle=(1.0, 1.0), lat=0.5, lon=2.5, pas=0.10, grille=0.03):
    """Translation (dx latéral, dy longitudinal, m) du gabarit `polys` (coordonnées gabarit, [[anneau, ...]])
    posé en (origine, cap) qui maximise la corrélation avec la luminance de l'ortho ; la fenêtre d'échantillonnage
    est la boîte du gabarit élargie de 0,4 m. -> {dx, dy, corr_max, corr_v2} ou None (hors ortho)."""
    from commun import dans_polygones
    ex_, ey_ = echelle
    h = math.radians(cap_deg)
    ex, ey = np.array([math.sin(h), -math.cos(h)]), np.array([math.cos(h), math.sin(h)])
    R = [[np.c_[r[:, 0] * ex_, r[:, 1] * ey_] for r in poly] for poly in polys]
    allp = np.vstack([r for poly in R for r in poly])
    xs = np.arange(allp[:, 0].min() - 0.4, allp[:, 0].max() + 0.4 + 1e-9, grille)
    ys = np.arange(allp[:, 1].min() - 0.4, allp[:, 1].max() + 0.4 + 1e-9, grille)
    Xg, Yg = np.meshgrid(xs, ys)
    G = np.c_[Xg.ravel(), Yg.ravel()]
    m = dans_polygones(G, R).astype(float)
    if m.std() < 1e-6:
        return None
    mn = (m - m.mean()) / m.std()
    o = np.asarray(origine, float)

    def corr(dx, dy):
        Q = o + (G[:, 0] + dx)[:, None] * ex + (G[:, 1] + dy)[:, None] * ey
        lu = luminance(Q)
        if np.isnan(lu).any():
            return None
        lu = (lu - lu.mean()) / max(float(lu.std()), 1e-6)
        return float(np.mean(lu * mn))
    c0 = corr(0.0, 0.0)
    if c0 is None:
        return None
    best = (0.0, 0.0, c0)
    for dx in np.round(np.arange(-lat, lat + 1e-9, pas), 3):
        for dy in np.round(np.arange(-lon, lon + 1e-9, pas), 3):
            c = corr(dx, dy)
            if c is not None and c > best[2] + 1e-9:
                best = (float(dx), float(dy), c)
    # affinage au cm autour du meilleur
    bx, by, bc = best
    for dx in np.round(np.arange(bx - pas, bx + pas + 1e-9, 0.02), 3):
        for dy in np.round(np.arange(by - pas, by + pas + 1e-9, 0.02), 3):
            c = corr(dx, dy)
            if c is not None and c > best[2] + 1e-9:
                best = (float(dx), float(dy), c)
    bx, by, bc = best
    for dx in np.round(np.arange(bx - 0.02, bx + 0.02 + 1e-9, 0.01), 3):
        for dy in np.round(np.arange(by - 0.02, by + 0.02 + 1e-9, 0.01), 3):
            c = corr(dx, dy)
            if c is not None and c > best[2] + 1e-9:
                best = (float(dx), float(dy), c)
    return {"dx": round(best[0], 3), "dy": round(best[1], 3), "corr_max": round(best[2], 3), "corr_v2": round(c0, 3)}


def diagnostic(base=SORTIE / "base"):
    out = []
    for f in lire_geojson(Path(base) / "marquages.geojson"):
        p = f["properties"]
        if p["classe"] != "ligne" or p["type"] != "discontinue" or p["etat"] not in ETATS_2022:
            continue
        P = repere(np.asarray(f["geometry"]["coordinates"], float))
        r = phase_ortho(P, p)
        if r is None or r["n_tirets"] < 2:
            continue
        out.append(dict(id=p["id"], modulation=p["modulation"], periode_m=round(p["trait_m"] + p["vide_m"], 3),
                        phase_src=p["prov"]["phase_m"]["src"], **r))
    nets = [o for o in out if o["corr_max"] >= PIC_NET]
    dn = np.array([abs(o["delta_m"]) for o in nets])
    return {"methode": "luminance PCRS 5 cm 2022 le long de l'axe (pas 2 cm) contre le motif des tirets décalé de δ (pas 1 cm)",
            "n_lignes": len(out), "n_pic_net": len(nets),
            "decalage_abs_pic_net_m": {"p50": round(float(np.median(dn)), 3) if len(dn) else None,
                                       "p95": round(float(np.percentile(dn, 95)), 3) if len(dn) else None,
                                       "max": round(float(dn.max()), 3) if len(dn) else None},
            "a_reprendre": [o["id"] for o in nets if abs(o["delta_m"]) > 0.10], "lignes": out}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default=str(SORTIE / "base"))
    ap.add_argument("--json")
    a = ap.parse_args()
    r = diagnostic(a.base)
    print(json.dumps({k: v for k, v in r.items() if k != "lignes"}, ensure_ascii=False))
    if a.json:
        Path(a.json).write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
