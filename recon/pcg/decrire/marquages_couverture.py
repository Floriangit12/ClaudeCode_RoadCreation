"""Carte de couverture des marquages par source (ortho 2022 en fond) : couverture_marquages.png (site) et zooms.

Usage :
    python recon/pcg/decrire/marquages_couverture.py [--base DOSSIER_BASE] [--sortie DOSSIER] [--res 0.12]
Couleurs (remplissage de l'empreinte PEINTE reconstruite depuis les paramètres de la description) :
    GAM 2026 magenta, plan 2025 orange, ortho 2022 cyan, règle (inférence) vert, indice v1 seul jaune ;
    contour pointillé blanc : ligne d'arrêt virtuelle ou hypothèse non peinte (MQ-LEF-002 / MQ-LEF-011) ;
    trait fin rose : polylignes brutes du levé GAM (référence de comparaison) ;
    croix rouge : indice v1 retiré (non confirmé, fantôme ou forme d'origine raster).
Zooms : a_centre (vue de l'image 12 de l'utilisateur), b_verdun_ne, c_verdun_sw, d_vercors_sud, e_reviree.
"""
import argparse
import functools
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import marquages_commun as M  # noqa: E402
import marquages_ortho as MO  # noqa: E402
from commun import O, SORTIE, lire_geojson, repere  # noqa: E402

COULEURS = {"gam": (255, 0, 255), "plan2025": (255, 150, 0), "ortho2022": (0, 210, 255), "regle": (40, 230, 40), "v1": (255, 255, 0)}
LIBELLES = {"gam": "levé GAM 2026", "plan2025": "détection plan projet 2025", "ortho2022": "détection ortho 2022",
            "regle": "inférence par règle", "v1": "indice v1 seul (a_verifier)"}
VUES = {
    "a_centre": (-24.0, -34.0, 24.0, 14.0, 0.025),
    "b_verdun_ne": (12.0, 10.0, 72.0, 70.0, 0.03),
    "c_verdun_sw": (-82.0, -92.0, -22.0, -32.0, 0.03),
    "d_vercors_sud": (-40.0, -150.0, 50.0, -100.0, 0.04),
    "e_reviree": (-100.0, 60.0, -40.0, 140.0, 0.04),
}


@functools.lru_cache(maxsize=None)
def _rgb(ch):
    return np.asarray(Image.open(ch).convert("RGB"), dtype=np.uint8)


def ortho_rgb(x0, y0, x1, y1, res):
    W, H = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    xs = x0 + (np.arange(W) + 0.5) * res + O[0]
    ys = y1 - (np.arange(H) + 0.5) * res + O[1]
    X, Y = np.meshgrid(xs, ys)
    out = np.full((H, W, 3), 40, np.uint8)
    tx = (np.floor(X / 50) * 50).astype(np.int64)
    ty = (np.ceil(Y / 50) * 50).astype(np.int64)
    d = MO.dalles()
    for cle in sorted(set(zip(tx.ravel().tolist(), ty.ravel().tolist()))):
        f = d.get(cle)
        if f is None:
            continue
        im = _rgb(f)
        m = (tx == cle[0]) & (ty == cle[1])
        c = np.clip(((X[m] - cle[0]) / 0.05).astype(int), 0, im.shape[1] - 1)
        r = np.clip(((cle[1] - Y[m]) / 0.05).astype(int), 0, im.shape[0] - 1)
        out[m] = im[r, c]
    return Image.fromarray(out)


def police(t):
    for nom in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nom, t)
        except OSError:
            pass
    return ImageFont.load_default()


def _src(p):
    s = str(p.get("src", "v1"))
    return "regle" if s.startswith("regle:") else s if s in COULEURS else "v1"


def _hachures(cal, e, x0, y1, res, col):
    """Bandes de hachures (bande_m au pas pas_m, cap_bandes_deg, origine) dans le contour de la zone."""
    import math
    from PIL import ImageDraw as ID
    zone = e["geom"][1][0][0]
    lo, hi = zone.min(axis=0), zone.max(axis=0)
    W, H = cal.size
    c0, c1 = max(0, int((lo[0] - x0) / res)), min(W, int((hi[0] - x0) / res) + 1)
    r0, r1 = max(0, int((y1 - hi[1]) / res)), min(H, int((y1 - lo[1]) / res) + 1)
    if c1 <= c0 or r1 <= r0:
        return
    m = Image.new("L", (c1 - c0, r1 - r0), 0)
    ID.Draw(m).polygon([((x - x0) / res - c0, (y1 - y) / res - r0) for x, y in zone], fill=255)
    msk = np.asarray(m) > 0
    X, Y = np.meshgrid(x0 + (np.arange(c0, c1) + 0.5) * res, y1 - (np.arange(r0, r1) + 0.5) * res)
    h = math.radians(float(e["cap_bandes_deg"]))
    n = np.array([-math.sin(h), math.cos(h)])
    o = repere(np.asarray([e["origine_bandes_l93"]], float))[0] if e.get("origine_bandes_l93") else zone.mean(axis=0)
    d = ((X - o[0]) * n[0] + (Y - o[1]) * n[1]) % float(e["pas_m"])
    bande = (d < float(e["bande_m"]) / 2) | (d > float(e["pas_m"]) - float(e["bande_m"]) / 2)
    a = np.zeros((r1 - r0, c1 - c0, 4), np.uint8)
    a[msk & bande] = col + (200,)
    a[msk & ~bande] = col + (40,)
    cal.alpha_composite(Image.fromarray(a, "RGBA"), (c0, r0))


