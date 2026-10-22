# Lot L6 — Signalisation verticale et feux (étape E14) : rapport

*`recon/generateur/validation/RAPPORT_signalisation.md`, 22/10/2026. Données : `validation/rapport_signalisation.json`
(critères, test ARB-19, déterminisme, constats visuels), `validation/controles_signalisation.json` (contrôle
indépendant scène par scène), `validation/constats_visuels_signalisation.json`. Documentation :
`hda/rg_signalisation/README_SIGNALISATION.md` ; § 17 ajouté à `hda/README_RG.md`.*

## 1. En bref

- **Ce qui est fait.** Une nouvelle HDA `rg::signalisation::1.0` et son pilote `fabriquer_signalisation.py` posent les
  panneaux, les balises et les feux sur la route déjà fabriquée, d'après les règles : régimes de priorité (AB2, AB3a +
  M9c, AB3b, AB4, AB5, AB25, B21-1, J3, J5), prescriptions (B1, B14, B33), danger (A2b, A13b), indication (C12, C20a + M9d,
  C24b des voies affectées, C27), direction (D21, D42a, D42b, D43 en carrefour ; D31d et D62c sur portique de sortie
  d'autoroute ; EB10 / EB20 d'entrée et de sortie d'agglomération avec cartouche E42), feux (R11v + répétiteur, rappels
  sur îlot, R12 + bouton d'appel, M12, lentilles allumées selon la 1re phase du contrôleur), sur supports du catalogue
  route_fr (supports ronds Ø 60,3 / 76 / 89, mâts de feux Ø 114, portique L1600, potence L600).
- **Où.** Les 17 scènes demandées (J1-J6, G1-G4, A1-A4, S07, S08, S10) et une scène nouvelle,
  `scenes_signalisation/E01_entree_agglomeration.yaml` (route départementale qui entre dans « MEYLAN » : B14 70, EB10 /
  EB20, avancé A13b + B14 30 + M9d, plateau avec C20a + M9d, B33).
- **Résultat.** 217 ensembles posés, 0 en échec, 9 sous contrainte signalée (îlots directionnels étroits, répétition à
  gauche sur la GBA d'A1). Tous les critères du lot L6 mesurés par le contrôle indépendant sont atteints (§ 4) ; les
  rendus du conducteur montrent les faces texturées, orientées vers l'usager et lisibles (§ 5).
- **Écarts au cahier des charges, assumés et justifiés (§ 6)** : pas de B14 50 sous l'EB10 (l'EB10 suffit, IISR4
  art. 63) ; sur autoroute, la séquence réglementaire d'une sortie est D41 / D31 (IISR5 art. 84 A 3), pas D42 / D43 ; la D41a
  tombe hors des scènes de 800 m ; R13, A14, B22a, AB6 / AB7 ne sont décrits dans aucune scène (posables par le
  complément).

## 2. Livrables

| Fichier | Rôle |
|---|---|
| `hda/rg_signalisation/plan_signalisation.py` | plan : quoi poser et où l'ancrer (Python hors Houdini, déterministe) |
| `hda/rg_signalisation/faces_composees.py` | faces à inscriptions de la scène (EB10, EB20, E42, D21, D42a, D42b, D43, D31, D41, D62, C24b, M1, M5, M9z) |
| `hda/rg_signalisation/vex_signalisation.py`, `construire.py`, `lecteur_signalisation.py`, `rg_signalisation.hdalc/` | HDA `rg::signalisation::1.0` (VEX : classes du sol, ancrage, placement ARB-20, plaques) |
| `hda/rg_signalisation/lecteurs_scene.py` | lecture des sorties fabriquées (sol, références, retenues) pour le pilote |
| `hda/rg_signalisation/regles_signalisation_l6.json` | 14 règles relues (IISR1, 3, 4, 5) absentes de la base fusionnée, espace `L6-`, à verser |
| `hda/rg_signalisation/README_SIGNALISATION.md` | documentation du lot |
| `fabriquer_signalisation.py` | pilote hython (plan, faces, HDA, exports, USD, rendus) |
| `scenes_signalisation/E01_entree_agglomeration.yaml` | scène nouvelle |
| `scenes_signalisation/complements/*.yaml` | complément de description de la signalisation (destinations, agglomération, sortie, vues) |
| `validation/controler_signalisation.py`, `faire_rapport_signalisation.py` | contrôle indépendant (shapely, sans Houdini) et rapport |
| sorties `recon/out/generateur/<scene>/l6/` (non versionnées) | plan, faces, `ensembles.json`, `instances.json`, `points/signalisation.json`, `points/feux.json` (pj_points/0.1), `signalisation.usda`, `mesures_l6.json`, `manifest_l6.json`, `rendus/` |

Fichiers partagés : seul `hda/README_RG.md` reçoit un § 17 (ajout). `fabriquer_generateur.py`, `description/`, `schema/`,
`rendu/`, `commun/`, `regles_route_fr.json` et les specs de l'autre équipe ne sont pas modifiés ; les sorties de la chaîne
(l1 à l5, rendus/) sont lues, jamais réécrites ; la scène de rendu de la chaîne est prise en sous-couche.

## 3. Chaîne

1. **Plan** (`l6/plan_signalisation.json`) : signaux décidés par le compilateur (régimes, feux) + règles du lot (§ 3 du
   README) + complément de description ; exigences par branche, section et itinéraire ; exclusions (bateaux fabriqués) ;
   panneaux non posés avec leur motif.
2. **HDA** sur le sol fabriqué : rive mesurée (bord extérieur de la chaussée du sens visé ; chaussée cachée sous les
   îlots écartée) ; point visé Q = rive + 0,70 + l/2 (feux : 0,70) ; recherche du point admissible le plus proche par
   anneaux de 5 cm, dans la fenêtre de l'ancrage, par cas ARB-20 (1 : 1,40 m libres côté façade ; 2 : support côté
   façade, plaque en surplomb ≥ 2,20 m ; 3 : axe réduit signalé) ; rase campagne : support à ≥ 2 m du bord, sinon
   accotement étroit ; hauteur réglementaire au-dessus du sol au pied du support ; face vers l'usager tournée de 4° vers
   l'extérieur ; support du catalogue à la hauteur exacte.
