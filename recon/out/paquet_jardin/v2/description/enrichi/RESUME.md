# Fusion du recensement : couche `description/enrichi/`

Générateur : `python recon/pcg/enrichir/fusion_recensement.py` (fusion_recensement/0.1), déterministe. Couche séparée : ni la description de base, ni la cohérence, ni les observations ne sont modifiées. Le composeur la fusionnera (priorité arbitré > enrichi vérifié > base).

## Entrées

| fichier | observations |
|---|---|
| `recon/out/paquet_jardin/v2/enrichi/recensement/obs_ortho_A.json` | 200 |
| `recon/out/paquet_jardin/v2/enrichi/recensement/obs_ortho_B.json` | 424 |
| `recon/out/paquet_jardin/v2/enrichi/recensement/obs_pano_0.json` | 61 |
| `recon/out/paquet_jardin/v2/enrichi/recensement/obs_pano_1.json` | 90 |
| `recon/out/paquet_jardin/v2/enrichi/recensement/obs_pano_2.json` | 60 |
| `recon/out/paquet_jardin/v2/enrichi/recensement/web/obs_web.json` | 34 |

Total : 869 observations. Description lue : base v0.3 (`base/`), objets du paquet, instances, bordures du site (carte de cohérence), surfaces v1, corrections et propositions de cohérence, levé GAM 2026 des arbres. Les empreintes SHA-256 de toutes les entrées sont dans `observations_index.json` (`meta.entrees`).

## Synthèse