def planche(base, chemin, emprise, res, titre, etiquettes=False):
    from marquages_controles import entite_locale
    import marquages_reprises as RP
    x0, y0, x1, y1 = emprise
    fond = ortho_rgb(x0, y0, x1, y1, res)
    img = Image.blend(fond, Image.new("RGB", fond.size, (0, 0, 0)), 0.45).convert("RGBA")
    cal = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(cal)
    k = max(1, int(round(0.05 / res)))

    def px(P):
        return [((x - x0) / res, (y1 - y) / res) for x, y in np.asarray(P)[:, :2]]
    # levé GAM brut
    for P in M.gam_lin():
        if P[:, 0].max() < x0 or P[:, 0].min() > x1 or P[:, 1].max() < y0 or P[:, 1].min() > y1:
            continue
        d.line(px(P), fill=(255, 150, 220, 200), width=1)
    comptes = {}
    feats = lire_geojson(Path(base) / "marquages.geojson")
    for f in sorted(feats, key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        e = entite_locale(f)
        try:
            polys = RP.empreinte(e)
        except Exception:                          # entité sans empreinte calculable : ignorée sur la planche
            polys = []
        if not polys:
            continue
        P = np.vstack([r for poly in polys for r in poly])
        if P[:, 0].max() < x0 or P[:, 0].min() > x1 or P[:, 1].max() < y0 or P[:, 1].min() > y1:
            continue
        s = _src(p)
        comptes[s] = comptes.get(s, 0) + 1
        virtuelle = (p.get("fabrication") or {}).get("statut") == "non_fabrique"
        col = COULEURS[s]
        if p["classe"] == "zone" and p["type"] == "hachures":
            _hachures(cal, e, x0, y1, res, col)
            continue
        for poly in polys:
            for j, r in enumerate(poly):
                if len(r) < 3:
                    continue
                if virtuelle:
                    d.polygon(px(r), outline=(255, 255, 255, 230), width=max(1, k))
                else:
                    d.polygon(px(r), fill=col + (200,) if j == 0 else (0, 0, 0, 0), outline=col + (255,))
        if etiquettes:
            c = P.mean(axis=0)
            d.text(((c[0] - x0) / res + 4, (y1 - c[1]) / res - 6), p["id"][3:], fill=(255, 255, 255, 230), font=police(9 * k))
    # indices v1 retirés
    corr = lire_geojson(Path(base) / "marquages_correspondance.geojson") if (Path(base) / "marquages_correspondance.geojson").exists() else []
    retires = {f["properties"]["id"] for f in corr if f["properties"]["devenir"] == "retire"}
    n_ret = 0
    for m in M.v1():
        if m["id"] not in retires:
            continue
        c = m["obb"]["c"]
        if not (x0 <= c[0] <= x1 and y0 <= c[1] <= y1):
            continue
        u, v = (c[0] - x0) / res, (y1 - c[1]) / res
        r_ = 3 * k
        d.line([(u - r_, v - r_), (u + r_, v + r_)], fill=(255, 40, 40, 220), width=max(1, k // 2))
        d.line([(u - r_, v + r_), (u + r_, v - r_)], fill=(255, 40, 40, 220), width=max(1, k // 2))
        n_ret += 1
    out = Image.alpha_composite(img, cal).convert("RGB")
    # légende
    W = out.size[0]
    lg = Image.new("RGB", (W, 30 + 22 * 7), (20, 20, 20))
    dl = ImageDraw.Draw(lg)
    f1 = police(16)
    dl.text((10, 6), titre, fill=(255, 255, 255), font=f1)
    y = 30
    for s in ("gam", "plan2025", "ortho2022", "regle", "v1"):
        dl.rectangle([10, y + 3, 30, y + 17], fill=COULEURS[s])
        dl.text((38, y), f"{LIBELLES[s]} : {comptes.get(s, 0)} entités", fill=(235, 235, 235), font=f1)
        y += 22
    dl.line([(10, y + 10), (30, y + 10)], fill=(255, 150, 220), width=2)
    dl.text((38, y), "polylignes brutes du levé GAM ; contour blanc : ligne virtuelle / hypothèse non peinte", fill=(235, 235, 235), font=f1)
    y += 22
    dl.text((10, y), f"x rouge : indice v1 retiré ({n_ret} dans la vue)", fill=(255, 120, 120), font=f1)
    tot = Image.new("RGB", (W, out.size[1] + lg.size[1]))
    tot.paste(out, (0, 0))
    tot.paste(lg, (0, out.size[1]))
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    tot.save(chemin, optimize=True)
    return comptes


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default=str(SORTIE / "base"))
    ap.add_argument("--sortie", default=str(SORTIE))
    ap.add_argument("--res", type=float, default=0.12)
    ap.add_argument("--vues", nargs="*", default=None)
    a = ap.parse_args()
    sortie = Path(a.sortie)
    if not a.vues:
        planche(a.base, sortie / "couverture_marquages.png", (-152.0, -152.0, 152.0, 152.0), a.res,
                "Couverture des marquages par source (fond : ortho PCRS 2022)")
    for nom, (x0, y0, x1, y1, res) in VUES.items():
        if a.vues and nom not in a.vues:
            continue
        planche(a.base, sortie / f"couverture_marquages_{nom}.png", (x0, y0, x1, y1), res,
                f"Couverture des marquages : {nom} ({res * 100:.1f} cm/px)", etiquettes=True)


if __name__ == "__main__":
    main()