3. **Exports** : points pj_points/0.1 pour le PCG d'Unreal (asset du catalogue, p, rpy, échelle), USD (références aux
   assets avec variante de gamme, plaques composées texturées), rendus Karma (sous-couche de la scène de rendu de la
   chaîne + signalisation ; dessus, oblique 3/4, conducteur à 1,20 m).

## 4. Critères (contrôle indépendant `controler_signalisation.py`)

| Id | Critère | Valeur | Seuil | Atteint |
|---|---|---|---|---|
| L6-1 | branches et sections à régime : panneaux présents (P14-1) | 63/63 | 100 % | oui |
| L6-2 | AB4 sur une branche à feux ou « stop_a_verifier » (P14-2, ARB-19) | 0 ; test ARB-19 réussi | 0 | oui |
| L6-3 | bord du panneau à ≥ 0,70 m de la rive, sauf contrainte signalée (P14-3, ARB-20) | 0 non signalé(s) ; 11 plaque(s) sous 0,70 m signalée(s) « contrainte » sur 207 | 0 non signalé | oui |
| L6-4 | supports dans le cheminement de 1,40 m ; plaque au-dessus d'un trottoir sous 2,20 m (P14-5) | 0 sur 106 supports sur trottoir | 0 | oui |
| L6-5 | supports sur surface circulée, îlot peint ou abaissé | 0 sur 213 | 0 | oui |
| L6-6 | hauteur sous panneau (2,30 agglo / 1,00 campagne / îlot, feux, surplomb) ± 2 cm | 165/165 ; écart max 0.0 m | 100 % à ± 0,02 m | oui |
| L6-7 | feux (IISR6) : R11 à droite du couloir, au droit ou à l'aval de la ligne d'effet, bas ≥ 2,00 m, axe < 4,20 m, ≤ 2 ensembles juxtaposés ; R12 aux deux extrémités | R11 24/24 ; R12 24/24 ; R14 0 | 100 % | oui |
| L6-8 | branches à voies affectées : C24 (ou Da30) présent (P14-6, RF-MQ-DIR-01) | 6/6 | 100 % | oui |
| L6-9 | faces tournées vers l'usager (écart ≤ 15°, RF-SV-GEN.ORIENTATION) | 169/169 | 100 % | oui |
| L6-10 | séquences : EB10 / EB20 dos à dos, B14 répété à gauche sur 2 × 2 (P14-8) | 9/9 | 100 % | oui |
| L6-11 | ensembles en échec de placement (aucun point admissible) | 0 ; 9 sous contrainte signalée ; 208 conformes | 0 échec | oui |
| L6-12 | vue du conducteur : la plaque visée est dans l'image et mesure ≥ 40 px | 18/18 | 100 % | oui |
| L6-13 | déterminisme (second passage, fichiers l6 à l'octet) | 35 fichiers, écarts [] | identique | oui |
| L6-14 | rendus regardés en tuiles : faces texturées, orientées vers l'usager, lisibles dans la vue du conducteur | 18/18 | 100 % | oui |

Détail par scène : `validation/controles_signalisation.json` ; synthèse : `validation/rapport_signalisation.json`.
Les plaques en surplomb des voies (portique d'A4 ; potence quand une scène en demande) ne relèvent pas de la distance à la rive (C3) :
leur bas est contrôlé en C6 au-dessus de la chaussée sous chaque plaque, au moins égal au gabarit
(L6-SV-SURPLOMB.GABARIT : 4,90 m sur route, 5,35 m sur autoroute ; portique du catalogue à 5,50 m). Le M12 d'un mât de
feu suit l'axe du mât (0,70 m, DEF-027) et n'est pas non plus compté en C3.

**Contraintes signalées (9 ensembles)** : AB3a « petite » et J5 sur les nez d'îlots directionnels de J5 et J6 (largeur de
l'îlot au nez < 2 × 0,70 + l : IISR3 art. 43-4 D « si possible ») ; J5 de l'îlot nord de J4 ; répétitions à gauche du B14
d'A1 fixées sur la GBA du terre-plein central de 2,60 m (bord de la plaque à 0,67 m de la rive : IISR1 art. 8 i,
contrainte).

**Test ARB-19** : une copie de J2 dont la branche nord passe au régime « stop_a_verifier » garde son AB4 dans le modèle ;
le plan le refuse (écrit dans `non_poses`, règle ARB-19) et l'exigence de la branche l'interdit.

## 5. Rendus regardés

Trois vues par scène (dessus, oblique 3/4, conducteur à 1,20 m), planche ≤ 1092 px
(`recon/out/generateur/<scene>/l6/rendus/planche_l6_<scene>.png`) et tuiles natives (`l6/rendus/tuiles/`). Constats
(`validation/constats_visuels_signalisation.json`) :

| Scène | Vue du conducteur | Texturées | Orientées | Lisibles | Constat |
|---|---|---|---|---|---|
| E01_entree_agglomeration | EB10 « MEYLAN » + cartouche « D 1090 » | oui | oui | oui | tuile native : MEYLAN et D 1090 lisibles ; A13b + 30 + M9d au support suivant, C20a au plateau ; revers gris de l'EB20 à gauche ; trottoirs qui commencent à la limite |
| J1_T_cedez | AB3a + M9c et ensemble D21 en face | oui | oui | oui | tuile native : « CÉDEZ LE PASSAGE », D21 « GRENOBLE » (pointe à gauche) et « MONTBONNOT » (pointe à droite) lisibles ; AB3a au coin, hors chaussée |
| J2_croix_stop | AB4 | oui | oui | oui | STOP lisible sur l'accotement ; balises J3 rouges et blanches aux angles ; D43 et AB5 en amont |
| J3_croix_feux | R11v + répétiteur | oui | oui | oui | tuile native : R11 au rouge (1re phase) et répétiteur ; R12 au vert de la traversée parallèle ; mâts hors du cheminement |
| J4_ilots_directionnel_separateurs | AB3a sur l'îlot directionnel | oui | oui | oui | AB3a + M9c lisible ; J5 au nez de l'îlot ; revers des AB3a des autres branches |
| J5_carrefour_complexe | R11v de droite (voies directes) | oui | oui | oui | R11 au vert sur le trottoir de droite et rappel sur l'îlot de TAG ; AB3a de l'îlot directionnel, J5 et C24b visibles |
| J6_carrefour_complexe_2x2 | R11v de droite (voies directes) | oui | oui | oui | même disposition que J5 sur les deux avenues ; feux et J5 lisibles |
| G1_giratoire_urbain_D40 | AB25 | oui | oui | oui | AB25 lisible ; B21-1 sur l'îlot central face à l'entrée ; D21 aux sorties |
| G2_giratoire_periurbain_D50 | D42b à 150 m | oui | oui | oui | tuile native : D42b « CORENC », « GRENOBLE », « SAINT-ISMIER » lisibles ; AB25 ramené à 100 m derrière ; support sur l'accotement hors emprise |
| G3_mini_giratoire_D20 | AB25 | oui | oui | oui | AB25 puis D42b 15 m plus loin, sans masque ; pas de B21-1 (mini-giratoire) |
| G4_giratoire_multivoie_D50 | AB25 | oui | oui | oui | AB25 lisible ; B21-1 au centre ; D21 aux sorties |
| A1_autoroute_2x2_GBA | B14 130 « RAPPEL » à droite | oui | oui | oui | B14 130 + RAPPEL à droite et répété à gauche sur la GBA (contrainte signalée) |
| A2_autoroute_2x3_glissieres | B14 130 « RAPPEL » à droite | oui | oui | oui | B14 130 + RAPPEL à droite et sur le terre-plein central derrière la glissière |
| A3_bretelle_entree | AB3a + M9c d'insertion | oui | oui | oui | AB3a + M9c à droite de la bretelle au bout du musoir ; B14 110 RAPPEL après l'insertion |
| S08 | C27 (dos-d'âne) | oui | oui | oui | C20a au passage puis C27 au dos-d'âne, lisibles ; B14 30 + A2b à l'entrée de la rue ; supports hors cheminement |
| S10 | C20a + M9d au plateau | oui | oui | oui | C20a + M9d (passage surélevé) lisibles au plateau ; à l'entrée de la rue, A13b + B14 30 + M9d sur le même support |
| A4_bretelle_sortie | portique : D62c filante + D31d de sortie | oui | oui | oui | portique L1600 au-dessus des deux voies et de la voie de sortie : D62c « CHAMBÉRY » à flèches vers le bas au-dessus des voies, D31d « SORTIE 13 / MEYLAN / MONTBONNOT » au-dessus de la voie de sortie, faces perpendiculaires à l'axe, lisibles à ~110 m (tuile native) ; vue de dessus : le portique n'est qu'un trait |
| S07 | C12 (sens unique) à l'entrée de la rue | oui | oui | oui | C12 lisible sur le trottoir de droite à l'entrée ; B1 au bout opposé vu de dos (il fait face au sens interdit) ; la caméra est à 22 m en amont du début de la rue, hors du tronçon modélisé |

## 6. Écarts au cahier des charges et limites

| Demande | Ce qui est fait | Raison |
|---|---|---|
| scène d'entrée d'agglomération avec « B14 50 » | EB10 seul à 50 km/h ; B14 70 en palier avant l'entrée ; B33 (fin de 30) après le plateau | IISR4 art. 63 (RF-SV-B14.EMPLOI agglo_50 : « pas de B14, le EB10 suffit ») ; art. 68-2 (L6-SV-B33.EMPLOI) |
| sur autoroute, D42 / D43 avant une sortie | D31d (signalisation avancée) au point où la voie de sortie a 1,50 m et D62c (filante), sur portique ; D41a à 30 s | IISR5 art. 83-2, 83-4 et tableau de l'art. 84 A 3 : D42 / D43 servent aux carrefours, la séquence d'une sortie est D51, D41, D62, D31 |
| D41a à la distance réglementaire | non posée : 917 m en amont du D31d, hors de la scène (800 m) ; écrite dans `non_poses` | L6-SV-D40.POSITION ; aucune position fausse posée « pour l'image » |
| D51c | non posée : l'espacement des échangeurs (≥ 5 km) n'est pas décrit | L6-SV-D50.EMPLOI |
| R13 bus, A14, B22a, AB6 / AB7 | non posés : aucune scène ne les décrit (pas de phase bus, de danger particulier, de piste obligatoire ni d'itinéraire à caractère prioritaire) | posables par le complément (`panneaux:`) ; pas de règle d'inférence sans description |
| D21 en carrefour | ensemble D21 en face de la branche non prioritaire d'un T ; D21 à chaque sortie de giratoire | les D21 des carrefours en croix et à feux ne sont pas posés (D42a / D43 en présignalisation) |
| panneaux lisibles | faces officielles du catalogue ; faces à inscriptions dessinées en Bahnschrift | caractères L1 / L4 de l'IISR non disponibles ; faces de scène, pas des signaux officiels |

Autres limites : les choix de générateur [G] (écarts de 15 m entre panneaux du même sens, 0,05 m entre plaques, 1 m
entre supports, portique ramené à la portée mesurée, pied de portique et répétition à gauche fixés sur le séparateur
béton, M12 réduit à 300 mm et décalé, vue d'un abaissé) sont déclarés dans l'aide des paramètres et dans
`regles_signalisation_l6.json`. Le modèle `modele_voie/0.1` ne porte qu'un contexte par route : la limite
d'agglomération d'E01 vient du complément, et le plateau d'E01 est admis par écart (RF-MA-RAL-001) dans la section
limitée à 30 par les B14 posés.

## 7. Commandes

```
hython recon/generateur/fabriquer_signalisation.py recon/out/generateur/<scene> [...] [--rendus] [--construire-hda]
hython recon/generateur/fabriquer_signalisation.py recon/generateur/scenes_signalisation/E01_entree_agglomeration.yaml --rendus
python recon/generateur/validation/controler_signalisation.py
python recon/generateur/validation/faire_rapport_signalisation.py --determinisme
```
