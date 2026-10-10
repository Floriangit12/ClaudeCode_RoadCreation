"""Repere unique de la scene Paquet Jardin (seule implementation de la conversion).

local = Lambert-93 - O, z = NGF - 216.30, en metres, Z haut (repere direct).
UE (comme CARLA / OpenDRIVE) : X = x*100, Y = -y*100, Z = z*100 (cm, repere indirect), yaw_UE = -yaw.
Orientations : rpy_deg = [r, p, y] ZYX intrinseques (R = Rz(y).Ry(p).Rx(r), rotations directes autour des
axes locaux) ou quaternion q = [x, y, z, w] (meme rotation). Le miroir Y (M = diag(1,-1,1)) conjugue la rotation
(R_ue = M.R.M) : Rotator(roll=+r, pitch=-p, yaw=-y), Quat(-x, +y, -z, w) (test : tests/test_rotations.py).
Python pur : utilisable dans l'editeur UE et hors UE (tests, hython).
"""
from __future__ import annotations

import math

O_L93 = (917279.43, 6460289.98, 216.30)   # E, N, altitude NGF de l'origine locale
EPSG = 2154


def l93_vers_local(e: float, n: float, h: float = O_L93[2]) -> tuple[float, float, float]:
    return (e - O_L93[0], n - O_L93[1], h - O_L93[2])


def local_vers_l93(x: float, y: float, z: float = 0.0) -> tuple[float, float, float]:
    return (x + O_L93[0], y + O_L93[1], z + O_L93[2])


def local_vers_ue(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Position locale (m) -> position UE (cm)."""
    return (x * 100.0, -y * 100.0, z * 100.0)


def ue_vers_local(X: float, Y: float, Z: float) -> tuple[float, float, float]:
    return (X / 100.0, -Y / 100.0, Z / 100.0)


def yaw_local_vers_ue(yaw_deg: float) -> float:
    """Cap local (deg, trigo depuis +x) -> yaw UE (deg, horaire vu de dessus)."""
    return -yaw_deg


def yaw_ue_vers_local(yaw_ue: float) -> float:
    return -yaw_ue


def l93_vers_ue(e: float, n: float, h: float) -> tuple[float, float, float]:
    return local_vers_ue(*l93_vers_local(e, n, h))


# ---------------------------------------------------------------- orientations
def rpy_local_vers_ue(r: float, p: float, y: float) -> tuple[float, float, float]:
    """rpy local (deg) -> (roll, pitch, yaw) d'un unreal.Rotator : M.Rz(y).Ry(p).Rx(r).M."""
    return (float(r), -float(p), yaw_local_vers_ue(float(y)))


def quat_local_vers_ue(q) -> tuple[float, float, float, float]:
    """Quaternion local [x, y, z, w] -> composantes (x, y, z, w) d'un unreal.Quat (normalise)."""
    x, y, z, w = (float(v) for v in q)
    n = math.sqrt(x * x + y * y + z * z + w * w)
    if n < 1e-12:
        raise ValueError(f'quaternion nul : {q}')
    return (-x / n, y / n, -z / n, w / n)


def matrice_rpy(r: float, p: float, y: float) -> list[list[float]]:
    """Matrice 3x3 (lignes) de Rz(y).Ry(p).Rx(r), angles en degres ; colonnes = images des axes."""
    cr, sr = math.cos(math.radians(r)), math.sin(math.radians(r))
    cp, sp = math.cos(math.radians(p)), math.sin(math.radians(p))
    cy, sy = math.cos(math.radians(y)), math.sin(math.radians(y))
    return [[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr]]


def matrice_quat(q) -> list[list[float]]:
    """Matrice 3x3 (lignes) du quaternion [x, y, z, w] (normalise au passage)."""
    x, y, z, w = (float(v) for v in q)
    n = math.sqrt(x * x + y * y + z * z + w * w)
    x, y, z, w = x / n, y / n, z / n, w / n
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]]


def quat_depuis_rpy(r: float, p: float, y: float) -> tuple[float, float, float, float]:
    """rpy local (deg, ZYX intrinseques) -> quaternion local [x, y, z, w]."""
    hr, hp, hy = (math.radians(a) / 2.0 for a in (r, p, y))
    cr, sr, cp, sp, cy, sy = math.cos(hr), math.sin(hr), math.cos(hp), math.sin(hp), math.cos(hy), math.sin(hy)
    return (sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy)


def ecart_rotations_deg(a: list[list[float]], b: list[list[float]]) -> float:
    """Angle (deg) de la rotation d = a^T.b entre deux matrices 3x3 (atan2 : precis aux petits angles)."""
    d = [[sum(a[k][i] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    sin_ = 0.5 * math.sqrt((d[2][1] - d[1][2]) ** 2 + (d[0][2] - d[2][0]) ** 2 + (d[1][0] - d[0][1]) ** 2)
    return math.degrees(math.atan2(sin_, (d[0][0] + d[1][1] + d[2][2] - 1.0) / 2.0))


if __name__ == '__main__':
    # auto-test : aller-retour et cas connus
    assert local_vers_ue(1.0, 2.0, 3.0) == (100.0, -200.0, 300.0)
    p = (917300.0, 6460300.0, 217.30)
    q = local_vers_l93(*l93_vers_local(*p))
    assert all(abs(a - b) < 1e-6 for a, b in zip(p, q))
    assert all(abs(a - b) < 1e-9 for a, b in zip(ue_vers_local(*local_vers_ue(4.5, -7.25, 0.3)), (4.5, -7.25, 0.3)))
    assert yaw_local_vers_ue(30.0) == -30.0
    assert rpy_local_vers_ue(20.0, 10.0, 30.0) == (20.0, -10.0, -30.0)
    assert ecart_rotations_deg(matrice_rpy(20, 10, 30), matrice_quat(quat_depuis_rpy(20, 10, 30))) < 1e-6
    print('repere OK (rotations completes : tests/test_rotations.py)')
