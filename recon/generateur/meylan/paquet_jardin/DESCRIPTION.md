# Carrefour Paquet Jardin — avenue de Verdun × chemin de la Revirée × avenue du Vercors

*Relevé Meylan, lot A (carrefours et rues), 17/10/2026. Site M01 du dossier `D:\DocRoute\13_Observations_Panoramax_Isere`.
Centre : 45,20765 N, 5,7682 E ; Lambert-93 (917 279,43 ; 6 460 289,98), z 216,1 m (RGE ALTI) — c'est l'origine O du dépôt.*

**État décrit : avant les travaux de 2025, au 18/05/2025** (dernière série photographique d'avant travaux : photo 360°
119d9094 au centre, aucun chantier visible ; configuration de voirie inchangée depuis le 24/08/2024). Décision prise
avec l'utilisateur : la cible du dépôt est l'état avant travaux (CLAUDE.md ; inventaire
`recon/out/paquet_jardin/v2_avant_travaux/inventaire/`). La première version de ce relevé (17/10/2026) décrivait le
31/08/2025, pendant le chantier (travaux du 23/06/2025 au 05/12/2025), et mêlait trois états (relecture M2) ; les
photos de ce jour ne servent plus que hors de l'emprise des travaux (approche nord-est de Verdun, 20d1a815). Aucune
photo publique de l'état fini (après le 05/12/2025) n'existe sur Panoramax au 17/10/2026.

**Réseau (lot N1, 18/10/2026).** date d'état **18/05/2025**, état **avant les travaux** de 2025 (décision prise avec l'utilisateur) ; Verdun nord-est finit sur le nœud partagé `N_VERDUN_PJ_NE` (100 m du centre, médiane OSM), dont le profil est le contrat du joint avec `axe_verdun_centre` ; la bretelle de tourne-à-droite SE, la contre-allée de Verdun SO, les îlots en galets et les traversées à feux de la bretelle (supprimés en 2025) sont rétablis d'après l'OSM du 01/06/2025, l'ortho 2024 et la photo 119d9094 ; le levé GAM n'est utilisé que sur Verdun nord-est et la Revirée (CHANGEMENTS.md § 3). Description au format réseau, résolue par `recon/generateur/reseau/resoudre_reseau.py` ; nœuds partagés et contrats de profil dans `../reseau_meylan.yaml`.

## 1. Description simple (comme on la dirait)

*Réécrite le 18/10/2026 (passe v2) d'après `COMPREHENSION.md` : orthos de 7 dates et 60 photos croisées, centre d'abord.*

