# Rapport du lot « catalogue » : routes simples en description simple

*`recon/generateur/validation/RAPPORT_catalogue.md` — généré par `recon/generateur/scenes_simples/catalogue.py` (2026-10-17). Statut : **ok**.*

Douze tronçons droits de 80 à 120 m (une courbe), chacun décrit en YAML au format `description_simple/0.1` (`scenes_simples/FORMAT_PROPOSE.md`), avec un plan coté SVG généré (`scenes_simples/plans/`) et une ligne `attendus` comparée aux mesures recalculées par les règles de `regles_route_fr.json` (SHA-256 `d4d63edeabf0820a…`, 857 règles).

## Critères

| Critère | Valeur | Seuil | Atteint |
|---|---|---|---|
| C1_scenes | 12/12 (S01, S02, S03, S04, S05, S06, S07, S08, S09, S10, S11, S12) | 12 descriptions S01-S12 | oui |
| C2_lecture | 12/12 lues sans erreur (description_simple/0.1) | 100 % | oui |
| C3_longueurs | 12/12 dans [80 ; 120] m | 100 % | oui |
| C4_une_courbe | 1 scène(s) avec courbe | exactement 1 | oui |
| C5_regles_citees | 12/12 scènes dont toutes les règles citées existent | 100 % | oui |
| C6_attendus | 12/12 lignes « attendus » = mesures calculées | 100 % | oui |
| C7_conformite | 232/233 contrôles atteints ; 0 échec(s) bloquant(s) ; 1 avertissement(s) | 0 échec bloquant | oui |
| C8_plans_svg | 12/12 plans SVG | 100 % | oui |
| C9_tuiles_regardees | 12/12 scènes dont les tuiles ont été regardées | 100 % | oui |
| C10_determinisme | 13/13 fichiers identiques à l'octet entre deux exécutions | 100 % | oui |

## Scènes

| Scène | Titre | L (m) | Emprise (m) | Contrôles | Attendus |
|---|---|---|---|---|---|
| S01 | Route 1 + 1 hors agglomération, sans bordures, axe T1 passant en continue | 120 | 10 | 11/11 | 9/9 |
| S02 | Rue 1 + 1 urbaine, bordures T2, trottoirs de 2 m | 100 | 10 | 14/14 | 6/6 |
| S03 | Rue 1 + 1, stationnement longitudinal à droite, arbres en fosses entre les places | 100 | 12 | 19/19 | 10/10 |
| S04 | Rue 1 + 1 avec bandes cyclables des deux côtés | 100 | 14 | 19/19 | 7/7 |
| S05 | Rue 1 + 1, pistes cyclables unidirectionnelles au niveau du trottoir, séparées | 100 | 15.6 | 17/17 | 7/7 |
| S06 | Avenue 2 × 2 voies, terre-plein central planté bordé de T2 | 100 | 21 | 24/24 | 8/8 |
| S07 | Rue à sens unique 2 voies, flèches directionnelles « tout droit » | 100 | 10 | 19/19 | 8/8 |
| S08 | Rue 1 + 1 à 30 km/h, passage piéton puis dos-d'âne | 100 | 10 | 30/30 | 10/10 |
| S09 | Rue à sens unique, réduction de 2 à 1 voie avec flèches de rabattement | 100 | 10 | 21/21 | 11/11 |
| S10 | Rue 1 + 1 à 30 km/h, passage piéton sur plateau trapézoïdal | 100 | 10 | 28/28 | 9/9 |
| S11 | Rue 1 + 1 en courbe à gauche de rayon 60 m, bordures T2 et trottoirs | 102.832 | 10 | 14/15 | 7/7 |
| S12 | Rue à sens unique, voie générale + couloir bus à droite, BUS au sol | 100 | 10.3 | 16/16 | 7/7 |

### S01 — Route 1 + 1 hors agglomération, sans bordures, axe T1 passant en continue

