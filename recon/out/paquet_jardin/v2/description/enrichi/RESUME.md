# Fusion du recensement : couche `description/enrichi/`

Générateur : `python recon/pcg/enrichir/fusion_recensement.py` (fusion_recensement/0.2), déterministe. Couche séparée : ni la description de base, ni la cohérence, ni les observations ne sont modifiées. Le composeur la fusionnera (priorité arbitré > enrichi vérifié > base).

## Dates des images

| catégorie (FUS-SRC-01) | source | dates des observations | observations |
|---|---|---|---|
| photo_2026 | Panoramax, 7 photos (3 calées) | 2026-07-28 | 48 |
| photo_2025 | Panoramax et Mapillary | 2025-01-12 à 2025-08-31 | 265 |
| ortho_2025 | Pléiades 2025, 50 cm (non datée) | 2025 (sans date publiée) | 1 |
| photo_2020_2024 | Panoramax et Mapillary | 2020-05-21 à 2024-08-24 | 301 |
| ortho_2024 | IGN BD ORTHO, 20 cm | 2024-08-09 | 202 |
| ortho_2022 | PCRS 5 cm | 2022-05-10 | 624 |

Les seules images de l'état 2026 sont les photos Panoramax du 28/07/2026 (après la fin des travaux, le 05/12/2025 ; trottoirs du Vercors achevés le 30/01/2026). Elles ont été prises sur la place, environ 135 m au sud du cœur, et ne voient pas le cœur du carrefour. Toutes les autres images sont antérieures aux travaux du cœur : Panoramax jusqu'au 31/08/2025 (série à plat en plein chantier), Mapillary jusqu'au 18/05/2025, IGN du 09/08/2024, Pléiades 2025 sans date (le cœur y est encore dans son état de 2024), PCRS du 10/05/2022.

## Entrées

| fichier | observations |
|---|---|
| `recon/out/paquet_jardin/v2/enrichi/recensement/obs_mapillary.json` | 355 |
| `recon/out/paquet_jardin/v2/enrichi/recensement/obs_ortho_A.json` | 200 |
| `recon/out/paquet_jardin/v2/enrichi/recensement/obs_ortho_B.json` | 424 |
| `recon/out/paquet_jardin/v2/enrichi/recensement/obs_ortho_recentes.json` | 203 |
| `recon/out/paquet_jardin/v2/enrichi/recensement/obs_pano_0.json` | 61 |
| `recon/out/paquet_jardin/v2/enrichi/recensement/obs_pano_1.json` | 90 |
| `recon/out/paquet_jardin/v2/enrichi/recensement/obs_pano_2.json` | 60 |
| `recon/out/paquet_jardin/v2/enrichi/recensement/obs_pano_2026.json` | 48 |
| `recon/out/paquet_jardin/v2/enrichi/recensement/web/obs_web.json` | 34 |

Total : 1475 observations. Description lue : base v0.3 (`base/`), objets du paquet, instances, bordures du site (carte de cohérence), surfaces v1, corrections et propositions de cohérence, levé GAM 2026 des arbres, arbitrages de revue (`arbitrages_fusion.json`). Les empreintes SHA-256 de toutes les entrées sont dans `observations_index.json` (`meta.entrees`).

## Synthèse

- 1020 entités de la description reçoivent au moins une observation ; 529 sont confirmées sans correction ; 123 ont au moins un attribut corrigé (150 mises à jour).
- Position : 18 corrections mesurées, dont 11 à appliquer et 7 en revue (FUS-POS-05/06).
- Existence : 33 entités à retirer ou absentes en 2026.
- Ajouts : 189 objets nouveaux, dont 125 instanciables ; 5 ajouts remplacés par un conflit avec le levé GAM (FUS-ADD-04).
- Conflits : 100 (56 à vérifier, 44 pour information).
- Cohérence : 31 corrections du solveur ont une preuve image ; corrobore_avant_travaux 1, indifferent 1, non_conclu_sans_mesure 16, non_contredit 4, partiel 6.

## Contrôles automatiques des marquages (FUS-AUTO-01/02)

| atelier | confirmations automatiques | requalifiées « incertain » | corroborées par une observation manuelle |
|---|---|---|---|
| ortho_A | 47 | 45 | 2 |
| ortho_B | 57 | 57 | 0 |
| ortho_recentes | 102 | 76 | 26 |

