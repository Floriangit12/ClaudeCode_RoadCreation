"""Calage (toolkit enrichir/poses.py) des photos de la part VISION-PANORAMAX-1 non encore calées.
N'écrit PAS dans enrichi/poses/ : _ecrire est redirigé vers le dossier de travail pano_1/poses_pano1/.
Usage : python -I caler_pano1.py <id8> [--sequence]"""
import sys
from pathlib import Path

RACINE = Path("D:/ClaudeCode_RoadCreation")
sys.path.insert(0, str(RACINE / "recon/pcg/enrichir"))
sys.path.insert(0, str(RACINE / "recon/pcg"))
import os
os.chdir(RACINE / "recon/pcg/enrichir")
import poses as PO  # noqa: E402
from camera import arrondi, ecrire_json  # noqa: E402

OUT = Path(__file__).resolve().parent / "poses_pano1"
OUT.mkdir(exist_ok=True)


def _ecrire(rec):
    ecrire_json(OUT / f"{rec['id8']}.json", arrondi(rec, 4))


PO._ecrire = _ecrire

if __name__ == "__main__":
    seq = "--sequence" in sys.argv
    for pid in [a for a in sys.argv[1:] if not a.startswith("--")]:
        try:
            r = PO.caler(pid, verbeux=True, sequence=seq)
            print("FIN", pid, r.get("accepte"), r.get("raison"), flush=True)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            print("ERREUR", pid, e, flush=True)
