# Carrefour Vieux Chêne × Taillefer × Hélice (M07) — compréhension de la scène (passe v2)

*`recon/generateur/meylan/vieux_chene_taillefer_feux/COMPREHENSION.md` — 18/10/2026, étape 3, passe v2 du lot
« carrefours ». État décrit : **28/07/2026** (fenêtre d'état des photos : depuis le 01/06/2025 ; 40 photos dedans,
20 antérieures « hors fenêtre » du 01/05/2024 et du 23/11/2024). Aucune photo n'est versionnée : vues sous
`recon/out/generateur/meylan_vieux_chene_taillefer_feux/comparaison/meylan_vieux_chene_taillefer_feux/photos_non_versionnees/v2/vues/`.*

J'ai regardé moi-même les images en tuiles natives et croisé ce qu'elles montrent ; aucun algorithme n'a fusionné les
sources. Positions lues avec une grille de 1 m posée sur l'IGN 20 cm (et le levé GAM en surimpression) :
`recon/out/generateur/meylan_vieux_chene_taillefer_feux/_travail/v2/lecture/` (images sans photo de tiers). Repère du
site : x vers l'est, y vers le nord, origine au point M07 (L93 918 477,69 ; 6 460 317,67).

## 1. Images lues

| Source | Date | Ce que j'en ai tiré |
|---|---|---|
| IGN BD ORTHO 20 cm, vue générale, zoom du centre, lectures à grille `ign24_centre_g5`, `ign24_coeur`, `ign24_gam_centre`, `ign24_gam_N`, `ign24_gam_SO` | 09/08/2024 | formes des îlots, position de l'îlot refuge du Taillefer (≈ (−2,6 ; 8 à 11,5)), cœur en enrobé uni (traces de pneus seulement), passages |
| IGN 2021, 2018, 2015, IRC 2024, Pléiades 2025 (planches de dates) | 2015 → 2025 | même dessin des îlots depuis 2015 ; végétation des îlots directionnels (IRC) |
| Levé GAM (bordures, marquages) en surimpression | — | bordures des branches et des îlots (justes à ≈ 0,5 m sur l'ortho) ; **zébra du Taillefer du levé décalé de ≈ 4 m vers le sud par rapport à l'ortho 2024 et aux photos** (levé d'un autre état : non retenu pour le passage) |
| Planches du centre `centre_p01` à `centre_p12` (48 des 65 vues du centre) | 2024 → 2026 | tour d'horizon : îlots, mâts, B21, traversées vertes, damier ouest |
| Vues natives : c02e39f5_-131, cba31686_-060, fccb6997_-180, 45da0502_+024, 2a5175d2_+009, 0190214f_-170 | 28/06 et 28/07/2026 | îlot refuge du Taillefer, traversée verte, îlot du tourne-à-droite Hélice → est, îlot du tourne-à-droite ouest → Hélice, voies du Taillefer |
| Plan de vue de dessus rendu \| ortho (`dessus/planche_dessus_centre_ign_t00..t03`) | passe 1 | écarts du modèle de la passe 1 |

## 2. La scène en une phrase

Un grand carrefour à feux à **cœur en enrobé uni, très rapiécé**, sans marquage intérieur : quatre branches qui y
débouchent chacune avec un **îlot** (refuge du Taillefer, îlot étroit à balise du Vieux Chêne ouest, séparateur en
gravillons du Vieux Chêne est, îlot central de l'Hélice) et **deux tourne-à-droite directs** en cédez derrière des
îlots d'angle (Hélice → Vieux Chêne est, petit îlot triangulaire revêtu ; Vieux Chêne ouest → Hélice, grand îlot
triangulaire).

## 3. Le centre (zone de conflit)

| Élément | Où (repère du site) | Images |
|---|---|---|
| **Cœur** | enrobé uni, très rapiécé, aucun marquage de guidage, pas de flèche ni d'îlot libre ; traces de pneus | `ign24_coeur` (2024) ; 0190214f_-117, 45da0502_-076, -042 (2026) ; fccb6997_-180 |
| **Îlot refuge du Taillefer** | séparation des sens au débouché : îlot bordé ≈ 1,5 × 4 m, contour peint, B21 face au cœur, vers (−2,6 ; 8 à 11,5) ; mât de feu sur l'îlot ; le passage et la **traversée cyclable verte** (côté cœur) le coupent ; au-delà, séparateur étroit bordé sur ≈ 8-10 m | `ign24_coeur` ; c02e39f5_-131, -174 ; 3c82fa3f_+013 ; 23ecaea9_+003 ; 2a5175d2_+009 |
| **Passage du Taillefer** | bandes épaisses, ≈ 3-4 m, vers y ≈ 12-16 (côté nord de l'îlot), bande verte de traversée cyclable accolée côté cœur | c02e39f5_-131 ; 3c82fa3f_+013 ; ad0b728e_+091 ; IGN 2024 |
| **Îlot du tourne-à-droite Hélice → Vieux Chêne est** | petit triangle revêtu bordé vers (8 à 11 ; −2 à −6), mât, B1 et D21 ; la voie directe (≈ 4 m) passe à l'est, en cédez | fccb6997_+153 ; 45da0502_-042, -076 ; 0190214f_-091 ; IGN 2024 |
| **Îlot du tourne-à-droite Vieux Chêne ouest → Hélice** | grand triangle bordé entre (−20 ; −12), (−9 ; −13) et (−6 ; −30), revêtu côté pointe, D21 groupés, B1 | 45da0502_+024 ; d873ad85_+138 ; IGN 2024, `ign24_gam_SO` |
| **Îlot du Vieux Chêne ouest** | îlot étroit allongé (≈ 1,2-1,5 m) entre la sortie et les entrées, de (−24 ; −11) à (−13 ; −5,5), nez arrondi côté cœur, balise | `ign24_gam_SO` (bordure GAM fermée) ; e5c7653d ; 88049009 |
| **Hélice** | deux voies d'entrée (TAG, TD/TAD) et deux de sortie, séparées par un îlot central étroit bordé jusqu'au bord du cœur (y ≈ −10) | IGN 2024 ; d873ad85_-168 ; ad0b728e_+058 |
| **Vieux Chêne est** | trois voies d'entrée (deux TAG, TD/TAD) derrière un séparateur bordé en gravillons, sortie + voie du shunt | passe 1 (photos 3eb5557e, efc67150, 12844b83) ; IGN 2024 |

## 4. Contradictions et comment je les ai tranchées

| Contradiction | Tranchée ainsi |
|---|---|
| Zébra du Taillefer : levé GAM vers (−11 ; 3) → (1 ; 11) / ortho 2024 et photos 2026 : au nord de l'îlot refuge (y ≈ 12-16) | photos 2026 (état décrit) et ortho 2024 concordent : passage au nord de l'îlot ; le levé GAM est d'un autre état |
| Axe du Taillefer (passe 1, médiane OSM) : îlot refuge du modèle à ≈ 3 m à l'ouest de l'îlot réel | l'îlot (séparation des sens) est lu sur l'ortho et confirmé par la bordure est du levé GAM : axe déplacé de 2,5 m vers l'est |
| Photos de 2024 (HF) et de 2026 : même géométrie, marquages un peu plus usés en 2026 | géométrie stable ; état du 28/07/2026 |

## 5. Ce qui reste incertain

- La largeur réelle de l'îlot refuge du Taillefer (1,2 à 1,8 m) et la longueur du séparateur étroit au-delà.
- Le nombre de voies d'entrée du Taillefer à la ligne de feux (OSM : 3 ; photos : 2 nettes et une surlargeur à droite).
- Le régime exact des tourne-à-droite directs (cédez vu sur OSM ; panneau AB3a non lu sur les photos).
- Le plan de feux (non observable).

## 6. Ce que la description en tire

Itération v2-1 : îlot refuge du Taillefer (ouverture de 4 m, terre-plein bordé 1,5 m) ; v2-2 : axe du Taillefer
déplacé de 2,5 m vers l'est (îlot sur sa position réelle). Le reste du centre (cœur uni, deux îlots directionnels,
îlots de l'Hélice et du Vieux Chêne) était déjà juste en plan à ≈ 1-2 m. Ce que le format ne sait pas dire :
`BESOINS.md` (traversées cyclables vertes et damier, îlot refuge plus court que l'îlot du profil, séparateur étroit).
