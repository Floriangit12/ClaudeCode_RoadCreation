"""Le MNT LiDAR 2021 en JPEG couleur (data/sites/paquet_jardin/lidar/dtm_15cm, palette inconnue) est-il
utilisable pour mesurer des hauteurs de bordure ? Test : table de décodage couleur -> z apprise sur la
heightmap 16 bits du paquet v1 (sol nu 2021 débruité) HORS de toute zone modifiée en 2025
(relief_zones_2026.geojson, chaussée 2026 comprise), validation croisée en damier (cases de 10 m).

Sortie : ../dtm_jpg_decodage.json. `MNT2021Jpg()` rend un échantillonneur (z NGF décodé, bilinéaire) utilisé par
mesurer_bordures.py dans les zones où la heightmap v1 est modifiée (aucun cache écrit).
Usage : python -I dtm_jpg.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image, ImageDraw

import commun_sol as C

RES = 0.15
BITS = 5            # quantification RGB de la table (32 niveaux par canal)


def charger_jpg():
    d = C.SITE / "lidar/dtm_15cm"
    idx = C.lire_json(d / "index.json")
    W = max(it["px_box"][2] for it in idx)
    H = max(it["px_box"][3] for it in idx)
    A = np.zeros((H, W, 3), np.uint8)
    for it in idx:
        c0, r0, c1, r1 = it["px_box"]
        A[r0:r1, c0:c1] = np.asarray(Image.open(d / it["file"]).convert("RGB"))
    x0 = min(it["l93_bbox"][0] for it in idx)
    y1 = max(it["l93_bbox"][3] for it in idx)
    return A, x0, y1


def masque_zones(x0, y1, W, H):
    im = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(im)
    for f in C.lire_json(C.PAQUET / "relief/relief_zones_2026.geojson")["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for p in polys:
            for k, r in enumerate(p):
                r = np.asarray(r)[:, :2]
                u = (r[:, 0] - x0) / RES
                v = (y1 - r[:, 1]) / RES
                dr.polygon(list(zip(u.tolist(), v.tolist())), fill=1 if k == 0 else 0)
    m = np.asarray(im, bool)
    # marge de 0,6 m (bords des zones lissés)
    k = 4
    mm = m.copy()
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            mm |= np.roll(np.roll(m, dy, 0), dx, 1)
    return mm


def main():
    res, _ = evaluer()
    C.ecrire_json(C.SORTIE / "dtm_jpg_decodage.json", res)
    print(res)


class MNT2021Jpg:
    """z NGF décodé du JPEG (table apprise sur toute la zone non modifiée), interpolation bilinéaire."""

    def __init__(self):
        _, (self.z, self.x0, self.y1) = evaluer()

    def __call__(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        H, W = self.z.shape
        fc = np.clip((x - self.x0) / RES - 0.5, 0, W - 1.000001)
        fr = np.clip((self.y1 - y) / RES - 0.5, 0, H - 1.000001)
        c, r = np.floor(fc).astype(int), np.floor(fr).astype(int)
        tc, tr = fc - c, fr - r
        z = self.z
        return ((z[r, c] * (1 - tc) + z[r, c + 1] * tc) * (1 - tr) + (z[r + 1, c] * (1 - tc) + z[r + 1, c + 1] * tc) * tr)


def evaluer():
    A, x0, y1 = charger_jpg()
    H, W = A.shape[:2]
    xs = x0 + (np.arange(W) + 0.5) * RES
    ys = y1 - (np.arange(H) + 0.5) * RES
    X, Y = np.meshgrid(xs, ys)
    hm = C.Heightmap()
    Z = hm(X, Y)
    mod = masque_zones(x0, y1, W, H)
    q = (A >> (8 - BITS)).astype(np.int32)
    cle = (q[..., 0] << (2 * BITS)) | (q[..., 1] << BITS) | q[..., 2]
    # damier de 10 m : apprentissage sur les cases paires, test sur les impaires
    case = ((np.floor((X - x0) / 10) + np.floor((y1 - Y) / 10)) % 2).astype(int)
    ok = ~mod
    res = {}

    def table(sel):
        k = cle[sel].ravel()
        z = Z[sel].ravel()
        o = np.argsort(k, kind="stable")
        k, z = k[o], z[o]
        u, deb = np.unique(k, return_index=True)
        fin = np.r_[deb[1:], len(k)]
        med = np.array([np.median(z[a:b]) for a, b in zip(deb, fin)])
        lut = np.full(1 << (3 * BITS), np.nan)
        lut[u] = med
        return lut

    def decoder(lut, cles):
        z = lut[cles]
        # cases vides : voisin le plus proche dans l'espace RGB quantifié
        vide = np.isnan(z)
        if vide.any():
            pleins = np.flatnonzero(~np.isnan(lut))
            rgb_p = np.c_[pleins >> (2 * BITS), (pleins >> BITS) & ((1 << BITS) - 1), pleins & ((1 << BITS) - 1)]
            cv = cles[vide]
            rgb_v = np.c_[cv >> (2 * BITS), (cv >> BITS) & ((1 << BITS) - 1), cv & ((1 << BITS) - 1)]
            out = np.empty(len(cv))
            for i in range(0, len(cv), 2000):
                d = ((rgb_v[i:i + 2000, None, :] - rgb_p[None]) ** 2).sum(-1)
                out[i:i + 2000] = lut[pleins[d.argmin(1)]]
            z = z.copy()
            z[vide] = out
        return z

    lut_a = table(ok & (case == 0))
    zt = decoder(lut_a, cle[ok & (case == 1)])
    e = zt - Z[ok & (case == 1)]
    res["validation_croisee_damier_10m"] = {
        "pixels_test": int(e.size),
        "erreur_abs_m": {"p50": round(float(np.median(np.abs(e))), 4), "p90": round(float(np.percentile(np.abs(e), 90)), 4),
                         "p95": round(float(np.percentile(np.abs(e), 95)), 4)},
        "biais_m": round(float(np.median(e)), 4),
    }
    # pas de quantification apparent : écart entre niveaux successifs de la table
    lut = table(ok)
    zz = np.sort(lut[~np.isnan(lut)])
    res["table"] = {"cases_pleines": int((~np.isnan(lut)).sum()), "bits_par_canal": BITS,
                    "pas_median_entre_niveaux_m": round(float(np.median(np.diff(np.unique(np.round(zz, 3))))), 4)}
    Zd = decoder(lut, cle.ravel()).reshape(H, W)
    # bruit local : écart-type dans 3x3 sur sol plat (pente heightmap < 2 %)
    gy, gx = np.gradient(Z, RES)
    plat = ok & (np.hypot(gx, gy) < 0.02)
    lap = Zd - (np.roll(Zd, 1, 0) + np.roll(Zd, -1, 0) + np.roll(Zd, 1, 1) + np.roll(Zd, -1, 1)) / 4
    res["bruit_local_sol_plat_m"] = {"p50_abs_laplacien": round(float(np.median(np.abs(lap[plat]))), 4),
                                     "p95_abs_laplacien": round(float(np.percentile(np.abs(lap[plat]), 95)), 4)}
    res["conclusion_auto"] = ("decodable a quelques cm" if res["validation_croisee_damier_10m"]["erreur_abs_m"]["p90"] < 0.04
                              else "trop imprecis pour des hauteurs de bordure")
    return res, (Zd, x0, y1)


if __name__ == "__main__":
    main()
