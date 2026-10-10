"""note.py : saisie des observations (agent VISION-PANORAMAX-2) -> notes/<photo>.json ; assemblage -> obs_pano_2.json."""
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
NOTES = ICI / "notes"
O = (917279.43, 6460289.98, 216.30)
SORTIE = ICI.parent / "obs_pano_2.json"


def pos(local=None, l93=None, precision_m=0.5, methode="projection_description"):
    p = dict(precision_m=precision_m, methode=methode)
    if local is not None:
        p["local"] = [round(float(v), 3) for v in local]
        p["l93"] = [round(float(local[0]) + O[0], 3), round(float(local[1]) + O[1], 3)]
    if l93 is not None:
        p["l93"] = [round(float(v), 3) for v in l93]
    return p


def ecrire(photo, obs):
    """Remplace les observations de la photo (liste de dicts sans id)."""
    NOTES.mkdir(exist_ok=True)
    (NOTES / f"{photo}.json").write_text(json.dumps(obs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(photo, len(obs), "observations")


def _copier_preuve(o):
    import shutil
    pr = o.get("preuve") or {}
    f = pr.get("fichier")
    if not f:
        return
    base = "recon/out/paquet_jardin/v2/enrichi/recensement/pano_2/"
    rel = f.replace(base, "")
    src = ICI / rel
    if src.exists() and rel.startswith("crops/"):
        dst = ICI / "preuves" / src.name
        dst.parent.mkdir(exist_ok=True)
        shutil.copy2(src, dst)
        pr["fichier"] = base + "preuves/" + src.name
        pj = src.with_name(src.stem.replace("_obj", "").replace("_sol", "").replace("_tout", "").replace("_ov", "") + "_proj.json")
        if pj.exists():
            shutil.copy2(pj, ICI / "preuves" / pj.name)
            pr["projection"] = base + "preuves/" + pj.name


def assembler():
    tout = []
    for f in sorted(NOTES.glob("*.json")):
        tout += json.loads(f.read_text(encoding="utf-8"))
    for o in tout:
        _copier_preuve(o)
    for k, o in enumerate(tout, 1):
        o_ = {"id": f"VISION-PANORAMAX-2-{k}"}
        o_.update(o)
        tout[k - 1] = o_
    SORTIE.write_text(json.dumps(tout, ensure_ascii=False, indent=1), encoding="utf-8")
    print(SORTIE, len(tout))
    return tout


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "assembler":
    assembler()


_INST = None


def inst(i):
    """Position locale (x, y, z) d'une instance du paquet (instances.json)."""
    global _INST
    if _INST is None:
        p = ICI.parents[3] / "package/donnees/objets/instances.json"
        _INST = {x["id"]: x for x in json.loads(p.read_text(encoding="utf-8"))["instances"]}
    x = _INST[i]
    return [x["x"], x["y"], x["z"]]


def P(i, prec=0.3):
    return pos(local=inst(i), precision_m=prec, methode="projection_description")


def V(val, raison):
    return {"valeur": val, "raison": raison}


def preuve(fichier, pixels=None, bbox=None):
    d = {"fichier": "recon/out/paquet_jardin/v2/enrichi/recensement/pano_2/" + fichier}
    if pixels is not None:
        d["pixels"] = pixels
    if bbox is not None:
        d["bbox"] = bbox
    return d