- Fichier : `scenes_simples/S01_route_1x1_hors_agglomeration.yaml` ; plan : `recon/generateur/scenes_simples/plans/S01_route_1x1_hors_agglomeration.svg` (2760 × 750 px, 20 px/m).
- Profil (gauche → droite) : bd1 bande_derasee 1.75 | acc1 accotement_revetu 0.25 | v1 voie_circulation 3.0 | v2 voie_circulation 3.0 | acc2 accotement_revetu 0.25 | bd2 bande_derasee 1.75.
- Mesures : `{"longueur": 120.0, "largeur_emprise": 10.0, "largeur_chaussee": 6.5, "voies": {"arriere": 1, "avant": 1}, "traits": {"T1 2u": 1, "T2 3u": 38, "T3 2u": 18}, "continues_m": {"continue 2u": 32.0}, "fleches": {"RAB_D": 3}, "annonce": {"L": 78.0, "s0": 10.0, "s1": 88.0}, "fleches_s": [10.0, 49.0, 75.0]}`.
- Constat visuel (tuiles regardées) : Annonce T3 de 10 à 88 m avec 3 flèches RAB_D à cheval sur l'axe (pied à gauche, pointe à droite du sens avant), un trait T1 de 0 à 3 m, continue à partir de 88 m après un vide de 1,33 m ; rives T2 au bord de la chaussée, surlargeur revêtue visible ; accotements enherbés distincts des abords (abords éclaircis après la 1re lecture, où ils se confondaient).

### S02 — Rue 1 + 1 urbaine, bordures T2, trottoirs de 2 m

- Fichier : `scenes_simples/S02_rue_1x1_bordures_trottoirs.yaml` ; plan : `recon/generateur/scenes_simples/plans/S02_rue_1x1_bordures_trottoirs.svg` (2360 × 750 px, 20 px/m).
- Profil (gauche → droite) : tr1 trottoir 2.0 | v1 voie_circulation 3.0 | v2 voie_circulation 3.0 | tr2 trottoir 2.0.
- Mesures : `{"longueur": 100.0, "largeur_emprise": 10.0, "largeur_chaussee": 6.0, "voies": {"arriere": 1, "avant": 1}, "traits": {"T'1 2u": 16}, "bordures_m": {"T2": 200.0}}`.
- Constat visuel (tuiles regardées) : Profil lisible : trottoirs, bordure + caniveau, axe T'1 de 1,50 m tous les 6,50 m ; chaînes de cotes 2,00 / 3,00 / 3,00 / 2,00, emprise 10,00.

### S03 — Rue 1 + 1, stationnement longitudinal à droite, arbres en fosses entre les places

- Fichier : `scenes_simples/S03_rue_stationnement_arbres.yaml` ; plan : `recon/generateur/scenes_simples/plans/S03_rue_stationnement_arbres.svg` (2360 × 790 px, 20 px/m).
- Profil (gauche → droite) : tr1 trottoir 2.0 | v1 voie_circulation 3.0 | v2 voie_circulation 3.0 | st1 stationnement 2.0 | tr2 trottoir 2.0.
- Mesures : `{"longueur": 100.0, "largeur_emprise": 12.0, "largeur_chaussee": 8.0, "voies": {"arriere": 1, "avant": 1}, "traits": {"T'1 2u": 16, "T'2 2u": 65}, "bordures_m": {"T2": 165.0}, "bordures_avancees_m": {"T2": 91.0}, "arbres": 14, "avancees": 14, "places": 13}`.
- Constat visuel (tuiles regardées) : 14 avancées plantées tous les 7,50 m, bordure sur trois côtés, arbre à 1,50 m du bord de la voie ; ligne T'2 de 5 traits par place, interrompue au droit des avancées. Défaut vu et corrigé : à la 1re lecture la bordure principale et le caniveau traversaient les avancées ; ils sont maintenant interrompus.

### S04 — Rue 1 + 1 avec bandes cyclables des deux côtés

