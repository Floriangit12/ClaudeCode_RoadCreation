# Avenue de Verdun (D1090), centre de Meylan — 2 × 1 voies à îlot central peint

*Lot B du relevé de Meylan, 17/10/2026. Site : avenue de Verdun entre Paquet Jardin (M01, k ≈ 1 004) et le carrefour
du lycée (M08, k ≈ 1 990), en deux tronçons de part et d'autre du carrefour à feux M17 (k ≈ 1 567). Les carrefours
relèvent du lot A ; le passage à refuge de k ≈ 1 325 est déjà décrit en détail à l'étape 1
(`scenes_meylan/M27_avenue_de_verdun.yaml`) : ce site le prolonge et en corrige les largeurs par l'ortho.*

## 1. Description en texte libre

> Avenue de quartier à 50 km/h, une voie par sens d'environ 3,60 m, séparées par une bande peinte d'environ 3,40 m
> (deux lignes continues et des hachures) ; à chaque passage piéton elle devient un refuge bordé de bordures basses,
> et aux rues latérales elle s'ouvre en petite voie de tourne-à-gauche avec flèche. Pas de bordure le long des voies :
> une rive peinte puis un accotement d'herbe (fleuri au printemps) de 4 à 6 m. Côté nord-ouest, une piste cyclable à
> double sens de 4 m en enrobé doublée d'un trottoir ; côté sud-est, un trottoir de 2 m ; au-delà, des haies taillées,
> de grands arbres (cèdres, peupliers, saules) et des immeubles. Candélabres à simple crosse d'environ 9 m côté
> nord-ouest, abris de bus. Enrobé ancien très fissuré, fissures pontées, marquages usés.

## 2. Ordre de construction

1. Plate-forme : chaussée unique de 10,8 m entre rives, accotements enherbés au même niveau.
2. Refuges : bordures basses (vue 0,11) autour des îlots de 10-14 m aux passages piétons.
3. Enrobés : chaussée (ancienne, fissurée), piste à double sens et trottoirs.
4. Accotements enherbés, bandes plantées, haies taillées, grands arbres.
5. Marquages : continues et hachures de l'îlot central, rives, passages piétons (bandes prolongées sur les liaisons
   revêtues des accotements), flèches des poches de tourne-à-gauche.
6. Signalisation : C20a aux passages, arrêts de bus ; feux aux carrefours (lot A).
7. Éclairage côté nord-ouest, abris de bus, immeubles.

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
