# Solveur de cohérence v3 : « l'objet est-il là, et les photos le confirment-elles ? »

Couche séparée, à fusionner par le composeur. Ni le paquet v1 ni la description de base v2 ne sont modifiés.
Commande : `python recon/pcg/decrire/coherence.py` (déterministe ; `--sans-planches` pour l'évaluation seule). Les planches `planches/*.jpg` et `planches/presence/*.jpg` contiennent des photos de tiers : locales, ignorées par git.

## Résumé

- Faux de la revue v2 corrigés : 6 sur 6 ; incertains : 2 traités ou signalés, 9 inchangés (Q9 hors lot ou aucune photo 2026 à moins de 25 m).
- Mesures confrontées aux photos (Q1) : 28 ; accord 12, devenues indices : 8 objets ; mesures appliquées : 16.
- Absents en 2026 non instanciés : arbre_013, arbre_015, arbre_027, arbre_028, arbre_029, arbre_175, lamp_12887274329.
- Déplacé par les travaux (Q8) : pan_AB3a_3 ; désaccords avec la fusion journalisés : 12.

## Ce qui change par rapport à la v2 (revue adverse v2, Q1 à Q8)

- **Q1, accord image automatique** : chaque mesure candidate et chaque candidat de la résolution (> 0,3 m) est confronté aux photos décisives de sa planche : axe vertical détecté entre le pied et la hauteur de l'objet (contraste de barre à deux flancs, 70e centile de la bande, la structure doit descendre jusqu'au pied), résidus r(A), r(X) en σ de la pose ; accord exigé sur ≥ 2 photos avec Σr²(X) < Σr²(A) et sans vote majoritaire pour A ; sinon la mesure devient un indice et l'objet reste en A (ou seule la composante latérale observée s'applique). Mesures : {'accord': 12, 'accord_insuffisant': 3, 'contradictoire': 1, 'desaccord': 4, 'non_testable': 8} ; devenues indices : feu_NE_TPC, feu_REV_droite, lamp_9514828517, lamp_9665416717, pan_B6a1_1, pan_C114_1, pan_C13a_1, poteau_bois_REV_ilot. Candidats : {'accord_insuffisant': 1, 'non_testable': 18}. Résidus imprimés sur chaque planche (pied de vignette) et dans `verifications_image.json`.
- **Q2, décisivité locale des poses** : une photo n'est décisive pour un objet que si ≥ 2 éléments levés (arêtes de bordure GAM 2026 ou PCRS hors tronçons refaits, marquages GAM ; avant les travaux, seulement les éléments non modifiés) à moins de 15 m de l'objet et à ±30° de son azimut se reprojettent à moins de 2σ (profil moyen du gradient le long de la normale image). 213 validations sur 355 couples photo-objet ; 80 sans assez d'éléments dans le secteur. σ_rot gonflé (×(1 + 3 − n)) pour les poses à moins de 3 secteurs de 45° : pnx:00c1ba9a, pnx:6e97bb8c, pnx:79a18815, pnx:aa9d7e12, pnx:e540bf1d, pnx:f8d91bb1. Une cohérence multi-vues complète le test : une photo hors du consensus des axes (≥ 3 photos) est écartée pour l'objet. Les portes P2 utilisent cette décisivité locale.
- **Q3, verdicts d'existence de la fusion** (`enrichi/entites_verifiees.json`) : absent_2026 -> non_instancie_absent_2026, retirer -> a_retirer (hors contrôle des marquages), absent_2026_a_verifier -> drapeau. Objets : {'non_instancie_absent_2026': 3} ; marquages hors contrôle : 28 ; à vérifier : ML-0222, ML-5341, ML-5342, ML-5343. Désaccords journalisés dans `conflits_fusion.json` : {'absence_constatee_par_la_coherence': 4, 'hypothese_fusion_confirmee_q1': 2, 'mesure_fusion_non_retenue': 4, 'retrait_fusion_contre_leve_gam_2026': 2}.
- **Q4, présence 2026** : 27 objets à moins de 25 m d'une photo calée de 2026, chacun avec ses vignettes (`planches/presence/`), un test automatique (structure verticale ; végétation et tronc pour un arbre) et une entrée de revue obligatoire (`revue_coherence.json`, presence_2026) : 27 revus, absents : arbre_013, arbre_015, arbre_027, arbre_028, arbre_029, lamp_12887274329. Le test automatique seul est trop faible pour conclure (végétation du fond) : {'indetermine': 7, 'present': 20}.
- **Q5, flèches** : contraste de la tête seule (tige exclue) ; flèche douteuse si la tige est à moins de 0,10 m de l'axe d'une ligne longitudinale ou le pied à moins de 0,5 m d'une limite de voie OpenDRIVE ; toute limite qui coupe la boîte donne voie_coupee (jamais de recalage) ; aucun recalage dont le résultat n'est pas entièrement roulable ; répétitions INF-FLE-004 glissées en s (voie ≥ boîte + 2 × 0,3 m) ou supprimées. Comptes : {'a_retirer': 1, 'conflit_surface_marquage': 1, 'conforme': 6, 'garde_par_ortho': 2, 'glissement_s_propose': 1, 'leve_ecart_garde': 4, 'recalage_propose': 6, 'voie_coupee': 1, 'voie_non_bornee': 4}.
- **Q6, σ des mesures** : covariance anisotrope tirée de la dispersion réelle des résidus photo (triangulation mixte, axes observés par Q1), plancher d·σ_pose en travers et d·σ_pose / sin(angle) en profondeur (infinie sous 15°) ; σ saisis sous le plancher refusés : lamp_9514828431, lamp_9514828517, lamp_9665416817, pan_AB3a_2, pan_AB3a_3, pan_AB4_2, pan_B6a1_1, pan_C13a_1, poteau_reseau_12888048898. Une mesure compatible dont la profondeur n'est pas observée garde la profondeur de la source.
- **Q7, nature des mesures** : pixel_ortho seulement pour les objets au sol ; un mât exige un départ d'ombre corroboré (deux lectures indépendantes) ou une triangulation photo, tous soumis à Q1. Mesures ramenées à des indices : pan_AB3a_2.
- **Q8, budget et compatibilité** : le budget de la source d'origine est gardé (dépassements signalés : pan_AB3a_3) et chaque mesure est testée contre sa source (Mahalanobis ≤ 3) : {'compatible': 18, 'deplace_par_travaux': 1} ; {'pan_AB3a_3': 'deplace_par_travaux'}. Statut 2026 mis à jour pour les objets déplacés par les travaux.
- **Q10 (défauts cités)** : relèvement moyen par moyenne circulaire (atan2 de la somme des vecteurs) dans la porte P2 ; en-tête des planches au statut de résolution final ; chaque affirmation chiffrée de la revue passe par Q1 (une revue « corrigée » contredite par les photos est refusée).

## Recontrôle des 6 faux et des 11 incertains de la revue v2

Faux corrigés : 6 sur 6. Détail calculé par le solveur (statut et tests de cette exécution) :

| revue v2 | objet | constat de la revue | nouvel état v3 | statut |
|---|---|---|---|---|
| faux | `lamp_9665416717` | mesure fusion « pixel_ortho » appliquée (0,88 m) ; les 5 photos décisives placent le fût près de A | corrigé : reste en A (mesure ramenée à un indice) | conforme_signale |
| faux | `arbre_027` | « existant inchangé » alors qu'il est absent sur les 3 photos calées de 2026 | corrigé : non instancié (absent 2026) | non_instancie_absent_2026 |
| faux | `arbre_028` | « existant inchangé » alors qu'il est absent sur les 3 photos calées de 2026 | corrigé : non instancié (absent 2026) | non_instancie_absent_2026 |
| faux | `MF-0286` | tiret de la ligne axiale gardé « par l'ortho » ; la fusion le déclare « retirer » | corrigé : à retirer (verdict de la fusion appliqué) | a_retirer |
| faux | `MF-0774` | recalage proposé alors que la flèche et son recalage sont sur le trottoir | corrigé : conflit surface / marquage, aucun recalage | conflit_surface_marquage |
| faux | `MF-8000` | recalage poussant la flèche sur la bordure K-0415 (ignorée par le filtre |x| > 0,3 m) | corrigé : glissement en s proposé | glissement_s_propose |
| incertain | `pan_AB3a_2` | position non prouvée (3 vues du SO dispersées de +0,37 à −1,0 m, mly:1207034570953803 fausse localement, σ_travers 0,06 m intenable) | partiellement corrigé : la mesure de la revue n'est plus appliquée (Q6, Q7) ; position par la règle, confiance faible ; azimut 15,5° gardé (P4) | corrige |
| incertain | `pan_D21_1` | non instancié sans hypothèse de jalonnement relocalisée (P12) | inchangé : relève de Q9 (P11 à P16), hors de ce lot ; station terrain | non_resolu |
| incertain | `pan_J5_2` | non instancié (même îlot que le D21) | inchangé : relève de Q9 (P11 à P16), hors de ce lot ; station terrain | non_resolu |
| incertain | `pan_B21a1_4` | azimut 10° -> 341,1° déduit de la voie OpenDRIVE, sans image | inchangé : relève de Q9 (P11 à P16), hors de ce lot ; station terrain | reoriente |
| incertain | `lamp_lidar_VERC_E` | 0,45 m par triangulation mixte ; deux poteaux proches, identité non établie | signalé : mesure non testable (aucune pose validée localement, Q2) -> confiance faible | mesure |
| incertain | `potelet_13827066658` | 1,90 m par la règle POT-01 ; repère (s, t) hors étendue (P14) | inchangé : relève de Q9 (P11 à P16), hors de ce lot ; station terrain | corrige |
| incertain | `portail_12462947807` | conforme sur la seule foi d'OSM ; aucun portail lisible sur l'ortho 2022 | inchangé : aucune photo calée 2026 à moins de 25 m (Q4 ne s'applique pas), aucune mesure à tester (Q1) | conforme |
| incertain | `portail_12976463291` | conforme ; OSM 2026-04 dans l'emprise des travaux, invérifiable | inchangé : aucune photo calée 2026 à moins de 25 m (Q4 ne s'applique pas), aucune mesure à tester (Q1) | conforme |
| incertain | `lamp_9514795817` | déduit 2026 ; pied d'ombre 2022 à 0,51 m le long de la bordure | inchangé : aucune photo calée 2026 à moins de 25 m (Q4 ne s'applique pas), aucune mesure à tester (Q1) | conforme |
| incertain | `barriere_levante_12462947804` | conforme au milieu d'une aire en enrobé, aucun fût visible | inchangé : aucune photo calée 2026 à moins de 25 m (Q4 ne s'applique pas), aucune mesure à tester (Q1) | conforme |
| incertain | `arbre_236` | conforme ; ortho 2022 illisible (bande d'ombre) | inchangé : aucune photo calée 2026 à moins de 25 m (Q4 ne s'applique pas), aucune mesure à tester (Q1) | conforme |

