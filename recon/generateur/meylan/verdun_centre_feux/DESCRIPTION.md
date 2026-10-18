# Avenue de Verdun × chemin des Buclos — baïonnette et passage piéton à feux (Meylan, centre)

*Relevé Meylan, lot A, 17/10/2026. Site M17 du dossier `D:\DocRoute\13_Observations_Panoramax_Isere` (« carrefour à feux
av. de Verdun, centre »). Point du site : 45,211125 N, 5,773428 E ; Lambert-93 (917 676,06 ; 6 460 690,07) ;
z ≈ 229,3 m (RGE ALTI). C'est le passage piéton à feux (OSM 1333024067 / 1333024069).*

**État décrit : 28/07/2026** (campagne IGN, photos planes 92° de 10:54), le plus récent.

Le « carrefour à feux » du dossier 13 est en fait un **passage piéton à feux à bouton d'appel** sur l'avenue de Verdun,
entre les deux branches du chemin des Buclos, qui débouchent **en baïonnette** (≈ 29 m l'une de l'autre) et en
cédez-le-passage. Ce site complète l'axe « avenue de Verdun centre » relevé par le lot B (`../axe_verdun_centre/`).

**Réseau (lot N1, 18/10/2026).** date d'état **28/07/2026** ; Verdun sud-ouest finit sur `N_VERDUN_M17_SO` (80 m du carrefour Buclos sud), Verdun nord-est sur `N_VERDUN_M17_NE`, ramené de 65 à 40 m du carrefour Buclos nord : l'axe de `axe_verdun_centre` commence et finit sur ces nœuds (recouvrements de 52,9 et 48,1 m supprimés) ; le profil de ce site est le contrat des deux joints. Description au format réseau, résolue par `recon/generateur/reseau/resoudre_reseau.py` ; nœuds partagés et contrats de profil dans `../reseau_meylan.yaml`.

## 1. Description simple

