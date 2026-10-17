# Bibliothèque d'assets de la route française (`route_fr`) — étape 3 : élargissement

*Généré le 2026-10-17 par `recon/pcg/assets_route/ecrire_doc_etape3.py` à partir du catalogue versionné `assets/specs/route/catalogue_assets_route.json` (entrées `"etape": 3`). Complète `D:\DocRoute\14_Assets_Route_Statics\ASSETS_ROUTE.md` (étape 1, 120 meshes, non modifié). Toute cote renvoie à un document et une page ; « estimation » signale une valeur sans source.*

## 1. Résumé

- **168 nouveaux static meshes** fabriqués dans Houdini 22 (hython ; HDA `route::assemblage` et `route::panneau` créées pour cette étape, HDA `route::extrusion_profil`, `revolution`, `poteau`, `dalle`, `ossature` de l'étape 1), en USD (Z haut, m, variantes LOD0/1/2, UV en mètres `st`/`st1`, sous-ensembles par matériau) et FBX (un fichier par LOD) : bordures 40, supports 24, retenue 21, caniveaux 12, mobilier 11, balises 11, feux 9, ilots 9, eclairage 8, paves 6, assainissement 5, dalles 5, potelets 4, barrieres 3.
  Confiance des cotes : haute 36, moyenne 104, estimation 28.
- **600 panneaux montés sur plaques** (un USD par signal, jeu de variantes `gamme`, faces officielles des PNG du dossier 09 en texture à UV 0-1, revers, bord tombé, rails de fixation) ; 1644 variantes de gamme fabriquées (une plaque à la taille de chaque gamme IISR) ; échelle : haute 210, moyenne 216, estimation 174 (panneaux à dimensions variables D, E, H, SR).
- **27 ensembles** (compositions USD par références) : support + colliers + panneau(x) aux hauteurs de l'IISR, mâts + têtes de feux aux hauteurs relevées à Meylan.
- **21 matériaux PBR CC0 nouveaux** (enrobés 4K : BBTM, ESU, pelade, granulats clairs, rouge, ocre ; bétons désactivés, galets scellés, résine gravillonnée, gravillons, pavés, dalles, BRF, terres, bois, RAL 7024) et **fiche mesurée** (albédo moyen, rugosité, licence) pour les 77 matériaux de `route_fr` et du site : `recon/pcg/assets_route/fiches_materiaux_route.json`.
- **49 planches de rendu Karma XPU** (≤ 1092 px, regardées à la taille native) dans `D:\DocRoute\14_Assets_Route_Statics\controle\etape3\` ; constats et corrections au § 9.
- Catalogue : 120 entrées existantes **conservées à l'identique**, 795 ajoutées (écriture atomique) ; clés nouvelles `etape3`, sources et matériaux ajoutés sans retrait.

## 2. Construire comme un chantier : phases et continuité

Chaque asset porte `phase_chantier` (ordre de pose) et `pose` (pas de répétition, raccords, accroches, hauteurs). Le PCG fabrique la scène phase par phase, chaque phase s'appuyant sur la géométrie de la précédente (niveau fini, arêtes de bordure, axes des voies) — c'est ce qui évite les « bouts de segments » :

| phase | contenu | assets (familles) | ce que la phase fournit à la suivante |
|---|---|---|---|
| P01_reseaux | terrassement, réseaux enterrés, regards et chambres (corps sous chaussée) | — (les corps de regards sont portés par les affleurants P05) | positions des regards et chambres (sous chaussée et trottoir) |
| P02_bordures | bordures, caniveaux, éléments d'îlots et de giratoires préfabriqués (posés sur béton de calage) | assainissement 1, bordures 40, caniveaux 12, ilots 9 | arêtes vues des bordures (fil d'eau, nez) : limites des surfaces, abaissés, nez d'îlots |
| P03_chaussee | couches de chaussée et couche de roulement (enrobés, matériaux de surface) | matériaux de chaussée (§ 7) | niveau fini de la chaussée (couche de roulement) et son matériau |
| P04_trottoirs | revêtements des trottoirs, îlots, terre-pleins (béton, dalles, pavés, résine, galets, gravillons) | dalles 5, paves 6 | niveau fini des trottoirs, îlots, terre-pleins |
| P05_affleurants | mise à niveau des affleurants : tampons, grilles, bouches à clé, avaloirs | assainissement 4 | tampons, grilles, bouches à clé mis au niveau fini (dessus à Z = 0 de l'asset) |
| P06_retenue | dispositifs de retenue : GBA/DBA/MVL coulés en place, glissières, extrémités, atténuateurs | retenue 21 | files continues : modules au pas, extrémités, atténuateurs aux musoirs |
| P07_eclairage | candélabres et luminaires | eclairage 8 | candélabres au pas dans la bande technique |
| P08_signalisation | supports, panneaux, panonceaux, potences, portiques, balises | balises 4, supports 18, panneaux_montes 24, panneaux 600 | supports, panneaux et balises (hauteurs, dégagements IISR) |
| P09_feux | mâts, têtes de feux, répétiteurs, boîtiers d'appel, armoires | feux_montes 3, feux 9, supports 6 | mâts, têtes, répétiteurs, boîtiers (hauteurs [G] du dossier 09) |
| P10_marquage | marquage au sol et plots rétroréfléchissants J15a (dossier 08) | balises 5 | marquage (dossier 08), plots J15a, balises J11/J12 le long des lignes |
| P11_mobilier | potelets, barrières, arceaux, bancs, corbeilles, abris | mobilier 11, balises 2, barrieres 3, potelets 4 | potelets, barrières, arceaux, bancs, corbeilles, abris hors cheminement de 1,40 m |

Règles de continuité des éléments linéaires (champ `pose`) :

- **Modules au pas** : bordures et caniveaux 1,00 m (0,994 + joint 6 mm), courbes de 1 m mesurés sur la face (R 1,2 / 3 / 6 m), GBA/DBA/MVL/LBA en modules de 1 et 4 m sans joint (ouvrage coulé en place), glissières en modules de 4 m (lisse de 4,315 m, recouvrement 0,315 m modélisé par une éclisse en bout de module) ; le PCG pose les modules bout à bout le long de la courbe (pivot au milieu du module, face côté circulation vers −Y).
- **Débuts et fins de file** : `retenue_GBA/DBA_extremite_abaissee_L0165` (fin de file) et `_L2000` (origine), `retenue_glissiere_GS2/GS4_extremite_abaissee_L1200` (lisse abaissée et enterrée), atténuateurs `retenue_attenuateur_*` au nez des musoirs (Cerema, guide d'installation, § 4.1, p. 49-51).
- **Raccords de bordure** : rampants T2 → T2 basse / surbaissée (étape 1), T3 → T3 basse et T2 basse → T2 surbaissée (étape 3), pièces d'angle et courbes ; avaloir T2 à la place d'un élément de 1 m.
- **Accroches** : panneaux (rails à `pose.rails_z_m`, face à Y = rayon du poteau + 0,06 m) ; colliers `collier_panneau_D*` à la hauteur des rails ; têtes de feux sur mâts (azimut, hauteur du bas) ; potences et portique (console à 5,00 / 5,50 m).

### 2.1 Du vocabulaire des descriptions simples aux assets

Proposition au générateur (clé `etape3.correspondances_description` du catalogue) : les mots des descriptions simples (`recon/generateur/description/FORMAT_DESCRIPTION.md` § 5-10) et l'asset ou le matériau choisi par défaut (premier de la liste), les autres étant des variantes. Exemple : « route 2 × 2 voies avec terre-plein central végétalisé de 20 m » → bordures `bordure_I2_L100` et courbes I2 autour du terre-plein (P02), enrobé `enrobe_bbsg_use` (P03), terre `terre_vegetale` et plantations (P04 + végétation), candélabres `candelabre_routier_H100_double_crosse` dans le terre-plein (P07), balise J5 et `ensemble_B21_1_ilot` aux nez (P08).

| catégorie | mot | assets / matériaux |
|---|---|---|
| separateurs | glissière | `retenue_glissiere_GS2_module_L400`, `retenue_glissiere_GS4_module_L400`, `retenue_glissiere_GS2_extremite_abaissee_L1200` |
| separateurs | glissière double / DE2 | `retenue_glissiere_DE2_module_L400` |
| separateurs | GBA | `retenue_GBA_L400`, `retenue_GBA_L100`, `retenue_GBA_extremite_abaissee_L0165`, `retenue_GBA_extremite_abaissee_L2000` |
| separateurs | DBA | `retenue_DBA_L400`, `retenue_DBA_L100`, `retenue_DBA_extremite_abaissee_L0165`, `retenue_DBA_extremite_abaissee_L2000` |
| separateurs | muret | `retenue_MVL_L400`, `retenue_MVL_L100` |
| separateurs | atténuateur / musoir | `retenue_attenuateur_P80`, `retenue_attenuateur_P50`, `retenue_attenuateur_M80`, `retenue_attenuateur_P110` |
| separateurs | potelets | `potelet_GAM_acier_D89_H120`, `potelet_GAM_memoire_forme_D90_H90`, `potelet_gorge_D102_H100` |
| separateurs | bornes | `borne_bois_GAM_150x150_H130`, `balise_borne_PU_D200_H66` |
| separateurs | balises | `balise_J11_H085`, `balise_J11_H070`, `balise_J11_H050`, `balise_quille_PU_D80_H100` |
| separateurs | plots | `balise_J15a_plot` |
| separateurs | barrières | `barriere_GAM_croix_st_andre_L120`, `barriere_GAM_croix_st_andre_L150`, `barriere_GAM_croix_st_andre_L080` |
| bordures | bordure granit | `bordure_GR_T2_L100`, `bordure_GR_A2_L100`, `bordure_GR_P3_L100`, `bordure_GR_T2_courbe_ext_R300` |
| bordures | giratoire franchissable | `giratoire_ariane_D1000_element`, `giratoire_franchissable_D400`, `giratoire_franchissable_D300` |
| bordures | îlot préfabriqué | `ilot_separateur_100x50x25`, `ilot_monobloc_120x60x13` |
| bordures | avaloir | `assainissement_avaloir_T2_bouche_egout` |
| materiaux | enrobé neuf | `enrobe_neuf` |
| materiaux | enrobé usé | `enrobe_bbsg_use` |
| materiaux | enrobé ancien | `enrobe_bbsg_ancien` |
| materiaux | BBTM | `enrobe_bbtm` |
| materiaux | enduit / gravillonné | `enrobe_esu_gravillonne` |
| materiaux | rapiécé | `enrobe_pelade_rapiece`, `enrobe_reprise` |
| materiaux | fissuré | `enrobe_fissure`, `enrobe_faience` |
| materiaux | granulats clairs | `enrobe_granulats_clairs` |
| materiaux | rouge | `enrobe_colore_rouge`, `resine_rouge` |
| materiaux | ocre | `enrobe_colore_ocre` |
| materiaux | béton désactivé | `beton_desactive`, `beton_desactive_moyen`, `beton_desactive_gros` |
| materiaux | béton balayé | `beton_balaye` |
| materiaux | résine | `resine_gravillonnee_beige`, `resine_rouge` |
| materiaux | galets | `galets_scelles`, `galets_roules` |
| materiaux | pavés | `paves_granit_carres`, `paves_beton_chevrons`, `paves_beton_rect` |
| materiaux | dalles | `dalles_beton_grises`, `dalles_beton_40`, `dalles_beton_ocre` |
| materiaux | dalles gazon | `dalles_beton_gazon` |
| materiaux | gravier / gravillons | `gravillons_roules_gris`, `gravillons_stabilises` |
| materiaux | BRF | `brf_copeaux_frais` |
| materiaux | terre | `terre_vegetale`, `terre_battue` |
| objets | candélabre (avenue, voie rapide) | `candelabre_routier_H100_simple_crosse`, `candelabre_routier_H100_double_crosse`, `candelabre_routier_H080_simple_crosse`, `candelabre_routier_H120_simple_crosse` |
| objets | candélabre (rue) | `candelabre_urbain_H050_top`, `candelabre_urbain_H060_crosse`, `candelabre_urbain_H040_top` |
| objets | abri bus | `abri_bus_L411`, `abri_bus_L340` |
| objets | arceaux | `arceau_velo_GAM_a_sceller`, `arceau_velo_GAM_a_cheviller` |
| objets | banc | `banc_lames_bois_L180_dossier`, `banc_lames_bois_L180_sans_dossier` |
| objets | corbeille | `corbeille_vigipirate_110L`, `corbeille_beton_60L` |
| objets | regard / tampon | `assainissement_regard_D600_cadre_rond_850`, `assainissement_regard_D600_cadre_carre_840` |
| objets | grille / avaloir | `assainissement_grille_plate_750x300_C250`, `assainissement_avaloir_T2_bouche_egout` |
| objets | bouche à clé | `assainissement_bouche_a_cle_trottoir` |
| signalisation | STOP | `ensemble_AB4_agglo`, `ensemble_AB4_campagne`, `panneau_AB4` |
| signalisation | cédez le passage | `ensemble_AB3a_agglo`, `ensemble_AB3a_campagne`, `panneau_AB3a` |
| signalisation | giratoire | `ensemble_AB25_agglo` |
| signalisation | sens interdit | `ensemble_B1_agglo` |
| signalisation | sens unique | `ensemble_C12_agglo` |
| signalisation | passage piéton (panneau) | `ensemble_C20a_agglo` |
| signalisation | limitation 30 / 50 | `ensemble_B14_30_agglo`, `ensemble_B14_50_agglo` |
| signalisation | nez d'îlot | `ensemble_J5_nez_ilot`, `ensemble_B21_1_ilot` |
| signalisation | feux (Meylan) | `ensemble_feux_meylan_mat_principal`, `ensemble_feux_meylan_ilot_axial` |
| signalisation | feux (générique) | `ensemble_feux_R11v_D200_mat_D90` |
| signalisation | potence / portique | `potence_signalisation_L600`, `portique_signalisation_L1600`, `potence_feux_L600` |

## 3. Où sont les fichiers

| Quoi | Chemin | Versionné |
|---|---|---|
| Table des cotes, sources, phases, descriptions de pièces | `recon/pcg/assets_route/specs_assets_etape3.py` | oui |
| HDA `route::assemblage`, `route::panneau` (format développé) | `recon/pcg/assets_route/hda/route_assemblage.hdalc, route_panneau.hdalc + construire_hda_etape3.py` | oui |
| Fabrication (assets, panneaux, ensembles, catalogue) | `recon/pcg/assets_route/fabriquer_assets_etape3.py` | oui |
| Contours des plaques relevés sur les faces | `recon/pcg/assets_route/signalisation/contours_faces_panneaux.py → assets/lib/route_fr/panneaux_3d/contours_faces.json` | script oui |
| Matériaux CC0 et fiches | `recon/pcg/assets_route/telecharger_materiaux_etape3.py, manifeste_materiaux_etape3.json, fiches_materiaux_route.json` | oui |
| Rendus de contrôle | `recon/pcg/assets_route/rendre_controle_etape3.py → D:/DocRoute/14_Assets_Route_Statics/controle/etape3/` | script oui |
| Scène maîtresse Houdini (une instance d'HDA par asset) | `recon/pcg/assets_route/assets_route_etape3.hiplc` | oui |
| Static meshes USD + FBX | `assets/lib/route_fr/meshes/<famille>/<id>/` | non |
| Panneaux (USD par signal + FBX gamme normale) | `assets/lib/route_fr/panneaux_3d/<famille_signal>/panneau_<code>/` | non |
| Ensembles (compositions USD) | `assets/lib/route_fr/meshes/ensembles/<id>/` | non |
| Sources téléchargées (fiches fabricants) | `assets/lib/route_fr/_sources_etape3/ (retenue, mobilier)` | non |
| Catalogue versionné | `assets/specs/route/catalogue_assets_route.json (entrées `etape: 3`, clé `etape3`)` | oui |

Régénérer : `python -P recon/pcg/assets_route/signalisation/contours_faces_panneaux.py` puis `hython recon/pcg/assets_route/fabriquer_assets_etape3.py` puis `hython recon/pcg/assets_route/rendre_controle_etape3.py` ; matériaux : `python recon/pcg/assets_route/telecharger_materiaux_etape3.py`. `fabriquer_assets_route.py` (étape 1) a été corrigé pour **conserver** les entrées de l'étape 3 et écrire le catalogue de façon atomique.

## 4. Conventions et HDA nouvelles

- **objets_au_sol** : pivot au pied, sol à Z = 0, face principale (feux, panneaux) vers +Y
- **lineaires** : X le long, face côté circulation vers −Y à Y = 0, modules centrés, longueur = pas
- **affleurants** : dessus à Z = 0 (niveau fini), corps sous le sol
- **panneaux** : face dans le plan Y = 0 vers +Y, pivot au milieu du bord inférieur de la plaque principale ; jeu de variantes USD « gamme »
- **ensembles** : compositions USD (références relatives) : support + colliers + panneaux, mât + têtes
- **`route::assemblage`** : un texte décrit des pièces cotées, une par ligne : `B` boîte (centre, tailles, rotation Z), `T` tube à rayon variable le long d'une polyligne (transport parallèle, onglets), `Q` profil (u, v) balayé le long d'une polyligne, `E` ellipsoïde, `F` face rectangulaire et `G` disque à UV 0-1 (décalques : tampons, grilles, vasques). Le wrangle VEX fabrique des pièces fermées orientées vers l'extérieur (normale contrôlée par la méthode de Newell), UV en mètres ; Fuse, Divide (polygones convexes, pour un import sûr dans Unreal), puis la chaîne commune de l'étape 1 (normales à angle de coupure, LOD PolyReduce).
- **`route::panneau`** : plaque(s) convexe(s) relevée(s) sur l'emprise opaque de la face officielle ; face avant à UV rapportées à l'image entière (une seule texture pour toutes les plaques d'un dessin : panneau + panonceau), bord tombé de 25 mm, rebord arrière de 12 mm, tôle de 2 mm, revers creux, 1 ou 2 rails de fixation (2 si la plaque dépasse 0,45 m). Vue de face, la gauche de l'image est en +X (corrigé après la 1re planche, § 9).

## 5. Static meshes de l'étape 3

### 5.1 Équipements de retenue (GBA, DBA, MVL, LBA, glissières, extrémités, atténuateurs) (21)

| id | type | dimensions (m) | matériau | sources des cotes | confiance | phase | tri LOD0/1/2 |
|---|---|---|---|---|---|---|---|
| `retenue_DBA_L100` | séparateur béton DBA coulé en place – module de 1 m | base 0.6, H 0.81, longueur 1 | beton_prefa_lisse | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) ; cerema_dr p. 31 | haute | P06 | 124/124/56 |
| `retenue_DBA_L400` | séparateur béton DBA coulé en place – module de 4 m | base 0.6, H 0.81, longueur 4 | beton_prefa_lisse | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) ; cerema_dr p. 31 | haute | P06 | 124/124/56 |
| `retenue_DBA_extremite_abaissee_L0165` | extrémité de DBA abaissée sur 1.65 m | base 0.6, H_debut 0.81, H_fin 0.04, longueur 1.65 | beton_prefa_lisse | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) ; cerema_dr p. 49 (§ 4.1.2.2-4.1.2.3, fig. 30-31) | moyenne | P06 | 508/508/184 |
| `retenue_DBA_extremite_abaissee_L2000` | extrémité de DBA abaissée sur 20 m | base 0.6, H_debut 0.81, H_fin 0.04, longueur 20 | beton_prefa_lisse | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) ; cerema_dr p. 51 (§ 4.1.2.2-4.1.2.3, fig. 30-31) | moyenne | P06 | 1532/1532/608 |
| `retenue_GBA_L100` | séparateur béton GBA coulé en place – module de 1 m | base 0.48, H 0.81, longueur 1 | beton_prefa_lisse | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) ; cerema_dr p. 31 | haute | P06 | 92/92/40 |
| `retenue_GBA_L400` | séparateur béton GBA coulé en place – module de 4 m | base 0.48, H 0.81, longueur 4 | beton_prefa_lisse | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) ; cerema_dr p. 31 | haute | P06 | 92/92/40 |
| `retenue_GBA_extremite_abaissee_L0165` | extrémité de GBA abaissée sur 1.65 m | base 0.48, H_debut 0.81, H_fin 0.04, longueur 1.65 | beton_prefa_lisse | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) ; cerema_dr p. 49 (§ 4.1.2.2-4.1.2.3, fig. 30-31) | moyenne | P06 | 380/380/138 |
| `retenue_GBA_extremite_abaissee_L2000` | extrémité de GBA abaissée sur 20 m | base 0.48, H_debut 0.81, H_fin 0.04, longueur 20 | beton_prefa_lisse | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) ; cerema_dr p. 51 (§ 4.1.2.2-4.1.2.3, fig. 30-31) | moyenne | P06 | 1148/1148/450 |
| `retenue_LBA_L100` | séparateur béton LBA coulé en place – module de 1 m | base 0.85, H 1.5, longueur 1 | beton_prefa_lisse | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) ; cerema_dr p. 31 | moyenne | P06 | 92/92/40 |
| `retenue_LBA_L400` | séparateur béton LBA coulé en place – module de 4 m | base 0.85, H 1.5, longueur 4 | beton_prefa_lisse | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) ; cerema_dr p. 31 | moyenne | P06 | 92/92/40 |
| `retenue_MVL_L100` | séparateur béton MVL coulé en place – module de 1 m | base 0.36, H 0.6, longueur 1 | beton_prefa_lisse | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) ; cerema_dr p. 31 | haute | P06 | 60/60/24 |
| `retenue_MVL_L400` | séparateur béton MVL coulé en place – module de 4 m | base 0.36, H 0.6, longueur 4 | beton_prefa_lisse | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) ; cerema_dr p. 31 | haute | P06 | 60/60/24 |
| `retenue_attenuateur_M80` | atténuateur de choc redirectif M80 | longueur 3.82, largeur 1.5, hauteur 0.82 | acier_galvanise | aximum_tau p. 2 | moyenne | P06 | 1908/954/380 |
| `retenue_attenuateur_P110` | atténuateur de choc redirectif P110 | longueur 4.82, largeur 0.85, hauteur 0.82 | acier_galvanise | aximum_tau p. 2 | moyenne | P06 | 2376/1188/474 |
| `retenue_attenuateur_P50` | atténuateur de choc redirectif P50 | longueur 1.9, largeur 0.85, hauteur 0.82 | acier_galvanise | aximum_tau p. 2 | moyenne | P06 | 972/486/194 |
| `retenue_attenuateur_P80` | atténuateur de choc redirectif P80 | longueur 3.82, largeur 0.85, hauteur 0.82 | acier_galvanise | aximum_tau p. 2 | moyenne | P06 | 1908/954/380 |
| `retenue_glissiere_DE2_module_L400` | glissière double DE2 (terre-plein central) – module de 4 m | longueur 4, hauteur_lisse 0.8, entretoise 0.636 | acier_galvanise | setra_bvl p. 30 (§ 3.3.4.3 a) ; aximum_de2 p. 2 | moyenne | P06 | 1000/500/200 |
| `retenue_glissiere_GS2_extremite_abaissee_L1200` | glissière GS2 – extrémité abaissée et enterrée sur 12 m | longueur 12, hauteur_depart 0.7 | acier_galvanise | setra_bvl p. 30 (§ 3.3.4.3 a) ; setra_bvl p. 73 (fig. 47) ; aximum_gs2 p. 2 | moyenne | P06 | 1168/584/232 |
| `retenue_glissiere_GS2_module_L400` | glissière métallique GS2 – module de 4 m (lisse + supports + écarteurs) | longueur 4, hauteur_lisse 0.7, entraxe_supports 2 | acier_galvanise | setra_bvl p. 30 (§ 3.3.4.3 a) ; setra_bvl p. 73 (fig. 47) ; aximum_gs2 p. 2 | moyenne | P06 | 528/264/104 |
| `retenue_glissiere_GS4_extremite_abaissee_L1200` | glissière GS4 – extrémité abaissée et enterrée sur 12 m | longueur 12, hauteur_depart 0.7 | acier_galvanise | setra_bvl p. 30 (§ 3.3.4.3 a) ; setra_bvl p. 73 (fig. 47) ; aximum_gs2 p. 2 | moyenne | P06 | 1032/516/206 |
| `retenue_glissiere_GS4_module_L400` | glissière métallique GS4 – module de 4 m (lisse + supports + écarteurs) | longueur 4, hauteur_lisse 0.7, entraxe_supports 4 | acier_galvanise | setra_bvl p. 30 (§ 3.3.4.3 a) ; setra_bvl p. 73 (fig. 47) ; aximum_gs2 p. 2 | moyenne | P06 | 460/230/92 |

### 5.2 Balises J et quilles (11)

| id | type | dimensions (m) | matériau | sources des cotes | confiance | phase | tri LOD0/1/2 |
|---|---|---|---|---|---|---|---|
| `balise_J1` | balise J1 | diametre 0.2, hauteur_hors_sol 1.3, bande 0.8 × 1 | blanc_balise | iisr1 p. 23 (art. 9-2 B) | haute | P08 | 188/94/37 |
| `balise_J11_H050` | balise J11 H050 | hauteur 0.5, largeur_apparente 0.15 | blanc_balise | iisr1 p. 26 (art. 9-2 I) | haute | P10 | 328/164/64 |
| `balise_J11_H070` | balise J11 H070 | hauteur 0.7, largeur_apparente 0.15 | blanc_balise | iisr1 p. 26 (art. 9-2 I) | haute | P10 | 328/164/65 |
| `balise_J11_H085` | balise J11 H085 | hauteur 0.85, largeur_apparente 0.2 | blanc_balise | iisr1 p. 26 (art. 9-2 I) | haute | P10 | 328/164/64 |
| `balise_J12_H085` | balise J12 H085 | hauteur 0.85, largeur_apparente 0.2 | vert_balise_J12 | iisr1 p. 27 (art. 9-2 J) | haute | P10 | 328/164/64 |
| `balise_J13` | balise J13 | hauteur_hors_sol 1.2, largeur 0.25 | blanc_balise | iisr1 p. 27 (art. 9-2 K) | moyenne | P08 | 48/24/16 |
| `balise_J15a_plot` | balise J15a plot | hauteur 0.018, emprise 0.1 × 0.1 | blanc_balise | iisr1 p. 29 (art. 9-2 N) | moyenne | P10 | 24/12/8 |
| `balise_J3` | balise J3 | diametre 0.2, hauteur_hors_sol 1.3 | blanc_balise | iisr1 p. 24 (art. 9-2 C) | haute | P08 | 188/94/37 |
| `balise_J6` | balise J6 | hauteur_hors_sol 1, largeur 0.15 | blanc_balise | iisr1 p. 25 (art. 9-2 F) | moyenne | P08 | 32/16/12 |
| `balise_borne_PU_D200_H66` | balise borne PU D200 H66 | diametre 0.2, hauteur 0.66 | blanc_balise | paris_rvc p. 66 (annexe 3) | moyenne | P11 | 646/322/129 |
| `balise_quille_PU_D80_H100` | balise quille PU D80 H100 | diametre 0.08, hauteur 1, embase 0.2 | blanc_balise | paris_rvc p. 66 (annexe 3) | moyenne | P11 | 216/108/42 |

### 5.3 Assainissement (grilles, regards, bouches à clé, avaloir) (5)

| id | type | dimensions (m) | matériau | sources des cotes | confiance | phase | tri LOD0/1/2 |
|---|---|---|---|---|---|---|---|
| `assainissement_avaloir_T2_bouche_egout` | assainissement avaloir T2 bouche egout | longueur 1, ouverture 0.69 × 0.165, plaque 0.8 × 0.6 | beton_bordure | alkern2026 p. 11 (T2 Avaloir (réf. 520159)) ; estimation | moyenne | P02 | 210/104/48 |
| `assainissement_bouche_a_cle_trottoir` | assainissement bouche a cle trottoir | tete_diametre 0.15, hauteur 0.16, tube_diametre 0.102 | fonte_noire | pam | moyenne | P05 | 174/87/34 |
| `assainissement_grille_plate_750x300_C250` | assainissement grille plate 750x300 C250 | cadre 0.776 × 0.345, ouverture 0.75 × 0.3, hauteur 0.041 | fonte_noire | pam | moyenne | P05 | 240/120/80 |
| `assainissement_regard_D600_cadre_carre_840` | assainissement regard D600 cadre carre 840 | cadre 0.84 × 0.84, hauteur 0.1 | fonte_noire | pam | moyenne | P05 | 58/29/10 |
| `assainissement_regard_D600_cadre_rond_850` | assainissement regard D600 cadre rond 850 | cadre_diametre 0.85, tampon_diametre 0.673, passage 0.61, hauteur 0.1 | fonte_noire | pam | moyenne | P05 | 328/163/64 |

### 5.4 Éclairage (candélabres routiers et urbains) (8)

| id | type | dimensions (m) | matériau | sources des cotes | confiance | phase | tri LOD0/1/2 |
|---|---|---|---|---|---|---|---|
| `candelabre_routier_H080_simple_crosse` | candélabre routier 8 m à simple crosse | hauteur_feu 8, diametre_pied 0.16, diametre_tete 0.076, saillie_crosse 1.5 | acier_galvanise | odyssee ; obs_isere ; estimation | estimation | P07 | 376/188/74 |
| `candelabre_routier_H100_double_crosse` | candélabre routier 10 m à double crosse | hauteur_feu 10, diametre_pied 0.176, diametre_tete 0.076, saillie_crosse 1.5 | acier_galvanise | odyssee ; obs_isere ; estimation | moyenne | P07 | 636/318/126 |
| `candelabre_routier_H100_simple_crosse` | candélabre routier 10 m à simple crosse | hauteur_feu 10, diametre_pied 0.176, diametre_tete 0.076, saillie_crosse 1.5 | acier_galvanise | odyssee ; obs_isere ; estimation | moyenne | P07 | 376/188/74 |
| `candelabre_routier_H120_simple_crosse` | candélabre routier 12 m à simple crosse | hauteur_feu 12, diametre_pied 0.19, diametre_tete 0.089, saillie_crosse 2 | acier_galvanise | odyssee ; obs_isere ; estimation | estimation | P07 | 376/188/74 |
| `candelabre_urbain_H040_top` | candélabre urbain 4 m (lanterne top) | hauteur 4, diametre_pied 0.12 | acier_thermolaque_7016 | odyssee ; angers_mob ; estimation | estimation | P07 | 612/306/120 |
| `candelabre_urbain_H050_top` | candélabre urbain 5 m (lanterne top) | hauteur 5, diametre_pied 0.13 | acier_thermolaque_7016 | odyssee ; angers_mob ; estimation | estimation | P07 | 612/306/122 |
| `candelabre_urbain_H060_crosse` | candélabre urbain 6 m (crosse et lanterne) | hauteur 6, diametre_pied 0.14 | acier_thermolaque_7016 | odyssee ; angers_mob ; estimation | estimation | P07 | 328/164/64 |
| `candelabre_urbain_H080_crosse` | candélabre urbain 8 m (crosse et lanterne) | hauteur 8, diametre_pied 0.16 | acier_thermolaque_7016 | odyssee ; angers_mob ; estimation | estimation | P07 | 328/164/64 |

### 5.5 Mobilier urbain (11)

| id | type | dimensions (m) | matériau | sources des cotes | confiance | phase | tri LOD0/1/2 |
|---|---|---|---|---|---|---|---|
| `abri_bus_L340` | abri bus L340 | longueur 3.4, profondeur 1.5, hauteur 2.38 | acier_thermolaque_7016 | estimation | moyenne | P11 | 144/72/48 |
| `abri_bus_L411` | abri bus L411 | longueur 4.11, profondeur 1.5, hauteur 2.38 | acier_thermolaque_7016 | angers_mob ; estimation | moyenne | P11 | 144/72/48 |
| `arceau_velo_GAM_a_cheviller` | arceau velo GAM a cheviller | largeur 0.6, hauteur 0.9 | acier_thermolaque_7024 | gam_f16 p. 4 ; estimation | moyenne | P11 | 500/250/100 |
| `arceau_velo_GAM_a_sceller` | arceau velo GAM a sceller | largeur 0.6, longueur_tube 1.15, hauteur_hors_sol 0.9 | acier_thermolaque_7024 | gam_f16 p. 4 ; estimation | moyenne | P11 | 476/238/94 |
| `arceau_velo_angers` | arceau velo angers | hauteur 1.2, largeur 0.46 | acier_thermolaque_7016 | angers_mob | haute | P11 | 740/370/148 |
| `banc_lames_bois_L180_dossier` | banc lames bois L180 dossier | longueur 1.8, profondeur 0.42, hauteur_assise 0.5, hauteur_dossier 0.52 | bois_brut_grise | angers_mob | haute | P11 | 164/82/56 |
| `banc_lames_bois_L180_sans_dossier` | banc lames bois L180 sans dossier | longueur 1.8, profondeur 0.42, hauteur_assise 0.49, hauteur_dossier_m 0 | bois_brut_grise | angers_mob | haute | P11 | 128/64/44 |
| `banc_lames_bois_L240_dossier` | banc lames bois L240 dossier | longueur 2.4, profondeur 0.42, hauteur_assise 0.5, hauteur_dossier 0.52 | bois_brut_grise | angers_mob | haute | P11 | 164/82/56 |
| `borne_fontaine_angers` | borne fontaine angers | hauteur_hors_sol 0.99 | acier_thermolaque_7016 | angers_mob | moyenne | P11 | 536/268/106 |
| `corbeille_beton_60L` | corbeille beton 60L | dimensions 0.5 × 0.5 × 0.75 | beton_prefa_lisse | angers_mob | haute | P11 | 36/18/12 |
| `corbeille_vigipirate_110L` | corbeille vigipirate 110L | diametre 0.47, hauteur 0.828 | acier_thermolaque_7016 | angers_mob | haute | P11 | 1384/691/276 |

### 5.6 Potelets et bornes (gamme Grenoble-Alpes Métropole) (4)

| id | type | dimensions (m) | matériau | sources des cotes | confiance | phase | tri LOD0/1/2 |
|---|---|---|---|---|---|---|---|
| `borne_bois_GAM_150x150_H130` | borne bois GAM 150x150 H130 | section 0.15 × 0.15, hauteur 1.3 | bois_brut_grise | gam_f16 p. 4 | haute | P11 | 236/118/46 |
| `potelet_GAM_acier_D89_H120` | potelet GAM acier D89 H120 | diametre 0.0889, hauteur_hors_sol 1.2 | acier_thermolaque_7024 | gam_f16 p. 4 ; arrete2007 | haute | P11 | 240/90/30 |
| `potelet_GAM_acier_D89_H140` | potelet GAM acier D89 H140 | diametre 0.0889, hauteur_hors_sol 1.4 | acier_thermolaque_7024 | gam_f16 p. 4 ; arrete2007 | haute | P11 | 240/90/28 |
| `potelet_GAM_memoire_forme_D90_H90` | potelet GAM memoire forme D90 H90 | diametre 0.09, hauteur_hors_sol 0.9 | acier_thermolaque_7024 | gam_f16 p. 4 | haute | P11 | 240/90/28 |

### 5.7 Barrières (3)

| id | type | dimensions (m) | matériau | sources des cotes | confiance | phase | tri LOD0/1/2 |
|---|---|---|---|---|---|---|---|
| `barriere_GAM_croix_st_andre_L080` | barriere GAM croix st andre L080 | longueur 0.8, hauteur 1.2 | acier_thermolaque_7024 | gam_f16 p. 4 | haute | P11 | 136/42/12 |
| `barriere_GAM_croix_st_andre_L120` | barriere GAM croix st andre L120 | longueur 1.2, hauteur 1.2 | acier_thermolaque_7024 | gam_f16 p. 4 | haute | P11 | 136/40/10 |
| `barriere_GAM_croix_st_andre_L150` | barriere GAM croix st andre L150 | longueur 1.5, hauteur 1.2 | acier_thermolaque_7024 | gam_f16 p. 4 | haute | P11 | 136/44/14 |

### 5.8 Feux (têtes du site, compléments) (9)

| id | type | dimensions (m) | matériau | sources des cotes | confiance | phase | tri LOD0/1/2 |
|---|---|---|---|---|---|---|---|
| `feu_R11j_meylan_pots` | feu R11j meylan pots | hauteur_tete 1.1 | plastique_gris_clair | iisr6 p. 5 ; feux_json | moyenne | P09 | 1038/519/207 |
| `feu_R11v_meylan_pots` | feu R11v meylan pots | hauteur_tete 1.1, pas_vertical 0.37, diametreodule 0.32, profondeur_avec_visiere 0.5, diametre_optique 0.2 | plastique_gris_clair | feux_json ; feux_doc | moyenne | P09 | 1038/519/207 |
| `feu_R12_meylan_boitier_horizontal` | feu R12 meylan boitier horizontal | largeur 0.33, hauteur 0.3, profondeur 0.18, casquette 0.12 | boitier_noir | feux_json ; iisr6 p. 5, art. 109-3 A | moyenne | P09 | 40/20/12 |
| `feu_R13c_meylan_pots` | feu R13c meylan pots | hauteur_tete 1.1, diametre_optique 0.2 | plastique_gris_clair | feux_json ; iisr6 p. 6 (fig. 3) | moyenne | P09 | 1038/519/207 |
| `feu_armoire_commande` | feu armoire commande | dimensions 0.8 × 0.35 × 1.54 | gris_armoire | obs_isere ; estimation | estimation | P09 | 60/30/20 |
| `feu_boitier_appel_pieton` | feu boitier appel pieton | largeur 0.12, hauteur 0.16, profondeur 0.1 | boitier_noir | feux_json ; feux_doc | moyenne | P09 | 114/57/22 |
| `feu_bras_court_L033` | feu bras court L033 | longueur 0.33, diametre 0.06 | acier_galvanise | feux_json ; estimation | moyenne | P09 | 120/60/23 |
| `feu_ecran_contraste_R11v_D200` | feu ecran contraste R11v D200 | largeur 0.56, hauteur 0.98 | noir_mat | iisr6 p. 11 ; estimation | estimation | P09 | 12/6/4 |
| `feu_repetiteur_R11v_meylan` | feu repetiteur R11v meylan | largeur 0.15, hauteur 0.5, profondeur 0.15, optique 0.09 | boitier_noir | feux_json ; iisr6 p. 35 | moyenne | P09 | 198/99/39 |

### 5.9 Supports : mâts, colliers, potences, portique (24)

| id | type | dimensions (m) | matériau | sources des cotes | confiance | phase | tri LOD0/1/2 |
|---|---|---|---|---|---|---|---|
| `collier_panneau_D048` | collier panneau D048 | diametre_poteau 0.0483, hauteur 0.04, saillie 0.06915 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; estimation | estimation | P08 | 148/73/28 |
| `collier_panneau_D060` | collier panneau D060 | diametre_poteau 0.0603, hauteur 0.04, saillie 0.07515 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; estimation | estimation | P08 | 148/74/28 |
| `collier_panneau_D076` | collier panneau D076 | diametre_poteau 0.076, hauteur 0.04, saillie 0.083 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; estimation | estimation | P08 | 148/74/28 |
| `collier_panneau_D089` | collier panneau D089 | diametre_poteau 0.089, hauteur 0.04, saillie 0.0895 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; estimation | estimation | P08 | 148/74/28 |
| `collier_panneau_D114` | collier panneau D114 | diametre_poteau 0.114, hauteur 0.04, saillie 0.102 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; estimation | estimation | P08 | 148/73/29 |
| `mat_feux_D114_H34` | mat feux D114 H34 | hauteur 3.4, diametre 0.114 | acier_galvanise | feux_json ; feux_doc | moyenne | P09 | 188/64/24 |
| `mat_feux_D114_H34_fourreau` | mat feux D114 H34 fourreau | hauteur 3.4, diametre 0.114 | acier_galvanise | feux_json | moyenne | P09 | 232/115/46 |
| `mat_feux_D114_H42` | mat feux D114 H42 | hauteur 4.2, diametre 0.114 | acier_galvanise | feux_json ; feux_doc | moyenne | P09 | 188/64/24 |
| `portique_signalisation_L1600` | portique signalisation L1600 | portee 16, hauteur_poutre 5.6 × 7.4, bas_panneau 5.5 | acier_galvanise | iisr1 p. 19, art. 9 c ; estimation | estimation | P08 | 1784/892/356 |
| `potence_feux_L400` | potence feux L400 | portee 4, hauteurat 6.2, diametreat 0.168 | acier_galvanise | feux_doc ; estimation | estimation | P09 | 584/292/116 |
| `potence_feux_L600` | potence feux L600 | portee 6, hauteurat 6.2, diametreat 0.168 | acier_galvanise | feux_doc ; estimation | estimation | P09 | 808/404/160 |
| `potence_feux_L800` | potence feux L800 | portee 8, hauteurat 6.2, diametreat 0.168 | acier_galvanise | feux_doc ; estimation | estimation | P09 | 1000/500/200 |
| `potence_signalisation_L600` | potence signalisation L600 | portee 6, bas_panneau 5, hauteur_panneauax 1.5, diametreat 0.219 | acier_galvanise | iisr1 p. 19, art. 9 c ; iisr4 ; estimation | estimation | P08 | 392/196/78 |
| `support_rond_D60_H18` | support rond D60 H1.8 (coupé à longueur pour un ensemble) | hauteur 1.8, d1 0.0603, d2 0.0603 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; arrete2007 ; angers_cpu | haute | P08 | 408/160/60 |
| `support_rond_D60_H29` | support rond D60 H2.9 (coupé à longueur pour un ensemble) | hauteur 2.9, d1 0.0603, d2 0.0603 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; arrete2007 ; angers_cpu | haute | P08 | 408/144/48 |
| `support_rond_D60_H31` | support rond D60 H3.1 (coupé à longueur pour un ensemble) | hauteur 3.1, d1 0.0603, d2 0.0603 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; arrete2007 ; angers_cpu | haute | P08 | 408/144/48 |
| `support_rond_D60_H32` | support rond D60 H3.2 (coupé à longueur pour un ensemble) | hauteur 3.2, d1 0.0603, d2 0.0603 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; arrete2007 ; angers_cpu | haute | P08 | 408/144/48 |
| `support_rond_D60_H33` | support rond D60 H3.3 (coupé à longueur pour un ensemble) | hauteur 3.3, d1 0.0603, d2 0.0603 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; arrete2007 ; iisr1 p. 19, art. 9 b | haute | P08 | 408/144/48 |
| `support_rond_D60_H34` | support rond D60 H3.4 (coupé à longueur pour un ensemble) | hauteur 3.4, d1 0.0603, d2 0.0603 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; arrete2007 ; iisr1 p. 19, art. 9 b | haute | P08 | 408/144/48 |
| `support_rond_D60_H40` | support rond D60 H40 | hauteur 4, d1 0.0603, d2 0.0603 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; arrete2007 ; iisr1 p. 19, art. 9 b | haute | P08 | 408/144/48 |
| `support_rond_D76_H19` | support rond D76 H1.9 (coupé à longueur pour un ensemble) | hauteur 1.9, d1 0.076, d2 0.076 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; arrete2007 ; iisr1 p. 19, art. 9 b | haute | P08 | 284/136/46 |
| `support_rond_D76_H21` | support rond D76 H2.1 (coupé à longueur pour un ensemble) | hauteur 2.1, d1 0.076, d2 0.076 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; arrete2007 ; iisr1 p. 19, art. 9 b | haute | P08 | 284/126/42 |
| `support_rond_D76_H40` | support rond D76 H40 | hauteur 4, d1 0.076, d2 0.076 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; arrete2007 ; iisr1 p. 19, art. 9 b | haute | P08 | 284/104/32 |
| `support_rond_D76_H45` | support rond D76 H45 | hauteur 4.5, d1 0.076, d2 0.076 | acier_galvanise | iisr1 p. 15, art. 6 B 1° ; arrete2007 ; iisr1 p. 19, art. 9 b | haute | P08 | 284/104/32 |

### 5.10 Bordures (courbes, granit, rampants) (40)

| id | type | dimensions (m) | matériau | sources des cotes | confiance | phase | tri LOD0/1/2 |
|---|---|---|---|---|---|---|---|
| `bordure_A2_courbe_ext_R120` | bordure A2 – courbe_ext | base 0.15, H 0.2, rayon_face 1.2, angle_deg 47.46 | beton_bordure | alkern2026 p. 15 (Bordure A2) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 256/116/42 |
| `bordure_A2_courbe_ext_R300` | bordure A2 – courbe_ext | base 0.15, H 0.2, rayon_face 3, angle_deg 18.984 | beton_bordure | alkern2026 p. 15 (Bordure A2) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 256/116/50 |
| `bordure_A2_courbe_ext_R600` | bordure A2 – courbe_ext | base 0.15, H 0.2, rayon_face 6, angle_deg 9.492 | beton_bordure | alkern2026 p. 15 (Bordure A2) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 256/116/42 |
| `bordure_A2_courbe_int_R120` | bordure A2 – courbe_int | base 0.15, H 0.2, rayon_face 1.2, angle_deg 47.46 | beton_bordure | alkern2026 p. 15 (Bordure A2) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 256/116/44 |
| `bordure_A2_courbe_int_R300` | bordure A2 – courbe_int | base 0.15, H 0.2, rayon_face 3, angle_deg 18.984 | beton_bordure | alkern2026 p. 15 (Bordure A2) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 256/116/42 |
| `bordure_A2_courbe_int_R600` | bordure A2 – courbe_int | base 0.15, H 0.2, rayon_face 6, angle_deg 9.492 | beton_bordure | alkern2026 p. 15 (Bordure A2) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 256/116/46 |
| `bordure_GR_A1_L050` | bordure GR_A1 – droit | base 0.2, H 0.25, longueur 0.494 | granit_gris_flamme | noblema ; alkern2026 p. 15 | moyenne | P02 | 56/16/4 |
| `bordure_GR_A1_L100` | bordure GR_A1 – droit | base 0.2, H 0.25, longueur 0.994 | granit_gris_flamme | noblema ; alkern2026 p. 15 | moyenne | P02 | 56/16/4 |
| `bordure_GR_A2_L050` | bordure GR_A2 – droit | base 0.15, H 0.2, longueur 0.494 | granit_gris_flamme | noblema ; alkern2026 p. 15 | moyenne | P02 | 56/16/4 |
| `bordure_GR_A2_L100` | bordure GR_A2 – droit | base 0.15, H 0.2, longueur 0.994 | granit_gris_flamme | noblema ; alkern2026 p. 15 | moyenne | P02 | 56/16/4 |
| `bordure_GR_P3_L050` | bordure GR_P3 – droit | base 0.06, H 0.2, longueur 0.494 | granit_gris_flamme | noblema ; alkern2026 p. 21 | moyenne | P02 | 44/12/4 |
| `bordure_GR_P3_L100` | bordure GR_P3 – droit | base 0.06, H 0.2, longueur 0.994 | granit_gris_flamme | noblema ; alkern2026 p. 21 | moyenne | P02 | 44/12/4 |
| `bordure_GR_T2_courbe_ext_R120` | bordure GR_T2 – courbe_ext | base 0.15, H 0.25, rayon_face 1.2, angle_deg 47.46 | granit_gris_flamme | angers_cpu ; bordures_elements.json | moyenne | P02 | 348/236/94 |
| `bordure_GR_T2_courbe_ext_R300` | bordure GR_T2 – courbe_ext | base 0.15, H 0.25, rayon_face 3, angle_deg 18.984 | granit_gris_flamme | angers_cpu ; bordures_elements.json | moyenne | P02 | 348/236/100 |
| `bordure_GR_T2_courbe_ext_R600` | bordure GR_T2 – courbe_ext | base 0.15, H 0.25, rayon_face 6, angle_deg 9.492 | granit_gris_flamme | angers_cpu ; bordures_elements.json | moyenne | P02 | 348/236/94 |
| `bordure_GR_T2_courbe_int_R120` | bordure GR_T2 – courbe_int | base 0.15, H 0.25, rayon_face 1.2, angle_deg 47.46 | granit_gris_flamme | angers_cpu ; bordures_elements.json | moyenne | P02 | 348/236/94 |
| `bordure_GR_T2_courbe_int_R300` | bordure GR_T2 – courbe_int | base 0.15, H 0.25, rayon_face 3, angle_deg 18.984 | granit_gris_flamme | angers_cpu ; bordures_elements.json | moyenne | P02 | 348/236/96 |
| `bordure_GR_T2_courbe_int_R600` | bordure GR_T2 – courbe_int | base 0.15, H 0.25, rayon_face 6, angle_deg 9.492 | granit_gris_flamme | angers_cpu ; bordures_elements.json | moyenne | P02 | 348/236/90 |
| `bordure_I2_courbe_ext_R120` | bordure I2 – courbe_ext | base 0.25, H 0.18, rayon_face 1.2, angle_deg 47.46 | beton_bordure | alkern2026 p. 28 (Bordure I2 100) ; celtys p. 3 ; fabemi_I2 p. 1 | moyenne | P02 | 476/308/142 |
| `bordure_I2_courbe_ext_R300` | bordure I2 – courbe_ext | base 0.25, H 0.18, rayon_face 3, angle_deg 18.984 | beton_bordure | alkern2026 p. 28 (Bordure I2 100) ; celtys p. 3 ; fabemi_I2 p. 1 | moyenne | P02 | 476/308/126 |
| `bordure_I2_courbe_ext_R600` | bordure I2 – courbe_ext | base 0.25, H 0.18, rayon_face 6, angle_deg 9.492 | beton_bordure | alkern2026 p. 28 (Bordure I2 100) ; celtys p. 3 ; fabemi_I2 p. 1 | moyenne | P02 | 476/308/110 |
| `bordure_I2_courbe_int_R120` | bordure I2 – courbe_int | base 0.25, H 0.18, rayon_face 1.2, angle_deg 47.46 | beton_bordure | alkern2026 p. 28 (Bordure I2 100) ; celtys p. 3 ; fabemi_I2 p. 1 | moyenne | P02 | 476/308/142 |
| `bordure_I2_courbe_int_R300` | bordure I2 – courbe_int | base 0.25, H 0.18, rayon_face 3, angle_deg 18.984 | beton_bordure | alkern2026 p. 28 (Bordure I2 100) ; celtys p. 3 ; fabemi_I2 p. 1 | moyenne | P02 | 476/308/120 |
| `bordure_I2_courbe_int_R600` | bordure I2 – courbe_int | base 0.25, H 0.18, rayon_face 6, angle_deg 9.492 | beton_bordure | alkern2026 p. 28 (Bordure I2 100) ; celtys p. 3 ; fabemi_I2 p. 1 | moyenne | P02 | 476/308/114 |
| `bordure_T1_courbe_ext_R120` | bordure T1 – courbe_ext | base 0.12, H 0.2, rayon_face 1.2, angle_deg 47.46 | beton_bordure | alkern2026 p. 9 (Bordure T1 (coupe cotée)) ; celtys p. 7 ; sepa_T p. 1 | moyenne | P02 | 452/284/122 |
| `bordure_T1_courbe_ext_R300` | bordure T1 – courbe_ext | base 0.12, H 0.2, rayon_face 3, angle_deg 18.984 | beton_bordure | alkern2026 p. 9 (Bordure T1 (coupe cotée)) ; celtys p. 7 ; sepa_T p. 1 | moyenne | P02 | 452/284/102 |
| `bordure_T1_courbe_ext_R600` | bordure T1 – courbe_ext | base 0.12, H 0.2, rayon_face 6, angle_deg 9.492 | beton_bordure | alkern2026 p. 9 (Bordure T1 (coupe cotée)) ; celtys p. 7 ; sepa_T p. 1 | moyenne | P02 | 452/284/110 |
| `bordure_T1_courbe_int_R120` | bordure T1 – courbe_int | base 0.12, H 0.2, rayon_face 1.2, angle_deg 47.46 | beton_bordure | alkern2026 p. 9 (Bordure T1 (coupe cotée)) ; celtys p. 7 ; sepa_T p. 1 | moyenne | P02 | 452/284/122 |
| `bordure_T1_courbe_int_R300` | bordure T1 – courbe_int | base 0.12, H 0.2, rayon_face 3, angle_deg 18.984 | beton_bordure | alkern2026 p. 9 (Bordure T1 (coupe cotée)) ; celtys p. 7 ; sepa_T p. 1 | moyenne | P02 | 452/284/104 |
| `bordure_T1_courbe_int_R600` | bordure T1 – courbe_int | base 0.12, H 0.2, rayon_face 6, angle_deg 9.492 | beton_bordure | alkern2026 p. 9 (Bordure T1 (coupe cotée)) ; celtys p. 7 ; sepa_T p. 1 | moyenne | P02 | 452/284/114 |
| `bordure_T3_courbe_ext_R120` | bordure T3 – courbe_ext | base 0.17, H 0.28, rayon_face 1.2, angle_deg 47.46 | beton_bordure | alkern2026 p. 12 (Bordure T3 (coupe cotée)) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 452/284/120 |
| `bordure_T3_courbe_ext_R300` | bordure T3 – courbe_ext | base 0.17, H 0.28, rayon_face 3, angle_deg 18.984 | beton_bordure | alkern2026 p. 12 (Bordure T3 (coupe cotée)) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 452/284/106 |
| `bordure_T3_courbe_ext_R600` | bordure T3 – courbe_ext | base 0.17, H 0.28, rayon_face 6, angle_deg 9.492 | beton_bordure | alkern2026 p. 12 (Bordure T3 (coupe cotée)) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 452/284/108 |
| `bordure_T3_courbe_int_R120` | bordure T3 – courbe_int | base 0.17, H 0.28, rayon_face 1.2, angle_deg 47.46 | beton_bordure | alkern2026 p. 12 (Bordure T3 (coupe cotée)) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 452/284/118 |
| `bordure_T3_courbe_int_R300` | bordure T3 – courbe_int | base 0.17, H 0.28, rayon_face 3, angle_deg 18.984 | beton_bordure | alkern2026 p. 12 (Bordure T3 (coupe cotée)) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 452/284/100 |
| `bordure_T3_courbe_int_R600` | bordure T3 – courbe_int | base 0.17, H 0.28, rayon_face 6, angle_deg 9.492 | beton_bordure | alkern2026 p. 12 (Bordure T3 (coupe cotée)) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 452/284/104 |
| `bordure_raccord_T2_basse_T2_surbaissee_droite` | raccord (rampant) T2_basse → T2_surbaissee (droite) | longueur 0.994, base 0.151, H 0.23, vue_debut 0.1, vue_fin 0.02 | beton_bordure | alkern2026 p. 11 (Raccord T2 basse / T2 surbaissee (1000 mm, droite et gauche)) ; arrete2007 | moyenne | P02 | 452/284/112 |
| `bordure_raccord_T2_basse_T2_surbaissee_gauche` | raccord (rampant) T2_basse → T2_surbaissee (gauche) | longueur 0.994, base 0.151, H 0.23, vue_debut 0.02, vue_fin 0.1 | beton_bordure | alkern2026 p. 11 (Raccord T2 basse / T2 surbaissee (1000 mm, droite et gauche)) ; arrete2007 | moyenne | P02 | 452/284/112 |
| `bordure_raccord_T3_T3_basse_droite` | raccord (rampant) T3 → T3_basse (droite) | longueur 0.994, base 0.17, H 0.28, vue_debut 0.18, vue_fin 0.12 | beton_bordure | alkern2026 p. 13 (Raccord T3 / T3 basse (1000 mm, droite et gauche)) ; arrete2007 | moyenne | P02 | 452/284/118 |
| `bordure_raccord_T3_T3_basse_gauche` | raccord (rampant) T3 → T3_basse (gauche) | longueur 0.994, base 0.17, H 0.28, vue_debut 0.12, vue_fin 0.18 | beton_bordure | alkern2026 p. 13 (Raccord T3 / T3 basse (1000 mm, droite et gauche)) ; arrete2007 | moyenne | P02 | 452/284/118 |

### 5.11 Caniveaux courbes (12)

| id | type | dimensions (m) | matériau | sources des cotes | confiance | phase | tri LOD0/1/2 |
|---|---|---|---|---|---|---|---|
| `bordure_CC1_courbe_ext_R120` | bordure CC1 – courbe_ext | base 0.4, H 0.12, rayon_face 1.2, angle_deg 47.46 | beton_bordure | alkern2026 p. 18 (CC1) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 336/164/56 |
| `bordure_CC1_courbe_ext_R300` | bordure CC1 – courbe_ext | base 0.4, H 0.12, rayon_face 3, angle_deg 18.984 | beton_bordure | alkern2026 p. 18 (CC1) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 336/164/64 |
| `bordure_CC1_courbe_ext_R600` | bordure CC1 – courbe_ext | base 0.4, H 0.12, rayon_face 6, angle_deg 9.492 | beton_bordure | alkern2026 p. 18 (CC1) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 336/164/66 |
| `bordure_CC1_courbe_int_R120` | bordure CC1 – courbe_int | base 0.4, H 0.12, rayon_face 1.2, angle_deg 47.46 | beton_bordure | alkern2026 p. 18 (CC1) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 336/164/60 |
| `bordure_CC1_courbe_int_R300` | bordure CC1 – courbe_int | base 0.4, H 0.12, rayon_face 3, angle_deg 18.984 | beton_bordure | alkern2026 p. 18 (CC1) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 336/164/60 |
| `bordure_CC1_courbe_int_R600` | bordure CC1 – courbe_int | base 0.4, H 0.12, rayon_face 6, angle_deg 9.492 | beton_bordure | alkern2026 p. 18 (CC1) ; celtys p. 7 ; bordures_elements.json | moyenne | P02 | 336/164/62 |
| `bordure_CS2_courbe_ext_R120` | bordure CS2 – courbe_ext | base 0.25, H 0.135, rayon_face 1.2, angle_deg 47.46 | beton_bordure | alkern2026 p. 17 (CS2) ; sepa_CS p. 1 ; bordures_elements.json | moyenne | P02 | 256/116/38 |
| `bordure_CS2_courbe_ext_R300` | bordure CS2 – courbe_ext | base 0.25, H 0.135, rayon_face 3, angle_deg 18.984 | beton_bordure | alkern2026 p. 17 (CS2) ; sepa_CS p. 1 ; bordures_elements.json | moyenne | P02 | 256/116/40 |
| `bordure_CS2_courbe_ext_R600` | bordure CS2 – courbe_ext | base 0.25, H 0.135, rayon_face 6, angle_deg 9.492 | beton_bordure | alkern2026 p. 17 (CS2) ; sepa_CS p. 1 ; bordures_elements.json | moyenne | P02 | 256/116/42 |
| `bordure_CS2_courbe_int_R120` | bordure CS2 – courbe_int | base 0.25, H 0.135, rayon_face 1.2, angle_deg 47.46 | beton_bordure | alkern2026 p. 17 (CS2) ; sepa_CS p. 1 ; bordures_elements.json | moyenne | P02 | 256/116/36 |
| `bordure_CS2_courbe_int_R300` | bordure CS2 – courbe_int | base 0.25, H 0.135, rayon_face 3, angle_deg 18.984 | beton_bordure | alkern2026 p. 17 (CS2) ; sepa_CS p. 1 ; bordures_elements.json | moyenne | P02 | 256/116/40 |
| `bordure_CS2_courbe_int_R600` | bordure CS2 – courbe_int | base 0.25, H 0.135, rayon_face 6, angle_deg 9.492 | beton_bordure | alkern2026 p. 17 (CS2) ; sepa_CS p. 1 ; bordures_elements.json | moyenne | P02 | 256/116/42 |

### 5.12 Îlots et giratoires préfabriqués (9)

| id | type | dimensions (m) | matériau | sources des cotes | confiance | phase | tri LOD0/1/2 |
|---|---|---|---|---|---|---|---|
| `giratoire_ariane_D0600_element` | bordure franchissable de giratoire Ariane – élément pour Ø 6 m | diametre_ext 6, nb_elements 19, angle_deg 18.947, largeur 0.6, hauteur 0.3 | beton_prefa_lisse | alkern2026 p. 51 (Giratoire Ariane) ; estimation | moyenne | P02 | 372/220/102 |
| `giratoire_ariane_D1000_element` | bordure franchissable de giratoire Ariane – élément pour Ø 10 m | diametre_ext 10, nb_elements 29, angle_deg 12.414, largeur 0.6, hauteur 0.3 | beton_prefa_lisse | alkern2026 p. 51 (Giratoire Ariane) ; estimation | moyenne | P02 | 372/220/84 |
| `giratoire_ariane_D1600_element` | bordure franchissable de giratoire Ariane – élément pour Ø 16 m | diametre_ext 16, nb_elements 44, angle_deg 8.182, largeur 0.6, hauteur 0.3 | beton_prefa_lisse | alkern2026 p. 51 (Giratoire Ariane) ; estimation | moyenne | P02 | 372/220/96 |
| `giratoire_franchissable_D300` | giratoire franchissable D300 | diametre 3, hauteur 0.14 | beton_prefa_lisse | alkern2026 p. 52 | moyenne | P02 | 512/238/74 |
| `giratoire_franchissable_D400` | giratoire franchissable D400 | diametre 4, hauteur 0.23 | beton_prefa_lisse | alkern2026 p. 53 | moyenne | P02 | 384/150/52 |
| `ilot_monobloc_120x60x13` | ilot monobloc 120x60x13 | longueur 1.2, largeur 0.6, hauteur 0.13 | beton_prefa_lisse | alkern2026 p. 50 | moyenne | P02 | 44/22/8 |
| `ilot_monobloc_120x60x18` | ilot monobloc 120x60x18 | longueur 1.2, largeur 0.6, hauteur 0.18 | beton_prefa_lisse | alkern2026 p. 50 | moyenne | P02 | 44/24/8 |
| `ilot_separateur_100x50x25` | ilot separateur 100x50x25 | longueur 1, largeur 0.5, hauteur 0.25 | beton_prefa_lisse | alkern2026 p. 49 | moyenne | P02 | 44/22/8 |
| `ilot_separateur_60x60x25_arrondi` | ilot separateur 60x60x25 arrondi | longueur 0.6, largeur 0.6, hauteur 0.25 | beton_prefa_lisse | alkern2026 p. 49 | moyenne | P02 | 44/24/8 |

### 5.13 Dalles (5)

| id | type | dimensions (m) | matériau | sources des cotes | confiance | phase | tri LOD0/1/2 |
|---|---|---|---|---|---|---|---|
| `dalle_beton_300x300x50` | dalle beton 300x300x50 | longueur 0.3, largeur 0.3, epaisseur 0.05 | beton_prefa_lisse | estimation | estimation | P04 | 44/22/8 |
| `dalle_beton_400x400x50` | dalle beton 400x400x50 | longueur 0.4, largeur 0.4, epaisseur 0.05 | beton_prefa_lisse | estimation | estimation | P04 | 44/22/8 |
| `dalle_beton_500x500x60` | dalle beton 500x500x60 | longueur 0.5, largeur 0.5, epaisseur 0.06 | beton_prefa_lisse | estimation | estimation | P04 | 44/22/8 |
| `dalle_granit_600x400x80` | dalle granit 600x400x80 | longueur 0.6, largeur 0.4, epaisseur 0.08 | granit_gris_flamme | estimation | estimation | P04 | 44/22/8 |
| `dalle_reperage_porte_bus_600x600` | dalle reperage porte bus 600x600 | longueur 0.6, largeur 0.6, epaisseur 0.06 | beton_prefa_lisse | estimation | moyenne | P04 | 44/22/8 |

### 5.14 Pavés et galets (6)

| id | type | dimensions (m) | matériau | sources des cotes | confiance | phase | tri LOD0/1/2 |
|---|---|---|---|---|---|---|---|
| `galet_couronne_120` | galet couronne 120 | longueur 0.13, largeur 0.1, hauteur 0.07 | galets_roules | estimation | estimation | P04 | 168/84/32 |
| `galet_couronne_60` | galet couronne 60 | longueur 0.07, largeur 0.056, hauteur 0.04 | galets_roules | estimation | estimation | P04 | 168/84/32 |
| `galet_couronne_90` | galet couronne 90 | longueur 0.1, largeur 0.08, hauteur 0.056 | galets_roules | estimation | estimation | P04 | 168/84/32 |
| `pave_beton_200x200x80` | pave beton 200x200x80 | longueur 0.2, largeur 0.2, epaisseur 0.08 | beton_prefa_lisse | estimation | estimation | P04 | 44/24/8 |
| `pave_granit_100x100x100` | pave granit 100x100x100 | longueur 0.1, largeur 0.1, epaisseur 0.1 | granit_gris_flamme | estimation | estimation | P04 | 44/22/8 |
| `pave_granit_200x100x100_scie` | pave granit 200x100x100 scie | longueur 0.2, largeur 0.1, epaisseur 0.1 | granit_gris_flamme | angers_cpu ; estimation | estimation | P04 | 44/24/6 |

Lecture des profils et pièces nouvelles (cotes en mm) :

| asset | lecture du document | source |
|---|---|---|
| `retenue_DBA_L100` | profil symétrique : talons 9 cm, faces à 36° sur 25 cm (r = 25 cm), 72 cm au-dessus du talon, sommet 15 cm, base 60 cm | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) |
| `retenue_DBA_L400` | profil symétrique : talons 9 cm, faces à 36° sur 25 cm (r = 25 cm), 72 cm au-dessus du talon, sommet 15 cm, base 60 cm | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) |
| `retenue_DBA_extremite_abaissee_L0165` | rampant linéaire du profil plein vers un profil réduit à 4 cm (forme exacte non cotée) | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) |
| `retenue_DBA_extremite_abaissee_L2000` | rampant linéaire du profil plein vers un profil réduit à 4 cm (forme exacte non cotée) | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) |
| `retenue_GBA_L100` | talon 9 cm vertical ; face à 36° de la verticale sur 25 cm (cassure en congé r = 25 cm) ; face haute jusqu'à 72 cm au-dessus du talon ; sommet 15 cm ; base 48 cm ; dos incliné de 6° | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) |
| `retenue_GBA_L400` | talon 9 cm vertical ; face à 36° de la verticale sur 25 cm (cassure en congé r = 25 cm) ; face haute jusqu'à 72 cm au-dessus du talon ; sommet 15 cm ; base 48 cm ; dos incliné de 6° | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) |
| `retenue_GBA_extremite_abaissee_L0165` | rampant linéaire du profil plein vers un profil réduit à 4 cm (forme exacte non cotée) | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) |
| `retenue_GBA_extremite_abaissee_L2000` | rampant linéaire du profil plein vers un profil réduit à 4 cm (forme exacte non cotée) | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) |
| `retenue_LBA_L100` | talon 15 cm ; 36° sur 25 cm (r = 25) ; 135 cm au-dessus du talon ; sommet 20 cm ; base 85 cm ; pentes de la face haute (6°) et du dos déduites de la base et du sommet (non cotées) | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) |
| `retenue_LBA_L400` | talon 15 cm ; 36° sur 25 cm (r = 25) ; 135 cm au-dessus du talon ; sommet 20 cm ; base 85 cm ; pentes de la face haute (6°) et du dos déduites de la base et du sommet (non cotées) | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) |
| `retenue_MVL_L100` | muret trapézoïdal : hauteur hors sol 60 cm, base 36 cm, sommet 24 cm | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) |
| `retenue_MVL_L400` | muret trapézoïdal : hauteur hors sol 60 cm, base 36 cm, sommet 24 cm | cerema_dr p. 32 (Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)) |
| `retenue_attenuateur_M80` | forme générique (cartouches et panneaux latéraux télescopiques) aux dimensions hors tout de la fiche ; décor de chevrons du nez en couleur moyenne | aximum_tau p. 2 |
| `retenue_attenuateur_P110` | forme générique (cartouches et panneaux latéraux télescopiques) aux dimensions hors tout de la fiche ; décor de chevrons du nez en couleur moyenne | aximum_tau p. 2 |
| `retenue_attenuateur_P50` | forme générique (cartouches et panneaux latéraux télescopiques) aux dimensions hors tout de la fiche ; décor de chevrons du nez en couleur moyenne | aximum_tau p. 2 |
| `retenue_attenuateur_P80` | forme générique (cartouches et panneaux latéraux télescopiques) aux dimensions hors tout de la fiche ; décor de chevrons du nez en couleur moyenne | aximum_tau p. 2 |
| `retenue_glissiere_DE2_module_L400` | section de la lisse profil A : 312 × 83 × 3 mm ESTIMÉE (profil européen courant à 2 ondes ; profil B : 296 × 2,5 mm d'après une fiche Hellopro) ; écarteurs 70 × 150 × 200 et C100 100 × 50 × 5 estimés | setra_bvl p. 30 (§ 3.3.4.3 a) |
| `retenue_glissiere_GS2_extremite_abaissee_L1200` | section de la lisse profil A : 312 × 83 × 3 mm ESTIMÉE (profil européen courant à 2 ondes ; profil B : 296 × 2,5 mm d'après une fiche Hellopro) ; écarteurs 70 × 150 × 200 et C100 100 × 50 × 5 estimés ; abaissement linéaire jusqu'à −5 cm (enterrée) | setra_bvl p. 30 (§ 3.3.4.3 a) |
| `retenue_glissiere_GS2_module_L400` | section de la lisse profil A : 312 × 83 × 3 mm ESTIMÉE (profil européen courant à 2 ondes ; profil B : 296 × 2,5 mm d'après une fiche Hellopro) ; écarteurs 70 × 150 × 200 et C100 100 × 50 × 5 estimés | setra_bvl p. 30 (§ 3.3.4.3 a) |
| `retenue_glissiere_GS4_extremite_abaissee_L1200` | section de la lisse profil A : 312 × 83 × 3 mm ESTIMÉE (profil européen courant à 2 ondes ; profil B : 296 × 2,5 mm d'après une fiche Hellopro) ; écarteurs 70 × 150 × 200 et C100 100 × 50 × 5 estimés ; abaissement linéaire jusqu'à −5 cm (enterrée) | setra_bvl p. 30 (§ 3.3.4.3 a) |
| `retenue_glissiere_GS4_module_L400` | section de la lisse profil A : 312 × 83 × 3 mm ESTIMÉE (profil européen courant à 2 ondes ; profil B : 296 × 2,5 mm d'après une fiche Hellopro) ; écarteurs 70 × 150 × 200 et C100 100 × 50 × 5 estimés | setra_bvl p. 30 (§ 3.3.4.3 a) |

## 6. Panneaux sur plaques (signalisation verticale)

Méthode (`contours_faces_panneaux.py`) : pour chacun des 600 signaux « plaques » des 870 faces (les symboles, idéogrammes, feux, balises cylindriques et panneaux temporaires K hors triangles AK sont exclus), le masque d'opacité est découpé en composantes connexes (plaques), les supports dessinés sont écartés, les plaques jointives à un poteau dessiné sont séparées par une ouverture morphologique horizontale ; l'enveloppe convexe de chaque plaque est simplifiée à 0,8 px. 8 exemples de composition à plaques jointives (illustrations) ne sont pas fabriqués.

Échelle (m par pixel) à la gamme normale :

| règle | nombre de signaux |
|---|---|
| cadre du dessin PDF × 4.99 (échelle des dessins Cerema, gamme normale) | 204 |
| dimensions variables | 174 |
| carré, gamme normale 700 mm de côté | 126 |
| disque, gamme normale 850 mm (largeur de la plaque) | 86 |
| dimensions spécifiques IISR 1 art. 5-3 | 9 |
| octogone, gamme normale 800 mm entre côtés opposés | 1 |

Contrôle : l'échelle des dessins du Cerema (cadre du PDF × 4,99) redonne la gamme normale à ± 0,1 % pour les disques (850), l'octogone AB4 (800), les carrés (700) et les triangles (925 mm de largeur pour 1000 de côté à angles arrondis). Écarts > 3 % (confiance ramenée à « moyenne ») :

- `C14_ex1` : +99.7 % — dimensions spécifiques IISR 1 art. 5-3 : 900 × 1300 mm (largeur de la plaque) ; le dessin du Cerema est à une autre échelle (+100 %)
- `C14_ex2` : +99.7 % — dimensions spécifiques IISR 1 art. 5-3 : 900 × 1300 mm (largeur de la plaque) ; le dessin du Cerema est à une autre échelle (+100 %)
- `C14_ex3` : +99.7 % — dimensions spécifiques IISR 1 art. 5-3 : 900 × 1300 mm (largeur de la plaque) ; le dessin du Cerema est à une autre échelle (+100 %)
- `C14_ex4` : +99.7 % — dimensions spécifiques IISR 1 art. 5-3 : 900 × 1300 mm (largeur de la plaque) ; le dessin du Cerema est à une autre échelle (+100 %)
- `C25a` : +300.0 % — dimensions spécifiques IISR 1 art. 5-3 : 1600 × 2400 mm (largeur de la plaque) ; le dessin du Cerema est à une autre échelle (+300 %)
- `C25b` : +300.0 % — dimensions spécifiques IISR 1 art. 5-3 : 1600 × 2400 mm (largeur de la plaque) ; le dessin du Cerema est à une autre échelle (+300 %)
- `C64b` : +98.7 % — carré, gamme normale 700 mm de côté ; le dessin du Cerema est à une autre échelle (+99 %)
- `C64c2` : +33.1 % — carré, gamme normale 700 mm de côté ; le dessin du Cerema est à une autre échelle (+33 %)
- `CE22` : -8.4 % — carré, gamme normale 700 mm de côté ; le dessin du Cerema est à une autre échelle (-8 %)
- `CE6a` : +24.8 % — carré, gamme normale 700 mm de côté ; le dessin du Cerema est à une autre échelle (+25 %)
- `CE9` : +33.0 % — carré, gamme normale 700 mm de côté ; le dessin du Cerema est à une autre échelle (+33 %)
- `SC8_19` : +11.7 % — carré, gamme normale 700 mm de côté ; le dessin du Cerema est à une autre échelle (+12 %)

| famille de signaux | panneaux | gammes fabriquées | exemple (taille normale, m) |
|---|---|---|---|
| danger_A | 30 | miniature, petite, normale, grande, tres_grande | `panneau_A13a` 0.925 × 0.815 |
| indication_C | 74 | miniature, petite, normale, grande, tres_grande | `panneau_C107` 0.7 × 0.7 |
| intersection_priorite_AB | 9 | miniature, petite, normale, grande, tres_grande | `panneau_AB1` 0.925 × 0.815 |
| localisation_E_EB | 46 | normale | `panneau_E31a` 2.015 × 2.977 |
| panonceau_M | 125 | normale | `panneau_M10A` 0.703 × 0.202 |
| passage_niveau_G_balises_J | 25 | normale | `panneau_G1` 0.577 × 0.377 |
| prescription_B | 108 | miniature, petite, normale, grande, tres_grande | `panneau_B0` 0.85 × 0.85 |
| reperage_direction_D | 103 | normale | `panneau_D31B_ex1` 0.833 × 0.532 |
| securite_routiere_SR | 14 | normale | `panneau_SR2` 0.292 × 1.004 |
| services_CE | 45 | miniature, petite, normale, grande, tres_grande | `panneau_CE1` 0.7 × 0.7 |
| temporaire_K | 10 | miniature, petite, normale, grande, tres_grande | `panneau_AK14` 0.925 × 0.815 |
| touristique_H | 11 | normale | `panneau_H11` 0.74 × 0.25 |

Gammes (IISR 1 art. 5-3, p. 10) : triangle 500 / 700 / 1000 / 1250 / 1500 ; disque 450 / 650 / 850 / 1050 / 1250 ; octogone 400 / 600 / 800 / 1000 / 1200 ; carré 350 / 500 / 700 / 900 / 1050 (exceptionnelle et supérieure non fabriquées, réservées aux C et CE de présignalisation). Les plaques des panneaux à dimensions variables (D, E/EB, H, SR) sont à l'échelle « hauteur minimale de 250 mm » : à redimensionner selon le texte réel (le PNG garde les proportions du dessin).

### 6.1 Ensembles

| id | composants | bas (m) | haut (m) | sources |
|---|---|---|---|---|
| `ensemble_A13a_campagne` | support_rond_D76_H19 + panneau_A13a (normale) | 1.0 | 1.815 | iisr1 p. 19, art. 9 a |
| `ensemble_A13b_agglo` | support_rond_D60_H30 + panneau_A13b (petite) | 2.3 | 2.871 | iisr1 p. 19, art. 9 b |
| `ensemble_AB25_agglo` | support_rond_D60_H32 + panneau_AB25 (normale) | 2.3 | 3.115 | iisr1 p. 19, art. 9 b |
| `ensemble_AB2_campagne` | support_rond_D76_H19 + panneau_AB2 (normale) | 1.0 | 1.815 | iisr1 p. 19, art. 9 a |
| `ensemble_AB3a_agglo` | support_rond_D60_H34 + panneau_AB3a (normale) | 2.3 | 3.315 | iisr1 p. 19, art. 9 b ; iisr1 p. 16, art. 6 |
| `ensemble_AB3a_campagne` | support_rond_D76_H21 + panneau_AB3a (normale) | 1.0 | 2.015 | iisr1 p. 19, art. 9 a ; iisr1 p. 16, art. 6 |
| `ensemble_AB4_agglo` | support_rond_D60_H32 + panneau_AB4 (normale) | 2.3 | 3.101 | iisr1 p. 19, art. 9 b ; iisr1 p. 16, art. 6 |
| `ensemble_AB4_campagne` | support_rond_D76_H19 + panneau_AB4 (normale) | 1.0 | 1.801 | iisr1 p. 19, art. 9 a ; iisr1 p. 16, art. 6 |
| `ensemble_AB6_agglo` | support_rond_D60_H34 + panneau_AB6 (normale) | 2.3 | 3.256 | iisr1 p. 19, art. 9 b |
| `ensemble_B14_30_agglo` | support_rond_D60_H30 + panneau_B14_30 (petite) | 2.3 | 2.949 | iisr1 p. 19, art. 9 b |
| `ensemble_B14_50_agglo` | support_rond_D60_H32 + panneau_B14_50 (normale) | 2.3 | 3.149 | iisr1 p. 19, art. 9 b |
| `ensemble_B14_70_campagne` | support_rond_D76_H19 + panneau_B14_70 (normale) | 1.0 | 1.849 | iisr1 p. 19, art. 9 a |
| `ensemble_B14_90_campagne` | support_rond_D76_H19 + panneau_B14_90 (normale) | 1.0 | 1.849 | iisr1 p. 19, art. 9 a |
| `ensemble_B1_agglo` | support_rond_D60_H32 + panneau_B1 (normale) | 2.3 | 3.15 | iisr1 p. 19, art. 9 b |
| `ensemble_B21_1_ilot` | support_rond_D60_H18 + panneau_B21_t_1 (petite) | 1.0 | 1.65 | iisr1 p. 19 |
| `ensemble_B22a_agglo` | support_rond_D60_H31 + panneau_B22a (petite) | 2.3 | 2.95 | iisr1 p. 19, art. 9 b |
| `ensemble_B2a_agglo` | support_rond_D60_H31 + panneau_B2a (petite) | 2.3 | 2.95 | iisr1 p. 19, art. 9 b |
| `ensemble_B6a1_M6h_agglo` | support_rond_D60_H33 + panneau_M6h (normale) + panneau_B6a1 (petite) | 2.3 | 3.154 | iisr1 p. 19, art. 9 b ; iisr1 p. 19, art. 9-1 A |
| `ensemble_B6a1_agglo` | support_rond_D60_H31 + panneau_B6a1 (petite) | 2.3 | 2.95 | iisr1 p. 19, art. 9 b |
| `ensemble_C12_agglo` | support_rond_D60_H29 + panneau_C12 (petite) | 2.3 | 2.8 | iisr1 p. 19, art. 9 b |
| `ensemble_C13a_agglo` | support_rond_D60_H29 + panneau_C13a (petite) | 2.3 | 2.8 | iisr1 p. 19, art. 9 b |
| `ensemble_C1a_agglo` | support_rond_D60_H29 + panneau_C1a (petite) | 2.3 | 2.8 | iisr1 p. 19, art. 9 b |
| `ensemble_C20a_agglo` | support_rond_D60_H29 + panneau_C20a (petite) | 2.3 | 2.8 | iisr1 p. 19, art. 9 b |
| `ensemble_J5_nez_ilot` | support_rond_D60_H18 + panneau_J5 (normale) | 1.0 | 1.701 | iisr1 p. 25 (art. 9-2 E) |
| `ensemble_feux_R11v_D200_mat_D90` | mat_feux_D90_H34 + feu_R11v_D200 + feu_bras_court_L033 + feu_repetiteur_R11v_D90 + feu_bras_court_L033 |  |  | feux_doc |
| `ensemble_feux_meylan_ilot_axial` | mat_feux_D114_H42 + feu_R11v_meylan_pots + feu_bras_court_L033 + feu_repetiteur_R11v_meylan + feu_bras_court_L033 |  |  | feux_json |
| `ensemble_feux_meylan_mat_principal` | mat_feux_D114_H34_fourreau + feu_R11v_meylan_pots + feu_bras_court_L033 + feu_repetiteur_R11v_meylan + feu_bras_court_L033 + feu_R12_meylan_boitier_horizontal + feu_bras_court_L033 + feu_boitier_appel_pieton + feu_bras_court_L033 |  |  | feux_json ; feux_doc |

## 7. Matériaux PBR CC0 nouveaux (fiches mesurées)

Licence de toutes les sources : CC0 1.0 (ambientCG https://docs.ambientcg.com/license/ ; Poly Haven https://polyhaven.com/license). Choix : vignettes des sources puis recadrages NATIFS 340 × 340 px des albédos 1K des candidats retenus (planches de travail hors dépôt). Albédo et rugosité mesurés sur les cartes livrées (pas 4).

| nom | source | rés. | tuile (m) | albédo moyen linéaire (sRGB 8 bits) | rugosité moy. ± σ | usage | choix |
|---|---|---|---|---|---|---|---|
| `acier_thermolaque_7024` | ambientCG Metal027 | 2K | 1.0 (estimé (grain de poudre fin)) | 0.064, 0.069, 0.083 (71, 74, 82) | 0.649 ± 0.033 | Acier thermolaqué gris graphite RAL 7024 (gamme de Grenoble-Alpes Métropole : potelets, barrières, arceaux) | même source que acier_thermolaque_7016, moyenne ramenée sur RAL 7024 (GAM fiche n° 16 p. 4 : potelets, barrières, arceaux en RAL 7024) |
| `beton_desactive_gros` | Poly Haven gravel_concrete_02 | 2K | 2.1 (API Poly Haven « dimensions » (mm)) | 0.262, 0.202, 0.142 (140, 124, 105) | 0.769 ± 0.009 | Béton désactivé à gros granulats roulés (6/14) affleurants, teinte brun-gris | recadrage natif : granulats roulés de 5-15 mm serrés (béton désactivé grossier) ; distinct de beton_desactive (granulats fins) et de beton_bordure |
| `beton_desactive_moyen` | Poly Haven gravel_embedded_concrete | 2K | 2.0 (API Poly Haven « dimensions » (mm)) | 0.313, 0.286, 0.242 (152, 146, 135) | 0.732 ± 0.022 | Béton désactivé gris à granulats moyens (4/10), trottoirs et parvis | recadrage natif : granulats gris serrés, matrice grise ; intermédiaire entre beton_desactive et beton_desactive_gros |
| `bois_brut_grise` | Poly Haven rough_wood | 2K | 0.5 (API Poly Haven « dimensions » (mm)) | 0.154, 0.130, 0.102 (109, 101, 90) | 0.509 ± 0.027 | Bois brut grisé (mélèze, chêne vieilli) : bornes bois, lames de bancs, rondins | vignettes : seul bois d'extérieur grisé sans joints de lames (convient aux éléments unitaires) |
| `brf_copeaux_frais` | ambientCG WoodChips003 | 2K | 1.6 (API ambientCG dimensionX (cm)) | 0.392, 0.255, 0.140 (168, 138, 105) | 0.594 ± 0.081 | Bois raméal fragmenté frais / copeaux clairs (paillage de massifs et de pieds d'arbres) | vignettes : copeaux clairs fins ; WoodChips002 (vu en recadrage natif, plus grossier) écarté car son albédo n'est pas carré (2048 × 1024) ; complète brf_bois_concasse et brf_bois_gris du site (vieillis) |
| `dalles_beton_gazon` | Poly Haven grass_concrete_pavement | 2K | 1.97 (API Poly Haven « dimensions » (mm)) | 0.390, 0.313, 0.227 (168, 152, 131) | 0.73 ± 0.022 | Dalles béton-gazon (alvéoles engazonnées) : stationnements, accotements stabilisés | recadrage natif : plots béton carrés réguliers et herbe sèche dans les alvéoles |
| `dalles_beton_ocre` | Poly Haven concrete_pavers_02 | 2K | 2.0 (API Poly Haven « dimensions » (mm)) | 0.171, 0.119, 0.082 (115, 97, 81) | 0.874 ± 0.014 | Dalles béton rectangulaires ocre-brun à joints larges | recadrage natif : dalles rectangulaires teintées, joints marqués |
| `enrobe_bbtm` | ambientCG Asphalt027A | 4K | 2.0 (estimé : granulats de 3 à 6 px sur l'alb) | 0.070, 0.068, 0.060 (75, 74, 70) | 0.663 ± 0.048 | Béton bitumineux très mince (BBTM 0/6-0/10) : enrobé sombre à macrotexture ouverte, granulats serrés | recadrage natif : grain grossier régulier, sombre et ouvert, sans fissure ni marquage ; Asphalt010 (bleuté, fin) et ph asphalt_01 (brun) rejetés |
| `enrobe_colore_ocre` | ambientCG Asphalt020S | 4K | 1.85 (API ambientCG dimensionX (cm)) | 0.364, 0.292, 0.231 (163, 147, 132) | 0.644 ± 0.081 | Enrobé ou résine ocre (îlots, trottoirs, plateaux) à grain fin | enrobé gris fin à gravillons épars ramené sur la teinte ocre MESURÉE au site (îlots de la Revirée) ; version 4K du matériau du site (2K) |
| `enrobe_colore_rouge` | ambientCG Asphalt029B | 4K | 2.0 (estimé (aucune dimension publiée par la ) | 0.330, 0.090, 0.066 (155, 85, 73) | 0.653 ± 0.041 | Enrobé coloré rouge (liant pigmenté oxyde de fer) : couloirs bus, pistes cyclables, plateaux | seul enrobé rouge homogène de la source (Asphalt029A sert déjà à resine_rouge) ; rouge vif de la source ramené vers un rouge brique |
| `enrobe_esu_gravillonne` | Poly Haven tarred_gravel | 4K | 2.2 (API Poly Haven « dimensions » (mm)) | 0.053, 0.047, 0.038 (65, 61, 55) | 0.86 ± 0.083 | Enduit superficiel d'usure (ESU, gravillonnage) : liant noir et gravillons clairs épars (routes secondaires, accotements revêtus) | seul candidat montrant des gravillons clairs isolés sur liant noir (aspect d'un enduit bicouche usé) |
| `enrobe_granulats_clairs` | ambientCG Asphalt023S | 4K | 1.25 (API ambientCG dimensionX (cm)) | 0.208, 0.205, 0.176 (126, 125, 117) | 0.69 ± 0.042 | BBSG à granulats clairs (gris moyen, gravillons blancs épars) : enrobé récent à granulats calcaires | recadrage natif : gris neutre, gravillons clairs nets de 2-8 mm ; complète enrobe_clair_granulats (site, 2K, source pebble_cemented_floor recolorée) |
| `enrobe_pelade_rapiece` | ambientCG Asphalt019 | 4K | 2.0 (estimé (aucune dimension publiée par la ) | 0.049, 0.048, 0.047 (62, 62, 61) | 0.756 ± 0.082 | Enrobé ancien sombre avec plage de pelade (arrachement de la couche de roulement, granulats clairs à nu) : chaussée rapiécée ou dégradée | recadrage natif : enrobé noir lisse et une plage arrachée claire à bord franc ; les « Road0xx » rapiécés portent des marquages américains |
| `galets_scelles` | Poly Haven rock_embedded_concrete | 2K | 2.0 (API Poly Haven « dimensions » (mm)) | 0.174, 0.136, 0.085 (116, 103, 82) | 0.893 ± 0.072 | Galets roulés 5-8 cm scellés au mortier (pavage en galets, couronnes et nez d'îlots, caniveaux pavés) | recadrage natif : galets ovales jointifs dans un mortier gris (« calade ») ; seul candidat à galets scellés |
| `gravillons_roules_gris` | ambientCG Gravel041 | 2K | 0.6 (estimé : gravillons 8/16 (≈ 12 mm) de 15) | 0.285, 0.274, 0.195 (145, 143, 122) | 0.475 ± 0.082 | Gravillons roulés gris-vert 8/16 en couche (îlots minéraux, noues) | recadrage natif : gravillons roulés jointifs gris-vert (alluvions alpines) ; complète gravillons_ilot du site |
| `gravillons_stabilises` | Poly Haven floor_pebbles_01 | 2K | 3.0 (API Poly Haven « dimensions » (mm)) | 0.316, 0.256, 0.165 (152, 138, 113) | 0.897 ± 0.103 | Gravillons roulés sur sable stabilisé (allées, accotements, pieds d'arbres) | recadrage natif : gravillons roulés épars sur matrice sableuse |
| `paves_beton_chevrons` | Poly Haven herringbone_pavement_03 | 2K | 2.4 (API Poly Haven « dimensions » (mm)) | 0.058, 0.045, 0.033 (68, 60, 51) | 0.867 ± 0.033 | Pavés béton gris foncé 20 × 10 en chevrons (voies piétonnes, plateaux) | recadrage natif : pavés rectangulaires gris anthracite à joints fins, appareillage en chevrons |
| `paves_granit_carres` | Poly Haven cobblestone_square | 2K | 1.0 (API Poly Haven « dimensions » (mm)) | 0.238, 0.207, 0.149 (134, 126, 108) | 0.827 ± 0.153 | Pavés de granit gris carrés (≈ 9 cm : 90 px sur l'albédo 1K d'une tuile de 1,0 m) clivés, joints sablés et moussus | recadrage natif : pavés gris clivés à arêtes émoussées, joints larges (anneaux et couronnes de giratoire) |
| `resine_gravillonnee_beige` | Poly Haven pebble_cemented_floor | 2K | 1.56 (API Poly Haven « dimensions » (mm)) | 0.476, 0.387, 0.290 (184, 167, 147) | 0.725 ± 0.045 | Gravillons liés à la résine (sol drainant beige), trottoirs, pieds d'arbres, îlots | petits gravillons jointifs liés (aspect d'un sol en gravillons-résine) ; même source que enrobe_clair_granulats du site mais recolorée en beige |
| `terre_battue` | Poly Haven dirt_floor | 2K | 2.07 (API Poly Haven « dimensions » (mm)) | 0.475, 0.265, 0.131 (183, 141, 101) | 0.92 ± 0.012 | Terre battue compactée brun clair (chemins, accotements non revêtus) | recadrage natif : terre sèche compactée, débris fins |
| `terre_vegetale` | ambientCG Ground048 | 2K | 1.4 (API ambientCG dimensionX (cm)) | 0.114, 0.062, 0.042 (95, 70, 58) | 0.669 ± 0.048 | Terre végétale sombre humifère (massifs, fosses d'arbres, chantier) | recadrage natif : terre brun foncé à débris organiques |

Fiches des autres matériaux (`route_fr` étape 1 et site, non modifiés) :

| nom | bibliothèque | albédo moyen linéaire | rugosité moyenne | tuile (m) |
|---|---|---|---|---|
| `acier_galvanise` | route_fr | 0.566, 0.619, 0.702 | 0.456 | 1.0 |
| `acier_thermolaque_7016` | route_fr | 0.041, 0.048, 0.055 | 0.649 | 1.0 |
| `beton_balaye` | route_fr | 0.141, 0.114, 0.089 | 0.972 | 2.001 |
| `beton_desactive` | route_fr | 0.157, 0.136, 0.103 | 0.754 | 2.4 |
| `beton_prefa_lisse` | route_fr | 0.242, 0.242, 0.242 | 0.487 | 1.0 |
| `dalles_beton_40` | route_fr | 0.364, 0.313, 0.175 | 0.502 | 1.6 |
| `dalles_beton_grises` | route_fr | 0.139, 0.126, 0.110 | 0.939 | 1.825 |
| `dalles_beton_joint_gravier` | route_fr | 0.210, 0.196, 0.162 | 0.879 | 3.0 |
| `enrobe_bbsg_ancien` | route_fr | 0.284, 0.293, 0.272 | 0.524 | 2.0 |
| `enrobe_bbsg_use` | route_fr | 0.182, 0.184, 0.189 | 0.528 | 1.6 |
| `enrobe_faience` | route_fr | 0.122, 0.122, 0.112 | 0.689 | 1.85 |
| `enrobe_fissure` | route_fr | 0.119, 0.117, 0.105 | 0.77 | 3.0 |
| `enrobe_grenaille` | route_fr | 0.392, 0.353, 0.274 | 0.612 | 2.2 |
| `enrobe_neuf` | route_fr | 0.061, 0.063, 0.064 | 0.66 | 2.1 |
| `enrobe_neuf_frais` | route_fr | 0.019, 0.015, 0.014 | 0.831 | 2.0 |
| `enrobe_reprise` | route_fr | 0.060, 0.049, 0.039 | 0.832 | 2.0 |
| `galets_roules` | route_fr | 0.231, 0.163, 0.099 | 0.812 | 2.001 |
| `granit_gris_flamme` | route_fr | 0.492, 0.471, 0.446 | 0.607 | 1.0 |
| `inox_brosse` | route_fr | 0.292, 0.297, 0.315 | 0.47 | 0.5 |
| `paves_beton_autobloquant` | route_fr | 0.254, 0.254, 0.231 | 0.529 | 2.0 |
| `paves_beton_rect` | route_fr | 0.215, 0.232, 0.217 | 0.7 | 0.82 |
| `paves_granit_anciens` | route_fr | 0.281, 0.273, 0.247 | 0.517 | 1.15 |
| `paves_mosaique` | route_fr | 0.127, 0.105, 0.080 | 0.957 | 2.02 |
| `paves_pierre_scies` | route_fr | 0.152, 0.127, 0.100 | 0.944 | 2.5 |
| `peinture_routiere` | route_fr |  | None | 4.0 |
| `plastique_noir_feux` | route_fr | 0.028, 0.026, 0.036 | 0.649 | 1.0 |
| `resine_rouge` | route_fr | 0.505, 0.061, 0.058 | 0.691 | 2.0 |
| `beton_bordure` | site | 0.368, 0.383, 0.350 | 0.608 | 2.0 |
| `beton_galets` | site | 0.204, 0.207, 0.185 | 0.893 | 2.0 |
| `bev_podotactile` | site | 0.416, 0.430, 0.390 | 0.514 | 1.2 |
| `brf_bois_concasse` | site | 0.073, 0.059, 0.048 | 0.594 | 1.6 |
| `brf_bois_gris` | site | 0.261, 0.235, 0.204 | 0.586 | 1.8 |
| `calcaire_bordure` | site | 0.462, 0.431, 0.362 | 0.696 | 1.2 |
| `decal_grille_avaloir` | site | 0.228, 0.225, 0.220 | 0.576 | 0.65 |
| `decal_tampon_fonte` | site | 0.167, 0.132, 0.125 | 0.514 | 0.8 |
| `decal_tampon_fonte_carre` | site | 0.177, 0.167, 0.203 | 0.524 | 0.8 |
| `enrobe_bbsg_ancien` | site | 0.279, 0.287, 0.266 | 0.524 | 2.0 |
| `enrobe_bbsg_neuf` | site | 0.138, 0.143, 0.137 | 0.745 | 2.5 |
| `enrobe_clair_granulats` | site | 0.462, 0.444, 0.386 | 0.725 | 1.56 |
| `enrobe_colore_ocre` | site | 0.364, 0.290, 0.230 | 0.853 | 4.04 |
| `enrobe_piste_cyclable` | site | 0.197, 0.208, 0.182 | 0.527 | 2.0 |
| `enrobe_reprise_tranchee` | site | 0.190, 0.195, 0.178 | 0.781 | 2.0 |
| `enrobe_trottoir` | site | 0.211, 0.215, 0.189 | 0.861 | 2.2 |
| `gazon_sec` | site | 0.306, 0.239, 0.144 | 0.808 | 2.0 |
| `gazon_tondu` | site | 0.043, 0.094, 0.021 | 0.263 | 1.4 |
| `gravier_concasse_6_10` | site | 0.337, 0.338, 0.317 | 0.473 | 2.0 |
| `gravillons_ilot` | site | 0.332, 0.334, 0.315 | 0.453 | 1.9 |
| `herbe_haute` | site | 0.140, 0.208, 0.065 | 0.936 | 2.0 |
| `noue_plantee` | site | 0.077, 0.109, 0.055 | 0.684 | 2.0 |
| `overlay_feuilles_mortes` | site | 0.299, 0.163, 0.049 | 0.68 | 1.7 |
| `paillage_mineral` | site | 0.139, 0.151, 0.114 | 0.768 | 2.0 |
| `paves_granit` | site | 0.449, 0.440, 0.382 | 0.546 | 1.15 |
| `resine_cyan` | site | 0.312, 0.347, 0.332 | 0.594 | 2.5 |
| `resine_verte` | site | 0.259, 0.314, 0.267 | 0.594 | 2.5 |
| `stabilise_beige` | site | 0.256, 0.234, 0.183 | 0.871 | 2.1 |
| `terre_nue` | site | 0.130, 0.117, 0.083 | 0.527 | 1.3 |

## 8. Sources de l'étape 3

| clé | document | fichier ou URL | statut |
|---|---|---|---|
| `cerema_dr` | Cerema, « Dispositifs de retenue en section courante – Guide d'installation » | D:/DocRoute/10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/sources/Cerema_Guide_Dispositifs_Retenue_Routiers.pdf | guide technique public (droits réservés : cotes citées seulement) ; reprend NF P98-426 |
| `setra_bvl` | Setra, « Barrières de sécurité pour la retenue des véhicules légers » (niveau N, TPC), 2001 | D:/DocRoute/10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/sources/SETRA_Barrieres_VL_Niveau_N_TPC_2001.pdf | guide technique public |
| `aximum_gs2` | Aximum, fiche « Glissière métal simple file GS2 » (04/2022) | D:/ClaudeCode_RoadCreation/assets/lib/route_fr/_sources_etape3/retenue/glissiere-metal-simple-file-gs2.pdf | fiche fabricant publique |
| `aximum_gs4p` | Aximum, fiche « GS4+ » (04/2022) | D:/ClaudeCode_RoadCreation/assets/lib/route_fr/_sources_etape3/retenue/gs4-plus.pdf | fiche fabricant publique |
| `aximum_de2` | Aximum, fiche « DE2+R4 glissière métal double file » | D:/ClaudeCode_RoadCreation/assets/lib/route_fr/_sources_etape3/retenue/glissiere-metal-double-file-de2-plus-r4.pdf.pdf | fiche fabricant publique |
| `aximum_tau` | Aximum, fiches « Tau Tube P50 », « Tau Tube 80 » et plaquette « Atténuateurs de choc » (2025) | D:/ClaudeCode_RoadCreation/assets/lib/route_fr/_sources_etape3/retenue/attenuateur-choc-tau-tube-80.pdf | fiches fabricant publiques |
| `pam` | Saint-Gobain PAM (pamline.com) : regard PAMREX 600 D400 cadre rond (CDPA60EF, 20/10/2025), grille plate à cadre C250 750 × 300 (ECML30ZF), bouche à clé TOTALE trottoir | https://www.pamline.com/fr-fr/ | fiches fabricant publiques ; cotes relevées dans les résultats de recherche du 17/10/2026 (PDF non téléchargés) : confiance moyenne |
| `angers_mob` | Ville d'Angers, Cahier de prescriptions urbaines, fiches produit (banc lames de bois, corbeilles béton et Vigipirate, abribus, abri tramway, arceau vélo, lanternes) | D:/ClaudeCode_RoadCreation/assets/lib/route_fr/_sources_etape3/mobilier/fiche-arceau.pdf | document public de collectivité |
| `gam_f16` | Grenoble-Alpes Métropole, Guide métropolitain des espaces publics et de la voirie, fiche n° 16 « Pour un meilleur partage de l'espace public : les nouveaux réflexes », p. 4 | D:/ClaudeCode_RoadCreation/data/raw/docs_web/grenoblealpesmetropole/ | document public de collectivité (Meylan est dans le périmètre GAM) |
| `paris_rvc` | Ville de Paris, référentiel aménagements cyclables (1re partie), annexe 3 p. 66 : fiche fabricant reproduite (balise PU Ø 80, borne Ø 200) |  | cité par DocRoute 11 CYCLES.md § 10 (RF-MA-SEP-011) |
| `odyssee` | Odyssée Lumière Export, mâts d'éclairage aluminium 3-6 m (Ø base 120-140) et 9,3-12,8 m (Ø base 176, crosse cintrée 1,5-2,5 m, embout Ø 60, semelle 400 entraxe 300) — fiches Hellopro | https://www.hellopro.fr/mat-d-eclairage-public-hauteur-9-3-12-8-m-en-aluminium-diametre-base-176-mm-2008383-5819902-produit.html | fiches fabricant publiques (pages web) |
| `obs_isere` | DocRoute 13, OBSERVATIONS_ISERE.md (Panoramax) : OBS-ECL-01 candélabres simple ou double crosse 8-11 m ; DBA de 2,6 m en voie rapide ; armoires de commande | D:/DocRoute/13_Observations_Panoramax_Isere/OBSERVATIONS_ISERE.md | observation |
| `feux_doc` | DocRoute 09, FEUX_IMPLANTATION.md § 7 et § 12 (hauteurs [G]/[M], tête R11v de Meylan) | D:/DocRoute/09_Signalisation_Verticale_Feux/FEUX_IMPLANTATION.md | synthèse sourcée |
| `panneaux_cat` | assets/specs/route/panneaux_fr_catalogue.json : 870 faces officielles (Cerema, PDF détourés) ; gammes IISR 1re partie art. 5-3 p. 10 ; panonceaux art. 9-1 D p. 22 ; échelle des dessins 1:4,99 | D:/ClaudeCode_RoadCreation/assets/specs/route/panneaux_fr_catalogue.json | catalogue du dépôt |
| `iisr4` | IISR 4e partie (prescription), art. 61 : hauteurs libres < 4,30 m à signaler | D:/DocRoute/01_IISR_Signalisation_Officielle/IISR_4e_Partie_Prescription_20220613.pdf | texte réglementaire |
| `estimation` | estimation |  | aucune source : valeur de pratique à vérifier |

Sources de l'étape 1 réutilisées : IISR 1re partie (art. 5-3, 6, 8, 9, 9-1, 9-2, 10), IISR 6e partie, Alkern 2026 (p. 11, 15, 21, 49-53), Angers CPU, Noblema, arrêté du 15/01/2007, `assets/specs/feux.json` (relevés de Meylan).

Pages web consultées le 17/10/2026 (cotes relevées, rien de copié) : fiches Aximum GS2, GS4+, DE2+R4, Tau Tube P50/80 et plaquette atténuateurs (aximum.com, PDF dans `_sources_etape3/retenue`) ; Ville d'Angers, CPU : banc-banquette-lames-de-bois, corbeille-proprete-beton, corbeille-proprete-vigipirate, abribus, abri-tramway, arceaux-velos (fiche-arceau.pdf), borne-fontaine, lanternes ; Hellopro : mâts Odyssée Lumière 3-6 m et 9,3-12,8 m ; résultats de recherche pamline.com (PAMREX 600, grille ECML30ZF, bouche à clé TOTALE) ; API ambientCG et Poly Haven (textures CC0).

## 9. Contrôles

### 9.1 Planches de rendu (Karma XPU, exposition fixe, ≤ 1092 px, regardées à la taille native)

| planche | assets | fichier | constat |
|---|---|---|---|
| retenue_beton | 6 | `controle/etape3/e3_retenue_beton.png` | GBA (talon, face à 36° puis quasi verticale, dos à 6°), DBA symétrique, MVL trapézoïdal, LBA 1,50 m et extrémités abaissées sur 1,65 m conformes aux coupes du tableau 15 ; un seul rang (les modules hauts masquaient les bas). |
| retenue_zoom_GS2_GBA | 3 | `controle/etape3/e3_retenue_zoom_GS2_GBA.png` | lisse à deux ondes à 0,70 m, deux supports C100 au pas de 2 m derrière la lisse, éclisse de recouvrement en bout ; GBA et DBA à hauteur 0,81 m. |
| retenue_glissieres_modules | 3 | `controle/etape3/e3_retenue_glissieres_modules.png` | DE2 à deux files dos à dos (entretoise 0,636 m), GS2 (2 supports), GS4 (1 support) ; vue d'ensemble petite : détail sur la planche zoom. |
| retenue_glissieres_extremites | 2 | `controle/etape3/e3_retenue_glissieres_extremites.png` | lisse abaissée et enterrée sur 12 m ; après correction, plus aucun support ne dépasse du sol au-delà du point d'enfouissement. |
| retenue_beton_extremites_20m | 2 | `controle/etape3/e3_retenue_beton_extremites_20m.png` | rampants de 20 m (origine de file) continus, sans facette visible. |
| retenue_attenuateurs | 4 | `controle/etape3/e3_retenue_attenuateurs.png` | nez jaune, cartouches, panneaux latéraux vers l'intérieur, butoir arrière ; longueurs 1,90 / 3,82 / 4,82 m et largeurs 0,85 / 1,50 m lisibles. |
| balises_1 | 6 | `controle/etape3/e3_balises_1.png` | J1 blanche Ø 200 × 1,30 m, J11 (0,50 / 0,70 / 0,85 m) sur embase, J12 verte à deux bandes blanches, J13 à bandes bleues (horizontales : lacune) ; bandes blanches rétroréfléchissantes peu visibles de jour (blanc sur blanc, conforme). |
| balises_2 | 5 | `controle/etape3/e3_balises_2.png` | J3 à bande rouge de 200 à 300 mm de la tête, J6 à section triangulaire et catadioptre, borne et quille PU (Paris), plot J15a de 18 mm. |
| assainissement | 5 | `controle/etape3/e3_assainissement.png` | avaloir T2 + bouche d'égout, bouche à clé, grille plate 750 × 300 (barreaux seuls après retrait du décalque), regards Ø 600 à cadre carré 840 et rond 850 (décalque de tampon du site). |
| eclairage_routier | 4 | `controle/etape3/e3_eclairage_routier.png` | mâts cylindro-coniques 8 / 10 / 12 m, crosses cintrées de 1,5-2,0 m, luminaires allumés ; caméra recentrée (mâts alignés dans l'axe à la 1re passe). |
| eclairage_urbain | 4 | `controle/etape3/e3_eclairage_urbain.png` | lanternes « top » 4 et 5 m, crosses courtes 6 et 8 m, RAL 7016. |
| mobilier_bancs_corbeilles_arceaux | 9 | `controle/etape3/e3_mobilier_bancs_corbeilles_arceaux.png` | arceaux GAM en U (à sceller, à cheviller sur platines), arceau d'Angers (poteau Ø 60 et ellipse Ø 30), bancs à lames (assise 0,50, dossier), corbeille Vigipirate (28 tiges, ouverture latérale), corbeille béton, borne fontaine. |
| mobilier_abris | 2 | `controle/etape3/e3_mobilier_abris.png` | abris 4,11 × 1,50 × 2,38 et 3,40 m : toiture, paroi arrière et joue vitrées, caisson d'affichage éclairé, banc. |
| potelets_barrieres | 7 | `controle/etape3/e3_potelets_barrieres.png` | potelets GAM RAL 7024 à bande blanche haute (visible après correction du profil), potelet à mémoire de forme, borne bois 150 × 150, barrières croix de Saint-André 0,8 / 1,2 / 1,5 m × 1,20 m. |
| feux | 9 | `controle/etape3/e3_feux.png` | têtes de Meylan à trois pots gris (R11v, R11j, R13c), R12 rouge à gauche / vert à droite vu de face (corrigé), répétiteur, boîtier d'appel, armoire, écran de contraste, bras court. |
| supports_mats | 14 | `controle/etape3/e3_supports_mats.png` | mâts de feux Ø 114 de 3,4 et 4,2 m (dont fourreau jaune 0,58-0,93 m), supports Ø 60 / 76 coupés à longueur pour les ensembles, avec bande contrastée 1,25-1,35 m. |
| supports_colliers | 5 | `controle/etape3/e3_supports_colliers.png` | brides Ø 48 à 114 avec patte et boulon vers le rail du panneau (+Y). |
| potences_feux | 3 | `controle/etape3/e3_potences_feux.png` | potences de 4, 6 et 8 m (mât Ø 168, crosse montante, tirant). |
| potence_portique_signalisation | 2 | `controle/etape3/e3_potence_portique_signalisation.png` | potence à console treillis de 6 m (bas des panneaux à 5,00 m) et portique à poutre treillis de 16 m (5,60-7,40 m). |
| bordures_courbes_T1 | 6 | `controle/etape3/e3_bordures_courbes_T1.png` | courbes de 1 m à R 1,2 / 3 / 6 m, faces convexes et concaves, profils T1 conservés. |
| bordures_courbes_T3 | 6 | `controle/etape3/e3_bordures_courbes_T3.png` | idem en T3. |
| bordures_courbes_A2 | 6 | `controle/etape3/e3_bordures_courbes_A2.png` | idem en A2 (chanfrein franchissable). |
| bordures_courbes_I2 | 6 | `controle/etape3/e3_bordures_courbes_I2.png` | idem en I2 (bordure d'îlot). |
| bordures_courbes_CS2 | 6 | `controle/etape3/e3_bordures_courbes_CS2.png` | caniveaux CS2 courbes, pente du fil d'eau conservée. |
| bordures_courbes_CC1 | 6 | `controle/etape3/e3_bordures_courbes_CC1.png` | caniveaux double pente CC1 courbes. |
| bordures_courbes_GR_T2 | 6 | `controle/etape3/e3_bordures_courbes_GR_T2.png` | bordures granit GR_T2 courbes (granit gris flammé). |
| bordures_granit_rampants | 10 | `controle/etape3/e3_bordures_granit_rampants.png` | granit A1, A2, P3 en 1 m et 0,5 m ; rampants T3 → T3 basse et T2 basse → T2 surbaissée (droite, gauche). |
| giratoires | 5 | `controle/etape3/e3_giratoires.png` | éléments Ariane pour Ø 6 / 10 / 16 m, giratoires franchissables Ø 3 m (dôme 0,14 m) et Ø 4 m (0,23 m, chanfrein 7 cm). |
| ilots | 4 | `controle/etape3/e3_ilots.png` | îlots monoblocs 120 × 60 × 13/18 et séparateurs 100 × 50 × 25, 60 × 60 × 25 (chanfreins de 3 cm). |
| dalles_paves_galets | 11 | `controle/etape3/e3_dalles_paves_galets.png` | dalles béton 30, 40, 50 cm, dalle granit 60 × 40, dalle de repérage de porte de bus, pavés granit 10 cm et 20 × 10 sciés, pavé béton 20 × 20, galets de couronne 6 / 9 / 12 cm. |
| panneaux_danger_A | 12 | `controle/etape3/e3_panneaux_danger_A.png` | faces lisibles, non inversées, triangles de 925 mm (gamme normale) ; vue en 2 rangs (élévation 16°). |
| panneaux_indication_C | 12 | `controle/etape3/e3_panneaux_indication_C.png` | carrés de 700 mm, C25b 1,60 × 2,40 (dimensions spécifiques), C64c2 et C24a à leur échelle de dessin. |
| panneaux_intersection_priorite_AB | 9 | `controle/etape3/e3_panneaux_intersection_priorite_AB.png` | AB4 octogone 800, AB3a avec son panonceau (deux plaques), AB6 sur pointe, AB25, AB5 avec panonceau ; faces dans le bon sens après correction du miroir. |
| panneaux_localisation_E_EB | 12 | `controle/etape3/e3_panneaux_localisation_E_EB.png` | plaques E/EB à l'échelle estimée ; EB10 (contour réel) correct. |
| panneaux_panonceau_M | 12 | `controle/etape3/e3_panneaux_panonceau_M.png` | panonceaux aux formats IISR (M1 = 700 × 200 mm), M11b (carré), M4, M6d, M9 ; faces lisibles. |
| panneaux_passage_niveau_G_balises_J | 12 | `controle/etape3/e3_panneaux_passage_niveau_G_balises_J.png` | G1 bis et G1a bis (plaques non convexes) découpés au contour réel ; G1 et G1a gardent le fond blanc rectangulaire du dessin (lacune) ; J4, J5, J10, J12 en plaques. |
| panneaux_prescription_B | 12 | `controle/etape3/e3_panneaux_prescription_B.png` | disques de 850 mm (gamme normale), panneaux carrés et rectangulaires de la famille B. |
| panneaux_reperage_direction_D | 12 | `controle/etape3/e3_panneaux_reperage_direction_D.png` | panneaux de direction à l'échelle ESTIMÉE (plus petite plaque à 250 mm) : proportions cohérentes, tailles à ajuster au texte réel. |
| panneaux_securite_routiere_SR | 12 | `controle/etape3/e3_panneaux_securite_routiere_SR.png` | panneaux SR à l'échelle estimée. |
| panneaux_services_CE | 12 | `controle/etape3/e3_panneaux_services_CE.png` | carrés de 700 mm. |
| panneaux_temporaire_K | 10 | `controle/etape3/e3_panneaux_temporaire_K.png` | triangles AK de 925 mm (gamme normale). |
| panneaux_touristique_H | 11 | `controle/etape3/e3_panneaux_touristique_H.png` | panneaux H à l'échelle estimée. |
| panneaux_montes_1 | 8 | `controle/etape3/e3_panneaux_montes_1.png` | AB4, AB3a, AB25, AB2, A13a, A13b montés à 2,30 m (agglomération) ou 1,00 m (rase campagne) ; supports coupés à 5 cm au-dessus du panneau (corrigé). |
| panneaux_montes_2 | 8 | `controle/etape3/e3_panneaux_montes_2.png` | AB6 (sur pointe) à 2,30 m, B14 30 (petite) et 50 à 2,30 m, B14 70 et 90 à 1,00 m (rase campagne), B1, B21-1 sur îlot à 1,00 m, B22a ; supports coupés à longueur. |
| panneaux_montes_3 | 8 | `controle/etape3/e3_panneaux_montes_3.png` | B2a, B6a1 seul et B6a1 + panonceau M6h « sauf PMR » (panonceau sous le panneau, même support, IISR 1 art. 9-1 A), C12, C13a, C1a, C20a (gamme petite, 2,30 m), J5 de nez d'îlot à 1,00 m. Le 1er essai associait M6h à un B14 (combinaison sans objet) : remplacé. |
| feux_montes | 3 | `controle/etape3/e3_feux_montes.png` | mât principal de Meylan (R11v en bas à 2,30 m, répétiteur, R12 et boîtier d'appel à 90°, fourreau jaune), îlot axial (mât 4,2 m), ensemble D200 sur mât Ø 90 ; bras courts entre mât et têtes (ajoutés). |
| materiaux_1 | 8 | `controle/etape3/e3_materiaux_1.png` | enrobés BBTM (sombre, ouvert), ESU, pelade, granulats clairs, rouge brique, ocre (cible mesurée au site) ; bétons désactivés gros et moyen. |
| materiaux_2 | 8 | `controle/etape3/e3_materiaux_2.png` | galets scellés, gravillons-résine beige, gravillons stabilisés, gravillons roulés, pavés granit carrés, pavés béton en chevrons, dalles béton-gazon, dalles ocre. |
| materiaux_3 | 5 | `controle/etape3/e3_materiaux_3.png` | BRF frais, terre végétale, terre battue, bois brut grisé (tuile 0,5 m), acier RAL 7024. |

### 9.2 Contrôles automatiques

- Volume des maillages (faces orientées vers l'extérieur) : 168 / 168 positifs ; aucun négatif.
- Alertes de fabrication : 0.
- Panneaux : 600 USD, 1644 variantes de gamme, 600 FBX (gamme normale).

### 9.3 Constats et corrections

- Panneaux : la 1re planche (AB4, AB3a) montrait les faces en miroir (« STOP » inversé) : vue de face, l'observateur placé en +Y voit +X à sa gauche ; les contours sont maintenant convertis par X = (x_pivot − x) × échelle et la largeur d'image passée négative à route::panneau (UV u croissant vers −X). Contrôlé sur la planche des AB après correction.
- Feu R12 du site (boîtier horizontal) : rouge à droite et vert à gauche vus de face (même erreur de repère) ; corrigé (rouge en +X = à gauche du piéton, vert à droite, IISR 6 art. 109-3 A p. 5).
- Potelets GAM : la bande blanche de 10 cm en partie haute n'apparaissait pas (le profil tourné n'avait pas de sommet aux limites de la bande) ; points de profil ajoutés aux cotes de la bande.
- Glissières, extrémités abaissées : des supports C100 de 0,30 m dépassaient du sol là où la lisse est déjà enterrée ; les supports suivent maintenant la lisse et sont supprimés quand le haut de la lisse est à moins de 0,23 m.
- Grille plate 750 × 300 : le décalque decal_grille_avaloir du site (photo d'une autre grille) doublait les barreaux modélisés ; retiré. Regard à cadre carré : le décalque de tampon carré se superposait au tampon rond ; retiré (cadre carré en fonte, tampon rond Ø 673).
- Candélabres : le volume signé était négatif (vasques en faces ouvertes F/G) ; vasques refaites en boîtes minces fermées ; luminaire routier réorienté (grand côté de 0,70 m dans l'axe de la crosse).
- Panneaux : collision d'identifiants M8d-bis / M8d_bis (le « - » est interdit dans les noms USD) : « - » remplacé par « _t_ » ; ensemble B21-1 renommé ensemble_B21_1_ilot.
- Mise en page des planches : modules hauts devant des modules bas (retenue béton), candélabres alignés dans l'axe de la caméra, potences imbriquées dans le portique, colliers invisibles à l'échelle des mâts : planches recadrées ou scindées (zoom glissière/GBA, colliers seuls, potences de feux seules).
- Panneaux sur plaques non convexes (G1 bis, G1a bis, J15b, EB10) : l'enveloppe convexe laissait voir l'intérieur du revers à travers les zones transparentes de la face ; contour réel (OpenCV) et faces triangulées (Divide) pour les plaques remplissant moins de 95 % de leur enveloppe.
- Ensembles de panneaux : supports de longueur fixe (3,0 / 3,5 / 4,0 m) dépassant de 0,3 à 0,6 m au-dessus des panneaux ; supports désormais coupés à 5 cm au-dessus du haut du panneau (arrondi au décimètre), 10 supports sur mesure ajoutés.
- Ensembles de feux : têtes « flottant » à 5 cm du mât ; bras court Ø 60 de 0,33 m (feu_bras_court_L033, feux.json : bras de 0,15-0,25 m) ajouté au centre de chaque tête.

## 10. Lacunes

- Lisse de glissière profil A : section 312 × 83 × 3 mm ESTIMÉE (aucune fiche cotée trouvée ; profil B 296 × 2,5 mm d'après Hellopro) ; écarteurs (DEM) et C100 (100 × 50 × 5) estimés ; pas de terminal en « queue de carpe », pas de raccord NF 058 GBA ↔ glissière, pas de GR4/GRC/GCU ni de barrières de pont BN1/BN2/BN4.
- LBA : pentes de la face haute et du dos déduites de la base et du sommet (non cotées) ; extrémités GBA/DBA abaissées : rampant linéaire vers un profil de 4 cm (forme exacte non cotée).
- Atténuateurs : forme générique aux dimensions hors tout des fiches Aximum ; décor à chevrons du nez en couleur moyenne (décalque à faire).
- Balises : bandes obliques à 30° des J6 et J13 modélisées horizontales ; J13 sans son élévation trapézoïdale ; J4, J5, J10 fabriquées comme plaques (panneaux) ; J14a/J14b, J1 sur glissière (corps 550) et J7 non fabriquées ; bandes rétroréfléchissantes non simulées (blanc sur blanc).
- Panneaux : échelle ESTIMÉE pour les 174 panneaux à dimensions variables (D, E/EB, H, SR : plus petite plaque à 250 mm) ; 12 dessins du Cerema à une autre échelle que 1:4,99 (C14, C25, C64b…, confiance moyenne) ; G1 et G1a dessinés sur fond blanc rectangulaire (la plaque garde ce fond) ; rétroréflexion non simulée ; une seule LOD ; FBX seulement pour la gamme normale ; supports profilés des grands panneaux (IPN 57 × 95 à 131 × 220, IISR 1 art. 6 B) non fabriqués ; 8 compositions d'exemple exclues ; panneaux temporaires K hors triangles AK exclus (cônes, piquets, barrières de chantier).
- Ensembles : 24 configurations de panneaux et 3 de feux seulement (exemples à généraliser par le générateur) ; ni fourreau ni massif de fondation ; la hauteur 2,30 m est appliquée au bord inférieur de la plaque la plus basse (IISR 1 art. 9 b).
- Feux : pictogrammes des R12 (figurines) et R13c (cycle) non dessinés (matériaux nommés par pictogramme) ; visières tubulaires fermées en bas ; armoire de commande, écran de contraste, potences de feux et leurs sections : estimations.
- Éclairage : diamètres des mâts de 8 et 12 m interpolés, luminaires génériques (pas de photométrie ni de modèle fabricant) ; candélabres urbains : estimations.
- Assainissement : cotes PAM relevées dans les résultats de recherche (PDF non lus) ; chambre de la bouche d'égout et plaque de 0,80 × 0,60 estimées ; arc de la gueule de l'avaloir T2 approché par un linteau droit.
- Mobilier : profondeur de l'abri (1,50 m) reprise d'un exemple (SMT) ; longueurs de bancs choisies (catalogue « variable ») ; borne fontaine de forme générique.
- Bordures : granit A1, A2, P3 à la section des profils béton correspondants ; profil Ariane relu sur un dessin non à l'échelle (cotes 600 × 300 seulement) ; dôme du giratoire franchissable Ø 3 m estimé ; biseaux des îlots approchés par un chanfrein ; pièces d'angle T3/T4 et courbes T4/A1/I1/I3/I4 toujours absentes.
- Dalles et pavés : formats courants non sourcés par un catalogue (confiance « estimation »).
- Matériaux : cibles de teinte du rouge et de la résine beige estimées (pas de mesure sur le site) ; côtés de tuile estimés pour BBTM, pelade, rouge, gravillons roulés (2,0 / 2,0 / 2,0 / 0,6 m) ; pas de mesure terrain de Meylan pour ces revêtements.
- Import Unreal non testé (USD à variantes LOD et gamme, références relatives ; FBX un fichier par LOD).

## 11. Licences

- Meshes : création maison (HDA `route::*`), cotes tirées de documents publics cités ; aucune géométrie copiée d'un fabricant, aucune donnée City Sample ni CARLA.
- Matériaux : CC0 1.0 (ambientCG, Poly Haven) ; matériaux simples : maison.
- Faces des panneaux : signaux officiels du Cerema (PDF détourés, Licence Ouverte 2.0 présumée, réserve non levée : voir `panneaux_fr_catalogue.json` meta.licence_source) ; PNG et USD de panneaux non versionnés.
- Fiches fabricants (Aximum, Saint-Gobain PAM, Odyssée Lumière, Alkern) et documents des collectivités (Angers, Grenoble-Alpes Métropole) : consultés et cités (cotes, pages), non redistribués (`assets/lib/route_fr/_sources_etape3/`, non versionné).
