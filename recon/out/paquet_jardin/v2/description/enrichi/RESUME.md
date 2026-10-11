# Fusion du recensement : couche `description/enrichi/`

Générateur : `python recon/pcg/enrichir/fusion_recensement.py` (fusion_recensement/0.3), déterministe : deux exécutions successives donnent des sorties identiques octet pour octet. Couche séparée : ni la description de base, ni la cohérence, ni les observations ne sont modifiées. Le composeur la fusionnera (priorité arbitré > enrichi vérifié > base).

## Ce qui change en 0.3 (critique de couverture du 10/10/2026)

La couverture publiée en 0.2 était surestimée. La fusion garde désormais deux mesures : la couverture **large** (FUS-COUV-01, définition 0.2, pour comparaison) et la couverture **stricte** (FUS-COUV-02). Toutes les décisions utilisent la stricte : statut « confirmé », application d'un déplacement, d'un attribut ou d'un retrait, carte.

| zone | entités | large 0.2 (publiée) | stricte 0.2 (recomptée par la critique) | large 0.3 | **stricte 0.3** | dont après travaux |
|---|---|---|---|---|---|---|
| Site entier | 3031 | 23.1 % | 13.2 % | 21.4 % | **10.5 %** (319) | 32 |
| Cœur du carrefour (± 80 m) | 1261 | 19.8 % | 11.5 % | 18.3 % | **9.0 %** (113) | 0 |
| Zone des travaux 2025 | 662 | 7.6 % | 3.3 % | 8.0 % | **1.4 %** (9) | 4 |

La large 0.3 applique la définition 0.2 aux liens corrigés (contrôles automatiques des bordures requalifiés, liens groupés sans preuve propre, liens invalidés par une revue). La stricte 0.3 est plus basse que le recomptage de la critique parce qu'elle applique aussi les classes de date relatives aux travaux (cause 3), le plafond de confiance des projections lointaines (FUS-CONF-02) et les liens groupés (FUS-LIEN-09) ; la zone des travaux compte aussi plus d'entités (cause 5).

