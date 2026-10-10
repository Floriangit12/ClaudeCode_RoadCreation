"""Outils communs des essais de phase 0 (cote client, hors editeur).

Les scripts executes DANS l'editeur sont dans ./ue/ et passent par pj_tools.run_python_file.
Sorties (PNG, journaux, JSON) : recon/out/paquet_jardin/v2/ue_phase0/.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
UE_DIR = os.path.join(ICI, 'ue')
sys.path.insert(0, os.path.dirname(ICI))            # recon/pcg/ue -> mcp_client
sys.path.insert(0, os.path.join(os.path.dirname(ICI), 'pj_tools'))   # repere

from mcp_client import McpClient, McpErreur  # noqa: E402
from pj_tools import eclairage  # noqa: E402  (reference d'eclairage et d'exposition, Python pur)

DEPOT = os.path.abspath(os.path.join(ICI, '..', '..', '..', '..'))
OUT = os.path.join(DEPOT, 'recon', 'out', 'paquet_jardin', 'v2', 'ue_phase0').replace('\\', '/')
NIVEAU = '/Game/PJ/Maps/PJ_Phase0'
EV100 = eclairage.EV100   # exposition manuelle commune (14 : gris 18 % au soleil ~0,15 ; 12 surexposait de 1,5 a 2 EV)

os.makedirs(OUT, exist_ok=True)


def client() -> McpClient:
    c = McpClient()
    c.initialize()
    return c


def ue(c: McpClient, script: str, args: dict | None = None, timeout: float = 1800.0) -> dict:
    """Execute ue/<script> dans l'editeur ; renvoie le JSON de run_python_file (leve si ok=False)."""
    chemin = os.path.join(UE_DIR, script).replace('\\', '/')
    r = c.pj('run_python_file', {'path': chemin, 'args_json': json.dumps(args or {})}, timeout=timeout)
    if not isinstance(r, dict) or not r.get('ok'):
        msg = r if isinstance(r, str) else json.dumps(r, ensure_ascii=False, indent=1)
        raise McpErreur(f'{script} : {msg[-6000:]}')
    return r


def capture(c: McpClient, nom: str, cam, yaw, pitch, fov=70.0, w=1920, h=1080, ev100=EV100,
            warmup=32, dossier: str | None = None, max_s: float = 900.0) -> dict:
    """Capture PNG (tramee) + EXR via pj_tools.high_res_capture (asynchrone : sondage de
    high_res_capture_etat jusqu'a fini) ; cam en metres locaux."""
    png = f'{dossier or OUT}/{nom}.png'
    r = c.pj('high_res_capture', {'out_png': png, 'cam_x_m': cam[0], 'cam_y_m': cam[1], 'cam_z_m': cam[2],
                                  'yaw_deg': yaw, 'pitch_deg': pitch, 'fov_deg': fov,
                                  'width': w, 'height': h, 'warmup': warmup, 'ev100': ev100},
             timeout=900)
    t0 = time.time()
    while isinstance(r, dict) and r.get('ok') and r.get('en_cours') and time.time() - t0 < max_s:
        time.sleep(0.5)
        r = c.pj('high_res_capture_etat', {'out_png': png}, timeout=300)
    if not isinstance(r, dict) or not r.get('ok') or not r.get('fini'):
        raise McpErreur(f'capture {nom} : {r}')
    return r


VIEWPORT = 'EditorToolset.EditorAppToolset'
ANNOT_VIDE = {'gridSpacing': 0, 'gridExtent': 0, 'gridHeight': 0, 'maxLabelDistance': 0,
              'classFilter': {'refPath': '/Script/Engine.StaticMeshActor'}, 'maxLabels': 0}