- 633 entités de la description reçoivent au moins une observation ; 59 ont au moins un attribut corrigé (79 mises à jour).
- Position : 14 corrections mesurées, dont 7 à appliquer et 7 en revue (règles FUS-POS-05/06).
- Existence : 22 entités à retirer ou absentes en 2026 (surtout des lignes de parking détectées à tort sur l'ortho 2022).
- Ajouts : 178 objets nouveaux, dont 116 instanciables (tampons, avaloirs, marquages de stationnement, haies, massifs, blocs rocheux...).
- Conflits : 81 (42 à vérifier, 39 pour information).
- Cohérence : 26 corrections du solveur ont une preuve image ; corrobore_avant_travaux 1, indifferent 1, non_conclu_sans_mesure 14, non_contredit 4, partiel 3.

## Comptes par classe

Une entité compte une fois par colonne. « confirmées » : présence ou position confirmée sans correction. « non valables 2026 » : entités vues seulement sur des images antérieures à leur forme 2026.

| classe | entités vues | confirmées | attribut corrigé | position corrigée (appliquer) | absentes / à retirer | non valables 2026 | ajouts (instanciés) | avec conflit |
|---|---|---|---|---|---|---|---|---|
| arbre | 267 | 169 | 23 | 1 (0) | 0 | 42 | 14 (10) | 9 |
| haie_massif | 0 | 0 | 0 | 0 (0) | 0 | 0 | 9 (7) | 2 |
| marquage | 201 | 137 | 9 | 0 (0) | 22 | 26 | 42 (30) | 15 |
| bordure | 27 | 15 | 0 | 1 (0) | 0 | 2 | 0 (0) | 10 |
| surface_ilot | 35 | 17 | 9 | 0 (0) | 0 | 9 | 4 (4) | 3 |
| ponctuel_sol | 1 | 1 | 0 | 0 (0) | 0 | 0 | 67 (49) | 12 |
| candelabre_poteau | 42 | 19 | 10 | 8 (6) | 0 | 3 | 5 (3) | 10 |
| panneau | 24 | 11 | 6 | 1 (1) | 0 | 1 | 5 (3) | 3 |
| feu | 9 | 6 | 0 | 0 (0) | 0 | 3 | 2 (0) | 1 |
| potelet_borne | 13 | 7 | 2 | 1 (0) | 0 | 2 | 2 (0) | 1 |
| cloture_barriere | 7 | 3 | 0 | 0 (0) | 0 | 0 | 2 (2) | 6 |
| mobilier | 7 | 5 | 0 | 2 (0) | 0 | 0 | 17 (8) | 4 |
| autre | 0 | 0 | 0 | 0 (0) | 0 | 0 | 9 (0) | 2 |
| **total** | 633 | 390 | 59 | 14 (7) | 22 | 88 | 178 (116) | 78 |

## Couverture : preuve image la plus récente valable 2026, par classe

Entités de la description (base v0.3 + objets du paquet). « non valable » : vue seulement avant sa forme 2026 (chantier 2022, zone refaite 2025). Aucune image n'est postérieure au 31/08/2025.

| classe | entités décrites | photo 2025 | photo 2020-2024 | ortho 2022 | web seul | non valable 2026 | sans preuve |
|---|---|---|---|---|---|---|---|
| arbre | 467 | 12 | 20 | 182 | 11 | 42 | 200 |
| marquage | 401 | 7 | 2 | 163 | 2 | 26 | 201 |
| bordure | 510 | 1 | 0 | 24 | 0 | 2 | 483 |
| surface_ilot | 1594 | 3 | 4 | 15 | 3 | 9 | 1560 |
| ponctuel_sol | 12 | 1 | 0 | 0 | 0 | 0 | 11 |
| candelabre_poteau | 52 | 16 | 0 | 23 | 0 | 3 | 10 |
| panneau | 33 | 17 | 1 | 5 | 0 | 1 | 9 |
| feu | 13 | 2 | 2 | 0 | 0 | 3 | 6 |
| potelet_borne | 13 | 2 | 0 | 9 | 0 | 2 | 0 |
| cloture_barriere | 63 | 1 | 1 | 5 | 0 | 0 | 56 |
| mobilier | 30 | 2 | 1 | 3 | 1 | 0 | 23 |
| **total** | 3188 | 64 | 31 | 429 | 17 | 88 | 2559 |

Rôle des observations : ajout 180, contexte 36, entite 648, non_apparie 3, temporaire 2. « contexte » et « temporaire » ne sont jamais fusionnés (FUS-CTX-01, FUS-TMP-01) ; « non_apparie » : observations sans lien ni candidat (voir l'index).

Attributs mis à jour : essence 18, materiau_id 9, hauteur_m 8, couleur_mat 7, type 6, couronne_m 4, azimut_deg 3, nb_lanternes 3, usure 3, bouton_appel 2, diametre_m 2, largeur_m 2, modulation 2, nb_crosses 2, porte_a_faux_m 2, signal_sonore 2, vibreur 2, classe 1, etat 1.

## Contrôle croisé avec la cohérence (`coherence/corrections.geojson`)

26 corrections de cohérence ont une preuve image. Positions : corrobore_avant_travaux 1, indifferent 1, non_conclu_sans_mesure 14, non_contredit 4, partiel 3. Azimuts : accord 3 (FUS-COH-01).

| entité | cohérence | verdict image | écart image / corrigé | écart image / origine | obs |
|---|---|---|---|---|---|
| `ADD-BTN-MP-0580-b` | proposition_ajout  m | corrobore_avant_travaux |  |  | VISION-PANORAMAX-2-31 |
| `arbre_020` | deplacement 0.5 m | non_conclu_sans_mesure |  |  | ORTHO-B-214 |
| `arbre_063` | deplacement 0.05 m | non_conclu_sans_mesure |  |  | ORTHO_A-0048 |
| `arbre_109` | non_instanciation  m | non_contredit |  |  | ORTHO-B-240 |
| `arbre_173` | deplacement 0.85 m | non_conclu_sans_mesure |  |  | ORTHO-B-347 |
| `arbre_302` | deplacement 0.55 m | non_conclu_sans_mesure |  |  | ORTHO-B-228 |
| `arbre_385` | deplacement 0.05 m | non_conclu_sans_mesure |  |  | ORTHO-B-324 |
| `arbre_427` | deplacement 0.75 m | non_conclu_sans_mesure |  |  | ORTHO-B-262 |
| `lamp_12668578865` | deplacement 0.45 m | non_conclu_sans_mesure |  |  | ORTHO-B-188 |
| `lamp_9514795718` | deplacement 0.05 m | non_conclu_sans_mesure |  |  | ORTHO-B-204 |
| `lamp_9514828418` | deplacement 0.05 m | non_conclu_sans_mesure |  |  | ORTHO-B-167 |
| `lamp_9514828820` | deplacement 0.05 m | non_conclu_sans_mesure |  |  | ORTHO-B-135 |
| `lamp_9665416617` | deplacement 0.05 m | non_conclu_sans_mesure |  |  | ORTHO_A-0188 |
| `lamp_9665416717` | deplacement 0.1 m | partiel | 0.837 | 0.876 | ORTHO_A-0167 |
| `lamp_9665416817` | deplacement 0.65 m | partiel | 0.436 | 0.581 | VISION-PANORAMAX-1-55, VISION-PANORAMAX-2-57 |
| `mat_camera_SW_TPC` | deplacement 0.05 m | partiel | 1.583 | 1.59 | pano_0-47 |
| `pan_B1_1` | reorientation  m |  ; azimut accord (45.0° / 65.0°) |  |  |  |
| `pan_B2a_1` | deplacement+reorientation 1.05 m |  ; azimut accord (45.0° / 50.0°) |  |  |  |
| `pan_C113_1` | reorientation  m |  ; azimut accord (55.0° / 65.0°) |  |  |  |
| `pan_D21_1` | non_instanciation  m | non_contredit |  |  | pano_0-3, pano_0-39 |
| `pan_D21_2` | non_instanciation  m | non_contredit |  |  | VISION-PANORAMAX-2-23, pano_0-23 |
| `pan_J5_1` | deplacement 0.5 m | indifferent | 0.25 | 0.668 | VISION-PANORAMAX-2-27, VISION-PANORAMAX-2-5 |
| `pan_J5_2` | non_instanciation  m | non_contredit |  |  | pano_0-4 |
| `poteau_REV_ligne42` | deplacement 0.25 m | non_conclu_sans_mesure |  |  | DOC-LOCALE-009 |
| `potelet_REV_1` | deplacement 0.15 m | non_conclu_sans_mesure |  |  | ORTHO-B-106 |
| `potelet_REV_2` | deplacement 0.15 m | non_conclu_sans_mesure |  |  | ORTHO-B-107 |

## Corrections de position

| entité | nature | d (m) | σ (m) | décision | méthodes | obs | raisons |
|---|---|---|---|---|---|---|---|
| `pan_AB4_2` | deplacement | 3.796 | 0.312 | appliquer | pixel_ortho | ORTHO-B-123 |  |
| `poteau_reseau_12888056356` | deplacement | 3.29 | 0.4 | appliquer | triangulation | pano_0-20 |  |
| `lamp_12668620636` | deplacement | 1.826 | 0.188 | appliquer | pixel_ortho | ORTHO-B-209 |  |
| `poteau_reseau_12888048898` | deplacement | 1.814 | 0.35 | appliquer | triangulation | pano_0-21 |  |
| `lamp_9530354517` | deplacement | 1.2 | 0.188 | appliquer | pixel_ortho | ORTHO-B-109 |  |
| `lamp_9665416717` | deplacement | 0.876 | 0.25 | appliquer | pixel_ortho | ORTHO_A-0167 |  |
| `lamp_9665416817` | affinage | 0.581 | 0.083 | appliquer | triangulation | VISION-PANORAMAX-1-55, VISION-PANORAMAX-2-57 |  |
| `arbre_224` | deplacement | 7.619 | 2.4 | revue_requise | triangulation | VISION-PANORAMAX-2-13 | σ fusion 2.40 m > 0,5 m; σ fusion 2.40 m > preuve de la description (0.05 m); objet levé GAM : déplacement > 0,5 m (FUS-POS-06) |
| `banc_8360664518` | deplacement | 4.474 | 0.375 | revue_requise | pixel_ortho | ORTHO_A-0100 | aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines) |
| `potelet_12462947806` | deplacement | 1.969 | 0.375 | revue_requise | pixel_ortho | ORTHO_A-0081 | une seule source non triangulée et pas de correction affirmée |
| `mat_camera_SW_TPC` | deplacement | 1.59 | 0.25 | revue_requise | triangulation | pano_0-47 | aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines) |
| `armoire_1313238971` | deplacement | 1.044 | 0.188 | revue_requise | pixel_ortho | ORTHO-B-171 | une seule source non triangulée et pas de correction affirmée |
| `K-0227` | translation | 0.868 | 0.188 | revue_requise | pixel_ortho | ORTHO_A-0019 | géométrie levée GAM : translation > 0,5 m (FUS-POS-06) |
| `lamp_lidar_VERC_E` | deplacement | 0.772 | 0.15 | revue_requise | triangulation | VISION-PANORAMAX-2-2 | aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines) |

## Existence : entités absentes en 2026 ou à retirer

- `MF-0286` (fleche) : **retirer** ; obs ORTHO-B-102
- `ML-0102` (ligne) : **retirer** ; obs ORTHO_A-0008
- `ML-0106` (ligne) : **retirer** ; obs ORTHO_A-0009
- `ML-0107` (ligne) : **retirer** ; obs ORTHO-B-211
- `ML-0112` (ligne) : **retirer** ; obs ORTHO_A-0068
- `ML-0121` (ligne) : **retirer** ; obs ORTHO_A-0084
- `ML-0131` (ligne) : **retirer** ; obs ORTHO_A-0051
- `ML-0132` (ligne) : **retirer** ; obs ORTHO_A-0052
- `ML-0133` (ligne) : **retirer** ; obs ORTHO_A-0053
- `ML-0135` (ligne) : **retirer** ; obs ORTHO_A-0054
- `ML-0148` (ligne) : **retirer** ; obs ORTHO_A-0092
- `ML-0150` (ligne) : **retirer** ; obs ORTHO_A-0093
- `ML-0151` (ligne) : **retirer** ; obs ORTHO_A-0094
- `ML-0161` (ligne) : **retirer** ; obs ORTHO_A-0106
- `ML-0162` (ligne) : **retirer** ; obs ORTHO_A-0107
- `ML-0163` (ligne) : **retirer** ; obs ORTHO_A-0108
- `ML-0168` (ligne) : **retirer** ; obs ORTHO_A-0109
- `ML-0201` (ligne) : **retirer** ; obs ORTHO_A-0010
- `ML-0202` (ligne) : **absent_2026** ; obs ORTHO-B-208
- `ML-0225` (ligne) : **retirer** ; obs ORTHO_A-0095
- `ML-0226` (ligne) : **retirer** ; obs ORTHO_A-0096
- `ML-0930` (ligne) : **retirer** ; obs ORTHO-B-206

