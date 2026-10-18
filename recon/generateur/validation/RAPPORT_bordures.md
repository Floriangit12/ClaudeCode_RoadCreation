# Lot « bordures » : tous les types de bordures et de caniveaux, pièces d'abaissé et d'angle, nuancier B01, reliquats

*`recon/generateur/validation/RAPPORT_bordures.md` — 17/10/2026. Mesures : `validation/controler_bordures.py`
(→ `validation/rapport_bordures.json`). Route seule (étape 1) : sol neutre, ciel simple et soleil, ni décor ni végétation.*

## 1. Ce qui est livré

**Choisir n'importe quel type du catalogue dans la description.** `bordure T4`, `{bordure: GR_T2}`, `I3`, `P4`,
`T2_basse`, `T3_surbaissee`, `P1_basse`, `ACCESBUS`, `GR_A1`, `GR_A2`, `GR_P1`, `GR_P3`, `TU`, `AC1`, `paves_granit`,
`quai_bus`, `bordurette` (= P1), caniveaux `CS3`, `CS4` s'ajoutent aux mots existants (T1-T3, A1, A2, I1, I2, IL, P1-P3,
CS1, CS2, CC1, CC2, quai, bateau). Les 32 types du catalogue route_fr (26 bordures, 6 caniveaux) sont nommables et
posés dans B01, plus les 6 profils de `bordures.json` hors catalogue (TU, AC1, IL, PAVES_GRANIT, QUAI_BUS, T2_bateau).

- Cotes des profils ajoutés : règles `RF-AS-profil_*` de `regles_route_fr.json` (contour_uv_m), et pour GR_A1, GR_A2,
  GR_P3, qui n'ont pas de règle, le contour du mesh du catalogue (`catalogue_assets_route.json`, `bordure_<nom>_L100`).
- La table de `bordures.json` et `bordures_elements.json` (autre équipe) est gardée telle quelle pour ses profils.
- Tout est réuni dans `commun/bordures_catalogue.py` : table étendue, vues nominales, pièces d'abaissé, règles par
  contexte, meshes du catalogue, extension de la description.

**Règles par défaut selon le contexte** (`CONTEXTES`, 18 contextes). Chaque contexte donne un profil à une vue de sa plage
nominale, avec des règles existantes (C-B10 : 18/18) :

| Contexte | Profil, vue | Règles |
|---|---|---|
| trottoir | T2, 0,14 | RF-OSM-NIV-010, DEF-005, ARB-18 |
| îlot directionnel | I2, 0,11 | DEF-005, RF-AS-liste_profils_nf (I : îlots) |
| îlot franchissable, îlot central de route principale | I1, 0,06 | RF-GV-CAR-016, RF-MQ-ILOT-01 |
| refuge | T2, 0,12 | RF-MA-REF-003, DEF-005, RF-MQ-ILOT-01 (bordures hautes) |
| terre-plein / TPC de VRU | I2, 0,11 / T2, 0,14 | DEF-005 / RF-GV-TPC-002 |
| couronne franchissable de giratoire | T2_surbaissee, 0,03 | RF-GV-GIR-006 (≤ 3 cm), ARB-18 |
| îlot central de giratoire (derrière la couronne) | I1, 0,06 | RF-GV-GIR-006 (≤ 6 cm) |
| piste / trottoir, piste / chaussée, piste à niveau intermédiaire | A2 0,05 ; T2 0,13 ; A2 0,04 | RF-MA-SEP-004, RF-OBS-CYC-02, RF-MA-SEP-005 |
| entrée charretière | T2_bateau, 0,03 | RF-MA-TRO-015 (≤ 0,05), RF-MA-TRO-016 (sans BEV) |
| quai bus / quai à guide-roues | QUAI_BUS 0,21 / ACCESBUS 0,21 | DEF-032 / RF-MA-BUS-010 |
| bordurette, accotement, granit | P1 0,03 ; A1 0,09 ; GR_T2 0,14 | RF-AS-liste_profils_nf, RF-AS-profil_* |
| autoroute | pas de bordure | RF-GV-PON-005, RF-OSM-MRQ-022 |

