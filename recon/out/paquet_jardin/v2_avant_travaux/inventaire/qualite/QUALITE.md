# Qualité de la reconstruction v2 « 2026 » : causes racines et définition de « terminé » pour la map avant travaux

Date : 11/10/2026. Objet : expliquer pourquoi le résultat est jugé « super mal fait » et fixer des critères mesurables pour la reconstruction de l'état avant travaux (cible « 2022 à 2025 environ »).

Périmètre examiné :
- **Fabrication HDA du site** : `recon/out/paquet_jardin/v2/fabrique_hda` (description `222b11f5…`).
- **Rendus Karma de contrôle** : `recon/pc/rendus/v2_site/*.png`, 15 vues rendues le 11/10 à 08:34.
- **Niveau Unreal `PJ_2026`** : captures `recon/out/paquet_jardin/v2/ue_pilote/*.png` du 10/10.
- **Rapport du contrôleur** : `recon/out/paquet_jardin/v2/controle/RAPPORT_REGLES.md` et `rapport_regles.json`, 11/10 à 08:34.
- **Documentation** : `recon/pcg/README.md`, `recon/pcg/houdini/README.md`, `recon/pcg/houdini/hda/README_HDA.md`, `recon/out/paquet_jardin/package/donnees/relief/README_relief.md`.

Aucun fichier existant du dépôt n'a été modifié. Toutes les sorties sont dans ce dossier (§ 8).

Repère : local = L93 − (917279,43 ; 6460289,98), z = NGF − 216,30.

---

## 1. Résumé

Le rendu est mauvais pour **six causes racines**. Aucune ne relève d'un réglage : chacune vient d'un choix de chaîne. Elles sont classées par impact.

1. **Mauvaise époque, sources mélangées.**
   - La géométrie du cœur vient du levé GAM **postérieur aux travaux**. Les Z viennent d'un « MNT 2026 » synthétique. Une partie des marquages vient du plan projet 2025. Or toutes les images calées sont **antérieures** aux travaux.
   - Mesure sur l'ortho PCRS du 10/05/2022 : hors zones modifiées, 84,8 % des bordures décrites ont une arête visible à ≤ 10 cm. Dans les zones refaites en 2025 ou construites en 2023-2024 (36 % du carré de 300 m), ce taux tombe à 58,6 %, et 15 % des points n'ont aucune arête.
   - **Les couches `vector/gam_topo_sol_*` sont identiques à `etat_2026`** (écart 0 mm, voir § 3a). Le dépôt ne contient donc aucun levé vectoriel d'avant travaux.
2. **Les rendus du site n'ont aucun matériau.**
   - `fabrique_hda/materiaux_ue.usda` contient 51 `UsdPreviewSurface` à albédo constant, sans aucune texture (`recon/pcg/houdini/fabriquer_hda.py:431-473`).
   - Le look-dev texturé de la chaîne pilote (`pj_materiaux.py` : MaterialX + CC0) n'a pas été porté dans la chaîne HDA. D'où le « gris uniforme » (planche `planche_regression_lookdev_pilote_vs_site.png`).
3. **La scène se réduit au sol.**
   - `recon/pcg/controle/rendre_controle.py:40-41` ne compose que 9 couches de sol. Les bâtiments sont des **trous** de la partition (`recon/pcg/decrire/surfaces.py:8`, `:289`).
   - Côté Karma : ni arbre, ni mobilier, ni feu, ni panneau, ni véhicule, ni horizon.
   - Côté UE : le contexte existe mais reste générique : 34 boîtes BD TOPO, 6 matériaux de façade, arbres CARLA plafonnés à 22-23 m. Surtout, **0 feu sur 13 mâts, 0 tête de feu sur 29 et 0 panneau sur environ 30** (`ue_pilote/contexte_mobilier.json`).
4. **Le niveau UE est un patchwork v2 / v1.**
   - La v2 ne couvre que la zone pilote ZP-01 (71 × 100 m, ancienne chaîne numpy via `fabrique_ue_snapshot`). Tout le reste vient du v1 :
     - bordures en murs verticaux à tête en dents de scie (119 924 triangles) ;
     - marquages vectorisés depuis le raster, en escalier (45 633 triangles) ;
     - peinture jaune drapée sur la face de bordure.
   - La fabrication HDA du site (1,22 M triangles de sol) n'a jamais été importée.
5. **Le modèle de Z est synthétique et ses défauts sont maquillés par du flou.**
   - Le MNT 2026 combine le LiDAR 2021, une chaussée lissée, des hauteurs standard et un régalage harmonique, sur une grille de 0,10 m.
   - Puis `pj_sol` applique des raccords et 40 itérations d'*Attribute Blur*, et retire des triangles « falaises ». Résultats :
     - ondulations, plis et trous ;
     - trottoirs à plus de 8 % sur 2 m pour 30 % de leur aire (p95 : 14,4 %) ;
     - pied de bordure − MNT : p95 24 cm ;
     - 76 cuvettes (1 150 m²) sans avaloir.
6. **La « définition de terminé » était la conformité normative, pas la ressemblance.**
   - 255 règles et 128 contrôles ont relevé 4 383 violations. Mais aucun ne mesure la similarité avec une photo, la présence de texture ou de contexte, ou la position par rapport à l'image, hormis la corrélation NCC sur 194 marquages.
   - Seules **13 photos Panoramax** ont une pose acceptée (8 du 18/05/2025, 5 du 24/08/2024), et seules 2 planches photo / UE existent.

Causes secondaires :
- **Éclairage.**
  - Le ciel Karma est gris : RVB (0,46 ; 0,50 ; 0,55), contre (0,65-0,79 ; 0,74-0,87 ; 0,85-0,94) sur les photos.
  - La dynamique p99 − p1 est divisée par deux (0,35-0,57 contre 0,80-0,95).
  - Le soleil est celui d'octobre (220° / 29°), alors que les photos de référence ont 235° / 53,5° (18/05/2025, 13 h 38 UTC).
- **Détails procéduraux non observés** : pontages en gribouillis, épaufrures en trous ronds, éclats posés sur l'enrobé.

Ce qui fonctionne et doit être gardé est listé au § 5.

---

## 2. Matériel examiné et méthode

