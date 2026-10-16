"""Planches de contrôle des profils de bordures et de caniveaux (sections 2D de specs_assets_route.PROFILS).

    python recon/pcg/assets_route/planche_profils.py [--sortie D:/DocRoute/14_Assets_Route_Statics/controle]

Chaque planche fait au plus 1020 × 1060 px : elle entre SANS réduction dans l'entrée image native (pas de découpe
nécessaire). Échelle uniforme par planche (1 px/mm pour les bordures, 0,6 px/mm pour les caniveaux), quadrillage de
50 mm, chaussée à GAUCHE (u = 0 = face vue), trottoir à droite ; trait tireté = niveau de la chaussée pour la vue
nominale moyenne (vue_nominale_m), cote base × H et confiance dans l'en-tête de chaque case.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import specs_assets_route as SP  # noqa: E402

CASE, NCOL, NLIG = 340, 3, 3


def police(t, gras=False):
    try:
        return ImageFont.truetype("arialbd.ttf" if gras else "arial.ttf", t)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def dessiner_case(d, x0, y0, pid, p, ech):
    f, fb = police(12), police(14, True)
    d.rectangle([x0, y0, x0 + CASE - 1, y0 + CASE - 1], outline=(120, 120, 120))
    marge_g, marge_b = 30, 26
    ox, oy = x0 + marge_g, y0 + CASE - marge_b                 # origine (u = 0, v = 0)
    pas = 50
    for k in range(0, 1000, pas):
        X = ox + k * ech
        if X < x0 + CASE - 4:
            d.line([X, y0 + 40, X, oy], fill=(225, 225, 225))
        Y = oy - k * ech
        if Y > y0 + 40:
            d.line([ox, Y, x0 + CASE - 4, Y], fill=(225, 225, 225))
    pts = [(ox + u * 1000 * ech, oy - v * 1000 * ech) for u, v in p["pts"]]
    d.polygon(pts, fill=(200, 200, 200), outline=(0, 0, 0))
    vue = p.get("vue")
    if vue:
        vm = 0.5 * (vue[0] + vue[1])
        Y = oy - (p["H"] - vm) * 1000 * ech
        for X in range(int(x0 + 4), int(ox), 8):
            d.line([X, Y, X + 4, Y], fill=(30, 60, 200), width=2)
        d.text((x0 + 4, Y - 16), f"vue {vm * 100:.0f} cm", fill=(30, 60, 200), font=f)
    d.text((x0 + 6, y0 + 4), f"{pid}  {p['base'] * 1000:.0f} × {p['H'] * 1000:.0f} mm", fill="black", font=fb)
    s0 = p["sources"][0]
    d.text((x0 + 6, y0 + 22), f"{s0['doc']} p. {s0.get('page', '?')} — confiance {p['confiance']}", fill=(80, 80, 80), font=f)
    can = p["famille"] == "caniveau"
    d.text((x0 + 4, oy + 6), "← chaussée" if can else "← chaussée (face vue)", fill=(80, 80, 80), font=f)
    d.text((x0 + CASE - (110 if can else 70), oy + 6), "face de bordure →" if can else "trottoir →", fill=(80, 80, 80), font=f)


def planche(ids, ech, titre, fichier):
    W, H = NCOL * CASE, NLIG * CASE + 40
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    d.text((8, 10), titre, fill="black", font=police(16, True))
    for k, pid in enumerate(ids):
        c, l = k % NCOL, k // NCOL
        dessiner_case(d, c * CASE, 40 + l * CASE, pid, SP.PROFILS[pid], ech)
    im.save(fichier)
    print(fichier, im.size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default="D:/DocRoute/14_Assets_Route_Statics/controle")
    a = ap.parse_args()
    out = Path(a.sortie)
    out.mkdir(parents=True, exist_ok=True)
    bord = [k for k, p in SP.PROFILS.items() if p["famille"] != "caniveau"]
    can = [k for k, p in SP.PROFILS.items() if p["famille"] == "caniveau"]
    for f in out.glob("profils_*.png"):
        f.unlink()
    n = NCOL * NLIG
    for i in range(0, len(bord), n):
        planche(bord[i:i + n], 1.0 if all(SP.PROFILS[b]["base"] <= 0.31 and SP.PROFILS[b]["H"] <= 0.30 for b in bord[i:i + n]) else 0.6,
                f"Profils de bordures route_fr ({i // n + 1}) — quadrillage 50 mm — specs_assets_route.PROFILS",
                out / f"profils_bordures_{i // n + 1}.png")
    planche(can, 0.6, "Profils de caniveaux route_fr — quadrillage 50 mm (u = 0 côté chaussée)", out / "profils_caniveaux.png")


if __name__ == "__main__":
    main()