Un saut de niveau sans règle (profil « autre », que `rg::nivellement` refusait) prend le profil dont la vue nominale
contient la vue : P1 sous 0,03, A2 de 0,03 à 0,09, T2 de 0,09 à 0,175, T3 ou T4 au-delà (`bordures.json`
regles_affectation, `RF-AS-profil_*`).

**Pièces d'abaissé.** Chaque type a sa pièce, de même base que lui :

| Type | Pièce d'abaissé | Source |
|---|---|---|
| T2 | T2_bateau | `bordures_elements.json` abaisses |
| T3, T3_basse | T3_surbaissee | RF-AS-raccord_bateau |
| T2_basse | T2_surbaissee | RF-AS-raccord_bateau |
| A2 | A2 | abaisses.entree_charretiere |

Les autres types sont posés abaissés avec leur propre contour (marqué [G]) : seule la tête chanfreinée ou arrondie
dépasse, ce qui respecte RF-MA-ABA-002. Les rampants sont des chartières : des lofts du profil courant vers la pièce,
qui suivent la pente du modèle. Un intervalle n'est « bateau » que s'il est plus bas que la vue courante de la file.
IL, les bordurettes et la T2 surbaissée de couronne, posées basses sur toute la file, restent donc « courant ».

**Pièces d'angle.** Elles s'appliquent à tous les coins (déviation de plus de 30°), dans tous les profils (C-B6 :
76/76) : deux éléments sur mesure en onglet, avec le sens (sortant ou rentrant) et la déviation dans `elements.json`.
Les boucles des îlots sont désormais ouvertes au milieu d'un côté : avant, un coin servait de début et de fin de file et
se posait en deux abouts sciés droits.

**Meshes du catalogue route_fr.** Chaque élément de `elements.json` porte un `asset_id` et un `asset_motif` : élément
entier L100 ou L050, coupe, pièce d'angle sortante ou rentrante (T1, T2, T3), raccord, ou équivalent (T2_bateau →
T2_surbaissee). Sinon, il porte le motif de la pièce sur mesure. Dans B01, 639 éléments sur 639 sont renseignés,
74,6 % de la longueur au catalogue et 49 meshes distincts. Le reste est sur mesure :
- 120 demi-pièces d'angle en onglet sur les profils qui n'ont pas de pièce d'angle au catalogue ;
- 16 chartières en plusieurs pièces (rampants de 2,40 et 2,00 m) ;
- les profils absents du catalogue.

**Corrections dans la chaîne.**
- **Une file par type** (`rg::vers_entites`, `decouper_profils`). `rg::nivellement` chaîne en une seule file les
  bordures d'une même limite sur toutes les sections, avec le profil de son premier point : un changement de type au fil
  de la rue était perdu (B01, premier essai : 6 caniveaux décrits, 1 posé). La file est maintenant coupée aux
  changements de profil, de caniveau ou de matériau dits des deux côtés. Les files sans changement sont inchangées.
- **Prototypes larges** (`pj::caniveau::2.2`). En 1.0, 2.0 et 2.1, les prototypes sont décalés de k m et retrouvés par
  `floor(z + 0,5)`. Or le CC2 fait exactement 0,50 m : son arête était rattachée au prototype voisin. Cela posait une
  face de 0,94 m à 2 cm au-dessus du caniveau CS1 (bande noire en vue de dessus). Correctif : pas de 2 m, dans la
  nouvelle version seulement. Le défaut restait latent tant que S01-S12 n'employaient que CS2.
