import sys, json
sys.path.insert(0, "C:/Users/flori/AppData/Local/Temp/claude/D--/193706ca-c280-454e-8894-a24c258637c3/scratchpad/q")
from qutil import *
res = 0.05
X0, Y0, X1, Y1 = O[0]-150, O[1]-150, O[0]+150, O[1]+150
img = np.load("orth05_gris.npy"); trav = np.load("travaux025.npy")
def val(x, y):
    c = (x - X0) / res - 0.5; r = (Y1 - y) / res - 0.5
    c0 = np.clip(np.floor(c).astype(int), 0, img.shape[1]-2); r0 = np.clip(np.floor(r).astype(int), 0, img.shape[0]-2)
    tc, tr = c - c0, r - r0
    return (img[r0, c0]*(1-tc) + img[r0, c0+1]*tc)*(1-tr) + (img[r0+1, c0]*(1-tc) + img[r0+1, c0+1]*tc)*tr
def en_travaux(x, y):
    c = int((x - X0) / 0.25); r = int((Y1 - y) / 0.25)
    return bool(trav[r, c]) if 0 <= c < 1200 and 0 <= r < 1200 else True
offs = np.arange(-0.6, 0.6001, 0.025)
out = {"hors": [], "travaux": []}; sans = {"hors": 0, "travaux": 0}
for f in load(R/"recon/out/paquet_jardin/v2/description/base/bordures.geojson"):
    src = f["properties"]["prov"].get("geometrie", {}).get("src", "?")
    a = np.array(f["geometry"]["coordinates"], float)[:, :2]
    seg = np.diff(a, axis=0); L = np.hypot(*seg.T); s = np.r_[0, np.cumsum(L)]
    if s[-1] < 3: continue
    for t in np.arange(1.0, s[-1]-1.0, 1.0):
        k = min(max(np.searchsorted(s, t) - 1, 0), len(seg)-1)
        p = a[k] + seg[k] * (t - s[k]) / max(L[k], 1e-9); tg = seg[k] / max(L[k], 1e-9); n = np.array([-tg[1], tg[0]])
        pts = p[None] + offs[:, None] * n[None]
        prof = np.mean([val(pts[:, 0] + tg[0]*dt, pts[:, 1] + tg[1]*dt) for dt in (-0.25, 0, 0.25)], axis=0)
        gr = np.abs(np.gradient(prof, 0.025))
        z = "travaux" if en_travaux(*p) else "hors"
        loc = [i for i in range(1, len(gr)-1) if gr[i] >= gr[i-1] and gr[i] >= gr[i+1] and gr[i] > 60]
        if not loc: sans[z] += 1; continue
        out[z].append(min(abs(offs[i]) for i in loc))
rap = {}
for z, v in out.items():
    v = np.array(v); tot = len(v) + sans[z]
    rap[z] = {"echantillons_1m": tot, "sans_arete_nette": sans[z], "p50_m": round(float(np.percentile(v, 50)), 3), "p90_m": round(float(np.percentile(v, 90)), 3),
              "part_arete_a_10cm": round(float((v <= 0.10).sum() / tot), 3), "part_arete_a_20cm": round(float((v <= 0.20).sum() / tot), 3)}
    print(z, rap[z])
json.dump(rap, open("ecart_ortho.json", "w"), indent=1)