1. **Preuve stricte (FUS-COUV-02).** Une entité n'est couverte, et « confirmée », que si au moins une observation image manuelle, de confiance moyenne ou haute, valide 2026 et probante la porte. 333 entités qui avaient une preuve au sens large n'ont qu'un indice (confiance faible, validité incertaine, contrôle automatique, lien groupé ou image antérieure aux travaux dans leur emprise). Statuts : a_retirer 26, absent_2026 7, absent_2026_a_verifier 4, confirme 200, conteste 7, corrige 79, indice_seulement 619, non_valable_2026 78 (FUS-STAT-01).
2. **Validité « incertaine » (FUS-VAL-04).** Elle ne prouve plus ni la présence ni l'absence : 135 liens observation-entité concernés ; 36 entités ne reposaient que sur ce type d'observation et passent en « indice seulement ». Les attributs et les mesures la gardent avec le poids 0,5 (toujours en revue).
3. **Dates relatives aux travaux (FUS-DATE-02).** Les 265 observations sur photos de 2025 (12/01 au 31/08/2025, dont 15 du 31/08/2025, en plein chantier) sont toutes antérieures à la fin des travaux. Liens observation-entité : après travaux 60, avant travaux hors emprise 1062, avant travaux dans l'emprise (± 3 m) 264, dont 110 avec un appui de règle (FUS-SRC-001 : marquage conservé, bordure levée GAM hors périmètre refait, surface inchangée, objet attesté après les travaux) et 154 sans appui, devenus non probants.
4. **Contrôles automatiques des bordures (FUS-AUTO-01/02 étendues).** 54 confirmations automatiques de bordures (orthos 2022 et 2024, sans masque véhicules / ombres ni réponse d'arête) : 35 requalifiées « incertain », 19 corroborées par une observation manuelle. La bordure K-0236 citée par la critique (fausse confirmation sur deux dates) n'a plus d'observation : l'atelier des orthos récentes l'a déjà rejetée à l'échantillonnage.
5. **Zone des travaux (FUS-ZONE-01).** Elle comprend maintenant les surfaces dont une photo du 28/07/2026 montre un revêtement neuf : `S-0268a` (chaussee, 1411 m², PANO2026-034), `S-0268d` (chaussee, 13 m², PANO2026-035), `S-0268e` (chaussee, 11 m², PANO2026-035). 16 entités décrites y entrent en plus ; l'état de ces surfaces passe à « modifie_2025 » (mise à jour etat_v1).
6. **Trois cas faux corrigés.** Places ML-5341, ML-5342 et ML-5343 : le lien groupé de PANO2026-014 ne les prouve plus (FUS-LIEN-09 : seules ML-5339, ML-5340 et ML-5344 sont citées dans sa preuve) et le constat de revue ARB-005 (photo f8d91bb1 du 28/07/2026 : enrobé et butées, aucune ligne) les met en « absent_2026_a_verifier » : `ML-5341` absent_2026_a_verifier, `ML-5342` absent_2026_a_verifier, `ML-5343` absent_2026_a_verifier. MLY-MAR-017 (« tracé sur la bande plantée », projection à 25,9 m) n'est plus un constat indépendant de la date (FUS-VAL-02 limité à 15 m) et son lien est invalidé (ARB-004) ; MLY-MAR-016 et MLY-MAR-018, même image à 23,6 et 28,1 m, perdent aussi ce statut. K-0358, masquée par la haie, n'est plus confirmée (ARB-006, et confiance faible) : `K-0358` indice_seulement.
7. **Vote des attributs de bordure (FUS-BOR-01..03).** 188 textes libres de profil lus sur les observations de bordures : vue chiffrée 12, qualificatif explicite 17, vue déduite 17, abaissé 0 ; 141 observations sans lecture de profil. Intervalles votés : accord 16, contradiction 19. Contradictions de vue à vérifier : 8 bordures (K-0118, K-0185, K-0298, K-0435, K-0439, K-0465, K-0511, K-0675) ; pour information : 8 (K-0123, K-0124, K-0509, K-0644, K-0658, K-0662, K-0663, K-0673). Détail dans la section Bordures.

## Dates des images et classes relatives aux travaux

| catégorie (FUS-SRC-01) | source | dates des observations | observations | classe relative aux travaux |
|---|---|---|---|---|
| photo_2026 | Panoramax, 7 photos (3 calées) et constats de revue | 2026-07-28 | 51 | après travaux |
| photo_2025 | Panoramax et Mapillary | 2025-01-12 à 2025-08-31 | 265 | avant travaux (hors ou dans l'emprise selon l'entité) |
| ortho_2025 | Pléiades 2025, 50 cm (non datée) | 2025 (sans date publiée) | 1 | avant travaux (hors ou dans l'emprise selon l'entité) |
| photo_2020_2024 | Panoramax et Mapillary | 2020-05-21 à 2024-08-24 | 301 | avant travaux (hors ou dans l'emprise selon l'entité) |
| ortho_2024 | IGN BD ORTHO, 20 cm | 2024-08-09 | 202 | avant travaux (hors ou dans l'emprise selon l'entité) |
| ortho_2022 | PCRS 5 cm | 2022-05-10 | 624 | avant travaux (hors ou dans l'emprise selon l'entité) |

Travaux du cœur : 23/06 au 05/12/2025 ; trottoirs du Vercors achevés le 30/01/2026. Les seules images de l'état 2026 sont les photos Panoramax du 28/07/2026, prises sur la place, environ 135 m au sud du cœur : aucune ne voit le cœur. Toutes les autres sont antérieures à la fin des travaux, y compris la série à plat du 31/08/2025 (en plein chantier). Une observation antérieure ne vaut pour une entité dans l'emprise des travaux (à 3 m au plus, au point observé pour une ligne ou une surface) que si une règle appuie sa conservation (FUS-DATE-02).

| classe de date (FUS-DATE-02) | liens observation-entité | avec appui de règle | non probants (motifs) |
|---|---|---|---|
| apres_travaux | 60 | 0 | FUS-VAL-04 3 |
| avant_travaux_hors_emprise | 1062 | 0 | FUS-VAL-03 18, FUS-VAL-04 39 |
| avant_travaux_dans_emprise | 264 | 110 | FUS-DATE-02 154, FUS-VAL-03 33, FUS-VAL-04 93 |

Appuis de conservation utilisés : objet attesté après les travaux (66), marquage « conserve » (22), surface « construit_2023_2024 » hors de la zone des travaux (7), bordure levée GAM après travaux, hors périmètre refait (5), surface « inchange_2022 » hors de la zone des travaux (5), îlot à ceinture levée GAM après travaux (5).

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
| `recon/out/paquet_jardin/v2/description/enrichi/arbitrages_fusion.json` (constats de revue, FUS-ARB-01) | 3 |

Total : 1478 observations. Description lue : base v0.3 (`base/`), objets du paquet, instances, bordures du site (carte de cohérence), surfaces v1, corrections et propositions de cohérence, levé GAM 2026 des arbres, arbitrages de revue (`arbitrages_fusion.json`). Les empreintes SHA-256 de toutes les entrées sont dans `observations_index.json` (`meta.entrees`).

## Synthèse

- 1020 entités de la description reçoivent au moins une observation ; 200 sont **confirmées** (preuve stricte, sans correction) ; 79 corrigées ; 7 contestées (vue de bordure) ; 619 n'ont qu'un indice ; 78 ne sont vues qu'avant leur forme 2026 ou sans appui de conservation.
- Attributs : 97 entités ont au moins une mise à jour (121 mises à jour, dont 88 à appliquer et 33 en revue, FUS-ATT-06).
- Position : 18 corrections mesurées, dont 9 à appliquer et 9 en revue (FUS-POS-05/06).
- Existence : 33 entités à retirer ou absentes en 2026 ; 4 absences à vérifier (FUS-EXI-04).
- Ajouts : 189 objets nouveaux, dont 111 instanciables ; 5 ajouts remplacés par un conflit avec le levé GAM (FUS-ADD-04).
- Conflits : 124 (72 à vérifier, 52 pour information).
- Cohérence : 30 corrections du solveur ont une preuve image ; corrobore_avant_travaux 1, indifferent 1, non_conclu_sans_mesure 16, non_contredit 4, partiel 6.

## Couverture

Entités de la description (base v0.3 + objets du paquet). **Stricte** (FUS-COUV-02, décisions) : classe de date de la meilleure preuve stricte (après travaux > avant travaux hors emprise > avant travaux dans l'emprise avec appui de règle). « indice » : vue concluante au sens large sans preuve stricte. **Large** (FUS-COUV-01, définition 0.2, comparaison seulement) : preuve image concluante quelle que soit sa confiance. « auto seul » : preuve large venant uniquement de contrôles automatiques. Cœur : carré ± 80 m autour de l'origine ; zone 2025 : FUS-ZONE-01.

### Site entier

| classe | entités | **stricte %** | après travaux | avant, hors emprise | avant, dans l'emprise (appui) | indice | non concluant | non valable 2026 | sans observation | large % | auto seul | confirmées |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| arbre | 467 | **11.1** | 7 | 41 | 4 | 193 | 35 | 32 | 155 | 50.1 | 143 | 28 |
| marquage | 402 | **20.6** | 9 | 63 | 11 | 12 | 132 | 19 | 156 | 23.4 | 0 | 40 |
| bordure | 512 | **13.1** | 2 | 63 | 2 | 36 | 52 | 7 | 350 | 20.1 | 0 | 57 |
| surface_ilot | 1434 | **4.3** | 7 | 49 | 6 | 63 | 25 | 8 | 1276 | 8.5 | 0 | 35 |
| ponctuel_sol | 12 | **0.0** | 0 | 0 | 0 | 1 | 0 | 1 | 10 | 8.3 | 0 | 0 |
| candelabre_poteau | 52 | **38.5** | 2 | 18 | 0 | 16 | 7 | 3 | 6 | 69.2 | 0 | 13 |
| panneau | 33 | **42.4** | 4 | 8 | 2 | 7 | 2 | 2 | 8 | 63.6 | 0 | 5 |
| feu | 13 | **0.0** | 0 | 0 | 0 | 4 | 0 | 3 | 6 | 30.8 | 0 | 0 |
| potelet_borne | 13 | **53.8** | 0 | 7 | 0 | 3 | 0 | 3 | 0 | 76.9 | 0 | 7 |
| cloture_barriere | 63 | **19.0** | 1 | 11 | 0 | 8 | 16 | 0 | 27 | 31.7 | 0 | 12 |
| mobilier | 30 | **6.7** | 0 | 2 | 0 | 6 | 1 | 0 | 21 | 16.7 | 0 | 2 |
| **total** | 3031 | **10.5** | 32 | 262 | 25 | 349 | 270 | 78 | 2015 | 21.4 | 143 | 199 |

### Cœur du carrefour (± 80 m)

| classe | entités | **stricte %** | après travaux | avant, hors emprise | avant, dans l'emprise (appui) | indice | non concluant | non valable 2026 | sans observation | large % | auto seul | confirmées |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| arbre | 158 | **10.1** | 0 | 12 | 4 | 65 | 6 | 9 | 62 | 48.7 | 49 | 8 |
| marquage | 221 | **16.7** | 0 | 30 | 7 | 4 | 34 | 13 | 133 | 18.1 | 0 | 24 |
| bordure | 204 | **11.3** | 0 | 23 | 0 | 4 | 18 | 5 | 154 | 13.2 | 0 | 23 |
| surface_ilot | 557 | **3.1** | 0 | 15 | 2 | 19 | 10 | 4 | 507 | 5.9 | 0 | 11 |
| ponctuel_sol | 12 | **0.0** | 0 | 0 | 0 | 1 | 0 | 1 | 10 | 8.3 | 0 | 0 |
| candelabre_poteau | 26 | **15.4** | 0 | 4 | 0 | 14 | 3 | 3 | 2 | 69.2 | 0 | 1 |
| panneau | 21 | **47.6** | 0 | 8 | 2 | 4 | 0 | 2 | 5 | 66.7 | 0 | 5 |
| feu | 13 | **0.0** | 0 | 0 | 0 | 4 | 0 | 3 | 6 | 30.8 | 0 | 0 |
| potelet_borne | 6 | **16.7** | 0 | 1 | 0 | 2 | 0 | 3 | 0 | 50.0 | 0 | 1 |
| cloture_barriere | 26 | **15.4** | 0 | 4 | 0 | 7 | 8 | 0 | 7 | 42.3 | 0 | 4 |
| mobilier | 17 | **5.9** | 0 | 1 | 0 | 5 | 0 | 0 | 11 | 17.6 | 0 | 1 |
| **total** | 1261 | **9.0** | 0 | 98 | 15 | 129 | 79 | 43 | 897 | 18.3 | 49 | 78 |

### Zone des travaux 2025

| classe | entités | **stricte %** | après travaux | avant, hors emprise | avant, dans l'emprise (appui) | indice | non concluant | non valable 2026 | sans observation | large % | auto seul | confirmées |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| arbre | 71 | **4.2** | 0 | 0 | 3 | 15 | 2 | 5 | 46 | 25.4 | 12 | 3 |
| marquage | 141 | **0.7** | 1 | 0 | 0 | 1 | 4 | 11 | 124 | 0.7 | 0 | 0 |
| bordure | 100 | **0.0** | 0 | 0 | 0 | 2 | 1 | 3 | 94 | 2.0 | 0 | 0 |
| surface_ilot | 269 | **1.5** | 3 | 0 | 1 | 4 | 0 | 4 | 257 | 1.9 | 0 | 1 |
| ponctuel_sol | 11 | **0.0** | 0 | 0 | 0 | 1 | 0 | 0 | 10 | 9.1 | 0 | 0 |
| candelabre_poteau | 17 | **0.0** | 0 | 0 | 0 | 13 | 0 | 3 | 1 | 76.5 | 0 | 0 |
| panneau | 14 | **7.1** | 0 | 0 | 1 | 6 | 0 | 2 | 5 | 50.0 | 0 | 1 |
| feu | 12 | **0.0** | 0 | 0 | 0 | 3 | 0 | 3 | 6 | 25.0 | 0 | 0 |
| potelet_borne | 3 | **0.0** | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0.0 | 0 | 0 |
| cloture_barriere | 10 | **0.0** | 0 | 0 | 0 | 1 | 2 | 0 | 7 | 10.0 | 0 | 0 |
| mobilier | 14 | **0.0** | 0 | 0 | 0 | 4 | 0 | 0 | 10 | 14.3 | 0 | 0 |
| **total** | 662 | **1.4** | 4 | 0 | 5 | 50 | 9 | 34 | 560 | 8.0 | 12 | 5 |

Rôle des observations : ajout 193, conflit_ajout 5, contexte 41, entite 1234, non_apparie 3, temporaire 2. « contexte » et « temporaire » ne sont jamais fusionnés (FUS-CTX-01, FUS-TMP-01) ; « conflit_ajout » : ajout remplacé par un conflit avec le levé GAM (FUS-ADD-04) ; « non_apparie » : observations sans lien ni candidat (voir l'index).

## Liens groupés (FUS-LIEN-09)

- `PANO2026-014` : prouvées ML-5339, ML-5340, ML-5344 ; vues sans preuve propre ML-5337, ML-5338, ML-5341, ML-5342, ML-5343, ML-5345, ML-5358.
- `PANO2026-044` : prouvées aucune ; vues sans preuve propre K-0420, K-0513, K-0658, K-0658z, K-0667.
- `VISION-PANORAMAX-2-47` : prouvées arbre_101, arbre_134 ; vues sans preuve propre arbre_102.
- `pano_0-25` : prouvées aucune ; vues sans preuve propre arbre_146, arbre_147, arbre_170, arbre_228, arbre_241, arbre_242.
- `pano_0-49` : prouvées aucune ; vues sans preuve propre arbre_187, arbre_188, arbre_189, arbre_201, arbre_202, arbre_211, arbre_212, arbre_214, arbre_219.

## Contrôles automatiques (FUS-AUTO-01/02)

| atelier | classe | confirmations automatiques | requalifiées « incertain » | corroborées par une observation manuelle |
|---|---|---|---|---|
| ortho_A | marquage | 47 | 45 | 2 |
| ortho_B | marquage | 57 | 57 | 0 |
| ortho_recentes | bordure | 54 | 35 | 19 |
| ortho_recentes | marquage | 102 | 76 | 26 |

Aucune n'a le contrat FUS-AUTO-02 (masque véhicules / ombres, part masquée ≤ 0,2, réponse de ligne fine ou de peinture pour un marquage, de ligne fine ou d'arête pour une bordure) : une confirmation automatique ne compte que si une observation manuelle confirme la même entité, et n'est jamais une preuve stricte. Calcul de référence : `recon/pcg/enrichir/controle_auto.py` (marquages ; essai sur le PCRS 2022 : `controle_auto_essai.jpg`). Le PCRS 5 cm est requis pour la réponse de ligne fine : à 20 cm (IGN 2024), un trait de 0,10-0,15 m n'est pas résolu.

## Bordures : vue, profil et abaissés (FUS-BOR-01..03)

188 textes libres lus (champs hauteur_vue_estimee_m, profil_observe, profil_description, observe, observation, note) sur les observations de bordures. Lectures : vue chiffrée 12 (lecture haute), qualificatif explicite 17 (moyenne : arasée, sans vue, aucune bordure saillante…), vue déduite 17 (faible : « basse », « bordure de trottoir »), abaissé 0. Chaque lecture est rapportée à l'abscisse de l'observation sur la bordure ; le vote se fait par intervalle de la description. Une contradiction est cherchée dans l'intervalle observé et dans les intervalles courants vus à ± 5 m.

| bordure | intervalle | décrit (vue, origine) | lecture | obs | gravité |
|---|---|---|---|---|---|
| `K-0118` | 0 (s 0.0-1.2 m) | T3 0.19 m (mesuree) | « vue ≤ 5 cm » -> 0.0-0.05 m (haute) | MLY-BOR-002 | a_verifier |
| `K-0123` | 0 (s 0.0-1.9 m) | T2 0.16 m (mesuree) | « bordure de rive basse » -> 0.03-0.09 m (faible) | MLY-BOR-003 | info |
| `K-0124` | 0 (s 0.0-1.3 m) | T3 0.2 m (mesuree) | « bordure de rive basse » -> 0.03-0.09 m (faible) | MLY-BOR-004 | info |
| `K-0185` | 0 (s 0.0-4.6 m) | T2 0.125 m (mesuree) | « rive de chaussée arasée contre l'accotement enherbé (ligne de rive en tirets) » -> 0.0-0.03 m (moyenne) | MLY-BOR-012 | a_verifier |
| `K-0298` | 0 (s 0.0-12.6 m) | T3 0.21 m (mesuree) | « vue ≈ 5–10 cm » -> 0.05-0.1 m (haute) | MLY-BOR-020 | a_verifier |
| `K-0435` | 3 (s 17.5-31.0 m, voisin) | P1 0.02 m (estimee) | « vue ≈ 10–15 cm » -> 0.1-0.15 m (haute) | MLY-BOR-031 | a_verifier |
| `K-0439` | 0 (s 0.0-86.5 m) | T2 0.14 m (estimee) | « bordure arasée entre la voie en enrobé et l'aire de stationnement en pavés béton » -> 0.0-0.03 m (moyenne) | MLY-BOR-034 | a_verifier |
| `K-0465` | 1 (s 2.0-49.8 m) | T2 0.14 m (estimee) | « rive arasée entre la voie en enrobé et les places en stabilisé / gravier, sur l'arête projetée » -> 0.0-0.03 m (moyenne) | MLY-BOR-043 | a_verifier |
| `K-0509` | 9 (s 34.5-48.4 m) | A2 0.07 m (mesuree) | « vue ≈ 12–14 cm » -> 0.12-0.14 m (haute, non probante FUS-DATE-02) | MLY-BOR-054 | info |
| `K-0511` | 0 (s 0.0-2.4 m) | P1 0.015 m (sans_ressaut_mesuree) | « vue ≈ 10 cm » -> 0.08-0.12 m (haute) | MLY-BOR-056 | a_verifier |
| `K-0644` | 0 (s 0.0-6.7 m) | A2 0.03 m (mesuree) | « bordure de trottoir » -> 0.09-0.175 m (faible) | MLY-BOR-066 | info |
| `K-0658` | 2 (s 3.9-5.1 m) | T2_bateau 0.0 m (mesuree) | « bordure de trottoir » -> 0.09-0.175 m (faible) | MLY-BOR-068 | info |
| `K-0662` | 1 (s 2.0-4.9 m) | T3 0.2 m (mesuree) | « bordure basse » -> 0.03-0.09 m (faible) | MLY-BOR-069 | info |
| `K-0663` | 0 (s 0.0-2.6 m) | T2 0.165 m (mesuree) | « bordure basse » -> 0.03-0.09 m (faible) | MLY-BOR-070 | info |
| `K-0673` | 0 (s 0.0-2.2 m, voisin) | T2 0.115 m (mesuree) | « bordure basse » -> 0.03-0.09 m (faible, non probante FUS-DATE-02) | MLY-BOR-076 | info |
| `K-0673` | 2 (s 4.7-5.9 m) | T2_bateau 0.0 m (mesuree) | « bordure basse » -> 0.03-0.09 m (faible, non probante FUS-DATE-02) | MLY-BOR-076 | info |
| `K-0673` | 4 (s 8.4-10.7 m, voisin) | T2 0.115 m (mesuree) | « bordure basse » -> 0.03-0.09 m (faible, non probante FUS-DATE-02) | MLY-BOR-076 | info |
| `K-0675` | 7 (s 35.5-45.5 m, voisin) | T2 0.1 m (mesuree) | « rive arasée de la contre-allée de stationnement (limite gravillons / enrobé), sur l'arête projetée » -> 0.0-0.03 m (moyenne) | MLY-BOR-078 | a_verifier |
| `K-0675` | 10 (s 46.5-54.6 m) | A2 0.055 m (mesuree) | « rive arasée de la contre-allée de stationnement (limite gravillons / enrobé), sur l'arête projetée » -> 0.0-0.03 m (moyenne) | MLY-BOR-078 | a_verifier |

Les cinq cas de la critique (« arasée » contre 8 à 14 cm) : `K-0185` contradiction signalée (intervalles 0) ; `K-0439` contradiction signalée (intervalles 0) ; `K-0465` contradiction signalée (intervalles 1) ; `K-0668` pas de contradiction au point observé : intervalle 9 (s 46.3-57.3 m) décrit P1 0.02 m, compatible avec la lecture « arasée » ; `K-0675` contradiction signalée (intervalles 7, 10). Aucune contradiction n'est appliquée : la proposition reste « revue_requise » (relevé terrain : photo rasante à moins de 5 m, mètre pliant).

## Priorité des photos 2026 (FUS-DATE-01)

46 entités sont vues sur les photos du 28/07/2026 (32 avec une preuve stricte après travaux) ; pour 10 d'entre elles, la photo 2026 a écarté des observations plus anciennes (existence, attribut ou position).

| entité | statut | existence | position | attributs | observations antérieures écartées |
|---|---|---|---|---|---|
| `I-0658` | confirme | present | non_mesure | - | MLY-ILO-003 |
| `I-0673` | confirme | present | non_mesure | - | MLY-ILO-004 |
| `K-0420` | indice_seulement | non_verifie | non_mesure | - | - |
| `K-0513` | indice_seulement | non_verifie | non_mesure | - | - |
| `K-0645` | confirme | present | confirme | - | MLY-BOR-067, OR-K-0645 |
| `K-0658` | confirme | present | non_mesure | - | - |
| `K-0658z` | indice_seulement | non_verifie | non_mesure | - | - |
| `K-0667` | indice_seulement | non_verifie | non_mesure | - | - |
| `K-0670` | confirme | present | non_mesure | - | MLY-BOR-074 |
| `MF-5523` | indice_seulement | non_verifie | non_mesure | - | - |
| `ML-0432` | a_retirer | retirer | non_mesure | - | - |
| `ML-0433` | indice_seulement | non_verifie | non_mesure | - | - |
| `ML-0434` | indice_seulement | non_verifie | non_mesure | - | - |
| `ML-5337` | indice_seulement | non_verifie | non_mesure | - | - |
| `ML-5338` | indice_seulement | non_verifie | non_mesure | - | - |
| `ML-5339` | corrige | present | non_mesure | usure | - |
| `ML-5340` | corrige | present | non_mesure | usure | - |
| `ML-5341` | absent_2026_a_verifier | absent_2026_a_verifier | non_mesure | - | - |
| `ML-5342` | absent_2026_a_verifier | absent_2026_a_verifier | non_mesure | - | - |
| `ML-5343` | absent_2026_a_verifier | absent_2026_a_verifier | non_mesure | - | - |
| `ML-5344` | corrige | present | non_mesure | usure | - |
| `ML-5345` | indice_seulement | non_verifie | non_mesure | - | - |
| `ML-5358` | indice_seulement | non_verifie | non_mesure | - | - |
| `ML-5452` | corrige | present | non_mesure | etat, usure | - |
| `MP-0085` | corrige | present | non_mesure | etat | - |
| `MS-5515` | corrige | present | non_mesure | etat, usure | - |
| `MS-5516` | corrige | present | non_mesure | etat, usure | - |
| `S-0268a` | corrige | present | non_mesure | etat_v1, materiau_id | - |
| `S-0268b` | confirme | present | non_mesure | - | MLY-SUR-061 |
| `S-0268c` | confirme | present | non_mesure | - | MLY-SUR-062 |
| `S-0268d` | corrige | present | non_mesure | etat_v1, materiau_id | - |
| `S-0268e` | corrige | present | non_mesure | etat_v1, materiau_id | - |
| `arbre_013` | absent_2026 | absent_2026 | non_mesure | - | - |
| `arbre_014` | corrige | present | confirme_sans_mesure | type | - |
| `arbre_015` | absent_2026 | absent_2026 | non_mesure | - | - |
| `arbre_016` | corrige | present | confirme_sans_mesure | hauteur_m | - |
| `arbre_018` | indice_seulement | non_verifie | confirme_sans_mesure | - | - |
| `arbre_026` | confirme | present | confirme_sans_mesure | - | - |
| `arbre_029` | confirme | present | confirme_sans_mesure | - | - |
| `barriere_levante_3375058657` | confirme | present | non_mesure | - | - |
| `lamp_9514828431` | corrige | present | deplacement 1.883 m (revue_requise) | - | - |
| `lamp_9514828517` | corrige | present | affinage 0.699 m (appliquer) | couleur_mat | ORTHO-B-166 |
| `pan_AB3a_3` | corrige | present | deplacement 4.147 m (appliquer) | - | - |
| `pan_AB4_2` | corrige | present | deplacement 0.922 m (appliquer) | - | ORTHO-B-123 |
| `pan_B6a1_1` | corrige | present | affinage 0.683 m (appliquer) | couleur_mat | ORTHO-B-166 |
| `pan_C13a_1` | corrige | present | affinage 0.683 m (appliquer) | couleur_mat | ORTHO-B-166 |

## Arbitrages de revue (FUS-ARB-01)

| id | action | observations | effet | motif |
|---|---|---|---|---|
| ARB-001 | ne_pas_instancier | ORTHO-B-187 | ENR-PON-011 non instancié | tache d'enrobé sombre aux bords flous, sans anneau ni cadre : pas un tampon (le tampon rond voisin, net, est un autre objet) |
| ARB-002 | ancrer_bord_ilot | VISION-PANORAMAX-1-78 | ENR-MAT-005 ancré au bord de surf_0358 (espace_vert), déplacé de 1.572 m | le mât (4,5 m, gris clair) se dresse dans le petit îlot planté rond bordé, à la sortie de la voie privée des Saules Blancs (photo 81f3f695 du 24/08/2024) ; le … |
| ARB-003 | mesure_position | DOC-LOCALE-018 | arbre_224 : deplacement 7.823 m, σ 1.874 m, 2 mesures, décision revue_requise | le point de l'inventaire Métropole MEY00085 (peuplier noir) est à 1,2 m du tronc triangulé par VISION-PANORAMAX-2-13 et à 8,5 m de arbre_224 (levé GAM) : deux … |
| ARB-004 | invalider_observation | MLY-MAR-017 | lien invalidé : MLY-MAR-017 -> ML-5342 | projection de la description à 25,9 m (image Mapillary 1546760642583408 du 24/08/2024) tombée sur la haie qui masque les places depuis Verdun : erreur de proje… |
| ARB-005 | constat_revue | PANO2026-014 | REV-ARB-005-01 -> ML-5342 (absent_sur_image, moyenne) : absent_2026_a_verifier; REV-ARB-005-02 -> ML-5343 (absent_sur_image, faible) : absent_2026_a_verifier; REV-ARB-005-03 -> ML-5341 (absent_sur_image, faible) : absent_2026_a_verifier | PANO2026-014 confirmait 10 places par un lien groupé alors que ses pixels de preuve ne citent que ML-5339, ML-5340 et ML-5344 ; sur f8d91bb1, les places à l'es… |
| ARB-006 | invalider_observation | MLY-BOR-027 | lien invalidé : MLY-BOR-027 -> K-0358 | la ligne projetée (16,7 m) tombe sur la limite pelouse / haie vue depuis Verdun ; sur le PCRS 2022, K-0358 est la bordure du parking, derrière la haie : masqué… |

## Comptes par classe (statut de vérification, FUS-STAT-01)

| classe | entités vues | confirmées | corrigées | contestées | indice seulement | non valables 2026 | absentes / à retirer | absence à vérifier | position corrigée (appliquer) | ajouts (instanciés) | ajouts -> conflit GAM | avec conflit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| arbre | 312 | 28 | 20 | 0 | 229 | 32 | 3 | 0 | 1 (0) | 14 (10) | 0 | 13 |
| haie_massif | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 (0) | 10 (7) | 0 | 2 |
| marquage | 247 | 41 | 14 | 0 | 141 | 19 | 28 | 4 | 0 (0) | 40 (28) | 5 | 22 |
| bordure | 162 | 57 | 1 | 7 | 88 | 7 | 2 | 0 | 1 (0) | 0 (0) | 0 | 26 |
| surface_ilot | 159 | 35 | 28 | 0 | 88 | 8 | 0 | 0 | 0 (0) | 8 (5) | 0 | 7 |
| ponctuel_sol | 2 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 (0) | 68 (44) | 0 | 12 |
| candelabre_poteau | 46 | 13 | 7 | 0 | 23 | 3 | 0 | 0 | 9 (5) | 5 (2) | 0 | 11 |
| panneau | 25 | 5 | 9 | 0 | 9 | 2 | 0 | 0 | 4 (4) | 12 (6) | 0 | 6 |
| feu | 9 | 0 | 0 | 0 | 6 | 3 | 0 | 0 | 0 (0) | 2 (0) | 0 | 1 |
| potelet_borne | 13 | 7 | 0 | 0 | 3 | 3 | 0 | 0 | 1 (0) | 2 (0) | 0 | 1 |
| cloture_barriere | 36 | 12 | 0 | 0 | 24 | 0 | 0 | 0 | 0 (0) | 2 (2) | 0 | 7 |
| mobilier | 9 | 2 | 0 | 0 | 7 | 0 | 0 | 0 | 2 (0) | 17 (7) | 0 | 5 |
| autre | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 (0) | 9 (0) | 0 | 2 |
| **total** | 1020 | 200 | 79 | 7 | 619 | 78 | 33 | 4 | 18 (9) | 189 (111) | 5 | 115 |

Attributs mis à jour : materiau_id 45, hauteur_m 12, essence 9, usure 9, couronne_m 8, classe 5, etat 5, couleur_mat 4, type 4, etat_v1 3, azimut_deg 2, bouton_appel 2, largeur_m 2, modulation 2, nb_lanternes 2, porte_a_faux_m 2, signal_sonore 2, vibreur 2, nb_crosses 1.

## Contrôle croisé avec la cohérence (`coherence/corrections.geojson`)

30 corrections de cohérence ont une preuve image. Positions : corrobore_avant_travaux 1, indifferent 1, non_conclu_sans_mesure 16, non_contredit 4, partiel 6. Azimuts : accord 2 (FUS-COH-01).

| entité | cohérence | verdict image | écart image / corrigé | écart image / origine | obs |
|---|---|---|---|---|---|
| `ADD-BTN-MP-0580-b` | proposition_ajout  m | corrobore_avant_travaux |  |  | VISION-PANORAMAX-2-31 |
| `arbre_020` | deplacement 0.5 m | non_conclu_sans_mesure |  |  | ORTHO-B-214 |
| `arbre_063` | deplacement 0.05 m | non_conclu_sans_mesure |  |  | ORTHO_A-0048 |
| `arbre_109` | non_instanciation  m | non_contredit |  |  |  |
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
| `pan_C13a_1` | deplacement 0.016 m | partiel | 0.698 | 0.683 | PANO2026-018 |
| `pan_D21_1` | non_instanciation  m | non_contredit |  |  |  |
| `pan_D21_2` | non_instanciation  m | non_contredit |  |  |  |
| `pan_J5_1` | deplacement 0.5 m | indifferent | 0.25 | 0.668 | VISION-PANORAMAX-2-27, VISION-PANORAMAX-2-5 |
| `pan_J5_2` | non_instanciation  m | non_contredit |  |  |  |
| `poteau_REV_ligne42` | deplacement 0.25 m | non_conclu_sans_mesure |  |  | DOC-LOCALE-009 |
| `potelet_REV_1` | deplacement 0.15 m | non_conclu_sans_mesure |  |  | ORTHO-B-106 |
| `potelet_REV_2` | deplacement 0.15 m | non_conclu_sans_mesure |  |  | ORTHO-B-107 |

## Corrections de position

| entité | nature | d (m) | σ (m) | décision | méthodes | obs | raisons |
|---|---|---|---|---|---|---|---|
| `pan_AB3a_3` | deplacement | 4.147 | 0.15 | appliquer | triangulation | PANO2026-016 |  |
| `lamp_12668620636` | deplacement | 1.826 | 0.188 | appliquer | pixel_ortho | ORTHO-B-209 |  |
| `lamp_9530354517` | deplacement | 1.2 | 0.188 | appliquer | pixel_ortho | ORTHO-B-109 |  |
| `pan_AB4_2` | deplacement | 0.922 | 0.3 | appliquer | triangulation | PANO2026-015 |  |
| `lamp_9665416717` | deplacement | 0.876 | 0.25 | appliquer | pixel_ortho | ORTHO_A-0167 |  |
| `lamp_9514828517` | affinage | 0.699 | 0.05 | appliquer | triangulation | PANO2026-018 |  |
| `pan_B6a1_1` | affinage | 0.683 | 0.05 | appliquer | triangulation | PANO2026-018 |  |
| `pan_C13a_1` | affinage | 0.683 | 0.05 | appliquer | triangulation | PANO2026-018 |  |
| `lamp_9665416817` | affinage | 0.581 | 0.083 | appliquer | triangulation | VISION-PANORAMAX-1-55, VISION-PANORAMAX-2-57 |  |
| `arbre_224` | deplacement | 7.823 | 1.874 | revue_requise | coordonnees_inventaire, triangulation | DOC-LOCALE-018, VISION-PANORAMAX-2-13 | σ fusion 1.87 m > 0,5 m; σ fusion 1.87 m > preuve de la description (0.05 m); objet levé GAM : déplacement > 0,5 m (FUS-POS-06) |
| `banc_8360664518` | deplacement | 4.474 | 0.375 | revue_requise | pixel_ortho | ORTHO_A-0100 | aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines); aucune mesure stricte (FUS-COUV-02) |
| `poteau_reseau_12888056356` | deplacement | 3.29 | 0.4 | revue_requise | triangulation | pano_0-20 | aucune mesure stricte (FUS-COUV-02); mesures antérieures aux travaux, dans leur emprise, sans appui de conservation (FUS-DATE-02) |
| `potelet_12462947806` | deplacement | 1.969 | 0.375 | revue_requise | pixel_ortho | ORTHO_A-0081 | une seule source non triangulée et pas de correction affirmée; aucune mesure stricte (FUS-COUV-02) |
| `lamp_9514828431` | deplacement | 1.883 | 0.6 | revue_requise | triangulation | PANO2026-019 | σ fusion 0.60 m > 0,5 m |
| `poteau_reseau_12888048898` | deplacement | 1.814 | 0.35 | revue_requise | triangulation | pano_0-21 | aucune mesure stricte (FUS-COUV-02); mesures antérieures aux travaux, dans leur emprise, sans appui de conservation (FUS-DATE-02) |
| `mat_camera_SW_TPC` | deplacement | 1.59 | 0.25 | revue_requise | triangulation | pano_0-47 | aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines); aucune mesure stricte (FUS-COUV-02) |
| `armoire_1313238971` | deplacement | 1.044 | 0.188 | revue_requise | pixel_ortho | ORTHO-B-171 | une seule source non triangulée et pas de correction affirmée; aucune mesure stricte (FUS-COUV-02) |
| `K-0227` | translation | 0.868 | 0.188 | revue_requise | pixel_ortho | ORTHO_A-0019 | géométrie levée GAM : translation > 0,5 m (FUS-POS-06) |