- Fichier : `scenes_simples/S04_rue_bandes_cyclables.yaml` ; plan : `recon/generateur/scenes_simples/plans/S04_rue_bandes_cyclables.svg` (2360 × 830 px, 20 px/m).
- Profil (gauche → droite) : tr1 trottoir 2.0 | bc1 bande_cyclable 2.0 | v1 voie_circulation 3.0 | v2 voie_circulation 3.0 | bc2 bande_cyclable 2.0 | tr2 trottoir 2.0.
- Mesures : `{"longueur": 100.0, "largeur_emprise": 14.0, "largeur_chaussee": 10.0, "voies": {"arriere": 1, "avant": 1}, "traits": {"T'1 2u": 16, "T3 5u": 46}, "bordures_m": {"T2": 200.0}, "figurines": 4}`.
- Constat visuel (tuiles regardées) : Lignes T3 5u (3,00 / 1,33, 0,25 de large) des deux bandes, figurines vélo dans l'axe des bandes, roues vers le cycliste qui arrive (figurine D.1 à roues pleines, conforme à la planche D.1 regardée).

### S05 — Rue 1 + 1, pistes cyclables unidirectionnelles au niveau du trottoir, séparées

- Fichier : `scenes_simples/S05_rue_pistes_sur_trottoir.yaml` ; plan : `recon/generateur/scenes_simples/plans/S05_rue_pistes_sur_trottoir.svg` (2360 × 862 px, 20 px/m).
- Profil (gauche → droite) : tr1 trottoir 2.0 | sep1 separateur 0.3 | pc1 piste_cyclable 2.0 | sep2 separateur 0.5 | v1 voie_circulation 3.0 | v2 voie_circulation 3.0 | sep3 separateur 0.5 | pc2 piste_cyclable 2.0 | sep4 separateur 0.3 | tr2 trottoir 2.0.
- Mesures : `{"longueur": 100.0, "largeur_emprise": 15.6, "largeur_chaussee": 6.0, "voies": {"arriere": 1, "avant": 1}, "traits": {"T'1 2u": 16}, "bordures_m": {"T2": 200.0}, "figurines": 4}`.
- Constat visuel (tuiles regardées) : Pistes en enrobé sombre au niveau du trottoir, bande pavée de 0,50 m contre la bordure T2, bande pavée de 0,30 m côté trottoir en dalles claires ; contraste net ; figurines orientées dans le sens de chaque piste.

### S06 — Avenue 2 × 2 voies, terre-plein central planté bordé de T2

