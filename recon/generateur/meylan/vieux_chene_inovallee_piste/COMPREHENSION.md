# Chemin du Vieux Chêne (Inovallée) — compréhension de la scène (fusion des images dans le modèle)

*`recon/generateur/meylan/vieux_chene_inovallee_piste/COMPREHENSION.md`, 18/10/2026, passe 2 de l'étape 3.*

Ce texte est ma lecture des images, croisées entre elles. Aucun algorithme n'a fusionné ces images. Les sources sont :

- les orthos datées (2018, 2021, 2024 et Pléiades 2025) ;
- les 39 photos de la comparaison v2 (26 Panoramax, 13 Mapillary ; 87 vues, dont 33 voient le centre) ;
- les bordures et les marquages du levé GAM.

Les images ont été lues en tuiles natives (≤ 1 092 px). Les chemins sont relatifs à
`recon/out/generateur/meylan_vieux_chene_inovallee_piste/comparaison/meylan_vieux_chene_inovallee_piste/`. Les photos
sont sous `photos_non_versionnees/` et ne sont jamais versionnées.

## 1. Images lues, fenêtre d'état

**Fenêtre d'état.** Elle commence le **01/01/2025**, parce que la rue a été refaite entre le 23/11/2024 et le
28/07/2026 (§ 4). Seules 11 photos sont dans la fenêtre, toutes du 28/07/2026. Les 28 autres, de 2022 et 2024, sont
**hors fenêtre** et ont servi seulement à comprendre ce qui a changé.

| Source | Images |
|---|---|
| Orthos datées | `orthos/planche_dates_centre_p01.png` (IGN 2024-08-09, Pléiades 2025, IGN 2021-08-13, IGN 2018-08-21), `orthos/planche_dates_site_p01.png` |
| Zooms d'ortho IGN 2024 (grille du repère du site ; bordures GAM en rouge, marquages GAM en cyan) | `comprehension/zooms/centre_gam.png`, `centre_ign2024.png` |
| Rendu de dessus de l'itération 1 \| ortho | `dessus/planche_dessus_site_ign_t00.png`, `dessus/contours_site_ign_t00.png`, `dessus/planche_dessus_centre_ign_t00.png` ; `comprehension/zooms/cote_centre.png`, `cote_ouest.png`, `cote_est.png` |
| Vues du centre (planches 2 × 2) | `centre_p01` à `centre_p06`, soit 24 vues |
| Vues natives du 28/07/2026 | `7d44455e_-014`, `7d44455e_+018`, `7d44455e_+114`, `7d44455e_-169`, `cbd7ccdb_+002`, `cbd7ccdb_+069`, `17826b13_-165`, `17826b13_+132`, `fe78d282_-165`, `7a1d2d4e_+006`, `6e324d31_-165`, `b15b7c4c_+011`, `99722e28_-150` |

## 2. Ce que je comprends de la scène (état du 28/07/2026)

### 2.1 Le centre du carrefour en T

- **Revêtement.** Le centre est en **enrobé neuf, presque noir**. On n'y voit ni ligne de guidage, ni îlot, ni marquage de zone de conflit (`7d44455e_-014`, `7d44455e_+018`, `cbd7ccdb_+002`).
- **Feux.** Les feux sont sur poteaux aux trois branches, avec répétiteurs piétons (`cbd7ccdb_+002`, `cbd7ccdb_+036`, `fe78d282_-165`).
- **Passage sur la branche ouest.** Un passage zébré à feux, à environ 6 à 8 m du centre, traverse les deux voies.
  - L'**îlot peint ocre** de la branche ouest le traverse.
  - Au milieu du passage, on voit un **refuge peint rond** : aplat ocre à contour blanc arrondi, qui dépasse d'≈ 1,5 m côté carrefour (`7d44455e_-014`, `fe78d282_-165`).
- **Desserte nord.** On y voit (`17826b13_+132`, `7d44455e_+018`) :
  - un **passage zébré** ;
  - et, côté est, la **traversée de la piste** marquée par des **figurines vélo et des doubles chevrons**. En 2024, c'était un aplat vert.
- **Angle nord-ouest.** Un îlot bordé arrondi, à bordure basse, est enherbé, avec la piste derrière (`7d44455e_+114`, `17826b13_+132`).
  - Le modèle en fait un trottoir d'angle gris : c'est un écart connu (itération 1).

### 2.2 Branche ouest