## Existence : entités absentes en 2026, à retirer ou à vérifier

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
- `ML-0222` (ligne) : **absent_2026_a_verifier** ; obs MLY-MAR-001
- `ML-0225` (ligne) : **retirer** ; obs ORTHO_A-0095
- `ML-0226` (ligne) : **retirer** ; obs ORTHO_A-0096
- `ML-0238` (ligne) : **absent_2026** ; obs MLY-MAR-002
- `ML-0240` (ligne) : **absent_2026** ; obs MLY-MAR-003
- `ML-0432` (ligne) : **retirer** ; obs PANO2026-004
- `ML-0930` (ligne) : **retirer** ; obs ORTHO-B-206
- `ML-0935` (ligne) : **absent_2026** ; obs MLY-MAR-006
- `ML-5141` (ligne) : **retirer** ; obs MLY-MAR-011, OR-V-022
- `ML-5341` (ligne) : **absent_2026_a_verifier** ; obs REV-ARB-005-03
- `ML-5342` (ligne) : **absent_2026_a_verifier** ; obs REV-ARB-005-01
- `ML-5343` (ligne) : **absent_2026_a_verifier** ; obs REV-ARB-005-02
- `MZ-5002` (zone) : **retirer** ; obs MLY-CON-017
- `arbre_013` (feuillu) : **absent_2026** ; obs PANO2026-026
- `arbre_015` (feuillu) : **absent_2026** ; obs PANO2026-027
- `arbre_175` (feuillu) : **absent_2026** [retire_entre_dates] ; obs OR-V-003, ORTHO_A-0192

