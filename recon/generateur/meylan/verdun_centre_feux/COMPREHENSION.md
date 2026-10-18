# Avenue de Verdun × chemin des Buclos (M17) — compréhension de la scène (passe v2)

*`recon/generateur/meylan/verdun_centre_feux/COMPREHENSION.md` — 18/10/2026, étape 3, passe v2 du lot « carrefours ».
État décrit : **28/07/2026** ; fenêtre d'état des photos depuis le 01/06/2025 (25 photos à plat du 31/08/2025 et du
28/07/2026), complétée de 25 photos antérieures « hors fenêtre » (360° du 01/05/2024 et du 18/05/2025, Mapillary
2019-2023). Aucune photo n'est versionnée : vues sous `recon/out/generateur/meylan_verdun_centre_feux/comparaison/
meylan_verdun_centre_feux/photos_non_versionnees/v2/vues/`.*

J'ai regardé moi-même les images en tuiles natives et croisé ce qu'elles montrent ; aucune fusion algorithmique.
Positions lues avec une grille de 1 m sur l'IGN 20 cm et le levé GAM en surimpression, le modèle compilé tracé
par-dessus (`recon/out/generateur/meylan_verdun_centre_feux/_travail/v2/lecture/ign24_gam_centre`, `modele_gam_S`,
`modele_gam_N`, `modele_v2_1` ; images sans photo de tiers). Repère du site : x vers l'est, y vers le nord, origine au
passage à feux (L93 917 676,06 ; 6 460 690,07).

## 1. Images lues

| Source | Date | Ce que j'en ai tiré |
|---|---|---|
| IGN BD ORTHO 20 cm, zoom du centre, lectures à grille avec le levé GAM et le modèle | 09/08/2024 | baïonnette, îlots du passage, zébras, bandes vertes, angles plantés |
| IGN 2021, 2018, 2015, IRC 2024, Pléiades 2025 (planches de dates) | 2015 → 2025 | dessin stable ; bandes vertes de traversée cyclable visibles depuis 2021 |
| Plan IGN v2 (contexte) | courant | chemin des Buclos au nord-ouest (vers le chemin de Chaumetière) et au sud-est ; allée de la Faculté plus au nord-est |
| Vues natives 2b9bed48_-011, 2b9bed48_+155, 5ac41175_-015 (18/05/2025, HF), 3fc24f3e, de22683a (28/07/2026) | 2025-2026 | îlot refuge en D, bande verte + zébra, ligne de cédez de Buclos nord, traversée de la Chronovélo, zone hachurée à chevrons |

## 2. La scène en une phrase

Une avenue de Verdun en 2 × 1 voies séparées par une **zone hachurée** de ≈ 3,7 m, coupée en **baïonnette** par le
chemin des Buclos (sortie vers le sud-est, débouché en cédez au nord-ouest), avec entre les deux un **passage piéton à
feux doublé d'une bande verte cyclable** qui traverse la médiane sur **deux îlots refuges en D** (gravillons, panneau
de contournement), et la Chronovélo qui longe le côté nord-ouest et traverse Buclos nord.

## 3. Le centre (les deux T et le passage)

| Élément | Où (repère du site) | Images |
|---|---|---|
| **Passage à feux** | zébra de ≈ 3-4 m sur les deux voies, vers (−1 ; 0) → (3 ; −4) et (−5 ; 4) → (−1 ; 0), précédé côté sud-ouest d'une **bande verte de traversée cyclable** | `ign24_gam_centre` ; 2b9bed48_-011 (2025) ; de22683a (2026) |
| **Îlots refuges** | deux îlots en D bordés, gravillons, B21 « contournement », de part et d'autre du passage dans la zone hachurée : vers (−5 à −2 ; −6 à −2) et (0 à 3 ; 1 à 5) | `modele_gam_S` (bordures GAM fermées) ; 2b9bed48_-011 ; de22683a |
| **Zone hachurée de la médiane** | ≈ 3,7 m, chevrons, de part et d'autre des îlots ; au nord-est, une voie de tourne-à-gauche naît au nez de l'îlot | 5ac41175_-015 ; de22683a ; f252d62f |
| **T de Buclos sud** | sortie à sens unique vers le sud-est, embouchure évasée entre deux angles plantés ; zébra ≈ 6 m dans la rue, vers (4 à 7 ; −12 à −16) | `modele_gam_S` ; 3fc24f3e (vue depuis Buclos sud vers le carrefour) |
| **T de Buclos nord** | débouché en cédez (AB3a), ligne de cédez au bord de Verdun ; la Chronovélo et le trottoir le traversent quelques mètres plus loin (zébra + bande verte) | `modele_gam_N` ; 2b9bed48_+155 (2025) |
| **Côtés** | nord-ouest : bande enherbée, Chronovélo, trottoir ; sud-est : bande enherbée, piste mixte ; angles plantés aux quatre coins des T | IGN 2024 ; de22683a ; 3fc24f3e |

## 4. Contradictions et comment je les ai tranchées

| Contradiction | Tranchée ainsi |
|---|---|
| Passages de Buclos (passe 1, retrait par défaut) : ≈ 2 à 4 m plus près de Verdun que les zébras réels | retraits dits : 6 m (sud), 4 m (nord) |
| Photos du 31/08/2025 (fenêtre) mal positionnées par leur GNSS (passe 1) / 360° de 2024-2025 (HF) bien placées | géométrie lue sur l'ortho 2024 et les 360° ; voirie identique sur toutes les dates |

## 5. Ce qui reste incertain

- Le régime exact du T sud (sortie seule, aucun panneau lisible à l'entrée de Verdun).
- La largeur des îlots en D (≈ 3 m dans la médiane de 3,7 m ?).

## 6. Ce que la description en tire

Itération v2-1 : retraits des passages de Buclos (6 et 4 m). Le passage à feux, les îlots refuges et la zone hachurée
étaient déjà justes en plan à ≈ 1 m (décrits en passe 1). Restent hors format (`BESOINS.md`) : la baïonnette (C1), le
côté continu des T (C2), la bande verte cyclable (G4), les îlots en D (îlot refuge de forme dite).
