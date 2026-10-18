# A41 à Meylan — extrémité ouest : début de l'autoroute, réduction 3 → 2, sortie et entrée 27 Mi-Plaine

*Lot B du relevé de Meylan, 17/10/2026. Site : A41 du carrefour à feux de L'Alpine / avenue de Verdun (limite de
La Tronche, L93 ≈ 916 625 ; 6 459 501) jusqu'au début de `auto_a41_section_courante` (808 m plus à l'est), avec la
sortie 27 (sens Chambéry → Grenoble) et l'entrée de Mi-Plaine (vers Grenoble). État 2024-2025.*

**Réseau (lot N1, 18/10/2026).** date d'état **14/06/2025** ; les deux tronçons de l'A41 se suivent par le nœud local `N_A41_MIPLAINE` et sont fusionnés en une route ; le second finit sur `N_A41_PEPINIERES_O`. Description au format réseau, résolue par `recon/generateur/reseau/resoudre_reseau.py` ; nœuds partagés et contrats de profil dans `../reseau_meylan.yaml`.

## 1. Description en texte libre

> C'est le « bout » de l'autoroute. Vers Chambéry, on part d'un carrefour à feux sur L'Alpine (flèches au sol,
> passage piéton) ; aussitôt après, panneaux « autoroute » et « 110 » des deux côtés, grands panneaux de direction
> bleu (A41 Turin-Milan, Chambéry) et vert (Sisteron, Saint-Martin-d'Hères). Trois voies, puis la voie de gauche se
> rabat au bout de 100 m (panneau de réduction de voies, flèche au sol) et il en reste deux. Le terre-plein central est
> très large au départ (une dizaine de mètres d'herbe haute entre deux glissières, 14 m entre les lignes continues)
> puis se resserre jusqu'aux 7 m de la section courante. Vers Grenoble, deux voies à 90 avec une large bande revêtue à
> gauche ; la sortie 27 (Mi-Plaine, La Tronche, Corenc) se détache à droite avec un musoir à chevrons ; plus loin
> l'entrée de Mi-Plaine ajoute une 3e voie, la vitesse tombe à 70, des candélabres apparaissent, et l'autoroute se
> termine sur un carrefour à feux (feux sur mâts et sur potence, panneau de zone à circulation restreinte). Talus
> enherbés, glissières aux bords, zone d'activités de Mi-Plaine au nord, bois au sud.

## 2. Ordre de construction (celui de la chaîne)

L'ordre qui fait foi est celui de la chaîne de construction (`../../CHAINE_CONSTRUCTION.md` § 2 et `chaine_construction.json`) : bordures et caniveaux avant l'enrobé, marquages avant la retenue et les panneaux, éclairage après les panneaux. L'ordre que proposait ce relevé est rangé ci-dessous dans ces étapes (relecture de la préparation, § 3).

| Étape de la chaîne | Ce que le site y construit |
|---|---|
| E07 plate-forme | talus enherbés, TPC de 14 m au départ qui se resserre à 7 m (transitions de 160 et 248 m) |
| E10 chaussée | 3 + 3 voies sur 108 m (sens est) / 206 m (sens ouest), puis 2 + 2 ; BDG ouest revêtue de 2,4-2,9 m ; bretelles de 4 m |
| E11 terre-pleins | TPC enherbé |
| E12 marquages | rives continues 3u, T4 3u des BAU, T1 puis T3 (dissuasion avant la sortie 27), oblique de réduction et flèche de rabattement, T'3 3u des bretelles, chevrons du musoir |
| E13 retenue | glissières : deux files au TPC, une à chaque bord |
| E14 signalisation | C207 et B14 110 au départ (deux côtés), C28, panneaux de direction ; fin au carrefour à feux |
| E15 éclairage | candélabres sur ≈ 300 m depuis le carrefour |
| E17 abords (plus tard) | Mi-Plaine au nord, bois au sud |

## 3. Profils (mesures ortho, `mesures.json`)

| Zone (s) | Profil, du nord au sud | Provenance |
|---|---|---|
| 0-108 | BAU · 3 voies ← (3,6 / 3,6 / 3,0) · BDG 1,0 · glissière · herbe 8,0 · glissière · BDG 1,0 · 3 voies → · BAU | coupe s0140, photos 80d3d532, 31863b68 |
| 108-206 | idem, sens → réduit à 2 voies (rabattement de la voie de gauche, biseau 80 m [G]) | OSM 1310424871 (merge_to_right) |
| 206-400 | BAU 2,8 · 2 voies ← (3,6 / 3,6) · BDG 2,9 · glissière · herbe 10,3 · glissière · BDG 0,9 · 2 voies → (3,5 / 3,7) · BAU 3,2 | coupes s0260-s0380 (± 0,15) |
| 400-560 | transition vers BDG 2,4 · herbe 6,0 · BDG 0,9 | coupes s0500-s0560 |
| 560-808 | transition vers le profil de la section courante (BDG 1,0 · herbe 4,9 · BDG 1,0 ; BAU 3,4) | auto_a41_section_courante |
| bretelles | accotement 0,5 · voie 4,0 · T'3 · BAU 1,5-2,0 · glissières | coupes bretelle_sortie27, bretelle_entree_miplaine |

## 4. Simplifications et incertitudes

- Vitesse par sens (110 vers l'est, 90 puis 70 vers l'ouest) : le format ne porte qu'une vitesse par tronçon
  (BESOINS B10) ; le carrefour à feux de l'extrémité n'est pas décrit (carrefours : autre lot).
- Le tronçon est coupé en deux à s = 206,9 parce qu'une transition se compare au profil de départ du tronçon
  (BESOINS B13).
- Une seule flèche de rabattement vue ; aucune autre n'est inventée. Biseau du rabattement non mesuré (80 m [G],
  plus court que l'oblique réglementaire : avertissement du compilateur).