- **Matériaux de rendu** (`rendu/rendu_l2b.py`). `granit_bordure` (granit_gris_flamme ramené à la valeur et à la teinte
  de la bordure béton) et `calcaire_bordure` retombaient sur `enrobe_trottoir`. `beton_bordure_clair` est 1,27 fois plus
  clair que le gris (`bordures_elements.json` materiaux), au lieu d'être identique.

## 2. Scène B01 « nuancier des bordures »

Description : `scenes_simples/B01_nuancier_bordures.yaml`, écrite par `scenes_simples/B01_generer.py`. Étiquettes :
`B01_nuancier_bordures.etiquettes.json`. Vues : `B01_nuancier_bordures.vues.json`.

La rue fait 96 m, en 2 × 1 voies de 3,00 m. Elle a trois rangées et 33 sections. Les bordures sont en béton gris sauf
mention contraire.

| Rangée | s (m) | Type (+ caniveau / bordurette) | Vue (m) | Vue nominale | Pièce d'abaissé | Matériau |
|---|---|---|---|---|---|---|
| G | 0-4,5 | T1 | 0,12 | 0,10-0,14 | T1 [G] | béton gris |
| G | 6-10,5 | T2 | 0,14 | 0,12-0,16 | T2_bateau | béton gris |
| G | 12-16,5 | T3 | 0,18 | 0,16-0,20 | T3_surbaissee | béton gris |
| G | 18-22,5 | T4 | 0,20 | 0,18-0,22 | T4 [G] | béton gris |
| G | 24-28,5 | GR_T1 | 0,12 | 0,10-0,14 | GR_T1 [G] | granit |
| G | 30-34,5 | GR_T2 | 0,14 | 0,12-0,16 | GR_T2 [G] | granit |
| G | 36-40,5 | T2_basse | 0,08 | 0,06-0,10 | T2_surbaissee | béton gris |
| G | 42-46,5 | T3_basse | 0,10 | 0,08-0,12 | T3_surbaissee | béton gris |
| G | 48-52,5 | PAVES_GRANIT | 0,12 | 0,10-0,13 | — | granit |
| G | 54-58,5 | QUAI_BUS (quai) | 0,21 | 0,18-0,21 | — | béton gris |
| G | 60-64,5 | ACCESBUS (quai) | 0,21 | 0,18-0,21 | — | béton gris |
| G | 66-70,5 | T2 | 0,14 | 0,12-0,16 | T2_bateau | béton clair |
| G | 72-76,5 | T2 | 0,14 | 0,12-0,16 | T2_bateau | calcaire |
| G | 78-96 | T2 continu, entrée charretière en s = 87 | 0,14 (0,05) | 0,12-0,16 | T2_bateau | béton gris |
| C | 0-4,5 | A1 | 0,09 | 0,06-0,12 | — | béton gris |
| C | 6-10,5 | A2 | 0,07 | 0,04-0,10 | A2 | béton gris |
| C | 12-16,5 | I1 | 0,06 | 0,06 | — | béton gris |
| C | 18-22,5 | I2 | 0,11 | 0,11 | — | béton gris |
| C | 24-28,5 | I3 | 0,06 | 0,06 | — | béton gris |
| C | 30-34,5 | I4 | 0,11 | 0,11 | — | béton gris |
| C | 36-40,5 | IL | 0,03 | 0,03 | — | béton gris |
| C | 42-46,5 | TU | 0,06 | 0,03-0,10 | — | béton gris |
| C | 48-52,5 | AC1 | 0,06 | 0,06-0,07 | — | béton gris |
| C | 54-58,5 | T2_surbaissee (couronne de giratoire) | 0,03 | 0,00-0,04 | — | béton gris |
| C | 60-64,5 | T2 (refuge) | 0,12 | 0,12-0,16 | — | béton gris |
| C | 66-70,5 | GR_A1 | 0,09 | 0,06-0,12 | — | granit |
| C | 72-76,5 | GR_A2 | 0,07 | 0,04-0,10 | — | granit |
| D | 0-13 | T2 + CS1 / P1 | 0,16 / 0,03 | 0,12-0,16 / 0-0,06 | T2_bateau | béton gris |
| D | 13-26 | T2 + CS2 / P2 | 0,16 / 0,03 | 0,12-0,16 / 0-0,08 | T2_bateau | béton gris |
| D | 26-39 | T3 + CS3 / P3 | 0,16 / 0,03 | 0,16-0,20 / 0-0,06 | T3_surbaissee | béton gris |
| D | 39-52 | T3 + CS4 / P4 | 0,16 / 0,03 | 0,16-0,20 / 0-0,05 | T3_surbaissee | béton gris |
| D | 52-65 | T2 + CC1 / GR_P1 | 0,16 / 0,03 | — / 0-0,06 | T2_bateau | bordurette en granit |
| D | 65-78 | T2 + CC2 / P1_basse | 0,16 / 0,03 | — / 0-0,04 | T2_bateau | béton gris |
| D | 78-87 | T2 + CS2 / P1, abaissé en s = 82,5 | 0,16 → 0,02 | — | T2_bateau | béton gris |
| D | 87-96 | T3 + CS3 / GR_P3, abaissé en s = 91,5 | 0,16 → 0,02 | — | T3_surbaissee | bordurette en granit |

