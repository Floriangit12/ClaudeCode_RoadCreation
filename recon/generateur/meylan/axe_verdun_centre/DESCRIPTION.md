# Avenue de Verdun (D1090), centre de Meylan — 2 × 1 voies à îlot central peint

*Lot B du relevé de Meylan, 17/10/2026. Site : avenue de Verdun entre Paquet Jardin (M01, k ≈ 1 004) et le carrefour
du lycée (M08, k ≈ 1 990), en deux tronçons de part et d'autre du carrefour à feux M17 (k ≈ 1 567). Les carrefours
relèvent du lot A ; le passage à refuge de k ≈ 1 325 est déjà décrit en détail à l'étape 1
(`scenes_meylan/M27_avenue_de_verdun.yaml`) : ce site le prolonge et en corrige les largeurs par l'ortho.*

**Réseau (lot N1, 18/10/2026).** date d'état **18/05/2025** ; tronçon 1 de `N_VERDUN_PJ_NE` (k ≈ 1 104) à `N_VERDUN_M17_SO` (k ≈ 1 478), tronçon 2 de `N_VERDUN_M17_NE` (k ≈ 1 627) à `N_VERDUN_M08_SO` (k ≈ 1 920) : un tronçon, un propriétaire, les carrefours du lot A gardent leurs branches ; les abscisses des évènements sont comptées depuis ces débuts ; à chaque bout, le résolveur raccorde le profil de l'axe au profil mesuré par le carrefour (contrat du nœud) sur 25 à 30 m. Description au format réseau, résolue par `recon/generateur/reseau/resoudre_reseau.py` ; nœuds partagés et contrats de profil dans `../reseau_meylan.yaml`.

## 1. Description en texte libre

> Avenue de quartier à 50 km/h, une voie par sens d'environ 3,60 m, séparées par une bande peinte d'environ 3,40 m
> (deux lignes continues et des hachures) ; à chaque passage piéton elle devient un refuge bordé de bordures basses,
> et aux rues latérales elle s'ouvre en petite voie de tourne-à-gauche avec flèche. Pas de bordure le long des voies :
> une rive peinte puis un accotement d'herbe (fleuri au printemps) de 4 à 6 m. Côté nord-ouest, une piste cyclable à
> double sens de 4 m en enrobé doublée d'un trottoir ; côté sud-est, un trottoir de 2 m ; au-delà, des haies taillées,
> de grands arbres (cèdres, peupliers, saules) et des immeubles. Candélabres à simple crosse d'environ 9 m côté
> nord-ouest, abris de bus. Enrobé ancien très fissuré, fissures pontées, marquages usés.

## 2. Ordre de construction (celui de la chaîne)

L'ordre qui fait foi est celui de la chaîne de construction (`../../CHAINE_CONSTRUCTION.md` § 2 et `chaine_construction.json`) : bordures et caniveaux avant l'enrobé, marquages avant la retenue et les panneaux, éclairage après les panneaux. L'ordre que proposait ce relevé est rangé ci-dessous dans ces étapes (relecture de la préparation, § 3).

| Étape de la chaîne | Ce que le site y construit |
|---|---|
| E07 plate-forme | chaussée unique de 10,8 m entre rives, accotements enherbés au même niveau |
| E08 bordures | bordures basses (vue 0,11) autour des refuges de 10-14 m aux passages piétons |
| E10 chaussée | enrobé ancien fissuré (pontages), piste à double sens et trottoirs en enrobé |
| E11 trottoirs, pistes | accotements enherbés, liaisons revêtues des passages |
| E12 marquages | continues et hachures de l'îlot central, rives, passages piétons (bandes prolongées sur les liaisons revêtues), flèches des poches de tourne-à-gauche |
| E14 signalisation | C20a aux passages, arrêts de bus ; feux aux carrefours (lot A) |
| E15 éclairage | candélabres côté nord-ouest |
| E16 mobilier | abris de bus |
| E17 végétation (plus tard) | bandes plantées, haies taillées, grands arbres |

## 3. Profil (nord-ouest → sud-est), mesuré sur l'ortho

| Élément | Largeur | Provenance |
|---|---|---|
| bande plantée, trottoir, piste à double sens | 2,0 · 2,0 · 4,0 m | OSM (cycleway width = 4 à t ≈ +13, trottoir à +13…+15) ; photos |
| accotement enherbé | 5,6 m (5,0 au tronçon 2) | ortho : rive +5,2 → piste +11 |
| voie vers La Tronche | 3,6 m | lignes +5,2 / +1,4 (axe à axe ; ≈ 3,45 entre bords) |
| îlot central peint | 3,4 m | lignes +1,4 / −1,9 ; refuges bordés aux passages |
| voie vers Meylan | 3,6 m | lignes −1,9 / −5,6 |
| accotement enherbé, trottoir, bande plantée | 4,4 · 2,0 · 3,0 m | ortho ; OSM (trottoir à −10…−12) |

## 4. Simplifications et incertitudes

- Voies de 3,60 m au lieu des 3,25 m estimés à l'étape 1 sur photo : écart à la règle urbaine (2,75-3,25) admis et
  justifié (`ecarts_admis`) ; îlot 3,40 au lieu de 2,80.
- Les poches de tourne-à-gauche (tous les 60-100 m selon OSM) ne sont pas positionnées, sauf une (k ≈ 1 767) ; l'arrêt
  de bus (k ≈ 1 690) est dans `extensions_auto` (le format exige un trottoir contigu à la chaussée).
- Au tronçon 2, les lignes du sens vers Meylan sont masquées par les arbres sur l'ortho : profil supposé symétrique.

## Reconstruction (lot SITES, étape 3, 18/10/2026)

Itération 0 (lot SITES) : approche du carrefour M17 dite avec le profil mesuré par M17 sur les 35 derniers mètres de T1 (le raccord généré faisait planter le générateur) ; le site est fabriqué en deux scènes (T1, T2) dérivées de `description.yaml` (`BESOINS.md` V-C1). Constat des photos 392b3706 et 1791b85f (18/05/2025) : depuis Paquet Jardin, la chaussée reste à 2 × 2 voies jusqu'à k ≈ 1 140, puis la voie de gauche du sens nord-est se rabat et l'îlot hachuré s'ouvre (le raccord généré la remplace par une transition de 30 m, `BESOINS.md` V-C2). Détail : `RECONSTRUCTION.md`.
