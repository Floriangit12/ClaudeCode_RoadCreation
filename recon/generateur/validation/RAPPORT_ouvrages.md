# Rapport du lot « ouvrages » : ponts, passages inférieurs, viaducs (L8 du plan, étape E07 de la chaîne)

*`recon/generateur/validation/RAPPORT_ouvrages.md`, 22/10/2026. Données : `rapport_ouvrages.json` (rejoué par
`faire_rapport_ouvrages.py`), contrôles `controles_ouvrages.json`, constats des rendus `constats_visuels_ouvrages.json`.*

## 1. En bref

Le générateur sait maintenant fabriquer des ouvrages d'art à partir d'une description en mots, comme les rues et les
carrefours : un passage supérieur sur une autoroute (D1), un passage inférieur sous une voie rapide (D2), un viaduc de
cinq travées sur une vallée sèche (D3) et un pont urbain avec piste cyclable (D4). Chaque scène est « imaginée d'après »
des ouvrages courants français, dont ceux de l'A41 et de la Rocade Sud à Meylan, et décrite comme sur une photo.

Ce qui est fabriqué :

- le **profil en long** de la route portée : rampes et raccordements, avec gabarit et revanche garantis ;
- le **tablier** sous la section courante de la route portée : dalle, dalle à larges encorbellements, portique, caisson
  ou poutres. Le profil en travers est conservé : chaussée, trottoirs, bordures et marquages continus sur l'ouvrage ;