## Ajouts

189 objets nouveaux (groupes d'observations), dont 111 instanciables. Par classe (instanciés / candidats) : arbre 10/4, autre 0/9, avaloir 9/1, candelabre 2/3, cloture 2/0, feu 0/2, haie 4/3, marquage 28/12, massif 3/0, mobilier 7/10, panneau 6/6, potelet 0/2, surface 5/3, tampon 35/23. Un ajout vu seulement avant la fin des travaux, dans leur emprise, n'est pas instancié (FUS-DATE-02).

5 ajouts proposés sont remplacés par un conflit `ajout_contre_leve_gam` (FUS-ADD-04, rayon 1.5 m) : DOC-LOCALE-016 (lignes_de_voie_vercors) à 1.309 m de `ML-5228`; DOC-LOCALE-017 (lignes_de_voie_vercors) à 0.918 m de `ML-5401`; ORTHO-B-090 (symbole_velo) à 0.659 m de `MS-5000`; ORTHO_A-0033 (t_stationnement) à 1.423 m de `ML-5159`; ORTHO_A-0034 (lignes_stationnement) à 0.675 m de `ML-5159`.

| id | classe | sous-types | famille cible | preuve stricte | valide 2026 | instancier | obs |
|---|---|---|---|---|---|---|---|
| `ENR-ARB-001` | arbre | jeunes_arbres_alignement | vegetation.arbres | avant_travaux_hors_emprise | True | oui | ORTHO_A-0004 |
| `ENR-ARB-002` | arbre | arbre_inventaire_metropole | vegetation.arbres | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | DOC-LOCALE-034 |
| `ENR-ARB-003` | arbre | arbustes_conifères | vegetation.arbres | avant_travaux_hors_emprise | True | oui | ORTHO_A-0045 |
| `ENR-ARB-004` | arbre | petit_arbre | vegetation.arbres | avant_travaux_hors_emprise | True | oui | ORTHO_A-0090 |
| `ENR-ARB-005` | arbre | souche_ou_massif | vegetation.arbres | avant_travaux_hors_emprise | True | oui | ORTHO_A-0120 |
| `ENR-ARB-006` | arbre | grand_feuillu | vegetation.arbres | avant_travaux_hors_emprise | True | oui | ORTHO_A-0119 |
| `ENR-ARB-007` | arbre | petit_arbre_fleuri | vegetation.arbres | avant_travaux_hors_emprise | True | oui | ORTHO-B-042 |
| `ENR-ARB-008` | arbre | petit_arbre_fleuri | vegetation.arbres | avant_travaux_hors_emprise | True | oui | ORTHO-B-041 |
| `ENR-ARB-009` | arbre | feuillu | vegetation.arbres | avant_travaux_hors_emprise | True | oui | ORTHO_A-0153 |
| `ENR-ARB-010` | arbre | feuillage_pourpre | vegetation.arbres | avant_travaux_hors_emprise | True | oui | ORTHO_A-0152 |
| `ENR-ARB-011` | arbre | arbustes_boules | vegetation.arbres | avant_travaux_hors_emprise | True | oui | ORTHO_A-0154 |
| `ENR-ARB-012` | arbre | arbre_inventaire_metropole | vegetation.arbres | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | DOC-LOCALE-024 |
| `ENR-ARB-013` | arbre | arbre_inventaire_metropole | vegetation.arbres | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | DOC-LOCALE-025 |
| `ENR-ARB-014` | arbre | arbre_inventaire_metropole | vegetation.arbres | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | DOC-LOCALE-032 |
| `ENR-AUT-001` | autre | objet_vertical_blanc | - | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | ORTHO_A-0044 |
| `ENR-AUT-002` | autre | cables_transversaux | - | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | VISION-PANORAMAX-1-73 |
| `ENR-AUT-003` | autre | portique_entree | - | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | pano_0-18 |
| `ENR-AUT-004` | autre | escalier_garde_corps | - | avant_travaux_hors_emprise | True | non : famille cible inexistante dans la description | ORTHO_A-0131 |
| `ENR-AUT-005` | autre | aire_de_jeux | - | avant_travaux_hors_emprise | True | non : famille cible inexistante dans la description | ORTHO_A-0157 |
| `ENR-AUT-006` | autre | objet_blanc_bas | - | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02); observations « incertain » seulement | ORTHO-B-029 |
| `ENR-AUT-007` | autre | ligne_sombre_continue | - | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | ORTHO-B-004 |
| `ENR-AUT-008` | autre | coffret_maconne | - | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | VISION-PANORAMAX-2-36 |
| `ENR-AUT-009` | autre | anneaux_sombres_pelouse | - | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne; famille cible inexistante dans la description | ORTHO_A-0180 |
| `ENR-CLO-001` | cloture | grillages_tennis | mobilier.cloture | avant_travaux_hors_emprise | True | oui | ORTHO_A-0018 |
| `ENR-CLO-002` | cloture | portail_coulissant | mobilier.cloture | avant_travaux_hors_emprise | True | oui | ORTHO_A-0110 |
| `ENR-FEU-001` | feu | support_pietons_R12_bouton | signaux.feux | indice_seulement | False | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02); observations « incertain » seulement | pano_0-52 |
| `ENR-FEU-002` | feu | boitier_appel_pietons | signaux.feux | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | VISION-PANORAMAX-2-31 |
| `ENR-MAR-001` | marquage | hachures | marquages | avant_travaux_hors_emprise | True | oui | ORTHO_A-0002 |
| `ENR-MAR-002` | marquage | bande_centrale_hachuree | marquages | avant_travaux_hors_emprise | True | oui | ORTHO_A-0005 |
| `ENR-MAR-003` | marquage | places_parking | marquages | avant_travaux_hors_emprise | True | oui | ORTHO_A-0006 |
| `ENR-MAR-004` | marquage | places_parking | marquages | avant_travaux_hors_emprise | True | oui | ORTHO_A-0025 |
| `ENR-MAR-005` | marquage | damier | marquages | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0028 |
| `ENR-MAR-006` | marquage | hachures | marquages | avant_travaux_hors_emprise | True | oui | ORTHO_A-0036 |
| `ENR-MAR-007` | marquage | hachures | marquages | avant_travaux_hors_emprise | True | oui | ORTHO_A-0035 |
| `ENR-MAR-008` | marquage | pictogrammes_pmr_bleus | marquages | avant_travaux_hors_emprise | True | oui | ORTHO_A-0066 |
| `ENR-MAR-009` | marquage | places_parking_jardinerie_o | marquages | avant_travaux_hors_emprise | True | oui | ORTHO_A-0067 |
| `ENR-MAR-010` | marquage | places_en_epi_contre_allee | marquages | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-154 |
| `ENR-MAR-011` | marquage | ligne_discontinue_stationnement | marquages | avant_travaux_hors_emprise | True | oui | ORTHO_A-0041 |
| `ENR-MAR-012` | marquage | damier | marquages | indice_seulement | False | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO_A-0099 |
| `ENR-MAR-013` | marquage | ligne_place_stationnement | marquages | avant_travaux_hors_emprise | True | oui | ORTHO-B-059 |
| `ENR-MAR-014` | marquage | logo_velo_piste | marquages | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO_A-0101 |
| `ENR-MAR-015` | marquage | ilot_peint_ocre | marquages | avant_travaux_hors_emprise | True | oui | ORTHO-B-100 |
| `ENR-MAR-016` | marquage | ligne_place_stationnement | marquages | avant_travaux_hors_emprise | True | oui | ORTHO-B-060 |
| `ENR-MAR-017` | marquage | ligne_place_stationnement | marquages | avant_travaux_hors_emprise | True | oui | ORTHO-B-058 |
| `ENR-MAR-018` | marquage | ligne_place_stationnement | marquages | avant_travaux_hors_emprise | True | oui | ORTHO-B-057 |
| `ENR-MAR-019` | marquage | ligne_place_stationnement | marquages | avant_travaux_hors_emprise | True | oui | ORTHO-B-056 |
| `ENR-MAR-020` | marquage | ilot_peint_ocre | marquages | avant_travaux_hors_emprise | True | oui | ORTHO-B-101 |
| `ENR-MAR-021` | marquage | lignes_places_terrasse | marquages | avant_travaux_hors_emprise | True | oui | ORTHO-B-142 |
| `ENR-MAR-022` | marquage | ligne_place_stationnement | marquages | avant_travaux_hors_emprise | True | oui | ORTHO-B-053 |
| `ENR-MAR-023` | marquage | ligne_place_stationnement | marquages | avant_travaux_hors_emprise | True | oui | ORTHO-B-052 |
| `ENR-MAR-024` | marquage | ligne_place_stationnement | marquages | avant_travaux_hors_emprise | True | oui | ORTHO-B-054 |
| `ENR-MAR-025` | marquage | ligne_place_stationnement | marquages | avant_travaux_hors_emprise | True | oui | ORTHO-B-055 |
| `ENR-MAR-026` | marquage | ligne_place_stationnement | marquages | avant_travaux_hors_emprise | True | oui | ORTHO-B-051 |
| `ENR-MAR-027` | marquage | places_parking_jardinerie | marquages | avant_travaux_hors_emprise | True | oui | ORTHO_A-0111 |
| `ENR-MAR-028` | marquage | lignes_stationnement_parking | marquages | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO_A-0102 |
| `ENR-MAR-029` | marquage | zigzag_arret_ancien | marquages | indice_seulement | False | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02); observations « incertain » seulement | ORTHO-B-085 |
| `ENR-MAR-030` | marquage | zone_jaune_croix | marquages | avant_travaux_hors_emprise | True | oui | ORTHO_A-0126 |
| `ENR-MAR-031` | marquage | traversee_cyclable_verte | marquages | indice_seulement | False | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02); observations « incertain » seulement | pano_0-46 |
| `ENR-MAR-032` | marquage | chiffre_vitesse_50 | marquages | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | pano_0-45 |
| `ENR-MAR-033` | marquage | ligne_place_stationnement | marquages | indice_seulement | True | non : vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-081 |
| `ENR-MAR-034` | marquage | logo_velo_piste | marquages | indice_seulement | True | non : vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO_A-0162 |
| `ENR-MAR-035` | marquage | paves_jaunes_traversee_cyclable, traversee_cyclable_jaune | marquages | apres_travaux | True | oui | ORTHO-B-130, PANO2026-008 |
| `ENR-MAR-036` | marquage | paves_jaunes_traversee_cyclable | marquages | apres_travaux | True | oui | PANO2026-009 |
| `ENR-MAR-037` | marquage | ligne_continue_axiale | marquages | apres_travaux | True | oui | PANO2026-011 |
| `ENR-MAR-038` | marquage | ligne_effet_stop | marquages | apres_travaux | True | oui | PANO2026-010 |
| `ENR-MAR-039` | marquage | bandes_traversee_vercors | marquages | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-127 |
| `ENR-MAR-040` | marquage | nez_ilot_peint | marquages | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO_A-0159 |
| `ENR-MAT-001` | candelabre | borne_globe | mobilier.lampadaire | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0122 |
| `ENR-MAT-002` | candelabre | lampadaire_pieton | mobilier.lampadaire | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-164 |
| `ENR-MAT-003` | candelabre | borne_lumineuse_globe | mobilier.lampadaire | avant_travaux_hors_emprise | True | oui | ORTHO_A-0156 |
| `ENR-MAT-004` | candelabre | lampadaire_pieton | mobilier.lampadaire | avant_travaux_hors_emprise | True | oui | ORTHO-B-163 |
| `ENR-MAT-005` | candelabre | mat_droit_residentiel | mobilier.lampadaire | indice_seulement | True | non : vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | VISION-PANORAMAX-1-78 |
| `ENR-MOB-001` | mobilier | cage_metallique | mobilier | avant_travaux_hors_emprise | True | oui | ORTHO_A-0024 |
| `ENR-MOB-002` | mobilier | abri_ou_range_velos | mobilier | avant_travaux_hors_emprise | True | oui | ORTHO-B-210 |
| `ENR-MOB-003` | mobilier | coffret | mobilier | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0080 |
| `ENR-MOB-004` | mobilier | bloc_rocheux_alignement | mobilier | avant_travaux_hors_emprise | True | oui | ORTHO_A-0029 |
| `ENR-MOB-005` | mobilier | conteneurs | mobilier | avant_travaux_hors_emprise | True | oui | ORTHO-B-172 |
| `ENR-MOB-006` | mobilier | blocs_rocheux | mobilier | avant_travaux_hors_emprise | True | oui | ORTHO_A-0074 |
| `ENR-MOB-007` | mobilier | objet_rectangulaire | mobilier | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | ORTHO-B-112 |
| `ENR-MOB-008` | mobilier | butees_de_roues | mobilier | indice_seulement | True | non : vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-078 |
| `ENR-MOB-009` | mobilier | objet_rouge | mobilier | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0121 |
| `ENR-MOB-010` | mobilier | arceaux_velos | mobilier | indice_seulement | False | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02); observations « incertain » seulement | VISION-PANORAMAX-1-90 |
| `ENR-MOB-011` | mobilier | stationnement_trottinettes | mobilier | indice_seulement | False | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02); observations « incertain » seulement | ORTHO-B-067 |
| `ENR-MOB-012` | mobilier | coffret_ou_borne | mobilier | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0113 |
| `ENR-MOB-013` | mobilier | conteneurs_dechets | mobilier | avant_travaux_hors_emprise | True | oui | ORTHO_A-0130 |
| `ENR-MOB-014` | mobilier | bancs | mobilier | avant_travaux_hors_emprise | True | oui | ORTHO_A-0155 |
| `ENR-MOB-015` | mobilier | coffre_ou_abri_conteneurs | mobilier | indice_seulement | False | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-080 |
| `ENR-MOB-016` | mobilier | armoire_commande_feux_probable | mobilier | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | VISION-PANORAMAX-2-1 |
| `ENR-MOB-017` | mobilier | objet_blanc | mobilier | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | ORTHO-B-095 |
| `ENR-PAN-001` | panneau | C1a_reserve | signaux.panneaux | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | PANO2026-043 |
| `ENR-PAN-002` | panneau | plaque_de_rue | signaux.panneaux | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | pano_0-2 |
| `ENR-PAN-003` | panneau | D21_double | signaux.panneaux | indice_seulement | False | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | VISION-PANORAMAX-1-41 |
| `ENR-PAN-004` | panneau | panneau_parking_prive | signaux.panneaux | apres_travaux | True | oui | PANO2026-022 |
| `ENR-PAN-005` | panneau | panneau_parking_prive | signaux.panneaux | apres_travaux | True | oui | PANO2026-021 |
| `ENR-PAN-006` | panneau | panneau_parking_prive | signaux.panneaux | apres_travaux | True | oui | PANO2026-020 |
| `ENR-PAN-007` | panneau | fleche_directionnelle_privee | signaux.panneaux | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | PANO2026-042 |
| `ENR-PAN-008` | panneau | plaque_de_rue | signaux.panneaux | indice_seulement | True | non : vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | VISION-PANORAMAX-2-37 |
| `ENR-PAN-009` | panneau | panneau_information_2_poteaux | signaux.panneaux | apres_travaux | True | oui | PANO2026-017 |
| `ENR-PAN-010` | panneau | C13a_dos, C13a_nom_de_rue | signaux.panneaux | apres_travaux | True | oui | ORTHO-B-126, PANO2026-023 |
| `ENR-PAN-011` | panneau | panneau_large_ilot_nord | signaux.panneaux | indice_seulement | True | non : vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-125 |
| `ENR-PAN-012` | panneau | AB3a_dos | signaux.panneaux | apres_travaux | True | oui | PANO2026-024 |
| `ENR-PON-001` | avaloir | grille | ponctuels_sol.avaloir | avant_travaux_hors_emprise | True | oui | ORTHO_A-0020 |
| `ENR-PON-002` | tampon | regard_carre | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO_A-0022 |
| `ENR-PON-003` | avaloir | grille | ponctuels_sol.avaloir | avant_travaux_hors_emprise | True | oui | ORTHO_A-0021 |
| `ENR-PON-004` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO_A-0023 |
| `ENR-PON-005` | avaloir | grille | ponctuels_sol.avaloir | avant_travaux_hors_emprise | True | oui | ORTHO-B-180 |
| `ENR-PON-006` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-181 |
| `ENR-PON-007` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-186 |
| `ENR-PON-008` | tampon | tampons_ronds_cour | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO_A-0075 |
| `ENR-PON-009` | tampon | disque_beton_clair | ponctuels_sol.tampon | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0079 |
| `ENR-PON-010` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-185 |
| `ENR-PON-011` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | non : arbitrage ARB-001 (FUS-ARB-01) : tache d'enrobé sombre aux bords flous, sans anneau ni cadre : pas un tampon (le tampon rond voisin, net, est un autre objet) | ORTHO-B-187 |
| `ENR-PON-012` | avaloir | grille_carree | ponctuels_sol.avaloir | avant_travaux_hors_emprise | True | oui | ORTHO-B-179 |
| `ENR-PON-013` | avaloir | grille_carree | ponctuels_sol.avaloir | avant_travaux_hors_emprise | True | oui | ORTHO-B-182 |
| `ENR-PON-014` | tampon | regard_carre | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO_A-0037 |
| `ENR-PON-015` | tampon | regard_carre | ponctuels_sol.tampon | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0077 |
| `ENR-PON-016` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-183 |
| `ENR-PON-017` | avaloir | grille | ponctuels_sol.avaloir | avant_travaux_hors_emprise | True | oui | ORTHO_A-0078 |
| `ENR-PON-018` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-184 |
| `ENR-PON-019` | tampon | regard_petit | ponctuels_sol.tampon | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0038 |
| `ENR-PON-020` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO_A-0076 |
| `ENR-PON-021` | tampon | regard_carre | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-155 |
| `ENR-PON-022` | tampon | regard_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO_A-0039 |
| `ENR-PON-023` | tampon | regard_carre | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-114 |
| `ENR-PON-024` | tampon | regard_carre | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-120 |
| `ENR-PON-025` | tampon | regard_carre | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-143 |
| `ENR-PON-026` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-113 |
| `ENR-PON-027` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-110 |
| `ENR-PON-028` | tampon | regard_carre | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-111 |
| `ENR-PON-029` | tampon | regard_carre | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-065 |
| `ENR-PON-030` | tampon | tampon_rond | ponctuels_sol.tampon | indice_seulement | True | non : vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-074 |
| `ENR-PON-031` | tampon | tampon_rond | ponctuels_sol.tampon | indice_seulement | True | non : vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-070 |
| `ENR-PON-032` | tampon | regard_carre | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-115 |
| `ENR-PON-033` | tampon | regard_carre | ponctuels_sol.tampon | indice_seulement | True | non : vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-073 |
| `ENR-PON-034` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-072 |
| `ENR-PON-035` | tampon | tampon_rond | ponctuels_sol.tampon | indice_seulement | False | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-071 |
| `ENR-PON-036` | avaloir | grille | ponctuels_sol.avaloir | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-117 |
| `ENR-PON-037` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-118 |
| `ENR-PON-038` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-116 |
| `ENR-PON-039` | tampon | regard_carre | ponctuels_sol.tampon | indice_seulement | False | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-075 |
| `ENR-PON-040` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-069 |
| `ENR-PON-041` | tampon | regard_rectangulaire | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO_A-0112 |
| `ENR-PON-042` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-043 |
| `ENR-PON-043` | tampon | regard_carre | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-024 |
| `ENR-PON-044` | avaloir | grille | ponctuels_sol.avaloir | avant_travaux_hors_emprise | True | oui | ORTHO_A-0128 |
| `ENR-PON-045` | tampon | petit_regard | ponctuels_sol.tampon | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO_A-0129 |
| `ENR-PON-046` | tampon | tampon_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-025 |
| `ENR-PON-047` | avaloir | grille | ponctuels_sol.avaloir | avant_travaux_hors_emprise | True | oui | ORTHO_A-0127 |
| `ENR-PON-048` | tampon | regard | ponctuels_sol.tampon | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO_A-0144 |
| `ENR-PON-049` | tampon | bouche_a_cle | ponctuels_sol.tampon | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | ORTHO-B-036 |
| `ENR-PON-050` | avaloir | grille_avaloir | ponctuels_sol.avaloir | avant_travaux_hors_emprise | True | oui | ORTHO-B-035 |
| `ENR-PON-051` | tampon | tampon_rond | ponctuels_sol.tampon | indice_seulement | False | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-028 |
| `ENR-PON-052` | tampon | regard | ponctuels_sol.tampon | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO_A-0140 |
| `ENR-PON-053` | tampon | tampon_rond | ponctuels_sol.tampon | indice_seulement | True | non : vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-026 |
| `ENR-PON-054` | tampon | tampon_rond | ponctuels_sol.tampon | indice_seulement | True | non : vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-027 |
| `ENR-PON-055` | tampon | regard_grille | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-086 |
| `ENR-PON-056` | tampon | regard | ponctuels_sol.tampon | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO_A-0142 |
| `ENR-PON-057` | tampon | regard | ponctuels_sol.tampon | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO_A-0141 |
| `ENR-PON-058` | tampon | regard | ponctuels_sol.tampon | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO_A-0143 |
| `ENR-PON-059` | tampon | regard | ponctuels_sol.tampon | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO_A-0139 |
| `ENR-PON-060` | tampon | regard_rond | ponctuels_sol.tampon | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | VISION-PANORAMAX-1-23 |
| `ENR-PON-061` | tampon | regard | ponctuels_sol.tampon | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO_A-0145 |
| `ENR-PON-062` | tampon | regard_carre | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-030 |
| `ENR-PON-063` | tampon | regard_carre | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-031 |
| `ENR-PON-064` | tampon | regard_carre | ponctuels_sol.tampon | indice_seulement | False | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-033 |
| `ENR-PON-065` | tampon | regard_carre | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-032 |
| `ENR-PON-066` | tampon | regard_dalle | ponctuels_sol.tampon | apres_travaux | True | oui | PANO2026-033 |
| `ENR-PON-067` | tampon | regard_rond | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO_A-0166 |
| `ENR-PON-068` | tampon | regard_grille | ponctuels_sol.tampon | avant_travaux_hors_emprise | True | oui | ORTHO-B-097 |
| `ENR-POT-001` | potelet | borne_blanche | mobilier.potelet | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne; observations « incertain » seulement | ORTHO-B-037 |
| `ENR-POT-002` | potelet | file_de_potelets, file_potelets_inox | mobilier.potelet | indice_seulement | True | non : aucune observation valide 2026 en confiance ≥ moyenne | VISION-PANORAMAX-2-48, pano_0-48 |
| `ENR-SUR-001` | surface | reprise_enrobe | surfaces | avant_travaux_hors_emprise | True | oui | ORTHO-B-178 |
| `ENR-SUR-002` | surface | reprise_enrobe | surfaces | avant_travaux_hors_emprise | True | oui | ORTHO-B-066 |
| `ENR-SUR-003` | surface | reprise_enrobe | surfaces | indice_seulement | True | non : vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-034 |
| `ENR-SUR-004` | surface | cheminement_pieton_neuf_rive_E_Vercors | surfaces | indice_seulement | True | non : vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | DOC-LOCALE-004 |
| `ENR-SUR-005` | surface | allee_stabilisee | surfaces | avant_travaux_hors_emprise | True | oui | OR-V-017 |
| `ENR-SUR-006` | surface | trottoir_beton | surfaces | avant_travaux_hors_emprise | True | oui | OR-V-018 |
| `ENR-SUR-007` | surface | sous_zone_parking | surfaces | avant_travaux_hors_emprise | True | oui | OR-V-019 |
| `ENR-SUR-008` | surface | lits_mineraux_2024 | surfaces | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | OR-V-020 |
| `ENR-VEG-001` | haie | haie_basse_taillee, haie_taillee | vegetation.haies | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne; vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | ORTHO-B-076, pano_0-54 |
| `ENR-VEG-002` | haie | haie_taillee_parking_Reviree | vegetation.haies | avant_travaux_hors_emprise | True | oui | VISION-PANORAMAX-1-26 |
| `ENR-VEG-003` | massif | massif_paille | vegetation.massifs | avant_travaux_hors_emprise | True | oui | ORTHO-B-038 |
| `ENR-VEG-004` | haie | haie_taillee_persistante | vegetation.haies | indice_seulement | True | non : vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02) | pano_0-53 |
| `ENR-VEG-005` | haie | haie_taillee_angle_N | vegetation.haies | avant_travaux_hors_emprise | True | oui | VISION-PANORAMAX-1-25 |
| `ENR-VEG-006` | haie | haie_haute | vegetation.haies | apres_travaux | True | oui | PANO2026-025 |
| `ENR-VEG-007` | haie | haie_taillee_piste_vercors | vegetation.haies | indice_seulement | incertain | non : aucune observation valide 2026 en confiance ≥ moyenne | VISION-PANORAMAX-1-88 |
| `ENR-VEG-008` | haie | haie_taillee | vegetation.haies | avant_travaux_hors_emprise | True | oui | VISION-PANORAMAX-2-51 |
| `ENR-VEG-009` | massif | arbustes_tailles_en_blocs | vegetation.massifs | avant_travaux_hors_emprise | True | oui | ORTHO_A-0185 |
| `ENR-VEG-010` | massif | arbustes_tailles_en_blocs | vegetation.massifs | avant_travaux_hors_emprise | True | oui | ORTHO_A-0198 |

