# Rond-point du Lycée — avenue de Verdun × avenue des 7 Laux (RD1090) × avenue du Taillefer × chemin de l'Ancienne Mairie

*Relevé Meylan, lot A, 17/10/2026. Site M02 du dossier `D:\DocRoute\13_Observations_Panoramax_Isere`. Point du site :
45,214213 N, 5,779941 E ; Lambert-93 (918 174,96 ; 6 461 050,78) ; z ≈ 252,5 m (RGE ALTI). Centre de l'anneau : (+2,57 ;
+1,01) m de ce point (OSM way/620133380).*

**État décrit : 28/07/2026** (campagne IGN, photos 360°, la plus récente ; identique aux photos du 18/05/2025 et à l'ortho
IGN 2024).

**Réseau (lot N1, 18/10/2026).** date d'état **28/07/2026** ; la branche des 7 Laux suit l'axe du séparateur jusqu'au nœud partagé `N_7LAUX_SO` (74 m du bord de l'anneau), où commence `avenue_7_laux_separateur` : décalage de 11,6 m et vide de 17 m supprimés (relecture M7) ; le résolveur raccorde son profil à celui du joint sur les 30 derniers mètres. Description au format réseau, résolue par `recon/generateur/reseau/resoudre_reseau.py` ; nœuds partagés et contrats de profil dans `../reseau_meylan.yaml`.

**Reconstruction (étape 3, 18/10/2026).** Branches tracées vers l'anneau ; Verdun, Ancienne Mairie et Taillefer recalés sur OSM et les photos (Taillefer : tronc commun puis îlot planté de 4,6 m ; entrée en une voie large) ; accès est prolongé à 31 m (fabrication, BESOINS G8) ; séparation de l'Ancienne Mairie limitée aux 20 derniers mètres. Détail, ressemblance par photo et écarts restants : `RECONSTRUCTION.md` ; manques du générateur : `BESOINS.md`.

## 1. Description simple

