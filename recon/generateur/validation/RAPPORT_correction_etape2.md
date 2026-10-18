# Rapport du lot « correction de l'étape 2 » : carrefours complexes praticables, giratoires, autoroutes, contrôles généraux

*`recon/generateur/validation/RAPPORT_correction_etape2.md` — 18/10/2026. Critères mesurés :
`validation/rapport_correction_etape2.json` (écrit par `validation/faire_rapport_correction_etape2.py`) ; contrôles ajoutés :
`validation/controler_correction_etape2.py` (CE-1 à CE-5), `validation/comparer_permutation.py`. Documentation :
`hda/README_RG.md` § 15, `description/FORMAT_DESCRIPTION.md` § 15.3 et 15.4.*

Demande de l'utilisateur : « le PCG doit reproduire des autoroutes, des ronds-points, plusieurs types de bordures, il doit
être complet, et **surtout les carrefours complexes** ». Le contrôle indépendant de l'étape 2 a trouvé J5, la scène phare,
impraticable, et plusieurs défauts de peinture et de chaîne. Ce lot les corrige **à la cause** (HDA, compilateur, pilote),
refait les scènes touchées et leurs rendus, et ajoute un second carrefour complexe (J6) et un giratoire multivoie (G4).
Route seule : sol neutre, ciel simple et soleil.

## 1. Défauts du contrôle et corrections

