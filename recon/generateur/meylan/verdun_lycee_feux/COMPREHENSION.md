# Carrefour Verdun × Chamrousse × Chaumetière (M08) — compréhension de la scène (passe v2)

*`recon/generateur/meylan/verdun_lycee_feux/COMPREHENSION.md` — 18/10/2026, étape 3, passe v2 du lot « carrefours ».
État décrit : **28/07/2026** ; fenêtre d'état des photos depuis le 01/05/2024 (voirie inchangée depuis : passe 1).
Aucune photo n'est versionnée : vues sous `recon/out/generateur/meylan_verdun_lycee_feux/comparaison/
meylan_verdun_lycee_feux/photos_non_versionnees/v2/vues/`.*

J'ai regardé moi-même les images en tuiles natives et croisé ce qu'elles montrent ; aucune fusion algorithmique.
Positions lues avec une grille de 1 m sur l'IGN 20 cm et le levé GAM en surimpression (`_travail/v2/lecture/gam_NO`,
`gam_NE`, `gam_SE`, `gam_SO`, `ign24_gam_centre`, images sans photo de tiers). Repère du site : x vers l'est, y vers le
nord, origine au point M08 (L93 917 989,78 ; 6 460 971,81).

## 1. Images lues

| Source | Date | Ce que j'en ai tiré |
|---|---|---|
| IGN BD ORTHO 20 cm, vue générale, zoom du centre, 6 lectures à grille avec le levé GAM | 09/08/2024 | îlots, passages, carrés des traversées cyclables, bordures (le levé GAM concorde avec l'ortho à ≈ 0,5 m) |
| IGN 2021, 2018, 2015, IRC 2024, Pléiades 2025 (planches de dates) | 2015 → 2025 | dessin stable depuis 2015 ; buttes plantées des îlots (IRC) |
| Plan IGN v2 (contexte) | courant | Verdun (sud-ouest / nord-est), avenue de Chamrousse (ouest), chemin de Chaumetière (sud), allée du Château |
| Planches du centre `centre_p01` à `centre_p06` (24 des 52 vues du centre) et vues natives 54c3c177_-008, 8892229b_-012, e40f8d0c, 5922e7b4, f87c4f15, 86c9e1cc_-126, 80dcf3ae_-054, 6b04ee98 | 01/05/2024 → 28/07/2026 | îlots refuges à balise J5, traversées cyclables en carrés, passages, revêtement |

## 2. La scène en une phrase

Un carrefour à feux **très ouvert** où l'avenue de Verdun, à chaussées séparées par une médiane plantée qui finit en
**nez revêtu** à chaque passage, croise en biais l'avenue de Chamrousse (qui arrive très obliquement, ses deux sens
écartés autour d'une butte plantée) et le chemin de Chaumetière ; le cœur est un grand espace d'enrobé fissuré que
traversent **en diagonale** un long passage piéton et des **traversées cyclables en carrés**, avec de **petits îlots
refuges à balise J5**.

## 3. Le centre (zone de conflit)

| Élément | Où (repère du site) | Images |
|---|---|---|
| **Nez de la médiane de Verdun nord-est** | îlot ≈ 3 m, revêtu (dessus gris, bordure basse), nez vers (8,2 ; 4,5) à ≈ 9 m du centre, jusqu'au passage (≈ 18,5-20,5 m), médiane plantée au-delà | `gam_NE` ; 54c3c177_-008, 8892229b_-012 |
| **Passage de Verdun nord-est** | deux zébras : sur les 3 voies d'entrée de (10 ; 20) à (17 ; 12), sur la sortie de (16 ; 9) à (20,5 ; 4) | `gam_NE` ; 54c3c177_-008 |
| **Nez de la médiane de Verdun sud-ouest** | îlot ≈ 2,8 m, nez vers (−12,5 ; −7,5) à ≈ 14,5 m du centre, refuge du passage vers 19-20 m | `gam_SO` ; 674d46c6_+171, 80dcf3ae_-144 |
| **Passage de Verdun sud-ouest** | zébra sur les entrées de (−22 ; −4) à (−17 ; −10), zébra sur la sortie de (−26 ; 1) à (−22 ; −1) | `gam_SO` ; f87c4f15 |
| **Long passage de Chamrousse** | ≈ 25 m **en biais**, le long du bord nord-ouest de Verdun, de (−24 ; 4) à (−5 ; 19), avec des refuges | `gam_NO` ; e40f8d0c, 674d46c6_+171 |
| **Traversées cyclables en carrés** | rangées de carrés blancs (≈ 0,5 m) le long du long passage et en travers du cœur, de (−20 ; 0) vers (−5 ; 12) | `gam_NO` ; 674d46c6_+171, 208a1f46_-158, 02b1aad4_-049, a7bf442e_-122 |
| **Petits îlots refuges du cœur** | îlots de ≈ 1,5-2 m bordés bas, gravillons, **balise J5**, vers (−13 ; 13), (−5,5 ; 10,5) et (−18 ; 2) | `gam_NO` (bordures fermées) ; 208a1f46_-076, a7bf442e_-122, 02b1aad4_-014 |
| **Chamrousse** | sortie (bande cyclable) au nord, entrée au sud, écartées autour d'une butte plantée bordée de (−37 ; 4) à (−25 ; 11) | `gam_NO`, IGN 2024 ; 921c90d1 (passe 1) |
| **Chaumetière** | rue d'≈ 6 m qui s'évase à ≈ 13 m au débouché ; zébra de (−3 ; −17) à (10 ; −9), petit îlot allongé vers (0 ; −11,5) côté cœur | `gam_SE` ; 6b04ee98, 80dcf3ae_-054 |
| **Angles** | sud-est (Verdun NE / Chaumetière) : îlot planté bordé de (10 ; −7) à (17 ; 0) ; nord-ouest : butte en goutte (2 à 10 ; 16 à 23) avec la piste autour | `gam_SE`, `gam_NE` |
| **Revêtement** | enrobé ancien fissuré à pontages, marquages moyens | 5922e7b4, e40f8d0c, 80dcf3ae_-054 |

## 4. Contradictions et comment je les ai tranchées

| Contradiction | Tranchée ainsi |
|---|---|
| Modèle de la passe 1 : aucun îlot dans le carrefour (les médianes s'arrêtaient avant la zone de conflit) / ortho et photos : nez revêtus jusqu'aux passages | les médianes vont jusqu'aux passages et portent le refuge (itération v2-1) |
| Passage de Chaumetière du modèle ≈ 4 m plus loin que le zébra réel | retrait de 0,6 m (zébra réel à 12-15 m du centre) |
| Photos de 2019 et 2022 (HF) : mêmes îlots, marquages plus nets | état géométrique stable |

## 5. Ce qui reste incertain

- La zone de conflit réelle est plus petite que celle du modèle : le nez nord-est est à ≈ 9 m du centre, la frontière
  calculée à 15 m ; le cœur réel est découpé par les carrés cyclables et les refuges.
- Le revêtement exact des nez (béton ou enrobé) : gris clair sur les photos, pris « béton ».
- L'affectation des voies de Chamrousse à la ligne de feux (photos lointaines).

## 6. Ce que la description en tire

Itération v2-1 : médianes de Verdun nord-est et sud-ouest revêtues depuis ≈ 26 m jusqu'au cœur (îlots portés par le
profil, refuges des passages) ; liaison revêtue nord-est réduite à 3 m (la bande plantée reste derrière) ; passage de
Chaumetière en retrait de 0,6 m. Le long passage en biais, les traversées en carrés, les petits refuges à J5 et la
forme de chaussées séparées qui se croisent restent hors format (`BESOINS.md`).
