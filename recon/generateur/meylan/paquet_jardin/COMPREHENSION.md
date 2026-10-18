# Carrefour Paquet Jardin (M01) — compréhension de la scène (passe v2)

*`recon/generateur/meylan/paquet_jardin/COMPREHENSION.md` — 18/10/2026, étape 3, passe v2 du lot « carrefours ».
État décrit : **avant travaux, 18/05/2025** (fenêtre d'état des photos : 24/08/2024 → 22/06/2025). Aucune photo n'est
versionnée : les vues citées sont sous `recon/out/generateur/meylan_paquet_jardin/comparaison/meylan_paquet_jardin/
photos_non_versionnees/v2/vues/vue_<clé>.png` (numéros P.. du plan `comprehension/plan_vues_centre.png`).*

Comment cette compréhension a été construite : j'ai regardé moi-même les images, en tuiles natives (≤ 1 092 px), et
croisé ce qu'elles montrent ; aucun algorithme n'a fusionné les sources. Pour lire des positions, j'ai posé une grille
de 1 m (repère du site) sur l'ortho PCRS 5 cm et l'IGN 20 cm (`_travail/v2/grille.py`, sorties dans
`recon/out/generateur/meylan_paquet_jardin/_travail/v2/lecture/`, images sans photo de tiers). Le repère est celui du
site : x vers l'est, y vers le nord, origine O du dépôt (L93 917 279,43 ; 6 460 289,98).

## 1. Images lues

| Source | Date | Ce que j'en ai tiré |
|---|---|---|
| PCRS 5 cm (CRAIG), zoom du centre et 9 tuiles du site ; 10 lectures à grille (`pcrs_NO`, `pcrs_NE`, `pcrs_SO`, `pcrs_SE`, `pcrs_coin_SO_vercors`, `pcrs_S_vercors`, `pcrs_S_bretelle`, `pcrs_verdun_ne`, `pcrs_reviree`, `pcrs_verdun_so_30`) | 10/05/2022 | toute la géométrie fine : bordures, îlots, passages, rectangles jaunes, damiers verts, lignes du cœur |
| IGN BD ORTHO 20 cm, zoom du centre et lecture à grille `ign24_S` | 09/08/2024 | état le plus proche de la date d'état : enrobé neuf (sombre) sur la moitié nord-ouest du cœur, ligne axiale repeinte en longue ligne ; îlots inchangés |
| IGN IRC 20 cm | 09/08/2024 | végétation : îlots d'angle est (planté) ; angle ouest sans végétation vigoureuse (refait en 2024) |
| IGN 20 cm 2021, 2018, 2015 ; Pléiades 50 cm 2025 | 13/08/2021, 21/08/2018, 03/07/2015 ; 2025 | même dessin des îlots et des passages depuis 2015 ; Pléiades trop flou pour le détail |
| Plan IGN v2 (contexte) | courant | noms : la Revirée et le Vercors forment l'axe nord-nord-ouest / sud-sud-est, Verdun l'axe sud-ouest / nord-est |
| Planches du centre 2 × 2 `centre_p01` à `centre_p13` (52 vues réduites de moitié) | 2019 → 2025 | tour d'horizon du cœur, chantier de l'angle ouest le 01/05/2024 |
| Vues natives du cœur et des branches (1 092 px) : 119d9094 (-045, -015, -084, -134, -162, +114), 31d16b8e (-113, +160), 734a0da6 (-169), e5d79de9 (+037), 4d9fa65d (+180), 29fb102d (-129) | 18/05/2025, 12/01/2025 | détail des îlots, des marquages du cœur, des traversées cyclables |

Au total : 7 couches d'ortho, 52 vues du centre lues en planches et 13 vues natives (dont 11 dans la fenêtre d'état).

## 2. La scène en une phrase

Un grand carrefour à feux en croix **légèrement décalé** : l'avenue de Verdun (2 × 2 voies, nord-est / sud-ouest) est
coupée par la Revirée (nord-nord-ouest) et le Vercors (sud-sud-est), dont les axes croisent la médiane de Verdun à
≈ 4,4 m l'un de l'autre ; **chaque branche a un îlot au droit de son passage**, l'angle sud est un **grand îlot revêtu**
derrière lequel une **bretelle** file de Verdun sud-ouest au Vercors, et la Chronovélo traverse Verdun sud-ouest entre
deux rangées de **rectangles jaunes**.

