# Rond-point de Didcot — chemin du Vieux Chêne × avenue de Chamechaude × bretelle de la rocade

*Relevé Meylan, lot A, 17/10/2026. Site M03 du dossier `D:\DocRoute\13_Observations_Panoramax_Isere`. Point du site :
45,208891 N, 5,791712 E ; Lambert-93 (919 119,28 ; 6 460 492,69) ; z ≈ 221,9 m (RGE ALTI). Centre de l'anneau :
(−0,56 ; −0,33) m de ce point (OSM way/624258028).*

**État décrit : 28/07/2026** (campagne IGN : photos 360° de 08:28 et photo plane de 10:07), le plus récent.

**Réseau (lot N1, 18/10/2026).** date d'état **28/07/2026** ; pas de nœud partagé (la sortie 26 de l'échangeur s'arrête à ≈ 48 m de la branche de la bretelle : écart signalé, hors recouvrement). Description au format réseau, résolue par `recon/generateur/reseau/resoudre_reseau.py` ; nœuds partagés et contrats de profil dans `../reseau_meylan.yaml`.

**Reconstruction (étape 3, 18/10/2026).** Quatre directions (et non sept bras), chacune tracée vers l'anneau ; rayons de raccordement au bas des plages (Re 8, Rs 15) pour que les coins tiennent entre les branches (BESOINS D1) ; branche ouest recalée sur OSM, chemin piéton au sud-est loin de l'anneau, passage piéton au nœud OSM. Détail : `RECONSTRUCTION.md` ; manques du générateur : `BESOINS.md`.

## 1. Description simple

> Giratoire moyen d'environ 47 m de diamètre à l'entrée d'Inovallée, dans les arbres. Anneau d'environ 9 m en enrobé
> sombre, sans voies marquées, avec une ligne blanche continue au bord de l'îlot. Îlot central en butte plantée
> (arbustes, graminées, grands arbres) avec des mâts rouges décoratifs ; tout autour une couronne franchissable
> d'environ 2 m en pavés rouges inclinés, avec deux rangs de galets incrustés ; un panneau bleu « contournement »
> (B21-1) avec le nom « Rond-point de Didcot » face à l'entrée. Quatre directions : l'avenue de Chamechaude au nord
> (2 voies larges d'environ 4,5 m avec une bande peinte au milieu et un passage piéton à îlot), le chemin du Vieux
> Chêne à l'est et à l'ouest (entrée et sortie d'une voie chacune, bien séparées par de grands îlots plantés), et la
> bretelle de la rocade au sud (entrée en 2 voies d'environ 4 m avec un feu, sortie d'une voie fermable par une
> barrière). Cédez-le-passage aux entrées. Pistes mixtes piétons-vélos d'environ 3 m autour, accotements enherbés,
> grands arbres partout ; enrobé un peu fissuré.

## 2. Ordre de construction (celui de la chaîne)

L'ordre qui fait foi est celui de la chaîne de construction (`../../CHAINE_CONSTRUCTION.md` § 2 et `chaine_construction.json`) : bordures et caniveaux avant l'enrobé, marquages avant la retenue et les panneaux, éclairage après les panneaux. L'ordre que proposait ce relevé est rangé ci-dessous dans ces étapes (relecture de la préparation, § 3).

| Étape de la chaîne | Ce que le site y construit |
|---|---|
| E07 plate-forme | terrain plat (z ≈ 222 m), boisé |
| E08 bordures | bordure extérieure, bordure de couronne (vue ≤ 3 cm), bordures des îlots |
| E10 chaussée | anneau de 8,9 m (dévers vers l'extérieur), branches et bretelle, grands îlots séparateurs |
| E11 trottoirs, pistes, îlots | couronne en pavés rouges + 2 rangs de galets, pistes mixtes en béton, trottoirs, passage à îlot sur Chamechaude |
| E12 marquages | ligne continue de bord d'îlot, lignes cédez T'2, rives, bande médiane de Chamechaude, passage |
| E14 signalisation et feux | B21-1 + panonceau nominatif, AB3a, D21 groupés sur mât à l'angle ouest, panneau de zone, feu de fermeture de la bretelle |
| E16 mobilier | barrière de fermeture de la bretelle, mâts rouges de l'îlot central |
| E17 végétation (plus tard) | butte et îlots plantés, grands feuillus et peupliers, accotements en herbe |

## 3. Constats et provenance

| Élément | Valeur | Provenance |
|---|---|---|
| Diamètre extérieur | ≈ 47 m (rayon 23,0-24,4 m) | 4 coupes radiales (bordures GAM) ; dossier 13 M03 : 47 ± 2 m |
| Îlot (couronne comprise) | rayon ≈ 14,6 m | bordure GAM (14,2-14,7 m) |
| Couronne | ≈ 2 m, pavés rouges + 2 rangs de galets | limites de revêtement GAM ; photo 25cbe3d8 (l-0102.9) ; dossier 13 : 1,8 m |
| Anneau | ≈ 8,9 m, aucune voie visible ; ligne de bord d'îlot | coupes radiales ; photos 7544b177, 25cbe3d8. Le levé GAM porte une ligne médiane (r 19,1 m) invisible en 2026 : non retenue |
| Chamechaude | chaussée 11,5 m : 2 × (0,5 + 4,7) + bande médiane 1,0 | coupe `br_n` |
| Bretelle sud | entrée 2 voies de 4,1 m, feu ; sortie 1 voie, barrière + B1 | coupe `br_s_in` ; photo 0f41f230 (l+0102.9) ; OSM 8015852, 10577671775 |
| Vieux Chêne ouest | sortie 1 voie de 4,8 m, piste mixte de 3,2 m | coupe `br_w_out` ; photo 7b6c1e1a (t004) |
| Signalisation | B21-1 + panonceau nominatif, D21 groupés, panneau de zone | photos 25cbe3d8, 7544b177, 7b6c1e1a |

## 4. Ce que la description simplifie

- Les sept bras (quatre directions, entrées et sorties séparées) sont radiaux et droits.
- Largeurs non mesurées (entrées est et ouest, sortie est, sortie de bretelle) : 4 m, d'après les photos.
- La butte plantée, les mâts rouges, la barrière de fermeture et le feu de la bretelle n'ont pas de mot dans le format
  (`../BESOINS_FORMAT.md`).