- L'**îlot peint ocre de ≈ 2,3 m** est continu, à contour blanc. Il va de l'extrémité ouest du site (`99722e28_-150`, ≈ 60 m) jusqu'au passage (`6e324d31_-165`, `fe78d282_-165`).
- On voit une voie par sens d'≈ 3,3 m et, au sud, des arrêts de bus avec une ligne jaune (`6e324d31_-165`).
- Au nord, une bande enherbée puis la piste séparée.

### 2.3 Branche est

En partant de l'extrémité est vers le carrefour :

1. **Axe en tirets** loin du carrefour (x > 35) (`b15b7c4c_+011`).
2. **Deux lignes continues qui s'écartent** (`7a1d2d4e_+006`).
3. Un **îlot peint ocre d'≈ 1 m** sur ≈ 15 m, dont le **nez arrondi** est à ≈ 10 m du centre (`7d44455e_-169`, `cbd7ccdb_+002`).
4. Entre le nez et le carrefour, les deux sens sont côte à côte, séparés seulement par une ligne.

Au nord, une large bande enherbée (≈ 7 m) puis la piste (`cbd7ccdb_+069`).

## 3. Ce que le modèle de l'itération 1 montrait faux, et ce que la passe 2 corrige

| N° | Élément | Itération 1 | Réel | Passe 2 |
|---|---|---|---|---|
| 3.1 | Îlot ocre est | sur toute la branche (100 m), jusqu'au centre du carrefour | ≈ 15 m d'îlot, nez à 10 m du centre ; avant : deux lignes, puis axe en tirets | zone ocre ouverte de s = 60 à 75, refermée de 88 à 90 ; axe simple au-delà |
| 3.2 | Îlot ocre ouest | jusqu'au centre du carrefour | jusqu'au passage, puis refuge rond | **non corrigé** : refermer la zone au droit du passage, par une fermeture ou un changement de profil, fait s'emballer `rg::sol` (2 essais, BESOINS V7) |
| 3.3 | Hachures | hachures blanches sur l'ocre | aplat ocre plein à contour blanc | inchangé (V2) |
| 3.4 | Traversée cyclable | absente | figurines et doubles chevrons | inchangé (V4) |
| 3.5 | Angle nord-ouest | trottoir d'angle | îlot bordé enherbé | inchangé |
| 3.6 | Marquage le long de l'îlot est | deux lignes blanches qui quittent l'îlot et coupent la voie (vue de dessus, `cote_est`) | — | défaut de tracé du générateur, déjà relevé (écart 2 de `RECONSTRUCTION.md`) |

## 4. Contradictions entre dates, et comment je les tranche

L'état a changé entre 2024 et 2026. Les dates montrent une suite d'états différents.

- **Ortho 2018.** Il y a déjà une traversée verte sur la desserte. La branche est porte une double ligne.
- **Orthos 2021 et 2024, photos de 2022, du 01/05/2024 et du 23/11/2024** (hors fenêtre).
  - Branche est : un **séparateur bordé bas** et une zone hachurée blanche (bordures GAM (5,5 ; −10) → (8 ; −12)).
  - Branche ouest : une zone hachurée blanche et grise.
  - Desserte : une **traversée cyclable verte**.
  - Enrobé gris clair et ancien (`centre_p01` à `p06`, magenta « HORS FENÊTRE »).
- **28/07/2026** (dans la fenêtre).
  - **Enrobé neuf presque noir** ; îlots **peints en ocre** et non plus hachurés ; traversée à **figurines et chevrons**.
  - Le petit séparateur bordé de l'est a disparu : on voit à sa place le nez de l'îlot ocre.
- **Pléiades 2025.** L'image est trop floue (50 cm) pour dater la réfection.

**Décision.** L'état décrit est celui du 28/07/2026. Les positions (passages, nez, bordures) viennent du levé GAM et de
l'ortho 2024, là où les photos de 2026 montrent les mêmes places. Les marquages et les matériaux viennent des photos de
2026 seulement.

## 5. Ce qui reste incertain

- **Date de la réfection** : entre le 23/11/2024 et le 28/07/2026. Aucune photo publique entre les deux.
- **Longueur exacte de l'îlot ocre est** (≈ 15 m) et **position de son nez** (≈ 10 m du centre, à ± 2 m) : je les ai lues en perspective sur deux vues, pas sur une ortho postérieure à la réfection.
- **Lignes d'effet des feux** : non vues nettement sur les vues de 2026. Elles ne sont pas décrites.
