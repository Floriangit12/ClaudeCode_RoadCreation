# assets/specs/trafic — paramètres du modèle de véhicules et de conducteurs

Paramètres sourcés du modèle de trafic « conducteur + véhicule » (simulateur ADAS, routes françaises). La
documentation est dans `D:\DocRoute\17_Modele_Vehicules_Conducteurs\` ; le code dans `recon/trafic/`.
**Ne pas éditer ces fichiers à la main** : chacun est produit par un script (colonne « Construit par »).

| Fichier | Contenu | Construit par | Documentation |
|---|---|---|---|
| `parametres_modele.json` | **point d'entrée du modèle** : 359 paramètres et distributions retenus, rangés par couche, avec règles (24), hypothèses (18), facteurs latents et profils, correspondance réseau → vitesse désirée, lecture du modèle de route, correspondance SUMO, 25 cibles de validation | `recon/trafic/conception/construire_parametres_modele.py` | `04_Conception/MODELE_CONDUCTEUR_VEHICULE.md` |
| `parametres_prototype.json` | valeurs propres au **prototype** (v0.2) : calages (démarrage EIDM sur Salles 2020, facteur d'accélération de décharge, r = T_décharge/T_suivi sur 1 800 uvpd/h sous contrainte de zéro collision, tpreview sur inD), conventions (tous les seuils du simulateur) et hypothèses, chacune avec nature et source ; les entrées « reference_modele » sont lues dans `parametres_modele.json` (recopiées pour mémoire) | `recon/trafic/prototype/calage.py` | `05_Prototype/RAPPORT_PROTOTYPE.md` |
| `vehicules_parametres.json` | volet 01 : parc, composition du trafic, classes de véhicules (masses, puissances, dimensions, loi conjointe masse / P/m / famille par segment), dynamique calée ADAC, freinage (neuf et parc en circulation), adhérence, réglementation (158 paramètres) | `recon/trafic/vehicules/construire_parametres.py` | `01_Vehicules/VEHICULES.md` |
| `modeles_existants_reference.json` | volet 03 : valeurs par défaut de SUMO 1.27.1, CARLA, MassTraffic, modèles de la littérature et résultats des scénarios S1-S3 (95 entrées) | `recon/trafic/etat_art_sumo/parametres_reference.py` | `03_Modeles_Existants/MODELES_EXISTANTS.md` |

Le volet 02 (conducteurs) garde ses fichiers dans `D:\DocRoute\17_Modele_Vehicules_Conducteurs\02_Conducteurs\`
(`conducteurs_parametres.json`, `profils_conducteurs.json`) ; `parametres_modele.json` en recopie les 108 paramètres,
les facteurs latents et les profils.

## Forme d'un paramètre (`parametres_modele.json → parametres[]`)

```jsonc
{
  "id": "PER.tpr.anticipe",            // préfixe = couche du modèle
  "couche": "PER",                     // PER STR TAC LON LAT VEH POP CTX VAL REF (voir meta.couches)
  "role": "parametre_conducteur",
  "grandeur": "...", "population": "...",
  "loi": "lognormale", "parametres": {"mu_log": -0.3382, "sigma_log": 0.2166}, "unite": "s",
  "conditions": "...",
  "nature": "estimation",              // norme, mesure, donnee_administrative, donnee_constructeur, derive,
                                       // estimation, calage, defaut_logiciel, mesure_simulation, convention, hypothese
  "source": {"doc": "...", "page": "...", "annee": 1997, "cle": "NCHRP400", "catalogue": "V02:NCHRP400"},
  "confiance": "elevee",               // elevee, moyenne, faible
  "usage": "délai avant action quand l'événement est attendu ...",
  "origine": {"volet": "02_Conducteurs", "fichier": "...", "id": "tpr.anticipe"},
  "tirage": {"facteur": "vigilance", "charge": -0.5, "groupe": "tpr"}   // si tiré par conducteur
}
```

- Couches : `PER` perception, `STR` décision stratégique, `TAC` décision tactique, `LON` et `LAT` contrôle
  opérationnel longitudinal et latéral, `VEH` véhicule, `POP` population, `CTX` contexte (nuit, week-end),
  `VAL` référence de validation, `REF` comparaison (SUMO, CARLA, MassTraffic, littérature).
- Identifiants `XXX.MOD.*` : paramètres propres à la conception (dérivés des calculs de cohérence ou des sources,
  calcul indiqué dans `conditions` et `source`).
- Lois : voir `recon/trafic/conducteurs/lois.py` (GEV au sens MATLAB / Huang : k = forme). Troncature explicite possible
  par les clés `q_min` / `q_max` des paramètres (ordres de quantile ; ex. GEV de Huang coupées à P99).

## Autres sections de `parametres_modele.json`

| Section | Contenu |
|---|---|
| `meta` | version, empreintes sha256 des fichiers d'entrée, effectifs par couche et par nature, pas de temps (0,1 s, balistique) |
| `architecture` | les six couches : fréquence, entrées, sorties, modèle, règles |
| `regles` | R-PER-01 … R-VEH-04 : énoncé, paramètres utilisés, nature, justification |
| `hypotheses` | H-01 … H-13 : énoncé, statut, données de calage |
| `facteurs_latents`, `profils` | copule à deux facteurs (style, vigilance), 19 groupes du volet 02 + groupe « politesse », profils |
| `correspondance_reseaux` | CR-01 … CR-15 : condition sur le modèle de route → loi de vitesse désirée |
| `lecture_modele_route` | éléments de `modele_voie/0.1` lus par le modèle de trafic, usage, état |
| `correspondance_sumo` | paramètre → attribut ou commande SUMO, portée, limite |
| `validation.cibles` | V-01 … V-25 : métrique, scénario, valeurs cibles recopiées des paramètres cités, tolérance proposée, résultats de SUMO par défaut |
| `lacunes` | lacunes de la conception et des volets |
| `sources` | catalogues fusionnés (`V01:*`, `V02:*`, `V03`, `V04:COHERENCE`) |

## Reconstruire et contrôler

```bash
cd D:/ClaudeCode_RoadCreation
python recon/trafic/conception/verifier_coherence.py           # écrit 04_Conception/verification/coherence.json
python recon/trafic/conception/construire_parametres_modele.py  # écrit parametres_modele.json
python recon/trafic/conception/test_parametres_modele.py        # code 1 si échec
```

Le test contrôle la forme, l'identité des lois avec leur volet d'origine, la fraîcheur (empreintes des entrées) et
les renvois internes. Il signale en avertissement 11 paramètres hérités dont la page ou l'année est vide dans leur
volet d'origine (documents non datés).
