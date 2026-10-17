"""Sensibilité du créneau critique SUMO (S3, cédez, Krauss pas 0,1 s) aux paramètres de carrefour.

Teste impatience (0 par défaut ; 0,5 ; 1) et jmTimegapMinor (1 s par défaut ; 0 s) pour vérifier
l'explication du créneau critique très long observé (critère « unsafeMergeSpeeds » de MSLink :
avec impatience 0 l'inséré ne doit imposer AUCUN freinage au prioritaire).

Usage : python s3_sensibilite.py [--graines 3]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as C  # noqa: E402
import s3_insertion_cedez as S  # noqa: E402
import sumolib  # noqa: E402

VARIANTES_JM = {
    "defaut": "",
    "impatience_0.5": 'impatience="0.5"',
    "impatience_1": 'impatience="1"',
    "timegap_0": 'jmTimegapMinor="0"',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graines", type=int, default=3)
    a = ap.parse_args()
    S.construire("cedez")
    net = sumolib.net.readNet(str(S.DOSSIER / "s3_cedez.net.xml"))
    L_maj = net.getLane("WJ_0").getLength(); L_min = net.getLane("SJ_0").getLength()
    res = {}
    for nom, attrs in VARIANTES_JM.items():
        rou = S.DOSSIER / f"s3_sens_{nom}.rou.xml"
        C.ecrire(rou, f"""<routes>
  <vType id="vp" vClass="passenger" carFollowModel="Krauss" {attrs}/>
  <flow id="maj_OE" type="vp" begin="0" end="{S.DUREE:.0f}" period="exp({600/3600:.6f})" from="WJ" to="JE" departSpeed="max"/>
  <flow id="maj_EO" type="vp" begin="0" end="{S.DUREE:.0f}" period="exp({600/3600:.6f})" from="EJ" to="JW" departSpeed="max"/>
  <flow id="min_SE" type="vp" begin="0" end="{S.DUREE:.0f}" period="exp({180/3600:.6f})" from="SJ" to="JE" departSpeed="max"/>
</routes>
""")
        rows = []
        (C.RACINE_BRUT / S.DOSSIER.name).mkdir(parents=True, exist_ok=True)
        for g in range(a.graines):
            fcd = C.RACINE_BRUT / S.DOSSIER.name / f"fcd_sens_{nom}_g{g}.xml.gz"
            C.lancer_sumo(["-n", str(S.DOSSIER / "s3_cedez.net.xml"), "-r", str(rou), "--step-length", "0.1",
                           "--seed", str(g), "--no-step-log", "true", "--end", str(S.DUREE + 300),
                           "--fcd-output", str(fcd), "--fcd-output.attributes", "lane,pos,speed,acceleration",
                           "--fcd-output.filter-edges.input-file", str(S.DOSSIER / "s3_filtre_fcd.txt"),
                           "--collision.action", "warn", "--collision.check-junctions", "true"],
                          C.RACINE_BRUT / S.DOSSIER.name / f"log_sens_{nom}_g{g}.txt")
            rows += S.analyser(S.lire(fcd, 0.1), L_maj, L_min)
        arr = [r for r in rows if r["arret_complet"]]
        res[nom] = {
            "attributs_vType": attrs or "(défauts)", "n_conducteurs": len(rows),
            "arretes_creneau_critique_mle_lognormal": S.mle_lognormale([r["accepte"] for r in arr], [r["max_rejete"] for r in arr]),
            "arretes_creneau_accepte_s": C.percentiles([r["accepte"] for r in arr]),
            "attente_s": C.percentiles([r["attente"] for r in rows]),
            "accel_min_prioritaire_suivant_ms2": C.percentiles([r["accel_min_prioritaire_suivant"] for r in rows], ps=(1, 5, 50)),
        }
        print(nom, len(rows), res[nom]["arretes_creneau_critique_mle_lognormal"], res[nom]["accel_min_prioritaire_suivant_ms2"]["p5"])
    C.json_ecrire(S.DOSSIER / "resultats" / "S3_sensibilite_jm.json", {"scenario": __doc__.strip().splitlines()[0], "graines": a.graines, "resultats": res})


if __name__ == "__main__":
    main()
