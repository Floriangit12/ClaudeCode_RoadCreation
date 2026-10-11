import sys
sys.path.insert(0, "C:/Users/flori/AppData/Local/Temp/claude/D--/193706ca-c280-454e-8894-a24c258637c3/scratchpad/q")
from qutil import *
from PIL import Image, ImageDraw, ImageFont
cx, cy, half, res, out = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
x0, y0, x1, y1 = O[0]+cx-half, O[1]+cy-half, O[0]+cx+half, O[1]+cy+half
base = Image.fromarray(ortho(x0, y0, x1, y1, res)).convert("RGBA")
lay = Image.new("RGBA", base.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
COL = {"espace_vert": (0, 200, 0), "terre_plein_vegetal": (0, 140, 0), "parking": (160, 0, 200), "chaussee": (60, 60, 255),
       "trottoir": (255, 160, 0), "piste_cyclable": (255, 0, 120), "acces_riverain": (0, 200, 200), "ilot": (255, 255, 0),
       "quai_bus": (255, 80, 80), "autre": (128, 128, 128), "emprise_bordure": (255, 255, 255)}
px = lambda l: [((x - x0) / res, (y1 - y) / res) for x, y in np.asarray(l)[:, :2]]
for f in load(R/"recon/out/paquet_jardin/v2/description/base/surfaces.geojson"):
    c = COL.get(f["properties"]["classe"], (255, 255, 255))
    g = f["geometry"]; polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    for poly in polys:
        for k, ring in enumerate(poly):
            d.polygon(px(ring), fill=c + (70,) if k == 0 else None, outline=c + (230,))
im = Image.alpha_composite(base, lay).convert("RGB")
dd = ImageDraw.Draw(im)
for l in lignes(load(R/"recon/out/paquet_jardin/v2/description/base/bordures.geojson")):
    dd.line(px(l), fill=(255, 0, 0), width=2)
try: f = ImageFont.truetype("arial.ttf", 14)
except Exception: f = ImageFont.load_default()
y = 5
for k, c in COL.items():
    dd.rectangle((5, y, 20, y + 12), fill=c); dd.text((24, y - 2), k, fill="white", font=f, stroke_width=2, stroke_fill="black"); y += 16
dd.line((5, y + 6, 20, y + 6), fill=(255, 0, 0), width=3); dd.text((24, y - 2), "bordures decrites (face vue)", fill="white", font=f, stroke_width=2, stroke_fill="black")
im.save(out); print(im.size)
