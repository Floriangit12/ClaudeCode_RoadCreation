import sys, json, math
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg/enrichir")
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg")
import numpy as np
from camera import camera_calee
from projection import decoupe_perspective
OUT = "D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2_avant_travaux/inventaire/qualite/photos_non_versionnees/"
VUES = [("119d9094", 0.0, "sw"), ("119d9094", 180.0, "ne"), ("2ab4efbc", 0.0, "sw"), ("9834f494", 0.0, "sw"), ("aa9d7e12", 0.0, "sw")]
FOV, W, H, TANG = 90.0, 960, 640, -8.0
cams = {}
for pid, dl, nom in VUES:
    cam, st = camera_calee(pid)
    lac = (cam.pose[3] + dl) % 360.0
    im, cv = decoupe_perspective(pid, lac, TANG, FOV, (W, H), cam=cam)
    f = f"{pid}_{nom}.jpg"
    im.save(OUT + f, quality=90)
    cams[f"{pid}_{nom}"] = {"photo": pid, "statut_pose": st, "C": [float(v) for v in cv.C], "R": cv.R.tolist(), "f_px": cv.f, "W": W, "H": H,
                            "lacet_grille": lac, "tangage": TANG, "hfov": FOV}
    print(pid, nom, st, [round(v, 2) for v in cv.C], round(lac, 1))
json.dump(cams, open(OUT + "cameras_vignettes.json", "w"), indent=1)
