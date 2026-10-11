import sys
from qutil import *
from PIL import Image, ImageDraw, ImageFont
cx, cy, half, res, out = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
x0, y0, x1, y1 = O[0]+cx-half, O[1]+cy-half, O[0]+cx+half, O[1]+cy+half
im = Image.fromarray(ortho(x0, y0, x1, y1, res)).convert("RGB")
d = ImageDraw.Draw(im)
def px(l):
    return [((x - x0) / res, (y1 - y) / res) for x, y in l]
for l in lignes(load(R/'data/sites/paquet_jardin/etat_2026/bordure_lin_L93.geojson')):
    d.line(px(l), fill=(255, 0, 0), width=2)
for l in lignes(load(R/'data/sites/paquet_jardin/etat_2026/signalisation_horizontale_lin_L93.geojson')):
    d.line(px(l), fill=(0, 255, 255), width=2)
im.save(out)
print(im.size)
