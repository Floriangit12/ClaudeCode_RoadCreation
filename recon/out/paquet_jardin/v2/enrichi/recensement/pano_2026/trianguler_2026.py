"""trianguler_2026.py : position au sol d'un objet vertical (mât, poteau) par intersection des visées
(azimuts) pointées dans les découpes des photos calées du 2026-07-28 (moindres carrés 2D).
Entrée : liste de (id8, fichier proj.json de la découpe, x, y) ; sortie : position locale et L93,
résidus de visée (m, à la distance de l'objet), angle d'intersection maximal entre visées."""
import json
import math
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import numpy as np  # noqa: E402
import vues_2026 as V  # noqa: E402
from camera import O  # noqa: E402
from projection import camera_virtuelle  # noqa: E402


def visee(pid, fproj, x, y):
    pr = json.loads((ICI / fproj).read_text(encoding="utf-8"))
    cam, statut = V.camera_2026(pid)
    cv = camera_virtuelle(cam, pr["lacet"], pr["tangage"], pr["fov"], tuple(pr["taille"]))
    d = cv.rayons(np.array([[x, y]], float))[0]
    return cam.C[:2].copy(), math.degrees(math.atan2(d[0], d[1])) % 360.0, statut


def trianguler(obs):
    C, U, st = [], [], []
    for pid, f, x, y in obs:
        c, az, s = visee(pid, f, x, y)
        C.append(c)
        U.append([math.sin(math.radians(az)), math.cos(math.radians(az))])
        st.append(s)
    C, U = np.array(C), np.array(U)
    N = np.c_[U[:, 1], -U[:, 0]]                       # normales aux visées
    A = N
    b = np.sum(N * C, axis=1)
    X, *_ = np.linalg.lstsq(A, b, rcond=None)
    res = A @ X - b
    ang = 0.0
    for i in range(len(U)):
        for j in range(i + 1, len(U)):
            ang = max(ang, math.degrees(math.acos(min(1.0, abs(float(U[i] @ U[j]))))))
    dist = np.hypot(*(X - C).T)
    return dict(local=[round(float(X[0]), 3), round(float(X[1]), 3)],
                l93=[round(float(X[0] + O[0]), 2), round(float(X[1] + O[1]), 2)],
                residus_m=[round(float(r), 3) for r in res], distances_m=[round(float(d), 1) for d in dist],
                angle_intersection_deg=round(ang, 1), n=len(obs), poses=st)


if __name__ == "__main__":
    obs = json.loads(sys.argv[1])
    print(json.dumps(trianguler(obs), ensure_ascii=False))