> Grand carrefour à feux en croix, un peu décalé, à la sortie de Meylan vers La Tronche. L'avenue de Verdun (RD1090,
> 50 km/h) arrive en 2 × 2 voies d'environ 3 m ; le chemin de la Revirée (nord-nord-ouest) et l'avenue du Vercors
> (sud-sud-est) la coupent à environ 4 m l'un de l'autre. **Au centre**, un grand espace d'enrobé que traversent la
> ligne axiale de Verdun (ligne mixte) et des flèches ; **chaque branche a un îlot au droit de son passage** : sur
> Verdun nord-est un îlot revêtu d'environ 2 m à nez arrondi, coupé par le passage, puis la zone hachurée et la voie de
> tourne-à-gauche ; sur Verdun sud-ouest un îlot refuge à nez arrondi (B21) au passage et, côté cœur, un petit îlot
> rond entre les deux moitiés de la traversée de la Chronovélo, qui passe juste après le passage entre **deux rangées
> de rectangles jaunes** ; sur la Revirée un îlot en coin qui porte les panneaux de direction, coupé par deux
> demi-passages décalés doublés de **traversées cyclables vertes à damier** ; sur le Vercors un **îlot central en
> galets** (triangle au bord du cœur, passage, puis îlot long d'environ 20 m) entre la sortie d'une voie large et les
> deux entrées. **L'angle sud est un grand îlot revêtu** (environ 8 × 8 m, mâts) derrière lequel une bretelle d'une voie
> file de Verdun sud-ouest au Vercors, avec sa propre traversée ; l'angle ouest est un îlot planté en pointe, l'angle
> est un îlot planté. Passages à feux de 3 m, Chronovélo le long du côté nord-ouest de Verdun, contre-allée vers le
> parking relais, enrobé ancien fissuré à pontages, marquages usés.

## 2. Ordre de construction (celui de la chaîne)

L'ordre qui fait foi est celui de la chaîne de construction (`../../CHAINE_CONSTRUCTION.md` § 2 et `chaine_construction.json`) : bordures et caniveaux avant l'enrobé, marquages avant la retenue et les panneaux, éclairage après les panneaux. L'ordre que proposait ce relevé est rangé ci-dessous dans ces étapes (relecture de la préparation, § 3).

| Étape de la chaîne | Ce que le site y construit |
|---|---|
| E07 terrassements, plate-forme | terrain plat (z ≈ 216 m), toit de chaussée sur l'axe de Verdun |
| E08 bordures et caniveaux | bordures T2 des trottoirs, îlot étroit de la Revirée, îlot allongé en galets entre Verdun SO et la bretelle, îlot du Vercors, refuge de Verdun SO, nez arrondis ; abaissés |
| E10 chaussée | Verdun 2 × 2 voies (14,5-15,4 m), bretelle SE vers le Vercors, contre-allée NO de Verdun SO, Revirée 8 m, Vercors 10,8 m ; enrobé ancien, reprises |
| E11 trottoirs, pistes, îlots | Chronovélo au niveau du trottoir côté NO de Verdun, bandes d'herbe, trottoirs en enrobé, quais La Revirée, galets des îlots ; BEV aux passages |
| E12 marquages | rives, lignes entre voies, zone hachurée de l'approche NE, flèches TAG et TD+TAD, passages (bandes de 3 m), traversées cyclables vertes de la Revirée et traversée Chronovélo à pavés jaunes (pratiques locales photographiées), « 50 » au sol sur Verdun SO |
| E14 signalisation et feux | mâts R11 + répétiteurs (dont ceux des deux traversées de la bretelle, supprimées en 2025), R12, D21 « La Revirée », J5 sur les nez, AB3a et C113/C114 de la Chronovélo, poteaux d'arrêt de bus |
| E15 éclairage | candélabres |
| E16 mobilier | potelets, abri de bus |
| E17 végétation (plus tard) | haies taillées, grands feuillus et conifères côté NO |

L'option « chantier du 31/08/2025 » (séparateurs K16, clôtures, ligne jaune provisoire) ne fait pas partie de l'état décrit : RF-OBS-MAR-03, un marquage de chantier n'est jamais l'état permanent.

## 3. Constats et provenance

| Élément | Valeur | Provenance |
|---|---|---|
| Régime | feux sur les 4 branches | OSM (10 `crossing=traffic_signals`, 4 `traffic_signals` à < 25 m) ; photos 10ec04d5, e96ea4be |
| Vitesse, catégorie | 50 km/h, RD1090 « primary » | OSM 63600584, 185326640 |
| Verdun NE à 80 m | 4 voies 3,17 / 2,86 / 3,01 / 2,59 m, chaussée 11,6 m, sans zone hachurée | coupe `verdun_ne_80` (lignes et bordures GAM, limite PCRS) |
| Verdun NE à 40 m | chaussée 14,5 m : 3,3 + 2,9 (sortantes) / zone hachurée 2,2 / 3,0 (TAG) + 2,9 (TD+TAD) | coupe `verdun_ne_40` ; flèches sur 20d1a815 (t005, t007) |
| Côté NO de Verdun NE | bande enherbée 2,7 m, Chronovélo 3,0 m entre bordurettes, trottoir 1,8 m | coupe `verdun_ne_40` ; photo 20d1a815 (t007) ; OSM 398052219 (width 4) |
| Verdun SO à 40 m | chaussée 15,4 m, 2 + 2 voies, « 50 » au sol, ligne axiale | coupe `verdun_so_40` ; photo 7dcdf1d1 (t006) |
| Côté NO de Verdun SO | bande 0,8 + herbe 2,2, caniveau, Chronovélo 3,1 m, trottoir 3,4 m (levé GAM, état projet) ; **en chantier le 31/08/2025** | coupe `verdun_so_40` ; photos 22c050a5 (t008), 4c652c50 (t008) |
| Côté SE de Verdun SO | trottoir ≈ 4,5 m, arrêt de bus « La Revirée » avec abri | coupe ; photo 7dcdf1d1 ; OSM 514050476 |
| Revirée à 30 m | chaussée 8,05 m (axe au milieu), trottoirs 2,0 et 1,8 m | coupe `reviree_30` |
| Revirée au débouché | deux sens séparés par un îlot étroit bordé (≈ 1 m) portant les D21 ; passages à feux ; bandes vertes de traversée cyclable | photo 119d9094 (18/05/2025, l+102.9) ; OSM 40994097 (width 3), 185326634 (width 4) |
| Vercors à 35 m | chaussée 10,8 m : sortie 1 voie ≈ 5,0 m, entrée 2 voies 2,75 + 3,0 m ; trottoir est 2,15 m | coupe `vercors_35` ; OSM 185326635 (lanes 2, width 6), 169866973 (lanes 1) |
| Passages piétons | 4 branches, bandes ≈ 3 m, 0,5 m de large | ortho IGN 2024 (zoom du centre) ; DEF-011 (« paquet_jardin » : 3,00 m) ; photo e96ea4be (t006) |
| Chronovélo | piste bidirectionnelle côté NO de Verdun, traverse Verdun SO près du carrefour puis part vers l'est (piste 54585242, width 4) | OSM ; `data/context/chronovelo.geojson` (GAM 2022) |
| Signalisation | R11 sur mâts gris, répétiteurs, D21 « LA REVIRÉE / Collège L. Terray » et « Commerces de la Revirée », J5 sur les nez d'îlots, C113 / C114 + AB3a sur la Chronovélo | photos 10ec04d5 (t005, t007, t009), e96ea4be (t008), 20d1a815 (t006) |
| Revêtement | enrobé ancien fissuré, pontages noirs, marquages usés | photos 20d1a815, e96ea4be (RF-OBS-REV-01) |
| Traversée Chronovélo de Verdun SO | bandes du passage piéton puis traversée cyclable bordée de deux rangées de pavés jaunes | photo 22c050a5 (t006) ; RF-MA-CHR-007, RF-OBS-MAR-01 |
| Chantier (31/08/2025) | séparateurs K16 rouges et blancs, clôtures orange, cônes, « ROUTE BARRÉE », panneau à chevrons, ligne jaune provisoire, emprise en grave côté NO de Verdun SO | photos 10ec04d5, e96ea4be, 22c050a5, 4c652c50 ; RF-OBS-MAR-03 |

Les coupes sont dans `mesures.json` (« coupes ») ; les constats par photo, avec les tuiles regardées, dans `photos.json`.

## 4. Ce que la description simplifie

- Les branches sont droites (Verdun l'est ; la Revirée et le Vercors s'incurvent au-delà de 60 m).
- Le plan de feux n'est pas observable : celui du YAML est une **hypothèse** à 2 phases (cycle ≈ 60 s, DEF-028).
- Le levé GAM du dépôt (`Meylan_Topo.dwg`) intègre le projet de 2025 sur Verdun SO (nouveau passage, terre-plein
  planté prévu) : il n'est pas l'état du 31/08/2025 ; les cotes de chaussée bordure à bordure de Verdun NE, de la
  Revirée et du Vercors sont, elles, inchangées depuis 2022 (`CHANGEMENTS.md` du dépôt).
- Les traversées de la Chronovélo (pavés jaunes sur Verdun SO, piste vers le Vercors) et les bandes vertes de la
  Revirée n'ont pas de mot dans le format (`../BESOINS_FORMAT.md`, A2).

## 5. Pour aller plus loin

L'état avant travaux (printemps 2025) est inventorié en détail dans
`recon/out/paquet_jardin/v2_avant_travaux/inventaire/` (PLAN_AVANT_TRAVAUX.md, CHANGEMENTS.md). L'état fini (après le
05/12/2025) n'a pas de photo publique : le levé GAM et l'OSM de 2026 en donnent seulement une partie.

