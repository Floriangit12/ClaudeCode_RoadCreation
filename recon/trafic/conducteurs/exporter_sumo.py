"""Exporte une population de conducteurs tirée par le prototype vers une vTypeDistribution SUMO.

Chaque conducteur tiré devient un vType (probabilité égale) avec :
  speedFactor   = v_désirée(réseau) / VMA       (facteur du réseau choisi, ex. artere_centre_ville_50)
  accel         = acc.demarrage_pic             (Salles 2020)
  decel         = dec.max_courante_urbain       (Huang 2018)
  emergencyDecel= |dec.urgence_max_markkula|    (Markkula 2016), borné ≥ decel
  tau           = tiv.moyen_conducteur_urbain   (Huang 2018) - interprétation « TIV désiré »
  minGap        = tiv.ecart_arret               (plage de calage, faible confiance)
  actionStepLength = tpr.anticipe arrondi au pas de simulation (option --reaction)
Le modèle de poursuite est laissé au choix (Krauss par défaut, EIDM conseillé) : voir CONDUCTEURS.md.

Usage : python exporter_sumo.py --n 200 --reseau artere_centre_ville_50 --sortie vtypes.add.xml [--graine 1] [--profil presse]
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from xml.sax.saxutils import quoteattr

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modele_conducteurs as mc  # noqa: E402

VMA = {"artere_centre_ville_50": 50, "traversee_petite_agglo_50": 50, "entree_sortie_agglo_50": 50,
       "route_2_3_voies_80": 80, "route_2x2_110": 110, "autoroute_degagement_110": 110,
       "autoroute_liaison_130": 130, "zone_30_be": 30}


def tirer_style_profil(prof, profil, n, rng):
    """Facteur style tiré dans la tranche du profil (normale tronquée)."""
    from scipy import stats
    p = next(x for x in prof["profils"] if x["id"] == profil)
    a, b = p["facteur_style"].get("intervalle", [None, None])
    a = -np.inf if a is None else a
    b = np.inf if b is None else b
    return stats.truncnorm.rvs(a, b, size=n, random_state=rng)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--reseau", default="artere_centre_ville_50", choices=sorted(VMA))
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--graine", type=int, default=1)
    ap.add_argument("--profil", default=None, help="prudent | moyen | presse | agressif (tranche de style)")
    ap.add_argument("--pas", type=float, default=0.1, help="pas de simulation SUMO (s)")
    ap.add_argument("--reaction", action="store_true", help="actionStepLength = TPR anticipé")
    ap.add_argument("--modele", default="Krauss", help="carFollowModel SUMO")
    ap.add_argument("--sigma", default=None, help="imperfection Krauss (défaut SUMO 0,5 : abaisse la vitesse libre)")
    a = ap.parse_args()
    params, prof = mc.charger()
    rng = np.random.default_rng(a.graine)
    S = tirer_style_profil(prof, a.profil, a.n, rng) if a.profil else None
    val, _ = mc.tirer_population(params, a.n, rng, S=S)
    vma = VMA[a.reseau]
    v = val[f"vit.{a.reseau}"]
    lignes = [f'<additional>\n  <!-- {a.n} conducteurs tirés (graine {a.graine}, réseau {a.reseau}, profil {a.profil or "population"}) '
              f'par recon/trafic/conducteurs/exporter_sumo.py -->',
              f'  <vTypeDistribution id={quoteattr("conducteurs_" + a.reseau)}>']
    for i in range(a.n):
        dec = float(val["dec.max_courante_urbain"][i])
        emerg = max(dec, abs(float(val["dec.urgence_max_markkula"][i])))
        attrs = {
            "id": f"cond_{i:04d}", "vClass": "passenger", "carFollowModel": a.modele, "probability": "1",
            "speedFactor": f"{max(0.2, float(v[i]) / vma):.4f}", "speedDev": "0",
            "accel": f"{float(val['acc.demarrage_pic'][i]):.3f}", "decel": f"{dec:.3f}",
            "emergencyDecel": f"{emerg:.3f}", "tau": f"{float(val['tiv.moyen_conducteur_urbain'][i]):.3f}",
            "minGap": f"{float(val['tiv.ecart_arret'][i]):.3f}",
        }
        if a.sigma is not None:
            attrs["sigma"] = str(a.sigma)
        if a.reaction:
            tpr = float(val["tpr.anticipe"][i])
            attrs["actionStepLength"] = f"{max(a.pas, round(tpr / a.pas) * a.pas):.2f}"
        lignes.append("    <vType " + " ".join(f'{k}="{w}"' for k, w in attrs.items()) + "/>")
    lignes += ["  </vTypeDistribution>", "</additional>", ""]
    os.makedirs(os.path.dirname(os.path.abspath(a.sortie)), exist_ok=True)
    with open(a.sortie, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes))
    print(f"{a.n} vTypes -> {a.sortie} ; speedFactor moyen {np.mean(v) / vma:.3f}, écart-type {np.std(v) / vma:.3f}")


if __name__ == "__main__":
    main()
