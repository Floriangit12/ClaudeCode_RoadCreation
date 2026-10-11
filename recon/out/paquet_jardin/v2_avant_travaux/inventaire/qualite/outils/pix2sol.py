import re, numpy as np, sys
t = open("D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/controle/rendu/cameras_controle.usda", encoding="utf-8").read()
cams = {}
for m in re.finditer(r'def Camera "(\w+)"(.*?)xformOp:transform = (\(.*?\) \))', t, re.S):
    nom, b, mx = m.group(1), m.group(2), m.group(3)
    f = float(re.search(r"focalLength = ([\d.e-]+)", b).group(1)); ha = float(re.search(r"horizontalAperture = ([\d.e-]+)", b).group(1))
    va = re.search(r"verticalAperture = ([\d.e-]+)", b); va = float(va.group(1)) if va else ha
    M = np.array(eval(mx.replace("(", "[").replace(")", "]")))
    cams[nom] = (f, ha, va, M)
z = np.load("D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/controle/cache/sol_grille.npz")["z"]
def zs(x, y):
    i = int((x + 150) / 0.1); j = int((y + 150) / 0.1)
    if 0 <= i < 3001 and 0 <= j < 3001:
        v = z[j, i]
        return float(v) if np.isfinite(v) else 0.0
    return 0.0
def sol(nom, u, v, W, H):
    f, ha, va, M = cams[nom]
    va = ha * H / W if abs(va - ha) < 1e-9 and W != H else va
    d = np.array([(u / W - 0.5) * ha, (0.5 - v / H) * va, -f])
    dw = d[0] * M[0, :3] + d[1] * M[1, :3] + d[2] * M[2, :3]; dw /= np.linalg.norm(dw)
    C = M[3, :3]
    for s in np.arange(0.2, 400, 0.05):
        p = C + s * dw
        if p[2] <= zs(p[0], p[1]): return p.round(2), round(s, 1)
    return None, None
if __name__ == "__main__":
    for a in sys.argv[1:]:
        nom, u, v, W, H = a.split(":")
        print(nom, u, v, sol(nom, float(u), float(v), int(W), int(H)))
