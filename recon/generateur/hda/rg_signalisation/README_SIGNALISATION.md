# rg::signalisation — lot L6 (étape E14) : signalisation verticale et feux

*`recon/generateur/hda/rg_signalisation/README_SIGNALISATION.md`, 22/10/2026. Plan : `PLAN_GENERATEUR.md` (lot L6),
`CHAINE_CONSTRUCTION.md` (fiche E14). Rapport : `validation/RAPPORT_signalisation.md`, `validation/rapport_signalisation.json`.*

La chaîne fabrique d'abord la route (étapes E01 à E13 : sol, bordures, marquages, carrefours, giratoires, retenues).
Ce lot pose ensuite les panneaux, les balises et les feux, comme sur un chantier : **d'après les régimes, les lignes et
les surfaces déjà fabriquées**. Le travail est partagé en deux temps.

1. **Le plan** (`plan_signalisation.py`, Python pur, hors Houdini, déterministe) décide quoi poser et où l'ancrer :
   route, abscisse, côté, sens de l'usager visé, hauteur réglementaire, gamme, plaques de bas en haut, règles citées.
   Il reprend les signaux déjà décidés par le compilateur (AB3a, AB4, AB25, B21-1, J3, R11, R12…) et ajoute ce que
   les règles exigent ou proposent : J5 aux nez d'îlots, D21 / D42 / D43 en carrefour, D31 et D41 d'autoroute, C24b des
   voies affectées, B14 et rappels, C12 et B1 des sens uniques, C27, C20a, A2b, A13b des ralentisseurs et passages,
   EB10 / EB20 et paliers de vitesse décrits, M12 et boutons d'appel des feux.
2. **L'HDA** `rg::signalisation::1.0` (VEX) fait la géométrie sur le sol fabriqué : rive mesurée, règle de placement
   ARB-20, cheminement de 1,40 m, refus des surfaces circulées, îlots peints, abaissés et emprises de retenue, recherche
   du point admissible le plus proche du point visé, hauteur, orientation, empilement des plaques, têtes de feux,
   choix du support du catalogue route_fr, contrôles.

```
plan_signalisation.py (modèle, l1, l3, l2/entites, autoroute/, complément) ──► l6/plan_signalisation.json ──┐
faces_composees.py ──► l6/faces/*.png (EB10, EB20, E42, D21, D42, D43, D31, D41, C24b, M1, M5, M9z)       │
                                                                                                        ▼
l2/sol_*.npy ─ lire_sol ─────────┐   rg::signalisation  lire_ensembles, lire_exclusions (Python : lecture du plan)
l1/courbes ─ lire_references ────┼─► classer (VEX, classes du sol, chaussée cachée sous les îlots) ─► rive à plat
autoroute/ ─ lire_obstacles ─────┘    exclusions (abaissés) + obstacles (retenue) ─► interdits
                                       ancrer (point et tangente de la référence) ─► placer (VEX) ─► plaques (VEX)
   sorties : 1 ENSEMBLES (supports, contrôles) · 2 INSTANCES (assets) · 3 PLAQUES (faces composées) · 4 CONTEXTE
fabriquer_signalisation.py ─► l6/ensembles.json, instances.json, points/signalisation.json, points/feux.json
                              (pj_points/0.1), signalisation.usda, mesures_l6.json, manifest_l6.json, rendus/
```

## 1. Classes du sol (paramètres de l'HDA)

| cl | Classes du sol fabriqué | Rôle |
|---|---|---|
| 1 | voies, bandes cyclables, stationnement, chaussée de carrefour, zone neutralisée, musoir, caniveaux | **chaussée** : la rive est son bord ; jamais de support |
| 2 | BDD, BAU, accotement revêtu, piste, voie verte ; îlot de giratoire en pavés (couronne franchissable) | circulée : jamais de support |
| 3 | trottoir, trottoir de carrefour, quai, chemin | piéton : cheminement de 1,40 m (RF-MA-TRO-001) |
| 4 | terre-plein, îlots (carrefour, giratoire), séparateur | îlot bordé : support admis (RF-SV-GEN.EMPLACEMENT) |
| 5 | berme, accotement de carrefour, terre-plein latéral, bande plantée | accotement : rase campagne, support à ≥ 2 m du bord sauf accotement étroit |
| 6 / −1 | abord du modèle / terrain hors de l'emprise fabriquée | admis en rase campagne seulement, signalé |
| 7 / 8 | corps de bordure, murs ; chaussée cachée sous un îlot posé dessus | ni support, ni rive |

## 2. Placement (VEX `placer`)