## Conflits

124 conflits : ajout_contre_leve_gam 5, attribut_desaccord 1, bordure_vue_contradiction 16, changement_entre_dates 1, coherence_desaccord 6, deplacement_non_etaye 9, doublon_apres_correction 1, existence_douteuse_2026 4, lien_introuvable 1, position_anterieure_divergente 1, position_desaccord 11, surface_a_decouper 4, validite_2026_douteuse 64. Détail dans `conflits.json` (les conflits d'information ne sont pas listés ici).

| id | type | cible | obs | détail |
|---|---|---|---|---|
| CF-ENR-001 | ajout_contre_leve_gam | `ML-5159` | ORTHO_A-0033 | objet observé absent de la description (t_stationnement) à 1.42 m de ML-5159 (marquages ligne, levé GAM) : même objet probable ; ajout non créé (FUS-ADD-04) |
| CF-ENR-002 | ajout_contre_leve_gam | `ML-5159` | ORTHO_A-0034 | objet observé absent de la description (lignes_stationnement) à 0.67 m de ML-5159 (marquages ligne, levé GAM) : même objet probable ; ajout non créé (FUS-ADD-04) |
| CF-ENR-003 | ajout_contre_leve_gam | `ML-5228` | DOC-LOCALE-016 | objet observé absent de la description (lignes_de_voie_vercors) à 1.31 m de ML-5228 (marquages ligne, levé GAM) : même objet probable ; ajout non créé (FUS-ADD-04) |
| CF-ENR-004 | ajout_contre_leve_gam | `ML-5401` | DOC-LOCALE-017 | objet observé absent de la description (lignes_de_voie_vercors) à 0.92 m de ML-5401 (marquages ligne, levé GAM) : même objet probable ; ajout non créé (FUS-ADD-04) |
| CF-ENR-005 | ajout_contre_leve_gam | `MS-5000` | ORTHO-B-090 | objet observé absent de la description (symbole_velo) à 0.66 m de MS-5000 (marquages symbole, levé GAM) : même objet probable ; ajout non créé (FUS-ADD-04) |
| CF-ENR-006 | attribut_desaccord | `lamp_9665416817` | MLY-CON-001, VISION-PANORAMAX-1-17, VISION-PANORAMAX-1-43 | couleur_mat : {"\"brun-rouille\"": ["MLY-CON-001", "VISION-PANORAMAX-1-17"], "\"gris anthracite patiné\"": ["VISION-PANORAMAX-1-43"]} |
| CF-ENR-007 | bordure_vue_contradiction | `K-0118` | MLY-BOR-002 | intervalle 0 (s 0.0-1.2 m, T3, vue 0.190 m mesurée au LiDAR 2021) contre MLY-BOR-002 à s 0.598 m « vue ≤ 5 cm » -> [0.0, 0.05] m (haute) -> vue lue 0.025 m (P1) |
| CF-ENR-010 | bordure_vue_contradiction | `K-0185` | MLY-BOR-012 | intervalle 0 (s 0.0-4.6 m, T2, vue 0.125 m mesurée au LiDAR 2021) contre MLY-BOR-012 à s 2.279 m « rive de chaussée arasée contre l'accotement enherbé (ligne de rive en tirets) » -> [0.0, 0.03] m (moyenne) -> vue lue 0.… |
| CF-ENR-011 | bordure_vue_contradiction | `K-0298` | MLY-BOR-020 | intervalle 0 (s 0.0-12.6 m, T3, vue 0.210 m mesurée au LiDAR 2021) contre MLY-BOR-020 à s 7.336 m « vue ≈ 5–10 cm » -> [0.05, 0.1] m (haute) -> vue lue 0.075 m (A2) |
| CF-ENR-012 | bordure_vue_contradiction | `K-0435` | MLY-BOR-031 | intervalle 3 (s 17.5-31.0 m, P1, vue 0.020 m « estimee » (a priori)) contre MLY-BOR-031 à s 15.503 m « vue ≈ 10–15 cm » -> [0.1, 0.15] m (haute, intervalle voisin) -> vue lue 0.125 m (T2) |
| CF-ENR-013 | bordure_vue_contradiction | `K-0439` | MLY-BOR-034 | intervalle 0 (s 0.0-86.5 m, T2, vue 0.140 m « estimee » (a priori)) contre MLY-BOR-034 à s 43.968 m « bordure arasée entre la voie en enrobé et l'aire de stationnement en pavés béton » -> [0.0, 0.03] m (moyenne) -> vue … |
| CF-ENR-014 | bordure_vue_contradiction | `K-0465` | MLY-BOR-043 | intervalle 1 (s 2.0-49.8 m, T2, vue 0.140 m « estimee » (a priori)) contre MLY-BOR-043 à s 39.708 m « rive arasée entre la voie en enrobé et les places en stabilisé / gravier, sur l'arête projetée » -> [0.0, 0.03] m (mo… |
| CF-ENR-016 | bordure_vue_contradiction | `K-0511` | MLY-BOR-056 | intervalle 0 (s 0.0-2.4 m, P1, vue 0.015 m mesurée au LiDAR 2021) contre MLY-BOR-056 à s 1.197 m « vue ≈ 10 cm » -> [0.08, 0.12] m (haute) -> vue lue 0.100 m (T2) |
| CF-ENR-022 | bordure_vue_contradiction | `K-0675` | MLY-BOR-078 | intervalle 7 (s 35.5-45.5 m, T2, vue 0.100 m mesurée au LiDAR 2021) contre MLY-BOR-078 à s 50.049 m « rive arasée de la contre-allée de stationnement (limite gravillons / enrobé), sur l'arête projetée » -> [0.0, 0.03] m… |
| CF-ENR-024 | coherence_desaccord | `lamp_9514828431` | PANO2026-019 | cohérence : deplacement de 0.1 m ; image à 1.98 m de la position corrigée et 1.88 m de l'origine (partiel) |
| CF-ENR-025 | coherence_desaccord | `lamp_9665416717` | ORTHO_A-0167 | cohérence : deplacement de 0.1 m ; image à 0.84 m de la position corrigée et 0.88 m de l'origine (partiel) |
| CF-ENR-026 | coherence_desaccord | `lamp_9665416817` | VISION-PANORAMAX-1-55, VISION-PANORAMAX-2-57 | cohérence : deplacement de 0.65 m ; image à 0.44 m de la position corrigée et 0.58 m de l'origine (partiel) |
| CF-ENR-027 | coherence_desaccord | `mat_camera_SW_TPC` | pano_0-47 | cohérence : deplacement de 0.05 m ; image à 1.58 m de la position corrigée et 1.59 m de l'origine (partiel) |
| CF-ENR-028 | coherence_desaccord | `pan_B6a1_1` | PANO2026-018 | cohérence : deplacement de 0.016 m ; image à 0.70 m de la position corrigée et 0.68 m de l'origine (partiel) |
| CF-ENR-029 | coherence_desaccord | `pan_C13a_1` | PANO2026-018 | cohérence : deplacement de 0.016 m ; image à 0.70 m de la position corrigée et 0.68 m de l'origine (partiel) |
| CF-ENR-030 | deplacement_non_etaye | `K-0227` | ORTHO_A-0019 | translation de 0.87 m proposée ; géométrie levée GAM : translation > 0,5 m (FUS-POS-06) |
| CF-ENR-031 | deplacement_non_etaye | `arbre_224` | DOC-LOCALE-018, VISION-PANORAMAX-2-13 | deplacement de 7.82 m proposé ; σ fusion 1.87 m > 0,5 m ; σ fusion 1.87 m > preuve de la description (0.05 m) ; objet levé GAM : déplacement > 0,5 m (FUS-POS-06) |
| CF-ENR-032 | deplacement_non_etaye | `armoire_1313238971` | ORTHO-B-171 | deplacement de 1.04 m proposé ; une seule source non triangulée et pas de correction affirmée ; aucune mesure stricte (FUS-COUV-02) |
| CF-ENR-033 | deplacement_non_etaye | `banc_8360664518` | ORTHO_A-0100 | deplacement de 4.47 m proposé ; aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines) ; aucune mesure stricte (FUS-COUV-02) |
| CF-ENR-034 | deplacement_non_etaye | `lamp_9514828431` | PANO2026-019 | deplacement de 1.88 m proposé ; σ fusion 0.60 m > 0,5 m |
| CF-ENR-035 | deplacement_non_etaye | `mat_camera_SW_TPC` | pano_0-47 | deplacement de 1.59 m proposé ; aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines) ; aucune mesure stricte (FUS-COUV-02) |
| CF-ENR-036 | deplacement_non_etaye | `poteau_reseau_12888048898` | pano_0-21 | deplacement de 1.81 m proposé ; aucune mesure stricte (FUS-COUV-02) ; mesures antérieures aux travaux, dans leur emprise, sans appui de conservation (FUS-DATE-02) |
| CF-ENR-037 | deplacement_non_etaye | `poteau_reseau_12888056356` | pano_0-20 | deplacement de 3.29 m proposé ; aucune mesure stricte (FUS-COUV-02) ; mesures antérieures aux travaux, dans leur emprise, sans appui de conservation (FUS-DATE-02) |
| CF-ENR-038 | deplacement_non_etaye | `potelet_12462947806` | ORTHO_A-0081 | deplacement de 1.97 m proposé ; une seule source non triangulée et pas de correction affirmée ; aucune mesure stricte (FUS-COUV-02) |
| CF-ENR-039 | doublon_apres_correction | `poteau_reseau_12888056356` | pano_0-20 | position corrigée à 0.66 m de lamp_lidar_SW_NO (lampadaire) : même objet probable |
| CF-ENR-040 | existence_douteuse_2026 | `ML-0222` | MLY-MAR-001 | absence ou retrait vu sans preuve stricte, ou constat de revue « à vérifier » (absence 0.30, retrait 0.00, présence 0.00). le tracé tombe sur la bande plantée (haie taillée devant un muret) : aucun marquage possible |
| CF-ENR-041 | existence_douteuse_2026 | `ML-5341` | REV-ARB-005-03 | absence ou retrait vu sans preuve stricte, ou constat de revue « à vérifier » (absence 0.30, retrait 0.00, présence 0.00). au bord droit du cadre, au-delà de ML-5342 : enrobé et butée béton, aucune ligne blanche lisible… |
| CF-ENR-042 | existence_douteuse_2026 | `ML-5342` | REV-ARB-005-01 | absence ou retrait vu sans preuve stricte, ou constat de revue « à vérifier » (absence 0.60, retrait 0.00, présence 0.00). place à l'est de la Dacia vue en entier, de près : enrobé gris et butée béton, aucune ligne blan… |
| CF-ENR-043 | existence_douteuse_2026 | `ML-5343` | REV-ARB-005-02 | absence ou retrait vu sans preuve stricte, ou constat de revue « à vérifier » (absence 0.30, retrait 0.00, présence 0.00). tracé en grande partie sous la Dacia et son ombre ; l'extrémité visible côté trottoir n'a aucune… |
| CF-ENR-044 | lien_introuvable | `BEV-0348-2` | VISION-PANORAMAX-1-24 | id BEV-0348-2 absent de la description courante et sans équivalent spatial |
| CF-ENR-057 | surface_a_decouper | `S-0094a` | ORTHO-B-039, ORTHO-B-099 | surface de 11598 m² (espace_vert, gazon_tondu) contenant des sous-zones observées : gazon_tondu (ORTHO-B-039); enrobe_bbsg_ancien (ORTHO-B-099) |
| CF-ENR-058 | surface_a_decouper | `S-0159a` | ORTHO-B-088 | surface de 4036 m² (parking, enrobe_bbsg_ancien) contenant des sous-zones observées : |
| CF-ENR-059 | surface_a_decouper | `S-0161a` | ORTHO-B-077, ORTHO-B-149, ORTHO-B-156 | surface de 10647 m² (parking, enrobe_bbsg_ancien) contenant des sous-zones observées : gravier (ORTHO-B-077); eau_bassin (ORTHO-B-149) |
| CF-ENR-060 | surface_a_decouper | `S-0374a` | MLY-SUR-087 | surface de 2072 m² (espace_vert, gazon_tondu) contenant des sous-zones observées : herbe_haute (MLY-SUR-087) |
| CF-ENR-092 | validite_2026_douteuse | `K-0078` | ORTHO-B-094 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-094, FUS-VAL-03). l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) traverse… |
| CF-ENR-093 | validite_2026_douteuse | `K-0081` | ORTHO-B-094 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-094, FUS-VAL-03). l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) traverse… |
| CF-ENR-094 | validite_2026_douteuse | `K-0082` | ORTHO-B-094 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-094, FUS-VAL-03). l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) traverse… |
| CF-ENR-095 | validite_2026_douteuse | `K-0083` | ORTHO-B-094 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-094, FUS-VAL-03). l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) traverse… |
| CF-ENR-096 | validite_2026_douteuse | `K-0084` | ORTHO-B-094 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-094, FUS-VAL-03). l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) traverse… |
| CF-ENR-097 | validite_2026_douteuse | `K-0085` | ORTHO-B-094 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-094, FUS-VAL-03). l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) traverse… |
| CF-ENR-098 | validite_2026_douteuse | `K-0086` | ORTHO-B-094 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-094, FUS-VAL-03). l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) traverse… |
| CF-ENR-099 | validite_2026_douteuse | `MP-0370` | ORTHO_A-0181 | absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO_A-0181, FUS-VAL-04). en 05/2022 l'emplacement est un terrain de chantier (terre, gravats, herbe) sans aucun marquage : la « rangée ja… |
| CF-ENR-100 | validite_2026_douteuse | `MS-5129` | VISION-PANORAMAX-2-49 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la fin des travaux, dans leur emprise, sans appui de conservation (VISION-PANORAMAX-2-49, FUS-DATE-02). |
| CF-ENR-101 | validite_2026_douteuse | `MZ-5002` | ORTHO-B-091 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-091, FUS-VAL-03). rien de peint au point de MZ-5002 (forme en Y, « conserve ») : enrobé d… |
| CF-ENR-102 | validite_2026_douteuse | `arbre_022` | ORTHO_A-0046 | absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO_A-0046, FUS-VAL-04). pelouse sans couronne à la position en 05/2022 |
| CF-ENR-103 | validite_2026_douteuse | `arbre_071` | ORTHO-B-197 | absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO-B-197, FUS-VAL-04). aucun arbre au point de arbre_071 (« h 5 m ») sur le parvis en enrobé noir en mai 2022 : plantation postérieure |
| CF-ENR-104 | validite_2026_douteuse | `arbre_184` | MLY-CON-019, pano_0-16 | absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (MLY-CON-019, pano_0-16, FUS-VAL-04). à la position d'arbre_184 : abri voyageurs vitré, barrière et trottoir ; arbres seulement de part et d… |
| CF-ENR-105 | validite_2026_douteuse | `arbre_229` | MLY-CON-020, pano_0-14 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (MLY-CON-020, FUS-VAL-03) ; validité 2026 incertaine (pano_0-14, FUS-VAL-04). haie taillée ≈ 1,2 m… |
| CF-ENR-106 | validite_2026_douteuse | `arbre_230` | MLY-CON-021, MLY-CON-022, pano_0-13 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (MLY-CON-021, MLY-CON-022, FUS-VAL-03) ; validité 2026 incertaine (pano_0-13, FUS-VAL-04). haie ta… |
| CF-ENR-107 | validite_2026_douteuse | `arbre_257` | ORTHO-B-161 | absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO-B-161, FUS-VAL-04). aucun arbre en 2022 aux points de arbre_257 et arbre_258 (« h 5 m, couronne 2,5 m » : valeurs par défaut) : enrob… |
| CF-ENR-108 | validite_2026_douteuse | `arbre_258` | ORTHO-B-161 | absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO-B-161, FUS-VAL-04). aucun arbre en 2022 aux points de arbre_257 et arbre_258 (« h 5 m, couronne 2,5 m » : valeurs par défaut) : enrob… |
| CF-ENR-109 | validite_2026_douteuse | `arbre_269` | ORTHO_A-0196 | absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO_A-0196, FUS-VAL-04). terre nue de chantier à la position en 05/2022 (hors de la couronne de arbre_270) |
| CF-ENR-110 | validite_2026_douteuse | `arbre_362` | ORTHO-B-193 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-193, FUS-VAL-03). au point de arbre_362 (h 25,4 m, couronne 13,9 m d'après le LiDAR 2021)… |
| CF-ENR-111 | validite_2026_douteuse | `arbre_383` | ORTHO-B-194 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-194, FUS-VAL-03). même cas que arbre_362 : h 22,7 m décrite, sol de chantier nu en mai 20… |
| CF-ENR-112 | validite_2026_douteuse | `arbre_435` | ORTHO_A-0178 | absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO_A-0178, FUS-VAL-04). pelouse ouverte (en partie à l'ombre des arbres voisins au NO) sans couronne de conifère à la position ; un cèdr… |
| CF-ENR-113 | validite_2026_douteuse | `barriere_levante_12462947804` | ORTHO-B-189 | absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO-B-189, FUS-VAL-04). aucune lisse ni potence visible au point (voie du parking) en 2022 ; objet OSM récent, peut-être postérieur |
| CF-ENR-114 | validite_2026_douteuse | `chicane_12462947805` | ORTHO-B-177 | absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO-B-177, FUS-VAL-04). aucune barrière / chicane visible au point (place de parking marquée) ; peut être postérieure à 2022 (nœud OSM ré… |
| CF-ENR-115 | validite_2026_douteuse | `cloture_gam_001` | ORTHO-B-083 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-083, FUS-VAL-03). le tracé GAM de cloture_gam_002 (et cloture_gam_001 dans son prolongeme… |
| CF-ENR-116 | validite_2026_douteuse | `cloture_gam_002` | ORTHO-B-083 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-083, FUS-VAL-03). le tracé GAM de cloture_gam_002 (et cloture_gam_001 dans son prolongeme… |
| CF-ENR-117 | validite_2026_douteuse | `cloture_gam_047` | MLY-MOB-023 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (MLY-MOB-023, FUS-VAL-03). |
| CF-ENR-118 | validite_2026_douteuse | `cloture_gam_049` | VISION-PANORAMAX-1-64, VISION-PANORAMAX-1-65 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (VISION-PANORAMAX-1-64, VISION-PANORAMAX-1-65, FUS-VAL-03). ; aucune clôture le long de la ligne c… |
| CF-ENR-119 | validite_2026_douteuse | `lamp_12758859672` | MLY-CON-026, ORTHO-B-061 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-06-07) (MLY-CON-026, ORTHO-B-061, FUS-VAL-03). aucun mât à la position (voitures en stationnement, haie) … |
| CF-ENR-120 | validite_2026_douteuse | `lamp_12758894668` | ORTHO-B-062 | absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO-B-062, FUS-VAL-04). rien au point décrit (bord de la serre) en 2022 ; nœud OSM 2026-03 : candélabre peut-être posé après 2022 |
| CF-ENR-121 | validite_2026_douteuse | `lamp_12887274334` | MLY-CON-027, ORTHO-B-151 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-10-25) (MLY-CON-027, ORTHO-B-151, FUS-VAL-03). massifs arbustifs et haie de la jardinerie, aucun mât à la… |
| CF-ENR-122 | validite_2026_douteuse | `lamp_13539965051` | MLY-CON-028, ORTHO-B-141 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2026-02-10) (MLY-CON-028, ORTHO-B-141, FUS-VAL-03). grand massif arbustif à côté de la rampe d'accès, aucun mâ… |
| CF-ENR-123 | validite_2026_douteuse | `pan_J5_1` | ORTHO-B-003 | absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO-B-003, FUS-VAL-04). aucune balise ni ombre au point décrit (extrémité NE de l'îlot I-0386) ; balise vue sur les photos 2025-05 : posé… |
| CF-ENR-124 | validite_2026_douteuse | `stationnement_velos_12673486211` | MLY-MOB-035 | absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-03-17) (MLY-MOB-035, FUS-VAL-03). banc-muret béton, rocher et haie ; aucun arceau vélo visible à la posit… |