> Avenue de Verdun en ligne droite, une voie par sens d'environ 3,5 m, séparées par une zone hachurée d'environ 3,7 m
> qui devient un refuge bordé au droit d'un passage piéton à feux (bouton d'appel). Le chemin des Buclos coupe
> l'avenue en baïonnette : au sud-ouest, une sortie à sens unique d'environ 4,5 m vers le sud ; une trentaine de mètres
> plus loin au nord-est, une petite rue à double sens vers le nord, avec un cédez-le-passage. Côté nord-ouest, une
> bande d'herbe d'environ 2,5 m puis la Chronovélo (piste vélo à double sens d'environ 3 m) et un trottoir ; côté
> sud-est, une bande d'herbe et une piste mixte piétons / vélos. Bande verte de traversée cyclable au passage, feux
> sur mâts avec caméra, panneau d'affectation des voies, abribus. Enrobé très fissuré avec beaucoup de pontages noirs,
> marquages moyennement usés, falaise du Saint-Eynard en fond.

## 2. Ordre de construction (celui de la chaîne)

L'ordre qui fait foi est celui de la chaîne de construction (`../../CHAINE_CONSTRUCTION.md` § 2 et `chaine_construction.json`) : bordures et caniveaux avant l'enrobé, marquages avant la retenue et les panneaux, éclairage après les panneaux. L'ordre que proposait ce relevé est rangé ci-dessous dans ces étapes (relecture de la préparation, § 3).

| Étape de la chaîne | Ce que le site y construit |
|---|---|
| E07 plate-forme | légère pente (z ≈ 229 m) |
| E08 bordures | refuge bordé au passage (vue ≈ 0,11 m), îlots des débouchés, bordurettes des pistes |
| E10 chaussée | Verdun 2 × 1 voies avec bande médiane, deux débouchés du chemin des Buclos |
| E11 trottoirs, pistes | Chronovélo au nord-ouest, piste mixte séparée au sud-est, bandes enherbées, liaisons revêtues au droit du passage |
| E12 marquages | zone hachurée axiale à chevrons, voies de tourne-à-gauche, passage piéton, ligne d'effet, cédez-le-passage du chemin des Buclos, bande verte de traversée cyclable (pratique locale photographiée) |
| E14 signalisation et feux | feux R11 + R12 et bouton d'appel, AB3a, B1, panneau d'affectation des voies, D21 |
| E15 éclairage | candélabres |
| E16 mobilier | abribus, caméra |
| E17 végétation (plus tard) | haies, grands arbres |

## 3. Constats et provenance

| Élément | Valeur | Provenance |
|---|---|---|
| Verdun sud-ouest | voie 4,1 m (sens NE) / zone hachurée 3,66 m / voie 3,4 m + rive (sens SO) ; bande enherbée 2,55 ; Chronovélo 3,0 ; trottoir 1,8 | coupe `verdun_so_25` (GAM, PCRS) |
| Verdun nord-est | voie(s) sens NE 5,55 m (rive comprise) / zone hachurée 3,66 m / sens SO 9,3 m (2 voies OSM left\|through) ; piste mixte 5,0 m côté SE | coupe `verdun_ne_15` ; OSM 1412130603, 301046542 |
| Passage à feux | bouton d'appel, refuge, BEV | OSM crossing=traffic_signals, crossing:island=yes ; photo de22683a (t003) |
| Chemin des Buclos sud | sortie à sens unique, chaussée 4,4 m | coupe `buclos_s_20` ; OSM 28420143 (oneway) |
| Chemin des Buclos nord | double sens (lanes 2), cédez-le-passage, AB3a | OSM 581180883, give_way 8355380882 ; photo f252d62f (t004) |
| Revêtement | enrobé très fissuré, pontages, reprises | photos de22683a (t004), f252d62f (t007) ; RF-OBS-REV-01 |
| Couleur | bande verte de traversée cyclable | photo de22683a (t003) ; pratique locale (RF-OBS-CYC-03), seulement parce que photographiée |

## 4. Ce que la description simplifie

- La bande parallèle de 4,7 m au sud-est de Verdun sud-ouest (contre-allée ou stationnement, absente d'OSM) est
  décrite en trottoir et bande enherbée.
- Le carrefour voisin de l'allée de la Faculté (≈ 45 m au nord-est) n'est pas décrit.
- Le chemin des Buclos nord est une liaison à double sens suivie d'une voie à sens unique (OSM 27286062) : seule la
  liaison est décrite.
- La largeur de la Chronovélo et des pistes au droit du passage, la bande verte de traversée cyclable et la caméra n'ont
  pas de mot dans le format (`../BESOINS_FORMAT.md`).

## Étape 3 — reconstruction (18/10/2026)

- Itération 1 : entre le refuge du passage et Buclos nord, **deux voies vers le nord-est** (voie de tourne-à-gauche
  d'environ 3 m prise sur la zone hachurée, qui tombe à ≈ 1 m) ; la voie continue ≈ 15 m après Buclos nord puis
  s'efface vers le profil du nœud partagé : photos de22683a (t004 : C24 et deux voies dès le refuge) et fce0902f.
- Rapport : `RECONSTRUCTION.md` ; manques du générateur : `BESOINS.md`.

## Étape 3, passe v2 — centre relu (18/10/2026)

Dossier de compréhension v2 lu en tuiles natives (50 photos, 77 vues ; IGN 2015 à 2025, levé GAM en surimpression) :
`COMPREHENSION.md`. Description simple du centre, telle qu'on la dirait :

> Entre les deux branches du chemin des Buclos, le passage piéton à feux est doublé côté sud-ouest d'une bande verte
> cyclable et traverse la zone hachurée sur deux îlots refuges en D garnis de gravillons. Au sud-est, la sortie de
> Buclos s'évase entre deux angles plantés, son passage est à ≈ 6 m dans la rue ; au nord-ouest, Buclos débouche en
> cédez, la Chronovélo le traverse quelques mètres plus loin.

| Itération | Changement | Preuve |
|---|---|---|
| v2-1 | retraits des passages de Buclos sud (6 m) et nord (4 m) ; passage à feux recentré sur les zébras réels (0,9 m plus au nord-est, bandes de 3,5 m) ; îlots refuges allongés (≈ 0,5 → 13,3 m du tronçon, 12,8 m au lieu de 8) et garnis de gravillons | `modele_gam_S`, `modele_gam_N` (IGN 2024 + levé GAM) ; 3fc24f3e (28/07/2026), 2b9bed48 +155 (18/05/2025) |

Hors format : `BESOINS.md` (VC-1 îlots en D, VC-2 traversée de la Chronovélo ; C1 baïonnette, C2 côté continu).