## 6. Étape 3 — reconstruction (18/10/2026)

- Itération 1 : la séparation entre Verdun sud-ouest et la bretelle de tourne-à-droite est **peinte** (zone hachurée
  d'environ 1,7 m entre deux lignes continues) et non un îlot en galets sur toute la longueur : photos 0fe2656f
  (24/08/2024) et 034cb578 (18/05/2025) ; l'îlot en galets IA-2 (≈ 22 m²) reste au cœur.
- Rapport : `RECONSTRUCTION.md` ; manques du générateur : `BESOINS.md`.

## 7. Étape 3, passe v2 — centre refait (18/10/2026)

Remarque de l'utilisateur : « avec 6-10 photos tu ne peux pas comprendre toute la scène, et surtout le centre avec la
zone de conflit ». Le dossier de compréhension v2 (60 photos, 123 vues dont 54 du centre, 7 orthos datées) a été lu en
tuiles natives et la scène comprise en croisant ces images (`COMPREHENSION.md`). Itération 2 de la description :

| Changement | Preuve |
|---|---|
| centre déplacé sur la médiane réelle de Verdun (0,10 ; −2,85) ; axes réels de la Revirée (ligne axiale à 326°) et du Vercors (médiane des îlots en galets, courbe à ≈ 27 m), décalés latéralement du centre | PCRS 2022 lu à la grille (`pcrs_NE`, `pcrs_SO`, `pcrs_reviree`, `pcrs_S_vercors`) ; nœud N_VERDUN_PJ_NE |
| passages posés par leur retrait (Verdun NE 5,5 ; Revirée 5 ; Verdun SO 5 ; Vercors 3,5 m) | PCRS 2022 ; 119d9094, 734a0da6, 31d16b8e |
| îlots : Verdun NE revêtu jusqu'au nez (≈ 9 m de long), Revirée en coin (2,2 m, ouverture de 4,5 m), Verdun SO (refuge + îlot de la traversée Chronovélo, depuis ≈ 24 m), Vercors (îlot central en galets, nouveau) | PCRS 2022, IGN 2024 ; 119d9094 (-045, -084, -134, +114), e5d79de9 +037, 31d16b8e (-113, +160) |
| bretelle SE en voie directe derrière l'îlot de l'angle sud (îlot directionnel R 16, voie 4 m, passage), au lieu d'une voie de tourne-à-droite qui débouchait dans le cœur | `pcrs_coin_SO_vercors`, `pcrs_S_bretelle` ; 31d16b8e -113 |
| angles : Revirée / Verdun SO en rayon 12, Vercors / Verdun NE en rayon 10 | `pcrs_NO`, `pcrs_SE` |

Hors format (besoins PJ-1 à PJ-8 de `BESOINS.md`) : traversée Chronovélo en rectangles jaunes, traversées vertes à
damier, ligne mixte et flèches du cœur, triangle du Vercors (refuge à rampants), bretelle longue et îlot d'angle de
forme dite, îlot en coin, angle planté en pointe ; triangulation de `rg::sol` qui plante (G2 étendu).
