import json, math, numpy as np
from pathlib import Path
R = Path("D:/ClaudeCode_RoadCreation")
O = np.array([917279.43, 6460289.98])

def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))["features"]

_tr = None
def to_l93(lon, lat):
    global _tr
    if _tr is None:
        from pyproj import Transformer
        _tr = Transformer.from_crs(4326, 2154, always_xy=True)
    return _tr.transform(lon, lat)

def lignes(fs, wgs=False):
    out = []
    for f in fs:
        g = f["geometry"]
        if g is None: continue
        cs = g["coordinates"]
        if g["type"] == "LineString": cs = [cs]
        elif g["type"] == "Polygon": cs = cs
        elif g["type"] == "MultiPolygon": cs = [r for p in cs for r in p]
        elif g["type"] != "MultiLineString": continue
        for l in cs:
            l = np.array(l, float)[:, :2]
            if wgs:
                x, y = to_l93(l[:, 0], l[:, 1]); l = np.c_[x, y]
            out.append(l)
    return out

def echantillonner(ls, pas=0.1):
    P = []
    for l in ls:
        for i in range(len(l) - 1):
            d = np.hypot(*(l[i+1] - l[i])); n = max(1, int(d / pas))
            t = np.arange(n)[:, None] / n
            P.append(l[i] + (l[i+1] - l[i]) * t)
        P.append(l[-1:])
    return np.vstack(P) if P else np.zeros((0, 2))

class Grille:
    """voisin le plus proche approché par hachage en cellules de c m"""
    def __init__(self, P, c=0.5):
        self.P = P; self.c = c; self.d = {}
        k = np.floor(P / c).astype(np.int64)
        for i, (a, b) in enumerate(k):
            self.d.setdefault((a, b), []).append(i)
    def dist(self, Q, rmax=2.0):
        out = np.full(len(Q), np.inf); n = int(math.ceil(rmax / self.c))
        k = np.floor(Q / self.c).astype(np.int64)
        for j, (a, b) in enumerate(k):
            best = np.inf
            for da in range(-n, n + 1):
                for db in range(-n, n + 1):
                    ids = self.d.get((a + da, b + db))
                    if ids:
                        dd = np.hypot(*(self.P[ids] - Q[j]).T).min()
                        if dd < best: best = dd
            out[j] = best
        return out

def ortho(x0, y0, x1, y1, res=0.05, dossier="data/sites/paquet_jardin/ortho5cm_2022"):
    """mosaïque de l'ortho PCRS 2022 sur la boîte L93 (x0,y0)-(x1,y1), résolution res (m/px), nord en haut"""
    from PIL import Image
    W = int(round((x1 - x0) / res)); H = int(round((y1 - y0) / res))
    out = np.zeros((H, W, 3), np.uint8)
    d = R / dossier
    for jgw in d.glob("*.jgw"):
        a = [float(v) for v in jgw.read_text().split()]
        px, ox, oy = a[0], a[4] - a[0] / 2, a[5] - a[3] / 2
        tx0, ty1 = ox, oy
        im = None
        tw = th = None
        # taille via PIL (lazy)
        img = Image.open(jgw.with_suffix(".jpg")); tw, th = img.size
        tx1, ty0 = tx0 + tw * px, ty1 - th * px
        if tx1 <= x0 or tx0 >= x1 or ty1 <= y0 or ty0 >= y1: continue
        ix0, ix1 = max(x0, tx0), min(x1, tx1); iy0, iy1 = max(y0, ty0), min(y1, ty1)
        crop = img.crop((int(round((ix0 - tx0) / px)), int(round((ty1 - iy1) / px)), int(round((ix1 - tx0) / px)), int(round((ty1 - iy0) / px))))
        cw = int(round((ix1 - ix0) / res)); ch = int(round((iy1 - iy0) / res))
        if cw <= 0 or ch <= 0: continue
        crop = crop.convert("RGB").resize((cw, ch), Image.LANCZOS)
        c0 = int(round((ix0 - x0) / res)); r0 = int(round((y1 - iy1) / res))
        out[r0:r0 + ch, c0:c0 + cw] = np.asarray(crop)[:H - r0, :W - c0]
    return out