**Rangée G (gauche).** Chaque bloc de trottoir ou de quai est séparé du suivant par 1,50 m de trottoir au niveau de la
chaussée. Il est donc fermé par deux retours, qui posent deux pièces d'angle sortantes. La vue de chaque bloc est dans
la plage nominale de son type.

**Rangée C (centre).** Les îlots ont la même largeur que la zone hachurée qui les sépare. Ils sont à plat (dévers 0, comme
la zone hachurée), de sorte que les retours ont une vue constante.

**Rangée D (droite).** Le trottoir est continu à une vue de 0,16, borne commune de T2 et de T3. La bande plantée est
0,03 m plus haute que lui, ce qui donne la vue de la bordurette. La zone des abaissés (s = 78 à 96) n'a pas d'îlot : un
abaissé décrit « côté droite » vise la première bordure à droite de la ligne de référence, qui serait celle d'un îlot.

**Rendus.** Les rendus sont dans `recon/out/generateur/B01/rendus/`. Les vues rapprochées sont à 1,5 m de haut, à 2,4 à
3,4 m de la file, en biais à 45°.
- `planche_B01.png` : vue de dessus de toute la rue (2 184 × 480 px, 4,6 cm/px) et vue conducteur.
- `planche_B01_etiquettes_1.png` et `planche_B01_etiquettes_2.png` : vue de dessus à la résolution native, avec le type
  et la vue de chaque tronçon.
- `planche_B01_detail_1.png` à `planche_B01_detail_4.png` : vue conducteur et 15 vues rapprochées.

## 3. Critères (mesurés, seuils non modifiés)

| Id | Critère | Valeur | Seuil | Atteint |
|---|---|---|---|---|
| C-B1 | Types du catalogue route_fr posés dans B01 | 32/32 | 32/32 | oui |
| C-B2 | Types du catalogue nommables par la description | 32/32 | 32/32 | oui |
| C-B3 | Vue posée des éléments courants = vue décrite | 432/432 | ± 5 mm | oui |
| C-B4 | Vue posée dans la vue nominale du profil | 432/432 | 100 % | oui |
| C-B5 | Pièce d'abaissé du type, vue ≤ 0,05 | 7/7 (T2_bateau, T3_surbaissee ; 0,02 et 0,05) | 100 % | oui |
| C-B6 | Coins de file posés en pièce d'angle | 76/76 (152 éléments, sortants) | 100 % | oui |
| C-B7 | Continuité des files (trous, recouvrements > 2 cm) | 0 m, 0 | 0 | oui |
| C-B8 | Éléments avec mesh du catalogue ou motif sur mesure | 639/639 ; 74,6 % de la longueur au catalogue | 100 % | oui |
| C-B9 | Contour posé des 17 profils ajoutés / mesh du catalogue, hors chanfrein arrière | 0,00 mm | ≤ 1 mm | oui |
| C-B10 | Règles par contexte : profil connu, vue nominale, règles existantes | 18/18 | 100 % | oui |
| C-B11 | Rétrocompatibilité : chaîne principale (`fabriquer_generateur.py`) avec le nouveau `rg::vers_entites`, fichiers l2 et l2b | S03, S08 : 21/21 identiques ; S_M24 : 18/21, la différence venant de la boucle du refuge (angles) | identiques hors correction | oui |
| C-B12 | Déterminisme (B01, S_M24 ; second processus, sans rendu) | identique, 56 fichiers | identique | oui |

