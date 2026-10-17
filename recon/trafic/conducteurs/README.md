# recon/trafic/conducteurs — prototype du modèle de conducteurs

Code du volet « conducteurs » du modèle de véhicules et de conducteurs. La documentation et les données sont dans `D:/DocRoute/17_Modele_Vehicules_Conducteurs/02_Conducteurs/` (`CONDUCTEURS.md`, `conducteurs_parametres.json`, `profils_conducteurs.json`, `sources/`).

| Fichier | Rôle |
|---|---|
| `lois.py` | lois de probabilité. Ajuste une loi sur des statistiques publiées (moyenne / écart-type, moyenne / percentile, taux de dépassement, V85, P10 / P90). Fournit quantiles, fonctions de répartition, moments et tirage par inversion. |
| `sources_conducteurs.py` | catalogue des sources (titre, auteurs, année, URL, fichier local, licence, type). |
| `construire_parametres.py` | écrit `conducteurs_parametres.json` : 108 paramètres sourcés, forme `{id, grandeur, population, loi, parametres, unite, conditions, nature, source{doc, page, annee}, confiance}`. |
| `construire_profils.py` | écrit `profils_conducteurs.json` : facteurs latents, charges justifiées, corrélations attendues, profils (prudent, moyen, pressé, agressif, distrait, novice, senior, PL, bus, cyclistes) et correspondance SUMO. |
| `modele_conducteurs.py` | tire une population par copule gaussienne à deux facteurs, style et vigilance (`tirer_population`). Tire aussi un comportement discret à chaque rencontre (`tirer_evenement`) et calcule les quantiles conditionnels. |
| `valider.py` | 15 contrôles : forme, reproduction des statistiques publiées (dont centiles NCHRP de la décélération d'urgence, lois tronquées), vitesses, marges et corrélations, normes françaises (γv corrigé), profils, cohérences ; les contrôles vrais par construction (T6, T7b) sont non bloquants et nommés comme tels. Code de sortie 1 si un test bloquant échoue. |
| `exporter_sumo.py` | écrit une `vTypeDistribution` SUMO (un vType par conducteur tiré). |
| `test_sumo_vitesse_libre.py` | test d'intégration SUMO : vitesses libres simulées comparées à la loi ONISR 2023. |
| `outils/` | outils d'extraction utilisés pour les sources : recherche plein texte et rendu de pages PDF, découpe de zones, OCR (RapidOCR, `pip install --user rapidocr_onnxruntime`), lecture des pixels d'une courbe. À lancer avec `python -I` sur des fichiers téléchargés. |

```bash
python construire_parametres.py && python construire_profils.py && python valider.py --n 200000
python exporter_sumo.py --n 200 --reseau artere_centre_ville_50 --sortie vtypes.add.xml --sigma 0
python test_sumo_vitesse_libre.py
```

Dépendances : Python 3.11, numpy, scipy. Pour le test SUMO : sumo et netconvert (1.27.1) dans le PATH.