- Fichier : `scenes_simples/S06_avenue_2x2_terre_plein_plante.yaml` ; plan : `recon/generateur/scenes_simples/plans/S06_avenue_2x2_terre_plein_plante.svg` (2360 × 970 px, 20 px/m).
- Profil (gauche → droite) : tr1 trottoir 2.0 | v1 voie_circulation 3.0 | v2 voie_circulation 3.0 | bdg1 bande_derasee 0.5 | tp1 terre_plein 4.0 | bdg2 bande_derasee 0.5 | v3 voie_circulation 3.0 | v4 voie_circulation 3.0 | tr2 trottoir 2.0.
- Mesures : `{"longueur": 100.0, "largeur_emprise": 21.0, "largeur_chaussee": 6.5, "voies": {"arriere": 2, "avant": 2}, "traits": {"T'1 2u": 32}, "continues_m": {"continue 3u": 200.0}, "bordures_m": {"T2": 400.0}, "arbres": 13}`.
- Constat visuel (tuiles regardées) : Deux chaussées de 2 voies (T'1), continues 3u le long des BDG de 0,50 m, TPC engazonné de 4,00 m bordé de T2, 13 arbres dans l'axe du TPC.

### S07 — Rue à sens unique 2 voies, flèches directionnelles « tout droit »

- Fichier : `scenes_simples/S07_rue_sens_unique_2_voies.yaml` ; plan : `recon/generateur/scenes_simples/plans/S07_rue_sens_unique_2_voies.svg` (2360 × 750 px, 20 px/m).
- Profil (gauche → droite) : tr1 trottoir 2.0 | v1 voie_circulation 3.0 | v2 voie_circulation 3.0 | tr2 trottoir 2.0.
- Mesures : `{"longueur": 100.0, "largeur_emprise": 10.0, "largeur_chaussee": 6.0, "voies": {"avant": 2}, "traits": {"T'1 2u": 16}, "bordures_m": {"T2": 200.0}, "fleches": {"TD": 6}, "fleches_s": [20.0, 40.0, 60.0, 20.0, 40.0, 60.0]}`.
- Constat visuel (tuiles regardées) : Flèches TD (tige 0,15, tête 0,70 × 2,00) au milieu de chaque voie, dans le même profil, à 20 / 40 / 60 m.

### S08 — Rue 1 + 1 à 30 km/h, passage piéton puis dos-d'âne

- Fichier : `scenes_simples/S08_rue_dos_d_ane_passage.yaml` ; plan : `recon/generateur/scenes_simples/plans/S08_rue_dos_d_ane_passage.svg` (2360 × 750 px, 20 px/m).
- Profil (gauche → droite) : tr1 trottoir 2.0 | v1 voie_circulation 3.0 | v2 voie_circulation 3.0 | tr2 trottoir 2.0.
- Mesures : `{"longueur": 100.0, "largeur_emprise": 10.0, "largeur_chaussee": 6.0, "voies": {"arriere": 1, "avant": 1}, "traits": {"T'1 2u": 12, "T3 2u": 5}, "bordures_m": {"T2": 200.0}, "passages": [{"s": 48.0, "W": 6.0, "bandes": 5, "e": 0.583, "longueur_bandes": 4.0}], "triangles": 6, "abaisses": 2, "bev": 2, "ralentisseurs": [{"type": "dos_d_ane", "s": 54.0, "longueur": 4.0, "hauteur": 0.1, "s_debut": 54.0, "s_fin": 58.0}]}`.
- Constat visuel (tuiles regardées) : Passage de 5 bandes de 0,50 × 4,00 ; abaissé (bordure en ocre) de 4,00 m et rampants latéraux de 2,40 m de chaque côté ; BEV à plots à 0,50 m du nez ; axe coupé à 0,50 m des bandes ; dos-d'âne 54-58 avec 3 triangles par voie sur la moitié montante, pointes dans le sens de circulation de chaque voie ; axe T3 sur le ralentisseur jusqu'à 68 m puis T'1.

### S09 — Rue à sens unique, réduction de 2 à 1 voie avec flèches de rabattement

- Fichier : `scenes_simples/S09_reduction_2_vers_1_voie.yaml` ; plan : `recon/generateur/scenes_simples/plans/S09_reduction_2_vers_1_voie.svg` (2360 × 750 px, 20 px/m).
- Profil (gauche → droite) : tr1 trottoir loi | v1 voie_circulation loi | v2 voie_circulation 3.0 | tr2 trottoir 2.0.
- Mesures : `{"longueur": 100.0, "largeur_emprise": 10.0, "largeur_chaussee": 6.0, "voies": {"avant": 2}, "traits": {"T'1 2u": 13}, "bordures_m": {"T2": 200.23}, "fleches": {"RAB_D": 2}, "hachures": 4, "aplats": 2, "oblique": {"L": 39.0, "s0": 45.0, "s1": 84.0, "PCI": 64.5, "Lp": 19.5}, "fleches_s": [25.5, 51.5]}`.
- Constat visuel (tuiles regardées) : Oblique continue 3u de 45 à 84 m raccordée au nez de bordure aux deux bouts, bordure rabattue de 64,5 à 84 m, zébra : 4 hachures inclinées vers la voie ouverte et 2 aplats de pointe ; flèche 1 à 25,5 m, flèche 2 à 51,5 m (0,26 m du bord de l'oblique) ; la ligne T'1 s'arrête à 80,1 m. Défauts vus et corrigés : flèche 2 à 1,4 cm de l'oblique et oblique finissant sur le caniveau dans une version précédente ; petite hachure tronquée à la sortie de l'aplat.

### S10 — Rue 1 + 1 à 30 km/h, passage piéton sur plateau trapézoïdal

- Fichier : `scenes_simples/S10_rue_plateau_passage.yaml` ; plan : `recon/generateur/scenes_simples/plans/S10_rue_plateau_passage.svg` (2360 × 750 px, 20 px/m).
- Profil (gauche → droite) : tr1 trottoir 2.0 | v1 voie_circulation 3.0 | v2 voie_circulation 3.0 | tr2 trottoir 2.0.
- Mesures : `{"longueur": 100.0, "largeur_emprise": 10.0, "largeur_chaussee": 6.0, "voies": {"arriere": 1, "avant": 1}, "traits": {"T'1 2u": 16}, "bordures_m": {"T2": 200.0}, "passages": [{"s": 50.0, "W": 6.0, "bandes": 5, "e": 0.583, "longueur_bandes": 5.0}], "abaisses": 2, "bev": 2, "ralentisseurs": [{"type": "trapezoidal", "s": 50.0, "plateau": 4.0, "hauteur": 0.1, "rampe_pct": 7.0, "rampant": 1.4286, "s_debut": 46.5714, "s_fin": 53.4286}]}`.
- Constat visuel (tuiles regardées) : Plateau de 4,00 m entre deux rampants de 1,43 m, bandes de 5,00 m débordant de 0,50 m sur les rampants, aucun triangle, abaissé (vue 0,02) et BEV au droit du plateau, axe coupé de 47 à 53 m.

### S11 — Rue 1 + 1 en courbe à gauche de rayon 60 m, bordures T2 et trottoirs

- Fichier : `scenes_simples/S11_rue_courbe_R60.yaml` ; plan : `recon/generateur/scenes_simples/plans/S11_rue_courbe_R60.svg` (2234 × 1537 px, 20 px/m).
- Profil (gauche → droite) : tr1 trottoir 2.0 | v1 voie_circulation 3.0 | v2 voie_circulation 3.0 | tr2 trottoir 2.0.
- Mesures : `{"longueur": 102.832, "largeur_emprise": 10.0, "largeur_chaussee": 6.0, "voies": {"arriere": 1, "avant": 1}, "rayons": [60.0], "traits": {"T'1 2u": 16}, "bordures_m": {"T2": 205.66}}`.
- Avertissement `courbe_epure` : courbe : rayon < 125 m → épure de giration bus à faire (lot L3a) = 60.0 (seuil >= 125) — RF-GV-RAY-012
- Constat visuel (tuiles regardées) : Courbe à gauche R = 60 m sur 60°, trottoirs, bordures et tirets suivent l'arc ; chaînage le long de l'arc. Défaut vu et corrigé : joint d'anticrénelage visible entre les deux voies (liseré de même couleur ajouté).

### S12 — Rue à sens unique, voie générale + couloir bus à droite, BUS au sol

- Fichier : `scenes_simples/S12_couloir_bus.yaml` ; plan : `recon/generateur/scenes_simples/plans/S12_couloir_bus.svg` (2360 × 756 px, 20 px/m).
- Profil (gauche → droite) : tr1 trottoir 2.0 | v1 voie_circulation 3.0 | bus1 voie_bus 3.3 | tr2 trottoir 2.0.
- Mesures : `{"longueur": 100.0, "largeur_emprise": 10.3, "largeur_chaussee": 6.3, "voies": {"avant": 2}, "traits": {}, "continues_m": {"continue 5u": 100.0}, "bordures_m": {"T2": 200.0}, "inscriptions": {"BUS": 1}}`.
- Constat visuel (tuiles regardées) : Couloir bus séparé par une continue 5u ; mot BUS (série V ≤ 70, 1,50 m) dans l'axe du couloir, pied côté conducteur, lu de gauche à droite par le conducteur.

## Règles manquantes, imprécises ou à corriger (signalées, non modifiées)

- RF-MQ-RAL-01 et gabarit TRIANGLE_DOS_ANE (dossier 08) : la correction du 17/10 dit la longueur de 2,00 m « non cotée par l'IISR » ; or la figure de l'IISR 7e partie p. 55, placée dans le § 118-9 A (dos-d'âne), porte une cote verticale « 2 m » et trois cotes « 0,70 m » (tuile t_iisr7_p55 regardée). À revoir par le propriétaire des règles (confiance remontable à haute) — aucune modification faite ici.
- RF-MQ-SC-11 (rive « rabattement : T'3 3u à partir de la 1re flèche ») : l'IISR p. 14 dit que la rive « peut » être remplacée par une T'3 3u « dans les intersections où il y a rabattement » ; la valeur fusionnée perd la condition d'intersection et le caractère facultatif (RF-OSM-MRQ-021 la garde : « approche_carrefour_avec_rabattement »). S01 garde donc la rive T2 3u.
- RF-MQ-RAB-05 : pour L = 39 m, la « distance à la ligne continue » est une case vide de l'IISR (p. 22) ; la base en déduit 0. Dans une réduction de voies (S09) la 3e flèche tombe alors au milieu de l'oblique, dans le zébra (marge mesurée −0,74 m) : la case vide signifie vraisemblablement « pas de 3e flèche » (2 flèches, exception d'agglomération de RF-MQ-RAB-03).
- DEF-034 (plateau h = 0,10) et DEF-005 (vue de trottoir 0,14) sont incompatibles avec RF-GV-RAL-002 (plateau = trottoir − 2 cm) : avec les deux défauts, la vue au droit d'un passage sur plateau vaut 0,04 m, au-dessus des 0,02 m d'un abaissé (RF-MA-ABA-001). S10 décrit une vue de 0,12 m pour rester conforme ; un défaut cohérent manque.
- RF-MA-ABA-005 (« partie abaissée = largeur du marquage ») contre RF-MQ-PP-04 (bandes prolongées de 0,50 m de part et d'autre du plateau) : sur un ralentisseur trapézoïdal l'abaissé (dessus du plateau, 4,00 m) est plus court que le marquage (5,00 m). Arbitrage à prendre.
- Aucune règle urbaine pour la longueur du rétrécissement physique d'une réduction de voies : RF-GV-PT-014 (déport 37 × d, ARP) est interurbaine (111 m pour 3 m) ; S09 dit Lp = 19,5 m.
- Aucune règle pour l'espace minimal entre deux marques distinctes (flèche / oblique, ligne / oblique) ni pour la phase des tirets et le traitement d'un trait tronqué : choix [G] du catalogue (2u par analogie avec RF-MQ-MUS-01 ; trait gardé s'il fait au moins la moitié d'un trait).
- DEF-030 « axe_depuis_bord_chaussee_min : 1,50 » : le bord de référence est ambigu (bord de voie circulée, ou bordure comme dans la scène E du PLAN_GENERATEUR) ; S03 le mesure depuis le bord de la voie.
- Avancées plantées entre places (S03) : aucune règle sur l'écoulement du caniveau interrompu (avaloir en amont, caniveau-grille) ; à fixer avant le lot L2.
- Courbe urbaine R = 60 m (S11) : aucune surlargeur urbaine chiffrée (RF-GV-RAY-012 est interurbaine) ; épure de giration bus à faire au lot L3a (avertissement non bloquant).

## Coordination avec le lot L0 (compilateur de description)

- Compilateur L0 (description/description_vers_modele.py, état du 17/10 vers 01 h 50) essayé sur les 12 descriptions, sorties dans recon/generateur/tmp/catalogue/l0/ : 8 compilent avec 0 erreur de validation (S02, S03, S04, S06, S08, S09, S10, S11).
- Refus à lever côté L0 : évènements zone_depassement_interdit (S01), fleches (S07), inscription (S12) ; bande separateur au niveau du trottoir (dz 0,14) suivie d une bordure T2 (S05, « deux bandes au même niveau ») ; nombre_fleches entier pour rabattement ; objets (avancees_plantees, arbres, figurines).
- Écart de règle relevé dans la sortie L0 de S09 : flèches de rabattement à 35,25 / 61,25 / 74,25 m comptées depuis le milieu du biseau physique (Lp = 19,5) ; IISR 115-4 A et RF-MQ-OBL-02, RF-MQ-RAB-04, RF-MQ-RAB-07 : oblique marquée de longueur L = 39 finissant au PCF (45 → 84), distances depuis son milieu (64,5) → 25,5 et 51,5 m ; 3e flèche (d = 0) dans le zébra → 2 flèches.
- Plateau + passage chez L0 : bandes de la longueur du plateau ; RF-MQ-PP-04 demande le plateau + 2 × 0,50 m.
- Biseau par défaut L0 = 37 × d (RF-GV-PT-014, ARP, interurbain) : pas une règle d agglomération.

## Déterminisme

13/13 fichiers (SVG + JSON) identiques à l'octet entre deux exécutions dans deux processus.