C-B9 donne aussi l'écart des contours de `bordures.json` (autre équipe, non modifiés) aux meshes du catalogue. Il va de
1,5 à 4,4 mm pour CS1, CS2, T1, T2, A1, A2 et CC2, et de 5,7 à 30 mm pour P1, CC1, T3, I1, I2, P3, CS3 et P2. Deux
sources divergent donc, et l'autre équipe doit trancher.

## 4. Reliquats du contrôle de l'étape 1 (`tmp/controle_route_seule.json`)

La correction interrompue (`tmp/second_controle/`) avait déjà traité presque tout. Je l'ai vérifiée, puis j'ai refait
les trois rues de Meylan avec le code final, en 2 vues. Elles avaient été rendues en passe 1, avant les dernières
modifications de `rg::vers_entites`, `pj::caniveau` 2.1 et `fabriquer_l2`. S01 à S12 avaient été refaites en passe 2 avec
le code final : seule la vérification de déterminisme de S12 avait été interrompue.

| Id | Reliquat | Mesure | Seuil | Atteint |
|---|---|---|---|---|
| R1 | Passages de Meylan : BEV et bandes de passage | BEV 1 760/1 760 dalles sur trottoir, chemin ou refuge ; bandes 23 334/23 334 faces sur chaussée, liaison revêtue ou piste | 0 exception | oui |
| R2 | Teinte de l'enrobé (dessus et conducteur ; S01, S02, S03, S05, S10, S12, Meylan, B01) | 26,7-36,0° sur les scènes de l'étape 1 et de Meylan ; B01 en vue conducteur : 37,5° | 26-37° | **non** (B01 en vue conducteur) |
| R3 | Bordures et caniveaux non bleutés (têtes, caniveaux, faces au soleil) | 27,3-36,0°, saturation ≥ 0,062 | 20-45°, ≥ 0,04 | oui |
| R4 | Piste plus sombre que la chaussée et non verdâtre (S05, S_M24, S_M27) | ΔY de −0,058 à −0,055 ; 25,7-30,0° | ΔY < 0 ; 20-45° | oui |
| R5 | Usure de l'enrobé variée par scène : corrélation au même (x, y) | max 0,135 (10 paires) | < 0,2 | oui |
| R6 | Avaloirs qui remplacent l'élément de caniveau (S03, S10) | 13 et 4 avaloirs, 0 recouvrement, 0 trou | 0 | oui |

Remarques :
- **R1.** M27 et M20 décrivent la traversée revêtue des bermes au droit du passage. Les abaissés et les BEV sont du côté
  piéton. Il ne reste aucune dalle dans la bande plantée.
- **R2.** La teinte vient d'une médiane sur une image 8 bits : 37,5° correspond à un écart d'une unité sur 255 au-dessus
  de 36°. Le dépassement de B01 (scène de démonstration, et non reliquat) est déclaré et le seuil n'est pas relevé. Toutes
  les scènes à reliquat sont dans la plage.
