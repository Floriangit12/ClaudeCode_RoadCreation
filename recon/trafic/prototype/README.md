# recon/trafic/prototype — prototype du modèle « conducteur + véhicule » (v0.2, 17/10/2026)

Prototype, en Python (numpy), du modèle conçu dans
`D:\DocRoute\17_Modele_Vehicules_Conducteurs\04_Conception\MODELE_CONDUCTEUR_VEHICULE.md`.

- Les lois et valeurs sourcées sont **lues** dans `assets/specs/trafic/parametres_modele.json` : les entrées « ref » de
  `DEFAUTS_PROTOTYPE` (`parametres.py`) désignent l'identifiant et la clé à lire (HDM, kB de Markkula, créneau du Certu,
  jerk, défauts EIDM, tpreview calé sur inD…). Rien de sourcé n'est recopié dans le code.
- Les valeurs propres au prototype sont déclarées dans `DEFAUTS_PROTOTYPE` avec leur nature (`calage`, `convention`,
  `hypothese`) et leur justification ; tous les seuils numériques du simulateur y sont (v0.1 : une douzaine de
  littéraux dans `simulateur.py`). `calage.py` écrit `assets/specs/trafic/parametres_prototype.json` ; seules les
  entrées `calage` y sont relues.
- Rapport, figures et tableaux : `D:\DocRoute\17_Modele_Vehicules_Conducteurs\05_Prototype\` (`RAPPORT_PROTOTYPE.md`).
  Corrections de la relecture adverse : `D:\DocRoute\17_Modele_Vehicules_Conducteurs\CRITIQUES_ET_CORRECTIONS.md`.

| Fichier | Rôle |
|---|---|
| `parametres.py` | accès aux paramètres (index, références au modèle, lois via `conducteurs/lois.py`, groupes de la copule) ; conventions, calages et hypothèses du prototype avec leur source ; écriture de `parametres_prototype.json` |
| `conducteurs.py` | tirage de la population par copule gaussienne à deux facteurs (style, vigilance), corrélation intra-groupe ρ_w < 1, grandeurs ordonnées sans croisement (TPR par incrément, planchers a1 ≥ b, TIV min ≤ moyen), troncature basse de la loi ONISR ; T_suivi par réseau ; distraction liée à la vigilance ; tirages par rencontre (STOP) |
| `vehicules.py` | tirage des VP (volet 01, `vehicules/population.py` : loi conjointe masse / P/m / famille, parc en circulation) ; a_max(v, pente, µ) vectorisé (même formule que `vehicules/dynamique.py`) ; freinage ≤ min(d_max, µg) |
| `modele.py` | fonctions pures : IIDM, CAH et combinaison ACC, facteur de démarrage EIDM, vitesse en courbe (Bosetti / Sétra × κ, plafonnée par √(a_lat,i R)), triangle g-g, looming, prédiction de Markkula, décélération requise, décision au jaune (option H-11) |
| `route.py` | itinéraires 1D : courbes, ralentisseurs, feux (horaires par couloir), STOP, jonctions, détecteurs, pente |
| `simulateur.py` | simulateur à pas fixe (0,1 s, balistique, graine) : perception (points d'action, ε, Wiener HDM, événements jugés avec le b du suiveur, Markkula ou TPR, distraction H-18), décisions tactiques (feux, STOP, créneaux, H-10 avec prioritaire médian), contrôle (IIDM + CAH, T contextuel ≥ Δ_a, démarrage, jerk, urgence, triangle g-g), véhicule (capacité, adhérence, cercle de friction, pente de l'itinéraire), collisions (choc inélastique, primaires / secondaires), détecteurs, traces |
| `lateral.py` | point de visée (pure pursuit) + bicyclette cinématique, appliqués aux trajectoires de la courbe |
| `scenarios.py` | S1 file au vert, S1b jaune, S2 freinage d'urgence, S3 STOP et créneaux, S4 courbe R 60 m, S5 dos-d'âne (loi belge, variante bruxelloise) |
| `sumo_scenarios.py` | mêmes scénarios dans SUMO 1.27.1 (netconvert), Krauss et EIDM, réglages par défaut et « nos lois » (un vType par conducteur tiré, apparié), intégration d'Euler pour tous ; S1 : tau calé par modèle ; S2 : meneur à decel = apparentDecel = b, EIDM treaction = TPR inattendu, variantes actionStepLength et driverstate ; S3 : impatience 0,5 (et transfert brut) |
| `analyse.py` | métriques communes (modèle et SUMO), créneau critique par maximum de vraisemblance (Troutbeck) et mesures depuis l'arrêt / au point de conflit, collisions primaires et taux sachant le meneur intact, contrôles de population |
| `figures.py`, `tableaux.py` | figures (PNG ≤ 1300 × 750 px) et tableaux du rapport |
| `calage.py` | calage du démarrage (Salles 2020 p. 14), du facteur d'accélération de décharge (Salles fig. 8) et de r (Certu Feux 2010 p. 34) sous contrainte de zéro collision primaire (5 graines × 200 files) |
| `executer.py` | exécute tout et écrit `05_Prototype/resultats/resultats_prototype.json`, `figures/`, `sumo/` |

```bash
cd D:/ClaudeCode_RoadCreation
python recon/trafic/prototype/calage.py                 # ≈ 1 min -> parametres_prototype.json, 05_Prototype/resultats/calage.json
python recon/trafic/prototype/executer.py               # ≈ 25 min avec SUMO ; --rapide ≈ 6 min ; --sans-sumo ≈ 2 min
python recon/trafic/prototype/tableaux.py               # tableaux Markdown/CSV à partir des résultats
python -m unittest discover -s recon/trafic/tests -v    # 41 tests, ≈ 25 s
```

Dépendances : Python 3.11, numpy, scipy ; SUMO 1.27.1 (`sumo`, `netconvert`, `SUMO_HOME/tools` pour sumolib et traci)
pour la comparaison ; matplotlib pour les figures (installé hors de C: dans
`D:\DocRoute\17_Modele_Vehicules_Conducteurs\tmp\03\pylib`, ajouté au chemin par `executer.py`). Les scripts ne lisent
que des fichiers produits par le projet (aucun fichier téléchargé). Outils de débogage intégrés au simulateur :
attributs `debug_agent` / `debug_t0` / `debug_t1` (impression des grandeurs perçues) et `surveiller` (journal de positions).
