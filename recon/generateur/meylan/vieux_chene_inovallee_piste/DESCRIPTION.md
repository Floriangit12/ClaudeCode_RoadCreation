# Chemin du Vieux Chêne (Inovallée) — rue à piste cyclable séparée, îlot peint ocre, carrefour en T à feux

*Relevé Meylan, lot A, 17/10/2026. Site M16 du dossier `D:\DocRoute\13_Observations_Panoramax_Isere` (« carrefour à feux
chemin du Vieux Chêne, Inovallée »). Point du site : 45,208691 N, 5,797932 E ; Lambert-93 (919 608,06 ; 6 460 487,77) ;
z ≈ 215,7 m (RGE ALTI). Centre du carrefour : nœud OSM à (−1,04 ; −2,64) m.*

**État décrit : 28/07/2026** (campagne IGN, photos 360° de 07:52), le plus récent. Depuis l'ortho IGN 2024, l'enrobé a
été refait et la traversée cyclable verte remplacée par des figurines et doubles chevrons.

**Réseau (lot N1, 18/10/2026).** date d'état **28/07/2026** (enrobé refait depuis l'ortho 2024 : la photo prime) ; pas de nœud partagé. Description au format réseau, résolue par `recon/generateur/reseau/resoudre_reseau.py` ; nœuds partagés et contrats de profil dans `../reseau_meylan.yaml`.

**Reconstruction (étape 3, 18/10/2026).** Branches tracées vers le carrefour, en polylignes OSM lissées (les cassures non raccordées faisaient s'emballer la fabrication sous les îlots peints, BESOINS V1). Détail : `RECONSTRUCTION.md` ; manques du générateur : `BESOINS.md`.

## 1. Description simple

> Rue d'Inovallée à 50 km/h sous de grands arbres. Une voie par sens d'environ 3,3 m, séparées au milieu par une
> bande peinte remplie d'ocre (pas de hachures) d'environ 2 m à l'ouest et 1 m à l'est. Côté nord, une bande d'herbe
> (4 m à l'ouest, 7 m à l'est) puis une piste séparée piétons / vélos en enrobé, environ 3 m pour les vélos et 1,5 m
> pour les piétons. Petit carrefour en T à feux avec une rue de desserte au nord, à double sens, d'environ 5 m sans
> ligne au milieu. Passages piétons à feux à bouton d'appel avec un petit refuge rond à l'ouest ; sur la desserte, la
> piste traverse avec des figurines vélo et des doubles chevrons. Arrêts de bus de chaque côté juste à l'ouest, avec
> abris et zigzags jaunes. Enrobé neuf presque noir, marquages neufs, haies, candélabres, palissade de chantier au sud.

## 2. Ordre de construction (celui de la chaîne)

L'ordre qui fait foi est celui de la chaîne de construction (`../../CHAINE_CONSTRUCTION.md` § 2 et `chaine_construction.json`) : bordures et caniveaux avant l'enrobé, marquages avant la retenue et les panneaux, éclairage après les panneaux. L'ordre que proposait ce relevé est rangé ci-dessous dans ces étapes (relecture de la préparation, § 3).

| Étape de la chaîne | Ce que le site y construit |
|---|---|
| E07 plate-forme | terrain plat (z ≈ 216 m) |
| E08 bordures | bordures de trottoir et de quais, refuge rond, bordurettes de la piste |
| E10 chaussée | 2 × 1 voies, rue de desserte, enrobé neuf |
| E11 trottoirs, pistes | piste séparée (vélos + piétons) au nord, bandes enherbées, liaisons revêtues aux passages |
| E12 marquages | îlots peints ocre à contour blanc (pratique locale photographiée), rives, passages, figurines et doubles chevrons de la traversée cyclable, zigzags jaunes des arrêts |
| E14 signalisation et feux | feux tricolores, feux piétons et cyclistes à bouton, panneaux d'arrêt de bus |
| E15 éclairage | candélabres |
| E16 mobilier | abribus, borne incendie |
| E17 végétation (plus tard) | grands arbres, haies |

## 3. Constats et provenance

| Élément | Valeur | Provenance |
|---|---|---|
| Chaussée ouest (20 m) | 9,1 m : 3,34 / îlot ocre 2,29 / 3,31 ; bande enherbée 3,7 ; piste 2,9 + trottoir 1,6 | coupe `o_20` (GAM) ; photo 17826b13 |
| Chaussée est (20 m) | 7,3 m : 3,36 / îlot ocre 0,95 / 3,01 ; bande enherbée 7,1 au nord ; bande 1,1 au sud | coupe `e_20` ; photo 7d44455e (l-0154.3) |
| Desserte nord | 5,2 m à double sens, trottoirs 2,0 et 1,4 | coupe `n_12` ; OSM 1425974964 (shared_lane) |
| Régime | feux sur les 3 branches, passages à feux à bouton d'appel | OSM traffic_signals ×3, crossings ×3 |
| Traversée cyclable | figurines + doubles chevrons (conformes à l'IISR7 art. 118-1 C) | photo 7d44455e (l+0051.4) |
| Îlot peint | rempli d'ocre sans hachures (différent de l'IISR7 p. 6) | photos 7d44455e, 17826b13 ; dossier 13 OBS-ILO-03 |
| Bus | arrêts « Busserolles » des deux côtés, abris, zigzags | OSM 911300141 ; levé GAM ; photos |

## 4. Ce que la description simplifie

- Les îlots peints ocre sont décrits en zones hachurées : le remplissage coloré sans hachures, les arrêts de bus en
  alignement avec abri et la traversée cyclable à figurines et chevrons sur une branche de carrefour n'ont pas de mot
  (`../BESOINS_FORMAT.md`).
- Plan de feux supposé (2 phases).