Aucune n'a de masque véhicules / ombres (FUS-AUTO-02) : les échantillons revus montraient des voitures, des ombres et du feuillage pris pour de la peinture (ateliers 2022 ; 18 / 22 correctes en 2024). Une confirmation automatique ne compte plus que si une observation manuelle (vue, photo) confirme la même entité ; deux contrôles automatiques ne se corroborent pas. Contrat d'un futur contrôle automatique : `attributs.controle_auto` = {masque_vehicules_ombres: true, part_masquee ≤ 0,2, reponse_ligne_fine: true (ligne) ou reponse_peinture: true (flèche, symbole)}, calculé par `recon/pcg/enrichir/controle_auto.py`. Essai sur le PCRS 2022 (`controle_auto_essai.jpg`) : les quatre fausses confirmations relevées par la critique (ML-0294, ML-0295, ML-0119, ML-5360 : voitures, ombre de bâtiment) sont masquées ; quatre lignes réelles et une flèche sont confirmées ; deux lignes ne sont pas confirmées (l'une sous une ombre d'arbre, l'autre décalée de 0,4 m). Le PCRS 5 cm est requis pour la réponse de ligne fine : à 20 cm (IGN 2024), un trait de 0,10-0,15 m n'est pas résolu.

## Priorité des photos 2026 (FUS-DATE-01)

46 entités sont vues sur les photos du 28/07/2026 (43 avec une preuve concluante) ; pour 24 d'entre elles, la photo 2026 a écarté des observations plus anciennes (existence, attribut ou position).

| entité | existence | position | attributs | observations antérieures écartées |
|---|---|---|---|---|
| `I-0658` | present | non_mesure | - | MLY-ILO-003 |
| `I-0673` | present | non_mesure | - | MLY-ILO-004 |
| `K-0420` | present | non_mesure | - | MLY-BOR-028 |
| `K-0513` | present | non_mesure | - | MLY-BOR-058 |
| `K-0645` | present | confirme | - | MLY-BOR-067, OR-K-0645 |
| `K-0658` | present | non_mesure | - | MLY-BOR-068 |
| `K-0658z` | present | non_mesure | - | - |
| `K-0667` | present | confirme | - | OR-K-0667 |
| `K-0670` | present | non_mesure | - | MLY-BOR-074 |
| `MF-5523` | non_verifie | non_mesure | - | - |
| `ML-0432` | retirer | non_mesure | - | - |
| `ML-0433` | non_verifie | non_mesure | - | - |
| `ML-0434` | non_verifie | non_mesure | - | - |
| `ML-5337` | present | non_mesure | usure | - |
| `ML-5338` | present | non_mesure | usure | - |
| `ML-5339` | present | non_mesure | usure | - |
| `ML-5340` | present | non_mesure | usure | - |
| `ML-5341` | present | non_mesure | usure | MLY-MAR-016 |
| `ML-5342` | present | non_mesure | - | MLY-MAR-017 |
| `ML-5343` | present | non_mesure | - | MLY-MAR-018 |
| `ML-5344` | present | non_mesure | usure | - |
| `ML-5345` | present | non_mesure | usure | - |
| `ML-5358` | present | non_mesure | usure | - |
| `ML-5452` | present | non_mesure | etat, usure | - |
| `MP-0085` | present | non_mesure | etat | - |
| `MS-5515` | present | non_mesure | etat, usure | - |
| `MS-5516` | present | non_mesure | etat, usure | - |
| `S-0268a` | present | non_mesure | materiau_id | MLY-SUR-060 |
| `S-0268b` | present | non_mesure | - | MLY-SUR-061 |
| `S-0268c` | present | non_mesure | - | MLY-SUR-062 |
| `S-0268d` | present | non_mesure | materiau_id | MLY-SUR-063 |
| `S-0268e` | present | non_mesure | materiau_id | MLY-SUR-064 |
| `arbre_013` | absent_2026 | non_mesure | - | - |
| `arbre_014` | present | confirme_sans_mesure | type | ORTHO-B-168 |
| `arbre_015` | absent_2026 | non_mesure | - | - |
| `arbre_016` | present | confirme_sans_mesure | hauteur_m | ORTHO-B-168 |
| `arbre_018` | non_verifie | confirme_sans_mesure | - | ORTHO-B-380 |
| `arbre_026` | present | confirme_sans_mesure | - | - |
| `arbre_029` | present | confirme_sans_mesure | - | - |
| `barriere_levante_3375058657` | present | non_mesure | - | - |
| `lamp_9514828431` | present | deplacement 1.883 m (revue_requise) | - | MLY-MOB-026 |
| `lamp_9514828517` | present | affinage 0.699 m (appliquer) | couleur_mat | ORTHO-B-166 |
| `pan_AB3a_3` | present | deplacement 4.147 m (appliquer) | - | - |
| `pan_AB4_2` | present | deplacement 0.922 m (appliquer) | - | ORTHO-B-123 |
| `pan_B6a1_1` | present | affinage 0.683 m (appliquer) | couleur_mat | ORTHO-B-166 |
| `pan_C13a_1` | present | affinage 0.683 m (appliquer) | couleur_mat | ORTHO-B-166 |

## Arbitrages de revue (FUS-ARB-01)

| id | action | observations | effet | motif |
|---|---|---|---|---|
| ARB-001 | ne_pas_instancier | ORTHO-B-187 | ENR-PON-011 non instancié | tache d'enrobé sombre aux bords flous, sans anneau ni cadre : pas un tampon (le tampon rond voisin, net, est un autre objet) |
| ARB-002 | ancrer_bord_ilot | VISION-PANORAMAX-1-78 | ENR-MAT-005 ancré au bord de surf_0358 (espace_vert), déplacé de 1.572 m | le mât (4,5 m, gris clair) se dresse dans le petit îlot planté rond bordé, à la sortie de la voie privée des Saules Blancs (photo 81f3f695 du 24/08/2024) ; le … |
| ARB-003 | mesure_position | DOC-LOCALE-018 | arbre_224 : deplacement 7.823 m, σ 1.874 m, 2 mesures, décision revue_requise | le point de l'inventaire Métropole MEY00085 (peuplier noir) est à 1,2 m du tronc triangulé par VISION-PANORAMAX-2-13 et à 8,5 m de arbre_224 (levé GAM) : deux … |

## Comptes par classe

Une entité compte une fois par colonne. « confirmées » : présente sans correction. « sans preuve concluante » : vue seulement par des observations incertaines (dont les confirmations automatiques requalifiées) ou avant sa forme 2026.

| classe | entités vues | confirmées | attribut corrigé | position corrigée (appliquer) | absentes / à retirer | sans preuve concluante | ajouts (instanciés) | ajouts -> conflit GAM | avec conflit |
|---|---|---|---|---|---|---|---|---|---|
| arbre | 312 | 202 | 35 | 1 (0) | 3 | 55 | 14 (10) | 0 | 10 |
| haie_massif | 0 | 0 | 0 | 0 (0) | 0 | 0 | 10 (8) | 0 | 2 |
| marquage | 247 | 49 | 21 | 0 (0) | 28 | 147 | 40 (30) | 5 | 19 |
| bordure | 162 | 130 | 0 | 1 (0) | 2 | 25 | 0 (0) | 0 | 10 |
| surface_ilot | 159 | 80 | 46 | 0 (0) | 0 | 33 | 8 (7) | 0 | 7 |
| ponctuel_sol | 2 | 1 | 0 | 0 (0) | 0 | 1 | 68 (49) | 0 | 12 |
| candelabre_poteau | 46 | 19 | 11 | 9 (7) | 0 | 10 | 5 (3) | 0 | 10 |
| panneau | 25 | 9 | 8 | 4 (4) | 0 | 4 | 12 (8) | 0 | 6 |
| feu | 9 | 6 | 0 | 0 (0) | 0 | 3 | 2 (0) | 0 | 1 |
| potelet_borne | 13 | 7 | 2 | 1 (0) | 0 | 3 | 2 (0) | 0 | 1 |
| cloture_barriere | 36 | 20 | 0 | 0 (0) | 0 | 16 | 2 (2) | 0 | 7 |
| mobilier | 9 | 6 | 0 | 2 (0) | 0 | 1 | 17 (8) | 0 | 5 |
| autre | 0 | 0 | 0 | 0 (0) | 0 | 0 | 9 (0) | 0 | 2 |
| **total** | 1020 | 529 | 123 | 18 (11) | 33 | 298 | 189 (125) | 5 | 92 |

## Couverture : preuve image concluante la plus récente, valable 2026 (FUS-COUV-01)

Entités de la description (base v0.3 + objets du paquet), par tranche de date de leur preuve la plus récente. « % image » : part des entités ayant une preuve image concluante (2026, 2025, 2020-2024 ou ortho 2022). « auto seul » : preuve venant uniquement de contrôles automatiques non requalifiés (couronnes d'arbres sur l'ortho 2022, bordures vues sur les orthos 2022 et 2024 ; poids x0,7). Cœur : carré ± 80 m autour de l'origine ; zone 2025 : surfaces refaites et zones de chaussée reprises en 2025.

### Site entier

| classe | entités | 2026 | 2025 | 2020-2024 | ortho 2022 | web seul | non concluant | non valable 2026 | sans preuve | auto seul | % image | % ≥ 2024 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| arbre | 467 | 7 | 24 | 58 | 157 | 11 | 24 | 31 | 155 | 141 | 52.7 | 19.1 |
| marquage | 402 | 15 | 16 | 26 | 41 | 1 | 128 | 19 | 156 | 0 | 24.4 | 14.2 |
| bordure | 512 | 7 | 24 | 94 | 12 | 0 | 23 | 2 | 350 | 31 | 26.8 | 24.4 |
| surface_ilot | 1434 | 7 | 37 | 63 | 15 | 3 | 25 | 8 | 1276 | 0 | 8.5 | 7.5 |
| ponctuel_sol | 12 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 10 | 0 | 8.3 | 8.3 |
| candelabre_poteau | 52 | 2 | 16 | 1 | 17 | 0 | 7 | 3 | 6 | 0 | 69.2 | 36.5 |
| panneau | 33 | 4 | 16 | 1 | 0 | 0 | 3 | 1 | 8 | 0 | 63.6 | 63.6 |
| feu | 13 | 0 | 2 | 2 | 0 | 0 | 0 | 3 | 6 | 0 | 30.8 | 30.8 |
| potelet_borne | 13 | 0 | 2 | 0 | 8 | 0 | 1 | 2 | 0 | 0 | 76.9 | 15.4 |
| cloture_barriere | 63 | 1 | 1 | 17 | 1 | 0 | 16 | 0 | 27 | 0 | 31.7 | 30.2 |
| mobilier | 30 | 0 | 1 | 1 | 3 | 3 | 1 | 0 | 21 | 0 | 16.7 | 6.7 |
| **total** | 3031 | 43 | 140 | 263 | 254 | 18 | 228 | 70 | 2015 | 172 | 23.1 | 14.7 |

### Cœur du carrefour (± 80 m)

| classe | entités | 2026 | 2025 | 2020-2024 | ortho 2022 | web seul | non concluant | non valable 2026 | sans preuve | auto seul | % image | % ≥ 2024 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| arbre | 158 | 0 | 12 | 18 | 50 | 4 | 3 | 9 | 62 | 47 | 50.6 | 19.0 |
| marquage | 221 | 0 | 10 | 14 | 16 | 1 | 34 | 13 | 133 | 0 | 18.1 | 10.9 |
| bordure | 204 | 0 | 3 | 30 | 10 | 0 | 5 | 2 | 154 | 15 | 21.1 | 16.2 |
| surface_ilot | 557 | 0 | 10 | 19 | 4 | 3 | 10 | 4 | 507 | 0 | 5.9 | 5.2 |
| ponctuel_sol | 12 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 10 | 0 | 8.3 | 8.3 |
| candelabre_poteau | 26 | 0 | 15 | 0 | 3 | 0 | 3 | 3 | 2 | 0 | 69.2 | 57.7 |
| panneau | 21 | 0 | 14 | 0 | 0 | 0 | 1 | 1 | 5 | 0 | 66.7 | 66.7 |
| feu | 13 | 0 | 2 | 2 | 0 | 0 | 0 | 3 | 6 | 0 | 30.8 | 30.8 |
| potelet_borne | 6 | 0 | 2 | 0 | 1 | 0 | 1 | 2 | 0 | 0 | 50.0 | 33.3 |
| cloture_barriere | 26 | 0 | 1 | 9 | 1 | 0 | 8 | 0 | 7 | 0 | 42.3 | 38.5 |
| mobilier | 17 | 0 | 1 | 1 | 1 | 3 | 0 | 0 | 11 | 0 | 17.6 | 11.8 |
| **total** | 1261 | 0 | 71 | 93 | 86 | 11 | 65 | 38 | 897 | 62 | 19.8 | 13.0 |

### Zone des travaux 2025

| classe | entités | 2026 | 2025 | 2020-2024 | ortho 2022 | web seul | non concluant | non valable 2026 | sans preuve | auto seul | % image | % ≥ 2024 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| arbre | 71 | 0 | 1 | 4 | 15 | 0 | 0 | 5 | 46 | 12 | 28.2 | 7.0 |
| marquage | 132 | 0 | 0 | 0 | 0 | 1 | 1 | 11 | 119 | 0 | 0.0 | 0.0 |
| bordure | 96 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 94 | 0 | 0.0 | 0.0 |
| surface_ilot | 266 | 0 | 2 | 0 | 0 | 3 | 0 | 4 | 257 | 0 | 0.8 | 0.8 |
| ponctuel_sol | 11 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 10 | 0 | 9.1 | 9.1 |
| candelabre_poteau | 17 | 0 | 11 | 0 | 2 | 0 | 0 | 3 | 1 | 0 | 76.5 | 64.7 |
| panneau | 14 | 0 | 6 | 1 | 0 | 0 | 1 | 1 | 5 | 0 | 50.0 | 50.0 |
| feu | 12 | 0 | 1 | 2 | 0 | 0 | 0 | 3 | 6 | 0 | 25.0 | 25.0 |
| potelet_borne | 3 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0.0 | 0.0 |
| cloture_barriere | 10 | 0 | 0 | 0 | 1 | 0 | 2 | 0 | 7 | 0 | 10.0 | 0.0 |
| mobilier | 14 | 0 | 1 | 0 | 1 | 2 | 0 | 0 | 10 | 0 | 14.3 | 7.1 |
| **total** | 646 | 0 | 23 | 7 | 19 | 6 | 6 | 30 | 555 | 12 | 7.6 | 4.6 |

Rôle des observations : ajout 193, conflit_ajout 5, contexte 41, entite 1231, non_apparie 3, temporaire 2. « contexte » et « temporaire » ne sont jamais fusionnés (FUS-CTX-01, FUS-TMP-01) ; « conflit_ajout » : ajout remplacé par un conflit avec le levé GAM (FUS-ADD-04) ; « non_apparie » : observations sans lien ni candidat (voir l'index).

Attributs mis à jour : materiau_id 45, essence 18, hauteur_m 15, usure 14, couleur_mat 10, couronne_m 9, type 7, classe 5, etat 5, azimut_deg 3, nb_lanternes 3, bouton_appel 2, diametre_m 2, largeur_m 2, modulation 2, nb_crosses 2, porte_a_faux_m 2, signal_sonore 2, vibreur 2.

## Contrôle croisé avec la cohérence (`coherence/corrections.geojson`)

31 corrections de cohérence ont une preuve image. Positions : corrobore_avant_travaux 1, indifferent 1, non_conclu_sans_mesure 16, non_contredit 4, partiel 6. Azimuts : accord 3 (FUS-COH-01).

| entité | cohérence | verdict image | écart image / corrigé | écart image / origine | obs |
|---|---|---|---|---|---|
| `ADD-BTN-MP-0580-b` | proposition_ajout  m | corrobore_avant_travaux |  |  | VISION-PANORAMAX-2-31 |
| `arbre_020` | deplacement 0.5 m | non_conclu_sans_mesure |  |  | ORTHO-B-214 |
| `arbre_063` | deplacement 0.05 m | non_conclu_sans_mesure |  |  | ORTHO_A-0048 |
| `arbre_109` | non_instanciation  m | non_contredit |  |  | ORTHO-B-240 |
| `arbre_173` | deplacement 0.85 m | non_conclu_sans_mesure |  |  | ORTHO-B-347 |
| `arbre_279` | deplacement 0.15 m | non_conclu_sans_mesure |  |  | MLY-ARB-039 |
| `arbre_302` | deplacement 0.55 m | non_conclu_sans_mesure |  |  | ORTHO-B-228 |
| `arbre_385` | deplacement 0.05 m | non_conclu_sans_mesure |  |  | ORTHO-B-324 |
| `arbre_396` | deplacement 1.85 m | non_conclu_sans_mesure |  |  | MLY-ARB-051 |
| `arbre_427` | deplacement 0.75 m | non_conclu_sans_mesure |  |  | ORTHO-B-262 |
| `lamp_12668578865` | deplacement 0.45 m | non_conclu_sans_mesure |  |  | ORTHO-B-188 |
| `lamp_9514795718` | deplacement 0.05 m | non_conclu_sans_mesure |  |  | ORTHO-B-204 |
| `lamp_9514828418` | deplacement 0.05 m | non_conclu_sans_mesure |  |  | ORTHO-B-167 |
| `lamp_9514828431` | deplacement 0.1 m | partiel | 1.979 | 1.883 | PANO2026-019 |
| `lamp_9514828820` | deplacement 0.05 m | non_conclu_sans_mesure |  |  | ORTHO-B-135 |
| `lamp_9665416617` | deplacement 0.05 m | non_conclu_sans_mesure |  |  | ORTHO_A-0188 |
| `lamp_9665416717` | deplacement 0.1 m | partiel | 0.837 | 0.876 | ORTHO_A-0167 |
| `lamp_9665416817` | deplacement 0.65 m | partiel | 0.436 | 0.581 | VISION-PANORAMAX-1-55, VISION-PANORAMAX-2-57 |
| `mat_camera_SW_TPC` | deplacement 0.05 m | partiel | 1.583 | 1.59 | pano_0-47 |
| `pan_B1_1` | reorientation  m |  ; azimut accord (45.0° / 65.0°) |  |  |  |
| `pan_B2a_1` | deplacement+reorientation 1.05 m |  ; azimut accord (45.0° / 50.0°) |  |  |  |
| `pan_B6a1_1` | deplacement 0.016 m | partiel | 0.698 | 0.683 | PANO2026-018 |
| `pan_C113_1` | reorientation  m |  ; azimut accord (55.0° / 65.0°) |  |  |  |
| `pan_C13a_1` | deplacement 0.016 m | partiel | 0.698 | 0.683 | PANO2026-018 |
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
| `pan_AB3a_3` | deplacement | 4.147 | 0.15 | appliquer | triangulation | PANO2026-016 |  |
| `poteau_reseau_12888056356` | deplacement | 3.29 | 0.4 | appliquer | triangulation | pano_0-20 |  |
| `lamp_12668620636` | deplacement | 1.826 | 0.188 | appliquer | pixel_ortho | ORTHO-B-209 |  |
| `poteau_reseau_12888048898` | deplacement | 1.814 | 0.35 | appliquer | triangulation | pano_0-21 |  |
| `lamp_9530354517` | deplacement | 1.2 | 0.188 | appliquer | pixel_ortho | ORTHO-B-109 |  |
| `pan_AB4_2` | deplacement | 0.922 | 0.3 | appliquer | triangulation | PANO2026-015 |  |
| `lamp_9665416717` | deplacement | 0.876 | 0.25 | appliquer | pixel_ortho | ORTHO_A-0167 |  |
| `lamp_9514828517` | affinage | 0.699 | 0.05 | appliquer | triangulation | PANO2026-018 |  |
| `pan_B6a1_1` | affinage | 0.683 | 0.05 | appliquer | triangulation | PANO2026-018 |  |
| `pan_C13a_1` | affinage | 0.683 | 0.05 | appliquer | triangulation | PANO2026-018 |  |
| `lamp_9665416817` | affinage | 0.581 | 0.083 | appliquer | triangulation | VISION-PANORAMAX-1-55, VISION-PANORAMAX-2-57 |  |
| `arbre_224` | deplacement | 7.823 | 1.874 | revue_requise | coordonnees_inventaire, triangulation | DOC-LOCALE-018, VISION-PANORAMAX-2-13 | σ fusion 1.87 m > 0,5 m; σ fusion 1.87 m > preuve de la description (0.05 m); objet levé GAM : déplacement > 0,5 m (FUS-POS-06) |
| `banc_8360664518` | deplacement | 4.474 | 0.375 | revue_requise | pixel_ortho | ORTHO_A-0100 | aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines) |
| `potelet_12462947806` | deplacement | 1.969 | 0.375 | revue_requise | pixel_ortho | ORTHO_A-0081 | une seule source non triangulée et pas de correction affirmée |
| `lamp_9514828431` | deplacement | 1.883 | 0.6 | revue_requise | triangulation | PANO2026-019 | σ fusion 0.60 m > 0,5 m |
| `mat_camera_SW_TPC` | deplacement | 1.59 | 0.25 | revue_requise | triangulation | pano_0-47 | aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines) |
| `armoire_1313238971` | deplacement | 1.044 | 0.188 | revue_requise | pixel_ortho | ORTHO-B-171 | une seule source non triangulée et pas de correction affirmée |
| `K-0227` | translation | 0.868 | 0.188 | revue_requise | pixel_ortho | ORTHO_A-0019 | géométrie levée GAM : translation > 0,5 m (FUS-POS-06) |

