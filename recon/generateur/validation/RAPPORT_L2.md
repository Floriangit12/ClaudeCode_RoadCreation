# Rapport du lot L2 : nivellement, sol étanche, bordures et caniveaux (S01-S12)

*`recon/generateur/validation/RAPPORT_L2.md` — 17/10/2026. Données chiffrées : `rapport_L2.json`, `controles_L2.json`
et `constats_visuels_L2.json`, produits par `python recon/generateur/validation/faire_rapport_L2.py` (rejoue tout :
construction des HDA deux fois, fabrication et rendus de S01-S12, second processus de déterminisme, contrôles
indépendants, témoins négatifs ; aucune date ni durée écrite). Houdini 22.0.459 Indie (hython), VEX interprété (JIT
coupé), Karma XPU (husk). Base de règles lue, non modifiée : `regles_route_fr/1.0` (SHA-256 `d4d63ede…`) ;
`assets/specs/{bordures,vegetation,mobilier,carla_correspondances}.json` lus, non modifiés.*

**Statut : ok — les 14 critères sont atteints**

> **Mise à jour (étape 1, la route seule, correction après contrôle)** : `rapport_L2.json` régénéré par `faire_rapport_L2.py --sans-fabrication --journal recon/generateur/tmp/etape1_route/fabrication.log` : statut ok, 16 critères sur 16 (L2-15 et L2-16 ajoutés par la correction). pj::bordure n'est plus réutilisée telle quelle : nouvelle version **pj::bordure::2.0** (pièces d'angle des avancées et des îlots ; la 1.0 reste intacte, `hda/README_RG.md`). Rendus refaits en « route seule » (décision de l'utilisateur : rien hors de l'emprise de la route, végétation à l'étape 2). Détail : `RAPPORT_correction.md`. Le texte ci-dessous est celui du lot L2 d'origine.

## 1. Ce que le lot apporte

Une description simple (« trottoir 2 | bordure T2 + CS2 | voie ← | voie → | … », un dos-d'âne ici, un abaissé avec
BEV là) est compilée en modèle `modele_voie/0.1` (lot L0), échantillonnée par les HDA du lot L1, puis **fabriquée en
surfaces** :

```
hython recon/generateur/fabriquer_generateur.py recon/generateur/scenes_simples/S08_rue_dos_d_ane_passage.yaml --l2 --rendus
  -> recon/out/generateur/S08/l2/   sol (une nappe étanche), bordures et caniveaux en éléments, BEV, arbres,
                                    HeightField, route_l2.usda (Z haut, matériaux de la bibliothèque), mesures
  -> recon/out/generateur/S08/rendus/   rendus Karma XPU, tuiles natives
```

Trois HDA nouvelles et une nouvelle version d'HDA pj (README : `recon/generateur/hda/README_RG.md` § 5) :

- **`rg::nivellement::1.0`** : le modèle de Z unique (TQ-SOL-013) — chaussée (dévers par bande, ralentisseurs d'un
  trottoir à l'autre), caniveau (fil d'eau = arête − Δh de `bordures.json`), pied et tête de chaque bordure (vue,
  abaissés et rampants), trottoir à tête − 4 mm, bande plantée isolée à tête − 4 cm ; files de bordures chaînées
  (pièces longitudinales et retours aux avancées) ; **HeightField** au pas de 0,10 m rangé comme celui de
  `pj::lire_description` (height, r0, z1, r1, z2, r2), lu par `pj_niv_z` sans modification ;
- **`rg::sol::1.0`** : une triangulation contrainte par route (lignes de rupture, zones sous les éléments), Z de
  chaque sommet par le modèle, marches fermées par des murs cachés : **une seule nappe 2-variété** ; normales des
  faces de bande issues du gradient analytique (TQ-SOL-008) ; BEV ;
- **`rg::vers_entites::1.0`** : les files de bordures au contrat de `pj::lire_description` (intervalles courant,
  chartière, bateau ; profils en long du pied et de la tête), arbres des bandes ;
- **`pj::caniveau::2.0`** : la 1.0 lisait mal les intervalles du caniveau (groupes capturants dans `re_findall`), ce
  qui l'empêchait de s'interrompre au droit des ralentisseurs et des avancées ; la 2.0 corrige la seule lecture, la
  1.0 reste intacte. `pj::bordure::1.0` est réutilisée telle quelle (jitter de hauteur réglé à 1 mm, § 6).

Houdini n'invente rien : chaque cote vient du modèle ou d'une règle citée — vue des bordures (DEF-005), profils,
bases et Δh des caniveaux (`bordures.json`, autre équipe, lecture seule), rampe des plateaux (DEF-034), dos-d'âne
(RF-MA-RAL-001), rampants (RF-MA-ABA-004), BEV (DEF-031), retraits du trottoir et des bandes plantées (TQ-SOL-013),
recouvrement sous la tête (TQ-BOR-007), arbres (DEF-030). Les choix sans règle sont dits (§ 6).

## 2. Critères

| Critère | Valeur | Seuil | Atteint |
|---|---|---|---|
| L2-1 HDA rg::nivellement, rg::sol, rg::vers_entites et pj::caniveau::2.0 (nouvelle version) : dossiers développés, signatures stables, reconstruction identique ; pj::bordure::1.0 réutilisée telle quelle | 4 / 4 ; signatures stables, dossiers identiques | 4 / 4 | oui |
| L2-2 fabrication de S01-S12 (sol, bordures, caniveaux, BEV, arbres, HeightField, USD) sans erreur | 12 / 12 | 12 / 12 | oui |
| L2-3 surfaces étanches : 0 arête libre intérieure (TQ-SOL-009) | 0 arête de bord hors contour, 0 non-variété, 0 doublon, 0 face d'aire < 1e-6 m², 0 mal orientée ; recouvrement en (s, t) 0.0e+00 m² | 0 | oui |
| L2-4 jointure entre surfaces ≤ 1 mm (marche visible hors éléments ; sol sous chaque élément) | marche visible max 0,00 mm, 0 mur visible hors élément ; 0 élément sans sol dessous | ≤ 1 mm ; 0 | oui |
| L2-5 vue des bordures = modèle ± 5 mm (dessus de l'élément − surface devant la face) | écart max 2,34 mm ; 0 sonde hors tolérance, 0 sans impact (0 sondes d'angle écartées) | ≤ 5 mm ; 0 | oui |
| L2-6 trottoirs : dévers ≤ 2 % et pente < 5 % hors rampants (A2007) | dévers max 1.503 % ; pente max 0.1539 % | ≤ 2 % ; < 5 % | oui |
| L2-7 rampants d'abaissé ≥ 1,50 m (8 %) ou ≥ 2,40 m (5 %), mesurés sur le sol fabriqué | 4 rampants, 0 non conforme | 0 non conforme (≥ 1 mesuré) | oui |
| L2-8 contrôles TQ-SOL-* applicables au sol fabriqué : 0 échec | TQ-SOL-001 (aire(union) = somme(aires) à 1e-6 m² près, 0 recouvrement ; 0 doublon, 0 face inversée) OK ; TQ-SOL-003 (lignes de rupture = arêtes contraintes) OK ; TQ-SOL-004 / TQ-SOL-013 (Z de chaque sommet = modèle unique, ≤ 1 mm) OK ; TQ-SOL-013 (6) (trottoir = tête − 4 mm ± 2 mm) OK ; TQ-SOL-013 (7) (bande plantée isolée = tête − 3 à 5 cm) OK ; TQ-SOL-008 (normales des faces de bande = gradient analytique du modèle, ≤ 0,01°, seuil interne) OK ; TQ-SOL-009 (étanchéité : 0 non-variété, 0 doublon, 0 aire < 1e-6 m², bords sur l'emprise seulement, 99 % des triangles à angle min ≥ 20°) OK ; hors périmètre L2 : TQ-SOL-002 (règle de génération : appliquée par les paramètres de rg::sol, angle 25°, arête min 0,02 m, arête cible 0,25 m ; tuiles hors lot), TQ-SOL-007 (MNT des abords), TQ-SOL-010 à 012 (Unreal), TQ-SOL-014 (carrefour, lot L3) ; TQ-BOR-001, 003, 004, 006 (Unreal) | 0 échec | oui |
| L2-9 contrôles TQ-BOR-* applicables : 0 échec | TQ-BOR-002 (éléments rigides, coupe ≥ 0,20 m) OK ; TQ-BOR-005 (joints non transparents, 0 échec) OK ; TQ-BOR-007 (sol sous chaque élément ; caniveau affleurant ± 3 mm) OK (4530 éléments, 2472 joints, 14832 rayons) | 0 échec | oui |
| L2-10 relief et accessoires : ralentisseurs en relief, BEV, terre-plein planté, arbres (DEF-030) | ralentisseurs 2 (S08 1, S10 1) au Z du modèle ; BEV 4 / 4 (écart max 0,00 mm) ; retrait planté 38,84 mm à 41,15 mm ; arbres 27 / 27 (écart max 0,00 mm, axe à 1.5 m au moins du bord de chaussée) | BEV et arbres = attendus ; écarts ≤ 1 mm ; axe ≥ 1,50 m | oui |
| L2-11 HeightField de nivellement (README_HDA § 2, sortie 2 de rg::nivellement) : Z lu par pj_niv_z aux sommets visibles du sol (seuil interne : tolérance de vue, 5 mm) | 12 / 12 ; 798982 points, 0 sans région ; écart max 3,12 mm, p99 1,88 mm | 12 / 12 ; 0 sans région ; ≤ 5 mm | oui |
| L2-12 déterminisme (deux processus identiques à l'octet : l1/ et l2/) | déterminisme : identique (204 fichiers ; .usda : chemins relatifs des matériaux normalisés) | identique | oui |
| L2-13 rendus Karma XPU de S01-S12 regardés en tuiles natives | 12 / 12 rendues ; 12 / 12 regardées ; 35 tuiles regardées sur 119 | 12 / 12 | oui |
| L2-14 témoins négatifs détectés par le contrôle indépendant | 8 / 8 : une face de chaussée retirée du sol (S02) → 3 arêtes de bord hors contour ; un sommet de chaussée relevé de 2 mm (S02) → écart Z max 2.000 mm ; trottoirs de S02 basculés de 3 % en travers → dévers max 4.50 % ; trois éléments de bordure de S02 posés 6 mm trop haut → 1 sondes hors ± 5 mm ; un joint de S08 vu à travers (impact à 0,60 m derrière la face) → 1 échec ; un élément de caniveau de S08 posé 5 mm trop bas → 1 hors ± 3 mm ; une bande d'éveil de vigilance de S08 retirée → 1 BEV pour 2 attendues ; un arbre de S03 déplacé de 0,30 m → écart de position max 0.300 m | 100 % | oui |

Les critères du plan (§ 3, L2) sont L2-3 à L2-9 et L2-13 ; L2-10 et L2-11 vérifient les objets du lot (relief,
abaissés, BEV, terre-plein, arbres ; HeightField du contrat de branche) ; L2-1, L2-2, L2-12 et L2-14 vérifient le
livrable et la capacité du contrôle à trouver une erreur.

## 3. Mesures

**Méthode, indépendante du VEX.** Houdini ne fait que fabriquer et sonder : `fabriquer_l2.py` exporte le sol
(`sol_*.npy`), les niveaux, les entités, les éléments posés par pj::bordure et pj::caniveau, et des **sondes sur la
géométrie fabriquée** (`hou.Geometry.intersect`) : dessus de chaque élément, sol 4 mm devant la face, sol 3 cm
derrière l'arrière, sol sous l'élément, affleurement des caniveaux, six rayons par joint depuis 1,2 et 1,6 m de haut
à 2, 5 et 10 m. Les valeurs attendues sont recalculées en Python par `validation/analytique_L2.py`, qui relit le
modèle et réécrit le nivellement (TQ-SOL-013) sans code commun avec `rg_niveau.h` ; `validation/controler_L2.py`
compare :

| Contrôle | Résultat (12 scènes) |
|---|---|
| Étanchéité (TQ-SOL-009) | 1624921 faces (dont 23544 murs cachés) ; 0 arête de bord hors du contour, 0 non-variété, 0 arête mal orientée, 0 doublon, 0 face d'aire < 1e-6 m² ; 99,985 % des triangles visibles au moins (seuil 99 %) ont un angle minimal ≥ 20° |
| Recouvrement (TQ-SOL-001) | somme des aires − aire de l'union en (s, t) : 0.0e+00 m² (seuil 1e-6) ; 0 face inversée ; aire contre contour intégré : 3.4e-08 relatif |
| Z du sol visible contre le modèle (TQ-SOL-004, TQ-SOL-013) | 834106 sommets, écart max 0,000 mm ; marche visible hors élément : 0 (max 0,000 mm) |
| Lignes de rupture (TQ-SOL-003) | 0 face visible traversant une ligne de rupture (tolérance 1e-5 m, 1e-4 en float32) |
| Normales (TQ-SOL-008) | 452184 sommets de faces de bande, écart au gradient analytique max 0,00045° |
| Vue des bordures | 7404 sondes, écart max 2,34 mm, 0 hors ± 5 mm, 0 sans impact |
| Trottoir sous la tête (TQ-SOL-013 (6)) ; bande plantée (7) | écart au retrait attendu max 1,18 mm (± 2 mm) ; bande plantée de S06 : 38,8 mm à 41,2 mm sous la tête (3 à 5 cm) |
| Trottoirs : dévers et pente (A2007) | dévers max 1,503 % (≤ 2 %), pente max hors rampants 0,154 % (< 5 %) |
| Rampants d'abaissé (S08) | 4 rampants : 2,400 m à 5,00 % chacun (dénivelé 120 mm) ; 0 non conforme |
| Joints (TQ-BOR-005) | 2472 joints, 14832 rayons, 0 échec (impact à plus de 0,30 m derrière la face ou dans le vide) |
| Éléments (TQ-BOR-002) ; sol sous les éléments, caniveaux (TQ-BOR-007) | 4530 éléments posés, 0 coupe < 0,20 m ; 0 élément sans sol dessous ; 0 caniveau hors ± 3 mm |
| BEV (S08, S10) ; arbres (S03, S06) | BEV 4 / 4 (étendue s0-s1, 0,50 m du nez, 0,5875 m de profondeur, dessus 3,0 à 3,0 mm au-dessus du trottoir, 1666 plots) ; arbres 27 / 27, écart 0,000 mm, axe à 1,50 m au moins du bord de chaussée |
| HeightField (`pj_niv_z` aux sommets visibles) | 12 / 12 ; 798982 points, 0 sans région ; écart max 3,12 mm, p99 1,88 mm |

Écarts résiduels attendus : la vue mesurée porte le jitter de hauteur de pj::bordure (± 1 mm) et la sonde du dessus
tombe sur le chanfrein près des abouts ; le HeightField, interpolé bilinéairement au pas de 0,10 m, s'écarte du sol
exact d'au plus quelques millimètres, pour l'essentiel sur les lignes de rupture (arête du caniveau, couronne).

## 4. Témoins négatifs

- une face de chaussée retirée du sol (S02) → 3 arêtes de bord hors contour : détecté
- un sommet de chaussée relevé de 2 mm (S02) → écart Z max 2.000 mm : détecté
- trottoirs de S02 basculés de 3 % en travers → dévers max 4.50 % : détecté
- trois éléments de bordure de S02 posés 6 mm trop haut → 1 sondes hors ± 5 mm : détecté
- un joint de S08 vu à travers (impact à 0,60 m derrière la face) → 1 échec : détecté
- un élément de caniveau de S08 posé 5 mm trop bas → 1 hors ± 3 mm : détecté
- une bande d'éveil de vigilance de S08 retirée → 1 BEV pour 2 attendues : détecté
- un arbre de S03 déplacé de 0,30 m → écart de position max 0.300 m : détecté

## 5. Revue visuelle

Rendus Karma XPU de contrôle (`rendus/`, `rendu/rendu_scenes.py`) : vues générales (oblique, piéton), vues propres à
chaque scène (détail de bordure, avancées, abaissé et BEV, dos-d'âne, plateau, courbe…) et une vue de dessus à
5 cm/px, toutes découpées en tuiles natives. Les rendus viennent du passage complet de `faire_rapport_L2.py` (avec
rendus) ; le passage final (`--sans-rendus`) n'a changé que l'export du zéro signé et la comparaison de déterminisme,
pas la géométrie. 35 tuiles regardées sur 119 produites, 12 scènes sur 12, plus deux agrandissements ciblés. Constats (`constats_visuels_L2.json`) : nivellement, bordures,
caniveaux, abaissés, BEV, ralentisseurs, terre-plein et arbres conformes sur les 12 scènes ; défauts relevés :

- angles des avancées (S03) : abouts droits sans onglet ni pièce d'angle ; l'about à l'ombre se lit comme un
  triangle sombre (pj::bordure n'applique l'onglet qu'aux angles qui ne portent pas aussi un changement
  d'intervalle) ; aucun jour (0 rayon traversant) ;
- décor : liseré sombre au bord extérieur des abords (marche entre le bord du modèle et le plan de décor) ;
- matériaux corrigés pendant la revue : gazon de la bibliothèque brillant comme de l'eau (carte de rugosité
  inversée, moyenne 0,26 : inversée au rendu) ; dalles « claires » de S05 rendues sombres (alias porté sur
  `dalles_beton_40`) ;
- marquages absents (lot L4) : bandes cyclables, couloir bus, zébra et passages ne se lisent pas encore.

## 6. Écarts au plan, interprétations et règles manquantes

- **Scène E du plan (ex05)** : non fabriquée au lot L2. Son profil met une piste entre deux bordures à un niveau
  intermédiaire (profil de bordure `autre`, trois niveaux) : le modèle de Z ne connaît que bas / haut (+ plantée) ;
  `rg::nivellement` refuse ce cas par une erreur explicite. Lot fait sur S01-S12 comme demandé.
- **`pj::sol` non utilisé** : il triangule un relevé de site (polygones de surfaces, Z lu dans un HeightField à
  0,10 m) ; le sol généré doit porter les lignes de rupture du modèle (TQ-SOL-003) et le Z exact de chaque sommet
  (TQ-SOL-004). `rg::sol` sort le même contrat (maillage Y haut, `materiau_id`, `pj_couche`, `pj_entite`, N, uv).
- **pj::bordure::1.0, jitter de hauteur** : 1 mm au lieu de 2 (paramètre de l'HDA) pour tenir ensemble TQ-SOL-013 (6)
  (trottoir = tête − 4 mm ± 2 mm) et la vue ± 5 mm.
- **Interprétations** (sans règle écrite) : ralentisseur d'un trottoir à l'autre, la bordure ne bouge pas et le
  caniveau est interrompu et relevé au droit du ralentisseur ; abaissé couvert par un plateau (S10) réalisé par le
  plateau lui-même ; avancée de trottoir au niveau du trottoir, plan tendu entre la tête de sa bordure et le
  trottoir ; retours de bordure à vue linéaire posés en raccords de vue (« chartière » de pj::bordure, éléments de
  1,00 m au plus) ; trottoir abaissé sur toute sa largeur quand il fait 2 m ; premier arbre d'un alignement « de X »
  à X (phase comptée depuis le début de l'intervalle).
- **Règles manquantes ou à compléter** : raccord latéral du dos-d'âne à la bordure et au caniveau (NF P98-300 non
  lue, payante ; le décret 94-447 ne donne aucune cote) ; ouverture visible d'une fosse d'arbre dans un trottoir revêtu
  (seuls le volume 9-12 m³ et la fosse de 3 × 3 m sont écrits : RF-GV-TPC-010, DEF-030) ; traitement des angles de
  bordure (pièce d'angle ou onglet) ; ces points sont à porter dans `regles_route_fr.json` par son propriétaire.
- **Karma XPU 22.0.459** : une caméra USD orthographique ne lance aucun rayon et husk ne rend pas la main (mémoire
  > 20 Go) ; la vue de dessus est une perspective depuis 2 000 m (parallaxe ≤ 5 mm pour 15 cm de relief), et chaque
  appel à husk a désormais une garde de durée.
- **Bibliothèque de matériaux** : `assets/lib/materiaux/gazon_tondu` a une carte de rugosité inversée (à corriger à
  la source ; inversée au rendu en attendant).
- **Déterminisme** : comparaison à l'octet de tous les fichiers `l1/` et `l2/` des deux processus, avec deux
  traitements dits : dans `route_l2.usda`, les références aux matériaux sont relatives au dossier de sortie, dont la
  profondeur diffère pour le second processus (« ../ » ramenés à « <depot>/ » avant comparaison) ; à l'export du sol,
  le zéro signé est ramené à +0,0 (sur S10 et S11, t valait −0,0 ou +0,0 selon le processus en 1 à 2 points de la
  ligne de référence : même nombre, signe du zéro seul). Les rendus (bruit de Monte-Carlo de Karma) ne sont pas
  comparés.
- **Triangulation** (TQ-SOL-002, règle de génération) : arête cible 0,25 m partout (la plus fine des deux valeurs de
  la règle), arête minimale 0,02 m (avec 1 mm, le croisement rasant d'une limite de bande et du bord d'un caniveau dans
  le biseau de S09 donnait 218 aiguilles d'aire < 1e-6 m², refusées par TQ-SOL-009).
- **Contrôles L1 et L0 rejoués** après les corrections du compilateur (caniveau gardé au changement de profil de S09,
  phase des arbres) : `rapport_L0.json` inchangé, `rapport_L1.json` inchangé hormis l'ordre des dossiers d'HDA (le
  script L1 ne compte plus que ses trois HDA).

## 7. Fichiers

- HDA : `recon/generateur/hda/{rg_nivellement,rg_sol,rg_vers_entites}/` (construire.py, dossier .hdalc),
  `recon/generateur/hda/pj_caniveau_v2/`, `recon/generateur/hda/commun/vex/rg_niveau.h`, `README_RG.md`.
- Pilote : `recon/generateur/fabriquer_generateur.py` (`--l2`, `--rendus`), `recon/generateur/fabriquer_l2.py`,
  `recon/generateur/rendu/{rendre_l2,rendu_scenes,decor}.py`, `recon/generateur/commun/determinisme.py`.
- Contrôle : `recon/generateur/validation/{analytique_L2,controler_L2,faire_rapport_L2}.py`, `rapport_L2.json`,
  `controles_L2.json`, `constats_visuels_L2.json`.
- Sorties (non versionnées) : `recon/out/generateur/S01…S12/l2/` et `rendus/`.