- `lamp_9665416717` : conforme_signale, déplacement 0.00 m, conf - ; Q1 sur la mesure fusion_recensement_0.3 : desaccord (votes 0 pour la mesure, 4 pour A ; Σr² 38.04 / 10.85) ; composante latérale observée -0.04 ± 0.07 m (non significative) ; drapeaux : mesure_indice_q1
- `arbre_027` : non instancié : constat de présence 2026 (Q4) ; revue de présence : la boîte tombe sur les voitures garées puis sur la façade, aucun tronc ni houppier (10,1 à 12,7 m) ; l'arbre de 2022 a disparu (revue adverse v2)
- `arbre_028` : non instancié : constat de présence 2026 (Q4) ; revue de présence : pelouse sèche nue devant la façade, aucun arbre (7,5 à 13,7 m) ; arbre_026 voisin présent exactement sur son point (revue adverse v2)
- `MF-0286` : verdict d'existence de la fusion (retirer, ORTHO-B-102) : hors contrôle des marquages (Q3) ; le test Q5 la juge aussi douteuse : tige à 0.03 m de l'axe de la ligne ML-6232 ; pied à 0.02 m d'une limite de la voie OpenDRIVE 5/1
- `MF-0774` : aucun recalage : recalage refusé : le résultat n'est pas entièrement roulable (0 % roulable) ; position actuelle 0 % roulable : conflit surface / marquage à arbitrer (Q5)
- `MF-8000` : glissement de -11.0 m en s, voie de 2.569 m après glissement, entièrement roulable ; limites dans la boîte avant : bordure K-0415 (x +0.46)
- `pan_AB3a_2` : corrige, déplacement 0.70 m, conf faible ; Q7 : rayon photo borné par une règle : pas une triangulation (mât, Q7) ; Q6 : σ saisi refusé (0.06 m < plancher 0.26 m; 0.25 m < plancher 100.00 m) ; Q1 sur le candidat de la résolution : accord_insuffisant ; azimut 342.0 -> 15.5° (reoriente) ; drapeaux : candidat_accord_insuffisant_q1, mesure_indice_q7, revue_non_probante_geometrie
- `pan_D21_1` : non_resolu, déplacement 0.00 m, conf faible ; azimut 225.0 -> 225.0° (orientation_signalee) ; drapeaux : a_verifier_terrain2026, obsolete_probable
- `pan_J5_2` : non_resolu, déplacement 0.00 m, conf faible ; drapeaux : a_verifier_terrain2026, obsolete_probable, surface_modifiee_2025
- `pan_B21a1_4` : reoriente, déplacement 0.00 m, conf faible ; azimut 10.0 -> 341.1° (reoriente)
- `lamp_lidar_VERC_E` : mesure, déplacement 0.45 m, conf faible ; Q1 sur la mesure triangulation_mixte : non_testable (votes 0 pour la mesure, 0 pour A ; Σr² 0 / 0) ; drapeaux : mesure_non_testee_q1
- `potelet_13827066658` : corrige, déplacement 1.90 m, conf faible ; Q1 sur le candidat de la résolution : non_testable ; drapeaux : a_verifier_terrain2026, candidat_non_teste_q1
- `portail_12462947807` : conforme, déplacement 0.00 m, conf -
- `portail_12976463291` : conforme, déplacement 0.00 m, conf -
- `lamp_9514795817` : conforme, déplacement 0.00 m, conf -
- `barriere_levante_12462947804` : conforme, déplacement 0.00 m, conf -
- `arbre_236` : conforme, déplacement 0.00 m, conf -

## Vérifications image (Q1) : mesures

| objet | mesure | nature | verdict | photos sur la mesure | votes mesure / A | Σr² mesure / A | statut |
|---|---|---|---|---|---|---|---|
| `armoire_1313238971` | fusion_recensement_0.3 | pixel_ortho | non_testable | 0 | 0 / 0 | 0 / 0 | hypothese |
| `feu_NE_TPC` | triangulation_mixte | triangulation_photos | desaccord | 8 | 0 / 1 | 12.18 / 5.94 | indice |
| `feu_NE_droite` | triangulation_mixte | triangulation_photos | accord | 9 | 1 / 0 | 12.88 / 24.78 | probante |
| `feu_REV_E_pietons` | triangulation_mixte | triangulation_photos | accord | 9 | 0 / 0 | 1.33 / 6.12 | probante |
| `feu_REV_droite` | triangulation_mixte | triangulation_photos | accord | 3 | 1 / 0 | 2.07 / 20.46 | probante |
| `feu_REV_droite` | ombre_ortho | ombre_detecteur | contradictoire | 1 | 1 / 1 | 12.84 / 11.46 | indice |
| `feu_VERC_droite` | triangulation_mixte | triangulation_photos | non_testable | 0 | 0 / 0 | 0 / 0 | probante |
| `lamp_12668578865` | revue_coherence | lecture_ombre | non_testable | 0 | 0 / 0 | 0 / 0 | probante |
| `lamp_12668620636` | fusion_recensement_0.3 | pixel_ortho | non_testable | 0 | 0 / 0 | 0 / 0 | probante |
| `lamp_9514825221` | revue_coherence | lecture_ombre | non_testable | 0 | 0 / 0 | 0 / 0 | probante |
| `lamp_9514828431` | fusion_recensement_0.3 | triangulation_photos | accord | 2 | 1 / 0 | 0.15 / 10.42 | hypothese |
| `lamp_9514828517` | fusion_recensement_0.3 | triangulation_photos | accord_insuffisant | 1 | 0 / 0 | 0.0 / 0.14 | indice |
| `lamp_9665416717` | fusion_recensement_0.3 | pixel_ortho | desaccord | 1 | 0 / 4 | 38.04 / 10.85 | indice |
| `lamp_9665416817` | fusion_recensement_0.3 | triangulation_photos | accord | 8 | 5 / 0 | 7.3 / 53.68 | probante |
| `lamp_lidar_VERC_E` | triangulation_mixte | triangulation_photos | non_testable | 0 | 0 / 0 | 0 / 0 | probante |
| `mat_camera_9831317323` | revue_coherence | lecture_ombre | non_testable | 0 | 0 / 0 | 0 / 0 | probante |
| `pan_AB3a_1` | triangulation_mixte | triangulation_photos | accord | 5 | 2 / 0 | 3.0 / 13.96 | probante |
| `pan_AB3a_3` | fusion_recensement_0.3 | triangulation_photos | accord | 2 | 2 / 1 | 9.1 / 20.25 | probante |
| `pan_AB4_2` | fusion_recensement_0.3 | triangulation_photos | accord | 2 | 2 / 1 | 9.11 / 21.35 | probante |
| `pan_B6a1_1` | fusion_recensement_0.3 | triangulation_photos | accord_insuffisant | 1 | 0 / 0 | 0.0 / 0.07 | indice |
| `pan_C113_1` | triangulation_mixte | triangulation_photos | accord | 9 | 0 / 0 | 1.74 / 13.7 | probante |
| `pan_C114_1` | triangulation_mixte | triangulation_photos | desaccord | 3 | 0 / 1 | 11.0 / 13.86 | indice |
| `pan_C13a_1` | fusion_recensement_0.3 | triangulation_photos | accord_insuffisant | 1 | 0 / 0 | 0.0 / 0.07 | indice |
| `pan_J5_1` | revue_coherence | triangulation_photos | accord | 7 | 5 / 0 | 28.67 / 33.77 | probante |
| `poteau_bois_NE` | triangulation_mixte | triangulation_photos | accord | 3 | 0 / 0 | 1.75 / 1.83 | probante |
| `poteau_bois_REV_ilot` | triangulation_mixte | triangulation_photos | desaccord | 5 | 0 / 0 | 6.81 / 2.91 | indice |
| `poteau_reseau_12888048898` | fusion_recensement_0.3 | triangulation_photos | accord | 2 | 1 / 0 | 0.16 / 18.0 | hypothese |
| `potelet_12462947806` | fusion_recensement_0.3 | pixel_ortho | non_testable | 0 | 0 / 0 | 0 / 0 | hypothese |

