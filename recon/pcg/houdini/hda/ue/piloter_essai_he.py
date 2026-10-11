"""Pilote (Python système) de l'essai Houdini Engine de pj::bordure dans l'éditeur UE 5.8 (MCP 127.0.0.1:8000).

    python recon/pcg/houdini/hda/ue/piloter_essai_he.py [--sans-pcg] [--garder-niveau]

1. importe fabrique_hda/hda/pj_bordure.hdalc (bibliothèque à une seule définition) dans /Game/PJ/Houdini ;
2. ouvre (ou crée depuis Template_Default) le niveau d'essai /Game/PJ/Maps/PJ_Test_HDA (jamais PJ_2026) ;
3. instancie pj::bordure (Houdini Public API) avec une courbe Houdini de 12 m (pente 1 %) et un abaissé de traversée
   (partie abaissée s = 5-7 m, GA-ABA-001 ; rampants de la règle GA-ABA-004), joints 6 mm, sorties 2-3 vides ;
4. attend la cuisson, compte éléments et joints (instances), capture deux vues (pj_tools.high_res_capture) ;
5. joint_mm 6 -> 10 par la Public API, recuisson, recompte, captures ;
6. (sauf --sans-pcg) graphe PCG : spline UE -> nœud « Houdini Digital Asset » (pj::bordure), génération, captures ;
7. enregistre le niveau d'essai, recharge le niveau d'origine ; rapport controle/essai_houdini_engine_ue.json.
Le script UE est essai_he_bordure.py (même dossier), exécuté par pj_tools.run_python_file.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[4]
sys.path.insert(0, str(RACINE / "recon/pcg/ue"))
from mcp_client import McpClient  # noqa: E402

SORTIE = RACINE / "recon/out/paquet_jardin/v2/fabrique_hda"
HDA = SORTIE / "hda" / "pj_bordure.hdalc"
SCRIPT = (ICI / "essai_he_bordure.py").as_posix()
NIVEAU = "/Game/PJ/Maps/PJ_Test_HDA"
ASSET = "/Game/PJ/Houdini/pj_bordure"
GRAPHE = "/Game/PJ/Houdini/PCG_Bordure_HDA"
LABEL = "PJ_Essai_Bordure_HE"
LABEL_PCG = "PJ_Essai_Bordure_PCG"
# courbe : x local de −6 à +6 m (UE X), y = 0, pente 1 % ; trottoir à gauche = +y local = −Y UE (README_HDA.md § 2)
POINTS_CM = [[x * 100.0, 0.0, round(x + 6.0, 3)] for x in (-6.0, -3.0, 0.0, 3.0, 6.0)]
POINTS_PCG_CM = [[p[0], p[1] - 400.0, p[2]] for p in POINTS_CM]       # spline PCG 4 m plus loin (y local = +4)
PARAMETRES = {"ue_id": "K-UE-ESSAI", "ue_abaisse": True, "ue_abaisse_debut": 5.0, "ue_abaisse_fin": 7.0,
              "sorties_unreal": True, "joints_aleatoires": False, "joint_mm": 6.0, "sortie": 1, "jitter": True}
# vues (repère local, m) : ensemble face vue (côté chaussée, y < 0) et gros plan des joints au rampant
VUES = {"ensemble": (0.0, -7.0, 1.7, 90.0, -11.0, 70.0), "joints": (-2.2, -1.25, 0.55, 62.0, -16.0, 45.0),
        "macro_joint": (-5.0, -0.32, 0.10, 90.0, -6.0, 22.0)}       # premier joint (s ≈ 1,0 m), face vue
VUES_PCG = {"pcg": (0.0, -7.0, 2.6, 90.0, -14.0, 80.0)}


def appeler(c, etape, **kw):
    r = c.pj("run_python_file", {"path": SCRIPT, "args_json": json.dumps(dict(kw, etape=etape))})
    if not r.get("ok"):
        raise RuntimeError(f"{etape} : {r.get('erreur')}\n{r.get('stdout', '')[-2000:]}\n{r.get('trace', '')[-2000:]}")
    return r.get("resultat")


def attendre(c, etape, test, max_s=600, pas=3.0):
    t0 = time.time()
    while time.time() - t0 < max_s:
        e = appeler(c, etape)
        if test(e):
            return e, round(time.time() - t0, 1)
        time.sleep(pas)
    raise TimeoutError(f"{etape} : délai dépassé ({max_s} s) ; dernier état {json.dumps(e)[:1500]}")


def capturer(c, nom, vue, w=1600, h=900):
    png = (SORTIE / "controle" / f"he_{nom}.png").as_posix()
    x, y, z, yaw, pitch, fov = vue
    r = c.pj("high_res_capture", {"out_png": png, "cam_x_m": x, "cam_y_m": y, "cam_z_m": z, "yaw_deg": yaw,
                                  "pitch_deg": pitch, "fov_deg": fov, "width": w, "height": h, "warmup": 48,
                                  "exr": False})
    if not r.get("ok"):
        raise RuntimeError(f"capture {nom} : {r}")
    t0 = time.time()
    while time.time() - t0 < 300:
        e = c.pj("high_res_capture_etat", {"out_png": png})
        if e.get("fini"):
            return {"png": Path(png).relative_to(RACINE).as_posix(), "ev100": e.get("ev100"),
                    "moyenne": e.get("moyenne")}
        if not e.get("ok", True):
            raise RuntimeError(f"capture {nom} : {e}")
        time.sleep(2.0)
    raise TimeoutError(f"capture {nom}")


def journal_ue(motifs, depuis):
    """Lignes du journal de l'éditeur (après FlushLog) contenant un des motifs, écrites après l'octet « depuis »."""
    f = Path("D:/ClaudeADAS/Saved/Logs/ClaudeADAS.log")
    try:
        with open(f, "rb") as h:
            h.seek(depuis)
            txt = h.read().decode("utf-8", "replace")
    except OSError:
        return []
    return [x.split("]", 2)[-1].strip()[:300] for x in txt.splitlines() if any(m in x for m in motifs)][-20:]


def essai_pcg(c):
    """Graphe PCG « spline -> Houdini Digital Asset (pj::bordure) » créé et câblé par Python, puis généré."""
    out = {}
    try:
        depuis = Path("D:/ClaudeADAS/Saved/Logs/ClaudeADAS.log").stat().st_size
        out["creation"] = appeler(c, "pcg", asset=ASSET, graphe=GRAPHE, label=LABEL_PCG, points_cm=POINTS_PCG_CM,
                                  parametres=PARAMETRES)
        out["cablage"], _ = attendre(c, "pcg_cabler", lambda e: (e or {}).get("pret"), max_s=120, pas=2.0)
        t0, e = time.time(), {}
        while time.time() - t0 < 45:
            time.sleep(3.0)
            e = appeler(c, "pcg_etat")
            if any(x.get("mesh") not in (None, "houdini_logo") for x in e.get("composants", [])):
                break
        out["etat"] = e
        c.pj("run_python_file", {"path": str(ICI / "vider_journal.py")})
        out["journal"] = journal_ue(("HoudiniPCGActor", "LogPCG"), depuis)
        out["sorties_pcg"] = any(x.get("mesh") not in (None, "houdini_logo") for x in e.get("composants", []))
        if out["sorties_pcg"]:
            out["captures"] = {n: capturer(c, f"bordure_{n}", v) for n, v in VUES_PCG.items()}
    except Exception as ex:  # noqa: BLE001
        out["erreur"] = str(ex)[:3000]
    return out


def niveau_courant(c):
    r = c.pj("run_python_file", {"path": str(ICI / "niveau_courant.py")})
    return (r.get("resultat") or {}).get("niveau")


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-pcg", action="store_true")
    ap.add_argument("--garder-niveau", action="store_true", help="rester dans le niveau d'essai à la fin")
    a = ap.parse_args()
    rapport = {"schema": "pj_essai_houdini_engine/0.1", "hda": HDA.relative_to(RACINE).as_posix(), "niveau": NIVEAU,
               "asset": ASSET, "courbe_cm": POINTS_CM, "parametres": PARAMETRES}
    with McpClient() as c:
        origine = niveau_courant(c)
        rapport["niveau_origine"] = origine
        rapport["import"] = appeler(c, "importer", hda=HDA.as_posix(), dossier="/Game/PJ/Houdini")
        existe = c.pj("list_assets", {"path": "/Game/PJ/Maps", "recursive": False})
        if any(x[0].startswith(NIVEAU + ".") for x in existe.get("assets", [])):
            rapport["ouverture_niveau"] = c.pj("load_level", {"path": NIVEAU})
        else:
            rapport["ouverture_niveau"] = c.pj("new_level", {"path": NIVEAU,
                                                             "template": "/Engine/Maps/Templates/Template_Default"})
        appeler(c, "nettoyer", labels=[LABEL, LABEL_PCG])
        rapport["session"] = appeler(c, "session")       # session neuve après le réimport (valeurs de paramètres sûres)
        rapport["instanciation"] = appeler(c, "instancier", asset=ASSET, label=LABEL, points_cm=POINTS_CM,
                                           parametres=PARAMETRES)
        e, dt = attendre(c, "etat", lambda e: (e or {}).get("traitements", 0) >= 1)
        rapport["joint_6mm"] = dict(e, duree_s=dt)
        rapport["parametres_lus"] = appeler(c, "parametres_lus")
        rapport["joint_6mm"]["captures"] = {n: capturer(c, f"bordure_joint6_{n}", v) for n, v in VUES.items()}
        avant = e["traitements"]
        rapport["changement"] = appeler(c, "parametre", nom="joint_mm", valeur=10.0)
        e, dt = attendre(c, "etat", lambda e: (e or {}).get("traitements", 0) > avant)
        rapport["joint_10mm"] = dict(e, duree_s=dt)
        rapport["joint_10mm"]["captures"] = {n: capturer(c, f"bordure_joint10_{n}", v) for n, v in VUES.items()}
        if not a.sans_pcg:
            rapport["pcg"] = essai_pcg(c)
        rapport["enregistrement"] = c.pj("save_all", {})
        if origine and not a.garder_niveau and not origine.startswith(NIVEAU):
            rapport["retour_niveau"] = c.pj("load_level", {"path": origine.split(".")[0]})
    f = SORTIE / "controle" / "essai_houdini_engine_ue.json"
    f.write_text(json.dumps(rapport, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps({k: rapport.get(k) for k in ("import", "instanciation", "changement", "pcg")},
                     ensure_ascii=False, indent=1)[:3000])
    for k in ("joint_6mm", "joint_10mm"):
        if k in rapport:
            print(k, json.dumps(rapport[k].get("bilan"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
