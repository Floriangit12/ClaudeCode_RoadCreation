"""Lanceur d'un module du pipeline pour un état cible : fixe PJ_ETAT (et PJ_DATE_CIBLE) AVANT les imports, fige la
configuration dans <dossier_sortie>/etat_cible.json, refuse les écritures croisées, puis exécute le module.

    python recon/pcg/etat/lancer.py --etat avant_travaux [--date AAAA-MM-JJ] [--nouvelle-date] [--hython]
                                    [--verifier-seulement] -- SCRIPT.py [arguments du script...]
    python recon/pcg/etat/lancer.py --etat avant_travaux --figer        (fige seulement la configuration)

Refus (code de sortie 3), avant toute exécution (PLAN § 3.5) :
- <dossier_sortie>/etat_cible.json appartient à un autre état (id différent) ;
- il est figé pour une autre date cible (sauf --nouvelle-date : les sorties existantes sont alors à refaire) ;
- un argument du script désigne un chemin d'un autre état ou d'une archive en lecture seule (v2/, package/), sauf
  une entrée partagée déclarée (entrees_partagees) passée à une option d'entrée.
Les modules refusent aussi l'écriture croisée à l'exécution (etat_cible.verifier_ecriture, appelé par
commun.ecrire_json / ecrire_geojson et par les contrôleurs).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import etat_cible as EC  # noqa: E402

HYTHON = Path("C:/Program Files/Side Effects Software/Houdini 22.0.459/bin/hython.exe")
OPTIONS_SORTIE = ("--sortie", "--out", "--png", "--cache", "--planche", "--rapport", "-o")
CODE_REFUS = 3


def chemins_arguments(args):
    """[(option, valeur)] des arguments qui ressemblent à des chemins (positionnels : option None)."""
    out, prec = [], None
    for a in args:
        opt, val = prec, a
        if a.startswith("-"):
            if "=" in a:
                opt, val = a.split("=", 1)
            else:
                prec = a
                continue
        prec = None
        if ("/" in val or "\\" in val or val.endswith((".json", ".geojson", ".png", ".jpg", ".usd", ".usdc"))) \
                and not val.startswith(("http:", "https:")):
            out.append((opt, val))
    return out


def verifier_arguments(E, args):
    """Liste des refus pour les chemins passés au script (vide si tout est permis)."""
    partagees = {str(Path(v).resolve()) for k, v in ((k, EC.RACINE / v) for k, v in E.config["entrees_partagees"].items()
                                                      if not k.startswith("_"))}
    refus = []
    for opt, val in chemins_arguments(args):
        p = Path(val)
        p = p if p.is_absolute() else (Path.cwd() / p)
        ou = EC.etat_du_chemin(p)
        if ou is None:
            continue
        sortie = opt in OPTIONS_SORTIE
        if ou[0] == "etat" and ou[1] == E.id:
            continue
        if ou[0] == "archive" and not sortie and any(str(p.resolve()).startswith(s) for s in partagees):
            continue                                     # entrée partagée déclarée, en lecture
        quoi = f"archive ({ou[1]})" if ou[0] == "archive" else f"dossier de l'état « {ou[1]} »"
        refus.append(f"{opt or 'argument'} {val} : {quoi}, état courant « {E.id} »"
                     + (" (option de sortie)" if sortie else ""))
    return refus


def principal(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" in argv:
        i = argv.index("--")
        propres, script = argv[:i], argv[i + 1:]
    else:
        propres, script = argv, []
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--etat", required=True, help="identifiant (recon/pcg/etat/etats/<id>.json)")
    ap.add_argument("--date", default=None, help="date cible (variante déclarée ; défaut : date_cible de l'état)")
    ap.add_argument("--nouvelle-date", action="store_true", help="autorise le changement de date cible du dossier")
    ap.add_argument("--figer", action="store_true", help="fige seulement la configuration (aucun script)")
    ap.add_argument("--verifier-seulement", action="store_true", help="contrôles sans écriture ni exécution")
    ap.add_argument("--hython", action="store_true", help="exécute le script avec hython (Houdini)")
    a = ap.parse_args(propres)
    try:
        E = EC.charger(a.etat, a.date)
    except EC.ErreurEtat as e:
        print(f"REFUS : {e}", file=sys.stderr)
        return CODE_REFUS
    action, msg = EC.figer(E, nouvelle_date=a.nouvelle_date, ecrire=not a.verifier_seulement)
    if action.startswith("refus"):
        print(f"REFUS : {msg}", file=sys.stderr)
        return CODE_REFUS
    print(f"état {E.id} (T = {E.date_cible}, sha256 {E.sha256[:12]}) : {msg}")
    refus = verifier_arguments(E, script[1:]) if script else []
    if refus:
        for r in refus:
            print(f"REFUS : {r}", file=sys.stderr)
        return CODE_REFUS
    if a.figer or a.verifier_seulement or not script:
        return 0
    env = dict(os.environ, PJ_ETAT=E.id, PYTHONDONTWRITEBYTECODE="1")
    if a.date:
        env["PJ_DATE_CIBLE"] = a.date
    else:
        env.pop("PJ_DATE_CIBLE", None)
    if a.hython:
        env["HOUDINI_VEX_DISABLE_JIT"] = "1"
    exe = str(HYTHON) if a.hython else sys.executable
    return subprocess.run([exe] + script, env=env).returncode


if __name__ == "__main__":
    sys.exit(principal())
