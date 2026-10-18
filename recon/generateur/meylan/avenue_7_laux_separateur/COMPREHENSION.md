# Avenue des 7 Laux (RD1090) — compréhension de la scène (fusion des images dans le modèle)

*`recon/generateur/meylan/avenue_7_laux_separateur/COMPREHENSION.md`, 18/10/2026, passe 2 de l'étape 3. C'est une
section courante : il n'y a pas de zone de conflit, et la comparaison v2 n'a pas de « centre ».*

Ce texte est ma lecture des images, croisées entre elles. Aucun algorithme n'a fusionné les images. Sources :

- les orthos datées : 2018, 2021, 2024, Pléiades 2025 ;
- les 13 photos Panoramax de la comparaison v2 (50 vues, fenêtre d'état depuis le 01/05/2024) ;
- les vues de l'itération 2 du premier passage ;
- les bordures et les marquages du levé GAM.

Les chemins sont relatifs à
`recon/out/generateur/meylan_avenue_7_laux_separateur/comparaison/meylan_avenue_7_laux_separateur/`.

**Abscisse s.** Dans tout le texte, `s` est la distance le long du tronçon depuis le nœud `N_7LAUX_SO`, au cap
51,65°. Le nœud est en (−15,7 ; −24,3) du repère du site. Je l'ai calculée par projection des positions sur l'axe, et
non lue sur les planches (piège de l'itération 1).

## 1. Images lues

| Source | Images |
|---|---|
| Orthos datées, même emprise | `orthos/planche_dates_site_p01.png` (IGN 2024-08-09, Pléiades 2025, IGN 2021-08-13, IGN 2018-08-21), `orthos/site_ign2024.png` |
| Zooms et vues côte à côte rendu \| ortho (bordures GAM en rouge, marquages en cyan) | `comprehension/zooms/cote_sud_ouest.png`, `cote_milieu.png`, `cote_nord_est.png`, `nord_ouest_gam.png` (pas de 2 m) |
| Vues natives | `e17dc3d0_-003` (28/07/2026, s ≈ 80), `0630f847_+006` (28/07/2026), `58cc1950_+034` (28/07/2026), `6f988e15_+006` (01/05/2024), `44adba06_-170` (09/05/2024) |

## 2. Ce que je comprends de la scène

Je décris le profil du nord-ouest au sud-est, en regardant vers le nord-est.

| Élément | Constat | Images |
|---|---|---|
| Contre-allée | sens unique vers le sud-ouest, ≈ 3,5 à 4 m, ligne de rive discontinue, murs blancs et haies des maisons | `44adba06_-170`, `cote_milieu` |
| Bande plantée (contre-allée \| piste) | massif d'arbustes et genêts de ≈ 4 m près du nœud. **Elle se referme en pointe à s ≈ 47 m** : les deux bordures GAM convergent en (6 ; 18,5). Elle rétrécit dès le nœud : 1,6 m à la coupe t0, s ≈ 29. Au-delà, la piste et la contre-allée sont côte à côte, séparées par une **ligne de gros blocs** (carrés cyan du levé, s > 47) | `nord_ouest_gam`, `6f988e15_+006`, `cote_nord_est` |
| Piste cyclable | bidirectionnelle, ≈ 3 m, en enrobé | `6f988e15_+006`, `0630f847_+006` (panneaux piste et piétons) |
| Bande béton | ≈ 1,4 à 2,1 m, **barrière bordeaux à croisillons**, avaloir | `58cc1950_+034`, `0630f847_+006`, `e17dc3d0_-003` |
| Chaussée nord-ouest (vers le rond-point) | **deux voies séparées par des tirets sur toute la longueur** : `e17dc3d0_-003` à s ≈ 80, au-delà du bout du tronçon ; `0630f847_+006` ; ortho 2024 ; ligne GAM jusqu'à s ≈ 65 au moins. Enrobé très fissuré, avec des pontages noirs | `e17dc3d0_-003`, `0630f847_+006` |
| Séparateur central | **muret en béton plein** d'≈ 0,8 à 1 m, à about incliné, du nœud jusqu'à **≈ 25 m** (vu de face au bout de la chaussée sur `0630f847_+006` et `e17dc3d0_-003`). Au-delà, **deux bordures basses et un caniveau en pavés gris**. L'ombre du muret se voit sur les orthos de 2018 à 2025 | `0630f847_+006`, `e17dc3d0_-003`, `planche_dates_site_p01` |
| Chaussée sud-est (vers le nord-est) | une voie, ≈ 6,5 m près du nœud et ≈ 4 m au point du site | coupes t_sw, t0 ; `cote_sud_ouest` |
| Sud-est | pelouse, puis parkings | ortho |

## 3. Ce que le modèle de l'itération 2 montrait faux, et ce que la passe 2 corrige

| N° | Élément | Itération 2 | Réel | Passe 2 |
|---|---|---|---|---|
| 3.1 | Seconde voie nord-ouest | refermée de s = 50 à 62 m | deux voies jusqu'au bout | fermeture retirée : deux voies de 2,6 m jusqu'au bout |
| 3.2 | Bande plantée | refermée de 14 à 24 m, sur une abscisse mal lue | pointe à s ≈ 47 m (GAM) | fermeture de 25 à 47 m. Le rétrécissement entre 0 et 25 m n'est pas décrit : un évènement ne peut pas chevaucher le changement de séparateur |
| 3.3 | Séparateur | « béton » jusqu'à 12 m, « pavés » ensuite | muret jusqu'à ≈ 25 m, pavés ensuite | changement à ≈ 25 m. Le muret lui-même n'a pas de mot (S1) |
| 3.4 | Barrière, blocs, pontages | absents | présents | sans mot (S2, S3, S4) |

## 4. Contradictions entre dates

- **Orthos de 2018 à 2025.** Même géométrie : muret, deux voies, ligne de blocs, pointe de la bande plantée. En 2018, la bande plantée et la haie sont plus hautes et plus denses.
- **Itération 1 contre passe 2 : abscisse de fin de la bande plantée.**
  - L'itération 1 la plaçait à 17 m. L'erreur venait de l'abscisse des planches de la v1 (x du repère, et non distance le long du tronçon).
  - La projection sur l'axe et la lecture du levé GAM la placent à 47 m.
  - La coupe t0 (1,6 m de bande à s ≈ 29) va dans le même sens.
  - Je retiens **47 m**.

## 5. Ce qui reste incertain

- La position exacte de l'about du muret : ≈ 25 m ± 5 m, estimée en perspective sur deux photos.
- La forme du rétrécissement de la bande plantée entre le nœud et 47 m : linéaire ou non.
- Le double sens éventuel de la contre-allée : une ligne discontinue au milieu sur `44adba06_-170`, alors qu'OSM la donne à sens unique.