## Existence : entités absentes en 2026 ou à retirer

- `K-0470` (None) : **retirer** (doublon de `K-0469`) ; obs OR-V-015
- `K-0472` (None) : **retirer** (doublon de `K-0471`) ; obs OR-V-016
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
- `ML-0238` (ligne) : **retirer** ; obs MLY-MAR-002
- `ML-0240` (ligne) : **retirer** ; obs MLY-MAR-003
- `ML-0432` (ligne) : **retirer** ; obs PANO2026-004
- `ML-0930` (ligne) : **retirer** ; obs ORTHO-B-206
- `ML-0935` (ligne) : **retirer** ; obs MLY-MAR-006
- `ML-5141` (ligne) : **retirer** ; obs MLY-MAR-011, OR-V-022
- `MZ-5002` (zone) : **retirer** ; obs MLY-CON-017
- `arbre_013` (feuillu) : **absent_2026** ; obs PANO2026-026
- `arbre_015` (feuillu) : **absent_2026** ; obs PANO2026-027
- `arbre_175` (feuillu) : **absent_2026** [retire_entre_dates] ; obs OR-V-003, ORTHO_A-0192

## Ajouts

189 objets nouveaux (groupes d'observations), dont 125 instanciables. Par classe (instanciés / candidats) : arbre 10/4, autre 0/9, avaloir 9/1, candelabre 3/2, cloture 2/0, feu 0/2, haie 5/2, marquage 30/10, massif 3/0, mobilier 8/9, panneau 8/4, potelet 0/2, surface 7/1, tampon 40/18.

5 ajouts proposés sont remplacés par un conflit `ajout_contre_leve_gam` (FUS-ADD-04, rayon 1.5 m) : DOC-LOCALE-016 (lignes_de_voie_vercors) à 1.309 m de `ML-5228`; DOC-LOCALE-017 (lignes_de_voie_vercors) à 0.918 m de `ML-5401`; ORTHO-B-090 (symbole_velo) à 0.659 m de `MS-5000`; ORTHO_A-0033 (t_stationnement) à 1.423 m de `ML-5159`; ORTHO_A-0034 (lignes_stationnement) à 0.675 m de `ML-5159`.

| id | classe | sous-types | famille cible | preuve | valide 2026 | instancier | obs |
|---|---|---|---|---|---|---|---|
| `ENR-ARB-001` | arbre | jeunes_arbres_alignement | vegetation.arbres | ortho_2022 | True | oui | ORTHO_A-0004 |
| `ENR-ARB-002` | arbre | arbre_inventaire_metropole | vegetation.arbres | web | True | non : aucune observation valide 2026 en confiance ≥ moyenne | DOC-LOCALE-034 |
| `ENR-ARB-003` | arbre | arbustes_conifères | vegetation.arbres | ortho_2022 | True | oui | ORTHO_A-0045 |
| `ENR-ARB-004` | arbre | petit_arbre | vegetation.arbres | ortho_2022 | True | oui | ORTHO_A-0090 |
| `ENR-ARB-005` | arbre | souche_ou_massif | vegetation.arbres | ortho_2022 | True | oui | ORTHO_A-0120 |
| `ENR-ARB-006` | arbre | grand_feuillu | vegetation.arbres | ortho_2022 | True | oui | ORTHO_A-0119 |
| `ENR-ARB-007` | arbre | petit_arbre_fleuri | vegetation.arbres | ortho_2022 | True | oui | ORTHO-B-042 |
| `ENR-ARB-008` | arbre | petit_arbre_fleuri | vegetation.arbres | ortho_2022 | True | oui | ORTHO-B-041 |
| `ENR-ARB-009` | arbre | feuillu | vegetation.arbres | ortho_2022 | True | oui | ORTHO_A-0153 |
| `ENR-ARB-010` | arbre | feuillage_pourpre | vegetation.arbres | ortho_2022 | True | oui | ORTHO_A-0152 |
| `ENR-ARB-011` | arbre | arbustes_boules | vegetation.arbres | ortho_2022 | True | oui | ORTHO_A-0154 |
| `ENR-ARB-012` | arbre | arbre_inventaire_metropole | vegetation.arbres | web | True | non : aucune observation valide 2026 en confiance ≥ moyenne | DOC-LOCALE-024 |
| `ENR-ARB-013` | arbre | arbre_inventaire_metropole | vegetation.arbres | web | True | non : aucune observation valide 2026 en confiance ≥ moyenne | DOC-LOCALE-025 |
| `ENR-ARB-014` | arbre | arbre_inventaire_metropole | vegetation.arbres | web | True | non : aucune observation valide 2026 en confiance ≥ moyenne | DOC-LOCALE-032 |
| `ENR-AUT-001` | autre | objet_vertical_blanc | - | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | ORTHO_A-0044 |
| `ENR-AUT-002` | autre | cables_transversaux | - | photo_2025 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | VISION-PANORAMAX-1-73 |
| `ENR-AUT-003` | autre | portique_entree | - | photo_2025 | True | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | pano_0-18 |
| `ENR-AUT-004` | autre | escalier_garde_corps | - | ortho_2022 | True | non : famille cible inexistante dans la description | ORTHO_A-0131 |
| `ENR-AUT-005` | autre | aire_de_jeux | - | ortho_2022 | True | non : famille cible inexistante dans la description | ORTHO_A-0157 |
| `ENR-AUT-006` | autre | objet_blanc_bas | - | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description; observations « incertain » seulement | ORTHO-B-029 |
| `ENR-AUT-007` | autre | ligne_sombre_continue | - | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | ORTHO-B-004 |
| `ENR-AUT-008` | autre | coffret_maconne | - | photo_2025 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | VISION-PANORAMAX-2-36 |
| `ENR-AUT-009` | autre | anneaux_sombres_pelouse | - | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | ORTHO_A-0180 |
| `ENR-CLO-001` | cloture | grillages_tennis | mobilier.cloture | ortho_2022 | True | oui | ORTHO_A-0018 |
| `ENR-CLO-002` | cloture | portail_coulissant | mobilier.cloture | ortho_2022 | True | oui | ORTHO_A-0110 |
| `ENR-FEU-001` | feu | support_pietons_R12_bouton | signaux.feux | - | False | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | pano_0-52 |
| `ENR-FEU-002` | feu | boitier_appel_pietons | signaux.feux | photo_2025 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | VISION-PANORAMAX-2-31 |
| `ENR-MAR-001` | marquage | hachures | marquages | ortho_2022 | True | oui | ORTHO_A-0002 |
| `ENR-MAR-002` | marquage | bande_centrale_hachuree | marquages | ortho_2022 | True | oui | ORTHO_A-0005 |
| `ENR-MAR-003` | marquage | places_parking | marquages | ortho_2022 | True | oui | ORTHO_A-0006 |
| `ENR-MAR-004` | marquage | places_parking | marquages | ortho_2022 | True | oui | ORTHO_A-0025 |
| `ENR-MAR-005` | marquage | damier | marquages | ortho_2022 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0028 |
| `ENR-MAR-006` | marquage | hachures | marquages | ortho_2022 | True | oui | ORTHO_A-0036 |
| `ENR-MAR-007` | marquage | hachures | marquages | ortho_2022 | True | oui | ORTHO_A-0035 |
| `ENR-MAR-008` | marquage | pictogrammes_pmr_bleus | marquages | ortho_2022 | True | oui | ORTHO_A-0066 |
| `ENR-MAR-009` | marquage | places_parking_jardinerie_o | marquages | ortho_2022 | True | oui | ORTHO_A-0067 |
| `ENR-MAR-010` | marquage | places_en_epi_contre_allee | marquages | ortho_2022 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-154 |
| `ENR-MAR-011` | marquage | ligne_discontinue_stationnement | marquages | ortho_2022 | True | oui | ORTHO_A-0041 |
| `ENR-MAR-012` | marquage | damier | marquages | - | False | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0099 |
| `ENR-MAR-013` | marquage | ligne_place_stationnement | marquages | ortho_2022 | True | oui | ORTHO-B-059 |
| `ENR-MAR-014` | marquage | logo_velo_piste | marquages | ortho_2022 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0101 |
| `ENR-MAR-015` | marquage | ilot_peint_ocre | marquages | ortho_2022 | True | oui | ORTHO-B-100 |
| `ENR-MAR-016` | marquage | ligne_place_stationnement | marquages | ortho_2022 | True | oui | ORTHO-B-060 |
| `ENR-MAR-017` | marquage | ligne_place_stationnement | marquages | ortho_2022 | True | oui | ORTHO-B-058 |
| `ENR-MAR-018` | marquage | ligne_place_stationnement | marquages | ortho_2022 | True | oui | ORTHO-B-057 |
| `ENR-MAR-019` | marquage | ligne_place_stationnement | marquages | ortho_2022 | True | oui | ORTHO-B-056 |
| `ENR-MAR-020` | marquage | ilot_peint_ocre | marquages | ortho_2022 | True | oui | ORTHO-B-101 |
| `ENR-MAR-021` | marquage | lignes_places_terrasse | marquages | ortho_2022 | True | oui | ORTHO-B-142 |
| `ENR-MAR-022` | marquage | ligne_place_stationnement | marquages | ortho_2022 | True | oui | ORTHO-B-053 |
| `ENR-MAR-023` | marquage | ligne_place_stationnement | marquages | ortho_2022 | True | oui | ORTHO-B-052 |
| `ENR-MAR-024` | marquage | ligne_place_stationnement | marquages | ortho_2022 | True | oui | ORTHO-B-054 |
| `ENR-MAR-025` | marquage | ligne_place_stationnement | marquages | ortho_2022 | True | oui | ORTHO-B-055 |
| `ENR-MAR-026` | marquage | ligne_place_stationnement | marquages | ortho_2022 | True | oui | ORTHO-B-051 |
| `ENR-MAR-027` | marquage | places_parking_jardinerie | marquages | ortho_2022 | True | oui | ORTHO_A-0111 |
| `ENR-MAR-028` | marquage | lignes_stationnement_parking | marquages | ortho_2022 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0102 |
| `ENR-MAR-029` | marquage | zigzag_arret_ancien | marquages | - | False | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | ORTHO-B-085 |
| `ENR-MAR-030` | marquage | zone_jaune_croix | marquages | ortho_2022 | True | oui | ORTHO_A-0126 |
| `ENR-MAR-031` | marquage | traversee_cyclable_verte | marquages | - | False | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | pano_0-46 |
| `ENR-MAR-032` | marquage | chiffre_vitesse_50 | marquages | photo_2025 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | pano_0-45 |
| `ENR-MAR-033` | marquage | ligne_place_stationnement | marquages | ortho_2022 | True | oui | ORTHO-B-081 |
| `ENR-MAR-034` | marquage | logo_velo_piste | marquages | ortho_2022 | True | oui | ORTHO_A-0162 |
| `ENR-MAR-035` | marquage | paves_jaunes_traversee_cyclable, traversee_cyclable_jaune | marquages | photo_2026 | True | oui | ORTHO-B-130, PANO2026-008 |
| `ENR-MAR-036` | marquage | paves_jaunes_traversee_cyclable | marquages | photo_2026 | True | oui | PANO2026-009 |
| `ENR-MAR-037` | marquage | ligne_continue_axiale | marquages | photo_2026 | True | oui | PANO2026-011 |
| `ENR-MAR-038` | marquage | ligne_effet_stop | marquages | photo_2026 | True | oui | PANO2026-010 |
| `ENR-MAR-039` | marquage | bandes_traversee_vercors | marquages | ortho_2022 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-127 |
| `ENR-MAR-040` | marquage | nez_ilot_peint | marquages | ortho_2022 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0159 |
| `ENR-MAT-001` | candelabre | borne_globe | mobilier.lampadaire | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0122 |
| `ENR-MAT-002` | candelabre | lampadaire_pieton | mobilier.lampadaire | ortho_2022 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-164 |
| `ENR-MAT-003` | candelabre | borne_lumineuse_globe | mobilier.lampadaire | ortho_2022 | True | oui | ORTHO_A-0156 |
| `ENR-MAT-004` | candelabre | lampadaire_pieton | mobilier.lampadaire | ortho_2022 | True | oui | ORTHO-B-163 |
| `ENR-MAT-005` | candelabre | mat_droit_residentiel | mobilier.lampadaire | photo_2020_2024 | True | oui | VISION-PANORAMAX-1-78 |
| `ENR-MOB-001` | mobilier | cage_metallique | mobilier | ortho_2022 | True | oui | ORTHO_A-0024 |
| `ENR-MOB-002` | mobilier | abri_ou_range_velos | mobilier | ortho_2022 | True | oui | ORTHO-B-210 |
| `ENR-MOB-003` | mobilier | coffret | mobilier | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0080 |
| `ENR-MOB-004` | mobilier | bloc_rocheux_alignement | mobilier | ortho_2022 | True | oui | ORTHO_A-0029 |
| `ENR-MOB-005` | mobilier | conteneurs | mobilier | ortho_2022 | True | oui | ORTHO-B-172 |
| `ENR-MOB-006` | mobilier | blocs_rocheux | mobilier | ortho_2022 | True | oui | ORTHO_A-0074 |
| `ENR-MOB-007` | mobilier | objet_rectangulaire | mobilier | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | ORTHO-B-112 |
| `ENR-MOB-008` | mobilier | butees_de_roues | mobilier | ortho_2022 | True | oui | ORTHO-B-078 |
| `ENR-MOB-009` | mobilier | objet_rouge | mobilier | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0121 |
| `ENR-MOB-010` | mobilier | arceaux_velos | mobilier | - | False | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | VISION-PANORAMAX-1-90 |
| `ENR-MOB-011` | mobilier | stationnement_trottinettes | mobilier | - | False | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | ORTHO-B-067 |
| `ENR-MOB-012` | mobilier | coffret_ou_borne | mobilier | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0113 |
| `ENR-MOB-013` | mobilier | conteneurs_dechets | mobilier | ortho_2022 | True | oui | ORTHO_A-0130 |
| `ENR-MOB-014` | mobilier | bancs | mobilier | ortho_2022 | True | oui | ORTHO_A-0155 |
| `ENR-MOB-015` | mobilier | coffre_ou_abri_conteneurs | mobilier | - | False | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-080 |
| `ENR-MOB-016` | mobilier | armoire_commande_feux_probable | mobilier | photo_2020_2024 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | VISION-PANORAMAX-2-1 |
| `ENR-MOB-017` | mobilier | objet_blanc | mobilier | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | ORTHO-B-095 |
| `ENR-PAN-001` | panneau | C1a_reserve | signaux.panneaux | photo_2026 | True | non : aucune observation valide 2026 en confiance ≥ moyenne | PANO2026-043 |
| `ENR-PAN-002` | panneau | plaque_de_rue | signaux.panneaux | photo_2025 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | pano_0-2 |
| `ENR-PAN-003` | panneau | D21_double | signaux.panneaux | - | False | non : aucune observation valide 2026 en confiance ≥ moyenne | VISION-PANORAMAX-1-41 |
| `ENR-PAN-004` | panneau | panneau_parking_prive | signaux.panneaux | photo_2026 | True | oui | PANO2026-022 |
| `ENR-PAN-005` | panneau | panneau_parking_prive | signaux.panneaux | photo_2026 | True | oui | PANO2026-021 |
| `ENR-PAN-006` | panneau | panneau_parking_prive | signaux.panneaux | photo_2026 | True | oui | PANO2026-020 |
| `ENR-PAN-007` | panneau | fleche_directionnelle_privee | signaux.panneaux | photo_2026 | True | non : aucune observation valide 2026 en confiance ≥ moyenne | PANO2026-042 |
| `ENR-PAN-008` | panneau | plaque_de_rue | signaux.panneaux | photo_2025 | True | oui | VISION-PANORAMAX-2-37 |
| `ENR-PAN-009` | panneau | panneau_information_2_poteaux | signaux.panneaux | photo_2026 | True | oui | PANO2026-017 |
| `ENR-PAN-010` | panneau | C13a_dos, C13a_nom_de_rue | signaux.panneaux | photo_2026 | True | oui | ORTHO-B-126, PANO2026-023 |
| `ENR-PAN-011` | panneau | panneau_large_ilot_nord | signaux.panneaux | ortho_2022 | True | oui | ORTHO-B-125 |
| `ENR-PAN-012` | panneau | AB3a_dos | signaux.panneaux | photo_2026 | True | oui | PANO2026-024 |
| `ENR-PON-001` | avaloir | grille | ponctuels_sol.avaloir | ortho_2022 | True | oui | ORTHO_A-0020 |
| `ENR-PON-002` | tampon | regard_carre | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO_A-0022 |
| `ENR-PON-003` | avaloir | grille | ponctuels_sol.avaloir | ortho_2022 | True | oui | ORTHO_A-0021 |
| `ENR-PON-004` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO_A-0023 |
| `ENR-PON-005` | avaloir | grille | ponctuels_sol.avaloir | ortho_2022 | True | oui | ORTHO-B-180 |
| `ENR-PON-006` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-181 |
| `ENR-PON-007` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-186 |
| `ENR-PON-008` | tampon | tampons_ronds_cour | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO_A-0075 |
| `ENR-PON-009` | tampon | disque_beton_clair | ponctuels_sol.tampon | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0079 |
| `ENR-PON-010` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-185 |
| `ENR-PON-011` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | non : arbitrage ARB-001 (FUS-ARB-01) : tache d'enrobé sombre aux bords flous, sans anneau ni cadre : pas un tampon (le tampon rond voisin, net, est un autre objet) | ORTHO-B-187 |
| `ENR-PON-012` | avaloir | grille_carree | ponctuels_sol.avaloir | ortho_2022 | True | oui | ORTHO-B-179 |
| `ENR-PON-013` | avaloir | grille_carree | ponctuels_sol.avaloir | ortho_2022 | True | oui | ORTHO-B-182 |
| `ENR-PON-014` | tampon | regard_carre | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO_A-0037 |
| `ENR-PON-015` | tampon | regard_carre | ponctuels_sol.tampon | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0077 |
| `ENR-PON-016` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-183 |
| `ENR-PON-017` | avaloir | grille | ponctuels_sol.avaloir | ortho_2022 | True | oui | ORTHO_A-0078 |
| `ENR-PON-018` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-184 |
| `ENR-PON-019` | tampon | regard_petit | ponctuels_sol.tampon | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0038 |
| `ENR-PON-020` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO_A-0076 |
| `ENR-PON-021` | tampon | regard_carre | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-155 |
| `ENR-PON-022` | tampon | regard_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO_A-0039 |
| `ENR-PON-023` | tampon | regard_carre | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-114 |
| `ENR-PON-024` | tampon | regard_carre | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-120 |
| `ENR-PON-025` | tampon | regard_carre | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-143 |
| `ENR-PON-026` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-113 |
| `ENR-PON-027` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-110 |
| `ENR-PON-028` | tampon | regard_carre | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-111 |
| `ENR-PON-029` | tampon | regard_carre | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-065 |
| `ENR-PON-030` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-074 |
| `ENR-PON-031` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-070 |
| `ENR-PON-032` | tampon | regard_carre | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-115 |
| `ENR-PON-033` | tampon | regard_carre | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-073 |
| `ENR-PON-034` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-072 |
| `ENR-PON-035` | tampon | tampon_rond | ponctuels_sol.tampon | - | False | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-071 |
| `ENR-PON-036` | avaloir | grille | ponctuels_sol.avaloir | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-117 |
| `ENR-PON-037` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-118 |
| `ENR-PON-038` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-116 |
| `ENR-PON-039` | tampon | regard_carre | ponctuels_sol.tampon | - | False | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-075 |
| `ENR-PON-040` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-069 |
| `ENR-PON-041` | tampon | regard_rectangulaire | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO_A-0112 |
| `ENR-PON-042` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-043 |
| `ENR-PON-043` | tampon | regard_carre | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-024 |
| `ENR-PON-044` | avaloir | grille | ponctuels_sol.avaloir | ortho_2022 | True | oui | ORTHO_A-0128 |
| `ENR-PON-045` | tampon | petit_regard | ponctuels_sol.tampon | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0129 |
| `ENR-PON-046` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-025 |
| `ENR-PON-047` | avaloir | grille | ponctuels_sol.avaloir | ortho_2022 | True | oui | ORTHO_A-0127 |
| `ENR-PON-048` | tampon | regard | ponctuels_sol.tampon | ortho_2022 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0144 |
| `ENR-PON-049` | tampon | bouche_a_cle | ponctuels_sol.tampon | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-036 |
| `ENR-PON-050` | avaloir | grille_avaloir | ponctuels_sol.avaloir | ortho_2022 | True | oui | ORTHO-B-035 |
| `ENR-PON-051` | tampon | tampon_rond | ponctuels_sol.tampon | - | False | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-028 |
| `ENR-PON-052` | tampon | regard | ponctuels_sol.tampon | ortho_2022 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0140 |
| `ENR-PON-053` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-026 |
| `ENR-PON-054` | tampon | tampon_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-027 |
| `ENR-PON-055` | tampon | regard_grille | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-086 |
| `ENR-PON-056` | tampon | regard | ponctuels_sol.tampon | ortho_2022 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0142 |
| `ENR-PON-057` | tampon | regard | ponctuels_sol.tampon | ortho_2022 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0141 |
| `ENR-PON-058` | tampon | regard | ponctuels_sol.tampon | ortho_2022 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0143 |
| `ENR-PON-059` | tampon | regard | ponctuels_sol.tampon | ortho_2022 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0139 |
| `ENR-PON-060` | tampon | regard_rond | ponctuels_sol.tampon | photo_2025 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | VISION-PANORAMAX-1-23 |
| `ENR-PON-061` | tampon | regard | ponctuels_sol.tampon | ortho_2022 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0145 |
| `ENR-PON-062` | tampon | regard_carre | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-030 |
| `ENR-PON-063` | tampon | regard_carre | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-031 |
| `ENR-PON-064` | tampon | regard_carre | ponctuels_sol.tampon | - | False | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-033 |
| `ENR-PON-065` | tampon | regard_carre | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-032 |
| `ENR-PON-066` | tampon | regard_dalle | ponctuels_sol.tampon | photo_2026 | True | oui | PANO2026-033 |
| `ENR-PON-067` | tampon | regard_rond | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO_A-0166 |
| `ENR-PON-068` | tampon | regard_grille | ponctuels_sol.tampon | ortho_2022 | True | oui | ORTHO-B-097 |
| `ENR-POT-001` | potelet | borne_blanche | mobilier.potelet | ortho_2022 | True | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | ORTHO-B-037 |
| `ENR-POT-002` | potelet | file_de_potelets, file_potelets_inox | mobilier.potelet | photo_2020_2024 | True | non : aucune observation valide 2026 en confiance ≥ moyenne | VISION-PANORAMAX-2-48, pano_0-48 |
| `ENR-SUR-001` | surface | reprise_enrobe | surfaces | ortho_2022 | True | oui | ORTHO-B-178 |
| `ENR-SUR-002` | surface | reprise_enrobe | surfaces | ortho_2022 | True | oui | ORTHO-B-066 |
| `ENR-SUR-003` | surface | reprise_enrobe | surfaces | ortho_2022 | True | oui | ORTHO-B-034 |
| `ENR-SUR-004` | surface | cheminement_pieton_neuf_rive_E_Vercors | surfaces | web | True | oui | DOC-LOCALE-004 |
| `ENR-SUR-005` | surface | allee_stabilisee | surfaces | ortho_2024 | True | oui | OR-V-017 |
| `ENR-SUR-006` | surface | trottoir_beton | surfaces | ortho_2024 | True | oui | OR-V-018 |
| `ENR-SUR-007` | surface | sous_zone_parking | surfaces | ortho_2024 | True | oui | OR-V-019 |
| `ENR-SUR-008` | surface | lits_mineraux_2024 | surfaces | ortho_2024 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | OR-V-020 |
| `ENR-VEG-001` | haie | haie_basse_taillee, haie_taillee | vegetation.haies | photo_2020_2024 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-076, pano_0-54 |
| `ENR-VEG-002` | haie | haie_taillee_parking_Reviree | vegetation.haies | photo_2025 | True | oui | VISION-PANORAMAX-1-26 |
| `ENR-VEG-003` | massif | massif_paille | vegetation.massifs | ortho_2022 | True | oui | ORTHO-B-038 |
| `ENR-VEG-004` | haie | haie_taillee_persistante | vegetation.haies | photo_2025 | True | oui | pano_0-53 |
| `ENR-VEG-005` | haie | haie_taillee_angle_N | vegetation.haies | photo_2025 | True | oui | VISION-PANORAMAX-1-25 |
| `ENR-VEG-006` | haie | haie_haute | vegetation.haies | photo_2026 | True | oui | PANO2026-025 |
| `ENR-VEG-007` | haie | haie_taillee_piste_vercors | vegetation.haies | photo_2025 | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | VISION-PANORAMAX-1-88 |
| `ENR-VEG-008` | haie | haie_taillee | vegetation.haies | photo_2025 | True | oui | VISION-PANORAMAX-2-51 |
| `ENR-VEG-009` | massif | arbustes_tailles_en_blocs | vegetation.massifs | ortho_2022 | True | oui | ORTHO_A-0185 |
| `ENR-VEG-010` | massif | arbustes_tailles_en_blocs | vegetation.massifs | ortho_2022 | True | oui | ORTHO_A-0198 |

## Conflits

100 conflits : ajout_contre_leve_gam 5, attribut_desaccord 1, changement_2026 3, changement_entre_dates 1, coherence_desaccord 6, deplacement_non_etaye 7, doublon_apres_correction 1, lien_introuvable 1, position_anterieure_divergente 1, position_desaccord 11, surface_a_decouper 4, validite_2026_douteuse 59. Détail dans `conflits.json` (les conflits d'information ne sont pas listés ici).

| id | type | cible | obs | détail |
|---|---|---|---|---|
| CF-ENR-001 | ajout_contre_leve_gam | `ML-5159` | ORTHO_A-0033 | objet observé absent de la description (t_stationnement) à 1.42 m de ML-5159 (marquages ligne, levé GAM) : même objet probable ; ajout non créé (FUS-ADD-04) |
| CF-ENR-002 | ajout_contre_leve_gam | `ML-5159` | ORTHO_A-0034 | objet observé absent de la description (lignes_stationnement) à 0.67 m de ML-5159 (marquages ligne, levé GAM) : même objet probable ; ajout non créé (FUS-ADD-04) |
| CF-ENR-003 | ajout_contre_leve_gam | `ML-5228` | DOC-LOCALE-016 | objet observé absent de la description (lignes_de_voie_vercors) à 1.31 m de ML-5228 (marquages ligne, levé GAM) : même objet probable ; ajout non créé (FUS-ADD-04) |
| CF-ENR-004 | ajout_contre_leve_gam | `ML-5401` | DOC-LOCALE-017 | objet observé absent de la description (lignes_de_voie_vercors) à 0.92 m de ML-5401 (marquages ligne, levé GAM) : même objet probable ; ajout non créé (FUS-ADD-04) |
| CF-ENR-005 | ajout_contre_leve_gam | `MS-5000` | ORTHO-B-090 | objet observé absent de la description (symbole_velo) à 0.66 m de MS-5000 (marquages symbole, levé GAM) : même objet probable ; ajout non créé (FUS-ADD-04) |
| CF-ENR-006 | attribut_desaccord | `lamp_9665416817` | MLY-CON-001, VISION-PANORAMAX-1-17, VISION-PANORAMAX-1-43 | couleur_mat : {"\"brun-rouille\"": ["MLY-CON-001", "VISION-PANORAMAX-1-17"], "\"gris anthracite patiné\"": ["VISION-PANORAMAX-1-43"]} |
| CF-ENR-007 | changement_2026 | `ML-5341` | MLY-MAR-016, PANO2026-014 | photo 2026 : present ; images antérieures : retirer (constat d'artefact indépendant de la date contredit par la photo 2026) |
| CF-ENR-008 | changement_2026 | `ML-5342` | MLY-MAR-017, PANO2026-014 | photo 2026 : present ; images antérieures : retirer (constat d'artefact indépendant de la date contredit par la photo 2026) |
| CF-ENR-009 | changement_2026 | `ML-5343` | MLY-MAR-018, PANO2026-014 | photo 2026 : present ; images antérieures : retirer (constat d'artefact indépendant de la date contredit par la photo 2026) |
| CF-ENR-011 | coherence_desaccord | `lamp_9514828431` | PANO2026-019 | cohérence : deplacement de 0.1 m ; image à 1.98 m de la position corrigée et 1.88 m de l'origine (partiel) |
| CF-ENR-012 | coherence_desaccord | `lamp_9665416717` | ORTHO_A-0167 | cohérence : deplacement de 0.1 m ; image à 0.84 m de la position corrigée et 0.88 m de l'origine (partiel) |
| CF-ENR-013 | coherence_desaccord | `lamp_9665416817` | VISION-PANORAMAX-1-55, VISION-PANORAMAX-2-57 | cohérence : deplacement de 0.65 m ; image à 0.44 m de la position corrigée et 0.58 m de l'origine (partiel) |
| CF-ENR-014 | coherence_desaccord | `mat_camera_SW_TPC` | pano_0-47 | cohérence : deplacement de 0.05 m ; image à 1.58 m de la position corrigée et 1.59 m de l'origine (partiel) |
| CF-ENR-015 | coherence_desaccord | `pan_B6a1_1` | PANO2026-018 | cohérence : deplacement de 0.016 m ; image à 0.70 m de la position corrigée et 0.68 m de l'origine (partiel) |
| CF-ENR-016 | coherence_desaccord | `pan_C13a_1` | PANO2026-018 | cohérence : deplacement de 0.016 m ; image à 0.70 m de la position corrigée et 0.68 m de l'origine (partiel) |
| CF-ENR-017 | deplacement_non_etaye | `K-0227` | ORTHO_A-0019 | translation de 0.87 m proposée ; géométrie levée GAM : translation > 0,5 m (FUS-POS-06) |
| CF-ENR-018 | deplacement_non_etaye | `arbre_224` | DOC-LOCALE-018, VISION-PANORAMAX-2-13 | deplacement de 7.82 m proposé ; σ fusion 1.87 m > 0,5 m ; σ fusion 1.87 m > preuve de la description (0.05 m) ; objet levé GAM : déplacement > 0,5 m (FUS-POS-06) |
| CF-ENR-019 | deplacement_non_etaye | `armoire_1313238971` | ORTHO-B-171 | deplacement de 1.04 m proposé ; une seule source non triangulée et pas de correction affirmée |
| CF-ENR-020 | deplacement_non_etaye | `banc_8360664518` | ORTHO_A-0100 | deplacement de 4.47 m proposé ; aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines) |
| CF-ENR-021 | deplacement_non_etaye | `lamp_9514828431` | PANO2026-019 | deplacement de 1.88 m proposé ; σ fusion 0.60 m > 0,5 m |
| CF-ENR-022 | deplacement_non_etaye | `mat_camera_SW_TPC` | pano_0-47 | deplacement de 1.59 m proposé ; aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines) |
| CF-ENR-023 | deplacement_non_etaye | `potelet_12462947806` | ORTHO_A-0081 | deplacement de 1.97 m proposé ; une seule source non triangulée et pas de correction affirmée |
| CF-ENR-024 | doublon_apres_correction | `poteau_reseau_12888056356` | pano_0-20 | position corrigée à 0.66 m de lamp_lidar_SW_NO (lampadaire) : même objet probable |
| CF-ENR-025 | lien_introuvable | `BEV-0348-2` | VISION-PANORAMAX-1-24 | id BEV-0348-2 absent de la description courante et sans équivalent spatial |
| CF-ENR-038 | surface_a_decouper | `S-0094a` | ORTHO-B-039, ORTHO-B-099 | surface de 11598 m² (espace_vert, gazon_tondu) contenant des sous-zones observées : gazon_tondu (ORTHO-B-039); enrobe_bbsg_ancien (ORTHO-B-099) |
| CF-ENR-039 | surface_a_decouper | `S-0159a` | ORTHO-B-088 | surface de 4036 m² (parking, enrobe_bbsg_ancien) contenant des sous-zones observées : |
| CF-ENR-040 | surface_a_decouper | `S-0161a` | ORTHO-B-077, ORTHO-B-149, ORTHO-B-156 | surface de 10647 m² (parking, enrobe_bbsg_ancien) contenant des sous-zones observées : gravier (ORTHO-B-077); eau_bassin (ORTHO-B-149) |
| CF-ENR-041 | surface_a_decouper | `S-0374a` | MLY-SUR-087 | surface de 2072 m² (espace_vert, gazon_tondu) contenant des sous-zones observées : herbe_haute (MLY-SUR-087) |
| CF-ENR-073 | validite_2026_douteuse | `K-0078` | ORTHO-B-094 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) tr… |
| CF-ENR-074 | validite_2026_douteuse | `K-0081` | ORTHO-B-094 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) tr… |
| CF-ENR-075 | validite_2026_douteuse | `K-0082` | ORTHO-B-094 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) tr… |
| CF-ENR-076 | validite_2026_douteuse | `K-0083` | ORTHO-B-094 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) tr… |
| CF-ENR-077 | validite_2026_douteuse | `K-0084` | ORTHO-B-094 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) tr… |
| CF-ENR-078 | validite_2026_douteuse | `K-0085` | ORTHO-B-094 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) tr… |
| CF-ENR-079 | validite_2026_douteuse | `K-0086` | ORTHO-B-094 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) tr… |
| CF-ENR-080 | validite_2026_douteuse | `MZ-5002` | ORTHO-B-091 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. rien de peint au point de MZ-5002 (forme en Y, « conserve ») : en… |
| CF-ENR-081 | validite_2026_douteuse | `arbre_022` | ORTHO_A-0046 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. pelouse sans couronne à la position en 05/2022 |
| CF-ENR-082 | validite_2026_douteuse | `arbre_184` | MLY-CON-019, pano_0-16 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. à la position d'arbre_184 : abri voyageurs vitré, barrière et tro… |
| CF-ENR-083 | validite_2026_douteuse | `arbre_229` | MLY-CON-020, pano_0-14 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. haie taillée ≈ 1,2 m sous un grand cèdre plus en retrait ; aucun … |
| CF-ENR-084 | validite_2026_douteuse | `arbre_230` | MLY-CON-021, MLY-CON-022, pano_0-13 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. haie taillée ; poteau bois brun juste à droite de la position ; a… |
| CF-ENR-085 | validite_2026_douteuse | `arbre_269` | ORTHO_A-0196 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. terre nue de chantier à la position en 05/2022 (hors de la couron… |
| CF-ENR-086 | validite_2026_douteuse | `arbre_362` | ORTHO-B-193 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. au point de arbre_362 (h 25,4 m, couronne 13,9 m d'après le LiDAR… |
| CF-ENR-087 | validite_2026_douteuse | `arbre_383` | ORTHO-B-194 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. même cas que arbre_362 : h 22,7 m décrite, sol de chantier nu en … |
| CF-ENR-088 | validite_2026_douteuse | `arbre_435` | ORTHO_A-0178 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2023-09-11) : non probante pour 2026. pelouse ouverte (en partie à l'ombre des arbres voisins au NO) sa… |
| CF-ENR-089 | validite_2026_douteuse | `barriere_levante_12462947804` | ORTHO-B-189 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-04-08) : non probante pour 2026. aucune lisse ni potence visible au point (voie du parking) en 202… |
| CF-ENR-090 | validite_2026_douteuse | `chicane_12462947805` | ORTHO-B-177 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-03-15) : non probante pour 2026. aucune barrière / chicane visible au point (place de parking marq… |
| CF-ENR-091 | validite_2026_douteuse | `cloture_gam_001` | ORTHO-B-083 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. le tracé GAM de cloture_gam_002 (et cloture_gam_001 dans son prol… |
| CF-ENR-092 | validite_2026_douteuse | `cloture_gam_002` | ORTHO-B-083 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. le tracé GAM de cloture_gam_002 (et cloture_gam_001 dans son prol… |
| CF-ENR-093 | validite_2026_douteuse | `cloture_gam_047` | MLY-MOB-023 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. |
| CF-ENR-094 | validite_2026_douteuse | `cloture_gam_049` | VISION-PANORAMAX-1-64, VISION-PANORAMAX-1-65 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-12-01) : non probante pour 2026. ; aucune clôture le long de la ligne cloture_gam_049 le 18/05/202… |
| CF-ENR-095 | validite_2026_douteuse | `lamp_12758859672` | MLY-CON-026, ORTHO-B-061 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-06-07) : non probante pour 2026. aucun mât à la position (voitures en stationnement, haie) le 24/0… |
| CF-ENR-096 | validite_2026_douteuse | `lamp_12758894668` | ORTHO-B-062 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2026-03-16) : non probante pour 2026. rien au point décrit (bord de la serre) en 2022 ; nœud OSM 2026-0… |
| CF-ENR-097 | validite_2026_douteuse | `lamp_12887274334` | MLY-CON-027, ORTHO-B-151 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-10-25) : non probante pour 2026. massifs arbustifs et haie de la jardinerie, aucun mât à la positi… |
| CF-ENR-098 | validite_2026_douteuse | `lamp_13539965051` | MLY-CON-028, ORTHO-B-141 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2026-02-10) : non probante pour 2026. grand massif arbustif à côté de la rampe d'accès, aucun mât à la … |
| CF-ENR-099 | validite_2026_douteuse | `pan_J5_1` | ORTHO-B-003 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-05-15) : non probante pour 2026. aucune balise ni ombre au point décrit (extrémité NE de l'îlot I-… |
| CF-ENR-100 | validite_2026_douteuse | `stationnement_velos_12673486211` | MLY-MOB-035 | absence (ou retrait proposé) vue sur une image antérieure à la première attestation de l'objet (2025-03-17) : non probante pour 2026. banc-muret béton, rocher et haie ; aucun arceau vélo visible à la… |

## Carte de couverture

`couverture_preuves.png` : A/C preuve image concluante la plus récente par entité et par bordure (rampe bleue ordinale : ortho 2022 clair, 2020-2024, 2025, 2026 foncé ; anneau noir : web seul ; anneau gris : vue sans preuve concluante ou non valable 2026 ; petit point gris : aucune observation), zones refaites en 2025 hachurées, positions des photos citées (croix : Panoramax, point : Mapillary, étoile : photo 2026) ; B/D décisions (carré orange : attribut, flèche : déplacement, à l'échelle au-delà de 1 m et x5 en dessous, losange aqua : ajout, croix : absent / retirer, anneau rouge : conflit). Fond : ortho 2022 éclaircie. `couverture.json` : tableaux de couverture complets.

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
- **FUS-CONF-01** : poids de confiance : haute 1 ; moyenne 0,6 ; faible 0,3 ; contrôle automatique (automatique, automatique_2_dates, automatique_2e_date) x0,7 ; valeur « probable » ou « ? » x0,6.
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
- **FUS-EXI-03** : chronologie : quand présence et absence probantes s'opposent, si toutes les absences sont postérieures à toutes les présences, l'objet est absent en 2026 (retiré entre deux prises de vue, absence ≥ 0,6) ; dans le cas inverse il est présent (posé entre deux prises de vue) ; conflit d'information changement_entre_dates.
- **FUS-EXI-02** : retrait (artefact de la description : faux positif, « à retirer », « à supprimer », doublon) si poids ≥ 0,6 ; retypage (poteau réseau au lieu de lampadaire) si vote explicite ≥ 0,6.
- **FUS-ADD-01** : ajouts : observations absent_de_description (et candidats incertains non appariés) regroupées par lien simple, même groupe de classe, distance ≤ tolérance + min(σi + σj ; 3 m) entre ateliers différents, ≤ tolérance et même sous-type dans un même atelier.
- **FUS-ADD-02** : ajout à moins de la moitié de la tolérance d'une entité existante de même famille : conflit ajout_proche_existant, non instancié. Exceptions : sous-zone ou reprise de surface (la surface est son hôte) ; équipement porté (boîtier, plaque, panonceau : le support voisin est son hôte).
- **FUS-ADD-03** : ajout instancié si au moins une observation valide 2026 (vrai) en confiance ≥ moyenne, non temporaire, famille cible connue ; croisé avec les propositions de cohérence (≤ 3 m) et le levé GAM 2026 des arbres (≤ 2 m).
- **FUS-COH-01** : contrôle croisé avec coherence/corrections.geojson : accord si la position image est à ≤ max(0,35 ; 2σ) de la position corrigée ; désaccord si elle est à cette distance de la position d'origine seulement ; partiel si elle est loin des deux ; les deux dans la tolérance : tendance_accord / tendance_desaccord si l'écart les départage d'au moins σ, sinon indifférent ; confirmations sans mesure : non concluant ; azimut : accord à ≤ 30° ; propositions d'ajout rejointes par une observation : corroborées (datées).
- **FUS-SRC-01** : sources : « ortho2022 » (PCRS 5 cm du 10/05/2022) -> ortho_2022 ; « ortho_recente:<couche> » (IGN 20 cm du 09/08/2024 -> ortho_2024 ; Pléiades 2025 non datée, avant travaux -> ortho_2025) ; « pnx: » (Panoramax) et « mly: » (Mapillary) : photos, catégorie selon la date : photo_2026 (≥ 05/12/2025, fin des travaux), photo_2025, photo_2020_2024 ; autres : documents web.
- **FUS-DATE-01** : priorité photo_2026 : pour l'état 2026, dès qu'une observation photo_2026 de poids > 0 porte sur l'existence, un attribut ou la position d'une entité, elle seule décide de cet aspect ; les observations plus anciennes sont gardées comme antérieures (obs_anterieures_ecartees) ; un désaccord ouvre un conflit d'information changement_2026 ou position_anterieure_divergente (objet déplacé, refait ou retiré pendant les travaux).
- **FUS-AUTO-01** : confirmation automatique d'un marquage sur ortho (contrôles ortho_A / ortho_B 2022, orthos récentes 2024) sans masque véhicules / ombres : requalifiée « incertain » (ni présence, ni preuve de couverture) sauf si une observation manuelle (contrôle visuel ou photo) confirme la même entité avec un poids > 0. Deux contrôles automatiques ne se corroborent pas (erreurs corrélées : voitures garées aux mêmes places, ombres de supports fixes, lignes de places détectées à tort).
- **FUS-AUTO-02** : contrat de tout contrôle automatique futur : il n'est accepté comme confirmation (poids x0,7) que s'il déclare attributs.controle_auto = {masque_vehicules_ombres: true (taches claires ou sombres de plus de 3 m² et de largeur ≥ 1,2 m, ombres portées), part_masquee ≤ 0,2 le long de l'objet, et pour un marquage reponse_ligne_fine: true (trait de 0,10 à 0,15 m répondant sur toute la longueur) ou reponse_peinture: true (flèche, symbole : part peinte ≥ 0,3)} ; calcul de référence : controle_auto.py ; sinon FUS-AUTO-01 (marquages) ou drapeau « automatique seul » (autres classes).
- **FUS-ADD-04** : dédoublonnage des ajouts : entité existante de même classe (type de marquage compatible ; pavés de traversée = passage) dans un rayon max(1,5 m ; tolérance de classe) ; si elle vient d'un levé GAM (marquage, bordure, îlot, arbre, clôture), pas d'ajout : conflit ajout_contre_leve_gam (l'objet vu est probablement l'objet levé, mal placé ou mal typé ; à trancher sur photo 2026 ou terrain). Exception : l'atelier qui signale l'objet a aussi confirmé à la main l'entité levée, sans la retyper (deux objets distingués par le même observateur).
- **FUS-ARB-01** : arbitrages de revue (description/enrichi/arbitrages_fusion.json, clés = identifiants d'observations, jamais les ENR-* renumérotés) : ne_pas_instancier (ajout), ancrer_bord_ilot (ajout ponctuel ramené au bord de l'îlot ou de l'espace vert le plus proche, en retrait vers l'intérieur), mesure_position (coordonnées d'un document utilisées comme mesure de position, σ donné, pondérée comme FUS-POS-01). Chaque arbitrage cite son motif et sa preuve ; un arbitrage sans effet ouvre un conflit arbitrage_inapplicable.
- **FUS-COUV-01** : couverture : preuve image la plus récente, valable 2026 et concluante (présence, attribut, position, ou absence probante ; observations « incertain » et confirmations automatiques requalifiées exclues), par tranche : 2026 > 2025 > 2020-2024 (photos, ortho IGN 2024) > ortho 2022 > web seul ; « non concluant » : vue sans conclusion ; « non valable 2026 » : vue seulement avant sa forme 2026.

## Limites

- Le cœur du carrefour n'a aucune image postérieure aux travaux : les 7 photos du 28/07/2026 sont sur la place, environ 135 m au sud, et seules 3 sont calées. Les objets du cœur refaits en 2025 restent sans preuve concluante ou en « revue_requise » ; une prise de vue terrain (protocole du critique, stations S1 à S12) trancherait.
- Les confirmations automatiques requalifiées ne sont pas des absences : ces marquages restent décrits, sans preuve.
- La description de base est régénérée en parallèle : relancer ce script après chaque régénération (les liens disparus deviennent des conflits `lien_introuvable`).
- Les attributs en texte libre ne sont pas votés : ils restent dans `notes` (revue humaine, `revue_texte`).
- Les poids et seuils (REGLES) sont des choix documentés, pas des mesures ; les sorties restent des propositions pour le composeur et l'arbitrage.