| Source | Ce que j'ai regardé |
|---|---|
| `recon/pc/rendus/v2_site/` | Les 15 rendus : c_cam1-4, n1-5, p_a-p_f. Zooms à 2× sur les zones suspectes. |
| `recon/out/paquet_jardin/v2/ue_pilote/` | `planche_karma_vs_ue`, `planche_panoramax_{e5d79de9,9834f494}`, `planche_corrections_revue`, `planche_revue_pieton`, `planche_contexte_pilote`, `ctx_cam1-4`. Zooms à 1920 px. |
| `recon/out/paquet_jardin/v2/fabrique_hda/controle/` | `integration_site.png`, `integration_rue.png` |
| `recon/pc/rendus/v2_pilote/` | Rendus Karma de la chaîne pilote du 10/10 (comparaison du look-dev) |
| Contrôleur | `RAPPORT_REGLES.md` et les mesures de `rapport_regles.json` (TQ-SOL-009, VAL-SOL-009, GA-TRO-004, TQ-SOL-013, VAL-KRB-005, GA-BOR-005, VAL-IMG-007…) |
| Ortho | PCRS 5 cm du 10/05/2022, mosaïquée sur le carré de 300 m |
| Photos | 5 vignettes perspectives (90°, 960 × 640) extraites de 4 photos Panoramax 360° calées (`enrichi/poses/poses.json`), dans `photos_non_versionnees/` |

Mesures nouvelles, toutes dans `mesures_qualite.json`, avec les scripts dans `outils/` :
- **M-A : bordures décrites et arêtes de l'ortho 2022.**
  - Chaque bordure est échantillonnée tous les 1 m. On prend un profil perpendiculaire de ±0,6 m, moyenné sur 0,5 m.
  - La mesure est la distance au maximum local de gradient le plus proche (seuil : 60 niveaux/m).
  - La zone de travaux est formée des surfaces `etat ∈ {modifie_2025, construit_2023_2024}` de `package/donnees/surfaces/surfaces_2026.geojson`, élargies de 1,5 m.
  - C'est un indicateur indulgent (n'importe quelle arête proche compte), mais discriminant.
- **M-B : classes de surface et verdure de l'ortho 2022.**
  - On calcule la part de pixels verts (ExG > 0,06) dans chaque surface, hors zone de travaux et hors canopée LiDAR.
- **M-C : photo et rendu au même point de vue.**
  - Rendu Karma (CPU, 16 spp) d'une copie de `fabrique_hda` faite le 11/10 à 08:41, aux 5 poses calées.
  - On mesure l'énergie du laplacien et l'écart type sur une bande de chaussée, la couleur moyenne du ciel (12 % supérieurs), la dynamique p99 − p1 et la saturation du sol.
- **Pixel → sol.** Les coordonnées des défauts vus dans les rendus sont obtenues par lancer de rayon sur la grille du sol fabriqué (`controle/cache/sol_grille.npz`), avec `outils/pix2sol.py`.

---

## 3. Défauts classés

Format des exemples : image (pixel x, y) → coordonnée locale (x ; y) en m.

### (a) Données et description