> Grand giratoire urbain d'environ 66 m de diamètre sur la RD1090, avec 5 branches. L'anneau fait à peu près 8 m de
> large, en enrobé gris, sans voies marquées. Au milieu, un gros îlot boisé surélevé d'environ 50 m de diamètre : une
> couronne franchissable en béton d'environ 1,5 m bordée d'un rang de pavés, puis un muret béton d'environ 60 cm qui
> retient un massif d'arbres et d'arbustes ; un sentier fait le tour à l'intérieur. À l'ouest arrive l'avenue de Verdun :
> 2 voies d'entrée (≈ 8 m) et une sortie, séparées par un îlot revêtu d'environ 4 m qui porte un sens interdit, avec
> des arrêts de bus de chaque côté. Au nord-est l'avenue des 7 Laux arrive en 2 voies (≈ 8 m) et repart en 1 voie,
> séparées par un muret bas, avec une piste cyclable sur le côté. Au sud l'avenue du Taillefer (entrée large ≈ 7 m,
> sortie ≈ 4,5 m, îlot de ≈ 4,5 m), au nord le chemin de l'Ancienne Mairie (deux voies d'environ 4 m séparées par une
> bordure), à l'est un accès de service en entrée seule. Cédez-le-passage à chaque entrée, passages piétons seulement
> au nord : ailleurs piétons et vélos passent dessous par des passages inférieurs (garde-corps sur murets en bord
> d'anneau). Bordures aux joints repeints en blanc, enrobé fissuré et faïencé, beaucoup d'arbres autour.

## 2. Ordre de construction (celui de la chaîne)

L'ordre qui fait foi est celui de la chaîne de construction (`../../CHAINE_CONSTRUCTION.md` § 2 et `chaine_construction.json`) : bordures et caniveaux avant l'enrobé, marquages avant la retenue et les panneaux, éclairage après les panneaux. L'ordre que proposait ce relevé est rangé ci-dessous dans ces étapes (relecture de la préparation, § 3).

| Étape de la chaîne | Ce que le site y construit |
|---|---|
| E07 terrassements, ouvrages | léger relief (z ≈ 250 m) ; passages inférieurs des cheminements sous l'anneau (trémies, murets, garde-corps) |
| E08 bordures | bordure extérieure de l'anneau, bordure de la couronne (vue ≤ 3 cm), muret de l'îlot central, bordures des îlots séparateurs (joints peints en blanc : pratique locale photographiée) |
| E10 chaussée | anneau de 8 m (dévers vers l'extérieur, DEF-006), branches |
| E11 trottoirs, pistes, îlots | couronne béton balayé + rang de pavés, îlot central surélevé, piste bidirectionnelle le long des 7 Laux, trottoirs, quais de bus sur Verdun |
| E12 marquages | lignes cédez T'2 à chaque entrée, ligne entre les 2 voies d'entrée, passages piétons au nord, zigzags jaunes des arrêts |
| E14 signalisation | AB3a, B1 sur l'îlot de Verdun, panneaux d'arrêt de bus, B21-1 sur l'îlot (non vu : à vérifier) |
| E15 éclairage | candélabres |
| E16 mobilier | poteaux bois |
| E17 végétation (plus tard) | massif boisé, alignements et talus enherbés |

## 3. Constats et provenance

| Élément | Valeur | Provenance |
|---|---|---|
| Diamètre extérieur | ≈ 66 m (rayon 33,0 m, 32,2-33,7) | 4 coupes radiales sur les bordures GAM (`mesures.json` → `giratoire`) ; dossier 13 : 65 ± 1,5 m |
| Anneau | 8,0 m (7,97-8,05) bordure à bordure | 4 coupes radiales (GAM) ; dossier 13 : 9,0 ± 1 m (couronne comprise) |
| Couronne franchissable | ≈ 1,5 m, béton balayé + rang de pavés | photos 3d7dd376, a23479c9 (l-0051.4) ; dossier 13 |
| Îlot central | muret béton ≈ 0,6 m, massif boisé surélevé, sentier circulaire (rayon 15,3 m) | photos 3d7dd376, a23479c9 ; OSM path 118543290 |
| Verdun ouest | entrée 2 voies 8,0 m, îlot 4,3 m (B1, AB3a de dos, feu), sortie 6,3 m (1 voie OSM) | coupe `verdun_o_45` ; photo 770c2fc8 ; OSM 1412130617, 168646541 |
| 7 Laux (RD1090) | entrée 8,1 m (2 voies, ligne GAM), séparateur 1,55 m (muret bas), sortie 4,85 m ; piste 3,1 m côté nord-ouest | coupe `sept_laux_45` ; photo f4a9aa12 (l+0154.3) |
| Taillefer | sortie 4,5 m, îlot 4,6 m, entrée 7,0 m (1 voie OSM) | coupe `taillefer_42` |
| Ancienne Mairie | entrée 3,6 m, séparateur 0,55 m, sortie 4,35 m | coupe `mairie_42` |
| Accès est | entrée seule, 1 voie de 4,0 m | coupe `est_42` ; OSM 154686060 (oneway) |
| Régime | cédez-le-passage à chaque entrée, ligne T'2 | OSM give_way ×5 ; photo f4a9aa12 |
| Piétons, cycles | passages au nord seulement ; passages inférieurs ailleurs | OSM crossing ×4, path layer=-1 ×4 ; photos 3d7dd376, ea409889 (garde-corps sur murets) |
| Revêtement | enrobé gris fissuré, faïencé sur Verdun ; joints de bordures peints en blanc | photos a23479c9, 770c2fc8 |

## 4. Ce que la description simplifie

- Les branches sont droites et radiales ; entrées et sorties de Verdun (42° d'écart) sont réunies en une branche
  avec un îlot de 4,3 m.
- La sortie de Verdun (6,3 m bordure à bordure) est décrite en une voie de 4,5 m (le surplus, quai de bus, n'est pas
  décrit) ; l'entrée du Taillefer (7 m) en une voie de 4 m et une bande hachurée.
- Le muret de l'îlot central, le massif boisé surélevé, les passages inférieurs et les arrêts de bus de Verdun n'ont
  pas de mot dans le format (`../BESOINS_FORMAT.md`).