## 3. Le centre (zone de conflit)

| Élément | Où (repère du site) | Images qui le montrent |
|---|---|---|
| **Médiane de Verdun** | droite à 45° passant ≈ 2,1 m au sud-est de la droite y = x du repère (îlot NE à 1,9 m, îlots SO à 2,1-2,5 m, nœud OSM N_VERDUN_PJ_NE à 2,13 m) | `pcrs_NE`, `pcrs_SO`, `pcrs_S_bretelle` ; nœud de `reseau_meylan.yaml` |
| **Ligne axiale dans le cœur** | le long de la médiane de Verdun, de l'îlot SO à l'îlot NE : en 2022 tirets courts (PCRS) ; en 2024-2025 **ligne mixte** (continue côté sud-est, discontinue côté nord-ouest, que franchissent les tourne-à-gauche de Verdun NE vers le Vercors) | PCRS centre ; IGN 2024 centre ; 119d9094 -045, -015, -134 ; 5c0d1d39 -057 ; 2ab4efbc -099 ; e5d79de9 -051 |
| **Flèches dans le cœur** | flèches de direction (tout droit) de part et d'autre de la ligne axiale, vers (5 ; 1) et (−6 ; −8) | PCRS centre ; 119d9094 -045, -134 ; 2ab4efbc -099 |
| **Îlot de Verdun NE** | îlot allongé ≈ 2 m, revêtu (enrobé sombre), bordure basse : nez arrondi côté cœur vers (7,4 ; 5,2), coupé à niveau par le passage (≈ 11-14 m de l'origine le long de Verdun), nez côté approche avec B21 (≈ 16-18 m), puis zone hachurée de 2,2 m | `pcrs_NE` ; 119d9094 -134, -162 ; e86aa913 -010 ; 9834f494 -048 ; e5d79de9 -051 |
| **Îlots de Verdun SO** | deux îlots sur la médiane : îlot rond ≈ 2,7 m (dessus en enrobé neuf, bordure claire, mât) vers (−7,4 ; −10,9), au bord du cœur, entre les deux moitiés de la traversée de la Chronovélo ; îlot à nez arrondi (B21, mât) vers (−13,5 ; −16,5), refuge du passage piéton ; zone hachurée de la médiane au-delà, qui s'élargit vers le sud-ouest | `pcrs_SO`, `pcrs_S_bretelle` ; 31d16b8e -113 ; 734a0da6 -169, -143 ; aa9d7e12 -161, -133 ; 2ab4efbc -099 |
| **Traversée de la Chronovélo (Verdun SO)** | bande de ≈ 2,7 m entre **deux rangées de rectangles jaunes** (≈ 1,2 × 0,5 m), logos vélo, du coin ouest (−13 ; −5,5) au coin sud (−2,5 ; −15), entre le passage piéton et le cœur ; interrompue par l'îlot rond | `pcrs_SO`, PCRS centre ; 31d16b8e -113 (2025) ; IGN 2024 (moitié nord-ouest) ; m197449629 (2022, HF) |
| **Passage de Verdun SO** | zébra de 3 m en deux moitiés décalées de ≈ 1,4 m : (−17,5 ; −10) → (−13 ; −14,5) et (−10,5 ; −15) → (−6 ; −19,5) | `pcrs_SO` ; 734a0da6 -169 ; 31d16b8e -113 |
| **Passage de Verdun NE** | deux moitiés : (4,5 ; 13,3) → (10,6 ; 7,3) et (10,4 ; 7,7) → (16,7 ; 2,1) | `pcrs_NE` ; 119d9094 -134, -162 ; e5d79de9 -051 |
| **Îlot de la Revirée** | îlot en coin, bordure basse, dessus revêtu (enrobé sombre), qui porte les D21 « LA REVIRÉE / Collège L. Terray » et « Commerces de la Revirée » : ≈ 2-3 m de large au bord de Verdun (≈ (−4,3 ; 5,7)), il s'effile et passe entre les deux demi-passages jusqu'à un nez (poteau bois) au-delà | `pcrs_NO` ; 119d9094 +114 ; e5d79de9 +037 ; 2ab4efbc +179 (24/08/2024) ; 31d16b8e +160 |
| **Passage de la Revirée** | deux demi-passages décalés : (−10,3 ; 10,4) → (−7,2 ; 6,1) et (−7,5 ; 15,6) → (−2,3 ; 10) ; **traversées cyclables vertes** (damier blanc sur fond vert) côté cœur de chaque moitié | `pcrs_NO` ; 119d9094 +114 ; e5d79de9 +037 |
| **Angle ouest (Revirée / Verdun SO)** | îlot d'angle planté en pointe (herbe haute, bordure granit), hypoténuse ≈ (−8,5 ; 3) → (−13,5 ; −2), la Chronovélo passe derrière | `pcrs_NO` ; 31d16b8e +160 (18/05/2025) ; chantier le 01/05/2024 (26ea5f01, 1149e115, 3fc0ff2e : HF) |
| **Angle nord (Revirée / Verdun NE)** | trottoir revêtu, bordure courbe, BEV ; zébra de la Chronovélo / du trottoir au nord de la Revirée | e5d79de9 +037 ; `pcrs_NE` |
| **Angle est (Verdun NE / Vercors)** | îlot d'angle planté (terre et arbustes), bordure ≈ (13,5 ; 1,2) → (12,5 ; −8,5) | `pcrs_NE`, `pcrs_SE` ; IRC 2024 |
| **Angle sud = grand îlot revêtu** | ≈ 8 × 8 m entre les voies montantes de Verdun SO (nord-ouest), la sortie du Vercors (est) et la bretelle (sud) : sommets ≈ (−2,3 ; −14,7), (−6,5 ; −19), (1,1 ; −20,8), dos vers y ≈ −23,5 ; mâts R11, la Chronovélo le traverse | `pcrs_coin_SO_vercors`, `pcrs_SO` ; 31d16b8e -113 ; P16/P20 (HF) |
| **Vercors : îlot central en galets** | **triangle** au bord du cœur, sommets ≈ (2,9 ; −12,2), (6,2 ; −13,5), (4,2 ; −15,7), B21 ; coupé par le passage (refuge, mât R11) ; puis **îlot long** ≈ 2 m de (6,5 ; −16,5) à (11,3 ; −27,3) ; la sortie (une voie large) passe à l'ouest, les deux entrées à l'est | `pcrs_coin_SO_vercors`, `pcrs_SE`, `pcrs_S_vercors` ; 119d9094 -045, -084 ; a1ffea74, 4d9fa65d, 29fb102d |
| **Passage du Vercors** | deux moitiés décalées : (1,1 ; −20,8) → (5,9 ; −16,1) sur la sortie, (6,3 ; −16,1) → (12,6 ; −8,6) sur les entrées | `pcrs_coin_SO_vercors` ; 119d9094 -084 |
| **Bretelle SE** | une voie (≈ 4 m) le long de Verdun SO derrière une séparation peinte et une barrière, quais La Revirée (zigzags jaunes, abri), puis elle passe au sud du grand îlot de l'angle sud (traversée : zébra + rectangles jaunes de la Chronovélo, orientée nord-sud vers (−5 ; −27)) et rejoint la sortie du Vercors vers (5 ; −26) | `pcrs_S_bretelle`, `pcrs_coin_SO_vercors`, tuiles t06-t07 du PCRS ; 0fe2656f, 034cb578 (itération 1) |

## 4. Branches

- **Verdun NE** : 2 voies sortantes (≈ 3,3 + 2,9), zone hachurée de 2,2 m qui s'ouvre vers 50 m, voie de TAG + voie
  TD/TAD en entrée (flèches, 9834f494 -013, e86aa913 -010) ; côté nord-ouest bande enherbée, Chronovélo 3 m, trottoir ;
  « 50 » au sol sur les voies sortantes (`pcrs_verdun_ne`). Profil du levé GAM (coupe verdun_ne_40) cohérent avec la
  lecture à ≈ 1 m près ; médiane à 2,1 m au sud-est de la droite du repère.
- **Revirée** : chaussée de ≈ 8 m, ligne continue axiale à 326° (`pcrs_reviree`), « 30 » au sol, trottoirs.
- **Verdun SO** : 2 voies sortantes (« 50 » au sol, ≈ 3 m), médiane hachurée qui s'élargit vers le sud-ouest (≈ 2,4 m à
  l'îlot, ≈ 3,5-4 m à 35 m : 734a0da6 -143, -169), 2 voies montantes, séparation peinte + barrière, bretelle ; côté
  nord-ouest contre-allée, bande fleurie, Chronovélo, trottoir.
- **Vercors** : sortie d'une voie de ≈ 5 m (« 30 » au sol), ligne continue, deux entrées de ≈ 3 m (flèches TAG, TD/TAD) ;
  la route s'incurve au bout de l'îlot long (151° → 163°, `pcrs_S_vercors`) ; Chronovélo le long du côté ouest, bordée de
  lignes jaunes, derrière une bande plantée (4d9fa65d +180).

## 5. Contradictions entre dates, et comment je les ai tranchées

| Contradiction | Tranchée ainsi |
|---|---|
| Ligne du cœur : tirets courts (PCRS 2022) / longue ligne (IGN 2024) / ligne mixte (photos 2024-2025) | marquage repeint en 2024 avec l'enrobé neuf de la moitié nord-ouest (IGN 2024 sombre) ; l'état du 18/05/2025 est celui des photos : ligne mixte |
| Angle ouest : îlot planté (PCRS 2022) / chantier (photos du 01/05/2024, HF) / terre et gravier (2ab4efbc +179, 24/08/2024) / îlot planté à herbe haute (31d16b8e +160, 18/05/2025) | travaux de l'angle ouest au printemps-été 2024 ; à la date d'état l'îlot d'angle planté existe à nouveau, de même forme en plan à ≈ 1 m près : la géométrie du PCRS est gardée |
| Îlots SO et îlot de Verdun NE : dessus gris clair (PCRS 2022) / enrobé neuf sombre (2024-2025) | même forme ; dessus refait en 2024 : « enrobé » |
| Photos du 01/05/2024 (HF) : barrières, pelleteuse, fouilles à l'angle ouest | état transitoire, écarté (la fenêtre d'état commence le 24/08/2024) |
| Description de l'itération 1 : bretelle = voie qui entre dans le cœur ; médiane sur y = x | contredite par toutes les orthos (2015-2024) et par 31d16b8e -113 : corrigée (§ 3) |