| # | Défaut | Exemple | Cause racine | Correctif |
|---|---|---|---|---|
| a1 | **La géométrie est celle d'après travaux, alors que toutes les images sont d'avant.** | Voir le détail sous le tableau. | Voir le détail sous le tableau. | Description **datée** (`date_cible`), toute source postérieure exclue (§ 7). |
| a2 | **Aucun levé vectoriel d'avant travaux.** Les 18 couches `data/sites/paquet_jardin/vector/gam_topo_sol_*` viennent du même DWG que `etat_2026` (`/sigdata/Planotheque/esp_publics/MEYLAN/PLAN_GLOBAL/Meylan_Topo.dwg`). | Bordures 622/622, lignes de marquage 409/409, limites de revêtement 429/429, caniveaux 12/12. Après reprojection WGS84 → L93, 0 % des points sont à plus de 5 cm de l'autre couche (échantillon tous les 0,25 m). | Un même export du levé, à deux dates d'extraction : le contenu est le même. | Ne pas compter sur `gam_topo_sol` pour l'avant-travaux. Hors des zones modifiées, il reste valide : il correspond à l'ortho 2022 (M-A). Dans les zones modifiées, retracer depuis l'ortho 2022, les couches `*_pcrs`, le LiDAR 2021 et les photos. |
| a3 | **Z venant d'un « MNT 2026 » synthétique.** | Voir § 3b, b4. | `recon/pcg/decrire/commun.py:121-134` lit `heightmap_3025_10cm` = `dtm_2026_10cm.tif`. D'après `README_relief.md`, ce MNT combine le sol nu 2021, une chaussée lissée 2026, des anciennes chaussées « arasées + hauteur standard » et le chantier des Saules Blancs « régalé par interpolation harmonique ». | Pour l'avant-travaux, partir de `dtm_sol_10cm.tif` (sol nu LiDAR 2021, classe 2), plus des surfaces de projet planes (dévers) là où le LiDAR est bruité. |
| a4 | **La partition des surfaces vient du raster v1 et ses classes sont a priori.** | Voir le détail sous le tableau. | `surfaces.py`, fermetures `limite_raster` ; aucune source vectorielle pour ces limites. | Limites tirées des couches PCRS (`gam_limite_voirie_pcrs`, `gam_changement_revetements_pcrs`, `gam_accotement_pcrs`), de l'ortho et d'OSM. Places de stationnement et allées comme entités. Matériaux mesurés sur photos datées. |
| a5 | **Objets absents de la description.** | Aucun avaloir ni tampon (GA-CHA-004 : `avaloirs_decrits = 0`, 76/76 cuvettes sans exutoire). `ponctuels_sol` ne contient que 12 BEV. Feux, panneaux et mobilier n'existent pas dans la description de sol fabriquée, donc pas dans Karma. | La description v2 a été centrée sur le sol (phases 1 à 3) ; la phase 5 (signalisation) n'a pas commencé. | Familles `ponctuels_sol` (tampons et avaloirs visibles sur l'ortho 5 cm) et `signaux` / `mobilier` (OSM `traffic_signals`, `road_signs`, `street_lamps`, photos) dès la v0 de l'avant-travaux. |
| a6 | **Marquages incertains ou mal ancrés.** | Voir le détail sous le tableau. | Les détecteurs sur l'ortho ont une précision limitée (contraste 2022 médian 0,42). Le drapé d'une marque ne vérifie pas son support. | Seuil de NCC et d'IoU par marque (§ 6). Coupure aux bordures et aux trottoirs dans la description. |

**a1 en détail : géométrie d'après travaux.**
- Exemples :
  - `planche_n1_rendu2026_vs_ortho2022.png`, cadres c et d : en 2022, deux refuges centraux existaient, vers (−7,6 ; −10,1) et (−4,3 ; 5,7). Dans la description, ils sont recouverts de chaussée. Inversement, la description contient le refuge long du TPC NE (≈ 14,6 ; 11,9) et l'îlot (≈ 8,7 ; 5,7), qui sont de 2025.
  - `photos_non_versionnees/planche_photo_vs_karma_2026.png`, vue `2ab4efbc_sw` (photo du 24/08/2024, caméra (−10,6 ; −3,9), cap 225°) : les bordures décrites traversent la chaussée et la bande ocre de 2024.
  - Même planche, vue `aa9d7e12_sw` : un zigzag de bus de 2025 est dessiné (MZ-5299 (−39,5 ; −33,3), MZ-5300 (−55,1 ; −71,0)).
- Cause racine :
  - La priorité de fusion place le « levé GAM 2026 d'abord » (`recon/pcg/README.md` § Marquages, `decrire/sol_site.py`).
  - Origine de la géométrie des bordures : 419/504 du GAM, 8 du plan 2025, 23 a priori.
  - Origine des 404 marquages : 154 du GAM, 52 du plan 2025, 9 de règles. 139 portent `zone_etat = neuf_2025`.
  - Les marques encore visibles en 2022 ont été retirées comme fantômes : 109 hypothèses `retire_fantome`, 309 marques v1 « retire ».

**a4 en détail : partition raster et classes a priori.**
- 279 surfaces portent `limite_raster` (40 510 m², 54 % de l'aire décrite). Il y a 3 144 m de fermetures sans source.
- Origine de la classe : a priori pour 766 surfaces sur 1 410. Origine du revêtement : a priori pour 767.
- Matériau des bordures : a priori pour 499 sur 504.
- Les grands aplats ne contiennent aucun détail : parkings 21 793 m², espaces verts 24 232 m². Exemple : c_cam1 (1050, 760) → aplat du secteur est, vers (51 ; −6).
- En revanche, les classes sont cohérentes avec l'ortho 2022 hors travaux : seulement 668 m² incohérents sur 29 870 m² contrôlés (2,2 %). Exemples d'écarts : S-0121a (chaussée verte), S-0114 (espace vert minéral).

**a6 en détail : marquages incertains ou mal ancrés.**
- Corrélation des lignes tirées de l'ortho 2022 avec le contraste de l'ortho (VAL-IMG-007) : médiane 0,35, avec 84 marques sur 194 en violation.
- Marques sur trottoir (MQ-DET-010) : 59, par exemple ML-5139, 10,4 m² vers (113,5 ; 94,5).
- Marques sur bordure (TQ-MQG-014) : 14, par exemple ML-0121, 1,22 m².
- ML-5253 est fabriquée à 166 mm de large au lieu de 120 mm (+108 % d'aire).

### (b) Géométrie fabriquée (HDA `pj::*`)

| # | Défaut | Exemple | Cause racine | Correctif |
|---|---|---|---|---|
| b1 | **Trous et recouvrements de sol** | p_e (765, 382) → trou de 0,02 m² dans le remplissage de I-0390 à (1,7 ; −13,0), au contact de S-B0390. Sol : 4 trous (0,16 m², pire S-0161a (−138,6 ; −88,3)) et 1 101 nœuds de recouvrement > 3 mm (11 m² ; 27 grappes en comptant tous les écarts ; pire T_02_02 S-0312c / S-0301a (−23,8 ; −15,7) 0,86 m²) : TQ-SOL-009 bloquant sur 14 tuiles sur 36. | Chaque surface est triangulée seule (README_HDA § 8). Les limites voisines viennent de deux régularisations (D2 / D3). Les trous d'emprise (mâts) ne sont comblés que sous 2 m². `pj_sol` retire les triangles « falaises » (`hda/pj_sol/construire.py:233-248`) et laisse un vide. | Partition **topologique** : un arc partagé maillé une seule fois, contraint dans une triangulation unique par tuile. Interdire tout retrait de triangle : corriger le Z en amont. Contrôle « 0 m² » en sortie de la description (pas seulement de la fabrication). |
| b2 | **Ondulations, plis et taches d'ombrage** au pied des bordures et dans les remplissages | p_a (830, 520) → (27,4 ; 14,6), plis perpendiculaires à la bordure. p_e : plis du remplissage. n1 (1340, 950) → taches sombres sur la piste brune vers (23,9 ; −15,0). | Les marches du modèle de Z sont **masquées par du flou** : raccords additifs Δ(s)·w(d) sur 0,3 à 3 m, puis 4 passes d'*Attribute Blur* de 40 itérations sur des anneaux de 2 à 8 voisins (`hda/pj_sol/construire.py:197-231`, paramètre l. 67). Les normales lissées à 30° étalent l'ombrage. | Sol construit sur des **surfaces de conception planes** par surface (plan ou profil en travers à dévers constant, raccordé aux lignes de bordure) au lieu d'un MNT corrigé. Plus aucun flou de Z. |
| b3 | **Raccords de bordures** (bouts, T, coudes) | p_b (1330, 300) → bout coudé avec ressaut vers (16,8 ; −0,7). c_cam1 : bouts de bordure isolés. GA-BOR-005 : 326 contacts sur 449 en défaut (pied > 1 cm : 310 ; tête > 2 cm : 149 ; dessus fabriqué > 2 cm : 158). | Le levé est découpé en 504 tronçons (dédoublonnés, jonctions `sol_lacunes`). Les hauteurs de vue viennent de sources différentes à chaque bout (LiDAR, règle, xodr). Aucun graphe de bordures (nœuds partagés). | Un **graphe de bordures** : nœuds partagés, hauteur imposée au nœud, profils raccordés par chartière ou quart de rond. Contrôle GA-BOR-005 à 100 %. |
| b4 | **Pentes et Z irréalistes** | n3 (1250, 250) → trottoir NE S-0213a vers (79 ; 45) : 1 427 m² au-dessus de 8 % sur 2 m et 11 marches de plus de 2 cm (GA-RES-001). Voir le détail sous le tableau. | MNT 2026 (a3) sur une grille de 0,10 m « sans lissage des marches » (README_HDA § 8). Le bruit LiDAR de ±2 cm et les hauteurs standard créent des marches que la fabrication corrige localement. | Z par **conception** : profil en long, dévers de 1,5 à 2 % vers le fil d'eau, fil d'eau continu vers des avaloirs décrits. Le LiDAR 2021 ne sert qu'à caler et contrôler (§ 6, G3). |
| b5 | **Épaufrures en trous ronds** sur la face des bordures | p_a (700, 1000) et (640, 860) | `hda/pj_bordure/construire.py:361-372` : sphère polygonale (freq 3) bruitée puis soustraite par Boolean, d'où des cratères hémisphériques et non des éclats d'arête conchoïdaux. | Éclats d'arête : plans de coupe obliques ou Voronoi le long des arêtes uniquement, densité selon l'âge observé. Ou simple masque de normales et d'albédo dans le matériau. |
| b6 | **Éclats épars posés sur l'enrobé**, qui se lisent comme des déchets | p_b (250, 585) → (16,5 ; 3,2). p_e (420, 1060). p_d (660, 450) → (11,7 ; −4,1). | `pj_ilot` `eclats_debordement` : 397 éclats sur tout le site, posés même là où aucune photo n'en montre, et rendus au matériau constant. | Pas de débordement par défaut. Seulement s'il est **observé** sur photo datée, avec le matériau du remplissage. |
| b7 | **Bord du monde visible** | n3 (1250, 250) → (108 ; 43) : fin d'emprise en paroi grise, puis le vide. | Emprise carrée de ±150 m sans terrain périphérique (`rendre_controle.py` ne charge pas de décor). | Anneau de terrain, de bâtiments et d'arbres simplifiés jusqu'à 500 m au moins, plus un horizon (relief lointain). |
| b8 | **Courbes** | Plutôt bon : la description est régularisée en droites et arcs G1 (README pcg § Régularisation). Restent des coudes aux jonctions (b3) et les nez d'îlot avec éclats de surface (p_e). | Voir b3. | Garder la régularisation G1. Ajouter les mêmes primitives aux **limites de surfaces** issues du raster (a4). |

**b4 en détail : pentes et Z irréalistes.**
- Sur tous les trottoirs (GA-TRO-004) : 30 % de l'aire dépasse 8 % sur 2 m, p95 14,4 %. Le modèle décrit est déjà à 29,4 %.
- 76 cuvettes couvrent 1 150 m² (VAL-SOL-009). Pire cas : S-0161a, 337 mm vers (−118,8 ; −41,5).
- Pied de bordure − MNT (TQ-SOL-013) : p50 7,2 cm, p95 24,2 cm, maximum 63,6 cm. Pire bordure : K-0380 vers (−53,9 ; −38,5).
- Vue des bordures − LiDAR (VAL-KRB-005 b) : p95 7,5 cm.

### (c) Matériaux et look-dev

| # | Défaut | Exemple | Cause racine | Correctif |
|---|---|---|---|---|
| c1 | **Gris uniforme sans aucune texture** dans tous les rendus du site | Les 15 vues de `v2_site`. `planche_regression_lookdev_pilote_vs_site.png` : mêmes caméras, pilote texturé du 10/10 contre site plat du 11/10. M-C, énergie du laplacien sur la chaussée : photo de 14,3 à 37,2 ; rendu de 5,2 à 7,9 (ce résidu n'est que du bruit de rendu). | `fabriquer_hda.py:431-473` (`ecrire_materiaux`) : `diffuseColor` = `albedo_cible_lineaire` et rugosité constante, sans texture. `rendre_controle.py:40-41` compose cette couche, pas `materiaux_v2.usda` (MaterialX de `pj_materiaux.py`). | **Une seule source de matériaux** pour Karma et UE : réseau MaterialX texturé (albédo, normale, rugosité, AO en tuilage hexagonal) pour chaque `materiau_id`, lié en `material:binding` complet, et `MI_<id>` côté UE. Un contrôle refuse tout matériau sans texture. |
| c2 | **Ni usure, ni reprises, ni salissure, ni peinture fatiguée** | Photos `119d9094_ne` et `2ab4efbc_sw` : fissures pontées, reprises de tranchée, taches, zébras et bandes ocre délavés. Les rendus montrent un enrobé neuf et une peinture blanche pleine. | L'attribut `usure` de la description n'est traduit qu'en 5 albédos constants `PJ_Peinture_*_u0..uF`. Aucune carte d'usure ni d'entretien n'est tirée des images. | Masques d'usure et de reprises **observés** (ortho 5 cm 2022 et 2024, photos datées) projetés en UV monde. Peinture modulée par l'indice de contraste mesuré (médiane 0,42, `marquages/contraste_par_tuile.json`). |
| c3 | **Albédos relatifs faux** | `ue_materiaux/rapports_photos_rendus.json` : bordure / enrobé = 4,48 sur la photo 3 contre 1,01-1,21 dans le rendu ; gravier / enrobé = 2,79 contre 1,16. | Albédos cibles saisis par matériau, non calés sur les photos datées du site. | Calage colorimétrique sur les photos calées (charte : enrobé, bordure, peinture), tolérance ±15 % sur les rapports (§ 6, M2). |
| c4 | **Remplissages d'îlots en aplat** | p_d : BRF brun uni. p_e : gravier gris uni. | La couverture dense (Scatter + Copy) est désactivée, simple « aperçu » (README_HDA § 8, limites). Le matériau est constant. | Texture du remplissage (CC0 WoodChips, gravier), plus une dispersion PCG dans UE. |
| c5 | **Détails procéduraux non observés** dans UE | `revue_pieton_nord_est`, `a_pieton_file_joints` : pontages en traits noirs ou blancs sinueux qui croisent trottoir et chaussée. | `recon/pcg/houdini/pj_decals.py:114-124` : motif statistique « d'entretien », 0,10 m/m², aléatoire par graine. | Aucun détail sans preuve : les pontages et reprises viennent de l'ortho 5 cm ou des photos, sinon rien. |

### (d) Éclairage et rendu

| # | Défaut | Exemple | Cause racine | Correctif |
|---|---|---|---|---|
| d1 | **Ciel gris, image plate et terne** | Voir le détail sous le tableau. | Voir le détail sous le tableau. | Pour la validation : HDRI réel (ciel clair de mai, CC0) ou ciel physique, sans gains de balance appliqués au ciel, avec la courbe de tons standard (ACES ou AgX). La lumière du rendu est jugée **contre la photo** (M-C). |
| d2 | **Date et soleil incohérents avec les références** | Rendus et UE : 10 octobre, azimut 220°, hauteur 27,6-29°, feuillage d'automne (UE). Photos calées : 18/05/2025 à 13 h 38 UTC (soleil à 235,2° / 53,5°) et 24/08/2024 à 15 h 10 UTC (249,9° / 33,6°). `planche_panoramax_e5d79de9` : contre-jour UE et ciel brûlé, alors que la photo est éclairée de trois-quarts. | Niveau et rendus calés sur l'état « octobre 2026 » (ARCHITECTURE § 1.5). | Pour chaque vue de validation, le **soleil et la saison de la photo**. Pour la map avant travaux, une date de référence au printemps ou en été 2025 (§ 7). |
| d3 | **Exposition fixe EV100 14 dans UE** | `planche_corrections_revue`, vue « Panoramax e5d79de9 avant » : ciel blanc. | Exposition fixe choisie pour les capteurs (`ue_pilote/niveau.json`). | Garder l'exposition fixe pour les capteurs, mais la valeur EV doit venir de la luminance réelle de la scène à la date et à l'heure (mesurée sur la photo de même pose). |

**d1 en détail : ciel gris, image plate.**
- Exemples : c_cam2, c_cam3, c_cam4 et n2 à n5.
- Mesures M-C :
  - ciel Karma (0,46 ; 0,50 ; 0,55) contre (0,65-0,79 ; 0,74-0,87 ; 0,85-0,94) sur les photos ;
  - dynamique p99 − p1 : 0,35-0,57 contre 0,80-0,95 ;
  - saturation du sol : 0,06-0,15 contre 0,16-0,24.
- Aucune ombre portée, faute d'objets.
- Cause racine :
  - Ciel procédural « ciel_clair.hdr » : zénith désaturé (0,30 / 0,42 / 0,70).
  - Balance des blancs calculée sur une carte grise sous soleil et ciel, ce qui neutralise le bleu.
  - Exposition EV 0,2 et épaule à 0,6 (`rendre_controle.py:43-45`, `pj_rendu.py`).
  - Scène sans volumes.

### (e) Contexte

| # | Défaut | Exemple | Cause racine | Correctif |
|---|---|---|---|---|
| e1 | **Karma : aucun élément vertical** | Toutes les vues : pas de bâtiment, d'arbre, de lampadaire, de feu, de panneau ni de véhicule. c_cam1 (1330, 720) → trou de bâtiment vers (51 ; −6) ; (120, 560) → (−56 ; 13). `integration_site.png` : bâtiments en noir. | Les bâtiments sont des trous de la partition (`decrire/surfaces.py:8`, `:289`, `:498`). `rendre_controle.py:40-41` ne compose que le sol. Le décor v1 (`pj_contexte.py`) n'est pas repris dans la chaîne HDA. | Couches de contexte dans la même fabrication : bâtiments (§ e2), arbres, signalisation, mobilier. Le rendu de contrôle les compose toutes. |
| e2 | **UE : bâtiments génériques** | `ctx_cam1`, `ctx_cam3` (hangar gris lisse), `planche_panoramax_*` (façades sans rapport avec la photo). | 34 extrusions BD TOPO de 2 à 188 triangles de murs, 6 matériaux de façade génériques (`ue_pilote/contexte_usd.json`). Toits plats ou à pans simples. Aucune image de façade. | Hauteur à l'égout et au faîte par le LiDAR (±1 m), forme du toit par le LiDAR, façade choisie par type et couleur mesurée sur photo. Bâtiments du secteur est conformes à la date cible (construits en 2023-2024). |
| e3 | **UE : arbres** | 451 arbres CARLA. Les grands sont plafonnés : arbre_424 mesure 30,7 m dans les données et 22,5 m posé. 15 hors tolérance (6 SM_Maple_L, 3 SM_Oak_L…). Feuillage d'automne contre photos de mai et d'août. | Bibliothèque CARLA limitée à environ 23 m. Saison d'octobre. | Mise à l'échelle non uniforme bornée, ou assets PVE plus hauts. Saison de la date cible. Essences selon `gam_topo_sol_arbre_*`. |
| e4 | **Signalisation et mobilier absents (critique pour l'ADAS)** | Photos : feux véhicules et piétons, panneaux ronds bleus (B21), totem P+R, abris. UE : 58 objets posés (lampadaires, poteaux, potelets). | `ue_pilote/contexte_mobilier.json` : tout le reste est `non_substitues` : 13 mâts de feux, 29 têtes, environ 30 panneaux, 2 abris de bus, 18 poteaux de panneau, et d'autres. Aucun asset français dans la bibliothèque (ARCHITECTURE § 0). | Fabriquer les assets FR (faces PNG de `panneaux.json`, feux R11v, R12, R13c, mâts) **avant** de juger le réalisme. Positions depuis OSM, GAM et photos datées. |
| e5 | **Secteur est (Saules Blancs) en aplat** | c_cam1 (1050, 760) → (51 ; −6) : grand aplat gris, trous de bâtiments. | Le secteur a été construit en 2023-2024. Son Z est un régalage harmonique (`README_relief.md`) et ses surfaces sont a priori. | Choisir la date cible en conséquence (§ 7). Décrire le secteur depuis l'ortho IGN du 09/08/2024 recalée et les photos de 2024-2025. |
| e6 | **Pas de véhicules garés ni de vie** | Ortho 2022 : parkings pleins. Photos : files de voitures. | Hors périmètre actuel. | Facultatif pour l'ADAS (scénarios), mais utile pour la comparaison visuelle. |

### (f) Intégration UE

| # | Défaut | Exemple | Cause racine | Correctif |
|---|---|---|---|---|
| f1 | **Le niveau `PJ_2026` mélange v2 pilote et v1** | Voir le détail sous le tableau. | Voir le détail sous le tableau. | Importer **toute** la fabrication HDA du site et retirer toute géométrie v1. Le contrôle compare le hash de description du niveau à celui de Karma. |
| f2 | **Falaises de sol restantes dans le pilote UE** | `ue_pilote/fabrication_corrections.json` : 15 triangles E8 à 45-51°, dz jusqu'à 0,375 m vers (22,3 ; −10,6) (`enrobe_trottoir`). | Voir b2 et b4. | Voir b2 et b4. |
| f3 | **Houdini Engine et PCG incomplet** | Le nœud PCG « Houdini Digital Asset » n'accepte pas l'entrée « PCG Input » réglée par Python. | Paramètre protégé (README_HDA § 9.4). | Garder la voie batch hython → USD comme référence (c'est déjà le cas) et ne pas en dépendre. |
| f4 | **Matériaux définis deux fois** (Karma et UE) | Le pilote Karma (MaterialX CC0) et UE (`MI_*` CC0) divergent : `planche_karma_vs_ue`, `rapports_photos_rendus.json`. | Deux chaînes de look-dev parallèles. | Une seule définition, mesurée contre les photos (c1, c3). |

**f1 en détail : niveau `PJ_2026`.**
- Exemples :
  - `ctx_cam2` (1700, 1010) : marquage jaune drapé sur la face d'une bordure en mur vertical, tête en dents de scie (1250, 620).
  - `ctx_cam4` (1150, 800) : flèche vectorisée en escalier, fusionnée avec la ligne voisine.
  - `ctx_cam3` : bandes jaunes posées en bout de zébras blancs.
- Cause racine :
  - Le pilote UE lit `fabrique_ue_snapshot`, l'instantané de l'ancienne chaîne numpy (`recon/pcg/ue/pilote/pilote.py:8`).
  - Hors emprise ZP-01, c'est le v1 qui reste (`ue_pilote/contexte_usd.json` : `bordures_v1` 119 924 triangles, `marquages_v1` 45 633 triangles, sol v2 117 075 triangles sur la seule emprise du pilote).

---

## 4. Causes racines (synthèse)

| Rang | Cause racine | Défauts expliqués | Pourquoi elle a pu passer |
|---|---|---|---|
| RC1 | **Cible temporelle non contrôlée.** Une description « 2026 » sans aucune image 2026, où se mêlent sources 2019, 2021, 2022, 2025 et 2026. | a1, a2, a3, b4, e5, d2 | Aucune règle ne vérifie que chaque entité est datée et compatible avec la date cible. Le contrôleur juge la conformité aux normes, pas la vérité terrain. |
| RC2 | **Chaîne de rendu du site dégradée par rapport au pilote** : matériaux constants, sol seul. | c1, c4, d1, e1, b7 | Le passage aux HDA (10-11/10) a porté la géométrie, pas le look-dev ni le décor. `verifier_usd` vérifie le contrat (0 erreur), pas l'aspect. |
| RC3 | **Sol fabriqué à partir d'un MNT, corrigé a posteriori**, au lieu de surfaces de conception. | b1, b2, b3, b4, f2 | Chaque revue a ajouté un correctif local (raccords, flou, retrait de falaises, comblement des petits trous) au lieu de changer de modèle. |
| RC4 | **Description limitée au sol et au marquage.** | a5, e1, e4, e6 | Phases 4 et 5 (végétation, signalisation) repoussées, alors que ce sont elles qui portent l'essentiel de la perception « réaliste » à hauteur d'œil. |
| RC5 | **Intégration UE partielle** (pilote numpy + v1). | f1, f4, e2, e3 | Le niveau UE a été jugé sur 6 vues du pilote (ZP-01), jamais sur le site entier. |
| RC6 | **Validation sans référence visuelle.** | Toutes | 13 poses acceptées seulement, 2 planches photo / UE, aucune mesure photo / rendu automatique. La « revue indépendante » de l'ARCHITECTURE § 1.7 n'a pas été faite sur le site. |
| RC7 | **Détails procéduraux décidés par règle, sans preuve.** | b5, b6, c2, c5 | Le principe « Houdini n'invente rien » (ARCHITECTURE § 1.1) a été appliqué à la géométrie, mais pas aux détails d'aspect. |

---

## 5. Ce qu'il faut garder

- **Fidélité au tracé** : bordures posées et levé GAM, écart p95 de 1,6 cm, maximum 4,1 cm (VAL-KRB-005 a).
- **Le levé GAM reste valide hors zones modifiées** : 84,8 % d'arête ortho 2022 à ≤ 10 cm (M-A).
- **Classes de surface cohérentes avec l'ortho 2022 hors travaux** : 2,2 % d'aire incohérente (M-B).
- **Poses Panoramax calées** : les bordures projetées tombent sur les bordures réelles là où rien n'a changé (`planche_photo_vs_karma_2026.png`, vue `119d9094_sw`, bord du TPC à droite). La flèche de tourne-à-gauche tirée de l'ortho 2022 coïncide aussi.
- **Bordures** : pose en éléments, joints de 5 à 8 mm, chartières, pièces courbes. Le **look-dev du pilote** (Karma 10/10 et UE ZP-01) est crédible en vue rapprochée (`planche_karma_vs_ue.png`).
- **Déterminisme** octet par octet, contrat USD vers UE, régularisation G1, contrôleur de règles. Ce sont de bons outils, à compléter par des critères de réalisme.

---

## 6. Définition de « terminé » pour la map avant travaux

Chaque critère se mesure automatiquement et doit être rapporté avec sa valeur. La colonne « actuel » donne la mesure sur la v2 2026 quand elle existe.

### 6.1 Date et sources

| ID | Critère | Seuil | Mesure | Actuel (v2 2026) |
|---|---|---|---|---|
| S1 | Chaque entité porte `date_validite` et ses sources sont antérieures ou égales à la date cible, ou ne sont pas contredites par une image ≤ date cible | 100 % | Script de provenance sur la description | 154 marquages du GAM post-travaux, 52 du plan 2025, 139 `neuf_2025`, 1 429 m de bordures en zone de travaux |
| S2 | Part d'aire et de longueur en `a_priori` | ≤ 15 % de l'aire de sol, ≤ 10 % des bordures (matériau compris) | Manifeste | Classe a priori : 766 / 1 410 surfaces. Matériau des bordures a priori : 499 / 504 |
| S3 | Couverture photo datée dans la fenêtre cible (±12 mois) | ≥ 1 photo calée à ≤ 25 m de tout point de chaussée du cœur (r = 60 m) ; ≥ 30 poses acceptées réparties sur les 4 branches | `poses.json`, carte de couverture | 13 poses acceptées (2 dates, axe Verdun seulement) |

### 6.2 Position et géométrie

| ID | Critère | Seuil | Mesure | Actuel |
|---|---|---|---|---|
| P1 | Bordures décrites et arête de l'ortho de référence (PCRS 2022 ; IGN 2024 recalée là où 2022 est périmé) | ≥ 90 % des échantillons de 1 m à ≤ 10 cm, ≤ 3 % sans arête, p90 ≤ 12 cm | `outils/ecart_ortho2.py` (M-A) | Hors travaux : 84,8 %, p90 12,5 cm, 2,5 % sans arête. Zone de travaux : 58,6 %, p90 32,5 cm, 15,3 % sans arête |
| P2 | Marquages et image de référence | NCC ≥ 0,5 pour ≥ 90 % des marques ; IoU (marque rastérisée / masque peint de l'ortho) ≥ 0,6 ; phase des tirets p95 ≤ 0,10 m ; écart latéral p95 ≤ 0,05 m | VAL-IMG-007 étendu, nouvelle IoU | NCC médiane 0,35 ; 84 / 194 sous le seuil |
| P3 | Classes de surface et ortho (verdure, minéral) | ≤ 2 % d'aire incohérente | `outils/classes.py` (M-B) | 2,2 % hors travaux, non mesuré en zone de travaux |
| P4 | Reprojection des arêtes (bordures, bords de marquage) dans les photos calées | Médiane ≤ 3 px et p90 ≤ 8 px à 960 px / 90° (≈ 0,3° / 0,75°) sur les entités valides à la date de la photo | Projection et distance aux contours de la photo | Non mesuré. Visuellement bon hors travaux, faux au cœur |
| G1 | Continuité G1 des bordures, limites et lignes | 0 cassure > 2° hors coins voulus ; rayon ≥ rayon du gabarit | Règles GQ-* existantes, étendues aux limites de surfaces | Bordures régularisées ; limites raster non régularisées |
| G2 | Sol étanche | 0 trou > 0,005 m², 0 recouvrement > 3 mm, 0 triangle retiré (« falaise ») | TQ-SOL-009, compteur `pj_sol_falaises` | 4 trous (0,16 m²) + I-0390 (0,02 m²), 11 m² de recouvrements |
| G3 | Cohérence des Z avec le LiDAR 2021 hors zones modifiées : chaussée et trottoir − sol LiDAR | RMS ≤ 3 cm, p95 ≤ 5 cm ; pied de bordure − LiDAR p95 ≤ 3 cm ; vue des bordures − LiDAR p95 ≤ 2 cm | TQ-SOL-013, VAL-KRB-005 b | Pied − MNT : p95 24,2 cm. Vue − LiDAR : p95 7,5 cm |
| G4 | Pentes réalistes | Trottoirs : dévers 1 à 3 %, pente sur 2 m ≤ 5 % pour ≥ 95 % de l'aire hors rampes. Chaussée : dévers 1 à 4,5 %. 0 cuvette > 3 mm hors avaloir décrit | GA-TRO-004, GA-CHA-001, VAL-SOL-009 (4) | 30 % de l'aire des trottoirs à plus de 8 % ; 76 cuvettes (1 150 m²) ; 0 avaloir |
| G5 | Raccords de bordures | GA-BOR-005 à 100 % (pied ≤ 1 cm, tête ≤ 2 cm) | Contrôleur | 27 % (326 / 449 en défaut) |
| G6 | Échelle des objets | Hauteur des bâtiments et arbres comparée au LiDAR : ≤ ±1 m pour les bâtiments, ≤ 15 % pour 90 % des arbres, aucun plafonnement | Comparaison des hauteurs | Arbres UE : 96,7 % dans la tolérance, mais les grands plafonnés à 22-23 m |

### 6.3 Matériaux, éclairage et ressemblance

| ID | Critère | Seuil | Mesure | Actuel |
|---|---|---|---|---|
| M1 | Tout maillage visible a un matériau texturé (albédo, normale, rugosité), UV en mètres, sans répétition visible au-delà de 20 m (tuilage hexagonal ou macro-variation) | 100 % | Contrôle USD : aucune `UsdPreviewSurface` sans `UsdUVTexture` en rendu | 0 / 51 matériaux texturés dans la chaîne HDA |
| M2 | Rapports d'albédo (bordure / enrobé, peinture / enrobé, remplissage / enrobé), rendu contre photo à même pose et lumière | Écart ≤ 15 % | `rapports_photos_rendus.json` généralisé | Bordure / enrobé : 1,01-1,21 contre 4,48 (photo 3) ; gravier : 1,16 contre 2,79 |
| M3 | Détail haute fréquence de la chaussée (énergie du laplacien, bande devant la caméra) | Rendu ≥ 60 % de la photo, bruit de rendu soustrait | M-C | 5-8 contre 14-37 (bruit seul) |
| M4 | Usure et reprises **observées** reproduites ; aucun détail procédural sans preuve | 100 % des reprises et pontages visibles sur l'ortho 5 cm décrits ; 0 détail non sourcé | Revue de provenance | Pontages statistiques, épaufrures en sphères |
| L1 | Ciel et dynamique | Dynamique p99 − p1 ≥ 0,75 ; ciel dans ±15 % (RVB) de la photo de même pose | M-C | 0,35-0,57 ; ciel (0,46 ; 0,50 ; 0,55) contre (0,65-0,79 ; 0,74-0,87 ; 0,85-0,94) |
| L2 | Soleil, saison et feuillage de la vue de validation égaux à ceux de la photo | Azimut et hauteur à ±2° de l'éphéméride de la photo | Horodatage EXIF et calcul solaire | Octobre (220° / 29°) contre 18/05/2025 (235° / 53,5°) |
| V1 | Comparaison photo / rendu à même pose sur ≥ 30 vues : IoU sémantique (SAM sur la photo, classes UE ou Karma) | ≥ 0,7 par classe de sol (chaussée, trottoir, végétation basse, marquage) et ≥ 0,5 pour bâtiments et arbres | Planches `photo | rendu | superposition` | Non mesuré (2 planches UE) |
| V2 | Revue indépendante en aveugle (paires photo / rendu dans un ordre aléatoire, notes de 0 à 3 par critère, ARCHITECTURE § 1.7) | Moyenne ≥ 2, aucun 0, puis accord de l'utilisateur | Agent séparé | Non faite sur le site |

### 6.4 Contexte et intégration

| ID | Critère | Seuil | Mesure | Actuel |
|---|---|---|---|---|
| C1 | Bâtiments existant à la date cible | 100 % posés, aucun trou de sol visible, hauteur LiDAR ±1 m, façade par type et couleur photo | Inventaire contre BD TOPO, GAM et ortho | Karma : 0. UE : 34 boîtes génériques |
| C2 | Arbres, haies, massifs | 100 % des arbres GAM et LiDAR, essence et saison de la date cible | `contexte_arbres` | Karma : 0. UE : 451 CARLA |
| C3 | Feux et signalisation verticale | 100 % des mâts, têtes et panneaux de la date cible, positions à ≤ 0,5 m des photos | Inventaire OSM, GAM et photos | UE : 0 / 13 mâts, 0 / 29 têtes, 0 / ≈ 30 panneaux |
| C4 | Mobilier et réseaux (lampadaires, potelets, abris, avaloirs, tampons) | ≥ 95 % de l'inventaire | Idem | 58 objets posés (lampadaires, poteaux, potelets), 0 avaloir |
| C5 | Horizon et périphérie | Terrain, bâtiments et arbres simplifiés jusqu'à ≥ 500 m, relief lointain, aucun « bord du monde » visible depuis les vues ADAS | Vues de contrôle | Karma : bord visible (n3). UE : relief lointain présent |
| U1 | Le niveau UE contient exactement la fabrication du site (hash de la description identique à Karma), 0 maillage v1 | 100 % | Inventaire des acteurs, `contexte_usd` | v2 sur 71 × 100 m seulement, v1 ailleurs |
| U2 | Performance | ≥ 60 i/s en 1080p sur la RTX 5070 (Lumen) | `contexte_perf` | 68 i/s sur le pilote |

---

## 7. Recommandations pour la reconstruction avant travaux (dans l'ordre)

1. **Fixer une seule date cible**, plutôt qu'un intervalle de 2022 à 2025.
   - Proposition : le **18/05/2025**, juste avant les travaux du 23/06/2025. C'est la meilleure couverture photo (8 poses 360° acceptées, 13 Panoramax 2025-S1, 21 Mapillary 2025-S1), et la Pléiades 2025 est probablement antérieure (à confirmer).
   - Le secteur est (Saules Blancs) est alors construit (livré en 2024). Il se décrit avec l'ortho IGN du 09/08/2024 recalée et les photos de 2024-2025.
   - Le cœur, inchangé entre 2022 et le 22/06/2025 (sauf preuve contraire à chercher dans les photos de 2024-2025), se décrit avec l'ortho PCRS 2022.
   - Une date cible en 2022 obligerait à modéliser le chantier des Saules Blancs, ce qui est déconseillé.
2. **Description : réécrire les priorités de sources par date** (corrige RC1).
   - Exclure `etat_2026` et `gam_topo_sol_*` (identiques) et `plan_projet_2025` dans l'emprise des travaux, sauf pour les entités prouvées inchangées.
   - Tracer bordures et limites depuis les couches PCRS, l'ortho 5 cm, les ruptures du LiDAR 2021 et les photos.
   - Réintégrer les 109 marques `retire_fantome` et réexaminer les 309 marques v1 « retire » : ce sont les marquages d'avant travaux.
3. **Z : le LiDAR 2021 pour mesurer, des surfaces de conception pour construire** (corrige RC3).
   - Fil d'eau et tête de bordure tirés du LiDAR 2021 (`dtm_sol_10cm.tif`, `bordures_hauteurs.geojson` : h_lidar_2021).
   - Dévers constants, avaloirs aux points bas.
   - Supprimer le flou de Z et le retrait de triangles.
4. **Look-dev unique et mesuré** (corrige RC2) : MaterialX texturé dans la chaîne HDA (reprendre `pj_materiaux.py`), mêmes `MI_*` dans UE, albédos calés sur les photos datées (M2), usure observée (M4).
5. **Contexte au même rang que le sol** (corrige RC4) : bâtiments à hauteur LiDAR, arbres, **feux et panneaux FR**, mobilier, avaloirs et tampons, périphérie et horizon. Le rendu de contrôle compose tout.
6. **UE** (corrige RC5) : importer la fabrication HDA du site entier, supprimer le v1, régler date et soleil sur la référence, exposition mesurée.
7. **Validation par l'image d'abord** (corrige RC6) : au moins 30 poses acceptées, planches `photo | rendu | superposition` générées à chaque fabrication, mesures automatiques P4, M3, L1 et V1, revue en aveugle V2. Un rendu ne part plus vers l'utilisateur tant que les critères du § 6 ne sont pas mesurés.
8. **Inscrire les critères de réalisme dans `regles_conception.json`** (nouvelle famille « realisme_validation ») pour que `verifier_regles.py` les rapporte avec la conformité normative (corrige RC6 et RC7).

---

## 8. Fichiers produits (ce dossier)

| Fichier | Contenu |
|---|---|
| `QUALITE.md` | Ce rapport. |
| `mesures_qualite.json` | Mesures M-A (bordures et arêtes de l'ortho 2022, hors travaux et en travaux), M-B (classes et verdure de l'ortho), M-C (photo et rendu : détail, ciel, dynamique, saturation, poses). |
| `planche_n1_rendu2026_vs_ortho2022.png` | Vue de dessus du centre (54 × 54 m), 4 cadres : (a) ortho 2022 ; (b) rendu Karma n1 ; (c) levé GAM sur l'ortho 2022 ; (d) fondu à 50 %. |
| `leve_gam_sur_ortho2022_centre.png` | Levé GAM (identique à `etat_2026`) sur l'ortho 2022, 70 × 70 m. |
| `classes_decrites_sur_ortho2022_centre.png` | Classes de surface et bordures de la description v2 sur l'ortho 2022, 54 × 54 m. |
| `planche_regression_lookdev_pilote_vs_site.png` | Mêmes caméras : chaîne pilote texturée du 10/10 contre chaîne HDA du site du 11/10. |
| `planche_defauts_annotes.png` | 6 cas annotés (Karma p_e, p_a, p_b, c_cam1 ; UE ctx_cam2, ctx_cam4). |
| `rendus_karma_poses_photo/rendu_*.png` | Rendus Karma CPU de `fabrique_hda` (copie du 11/10 08:41) aux 5 poses photo calées. |
| `photos_non_versionnees/*.jpg`, `planche_photo_vs_karma_2026.png`, `cameras_vignettes.json` | Vignettes Panoramax (Eric S / Panoramax osm-fr, CC-BY-SA-4.0) et planche photo contre rendu avec les bordures décrites projetées. **À ne pas versionner.** |
| `outils/*.py` | Scripts d'analyse en lecture seule : mosaïque d'ortho, mesures M-A, M-B et M-C, vignettes, rendus husk Karma CPU, planches, pixel → sol. Les chemins de travail intermédiaires pointent vers le scratchpad de la session : à adapter. |

Les rendus Karma de ce dossier ont été faits sur **CPU** (`BRAY_HdKarma`, 16 spp) pour ne pas gêner l'éditeur UE ouvert (GPU à 86 %), à partir d'une copie de `fabrique_hda` faite dans le scratchpad. Le dépôt n'a pas été touché.