| Défaut (contrôle de l'étape 2) | Cause | Correction (où) | Résultat mesuré |
|---|---|---|---|
| **J5, phase P2 impraticable** : axes des deux TAG guidés à 1,96 m, couloirs recouverts (2,27 m²), garde caisse / ligne 3 mm | voies de TAG côte à côte (TPC 5 m, îlot 2 m) ; L4 ne demandait qu'une caisse qui ne touche pas la peinture | **description J5** : voies de TAG **face à face** (TPC 3,50 m, RF-OBS-TPC-01 ; îlot de TAG 3,50 m ; déport 3,25 m, arcs de 212,83 m) ; **L4** `garde_guidage` = (1,25 − 0,10)/2 + (2,10 − 1,80)/2 = 0,725 m sur les raccords et l'oblique (RF-GV-TRJ-006, VU p. 142) | R = 8,06 m ; balayages **disjoints (0 m², 0,84 m d'écart)** ; garde caisse / peinture min **0,56 m** ; aucun contact avec les nez ; axes sans croisement |
| **J5, nez dans les balayages** (VL 4/8, bus 0/8 ; retrait plafonné) ; TAG nord / sud de la rue croisés en P3 | balayages calculés sur les géométries du compilateur ; TAG de rue servis dans la même phase | **une seule source** (§ 2) ; **4 phases** (P3 nord, P4 sud) ; **bus = ligne de l'artère** (clé `vehicule`) ; passages à 5 m (RF-GV-PIE-006 : 2-5 m) | nez : **VL 6/6** dégagés (marge min 0,33 m), **bus 2/2** (1,75 m), îlot directionnel à 0,62 m ; **0 croisement de TAG dans une même phase** ; L4-16 garde 1 écart géométrie / topologie (nord / sud, phases disjointes : § 6) |
| **J5, refuges des TPC en gazon**, BEV sur l'herbe | le compilateur abaissait le TPC planté sans le revêtir | **compilateur** : opération `revetir` : tout terre-plein planté traversé (refuge) prend le béton balayé sur passage + rampants (RF-OBS-ILO-01) | CE-2 : **0 point meuble** sous 27 traversées des carrefours, giratoires et rues |
| **J5, passages dans les congés** (0,76 à 3,21 m non marqués) | bandes dimensionnées sur la section ; passages à 2 m dans des congés de 8 m | **J5** : passages à 5 m et coins de 6 m (DEF-010 aux feux) ; **rg::carrefours_sol** : bandes des groupes extrêmes **prolongées dans les congés**, découpées à e de la bordure (toutes scènes) | J5 artère et rue : ≤ 0,74 m sur l'axe du passage ; J3 : 3,08 → 0,74 m ; voir CE-3 (§ 3) pour les passages voisins d'un îlot directionnel |
| **G3, îlots non fabriqués** (0/4), débris d'aplats sur les passages | saillie de 0,50 m d'un îlot infranchissable appliquée à un îlot de 1,50 m | **compilateur** : îlot franchissable du mini-giratoire en retrait de 2u + 3u (IISR7 117-2) ; **G3** : enveloppe de 2,00 m, passages à 5 m (`passage: {retrait}` ajouté aux giratoires, DEF-012 contrôlé) | **GI-03 4/4** (1,07 m) ; aucun débris (CE-1 = 0) |
| **G1, hachures sous les passages** (6,36 m²) | les zébras ne connaissaient pas les passages | **rg::marquages** : zébras et aplats interrompus à 0,50 m des passages (RF-MQ-PP-03) | CE-1 G1 = **0 m²** |
| **G2, anneau en T2 3u** | rive inférée des routes sans bordure (RF-OSM-MRQ-021) | **compilateur** : contour de l'îlot central et rive de l'anneau en **continue 3u** (RF-MQ-GIR-01, -04) ; rives d'approche en T2 3u | lignes de l'anneau : continue |
| **Chaîne : L3 et L4 n'utilisaient pas les mêmes trajectoires** | deux constructions (compilateur / VEX L4) | **pilote** : balayages calculés sur les trajectoires **finales** de L4, passes jusqu'au point fixe (nez → fin de branche → trajectoires) ; bus sur les mêmes axes de voie avec un arc de son rayon minimal ; L4 : rayon des TAG non guidés tenu entre les **frontières** (indépendant des nez) | J1-J6 : trajectoires balayées = trajectoires finales (empreintes) ; 2 à 3 passes ; L3-9 / L3-10 rejoués **avec les TAG** (VL et bus) |
| Effet de la source unique sur J4 : les TAG de l'avenue balaient les nez des îlots de la rue (VL −2,4 m, bus −5,4 m) ; bus TAG contre l'îlot directionnel | J4 décrite sans véhicule par mouvement, passages à 2 m qui plafonnent le retrait des nez | **description J4** : bus = ligne de l'avenue (`vehicule`), passage de la rue nord à 6 m | nez nord dégagé (VL, bus) ; îlot directionnel hors balayages (0,64 m) ; **nez sud non dégagé** (§ 6) |
| **A3, rive de BAU absente sur 32 m** | dernier trait T4 tronqué retiré avant la fin de la BAU | **description A3** : la T4 devient rive continue 3u sur les 35 m avant l'interruption (IISR7 p. 15, RF-MQ-SC-13) ; contrôle CE-4 | **0 trou** de rive (A1-A4, S01) |
| **Déterminisme : sorties dépendantes de l'ordre** | nœuds réutilisés d'une scène à l'autre | **pilote** : réseau reconstruit pour chaque scène | S02 seul = S02 après J5 (même processus), **manifestes compris** ; J5 identique dans deux processus |
| Doublons : J5 ligne2 / sas_arriere ; contours de musoir A3, A4 ; pointes axe_g / axe_d ; aplats sur les contours | ligne arrière du sas = ligne d'effet ; demi-lignes de musoir non bornées ; deux lignes nées au même point | **compilateur** : pas de seconde ligne au même endroit ; ligne de droite d'une bande centrale commencée où les deux lignes se touchent ; **rg::autoroute** : demi-lignes bornées à la moitié de l'écart (signé) ; **rg::marquages** : zone hachurable bornée par toutes les lignes voisines | CE-1 (§ 3) |
| Correction connue de `vex_sol.py` non appliquée | `t` du bord pris en `s_end` sur un bord évasé | **rg::carrefours_sol** : bord de chaussée réel en `s_tan` | marche de G3 : 1,72 → **0,13 mm** ; J4 : 1,74 → **0,21 mm** |
| Rapport d'intégration : INT-2, R2, exemples | formulations | `RAPPORT_integration.md` / `.json` corrigés : `route_l2.usda` diffère dans 11 scènes (caniveaux), **R2 non compté** ; ex08, ex11 refabriqués | ex05 : échec du lot L2 (§ 6) |
| Couverture : un seul carrefour complexe, pas de giratoire multivoie | — | **J6** : deux avenues 2 × 2, TAG face à face sur les **quatre** approches, deux lignes de guidage, deux îlots directionnels, 4 phases ; **G4** : giratoire Ø 50 m, anneau 9 m sans voies peintes, entrées à 2 voies (T3 puis continue sur 13 m, arrêtée à la ligne cédez) | § 3 |

## 2. Une seule source de trajectoires (pilote)

`fabriquer_generateur.balayages_trajectoires_l4` : passe 1 sans balayage, cuisson de L3 et L4, balayages des trajectoires
L4 (`fabriquer_carrefours.balayages_l4`, lot L3a) ; passe suivante avec ces balayages ; arrêt quand les balayages ne
changent plus. Journal dans `l3/manifest_l3.json` (`balayages_passes`), enveloppes dans `l3/balayages.json`, contrôle
`trajectoires_balayees_identiques` dans `l4/manifest_l4.json`. Véhicules par mouvement : clé de description
`vehicule: {bus: [...]}` → `trajectoires[].usagers` (sans la clé : VL et bus partout, comme avant).

## 3. Critères

*(tableau recopié de `rapport_correction_etape2.json` ; voir § 7 pour la commande)*

| Id | Critère | Valeur mesurée | Seuil | Atteint |
|---|---|---|---|---|
| CE-J1 | TAG guidés (phase spéciale) : balayages du VL des deux courants disjoints (L4-13) | recouvrement max 0.0 m² (3 lignes : J5 1, J6 2) | 0 m² | oui |
| CE-J2 | TAG guidés : garde caisse (1,80 m) / bord de la peinture de la ligne de guidage | min 0.55 m | ≥ 0,50 m | oui |
| CE-J3 | TAG guidés : balayages contre les faces de bordure (nez des TPC) | max 0.0 m | 0 m | oui |
| CE-J4 | TAG guidés : axes sans croisement | 0 croisement(s) | 0 | oui |
| CE-L3-9-vl | nez des îlots au premier contact des balayages + 0,30 m (VL), J1-J6 | 15/16 nez touchés dégagés (16 nez) ; marge min -2.425 m (J4 B-sud.nez.tp1) | ≥ 0,30 m pour chaque nez | **non** |
| CE-L3-9-bus_standard_12m | nez des îlots au premier contact des balayages + 0,30 m (bus 12 m (mouvements desservis)), J1-J6 | 11/12 nez touchés dégagés (16 nez) ; marge min 0.25 m (J4 B-sud.nez.tp1) | ≥ 0,30 m pour chaque nez | **non** |
| CE-L3-10 | îlots du cœur (directionnels) hors des balayages faisables, J1-J6 | distance min 0.615 m (4 îlots) ; balayages qui coupent un îlot : 0 | ≥ 0,30 m, 0 coupe | oui |
| CE-L3-src | une seule source : balayages calculés sur les trajectoires finales du lot L4 (empreintes identiques), TAG compris | J1 True (2 balayages de TAG); J2 True (4 balayages de TAG); J3 True (4 balayages de TAG); J4 True (4 balayages de TAG); J5 True (4 balayages de TAG); J6 True (4 balayages de TAG) | identiques, ≥ 1 TAG balayé par carrefour à TAG | oui |
| CE-L4-16 | conflits : géométrie (intersections des axes) = topologie (ordre des bouts) — rapporté | J1 0; J2 0; J3 0; J4 0; J5 1; J6 0 | 0 écart | **non** |
| CE-5 | TAG qui se croisent dans une même phase (carrefours à feux) | J1 0 (0 phases); J2 0 (0 phases); J3 0 (2 phases); J4 0 (0 phases); J5 0 (4 phases); J6 0 (4 phases) | 0 | oui |
| CE-1 | non-superposition des peintures (aire entre deux entités ≤ 1e-4 m²), toutes scènes | 5 paire(s) au-dessus du seuil ; J6_ 0.4343 m²; A3_ 0.0002 m² | 0 paire | **non** |
| CE-2 | sol sous chaque passage et chaque refuge non meuble (ni gazon, ni terre) | 0 point(s) meuble(s) sur 49 passages | 0 | oui |
| CE-3a | passages : dernière bande → bord de chaussée sur l'axe du passage (RF-MQ-PP-05) | max 1.18 m (49 passages) | ≤ 0,80 m | **non** |
| CE-3b | passages : dernière bande → bord de chaussée sur toute la longueur des bandes (congés, bords évasés) : pas de place pour une bande de plus | max 6.0 m | < 1,50 m (0,50 + 2 × 0,50) | **non** |
| CE-4 | rives peintes continues (autoroutes, S01) : aucun tronçon sans peinture plus long que l'intervalle de la modulation | 2 trou(s) | 0 | **non** |
| GI-03-G1 | C-G1 : îlots séparateurs fabriqués = ACI tableau 2 (H, B, d, r ; retrait 1 m) | 4 îlots ; écart max 2.8 mm ; I-G1.nord H 20.000 B 5.000 d 0.450 r 0.400 retrait 0.997 | H 20.0, B 5.0, d 0.450, r 0.400 ± 1 cm | oui |
| GI-04-G1 | C-G1 : refuges dans les îlots séparateurs au droit des passages (face fabriquée) | min 2.117 m (4 refuges) | ≥ 2,00 m | oui |
| GI-12-G1 | C-G1 : abaissés des refuges (DEF-031) et leurs BEV | 8 abaissés sur 4 îlots ; 8 BEV | 8 abaissés et autant de BEV | oui |
| GI-07-G1 | C-G1 : passages en retrait de la ligne CÉDEZ (bande peinte la plus proche → ligne) | 5.00-5.00 m (4 passages) | 2-5 m (± 5 cm) | oui |
| GI-11-G1 | C-G1 : sol étanche (raccords cœur / branches ; bords libres ; îlots posés) | écart max 0.13 mm ; 8 bords libres hors extérieur ; îlots : 0 bords libres visibles | ≤ 1 mm ; 0 ; 0 | **non** |
| GI-03-G2 | C-G2 : îlots séparateurs fabriqués = ACI tableau 2 (H, B, d, r ; retrait 1 m) | 4 îlots ; écart max 3.5 mm ; I-G2.nord H 25.000 B 6.250 d 0.500 r 0.500 retrait 0.997 | H 25.0, B 6.25, d 0.500, r 0.500 ± 1 cm | oui |
| GI-11-G2 | C-G2 : sol étanche (raccords cœur / branches ; bords libres ; îlots posés) | écart max 1.00 mm ; 0 bords libres hors extérieur ; îlots : 0 bords libres visibles | ≤ 1 mm ; 0 ; 0 | oui |
| GI-03-G3 | C-G3 : îlots séparateurs du mini-giratoire (RF-GV-GIR-016) | 4 / 4 îlots fabriqués ; largeurs 1.07-1.07 m | 4 îlots de 0.85 à 2.00 m | oui |
| GI-07-G3 | C-G3 : passages en retrait de la ligne CÉDEZ (bande peinte la plus proche → ligne) | 5.00-5.00 m (4 passages) | 2-5 m (± 5 cm) | oui |
| GI-11-G3 | C-G3 : sol étanche (raccords cœur / branches ; bords libres ; îlots posés) | écart max 0.13 mm ; 0 bords libres hors extérieur ; îlots : 0 bords libres visibles | ≤ 1 mm ; 0 ; 0 | oui |
| GI-03-G4 | C-G4 : îlots séparateurs fabriqués = ACI tableau 2 (H, B, d, r ; retrait 1 m) | 4 îlots ; écart max 3.5 mm ; I-G4.nord H 25.000 B 6.250 d 0.500 r 0.500 retrait 0.997 | H 25.0, B 6.25, d 0.500, r 0.500 ± 1 cm | oui |
| GI-04-G4 | C-G4 : refuges dans les îlots séparateurs au droit des passages (face fabriquée) | min 3.367 m (4 refuges) | ≥ 2,00 m | oui |
| GI-12-G4 | C-G4 : abaissés des refuges (DEF-031) et leurs BEV | 8 abaissés sur 4 îlots ; 8 BEV | 8 abaissés et autant de BEV | oui |
| GI-07-G4 | C-G4 : passages en retrait de la ligne CÉDEZ (bande peinte la plus proche → ligne) | 5.00-5.00 m (4 passages) | 2-5 m (± 5 cm) | oui |
| GI-11-G4 | C-G4 : sol étanche (raccords cœur / branches ; bords libres ; îlots posés) | écart max 0.12 mm ; 0 bords libres hors extérieur ; îlots : 0 bords libres visibles | ≤ 1 mm ; 0 ; 0 | oui |
| CE-G2 | G2 : lignes de l'anneau (contour de l'îlot central, rive) en continue 3u (RF-MQ-GIR-01, -04) | l0 r = 17.075 m : continue 0.15 m; l1 r = 25.0 m : continue 0.15 m | continue 0,15 m (3u) | oui |
| CE-R | rendus : géométrie rendue = .usda finaux, planche ≤ 1092 px (2 vues ; 3 pour J5, G1, A3) | 27/27 | 27/27 | oui |
| CE-D-permutation | S02 seul / S02 après J5 (même processus) : sorties identiques à l'octet, manifestes compris | 28 fichiers, écarts [] | identique | oui |
| CE-D-determinisme | J5 : deux processus : sorties identiques à l'octet, manifestes compris | 41 fichiers, écarts [] | identique | oui |

26 critères atteints sur 34.

## 4. Scènes refaites, rendus, non-régression

- **Refaites avec rendus** (2 vues ; 3 pour J5, G1, A3) : J1-J6, G1-G4, A3, A4 ; descriptions modifiées : J5, J4 (bus,
  passage nord), G3, A3 ; ajoutées : J6, G4. Planches ≤ 1092 px regardées en entier :
  J5, J6, G1, G2, G3, G4, J3, J4, A3 ; vues de dessus de J5 et J6 regardées à 1092 px ; zooms sur J5 sud-est, G1 (îlot,
  avant / après), G4 entrée ouest, J3 coin (raster du sol et des peintures).
- **Refaites sans rendu** (géométrie inchangée, rendus d'avant valides : empreintes des `.usda` identiques) : S01-S12, B01,
  A1, A2. S01-S12 et B01 : tous les fichiers identiques à l'octet à ceux d'avant la correction, sauf `manifest_l2b.json`
  (signature de `rg::marquages` ; avertissements dépendants de l'ordre retirés : 6 → 3 pour S02, S03, S06, S11). A1, A2 :
  seuls les manifestes changent.
- **Exemples** : ex08 et ex11 refabriqués ; ex05 en échec au lot L2 (piste à un niveau intermédiaire entre deux bordures,
  limite connue de `rg::nivellement`, README § 8).
- `l4/plan_l4.png` (image de contrôle du lot L4, pas une sortie de la chaîne) retirée de `l4/` de J1-J5 : elle entrait dans
  les manifestes et faisait différer J5 d'un processus à l'autre ; le manifeste de J5 a été réécrit sans elle.
- Planches d'ensemble : `recon/out/generateur/catalogue_rendus/etape2_*.png` (J6 et G4 ajoutées).

## 5. Comparaison Panoramax (photos locales du dossier 13, route seule)

- **J5 / J6** et M11 Taillefer, M15 Plaine Fleurie : guidage en tirets courts dans un carrefour à feux, plausible ; le
  refuge revêtu traversé à niveau correspond maintenant à I10 (Crolles) et M24 (îlot coupé à niveau, surface revêtue).
- **G2** et G01 Domène, I01, M03 : contour de l'îlot central et rive en continue, comme observé (G01) ; G1 : couronne de
  1,50 m et anneau sans voies conformes ; G4 : anneau large sans voies peintes, comme observé en agglomération.
- **A1 / A3** et A41 à Meylan (c0a557b7) : T1 2u, continue côté TPC, T2 5u d'insertion, TPC béton concordent ; revêtement
  toujours trop uniforme (pas de pontages ni de rapiéçages : § 6).

## 6. Ce qui reste (non atteint ou non fait)

Mesurés et **non atteints** (aucun seuil baissé) :

- **CE-L3-9, J4 sud** : le TAG de l'avenue vers la rue sud balaie le nez de l'îlot séparateur de la rue sud (VL −2,43 m ;
  bus 0,25 m pour 0,30 m). Le retrait du nez est plafonné par le refuge du passage à 2 m de la ligne cédez ; ce passage
  ne peut pas être reculé comme celui de la rue nord (6 m), car il se prolonge à travers la voie directe sur l'îlot
  directionnel (refuge DEF-022). Ce défaut n'était pas visible avant ce lot : les TAG de J1-J4 étaient exclus des
  balayages (R = 4,47 m). À faire : redessiner l'angle sud-est de J4 (îlot directionnel et passage reculés ensemble).
- **CE-L4-16, J5** : 1 écart géométrie / topologie (TAG nord et sud de la rue). Leurs axes se croisent (les sorties sont
  sur une artère de 31 m : aucun tracé droite-arc-droite ne les sépare), alors que l'ordre des bouts autour du centre
  prédit qu'ils ne se croisent pas. Ils sont maintenant servis dans deux phases (P3, P4) : **aucun croisement de TAG dans
  une même phase** (CE-5 = 0). Le modèle topologique de L4-16 ignore les phases.
- **CE-1** :
  - J6 : 0,43 m², les figurines vélo des bandes cyclables tombent sur une bande de passage. Cause trouvée :
    `rg::marquages` (section 3) pose les figurines au pas sans appliquer les `exclusions` du modèle (passage_pieton,
    carrefour). La correction changerait `rg::marquages` pour toutes les scènes ; elle n'est pas faite.
  - A3 : 0,0002 m², bout de la rive gauche de la bretelle contre la demi-ligne de contour du musoir. Avant : 0,54 m².
- **CE-3a / CE-3b, passages voisins d'un îlot directionnel** (J4, J5, J6) : jusqu'à 1,18 m entre la dernière bande et la
  face de l'îlot sur l'axe du passage. La bande de la voie directe (`passage_libre`) est dimensionnée sur la voie peinte
  (rayon R à R + W) et non jusqu'à la face de l'îlot, posée 0,50 m plus loin (saillie RF-GV-ILO-015). La branche sud
  s'arrête aussi au bord de sa section devant l'îlot. CE-3b (6,0 m, J4) est une génératrice de cette bande qui sort de
  l'îlot. À faire au compilateur : W sur la largeur réelle, de la face de bordure à la face de l'îlot. Partout ailleurs,
  l'axe est ≤ 0,74 m (J5 artère 0,52, J3 0,74, G1 0,52, G3 0,60, G4 0,66).
- **CE-4, A4** : 2 trous de rive. Le premier, de 4,0 m pour un intervalle de 3,5 m, se trouve sur la T2 de la voie de
  décélération avant la divergence. Le second, de 19,3 m pour un intervalle de 13 m, est la T4 de la BAU à l'ouverture
  de la voie de décélération. Le contrôle indépendant ne les avait pas signalés ; ils restent à corriger, comme pour A3
  (fin de ligne tronquée, phase d'une limite qui change de clé).
- **GI-11, G1** : 8 bords libres cachés sous les bordures (hérité, non traité). Non traités non plus : marche de 20 mm
  de J2, bords libres de J1 (1) et J2 (5).

Non faits (demande de couverture, P3) :

- caniveaux CS1 / CS2 le long des T2 dans les carrefours et giratoires : les coins de `rg::carrefours_sol` ne portent
  pas de caniveau (limite du lot L3), et en poser sur les seules branches les arrêterait net au point de tangence ;
- scène composée bretelle → giratoire, décalques d'usure, pontages et rapiéçages, bordures A1 / T1 / T3 dans les
  carrefours ;
- ex05 : `rg::nivellement` refuse la piste à un niveau intermédiaire entre deux bordures (README § 8) ;
- R2 (teinte de l'enrobé de B01) : matériau non corrigé, donc non compté.

Durée : la recherche du rayon des TAG guidés (pas de 1 cm, VEX interprété) rend chaque passe de J6 longue (≈ 10 min
avec trois processus). Une recherche par dichotomie la raccourcirait.

## 7. Fichiers

**Modifiés** : `fabriquer_generateur.py` (réseau par scène, balayages L4 au point fixe, dossier temporaire par sortie),
`fabriquer_carrefours.py` (`balayages_l4`, `_axe_vehicule`), `description/carrefours.py` (`vehicule` / `usagers`, sas,
rives de l'anneau, passages de giratoire avec retrait, îlot de mini-giratoire, entrées à 2 voies, ligne arrêtée à la ligne
cédez), `description/description_vers_modele.py` (`revetir`, interruption des lignes convergentes, cible
`limite_bande_ext`), `hda/rg_marquages_carrefour/{vex_l4.py, construire.py}`, `hda/rg_marquages/{marquages.vfl,
construire.py}`, `hda/rg_carrefours/{vex_sol.py, vex_solveur.py, lecteur_carrefours.py}`,
`hda/rg_giratoires/lecteur_giratoires.py`, `hda/rg_autoroute/vex_autoroute.py`, `rendu/planches_etape2.py`,
`validation/controler_L3.py` (balayages de `l3/`), `validation/controler_L4.py`, `validation/controler_giratoires.py`
(scènes J6, G4) ; descriptions J5, G3, A3 ; documentation `hda/README_RG.md` § 15, `description/FORMAT_DESCRIPTION.md` ;
rapport d'intégration (INT-2, INT-5-bordures) ; descriptions J4, J5, G3, A3.

**Créés** : `scenes_carrefours/J6_carrefour_complexe_2x2.yaml`, `scenes_giratoires/G4_giratoire_multivoie_D50.yaml`,
`validation/controler_correction_etape2.py`, `validation/comparer_permutation.py`,
`validation/faire_rapport_correction_etape2.py`, ce rapport et `validation/rapport_correction_etape2.json`.

**HDA reconstruites** (nouvelles signatures) : `rg::marquages`, `rg::carrefours`, `rg::carrefours_sol`,
`rg::marquages_carrefour`, `rg::giratoires`, `rg::autoroute` ; `pj::*` inchangées.

```
hython recon/generateur/fabriquer_generateur.py SCENE.yaml ... --complet
python recon/generateur/validation/faire_rapport_correction_etape2.py
python recon/generateur/validation/comparer_permutation.py DOSSIER_A DOSSIER_B SCENE
```
