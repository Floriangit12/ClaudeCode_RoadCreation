# A41 à Meylan — échangeur 26 « Meylan-Est / Inovallée » et convergence de la branche N87

*Lot B du relevé de Meylan, 17/10/2026. Site : A41 de x ≈ 919 110 à 920 280 (L93), 1 300 m, avec la branche
qui amène la Rocade Sud (N87) vers Chambéry, la sortie 26 (sens Chambéry → Grenoble) et les bretelles de
Meylan-Est. État décrit : 2024-2025. Voir `description.yaml`, `mesures.json`, `photos.json`.*

**Réseau (lot N1, 18/10/2026).** date d'état **28/02/2026** (photo 0ee0e9e0 la plus récente, cohérente) ; l'A41 commence sur `N_A41_MEYLAN_EST_O`, la branche N87 et la sortie vers Meylan-Est sur `N_A41_BRANCHE_N87` ; séparateur central en **DBA**. Description au format réseau, résolue par `recon/generateur/reseau/resoudre_reseau.py` ; nœuds partagés et contrats de profil dans `../reseau_meylan.yaml`.

## 1. Description en texte libre

> Autoroute en rase campagne, 110 km/h, sans éclairage, entre deux rideaux d'arbres. Au milieu, un terre-plein étroit
> tout en enrobé (3,3 m entre les lignes continues) avec une GBA en béton. Côté Grenoble (nord), 3 voies de 3,60 m et
> une BAU de 3 m ; environ 100 m avant la sortie, une 4e voie s'ouvre à droite (voie de décélération, ligne à tirets
> larges), puis elle se détache : deux lignes continues encadrent une zone de chevrons longue d'environ 90 m, une
> balise verte et blanche marque le nez, et la bretelle de sortie (une voie de 4 m, rive gauche continue, rive droite
> en tirets longs, accotement de 2 m, glissière) tourne vers le nord et monte jusqu'à un carrefour avec la route qui
> franchit l'autoroute sur un pont à poutres en béton. Côté Chambéry (sud), l'A41 a 2 voies et une BAU ; juste à côté,
> derrière une double glissière, roule une seconde chaussée à 2 voies : la branche qui vient de la Rocade Sud. Cette
> branche a sa propre sortie vers Meylan-Est (au droit du pont) et reçoit 280 m plus loin l'entrée de Meylan-Est par
> une voie d'insertion. 900 m après le pont, la double glissière s'arrête et les deux chaussées se juxtaposent :
> 4 voies côte à côte (la ligne entre les deux groupes est en tirets courts), un « cédez le passage » à droite, puis la
> voie de droite disparaît en biseau ; il reste 3 voies et une BAU large. Plus loin, un portique avec panneau à
> messages variables.

## 2. Ordre de construction (celui de la chaîne)

L'ordre qui fait foi est celui de la chaîne de construction (`../../CHAINE_CONSTRUCTION.md` § 2 et `chaine_construction.json`) : bordures et caniveaux avant l'enrobé, marquages avant la retenue et les panneaux, éclairage après les panneaux. L'ordre que proposait ce relevé est rangé ci-dessous dans ces étapes (relecture de la préparation, § 3).

| Étape de la chaîne | Ce que le site y construit |
|---|---|
| E07 terrassements, ouvrages | plate-forme commune (remblai léger) pour l'A41 et la branche N87, plates-formes des bretelles ; pont de l'échangeur (piles dans le TPC et entre l'A41 et la branche, culée en talus bétonné), avant les enrobés |
| E10 chaussée | A41 (3 + 2 voies), branche (2 voies), voie de décélération, voie d'insertion, 3 bretelles de 4 m |
| E12 marquages | rives continues 3u, T4 3u des BAU, T1 2u entre voies (T3 2u après la convergence), T2 5u des voies d'insertion et de décélération, T'3 3u des bretelles, chevrons et lignes du musoir de la sortie 26 |
| E13 retenue | DBA au TPC sur toute la longueur ; glissières simples aux bords extérieurs ; double glissière entre l'A41 et la branche jusqu'à s = 908 |
| E14 signalisation | limitation 70 et balise de musoir (J14a probable), AB3a + panonceau « cédez le passage » dans la zone à 4 voies, panneaux de direction portés par le pont, portique PMV à l'est |
| E17 abords (plus tard) | bois au nord et au sud, champ au sud-est, ligne HT |

## 3. Profils mesurés (ortho IGN 2024, coupes redressées)

| Tronçon / zone | Profil (gauche → droite dans le sens du tronçon) | Provenance |
|---|---|---|
| A41, s 0-364 et 463-908 | berme · glissière · BAU 3,0 · T4 · 3 voies ← (3,6 / 3,6 / 3,5) · continue 3u · BDG 1,0 · GBA (≈ 0,8) · BDG 1,4 · continue 3u · 2 voies → (3,6 / 3,6) · T4 · BAU 3,0 · glissière | coupes a41_est s0050-s0400 |
| A41, s 364-463 (sens ←) | + voie de décélération 3,5 à droite des usagers, ligne T2 5u | OSM 667912799 ; coupe s0400 ; photos bf8e09f3, c0a557b7 |
| A41, s 908-1250 | sens → : 4 voies (3,6 / 3,6 / 3,6 / 3,2), T3 2u au milieu, BAU 3,6 ; biseau de la voie de droite jusqu'à s ≈ 1 250 | coupes s0950-s1150 ; photos d7473696, efe0ae74, d5742174 |
| branche N87 | glissière double · BDG 0,8 · continue · 2 voies → (3,6 / 3,7) · T4 · BAU 2,7 · glissière ; voie d'insertion 3,5 de s = 280 à ≈ 480 | coupes branche_n87 ; photo e8712f96 |
| bretelles (3) | accotement 0,5 · continue 3u · voie 4,0-4,2 · T'3 3u · BAU 2,0 · glissières | coupes bretelle_* ; photo 4d06322c |

## 4. Simplifications et incertitudes

- Lignes à ± 0,15 m ; position de la GBA à ± 0,3 m (pics confondus avec ses faces éclairées).
- La voie d'insertion de la branche n'a pas de fin relevée (60 m de biseau [G]) ; le biseau 4 → 3 (80 m ± 30) est
  plus court que l'oblique réglementaire (avertissement du compilateur, `mesures.json` § écarts).
- Les bretelles sont décrites par les polylignes OSM (cassures de 16 à 25°) : rayons non ajustés ; leur raccord à
  l'A41 (musoir, nez, voie de décélération) et le pont sont dans `extensions_auto` (BESOINS B1-B5, B9).
- Le carrefour en haut de la sortie (côté Inovallée) n'est pas décrit (hors lot B).