## 6. Ce qui reste incertain

- La forme exacte de l'îlot de la Revirée après les travaux de 2024 (largeur au bord du cœur 2 à 3 m, longueur du nez) :
  aucune ortho nette après 2022 (IGN 2024 à 20 cm floue), photos en oblique seulement.
- La largeur de la médiane hachurée de Verdun SO au-delà de 25 m (2,4 à 4 m) et la position exacte de la bretelle au
  sud de l'angle sud (PCRS 2022 seul ; pas de photo verticale).
- Le régime de la bretelle à son débouché sur le Vercors (cédez ou feux) : aucun panneau lisible.
- Le plan de feux (non observable).
- Les rectangles jaunes de la Chronovélo de la moitié sud-est de Verdun SO en 2024 (IGN 2024 ne les montre pas nettement ;
  31d16b8e -113 les montre en 2025 : présents).

## 7. Ce que la description en tire

`description.yaml` (itération 2) : centre sur la médiane réelle, axes réels des quatre branches (décalages latéraux
rapportés), passages posés par leur retrait, îlots de chaque branche, îlot central du Vercors, bretelle en îlot
directionnel derrière le grand îlot de l'angle sud, angles. Ce que le format ne sait pas dire est dans `BESOINS.md`
(traversées cyclables jaunes et vertes, ligne mixte et flèches du cœur, refuge à niveau sans rampants, bretelle longue,
angle planté en pointe).