- **Rive** : marche latérale depuis la référence, côté visé ; la rive est le bord extérieur de la chaussée du sens visé
  (un îlot de moins de 5,00 m entre deux couloirs est franchi [G]) ; au coin d'un carrefour, la rive 8 m en amont est
  prolongée (« rive prolongée (coin) »). Point visé Q = rive + a.
- **ARB-20** : cas 1, axe à 0,70 + l/2 de la rive (feux : 0,70, DEF-027) avec 1,40 m libres côté façade ; cas 2, support
  côté façade à ≥ 1,40 + r du bord, plaque en surplomb à ≥ 2,20 m ; cas 3, axe réduit signalé « IISR1 8 i, contrainte ».
  Rase campagne : support à ≥ 2 m du bord (RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE), sinon accotement étroit (exception
  de la même règle, bord du panneau toujours ≥ 0,70 m). Îlot : aplombs à 0,70 m des rives « si possible » (IISR3 43-4 D).
- **Recherche** : anneaux de 5 cm autour de Q (fenêtre longitudinale de l'ancrage : AB3a / AB4 au droit de la ligne
  −6 / +1 m ; R11 de −0,30 à +3,00 m de l'ancre, soit au droit ou à l'aval de la ligne d'effet) ; le point retenu est le
  plus proche de Q qui satisfait le meilleur cas ; refus : surface non admise, disque du support hors surface,
  abaissé (vue < 0,05 m, RF-MA-TRO-015, et bandes de 1,20 m de part et d'autre des bateaux fabriqués), emprise d'un
  dispositif de retenue, autre support à moins de 1 m [G].
- **Hauteur** : bord inférieur de la plaque la plus basse à la hauteur du plan au-dessus du sol au pied du support
  (DEF-025 : 2,30 agglomération, 1,00 rase campagne ; DEF-026 / ARB-04 : J5 1,00, prescription d'îlot 0,60 [G] en
  agglomération ; DEF-027 : feux 2,30, répétiteur 1,40, R12 2,10, bouton 1,00 ; L6-SV-SURPLOMB.GABARIT : 5,35 m au-dessus
  de la chaussée d'autoroute). Plaques empilées de bas en haut, écart 0,05 m [G].
- **Orientation** : face vers l'usager, tournée de 4° vers l'extérieur (DEF-025) ; R12 vers le trottoir de départ ;
  répétiteur vers le premier véhicule arrêté [G] ; D21 de sortie de giratoire vers l'anneau.
- **Supports** : support rond du catalogue (Ø 60,3 / 76 / 89 / 114, IISR1 art. 6 B) de la hauteur juste supérieure,
  mis à la hauteur exacte par une échelle en Z ; mâts de feux D114 H34 / H42 (ARB-05) ; potence de signalisation L600
  allongée pour le gabarit d'autoroute.

## 3. Ce que le plan ajoute (règles)

| Situation | Panneaux | Règles |
|---|---|---|
| giratoire | D42b à 6 s (rase campagne : 150 m, AB25 ramené à 100 m) ; D21 à chaque sortie | RF-SV-D.TEMPS_DE_PARCOURS, RF-SV-AVANCE.DIST.RASE_CAMPAGNE, RF-SV-D.HAUTEURS ; L6-SV-D21.SORTIE_GIRATOIRE [G] |
| carrefour à feux, complexe ou à îlots | D42a à 6 s | RF-SV-D.TEMPS_DE_PARCOURS |
| carrefour simple hors agglomération | D43 à 3 s | idem |
| T, branche non prioritaire | ensemble D21 en face de la branche | RF-SV-D21.POSITION ; L6-SV-D21.FACE_A_LA_BRANCHE [G] |
| voies affectées (flèches) | C24b au début des flèches | RF-MQ-DIR-01, RF-SV-C24.EMPLOI |
| nez d'îlot (balise J5 du compilateur) | J5 de 700 mm, ou 500 mm sous 2,10 m de large | RF-SV-J5, RF-GV-ILO-008, DEF-026 |
| sens unique | C12 au début, B1 à l'autre bout | RF-SV-C12.EMPLOI, RF-SV-B1.POSITION |
| rue à 30 | B14 30 aux entrées | RF-SV-B14.EMPLOI |
| dos-d'âne / plateau | C27 ; C20a + M9d (passage surélevé) ; avancé A2b + B14 30, A13b + B14 30 + M9d | RF-SV-C27.RALENTISSEUR, RF-SV-C20A.EMPLOI, RF-SV-A13B.EMPLOI, RF-SV-ORDRE.VERTICAL |
| autoroute | B14 « RAPPEL » à droite et à gauche ; AB3a + M9c d'insertion ; portique de sortie où la voie de sortie a 1,50 m : D31d au-dessus de la voie de sortie, D62c (filante) au-dessus des voies directes ; D41a à 30 s (hors scène : non posé) | RF-SV-B14.EMPLOI, RF-SV-GEN.REPETITION_GAUCHE_2X2, L6-SV-AB3A.INSERTION, L6-SV-D30.POSITION, L6-SV-D40.POSITION, L6-SV-ECHANGEUR.SUPPORTS |
| feux | R11 + répétiteur, rappel sur îlot, R12 + bouton d'appel, M12 si sas vélo ou bande cyclable ; lentilles allumées selon la 1re phase | RF-FEU.*, DEF-027, RF-FEU.BOUTON_APPEL, RF-FEU.M12 |
| branche à feux ou « stop_a_verifier » | AB4 refusé même si le modèle en porte un | RF-SV-AB4.POSITION, ARB-19 |
| complément décrit | EB10 / EB20, paliers B14, B33, panneaux un à un | RF-SV-EB.POSITION, RF-SV-B14.EMPLOI, L6-SV-B33.EMPLOI |

Règles absentes de la base fusionnée (autoroutes, gabarit, fin de limitation, choix de générateur) : fichier
`regles_signalisation_l6.json` (espace `L6-`, sources et pages), à verser dans `regles_route_fr.json` par son propriétaire.

## 4. Complément de description de la signalisation

`recon/generateur/scenes_signalisation/complements/<scene>.yaml` (facultatif ; sans lui, destinations génériques) :

```yaml
directions: {ouest: "Grenoble", est: "Montbonnot", sud: "Meylan centre"}   # destination de chaque branche de sortie
agglomeration: {nom: "MEYLAN", cartouche: "D 1090"}                         # EB10 / EB20 et cartouche E42
limite_agglomeration: {troncon: R-1, a: 150, vitesse_hors: 80}
panneaux: [{id: B14_70, troncon: R-1, a: 50, sens: avant, codes: [B14_70], agglomeration: non, regles: [RF-SV-B14.EMPLOI]}]
sortie: {numero: "13", destinations: ["Meylan", "Montbonnot"]}             # D31d / D41a
feux: {boutons: oui, m12: [ouest]}
vue_conducteur: {ensemble: E-J1.sud.AB3a, recul: 22, focale: 45}           # vue du conducteur des rendus
```

Le compilateur de description refuse les clés inconnues : ce complément est donc un fichier à part (comme
`<scene>.vues.json` du lot bordures), lu par le seul plan de signalisation. Il pourra être versé dans le format de
description par l'intégration.

## 5. Commandes

```
hython recon/generateur/fabriquer_signalisation.py recon/out/generateur/J5_carrefour_complexe [--rendus] [--construire-hda]
hython recon/generateur/fabriquer_signalisation.py recon/generateur/scenes_signalisation/E01_entree_agglomeration.yaml --rendus
python recon/generateur/validation/controler_signalisation.py [recon/out/generateur/<scene> ...]
python recon/generateur/validation/faire_rapport_signalisation.py [--determinisme]
```

## 6. Limites

- Les ensembles D21 ne sont posés qu'en T (branche non prioritaire) et aux sorties de giratoire ; pas de D61
  (confirmation) ni de D29.
- D41a et D51c d'autoroute tombent hors des scènes de 800 m : non posés, écrits dans `non_poses`.
- Le modèle ne porte qu'un contexte par route : la limite d'agglomération et les limites de vitesse locales viennent
  du complément (E01 : écart admis RF-MA-RAL-001 pour le plateau dans la section à 30).
- Faces composées en police Bahnschrift (dessin DIN 1451), à défaut des caractères L1 / L4 de l'IISR.
- Portique de sortie : l'asset portique_signalisation_L1600 (16 m) est ramené à la portée mesurée (accotement de droite →
  axe du terre-plein central, pied fixé sur le séparateur béton [G]) par une échelle en X ; la potence L600 (bas 5,00 m
  au catalogue) reste disponible, allongée pour le gabarit d'autoroute (5,35 m). Le contrôle indépendant exclut les
  plaques en surplomb (potence, portique) de la distance à la rive (C3) et vérifie leur bas au-dessus de la chaussée
  sous chaque plaque (C6, ≥ gabarit ; A4 : 5,50 m).
- Abaissé : partie abaissée de la bordure (bateau fabriqué, vue 0,02 m, DEF-031) et zone d'attente de 1,20 m de part et
  d'autre de la face, plus le fond de l'abaissé (vue < 0,03 m) ; les rampants latéraux ne sont pas exclus.
- M12 : panonceau de 300 mm (RF-SV-DIM.M12) décalé vers la chaussée pour ne pas surplomber le cheminement sous
  2,20 m ; accessoire du feu, il suit la règle latérale des feux (axe du mât à 0,70 m, DEF-027) et non celle des
  panneaux (bord à 0,70 m).
