"""ortho_crop.py : extrait de l'ortho PCRS 2022 (5 cm) autour d'un point local, avec arbres/mobilier de la description et points marqués."""
import sys
import numpy as np
from PIL import Image, ImageDraw
import overlay_pnx as OV
from projection import ortho_mosaique

def crop(x, y, demi=20.0, nom="ortho", points=()):
    img, x0, y1 = ortho_mosaique()
    pas = 0.05
    i0, i1 = int((x - demi - x0) / pas), int((x + demi - x0) / pas)
    j0, j1 = int((y1 - (y + demi)) / pas), int((y1 - (y - demi)) / pas)
    a = (np.clip(img[j0:j1, i0:i1], 0, 1) * 255).astype(np.uint8)
    im = Image.fromarray(a).convert("RGB")
    dr = ImageDraw.Draw(im)
    f = lambda X, Y: ((X - (x0 + i0 * pas)) / pas, ((y1 - j0 * pas) - Y) / pas)
    for e in OV.entites():
        if e["kind"] in ("arbre", "mat"):
            u, v = f(e["foot"][0], e["foot"][1])
            if 0 <= u < im.width and 0 <= v < im.height:
                c = (0, 255, 0) if e["kind"] == "arbre" else (255, 0, 0)
                dr.ellipse([u - 6, v - 6, u + 6, v + 6], outline=c, width=2)
                dr.text((u + 8, v - 6), e["id"], fill=c)
    for (X, Y, t) in points:
        u, v = f(X, Y)
        dr.line([u - 10, v - 10, u + 10, v + 10], fill=(255, 255, 0), width=3)
        dr.line([u - 10, v + 10, u + 10, v - 10], fill=(255, 255, 0), width=3)
        dr.text((u + 12, v + 4), t, fill=(255, 255, 0))
    im = im.resize((800, 800))
    im.save(OV.CROPS / f"{nom}.jpg", quality=90)
    print(nom)

if __name__ == "__main__":
    a = sys.argv[1:]
    pts = []
    for k in range(4, len(a), 3):
        pts.append((float(a[k]), float(a[k + 1]), a[k + 2]))
    crop(float(a[0]), float(a[1]), float(a[2]), a[3], pts)