def capture_viewport(c: McpClient, nom: str, cam, yaw, pitch, dossier: str | None = None, rendus: int = 3) -> dict:
    """PNG du viewport de l'editeur (EditorAppToolset.CaptureViewport) a une pose locale ; 'rendus' appels
    successifs (le premier deplace la camera, Lumen converge), camera du viewport restauree ensuite.
    Renvoie {png, fov, largeur, hauteur}."""
    import base64
    X, Y, Z = cam[0] * 100.0, -cam[1] * 100.0, cam[2] * 100.0
    pose = {'location': {'x': X, 'y': Y, 'z': Z}, 'rotation': {'pitch': pitch, 'yaw': -yaw, 'roll': 0},
            'scale': {'x': 1, 'y': 1, 'z': 1}}
    cam0 = c.call_tool(VIEWPORT, 'GetCameraTransform', {})
    try:
        for _ in range(max(1, rendus)):
            r = c.call_tool(VIEWPORT, 'CaptureViewport', {'captureTransform': pose, 'annotations': ANNOT_VIDE,
                                                          'bShowUI': False}, timeout=300)
            time.sleep(0.5)
    finally:
        c.call_tool(VIEWPORT, 'SetCameraTransform', {'transform': cam0.get('returnValue', cam0)})
    rv = r.get('returnValue', r)
    png = f'{dossier or OUT}/{nom}.png'
    with open(png, 'wb') as f:
        f.write(base64.b64decode(rv['image']['data']))
    from PIL import Image
    w, h = Image.open(png).size
    return {'png': png, 'fov': rv['cameraFOV'], 'largeur': w, 'hauteur': h,
            'camera_ue': [rv['cameraLocation'], rv['cameraRotation']]}


def projeter(points, cam, yaw, pitch, fov, w, h):
    """Points locaux (m) -> pixels (u, v) d'une camera locale (cap yaw, site pitch, champ horizontal fov)."""
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    av = (cp * cy, cp * sy, sp)                       # repere local direct : avant, droite, haut
    dr = (sy, -cy, 0.0)
    ht = (-sp * cy, -sp * sy, cp)
    foc = (w / 2.0) / math.tan(math.radians(fov) / 2.0)
    out = []
    for p in points:
        v = [p[i] - cam[i] for i in range(3)]
        x = sum(a * b for a, b in zip(v, av))
        out.append((w / 2.0 + foc * sum(a * b for a, b in zip(v, dr)) / x,
                    h / 2.0 - foc * sum(a * b for a, b in zip(v, ht)) / x))
    return out


def lire_exr(chemin: str):
    """EXR scanline (NONE/ZIPS/ZIP, HALF/FLOAT) -> dict canal -> tableau numpy float32 (h, w)."""
    import struct
    import zlib
    import numpy as np
    b = open(chemin, 'rb').read()
    assert struct.unpack('<I', b[:4])[0] == 20000630, 'pas un EXR'
    i, att = 8, {}
    while b[i] != 0:
        j = b.index(0, i); nom = b[i:j].decode(); i = j + 1
        j = b.index(0, i); i = j + 1
        n = struct.unpack('<I', b[i:i + 4])[0]; i += 4
        att[nom] = b[i:i + n]; i += n
    i += 1
    chs, k, v = [], 0, att['channels']
    while v[k] != 0:
        j = v.index(0, k); chs.append((v[k:j].decode(), struct.unpack('<i', v[j + 1:j + 5])[0])); k = j + 17
    x0, y0, x1, y1 = struct.unpack('<4i', att['dataWindow'])
    w, h, comp = x1 - x0 + 1, y1 - y0 + 1, att['compression'][0]
    lignes = {0: 1, 2: 1, 3: 16}[comp]
    nblocs = (h + lignes - 1) // lignes
    offs = struct.unpack(f'<{nblocs}Q', b[i:i + 8 * nblocs])
    taille = {1: 2, 2: 4}
    out = {n: np.zeros((h, w), np.float32) for n, _ in chs}
    for o in offs:
        y, n = struct.unpack('<iI', b[o:o + 8])
        d = b[o + 8:o + 8 + n]
        nl = min(lignes, y1 - y + 1)
        brut = sum(taille[t] for _, t in chs) * w * nl
        if comp and n < brut:
            t = np.frombuffer(zlib.decompress(d), np.uint8).astype(np.int32)
            t = (np.cumsum(t - 128 + np.r_[128, np.zeros(len(t) - 1, np.int32)]) & 255).astype(np.uint8)
            m = (len(t) + 1) // 2
            d = np.empty(len(t), np.uint8); d[0::2] = t[:m]; d[1::2] = t[m:]
            d = d.tobytes()
        k = 0
        for r in range(nl):
            for nom, t in chs:
                nb = taille[t] * w
                out[nom][y - y0 + r] = np.frombuffer(d[k:k + nb], np.float16 if t == 1 else np.float32)
                k += nb
    return out


def ecrire_json(nom: str, obj) -> str:
    p = f'{OUT}/{nom}'
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=str)
    return p


def horodatage() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%S')