## Carte de couverture

`couverture_preuves.png` : A/C preuve stricte par entité et par bordure, colorée par classe de date relative aux travaux (rampe bleue ordinale : avant travaux dans l'emprise avec appui clair, avant travaux hors emprise moyen, après travaux foncé ; anneau gris foncé : indice seulement ; anneau gris clair : non concluant ou non valable 2026 ; petit point gris : aucune observation), zone des travaux hachurée (extension FUS-ZONE-01 comprise), positions des photos citées (croix : Panoramax, point : Mapillary, étoile : photo 2026) ; B/D décisions (carré orange plein : attribut à appliquer, creux : en revue ; flèche : déplacement, à l'échelle au-delà de 1 m et x5 en dessous ; losange aqua : ajout ; croix épaisse : absent / retirer, fine : absence à vérifier ; point gris : confirmée ; anneau rouge : conflit à vérifier). Fond : ortho 2022 éclaircie. `couverture.json` : tableaux complets (large et stricte).

## Règles de fusion

- **FUS-LIEN-01** : lien_description explicite (ids séparés par « ; ») résolu dans l'index : base v0.3 > mobilier > arbres > instances > bordures_site > surfaces v1 > propositions de cohérence.
- **FUS-LIEN-02** : marquage absent de la v0.3 mais présent dans marquages_indices_v1 : remappé par lien_v1 -> marquages_correspondance (devenir « genere » -> entité v0.3 ; « retire » -> entité retirée).
- **FUS-LIEN-03** : surface v0.2 sans suffixe (S-0121) : polygone S-0121* qui contient le point (sinon le plus proche à ≤ 1 m).
- **FUS-LIEN-04** : autre id introuvable : appariement spatial dans la famille de son préfixe, tolérance de la classe ; sinon conflit lien_introuvable.
- **FUS-LIEN-05** : liens secondaires (attributs liens / confirmes / arbres_confirmes / arbres) : l'observation vaut pour chaque entité citée (attributs et existence) ; la position ne vaut que pour les liens primaires co-implantés (≤ 1,5 m, même support).
- **FUS-LIEN-06** : observation sans lien (statut ≠ absent_de_description, précision ≤ 3 m) : entité la plus proche de la famille compatible dans la tolérance de classe.
- **FUS-CTX-01** : observation de contexte (précision absente ou > 5 m, sous-type chantier / hors emprise / programme / état 2022 remplacé, bâtiment) sans lien : indexée, jamais fusionnée ni ajoutée.
- **FUS-TMP-01** : objet temporaire (chantier, provisoire, temporaire, base vie, bungalow, affiche) : jamais ajouté ; s'il est lié et que l'image est postérieure à l'attestation de l'objet, existence « non_instancier » (sinon conflit validite_2026_douteuse).
- **FUS-VAL-01** : poids de validité 2026 : vrai 1 ; incertain 0,5 (attributs et mesures seulement, FUS-VAL-04) ; faux 0 (observation historique, conservée pour la traçabilité).
- **FUS-VAL-02** : constat indépendant de la date (sous-type faux_positif*, raison « artefact », marquage posé sur une toiture ou un massif) : poids 1 même si valide_2026 = faux, à condition que la projection photo soit vue à 15 m au plus de la caméra (attributs.image.distance_m ; sans limite sur une ortho) ; au-delà, constat ordinaire, que seul un arbitrage de revue (FUS-ARB-01) peut corroborer (critique de couverture : MLY-MAR-017, projection à 25,9 m tombée sur la haie, alors que la photo 2026 montre des places en enrobé).
- **FUS-VAL-04** : validité 2026 « incertaine » : jamais une preuve de présence ni d'absence (existence, couverture, statut confirmé) ; seuls les attributs et les mesures de position la gardent avec le poids 0,5 (mesures toujours en revue, FUS-POS-05).
- **FUS-CONF-02** : projection de la description sur une photo prise à plus de 20 m (attributs.image.distance_m) : confiance plafonnée à « faible » (à 20 m, 0,5° d'erreur de pose déplace le tracé de 0,17 m et l'occultation n'est plus lisible ; échecs de la critique au-delà de 20 m).
- **FUS-DATE-02** : classes de date relatives aux travaux (23/06-05/12/2025 ; trottoirs du Vercors jusqu'au 30/01/2026) : « apres_travaux » (image du 05/12/2025 ou après) ; « avant_travaux_hors_emprise » (image antérieure, entité à plus de 3 m de la zone des travaux FUS-ZONE-01) ; « avant_travaux_dans_emprise » (image antérieure, entité dans la zone ou à 3 m au plus). Les photos de 2025-01 à 2025-08 sont antérieures ou contemporaines du chantier : aucune n'est « après travaux ». Une observation « avant_travaux_dans_emprise » ne vaut (présence, absence, attribut, position) que si une règle appuie la conservation de l'entité pendant les travaux (FUS-SRC-001 de regles_conception, admissibilité par état) : marquage « conserve » ; bordure levée GAM hors du périmètre refait (zone_travaux_2025 faux, hauteur non « modifiee_2025 », à plus de 3 m d'une extension FUS-ZONE-01) ; surface « inchange_2022 » ou « construit_2023_2024 » hors de la zone ; îlot à ceinture levée GAM ; objet ou arbre attesté après les travaux (levé GAM, OSM édité à partir du 01/12/2025, « 2026 confirmé », Panoramax 2026, arbre du levé GAM 2026 à 2 m au plus). Sans appui : présumée conservée, pas prouvée (non probante).
- **FUS-ZONE-01** : zone des travaux 2025 : surfaces v1 « modifie_2025 », zones de relief reprises (ancienne chaussée rehaussée, traversées abaissées, trottoirs par défaut), et toute surface de la description dont une photo postérieure aux travaux (valide 2026, confiance moyenne ou haute) montre un revêtement neuf (sous-type ou matériau proposé « neuf ») : S-0268a, chaussée du Vercors, enrobé neuf sur PANO2026-034 (critique, cause 5) ; son état devient « modifie_2025 » (mise à jour etat_v1).
- **FUS-LIEN-09** : photo liée à 3 entités ou plus qui ne sont pas sur le même support (liens primaires non co-implantés et liens secondaires) : seule une entité dont l'identifiant est cité dans la preuve (preuve.note) ou dans le texte de l'observation est prouvée ; pour les autres, le lien devient « vu, non prouvé » (incertain : ni présence, ni attribut, ni couverture) (critique : PANO2026-014 liait 10 places, ses pixels de preuve n'en citent que 3).
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
- **FUS-POS-05** : application : « appliquer » si une mesure valide 2026 (poids 1) existe, σ ≤ 0,5 m, σ ≤ max(σ de la preuve décrite ; 0,30) et (triangulation, ou ≥ 2 sources indépendantes concordantes, ou position_corrigee affirmée par l'observateur en confiance ≥ moyenne) et qu'au moins une mesure est stricte (FUS-COUV-02) ; sinon « revue_requise ».
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
- **FUS-AUTO-01** : confirmation automatique d'un marquage ou d'une bordure sur ortho (contrôles ortho_A / ortho_B 2022, orthos récentes 2024, bordures « automatique_2_dates ») sans contrat FUS-AUTO-02 : requalifiée « incertain » (ni présence, ni preuve de couverture) sauf si une observation manuelle (contrôle visuel ou photo) confirme la même entité avec un poids de présence > 0. Deux contrôles automatiques ne se corroborent pas (erreurs corrélées : voitures garées aux mêmes places, ombres de supports fixes, lignes de places détectées à tort ; bordure K-0236 confirmée sur deux dates sans arête réelle).
- **FUS-AUTO-02** : contrat de tout contrôle automatique futur : il n'est accepté comme confirmation (poids x0,7) que s'il déclare attributs.controle_auto = {masque_vehicules_ombres: true (taches claires ou sombres de plus de 3 m² et de largeur ≥ 1,2 m, ombres portées), part_masquee ≤ 0,2 le long de l'objet, et pour un marquage reponse_ligne_fine: true (trait de 0,10 à 0,15 m répondant sur toute la longueur) ou reponse_peinture: true (flèche, symbole : part peinte ≥ 0,3) ; pour une bordure reponse_ligne_fine: true (tête de bordure claire de 0,10 à 0,20 m répondant sur toute la longueur) ou reponse_arete: true (saut de luminance de la face vue sur 80 % des profils non masqués)} ; calcul de référence : controle_auto.py ; sinon FUS-AUTO-01 (marquages, bordures) ou drapeau « automatique seul » (autres classes). Un contrôle automatique n'est jamais une preuve stricte (FUS-COUV-02).
- **FUS-ADD-04** : dédoublonnage des ajouts : entité existante de même classe (type de marquage compatible ; pavés de traversée = passage) dans un rayon max(1,5 m ; tolérance de classe) ; si elle vient d'un levé GAM (marquage, bordure, îlot, arbre, clôture), pas d'ajout : conflit ajout_contre_leve_gam (l'objet vu est probablement l'objet levé, mal placé ou mal typé ; à trancher sur photo 2026 ou terrain). Exception : l'atelier qui signale l'objet a aussi confirmé à la main l'entité levée, sans la retyper (deux objets distingués par le même observateur).
- **FUS-ARB-01** : arbitrages de revue (description/enrichi/arbitrages_fusion.json, clés = identifiants d'observations, jamais les ENR-* renumérotés) : ne_pas_instancier (ajout), ancrer_bord_ilot (ajout ponctuel ramené au bord de l'îlot ou de l'espace vert le plus proche, en retrait vers l'intérieur), mesure_position (coordonnées d'un document utilisées comme mesure de position, σ donné, pondérée comme FUS-POS-01), invalider_observation (lien d'une observation à une entité rendu « incertain » : erreur de projection, occultation), constat_revue (lecture d'une image par une revue, versée comme observation « REV-… » de l'agent revue, avec sa source, sa date, sa confiance et son drapeau « à vérifier »). Chaque arbitrage cite son motif et sa preuve ; un arbitrage sans effet ouvre un conflit arbitrage_inapplicable.
- **FUS-COUV-01** : couverture large (définition 0.2, gardée pour comparaison ; aucune décision ne l'utilise) : preuve image la plus récente, valable 2026 et concluante (présence, attribut, position, ou absence probante ; observations « incertain », liens invalidés ou groupés sans preuve propre, confirmations automatiques requalifiées exclues ; confiance faible et validité incertaine admises), par tranche : 2026 > 2025 > 2020-2024 (photos, ortho IGN 2024) > ortho 2022 > web seul ; « non concluant » : vue sans conclusion ; « non valable 2026 » : vue seulement avant sa forme 2026.
- **FUS-COUV-02** : couverture stricte (décisions) : au moins une observation image manuelle (ni contrôle automatique, ni document web), de confiance moyenne ou haute (après FUS-CONF-02), valide 2026 (vrai, ou constat indépendant de la date FUS-VAL-02), probante après FUS-VAL-03/04 et FUS-DATE-02, non invalidée (FUS-ARB-01) ni liée en groupe sans preuve propre (FUS-LIEN-09), portant sur la présence (confirme, attribut ou position corrigés) ou sur une absence probante. Classée par la meilleure classe de date (FUS-DATE-02) : après travaux > avant travaux hors emprise > avant travaux dans l'emprise avec appui de règle ; sinon « indice seulement » (vue concluante au sens large, sans preuve stricte). Le statut « confirmé », les décisions d'application (position, attribut, retrait) et la carte utilisent cette définition.
- **FUS-STAT-01** : statut de vérification d'une entité : « confirme » (preuve stricte de présence, sans correction ni contradiction) ; « corrige » (preuve stricte de présence, attribut ou position corrigés) ; « conteste » (preuve stricte de présence, mais attribut contredit : vue de bordure FUS-BOR-03) ; « absent_2026 » ou « a_retirer » (absence ou artefact prouvés strictement) ; « absent_2026_a_verifier » (FUS-EXI-04) ; « indice_seulement » (vue sans preuve stricte) ; « non_valable_2026 » (vue seulement avant sa forme 2026 ou sans appui de règle).
- **FUS-ATT-06** : décision d'une mise à jour d'attribut : « appliquer » si la valeur gagnante est portée par au moins une observation stricte (FUS-COUV-02) sans conflit d'attribut ; sinon « revue_requise ».
- **FUS-EXI-04** : absence sans preuve stricte : un retrait ou une absence 2026 qu'aucune observation stricte ne porte, ou dont un constat de revue est marqué « à vérifier », ou une absence vue (poids ≥ 0,3) sans présence ni seuil de retrait, devient « absent_2026_a_verifier » : l'entité est gardée (instancier = null) et un conflit existence_douteuse_2026 est ouvert.
- **FUS-BOR-01** : lecture des profils de bordure en texte libre (champs hauteur_vue_estimee_m, profil_observe, profil_description, observe, observation, note des observations de présence) : vue chiffrée (« vue ≈ 12–14 cm », « ≈0,13-0,15 m », « vue ≤ 5 cm ») -> intervalle [min ; max] (valeur seule « ≈ x » : x ± 0,02 m), lecture haute ; qualificatif explicite (arasée, à niveau, affleurante, sans vue, aucune bordure saillante) -> [0 ; 0,03 m], lecture moyenne ; « basse » -> [0,03 ; 0,09 m], « bordure de trottoir » -> [0,09 ; 0,175 m], lecture faible ; abaissé (abaissé, bateau, chartière) -> abaissé vrai. Profil déduit de la vue par bordures.json (regles_affectation : P1 < 0,03 ; A2 < 0,09 ; T2 < 0,175 ; T3 < 0,30 m). Une limite sans mot de bordure (pelouse, haie, enrobé, rive) ne vote pas.
- **FUS-BOR-02** : vote par intervalle de la description : chaque lecture est rapportée à l'abscisse s de l'observation sur la bordure (≤ 3 m) ; poids = confiance x validité (FUS-DATE-02) x lecture (1 ; 0,8 ; 0,5) ; vue observée = moyenne pondérée des milieux ; profil = classe de cette vue ; abaissé : vote contre le rôle de l'intervalle (bateau, chartière). Accord : vue décrite dans l'intervalle lu ± 0,02 m ou même classe de profil -> attribut confirmé.
- **FUS-BOR-03** : contradiction de vue : intervalle lu qui exclut la vue décrite (± 0,02 m) avec une autre classe de profil (ex. rive « arasée » contre T2 de 8 à 14 cm), poids ≥ 0,15 -> conflit bordure_vue_contradiction (à vérifier), statut « conteste », proposition « revue_requise » (jamais appliquée sans revue : vue mesurée au LiDAR 2021 ou estimée a priori, signalée) ; lectures incompatibles entre elles -> conflit bordure_vue_desaccord.

## Limites

- Aucune image publique ne montre le cœur après les travaux : les 7 photos du 28/07/2026 sont sur la place, environ 135 m au sud, et seules 3 sont calées ; aucune entité du cœur n'a de preuve stricte après travaux. Seule une campagne terrain (stations du protocole, à compléter de S13, S14 et S15 proposées par la critique) peut couvrir le cœur et la zone des travaux.
- L'emprise des travaux est celle des surfaces et zones de relief 2025 connues, plus les surfaces vues refaites en 2026 (FUS-ZONE-01) ; une reprise non vue (trottoirs du Vercors au-delà de la photo) reste hors emprise.
- Les appuis de conservation (FUS-DATE-02) reposent sur les états de la description (marquage « conserve », bordure hors périmètre refait…) : une erreur de ces états se propage.
- Les lectures de profil de bordure viennent de textes libres : la vue chiffrée est une estimation visuelle, pas une mesure ; une contradiction n'est jamais appliquée sans relevé.
- Les confirmations automatiques requalifiées ne sont pas des absences : ces objets restent décrits, sans preuve.
- `recon/pcg/enrichir/PROTOCOLE_TERRAIN.md` n'est pas modifié par la fusion : son propriétaire doit y reporter les stations S13, S14 et S15 de la critique, l'ordre de passage et les nouveaux taux sans preuve stricte (tableaux ci-dessus), et demander une photo rasante, mètre pliant en place, sur chaque bordure contestée.
- La description de base est régénérée en parallèle : relancer ce script après chaque régénération (les liens disparus deviennent des conflits `lien_introuvable`).
- Les poids et seuils (REGLES) sont des choix documentés, pas des mesures ; les sorties restent des propositions pour le composeur et l'arbitrage.
