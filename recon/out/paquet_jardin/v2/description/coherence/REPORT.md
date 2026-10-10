# Solveur de cohérence des objets : « l'objet devait-il être ici, ou plutôt là ? »

Couche séparée, à fusionner par le composeur. Ni le paquet v1 ni la description de base v2 ne sont modifiés.
Commande : `python recon/pcg/decrire/coherence.py` (déterministe ; `--sans-planches` pour l'évaluation seule).

## Méthode

1. **Carte sémantique du site** (raster 5 cm, `carte/`) : classes îlots v2 > surfaces v2 > bâtiments > surfaces_2026 ; zones dérivées (passages, traversées cyclables, îlots peints, voies bus et bandes cyclables, abaissés, paliers, BEV, clôtures) selon `precedence_zones` ; bordures orientées sur tout le site (v2 en zone pilote, GAM/PCRS/plan 2025 dédoublonnées ailleurs) ; voies OpenDRIVE et sens ; largeur libre par coupe perpendiculaire à la bordure. Près d'une bordure (|t| < 1 m), la classe est arbitrée par la bordure levée (côté haut / côté chaussée).
2. **Règles** (`assets/specs/regles_implantation.json`, 66 règles) : surfaces, reculs, relations (ligne d'effet, extrémités de passage, nez d'îlot, fuseau peint), orientation (usagers visés, chaussée éclairée, extrémité opposée du passage), z, cheminement de 1,40 m, collisions et doublons. Politique : critique toujours dure ; majeur dure si σ ≥ 0,5 m ; une règle « vérifier » contraint un objet a priori ; une borne a priori ou une zone dérivée a priori ne s'oppose pas à un objet bien prouvé.
3. **Résolution** : normale à la bordure en s0 puis grille (Δs, Δt), coût J = (Δt/σ)² + 4(Δs/σ)² + termes mous, sans dépasser le déplacement autorisé par la preuve (GAM 0,5 m ; LiDAR 0,75 ; ortho 1,0 ; OSM 2,0 ; a priori 5,0). Sinon arbitrage : anomalie de surface (objet bien prouvé, la surface est fausse), photo, candidat a priori (conf faible), non-instanciation.
4. **Preuves** : planche Panoramax (poses calées, photos valides à la date de l'objet) + ortho 2022 pour chaque correction > 0,3 m ou > 20°, lue par Claude (`revue_coherence.json`) ; triangulation des mâts en désaccord > 0,75 m.

Vue d'ensemble : `carte/apercu_corrections.png` (carte sémantique du cœur, déplacements, retraits, anomalies, ajouts).

## Comptes

| verdict | objets |
|---|---|
| a_verifier | 81 |
| conforme | 479 |
| violation | 60 |

| statut de résolution | objets |
|---|---|
| anomalie_surface | 14 |
| conforme | 510 |
| conforme_signale | 30 |
| corrige | 46 |
| non_instancie_absent_2026 | 10 |
| non_resolu | 4 |
| reoriente | 6 |

| type | conforme | a_verifier | violation |
|---|---|---|---|
| abri_bus | 1 | 1 | 0 |
| arbre | 386 | 63 | 18 |
| armoire | 2 | 0 | 0 |
| balise_J11 | 2 | 0 | 0 |
| banc | 2 | 0 | 0 |
| barriere_levante | 3 | 0 | 0 |
| boite_aux_lettres | 1 | 0 | 0 |
| chicane | 1 | 0 | 0 |
| conteneur_verre | 0 | 1 | 0 |
| corbeille | 2 | 2 | 1 |
| distributeur | 0 | 1 | 1 |
| fontaine | 1 | 0 | 0 |
| lampadaire | 30 | 2 | 10 |
| mat_camera | 0 | 0 | 2 |
| mobilier_publicitaire | 2 | 0 | 0 |
| panneau | 8 | 6 | 14 |
| panneau_information | 3 | 0 | 1 |
| portail | 7 | 0 | 1 |
| poteau_arret | 1 | 0 | 2 |
| poteau_incendie | 1 | 0 | 2 |
| poteau_reseau | 7 | 1 | 0 |
| potelet | 2 | 2 | 4 |
| stationnement_velos | 9 | 0 | 0 |
| support_feux | 7 | 2 | 4 |
| totem_PR | 1 | 0 | 0 |

| zone au point | conforme | a_verifier | violation |
|---|---|---|---|
| - | 10 | 1 | 0 |
| abaisse_traversee | 0 | 1 | 0 |
| acces_riverain | 3 | 1 | 2 |
| autre | 25 | 0 | 0 |
| batiment | 5 | 4 | 1 |
| bev | 0 | 0 | 2 |
| chaussee | 4 | 6 | 9 |
| espace_vert | 292 | 49 | 20 |
| ilot | 2 | 1 | 2 |
| ilot_peint | 2 | 0 | 0 |
| parking | 53 | 7 | 1 |
| piste_cyclable | 0 | 0 | 4 |
| quai_bus | 3 | 2 | 2 |
| terre_plein_vegetal | 8 | 0 | 5 |
| traversee_cyclable | 0 | 0 | 2 |
| trottoir | 72 | 9 | 10 |

Têtes de feux : {'conforme': 15, 'reoriente': 12, 'orientation_signalee': 4}. Corrections : {'deplacement': 45, 'non_instanciation': 4, 'reorientation': 18, 'deplacement+reorientation': 3}. Propositions d'ajouts : {'tete_feu': 2, 'ilot_manquant': 2, 'hypothese_spec': 8, 'surface_a_corriger': 3, 'fusion_supports': 2}.
Objets non instanciés (violation critique non résolue sur surface circulée) : arbre_109, pan_D21_1, pan_D21_2, pan_J5_2.

Violations par règle : BAR-03 3, ECL-01 14, ECL-02 1, ECL-05 2, FEU-01 1, FEU-02 1, FEU-04 2, FEU-07 4, GEN-01 29, GEN-02 3, GEN-03 16, GEN-04 33, GEN-06 8, GEN-08 2, GEN-09 6, MOB-01 1, PMR-01 6, POT-01 6, POT-03 1, RES-02 1, RES-03 2, SIG-01 6, SIG-02 6, SIG-04 11, SIG-05 1, SIG-07 1, SIG-10 3, SIG-12 3, VEG-01 17, VEG-02 33, VEG-03 1, VEG-06 4.

## Les 15 corrections les plus significatives

| # | objet | correction | règles | preuve | revue | planche |
|---|---|---|---|---|---|---|
| 1 | `pan_AB3a_2` (panneau AB3a) + pan_B2a_1, pan_M9_2 | 1.05 m (Δt 1.05, Δs 0.0) ; azimut 342.0 → 50.0° | GEN-01, GEN-03, SIG-01, SIG-02, SIG-04 | panoramax_brut σ 1.5 | corrigee (moyenne) | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_AB3a_2.jpg` |
| 2 | `pan_C113_1` (panneau C113) | azimut 225.0 → 65.0° | SIG-04 | photo_pnp σ 0.1 | origine (moyenne) | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_C113_1.jpg` |
| 3 | `pan_B1_1` (panneau B1) + pan_B2b_1 | azimut 125.0 → 65.0° | SIG-04 | panoramax_brut σ 1.5 | origine (moyenne) | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_B1_1.jpg` |
| 4 | `feu_VERC_O_pietons` (support_feux) | 1.90 m (Δt 0.0, Δs -1.9) | FEU-07, GEN-02 | a_priori σ 2.0 | ambigu (faible) | `recon/out/paquet_jardin/v2/description/coherence/planches/feu_VERC_O_pietons.jpg` |
| 5 | `pan_D21_1` (panneau D21) + pan_D21_2 | non instancié (obsolete_probable, a_verifier_terrain2026) | GEN-01, SIG-01 | lidar2021 σ 0.15 | ambigu (faible) | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_D21_1.jpg` |
| 6 | `pan_J5_2` (panneau J5) | non instancié (a_verifier_terrain2026, obsolete_probable, surface_modifiee_2025) | GEN-01, SIG-01, SIG-10 | constat σ 1.5 | ambigu (faible) | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_J5_2.jpg` |
| 7 | `pan_J5_1` (panneau J5) | 0.50 m (Δt 0.0, Δs 0.5) | SIG-10 | panoramax_brut σ 1.5 | corrigee (moyenne) | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_J5_1.jpg` |
| 8 | `feu_SW_NO_pietons` (support_feux) + feu_SW_NO_pietons_t1 | 1.10 m (Δt 0.0, Δs -1.1) | FEU-07, GEN-02 | plan2025 σ 1.5 | ambigu (faible) | `recon/out/paquet_jardin/v2/description/coherence/planches/feu_SW_NO_pietons.jpg` |
| 9 | `lamp_9665416817` (lampadaire) | 0.65 m (Δt 0.65, Δs 0.0) | ECL-01, GEN-01, GEN-03 | osm σ 1.0 | corrigee (moyenne) | `recon/out/paquet_jardin/v2/description/coherence/planches/lamp_9665416817.jpg` |
| 10 | `pan_B21a1_4` (panneau B21a1) | azimut 10.0 → 341.1° | SIG-04 | plan2025 σ 1.5 | ambigu (faible) | `recon/out/paquet_jardin/v2/description/coherence/planches/pan_B21a1_4.jpg` |
| 11 | `lamp_12668578865` (lampadaire) | 0.45 m | ECL-01, GEN-01 | osm σ 1.0 | corrigee (moyenne) | `recon/out/paquet_jardin/v2/description/coherence/planches/lamp_12668578865.jpg` |
| 12 | `mat_camera_9831317323` (mat_camera) | 0.55 m (Δt 0.55, Δs 0.0) | ECL-01, GEN-01, GEN-03 | osm σ 1.0 | corrigee (moyenne) | `recon/out/paquet_jardin/v2/description/coherence/planches/mat_camera_9831317323.jpg` |
| 13 | `potelet_13827066658` (potelet) | 1.85 m (Δt -1.85, Δs 0.0) | GEN-01, POT-01 | osm σ 1.0 | ambigu (faible) | `recon/out/paquet_jardin/v2/description/coherence/planches/potelet_13827066658.jpg` |
| 14 | `arbre_109` (arbre) | non instancié (a_verifier_terrain2026, surface_modifiee_2025) | GEN-01, VEG-01 | inventaire σ 1.0 | ambigu (faible) | `recon/out/paquet_jardin/v2/description/coherence/planches/arbre_109.jpg` |
| 15 | `arbre_396` (arbre) | 1.85 m (Δt 1.85, Δs 0.0) | GEN-01, GEN-03, VEG-01, VEG-02, VEG-06 | lidar2021_couronne σ 1.0 | ambigu (faible) | `recon/out/paquet_jardin/v2/description/coherence/planches/arbre_396.jpg` |

Justifications :

1. `pan_AB3a_2` : candidat admissible le plus proche (normale, Δt +1.05 m, Δs +0.00 m, J 0.49) dans la limite de la preuve (panoramax_brut, d_max 3.0 m) ; revue photo : position corrigée confirmée (79a18815 (2024-08, 29 m) et eeb2f8f1 (2025-05, 34 m) : un seul mât portant un disque et un triangle (dos gris visibles depuis le SO) sur C, pas sur A (chaussée) ; la position de panneaux.json (S, 46,4 ; 65,1) ne porte aucun panneau ; faces tournées vers le NE (dos vus depuis le SO) : azimut 50° retenu) ; azimut photo de la spec (50°) conforme à la règle (40°) ; couche à 342°
2. `pan_C113_1` : revue photo : position d'origine confirmée (le poteau du C113 est sur A dans les 4 photos (triangulation 8 photos à 0,05 m) ; S (panneaux.json, 3,1 m, dans la piste) rejetée ; face bleue vue depuis le NE (9834f494, 6e97bb8c, e86aa913) et dos vu depuis le SO (5c0d1d39) : la face regarde le NE (65°), pas le SO (225°)) ; azimut photo de la spec (65°) conforme à la règle (48°) ; couche à 225°
3. `pan_B1_1` : revue photo : position d'origine confirmée (mêmes photos : le mât (disque + triangle) est à la position de la couche ; vu de dos depuis le SO, ce qui exclut 125° (on verrait la tranche) : face ≈ 65° ; la position de panneaux.json (S, dans la piste) ne porte rien ; même mât que pan_AB3a_2 corrigé (0,17 m) : fusion proposée) ; azimut photo de la spec (65°) conforme à la règle (41°) ; couche à 125°
4. `feu_VERC_O_pietons` : candidat admissible le plus proche (longitudinal, Δt +0.00 m, Δs -1.90 m, J 3.68) dans la limite de la preuve (a_priori, d_max 5.0 m) ; revue photo ambiguë ou impossible : correction par la règle, confiance faible
5. `pan_D21_1` : preuve antérieure aux travaux 2025 (lidar2021) ; le marquage posé en 2025 MP-0001 (traversee_cyclable, neuf_2025) passe à son emplacement et la surface 2026 y est circulée : objet probablement déposé ou déplacé par les travaux, non instancié
6. `pan_J5_2` : preuve faible, aucune position admissible dans 3.0 m : arbitrage par 5 photo(s) calée(s) ; la surface surf_0323 (chaussee) a été (re)construite en 2025 (limites:gam_bordure ; classe:plan_projet_2025+osm_2026) et l'objet n'est prouvé qu'avant les travaux : objet peut-être supprimé ; violation critique non résolue sur une surface circulée : objet non instancié (resolution.arbitrage.non_instanciation) ; sur le même îlot que pan_D21_1, pan_D21_2 (probablement supprimé par les travaux 2025)
7. `pan_J5_1` : candidat admissible le plus proche (grille, Δt -0.00 m, Δs +0.50 m, J 0.444) dans la limite de la preuve (panoramax_brut, d_max 3.0 m) ; revue photo : position corrigée confirmée (9834f494, e86aa913, e5d79de9 (dos gris), 6e97bb8c : la balise J5 est sur le nez arrondi du TPC NE ; C est plus près de la balise que A dans les 4 photos (la balise est encore ≈ 0,3 m plus près de la pointe) ; la position de panneaux.json (S, 1,5 m au sud) tombe hors de l'îlot : rejetée)
8. `feu_SW_NO_pietons` : candidat admissible le plus proche (longitudinal, Δt +0.00 m, Δs -1.10 m, J 2.151) dans la limite de la preuve (plan2025, d_max 3.0 m) ; revue photo ambiguë ou impossible : correction par la règle, confiance faible
9. `lamp_9665416817` : candidat admissible le plus proche (normale, Δt +0.65 m, Δs +0.00 m, J 0.423) dans la limite de la preuve (osm, d_max 2.0 m) ; revue photo : position corrigée confirmée (e5d79de9 (14 m) : fût exactement sur C ; 6e97bb8c, e540bf1d, 7651c539 (6-10 m) : fût entre A et C, plus près de C ; le candélabre (bannière LANDRI) est derrière la bordure, pas sur l'arête avant (A, t = 0,00 m) ; position réelle ≈ 0,4-0,5 m derrière la bordure)
10. `pan_B21a1_4` : azimut d'une preuve faible à 29° de la règle : affiné
11. `lamp_12668578865` : candidat admissible le plus proche (normale, Δt -0.45 m, Δs +0.00 m, J 0.202) dans la limite de la preuve (osm, d_max 2.0 m) ; revue photo : position corrigée confirmée (ortho 2022 : lanterne (disque clair) et départ de l'ombre du mât à ≈ 0,1 m de C, ≈ 0,5 m de A)
12. `mat_camera_9831317323` : candidat admissible le plus proche (normale, Δt +0.55 m, Δs +0.00 m, J 0.303) dans la limite de la preuve (osm, d_max 2.0 m) ; revue photo : position corrigée confirmée (ortho 2022 : l'ombre du mât part d'un pied plus proche de C que de A (A est sur l'arête avant) ; C est à 0,3 m de lamp_9514825221 : très probablement le même mât (caméra sur candélabre), fusion proposée)
13. `potelet_13827066658` : candidat admissible le plus proche (normale, Δt -1.85 m, Δs +0.00 m, J 3.422) dans la limite de la preuve (osm, d_max 2.0 m) ; aucune position ne satisfait toutes les règles : seules les règles critiques sont imposées, POT-01, POT-03 restent signalées ; revue photo ambiguë ou impossible : correction par la règle, confiance faible
14. `arbre_109` : aucune position admissible et aucune preuve pour trancher ; la surface surf_0321 (piste_cyclable) a été (re)construite en 2025 (limites:gam_bordure ; classe:plan_projet_2025+osm_2026) et l'objet n'est prouvé qu'avant les travaux : objet peut-être supprimé ; violation critique non résolue sur une surface circulée : objet non instancié (resolution.arbitrage.non_instanciation)
15. `arbre_396` : candidat admissible le plus proche (normale, Δt +1.85 m, Δs +0.00 m, J 3.423) dans la limite de la preuve (lidar2021_couronne, d_max 2.0 m) ; revue photo ambiguë ou impossible : correction par la règle, confiance faible

## Têtes de feux (16 réorientées ou signalées sur 31)

| tête | support | azimut | règle | motif | statut |
|---|---|---|---|---|---|
| `feu_NE_TPC_t2` (R12) | `feu_NE_TPC` | 315.0 → 296.1° (cible 296.1°, écart 18.9°) | FEU-07 | extrémité opposée du passage MP-0574 | reoriente |
| `feu_NE_TPC_t3` (R12) | `feu_NE_TPC` | 135.0 → 151.4° (cible 151.4°, écart 16.4°) | FEU-07 | extrémité opposée du passage MP-0580 | reoriente |
| `feu_NE_droite_t2` (R12) | `feu_NE_droite` | 135.0 → 157.2° (cible 157.2°, écart 22.2°) | FEU-07 | extrémité opposée du passage MP-0574 | reoriente |
| `feu_NE_droite_t3` (R11v_rep) | `feu_NE_droite` | 45.0 → 85.8° (cible 85.8°, écart 40.8°) | FEU-06 | premier véhicule arrêté à la ligne MT-0563 (axe de la voie la plus proche) | reoriente |
| `feu_REV_droite_t3` (R13c) | `feu_REV_droite` | 225.0 → 255.0° (cible 255.0°, écart 30.0°) | FEU-09 | cyclistes en attente avant la traversée MP-0272 | reoriente |
| `feu_REV_droite_t4` (R11v_rep) | `feu_REV_droite` | 330.0 → 0.8° (cible 0.8°, écart 30.8°) | FEU-06 | premier véhicule arrêté à la ligne MT-0322 (axe de la voie la plus proche) | reoriente |
| `feu_SW_NO_pietons_t1` (R12) | `feu_SW_NO_pietons` | 135.0 → 117.5° (cible 117.5°, écart 17.5°) | FEU-07 | extrémité opposée du passage MP-0863 | reoriente |
| `feu_SW_TPC_t2` (R12) | `feu_SW_TPC` | 135.0 → 114.4° (cible 114.4°, écart 20.6°) | FEU-07 | extrémité opposée du passage MP-0869 | reoriente |
| `feu_SW_TPC_t3` (R12) | `feu_SW_TPC` | 315.0 → 333.6° (cible 333.6°, écart 18.6°) | FEU-07 | extrémité opposée du passage MP-0863 | reoriente |
| `feu_SW_droite_t2` (R12) | `feu_SW_droite` | 315.0 → 338.0° (cible 338.0°, écart 23.0°) | FEU-07 | extrémité opposée du passage MP-0869 | reoriente |
| `feu_SW_droite_t3` (R11v_rep) | `feu_SW_droite` | 225.0 → 265.1° (cible 265.1°, écart 40.1°) | FEU-06 | premier véhicule arrêté à la ligne MT-0853 (axe de la voie la plus proche) | reoriente |
| `feu_VERC_droite_t1` (R11v) | `feu_VERC_droite` | 172.0 → 172.0° (cible 160.9°, écart 11.1°) | FEU-05 | voie gérée à 40 m en amont de la ligne MT-0436 | orientation_signalee |
| `feu_VERC_droite_t3` (R11v_rep) | `feu_VERC_droite` | 172.0 → 189.0° (cible 189.0°, écart 17.0°) | FEU-06 | premier véhicule arrêté à la ligne MT-0436 (axe de la voie la plus proche) | reoriente |
| `feu_VERC_droite_t4` (AB3a) | `feu_VERC_droite` | 172.0 → 172.0° (cible 160.9°, écart 11.1°) | SIG-08 | voie gérée à 40 m en amont de la ligne MT-0436 | orientation_signalee |
| `feu_VERC_ilot_t1` (R11v) | `feu_VERC_ilot` | 172.0 → 172.0° (cible 152.5°, écart 19.5°) | FEU-05 | voie gérée à 40 m en amont de la ligne MT-0436 | orientation_signalee |
| `feu_VERC_ilot_t2` (R12) | `feu_VERC_ilot` | 59.0 → 59.0° (cible 33.7°, écart 25.3°) | FEU-07 | extrémité opposée du passage MP-0444 | orientation_signalee |

## Cheminement piéton de 1,40 m (PMR-01, 6 objets)

Coupes tous les 1 m le long des trottoirs (`carte/cheminement_coupes.geojson`) : 1005 coupes, 71 sous le seuil (1,40 m contre un mur ou une clôture, 1,20 m sinon), dont 68 réduites par un objet (positions résolues).

- `arbre_020` (arbre) : cheminement réduit à 0.85 m (sans l'objet 1.95 m, limite hors) ; trottoir 1.95 m, objet à t = 0.9 m -> corrige (déplacement 0.5 m)
- `arbre_427` (arbre) : cheminement réduit à 1.15 m (sans l'objet 2.00 m, limite espace_vert) ; trottoir 2.0 m, objet à t = 0.69 m -> corrige (déplacement 0.75 m)
- `distributeur_12321482421` (distributeur) : cheminement réduit à 0.85 m (sans l'objet 1.45 m, limite espace_vert) ; trottoir 3.0 m, objet à t = 1.92 m -> corrige (déplacement 0.35 m)
- `lamp_12894130974` (lampadaire) : cheminement réduit à 1.10 m (sans l'objet 1.75 m, limite espace_vert) ; trottoir 1.75 m, objet à t = 1.23 m -> conforme_signale (déplacement 0.0 m)
- `poteau_NO_0021` (poteau_arret) : cheminement réduit à 1.15 m (sans l'objet 1.45 m, limite espace_vert) ; trottoir 3.0 m, objet à t = 1.14 m -> corrige (déplacement 0.5 m)
- `poteau_REV_ligne42` (poteau_arret) : cheminement réduit à 1.05 m (sans l'objet 2.10 m, limite espace_vert) ; trottoir 2.1 m, objet à t = 1.12 m -> corrige (déplacement 0.25 m)

## Anomalies de surface (14 objets : l'objet prouvé prime, la surface est à corriger)

- `arbre_019` (arbre) sur batiment (classe batiment, d bordure 8.576 m), preuve gam : preuve forte (gam, σ 0.05 m) sur batiment de classe peu sûre (d bordure 8.576 m) : emprise bâtie (BD TOPO / OSM) trop large ou arbre de cour
- `arbre_034` (arbre) sur batiment (classe batiment, d bordure 7.855 m), preuve gam : preuve forte (gam, σ 0.05 m) sur batiment de classe peu sûre (d bordure 7.855 m) : emprise bâtie (BD TOPO / OSM) trop large ou arbre de cour
- `arbre_188` (arbre) sur batiment (classe batiment, d bordure 4.872 m), preuve gam : preuve forte (gam, σ 0.05 m) sur batiment de classe peu sûre (d bordure 4.872 m) : emprise bâtie (BD TOPO / OSM) trop large ou arbre de cour
- `arbre_189` (arbre) sur batiment (classe batiment, d bordure 6.443 m), preuve gam : preuve forte (gam, σ 0.05 m) sur batiment de classe peu sûre (d bordure 6.443 m) : emprise bâtie (BD TOPO / OSM) trop large ou arbre de cour
- `arbre_297` (arbre) sur chaussee (classe chaussee, d bordure 4.451 m), preuve gam : preuve forte (gam, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 4.451 m) : îlot, refuge, fosse ou bande plantée absents des surfaces
- `arbre_298` (arbre) sur chaussee (classe chaussee, d bordure 3.281 m), preuve gam : preuve forte (gam, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 3.281 m) : îlot, refuge, fosse ou bande plantée absents des surfaces
- `arbre_364` (arbre) sur acces_riverain (classe acces_riverain, d bordure 1.402 m), preuve gam : preuve forte (gam, σ 0.05 m) sur acces_riverain de classe peu sûre (d bordure 1.402 m) : bande plantée ou limite d'accès mal placée
- `arbre_397` (arbre) sur chaussee (classe chaussee, d bordure 2.437 m), preuve gam : preuve forte (gam, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 2.437 m) : îlot, refuge, fosse ou bande plantée absents des surfaces
- `arbre_398` (arbre) sur chaussee (classe chaussee, d bordure 2.187 m), preuve gam : preuve forte (gam, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 2.187 m) : îlot, refuge, fosse ou bande plantée absents des surfaces
- `arbre_426` (arbre) sur parking (classe parking, d bordure 5.117 m), preuve gam : preuve forte (gam, σ 0.05 m) sur parking de classe peu sûre (d bordure 5.117 m) : fosse ou terre-plein de parking absent des surfaces
- `corbeille_12328578845` (corbeille) sur espace_vert (classe espace_vert, d bordure 8.321 m), preuve osm : revue photo : ortho 2022 : petit objet clair (corbeille probable) en A, au bord du parking, à côté des conteneurs ; la limite raster de la surface est approximative
- `feu_REV_E_pietons` (support_feux) sur abaisse_traversee (classe trottoir, d bordure 0.696 m), preuve photo_pnp : revue photo : mât de la tête R12 exactement sur A dans 4 photos, à l'angle du passage et de la bordure : c'est la zone d'abaissé dérivée (profondeur a priori 1,20 m) qui est trop profonde à cet endroit
- `poteau_bois_REV_ilot` (poteau_reseau) sur chaussee (classe chaussee, d bordure 4.106 m), preuve photo_pnp : revue photo : poteau bois sans tête de feu sur un petit îlot surélevé (2024-08, 2025-05) ; feux.json « feu_REV_ilot_axial » est ce poteau (rejeté) ; l'îlot est absent du levé GAM 2026 et des surfaces : état 2026 à vérifier sur place
- `potelet_REV_3` (potelet) sur chaussee (classe chaussee, d bordure 0.386 m), preuve constat : revue photo : ortho 2022 : tête blanche du potelet visible exactement en A, au bord de la traversée de la Revirée ; la classe « chaussée » v1 (limite raster) est fausse à cet endroit

## Propositions d'ajouts

- `ADD-BTN-MP-0580-a` (tete_feu boitier_bouton_appel, proposition, conf faible) : OSM node/1959022976 button_operated=yes sur le passage MP-0580 : boîtier à 1,0 m sur feu_NE_SE_pietons, face vers le passage
- `ADD-BTN-MP-0580-b` (tete_feu boitier_bouton_appel, proposition, conf faible) : OSM node/1959022976 button_operated=yes sur le passage MP-0580 : boîtier à 1,0 m sur feu_NE_TPC, face vers le passage
- `ADD-ILOT-arbre_397` (ilot_manquant, proposition, conf faible) : objets prouvés (arbre_397) sur la chaussée à plus de 2 m de toute bordure : îlot bordé absent des surfaces ; MNT 2026 surélevé de 0.07 m
- `ADD-ILOT-poteau_bois_REV_ilot` (ilot_manquant, proposition, conf moyenne) : objets prouvés (poteau_bois_REV_ilot) sur la chaussée à plus de 2 m de toute bordure : îlot bordé absent des surfaces ; emprise a priori (MNT 2026 : -0.01 m)
- `ADD-SPEC-J5_SO` (hypothese_spec, a_arbitrer, conf faible) : panneaux.json décrit J5_SO (J5), absent de mobilier.geojson
- `ADD-SPEC-M12a_feu_REV_droite` (hypothese_spec, fusionne, conf moyenne) : panneaux.json place M12a_feu_REV_droite (M12a (probable)) à 0.0 m de feu_REV_droite (même support ?)
- `ADD-SPEC-M12a_ou_AB3a_feu_VERC_droite` (hypothese_spec, fusionne, conf moyenne) : panneaux.json place M12a_ou_AB3a_feu_VERC_droite (M12a (probable)) à 0.0 m de feu_VERC_droite (même support ?)
- `ADD-SPEC-M9c_acces_NE` (hypothese_spec, rejete, conf moyenne) : panneaux.json décrit M9c_acces_NE (M9c), absent de mobilier.geojson
- `ADD-SPEC-M9c_ruisseau` (hypothese_spec, fusionne, conf moyenne) : panneaux.json place M9c_ruisseau (M9c) à 0.531 m de lamp_12894130974 (même support ?)
- `ADD-SPEC-feu_REV_ilot_E` (hypothese_spec, ambigu, conf moyenne) : feux.json place feu_REV_ilot_E (support_feux) à 0.583 m de pan_D21_1 (même support ?)
- `ADD-SPEC-feu_REV_ilot_axial` (hypothese_spec, rejete, conf moyenne) : feux.json place feu_REV_ilot_axial (support_feux) à 0.054 m de poteau_bois_REV_ilot (même support ?)
- `ADD-SPEC-plaque_mat_3150` (hypothese_spec, a_arbitrer, conf faible) : panneaux.json décrit plaque_mat_3150 (plaque de rue), absent de mobilier.geojson
- `ADD-SURF-arbre_297` (surface_a_corriger, proposition, conf faible) : arbre levé (arbre_297) sur une chaussée v1 d'origine raster, à plus de 2 m de toute bordure (emprise a priori (MNT 2026 : -0.85 m)) : fosse, bande plantée ou limite de surface à corriger
- `ADD-SURF-arbre_298` (surface_a_corriger, proposition, conf faible) : arbre levé (arbre_298) sur une chaussée v1 d'origine raster, à plus de 2 m de toute bordure (emprise a priori (MNT 2026 : +0.03 m)) : fosse, bande plantée ou limite de surface à corriger
- `ADD-SURF-arbre_398` (surface_a_corriger, proposition, conf faible) : arbre levé (arbre_398) sur une chaussée v1 d'origine raster, à plus de 2 m de toute bordure (emprise a priori (MNT 2026 : -0.23 m)) : fosse, bande plantée ou limite de surface à corriger
- `FUS-lamp_9514825221-mat_camera_9831317323` (fusion_supports, proposition, conf moyenne) : supports lamp_9514825221 (lampadaire) et mat_camera_9831317323 (mat_camera) à 0.32 m l'un de l'autre après résolution : très probablement un seul mât (GEN-06) ; fusionner les éléments portés sur un support
- `FUS-poteau:riv_NE_1-poteau:riv_NE_2` (fusion_supports, proposition, conf moyenne) : supports poteau:riv_NE_1 (panneau) et poteau:riv_NE_2 (panneau) à 0.17 m l'un de l'autre après résolution : très probablement un seul mât (GEN-06) ; fusionner les éléments portés sur un support

## Conflits avec feux.json / panneaux.json

- `SPEC-B1_acces_NE` ↔ `pan_B1_1` : écart 4.442 m, azimut 60.0° ; position de la spec illégale (GEN-01, GEN-03, SIG-01, SIG-02)
- `SPEC-B21a1_ilot_D_centre` ↔ `pan_B21a1_1` : écart 0.56 m, azimut 15.0° ; position de la spec légale
- `SPEC-B2b_acces_NE` ↔ `pan_B2b_1` : écart 4.442 m, azimut 60.0° ; position de la spec illégale (GEN-01, GEN-03, SIG-01, SIG-02)
- `SPEC-J5_nez_TPC_NE` ↔ `pan_J5_1` : écart 1.494 m ; position de la spec illégale (GEN-01, GEN-03, SIG-01, SIG-02, SIG-10)
- `SPEC-feu_SW_cycles_SE` ↔ `feu_SW_cycles_SE` : écart 3.139 m ; position de la spec illégale (GEN-01)
- `SPEC-feu_VERC_O_pietons` ↔ `feu_VERC_O_pietons` : écart 0.3 m ; position de la spec illégale (FEU-07, GEN-02)
- `SPEC-pan_A17_1` ↔ `pan_A17_1` : écart 1.523 m ; position de la spec illégale (GEN-01, SIG-01)
- `SPEC-pan_AB3a_1` ↔ `pan_AB3a_1` : écart 0.531 m, azimut 50.0° ; position de la spec légale
- `SPEC-pan_AB3a_2` ↔ `pan_AB3a_2` : écart 6.699 m, azimut 68.0° ; position de la spec légale
- `SPEC-pan_AB3a_3` ↔ `pan_AB3a_3` : écart 1.513 m ; position de la spec illégale (GEN-01, SIG-01)
- `SPEC-pan_AB4_1` ↔ `pan_AB4_2` : écart 0.7 m ; position de la spec illégale (GEN-01, SIG-01)
- `SPEC-pan_B2a_1` ↔ `pan_B2a_1` : écart 6.699 m, azimut 68.0° ; position de la spec légale
- `SPEC-pan_C113_1` ↔ `pan_C113_1` : écart 3.127 m, azimut 160.0° ; position de la spec illégale (GEN-01, SIG-01)
- `SPEC-pan_C114_1` ↔ `pan_C114_1` : écart 0.531 m, azimut 50.0° ; position de la spec légale
- `SPEC-pan_D21_1` ↔ `pan_D21_1` : écart 0.0 m, azimut 90.0° ; position de la spec illégale (GEN-01, SIG-01)
- `SPEC-pan_D21_2` ↔ `pan_D21_2` : écart 0.0 m, azimut 90.0° ; position de la spec illégale (GEN-01, SIG-01)

## Limites

- Aucune photo du cœur après les travaux 2025 : un objet posé ou déduit pour 2026 ne peut être prouvé par photo ; ses corrections restent à confiance faible (drapeau a_verifier_terrain2026).
- 13 photos calées (2024-08 et 2025-05), toutes le long de l'avenue de Verdun : au-delà de 25-30 m de cet axe, seule l'ortho 2022 sert de preuve visuelle.
- Zones dérivées a priori (profondeur de rampe 1,20 m, BEV 0,50-0,90 m hors zone pilote) : elles ne s'opposent pas aux objets bien prouvés.
- Les classes de surface v1 d'origine raster sont peu sûres ; la bordure levée les arbitre à moins de 1 m.
