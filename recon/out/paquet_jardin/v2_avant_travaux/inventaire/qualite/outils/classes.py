import sys, collections
sys.path.insert(0, "C:/Users/flori/AppData/Local/Temp/claude/D--/193706ca-c280-454e-8894-a24c258637c3/scratchpad/q")
from qutil import *
from PIL import Image, ImageDraw, ImageFilter
res = 0.25
X0, Y0, X1, Y1 = O[0]-150, O[1]-150, O[0]+150, O[1]+150
N = 1200
orth = ortho(X0, Y0, X1, Y1, res).astype(np.float32)
np.save("orth025.npy", orth)
# hauteur LiDAR (visualisation 8 bits) -> masque canopée
hag = np.zeros((N, N), np.float32)
idx = json.loads((R/"data/sites/paquet_jardin/lidar/height_above_ground_25cm/index.json").read_text(encoding="utf-8"))
for t in idx:
    im = np.asarray(Image.open(R/"data/sites/paquet_jardin/lidar/height_above_ground_25cm"/t["file"]).convert("L"), np.float32)
    bx = t["l93_bbox"]; c0 = int(round((bx[0]-X0)/res)); r0 = int(round((Y1-bx[3])/res))
    hag[r0:r0+im.shape[0], c0:c0+im.shape[1]] = np.maximum(hag[r0:r0+im.shape[0], c0:c0+im.shape[1]], im[:N-r0, :N-c0])
print("hag quantiles", np.percentile(hag, [50, 75, 90, 95, 99]))
np.save("hag025.npy", hag)
def rast(polys, draw, val):
    for poly in polys:
        for k, ring in enumerate(poly):
            pts = [((x-X0)/res, (Y1-y)/res) for x, y in np.asarray(ring)[:, :2]]
            if len(pts) >= 3: draw.polygon(pts, fill=(val if k == 0 else 0))
def anneaux(g):
    if g["type"] == "Polygon": return [g["coordinates"]]
    if g["type"] == "MultiPolygon": return g["coordinates"]
    return []
# zone de travaux / construite (package surfaces_2026)
zt = Image.new("L", (N, N), 0); dz = ImageDraw.Draw(zt)
for f in load(R/"recon/out/paquet_jardin/package/donnees/surfaces/surfaces_2026.geojson"):
    if f["properties"].get("etat") in ("modifie_2025", "construit_2023_2024"):
        rast(anneaux(f["geometry"]), dz, 255)
zt = zt.filter(ImageFilter.MaxFilter(13))   # +1,5 m
ztr = np.asarray(zt) > 0
np.save("travaux025.npy", ztr)
print("part zone travaux/construite: %.1f %%" % (100*ztr.mean()))
r, g, b = orth[..., 0], orth[..., 1], orth[..., 2]
exg = (2*g - r - b) / np.maximum(r + g + b, 1)
lum = (r + g + b) / 3
stats = collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0])
rows = []
for f in load(R/"recon/out/paquet_jardin/v2/description/base/surfaces.geojson"):
    p = f["properties"]
    m = Image.new("L", (N, N), 0); rast(anneaux(f["geometry"]), ImageDraw.Draw(m), 255)
    m = np.asarray(m) > 0
    if m.sum() < 8: continue
    hors = m & ~ztr & (hag < 20)
    if hors.sum() < 8: continue
    vert = (exg[hors] > 0.06).mean()
    rows.append((p["id"], p["classe"], (p.get("revetement") or {}).get("materiau_id"), float(hors.sum()*res*res), float(vert), float(lum[hors].mean()), (p.get("prov") or {}).get("classe", {}).get("src", "?"), bool(p.get("limite_raster"))))
json.dump(rows, open("classes_rows.json", "w"))
agg = collections.defaultdict(lambda: [0.0, 0.0])
for _, c, mat, a, v, l, s, lr in rows:
    agg[c][0] += a; agg[c][1] += a * v
for c, (a, av) in sorted(agg.items(), key=lambda t: -t[1][0]):
    print(f"{c:22s} aire hors travaux {a:9.0f} m2  part verte ortho2022 {100*av/max(a,1):5.1f} %")
veg = {"espace_vert", "terre_plein_vegetal"}
dur = {"chaussee", "trottoir", "parking", "piste_cyclable", "acces_riverain", "quai_bus"}
inc_v = [(i, c, a, v) for i, c, mat, a, v, l, s, lr in rows if c in veg and v < 0.25 and a > 5]
inc_d = [(i, c, a, v) for i, c, mat, a, v, l, s, lr in rows if c in dur and v > 0.5 and a > 5]
print("espace vert peu vert (<25 % de pixels verts) :", len(inc_v), round(sum(a for *_, a, v in inc_v)), "m2")
print("revetu majoritairement vert (>50 %) :", len(inc_d), round(sum(a for *_, a, v in inc_d)), "m2")
for t in sorted(inc_v, key=lambda t: -t[2])[:8]: print("  V", t)
for t in sorted(inc_d, key=lambda t: -t[2])[:8]: print("  D", t)
tot = sum(a for _, c, mat, a, v, l, s, lr in rows if c in veg | dur)
print("aire controlee", round(tot), "incoherente", round(sum(a for *_, a, v in inc_v) + sum(a for *_, a, v in inc_d)))