- les **corniches**, les **piles** (voiles, ou poteaux et chevêtre), les **bossages et appareils d'appui** ;
- les **culées** (sommier, garde-grève, murs en retour) et les **dalles de transition** ;
- les **piédroits et murs en aile** des portiques ;
- les **joints de chaussée** aux abouts, sur toute la plate-forme, trottoirs compris ;
- les **garde-corps S8** (bande GC97, ou 1,20 m le long d'une piste) et les **BN4** ;
- le **terrain** : remblais d'accès et talus 3/2, sol abaissé sous le tablier, talweg, déblai de la route franchie.

Les **4 scènes passent les 10 critères mesurés** par le contrôle indépendant (§ 5), sur la dernière fabrication
(passe 10). Les rendus ont été regardés en tuiles natives. Huit défauts vus sur ces tuiles ont été corrigés à la source
(§ 6).

## 2. Livrables

| Fichier | Rôle |
|---|---|
| `hda/rg_ouvrages/construire.py`, `vex_ouvrages.py`, `rg_ouvrages.hdalc/` | HDA **`rg::ouvrages::1.0`** (nouvelle) : 2 entrées (couches fabriquées, références), 5 sorties (routes déformées, ouvrages, terrain, points, ouvrages lus) ; Python SOP de lecture seulement, géométrie en VEX |
| `fabriquer_ouvrages.py` | pilote du lot (nouveau) : compilation, une couche par route fabriquée par la chaîne de l'étape 2 (importée sans modification), `rg::ouvrages`, exports, rendus |
| `description/ouvrages.py` | compilateur de la clé `ouvrages` (nouveau) |
| `description/description_vers_modele.py` | **ajout minimal** : clé racine `ouvrages` admise, appel du compilateur ; la liste `ouvrages` ne déclenche pas la couche réseau (sa clé `ouvrages` en dictionnaire reste traitée comme avant) |
| `schema/modele_voie.schema.json` | **ajout minimal** : `ouvrage.construction` (objet), `tablier.type`, `tablier.structure` + `caisson`, `portique`, `cadre` |
| `description/FORMAT_DESCRIPTION.md` § 17, `hda/README_RG.md` § 16 | documentation (sections ajoutées) |
| `scenes_ouvrages/D1` à `D4` | scènes de test (nouvelles) |
| `assets/specs/route/regles_ouvrages_fr.json` | 16 règles complémentaires sourcées (OA-*), nouveau fichier ; `regles_route_fr.json` n'est pas modifié |
| `validation/controler_ouvrages.py`, `faire_rapport_ouvrages.py` | contrôle indépendant (numpy, rayons verticaux sur les maillages exportés) et rapport |
| `validation/regles_demandees_ouvrages.json` | règles demandées au propriétaire de la base fusionnée |
| sorties (non versionnées) `recon/out/generateur/<scène>/` | `couches/<route>/` (couche figée, chaîne de l'étape 2), `ouvrages/` (`scene_ouvrages.usdc` Z haut, `points_ouvrages.json` au contrat `pj_points/0.1`, `maillage_*.npz`, `ouvrages.json`, manifeste), `rendus/` (3 vues, tuiles, planche ≤ 1092 px) |

## 3. Méthode

**Houdini n'invente rien.** Chaque cote vient de l'une de ces sources :

- la description, en provenance `description:` ;
- une règle de la base fusionnée : RF-GV-PON-003, -007, -010, -012, -014, -015, DEF-033, RF-OSM-OUV-001 ;
- une règle complémentaire sourcée, en provenance `catalogue:regles_ouvrages_fr.json#OA-…`.

Faute de source, la compilation s'arrête et dit « à dire ». Les choix de fabrication sans règle sont déclarés `[G]`
dans `vex_ouvrages.py` et dans `README_RG.md` § 16.

**Une couche par route.** `rg::nivellement` n'a qu'un Z par point (x, y). Deux routes superposées ne peuvent donc pas
partager son HeightField : dans un essai, les bordures et la peinture d'une route se seraient drapées sur l'autre.
Chaque route est donc fabriquée seule par la chaîne existante, sans profil en long :

- L1, L2, L2b ;
- `rg::autoroute` pour la GBA, quand il y en a une.

Elle est ensuite figée dans un fichier bgeo. `rg::ouvrages` applique enfin le profil en long par déformation verticale,
z += z_long(s) :

- la géométrie est découpée au préalable en briques de 1 m ;
- les normales sont transformées par J^-T.

La coupe, les marches des bordures et l'épaisseur de la peinture restent ainsi exactes : écart au profil du modèle 0,0 mm
dans l'axe.

**Le profil en long** est calculé par le compilateur. Il assure, sur toute la largeur franchie :

- le gabarit sous l'ouvrage : 4,30 m, ou 4,75 m sous une autoroute ou une voie express, + revanche de 0,10 m
  (RF-GV-PON-012, DEF-033) ;
- une revanche au-dessus du terrain naturel sous le tablier.

Ses valeurs limites viennent de l'ARP (tableau 12) ou de l'ICTAVRU (§ 3). Il est publié dans `routes[].profil_long`,
avec la source « ouvrage » et les z NGF tous les 0,50 m.

**Le terrain** est un seul champ de Z, de la plus basse à la plus haute priorité :

- le terrain naturel, avec le talweg dit ;
- les remblais en « cônes » 3/2 autour des plates-formes, aux coins arrondis, avec un raccord adouci au pied ;
- les massifs sous les sommiers ;
- les déblais : plate-forme portée, route franchie (couloir vertical sous un portique), sol abaissé sous le tablier.

Il est maillé à 1 m (0,50 m autour de l'ouvrage), avec des lignes imposées sur les bords de plate-forme et les faces
des piédroits, jusqu'à 2 km.

## 4. Règles et sources

DocRoute (lecture seule) donne :

- le gabarit, la revanche, les trottoirs, les garde-corps et l'élancement des dalles, des portiques et des cadres
  (`10_…/PONTS_OUVRAGES.md`, RF-GV-PON-*) ;
- la bande GC97 (DEF-033).

Les valeurs absentes ont été lues dans les PDF locaux (texte extrait de `10_…/tmp/txt`) ou cherchées sur internet. Elles
sont rangées dans `regles_ouvrages_fr.json` avec la page et la citation :

| Id | Valeur | Source |
|---|---|---|
| OA-TAL-001 / -002 | talus 3/2 ; remblai technique 10 m | GPOA p. 241 |
| OA-BAL-001 | balancement ≤ 0,80 environ, ≥ 0,55 | GPOA p. 208 |
| OA-ELA-001 / -002 | PRAD 1/18-1/20 (isostatique) ; PSIDP à larges encorbellements l/28 (≥ 3 travées) | GPOA p. 210-211 |
| OA-PIPO-001 | portiques : murs de tête, remblai ≤ 1 m, ni joint ni appareil d'appui | GPOA p. 213, 219-223 |
| OA-ESP-001 | 0,40 m about / garde-grève ; 0,30 m chevêtre / intrados | GPOA p. 138 |
| OA-JNT-001 / -002 | joint à revêtement amélioré de 0,50 m (0,40-0,60) ; about à 0,50 m de l'appareil (exemple) | Cerema JC16 p. 83, p. 81 |
| OA-DDT-001 | dalle de transition 0,30 m, 3 à 5 m (4,0 m retenu [G]) | Cerema, ROA 2024, article BOA p. 2 (internet) |
| OA-BN4-001 | BN4 : 3 lisses, supérieure à 1,00 m, poteaux tous les 2,50 m, longrine 0,12-0,18, 0,45 m du bord, file ≥ 30 m | fiche Aximum BN4 04/2022, NF P 98-421 (internet) |
| OA-PEL-001 / -002 | déclivité et rayons saillant / rentrant (R1, R2, artère 110 ; U60, U80/A80, A100) | ARP tableau 12 p. 60 ; ICTAVRU p. 31 |
| OA-CAI-001 | caissons de hauteur constante : h/l observé 0,045-0,056 | AFGC (pont sur le Var), Infociments (viaduc du Courtineau) (internet, observations) |
| OA-REV-001 | revêtement sur tablier 0,10 m | choix [G] (ordre de grandeur de RF-GV-PON-011) |

Les guides Setra des corniches (1994), des piles (PP73), des appareils d'appui (2007), des dalles de transition (1984)
et des encorbellements successifs (2003) n'ont pas pu être lus : le site renvoie un accès refusé. Les cotes des
corniches, piles, sommiers et appareils sont donc **dites** par chaque description. Elles sont demandées en règles
(`regles_demandees_ouvrages.json`).

## 5. Critères mesurés (contrôle indépendant, passe 10)

| Critère | D1 PS (PSIDP 19,5 + 26 + 19,5) | D2 PI (PIPO 10,6) | D3 viaduc (caisson 32 + 3 × 40 + 32) | D4 pont urbain (PRAD 2 × 16) | Seuil |
|---|---|---|---|---|---|
| hauteur libre | **4,896 m** (475 rayons) | **4,402 m** (1 175 rayons) | 0,153 m au-dessus du terrain (talweg) | 1,563 m au-dessus du terrain (talweg) | ≥ 4,85 (autoroute) / ≥ 4,40 ; talweg : ≥ revanche 0,10 |
| épaisseur | **0,929 m = l/27,99** | 0,365 m = l/40 + 0,10 | 2,00 m (h/l 0,050, dans les observations) | 0,845 m = l/18,9 | dalle : l/28 ± 1 cm ; autres : leur règle |
| rapport de travées | **0,75 / 0,75** (travées mesurées 19,5 / 26,0 / 19,5) | 10,6 (1 travée) | **0,80 / 0,80** | 16,0 / 16,0 (isostatiques) | [0,6 ; 0,85] |
| garde-corps / BN4 | 0,985 / 0,985 (Hc mesurée 6,44 m ; bande [0,932 ; 1,032]) | BN4 0,999, file de 30,1 m | BN4 0,998, file de 196 m | trottoir 0,981 (bande [0,928 ; 1,028]) ; piste **1,202** | GC97 ; 1,20 ± 0,02 piste ; BN4 > 0,90 et ≥ 30 m |
| marquages continus sur l'ouvrage | T'1 : vide max 5,0 m (modulation 5,0) ; peinture à 1-2 mm du sol | 6 lignes (T1, T4, continues) | 3 lignes (T2, T1) | 2 demi-axes T'1 de piste | vide ≤ modulation + 0,10 ; 0-6 mm |
| pas de trou route / tablier | 0 rayon sans tablier ; 0,111-0,256 m ; corniche au bord à 3 mm | 0 ; 0,101-0,363 ; 1 mm | 0 ; 0,102-0,268 ; 1 mm | 0 ; 0,097-0,264 ; 3 mm | 0 ; 0,08-0,60 ; ≤ 3 cm |
| joints aux abouts | 2 ; couverture 100 % ; 97 % à 1-6 mm (médiane 3 mm) | 0 (portique, OA-PIPO-001) | 2 ; 100 % ; 100 % | 2 ; 100 % ; 98 % | ≥ 99 % de la plate-forme ; ≥ 95 % à 1-6 mm |
| talus sans falaise | 0,677 (478 565 facettes) | 0,681 | 0,677 | 0,667 | pente ≤ 1/1,5 + 5 % de discrétisation (0,700) ; 0 facette plus raide |
| terrain sous les routes | 0 / 5 576 points | 0 / 5 236 | 0 / 2 703 | 0 / 1 853 | 0 point où le terrain affleure le revêtement |
| profil en long (axe) | 0,0 mm | 0,0 mm | 0,0 mm | 0,0 mm | ≤ 5 mm |

Les valeurs de la dernière passe sont dans `rapport_ouvrages.json`, qui fait foi : 10 critères sur 10 atteints dans les 4 scènes.

Contrôles du compilateur (dans `compilation.json`, tous conformes) :

- domaine de portée du type ;
- balancement ;
- bande GC97 ;
- trottoirs sur l'ouvrage (≥ 1,00 m) et dessous (≥ 2,00 m) ;
- distance des piles aux voies franchies : 4,3 m en D1, pour 2 m exigés ;
- déclivité : 6,0 % en D1 (U60), 5,07 % en D2 (U80/A80).

## 6. Rendus regardés

Trois vues par scène : dessus, oblique 3/4 et conducteur à 1,20 m. Pour le passage inférieur D2, le conducteur est
sous l'ouvrage. Toutes ont été regardées en tuiles natives, avec une planche ≤ 1092 px par scène
(`<scène>/rendus/planche_<scène>.png`).

Défauts vus puis corrigés à la source, chacun suivi d'une nouvelle fabrication :

1. bordures en dents de scie, dues à des normales nulles sur les pièces fusionnées ;
2. pied de talus en escalier : triangulation, coins arrondis, raccord adouci ;
3. murs en aile absents en D2 : sens inversé ;
4. terrain naturel recouvrant la chaussée en D3 et D4 : déblai de la route portée ;
5. marche du remblai le long des rives devant les culées, remplacée par le « sol abaissé » sous le tablier ;
6. file de BN4 trop courte : 30 m ;
7. bande de terrain sur le bord de la rue franchie en D2 : marche des bordures dans la coupe. Un critère a été ajouté au
   contrôle ;
8. liseré de terrain au bord des bandes dérasées en D3 : lignes de grille imposées ;
9. liseré de remblai sur le bord extérieur du trottoir sous l'ouvrage (D2 : tolérance d'appartenance à la plate-forme)
   et facette de 0,74 au bout de la route (D1 : ni remblai ni déblai au-delà des bouts de scène) ; corrigés en passe 10.

Ce qui reste visible et assumé :

- terrain neutre, selon la consigne « route seule » : les reliefs ne se lisent que par l'ombrage, et la vallée de D3
  est peu lisible de dessus ;
- en D1, piles nues au bord des bermes : la glissière de protection relève de l'étape E13 ;
- bouts de routes coupés en limite de scène.

## 7. Rétrocompatibilité

- `description/tests/tester_descriptions.py` : 27/27 descriptions valides, 27 déterministes, attendus du catalogue
  12/12, faits 25/25, erreurs attendues 26/26.
- Recompilation des 29 descriptions S, A, J, G et M : 27 modèles sont identiques à l'octet à ceux déjà produits. Les deux
  autres, M24 et M27, sont comparés à des modèles du 17/10. Ces modèles sont antérieurs aux évolutions du compilateur
  faites par d'autres lots le 18/10 (matériau des bordures) ; aucune de ces deux descriptions n'a de clé `ouvrages`.
- Les HDA existantes et `fabriquer_generateur.py` ne sont pas modifiés.

## 8. Limites

- Routes portées droites près de l'ouvrage. Le repère est construit par segments : une route courbe donnerait des
  facettes au droit des sommets de sa référence.
- Un ouvrage par route portée, et profil en long symétrique centré sur le croisement.
- Pas de relèvement ni d'abaissement de la route franchie.
- Pas de culée enterrée à colonnes, de mur de front, de trémie ni de tunnel.
- Glissières de protection des piles et transitions BN4 / glissière : étape E13.
- Cotes des corniches, piles, sommiers et appareils dites par la description, faute de règle lue.
- Hauteurs des lisses intermédiaire et inférieure de la BN4 : choix [G].
- Élancement du caisson contrôlé contre deux observations seulement : confiance faible, contrôle d'avertissement.
- `fabriquer_generateur.py` ne connaît pas encore la famille « ouvrages » : l'agent d'intégration branchera
  `fabriquer_ouvrages`.
- Taille des sorties : `scene_ouvrages.usdc` contient les routes déformées complètes, de 34 à 102 Mo selon la scène.

## 9. Commandes

```
hython recon/generateur/fabriquer_ouvrages.py recon/generateur/scenes_ouvrages/D1_passage_superieur_autoroute.yaml \
       recon/generateur/scenes_ouvrages/D2_passage_inferieur_voie_rapide.yaml recon/generateur/scenes_ouvrages/D3_viaduc_vallee_seche.yaml \
       recon/generateur/scenes_ouvrages/D4_pont_urbain_piste_cyclable.yaml --construire-hda --rendus [--reprendre-couches]
python recon/generateur/validation/controler_ouvrages.py            # 4 scènes -> validation/controles_ouvrages.json
python recon/generateur/validation/faire_rapport_ouvrages.py        # -> validation/rapport_ouvrages.json
```
