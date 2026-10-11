# Solveur de cohérence v2 : « l'objet devait-il être ici, ou plutôt là ? »

Couche séparée, à fusionner par le composeur. Ni le paquet v1 ni la description de base v2 ne sont modifiés.
Commande : `python recon/pcg/decrire/coherence.py` (déterministe ; `--sans-planches` pour l'évaluation seule). Les planches `planches/*.jpg` contiennent des photos de tiers : locales, ignorées par git.

## Ce qui change par rapport à la v1 (revue adverse P1 à P10)

- **P1, photos** : 48 poses calées utilisées (mapillary calee_bordures 27, mapillary calee_gcp 5 décisives, panoramax calee 1, panoramax calee 12 décisives, panoramax_2026 calee_sequence 3 décisives), dont 20 décisives (LOO ≤ 0,5°). L'a priori de séquence est impossible pour 2025-08-31, 2025-01-12 et 2024-05-01 (aucune photo acceptée dans ces séries) : ces photos servent aux tests ordinaux de la revue (nombre de mâts, plaques, présence à une date), photo citée.
- **P2, géométrie** : chaque planche affiche, photo par photo, la séparation A↔C rapportée au σ de la pose, et la porte de chaque paire (complète / latérale / non observable). Corrections par porte : {'complet': 8, 'lateral': 7, 'non_observable': 33, 'sans_photo': 16}.
- **P3, mesures** : 24 objets reçoivent une mesure comme nouvel a priori (revue, fusion 0.3 « appliquer », triangulations fiables, ombres concordantes) avant la résolution.
- **P4, orientation** : azimut par raccourci des plaques sur ≥ 2 vues (w/h mesuré / w/h de face), plaques du mât identifiées avant tout transfert.
- **P5, fusions** : candidats exclus à moins de r1 + r2 + 0,10 m d'un objet de preuve au moins aussi bonne ; fusion seulement si « même support » ou photo à un seul mât. Propositions : {'fusion_supports': 1, 'hypothese_spec': 8, 'ilot_manquant': 4, 'supports_distincts': 1, 'surface_a_corriger': 5, 'tete_feu': 2}.
- **P6, bordures** : 512 bordures de la description régularisée (site complet), 305 d'orientation forte ; incohérences voie/côté haut restantes : 0.
- **P7, dureté** : pour un objet existant, seules les violations physiques (chaussée, voies, passages, îlot peint, bâti) sont dures. Statuts d'objets : {'absent': 10, 'deduit': 14, 'existant': 579, 'projet': 17}. Règles dures violées : {'BAR-03': 1, 'ECL-01': 6, 'FEU-02': 1, 'FEU-04': 3, 'FEU-07': 2, 'GEN-01': 38, 'GEN-02': 1, 'GEN-03': 4, 'GEN-09': 5, 'MOB-01': 1, 'PMR-01': 6, 'POT-01': 2, 'RES-02': 3, 'RES-03': 1, 'SIG-01': 6, 'SIG-02': 2, 'SIG-10': 1, 'SIG-12': 2, 'TC-01': 1, 'VEG-01': 21, 'VEG-02': 1, 'VEG-06': 4}. Règles signalées sans déplacement (objets existants) : {'BAR-03': 1, 'ECL-01': 5, 'ECL-05': 2, 'FEU-01': 2, 'FEU-04': 2, 'GEN-02': 4, 'GEN-03': 15, 'GEN-08': 1, 'PMR-01': 4, 'POT-01': 6, 'RES-02': 1, 'SIG-02': 4, 'SIG-05': 1, 'SIG-07': 1, 'SIG-10': 1, 'VEG-02': 35, 'VEG-03': 1}.
- **P8, GEN-02** : supports de feux piétons et boutons d'appel admis à la limite arrière de la BEV dans le prolongement du passage (CEREMA fiche BEV 03) ; palier de 0,80 m majeur, dessiné seulement si le trottoir le permet (ARR2007 art. 1er 4°).
- **P9, budget** : déplacement compté depuis la position source brute (nœud OSM brut) ; dépassements : aucun.
- **P10, ombres (PCRS 5 cm 2022-05-10)** : ombres à 334.0° (grille), soleil à 60.68° vers 10:45 UTC, calé sur 15 mâts triangulés ; validation : 25 détections acceptées sur 60 essais (9 mâts), biais le long de l'ombre 0.146 m, σ long 0.179 m, σ travers 0.077 m, p90 1.025 m -> σ retenus {'long': 0.6, 'travers': 0.15} ; une détection seule est un indice, probante si les deux orthos concordent.
- **P10, ombres (IGN BD ORTHO 20 cm 2024-08-09)** : ombres à 318.5° (grille), soleil à 54.97° vers 10:13 UTC, calé sur 8 mâts triangulés ; validation : 8 détections acceptées sur 60 essais (5 mâts), biais le long de l'ombre 0.132 m, σ long 0.104 m, σ travers 0.253 m, p90 0.693 m -> σ retenus {'long': 0.6, 'travers': 0.253} ; une détection seule est un indice, probante si les deux orthos concordent.

## Comptes

| verdict | objets |
|---|---|
| a_verifier | 111 |
| conforme | 455 |
| violation | 54 |

| statut de résolution | objets |
|---|---|
| a_arbitrer_photo | 1 |
| anomalie_surface | 23 |
| conforme | 484 |
| conforme_signale | 54 |
| corrige | 29 |
| mesure | 9 |
| non_instancie_absent_2026 | 10 |
| non_resolu | 3 |
| reoriente | 7 |

| type | conforme | a_verifier | violation |
|---|---|---|---|
| abri_bus | 1 | 0 | 1 |
| arbre | 374 | 77 | 16 |
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
| panneau | 7 | 9 | 12 |
| panneau_information | 3 | 1 | 0 |
| portail | 7 | 0 | 1 |
| poteau_arret | 2 | 1 | 0 |
| poteau_incendie | 0 | 0 | 3 |
| poteau_reseau | 4 | 2 | 2 |
| potelet | 2 | 4 | 2 |
| stationnement_velos | 7 | 1 | 1 |
| support_feux | 2 | 3 | 8 |
| totem_PR | 1 | 0 | 0 |

Têtes de feux : {'conforme': 15, 'orientation_signalee': 4, 'reoriente': 12}. Corrections : {'deplacement': 53, 'deplacement+reorientation': 4, 'non_instanciation': 4, 'reorientation': 15} (confiance : {'faible': 47, 'moyenne': 29}). Propositions : {'fusion_supports': 1, 'hypothese_spec': 8, 'ilot_manquant': 4, 'supports_distincts': 1, 'surface_a_corriger': 5, 'tete_feu': 2}.
Objets non instanciés : arbre_109, pan_D21_1, pan_D21_2, pan_J5_2.

Violations par règle (dures et signalées) : BAR-03 2, ECL-01 11, ECL-02 1, ECL-05 2, FEU-01 2, FEU-02 1, FEU-04 5, FEU-07 2, GEN-01 38, GEN-02 5, GEN-03 19, GEN-04 42, GEN-06 10, GEN-08 1, GEN-09 5, MOB-01 1, PMR-01 10, POT-01 8, RES-02 4, RES-03 3, SIG-01 6, SIG-02 6, SIG-04 10, SIG-05 1, SIG-07 1, SIG-10 2, SIG-12 3, TC-01 1, VEG-01 21, VEG-02 36, VEG-03 1, VEG-06 4.

## Les 20 décisions les plus significatives

| # | objet | décision | preuve | revue | porte P2 | planche |
|---|---|---|---|---|---|---|
| 1 | `pan_C113_1` (panneau C113) | 0.09 m (Δt 0.052, Δs -0.068) ; azimut 225.0 → 65.0° — reoriente | mesure σ 0.1 ; mesure triangulation_mixte | azimut corrigee (moyenne) | - | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_C113_1.jpg` |
| 2 | `pan_AB3a_3` (panneau AB3a) | 4.15 m (Δt 1.107, Δs 3.996) — mesure | mesure σ 0.15 ; mesure fusion_recensement_0.3 | corrigee (moyenne) | complet (3/11 photos > 3σ, 23.3°, validé +4.15 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_AB3a_3.jpg` |
| 3 | `pan_AB3a_2` (panneau AB3a) + pan_B2a_1, pan_M9_2 | 0.57 m (Δt 0.565, Δs 0.069) ; azimut 342.0 → 15.5° — reoriente | mesure σ 0.25 ; mesure revue_coherence | corrigee (faible) | non_observable (0/6 photos > 3σ, 0.0°, validé +0.00 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_AB3a_2.jpg` |
| 4 | `lamp_12668620636` (lampadaire) | 1.83 m — anomalie_surface | mesure σ 0.188 ; mesure fusion_recensement_0.3 | corrigee (moyenne) | aucune photo calée valide (preuve ortho ou règle) | `recon/out/paquet_jardin/v2/description/coherence/planches/lamp_12668620636.jpg` |
| 5 | `lamp_12668578865` (lampadaire) | 1.63 m — anomalie_surface | mesure σ 0.3 ; mesure revue_coherence | corrigee (moyenne) | aucune photo calée valide (preuve ortho ou règle) | `recon/out/paquet_jardin/v2/description/coherence/planches/lamp_12668578865.jpg` |
| 6 | `pan_J5_1` (panneau J5) | 0.93 m (Δt -0.889, Δs 0.259) — mesure | mesure σ 0.1 ; mesure revue_coherence | corrigee (moyenne) | complet (5/13 photos > 3σ, 84.4°, validé +0.93 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_J5_1.jpg` |
| 7 | `pan_AB4_2` (panneau AB4) | 0.92 m (Δt 0.088, Δs -0.918) — anomalie_surface | mesure σ 0.3 ; mesure fusion_recensement_0.3 | corrigee (moyenne) | complet (3/11 photos > 3σ, 17.4°, validé +0.92 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_AB4_2.jpg` |
| 8 | `lamp_9514825221` (lampadaire) | 1.17 m (Δt 0.055, Δs -1.164) — mesure | mesure σ 0.3 ; mesure revue_coherence | corrigee (moyenne) | non_observable (0/1 photos > 3σ, 0.0°, validé +0.00 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/lamp_9514825221.jpg` |
| 9 | `pan_B6a1_1` (panneau B6a1) + lamp_9514828517, pan_C13a_1 | 0.68 m (Δt -0.17, Δs 0.661) — anomalie_surface | mesure σ 0.05 ; mesure fusion_recensement_0.3 | - (faible) | lateral (1/2 photos > 3σ, 0.0°, validé -0.70 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/lamp_9514828517.jpg` |
| 10 | `pan_D21_1` (panneau D21) + pan_D21_2 | non instancié (a_verifier_terrain2026, obsolete_probable) — non_resolu | lidar2021 σ 0.15 | ambigu (faible) | - | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_D21_1.jpg` |
| 11 | `pan_J5_2` (panneau J5) | non instancié (a_verifier_terrain2026, obsolete_probable, surface_modifiee_2025) — non_resolu | constat σ 1.5 | ambigu (faible) | - | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_J5_2.jpg` |
| 12 | `mat_camera_9831317323` (mat_camera) | 1.12 m (Δt 0.697, Δs -0.872) — mesure | mesure σ 0.3 ; mesure revue_coherence | corrigee (moyenne) | non_observable (0/2 photos > 3σ, 0.0°, validé +0.00 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/mat_camera_9831317323.jpg` |
| 13 | `lamp_9665416717` (lampadaire) | 0.88 m (Δt 0.406, Δs -0.776) — mesure | mesure σ 0.25 ; mesure fusion_recensement_0.3 | - (moyenne) | lateral (3/8 photos > 3σ, 2.9°, validé -0.48 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/lamp_9665416717.jpg` |
| 14 | `feu_NE_droite` (support_feux) + feu_NE_droite_t2, feu_NE_droite_t3 | 0.36 m (Δt -0.041, Δs -0.357) — mesure | mesure σ 0.1 ; mesure triangulation_mixte | - (moyenne) | non_observable (0/12 photos > 3σ, 0.0°, validé +0.00 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/feu_NE_droite.jpg` |
| 15 | `lamp_9665416817` (lampadaire) | 0.58 m (Δt 0.437, Δs -0.382) — conforme_signale | mesure σ 0.083 ; mesure fusion_recensement_0.3 | corrigee (moyenne) | complet (5/10 photos > 3σ, 18.0°, validé +0.58 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/lamp_9665416817.jpg` |
| 16 | `feu_VERC_droite` (support_feux) + feu_VERC_droite_t3 | 0.26 m (Δt 0.061, Δs 0.247) — conforme_signale | mesure σ 0.169 ; mesure triangulation_mixte | - (faible) | - | `recon/out/paquet_jardin/v2/description/coherence/planches/feu_VERC_droite.jpg` |
| 17 | `pan_AB3a_1` (panneau AB3a) + lamp_12894130974, pan_C114_1, pan_M9_1 | 0.30 m (Δt 0.287, Δs -0.098) — conforme_signale | mesure σ 0.119 ; mesure triangulation_mixte | - (faible) | complet (2/10 photos > 3σ, 16.3°, validé +0.30 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/lamp_12894130974.jpg` |
| 18 | `pan_B21a1_4` (panneau B21a1) | azimut 10.0 → 341.1° — reoriente | plan2025 σ 1.5 | - (faible) | - | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_B21a1_4.jpg` |
| 19 | `lamp_lidar_VERC_E` (lampadaire) | 0.45 m (Δt 0.158, Δs 0.423) — mesure | mesure σ 0.163 ; mesure triangulation_mixte | - (moyenne) | lateral (1/10 photos > 3σ, 0.0°, validé -0.29 m) | `recon/out/paquet_jardin/v2/description/coherence/planches/lamp_lidar_VERC_E.jpg` |
| 20 | `potelet_13827066658` (potelet) | 1.90 m (Δt -1.9, Δs 0.0) — corrige | osm σ 1.0 | ambigu (faible) | aucune photo calée valide (preuve ortho ou règle) | `recon/out/paquet_jardin/v2/description/coherence/planches/potelet_13827066658.jpg` |

Justifications :

1. `pan_C113_1` : mesure retenue comme nouvel a priori (P3) : triangulation_mixte, σ 0.1 m, 0.09 m de la position source ; azimut photo de la spec (65°) conforme à la règle (48°) ; couche à 225°
2. `pan_AB3a_3` : mesure retenue comme nouvel a priori (P3) : fusion_recensement_0.3, σ 0.15 m, 4.15 m de la position source ; revue photo : position corrigée confirmée, porte P2 complète (3 photos discriminantes, 23.3°) (photos 2026 calées f8d91bb1, ded07efa, 00c1ba9a : le triangle AB3a et son poteau sont exactement sur C (refuge I-0658), A ne porte rien ; porte P2 complète)
3. `pan_AB3a_2` : mesure retenue comme nouvel a priori (P3) : revue_coherence, σ 0.25 m, 0.57 m de la position source ; revue : position = mesure de la revue ; la porte P2 est non observable (les photos voient le déplacement le long de leur visée) : seule la contrainte latérale est prouvée, confiance faible (mât 2 (B2a + AB3a + panonceau « CÉDEZ LE PASSAGE ») sur le rayon commun des 3 photos calées du SO (79a18815, eeb2f8f1, mly:1207034570953803, relèvements 217,5-220,1°) ; profondeur non observable (2,6°) : bornée par la bordure K-0186 (t ≥ 0,1 m, le mât n'est pas sur la piste) et par le mât 1 qu'il masque depuis le SO) ; test ordinal n_mats = 2 (pnx:bb9c05ff, 2025-08-31) : deux fûts distincts à ≈ 25 px l'un de l'autre (≈ 0,5° à 20 m), chacun avec ses plaques ; test ordinal plaques = mât 1 : disque B2b au-dessus du disque B1 ; mât 2 : disque B2a, triangle AB3a, panonceau « CÉDEZ LE PASSAGE » (de haut en bas) (pnx:bb9c05ff, pnx:9ef861d4, 2025-08-31) : identification faite avant tout transfert (P4) ; test ordinal occultation = depuis le SO le mât 2 masque le mât 1 ; depuis le NE (bb9c05ff) le mât 1 est devant (pnx:79a18815, pnx:eeb2f8f1, pnx:bb9c05ff, 2024-08-24/2025-08-31) : le mât 1 est au NE du mât 2 sur la même visée (≈ 38°) : les dos vus depuis le SO sont ceux du mât 2 ; raccourci des plaques sur 4 vues : face à 16° (rms 8.4°, second minimum 46° à 27.8°) (P4)
4. `lamp_12668620636` : mesure retenue comme nouvel a priori (P3) : fusion_recensement_0.3, σ 0.188 m, 1.83 m de la position source ; preuve forte (mesure, σ 0.188 m) sur chaussee de classe peu sûre (d bordure None m) : îlot, refuge, fosse ou bande plantée absents des surfaces ; revue (ortho) : position corrigée confirmée (ortho 2022 : le mât est au centre de la jardinière ronde du parking, son ombre (trait vers 334° jusqu'au disque de la lanterne) part de C ; le détecteur d'ombres (O) tombe à 0,2 m ; le nœud OSM (A) est à 1,8 m dans les places. La jardinière manque aux surfaces (classe chaussée) : anomalie de surface)
5. `lamp_12668578865` : mesure retenue comme nouvel a priori (P3) : revue_coherence, σ 0.3 m, 1.63 m de la position source ; preuve forte (mesure, σ 0.3 m) sur chaussee de classe peu sûre (d bordure 13.883 m) : îlot, refuge, fosse ou bande plantée absents des surfaces ; revue (ortho) : position corrigée confirmée (ortho 2022 grille 0,25 m : l'ombre du mât (trait fin vers 334°, ombre de la lanterne au bout) s'arrête au bord du disque clair (lanterne vue de dessus) vers (−124,36 ; 119,45) ; début d'ombre possiblement masqué par le disque sur ≤ 0,3 m : pied ≈ (−124,33 ; 119,38), à 1,6 m du nœud OSM (v1 : 0,22 m de recalage + 0,45 m de la règle, dans le mauvais sens le long))
6. `pan_J5_1` : mesure retenue comme nouvel a priori (P3) : revue_coherence, σ 0.1 m, 0.93 m de la position source ; revue photo : position corrigée confirmée, porte P2 complète (5 photos discriminantes, 84.4°) (pied de la balise pointé sur 4 vues calées (9834f494, 6e97bb8c, e86aa913, e5d79de9 ; relèvements 80° à 198°) : triangulé en (17,606 ; 14,805), résidus ≤ 0,06 m ; 0,93 m de la position de la couche vers le nez du TPC (lecture v1 : Δs ≈ +0,8 à 0,9 m))
7. `pan_AB4_2` : mesure retenue comme nouvel a priori (P3) : fusion_recensement_0.3, σ 0.3 m, 0.92 m de la position source ; preuve forte (mesure, σ 0.3 m) sur espace_vert de classe peu sûre (d bordure 3.066 m) : limite de surface ou zone dérivée à corriger ; revue photo : position corrigée confirmée, porte P2 complète (3 photos discriminantes, 17.4°) (photos 2026 calées : le STOP est sur C, à la pointe NO de l'îlot herbeux (mesure de la fusion PANO2026-015))
8. `lamp_9514825221` : mesure retenue comme nouvel a priori (P3) : revue_coherence, σ 0.3 m, 1.17 m de la position source ; revue (ortho) : position corrigée confirmée (même mât que mat_camera_9831317323 (une seule ombre sur l'ortho 2022)) ; test ordinal n_mats = 1 (ortho:pcrs2022, 2022-05-10) : une seule ombre de mât portant lanterne et caméra
9. `pan_B6a1_1` : mesure retenue comme nouvel a priori (P3) : fusion_recensement_0.3, σ 0.05 m, 0.68 m de la position source ; preuve forte (mesure, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 7.806 m) : îlot, refuge, fosse ou bande plantée absents des surfaces
10. `pan_D21_1` : preuve antérieure aux travaux 2025 (lidar2021) ; le marquage posé en 2025 MP-0001 (traversee_cyclable, neuf_2025) passe à son emplacement et la surface 2026 y est circulée : objet probablement déposé ou déplacé par les travaux, non instancié ; test ordinal presence = présent (pnx:a83dae90, pnx:81882270, 2025-08-31) : D21 « LA REVIRÉE / Collège L. Terray » et « Commerces de LA REVIRÉE » sur leur mât, balise J5 au pied, barrières de chantier ; antérieur à la fin des travaux (05/12/2025) : ne prouve rien de l'état 2026
11. `pan_J5_2` : preuve faible, aucune position admissible dans 3.0 m : arbitrage par 5 photo(s) calée(s) ; la surface surf_0323 (chaussee) a été (re)construite en 2025 (limites:gam_bordure ; classe:plan_projet_2025+osm_2026) et l'objet n'est prouvé qu'avant les travaux : objet peut-être supprimé ; violation critique non résolue sur une surface circulée : objet non instancié (resolution.arbitrage.non_instanciation) ; sur le même îlot que pan_D21_1, pan_D21_2 (probablement supprimé par les travaux 2025) ; test ordinal presence = présent (pnx:a83dae90, pnx:81882270, 2025-08-31) : D21 « LA REVIRÉE / Collège L. Terray » et « Commerces de LA REVIRÉE » sur leur mât, balise J5 au pied, barrières de chantier ; antérieur à la fin des travaux (05/12/2025) : ne prouve rien de l'état 2026
12. `mat_camera_9831317323` : mesure retenue comme nouvel a priori (P3) : revue_coherence, σ 0.3 m, 1.12 m de la position source ; revue (ortho) : position corrigée confirmée (ortho 2022 grille 0,25 m : une seule ombre de mât, qui commence vers (19,0 ; −62,07), au bord NO des images claires (lanterne et boîtier déversés vers le SE) ; nœuds OSM du candélabre et de la caméra à ≈ 1,1 m au NNO) ; test ordinal n_mats = 1 (ortho:pcrs2022, 2022-05-10) : une seule ombre de mât portant lanterne et caméra
13. `lamp_9665416717` : mesure retenue comme nouvel a priori (P3) : fusion_recensement_0.3, σ 0.25 m, 0.88 m de la position source
14. `feu_NE_droite` : mesure retenue comme nouvel a priori (P3) : triangulation_mixte, σ 0.1 m, 0.36 m de la position source
15. `lamp_9665416817` : mesure retenue comme nouvel a priori (P3) : fusion_recensement_0.3, σ 0.083 m, 0.58 m de la position source ; revue photo : position corrigée confirmée, porte P2 complète (5 photos discriminantes, 18.0°) (fût du candélabre (bannière LANDRI) exactement sur C dans les 4 vignettes (6e97bb8c, e540bf1d, 7651c539, e5d79de9) ; C = mesure de la fusion (triangulation), t = +0,44 m derrière K-0353 (lecture v1 : 0,37-0,59 m))
16. `feu_VERC_droite` : mesure retenue comme nouvel a priori (P3) : triangulation_mixte, σ 0.169 m, 0.26 m de la position source
17. `pan_AB3a_1` : mesure retenue comme nouvel a priori (P3) : triangulation_mixte, σ 0.119 m, 0.30 m de la position source
18. `pan_B21a1_4` : azimut d'une preuve faible à 29° de la règle : affiné
19. `lamp_lidar_VERC_E` : mesure retenue comme nouvel a priori (P3) : triangulation_mixte, σ 0.163 m, 0.45 m de la position source
20. `potelet_13827066658` : candidat admissible le plus proche (normale, Δt -1.90 m, Δs +0.00 m, J 78.212) dans la limite de la preuve (osm, d_max 2.0 m) ; revue ambiguë ou impossible : correction par la règle, confiance faible

## Tests ordinaux sur photos non calées ou orthos (P1)

- presence = troncs en retrait — objets arbre_396 — photos pnx:7a182db7 (2025-05-18) : grands peupliers penchés au-dessus de la piste, troncs plusieurs mètres en retrait (photo 360° non calée) : le sens de la correction est juste, son ampleur (1,6 m) est un minimum
- n_mats = 1 — objets mat_camera_9831317323, lamp_9514825221 — photos ortho:pcrs2022 (2022-05-10) : une seule ombre de mât portant lanterne et caméra
- n_mats = 2 — objets pan_AB3a_2, pan_B1_1 — photos pnx:bb9c05ff (2025-08-31) : deux fûts distincts à ≈ 25 px l'un de l'autre (≈ 0,5° à 20 m), chacun avec ses plaques
- plaques = mât 1 : disque B2b au-dessus du disque B1 ; mât 2 : disque B2a, triangle AB3a, panonceau « CÉDEZ LE PASSAGE » (de haut en bas) — objets pan_AB3a_2, pan_B1_1 — photos pnx:bb9c05ff, pnx:9ef861d4 (2025-08-31) : identification faite avant tout transfert (P4)
- occultation = depuis le SO le mât 2 masque le mât 1 ; depuis le NE (bb9c05ff) le mât 1 est devant — objets pan_AB3a_2, pan_B1_1 — photos pnx:79a18815, pnx:eeb2f8f1, pnx:bb9c05ff (2024-08-24/2025-08-31) : le mât 1 est au NE du mât 2 sur la même visée (≈ 38°) : les dos vus depuis le SO sont ceux du mât 2
- presence = présent — objets pan_D21_1, pan_D21_2, pan_J5_2 — photos pnx:a83dae90, pnx:81882270 (2025-08-31) : D21 « LA REVIRÉE / Collège L. Terray » et « Commerces de LA REVIRÉE » sur leur mât, balise J5 au pied, barrières de chantier ; antérieur à la fin des travaux (05/12/2025) : ne prouve rien de l'état 2026

**Raccourci des plaques (P4), `pan_AB3a_2`** : pnx:79a18815 relèvement 218.6°, w/h 1.08 / 1.1547 (dos, triangle AB3a) ; pnx:eeb2f8f1 relèvement 220.1°, w/h 1.13 / 1.1547 (dos, triangle AB3a) ; pnx:9ef861d4 relèvement 70.0°, w/h 0.53 / 1.1547 (face, triangle AB3a) ; pnx:9ef861d4 relèvement 70.0°, w/h 0.48 / 1.0 (face, disque B2a) -> raccourci des plaques sur 4 vues : face à 16° (rms 8.4°, second minimum 46° à 27.8°).

## Mesures appliquées comme a priori (P3, 24)

- `pan_AB3a_3` : 4.15 m de la position source, σ 0.15 m (fusion_recensement_0.3)
- `lamp_12668620636` : 1.83 m de la position source, σ 0.188 m (fusion_recensement_0.3)
- `lamp_12668578865` : 1.63 m de la position source, σ 0.3 m (revue_coherence)
- `lamp_9514825221` : 1.17 m de la position source, σ 0.3 m (revue_coherence)
- `mat_camera_9831317323` : 1.12 m de la position source, σ 0.3 m (revue_coherence)
- `pan_J5_1` : 0.93 m de la position source, σ 0.1 m (revue_coherence)
- `pan_AB4_2` : 0.92 m de la position source, σ 0.3 m (fusion_recensement_0.3)
- `lamp_9665416717` : 0.88 m de la position source, σ 0.25 m (fusion_recensement_0.3)
- `lamp_9514828517` : 0.70 m de la position source, σ 0.05 m (fusion_recensement_0.3)
- `pan_B6a1_1` : 0.68 m de la position source, σ 0.05 m (fusion_recensement_0.3)
- `pan_C13a_1` : 0.68 m de la position source, σ 0.05 m (fusion_recensement_0.3)
- `lamp_9665416817` : 0.58 m de la position source, σ 0.083 m (fusion_recensement_0.3)
- `pan_AB3a_2` : 0.57 m de la position source, σ 0.25 m (revue_coherence)
- `pan_C114_1` : 0.53 m de la position source, σ 0.121 m (triangulation_mixte)
- `lamp_lidar_VERC_E` : 0.45 m de la position source, σ 0.163 m (triangulation_mixte)
- `feu_NE_droite` : 0.36 m de la position source, σ 0.1 m (triangulation_mixte)
- `pan_AB3a_1` : 0.30 m de la position source, σ 0.119 m (triangulation_mixte)
- `feu_VERC_droite` : 0.26 m de la position source, σ 0.169 m (triangulation_mixte)
- `feu_NE_TPC` : 0.19 m de la position source, σ 0.1 m (triangulation_mixte)
- `poteau_bois_NE` : 0.18 m de la position source, σ 0.1 m (triangulation_mixte)
- `feu_REV_droite` : 0.16 m de la position source, σ 0.099 m (ombre_ortho, triangulation_mixte)
- `poteau_bois_REV_ilot` : 0.12 m de la position source, σ 0.134 m (triangulation_mixte)
- `pan_C113_1` : 0.09 m de la position source, σ 0.1 m (triangulation_mixte)
- `feu_REV_E_pietons` : 0.07 m de la position source, σ 0.1 m (triangulation_mixte)

## Marquages : flèches centrées dans leur voie, marques dans la chaussée

Comptes : {'fleches': {'garde_par_ortho': 3, 'conforme': 6, 'recalage_propose': 8, 'leve_ecart_garde': 5, 'voie_non_bornee': 4}, 'marques_hors_chaussee': {'signalement': 21, 'raccourcissement_propose': 9, 'translation_proposee': 1, 'exception': 18}}. Détail : `marquages_controle.json` ; propositions : `corrections_marquages.geojson`.

| flèche | gabarit | état / source | bords de voie | décalage obs. / attendu | écart | statut |
|---|---|---|---|---|---|---|
| `MF-0286` | TD | conserve / ortho2022 | voie OpenDRIVE 5/1 | 2.011 / 0.0 | 2.011 | garde_par_ortho |
| `MF-0764` | TD | neuf_2025 / plan2025 | ligne ML-5298 ; bordure K-0405 | -0.025 / 0.0 | -0.025 | conforme |
| `MF-0767` | TD_TAG | neuf_2025 / plan2025 | bordure K-0627 ; ligne ML-5297 | 0.21 / 0.275 | -0.065 | conforme |
| `MF-0769` | TD_TAD | neuf_2025 / plan2025 | bordure K-0402 ; ligne ML-0799 | -0.463 / -0.275 | -0.188 | recalage_propose |
| `MF-0774` | TD_TAD | neuf_2025 / plan2025 | bordure K-0347 ; ligne ML-0802 | -0.808 / -0.275 | -0.533 | recalage_propose |
| `MF-5042` | TD_TAG | conserve / gam | bordure K-0386 ; ligne ML-5136 | -0.091 / 0.275 | -0.366 | leve_ecart_garde |
| `MF-5043` | TD_TAD | conserve / gam | ligne ML-5136 ; ligne ML-5185 | 0.061 / -0.275 | 0.336 | leve_ecart_garde |
| `MF-5092` | TD | neuf_2025 / gam | - | None / None | None | voie_non_bornee |
| `MF-5096` | TD | neuf_2025 / gam | - | None / None | None | voie_non_bornee |
| `MF-5097` | TD | neuf_2025 / gam | - | None / None | None | voie_non_bornee |
| `MF-5109` | TD | neuf_2025 / gam | - | None / None | None | voie_non_bornee |
| `MF-5523` | TD | refait_2025_identique / gam | ligne ML-5405 ; ligne ML-5228 | 0.013 / 0.0 | 0.013 | conforme |
| `MF-5524` | TD_TAD | neuf_2025 / gam | ligne ML-5228 ; bordure K-0415 | -0.05 / -0.275 | 0.225 | leve_ecart_garde |
| `MF-5525` | TAG | neuf_2025 / gam | ligne ML-5401 ; ligne ML-5228 | 0.047 / 0.425 | -0.378 | leve_ecart_garde |
| `MF-5527` | TAG | neuf_2025 / gam | ligne ML-5402 ; ligne ML-5228 | 0.147 / 0.425 | -0.278 | leve_ecart_garde |
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
| `MF-8000` | TD_TAD | neuf_2025 / regle:INF-FLE-004 | ligne ML-5228 ; bordure K-0414 | -0.481 / -0.275 | -0.206 | recalage_propose |

Marques hors chaussée (hors exceptions : lignes jaunes, figurines, passages coupant un refuge) : 31.

- `MF-0774` (fleche directionnelle, plan2025, neuf_2025) : 100 % hors chaussée, débord max 1.0 m -> signalement
- `MF-8000` (fleche directionnelle, regle:INF-FLE-004, neuf_2025) : 32 % hors chaussée, débord max 0.734 m -> signalement
- `ML-0113` (ligne continue, ortho2022, conserve) : 9 % hors chaussée, débord max 0.448 m -> raccourcissement_propose (extrémités au-delà de l'arête avant de la bordure : la marque s'arrête à l'arête chaussée (TQ-MQG-014, MQ-DET-010))
- `ML-0115` (ligne continue, ortho2022, conserve) : 11 % hors chaussée, débord max 0.028 m -> translation_proposee
- `ML-0131` (ligne continue, ortho2022, conserve) : 22 % hors chaussée, débord max 1.0 m -> raccourcissement_propose (extrémités au-delà de l'arête avant de la bordure : la marque s'arrête à l'arête chaussée (TQ-MQG-014, MQ-DET-010))
- `ML-0132` (ligne continue, ortho2022, conserve) : 100 % hors chaussée, débord max 1.0 m -> signalement
- `ML-0133` (ligne continue, ortho2022, conserve) : 100 % hors chaussée, débord max 1.0 m -> signalement
- `ML-0135` (ligne continue, ortho2022, conserve) : 62 % hors chaussée, débord max 1.0 m -> signalement
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
| `feu_NE_TPC_t2` (R12) | `feu_NE_TPC` | 315.0 → 297.5° (cible 297.5°, écart 17.5°) | FEU-07 | extrémité opposée du passage MP-5170 | reoriente |
| `feu_NE_TPC_t3` (R12) | `feu_NE_TPC` | 135.0 → 150.0° (cible 150.0°, écart 15.0°) | FEU-07 | extrémité opposée du passage MP-5191 | reoriente |
| `feu_NE_droite_t2` (R12) | `feu_NE_droite` | 135.0 → 154.6° (cible 154.6°, écart 19.6°) | FEU-07 | extrémité opposée du passage MP-5170 | reoriente |
| `feu_NE_droite_t3` (R11v_rep) | `feu_NE_droite` | 45.0 → 78.9° (cible 78.9°, écart 33.9°) | FEU-06 | premier véhicule arrêté à la ligne MT-8002 (axe de la voie la plus proche) | reoriente |
| `feu_REV_E_pietons_t2` (R13c) | `feu_REV_E_pietons` | 45.0 → 17.9° (cible 17.9°, écart 27.1°) | FEU-09 | cyclistes en attente avant la traversée MP-0001 | reoriente |
| `feu_REV_droite_t3` (R13c) | `feu_REV_droite` | 225.0 → 282.3° (cible 282.3°, écart 57.3°) | FEU-09 | cyclistes en attente avant la traversée MP-0001 | reoriente |
| `feu_REV_droite_t4` (R11v_rep) | `feu_REV_droite` | 330.0 → 352.5° (cible 352.5°, écart 22.5°) | FEU-06 | premier véhicule arrêté à la ligne MT-8004 (axe de la voie la plus proche) | reoriente |
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

Coupes tous les 1 m derrière les bordures à côté bas circulé (`carte/cheminement_coupes.geojson`, classes des surfaces v2 du site complet) : 1579 coupes, 455 sous le seuil, dont 101 hors îlots et terre-pleins (coupe qui ne finit pas sur une autre chaussée) et 80 réduites par un objet (positions résolues). La v1 (classes raster) en comptait 71 sur 1005 : les surfaces v2 bornent le cheminement aux bandes vertes et comptent les îlots ; seule la réduction due à un objet déclenche PMR-01.


## Anomalies de surface (23 objets : l'objet prouvé prime, la surface est à corriger)

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
- `lamp_9514828517` (lampadaire) sur chaussee (classe chaussee, d bordure 7.806 m), preuve mesure : mesure retenue comme nouvel a priori (P3) : fusion_recensement_0.3, σ 0.05 m, 0.70 m de la position source; preuve forte (mesure, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 7.806 m) : îlot, refuge, fosse ou bande plantée absents des surfaces
- `pan_AB4_2` (panneau) sur espace_vert (classe espace_vert, d bordure 3.066 m), preuve mesure : revue : photos 2026 calées : le STOP est sur C, à la pointe NO de l'îlot herbeux (mesure de la fusion PANO2026-015)
- `pan_B6a1_1` (panneau) sur chaussee (classe chaussee, d bordure 7.806 m), preuve mesure : mesure retenue comme nouvel a priori (P3) : fusion_recensement_0.3, σ 0.05 m, 0.68 m de la position source; preuve forte (mesure, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 7.806 m) : îlot, refuge, fosse ou bande plantée absents des surfaces
- `pan_C13a_1` (panneau) sur chaussee (classe chaussee, d bordure 7.806 m), preuve mesure : mesure retenue comme nouvel a priori (P3) : fusion_recensement_0.3, σ 0.05 m, 0.68 m de la position source; preuve forte (mesure, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 7.806 m) : îlot, refuge, fosse ou bande plantée absents des surfaces
- `poteau_bois_REV_ilot` (poteau_reseau) sur chaussee (classe chaussee, d bordure 4.218 m), preuve mesure : mesure retenue comme nouvel a priori (P3) : triangulation_mixte, σ 0.134 m, 0.12 m de la position source; preuve forte (mesure, σ 0.134 m) sur chaussee de classe peu sûre (d bordure 4.218 m) : îlot, refuge, fosse ou bande plantée absents des surfaces
- `poteau_reseau_9742811518` (poteau_reseau) sur bande_cyclable (classe chaussee, d bordure 1.456 m), preuve osm : aucune position admissible et aucune preuve pour trancher; la surface surf_0280 (espace_vert) a été (re)construite en 2025 (limites:gam_bordure ; classe:plan_projet_2025+ortho_2022+lidar_2021) et l'objet n'est prouvé qu'avant les travaux : objet peut-être supp
- `stationnement_velos_8360665117` (stationnement_velos) sur bande_cyclable (classe chaussee, d bordure 1.62 m), preuve osm : aucune position admissible et aucune preuve pour trancher; anomalie collective : 4 objets indépendants (arbre_166, arbre_179, poteau_reseau_9742811518, stationnement_velos_8360665117) en violation physique sur la surface S-0280a (chaussee, classe a_priori:vote

## Propositions d'ajouts et signalements

- `ADD-BTN-MP-5191-a` (tete_feu boitier_bouton_appel, proposition, conf faible) : OSM node/1959022976 button_operated=yes sur le passage MP-5191 : boîtier à 1,0 m sur feu_NE_SE_pietons, face vers le passage
- `ADD-BTN-MP-5191-b` (tete_feu boitier_bouton_appel, proposition, conf faible) : OSM node/1959022976 button_operated=yes sur le passage MP-5191 : boîtier à 1,0 m sur feu_NE_TPC, face vers le passage
- `ADD-ILOT-arbre_397` (ilot_manquant, proposition, conf faible) : objets prouvés (arbre_397) sur la chaussée à plus de 2 m de toute bordure : îlot bordé absent des surfaces ; MNT 2026 surélevé de 0.07 m
- `ADD-ILOT-lamp_12668578865` (ilot_manquant, proposition, conf moyenne) : objets prouvés (lamp_12668578865) sur la chaussée à plus de 2 m de toute bordure : îlot bordé absent des surfaces ; MNT 2026 surélevé de 0.07 m
- `ADD-ILOT-lamp_9514828517` (ilot_manquant, proposition, conf moyenne) : objets prouvés (lamp_9514828517, pan_B6a1_1, pan_C13a_1) sur la chaussée à plus de 2 m de toute bordure : îlot bordé absent des surfaces ; MNT 2026 surélevé de 0.05 m
- `ADD-ILOT-poteau_bois_REV_ilot` (ilot_manquant, proposition, conf moyenne) : objets prouvés (poteau_bois_REV_ilot) sur la chaussée à plus de 2 m de toute bordure : îlot bordé absent des surfaces ; emprise a priori (MNT 2026 : -0.01 m)
- `ADD-SPEC-J5_SO` (hypothese_spec, a_arbitrer, conf faible) : panneaux.json décrit J5_SO (J5), absent de mobilier.geojson
- `ADD-SPEC-M12a_feu_REV_droite` (hypothese_spec, a_arbitrer, conf faible) : panneaux.json place M12a_feu_REV_droite (M12a (probable)) à 0.16 m de feu_REV_droite (même support ?)
- `ADD-SPEC-M12a_ou_AB3a_feu_VERC_droite` (hypothese_spec, a_arbitrer, conf faible) : panneaux.json place M12a_ou_AB3a_feu_VERC_droite (M12a (probable)) à 0.255 m de feu_VERC_droite (même support ?)
- `ADD-SPEC-M9c_acces_NE` (hypothese_spec, a_arbitrer, conf faible) : panneaux.json décrit M9c_acces_NE (M9c), absent de mobilier.geojson
- `ADD-SPEC-M9c_ruisseau` (hypothese_spec, a_arbitrer, conf faible) : panneaux.json place M9c_ruisseau (M9c) à 0.202 m de pan_C114_1 (même support ?)
- `ADD-SPEC-feu_REV_ilot_E` (hypothese_spec, a_arbitrer, conf faible) : feux.json place feu_REV_ilot_E (support_feux) à 0.583 m de pan_D21_1 (même support ?)
- `ADD-SPEC-feu_REV_ilot_axial` (hypothese_spec, a_arbitrer, conf faible) : feux.json place feu_REV_ilot_axial (support_feux) à 0.127 m de poteau_bois_REV_ilot (même support ?)
- `ADD-SPEC-plaque_mat_3150` (hypothese_spec, a_arbitrer, conf faible) : panneaux.json décrit plaque_mat_3150 (plaque de rue), absent de mobilier.geojson
- `ADD-SURF-S-0280a` (surface_a_corriger, proposition, conf faible) : 4 objets de 2 source(s) (arbres/plan2025, mobilier/osm) sur la surface S-0280a classée chaussee (a_priori:vote_indices_classe ; v1 surf_0280 espace_vert) : bande plantée, îlot ou trottoir probable ; à vérifier sur place
- `ADD-SURF-S-0282a` (surface_a_corriger, proposition, conf faible) : 3 objets de 1 source(s) (arbres/plan2025) sur la surface S-0282a classée chaussee (a_priori:vote_indices_classe ; v1 surf_0282 espace_vert) : bande plantée, îlot ou trottoir probable ; à vérifier sur place
- `ADD-SURF-arbre_297` (surface_a_corriger, proposition, conf faible) : arbre levé (arbre_297) sur une chaussée v1 d'origine raster, à plus de 2 m de toute bordure (emprise a priori (MNT 2026 : -0.85 m)) : fosse, bande plantée ou limite de surface à corriger
- `ADD-SURF-arbre_298` (surface_a_corriger, proposition, conf faible) : arbre levé (arbre_298) sur une chaussée v1 d'origine raster, à plus de 2 m de toute bordure (emprise a priori (MNT 2026 : +0.03 m)) : fosse, bande plantée ou limite de surface à corriger
- `ADD-SURF-arbre_398` (surface_a_corriger, proposition, conf faible) : arbre levé (arbre_398) sur une chaussée v1 d'origine raster, à plus de 2 m de toute bordure (emprise a priori (MNT 2026 : -0.23 m)) : fosse, bande plantée ou limite de surface à corriger
- `DISTINCTS-poteau:riv_NE_1-poteau:riv_NE_2` (supports_distincts, signalement, conf moyenne) : supports poteau:riv_NE_1 et poteau:riv_NE_2 à 0.32 m : deux mâts distincts établis par pnx:bb9c05ff (2025-08-31) : 2 mât(s) : jamais fusionnés (P5)
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
- `SPEC-pan_AB3a_2` ↔ `pan_AB3a_2` : écart 7.078 m, azimut 68.0° ; position de la spec légale
- `SPEC-pan_AB3a_3` ↔ `pan_AB3a_3` : écart 4.827 m ; position de la spec illégale (GEN-01, SIG-01)
- `SPEC-pan_AB4_1` ↔ `pan_AB4_2` : écart 1.245 m ; position de la spec illégale (GEN-01, SIG-01)
- `SPEC-pan_B2a_1` ↔ `pan_B2a_1` : écart 7.078 m, azimut 68.0° ; position de la spec légale
- `SPEC-pan_B6a1_1` ↔ `pan_B6a1_1` : écart 0.683 m ; position de la spec légale
- `SPEC-pan_C113_1` ↔ `pan_C113_1` : écart 3.133 m, azimut 160.0° ; position de la spec illégale (GEN-01, SIG-01)
- `SPEC-pan_C114_1` ↔ `pan_C114_1` : écart 0.202 m, azimut 50.0° ; position de la spec légale
- `SPEC-pan_C13a_1` ↔ `pan_C13a_1` : écart 0.683 m ; position de la spec légale
- `SPEC-pan_D21_1` ↔ `pan_D21_1` : écart 0.0 m, azimut 90.0° ; position de la spec illégale (GEN-01, SIG-01, SIG-12)
- `SPEC-pan_D21_2` ↔ `pan_D21_2` : écart 0.0 m, azimut 90.0° ; position de la spec illégale (GEN-01, SIG-01, SIG-12)

## Limites

- Aucune photo du cœur après les travaux 2025 (les 3 photos 2026 calées sont à 130 m au sud) : un objet posé ou déduit pour 2026 au cœur n'est prouvable que par le terrain ; ses corrections restent à confiance faible (a_verifier_terrain2026).
- Les photos à plat du 2025-08-31 ne sont pas calables (aucune voisine acceptée) : elles ne servent qu'aux tests ordinaux.
- Détecteur d'ombres : fiable en travers de l'ombre ; le début de l'ombre est souvent masqué par l'image déversée du mât (lanterne claire) : σ le long de l'ombre ≥ 0,6 m ; erreurs grossières possibles (mât voisin), d'où la corroboration exigée.
- Les flèches levées GAM ne sont jamais déplacées : un écart à MQ-FLE-006 y signale des bords de voie à vérifier.
- P11 à P16 (rangées d'arbres, jalonnement relocalisé, masque du véhicule dans le calage, repère (s, t) hors étendue, statut temporel des arbres GAM, double lecture) ne font pas partie de ce lot ; voir open_issues.