- **R3.** Les faces de bordure à l'ombre (côté nord) restent à 220-222°, saturation 0,18-0,30, luminance 0,12-0,17.
  Elles ne sont éclairées que par le ciel bleu, ce qui est physique. Je l'indique sans critère.

## 5. Écarts, limites, à trancher

1. **Entrée charretière.** Le compilateur pose la vue maximale de RF-MA-TRO-015 (0,05), alors que
   `bordures_elements.json` vise 0,02-0,04 (défaut 0,03). Le contexte `charretiere` du lot retient 0,03, ce qui satisfait
   les deux. Dans B01, la pièce T2_bateau est donc posée à 0,05, 1 cm au-dessus de sa vue nominale (`vue_max_bateau` =
   0,05 dans le pilote du lot). Il faudrait passer `ev_charretiere` à 0,03 (fichier partagé, non modifié).
2. **Couronne franchissable de giratoire.** A2 (RF-OSM-NIV-012 « rolled ») a une vue nominale de 0,04-0,10 et ne descend
   pas à 0,03 (RF-GV-GIR-006). J'ai retenu T2_surbaissee (0-0,04), un élément franchissable par les véhicules.
3. **Types sans pièce d'abaissé au catalogue.** T1, T4, granits, I et P sont posés abaissés avec leur propre contour
   ([G], RF-MA-ABA-002 respecté).
4. **P4.** Le catalogue ne l'offre qu'en 0,50 m. `elements.json` le note (« 2 éléments de 0,50 m du catalogue »), mais la
   pose de `pj::bordure` reste au pas de 1 m.
5. **Pièces d'angle.** Seules T1, T2 et T3 en ont au catalogue (angle sortant ou rentrant, jambes de 0,325 m). Ailleurs,
   on pose deux demi-éléments en onglet sur mesure.
6. **Faces à l'ombre bleutées** (R3, information) : à trancher si l'utilisateur veut une balance des blancs de type photo.
7. **Quais.** Leurs retours ont une vue variable, à cause des dévers différents du quai et du trottoir au niveau de la
   chaussée. Ils sont typés `raccord_vue` et posés sur mesure.

## 6. Déterminisme

`fabriquer_bordures.py --verifier-determinisme` a été lancé sur B01 et S_M24 (second processus, sans rendu) :
**identique** (56 fichiers l1, l2, l2b comparés ; `.usda` : chemins relatifs des matériaux normalisés ; log `tmp/bordures/determinisme.log`). Les images Karma ne sont pas comparées au pixel..

## 7. Pour l'intégration (ajouts rétrocompatibles, en mémoire dans mon pilote, à reporter dans les fichiers partagés)

- `description/vocabulaire.py` : `PROFILS_BORDURE.update(BC.MOTS_PROFILS)` et `CANIVEAUX.update(BC.MOTS_CANIVEAUX)`.
- `schema/modele_voie.schema.json` : énumérations `bordure.profil` et `caniveau.profil` étendues
  (`BC.enumerations_schema()`).
- `commun/profil.py` : repli de `bordure_entre` pour le profil « autre » (`BC.installer_description`, contextes ci-dessus).
- `hda/rg_nivellement/construire.py` : `table_profils()` sur `BC.construire_table_etendue()`. Sans cela, un profil
  ajouté est refusé (« profil de bordure inconnu »).
- `fabriquer_l2.py` :
  - `pj::bordure::2.1` et `pj::caniveau::2.2` à la place de 2.0 et 2.1 ;
  - paramètres `pieces_abaisse` (`BC.table_pieces_abaisse()`) et `vue_max_bateau` de `rg::vers_entites` ;
  - `asset_id` et `asset_motif` dans `elements.json` (`fabriquer_bordures.exporter_elements`).
- Les autres lots (giratoires, carrefours, autoroutes) peuvent appeler `BC.bordure_par_contexte("couronne_giratoire" |
  "ilot_central_giratoire" | "ilot" | "refuge" | "terre_plein_vru" | "autoroute" …)`.
