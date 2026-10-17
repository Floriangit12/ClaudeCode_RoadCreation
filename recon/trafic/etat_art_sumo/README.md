# recon/trafic/etat_art_sumo — démonstrateurs SUMO (volet 03, état de l'art)

Scripts qui font tourner SUMO 1.27.1 sur 3 situations simples pour montrer, chiffres à l'appui, ce que
font les modèles de poursuite **Krauss** (défaut SUMO) et **EIDM** avec leurs paramètres par défaut,
et où ils s'écartent du réel. Analyse complète : `D:\DocRoute\17_Modele_Vehicules_Conducteurs\03_Modeles_Existants\MODELES_EXISTANTS.md` (§ 11).

| Script | Scénario | Sorties (`…\03_Modeles_Existants\scenarios_sumo\`) |
|---|---|---|
| `s1_file_route_droite.py` | file de 10 véhicules à 50 km/h, meneur piloté par TraCI (profil imposé) | `S1_file_route_droite/` (réseau, routes, `resultats/S1_*.png`, `S1_resume.json`) |
| `s2_arret_feu.py` | feu isolé, cycle 60 s (vert 30 / jaune 3 / rouge 27), Poisson 720 véh/h | `S2_arret_feu/` |
| `s3_insertion_cedez.py` | T, tourne-à-droite depuis une voie secondaire (cédez et STOP), 600 véh/h/sens prioritaires | `S3_insertion_cedez/` (+ CSV par conducteur) |
| `s3_sensibilite.py` | S3 cédez, sensibilité à `impatience` et `jmTimegapMinor` | `S3_insertion_cedez/resultats/S3_sensibilite_jm.json` |
| `s3_reanalyse_creneaux.py` | S3 : créneau critique recalculé sur les sorties existantes, décalage compté depuis l'arrêt en tête de ligne, à l'entrée et au point de conflit (relecture du 17/10/2026) | `S3_insertion_cedez/resultats/S3_reanalyse_creneaux.json` |
| `parametres_reference.py` | forme machine de tous les paramètres cités (défauts logiciels, calages, normes, mesures en simulation) | `assets/specs/trafic/modeles_existants_reference.json` et copie dans `03_Modeles_Existants/` |
| `commun.py` | configurations comparées, valeurs de référence sourcées (`REFERENCES`), lecture FCD, utilitaires | — |

Configurations comparées (`commun.CONFIGS`) : Krauss pas 1 s (défaut SUMO), Krauss pas 0,1 s, EIDM pas 0,1 s.

## Lancer

```powershell
$env:PYTHONPATH = "D:\DocRoute\17_Modele_Vehicules_Conducteurs\tmp\03\pylib"   # matplotlib installé hors C:
python recon\trafic\etat_art_sumo\s1_file_route_droite.py --graines 5
python recon\trafic\etat_art_sumo\s2_arret_feu.py --graines 8
python recon\trafic\etat_art_sumo\s3_insertion_cedez.py --graines 6      # --reutiliser : relit les FCD existants
python recon\trafic\etat_art_sumo\s3_sensibilite.py --graines 3
python recon\trafic\etat_art_sumo\parametres_reference.py
```

Prérequis : `sumo`/`netconvert` dans le PATH, `SUMO_HOME` (défaut `C:\Program Files (x86)\Eclipse\Sumo`), numpy, scipy, matplotlib.
Les sorties brutes (FCD `.xml.gz`, journaux) vont dans `D:\DocRoute\17_Modele_Vehicules_Conducteurs\tmp\03\sumo_brut\` (régénérables, ~180 Mo).

## Conventions de mesure

- Temps : SUMO écrit au pas étiqueté *t* l'état **après** le mouvement du pas [*t*, *t*+Δ] (vérifié sur les sorties : le premier
  véhicule d'une file franchit la ligne dans le pas étiqueté au début du vert). Les scripts S2/S3 recalent donc *t*_phys = *t* + Δ.
- Franchissement d'une ligne : interpolation linéaire entre deux échantillons (extrapolation à vitesse constante si le véhicule
  quitte les voies filtrées).
- Créneau critique : maximum de vraisemblance (Troutbeck) avec loi log-normale sur (plus grand créneau refusé, créneau accepté)
  des conducteurs arrêtés à la ligne.
