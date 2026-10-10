"""a_priori_pano2.py : pose a priori des 360° non calées (a priori de séquence de poses.py, sinon GNSS brut + hauteur de séquence)
-> poses_pano2.json (qualite 'a_verifier' tant que la revue visuelle des bandes n'est pas faite)."""
import json, sys
from pathlib import Path
ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import overlay_pnx  # noqa
import poses as PS
from camera import photo, pose_brute, z_sol, intrinseques

def un(pid):
    ph = photo(pid)
    pb = pose_brute(ph); p = pb["pose"].copy()
    seq = PS.a_priori_sequence(ph, p)
    if seq is not None:
        q = seq["pose"]; m = "a_priori_sequence"; sig = seq["sigma"]
    else:
        q = p.copy(); q[2] = z_sol(q[0], q[1]) + ph.seq["h"]; m = "gnss_brut"; sig = pb["sigma"]
    return dict(id8=ph.id8, date=ph.date, methode=m, voisins=seq["voisins"] if seq else [], sigma=sig,
                pose=dict(x=round(float(q[0]),3), y=round(float(q[1]),3), z=round(float(q[2]),3), lacet=round(float(q[3]),3),
                          tangage=round(float(q[4]),3), roulis=round(float(q[5]),3)), qualite="a_verifier")

if __name__ == "__main__":
    S = ICI / "poses_pano2.json"
    d = json.loads(S.read_text(encoding="utf-8")) if S.exists() else {"photos": {}}
    for pid in sys.argv[1:]:
        r = un(pid)
        if pid in d["photos"] and d["photos"][pid].get("qualite") not in (None, "a_verifier"):
            continue
        d["photos"][pid] = r
        print(pid, r["methode"], r["pose"])
    d["description"] = "poses VISION-PANORAMAX-2 (a priori de séquence / GNSS, corrections manuelles après revue des bandes azimut-élévation) ; ne remplace pas enrichi/poses/poses.json"
    S.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
