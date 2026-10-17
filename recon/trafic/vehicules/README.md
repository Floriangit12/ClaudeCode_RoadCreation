# recon/trafic/vehicules — modèle de véhicules (prototype v0.1, 17/10/2026)

Volet « véhicules » du modèle de trafic (capacités physiques des véhicules ; le comportement des conducteurs
est traité ailleurs). Documentation et sources : `D:\DocRoute\17_Modele_Vehicules_Conducteurs\01_Vehicules\`
(`VEHICULES.md`, `sources/SOURCES.md`). Paramètres : `assets/specs/trafic/vehicules_parametres.json`
(copie de `D:\DocRoute\…\01_Vehicules\vehicules_parametres.json`, reconstruite par `construire_parametres.py`).

| Fichier | Rôle |
|---|---|
| `dynamique.py` | modèle longitudinal : `Vehicule.acceleration_max(v, pente)`, `temps_acceleration`, `distance_freinage` ; bornes ONU R13-H / R13 ; calage de k et a_lancement |
| `valider_vehicules.py` | calage sur 10 essais ADAC + validation croisée « un exclu » → `…/01_Vehicules/donnees/validation_dynamique.json` |
| `construire_parametres.py` | assemble `vehicules_parametres.json` depuis les données dérivées (SDES, AEE, ADAC, Greibe, règlements) |
| `population.py` | tire une population de voitures (classes VP) : loi conjointe masse / P/m / famille (combinaisons AEE 2024), parc en circulation (défaut, familles ramenées au parc SDES, d_max Greibe) ou véhicules neufs (`--parc neuf`) ; résume ses performances |
| `test_dynamique.py`, `test_parametres.py` | tests unitaires du modèle et contrôle de forme du JSON |
| `outils/` | extraction des sources (lancer avec `python -I`, ou `python -E -P` si openpyxl est requis) : `eea_sql.py` (requêtes Discodata AEE), `hdv_filtre_fr.py` (CSV poids lourds AEE lu en flux, lignes FR), `hdv_stats.py`, `sdes_vers_json.py` (xlsx SDES → JSON), `pdf_texte.py`, `pdf_page_png.py`, `adac_extraire.py` |

Ordre de reconstruction :

```
python recon/trafic/vehicules/test_dynamique.py
python recon/trafic/vehicules/valider_vehicules.py
python -I recon/trafic/vehicules/construire_parametres.py
python recon/trafic/vehicules/test_parametres.py
python recon/trafic/vehicules/population.py --n 3000 --graine 1
```

Résultat de validation (v0.1) : erreur absolue moyenne en validation croisée 7,7 % (60-100 km/h), 8,4 %
(80-120 km/h), 4,0 % (0-100 km/h) sur 10 voitures ; 3,6 / 3,5 / 1,3 % sur les 4 électriques. Les classes PL,
bus et 2RM ont des données de masse, puissance et réglementation, mais pas encore de calage dynamique.
Dépendances : bibliothèque standard Python 3.11 uniquement.
