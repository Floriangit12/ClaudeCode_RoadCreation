"""Planche-contact des 360° d'une séance (bande d'élévation −35..+20°), pour repérer chantiers, panneaux
et déviations. Sortie photos_non_versionnees/ (jamais versionné). python planche_360.py <date> [src]"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chrono import candidats, image_de
from commun_chg import PHOTOS_NV, police, ecrire_json

date = sys.argv[1]
src = sys.argv[2] if len(sys.argv) > 2 else "panoramax"
cs = sorted([c for c in candidats() if c["date"] == date and c["src"] == src and c["is360"]], key=lambda c: c["dt"])
W = 1400
cel, meta = [], []
for c in cs:
    a = image_de(c)
    H0, W0 = a.shape[:2]
    v0, v1 = int(H0 * (0.5 - 20 / 180)), int(H0 * (0.5 + 35 / 180))
    # recentrer : colonne 0 = azimut grille 0 (nord)
    lac = float(c["cam"].pose[3])
    dec = int(round((-lac / 360.0) * W0)) % W0 + W0 // 2
    a = np.roll(a[v0:v1], -dec, axis=1)
    im = Image.fromarray(a).resize((W, round(W * (v1 - v0) / W0)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for az in range(0, 360, 45):
        u = az / 360 * W
        d.line([(u, 0), (u, 12)], fill=(255, 255, 0), width=2)
        d.text((u + 3, 0), str(az), fill=(255, 255, 0), font=police(12))
    x, y = c["cam"].C[:2]
    d.rectangle([0, im.height - 18, 520, im.height], fill=(0, 0, 0))
    d.text((3, im.height - 17), f"{c['dt'][:16]} {src} {c['id'][:10]} ({x:+.0f};{y:+.0f}) — azimuts grille", fill=(255, 255, 255), font=police(13))
    cel.append(im)
    meta.append(dict(id=c["id"], date=c["dt"], lien=c["lien"], auteur=c["auteur"], position_local=[round(float(x), 1), round(float(y), 1)]))
for k in range(0, len(cel), 6):
    lot = cel[k:k + 6]
    pl = Image.new("RGB", (W, sum(i.height for i in lot) + 4 * len(lot)), (40, 40, 40))
    yy = 0
    for i in lot:
        pl.paste(i, (0, yy)); yy += i.height + 4
    out = PHOTOS_NV / "seances_360"
    out.mkdir(parents=True, exist_ok=True)
    pl.save(out / f"{date}_{src}_{k // 6 + 1}.jpg", quality=85)
    print(out / f"{date}_{src}_{k // 6 + 1}.jpg")
ecrire_json(PHOTOS_NV / "seances_360" / f"{date}_{src}.json", meta)