**Candidats de la résolution (C contre l'a priori)** : `abri_NO_0021` non_testable; `arbre_093` non_testable; `arbre_110` non_testable; `arbre_173` non_testable; `arbre_181` non_testable; `arbre_196` non_testable; `arbre_308` non_testable; `arbre_396` non_testable; `arbre_413` non_testable; `feu_SW_NO_pietons` non_testable; `feu_VERC_ilot` non_testable; `lamp_9514795519` non_testable; `pan_AB3a_2` accord_insuffisant; `portail_13827066643` non_testable; `poteau_incendie_9577881491` non_testable; `poteau_reseau_13624544994` non_testable; `potelet_13827066657` non_testable; `potelet_13827066658` non_testable; `stationnement_velos_10265340447` non_testable.

## Présence 2026 (Q4)

| objet | type | auto | revue | photos | note |
|---|---|---|---|---|---|
| `arbre_004` | arbre | present | **present** | 00c1ba9a | arbre à feuillage persistant dense, tronc dans la boîte (22,9 m) |
| `arbre_005` | arbre | present | **present** | 00c1ba9a, ded07efa, f8d91bb1 | même type d'arbre, tronc dans la boîte sur les 3 vues |
| `arbre_006` | arbre | present | **present** | ded07efa, f8d91bb1 | feuillu à houppier clair, tronc fin dans la boîte |
| `arbre_013` | arbre | indetermine | **absent** | 00c1ba9a, ded07efa, f8d91bb1 | pelouse sèche nue devant la façade et la rampe de garage, aucun tronc ni houppier dans la boîte (4,9 à 13,4 m) ; concorde avec la fusion (PANO2026-026) |
| `arbre_014` | arbre | present | **present** | 00c1ba9a, ded07efa, f8d91bb1 | petit arbre ou arbuste en cépée (≈ 2,5 m) exactement dans la boîte sur les 3 vues |
| `arbre_015` | arbre | present | **absent** | 00c1ba9a, ded07efa, f8d91bb1 | sol nu entre la haie et le candélabre lamp_9514828517, aucun arbre dans la boîte (5,9 à 10,2 m) ; concorde avec la fusion (PANO2026-027) |
| `arbre_016` | arbre | present | **present** | 00c1ba9a, ded07efa, f8d91bb1 | jeune arbre à tronc fin dans la boîte, à côté du candélabre |
| `arbre_017` | arbre | present | **present** | 00c1ba9a, ded07efa, f8d91bb1 | arbre à tronc fin dans la boîte (ded07efa, f8d91bb1) ; depuis 00c1ba9a la visée longe un candélabre |
| `arbre_025` | arbre | present | **present** | 00c1ba9a, ded07efa, f8d91bb1 | grand arbre à houppier rond ; tronc dans la boîte depuis ded07efa et f8d91bb1 |
| `arbre_026` | arbre | present | **present** | 00c1ba9a, ded07efa, f8d91bb1 | grand tilleul : la boîte tombe dans le tronc sur les 3 vues (poses validées sur cet arbre) |
| `arbre_027` | arbre | present | **absent** | 00c1ba9a, ded07efa, f8d91bb1 | la boîte tombe sur les voitures garées puis sur la façade, aucun tronc ni houppier (10,1 à 12,7 m) ; l'arbre de 2022 a disparu (revue adverse v2) |
| `arbre_028` | arbre | present | **absent** | 00c1ba9a, ded07efa, f8d91bb1 | pelouse sèche nue devant la façade, aucun arbre (7,5 à 13,7 m) ; arbre_026 voisin présent exactement sur son point (revue adverse v2) |
| `arbre_029` | arbre | indetermine | **absent** | 00c1ba9a, ded07efa, f8d91bb1 | souche coupée au ras du sol visible dans la boîte sur ded07efa (6,6 m) et f8d91bb1 (10,5 m) : arbre abattu |
| `arbre_049` | arbre | present | **present** | ded07efa, f8d91bb1 | pin à tronc élancé dans la boîte (≈ 21-25 m) |
| `arbre_050` | arbre | indetermine | **present** | ded07efa, f8d91bb1 | feuillu élancé dans la boîte (≈ 24-28 m) |
| `barriere_levante_3375058657` | barriere_levante | present | **non_visible** | 00c1ba9a | masquée par une voiture garée ; seule vue à 22,7 m |
| `boite_aux_lettres_12887274328` | boite_aux_lettres | indetermine | **non_visible** | 00c1ba9a, ded07efa, f8d91bb1 | masquée par les voitures garées sur les 3 vues |
| `lamp_12887274329` | lampadaire | indetermine | **absent** | 00c1ba9a, ded07efa, f8d91bb1 | aucun mât dans la boîte ni à ±2 m sur les 3 vues (façade et ciel visibles derrière, jusqu'à 7 m de haut) ; un luminaire mural reste possible : à vérifier sur place (OSM 2026-02) |
| `lamp_9514828418` | lampadaire | present | **present** | 00c1ba9a | mât de candélabre sur la visée (23,2 m) |
| `lamp_9514828431` | lampadaire | present | **present** | ded07efa, f8d91bb1 | mât de candélabre sur la visée (20-21 m) |
| `lamp_9514828517` | lampadaire | present | **present** | 00c1ba9a, ded07efa | grand candélabre portant les plaques B6a1 et C13a (7,8-8,3 m) |
| `pan_AB3a_3` | panneau | present | **present** | 00c1ba9a, ded07efa, f8d91bb1 | triangle AB3a sur son poteau, au refuge (déplacé lors des travaux) |
| `pan_AB4_2` | panneau | present | **present** | ded07efa, f8d91bb1 | STOP sur son poteau à la pointe de l'îlot herbeux |
| `pan_B6a1_1` | panneau | present | **present** | 00c1ba9a, ded07efa | plaque B6a1 sur le candélabre lamp_9514828517 |
| `pan_B6a1_2` | panneau | indetermine | **non_visible** | 00c1ba9a | position masquée par les voitures garées ; un disque B6a1 est visible ≈ 17° plus à droite devant la façade, non apparié (position de la triangulation à 2 rayons à revoir) |
| `pan_C13a_1` | panneau | present | **present** | 00c1ba9a, ded07efa | plaque sous le B6a1 sur le même candélabre |
| `stationnement_velos_13542473491` | stationnement_velos | indetermine | **non_visible** | 00c1ba9a | masqué par les voitures garées (21,4 m) |

## Désaccords avec la fusion (Q3, `conflits_fusion.json`)

- `ML-5141` (retrait_fusion_contre_leve_gam_2026) : verdict de la fusion appliqué au contrôle (hors contrôle) ; le levé GAM 2026 le contredit avec une preuve antérieure aux travaux : à arbitrer (terrain) — fusion : {'existence': 'retirer', 'obs': ['MLY-MAR-011'], 'date': '2024-08-24'} — cohérence : {'source': 'levé GAM 2026', 'etat': 'conserve'}
- `MZ-5002` (retrait_fusion_contre_leve_gam_2026) : verdict de la fusion appliqué au contrôle (hors contrôle) ; le levé GAM 2026 le contredit avec une preuve antérieure aux travaux : à arbitrer (terrain) — fusion : {'existence': 'retirer', 'obs': ['MLY-CON-017'], 'date': '2024-08-24'} — cohérence : {'source': 'levé GAM 2026', 'etat': 'conserve'}
- `arbre_027` (absence_constatee_par_la_coherence) : non instancié (non_instancie_absent_2026) ; constat à reporter dans la fusion (arbitrages_fusion.json, action constat_revue) — cohérence : {'presence': 'absent', 'photos': ['pnx:00c1ba9a', 'pnx:ded07efa', 'pnx:f8d91bb1'], 'note': "la boîte tombe sur les voitures garées puis sur la façade, aucun tronc ni houppier (10,1 à 12,7 m) ; l'arbre de 2022 a disparu (revue adverse v2)"}
- `arbre_028` (absence_constatee_par_la_coherence) : non instancié (non_instancie_absent_2026) ; constat à reporter dans la fusion (arbitrages_fusion.json, action constat_revue) — fusion : {'existence': 'non_verifie', 'statut': 'indice_seulement', 'obs': [], 'date': '2024-08-24'} — cohérence : {'presence': 'absent', 'photos': ['pnx:00c1ba9a', 'pnx:ded07efa', 'pnx:f8d91bb1'], 'note': 'pelouse sèche nue devant la façade, aucun arbre (7,5 à 13,7 m) ; arbre_026 voisin présent exactement sur son point (revue adverse v2)'}
- `arbre_029` (absence_constatee_par_la_coherence) : non instancié (non_instancie_absent_2026) ; constat à reporter dans la fusion (arbitrages_fusion.json, action constat_revue) — fusion : {'existence': 'present', 'statut': 'confirme', 'obs': ['PANO2026-031'], 'date': '2026-07-28'} — cohérence : {'presence': 'absent', 'photos': ['pnx:00c1ba9a', 'pnx:ded07efa', 'pnx:f8d91bb1'], 'note': 'souche coupée au ras du sol visible dans la boîte sur ded07efa (6,6 m) et f8d91bb1 (10,5 m) : arbre abattu'}
- `lamp_12887274329` (absence_constatee_par_la_coherence) : non instancié (non_instancie_absent_2026) ; constat à reporter dans la fusion (arbitrages_fusion.json, action constat_revue) — cohérence : {'presence': 'absent', 'photos': ['pnx:00c1ba9a', 'pnx:ded07efa', 'pnx:f8d91bb1'], 'note': "aucun mât dans la boîte ni à ±2 m sur les 3 vues (façade et ciel visibles derrière, jusqu'à 7 m de haut) ; un luminaire mural reste possible : à vérifier sur place (OSM 2026-02)"}
- `lamp_9514828431` (hypothese_fusion_confirmee_q1) : non appliquée par la cohérence (hypothèse de la fusion) ; les photos décisives la confirment : la fusion peut la passer en « appliquer » — fusion : {'decision': 'revue_requise', 'xy': [34.77, -141.19], 'methode': 'triangulation', 'obs': ['PANO2026-019']} — cohérence : {'q1': 'accord', 'votes_X': ['pnx:ded07efa'], 'photos': ['pnx:ded07efa', 'pnx:f8d91bb1']}
- `lamp_9514828517` (mesure_fusion_non_retenue) : mesure gardée comme indice ; l'objet reste à sa position (ou composante latérale observée) — fusion : {'decision': 'appliquer', 'xy': [13.25, -140.34], 'methode': 'triangulation', 'obs': ['PANO2026-018']} — cohérence : {'motif': 'Q1 : accord_insuffisant avec les photos décisives de la planche', 'q1': 'accord_insuffisant', 'votes_A': [], 'votes_X': []}
- `lamp_9665416717` (mesure_fusion_non_retenue) : mesure gardée comme indice ; l'objet reste à sa position (ou composante latérale observée) — fusion : {'decision': 'appliquer', 'xy': [45.57, 51.94], 'methode': 'pixel_ortho', 'obs': ['ORTHO_A-0167']} — cohérence : {'motif': 'Q1 : desaccord avec les photos décisives de la planche', 'q1': 'desaccord', 'votes_A': ['pnx:79a18815', 'pnx:e86aa913', 'pnx:7651c539', 'pnx:eeb2f8f1'], 'votes_X': []}
- `pan_B6a1_1` (mesure_fusion_non_retenue) : mesure gardée comme indice ; l'objet reste à sa position (ou composante latérale observée) — fusion : {'decision': 'appliquer', 'xy': [13.25, -140.34], 'methode': 'triangulation', 'obs': ['PANO2026-018']} — cohérence : {'motif': 'Q1 : accord_insuffisant avec les photos décisives de la planche', 'q1': 'accord_insuffisant', 'votes_A': [], 'votes_X': []}
- `pan_C13a_1` (mesure_fusion_non_retenue) : mesure gardée comme indice ; l'objet reste à sa position (ou composante latérale observée) — fusion : {'decision': 'appliquer', 'xy': [13.25, -140.34], 'methode': 'triangulation', 'obs': ['PANO2026-018']} — cohérence : {'motif': 'Q1 : accord_insuffisant avec les photos décisives de la planche', 'q1': 'accord_insuffisant', 'votes_A': [], 'votes_X': []}
- `poteau_reseau_12888048898` (hypothese_fusion_confirmee_q1) : non appliquée par la cohérence (hypothèse de la fusion) ; les photos décisives la confirment : la fusion peut la passer en « appliquer » — fusion : {'decision': 'revue_requise', 'xy': [-19.42, 10.3], 'methode': 'triangulation', 'obs': ['pano_0-21']} — cohérence : {'q1': 'accord', 'votes_X': ['pnx:119d9094'], 'photos': ['pnx:5c0d1d39', 'pnx:119d9094']}

## Acquis de la v2 (revue adverse v1, P1 à P10)

- **P1, photos** : 48 poses calées (mapillary calee_bordures 27, mapillary calee_gcp 5 décisives, panoramax calee 1, panoramax calee 12 décisives, panoramax_2026 calee_sequence 3 décisives), dont 20 décisives par le LOO (≤ 0,5°), avant la validation locale Q2.
- **P2, porte géométrique** (décisivité locale Q2) : corrections par porte : {'complet': 3, 'lateral': 5, 'non_observable': 34, 'sans_photo': 25}.
- **P3, mesures** : 16 objets reçoivent une mesure comme nouvel a priori après Q1, Q6, Q7 et Q8.
- **P4, orientation** par raccourci des plaques ; **P5, fusions** seulement « même support » ou photo à un seul mât (propositions : {'fusion_supports': 1, 'hypothese_spec': 8, 'ilot_manquant': 3, 'supports_distincts': 1, 'surface_a_corriger': 5, 'tete_feu': 2}).
- **P6, bordures** : 512 bordures v2, 305 d'orientation forte ; incohérences voie/côté haut : 0.
- **P7, dureté** : statuts d'objets {'absent': 17, 'deduit': 14, 'existant': 572, 'projet': 17} ; règles dures violées {'BAR-03': 1, 'ECL-01': 5, 'FEU-02': 1, 'FEU-04': 3, 'FEU-07': 2, 'GEN-01': 38, 'GEN-02': 1, 'GEN-03': 4, 'GEN-09': 5, 'MOB-01': 1, 'PMR-01': 6, 'POT-01': 2, 'RES-02': 3, 'RES-03': 1, 'SIG-01': 7, 'SIG-02': 2, 'SIG-10': 1, 'SIG-12': 2, 'TC-01': 1, 'VEG-01': 21, 'VEG-02': 1, 'VEG-06': 4}.
- **P8, GEN-02** : supports piétons admis à la limite arrière de la BEV ; palier de 0,80 m majeur et conditionnel.
- **P9 / Q8, budgets** : budget de la mesure dépassé : aucun ; budget de la source d'origine dépassé : ['pan_AB3a_3'].
- **P10, ombres (PCRS 5 cm 2022-05-10)** : ombres à 334.0°, soleil à 60.68° ; validation 25 détections sur 60 essais, σ travers 0.077 m, p90 1.025 m ; une détection seule est un indice.
- **P10, ombres (IGN BD ORTHO 20 cm 2024-08-09)** : ombres à 318.5°, soleil à 54.97° ; validation 8 détections sur 60 essais, σ travers 0.253 m, p90 0.693 m ; une détection seule est un indice.

## Comptes

| verdict | objets |
|---|---|
| a_verifier | 106 |
| conforme | 453 |
| violation | 61 |

| statut de résolution | objets |
|---|---|
| a_arbitrer_photo | 1 |
| anomalie_surface | 19 |
| conforme | 482 |
| conforme_signale | 53 |
| corrige | 33 |
| mesure | 8 |
| non_instancie_absent_2026 | 17 |
| non_resolu | 3 |
| reoriente | 4 |

| type | conforme | a_verifier | violation |
|---|---|---|---|
| abri_bus | 1 | 0 | 1 |
| arbre | 369 | 76 | 22 |
| armoire | 2 | 0 | 0 |
| balise_J11 | 2 | 0 | 0 |
| banc | 2 | 0 | 0 |
| barriere_levante | 3 | 0 | 0 |
| boite_aux_lettres | 1 | 0 | 0 |
| chicane | 1 | 0 | 0 |
| conteneur_verre | 1 | 0 | 0 |
| corbeille | 1 | 3 | 1 |
| distributeur | 1 | 1 | 0 |
| fontaine | 1 | 0 | 0 |
| lampadaire | 28 | 8 | 6 |
| mat_camera | 0 | 1 | 1 |
| mobilier_publicitaire | 2 | 0 | 0 |
| panneau | 9 | 6 | 13 |
| panneau_information | 3 | 1 | 0 |
| portail | 7 | 0 | 1 |
| poteau_arret | 2 | 1 | 0 |
| poteau_incendie | 0 | 0 | 3 |
| poteau_reseau | 4 | 2 | 2 |
| potelet | 2 | 4 | 2 |
| stationnement_velos | 7 | 1 | 1 |
| support_feux | 3 | 2 | 8 |
| totem_PR | 1 | 0 | 0 |

Têtes de feux : {'conforme': 15, 'orientation_signalee': 4, 'reoriente': 12}. Corrections : {'deplacement': 49, 'deplacement+reorientation': 4, 'non_instanciation': 11, 'reorientation': 15} (confiance : {'faible': 44, 'haute': 2, 'moyenne': 33}). Propositions : {'fusion_supports': 1, 'hypothese_spec': 8, 'ilot_manquant': 3, 'supports_distincts': 1, 'surface_a_corriger': 5, 'tete_feu': 2}.
Objets non instanciés : arbre_109, pan_D21_1, pan_D21_2, pan_J5_2.

Violations par règle (dures et signalées) : BAR-03 2, ECL-01 11, ECL-02 1, ECL-05 1, FEU-01 2, FEU-02 1, FEU-04 4, FEU-07 2, GEN-01 38, GEN-02 5, GEN-03 19, GEN-04 37, GEN-06 10, GEN-08 1, GEN-09 5, MOB-01 1, PMR-01 10, POT-01 8, RES-02 4, RES-03 3, SIG-01 7, SIG-02 6, SIG-04 10, SIG-05 2, SIG-07 1, SIG-10 2, SIG-12 3, TC-01 1, VEG-01 21, VEG-02 35, VEG-03 1, VEG-06 4.

## Les 20 décisions les plus significatives

| # | objet | décision | preuve | revue | porte P2 | planche |
|---|---|---|---|---|---|---|
| 1 | `pan_C113_1` (panneau C113) | 0.09 m (Δt 0.052, Δs -0.068) ; azimut 225.0 → 65.0° — reoriente | mesure σ 0.107 ; mesure triangulation_mixte | azimut corrigee (moyenne) | - | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_C113_1.jpg` |
| 2 | `pan_AB3a_3` (panneau AB3a) | 4.15 m (Δt 1.107, Δs 3.996) — mesure | mesure σ 0.411 ; mesure fusion_recensement_0.3 | corrigee (moyenne) | complet (3/3 photos > 3σ, 23.3°, validé +4.15 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_AB3a_3.jpg` |
| 3 | `pan_AB3a_2` (panneau AB3a) + pan_B2a_1, pan_M9_2 | 0.70 m (Δt 0.7, Δs 0.0) ; azimut 342.0 → 15.5° — corrige | panoramax_brut σ 1.5 | corrigee (faible) | non_observable (0/6 photos > 3σ, 0.0°, validé +0.00 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_AB3a_2.jpg` |
| 4 | `lamp_12668620636` (lampadaire) | 1.83 m — anomalie_surface | mesure σ 0.188 ; mesure fusion_recensement_0.3 | corrigee (moyenne) | aucune photo calée valide (preuve ortho ou règle) | `recon/out/paquet_jardin/v2/description/coherence/planches/lamp_12668620636.jpg` |
| 5 | `lamp_12668578865` (lampadaire) | 1.63 m — anomalie_surface | mesure σ 0.3 ; mesure revue_coherence | corrigee (moyenne) | aucune photo calée valide (preuve ortho ou règle) | `recon/out/paquet_jardin/v2/description/coherence/planches/lamp_12668578865.jpg` |
| 6 | `pan_J5_1` (panneau J5) | 0.93 m (Δt -0.889, Δs 0.259) — mesure | mesure σ 0.1 ; mesure revue_coherence | corrigee (moyenne) | complet (4/13 photos > 3σ, 73.4°, validé +0.93 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_J5_1.jpg` |
| 7 | `pan_AB4_2` (panneau AB4) | 0.78 m (Δt 0.084, Δs -0.775) — corrige | mesure σ 1.5 ; mesure fusion_recensement_0.3 | corrigee (faible) | lateral (2/11 photos > 3σ, 11.5°, validé -0.74 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_AB4_2.jpg` |
| 8 | `lamp_9514825221` (lampadaire) | 1.17 m (Δt 0.055, Δs -1.164) — mesure | mesure σ 0.3 ; mesure revue_coherence | corrigee (moyenne) | non_observable (0/1 photos > 3σ, 0.0°, validé +0.00 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/lamp_9514825221.jpg` |
| 9 | `lamp_12887274329` (lampadaire) | non instancié (absent_2026, q4) — non_instancie_absent_2026 | osm σ 1.0 | - (moyenne) | - | `-` |
| 10 | `pan_D21_1` (panneau D21) + pan_D21_2 | non instancié (a_verifier_terrain2026, obsolete_probable) — non_resolu | lidar2021 σ 0.15 | ambigu (faible) | - | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_D21_1.jpg` |
| 11 | `pan_J5_2` (panneau J5) | non instancié (a_verifier_terrain2026, obsolete_probable, surface_modifiee_2025) — non_resolu | constat σ 1.5 | ambigu (faible) | - | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_J5_2.jpg` |
| 12 | `mat_camera_9831317323` (mat_camera) | 1.12 m (Δt 0.697, Δs -0.872) — mesure | mesure σ 0.3 ; mesure revue_coherence | corrigee (moyenne) | non_observable (0/2 photos > 3σ, 0.0°, validé +0.00 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/mat_camera_9831317323.jpg` |
| 13 | `feu_NE_droite` (support_feux) + feu_NE_droite_t2, feu_NE_droite_t3 | 0.36 m (Δt -0.041, Δs -0.357) — mesure | mesure σ 0.12 ; mesure triangulation_mixte | - (moyenne) | non_observable (0/12 photos > 3σ, 0.0°, validé +0.00 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/feu_NE_droite.jpg` |
| 14 | `lamp_9665416817` (lampadaire) | 0.58 m (Δt 0.437, Δs -0.382) — conforme_signale | mesure σ 0.205 ; mesure fusion_recensement_0.3 | corrigee (moyenne) | complet (5/10 photos > 3σ, 18.0°, validé +0.58 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/lamp_9665416817.jpg` |
| 15 | `arbre_013` (arbre) | non instancié (absent_2026, q3) — non_instancie_absent_2026 | gam σ 0.05 | - (moyenne) | - | `-` |
| 16 | `arbre_015` (arbre) | non instancié (absent_2026, q3) — non_instancie_absent_2026 | gam σ 0.05 | - (moyenne) | - | `-` |
| 17 | `arbre_027` (arbre) | non instancié (absent_2026, q4) — non_instancie_absent_2026 | gam σ 0.05 | - (moyenne) | - | `-` |
| 18 | `arbre_028` (arbre) | non instancié (absent_2026, q4) — non_instancie_absent_2026 | gam σ 0.05 | - (moyenne) | - | `-` |
| 19 | `arbre_029` (arbre) | non instancié (absent_2026, q4) — non_instancie_absent_2026 | gam σ 0.05 | - (moyenne) | - | `-` |
| 20 | `arbre_175` (arbre) | non instancié (absent_2026, q3) — non_instancie_absent_2026 | lidar2021_couronne σ 1.0 | - (moyenne) | - | `-` |

Justifications :

1. `pan_C113_1` : mesure retenue comme nouvel a priori (P3) : triangulation_mixte, σ 0.107 m, 0.09 m de la position source ; azimut photo de la spec (65°) conforme à la règle (48°) ; couche à 225°
2. `pan_AB3a_3` : mesure retenue comme nouvel a priori (P3) : fusion_recensement_0.3, σ 0.411 m, 4.15 m de la position source ; revue photo : position corrigée confirmée, porte P2 complète (3 photos discriminantes, 23.3°) (photos 2026 calées f8d91bb1, ded07efa, 00c1ba9a : le triangle AB3a et son poteau sont exactement sur C (refuge I-0658), A ne porte rien ; porte P2 complète) ; Q8 : la mesure du 2026-07-28 est à 10.7σ de la source d'origine (position v1 (recalée de 1.51 m, source brute inconnue : budget réduit)) : objet déplacé lors des travaux 2025 (statut 2026 mis à jour)
3. `pan_AB3a_2` : candidat admissible le plus proche (normale, Δt +0.70 m, Δs +0.00 m, J 0.268) dans la limite de la preuve (panoramax_brut, d_max 3.0 m) ; revue : sa mesure est un indice (Q7 : rayon photo borné par une règle : pas une triangulation (mât, Q7)) ; position par la règle, porte P2 non observable : confiance faible (mât 2 (B2a + AB3a + panonceau « CÉDEZ LE PASSAGE ») sur le rayon commun des 3 photos calées du SO (79a18815, eeb2f8f1, mly:1207034570953803, relèvements 217,5-220,1°) ; profondeur non observable (2,6°) : bornée par la bordure K-0186 (t ≥ 0,1 m, le mât n'est pas sur la piste) et par le mât 1 qu'il masque depuis le SO) ; test ordinal n_mats = 2 (pnx:bb9c05ff, 2025-08-31) : deux fûts distincts à ≈ 25 px l'un de l'autre (≈ 0,5° à 20 m), chacun avec ses plaques ; test ordinal plaques = mât 1 : disque B2b au-dessus du disque B1 ; mât 2 : disque B2a, triangle AB3a, panonceau « CÉDEZ LE PASSAGE » (de haut en bas) (pnx:bb9c05ff, pnx:9ef861d4, 2025-08-31) : identification faite avant tout transfert (P4) ; test ordinal occultation = depuis le SO le mât 2 masque le mât 1 ; depuis le NE (bb9c05ff) le mât 1 est devant (pnx:79a18815, pnx:eeb2f8f1, pnx:bb9c05ff, 2024-08-24/2025-08-31) : le mât 1 est au NE du mât 2 sur la même visée (≈ 38°) : les dos vus depuis le SO sont ceux du mât 2 ; raccourci des plaques sur 4 vues : face à 16° (rms 8.4°, second minimum 46° à 27.8°) (P4)
4. `lamp_12668620636` : mesure retenue comme nouvel a priori (P3) : fusion_recensement_0.3, σ 0.188 m, 1.83 m de la position source ; preuve forte (mesure, σ 0.188 m) sur chaussee de classe peu sûre (d bordure None m) : îlot, refuge, fosse ou bande plantée absents des surfaces ; revue (ortho) : position corrigée confirmée (ortho 2022 : le mât est au centre de la jardinière ronde du parking, son ombre (trait vers 334° jusqu'au disque de la lanterne) part de C ; le détecteur d'ombres (O) tombe à 0,2 m ; le nœud OSM (A) est à 1,8 m dans les places. La jardinière manque aux surfaces (classe chaussée) : anomalie de surface)
5. `lamp_12668578865` : mesure retenue comme nouvel a priori (P3) : revue_coherence, σ 0.3 m, 1.63 m de la position source ; preuve forte (mesure, σ 0.3 m) sur chaussee de classe peu sûre (d bordure 13.883 m) : îlot, refuge, fosse ou bande plantée absents des surfaces ; revue (ortho) : position corrigée confirmée (ortho 2022 grille 0,25 m : l'ombre du mât (trait fin vers 334°, ombre de la lanterne au bout) s'arrête au bord du disque clair (lanterne vue de dessus) vers (−124,36 ; 119,45) ; début d'ombre possiblement masqué par le disque sur ≤ 0,3 m : pied ≈ (−124,33 ; 119,38), à 1,6 m du nœud OSM (v1 : 0,22 m de recalage + 0,45 m de la règle, dans le mauvais sens le long))
6. `pan_J5_1` : mesure retenue comme nouvel a priori (P3) : revue_coherence, σ 0.1 m, 0.93 m de la position source ; revue photo : position corrigée confirmée, porte P2 complète (4 photos discriminantes, 73.4°) (pied de la balise pointé sur 4 vues calées (9834f494, 6e97bb8c, e86aa913, e5d79de9 ; relèvements 80° à 198°) : triangulé en (17,606 ; 14,805), résidus ≤ 0,06 m ; 0,93 m de la position de la couche vers le nez du TPC (lecture v1 : Δs ≈ +0,8 à 0,9 m))
7. `pan_AB4_2` : mesure retenue comme nouvel a priori (P3) : fusion_recensement_0.3, σ 1.5 m, 0.84 m de la position source ; candidat admissible le plus proche (normale, Δt -0.25 m, Δs +0.00 m, J 0.028) dans la limite de la preuve (mesure, d_max 4.5 m) ; revue photo : porte P2 latérale : 2 photo(s), angle 11.5° < 15° ; composante validée -0.74 m, profondeur -0.25 m non observable ; la seule composante latérale laisse une violation (GEN-01, SIG-01) : la profondeur reste celle de la règle
8. `lamp_9514825221` : mesure retenue comme nouvel a priori (P3) : revue_coherence, σ 0.3 m, 1.17 m de la position source ; revue (ortho) : position corrigée confirmée (même mât que mat_camera_9831317323 (une seule ombre sur l'ortho 2022)) ; test ordinal n_mats = 1 (ortho:pcrs2022, 2022-05-10) : une seule ombre de mât portant lanterne et caméra
9. `lamp_12887274329` : constat de présence 2026 de la cohérence : absent (pnx:00c1ba9a, pnx:ded07efa, pnx:f8d91bb1) (Q4)
10. `pan_D21_1` : preuve antérieure aux travaux 2025 (lidar2021) ; le marquage posé en 2025 MP-0001 (traversee_cyclable, neuf_2025) passe à son emplacement et la surface 2026 y est circulée : objet probablement déposé ou déplacé par les travaux, non instancié ; test ordinal presence = présent (pnx:a83dae90, pnx:81882270, 2025-08-31) : D21 « LA REVIRÉE / Collège L. Terray » et « Commerces de LA REVIRÉE » sur leur mât, balise J5 au pied, barrières de chantier ; antérieur à la fin des travaux (05/12/2025) : ne prouve rien de l'état 2026
11. `pan_J5_2` : preuve faible, aucune position admissible dans 3.0 m : arbitrage par 5 photo(s) calée(s) ; la surface surf_0323 (chaussee) a été (re)construite en 2025 (limites:gam_bordure ; classe:plan_projet_2025+osm_2026) et l'objet n'est prouvé qu'avant les travaux : objet peut-être supprimé ; violation critique non résolue sur une surface circulée : objet non instancié (resolution.arbitrage.non_instanciation) ; sur le même îlot que pan_D21_1, pan_D21_2 (probablement supprimé par les travaux 2025) ; test ordinal presence = présent (pnx:a83dae90, pnx:81882270, 2025-08-31) : D21 « LA REVIRÉE / Collège L. Terray » et « Commerces de LA REVIRÉE » sur leur mât, balise J5 au pied, barrières de chantier ; antérieur à la fin des travaux (05/12/2025) : ne prouve rien de l'état 2026
12. `mat_camera_9831317323` : mesure retenue comme nouvel a priori (P3) : revue_coherence, σ 0.3 m, 1.12 m de la position source ; revue (ortho) : position corrigée confirmée (ortho 2022 grille 0,25 m : une seule ombre de mât, qui commence vers (19,0 ; −62,07), au bord NO des images claires (lanterne et boîtier déversés vers le SE) ; nœuds OSM du candélabre et de la caméra à ≈ 1,1 m au NNO) ; test ordinal n_mats = 1 (ortho:pcrs2022, 2022-05-10) : une seule ombre de mât portant lanterne et caméra
13. `feu_NE_droite` : mesure retenue comme nouvel a priori (P3) : triangulation_mixte, σ 0.12 m, 0.36 m de la position source
14. `lamp_9665416817` : mesure retenue comme nouvel a priori (P3) : fusion_recensement_0.3, σ 0.205 m, 0.58 m de la position source ; revue photo : position corrigée confirmée, porte P2 complète (5 photos discriminantes, 18.0°) (fût du candélabre (bannière LANDRI) exactement sur C dans les 4 vignettes (6e97bb8c, e540bf1d, 7651c539, e5d79de9) ; C = mesure de la fusion (triangulation), t = +0,44 m derrière K-0353 (lecture v1 : 0,37-0,59 m))
15. `arbre_013` : fusion : existence « absent_2026 » (PANO2026-026, 2026-07-28) (Q3)
16. `arbre_015` : fusion : existence « absent_2026 » (PANO2026-027, 2026-07-28) (Q3)
17. `arbre_027` : constat de présence 2026 de la cohérence : absent (pnx:00c1ba9a, pnx:ded07efa, pnx:f8d91bb1) (Q4)
18. `arbre_028` : constat de présence 2026 de la cohérence : absent (pnx:00c1ba9a, pnx:ded07efa, pnx:f8d91bb1) (Q4)
19. `arbre_029` : constat de présence 2026 de la cohérence : absent (pnx:00c1ba9a, pnx:ded07efa, pnx:f8d91bb1) (Q4)
20. `arbre_175` : fusion : existence « absent_2026 » (OR-V-003, 2024-08-09) (Q3)

## Tests ordinaux sur photos non calées ou orthos (P1)

- presence = troncs en retrait — objets arbre_396 — photos pnx:7a182db7 (2025-05-18) : grands peupliers penchés au-dessus de la piste, troncs plusieurs mètres en retrait (photo 360° non calée) : le sens de la correction est juste, son ampleur (1,6 m) est un minimum
- n_mats = 1 — objets mat_camera_9831317323, lamp_9514825221 — photos ortho:pcrs2022 (2022-05-10) : une seule ombre de mât portant lanterne et caméra
- n_mats = 2 — objets pan_AB3a_2, pan_B1_1 — photos pnx:bb9c05ff (2025-08-31) : deux fûts distincts à ≈ 25 px l'un de l'autre (≈ 0,5° à 20 m), chacun avec ses plaques
- plaques = mât 1 : disque B2b au-dessus du disque B1 ; mât 2 : disque B2a, triangle AB3a, panonceau « CÉDEZ LE PASSAGE » (de haut en bas) — objets pan_AB3a_2, pan_B1_1 — photos pnx:bb9c05ff, pnx:9ef861d4 (2025-08-31) : identification faite avant tout transfert (P4)
- occultation = depuis le SO le mât 2 masque le mât 1 ; depuis le NE (bb9c05ff) le mât 1 est devant — objets pan_AB3a_2, pan_B1_1 — photos pnx:79a18815, pnx:eeb2f8f1, pnx:bb9c05ff (2024-08-24/2025-08-31) : le mât 1 est au NE du mât 2 sur la même visée (≈ 38°) : les dos vus depuis le SO sont ceux du mât 2
- presence = présent — objets pan_D21_1, pan_D21_2, pan_J5_2 — photos pnx:a83dae90, pnx:81882270 (2025-08-31) : D21 « LA REVIRÉE / Collège L. Terray » et « Commerces de LA REVIRÉE » sur leur mât, balise J5 au pied, barrières de chantier ; antérieur à la fin des travaux (05/12/2025) : ne prouve rien de l'état 2026

**Raccourci des plaques (P4), `pan_AB3a_2`** : pnx:79a18815 relèvement 218.6°, w/h 1.08 / 1.1547 (dos, triangle AB3a) ; pnx:eeb2f8f1 relèvement 220.1°, w/h 1.13 / 1.1547 (dos, triangle AB3a) ; pnx:9ef861d4 relèvement 70.0°, w/h 0.53 / 1.1547 (face, triangle AB3a) ; pnx:9ef861d4 relèvement 70.0°, w/h 0.48 / 1.0 (face, disque B2a) -> raccourci des plaques sur 4 vues : face à 16° (rms 8.4°, second minimum 46° à 27.8°).

## Mesures appliquées comme a priori (P3, 16)

- `pan_AB3a_3` : 4.15 m de la position source, σ 0.411 m (fusion_recensement_0.3)
- `lamp_12668620636` : 1.83 m de la position source, σ 0.188 m (fusion_recensement_0.3)
- `lamp_12668578865` : 1.63 m de la position source, σ 0.3 m (revue_coherence)
- `lamp_9514825221` : 1.17 m de la position source, σ 0.3 m (revue_coherence)
- `mat_camera_9831317323` : 1.12 m de la position source, σ 0.3 m (revue_coherence)
- `pan_J5_1` : 0.93 m de la position source, σ 0.1 m (revue_coherence)
- `pan_AB4_2` : 0.84 m de la position source, σ 1.5 m (fusion_recensement_0.3)
- `lamp_9665416817` : 0.58 m de la position source, σ 0.205 m (fusion_recensement_0.3)
- `lamp_lidar_VERC_E` : 0.45 m de la position source, σ 0.199 m (triangulation_mixte)
- `feu_NE_droite` : 0.36 m de la position source, σ 0.12 m (triangulation_mixte)
- `pan_AB3a_1` : 0.30 m de la position source, σ 0.119 m (triangulation_mixte)
- `feu_VERC_droite` : 0.26 m de la position source, σ 0.196 m (triangulation_mixte)
- `poteau_bois_NE` : 0.18 m de la position source, σ 0.1 m (triangulation_mixte)
- `feu_REV_droite` : 0.17 m de la position source, σ 0.102 m (triangulation_mixte)
- `pan_C113_1` : 0.09 m de la position source, σ 0.107 m (triangulation_mixte)
- `feu_REV_E_pietons` : 0.07 m de la position source, σ 0.1 m (triangulation_mixte)

## Marquages : flèches centrées dans leur voie, marques dans la chaussée

Comptes : {'fleches': {'a_retirer': 1, 'conflit_surface_marquage': 1, 'conforme': 6, 'garde_par_ortho': 2, 'glissement_s_propose': 1, 'leve_ecart_garde': 4, 'recalage_propose': 6, 'voie_coupee': 1, 'voie_non_bornee': 4}, 'marques_hors_chaussee': {'exception': 18, 'raccourcissement_propose': 8, 'signalement': 18, 'translation_proposee': 1}, 'hors_controle_q3': 28, 'absent_2026_a_verifier': ['ML-0222', 'ML-5341', 'ML-5342', 'ML-5343']}. Détail : `marquages_controle.json` ; propositions : `corrections_marquages.geojson`.

| flèche | gabarit | état / source | bords de voie | décalage obs. / attendu | écart | statut |
|---|---|---|---|---|---|---|
| `MF-0286` | TD | conserve / ortho2022 | - | None / None | None | a_retirer |
| `MF-0764` | TD | neuf_2025 / plan2025 | ligne ML-5298 ; bordure K-0405 | -0.025 / 0.0 | -0.025 | conforme |
| `MF-0767` | TD_TAG | neuf_2025 / plan2025 | bordure K-0627 ; ligne ML-5297 | 0.21 / 0.275 | -0.065 | conforme |
| `MF-0769` | TD_TAD | neuf_2025 / plan2025 | bordure K-0402 ; ligne ML-0799 | -0.463 / -0.275 | -0.188 | recalage_propose |
| `MF-0774` | TD_TAD | neuf_2025 / plan2025 | bordure K-0347 ; ligne ML-0802 | -0.808 / -0.275 | -0.533 | conflit_surface_marquage |
| `MF-5042` | TD_TAG | conserve / gam | bordure K-0386 ; ligne ML-5136 | -0.091 / 0.275 | -0.366 | leve_ecart_garde |
| `MF-5043` | TD_TAD | conserve / gam | ligne ML-5136 ; ligne ML-5185 | 0.061 / -0.275 | 0.336 | leve_ecart_garde |
| `MF-5092` | TD | neuf_2025 / gam | - | None / None | None | voie_non_bornee |
| `MF-5096` | TD | neuf_2025 / gam | - | None / None | None | voie_non_bornee |
| `MF-5097` | TD | neuf_2025 / gam | - | None / None | None | voie_non_bornee |
| `MF-5109` | TD | neuf_2025 / gam | - | None / None | None | voie_non_bornee |
| `MF-5523` | TD | refait_2025_identique / gam | ligne ML-5405 ; ligne ML-5228 | 0.013 / 0.0 | 0.013 | conforme |
| `MF-5524` | TD_TAD | neuf_2025 / gam | ligne ML-5228 ; bordure K-0415 | -0.05 / -0.275 | 0.225 | leve_ecart_garde |
| `MF-5525` | TAG | neuf_2025 / gam | ligne ML-5401 ; ligne ML-5228 | 0.047 / 0.425 | -0.378 | leve_ecart_garde |
| `MF-5527` | TAG | neuf_2025 / gam | - | None / None | None | voie_coupee |
| `MF-6000` | TD_TAG | conserve / ortho2022 | ligne ML-5231 ; ligne ML-5136 | 0.051 / 0.275 | -0.224 | garde_par_ortho |
| `MF-6003` | TD_TAD | conserve / ortho2022 | ligne ML-5136 ; ligne ML-5185 | 0.027 / -0.275 | 0.302 | garde_par_ortho |
| `MF-6013` | TD_TAG | neuf_2025 / plan2025 | bordure K-0627 ; ligne ML-5297 | -0.05 / 0.275 | -0.325 | recalage_propose |
| `MF-6014` | TD_TAD | neuf_2025 / plan2025 | ligne ML-5297 ; bordure K-0388 | -0.34 / -0.275 | -0.065 | conforme |
| `MF-6015` | TD | neuf_2025 / plan2025 | ligne ML-0804 ; bordure K-0403 | -0.09 / 0.0 | -0.09 | conforme |
| `MF-6016` | TD | neuf_2025 / plan2025 | bordure K-0626 ; ligne ML-5298 | -0.067 / 0.0 | -0.067 | conforme |
| `MF-6017` | TD | neuf_2025 / plan2025 | bordure K-0626 ; ligne ML-5298 | -0.188 / 0.0 | -0.188 | recalage_propose |
| `MF-6018` | TD | neuf_2025 / plan2025 | ligne ML-5298 ; bordure K-0381 | -0.162 / 0.0 | -0.162 | recalage_propose |
| `MF-6020` | TD | neuf_2025 / plan2025 | voie OpenDRIVE 2/-1 | -0.255 / 0.0 | -0.255 | recalage_propose |
| `MF-6021` | TD | neuf_2025 / plan2025 | voie OpenDRIVE 2/-2 | -0.205 / 0.0 | -0.205 | recalage_propose |
| `MF-8000` | TD_TAD | neuf_2025 / regle:INF-FLE-004 | - | None / None | None | glissement_s_propose |

Marques hors chaussée (hors exceptions : lignes jaunes, figurines, passages coupant un refuge) : 27.

- `MF-0774` (fleche directionnelle, plan2025, neuf_2025) : 100 % hors chaussée, débord max 1.0 m -> signalement (flèche hors chaussée : jamais translatée ici (Q5) ; voir le contrôle des flèches (conflit surface / marquage))
- `MF-8000` (fleche directionnelle, regle:INF-FLE-004, neuf_2025) : 32 % hors chaussée, débord max 0.734 m -> signalement (flèche hors chaussée : jamais translatée ici (Q5) ; voir le contrôle des flèches (conflit surface / marquage))
- `ML-0113` (ligne continue, ortho2022, conserve) : 9 % hors chaussée, débord max 0.448 m -> raccourcissement_propose (extrémités au-delà de l'arête avant de la bordure : la marque s'arrête à l'arête chaussée (TQ-MQG-014, MQ-DET-010))
- `ML-0115` (ligne continue, ortho2022, conserve) : 11 % hors chaussée, débord max 0.028 m -> translation_proposee
- `ML-0187` (ligne continue, ortho2022, conserve) : 100 % hors chaussée, débord max 1.0 m -> signalement
- `ML-0189` (ligne continue, ortho2022, conserve) : 100 % hors chaussée, débord max 1.0 m -> signalement
- `ML-0190` (ligne continue, ortho2022, conserve) : 100 % hors chaussée, débord max 1.0 m -> signalement
- `ML-0197` (ligne continue, ortho2022, conserve) : 100 % hors chaussée, débord max 1.0 m -> signalement
- `ML-0198` (ligne continue, ortho2022, conserve) : 100 % hors chaussée, débord max 1.0 m -> signalement
- `ML-0208` (ligne segment, ortho2022, conserve) : 6 % hors chaussée, débord max 0.469 m -> raccourcissement_propose (extrémités au-delà de l'arête avant de la bordure : la marque s'arrête à l'arête chaussée (TQ-MQG-014, MQ-DET-010))
- `ML-5139` (ligne continue, gam, conserve) : 99 % hors chaussée, débord max 1.0 m -> signalement (marque levée GAM : la bordure ou la limite de chaussée décrite est à revoir)
- `ML-5140` (ligne segment, gam, conserve) : 27 % hors chaussée, débord max 0.68 m -> signalement (marque levée GAM : la bordure ou la limite de chaussée décrite est à revoir)
- `ML-5142` (ligne segment, gam, conserve) : 27 % hors chaussée, débord max 0.531 m -> signalement (marque levée GAM : la bordure ou la limite de chaussée décrite est à revoir)
- `ML-5145` (ligne segment, gam, conserve) : 100 % hors chaussée, débord max 1.0 m -> signalement (marque levée GAM : la bordure ou la limite de chaussée décrite est à revoir)
- `ML-5146` (ligne segment, gam, conserve) : 27 % hors chaussée, débord max 0.686 m -> signalement (marque levée GAM : la bordure ou la limite de chaussée décrite est à revoir)
- `ML-5252` (ligne continue, gam, neuf_2025) : 13 % hors chaussée, débord max 0.034 m -> signalement (marque levée GAM : la bordure ou la limite de chaussée décrite est à revoir)
- `ML-5253` (ligne continue, gam, neuf_2025) : 4 % hors chaussée, débord max 0.019 m -> signalement (marque levée GAM : la bordure ou la limite de chaussée décrite est à revoir)
- `ML-5302` (ligne continue, gam, neuf_2025) : 4 % hors chaussée, débord max 0.42 m -> signalement (marque levée GAM : la bordure ou la limite de chaussée décrite est à revoir)
- `MT-0563` (transversale effet_feux, plan2025, conserve) : 4 % hors chaussée, débord max 0.102 m -> raccourcissement_propose (extrémités au-delà de l'arête avant de la bordure : la marque s'arrête à l'arête chaussée (TQ-MQG-014, MQ-DET-010))
- `MT-8000` (transversale effet_feux, regle:MQ-LEF-002, neuf_2025) : 7 % hors chaussée, débord max 0.165 m -> raccourcissement_propose (extrémités au-delà de l'arête avant de la bordure : la marque s'arrête à l'arête chaussée (TQ-MQG-014, MQ-DET-010))
- `MT-8001` (transversale effet_feux, regle:MQ-LEF-011, neuf_2025) : 7 % hors chaussée, débord max 0.161 m -> raccourcissement_propose (extrémités au-delà de l'arête avant de la bordure : la marque s'arrête à l'arête chaussée (TQ-MQG-014, MQ-DET-010))
- `MT-8002` (transversale effet_feux, regle:MQ-LEF-002, neuf_2025) : 4 % hors chaussée, débord max 0.007 m -> raccourcissement_propose (extrémités au-delà de l'arête avant de la bordure : la marque s'arrête à l'arête chaussée (TQ-MQG-014, MQ-DET-010))
- `MT-8005` (transversale effet_feux, regle:MQ-LEF-002, neuf_2025) : 4 % hors chaussée, débord max 0.457 m -> raccourcissement_propose (extrémités au-delà de l'arête avant de la bordure : la marque s'arrête à l'arête chaussée (TQ-MQG-014, MQ-DET-010))
- `MT-8006` (transversale effet_feux, regle:MQ-LEF-011, neuf_2025) : 4 % hors chaussée, débord max 0.451 m -> raccourcissement_propose (extrémités au-delà de l'arête avant de la bordure : la marque s'arrête à l'arête chaussée (TQ-MQG-014, MQ-DET-010))
- `MZ-5189` (zone bande_isolee, gam, neuf_2025) : 30 % hors chaussée, débord max 0.338 m -> signalement (marque levée GAM : la bordure ou la limite de chaussée décrite est à revoir)
- `MZ-5211` (zone divers, gam, conserve) : 100 % hors chaussée, débord max 0.986 m -> signalement (marque levée GAM : la bordure ou la limite de chaussée décrite est à revoir)
- `MZ-5282` (zone bande_isolee, gam, neuf_2025) : 6 % hors chaussée, débord max 0.055 m -> signalement (marque levée GAM : la bordure ou la limite de chaussée décrite est à revoir)

## Têtes de feux (16 réorientées ou signalées sur 31)

| tête | support | azimut | règle | motif | statut |
|---|---|---|---|---|---|
| `feu_NE_TPC_t2` (R12) | `feu_NE_TPC` | 315.0 → 296.0° (cible 296.0°, écart 19.0°) | FEU-07 | extrémité opposée du passage MP-5170 | reoriente |
| `feu_NE_TPC_t3` (R12) | `feu_NE_TPC` | 135.0 → 151.4° (cible 151.4°, écart 16.4°) | FEU-07 | extrémité opposée du passage MP-5191 | reoriente |
| `feu_NE_droite_t2` (R12) | `feu_NE_droite` | 135.0 → 154.6° (cible 154.6°, écart 19.6°) | FEU-07 | extrémité opposée du passage MP-5170 | reoriente |
| `feu_NE_droite_t3` (R11v_rep) | `feu_NE_droite` | 45.0 → 78.9° (cible 78.9°, écart 33.9°) | FEU-06 | premier véhicule arrêté à la ligne MT-8002 (axe de la voie la plus proche) | reoriente |
| `feu_REV_E_pietons_t2` (R13c) | `feu_REV_E_pietons` | 45.0 → 17.9° (cible 17.9°, écart 27.1°) | FEU-09 | cyclistes en attente avant la traversée MP-0001 | reoriente |
| `feu_REV_droite_t3` (R13c) | `feu_REV_droite` | 225.0 → 282.3° (cible 282.3°, écart 57.3°) | FEU-09 | cyclistes en attente avant la traversée MP-0001 | reoriente |
| `feu_REV_droite_t4` (R11v_rep) | `feu_REV_droite` | 330.0 → 352.3° (cible 352.3°, écart 22.3°) | FEU-06 | premier véhicule arrêté à la ligne MT-8004 (axe de la voie la plus proche) | reoriente |
| `feu_SW_TPC_t2` (R12) | `feu_SW_TPC` | 135.0 → 114.0° (cible 114.0°, écart 21.0°) | FEU-07 | extrémité opposée du passage MP-5246 | reoriente |
| `feu_SW_TPC_t3` (R12) | `feu_SW_TPC` | 315.0 → 333.9° (cible 333.9°, écart 18.9°) | FEU-07 | extrémité opposée du passage MP-5257 | reoriente |
| `feu_SW_droite_t2` (R12) | `feu_SW_droite` | 315.0 → 338.0° (cible 338.0°, écart 23.0°) | FEU-07 | extrémité opposée du passage MP-5246 | reoriente |
| `feu_SW_droite_t3` (R11v_rep) | `feu_SW_droite` | 225.0 → 260.7° (cible 260.7°, écart 35.7°) | FEU-06 | premier véhicule arrêté à la ligne MT-8001 (axe de la voie la plus proche) | reoriente |
| `feu_VERC_droite_t1` (R11v) | `feu_VERC_droite` | 172.0 → 172.0° (cible 161.5°, écart 10.5°) | FEU-05 | voie gérée à 40 m en amont de la ligne MT-8006 | orientation_signalee |
| `feu_VERC_droite_t3` (R11v_rep) | `feu_VERC_droite` | 172.0 → 182.8° (cible 182.8°, écart 10.8°) | FEU-06 | premier véhicule arrêté à la ligne MT-8006 (axe de la voie la plus proche) | reoriente |
| `feu_VERC_droite_t4` (AB3a) | `feu_VERC_droite` | 172.0 → 172.0° (cible 161.5°, écart 10.5°) | SIG-08 | voie gérée à 40 m en amont de la ligne MT-8006 | orientation_signalee |
| `feu_VERC_ilot_t1` (R11v) | `feu_VERC_ilot` | 172.0 → 172.0° (cible 154.7°, écart 17.3°) | FEU-05 | voie gérée à 40 m en amont de la ligne MT-8006 | orientation_signalee |
| `feu_VERC_ilot_t2` (R12) | `feu_VERC_ilot` | 59.0 → 59.0° (cible 35.1°, écart 23.9°) | FEU-07 | extrémité opposée du passage MP-5189 | orientation_signalee |

## Cheminement piéton (PMR-01, 10 objets)

Coupes tous les 1 m derrière les bordures à côté bas circulé (`carte/cheminement_coupes.geojson`, classes des surfaces v2 du site complet) : 1579 coupes, 456 sous le seuil, dont 101 hors îlots et terre-pleins (coupe qui ne finit pas sur une autre chaussée) et 81 réduites par un objet (positions résolues). La v1 (classes raster) en comptait 71 sur 1005 : les surfaces v2 bornent le cheminement aux bandes vertes et comptent les îlots ; seule la réduction due à un objet déclenche PMR-01.


## Anomalies de surface (19 objets : l'objet prouvé prime, la surface est à corriger)

- `arbre_019` (arbre) sur batiment (classe batiment, d bordure 8.576 m), preuve gam : preuve forte (gam, σ 0.05 m) sur batiment de classe peu sûre (d bordure 8.576 m) : emprise bâtie (BD TOPO / OSM) trop large ou arbre de cour
- `arbre_034` (arbre) sur batiment (classe batiment, d bordure 7.856 m), preuve gam : preuve forte (gam, σ 0.05 m) sur batiment de classe peu sûre (d bordure 7.856 m) : emprise bâtie (BD TOPO / OSM) trop large ou arbre de cour
- `arbre_166` (arbre) sur bande_cyclable (classe chaussee, d bordure 1.444 m), preuve plan2025 : aucune position admissible et aucune preuve pour trancher; la surface surf_0280 (espace_vert) a été (re)construite en 2025 (limites:gam_bordure ; classe:plan_projet_2025+ortho_2022+lidar_2021) et l'objet n'est prouvé qu'avant les travaux : objet peut-être supp
- `arbre_179` (arbre) sur bande_cyclable (classe chaussee, d bordure 1.591 m), preuve plan2025 : aucune position admissible et aucune preuve pour trancher; la surface surf_0280 (espace_vert) a été (re)construite en 2025 (limites:gam_bordure ; classe:plan_projet_2025+ortho_2022+lidar_2021) et l'objet n'est prouvé qu'avant les travaux : objet peut-être supp
- `arbre_188` (arbre) sur batiment (classe batiment, d bordure 4.872 m), preuve gam : preuve forte (gam, σ 0.05 m) sur batiment de classe peu sûre (d bordure 4.872 m) : emprise bâtie (BD TOPO / OSM) trop large ou arbre de cour
- `arbre_189` (arbre) sur batiment (classe batiment, d bordure 6.436 m), preuve gam : preuve forte (gam, σ 0.05 m) sur batiment de classe peu sûre (d bordure 6.436 m) : emprise bâtie (BD TOPO / OSM) trop large ou arbre de cour
- `arbre_194` (arbre) sur bande_cyclable (classe chaussee, d bordure 1.55 m), preuve plan2025 : aucune position admissible et aucune preuve pour trancher; la surface surf_0282 (espace_vert) a été (re)construite en 2025 (limites:gam_bordure ; classe:plan_projet_2025+ortho_2022+lidar_2021) et l'objet n'est prouvé qu'avant les travaux : objet peut-être supp
- `arbre_206` (arbre) sur bande_cyclable (classe chaussee, d bordure 1.685 m), preuve plan2025 : aucune position admissible et aucune preuve pour trancher; la surface surf_0282 (espace_vert) a été (re)construite en 2025 (limites:gam_bordure ; classe:plan_projet_2025+ortho_2022+lidar_2021) et l'objet n'est prouvé qu'avant les travaux : objet peut-être supp
- `arbre_207` (arbre) sur bande_cyclable (classe chaussee, d bordure 1.635 m), preuve plan2025 : aucune position admissible et aucune preuve pour trancher; la surface surf_0282 (espace_vert) a été (re)construite en 2025 (limites:gam_bordure ; classe:plan_projet_2025+ortho_2022+lidar_2021) et l'objet n'est prouvé qu'avant les travaux : objet peut-être supp
- `arbre_226` (arbre) sur chaussee (classe chaussee, d bordure 1.471 m), preuve gam : preuve forte (gam, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 1.471 m) : îlot, refuge, fosse ou bande plantée absents des surfaces
- `arbre_297` (arbre) sur chaussee (classe chaussee, d bordure 4.448 m), preuve gam : preuve forte (gam, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 4.448 m) : îlot, refuge, fosse ou bande plantée absents des surfaces
- `arbre_298` (arbre) sur chaussee (classe chaussee, d bordure 3.281 m), preuve gam : preuve forte (gam, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 3.281 m) : îlot, refuge, fosse ou bande plantée absents des surfaces
- `arbre_397` (arbre) sur chaussee (classe chaussee, d bordure 2.437 m), preuve gam : preuve forte (gam, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 2.437 m) : îlot, refuge, fosse ou bande plantée absents des surfaces
- `arbre_398` (arbre) sur chaussee (classe chaussee, d bordure 2.196 m), preuve gam : preuve forte (gam, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 2.196 m) : îlot, refuge, fosse ou bande plantée absents des surfaces
- `lamp_12668578865` (lampadaire) sur chaussee (classe chaussee, d bordure 13.883 m), preuve mesure : revue : ortho 2022 grille 0,25 m : l'ombre du mât (trait fin vers 334°, ombre de la lanterne au bout) s'arrête au bord du disque clair (lanterne vue de dessus) vers (−124,36 ; 119,45) ; début d'ombre possiblement masqué par le disque sur ≤ 0,3 m : pied ≈ (−124
- `lamp_12668620636` (lampadaire) sur chaussee (classe chaussee, d bordure None m), preuve mesure : revue : ortho 2022 : le mât est au centre de la jardinière ronde du parking, son ombre (trait vers 334° jusqu'au disque de la lanterne) part de C ; le détecteur d'ombres (O) tombe à 0,2 m ; le nœud OSM (A) est à 1,8 m dans les places. La jardinière manque aux 
- `poteau_bois_REV_ilot` (poteau_reseau) sur chaussee (classe chaussee, d bordure 4.136 m), preuve photo_pnp : preuve forte (photo_pnp, σ 0.1 m) sur chaussee de classe peu sûre (d bordure 4.136 m) : îlot, refuge, fosse ou bande plantée absents des surfaces
- `poteau_reseau_9742811518` (poteau_reseau) sur bande_cyclable (classe chaussee, d bordure 1.456 m), preuve osm : aucune position admissible et aucune preuve pour trancher; la surface surf_0280 (espace_vert) a été (re)construite en 2025 (limites:gam_bordure ; classe:plan_projet_2025+ortho_2022+lidar_2021) et l'objet n'est prouvé qu'avant les travaux : objet peut-être supp
- `stationnement_velos_8360665117` (stationnement_velos) sur bande_cyclable (classe chaussee, d bordure 1.62 m), preuve osm : aucune position admissible et aucune preuve pour trancher; anomalie collective : 4 objets indépendants (arbre_166, arbre_179, poteau_reseau_9742811518, stationnement_velos_8360665117) en violation physique sur la surface S-0280a (chaussee, classe a_priori:vote

## Propositions d'ajouts et signalements

- `ADD-BTN-MP-5191-a` (tete_feu boitier_bouton_appel, proposition, conf faible) : OSM node/1959022976 button_operated=yes sur le passage MP-5191 : boîtier à 1,0 m sur feu_NE_SE_pietons, face vers le passage
- `ADD-BTN-MP-5191-b` (tete_feu boitier_bouton_appel, proposition, conf faible) : OSM node/1959022976 button_operated=yes sur le passage MP-5191 : boîtier à 1,0 m sur feu_NE_TPC, face vers le passage
- `ADD-ILOT-arbre_397` (ilot_manquant, proposition, conf faible) : objets prouvés (arbre_397) sur la chaussée à plus de 2 m de toute bordure : îlot bordé absent des surfaces ; MNT 2026 surélevé de 0.07 m
- `ADD-ILOT-lamp_12668578865` (ilot_manquant, proposition, conf moyenne) : objets prouvés (lamp_12668578865) sur la chaussée à plus de 2 m de toute bordure : îlot bordé absent des surfaces ; MNT 2026 surélevé de 0.07 m
- `ADD-ILOT-poteau_bois_REV_ilot` (ilot_manquant, proposition, conf moyenne) : objets prouvés (poteau_bois_REV_ilot) sur la chaussée à plus de 2 m de toute bordure : îlot bordé absent des surfaces ; emprise a priori (MNT 2026 : -0.01 m)
- `ADD-SPEC-J5_SO` (hypothese_spec, a_arbitrer, conf faible) : panneaux.json décrit J5_SO (J5), absent de mobilier.geojson
- `ADD-SPEC-M12a_feu_REV_droite` (hypothese_spec, a_arbitrer, conf faible) : panneaux.json place M12a_feu_REV_droite (M12a (probable)) à 0.169 m de feu_REV_droite (même support ?)
- `ADD-SPEC-M12a_ou_AB3a_feu_VERC_droite` (hypothese_spec, a_arbitrer, conf faible) : panneaux.json place M12a_ou_AB3a_feu_VERC_droite (M12a (probable)) à 0.255 m de feu_VERC_droite (même support ?)
- `ADD-SPEC-M9c_acces_NE` (hypothese_spec, a_arbitrer, conf faible) : panneaux.json décrit M9c_acces_NE (M9c), absent de mobilier.geojson
- `ADD-SPEC-M9c_ruisseau` (hypothese_spec, a_arbitrer, conf faible) : panneaux.json place M9c_ruisseau (M9c) à 0.238 m de lamp_12894130974 (même support ?)
- `ADD-SPEC-feu_REV_ilot_E` (hypothese_spec, a_arbitrer, conf faible) : feux.json place feu_REV_ilot_E (support_feux) à 0.583 m de pan_D21_1 (même support ?)
- `ADD-SPEC-feu_REV_ilot_axial` (hypothese_spec, a_arbitrer, conf faible) : feux.json place feu_REV_ilot_axial (support_feux) à 0.054 m de poteau_bois_REV_ilot (même support ?)
- `ADD-SPEC-plaque_mat_3150` (hypothese_spec, a_arbitrer, conf faible) : panneaux.json décrit plaque_mat_3150 (plaque de rue), absent de mobilier.geojson
- `ADD-SURF-S-0280a` (surface_a_corriger, proposition, conf faible) : 4 objets de 2 source(s) (arbres/plan2025, mobilier/osm) sur la surface S-0280a classée chaussee (a_priori:vote_indices_classe ; v1 surf_0280 espace_vert) : bande plantée, îlot ou trottoir probable ; à vérifier sur place
- `ADD-SURF-S-0282a` (surface_a_corriger, proposition, conf faible) : 3 objets de 1 source(s) (arbres/plan2025) sur la surface S-0282a classée chaussee (a_priori:vote_indices_classe ; v1 surf_0282 espace_vert) : bande plantée, îlot ou trottoir probable ; à vérifier sur place
- `ADD-SURF-arbre_297` (surface_a_corriger, proposition, conf faible) : arbre levé (arbre_297) sur une chaussée v1 d'origine raster, à plus de 2 m de toute bordure (emprise a priori (MNT 2026 : -0.85 m)) : fosse, bande plantée ou limite de surface à corriger
- `ADD-SURF-arbre_298` (surface_a_corriger, proposition, conf faible) : arbre levé (arbre_298) sur une chaussée v1 d'origine raster, à plus de 2 m de toute bordure (emprise a priori (MNT 2026 : +0.03 m)) : fosse, bande plantée ou limite de surface à corriger
- `ADD-SURF-arbre_398` (surface_a_corriger, proposition, conf faible) : arbre levé (arbre_398) sur une chaussée v1 d'origine raster, à plus de 2 m de toute bordure (emprise a priori (MNT 2026 : -0.23 m)) : fosse, bande plantée ou limite de surface à corriger
- `DISTINCTS-poteau:riv_NE_1-poteau:riv_NE_2` (supports_distincts, signalement, conf moyenne) : supports poteau:riv_NE_1 et poteau:riv_NE_2 à 0.19 m : deux mâts distincts établis par pnx:bb9c05ff (2025-08-31) : 2 mât(s) : jamais fusionnés (P5)
- `FUS-lamp_9514825221-mat_camera_9831317323` (fusion_supports, proposition, conf moyenne) : supports lamp_9514825221 (lampadaire) et mat_camera_9831317323 (mat_camera) à 0.00 m : un seul mât établi par ortho:pcrs2022 (2022-05-10) : 1 mât(s) (P5)

## Conflits avec feux.json / panneaux.json

- `SPEC-B1_acces_NE` ↔ `pan_B1_1` : écart 4.442 m, azimut 60.0° ; position de la spec illégale (GEN-01, SIG-01)
- `SPEC-B21a1_ilot_D_centre` ↔ `pan_B21a1_1` : écart 0.56 m, azimut 15.0° ; position de la spec légale
- `SPEC-B2b_acces_NE` ↔ `pan_B2b_1` : écart 4.442 m, azimut 60.0° ; position de la spec illégale (GEN-01, SIG-01)
- `SPEC-J5_nez_TPC_NE` ↔ `pan_J5_1` : écart 2.226 m ; position de la spec illégale (GEN-01, SIG-01, SIG-10)
- `SPEC-feu_NE_droite` ↔ `feu_NE_droite` : écart 0.359 m ; position de la spec légale
- `SPEC-feu_SW_cycles_SE` ↔ `feu_SW_cycles_SE` : écart 3.139 m ; position de la spec illégale (FEU-04, GEN-01, GEN-03)
- `SPEC-feu_VERC_O_pietons` ↔ `feu_VERC_O_pietons` : écart 0.3 m ; position de la spec illégale (FEU-04, FEU-07, GEN-02)
- `SPEC-pan_A17_1` ↔ `pan_A17_1` : écart 1.523 m ; position de la spec illégale (GEN-01, SIG-01)
- `SPEC-pan_AB3a_1` ↔ `pan_AB3a_1` : écart 0.238 m, azimut 50.0° ; position de la spec légale
- `SPEC-pan_AB3a_2` ↔ `pan_AB3a_2` : écart 6.699 m, azimut 68.0° ; position de la spec légale
- `SPEC-pan_AB3a_3` ↔ `pan_AB3a_3` : écart 4.827 m ; position de la spec illégale (GEN-01, SIG-01)
- `SPEC-pan_AB4_1` ↔ `pan_AB4_2` : écart 1.014 m ; position de la spec illégale (GEN-01, SIG-01)
- `SPEC-pan_B2a_1` ↔ `pan_B2a_1` : écart 6.699 m, azimut 68.0° ; position de la spec légale
- `SPEC-pan_C113_1` ↔ `pan_C113_1` : écart 3.133 m, azimut 160.0° ; position de la spec illégale (GEN-01, SIG-01)
- `SPEC-pan_C114_1` ↔ `pan_C114_1` : écart 0.238 m, azimut 50.0° ; position de la spec légale
- `SPEC-pan_D21_1` ↔ `pan_D21_1` : écart 0.0 m, azimut 90.0° ; position de la spec illégale (GEN-01, SIG-01, SIG-12)
- `SPEC-pan_D21_2` ↔ `pan_D21_2` : écart 0.0 m, azimut 90.0° ; position de la spec illégale (GEN-01, SIG-01, SIG-12)

## Limites

- Q9 (P11 à P16 de la revue v1 : rangées d'arbres, jalonnement relocalisé du D21, masque du véhicule dans le calage, repère (s, t) hors étendue, statut temporel des arbres GAM, double lecture à l'aveugle) n'est pas dans ce lot : arbre_109 / arbre_110, D21 et J5_2, potelet_13827066658 restent tels quels.
- Q2 est strict : là où aucun élément levé n'entre dans le secteur de ±30° (B6a1 depuis ded07efa, abords du Vercors avant travaux), la photo n'est pas décisive et une mesure qui ne reposait que sur elle devient un indice (B6a1 / C13a / lamp_9514828517 restent à leur position source). Une pose validée à son propre σ peut rester fausse de 2σ (mly:1207034570953803, σ ≈ 0,6 à 1,0° à cause de σ_pos 0,25 m) : le vote multi-photos et le consensus des axes la neutralisent pour lamp_9665416717.
- Le détecteur d'axe ne voit que les structures verticales nettes ; sous la résolution des photos (déplacement < 2σ), les deux hypothèses s'ajustent et la mesure reste un indice (feu_NE_TPC, poteau_bois_REV_ilot : ≤ 0,2 m).
- Le test automatique de présence est un indice (végétation du fond, voitures) : la décision vient de la revue de présence de Claude, obligatoire et datée.
- Aucune photo du cœur après les travaux 2025 : un objet posé ou déduit pour 2026 au cœur n'est prouvable que par le terrain (stations S1 à S15).
- Les flèches levées GAM ne sont jamais déplacées ; un écart à MQ-FLE-006 y signale des bords de voie à vérifier.