## Ajouts

178 objets nouveaux (groupes d'observations), dont 116 instanciables. Par classe (instanciés / candidats) : arbre 10/4, autre 0/9, avaloir 9/1, candelabre 3/2, cloture 2/0, feu 0/2, haie 4/2, marquage 30/12, massif 3/0, mobilier 8/9, panneau 3/2, potelet 0/2, surface 4/0, tampon 40/17.

| id | classe | sous-types | famille cible | valide 2026 | instancier | obs |
|---|---|---|---|---|---|---|
| `ENR-ARB-001` | arbre | jeunes_arbres_alignement | vegetation.arbres | True | oui | ORTHO_A-0004 |
| `ENR-ARB-002` | arbre | arbre_inventaire_metropole | vegetation.arbres | True | non : aucune observation valide 2026 en confiance ≥ moyenne | DOC-LOCALE-034 |
| `ENR-ARB-003` | arbre | arbustes_conifères | vegetation.arbres | True | oui | ORTHO_A-0045 |
| `ENR-ARB-004` | arbre | petit_arbre | vegetation.arbres | True | oui | ORTHO_A-0090 |
| `ENR-ARB-005` | arbre | souche_ou_massif | vegetation.arbres | True | oui | ORTHO_A-0120 |
| `ENR-ARB-006` | arbre | grand_feuillu | vegetation.arbres | True | oui | ORTHO_A-0119 |
| `ENR-ARB-007` | arbre | petit_arbre_fleuri | vegetation.arbres | True | oui | ORTHO-B-042 |
| `ENR-ARB-008` | arbre | petit_arbre_fleuri | vegetation.arbres | True | oui | ORTHO-B-041 |
| `ENR-ARB-009` | arbre | feuillu | vegetation.arbres | True | oui | ORTHO_A-0153 |
| `ENR-ARB-010` | arbre | feuillage_pourpre | vegetation.arbres | True | oui | ORTHO_A-0152 |
| `ENR-ARB-011` | arbre | arbustes_boules | vegetation.arbres | True | oui | ORTHO_A-0154 |
| `ENR-ARB-012` | arbre | arbre_inventaire_metropole | vegetation.arbres | True | non : aucune observation valide 2026 en confiance ≥ moyenne | DOC-LOCALE-024 |
| `ENR-ARB-013` | arbre | arbre_inventaire_metropole | vegetation.arbres | True | non : aucune observation valide 2026 en confiance ≥ moyenne | DOC-LOCALE-025 |
| `ENR-ARB-014` | arbre | arbre_inventaire_metropole | vegetation.arbres | True | non : aucune observation valide 2026 en confiance ≥ moyenne | DOC-LOCALE-032 |
| `ENR-AUT-001` | autre | objet_vertical_blanc | - | True | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | ORTHO_A-0044 |
| `ENR-AUT-002` | autre | cables_transversaux | - | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | VISION-PANORAMAX-1-73 |
| `ENR-AUT-003` | autre | portique_entree | - | True | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | pano_0-18 |
| `ENR-AUT-004` | autre | escalier_garde_corps | - | True | non : famille cible inexistante dans la description | ORTHO_A-0131 |
| `ENR-AUT-005` | autre | aire_de_jeux | - | True | non : famille cible inexistante dans la description | ORTHO_A-0157 |
| `ENR-AUT-006` | autre | objet_blanc_bas | - | True | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description; observations « incertain » seulement | ORTHO-B-029 |
| `ENR-AUT-007` | autre | ligne_sombre_continue | - | True | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | ORTHO-B-004 |
| `ENR-AUT-008` | autre | coffret_maconne | - | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | VISION-PANORAMAX-2-36 |
| `ENR-AUT-009` | autre | anneaux_sombres_pelouse | - | True | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | ORTHO_A-0180 |
| `ENR-CLO-001` | cloture | grillages_tennis | mobilier.cloture | True | oui | ORTHO_A-0018 |
| `ENR-CLO-002` | cloture | portail_coulissant | mobilier.cloture | True | oui | ORTHO_A-0110 |
| `ENR-FEU-001` | feu | support_pietons_R12_bouton | signaux.feux | False | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | pano_0-52 |
| `ENR-FEU-002` | feu | boitier_appel_pietons | signaux.feux | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | VISION-PANORAMAX-2-31 |
| `ENR-MAR-001` | marquage | hachures | marquages | True | oui | ORTHO_A-0002 |
| `ENR-MAR-002` | marquage | bande_centrale_hachuree | marquages | True | oui | ORTHO_A-0005 |
| `ENR-MAR-003` | marquage | places_parking | marquages | True | oui | ORTHO_A-0006 |
| `ENR-MAR-004` | marquage | places_parking | marquages | True | oui | ORTHO_A-0025 |
| `ENR-MAR-005` | marquage | t_stationnement | marquages | True | oui | ORTHO_A-0033 |
| `ENR-MAR-006` | marquage | damier | marquages | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0028 |
| `ENR-MAR-007` | marquage | hachures | marquages | True | oui | ORTHO_A-0036 |
| `ENR-MAR-008` | marquage | hachures | marquages | True | oui | ORTHO_A-0035 |
| `ENR-MAR-009` | marquage | pictogrammes_pmr_bleus | marquages | True | oui | ORTHO_A-0066 |
| `ENR-MAR-010` | marquage | places_parking_jardinerie_o | marquages | True | oui | ORTHO_A-0067 |
| `ENR-MAR-011` | marquage | lignes_stationnement | marquages | True | oui | ORTHO_A-0034 |
| `ENR-MAR-012` | marquage | places_en_epi_contre_allee | marquages | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-154 |
| `ENR-MAR-013` | marquage | ligne_discontinue_stationnement | marquages | True | oui | ORTHO_A-0041 |
| `ENR-MAR-014` | marquage | damier | marquages | False | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0099 |
| `ENR-MAR-015` | marquage | ligne_place_stationnement | marquages | True | oui | ORTHO-B-059 |
| `ENR-MAR-016` | marquage | logo_velo_piste | marquages | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0101 |
| `ENR-MAR-017` | marquage | ilot_peint_ocre | marquages | True | oui | ORTHO-B-100 |
| `ENR-MAR-018` | marquage | ligne_place_stationnement | marquages | True | oui | ORTHO-B-060 |
| `ENR-MAR-019` | marquage | ligne_place_stationnement | marquages | True | oui | ORTHO-B-058 |
| `ENR-MAR-020` | marquage | ligne_place_stationnement | marquages | True | oui | ORTHO-B-057 |
| `ENR-MAR-021` | marquage | ligne_place_stationnement | marquages | True | oui | ORTHO-B-056 |
| `ENR-MAR-022` | marquage | ilot_peint_ocre | marquages | True | oui | ORTHO-B-101 |
| `ENR-MAR-023` | marquage | lignes_places_terrasse | marquages | True | oui | ORTHO-B-142 |
| `ENR-MAR-024` | marquage | ligne_place_stationnement | marquages | True | oui | ORTHO-B-053 |
| `ENR-MAR-025` | marquage | ligne_place_stationnement | marquages | True | oui | ORTHO-B-052 |
| `ENR-MAR-026` | marquage | ligne_place_stationnement | marquages | True | oui | ORTHO-B-054 |
| `ENR-MAR-027` | marquage | ligne_place_stationnement | marquages | True | oui | ORTHO-B-055 |
| `ENR-MAR-028` | marquage | ligne_place_stationnement | marquages | True | oui | ORTHO-B-051 |
| `ENR-MAR-029` | marquage | places_parking_jardinerie | marquages | True | oui | ORTHO_A-0111 |
| `ENR-MAR-030` | marquage | lignes_stationnement_parking | marquages | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0102 |
| `ENR-MAR-031` | marquage | zigzag_arret_ancien | marquages | False | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | ORTHO-B-085 |
| `ENR-MAR-032` | marquage | zone_jaune_croix | marquages | True | oui | ORTHO_A-0126 |
| `ENR-MAR-033` | marquage | traversee_cyclable_verte | marquages | False | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | pano_0-46 |
| `ENR-MAR-034` | marquage | chiffre_vitesse_50 | marquages | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | pano_0-45 |
| `ENR-MAR-035` | marquage | ligne_place_stationnement | marquages | True | oui | ORTHO-B-081 |
| `ENR-MAR-036` | marquage | lignes_de_voie_vercors | marquages | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | DOC-LOCALE-017 |
| `ENR-MAR-037` | marquage | lignes_de_voie_vercors | marquages | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | DOC-LOCALE-016 |
| `ENR-MAR-038` | marquage | logo_velo_piste | marquages | True | oui | ORTHO_A-0162 |
| `ENR-MAR-039` | marquage | traversee_cyclable_jaune | marquages | True | oui | ORTHO-B-130 |
| `ENR-MAR-040` | marquage | bandes_traversee_vercors | marquages | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-127 |
| `ENR-MAR-041` | marquage | nez_ilot_peint | marquages | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0159 |
| `ENR-MAR-042` | marquage | symbole_velo | marquages | True | oui | ORTHO-B-090 |
| `ENR-MAT-001` | candelabre | borne_globe | mobilier.lampadaire | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0122 |
| `ENR-MAT-002` | candelabre | lampadaire_pieton | mobilier.lampadaire | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-164 |
| `ENR-MAT-003` | candelabre | borne_lumineuse_globe | mobilier.lampadaire | True | oui | ORTHO_A-0156 |
| `ENR-MAT-004` | candelabre | lampadaire_pieton | mobilier.lampadaire | True | oui | ORTHO-B-163 |
| `ENR-MAT-005` | candelabre | mat_droit_residentiel | mobilier.lampadaire | True | oui | VISION-PANORAMAX-1-78 |
| `ENR-MOB-001` | mobilier | cage_metallique | mobilier | True | oui | ORTHO_A-0024 |
| `ENR-MOB-002` | mobilier | abri_ou_range_velos | mobilier | True | oui | ORTHO-B-210 |
| `ENR-MOB-003` | mobilier | coffret | mobilier | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0080 |
| `ENR-MOB-004` | mobilier | bloc_rocheux_alignement | mobilier | True | oui | ORTHO_A-0029 |
| `ENR-MOB-005` | mobilier | conteneurs | mobilier | True | oui | ORTHO-B-172 |
| `ENR-MOB-006` | mobilier | blocs_rocheux | mobilier | True | oui | ORTHO_A-0074 |
| `ENR-MOB-007` | mobilier | objet_rectangulaire | mobilier | True | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | ORTHO-B-112 |
| `ENR-MOB-008` | mobilier | butees_de_roues | mobilier | True | oui | ORTHO-B-078 |
| `ENR-MOB-009` | mobilier | objet_rouge | mobilier | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0121 |
| `ENR-MOB-010` | mobilier | arceaux_velos | mobilier | False | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | VISION-PANORAMAX-1-90 |
| `ENR-MOB-011` | mobilier | stationnement_trottinettes | mobilier | False | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | ORTHO-B-067 |
| `ENR-MOB-012` | mobilier | coffret_ou_borne | mobilier | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0113 |
| `ENR-MOB-013` | mobilier | conteneurs_dechets | mobilier | True | oui | ORTHO_A-0130 |
| `ENR-MOB-014` | mobilier | bancs | mobilier | True | oui | ORTHO_A-0155 |
| `ENR-MOB-015` | mobilier | coffre_ou_abri_conteneurs | mobilier | False | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-080 |
| `ENR-MOB-016` | mobilier | armoire_commande_feux_probable | mobilier | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | VISION-PANORAMAX-2-1 |
| `ENR-MOB-017` | mobilier | objet_blanc | mobilier | True | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | ORTHO-B-095 |
| `ENR-PAN-001` | panneau | plaque_de_rue | signaux.panneaux | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | pano_0-2 |
| `ENR-PAN-002` | panneau | D21_double | signaux.panneaux | False | non : aucune observation valide 2026 en confiance ≥ moyenne | VISION-PANORAMAX-1-41 |
| `ENR-PAN-003` | panneau | plaque_de_rue | signaux.panneaux | True | oui | VISION-PANORAMAX-2-37 |
| `ENR-PAN-004` | panneau | C13a_nom_de_rue | signaux.panneaux | True | oui | ORTHO-B-126 |
| `ENR-PAN-005` | panneau | panneau_large_ilot_nord | signaux.panneaux | True | oui | ORTHO-B-125 |
| `ENR-PON-001` | avaloir | grille | ponctuels_sol.avaloir | True | oui | ORTHO_A-0020 |
| `ENR-PON-002` | tampon | regard_carre | ponctuels_sol.tampon | True | oui | ORTHO_A-0022 |
| `ENR-PON-003` | avaloir | grille | ponctuels_sol.avaloir | True | oui | ORTHO_A-0021 |
| `ENR-PON-004` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO_A-0023 |
| `ENR-PON-005` | avaloir | grille | ponctuels_sol.avaloir | True | oui | ORTHO-B-180 |
| `ENR-PON-006` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-181 |
| `ENR-PON-007` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-186 |
| `ENR-PON-008` | tampon | tampons_ronds_cour | ponctuels_sol.tampon | True | oui | ORTHO_A-0075 |
| `ENR-PON-009` | tampon | disque_beton_clair | ponctuels_sol.tampon | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0079 |
| `ENR-PON-010` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-185 |
| `ENR-PON-011` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-187 |
| `ENR-PON-012` | avaloir | grille_carree | ponctuels_sol.avaloir | True | oui | ORTHO-B-179 |
| `ENR-PON-013` | avaloir | grille_carree | ponctuels_sol.avaloir | True | oui | ORTHO-B-182 |
| `ENR-PON-014` | tampon | regard_carre | ponctuels_sol.tampon | True | oui | ORTHO_A-0037 |
| `ENR-PON-015` | tampon | regard_carre | ponctuels_sol.tampon | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0077 |
| `ENR-PON-016` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-183 |
| `ENR-PON-017` | avaloir | grille | ponctuels_sol.avaloir | True | oui | ORTHO_A-0078 |
| `ENR-PON-018` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-184 |
| `ENR-PON-019` | tampon | regard_petit | ponctuels_sol.tampon | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0038 |
| `ENR-PON-020` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO_A-0076 |
| `ENR-PON-021` | tampon | regard_carre | ponctuels_sol.tampon | True | oui | ORTHO-B-155 |
| `ENR-PON-022` | tampon | regard_rond | ponctuels_sol.tampon | True | oui | ORTHO_A-0039 |
| `ENR-PON-023` | tampon | regard_carre | ponctuels_sol.tampon | True | oui | ORTHO-B-114 |
| `ENR-PON-024` | tampon | regard_carre | ponctuels_sol.tampon | True | oui | ORTHO-B-120 |
| `ENR-PON-025` | tampon | regard_carre | ponctuels_sol.tampon | True | oui | ORTHO-B-143 |
| `ENR-PON-026` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-113 |
| `ENR-PON-027` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-110 |
| `ENR-PON-028` | tampon | regard_carre | ponctuels_sol.tampon | True | oui | ORTHO-B-111 |
| `ENR-PON-029` | tampon | regard_carre | ponctuels_sol.tampon | True | oui | ORTHO-B-065 |
| `ENR-PON-030` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-074 |
| `ENR-PON-031` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-070 |
| `ENR-PON-032` | tampon | regard_carre | ponctuels_sol.tampon | True | oui | ORTHO-B-115 |
| `ENR-PON-033` | tampon | regard_carre | ponctuels_sol.tampon | True | oui | ORTHO-B-073 |
| `ENR-PON-034` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-072 |
| `ENR-PON-035` | tampon | tampon_rond | ponctuels_sol.tampon | False | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-071 |
| `ENR-PON-036` | avaloir | grille | ponctuels_sol.avaloir | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-117 |
| `ENR-PON-037` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-118 |
| `ENR-PON-038` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-116 |
| `ENR-PON-039` | tampon | regard_carre | ponctuels_sol.tampon | False | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-075 |
| `ENR-PON-040` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-069 |
| `ENR-PON-041` | tampon | regard_rectangulaire | ponctuels_sol.tampon | True | oui | ORTHO_A-0112 |
| `ENR-PON-042` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-043 |
| `ENR-PON-043` | tampon | regard_carre | ponctuels_sol.tampon | True | oui | ORTHO-B-024 |
| `ENR-PON-044` | avaloir | grille | ponctuels_sol.avaloir | True | oui | ORTHO_A-0128 |
| `ENR-PON-045` | tampon | petit_regard | ponctuels_sol.tampon | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0129 |
| `ENR-PON-046` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-025 |
| `ENR-PON-047` | avaloir | grille | ponctuels_sol.avaloir | True | oui | ORTHO_A-0127 |
| `ENR-PON-048` | tampon | regard | ponctuels_sol.tampon | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0144 |
| `ENR-PON-049` | tampon | bouche_a_cle | ponctuels_sol.tampon | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-036 |
| `ENR-PON-050` | avaloir | grille_avaloir | ponctuels_sol.avaloir | True | oui | ORTHO-B-035 |
| `ENR-PON-051` | tampon | tampon_rond | ponctuels_sol.tampon | False | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-028 |
| `ENR-PON-052` | tampon | regard | ponctuels_sol.tampon | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0140 |
| `ENR-PON-053` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-026 |
| `ENR-PON-054` | tampon | tampon_rond | ponctuels_sol.tampon | True | oui | ORTHO-B-027 |
| `ENR-PON-055` | tampon | regard_grille | ponctuels_sol.tampon | True | oui | ORTHO-B-086 |
| `ENR-PON-056` | tampon | regard | ponctuels_sol.tampon | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0142 |
| `ENR-PON-057` | tampon | regard | ponctuels_sol.tampon | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0141 |
| `ENR-PON-058` | tampon | regard | ponctuels_sol.tampon | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0143 |
| `ENR-PON-059` | tampon | regard | ponctuels_sol.tampon | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0139 |
| `ENR-PON-060` | tampon | regard_rond | ponctuels_sol.tampon | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | VISION-PANORAMAX-1-23 |
| `ENR-PON-061` | tampon | regard | ponctuels_sol.tampon | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0145 |
| `ENR-PON-062` | tampon | regard_carre | ponctuels_sol.tampon | True | oui | ORTHO-B-030 |
| `ENR-PON-063` | tampon | regard_carre | ponctuels_sol.tampon | True | oui | ORTHO-B-031 |
| `ENR-PON-064` | tampon | regard_carre | ponctuels_sol.tampon | False | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-033 |
| `ENR-PON-065` | tampon | regard_carre | ponctuels_sol.tampon | True | oui | ORTHO-B-032 |
| `ENR-PON-066` | tampon | regard_rond | ponctuels_sol.tampon | True | oui | ORTHO_A-0166 |
| `ENR-PON-067` | tampon | regard_grille | ponctuels_sol.tampon | True | oui | ORTHO-B-097 |
| `ENR-POT-001` | potelet | borne_blanche | mobilier.potelet | True | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | ORTHO-B-037 |
| `ENR-POT-002` | potelet | file_de_potelets, file_potelets_inox | mobilier.potelet | True | non : aucune observation valide 2026 en confiance ≥ moyenne | VISION-PANORAMAX-2-48, pano_0-48 |
| `ENR-SUR-001` | surface | reprise_enrobe | surfaces | True | oui | ORTHO-B-178 |
| `ENR-SUR-002` | surface | reprise_enrobe | surfaces | True | oui | ORTHO-B-066 |
| `ENR-SUR-003` | surface | reprise_enrobe | surfaces | True | oui | ORTHO-B-034 |
| `ENR-SUR-004` | surface | cheminement_pieton_neuf_rive_E_Vercors | surfaces | True | oui | DOC-LOCALE-004 |
| `ENR-VEG-001` | haie | haie_basse_taillee, haie_taillee | vegetation.haies | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-076, pano_0-54 |
| `ENR-VEG-002` | haie | haie_taillee_parking_Reviree | vegetation.haies | True | oui | VISION-PANORAMAX-1-26 |
| `ENR-VEG-003` | massif | massif_paille | vegetation.massifs | True | oui | ORTHO-B-038 |
| `ENR-VEG-004` | haie | haie_taillee_persistante | vegetation.haies | True | oui | pano_0-53 |
| `ENR-VEG-005` | haie | haie_taillee_angle_N | vegetation.haies | True | oui | VISION-PANORAMAX-1-25 |
| `ENR-VEG-006` | haie | haie_taillee_piste_vercors | vegetation.haies | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | VISION-PANORAMAX-1-88 |
| `ENR-VEG-007` | haie | haie_taillee | vegetation.haies | True | oui | VISION-PANORAMAX-2-51 |
| `ENR-VEG-008` | massif | arbustes_tailles_en_blocs | vegetation.massifs | True | oui | ORTHO_A-0185 |
| `ENR-VEG-009` | massif | arbustes_tailles_en_blocs | vegetation.massifs | True | oui | ORTHO_A-0198 |

## Conflits

81 conflits : attribut_desaccord 1, coherence_desaccord 3, deplacement_non_etaye 7, doublon_apres_correction 1, lien_introuvable 1, position_desaccord 9, surface_a_decouper 3, validite_2026_douteuse 56. Détail dans `conflits.json`.

| id | type | cible | obs | détail |
|---|---|---|---|---|
| CF-ENR-001 | attribut_desaccord | `lamp_9665416817` | VISION-PANORAMAX-1-17, VISION-PANORAMAX-1-43 | couleur_mat : {"\"brun-rouille\"": ["VISION-PANORAMAX-1-17"], "\"gris anthracite patiné\"": ["VISION-PANORAMAX-1-43"]} |
| CF-ENR-002 | coherence_desaccord | `lamp_9665416717` | ORTHO_A-0167 | cohérence : deplacement de 0.1 m ; image à 0.84 m de la position corrigée et 0.88 m de l'origine (partiel) |
| CF-ENR-003 | coherence_desaccord | `lamp_9665416817` | VISION-PANORAMAX-1-55, VISION-PANORAMAX-2-57 | cohérence : deplacement de 0.65 m ; image à 0.44 m de la position corrigée et 0.58 m de l'origine (partiel) |
| CF-ENR-004 | coherence_desaccord | `mat_camera_SW_TPC` | pano_0-47 | cohérence : deplacement de 0.05 m ; image à 1.58 m de la position corrigée et 1.59 m de l'origine (partiel) |
| CF-ENR-005 | deplacement_non_etaye | `K-0227` | ORTHO_A-0019 | translation de 0.87 m proposée ; géométrie levée GAM : translation > 0,5 m (FUS-POS-06) |
| CF-ENR-006 | deplacement_non_etaye | `arbre_224` | VISION-PANORAMAX-2-13 | deplacement de 7.62 m proposé ; σ fusion 2.40 m > 0,5 m ; σ fusion 2.40 m > preuve de la description (0.05 m) ; objet levé GAM : déplacement > 0,5 m (FUS-POS-06) |
| CF-ENR-007 | deplacement_non_etaye | `armoire_1313238971` | ORTHO-B-171 | deplacement de 1.04 m proposé ; une seule source non triangulée et pas de correction affirmée |
| CF-ENR-008 | deplacement_non_etaye | `banc_8360664518` | ORTHO_A-0100 | deplacement de 4.47 m proposé ; aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines) |
| CF-ENR-009 | deplacement_non_etaye | `lamp_lidar_VERC_E` | VISION-PANORAMAX-2-2 | deplacement de 0.77 m proposé ; aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines) |
| CF-ENR-010 | deplacement_non_etaye | `mat_camera_SW_TPC` | pano_0-47 | deplacement de 1.59 m proposé ; aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines) |
| CF-ENR-011 | deplacement_non_etaye | `potelet_12462947806` | ORTHO_A-0081 | deplacement de 1.97 m proposé ; une seule source non triangulée et pas de correction affirmée |
| CF-ENR-012 | doublon_apres_correction | `poteau_reseau_12888056356` | pano_0-20 | position corrigée à 0.66 m de lamp_lidar_SW_NO (lampadaire) : même objet probable |
| CF-ENR-013 | lien_introuvable | `BEV-0348-2` | VISION-PANORAMAX-1-24 | id BEV-0348-2 absent de la description courante et sans équivalent spatial |
| CF-ENR-023 | surface_a_decouper | `S-0094a` | ORTHO-B-039, ORTHO-B-099 | surface de 11599 m² (espace_vert, gazon_tondu) contenant des sous-zones observées : gazon_tondu (ORTHO-B-039); enrobe_bbsg_ancien (ORTHO-B-099) |
| CF-ENR-024 | surface_a_decouper | `S-0159a` | ORTHO-B-088 | surface de 4101 m² (parking, enrobe_bbsg_ancien) contenant des sous-zones observées : |
| CF-ENR-025 | surface_a_decouper | `S-0161a` | ORTHO-B-077, ORTHO-B-149, ORTHO-B-156 | surface de 11047 m² (parking, enrobe_bbsg_ancien) contenant des sous-zones observées : gravier (ORTHO-B-077); eau_bassin (ORTHO-B-149) |
| CF-ENR-056 | validite_2026_douteuse | `K-0078` | ORTHO-B-094 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) tr… |
| CF-ENR-057 | validite_2026_douteuse | `K-0081` | ORTHO-B-094 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) tr… |
| CF-ENR-058 | validite_2026_douteuse | `K-0082` | ORTHO-B-094 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) tr… |
| CF-ENR-059 | validite_2026_douteuse | `K-0083` | ORTHO-B-094 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) tr… |
| CF-ENR-060 | validite_2026_douteuse | `K-0084` | ORTHO-B-094 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) tr… |
| CF-ENR-061 | validite_2026_douteuse | `K-0085` | ORTHO-B-094 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) tr… |
| CF-ENR-062 | validite_2026_douteuse | `K-0086` | ORTHO-B-094 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) tr… |
| CF-ENR-063 | validite_2026_douteuse | `MZ-5002` | ORTHO-B-091 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. rien de peint au point de MZ-5002 (forme en Y, « conserve ») : en… |
| CF-ENR-064 | validite_2026_douteuse | `arbre_022` | ORTHO_A-0046 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. pelouse sans couronne à la position en 05/2022 |
| CF-ENR-065 | validite_2026_douteuse | `arbre_184` | pano_0-16 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. à l'axe : façade grise, clôture, armoire grise et mât portant un … |
| CF-ENR-066 | validite_2026_douteuse | `arbre_229` | pano_0-14 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. même situation que arbre_230 (1,4 m plus loin) : poteau bois + ha… |
| CF-ENR-067 | validite_2026_douteuse | `arbre_230` | pano_0-13 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. l'axe projeté tombe sur un poteau bois brun derrière une haie bas… |
| CF-ENR-068 | validite_2026_douteuse | `arbre_269` | ORTHO_A-0196 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. terre nue de chantier à la position en 05/2022 (hors de la couron… |
| CF-ENR-069 | validite_2026_douteuse | `arbre_362` | ORTHO-B-193 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. au point de arbre_362 (h 25,4 m, couronne 13,9 m d'après le LiDAR… |
| CF-ENR-070 | validite_2026_douteuse | `arbre_383` | ORTHO-B-194 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. même cas que arbre_362 : h 22,7 m décrite, sol de chantier nu en … |
| CF-ENR-071 | validite_2026_douteuse | `arbre_435` | ORTHO_A-0178 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2023-09-11) : non probante pour 2026. pelouse ouverte (en partie à l'ombre des arbres voisins au NO) sa… |
| CF-ENR-072 | validite_2026_douteuse | `barriere_levante_12462947804` | ORTHO-B-189 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-04-08) : non probante pour 2026. aucune lisse ni potence visible au point (voie du parking) en 202… |
| CF-ENR-073 | validite_2026_douteuse | `chicane_12462947805` | ORTHO-B-177 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-03-15) : non probante pour 2026. aucune barrière / chicane visible au point (place de parking marq… |
| CF-ENR-074 | validite_2026_douteuse | `cloture_gam_001` | ORTHO-B-083 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. le tracé GAM de cloture_gam_002 (et cloture_gam_001 dans son prol… |
| CF-ENR-075 | validite_2026_douteuse | `cloture_gam_002` | ORTHO-B-083 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. le tracé GAM de cloture_gam_002 (et cloture_gam_001 dans son prol… |
| CF-ENR-076 | validite_2026_douteuse | `cloture_gam_049` | VISION-PANORAMAX-1-64, VISION-PANORAMAX-1-65 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. ; aucune clôture le long de la ligne cloture_gam_049 le 18/05/202… |
| CF-ENR-077 | validite_2026_douteuse | `lamp_12758859672` | ORTHO-B-061 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-06-07) : non probante pour 2026. aucun mât ni ombre au point décrit (au milieu d'une place du park… |
| CF-ENR-078 | validite_2026_douteuse | `lamp_12758894668` | ORTHO-B-062 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2026-03-16) : non probante pour 2026. rien au point décrit (bord de la serre) en 2022 ; nœud OSM 2026-0… |
| CF-ENR-079 | validite_2026_douteuse | `lamp_12887274334` | ORTHO-B-151 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-10-25) : non probante pour 2026. le point décrit tombe sur un buis taillé en boule dans la jardini… |
| CF-ENR-080 | validite_2026_douteuse | `lamp_13539965051` | ORTHO-B-141 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2026-02-10) : non probante pour 2026. au point décrit (extrémité NO de la terrasse) une voiture est gar… |
| CF-ENR-081 | validite_2026_douteuse | `pan_J5_1` | ORTHO-B-003 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-05-15) : non probante pour 2026. aucune balise ni ombre au point décrit (extrémité NE de l'îlot I-… |

## Carte de couverture

`couverture_preuves.png` : A/C preuve image la plus récente valable 2026 par entité (rampe bleue ordinale : ortho 2022 clair, photos 2020-2024, photos 2025 foncé ; anneau noir : web seul ; anneau gris : preuve antérieure non valable ; petit point : aucune preuve), zones refaites en 2025 hachurées, positions des photos citées ; B/D décisions (carré orange : attribut, flèche : déplacement, à l'échelle au-delà de 1 m et x5 en dessous, losange aqua : ajout, croix : absent/retirer, anneau rouge : conflit). Fond : ortho 2022 éclaircie, bordures v0.3 en gris.

## Règles de fusion

- **FUS-LIEN-01** : lien_description explicite (ids séparés par « ; ») résolu dans l'index : base v0.3 > mobilier > arbres > instances > bordures_site > surfaces v1 > propositions de cohérence.
- **FUS-LIEN-02** : marquage absent de la v0.3 mais présent dans marquages_indices_v1 : remappé par lien_v1 -> marquages_correspondance (devenir « genere » -> entité v0.3 ; « retire » -> entité retirée).
- **FUS-LIEN-03** : surface v0.2 sans suffixe (S-0121) : polygone S-0121* qui contient le point (sinon le plus proche à ≤ 1 m).
- **FUS-LIEN-04** : autre id introuvable : appariement spatial dans la famille de son préfixe, tolérance de la classe ; sinon conflit lien_introuvable.
- **FUS-LIEN-05** : liens secondaires (attributs liens / confirmes / arbres_confirmes / arbres) : l'observation vaut pour chaque entité citée (attributs et existence) ; la position ne vaut que pour les liens primaires co-implantés (≤ 1,5 m, même support).
- **FUS-LIEN-06** : observation sans lien (statut ≠ absent_de_description, précision ≤ 3 m) : entité la plus proche de la famille compatible dans la tolérance de classe.
- **FUS-CTX-01** : observation de contexte (précision absente ou > 5 m, sous-type chantier / hors emprise / programme / état 2022 remplacé, bâtiment) sans lien : indexée, jamais fusionnée ni ajoutée.
- **FUS-TMP-01** : objet temporaire (chantier, provisoire, temporaire, base vie, bungalow, affiche) : jamais ajouté ; s'il est lié et que l'image est postérieure à l'attestation de l'objet, existence « non_instancier » (sinon conflit validite_2026_douteuse).
- **FUS-VAL-01** : poids de validité 2026 : vrai 1 ; incertain 0,5 ; faux 0 (observation historique, conservée pour la traçabilité).
- **FUS-VAL-02** : constat indépendant de la date (sous-type faux_positif*, raison « artefact », marquage posé sur une toiture ou un massif) : poids 1 même si valide_2026 = faux.
- **FUS-VAL-03** : entité créée après l'image (marquage neuf_2025 ou refait, bordure ou surface modifiée 2025, objet « déduit 2026 » ou « planté 2025 », surface construite 2023-2024) : l'image antérieure ne prouve ni absence ni attribut (poids 0). Une absence ne prouve l'absence 2026 que si la première attestation de l'objet (LiDAR 2021, ortho 2022, OSM daté, inventaire 2023, plan 2025, levé GAM postérieur aux travaux ≈ 2025-12, « 2026 confirmé ») précède l'image ; sinon elle est non probante : signalée (conflit validite_2026_douteuse) sauf si l'observateur la dit attendue (« cohérent avec la description », « comme attendu », « plantations postérieures »...).
- **FUS-LIEN-07** : observation absent_de_description portant un lien vers une entité d'une autre famille (surface, support, proposition de cohérence) : le lien est l'hôte de l'objet nouveau, l'observation devient candidat d'ajout ; ses liens secondaires sont des « liens associés » sans effet sur les attributs. Même famille (surface sur surface) : constat d'état de l'entité (notes).
- **FUS-LIEN-08** : ids de la carte de cohérence (KS-xxxx-n) et des surfaces v1 (surf_xxxx) : remappés vers la description de base (K- de même ligne GAM, S- de même lien_v1) au plus proche de la mesure (≤ 2 m / ≤ 1 m).
- **FUS-ATT-05** : surface de plus de 2 000 m² : une observation ponctuelle ne requalifie pas tout le polygone ; matériaux et classes proposés y deviennent des sous-zones (conflit surface_a_decouper).
- **FUS-POS-08** : après correction, deux objets de même classe à moins de 0,75 m : conflit doublon_apres_correction (fusion à décider).
- **FUS-CONF-01** : poids de confiance : haute 1 ; moyenne 0,6 ; faible 0,3 ; contrôle automatique x0,7 ; valeur « probable » ou « ? » x0,6.
- **FUS-POS-01** : mesures de position : triangulation σ = max(préc. ; 0,05) et rayon au sol σ = 2·max(préc. ; 0,30) (tout statut) ; pixel ortho σ = 1,25·max(préc. ; 0,10) seulement pour position_corrigee (ailleurs le pixel peut désigner une lanterne ou une couronne) ; une observation « confirme » sans mesure (projection, pixel ortho) = confirmation à la position décrite, utilisée seulement sans autre mesure (σ = 1,5·max(préc. ; 0,15) en projection) ; pour la pondération, σ divisé par √(poids confiance x validité). Mesures identiques (≤ 1 cm, même méthode) comptées une fois.
- **FUS-POS-02** : triangulation à angle d'intersection < 15° (lu dans l'observation) : σ x2.
- **FUS-POS-03** : moyenne pondérée 1/σ², rejet itératif de la mesure au plus fort résidu normalisé (> 3 et > tolérance de classe) -> conflit position_desaccord.
- **FUS-POS-04** : verdict (README triangulation) : écart d à la description ≤ max(0,35 m ; 3σ), σ de mesure fusionné sans pondération de confiance -> confirmé ; sinon affinage (≤ 0,75 m) ou déplacement (> 0,75 m).
- **FUS-POS-05** : application : « appliquer » si une mesure valide 2026 (poids 1) existe, σ ≤ 0,5 m, σ ≤ max(σ de la preuve décrite ; 0,30) et (triangulation, ou ≥ 2 sources indépendantes concordantes, ou position_corrigee affirmée par l'observateur en confiance ≥ moyenne) ; sinon « revue_requise ».
- **FUS-POS-06** : objet levé GAM (σ ≤ 0,05 m) : jamais déplacé de plus de 0,5 m sans revue (« revue_requise »).
- **FUS-POS-07** : ligne ou polygone (marquage, bordure, clôture, BEV) : vecteur du point le plus proche de la géométrie (ou du point « au lieu de (x ; y) » cité) à la mesure ; translation proposée si |v| > max(0,10 m marquage | 0,20 m autre ; 3σ).
- **FUS-ATT-01** : attributs normalisés par table d'alias (hauteur, couronne, essence, type, crosses, lanternes, azimut de face, code, modulation, couleur, état, usure, gabarit, largeur, matériau, classe, bouton d'appel...). Le texte libre reste en notes.
- **FUS-ATT-02** : vote pondéré (confiance x validité x contrôle x « probable ») ; catégoriel : valeur de poids maximal ; numérique : moyenne pondérée ; azimut : moyenne circulaire.
- **FUS-ATT-03** : conflit d'attribut : catégoriel si le 2e poids ≥ 0,5 x le 1er (et ≥ 0,3) ; numérique si l'étendue dépasse max(tolérance absolue ; tolérance relative x moyenne) ; azimut si un vote s'écarte de > 30°.
- **FUS-ATT-04** : mise à jour émise si poids gagnant ≥ 0,3 et écart à la description au-delà du seuil de l'attribut (valeur absente de la description : ajout d'attribut).
- **FUS-EXI-01** : existence : présence (confirme, attribut_corrige, position_corrigee) contre absence (absent_sur_image) ; « absent_2026 » si poids absence ≥ 0,6 et ≥ 2 x présence ; conflit si les deux ≥ 0,3.
- **FUS-EXI-02** : retrait (artefact de la description : faux positif, « à retirer », « à supprimer », doublon) si poids ≥ 0,6 ; retypage (poteau réseau au lieu de lampadaire) si vote explicite ≥ 0,6.
- **FUS-ADD-01** : ajouts : observations absent_de_description (et candidats incertains non appariés) regroupées par lien simple, même groupe de classe, distance ≤ tolérance + min(σi + σj ; 3 m) entre ateliers différents, ≤ tolérance et même sous-type dans un même atelier.
- **FUS-ADD-02** : ajout à moins de la moitié de la tolérance d'une entité existante de même famille : conflit ajout_proche_existant, non instancié. Exceptions : sous-zone ou reprise de surface (la surface est son hôte) ; équipement porté (boîtier, plaque, panonceau : le support voisin est son hôte).
- **FUS-ADD-03** : ajout instancié si au moins une observation valide 2026 (vrai) en confiance ≥ moyenne, non temporaire, famille cible connue ; croisé avec les propositions de cohérence (≤ 3 m) et le levé GAM 2026 des arbres (≤ 2 m).
- **FUS-COH-01** : contrôle croisé avec coherence/corrections.geojson : accord si la position image est à ≤ max(0,35 ; 2σ) de la position corrigée ; désaccord si elle est à cette distance de la position d'origine seulement ; partiel si elle est loin des deux ; les deux dans la tolérance : tendance_accord / tendance_desaccord si l'écart les départage d'au moins σ, sinon indifférent ; confirmations sans mesure : non concluant ; azimut : accord à ≤ 30° ; propositions d'ajout rejointes par une observation : corroborées (datées).

## Limites

- Aucune image ne montre le cœur après les travaux (dernière photo : 31/08/2025) : les objets refaits en 2025 restent « non valables 2026 » ou « revue_requise » ; une prise de vue 2026 avec la même chaîne trancherait.
- La description de base est régénérée en parallèle : relancer ce script après chaque régénération (les liens disparus deviennent des conflits `lien_introuvable`).
- Les attributs en texte libre ne sont pas votés : ils restent dans `notes` (revue humaine, `revue_texte`).
- Les poids et seuils (REGLES) sont des choix documentés, pas des mesures ; les sorties restent des propositions pour le composeur et l'arbitrage.
