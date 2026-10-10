"""outils_pano2.py : pointage dans les découpes de overlay_pnx.py (agent VISION-PANORAMAX-2).

  python outils_pano2.py loupe <crop> u v [fov] [nom]     zoom natif centré sur le pixel (u, v) d'une découpe
  python outils_pano2.py sol <crop> u v                   pixel -> rayon -> point au sol (MNT 2026), local + L93
  python outils_pano2.py tri <crop> u v <crop> u v ...    triangulation (moindres carrés 3D des rayons) ; si --mat :
                                                          intersection des plans verticaux (azimuts seuls, pour un mât)
  python outils_pano2.py pres x y [r]                     entités de la description à moins de r m (défaut 3)
<crop> = nom sans extension dans crops/ (ex. e5d79de9_v1_a152) ou chemin d'un _proj.json.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import overlay_pnx as OV  # noqa: E402
from projection import decoupe_perspective, intersection_sol  # noqa: E402
from camera import O  # noqa: E402


def _js(crop):
    p = Path(crop)
    if p.suffix == ".json":
        return p
    return OV.CROPS / f"{crop}_proj.json"


def rayon(crop, u, v):
    cv, m = OV.cam_depuis_json(_js(crop))
    d = cv.rayons(np.array([[u, v]], float))[0]
    return cv.C.copy(), d, m


def sol(crop, u, v):
    C, d, m = rayon(crop, u, v)
    t = intersection_sol(C, d[None])[0]
    if not np.isfinite(t):
        return None
    X = C + t * d
    return dict(local=[round(float(X[0]), 3), round(float(X[1]), 3), round(float(X[2]), 3)],
                l93=[round(float(X[0] + O[0]), 3), round(float(X[1] + O[1]), 3)], distance=round(float(t), 2),
                photo=m["photo"], date=m["date"])


def tri(obs, mat=False):
    """obs : [(crop, u, v), ...]. Renvoie point local, résidus (m) et angle max entre visées."""
    Cs, Ds = [], []
    for crop, u, v in obs:
        C, d, m = rayon(crop, u, v)
        Cs.append(C)
        Ds.append(d)
    Cs, Ds = np.array(Cs), np.array(Ds)
    if mat:
        D2 = Ds[:, :2] / np.linalg.norm(Ds[:, :2], axis=1, keepdims=True)
        A, b = np.zeros((2, 2)), np.zeros(2)
        for C, d in zip(Cs, D2):
            P = np.eye(2) - np.outer(d, d)
            A += P
            b += P @ C[:2]
        X = np.linalg.solve(A, b)
        res = [float(np.linalg.norm((np.eye(2) - np.outer(d, d)) @ (X - C[:2]))) for C, d in zip(Cs, D2)]
        X = np.r_[X, np.nan]
        Dang = D2
    else:
        A, b = np.zeros((3, 3)), np.zeros(3)
        for C, d in zip(Cs, Ds):
            P = np.eye(3) - np.outer(d, d)
            A += P
            b += P @ C
        X = np.linalg.solve(A, b)
        res = [float(np.linalg.norm((np.eye(3) - np.outer(d, d)) @ (X - C))) for C, d in zip(Cs, Ds)]
        Dang = Ds[:, :2] / np.linalg.norm(Ds[:, :2], axis=1, keepdims=True)
    ang = 0.0
    for i in range(len(Dang)):
        for j in range(i + 1, len(Dang)):
            c = abs(float(Dang[i] @ Dang[j]))
            ang = max(ang, math.degrees(math.acos(min(1.0, c))))
    return dict(local=[round(float(v), 3) for v in X], l93=[round(float(X[0] + O[0]), 3), round(float(X[1] + O[1]), 3)],
                residus_m=[round(r, 3) for r in res], angle_max_deg=round(ang, 1))


def loupe(crop, u, v, fov=12.0, nom=None, taille=900):
    js = _js(crop)
    C, d, m = rayon(crop, u, v)
    lac = math.degrees(math.atan2(d[0], d[1])) % 360
    tg = math.degrees(math.asin(max(-1, min(1, d[2]))))
    cam, statut = OV.camera_photo(m["photo"])
    img, cv = decoupe_perspective(m["photo"], lac, tg, fov, (taille, taille), cam=cam)
    nom = nom or f"{Path(js).stem.replace('_proj', '')}_loupe_{int(u)}_{int(v)}"
    img.save(OV.CROPS / f"{nom}.jpg", quality=94)
    ov, projs = OV.dessiner(img, cv, dmax=80, dlab=80, familles=("support", "tete", "arbre", "correction", "ilot", "ponctuel", "marquage", "bordure"))
    OV.cartouche(ov, f"{m['photo']} {m['date']} loupe fov {fov:.0f} az {lac:.1f} tg {tg:.1f}")
    ov.save(OV.CROPS / f"{nom}_ov.jpg", quality=92)
    meta = dict(photo=m["photo"], date=m["date"], pose_statut=statut, vue=dict(lacet=lac, tangage=tg, fov=fov, taille=[taille, taille]),
                cam_virtuelle=dict(pose=[round(float(x), 5) for x in cv.pose], f=cv.f, W=cv.W, H=cv.H), entites=projs)
    (OV.CROPS / f"{nom}_proj.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(nom)
    return nom


def pres(x, y, r=3.0):
    out = []
    for e in OV.entites():
        if e["kind"] == "ligne":
            P = e["P"]
            d = float(np.min(np.hypot(P[:, 0] - x, P[:, 1] - y)))
        elif e["kind"] in ("mat", "arbre"):
            d = math.hypot(e["foot"][0] - x, e["foot"][1] - y)
        elif e["kind"] == "tete":
            d = math.hypot(e["C"][0] - x, e["C"][1] - y)
        else:
            d = math.hypot(e["B"][0] - x, e["B"][1] - y)
        if d <= r and e["fam"] != "bordure_gam":
            out.append((round(d, 2), e["id"], e["fam"], e.get("lab")))
    for o in sorted(out)[:25]:
        print(o)
    return sorted(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "loupe":
        loupe(a[1], float(a[2]), float(a[3]), float(a[4]) if len(a) > 4 else 12.0, a[5] if len(a) > 5 else None)
    elif a[0] == "sol":
        print(json.dumps(sol(a[1], float(a[2]), float(a[3]))))
    elif a[0] == "tri":
        mat = "--mat" in a
        b = [x for x in a[1:] if x != "--mat"]
        obs = [(b[i], float(b[i + 1]), float(b[i + 2])) for i in range(0, len(b), 3)]
        print(json.dumps(tri(obs, mat)))
    elif a[0] == "pres":
        pres(float(a[1]), float(a[2]), float(a[3]) if len(a) > 3 else 3.0)


# --------------------------------------------------------------------------- zones de travaux 2025
def _dans_poly(x, y, r):
    r = np.asarray(r)
    xs, ys = r[:, 0], r[:, 1]
    c = False
    j = len(r) - 1
    for i in range(len(r)):
        if ((ys[i] > y) != (ys[j] > y)) and (x < (xs[j] - xs[i]) * (y - ys[i]) / (ys[j] - ys[i] + 1e-12) + xs[i]):
            c = not c
        j = i
    return c


def travaux(x, y):
    """Zones de relief_zones_2026 contenant le point local (x, y) + bordures v2 'zone_travaux_2025' à < 1,5 m."""
    d = OV.lire(OV.PKG / "relief/relief_zones_2026.geojson")
    out = []
    X, Y = x + O[0], y + O[1]
    for f in d["features"]:
        z = f["properties"].get("zone")
        for r in OV._anneaux(f["geometry"]):
            if _dans_poly(X, Y, np.array(r)[:, :2]):
                out.append(z)
    for f in OV.lire(OV.DESC / "base/bordures.geojson")["features"]:
        P = np.array(f["geometry"]["coordinates"])[:, :2] - np.array(O[:2])
        if np.min(np.hypot(P[:, 0] - x, P[:, 1] - y)) < 1.5:
            out.append(f"{f['properties']['id']}:travaux2025={f['properties'].get('zone_travaux_2025')}")
    return out


def ids(crop, u, v, r=60):
    """Entités projetées (pied ou uv) à moins de r px du pixel (u, v) d'une découpe."""
    m = json.loads(_js(crop).read_text(encoding="utf-8"))
    out = []
    for e in m.get("entites", []):
        p = e.get("pied") or e.get("uv")
        d = math.hypot(p[0] - u, p[1] - v)
        if e.get("sommet"):
            # distance au segment pied-sommet
            a, b = np.array(e["pied"]), np.array(e["sommet"])
            t = np.clip(np.dot([u - a[0], v - a[1]], b - a) / max(1e-9, np.dot(b - a, b - a)), 0, 1)
            d = float(np.hypot(*(a + t * (b - a) - [u, v])))
        if d <= r:
            out.append((round(d, 1), e["id"], e["fam"], e.get("d"), p))
    for o in sorted(out):
        print(o)
    return sorted(out)


if __name__ == "__main__" and sys.argv[1] == "ids":
    ids(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]) if len(sys.argv) > 5 else 60)


def hauteur(crop, u, v, x, y):
    """Altitude locale du point de la verticale (x, y) vu au pixel (u, v) ; et hauteur au-dessus du MNT."""
    C, d, m = rayon(crop, u, v)
    h = math.hypot(d[0], d[1])
    t = math.hypot(x - C[0], y - C[1]) / max(h, 1e-9)
    z = float(C[2] + t * d[2])
    zs = float(OV.z_mnt(x, y))
    return dict(z_local=round(z, 3), h_sol=round(z - zs, 3), z_sol=round(zs, 3))


if __name__ == "__main__" and sys.argv[1] == "haut":
    print(hauteur(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6])))
