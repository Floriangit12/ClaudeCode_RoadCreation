"""caler_pano2.py : lance le calage complet de recon/pcg/enrichir/poses.py (points d'appui datés, vote, RANSAC,
critères d'acceptation inchangés) sur les photos de VISION-PANORAMAX-2 non traitées par l'atelier des poses,
en redirigeant l'écriture vers pano_2/par_photo_pano2/ (enrichi/poses/ n'est pas modifié).

  python caler_pano2.py <n_proc> <id8> ...
  python caler_pano2.py --assembler          -> poses_pano2.json (poses acceptées par les critères de poses.py)
"""
import json
import sys
from multiprocessing import Pool
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import overlay_pnx  # noqa: E402,F401  (chemins)
import poses as PS  # noqa: E402
from camera import arrondi, ecrire_json  # noqa: E402

PAR = ICI / "par_photo_pano2"


def _ecrire(rec):
    PAR.mkdir(parents=True, exist_ok=True)
    ecrire_json(PAR / f"{rec['id8']}.json", arrondi(rec, 4))


def un(pid):
    PS._ecrire = _ecrire
    try:
        rec = PS.caler(pid, verbeux=False, sequence=True)
        return pid, rec.get("accepte"), rec.get("raison"), (rec.get("qualite") or {}).get("n_gcp")
    except Exception as e:  # noqa: BLE001
        return pid, None, f"erreur {e!r}", None


def assembler():
    out = json.loads((ICI / "poses_pano2.json").read_text(encoding="utf-8")) if (ICI / "poses_pano2.json").exists() else {"photos": {}}
    for f in sorted(PAR.glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        if not r.get("pose"):
            continue
        q = r.get("qualite") or {}
        out["photos"][r["id8"]] = dict(id8=r["id8"], date=r["date"], methode="poses.py (GCP datés) relancé par VISION-PANORAMAX-2",
                                       accepte_criteres_poses=r.get("accepte"), raison=r.get("raison"), pose=r["pose"],
                                       intrinseques=r.get("intrinseques"), n_gcp=q.get("n_gcp"), residu_moy_deg=q.get("residu_moy_deg"),
                                       residu_moy_px=q.get("residu_moy_px"), decalage_gps_m=q.get("decalage_gps_m"),
                                       qualite="acceptee" if r.get("accepte") else "refusee_criteres")
    out["description"] = "poses VISION-PANORAMAX-2 : calage poses.py relancé (par_photo_pano2/) ; ne remplace pas enrichi/poses/poses.json"
    (ICI / "poses_pano2.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(out["photos"]), "poses")


if __name__ == "__main__":
    if sys.argv[1] == "--assembler":
        assembler()
    else:
        n = int(sys.argv[1])
        ids = sys.argv[2:]
        with Pool(n) as p:
            for r in p.imap_unordered(un, ids):
                print(r, flush=True)
